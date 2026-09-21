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

from collections.abc import Iterable
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

__all__ = ["DojiCandidate", "detect_dojis"]

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
) -> tuple[DojiCandidate, ...]:
    """Raw Doji geometry, with direction taken from the frozen confirmed swings.

    At most one candidate per candle: see the module docstring on identity.
    """
    low_pivots: set[UUID] = set()
    high_pivots: set[UUID] = set()
    for swing in confirmed_swings:
        target = high_pivots if swing.swing_type == SwingType.SWING_HIGH else low_pivots
        target.update(swing.pivot_candle_record_ids)

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

        low_side = candle.record_id in low_pivots
        high_side = candle.record_id in high_pivots
        if low_side == high_side:
            # neither (mid-leg texture) or both (no defended side) -> raw only
            continue
        if low_side:
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
