"""BTRC-T1 deterministic multi-timeframe trend engine.

Consumes ONLY existing scanner outputs (confirmed swings + structure transitions
+ current structure state) from a ``ScannerAnalysis``. It never re-derives swings
or structure and never mutates any scanner record. Trend classification is
supervisory: it labels the prevailing direction/state; it does not decide whether
a POI or BTMM setup is valid.

Pure function of the ScannerAnalysis (which is itself a pure function of the
accepted candle history) → deterministic, no-lookahead, and incremental-vs-batch
equivalent by construction.
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import Direction, TrendState
from btmm_ai_scanner.btrc.trend_assessment import (
    TimeframeTrendAssessment,
    TrendAssessment,
)
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)
from btmm_ai_scanner.structure.transitions import StructureTransition

# T1 authority hierarchy (validated timeframes only; H6/H8/H12 deferred).
_AUTHORITY_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.W1,
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.H1,
    Timeframe.M15,
    Timeframe.M5,
)
_BULLISH_SIDE = frozenset({Direction.BULLISH, Direction.STRONG_BULLISH})
_BEARISH_SIDE = frozenset({Direction.BEARISH, Direction.STRONG_BEARISH})
_CONTINUATION_BOS = {
    StructureDirection.BULLISH: StructureTransitionType.BULLISH_BOS,
    StructureDirection.BEARISH: StructureTransitionType.BEARISH_BOS,
}
_OPPOSING_BOS = {
    StructureDirection.BULLISH: StructureTransitionType.BEARISH_BOS,
    StructureDirection.BEARISH: StructureTransitionType.BULLISH_BOS,
}
_CHOCH_TYPES = frozenset(
    {StructureTransitionType.BULLISH_CHOCH, StructureTransitionType.BEARISH_CHOCH}
)


def _ordered_transitions(
    transitions: tuple[StructureTransition, ...],
) -> list[StructureTransition]:
    return sorted(
        transitions,
        key=lambda t: (t.availability_time_utc, t.event_time_utc, str(t.record_id)),
    )


def _ordered_swings(swings: tuple[ConfirmedSwing, ...]) -> list[ConfirmedSwing]:
    return sorted(
        swings,
        key=lambda s: (
            s.availability_time_utc,
            s.pivot_start_time_utc,
            str(s.record_id),
        ),
    )


def _continuation_streak(
    transitions: list[StructureTransition], direction: StructureDirection
) -> int:
    """Consecutive most-recent same-direction continuation BOS (a CHOCH or an
    opposing transition ends the streak). The initiating CHOCH is not a BOS, so a
    just-flipped direction has streak 0."""
    target = _CONTINUATION_BOS[direction]
    streak = 0
    for transition in reversed(transitions):
        if transition.transition_type == target:
            streak += 1
        else:
            break
    return streak


def _prior_opposite_streak(
    transitions: list[StructureTransition], direction: StructureDirection
) -> int:
    """When the latest transition is the initiating CHOCH into ``direction``,
    count how established the PRIOR opposite trend was (consecutive opposing BOS
    immediately before that CHOCH). Distinguishes a real reversal (TRANSITION)
    from a fresh directional attempt (FORMING)."""
    if not transitions:
        return 0
    opposing = _OPPOSING_BOS[direction]
    streak = 0
    for transition in reversed(transitions[:-1]):
        if transition.transition_type == opposing:
            streak += 1
        else:
            break
    return streak


def _alternation_count(transitions: list[StructureTransition], window: int) -> int:
    return sum(1 for t in transitions[-window:] if t.transition_type in _CHOCH_TYPES)


def _exhaustion(
    swings: list[ConfirmedSwing], direction: StructureDirection
) -> tuple[bool, str | None]:
    """Structural continuation weakening WITHOUT a confirmed reversal: a lower
    high while bullish, or a higher low while bearish (compared on the two most
    recent same-type confirmed swings)."""
    if direction is StructureDirection.BULLISH:
        highs = [s for s in swings if s.swing_type is SwingType.SWING_HIGH]
        if len(highs) >= 2 and highs[-1].pivot_price < highs[-2].pivot_price:
            return True, "latest swing high is a LOWER HIGH (continuation weakening)"
    elif direction is StructureDirection.BEARISH:
        lows = [s for s in swings if s.swing_type is SwingType.SWING_LOW]
        if len(lows) >= 2 and lows[-1].pivot_price > lows[-2].pivot_price:
            return True, "latest swing low is a HIGHER LOW (continuation weakening)"
    return False, None


def _assess_timeframe(
    timeframe: Timeframe,
    swings: tuple[ConfirmedSwing, ...],
    transitions: tuple[StructureTransition, ...],
    current_state: CurrentStructureState | None,
    config: TrendEngineConfiguration,
) -> TimeframeTrendAssessment:
    ordered_transitions = _ordered_transitions(transitions)
    ordered_swings = _ordered_swings(swings)
    supporting: list[str] = []
    opposing: list[str] = []
    refs: list[str] = [str(t.record_id) for t in ordered_transitions]

    analyzed_swing_count = (
        current_state.analyzed_swing_count if current_state is not None else 0
    )
    evaluation_time: datetime | None = (
        current_state.availability_time_utc if current_state is not None else None
    )

    if current_state is None or analyzed_swing_count < config.min_swings_for_assessment:
        supporting.append(
            f"insufficient confirmed structure ({analyzed_swing_count} swings)"
        )
        return TimeframeTrendAssessment(
            timeframe=timeframe,
            direction=Direction.NEUTRAL,
            trend_state=TrendState.UNKNOWN,
            evaluation_time_utc=evaluation_time,
            analyzed_swing_count=analyzed_swing_count,
            continuation_streak=0,
            supporting_evidence=tuple(supporting),
            opposing_evidence=tuple(opposing),
            structure_reference_ids=tuple(refs),
        )

    structural_direction = current_state.direction
    if structural_direction is StructureDirection.UNDETERMINED:
        supporting.append("swings present but no confirmed directional break yet")
        return TimeframeTrendAssessment(
            timeframe=timeframe,
            direction=Direction.NEUTRAL,
            trend_state=TrendState.FORMING,
            evaluation_time_utc=evaluation_time,
            analyzed_swing_count=analyzed_swing_count,
            continuation_streak=0,
            supporting_evidence=tuple(supporting),
            opposing_evidence=tuple(opposing),
            structure_reference_ids=tuple(refs),
        )

    streak = _continuation_streak(ordered_transitions, structural_direction)
    alternation = _alternation_count(ordered_transitions, config.range_window)
    is_bullish = structural_direction is StructureDirection.BULLISH
    side_word = "bullish" if is_bullish else "bearish"

    # --- trend state ---
    if alternation >= config.range_choch_count:
        trend_state = TrendState.RANGE
        supporting.append(
            f"{alternation} change-of-character events in the last"
            f" {config.range_window} transitions (alternating / non-persistent)"
        )
    elif streak == 0:
        prior = _prior_opposite_streak(ordered_transitions, structural_direction)
        if prior >= config.trend_min_streak:
            trend_state = TrendState.TRANSITION
            supporting.append(
                f"{side_word} change-of-character reversed a prior established"
                f" opposite trend ({prior} continuation BOS); new trend unconfirmed"
            )
        else:
            trend_state = TrendState.FORMING
            supporting.append(
                f"{side_word} change-of-character; direction emerging, not yet"
                " persistent"
            )
    else:
        exhausting, exhaustion_reason = _exhaustion(
            ordered_swings, structural_direction
        )
        if exhausting:
            trend_state = TrendState.EXHAUSTING
            assert exhaustion_reason is not None
            opposing.append(exhaustion_reason)
            supporting.append(
                f"{side_word} structure still valid ({streak} continuation BOS)"
            )
        else:
            trend_state = TrendState.TRENDING
            supporting.append(
                f"confirmed {side_word} structure with {streak} continuation BOS"
            )

    # --- direction (STRONG requires TRENDING + strong persistence) ---
    if trend_state is TrendState.TRENDING and streak >= config.strong_streak:
        direction = Direction.STRONG_BULLISH if is_bullish else Direction.STRONG_BEARISH
        supporting.append(
            f"strong persistence ({streak} >= {config.strong_streak} continuation BOS)"
        )
    else:
        direction = Direction.BULLISH if is_bullish else Direction.BEARISH

    return TimeframeTrendAssessment(
        timeframe=timeframe,
        direction=direction,
        trend_state=trend_state,
        evaluation_time_utc=evaluation_time,
        analyzed_swing_count=analyzed_swing_count,
        continuation_streak=streak,
        supporting_evidence=tuple(supporting),
        opposing_evidence=tuple(opposing),
        structure_reference_ids=tuple(refs),
    )


def _resolve_global(
    direction_by_tf: dict[Timeframe, Direction],
) -> Direction:
    """Deterministic authority resolver. D1 is primary; W1 macro + H4 operational
    agreement can strengthen it; H1/M15/M5 NEVER change global direction."""
    d1 = direction_by_tf.get(Timeframe.D1)
    w1 = direction_by_tf.get(Timeframe.W1)
    h4 = direction_by_tf.get(Timeframe.H4)
    if d1 in _BULLISH_SIDE:
        if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
            return Direction.STRONG_BULLISH
        return Direction.BULLISH
    if d1 in _BEARISH_SIDE:
        if w1 in _BEARISH_SIDE and h4 in _BEARISH_SIDE:
            return Direction.STRONG_BEARISH
        return Direction.BEARISH
    # D1 neutral or absent: only W1+H4 agreement gives a provisional (non-strong)
    # global direction; otherwise NEUTRAL.
    if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
        return Direction.BULLISH
    if w1 in _BEARISH_SIDE and h4 in _BEARISH_SIDE:
        return Direction.BEARISH
    return Direction.NEUTRAL


def assess_trend(
    analysis: ScannerAnalysis,
    configuration: TrendEngineConfiguration | None = None,
) -> TrendAssessment:
    config = configuration or TrendEngineConfiguration()
    swings_by_tf: dict[Timeframe, tuple[ConfirmedSwing, ...]] = {}
    for measurement in analysis.measurement_analyses:
        if measurement.timeframe is not None:
            swings_by_tf[measurement.timeframe] = measurement.confirmed_swings
    transitions_by_tf: dict[Timeframe, tuple[StructureTransition, ...]] = {}
    state_by_tf: dict[Timeframe, CurrentStructureState | None] = {}
    for structure in analysis.structure_analyses:
        if structure.timeframe is not None:
            transitions_by_tf[structure.timeframe] = structure.structure_transitions
            state_by_tf[structure.timeframe] = structure.current_state

    assessments: list[TimeframeTrendAssessment] = []
    direction_by_tf: dict[Timeframe, Direction] = {}
    for timeframe in _AUTHORITY_TIMEFRAMES:
        if timeframe not in swings_by_tf and timeframe not in state_by_tf:
            continue
        assessment = _assess_timeframe(
            timeframe,
            swings_by_tf.get(timeframe, ()),
            transitions_by_tf.get(timeframe, ()),
            state_by_tf.get(timeframe),
            config,
        )
        assessments.append(assessment)
        direction_by_tf[timeframe] = assessment.direction

    assessments.sort(key=lambda a: _TIMEFRAME_RANK[a.timeframe])
    global_direction = _resolve_global(direction_by_tf)
    macro_context = direction_by_tf.get(Timeframe.W1, Direction.NEUTRAL)
    operational_context = direction_by_tf.get(Timeframe.H4, Direction.NEUTRAL)

    supporting_reasons, opposing_reasons = _global_reasons(
        global_direction, direction_by_tf
    )

    evaluation_time = analysis.availability_time_utc
    return TrendAssessment(
        symbol=_analysis_symbol(analysis),
        evaluation_time_utc=evaluation_time,
        global_direction=global_direction,
        macro_context=macro_context,
        operational_context=operational_context,
        timeframe_assessments=tuple(assessments),
        supporting_reasons=supporting_reasons,
        opposing_reasons=opposing_reasons,
    )


def _global_reasons(
    global_direction: Direction, direction_by_tf: dict[Timeframe, Direction]
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    supporting: list[str] = []
    opposing: list[str] = []
    global_side = (
        _BULLISH_SIDE
        if global_direction in _BULLISH_SIDE
        else _BEARISH_SIDE
        if global_direction in _BEARISH_SIDE
        else frozenset()
    )
    for timeframe, direction in sorted(
        direction_by_tf.items(), key=lambda item: _TIMEFRAME_RANK[item[0]]
    ):
        authority = timeframe in (Timeframe.W1, Timeframe.D1, Timeframe.H4)
        if not global_side:
            continue
        if direction in global_side:
            if authority:
                supporting.append(
                    f"{timeframe.value} {direction.value} confirms global"
                )
        elif direction in _BULLISH_SIDE or direction in _BEARISH_SIDE:
            note = (
                "authority opposes global"
                if authority
                else "local retracement / does not flip global"
            )
            opposing.append(f"{timeframe.value} {direction.value} ({note})")
    return tuple(supporting), tuple(opposing)


def _analysis_symbol(analysis: ScannerAnalysis) -> InternalSymbol | None:
    return analysis.symbol
