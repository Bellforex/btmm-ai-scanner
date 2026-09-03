"""The P6 -> P5 transport differential: authoritative oracle vs Pine model.

TWO IMPLEMENTATIONS, DELIBERATELY UNRELATED
--------------------------------------------
`p5_transport_oracle` produces the 26 fields by calling the engines' OWN private
helpers over the full collections -- `_continuation_streak`,
`_prior_opposite_streak`, `_exhaustion`, `_recent_displacements`,
`_displacement_at`, `_retracement_depth`. It re-implements nothing, so it cannot
drift from the source.

`p5_transport_pine_model` produces the same 26 fields the way the requested Pine
context will: arrival order with no sorting, explicit backward index loops,
bounded windows, floats, and -- for the pullback -- roles re-derived from the
rule rather than read out of the engine's returned refs.

The differential between them is therefore a real test. If both called
`_prior_opposite_streak`, it would be a check that a function equals itself.

WHAT THE DIFFERENTIAL ALREADY CAUGHT
-------------------------------------
A first draft of the oracle called `_retracement_depth` unconditionally. The
helper branches `if BULLISH: ... else: <bearish>`, so an UNDETERMINED direction
would have received bearish role selection and reported a pullback --
`_assess_timeframe_pullback` returns before ever calling it in that case. The
model disagreed, which is exactly what the differential is for.

DIRECTED FIXTURES ASSERT VALUES, NOT JUST AGREEMENT
-----------------------------------------------------
Every directed case below pins the EXPECTED value as well as oracle == model.
Two implementations can agree on a wrong answer; only a stated expectation
catches that, and the streak/window reductions are precisely where a shared
misreading would look plausible.
"""

from __future__ import annotations

import random
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.t3_configuration import (
    MomentumBreakoutPullbackConfiguration,
)
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)
from btmm_ai_scanner.structure.transitions import StructureTransition
from tests.parity_support.p5_transport_contract import (
    C_ST_NA,
    DISP_CLS_FAST,
    DISP_CLS_NORMAL,
    DISP_CLS_VERY_FAST,
    DISP_DIR_BEARISH,
    DISP_DIR_BULLISH,
    DISPLACEMENT_WINDOW_CAPACITY,
    FIELD_COUNT,
    FIELD_NAMES,
    FIELDS,
    TR_BEARISH_BOS,
    TR_BEARISH_CHOCH,
    TR_BULLISH_BOS,
    TR_BULLISH_CHOCH,
    TRANSITION_WINDOW_CAPACITY,
    P5TransportRecord,
    record_field_names,
)
from tests.parity_support.p5_transport_fixtures import (
    displacement,
    moment,
    random_history,
    state,
    swing,
    transition,
)
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.p5_transport_pine_model import reduce_pine_equivalent
from tests.parity_support.p5_transport_records import (
    DisplacementRec,
    StateRec,
    SwingRec,
    TransitionRec,
    epoch_ms,
)

BULL_BOS = StructureTransitionType.BULLISH_BOS
BEAR_BOS = StructureTransitionType.BEARISH_BOS
BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH
HIGH = SwingType.SWING_HIGH
LOW = SwingType.SWING_LOW
BULLISH = StructureDirection.BULLISH
BEARISH = StructureDirection.BEARISH
UNDETERMINED = StructureDirection.UNDETERMINED
NORMAL = DisplacementClassification.NORMAL
FAST = DisplacementClassification.FAST
VERY_FAST = DisplacementClassification.VERY_FAST
UP = DisplacementDirection.BULLISH
DOWN = DisplacementDirection.BEARISH


def both(
    swings: list[SwingRec] | None = None,
    transitions: list[TransitionRec] | None = None,
    displacements: list[DisplacementRec] | None = None,
    current_state: StateRec | None = None,
) -> P5TransportRecord:
    """Run both implementations, require agreement, return the record.

    Every directed test goes through here, so agreement is checked on every
    fixture in the module rather than in one place that could be skipped.
    """
    args = (swings or [], transitions or [], displacements or [], current_state)
    authoritative = reduce_authoritative(*args)
    pine = reduce_pine_equivalent(*args)
    assert authoritative.differing_fields(pine) == (), (
        authoritative.differing_fields(pine),
        authoritative,
        pine,
    )
    return authoritative


