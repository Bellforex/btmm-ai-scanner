from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import (
    body_efficiency,
    lower_wick,
    total_range,
    upper_wick,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType


class SingleCandleReversalCandidate(NamedTuple):
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


def detect_single_candle_reversals(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[SingleCandleReversalCandidate, ...]:
    results: list[SingleCandleReversalCandidate] = []

    for candle in candles:
        candle_range = total_range(candle)
        if candle_range == 0:
            continue

        lw_share = lower_wick(candle) / candle_range
        uw_share = upper_wick(candle) / candle_range
        efficiency = body_efficiency(candle)

        hammer_ok = (
            lw_share >= configuration.hammer_shooting_star_wick_share_standard
            and efficiency
            <= configuration.hammer_shooting_star_body_efficiency_standard
            and uw_share <= configuration.hammer_shooting_star_opposite_wick_standard
        )
        star_ok = (
            uw_share >= configuration.hammer_shooting_star_wick_share_standard
            and efficiency
            <= configuration.hammer_shooting_star_body_efficiency_standard
            and lw_share <= configuration.hammer_shooting_star_opposite_wick_standard
        )

        if hammer_ok:
            poi_type = PoiType.HAMMER
            direction = PoiDirection.BULLISH
            zone_top = min(candle.open, candle.close)
            zone_bottom = candle.low
            strong = (
                lw_share >= configuration.hammer_shooting_star_wick_share_strong
                and efficiency
                <= configuration.hammer_shooting_star_body_efficiency_strong
                and uw_share <= configuration.hammer_shooting_star_opposite_wick_strong
            )
        elif star_ok:
            poi_type = PoiType.SHOOTING_STAR
            direction = PoiDirection.BEARISH
            zone_top = candle.high
            zone_bottom = max(candle.open, candle.close)
            strong = (
                uw_share >= configuration.hammer_shooting_star_wick_share_strong
                and efficiency
                <= configuration.hammer_shooting_star_body_efficiency_strong
                and lw_share <= configuration.hammer_shooting_star_opposite_wick_strong
            )
        else:
            continue

        results.append(
            SingleCandleReversalCandidate(
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=zone_top,
                zone_bottom=zone_bottom,
                strength_tier=(
                    PoiStrengthTier.STRONG if strong else PoiStrengthTier.STANDARD
                ),
                source_candle_record_ids=(candle.record_id,),
                candidate_event_time_utc=candle.event_time_utc,
                confirmation_time_utc=candle.availability_time_utc,
                availability_time_utc=candle.availability_time_utc,
            )
        )

    return tuple(results)
