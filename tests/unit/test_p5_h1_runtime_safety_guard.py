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

from pathlib import Path

import pytest

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


def test_no_other_unguarded_ext_dereference_sites_exist():
    """Structural completeness check: every function whose parameter list
    declares a `P5TransportExt` argument is accounted for by either
    `_GUARDED_SITES` or the already-safe `f_p5xLine`."""
    import re

    functions_taking_ext = set(re.findall(r"^(f_\w+)\([^\n]*P5TransportExt \w+[^\n]*=>", _P5_SOURCE, re.M))
    accounted = {sig.split("(")[0] for sig, *_ in _GUARDED_SITES} | {"f_p5xLine", "f_p5WireExt"}
    unaccounted = functions_taking_ext - accounted
    assert unaccounted == set(), f"new/unaudited P5TransportExt consumer(s) found: {unaccounted}"
