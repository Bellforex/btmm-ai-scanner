from datetime import UTC, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.normalized_candle_repository import (
    InMemoryNormalizedCandleRepository,
)
from btmm_ai_scanner.market_data.ports import NormalizedCandleSink
from btmm_ai_scanner.market_data.raw_candle_repository import (
    InvalidTimeRangeError,
    RecordIdentityConflictError,
)

_RECORD_ID = UUID("0193f2c1-1234-7abc-8def-abcdefabcd01")
_SECOND_RECORD_ID = UUID("0193f2c1-1234-7abc-8def-abcdefabcd02")
_THIRD_RECORD_ID = UUID("0193f2c1-1234-7abc-8def-abcdefabcd03")
_RAW_CANDLE_ID = UUID("0193f2c1-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2c1-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_SECOND_FINGERPRINT = "b" * 64
_THIRD_FINGERPRINT = "c" * 64

_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
_AVAILABILITY_TIME = _EVENT_TIME + timedelta(minutes=1)
_PROCESSING_TIME = _AVAILABILITY_TIME + timedelta(seconds=1)


def _valid_normalized_candle_kwargs(**overrides: object) -> dict[str, object]:
    kwargs: dict[str, object] = {
        "record_id": _RECORD_ID,
        "content_fingerprint": _FINGERPRINT,
        "raw_candle_id": _RAW_CANDLE_ID,
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


def test_in_memory_normalized_candle_repository_stores_and_queries_by_symbol_and_timeframe() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    candle = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())
    repository.store_normalized_candle(candle)

    found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert found == (candle,)

    not_found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.EURUSD, Timeframe.M1, None, None
    )
    assert not_found == ()
    not_found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M5, None, None
    )
    assert not_found == ()


def test_in_memory_normalized_candle_repository_preserves_conflicting_revisions() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    original = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())

    exact_duplicate = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(record_id=_SECOND_RECORD_ID)
    )
    repository.store_normalized_candle(original)
    repository.store_normalized_candle(exact_duplicate)
    found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert set(found) == {original, exact_duplicate}

    conflicting_revision = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(
            record_id=_THIRD_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            close=Decimal("200.0"),
            high=Decimal("201.0"),
        )
    )
    repository.store_normalized_candle(conflicting_revision)
    found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert set(found) == {original, exact_duplicate, conflicting_revision}


def test_in_memory_normalized_candle_repository_rejects_silent_overwrite_of_differing_content() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    candle = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())
    repository.store_normalized_candle(candle)

    repository.store_normalized_candle(candle)
    found = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert found == (candle,)

    differing_content = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(content_fingerprint=_SECOND_FINGERPRINT)
    )
    with pytest.raises(RecordIdentityConflictError):
        repository.store_normalized_candle(differing_content)

    found_after = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert found_after == (candle,)


def test_in_memory_normalized_candle_repository_range_query_boundary_is_half_open() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    early = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(
            record_id=_RECORD_ID,
            event_time_utc=_EVENT_TIME,
            availability_time_utc=_EVENT_TIME + timedelta(minutes=1),
            processing_time_utc=_EVENT_TIME + timedelta(minutes=1, seconds=1),
            original_event_time=_EVENT_TIME,
            original_availability_time=_EVENT_TIME + timedelta(minutes=1),
        )
    )
    middle_time = _EVENT_TIME + timedelta(minutes=1)
    middle = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(
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
    late = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(
            record_id=_THIRD_RECORD_ID,
            content_fingerprint=_THIRD_FINGERPRINT,
            event_time_utc=late_time,
            availability_time_utc=late_time + timedelta(minutes=1),
            processing_time_utc=late_time + timedelta(minutes=1, seconds=1),
            original_event_time=late_time,
            original_availability_time=late_time + timedelta(minutes=1),
        )
    )
    repository.store_normalized_candle(early)
    repository.store_normalized_candle(middle)
    repository.store_normalized_candle(late)

    result = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, _EVENT_TIME, late_time
    )
    assert result == (early, middle)

    result = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, middle_time, middle_time
    )
    assert result == ()

    result = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, None, None
    )
    assert result == (early, middle, late)
    result = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, middle_time, None
    )
    assert result == (middle, late)


def test_in_memory_normalized_candle_repository_rejects_invalid_time_range_inputs() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()

    with pytest.raises(InvalidTimeRangeError):
        repository.find_by_symbol_timeframe_range(
            InternalSymbol.XAUUSD,
            Timeframe.M1,
            _EVENT_TIME,
            _EVENT_TIME - timedelta(minutes=1),
        )

    naive = datetime(2026, 1, 1, 0, 0, 0)
    with pytest.raises(InvalidTimeRangeError):
        repository.find_by_symbol_timeframe_range(
            InternalSymbol.XAUUSD, Timeframe.M1, naive, None
        )
    with pytest.raises(InvalidTimeRangeError):
        repository.find_by_symbol_timeframe_range(
            InternalSymbol.XAUUSD, Timeframe.M1, None, naive
        )

    non_utc = _EVENT_TIME.astimezone(timezone(timedelta(hours=2)))
    result = repository.find_by_symbol_timeframe_range(
        InternalSymbol.XAUUSD, Timeframe.M1, non_utc, None
    )
    assert result == ()


def test_in_memory_normalized_candle_repository_returns_stable_deterministic_ordering() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    later = NormalizedCandle.model_validate(
        _valid_normalized_candle_kwargs(
            record_id=_SECOND_RECORD_ID,
            content_fingerprint=_SECOND_FINGERPRINT,
            event_time_utc=_EVENT_TIME + timedelta(minutes=5),
            availability_time_utc=_EVENT_TIME + timedelta(minutes=6),
            processing_time_utc=_EVENT_TIME + timedelta(minutes=6, seconds=1),
            original_event_time=_EVENT_TIME + timedelta(minutes=5),
            original_availability_time=_EVENT_TIME + timedelta(minutes=6),
        )
    )
    earlier = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())

    repository.store_normalized_candle(later)
    repository.store_normalized_candle(earlier)

    assert repository.all_normalized_candles() == (earlier, later)


def test_in_memory_normalized_candle_repository_query_results_do_not_mutate_stored_state() -> (
    None
):
    repository = InMemoryNormalizedCandleRepository()
    candle = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())
    repository.store_normalized_candle(candle)

    result = repository.all_normalized_candles()
    assert isinstance(result, tuple)
    with pytest.raises(TypeError):
        result[0] = candle  # type: ignore[index]

    assert repository.all_normalized_candles() == (candle,)


def test_in_memory_normalized_candle_repository_implements_sink_protocol_only() -> None:
    repository: NormalizedCandleSink = InMemoryNormalizedCandleRepository()
    candle = NormalizedCandle.model_validate(_valid_normalized_candle_kwargs())
    repository.store_normalized_candle(candle)

    assert not hasattr(repository, "find_raw_candles_by_source_identity")
    assert not hasattr(repository, "replay")
