"""BTRC-T3 deterministic momentum / breakout / pullback engines.

All three consume existing scanner price-action outputs and never re-derive them:
- momentum: ``displacement_observations`` (direction consensus + range_speed_ratio
  trend). Never "last candle green/red" — always a multi-observation window.
- breakout: ``structure_transitions`` (the break) classified by displacement
  strength; ``equal_level_clusters`` distinguish LIQUIDITY_SWEEP; a whipsaw
  reversal is FAILED_BREAK. The causal VALID->FAILED lifecycle is automatic: each
  assessment is a pure function of its prefix analysis, so history is never
  rewritten (an earlier prefix keeps its VALID reading).
- pullback: confirmed ``confirmed_swings`` retracement relative to the impulse leg;
  STRUCTURAL_FAILURE requires structural evidence (impulse origin exceeded or a POI
  genuine invalidation), never a bare percentage.

No RSI/MACD/ADX, no volume dependency, no trade instruction, no scanner mutation.
"""

from __future__ import annotations

from decimal import Decimal

from btmm_ai_scanner.btrc.enums import (
    BreakoutState,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
)
from btmm_ai_scanner.btrc.t3_assessment import (
    TimeframeBreakoutAssessment,
    TimeframeMomentumAssessment,
    TimeframePullbackAssessment,
)
from btmm_ai_scanner.btrc.t3_configuration import MomentumBreakoutPullbackConfiguration
from btmm_ai_scanner.btrc.trend_engine import _AUTHORITY_TIMEFRAMES
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from btmm_ai_scanner.structure.transitions import StructureTransition

_ZERO = Decimal("0")
_STRENGTH_BY_CLASSIFICATION = {
    DisplacementClassification.NORMAL: (BreakoutState.VALID_BREAK, 50),
    DisplacementClassification.FAST: (BreakoutState.STRONG_BREAK, 75),
    DisplacementClassification.VERY_FAST: (BreakoutState.EXPLOSIVE_BREAK, 90),
}
_BULLISH_CHOCH = StructureTransitionType.BULLISH_CHOCH
_BEARISH_CHOCH = StructureTransitionType.BEARISH_CHOCH


def _order_disp(
    obs: tuple[DisplacementObservation, ...],
) -> list[DisplacementObservation]:
    return sorted(
        obs, key=lambda o: (o.availability_time_utc, o.event_time_utc, str(o.record_id))
    )


def _order_transitions(
    ts: tuple[StructureTransition, ...],
) -> list[StructureTransition]:
    return sorted(
        ts, key=lambda t: (t.availability_time_utc, t.event_time_utc, str(t.record_id))
    )


def _order_swings(sw: tuple[ConfirmedSwing, ...]) -> list[ConfirmedSwing]:
    return sorted(
        sw,
        key=lambda s: (
            s.availability_time_utc,
            s.pivot_start_time_utc,
            str(s.record_id),
        ),
    )


# ------------------------------------------------------------------ momentum
def _assess_timeframe_momentum(
    timeframe: Timeframe,
    displacements: tuple[DisplacementObservation, ...],
    config: MomentumBreakoutPullbackConfiguration,
) -> TimeframeMomentumAssessment:
    window = _order_disp(displacements)[-config.momentum_window :]
    supporting: list[str] = []
    opposing: list[str] = []
    provenance = tuple(str(o.record_id) for o in window)
    evaluation_time = window[-1].availability_time_utc if window else None

    if not window:
        return TimeframeMomentumAssessment(
            timeframe=timeframe,
            direction=MomentumDirection.NEUTRAL,
            acceleration=MomentumAcceleration.STEADY,
            momentum_score=0,
            evaluation_time_utc=evaluation_time,
            displacement_count=0,
            supporting_evidence=("no recent displacement",),
            opposing_evidence=(),
            provenance_ids=provenance,
        )

    bull = sum(1 for o in window if o.direction is DisplacementDirection.BULLISH)
    bear = len(window) - bull
    has_very_fast = any(
        o.classification is DisplacementClassification.VERY_FAST for o in window
    )
    strong = len(window) >= config.momentum_strong_count or has_very_fast

    if bull > 0 and bear == 0:
        direction = (
            MomentumDirection.STRONG_BULLISH if strong else MomentumDirection.BULLISH
        )
        supporting.append(f"{bull} consecutive bullish displacement(s)")
    elif bear > 0 and bull == 0:
        direction = (
            MomentumDirection.STRONG_BEARISH if strong else MomentumDirection.BEARISH
        )
        supporting.append(f"{bear} consecutive bearish displacement(s)")
    elif bull > bear:
        direction = MomentumDirection.BULLISH
        supporting.append(f"bullish displacement majority ({bull}/{len(window)})")
    elif bear > bull:
        direction = MomentumDirection.BEARISH
        supporting.append(f"bearish displacement majority ({bear}/{len(window)})")
    else:
        direction = MomentumDirection.NEUTRAL
        opposing.append("mixed displacement direction")

    acceleration = _acceleration(window, config)
    momentum_score = _momentum_score(window, bull, bear, config)
    return TimeframeMomentumAssessment(
        timeframe=timeframe,
        direction=direction,
        acceleration=acceleration,
        momentum_score=momentum_score,
        evaluation_time_utc=evaluation_time,
        displacement_count=len(window),
        supporting_evidence=tuple(supporting),
        opposing_evidence=tuple(opposing),
        provenance_ids=provenance,
    )


