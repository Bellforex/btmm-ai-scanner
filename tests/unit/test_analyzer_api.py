import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    AmbiguousEventTimeAnalysisError,
    DuplicateCandleRecordError,
    InvalidMarketMeasurementConfigurationError,
    MixedSymbolAnalysisError,
    MixedTimeframeAnalysisError,
    UnsortedCandleSequenceError,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType

_RAW_CANDLE_ID = UUID("0193f340-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f340-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f340-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    timeframe: Timeframe = Timeframe.M1,
    event_time: datetime | None = None,
    record_id: UUID | None = None,
) -> NormalizedCandle:
    if event_time is None:
        event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": record_id if record_id is not None else _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": symbol,
            "timeframe": timeframe,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(str(o)),
            "high": Decimal(str(h)),
            "low": Decimal(str(low)),
            "close": Decimal(str(c)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(
    prices: list[tuple[float, float, float, float]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *p) for i, p in enumerate(prices))


_VALID_CANDLES = _build([(100.0, 101.0, 99.0, 100.0)] * 20)


def test_analyze_market_measurements_rejects_mixed_symbol_input() -> None:
    candles = (
        *_VALID_CANDLES[:-1],
        _candle(19, 100.0, 101.0, 99.0, 100.0, symbol=InternalSymbol.EURUSD),
    )
    with pytest.raises(MixedSymbolAnalysisError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_rejects_mixed_timeframe_input() -> None:
    candles = (
        *_VALID_CANDLES[:-1],
        _candle(19, 100.0, 101.0, 99.0, 100.0, timeframe=Timeframe.M5),
    )
    with pytest.raises(MixedTimeframeAnalysisError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_rejects_unsorted_input() -> None:
    candles = (
        _VALID_CANDLES[1],
        _VALID_CANDLES[0],
        *_VALID_CANDLES[2:],
    )
    with pytest.raises(UnsortedCandleSequenceError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_rejects_duplicate_record_id_input() -> None:
    duplicate = _candle(
        19, 100.0, 101.0, 99.0, 100.0, record_id=_VALID_CANDLES[0].record_id
    )
    candles = (*_VALID_CANDLES[:-1], duplicate)
    with pytest.raises(DuplicateCandleRecordError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_rejects_ambiguous_tied_event_time_input() -> None:
    tied = _candle(
        1000,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_VALID_CANDLES[0].event_time_utc,
    )
    candles = (_VALID_CANDLES[0], tied, *_VALID_CANDLES[1:])
    with pytest.raises(AmbiguousEventTimeAnalysisError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_rejects_missing_instrument_metadata() -> None:
    malformed = NormalizedCandle.model_construct(
        **{**_VALID_CANDLES[-1].model_dump(), "symbol": None}
    )
    candles = (*_VALID_CANDLES[:-1], malformed)
    with pytest.raises(InvalidMarketMeasurementConfigurationError):
        analyze_market_measurements(candles, _CONFIG, _HashIdentityProvider())


def test_analyze_market_measurements_returns_empty_aggregate_for_empty_input() -> None:
    result = analyze_market_measurements((), _CONFIG, _HashIdentityProvider())

    assert result.symbol is None
    assert result.timeframe is None
    assert result.analyzed_candle_count == 0
    assert result.confirmed_swings == ()
    assert result.displacement_observations == ()
    assert result.equal_level_clusters == ()
    assert result.support_resistance_zones == ()
    assert result.trendlines == ()


def test_analyze_market_measurements_is_deterministic_across_repeated_calls() -> None:
    first = analyze_market_measurements(
        _VALID_CANDLES, _CONFIG, _HashIdentityProvider()
    )
    second = analyze_market_measurements(
        _VALID_CANDLES, _CONFIG, _HashIdentityProvider()
    )

    assert first == second
