"""RC1-POI-V2 Phase 27: FVG visual clustering.

Presentation only. P3/P5/P8 and the registry keep every FVG as its own
identity; only the drawn objects group.

A cluster requires ALL of: FVG family, same direction, same origin
timeframe, simultaneously eligible, and intervals that OVERLAP OR TOUCH.
Membership is transitive. Geometry is the ENVELOPE of members, never an
average and never a midpoint-derived synthetic zone.
"""

from __future__ import annotations

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    TIER_STANDARD,
    PoiGeometry,
    build_visual_groups,
    cluster_geometry,
    fvg_cluster_label,
    fvg_connected_components,
)

BUY_FVG, SELL_FVG = 3, 4


def _f(idx, top, bottom, poi_type=BUY_FVG, direction=DIRECTION_BULLISH, avail=None):
    return PoiGeometry(
        idx=idx,
        poi_type=poi_type,
        direction=direction,
        zone_top=top,
        zone_bottom=bottom,
        avail_time_ms=avail if avail is not None else 1000 + idx,
        tier=TIER_STANDARD,
    )


# ---- the author's golden area, computed not assumed ---------------------

GOLDEN = {
    176: _f(176, 4358.53, 4357.15),
    177: _f(177, 4358.64, 4358.60),
    178: _f(178, 4360.65, 4359.88),
    179: _f(179, 4361.79, 4360.88),
}


def test_golden_fvg_members_do_not_form_one_component():
    """The four BUY FVGs in the marked M1 area are pairwise SEPARATED, so
    the authorized rule decomposes them into four singleton clusters.
    Recorded as a golden so a later clustering change that silently merges
    them fails here."""
    assert fvg_connected_components(sorted(GOLDEN), GOLDEN) == [[176], [177], [178], [179]]


@pytest.mark.parametrize("lo,hi,gap", [(176, 177, 0.07), (177, 178, 1.24), (178, 179, 0.23)])
def test_golden_gaps_are_real_and_positive(lo, hi, gap):
    assert GOLDEN[hi].zone_bottom - GOLDEN[lo].zone_top == pytest.approx(gap, abs=0.005)


# ---- the connectivity rule ---------------------------------------------


def test_single_fvg_is_its_own_cluster():
    geo = {0: _f(0, 10.0, 9.0)}
    assert fvg_connected_components([0], geo) == [[0]]


def test_two_overlapping_fvgs_merge():
    geo = {0: _f(0, 10.0, 9.0), 1: _f(1, 9.5, 8.5)}
    assert fvg_connected_components([0, 1], geo) == [[0, 1]]


def test_two_exactly_touching_fvgs_merge():
    """Closed intervals: sharing a single price counts as touching."""
    geo = {0: _f(0, 10.0, 9.0), 1: _f(1, 9.0, 8.0)}
    assert fvg_connected_components([0, 1], geo) == [[0, 1]]


def test_two_separated_fvgs_stay_apart():
    geo = {0: _f(0, 10.0, 9.0), 1: _f(1, 8.99, 8.0)}
    assert fvg_connected_components([0, 1], geo) == [[0], [1]]


def test_transitive_overlap_pulls_in_a_non_adjacent_member():
    """A-B and B-C overlap; A and C do not touch each other at all."""
    a, b, c = _f(0, 10.0, 9.0), _f(1, 9.5, 8.0), _f(2, 8.2, 7.0)
    geo = {0: a, 1: b, 2: c}
    assert not (a.zone_bottom <= c.zone_top and c.zone_bottom <= a.zone_top)
    assert fvg_connected_components([0, 1, 2], geo) == [[0, 1, 2]]


def test_component_result_is_independent_of_input_order():
    geo = {0: _f(0, 10.0, 9.0), 1: _f(1, 9.5, 8.0), 2: _f(2, 8.2, 7.0), 3: _f(3, 5.0, 4.0)}
    expected = [[0, 1, 2], [3]]
    for order in ([0, 1, 2, 3], [3, 2, 1, 0], [1, 3, 0, 2], [2, 0, 3, 1]):
        assert fvg_connected_components(order, geo) == expected


# ---- direction and timeframe never merge --------------------------------


def test_buy_and_sell_fvgs_never_merge_even_with_identical_geometry():
    geo = {
        0: _f(0, 10.0, 9.0, poi_type=BUY_FVG, direction=DIRECTION_BULLISH),
        1: _f(1, 10.0, 9.0, poi_type=SELL_FVG, direction=DIRECTION_BEARISH),
    }
    groups = build_visual_groups(list(geo), geo, 12.0, 10, "1")
    assert len(groups) == 2
    assert sorted(g["label"] for g in groups) == ["M1 • BUY FVG", "M1 • SELL FVG"]


def test_same_direction_different_timeframe_render_distinct_labels():
    """P3 is single-timeframe, so the host TF is the origin TF. Identical
    geometry on two hosts must still read as two different timeframes."""
    geo = {0: _f(0, 10.0, 9.0)}
    m1 = build_visual_groups([0], geo, 12.0, 10, "1")[0]["label"]
    m5 = build_visual_groups([0], geo, 12.0, 10, "5")[0]["label"]
    assert m1 == "M1 • BUY FVG" and m5 == "M5 • BUY FVG"


