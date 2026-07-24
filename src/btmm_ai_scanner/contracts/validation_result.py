import re
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

_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


class ValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    INDETERMINATE = "INDETERMINATE"


class AnalyticalEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNDETERMINED = "UNDETERMINED"


_PERMITTED_ELIGIBILITY_BY_STATUS = {
    ValidationStatus.VALID: frozenset(
        {
            AnalyticalEligibility.ELIGIBLE,
            AnalyticalEligibility.INELIGIBLE,
            AnalyticalEligibility.UNDETERMINED,
        }
    ),
    ValidationStatus.INVALID: frozenset({AnalyticalEligibility.INELIGIBLE}),
    ValidationStatus.INDETERMINATE: frozenset({AnalyticalEligibility.UNDETERMINED}),
}


class ValidationResult(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    subject_record_id: UUIDv7

    validation_profile: str
    status: ValidationStatus
    analytical_eligibility: AnalyticalEligibility
    reason_codes: tuple[str, ...]

    evaluated_at_utc: datetime

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    provenance_id: UUIDv7

    @field_validator("validation_profile")
    @classmethod
    def _validate_validation_profile(cls, value: str) -> str:
        if value == "" or value.strip() != value:
            raise ValueError(
                "validation_profile must be nonblank and must not have leading"
                " or trailing whitespace."
            )
        return value

    @field_validator("reason_codes")
    @classmethod
    def _validate_reason_codes(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if len(set(value)) != len(value):
            raise ValueError("reason_codes must not contain duplicate values.")
        for code in value:
            if _REASON_CODE_PATTERN.fullmatch(code) is None:
                raise ValueError(
                    f"{code!r} does not match the required reason-code pattern"
                    " ^[A-Z][A-Z0-9_]*$."
                )
        return value

    @field_validator("evaluated_at_utc")
    @classmethod
    def _normalize_evaluated_at(cls, value: datetime) -> datetime:
        return to_utc(value)

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "ValidationResult":
        if self.record_id == self.subject_record_id:
            raise ValueError("record_id must differ from subject_record_id.")

        permitted = _PERMITTED_ELIGIBILITY_BY_STATUS[self.status]
        if self.analytical_eligibility not in permitted:
            raise ValueError(
                f"analytical_eligibility {self.analytical_eligibility!r} is not"
                f" permitted for status {self.status!r}."
            )

        requires_reason = not (
            self.status == ValidationStatus.VALID
            and self.analytical_eligibility == AnalyticalEligibility.ELIGIBLE
        )
        if requires_reason and len(self.reason_codes) == 0:
            raise ValueError(
                "reason_codes must contain at least one entry unless status is"
                " VALID and analytical_eligibility is ELIGIBLE."
            )
        return self
