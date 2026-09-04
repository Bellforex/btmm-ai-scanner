"""Does the 26-field transport wire suffice to reproduce T1's classification?

THE QUESTION THIS ANSWERS
---------------------------
The transport campaign proved Pine can compute and carry `contStreak`,
`priorOppStreak`, `exhaustFlag`, the bounded transition window, `stateAvailT`,
and the old `p2Dir`/`swingCount` scalars correctly. It never asked whether
those fields are SUFFICIENT to reproduce `_assess_timeframe`'s classification
-- a port could transport everything correctly and still be missing one field
T1 secretly needs. This module answers that directly: run the REAL
`_assess_timeframe` on full synthetic data, reduce the SAME data through the
transport oracle, and require `assess_trend_from_transport` (reading only the
wire) to agree.

TWO SEPARATE CLAIMS, TWO SEPARATE KINDS OF EVIDENCE
-------------------------------------------------------
1. **Sufficiency of the wire, given the premise that `swingCount ==
   analyzed_swing_count`.** Proven here, synthetically, with the fixtures
   generator's `current_state` built exactly that way (as it already is).
2. **The premise itself holds in production.** NOT provable synthetically --
   `analyzed_swing_count` is production's own field, and a synthetic fixture
   that assumes the equality cannot also test it. Proven instead on the real
   FXCM capture already on disk (`artifacts/p6x_capture/`): `analyzed_swing_count
   == len(swings) == 66` on W1, independently confirmed for this module rather
   than merely asserted -- see `test_analyzed_swing_count_equals_len_swings_on_real_data`.

Both are required for the sufficiency claim to mean anything on real data.
"""

from __future__ import annotations

import random

import pytest

from btmm_ai_scanner.btrc.enums import Direction, TrendState
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import _assess_timeframe
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from tests.parity_support.p5_transport_contract import DIR_BEARISH, DIR_BULLISH
from tests.parity_support.p5_transport_fixtures import (
    random_history,
    state,
    swing,
    transition,
)
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.t1_trend_pine_model import (
    T1Config,
    assess_trend_from_transport,
)

BULL_BOS = StructureTransitionType.BULLISH_BOS
BEAR_BOS = StructureTransitionType.BEARISH_BOS
BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH
BULLISH = StructureDirection.BULLISH
BEARISH = StructureDirection.BEARISH
UNDETERMINED = StructureDirection.UNDETERMINED

_DIR_CODE = {BULLISH: DIR_BULLISH, BEARISH: DIR_BEARISH, UNDETERMINED: 0}


def both(swings=(), transitions=(), displacements=(), current_state=None):
    """Real `_assess_timeframe` vs the wire-only Pine model. Requires agreement
    on BOTH trend_state and direction, and returns the real result."""
    real = _assess_timeframe(
        Timeframe.M15, tuple(swings), tuple(transitions), current_state,
        TrendEngineConfiguration(),
    )
    record = reduce_authoritative(swings, transitions, displacements, current_state)
    p2_direction = _DIR_CODE[current_state.direction] if current_state else 0
    swing_count = current_state.analyzed_swing_count if current_state else 0
    wire = assess_trend_from_transport(
        p2_direction=p2_direction, swing_count=swing_count, record=record,
    )
    assert real.trend_state == wire.trend_state, (real.trend_state, wire.trend_state)
    assert real.direction == wire.direction, (real.direction, wire.direction)
    return real


# ---------------------------------------------------------------------------
# The premise: analyzed_swing_count == len(swings) in production
# ---------------------------------------------------------------------------


def test_analyzed_swing_count_equals_len_swings_on_real_data() -> None:
    """Not provable synthetically -- this is production's own analyzer, run
    on the real captured FXCM history the P6X closure already established."""
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parents[2]
    capture = repo / "artifacts" / "p6x_capture" / "atomic_all_raw_log.csv"
    if not capture.exists():
        pytest.skip(f"no P6X capture present: {capture.name}")

    sys.path.insert(0, str(repo))
    from decimal import Decimal

    from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
    from btmm_ai_scanner.historical_backtest.identity import (
        ContentAddressedIdentityProvider,
    )
    from btmm_ai_scanner.measurements.atr import compute_atr_series
    from btmm_ai_scanner.structure.analyzer import analyze_structure_state
    from btmm_ai_scanner.structure.configuration import StructureConfiguration
    from tests.parity_support.p6_atomic_capture_log import group_by_emission, parse_raw
    from tests.parity_support.p6_real_data_replay import build_candles
    from tests.parity_support.p6x_transport_replay import _DIAG, _TRUNC, ORACLE

    text = capture.read_text(encoding="utf-8")
    groups = group_by_emission(text)
    stamps = {
        "W1": "2026-09-04T02:12:44.416+01:00",
        "M5": "2026-09-04T02:12:42.226+01:00",
    }
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
    scfg = StructureConfiguration()
    checked = 0
    for tf, stamp in stamps.items():
        raw = None
        for group_stamp, records in groups:
            if group_stamp != stamp:
                continue
            block = "\n".join(records)
            if "P6RAW_SUMMARY|" in block:
                candidate = parse_raw(block)
                if candidate.timeframe == tf:
                    raw = candidate
        assert raw is not None
        candles = build_candles(tf, raw.bars)
        atr_all = compute_atr_series(candles, mcfg.atr_period)
        terminal = len(candles) - 1
        lookback = ORACLE.LOOKBACK
        window = candles[max(0, terminal + 1 - lookback) : terminal + 1]
        watr = ORACLE._REPLAY.window_atr(atr_all, terminal, lookback)
        with _TRUNC.injected_atr(watr):
            swings = tuple(_DIAG._confirmed_swings(window, mcfg))
            analysis = analyze_structure_state(
                window, swings, scfg, ContentAddressedIdentityProvider()
            )
        assert analysis.current_state.analyzed_swing_count == len(swings), tf
        checked += 1
    assert checked == 2


