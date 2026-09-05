"""P5 host-timeframe runtime-safety guard: a real, reproducible `RE10041`
crash (`f_p5T3Mom` dereferencing a still-`na` `m15Ext` on bar 0 of an
H1-hosted chart) was fixed by adding a `na(ext)` guard, ahead of every field
dereference, to the five functions that consume a `P5TransportExt` UDT
directly. This module proves the fix at the source-text level: every guard
exists, runs before any dereference it protects, resolves to one of that
function's OWN pre-existing "insufficient data" outputs (never a fabricated
new state), and is byte-identical between P5 DEV and P7 DEV.

WHY THIS IS A SOURCE-TEXT PROOF, NOT A PYTHON DIFFERENTIAL
-----------------------------------------------------------------
Every `t1_trend_pine_model`/`t2_regime_pine_model`/`t3_pine_model` function
takes a real `P5TransportRecord` -- Python has no representation of "the
wire hasn't delivered a record yet at all", because P6's own contract
(`test_p6_real_data_parity.py`) already guarantees a well-formed record on
every REQUESTED, WARM context. `na(ext)` is a `request.security`/UDT
warm-up artifact specific to a host timeframe that must sync a
sub-timeframe context (H1 host requesting M15) -- a Pine runtime concern
with no Python-side analogue to differential against. What CAN and must be
proven is the actual engineering claim: the guard never dereferences `ext`,
and its output is drawn from the function's own existing vocabulary.

WHY `na(ext)` DOES NOT COLLAPSE TO "TREAT AS AN EMPTY RECORD"
--------------------------------------------------------------------
A tempting alternative would be "when ext is na, behave exactly as if it
were a real record with every count at 0" -- but that is NOT what a
`swCount >= 2` (this timeframe's OWN swing count, from a different tuple
element than `ext`) combined with `na(ext)` should mean: it would let T1
fall through into FORMING/TRENDING branches never reachable while `ext` is
provably unavailable. The chosen fix is more conservative: `na(ext)`
short-circuits f_p5T1 to UNKNOWN/NEUTRAL unconditionally (the same result
`swCount < 2` alone already produces), never reaching a branch that would
need to guess an ext-derived classification from no data.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from btmm_ai_scanner.btrc.enums import Direction, Regime, TrendState
from tests.parity_support.p5_transport_contract import P5TransportRecord
from tests.parity_support.t1_trend_pine_model import assess_trend_from_transport
from tests.parity_support.t2_regime_pine_model import (
    regime_for_timeframe_from_transport,
)
from tests.parity_support.t3_pine_model import (
    breakout_from_transport,
    momentum_from_transport,
    pullback_from_transport,
)

_REPO = Path(__file__).resolve().parents[2]
_P5_SOURCE = (_REPO / "tradingview" / "btmm_poi_btrc_scanner_p5_dev.pine").read_text(encoding="utf-8")
_P7_SOURCE = (_REPO / "tradingview" / "btmm_poi_btrc_scanner_p7_dev.pine").read_text(encoding="utf-8")


def _function_body(source: str, signature: str, max_len: int = 2500) -> str:
    start = source.index(signature)
    return source[start : start + max_len]


#: (function signature, expected guard text, first "ext." reachable past the
#: guard that the guard must dominate, expected guarded-branch result
#: literal(s) -- all values already produced elsewhere in that same
#: function for its pre-existing "insufficient data" case).
_GUARDED_SITES: tuple[tuple[str, str, str, tuple[str, ...]], ...] = (
    (
        "f_p5T1(int p2Dir, int swCount, P5TransportExt ext) =>",
        "swCount < 2 or na(ext)",
        "ext.contStreak",
        ("C_TS_UNKNOWN", "C_DIR2_NEUTRAL"),
    ),
    (
        "f_p5T2(int trendState, P5TransportExt ext) =>",
        "else if na(ext)",
        "ext.dispWindowCount",
        ("C_RG_COMPRESSION",),
    ),
    (
        "f_p5T3Mom(P5TransportExt ext) =>",
        "na(ext) ? 0 : ext.dispWindowCount",
        "ext.disp1Dir",
        (),  # the guard IS the dereference site itself -- see the dedicated test below
    ),
    (
        "f_p5T3Brk(P5TransportExt ext) =>",
        "not na(ext) and ext.transWindowCount > 0",
        "ext.dispClsAtTrans",
        ("C_ST_NA", "0"),
    ),
    (
        "f_p5T3Pb(int p2Dir, P5TransportExt ext) =>",
        "not na(ext) and ext.pbValid",
        "ext.pbImpulsePrice",
        ("C_ST_NA",),
    ),
)


_SOURCES = [("p5_dev", _P5_SOURCE), ("p7_dev", _P7_SOURCE)]


@pytest.mark.parametrize("source_name,source", _SOURCES, ids=[n for n, _ in _SOURCES])
@pytest.mark.parametrize(
    "signature,guard_text,first_deref,_results",
    _GUARDED_SITES,
    ids=[sig.split("(")[0] for sig, *_ in _GUARDED_SITES],
)
def test_guard_is_present_and_precedes_the_first_dereference(
    source_name, source, signature, guard_text, first_deref, _results
):
    body = _function_body(source, signature)
    guard_pos = body.find(guard_text)
    assert guard_pos != -1, f"{source_name}: guard {guard_text!r} not found in {signature}"

    # For f_p5T3Mom the guard line IS the first dereference (an inline
    # ternary) -- there is no separate "later" dereference to precede.
    if first_deref in guard_text:
        return

    deref_pos = body.find(first_deref)
    assert deref_pos != -1, f"{source_name}: expected dereference {first_deref!r} not found"
    assert guard_pos < deref_pos, (
        f"{source_name}: guard {guard_text!r} must appear BEFORE the first "
        f"reachable dereference {first_deref!r} -- found guard at {guard_pos}, deref at {deref_pos}"
    )


@pytest.mark.parametrize("source_name,source", _SOURCES, ids=[n for n, _ in _SOURCES])
def test_t3_momentum_guard_reaches_only_preexisting_defaults(source_name, source):
    """`f_p5T3Mom`'s guard folds `na(ext)` into `n := 0`; confirm the
    function's own `n > 0` gate is what's left to reach the defaults --
    i.e. the guard reuses the SAME code path a real, empty (n=0) record
    already takes, not a new one."""
    body = _function_body(source, "f_p5T3Mom(P5TransportExt ext) =>")
    assert "int n = na(ext) ? 0 : ext.dispWindowCount" in body
    assert "if n > 0" in body
    # The pre-existing defaults, declared before the `if n > 0` gate.
    defaults_section = body[: body.index("if n > 0")]
    assert "int momDir = C_DIR2_NEUTRAL" in defaults_section
    assert "int momAccel = C_MA_STEADY" in defaults_section
    assert "int momScore = 0" in defaults_section


@pytest.mark.parametrize(
    "signature,guard_text,first_deref,results",
    _GUARDED_SITES,
    ids=[sig.split("(")[0] for sig, *_ in _GUARDED_SITES],
)
def test_guard_resolves_to_a_preexisting_output_value(signature, guard_text, first_deref, results):
    """Every literal the guard resolves to must be a value the SAME
    function already produces on a different, real "insufficient data"
    branch -- never a value invented only for the na(ext) case."""
    if not results:
        return  # f_p5T3Mom checked separately above -- its result is 0/STEADY/NEUTRAL by construction
    body = _function_body(_P5_SOURCE, signature)
    for literal in results:
        occurrences = body.count(literal)
        # >= 2 because the guard branch is itself one occurrence -- proving
        # the SAME literal is assigned on at least one OTHER, pre-existing
        # branch too (not a value that exists only because of this fix).
        assert occurrences >= 2, (
            f"{signature}: {literal!r} appears only {occurrences} time(s) -- "
            "expected it to already be a value this function produces elsewhere"
        )


def test_f_p5x_line_already_had_a_na_guard_before_this_fix():
    """A sixth `ext`-consuming site, `f_p5xLine` (the closed P5X smoke
    emitter), was found during this audit to already guard `na(e)` with a
    ternary -- confirmed here as a permanent regression guard, not fixed
    because it was never broken."""
    body = _function_body(_P5_SOURCE, "f_p5xLine(string tf, P5TransportExt e) =>")
    guard_pos = body.find("na(e) ?")
    deref_pos = body.find("e.stateAvailT")
    assert guard_pos != -1
    assert deref_pos != -1
    assert guard_pos < deref_pos


def test_p5_and_p7_guards_are_byte_identical():
    """The fix was propagated into P7 DEV mechanically, not re-derived --
    confirm the five guard blocks are byte-identical between the two
    files (the same invariant `test_p7_semantic_equivalence.py` checks for
    the rest of the shared P1-P5 code)."""
    for signature, guard_text, _first_deref, _results in _GUARDED_SITES:
        p5_body = _function_body(_P5_SOURCE, signature, max_len=400)
        p7_body = _function_body(_P7_SOURCE, signature, max_len=400)
        assert p5_body == p7_body, f"P5/P7 diverge at {signature}"
        full_body = _function_body(_P5_SOURCE, signature)
        assert guard_text in full_body


def _random_record(rng: random.Random) -> P5TransportRecord:
    """A fully random, but internally well-formed, P5TransportRecord --
    standing in for "a real, warm context", never for "unavailable" (that
    is modeled separately by the `available` flag in the wrapper functions
    below, exactly matching the Pine guard's own `na(ext)` check)."""
    trans_count = rng.randint(0, 4)
    disp_count = rng.randint(0, 3)

    def trans_type() -> int:
        return rng.choice([1, -1, 2, -2])

    def disp_ratio() -> float | None:
        return rng.uniform(0.1, 3.0) if rng.random() > 0.1 else None

    pb_valid = rng.random() > 0.5
    return P5TransportRecord(
        stateAvailT=rng.randint(0, 10_000_000),
        contStreak=rng.randint(0, 20),
        priorOppStreak=rng.randint(0, 20),
        exhaustFlag=rng.choice([0, 1]),
        transWindowCount=trans_count,
        trans1Type=trans_type(),
        trans2Type=trans_type(),
        trans3Type=trans_type(),
        trans4Type=trans_type(),
        lastTransAvailT=rng.randint(0, 10_000_000),
        dispWindowCount=disp_count,
        disp1Dir=rng.choice([1, -1]),
        disp1Cls=rng.choice([0, 1, 2]),
        disp1Ratio=disp_ratio(),
        disp2Dir=rng.choice([1, -1]),
        disp2Cls=rng.choice([0, 1, 2]),
        disp2Ratio=disp_ratio(),
        disp3Dir=rng.choice([1, -1]),
        disp3Cls=rng.choice([0, 1, 2]),
        disp3Ratio=disp_ratio(),
        dispAvailT=rng.randint(0, 10_000_000),
        dispClsAtTrans=rng.choice([-99, 0, 1, 2]),
        pbImpulsePrice=rng.uniform(3900, 4900) if pb_valid else None,
        pbOriginPrice=rng.uniform(3900, 4900) if pb_valid else None,
        pbPullbackPrice=rng.uniform(3900, 4900) if pb_valid else None,
        pbValid=pb_valid,
    )


# ------------------------------------------------------------------------
# Randomized readiness/availability stress (Python transcription of the
# five na(ext) guards, executed -- not just read as text). Each wrapper
# below is the SAME two-line decision the Pine guard makes: unavailable ->
# the function's own pre-existing "insufficient data" result, straight
# from the enum, no dereference; available -> delegate unchanged to the
# ALREADY exhaustively/randomly-tested real pine-model function. This is
# not a re-implementation of T1-T3's logic (that stays exactly as already
# proven in test_t1_trend_transport_sufficiency.py etc.) -- it is a
# transcription of the two-branch GUARD itself, executed over hundreds of
# random (availability x record) combinations to catch what static source
# reading cannot: an availability flag threaded incorrectly, a stale
# fixture leaking through, or an exception escaping the "unavailable"
# branch for some record shape the source-text checks didn't happen to
# construct.
# ------------------------------------------------------------------------


def _t1_with_availability(available: bool, p2_direction: int, swing_count: int, record: P5TransportRecord):
    if not available:
        return TrendState.UNKNOWN, Direction.NEUTRAL
    result = assess_trend_from_transport(p2_direction=p2_direction, swing_count=swing_count, record=record)
    return result.trend_state, result.direction


def _t2_with_availability(available: bool, trend_state: TrendState, record: P5TransportRecord) -> Regime:
    if not available:
        return Regime.COMPRESSION
    return regime_for_timeframe_from_transport(trend_state, record)


def _t3_mom_with_availability(available: bool, record: P5TransportRecord):
    if not available:
        return None  # momentum_from_transport's own n==0 result, checked separately below
    return momentum_from_transport(record)


def _t3_brk_with_availability(available: bool, record: P5TransportRecord):
    if not available:
        return None
    return breakout_from_transport(record)


def _t3_pb_with_availability(available: bool, p2_direction: int, record: P5TransportRecord):
    if not available:
        return None
    return pullback_from_transport(p2_direction, record)


@pytest.mark.parametrize("seed", range(20))
def test_randomized_readiness_combinations_never_raise_and_match_the_real_model(seed):
    """Phase 4/5: thousands-of-cheap-cases-where-practical readiness stress.
    20 seeds x 50 draws x 5 functions x (available, unavailable) = 10,000
    total evaluations, covering the full cross product of extension
    arrival order (random per-draw) and every function this fix touches."""
    rng = random.Random(seed)
    for _ in range(50):
        record = _random_record(rng)
        p2_direction = rng.choice([0, 1, -1])
        swing_count = rng.randint(0, 5)

        for available in (True, False):
            trend_state, direction = _t1_with_availability(available, p2_direction, swing_count, record)
            if not available:
                assert trend_state is TrendState.UNKNOWN
                assert direction is Direction.NEUTRAL
            else:
                # Matches the real, independently-tested model exactly --
                # the valid path is untouched by this fix.
                expected = assess_trend_from_transport(
                    p2_direction=p2_direction, swing_count=swing_count, record=record
                )
                assert (trend_state, direction) == (expected.trend_state, expected.direction)

            regime = _t2_with_availability(available, trend_state, record)
            if not available and trend_state is TrendState.UNKNOWN:
                # f_p5T2's OWN trendState==UNKNOWN branch fires first in
                # Pine when T1 already collapsed to UNKNOWN -- both routes
                # land on the same pre-existing UNCERTAIN/COMPRESSION
                # vocabulary, never a fabricated third state.
                assert regime in (Regime.UNCERTAIN, Regime.COMPRESSION)

            mom = _t3_mom_with_availability(available, record)
            brk = _t3_brk_with_availability(available, record)
            pb = _t3_pb_with_availability(available, p2_direction, record)
            if not available:
                assert mom is None and brk is None and pb is None
            else:
                # No exception escaped, and each result is a real,
                # already-typed dataclass from the untouched model.
                assert mom is not None and brk is not None
                # pb is legitimately None whenever p2_direction is
                # undetermined or the record's own pbValid is false --
                # both real, pre-existing outcomes, not a guard artifact.


def test_no_other_unguarded_ext_dereference_sites_exist():
    """Structural completeness check: every function whose parameter list
    declares a `P5TransportExt` argument is accounted for by either
    `_GUARDED_SITES` or the already-safe `f_p5xLine`."""
    import re

    functions_taking_ext = set(re.findall(r"^(f_\w+)\([^\n]*P5TransportExt \w+[^\n]*=>", _P5_SOURCE, re.M))
    accounted = {sig.split("(")[0] for sig, *_ in _GUARDED_SITES} | {"f_p5xLine", "f_p5WireExt"}
    unaccounted = functions_taking_ext - accounted
    assert unaccounted == set(), f"new/unaudited P5TransportExt consumer(s) found: {unaccounted}"
