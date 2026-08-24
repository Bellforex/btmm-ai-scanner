"""TD-A — the BOS protected-fallback branch in `structure/transitions.py`.

The branch under investigation is the `else` half of:

    new_protected_low = (
        replacement_protected_low
        if replacement_protected_low is not None
        else protected_low            # <-- TD-A: the FALLBACK
    )

and its bearish mirror (`transitions.py:262-270` / `:292-300`).

WHAT THIS FILE ESTABLISHES
--------------------------

1. **The fallback is unreachable through the public API** for any input that
   `_validate_swings` accepts. The reason is a specific ordering detail in the
   CHOCH handler, pinned by `test_choch_abort_precedes_broken_ids_add`:

   * `protected_low` enters `broken_ids` ONLY as a CHOCH `broken_swing`, and that
     CHOCH simultaneously flips the direction to BEARISH and sets
     `protected_low = None` (`:246-248`);
   * when a CHOCH *aborts*, it `continue`s **before** `broken_ids.add`
     (`:189-191` / `:223-225`), so an aborted CHOCH leaves `protected_low`
     unbroken;
   * a BULLISH BOS adds only the broken *high* to `broken_ids` (`:260`);
   * bootstrap assigns `protected_low` while `broken_ids` is still empty, because
     `broken_ids` can only gain entries once a direction exists.

   Therefore **while `direction == BULLISH`, `protected_low` is always visible and
   always unbroken**, so `_most_recent_unbroken(lows, broken_ids)` always has at
   least that one candidate and cannot return `None`. The bearish side is the
   exact mirror. The invariant is asserted empirically over a campaign in
   `test_campaign_never_reaches_the_fallback`.

2. **The fallback's semantics are pinned anyway**, by injecting a `None` return
   at the replacement call (`test_injected_replacement_none_*`). That is a
   deliberate coupling to a private helper, justified because public state cannot
   reach the branch: without it, P2-I5 would have no executable target for the
   defensive path. These tests make no reachability claim.

3. Everything P2-I5 needs *around* the fallback is pinned from reachable state:
   replacement selection and its ordering, weak-side mutation, the boundary
   update, transition field values and timing, and repeat suppression.

A test that merely observes an unchanged protected id after a BOS proves nothing —
`test_unchanged_protected_id_does_not_imply_fallback` exists to demonstrate that
exact trap and is why every assertion here also checks the eligible-candidate set.
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
    "_tda_fixtures",
    Path(__file__).with_name("test_structure_transitions_contract.py"),
)
assert _SIB is not None and _SIB.loader is not None
_fx = importlib.util.module_from_spec(_SIB)
sys.modules[_SIB.name] = _fx
_SIB.loader.exec_module(_fx)

_series = _fx._series
_swing = _fx._swing
_analyze = _fx._analyze
BAR_COUNT = _fx.BAR_COUNT

H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW


# ---------------------------------------------------------------------------
# Instrumentation
# ---------------------------------------------------------------------------

@contextmanager
def _spy_replacements():
    """Record every `_most_recent_unbroken` call the walk makes.

    `eligible` is the size of the candidate set the production helper itself
    computes, so `eligible == 0` is exactly the condition that returns None and
    would take the CHOCH abort or the BOS fallback.
    """
    calls: list[dict] = []
    real = _transitions._most_recent_unbroken

    def spy(visible, broken_ids):
        eligible = [s for s in visible if s.record_id not in broken_ids]
        result = real(visible, broken_ids)
        calls.append(
            {
                "visible": len(visible),
                "eligible": len(eligible),
                "eligible_ids": {s.record_id for s in eligible},
                "result": result,
            }
        )
        return result

    _transitions._most_recent_unbroken = spy
    try:
        yield calls
    finally:
        _transitions._most_recent_unbroken = real


@contextmanager
def _force_replacement_none():
    """Force the replacement search to report 'no candidate'.

    Used ONLY to execute the defensive fallback expression so its semantics can
    be pinned for P2-I5. Makes no claim that production can reach it.
    """
    real = _transitions._most_recent_unbroken

    def always_none(_visible, _broken_ids):
        return None

    _transitions._most_recent_unbroken = always_none
    try:
        yield
    finally:
        _transitions._most_recent_unbroken = real


def _build(specs, neutral: str, overrides=None):
    """specs: [(swing_type, price, pivot_bar, conf_bar)] in source chronology."""
    candles = _series(neutral, overrides)
    swings = tuple(
        _swing(i + 1, swing_type, price, pivot_bar, conf_bar, candles)
        for i, (swing_type, price, pivot_bar, conf_bar) in enumerate(specs)
    )
    return candles, swings


def _swing_by_pivot(swings, pivot_bar):
    return next(s for s in swings if s.pivot_bar_index == pivot_bar)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
# Bootstrap shape: L1 100 -> H1 110 -> L2 102 (HL) -> H2 112 (HH)
#   => BULLISH, protected_low = L2 (102), weak_high = H2 (112)
# Neutral 105 sits strictly inside (102, 112), so nothing breaks unprompted.

_BOOT = [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9)]
NEUTRAL = "105"
BREAK_BAR = 12
BREAK_CLOSE = "113"


def _bos_with_newer_low():
    """A BULLISH BOS where a strictly newer eligible low exists (L3, bar 10)."""
    return _build(
        _BOOT + [(L, "104", 10, 11)],
        NEUTRAL,
        {BREAK_BAR: {"close": BREAK_CLOSE}},
    )


def _bos_without_newer_low():
    """The same BOS with no low newer than the protected one."""
    return _build(_BOOT, NEUTRAL, {BREAK_BAR: {"close": BREAK_CLOSE}})


# ---------------------------------------------------------------------------
# The reachability question
# ---------------------------------------------------------------------------

def test_choch_abort_precedes_broken_ids_add() -> None:
    """The single source property that makes the BOS fallback dead code.

    If a CHOCH ever added the broken swing to `broken_ids` BEFORE deciding to
    abort, an aborted CHOCH would leave the still-current `protected_low`
    flagged broken, and the very next BOS could find no eligible replacement.
    This test fails the moment that ordering changes, which is precisely when
    TD-A must be reopened.
    """
    source = (
        Path(_fx.__file__).parents[2]
        / "src" / "btmm_ai_scanner" / "structure" / "transitions.py"
    ).read_text(encoding="utf-8")

    choch_block = source.split("if choch_candidate is not None:")[1].split(
        "if bos_candidate is not None:"
    )[0]
    for half in choch_block.split("else:"):
        if "_most_recent_unbroken" not in half:
            continue
        abort = half.index("continue")
        add = half.index("broken_ids.add")
        assert abort < add, (
            "CHOCH must abort BEFORE consuming the broken swing; reversing this "
            "makes the BOS protected-fallback reachable and reopens TD-A"
        )


def test_bos_consumes_only_the_opposite_side_of_the_replacement_search() -> None:
    """A BULLISH BOS breaks a HIGH but searches the LOWS for a replacement, so the
    BOS itself can never empty the candidate set it is about to query."""
    source = (
        Path(_fx.__file__).parents[2]
        / "src" / "btmm_ai_scanner" / "structure" / "transitions.py"
    ).read_text(encoding="utf-8")
    bos_block = source.split("if bos_candidate is not None:")[1].split(
        "elif kind == _EVENT_SWING_VISIBLE"
    )[0]
    high_side = bos_block.split("if is_high_side:")[1].split("else:")[0]
    assert "SwingType.SWING_LOW" in high_side
    assert "SwingType.SWING_HIGH" not in high_side


def _campaign_case(seed: int):
    """Deterministic CHOCH/BOS chains: valid alternating swings plus a close path
    that repeatedly crosses the live structural levels."""
    state = seed
    def nxt(mod):
        nonlocal state
        state = (state * 1103515245 + 12345) & 0x7FFFFFFF
        return state % mod

    # Alternating swings on even pivot bars, confirmed one bar later.
    specs = []
    swing_type = L if seed % 2 == 0 else H
    low_base, high_base = 100, 112
    for i in range(9):
        pivot = 2 + 2 * i
        if swing_type is L:
            price = low_base + nxt(9) - 4
        else:
            price = high_base + nxt(9) - 4
        specs.append((swing_type, str(price), pivot, pivot + 1))
        swing_type = H if swing_type is L else L

    overrides = {}
    for bar in range(3, BAR_COUNT):
        overrides[bar] = {"close": str(96 + nxt(22))}
    return _build(specs, NEUTRAL, overrides)


# Seeds verified to produce at least one CHOCH/BOS, jointly covering all four
# transition types. Seeds that never bootstrap prove nothing and are excluded
# deliberately rather than silently tolerated.
_SEEDS = (2, 3, 6, 9, 14, 16, 19, 21, 24, 25, 30, 32)

# The whole band is swept as well — see test_broad_seed_sweep_never_reaches_the_fallback.
_SWEEP = range(2, 400)


@pytest.mark.parametrize("seed", _SEEDS)
def test_campaign_never_reaches_the_fallback(seed: int) -> None:
    """Every replacement search in a real walk has at least one candidate."""
    candles, swings = _campaign_case(seed)
    with _spy_replacements() as calls:
        _analyze(candles, swings)
    assert calls, f"seed {seed} produced no CHOCH/BOS at all"
    for call in calls:
        assert call["eligible"] >= 1, (
            f"seed {seed}: replacement search found no candidate — "
            "the fallback branch would be reachable, reopen TD-A"
        )
        assert call["result"] is not None


def test_broad_seed_sweep_never_reaches_the_fallback() -> None:
    """The primary reachability evidence: a wide deterministic sweep.

    Every replacement search across the whole band is recorded, and the minimum
    eligible-candidate count is reported. A single zero anywhere would mean the
    fallback is live and TD-A must be reopened.
    """
    productive = 0
    searches = 0
    minimum_eligible = None
    kinds: set[StructureTransitionType] = set()

    for seed in _SWEEP:
        candles, swings = _campaign_case(seed)
        with _spy_replacements() as calls:
            analysis = _analyze(candles, swings)
        if not calls:
            continue
        productive += 1
        searches += len(calls)
        kinds.update(t.transition_type for t in analysis.structure_transitions)
        worst = min(c["eligible"] for c in calls)
        minimum_eligible = worst if minimum_eligible is None else min(
            minimum_eligible, worst
        )
        for call in calls:
            assert call["result"] is not None

    assert productive >= 350, productive
    assert searches >= 900, searches
    assert len(kinds) == 4, sorted(k.value for k in kinds)
    assert minimum_eligible == 1, (
        f"minimum eligible candidate count was {minimum_eligible}; it must be "
        "exactly 1 — 0 means the fallback is reachable, and >1 means the sweep "
        "no longer approaches the boundary and has stopped being evidence"
    )


def test_the_campaign_actually_exercises_bos_and_choch() -> None:
    """Guard the guard: a campaign that never breaks anything proves nothing."""
    kinds: set[StructureTransitionType] = set()
    replacement_calls = 0
    for seed in _SEEDS:
        candles, swings = _campaign_case(seed)
        with _spy_replacements() as calls:
            analysis = _analyze(candles, swings)
        replacement_calls += len(calls)
        kinds.update(t.transition_type for t in analysis.structure_transitions)
    assert StructureTransitionType.BULLISH_BOS in kinds, kinds
    assert StructureTransitionType.BEARISH_BOS in kinds, kinds
    assert {
        StructureTransitionType.BULLISH_CHOCH,
        StructureTransitionType.BEARISH_CHOCH,
    } & kinds, kinds
    assert replacement_calls >= 20, replacement_calls


def test_protected_level_is_never_broken_while_its_direction_holds() -> None:
    """The invariant behind the unreachability proof, checked on real walks.

    At every replacement search, the currently protected swing of the searched
    side is among the eligible candidates.
    """
    for seed in _SEEDS:
        candles, swings = _campaign_case(seed)
        with _spy_replacements() as calls:
            _analyze(candles, swings)
        for call in calls:
            assert call["result"].record_id in call["eligible_ids"]


def test_exhausting_the_lows_flips_direction_instead_of_emptying_the_set() -> None:
    """The adversarial construction, and why it cannot work.

    Breaking the protected low requires a BEARISH CHOCH, which in the same step
    flips the direction to BEARISH and clears `protected_low`. There is no
    sequence that leaves the direction BULLISH with its protected low broken.
    """
    candles, swings = _build(
        _BOOT + [(L, "98", 12, 13)],
        NEUTRAL,
        {10: {"close": "101"}, 15: {"close": "97"}},
    )
    with _spy_replacements() as calls:
        analysis = _analyze(candles, swings)

    types = [t.transition_type for t in analysis.structure_transitions]
    assert StructureTransitionType.BEARISH_CHOCH in types, types
    # The CHOCH that consumed the protected low also flipped the direction.
    choch = next(
        t for t in analysis.structure_transitions
        if t.transition_type is StructureTransitionType.BEARISH_CHOCH
    )
    assert choch.direction_before is StructureDirection.BULLISH
    assert choch.direction_after is StructureDirection.BEARISH
    assert choch.broken_swing_id == _swing_by_pivot(swings, 6).record_id
    for call in calls:
        assert call["eligible"] >= 1


# ---------------------------------------------------------------------------
# Fallback semantics — pinned by injection, no reachability claimed
# ---------------------------------------------------------------------------

def test_injected_replacement_none_retains_the_existing_protected_low() -> None:
    """Executes the bullish fallback expression and pins its exact effect.

    Discriminating: unpatched this fixture selects L3 (bar 10); with the
    replacement forced to None it must retain L2 (bar 6), the pre-BOS protected
    low. A no-op fallback would be indistinguishable without that difference.
    """
    candles, swings = _bos_with_newer_low()
    protected_before = _swing_by_pivot(swings, 6)
    newer_low = _swing_by_pivot(swings, 10)

    natural = _analyze(candles, swings)
    assert natural.current_state.active_protected_low_swing_id == newer_low.record_id

    with _force_replacement_none():
        fallback = _analyze(candles, swings)

    assert len(fallback.structure_transitions) == 1, "BOS must still emit"
    bos = fallback.structure_transitions[0]
    assert bos.transition_type is StructureTransitionType.BULLISH_BOS
    assert bos.protected_swing_id == protected_before.record_id
    assert fallback.current_state.active_protected_low_swing_id == (
        protected_before.record_id
    )
    assert fallback.current_state.direction is StructureDirection.BULLISH


def test_injected_replacement_none_retains_the_existing_protected_high() -> None:
    """Bearish mirror of the fallback expression."""
    candles, swings = _build(
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9),
         (H, "106", 10, 11)],
        "103",
        {BREAK_BAR: {"close": "97"}},
    )
    protected_before = _swing_by_pivot(swings, 6)
    newer_high = _swing_by_pivot(swings, 10)

    natural = _analyze(candles, swings)
    assert natural.current_state.active_protected_high_swing_id == newer_high.record_id

    with _force_replacement_none():
        fallback = _analyze(candles, swings)

    assert len(fallback.structure_transitions) == 1
    bos = fallback.structure_transitions[0]
    assert bos.transition_type is StructureTransitionType.BEARISH_BOS
    assert bos.protected_swing_id == protected_before.record_id
    assert fallback.current_state.active_protected_high_swing_id == (
        protected_before.record_id
    )
    assert fallback.current_state.direction is StructureDirection.BEARISH


def test_fallback_still_consumes_the_broken_weak_level() -> None:
    """Even on the fallback path the broken weak swing is consumed, so the same
    level cannot break twice."""
    candles, swings = _build(
        _BOOT + [(L, "104", 10, 11)],
        NEUTRAL,
        {BREAK_BAR: {"close": BREAK_CLOSE}, BREAK_BAR + 2: {"close": "114"}},
    )
    with _force_replacement_none():
        analysis = _analyze(candles, swings)
    assert len(analysis.structure_transitions) == 1
    assert analysis.current_state.active_weak_high_swing_id is None


# ---------------------------------------------------------------------------
# Non-fallback control — replacement genuinely selected
# ---------------------------------------------------------------------------

def test_bos_selects_a_newer_replacement_and_changes_the_protected_low() -> None:
    candles, swings = _bos_with_newer_low()
    protected_before = _swing_by_pivot(swings, 6)
    newer_low = _swing_by_pivot(swings, 10)

    with _spy_replacements() as calls:
        analysis = _analyze(candles, swings)

    assert len(calls) == 1
    assert calls[0]["eligible"] == 3, calls[0]["eligible"]
    assert calls[0]["result"].record_id == newer_low.record_id

    assert len(analysis.structure_transitions) == 1
    bos = analysis.structure_transitions[0]
    assert bos.transition_type is StructureTransitionType.BULLISH_BOS
    assert bos.direction_before is StructureDirection.BULLISH
    assert bos.direction_after is StructureDirection.BULLISH
    assert bos.protected_swing_id == newer_low.record_id
    assert bos.protected_swing_id != protected_before.record_id
    assert analysis.current_state.active_protected_low_swing_id == newer_low.record_id


def test_unchanged_protected_id_does_not_imply_fallback() -> None:
    """The vacuity trap TD-A must avoid.

    Here the protected low is identical before and after the BOS — yet the
    fallback was NOT taken: the replacement search found two candidates and
    happened to re-select the same swing.
    """
    candles, swings = _bos_without_newer_low()
    protected = _swing_by_pivot(swings, 6)

    with _spy_replacements() as calls:
        analysis = _analyze(candles, swings)

    assert analysis.current_state.active_protected_low_swing_id == protected.record_id
    assert len(calls) == 1
    assert calls[0]["eligible"] == 2, "not a fallback — candidates existed"
    assert calls[0]["result"].record_id == protected.record_id


# ---------------------------------------------------------------------------
# Replacement ordering — the P2-I5 parity target
# ---------------------------------------------------------------------------

def test_most_recent_unbroken_key_is_pinned_to_source() -> None:
    source = (
        Path(_fx.__file__).parents[2]
        / "src" / "btmm_ai_scanner" / "structure" / "transitions.py"
    ).read_text(encoding="utf-8")
    body = source.split("def _most_recent_unbroken(")[1].split("\ndef ")[0]
    assert "s.record_id not in broken_ids" in body
    assert "key=lambda s: (s.pivot_bar_index, s.pivot_start_time_utc, str(s.record_id))" in body
    assert "max(" in body


def test_replacement_picks_the_newest_of_several_eligible_candidates() -> None:
    """Three eligible lows; the one with the greatest pivot_bar_index wins."""
    candles, swings = _bos_with_newer_low()
    with _spy_replacements() as calls:
        _analyze(candles, swings)
    eligible = calls[0]["eligible_ids"]
    assert eligible == {
        _swing_by_pivot(swings, 2).record_id,
        _swing_by_pivot(swings, 6).record_id,
        _swing_by_pivot(swings, 10).record_id,
    }
    assert calls[0]["result"].record_id == _swing_by_pivot(swings, 10).record_id


def test_replacement_skips_broken_candidates() -> None:
    """A low already consumed by an earlier break is not eligible again."""
    candles, swings = _build(
        _BOOT + [(L, "98", 12, 13), (H, "114", 14, 15)],
        NEUTRAL,
        {10: {"close": "101"}, 17: {"close": "115"}},
    )
    broken_low = _swing_by_pivot(swings, 6)          # consumed by the CHOCH
    with _spy_replacements() as calls:
        _analyze(candles, swings)
    later = [c for c in calls if broken_low.record_id not in c["eligible_ids"]]
    assert later, "expected a search after the low was consumed"
    for call in later:
        assert call["result"].record_id != broken_low.record_id


# ---------------------------------------------------------------------------
# BOS state mutation
# ---------------------------------------------------------------------------

def test_bos_clears_only_its_own_weak_side() -> None:
    candles, swings = _bos_with_newer_low()
    analysis = _analyze(candles, swings)
    state = analysis.current_state
    assert state.direction is StructureDirection.BULLISH
    assert state.active_weak_high_swing_id is None, "the broken weak high clears"
    assert state.active_weak_low_swing_id is None, "BULLISH never arms a weak low"
    assert state.active_protected_high_swing_id is None
    assert state.active_protected_low_swing_id is not None


def test_bos_does_not_re_arm_the_weak_side_in_its_own_branch() -> None:
    """Re-arming happens only on a later SWING_VISIBLE event whose pivot bar is
    past the boundary index (`transitions.py:328-340`) — never inside the BOS
    handler. TD-B owns the positive re-arm case; this pins the negative."""
    candles, swings = _bos_with_newer_low()
    analysis = _analyze(candles, swings)
    assert analysis.current_state.active_weak_high_swing_id is None


def test_bos_sets_the_weak_boundary_to_the_break_candle_index() -> None:
    """The boundary index is private, so it is pinned at the source. Its
    observable effect is the re-arm gate, which TD-B will exercise."""
    source = (
        Path(_fx.__file__).parents[2]
        / "src" / "btmm_ai_scanner" / "structure" / "transitions.py"
    ).read_text(encoding="utf-8")
    bos_block = source.split("if bos_candidate is not None:")[1].split(
        "elif kind == _EVENT_SWING_VISIBLE"
    )[0]
    assert (
        "weak_high_boundary_index = candle_index_by_id[candle.record_id]" in bos_block
    )
    assert (
        "weak_low_boundary_index = candle_index_by_id[candle.record_id]" in bos_block
    )
    gate = source.split("elif kind == _EVENT_SWING_VISIBLE:")[1]
    assert "swing.pivot_bar_index > weak_high_boundary_index" in gate
    assert "swing.pivot_bar_index > weak_low_boundary_index" in gate


def test_bos_transition_fields_match_the_break() -> None:
    candles, swings = _bos_with_newer_low()
    broken = _swing_by_pivot(swings, 8)              # the weak high, 112
    break_candle = candles[BREAK_BAR]

    analysis = _analyze(candles, swings)
    bos = analysis.structure_transitions[0]

    assert bos.broken_swing_id == broken.record_id
    assert bos.broken_level_price == broken.pivot_price == Decimal("112")
    assert bos.break_close_price == break_candle.close == Decimal(BREAK_CLOSE)
    assert bos.break_candle_id == break_candle.record_id
    assert bos.weak_swing_id is None
    assert analysis.current_state.latest_transition_id == bos.record_id


def test_bos_timing_is_the_later_of_candle_and_broken_swing() -> None:
    """`availability = max(candle.availability, broken_swing.availability)`.

    The two operands genuinely differ here — the broken weak high was confirmed
    well before the break candle — so the max is exercised, not trivially equal.
    In fact the candle side always wins: a weak level must already be armed for a
    BOS to fire, so its availability necessarily precedes the break candle's.
    """
    candles, swings = _bos_with_newer_low()
    broken = _swing_by_pivot(swings, 8)
    break_candle = candles[BREAK_BAR]

    bos = _analyze(candles, swings).structure_transitions[0]

    assert broken.availability_time_utc < break_candle.availability_time_utc
    assert bos.event_time_utc == break_candle.event_time_utc
    assert bos.availability_time_utc == max(
        break_candle.availability_time_utc, broken.availability_time_utc
    )
    assert bos.availability_time_utc == break_candle.availability_time_utc


def test_repeat_break_of_the_same_level_emits_no_second_transition() -> None:
    candles, swings = _build(
        _BOOT + [(L, "104", 10, 11)],
        NEUTRAL,
        {
            BREAK_BAR: {"close": BREAK_CLOSE},
            BREAK_BAR + 2: {"close": "114"},
            BREAK_BAR + 4: {"close": "120"},
        },
    )
    analysis = _analyze(candles, swings)
    assert len(analysis.structure_transitions) == 1
    assert analysis.current_state.active_weak_high_swing_id is None


# ---------------------------------------------------------------------------
# Batch / incremental replay
# ---------------------------------------------------------------------------

def _visible_through(swings, watermark):
    return tuple(
        s for s in swings if s.meaningful_confirmation_time_utc <= watermark
    )


def _replay(candles, swings):
    comparisons = 0
    last = None
    for k in range(1, len(candles) + 1):
        prefix = candles[:k]
        visible = _visible_through(swings, prefix[-1].availability_time_utc)
        last = _analyze(prefix, visible)
        comparisons += 1
    return last, comparisons


@pytest.mark.parametrize(
    "name", ["with_newer_low", "without_newer_low", "choch_then_bos"]
)
def test_batch_equals_incremental_replay(name: str) -> None:
    if name == "with_newer_low":
        candles, swings = _bos_with_newer_low()
    elif name == "without_newer_low":
        candles, swings = _bos_without_newer_low()
    else:
        candles, swings = _build(
            _BOOT + [(L, "98", 12, 13)],
            NEUTRAL,
            {10: {"close": "101"}, 15: {"close": "97"}},
        )

    batch = _analyze(candles, swings)
    replayed, comparisons = _replay(candles, swings)

    assert comparisons == BAR_COUNT
    assert replayed.structure_transitions == batch.structure_transitions
    assert replayed.current_state == batch.current_state
    assert replayed.swing_relationships == batch.swing_relationships
    assert replayed.analyzed_swing_count == batch.analyzed_swing_count


def test_replay_totals() -> None:
    total = 0
    for seed in _SEEDS:
        candles, swings = _campaign_case(seed)
        batch = _analyze(candles, swings)
        replayed, comparisons = _replay(candles, swings)
        total += comparisons
        assert replayed.structure_transitions == batch.structure_transitions
        assert replayed.current_state == batch.current_state
    assert total == len(_SEEDS) * BAR_COUNT
