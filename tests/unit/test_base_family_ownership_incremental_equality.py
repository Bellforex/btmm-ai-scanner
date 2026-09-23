"""Batch == incremental for the Base family axis AND formation ownership.

Symmetry of the two code paths was argued when the family axis landed; an
argument is not a proof. This walks every prefix of a real series, runs the
batch detector and the incremental frontier over the same prefix, and requires
exact equality of the family, the source identity, the zone, the availability,
and the ownership records with their activation instants.

No final-state reconstruction: each prefix is judged on its own knowledge.
"""

from __future__ import annotations

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, _detect_bundle_candidates
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.detector_frontier import _evaluate_new_bases
from btmm_ai_scanner.poi.formation_ownership import (
    BASE_TYPES,
    resolve_formation_ownership,
)
from btmm_ai_scanner.poi.single_candle_reversals import (
    detect_single_candle_reversals,
)
from tests.unit.test_a6a_detector_frontiers import (
    _MCONFIG,
    _PCONFIG,
    _candle,
    _HashIdentityProvider,
)

#: Produces THREE bases across three different families -- RALLY_BASE_RALLY,
#: RALLY_BASE_DROP and DROP_BASE_DROP -- so the equality assertions cover more
#: than one arrival/departure combination rather than a single lucky shape.
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


#: Arm B of the size-basis experiment. Batch and frontier must agree under
#: BOTH bases -- a switch implemented in only one path would be worse than no
#: switch at all.
_PCONFIG_BODY = _PCONFIG.model_copy(update={"base_size_uses_body": True})


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
        seen.update(row[1] for row in _base_signature(batch))
    return seen


def test_batch_equals_incremental_under_the_body_size_basis() -> None:
    """Arm B: the experimental size basis must be identical in both paths."""
    seen = _assert_paths_agree(_PCONFIG_BODY)
    assert seen, "arm B produced no Base; the assertions were vacuous"


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
        seen_families.update(row[1] for row in _base_signature(batch))

    assert seen_families, "fixture never produced a Base; assertions were vacuous"
    assert len(seen_families) >= 2, f"only one family exercised: {seen_families}"


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


def test_family_is_assigned_on_the_prefix_that_confirms_the_base() -> None:
    """Causal: a Base's family is known as soon as the Base is, never later."""
    candles = _series()
    idp = _HashIdentityProvider()
    seen: dict[tuple, object] = {}

    for k in range(1, len(candles) + 1):
        prefix = tuple(candles[:k])
        measurement = analyze_market_measurements(prefix, _MCONFIG, idp)
        bundle = PoiTimeframeInput(
            timeframe=Timeframe.M1,
            candles=prefix,
            measurement_analysis=measurement,
        )
        for candidate in _detect_bundle_candidates(bundle, _PCONFIG, idp):
            if candidate.poi_type not in BASE_TYPES:
                continue
            key = (candidate.poi_type, candidate.source_candle_record_ids)
            if key in seen:
                # never revised on a later prefix
                assert seen[key] == candidate.base_family
            else:
                seen[key] = candidate.base_family
