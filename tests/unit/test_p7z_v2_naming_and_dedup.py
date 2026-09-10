"""RC1-POI-V2: frozen user-facing naming, and exact-geometry visual dedup.

WHY
---------------------------------------------------------------------
Live M1 screenshots showed labels reading "1 • BUY FVG". Pine's
`timeframe.period` is a raw token ("1", "60", "D"), so rendering it directly
prints a bare number where the trader expects a timeframe. Separately, the
live FX:XAUUSD M1 capture of 2026-09-09 contains 28 groups of POIs with
IDENTICAL geometry (56 registry entries), which drew as stacked duplicate
rectangles.

SCOPE: presentation only. Registry identity is never merged.
"""

from __future__ import annotations

import pytest

from tests.parity_support.p7z_zone_model import (
    POI_TYPE_LABEL,
    TIER_STANDARD,
    TIER_STRONG,
    UNKNOWN_TF_LABEL,
    UNKNOWN_TYPE_LABEL,
    PoiGeometry,
    combined_zone_label,
    geometry_key,
    group_exact_duplicates,
    timeframe_label,
    type_label,
    zone_label_v2,
)

# The frozen dictionary from the campaign brief, transcribed independently of
# the implementation so a silent edit to either side fails.
FROZEN_NAMES = {
    1: "BUY OB", 2: "SELL OB", 3: "BUY FVG", 4: "SELL FVG",
    5: "B2S", 6: "S2B", 7: "BASE RALLY", 8: "BASE DROP",
    9: "BULL PRESSURE", 10: "BEAR PRESSURE",
    11: "BULL ENGULF", 12: "BEAR ENGULF",
    13: "HAMMER", 14: "SHOOTING STAR",
    15: "MORNING STAR", 16: "EVENING STAR",
    17: "SUPPORT", 18: "RESISTANCE",
}


def _geo(idx, top, bottom, poi_type=1, direction=1, avail=1000, tier=TIER_STANDARD):
    return PoiGeometry(idx=idx, poi_type=poi_type, direction=direction,
                       zone_top=top, zone_bottom=bottom, avail_time_ms=avail, tier=tier)


# ---- naming dictionary --------------------------------------------------


def test_all_eighteen_names_match_the_frozen_dictionary():
    assert POI_TYPE_LABEL == FROZEN_NAMES


@pytest.mark.parametrize("code,name", sorted(FROZEN_NAMES.items()))
def test_each_type_renders_its_frozen_name(code, name):
    assert type_label(code) == name


def test_no_name_is_awkwardly_repetitive():
    """Guards the brief's explicit example: never 'RALLY BASE RALLY'."""
    for name in POI_TYPE_LABEL.values():
        words = name.split()
        assert len(words) == len(set(words)), f"repeated word in {name!r}"


@pytest.mark.parametrize("code", [0, 19, 20, 32, 99, -1])
def test_types_outside_the_closed_core_render_unknown(code):
    assert type_label(code) == UNKNOWN_TYPE_LABEL


# ---- timeframe formatting: the "1 •" defect -----------------------------


@pytest.mark.parametrize("period,expected", [
    ("1", "M1"), ("5", "M5"), ("15", "M15"), ("30", "M30"),
    ("60", "H1"), ("120", "H2"), ("240", "H4"), ("720", "H12"),
    ("D", "D1"), ("W", "W1"), ("M", "MN1"),
])
def test_raw_pine_period_becomes_a_real_timeframe_token(period, expected):
    assert timeframe_label(period) == expected


@pytest.mark.parametrize("period", ["1", "5", "15", "60", "240", "D", "W"])
def test_no_label_ever_starts_with_a_bare_number(period):
    label = zone_label_v2(3, TIER_STANDARD, period)
    head = label.split(" • ")[0]
    assert not head.isdigit(), f"bare numeric timeframe rendered: {label!r}"
    assert head[0].isalpha()


def test_the_exact_defect_from_the_screenshot_is_fixed():
    assert zone_label_v2(3, TIER_STANDARD, "1") == "M1 • BUY FVG"
    assert zone_label_v2(9, TIER_STANDARD, "1") == "M1 • BULL PRESSURE"
    assert zone_label_v2(7, TIER_STANDARD, "1") == "M1 • BASE RALLY"


def test_strong_tier_suffix_survives_the_new_formatting():
    assert zone_label_v2(1, TIER_STRONG, "15") == "M15 • BUY OB • STRONG"


@pytest.mark.parametrize("period", ["", "  ", None, "garbage", "0"])
def test_unparseable_periods_degrade_to_a_marker_not_a_number(period):
    assert timeframe_label(period) == UNKNOWN_TF_LABEL


# ---- exact-geometry dedup ----------------------------------------------