def _acceleration(
    window: list[DisplacementObservation],
    config: MomentumBreakoutPullbackConfiguration,
) -> MomentumAcceleration:
    if len(window) < 2:
        return MomentumAcceleration.STEADY
    mid = len(window) // 2
    earlier = window[:mid] or window[:1]
    recent = window[mid:]
    earlier_mean = sum((o.range_speed_ratio for o in earlier), _ZERO) / len(earlier)
    recent_mean = sum((o.range_speed_ratio for o in recent), _ZERO) / len(recent)
    if earlier_mean == _ZERO:
        return MomentumAcceleration.STEADY
    margin = config.momentum_acceleration_margin
    if recent_mean > earlier_mean * (Decimal("1") + margin):
        return MomentumAcceleration.ACCELERATING
    if recent_mean < earlier_mean * (Decimal("1") - margin):
        return MomentumAcceleration.DECELERATING
    return MomentumAcceleration.STEADY


def _momentum_score(
    window: list[DisplacementObservation],
    bull: int,
    bear: int,
    config: MomentumBreakoutPullbackConfiguration,
) -> int:
    mean_ratio = sum((o.range_speed_ratio for o in window), _ZERO) / len(window)
    magnitude = min(Decimal("1"), mean_ratio / config.momentum_score_reference_ratio)
    consistency = Decimal(max(bull, bear)) / Decimal(len(window))
    return int((magnitude * consistency * Decimal("100")).to_integral_value())


# ------------------------------------------------------------------ breakout
def _assess_timeframe_breakout(
    timeframe: Timeframe,
    transitions: tuple[StructureTransition, ...],
    equal_levels: tuple[EqualLevelCluster, ...],
    displacements: tuple[DisplacementObservation, ...],
) -> TimeframeBreakoutAssessment:
    ordered_transitions = _order_transitions(transitions)
    supporting: list[str] = []
    opposing: list[str] = []

    last_transition = ordered_transitions[-1] if ordered_transitions else None

    # A breakout REQUIRES a confirmed structural transition (the structural
    # precondition). Displacement alone -- however fast -- is NOT a breakout, which
    # keeps breakout quality independent of displacement classification.
    #
    # LIQUIDITY_SWEEP is intentionally NOT emitted in V1: distinguishing a genuine
    # liquidity take (price trades THROUGH a known level AND fails required
    # structural acceptance, with rejection/re-entry evidence) from a generic
    # equal-level touch/proximity is not decidable from the exposed scanner outputs
    # (EqualLevelCluster is a liquidity REFERENCE, not a sweep event). We classify
    # conservatively and disclose this limitation rather than invent a sweep rule.
    if last_transition is None:
        return TimeframeBreakoutAssessment(
            timeframe=timeframe,
            breakout_state=None,
            breakout_score=0,
            evaluation_time_utc=None,
            supporting_evidence=("no confirmed structural break",),
            opposing_evidence=(),
            provenance_ids=(),
        )

    # FAILED_BREAK: an immediate whipsaw reversal (two opposite-polarity CHOCHs in a
    # row) means the earlier break failed.
    if (
        len(ordered_transitions) >= 2
        and last_transition.transition_type in (_BULLISH_CHOCH, _BEARISH_CHOCH)
        and ordered_transitions[-2].transition_type in (_BULLISH_CHOCH, _BEARISH_CHOCH)
        and ordered_transitions[-2].transition_type != last_transition.transition_type
    ):
        opposing.append("immediate opposite change-of-character; prior break failed")
        return TimeframeBreakoutAssessment(
            timeframe=timeframe,
            breakout_state=BreakoutState.FAILED_BREAK,
            breakout_score=10,
            evaluation_time_utc=last_transition.availability_time_utc,
            supporting_evidence=(),
            opposing_evidence=tuple(opposing),
            provenance_ids=(str(last_transition.record_id),),
        )

    # Strength = the confirmed structural break (precondition) MODULATED by the
    # displacement observed at the break. Displacement is one input, not an alias:
    # a structurally-confirmed break with no displacement is still a WEAK_BREAK.
    classification = _displacement_at(displacements, last_transition)
    if classification is None:
        state, score = BreakoutState.WEAK_BREAK, 25
        supporting.append("confirmed structural break, no accompanying displacement")
    else:
        state, score = _STRENGTH_BY_CLASSIFICATION[classification]
        supporting.append(
            f"confirmed structural break modulated by {classification.value} displacement"
        )
    return TimeframeBreakoutAssessment(
        timeframe=timeframe,
        breakout_state=state,
        breakout_score=score,
        evaluation_time_utc=last_transition.availability_time_utc,
        supporting_evidence=tuple(supporting),
        opposing_evidence=tuple(opposing),
        provenance_ids=(str(last_transition.record_id),),
    )


