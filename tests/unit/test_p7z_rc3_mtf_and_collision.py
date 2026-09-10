"""RC3 presentation: host-timeframe eligibility and annotation collision.

Includes the mutants the campaign names. Every assertion here is about what is
DRAWN; none of it touches detection, geometry, lifecycle or scoring.
"""

from __future__ import annotations

import itertools
import random

import pytest

from tests.parity_support.p7z_mtf_presentation import (
    TF_RANK,
    AnnotationDecision,
    ZoneForDisplay,
    collision_groups,
    host_eligible,
    resolve_annotations,
    timeframe_rank,
)
from tests.parity_support.p7z_zone_model import UNKNOWN_TF_LABEL, timeframe_label

# ---- timeframe rank ---------------------------------------------------------


def test_the_rank_order_is_strictly_increasing_in_duration() -> None:
    ordered = ["M1", "M5", "M15", "H1", "H4", "H6", "H8", "H12", "D1", "W1"]
    ranks = [timeframe_rank(t) for t in ordered]
    assert all(a < b for a, b in itertools.pairwise(ranks))


def test_an_unrecognised_token_has_no_rank() -> None:
    """None, not a sentinel: an unnameable timeframe must not sort silently."""
    assert timeframe_rank(UNKNOWN_TF_LABEL) is None
    assert timeframe_rank("") is None
    assert timeframe_rank("H5") is None


def test_every_token_the_formatter_emits_for_a_real_host_is_ranked() -> None:
    for period in (
        "1",
        "5",
        "15",
        "60",
        "240",
        "360",
        "480",
        "720",
        "1D",
        "1W",
        "D",
        "W",
    ):
        token = timeframe_label(period)
        assert token != UNKNOWN_TF_LABEL, period
        assert timeframe_rank(token) is not None, (period, token)


# ---- host eligibility -------------------------------------------------------


@pytest.mark.parametrize(
    ("source", "host", "expected"),
    [
        ("M1", "D1", False),
        ("H1", "D1", False),
        ("H4", "D1", False),
        ("D1", "D1", True),
        ("W1", "D1", True),
        ("D1", "H4", True),
        ("W1", "H4", True),
        ("H4", "H4", True),
        ("M15", "H4", False),
        ("M1", "W1", False),
        ("D1", "W1", False),
        ("W1", "W1", True),
        ("M1", "M1", True),
        ("W1", "M1", True),
        ("D1", "M1", True),
        ("H4", "H6", False),
        ("H8", "H6", True),
        ("D1", "H12", True),
    ],
)
def test_host_eligibility_is_origin_at_or_above_host(source, host, expected):
    assert host_eligible(source, host) is expected


def test_an_unnameable_timeframe_is_never_eligible() -> None:
    """Release mode suppresses rather than rendering TF? to a user."""
    assert host_eligible(UNKNOWN_TF_LABEL, "D1") is False
    assert host_eligible("D1", UNKNOWN_TF_LABEL) is False


def test_eligibility_is_reflexive_on_every_ranked_token() -> None:
    for token in TF_RANK:
        assert host_eligible(token, token) is True


def test_eligibility_is_transitive() -> None:
    tokens = ["M1", "M15", "H1", "H4", "D1", "W1"]
    for a, b, c in itertools.product(tokens, repeat=3):
        if host_eligible(a, b) and host_eligible(b, c):
            assert host_eligible(a, c)


def test_mutant_a_lower_timeframe_may_not_appear_on_a_daily_host() -> None:
    for lower in ("M1", "M5", "M15", "H1", "H4", "H12"):
        assert host_eligible(lower, "D1") is False


def test_mutant_a_lower_timeframe_may_not_appear_on_a_weekly_host() -> None:
    for lower in ("M1", "H4", "D1"):
        assert host_eligible(lower, "W1") is False


def test_mutant_reversing_the_comparison_breaks_the_daily_case() -> None:
    """The rule is origin >= host, not host >= origin."""
    assert host_eligible("W1", "H4") and not host_eligible("H4", "W1")


# ---- collision grouping -----------------------------------------------------


