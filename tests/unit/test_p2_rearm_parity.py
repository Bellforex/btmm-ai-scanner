"""Parity between the Pine P2-I6 weak re-arm and production Python.

The model is the one in `test_p2_bos_parity.py`, extended with the re-arm branch;
production `analyze_structure_state` is always the reference side. Every
assertion here goes through `_assert_parity`, which compares direction, both
protected keys, both weak keys, the full transition sequence AND the published
`availability_time_utc`.

THE RULE THAT IS EASY TO GET WRONG - AND AN HONEST LIMIT ON THIS FILE
---------------------------------------------------------------------
Weak re-arm takes the **FIRST** qualifying swing after the boundary; protected
replacement takes the **NEWEST** eligible candidate. They are written as opposite
rules a few lines apart, and the Pine port transcribes the source rule.

But for the *weak* side the two turn out to be **provably equivalent** under the
validated input contract - see
`test_first_qualifying_and_newest_eligible_coincide_for_re_arm` for the argument
and the empirical check. So no fixture in this file can discriminate them, and
substituting the newest-wins selector into the re-arm produces zero parity
failures. That is a property of the contract, not a gap in the fixtures.

The prohibition is therefore enforced as a **source guard**
(`test_pine_re_arm_does_not_call_the_protected_selector`), not behaviourally: the
equivalence depends on `conf_bar >= pivot_bar` and on the boundary rule, and a
future change to either would break it silently.

SCOPE. I6 adds re-arm only. CHOCH is still unimplemented in Pine, and the I5
CHOCH price guard remains a BOS suppressor that sets no boundary — so it cannot
feed re-arm. `test_choch_suppression_still_sets_no_boundary` holds that line.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure.enums import StructureTransitionType


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_bos = _load("_p2rearm_bos", "test_p2_bos_parity.py")

_build = _bos._build
_key = _bos._key
_pine_walk = _bos._pine_walk
_assert_parity = _bos._assert_parity
_assert_prefix_parity = _bos._assert_prefix_parity
_analyze = _bos._analyze
BAR_COUNT = _bos.BAR_COUNT

DIR_BULLISH, DIR_BEARISH = _bos.DIR_BULLISH, _bos.DIR_BEARISH
H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW

_BULL = _bos._BULL
_BEAR = _bos._BEAR
BULL_NEUTRAL, BEAR_NEUTRAL = _bos.BULL_NEUTRAL, _bos.BEAR_NEUTRAL

PINE = Path(__file__).resolve().parents[2] / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"

# BOS #1 at bar 10 clears the weak high and sets the boundary to 10; H3 pivots at
# bar 12 and re-arms; BOS #2 at bar 20 breaks the re-armed level.
_BULL_CYCLE = _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)]
_BULL_CYCLE_OVR = {10: {"close": "113"}, 20: {"close": "121"}}
_BEAR_CYCLE = _BEAR + [(H, "106", 10, 11), (L, "90", 12, 13)]
_BEAR_CYCLE_OVR = {10: {"close": "97"}, 20: {"close": "89"}}


# ---------------------------------------------------------------------------
# 1 / 2 — re-arm happens, both directions
# ---------------------------------------------------------------------------

def test_bullish_weak_high_re_arms_after_the_boundary() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, {10: {"close": "113"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high == _key(candles, 12), "H3 re-armed the slot"
    assert len(walk.transitions) == 1


def test_bearish_weak_low_re_arms_after_the_boundary() -> None:
    candles, swings = _build(_BEAR_CYCLE, BEAR_NEUTRAL, {10: {"close": "97"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_low == _key(candles, 12)
    assert len(walk.transitions) == 1


# ---------------------------------------------------------------------------
# 3 / 4 / 5 — strict boundary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("break_bar", "expect_arm"), [(11, True), (12, False)]
)
def test_boundary_is_strict_bullish(break_bar: int, expect_arm: bool) -> None:
    """H3 pivots at bar 12: breaking at 11 leaves 12 > 11 (arm), breaking at 12
    leaves 12 > 12 false (reject)."""
    candles, swings = _build(
        _BULL_CYCLE, BULL_NEUTRAL, {break_bar: {"close": "113"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert (walk.weak_high == _key(candles, 12)) is expect_arm
    if not expect_arm:
        assert walk.weak_high is None


@pytest.mark.parametrize(
    ("break_bar", "expect_arm"), [(11, True), (12, False)]
)
def test_boundary_is_strict_bearish(break_bar: int, expect_arm: bool) -> None:
    candles, swings = _build(
        _BEAR_CYCLE, BEAR_NEUTRAL, {break_bar: {"close": "97"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert (walk.weak_low == _key(candles, 12)) is expect_arm


def test_a_pivot_before_the_boundary_never_arms() -> None:
    """H3 pivots at bar 12 but confirms at bar 16, after a break at bar 14."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 16)],
        BULL_NEUTRAL,
        {14: {"close": "113"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert walk.weak_high is None


# ---------------------------------------------------------------------------
# 6 / 7 — swing type and direction filters
# ---------------------------------------------------------------------------

def test_wrong_type_and_wrong_direction_are_both_rejected() -> None:
    """In a BEARISH structure a HIGH past the boundary must not arm anything: it
    fails the type test for weak_low and the direction test for weak_high."""
    candles, swings = _build(
        _BEAR + [(H, "106", 11, 12), (L, "90", 13, 14)],
        BEAR_NEUTRAL,
        {10: {"close": "97"}},
    )
    h3 = _key(candles, 11)
    walk, _ = _assert_parity(candles, swings)
    assert walk.direction == DIR_BEARISH
    assert walk.weak_high is None, "a HIGH must not arm while BEARISH"
    assert walk.weak_high != h3
    assert walk.weak_low == _key(candles, 13), "the LOW does arm"


def test_a_low_past_the_boundary_does_not_arm_the_weak_high() -> None:
    candles, swings = _build(
        _BULL + [(L, "104", 11, 12), (H, "120", 13, 14)],
        BULL_NEUTRAL,
        {10: {"close": "113"}},
    )
    walks = _assert_prefix_parity(candles, swings)
    # After the LOW is visible (bar 12 availability) but before the HIGH (bar 14).
    assert walks[12].weak_high is None, "a LOW must not arm the weak HIGH"
    assert walks[-1].weak_high == _key(candles, 13)


# ---------------------------------------------------------------------------
# 8 / 9 / 10 — occupied slot, first-wins, no return
# ---------------------------------------------------------------------------

def test_an_occupied_slot_is_not_replaced() -> None:
    """H3 becomes visible while H2 is still armed, so it is passed over."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL,
        {20: {"close": "113"}},
    )
    walks = _assert_prefix_parity(candles, swings)
    assert walks[19].weak_high == _key(candles, 8), "still H2 — H3 ignored"
    assert walks[-1].weak_high is None, "H3 does not return after the BOS"
    assert walks[-1].transitions[0][1] == _key(candles, 8)


def test_the_first_qualifying_swing_wins_not_the_newest() -> None:
    """H3 (bar 12) and H4 (bar 16) both qualify after the boundary; H3 arms."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "103", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL,
        {10: {"close": "113"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high == _key(candles, 12), "FIRST"
    assert walk.weak_high != _key(candles, 16), "not newest"


def test_the_two_selection_rules_are_written_differently() -> None:
    """One fixture exercising both: the weak slot kept its FIRST armed high and
    was never replaced, while protected took the NEWEST low."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "103", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL,
        {20: {"close": "113"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.protected_low == _key(candles, 14), "protected: NEWEST low"
    assert walk.transitions[0][1] == _key(candles, 8), "weak: never replaced"


def test_first_qualifying_and_newest_eligible_coincide_for_re_arm() -> None:
    """The two selection rules cannot be told apart by any valid fixture.

    Suppose swing S arms the slot and some other visible unbroken same-type swing
    H has a LARGER pivot index. Validation forces `conf_bar >= pivot_bar`, so H
    became visible at or after `pivot_H + 1`.

      * If the slot was EMPTY when H became visible, H would have armed (its
        pivot also clears the boundary), so the slot could not still be empty
        for S.
      * So the slot was OCCUPIED at H's visibility and was emptied later by a
        break at candle index B_new, with `visible_H <= B_new + 1`, hence
        `pivot_H <= B_new`. S must clear that new boundary:
        `pivot_S > B_new >= pivot_H`, i.e. `pivot_S > pivot_H` - contradicting
        `pivot_H > pivot_S`.

    So no such H exists: the armed swing is always also the newest eligible one.
    Checked empirically across the campaign below.
    """
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        normal = _pine_walk(candles, swings)
        newest = _walk_with_newest_wins_re_arm(candles, swings)
        assert (normal.weak_high, normal.weak_low) == newest, (
            "the equivalence argument failed - first-wins and newest-wins "
            "diverged, so the source rule must be transcribed exactly"
        )


def _walk_with_newest_wins_re_arm(candles, swings):
    """The model with the protected selector wired into the re-arm assignment."""
    views = [_bos._V(s) for s in swings]
    rels = _bos._pine_rels(swings)
    rel_order = _bos._pine_order_rels(rels)
    swing_order = _bos._pine_order_swings(views)
    closes = [c.close for c in candles]
    avail_t = [c.availability_time_utc for c in candles]

    direction = _bos.DIR_UNDETERMINED
    prot_high_ix = prot_low_ix = weak_high_ix = weak_low_ix = -1
    wh_bound = wl_bound = -1
    hi_label = lo_label = hi_key = lo_key = None
    broken: list = []
    vis: list = []
    ci = si = ri = 0
    nc, ns, nr = len(closes), len(swing_order), len(rel_order)

    for _ in range(nc + ns + nr):
        pick, best_t = -1, None
        if ci < nc:
            pick, best_t = 0, avail_t[ci]
        if si < ns and (pick < 0 or views[swing_order[si]].meaningfulConfTime < best_t):
            pick, best_t = 1, views[swing_order[si]].meaningfulConfTime
        if ri < nr and (pick < 0 or rels[rel_order[ri]][3] < best_t):
            pick, best_t = 2, rels[rel_order[ri]][3]

        if pick == 0:
            guard = False
            if direction == _bos.DIR_BEARISH and prot_high_ix >= 0:
                guard = closes[ci] > views[prot_high_ix].pivotPrice
            if direction == _bos.DIR_BULLISH and prot_low_ix >= 0:
                guard = closes[ci] < views[prot_low_ix].pivotPrice
            if not guard:
                bh = (direction == _bos.DIR_BULLISH and weak_high_ix >= 0
                      and closes[ci] > views[weak_high_ix].pivotPrice)
                bl = (direction == _bos.DIR_BEARISH and weak_low_ix >= 0
                      and closes[ci] < views[weak_low_ix].pivotPrice)
                if bh or bl:
                    bix = weak_high_ix if bh else weak_low_ix
                    broken.append(views[bix].stableKey)
                    want = _bos.SWING_LOW if bh else _bos.SWING_HIGH
                    repl = _bos._pine_most_recent_unbroken(views, vis, want, broken)
                    existing = prot_low_ix if bh else prot_high_ix
                    new_prot = repl if repl >= 0 else existing
                    if bh:
                        prot_low_ix, weak_high_ix, wh_bound = new_prot, -1, ci
                    else:
                        prot_high_ix, weak_low_ix, wl_bound = new_prot, -1, ci
            ci += 1
        elif pick == 1:
            v_ix = swing_order[si]
            vs = views[v_ix]
            vis.append(v_ix)
            if (vs.swingType == _bos.SWING_HIGH and direction == _bos.DIR_BULLISH
                    and weak_high_ix < 0 and vs.pivotStartAbs > wh_bound
                    and vs.stableKey not in broken):
                weak_high_ix = _bos._pine_most_recent_unbroken(
                    views, vis, _bos.SWING_HIGH, broken
                )
            if (vs.swingType == _bos.SWING_LOW and direction == _bos.DIR_BEARISH
                    and weak_low_ix < 0 and vs.pivotStartAbs > wl_bound
                    and vs.stableKey not in broken):
                weak_low_ix = _bos._pine_most_recent_unbroken(
                    views, vis, _bos.SWING_LOW, broken
                )
            si += 1
        else:
            r = rels[rel_order[ri]]
            if r[2] in _bos._boot._HIGH_CODES:
                hi_label, hi_key = r[2], r[0]
            else:
                lo_label, lo_key = r[2], r[0]
            if direction == _bos.DIR_UNDETERMINED:
                if hi_label == _bos._boot.C_HH and lo_label == _bos._boot.C_HL:
                    direction = _bos.DIR_BULLISH
                    prot_low_ix = next(i for i, v in enumerate(views) if v.stableKey == lo_key)
                    weak_high_ix = next(i for i, v in enumerate(views) if v.stableKey == hi_key)
                elif hi_label == _bos._boot.C_LH and lo_label == _bos._boot.C_LL:
                    direction = _bos.DIR_BEARISH
                    prot_high_ix = next(i for i, v in enumerate(views) if v.stableKey == hi_key)
                    weak_low_ix = next(i for i, v in enumerate(views) if v.stableKey == lo_key)
            ri += 1

    return (
        views[weak_high_ix].stableKey if weak_high_ix >= 0 else None,
        views[weak_low_ix].stableKey if weak_low_ix >= 0 else None,
    )


def test_pine_re_arm_does_not_call_the_protected_selector() -> None:
    """Enforced at the source, because the equivalence above means no fixture can
    catch it behaviourally. That equivalence depends on `conf_bar >= pivot_bar`
    and on the boundary rule; if either changes the rules diverge, and only this
    guard would notice."""
    text = PINE.read_text(encoding="utf-8")
    branch = text.split("else if pick == 1")[1].split("            else\n")[0]
    code = "\n".join(
        line for line in branch.splitlines() if not line.strip().startswith("//")
    )
    assert "f_p2MostRecentUnbroken" not in code, (
        "weak re-arm must not reuse the newest-wins protected selector"
    )
    assert "array.sort" not in code and "f_p2Order" not in code


# ---------------------------------------------------------------------------
# 11 — defensive broken-key filter
# ---------------------------------------------------------------------------

def test_the_broken_key_filter_is_present_in_pine_and_in_the_model() -> None:
    """Unreachable in valid state (a swing cannot be broken at its own
    SWING_VISIBLE) but reproduced deliberately, per the 17.5a policy."""
    text = PINE.read_text(encoding="utf-8")
    branch = text.split("else if pick == 1")[1].split("            else\n")[0]
    assert branch.count("array.indexof(brokenKeys, vs.stableKey) < 0") == 2
    assert "runtime.error" not in branch

    model = Path(_bos.__file__).read_text(encoding="utf-8")
    rearm = model.split("# P2-I6 weak re-arm")[1].split("        else:")[0]
    assert rearm.count("vs.stableKey not in broken_keys") == 2


def test_no_swing_is_ever_broken_before_its_own_visibility() -> None:
    """The empirical half of the unreachability argument, on I6 fixtures."""
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        analysis = _analyze(candles, tuple(swings))
        by_id = {s.record_id: s for s in swings}
        candle_by_id = {c.record_id: c for c in candles}
        for transition in analysis.structure_transitions:
            broken = by_id[transition.broken_swing_id]
            candle = candle_by_id[transition.break_candle_id]
            assert broken.meaningful_confirmation_time_utc <= (
                candle.availability_time_utc
            )


# ---------------------------------------------------------------------------
# 12 — boundary persistence
# ---------------------------------------------------------------------------

def test_re_arming_does_not_move_the_boundary() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, {10: {"close": "113"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high == _key(candles, 12), "it did re-arm"
    assert walk.weak_high_boundary == 10, "and the boundary stayed at the break"
    assert walk.weak_low_boundary == -1


def test_the_boundary_advances_only_on_a_later_break() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR)
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 2
    assert walk.weak_high_boundary == 20


def test_pine_re_arm_branch_never_assigns_a_boundary() -> None:
    text = PINE.read_text(encoding="utf-8")
    branch = text.split("else if pick == 1")[1].split("            else\n")[0]
    code = "\n".join(
        line for line in branch.splitlines() if not line.strip().startswith("//")
    )
    assert "weakHighBoundaryAbs :=" not in code
    assert "weakLowBoundaryAbs :=" not in code
    assert "weakHighBoundaryAbs" in code, "it must still READ the boundary"
    assert "weakLowBoundaryAbs" in code


# ---------------------------------------------------------------------------
# 13 / 14 — the second BOS cycle, the central I6 proof
# ---------------------------------------------------------------------------

def test_second_bullish_bos_after_re_arm() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR)
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 2
    first, second = walk.transitions
    assert first[0] == second[0] == 1, "both BULLISH_BOS"
    assert first[1] == _key(candles, 8)
    assert second[1] == _key(candles, 12), "the RE-ARMED level breaks"
    assert first[1] != second[1], "two distinct broken keys"
    assert first[6] == _key(candles, 6), "protected: L2"
    assert second[6] == _key(candles, 10), "protected: newest unbroken low"
    assert walk.broken == [_key(candles, 8), _key(candles, 12)]
    assert walk.weak_high is None, "cleared again by BOS #2"
    assert len(analysis.structure_transitions) == 2


def test_second_bearish_bos_after_re_arm() -> None:
    candles, swings = _build(_BEAR_CYCLE, BEAR_NEUTRAL, _BEAR_CYCLE_OVR)
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 2
    first, second = walk.transitions
    assert first[0] == second[0] == -1
    assert first[1] == _key(candles, 8)
    assert second[1] == _key(candles, 12)
    assert walk.weak_low is None


def test_the_cycle_really_passes_through_an_empty_slot() -> None:
    """Guard the guard: two breaks only prove re-arm if the slot emptied between
    them."""
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR)
    walks = _assert_prefix_parity(candles, swings)
    trace = [w.weak_high for w in walks]
    distinct = [k for i, k in enumerate(trace) if i == 0 or k != trace[i - 1]]
    assert distinct == [
        None, _key(candles, 8), None, _key(candles, 12), None
    ], distinct


# ---------------------------------------------------------------------------
# 15 — event ordering
# ---------------------------------------------------------------------------

# H3 pivots at bar 12 and confirms at bar 14, so its SWING_VISIBLE availability
# ties exactly with candle 14's. CANDLE goes first, so candle 14 sees an empty
# slot and emits nothing; only then does H3 arm.
_ORDER = _BULL + [(L, "104", 10, 11), (H, "115", 12, 14)]
_ORDER_OVR = {10: {"close": "113"}, 14: {"close": "116"}}


def test_the_order_fixture_really_ties() -> None:
    candles, swings = _build(_ORDER, BULL_NEUTRAL, _ORDER_OVR)
    h3 = next(s for s in swings if s.pivot_bar_index == 12)
    assert h3.meaningful_confirmation_time_utc == candles[14].availability_time_utc


def test_candle_is_processed_before_swing_visible() -> None:
    candles, swings = _build(_ORDER, BULL_NEUTRAL, _ORDER_OVR)
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1, "candle 14 must not break the new level"
    assert walk.weak_high == _key(candles, 12)


def test_swapping_the_order_in_the_model_produces_a_false_second_bos() -> None:
    """Guard the guard: the CANDLE < SWING_VISIBLE tie rule is load-bearing."""
    candles, swings = _build(_ORDER, BULL_NEUTRAL, _ORDER_OVR)
    swapped = _walk_with_swing_before_candle(candles, swings)
    assert len(swapped) == 2, "wrong order breaks the newly armed level"
    assert len(_pine_walk(candles, swings).transitions) == 1


def _walk_with_swing_before_candle(candles, swings):
    """Re-run the model with the two event kinds transposed. Exists only to prove
    the shipped ordering matters."""
    views = [_bos._V(s) for s in swings]
    rels = _bos._pine_rels(swings)
    rel_order = _bos._pine_order_rels(rels)
    swing_order = _bos._pine_order_swings(views)
    closes = [c.close for c in candles]
    avail_t = [c.availability_time_utc for c in candles]

    direction = _bos.DIR_UNDETERMINED
    prot_low_ix = weak_high_ix = -1
    wh_bound = -1
    hi_label = lo_label = None
    hi_key = lo_key = None
    broken: list = []
    events: list = []
    ci = si = ri = 0
    nc, ns, nr = len(closes), len(swing_order), len(rel_order)

    for _ in range(nc + ns + nr):
        pick, best_t = -1, None
        if si < ns:                                  # <-- swings tested FIRST
            sv = views[swing_order[si]]
            pick, best_t = 1, sv.meaningfulConfTime
        if ci < nc and (pick < 0 or avail_t[ci] < best_t):
            pick, best_t = 0, avail_t[ci]
        if ri < nr:
            rr = rels[rel_order[ri]]
            if pick < 0 or rr[3] < best_t:
                pick, best_t = 2, rr[3]

        if pick == 0:
            if (direction == _bos.DIR_BULLISH and weak_high_ix >= 0
                    and closes[ci] > views[weak_high_ix].pivotPrice):
                broken.append(views[weak_high_ix].stableKey)
                events.append(views[weak_high_ix].stableKey)
                weak_high_ix, wh_bound = -1, ci
            ci += 1
        elif pick == 1:
            v_ix = swing_order[si]
            vs = views[v_ix]
            if (vs.swingType == _bos.SWING_HIGH and direction == _bos.DIR_BULLISH
                    and weak_high_ix < 0 and vs.pivotStartAbs > wh_bound
                    and vs.stableKey not in broken):
                weak_high_ix = v_ix
            si += 1
        else:
            r = rels[rel_order[ri]]
            if r[2] in _bos._boot._HIGH_CODES:
                hi_label, hi_key = r[2], r[0]
            else:
                lo_label, lo_key = r[2], r[0]
            if direction == _bos.DIR_UNDETERMINED and hi_label == _bos._boot.C_HH \
                    and lo_label == _bos._boot.C_HL:
                direction = _bos.DIR_BULLISH
                prot_low_ix = next(
                    i for i, v in enumerate(views) if v.stableKey == lo_key
                )
                weak_high_ix = next(
                    i for i, v in enumerate(views) if v.stableKey == hi_key
                )
            ri += 1
    del prot_low_ix
    return events


# ---------------------------------------------------------------------------
# 16 — bounded window
# ---------------------------------------------------------------------------

def test_removing_the_re_arming_swing_removes_the_second_bos() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR)
    full, _ = _assert_parity(candles, swings)
    assert len(full.transitions) == 2

    trimmed_swings = tuple(s for s in swings if s.pivot_bar_index != 12)
    trimmed, _ = _assert_parity(candles, trimmed_swings)
    assert len(trimmed.transitions) == 1, "no candidate, no second break"
    assert trimmed.weak_high is None, "no hidden candidate survives"


def test_re_arm_holds_no_state_across_the_window_edge() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR)
    for start in range(len(swings)):
        _assert_parity(candles, swings[start:])


# ---------------------------------------------------------------------------
# 17 — the CHOCH suppression guard is still only a suppressor
# ---------------------------------------------------------------------------

def test_choch_suppression_still_sets_no_boundary() -> None:
    """I6 must not let the I5 price guard become a CHOCH: it may not set a
    boundary, and therefore may not trigger a re-arm."""
    candles, swings = _build(_bos._PRECEDENCE_BULL, _bos._PRECEDENCE_NEUTRAL)
    walk = _pine_walk(candles, swings)
    assert walk.suppressed >= 1, "the guard fired"
    assert walk.transitions == [], "no BOS"
    assert walk.weak_high_boundary == -1, "suppression must not set a boundary"
    assert walk.weak_low_boundary == -1
    assert walk.broken == [], "suppression must consume nothing"


def test_pine_suppression_path_still_mutates_only_the_counter() -> None:
    text = PINE.read_text(encoding="utf-8")
    candle = text.split("if pick == 0")[1].split("            else if pick == 1")[0]
    taken = candle.split("if chochGuard")[1].split("\n                else\n")[0]
    import re
    assert set(re.findall(r"(\w+)\s*:=", taken)) == {"suppressed"}, taken


def test_no_choch_transition_is_emitted_anywhere() -> None:
    text = PINE.read_text(encoding="utf-8")
    for code in ("C_ST_TR_BULLISH_CHOCH", "C_ST_TR_BEARISH_CHOCH"):
        assert text.count(code) == 1, f"{code} used beyond its declaration"


# ---------------------------------------------------------------------------
# Prefix parity and campaign
# ---------------------------------------------------------------------------

_CAMPAIGN = {
    "bull_cycle": (_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVR),
    "bear_cycle": (_BEAR_CYCLE, BEAR_NEUTRAL, _BEAR_CYCLE_OVR),
    "bull_rearm_only": (_BULL_CYCLE, BULL_NEUTRAL, {10: {"close": "113"}}),
    "bear_rearm_only": (_BEAR_CYCLE, BEAR_NEUTRAL, {10: {"close": "97"}}),
    "boundary_equal": (_BULL_CYCLE, BULL_NEUTRAL, {12: {"close": "113"}}),
    "boundary_before": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 16)],
        BULL_NEUTRAL, {14: {"close": "113"}},
    ),
    "wrong_type_and_direction": (
        _BEAR + [(H, "106", 11, 12), (L, "90", 13, 14)],
        BEAR_NEUTRAL, {10: {"close": "97"}},
    ),
    "occupied_slot": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL, {20: {"close": "113"}},
    ),
    "first_not_newest": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "103", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL, {10: {"close": "113"}},
    ),
    "event_order_tie": (_ORDER, BULL_NEUTRAL, _ORDER_OVR),
}


@pytest.mark.parametrize("name", sorted(_CAMPAIGN))
def test_campaign_prefix_parity(name: str) -> None:
    specs, neutral, overrides = _CAMPAIGN[name]
    candles, swings = _build(specs, neutral, overrides)
    _assert_prefix_parity(candles, swings)


def _count_re_arms(walks) -> int:
    re_arms = 0
    previous = walks[0]
    for walk in walks[1:]:
        for before, after, had in (
            (previous.weak_high, walk.weak_high, previous.transitions),
            (previous.weak_low, walk.weak_low, previous.transitions),
        ):
            if before is None and after is not None and had:
                re_arms += 1
        previous = walk
    return re_arms


def test_campaign_totals() -> None:
    comparisons = 0
    re_arms = 0
    second_bos = 0
    bull = bear = 0

    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walks = _assert_prefix_parity(candles, swings)
        comparisons += len(walks)
        re_arms += _count_re_arms(walks)
        final = walks[-1]
        if len(final.transitions) >= 2:
            second_bos += 1
        for transition in final.transitions:
            if transition[0] == 1:
                bull += 1
            else:
                bear += 1

    assert len(_CAMPAIGN) == 10
    assert comparisons == 10 * BAR_COUNT == 240
    assert re_arms == 7, re_arms
    assert second_bos == 2, second_bos
    assert bull >= 1 and bear >= 1, (bull, bear)


def test_the_campaign_actually_reaches_re_arm_in_both_directions() -> None:
    """Fails on degeneration."""
    bullish = bearish = 0
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walks = _assert_prefix_parity(candles, swings)
        if _count_re_arms(walks) == 0:
            continue
        if walks[-1].direction == DIR_BULLISH:
            bullish += 1
        elif walks[-1].direction == DIR_BEARISH:
            bearish += 1
    assert bullish >= 2, bullish
    assert bearish >= 2, bearish
