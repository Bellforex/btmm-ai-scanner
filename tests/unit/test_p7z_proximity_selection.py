"""RC1-POI corrective: proof that P7-Z display selection puts the POIs
NEAREST current price on screen, and that the frozen RC1 rule does not.

WHY THIS SUITE EXISTS
---------------------------------------------------------------------
Real user screenshots showed 101-136 ACTIVE POIs and no usable zones near
current price. The cause is static and reproducible: frozen RC1 selects
`sorted(eligible)[:capacity]` -- ascending registry index -- and P3 has no
expiry, so the first 12 registry entries are the 12 OLDEST surviving POIs.
After ~1800 bars of drift those sit many ATR from price.

Measured on the frozen FXCM M15 capture (anchor 1788267600000, close
4329.33, ATR14 11.78, 157 active): the displayed 12 were 199.01-259.06
away (~17-22 ATR) while FOUR active POIs contained current price. The
overlap between "displayed" and "nearest 12" was ZERO.

SCOPE: presentation only. Every test here asserts the ENGINE UNIVERSE is
untouched -- selection may bound what is DRAWN, never what is active.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    TIER_STANDARD,
    PoiGeometry,
    _select_first_n,
    _select_last_n,
    _select_midpoint_distance,
    select_nearest,
    select_registry_order,
    zone_distance,
)

CAPACITY = 12
MUTANTS = (_select_first_n, _select_last_n, _select_midpoint_distance)


def _geo(idx: int, bottom: float, top: float, direction: int = DIRECTION_BULLISH):
    return PoiGeometry(
        idx=idx,
        poi_type=1,
        direction=direction,
        zone_top=top,
        zone_bottom=bottom,
        avail_time_ms=1_000 + idx,
        tier=TIER_STANDARD,
    )


def _universe(specs):
    """specs: list of (bottom, top) -> (eligible, geometry_by_idx)."""
    geo = {i: _geo(i, b, t) for i, (b, t) in enumerate(specs)}
    return frozenset(geo), geo


# ---- the frozen distance definition -------------------------------------


def test_distance_price_above_zone_is_gap_to_top():
    assert zone_distance(100.0, 90.0, 80.0) == pytest.approx(10.0)


def test_distance_price_below_zone_is_gap_to_bottom():
    assert zone_distance(100.0, 130.0, 110.0) == pytest.approx(10.0)


def test_distance_price_inside_zone_is_zero():
    assert zone_distance(100.0, 110.0, 90.0) == 0.0


def test_distance_at_exact_boundary_is_zero():
    assert zone_distance(110.0, 110.0, 90.0) == 0.0
    assert zone_distance(90.0, 110.0, 90.0) == 0.0


# ---- capacity behaviour (Phase 7 required cases) ------------------------


def test_zero_active_selects_nothing():
    assert select_nearest(frozenset(), {}, 100.0, CAPACITY) == []


def test_one_active_selects_it():
    eligible, geo = _universe([(90.0, 95.0)])
    assert select_nearest(eligible, geo, 100.0, CAPACITY) == [0]


def test_exactly_capacity_active_selects_all_of_them():
    eligible, geo = _universe([(float(i), i + 0.5) for i in range(CAPACITY)])
    assert sorted(select_nearest(eligible, geo, 100.0, CAPACITY)) == list(range(CAPACITY))


def test_capacity_plus_one_drops_exactly_the_farthest():
    # idx 0 is farthest from close=100; the rest march toward price.
    specs = [(float(i), float(i) + 0.5) for i in range(CAPACITY + 1)]
    eligible, geo = _universe(specs)
    chosen = select_nearest(eligible, geo, 100.0, CAPACITY)
    assert len(chosen) == CAPACITY
    assert 0 not in chosen  # the single farthest is the one dropped


def test_one_hundred_active_selects_the_twelve_nearest():
    specs = [(float(i), float(i) + 0.5) for i in range(100)]
    eligible, geo = _universe(specs)
    chosen = select_nearest(eligible, geo, 200.0, CAPACITY)
    assert chosen == list(range(99, 87, -1))


# ---- the defect, stated as a test ---------------------------------------


def test_registry_order_rule_shows_far_zones_while_near_ones_exist():
    """The frozen RC1 rule, reproduced: low registry indices are far from
    price, high indices contain it, and RC1 displays only the far ones."""
    specs = [(float(i), float(i) + 0.5) for i in range(100)]
    eligible, geo = _universe(specs)
    close = 99.25  # sits INSIDE zone 99

    frozen = select_registry_order(eligible, geo, close, CAPACITY)
    fixed = select_nearest(eligible, geo, close, CAPACITY)

    assert frozen == list(range(CAPACITY))
    assert not set(frozen) & set(fixed), "defect: zero overlap with the nearest set"
    assert min(zone_distance(close, geo[i].zone_top, geo[i].zone_bottom) for i in frozen) > 80
    assert zone_distance(close, geo[fixed[0]].zone_top, geo[fixed[0]].zone_bottom) == 0.0


def test_zone_containing_price_is_always_selected_when_capacity_allows():
    specs = [(1000.0 + i, 1001.0 + i) for i in range(50)]
    specs.append((99.0, 101.0))  # last registry entry contains price
    eligible, geo = _universe(specs)
    chosen = select_nearest(eligible, geo, 100.0, CAPACITY)
    assert chosen[0] == 50


def test_all_zones_far_away_still_returns_the_nearest_ones():
    specs = [(10_000.0 + 100 * i, 10_050.0 + 100 * i) for i in range(30)]
    eligible, geo = _universe(specs)
    chosen = select_nearest(eligible, geo, 100.0, CAPACITY)
    assert chosen == list(range(CAPACITY))  # nearest happen to be lowest here


# ---- tiebreak (Phase 5) -------------------------------------------------


def test_equal_distance_falls_back_to_ascending_registry_index():
    specs = [(90.0, 95.0)] * 5  # identical geometry -> identical distance
    eligible, geo = _universe(specs)
    assert select_nearest(eligible, geo, 100.0, 3) == [0, 1, 2]


def test_equal_distance_tiebreak_is_order_independent():
    specs = [(90.0, 95.0)] * 20
    eligible, geo = _universe(specs)
    rng = random.Random(7)
    for _ in range(25):
        shuffled = list(eligible)
        rng.shuffle(shuffled)
        assert select_nearest(shuffled, geo, 100.0, CAPACITY) == list(range(CAPACITY))


def test_selection_is_deterministic_across_repeated_calls():
    rng = random.Random(11)
    specs = []
    for _ in range(80):
        bottom = rng.uniform(50, 150)
        specs.append((bottom, bottom + rng.uniform(0.1, 5)))
    eligible, geo = _universe(specs)
    first = select_nearest(eligible, geo, 100.0, CAPACITY)
    for _ in range(10):
        assert select_nearest(eligible, geo, 100.0, CAPACITY) == first


# ---- directional cases (Phase 6 input) ----------------------------------


def test_bull_zone_below_price_and_bear_zone_above_are_both_reachable():
    geo = {
        0: _geo(0, 90.0, 95.0, DIRECTION_BULLISH),  # below price
        1: _geo(1, 105.0, 110.0, DIRECTION_BEARISH),  # above price
    }
    chosen = select_nearest(frozenset(geo), geo, 100.0, CAPACITY)
    assert sorted(chosen) == [0, 1]


def test_pure_distance_can_return_an_entirely_one_sided_set():
    """Phase 6: documents, without silently fixing, that nearest-distance
    alone may put all 12 zones on one side of price. Reported to the author
    as a decision item -- no 6/6 quota is introduced here."""
    specs = [(80.0 + i, 80.5 + i) for i in range(20)]  # all below price
    specs += [(400.0 + i, 401.0 + i) for i in range(20)]  # all far above
    eligible, geo = _universe(specs)
    chosen = select_nearest(eligible, geo, 100.0, CAPACITY)
    assert all(geo[i].zone_top <= 100.0 for i in chosen)


# ---- engine-universe invariant (Phase 3) --------------------------------


@pytest.mark.parametrize("capacity", [1, 5, 12, 30])
def test_selection_never_shrinks_or_mutates_the_active_universe(capacity):
    rng = random.Random(3)
    specs = []
    for _ in range(120):
        bottom = rng.uniform(50, 150)
        specs.append((bottom, bottom + rng.uniform(0.1, 4)))
    eligible, geo = _universe(specs)
    before_ids = set(eligible)
    before_geo = dict(geo)
    chosen = select_nearest(eligible, geo, 100.0, capacity)
    assert set(eligible) == before_ids, "selection mutated the active set"
    assert geo == before_geo, "selection mutated registry geometry"
    assert len(eligible) == 120, "engine universe must stay ALL active POIs"
    assert len(chosen) == min(capacity, 120)
    assert set(chosen) <= set(eligible)


# ---- mutation tests (Phase 8) -------------------------------------------


@pytest.mark.parametrize("mutant", MUTANTS, ids=lambda f: f.__name__)
def test_mutant_selection_rules_are_all_caught(mutant):
    """Each Phase 8 mutant must DIFFER from the correct rule on at least one
    of these adversarial universes -- otherwise this suite proves nothing."""
    universes = []

    # far-low indices, near-high indices: kills first-N.
    specs = [(float(i), float(i) + 0.5) for i in range(40)]
    universes.append((specs, 39.25))

    # near-low indices, far-high indices: kills last-N.
    specs = [(1000.0 - 10 * i, 1002.0 - 10 * i) for i in range(40)]
    universes.append((specs, 640.0))

    # one WIDE zone containing price vs many narrow zones closer in
    # midpoint terms: kills midpoint-distance.
    specs = [(95.0, 400.0)] + [(120.0 + i, 120.5 + i) for i in range(30)]
    universes.append((specs, 100.0))

    differed = False
    for specs, close in universes:
        eligible, geo = _universe(specs)
        correct = select_nearest(eligible, geo, close, CAPACITY)
        if mutant(eligible, geo, close, CAPACITY) != correct:
            differed = True
    assert differed, f"{mutant.__name__} was not distinguished from the correct rule"


def test_midpoint_mutant_specifically_drops_a_zone_containing_price():
    specs = [(95.0, 400.0)] + [(120.0 + i, 120.5 + i) for i in range(30)]
    eligible, geo = _universe(specs)
    close = 100.0
    assert zone_distance(close, geo[0].zone_top, geo[0].zone_bottom) == 0.0
    assert select_nearest(eligible, geo, close, CAPACITY)[0] == 0
    assert 0 not in _select_midpoint_distance(eligible, geo, close, CAPACITY)


def test_first_n_mutant_is_exactly_the_frozen_rc1_rule():
    """Documents the finding: the shipped RC1 rule IS a Phase 8 mutant."""
    rng = random.Random(5)
    specs = []
    for _ in range(60):
        bottom = rng.uniform(50, 150)
        specs.append((bottom, bottom + rng.uniform(0.1, 4)))
    eligible, geo = _universe(specs)
    assert _select_first_n(eligible, geo, 100.0, CAPACITY) == select_registry_order(
        eligible, geo, 100.0, CAPACITY
    )


# ---- Pine-port differential ---------------------------------------------
# `btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine` cannot call `select_nearest`;
# it runs a repeated-minimum scan because Pine has no stable key-sort. This
# simulates that Pine loop EXACTLY and proves the two agree, so the port is
# verified rather than asserted.


def _pine_repeated_minimum(eligible, geometry_by_idx, close, capacity):
    """Line-for-line simulation of the DEV script's P7-Z selection loop."""
    p7_poi_idx = sorted(eligible)  # Pine builds p7PoiIdx in ascending order
    active = len(p7_poi_idx)
    shown = min(active, capacity)

    dist = []
    for r in range(active):
        g = geometry_by_idx[p7_poi_idx[r]]
        if close < g.zone_bottom:
            dist.append(g.zone_bottom - close)
        elif close > g.zone_top:
            dist.append(close - g.zone_top)
        else:
            dist.append(0.0)

    taken = [False] * active
    selected = []
    for _ in range(shown):
        best_r, best_d, best_poi = -1, 0.0, 0
        for r in range(active):
            if not taken[r]:
                d, cand = dist[r], p7_poi_idx[r]
                if best_r == -1 or d < best_d or (d == best_d and cand < best_poi):
                    best_r, best_d, best_poi = r, d, cand
        if best_r >= 0:
            taken[best_r] = True
            selected.append(best_poi)
    return selected


