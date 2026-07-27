from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.historical_replay import InMemoryHistoricalReplaySource

_RAW_CANDLE_ID = UUID("0193f2c3-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2c3-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_BASE_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _record_id(suffix: str) -> UUID:
    return UUID(f"0193f2c3-1234-7abc-8def-abcdefab{suffix}")


def _valid_normalized_candle_kwargs(**overrides: object) -> dict[str, object]:
    event_time = overrides.get("event_time_utc", _BASE_TIME)
    assert isinstance(event_time, datetime)
    availability_time = overrides.get(
        "availability_time_utc", event_time + timedelta(minutes=1)
    )
    assert isinstance(availability_time, datetime)
    processing_time = overrides.get("processing_time_utc", availability_time)
    assert isinstance(processing_time, datetime)
    kwargs: dict[str, object] = {
        "record_id": _record_id("0001"),
        "content_fingerprint": _FINGERPRINT,
        "raw_candle_id": _RAW_CANDLE_ID,
        "provider": "FXCM",
        "source_reference": "fxcm-xauusd-m1",
        "source_symbol": "XAUUSD",
        "source_timeframe": "M1",
        "symbol": InternalSymbol.XAUUSD,
        "timeframe": Timeframe.M1,
        "event_time_utc": event_time,
        "availability_time_utc": availability_time,
        "processing_time_utc": processing_time,
        "original_event_time": event_time,
        "original_availability_time": availability_time,
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


def _candle(**overrides: object) -> NormalizedCandle:
    return NormalizedCandle.model_validate(_valid_normalized_candle_kwargs(**overrides))


def test_replay_never_exposes_a_candle_before_its_availability_time() -> None:
    earliest = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME + timedelta(minutes=1),
        processing_time_utc=_BASE_TIME + timedelta(minutes=1),
    )
    middle = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=1),
        availability_time_utc=_BASE_TIME + timedelta(minutes=2),
        processing_time_utc=_BASE_TIME + timedelta(minutes=2),
    )
    latest = _candle(
        record_id=_record_id("0003"),
        event_time_utc=_BASE_TIME + timedelta(minutes=2),
        availability_time_utc=_BASE_TIME + timedelta(minutes=3),
        processing_time_utc=_BASE_TIME + timedelta(minutes=3),
    )

    # Constructed out of availability order to prove replay does not simply
    # echo insertion order.
    source = InMemoryHistoricalReplaySource([latest, earliest, middle])

    released_availability_times = []
    for _ in range(3):
        group = source.advance_next_availability_group()
        assert len(group) == 1
        released_availability_times.append(group[0].availability_time_utc)

    assert released_availability_times == sorted(released_availability_times)
    assert released_availability_times[0] == earliest.availability_time_utc
    assert released_availability_times[-1] == latest.availability_time_utc


def test_replay_exposes_a_candle_exactly_at_its_availability_time() -> None:
    candle = _candle(
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME + timedelta(minutes=1),
        processing_time_utc=_BASE_TIME + timedelta(minutes=1),
    )
    source = InMemoryHistoricalReplaySource([candle])

    group = source.advance_next_availability_group()
    assert group == (candle,)
    assert group[0].availability_time_utc == _BASE_TIME + timedelta(minutes=1)


def test_replay_releases_equal_availability_candles_in_stable_tie_broken_order() -> (
    None
):
    shared_availability = _BASE_TIME + timedelta(minutes=1)
    later_event = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=shared_availability,
        processing_time_utc=shared_availability,
    )
    earlier_event = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME - timedelta(seconds=30),
        availability_time_utc=shared_availability,
        processing_time_utc=shared_availability,
    )

    source = InMemoryHistoricalReplaySource([later_event, earlier_event])
    group = source.advance_next_availability_group()

    assert group == (earlier_event, later_event)
    assert source.is_exhausted is True


def test_event_time_alone_cannot_expose_a_candle_before_availability() -> None:
    # early_event has the earlier event_time_utc but a LATER availability_time_utc.
    early_event_late_availability = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME + timedelta(hours=1),
        processing_time_utc=_BASE_TIME + timedelta(hours=1),
    )
    # late_event has the later event_time_utc but an EARLIER availability_time_utc.
    late_event_early_availability = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=30),
        availability_time_utc=_BASE_TIME + timedelta(minutes=31),
        processing_time_utc=_BASE_TIME + timedelta(minutes=31),
    )

    source = InMemoryHistoricalReplaySource(
        [early_event_late_availability, late_event_early_availability]
    )

    first_group = source.advance_next_availability_group()
    assert first_group == (late_event_early_availability,)

    second_group = source.advance_next_availability_group()
    assert second_group == (early_event_late_availability,)


def test_processing_time_utc_does_not_control_historical_visibility() -> None:
    # first_available has a much later processing_time_utc than second_available,
    # yet its availability_time_utc is still earlier and must be released first.
    first_available = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME + timedelta(minutes=1),
        processing_time_utc=_BASE_TIME + timedelta(days=1),
    )
    second_available = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=10),
        availability_time_utc=_BASE_TIME + timedelta(minutes=11),
        processing_time_utc=_BASE_TIME + timedelta(minutes=11),
    )

    source = InMemoryHistoricalReplaySource([second_available, first_available])

    assert source.advance_next_availability_group() == (first_available,)
    assert source.advance_next_availability_group() == (second_available,)


def test_end_of_stream_never_leaks_a_future_record() -> None:
    candle = _candle()
    source = InMemoryHistoricalReplaySource([candle])

    assert source.advance_next_availability_group() == (candle,)
    assert source.is_exhausted is True

    for _ in range(5):
        assert source.advance_next_availability_group() == ()

    # The full immutable snapshot remains inspectable via replay(), but the
    # stateful cursor never re-surfaces or invents any further record.
    assert tuple(source.replay()) == (candle,)


def test_source_cannot_receive_a_normalized_candle_with_unavailable_availability_time() -> (
    None
):
    with pytest.raises(ValidationError):
        _candle(
            event_time_utc=_BASE_TIME,
            availability_time_utc=_BASE_TIME,
            processing_time_utc=_BASE_TIME,
        )

    with pytest.raises(ValidationError):
        _candle(
            event_time_utc=_BASE_TIME,
            availability_time_utc=_BASE_TIME - timedelta(seconds=1),
            processing_time_utc=_BASE_TIME,
        )
