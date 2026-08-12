"""A6-AΔ permanent tests: exact bounded candidate-universe deltas.

The frontier emits a PoiFrontierDelta (new / changed / removed) computed only from
its own bounded state — append-only families contribute this candle's step
candidates, and only the mutable reference-zone and period-level families are
diffed, over their bounded current sets. Applying (previous universe + new +
changed - removed) must reproduce the frontier's full filtered universe at every
prefix — which the A6-A suite already proves equals _detect_bundle_candidates. No
append-only candidate is ever emitted as changed or removed (no historical scan).
"""

import hashlib
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.detector_frontier import (
    _candidate_identity,
    advance_detector_frontier,
    create_initial_detector_frontier_state,
)

_RAW_CANDLE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f460-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


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


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    *,
    event_time: datetime | None = None,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    et = event_time if event_time is not None else _BASE_TIME + timedelta(minutes=index)
    av = et + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f460-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": et,
            "availability_time_utc": av,
            "processing_time_utc": av,
            "original_event_time": et,
            "original_availability_time": av,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _random_walk(
    n: int,
    seed: int,
    *,
    timeframe: Timeframe = Timeframe.M1,
    start: datetime | None = None,
) -> list[NormalizedCandle]:
    rng = random.Random(seed)
    step = {Timeframe.M1: timedelta(minutes=1), Timeframe.D1: timedelta(days=1)}[
        timeframe
    ]
    base = start if start is not None else _BASE_TIME
    price = 100.0
    candles: list[NormalizedCandle] = []
    for i in range(n):
        price += rng.uniform(-1.5, 1.5)
        o = price
        c = price + rng.uniform(-1.2, 1.2)
        h = max(o, c) + rng.uniform(0.0, 0.9)
        low = min(o, c) - rng.uniform(0.0, 0.9)
        candles.append(
            _candle(
                i,
                f"{o:.2f}",
                f"{h:.2f}",
                f"{low:.2f}",
                f"{c:.2f}",
                event_time=base + step * i,
                timeframe=timeframe,
            )
        )
    return candles


def _apply_delta_matches_universe_every_prefix(
    candles: list[NormalizedCandle], timeframe: Timeframe
) -> dict[str, int]:
    idp = _HashIdentityProvider()
    frontier = create_initial_detector_frontier_state()
    universe: dict[object, object] = {}
    counts = {"new": 0, "changed": 0, "removed": 0}
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        frontier, filtered, _atr = advance_detector_frontier(
            frontier, candles[k - 1], measurement, _PCONFIG
        )
        delta = frontier.last_delta

        # No append-only candidate is ever mutated or removed (identity[1] == "A").
        for c in delta.changed_candidates:
            assert _candidate_identity(c)[1] != "A"
        for ident in delta.removed_identities:
            assert ident[1] != "A"

        for c in delta.new_candidates:
            ident = _candidate_identity(c)
            assert ident not in universe
            universe[ident] = c
        for c in delta.changed_candidates:
            ident = _candidate_identity(c)
            assert ident in universe
            universe[ident] = c
        for ident in delta.removed_identities:
            assert ident in universe
            del universe[ident]

        counts["new"] += len(delta.new_candidates)
        counts["changed"] += len(delta.changed_candidates)
        counts["removed"] += len(delta.removed_identities)

        # Delta-applied universe reproduces the frontier's filtered universe
        # exactly (which the A6-A suite proves == _detect_bundle_candidates).
        expected = {_candidate_identity(c): c for c in filtered}
        assert universe == expected
    return counts


def test_delta_reconstructs_universe_every_prefix_m1() -> None:
    counts = _apply_delta_matches_universe_every_prefix(
        _random_walk(130, seed=7), Timeframe.M1
    )
    assert counts["new"] > 0


def test_delta_reconstructs_universe_across_calendar_boundaries_d1() -> None:
    # D1 across day/week/month/year boundaries exercises period ADD/REPLACE/REMOVE
    # => changed and removed deltas actually fire.
    candles = _random_walk(
        45, seed=3, timeframe=Timeframe.D1, start=datetime(2025, 12, 20, tzinfo=UTC)
    )
    counts = _apply_delta_matches_universe_every_prefix(candles, Timeframe.D1)
    assert counts["changed"] > 0
    assert counts["removed"] > 0


def test_delta_reconstructs_universe_reference_zone_stream() -> None:
    counts = _apply_delta_matches_universe_every_prefix(
        _random_walk(120, seed=44), Timeframe.M1
    )
    assert counts["new"] > 0
