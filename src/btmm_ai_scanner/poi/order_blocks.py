from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType


class OrderBlockCandidate(NamedTuple):
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


def detect_order_blocks(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[OrderBlockCandidate, ...]:
    if len(candles) < 2:
        return ()

    results: list[OrderBlockCandidate] = []
    for index in range(len(candles) - 1):
        origin = candles[index]
        displacement = candles[index + 1]

        origin_range = total_range(origin)
        if origin_range == 0:
            continue
        ratio = total_range(displacement) / origin_range
        if ratio < configuration.order_block_size_ratio_standard:
            continue

        origin_bearish = origin.close < origin.open
        origin_bullish = origin.close > origin.open
        displacement_bullish = displacement.close > displacement.open
        displacement_bearish = displacement.close < displacement.open

        if origin_bearish and displacement_bullish and displacement.close > origin.high:
            poi_type = PoiType.BUY_ORDER_BLOCK
            direction = PoiDirection.BULLISH
        elif (
            origin_bullish and displacement_bearish and displacement.close < origin.low
        ):
            poi_type = PoiType.SELL_ORDER_BLOCK
            direction = PoiDirection.BEARISH
        else:
            continue

        strength_tier = (
            PoiStrengthTier.STRONG
            if ratio >= configuration.order_block_size_ratio_strong
            else PoiStrengthTier.STANDARD
        )

        results.append(
            OrderBlockCandidate(
                symbol=origin.symbol,
                timeframe=origin.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=origin.high,
                zone_bottom=origin.low,
                strength_tier=strength_tier,
                source_candle_record_ids=(origin.record_id, displacement.record_id),
                candidate_event_time_utc=origin.event_time_utc,
                confirmation_time_utc=displacement.availability_time_utc,
                availability_time_utc=displacement.availability_time_utc,
            )
        )

    return tuple(results)
