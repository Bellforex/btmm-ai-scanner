import socket
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.ingestion.offline_file_source import OfflineFileSource
from btmm_ai_scanner.ingestion.port import MarketDataSourcePort
from btmm_ai_scanner.ingestion.requests import SourceAcquisitionRequest
from btmm_ai_scanner.ingestion.results import SourceAcquisitionOutcome
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_SECOND_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd03")
_THIRD_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd04")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_SECOND_FINGERPRINT = "c" * 64
_THIRD_FINGERPRINT = "d" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)


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


def test_offline_file_source_returns_fixture_for_known_request() -> None:
    # MarketDataSourcePort is intentionally not @runtime_checkable, so
    # conformance is proven via the real inheritance relationship rather
    # than isinstance()/issubclass() (which raise TypeError for a
    # non-runtime-checkable Protocol regardless of actual inheritance).
    assert MarketDataSourcePort in OfflineFileSource.__mro__

    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    empty_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="fxcm-xauusd-m1-empty")
    )

    source = OfflineFileSource(
        {
            known_request: (candle_input,),
            empty_request: (),
        }
    )

    single_result = source.acquire(known_request)
    assert single_result.outcome == SourceAcquisitionOutcome.SUCCEEDED
    assert single_result.source_candle_inputs == (candle_input,)
    assert single_result.reason_codes == ()
    # Provider identity is preserved exactly as fixture-supplied — never
    # rewritten to the adapter/stub concept "OFFLINE_FILE".
    assert single_result.source_candle_inputs[0].provider == "FXCM"
    assert single_result.source_candle_inputs[0].provider != "OFFLINE_FILE"

    empty_result = source.acquire(empty_request)
    assert empty_result.outcome == SourceAcquisitionOutcome.SUCCEEDED
    assert empty_result.source_candle_inputs == ()
    assert empty_result.reason_codes == ()


def test_offline_file_source_returns_unsupported_for_unknown_request() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    source = OfflineFileSource({known_request: (candle_input,)})

    unknown_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="not-in-the-catalogue")
    )
    unknown_result = source.acquire(unknown_request)
    assert unknown_result.outcome == SourceAcquisitionOutcome.UNSUPPORTED
    assert unknown_result.source_candle_inputs == ()
    assert unknown_result.reason_codes == ("SOURCE_REQUEST_UNSUPPORTED",)

    # Catalogue lookup is case-sensitive: a request differing only by the
    # case of `provider` is treated as a distinct, unknown key.
    case_varied_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(provider="fxcm")
    )
    assert (
        source.acquire(case_varied_request).outcome
        == SourceAcquisitionOutcome.UNSUPPORTED
    )

    # Whitespace-normalized lookup: a request constructed with padded
    # whitespace is stripped before hashing/equality, so it matches the
    # already-known (unpadded) catalogue key exactly.
    padded_known_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(provider=" FXCM ")
    )
    padded_result = source.acquire(padded_known_request)
    assert padded_result.outcome == SourceAcquisitionOutcome.SUCCEEDED
    assert padded_result.source_candle_inputs == (candle_input,)


def test_offline_file_source_is_deterministic_across_repeated_calls() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    unknown_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="not-in-the-catalogue")
    )
    source = OfflineFileSource({known_request: (candle_input,)})

    first_known = source.acquire(known_request)
    second_known = source.acquire(known_request)
    assert first_known == second_known

    first_unknown = source.acquire(unknown_request)
    second_unknown = source.acquire(unknown_request)
    assert first_unknown == second_unknown


def test_offline_file_source_preserves_source_candle_input_ordering() -> None:
    first = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    second = SourceCandleInput.model_validate(
        _valid_source_candle_input_kwargs(
            record_id=_SECOND_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            source_timeframe="M5",
        )
    )
    third = SourceCandleInput.model_validate(
        _valid_source_candle_input_kwargs(
            record_id=_THIRD_RECORD_ID,
            content_fingerprint=_THIRD_FINGERPRINT,
            source_timeframe="H1",
        )
    )
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())

    source = OfflineFileSource({known_request: (third, first, second)})
    result = source.acquire(known_request)

    assert result.source_candle_inputs == (third, first, second)
    assert [candle.source_timeframe for candle in result.source_candle_inputs] == [
        "H1",
        "M1",
        "M5",
    ]


