"""RC1-POI-V2: differential between the Pine group projection and the model.

The Pine build (`btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine`) cannot call
`build_visual_groups`. It also uses a DIFFERENT algorithm: Pine has no
union-find, so it grows each group against the running ENVELOPE until no
member can be added, while the model uses union-find over pairwise overlap.

Those agree only because the union of an overlap-connected set of intervals
is itself an interval equal to that set's envelope, so "touches the envelope"
and "touches some member" are the same predicate. That argument is the whole
correctness case for the port, so it is tested rather than asserted.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    FVG_TYPES,
    TIER_STANDARD,
    TIER_STRONG,
    PoiGeometry,
    build_visual_groups,
    timeframe_label,
    type_label,
)

BUY_FVG, SELL_FVG = 3, 4
NON_FVG_TYPES = (1, 7, 9, 11, 13)


def _pine_groups(active, geo, close, capacity, period):
    """Line-for-line simulation of the DEV's P7-Z group projection."""
    poi_idx = sorted(active)
    n = len(poi_idx)
    grp_of = [-1] * n
    groups = []

    for a in range(n):
        if grp_of[a] != -1:
            continue
        a_poi = poi_idx[a]
        ga = geo[a_poi]
        a_is_fvg = ga.poi_type in FVG_TYPES
        a_dir = ga.direction
        g_top, g_bot, g_left = ga.zone_top, ga.zone_bottom, ga.avail_time_ms
        g_key, g_count = a_poi, 1
        g_strong = ga.tier == TIER_STRONG
        g_names = [type_label(ga.poi_type)]
        gi = len(groups)
        grp_of[a] = gi

        changed = True
        while changed:
            changed = False
            for b in range(n):
                if grp_of[b] != -1:
                    continue
                b_poi = poi_idx[b]
                gb = geo[b_poi]
                b_is_fvg = gb.poi_type in FVG_TYPES
                joins = False
                if a_is_fvg and b_is_fvg and gb.direction == a_dir:
                    joins = gb.zone_bottom <= g_top and g_bot <= gb.zone_top
                elif not a_is_fvg and not b_is_fvg:
                    joins = (
                        gb.zone_top == g_top
                        and gb.zone_bottom == g_bot
                        and gb.avail_time_ms == g_left
                        and gb.direction == a_dir
                    )
                if joins:
                    grp_of[b] = gi
                    g_top = max(g_top, gb.zone_top)
                    g_bot = min(g_bot, gb.zone_bottom)
                    g_left = min(g_left, gb.avail_time_ms)
                    g_key = min(g_key, b_poi)
                    g_count += 1
                    g_strong = g_strong or gb.tier == TIER_STRONG
                    name = type_label(gb.poi_type)
                    if name not in g_names:
                        g_names.append(name)
                    changed = True

        tf = timeframe_label(period)
        label = f"{tf} • {' + '.join(g_names)}"
        if a_is_fvg:
            if g_count > 1:
                label = f"{tf} • {type_label(ga.poi_type)} ×{g_count}"
        elif g_strong:
            label += " • STRONG"
        members = sorted(poi_idx[i] for i in range(n) if grp_of[i] == gi)
        groups.append(
            {
                "members": members,
                "top": g_top,
                "bottom": g_bot,
                "left_time_ms": g_left,
                "key": g_key,
                "label": label,
            }
        )

    def dist(g):
        if close < g["bottom"]:
            return g["bottom"] - close
        if close > g["top"]:
            return close - g["top"]
        return 0.0

    taken = [False] * len(groups)
    out = []
    for _ in range(min(capacity, len(groups))):
        best, best_d, best_key = -1, 0.0, 0
        for gi, g in enumerate(groups):
            if taken[gi]:
                continue
            d, k = dist(g), g["key"]
            if best == -1 or d < best_d or (d == best_d and k < best_key):
                best, best_d, best_key = gi, d, k
        if best >= 0:
            taken[best] = True
            out.append(groups[best])
    return out


