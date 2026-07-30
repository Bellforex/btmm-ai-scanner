from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.poi.enums import LIFECYCLE_ELIGIBLE_POI_TYPES, PoiType


class InvalidBtmmConfigurationError(ValueError):
    pass


class BtmmConfiguration(ContractModel):
    minimum_price_tick: Decimal

    eligible_poi_types: frozenset[PoiType] = LIFECYCLE_ELIGIBLE_POI_TYPES
    supported_symbols: frozenset[InternalSymbol] = frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )
    formation_timeframes: frozenset[Timeframe] = frozenset(
        {Timeframe.M5, Timeframe.M15}
    )
    supporting_only_timeframes: frozenset[Timeframe] = frozenset({Timeframe.M1})

    interaction_contact_tolerance_atr_multiplier: Decimal = Decimal("0.05")
    interaction_contact_tolerance_zone_height_multiplier: Decimal = Decimal("0.10")
    interaction_overshoot_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    interaction_overshoot_tolerance_zone_height_multiplier: Decimal = Decimal("0.25")
    interaction_edge_touch_max_penetration_ratio: Decimal = Decimal("0.25")
    interaction_partial_entry_max_penetration_ratio: Decimal = Decimal("0.50")

    reaction_window_bars: int = 5
    reaction_standard_atr_ratio: Decimal = Decimal("0.75")
    reaction_standard_zone_clearance_ratio: Decimal = Decimal("1.00")
    reaction_standard_directional_efficiency: Decimal = Decimal("0.50")
    reaction_standard_directional_candle_share: Decimal = Decimal("0.60")
    reaction_strong_atr_ratio: Decimal = Decimal("1.25")
    reaction_strong_zone_clearance_ratio: Decimal = Decimal("1.50")
    reaction_strong_directional_efficiency: Decimal = Decimal("0.60")
    reaction_strong_directional_candle_share: Decimal = Decimal("0.67")

    reaction_speed_fast_normalized_speed_per_bar: Decimal = Decimal("0.50")
    reaction_speed_fast_directional_efficiency: Decimal = Decimal("0.60")
    reaction_speed_fast_directional_candle_share: Decimal = Decimal("0.67")
    reaction_speed_strong_fast_normalized_speed_per_bar: Decimal = Decimal("0.75")
    reaction_speed_strong_fast_directional_efficiency: Decimal = Decimal("0.75")
    reaction_speed_strong_fast_directional_candle_share: Decimal = Decimal("0.80")

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )


_POSITIVE_DECIMAL_FIELDS: tuple[str, ...] = (
    "minimum_price_tick",
    "interaction_contact_tolerance_atr_multiplier",
    "interaction_contact_tolerance_zone_height_multiplier",
    "interaction_overshoot_tolerance_atr_multiplier",
    "interaction_overshoot_tolerance_zone_height_multiplier",
    "interaction_edge_touch_max_penetration_ratio",
    "interaction_partial_entry_max_penetration_ratio",
    "reaction_standard_atr_ratio",
    "reaction_standard_zone_clearance_ratio",
    "reaction_standard_directional_efficiency",
    "reaction_standard_directional_candle_share",
    "reaction_strong_atr_ratio",
    "reaction_strong_zone_clearance_ratio",
    "reaction_strong_directional_efficiency",
    "reaction_strong_directional_candle_share",
    "reaction_speed_fast_normalized_speed_per_bar",
    "reaction_speed_fast_directional_efficiency",
    "reaction_speed_fast_directional_candle_share",
    "reaction_speed_strong_fast_normalized_speed_per_bar",
    "reaction_speed_strong_fast_directional_efficiency",
    "reaction_speed_strong_fast_directional_candle_share",
)


def validate_configuration(configuration: BtmmConfiguration) -> None:
    """Explicit, reachable validation raising the exact approved typed error.

    Pydantic field validators would wrap a raised error in ValidationError,
    losing the InvalidBtmmConfigurationError identity callers must be able to
    catch directly.
    """
    for field_name in _POSITIVE_DECIMAL_FIELDS:
        value: Decimal = getattr(configuration, field_name)
        if value <= 0:
            raise InvalidBtmmConfigurationError(
                f"{field_name} must be strictly greater than zero, got {value!r}."
            )

    if configuration.reaction_window_bars <= 0:
        raise InvalidBtmmConfigurationError(
            "reaction_window_bars must be strictly greater than zero, got"
            f" {configuration.reaction_window_bars!r}."
        )

    if not configuration.eligible_poi_types.issubset(LIFECYCLE_ELIGIBLE_POI_TYPES):
        raise InvalidBtmmConfigurationError(
            "eligible_poi_types may only contain approved BTMM-eligible PoiType"
            " members."
        )

    if len(configuration.supported_symbols) == 0:
        raise InvalidBtmmConfigurationError(
            "supported_symbols must contain at least one InternalSymbol."
        )

    if not configuration.formation_timeframes.isdisjoint(
        configuration.supporting_only_timeframes
    ):
        raise InvalidBtmmConfigurationError(
            "formation_timeframes and supporting_only_timeframes must be disjoint."
        )
