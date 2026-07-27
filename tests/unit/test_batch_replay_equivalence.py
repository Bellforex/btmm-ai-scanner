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
    DerivedIdentityCollisionError,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.market_data import InMemoryHistoricalReplaySource

_RAW_CANDLE_ID = UUID("0193f350-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f350-1234-7abc-8def-abcdefabcdff")
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


class _ConstantIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        return UUID("0193f350-0000-7000-8000-000000000001")


def _record_id(index: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    *,
    event_time: datetime | None = None,
    availability_time: datetime | None = None,
) -> NormalizedCandle:
    if event_time is None:
        event_time = _BASE_TIME + timedelta(minutes=index)
    if availability_time is None:
        availability_time = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
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


def _canonical_sort(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[NormalizedCandle, ...]:
    return tuple(sorted(candles, key=lambda c: (c.event_time_utc, c.record_id)))


_WARM_UP = [
    (100 + 0.1 * i, 100.5 + 0.1 * i, 99.6 + 0.1 * i, 100.2 + 0.1 * i) for i in range(16)
]
_ZIGZAG = [
    (100, 101, 99, 100),
    (100, 102, 99.5, 101.5),
    (101.5, 105, 101, 104),
    (104, 104.5, 100, 100.5),
    (100.5, 101, 96, 96.5),
    (96.5, 97, 93, 93.5),
    (93.5, 96, 93, 95.5),
    (95.5, 99, 95, 98.5),
    (98.5, 103, 98, 102.5),
    (102.5, 104, 101, 103.5),
    (103.5, 104, 100, 100.5),
    (100.5, 101, 97, 97.5),
    (97.5, 98, 94, 94.5),
    (94.5, 95, 91, 91.5),
    (91.5, 95, 91, 94.5),
    (94.5, 98, 94, 97.5),
    (97.5, 101, 97, 100.5),
]

_ALL_CANDLES = _build(_WARM_UP + _ZIGZAG)


def _replay_full_prefix(
    candles: tuple[NormalizedCandle, ...],
) -> tuple[NormalizedCandle, ...]:
    source = InMemoryHistoricalReplaySource(candles)
    accumulated: list[NormalizedCandle] = []
    while not source.is_exhausted:
        group = source.advance_next_availability_group()
        accumulated.extend(group)
    return _canonical_sort(tuple(accumulated))


def test_batch_and_replay_produce_identical_confirmed_swings_for_the_same_prefix() -> (
    None
):
    batch_result = analyze_market_measurements(
        _canonical_sort(_ALL_CANDLES), _CONFIG, _HashIdentityProvider()
    )
    replay_prefix = _replay_full_prefix(_ALL_CANDLES)
    replay_result = analyze_market_measurements(
        replay_prefix, _CONFIG, _HashIdentityProvider()
    )

    assert batch_result.confirmed_swings == replay_result.confirmed_swings


def test_batch_and_replay_produce_identical_trendlines_for_the_same_prefix() -> None:
    batch_result = analyze_market_measurements(
        _canonical_sort(_ALL_CANDLES), _CONFIG, _HashIdentityProvider()
    )
    replay_prefix = _replay_full_prefix(_ALL_CANDLES)
    replay_result = analyze_market_measurements(
        replay_prefix, _CONFIG, _HashIdentityProvider()
    )

    assert batch_result.trendlines == replay_result.trendlines


def test_batch_and_replay_produce_identical_support_resistance_zones_for_the_same_prefix() -> (
    None
):
    batch_result = analyze_market_measurements(
        _canonical_sort(_ALL_CANDLES), _CONFIG, _HashIdentityProvider()
    )
    replay_prefix = _replay_full_prefix(_ALL_CANDLES)
    replay_result = analyze_market_measurements(
        replay_prefix, _CONFIG, _HashIdentityProvider()
    )

    assert (
        batch_result.support_resistance_zones == replay_result.support_resistance_zones
    )


def test_unchanged_semantic_keys_retain_the_same_record_id_across_growing_prefixes() -> (
    None
):
    short_prefix = _canonical_sort(_ALL_CANDLES[:30])
    full_prefix = _canonical_sort(_ALL_CANDLES)

    short_result = analyze_market_measurements(
        short_prefix, _CONFIG, _HashIdentityProvider()
    )
    full_result = analyze_market_measurements(
        full_prefix, _CONFIG, _HashIdentityProvider()
    )

    short_ids = {swing.record_id for swing in short_result.confirmed_swings}
    full_ids = {swing.record_id for swing in full_result.confirmed_swings}
    assert len(short_ids) > 0
    assert short_ids.issubset(full_ids)


def test_replay_group_ingestion_processes_simultaneous_availability_candles_together() -> (
    None
):
    shared_availability = _BASE_TIME + timedelta(minutes=100)
    candle_a = _candle(
        200,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_BASE_TIME + timedelta(minutes=50),
        availability_time=shared_availability,
    )
    candle_b = _candle(
        201,
        100.0,
        101.0,
        99.0,
        100.0,
        event_time=_BASE_TIME + timedelta(minutes=51),
        availability_time=shared_availability,
    )
    source = InMemoryHistoricalReplaySource((candle_a, candle_b))

    group = source.advance_next_availability_group()

    assert len(group) == 2
    assert {c.record_id for c in group} == {candle_a.record_id, candle_b.record_id}
    assert source.is_exhausted


def test_identity_provider_raises_on_semantic_key_collision_within_one_call() -> None:
    with pytest.raises(DerivedIdentityCollisionError):
        analyze_market_measurements(
            _canonical_sort(_ALL_CANDLES), _CONFIG, _ConstantIdentityProvider()
        )
