"""TD-B — weak-level re-arm after a structural boundary.

The mechanism lives entirely in the `_EVENT_SWING_VISIBLE` branch of
`structure/transitions.py:323-353`. Each side has exactly FIVE conditions:

    swing.swing_type == SWING_HIGH                  # 1 type matches the weak side
    and direction == BULLISH                        # 2 direction matches
    and weak_high is None                           # 3 the slot is EMPTY
    and swing.pivot_bar_index > boundary_index      # 4 STRICT
    and swing.record_id not in broken_ids           # 5 not already consumed

and the bearish mirror. There is **no** price relation, **no** relationship
label, and **no** protected-side relation.

FOUR RESULTS THAT ARE NOT OBVIOUS FROM THE PHRASE "re-arm after boundary"
-------------------------------------------------------------------------

1. **First-after-boundary wins, NOT newest.** Condition 3 means the slot fills on
   the first qualifying swing and later ones are ignored. This is the *opposite*
   of protected replacement, where `_most_recent_unbroken` picks the newest.

2. **An armed weak level is never replaced.** A qualifying swing that becomes
   visible while the slot is still occupied is discarded, not remembered — so it
   cannot arm later once the slot empties. Its SWING_VISIBLE event has passed.

3. **Condition 5 is unreachable** — a second defensive branch of exactly the same
   kind as TD-A's protected fallback. Every id in `broken_ids` belongs to a swing
   that was previously weak or protected, both of which require prior visibility;
   SWING_VISIBLE fires once per swing. So a swing can never already be broken at
   its own SWING_VISIBLE. Proven below.

4. **CHOCH and BOS feed the SAME mechanism.** Both write the same two boundary
   variables (`:217`/`:251` for CHOCH, `:290`/`:320` for BOS) and the same generic
   re-arm code reads them. Boundaries are never reset — they only advance.

A structural consequence used throughout: a swing's confirmation bar is never
before its pivot bar, so a re-arming swing's SWING_VISIBLE always lands strictly
after the availability of the break that set its boundary. A re-arm can therefore
never tie with its own boundary-setting break.
"""

from __future__ import annotations

import importlib.util
import sys
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure import transitions as _transitions
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)

_SIB = importlib.util.spec_from_file_location(
    "_tdb_fixtures",
    Path(__file__).with_name("test_structure_transitions_contract.py"),
)
assert _SIB is not None and _SIB.loader is not None
_fx = importlib.util.module_from_spec(_SIB)
sys.modules[_SIB.name] = _fx
_SIB.loader.exec_module(_fx)

_TDA = importlib.util.spec_from_file_location(
    "_tdb_tda", Path(__file__).with_name("test_structure_bos_fallback_contract.py")
)
assert _TDA is not None and _TDA.loader is not None
_tda = importlib.util.module_from_spec(_TDA)
sys.modules[_TDA.name] = _tda
_TDA.loader.exec_module(_tda)

_series = _fx._series
_swing = _fx._swing
_analyze = _fx._analyze
BAR_COUNT = _fx.BAR_COUNT

H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW
SOURCE = (
    Path(_fx.__file__).parents[2]
    / "src" / "btmm_ai_scanner" / "structure" / "transitions.py"
).read_text(encoding="utf-8")


def _build(specs, neutral, overrides=None):
    candles = _series(neutral, overrides)
    swings = tuple(
        _swing(i + 1, t, price, pivot, conf, candles)
        for i, (t, price, pivot, conf) in enumerate(specs)
    )
    return candles, swings


def _state(candles, swings):
    analysis = _analyze(candles, tuple(swings))
    return analysis.current_state, analysis


def _by_pivot(swings, pivot_bar):
    return next(s for s in swings if s.pivot_bar_index == pivot_bar)


def _weak_high_timeline(candles, swings):
    """Weak-high identity at every candle prefix — the observable trace of arming,
    clearing and re-arming."""
    trace = []
    for k in range(1, len(candles) + 1):
        prefix = candles[:k]
        watermark = prefix[-1].availability_time_utc
        visible = tuple(
            s for s in swings if s.meaningful_confirmation_time_utc <= watermark
        )
        state, analysis = _state(prefix, visible)
        trace.append(
            (
                state.active_weak_high_swing_id,
                state.active_weak_low_swing_id,
                len(analysis.structure_transitions),
            )
        )
    return trace