def _z(idx, token="H4", top=100.0, bottom=90.0, t=1000, dist=5.0):
    return ZoneForDisplay(idx, token, top, bottom, t, dist)


def test_disjoint_price_intervals_do_not_collide() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=80, bottom=70)]
    assert collision_groups(zones) == [[0], [1]]


def test_overlapping_price_intervals_collide() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=95, bottom=85)]
    assert collision_groups(zones) == [[0, 1]]


def test_a_shared_boundary_counts_as_a_collision() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=90, bottom=80)]
    assert collision_groups(zones) == [[0, 1]]


def test_collision_is_transitive_through_a_middle_zone() -> None:
    """A and C never touch, but B's text sits between them either way."""
    zones = [
        _z(0, top=100, bottom=95),
        _z(1, top=96, bottom=85),
        _z(2, top=86, bottom=80),
    ]
    assert collision_groups(zones) == [[0, 1, 2]]


def test_group_membership_is_independent_of_input_order() -> None:
    base = [
        _z(0, top=100, bottom=95),
        _z(1, top=96, bottom=85),
        _z(2, top=50, bottom=40),
    ]
    expected = {frozenset(g) for g in collision_groups(base)}
    for perm in itertools.permutations(range(3)):
        shuffled = [base[i] for i in perm]
        got = {frozenset(perm[i] for i in g) for g in collision_groups(shuffled)}
        assert got == expected


def test_an_empty_input_produces_no_groups() -> None:
    assert collision_groups([]) == []


# ---- annotation ownership ---------------------------------------------------


def test_exactly_one_owner_per_group() -> None:
    zones = [
        _z(0, top=100, bottom=90),
        _z(1, top=95, bottom=85),
        _z(2, top=50, bottom=40),
    ]
    d = resolve_annotations(zones)
    for group in d.groups:
        assert len(set(group) & d.owners) == 1


def test_every_zone_is_either_an_owner_or_suppressed_never_both() -> None:
    zones = [_z(i, top=100 - i, bottom=90 - i) for i in range(6)]
    d = resolve_annotations(zones)
    assert d.owners.isdisjoint(d.suppressed)
    assert d.owners | d.suppressed == set(range(6))


def test_the_higher_timeframe_wins() -> None:
    zones = [_z(0, token="H4"), _z(1, token="D1"), _z(2, token="M15")]
    assert resolve_annotations(zones).owners == {1}


def test_at_equal_timeframe_the_nearer_zone_wins() -> None:
    zones = [_z(0, dist=9.0), _z(1, dist=2.0), _z(2, dist=5.0)]
    assert resolve_annotations(zones).owners == {1}


def test_at_equal_timeframe_and_distance_the_newer_source_wins() -> None:
    zones = [_z(0, t=1000), _z(1, t=3000), _z(2, t=2000)]
    assert resolve_annotations(zones).owners == {1}


def test_the_final_tie_break_is_the_lowest_stable_id() -> None:
    zones = [_z(7), _z(3), _z(5)]
    d = resolve_annotations(zones)
    assert d.owners == {1}, "index 1 carries stable_id 3"


def test_priority_is_lexicographic_and_timeframe_outranks_distance() -> None:
    """A far daily zone still beats a near 15-minute one."""
    zones = [_z(0, token="M15", dist=0.0), _z(1, token="D1", dist=500.0)]
    assert resolve_annotations(zones).owners == {1}


def test_suppression_never_removes_a_zone() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=95, bottom=85)]
    d = resolve_annotations(zones)
    assert len(d.owners) + len(d.suppressed) == len(zones)


# ---- collision mutants ------------------------------------------------------


def test_mutant_two_owners_in_one_group_is_detectable() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=95, bottom=85)]
    d = resolve_annotations(zones)
    assert len(d.groups) == 1
    assert len(d.owners) == 1


def test_mutant_a_lower_timeframe_beating_a_higher_one_is_detectable() -> None:
    zones = [_z(0, token="D1", dist=99.0), _z(1, token="M1", dist=0.1)]
    assert resolve_annotations(zones).owners == {0}


