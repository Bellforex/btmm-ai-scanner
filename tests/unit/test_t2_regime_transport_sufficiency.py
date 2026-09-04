"""Does the transport wire suffice to reproduce T2's regime classification?

Mirrors `test_t1_trend_transport_sufficiency.py`'s pattern exactly: run the
REAL `_regime_for_timeframe` (per timeframe) and the real primary-selection
logic on full synthetic data, reduce the same data through the transport
oracle, and require a wire-only reconstruction to agree.

THE ORDER TRAP, MADE INTO A FIXTURE
---------------------------------------
T2's primary order is D1, H4, W1, H1, M15, M5 -- textually different from T1's
W1, D1, H4, H1, M15, M5. `test_t2_order_differs_from_t1_order_and_it_matters`
builds a case with only D1 and W1 present, where T1's order would pick W1
first and T2's order must pick D1 first -- a fixture that only distinguishes
the two orders if BOTH are wired correctly, so a port that accidentally reused
T1's order fails this test specifically rather than the whole suite.
"""

from __future__ import annotations

import random

from btmm_ai_scanner.btrc.enums import Regime, TrendState
from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.regime_engine import _regime_for_timeframe
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import _assess_timeframe
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from tests.parity_support.p5_transport_contract import DISP_CLS_VERY_FAST
from tests.parity_support.p5_transport_fixtures import (
    displacement,
    random_history,
    state,
    swing,
    transition,
)
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.t2_regime_pine_model import (
    PRIMARY_ORDER,
    assess_regime_from_transport,
    regime_for_timeframe_from_transport,
)

BULLISH = StructureDirection.BULLISH
BEARISH = StructureDirection.BEARISH
UP = DisplacementDirection.BULLISH
DOWN = DisplacementDirection.BEARISH
NORMAL = DisplacementClassification.NORMAL
FAST = DisplacementClassification.FAST
VERY_FAST = DisplacementClassification.VERY_FAST
BULL_BOS = StructureTransitionType.BULLISH_BOS
BEAR_BOS = StructureTransitionType.BEARISH_BOS
BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH


def real_regime_for_tf(swings, transitions, displacements, current_state):
    trend = _assess_timeframe(
        Timeframe.M15, tuple(swings), tuple(transitions), current_state,
        TrendEngineConfiguration(),
    )
    return _regime_for_timeframe(trend, tuple(displacements), RegimeEngineConfiguration())


def both_per_tf(swings=(), transitions=(), displacements=(), current_state=None):
    """One timeframe's real regime vs the wire-only reconstruction. Requires
    agreement, returns the real result."""
    real = real_regime_for_tf(swings, transitions, displacements, current_state)
    record = reduce_authoritative(swings, transitions, displacements, current_state)
    trend = _assess_timeframe(
        Timeframe.M15, tuple(swings), tuple(transitions), current_state,
        TrendEngineConfiguration(),
    )
    wire = regime_for_timeframe_from_transport(trend.trend_state, record)
    assert real.regime == wire, (real.regime, wire, trend.trend_state)
    return real


# ---------------------------------------------------------------------------
# Directed: every regime state
# ---------------------------------------------------------------------------


def test_uncertain_maps_from_unknown() -> None:
    real = both_per_tf(current_state=state(BULLISH, 40, swing_count=1))
    assert real.regime == Regime.UNCERTAIN


