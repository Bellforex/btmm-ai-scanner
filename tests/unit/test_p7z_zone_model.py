"""P7-Z POI-zone display-layer hardening: offline, randomized, mutation-
tested proof that box/label creation, extension, terminal-freeze, and
bounded-window eviction are all correct — before any of this logic is
ported to Pine.

WHY OFFLINE RATHER THAN ONLY LIVE TRADINGVIEW ROUNDS
---------------------------------------------------------
Live FXCM observation (`BTRC_V1_P7Z_POI_VISUALIZATION_CLOSURE.md`) proves
the real chart renders correctly across whatever active counts actually
occur during one live session. It cannot cheaply exercise the rare edges
that matter most for a resource-bounded, identity-keyed drawing layer:
exactly-zero active, exactly-at-capacity, overflow far beyond capacity
(100+), and the object-leak/cross-layer-truncation mutants a broken build
must never pass unnoticed. This suite gives that at effectively zero
marginal cost per run.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    TIER_STANDARD,
    TIER_STRONG,
    UNKNOWN_TYPE_LABEL,
    P7ZDisplayState,
    PoiGeometry,
    _P7ZDisplayStateNeverEvicts,
    _P7ZDisplayStateUsesCapAsEligibility,
    type_label,
    zone_label,
)


def _geo(idx: int, *, terminal: bool = False) -> PoiGeometry:
    return PoiGeometry(
        idx=idx,
        poi_type=1 + (idx % 18),
        direction=DIRECTION_BULLISH if idx % 2 == 0 else DIRECTION_BEARISH,
        zone_top=100.0 + idx,
        zone_bottom=90.0 + idx,
        avail_time_ms=1_000_000 + idx * 900_000,
        tier=TIER_STRONG if idx % 3 == 0 else TIER_STANDARD,
    )


# --------------------------------------------------------------- type map


def test_every_one_of_the_18_core_types_has_a_distinct_label() -> None:
    labels = {type_label(t) for t in range(1, 19)}
    assert len(labels) == 18
    assert UNKNOWN_TYPE_LABEL not in labels


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (1, "BUY OB"),
        (2, "SELL OB"),
        (3, "BUY FVG"),
        (4, "SELL FVG"),
        (5, "B2S"),
        (6, "S2B"),
        (7, "BASE RALLY"),
        (8, "BASE DROP"),
        (9, "BULL PRESSURE"),
        (10, "BEAR PRESSURE"),
        (11, "BULL ENGULF"),
        (12, "BEAR ENGULF"),
        (13, "HAMMER"),
        (14, "SHOOTING STAR"),
        (15, "MORNING STAR"),
        (16, "EVENING STAR"),
        (17, "SUPPORT"),
        (18, "RESISTANCE"),
    ],
)
def test_type_label_mapping_matches_the_frozen_table(code: int, expected: str) -> None:
    assert type_label(code) == expected


@pytest.mark.parametrize("code", [0, 19, 20, 21, 32, 99, -1])
def test_out_of_range_type_codes_map_to_unknown_never_a_real_name(code: int) -> None:
    assert type_label(code) == UNKNOWN_TYPE_LABEL


def test_zone_label_appends_strong_only_for_strong_tier() -> None:
    strong = zone_label(1, TIER_STRONG, "M15")
    standard = zone_label(1, TIER_STANDARD, "M15")
    assert strong == "M15 • BUY OB • STRONG"
    assert standard == "M15 • BUY OB"


def test_zone_label_uses_the_given_timeframe_verbatim() -> None:
    assert zone_label(17, TIER_STANDARD, "H1").startswith("H1 • ")
    assert zone_label(17, TIER_STANDARD, "M5").startswith("M5 • ")


# ---------------------------------------------------------- basic lifecycle


def test_zero_active_produces_zero_boxes() -> None:
    state = P7ZDisplayState(max_visible=16)
    render = state.advance_bar({}, {}, 1_000_000)
    assert render.active_count == 0
    assert render.shown_count == 0
    assert render.boxes == ()
    assert render.created_ids == frozenset()
    assert render.removed_ids == frozenset()


def test_zero_active_after_prior_activity_leaves_no_stale_boxes() -> None:
    state = P7ZDisplayState(max_visible=16)
    state.advance_bar({0: False, 1: False}, {0: _geo(0), 1: _geo(1)}, 1_000_000)
    render = state.advance_bar({}, {}, 1_900_000, known_ids=frozenset())
    assert render.boxes == ()
    assert render.removed_ids == {0, 1}


def test_one_active_produces_exactly_one_box_and_label() -> None:
    state = P7ZDisplayState(max_visible=16)
    render = state.advance_bar({5: False}, {5: _geo(5)}, 1_000_000)
    assert render.active_count == 1
    assert render.shown_count == 1
    assert len(render.boxes) == 1
    box = render.boxes[0]
    assert box.idx == 5
    assert box.label_text != ""
    assert render.created_ids == {5}


@pytest.mark.parametrize("n", [2, 5, 8, 12, 20, 137])
def test_n_active_within_or_beyond_capacity_shows_bounded_count(n: int) -> None:
    max_visible = 16
    state = P7ZDisplayState(max_visible=max_visible)
    status = {i: False for i in range(n)}
    geo = {i: _geo(i) for i in range(n)}
    render = state.advance_bar(status, geo, 1_000_000)
    assert render.active_count == n
    assert render.shown_count == min(n, max_visible)
    assert len(render.boxes) == min(n, max_visible)
    assert [b.idx for b in render.boxes] == sorted(range(n))[: min(n, max_visible)]


# ----------------------------------------------- geometry and identity


def test_box_geometry_is_exact_p3_boundaries_never_swapped_by_direction() -> None:
    state = P7ZDisplayState(max_visible=16)
    bull = _geo(2)  # even -> bullish
    bear = _geo(3)  # odd -> bearish
    render = state.advance_bar({2: False, 3: False}, {2: bull, 3: bear}, 5_000_000)
    by_idx = {b.idx: b for b in render.boxes}
    assert by_idx[2].zone_top == bull.zone_top
    assert by_idx[2].zone_bottom == bull.zone_bottom
    assert by_idx[3].zone_top == bear.zone_top
    assert by_idx[3].zone_bottom == bear.zone_bottom
    # Direction never flips which field is "top" vs "bottom".
    assert by_idx[2].zone_top > by_idx[2].zone_bottom
    assert by_idx[3].zone_top > by_idx[3].zone_bottom


def test_left_edge_is_availability_time_not_bar_time_or_candidate_time() -> None:
    geo = _geo(9)
    state = P7ZDisplayState(max_visible=16)
    render = state.advance_bar({9: False}, {9: geo}, 50_000_000)
    box = render.boxes[0]
    assert box.left_time_ms == geo.avail_time_ms
    assert box.left_time_ms != 50_000_000


def test_two_distinct_pois_sharing_price_and_type_get_distinct_boxes() -> None:
    """Identity must be the registry index, never price/type/direction."""
    geo_a = PoiGeometry(
        idx=1,
        poi_type=1,
        direction=1,
        zone_top=100.0,
        zone_bottom=90.0,
        avail_time_ms=1,
        tier=1,
    )
    geo_b = PoiGeometry(
        idx=2,
        poi_type=1,
        direction=1,
        zone_top=100.0,
        zone_bottom=90.0,
        avail_time_ms=2,
        tier=1,
    )
    state = P7ZDisplayState(max_visible=16)
    render = state.advance_bar({1: False, 2: False}, {1: geo_a, 2: geo_b}, 10)
    assert {b.idx for b in render.boxes} == {1, 2}
    assert len(render.boxes) == 2  # not merged into one


# --------------------------------------------------------- extend / freeze


def test_box_extends_right_edge_while_non_terminal() -> None:
    geo = _geo(4)
    state = P7ZDisplayState(max_visible=16)
    state.advance_bar({4: False}, {4: geo}, 1_000_000)
    render = state.advance_bar({4: False}, {4: geo}, 2_000_000)
    box = render.boxes[0]
    assert box.right_time_ms == 2_000_000
    assert box.idx in render.updated_ids
    assert box.idx not in render.created_ids


def test_box_freezes_on_the_terminal_bar_but_is_still_shown_that_bar() -> None:
    geo = _geo(4)
    state = P7ZDisplayState(max_visible=16)
    state.advance_bar({4: False}, {4: geo}, 1_000_000)
    state.advance_bar({4: False}, {4: geo}, 2_000_000)
    # Final-pass bar: still eligible (previously active), now terminal.
    render = state.advance_bar({4: True}, {4: geo}, 3_000_000)
    assert len(render.boxes) == 1
    box = render.boxes[0]
    assert box.frozen is True
    assert box.right_time_ms == 3_000_000  # extends THROUGH the terminal bar


def test_box_is_removed_the_bar_after_it_leaves_eligibility() -> None:
    geo = _geo(4)
    state = P7ZDisplayState(max_visible=16)
    state.advance_bar({4: False}, {4: geo}, 1_000_000)
    state.advance_bar({4: True}, {4: geo}, 2_000_000)  # final pass
    render = state.advance_bar({}, {}, 3_000_000, known_ids=frozenset())
    assert render.boxes == ()
    assert render.removed_ids == {4}


def test_a_terminal_poi_cannot_resurrect_a_box_after_its_final_pass() -> None:
    """`resolve_eligible_and_next` itself (the frozen P5 loop contract)
    already refuses to re-admit a POI once its one final-pass bar has
    happened -- even if `status_by_idx` is (incorrectly) passed again on a
    later bar, it can no longer appear in the eligible set, so no box can
    be resurrected or re-extended for it."""
    geo = _geo(4)
    state = P7ZDisplayState(max_visible=16)
    state.advance_bar({4: False}, {4: geo}, 1_000_000)
    state.advance_bar({4: True}, {4: geo}, 2_000_000)  # final pass; now removed
    render = state.advance_bar(
        {4: True}, {4: geo}, known_ids=frozenset({4}), bar_time_ms=9_000_000
    )
    assert render.boxes == ()


# --------------------------------------------------- stale-box prevention


def test_stale_box_removed_when_display_selection_changes() -> None:
    state = P7ZDisplayState(max_visible=1)
    state.advance_bar({0: False}, {0: _geo(0)}, 1_000_000)
    # idx 0 goes terminal+finalized and leaves eligibility; idx 1 takes its slot.
    render = state.advance_bar(
        {1: False}, {1: _geo(1)}, 2_000_000, known_ids=frozenset({1})
    )
    assert render.removed_ids == {0}
    assert {b.idx for b in render.boxes} == {1}


def test_no_duplicate_box_for_the_same_poi_across_many_bars() -> None:
    geo = _geo(7)
    state = P7ZDisplayState(max_visible=16)
    for bar_ms in range(1_000_000, 1_010_000, 1_000):
        render = state.advance_bar({7: False}, {7: geo}, bar_ms)
        assert len(render.boxes) == 1
    assert render.created_ids == frozenset() or bar_ms == 1_000_000


# --------------------------------------------------------------- overflow


def test_display_overflow_never_truncates_the_engine_active_count() -> None:
    """Phase 3/21: P7-Z drawn count is bounded; the underlying eligible
    (engine) count reported alongside it must reflect the FULL universe."""
    max_visible = 16
    n_active = 101
    state = P7ZDisplayState(max_visible=max_visible)
    status = {i: False for i in range(n_active)}
    geo = {i: _geo(i) for i in range(n_active)}
    render = state.advance_bar(status, geo, 1_000_000)
    assert render.active_count == 101
    assert render.shown_count == max_visible
    assert len(render.boxes) == max_visible


def test_newest_poi_waits_for_a_slot_when_capacity_is_full_ascending_order() -> None:
    """Documents the accepted V1 behavior: ascending-index-first-N means a
    brand-new POI is not drawn until an older eligible one frees a slot --
    'displayed' is not 'best' or 'newest', matching P7's own table rule."""
    state = P7ZDisplayState(max_visible=2)
    status = {0: False, 1: False, 2: False}
    geo = {i: _geo(i) for i in range(3)}
    render = state.advance_bar(status, geo, 1_000_000)
    assert {b.idx for b in render.boxes} == {0, 1}
    assert 2 not in {b.idx for b in render.boxes}


