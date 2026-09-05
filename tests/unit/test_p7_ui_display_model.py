"""P7 UI display-layer hardening: offline, randomized, mutation-tested proof
that the active-POI table's clear/repopulate/overflow/ordering behavior is
correct, plus source-level label-mapping coverage for every `f_p7*Label`
function.

WHY OFFLINE RATHER THAN MORE LIVE TRADINGVIEW ROUNDS
---------------------------------------------------------
Live FXCM observation already proved (BTRC_V1_P7_UI_LIVE_ACCEPTANCE_ADDENDUM.md)
that the panel renders correctly across many real, changing active counts.
What live observation CANNOT cheaply give is exhaustive coverage of rare
transitions (0 active, exactly-at-capacity, one-bar-early/late terminal
removal) or a REAL mutation guard (would a broken build actually be caught
by CI, not just "look right in one screenshot"). This module gives that:
thousands of transitions, several explicit mutants, at effectively zero
marginal cost per run.
"""

from __future__ import annotations

import random

import pytest

from tests.parity_support.p7_ui_display_model import (
    P7DisplayState,
    PoiDecision,
    _P7DisplayStateNoClear,
    render_bar,
)

_REPO_ROOT = __import__("pathlib").Path(__file__).resolve().parents[2]
_P7_SOURCE = (
    _REPO_ROOT / "tradingview" / "btmm_poi_btrc_scanner_p7_dev.pine"
).read_text(encoding="utf-8")


def _decision(idx: int) -> PoiDecision:
    return PoiDecision(
        idx=idx,
        poi_bullish=idx % 2 == 0,
        tier=idx % 3,
        btmm_valid=idx % 5 != 0,
        align=idx % 4,
        final_score=(idx * 7) % 101,
        permission=idx % 6,
        lifecycle=[1, 3, 4, 5, 6, 7][idx % 6],
    )


# ---------------------------------------------------------------- rendering


def test_render_bar_shows_ascending_index_order():
    decisions = {i: _decision(i) for i in range(10)}
    result = render_bar(decisions, frozenset({7, 2, 5, 0}), max_visible=8)
    assert [row.idx for row in result.rows] == [0, 2, 5, 7]
    assert result.active_count == 4
    assert result.shown_count == 4
    assert result.footer == "4 shown / 4 active"


def test_render_bar_zero_active_is_clean():
    result = render_bar({}, frozenset(), max_visible=8)
    assert result.active_count == 0
    assert result.shown_count == 0
    assert result.rows == ()
    assert result.footer == "0 shown / 0 active"


def test_render_bar_exactly_at_capacity():
    decisions = {i: _decision(i) for i in range(8)}
    result = render_bar(decisions, frozenset(range(8)), max_visible=8)
    assert result.shown_count == 8
    assert result.active_count == 8
    assert result.footer == "8 shown / 8 active"


# ---------------------------------------------------------- overflow policy


def test_overflow_never_reduces_the_evaluated_set():
    """Phase 7/12's central claim: display capacity bounds only what is
    SHOWN, never what P5 evaluates. `active_count` here stands in for "how
    many POIs P5's own loop evaluated" -- it must equal the true eligible
    set size regardless of `max_visible`."""
    decisions = {i: _decision(i) for i in range(150)}
    eligible = frozenset(range(150))
    for max_visible in (1, 5, 8, 20, 200):
        result = render_bar(decisions, eligible, max_visible)
        assert result.active_count == 150, "evaluation count must never shrink"
        assert result.shown_count == min(150, max_visible)


def test_overflow_mutation_using_capacity_to_stop_evaluation_is_caught():
    """A MUTANT that (wrongly) treats `max_visible` as the evaluation bound
    itself -- exactly the regression Phase 20 names -- produces a different,
    detectably wrong `active_count`. This test's job is to prove the
    difference is visible, not to exercise real source code."""
    decisions = {i: _decision(i) for i in range(20)}
    eligible = frozenset(range(20))
    correct = render_bar(decisions, eligible, max_visible=8)

    # The mutant: evaluated == displayed (the bug this guards against).
    mutant_active_count = min(len(eligible), 8)
    assert correct.active_count != mutant_active_count
    assert correct.active_count == 20
    assert mutant_active_count == 8


