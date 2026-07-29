from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


class FairValueGapCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    source_candle_record_ids: tuple[UUID, ...]
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime


def detect_fair_value_gaps(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[FairValueGapCandidate, ...]:
    del configuration
    if len(candles) < 3:
        return ()

    results: list[FairValueGapCandidate] = []
    for index in range(len(candles) - 2):
        first, _second, third = (
            candles[index],
            candles[index + 1],
            candles[index + 2],
        )

        if third.low > first.high:
            poi_type = PoiType.BUY_FAIR_VALUE_GAP
            direction = PoiDirection.BULLISH
            zone_top = third.low
            zone_bottom = first.high
        elif third.high < first.low:
            poi_type = PoiType.SELL_FAIR_VALUE_GAP
            direction = PoiDirection.BEARISH
            zone_top = first.low
            zone_bottom = third.high
        else:
            continue

        results.append(
            FairValueGapCandidate(
                symbol=first.symbol,
                timeframe=first.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=zone_top,
                zone_bottom=zone_bottom,
                source_candle_record_ids=(
                    first.record_id,
                    _second.record_id,
                    third.record_id,
                ),
                candidate_event_time_utc=first.event_time_utc,
                confirmation_time_utc=third.availability_time_utc,
                availability_time_utc=third.availability_time_utc,
            )
        )

    return tuple(results)
