from decimal import Decimal

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration


def test_market_measurement_configuration_default_values_match_approved_standards() -> (
    None
):
    config = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

    assert config.atr_period == 14
    assert config.range_context_window == 20
    assert config.pivot_tie_tolerance_atr_multiplier == Decimal("0.02")
    assert config.meaningful_reversal_atr_multiplier == Decimal("0.50")
    assert config.equal_level_tolerance_atr_multiplier == Decimal("0.10")
    assert config.trendline_min_anchor_spacing_bars == 5
    assert config.trendline_horizontal_atr_multiplier == Decimal("0.02")
    assert config.trendline_too_steep_atr_multiplier == Decimal("0.35")
    assert config.trendline_touch_tolerance_atr_multiplier == Decimal("0.10")
    assert config.trendline_pierce_tolerance_atr_multiplier == Decimal("0.20")
    assert config.support_resistance_zone_depth_atr_multiplier == Decimal("0.10")
    assert config.support_resistance_touch_tolerance_atr_multiplier == Decimal("0.05")
    assert config.support_resistance_pierce_tolerance_atr_multiplier == Decimal("0.15")
    assert config.displacement_fast_ratio == Decimal("1.50")
    assert config.displacement_very_fast_ratio == Decimal("2.00")
    assert config.reaction_window_bars == 5
    assert config.reaction_standard_atr_ratio == Decimal("0.75")
    assert config.reaction_strong_atr_ratio == Decimal("1.25")
    assert (
        config.evidence_classification == EvidenceClassification.ENGINEERING_PROVISIONAL
    )


def test_market_measurement_configuration_is_frozen_and_immutable() -> None:
    config = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

    with pytest.raises(ValidationError):
        config.minimum_price_tick = Decimal("0.02")


def test_market_measurement_configuration_requires_minimum_price_tick_with_no_default() -> (
    None
):
    with pytest.raises(ValidationError):
        MarketMeasurementConfiguration()  # type: ignore[call-arg]


def test_market_measurement_configuration_rejects_non_positive_minimum_price_tick() -> (
    None
):
    with pytest.raises(ValidationError):
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("0"))
    with pytest.raises(ValidationError):
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("-0.01"))


def test_market_measurement_configuration_rejects_non_positive_atr_period() -> None:
    with pytest.raises(ValidationError):
        MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"), atr_period=0)


def test_market_measurement_configuration_rejects_non_positive_range_context_window() -> (
    None
):
    with pytest.raises(ValidationError):
        MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01"), range_context_window=-1
        )
