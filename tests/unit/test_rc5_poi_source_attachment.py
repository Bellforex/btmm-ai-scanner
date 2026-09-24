"""A POI must be drawn on the candles that created it, not where it became tradable.

The author's contract: every drawn POI begins on the exact candle or candles
that produced it, carries the exact detector price measurement, may extend
forward while active, and never detaches from its origin.

The zone renderer used to anchor `box.new(left = ...)` to `poiAvailTime`. The
record type says what that field is:

    int availTime      // == confirmTime for every production detector
    int srcFirstTime   // identity: first source candle event time (ms)

So every zone was drawn at the bar where it became tradable -- one or more bars
to the RIGHT of the formation. WHEN, not WHERE. The registry already carried
`poiSrcFirst`; the renderer simply read the wrong array.

These are static assertions against the Pine source because the renderer is
Pine, and a Pine box cannot be exercised from Python.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CORE = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_user.pine"


def _core() -> str:
    return _CORE.read_text(encoding="utf-8")


def _zone_box_new() -> str:
    """The one box.new in the P7-Z zone renderer, with its continuation lines.

    Pine wraps the call across four lines, so a single-line grab would miss
    `extend = extend.right` and silently weaken the assertions.
    """
    lines = _core().splitlines()
    starts = [
        i
        for i, line in enumerate(lines)
        if "box.new(" in line and "p7zNewBox" in line
    ]
    assert len(starts) == 1, f"expected exactly one zone box.new, got {len(starts)}"
    i = starts[0]
    return chr(10).join(lines[i : i + 4])


def test_THE_ZONE_ORIGIN_IS_THE_SOURCE_FORMATION() -> None:
    """THE contract. The left edge is the record's own source instant.

    For every family that is `poiSrcFirst`. S/R is the documented exception and
    is asserted separately below; it reads `poiCandTime`, which is where its
    origin pivot is carried.
    """
    call = _zone_box_new()
    assert "left = array.get(p7zIsSr ? poiCandTime : poiSrcFirst, p7zPoiI)" in call
    assert "poiSrcFirst" in call, "non-S/R types must anchor on srcFirst"


def test_the_zone_origin_is_never_an_availability_or_clock_time() -> None:
    """Named explicitly so a future edit cannot quietly reintroduce any of them."""
    call = _zone_box_new()
    left = call.split("left =", 1)[1].split(", top =", 1)[0]
    for forbidden in (
        "poiAvailTime",
        "time_close",
        "time_open",
        "timenow",
        "bar_index",
        "poiFirstTouchT",
    ):
        assert forbidden not in left, (
            f"zone origin must not be {forbidden}: WHEN is not WHERE"
        )
    # poiCandTime is permitted ONLY as the S/R branch of the ternary, never as
    # the unconditional origin -- for every other family candidateTime is not
    # the contract and must not creep in.
    if "poiCandTime" in left:
        assert "p7zIsSr ? poiCandTime :" in left, (
            "candidateTime may only be the S/R display-origin exception"
        )


def test_the_zone_price_edges_are_the_detector_measurement() -> None:
    """Top and bottom come from the frozen detector, not renderer geometry."""
    call = _zone_box_new()
    assert "top = array.get(poiZoneTop, p7zPoiI)" in call
    assert "bottom = array.get(poiZoneBottom, p7zPoiI)" in call
    for forbidden in ("high", "low", "close[", "open[", "math.avg"):
        segment = call.split("top =", 1)[1].split("xloc", 1)[0]
        assert forbidden not in segment, f"price edge derived from {forbidden}"


def test_an_active_zone_may_still_extend_forward() -> None:
    """Pinning the origin must not have frozen the right edge."""
    core = _core()
    assert "extend = extend.right" in _zone_box_new()
    assert "box.set_right(array.get(p7zBoxes, slot), p7zRightEdge)" in core


def test_the_source_span_fields_exist_and_are_populated_from_the_record() -> None:
    core = _core()
    for field in ("poiSrcFirst", "poiSrcLast", "poiSrcCount"):
        assert f"var array<int>   {field}" in core or f"{field} " in core, field
    assert "array.push(poiSrcFirst, rec.srcFirstTime)" in core
    assert "array.push(poiSrcLast, rec.srcLastTime)" in core


def test_srcFirst_is_documented_as_the_first_source_candle() -> None:
    """If this comment ever changes meaning, the contract changed."""
    core = _core()
    assert re.search(
        r"int\s+srcFirstTime\s+// identity: first source candle event time", core
    )
    assert re.search(
        r"int\s+availTime\s+// == confirmTime for every production detector", core
    )


# ---------------------------------------------------------------------------
# S/R -- the one family whose identity is deliberately not its origin
# ---------------------------------------------------------------------------


def test_SR_DRAWS_AT_ITS_ORIGIN_SWING_NOT_ITS_CONFIRMATION() -> None:
    """Support/Resistance is the documented exception.

    `f_poiDetectReferenceZones` emits with (srcFirst, count, srcLast) all set
    to `confirmationTime`, because that triple is POI IDENTITY and the
    collision fix depends on it. The real source instant -- the origin swing's
    pivot-end candle -- is carried in `candidateTime`.

    So anchoring the renderer to srcFirst, correct for every other family,
    would still land S/R on its confirmation bar. The display origin, and only
    the display origin, reads candidateTime for these two types.
    """
    call = _zone_box_new()
    assert "left = array.get(p7zIsSr ? poiCandTime : poiSrcFirst, p7zPoiI)" in call


def test_the_sr_predicate_is_exactly_the_two_reference_types() -> None:
    core = _core()
    assert (
        "bool p7zIsSr = ty2 == C_POI_SUPPORT_ZONE or ty2 == C_POI_RESISTANCE_ZONE"
        in core
    )


def test_the_sr_identity_triple_was_not_touched() -> None:
    """The fix is presentation. Identity must still be confirmationTime.

    If this ever changes, dedup and `f_poiFind` change with it, and that is a
    semantic change requiring a parity re-run -- not a renderer edit.
    """
    core = _core()
    emit = [
        line for line in core.splitlines() if "f_poiEmit(typeCode, direction, z." in line
    ]
    assert len(emit) == 1, emit
    assert (
        "C_POI_TIER_NA, z.confirmationTime, 1, z.confirmationTime, "
        "z.originPivotEndTime, z.confirmationTime" in emit[0]
    ), emit[0]


def test_candidate_time_really_is_the_origin_pivot_for_sr() -> None:
    """The renderer's S/R origin is only correct because of this wiring."""
    core = _core()
    # candidateTime receives originPivotEndTime at the S/R emit
    assert "z.originPivotEndTime, z.confirmationTime)" in core
    # and originPivotEndTime is a real bar time, not a synthetic id
    assert "int   pivotEndTime         // event/open time of pivot end candle" in core
    assert (
        "int   originPivotEndTime   // RC3: origin swing's pivot-end candle "
        "== the zone's SOURCE instant" in core
    )
