"""Parity between the Pine P2-I5 BOS walk and production Python.

The `_pine_*` helpers below are a faithful test-side transcription of
`f_p2OrderSwings` / `f_p2MostRecentUnbroken` / `f_p2StructureWalk` from
`tradingview/btmm_poi_btrc_scanner_v1.pine`, compared against production
`structure.analyzer.analyze_structure_state`, which is always the reference side.

SCOPE. As of P2-I7 the model covers the whole implemented walk — bootstrap,
BOS, weak re-arm and CHOCH — so `_assert_parity` no longer excludes any fixture
shape.

CHOCH PRECEDENCE
----------------
Python evaluates CHOCH before BOS and `continue`s past the BOS block on **both**
exits — the successful one (`transitions.py:253`) and the aborting one
(`:190`/`:224`). So once the CHOCH predicate is true, BOS is never evaluated on
that candle, whatever happens next. The tests below keep that pinned now that the
predicate leads to a real transition rather than a suppression counter.

MERGED EVENT ORDER. Python sorts all events by `(availability_time, kind,
tiebreak)` with CANDLE=0 < SWING_VISIBLE=1 < RELATIONSHIP=2. Each stream is
already sorted on its own key, so Pine merges them linearly. The model mirrors
that cursor merge rather than calling `sorted()`, so a mistake in the tie rule
shows up here instead of hiding behind Python's stable sort.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)


def _load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_fx = _load("_p2bos_fixtures", "test_structure_transitions_contract.py")
_boot = _load("_p2bos_bootstrap", "test_p2_bootstrap_parity.py")
_tda = _load("_p2bos_tda", "test_structure_bos_fallback_contract.py")

_series = _fx._series
_swing = _fx._swing
_analyze = _fx._analyze
BAR_COUNT = _fx.BAR_COUNT

_pine_rels = _boot._pine_rels
_pine_order_rels = _boot._pine_order
_force_replacement_none = _tda._force_replacement_none

SWING_HIGH, SWING_LOW = 1, -1
DIR_UNDETERMINED, DIR_BULLISH, DIR_BEARISH = 0, 1, -1
C_ST_NA = None

_DIR_FROM_PYTHON = {
    StructureDirection.UNDETERMINED: DIR_UNDETERMINED,
    StructureDirection.BULLISH: DIR_BULLISH,
    StructureDirection.BEARISH: DIR_BEARISH,
}
_TR_FROM_PYTHON = {
    StructureTransitionType.BULLISH_BOS: 1,
    StructureTransitionType.BEARISH_BOS: -1,
    StructureTransitionType.BULLISH_CHOCH: 2,
    StructureTransitionType.BEARISH_CHOCH: -2,
}

H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW


# ---------------------------------------------------------------------------
# Test-side transcription of the Pine walk
# ---------------------------------------------------------------------------

class _V:
    """Mirror of Pine `StructSwingView`."""

    __slots__ = (
        "meaningfulConfTime",
        "pivotPrice",
        "pivotStartAbs",
        "pivotStartTime",
        "referenceAtr",
        "stableKey",
        "swingType",
    )

    def __init__(self, swing) -> None:
        self.stableKey = swing.pivot_end_time_utc
        self.swingType = (
            SWING_HIGH if swing.swing_type == SwingType.SWING_HIGH else SWING_LOW
        )
        self.pivotPrice = swing.pivot_price
        self.referenceAtr = swing.pivot_reference_atr
        self.meaningfulConfTime = swing.meaningful_confirmation_time_utc
        self.pivotStartTime = swing.pivot_start_time_utc
        self.pivotStartAbs = swing.pivot_bar_index


def _pine_order_swings(views) -> list[int]:
    """f_p2OrderSwings — insertion sort on the SWING_VISIBLE event key."""
    order: list[int] = []
    for i, v in enumerate(views):
        pos = len(order)
        for j, other in enumerate(order):
            o = views[other]
            if (v.meaningfulConfTime, v.pivotStartAbs, v.pivotStartTime,
                    v.stableKey) < (o.meaningfulConfTime, o.pivotStartAbs,
                                    o.pivotStartTime, o.stableKey):
                pos = j
                break
        order.insert(pos, i)
    return order


def _pine_most_recent_unbroken(views, vis_order, want_type, broken_keys,
                               force_none=False) -> int:
    """f_p2MostRecentUnbroken. Returns -1 for Python's None."""
    if force_none:
        return -1
    best = -1
    for vi in vis_order:
        v = views[vi]
        if v.swingType != want_type or v.stableKey in broken_keys:
            continue
        if best < 0:
            best = vi
        else:
            b = views[best]
            if (v.pivotStartAbs, v.pivotStartTime, v.stableKey) > (
                b.pivotStartAbs, b.pivotStartTime, b.stableKey
            ):
                best = vi
    return best


