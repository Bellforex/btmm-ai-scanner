"""Tests for the V1-A report generator (``tests/parity_support/v1a_report.py``).

Includes a dedicated protocol §12 compliance test: no prohibited
trade-profitability metric name may appear anywhere in a built report,
under any key, at any nesting depth.
"""

from __future__ import annotations

import json
from decimal import Decimal

from tests.parity_support.v1a_report import (
    _distribution,
    build_frequency_tables,
    build_report,
    compute_event_outcomes,
    compute_incomplete_terminal_lifecycle_count,
    compute_poi_outcomes,
)

D = Decimal


def _event(
    *,
    bar_index: int,
    event_type: str = "POI_ACTIVATED",
    poi_record_id: str = "poi-1",
    direction: str = "BULLISH",
    poi_type: str = "BUY_ORDER_BLOCK",
    origin_timeframe: str = "M15",
    permission: str = "BUY_BIAS",
    score: int = 70,
    band: str = ">=65",
    btmm_valid: bool = True,
    trend_alignment: str = "ALIGNED",
    regime: str = "TREND",
    session: str = "LONDON",
    volatility_state: str = "NORMAL",
    day: str = "2026-06-01",
    week: str = "2026-W23",
) -> dict:
    return {
        "event_type": event_type,
        "bar_index": bar_index,
        "bar_ms": bar_index * 900_000,
        "poi_record_id": poi_record_id,
        "poi_idx": 0,
        "poi_type": poi_type,
        "poi_direction": direction,
        "origin_timeframe": origin_timeframe,
        "zone_top": "105",
        "zone_bottom": "100",
        "btrc_score": score,
        "btrc_score_band": band,
        "btrc_permission": permission,
        "btmm_valid": btmm_valid,
        "trend_alignment": trend_alignment,
        "regime": regime,
        "session": session,
        "volatility_state": volatility_state,
        "poi_lifecycle_status": "NO_BREACH",
        "calendar_day": day,
        "iso_week": week,
    }


def _ohlc_row(high: str, low: str, close: str) -> dict:
    return {"high": high, "low": low, "close": close}


def _dev_series(n: int, start_close: float = 100.0, step: float = 0.5) -> list[dict]:
    rows = []
    price = start_close
    for _ in range(n):
        price += step
        rows.append(_ohlc_row(str(price + 0.3), str(price - 0.3), str(price)))
    return rows


def test_distribution_known_values() -> None:
    values = [D("1"), D("2"), D("3"), D("4"), D("5")]
    dist = _distribution(values)
    assert dist["n"] == 5
    assert dist["mean"] == 3.0
    assert dist["median"] == 3.0


def test_distribution_empty_is_all_none() -> None:
    dist = _distribution([])
    assert dist["n"] == 0
    assert dist["mean"] is None


def test_compute_event_outcomes_and_report_smoke() -> None:
    dev_m15 = _dev_series(60)
    events = [_event(bar_index=5), _event(bar_index=5, event_type="BTMM_VALIDATED")]
    atr_series: list[Decimal | None] = [None] * 20 + [D("1")] * 40
    outcomes, exclusions = compute_event_outcomes(events, dev_m15, atr_series, {})
    assert len(outcomes) == 2
    # bar_index=5 -> atr_series[5] is None (index < 20) -> both events counted.
    assert atr_series[5] is None
    assert exclusions.atr_warmup == 2


def test_atr_warmup_exclusion_counted() -> None:
    dev_m15 = _dev_series(60)
    events = [_event(bar_index=5)]
    atr_series: list[Decimal | None] = [None] * 60
    _, exclusions = compute_event_outcomes(events, dev_m15, atr_series, {})
    assert exclusions.atr_warmup == 1


def test_horizon_censored_exclusion_counted_near_dev_end() -> None:
    dev_m15 = _dev_series(3)  # only 3 bars total
    events = [_event(bar_index=0)]
    atr_series: list[Decimal | None] = [D("1")] * 3
    _, exclusions = compute_event_outcomes(events, dev_m15, atr_series, {})
    # horizons [1,2,3,4,8,12,24,48] -- only horizon 1,2 fit in 2 remaining bars
    assert exclusions.horizon_censored == 6


def test_compute_poi_outcomes_smoke() -> None:
    dev_m15 = _dev_series(20)
    poi_registry = [
        {
            "record_id": "poi-1",
            "poi_idx": 0,
            "poi_type": "BUY_ORDER_BLOCK",
            "poi_direction": "BULLISH",
            "origin_timeframe": "M15",
            "effective_timeframe": "M15",
            "zone_top": "101",
            "zone_bottom": "99",
            "strength_tier": "STANDARD",
            "availability_time_utc": "2026-06-01T00:00:00+00:00",
            "first_seen_bar_index": 2,
        }
    ]
    atr_series: list[Decimal | None] = [D("1")] * 20
    outcomes, exclusions = compute_poi_outcomes(poi_registry, dev_m15, atr_series, {})
    assert len(outcomes) == 1
    assert exclusions.missing_context == 0


