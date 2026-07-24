from datetime import datetime

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import to_utc
from btmm_ai_scanner.contracts.rule_version_manifest import (
    CompatibilityClass,
    validate_initial_or_successor_consistency,
    validate_manifest_name,
)
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)


class SchemaVersionManifest(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    schema_name: str
    schema_version: SemVer
    previous_schema_version: SemVer | None
    compatibility_with_previous: CompatibilityClass
    supersedes_manifest_id: UUIDv7 | None

    effective_at_utc: datetime

    target_contract_name: str
    target_contract_version: SemVer
    evidence_classification: EvidenceClassification

    manifest_contract_version: SemVer
    manifest_schema_version: SemVer
    provenance_id: UUIDv7

    @field_validator("schema_name", "target_contract_name")
    @classmethod
    def _validate_names(cls, value: str) -> str:
        return validate_manifest_name(value)

    @field_validator("effective_at_utc")
    @classmethod
    def _normalize_effective_at(cls, value: datetime) -> datetime:
        return to_utc(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "SchemaVersionManifest":
        validate_initial_or_successor_consistency(
            previous_version=self.previous_schema_version,
            current_version=self.schema_version,
            supersedes_manifest_id=self.supersedes_manifest_id,
            compatibility_with_previous=self.compatibility_with_previous,
            record_id=self.record_id,
        )
        return self
