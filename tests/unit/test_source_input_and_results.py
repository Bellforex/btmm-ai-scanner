from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.results import IngestionOutcome, IngestionResult
from btmm_ai_scanner.market_data.source_input import SourceCandleInput

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_NORMALIZED_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd01")
_EXISTING_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd02")
_FINGERPRINT = "a" * 64
_NORMALIZED_FINGERPRINT = "b" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)

_NON_UTC_OFFSET = timedelta(hours=2)
_NON_UTC_TZ = timezone(_NON_UTC_OFFSET)

_EXPECTED_SOURCE_INPUT_FIELD_NAMES = {
    "record_id",
    "content_fingerprint",
    "provider",
    "source_reference",
    "source_symbol",
    "source_timeframe",
    "event_time_utc",
    "availability_time_utc",
    "processing_time_utc",
    "original_event_time",
    "original_availability_time",
    "original_timezone",
    "open",
    "high",
    "low",
    "close",
    "volume",
    "volume_kind",
    "completeness",
    "rule_version",
    "contract_version",
    "schema_version",
    "provenance_id",
}


def _valid_source_input_kwargs(**overrides: object) -> dict[str, object]:
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


def _valid_raw_candle_kwargs(**overrides: object) -> dict[str, object]:
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


def _valid_normalized_candle_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _NORMALIZED_RECORD_ID,
        "content_fingerprint": _NORMALIZED_FINGERPRINT,
        "raw_candle_id": _RECORD_ID,
        "provider": "FXCM",
        "source_reference": "fxcm-xauusd-m1",
        "source_symbol": "XAUUSD",
        "source_timeframe": "M1",
        "symbol": InternalSymbol.XAUUSD,
        "timeframe": Timeframe.M1,
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


def test_source_candle_input_accepts_valid_construction() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    assert candle_input.record_id == _RECORD_ID
    assert candle_input.availability_time_utc == _AVAILABILITY_TIME

    # Genuinely non-UTC (UTC+02:00) aware input: canonical fields must be
    # normalized to UTC while original fields retain the supplied offset.
    non_utc_event_time = _EVENT_TIME.astimezone(_NON_UTC_TZ)
    non_utc_availability_time = _AVAILABILITY_TIME.astimezone(_NON_UTC_TZ)
    non_utc_processing_time = _PROCESSING_TIME.astimezone(_NON_UTC_TZ)

    non_utc_candle_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            event_time_utc=non_utc_event_time,
            availability_time_utc=non_utc_availability_time,
            processing_time_utc=non_utc_processing_time,
            original_event_time=non_utc_event_time,
            original_availability_time=non_utc_availability_time,
            original_timezone="UTC+02:00",
        )
    )

    # Canonical fields are normalized to UTC (utcoffset == 0)...
    assert non_utc_candle_input.event_time_utc.utcoffset() == timedelta(0)
    assert non_utc_candle_input.availability_time_utc is not None
    assert non_utc_candle_input.availability_time_utc.utcoffset() == timedelta(0)
    assert non_utc_candle_input.processing_time_utc.utcoffset() == timedelta(0)
    # ...while representing the exact same instant as the UTC-supplied fixtures.
    assert non_utc_candle_input.event_time_utc == _EVENT_TIME
    assert non_utc_candle_input.availability_time_utc == _AVAILABILITY_TIME
    assert non_utc_candle_input.processing_time_utc == _PROCESSING_TIME

    # Original fields retain the caller-supplied non-UTC offset — they are
    # never silently converted to UTC — while still representing the same
    # instant as their canonical counterparts.
    assert non_utc_candle_input.original_event_time.utcoffset() == _NON_UTC_OFFSET
    assert non_utc_candle_input.original_availability_time is not None
    assert (
        non_utc_candle_input.original_availability_time.utcoffset() == _NON_UTC_OFFSET
    )
    assert non_utc_candle_input.original_event_time.astimezone(UTC) == _EVENT_TIME
    assert (
        non_utc_candle_input.original_availability_time.astimezone(UTC)
        == _AVAILABILITY_TIME
    )


def test_source_candle_input_requires_exact_field_set() -> None:
    assert set(SourceCandleInput.model_fields) == _EXPECTED_SOURCE_INPUT_FIELD_NAMES


def test_source_candle_input_is_frozen() -> None:
    candle_input = SourceCandleInput.model_validate(_valid_source_input_kwargs())
    with pytest.raises(ValidationError):
        candle_input.open = Decimal("200.0")


def test_source_candle_input_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SourceCandleInput.model_validate(_valid_source_input_kwargs(unexpected_field=1))


def test_source_candle_input_requires_availability_keys_present() -> None:
    kwargs = _valid_source_input_kwargs()
    del kwargs["availability_time_utc"]
    with pytest.raises(ValidationError):
        SourceCandleInput.model_validate(kwargs)

    kwargs = _valid_source_input_kwargs()
    del kwargs["original_availability_time"]
    with pytest.raises(ValidationError):
        SourceCandleInput.model_validate(kwargs)


