from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType


class EngulfingCandidate(NamedTuple):
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


def detect_engulfing(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[EngulfingCandidate, ...]:
    if len(candles) < 2:
        return ()

    results: list[EngulfingCandidate] = []
    for index in range(len(candles) - 1):
        engulfed = candles[index]
        engulfing = candles[index + 1]

        engulfed_range = total_range(engulfed)
        if engulfed_range == 0:
            continue
        ratio = total_range(engulfing) / engulfed_range
        if ratio < configuration.order_block_size_ratio_standard:
            continue

        engulfed_bearish = engulfed.close < engulfed.open
        engulfed_bullish = engulfed.close > engulfed.open
        engulfing_bullish = engulfing.close > engulfing.open
        engulfing_bearish = engulfing.close < engulfing.open

        if engulfed_bearish and engulfing_bullish:
            poi_type = PoiType.BULLISH_ENGULFING
            direction = PoiDirection.BULLISH
        elif engulfed_bullish and engulfing_bearish:
            poi_type = PoiType.BEARISH_ENGULFING
            direction = PoiDirection.BEARISH
        else:
            continue

        strength_tier = (
            PoiStrengthTier.STRONG
            if ratio >= configuration.order_block_size_ratio_strong
            else PoiStrengthTier.STANDARD
        )

        results.append(
            EngulfingCandidate(
                symbol=engulfed.symbol,
                timeframe=engulfed.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=engulfed.high,
                zone_bottom=engulfed.low,
                strength_tier=strength_tier,
                source_candle_record_ids=(engulfed.record_id, engulfing.record_id),
                candidate_event_time_utc=engulfed.event_time_utc,
                confirmation_time_utc=engulfing.availability_time_utc,
                availability_time_utc=engulfing.availability_time_utc,
            )
        )

    return tuple(results)
