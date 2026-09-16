"""RC1-POI-V2 hotfix: the optimized presentation projection must equal the
frozen V2 oracle exactly.

CONTEXT
---------------------------------------------------------------------
The V2 grouping runs inside `if barstate.isconfirmed`, so it executes on
EVERY confirmed bar -- roughly 1800 per full recalculation. Its
envelope-growth closure is O(n^2) in the active-POI count. On M5, whose 1800
bars span ~6.25 days of structure (against M1's 30 hours), that exceeded
TradingView's 20-second budget and raised RE10110, leaving the study drawing
nothing at all.

The replacement is partition -> sort -> sweep, which is O(n log n) and
computes the identical connected components. The oracle
(`build_visual_groups`) is retained and is the semantic authority
the
optimized path (`build_visual_groups_fast`) must reproduce it exactly.

WHY NOT JUST BOUND THE ACTIVE SET
---------------------------------------------------------------------
A seemingly distant FVG can connect transitively through overlapping
neighbours. Truncating before grouping can therefore change component
membership, geometry, distance and the final top-K selection.
`test_pre_bounding_the_active_set_changes_a_transitive_component` proves that
concretely, so the shortcut stays closed.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7z_zone_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    TIER_STANDARD,
    TIER_STRONG,
    OpCount,
    PoiGeometry,
    build_visual_groups,
    build_visual_groups_fast,
    fvg_components_sweep,
    fvg_connected_components,
)

BUY_FVG, SELL_FVG = 3, 4
NON_FVG = (1, 2, 7, 9, 11, 13, 14)
CAPACITY = 8


def _g(idx, top, bottom, poi_type=BUY_FVG, direction=DIRECTION_BULLISH, avail=None, tier=TIER_STANDARD):
    return PoiGeometry(
        idx=idx, poi_type=poi_type, direction=direction,
        zone_top=top, zone_bottom=bottom,
        avail_time_ms=avail if avail is not None else 1000 + idx, tier=tier,
    )


def _same(a: list[dict], b: list[dict]) -> bool:
    if len(a) != len(b):
        return False
    for x, y in zip(a, b, strict=True):
        if (
            x["members"] != y["members"]
            or x["top"] != y["top"]
            or x["bottom"] != y["bottom"]
            or x["left_time_ms"] != y["left_time_ms"]
            or x["direction"] != y["direction"]
            or x["label"] != y["label"]
            or x["distance"] != y["distance"]
        ):
            return False
    return True


def _assert_equivalent(geo, close, capacity=CAPACITY, period="1"):
    ids = list(geo)
    slow = build_visual_groups(ids, geo, close, capacity, period)
    fast = build_visual_groups_fast(ids, geo, close, capacity, period)
    assert _same(slow, fast), f"slow={slow}\nfast={fast}"
    return slow


# ---- Phase 11: adversarial cases ----------------------------------------


def test_zero_pois():
    assert build_visual_groups_fast([], {}, 100.0, CAPACITY, "1") == []


def test_single_fvg():
    _assert_equivalent({0: _g(0, 10.0, 9.0)}, 100.0)


def test_two_separated_fvgs():
    _assert_equivalent({0: _g(0, 10.0, 9.0), 1: _g(1, 8.99, 8.0)}, 100.0)


def test_two_overlapping_fvgs():
    _assert_equivalent({0: _g(0, 10.0, 9.0), 1: _g(1, 9.5, 8.5)}, 100.0)


def test_two_exactly_touching_fvgs():
    _assert_equivalent({0: _g(0, 10.0, 9.0), 1: _g(1, 9.0, 8.0)}, 100.0)


def test_three_interval_transitive_chain():
    geo = {0: _g(0, 10.0, 9.0), 1: _g(1, 9.5, 8.0), 2: _g(2, 8.2, 7.0)}
    groups = _assert_equivalent(geo, 100.0)
    assert groups[0]["members"] == [0, 1, 2]


def test_nested_intervals():
    geo = {0: _g(0, 20.0, 1.0), 1: _g(1, 12.0, 11.0), 2: _g(2, 15.0, 14.0)}
    groups = _assert_equivalent(geo, 100.0)
    assert groups[0]["members"] == [0, 1, 2]


def test_identical_intervals():
    geo = {i: _g(i, 10.0, 9.0) for i in range(5)}
    _assert_equivalent(geo, 100.0)


def test_same_geometry_different_direction_never_merges():
    geo = {
        0: _g(0, 10.0, 9.0, poi_type=BUY_FVG, direction=DIRECTION_BULLISH),
        1: _g(1, 10.0, 9.0, poi_type=SELL_FVG, direction=DIRECTION_BEARISH),
    }
    groups = _assert_equivalent(geo, 100.0)
    assert len(groups) == 2


def test_buy_and_sell_interleaved_across_price():
    geo = {}
    for i in range(20):
        t = BUY_FVG if i % 2 == 0 else SELL_FVG
        d = DIRECTION_BULLISH if t == BUY_FVG else DIRECTION_BEARISH
        geo[i] = _g(i, 100.0 + i * 0.5 + 0.4, 100.0 + i * 0.5, poi_type=t, direction=d)
    _assert_equivalent(geo, 105.0)


def test_many_exact_duplicates_non_fvg():
    geo = {i: _g(i, 10.0, 9.0, poi_type=NON_FVG[i % len(NON_FVG)], avail=5000) for i in range(30)}
    _assert_equivalent(geo, 100.0)


def test_many_singleton_fvgs():
    geo = {i: _g(i, 10.0 + i * 5, 9.0 + i * 5) for i in range(60)}
    _assert_equivalent(geo, 100.0)


def test_all_intervals_overlapping():
    geo = {i: _g(i, 200.0, 1.0 + i * 0.01) for i in range(50)}
    _assert_equivalent(geo, 100.0)


def test_all_intervals_separated():
    geo = {i: _g(i, 10.0 + i * 100, 9.0 + i * 100) for i in range(50)}
    _assert_equivalent(geo, 100.0)


def test_distance_ties():
    geo = {i: _g(i, 95.0, 90.0, poi_type=NON_FVG[i % len(NON_FVG)], avail=1000 + i) for i in range(12)}
    _assert_equivalent(geo, 100.0)


def test_price_inside_many_groups():
    geo = {i: _g(i, 105.0 + i, 95.0 - i, poi_type=NON_FVG[i % len(NON_FVG)], avail=1000 + i) for i in range(10)}
    _assert_equivalent(geo, 100.0)


def test_very_old_origins_and_large_price_ranges():
    geo = {
        0: _g(0, 9000.0, 100.0, avail=1),
        1: _g(1, 150.0, 120.0, avail=2),
        2: _g(2, 20.0, 10.0, avail=10**12),
    }
    _assert_equivalent(geo, 4000.0)


def test_strong_tier_labels_survive_optimization():
    geo = {
        0: _g(0, 10.0, 9.0, poi_type=1, tier=TIER_STRONG, avail=7000),
        1: _g(1, 10.0, 9.0, poi_type=11, tier=TIER_STANDARD, avail=7000),
    }
    groups = _assert_equivalent(geo, 100.0)
    assert groups[0]["label"].endswith(" • STRONG")


# ---- Phase 12: large randomized differential ----------------------------


def _random_universe(seed: int, n: int) -> dict[int, PoiGeometry]:
    rng = random.Random(seed)
    geo = {}
    for i in range(n):
        if rng.random() < 0.55:
            t = rng.choice([BUY_FVG, SELL_FVG])
            d = DIRECTION_BULLISH if t == BUY_FVG else DIRECTION_BEARISH
        else:
            t = rng.choice(NON_FVG)
            d = rng.choice([DIRECTION_BULLISH, DIRECTION_BEARISH])
        bottom = round(rng.uniform(4300.0, 4460.0), 2)
        width = rng.choice([0.0, 0.05, 0.5, 2.0, 12.0])
        geo[i] = _g(i, round(bottom + width, 2), bottom, poi_type=t, direction=d,
                    avail=1000 + rng.randrange(0, 5) * 60,
                    tier=rng.choice([TIER_STANDARD, TIER_STRONG]))
    return geo


@pytest.mark.parametrize("n", [1, 8, 20, 50, 100, 150, 250])
@pytest.mark.parametrize("seed", range(6))
def test_randomized_differential(n, seed):
    geo = _random_universe(seed * 1000 + n, n)
    _assert_equivalent(geo, 4380.0)


@pytest.mark.parametrize("n", [500, 750, 1000])
def test_randomized_differential_large(n):
    geo = _random_universe(90_000 + n, n)
    _assert_equivalent(geo, 4380.0)


def test_randomized_differential_at_full_bar_budget():
    """1800 is the calc_bars_count
    an active set that large is the worst
    realistic case the Pine build could face."""
    geo = _random_universe(180_000, 1800)
    _assert_equivalent(geo, 4380.0)


@pytest.mark.parametrize("close", [4290.0, 4380.0, 4470.0])
def test_randomized_differential_across_price_regimes(close):
    geo = _random_universe(4242, 300)
    _assert_equivalent(geo, close)


# ---- Phase 14: mutation tests -------------------------------------------


def test_pre_bounding_the_active_set_changes_a_transitive_component():
    """The reason bounding before grouping is forbidden.

    A far interval connects to a near one only THROUGH a middle interval.
    Keeping just the two nearest POIs breaks the chain and yields different
    membership and different geometry."""
    geo = {
        0: _g(0, 101.0, 100.0),   # nearest to close
        1: _g(1, 100.5, 99.0),    # the connector
        2: _g(2, 99.2, 90.0),     # far, but transitively connected
    }
    full = build_visual_groups_fast(list(geo), geo, 102.0, CAPACITY, "1")
    assert full[0]["members"] == [0, 1, 2]
    assert full[0]["bottom"] == 90.0

    bounded = build_visual_groups_fast([0, 1], geo, 102.0, CAPACITY, "1")
    assert bounded[0]["members"] == [0, 1]
    assert bounded[0]["bottom"] == 99.0
    assert bounded[0]["bottom"] != full[0]["bottom"], "pre-bounding was harmless"


def test_strict_overlap_excluding_touch_is_caught():
    """Touching at a single price must merge."""
    geo = {0: _g(0, 10.0, 9.0), 1: _g(1, 9.0, 8.0)}
    correct = fvg_components_sweep([0, 1], geo)
    strict = []
    ordered = sorted(geo, key=lambda i: (geo[i].zone_bottom, geo[i].zone_top, i))
    cur, top = [ordered[0]], geo[ordered[0]].zone_top
    for i in ordered[1:]:
        if geo[i].zone_bottom < top:  # MUTANT: strict <
            cur.append(i)
            top = max(top, geo[i].zone_top)
        else:
            strict.append(sorted(cur))
            cur, top = [i], geo[i].zone_top
    strict.append(sorted(cur))
    assert correct == [[0, 1]]
    assert strict != correct


def test_wrong_sort_key_is_caught():
    """Sorting by TOP instead of BOTTOM breaks the sweep on nested intervals."""
    geo = {0: _g(0, 20.0, 1.0), 1: _g(1, 12.0, 11.0), 2: _g(2, 15.0, 14.0)}
    correct = fvg_components_sweep(list(geo), geo)
    ordered = sorted(geo, key=lambda i: (geo[i].zone_top, i))  # MUTANT
    cur, top = [ordered[0]], geo[ordered[0]].zone_top
    mutant = []
    for i in ordered[1:]:
        if geo[i].zone_bottom <= top:
            cur.append(i)
            top = max(top, geo[i].zone_top)
        else:
            mutant.append(sorted(cur))
            cur, top = [i], geo[i].zone_top
    mutant.append(sorted(cur))
    assert correct == [[0, 1, 2]]
    assert mutant != correct


def test_sweep_matches_union_find_on_randomized_buckets():
    """Direct component-level differential, independent of the group builder.

    Compared as MEMBERSHIP, not as an ordered list. The union-find oracle's
    component order follows its internal root ids, and a root is not always
    the component's lowest member: merging b into a sets `parent[find(b)] =
    find(a)`, so an already-merged smaller root can be re-parented under a
    larger one. That ordering is therefore not a contract. It also cannot
    leak, because `build_visual_groups` re-sorts every group by
    (distance, min member) -- see the test below."""
    rng = random.Random(31337)
    for _ in range(200):
        n = rng.randint(1, 60)
        geo = {}
        for i in range(n):
            b = round(rng.uniform(0.0, 50.0), 2)
            geo[i] = _g(i, round(b + rng.choice([0.0, 0.1, 1.0, 5.0]), 2), b)
        sweep = {frozenset(c) for c in fvg_components_sweep(list(geo), geo)}
        union = {frozenset(c) for c in fvg_connected_components(list(geo), geo)}
        assert sweep == union


def test_sweep_component_order_is_by_lowest_member():
    """The sweep gives a stronger guarantee than the oracle: components come
    back ordered by their lowest registry index, deterministically."""
    rng = random.Random(99)
    for _ in range(50):
        geo = {}
        for i in range(rng.randint(1, 40)):
            b = round(rng.uniform(0.0, 50.0), 2)
            geo[i] = _g(i, round(b + rng.choice([0.0, 0.5, 3.0]), 2), b)
        comps = fvg_components_sweep(list(geo), geo)
        firsts = [c[0] for c in comps]
        assert firsts == sorted(firsts)
        assert all(c == sorted(c) for c in comps)


def test_component_order_cannot_leak_into_the_projection():
    """Group ordering in the final projection depends only on
    (distance, min member), so the two grouping algorithms' differing
    component order provably cannot change what is drawn."""
    geo = _random_universe(2024, 300)
    slow = build_visual_groups(list(geo), geo, 4380.0, 10**6, "1")
    fast = build_visual_groups_fast(list(geo), geo, 4380.0, 10**6, "1")
    keys_slow = [(g["distance"], min(g["members"])) for g in slow]
    keys_fast = [(g["distance"], min(g["members"])) for g in fast]
    assert keys_slow == sorted(keys_slow)
    assert keys_slow == keys_fast


def test_non_fvg_near_overlaps_still_never_group():
    geo = {
        0: _g(0, 10.0, 9.0, poi_type=1, avail=100),
        1: _g(1, 9.99, 8.9, poi_type=1, avail=100),
    }
    groups = _assert_equivalent(geo, 100.0)
    assert len(groups) == 2


def test_member_ids_are_never_lost():
    geo = _random_universe(777, 400)
    slow = build_visual_groups(list(geo), geo, 4380.0, 10**6, "1")
    fast = build_visual_groups_fast(list(geo), geo, 4380.0, 10**6, "1")
    flat_slow = sorted(i for g in slow for i in g["members"])
    flat_fast = sorted(i for g in fast for i in g["members"])
    assert flat_slow == flat_fast == sorted(geo)


# ---- Phase 17: operation-count evidence ---------------------------------


def test_optimized_path_does_far_less_work():
    geo = _random_universe(555, 400)
    ops = OpCount()
    build_visual_groups_fast(list(geo), geo, 4380.0, CAPACITY, "1", ops)
    # the quadratic oracle would perform on the order of n^2 = 160_000
    # envelope comparisons; the sweep is bounded by n plus its sorts.
    assert ops.compares < len(geo) * 4, (ops.compares, len(geo))
    assert ops.sorts <= 2


# ---- Pine-port differential for the sort-and-sweep build -----------------
# The Pine build cannot call the model, and it constructs non-FVG combined
# labels INCREMENTALLY (append a name, keep any "• STRONG" last) rather than
# from a finished member list. That string surgery is the risky part, so the
# whole Pine algorithm is simulated here and required to match.


def test_no_type_name_is_a_substring_of_another():
    """The Pine build tests `str.contains(label, name)` before appending a
    type name. That is only sound if no name contains another."""
    from tests.parity_support.p7z_zone_model import POI_TYPE_LABEL

    names = list(POI_TYPE_LABEL.values())
    for a in names:
        for b in names:
            if a != b:
                assert a not in b, f"{a!r} is a substring of {b!r}"


def _pine_sweep_groups(active, geo, close, capacity, period):
    """Line-for-line simulation of the DEV's partition/sort/sweep block."""
    from tests.parity_support.p7z_zone_model import (
        FVG_TYPES,
        timeframe_label,
        type_label,
    )

    poi_idx = sorted(active)
    tf = timeframe_label(period)
    g_top, g_bot, g_left, g_bull = [], [], [], []
    g_key, g_count, g_names, g_strong, g_term = [], [], [], [], []

    for want_dir in (DIRECTION_BULLISH, DIRECTION_BEARISH):
        bucket = [
            i for i in poi_idx
            if geo[i].poi_type in FVG_TYPES and geo[i].direction == want_dir
        ]
        if not bucket:
            continue
        # array.sort_indices on bottom, ascending (stable in the sim)
        ordered = sorted(bucket, key=lambda i: geo[i].zone_bottom)
        cur = None
        for i in ordered:
            bt, tp = geo[i].zone_bottom, geo[i].zone_top
            if cur is None or bt > cur["top"]:
                if cur is not None:
                    g_top.append(cur["top"])
                    g_bot.append(cur["bot"])
                    g_left.append(cur["left"])
                    g_bull.append(want_dir == DIRECTION_BULLISH)
                    g_key.append(cur["key"])
                    g_count.append(cur["n"])
                    g_names.append(f"{type_label(cur['type'])}"
                                   + (f" ×{cur['n']}" if cur["n"] > 1 else ""))
                    g_strong.append(False)
                    g_term.append(cur["term"])
                cur = {"top": tp, "bot": bt, "left": geo[i].avail_time_ms,
                       "key": i, "n": 1, "term": False, "type": geo[i].poi_type}
            else:
                cur["top"] = max(cur["top"], tp)
                cur["bot"] = min(cur["bot"], bt)
                cur["left"] = min(cur["left"], geo[i].avail_time_ms)
                cur["key"] = min(cur["key"], i)
                cur["n"] += 1
        if cur is not None:
            g_top.append(cur["top"])
            g_bot.append(cur["bot"])
            g_left.append(cur["left"])
            g_bull.append(want_dir == DIRECTION_BULLISH)
            g_key.append(cur["key"])
            g_count.append(cur["n"])
            g_names.append(f"{type_label(cur['type'])}"
                           + (f" ×{cur['n']}" if cur["n"] > 1 else ""))
            g_strong.append(False)
            g_term.append(cur["term"])

    slot: dict[str, int] = {}
    for i in poi_idx:
        if geo[i].poi_type in FVG_TYPES:
            continue
        gd = geo[i]
        gk = f"{gd.zone_top}|{gd.zone_bottom}|{gd.avail_time_ms}|{gd.direction}"
        is_strong = gd.tier == TIER_STRONG
        nm = type_label(gd.poi_type)
        if gk in slot:
            gi = slot[gk]
            g_count[gi] += 1
            g_key[gi] = min(g_key[gi], i)
            g_strong[gi] = g_strong[gi] or is_strong
            # Mirrors the Pine primary-name rule: an engulfing joining a
            # group that already names an ORDER BLOCK is not appended.
            if nm not in g_names[gi] and not (
                gd.poi_type in (11, 12) and " OB" in g_names[gi]
            ):
                g_names[gi] = f"{g_names[gi]} + {nm}"
        else:
            slot[gk] = len(g_top)
            g_top.append(gd.zone_top)
            g_bot.append(gd.zone_bottom)
            g_left.append(gd.avail_time_ms)
            g_bull.append(gd.direction == DIRECTION_BULLISH)
            g_key.append(i)
            g_count.append(1)
            g_names.append(nm)
            g_strong.append(is_strong)
            g_term.append(False)

    out = []
    for gi in range(len(g_top)):
        top, bot = g_top[gi], g_bot[gi]
        d = 0.0 if bot <= close <= top else (close - top if close > top else bot - close)
        # label assembled at DRAW time from names + strong, as the Pine does
        lab = f"{tf} • {g_names[gi]}" + (" • STRONG" if g_strong[gi] else "")
        out.append({"key": g_key[gi], "top": top, "bottom": bot,
                    "left_time_ms": g_left[gi], "label": lab, "distance": d,
                    "direction": DIRECTION_BULLISH if g_bull[gi] else DIRECTION_BEARISH})
    out.sort(key=lambda g: (g["distance"], g["key"]))
    return out[: min(capacity, len(out))]


@pytest.mark.parametrize("seed", range(40))
def test_pine_sweep_build_matches_the_model(seed):
    geo = _random_universe(seed + 60_000, 120)
    close = 4380.0
    model = build_visual_groups_fast(list(geo), geo, close, CAPACITY, "1")
    pine = _pine_sweep_groups(list(geo), geo, close, CAPACITY, "1")
    assert len(pine) == len(model)
    for a, b in zip(model, pine, strict=True):
        assert a["top"] == b["top"]
        assert a["bottom"] == b["bottom"]
        assert a["left_time_ms"] == b["left_time_ms"]
        assert a["direction"] == b["direction"]
        assert a["distance"] == b["distance"]
        assert a["label"] == b["label"]
        assert min(a["members"]) == b["key"]


@pytest.mark.parametrize("n", [1, 20, 150, 400, 900])
def test_pine_sweep_build_matches_at_scale(n):
    geo = _random_universe(31_000 + n, n)
    model = build_visual_groups_fast(list(geo), geo, 4380.0, CAPACITY, "1")
    pine = _pine_sweep_groups(list(geo), geo, 4380.0, CAPACITY, "1")
    assert [g["label"] for g in model] == [g["label"] for g in pine]
    assert [min(g["members"]) for g in model] == [g["key"] for g in pine]


def test_pine_incremental_strong_label_matches_finished_label():
    """The incremental '+ NAME' with a trailing STRONG is where the Pine
    string surgery could diverge from the model's one-shot construction."""
    geo = {
        0: _g(0, 10.0, 9.0, poi_type=1, avail=500, tier=TIER_STANDARD),
        1: _g(1, 10.0, 9.0, poi_type=11, avail=500, tier=TIER_STRONG),
        2: _g(2, 10.0, 9.0, poi_type=13, avail=500, tier=TIER_STANDARD),
    }
    model = build_visual_groups_fast(list(geo), geo, 100.0, CAPACITY, "1")
    pine = _pine_sweep_groups(list(geo), geo, 100.0, CAPACITY, "1")
    assert model[0]["label"] == pine[0]["label"]
    assert pine[0]["label"].endswith(" • STRONG")
    assert pine[0]["label"].count("STRONG") == 1