# Bullish bootstrap: L 100 -> H 110 -> L 102 (HL) -> H 112 (HH)
#   => BULLISH, protected_low = L2 (102), weak_high = H2 (112)
_BULL = [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9)]
# Bearish bootstrap: H 110 -> L 100 -> H 108 (LH) -> L 98 (LL)
_BEAR = [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9)]
BULL_NEUTRAL, BEAR_NEUTRAL = "105", "103"


# ---------------------------------------------------------------------------
# Phase 5 — the exact predicate, pinned condition by condition
# ---------------------------------------------------------------------------

def test_re_arm_predicate_has_exactly_the_five_source_conditions() -> None:
    branch = SOURCE.split("elif kind == _EVENT_SWING_VISIBLE:")[1].split(
        "\n        else:"
    )[0]
    for condition in (
        "swing.swing_type == SwingType.SWING_HIGH",
        "direction == StructureDirection.BULLISH",
        "weak_high is None",
        "swing.pivot_bar_index > weak_high_boundary_index",
        "swing.record_id not in broken_ids",
        "swing.swing_type == SwingType.SWING_LOW",
        "direction == StructureDirection.BEARISH",
        "weak_low is None",
        "swing.pivot_bar_index > weak_low_boundary_index",
    ):
        assert condition in branch, condition
    # Nothing else gates it: no price, no label, no protected relation.
    for absent in ("pivot_price", "label", "protected_high", "protected_low",
                   "SwingRelationshipLabel"):
        assert absent not in branch, f"unexpected gate on {absent}"


def test_boundaries_are_written_by_both_choch_and_bos_and_never_reset() -> None:
    writes = [
        line.strip() for line in SOURCE.splitlines()
        if "boundary_index =" in line
    ]
    # two initialisers + two CHOCH writes + two BOS writes
    assert len(writes) == 6, writes
    assert writes[0].endswith("= -1") and writes[1].endswith("= -1")
    for write in writes[2:]:
        assert write.endswith("= candle_index_by_id[candle.record_id]"), write
    assert "boundary_index = -1" not in SOURCE.split("transitions: list")[1], (
        "boundaries must never be reset mid-walk"
    )


# ---------------------------------------------------------------------------
# Phase 7 / 14 — the core TD-B fixture: BOS -> re-arm -> BOS
# ---------------------------------------------------------------------------

_BULL_CYCLE = _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)]
_BULL_CYCLE_OVERRIDES = {10: {"close": "113"}, 20: {"close": "121"}}


def test_bullish_bos_re_arm_bos_cycle() -> None:
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES)
    state, analysis = _state(candles, swings)

    h2, h3 = _by_pivot(swings, 8), _by_pivot(swings, 12)
    l2, l3 = _by_pivot(swings, 6), _by_pivot(swings, 10)

    assert len(analysis.structure_transitions) == 2
    first, second = analysis.structure_transitions
    assert first.transition_type is StructureTransitionType.BULLISH_BOS
    assert second.transition_type is StructureTransitionType.BULLISH_BOS
    assert first.broken_swing_id == h2.record_id
    assert second.broken_swing_id == h3.record_id, "the RE-ARMED level breaks"
    assert first.protected_swing_id == l2.record_id
    assert second.protected_swing_id == l3.record_id, "newest unbroken low"

    assert state.direction is StructureDirection.BULLISH
    assert state.active_weak_high_swing_id is None, "cleared by BOS #2"
    assert state.latest_transition_id == second.record_id


def test_the_cycle_actually_passes_through_a_re_arm() -> None:
    """Guard the guard: two BOS transitions are only meaningful if the weak slot
    genuinely emptied and refilled in between."""
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES)
    h2, h3 = _by_pivot(swings, 8), _by_pivot(swings, 12)
    trace = [weak for weak, _low, _n in _weak_high_timeline(candles, swings)]

    distinct = [k for i, k in enumerate(trace) if i == 0 or k != trace[i - 1]]
    assert distinct == [None, h2.record_id, None, h3.record_id, None], distinct


