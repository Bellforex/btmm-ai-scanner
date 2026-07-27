from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.ports import CandleReadRepository, RawCandleSink
from btmm_ai_scanner.market_data.raw_candle_repository import (
    InMemoryRawCandleRepository,
    InvalidTimeRangeError,
    RecordIdentityConflictError,
)

_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd01")
_SECOND_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd02")
_THIRD_RECORD_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcd03")
_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_SECOND_FINGERPRINT = "b" * 64
_THIRD_FINGERPRINT = "c" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)


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


def test_in_memory_raw_candle_repository_stores_and_finds_by_source_identity() -> None:
    repository = InMemoryRawCandleRepository()
    candle = RawCandle.model_validate(_valid_raw_candle_kwargs())
    repository.store_raw_candle(candle)

    found = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert found == (candle,)

    not_found = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME + timedelta(minutes=5)
    )
    assert not_found == ()


def test_in_memory_raw_candle_repository_preserves_conflicting_revisions() -> None:
    repository = InMemoryRawCandleRepository()
    original = RawCandle.model_validate(_valid_raw_candle_kwargs())

    # Case 3: different record_id, same source identity, same fingerprint —
    # the existing EXACT_DUPLICATE classification. Both remain stored and
    # query-visible; the repository does not collapse them.
    exact_duplicate = RawCandle.model_validate(
        _valid_raw_candle_kwargs(record_id=_SECOND_RECORD_ID)
    )
    repository.store_raw_candle(original)
    repository.store_raw_candle(exact_duplicate)
    found = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert set(found) == {original, exact_duplicate}

    # Case 4: different record_id, same source identity, different
    # fingerprint — the existing CONFLICTING_REVISION classification. Both
    # remain stored and query-visible; no automatic winner is chosen.
    conflicting_revision = RawCandle.model_validate(
        _valid_raw_candle_kwargs(
            record_id=_THIRD_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            close=Decimal("200.0"),
            high=Decimal("201.0"),
        )
    )
    repository.store_raw_candle(conflicting_revision)
    found = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert set(found) == {original, exact_duplicate, conflicting_revision}


def test_in_memory_raw_candle_repository_rejects_silent_overwrite_of_differing_content() -> (
    None
):
    repository = InMemoryRawCandleRepository()
    candle = RawCandle.model_validate(_valid_raw_candle_kwargs())
    repository.store_raw_candle(candle)

    # Case 1: same record_id, identical complete record — idempotent no-op.
    repository.store_raw_candle(candle)
    found = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert found == (candle,)

    # Case 2: same record_id, different complete record — never overwrite;
    # raises RecordIdentityConflictError; the repository remains unchanged.
    differing_content = RawCandle.model_validate(
        _valid_raw_candle_kwargs(content_fingerprint=_SECOND_FINGERPRINT)
    )
    with pytest.raises(RecordIdentityConflictError):
        repository.store_raw_candle(differing_content)

    found_after = repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert found_after == (candle,)


def test_in_memory_raw_candle_repository_range_query_boundary_is_half_open() -> None:
    repository = InMemoryRawCandleRepository()
    early = RawCandle.model_validate(
        _valid_raw_candle_kwargs(
            record_id=_RECORD_ID,
            event_time_utc=_EVENT_TIME,
            availability_time_utc=_EVENT_TIME + timedelta(minutes=1),
            processing_time_utc=_EVENT_TIME + timedelta(minutes=1, seconds=1),
            original_event_time=_EVENT_TIME,
            original_availability_time=_EVENT_TIME + timedelta(minutes=1),
        )
    )
    middle_time = _EVENT_TIME + timedelta(minutes=1)
    middle = RawCandle.model_validate(
        _valid_raw_candle_kwargs(
            record_id=_SECOND_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            event_time_utc=middle_time,
            availability_time_utc=middle_time + timedelta(minutes=1),
            processing_time_utc=middle_time + timedelta(minutes=1, seconds=1),
            original_event_time=middle_time,
            original_availability_time=middle_time + timedelta(minutes=1),
        )
    )
    late_time = _EVENT_TIME + timedelta(minutes=2)
    late = RawCandle.model_validate(
        _valid_raw_candle_kwargs(
            record_id=_THIRD_RECORD_ID,
            content_fingerprint=_THIRD_FINGERPRINT,
            event_time_utc=late_time,
            availability_time_utc=late_time + timedelta(minutes=1),
            processing_time_utc=late_time + timedelta(minutes=1, seconds=1),
            original_event_time=late_time,
            original_availability_time=late_time + timedelta(minutes=1),
        )
    )
    repository.store_raw_candle(early)
    repository.store_raw_candle(middle)
    repository.store_raw_candle(late)

    # Start inclusive, end exclusive.
    result = repository.find_raw_candles_by_source_identity_and_event_time_range(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME, late_time
    )
    assert result == (early, middle)

    # start == end is a valid query returning an empty tuple.
    result = repository.find_raw_candles_by_source_identity_and_event_time_range(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", middle_time, middle_time
    )
    assert result == ()

    # Omitted (None) bounds are unbounded on that side.
    result = repository.find_raw_candles_by_source_identity_and_event_time_range(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", None, None
    )
    assert result == (early, middle, late)
    result = repository.find_raw_candles_by_source_identity_and_event_time_range(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", middle_time, None
    )
    assert result == (middle, late)


