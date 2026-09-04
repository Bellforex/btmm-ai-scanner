"""Does the transport wire suffice to reproduce T3's momentum / breakout /
pullback classification?

Same pattern as T1/T2: run the REAL per-timeframe assessment on full synthetic
data, reduce the SAME data through the transport oracle, and require a
wire-only reconstruction (`t3_pine_model.py`) to agree. Momentum, breakout and
pullback are three independent claims, tested independently, since a port
could get one right and another wrong.
"""

from __future__ import annotations

import random

from btmm_ai_scanner.btrc.enums import (
    BreakoutState,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
)
from btmm_ai_scanner.btrc.t3_configuration import MomentumBreakoutPullbackConfiguration
from btmm_ai_scanner.btrc.t3_engine import (
    _assess_timeframe_breakout,
    _assess_timeframe_momentum,
    _assess_timeframe_pullback,
)
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from tests.parity_support.p5_transport_contract import DIR_BEARISH, DIR_BULLISH
from tests.parity_support.p5_transport_fixtures import (
    displacement,
    random_history,
    state,
    swing,
    transition,
)
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.t3_pine_model import (
    breakout_from_transport,
    momentum_from_transport,
    pullback_from_transport,
)

BULLISH = StructureDirection.BULLISH
BEARISH = StructureDirection.BEARISH
UNDETERMINED = StructureDirection.UNDETERMINED
UP = DisplacementDirection.BULLISH
DOWN = DisplacementDirection.BEARISH
NORMAL = DisplacementClassification.NORMAL
FAST = DisplacementClassification.FAST
VERY_FAST = DisplacementClassification.VERY_FAST
BULL_BOS = StructureTransitionType.BULLISH_BOS
BEAR_BOS = StructureTransitionType.BEARISH_BOS
BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH

_DIR_CODE = {BULLISH: DIR_BULLISH, BEARISH: DIR_BEARISH, UNDETERMINED: 0}
_CFG = MomentumBreakoutPullbackConfiguration()


def momentum_both(displacements=()):
    """`direction` is required exact -- it never crosses a rounding or
    threshold-tie step, only same-value comparisons on the same wire float, and
    has shown zero mismatches across every sweep run against this corpus.
    `momentum_score`/`acceleration` DO cross such a step (Decimal exact-tie vs
    float64 wire cast) and are asserted only within the bound
    `test_momentum_score_and_acceleration_tolerance_is_bounded` proves is real
    and small -- see `t3_pine_model`'s module docstring for why."""
    real = _assess_timeframe_momentum(Timeframe.M15, tuple(displacements), _CFG)
    record = reduce_authoritative([], [], displacements, None)
    wire = momentum_from_transport(record)
    assert real.direction == wire.direction, (real.direction, wire.direction)
    assert abs(real.momentum_score - wire.momentum_score) <= 1, (
        real.momentum_score, wire.momentum_score,
    )
    if real.acceleration != wire.acceleration:
        assert MomentumAcceleration.STEADY in (real.acceleration, wire.acceleration), (
            real.acceleration, wire.acceleration,
        )
    return real


def breakout_both(transitions=(), displacements=()):
    real = _assess_timeframe_breakout(Timeframe.M15, tuple(transitions), (), tuple(displacements))
    record = reduce_authoritative([], transitions, displacements, None)
    wire = breakout_from_transport(record)
    assert real.breakout_state == wire.breakout_state, (
        real.breakout_state, wire.breakout_state,
    )
    assert real.breakout_score == wire.breakout_score, (
        real.breakout_score, wire.breakout_score,
    )
    return real


def pullback_both(swings=(), current_state=None):
    real = _assess_timeframe_pullback(Timeframe.M15, tuple(swings), current_state, (), _CFG)
    record = reduce_authoritative(swings, [], [], current_state)
    p2_direction = _DIR_CODE[current_state.direction] if current_state else 0
    wire = pullback_from_transport(p2_direction, record)
    assert real.pullback_state == wire.pullback_state, (
        real.pullback_state, wire.pullback_state,
    )
    return real


