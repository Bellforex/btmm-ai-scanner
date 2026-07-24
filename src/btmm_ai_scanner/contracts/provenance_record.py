from datetime import datetime
from enum import StrEnum

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.raw_candle import to_utc
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)


class EvidenceClassification(StrEnum):
    BOOK_SOURCED = "BOOK-SOURCED"
    BOOK_SUPPORTED_UNDERLYING_CONCEPT = "BOOK-SUPPORTED UNDERLYING CONCEPT"
    AUTHOR_APPROVED = "AUTHOR-APPROVED"
    AUTHOR_ADDED_PROJECT_TERMINOLOGY = "AUTHOR-ADDED PROJECT TERMINOLOGY"
    ENGINEERING_PROVISIONAL = "ENGINEERING-PROVISIONAL"
    EMPIRICALLY_CALIBRATED = "EMPIRICALLY-CALIBRATED"
    OUT_OF_SAMPLE_VALIDATED = "OUT-OF-SAMPLE-VALIDATED"
    PRODUCTION_APPROVED = "PRODUCTION-APPROVED"


class ProvenanceSourceReference(ContractModel):
    source_reference: str
    source_record_id: UUIDv7 | None
    source_version: SemVer | None

    @field_validator("source_reference")
    @classmethod
    def _validate_source_reference(cls, value: str) -> str:
        if value == "" or value.strip() != value:
            raise ValueError(
                "source_reference must be nonblank and must not have leading or"
                " trailing whitespace."
            )
        return value


class ProvenanceRecord(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    subject_record_id: UUIDv7

    sources: tuple[ProvenanceSourceReference, ...]
    parent_provenance_ids: tuple[UUIDv7, ...]
    evidence_classification: EvidenceClassification

    created_at_utc: datetime

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer

    @field_validator("created_at_utc")
    @classmethod
    def _normalize_created_at(cls, value: datetime) -> datetime:
        return to_utc(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "ProvenanceRecord":
        if self.record_id == self.subject_record_id:
            raise ValueError("record_id must differ from subject_record_id.")

        if len(self.sources) == 0:
            raise ValueError("sources must contain at least one entry.")
        if len(set(self.sources)) != len(self.sources):
            raise ValueError("sources must not contain exact duplicate entries.")
        for source in self.sources:
            if source.source_record_id is not None and (
                source.source_record_id == self.record_id
                or source.source_record_id == self.subject_record_id
            ):
                raise ValueError(
                    "source_record_id may not equal record_id or subject_record_id."
                )

        if len(set(self.parent_provenance_ids)) != len(self.parent_provenance_ids):
            raise ValueError("parent_provenance_ids must contain unique values.")
        if self.record_id in self.parent_provenance_ids:
            raise ValueError("record_id may not appear in parent_provenance_ids.")

        return self
