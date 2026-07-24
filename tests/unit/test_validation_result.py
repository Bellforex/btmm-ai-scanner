from datetime import UTC, datetime, timedelta, timezone
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.contracts.validation_result import (
    AnalyticalEligibility,
    ValidationResult,
    ValidationStatus,
)

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_SUBJECT_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_EVALUATED_AT = datetime(2026, 1, 1, tzinfo=UTC)

_EXPECTED_FIELD_NAMES = {
    "record_id",
    "content_fingerprint",
    "subject_record_id",
    "validation_profile",
    "status",
    "analytical_eligibility",
    "reason_codes",
    "evaluated_at_utc",
    "rule_version",
    "contract_version",
    "schema_version",
    "provenance_id",
}


def _valid_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "subject_record_id": _SUBJECT_ID,
        "validation_profile": "profile-001",
        "status": ValidationStatus.VALID,
        "analytical_eligibility": AnalyticalEligibility.ELIGIBLE,
        "reason_codes": (),
        "evaluated_at_utc": _EVALUATED_AT,
        "rule_version": SemVer.parse("0.1.0"),
        "contract_version": SemVer.parse("0.1.0"),
        "schema_version": SemVer.parse("0.1.0"),
        "provenance_id": _PROVENANCE_ID,
    }
    kwargs.update(overrides)
    return kwargs


def test_validation_result_accepts_valid_contract() -> None:
    result = ValidationResult.model_validate(_valid_kwargs())
    assert result.record_id == _RECORD_ID


def test_validation_result_requires_exact_field_set() -> None:
    assert set(ValidationResult.model_fields) == _EXPECTED_FIELD_NAMES


def test_validation_result_is_frozen() -> None:
    result = ValidationResult.model_validate(_valid_kwargs())
    with pytest.raises(ValidationError):
        result.status = ValidationStatus.INVALID


def test_validation_result_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(unexpected_field=1))


def test_validation_result_requires_distinct_record_and_subject_ids() -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(subject_record_id=_RECORD_ID))


@pytest.mark.parametrize("bad_value", ["", "   ", " profile", "profile "])
def test_validation_result_rejects_blank_or_padded_profile(bad_value: str) -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(validation_profile=bad_value))


def test_validation_result_validates_status_values() -> None:
    for value in ValidationStatus:
        permitted = {
            ValidationStatus.VALID: AnalyticalEligibility.ELIGIBLE,
            ValidationStatus.INVALID: AnalyticalEligibility.INELIGIBLE,
            ValidationStatus.INDETERMINATE: AnalyticalEligibility.UNDETERMINED,
        }[value]
        reasons = () if permitted == AnalyticalEligibility.ELIGIBLE else ("CODE_A",)
        result = ValidationResult.model_validate(
            _valid_kwargs(
                status=value, analytical_eligibility=permitted, reason_codes=reasons
            )
        )
        assert result.status == value
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(status="NOT_A_VALUE"))


def test_validation_result_validates_eligibility_values() -> None:
    for value in AnalyticalEligibility:
        status = (
            ValidationStatus.VALID
            if value != AnalyticalEligibility.UNDETERMINED
            else ValidationStatus.INDETERMINATE
        )
        reasons = () if value == AnalyticalEligibility.ELIGIBLE else ("CODE_A",)
        result = ValidationResult.model_validate(
            _valid_kwargs(
                status=status, analytical_eligibility=value, reason_codes=reasons
            )
        )
        assert result.analytical_eligibility == value
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(analytical_eligibility="NOT_A_VALUE")
        )


def test_validation_result_enforces_status_eligibility_consistency() -> None:
    ValidationResult.model_validate(
        _valid_kwargs(
            status=ValidationStatus.VALID,
            analytical_eligibility=AnalyticalEligibility.INELIGIBLE,
            reason_codes=("CODE_A",),
        )
    )
    ValidationResult.model_validate(
        _valid_kwargs(
            status=ValidationStatus.VALID,
            analytical_eligibility=AnalyticalEligibility.UNDETERMINED,
            reason_codes=("CODE_A",),
        )
    )
    ValidationResult.model_validate(
        _valid_kwargs(
            status=ValidationStatus.INVALID,
            analytical_eligibility=AnalyticalEligibility.INELIGIBLE,
            reason_codes=("CODE_A",),
        )
    )
    ValidationResult.model_validate(
        _valid_kwargs(
            status=ValidationStatus.INDETERMINATE,
            analytical_eligibility=AnalyticalEligibility.UNDETERMINED,
            reason_codes=("CODE_A",),
        )
    )
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.INVALID,
                analytical_eligibility=AnalyticalEligibility.ELIGIBLE,
                reason_codes=("CODE_A",),
            )
        )
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.INDETERMINATE,
                analytical_eligibility=AnalyticalEligibility.ELIGIBLE,
                reason_codes=("CODE_A",),
            )
        )


@pytest.mark.parametrize(
    "bad_code",
    ["lowercase", "1LEADINGDIGIT", "HAS SPACE", "", "trailing_lower_", " CODE_A"],
)
def test_validation_result_validates_reason_code_format(bad_code: str) -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.INVALID,
                analytical_eligibility=AnalyticalEligibility.INELIGIBLE,
                reason_codes=(bad_code,) if bad_code else ("",),
            )
        )


def test_validation_result_rejects_duplicate_reason_codes() -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.INVALID,
                analytical_eligibility=AnalyticalEligibility.INELIGIBLE,
                reason_codes=("CODE_A", "CODE_A"),
            )
        )


def test_validation_result_requires_reasons_for_noneligible_or_nonvalid_results() -> (
    None
):
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.INVALID,
                analytical_eligibility=AnalyticalEligibility.INELIGIBLE,
                reason_codes=(),
            )
        )
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(
                status=ValidationStatus.VALID,
                analytical_eligibility=AnalyticalEligibility.UNDETERMINED,
                reason_codes=(),
            )
        )
    accepted = ValidationResult.model_validate(_valid_kwargs())
    assert accepted.reason_codes == ()


def test_validation_result_rejects_naive_evaluated_at() -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(
            _valid_kwargs(evaluated_at_utc=datetime(2026, 1, 1))
        )


def test_validation_result_normalizes_evaluated_at_to_utc() -> None:
    offset_zone = timezone(timedelta(hours=-5))
    local_time = _EVALUATED_AT.astimezone(offset_zone)
    result = ValidationResult.model_validate(_valid_kwargs(evaluated_at_utc=local_time))
    assert result.evaluated_at_utc == _EVALUATED_AT
    assert result.evaluated_at_utc.tzinfo == UTC


def test_validation_result_requires_version_and_provenance_types() -> None:
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(rule_version="not-a-version"))
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(rule_version=123))
    with pytest.raises(ValidationError):
        ValidationResult.model_validate(_valid_kwargs(provenance_id="not-a-uuid"))


def test_validation_result_round_trips_through_json() -> None:
    result = ValidationResult.model_validate(_valid_kwargs())
    restored = ValidationResult.model_validate_json(result.model_dump_json())
    assert restored == result
