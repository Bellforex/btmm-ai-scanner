from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.provenance_record import (
    EvidenceClassification,
    ProvenanceRecord,
    ProvenanceSourceReference,
)
from btmm_ai_scanner.contracts.types import SemVer

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_SUBJECT_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdaa")
_PARENT_ID_1 = UUID("0193f2c0-1234-7abc-8def-abcdefabcd01")
_PARENT_ID_2 = UUID("0193f2c0-1234-7abc-8def-abcdefabcd02")
_SOURCE_INTERNAL_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd03")
_FINGERPRINT = "a" * 64

_CREATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_SOURCE_REFERENCE_FIELD_NAMES = {
    "source_reference",
    "source_record_id",
    "source_version",
}

_PROVENANCE_RECORD_FIELD_NAMES = {
    "record_id",
    "content_fingerprint",
    "subject_record_id",
    "sources",
    "parent_provenance_ids",
    "evidence_classification",
    "created_at_utc",
    "rule_version",
    "contract_version",
    "schema_version",
}

_EXTERNAL_SOURCE = ProvenanceSourceReference(
    source_reference="Book Chapter 3",
    source_record_id=None,
    source_version=None,
)

_INTERNAL_SOURCE = ProvenanceSourceReference(
    source_reference="internal-rule-set",
    source_record_id=_SOURCE_INTERNAL_ID,
    source_version=SemVer.parse("0.1.0"),
)


def _valid_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "subject_record_id": _SUBJECT_ID,
        "sources": (_EXTERNAL_SOURCE,),
        "parent_provenance_ids": (),
        "evidence_classification": EvidenceClassification.BOOK_SOURCED,
        "created_at_utc": _CREATED_AT,
        "rule_version": SemVer.parse("0.1.0"),
        "contract_version": SemVer.parse("0.1.0"),
        "schema_version": SemVer.parse("0.1.0"),
    }
    kwargs.update(overrides)
    return kwargs


def test_provenance_source_reference_accepts_valid_values() -> None:
    assert _EXTERNAL_SOURCE.source_record_id is None
    assert _EXTERNAL_SOURCE.source_version is None
    assert _INTERNAL_SOURCE.source_record_id == _SOURCE_INTERNAL_ID
    assert _INTERNAL_SOURCE.source_version == SemVer.parse("0.1.0")


def test_provenance_source_reference_requires_exact_field_set() -> None:
    assert set(ProvenanceSourceReference.model_fields) == _SOURCE_REFERENCE_FIELD_NAMES


@pytest.mark.parametrize("bad_value", ["", "   ", " ref", "ref "])
def test_provenance_source_reference_rejects_blank_or_padded_reference(
    bad_value: str,
) -> None:
    with pytest.raises(ValidationError):
        ProvenanceSourceReference(
            source_reference=bad_value, source_record_id=None, source_version=None
        )


def test_provenance_record_accepts_valid_contract() -> None:
    record = ProvenanceRecord.model_validate(_valid_kwargs())
    assert record.record_id == _RECORD_ID


def test_provenance_record_requires_exact_field_set() -> None:
    assert set(ProvenanceRecord.model_fields) == _PROVENANCE_RECORD_FIELD_NAMES


def test_provenance_record_is_frozen() -> None:
    record = ProvenanceRecord.model_validate(_valid_kwargs())
    with pytest.raises(ValidationError):
        record.evidence_classification = EvidenceClassification.PRODUCTION_APPROVED


def test_provenance_record_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(_valid_kwargs(unexpected_field=1))


def test_provenance_record_requires_distinct_record_and_subject_ids() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(_valid_kwargs(subject_record_id=_RECORD_ID))


def test_provenance_record_requires_nonempty_sources() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(_valid_kwargs(sources=()))
    multiple = ProvenanceRecord.model_validate(
        _valid_kwargs(sources=(_EXTERNAL_SOURCE, _INTERNAL_SOURCE))
    )
    assert len(multiple.sources) == 2


def test_provenance_record_rejects_duplicate_sources() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(sources=(_EXTERNAL_SOURCE, _EXTERNAL_SOURCE))
        )


def test_provenance_record_rejects_self_source_references() -> None:
    self_referencing_record = ProvenanceSourceReference(
        source_reference="self",
        source_record_id=_RECORD_ID,
        source_version=None,
    )
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(sources=(self_referencing_record,))
        )
    self_referencing_subject = ProvenanceSourceReference(
        source_reference="self-subject",
        source_record_id=_SUBJECT_ID,
        source_version=None,
    )
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(sources=(self_referencing_subject,))
        )


def test_provenance_record_validates_evidence_classification() -> None:
    for value in EvidenceClassification:
        record = ProvenanceRecord.model_validate(
            _valid_kwargs(evidence_classification=value)
        )
        assert record.evidence_classification == value
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(evidence_classification="NOT_A_VALUE")
        )


def test_provenance_record_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(created_at_utc=datetime(2026, 1, 1))
        )


def test_provenance_record_normalizes_created_at_to_utc() -> None:
    offset_zone = timezone(timedelta(hours=3))
    local_time = _CREATED_AT.astimezone(offset_zone)
    record = ProvenanceRecord.model_validate(_valid_kwargs(created_at_utc=local_time))
    assert record.created_at_utc == _CREATED_AT
    assert record.created_at_utc.tzinfo == UTC


def test_provenance_record_validates_parent_provenance_ids() -> None:
    empty = ProvenanceRecord.model_validate(_valid_kwargs(parent_provenance_ids=()))
    assert empty.parent_provenance_ids == ()
    multiple = ProvenanceRecord.model_validate(
        _valid_kwargs(parent_provenance_ids=(_PARENT_ID_1, _PARENT_ID_2))
    )
    assert multiple.parent_provenance_ids == (_PARENT_ID_1, _PARENT_ID_2)
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(parent_provenance_ids=(_PARENT_ID_1, _PARENT_ID_1))
        )
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(
            _valid_kwargs(parent_provenance_ids=(_RECORD_ID,))
        )


def test_provenance_record_requires_version_types() -> None:
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(_valid_kwargs(rule_version="not-a-version"))
    with pytest.raises(ValidationError):
        ProvenanceRecord.model_validate(_valid_kwargs(rule_version=123))


def test_provenance_record_round_trips_through_json() -> None:
    record = ProvenanceRecord.model_validate(_valid_kwargs())
    restored = ProvenanceRecord.model_validate_json(record.model_dump_json())
    assert restored == record
