"""DOJI: the 19th canonical student POI type.

Author decision, 2026-09-21. Thresholds were fixed long before this detector
existed and are not re-tuned here: STANDARD is body efficiency <= 0.10, STRONG
<= 0.05, both already on ``PoiConfiguration`` and already used by the RC3 Doji
suppression rule. The efficiency itself comes from the shared
``measurements.candle_metrics.body_efficiency`` -- the formula is not
duplicated.

DIRECTION IS STRUCTURAL, NEVER COLOUR
-------------------------------------
A Doji has almost no body by definition, so its close relative to its open says
nothing about which side the market defended. Direction therefore comes from
the frozen confirmed swings: a Doji whose candle is a swing LOW pivot defends
the low side and is bullish; a swing HIGH pivot makes it bearish.

EXACTLY ONE DOJI PER CANDLE. ``_formation_key`` is
``(poi_type, source_candle_record_ids)``, so emitting both directions for one
candle would produce two candidates with the SAME identity -- the second would
silently overwrite the first in the gate's decision map and in the ledger.
Resolving direction here keeps identity unique by construction.

Ambiguity resolves the way the author specified: a candle that is a pivot of
both a swing high and a swing low has no defended side, so it is not promoted.
A candle that is neither is mid-leg texture and is not promoted either -- the
structural-origin gate would refuse it anyway, and refusing it here keeps the
raw population honest.

Being a confirmed swing pivot is necessary, not sufficient. The structural-role
doctrine still decides whether that swing is one the walk actually uses.

ZONE
----
The established single-candle convention, unchanged: the zone is the wick on
the side the pattern defends.

* bullish: ``min(open, close)`` down to ``low`` -- the lower wick
* bearish: ``high`` down to ``max(open, close)`` -- the upper wick

That is exactly what HAMMER / BULLISH PRESSURE WICK and SHOOTING STAR /
BEARISH PRESSURE WICK already use. No ATR padding, no pip buffer, no new
tolerance and no wick-share requirement of its own.

AVAILABILITY
------------
A Doji is a single candle, so it is complete at its own close and available at
its own ``availability_time_utc`` -- the same as every other single-candle
family. The structural-origin gate then delays promotion to the first causal
prefix that gives it a role, through the canonical provenance replay.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime
from decimal import Decimal
from typing import Any, NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.measurements.candle_metrics import body_efficiency, total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType

__all__ = ["DojiCandidate", "detect_dojis", "prefix_pivot_sides"]

_ZERO = Decimal("0")


class DojiCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    strength_tier: PoiStrengthTier
    source_candle_record_ids: tuple[UUID, ...]
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime


def detect_dojis(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
    confirmed_swings: Iterable[Any] = (),
    pivot_sides: dict[UUID, PoiDirection] | None = None,
) -> tuple[DojiCandidate, ...]:
    """Raw Doji geometry, with direction taken from the frozen confirmed swings.

    At most one candidate per candle: see the module docstring on identity.
    """
    if pivot_sides is None:
        # Live/incremental: the current swing set IS this prefix's truth, and
        # the append-only frontier makes the first emission permanent.
        low_pivots: set[UUID] = set()
        high_pivots: set[UUID] = set()
        for swing in confirmed_swings:
            target = (
                high_pivots if swing.swing_type == SwingType.SWING_HIGH else low_pivots
            )
            target.update(swing.pivot_candle_record_ids)
        pivot_sides = {}
        for candle_id in low_pivots | high_pivots:
            if candle_id in low_pivots and candle_id in high_pivots:
                continue
            pivot_sides[candle_id] = (
                PoiDirection.BULLISH
                if candle_id in low_pivots
                else PoiDirection.BEARISH
            )

    results: list[DojiCandidate] = []
    for candle in candles:
        if total_range(candle) == _ZERO:
            continue
        efficiency = body_efficiency(candle)
        if efficiency > configuration.doji_body_efficiency_standard:
            continue
        strong = efficiency <= configuration.doji_body_efficiency_strong
        tier = PoiStrengthTier.STRONG if strong else PoiStrengthTier.STANDARD
        body_low = min(candle.open, candle.close)
        body_high = max(candle.open, candle.close)

        resolved = pivot_sides.get(candle.record_id)
        if resolved is None:
            # never a pivot (mid-leg texture), or no defended side -> raw only
            continue
        if resolved is PoiDirection.BULLISH:
            direction, zone_top, zone_bottom = (
                PoiDirection.BULLISH,
                body_low,
                candle.low,
            )
        else:
            direction, zone_top, zone_bottom = (
                PoiDirection.BEARISH,
                candle.high,
                body_high,
            )
        # A doji whose defended wick is empty has no reaction area on that side.
        if zone_top <= zone_bottom:
            continue
        results.append(
            DojiCandidate(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                poi_type=PoiType.DOJI,
                direction=direction,
                zone_top=zone_top,
                zone_bottom=zone_bottom,
                strength_tier=tier,
                source_candle_record_ids=(candle.record_id,),
                candidate_event_time_utc=candle.event_time_utc,
                confirmation_time_utc=candle.availability_time_utc,
                availability_time_utc=candle.availability_time_utc,
            )
        )
    return tuple(results)


def prefix_pivot_sides(
    candles: Sequence[NormalizedCandle],
    measurement_configuration: Any,
    *,
    ring_size: int,
) -> dict[UUID, PoiDirection]:
    """The side each candle defended when it FIRST became a structural pivot.

    Swing supersession means "is a pivot of a confirmed swing" is not monotone:
    a candle can be a confirmed pivot at prefix N and absent from the final
    swing set. The append-only frontier remembers the formation it emitted at
    prefix N; a batch run that consults only the final swings drops it. That is
    the same asymmetry ORDER BLOCKS already resolve by prefix replay, and it is
    resolved the same way here.

    So the question is "WAS this candle a valid pivot at the causal prefix
    where it qualified?", never "is it still one now". The answer is recorded
    the first time it becomes true and is never revised:

    * one side only -> that side, permanently;
    * both sides at that same prefix -> no defended side, permanently refused
      (recording the refusal is what stops a later prefix from promoting it).

    ``ring_size`` mirrors the incremental detector's bounded look-back, so the
    two paths see the same candles at the same prefixes. Without it batch would
    find pivots the frontier's ring had already dropped.
    """
    from btmm_ai_scanner.poi.leg_origin import iter_prefix_swing_candidates

    decided: dict[UUID, PoiDirection | None] = {}
    for index, swings in iter_prefix_swing_candidates(
        candles, measurement_configuration
    ):
        visible = {
            c.record_id for c in candles[max(0, index - ring_size + 1) : index + 1]
        }
        low_side: set[UUID] = set()
        high_side: set[UUID] = set()
        for swing in swings:
            target = high_side if swing.swing_type == SwingType.SWING_HIGH else low_side
            target.update(c for c in swing.pivot_candle_record_ids if c in visible)
        for candle_id in low_side | high_side:
            if candle_id in decided:
                continue
            both = candle_id in low_side and candle_id in high_side
            decided[candle_id] = (
                None
                if both
                else (
                    PoiDirection.BULLISH
                    if candle_id in low_side
                    else PoiDirection.BEARISH
                )
            )
    return {k: v for k, v in decided.items() if v is not None}
