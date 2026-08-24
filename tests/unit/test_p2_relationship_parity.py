"""Parity between the Pine P2-I3 relationship algorithm and production Python.

Pine cannot run locally, so `_pine_model` below is a faithful **test-side**
transcription of `f_p2ClassifyRelationship` / `f_p2BuildRelationships` from
`tradingview/btmm_poi_btrc_scanner_v1.pine`. It is compared against the real
production function, `structure.relationships.detect_swing_relationships`.

The model is test support only. It is deliberately NOT importable by application
code, and it must never become the thing under test — production Python is
always the reference side of every assertion.

What the model reproduces, and why each detail matters:

* tolerance uses the **current** swing's `pivot_reference_atr` — a predecessor or
  median implementation would classify differently near the band edge;
* comparisons are **strict**, so exactly +tol and exactly -tol are EQUAL;
* swings are grouped **per type**, so the predecessor is the previous swing of
  the same type (never two-back arithmetic);
* output order is **all highs, then all lows** — Python filters `highs` then
  `lows` and appends in that order, so an interleaved build would diverge;
* relationship availability is `max` of the two confirmation times.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import SwingRelationshipLabel
from btmm_ai_scanner.structure.relationships import detect_swing_relationships

_SIB = importlib.util.spec_from_file_location(
    "_p2_rel_fixtures",
    Path(__file__).with_name("test_structure_transitions_contract.py"),
)
assert _SIB is not None and _SIB.loader is not None
_fx = importlib.util.module_from_spec(_SIB)
sys.modules[_SIB.name] = _fx
_SIB.loader.exec_module(_fx)

_series = _fx._series
_swing = _fx._swing

CONFIG = StructureConfiguration()
TOL_MULT = CONFIG.swing_relationship_equal_tolerance_atr_multiplier

# Pine int codes, mirrored from the production source.
C_ST_REL = {
    SwingRelationshipLabel.HIGHER_HIGH: 1,
    SwingRelationshipLabel.LOWER_HIGH: -1,
    SwingRelationshipLabel.EQUAL_HIGH: 10,
    SwingRelationshipLabel.HIGHER_LOW: 2,
    SwingRelationshipLabel.LOWER_LOW: -2,
    SwingRelationshipLabel.EQUAL_LOW: 20,
}
SWING_HIGH, SWING_LOW = 1, -1


# ---------------------------------------------------------------------------
# Test-side transcription of the Pine algorithm
# ---------------------------------------------------------------------------

class _View:
    """Mirror of Pine `StructSwingView`."""

    __slots__ = ("stableKey", "swingType", "pivotPrice", "referenceAtr",
                 "meaningfulConfTime")

    def __init__(self, swing) -> None:
        self.stableKey = swing.pivot_end_time_utc          # == SwingRec.pivotEndTime
        self.swingType = (
            SWING_HIGH if swing.swing_type == SwingType.SWING_HIGH else SWING_LOW
        )
        self.pivotPrice = swing.pivot_price
        self.referenceAtr = swing.pivot_reference_atr
        self.meaningfulConfTime = swing.meaningful_confirmation_time_utc


def _pine_classify(cur: _View, prev: _View) -> int:
    """f_p2ClassifyRelationship."""
    if cur.swingType != prev.swingType:
        return -99                                        # C_ST_NA
    tol = TOL_MULT * cur.referenceAtr                      # CURRENT swing's ATR
    is_high = cur.swingType == SWING_HIGH
    if cur.pivotPrice > prev.pivotPrice + tol:             # strict
        return 1 if is_high else 2
    if cur.pivotPrice < prev.pivotPrice - tol:             # strict
        return -1 if is_high else -2
    return 10 if is_high else 20


def _pine_model(swings) -> list[tuple]:
    """f_p2BuildRelationships -> [(swingKey, prevKey, code, availability)]."""
    views = [_View(s) for s in swings]
    out: list[tuple] = []
    for want in (SWING_HIGH, SWING_LOW):                   # highs pass, then lows
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
                    )
                )
            prev_idx = i
    return out


def _python_reference(swings) -> list[tuple]:
    """Same projection, from the production function."""
    return [
        (
            c.current_swing.pivot_end_time_utc,
            c.predecessor_swing.pivot_end_time_utc,
            C_ST_REL[c.label],
            c.availability_time_utc,
        )
        for c in detect_swing_relationships(tuple(swings), CONFIG)
    ]


def _assert_parity(swings) -> list[tuple]:
    reference = _python_reference(swings)
    assert _pine_model(swings) == reference
    return reference


# ---------------------------------------------------------------------------
# Boundary cases — Decimal-exact, so equality is never ambiguous
# ---------------------------------------------------------------------------
# atr 2.0 -> tol = 0.10 * 2.0 = 0.20 exactly in Decimal.

ATR = "2.0"
TOL = Decimal("0.20")
BASE_HIGH = Decimal("110.00")
BASE_LOW = Decimal("100.00")


def _pair(swing_type: SwingType, base: Decimal, delta: Decimal):
    candles = _series("105")
    a, b = (2, 4) if swing_type == SwingType.SWING_HIGH else (2, 4)
    return (
        _swing(1, swing_type, str(base), a, 3, candles, reference_atr=ATR),
        _swing(2, swing_type, str(base + delta), b, 5, candles, reference_atr=ATR),
    )


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (TOL + Decimal("0.01"), SwingRelationshipLabel.HIGHER_HIGH),
        (TOL, SwingRelationshipLabel.EQUAL_HIGH),
        (Decimal("0"), SwingRelationshipLabel.EQUAL_HIGH),
        (-TOL, SwingRelationshipLabel.EQUAL_HIGH),
        (-TOL - Decimal("0.01"), SwingRelationshipLabel.LOWER_HIGH),
    ],
)
def test_high_boundaries(delta, expected) -> None:
    swings = _pair(SwingType.SWING_HIGH, BASE_HIGH, delta)
    got = _assert_parity(swings)
    assert len(got) == 1
    assert got[0][2] == C_ST_REL[expected]


@pytest.mark.parametrize(
    ("delta", "expected"),
    [
        (TOL + Decimal("0.01"), SwingRelationshipLabel.HIGHER_LOW),
        (TOL, SwingRelationshipLabel.EQUAL_LOW),
        (Decimal("0"), SwingRelationshipLabel.EQUAL_LOW),
        (-TOL, SwingRelationshipLabel.EQUAL_LOW),
        (-TOL - Decimal("0.01"), SwingRelationshipLabel.LOWER_LOW),
    ],
)
def test_low_boundaries(delta, expected) -> None:
    swings = _pair(SwingType.SWING_LOW, BASE_LOW, delta)
    got = _assert_parity(swings)
    assert len(got) == 1
    assert got[0][2] == C_ST_REL[expected]


# ---------------------------------------------------------------------------
# Current-ATR asymmetry — decisive
# ---------------------------------------------------------------------------
# previous atr 50 (band +/-5.00), current atr 2 (band +/-0.20), delta +0.21.
# Correct -> HIGHER. A predecessor-ATR implementation -> EQUAL.

@pytest.mark.parametrize(
    ("swing_type", "base", "expected"),
    [
        (SwingType.SWING_HIGH, BASE_HIGH, SwingRelationshipLabel.HIGHER_HIGH),
        (SwingType.SWING_LOW, BASE_LOW, SwingRelationshipLabel.HIGHER_LOW),
    ],
)
def test_tolerance_uses_current_swing_atr(swing_type, base, expected) -> None:
    candles = _series("105")
    swings = (
        _swing(1, swing_type, str(base), 2, 3, candles, reference_atr="50.0"),
        _swing(2, swing_type, str(base + Decimal("0.21")), 4, 5, candles,
               reference_atr="2.0"),
    )
    got = _assert_parity(swings)
    assert got[0][2] == C_ST_REL[expected], (
        "a predecessor-ATR or median-ATR implementation would return EQUAL here"
    )


# ---------------------------------------------------------------------------
# Insufficient history
# ---------------------------------------------------------------------------

def test_no_swings_yields_no_relationships() -> None:
    assert _assert_parity(()) == []


@pytest.mark.parametrize("swing_type", [SwingType.SWING_HIGH, SwingType.SWING_LOW])
def test_single_swing_yields_no_relationship(swing_type) -> None:
    candles = _series("105")
    swings = (_swing(1, swing_type, "105", 2, 3, candles, reference_atr=ATR),)
    assert _assert_parity(swings) == []


def test_one_of_each_type_yields_no_relationship() -> None:
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_LOW, "100", 4, 5, candles, reference_atr=ATR),
    )
    assert _assert_parity(swings) == []


def test_three_alternating_starting_high_yields_one_high_relationship() -> None:
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_LOW, "100", 4, 5, candles, reference_atr=ATR),
        _swing(3, SwingType.SWING_HIGH, "112", 6, 7, candles, reference_atr=ATR),
    )
    got = _assert_parity(swings)
    assert len(got) == 1
    assert got[0][2] == C_ST_REL[SwingRelationshipLabel.HIGHER_HIGH]


def test_three_alternating_starting_low_yields_one_low_relationship() -> None:
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles, reference_atr=ATR),
        _swing(3, SwingType.SWING_LOW, "102", 6, 7, candles, reference_atr=ATR),
    )
    got = _assert_parity(swings)
    assert len(got) == 1
    assert got[0][2] == C_ST_REL[SwingRelationshipLabel.HIGHER_LOW]


def test_four_alternating_yields_two_relationships() -> None:
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles, reference_atr=ATR),
        _swing(3, SwingType.SWING_LOW, "102", 6, 7, candles, reference_atr=ATR),
        _swing(4, SwingType.SWING_HIGH, "112", 8, 9, candles, reference_atr=ATR),
    )
    assert len(_assert_parity(swings)) == 2


# ---------------------------------------------------------------------------
# Availability and ordering
# ---------------------------------------------------------------------------

def test_availability_is_the_later_of_the_two_confirmations() -> None:
    candles = _series("105")
    first = _swing(1, SwingType.SWING_HIGH, "110", 2, 3, candles, reference_atr=ATR)
    second = _swing(2, SwingType.SWING_HIGH, "112", 4, 9, candles, reference_atr=ATR)
    assert first.availability_time_utc != second.availability_time_utc, (
        "the two confirmations must differ or equality could mask a wrong pick"
    )
    got = _assert_parity((first, second))
    assert got[0][3] == max(
        first.availability_time_utc, second.availability_time_utc
    )


def test_same_confirmation_time_is_handled_identically() -> None:
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 2, 5, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_HIGH, "112", 4, 5, candles, reference_atr=ATR),
    )
    got = _assert_parity(swings)
    assert got[0][3] == swings[0].availability_time_utc


def test_output_order_is_all_highs_then_all_lows() -> None:
    """Not chronologically interleaved — Python appends the highs group first."""
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles, reference_atr=ATR),
        _swing(3, SwingType.SWING_LOW, "102", 6, 7, candles, reference_atr=ATR),
        _swing(4, SwingType.SWING_HIGH, "112", 8, 9, candles, reference_atr=ATR),
    )
    got = _assert_parity(swings)
    assert [code for _, _, code, _ in got] == [
        C_ST_REL[SwingRelationshipLabel.HIGHER_HIGH],
        C_ST_REL[SwingRelationshipLabel.HIGHER_LOW],
    ], "high relationship must precede low relationship"


def test_window_advancement_drops_the_predecessor_without_hidden_state() -> None:
    """Pine must classify exactly the bounded list it is given, as Python does.

    Trimming the oldest same-type swing must reduce the relationship count — if
    Pine retained a predecessor behind P1's window it would keep emitting one.
    """
    candles = _series("105")
    full = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles, reference_atr=ATR),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles, reference_atr=ATR),
        _swing(3, SwingType.SWING_LOW, "102", 6, 7, candles, reference_atr=ATR),
        _swing(4, SwingType.SWING_HIGH, "112", 8, 9, candles, reference_atr=ATR),
    )
    assert len(_assert_parity(full)) == 2
    assert len(_assert_parity(full[2:])) == 0, (
        "with one swing of each type retained there is no predecessor left"
    )
    assert len(_assert_parity(full[1:])) == 1


# ---------------------------------------------------------------------------
# Deterministic campaign
# ---------------------------------------------------------------------------

_SEEDS = (7, 19, 31, 53, 71, 97, 113, 149)


def _campaign_case(seed: int):
    import random

    rng = random.Random(seed)
    candles = _series("105")
    swings = []
    prev_high = Decimal("110")
    prev_low = Decimal("100")
    idx = 1
    bar = 2
    for step in range(4):
        atr = Decimal(str(rng.choice(["0.5", "2.0", "8.0", "50.0"])))
        tol = TOL_MULT * atr
        # deliberately straddle the band edge: exactly +/-tol, just inside, just outside
        offset = rng.choice([tol, -tol, tol + Decimal("0.01"),
                             -tol - Decimal("0.01"), Decimal("0")])
        is_high = step % 2 == 0
        if is_high:
            prev_high = prev_high + offset
            price, stype = prev_high, SwingType.SWING_HIGH
        else:
            prev_low = prev_low + offset
            price, stype = prev_low, SwingType.SWING_LOW
        swings.append(
            _swing(idx, stype, str(price), bar, bar + 1, candles,
                   reference_atr=str(atr))
        )
        idx += 1
        bar += 2
    # two more so each type has a predecessor
    for step in range(2):
        atr = Decimal(str(rng.choice(["0.5", "2.0", "8.0"])))
        tol = TOL_MULT * atr
        offset = rng.choice([tol, -tol, tol + Decimal("0.01"),
                             -tol - Decimal("0.01"), Decimal("0")])
        is_high = step % 2 == 0
        if is_high:
            prev_high = prev_high + offset
            price, stype = prev_high, SwingType.SWING_HIGH
        else:
            prev_low = prev_low + offset
            price, stype = prev_low, SwingType.SWING_LOW
        swings.append(
            _swing(idx, stype, str(price), bar, bar + 1, candles,
                   reference_atr=str(atr))
        )
        idx += 1
        bar += 2
    return tuple(swings)


@pytest.mark.parametrize("seed", _SEEDS)
def test_campaign_matches_production_on_every_prefix(seed: int) -> None:
    swings = _campaign_case(seed)
    for end in range(len(swings) + 1):
        _assert_parity(swings[:end])


def test_campaign_actually_reaches_every_relationship_label() -> None:
    """Guards the campaign: a generator that never hits an edge proves nothing."""
    seen = set()
    for seed in _SEEDS:
        swings = _campaign_case(seed)
        for c in detect_swing_relationships(swings, CONFIG):
            seen.add(c.label)
    assert len(seen) == len(SwingRelationshipLabel) == 6, (
        f"campaign must reach every label; missing "
        f"{sorted(m.name for m in SwingRelationshipLabel if m not in seen)}"
    )
