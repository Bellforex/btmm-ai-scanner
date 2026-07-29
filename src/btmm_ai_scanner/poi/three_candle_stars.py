from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import body_efficiency, total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType

_TWO = Decimal("2")


class ThreeCandleStarCandidate(NamedTuple):
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


def detect_three_candle_stars(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[ThreeCandleStarCandidate, ...]:
    if len(candles) < 3:
        return ()

    results: list[ThreeCandleStarCandidate] = []
    for index in range(len(candles) - 2):
        first, middle, third = (
            candles[index],
            candles[index + 1],
            candles[index + 2],
        )

        if total_range(middle) == 0:
            continue
        middle_efficiency = body_efficiency(middle)
        if middle_efficiency > configuration.doji_body_efficiency_standard:
            continue

        first_bearish = first.close < first.open
        first_bullish = first.close > first.open
        third_bullish = third.close > third.open
        third_bearish = third.close < third.open
        first_midpoint = (first.high + first.low) / _TWO

        if first_bearish and third_bullish and third.close > first_midpoint:
            poi_type = PoiType.MORNING_STAR
            direction = PoiDirection.BULLISH
        elif first_bullish and third_bearish and third.close < first_midpoint:
            poi_type = PoiType.EVENING_STAR
            direction = PoiDirection.BEARISH
        else:
            continue

        strength_tier = (
            PoiStrengthTier.STRONG
            if middle_efficiency <= configuration.doji_body_efficiency_strong
            else PoiStrengthTier.STANDARD
        )

        results.append(
            ThreeCandleStarCandidate(
                symbol=first.symbol,
                timeframe=first.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=middle.high,
                zone_bottom=middle.low,
                strength_tier=strength_tier,
                source_candle_record_ids=(
                    first.record_id,
                    middle.record_id,
                    third.record_id,
                ),
                candidate_event_time_utc=first.event_time_utc,
                confirmation_time_utc=third.availability_time_utc,
                availability_time_utc=third.availability_time_utc,
            )
        )

    return tuple(results)
