"""RC3 all-type POI coverage matrix (engine + presentation model).

Test/validation tooling only. For each timeframe export (last unsealed
segment, i.e. the chart's live end) runs the real engine and the P7-Z
presentation model and reports, per core POI type:

* detected   - P3 observations of that type in the segment
* fresh      - still fresh at the segment's last bar (eligible to draw)
* displayed  - fresh POIs of that type that land in a drawn visual group
               (capacity 30, nearest first, after same-formation dominance)
* annotated  - displayed POIs whose group label names that type
* dominated  - fresh FVGs hidden by same-formation dominance (by design)

A displayed POI that is not annotated is an annotation-integrity failure.
Live TradingView counts are collected separately; this is the reference.
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
from tests.parity_support.p4_atomic_state_replay import CODE_BY_POI_TYPE
from tests.parity_support.p7z_zone_model import (
    PoiGeometry,
    apply_visual_dominance,
    build_visual_groups_fast,
    type_label,
)
from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

__all__ = ["coverage_for_segment"]

_CORE_CODES = range(1, 19)
_PERIOD = {
    Timeframe.W1: "W",
    Timeframe.D1: "D",
    Timeframe.H4: "240",
    Timeframe.H1: "60",
    Timeframe.M15: "15",
    Timeframe.M5: "5",
}


def _ms(dt) -> int:
    return int(dt.timestamp() * 1000)


def coverage_for_segment(segment, timeframe: Timeframe, capacity: int = 30) -> dict:
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(
        segment,
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01")),
        identity,
    )
    pois = analyze_pois(
        (PoiTimeframeInput(timeframe, segment, measurement),),
        PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        identity,
    )
    states = {s.poi_record_id: s for s in pois.current_poi_states}
    geometry: dict[int, PoiGeometry] = {}
    detected: Counter[int] = Counter()
    fresh: list[int] = []
    for i, o in enumerate(pois.poi_observations):
        code = CODE_BY_POI_TYPE.get(o.poi_type)
        if code is None or code not in _CORE_CODES:
            continue
        detected[code] += 1
        geometry[i] = PoiGeometry(
            i,
            code,
            1 if o.direction.value == "BULLISH" else -1,
            float(o.zone_top),
            float(o.zone_bottom),
            _ms(o.availability_time_utc),
            0,
            _ms(o.candidate_event_time_utc),
        )
        if states[o.record_id].fresh_active:
            fresh.append(i)
    close = float(segment[-1].close)
    _candidates, dominated = apply_visual_dominance(fresh, geometry)
    groups = build_visual_groups_fast(
        fresh, geometry, close, capacity, _PERIOD[timeframe]
    )
    displayed: Counter[int] = Counter()
    annotated: Counter[int] = Counter()
    for g in groups:
        for m in g["members"]:
            code = geometry[m].poi_type
            displayed[code] += 1
            if type_label(code) in g["label"]:
                annotated[code] += 1
    fresh_by = Counter(geometry[i].poi_type for i in fresh)
    dominated_by = Counter(geometry[i].poi_type for i in dominated)
    return {
        type_label(code): {
            "detected": detected[code],
            "fresh": fresh_by[code],
            "displayed": displayed[code],
            "annotated": annotated[code],
            "dominated": dominated_by[code],
            "annotation_failures": displayed[code] - annotated[code],
        }
        for code in _CORE_CODES
    }


def main() -> int:  # pragma: no cover - manual measurement
    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_poi_coverage"
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
        segments = load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        )
        report[tf.value] = coverage_for_segment(segments[-1], tf)
        print(tf.value, json.dumps(report[tf.value]), flush=True)
    (out / "type_coverage.json").write_text(
        json.dumps(report, indent=1), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
