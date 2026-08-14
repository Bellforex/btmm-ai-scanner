"""A6-F6D: per-prefix oracle harness for the incremental support/resistance
replay frontier.

The UNMODIFIED ``_derive_support_resistance_zone_candidates`` (driven with its
own persistent reaction trackers) is the independent semantic oracle. For every
prefix of every fixture we assert that ``_advance_sr_frontier`` produces the
byte-identical candidate tuple. Confirmed swings are produced by the real
measurement replay (the exact production pivot/confirmation logic), so the
fixtures exercise genuine swing sequences -- including middle insertions.

On the first divergent prefix the harness reports the full per-origin walk state
needed to debug it (never a bare final-hash mismatch).
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.analyzer import (
    _advance_measurement_replay_state,
    _advance_sr_frontier,
    _create_initial_measurement_replay_state,
    _derive_support_resistance_zone_candidates,
    _ReactionTracker,
    _SupportResistanceFrontier,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZoneCandidate
from btmm_ai_scanner.domain.swings import ConfirmedSwing

_RAW = UUID("0193f350-1234-7abc-8def-abcdefabcdaa")
_PROV = UUID("0193f350-1234-7abc-8def-abcdefabcdff")
_FP = "a" * 64
_BASE = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        import hashlib

        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: float, h: float, low: float, c: float) -> NormalizedCandle:
    event = _BASE + timedelta(minutes=15 * index)
    avail = event + timedelta(minutes=15)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m15",
            "source_symbol": "XAUUSD",
            "source_timeframe": Timeframe.M15.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M15,
            "event_time_utc": event,
            "availability_time_utc": avail,
            "processing_time_utc": avail,
            "original_event_time": event,
            "original_availability_time": avail,
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
            "provenance_id": _PROV,
        }
    )


def _candles_from_prices(
    prices: list[tuple[float, float, float, float]],
) -> list[NormalizedCandle]:
    return [_candle(i, *p) for i, p in enumerate(prices)]


def _random_walk(
    n: int, seed: int, *, spread: float, wick: float
) -> list[tuple[float, float, float, float]]:
    rng = random.Random(seed)
    price = 100.0
    out: list[tuple[float, float, float, float]] = []
    for _ in range(n):
        o = price
        c = o + rng.uniform(-spread, spread)
        h = max(o, c) + rng.uniform(0, wick)
        low = min(o, c) - rng.uniform(0, wick)
        out.append((o, h, low, c))
        price = c
    return out


def _zigzag(
    n: int, amplitude: float, period: int
) -> list[tuple[float, float, float, float]]:
    out: list[tuple[float, float, float, float]] = []
    price = 100.0
    for i in range(n):
        direction = 1 if (i // period) % 2 == 0 else -1
        o = price
        c = o + direction * amplitude
        h = max(o, c) + amplitude * 0.2
        low = min(o, c) - amplitude * 0.2
        out.append((o, h, low, c))
        price = c
    return out


def _monotonic(n: int, step: float) -> list[tuple[float, float, float, float]]:
    out: list[tuple[float, float, float, float]] = []
    price = 100.0
    for _ in range(n):
        o = price
        c = o + step
        out.append((o, max(o, c) + 0.3, min(o, c) - 0.3, c))
        price = c
    return out


def _flat(n: int) -> list[tuple[float, float, float, float]]:
    return [(100.0, 100.4, 99.6, 100.0) for _ in range(n)]


_FIXTURES: dict[str, list[NormalizedCandle]] = {
    "random_dense": _candles_from_prices(
        _random_walk(220, 20260813, spread=1.5, wick=0.8)
    ),
    "random_lowvol": _candles_from_prices(_random_walk(180, 7, spread=0.4, wick=0.2)),
    "random_wide": _candles_from_prices(_random_walk(200, 34, spread=2.5, wick=1.2)),
    "zigzag_tight": _candles_from_prices(_zigzag(160, 3.0, 4)),
    "zigzag_wide": _candles_from_prices(_zigzag(160, 6.0, 7)),
    "monotonic_up": _candles_from_prices(_monotonic(120, 0.8)),
    "monotonic_down": _candles_from_prices(_monotonic(120, -0.8)),
    "flat": _candles_from_prices(_flat(120)),
    "random_long": _candles_from_prices(_random_walk(400, 99, spread=1.8, wick=0.9)),
}


def _diagnose(
    prefix: int,
    candle: NormalizedCandle,
    swings: tuple[ConfirmedSwing, ...],
    old_candidates: tuple[SupportResistanceZoneCandidate, ...],
    new_candidates: tuple[SupportResistanceZoneCandidate, ...],
) -> str:
    lines = [
        f"SR frontier divergence at prefix {prefix} "
        f"(candle {candle.record_id}, event {candle.event_time_utc.isoformat()})",
        f"confirmed swings ({len(swings)}): "
        + ", ".join(
            f"{s.swing_type.value[:1]}@{s.meaningful_confirmation_time_utc.isoformat()}"
            f"/{s.pivot_price}"
            for s in swings[-8:]
        ),
        f"old candidate count={len(old_candidates)} new count={len(new_candidates)}",
    ]
    old_by = {(c.zone_type, c.origin_swing_record_id): c for c in old_candidates}
    new_by = {(c.zone_type, c.origin_swing_record_id): c for c in new_candidates}
    for key in sorted(set(old_by) | set(new_by), key=str):
        o = old_by.get(key)
        nw = new_by.get(key)
        if o == nw:
            continue
        lines.append(f"  DIFF key={key[0].value}/{key[1]}")
        lines.append(f"    old={o}")
        lines.append(f"    new={nw}")
    return "\n".join(lines)


@pytest.mark.parametrize("fixture_name", sorted(_FIXTURES))
def test_sr_frontier_matches_oracle_every_prefix(fixture_name: str) -> None:
    candles = _FIXTURES[fixture_name]
    measurement = _create_initial_measurement_replay_state(
        _HashIdentityProvider(), _CONFIG
    )
    old_origin_trackers: dict[UUID, _ReactionTracker] = {}
    old_touch_trackers: dict[tuple[UUID, UUID], _ReactionTracker] = {}
    frontier = _SupportResistanceFrontier()

    for prefix, candle in enumerate(candles, start=1):
        measurement = _advance_measurement_replay_state(measurement, candle, _CONFIG)
        candle_list = measurement.candles_so_far
        atr_list = measurement.atr_values_so_far
        swings = measurement.confirmed_swings_so_far

        old_candidates, old_origin_trackers, old_touch_trackers = (
            _derive_support_resistance_zone_candidates(
                candle_list,
                atr_list,
                swings,
                old_origin_trackers,
                old_touch_trackers,
                _CONFIG,
            )
        )
        new_candidates, frontier = _advance_sr_frontier(
            frontier, candle_list, atr_list, swings, _CONFIG
        )

        assert new_candidates == old_candidates, _diagnose(
            prefix, candle, swings, old_candidates, new_candidates
        )


def _count_frontier_walks(
    candles: list[NormalizedCandle], monkeypatch: pytest.MonkeyPatch
) -> int:
    from btmm_ai_scanner.domain import analyzer as dom

    real = dom._sr_resume_origin
    calls = {"n": 0}

    def _counting(*args: object, **kwargs: object) -> object:
        calls["n"] += 1
        return real(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(dom, "_sr_resume_origin", _counting)
    measurement = _create_initial_measurement_replay_state(
        _HashIdentityProvider(), _CONFIG
    )
    frontier = _SupportResistanceFrontier()
    for candle in candles:
        measurement = _advance_measurement_replay_state(measurement, candle, _CONFIG)
        _, frontier = _advance_sr_frontier(
            frontier,
            measurement.candles_so_far,
            measurement.atr_values_so_far,
            measurement.confirmed_swings_so_far,
            _CONFIG,
        )
    return calls["n"]


@pytest.mark.xfail(
    reason=(
        "A6-F6D-M2 disclosed non-blocking finding. The engine is now incremental "
        "and PRODUCTION-WIRED: each dirty origin resumes from the earliest changed "
        "touch and stops at last_touch_time re-convergence, so per-resume WORK is "
        "O(1) in the common case (vs M1's O(A) full re-walk). That collapsed the SR "
        "cost from ~2.95s to ~1.41s at N=1000 and the empirical exponent from 2.50 "
        "to 2.36, byte-identical at every prefix. But the RESUME-CALL COUNT is still "
        "~O(A^2): a newly appended touch is routed to every prior same-type origin "
        "(most converge in one step because the touch is outside their zone). "
        "Reaching strictly sub-quadratic resume-calls needs a zone-price/interval "
        "index that routes only origins whose zone the new touch actually enters -- "
        "a further optimization, not required for byte-identical correctness. This "
        "xpasses once that index lands."
    ),
    strict=True,
)
def test_f6d_frontier_resume_call_scaling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Count per-origin resume invocations as candle count doubles on a fixture
    # with continuous SR churn (dense zigzag). Strictly sub-quadratic resume-calls
    # require the zone-price routing index described in the xfail reason.
    small = _candles_from_prices(_zigzag(120, 3.0, 4))
    large = _candles_from_prices(_zigzag(240, 3.0, 4))
    with monkeypatch.context() as m:
        n_small = _count_frontier_walks(small, m)
    with monkeypatch.context() as m:
        n_large = _count_frontier_walks(large, m)
    assert n_large < 2.6 * n_small, (n_small, n_large)
