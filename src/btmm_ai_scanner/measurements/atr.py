from collections.abc import Sequence
from decimal import Decimal

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle


def _true_range(candle: NormalizedCandle, previous_close: Decimal | None) -> Decimal:
    high_low = candle.high - candle.low
    if previous_close is None:
        return high_low
    return max(
        high_low,
        abs(candle.high - previous_close),
        abs(candle.low - previous_close),
    )


def compute_atr_series(
    candles: Sequence[NormalizedCandle], period: int = 14
) -> tuple[Decimal | None, ...]:
    true_ranges: list[Decimal] = []
    previous_close: Decimal | None = None
    for candle in candles:
        true_ranges.append(_true_range(candle, previous_close))
        previous_close = candle.close

    atr_values: list[Decimal | None] = [None] * len(candles)
    if len(candles) < period:
        return tuple(atr_values)

    seed_index = period - 1
    seed = sum(true_ranges[0:period], Decimal(0)) / Decimal(period)
    atr_values[seed_index] = seed

    previous_atr = seed
    for index in range(period, len(candles)):
        current_atr = (
            previous_atr * Decimal(period - 1) + true_ranges[index]
        ) / Decimal(period)
        atr_values[index] = current_atr
        previous_atr = current_atr

    return tuple(atr_values)
