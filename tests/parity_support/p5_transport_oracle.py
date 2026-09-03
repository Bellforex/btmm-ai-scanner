"""The AUTHORITATIVE P5 transport oracle: full collections, real engine helpers.

Test/parity tooling only.

WHAT MAKES THIS AUTHORITATIVE
------------------------------
It re-implements nothing. Every reduction is produced by calling the private
helper the production engine itself calls, over the FULL collection:

    _ordered_transitions   trend_engine     transition ordering
    _ordered_swings        trend_engine     swing ordering
    _continuation_streak   trend_engine     contStreak
    _prior_opposite_streak trend_engine     priorOppStreak
    _exhaustion            trend_engine     exhaustFlag
    _recent_displacements  regime_engine    the displacement window
    _displacement_at       t3_engine        dispClsAtTrans
    _retracement_depth     t3_engine        the three pullback swings

So if a future edit changes what `_prior_opposite_streak` means, this oracle
changes with it and the Pine-equivalent model starts failing -- which is the
alarm we want, instead of two copies of a stale rule agreeing with each other.

THE PULLBACK PRICES COME FROM THE SOURCE'S OWN ROLE SELECTION
---------------------------------------------------------------
`_retracement_depth` returns ``(depth, refs)`` where refs is
``(origin_id, impulse_id, pullback_id)`` in BOTH the bullish and bearish
branches. Rather than re-deriving which swing plays which role -- the exact
thing most likely to be got wrong -- the oracle takes the source's answer and
looks the three record ids back up. ``pbValid`` is simply whether the source
returned a depth at all.

WHAT THIS ORACLE IS NOT
-----------------------
It is not a model of Pine. It sorts by ``(availability, event, str(record_id))``
because the engines do, holds unbounded history, and uses ``Decimal``. The
bounded, arrival-ordered, float-shaped implementation lives in
`p5_transport_pine_model` and is written independently, so the differential
between them is a real test rather than a spelling check.
"""

from __future__ import annotations

from collections.abc import Sequence

from btmm_ai_scanner.btrc.regime_engine import _recent_displacements
from btmm_ai_scanner.btrc.t3_engine import _displacement_at, _retracement_depth
from btmm_ai_scanner.btrc.trend_engine import (
    _continuation_streak,
    _exhaustion,
    _ordered_swings,
    _ordered_transitions,
    _prior_opposite_streak,
)
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
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

TRANSITION_CODE: dict[StructureTransitionType, int] = {
    StructureTransitionType.BULLISH_BOS: TR_BULLISH_BOS,
    StructureTransitionType.BEARISH_BOS: TR_BEARISH_BOS,
    StructureTransitionType.BULLISH_CHOCH: TR_BULLISH_CHOCH,
    StructureTransitionType.BEARISH_CHOCH: TR_BEARISH_CHOCH,
}

DISPLACEMENT_DIRECTION_CODE: dict[DisplacementDirection, int] = {
    DisplacementDirection.BULLISH: DISP_DIR_BULLISH,
    DisplacementDirection.BEARISH: DISP_DIR_BEARISH,
}

DISPLACEMENT_CLASS_CODE: dict[DisplacementClassification, int] = {
    DisplacementClassification.NORMAL: DISP_CLS_NORMAL,
    DisplacementClassification.FAST: DISP_CLS_FAST,
    DisplacementClassification.VERY_FAST: DISP_CLS_VERY_FAST,
}


