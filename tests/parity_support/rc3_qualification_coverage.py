"""RC3 qualification type coverage: RAW -> QUALITY -> ARBITRATION -> CONTEXT -> MAPPED -> FRESH.

Test/validation tooling only. Per timeframe (unsealed FXCM segments) and core POI
type: raw detector candidates, candidates passing type quality, candidates
surviving same-origin arbitration, mapped P3 records (batch engine, incl. the
leg-origin OB gate and S/R locks) and records still fresh at the segment end.

    python -m tests.parity_support.rc3_qualification_coverage
"""

from __future__ import annotations

import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.leg_origin import ContextReason, structure_context_decisions
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.qualification import (
    CONTEXT_GATED_TYPES,
    QualificationReason,
    qualify_candidates,
)
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars

__all__ = ["coverage"]

_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_CORE = (
    "BUY_ORDER_BLOCK", "SELL_ORDER_BLOCK", "BUY_FAIR_VALUE_GAP", "SELL_FAIR_VALUE_GAP",
    "BUY_TO_SELL_CANDLE", "SELL_TO_BUY_CANDLE", "BASE_RALLY", "BASE_DROP",
    "BULLISH_PRESSURE_WICK", "BEARISH_PRESSURE_WICK", "BULLISH_ENGULFING",
    "BEARISH_ENGULFING", "HAMMER", "SHOOTING_STAR", "MORNING_STAR", "EVENING_STAR",
    "SUPPORT_ZONE", "RESISTANCE_ZONE",
)  # fmt: skip


def coverage(segment) -> dict[str, Counter[str]]:
    identity = ContentAddressedIdentityProvider()
    m = analyze_market_measurements(segment, _MCONFIG, identity)
    raw: list[Any] = [
        *detect_order_blocks(segment, _PCONFIG),
        *detect_fair_value_gaps(segment, _PCONFIG),
        *detect_reversal_candles(segment, _PCONFIG),
        *detect_bases(segment, _PCONFIG),
        *detect_pressure_wicks(segment, _PCONFIG),
        *detect_engulfing(segment, _PCONFIG),
        *detect_single_candle_reversals(segment, _PCONFIG),
        *detect_three_candle_stars(segment, _PCONFIG),
        *detect_reference_zones(m.support_resistance_zones, (), m.confirmed_swings),
    ]
    atr = compute_atr_series(segment, 14)
    _mapped, decisions = qualify_candidates(
        raw, {c.record_id: a for c, a in zip(segment, atr, strict=True)}, _PCONFIG
    )
    rejected = Counter(
        d.candidate.poi_type.value
        for d in decisions
        if d.reason is QualificationReason.QUALITY_REJECT
    )
    suppressed = Counter(
        d.candidate.poi_type.value
        for d in decisions
        if d.reason is QualificationReason.SAME_ORIGIN_SUPPRESSED
    )
    raw_counts = Counter(c.poi_type.value for c in raw)
    quality = raw_counts - rejected
    arbitration = quality - suppressed
    context = structure_context_decisions(
        [c for c in _mapped if c.poi_type in CONTEXT_GATED_TYPES],
        segment,
        m.confirmed_swings,
    )
    by_reason: dict[str, Counter[str]] = {
        r.value: Counter(d.candidate.poi_type.value for d in context if d.reason is r)
        for r in ContextReason
    }
    context_pass = arbitration - by_reason["CONTEXT_REJECT_COUNTER_TREND"] - by_reason[
        "CONTEXT_REJECT_NEUTRAL"
    ]
    pois = analyze_pois(
        (PoiTimeframeInput(segment[0].timeframe, segment, m),), _PCONFIG, identity
    )
    states = {s.poi_record_id: s for s in pois.current_poi_states}
    mapped = Counter(o.poi_type.value for o in pois.poi_observations)
    fresh = Counter(
        o.poi_type.value
        for o in pois.poi_observations
        if states[o.record_id].fresh_active
    )
    return {"raw": raw_counts, "quality": quality, "arbitration": arbitration,
            "context": context_pass, "mapped": mapped, "fresh": fresh,
            "suppressed": suppressed, **by_reason}  # fmt: skip


def main() -> int:  # pragma: no cover - manual measurement
    from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_qualification"
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    for stem, tf in (
        ("w1", Timeframe.W1), ("d1", Timeframe.D1), ("h4", Timeframe.H4),
        ("h1", Timeframe.H1), ("m15", Timeframe.M15), ("m5", Timeframe.M5),
    ):  # fmt: skip
        total: dict[str, Counter[str]] = {}
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        ):
            if len(seg) < 30:
                continue
            for k, v in coverage(seg).items():
                total[k] = total.get(k, Counter()) + v
        report[tf.value] = {
            t: {k: total.get(k, Counter())[t] for k in ("raw", "quality", "arbitration", "context", "mapped", "fresh", "suppressed", "MAPPED_TREND_ALIGNED", "MAPPED_REVERSAL_CONTEXT", "CONTEXT_REJECT_COUNTER_TREND", "CONTEXT_REJECT_NEUTRAL")}
            for t in _CORE
        }  # fmt: skip
        print(tf.value, json.dumps({t: [v["raw"], v["quality"], v["arbitration"], v["context"], v["mapped"], v["fresh"]] for t, v in report[tf.value].items()}), flush=True)  # fmt: skip
    (out / "type_coverage.json").write_text(json.dumps(report, indent=1), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