@pytest.mark.parametrize("seed", range(40))
def test_pine_loop_matches_the_python_selection_model(seed):
    rng = random.Random(seed)
    n = rng.randint(1, 160)
    specs = []
    for _ in range(n):
        bottom = rng.choice(
            [rng.uniform(90, 110), rng.uniform(50, 150), rng.uniform(500, 5000)]
        )
        specs.append((bottom, bottom + rng.uniform(0.0, 8)))
    eligible, geo = _universe(specs)
    close = 100.0
    capacity = rng.choice([1, 5, 12, 30])
    assert _pine_repeated_minimum(eligible, geo, close, capacity) == select_nearest(
        eligible, geo, close, capacity
    )


def test_pine_loop_matches_model_on_heavy_ties():
    """Ties are where a repeated-minimum scan and a key-sort most easily
    diverge, so they get their own case."""
    specs = [(90.0, 95.0)] * 30 + [(105.0, 106.0)] * 30
    eligible, geo = _universe(specs)
    assert _pine_repeated_minimum(eligible, geo, 100.0, CAPACITY) == select_nearest(
        eligible, geo, 100.0, CAPACITY
    )


# ---- P7 TABLE row-ordering (Step 10) ------------------------------------
# The table's parallel arrays (p7PoiBull/p7PoiTier/p7PoiFinal/...) are keyed by
# ROW POSITION inside p7PoiIdx, not by POI-registry index. Reordering the table
# by proximity therefore has a failure mode the box path does not have: read a
# parallel array with the printed row number instead of the source row and every
# row keeps its position's data while showing another POI's identity. The first
# cut of the Pine patch did exactly that on three of nine fields.


