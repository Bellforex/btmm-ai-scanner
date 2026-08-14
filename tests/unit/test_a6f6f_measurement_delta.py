"""A6-F6F: measurement delta-finalization + lazy-trendline operation gates.

F6F-A defers all trendline discovery to an on-demand batch derivation
(`_materialize_trendlines`), and F6F-B memoizes the identity resolver so an
unchanged historical candidate is not re-hashed every candle. Correctness stays
covered byte-for-byte by the batch/incremental equivalence cascade; this file
locks the *access-pattern* invariants and the *operation-count* reductions that
those equivalence tests do not measure:

* the lazily materialized trendlines equal the batch detector at EVERY prefix and
  are stable across repeated / interleaved materializations (no stale cache);
* the resolver invokes the underlying identity provider O(distinct records)
  times, not O(candles x records).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    _advance_measurement_replay_state,
    _create_initial_measurement_replay_state,
    _materialize_trendlines,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType

_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_FP = "a" * 64
_RAW = UUID("0193f350-1234-7abc-8def-abcdefabcdaa")
_PROV = UUID("0193f350-1234-7abc-8def-abcdefabcdff")


class _CountingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        import hashlib

        self.calls += 1
        payload = output_type.value + "|" + "|".join(semantic_key)
        d = hashlib.sha256(payload.encode()).digest()[:16]
        v = int.from_bytes(d, "big")
        v &= ~(0xF << 76)
        v |= 7 << 76
        v &= ~(0x3 << 62)
        v |= 0x2 << 62
        return UUID(int=v)


def _candle(i: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    et = _BASE + timedelta(minutes=15 * i)
    av = et + timedelta(minutes=15)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f350-1234-7abc-8def-{i:012x}"),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "r",
            "source_symbol": "XAUUSD",
            "source_timeframe": Timeframe.M15.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M15,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(f"{o:.2f}"),
            "high": Decimal(f"{h:.2f}"),
            "low": Decimal(f"{low:.2f}"),
            "close": Decimal(f"{c:.2f}"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV,
        }
    )


def _zigzag(n: int, amp: float, period: int) -> list[NormalizedCandle]:
    out = []
    price = 100.0
    for i in range(n):
        direction = 1 if (i // period) % 2 == 0 else -1
        o = price
        c = o + direction * amp
        out.append(_candle(i, o, max(o, c) + amp * 0.2, min(o, c) - amp * 0.2, c))
        price = c
    return out


def test_lazy_trendlines_match_batch_at_every_prefix() -> None:
    candles = _zigzag(140, 4.0, 5)
    state = _create_initial_measurement_replay_state(_CountingProvider(), _CONFIG)
    for prefix, candle in enumerate(candles, start=1):
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        lazy = _materialize_trendlines(state)
        batch = analyze_market_measurements(
            tuple(candles[:prefix]), _CONFIG, _CountingProvider()
        ).trendlines
        assert [t.record_id for t in lazy] == [t.record_id for t in batch], prefix
        assert [t.content_fingerprint for t in lazy] == [
            t.content_fingerprint for t in batch
        ], prefix


def test_repeated_and_interleaved_materialization_is_stable() -> None:
    # No stale cache: materializing trendlines several times at the same prefix,
    # and again after further advances, always yields the exact current history.
    candles = _zigzag(120, 4.0, 5)
    state = _create_initial_measurement_replay_state(_CountingProvider(), _CONFIG)
    for candle in candles[:80]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
    a = _materialize_trendlines(state)
    b = _materialize_trendlines(state)
    assert a == b
    for candle in candles[80:]:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
    c1 = _materialize_trendlines(state)
    c2 = _materialize_trendlines(state)
    assert c1 == c2
    batch = analyze_market_measurements(
        tuple(candles), _CONFIG, _CountingProvider()
    ).trendlines
    assert [t.record_id for t in c1] == [t.record_id for t in batch]


def test_resolver_memo_calls_provider_per_distinct_record_not_per_candle() -> None:
    # The resolver must invoke identify() a number of times bounded by the total
    # distinct (record, provenance) identities ever produced -- NOT by
    # candles x live-records. On a long run that is dramatically sub-quadratic.
    candles = _zigzag(160, 4.0, 5)
    provider = _CountingProvider()
    state = _create_initial_measurement_replay_state(provider, _CONFIG)
    for candle in candles:
        state = _advance_measurement_replay_state(state, candle, _CONFIG)
        _materialize_trendlines(state)  # exercises the resolver on the full history
    # Distinct identities across every measurement family at the final prefix.
    final = _materialize_trendlines(state)
    distinct_records = (
        len(state.confirmed_swings_so_far)
        + len(state.equal_level_clusters_so_far)
        + len(state.support_resistance_zones_so_far)
        + len(final)
        + len(state.displacement_candidates_so_far)
    )
    # Each distinct record contributes at most 2 identify calls (record +
    # provenance); the memo guarantees no re-hash of an already-seen key, so the
    # count is O(distinct records), far below the naive candles*records product.
    assert provider.calls <= 2 * distinct_records + 8, (
        provider.calls,
        distinct_records,
    )
    # And it stays well under a per-candle re-resolution of the live set.
    naive_upper = len(candles) * max(1, len(state.confirmed_swings_so_far))
    assert provider.calls < naive_upper, (provider.calls, naive_upper)
