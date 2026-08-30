"""P3 CORE — end-to-end synthetic parity and the frozen digest contract.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

The detector and lifecycle campaigns each prove their own layer against
production. This file joins them: it runs the whole P3 CORE pipeline —
detection over a bounded ring, persistent identity, persistent lifecycle,
downstream projection — over synthetic streams, and then exercises the digest
contract that the real-data campaign will hash.

Three properties matter here and are not covered by the layer campaigns:

* the canonical ordering is TOTAL over everything the detectors can emit, so
  hashing is well defined (AD-1 explicitly forbids falling back to an array
  index or identity bytes);
* the digest is independent of the order POIs were discovered in;
* every P3 CORE type and every reachable lifecycle state actually appears, so
  a green run is evidence rather than an artefact of a quiet fixture.
"""

from __future__ import annotations

import importlib.util
import random
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from types import ModuleType
from typing import Any
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection

REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


M = _load("_p3core_detectors", "tests/parity_support/p3_pine_model.py")
L = _load("_p3core_lifecycle", "tests/parity_support/p3_lifecycle_model.py")
G = _load("_p3core_digest", "tests/parity_support/p3_digest.py")

_TICK = Decimal("0.01")
_CONFIG = PoiConfiguration(minimum_price_tick=_TICK)
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_RAW_CANDLE_ID = UUID("0193f4b0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f4b0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "f" * 64


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f4b0-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
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


def _stream(seed: int, length: int) -> tuple[NormalizedCandle, ...]:
    """Impulse-and-retrace walk: the shape that actually triggers every family."""
    rng = random.Random(seed)
    candles: list[NormalizedCandle] = []
    price = Decimal("100")
    pending: Decimal | None = None
    for index in range(length):
        open_ = price
        if pending is not None:
            close, pending = pending, None
            spread = Decimal(rng.randint(0, 20)) / Decimal(100)
        elif rng.randint(0, 9) < 2:
            # Wick-dominant shapes. Without these the walk never produces a
            # pressure wick or a hammer/shooting star, because both need a
            # long wick relative to the body — which the coverage assertion
            # below catches rather than tolerates.
            shape = rng.randint(0, 3)
            if shape == 0:  # bullish pressure wick: lw .45 body .45 uw .10
                low = open_ - Decimal("0.45")
                close = open_ + Decimal("0.45")
                high = open_ + Decimal("0.55")
            elif shape == 1:  # hammer: lw .65 body .25 uw .10
                low = open_ - Decimal("0.65")
                close = open_ + Decimal("0.25")
                high = open_ + Decimal("0.35")
            elif shape == 2:  # bearish pressure wick
                high = open_ + Decimal("0.45")
                close = open_ - Decimal("0.45")
                low = open_ - Decimal("0.55")
            else:  # shooting star
                high = open_ + Decimal("0.65")
                close = open_ - Decimal("0.25")
                low = open_ - Decimal("0.35")
            candles.append(_candle(index, str(open_), str(high), str(low), str(close)))
            price = close
            continue
        elif rng.randint(0, 9) < 3:
            magnitude = Decimal(rng.randint(150, 320)) / Decimal(100)
            sign = 1 if rng.randint(0, 1) else -1
            close = open_ + magnitude * sign
            spread = Decimal(rng.randint(0, 12)) / Decimal(100)
            if rng.randint(0, 1):
                midpoint = (max(open_, close) + min(open_, close)) / Decimal(2)
                nudge = Decimal(rng.randint(5, 50)) / Decimal(100)
                pending = midpoint + (nudge if sign < 0 else -nudge)
        else:
            close = open_ + Decimal(rng.randint(-70, 70)) / Decimal(100)
            spread = Decimal(rng.randint(0, 60)) / Decimal(100)
        high = max(open_, close) + spread
        low = min(open_, close) - spread
        candles.append(_candle(index, str(open_), str(high), str(low), str(close)))
        price = close
        if price > Decimal("140") or price < Decimal("60"):
            price = Decimal("100")
    return tuple(candles)


def _run_pipeline(candles: tuple[NormalizedCandle, ...]) -> list[Any]:
    """Detection -> persistent identity -> persistent lifecycle -> projection."""
    atr_all = compute_atr_series(candles, 14)
    registry = M.run_frontier(list(candles), _CONFIG)

    states: list[Any] = []
    for poi in registry:
        direction = PoiDirection.BULLISH if poi.direction == 1 else PoiDirection.BEARISH
        cursor = L.PoiLifecycleCursor(
            zone_top=poi.zone_top,
            zone_bottom=poi.zone_bottom,
            direction=direction,
            availability_ms=poi.confirm_time,
            configuration=_CONFIG,
        )
        for t in range(len(candles)):
            cursor.advance(candles, atr_all, t)
        code, count, relevant, last = cursor.downstream_projection()
        states.append(
            G.P3PoiState(
                poi_type=poi.poi_type,
                direction=poi.direction,
                zone_bottom=poi.zone_bottom,
                zone_top=poi.zone_top,
                candidate_time=poi.candidate_time,
                confirm_time=poi.confirm_time,
                avail_time=poi.confirm_time,
                tier=poi.tier,
                src_first_time=poi.src_first_time,
                src_count=poi.src_count,
                src_last_time=poi.src_last_time,
                status=code,
                transition_count=count,
                relevant_count=relevant,
                last_transition_code=last[0],
                last_transition_event=last[1],
                last_transition_avail=last[2],
                tap_count=cursor.tap_count,
            )
        )
    return states


# ---------------------------------------------------------------------------
# Ordering totality — the property AD-1 requires before freezing the digest
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(10))
def test_canonical_ordering_is_total_over_everything_detectors_emit(
    seed: int,
) -> None:
    """Distinct POIs must never share a sort key.

    A collision would make the digest depend on insertion order, and AD-1
    forbids resolving that with an array index or identity bytes.
    """
    states = _run_pipeline(_stream(seed, 120))
    keys = [s.sort_key(_TICK) for s in states]
    assert len(keys) == len(set(keys)), (
        f"seed {seed}: {len(keys) - len(set(keys))} ordering collisions"
    )


