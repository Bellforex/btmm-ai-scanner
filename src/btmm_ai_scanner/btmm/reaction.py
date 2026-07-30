from collections.abc import Sequence
from decimal import Decimal
from typing import NamedTuple

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmReactionClassification
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.legs import (
    LegMeasurement,
    LegSpeedClassification,
    measure_leg,
)
from btmm_ai_scanner.poi.enums import PoiDirection

_ZERO = Decimal("0")


def find_reaction_start(
    candles: Sequence[NormalizedCandle],
    start_index: int,
    entry_boundary: Decimal,
    direction: PoiDirection,
) -> int | None:
    for index in range(start_index, len(candles)):
        candle = candles[index]
        if direction == PoiDirection.BULLISH:
            if candle.close > entry_boundary:
                return index
        else:
            if candle.close < entry_boundary:
                return index
    return None


def compute_reaction_anchor(
    candles: Sequence[NormalizedCandle],
    interaction_index: int,
    reaction_start_index: int,
    direction: PoiDirection,
) -> Decimal:
    span = candles[interaction_index : reaction_start_index + 1]
    if direction == PoiDirection.BULLISH:
        return min(candle.low for candle in span)
    return max(candle.high for candle in span)


class ReactionTierResult(NamedTuple):
    reaction_classification: BtmmReactionClassification
    reaction_speed_classification: LegSpeedClassification
    bars_to_standard_reaction: int | None
    bars_to_strong_reaction: int | None


def _favorable_extreme(
    window: Sequence[NormalizedCandle], direction: PoiDirection
) -> Decimal:
    if direction == PoiDirection.BULLISH:
        return max(candle.high for candle in window)
    return min(candle.low for candle in window)


def _tier_conditions(
    leg: LegMeasurement,
    atr_reaction_ratio: Decimal,
    zone_clearance_ratio: Decimal,
    configuration: BtmmConfiguration,
) -> tuple[bool, bool]:
    standard = (
        atr_reaction_ratio >= configuration.reaction_standard_atr_ratio
        and zone_clearance_ratio >= configuration.reaction_standard_zone_clearance_ratio
        and leg.directional_efficiency
        >= configuration.reaction_standard_directional_efficiency
        and leg.directional_candle_share
        >= configuration.reaction_standard_directional_candle_share
    )
    strong = (
        atr_reaction_ratio >= configuration.reaction_strong_atr_ratio
        and zone_clearance_ratio >= configuration.reaction_strong_zone_clearance_ratio
        and leg.directional_efficiency
        >= configuration.reaction_strong_directional_efficiency
        and leg.directional_candle_share
        >= configuration.reaction_strong_directional_candle_share
        and leg.classification
        in (LegSpeedClassification.FAST, LegSpeedClassification.STRONG_FAST)
    )
    return standard, strong


def evaluate_reaction_window(
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    reaction_start_index: int,
    reaction_anchor: Decimal,
    far_boundary: Decimal,
    zone_height: Decimal,
    direction: PoiDirection,
    configuration: BtmmConfiguration,
) -> ReactionTierResult:
    is_bullish = direction == PoiDirection.BULLISH
    window_bars = configuration.reaction_window_bars
    highest_tier = 0  # 0 = weak, 1 = standard, 2 = strong
    bars_to_standard: int | None = None
    bars_to_strong: int | None = None

    for k in range(1, window_bars + 1):
        sub_window = candles[reaction_start_index : reaction_start_index + k]
        sub_atr = atr_values[reaction_start_index : reaction_start_index + k]
        leg = measure_leg(
            sub_window,
            sub_atr,
            is_bullish_direction=is_bullish,
            fast_normalized_speed_per_bar=configuration.reaction_speed_fast_normalized_speed_per_bar,
            fast_directional_efficiency=configuration.reaction_speed_fast_directional_efficiency,
            fast_directional_candle_share=configuration.reaction_speed_fast_directional_candle_share,
            strong_fast_normalized_speed_per_bar=configuration.reaction_speed_strong_fast_normalized_speed_per_bar,
            strong_fast_directional_efficiency=configuration.reaction_speed_strong_fast_directional_efficiency,
            strong_fast_directional_candle_share=configuration.reaction_speed_strong_fast_directional_candle_share,
        )
        favorable_extreme = _favorable_extreme(sub_window, direction)
        reaction_mfe = abs(favorable_extreme - reaction_anchor)
        atr_reaction_ratio = (
            reaction_mfe / leg.reference_atr if leg.reference_atr > 0 else _ZERO
        )
        if is_bullish:
            zone_clearance_distance = favorable_extreme - far_boundary
        else:
            zone_clearance_distance = far_boundary - favorable_extreme
        zone_clearance_ratio = (
            zone_clearance_distance / zone_height if zone_height > 0 else _ZERO
        )

        standard, strong = _tier_conditions(
            leg, atr_reaction_ratio, zone_clearance_ratio, configuration
        )
        if strong:
            highest_tier = max(highest_tier, 2)
            if bars_to_strong is None:
                bars_to_strong = k
        if standard:
            highest_tier = max(highest_tier, 1)
            if bars_to_standard is None:
                bars_to_standard = k

    if highest_tier == 2:
        reaction_classification = BtmmReactionClassification.STRONG_REACTION
    elif highest_tier == 1:
        reaction_classification = BtmmReactionClassification.STANDARD_REACTION
    else:
        reaction_classification = BtmmReactionClassification.WEAK_REACTION

    full_window = candles[reaction_start_index : reaction_start_index + window_bars]
    final_mfe_offset = 0
    best_extreme: Decimal | None = None
    for offset, candle in enumerate(full_window):
        candidate_extreme = candle.high if is_bullish else candle.low
        if best_extreme is None or (
            candidate_extreme > best_extreme
            if is_bullish
            else candidate_extreme < best_extreme
        ):
            best_extreme = candidate_extreme
            final_mfe_offset = offset

    speed_leg_candles = candles[
        reaction_start_index : reaction_start_index + final_mfe_offset + 1
    ]
    speed_leg_atr = atr_values[
        reaction_start_index : reaction_start_index + final_mfe_offset + 1
    ]
    speed_leg = measure_leg(
        speed_leg_candles,
        speed_leg_atr,
        is_bullish_direction=is_bullish,
        fast_normalized_speed_per_bar=configuration.reaction_speed_fast_normalized_speed_per_bar,
        fast_directional_efficiency=configuration.reaction_speed_fast_directional_efficiency,
        fast_directional_candle_share=configuration.reaction_speed_fast_directional_candle_share,
        strong_fast_normalized_speed_per_bar=configuration.reaction_speed_strong_fast_normalized_speed_per_bar,
        strong_fast_directional_efficiency=configuration.reaction_speed_strong_fast_directional_efficiency,
        strong_fast_directional_candle_share=configuration.reaction_speed_strong_fast_directional_candle_share,
    )

    return ReactionTierResult(
        reaction_classification=reaction_classification,
        reaction_speed_classification=speed_leg.classification,
        bars_to_standard_reaction=bars_to_standard,
        bars_to_strong_reaction=bars_to_strong,
    )