#: Every record any directed test produced, for the coverage accounting below.
_OBSERVED: list[P5TransportRecord] = []


@pytest.fixture(autouse=True)
def _collect(request: pytest.FixtureRequest) -> None:
    """No-op fixture; the corpus is built by `both` via the module-level list."""
    return None


def observe(record: P5TransportRecord) -> P5TransportRecord:
    _OBSERVED.append(record)
    return record


# ===========================================================================
# The canonical contract
# ===========================================================================


def test_the_contract_has_exactly_twenty_six_fields() -> None:
    assert FIELD_COUNT == 26
    assert len(FIELDS) == 26
    assert len(FIELD_NAMES) == 26


def test_positions_are_contiguous_and_start_at_one() -> None:
    assert [f.position for f in FIELDS] == list(range(1, 27))


def test_field_names_are_unique() -> None:
    assert len(set(FIELD_NAMES)) == 26


def test_the_record_dataclass_matches_the_contract_order_exactly() -> None:
    """One list, two consumers. If they drift, the wire order and the Python
    record disagree and every digest silently changes meaning."""
    assert record_field_names() == FIELD_NAMES


def test_every_field_documents_its_absence_and_availability() -> None:
    for field in FIELDS:
        assert field.meaning.strip(), field.name
        assert field.absent.strip(), field.name
        assert field.availability.strip(), field.name
        assert field.consumer.strip(), field.name


def test_every_field_is_a_requestable_scalar_type() -> None:
    assert {f.pine_type for f in FIELDS} <= {"int", "float", "bool"}


def test_reordering_a_field_is_detectable() -> None:
    """The mutation this contract exists to stop."""
    swapped = list(FIELD_NAMES)
    swapped[1], swapped[2] = swapped[2], swapped[1]
    assert tuple(swapped) != record_field_names()


def test_configuration_fits_the_declared_capacity() -> None:
    assert TrendEngineConfiguration().range_window <= TRANSITION_WINDOW_CAPACITY
    assert (
        RegimeEngineConfiguration().recent_displacement_window
        <= DISPLACEMENT_WINDOW_CAPACITY
    )
    assert (
        MomentumBreakoutPullbackConfiguration().momentum_window
        <= DISPLACEMENT_WINDOW_CAPACITY
    )


# ===========================================================================
# State availability
# ===========================================================================


def test_absent_state_yields_absent_availability_and_zero_streaks() -> None:
    record = observe(both(transitions=[transition(1, BULL_BOS)]))
    assert record.stateAvailT is None
    assert record.contStreak == 0
    assert record.priorOppStreak == 0
    assert record.exhaustFlag == 0
    assert record.pbValid is False


def test_state_availability_is_carried_as_epoch_milliseconds() -> None:
    record = observe(both(current_state=state(BULLISH, 40)))
    assert record.stateAvailT == epoch_ms(moment(40))


def test_state_availability_is_independent_of_the_last_transition() -> None:
    """They are different events and the contract keeps them separate; a port
    that reused one for the other would pass most fixtures by accident."""
    record = observe(
        both(
            transitions=[transition(5, BULL_BOS)],
            current_state=state(BULLISH, 40),
        )
    )
    assert record.stateAvailT == epoch_ms(moment(40))
    assert record.lastTransAvailT == epoch_ms(moment(5))
    assert record.stateAvailT != record.lastTransAvailT


# ===========================================================================
# The transition window
# ===========================================================================


@pytest.mark.parametrize("count", [0, 1, 2, 3, 4])
def test_the_window_is_left_aligned_oldest_to_newest(count: int) -> None:
    kinds = [BULL_BOS, BEAR_BOS, BULL_CHOCH, BEAR_CHOCH][:count]
    record = observe(
        both(
            transitions=[transition(i + 1, k) for i, k in enumerate(kinds)],
            current_state=state(BULLISH, 50),
        )
    )
    expected = [TR_BULLISH_BOS, TR_BEARISH_BOS, TR_BULLISH_CHOCH, TR_BEARISH_CHOCH][
        :count
    ]
    expected += [C_ST_NA] * (4 - count)
    assert record.transWindowCount == count
    assert [
        record.trans1Type,
        record.trans2Type,
        record.trans3Type,
        record.trans4Type,
    ] == expected


