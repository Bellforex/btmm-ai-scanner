"""The requested contexts must actually be able to reach P1's warm-up.

THE BUG THIS EXISTS TO PREVENT FROM RETURNING
---------------------------------------------
`calc_bars_count` counts the bars a context is GIVEN, and one of them is always
the current, still-forming bar. The projection advances only on confirmed bars,
so a request of N yields N-1 confirmed. Measured live on TradingView at N=1250:
dataset 1250, confirmed 1249.

P1's publication guard is `confirmedBarCount >= C_P1_MIN_CALC_BARS` (1250), so a
1250-bar request can NEVER make a context warm. It is permanently one confirmed
bar short of the Wilder-ATR convergence the contract requires, and the symptom is
silent: the projection simply publishes nothing, forever, on every higher
timeframe.

The fix is a transport correction, not a semantic one. `C_P1_MIN_CALC_BARS`
remains 1250. The request envelope becomes 1251 -- the MINIMAL envelope yielding
1250 confirmed -- and is derived from the semantic minimum in the Pine source so
the two cannot drift apart.

Two things are deliberately kept distinct throughout, because conflating them is
exactly what hid the defect: the DATASET count (bars given, includes the forming
bar) and the CONFIRMED count (bars the projection has actually processed).
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P6_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"

#: P1's semantic minimum. This is a CONTRACT value and must not move.
SEMANTIC_MINIMUM = 1250

#: The host's validated execution horizon.
HOST_ENVELOPE = 1800


def _source() -> str:
    return P6_DEV.read_text(encoding="utf-8")


def _constant(name: str) -> int:
    match = re.search(rf"^int {name}\s*=\s*(\d+)", _source(), re.M)
    assert match, f"{name} not found as a literal"
    return int(match.group(1))


# ---------------------------------------------------------------------------
# The envelope arithmetic, modelled
# ---------------------------------------------------------------------------


def confirmed_bars(dataset_bars: int, *, forming: bool = True) -> int:
    """Bars the projection will have processed, given a dataset of that size.

    `forming` is the ordinary live case: the newest bar of the requested
    context has not closed, so `barstate.isconfirmed` is false for it and the
    projection's counter never counts it.
    """
    return dataset_bars - 1 if forming else dataset_bars


def is_warm(dataset_bars: int, *, forming: bool = True) -> bool:
    """The host's own guard, applied to a requested context."""
    return confirmed_bars(dataset_bars, forming=forming) >= SEMANTIC_MINIMUM


def test_a_1250_bar_request_is_never_warm() -> None:
    """The negative case. This is what was measured live, and it must stay
    detectable if anyone sets the envelope back."""
    assert confirmed_bars(1250) == 1249
    assert is_warm(1250) is False


def test_a_1251_bar_request_is_warm() -> None:
    """The positive case: the minimal envelope that satisfies the contract."""
    assert confirmed_bars(1251) == 1250
    assert is_warm(1251) is True


def test_1251_is_minimal() -> None:
    """Nothing smaller works, so no smaller value can be justified as adequate."""
    assert not any(is_warm(n) for n in range(1, 1251))
    assert is_warm(1251)


def test_the_forming_bar_is_the_whole_difference() -> None:
    """Phase 3: a forming requested bar must not increment the confirmed count.
    Without a forming bar the same dataset would already be warm, which is
    precisely why the defect was invisible to reasoning about dataset sizes."""
    assert is_warm(1250, forming=False) is True
    assert is_warm(1250, forming=True) is False


# ---------------------------------------------------------------------------
# The Pine source must encode exactly that
# ---------------------------------------------------------------------------


def test_the_semantic_minimum_is_unchanged() -> None:
    """The correction is to transport, never to the contract."""
    assert _constant("C_P1_MIN_CALC_BARS") == SEMANTIC_MINIMUM


def test_the_host_envelope_is_unchanged() -> None:
    assert _constant("C_P1_CALC_BARS") == HOST_ENVELOPE
    assert _constant("C_P6_HOST_CALC_BARS") == HOST_ENVELOPE
    assert re.search(
        r"indicator\([^)]*calc_bars_count = 1800", _source(), re.S
    ), "host declaration must still request 1800"


def test_the_request_envelope_is_derived_not_written() -> None:
    """Phase 4. A literal would let the two drift apart the next time the
    semantic minimum is discussed; deriving makes that impossible."""
    assert "int C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS + 1" in _source()
    assert not re.search(r"C_P6_REQUEST_CALC_BARS\s*=\s*\d+", _source()), (
        "the request envelope must not be a bare literal"
    )


def test_the_request_envelope_is_not_the_semantic_minimum() -> None:
    """The regression that matters: setting it back to exactly 1250 must fail."""
    assert not re.search(
        rf"C_P6_REQUEST_CALC_BARS\s*=\s*{SEMANTIC_MINIMUM}\b", _source()
    )
    assert "C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS\n" not in _source()


def test_the_derived_envelope_still_sits_below_the_host() -> None:
    """If the request ever exceeded the host, the host would follow it and every
    closed layer would leave the horizon it was validated on."""
    assert SEMANTIC_MINIMUM + 1 < HOST_ENVELOPE


def test_symmetry_with_the_host_was_not_taken() -> None:
    """Author decision: the contract is at least 1250 confirmed bars per
    context, not identical bar counts across contexts. Raising every request to
    1800 would buy no source-proven semantics and cost history, arrays and
    runtime six times over."""
    assert "C_P6_REQUEST_CALC_BARS = C_P1_CALC_BARS" not in _source()
    for call in re.findall(r"request\.security\([^\n]*", _source()):
        assert "calc_bars_count = C_P6_REQUEST_CALC_BARS" in call, call
        assert "1800" not in call, call


# ---------------------------------------------------------------------------
# Dataset and confirmed counts must stay separately observable
# ---------------------------------------------------------------------------


def test_both_counts_are_published_per_timeframe() -> None:
    """Conflating the two is what hid the defect, so both stay measurable."""
    source = _source()
    for tf in ("W1", "D1", "H4", "H1", "M15", "M5"):
        assert f'"P6_{tf}_dataset"' in source, f"dataset diagnostic missing: {tf}"
        assert f'"P6_{tf}_bars"' in source, f"confirmed diagnostic missing: {tf}"


def test_capacity_and_warmup_read_different_constants() -> None:
    """Capacity asks whether the context was GIVEN enough; warm-up asks whether
    it has CONFIRMED enough. Pointing both at one constant would recreate the
    conflation in a new form."""
    source = _source()
    assert "dataset >= C_P6_REQUEST_CALC_BARS" in source
    assert "bars >= C_P1_MIN_CALC_BARS" in source
