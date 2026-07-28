from decimal import Decimal

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.structure.configuration import StructureConfiguration


def test_structure_configuration_default_values_match_approved_standards() -> None:
    config = StructureConfiguration()

    assert config.swing_relationship_equal_tolerance_atr_multiplier == Decimal("0.10")
    assert (
        config.evidence_classification == EvidenceClassification.ENGINEERING_PROVISIONAL
    )


def test_structure_configuration_is_frozen_and_immutable() -> None:
    config = StructureConfiguration()

    with pytest.raises(ValidationError):
        config.swing_relationship_equal_tolerance_atr_multiplier = Decimal("0.20")


def test_structure_configuration_rejects_non_positive_tolerance_multiplier() -> None:
    with pytest.raises(ValidationError):
        StructureConfiguration(
            swing_relationship_equal_tolerance_atr_multiplier=Decimal("0")
        )
    with pytest.raises(ValidationError):
        StructureConfiguration(
            swing_relationship_equal_tolerance_atr_multiplier=Decimal("-0.10")
        )


def test_structure_configuration_evidence_classification_is_engineering_provisional() -> (
    None
):
    config = StructureConfiguration()
    assert (
        config.evidence_classification == EvidenceClassification.ENGINEERING_PROVISIONAL
    )


def test_structure_configuration_constructs_with_no_required_arguments() -> None:
    config = StructureConfiguration()
    assert config is not None