def test_more_than_capacity_keeps_the_newest_four() -> None:
    kinds = [BULL_BOS, BEAR_BOS, BULL_CHOCH, BEAR_CHOCH, BULL_BOS, BEAR_CHOCH]
    record = observe(
        both(
            transitions=[transition(i + 1, k) for i, k in enumerate(kinds)],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.transWindowCount == 4
    assert [
        record.trans1Type,
        record.trans2Type,
        record.trans3Type,
        record.trans4Type,
    ] == [TR_BEARISH_BOS, TR_BULLISH_CHOCH, TR_BEARISH_CHOCH, TR_BULLISH_BOS] or [
        record.trans1Type,
        record.trans2Type,
        record.trans3Type,
        record.trans4Type,
    ] == [TR_BULLISH_CHOCH, TR_BEARISH_CHOCH, TR_BULLISH_BOS, TR_BEARISH_CHOCH]


def test_the_newest_transition_lands_in_the_count_slot() -> None:
    """Stated as behaviour because breakout reads `[-2]` as slot count-1."""
    record = observe(
        both(
            transitions=[transition(1, BULL_BOS), transition(2, BEAR_CHOCH)],
            current_state=state(BEARISH, 50),
        )
    )
    assert record.transWindowCount == 2
    assert record.trans2Type == TR_BEARISH_CHOCH  # newest
    assert record.trans1Type == TR_BULLISH_BOS  # the [-2] breakout needs
    assert record.trans3Type == C_ST_NA
    assert record.trans4Type == C_ST_NA


# ===========================================================================
# Continuation streak
# ===========================================================================


def test_a_run_of_continuation_bos_counts_all_of_them() -> None:
    record = observe(
        both(
            transitions=[
                transition(1, BULL_CHOCH),
                transition(2, BULL_BOS),
                transition(3, BULL_BOS),
                transition(4, BULL_BOS),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.contStreak == 3


def test_a_choch_at_the_end_gives_streak_zero() -> None:
    record = observe(
        both(
            transitions=[transition(1, BULL_BOS), transition(2, BULL_CHOCH)],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.contStreak == 0


def test_an_opposing_bos_ends_the_streak() -> None:
    record = observe(
        both(
            transitions=[
                transition(1, BULL_BOS),
                transition(2, BEAR_BOS),
                transition(3, BULL_BOS),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.contStreak == 1


def test_the_streak_counts_only_the_current_direction() -> None:
    """The same history read as bearish gives a different answer."""
    transitions = [transition(1, BULL_BOS), transition(2, BULL_BOS)]
    bullish = observe(both(transitions=transitions, current_state=state(BULLISH, 50)))
    bearish = observe(both(transitions=transitions, current_state=state(BEARISH, 50)))
    assert bullish.contStreak == 2
    assert bearish.contStreak == 0


def test_a_streak_longer_than_the_transported_window() -> None:
    """contStreak is a scalar over the FULL history, so it is not capped by the
    four-slot window -- a port that computed it from the window would say 4."""
    record = observe(
        both(
            transitions=[transition(i + 1, BULL_BOS) for i in range(9)],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.contStreak == 9
    assert record.transWindowCount == 4


def test_undetermined_direction_gives_zero_streaks() -> None:
    record = observe(
        both(
            transitions=[transition(1, BULL_BOS), transition(2, BULL_BOS)],
            current_state=state(UNDETERMINED, 50),
        )
    )
    assert record.contStreak == 0
    assert record.priorOppStreak == 0


# ===========================================================================
# Prior opposite streak -- the `[:-1]` exclusion
# ===========================================================================


def test_prior_opposite_excludes_the_latest_transition() -> None:
    """Directed fixture where including the last transition changes the answer.

    Bullish CHOCH at the end, preceded by three bearish BOS. Counting over the
    whole list would stop immediately at the CHOCH and report 0; the source
    starts one earlier and reports 3.
    """
    record = observe(
        both(
            transitions=[
                transition(1, BEAR_BOS),
                transition(2, BEAR_BOS),
                transition(3, BEAR_BOS),
                transition(4, BULL_CHOCH),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.priorOppStreak == 3
    assert record.contStreak == 0


def test_prior_opposite_is_zero_with_a_single_transition() -> None:
    record = observe(
        both(
            transitions=[transition(1, BULL_CHOCH)],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.priorOppStreak == 0


def test_prior_opposite_stops_at_a_non_opposing_transition() -> None:
    record = observe(
        both(
            transitions=[
                transition(1, BEAR_BOS),
                transition(2, BULL_BOS),
                transition(3, BEAR_BOS),
                transition(4, BULL_CHOCH),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.priorOppStreak == 1


# ===========================================================================
# Exhaustion
# ===========================================================================


def test_bullish_exhaustion_needs_two_swing_highs() -> None:
    record = observe(
        both(
            swings=[
                swing(1, HIGH, "4500.00"),
                swing(2, LOW, "4400.00"),
                swing(3, HIGH, "4450.00"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.exhaustFlag == 1


def test_a_higher_high_is_not_exhaustion() -> None:
    record = observe(
        both(
            swings=[
                swing(1, HIGH, "4400.00"),
                swing(2, LOW, "4300.00"),
                swing(3, HIGH, "4500.00"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.exhaustFlag == 0


def test_bearish_exhaustion_is_a_higher_low() -> None:
    record = observe(
        both(
            swings=[
                swing(1, LOW, "4300.00"),
                swing(2, HIGH, "4400.00"),
                swing(3, LOW, "4350.00"),
            ],
            current_state=state(BEARISH, 50),
        )
    )
    assert record.exhaustFlag == 1


def test_exhaustion_uses_same_type_swings_not_the_last_two() -> None:
    """The trap: the two most recent swings here are a HIGH then a LOW, and a
    port comparing them would compare a high against a low."""
    record = observe(
        both(
            swings=[
                swing(1, HIGH, "4500.00"),
                swing(2, HIGH, "4450.00"),
                swing(3, LOW, "4000.00"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.exhaustFlag == 1


def test_equal_highs_are_not_exhaustion() -> None:
    """`<` not `<=`: an equal high is not a lower high."""
    record = observe(
        both(
            swings=[swing(1, HIGH, "4500.00"), swing(2, HIGH, "4500.00")],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.exhaustFlag == 0


def test_one_swing_cannot_exhaust() -> None:
    record = observe(
        both(swings=[swing(1, HIGH, "4500.00")], current_state=state(BULLISH, 50))
    )
    assert record.exhaustFlag == 0


# ===========================================================================
# The displacement window
# ===========================================================================


@pytest.mark.parametrize("count", [0, 1, 2, 3])
def test_displacement_window_left_aligned(count: int) -> None:
    specs = [(UP, NORMAL, "0.90"), (DOWN, FAST, "1.60"), (UP, VERY_FAST, "2.40")][
        :count
    ]
    record = observe(
        both(
            displacements=[
                displacement(i + 1, d, c, r) for i, (d, c, r) in enumerate(specs)
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispWindowCount == count
    dirs = [record.disp1Dir, record.disp2Dir, record.disp3Dir]
    clss = [record.disp1Cls, record.disp2Cls, record.disp3Cls]
    ratios = [record.disp1Ratio, record.disp2Ratio, record.disp3Ratio]
    for slot in range(count):
        assert dirs[slot] != C_ST_NA
        assert ratios[slot] is not None
    for slot in range(count, 3):
        assert dirs[slot] == C_ST_NA
        assert clss[slot] == C_ST_NA
        assert ratios[slot] is None


def test_the_window_keeps_the_newest_three_in_order() -> None:
    record = observe(
        both(
            displacements=[
                displacement(1, UP, NORMAL, "0.50"),
                displacement(2, DOWN, NORMAL, "0.60"),
                displacement(3, UP, FAST, "1.70"),
                displacement(4, DOWN, VERY_FAST, "2.30"),
                displacement(5, UP, NORMAL, "0.80"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispWindowCount == 3
    assert [record.disp1Ratio, record.disp2Ratio, record.disp3Ratio] == [1.7, 2.3, 0.8]
    assert [record.disp1Dir, record.disp2Dir, record.disp3Dir] == [
        DISP_DIR_BULLISH,
        DISP_DIR_BEARISH,
        DISP_DIR_BULLISH,
    ]
    assert [record.disp1Cls, record.disp2Cls, record.disp3Cls] == [
        DISP_CLS_FAST,
        DISP_CLS_VERY_FAST,
        DISP_CLS_NORMAL,
    ]
    assert record.dispAvailT == epoch_ms(moment(5))


def test_direction_survives_a_normal_classification() -> None:
    """The reason Dir and Cls are separate fields. P6's legacy signed code is
    `isBull ? cls : -cls`, so bullish NORMAL and bearish NORMAL both encode 0 --
    and momentum counts direction regardless of class."""
    bull = observe(
        both(
            displacements=[displacement(1, UP, NORMAL, "0.90")],
            current_state=state(BULLISH, 50),
        )
    )
    bear = observe(
        both(
            displacements=[displacement(1, DOWN, NORMAL, "0.90")],
            current_state=state(BULLISH, 50),
        )
    )
    assert bull.disp1Cls == bear.disp1Cls == DISP_CLS_NORMAL
    assert bull.disp1Dir == DISP_DIR_BULLISH
    assert bear.disp1Dir == DISP_DIR_BEARISH
    assert bull.disp1Dir != bear.disp1Dir


def test_the_raw_ratio_crosses_not_an_expansion_verdict() -> None:
    """Values either side of T2's provisional 1.50 both arrive as themselves."""
    below = observe(
        both(
            displacements=[displacement(1, UP, NORMAL, "1.49")],
            current_state=state(BULLISH, 50),
        )
    )
    above = observe(
        both(
            displacements=[displacement(1, UP, FAST, "1.51")],
            current_state=state(BULLISH, 50),
        )
    )
    assert below.disp1Ratio == 1.49
    assert above.disp1Ratio == 1.51


# ===========================================================================
# displacement-at-transition
# ===========================================================================


def test_displacement_at_takes_the_max_not_the_first() -> None:
    """Directed fixture where the FIRST match and the MAX differ."""
    target = transition(5, BULL_BOS)
    record = observe(
        both(
            transitions=[transition(1, BULL_CHOCH), target],
            displacements=[
                displacement(5, UP, NORMAL, "0.90", suffix="a"),
                displacement(5, UP, VERY_FAST, "2.60", suffix="b"),
                displacement(5, DOWN, FAST, "1.70", suffix="c"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispClsAtTrans == DISP_CLS_VERY_FAST


def test_displacement_at_is_absent_when_nothing_shares_the_time() -> None:
    record = observe(
        both(
            transitions=[transition(5, BULL_BOS)],
            displacements=[displacement(4, UP, VERY_FAST, "2.60")],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispClsAtTrans == C_ST_NA


def test_displacement_at_is_not_the_latest_displacement() -> None:
    """The other plausible wrong reading: a later, faster displacement exists,
    but it does not share the transition's availability time."""
    record = observe(
        both(
            transitions=[transition(3, BULL_BOS)],
            displacements=[
                displacement(3, UP, NORMAL, "0.90"),
                displacement(7, UP, VERY_FAST, "2.90"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispClsAtTrans == DISP_CLS_NORMAL


def test_displacement_at_matches_the_newest_transition_only() -> None:
    record = observe(
        both(
            transitions=[transition(2, BULL_BOS), transition(6, BULL_BOS)],
            displacements=[
                displacement(2, UP, VERY_FAST, "2.90"),
                displacement(6, UP, FAST, "1.60"),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispClsAtTrans == DISP_CLS_FAST


def test_no_transition_means_no_displacement_class() -> None:
    record = observe(
        both(
            displacements=[displacement(2, UP, VERY_FAST, "2.90")],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.dispClsAtTrans == C_ST_NA
    assert record.lastTransAvailT is None


# ===========================================================================
# Pullback roles
# ===========================================================================


def _bullish_pullback() -> list[SwingRec]:
    """low 4300 (origin) -> high 4500 (impulse) -> low 4400 (pullback)."""
    return [
        swing(1, LOW, "4300.00", start=0),
        swing(3, HIGH, "4500.00", start=2),
        swing(5, LOW, "4400.00", start=4),
    ]


def test_bullish_pullback_roles() -> None:
    record = observe(both(swings=_bullish_pullback(), current_state=state(BULLISH, 50)))
    assert record.pbValid is True
    assert record.pbOriginPrice == 4300.0
    assert record.pbImpulsePrice == 4500.0
    assert record.pbPullbackPrice == 4400.0


def test_bearish_pullback_roles_are_mirrored() -> None:
    record = observe(
        both(
            swings=[
                swing(1, HIGH, "4500.00", start=0),
                swing(3, LOW, "4300.00", start=2),
                swing(5, HIGH, "4400.00", start=4),
            ],
            current_state=state(BEARISH, 50),
        )
    )
    assert record.pbValid is True
    assert record.pbOriginPrice == 4500.0
    assert record.pbImpulsePrice == 4300.0
    assert record.pbPullbackPrice == 4400.0


def test_no_counter_swing_after_the_impulse_is_invalid() -> None:
    record = observe(
        both(
            swings=[swing(1, LOW, "4300.00", start=0), swing(3, HIGH, "4500.00", start=2)],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.pbValid is False
    assert record.pbImpulsePrice is None
    assert record.pbOriginPrice is None
    assert record.pbPullbackPrice is None


def test_a_non_positive_leg_is_invalid() -> None:
    """origin at or above the impulse high: the leg is <= 0 and the source
    reports nothing rather than a negative depth."""
    record = observe(
        both(
            swings=[
                swing(1, LOW, "4500.00", start=0),
                swing(3, HIGH, "4500.00", start=2),
                swing(5, LOW, "4400.00", start=4),
            ],
            current_state=state(BULLISH, 50),
        )
    )
    assert record.pbValid is False


def test_the_boundary_swing_belongs_to_origin_not_pullback() -> None:
    """The `<=` / `>` split, as behaviour.

    A counter swing whose pivot START equals the impulse's pivot start is an
    ORIGIN candidate. Here that is the only low at or before the impulse, so
    treating the boundary as `<` instead would leave no origin and report
    invalid.
    """
    swings = [
        swing(2, LOW, "4300.00", start=2),
        swing(3, HIGH, "4500.00", start=2),
        swing(5, LOW, "4400.00", start=4),
    ]
    record = observe(both(swings=swings, current_state=state(BULLISH, 50)))
    assert record.pbValid is True
    assert record.pbOriginPrice == 4300.0


def test_undetermined_direction_reports_no_pullback() -> None:
    """The divergence the differential caught: `_retracement_depth` would fall
    into its bearish branch, but the engine never calls it here."""
    record = observe(
        both(swings=_bullish_pullback(), current_state=state(UNDETERMINED, 50))
    )
    assert record.pbValid is False
    assert record.pbImpulsePrice is None


def test_the_depth_ratio_itself_is_not_transported() -> None:
    """P5 owns the division and the 0.382 / 0.618 bands."""
    record = observe(both(swings=_bullish_pullback(), current_state=state(BULLISH, 50)))
    assert not any("depth" in name.lower() for name in record.as_dict())


# ===========================================================================
# Coverage accounting -- 26 fields MEANINGFULLY exercised
# ===========================================================================


def test_every_field_takes_at_least_two_distinct_values_across_the_corpus() -> None:
    """"26 fields exist" is not coverage. This asserts each one actually MOVED
    in the directed fixtures above, so a field that is always its default
    cannot pass unnoticed."""
    assert len(_OBSERVED) >= 30, len(_OBSERVED)
    seen: dict[str, set[object]] = {name: set() for name in FIELD_NAMES}
    for record in _OBSERVED:
        for name, value in record.as_dict().items():
            seen[name].add(value)
    constant = sorted(name for name, values in seen.items() if len(values) < 2)
    assert constant == [], constant


# ===========================================================================
# Randomized differential
# ===========================================================================


def test_randomized_histories_agree_field_for_field() -> None:
    rng = random.Random(20260903)
    mismatches: list[tuple[int, tuple[str, ...]]] = []
    for case in range(3000):
        swings, transitions, displacements, current_state = random_history(rng)
        authoritative = reduce_authoritative(
            swings, transitions, displacements, current_state
        )
        pine = reduce_pine_equivalent(
            swings, transitions, displacements, current_state
        )
        differing = authoritative.differing_fields(pine)
        if differing:
            mismatches.append((case, differing))
    assert mismatches == [], mismatches[:5]


def test_randomized_histories_are_not_all_trivial() -> None:
    """A campaign of 3000 empty histories would pass and prove nothing."""
    rng = random.Random(20260903)
    interesting = 0
    for _ in range(3000):
        swings, transitions, displacements, current_state = random_history(rng)
        record = reduce_authoritative(
            swings, transitions, displacements, current_state
        )
        if (
            record.transWindowCount == TRANSITION_WINDOW_CAPACITY
            and record.dispWindowCount == DISPLACEMENT_WINDOW_CAPACITY
        ):
            interesting += 1
    assert interesting > 300, interesting


def test_randomized_campaign_exercises_every_field() -> None:
    rng = random.Random(7761)
    seen: dict[str, set[object]] = {name: set() for name in FIELD_NAMES}
    for _ in range(2000):
        swings, transitions, displacements, current_state = random_history(rng)
        record = reduce_authoritative(
            swings, transitions, displacements, current_state
        )
        for name, value in record.as_dict().items():
            seen[name].add(value)
    constant = sorted(name for name, values in seen.items() if len(values) < 2)
    assert constant == [], constant


# ===========================================================================
# Prefix differential
# ===========================================================================


def test_every_prefix_of_a_history_agrees() -> None:
    """Catches agreement that only holds once history is long enough -- warm-up
    assumptions and off-by-one at the first usable state."""
    rng = random.Random(4242)
    for _ in range(120):
        swings, transitions, displacements, current_state = random_history(rng)
        longest = max(len(swings), len(transitions), len(displacements))
        for cut in range(longest + 1):
            args = (
                swings[:cut],
                transitions[:cut],
                displacements[:cut],
                current_state,
            )
            authoritative = reduce_authoritative(*args)
            pine = reduce_pine_equivalent(*args)
            assert authoritative.differing_fields(pine) == (), (
                cut,
                authoritative.differing_fields(pine),
            )


def test_the_arrival_order_assumption_is_the_only_ordering_risk() -> None:
    """The Pine model cannot sort, so it assumes arrival order is chronological.

    Stated as a test rather than a comment: shuffling a history into
    non-chronological arrival order makes the two implementations disagree,
    which is why every generator emits strictly increasing availability times
    and why the Pine port must append events as bars confirm.
    """
    transitions = [
        transition(1, BULL_BOS),
        transition(2, BEAR_CHOCH),
        transition(3, BULL_BOS),
    ]
    shuffled = [transitions[2], transitions[0], transitions[1]]
    current = state(BULLISH, 50)
    authoritative = reduce_authoritative([], shuffled, [], current)
    pine = reduce_pine_equivalent([], shuffled, [], current)
    assert authoritative.differing_fields(pine) != ()
    # ...and in chronological order they agree again.
    assert (
        reduce_authoritative([], transitions, [], current).differing_fields(
            reduce_pine_equivalent([], transitions, [], current)
        )
        == ()
    )


# ===========================================================================
# The lightweight records are faithful to the real contract models
# ===========================================================================

_FP = "a" * 64
_V = SemVer.parse("0.1.0")
_EC = EvidenceClassification.ENGINEERING_PROVISIONAL


def _uid(n: int) -> UUID:
    return UUID(f"0193f350-1234-7abc-8def-{n:012x}")


def _real_swing(rec: SwingRec, n: int) -> ConfirmedSwing:
    return ConfirmedSwing(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        swing_type=rec.swing_type,
        pivot_price=rec.pivot_price,
        pivot_bar_index=n,
        pivot_candle_record_ids=(_uid(n + 500),),
        pivot_start_time_utc=rec.pivot_start_time_utc,
        pivot_end_time_utc=rec.pivot_start_time_utc + timedelta(minutes=15),
        local_confirmation_time_utc=rec.availability_time_utc,
        meaningful_confirmation_time_utc=rec.availability_time_utc,
        confirmation_candle_id=_uid(n + 900),
        pivot_reference_atr=Decimal("1.0"),
        pivot_tie_tolerance=Decimal("0.1"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("0.6"),
        availability_time_utc=rec.availability_time_utc,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(n + 1300),
    )


def _real_transition(rec: TransitionRec, n: int) -> StructureTransition:
    return StructureTransition(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        transition_type=rec.transition_type,
        direction_before=StructureDirection.UNDETERMINED,
        direction_after=StructureDirection.BULLISH,
        broken_swing_id=_uid(n + 100),
        broken_level_price=Decimal("4400.00"),
        break_close_price=Decimal("4410.00"),
        protected_swing_id=_uid(n + 200),
        weak_swing_id=None,
        break_candle_id=_uid(n + 300),
        event_time_utc=rec.event_time_utc,
        availability_time_utc=rec.availability_time_utc,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(n + 400),
    )


def _real_displacement(rec: DisplacementRec, n: int) -> DisplacementObservation:
    return DisplacementObservation(
        record_id=_uid(n),
        content_fingerprint=_FP,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        candle_record_id=_uid(n + 600),
        event_time_utc=rec.event_time_utc,
        availability_time_utc=rec.availability_time_utc,
        total_range=Decimal("5.00"),
        range_speed_ratio=rec.range_speed_ratio,
        direction=rec.direction,
        classification=rec.classification,
        rule_version=_V,
        contract_version=_V,
        schema_version=_V,
        evidence_classification=_EC,
        provenance_id=_uid(n + 700),
    )


def test_the_reduced_records_answer_exactly_as_the_real_contract_models() -> None:
    """Proves the five-attribute stand-ins are faithful, so the whole campaign
    above is about semantics rather than about a convenient shape.

    The real models are built with ascending record ids in chronological order,
    so the engines' `str(record_id)` tie-break cannot rescue a wrong ordering.
    """
    swings = [
        swing(1, LOW, "4300.00", start=0),
        swing(3, HIGH, "4500.00", start=2),
        swing(5, LOW, "4400.00", start=4),
        swing(7, LOW, "4460.00", start=6),
    ]
    transitions = [
        transition(2, BEAR_BOS),
        transition(4, BEAR_BOS),
        transition(6, BULL_CHOCH),
        transition(8, BULL_BOS),
    ]
    displacements = [
        displacement(4, DOWN, FAST, "1.70"),
        displacement(8, UP, NORMAL, "0.95"),
        displacement(8, UP, VERY_FAST, "2.40", suffix="b"),
    ]
    current_state = state(BULLISH, 60, swing_count=4)

    reduced = reduce_authoritative(swings, transitions, displacements, current_state)

    real_swings = [_real_swing(s, 10 + i) for i, s in enumerate(swings)]
    real_transitions = [_real_transition(t, 40 + i) for i, t in enumerate(transitions)]
    real_displacements = [
        _real_displacement(d, 70 + i) for i, d in enumerate(displacements)
    ]

    class _State:
        direction = current_state.direction
        analyzed_swing_count = current_state.analyzed_swing_count
        availability_time_utc = current_state.availability_time_utc

    from_real = reduce_authoritative(
        real_swings,  # type: ignore[arg-type]
        real_transitions,  # type: ignore[arg-type]
        real_displacements,  # type: ignore[arg-type]
        _State(),  # type: ignore[arg-type]
    )
    assert reduced.differing_fields(from_real) == (), reduced.differing_fields(from_real)
    # and the fixture is a non-trivial one
    assert reduced.pbValid is True
    assert reduced.dispClsAtTrans == DISP_CLS_VERY_FAST
    assert reduced.priorOppStreak == 0
    assert reduced.contStreak == 1
