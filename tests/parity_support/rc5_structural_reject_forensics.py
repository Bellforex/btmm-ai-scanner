"""RC5 structural-origin gate: WHY each reversal candidate was refused.

Counts alone cannot tell you whether an 88% reduction is sensible. This tool
reports the reason, and then shows real examples from each family -- survivors,
obvious rejects and questionable rejects together, so the sample cannot be
cherry-picked.

``structural_role_of`` has exactly two failure exits, so these two reasons are
the implementation's canonical vocabulary, not a reporting invention:

``NOT_A_PIVOT_ON_ITS_OWN_SIDE``
    No source candle of the pattern is a pivot candle of a confirmed swing on
    the side the pattern claims to defend. A bearish reversal that is not at a
    swing high is not at a top at all. (A pattern sitting on a swing of the
    WRONG side lands here too, because the resolver only ever consults the
    matching-side pivot map.)

``SWING_NEVER_USED_BY_THE_WALK``
    It IS a confirmed swing extreme on the right side, but the structure walk
    never named it a leg origin, never broke it, and is not protecting it. Under
    the accepted role set that is leg texture. These are the cases worth
    auditing, so the tool prints their forward behaviour: whether a FAST
    displacement in the pattern's own direction followed, and whether price
    later traded back through the pivot -- i.e. whether a real departure began
    there, and whether it held.
"""

from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DisplacementClassification
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.leg_origin import _gate, structural_role_of
from tests.parity_support.rc5_structural_origin_impact import _FAMILIES
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_TICK = Decimal("0.01")
_FORWARD_BARS = 40
_STRONG = frozenset(
    {DisplacementClassification.FAST, DisplacementClassification.VERY_FAST}
)

NOT_A_PIVOT = "NOT_A_PIVOT_ON_ITS_OWN_SIDE"
SWING_UNUSED = "SWING_NEVER_USED_BY_THE_WALK"


def _reason(candidate: Any, context: Any) -> str | None:
    """``None`` when the candidate holds a role; otherwise which exit it took."""
    if structural_role_of(candidate, context) is not None:
        return None
    pivots = (
        context.swing_low_candle_ids
        if candidate.direction is PoiDirection.BULLISH
        else context.swing_high_candle_ids
    )
    on_a_pivot = any(c in pivots for c in candidate.source_candle_record_ids)
    return SWING_UNUSED if on_a_pivot else NOT_A_PIVOT


def _forward(candidate: Any, bar: int, candles: Any, displacement: dict[int, Any]):
    """Did a real departure begin here, and did it hold? Uses only the frozen
    displacement primitive -- no new threshold."""
    bearish = candidate.direction is PoiDirection.BEARISH
    pivot = Decimal(candidate.zone_top if bearish else candidate.zone_bottom)
    window = candles[bar + 1 : bar + 1 + _FORWARD_BARS]
    if not window:
        return None
    strong_same_way = any(
        o.classification in _STRONG
        and (o.direction.value == ("BEARISH" if bearish else "BULLISH"))
        for i, o in displacement.items()
        if bar < i <= bar + _FORWARD_BARS
    )
    traded_back = (
        max(c.high for c in window) > pivot
        if bearish
        else min(c.low for c in window) < pivot
    )
    excursion = (
        pivot - min(c.low for c in window)
        if bearish
        else max(c.high for c in window) - pivot
    )
    return {
        "impulse_started": strong_same_way,
        "pivot_traded_through": traded_back,
        "excursion": excursion,
    }


def run(path: Path, timeframe: Timeframe, *, samples: int = 2) -> None:
    candles = load_v1a_csv(path, timeframe)
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(
        candles, MarketMeasurementConfiguration(minimum_price_tick=_TICK), identity
    )
    swings = tuple(measurement.confirmed_swings)
    _g, _walk, _d, _t, context = _gate((), candles, swings, ())
    bar_of = {c.record_id: i for i, c in enumerate(candles)}
    displacement = {
        bar_of[o.candle_record_id]: o for o in measurement.displacement_observations
    }

    def pois(rc5: bool):
        return analyze_pois(
            (PoiTimeframeInput(timeframe, candles, measurement),),
            PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=rc5),
            ContentAddressedIdentityProvider(),
        ).poi_observations

    rc4 = list(pois(False))
    kept = {(o.poi_type, o.source_candle_record_ids) for o in pois(True)}

    print(f"\n{'=' * 78}\n{timeframe.value}  ({len(candles)} bars, {path.name})")
    reasons: Counter[str] = Counter()
    per_family: dict[str, dict[str, list[Any]]] = {}
    for observation in rc4:
        family = next(
            (n for n, members in _FAMILIES if observation.poi_type in members), None
        )
        if family is None:
            continue
        key = (observation.poi_type, observation.source_candle_record_ids)
        bucket = per_family.setdefault(
            family, {"kept": [], NOT_A_PIVOT: [], SWING_UNUSED: []}
        )
        if key in kept:
            bucket["kept"].append(observation)
            continue
        reason = _reason(observation, context) or NOT_A_PIVOT
        reasons[f"{family}::{reason}"] += 1
        bucket[reason].append(observation)

    print("\nREJECT REASONS")
    for name, _members in _FAMILIES:
        rows = [(k, v) for k, v in reasons.items() if k.startswith(f"{name}::")]
        if not rows:
            continue
        total = sum(v for _, v in rows)
        detail = "  ".join(f"{k.split('::')[1]}={v}" for k, v in sorted(rows))
        print(f"  {name:<18} refused={total:<5} {detail}")

    print("\nSAMPLES (survivors / obvious rejects / questionable rejects)")
    for name, _members in _FAMILIES:
        bucket = per_family.get(name)
        if not bucket:
            continue
        print(f"\n  --- {name}")
        for observation in bucket["kept"][:samples]:
            bar = bar_of[observation.source_candle_record_ids[0]]
            role = structural_role_of(observation, context)
            print(
                f"    SURVIVOR  bar {bar:<5} {observation.poi_type.value:<22}"
                f" {observation.candidate_event_time_utc:%Y-%m-%d %H:%M}"
                f"  role={role.role.value if role else '?'}"
            )
        for observation in bucket[NOT_A_PIVOT][:samples]:
            bar = bar_of[observation.source_candle_record_ids[0]]
            print(
                f"    REJECT    bar {bar:<5} {observation.poi_type.value:<22}"
                f" {observation.candidate_event_time_utc:%Y-%m-%d %H:%M}"
                f"  {NOT_A_PIVOT}"
            )
        for observation in bucket[SWING_UNUSED][:samples]:
            bar = bar_of[observation.source_candle_record_ids[0]]
            forward = _forward(observation, bar, candles, displacement)
            print(
                f"    AUDIT     bar {bar:<5} {observation.poi_type.value:<22}"
                f" {observation.candidate_event_time_utc:%Y-%m-%d %H:%M}"
                f"  {SWING_UNUSED}  forward={forward}"
            )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ohlc", type=Path, required=True)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--samples", type=int, default=2)
    args = parser.parse_args()
    run(args.ohlc, Timeframe(args.timeframe), samples=args.samples)


if __name__ == "__main__":
    main()


__all__ = ["NOT_A_PIVOT", "SWING_UNUSED", "run"]
