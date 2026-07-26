import inspect
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.ingestion.port import MarketDataSourcePort
from btmm_ai_scanner.ingestion.requests import SourceAcquisitionRequest
from btmm_ai_scanner.ingestion.results import (
    SourceAcquisitionOutcome,
    SourceAcquisitionResult,
)
from btmm_ai_scanner.market_data.results import IngestionOutcome
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_SECOND_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd03")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_SECOND_FINGERPRINT = "c" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)

_MARKET_DATA_REASON_CODES = {
    "AVAILABILITY_TIME_UNAVAILABLE",
    "AVAILABILITY_TIME_PAIR_INCONSISTENT",
    "AVAILABILITY_TIME_INVALID",
    "RAW_CANDLE_VALIDATION_FAILED",
    "UNSUPPORTED_PROVIDER",
    "UNSUPPORTED_PROVIDER_SYMBOL",
    "UNSUPPORTED_PROVIDER_TIMEFRAME",
    "CONFLICTING_REVISION_DETECTED",
}


def _valid_request_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "provider": "FXCM",
        "source_reference": "fxcm-xauusd-m1",
        "source_symbol": "XAUUSD",
        "source_timeframe": "M1",
    }
    kwargs.update(overrides)
    return kwargs


def _valid_source_candle_input_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "provider": "FXCM",
        "source_reference": "fxcm-xauusd-m1",
        "source_symbol": "XAUUSD",
        "source_timeframe": "M1",
        "event_time_utc": _EVENT_TIME,
        "availability_time_utc": _AVAILABILITY_TIME,
        "processing_time_utc": _PROCESSING_TIME,
        "original_event_time": _EVENT_TIME,
        "original_availability_time": _AVAILABILITY_TIME,
        "original_timezone": "UTC",
        "open": Decimal("100.0"),
        "high": Decimal("101.0"),
        "low": Decimal("99.5"),
        "close": Decimal("100.5"),
        "volume": Decimal("10"),
        "volume_kind": CandleVolumeKind.TICK,
        "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
        "rule_version": SemVer.parse("0.1.0"),
        "contract_version": SemVer.parse("0.1.0"),
        "schema_version": SemVer.parse("0.1.0"),
        "provenance_id": _PROVENANCE_ID,
    }
    kwargs.update(overrides)
    return kwargs


def test_source_acquisition_request_accepts_valid_construction() -> None:
    request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    assert request.provider == "FXCM"
    assert request.source_reference == "fxcm-xauusd-m1"
    assert request.source_symbol == "XAUUSD"
    assert request.source_timeframe == "M1"

    # Leading/trailing whitespace is stripped during construction.
    padded = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(provider=" FXCM ")
    )
    assert padded.provider == "FXCM"

    # Matching is case-sensitive: no upper/lower/casefold normalization occurs
    # anywhere in construction or equality.
    lowercase_provider = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(provider="fxcm")
    )
    assert lowercase_provider.provider == "fxcm"
    assert lowercase_provider.provider != request.provider
    assert lowercase_provider != request

    lowercase_symbol = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_symbol="xauusd")
    )
    assert lowercase_symbol.source_symbol == "xauusd"
    assert lowercase_symbol.source_symbol != request.source_symbol
    assert lowercase_symbol != request


def test_source_acquisition_request_is_frozen() -> None:
    request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    with pytest.raises(ValidationError):
        request.provider = "OTHER"