# ---------------------------------------------------------------------------
# Momentum: directed
# ---------------------------------------------------------------------------


def test_momentum_neutral_on_no_displacement() -> None:
    real = momentum_both()
    assert real.direction == MomentumDirection.NEUTRAL
    assert real.acceleration == MomentumAcceleration.STEADY
    assert real.momentum_score == 0


def test_momentum_strong_bullish_via_very_fast() -> None:
    real = momentum_both([displacement(1, UP, VERY_FAST, "2.00")])
    assert real.direction == MomentumDirection.STRONG_BULLISH


def test_momentum_bullish_not_strong_below_threshold_count() -> None:
    real = momentum_both([displacement(1, UP, NORMAL, "0.80")])
    assert real.direction == MomentumDirection.BULLISH


def test_momentum_strong_bearish_via_count() -> None:
    real = momentum_both(
        [displacement(1, DOWN, NORMAL, "0.50"), displacement(2, DOWN, NORMAL, "0.60")]
    )
    assert real.direction == MomentumDirection.STRONG_BEARISH


def test_momentum_mixed_majority_bullish() -> None:
    real = momentum_both(
        [
            displacement(1, UP, NORMAL, "0.50"),
            displacement(2, UP, NORMAL, "0.50"),
            displacement(3, DOWN, NORMAL, "0.50"),
        ]
    )
    assert real.direction == MomentumDirection.BULLISH


def test_momentum_neutral_on_even_split() -> None:
    real = momentum_both(
        [displacement(1, UP, NORMAL, "0.50"), displacement(2, DOWN, NORMAL, "0.50")]
    )
    assert real.direction == MomentumDirection.NEUTRAL


def test_momentum_accelerating() -> None:
    real = momentum_both(
        [
            displacement(1, UP, NORMAL, "0.50"),
            displacement(2, UP, NORMAL, "0.50"),
            displacement(3, UP, NORMAL, "2.00"),
        ]
    )
    assert real.acceleration == MomentumAcceleration.ACCELERATING


def test_momentum_decelerating() -> None:
    real = momentum_both(
        [
            displacement(1, UP, NORMAL, "2.00"),
            displacement(2, UP, NORMAL, "2.00"),
            displacement(3, UP, NORMAL, "0.10"),
        ]
    )
    assert real.acceleration == MomentumAcceleration.DECELERATING


# ---------------------------------------------------------------------------
# Breakout: directed
# ---------------------------------------------------------------------------


def test_breakout_none_on_no_transitions() -> None:
    real = breakout_both()
    assert real.breakout_state is None
    assert real.breakout_score == 0


def test_breakout_weak_on_no_accompanying_displacement() -> None:
    real = breakout_both(transitions=[transition(1, BULL_BOS)])
    assert real.breakout_state == BreakoutState.WEAK_BREAK


def test_breakout_valid_on_normal_displacement() -> None:
    real = breakout_both(
        transitions=[transition(1, BULL_BOS)],
        displacements=[displacement(1, UP, NORMAL, "0.50")],
    )
    assert real.breakout_state == BreakoutState.VALID_BREAK
    assert real.breakout_score == 50


def test_breakout_strong_on_fast_displacement() -> None:
    real = breakout_both(
        transitions=[transition(1, BULL_BOS)],
        displacements=[displacement(1, UP, FAST, "1.00")],
    )
    assert real.breakout_state == BreakoutState.STRONG_BREAK


def test_breakout_explosive_on_very_fast_displacement() -> None:
    real = breakout_both(
        transitions=[transition(1, BULL_BOS)],
        displacements=[displacement(1, UP, VERY_FAST, "3.00")],
    )
    assert real.breakout_state == BreakoutState.EXPLOSIVE_BREAK


def test_breakout_failed_on_immediate_reversal_choch() -> None:
    real = breakout_both(transitions=[transition(1, BULL_CHOCH), transition(2, BEAR_CHOCH)])
    assert real.breakout_state == BreakoutState.FAILED_BREAK
    assert real.breakout_score == 10


