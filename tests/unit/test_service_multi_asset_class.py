"""Bell Academy Hub Phase 2C — engine-generalization test matrix.

Proves the claim the Phase 2C `InternalSymbol` audit made: the BTMM/POI/BTRC
analytical core carries zero currency-pair-specific branching, so a
non-forex symbol (crypto, a stock) scans exactly like a forex one through
the same live HTTP `/v1/analyze` path — no crash, deterministic, and
`NO_VALID_SETUP`/`INSUFFICIENT_DATA` remain ordinary, reachable verdicts.

These are deterministic, hand-built fixtures — TEST DATA ONLY, not real
market data for any of the three symbols, and not a claim that crypto/stock
market-data ingestion, session-aware timeframe aggregation, or the
Fri-Sun `is_likely_market_closure()` gap heuristic (historical_backtest
only, not reachable from this HTTP path) have been generalized — see
`InternalSymbol`'s own docstring in config/enums.py for exactly what
remains unaddressed.
"""

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


def _scalp_payload(symbol: str, start: Decimal, step: Decimal, request_id: str) -> dict:
    return {
        "request_id": request_id,
        "symbol": symbol,
        "mode": "SCALP",
        "presentation_timeframe": "M15",
        "timeframes": {
            "H4": _bars(50, start=start, step_minutes=240, step=step),
            "H3": _bars(50, start=start, step_minutes=180, step=step),
            "H2": _bars(50, start=start, step_minutes=120, step=step),
            "H1": _bars(50, start=start, step_minutes=60, step=step),
            "M15": _bars(50, start=start, step_minutes=15, step=step),
            "M5": _bars(50, start=start, step_minutes=5, step=step),
        },
    }


def _assert_scan_is_well_formed(response) -> None:  # type: ignore[no-untyped-def]
    assert response.status_code == 200
    body = response.json()
    assert body["contract"]["setup"]["verdict"] in {
        "VALID_SETUP",
        "WATCH_FOR_ALIGNMENT",
        "NO_VALID_SETUP",
        "INSUFFICIENT_DATA",
    }
    assert body["contract"]["trade_plan"] == {"status": "NOT_VALIDATED"}
    assert "boxes" in body["annotations"]


def test_forex_fixture_scans_without_crashing() -> None:
    payload = _scalp_payload("XAUUSD", Decimal("2000.00"), Decimal("0.30"), "forex-fixture-1")
    _assert_scan_is_well_formed(client.post("/v1/analyze", json=payload))


def test_crypto_fixture_scans_without_crashing() -> None:
    # A materially different price scale/step than the forex fixture (BTCUSD
    # trades in the tens of thousands, not around 2000) — this is exactly
    # the kind of "does anything hard-code a forex-shaped price range"
    # question the audit could not answer by reading code alone.
    payload = _scalp_payload("BTCUSD", Decimal("65000.00"), Decimal("120.00"), "crypto-fixture-1")
    _assert_scan_is_well_formed(client.post("/v1/analyze", json=payload))


def test_stock_fixture_scans_without_crashing() -> None:
    payload = _scalp_payload("AAPL", Decimal("190.00"), Decimal("0.40"), "stock-fixture-1")
    _assert_scan_is_well_formed(client.post("/v1/analyze", json=payload))


def test_crypto_and_stock_scans_are_deterministic() -> None:
    for symbol, start, step in [
        ("BTCUSD", Decimal("65000.00"), Decimal("120.00")),
        ("AAPL", Decimal("190.00"), Decimal("0.40")),
    ]:
        payload = _scalp_payload(symbol, start, step, f"determinism-{symbol}")
        first = client.post("/v1/analyze", json=payload).json()
        second = client.post("/v1/analyze", json=payload).json()
        first_contract = {k: v for k, v in first["contract"].items() if k != "evaluated_at_utc"}
        second_contract = {k: v for k, v in second["contract"].items() if k != "evaluated_at_utc"}
        assert first_contract == second_contract, symbol
        assert first["annotations"] == second["annotations"], symbol


def test_crypto_fixture_can_reach_no_valid_setup_and_insufficient_data() -> None:
    # Same "authority-only, no execution timeframe" shape already proven for
    # forex in test_service_app.py — repeated here for a non-forex symbol so
    # INSUFFICIENT_DATA is proven reachable regardless of asset class.
    payload = _scalp_payload("BTCUSD", Decimal("65000.00"), Decimal("120.00"), "crypto-insufficient-1")
    payload["timeframes"] = {
        "H4": payload["timeframes"]["H4"],
        "H3": payload["timeframes"]["H3"],
        "H2": payload["timeframes"]["H2"],
        "H1": payload["timeframes"]["H1"],
    }
    response = client.post("/v1/analyze", json=payload)
    assert response.status_code == 200
    assert response.json()["contract"]["setup"]["verdict"] == "INSUFFICIENT_DATA"


def test_stock_fixture_top_down_correlation_remains_deterministic_across_modes() -> None:
    for mode in ("SCALP", "DAY_TRADE", "SWING"):
        payload = _scalp_payload("AAPL", Decimal("190.00"), Decimal("0.40"), f"stock-mode-{mode}")
        payload["mode"] = mode
        if mode == "DAY_TRADE":
            payload["timeframes"] = {
                "D1": _bars(50, start=Decimal("190.00"), step_minutes=1440, step=Decimal("0.40")),
                "H12": _bars(50, start=Decimal("190.00"), step_minutes=720, step=Decimal("0.40")),
                "H9": _bars(50, start=Decimal("190.00"), step_minutes=540, step=Decimal("0.40")),
                "H4": _bars(50, start=Decimal("190.00"), step_minutes=240, step=Decimal("0.40")),
                "H1": _bars(50, start=Decimal("190.00"), step_minutes=60, step=Decimal("0.40")),
            }
        elif mode == "SWING":
            # NormalizedCandle requires availability_time_utc (real
            # processing "now") to be strictly later than every bar's own
            # event_time_utc — 50 weekly bars from _bars()'s fixed 2026-01-01
            # origin would run for ~50 weeks, overshooting into the future
            # relative to whenever this test actually runs. Fewer W1 bars
            # keeps the whole fixture safely in the past.
            payload["timeframes"] = {
                "W1": _bars(10, start=Decimal("190.00"), step_minutes=10080, step=Decimal("0.40")),
                "D1": _bars(50, start=Decimal("190.00"), step_minutes=1440, step=Decimal("0.40")),
                "H4": _bars(50, start=Decimal("190.00"), step_minutes=240, step=Decimal("0.40")),
            }
        response = client.post("/v1/analyze", json=payload)
        assert response.status_code == 200, mode
        assert response.json()["contract"]["mode"] == mode
