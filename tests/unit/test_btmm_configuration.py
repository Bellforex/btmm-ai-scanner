from decimal import Decimal

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.btmm.configuration import (
    BtmmConfiguration,
    InvalidBtmmConfigurationError,
    validate_configuration,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.poi.enums import LIFECYCLE_ELIGIBLE_POI_TYPES


def test_configuration_defaults_match_ambiguity_8_thresholds() -> None:
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    assert config.interaction_contact_tolerance_atr_multiplier == Decimal("0.05")
    assert config.interaction_contact_tolerance_zone_height_multiplier == Decimal(
        "0.10"
    )
    assert config.interaction_overshoot_tolerance_atr_multiplier == Decimal("0.10")
    assert config.interaction_overshoot_tolerance_zone_height_multiplier == Decimal(
        "0.25"
    )
    assert config.interaction_edge_touch_max_penetration_ratio == Decimal("0.25")
    assert config.interaction_partial_entry_max_penetration_ratio == Decimal("0.50")


def test_configuration_defaults_match_ambiguity_9_thresholds() -> None:
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    assert config.reaction_window_bars == 5
    assert config.reaction_standard_atr_ratio == Decimal("0.75")
    assert config.reaction_standard_zone_clearance_ratio == Decimal("1.00")
    assert config.reaction_standard_directional_efficiency == Decimal("0.50")
    assert config.reaction_standard_directional_candle_share == Decimal("0.60")
    assert config.reaction_strong_atr_ratio == Decimal("1.25")
    assert config.reaction_strong_zone_clearance_ratio == Decimal("1.50")
    assert config.reaction_strong_directional_efficiency == Decimal("0.60")
    assert config.reaction_strong_directional_candle_share == Decimal("0.67")


def test_configuration_is_frozen_and_immutable() -> None:
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    with pytest.raises(ValidationError):
        config.minimum_price_tick = Decimal("0.02")


def test_configuration_rejects_non_positive_thresholds() -> None:
    config = BtmmConfiguration(minimum_price_tick=Decimal("-1"))
    with pytest.raises(InvalidBtmmConfigurationError):
        validate_configuration(config)

    zero_window_config = BtmmConfiguration(
        minimum_price_tick=Decimal("0.01"), reaction_window_bars=0
    )
    with pytest.raises(InvalidBtmmConfigurationError):
        validate_configuration(zero_window_config)


def test_configuration_default_evidence_classification_is_engineering_provisional() -> (
    None
):
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    assert (
        config.evidence_classification == EvidenceClassification.ENGINEERING_PROVISIONAL
    )
    assert config.formation_timeframes == frozenset({Timeframe.M5, Timeframe.M15})
    assert config.supporting_only_timeframes == frozenset({Timeframe.M1})
    assert config.supported_symbols == frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )


def test_configuration_eligible_poi_types_default_matches_exact_18() -> None:
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))

    assert len(config.eligible_poi_types) == 18
    assert config.eligible_poi_types == LIFECYCLE_ELIGIBLE_POI_TYPES
