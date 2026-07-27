from decimal import Decimal

from pydantic import field_validator

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer


def _require_positive_decimal(value: Decimal) -> Decimal:
    if value <= 0:
        raise ValueError("Value must be strictly greater than zero.")
    return value


def _require_positive_int(value: int) -> int:
    if value <= 0:
        raise ValueError("Value must be strictly greater than zero.")
    return value


class MarketMeasurementConfiguration(ContractModel):
    minimum_price_tick: Decimal

    atr_period: int = 14
    range_context_window: int = 20

    pivot_tie_tolerance_atr_multiplier: Decimal = Decimal("0.02")
    meaningful_reversal_atr_multiplier: Decimal = Decimal("0.50")

    equal_level_tolerance_atr_multiplier: Decimal = Decimal("0.10")

    trendline_min_anchor_spacing_bars: int = 5
    trendline_horizontal_atr_multiplier: Decimal = Decimal("0.02")
    trendline_too_steep_atr_multiplier: Decimal = Decimal("0.35")
    trendline_touch_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    trendline_pierce_tolerance_atr_multiplier: Decimal = Decimal("0.20")

    support_resistance_zone_depth_atr_multiplier: Decimal = Decimal("0.10")
    support_resistance_touch_tolerance_atr_multiplier: Decimal = Decimal("0.05")
    support_resistance_pierce_tolerance_atr_multiplier: Decimal = Decimal("0.15")

    displacement_fast_ratio: Decimal = Decimal("1.50")
    displacement_very_fast_ratio: Decimal = Decimal("2.00")

    reaction_window_bars: int = 5
    reaction_standard_atr_ratio: Decimal = Decimal("0.75")
    reaction_standard_zone_clearance_ratio: Decimal = Decimal("1.00")
    reaction_standard_directional_efficiency: Decimal = Decimal("0.50")
    reaction_standard_directional_candle_share: Decimal = Decimal("0.60")
    reaction_strong_atr_ratio: Decimal = Decimal("1.25")
    reaction_strong_zone_clearance_ratio: Decimal = Decimal("1.50")
    reaction_strong_directional_efficiency: Decimal = Decimal("0.60")
    reaction_strong_directional_candle_share: Decimal = Decimal("0.67")

    leg_fast_normalized_speed_per_bar: Decimal = Decimal("0.50")
    leg_fast_directional_efficiency: Decimal = Decimal("0.60")
    leg_fast_directional_candle_share: Decimal = Decimal("0.67")
    leg_strong_fast_normalized_speed_per_bar: Decimal = Decimal("0.75")
    leg_strong_fast_directional_efficiency: Decimal = Decimal("0.75")
    leg_strong_fast_directional_candle_share: Decimal = Decimal("0.80")

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )

    @field_validator("minimum_price_tick")
    @classmethod
    def _validate_minimum_price_tick(cls, value: Decimal) -> Decimal:
        return _require_positive_decimal(value)

    @field_validator(
        "atr_period",
        "range_context_window",
        "trendline_min_anchor_spacing_bars",
        "reaction_window_bars",
    )
    @classmethod
    def _validate_positive_int_fields(cls, value: int) -> int:
        return _require_positive_int(value)