# ---------------------------------------------------------- resource stress


def test_bounded_box_count_under_heavy_repeated_churn() -> None:
    max_visible = 16
    state = P7ZDisplayState(max_visible=max_visible)
    rng = random.Random(1234)
    next_idx = 0
    known: set[int] = set()
    bar_ms = 1_000_000
    for _ in range(500):
        if rng.random() < 0.3:
            known.add(next_idx)
            next_idx += 1
        terminal_now = {i for i in known if rng.random() < 0.05}
        status = {i: (i in terminal_now) for i in known}
        geo = {i: _geo(i) for i in known}
        render = state.advance_bar(status, geo, bar_ms, known_ids=frozenset(known))
        assert len(render.boxes) <= max_visible
        assert len(state._boxes) <= max_visible
        bar_ms += 900_000
    # `known` only ever grows (POIs never truly vanish from the registry);
    # the box CACHE must stay bounded regardless.
    assert len(known) > max_visible


# ----------------------------------------------------------------- mutants


def test_mutant_never_evicting_leaks_objects_beyond_capacity() -> None:
    """The selection WINDOW must actually shift (old POIs terminating and
    leaving eligibility, new ones taking their slot) for a never-evicts bug
    to manifest as growth -- a static, never-terminating active set would
    keep even the buggy model's box count bounded by coincidence."""
    max_visible = 8
    good = P7ZDisplayState(max_visible=max_visible)
    bad = _P7ZDisplayStateNeverEvicts(max_visible=max_visible)
    bar_ms = 1_000_000
    # Pre-seed a full window of `max_visible` simultaneously-active POIs.
    next_idx = max_visible
    known_good: set[int] = set(range(max_visible))
    known_bad: set[int] = set(range(max_visible))
    status0 = {i: False for i in known_good}
    geo0 = {i: _geo(i) for i in known_good}
    good.advance_bar(status0, geo0, bar_ms, known_ids=frozenset(known_good))
    bad.advance_bar(status0, geo0, bar_ms, known_ids=frozenset(known_bad))
    bar_ms += 900_000
    # Each round: the current oldest survivor gets its final pass and
    # leaves eligibility, one fresh POI takes its place -- the window stays
    # at `max_visible` members, but WHICH members keeps shifting upward.
    for _ in range(40):
        oldest_good = min(known_good)
        oldest_bad = min(known_bad)
        known_good.add(next_idx)
        known_bad.add(next_idx)
        next_idx += 1
        status_good = {i: (i == oldest_good) for i in known_good}
        status_bad = {i: (i == oldest_bad) for i in known_bad}
        good.advance_bar(
            status_good,
            {i: _geo(i) for i in known_good},
            bar_ms,
            known_ids=frozenset(known_good),
        )
        bad.advance_bar(
            status_bad,
            {i: _geo(i) for i in known_bad},
            bar_ms,
            known_ids=frozenset(known_bad),
        )
        known_good.discard(oldest_good)
        known_bad.discard(oldest_bad)
        bar_ms += 900_000
    assert len(good._boxes) <= max_visible
    assert len(bad._boxes) > max_visible  # the leak the mutant introduces


