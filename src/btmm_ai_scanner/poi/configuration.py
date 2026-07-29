from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.poi.enums import PoiType

_ALL_IMPLEMENTABLE_POI_TYPES: frozenset[PoiType] = frozenset(PoiType)


class InvalidPoiConfigurationError(ValueError):
    pass


class PoiConfiguration(ContractModel):
    minimum_price_tick: Decimal

    enabled_poi_types: frozenset[PoiType] = _ALL_IMPLEMENTABLE_POI_TYPES
    supported_symbols: frozenset[InternalSymbol] = frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )

    order_block_size_ratio_standard: Decimal = Decimal("2.0")
    order_block_size_ratio_strong: Decimal = Decimal("3.0")
    small_candle_ratio_standard: Decimal = Decimal("0.50")
    small_candle_ratio_strong: Decimal = Decimal("0.3333")

    base_min_candles: int = 2
    base_max_candles: int = 6
    base_height_atr_multiplier: Decimal = Decimal("0.75")
    base_height_departure_multiplier: Decimal = Decimal("0.60")
    base_midpoint_drift_ratio: Decimal = Decimal("0.25")
    base_overlap_ratio_minimum: Decimal = Decimal("0.50")

    pressure_wick_share_standard: Decimal = Decimal("0.40")
    pressure_wick_body_efficiency_standard: Decimal = Decimal("0.25")
    pressure_wick_dominance_standard: Decimal = Decimal("2.0")
    pressure_wick_close_position_standard: Decimal = Decimal("0.60")
    pressure_wick_share_strong: Decimal = Decimal("0.50")
    pressure_wick_body_efficiency_strong: Decimal = Decimal("0.30")
    pressure_wick_dominance_strong: Decimal = Decimal("3.0")
    pressure_wick_close_position_strong: Decimal = Decimal("0.70")
    pressure_wick_range_context_strong: Decimal = Decimal("1.25")

    hammer_shooting_star_wick_share_standard: Decimal = Decimal("0.60")
    hammer_shooting_star_body_efficiency_standard: Decimal = Decimal("0.30")
    hammer_shooting_star_opposite_wick_standard: Decimal = Decimal("0.10")
    hammer_shooting_star_wick_share_strong: Decimal = Decimal("0.70")
    hammer_shooting_star_body_efficiency_strong: Decimal = Decimal("0.20")
    hammer_shooting_star_opposite_wick_strong: Decimal = Decimal("0.05")

    doji_body_efficiency_standard: Decimal = Decimal("0.10")
    doji_body_efficiency_strong: Decimal = Decimal("0.05")

    reversal_candidate_size_ratio_standard: Decimal = Decimal("2.0")
    reversal_candidate_size_ratio_strong: Decimal = Decimal("3.0")
    reversal_body_efficiency_standard: Decimal = Decimal("0.60")
    reversal_body_efficiency_strong: Decimal = Decimal("0.70")
    reversal_close_position_standard: Decimal = Decimal("0.70")
    reversal_close_position_strong: Decimal = Decimal("0.80")

    zone_contact_tolerance_atr_multiplier: Decimal = Decimal("0.05")
    zone_contact_tolerance_zone_height_multiplier: Decimal = Decimal("0.10")
    zone_overshoot_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    zone_overshoot_tolerance_zone_height_multiplier: Decimal = Decimal("0.25")

    reclaim_window_bars: int = 3
    displacement_window_bars: int = 3

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )


_POSITIVE_DECIMAL_FIELDS: tuple[str, ...] = (
    "minimum_price_tick",
    "order_block_size_ratio_standard",
    "order_block_size_ratio_strong",
    "small_candle_ratio_standard",
    "small_candle_ratio_strong",
    "base_height_atr_multiplier",
    "base_height_departure_multiplier",
    "base_midpoint_drift_ratio",
    "base_overlap_ratio_minimum",
    "pressure_wick_share_standard",
    "pressure_wick_body_efficiency_standard",
    "pressure_wick_dominance_standard",
    "pressure_wick_close_position_standard",
    "pressure_wick_share_strong",
    "pressure_wick_body_efficiency_strong",
    "pressure_wick_dominance_strong",
    "pressure_wick_close_position_strong",
    "pressure_wick_range_context_strong",
    "hammer_shooting_star_wick_share_standard",
    "hammer_shooting_star_body_efficiency_standard",
    "hammer_shooting_star_opposite_wick_standard",
    "hammer_shooting_star_wick_share_strong",
    "hammer_shooting_star_body_efficiency_strong",
    "hammer_shooting_star_opposite_wick_strong",
    "doji_body_efficiency_standard",
    "doji_body_efficiency_strong",
    "reversal_candidate_size_ratio_standard",
    "reversal_candidate_size_ratio_strong",
    "reversal_body_efficiency_standard",
    "reversal_body_efficiency_strong",
    "reversal_close_position_standard",
    "reversal_close_position_strong",
    "zone_contact_tolerance_atr_multiplier",
    "zone_contact_tolerance_zone_height_multiplier",
    "zone_overshoot_tolerance_atr_multiplier",
    "zone_overshoot_tolerance_zone_height_multiplier",
)

_POSITIVE_INT_FIELDS: tuple[str, ...] = (
    "base_min_candles",
    "base_max_candles",
    "reclaim_window_bars",
    "displacement_window_bars",
)


def validate_configuration(configuration: PoiConfiguration) -> None:
    """Explicit, reachable validation raising the exact approved typed error.

    Pydantic field validators would wrap a raised error in ValidationError,
    losing the InvalidPoiConfigurationError identity the register requires
    callers to be able to catch directly.
    """
    for field_name in _POSITIVE_DECIMAL_FIELDS:
        value: Decimal = getattr(configuration, field_name)
        if value <= 0:
            raise InvalidPoiConfigurationError(
                f"{field_name} must be strictly greater than zero, got {value!r}."
            )

    for int_field_name in _POSITIVE_INT_FIELDS:
        int_value: int = getattr(configuration, int_field_name)
        if int_value <= 0:
            raise InvalidPoiConfigurationError(
                f"{int_field_name} must be strictly greater than zero, got"
                f" {int_value!r}."
            )

    if configuration.base_max_candles < configuration.base_min_candles:
        raise InvalidPoiConfigurationError(
            "base_max_candles must be greater than or equal to base_min_candles."
        )

    if not configuration.enabled_poi_types.issubset(_ALL_IMPLEMENTABLE_POI_TYPES):
        raise InvalidPoiConfigurationError(
            "enabled_poi_types may only contain approved implementable PoiType members."
        )

    if len(configuration.supported_symbols) == 0:
        raise InvalidPoiConfigurationError(
            "supported_symbols must contain at least one InternalSymbol."
        )