class _WalkResult:
    __slots__ = (
        "aborted",
        "broken",
        "direction",
        "last_change",
        "protected_high",
        "protected_low",
        "transitions",
        "weak_high",
        "weak_high_boundary",
        "weak_low",
        "weak_low_boundary",
    )

    def state(self):
        return (self.direction, self.protected_high, self.protected_low,
                self.weak_high, self.weak_low, self.transitions)


def _pine_walk(candles, swings, force_no_replacement=False) -> _WalkResult:
    """f_p2StructureWalk."""
    views = [_V(s) for s in swings]
    rels = _pine_rels(swings)
    rel_order = _pine_order_rels(rels)
    swing_order = _pine_order_swings(views)

    closes = [c.close for c in candles]
    avail_t = [c.availability_time_utc for c in candles]
    open_t = [c.event_time_utc for c in candles]
    abs_first = 0

    direction = DIR_UNDETERMINED
    prot_high_ix = prot_low_ix = weak_high_ix = weak_low_ix = -1
    wh_bound = wl_bound = -1
    hi_label = lo_label = None
    hi_key = lo_key = None
    last_change = None
    aborted = 0
    broken_keys: list = []
    vis_order: list[int] = []
    events: list[tuple] = []

    ci = si = ri = 0
    nc, ns, nr = len(closes), len(swing_order), len(rel_order)

    for _ in range(nc + ns + nr):
        pick, best_t = -1, None
        if ci < nc:
            pick, best_t = 0, avail_t[ci]
        if si < ns:
            sv = views[swing_order[si]]
            if pick < 0 or sv.meaningfulConfTime < best_t:
                pick, best_t = 1, sv.meaningfulConfTime
        if ri < nr:
            rr = rels[rel_order[ri]]
            if pick < 0 or rr[3] < best_t:
                pick, best_t = 2, rr[3]

        if pick == 0:
            bar_close = closes[ci]
            bar_abs = abs_first + ci

            # P2-I7 CHOCH. Exactly one candidate can be set.
            choch_high = (
                direction == DIR_BEARISH and prot_high_ix >= 0
                and bar_close > views[prot_high_ix].pivotPrice
            )
            choch_low = (
                direction == DIR_BULLISH and prot_low_ix >= 0
                and bar_close < views[prot_low_ix].pivotPrice
            )

            if choch_high or choch_low:
                # PRECEDENCE: BOS is not evaluated on this candle, whether the
                # CHOCH succeeds or aborts.
                broken_ix = prot_high_ix if choch_high else prot_low_ix
                broken_sw = views[broken_ix]
                want = SWING_LOW if choch_high else SWING_HIGH
                # PRE-MUTATION ABORT: search before consuming anything.
                repl_ix = _pine_most_recent_unbroken(
                    views, vis_order, want, broken_keys, force_no_replacement
                )
                if repl_ix < 0:
                    aborted += 1                       # zero mutation
                else:
                    broken_keys.append(broken_sw.stableKey)
                    availability = max(avail_t[ci], broken_sw.meaningfulConfTime)
                    events.append(
                        (
                            2 if choch_high else -2,
                            broken_sw.stableKey,
                            broken_sw.pivotPrice,
                            bar_close,
                            open_t[ci],
                            availability,
                            views[repl_ix].stableKey,
                        )
                    )
                    if choch_high:
                        direction = DIR_BULLISH
                        prot_high_ix = -1
                        prot_low_ix = repl_ix
                        wh_bound = bar_abs
                    else:
                        direction = DIR_BEARISH
                        prot_low_ix = -1
                        prot_high_ix = repl_ix
                        wl_bound = bar_abs
                    weak_high_ix = -1
                    weak_low_ix = -1
                    last_change = availability
            else:
                bos_high = (
                    direction == DIR_BULLISH and weak_high_ix >= 0
                    and bar_close > views[weak_high_ix].pivotPrice
                )
                bos_low = (
                    direction == DIR_BEARISH and weak_low_ix >= 0
                    and bar_close < views[weak_low_ix].pivotPrice
                )
                if bos_high or bos_low:
                    broken_ix = weak_high_ix if bos_high else weak_low_ix
                    broken = views[broken_ix]
                    broken_keys.append(broken.stableKey)
                    want = SWING_LOW if bos_high else SWING_HIGH
                    repl_ix = _pine_most_recent_unbroken(
                        views, vis_order, want, broken_keys, force_no_replacement
                    )
                    existing = prot_low_ix if bos_high else prot_high_ix
                    new_prot_ix = repl_ix if repl_ix >= 0 else existing
                    availability = max(avail_t[ci], broken.meaningfulConfTime)
                    events.append(
                        (
                            1 if bos_high else -1,
                            broken.stableKey,
                            broken.pivotPrice,
                            bar_close,
                            open_t[ci],
                            availability,
                            views[new_prot_ix].stableKey if new_prot_ix >= 0 else None,
                        )
                    )
                    if bos_high:
                        prot_low_ix = new_prot_ix
                        weak_high_ix = -1
                        wh_bound = bar_abs
                    else:
                        prot_high_ix = new_prot_ix
                        weak_low_ix = -1
                        wl_bound = bar_abs
                    last_change = availability
            ci += 1

        elif pick == 1:
            v_ix = swing_order[si]
            vs = views[v_ix]
            vis_order.append(v_ix)

            # P2-I6 weak re-arm. Five conditions, FIRST qualifying swing wins —
            # condition 3 (`weak slot unset`) blocks every later candidate, so
            # this must NOT reuse the newest-wins protected selector.
            if (
                vs.swingType == SWING_HIGH
                and direction == DIR_BULLISH
                and weak_high_ix < 0
                and vs.pivotStartAbs > wh_bound
                and vs.stableKey not in broken_keys
            ):
                weak_high_ix = v_ix
                last_change = (
                    vs.meaningfulConfTime if last_change is None
                    else max(last_change, vs.meaningfulConfTime)
                )
            if (
                vs.swingType == SWING_LOW
                and direction == DIR_BEARISH
                and weak_low_ix < 0
                and vs.pivotStartAbs > wl_bound
                and vs.stableKey not in broken_keys
            ):
                weak_low_ix = v_ix
                last_change = (
                    vs.meaningfulConfTime if last_change is None
                    else max(last_change, vs.meaningfulConfTime)
                )
            si += 1

        else:
            r = rels[rel_order[ri]]
            code, key = r[2], r[0]
            if code in _boot._HIGH_CODES:
                hi_label, hi_key = code, key
            else:
                lo_label, lo_key = code, key
            if direction == DIR_UNDETERMINED:
                if hi_label == _boot.C_HH and lo_label == _boot.C_HL:
                    direction = DIR_BULLISH
                    prot_low_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == lo_key
                    )
                    weak_high_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == hi_key
                    )
                elif hi_label == _boot.C_LH and lo_label == _boot.C_LL:
                    direction = DIR_BEARISH
                    prot_high_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == hi_key
                    )
                    weak_low_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == lo_key
                    )
                if direction != DIR_UNDETERMINED and last_change is None:
                    last_change = r[3]
            ri += 1

    def key_of(ix):
        return views[ix].stableKey if ix >= 0 else None

    result = _WalkResult()
    result.direction = direction
    result.protected_high = key_of(prot_high_ix)
    result.protected_low = key_of(prot_low_ix)
    result.weak_high = key_of(weak_high_ix)
    result.weak_low = key_of(weak_low_ix)
    result.transitions = events
    result.broken = list(broken_keys)
    result.weak_high_boundary = wh_bound
    result.weak_low_boundary = wl_bound
    result.aborted = aborted
    result.last_change = last_change
    return result