def test_incomplete_terminal_lifecycle_counts_never_terminated_eligible_pois() -> None:
    poi_registry = [
        {"record_id": "poi-1", "poi_type": "BUY_ORDER_BLOCK"},
        {"record_id": "poi-2", "poi_type": "BUY_ORDER_BLOCK"},
        {"record_id": "poi-3", "poi_type": "PREVIOUS_DAY_HIGH"},  # NOT lifecycle-eligible
    ]
    events = [
        {"poi_record_id": "poi-1", "event_type": "POI_TERMINAL"},
        {"poi_record_id": "poi-2", "event_type": "POI_ACTIVATED"},
    ]
    count = compute_incomplete_terminal_lifecycle_count(poi_registry, events)
    assert count == 1  # only poi-2: eligible type, never terminated


def test_build_frequency_tables() -> None:
    events = [_event(bar_index=1, day="2026-06-01", week="2026-W23"), _event(bar_index=2, day="2026-06-01", week="2026-W23")]
    poi_registry = [
        {"availability_time_utc": "2026-06-01T00:00:00+00:00"},
        {"availability_time_utc": "2026-06-02T00:00:00+00:00"},
    ]
    freq = build_frequency_tables(events, poi_registry)
    assert freq["events_per_day"]["2026-06-01"] == 2
    assert freq["distinct_days_with_events"] == 1


_PROHIBITED_SUBSTRINGS = (
    "win_rate",
    "winrate",
    "profit_factor",
    "profitfactor",
    "expectancy",
    "r_multiple",
    "rmultiple",
    "average_r",
    "max_drawdown",
    "maxdrawdown",
    "drawdown",
    "consecutive_loss",
    "equity_curve",
    "equitycurve",
    "sharpe",
    "return_on_risk",
    "profitable",
)


def _flatten_keys_and_string_values(obj: object) -> list[str]:
    found: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            found.append(str(key))
            found.extend(_flatten_keys_and_string_values(value))
    elif isinstance(obj, list):
        for item in obj:
            found.extend(_flatten_keys_and_string_values(item))
    elif isinstance(obj, str):
        found.append(obj)
    return found


def test_report_contains_no_prohibited_metrics() -> None:
    """Protocol §12 hard rule, enforced in code as a dedicated test: no
    win-rate/profit-factor/expectancy/R-multiple/drawdown/Sharpe/equity-curve
    metric name may appear anywhere in a built report."""
    dev_m15 = _dev_series(80)
    events = [
        _event(bar_index=10, event_type="POI_ACTIVATED", poi_record_id="poi-1"),
        _event(bar_index=12, event_type="PERMISSION_ENTERED_ACTIONABLE", poi_record_id="poi-1"),
        _event(bar_index=20, event_type="POI_TERMINAL", poi_record_id="poi-1"),
        _event(bar_index=15, event_type="BTMM_VALIDATED", poi_record_id="poi-2", direction="BEARISH"),
    ]
    poi_registry = [
        {
            "record_id": "poi-1",
            "poi_idx": 0,
            "poi_type": "BUY_ORDER_BLOCK",
            "poi_direction": "BULLISH",
            "origin_timeframe": "M15",
            "effective_timeframe": "M15",
            "zone_top": "101",
            "zone_bottom": "99",
            "strength_tier": "STANDARD",
            "availability_time_utc": "2026-06-01T00:00:00+00:00",
            "first_seen_bar_index": 2,
        },
        {
            "record_id": "poi-2",
            "poi_idx": 1,
            "poi_type": "SELL_ORDER_BLOCK",
            "poi_direction": "BEARISH",
            "origin_timeframe": "H1",
            "effective_timeframe": "H1",
            "zone_top": "110",
            "zone_bottom": "108",
            "strength_tier": "STRONG",
            "availability_time_utc": "2026-06-01T01:00:00+00:00",
            "first_seen_bar_index": 4,
        },
    ]
    atr_series: list[Decimal | None] = [D("1")] * 80
    event_outcomes, event_exclusions = compute_event_outcomes(events, dev_m15, atr_series, {})
    poi_outcomes, poi_exclusions = compute_poi_outcomes(poi_registry, dev_m15, atr_series, {})
    report = build_report(
        events, poi_registry, event_outcomes, poi_outcomes, event_exclusions, poi_exclusions
    )

    # Serialize with a Decimal-tolerant default so nested Decimal cells (none
    # expected, but defensive) don't crash the scan.
    dumped = json.dumps(report, default=str).lower()
    for forbidden in _PROHIBITED_SUBSTRINGS:
        assert forbidden not in dumped, f"prohibited metric leaked into report: {forbidden!r}"