def test_in_memory_raw_candle_repository_rejects_invalid_time_range_inputs() -> None:
    repository = InMemoryRawCandleRepository()

    with pytest.raises(InvalidTimeRangeError):
        repository.find_raw_candles_by_source_identity_and_event_time_range(
            "FXCM",
            "fxcm-xauusd-m1",
            "XAUUSD",
            "M1",
            _EVENT_TIME,
            _EVENT_TIME - timedelta(minutes=1),
        )

    naive = datetime(2026, 1, 1, 0, 0, 0)
    with pytest.raises(InvalidTimeRangeError):
        repository.find_raw_candles_by_source_identity_and_event_time_range(
            "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", naive, None
        )
    with pytest.raises(InvalidTimeRangeError):
        repository.find_raw_candles_by_source_identity_and_event_time_range(
            "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", None, naive
        )

    # Aware, non-UTC-offset bounds are accepted and normalized — not an error.
    non_utc = _EVENT_TIME.astimezone(timezone(timedelta(hours=2)))
    result = repository.find_raw_candles_by_source_identity_and_event_time_range(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", non_utc, None
    )
    assert result == ()


def test_in_memory_raw_candle_repository_returns_stable_deterministic_ordering() -> (
    None
):
    repository = InMemoryRawCandleRepository()
    later = RawCandle.model_validate(
        _valid_raw_candle_kwargs(
            record_id=_SECOND_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            event_time_utc=_EVENT_TIME + timedelta(minutes=5),
            availability_time_utc=_EVENT_TIME + timedelta(minutes=6),
            processing_time_utc=_EVENT_TIME + timedelta(minutes=6, seconds=1),
            original_event_time=_EVENT_TIME + timedelta(minutes=5),
            original_availability_time=_EVENT_TIME + timedelta(minutes=6),
        )
    )
    earlier = RawCandle.model_validate(_valid_raw_candle_kwargs())

    # Stored out of order; results must come back in (event_time_utc, record_id) order.
    repository.store_raw_candle(later)
    repository.store_raw_candle(earlier)

    assert repository.all_raw_candles() == (earlier, later)


def test_in_memory_raw_candle_repository_query_results_do_not_mutate_stored_state() -> (
    None
):
    repository = InMemoryRawCandleRepository()
    candle = RawCandle.model_validate(_valid_raw_candle_kwargs())
    repository.store_raw_candle(candle)

    result = repository.all_raw_candles()
    assert isinstance(result, tuple)
    with pytest.raises(TypeError):
        result[0] = candle  # type: ignore[index]

    # Mutating a caller-held reference to a stored candle's tuple is
    # impossible since RawCandle itself is frozen; re-querying still returns
    # the exact same stored data.
    assert repository.all_raw_candles() == (candle,)


def test_in_memory_raw_candle_repository_implements_sink_and_read_protocols() -> None:
    repository: RawCandleSink = InMemoryRawCandleRepository()
    candle = RawCandle.model_validate(_valid_raw_candle_kwargs())
    repository.store_raw_candle(candle)

    read_repository: CandleReadRepository = InMemoryRawCandleRepository()
    read_repository.store_raw_candle(candle)  # type: ignore[attr-defined]
    found = read_repository.find_raw_candles_by_source_identity(
        "FXCM", "fxcm-xauusd-m1", "XAUUSD", "M1", _EVENT_TIME
    )
    assert found == (candle,)