def _displacement_at(
    displacements: tuple[DisplacementObservation, ...],
    transition: StructureTransition,
) -> DisplacementClassification | None:
    matches = [
        o
        for o in displacements
        if o.availability_time_utc == transition.availability_time_utc
    ]
    if not matches:
        return None
    order = {
        DisplacementClassification.NORMAL: 0,
        DisplacementClassification.FAST: 1,
        DisplacementClassification.VERY_FAST: 2,
    }
    return max((o.classification for o in matches), key=lambda c: order[c])


# ------------------------------------------------------------------ pullback
def _assess_timeframe_pullback(
    timeframe: Timeframe,
    swings: tuple[ConfirmedSwing, ...],
    current_state: CurrentStructureState | None,
    lifecycle_transitions: tuple[PoiLifecycleTransition, ...],
    config: MomentumBreakoutPullbackConfiguration,
) -> TimeframePullbackAssessment:
    supporting: list[str] = []
    opposing: list[str] = []
    if (
        current_state is None
        or current_state.direction is StructureDirection.UNDETERMINED
    ):
        return TimeframePullbackAssessment(
            timeframe=timeframe,
            pullback_state=None,
            evaluation_time_utc=(
                current_state.availability_time_utc if current_state else None
            ),
            supporting_evidence=("no confirmed directional impulse",),
            opposing_evidence=(),
            provenance_ids=(),
        )

    ordered = _order_swings(swings)
    depth, refs = _retracement_depth(ordered, current_state.direction)
    evaluation_time = current_state.availability_time_utc
    if depth is None:
        return TimeframePullbackAssessment(
            timeframe=timeframe,
            pullback_state=None,
            evaluation_time_utc=evaluation_time,
            supporting_evidence=("no counter-swing pullback in progress",),
            opposing_evidence=(),
            provenance_ids=refs,
        )

    # POI lifecycle truth is a SEPARATE contract from structure truth: a POI may
    # invalidate without the impulse structure failing. It is recorded as
    # SUPPORTING evidence only and never, on its own, classifies STRUCTURAL_FAILURE.
    poi_invalidation = any(
        t.transition_type is PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
        and t.timeframe is timeframe
        for t in lifecycle_transitions
    )
    # STRUCTURAL_FAILURE requires STRUCTURAL evidence: the retracement broke the
    # structural low/high that governs the active impulse (its origin swing), i.e.
    # depth > 1.0. (A confirmed opposing CHOCH/BOS would instead have flipped
    # current_state.direction, so this branch only sees an impulse that still holds.)
    if depth > Decimal("1"):
        opposing.append(
            "retracement broke the impulse origin swing (structural low/high failed)"
        )
        if poi_invalidation:
            supporting.append("POI genuine invalidation (supporting, not defining)")
        state = PullbackState.STRUCTURAL_FAILURE
    elif depth <= config.pullback_shallow_max:
        state = PullbackState.SHALLOW_PULLBACK
        supporting.append(f"shallow retracement (depth {depth})")
    elif depth <= config.pullback_deep_min:
        state = PullbackState.HEALTHY_PULLBACK
        supporting.append(f"healthy retracement (depth {depth})")
    else:
        state = PullbackState.DEEP_PULLBACK
        supporting.append(f"deep but structurally-valid retracement (depth {depth})")

    return TimeframePullbackAssessment(
        timeframe=timeframe,
        pullback_state=state,
        evaluation_time_utc=evaluation_time,
        supporting_evidence=tuple(supporting),
        opposing_evidence=tuple(opposing),
        provenance_ids=refs,
    )