# ---------------------------------------------------------------------------
# Production projection
# ---------------------------------------------------------------------------

def _python_state(candles, swings):
    analysis = _analyze(candles, tuple(swings))
    state = analysis.current_state
    key_of = {s.record_id: s.pivot_end_time_utc for s in swings}

    def resolve(record_id):
        return key_of[record_id] if record_id is not None else None

    transitions = [
        (
            _TR_FROM_PYTHON[t.transition_type],
            resolve(t.broken_swing_id),
            t.broken_level_price,
            t.break_close_price,
            t.event_time_utc,
            t.availability_time_utc,
            resolve(t.protected_swing_id),
        )
        for t in analysis.structure_transitions
    ]
    return (
        _DIR_FROM_PYTHON[state.direction],
        resolve(state.active_protected_high_swing_id),
        resolve(state.active_protected_low_swing_id),
        resolve(state.active_weak_high_swing_id),
        resolve(state.active_weak_low_swing_id),
        transitions,
    ), analysis


def _assert_parity(candles, swings, force_no_replacement=False):
    """Full-state parity over the whole implemented walk.

    As of P2-I7 the model covers bootstrap, BOS, weak re-arm AND CHOCH, so there
    is no longer any fixture shape it has to be excluded from.
    """
    reference, analysis = _python_state(candles, swings)
    walk = _pine_walk(candles, swings, force_no_replacement)
    assert walk.state() == reference

    # `current_state.availability_time_utc` is the walk's last_change, falling
    # back to the final candle when nothing ever changed (analyzer.py:404-408).
    expected_availability = (
        walk.last_change if walk.last_change is not None
        else candles[-1].availability_time_utc
    )
    assert analysis.current_state.availability_time_utc == expected_availability
    return walk, analysis


