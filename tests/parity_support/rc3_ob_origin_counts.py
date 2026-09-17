"""Before/after P3 type counts for the RC3 ORDER BLOCK movement-origin revision.

Test/validation tooling only. Runs the real engine (measurement analyzer ->
POI analyzer) over each unsealed segment of the same-session FXCM exports and
counts, per timeframe:

* raw OB formations (= every OB before the revision; the frozen detector);
* ORDER BLOCK records after the revision and their confirmation delay in bars
  (availability bar - displacement bar);
* engulfing records (unchanged by the revision) and how many were promoted;
* lookahead violations: an ORDER BLOCK whose availability precedes the close
  of its anchoring swing's confirmation candle, or its displacement close.
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
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiTerminalReason, PoiType
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

_OB = (PoiType.BUY_ORDER_BLOCK, PoiType.SELL_ORDER_BLOCK)
_ENG = (PoiType.BULLISH_ENGULFING, PoiType.BEARISH_ENGULFING)


def count_timeframe(
    export: Path, timeframe: Timeframe, scratch: Path
) -> dict[str, Any]:
    poi_config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    measurement_config = MarketMeasurementConfiguration(
        minimum_price_tick=Decimal("0.01")
    )
    before: Counter[str] = Counter()
    after: Counter[str] = Counter()
    delays: list[int] = []
    promoted = 0
    mitigated_before_promotion = 0
    lookahead = 0
    for segment in load_unsealed_segments(export, timeframe, scratch):
        identity = ContentAddressedIdentityProvider()
        measurement = analyze_market_measurements(segment, measurement_config, identity)
        pois = analyze_pois(
            (PoiTimeframeInput(timeframe, segment, measurement),),
            poi_config,
            identity,
        )
        bar = {c.availability_time_utc: i for i, c in enumerate(segment)}
        index = {c.record_id: i for i, c in enumerate(segment)}
        for formation in detect_order_blocks(segment, poi_config):
            before[formation.poi_type.value] += 1
        states = {s.poi_record_id: s for s in pois.current_poi_states}
        ob_keys = set()
        for o in pois.poi_observations:
            if o.poi_type in _OB:
                after[o.poi_type.value] += 1
                displacement = index[o.source_candle_record_ids[1]]
                delay = bar[o.availability_time_utc] - displacement
                delays.append(delay)
                if delay < 0:
                    lookahead += 1
                ob_keys.add(o.source_candle_record_ids)
            elif o.poi_type in _ENG:
                after[o.poi_type.value] += 1
                reason = states[o.record_id].terminal_reason
                if reason is PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK:
                    promoted += 1
        for o in pois.poi_observations:
            if o.poi_type in _ENG and o.source_candle_record_ids in ob_keys:
                if states[o.record_id].terminal_reason is PoiTerminalReason.MITIGATED:
                    mitigated_before_promotion += 1
    return {
        "before": dict(before),
        "after": dict(after),
        "reclassified_BUY_OB_to_BULLISH_ENGULFING": before["BUY_ORDER_BLOCK"]
        - after["BUY_ORDER_BLOCK"],
        "reclassified_SELL_OB_to_BEARISH_ENGULFING": before["SELL_ORDER_BLOCK"]
        - after["SELL_ORDER_BLOCK"],
        "confirmation_delay_bars": dict(sorted(Counter(delays).items())),
        "mean_delay_bars": round(sum(delays) / len(delays), 3) if delays else None,
        "max_delay_bars": max(delays) if delays else None,
        "engulfings_promoted": promoted,
        "engulfings_mitigated_before_promotion": mitigated_before_promotion,
        "lookahead_violations": lookahead,
    }


def main() -> int:  # pragma: no cover - manual measurement
    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_ob_origin"
    out.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {}
    for stem, tf in (
        ("w1", Timeframe.W1),
        ("d1", Timeframe.D1),
        ("h4", Timeframe.H4),
        ("h1", Timeframe.H1),
        ("m15", Timeframe.M15),
        ("m5", Timeframe.M5),
    ):
        report[tf.value] = count_timeframe(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        )
        print(tf.value, report[tf.value], flush=True)
    (out / "type_counts.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
