from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import to_utc
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)


class CompatibilityClass(StrEnum):
    FULLY_COMPATIBLE = "FULLY_COMPATIBLE"
    BACKWARD_COMPATIBLE = "BACKWARD_COMPATIBLE"
    FORWARD_COMPATIBLE = "FORWARD_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"


def validate_manifest_name(value: str) -> str:
    if value == "" or value.strip() != value:
        raise ValueError(
            "Value must be nonblank and must not have leading or trailing whitespace."
        )
    return value


def validate_initial_or_successor_consistency(
    *,
    previous_version: SemVer | None,
    current_version: SemVer,
    supersedes_manifest_id: object | None,
    compatibility_with_previous: CompatibilityClass,
    record_id: object,
) -> None:
    if previous_version is None:
        if supersedes_manifest_id is not None:
            raise ValueError(
                "An initial manifest (no previous version) must not have a"
                " supersedes_manifest_id."
            )
        if compatibility_with_previous != CompatibilityClass.UNKNOWN:
            raise ValueError(
                "An initial manifest (no previous version) must declare"
                " compatibility_with_previous as UNKNOWN."
            )
        return

    if supersedes_manifest_id is None:
        raise ValueError(
            "A successor manifest (previous version present) requires"
            " supersedes_manifest_id."
        )
    if supersedes_manifest_id == record_id:
        raise ValueError("supersedes_manifest_id must differ from record_id.")
    if previous_version.compare_precedence(current_version) != -1:
        raise ValueError(
            "A successor manifest's version must have strictly higher SemVer"
            " precedence than the previous version."
        )


class RuleVersionManifest(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    rule_set_name: str
    rule_version: SemVer
    previous_rule_version: SemVer | None
    compatibility_with_previous: CompatibilityClass
    supersedes_manifest_id: UUIDv7 | None

    effective_at_utc: datetime
    evidence_classification: EvidenceClassification

    manifest_contract_version: SemVer
    manifest_schema_version: SemVer
    provenance_id: UUIDv7

    @field_validator("rule_set_name")
    @classmethod
    def _validate_rule_set_name(cls, value: str) -> str:
        return validate_manifest_name(value)

    @field_validator("effective_at_utc")
    @classmethod
    def _normalize_effective_at(cls, value: datetime) -> datetime:
        return to_utc(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "RuleVersionManifest":
        validate_initial_or_successor_consistency(
            previous_version=self.previous_rule_version,
            current_version=self.rule_version,
            supersedes_manifest_id=self.supersedes_manifest_id,
            compatibility_with_previous=self.compatibility_with_previous,
            record_id=self.record_id,
        )
        return self