# ---- cluster geometry ---------------------------------------------------


def test_cluster_geometry_is_the_envelope_not_an_average():
    geo = {0: _f(0, 10.0, 9.0, avail=500), 1: _f(1, 9.5, 8.0, avail=300)}
    assert cluster_geometry([0, 1], geo) == (10.0, 8.0, 300)


def test_cluster_geometry_never_invents_a_midpoint_zone():
    geo = {0: _f(0, 10.0, 9.0), 1: _f(1, 9.5, 8.0)}
    top, bottom, _ = cluster_geometry([0, 1], geo)
    assert top != (10.0 + 9.5) / 2
    assert top == 10.0 and bottom == 8.0


def test_cluster_left_edge_is_the_earliest_member_origin():
    geo = {
        0: _f(0, 10.0, 9.0, avail=900),
        1: _f(1, 9.5, 8.0, avail=100),
        2: _f(2, 8.5, 8.0, avail=400),
    }
    assert cluster_geometry([0, 1, 2], geo)[2] == 100


# ---- labels -------------------------------------------------------------


@pytest.mark.parametrize(
    "n,expected",
    [(1, "M1 • BUY FVG"), (2, "M1 • BUY FVG ×2"), (3, "M1 • BUY FVG ×3"), (4, "M1 • BUY FVG ×4")],
)
def test_cluster_label_counts_members(n, expected):
    geo = {i: _f(i, 10.0 - i * 0.1, 9.0 - i * 0.1) for i in range(n)}
    assert fvg_cluster_label(list(range(n)), geo, "1") == expected


def test_cluster_label_omits_registry_ids():
    geo = {i: _f(i, 10.0 - i * 0.1, 9.0 - i * 0.1) for i in range(3)}
    label = fvg_cluster_label([0, 1, 2], geo, "1")
    assert "idx" not in label.lower()
    assert label == "M1 • BUY FVG ×3"


# ---- capacity counts GROUPS, and identities survive ---------------------


def test_capacity_counts_visual_groups_not_semantic_pois():
    """A 4-member cluster consumes exactly one of the 8 slots."""
    geo = {i: _f(i, 10.0 - i * 0.2, 9.6 - i * 0.2) for i in range(4)}
    for i in range(4, 12):
        # spaced 10 apart so these singletons neither touch nor overlap
        geo[i] = _f(i, 100.0 + i * 10, 99.0 + i * 10)
    groups = build_visual_groups(list(geo), geo, 9.8, 8, "1")
    assert len(groups) == 8
    assert len(groups[0]["members"]) == 4
    assert sum(len(g["members"]) for g in groups) == 11


def test_grouping_runs_over_the_whole_active_set_before_capacity():
    """A cluster must never be split by the display cut."""
    geo = {i: _f(i, 10.0 - i * 0.2, 9.6 - i * 0.2) for i in range(5)}
    groups = build_visual_groups(list(geo), geo, 9.8, 1, "1")
    assert len(groups) == 1
    assert groups[0]["members"] == [0, 1, 2, 3, 4]


def test_every_selected_poi_belongs_to_exactly_one_group():
    geo = {i: _f(i, 10.0 - i * 0.15, 9.5 - i * 0.15) for i in range(12)}
    groups = build_visual_groups(list(geo), geo, 5.0, 10**6, "1")
    flat = [i for g in groups for i in g["members"]]
    assert sorted(flat) == sorted(geo)
    assert len(flat) == len(set(flat)), "a POI appeared in two groups"


def test_large_active_universe_stays_deterministic():
    geo = {}
    for i in range(150):
        base = 100.0 + (i % 50) * 3.0
        geo[i] = _f(i, base + 1.0, base)
    a = build_visual_groups(list(geo), geo, 120.0, 8, "1")
    b = build_visual_groups(list(geo), geo, 120.0, 8, "1")
    assert [g["members"] for g in a] == [g["members"] for g in b]
    assert len(a) == 8


def test_non_fvg_types_are_never_overlap_merged():
    """Phase 10: outside the FVG rule, overlap alone merges nothing."""
    geo = {0: _f(0, 10.0, 9.0, poi_type=1), 1: _f(1, 9.5, 8.5, poi_type=1)}
    assert len(build_visual_groups([0, 1], geo, 12.0, 10, "1")) == 2


def test_base_rally_never_joins_an_fvg_cluster():
    geo = {
        0: _f(0, 4349.17, 4347.78, poi_type=7),
        1: _f(1, 4349.00, 4348.00, poi_type=BUY_FVG),
    }
    groups = build_visual_groups([0, 1], geo, 4360.0, 10, "1")
    assert len(groups) == 2
    assert {g["label"] for g in groups} == {"M1 • BASE RALLY", "M1 • BUY FVG"}


def test_bearish_direction_constant_is_wired():
    geo = {0: _f(0, 10.0, 9.0, poi_type=SELL_FVG, direction=DIRECTION_BEARISH)}
    assert build_visual_groups([0], geo, 12.0, 8, "1")[0]["direction"] == DIRECTION_BEARISH
