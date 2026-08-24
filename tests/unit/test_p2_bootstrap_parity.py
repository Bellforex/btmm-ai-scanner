"""Parity between the Pine P2-I4 direction bootstrap and production Python.

Pine cannot run locally, so the `_pine_*` helpers below are a faithful
**test-side** transcription of `f_p2RelIsHigh` / `f_p2OrderRelationships` /
`f_p2BootstrapWalk` from `tradingview/btmm_poi_btrc_scanner_v1.pine`. They are
compared against the real production entry point,
`structure.analyzer.analyze_structure_state`, which is always the reference side.

What the model reproduces, and why each detail matters:

* bootstrap fires ONLY on a relationship event and ONLY while the direction is
  still UNDETERMINED (`transitions.py:363`);
* `latest_relationship_label/swing` are overwritten UNCONDITIONALLY on every
  relationship event (`:358-361`), so an EQUAL erases prior directional evidence
  for that side and later contradictory evidence replaces earlier evidence;
* `HH + HL -> BULLISH` sets protected_low / weak_high, `LH + LL -> BEARISH` sets
  protected_high / weak_low; the opposite two stay unset (`:366-381`);
* bootstrap emits NO transition;
* events are walked in MERGED AVAILABILITY ORDER, not in the highs-then-lows
  order that `detect_swing_relationships` happens to build them in. This is the
  single highest-risk detail of the phase and is pinned by
  `test_api_order_is_not_chronology_*` below, which fails outright for an
  implementation that iterates the published tuple.

Ordering key. Python's merged key is `(availability_time, kind, tiebreak)` with
`kind = _EVENT_RELATIONSHIP` constant across relationships, so restricted to
relationships it is `(availability_time_utc, current_swing.pivot_bar_index,
str(record_id))` (`transitions.py:122-133`). The `record_id` leg is unreachable in
production — see `test_production_cannot_tie_pivot_bar_index_across_types`.

Fixtures are built so that NO BOS or CHOCH can fire after bootstrap: every candle
close sits strictly inside the resulting protected/weak band. Each test asserts
`structure_transitions == ()` to keep that honest.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure.enums import StructureDirection

_SIB = importlib.util.spec_from_file_location(
    "_p2_boot_fixtures",
    Path(__file__).with_name("test_structure_transitions_contract.py"),
)
assert _SIB is not None and _SIB.loader is not None
_fx = importlib.util.module_from_spec(_SIB)
sys.modules[_SIB.name] = _fx
_SIB.loader.exec_module(_fx)

_REL = importlib.util.spec_from_file_location(
    "_p2_boot_relmodel",
    Path(__file__).with_name("test_p2_relationship_parity.py"),
)
assert _REL is not None and _REL.loader is not None
_relmod = importlib.util.module_from_spec(_REL)
sys.modules[_REL.name] = _relmod
_REL.loader.exec_module(_relmod)

_series = _fx._series
_swing = _fx._swing
_analyze = _fx._analyze

# The I3 classifier, reused verbatim so the two models cannot drift apart.
_pine_classify = _relmod._pine_classify

SWING_HIGH, SWING_LOW = 1, -1

# Pine int codes, mirrored from the production source.
C_HH, C_LH, C_EH = 1, -1, 10
C_HL, C_LL, C_EL = 2, -2, 20
_HIGH_CODES = frozenset({C_HH, C_LH, C_EH})

DIR_UNDETERMINED, DIR_BULLISH, DIR_BEARISH = 0, 1, -1

_DIR_FROM_PYTHON = {
    StructureDirection.UNDETERMINED: DIR_UNDETERMINED,
    StructureDirection.BULLISH: DIR_BULLISH,
    StructureDirection.BEARISH: DIR_BEARISH,
}

# Pine encodes "absent" as the C_ST_NA sentinel (-99). The model uses None because
# the values it carries are timestamps; the mapping is one-to-one.
NA = None


# ---------------------------------------------------------------------------
# Test-side transcription of the Pine algorithm
# ---------------------------------------------------------------------------

class _View4:
    """Mirror of Pine `StructSwingView`, including the I4 ordering field."""

    __slots__ = ("stableKey", "swingType", "pivotPrice", "referenceAtr",
                 "meaningfulConfTime", "pivotStartAbs")

    def __init__(self, swing) -> None:
        self.stableKey = swing.pivot_end_time_utc
        self.swingType = (
            SWING_HIGH if swing.swing_type == SwingType.SWING_HIGH else SWING_LOW
        )
        self.pivotPrice = swing.pivot_price
        self.referenceAtr = swing.pivot_reference_atr
        self.meaningfulConfTime = swing.meaningful_confirmation_time_utc
        self.pivotStartAbs = swing.pivot_bar_index


def _pine_rels(swings) -> list[tuple]:
    """f_p2BuildRelationships -> [(key, prevKey, code, availability, startAbs)].

    Deliberately keeps the highs-then-lows build order, exactly as Pine does.
    """
    views = [_View4(s) for s in swings]
    out: list[tuple] = []
    for want in (SWING_HIGH, SWING_LOW):
        prev_idx = -1
        for i, v in enumerate(views):
            if v.swingType != want:
                continue
            if prev_idx >= 0:
                pv = views[prev_idx]
                out.append(
                    (
                        v.stableKey,
                        pv.stableKey,
                        _pine_classify(v, pv),
                        max(v.meaningfulConfTime, pv.meaningfulConfTime),
                        v.pivotStartAbs,
                    )
                )
            prev_idx = i
    return out


def _pine_order(rels) -> list[int]:
    """f_p2OrderRelationships — stable insertion sort on integer keys."""
    order: list[int] = []
    for i, r in enumerate(rels):
        pos = len(order)
        for j, other_index in enumerate(order):
            o = rels[other_index]
            earlier = r[3] < o[3] or (r[3] == o[3] and r[4] < o[4])
            if earlier:
                pos = j
                break
        order.insert(pos, i)
    return order


def _pine_bootstrap(swings) -> tuple:
    """f_p2BootstrapWalk -> (direction, protHigh, protLow, weakHigh, weakLow)."""
    rels = _pine_rels(swings)
    order = _pine_order(rels)

    direction = DIR_UNDETERMINED
    prot_high = prot_low = weak_high = weak_low = NA
    hi_label = lo_label = None
    hi_swing = lo_swing = NA

    for index in order:
        key, _prev_key, code, _avail, _start_abs = rels[index]
        if code in _HIGH_CODES:
            hi_label, hi_swing = code, key
        else:
            lo_label, lo_swing = code, key
        if direction == DIR_UNDETERMINED:
            if hi_label == C_HH and lo_label == C_HL:
                direction, prot_low, weak_high = DIR_BULLISH, lo_swing, hi_swing
            elif hi_label == C_LH and lo_label == C_LL:
                direction, prot_high, weak_low = DIR_BEARISH, hi_swing, lo_swing

    return (direction, prot_high, prot_low, weak_high, weak_low)


def _python_bootstrap(candles, swings) -> tuple:
    """Same projection, from the production analyzer."""
    analysis = _analyze(candles, tuple(swings))
    state = analysis.current_state
    key_of = {s.record_id: s.pivot_end_time_utc for s in swings}

    def resolve(record_id):
        return key_of[record_id] if record_id is not None else NA

    return (
        _DIR_FROM_PYTHON[state.direction],
        resolve(state.active_protected_high_swing_id),
        resolve(state.active_protected_low_swing_id),
        resolve(state.active_weak_high_swing_id),
        resolve(state.active_weak_low_swing_id),
    ), analysis


def _assert_parity(candles, swings) -> tuple:
    """Compare the full bootstrap state and prove no break fired."""
    reference, analysis = _python_bootstrap(candles, swings)
    assert analysis.structure_transitions == (), (
        "fixture must not trigger BOS/CHOCH — I4 implements neither"
    )
    assert analysis.current_state.latest_transition_id is None
    assert _pine_bootstrap(swings) == reference
    return reference


def _assert_prefix_parity(candles, swings) -> list[tuple]:
    """Compare at EVERY prefix, so bootstrap TIMING is validated, not just the
    final state."""
    seen = []
    for length in range(len(swings) + 1):
        seen.append(_assert_parity(candles, swings[:length]))
    return seen


# ---------------------------------------------------------------------------
# Fixture builder
# ---------------------------------------------------------------------------
# Swings ALTERNATE by type, as `_validate_swings` requires. `conf` is the bar
# whose availability_time becomes the swing's meaningful confirmation time, which
# is what relationship availability (and therefore event order) is built from.

NEUTRAL = "105"


def _build(specs, neutral: str = NEUTRAL):
    """specs: [(swing_type, price, pivot_bar, conf_bar)] in source chronology."""
    candles = _series(neutral)
    swings = tuple(
        _swing(i + 1, swing_type, price, pivot_bar, conf_bar, candles)
        for i, (swing_type, price, pivot_bar, conf_bar) in enumerate(specs)
    )
    return candles, swings


H, L = SwingType.SWING_HIGH, SwingType.SWING_LOW

# Canonical bullish shape: L 100 -> H 110 -> L 102 (HL) -> H 112 (HH).
BULL = [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "112", 8, 9)]
# Canonical bearish shape: H 110 -> L 100 -> H 108 (LH) -> L 98 (LL).
BEAR = [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "98", 8, 9)]


def _keys(candles, *pivot_bars):
    return [candles[b].event_time_utc for b in pivot_bars]


# ---------------------------------------------------------------------------
# Phase 11 — bullish cases. Every expectation comes from transitions.py, not
# from textbook structure rules.
# ---------------------------------------------------------------------------

def test_high_relationship_alone_does_not_bootstrap() -> None:
    # H 110 -> L 100 -> H 112 : one HIGH relationship (HH), no LOW relationship.
    candles, swings = _build([(H, "110", 2, 3), (L, "100", 4, 5), (H, "112", 6, 7)])
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_low_relationship_alone_does_not_bootstrap() -> None:
    # L 100 -> H 110 -> L 102 : one LOW relationship (HL), no HIGH relationship.
    candles, swings = _build([(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7)])
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_hh_then_hl_bootstraps_bullish() -> None:
    # Availability forced so the HIGH relationship lands FIRST.
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 15), (H, "112", 8, 9)]
    )
    prot_low, weak_high = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_hl_then_hh_bootstraps_bullish() -> None:
    # Natural availability: the LOW relationship lands first.
    candles, swings = _build(BULL)
    prot_low, weak_high = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_bullish_bootstrap_leaves_the_opposite_slots_unset() -> None:
    candles, swings = _build(BULL)
    direction, prot_high, prot_low, weak_high, weak_low = _assert_parity(
        candles, swings
    )
    assert direction == DIR_BULLISH
    assert prot_high is NA and weak_low is NA
    assert prot_low is not NA and weak_high is not NA


def test_equal_high_blocks_bullish_bootstrap() -> None:
    # EH + HL. H 110 -> H 110.05 is inside 0.10 * atr(1.0) = 0.10.
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "110.05", 8, 9)]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_equal_low_blocks_bullish_bootstrap() -> None:
    # HH + EL.
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "100.05", 6, 7), (H, "112", 8, 9)]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_equal_high_and_equal_low_blocks_bootstrap() -> None:
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "100.05", 6, 7), (H, "110.05", 8, 9)]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


# ---------------------------------------------------------------------------
# Phase 12 — bearish mirrors
# ---------------------------------------------------------------------------

def test_lh_alone_does_not_bootstrap() -> None:
    candles, swings = _build([(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7)])
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_ll_alone_does_not_bootstrap() -> None:
    candles, swings = _build([(L, "100", 2, 3), (H, "110", 4, 5), (L, "98", 6, 7)])
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_lh_then_ll_bootstraps_bearish() -> None:
    candles, swings = _build(BEAR, neutral="103")
    prot_high, weak_low = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BEARISH, prot_high, NA, NA, weak_low
    )


def test_ll_then_lh_bootstraps_bearish() -> None:
    # Availability forced so the LOW relationship lands first.
    candles, swings = _build(
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 15), (L, "98", 8, 9)],
        neutral="103",
    )
    prot_high, weak_low = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BEARISH, prot_high, NA, NA, weak_low
    )


def test_bearish_bootstrap_leaves_the_opposite_slots_unset() -> None:
    candles, swings = _build(BEAR, neutral="103")
    direction, prot_high, prot_low, weak_high, weak_low = _assert_parity(
        candles, swings
    )
    assert direction == DIR_BEARISH
    assert prot_low is NA and weak_high is NA
    assert prot_high is not NA and weak_low is not NA


def test_equal_high_blocks_bearish_bootstrap() -> None:
    candles, swings = _build(
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "110.05", 6, 7), (L, "98", 8, 9)],
        neutral="103",
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_equal_low_blocks_bearish_bootstrap() -> None:
    candles, swings = _build(
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "108", 6, 7), (L, "100.05", 8, 9)],
        neutral="103",
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_bearish_equal_high_and_equal_low_blocks_bootstrap() -> None:
    candles, swings = _build(
        [(H, "110", 2, 3), (L, "100", 4, 5), (H, "110.05", 6, 7), (L, "100.05", 8, 9)],
        neutral="103",
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


# ---------------------------------------------------------------------------
# Phase 13 — contradictory evidence. Production is the only authority here; no
# tie-resolution policy is invented.
# ---------------------------------------------------------------------------

def test_hh_with_ll_does_not_bootstrap() -> None:
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "98", 6, 7), (H, "112", 8, 9)]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_lh_with_hl_does_not_bootstrap() -> None:
    candles, swings = _build(
        [(L, "100", 2, 3), (H, "110", 4, 5), (L, "102", 6, 7), (H, "108", 8, 9)]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_later_evidence_replaces_earlier_evidence() -> None:
    # HH+LL (no bootstrap), then the LOW side is superseded by an HL, which
    # completes HH+HL and bootstraps BULLISH.
    candles, swings = _build(
        [
            (L, "100", 2, 3), (H, "110", 4, 5),
            (L, "98", 6, 7), (H, "112", 8, 9),
            (L, "104", 10, 11), (H, "114", 12, 13),
        ]
    )
    prot_low, weak_high = _keys(candles, 10, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_an_equal_erases_prior_directional_evidence() -> None:
    # HH established, then the HIGH side is overwritten by an EH before the LOW
    # side ever completes: the pair never qualifies.
    candles, swings = _build(
        [
            (L, "100", 2, 3), (H, "110", 4, 5),
            (L, "98", 6, 7), (H, "112", 8, 9),
            (L, "104", 10, 15), (H, "112.05", 12, 13),
        ]
    )
    assert _assert_parity(candles, swings) == (DIR_UNDETERMINED, NA, NA, NA, NA)


# ---------------------------------------------------------------------------
# Phase 14 — THE API-ORDER TRAP.
#
# `detect_swing_relationships` publishes ALL HIGH relationships before ALL LOW
# relationships. These fixtures are constructed so that consuming that order as
# chronology yields the WRONG direction. An implementation that loops
# highs-then-lows fails here; one that sorts by availability passes.
# ---------------------------------------------------------------------------

# Highs 110 -> 120 (HH) -> 115 (LH);  lows 100 -> 90 (LL) -> 95 (HL).
# Availability is forced to r_l1(7) < r_h1(9) < r_l2(11) < r_h2(21):
#   chronological : LL, HH, HL   -> HH+HL -> BULLISH
#   API order     : HH, LH, LL   -> LH+LL -> BEARISH   (wrong)
_TRAP_BULL = [
    (L, "100", 2, 3), (H, "110", 4, 5),
    (L, "90", 6, 7), (H, "120", 8, 9),
    (L, "95", 10, 11), (H, "115", 12, 21),
]


def test_api_order_is_not_chronology_bullish() -> None:
    candles, swings = _build(_TRAP_BULL)
    prot_low, weak_high = _keys(candles, 10, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_api_order_model_would_have_diverged_bullish() -> None:
    """Guard the guard: prove the trap fixture actually discriminates."""
    _candles, swings = _build(_TRAP_BULL)
    assert _naive_api_order_bootstrap(swings)[0] == DIR_BEARISH
    assert _pine_bootstrap(swings)[0] == DIR_BULLISH


# Mirror: highs 110 -> 100 (LH) -> 120 (HH);  lows 100 -> 90 (LL) -> 95 (HL).
# Availability is forced to r_h1(7) < r_l1(9) < r_l2(13) < r_h2(19):
#   chronological : LH, LL       -> LH+LL -> BEARISH
#   API order     : LH, HH, LL, HL -> HH+HL -> BULLISH   (wrong)
_TRAP_BEAR = [
    (H, "110", 2, 3), (L, "100", 4, 5),
    (H, "100", 6, 7), (L, "90", 8, 9),
    (H, "120", 10, 19), (L, "95", 12, 13),
]
_TRAP_BEAR_NEUTRAL = "95"


def test_api_order_is_not_chronology_bearish() -> None:
    candles, swings = _build(_TRAP_BEAR, neutral=_TRAP_BEAR_NEUTRAL)
    prot_high, weak_low = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BEARISH, prot_high, NA, NA, weak_low
    )


def test_api_order_model_would_have_diverged_bearish() -> None:
    _candles, swings = _build(_TRAP_BEAR, neutral=_TRAP_BEAR_NEUTRAL)
    assert _naive_api_order_bootstrap(swings)[0] == DIR_BULLISH
    assert _pine_bootstrap(swings)[0] == DIR_BEARISH


def _naive_api_order_bootstrap(swings) -> tuple:
    """The wrong implementation: walk the published tuple as if it were
    chronology. Used only to prove the trap fixtures discriminate."""
    rels = _pine_rels(swings)
    return _walk(rels, list(range(len(rels))))


def _walk(rels, order) -> tuple:
    direction = DIR_UNDETERMINED
    prot_high = prot_low = weak_high = weak_low = NA
    hi_label = lo_label = None
    hi_swing = lo_swing = NA
    for index in order:
        key, _p, code, _a, _s = rels[index]
        if code in _HIGH_CODES:
            hi_label, hi_swing = code, key
        else:
            lo_label, lo_swing = code, key
        if direction == DIR_UNDETERMINED:
            if hi_label == C_HH and lo_label == C_HL:
                direction, prot_low, weak_high = DIR_BULLISH, lo_swing, hi_swing
            elif hi_label == C_LH and lo_label == C_LL:
                direction, prot_high, weak_low = DIR_BEARISH, hi_swing, lo_swing
    return (direction, prot_high, prot_low, weak_high, weak_low)


# ---------------------------------------------------------------------------
# Phase 15 — same-availability tie
# ---------------------------------------------------------------------------

# r_l2 and r_h2 share an availability time (bar 15). Python breaks the tie on the
# CURRENT swing's pivot_bar_index: L3 (bar 10) sorts before H3 (bar 12), so the
# HL lands first and the direction is BULLISH. Reversing the tie gives BEARISH.
_TIE = [
    (L, "100", 2, 3), (H, "110", 4, 5),
    (L, "90", 6, 7), (H, "120", 8, 9),
    (L, "95", 10, 15), (H, "115", 12, 15),
]


def test_same_availability_tie_breaks_on_pivot_bar_index() -> None:
    candles, swings = _build(_TIE)
    prot_low, weak_high = _keys(candles, 10, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_the_tie_fixture_actually_ties() -> None:
    _candles, swings = _build(_TIE)
    rels = _pine_rels(swings)
    availabilities = [r[3] for r in rels]
    assert len(set(availabilities)) < len(availabilities), "fixture must tie"


def test_swapping_the_tied_pair_would_change_the_direction() -> None:
    """Guard the guard: the pivot_bar_index leg is load-bearing, not decorative.

    Swaps ONLY the two tied events — the whole order is left intact, so the test
    isolates the tiebreak rather than scrambling chronology.
    """
    _candles, swings = _build(_TIE)
    rels = _pine_rels(swings)
    order = _pine_order(rels)
    tied = [i for i, position in enumerate(order) if rels[position][3] == max(
        r[3] for r in rels
    )]
    assert len(tied) == 2, "fixture must present exactly one tied pair"
    swapped = list(order)
    swapped[tied[0]], swapped[tied[1]] = swapped[tied[1]], swapped[tied[0]]
    assert _walk(rels, swapped)[0] == DIR_BEARISH
    assert _pine_bootstrap(swings)[0] == DIR_BULLISH


def test_production_cannot_tie_pivot_bar_index_across_types() -> None:
    """The `str(record_id)` leg of Python's relationship key is UNREACHABLE.

    `_find_single_candle_pivots` emits at most one pivot per candle index and
    skips any index that qualifies as both a high and a low (swings.py:112-114),
    so `pivot_bar_index` is unique across confirmed swings and
    `(availability, pivot_bar_index)` is already a total order. Pine therefore
    reproduces the ordering exactly without needing a UUID surrogate.
    """
    source = Path(
        _fx.__file__
    ).parents[2] / "src" / "btmm_ai_scanner" / "domain" / "swings.py"
    text = source.read_text(encoding="utf-8")
    assert "if qualifies_as_high and qualifies_as_low:" in text
    assert "continue" in text.split("if qualifies_as_high and qualifies_as_low:")[1][:60]


# ---------------------------------------------------------------------------
# Phase 16 — once-only. Relationship evidence alone can never flip the direction;
# flips belong to CHOCH (P2-I5+).
# ---------------------------------------------------------------------------

def test_bullish_bootstrap_is_not_flipped_by_later_bearish_relationships() -> None:
    candles, swings = _build(
        [
            (L, "100", 2, 3), (H, "110", 4, 5),
            (L, "102", 6, 7), (H, "112", 8, 9),
            (L, "95", 10, 11), (H, "105", 12, 13),
        ]
    )
    prot_low, weak_high = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )


def test_bearish_bootstrap_is_not_flipped_by_later_bullish_relationships() -> None:
    candles, swings = _build(
        [
            (H, "110", 2, 3), (L, "100", 4, 5),
            (H, "108", 6, 7), (L, "98", 8, 9),
            (H, "107", 10, 11), (L, "99", 12, 13),
        ],
        neutral="103",
    )
    prot_high, weak_low = _keys(candles, 6, 8)
    assert _assert_parity(candles, swings) == (
        DIR_BEARISH, prot_high, NA, NA, weak_low
    )


def test_protected_and_weak_are_frozen_after_bootstrap_without_a_break() -> None:
    """The bootstrap assignment is not re-pointed by later swings while no BOS or
    CHOCH fires — the weak slot is already occupied, and the opposite weak slot
    requires the opposite direction (transitions.py:328-353)."""
    candles, short = _build(BULL)
    baseline = _assert_parity(candles, short)
    _candles2, long = _build(
        BULL + [(L, "103", 10, 11), (H, "111", 12, 13)]
    )
    extended = _assert_parity(candles, long)
    assert extended == baseline


# ---------------------------------------------------------------------------
# Phase 10 — LEFT-EDGE RESET. Pine must never bootstrap from evidence that has
# fallen outside the bounded input Python is given.
# ---------------------------------------------------------------------------

def test_bootstrap_disappears_when_the_evidence_leaves_the_window() -> None:
    candles, full = _build(BULL)
    assert _assert_parity(candles, full)[0] == DIR_BULLISH

    # Advance the window: the first low and first high drop out, leaving one
    # swing of each type and therefore NO relationships at all.
    truncated = full[2:]
    assert _assert_parity(candles, truncated) == (DIR_UNDETERMINED, NA, NA, NA, NA)


def test_bootstrap_returns_only_when_python_also_bootstraps() -> None:
    candles, full = _build(BULL + [(L, "104", 10, 11), (H, "114", 12, 13)])
    window = full[2:]                      # L 102, H 112, L 104, H 114
    # HL (102 -> 104) and HH (112 -> 114) are both inside the window.
    prot_low, weak_high = _keys(candles, 10, 12)
    assert _assert_parity(candles, window) == (
        DIR_BULLISH, NA, prot_low, weak_high, NA
    )
    # ...and the bootstrap is anchored to the IN-WINDOW swings, not the dropped
    # ones, which is what a hidden retained predecessor would get wrong.
    assert prot_low != candles[6].event_time_utc
    assert weak_high != candles[8].event_time_utc


def test_left_edge_no_hidden_state_across_growing_windows() -> None:
    candles, full = _build(_TRAP_BULL)
    for start in range(len(full)):
        _assert_parity(candles, full[start:])


# ---------------------------------------------------------------------------
# Phase 18 — prefix parity: bootstrap TIMING, not just the final state
# ---------------------------------------------------------------------------

_PREFIX_SCENARIOS = {
    "bull_natural": (BULL, NEUTRAL),
    "bear_natural": (BEAR, "103"),
    "trap_bull": (_TRAP_BULL, NEUTRAL),
    "trap_bear": (_TRAP_BEAR, _TRAP_BEAR_NEUTRAL),
    "tie": (_TIE, NEUTRAL),
}


@pytest.mark.parametrize("name", sorted(_PREFIX_SCENARIOS))
def test_prefix_parity(name: str) -> None:
    specs, neutral = _PREFIX_SCENARIOS[name]
    candles, swings = _build(specs, neutral)
    _assert_prefix_parity(candles, swings)


def test_prefix_parity_observes_the_moment_of_bootstrap() -> None:
    """A prefix walk is only meaningful if some prefix is UNDETERMINED and a
    later one is not."""
    candles, swings = _build(BULL)
    directions = [state[0] for state in _assert_prefix_parity(candles, swings)]
    assert directions[0] == DIR_UNDETERMINED
    assert directions[-1] == DIR_BULLISH
    assert DIR_UNDETERMINED in directions[:-1]


# ---------------------------------------------------------------------------
# Phase 19 — deterministic campaign
# ---------------------------------------------------------------------------

_CAMPAIGN = {
    # name: (specs, neutral)
    "undetermined_high_only": ([(H, "110", 2, 3), (L, "100", 4, 5),
                                (H, "112", 6, 7)], NEUTRAL),
    "undetermined_low_only": ([(L, "100", 2, 3), (H, "110", 4, 5),
                               (L, "102", 6, 7)], NEUTRAL),
    "bull_hl_then_hh": (BULL, NEUTRAL),
    "bull_hh_then_hl": ([(L, "100", 2, 3), (H, "110", 4, 5),
                         (L, "102", 6, 15), (H, "112", 8, 9)], NEUTRAL),
    "bear_lh_then_ll": (BEAR, "103"),
    "bear_ll_then_lh": ([(H, "110", 2, 3), (L, "100", 4, 5),
                         (H, "108", 6, 15), (L, "98", 8, 9)], "103"),
    "equal_high_blocks": ([(L, "100", 2, 3), (H, "110", 4, 5),
                           (L, "102", 6, 7), (H, "110.05", 8, 9)], NEUTRAL),
    "equal_low_blocks": ([(L, "100", 2, 3), (H, "110", 4, 5),
                          (L, "100.05", 6, 7), (H, "112", 8, 9)], NEUTRAL),
    "contradictory_hh_ll": ([(L, "100", 2, 3), (H, "110", 4, 5),
                             (L, "98", 6, 7), (H, "112", 8, 9)], NEUTRAL),
    "contradictory_lh_hl": ([(L, "100", 2, 3), (H, "110", 4, 5),
                             (L, "102", 6, 7), (H, "108", 8, 9)], NEUTRAL),
    "reversed_availability_bull": (_TRAP_BULL, NEUTRAL),
    "reversed_availability_bear": (_TRAP_BEAR, _TRAP_BEAR_NEUTRAL),
    "same_time_relationships": (_TIE, NEUTRAL),
    "once_only_bull": ([(L, "100", 2, 3), (H, "110", 4, 5),
                        (L, "102", 6, 7), (H, "112", 8, 9),
                        (L, "95", 10, 11), (H, "105", 12, 13)], NEUTRAL),
    "once_only_bear": ([(H, "110", 2, 3), (L, "100", 4, 5),
                        (H, "108", 6, 7), (L, "98", 8, 9),
                        (H, "107", 10, 11), (L, "99", 12, 13)], "103"),
    "late_supersession_bull": ([(L, "100", 2, 3), (H, "110", 4, 5),
                                (L, "98", 6, 7), (H, "112", 8, 9),
                                (L, "104", 10, 11), (H, "114", 12, 13)], NEUTRAL),
}


@pytest.mark.parametrize("name", sorted(_CAMPAIGN))
def test_campaign_matches_production_on_every_prefix(name: str) -> None:
    specs, neutral = _CAMPAIGN[name]
    candles, swings = _build(specs, neutral)
    _assert_prefix_parity(candles, swings)


def test_campaign_totals() -> None:
    """Report and pin the campaign's coverage. Fails on degeneration — a
    generator that stopped exercising a mode must not pass quietly."""
    comparisons = 0
    bullish = bearish = undetermined = 0
    for specs, neutral in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral)
        states = _assert_prefix_parity(candles, swings)
        comparisons += len(states)
        final = states[-1][0]
        if final == DIR_BULLISH:
            bullish += 1
        elif final == DIR_BEARISH:
            bearish += 1
        else:
            undetermined += 1

    assert len(_CAMPAIGN) == 16
    assert comparisons == 90
    assert bullish == 6, bullish
    assert bearish == 4, bearish
    assert undetermined == 6, undetermined
    assert bullish + bearish + undetermined == len(_CAMPAIGN)


def test_campaign_reaches_every_relationship_label() -> None:
    """The bootstrap contract is only exercised if all six labels occur somewhere
    in the campaign."""
    seen = set()
    for specs, neutral in _CAMPAIGN.values():
        _candles, swings = _build(specs, neutral)
        for rel in _pine_rels(swings):
            seen.add(rel[2])
    assert seen == {C_HH, C_LH, C_EH, C_HL, C_LL, C_EL}, seen


def test_campaign_never_fires_a_transition() -> None:
    for specs, neutral in _CAMPAIGN.values():
        candles, swings = _build(specs, neutral)
        analysis = _analyze(candles, swings)
        assert analysis.structure_transitions == ()
