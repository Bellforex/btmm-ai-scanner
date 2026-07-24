from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.rule_version_manifest import (
    CompatibilityClass,
    RuleVersionManifest,
)
from btmm_ai_scanner.contracts.schema_version_manifest import SchemaVersionManifest
from btmm_ai_scanner.contracts.types import SemVer

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_SUPERSEDED_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_EFFECTIVE_AT = datetime(2026, 1, 1, tzinfo=UTC)

_RULE_MANIFEST_FIELD_NAMES = {
    "record_id",
    "content_fingerprint",
    "rule_set_name",
    "rule_version",
    "previous_rule_version",
    "compatibility_with_previous",
    "supersedes_manifest_id",
    "effective_at_utc",
    "evidence_classification",
    "manifest_contract_version",
    "manifest_schema_version",
    "provenance_id",
}

_SCHEMA_MANIFEST_FIELD_NAMES = {
    "record_id",
    "content_fingerprint",
    "schema_name",
    "schema_version",
    "previous_schema_version",
    "compatibility_with_previous",
    "supersedes_manifest_id",
    "effective_at_utc",
    "target_contract_name",
    "target_contract_version",
    "evidence_classification",
    "manifest_contract_version",
    "manifest_schema_version",
    "provenance_id",
}


def _valid_rule_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "rule_set_name": "btmm-core",
        "rule_version": SemVer.parse("0.1.0"),
        "previous_rule_version": None,
        "compatibility_with_previous": CompatibilityClass.UNKNOWN,
        "supersedes_manifest_id": None,
        "effective_at_utc": _EFFECTIVE_AT,
        "evidence_classification": EvidenceClassification.AUTHOR_APPROVED,
        "manifest_contract_version": SemVer.parse("0.1.0"),
        "manifest_schema_version": SemVer.parse("0.1.0"),
        "provenance_id": _PROVENANCE_ID,
    }
    kwargs.update(overrides)
    return kwargs


def _valid_schema_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "schema_name": "raw_candle_schema",
        "schema_version": SemVer.parse("0.1.0"),
        "previous_schema_version": None,
        "compatibility_with_previous": CompatibilityClass.UNKNOWN,
        "supersedes_manifest_id": None,
        "effective_at_utc": _EFFECTIVE_AT,
        "target_contract_name": "RawCandle",
        "target_contract_version": SemVer.parse("0.1.0"),
        "evidence_classification": EvidenceClassification.AUTHOR_APPROVED,
        "manifest_contract_version": SemVer.parse("0.1.0"),
        "manifest_schema_version": SemVer.parse("0.1.0"),
        "provenance_id": _PROVENANCE_ID,
    }
    kwargs.update(overrides)
    return kwargs


def test_compatibility_class_values_are_exact() -> None:
    assert {member.value for member in CompatibilityClass} == {
        "FULLY_COMPATIBLE",
        "BACKWARD_COMPATIBLE",
        "FORWARD_COMPATIBLE",
        "INCOMPATIBLE",
        "UNKNOWN",
    }


def test_rule_version_manifest_accepts_initial_manifest() -> None:
    manifest = RuleVersionManifest.model_validate(_valid_rule_kwargs())
    assert manifest.previous_rule_version is None
    assert manifest.supersedes_manifest_id is None
    assert manifest.compatibility_with_previous == CompatibilityClass.UNKNOWN


def test_rule_version_manifest_accepts_successor_manifest() -> None:
    for previous_text, current_text in [
        ("0.1.0", "0.1.1"),
        ("0.1.0", "0.2.0"),
        ("0.9.0", "1.0.0"),
    ]:
        manifest = RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                previous_rule_version=SemVer.parse(previous_text),
                rule_version=SemVer.parse(current_text),
                compatibility_with_previous=CompatibilityClass.BACKWARD_COMPATIBLE,
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )
        assert manifest.rule_version == SemVer.parse(current_text)


def test_rule_version_manifest_requires_exact_field_set() -> None:
    assert set(RuleVersionManifest.model_fields) == _RULE_MANIFEST_FIELD_NAMES


def test_rule_version_manifest_is_frozen() -> None:
    manifest = RuleVersionManifest.model_validate(_valid_rule_kwargs())
    with pytest.raises(ValidationError):
        manifest.rule_set_name = "changed"


def test_rule_version_manifest_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(_valid_rule_kwargs(unexpected_field=1))


@pytest.mark.parametrize("bad_value", ["", "   ", " btmm-core", "btmm-core "])
def test_rule_version_manifest_rejects_blank_or_padded_rule_set_name(
    bad_value: str,
) -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(_valid_rule_kwargs(rule_set_name=bad_value))


def test_rule_version_manifest_enforces_initial_reference_consistency() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(supersedes_manifest_id=_SUPERSEDED_ID)
        )
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                compatibility_with_previous=CompatibilityClass.FULLY_COMPATIBLE
            )
        )


def test_rule_version_manifest_enforces_successor_reference_consistency() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(previous_rule_version=SemVer.parse("0.1.0"))
        )
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(supersedes_manifest_id=_SUPERSEDED_ID)
        )


def test_rule_version_manifest_requires_increasing_rule_version() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                previous_rule_version=SemVer.parse("0.2.0"),
                rule_version=SemVer.parse("0.1.0"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )


def test_rule_version_manifest_rejects_equal_precedence_successor() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                previous_rule_version=SemVer.parse("0.1.0"),
                rule_version=SemVer.parse("0.1.0"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                previous_rule_version=SemVer.parse("1.0.0+build.1"),
                rule_version=SemVer.parse("1.0.0+build.2"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )


def test_rule_version_manifest_rejects_self_supersession() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(
                previous_rule_version=SemVer.parse("0.1.0"),
                rule_version=SemVer.parse("0.2.0"),
                supersedes_manifest_id=_RECORD_ID,
            )
        )


