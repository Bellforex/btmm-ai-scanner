"""The PINE-EQUIVALENT P5 transport reduction, written independently.

Test/parity tooling only.

This is what the requested-context Pine function will do, expressed in Python so
it can be differentiated against the authoritative oracle before a line of Pine
is written. It deliberately shares NOTHING with `p5_transport_oracle` except the
contract constants and the record shapes -- no engine helpers, no imports of the
oracle. If both files called `_prior_opposite_streak`, the parity test would be
checking that a function equals itself.

HOW IT DIFFERS FROM THE ORACLE, ON PURPOSE
-------------------------------------------
* **Arrival order, no sorting.** Pine appends events as bars confirm; it has no
  ``record_id`` and cannot reproduce the engines' ``(availability, event,
  str(record_id))`` sort. The model therefore consumes the sequence as given.
  That is an ASSUMPTION about the input -- that arrival order is chronological
  and no two events share an availability/event pair -- and it is tested rather
  than hidden: see `test_the_arrival_order_assumption_is_the_only_ordering_risk`.
* **Explicit backward index loops**, the way the Pine will be written, instead of
  ``reversed()`` over a slice.
* **The pullback roles are re-derived** from the rule, not read out of
  `_retracement_depth`'s returned refs. This is the reduction most likely to be
  ported wrong, so the model earns its independence precisely here.
* **Floats, not Decimal**, matching Pine's only numeric type.

WHAT IT KEEPS UNBOUNDED, AND WHY THAT IS STILL FAITHFUL
--------------------------------------------------------
`contStreak`, `priorOppStreak`, `exhaustFlag` and `dispClsAtTrans` scan the
whole event history. That is not a violation of the bounded-transport rule: the
requested Pine context already HOLDS those arrays for its own 1250-bar window,
and scanning them there is exactly what the closed P6 projection already does.
What is bounded is what crosses the wire -- four transition types and three
displacements -- not what the context may read while computing a scalar.
"""

from __future__ import annotations

from collections.abc import Sequence

from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)

from .p5_transport_contract import (
    C_ST_NA,
    DISP_CLS_FAST,
    DISP_CLS_NORMAL,
    DISP_CLS_VERY_FAST,
    DISP_DIR_BEARISH,
    DISP_DIR_BULLISH,
    DISPLACEMENT_WINDOW_CAPACITY,
    TR_BEARISH_BOS,
    TR_BEARISH_CHOCH,
    TR_BULLISH_BOS,
    TR_BULLISH_CHOCH,
    TRANSITION_WINDOW_CAPACITY,
    P5TransportRecord,
)
from .p5_transport_records import (
    DisplacementRec,
    StateRec,
    SwingRec,
    TransitionRec,
    epoch_ms,
)

_TRANS_CODE = {
    StructureTransitionType.BULLISH_BOS: TR_BULLISH_BOS,
    StructureTransitionType.BEARISH_BOS: TR_BEARISH_BOS,
    StructureTransitionType.BULLISH_CHOCH: TR_BULLISH_CHOCH,
    StructureTransitionType.BEARISH_CHOCH: TR_BEARISH_CHOCH,
}
_DISP_DIR_CODE = {
    DisplacementDirection.BULLISH: DISP_DIR_BULLISH,
    DisplacementDirection.BEARISH: DISP_DIR_BEARISH,
}
_DISP_CLS_CODE = {
    DisplacementClassification.NORMAL: DISP_CLS_NORMAL,
    DisplacementClassification.FAST: DISP_CLS_FAST,
    DisplacementClassification.VERY_FAST: DISP_CLS_VERY_FAST,
}

#: Continuation BOS for a direction: the transition that EXTENDS the trend.
_CONTINUATION = {
    StructureDirection.BULLISH: TR_BULLISH_BOS,
    StructureDirection.BEARISH: TR_BEARISH_BOS,
}
#: Opposing BOS: the transition that breaks the other way.
_OPPOSING = {
    StructureDirection.BULLISH: TR_BEARISH_BOS,
    StructureDirection.BEARISH: TR_BULLISH_BOS,
}
_CHOCH_CODES = (TR_BULLISH_CHOCH, TR_BEARISH_CHOCH)


def _continuation_streak(codes: Sequence[int], direction: StructureDirection) -> int:
    """Walk back from the newest while the code is the continuation BOS."""
    if direction not in _CONTINUATION:
        return 0
    target = _CONTINUATION[direction]
    streak = 0
    index = len(codes) - 1
    while index >= 0 and codes[index] == target:
        streak += 1
        index -= 1
    return streak


def _prior_opposite_streak(codes: Sequence[int], direction: StructureDirection) -> int:
    """Same walk, but starting one BEFORE the newest: the latest transition is
    the CHOCH being explained and is excluded from its own evidence."""
    if direction not in _OPPOSING or not codes:
        return 0
    target = _OPPOSING[direction]
    streak = 0
    index = len(codes) - 2
    while index >= 0 and codes[index] == target:
        streak += 1
        index -= 1
    return streak


def _exhaustion_flag(
    swings: Sequence[SwingRec], direction: StructureDirection
) -> int:
    """Lower high while bullish, higher low while bearish, on the two most
    recent swings OF THAT TYPE -- not the two most recent swings."""
    if direction is StructureDirection.BULLISH:
        wanted = SwingType.SWING_HIGH
    elif direction is StructureDirection.BEARISH:
        wanted = SwingType.SWING_LOW
    else:
        return 0

    latest: SwingRec | None = None
    previous: SwingRec | None = None
    index = len(swings) - 1
    while index >= 0 and previous is None:
        swing = swings[index]
        if swing.swing_type is wanted:
            if latest is None:
                latest = swing
            else:
                previous = swing
        index -= 1
    if latest is None or previous is None:
        return 0

    if direction is StructureDirection.BULLISH:
        return 1 if latest.pivot_price < previous.pivot_price else 0
    return 1 if latest.pivot_price > previous.pivot_price else 0


