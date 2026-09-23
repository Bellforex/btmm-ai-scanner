from datetime import UTC, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from btmm_ai_scanner.service.app import app

client = TestClient(app, raise_server_exceptions=False)


def _bars(count: int, *, start: Decimal, step_minutes: int, step: Decimal) -> list[dict]:
    origin = datetime(2026, 1, 1, tzinfo=UTC)
    price = start
    out: list[dict] = []
    for i in range(count):
        open_price = price
        close_price = price + step
        high = max(open_price, close_price) + Decimal("0.05")
        low = min(open_price, close_price) - Decimal("0.05")
        out.append(
            {
                "time": (origin + timedelta(minutes=step_minutes * i)).isoformat(),
                "open": str(open_price),
                "high": str(high),
                "low": str(low),
                "close": str(close_price),
                "volume": "100",
            }
        )
        price = close_price
    return out


def _scalp_payload(request_id: str = "test-request-1") -> dict:
    return {
        "request_id": request_id,
        "symbol": "XAUUSD",
        "mode": "SCALP",
        "presentation_timeframe": "M15",
        "timeframes": {
            "H4": _bars(50, start=Decimal("2000.00"), step_minutes=240, step=Decimal("0.30")),
            "H3": _bars(50, start=Decimal("2000.00"), step_minutes=180, step=Decimal("0.30")),
            "H2": _bars(50, start=Decimal("2000.00"), step_minutes=120, step=Decimal("0.30")),
            "H1": _bars(50, start=Decimal("2000.00"), step_minutes=60, step=Decimal("0.30")),
            "M15": _bars(50, start=Decimal("2000.00"), step_minutes=15, step=Decimal("0.30")),
            "M5": _bars(50, start=Decimal("2000.00"), step_minutes=5, step=Decimal("0.30")),
        },
    }


def test_health_endpoint_reports_safe_metadata_only() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert set(body) == {
        "status",
        "scanner_git_sha",
        "contract_version",
        "schema_version",
        "rule_version",
    }


def test_analyze_returns_a_versioned_contract_for_a_well_formed_request() -> None:
    response = client.post("/v1/analyze", json=_scalp_payload())
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "test-request-1"
    assert body["contract"]["mode"] == "SCALP"
    assert body["contract"]["setup"]["verdict"] in {
        "VALID_SETUP",
        "WATCH_FOR_ALIGNMENT",
        "NO_VALID_SETUP",
        "INSUFFICIENT_DATA",
    }
    # Never a fabricated/validated trade plan (Phase 2's own hard constraint).
    assert body["contract"]["trade_plan"] == {"status": "NOT_VALIDATED"}
    assert "annotations" in body
    assert "boxes" in body["annotations"]


def test_analyze_is_deterministic_for_an_identical_request() -> None:
    payload = _scalp_payload()
    first = client.post("/v1/analyze", json=payload).json()
    second = client.post("/v1/analyze", json=payload).json()
    # evaluated_at_utc is the real processing instant (Phase 5: candles are
    # stamped with the actual processing time), so it legitimately differs
    # between two calls — every other analytical field must not.
    first_contract = {k: v for k, v in first["contract"].items() if k != "evaluated_at_utc"}
    second_contract = {k: v for k, v in second["contract"].items() if k != "evaluated_at_utc"}
    assert first_contract == second_contract
    assert first["annotations"] == second["annotations"]


def test_analyze_reports_insufficient_data_without_an_execution_timeframe() -> None:
    payload = _scalp_payload()
    # SCALP's authority set is H1-H4; supplying only authority timeframes
    # (no M15/M5 execution timeframe) is a well-formed request that the
    # engine itself classifies as SetupVerdict.INSUFFICIENT_DATA — a normal
    # 200 result, never an HTTP error (correlation/engine.py's own
    # docstring: "a normal 'not enough supplied timeframes' case ... never
    # raised"). This is the failure-taxonomy distinction Phase 2 requires:
    # engine unavailability (a real error) vs. a genuine analytical verdict.
    payload["timeframes"] = {
        "H4": payload["timeframes"]["H4"],
        "H3": payload["timeframes"]["H3"],
        "H2": payload["timeframes"]["H2"],
        "H1": payload["timeframes"]["H1"],
    }
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()
    assert body["contract"]["setup"]["verdict"] == "INSUFFICIENT_DATA"
    assert body["contract"]["setup"]["selected_candidate"] is None


def test_analyze_rejects_an_unsupported_symbol_with_422() -> None:
    payload = _scalp_payload()
    payload["symbol"] = "BTCUSD"
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_rejects_an_empty_timeframe_bundle_with_422() -> None:
    payload = _scalp_payload()
    payload["timeframes"] = {}
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 422


def test_analyze_never_leaks_a_traceback_on_error() -> None:
    payload = _scalp_payload()
    payload["symbol"] = "BTCUSD"
    response = client.post("/v1/analyze", json=payload)
    text = response.text
    assert "Traceback" not in text
    assert "File \"" not in text