def test_breakout_not_failed_on_same_direction_choch_repeat() -> None:
    real = breakout_both(transitions=[transition(1, BULL_CHOCH), transition(2, BULL_CHOCH)])
    assert real.breakout_state != BreakoutState.FAILED_BREAK


def test_breakout_dispclsattrans_uses_max_not_first_match() -> None:
    """Two displacements share the newest transition's availability time with
    DIFFERENT classifications -- the source takes the MAX, not the first."""
    real = breakout_both(
        transitions=[transition(1, BULL_BOS)],
        displacements=[
            displacement(1, UP, NORMAL, "0.50", suffix="a"),
            displacement(1, UP, VERY_FAST, "3.00", suffix="b"),
        ],
    )
    assert real.breakout_state == BreakoutState.EXPLOSIVE_BREAK


def test_breakout_minus_two_slot_is_count_relative_not_fixed() -> None:
    """A partial (non-full) transition window: the FAILED_BREAK check must read
    trans{count-1}Type, not a hardcoded trans3Type. Three transitions retained
    (window capacity 4), with the whipsaw at positions 2-3."""
    real = breakout_both(
        transitions=[
            transition(1, BULL_BOS),
            transition(2, BULL_CHOCH),
            transition(3, BEAR_CHOCH),
        ]
    )
    assert real.breakout_state == BreakoutState.FAILED_BREAK


# ---------------------------------------------------------------------------
# Pullback: directed
# ---------------------------------------------------------------------------


def test_pullback_none_when_undetermined() -> None:
    real = pullback_both(current_state=state(UNDETERMINED, 10))
    assert real.pullback_state is None


def test_pullback_none_when_no_current_state() -> None:
    real = pullback_both()
    assert real.pullback_state is None


def test_pullback_shallow() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "100.00"),
            swing(2, SwingType.SWING_HIGH, "110.00"),
            swing(3, SwingType.SWING_LOW, "108.00"),  # 20% retrace
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.SHALLOW_PULLBACK


def test_pullback_healthy() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "100.00"),
            swing(2, SwingType.SWING_HIGH, "110.00"),
            swing(3, SwingType.SWING_LOW, "105.00"),  # 50% retrace
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.HEALTHY_PULLBACK


def test_pullback_deep() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "100.00"),
            swing(2, SwingType.SWING_HIGH, "110.00"),
            swing(3, SwingType.SWING_LOW, "101.00"),  # 90% retrace
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.DEEP_PULLBACK


def test_pullback_structural_failure_bullish() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "100.00"),
            swing(2, SwingType.SWING_HIGH, "110.00"),
            swing(3, SwingType.SWING_LOW, "95.00"),  # broke below origin
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.STRUCTURAL_FAILURE


def test_pullback_structural_failure_bearish() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_HIGH, "110.00"),
            swing(2, SwingType.SWING_LOW, "100.00"),
            swing(3, SwingType.SWING_HIGH, "115.00"),  # broke above origin
        ],
        current_state=state(BEARISH, 10),
    )
    assert real.pullback_state == PullbackState.STRUCTURAL_FAILURE


def test_pullback_none_when_no_counter_swing_yet() -> None:
    real = pullback_both(
        swings=[swing(1, SwingType.SWING_LOW, "100.00"), swing(2, SwingType.SWING_HIGH, "110.00")],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state is None


# ---------------------------------------------------------------------------
# Boundary: pullback depth bands, exactly at 0.382 / 0.618 / 1.0
# ---------------------------------------------------------------------------


def test_pullback_boundary_exactly_shallow_max() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "0.00"),
            swing(2, SwingType.SWING_HIGH, "1000.00"),
            swing(3, SwingType.SWING_LOW, "618.00"),  # depth exactly 0.382
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.SHALLOW_PULLBACK


def test_pullback_boundary_exactly_deep_min() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "0.00"),
            swing(2, SwingType.SWING_HIGH, "1000.00"),
            swing(3, SwingType.SWING_LOW, "382.00"),  # depth exactly 0.618
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.HEALTHY_PULLBACK


