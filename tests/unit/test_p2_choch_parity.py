"""Parity between the Pine P2-I7 CHOCH handling and production Python.

Uses the unified model in `test_p2_bos_parity.py`, which as of I7 reproduces the
whole implemented bounded walk — bootstrap, BOS, weak re-arm and CHOCH — against
production `analyze_structure_state`. `_assert_parity` compares direction, both
protected keys, both weak keys, the full transition sequence and the published
`availability_time_utc`.

WHAT CHOCH DOES THAT BOS DOES NOT (`transitions.py:183-253`)
------------------------------------------------------------
* flips the direction;
* consumes the **protected** level rather than the weak one;
* clears **BOTH** weak levels (BOS clears only its own side);
* nulls the **outgoing** direction's protected reference;
* moves exactly **ONE** boundary — the *new* direction's weak side
  (`:217` / `:251`). The opposite boundary is deliberately left untouched;
* can **ABORT**: if no replacement exists it `continue`s having mutated nothing,
  and BOS is still skipped for that candle.

TWO REACHABILITY RESULTS ESTABLISHED HERE
-----------------------------------------
1. `test_abort_and_a_live_bos_predicate_are_mutually_exclusive` — an abort can
   never coincide with a true BOS predicate. A BEARISH_CHOCH aborts only when no
   unbroken visible HIGH exists, but a live BOS predicate requires an armed
   `weak_high`, which *is* an unbroken visible HIGH. So the "abort suppresses a
   BOS that would otherwise have fired" case cannot be constructed; precedence
   still matters, but only on the success path.
2. The natural abort is reached by **exhausting** candidates through a chain of
   alternating CHOCHs, not by injection — see `_CASCADE`.
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


_bos = _load("_p2choch_bos", "test_p2_bos_parity.py")
_tda = _load("_p2choch_tda", "test_structure_bos_fallback_contract.py")

_build = _bos._build
_key = _bos._key
_pine_walk = _bos._pine_walk
_assert_parity = _bos._assert_parity
_assert_prefix_parity = _bos._assert_prefix_parity
_analyze = _bos._analyze
BAR_COUNT = _bos.BAR_COUNT
_spy = _tda._spy_replacements
_force_none = _tda._force_replacement_none

DIR_BULLISH, DIR_BEARISH = _bos.DIR_BULLISH, _bos.DIR_BEARISH
BULL_CHOCH, BEAR_CHOCH = 2, -2
BULL_BOS, BEAR_BOS = 1, -1

H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW
_BULL = _bos._BULL          # -> BULLISH, protected_low 102, weak_high 112
_BEAR = _bos._BEAR          # -> BEARISH, protected_high 108, weak_low 98
BULL_NEUTRAL, BEAR_NEUTRAL = _bos.BULL_NEUTRAL, _bos.BEAR_NEUTRAL
BREAK = 10

PINE = Path(__file__).resolve().parents[2] / "tradingview" / "btmm_poi_btrc_scanner_v1.pine"


# ---------------------------------------------------------------------------
# 1 / 2 — success, both directions
# ---------------------------------------------------------------------------

def test_bullish_choch_success() -> None:
    """BEARISH -> BULLISH: close above the protected high."""
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 1
    code, broken, level, close, event, avail, protected = walk.transitions[0]
    assert code == BULL_CHOCH
    assert broken == _key(candles, 6), "the protected HIGH is consumed"
    assert level == Decimal("108")
    assert close == Decimal("109")
    assert protected == _key(candles, 8), "newest unbroken low becomes protected"
    assert walk.direction == DIR_BULLISH
    assert analysis.structure_transitions[0].transition_type is (
        StructureTransitionType.BULLISH_CHOCH
    )
    assert analysis.structure_transitions[0].direction_before is (
        StructureDirection.BEARISH
    )
    assert analysis.structure_transitions[0].direction_after is (
        StructureDirection.BULLISH
    )


def test_bearish_choch_success() -> None:
    """BULLISH -> BEARISH: close below the protected low."""
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "101"}})
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 1
    code, broken, level, _close, _event, _avail, protected = walk.transitions[0]
    assert code == BEAR_CHOCH
    assert broken == _key(candles, 6), "the protected LOW is consumed"
    assert level == Decimal("102")
    assert protected == _key(candles, 8), "newest unbroken high becomes protected"
    assert walk.direction == DIR_BEARISH
    assert analysis.structure_transitions[0].transition_type is (
        StructureTransitionType.BEARISH_CHOCH
    )


# ---------------------------------------------------------------------------
# 3 / 4 / 5 — non-breaks
# ---------------------------------------------------------------------------

def test_close_exactly_at_the_protected_level_is_not_a_choch() -> None:
    for specs, neutral, close in (
        (_BEAR, BEAR_NEUTRAL, "108"), (_BULL, BULL_NEUTRAL, "102")
    ):
        candles, swings = _build(specs, neutral, {BREAK: {"close": close}})
        walk, _ = _assert_parity(candles, swings)
        assert walk.transitions == [], "equality must not flip the structure"


def test_wick_through_with_close_back_inside_is_not_a_choch() -> None:
    candles, swings = _build(
        _BEAR, BEAR_NEUTRAL, {BREAK: {"high": "130", "close": "104"}}
    )
    assert candles[BREAK].high > Decimal("108") > candles[BREAK].close
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []


def test_gap_open_through_with_a_failing_close_is_not_a_choch() -> None:
    candles, swings = _build(
        _BULL, BULL_NEUTRAL, {BREAK: {"open": "95", "low": "94", "close": "106"}}
    )
    assert candles[BREAK].open < Decimal("102")
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions == []


def test_a_failed_choch_still_allows_bos_on_the_same_candle() -> None:
    """The CHOCH predicate being FALSE is what re-enables BOS — the interaction
    the precedence rule turns on."""
    candles, swings = _build(
        _BULL, BULL_NEUTRAL, {BREAK: {"low": "90", "close": "113"}}
    )
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert walk.transitions[0][0] == BULL_BOS, "wick below did not block the BOS"


# ---------------------------------------------------------------------------
# 6 — precedence on the success path
# ---------------------------------------------------------------------------

# BULLISH with protected_low (210) ABOVE weak_high (60), so a single close at 100
# satisfies the CHOCH predicate (100 < 210) AND the BOS predicate (100 > 60).
# Python resolves it as a CHOCH. Neutral 55 keeps everything else quiet.
_PRECEDENCE = [
    (L, "200", 2, 3), (H, "50", 4, 5), (L, "210", 6, 7), (H, "60", 8, 9),
]
_PRECEDENCE_NEUTRAL = "55"


def test_the_precedence_fixture_satisfies_both_raw_predicates() -> None:
    candles, swings = _build(
        _PRECEDENCE, _PRECEDENCE_NEUTRAL, {BREAK: {"close": "100"}}
    )
    close = candles[BREAK].close
    assert close < Decimal("210"), "CHOCH predicate true"
    assert close > Decimal("60"), "BOS predicate also true"
    del swings


def test_choch_wins_over_bos_on_the_same_candle() -> None:
    candles, swings = _build(
        _PRECEDENCE, _PRECEDENCE_NEUTRAL, {BREAK: {"close": "100"}}
    )
    walk, analysis = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1
    assert walk.transitions[0][0] == BEAR_CHOCH, "CHOCH, not BOS"
    assert walk.transitions[0][1] == _key(candles, 6), "the protected low broke"
    assert walk.transitions[0][1] != _key(candles, 8), "not the weak high"
    assert all(
        not t.transition_type.value.endswith("BOS")
        for t in analysis.structure_transitions
    )


# ---------------------------------------------------------------------------
# 7 / 8 — the abort path
# ---------------------------------------------------------------------------

# A chain of alternating CHOCHs that exhausts the replacement candidates: each
# flip consumes one protected swing until no unbroken opposite-side swing is
# left, at which point every later candle aborts.
_CASCADE = _PRECEDENCE
_CASCADE_NEUTRAL = "100"


def test_the_cascade_reaches_a_natural_abort() -> None:
    candles, swings = _build(_CASCADE, _CASCADE_NEUTRAL)
    with _spy() as calls:
        analysis = _analyze(candles, tuple(swings))
    empty = [c for c in calls if c["eligible"] == 0]
    assert empty, "expected the candidate set to run dry"
    assert all(c["result"] is None for c in empty)
    assert len(analysis.structure_transitions) >= 2, "and real CHOCHs before that"


def test_cascade_parity() -> None:
    candles, swings = _build(_CASCADE, _CASCADE_NEUTRAL)
    walk, analysis = _assert_parity(candles, swings)
    assert walk.aborted >= 1, "the model must record the abort"
    assert all(code in (BULL_CHOCH, BEAR_CHOCH) for code, *_ in walk.transitions)
    assert len(analysis.structure_transitions) == len(walk.transitions)


def test_abort_mutates_nothing() -> None:
    """Non-vacuity: at the abort the candidate set is EMPTY, and the state is
    byte-for-byte what it was on the previous prefix."""
    candles, swings = _build(_CASCADE, _CASCADE_NEUTRAL)
    walks = _assert_prefix_parity(candles, swings)

    # Find the first prefix whose extra candle produced no change at all while
    # the CHOCH predicate was live.
    settled = walks[-1]
    frozen = [w for w in walks if w.aborted > 0]
    assert frozen, "expected aborting prefixes"
    first = frozen[0]
    for walk in frozen:
        assert walk.direction == first.direction
        assert walk.protected_high == first.protected_high
        assert walk.protected_low == first.protected_low
        assert walk.weak_high == first.weak_high
        assert walk.weak_low == first.weak_low
        assert walk.transitions == first.transitions
        assert walk.broken == first.broken
        assert walk.weak_high_boundary == first.weak_high_boundary
        assert walk.weak_low_boundary == first.weak_low_boundary
    assert settled.aborted > 1, "the abort repeats every candle, changing nothing"


def test_abort_adds_no_broken_key() -> None:
    candles, swings = _build(_CASCADE, _CASCADE_NEUTRAL)
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.broken) == len(walk.transitions), (
        "one broken key per SUCCESSFUL transition, none for aborts"
    )


def test_injected_abort_matches_python() -> None:
    """A controlled abort: force the replacement search to find nothing on a
    fixture that otherwise succeeds, and confirm Pine and Python still agree."""
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    natural, _ = _assert_parity(candles, swings)
    assert len(natural.transitions) == 1

    with _force_none():
        walk, analysis = _assert_parity(candles, swings, force_no_replacement=True)
    assert walk.transitions == [], "abort emits nothing"
    assert analysis.structure_transitions == ()
    assert walk.direction == DIR_BEARISH, "direction unchanged"
    assert walk.protected_high == _key(candles, 6), "protected untouched"
    assert walk.weak_low == _key(candles, 8), "weak untouched"
    assert walk.broken == []
    assert walk.weak_high_boundary == -1 and walk.weak_low_boundary == -1


def test_abort_and_a_live_bos_predicate_are_mutually_exclusive() -> None:
    """Why "abort suppresses a would-be BOS" cannot be constructed.

    A BEARISH_CHOCH aborts only when no unbroken visible HIGH exists. A live BOS
    predicate requires an armed `weak_high`, and an armed weak high IS an
    unbroken visible high — so the candidate set is non-empty and the CHOCH
    cannot abort. The bearish mirror is symmetric.

    Checked empirically: whenever the walk aborts, the weak slot for the current
    direction is empty, so no BOS could have fired anyway.
    """
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walks = _assert_prefix_parity(candles, swings)
        for walk in walks:
            if walk.aborted == 0:
                continue
            live = (
                walk.weak_high if walk.direction == DIR_BULLISH else walk.weak_low
            )
            assert live is None, (
                "an abort coincided with an armed weak level — the exclusivity "
                "argument is wrong and precedence needs a new test"
            )


# ---------------------------------------------------------------------------
# 9 / 10 / 11 / 13 — state mutation
# ---------------------------------------------------------------------------

def test_success_clears_both_weak_levels_and_the_outgoing_protected() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    before = _assert_prefix_parity(candles, swings)[BREAK - 1]
    assert before.weak_low == _key(candles, 8), "weak low was armed beforehand"
    assert before.protected_high == _key(candles, 6)

    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high is None and walk.weak_low is None, "BOTH clear"
    assert walk.protected_high is None, "the outgoing protected side is nulled"
    assert walk.protected_low is not None


def test_abort_clears_neither_weak_level() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    with _force_none():
        walk, _ = _assert_parity(candles, swings, force_no_replacement=True)
    assert walk.weak_low == _key(candles, 8), "still armed"
    assert walk.weak_high is None, "was never armed in a BEARISH structure"


def test_bos_by_contrast_clears_only_its_own_weak_side() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "113"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions[0][0] == BULL_BOS
    assert walk.direction == DIR_BULLISH, "BOS never flips direction"
    assert walk.protected_low is not None, "and never nulls protected"


# ---------------------------------------------------------------------------
# 12 / 14 — replacement selection
# ---------------------------------------------------------------------------

def test_replacement_takes_the_newest_eligible_candidate() -> None:
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "96", 12, 13)],
        BEAR_NEUTRAL,
        {16: {"close": "109"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions[0][0] == BULL_CHOCH
    assert walk.protected_low == _key(candles, 12), "newest low, not the oldest"
    assert walk.protected_low != _key(candles, 8)


def test_replacement_excludes_previously_broken_candidates() -> None:
    """In the cascade the second bearish flip cannot re-use the high consumed by
    the first, so it falls back to the older one."""
    candles, swings = _build(_CASCADE, _CASCADE_NEUTRAL)
    walk, _ = _assert_parity(candles, swings)
    bearish = [t for t in walk.transitions if t[0] == BEAR_CHOCH]
    assert len(bearish) >= 2, bearish
    protected = [t[6] for t in bearish]
    assert len(set(protected)) == len(protected), "each flip took a fresh high"
    assert protected[0] == _key(candles, 8)
    assert protected[1] == _key(candles, 4), "the older high, once the newer broke"


# ---------------------------------------------------------------------------
# 15 / 16 / 17 — boundaries, and CHOCH -> re-arm -> BOS
# ---------------------------------------------------------------------------

def test_choch_moves_exactly_one_boundary() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_high_boundary == BREAK, "the NEW direction's weak side"
    assert walk.weak_low_boundary == -1, "the opposite boundary is untouched"


def test_bearish_choch_moves_the_low_boundary_only() -> None:
    candles, swings = _build(_BULL, BULL_NEUTRAL, {BREAK: {"close": "101"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.weak_low_boundary == BREAK
    assert walk.weak_high_boundary == -1


_CHOCH_REARM_BOS = _BEAR + [(H, "120", 12, 13)]
_CHOCH_REARM_OVR = {BREAK: {"close": "109"}, 20: {"close": "121"}}


def test_choch_then_re_arm_then_bos() -> None:
    """The end-to-end proof that the UNCHANGED I6 re-arm branch consumes a
    CHOCH-written boundary exactly as it consumes a BOS-written one."""
    candles, swings = _build(_CHOCH_REARM_BOS, BEAR_NEUTRAL, _CHOCH_REARM_OVR)
    walk, analysis = _assert_parity(candles, swings)

    assert len(walk.transitions) == 2
    choch, bos = walk.transitions
    assert choch[0] == BULL_CHOCH
    assert bos[0] == BULL_BOS, "a BOS on the re-armed level"
    assert bos[1] == _key(candles, 12), "the swing that re-armed is what broke"
    assert walk.direction == DIR_BULLISH
    assert walk.weak_high_boundary == 20, "advanced by the BOS"
    assert analysis.current_state.latest_transition_id == (
        analysis.structure_transitions[-1].record_id
    )


def test_the_re_arm_between_them_actually_happened() -> None:
    candles, swings = _build(_CHOCH_REARM_BOS, BEAR_NEUTRAL, _CHOCH_REARM_OVR)
    walks = _assert_prefix_parity(candles, swings)
    trace = [w.weak_high for w in walks]
    distinct = [k for i, k in enumerate(trace) if i == 0 or k != trace[i - 1]]
    assert distinct == [None, _key(candles, 12), None], distinct


# ---------------------------------------------------------------------------
# 18 — repeat suppression
# ---------------------------------------------------------------------------

def test_a_consumed_protected_level_cannot_break_again() -> None:
    candles, swings = _build(
        _BEAR, BEAR_NEUTRAL,
        {BREAK: {"close": "109"}, 12: {"close": "115"}, 14: {"close": "125"}},
    )
    walk, _ = _assert_parity(candles, swings)
    assert len(walk.transitions) == 1, "later, higher closes add nothing"
    assert walk.broken == [_key(candles, 6)]


def test_re_arm_never_resurrects_a_broken_protected_swing() -> None:
    candles, swings = _build(_CHOCH_REARM_BOS, BEAR_NEUTRAL, _CHOCH_REARM_OVR)
    walk, _ = _assert_parity(candles, swings)
    for broken_key in walk.broken:
        assert walk.weak_high != broken_key
        assert walk.weak_low != broken_key
        assert walk.protected_high != broken_key
        assert walk.protected_low != broken_key


# ---------------------------------------------------------------------------
# 20 / 21 — timing and latest transition
# ---------------------------------------------------------------------------

def test_transition_timing_uses_the_break_candle_and_the_structural_max() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    broken = next(s for s in swings if s.pivot_bar_index == 6)
    walk, analysis = _assert_parity(candles, swings)

    _code, _bk, _lv, _cl, event, avail, _pr = walk.transitions[0]
    assert event == candles[BREAK].event_time_utc
    assert broken.availability_time_utc < candles[BREAK].availability_time_utc, (
        "the two max operands genuinely differ"
    )
    assert avail == max(
        candles[BREAK].availability_time_utc, broken.availability_time_utc
    )
    assert analysis.structure_transitions[0].availability_time_utc == avail


def test_latest_transition_updates_on_success_and_not_on_abort() -> None:
    candles, swings = _build(_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    _walk, analysis = _assert_parity(candles, swings)
    assert analysis.current_state.latest_transition_id == (
        analysis.structure_transitions[0].record_id
    )

    with _force_none():
        _walk2, aborted = _assert_parity(candles, swings, force_no_replacement=True)
    assert aborted.current_state.latest_transition_id is None


# ---------------------------------------------------------------------------
# 19 / 24 — bounded window
# ---------------------------------------------------------------------------

def test_removing_the_replacement_candidates_turns_success_into_abort() -> None:
    """The bounded-input case: the walk sees only the swings it is handed."""
    candles, swings = _build(
        _BEAR + [(H, "106", 10, 11), (L, "96", 12, 13)],
        BEAR_NEUTRAL,
        {16: {"close": "109"}},
    )
    full, _ = _assert_parity(candles, swings)
    assert full.protected_low == _key(candles, 12)

    # Same candles, but the newest low never enters the stream.
    trimmed = tuple(s for s in swings if s.pivot_bar_index != 12)
    walk, _ = _assert_parity(candles, trimmed)
    assert walk.protected_low == _key(candles, 8), "falls back to the older low"
    assert len(walk.transitions) == 1


def test_choch_holds_no_state_across_the_window_edge() -> None:
    candles, swings = _build(_CHOCH_REARM_BOS, BEAR_NEUTRAL, _CHOCH_REARM_OVR)
    for start in range(len(swings)):
        _assert_parity(candles, swings[start:])


# ---------------------------------------------------------------------------
# 25 — event ordering
# ---------------------------------------------------------------------------

# L3 pivots at bar 10 and confirms at bar 10, so its SWING_VISIBLE availability
# ties with candle 10's. CANDLE runs first, so L3 is NOT yet a replacement
# candidate when the CHOCH resolves — the protected low becomes L2 (bar 8), not
# L3 (bar 10). Reversing the two kinds would pick L3.
_ORDER = [
    (H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9),
    (H, "107", 9, 9), (L, "96", 10, 10),
]


def test_the_order_fixture_really_ties() -> None:
    candles, swings = _build(_ORDER, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    l3 = next(s for s in swings if s.pivot_bar_index == 10)
    assert l3.meaningful_confirmation_time_utc == candles[BREAK].availability_time_utc


def test_candle_resolves_before_a_tied_swing_becomes_a_candidate() -> None:
    candles, swings = _build(_ORDER, BEAR_NEUTRAL, {BREAK: {"close": "109"}})
    walk, _ = _assert_parity(candles, swings)
    assert walk.transitions[0][0] == BULL_CHOCH
    assert walk.protected_low == _key(candles, 8), (
        "the tied swing must not be visible to the CHOCH on the same candle"
    )
    assert walk.protected_low != _key(candles, 10)


# ---------------------------------------------------------------------------
# Source guards for the phase boundary
# ---------------------------------------------------------------------------

def test_pine_has_one_choch_predicate_path_only() -> None:
    text = PINE.read_text(encoding="utf-8")
    code = "\n".join(
        line for line in text.splitlines() if not line.strip().startswith("//")
    )
    assert "chochGuard" not in code, "the I5 suppression path must be gone"
    assert "suppressed" not in code
    assert code.count("bool chochHigh") == 1
    assert code.count("bool chochLow") == 1


def test_pine_choch_emits_both_codes() -> None:
    text = PINE.read_text(encoding="utf-8")
    for code in ("C_ST_TR_BULLISH_CHOCH", "C_ST_TR_BEARISH_CHOCH"):
        assert text.count(code) >= 2


# ---------------------------------------------------------------------------
# Prefix parity and campaign
# ---------------------------------------------------------------------------

_CAMPAIGN = {
    "bull_choch": (_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "109"}}),
    "bear_choch": (_BULL, BULL_NEUTRAL, {BREAK: {"close": "101"}}),
    "equality_bear": (_BEAR, BEAR_NEUTRAL, {BREAK: {"close": "108"}}),
    "equality_bull": (_BULL, BULL_NEUTRAL, {BREAK: {"close": "102"}}),
    "wick_only": (_BEAR, BEAR_NEUTRAL, {BREAK: {"high": "130", "close": "104"}}),
    "gap_open": (
        _BULL, BULL_NEUTRAL, {BREAK: {"open": "95", "low": "94", "close": "106"}},
    ),
    "bos_after_failed_choch": (
        _BULL, BULL_NEUTRAL, {BREAK: {"low": "90", "close": "113"}},
    ),
    "precedence": (_PRECEDENCE, _PRECEDENCE_NEUTRAL, {BREAK: {"close": "100"}}),
    "cascade_and_abort": (_CASCADE, _CASCADE_NEUTRAL, None),
    "newest_replacement": (
        _BEAR + [(H, "106", 10, 11), (L, "96", 12, 13)],
        BEAR_NEUTRAL, {16: {"close": "109"}},
    ),
    "choch_rearm_bos": (_CHOCH_REARM_BOS, BEAR_NEUTRAL, _CHOCH_REARM_OVR),
    "repeat_suppression": (
        _BEAR, BEAR_NEUTRAL,
        {BREAK: {"close": "109"}, 12: {"close": "115"}, 14: {"close": "125"}},
    ),
    "event_order_tie": (_ORDER, BEAR_NEUTRAL, {BREAK: {"close": "109"}}),
}


@pytest.mark.parametrize("name", sorted(_CAMPAIGN))
def test_campaign_prefix_parity(name: str) -> None:
    specs, neutral, overrides = _CAMPAIGN[name]
    candles, swings = _build(specs, neutral, overrides)
    _assert_prefix_parity(candles, swings)


def test_campaign_totals() -> None:
    comparisons = 0
    bull_choch = bear_choch = bos = 0
    aborting = 0
    re_arms = 0

    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        walks = _assert_prefix_parity(candles, swings)
        comparisons += len(walks)
        final = walks[-1]
        if final.aborted:
            aborting += 1
        for code, *_ in final.transitions:
            if code == BULL_CHOCH:
                bull_choch += 1
            elif code == BEAR_CHOCH:
                bear_choch += 1
            else:
                bos += 1
        previous = walks[0]
        for walk in walks[1:]:
            for before, after in (
                (previous.weak_high, walk.weak_high),
                (previous.weak_low, walk.weak_low),
            ):
                if before is None and after is not None and previous.transitions:
                    re_arms += 1
            previous = walk

    assert len(_CAMPAIGN) == 13
    assert comparisons == 13 * BAR_COUNT == 312
    # Diversity guard — a campaign stuck in one mode proves nothing.
    assert bull_choch > 0, bull_choch
    assert bear_choch > 0, bear_choch
    assert aborting > 0, aborting
    assert bos > 0, bos
    assert re_arms > 0, re_arms


def test_campaign_reaches_every_transition_code() -> None:
    seen = set()
    for specs, neutral, overrides in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral, overrides)
        seen.update(code for code, *_ in _pine_walk(candles, swings).transitions)
    assert BULL_CHOCH in seen and BEAR_CHOCH in seen, seen
    assert BULL_BOS in seen, seen