def test_offline_file_source_never_generates_replacement_values() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())

    source = OfflineFileSource({known_request: (candle_input,)})
    result = source.acquire(known_request)

    # The exact fixture-supplied field values are echoed back unchanged —
    # never regenerated — so no new record_id, content_fingerprint, version,
    # or provenance_id was ever produced. (`ContractModel.revalidate_instances
    # == "always"` means the returned object is re-validated into a new
    # Python instance, so object identity is not the right proof here;
    # exact field-value equality is.)
    returned_candle_input = result.source_candle_inputs[0]
    assert returned_candle_input == candle_input
    assert returned_candle_input.record_id == candle_input.record_id
    assert returned_candle_input.content_fingerprint == candle_input.content_fingerprint
    assert returned_candle_input.rule_version == candle_input.rule_version
    assert returned_candle_input.contract_version == candle_input.contract_version
    assert returned_candle_input.schema_version == candle_input.schema_version
    assert returned_candle_input.provenance_id == candle_input.provenance_id


def test_offline_file_source_never_mutates_fixtures_or_request() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    unknown_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="not-in-the-catalogue")
    )

    caller_fixtures: dict[SourceAcquisitionRequest, tuple[SourceCandleInput, ...]] = {
        known_request: (candle_input,)
    }
    source = OfflineFileSource(caller_fixtures)

    # Caller-side mutation of the original mapping after construction cannot
    # affect the adapter's behavior.
    caller_fixtures[unknown_request] = ()
    caller_fixtures[known_request] = ()
    result = source.acquire(known_request)
    assert result.source_candle_inputs == (candle_input,)

    # Internal catalogue mutation is structurally prevented (MappingProxyType).
    with pytest.raises(TypeError):
        source._fixtures[known_request] = ()  # type: ignore[index]

    # request/candle objects remain frozen — acquire() never mutates them.
    with pytest.raises(ValidationError):
        known_request.provider = "OTHER"
    with pytest.raises(ValidationError):
        candle_input.open = Decimal("999")

    # The returned tuple itself cannot be modified.
    with pytest.raises(TypeError):
        result.source_candle_inputs[0] = candle_input  # type: ignore[index]


def test_offline_file_source_performs_no_file_or_network_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("no file or network access is permitted")

    monkeypatch.setattr("builtins.open", _raise_if_called)
    monkeypatch.setattr(socket.socket, "__init__", _raise_if_called)

    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    unknown_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="not-in-the-catalogue")
    )
    source = OfflineFileSource({known_request: (candle_input,)})

    known_result = source.acquire(known_request)
    assert known_result.outcome == SourceAcquisitionOutcome.SUCCEEDED

    unknown_result = source.acquire(unknown_request)
    assert unknown_result.outcome == SourceAcquisitionOutcome.UNSUPPORTED


def test_offline_file_source_never_constructs_raw_or_normalized_candles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _raise_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("RawCandle/NormalizedCandle must never be constructed")

    monkeypatch.setattr(RawCandle, "__init__", _raise_if_called)
    monkeypatch.setattr(NormalizedCandle, "__init__", _raise_if_called)

    candle_input = SourceCandleInput.model_validate(_valid_source_candle_input_kwargs())
    known_request = SourceAcquisitionRequest.model_validate(_valid_request_kwargs())
    unknown_request = SourceAcquisitionRequest.model_validate(
        _valid_request_kwargs(source_reference="not-in-the-catalogue")
    )
    source = OfflineFileSource({known_request: (candle_input,)})

    known_result = source.acquire(known_request)
    assert known_result.outcome == SourceAcquisitionOutcome.SUCCEEDED

    unknown_result = source.acquire(unknown_request)
    assert unknown_result.outcome == SourceAcquisitionOutcome.UNSUPPORTED