def test_bearish_bos_re_arm_bos_cycle() -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "90", 12, 13)],
        BEAR_NEUTRAL,
        {10: {"close": "97"}, 20: {"close": "89"}},
    )
    state, analysis = _state(candles, swings)
    l2, l3 = _by_pivot(swings, 8), _by_pivot(swings, 12)
    h2, h3 = _by_pivot(swings, 6), _by_pivot(swings, 10)

    assert len(analysis.structure_transitions) == 2
    first, second = analysis.structure_transitions
    assert first.transition_type is StructureTransitionType.BEARISH_BOS
    assert second.transition_type is StructureTransitionType.BEARISH_BOS
    assert first.broken_swing_id == l2.record_id
    assert second.broken_swing_id == l3.record_id
    assert first.protected_swing_id == h2.record_id
    assert second.protected_swing_id == h3.record_id
    assert state.direction is StructureDirection.BEARISH


# ---------------------------------------------------------------------------
# Phase 6 — strict boundary
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("break_bar", "expect_re_arm"),
    [(11, True), (12, False)],
)
def test_boundary_is_strict_for_weak_high(break_bar: int, expect_re_arm: bool) -> None:
    """H3's pivot is bar 12. Breaking at bar 11 leaves 12 > 11 (re-arm); breaking
    at bar 12 leaves 12 > 12 false (no re-arm)."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL,
        {break_bar: {"close": "113"}},
    )
    state, analysis = _state(candles, swings)
    h3 = _by_pivot(swings, 12)
    assert len(analysis.structure_transitions) == 1
    if expect_re_arm:
        assert state.active_weak_high_swing_id == h3.record_id
    else:
        assert state.active_weak_high_swing_id is None


@pytest.mark.parametrize(
    ("break_bar", "expect_re_arm"),
    [(11, True), (12, False)],
)
def test_boundary_is_strict_for_weak_low(break_bar: int, expect_re_arm: bool) -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "90", 12, 13)],
        BEAR_NEUTRAL,
        {break_bar: {"close": "97"}},
    )
    state, analysis = _state(candles, swings)
    l3 = _by_pivot(swings, 12)
    assert len(analysis.structure_transitions) == 1
    assert (state.active_weak_low_swing_id == l3.record_id) is expect_re_arm


def test_a_pivot_before_the_boundary_never_re_arms() -> None:
    """H3 pivots at bar 12 but is only confirmed at bar 16, after a break at bar
    14. 12 > 14 is false, so it never arms even though it is visible and unbroken.
    """
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 16)],
        BULL_NEUTRAL,
        {14: {"close": "113"}},
    )
    h3 = _by_pivot(swings, 12)
    assert h3.meaningful_confirmation_time_utc > candles[14].availability_time_utc
    state, analysis = _state(candles, swings)
    assert len(analysis.structure_transitions) == 1
    assert state.active_weak_high_swing_id is None


# ---------------------------------------------------------------------------
# Phase 8 — no same-branch re-arm
# ---------------------------------------------------------------------------

def test_bos_does_not_assign_a_replacement_weak_level_in_its_own_handler() -> None:
    bos_block = SOURCE.split("if bos_candidate is not None:")[1].split(
        "elif kind == _EVENT_SWING_VISIBLE"
    )[0]
    assert "weak_high = None" in bos_block
    assert "weak_low = None" in bos_block
    assert "weak_high = swing" not in bos_block
    assert "weak_low = swing" not in bos_block


def test_re_arm_happens_strictly_later_than_the_break_that_cleared_it() -> None:
    """The two events are separated in time, not merely in code order."""
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES)
    h3 = _by_pivot(swings, 12)
    break_availability = candles[10].availability_time_utc
    assert h3.meaningful_confirmation_time_utc > break_availability

    trace = _weak_high_timeline(candles, swings)
    cleared = next(i for i, (w, _l, n) in enumerate(trace) if n == 1 and w is None)
    armed = next(
        i for i, (w, _l, _n) in enumerate(trace) if w == h3.record_id
    )
    assert armed > cleared, "there must be at least one prefix with an empty slot"


def test_a_re_arm_can_never_tie_with_its_own_boundary_setting_break() -> None:
    """Structural, not incidental: a swing's confirmation bar is never before its
    pivot bar, so a swing whose pivot is past the break bar is always confirmed
    after the break bar, hence made visible strictly later."""
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES)
    for swing in swings:
        pivot_availability = candles[swing.pivot_bar_index].availability_time_utc
        assert swing.meaningful_confirmation_time_utc >= pivot_availability


# ---------------------------------------------------------------------------
# Phase 9 — swing type filter
# ---------------------------------------------------------------------------

def test_a_low_beyond_the_boundary_does_not_arm_the_weak_high() -> None:
    candles, swings = _build(
        _BULL + [(L, "104", 11, 12), (H, "120", 13, 14)],
        BULL_NEUTRAL,
        {10: {"close": "113"}},
    )
    l3, h3 = _by_pivot(swings, 11), _by_pivot(swings, 13)
    assert l3.pivot_bar_index > 10, "the low IS beyond the boundary"

    trace = _weak_high_timeline(candles, swings)
    # After the low becomes visible but before the high does, the slot is empty.
    low_visible = candles.index(
        next(c for c in candles
             if c.availability_time_utc >= l3.meaningful_confirmation_time_utc)
    )
    high_visible = candles.index(
        next(c for c in candles
             if c.availability_time_utc >= h3.meaningful_confirmation_time_utc)
    )
    assert trace[low_visible][0] is None, "a LOW must not arm the weak HIGH"
    assert trace[high_visible][0] == h3.record_id


def test_a_high_beyond_the_boundary_does_not_arm_the_weak_low() -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 11, 12), (L, "90", 13, 14)],
        BEAR_NEUTRAL,
        {10: {"close": "97"}},
    )
    h3 = _by_pivot(swings, 11)
    state, _ = _state(candles[: 13], tuple(
        s for s in swings
        if s.meaningful_confirmation_time_utc <= candles[12].availability_time_utc
    ))
    assert h3.meaningful_confirmation_time_utc <= candles[12].availability_time_utc
    assert state.active_weak_low_swing_id is None, "a HIGH must not arm the weak LOW"


# ---------------------------------------------------------------------------
# Phase 11 / 12 — the slot must be EMPTY, and FIRST wins (not newest)
# ---------------------------------------------------------------------------

def test_an_armed_weak_level_is_never_replaced_by_a_later_swing() -> None:
    """H3 becomes visible while H2 is still armed, so it is discarded — and it
    does not arm later when the BOS finally empties the slot."""
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL,
        {20: {"close": "113"}},
    )
    h2, h3 = _by_pivot(swings, 8), _by_pivot(swings, 12)
    assert h3.meaningful_confirmation_time_utc < candles[20].availability_time_utc

    trace = _weak_high_timeline(candles, swings)
    assert trace[19][0] == h2.record_id, "still H2 while armed — H3 ignored"
    state, analysis = _state(candles, swings)
    assert analysis.structure_transitions[0].broken_swing_id == h2.record_id
    assert state.active_weak_high_swing_id is None, (
        "H3's SWING_VISIBLE has passed; it cannot arm retroactively"
    )


def test_the_first_qualifying_swing_wins_not_the_newest() -> None:
    """The opposite of protected replacement, which takes the NEWEST candidate.

    Two highs qualify after the boundary: H3 (bar 12, 120) and H4 (bar 16, 130).
    Condition 3 (`weak_high is None`) means H3 arms and H4 is ignored.
    """
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "106", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL,
        {10: {"close": "113"}},
    )
    h3, h4 = _by_pivot(swings, 12), _by_pivot(swings, 16)
    assert h4.pivot_bar_index > h3.pivot_bar_index > 10, "both qualify"

    state, analysis = _state(candles, swings)
    assert len(analysis.structure_transitions) == 1
    assert state.active_weak_high_swing_id == h3.record_id, "FIRST, not newest"
    assert state.active_weak_high_swing_id != h4.record_id


def test_protected_replacement_takes_the_newest_for_contrast() -> None:
    """The same fixture, showing the two selection rules genuinely differ:
    protected took the NEWEST low while weak took the FIRST high."""
    # L4 is priced BELOW neutral: once it becomes the protected low, a neutral
    # close above it must not trip the CHOCH predicate and add a transition.
    candles, swings = _build(
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "103", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL,
        {20: {"close": "113"}},
    )
    l4 = _by_pivot(swings, 14)
    state, analysis = _state(candles, swings)
    assert analysis.structure_transitions[0].protected_swing_id == l4.record_id
    assert state.active_protected_low_swing_id == l4.record_id


# ---------------------------------------------------------------------------
# Phase 10 — condition 5 (broken filter) is UNREACHABLE
# ---------------------------------------------------------------------------

def test_broken_ids_only_ever_receives_already_visible_swings() -> None:
    """Source half of the proof: every id added to `broken_ids` is the id of a
    swing that was serving as a protected or weak level, and both roles require
    the swing to have been made visible first."""
    adds = [ln.strip() for ln in SOURCE.splitlines() if "broken_ids.add" in ln]
    assert adds, "expected broken_ids writes"
    for add in adds:
        assert add == "broken_ids.add(broken_swing.record_id)", add
    # broken_swing only ever comes from a choch/bos candidate, which is built
    # from protected_high/protected_low/weak_high/weak_low.
    for source_line in ("choch_candidate = (True, protected_high)",
                        "choch_candidate = (False, protected_low)",
                        "bos_candidate = (True, weak_high)",
                        "bos_candidate = (False, weak_low)"):
        assert source_line in SOURCE, source_line


@pytest.mark.parametrize("seed", _tda._SEEDS)
def test_every_broken_swing_was_visible_before_it_was_broken(seed: int) -> None:
    """Empirical half: for every transition in a real walk, the broken swing's
    SWING_VISIBLE event strictly preceded the break. Since SWING_VISIBLE fires
    exactly once per swing, no swing can be in `broken_ids` at its own
    SWING_VISIBLE — so condition 5 can never be the deciding factor.
    """
    candles, swings = _tda._campaign_case(seed)
    analysis = _analyze(candles, swings)
    by_id = {s.record_id: s for s in swings}
    candle_by_id = {c.record_id: c for c in candles}
    for transition in analysis.structure_transitions:
        broken = by_id[transition.broken_swing_id]
        break_candle = candle_by_id[transition.break_candle_id]
        assert broken.meaningful_confirmation_time_utc <= (
            break_candle.availability_time_utc
        ), "a swing was broken before it was ever visible — TD-B assumption fails"


def test_condition_five_is_retained_defensively_like_the_td_a_fallback() -> None:
    """It is unreachable, but it is still in the source and Pine I6 must keep it
    (architecture doc 17.5a policy)."""
    branch = SOURCE.split("elif kind == _EVENT_SWING_VISIBLE:")[1]
    assert branch.count("swing.record_id not in broken_ids") == 2


# ---------------------------------------------------------------------------
# Phase 13 — boundary persistence
# ---------------------------------------------------------------------------

def test_the_boundary_advances_with_each_break_and_is_never_cleared() -> None:
    """Observable via the re-arm gate: after BOS #2 at bar 20, a high pivoting at
    bar 18 (before the new boundary) cannot arm, even though it would have
    qualified against the old boundary of 10."""
    candles, swings = _build(
        _BULL_CYCLE + [(L, "103", 14, 15), (H, "125", 18, 21)],
        BULL_NEUTRAL,
        _BULL_CYCLE_OVERRIDES,
    )
    h4 = _by_pivot(swings, 18)
    assert h4.meaningful_confirmation_time_utc > candles[20].availability_time_utc
    assert 10 < h4.pivot_bar_index < 20, "qualifies against the OLD boundary only"

    state, analysis = _state(candles, swings)
    assert len(analysis.structure_transitions) == 2
    assert state.active_weak_high_swing_id is None, "the boundary moved to 20"


# ---------------------------------------------------------------------------
# Phase 15 — CHOCH-origin re-arm
# ---------------------------------------------------------------------------

_CHOCH_CYCLE = _BEAR + [(H, "120", 12, 13)]
_CHOCH_OVERRIDES = {10: {"close": "109"}, 20: {"close": "121"}}


def test_choch_sets_the_boundary_and_a_later_swing_re_arms_through_it() -> None:
    candles, swings = _build(_CHOCH_CYCLE, BEAR_NEUTRAL, _CHOCH_OVERRIDES)
    state, analysis = _state(candles, swings)
    h2, h3 = _by_pivot(swings, 6), _by_pivot(swings, 12)

    assert len(analysis.structure_transitions) == 2
    choch, bos = analysis.structure_transitions
    assert choch.transition_type is StructureTransitionType.BULLISH_CHOCH
    assert choch.broken_swing_id == h2.record_id
    assert choch.direction_before is StructureDirection.BEARISH
    assert choch.direction_after is StructureDirection.BULLISH

    # The CHOCH cleared both weak levels and set the weak-HIGH boundary; H3
    # (pivot 12 > 10) then armed through it, and the BOS broke it.
    assert bos.transition_type is StructureTransitionType.BULLISH_BOS
    assert bos.broken_swing_id == h3.record_id
    assert state.direction is StructureDirection.BULLISH


def test_choch_origin_re_arm_uses_the_same_generic_mechanism() -> None:
    """There is exactly one re-arm site, and it is origin-agnostic: it reads the
    boundary variables without caring which transition kind last wrote them."""
    branch = SOURCE.split("elif kind == _EVENT_SWING_VISIBLE:")[1].split(
        "\n        else:"
    )[0]
    assert branch.count("weak_high = swing") == 1
    assert branch.count("weak_low = swing") == 1
    for origin_token in ("choch", "bos", "transition_type"):
        assert origin_token not in branch, (
            f"re-arm must not branch on transition origin ({origin_token})"
        )


def test_choch_clears_both_weak_levels() -> None:
    for half in SOURCE.split("if choch_candidate is not None:")[1].split(
        "if bos_candidate is not None:"
    )[0].split("else:"):
        if "_most_recent_unbroken" not in half:
            continue
        assert "weak_high = None" in half and "weak_low = None" in half


# ---------------------------------------------------------------------------
# Phase 17 — event ordering
# ---------------------------------------------------------------------------

def test_event_kind_order_is_candle_then_swing_then_relationship() -> None:
    assert _transitions._EVENT_CANDLE == 0
    assert _transitions._EVENT_SWING_VISIBLE == 1
    assert _transitions._EVENT_RELATIONSHIP == 2
    assert "events.sort(key=lambda event: (event[0], event[1], event[2]))" in SOURCE


@contextmanager
def _swing_visible_before_candle():
    """Reorder SWING_VISIBLE ahead of CANDLE. Used ONLY to prove the shipped
    ordering is load-bearing."""
    original = _transitions._EVENT_SWING_VISIBLE
    _transitions._EVENT_SWING_VISIBLE = -1
    try:
        yield
    finally:
        _transitions._EVENT_SWING_VISIBLE = original


# H3 pivots at bar 12 and confirms at bar 14, so its SWING_VISIBLE availability
# ties exactly with candle 14's. Correct order (CANDLE first) sees an empty weak
# slot at candle 14 and emits nothing, then arms H3. Swapped order arms H3 first
# and candle 14 immediately breaks it — a spurious second BOS.
_ORDER_FIXTURE = _BULL + [(L, "104", 10, 11), (H, "115", 12, 14)]
_ORDER_OVERRIDES = {10: {"close": "113"}, 14: {"close": "116"}}


def test_the_order_fixture_really_ties() -> None:
    candles, swings = _build(_ORDER_FIXTURE, BULL_NEUTRAL, _ORDER_OVERRIDES)
    h3 = _by_pivot(swings, 12)
    assert h3.meaningful_confirmation_time_utc == candles[14].availability_time_utc


def test_candle_is_processed_before_swing_visible() -> None:
    candles, swings = _build(_ORDER_FIXTURE, BULL_NEUTRAL, _ORDER_OVERRIDES)
    h3 = _by_pivot(swings, 12)
    state, analysis = _state(candles, swings)
    assert len(analysis.structure_transitions) == 1, "candle 14 must not break H3"
    assert state.active_weak_high_swing_id == h3.record_id


def test_swapping_the_order_would_produce_a_spurious_second_bos() -> None:
    """Guard the guard: the CANDLE < SWING_VISIBLE ordering is load-bearing."""
    candles, swings = _build(_ORDER_FIXTURE, BULL_NEUTRAL, _ORDER_OVERRIDES)
    with _swing_visible_before_candle():
        _state, swapped = _state_and_analysis(candles, swings)
    assert len(swapped.structure_transitions) == 2, (
        "expected the wrong ordering to break the newly armed level"
    )


def _state_and_analysis(candles, swings):
    analysis = _analyze(candles, tuple(swings))
    return analysis.current_state, analysis


# ---------------------------------------------------------------------------
# Phase 18 — bounded window
# ---------------------------------------------------------------------------

def test_re_arm_uses_only_the_supplied_swing_stream() -> None:
    """Drop the re-arming swing from the bounded input: the slot must stay empty,
    with no hidden candidate surviving outside the stream."""
    candles, swings = _build(_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES)
    h3 = _by_pivot(swings, 12)

    full, _ = _state(candles, swings)
    assert full.active_weak_high_swing_id is None      # broken by BOS #2

    without_h3 = tuple(s for s in swings if s.record_id != h3.record_id)
    trimmed, analysis = _state(candles, without_h3)
    assert len(analysis.structure_transitions) == 1, "no second BOS without H3"
    assert trimmed.active_weak_high_swing_id is None


# ---------------------------------------------------------------------------
# Phase 19 — batch / incremental replay
# ---------------------------------------------------------------------------

def _replay(candles, swings):
    comparisons = 0
    last = None
    for k in range(1, len(candles) + 1):
        prefix = candles[:k]
        visible = tuple(
            s for s in swings
            if s.meaningful_confirmation_time_utc <= prefix[-1].availability_time_utc
        )
        last = _analyze(prefix, visible)
        comparisons += 1
    return last, comparisons


_REPLAY_SCENARIOS = {
    "bull_cycle": (_BULL_CYCLE, BULL_NEUTRAL, _BULL_CYCLE_OVERRIDES),
    "bear_cycle": (
        _BEAR + [(H, "106", 10, 11), (L, "90", 12, 13)],
        BEAR_NEUTRAL,
        {10: {"close": "97"}, 20: {"close": "89"}},
    ),
    "choch_cycle": (_CHOCH_CYCLE, BEAR_NEUTRAL, _CHOCH_OVERRIDES),
    "boundary_equal": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL, {12: {"close": "113"}},
    ),
    "first_not_newest": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13),
                 (L, "106", 14, 15), (H, "130", 16, 17)],
        BULL_NEUTRAL, {10: {"close": "113"}},
    ),
    "armed_not_replaced": (
        _BULL + [(L, "104", 10, 11), (H, "120", 12, 13)],
        BULL_NEUTRAL, {20: {"close": "113"}},
    ),
    "event_order_tie": (_ORDER_FIXTURE, BULL_NEUTRAL, _ORDER_OVERRIDES),
}


@pytest.mark.parametrize("name", sorted(_REPLAY_SCENARIOS))
def test_batch_equals_incremental_replay(name: str) -> None:
    specs, neutral, overrides = _REPLAY_SCENARIOS[name]
    candles, swings = _build(specs, neutral, overrides)
    batch = _analyze(candles, tuple(swings))
    replayed, comparisons = _replay(candles, swings)

    assert comparisons == BAR_COUNT
    assert replayed.structure_transitions == batch.structure_transitions
    assert replayed.current_state == batch.current_state
    assert replayed.swing_relationships == batch.swing_relationships
    assert replayed.analyzed_swing_count == batch.analyzed_swing_count


# ---------------------------------------------------------------------------
# Phase 20 — deterministic campaign
# ---------------------------------------------------------------------------

def _count_re_arms(candles, swings) -> int:
    """A re-arm is a weak slot going empty -> occupied at a prefix where at least
    one transition has already fired (so it is not the bootstrap arming)."""
    re_arms = 0
    previous = (None, None, 0)
    for weak_high, weak_low, count in _weak_high_timeline(candles, swings):
        for index in (0, 1):
            before = previous[index]
            after = (weak_high, weak_low)[index]
            if before is None and after is not None and previous[2] > 0:
                re_arms += 1
        previous = (weak_high, weak_low, count)
    return re_arms


def test_campaign_totals() -> None:
    scenarios = 0
    comparisons = 0
    re_arms = 0
    bos = choch = 0
    second_bos = 0

    for specs, neutral, overrides in _REPLAY_SCENARIOS.values():
        candles, swings = _build(specs, neutral, overrides)
        analysis = _analyze(candles, tuple(swings))
        scenarios += 1
        comparisons += BAR_COUNT
        re_arms += _count_re_arms(candles, swings)
        kinds = [t.transition_type for t in analysis.structure_transitions]
        bos += sum(1 for k in kinds if k.value.endswith("BOS"))
        choch += sum(1 for k in kinds if k.value.endswith("CHOCH"))
        if sum(1 for k in kinds if k.value.endswith("BOS")) >= 2:
            second_bos += 1

    assert scenarios == 7
    assert comparisons == 7 * BAR_COUNT == 168
    assert re_arms == 5, re_arms
    assert bos == 9, bos
    assert choch == 1, choch
    assert second_bos == 2, second_bos


def test_the_campaign_actually_reaches_re_arm() -> None:
    """Fails on degeneration: a campaign that never re-arms proves nothing."""
    reached = 0
    for specs, neutral, overrides in _REPLAY_SCENARIOS.values():
        candles, swings = _build(specs, neutral, overrides)
        if _count_re_arms(candles, swings) > 0:
            reached += 1
    assert reached >= 4, reached