def _displacement_class_at(
    displacements: Sequence[DisplacementRec], availability: object
) -> int:
    """MAX class among every displacement sharing the availability time.

    Written as a running maximum over the whole array, which is how Pine will do
    it, and which cannot accidentally become "the first match" or "the latest
    displacement" the way an early-return loop can.
    """
    best = C_ST_NA
    for observation in displacements:
        if observation.availability_time_utc == availability:
            code = _DISP_CLS_CODE[observation.classification]
            if best is C_ST_NA or code > best:
                best = code
    return best


def _pullback_prices(
    swings: Sequence[SwingRec], direction: StructureDirection
) -> tuple[float | None, float | None, float | None, bool]:
    """Re-derived from the rule, deliberately not from the engine's refs.

    Bullish: impulse is the last SWING_HIGH; origin is the last SWING_LOW whose
    pivot start is AT OR BEFORE the impulse's; pullback is the last SWING_LOW
    whose pivot start is STRICTLY AFTER it. The leg must be strictly positive.
    Bearish mirrors on the opposite swing type.
    """
    if direction is StructureDirection.BULLISH:
        impulse_type, counter_type = SwingType.SWING_HIGH, SwingType.SWING_LOW
    elif direction is StructureDirection.BEARISH:
        impulse_type, counter_type = SwingType.SWING_LOW, SwingType.SWING_HIGH
    else:
        return None, None, None, False

    impulse: SwingRec | None = None
    for index in range(len(swings) - 1, -1, -1):
        if swings[index].swing_type is impulse_type:
            impulse = swings[index]
            break
    if impulse is None:
        return None, None, None, False

    origin: SwingRec | None = None
    pullback: SwingRec | None = None
    for swing in swings:
        if swing.swing_type is not counter_type:
            continue
        if swing.pivot_start_time_utc <= impulse.pivot_start_time_utc:
            origin = swing
        else:
            pullback = swing
    if origin is None or pullback is None:
        return None, None, None, False

    if direction is StructureDirection.BULLISH:
        leg = impulse.pivot_price - origin.pivot_price
    else:
        leg = origin.pivot_price - impulse.pivot_price
    if leg <= 0:
        return None, None, None, False

    return (
        float(impulse.pivot_price),
        float(origin.pivot_price),
        float(pullback.pivot_price),
        True,
    )


def reduce_pine_equivalent(
    swings: Sequence[SwingRec],
    transitions: Sequence[TransitionRec],
    displacements: Sequence[DisplacementRec],
    current_state: StateRec | None,
) -> P5TransportRecord:
    """The bounded reduction, consuming sequences in arrival order."""
    direction = (
        current_state.direction
        if current_state is not None
        else StructureDirection.UNDETERMINED
    )

    codes = [_TRANS_CODE[t.transition_type] for t in transitions]

    retained = codes[-TRANSITION_WINDOW_CAPACITY:] if codes else []
    slots = list(retained) + [C_ST_NA] * (TRANSITION_WINDOW_CAPACITY - len(retained))

    window = (
        list(displacements[-DISPLACEMENT_WINDOW_CAPACITY:]) if displacements else []
    )
    disp_dirs = [_DISP_DIR_CODE[o.direction] for o in window]
    disp_clss = [_DISP_CLS_CODE[o.classification] for o in window]
    disp_ratios: list[float | None] = [float(o.range_speed_ratio) for o in window]
    pad = DISPLACEMENT_WINDOW_CAPACITY - len(window)
    disp_dirs += [C_ST_NA] * pad
    disp_clss += [C_ST_NA] * pad
    disp_ratios += [None] * pad

    if transitions:
        last_avail = transitions[-1].availability_time_utc
        disp_cls_at_trans = _displacement_class_at(displacements, last_avail)
        last_trans_avail = epoch_ms(last_avail)
    else:
        disp_cls_at_trans = C_ST_NA
        last_trans_avail = None

    impulse, origin, pullback, pb_valid = _pullback_prices(swings, direction)

    return P5TransportRecord(
        stateAvailT=epoch_ms(
            current_state.availability_time_utc if current_state else None
        ),
        contStreak=_continuation_streak(codes, direction),
        priorOppStreak=_prior_opposite_streak(codes, direction),
        exhaustFlag=_exhaustion_flag(swings, direction),
        transWindowCount=len(retained),
        trans1Type=slots[0],
        trans2Type=slots[1],
        trans3Type=slots[2],
        trans4Type=slots[3],
        lastTransAvailT=last_trans_avail,
        dispWindowCount=len(window),
        disp1Dir=disp_dirs[0],
        disp1Cls=disp_clss[0],
        disp1Ratio=disp_ratios[0],
        disp2Dir=disp_dirs[1],
        disp2Cls=disp_clss[1],
        disp2Ratio=disp_ratios[1],
        disp3Dir=disp_dirs[2],
        disp3Cls=disp_clss[2],
        disp3Ratio=disp_ratios[2],
        dispAvailT=epoch_ms(window[-1].availability_time_utc) if window else None,
        dispClsAtTrans=disp_cls_at_trans,
        pbImpulsePrice=impulse,
        pbOriginPrice=origin,
        pbPullbackPrice=pullback,
        pbValid=pb_valid,
    )