def test_identical_geometry_different_types_collapse_to_one_group():
    geo = {
        0: _geo(0, 10.0, 9.0, poi_type=1),   # BUY OB
        1: _geo(1, 10.0, 9.0, poi_type=11),  # BULL ENGULF, same geometry
    }
    groups = group_exact_duplicates([0, 1], geo)
    assert groups == [[0, 1]]
    assert combined_zone_label(groups[0], geo, "15") == "M15 • BUY OB + BULL ENGULF"


@pytest.mark.parametrize("field", ["top", "bottom", "avail", "direction"])
def test_any_geometry_difference_prevents_merging(field):
    a = _geo(0, 10.0, 9.0)
    b = _geo(
        1,
        10.5 if field == "top" else 10.0,
        8.5 if field == "bottom" else 9.0,
        direction=-1 if field == "direction" else 1,
        avail=2000 if field == "avail" else 1000,
    )
    geo = {0: a, 1: b}
    assert len(group_exact_duplicates([0, 1], geo)) == 2


def test_overlapping_but_distinct_zones_are_never_merged():
    """Phase 13: overlap alone must not collapse anything. No silent
    percentage-overlap clustering rule is introduced."""
    geo = {0: _geo(0, 10.0, 9.0), 1: _geo(1, 9.9, 9.1)}  # b sits inside a
    assert len(group_exact_duplicates([0, 1], geo)) == 2


def test_grouping_preserves_the_proximity_order_it_was_given():
    geo = {i: _geo(i, 10.0 + i, 9.0 + i) for i in range(4)}
    geo[3] = _geo(3, 10.0, 9.0)  # exact twin of 0
    groups = group_exact_duplicates([2, 0, 3, 1], geo)
    assert groups[0] == [2]
    assert groups[1] == [0, 3]  # twin folds into the earlier appearance
    assert groups[2] == [1]


def test_group_count_never_exceeds_member_count():
    geo = {i: _geo(i, 10.0, 9.0) for i in range(5)}
    groups = group_exact_duplicates(list(range(5)), geo)
    assert len(groups) == 1
    assert sum(len(g) for g in groups) == 5


def test_combined_label_dedupes_repeated_type_names():
    geo = {i: _geo(i, 10.0, 9.0, poi_type=3) for i in range(3)}
    assert combined_zone_label([0, 1, 2], geo, "1") == "M1 • BUY FVG"


def test_combined_label_marks_strong_when_any_member_is_strong():
    geo = {
        0: _geo(0, 10.0, 9.0, poi_type=1, tier=TIER_STANDARD),
        1: _geo(1, 10.0, 9.0, poi_type=11, tier=TIER_STRONG),
    }
    assert combined_zone_label([0, 1], geo, "1").endswith(" • STRONG")


def test_geometry_key_ignores_type_and_tier():
    a = _geo(0, 10.0, 9.0, poi_type=1, tier=TIER_STANDARD)
    b = _geo(1, 10.0, 9.0, poi_type=11, tier=TIER_STRONG)
    assert geometry_key(a) == geometry_key(b)


def test_dedup_does_not_drop_any_registry_identity():
    """The engine universe invariant, restated for the visual layer: every
    selected POI still appears in exactly one group."""
    geo = {i: _geo(i, 10.0 if i % 2 else 11.0, 9.0 if i % 2 else 10.0) for i in range(20)}
    selected = list(range(20))
    groups = group_exact_duplicates(selected, geo)
    flat = [i for g in groups for i in g]
    assert sorted(flat) == selected


# ---- Pine-port differential --------------------------------------------
# `f_p7zTfLabel` in btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine cannot call
# `timeframe_label`, so its branch structure is simulated here and the two
# are required to agree on every token TradingView can hand us.


def _pine_tf_label(period: str) -> str:
    out = "TF?"
    if period == "D":
        out = "D1"
    elif period == "W":
        out = "W1"
    elif period == "M":
        out = "MN1"
    else:
        try:
            mins = int(float(period))
        except (TypeError, ValueError):
            mins = 0
        if mins > 0:
            if mins < 60:
                out = f"M{mins}"
            elif mins < 1440 and mins % 60 == 0:
                out = f"H{mins // 60}"
            elif mins == 1440:
                out = "D1"
            else:
                out = f"M{mins}"
    return out


@pytest.mark.parametrize("period", [
    "1", "2", "3", "5", "10", "15", "30", "45", "59",
    "60", "120", "180", "240", "360", "480", "720",
    "1440", "2880", "D", "W", "M", "garbage", "0",
])
def test_pine_timeframe_formatter_matches_the_model(period):
    assert _pine_tf_label(period) == timeframe_label(period)


def test_hour_tokens_never_render_a_decimal_point():
    """Pine int division must not leak 'H4.0' into a user-facing label."""
    for period in ("60", "120", "240", "720"):
        assert "." not in timeframe_label(period)
        assert "." not in _pine_tf_label(period)
