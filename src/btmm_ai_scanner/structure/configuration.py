from decimal import Decimal

from pydantic import field_validator

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer


class StructureConfiguration(ContractModel):
    swing_relationship_equal_tolerance_atr_multiplier: Decimal = Decimal("0.10")

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = (
        EvidenceClassification.ENGINEERING_PROVISIONAL
    )

    @field_validator("swing_relationship_equal_tolerance_atr_multiplier")
    @classmethod
    def _validate_tolerance_multiplier(cls, value: Decimal) -> Decimal:
        if value <= 0:
            raise ValueError(
                "swing_relationship_equal_tolerance_atr_multiplier must be"
                " strictly greater than zero."
            )
        return value
