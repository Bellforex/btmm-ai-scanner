from collections.abc import Sequence
from decimal import Decimal

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle

_ZERO = Decimal("0")
_TWO = Decimal("2")


def total_range(candle: NormalizedCandle) -> Decimal:
    return candle.high - candle.low


def body(candle: NormalizedCandle) -> Decimal:
    return abs(candle.close - candle.open)


def body_efficiency(candle: NormalizedCandle) -> Decimal:
    range_value = total_range(candle)
    if range_value == _ZERO:
        return _ZERO
    return body(candle) / range_value


def upper_wick(candle: NormalizedCandle) -> Decimal:
    return candle.high - max(candle.open, candle.close)


def lower_wick(candle: NormalizedCandle) -> Decimal:
    return min(candle.open, candle.close) - candle.low


def bullish_close_position(candle: NormalizedCandle) -> Decimal:
    range_value = total_range(candle)
    if range_value == _ZERO:
        return _ZERO
    return (candle.close - candle.low) / range_value


def bearish_close_position(candle: NormalizedCandle) -> Decimal:
    range_value = total_range(candle)
    if range_value == _ZERO:
        return _ZERO
    return (candle.high - candle.close) / range_value


def median_total_range(candles: Sequence[NormalizedCandle]) -> Decimal:
    if len(candles) == 0:
        return _ZERO
    ranges = sorted(total_range(candle) for candle in candles)
    midpoint = len(ranges) // 2
    if len(ranges) % 2 == 1:
        return ranges[midpoint]
    return (ranges[midpoint - 1] + ranges[midpoint]) / _TWO


def range_speed_ratio(
    candle: NormalizedCandle, preceding: Sequence[NormalizedCandle]
) -> Decimal:
    baseline = median_total_range(preceding)
    if baseline == _ZERO:
        return _ZERO
    return total_range(candle) / baseline
