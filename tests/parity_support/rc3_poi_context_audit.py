"""RC3 market-context audit of mapped POIs (diagnostic, not a mapping gate).

Test/validation tooling only. For every mapped core POI it records the context
known AT ITS AVAILABILITY (no later bar):

* structure direction and ``leg_id`` = the latest frozen P2 break (BOS / CHOCH)
  available by then, and the leg's direction;
* role: TREND_ALIGNED (POI direction == leg direction), COUNTER_TREND
  (opposite), STRUCTURAL_NEUTRAL (no break yet);
* retracement location of the zone midpoint inside the latest confirmed swing
  range [last SWING_LOW, last SWING_HIGH] available by then: depth from the
  leg extreme in the POI's direction (bullish: from the high down), bucketed
  <50 / 50-61.8 / 61.8-79 / 79-100 / outside;
* confluence: overlap with a SUPPORT/RESISTANCE zone or EQUAL-level cluster
  available by then; a trendline available by then whose projection at the POI
  source bar lies within the zone +/- 0.10 x anchor ATR.

Swings / transitions come from the batch engine over the segment and are
filtered by their own availability; the confirmed-history lock means the mapped
POIs themselves never change, while a structure record superseded later could
still colour a label here (disclosed in the audit document).

    python -m tests.parity_support.rc3_poi_context_audit
"""

from __future__ import annotations

import bisect
import json
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import StructureDirection
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import run_structure_walk

__all__ = ["context_rows"]

_CORE = frozenset(PoiType) - {
    t for t in PoiType if t.value.startswith(("CURRENT_", "PREVIOUS_", "EQUAL_"))
}
_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _bucket(depth: float | None) -> str:
    if depth is None:
        return "NO_RANGE"
    if depth < 0 or depth > 1:
        return "OUTSIDE"
    if depth < 0.5:
        return "<50"
    if depth < 0.618:
        return "50-61.8"
    if depth < 0.79:
        return "61.8-79"
    return "79-100"


def context_rows(segment, timeframe: Timeframe) -> list[dict[str, Any]]:
    identity = ContentAddressedIdentityProvider()
    m = analyze_market_measurements(segment, _MCONFIG, identity)
    pois = analyze_pois((PoiTimeframeInput(timeframe, segment, m),), _PCONFIG, identity)
    swings = m.confirmed_swings
    walk = run_structure_walk(
        segment, swings, detect_swing_relationships(swings, StructureConfiguration())
    )
    breaks = sorted(walk.transitions, key=lambda t: t.availability_time_utc)
    break_times = [t.availability_time_utc for t in breaks]
    bar_index = {c.record_id: i for i, c in enumerate(segment)}
    rows: list[dict[str, Any]] = []
    for o in pois.poi_observations:
        if o.poi_type not in _CORE:
            continue
        t = o.availability_time_utc
        k = bisect.bisect_right(break_times, t)
        leg = breaks[k - 1] if k else None
        bull = o.direction is PoiDirection.BULLISH
        if leg is None:
            role = "STRUCTURAL_NEUTRAL"
        else:
            leg_bull = leg.direction_after is StructureDirection.BULLISH
            role = "TREND_ALIGNED" if leg_bull == bull else "COUNTER_TREND"
        known = [s for s in swings if s.meaningful_confirmation_time_utc <= t]
        highs = [s for s in known if s.swing_type is SwingType.SWING_HIGH]
        lows = [s for s in known if s.swing_type is SwingType.SWING_LOW]
        depth = None
        if highs and lows:
            hi, lo = highs[-1].pivot_price, lows[-1].pivot_price
            if hi > lo:
                mid = (o.zone_top + o.zone_bottom) / 2
                depth = float(
                    (hi - mid) / (hi - lo) if bull else (mid - lo) / (hi - lo)
                )
        sr = any(
            z.availability_time_utc <= t
            and z.zone_bottom <= o.zone_top
            and o.zone_bottom <= z.zone_top
            for z in m.support_resistance_zones
        ) or any(
            p.poi_type in (PoiType.SUPPORT_ZONE, PoiType.RESISTANCE_ZONE)
            and p.record_id != o.record_id
            and p.availability_time_utc <= t
            and p.zone_bottom <= o.zone_top
            and o.zone_bottom <= p.zone_top
            for p in pois.poi_observations
        )
        eq = any(
            c.availability_time_utc <= t
            and c.zone_bottom <= o.zone_top
            and o.zone_bottom <= c.zone_top
            for c in m.equal_level_clusters
        )
        src = (
            bar_index.get(o.source_candle_record_ids[0])
            if o.source_candle_record_ids
            else None
        )
        tl = False
        if src is not None:
            for line in m.trendlines:
                if line.availability_time_utc > t:
                    continue
                price = line.anchor_1_price + line.raw_slope * (
                    src - line.anchor_1_bar_index
                )
                tol = Decimal("0.10") * line.anchor_reference_atr
                if o.zone_bottom - tol <= price <= o.zone_top + tol:
                    tl = True
                    break
        rows.append(
            {
                "timeframe": timeframe.value,
                "type": o.poi_type.value,
                "direction": o.direction.value,
                "availability": t.isoformat(),
                "leg_id": leg.event_time_utc.isoformat() if leg else None,
                "leg_type": leg.transition_type.value if leg else None,
                "role": role,
                "retracement_bucket": _bucket(depth),
                "sr_confluence": sr,
                "equal_level_confluence": eq,
                "trendline_confluence": tl,
            }
        )
    return rows


def main() -> int:  # pragma: no cover - manual measurement
    from tests.parity_support.rc3_poi_overlap_audit import load_unsealed_segments

    repo = Path(__file__).resolve().parents[2]
    base = repo / "artifacts" / "rc3_aligned"
    out = repo / "artifacts" / "rc3_poi_context"
    out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for stem, tf in (
        ("m15", Timeframe.M15),
        ("h1", Timeframe.H1),
        ("h4", Timeframe.H4),
    ):
        for seg in load_unsealed_segments(
            base / f"ohlc_{stem}.csv", tf, out / "_n" / f"{stem}.csv"
        ):
            if len(seg) >= 60:
                rows.extend(context_rows(seg, tf))
    summary: dict[str, Any] = {}
    for tf in ("M15", "H1", "H4"):
        sub = [r for r in rows if r["timeframe"] == tf]
        by_type: dict[str, Counter[str]] = defaultdict(Counter)
        for r in sub:
            by_type[r["type"]][r["role"]] += 1
        summary[tf] = {
            "mapped": len(sub),
            "role": dict(Counter(r["role"] for r in sub)),
            "retracement": dict(Counter(r["retracement_bucket"] for r in sub)),
            "sr_confluence": sum(r["sr_confluence"] for r in sub),
            "equal_level_confluence": sum(r["equal_level_confluence"] for r in sub),
            "trendline_confluence": sum(r["trendline_confluence"] for r in sub),
            "by_type_role": {k: dict(v) for k, v in sorted(by_type.items())},
        }
        print(
            tf,
            json.dumps({k: v for k, v in summary[tf].items() if k != "by_type_role"}),
        )
    (out / "context_summary.json").write_text(json.dumps(summary, indent=1), "utf-8")
    (out / "context_rows.json").write_text(json.dumps(rows), "utf-8")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