def test_source_acquisition_request_rejects_extra_fields_and_candle_content() -> None:
    with pytest.raises(ValidationError):
        SourceAcquisitionRequest.model_validate(
            _valid_request_kwargs(unexpected_field=1)
        )

    # No candle-content field exists on the model — supplying one is rejected
    # exactly like any other unknown extra field.
    candle_only_fields: dict[str, object] = {
        "open": Decimal("100.0"),
        "high": Decimal("101.0"),
        "low": Decimal("99.0"),
        "close": Decimal("100.5"),
        "volume": Decimal("10"),
        "event_time_utc": _EVENT_TIME,
        "availability_time_utc": _EVENT_TIME,
        "processing_time_utc": _EVENT_TIME,
    }
    for field_name, field_value in candle_only_fields.items():
        with pytest.raises(ValidationError):
            SourceAcquisitionRequest.model_validate(
                _valid_request_kwargs(**{field_name: field_value})
            )

    # No default: omitting any required field is rejected.
    for field_name in (
        "provider",
        "source_reference",
        "source_symbol",
        "source_timeframe",
    ):
        kwargs = _valid_request_kwargs()
        del kwargs[field_name]
        with pytest.raises(ValidationError):
            SourceAcquisitionRequest.model_validate(kwargs)

    # Strict typing rejects non-string coercion.
    with pytest.raises(ValidationError):
        SourceAcquisitionRequest.model_validate(_valid_request_kwargs(provider=123))

    # Nonblank validation rejects empty and whitespace-only values.
    with pytest.raises(ValidationError):
        SourceAcquisitionRequest.model_validate(_valid_request_kwargs(provider=""))
    with pytest.raises(ValidationError):
        SourceAcquisitionRequest.model_validate(_valid_request_kwargs(provider="   "))


def test_source_acquisition_result_enforces_outcome_matrix() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())

    succeeded = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.SUCCEEDED,
            "source_candle_inputs": (candle_input,),
            "reason_codes": (),
        }
    )
    assert succeeded.outcome == SourceAcquisitionOutcome.SUCCEEDED

    unsupported = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.UNSUPPORTED,
            "source_candle_inputs": (),
            "reason_codes": ("SOURCE_REQUEST_UNSUPPORTED",),
        }
    )
    assert unsupported.outcome == SourceAcquisitionOutcome.UNSUPPORTED

    failed = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.FAILED,
            "source_candle_inputs": (),
            "reason_codes": ("SOURCE_ACQUISITION_FAILED",),
        }
    )
    assert failed.outcome == SourceAcquisitionOutcome.FAILED

    # SUCCEEDED must not carry a reason code.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.SUCCEEDED,
                "source_candle_inputs": (),
                "reason_codes": ("SOURCE_REQUEST_UNSUPPORTED",),
            }
        )

    # UNSUPPORTED must not carry source_candle_inputs.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.UNSUPPORTED,
                "source_candle_inputs": (candle_input,),
                "reason_codes": ("SOURCE_REQUEST_UNSUPPORTED",),
            }
        )

    # UNSUPPORTED with the swapped (FAILED) reason code is invalid.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.UNSUPPORTED,
                "source_candle_inputs": (),
                "reason_codes": ("SOURCE_ACQUISITION_FAILED",),
            }
        )

    # UNSUPPORTED with no reason code at all is invalid.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.UNSUPPORTED,
                "source_candle_inputs": (),
                "reason_codes": (),
            }
        )

    # FAILED must not carry source_candle_inputs.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.FAILED,
                "source_candle_inputs": (candle_input,),
                "reason_codes": ("SOURCE_ACQUISITION_FAILED",),
            }
        )

    # FAILED with the swapped (UNSUPPORTED) reason code is invalid.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.FAILED,
                "source_candle_inputs": (),
                "reason_codes": ("SOURCE_REQUEST_UNSUPPORTED",),
            }
        )

    # An arbitrary, non-approved reason code is rejected regardless of outcome.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.FAILED,
                "source_candle_inputs": (),
                "reason_codes": ("SOMETHING_ELSE_ENTIRELY",),
            }
        )

    # Missing required fields are rejected (no defaults).
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "source_candle_inputs": (),
                "reason_codes": (),
            }
        )

    # Extra fields are rejected.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.SUCCEEDED,
                "source_candle_inputs": (),
                "reason_codes": (),
                "unexpected_field": 1,
            }
        )


