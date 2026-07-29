from datetime import datetime
from decimal import Decimal
from itertools import pairwise
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.measurements.candle_metrics import total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType

_TWO = Decimal("2")
_ZERO = Decimal("0")
_ATR_PERIOD = 14


class BaseCandidate(NamedTuple):
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


def detect_bases(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[BaseCandidate, ...]:
    n = len(candles)
    if n < configuration.base_min_candles + 1:
        return ()

    atr_values = compute_atr_series(candles, _ATR_PERIOD)
    results: list[BaseCandidate] = []

    for start in range(n):
        for length in range(
            configuration.base_min_candles, configuration.base_max_candles + 1
        ):
            end = start + length
            if end >= n:
                continue

            base_candles = candles[start:end]
            departure = candles[end]
            departure_range = total_range(departure)
            if departure_range == 0:
                continue

            max_base_range = max(total_range(c) for c in base_candles)
            if max_base_range == 0:
                continue
            if (
                max_base_range
                > configuration.small_candle_ratio_standard * departure_range
            ):
                continue

            ratio = departure_range / max_base_range
            if ratio < configuration.order_block_size_ratio_standard:
                continue

            base_high = max(c.high for c in base_candles)
            base_low = min(c.low for c in base_candles)
            base_height = base_high - base_low

            reference_atr = atr_values[end - 1]
            if reference_atr is None or reference_atr == _ZERO:
                reference_atr = departure_range

            if base_height > configuration.base_height_atr_multiplier * reference_atr:
                continue
            if (
                base_height
                > configuration.base_height_departure_multiplier * departure_range
            ):
                continue

            if base_height > 0:
                base_midpoint = (base_high + base_low) / _TWO
                drift_ok = all(
                    abs(((c.high + c.low) / _TWO) - base_midpoint)
                    <= configuration.base_midpoint_drift_ratio * base_height
                    for c in base_candles
                )
                if not drift_ok:
                    continue

            overlap_ok = True
            for left, right in pairwise(base_candles):
                overlap_top = min(left.high, right.high)
                overlap_bottom = max(left.low, right.low)
                overlap = max(_ZERO, overlap_top - overlap_bottom)
                min_range = min(total_range(left), total_range(right))
                if min_range == 0:
                    continue
                if overlap / min_range < configuration.base_overlap_ratio_minimum:
                    overlap_ok = False
                    break
            if not overlap_ok:
                continue

            departure_bullish = (
                departure.close > departure.open and departure.close > base_high
            )
            departure_bearish = (
                departure.close < departure.open and departure.close < base_low
            )

            if departure_bullish:
                poi_type = PoiType.BASE_RALLY
                direction = PoiDirection.BULLISH
            elif departure_bearish:
                poi_type = PoiType.BASE_DROP
                direction = PoiDirection.BEARISH
            else:
                continue

            strong = (
                ratio >= configuration.order_block_size_ratio_strong
                and max_base_range
                <= configuration.small_candle_ratio_strong * departure_range
            )

            results.append(
                BaseCandidate(
                    symbol=departure.symbol,
                    timeframe=departure.timeframe,
                    poi_type=poi_type,
                    direction=direction,
                    zone_top=base_high,
                    zone_bottom=base_low,
                    strength_tier=(
                        PoiStrengthTier.STRONG if strong else PoiStrengthTier.STANDARD
                    ),
                    source_candle_record_ids=(
                        *(c.record_id for c in base_candles),
                        departure.record_id,
                    ),
                    candidate_event_time_utc=base_candles[0].event_time_utc,
                    confirmation_time_utc=departure.availability_time_utc,
                    availability_time_utc=departure.availability_time_utc,
                )
            )

    return tuple(results)