def test_pullback_boundary_exactly_at_origin() -> None:
    real = pullback_both(
        swings=[
            swing(1, SwingType.SWING_LOW, "0.00"),
            swing(2, SwingType.SWING_HIGH, "1000.00"),
            swing(3, SwingType.SWING_LOW, "0.00"),  # depth exactly 1.0
        ],
        current_state=state(BULLISH, 10),
    )
    assert real.pullback_state == PullbackState.DEEP_PULLBACK  # 1.0 is not > 1.0


# ---------------------------------------------------------------------------
# Invariance: POI lifecycle evidence never changes the classified state
# ---------------------------------------------------------------------------


def test_pullback_state_is_unaffected_by_poi_lifecycle_evidence() -> None:
    """`t3_engine.py` records a POI genuine-invalidation as SUPPORTING evidence
    only -- never as part of the state branch -- so the wire-only model (which
    carries no POI lifecycle at all) is correct to ignore it entirely."""
    swings = [
        swing(1, SwingType.SWING_LOW, "100.00"),
        swing(2, SwingType.SWING_HIGH, "110.00"),
        swing(3, SwingType.SWING_LOW, "95.00"),
    ]
    cs = state(BULLISH, 10)
    without = _assess_timeframe_pullback(Timeframe.M15, tuple(swings), cs, (), _CFG)

    from uuid import UUID

    from btmm_ai_scanner.config.enums import InternalSymbol
    from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
    from btmm_ai_scanner.contracts.types import SemVer
    from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
    from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition

    def _uid(n: int) -> UUID:
        return UUID(f"0193f350-1234-7abc-8def-{n:012x}")

    poi_transition = PoiLifecycleTransition(
        record_id=_uid(90001),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        poi_record_id=_uid(90002),
        transition_type=PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        triggering_candle_record_id=_uid(90003),
        event_time_utc=swings[-1].pivot_start_time_utc,
        availability_time_utc=swings[-1].availability_time_utc,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_uid(90004),
    )
    with_poi = _assess_timeframe_pullback(
        Timeframe.M15, tuple(swings), cs, (poi_transition,), _CFG
    )
    assert without.pullback_state == with_poi.pullback_state == PullbackState.STRUCTURAL_FAILURE


# ---------------------------------------------------------------------------
# Randomized
# ---------------------------------------------------------------------------


def test_randomized_momentum_sufficiency() -> None:
    rng = random.Random(555001)
    mismatches = []
    for _ in range(2000):
        _swings, _transitions, displacements, _state = random_history(rng)
        try:
            momentum_both(displacements)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_breakout_sufficiency() -> None:
    rng = random.Random(555002)
    mismatches = []
    for _ in range(2000):
        _swings, transitions, displacements, _state = random_history(rng)
        try:
            breakout_both(transitions, displacements)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_pullback_sufficiency() -> None:
    rng = random.Random(555003)
    mismatches = []
    for _ in range(2000):
        swings, _transitions, _displacements, current_state = random_history(rng)
        try:
            pullback_both(swings, current_state)
        except AssertionError as exc:
            mismatches.append(str(exc))
    assert mismatches == [], mismatches[:5]


def test_randomized_campaigns_cover_every_state() -> None:
    rng = random.Random(555004)
    seen_momentum: set[MomentumDirection] = set()
    seen_breakout: set[BreakoutState | None] = set()
    seen_pullback: set[PullbackState | None] = set()
    for _ in range(6000):
        swings, transitions, displacements, current_state = random_history(rng)
        seen_momentum.add(
            _assess_timeframe_momentum(Timeframe.M15, tuple(displacements), _CFG).direction
        )
        seen_breakout.add(
            _assess_timeframe_breakout(
                Timeframe.M15, tuple(transitions), (), tuple(displacements)
            ).breakout_state
        )
        seen_pullback.add(
            _assess_timeframe_pullback(
                Timeframe.M15, tuple(swings), current_state, (), _CFG
            ).pullback_state
        )
    assert seen_momentum == set(MomentumDirection)
    assert seen_breakout >= {
        None,
        BreakoutState.WEAK_BREAK,
        BreakoutState.VALID_BREAK,
        BreakoutState.STRONG_BREAK,
        BreakoutState.EXPLOSIVE_BREAK,
        BreakoutState.FAILED_BREAK,
    }
    assert seen_pullback >= {
        None,
        PullbackState.SHALLOW_PULLBACK,
        PullbackState.HEALTHY_PULLBACK,
        PullbackState.DEEP_PULLBACK,
        PullbackState.STRUCTURAL_FAILURE,
    }


