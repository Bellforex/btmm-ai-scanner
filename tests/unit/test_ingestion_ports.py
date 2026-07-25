from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import (
    CandleCompleteness,
    CandleVolumeKind,
    RawCandle,
)
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.ports import (
    CandleReadRepository,
    HistoricalReplaySource,
    NormalizedCandleSink,
    RawCandleSink,
)

_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _raw_candle(record_id: UUID) -> RawCandle:
    return RawCandle.model_validate(
        {
            "record_id": record_id,
            "content_fingerprint": _FINGERPRINT,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "event_time_utc": _EVENT_TIME,
            "availability_time_utc": _EVENT_TIME.replace(minute=1),
            "processing_time_utc": _EVENT_TIME.replace(minute=1, second=1),
            "original_event_time": _EVENT_TIME,
            "original_availability_time": _EVENT_TIME.replace(minute=1),
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
    )


def _normalized_candle(record_id: UUID, raw_candle: RawCandle) -> NormalizedCandle:
    return NormalizedCandle.model_validate(
        {
            "record_id": record_id,
            "content_fingerprint": "b" * 64,
            "raw_candle_id": raw_candle.record_id,
            "provider": raw_candle.provider,
            "source_reference": raw_candle.source_reference,
            "source_symbol": raw_candle.source_symbol,
            "source_timeframe": raw_candle.source_timeframe,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": raw_candle.event_time_utc,
            "availability_time_utc": raw_candle.availability_time_utc,
            "processing_time_utc": raw_candle.processing_time_utc,
            "original_event_time": raw_candle.original_event_time,
            "original_availability_time": raw_candle.original_availability_time,
            "original_timezone": raw_candle.original_timezone,
            "open": raw_candle.open,
            "high": raw_candle.high,
            "low": raw_candle.low,
            "close": raw_candle.close,
            "volume": raw_candle.volume,
            "volume_kind": raw_candle.volume_kind,
            "completeness": raw_candle.completeness,
            "rule_version": raw_candle.rule_version,
            "contract_version": raw_candle.contract_version,
            "schema_version": raw_candle.schema_version,
            "provenance_id": raw_candle.provenance_id,
        }
    )


class _InMemoryRawCandleSink:
    def __init__(self) -> None:
        self.stored: list[RawCandle] = []

    def store_raw_candle(self, raw_candle: RawCandle) -> None:
        self.stored.append(raw_candle)


class _InMemoryNormalizedCandleSink:
    def __init__(self) -> None:
        self.stored: list[NormalizedCandle] = []

    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None:
        self.stored.append(normalized_candle)


class _InMemoryCandleReadRepository:
    def __init__(self, records: Sequence[RawCandle]) -> None:
        self._records = list(records)

    def find_raw_candles_by_source_identity(
        self,
        provider: str,
        source_reference: str,
        source_symbol: str,
        source_timeframe: str,
        event_time_utc: datetime,
    ) -> Sequence[RawCandle]:
        return [
            record
            for record in self._records
            if record.provider == provider
            and record.source_reference == source_reference
            and record.source_symbol == source_symbol
            and record.source_timeframe == source_timeframe
            and record.event_time_utc == event_time_utc
        ]


class _InMemoryHistoricalReplaySource:
    def __init__(self, records: Sequence[NormalizedCandle]) -> None:
        self._records = list(records)

    def replay(self) -> Iterator[NormalizedCandle]:
        yield from self._records


def test_raw_candle_sink_protocol_conformance() -> None:
    sink: RawCandleSink = _InMemoryRawCandleSink()
    candle = _raw_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd01"))
    sink.store_raw_candle(candle)
    assert isinstance(sink, _InMemoryRawCandleSink)
    assert sink.stored == [candle]


def test_normalized_candle_sink_protocol_conformance() -> None:
    sink: NormalizedCandleSink = _InMemoryNormalizedCandleSink()
    raw_candle = _raw_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd02"))
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd03"), raw_candle
    )
    sink.store_normalized_candle(normalized)
    assert isinstance(sink, _InMemoryNormalizedCandleSink)
    assert sink.stored == [normalized]


def test_candle_read_repository_protocol_conformance() -> None:
    candle = _raw_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd04"))
    repository: CandleReadRepository = _InMemoryCandleReadRepository([candle])
    found = repository.find_raw_candles_by_source_identity(
        candle.provider,
        candle.source_reference,
        candle.source_symbol,
        candle.source_timeframe,
        candle.event_time_utc,
    )
    assert list(found) == [candle]


def test_historical_replay_source_protocol_conformance() -> None:
    raw_candle = _raw_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd05"))
    normalized = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd06"), raw_candle
    )
    source: HistoricalReplaySource = _InMemoryHistoricalReplaySource([normalized])
    assert list(source.replay()) == [normalized]


def test_candle_read_repository_has_no_mutation_method() -> None:
    public_methods = {
        name for name in vars(CandleReadRepository) if not name.startswith("_")
    }
    assert public_methods == {"find_raw_candles_by_source_identity"}
    assert not any(name.startswith("store") for name in public_methods)


def test_historical_replay_source_is_deterministic_and_ordered() -> None:
    raw_candle = _raw_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd07"))
    first = _normalized_candle(UUID("0193f2c0-1234-7abc-8def-abcdefabcd08"), raw_candle)
    second = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd09"), raw_candle
    )
    source = _InMemoryHistoricalReplaySource([first, second])
    assert list(source.replay()) == [first, second]
    assert list(source.replay()) == [first, second]
