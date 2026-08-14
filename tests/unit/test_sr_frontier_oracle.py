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
    _sr_has_opposite_between,
    _SupportResistanceFrontier,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType, SupportResistanceType
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


def _path(
    points: list[float], per_leg: int, wick: float = 0.3
) -> list[tuple[float, float, float, float]]:
    """Build candles by linearly interpolating between successive turning-point
    ``points`` with ``per_leg`` candles per leg. Lets a fixture describe an exact
    structural shape (double bottoms, dormant plateaus, retests) whose confirmed
    swings then drive the every-prefix oracle comparison."""
    out: list[tuple[float, float, float, float]] = []
    price = points[0]
    for target in points[1:]:
        start = price
        for i in range(1, per_leg + 1):
            o = out[-1][3] if out else start
            c = start + (target - start) * (i / per_leg)
            out.append((o, max(o, c) + wick, min(o, c) - wick, c))
        price = target
    return out


# --- A6-F6D-M2R middle-insertion / boundary structural fixtures (directive s16).
# Each is a genuine confirmed-swing sequence (produced by the real measurement
# replay) that exercises a middle-insertion or dormant-revisit path; the oracle
# harness asserts byte-identical candidates at EVERY prefix.
def _double_bottom_retests() -> list[tuple[float, float, float, float]]:
    # Support origin then repeated retests, each separated by an opposite high
    # confirmed strictly inside the touch interval (opposite-inside-interval).
    return _path([100, 90, 104, 90.2, 106, 89.8, 108, 90.1, 110], per_leg=5)


def _long_dormant_revisit() -> list[tuple[float, float, float, float]]:
    # Make a support origin + one touch, go dormant on a plateau far above the
    # zone for a long stretch, then revisit the original level much later (a long
    # dormant candidate whose walk must resume across many settled positions).
    dip = _path([100, 88, 103, 88.5, 104], per_leg=5)
    plateau = [(104.0, 104.4, 103.6, 104.0) for _ in range(40)]
    revisit = _path([104, 88.3, 105], per_leg=6)
    return dip + plateau + revisit


def _ascending_pullbacks() -> list[tuple[float, float, float, float]]:
    # Uptrend with higher-low pullbacks: opposites land before/after intervals,
    # touches drift out of older zones (routing must skip the stale origins).
    return _path([100, 96, 108, 103, 116, 111, 124, 119, 132], per_leg=5)


def _widening_whipsaw() -> list[tuple[float, float, float, float]]:
    # Amplitude grows each swing, so trackers are frequently pending across an
    # opposite confirmation before resolving (pending-tracker-during-insertion).
    return _path(
        [100, 97, 105, 99, 110, 96, 116, 93, 122, 90, 128], per_leg=4, wick=0.5
    )


def _tight_retest_cluster() -> list[tuple[float, float, float, float]]:
    # Several nearly-equal lows with deeper highs between, each leg long enough
    # to confirm pivots: multiple qualifying touches accumulate on one origin,
    # exercising the multi-touch resume + opposite-inside-interval path.
    return _path([100, 88, 100, 88.3, 101, 88.15, 102, 88.25, 104], per_leg=6, wick=0.4)


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
    # A6-F6D-M2R middle-insertion / dormant-revisit structural fixtures.
    "double_bottom_retests": _candles_from_prices(_double_bottom_retests()),
    "long_dormant_revisit": _candles_from_prices(_long_dormant_revisit()),
    "ascending_pullbacks": _candles_from_prices(_ascending_pullbacks()),
    "widening_whipsaw": _candles_from_prices(_widening_whipsaw()),
    "tight_retest_cluster": _candles_from_prices(_tight_retest_cluster()),
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


def _oracle_candidate_churn(candles: list[NormalizedCandle]) -> tuple[int, int]:
    """The irreducible amount of per-prefix work, computed from the UNMODIFIED
    oracle: the total number of (zone, origin) candidates that change value from
    one prefix to the next, plus the final confirmed-swing count. A frontier can
    never do sub-linearly *less* resume work than the candidates that genuinely
    change -- this is the lower bound the routing index is measured against."""
    measurement = _create_initial_measurement_replay_state(
        _HashIdentityProvider(), _CONFIG
    )
    _Key = tuple[SupportResistanceType, UUID]
    ot: dict[UUID, _ReactionTracker] = {}
    tt: dict[tuple[UUID, UUID], _ReactionTracker] = {}
    prev: dict[_Key, SupportResistanceZoneCandidate] = {}
    total_churn = 0
    swings = 0
    for candle in candles:
        measurement = _advance_measurement_replay_state(measurement, candle, _CONFIG)
        cands, ot, tt = _derive_support_resistance_zone_candidates(
            measurement.candles_so_far,
            measurement.atr_values_so_far,
            measurement.confirmed_swings_so_far,
            ot,
            tt,
            _CONFIG,
        )
        cur: dict[_Key, SupportResistanceZoneCandidate] = {
            (c.zone_type, c.origin_swing_record_id): c for c in cands
        }
        for k in set(cur) | set(prev):
            if cur.get(k) != prev.get(k):
                total_churn += 1
        prev = cur
        swings = len(measurement.confirmed_swings_so_far)
    return total_churn, swings


