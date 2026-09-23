"""Batch == incremental for the Base axis AND formation ownership, all 4 arms.

Two independent switches now sit on the Base:

    size basis   total range (approved)  |  body (experiment)
    arrival      none at the detector    |  structural, assigned downstream

    A = range, no arrival   B = body, no arrival
    C = range, structural   D = body, structural

Symmetry of the two code paths was argued when the axis landed; an argument is
not a proof. Arms A and B walk every prefix of a synthetic series at the
detector itself. Arms C and D walk prefixes of the real M15 capture, because
a structural arrival needs real structure to exist at all, and compare the
full record: identity, source ids, zone, availability, arrival direction,
arrival leg id, the instant the arrival became known, the family, and the
ownership relationships with their activation instants.

No final-state reconstruction: each prefix is judged on its own knowledge.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, _detect_bundle_candidates
from btmm_ai_scanner.poi.base_arrival import assign_base_arrival
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.detector_frontier import _evaluate_new_bases
from btmm_ai_scanner.poi.formation_ownership import (
    BASE_TYPES,
    resolve_formation_ownership,
)
from btmm_ai_scanner.poi.single_candle_reversals import (
    detect_single_candle_reversals,
)
from tests.unit._arrival_fixtures import M15_CSV, m15_eurusd, structure_of
from tests.unit.test_a6a_detector_frontiers import (
    _MCONFIG,
    _PCONFIG,
    _candle,
    _HashIdentityProvider,
)

#: Produces THREE bases across both departure directions, so the equality
#: assertions cover more than one shape. It establishes no structure, which is
#: why arms C and D use the real capture instead.
_SHAPE = [
    ("99.00", "100.10", "99.00", "100.05"),
    ("100.02", "100.10", "100.00", "100.06"),
    ("100.06", "100.10", "100.00", "100.03"),
    ("100.05", "101.20", "100.05", "101.10"),
    ("101.10", "101.20", "101.00", "101.05"),
    ("101.05", "101.15", "101.00", "101.10"),
    ("101.08", "101.12", "101.02", "101.06"),
    ("101.06", "101.10", "99.80", "99.90"),
    ("99.90", "100.00", "99.70", "99.85"),
    ("99.85", "99.95", "99.75", "99.80"),
]


#: FX-tick twins for the real M15 capture (arms C and D, and the bundle path).
_M15_PCONFIG = _PCONFIG.model_copy(update={"minimum_price_tick": Decimal("0.00001")})
_M15_MCONFIG = _MCONFIG.model_copy(update={"minimum_price_tick": Decimal("0.00001")})

#: Arms C and D, and the bundle path, need the real capture: a structural
#: arrival cannot be exercised where no structure exists.
_needs_capture = pytest.mark.skipif(
    not M15_CSV.exists(), reason="RC5 M15 forensic capture not present"
)


def _series():
    return [_candle(i, o, h, low, c) for i, (o, h, low, c) in enumerate(_SHAPE)]


def _base_signature(candidates) -> list[tuple]:
    """Everything about a Base that must survive the incremental path."""
    rows = [
        (
            c.poi_type,
            c.base_family,
            c.source_candle_record_ids,
            c.zone_top,
            c.zone_bottom,
            c.availability_time_utc,
        )
        for c in candidates
        if c.poi_type in BASE_TYPES
    ]
    return sorted(rows, key=repr)


def _ownership_signature(candidates) -> list[tuple]:
    return sorted(
        (
            (r.owner_key, r.member_key, r.relationship, r.reason, r.active_from_utc)
            for r in resolve_formation_ownership(list(candidates))
        ),
        key=repr,
    )


def _assert_paths_agree(cfg) -> set:
    """Walk every prefix under one config; return the families seen."""
    candles = _series()
    seen: set = set()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        batch = detect_bases(prefix, cfg)
        incremental: list[object] = []
        for m in range(1, k + 1):
            ring = prefix[max(0, m - 21) : m]
            atr = compute_atr_series(prefix[:m], 14)[m - 1]
            incremental.extend(_evaluate_new_bases(ring, atr, cfg))
        assert _base_signature(batch) == _base_signature(incremental), (
            f"Base family/geometry diverged at prefix {k}"
        )
        patterns = list(detect_single_candle_reversals(prefix, cfg))
        assert _ownership_signature(list(batch) + patterns) == _ownership_signature(
            incremental + patterns
        ), f"ownership diverged at prefix {k}"
        seen.update(_base_signature(batch))
    return seen


def test_batch_equals_incremental_under_the_body_size_basis() -> None:
    """Arm B: the experimental size basis must be identical in both paths."""
    rows = _assert_paths_agree(_PCONFIG)
    assert rows, "arm B produced no Base; the assertions were vacuous"
    assert {row[1] for row in rows} == {None}, "the detector invented an arrival"


def test_batch_equals_incremental_for_base_family_and_geometry() -> None:
    """Every prefix, both paths, exact equality of family AND geometry.

    Compared at the Base detector itself rather than after the structural gate:
    that is where the family axis lives, and it keeps the assertion sharp
    instead of depending on a gate that can legitimately drop candidates.
    """
    candles = _series()
    seen_families: set[object] = set()

    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        batch = detect_bases(prefix, _PCONFIG)

        # incremental: every base whose DEPARTURE is the newest candle, taken
        # over the whole stream, must reproduce the batch set exactly.
        incremental: list[object] = []
        for m in range(1, k + 1):
            ring = prefix[max(0, m - 21) : m]
            atr = compute_atr_series(prefix[:m], 14)[m - 1] if m >= 1 else None
            incremental.extend(_evaluate_new_bases(ring, atr, _PCONFIG))

        assert _base_signature(batch) == _base_signature(incremental), (
            f"Base family/geometry diverged at prefix {k}"
        )
        seen_families.update(_base_signature(batch))

    assert seen_families, "fixture never produced a Base; assertions were vacuous"
    assert {row[0] for row in seen_families} == set(BASE_TYPES), (
        "both departure directions must be exercised"
    )


def test_ownership_records_are_identical_from_either_candidate_path() -> None:
    """Ownership is a pure function of the candidate set, so equal candidate
    sets must yield byte-identical relationship records -- including the
    activation instants that carry the causality guarantee."""
    candles = _series()
    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        batch = list(detect_bases(prefix, _PCONFIG))
        incremental: list[object] = []
        for m in range(1, k + 1):
            ring = prefix[max(0, m - 21) : m]
            atr = compute_atr_series(prefix[:m], 14)[m - 1]
            incremental.extend(_evaluate_new_bases(ring, atr, _PCONFIG))
        patterns = list(detect_single_candle_reversals(prefix, _PCONFIG))
        assert _ownership_signature(batch + patterns) == _ownership_signature(
            incremental + patterns
        ), f"ownership diverged at prefix {k}"


@_needs_capture
def test_the_full_bundle_path_also_leaves_the_arrival_unresolved() -> None:
    """The detector is reached through several callers; none of them may slip a
    candle-derived arrival back in.

    Run on the real capture, not the synthetic shape: the bundle path applies
    the structural context gate, which rejects every candidate as neutral when
    no structure exists, so a structureless fixture makes this vacuous.
    """
    candles = m15_eurusd()
    idp = _HashIdentityProvider()
    measurement = analyze_market_measurements(candles, _M15_MCONFIG, idp)
    bundle = PoiTimeframeInput(
        timeframe=Timeframe.M15,
        candles=candles,
        measurement_analysis=measurement,
    )
    seen = [
        c
        for c in _detect_bundle_candidates(bundle, _M15_PCONFIG, idp)
        if c.poi_type in BASE_TYPES
    ]
    assert seen, "bundle path produced no Base; the assertion was vacuous"
    assert all(c.base_family is None for c in seen)


# ---------------------------------------------------------------------------
# arms C and D: the structural arrival, on real structure
# ---------------------------------------------------------------------------


def _arrival_signature(bases, facts) -> list[tuple]:
    """Everything the arrival layer decides, plus the identity it hangs on."""
    rows = []
    for base in bases:
        key = (base.poi_type, base.source_candle_record_ids)
        fact = facts[key]
        rows.append(
            (
                key,
                base.zone_top,
                base.zone_bottom,
                base.availability_time_utc,
                base.base_family,
                fact.arrival_direction,
                fact.arrival_leg_id,
                fact.arrival_known_from_utc,
                fact.arrival_reference_utc,
            )
        )
    return sorted(rows, key=repr)


def _incremental_bases_by_departure(candles, cfg):
    """Bases keyed by the index of the candle that confirmed them.

    Ring and ATR depend only on the departure index, so this is computed once
    and sliced per prefix instead of re-run inside the prefix loop.
    """
    out: dict[int, list] = {}
    atr = compute_atr_series(candles, 14)
    for m in range(1, len(candles) + 1):
        ring = candles[max(0, m - 21) : m]
        found = _evaluate_new_bases(ring, atr[m - 1], cfg)
        if found:
            out[m] = list(found)
    return out


def _assert_structural_arms_agree(cfg) -> list[tuple]:
    candles = m15_eurusd()
    incremental_by_m = _incremental_bases_by_departure(candles, cfg)
    last: list[tuple] = []

    for k in range(60, len(candles) + 1, 10):
        prefix = candles[:k]
        timeline, walk = structure_of(prefix, _M15_MCONFIG)

        batch, batch_facts = assign_base_arrival(
            detect_bases(prefix, cfg), timeline, walk
        )
        incremental_raw = [
            base for m, found in incremental_by_m.items() if m <= k for base in found
        ]
        incremental, incremental_facts = assign_base_arrival(
            incremental_raw, timeline, walk
        )

        assert _arrival_signature(batch, batch_facts) == _arrival_signature(
            incremental, incremental_facts
        ), f"arrival/geometry diverged at prefix {k}"

        patterns = list(detect_single_candle_reversals(prefix, cfg))
        assert _ownership_signature([*batch, *patterns]) == _ownership_signature(
            [*incremental, *patterns]
        ), f"ownership diverged at prefix {k}"
        last = _arrival_signature(batch, batch_facts)
    return last


@_needs_capture
def test_arm_c_batch_equals_incremental_with_structural_arrival() -> None:
    """Arm C: approved size basis, structural arrival."""
    rows = _assert_structural_arms_agree(_M15_PCONFIG)
    assert rows, "arm C produced no Base; the assertions were vacuous"


@_needs_capture
def test_arm_d_batch_equals_incremental_with_body_size_and_structural_arrival() -> None:
    """Arm D: both switches on -- the combination the author is evaluating.

    Families must actually be resolved here, or the equality is only proving
    that two paths agree about nothing.
    """
    rows = _assert_structural_arms_agree(_M15_PCONFIG)
    assert rows, "arm D produced no Base; the assertions were vacuous"
    families = {row[4] for row in rows}
    assert families - {None}, f"no family was ever resolved: {families}"