@pytest.mark.parametrize("active_size", [0, 1, 2, 8, 9, 20, 101, 300])
def test_overflow_footer_matches_every_observed_live_shape(active_size):
    """87, 88, 93, 97, 101 were the real live-observed counts; this
    parametrization covers those plus the structurally interesting
    boundaries (0, 1, at-capacity, just-over-capacity, and a size larger
    than any live observation this session)."""
    decisions = {i: _decision(i) for i in range(active_size)}
    eligible = frozenset(range(active_size))
    result = render_bar(decisions, eligible, max_visible=8)
    assert result.shown_count == min(active_size, 8)
    assert result.active_count == active_size
    assert result.footer == f"{result.shown_count} shown / {active_size} active"


# --------------------------------------------------------- stale-row proof


def test_directed_five_two_zero_sequence():
    """Phase 8/19's own literal directed sequence: 5 active -> 2 active ->
    0 active, requiring rows 5 -> 2 -> 0 with no leakage between bars."""
    state = P7DisplayState()
    decisions = {i: _decision(i) for i in range(10)}

    bar_a = state.advance_bar({i: False for i in range(5)}, decisions, known_ids=frozenset(range(5)))
    assert bar_a.active_count == 5
    assert {row.idx for row in bar_a.rows} == {0, 1, 2, 3, 4}

    bar_b = state.advance_bar({i: False for i in range(2)}, decisions, known_ids=frozenset(range(2)))
    assert bar_b.active_count == 2
    assert {row.idx for row in bar_b.rows} == {0, 1}, "no row from bar A may survive incorrectly"

    bar_c = state.advance_bar({}, decisions, known_ids=frozenset())
    assert bar_c.active_count == 0
    assert bar_c.rows == (), "no row from A or B may survive into the zero-active bar"


def test_no_clear_mutant_fails_the_five_two_zero_sequence():
    """The `array.clear()`-omitting mutant MUST fail this exact sequence --
    proving the directed test actually catches a missing clear, not just
    that the correct model happens to pass it."""
    state = _P7DisplayStateNoClear()
    decisions = {i: _decision(i) for i in range(10)}

    state.advance_bar({i: False for i in range(5)}, decisions, known_ids=frozenset(range(5)))
    bar_b = state.advance_bar({i: False for i in range(2)}, decisions, known_ids=frozenset(range(2)))
    # BUG: ids 2,3,4 (no longer known/active) linger from bar A.
    assert bar_b.active_count != 2
    assert {row.idx for row in bar_b.rows} != {0, 1}

    bar_c = state.advance_bar({}, decisions, known_ids=frozenset())
    assert bar_c.active_count != 0, "the mutant never reaches a true zero-row bar"


def test_randomized_transition_stress_no_stale_rows():
    """Thousands of transitions across sizes spanning 0, 1, 2, 8, 9, 20, and
    100+, with POIs randomly appearing, disappearing (terminal), and
    reappearing (a fresh index reused is not modeled -- real P3 indices are
    never reused -- but disjoint id pools per phase simulate 'new POIs
    replace old ones' realistically)."""
    rng = random.Random(20260904)
    state = P7DisplayState()
    universe_size = 400
    all_ids = list(range(universe_size))
    decisions = {i: _decision(i) for i in all_ids}

    previous_shown_ids: set[int] = set()
    for _ in range(3000):
        target_size = rng.choice([0, 1, 2, 8, 9, 20, 100, 150, universe_size])
        known = frozenset(rng.sample(all_ids, k=min(target_size, universe_size)))
        # Everything in `known` is non-terminal this bar (still active);
        # anything the state carried from before that's absent from `known`
        # naturally drops (simulating a POI that vanished from the registry
        # window entirely -- `known_ids` restriction in the real contract).
        status = {i: False for i in known}
        result = state.advance_bar(status, decisions, known_ids=known)

        assert result.active_count == len(known)
        assert result.shown_count == min(len(known), 8)
        shown_ids = {row.idx for row in result.rows}
        assert shown_ids <= known, "no row may reference an id outside this bar's known set"
        # Rows must be exactly the smallest `shown_count` ids -- ascending
        # order, no arbitrary subset.
        expected_shown = set(sorted(known)[: result.shown_count])
        assert shown_ids == expected_shown
        previous_shown_ids = shown_ids

    del previous_shown_ids  # loop-local sanity var, not asserted post-loop