def test_f6d_frontier_resume_calls_subquadratic_on_realistic_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A6-F6D-M2R zone-price routing gate. On realistic (random-walk) price
    action the vast majority of prior same-type origins do NOT contain a new
    touch's price, so the routing index skips them entirely. Doubling the candle
    count (~doubling the swing count) must therefore grow resume-CALL count
    clearly sub-quadratically (a quadratic mark-all scheme grows ~4x; M1's full
    re-walk grew 4.55x). Measured ~1.8-2.1x across seeds; asserted < 3.0 with
    margin. Byte-identical correctness is proven separately at every prefix."""
    for seed, spread, wick in ((20260813, 1.5, 0.8), (34, 2.5, 1.2)):
        small = _candles_from_prices(_random_walk(300, seed, spread=spread, wick=wick))
        large = _candles_from_prices(_random_walk(600, seed, spread=spread, wick=wick))
        with monkeypatch.context() as m:
            n_small = _count_frontier_walks(small, m)
        with monkeypatch.context() as m:
            n_large = _count_frontier_walks(large, m)
        assert n_large < 3.0 * n_small, (seed, n_small, n_large)


def test_f6d_frontier_resume_calls_track_irreducible_churn_on_dense_zigzag(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The routing index cannot (and must not) reduce GENUINE work. A tight
    zigzag makes every same-type zone overlap, so a new touch really does enter
    every prior origin's band and really does change ~O(A) candidates per swing
    -- the oracle's own candidate churn is quadratic here. This test proves the
    frontier does not blow that genuine work up spuriously: its resume-call count
    stays within a small constant of the oracle's irreducible churn (measured
    2.0-4.6x). This is the honest counterpart to the realistic-data gate: routing
    collapses spurious calls, never inflates necessary ones."""
    for amplitude, period in ((3.0, 4), (6.0, 7)):
        candles = _candles_from_prices(_zigzag(160, amplitude, period))
        with monkeypatch.context() as m:
            resume_calls = _count_frontier_walks(candles, m)
        churn, swings = _oracle_candidate_churn(candles)
        assert resume_calls <= 8 * (churn + swings), (
            amplitude,
            period,
            resume_calls,
            churn,
            swings,
        )


def _t(minutes: int) -> datetime:
    return _BASE + timedelta(minutes=minutes)


def test_has_opposite_between_boundaries() -> None:
    """A6-F6D-M2R directive s12: the O(log A) bisect index must reproduce the
    oracle's STRICT open-interval predicate ``last_time < opp < touch_time`` at
    every boundary. An opposite exactly at either endpoint is excluded; one just
    inside is included; one just outside is excluded."""
    last, touch = _t(20), _t(40)
    # opposite exactly AT the start boundary (== last_time) -> excluded
    assert _sr_has_opposite_between((_t(20),), last, touch) is False
    # opposite exactly AT the end boundary (== touch_time) -> excluded
    assert _sr_has_opposite_between((_t(40),), last, touch) is False
    # opposite immediately inside the open interval -> included
    assert _sr_has_opposite_between((_t(21),), last, touch) is True
    assert _sr_has_opposite_between((_t(39),), last, touch) is True
    # opposite immediately outside (just before / just after) -> excluded
    assert _sr_has_opposite_between((_t(19),), last, touch) is False
    assert _sr_has_opposite_between((_t(41),), last, touch) is False
    # empty index -> never between
    assert _sr_has_opposite_between((), last, touch) is False
    # multiple opposites, only boundary-touching ones present -> excluded
    assert _sr_has_opposite_between((_t(20), _t(40)), last, touch) is False
    # one interior among boundary-touchers -> included
    assert _sr_has_opposite_between((_t(20), _t(30), _t(40)), last, touch) is True
    # degenerate empty interval (last == touch) -> nothing can be strictly inside
    assert _sr_has_opposite_between((_t(30),), _t(30), _t(30)) is False


def test_has_opposite_between_matches_bruteforce() -> None:
    """Cross-check the bisect predicate against a brute-force ``any(... )`` over
    the same times (the oracle's exact form) across random configurations."""
    import random

    rng = random.Random(20260814)
    for _ in range(500):
        times = sorted(_t(rng.randint(0, 60)) for _ in range(rng.randint(0, 8)))
        last = _t(rng.randint(0, 60))
        touch = _t(rng.randint(0, 60))
        expected = any(last < s < touch for s in times)
        assert _sr_has_opposite_between(tuple(times), last, touch) is expected, (
            times,
            last,
            touch,
        )