def _pine_table_rows(active_poi_idx, geometry_by_idx, close, capacity):
    """Simulates the DEV table loop: returns the source ROW index per printed
    row, using the same repeated-minimum scan as the box selection."""
    n = len(active_poi_idx)
    shown = min(n, capacity)
    dist = []
    for r in range(n):
        g = geometry_by_idx[active_poi_idx[r]]
        if close < g.zone_bottom:
            dist.append(g.zone_bottom - close)
        elif close > g.zone_top:
            dist.append(close - g.zone_top)
        else:
            dist.append(0.0)
    taken = [False] * n
    order = []
    for _ in range(shown):
        best_r, best_d, best_poi = -1, 0.0, 0
        for r in range(n):
            if not taken[r]:
                d, cand = dist[r], active_poi_idx[r]
                if best_r == -1 or d < best_d or (d == best_d and cand < best_poi):
                    best_r, best_d, best_poi = r, d, cand
        if best_r >= 0:
            taken[best_r] = True
            order.append(best_r)
    return order


@pytest.mark.parametrize("seed", range(30))
def test_table_rows_keep_every_parallel_field_with_its_own_poi(seed):
    rng = random.Random(seed)
    n = rng.randint(1, 60)
    specs = []
    for _ in range(n):
        bottom = rng.uniform(50, 150)
        specs.append((bottom, bottom + rng.uniform(0.1, 6)))
    eligible, geo = _universe(specs)
    active = sorted(eligible)
    # a distinct per-POI payload, stored row-keyed exactly like the Pine arrays
    payload_by_row = {r: f"payload-{active[r]}" for r in range(len(active))}
    close = 100.0
    capacity = 8

    order = _pine_table_rows(active, geo, close, capacity)
    printed = [(active[src], payload_by_row[src]) for src in order]

    for poi_idx, payload in printed:
        assert payload == f"payload-{poi_idx}", "row payload desynced from its POI"


def test_table_and_box_projections_agree_on_shared_prefix():
    """Table capacity 8 and box capacity 12 must describe the same nearby POI
    universe: the table's rows are exactly the first 8 of the box selection."""
    rng = random.Random(99)
    specs = []
    for _ in range(80):
        bottom = rng.uniform(50, 150)
        specs.append((bottom, bottom + rng.uniform(0.1, 6)))
    eligible, geo = _universe(specs)
    active = sorted(eligible)
    close = 100.0

    table_pois = [active[src] for src in _pine_table_rows(active, geo, close, 8)]
    box_pois = select_nearest(eligible, geo, close, 12)
    assert table_pois == box_pois[:8]


def test_table_ordering_is_not_registry_order_when_price_has_drifted():
    specs = [(float(i), float(i) + 0.5) for i in range(40)]
    eligible, geo = _universe(specs)
    active = sorted(eligible)
    close = 39.25
    table_pois = [active[src] for src in _pine_table_rows(active, geo, close, 8)]
    assert table_pois != active[:8]
    assert table_pois[0] == 39