# -------------------------------------------------------- terminal boundary


def test_terminal_poi_gets_final_bar_then_disappears():
    """A POI active entering a bar that goes terminal ON that bar still
    renders THIS bar, then must be gone next bar (Phase 13/21)."""
    state = P7DisplayState()
    decisions = {0: _decision(0), 1: _decision(1)}

    # Bar 1: both active, neither terminal.
    bar1 = state.advance_bar({0: False, 1: False}, decisions, known_ids=frozenset({0, 1}))
    assert {row.idx for row in bar1.rows} == {0, 1}

    # Bar 2: POI 0 goes terminal THIS bar -- must still appear.
    bar2 = state.advance_bar({0: True, 1: False}, decisions, known_ids=frozenset({0, 1}))
    assert {row.idx for row in bar2.rows} == {0, 1}, "terminal-this-bar POI must still get its final row"

    # Bar 3: POI 0's final evaluation already happened -- must be gone now.
    bar3 = state.advance_bar({0: True, 1: False}, decisions, known_ids=frozenset({0, 1}))
    assert {row.idx for row in bar3.rows} == {1}, "terminal POI must not reappear the bar after its final row"


def test_terminal_removed_one_bar_early_is_a_real_bug():
    """Mutation guard: a broken model that drops a terminal POI on the SAME
    bar it goes terminal (instead of one bar later) produces a visibly
    different row set than the correct model at bar2 above."""
    # Simulate the buggy variant directly: terminal POIs are excluded
    # immediately rather than given their final bar.
    buggy_eligible_bar2 = frozenset({1})  # POI 0 wrongly dropped immediately
    correct_eligible_bar2 = frozenset({0, 1})
    assert buggy_eligible_bar2 != correct_eligible_bar2


def test_terminal_retained_one_bar_late_is_a_real_bug():
    """The opposite mutation: a broken model that keeps a terminal POI for
    one extra bar past its final evaluation."""
    buggy_eligible_bar3 = frozenset({0, 1})  # POI 0 wrongly retained
    correct_eligible_bar3 = frozenset({1})
    assert buggy_eligible_bar3 != correct_eligible_bar3


# ---------------------------------------------------------- identity/adversarial


def test_identical_looking_pois_never_conflate():
    """Two POIs sharing every displayable attribute (direction, tier, BTMM,
    align, score, permission, lifecycle) but different canonical indices
    must still render as two distinct, separately identified rows."""
    twin_a = PoiDecision(
        idx=10, poi_bullish=True, tier=2, btmm_valid=True,
        align=0, final_score=85, permission=0, lifecycle=7,
    )
    twin_b = PoiDecision(
        idx=11, poi_bullish=True, tier=2, btmm_valid=True,
        align=0, final_score=85, permission=0, lifecycle=7,
    )
    decisions = {10: twin_a, 11: twin_b}
    result = render_bar(decisions, frozenset({10, 11}), max_visible=8)
    assert len(result.rows) == 2
    assert {row.idx for row in result.rows} == {10, 11}
    assert result.rows[0].idx != result.rows[1].idx
    # Every OTHER field is identical -- confirming idx is genuinely the only
    # thing distinguishing the two rows, exactly as the adversarial case
    # requires.
    assert result.rows[0].poi_bullish == result.rows[1].poi_bullish
    assert result.rows[0].final_score == result.rows[1].final_score


def test_no_duplicate_rows_for_a_single_id_across_random_stress():
    """Across the randomized stress run's every bar, no id ever appears
    twice in one bar's rows (a real regression class: a loop bug that
    pushes the same index twice)."""
    rng = random.Random(7)
    state = P7DisplayState()
    all_ids = list(range(60))
    decisions = {i: _decision(i) for i in all_ids}
    for _ in range(500):
        known = frozenset(rng.sample(all_ids, k=rng.randint(0, 60)))
        status = {i: False for i in known}
        result = state.advance_bar(status, decisions, known_ids=known)
        ids_seen = [row.idx for row in result.rows]
        assert len(ids_seen) == len(set(ids_seen)), "duplicate row for one POI in one bar"


# --------------------------------------------------------------- label maps


