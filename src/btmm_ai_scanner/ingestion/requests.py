from pydantic import field_validator

from btmm_ai_scanner.contracts.types import ContractModel


def _require_nonblank_after_stripping(value: str) -> str:
    stripped = value.strip()
    if stripped == "":
        raise ValueError(
            "Value must be nonempty after stripping leading and trailing whitespace."
        )
    return stripped


class SourceAcquisitionRequest(ContractModel):
    provider: str
    source_reference: str
    source_symbol: str
    source_timeframe: str

    @field_validator(
        "provider", "source_reference", "source_symbol", "source_timeframe"
    )
    @classmethod
    def _validate_request_strings(cls, value: str) -> str:
        return _require_nonblank_after_stripping(value)
