import re
from enum import StrEnum

from pydantic import field_validator, model_validator

from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_REASON_CODE_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

_UNSUPPORTED_REASON_CODES: tuple[str, ...] = ("SOURCE_REQUEST_UNSUPPORTED",)
_FAILED_REASON_CODES: tuple[str, ...] = ("SOURCE_ACQUISITION_FAILED",)


class SourceAcquisitionOutcome(StrEnum):
    SUCCEEDED = "SUCCEEDED"
    UNSUPPORTED = "UNSUPPORTED"
    FAILED = "FAILED"


class SourceAcquisitionResult(ContractModel):
    outcome: SourceAcquisitionOutcome
    source_candle_inputs: tuple[SourceCandleInput, ...]
    reason_codes: tuple[str, ...]

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
    def _validate_outcome_matrix(self) -> "SourceAcquisitionResult":
        if self.outcome == SourceAcquisitionOutcome.SUCCEEDED:
            if self.reason_codes:
                raise ValueError("SUCCEEDED must not carry reason_codes.")
        elif self.outcome == SourceAcquisitionOutcome.UNSUPPORTED:
            if self.source_candle_inputs:
                raise ValueError("UNSUPPORTED must not carry source_candle_inputs.")
            if self.reason_codes != _UNSUPPORTED_REASON_CODES:
                raise ValueError(
                    "UNSUPPORTED requires reason_codes to equal exactly"
                    f" {_UNSUPPORTED_REASON_CODES!r}."
                )
        elif self.outcome == SourceAcquisitionOutcome.FAILED:
            if self.source_candle_inputs:
                raise ValueError("FAILED must not carry source_candle_inputs.")
            if self.reason_codes != _FAILED_REASON_CODES:
                raise ValueError(
                    "FAILED requires reason_codes to equal exactly"
                    f" {_FAILED_REASON_CODES!r}."
                )
        return self