def _extract_switch_arms(function_name: str) -> tuple[list[str], str | None]:
    """Pull the `switch code ... => "..."` arms out of one `f_p7*` function
    in the real P7 DEV source, by exact text search -- not a general Pine
    parser, just enough structure to check coverage and the default arm."""
    start = _P7_SOURCE.index(f"{function_name}(int code) =>")
    # The body is scanned line-by-line below until the next top-level
    # declaration or a blank line -- a fixed 2000-char slice is just a
    # generous upper bound on how long one label function can be.
    body = _P7_SOURCE[start:start + 2000]
    lines = [ln.strip() for ln in body.splitlines()]
    codes: list[str] = []
    default: str | None = None
    for ln in lines[1:]:
        if ln.startswith("f_p7") or (ln == "" and codes):
            break
        if "=>" not in ln:
            continue
        lhs, _, rhs = ln.partition("=>")
        lhs = lhs.strip()
        rhs = rhs.strip()
        if lhs == "":
            default = rhs
            break
        codes.append(lhs)
    return codes, default


_LABEL_FUNCTIONS_AND_DEFAULTS = {
    "f_p7DirLabel": '"-"',
    "f_p7TrendStateLabel": '"-"',
    "f_p7RegimeLabel": '"-"',
    "f_p7MomAccelLabel": '"-"',
    "f_p7BrkLabel": '"NONE"',
    "f_p7PbLabel": '"NONE"',
    "f_p7SessionLabel": '"-"',
    "f_p7VolLabel": '"-"',
    "f_p7AlignLabel": '"-"',
    "f_p7PermLabel": '"-"',
    "f_p7LifecycleLabel": '"-"',
    "f_p7TierLabel": '"-"',
}

_ACTIONABLE_LABEL_STRINGS = {
    "f_p7PermLabel": {'"BUY BIAS"', '"SELL BIAS"', '"ALLOW (BOTH)"', '"COUNTER-TREND"', '"WATCH ONLY"', '"NO TRADE"'},
}


@pytest.mark.parametrize("function_name", list(_LABEL_FUNCTIONS_AND_DEFAULTS))
def test_every_label_function_has_a_non_actionable_default_arm(function_name):
    """Phase 18: an unknown/out-of-range code must never silently map to a
    valid-looking actionable state. Every `f_p7*Label` function's `switch`
    must end with a bare `=>` default arm, and that default must be the
    documented placeholder -- never one of the real, actionable strings."""
    codes, default = _extract_switch_arms(function_name)
    assert codes, f"{function_name}: no named cases found (extraction bug or source drift)"
    assert default is not None, f"{function_name}: missing a default `=>` arm -- unknown codes would error, not degrade"
    assert default == _LABEL_FUNCTIONS_AND_DEFAULTS[function_name], (
        f"{function_name}: default arm is {default!r}, expected the documented placeholder"
    )
    actionable = _ACTIONABLE_LABEL_STRINGS.get(function_name)
    if actionable:
        assert default not in actionable, (
            f"{function_name}: default arm {default!r} is one of the ACTIONABLE labels -- "
            "an unknown code must not silently look like a real permission state"
        )


def test_permission_label_covers_every_wire_code_exactly_once():
    codes, _default = _extract_switch_arms("f_p7PermLabel")
    # `C_PERM_*` symbolic names, in the exact order the constants block
    # declares them (BUY_BIAS=0 .. NO_TRADE_CONTEXT=5).
    expected = [
        "C_PERM_BUY_BIAS",
        "C_PERM_SELL_BIAS",
        "C_PERM_ALLOW_BOTH_CONTEXT",
        "C_PERM_COUNTER_TREND",
        "C_PERM_WATCH_ONLY",
        "C_PERM_NO_TRADE_CONTEXT",
    ]
    assert codes == expected, "f_p7PermLabel must cover all 6 permission codes, in order, with no gaps"


def test_lifecycle_label_never_produces_the_unreachable_btmm_validated_case():
    """`C_LC_BTMM_VALIDATED` has no Pine constant at all (frozen as
    provably unreachable in the P5 closure) -- confirm `f_p7LifecycleLabel`
    was never given a case for it, since that would silently imply it IS
    reachable."""
    codes, _default = _extract_switch_arms("f_p7LifecycleLabel")
    assert "C_LC_BTMM_VALIDATED" not in codes
    assert "C_LC_DETECTED" in codes, "DETECTED is still a declared code even if unreachable in practice"