def _assert_prefix_parity(candles, swings):
    seen = []
    for k in range(1, len(candles) + 1):
        prefix = candles[:k]
        watermark = prefix[-1].availability_time_utc
        visible = tuple(
            s for s in swings if s.meaningful_confirmation_time_utc <= watermark
        )
        walk, _ = _assert_parity(prefix, visible)
        seen.append(walk)
    return seen


def _build(specs, neutral, overrides=None):
    candles = _series(neutral, overrides)
    swings = tuple(
        _swing(i + 1, t, price, pivot, conf, candles)
        for i, (t, price, pivot, conf) in enumerate(specs)
    )
    return candles, swings


def _key(candles, pivot_bar):
    return candles[pivot_bar].event_time_utc


# Bootstrap shapes (as in I4): BULLISH protected_low=102 weak_high=112,
# BEARISH protected_high=108 weak_low=98.
_BULL = [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9)]
_BEAR = [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9)]
BULL_NEUTRAL, BEAR_NEUTRAL = "105", "103"
BREAK = 12


# ---------------------------------------------------------------------------
# Phase 18.1 / 18.2 — valid BOS, both directions
# ---------------------------------------------------------------------------

def test_bullish_bos_emits_and_updates_state() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 1
    code, broken, level, close, event, avail, protected = walk.transitions[0]
    assert code == 1                                     # BULLISH_BOS
    assert broken == _key(candles, 8)
    assert level == Decimal("112")
    assert close == Decimal("113")
    assert event == candles[BREAK].event_time_utc
    assert avail == candles[BREAK].availability_time_utc
    assert protected == _key(candles, 6)
    assert walk.direction == DIR_BULLISH
    assert analysis.structure_transitions[0].transition_type is (
        StructureTransitionType.BULLISH_BOS
    )


def test_bearish_bos_emits_and_updates_state() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "97"}})
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 1
    code, broken, level, close, _event, _avail, protected = walk.transitions[0]
    assert code == -1                                    # BEARISH_BOS
    assert broken == _key(candles, 8)
    assert level == Decimal("98")
    assert close == Decimal("97")
    assert protected == _key(candles, 6)
    assert walk.direction == DIR_BEARISH
    assert analysis.structure_transitions[0].transition_type is (
        StructureTransitionType.BEARISH_BOS
    )


# ---------------------------------------------------------------------------
# Phase 18.3 / 18.4 / 18.5 — non-breaks
# ---------------------------------------------------------------------------

def test_close_exactly_at_the_weak_level_is_not_a_break() -> None:
    """Strict `>`; equality is not a break."""
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "112"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []
    assert walk.weak_high == _key(candles, 8), "weak level survives"


def test_close_exactly_at_the_weak_low_is_not_a_break() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "98"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []
    assert walk.weak_low == _key(candles, 8)


def test_wick_through_with_close_back_inside_is_not_a_break() -> None:
    """Breaks are close-only: a high far beyond the level breaks nothing."""
    candles, swings = _build(
        _BULL, BULL_NEUTRAL, {BREAK: {"high": "130", "close": "106"}}
    )
    assert candles[BREAK].high > Decimal("112") > candles[BREAK].close
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []


def test_wick_through_low_with_close_back_inside_is_not_a_break() -> None:
    candles, swings = _build(
        _BEAR, BEAR_NEUTRAL, {BREAK: {"low": "80", "close": "104"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []


def test_open_through_the_level_with_a_failing_close_is_not_a_break() -> None:
    """Only the close is consulted — a gap open beyond the level is irrelevant."""
    candles, swings = _build(
        _BULL, BULL_NEUTRAL, {BREAK: {"open": "125", "high": "126", "close": "107"}}
    )
    assert candles[BREAK].open > Decimal("112")
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []


# ---------------------------------------------------------------------------
# Phase 18.6 — repeat suppression
# ---------------------------------------------------------------------------

def test_repeat_break_of_the_same_level_emits_one_transition() -> None:
    candles, swings = _build(
        _BULL, BULL_NEUTRAL,
        {BREAK: {"close": "113"}, BREAK + 2: {"close": "118"},
         BREAK + 4: {"close": "125"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert walk.weak_high is None
    assert walk.broken == [_key(candles, 8)]


def test_repeat_break_of_the_same_low_emits_one_transition() -> None:
    candles, swings = _build(
        _BEAR, BEAR_NEUTRAL,
        {BREAK: {"close": "97"}, BREAK + 2: {"close": "90"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert walk.weak_low is None


# ---------------------------------------------------------------------------
# Phase 18.7 / 18.8 / 18.14 — replacement selection
# ---------------------------------------------------------------------------

def test_replacement_selects_the_newest_eligible_low() -> None:
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11)], BULL_NEUTRAL, {BREAK: {"close": "113"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.protected_low == _key(candles, 10), "newest low wins"
    assert walk.transitions[0][6] == _key(candles, 10)


def test_replacement_selects_the_newest_eligible_high() -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11)], BEAR_NEUTRAL, {BREAK: {"close": "97"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.protected_high == _key(candles, 10)


def test_replacement_ignores_a_swing_not_yet_visible() -> None:
    """A low confirmed only after the break candle is not a candidate."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 20)], BULL_NEUTRAL, {BREAK: {"close": "113"}}
    )
    late = swings[-1]
    assert late.meaningful_confirmation_time_utc > (
        candles[BREAK].availability_time_utc
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.protected_low == _key(candles, 6), "must not use a future swing"


def test_the_broken_swing_is_recorded_and_never_becomes_protected() -> None:
    """The consumed weak swing enters the broken set and is excluded from every
    later replacement search."""
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "95", 12, 13)],
        BEAR_NEUTRAL,
        {14: {"close": "97"}, 18: {"close": "94"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.broken == [walk.transitions[0][1]]
    assert walk.protected_high not in set(walk.broken)


def test_a_second_same_direction_bos_requires_weak_re_arm() -> None:
    """Not an omission: after a BOS the weak side is cleared, and only a later
    SWING_VISIBLE past the boundary can re-arm it. That gate is P2-I6 / TD-B, so
    within I5 a second same-direction BOS is unreachable — and Python agrees,
    which is why parity still holds on this fixture.
    """
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "95", 12, 13)],
        BEAR_NEUTRAL,
        {14: {"close": "97"}, 18: {"close": "94"}},
    )
    walk, analysis = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert len(analysis.structure_transitions) == 1
    assert walk.weak_low is None, "cleared and not re-armed"
    assert candles[18].close < Decimal("95"), "a later close does clear the level"


# ---------------------------------------------------------------------------
# Phase 18.9 — defensive fallback
# ---------------------------------------------------------------------------

def test_defensive_fallback_matches_python_under_injection() -> None:
    """With the replacement search forced to report nothing, Pine and Python must
    still agree: the BOS emits and the pre-break protected level is retained.

    Discriminating — unpatched this fixture selects the bar-10 low.
    """
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11)], BULL_NEUTRAL, {BREAK: {"close": "113"}}
    )
    natural, _ = _assert_parity(candles, swings)
    assert natural.protected_low == _key(candles, 10)

    with _force_replacement_none():
        walk, _ = _assert_parity(candles, swings, force_no_replacement=True)

    assert len(walk.transitions) == 1
    assert walk.protected_low == _key(candles, 6), "fallback retains the old level"
    assert walk.transitions[0][6] == _key(candles, 6)
    assert walk.direction == DIR_BULLISH


def test_defensive_fallback_bearish_matches_python_under_injection() -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11)], BEAR_NEUTRAL, {BREAK: {"close": "97"}}
    )
    natural, _ = _assert_parity(candles, swings)
    assert natural.protected_high == _key(candles, 10)

    with _force_replacement_none():
        walk, _ = _assert_parity(candles, swings, force_no_replacement=True)

    assert walk.protected_high == _key(candles, 6)
    assert walk.direction == DIR_BEARISH


# ---------------------------------------------------------------------------
# Phase 18.10 / 18.11 — weak side and boundary
# ---------------------------------------------------------------------------

def test_bos_clears_only_its_own_weak_side() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high is None
    assert walk.weak_low is None, "BULLISH never arms a weak low"
    assert walk.protected_high is None
    assert walk.protected_low is not None


def test_bos_sets_the_boundary_to_the_break_candle_index() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high_boundary == BREAK
    assert walk.weak_low_boundary == -1, "the untouched side keeps its boundary"


def test_bearish_bos_sets_the_low_boundary(recwarn=None) -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "97"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_low_boundary == BREAK
    assert walk.weak_high_boundary == -1


def test_no_weak_re_arm_after_a_bos() -> None:
    """A later same-type swing past the boundary would re-arm the weak level in
    Python. I5 does not implement that gate — it is P2-I6 / TD-B — so the fixture
    is built so Python does not re-arm either, and parity still holds."""
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, analysis = _assert_parity(candles, swings)
    assert walk.weak_high is None
    assert analysis.current_state.active_weak_high_swing_id is None


# ---------------------------------------------------------------------------
# Phase 18.12 / 18.13 — timing
# ---------------------------------------------------------------------------

def test_transition_event_time_is_the_break_candle_open_time() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, analysis = _assert_parity(candles, swings)
    assert walk.transitions[0][4] == candles[BREAK].event_time_utc
    assert analysis.structure_transitions[0].event_time_utc == (
        candles[BREAK].event_time_utc
    )


def test_transition_availability_is_the_max_of_candle_and_broken_swing() -> None:
    """The operands genuinely differ — the broken weak high was confirmed well
    before the break candle — so the `max` is exercised, not trivially equal."""
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    broken = swings[3]
    walk, _ = _assert_parity(candles, swings)
    assert broken.availability_time_utc < candles[BREAK].availability_time_utc
    assert walk.transitions[0][5] == max(
        candles[BREAK].availability_time_utc, broken.availability_time_utc
    )


# ---------------------------------------------------------------------------
# Phase 18.15 — CHOCH PRECEDENCE (mandatory)
# ---------------------------------------------------------------------------
# A candle can satisfy the CHOCH and BOS predicates simultaneously whenever the
# protected level sits on the far side of the weak level. Python resolves it by
# emitting CHOCH and skipping BOS entirely; I5 must emit no BOS.
#
# The fixture below is geometrically extreme — a swing low above a swing high —
# which real OHLC would not produce between adjacent pivots, but `_validate_swings`
# accepts it and it isolates the precedence question exactly. The guard is not
# justified by this fixture's realism; it is justified by Python's control flow,
# which skips BOS on *every* CHOCH-predicate candle.

_PRECEDENCE_BULL = [
    (L, "200", 2, 3), (H, "50", 4, 5), (L, "210", 6, 7), (H, "60", 8, 9),
]
_PRECEDENCE_NEUTRAL = "100"          # 100 < 210 (CHOCH) AND 100 > 60 (BOS)


def test_the_precedence_fixture_really_satisfies_both_predicates() -> None:
    """Guard the guard: if only one predicate fired, the test would prove
    nothing about precedence."""
    candles, swings = _build(_PRECEDENCE_BULL, _PRECEDENCE_NEUTRAL)
    protected_low = Decimal("210")
    weak_high = Decimal("60")
    close = Decimal(_PRECEDENCE_NEUTRAL)
    assert close < protected_low, "CHOCH predicate must be true"
    assert close > weak_high, "BOS predicate must be true"
    analysis = _analyze(candles, swings)
    assert any(
        t.transition_type is StructureTransitionType.BEARISH_CHOCH
        for t in analysis.structure_transitions
    ), "Python must choose CHOCH here"


def test_choch_precedence_emits_choch_and_never_bos_bullish() -> None:
    candles, swings = _build(_PRECEDENCE_BULL, _PRECEDENCE_NEUTRAL)
    walk, analysis = _assert_parity(candles, swings)

    python_bos = [
        t for t in analysis.structure_transitions
        if t.transition_type.value.endswith("BOS")
    ]
    assert python_bos == [], "Python emits no BOS on a CHOCH candle"
    assert all(code in (2, -2) for code, *_ in walk.transitions), walk.transitions
    assert walk.transitions, "a real CHOCH must now be emitted"


_PRECEDENCE_BEAR = [
    (H, "60", 2, 3), (L, "210", 4, 5), (H, "50", 6, 7), (L, "200", 8, 9),
]
_PRECEDENCE_BEAR_NEUTRAL = "100"     # 100 > 50 (CHOCH) AND 100 < 200 (BOS)


def test_choch_precedence_emits_choch_and_never_bos_bearish() -> None:
    candles, swings = _build(_PRECEDENCE_BEAR, _PRECEDENCE_BEAR_NEUTRAL)
    walk, analysis = _assert_parity(candles, swings)

    assert any(
        t.transition_type is StructureTransitionType.BULLISH_CHOCH
        for t in analysis.structure_transitions
    )
    assert [
        t for t in analysis.structure_transitions
        if t.transition_type.value.endswith("BOS")
    ] == []
    assert all(code in (2, -2) for code, *_ in walk.transitions), walk.transitions


def test_without_choch_precedence_a_false_bos_would_be_emitted() -> None:
    """Guard the guard: prove precedence is load-bearing by running the same walk
    with the CHOCH branch removed entirely."""
    candles, swings = _build(_PRECEDENCE_BULL, _PRECEDENCE_NEUTRAL)
    unguarded = _pine_walk_without_choch_guard(candles, swings)
    assert unguarded.transitions, "expected a false BOS without precedence"
    assert unguarded.transitions[0][0] == 1, "a BULLISH_BOS that must not happen"
    real = _pine_walk(candles, swings).transitions
    assert real, "the real walk emits a CHOCH instead"
    assert all(code in (2, -2) for code, *_ in real)


def _pine_walk_without_choch_guard(candles, swings) -> _WalkResult:
    """The same walk with the CHOCH price guard removed. Exists ONLY to prove the
    guard changes the outcome; it is not a model of anything shipped."""
    import types

    source_globals = dict(globals())
    result = _pine_walk(candles, swings)          # warm the helpers
    del result, source_globals, types

    views = [_V(s) for s in swings]
    rels = _pine_rels(swings)
    rel_order = _pine_order_rels(rels)
    swing_order = _pine_order_swings(views)
    closes = [c.close for c in candles]
    avail_t = [c.availability_time_utc for c in candles]
    open_t = [c.event_time_utc for c in candles]

    direction = DIR_UNDETERMINED
    prot_high_ix = prot_low_ix = weak_high_ix = weak_low_ix = -1
    hi_label = lo_label = None
    hi_key = lo_key = None
    broken_keys: list = []
    vis_order: list[int] = []
    events: list[tuple] = []
    ci = si = ri = 0
    nc, ns, nr = len(closes), len(swing_order), len(rel_order)

    for _ in range(nc + ns + nr):
        pick, best_t = -1, None
        if ci < nc:
            pick, best_t = 0, avail_t[ci]
        if si < ns:
            sv = views[swing_order[si]]
            if pick < 0 or sv.meaningfulConfTime < best_t:
                pick, best_t = 1, sv.meaningfulConfTime
        if ri < nr:
            rr = rels[rel_order[ri]]
            if pick < 0 or rr[3] < best_t:
                pick, best_t = 2, rr[3]

        if pick == 0:
            bar_close = closes[ci]
            bos_high = (
                direction == DIR_BULLISH and weak_high_ix >= 0
                and bar_close > views[weak_high_ix].pivotPrice
            )
            bos_low = (
                direction == DIR_BEARISH and weak_low_ix >= 0
                and bar_close < views[weak_low_ix].pivotPrice
            )
            if bos_high or bos_low:
                broken_ix = weak_high_ix if bos_high else weak_low_ix
                broken = views[broken_ix]
                broken_keys.append(broken.stableKey)
                want = SWING_LOW if bos_high else SWING_HIGH
                repl_ix = _pine_most_recent_unbroken(
                    views, vis_order, want, broken_keys
                )
                existing = prot_low_ix if bos_high else prot_high_ix
                new_prot_ix = repl_ix if repl_ix >= 0 else existing
                events.append(
                    (
                        1 if bos_high else -1,
                        broken.stableKey,
                        broken.pivotPrice,
                        bar_close,
                        open_t[ci],
                        max(avail_t[ci], broken.meaningfulConfTime),
                        views[new_prot_ix].stableKey if new_prot_ix >= 0 else None,
                    )
                )
                if bos_high:
                    prot_low_ix, weak_high_ix = new_prot_ix, -1
                else:
                    prot_high_ix, weak_low_ix = new_prot_ix, -1
            ci += 1
        elif pick == 1:
            vis_order.append(swing_order[si])
            si += 1
        else:
            r = rels[rel_order[ri]]
            code, key = r[2], r[0]
            if code in _boot._HIGH_CODES:
                hi_label, hi_key = code, key
            else:
                lo_label, lo_key = code, key
            if direction == DIR_UNDETERMINED:
                if hi_label == _boot.C_HH and lo_label == _boot.C_HL:
                    direction = DIR_BULLISH
                    prot_low_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == lo_key
                    )
                    weak_high_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == hi_key
                    )
                elif hi_label == _boot.C_LH and lo_label == _boot.C_LL:
                    direction = DIR_BEARISH
                    prot_high_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == hi_key
                    )
                    weak_low_ix = next(
                        i for i, v in enumerate(views) if v.stableKey == lo_key
                    )
            ri += 1

    out = _WalkResult()
    out.direction = direction
    out.protected_high = views[prot_high_ix].stableKey if prot_high_ix >= 0 else None
    out.protected_low = views[prot_low_ix].stableKey if prot_low_ix >= 0 else None
    out.weak_high = views[weak_high_ix].stableKey if weak_high_ix >= 0 else None
    out.weak_low = views[weak_low_ix].stableKey if weak_low_ix >= 0 else None
    out.transitions = events
    out.broken = list(broken_keys)
    out.weak_high_boundary = -1
    out.weak_low_boundary = -1
    out.aborted = 0
    return out


# ---------------------------------------------------------------------------
# Phase 19 — prefix parity
# ---------------------------------------------------------------------------

_PREFIX_SCENARIOS = {
    "bull_bos": (_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}}),
    "bear_bos": (_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "97"}}),
    "bull_equality": (_BULL, BULL_NEUTRAL, {BREAK: {"close": "112"}}),
    "bull_wick": (_BULL, BULL_NEUTRAL, {BREAK: {"high": "130", "close": "106"}}),
    "bull_repeat": (
        _BULL, BULL_NEUTRAL,
        {BREAK: {"close": "113"}, BREAK + 2: {"close": "118"}},
    ),
    "bull_replacement": (
        _BULL + [(L, "104", 10, 11)], BULL_NEUTRAL, {BREAK: {"close": "113"}},
    ),
    "bear_two_breaks": (
        _BEAR + [(H, "106", 10, 11), (L, "95", 12, 13)],
        BEAR_NEUTRAL,
        {14: {"close": "97"}, 18: {"close": "94"}},
    ),
}


@pytest.mark.parametrize("name", sorted(_PREFIX_SCENARIOS))
def test_prefix_parity(name: str) -> None:
    specs, neutral, overrides = _PREFIX_SCENARIOS[name]
    candles, swings = _build(specs, neutral, overrides)
    _assert_prefix_parity(candles, swings)


def test_prefix_parity_observes_the_moment_of_the_break() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walks = _assert_prefix_parity(candles, swings)
    counts = [len(w.transitions) for w in walks]
    assert counts[0] == 0
    assert counts[-1] == 1
    assert 0 in counts[:-1]


@pytest.mark.parametrize("name", ["bull", "bear"])
def test_prefix_parity_on_choch_fixtures(name: str) -> None:
    """Full parity at every prefix, and no BOS anywhere on a CHOCH path."""
    specs, neutral = (
        (_PRECEDENCE_BULL, _PRECEDENCE_NEUTRAL) if name == "bull"
        else (_PRECEDENCE_BEAR, _PRECEDENCE_BEAR_NEUTRAL)
    )
    candles, swings = _build(specs, neutral)
    walks = _assert_prefix_parity(candles, swings)
    assert walks[-1].transitions, "fixture must actually reach a CHOCH"
    for walk in walks:
        assert all(code in (2, -2) for code, *_ in walk.transitions)


# ---------------------------------------------------------------------------
# Phase 20 — deterministic campaign
# ---------------------------------------------------------------------------

_CAMPAIGN = dict(_PREFIX_SCENARIOS)
_CAMPAIGN.update(
    {
        "bear_equality": (_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "98"}}),
        "bear_wick": (_BEAR, BEAR_NEUTRAL, {BREAK: {"low": "80", "close": "104"}}),
        "bull_gap_open": (
            _BULL, BULL_NEUTRAL,
            {BREAK: {"open": "125", "high": "126", "close": "107"}},
        ),
        "bear_replacement": (
            _BEAR + [(H, "106", 10, 11)], BEAR_NEUTRAL, {BREAK: {"close": "97"}},
        ),
        "bull_late_swing_not_visible": (
            _BULL + [(L, "104", 10, 20)], BULL_NEUTRAL, {BREAK: {"close": "113"}},
        ),
        "undetermined_never_breaks": (
            [(L, "100", 2, 3), (H, "110", 4, 5), (L, "98", 6, 7), (H, "112", 8, 9)],
            BULL_NEUTRAL,
            {BREAK: {"close": "125"}},
        ),
    }
)


@pytest.mark.parametrize("name", sorted(_CAMPAIGN))
def test_campaign_prefix_parity(name: str) -> None:
    specs, neutral, overrides = _CAMPAIGN[name]
    candles, swings = _build(specs, neutral, overrides)
    _assert_prefix_parity(candles, swings)


def test_campaign_totals() -> None:
    comparisons = 0
    bos_transitions = 0
    scenarios_with_bos = 0
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walks = _assert_prefix_parity(candles, swings)
        comparisons += len(walks)
        count = len(walks[-1].transitions)
        bos_transitions += count
        scenarios_with_bos += 1 if count else 0

    choch = 0
    for specs, neutral in (
        (_PRECEDENCE_BULL, _PRECEDENCE_NEUTRAL),
        (_PRECEDENCE_BEAR, _PRECEDENCE_BEAR_NEUTRAL),
    ):
        candles, swings = _build(specs, neutral)
        choch += len(_pine_walk(candles, swings).transitions)

    assert len(_CAMPAIGN) == 13
    assert comparisons == 13 * BAR_COUNT == 312
    assert bos_transitions == 7, bos_transitions
    assert scenarios_with_bos == 7, scenarios_with_bos
    assert choch >= 2, choch


def test_campaign_covers_both_directions_and_both_non_break_kinds() -> None:
    """Fails on degeneration — a campaign that lost a mode must not pass quietly."""
    codes = set()
    non_breaks = 0
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walk = _pine_walk(candles, swings)
        codes.update(t[0] for t in walk.transitions)
        if not walk.transitions:
            non_breaks += 1
    assert codes == {1, -1}, codes
    assert non_breaks >= 5, non_breaks
