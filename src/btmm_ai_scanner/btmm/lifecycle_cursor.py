"""A6-B2-A: exact resumable BTMM lifecycle cursor.

``run_btmm_lifecycle`` (the batch oracle, unchanged) re-runs the whole setup
cascade over ``bundle_candles[0:]`` on every candle. This module reproduces its
result exactly, one appended candle at a time, without ever re-scanning history.

Design. The batch cascade is a MONOTONE forward pipeline whose only per-candle
work is three forward scans — first POI interaction (``find_first_interaction``
from the forming candle), reaction start (``find_reaction_start`` from the
interaction), and the bounded reaction window (``evaluate_reaction_window`` over
``reaction_window_bars`` bars). Each result, once found, is final. The cursor
advances only the un-committed scan frontier: it tests each newly appended candle
exactly once for the currently-open stage and caches the committed result
(forming candle, interaction index+class, reaction-start index, running reaction
anchor, and — once the window fills — the ``ReactionTierResult`` and window-close
candle). The only retained candle state is the previous candle (for the
interaction predicate's prior-reference price) and the ≤ ``reaction_window_bars``
reaction-window buffer.

Everything downstream of the reaction window (automatic + reviewed evidence, the
final gates, CONFIRM / CANCEL / BLOCK, and the source-POI genuine-invalidation
override) is NOT a candle scan — it is fixed logic over the two growing inputs
(``poi_lifecycle_transitions`` and ``reviewed_evidence``). ``materialize_btmm_cursor``
runs that exact cascade (a faithful transcription of the batch body, using the
cached scan results instead of re-scanning) with the CURRENT evidence/transition
inputs, so an evidence arrival or a later POI invalidation re-resolves the setup
without any price re-scan. ``run_btmm_lifecycle`` is never called here.

The materialized result at every prefix is byte-identical to
``run_btmm_lifecycle(full prefix, exact inputs)`` — asserted by the permanent
differential test.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmFormationStage,
    BtmmGateStatus,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLifecycleTransitionType,
    BtmmLiquidityEvidenceStatus,
    BtmmReactionClassification,
)
from btmm_ai_scanner.btmm.interaction import (
    ELIGIBLE_INTERACTION_CLASSES,
    find_first_interaction,
)
from btmm_ai_scanner.btmm.lifecycle import (
    LifecycleWalkResult,
    TransitionCandidate,
    _initial_fields,
    _resolve_final_gates,
    _StateFields,
    _StepRecord,
)
from btmm_ai_scanner.btmm.liquidity import find_automatic_liquidity_evidence
from btmm_ai_scanner.btmm.reaction import (
    ReactionTierResult,
    evaluate_reaction_window,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.legs import LegSpeedClassification
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition


@dataclass(frozen=True)
class BtmmLifecycleCursor:
    """Private resumable per-setup BTMM lifecycle cursor. Immutable; a new
    instance is produced each advance (transactional)."""

    symbol: InternalSymbol
    source_timeframe: Timeframe
    setup_record_id: UUID
    source_poi_record_id: UUID
    zone_top: Decimal
    zone_bottom: Decimal
    zone_height: Decimal
    direction: PoiDirection
    candidate_availability_time_utc: datetime
    is_formation_timeframe: bool
    entry_boundary: Decimal
    far_boundary: Decimal

    total_count: int = 0
    prev_candle: NormalizedCandle | None = None

    # Committed price-stage frontier.
    entered_forming_index: int | None = None
    entered_forming_candle: NormalizedCandle | None = None
    interaction_index: int | None = None
    interaction_class: BtmmInteractionClass | None = None
    interaction_candle: NormalizedCandle | None = None
    running_anchor: Decimal | None = None
    reaction_start_index: int | None = None
    reaction_anchor: Decimal | None = None
    window_candles: tuple[NormalizedCandle, ...] = ()
    window_atrs: tuple[Decimal | None, ...] = ()
    tier_result: ReactionTierResult | None = None
    window_close_candle: NormalizedCandle | None = None


def create_btmm_lifecycle_cursor(
    symbol: InternalSymbol,
    source_timeframe: Timeframe,
    setup_record_id: UUID,
    source_poi_record_id: UUID,
    zone_top: Decimal,
    zone_bottom: Decimal,
    direction: PoiDirection,
    candidate_availability_time_utc: datetime,
    configuration: BtmmConfiguration,
) -> BtmmLifecycleCursor:
    entry_boundary = zone_top if direction == PoiDirection.BULLISH else zone_bottom
    far_boundary = zone_bottom if direction == PoiDirection.BULLISH else zone_top
    return BtmmLifecycleCursor(
        symbol=symbol,
        source_timeframe=source_timeframe,
        setup_record_id=setup_record_id,
        source_poi_record_id=source_poi_record_id,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        zone_height=zone_top - zone_bottom,
        direction=direction,
        candidate_availability_time_utc=candidate_availability_time_utc,
        is_formation_timeframe=(source_timeframe in configuration.formation_timeframes),
        entry_boundary=entry_boundary,
        far_boundary=far_boundary,
    )


def advance_btmm_cursor(
    cursor: BtmmLifecycleCursor,
    candle: NormalizedCandle,
    atr_value: Decimal | None,
    configuration: BtmmConfiguration,
) -> BtmmLifecycleCursor:
    """Advance the cursor by exactly one appended candle (+ its full-prefix
    ATR-14). Only the currently-open price-stage scan tests this candle; committed
    stages are untouched. Never re-scans history."""
    m = cursor.total_count  # absolute index of this candle
    window_bars = configuration.reaction_window_bars
    is_bullish = cursor.direction == PoiDirection.BULLISH

    entered_forming_index = cursor.entered_forming_index
    entered_forming_candle = cursor.entered_forming_candle
    interaction_index = cursor.interaction_index
    interaction_class = cursor.interaction_class
    interaction_candle = cursor.interaction_candle
    running_anchor = cursor.running_anchor
    reaction_start_index = cursor.reaction_start_index
    reaction_anchor = cursor.reaction_anchor
    window_candles = cursor.window_candles
    window_atrs = cursor.window_atrs
    tier_result = cursor.tier_result
    window_close_candle = cursor.window_close_candle

    # 1. Forming: first candle strictly after the candidate's availability.
    if (
        entered_forming_index is None
        and candle.availability_time_utc > cursor.candidate_availability_time_utc
    ):
        entered_forming_index = m
        entered_forming_candle = candle

    # 2. First interaction: test this candle once if the interaction scan is open.
    if (
        entered_forming_index is not None
        and interaction_index is None
        and m >= entered_forming_index
    ):
        if m == 0:
            result = find_first_interaction(
                (candle,),
                0,
                (atr_value,),
                cursor.zone_top,
                cursor.zone_bottom,
                cursor.direction,
                configuration,
            )
        else:
            assert cursor.prev_candle is not None
            result = find_first_interaction(
                (cursor.prev_candle, candle),
                1,
                (None, atr_value),
                cursor.zone_top,
                cursor.zone_bottom,
                cursor.direction,
                configuration,
            )
        if result is not None:
            interaction_index = m
            interaction_class = result.interaction_class
            interaction_candle = candle
            if interaction_class in ELIGIBLE_INTERACTION_CLASSES:
                # Reaction anchor spans [interaction, reaction_start]; seed it now.
                running_anchor = candle.low if is_bullish else candle.high

    # 3. Reaction start: scan from interaction_index + 1.
    if (
        interaction_index is not None
        and interaction_class in ELIGIBLE_INTERACTION_CLASSES
        and reaction_start_index is None
        and m > interaction_index
    ):
        assert running_anchor is not None
        if is_bullish:
            running_anchor = min(running_anchor, candle.low)
            started = candle.close > cursor.entry_boundary
        else:
            running_anchor = max(running_anchor, candle.high)
            started = candle.close < cursor.entry_boundary
        if started:
            reaction_start_index = m
            reaction_anchor = running_anchor

    # 4. Reaction window: accumulate the bounded window; evaluate once it fills.
    if (
        reaction_start_index is not None
        and tier_result is None
        and reaction_start_index <= m < reaction_start_index + window_bars
    ):
        window_candles = (*window_candles, candle)
        window_atrs = (*window_atrs, atr_value)
        if len(window_candles) == window_bars:
            assert reaction_anchor is not None
            tier_result = evaluate_reaction_window(
                window_candles,
                window_atrs,
                0,
                reaction_anchor,
                cursor.far_boundary,
                cursor.zone_height,
                cursor.direction,
                configuration,
            )
            window_close_candle = candle

    return replace(
        cursor,
        total_count=m + 1,
        prev_candle=candle,
        entered_forming_index=entered_forming_index,
        entered_forming_candle=entered_forming_candle,
        interaction_index=interaction_index,
        interaction_class=interaction_class,
        interaction_candle=interaction_candle,
        running_anchor=running_anchor,
        reaction_start_index=reaction_start_index,
        reaction_anchor=reaction_anchor,
        window_candles=window_candles,
        window_atrs=window_atrs,
        tier_result=tier_result,
        window_close_candle=window_close_candle,
    )


def materialize_btmm_cursor(
    cursor: BtmmLifecycleCursor,
    poi_lifecycle_transitions: Sequence[PoiLifecycleTransition],
    reviewed_evidence: BtmmReviewedEvidence | None,
    configuration: BtmmConfiguration,
) -> LifecycleWalkResult:
    """Reproduce ``run_btmm_lifecycle``'s result exactly from the cached price-stage
    results plus the CURRENT evidence / POI-transition inputs, with no candle
    re-scan and without calling ``run_btmm_lifecycle``."""
    symbol = cursor.symbol
    source_timeframe = cursor.source_timeframe
    setup_record_id = cursor.setup_record_id
    is_formation_timeframe = cursor.is_formation_timeframe

    steps: list[_StepRecord] = [
        _StepRecord(None, _initial_fields(cursor.candidate_availability_time_utc))
    ]

    def emit(
        transition_type: BtmmLifecycleTransitionType,
        availability_time_utc: datetime,
        event_time_utc: datetime,
        new_fields: _StateFields,
        triggering_candle_record_id: UUID | None = None,
        triggering_reviewed_evidence_availability_time_utc: datetime | None = None,
        blocked_reason: BtmmBlockedReason | None = None,
    ) -> None:
        new_fields.availability_time_utc = availability_time_utc
        candidate = TransitionCandidate(
            symbol=symbol,
            timeframe=source_timeframe,
            btmm_setup_record_id=setup_record_id,
            transition_type=transition_type,
            blocked_reason=blocked_reason,
            triggering_candle_record_id=triggering_candle_record_id,
            triggering_reviewed_evidence_availability_time_utc=(
                triggering_reviewed_evidence_availability_time_utc
            ),
            event_time_utc=event_time_utc,
            availability_time_utc=availability_time_utc,
        )
        steps.append(_StepRecord(candidate, new_fields))

    if cursor.entered_forming_candle is not None:
        entered_forming_candle = cursor.entered_forming_candle
        fields = steps[-1].fields.copy()
        fields.primary_state = BtmmLifecycleStatus.BTMM_FORMING
        fields.formation_stage = BtmmFormationStage.POI_INTERACTION
        emit(
            BtmmLifecycleTransitionType.ENTERED_FORMING,
            entered_forming_candle.availability_time_utc,
            entered_forming_candle.event_time_utc,
            fields,
            triggering_candle_record_id=entered_forming_candle.record_id,
        )

        if cursor.interaction_index is not None:
            interaction_class = cursor.interaction_class
            interaction_candle = cursor.interaction_candle
            assert interaction_class is not None and interaction_candle is not None

            if interaction_class in ELIGIBLE_INTERACTION_CLASSES:
                fields = steps[-1].fields.copy()
                fields.accuracy_gate_status = BtmmGateStatus.PASS
                fields.interaction_class = interaction_class
                fields.formation_stage = BtmmFormationStage.REACTION_MONITORING
                emit(
                    BtmmLifecycleTransitionType.ACCURACY_GATE_CONFIRMED,
                    interaction_candle.availability_time_utc,
                    interaction_candle.event_time_utc,
                    fields,
                    triggering_candle_record_id=interaction_candle.record_id,
                )

                if cursor.tier_result is not None:
                    tier_result = cursor.tier_result
                    window_close_candle = cursor.window_close_candle
                    assert window_close_candle is not None

                    if (
                        tier_result.reaction_classification
                        == BtmmReactionClassification.WEAK_REACTION
                    ):
                        fields = steps[-1].fields.copy()
                        fields.primary_state = BtmmLifecycleStatus.BTMM_CANCELLED
                        fields.reaction_gate_status = BtmmGateStatus.FAIL
                        fields.reaction_classification = (
                            BtmmReactionClassification.WEAK_REACTION
                        )
                        fields.cancellation_reason = (
                            BtmmCancellationReason.WEAK_REACTION
                        )
                        emit(
                            BtmmLifecycleTransitionType.WEAK_REACTION,
                            window_close_candle.availability_time_utc,
                            window_close_candle.event_time_utc,
                            fields,
                            triggering_candle_record_id=window_close_candle.record_id,
                        )
                    else:
                        fields = steps[-1].fields.copy()
                        fields.reaction_gate_status = BtmmGateStatus.PASS
                        fields.reaction_classification = (
                            tier_result.reaction_classification
                        )
                        emit(
                            BtmmLifecycleTransitionType.REACTION_GATE_CONFIRMED,
                            window_close_candle.availability_time_utc,
                            window_close_candle.event_time_utc,
                            fields,
                            triggering_candle_record_id=window_close_candle.record_id,
                        )

                        if tier_result.reaction_speed_classification == (
                            LegSpeedClassification.SLOW_OR_UNCLEAR
                        ):
                            fields = steps[-1].fields.copy()
                            fields.primary_state = BtmmLifecycleStatus.BTMM_CANCELLED
                            fields.reaction_speed_gate_status = BtmmGateStatus.FAIL
                            fields.reaction_speed_classification = (
                                tier_result.reaction_speed_classification
                            )
                            fields.cancellation_reason = (
                                BtmmCancellationReason.REACTION_SPEED_FAILED
                            )
                            emit(
                                BtmmLifecycleTransitionType.REACTION_SPEED_FAILED,
                                window_close_candle.availability_time_utc,
                                window_close_candle.event_time_utc,
                                fields,
                                triggering_candle_record_id=window_close_candle.record_id,
                            )
                        else:
                            fields = steps[-1].fields.copy()
                            fields.reaction_speed_gate_status = BtmmGateStatus.PASS
                            fields.reaction_speed_classification = (
                                tier_result.reaction_speed_classification
                            )
                            fields.formation_stage = (
                                BtmmFormationStage.FINAL_GATE_EVALUATION
                            )
                            emit(
                                BtmmLifecycleTransitionType.REACTION_SPEED_GATE_CONFIRMED,
                                window_close_candle.availability_time_utc,
                                window_close_candle.event_time_utc,
                                fields,
                                triggering_candle_record_id=window_close_candle.record_id,
                            )

                            automatic_evidence = find_automatic_liquidity_evidence(
                                cursor.source_poi_record_id, poi_lifecycle_transitions
                            )
                            if automatic_evidence is not None:
                                fields = steps[-1].fields.copy()
                                fields.liquidity_location = (
                                    automatic_evidence.liquidity_location
                                )
                                fields.liquidity_evidence_source = (
                                    automatic_evidence.liquidity_evidence_source
                                )
                                steps.append(_StepRecord(None, fields))

                            t_reaction = window_close_candle.availability_time_utc
                            event_reaction = window_close_candle.event_time_utc

                            if reviewed_evidence is None:
                                fields = steps[-1].fields.copy()
                                fields.primary_state = (
                                    BtmmLifecycleStatus.BTMM_CANCELLED
                                )
                                fields.cancellation_reason = (
                                    BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE
                                )
                                emit(
                                    BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE,
                                    t_reaction,
                                    event_reaction,
                                    fields,
                                )
                            else:
                                t_evidence = reviewed_evidence.availability_time_utc
                                if t_evidence > t_reaction:
                                    fields = steps[-1].fields.copy()
                                    fields.primary_state = (
                                        BtmmLifecycleStatus.BTMM_BLOCKED
                                    )
                                    fields.blocked_reason = (
                                        BtmmBlockedReason.LIQUIDITY_REVIEW_PENDING
                                    )
                                    emit(
                                        BtmmLifecycleTransitionType.BLOCKED,
                                        t_reaction,
                                        event_reaction,
                                        fields,
                                        blocked_reason=(
                                            BtmmBlockedReason.LIQUIDITY_REVIEW_PENDING
                                        ),
                                    )

                                    outcome = _resolve_final_gates(
                                        reviewed_evidence, is_formation_timeframe
                                    )
                                    fields = steps[-1].fields.copy()
                                    fields.market_direction_status = (
                                        reviewed_evidence.market_direction_status
                                    )
                                    fields.analytical_framework_status = (
                                        reviewed_evidence.analytical_framework_status
                                    )
                                    fields.session_status = (
                                        reviewed_evidence.session_status
                                    )
                                    fields.volume_pillar_status = (
                                        reviewed_evidence.volume_pillar_status
                                    )
                                    fields.liquidity_evidence_status = (
                                        reviewed_evidence.liquidity_evidence_status
                                    )
                                    fields.reviewed_evidence_availability_time_utc = (
                                        t_evidence
                                    )
                                    if reviewed_evidence.liquidity_evidence_status == (
                                        BtmmLiquidityEvidenceStatus.PRESENT
                                    ):
                                        fields.liquidity_evidence_source = (
                                            reviewed_evidence.liquidity_event_source
                                        )
                                    if outcome.kind == "CANCEL":
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_CANCELLED
                                        )
                                        fields.cancellation_reason = (
                                            outcome.cancellation_reason
                                        )
                                        fields.blocked_reason = None
                                        transition_type = _cancel_transition_type(
                                            outcome.cancellation_reason
                                        )
                                        emit(
                                            transition_type,
                                            t_evidence,
                                            t_evidence,
                                            fields,
                                            triggering_reviewed_evidence_availability_time_utc=(
                                                t_evidence
                                            ),
                                        )
                                    elif outcome.kind == "CONFIRM":
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_CONFIRMED
                                        )
                                        fields.formation_timeframe_gate_status = (
                                            BtmmGateStatus.PASS
                                        )
                                        fields.blocked_reason = None
                                        emit(
                                            BtmmLifecycleTransitionType.CONFIRMED,
                                            t_evidence,
                                            t_evidence,
                                            fields,
                                            triggering_reviewed_evidence_availability_time_utc=(
                                                t_evidence
                                            ),
                                        )
                                    else:
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_FORMING
                                        )
                                        fields.blocked_reason = None
                                        emit(
                                            BtmmLifecycleTransitionType.RESUMED_FORMING,
                                            t_evidence,
                                            t_evidence,
                                            fields,
                                            triggering_reviewed_evidence_availability_time_utc=(
                                                t_evidence
                                            ),
                                        )
                                else:
                                    fields = steps[-1].fields.copy()
                                    fields.market_direction_status = (
                                        reviewed_evidence.market_direction_status
                                    )
                                    fields.analytical_framework_status = (
                                        reviewed_evidence.analytical_framework_status
                                    )
                                    fields.session_status = (
                                        reviewed_evidence.session_status
                                    )
                                    fields.volume_pillar_status = (
                                        reviewed_evidence.volume_pillar_status
                                    )
                                    fields.liquidity_evidence_status = (
                                        reviewed_evidence.liquidity_evidence_status
                                    )
                                    fields.reviewed_evidence_availability_time_utc = (
                                        t_evidence
                                    )
                                    if reviewed_evidence.liquidity_evidence_status == (
                                        BtmmLiquidityEvidenceStatus.PRESENT
                                    ):
                                        fields.liquidity_evidence_source = (
                                            reviewed_evidence.liquidity_event_source
                                        )

                                    outcome = _resolve_final_gates(
                                        reviewed_evidence, is_formation_timeframe
                                    )
                                    if outcome.kind == "CANCEL":
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_CANCELLED
                                        )
                                        fields.cancellation_reason = (
                                            outcome.cancellation_reason
                                        )
                                        transition_type = _cancel_transition_type(
                                            outcome.cancellation_reason
                                        )
                                        emit(
                                            transition_type,
                                            t_reaction,
                                            event_reaction,
                                            fields,
                                        )
                                    elif outcome.kind == "CONFIRM":
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_CONFIRMED
                                        )
                                        fields.formation_timeframe_gate_status = (
                                            BtmmGateStatus.PASS
                                        )
                                        emit(
                                            BtmmLifecycleTransitionType.CONFIRMED,
                                            t_reaction,
                                            event_reaction,
                                            fields,
                                        )
                                    else:
                                        fields.primary_state = (
                                            BtmmLifecycleStatus.BTMM_BLOCKED
                                        )
                                        fields.blocked_reason = outcome.blocked_reason
                                        emit(
                                            BtmmLifecycleTransitionType.BLOCKED,
                                            t_reaction,
                                            event_reaction,
                                            fields,
                                            blocked_reason=outcome.blocked_reason,
                                        )
            else:
                fields = steps[-1].fields.copy()
                fields.primary_state = BtmmLifecycleStatus.BTMM_CANCELLED
                fields.accuracy_gate_status = BtmmGateStatus.FAIL
                fields.interaction_class = interaction_class
                fields.cancellation_reason = (
                    BtmmCancellationReason.INTERACTION_INELIGIBLE
                )
                emit(
                    BtmmLifecycleTransitionType.INTERACTION_INELIGIBLE,
                    interaction_candle.availability_time_utc,
                    interaction_candle.event_time_utc,
                    fields,
                    triggering_candle_record_id=interaction_candle.record_id,
                )

    genuine_invalidation: PoiLifecycleTransition | None = None
    for transition in poi_lifecycle_transitions:
        if (
            transition.poi_record_id == cursor.source_poi_record_id
            and transition.transition_type
            == PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
        ):
            if (
                genuine_invalidation is None
                or transition.availability_time_utc
                < genuine_invalidation.availability_time_utc
            ):
                genuine_invalidation = transition

    if genuine_invalidation is None:
        kept_steps = steps
    else:
        inv_time = genuine_invalidation.availability_time_utc
        kept_steps = [steps[0]]
        for step in steps[1:]:
            if (
                step.candidate is not None
                and step.candidate.availability_time_utc < inv_time
            ):
                kept_steps.append(step)
            elif (
                step.candidate is None and step.fields.availability_time_utc < inv_time
            ):
                kept_steps.append(step)
            else:
                break

        last_state = kept_steps[-1].fields.primary_state
        if last_state != BtmmLifecycleStatus.BTMM_CANCELLED:
            fields = kept_steps[-1].fields.copy()
            fields.primary_state = BtmmLifecycleStatus.BTMM_CANCELLED
            fields.cancellation_reason = BtmmCancellationReason.POI_REJECTED
            fields.blocked_reason = None
            fields.availability_time_utc = inv_time
            candidate = TransitionCandidate(
                symbol=symbol,
                timeframe=source_timeframe,
                btmm_setup_record_id=setup_record_id,
                transition_type=BtmmLifecycleTransitionType.POI_REJECTED,
                blocked_reason=None,
                triggering_candle_record_id=genuine_invalidation.triggering_candle_record_id,
                triggering_reviewed_evidence_availability_time_utc=None,
                event_time_utc=genuine_invalidation.event_time_utc,
                availability_time_utc=inv_time,
            )
            kept_steps.append(_StepRecord(candidate, fields))

    transitions = tuple(
        step.candidate for step in kept_steps if step.candidate is not None
    )
    final_fields = kept_steps[-1].fields
    return LifecycleWalkResult(transitions=transitions, final_fields=final_fields)


def _cancel_transition_type(
    cancellation_reason: BtmmCancellationReason | None,
) -> BtmmLifecycleTransitionType:
    if cancellation_reason == BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE:
        return BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE
    if cancellation_reason == BtmmCancellationReason.CONTEXT_REJECTED:
        return BtmmLifecycleTransitionType.CONTEXT_REJECTED
    if cancellation_reason == BtmmCancellationReason.SESSION_INACTIVE:
        return BtmmLifecycleTransitionType.SESSION_INACTIVE
    return BtmmLifecycleTransitionType.VOLUME_PILLAR_FAILED
