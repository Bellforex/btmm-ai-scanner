from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import (
    bearish_close_position,
    body_efficiency,
    bullish_close_position,
    total_range,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType

_TWO = Decimal("2")
_LOOKBACK = 3
_CONFIRMATION_WINDOW = 3


class ReversalCandleCandidate(NamedTuple):
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


def detect_reversal_candles(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[ReversalCandleCandidate, ...]:
    n = len(candles)
    if n < _LOOKBACK + 1:
        return ()

    results: list[ReversalCandleCandidate] = []
    for index in range(_LOOKBACK, n):
        candidate = candles[index]
        preceding = candles[index - _LOOKBACK : index]
        baseline = max(total_range(c) for c in preceding)
        if baseline == 0:
            continue
        ratio = total_range(candidate) / baseline
        if ratio < configuration.reversal_candidate_size_ratio_standard:
            continue

        efficiency = body_efficiency(candidate)
        if efficiency < configuration.reversal_body_efficiency_standard:
            continue

        is_bearish = candidate.close < candidate.open
        is_bullish = candidate.close > candidate.open

        if is_bearish:
            close_position = bearish_close_position(candidate)
            poi_type = PoiType.SELL_TO_BUY_CANDLE
            direction = PoiDirection.BULLISH
        elif is_bullish:
            close_position = bullish_close_position(candidate)
            poi_type = PoiType.BUY_TO_SELL_CANDLE
            direction = PoiDirection.BEARISH
        else:
            continue

        if close_position < configuration.reversal_close_position_standard:
            continue

        midpoint = (candidate.high + candidate.low) / _TWO
        confirmation_index: int | None = None
        for probe_index in range(index + 1, min(index + 1 + _CONFIRMATION_WINDOW, n)):
            probe = candles[probe_index]
            if direction == PoiDirection.BULLISH and probe.close > midpoint:
                confirmation_index = probe_index
                break
            if direction == PoiDirection.BEARISH and probe.close < midpoint:
                confirmation_index = probe_index
                break
        if confirmation_index is None:
            continue

        strong = (
            ratio >= configuration.reversal_candidate_size_ratio_strong
            and efficiency >= configuration.reversal_body_efficiency_strong
            and close_position >= configuration.reversal_close_position_strong
        )
        confirmation_candle = candles[confirmation_index]

        results.append(
            ReversalCandleCandidate(
                symbol=candidate.symbol,
                timeframe=candidate.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=candidate.high,
                zone_bottom=candidate.low,
                strength_tier=(
                    PoiStrengthTier.STRONG if strong else PoiStrengthTier.STANDARD
                ),
                source_candle_record_ids=(candidate.record_id,),
                candidate_event_time_utc=candidate.event_time_utc,
                confirmation_time_utc=confirmation_candle.availability_time_utc,
                availability_time_utc=confirmation_candle.availability_time_utc,
            )
        )

    return tuple(results)
