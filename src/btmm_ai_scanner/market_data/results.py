import re
from enum import StrEnum

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import RawCandle
from btmm_ai_scanner.contracts.types import ContractModel, UUIDv7

_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


class IngestionOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INDETERMINATE = "INDETERMINATE"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_REVISION = "CONFLICTING_REVISION"


class IngestionResult(ContractModel):
    outcome: IngestionOutcome
    reason_codes: tuple[str, ...]
    candidate_raw_candle: RawCandle | None
    candidate_normalized_candle: NormalizedCandle | None
    existing_record_id: UUIDv7 | None

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

    @model_validator(mode="after")
    def _validate_outcome_matrix(self) -> "IngestionResult":
        if self.outcome == IngestionOutcome.ACCEPTED:
            if self.candidate_raw_candle is None:
                raise ValueError("ACCEPTED requires candidate_raw_candle.")
            if self.existing_record_id is not None:
                raise ValueError("ACCEPTED must not set existing_record_id.")
            if self.reason_codes:
                raise ValueError("ACCEPTED must not carry reason_codes.")
            if (
                self.candidate_normalized_candle is not None
                and self.candidate_normalized_candle.raw_candle_id
                != self.candidate_raw_candle.record_id
            ):
                raise ValueError(
                    "candidate_normalized_candle.raw_candle_id must equal"
                    " candidate_raw_candle.record_id."
                )
        elif self.outcome == IngestionOutcome.REJECTED:
            if not self.reason_codes:
                raise ValueError("REJECTED requires at least one reason code.")
            if self.candidate_normalized_candle is not None:
                raise ValueError("REJECTED must not carry candidate_normalized_candle.")
            if self.existing_record_id is not None:
                raise ValueError("REJECTED must not set existing_record_id.")
        elif self.outcome == IngestionOutcome.INDETERMINATE:
            if not self.reason_codes:
                raise ValueError("INDETERMINATE requires at least one reason code.")
            if self.candidate_normalized_candle is not None:
                raise ValueError(
                    "INDETERMINATE must not carry candidate_normalized_candle."
                )
            if self.existing_record_id is not None:
                raise ValueError("INDETERMINATE must not set existing_record_id.")
            if self.candidate_raw_candle is not None:
                raise ValueError("INDETERMINATE must not carry candidate_raw_candle.")
        elif self.outcome == IngestionOutcome.EXACT_DUPLICATE:
            if self.candidate_raw_candle is None:
                raise ValueError("EXACT_DUPLICATE requires candidate_raw_candle.")
            if self.candidate_normalized_candle is not None:
                raise ValueError(
                    "EXACT_DUPLICATE must not carry candidate_normalized_candle."
                )
            if self.existing_record_id is None:
                raise ValueError("EXACT_DUPLICATE requires existing_record_id.")
        elif self.outcome == IngestionOutcome.CONFLICTING_REVISION:
            if self.candidate_raw_candle is None:
                raise ValueError("CONFLICTING_REVISION requires candidate_raw_candle.")
            if self.candidate_normalized_candle is not None:
                raise ValueError(
                    "CONFLICTING_REVISION must not carry candidate_normalized_candle."
                )
            if self.existing_record_id is None:
                raise ValueError("CONFLICTING_REVISION requires existing_record_id.")
            if "CONFLICTING_REVISION_DETECTED" not in self.reason_codes:
                raise ValueError(
                    "CONFLICTING_REVISION requires CONFLICTING_REVISION_DETECTED in"
                    " reason_codes."
                )
        return self
