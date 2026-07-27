from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.historical_replay import InMemoryHistoricalReplaySource
from btmm_ai_scanner.market_data.ports import HistoricalReplaySource

_RAW_CANDLE_ID = UUID("0193f2c2-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2c2-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_BASE_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _record_id(suffix: str) -> UUID:
    return UUID(f"0193f2c2-1234-7abc-8def-abcdefab{suffix}")


def _valid_normalized_candle_kwargs(**overrides: object) -> dict[str, object]:
    event_time = overrides.get("event_time_utc", _BASE_TIME)
    assert isinstance(event_time, datetime)
    availability_time = overrides.get(
        "availability_time_utc", event_time + timedelta(minutes=1)
    )
    assert isinstance(availability_time, datetime)
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
        "processing_time_utc": availability_time,
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


def test_historical_replay_source_orders_by_availability_then_event_time_then_identity() -> (
    None
):
    third = _candle(
        record_id=_record_id("0003"),
        event_time_utc=_BASE_TIME + timedelta(minutes=2),
        availability_time_utc=_BASE_TIME + timedelta(minutes=3),
        processing_time_utc=_BASE_TIME + timedelta(minutes=3),
        original_event_time=_BASE_TIME + timedelta(minutes=2),
        original_availability_time=_BASE_TIME + timedelta(minutes=3),
    )
    first = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME + timedelta(minutes=1),
        processing_time_utc=_BASE_TIME + timedelta(minutes=1),
        original_event_time=_BASE_TIME,
        original_availability_time=_BASE_TIME + timedelta(minutes=1),
    )
    second = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=1),
        availability_time_utc=_BASE_TIME + timedelta(minutes=2),
        processing_time_utc=_BASE_TIME + timedelta(minutes=2),
        original_event_time=_BASE_TIME + timedelta(minutes=1),
        original_availability_time=_BASE_TIME + timedelta(minutes=2),
    )

    source = InMemoryHistoricalReplaySource([third, first, second])
    assert tuple(source.replay()) == (first, second, third)


def test_historical_replay_source_advance_next_availability_group_releases_simultaneous_candles_together() -> (
    None
):
    shared_availability = _BASE_TIME + timedelta(minutes=1)
    candle_a = _candle(
        record_id=_record_id("0001"),
        event_time_utc=_BASE_TIME,
        availability_time_utc=shared_availability,
        processing_time_utc=shared_availability,
        original_event_time=_BASE_TIME,
        original_availability_time=shared_availability,
    )
    candle_b = _candle(
        record_id=_record_id("0002"),
        source_reference="fxcm-xauusd-m1-b",
        event_time_utc=_BASE_TIME - timedelta(seconds=30),
        availability_time_utc=shared_availability,
        processing_time_utc=shared_availability,
        original_event_time=_BASE_TIME - timedelta(seconds=30),
        original_availability_time=shared_availability,
    )
    later = _candle(
        record_id=_record_id("0003"),
        event_time_utc=_BASE_TIME + timedelta(minutes=5),
        availability_time_utc=_BASE_TIME + timedelta(minutes=6),
        processing_time_utc=_BASE_TIME + timedelta(minutes=6),
        original_event_time=_BASE_TIME + timedelta(minutes=5),
        original_availability_time=_BASE_TIME + timedelta(minutes=6),
    )

    source = InMemoryHistoricalReplaySource([candle_a, candle_b, later])

    first_group = source.advance_next_availability_group()
    assert set(first_group) == {candle_a, candle_b}
    assert source.position == 2

    second_group = source.advance_next_availability_group()
    assert second_group == (later,)
    assert source.position == 3


def test_historical_replay_source_advance_next_availability_group_returns_empty_tuple_at_end() -> (
    None
):
    candle = _candle()
    source = InMemoryHistoricalReplaySource([candle])

    assert source.advance_next_availability_group() == (candle,)
    assert source.is_exhausted is True
    assert source.advance_next_availability_group() == ()
    assert source.advance_next_availability_group() == ()


def test_historical_replay_source_replay_reproduces_the_same_sequence_on_repeated_calls() -> (
    None
):
    first = _candle(record_id=_record_id("0001"))
    second = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=5),
        availability_time_utc=_BASE_TIME + timedelta(minutes=6),
        processing_time_utc=_BASE_TIME + timedelta(minutes=6),
        original_event_time=_BASE_TIME + timedelta(minutes=5),
        original_availability_time=_BASE_TIME + timedelta(minutes=6),
    )
    source = InMemoryHistoricalReplaySource([first, second])

    items1 = tuple(source.replay())
    source.advance_next_availability_group()
    items2 = tuple(source.replay())

    assert items1 == items2 == (first, second)


def test_historical_replay_source_reset_reproduces_the_exact_sequence() -> None:
    first = _candle(record_id=_record_id("0001"))
    second = _candle(
        record_id=_record_id("0002"),
        event_time_utc=_BASE_TIME + timedelta(minutes=5),
        availability_time_utc=_BASE_TIME + timedelta(minutes=6),
        processing_time_utc=_BASE_TIME + timedelta(minutes=6),
        original_event_time=_BASE_TIME + timedelta(minutes=5),
        original_availability_time=_BASE_TIME + timedelta(minutes=6),
    )
    source = InMemoryHistoricalReplaySource([first, second])

    consumed_before_reset = []
    consumed_before_reset.append(source.advance_next_availability_group())
    consumed_before_reset.append(source.advance_next_availability_group())
    assert source.is_exhausted is True

    source.reset()
    assert source.position == 0
    assert source.is_exhausted is False

    consumed_after_reset = []
    consumed_after_reset.append(source.advance_next_availability_group())
    consumed_after_reset.append(source.advance_next_availability_group())

    assert consumed_before_reset == consumed_after_reset == [(first,), (second,)]


def test_historical_replay_source_handles_empty_replay_deterministically() -> None:
    source = InMemoryHistoricalReplaySource([])

    assert source.is_exhausted is True
    assert source.position == 0
    assert tuple(source.replay()) == ()
    assert source.advance_next_availability_group() == ()

    source.reset()
    assert source.is_exhausted is True
    assert source.advance_next_availability_group() == ()


def test_historical_replay_source_implements_protocol_and_exposes_no_extra_state() -> (
    None
):
    candle = _candle()
    source: HistoricalReplaySource = InMemoryHistoricalReplaySource([candle])

    assert callable(source.replay)
    assert tuple(source.replay()) == (candle,)

    assert not hasattr(source, "store_raw_candle")
    assert not hasattr(source, "store_normalized_candle")
    assert not hasattr(source, "find_raw_candles_by_source_identity")


def test_market_data_repository_and_replay_exports_import_successfully() -> None:
    import btmm_ai_scanner.market_data as market_data

    assert market_data.InMemoryRawCandleRepository is not None
    assert market_data.InMemoryNormalizedCandleRepository is not None
    assert market_data.InMemoryHistoricalReplaySource is not None
    assert issubclass(market_data.RecordIdentityConflictError, ValueError)
    assert issubclass(market_data.InvalidTimeRangeError, ValueError)

    raw_repository = market_data.InMemoryRawCandleRepository()
    normalized_repository = market_data.InMemoryNormalizedCandleRepository()
    candle = _candle()
    normalized_repository.store_normalized_candle(candle)
    replay_source = market_data.InMemoryHistoricalReplaySource([candle])

    assert raw_repository.all_raw_candles() == ()
    assert normalized_repository.all_normalized_candles() == (candle,)
    assert tuple(replay_source.replay()) == (candle,)