def test_source_candle_input_accepts_both_availability_values_none() -> None:
    candle_input = SourceCandleInput.model_validate(
        _valid_source_input_kwargs(
            availability_time_utc=None, original_availability_time=None
        )
    )
    assert candle_input.availability_time_utc is None
    assert candle_input.original_availability_time is None


def test_source_candle_input_rejects_naive_availability_values() -> None:
    # Broadened beyond the two availability fields to cover every datetime
    # field capable of receiving a naive value: event_time_utc,
    # processing_time_utc, and original_event_time fail construction exactly
    # like the two availability fields, each in isolation (every other field
    # remains valid), and none of these cases ever reaches a raw-candle
    # builder — SourceCandleInput.model_validate raises before any builder
    # could be invoked.
    naive_time = datetime(2026, 1, 1, 0, 1, 0)
    naive_rejecting_fields = (
        "event_time_utc",
        "availability_time_utc",
        "processing_time_utc",
        "original_event_time",
        "original_availability_time",
    )
    for field_name in naive_rejecting_fields:
        with pytest.raises(ValidationError):
            SourceCandleInput.model_validate(
                _valid_source_input_kwargs(**{field_name: naive_time})
            )


def test_ingestion_outcome_and_result_values_are_exact() -> None:
    assert {member.value for member in IngestionOutcome} == {
        "ACCEPTED",
        "REJECTED",
        "INDETERMINATE",
        "EXACT_DUPLICATE",
        "CONFLICTING_REVISION",
    }

    raw_candle = RawCandle.model_validate(_valid_raw_candle_kwargs())
    normalized_candle = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs()
    )

    accepted = IngestionResult.model_validate(
        {
            "outcome": IngestionOutcome.ACCEPTED,
            "reason_codes": (),
            "candidate_raw_candle": raw_candle,
            "candidate_normalized_candle": normalized_candle,
            "existing_record_id": None,
        }
    )
    assert accepted.outcome == IngestionOutcome.ACCEPTED

    indeterminate = IngestionResult.model_validate(
        {
            "outcome": IngestionOutcome.INDETERMINATE,
            "reason_codes": ("AVAILABILITY_TIME_UNAVAILABLE",),
            "candidate_raw_candle": None,
            "candidate_normalized_candle": None,
            "existing_record_id": None,
        }
    )
    assert indeterminate.outcome == IngestionOutcome.INDETERMINATE

    exact_duplicate = IngestionResult.model_validate(
        {
            "outcome": IngestionOutcome.EXACT_DUPLICATE,
            "reason_codes": (),
            "candidate_raw_candle": raw_candle,
            "candidate_normalized_candle": None,
            "existing_record_id": _EXISTING_RECORD_ID,
        }
    )
    assert exact_duplicate.outcome == IngestionOutcome.EXACT_DUPLICATE

    conflicting = IngestionResult.model_validate(
        {
            "outcome": IngestionOutcome.CONFLICTING_REVISION,
            "reason_codes": ("CONFLICTING_REVISION_DETECTED",),
            "candidate_raw_candle": raw_candle,
            "candidate_normalized_candle": None,
            "existing_record_id": _EXISTING_RECORD_ID,
        }
    )
    assert conflicting.outcome == IngestionOutcome.CONFLICTING_REVISION

    # ACCEPTED without candidate_raw_candle is invalid.
    with pytest.raises(ValidationError):
        IngestionResult.model_validate(
            {
                "outcome": IngestionOutcome.ACCEPTED,
                "reason_codes": (),
                "candidate_raw_candle": None,
                "candidate_normalized_candle": None,
                "existing_record_id": None,
            }
        )

    # EXACT_DUPLICATE without existing_record_id is invalid.
    with pytest.raises(ValidationError):
        IngestionResult.model_validate(
            {
                "outcome": IngestionOutcome.EXACT_DUPLICATE,
                "reason_codes": (),
                "candidate_raw_candle": raw_candle,
                "candidate_normalized_candle": None,
                "existing_record_id": None,
            }
        )

    # REJECTED without a reason code is invalid.
    with pytest.raises(ValidationError):
        IngestionResult.model_validate(
            {
                "outcome": IngestionOutcome.REJECTED,
                "reason_codes": (),
                "candidate_raw_candle": None,
                "candidate_normalized_candle": None,
                "existing_record_id": None,
            }
        )

    # CONFLICTING_REVISION without CONFLICTING_REVISION_DETECTED is invalid.
    with pytest.raises(ValidationError):
        IngestionResult.model_validate(
            {
                "outcome": IngestionOutcome.CONFLICTING_REVISION,
                "reason_codes": (),
                "candidate_raw_candle": raw_candle,
                "candidate_normalized_candle": None,
                "existing_record_id": _EXISTING_RECORD_ID,
            }
        )