# ---------------------------------------------------------------------------
# Directed
# ---------------------------------------------------------------------------


def test_unknown_below_minimum_swings() -> None:
    result = both(current_state=state(BULLISH, 40, swing_count=1))
    assert result.trend_state == TrendState.UNKNOWN
    assert result.direction == Direction.NEUTRAL


def test_forming_when_undetermined() -> None:
    result = both(current_state=state(UNDETERMINED, 40, swing_count=5))
    assert result.trend_state == TrendState.FORMING


def test_trending_bullish_with_continuation() -> None:
    result = both(
        transitions=[transition(1, BULL_CHOCH), transition(2, BULL_BOS)],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.TRENDING
    assert result.direction == Direction.BULLISH


def test_strong_trending_at_the_strong_streak_threshold() -> None:
    result = both(
        transitions=[
            transition(1, BULL_CHOCH),
            transition(2, BULL_BOS),
            transition(3, BULL_BOS),
            transition(4, BULL_BOS),
        ],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.TRENDING
    assert result.direction == Direction.STRONG_BULLISH


def test_forming_on_a_fresh_choch_with_no_prior_run() -> None:
    result = both(
        transitions=[transition(1, BULL_CHOCH)],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.FORMING


def test_transition_on_a_choch_reversing_an_established_run() -> None:
    result = both(
        transitions=[
            transition(1, BEAR_BOS),
            transition(2, BEAR_BOS),
            transition(3, BULL_CHOCH),
        ],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.TRANSITION


def test_range_on_alternating_transitions() -> None:
    result = both(
        transitions=[
            transition(1, BULL_BOS),
            transition(2, BEAR_CHOCH),
            transition(3, BULL_CHOCH),
            transition(4, BEAR_CHOCH),
        ],
        current_state=state(BEARISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.RANGE


def test_exhausting_bullish() -> None:
    result = both(
        swings=[
            swing(1, SwingType.SWING_HIGH, "4500.00"),
            swing(2, SwingType.SWING_HIGH, "4450.00"),
        ],
        transitions=[transition(1, BULL_CHOCH), transition(2, BULL_BOS)],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert result.trend_state == TrendState.EXHAUSTING


# ---------------------------------------------------------------------------
# Randomized
# ---------------------------------------------------------------------------


def test_randomized_wire_sufficiency() -> None:
    rng = random.Random(20260904)
    mismatches = []
    for _ in range(2000):
        swings, transitions, displacements, current_state = random_history(rng)
        # random_history already sets analyzed_swing_count = len(swings), the
        # premise this module's other tests establish holds in production too.
        try:
            both(swings, transitions, displacements, current_state)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_the_corpus_catches_a_window_alignment_regression() -> None:
    """A real bug, caught by this exact campaign while writing the model: an
    earlier version of `_alternation_from_window` treated the bounded window
    as right-aligned (reading the LAST `count` array indices) instead of the
    contract's actual left-alignment (slot1..slot{count} populated,
    slot{count} newest). Re-implemented here as a mutation so a regression to
    that reading is guaranteed to fail loudly rather than pass quietly."""
    from tests.parity_support.p5_transport_contract import TRANSITION_WINDOW_CAPACITY

    def wrong_alternation(record, window: int) -> int:
        slots = [record.trans1Type, record.trans2Type, record.trans3Type, record.trans4Type]
        count = min(record.transWindowCount, window)
        tail = slots[TRANSITION_WINDOW_CAPACITY - count :]
        tail = tail[max(0, len(tail) - window) :]
        from tests.parity_support.t1_trend_pine_model import _CHOCH_CODES

        return sum(1 for code in tail if code in _CHOCH_CODES)

    rng = random.Random(7)
    caught = False
    for _ in range(500):
        swings, transitions, displacements, current_state = random_history(rng)
        record = reduce_authoritative(swings, transitions, displacements, current_state)
        if record.transWindowCount == 0 or record.transWindowCount == TRANSITION_WINDOW_CAPACITY:
            continue  # both alignments agree when the window is empty or full
        correct = _alternation_count_reference(record)
        wrong = wrong_alternation(record, T1Config().range_window)
        if correct != wrong:
            caught = True
            break
    assert caught, "corpus never exercised a partial (non-empty, non-full) window"


def _alternation_count_reference(record) -> int:
    from tests.parity_support.t1_trend_pine_model import _alternation_from_window

    return _alternation_from_window(record, T1Config().range_window)


def test_randomized_campaign_covers_every_trend_state() -> None:
    rng = random.Random(999)
    seen = set()
    for _ in range(3000):
        swings, transitions, _displacements, current_state = random_history(rng)
        real = _assess_timeframe(
            Timeframe.M15, tuple(swings), tuple(transitions), current_state,
            TrendEngineConfiguration(),
        )
        seen.add(real.trend_state)
    assert seen == set(TrendState)