def _random_universe(seed):
    rng = random.Random(seed)
    geo = {}
    for i in range(rng.randint(1, 45)):
        kind = rng.random()
        if kind < 0.55:
            poi_type = rng.choice([BUY_FVG, SELL_FVG])
            direction = DIRECTION_BULLISH if poi_type == BUY_FVG else DIRECTION_BEARISH
        else:
            poi_type = rng.choice(NON_FVG_TYPES)
            direction = rng.choice([DIRECTION_BULLISH, DIRECTION_BEARISH])
        bottom = round(rng.uniform(95.0, 108.0), 2)
        top = round(bottom + rng.uniform(0.0, 2.5), 2)
        geo[i] = PoiGeometry(
            idx=i,
            poi_type=poi_type,
            direction=direction,
            zone_top=top,
            zone_bottom=bottom,
            avail_time_ms=rng.choice([1000, 2000, 3000]),
            tier=rng.choice([TIER_STANDARD, TIER_STRONG]),
        )
    return geo


@pytest.mark.parametrize("seed", range(60))
def test_pine_projection_matches_the_model(seed):
    geo = _random_universe(seed)
    close = 101.5
    capacity = 8
    pine = _pine_groups(list(geo), geo, close, capacity, "1")
    model = build_visual_groups(list(geo), geo, close, capacity, "1")
    assert [g["members"] for g in pine] == [g["members"] for g in model]
    assert [g["label"] for g in pine] == [g["label"] for g in model]
    assert [(g["top"], g["bottom"]) for g in pine] == [
        (g["top"], g["bottom"]) for g in model
    ]
    assert [g["left_time_ms"] for g in pine] == [g["left_time_ms"] for g in model]


@pytest.mark.parametrize("seed", range(20))
@pytest.mark.parametrize("capacity", [1, 4, 8, 12])
def test_pine_projection_matches_across_capacities(seed, capacity):
    geo = _random_universe(seed + 500)
    pine = _pine_groups(list(geo), geo, 101.5, capacity, "1")
    model = build_visual_groups(list(geo), geo, 101.5, capacity, "1")
    assert [g["members"] for g in pine] == [g["members"] for g in model]


def test_envelope_growth_equals_union_find_on_a_chain():
    """The exact case the two algorithms could disagree on: a transitive
    chain whose ends do not touch each other."""
    geo = {
        0: PoiGeometry(0, BUY_FVG, DIRECTION_BULLISH, 10.0, 9.0, 1000, TIER_STANDARD),
        1: PoiGeometry(1, BUY_FVG, DIRECTION_BULLISH, 9.5, 8.0, 1000, TIER_STANDARD),
        2: PoiGeometry(2, BUY_FVG, DIRECTION_BULLISH, 8.2, 7.0, 1000, TIER_STANDARD),
    }
    pine = _pine_groups([0, 1, 2], geo, 20.0, 8, "1")
    model = build_visual_groups([0, 1, 2], geo, 20.0, 8, "1")
    assert pine[0]["members"] == model[0]["members"] == [0, 1, 2]


def test_pine_reproduces_the_golden_four_way_decomposition():
    geo = {
        176: PoiGeometry(176, BUY_FVG, DIRECTION_BULLISH, 4358.53, 4357.15, 1000, TIER_STANDARD),
        177: PoiGeometry(177, BUY_FVG, DIRECTION_BULLISH, 4358.64, 4358.60, 1001, TIER_STANDARD),
        178: PoiGeometry(178, BUY_FVG, DIRECTION_BULLISH, 4360.65, 4359.88, 1002, TIER_STANDARD),
        179: PoiGeometry(179, BUY_FVG, DIRECTION_BULLISH, 4361.79, 4360.88, 1003, TIER_STANDARD),
    }
    pine = _pine_groups(list(geo), geo, 4400.0, 8, "1")
    assert [g["members"] for g in pine] == [[179], [178], [177], [176]]
    assert all(g["label"] == "M1 • BUY FVG" for g in pine)
