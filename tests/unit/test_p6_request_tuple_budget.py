"""The script-wide ``request.*`` tuple budget, measured before the P5 extension.

WHY THIS EXISTS
---------------
The P5 transport audit concluded that ~20 bounded values per timeframe must
cross the P6 boundary, taking the projection from 14 scalars to ~34. The obvious
implementation -- widen the destructuring -- is not available.

Pine limits the COMBINED number of tuple elements returned by ALL ``request.*``
calls in one script to 127. The limit is script-wide, so it is not enough to ask
whether one call is too wide; the whole inventory has to be counted.

WHAT THE INVENTORY SHOWS
------------------------
::

    P6 DEV     6 semantic requests x 14                        =  84
    P6 ATOMIC  6 semantic x 14  +  6 capture x 5   = 84 + 30   = 114

Two things follow, and the second is the one that would have been missed.

FINDING 1 -- the scalar widening is arithmetically impossible
--------------------------------------------------------------
6 x 34 = 204 in P6 DEV alone, and 234 in the atomic twin. Both are far past 127.
No amount of care in writing the destructuring makes this compile, which is why
the representation changed to a UDT rather than to a wider tuple.

FINDING 2 -- the ATOMIC twin is the binding constraint, not P6 DEV
-------------------------------------------------------------------
With the selected shape (14 scalars + 1 UDT per semantic request) P6 DEV lands
at 90, a comfortable 37 below the limit. The atomic twin lands at **120** --
seven elements of headroom, because it carries a second family of six requests
that P6 DEV does not have.

So the atomic capture return CANNOT simply gain a transport H1/H2 pair: 6 x 7
= 42 puts the twin at 132 and it stops compiling. When the atomic instrumentation
is extended, the new digest must ride inside a UDT (or through ``log.info``,
which is already how the raw rows travel), never as two more scalars. This test
exists so that is discovered here rather than at the compiler.

THE LIMIT IS NOT ONLY DOCUMENTED, IT IS BOUNDED FROM BELOW BY EVIDENCE
----------------------------------------------------------------------
The atomic twin at 114 combined elements compiled with 0 errors on TradingView
during the P6 closure campaign. So the real ceiling is >= 114 and the documented
127 is consistent with what this repository has actually observed. That matters
because it means the design headroom below is measured against a limit we have
approached, not merely read about.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"
P6_ATOMIC = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_atomic_parity.pine"

#: Pine's combined limit across every ``request.*`` call in one script.
PINE_COMBINED_TUPLE_LIMIT = 127

#: Observed to compile with 0 errors on TradingView (P6 atomic, closure run).
PROVEN_COMPILING_COMBINED_TOTAL = 114

#: The audit's field count -- what a scalar widening would have cost.
AUDITED_NEW_FIELDS = 20

_TUPLE_REQUEST = re.compile(r"^\[([^\]]+)\]\s*=\s*request\.", re.M)
_SCALAR_REQUEST = re.compile(r"^\s*\w[\w.<>\s]*\s+\w+\s*=\s*request\.", re.M)


def tuple_returns(source: str) -> list[int]:
    """Element count of every tuple-returning ``request.*`` call, in file order."""
    return [len(m.group(1).split(",")) for m in _TUPLE_REQUEST.finditer(source)]


def combined_elements(source: str) -> int:
    """The number the 127 limit actually governs.

    A scalar-returning ``request.*`` call contributes one element, so it is
    counted too -- neither file has one today, but a port that added one would
    otherwise slip past this budget unnoticed.
    """
    return sum(tuple_returns(source)) + len(_SCALAR_REQUEST.findall(source))


# ---------------------------------------------------------------------------
# The measured inventory
# ---------------------------------------------------------------------------


def test_p6_dev_returns_six_semantic_tuples_of_fifteen() -> None:
    """Fourteen preserved scalars plus one appended P5TransportExt object."""
    assert tuple_returns(P6_DEV.read_text(encoding="utf-8")) == [15] * 6


def test_p6_atomic_carries_a_second_family_of_six_capture_requests() -> None:
    """The reason the twin is the binding constraint: it repeats DEV's six
    semantic requests and adds six capture requests DEV does not have."""
    assert tuple_returns(P6_ATOMIC.read_text(encoding="utf-8")) == [15] * 6 + [5] * 6


def test_the_combined_totals() -> None:
    """P6 DEV carries the extension; the atomic twin has not been extended yet.

    Measured, never estimated -- the closure evidence quotes these numbers.
    """
    assert combined_elements(P6_DEV.read_text(encoding="utf-8")) == 90
    assert combined_elements(P6_ATOMIC.read_text(encoding="utf-8")) == 120


def test_both_files_are_inside_the_limit_today() -> None:
    for path in (P6_DEV, P6_ATOMIC):
        total = combined_elements(path.read_text(encoding="utf-8"))
        assert total <= PINE_COMBINED_TUPLE_LIMIT, (path.name, total)


def test_the_limit_is_bounded_from_below_by_an_observed_compile() -> None:
    """The twin compiled at 114 with 0 errors during the closure run, so the
    ceiling is at least that. It is a HISTORICAL observation, not a property of
    the current file -- which now stands at 120, above that floor and still
    below the documented cap."""
    assert PROVEN_COMPILING_COMBINED_TOTAL == 114
    assert PROVEN_COMPILING_COMBINED_TOTAL <= PINE_COMBINED_TUPLE_LIMIT
    assert (
        combined_elements(P6_ATOMIC.read_text(encoding="utf-8"))
        > PROVEN_COMPILING_COMBINED_TOTAL
    )


def test_the_extension_landed_where_the_projection_said_it_would() -> None:
    """The design projected 90 for P6 DEV before a line of it was written."""
    assert combined_elements(P6_DEV.read_text(encoding="utf-8")) == (
        6 * SELECTED_SEMANTIC_WIDTH
    )


# ---------------------------------------------------------------------------
# Finding 1 -- why the scalar widening was abandoned
# ---------------------------------------------------------------------------


def test_widening_the_scalar_tuple_would_break_both_files() -> None:
    widened = 14 + AUDITED_NEW_FIELDS
    assert widened == 34
    assert 6 * widened == 204
    assert 6 * widened > PINE_COMBINED_TUPLE_LIMIT
    assert 6 * widened + 30 > PINE_COMBINED_TUPLE_LIMIT


def test_even_one_extra_scalar_per_context_is_not_free() -> None:
    """The budget is spent six times over, so per-timeframe costs multiply."""
    assert 84 + 6 <= PINE_COMBINED_TUPLE_LIMIT
    assert 114 + 6 <= PINE_COMBINED_TUPLE_LIMIT


# ---------------------------------------------------------------------------
# Finding 2 -- the selected shape, and the trap inside it
# ---------------------------------------------------------------------------

SELECTED_SEMANTIC_WIDTH = 15  # 14 preserved scalars + one P5TransportExt object


def test_the_selected_shape_fits_p6_dev_comfortably() -> None:
    total = 6 * SELECTED_SEMANTIC_WIDTH
    assert total == 90
    assert PINE_COMBINED_TUPLE_LIMIT - total == 37


def test_the_selected_shape_fits_the_atomic_twin_but_only_just() -> None:
    """Projected at 120 before implementation, and measured at 120 after."""
    total = 6 * SELECTED_SEMANTIC_WIDTH + 6 * 5
    assert total == 120
    assert total <= PINE_COMBINED_TUPLE_LIMIT
    assert PINE_COMBINED_TUPLE_LIMIT - total == 7
    assert combined_elements(P6_ATOMIC.read_text(encoding="utf-8")) == total


def test_the_atomic_twin_cannot_afford_two_more_capture_scalars() -> None:
    """The atomic instrumentation gains a transport digest. Doing it as an H1/H2
    scalar pair costs 12 elements and stops the twin compiling, so the new digest
    must ride inside a UDT or through ``log.info``."""
    naive = 6 * SELECTED_SEMANTIC_WIDTH + 6 * (5 + 2)
    assert naive == 132
    assert naive > PINE_COMBINED_TUPLE_LIMIT


def test_a_capture_udt_restores_the_headroom() -> None:
    """One object per capture request instead of five scalars."""
    total = 6 * SELECTED_SEMANTIC_WIDTH + 6 * 1
    assert total == 96
    assert total <= PINE_COMBINED_TUPLE_LIMIT


def test_the_full_udt_fallback_would_fit_too() -> None:
    """The fallback if a mixed tuple+UDT return turns out unsupported: one object
    per request, carrying old 14 and new ~20 together."""
    assert 6 * 1 <= PINE_COMBINED_TUPLE_LIMIT
    assert 6 * 1 + 6 * 1 <= PINE_COMBINED_TUPLE_LIMIT


# ---------------------------------------------------------------------------
# The request COUNT contract is separate from the element budget
# ---------------------------------------------------------------------------


def test_no_new_request_context_is_introduced_by_the_extension() -> None:
    """The author declined six new P5 engines, so the call count is frozen even
    though the element budget has room."""
    dev = P6_DEV.read_text(encoding="utf-8")
    assert len(re.findall(r"=\s*request\.security\(", dev)) == 6
    atomic = P6_ATOMIC.read_text(encoding="utf-8")
    assert len(re.findall(r"=\s*request\.security\(", atomic)) == 12
