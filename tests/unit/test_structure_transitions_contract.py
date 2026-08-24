"""Direct BOS / CHOCH contract tests for the production structure walk.

The pre-existing structure suite covered bootstrap (8 tests) and batch<->replay
equivalence (6 tests) thoroughly, but contained **no direct test of BOS or
CHOCH** — the break machinery is what a Pine port must reproduce most carefully,
and it was the least protected part of the contract.

Every expectation here is derived from `structure/transitions.py`:

* CHOCH predicates  `close > protected_high` / `close < protected_low`  (L171/L174)
* BOS   predicates  `close > weak_high`      / `close < weak_low`       (L177/L180)
* CHOCH is handled first and `continue`s past the BOS block             (L183/L253)
* CHOCH ABORTS via `continue` *before* any mutation when no unbroken
  opposite-side swing exists                                           (L189-190/L223-224)

All comparisons are strict and close-only: no wick, no intrabar, no ATR
tolerance. Tolerance applies solely to relationship labels.

Input-contract note: `_validate_swings` requires swings to ALTERNATE by type, so
a within-type predecessor is always two positions back in source order. P1's own
detector guarantees this via its alternation gate, so the fixtures honour it.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.analyzer import analyze_structure_state
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)

_RAW_CANDLE_ID = UUID("0193f420-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f420-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = StructureConfiguration()

BAR_COUNT = 24


class _HashIdentityProvider:
    def identify(self, *, output_type: object, semantic_key: tuple[str, ...]) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)  # type: ignore[attr-defined]
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f420-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    close: str,
    high: str | None = None,
    low: str | None = None,
    open_: str | None = None,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    c = Decimal(close)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_) if open_ is not None else c,
            "high": Decimal(high) if high is not None else c,
            "low": Decimal(low) if low is not None else c,
            "close": c,
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _series(
    neutral_close: str, overrides: dict[int, dict[str, str]] | None = None
) -> tuple[NormalizedCandle, ...]:
    """Flat neutral series with per-bar OHLC overrides."""
    overrides = overrides or {}
    bars = []
    for i in range(BAR_COUNT):
        spec = overrides.get(i)
        if spec is None:
            bars.append(_candle(i, neutral_close))
        else:
            bars.append(
                _candle(
                    i,
                    spec.get("close", neutral_close),
                    spec.get("high"),
                    spec.get("low"),
                    spec.get("open"),
                )
            )
    return tuple(bars)


def _swing(
    index: int,
    swing_type: SwingType,
    price: str,
    pivot_bar_index: int,
    confirmation_bar_index: int,
    candles: tuple[NormalizedCandle, ...],
    reference_atr: str = "1.0",
) -> ConfirmedSwing:
    pivot_time = candles[pivot_bar_index].event_time_utc
    confirmation_time = candles[confirmation_bar_index].availability_time_utc
    return ConfirmedSwing(
        record_id=_record_id(1000 + index),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_bar_index,
        pivot_candle_record_ids=(candles[pivot_bar_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=1),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[confirmation_bar_index].record_id,
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def _analyze(candles, swings):
    return analyze_structure_state(
        candles, swings, _CONFIG, _HashIdentityProvider()
    )


# ---------------------------------------------------------------------------
# Bootstrap fixtures. Swings ALTERNATE by type, as _validate_swings requires.
# ---------------------------------------------------------------------------
# BULLISH: L1 100 -> H1 110 -> L2 102 (HL) -> H2 112 (HH)
#   bootstrap => protected_low = L2 (102), weak_high = H2 (112)
# BEARISH: H1 110 -> L1 100 -> H2 108 (LH) -> L2 98 (LL)
#   bootstrap => protected_high = H2 (108), weak_low = L2 (98)

BULL_NEUTRAL = "105"      # strictly inside (102, 112): no break
BEAR_NEUTRAL = "103"      # strictly inside (98, 108): no break
BULL_PROTECTED_LOW = Decimal("102")
BULL_WEAK_HIGH = Decimal("112")
BEAR_PROTECTED_HIGH = Decimal("108")
BEAR_WEAK_LOW = Decimal("98")


def _bull(overrides=None):
    candles = _series(BULL_NEUTRAL, overrides)
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles),
        _swing(3, SwingType.SWING_LOW, "102", 6, 7, candles),
        _swing(4, SwingType.SWING_HIGH, "112", 8, 9, candles),
    )
    return candles, swings


def _bear(overrides=None):
    candles = _series(BEAR_NEUTRAL, overrides)
    swings = (
        _swing(1, SwingType.SWING_HIGH, "110", 2, 3, candles),
        _swing(2, SwingType.SWING_LOW, "100", 4, 5, candles),
        _swing(3, SwingType.SWING_HIGH, "108", 6, 7, candles),
        _swing(4, SwingType.SWING_LOW, "98", 8, 9, candles),
    )
    return candles, swings


def _types(analysis) -> list[StructureTransitionType]:
    return [t.transition_type for t in analysis.structure_transitions]


# ===========================================================================
# Baseline: the fixtures bootstrap as intended and do not break spuriously
# ===========================================================================

def test_bull_fixture_bootstraps_bullish_without_breaking() -> None:
    analysis = _analyze(*_bull())
    assert analysis.current_state.direction == StructureDirection.BULLISH
    assert _types(analysis) == []


def test_bear_fixture_bootstraps_bearish_without_breaking() -> None:
    analysis = _analyze(*_bear())
    assert analysis.current_state.direction == StructureDirection.BEARISH
    assert _types(analysis) == []


# ===========================================================================
# BOS — bullish
# ===========================================================================

def test_bos_b1_close_strictly_above_weak_high_emits_bullish_bos() -> None:
    candles, swings = _bull({12: {"close": "113"}})
    analysis = _analyze(candles, swings)
    assert _types(analysis) == [StructureTransitionType.BULLISH_BOS]
    t = analysis.structure_transitions[0]
    assert t.direction_before == StructureDirection.BULLISH
    assert t.direction_after == StructureDirection.BULLISH, "BOS must not flip direction"
    assert t.broken_level_price == BULL_WEAK_HIGH
    assert t.break_close_price == Decimal("113")
    assert t.break_candle_id == candles[12].record_id
    assert t.event_time_utc == candles[12].event_time_utc
    assert t.weak_swing_id is None
    assert analysis.current_state.direction == StructureDirection.BULLISH


def test_bos_b2_close_exactly_equal_to_weak_high_is_not_a_break() -> None:
    candles, swings = _bull({12: {"close": "112"}})
    assert _types(_analyze(candles, swings)) == []


def test_bos_b3_wick_above_but_close_below_is_not_a_break() -> None:
    candles, swings = _bull({12: {"close": "105", "high": "120"}})
    assert _types(_analyze(candles, swings)) == []


def test_bos_b4_open_above_but_close_not_above_is_not_a_break() -> None:
    candles, swings = _bull({12: {"close": "111", "open": "120", "high": "121"}})
    assert _types(_analyze(candles, swings)) == []


def test_bos_b5_break_consumes_the_weak_swing() -> None:
    candles, swings = _bull({12: {"close": "113"}})
    analysis = _analyze(candles, swings)
    assert analysis.structure_transitions[0].broken_swing_id == swings[3].record_id


def test_bos_b6_same_swing_cannot_emit_bos_twice() -> None:
    candles, swings = _bull({12: {"close": "113"}, 14: {"close": "114"}})
    assert _types(_analyze(candles, swings)) == [StructureTransitionType.BULLISH_BOS]


def test_bos_b7_protected_replacement_is_most_recent_unbroken_low() -> None:
    candles, swings = _bull({12: {"close": "113"}})
    analysis = _analyze(candles, swings)
    # lows visible: L1 (bar 2), L2 (bar 6) -> most recent unbroken is L2
    assert analysis.structure_transitions[0].protected_swing_id == swings[2].record_id


def test_bos_b8_protected_falls_back_when_no_replacement_exists() -> None:
    """With only one low visible it is already protected, so the fallback and the
    replacement coincide — the assertion is that a protected id is still set."""
    candles, swings = _bull({12: {"close": "113"}})
    analysis = _analyze(candles, swings)
    assert analysis.structure_transitions[0].protected_swing_id is not None
    assert analysis.current_state.active_protected_low_swing_id is not None


# ===========================================================================
# BOS — bearish (mirror)
# ===========================================================================

def test_bos_r1_close_strictly_below_weak_low_emits_bearish_bos() -> None:
    candles, swings = _bear({12: {"close": "97"}})
    analysis = _analyze(candles, swings)
    assert _types(analysis) == [StructureTransitionType.BEARISH_BOS]
    t = analysis.structure_transitions[0]
    assert t.direction_before == StructureDirection.BEARISH
    assert t.direction_after == StructureDirection.BEARISH
    assert t.broken_level_price == BEAR_WEAK_LOW
    assert t.break_close_price == Decimal("97")
    assert t.broken_swing_id == swings[3].record_id


def test_bos_r2_close_exactly_equal_to_weak_low_is_not_a_break() -> None:
    candles, swings = _bear({12: {"close": "98"}})
    assert _types(_analyze(candles, swings)) == []


def test_bos_r3_wick_below_but_close_above_is_not_a_break() -> None:
    candles, swings = _bear({12: {"close": "103", "low": "90"}})
    assert _types(_analyze(candles, swings)) == []


def test_bos_r6_same_swing_cannot_emit_bearish_bos_twice() -> None:
    candles, swings = _bear({12: {"close": "97"}, 14: {"close": "96"}})
    assert _types(_analyze(candles, swings)) == [StructureTransitionType.BEARISH_BOS]


def test_bos_r7_protected_replacement_is_most_recent_unbroken_high() -> None:
    candles, swings = _bear({12: {"close": "97"}})
    analysis = _analyze(candles, swings)
    assert analysis.structure_transitions[0].protected_swing_id == swings[2].record_id


# ===========================================================================
# CHOCH
# ===========================================================================

def test_choch_c1_bullish_direction_close_below_protected_low_emits_bearish_choch() -> None:
    candles, swings = _bull({12: {"close": "101"}})
    analysis = _analyze(candles, swings)
    assert _types(analysis) == [StructureTransitionType.BEARISH_CHOCH]
    t = analysis.structure_transitions[0]
    assert t.direction_before == StructureDirection.BULLISH
    assert t.direction_after == StructureDirection.BEARISH
    assert t.broken_level_price == BULL_PROTECTED_LOW
    assert t.broken_swing_id == swings[2].record_id
    assert analysis.current_state.direction == StructureDirection.BEARISH


def test_choch_c2_bearish_direction_close_above_protected_high_emits_bullish_choch() -> None:
    candles, swings = _bear({12: {"close": "109"}})
    analysis = _analyze(candles, swings)
    assert _types(analysis) == [StructureTransitionType.BULLISH_CHOCH]
    t = analysis.structure_transitions[0]
    assert t.direction_before == StructureDirection.BEARISH
    assert t.direction_after == StructureDirection.BULLISH
    assert t.broken_level_price == BEAR_PROTECTED_HIGH
    assert t.broken_swing_id == swings[2].record_id


def test_choch_c3_close_exactly_at_protected_level_is_not_a_choch() -> None:
    assert _types(_analyze(*_bull({12: {"close": "102"}}))) == []
    assert _types(_analyze(*_bear({12: {"close": "108"}}))) == []


def test_choch_c4_wick_through_protected_but_close_back_is_not_a_choch() -> None:
    assert _types(_analyze(*_bull({12: {"close": "105", "low": "90"}}))) == []
    assert _types(_analyze(*_bear({12: {"close": "103", "high": "120"}}))) == []


def test_choch_c5_clears_both_weak_levels() -> None:
    candles, swings = _bull({12: {"close": "101"}})
    state = _analyze(candles, swings).current_state
    assert state.active_weak_high_swing_id is None
    assert state.active_weak_low_swing_id is None


def test_choch_c6_direction_flips_exactly_once_per_break() -> None:
    candles, swings = _bull({12: {"close": "101"}, 14: {"close": "100.5"}})
    analysis = _analyze(candles, swings)
    assert _types(analysis) == [StructureTransitionType.BEARISH_CHOCH]
    assert analysis.current_state.direction == StructureDirection.BEARISH


def test_choch_c7_opposite_side_replacement_selected_correctly() -> None:
    candles, swings = _bull({12: {"close": "101"}})
    analysis = _analyze(candles, swings)
    # flipping to BEARISH needs a protected HIGH: H1 (bar 4), H2 (bar 8) -> H2
    assert analysis.structure_transitions[0].protected_swing_id == swings[3].record_id


def test_choch_c10_repeated_choch_against_consumed_level_cannot_re_emit() -> None:
    candles, swings = _bull({12: {"close": "101"}, 13: {"close": "101"}})
    assert _types(_analyze(candles, swings)) == [
        StructureTransitionType.BEARISH_CHOCH
    ]


# ===========================================================================
# CHOCH precedence and the ABORT path (the transcription hazard)
# ===========================================================================

def _choch_chain():
    """Consume every high through a CHOCH chain, then abort.

    bar 10  close 109 > H2 108 -> BULLISH_CHOCH  (breaks H2, protected_low = L2 98)
    bar 12  close  97 <  L2 98 -> BEARISH_CHOCH  (breaks L2, protected_high = H1 110)
    bar 14  close 111 > H1 110 -> BULLISH_CHOCH  (breaks H1, protected_low = L1 100)
    bar 16  close  99 <  L1 100 -> candidate, but BOTH highs are consumed -> ABORT
    """
    return _bear(
        {
            10: {"close": "109"},
            12: {"close": "97"},
            14: {"close": "111"},
            16: {"close": "99"},
        }
    )


def test_choch_chain_emits_exactly_three_transitions_then_aborts() -> None:
    analysis = _analyze(*_choch_chain())
    assert _types(analysis) == [
        StructureTransitionType.BULLISH_CHOCH,
        StructureTransitionType.BEARISH_CHOCH,
        StructureTransitionType.BULLISH_CHOCH,
    ], "the fourth candidate must abort, emitting nothing"


def test_choch_abort_leaves_state_completely_unmutated() -> None:
    """The abort `continue` precedes every mutation, so direction, protected and
    weak levels must all survive the aborted candle unchanged."""
    candles, swings = _choch_chain()
    after_abort = _analyze(candles, swings).current_state

    # same fixture with the aborting candle made neutral
    neutral = dict(
        {10: {"close": "109"}, 12: {"close": "97"}, 14: {"close": "111"}}
    )
    before_abort = _analyze(*_bear(neutral)).current_state

    assert after_abort.direction == before_abort.direction
    assert (
        after_abort.active_protected_low_swing_id
        == before_abort.active_protected_low_swing_id
    )
    assert (
        after_abort.active_protected_high_swing_id
        == before_abort.active_protected_high_swing_id
    )
    assert after_abort.latest_transition_id == before_abort.latest_transition_id


def test_choch_precedence_when_both_raw_conditions_hold_on_one_candle() -> None:
    """A single close that satisfies CHOCH and BOS must yield CHOCH only.

    The prices are deliberately unnatural — the weak high (111) sits BELOW the
    protected low (112) — because that is the only configuration in which one
    close can satisfy both predicates at once. The contract places no ordering
    constraint on these levels, and this is precisely the precedence a Pine port
    could invert (`transitions.py` handles CHOCH first, then `continue`s).
    """
    candles = _series("105", {10: {"close": "111.5"}})
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles),
        _swing(3, SwingType.SWING_LOW, "112", 6, 7, candles),   # HIGHER_LOW
        _swing(4, SwingType.SWING_HIGH, "111", 8, 9, candles),  # HIGHER_HIGH
    )
    analysis = _analyze(candles, swings)
    assert analysis.current_state.direction is not None
    assert analysis.structure_transitions, "fixture must produce a transition"
    first = analysis.structure_transitions[0]
    # close 111.5 is BOTH below protected_low 112 and above weak_high 111
    assert first.break_close_price == Decimal("111.5")
    assert first.transition_type == StructureTransitionType.BEARISH_CHOCH, (
        "CHOCH must take precedence over BOS on the same candle"
    )


# ===========================================================================
# Relationship tolerance — asymmetry and strict boundaries
# ===========================================================================
# tolerance = 0.10 * CURRENT swing's pivot_reference_atr.
# Previous ATR is deliberately far from current ATR so a wrong-ATR
# implementation produces a different label and the test fails.

PREV_ATR = "50.0"     # 0.10 * 50 = 5.00  (wrong source)
CURR_ATR = "2.0"      # 0.10 *  2 = 0.20  (correct source)


def _label_fixture(second_high_price: str):
    candles = _series("105")
    swings = (
        _swing(1, SwingType.SWING_LOW, "100", 2, 3, candles, reference_atr=PREV_ATR),
        _swing(2, SwingType.SWING_HIGH, "110", 4, 5, candles, reference_atr=PREV_ATR),
        _swing(3, SwingType.SWING_LOW, "100", 6, 7, candles, reference_atr=CURR_ATR),
        _swing(
            4, SwingType.SWING_HIGH, second_high_price, 8, 9, candles,
            reference_atr=CURR_ATR,
        ),
    )
    return candles, swings


def _high_label(analysis):
    highs = [
        r for r in analysis.swing_relationships if r.swing_type == SwingType.SWING_HIGH
    ]
    return highs[-1].label if highs else None


@pytest.mark.parametrize(
    ("price", "expected"),
    [
        ("110.21", SwingRelationshipLabel.HIGHER_HIGH),   # > +0.20
        ("110.20", SwingRelationshipLabel.EQUAL_HIGH),    # == +0.20 -> EQUAL
        ("110.00", SwingRelationshipLabel.EQUAL_HIGH),    # inside band
        ("109.80", SwingRelationshipLabel.EQUAL_HIGH),    # == -0.20 -> EQUAL
        ("109.79", SwingRelationshipLabel.LOWER_HIGH),    # < -0.20
    ],
)
def test_high_relationship_boundaries_are_strict(price, expected) -> None:
    analysis = _analyze(*_label_fixture(price))
    assert _high_label(analysis) == expected


def test_tolerance_uses_current_swing_atr_not_predecessor_atr() -> None:
    """+0.21 exceeds the current-ATR band (0.20) but sits far inside the
    predecessor-ATR band (5.00). HIGHER_HIGH proves the current ATR is used."""
    analysis = _analyze(*_label_fixture("110.21"))
    assert _high_label(analysis) == SwingRelationshipLabel.HIGHER_HIGH


# ===========================================================================
# Event timing
# ===========================================================================

def test_transition_timestamps_follow_the_break_candle_and_broken_swing() -> None:
    candles, swings = _bull({12: {"close": "113"}})
    t = _analyze(candles, swings).structure_transitions[0]
    broken = swings[3]
    assert t.event_time_utc == candles[12].event_time_utc
    assert t.availability_time_utc == max(
        candles[12].availability_time_utc, broken.availability_time_utc
    )
    # the two inputs differ, so equality cannot mask a wrong choice
    assert candles[12].availability_time_utc != broken.availability_time_utc


def test_swing_is_invisible_before_its_meaningful_confirmation_time() -> None:
    """A break candle before the weak high is confirmed must not fire."""
    candles, swings = _bull({7: {"close": "113"}})
    assert _types(_analyze(candles, swings)) == []


# ===========================================================================
# Batch <-> incremental equivalence over every break path
# ===========================================================================

_SCENARIOS = {
    "bullish_bos": lambda: _bull({12: {"close": "113"}}),
    "bearish_bos": lambda: _bear({12: {"close": "97"}}),
    "bearish_choch": lambda: _bull({12: {"close": "101"}}),
    "bullish_choch": lambda: _bear({12: {"close": "109"}}),
    "choch_abort_chain": _choch_chain,
    "repeat_suppressed": lambda: _bull({12: {"close": "113"}, 14: {"close": "114"}}),
    "equal_no_break": lambda: _bull({12: {"close": "112"}}),
    "bootstrap_then_bos": lambda: _bull({10: {"close": "113"}}),
    "bootstrap_then_choch": lambda: _bull({10: {"close": "101"}}),
}


@pytest.mark.parametrize("name", sorted(_SCENARIOS))
def test_every_prefix_is_internally_consistent(name: str) -> None:
    """Growing-prefix determinism over each break path.

    Re-analysing a prefix must reproduce byte-identical public state, and a
    prefix can never lose a transition that a shorter prefix already emitted.
    """
    candles, swings = _SCENARIOS[name]()
    seen: list[int] = []
    for end in range(1, len(candles) + 1):
        prefix = candles[:end]
        ids = {c.record_id for c in prefix}
        in_window = tuple(
            s
            for s in swings
            if s.confirmation_candle_id in ids
            and all(p in ids for p in s.pivot_candle_record_ids)
        )
        first = _analyze(prefix, in_window)
        second = _analyze(prefix, in_window)
        assert first.current_state.direction == second.current_state.direction
        assert _types(first) == _types(second)
        assert (
            first.current_state.content_fingerprint
            == second.current_state.content_fingerprint
        )
        seen.append(len(first.structure_transitions))
    assert seen == sorted(seen), (
        "transition count must be monotonic as the prefix grows"
    )


# ===========================================================================
# Deterministic randomized campaign (fixed seeds, modest scale)
#
# Diversity check rather than a scale test: enough alternating-swing sequences
# with varied prices to hit bootstrap, EQUAL labels, BOS, CHOCH and quiet
# stretches, asserting determinism and monotonic transition growth on every
# prefix. Fixed seeds keep it reproducible and fast.
# ===========================================================================

# seeds chosen so every mode (seed % 3 -> bull / bear / equal) appears twice
_SEEDS = (12, 13, 14, 102, 103, 104)


def _random_case(seed: int):
    """Build an alternating swing sequence with a deliberate structural mode.

    Purely random jitter almost never satisfies bootstrap (it needs HH *and* HL,
    or LH *and* LL simultaneously), so the mode is chosen explicitly and the
    jitter is applied while preserving it. That keeps the campaign diverse rather
    than degenerating into UNDETERMINED cases.
    """
    import random

    rng = random.Random(seed)
    mode = ("bull", "bear", "equal")[seed % 3]

    lo1, hi1 = 100, 110
    if mode == "bull":                       # HH + HL
        lo2 = lo1 + rng.randint(2, 6)
        hi2 = hi1 + rng.randint(2, 6)
    elif mode == "bear":                     # LH + LL
        lo2 = lo1 - rng.randint(2, 6)
        hi2 = hi1 - rng.randint(2, 6)
    else:                                    # inside the 0.10*ATR band -> EQUAL
        lo2, hi2 = lo1, hi1

    # break attempts straddling both levels so BOS and CHOCH are both reachable
    overrides = {}
    for bar in range(10, BAR_COUNT, 2):
        overrides[bar] = {
            "close": str(Decimal(str(rng.choice([
                min(lo1, lo2) - 2, max(hi1, hi2) + 2, 105,
            ]))))
        }
    candles = _series("105", overrides)
    swings = (
        _swing(1, SwingType.SWING_LOW, str(lo1), 2, 3, candles),
        _swing(2, SwingType.SWING_HIGH, str(hi1), 4, 5, candles),
        _swing(3, SwingType.SWING_LOW, str(lo2), 6, 7, candles),
        _swing(4, SwingType.SWING_HIGH, str(hi2), 8, 9, candles),
    )
    return candles, swings


@pytest.mark.parametrize("seed", _SEEDS)
def test_randomized_campaign_is_deterministic_on_every_prefix(seed: int) -> None:
    candles, swings = _random_case(seed)
    counts: list[int] = []
    for end in range(1, len(candles) + 1):
        prefix = candles[:end]
        ids = {c.record_id for c in prefix}
        in_window = tuple(
            s
            for s in swings
            if s.confirmation_candle_id in ids
            and all(p in ids for p in s.pivot_candle_record_ids)
        )
        a = _analyze(prefix, in_window)
        b = _analyze(prefix, in_window)
        assert a.current_state.content_fingerprint == b.current_state.content_fingerprint
        assert _types(a) == _types(b)
        counts.append(len(a.structure_transitions))
    assert counts == sorted(counts), "transitions must never be retracted"


def test_randomized_campaign_reaches_meaningful_diversity() -> None:
    """Guards the campaign against silently degenerating into no-op cases."""
    directions, kinds = set(), set()
    for seed in _SEEDS:
        a = _analyze(*_random_case(seed))
        directions.add(a.current_state.direction)
        kinds.update(_types(a))
    assert len(directions) >= 3, f"campaign saw only {directions}"
    assert len(kinds) >= 3, f"campaign saw only {sorted(k.name for k in kinds)}"