def test_mutant_using_display_cap_as_eligibility_is_detectably_wrong() -> None:
    max_visible = 4
    mutant = _P7ZDisplayStateUsesCapAsEligibility(max_visible=max_visible)
    n_active = 50
    status = {i: False for i in range(n_active)}
    geo = {i: _geo(i) for i in range(n_active)}
    render, true_engine_active = mutant.advance_bar(status, geo, 1_000_000)
    # The mutant's OWN reported active_count is wrongly capped...
    assert render.active_count == max_visible
    # ...while the true engine-eligible count (computed independently) is not.
    assert true_engine_active == n_active
    assert render.active_count != true_engine_active


def test_correct_model_active_count_is_never_capped_by_max_visible() -> None:
    """The non-mutant counterpart of the test above: engine/active accounting
    is identical regardless of how small `max_visible` is."""
    n_active = 50
    status = {i: False for i in range(n_active)}
    geo = {i: _geo(i) for i in range(n_active)}
    for max_visible in (1, 4, 16, 200):
        state = P7ZDisplayState(max_visible=max_visible)
        render = state.advance_bar(status, geo, 1_000_000)
        assert render.active_count == n_active


# ------------------------------------------------------------- randomized


def test_randomized_multi_bar_simulation_never_violates_invariants() -> None:
    rng = random.Random(99)
    max_visible = 16
    state = P7ZDisplayState(max_visible=max_visible)
    known: set[int] = set()
    terminal_forever: set[int] = set()
    bar_ms = 1_700_000_000_000
    for _ in range(2000):
        if rng.random() < 0.4:
            known.add(len(known))
        alive = known - terminal_forever
        newly_terminal = {i for i in alive if rng.random() < 0.02}
        status = {i: (i in newly_terminal) for i in alive}
        geo = {i: _geo(i) for i in alive}
        render = state.advance_bar(status, geo, bar_ms, known_ids=frozenset(alive))
        terminal_forever |= newly_terminal

        # Invariants that must hold on every single bar.
        assert len(render.boxes) <= max_visible
        assert render.shown_count == len(render.boxes)
        assert render.shown_count == min(render.active_count, max_visible)
        ids = [b.idx for b in render.boxes]
        assert ids == sorted(ids)  # ascending order, always
        assert len(set(ids)) == len(ids)  # no duplicate box for one POI
        for b in render.boxes:
            g = geo[b.idx]
            assert b.zone_top == g.zone_top
            assert b.zone_bottom == g.zone_bottom
            assert b.zone_top > b.zone_bottom
        bar_ms += 900_000