def reduce_authoritative(
    swings: Sequence[SwingRec],
    transitions: Sequence[TransitionRec],
    displacements: Sequence[DisplacementRec],
    current_state: StateRec | None,
) -> P5TransportRecord:
    """Produce the 26-field record from the full authoritative collections."""
    ordered_transitions = _ordered_transitions(tuple(transitions))
    ordered_swings = _ordered_swings(tuple(swings))

    direction = (
        current_state.direction
        if current_state is not None
        else StructureDirection.UNDETERMINED
    )

    # --- T1 reductions -----------------------------------------------------
    # The streak helpers index _CONTINUATION_BOS / _OPPOSING_BOS by direction,
    # which hold no UNDETERMINED key, so that case is answered here rather than
    # by letting the helper raise.
    if direction is StructureDirection.UNDETERMINED:
        cont_streak = 0
        prior_opposite = 0
    else:
        cont_streak = _continuation_streak(ordered_transitions, direction)
        prior_opposite = _prior_opposite_streak(ordered_transitions, direction)
    exhausting, _reason = _exhaustion(ordered_swings, direction)

    # --- bounded transition window, oldest -> newest, left aligned ---------
    retained_transitions = ordered_transitions[-TRANSITION_WINDOW_CAPACITY:]
    trans_codes = [TRANSITION_CODE[t.transition_type] for t in retained_transitions]
    trans_codes += [C_ST_NA] * (TRANSITION_WINDOW_CAPACITY - len(trans_codes))

    last_transition = ordered_transitions[-1] if ordered_transitions else None

    # --- bounded displacement window --------------------------------------
    window = _recent_displacements(
        tuple(displacements), DISPLACEMENT_WINDOW_CAPACITY
    )
    disp_dirs = [DISPLACEMENT_DIRECTION_CODE[o.direction] for o in window]
    disp_clss = [DISPLACEMENT_CLASS_CODE[o.classification] for o in window]
    disp_ratios: list[float | None] = [float(o.range_speed_ratio) for o in window]
    pad = DISPLACEMENT_WINDOW_CAPACITY - len(window)
    disp_dirs += [C_ST_NA] * pad
    disp_clss += [C_ST_NA] * pad
    disp_ratios += [None] * pad

    # --- breakout ----------------------------------------------------------
    if last_transition is None:
        disp_cls_at_trans = C_ST_NA
    else:
        matched = _displacement_at(tuple(displacements), last_transition)
        disp_cls_at_trans = (
            C_ST_NA if matched is None else DISPLACEMENT_CLASS_CODE[matched]
        )

    # --- pullback: the source picks the roles, we only read the prices -----
    # `_assess_timeframe_pullback` returns before calling `_retracement_depth`
    # when the direction is UNDETERMINED. Calling it anyway would NOT be
    # equivalent: the helper's own branch is `if BULLISH ... else <bearish>`, so
    # an undetermined direction would silently receive bearish role selection
    # and invent a pullback the engine never reports.
    if direction is StructureDirection.UNDETERMINED:
        depth, refs = None, ()
    else:
        depth, refs = _retracement_depth(ordered_swings, direction)
    if depth is None:
        pb_origin = pb_impulse = pb_pullback = None
        pb_valid = False
    else:
        by_id = {str(s.record_id): s for s in ordered_swings}
        origin_id, impulse_id, pullback_id = refs
        pb_origin = float(by_id[origin_id].pivot_price)
        pb_impulse = float(by_id[impulse_id].pivot_price)
        pb_pullback = float(by_id[pullback_id].pivot_price)
        pb_valid = True

    return P5TransportRecord(
        stateAvailT=epoch_ms(
            current_state.availability_time_utc if current_state else None
        ),
        contStreak=cont_streak,
        priorOppStreak=prior_opposite,
        exhaustFlag=1 if exhausting else 0,
        transWindowCount=len(retained_transitions),
        trans1Type=trans_codes[0],
        trans2Type=trans_codes[1],
        trans3Type=trans_codes[2],
        trans4Type=trans_codes[3],
        lastTransAvailT=epoch_ms(
            last_transition.availability_time_utc if last_transition else None
        ),
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
        dispAvailT=epoch_ms(window[-1].availability_time_utc) if window else C_ST_NA,
        dispClsAtTrans=disp_cls_at_trans,
        pbImpulsePrice=pb_impulse,
        pbOriginPrice=pb_origin,
        pbPullbackPrice=pb_pullback,
        pbValid=pb_valid,
    )