def test_source_acquisition_result_succeeded_may_carry_multiple_source_candle_inputs() -> (
    None
):
    first = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    second = SourceCandleInput.model_validate(
        _valid_source_candle_input_kwargs(
            record_id=_SECOND_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            source_timeframe="M5",
        )
    )

    result = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.SUCCEEDED,
            "source_candle_inputs": (first, second),
            "reason_codes": (),
        }
    )
    assert result.source_candle_inputs == (first, second)
    assert isinstance(result.source_candle_inputs, tuple)
    assert len(result.source_candle_inputs) == 2

    with pytest.raises(ValidationError):
        result.source_candle_inputs = (first,)


def test_source_acquisition_result_distinguishes_empty_success_from_failure() -> None:
    empty_success = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.SUCCEEDED,
            "source_candle_inputs": (),
            "reason_codes": (),
        }
    )
    assert empty_success.outcome == SourceAcquisitionOutcome.SUCCEEDED
    assert empty_success.source_candle_inputs == ()
    assert empty_success.reason_codes == ()

    unsupported = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.UNSUPPORTED,
            "source_candle_inputs": (),
            "reason_codes": ("SOURCE_REQUEST_UNSUPPORTED",),
        }
    )
    failed = SourceAcquisitionResult.model_validate(
        {
            "outcome": SourceAcquisitionOutcome.FAILED,
            "source_candle_inputs": (),
            "reason_codes": ("SOURCE_ACQUISITION_FAILED",),
        }
    )

    assert empty_success.outcome != unsupported.outcome
    assert empty_success.outcome != failed.outcome
    assert empty_success != unsupported
    assert empty_success != failed

    # A successful-but-empty acquisition must never be constructible with a
    # failure reason code, and a failure outcome must never be constructible
    # with an empty reason_codes tuple.
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.SUCCEEDED,
                "source_candle_inputs": (),
                "reason_codes": ("SOURCE_ACQUISITION_FAILED",),
            }
        )
    with pytest.raises(ValidationError):
        SourceAcquisitionResult.model_validate(
            {
                "outcome": SourceAcquisitionOutcome.FAILED,
                "source_candle_inputs": (),
                "reason_codes": (),
            }
        )


def test_source_acquisition_outcome_and_reason_codes_do_not_duplicate_market_data_vocabulary() -> (
    None
):
    assert {member.value for member in SourceAcquisitionOutcome} == {
        "SUCCEEDED",
        "UNSUPPORTED",
        "FAILED",
    }
    assert {member.value for member in SourceAcquisitionOutcome}.isdisjoint(
        {member.value for member in IngestionOutcome}
    )

    source_level_codes = {"SOURCE_REQUEST_UNSUPPORTED", "SOURCE_ACQUISITION_FAILED"}
    assert source_level_codes.isdisjoint(_MARKET_DATA_REASON_CODES)


def test_market_data_source_port_protocol_conformance() -> None:
    assert getattr(MarketDataSourcePort, "_is_protocol", False) is True

    # A Protocol cannot be instantiated directly — it carries no concrete
    # implementation behavior.
    with pytest.raises(TypeError):
        MarketDataSourcePort()  # type: ignore[misc]

    # Not runtime-checkable: isinstance() against a non-@runtime_checkable
    # Protocol raises TypeError rather than performing structural matching.
    with pytest.raises(TypeError):
        isinstance(object(), MarketDataSourcePort)  # type: ignore[misc]

    signature = inspect.signature(MarketDataSourcePort.acquire)
    assert list(signature.parameters) == ["self", "request"]
    assert signature.parameters["request"].annotation is SourceAcquisitionRequest
    assert signature.return_annotation is SourceAcquisitionResult

    assert not inspect.iscoroutinefunction(MarketDataSourcePort.acquire)
    assert not inspect.isgeneratorfunction(MarketDataSourcePort.acquire)
    assert not inspect.isasyncgenfunction(MarketDataSourcePort.acquire)

    # No Protocol state: the only public attribute is the abstract method
    # itself — no constructor, no networking/filesystem/database type, no
    # RawCandle/NormalizedCandle type anywhere in the signature.
    public_attrs = [
        name for name in vars(MarketDataSourcePort) if not name.startswith("_")
    ]
    assert public_attrs == ["acquire"]