def test_digest_is_independent_of_discovery_order() -> None:
    """Shuffling the registry must not move any hash."""
    states = _run_pipeline(_stream(4, 150))
    assert len(states) > 10
    shuffled = states[:]
    random.Random(99).shuffle(shuffled)
    assert G.overall_hashes(shuffled, _TICK) == G.overall_hashes(states, _TICK)
    assert G.family_hashes(shuffled, _TICK) == G.family_hashes(states, _TICK)
    assert G.lifecycle_hashes(shuffled, _TICK) == G.lifecycle_hashes(states, _TICK)


def test_hashes_are_deterministic_across_repeated_runs() -> None:
    first = _run_pipeline(_stream(11, 140))
    second = _run_pipeline(_stream(11, 140))
    assert G.overall_hashes(first, _TICK) == G.overall_hashes(second, _TICK)


def test_a_single_changed_field_moves_the_overall_hash() -> None:
    """A digest that ignored a field would hide a real divergence."""
    states = _run_pipeline(_stream(6, 120))
    assert len(states) > 0
    baseline = G.overall_hashes(states, _TICK)
    for field in ("status", "tap_count", "transition_count", "tier"):
        mutated = list(states)
        original = getattr(mutated[0], field)
        mutated[0] = type(mutated[0])(**{**mutated[0].__dict__, field: original + 1})
        assert G.overall_hashes(mutated, _TICK) != baseline, field


# ---------------------------------------------------------------------------
# Coverage — a green campaign must actually exercise P3 CORE
# ---------------------------------------------------------------------------


def test_campaign_covers_every_p3_core_type_and_family() -> None:
    seen_types: set[int] = set()
    for seed in range(14):
        for state in _run_pipeline(_stream(seed, 160)):
            seen_types.add(state.poi_type)
    missing = set(range(1, 17)) - seen_types
    assert not missing, f"candle-derived types never produced: {sorted(missing)}"

    families = {G.FAMILY_OF_TYPE[t] for t in seen_types}
    expected = set(G.FAMILIES) - {"reference_zone"}
    assert expected.issubset(families), f"families missing: {expected - families}"


def test_campaign_reaches_multiple_lifecycle_states() -> None:
    seen_status: set[int] = set()
    for seed in range(14):
        for state in _run_pipeline(_stream(seed, 160)):
            seen_status.add(state.status)
    assert 1 in seen_status, "no untouched POI"
    assert len(seen_status) >= 3, f"lifecycle barely exercised: {seen_status}"
    assert 10 in seen_status, "genuine invalidation never reached"


def test_counts_split_registry_into_active_and_terminal() -> None:
    states = _run_pipeline(_stream(2, 200))
    registry, active, terminal = G.counts(states)
    assert registry == len(states)
    assert active + terminal == registry
    assert terminal == sum(1 for s in states if s.status == 10)


# ---------------------------------------------------------------------------
# Contract shape
# ---------------------------------------------------------------------------


def test_digest_reuses_the_frozen_p2_primitives_unchanged() -> None:
    p2 = _load("_p3core_p2digest", "tests/parity_support/p2_digest.py")
    assert (G.MOD1, G.MOD2, G.BASE1, G.BASE2) == (
        p2.MOD1,
        p2.MOD2,
        p2.BASE1,
        p2.BASE2,
    )


def test_record_contains_no_uuid_or_rendering_state() -> None:
    names = {name for name, _kind in G.POI_FIELD_ORDER}
    for banned in ("record_id", "uuid", "colour", "color", "box", "line"):
        assert not any(banned in n for n in names), banned
    assert len(G.POI_FIELD_ORDER) == 18


def test_every_core_type_maps_to_exactly_one_family() -> None:
    assert set(G.FAMILY_OF_TYPE) == set(range(1, 19))
    assert set(G.FAMILY_OF_TYPE.values()) == set(G.FAMILIES)
