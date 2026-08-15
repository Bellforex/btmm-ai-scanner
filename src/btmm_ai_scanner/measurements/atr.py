from collections.abc import Sequence
from dataclasses import dataclass
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


@dataclass(frozen=True)
class IncrementalAtrState:
    """Exact append-stable incremental image of ``compute_atr_series(prefix,
    period)``. Wilder ATR is an IIR recurrence: the true range needs only the
    previous close, and the smoothed value needs either the warm-up sum (before
    the seed) or the previous finalized ATR (after it). No raw candle retention
    is required, so appending a candle is O(1) and reproduces the full-prefix
    series value-for-value at every prefix (never a suffix reseed).

    This mirrors the register-§44AI-proven measurement recurrence
    (``domain.analyzer._atr_incremental_step``) but is public, period-parametric,
    and free of any coupling to ``configuration.atr_period`` — the POI detectors
    require exactly ``period=14`` because that is what the batch detectors use.
    ``compute_atr_series`` above is left byte-for-byte unchanged as the oracle."""

    period: int
    previous_close: Decimal | None = None
    warmup_true_range_sum: Decimal = Decimal(0)
    warmup_sample_count: int = 0
    previous_finalized_atr: Decimal | None = None


def initial_incremental_atr_state(period: int = 14) -> IncrementalAtrState:
    return IncrementalAtrState(period=period)


def advance_incremental_atr(
    state: IncrementalAtrState, candle: NormalizedCandle
) -> tuple[IncrementalAtrState, Decimal | None]:
    """Advance one candle. Returns the new state and this candle's ATR value —
    ``None`` during warm-up (fewer than ``period`` samples), the seed mean at the
    ``period``-th sample, and the Wilder recurrence thereafter — identical to
    ``compute_atr_series(prefix, period)[-1]`` for the same prefix."""
    period = state.period
    true_range = _true_range(candle, state.previous_close)

    if state.previous_finalized_atr is not None:
        current_atr = (
            state.previous_finalized_atr * Decimal(period - 1) + true_range
        ) / Decimal(period)
        return (
            IncrementalAtrState(
                period=period,
                previous_close=candle.close,
                warmup_true_range_sum=state.warmup_true_range_sum,
                warmup_sample_count=state.warmup_sample_count,
                previous_finalized_atr=current_atr,
            ),
            current_atr,
        )

    new_sum = state.warmup_true_range_sum + true_range
    new_count = state.warmup_sample_count + 1
    if new_count < period:
        return (
            IncrementalAtrState(
                period=period,
                previous_close=candle.close,
                warmup_true_range_sum=new_sum,
                warmup_sample_count=new_count,
                previous_finalized_atr=None,
            ),
            None,
        )

    seed_atr = new_sum / Decimal(period)
    return (
        IncrementalAtrState(
            period=period,
            previous_close=candle.close,
            warmup_true_range_sum=new_sum,
            warmup_sample_count=new_count,
            previous_finalized_atr=seed_atr,
        ),
        seed_atr,
    )