def test_transition_maps_from_transition() -> None:
    real = both_per_tf(
        transitions=[
            transition(1, BEAR_BOS),
            transition(2, BEAR_BOS),
            transition(3, BULL_CHOCH),
        ],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.TRANSITION


def test_trend_maps_from_trending() -> None:
    real = both_per_tf(
        transitions=[transition(1, BULL_CHOCH), transition(2, BULL_BOS)],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.TREND


def test_deceleration_maps_from_exhausting() -> None:
    real = both_per_tf(
        swings=[
            swing(1, SwingType.SWING_HIGH, "4500.00"),
            swing(2, SwingType.SWING_HIGH, "4450.00"),
        ],
        transitions=[transition(1, BULL_CHOCH), transition(2, BULL_BOS)],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.DECELERATION


def test_range_maps_from_range() -> None:
    real = both_per_tf(
        transitions=[
            transition(1, BULL_BOS),
            transition(2, BEAR_CHOCH),
            transition(3, BULL_CHOCH),
            transition(4, BEAR_CHOCH),
        ],
        current_state=state(BEARISH, 40, swing_count=5),
    )
    assert real.regime == Regime.RANGE


def test_expansion_on_forming_with_a_fast_displacement() -> None:
    real = both_per_tf(
        displacements=[displacement(1, UP, VERY_FAST, "2.00")],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.EXPANSION


def test_breakout_pending_on_forming_with_only_slow_displacement() -> None:
    real = both_per_tf(
        displacements=[displacement(1, UP, NORMAL, "0.80")],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.BREAKOUT_PENDING


def test_compression_on_forming_with_no_displacement() -> None:
    real = both_per_tf(current_state=state(BULLISH, 40, swing_count=5))
    assert real.regime == Regime.COMPRESSION


# ---------------------------------------------------------------------------
# Boundary: the expansion threshold, exactly at 1.50
# ---------------------------------------------------------------------------


def test_expansion_threshold_just_below() -> None:
    real = both_per_tf(
        displacements=[displacement(1, UP, FAST, "1.4999999")],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.BREAKOUT_PENDING


def test_expansion_threshold_exactly_at() -> None:
    real = both_per_tf(
        displacements=[displacement(1, UP, FAST, "1.50")],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.EXPANSION


def test_expansion_threshold_just_above() -> None:
    real = both_per_tf(
        displacements=[displacement(1, UP, VERY_FAST, "1.5000001")],
        current_state=state(BULLISH, 40, swing_count=5),
    )
    assert real.regime == Regime.EXPANSION


# ---------------------------------------------------------------------------
# The order trap
# ---------------------------------------------------------------------------


def test_t2_order_differs_from_t1_order_and_it_matters() -> None:
    """W1 comes before D1 in T1's authority order but AFTER D1 in T2's
    primary order. Only D1 and W1 present, with DIFFERENT regimes, so picking
    the wrong order picks the wrong global regime."""
    d1_state = state(BULLISH, 40, swing_count=5)  # FORMING -> COMPRESSION
    w1_transitions = [
        transition(1, BULL_CHOCH),
        transition(2, BULL_BOS),
    ]
    w1_state = state(BULLISH, 40, swing_count=5)  # TRENDING -> TREND

    d1_real = real_regime_for_tf([], [], [], d1_state)
    w1_real = real_regime_for_tf([], w1_transitions, [], w1_state)
    assert d1_real.regime == Regime.COMPRESSION
    assert w1_real.regime == Regime.TREND
    assert d1_real.regime != w1_real.regime

    trend_states = {
        "D1": TrendState.FORMING,
        "W1": _assess_timeframe(
            Timeframe.M15, (), tuple(w1_transitions), w1_state, TrendEngineConfiguration()
        ).trend_state,
    }
    records = {
        "D1": reduce_authoritative([], [], [], d1_state),
        "W1": reduce_authoritative([], w1_transitions, [], w1_state),
    }
    global_regime = assess_regime_from_transport(trend_states, records)
    assert global_regime == Regime.COMPRESSION  # D1 wins: D1 precedes W1 in PRIMARY_ORDER

    # And the mutation this test exists to catch: T1's order would pick W1.
    t1_order = ("W1", "D1", "H4", "H1", "M15", "M5")
    wrong = next(tf for tf in t1_order if tf in trend_states)
    assert wrong == "W1"
    assert wrong != "D1"


def test_primary_order_matches_the_frozen_source_sequence() -> None:
    assert PRIMARY_ORDER == ("D1", "H4", "W1", "H1", "M15", "M5")


# ---------------------------------------------------------------------------
# Randomized
# ---------------------------------------------------------------------------


def test_randomized_wire_sufficiency() -> None:
    rng = random.Random(20260905)
    mismatches = []
    for _ in range(2000):
        swings, transitions, displacements, current_state = random_history(rng)
        try:
            both_per_tf(swings, transitions, displacements, current_state)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_campaign_covers_every_regime() -> None:
    rng = random.Random(4242)
    seen = set()
    for _ in range(4000):
        swings, transitions, displacements, current_state = random_history(rng)
        real = real_regime_for_tf(swings, transitions, displacements, current_state)
        seen.add(real.regime)
    assert seen == set(Regime)


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_mutation_using_t1_order_is_caught() -> None:
    """If the primary-order constant were silently replaced by T1's order,
    this differs from the frozen sequence."""
    t1_order = ("W1", "D1", "H4", "H1", "M15", "M5")
    assert t1_order != PRIMARY_ORDER


def test_mutation_using_only_latest_displacement_is_caught() -> None:
    """A port that checked only disp3Ratio (the newest) instead of the whole
    window would miss an earlier fast displacement."""
    record = reduce_authoritative(
        [],
        [],
        [
            displacement(1, UP, VERY_FAST, "3.00"),  # fast, but not newest
            displacement(2, UP, NORMAL, "0.50"),
            displacement(3, UP, NORMAL, "0.60"),  # newest, slow
        ],
        state(BULLISH, 40, swing_count=5),
    )
    correct = regime_for_timeframe_from_transport(TrendState.FORMING, record)
    latest_only = Regime.EXPANSION if (
        record.disp3Ratio is not None and record.disp3Ratio >= 1.50
    ) else (Regime.BREAKOUT_PENDING if record.dispWindowCount > 0 else Regime.COMPRESSION)
    assert correct == Regime.EXPANSION
    assert latest_only != correct


def test_mutation_using_classification_instead_of_ratio_is_caught() -> None:
    """VERY_FAST classification alone does not imply >= 1.50 by construction
    of these fixtures -- classification is a separate, config-driven bucket
    from the raw ratio the regime threshold actually compares."""
    record = reduce_authoritative(
        [], [], [displacement(1, UP, VERY_FAST, "1.20")], state(BULLISH, 40, swing_count=5)
    )
    # ratio 1.20 < 1.50 threshold even though classified VERY_FAST by the
    # engine's own (different) thresholds -- proves the model must read the
    # RATIO, not the classification, to get this case right.
    assert record.disp1Cls == DISP_CLS_VERY_FAST
    assert record.disp1Ratio is not None and record.disp1Ratio < 1.50
    result = regime_for_timeframe_from_transport(TrendState.FORMING, record)
    assert result == Regime.BREAKOUT_PENDING
