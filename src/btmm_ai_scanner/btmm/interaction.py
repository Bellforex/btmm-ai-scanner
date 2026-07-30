from collections.abc import Sequence
from decimal import Decimal
from typing import NamedTuple

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmInteractionClass
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import PoiDirection

_TWO = Decimal("2")
_ZERO = Decimal("0")

ELIGIBLE_INTERACTION_CLASSES: frozenset[BtmmInteractionClass] = frozenset(
    {
        BtmmInteractionClass.EDGE_TOUCH,
        BtmmInteractionClass.PARTIAL_ENTRY,
        BtmmInteractionClass.DEEP_ENTRY,
        BtmmInteractionClass.FAR_BOUNDARY_TOUCH,
        BtmmInteractionClass.CONTROLLED_OVERSHOOT,
    }
)


class InteractionResult(NamedTuple):
    candle_index: int
    interaction_class: BtmmInteractionClass


def _reference_atr(
    atr_values: Sequence[Decimal | None], index: int, fallback: Decimal
) -> Decimal:
    value = atr_values[index] if 0 <= index < len(atr_values) else None
    if value is not None and value > 0:
        return value
    return fallback


def _tolerance(
    candle: NormalizedCandle,
    reference_atr: Decimal,
    zone_height: Decimal,
    minimum_price_tick: Decimal,
    atr_multiplier: Decimal,
    height_multiplier: Decimal,
) -> Decimal:
    bound_a = atr_multiplier * reference_atr
    bound_b = height_multiplier * zone_height
    return max(_TWO * minimum_price_tick, min(bound_a, bound_b))


def _touches_zone(
    candle: NormalizedCandle, zone_top: Decimal, zone_bottom: Decimal
) -> bool:
    return candle.low <= zone_top and candle.high >= zone_bottom


def find_first_interaction(
    candles: Sequence[NormalizedCandle],
    start_index: int,
    atr_values: Sequence[Decimal | None],
    zone_top: Decimal,
    zone_bottom: Decimal,
    direction: PoiDirection,
    configuration: BtmmConfiguration,
) -> InteractionResult | None:
    zone_height = zone_top - zone_bottom
    min_tick = configuration.minimum_price_tick

    for index in range(start_index, len(candles)):
        candle = candles[index]
        fallback = candle.high - candle.low
        reference_atr = _reference_atr(atr_values, index, fallback)

        if not _touches_zone(candle, zone_top, zone_bottom):
            continue

        prior_reference_price = candles[index - 1].close if index > 0 else candle.open
        if direction == PoiDirection.BULLISH:
            canonical_side = prior_reference_price >= zone_top
        else:
            canonical_side = prior_reference_price <= zone_bottom

        if not canonical_side:
            return InteractionResult(
                index, BtmmInteractionClass.NONCANONICAL_SIDE_INTERACTION
            )

        overshoot_tolerance = _tolerance(
            candle,
            reference_atr,
            zone_height,
            min_tick,
            configuration.interaction_overshoot_tolerance_atr_multiplier,
            configuration.interaction_overshoot_tolerance_zone_height_multiplier,
        )

        if direction == PoiDirection.BULLISH:
            raw_penetration = zone_top - candle.low
        else:
            raw_penetration = candle.high - zone_bottom

        if raw_penetration >= zone_height:
            overshoot_distance = raw_penetration - zone_height
            penetration_ratio = Decimal("1")
        else:
            overshoot_distance = _ZERO
            penetration_ratio = (
                raw_penetration / zone_height if zone_height > 0 else _ZERO
            )

        if overshoot_distance > overshoot_tolerance:
            interaction_class = BtmmInteractionClass.EXCESSIVE_OVERSHOOT
        elif overshoot_distance > 0:
            interaction_class = BtmmInteractionClass.CONTROLLED_OVERSHOOT
        elif penetration_ratio >= 1:
            interaction_class = BtmmInteractionClass.FAR_BOUNDARY_TOUCH
        elif (
            penetration_ratio
            > configuration.interaction_partial_entry_max_penetration_ratio
        ):
            interaction_class = BtmmInteractionClass.DEEP_ENTRY
        elif (
            penetration_ratio
            > configuration.interaction_edge_touch_max_penetration_ratio
        ):
            interaction_class = BtmmInteractionClass.PARTIAL_ENTRY
        else:
            interaction_class = BtmmInteractionClass.EDGE_TOUCH

        return InteractionResult(index, interaction_class)

    return None
