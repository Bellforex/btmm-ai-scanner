from collections.abc import Sequence
from decimal import Decimal
from enum import StrEnum
from typing import NamedTuple

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.candle_metrics import total_range

_ZERO = Decimal("0")


class LegSpeedClassification(StrEnum):
    FAST = "FAST"
    STRONG_FAST = "STRONG_FAST"
    SLOW_OR_UNCLEAR = "SLOW_OR_UNCLEAR"


class LegMeasurement(NamedTuple):
    bar_count: int
    net_directional_distance: Decimal
    reference_atr: Decimal
    leg_path_distance: Decimal
    normalized_speed_per_bar: Decimal
    directional_efficiency: Decimal
    directional_candle_share: Decimal
    classification: LegSpeedClassification


def _median(values: Sequence[Decimal]) -> Decimal:
    if len(values) == 0:
        return _ZERO
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[midpoint]
    return (ordered[midpoint - 1] + ordered[midpoint]) / Decimal(2)


def measure_leg(
    leg_candles: Sequence[NormalizedCandle],
    leg_candle_atr_values: Sequence[Decimal | None],
    *,
    is_bullish_direction: bool,
    fast_normalized_speed_per_bar: Decimal,
    fast_directional_efficiency: Decimal,
    fast_directional_candle_share: Decimal,
    strong_fast_normalized_speed_per_bar: Decimal,
    strong_fast_directional_efficiency: Decimal,
    strong_fast_directional_candle_share: Decimal,
) -> LegMeasurement:
    bar_count = len(leg_candles)
    if bar_count == 0:
        return LegMeasurement(
            bar_count=0,
            net_directional_distance=_ZERO,
            reference_atr=_ZERO,
            leg_path_distance=_ZERO,
            normalized_speed_per_bar=_ZERO,
            directional_efficiency=_ZERO,
            directional_candle_share=_ZERO,
            classification=LegSpeedClassification.SLOW_OR_UNCLEAR,
        )

    start_price = leg_candles[0].open
    end_price = leg_candles[-1].close
    net_directional_distance = abs(end_price - start_price)

    known_atr_values = [value for value in leg_candle_atr_values if value is not None]
    reference_atr = _median(known_atr_values)

    leg_path_distance = sum((total_range(candle) for candle in leg_candles), _ZERO)

    directional_closes = sum(
        1
        for candle in leg_candles
        if (
            candle.close >= candle.open
            if is_bullish_direction
            else candle.close <= candle.open
        )
    )
    directional_candle_share = Decimal(directional_closes) / Decimal(bar_count)

    if reference_atr == _ZERO or leg_path_distance == _ZERO:
        return LegMeasurement(
            bar_count=bar_count,
            net_directional_distance=net_directional_distance,
            reference_atr=reference_atr,
            leg_path_distance=leg_path_distance,
            normalized_speed_per_bar=_ZERO,
            directional_efficiency=_ZERO,
            directional_candle_share=directional_candle_share,
            classification=LegSpeedClassification.SLOW_OR_UNCLEAR,
        )

    normalized_speed_per_bar = net_directional_distance / (
        Decimal(bar_count) * reference_atr
    )
    directional_efficiency = net_directional_distance / leg_path_distance

    if (
        normalized_speed_per_bar >= strong_fast_normalized_speed_per_bar
        and directional_efficiency >= strong_fast_directional_efficiency
        and directional_candle_share >= strong_fast_directional_candle_share
    ):
        classification = LegSpeedClassification.STRONG_FAST
    elif (
        normalized_speed_per_bar >= fast_normalized_speed_per_bar
        and directional_efficiency >= fast_directional_efficiency
        and directional_candle_share >= fast_directional_candle_share
    ):
        classification = LegSpeedClassification.FAST
    else:
        classification = LegSpeedClassification.SLOW_OR_UNCLEAR

    return LegMeasurement(
        bar_count=bar_count,
        net_directional_distance=net_directional_distance,
        reference_atr=reference_atr,
        leg_path_distance=leg_path_distance,
        normalized_speed_per_bar=normalized_speed_per_bar,
        directional_efficiency=directional_efficiency,
        directional_candle_share=directional_candle_share,
        classification=classification,
    )