def test_rule_version_manifest_normalizes_effective_at_to_utc() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(effective_at_utc=datetime(2026, 1, 1))
        )
    offset_zone = timezone(timedelta(hours=4))
    local_time = _EFFECTIVE_AT.astimezone(offset_zone)
    manifest = RuleVersionManifest.model_validate(
        _valid_rule_kwargs(effective_at_utc=local_time)
    )
    assert manifest.effective_at_utc == _EFFECTIVE_AT
    assert manifest.effective_at_utc.tzinfo == UTC


def test_rule_version_manifest_requires_version_evidence_and_provenance_types() -> None:
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(rule_version="not-a-version")
        )
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(evidence_classification="NOT_A_VALUE")
        )
    with pytest.raises(ValidationError):
        RuleVersionManifest.model_validate(
            _valid_rule_kwargs(provenance_id="not-a-uuid")
        )
    for value in EvidenceClassification:
        manifest = RuleVersionManifest.model_validate(
            _valid_rule_kwargs(evidence_classification=value)
        )
        assert manifest.evidence_classification == value


def test_rule_version_manifest_round_trips_through_json() -> None:
    manifest = RuleVersionManifest.model_validate(_valid_rule_kwargs())
    restored = RuleVersionManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest


def test_schema_version_manifest_accepts_initial_manifest() -> None:
    manifest = SchemaVersionManifest.model_validate(_valid_schema_kwargs())
    assert manifest.previous_schema_version is None
    assert manifest.supersedes_manifest_id is None
    assert manifest.compatibility_with_previous == CompatibilityClass.UNKNOWN


def test_schema_version_manifest_accepts_successor_manifest() -> None:
    for previous_text, current_text in [
        ("0.1.0", "0.1.1"),
        ("0.1.0", "0.2.0"),
        ("0.9.0", "1.0.0"),
    ]:
        manifest = SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                previous_schema_version=SemVer.parse(previous_text),
                schema_version=SemVer.parse(current_text),
                compatibility_with_previous=CompatibilityClass.BACKWARD_COMPATIBLE,
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )
        assert manifest.schema_version == SemVer.parse(current_text)


def test_schema_version_manifest_requires_exact_field_set() -> None:
    assert set(SchemaVersionManifest.model_fields) == _SCHEMA_MANIFEST_FIELD_NAMES


def test_schema_version_manifest_is_frozen() -> None:
    manifest = SchemaVersionManifest.model_validate(_valid_schema_kwargs())
    with pytest.raises(ValidationError):
        manifest.schema_name = "changed"


def test_schema_version_manifest_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(_valid_schema_kwargs(unexpected_field=1))


@pytest.mark.parametrize("bad_value", ["", "   ", " name", "name "])
def test_schema_version_manifest_rejects_blank_or_padded_names(bad_value: str) -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(schema_name=bad_value)
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(target_contract_name=bad_value)
        )


def test_schema_version_manifest_enforces_initial_reference_consistency() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(supersedes_manifest_id=_SUPERSEDED_ID)
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                compatibility_with_previous=CompatibilityClass.FULLY_COMPATIBLE
            )
        )


def test_schema_version_manifest_enforces_successor_reference_consistency() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(previous_schema_version=SemVer.parse("0.1.0"))
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(supersedes_manifest_id=_SUPERSEDED_ID)
        )


def test_schema_version_manifest_requires_increasing_schema_version() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                previous_schema_version=SemVer.parse("0.2.0"),
                schema_version=SemVer.parse("0.1.0"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )


def test_schema_version_manifest_rejects_equal_precedence_successor() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                previous_schema_version=SemVer.parse("0.1.0"),
                schema_version=SemVer.parse("0.1.0"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                previous_schema_version=SemVer.parse("1.0.0+build.1"),
                schema_version=SemVer.parse("1.0.0+build.2"),
                supersedes_manifest_id=_SUPERSEDED_ID,
            )
        )


def test_schema_version_manifest_rejects_self_supersession() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(
                previous_schema_version=SemVer.parse("0.1.0"),
                schema_version=SemVer.parse("0.2.0"),
                supersedes_manifest_id=_RECORD_ID,
            )
        )


def test_schema_version_manifest_normalizes_effective_at_to_utc() -> None:
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(effective_at_utc=datetime(2026, 1, 1))
        )
    offset_zone = timezone(timedelta(hours=4))
    local_time = _EFFECTIVE_AT.astimezone(offset_zone)
    manifest = SchemaVersionManifest.model_validate(
        _valid_schema_kwargs(effective_at_utc=local_time)
    )
    assert manifest.effective_at_utc == _EFFECTIVE_AT
    assert manifest.effective_at_utc.tzinfo == UTC


def test_schema_version_manifest_requires_target_version_evidence_and_provenance_types() -> (
    None
):
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(target_contract_version="not-a-version")
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(evidence_classification="NOT_A_VALUE")
        )
    with pytest.raises(ValidationError):
        SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(provenance_id="not-a-uuid")
        )
    for value in EvidenceClassification:
        manifest = SchemaVersionManifest.model_validate(
            _valid_schema_kwargs(evidence_classification=value)
        )
        assert manifest.evidence_classification == value


def test_schema_version_manifest_round_trips_through_json() -> None:
    manifest = SchemaVersionManifest.model_validate(_valid_schema_kwargs())
    restored = SchemaVersionManifest.model_validate_json(manifest.model_dump_json())
    assert restored == manifest
