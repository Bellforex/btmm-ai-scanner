from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdef")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)

_EXPECTED_FIELD_NAMES = {
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


def _valid_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "provider": "OFFLINE_FILE",
        "source_reference": "reference-001",
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


def test_raw_candle_accepts_valid_contract() -> None:
    candle = RawCandle.model_validate(_valid_kwargs())
    assert candle.record_id == _RECORD_ID


def test_raw_candle_requires_exact_field_set() -> None:
    assert set(RawCandle.model_fields) == _EXPECTED_FIELD_NAMES


def test_raw_candle_is_frozen() -> None:
    candle = RawCandle.model_validate(_valid_kwargs())
    with pytest.raises(ValidationError):
        candle.open = Decimal("200.0")


def test_raw_candle_rejects_extra_fields() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(unexpected_field=1))


@pytest.mark.parametrize("bad_value", ["100.0", 100, 100.0])
def test_raw_candle_requires_strict_decimal_inputs(bad_value: object) -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(open=bad_value))


@pytest.mark.parametrize("bad_price", [Decimal("0"), Decimal("-1")])
def test_raw_candle_rejects_nonpositive_prices(bad_price: Decimal) -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(open=bad_price))


def test_raw_candle_enforces_ohlc_bounds() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(open=Decimal("102.0")))
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(close=Decimal("99.0")))


def test_raw_candle_validates_volume_kind_and_value() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(
            _valid_kwargs(volume_kind=CandleVolumeKind.TICK, volume=None)
        )
    with pytest.raises(ValidationError):
        RawCandle.model_validate(
            _valid_kwargs(volume_kind=CandleVolumeKind.TRADE, volume=None)
        )
    unknown_none = RawCandle.model_validate(
        _valid_kwargs(volume_kind=CandleVolumeKind.UNKNOWN, volume=None)
    )
    assert unknown_none.volume is None
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(volume=Decimal("-1")))


def test_raw_candle_validates_completeness_values() -> None:
    for value in CandleCompleteness:
        candle = RawCandle.model_validate(_valid_kwargs(completeness=value))
        assert candle.completeness == value
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(completeness="NOT_A_VALUE"))


def test_raw_candle_rejects_naive_timestamps() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(event_time_utc=datetime(2026, 1, 1)))
    with pytest.raises(ValidationError):
        RawCandle.model_validate(
            _valid_kwargs(original_event_time=datetime(2026, 1, 1))
        )


def test_raw_candle_normalizes_aware_canonical_times_to_utc() -> None:
    offset_zone = timezone(timedelta(hours=2))
    event_local = _EVENT_TIME.astimezone(offset_zone)
    candle = RawCandle.model_validate(
        _valid_kwargs(event_time_utc=event_local, original_event_time=event_local)
    )
    assert candle.event_time_utc == _EVENT_TIME
    assert candle.event_time_utc.tzinfo == UTC


def test_raw_candle_preserves_original_timestamp_offsets() -> None:
    offset_zone = timezone(timedelta(hours=2))
    event_local = _EVENT_TIME.astimezone(offset_zone)
    candle = RawCandle.model_validate(
        _valid_kwargs(event_time_utc=event_local, original_event_time=event_local)
    )
    assert candle.original_event_time.utcoffset() == timedelta(hours=2)


def test_raw_candle_requires_original_and_utc_instants_to_match() -> None:
    mismatched = _EVENT_TIME + timedelta(hours=1)
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(original_event_time=mismatched))


def test_raw_candle_requires_event_before_availability() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(
            _valid_kwargs(
                availability_time_utc=_EVENT_TIME,
                original_availability_time=_EVENT_TIME,
            )
        )


def test_raw_candle_requires_processing_not_before_event() -> None:
    before_event = _EVENT_TIME - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(processing_time_utc=before_event))


def test_raw_candle_rejects_complete_status_before_availability() -> None:
    before_availability = _AVAILABILITY_TIME - timedelta(seconds=1)
    with pytest.raises(ValidationError):
        RawCandle.model_validate(
            _valid_kwargs(
                processing_time_utc=before_availability,
                completeness=CandleCompleteness.CONFIRMED_COMPLETE,
            )
        )
    incomplete = RawCandle.model_validate(
        _valid_kwargs(
            processing_time_utc=before_availability,
            completeness=CandleCompleteness.INCOMPLETE,
        )
    )
    assert incomplete.completeness == CandleCompleteness.INCOMPLETE


@pytest.mark.parametrize("bad_value", ["", "   ", " reference-001", "reference-001 "])
def test_raw_candle_rejects_blank_or_padded_source_text(bad_value: str) -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(source_reference=bad_value))


def test_raw_candle_requires_version_and_provenance_types() -> None:
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(rule_version="not-a-version"))
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(rule_version=123))
    with pytest.raises(ValidationError):
        RawCandle.model_validate(_valid_kwargs(provenance_id="not-a-uuid"))


def test_raw_candle_round_trips_through_json() -> None:
    candle = RawCandle.model_validate(_valid_kwargs())
    restored = RawCandle.model_validate_json(candle.model_dump_json())
    assert restored == candle
