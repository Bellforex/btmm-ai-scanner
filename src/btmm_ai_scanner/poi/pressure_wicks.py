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
    lower_wick,
    median_total_range,
    total_range,
    upper_wick,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType

_ONE = Decimal("1")
_BASELINE_WINDOW = 20


class PressureWickCandidate(NamedTuple):
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


def detect_pressure_wicks(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[PressureWickCandidate, ...]:
    results: list[PressureWickCandidate] = []

    for index, candle in enumerate(candles):
        candle_range = total_range(candle)
        if candle_range == 0:
            continue

        preceding = candles[max(0, index - _BASELINE_WINDOW) : index]
        baseline = median_total_range(preceding) if len(preceding) > 0 else candle_range
        range_context_ratio = candle_range / baseline if baseline > 0 else _ONE

        lw = lower_wick(candle)
        uw = upper_wick(candle)
        lw_share = lw / candle_range
        uw_share = uw / candle_range
        efficiency = body_efficiency(candle)
        bull_position = bullish_close_position(candle)
        bear_position = bearish_close_position(candle)

        dominance_ok_bull = (
            uw == 0 or lw >= configuration.pressure_wick_dominance_standard * uw
        )
        dominance_ok_bear = (
            lw == 0 or uw >= configuration.pressure_wick_dominance_standard * lw
        )

        bullish_candidate = (
            lw_share >= configuration.pressure_wick_share_standard
            and efficiency >= configuration.pressure_wick_body_efficiency_standard
            and dominance_ok_bull
            and bull_position >= configuration.pressure_wick_close_position_standard
        )
        bearish_candidate = (
            uw_share >= configuration.pressure_wick_share_standard
            and efficiency >= configuration.pressure_wick_body_efficiency_standard
            and dominance_ok_bear
            and bear_position >= configuration.pressure_wick_close_position_standard
        )

        if bullish_candidate:
            poi_type = PoiType.BULLISH_PRESSURE_WICK
            direction = PoiDirection.BULLISH
            zone_top = min(candle.open, candle.close)
            zone_bottom = candle.low
            strong = (
                lw_share >= configuration.pressure_wick_share_strong
                and efficiency >= configuration.pressure_wick_body_efficiency_strong
                and lw >= configuration.pressure_wick_dominance_strong * uw
                and bull_position >= configuration.pressure_wick_close_position_strong
                and range_context_ratio
                >= configuration.pressure_wick_range_context_strong
            )
        elif bearish_candidate:
            poi_type = PoiType.BEARISH_PRESSURE_WICK
            direction = PoiDirection.BEARISH
            zone_top = candle.high
            zone_bottom = max(candle.open, candle.close)
            strong = (
                uw_share >= configuration.pressure_wick_share_strong
                and efficiency >= configuration.pressure_wick_body_efficiency_strong
                and uw >= configuration.pressure_wick_dominance_strong * lw
                and bear_position >= configuration.pressure_wick_close_position_strong
                and range_context_ratio
                >= configuration.pressure_wick_range_context_strong
            )
        else:
            continue

        results.append(
            PressureWickCandidate(
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