def _retracement_depth(
    swings: list[ConfirmedSwing], direction: StructureDirection
) -> tuple[Decimal | None, tuple[str, ...]]:
    """Fraction of the impulse leg retraced by the latest counter-swing. Bullish:
    impulse = last SWING_LOW -> last SWING_HIGH; pullback = the SWING_LOW after that
    high. Returns (None, refs) when no counter-swing pullback is in progress."""
    highs = [s for s in swings if s.swing_type is SwingType.SWING_HIGH]
    lows = [s for s in swings if s.swing_type is SwingType.SWING_LOW]
    if direction is StructureDirection.BULLISH:
        if not highs or not lows:
            return None, ()
        impulse_top = highs[-1]
        origin_candidates = [
            s
            for s in lows
            if s.pivot_start_time_utc <= impulse_top.pivot_start_time_utc
        ]
        pullback_candidates = [
            s for s in lows if s.pivot_start_time_utc > impulse_top.pivot_start_time_utc
        ]
        if not origin_candidates or not pullback_candidates:
            return None, ()
        origin = origin_candidates[-1]
        pullback = pullback_candidates[-1]
        leg = impulse_top.pivot_price - origin.pivot_price
        if leg <= _ZERO:
            return None, ()
        depth = (impulse_top.pivot_price - pullback.pivot_price) / leg
        return depth, (
            str(origin.record_id),
            str(impulse_top.record_id),
            str(pullback.record_id),
        )
    # bearish
    if not highs or not lows:
        return None, ()
    impulse_bottom = lows[-1]
    origin_candidates = [
        s
        for s in highs
        if s.pivot_start_time_utc <= impulse_bottom.pivot_start_time_utc
    ]
    pullback_candidates = [
        s for s in highs if s.pivot_start_time_utc > impulse_bottom.pivot_start_time_utc
    ]
    if not origin_candidates or not pullback_candidates:
        return None, ()
    origin = origin_candidates[-1]
    pullback = pullback_candidates[-1]
    leg = origin.pivot_price - impulse_bottom.pivot_price
    if leg <= _ZERO:
        return None, ()
    depth = (pullback.pivot_price - impulse_bottom.pivot_price) / leg
    return depth, (
        str(origin.record_id),
        str(impulse_bottom.record_id),
        str(pullback.record_id),
    )


# ------------------------------------------------------------------ entry points
def assess_momentum(
    analysis: ScannerAnalysis,
    configuration: MomentumBreakoutPullbackConfiguration | None = None,
) -> tuple[TimeframeMomentumAssessment, ...]:
    config = configuration or MomentumBreakoutPullbackConfiguration()
    disp_by_tf = {
        m.timeframe: m.displacement_observations
        for m in analysis.measurement_analyses
        if m.timeframe is not None
    }
    out = [
        _assess_timeframe_momentum(tf, disp_by_tf[tf], config)
        for tf in _AUTHORITY_TIMEFRAMES
        if tf in disp_by_tf
    ]
    out.sort(key=lambda a: _TIMEFRAME_RANK[a.timeframe])
    return tuple(out)


def assess_breakout(
    analysis: ScannerAnalysis,
    configuration: MomentumBreakoutPullbackConfiguration | None = None,
) -> tuple[TimeframeBreakoutAssessment, ...]:
    disp_by_tf = {
        m.timeframe: m.displacement_observations
        for m in analysis.measurement_analyses
        if m.timeframe is not None
    }
    levels_by_tf = {
        m.timeframe: m.equal_level_clusters
        for m in analysis.measurement_analyses
        if m.timeframe is not None
    }
    transitions_by_tf = {
        s.timeframe: s.structure_transitions
        for s in analysis.structure_analyses
        if s.timeframe is not None
    }
    timeframes = sorted(
        set(disp_by_tf) | set(transitions_by_tf),
        key=lambda tf: _TIMEFRAME_RANK[tf],
    )
    out = [
        _assess_timeframe_breakout(
            tf,
            transitions_by_tf.get(tf, ()),
            levels_by_tf.get(tf, ()),
            disp_by_tf.get(tf, ()),
        )
        for tf in timeframes
        if tf in _AUTHORITY_TIMEFRAMES
    ]
    return tuple(out)


def assess_pullback(
    analysis: ScannerAnalysis,
    configuration: MomentumBreakoutPullbackConfiguration | None = None,
) -> tuple[TimeframePullbackAssessment, ...]:
    config = configuration or MomentumBreakoutPullbackConfiguration()
    swings_by_tf = {
        m.timeframe: m.confirmed_swings
        for m in analysis.measurement_analyses
        if m.timeframe is not None
    }
    state_by_tf = {
        s.timeframe: s.current_state
        for s in analysis.structure_analyses
        if s.timeframe is not None
    }
    lifecycle = analysis.poi_analysis.poi_lifecycle_transitions
    timeframes = sorted(
        set(swings_by_tf) | set(state_by_tf), key=lambda tf: _TIMEFRAME_RANK[tf]
    )
    out = [
        _assess_timeframe_pullback(
            tf, swings_by_tf.get(tf, ()), state_by_tf.get(tf), lifecycle, config
        )
        for tf in timeframes
        if tf in _AUTHORITY_TIMEFRAMES
    ]
    return tuple(out)