def test_momentum_score_and_acceleration_tolerance_is_bounded() -> None:
    """The empirical proof behind `momentum_both`'s tolerance: 20000 random
    cases, requiring `direction` exact (as always), `momentum_score` within 1,
    every `acceleration` mismatch a STEADY<->non-STEADY tie break, and the
    mismatch RATE itself bounded -- an unbounded or dominant rate here would
    mean the model is actually wrong, not merely imprecise at exact Decimal
    ties perturbed by the wire's float64 cast. See `t3_pine_model.py`'s module
    docstring for why this specific pair of fields (and no other field in
    T1/T2/T3) needs this."""
    rng = random.Random(20260906)
    score_mismatches = 0
    accel_mismatches = 0
    for _ in range(20000):
        _swings, _transitions, displacements, _state = random_history(rng)
        real = _assess_timeframe_momentum(Timeframe.M15, tuple(displacements), _CFG)
        record = reduce_authoritative([], [], displacements, None)
        wire = momentum_from_transport(record)
        assert real.direction == wire.direction, (real.direction, wire.direction)
        diff = abs(real.momentum_score - wire.momentum_score)
        assert diff <= 1, (real.momentum_score, wire.momentum_score)
        if diff:
            score_mismatches += 1
        if real.acceleration != wire.acceleration:
            accel_mismatches += 1
            assert MomentumAcceleration.STEADY in (real.acceleration, wire.acceleration), (
                real.acceleration, wire.acceleration,
            )
    assert score_mismatches < 400, score_mismatches  # observed ~0.6% of 20000
    assert accel_mismatches < 40, accel_mismatches  # observed ~0.06% of 20000


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_mutation_pullback_using_bullish_only_formula_is_caught() -> None:
    """A port that hardcoded the bullish leg formula (ignoring the proven
    direction-symmetry) would get the bearish case wrong. `pullback_both`
    already runs both directions through the SAME formula; this pins a
    concrete bearish case the wrong (bullish-shaped) formula misclassifies."""
    swings = [
        swing(1, SwingType.SWING_HIGH, "110.00"),
        swing(2, SwingType.SWING_LOW, "100.00"),
        swing(3, SwingType.SWING_HIGH, "104.00"),  # bearish, healthy retrace
    ]
    cs = state(BEARISH, 10)
    real = pullback_both(swings, cs)
    assert real.pullback_state == PullbackState.HEALTHY_PULLBACK

    record = reduce_authoritative(swings, [], [], cs)
    bullish_shaped = (record.pbPullbackPrice - record.pbOriginPrice) / (
        record.pbImpulsePrice - record.pbOriginPrice
    )
    correct = (record.pbImpulsePrice - record.pbPullbackPrice) / (
        record.pbImpulsePrice - record.pbOriginPrice
    )
    assert bullish_shaped != correct


def test_mutation_breakout_ignoring_displacement_is_caught() -> None:
    """A port that treated every confirmed break as VALID_BREAK regardless of
    `dispClsAtTrans` would miss the STRONG/EXPLOSIVE upgrade and the WEAK
    downgrade alike."""
    real_explosive = breakout_both(
        transitions=[transition(1, BULL_BOS)],
        displacements=[displacement(1, UP, VERY_FAST, "3.00")],
    )
    real_weak = breakout_both(transitions=[transition(1, BULL_BOS)])
    assert real_explosive.breakout_state == BreakoutState.EXPLOSIVE_BREAK
    assert real_weak.breakout_state == BreakoutState.WEAK_BREAK
    assert real_explosive.breakout_state != real_weak.breakout_state