def test_mutant_a_farther_zone_beating_a_nearer_one_is_detectable() -> None:
    zones = [_z(0, dist=50.0), _z(1, dist=1.0)]
    assert resolve_annotations(zones).owners == {1}


def test_mutant_an_older_source_beating_a_newer_one_is_detectable() -> None:
    zones = [_z(0, t=10), _z(1, t=20)]
    assert resolve_annotations(zones).owners == {1}


def test_mutant_an_unstable_tie_break_is_detectable() -> None:
    """Identical on every axis but the id: the result must not depend on order."""
    zones = [_z(9), _z(4), _z(6)]
    first = resolve_annotations(zones).owners
    for perm in itertools.permutations(range(3)):
        shuffled = [zones[i] for i in perm]
        won = next(iter(resolve_annotations(shuffled).owners))
        assert shuffled[won].stable_id == 4
    assert first == {1}


def test_mutant_suppressing_text_must_not_drop_the_box() -> None:
    zones = [
        _z(0, top=100, bottom=90),
        _z(1, top=95, bottom=85),
        _z(2, top=94, bottom=84),
    ]
    d = resolve_annotations(zones)
    assert d.owners | d.suppressed == {0, 1, 2}


def test_mutant_geometry_is_never_merged_by_the_collision_layer() -> None:
    zones = [_z(0, top=100, bottom=90), _z(1, top=95, bottom=85)]
    d = resolve_annotations(zones)
    assert isinstance(d, AnnotationDecision)
    assert zones[0].top == 100 and zones[1].top == 95
    assert zones[0].bottom == 90 and zones[1].bottom == 85


# ---- randomized model -------------------------------------------------------


@pytest.mark.parametrize("seed", [1, 7, 13, 42, 99, 123, 777, 2024])
def test_randomized_states_always_yield_one_owner_per_group(seed: int) -> None:
    rng = random.Random(seed)
    tokens = list(TF_RANK)
    for _ in range(250):
        n = rng.randint(0, 12)
        zones = []
        for _ in range(n):
            bottom = rng.uniform(0, 200)
            zones.append(
                ZoneForDisplay(
                    stable_id=rng.randint(0, 999),
                    source_token=rng.choice(tokens),
                    top=bottom + rng.uniform(0.01, 30),
                    bottom=bottom,
                    source_time=rng.randint(0, 10**6),
                    distance=rng.uniform(0, 500),
                )
            )
        d = resolve_annotations(zones)
        assert d.owners | d.suppressed == set(range(n))
        assert d.owners.isdisjoint(d.suppressed)
        seen: set[int] = set()
        for group in d.groups:
            assert len(set(group) & d.owners) == 1
            assert not (set(group) & seen)
            seen.update(group)
        assert seen == set(range(n))


@pytest.mark.parametrize("seed", [3, 11, 29, 57])
def test_randomized_states_are_order_independent(seed: int) -> None:
    rng = random.Random(seed)
    tokens = list(TF_RANK)
    for _ in range(120):
        n = rng.randint(2, 9)
        zones = []
        for _ in range(n):
            bottom = rng.uniform(0, 100)
            zones.append(
                ZoneForDisplay(
                    rng.randint(0, 99),
                    rng.choice(tokens),
                    bottom + rng.uniform(0.01, 20),
                    bottom,
                    rng.randint(0, 10**5),
                    rng.uniform(0, 100),
                )
            )
        winners = {zones[i].stable_id for i in resolve_annotations(zones).owners}
        order = list(range(n))
        rng.shuffle(order)
        shuffled = [zones[i] for i in order]
        again = {shuffled[i].stable_id for i in resolve_annotations(shuffled).owners}
        assert winners == again


@pytest.mark.parametrize("seed", [5, 17, 61])
def test_randomized_host_filter_never_lets_a_lower_timeframe_through(seed):
    rng = random.Random(seed)
    tokens = list(TF_RANK)
    for _ in range(500):
        host = rng.choice(tokens)
        source = rng.choice(tokens)
        if host_eligible(source, host):
            assert TF_RANK[source] >= TF_RANK[host]
        else:
            assert TF_RANK[source] < TF_RANK[host]
