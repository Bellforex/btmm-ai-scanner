from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmFormationStage,
    BtmmGateStatus,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLifecycleTransitionType,
    BtmmLiquidityEvidenceStatus,
    BtmmLiquidityLocation,
    BtmmReactionClassification,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.interaction import (
    ELIGIBLE_INTERACTION_CLASSES,
    find_first_interaction,
)
from btmm_ai_scanner.btmm.liquidity import find_automatic_liquidity_evidence
from btmm_ai_scanner.btmm.reaction import (
    compute_reaction_anchor,
    evaluate_reaction_window,
    find_reaction_start,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.measurements.legs import LegSpeedClassification
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation


class BtmmLifecycleTransition(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    btmm_setup_record_id: UUIDv7
    transition_type: BtmmLifecycleTransitionType
    blocked_reason: BtmmBlockedReason | None
    triggering_candle_record_id: UUIDv7 | None
    triggering_reviewed_evidence_availability_time_utc: datetime | None
    event_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7


class TransitionCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    btmm_setup_record_id: UUID
    transition_type: BtmmLifecycleTransitionType
    blocked_reason: BtmmBlockedReason | None
    triggering_candle_record_id: UUID | None
    triggering_reviewed_evidence_availability_time_utc: datetime | None
    event_time_utc: datetime
    availability_time_utc: datetime


@dataclass
class _StateFields:
    primary_state: BtmmLifecycleStatus
    formation_stage: BtmmFormationStage | None
    market_direction_status: BtmmContextAlignmentStatus
    analytical_framework_status: BtmmContextAlignmentStatus
    session_status: BtmmSessionStatus
    accuracy_gate_status: BtmmGateStatus
    interaction_class: BtmmInteractionClass | None
    reaction_gate_status: BtmmGateStatus
    reaction_classification: BtmmReactionClassification | None
    reaction_speed_gate_status: BtmmGateStatus
    reaction_speed_classification: LegSpeedClassification | None
    formation_timeframe_gate_status: BtmmGateStatus
    volume_pillar_status: BtmmVolumePillarStatus
    liquidity_evidence_status: BtmmLiquidityEvidenceStatus
    liquidity_location: BtmmLiquidityLocation | None
    liquidity_evidence_source: BtmmEvidenceSource | None
    reviewed_evidence_availability_time_utc: datetime | None
    cancellation_reason: BtmmCancellationReason | None
    blocked_reason: BtmmBlockedReason | None
    availability_time_utc: datetime

    def copy(self) -> "_StateFields":
        return _StateFields(**vars(self))


class _StepRecord(NamedTuple):
    candidate: TransitionCandidate | None
    fields: _StateFields


class LifecycleWalkResult(NamedTuple):
    transitions: tuple[TransitionCandidate, ...]
    final_fields: _StateFields


def _initial_fields(candidate_availability: datetime) -> _StateFields:
    return _StateFields(
        primary_state=BtmmLifecycleStatus.BTMM_CANDIDATE,
        formation_stage=None,
        market_direction_status=BtmmContextAlignmentStatus.PENDING,
        analytical_framework_status=BtmmContextAlignmentStatus.PENDING,
        session_status=BtmmSessionStatus.PENDING,
        accuracy_gate_status=BtmmGateStatus.PENDING,
        interaction_class=None,
        reaction_gate_status=BtmmGateStatus.PENDING,
        reaction_classification=None,
        reaction_speed_gate_status=BtmmGateStatus.PENDING,
        reaction_speed_classification=None,
        formation_timeframe_gate_status=BtmmGateStatus.PENDING,
        volume_pillar_status=BtmmVolumePillarStatus.PENDING,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PENDING,
        liquidity_location=None,
        liquidity_evidence_source=None,
        reviewed_evidence_availability_time_utc=None,
        cancellation_reason=None,
        blocked_reason=None,
        availability_time_utc=candidate_availability,
    )


class _ResolveOutcome(NamedTuple):
    kind: str  # "CANCEL", "CONFIRM", "BLOCKED"
    cancellation_reason: BtmmCancellationReason | None
    blocked_reason: BtmmBlockedReason | None


def _resolve_final_gates(
    evidence: BtmmReviewedEvidence, is_formation_timeframe: bool
) -> _ResolveOutcome:
    if evidence.liquidity_evidence_status != BtmmLiquidityEvidenceStatus.PRESENT:
        return _ResolveOutcome(
            "CANCEL", BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE, None
        )

    if (
        evidence.market_direction_status == BtmmContextAlignmentStatus.MISALIGNED
        or evidence.analytical_framework_status == BtmmContextAlignmentStatus.MISALIGNED
    ):
        return _ResolveOutcome("CANCEL", BtmmCancellationReason.CONTEXT_REJECTED, None)
    if evidence.session_status == BtmmSessionStatus.INACTIVE:
        return _ResolveOutcome("CANCEL", BtmmCancellationReason.SESSION_INACTIVE, None)
    if evidence.volume_pillar_status == BtmmVolumePillarStatus.FAILS:
        return _ResolveOutcome(
            "CANCEL", BtmmCancellationReason.VOLUME_PILLAR_FAILED, None
        )

    fully_aligned = (
        evidence.market_direction_status == BtmmContextAlignmentStatus.ALIGNED
        and evidence.analytical_framework_status == BtmmContextAlignmentStatus.ALIGNED
        and evidence.session_status == BtmmSessionStatus.ACTIVE
        and evidence.volume_pillar_status == BtmmVolumePillarStatus.SUPPORTS
    )
    if is_formation_timeframe and fully_aligned:
        return _ResolveOutcome("CONFIRM", None, None)

    if not is_formation_timeframe:
        reason = BtmmBlockedReason.FORMATION_TIMEFRAME_NOT_CONFIRMED
    elif (
        evidence.market_direction_status != BtmmContextAlignmentStatus.ALIGNED
        or evidence.analytical_framework_status != BtmmContextAlignmentStatus.ALIGNED
        or evidence.session_status != BtmmSessionStatus.ACTIVE
    ):
        reason = BtmmBlockedReason.CONTEXT_UNKNOWN
    else:
        reason = BtmmBlockedReason.VOLUME_REVIEW_PENDING
    return _ResolveOutcome("BLOCKED", None, reason)


def run_btmm_lifecycle(
    symbol: InternalSymbol,
    source_timeframe: Timeframe,
    btmm_setup_record_id: UUID,
    source_poi: PoiObservation,
    candidate_availability_time_utc: datetime,
    bundle_candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    poi_lifecycle_transitions: Sequence[PoiLifecycleTransition],
    reviewed_evidence: BtmmReviewedEvidence | None,
    configuration: BtmmConfiguration,
) -> LifecycleWalkResult:
    steps: list[_StepRecord] = [
        _StepRecord(None, _initial_fields(candidate_availability_time_utc))
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
            btmm_setup_record_id=btmm_setup_record_id,
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

    zone_top = source_poi.zone_top
    zone_bottom = source_poi.zone_bottom
    zone_height = zone_top - zone_bottom
    direction = source_poi.direction
    is_formation_timeframe = source_timeframe in configuration.formation_timeframes

    entered_forming_index: int | None = None
    for index, candle in enumerate(bundle_candles):
        if candle.availability_time_utc > candidate_availability_time_utc:
            entered_forming_index = index
            break

    if entered_forming_index is not None:
        entered_forming_candle = bundle_candles[entered_forming_index]
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

        interaction_result = find_first_interaction(
            bundle_candles,
            entered_forming_index,
            atr_values,
            zone_top,
            zone_bottom,
            direction,
            configuration,
        )

        if interaction_result is not None:
            interaction_index, interaction_class = interaction_result
            interaction_candle = bundle_candles[interaction_index]

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

                entry_boundary = (
                    zone_top if direction == PoiDirection.BULLISH else zone_bottom
                )
                far_boundary = (
                    zone_bottom if direction == PoiDirection.BULLISH else zone_top
                )

                reaction_start_index = find_reaction_start(
                    bundle_candles, interaction_index + 1, entry_boundary, direction
                )

                if reaction_start_index is not None:
                    window_bars = configuration.reaction_window_bars
                    if len(bundle_candles) - reaction_start_index >= window_bars:
                        window_close_candle = bundle_candles[
                            reaction_start_index + window_bars - 1
                        ]
                        reaction_anchor = compute_reaction_anchor(
                            bundle_candles,
                            interaction_index,
                            reaction_start_index,
                            direction,
                        )
                        tier_result = evaluate_reaction_window(
                            bundle_candles,
                            atr_values,
                            reaction_start_index,
                            reaction_anchor,
                            far_boundary,
                            zone_height,
                            direction,
                            configuration,
                        )

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
                                fields.primary_state = (
                                    BtmmLifecycleStatus.BTMM_CANCELLED
                                )
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
                                    source_poi.record_id, poi_lifecycle_transitions
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
                                        fields.analytical_framework_status = reviewed_evidence.analytical_framework_status
                                        fields.session_status = (
                                            reviewed_evidence.session_status
                                        )
                                        fields.volume_pillar_status = (
                                            reviewed_evidence.volume_pillar_status
                                        )
                                        fields.liquidity_evidence_status = (
                                            reviewed_evidence.liquidity_evidence_status
                                        )
                                        fields.reviewed_evidence_availability_time_utc = t_evidence
                                        if (
                                            reviewed_evidence.liquidity_evidence_status
                                            == (BtmmLiquidityEvidenceStatus.PRESENT)
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
                                            transition_type = (
                                                BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE
                                                if outcome.cancellation_reason
                                                == BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE
                                                else (
                                                    BtmmLifecycleTransitionType.CONTEXT_REJECTED
                                                    if outcome.cancellation_reason
                                                    == BtmmCancellationReason.CONTEXT_REJECTED
                                                    else (
                                                        BtmmLifecycleTransitionType.SESSION_INACTIVE
                                                        if outcome.cancellation_reason
                                                        == BtmmCancellationReason.SESSION_INACTIVE
                                                        else (
                                                            BtmmLifecycleTransitionType.VOLUME_PILLAR_FAILED
                                                        )
                                                    )
                                                )
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
                                        fields.analytical_framework_status = reviewed_evidence.analytical_framework_status
                                        fields.session_status = (
                                            reviewed_evidence.session_status
                                        )
                                        fields.volume_pillar_status = (
                                            reviewed_evidence.volume_pillar_status
                                        )
                                        fields.liquidity_evidence_status = (
                                            reviewed_evidence.liquidity_evidence_status
                                        )
                                        fields.reviewed_evidence_availability_time_utc = t_evidence
                                        if (
                                            reviewed_evidence.liquidity_evidence_status
                                            == (BtmmLiquidityEvidenceStatus.PRESENT)
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
                                            transition_type = (
                                                BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE
                                                if outcome.cancellation_reason
                                                == BtmmCancellationReason.NO_LIQUIDITY_EVIDENCE
                                                else (
                                                    BtmmLifecycleTransitionType.CONTEXT_REJECTED
                                                    if outcome.cancellation_reason
                                                    == BtmmCancellationReason.CONTEXT_REJECTED
                                                    else (
                                                        BtmmLifecycleTransitionType.SESSION_INACTIVE
                                                        if outcome.cancellation_reason
                                                        == BtmmCancellationReason.SESSION_INACTIVE
                                                        else (
                                                            BtmmLifecycleTransitionType.VOLUME_PILLAR_FAILED
                                                        )
                                                    )
                                                )
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
                                            fields.blocked_reason = (
                                                outcome.blocked_reason
                                            )
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
            transition.poi_record_id == source_poi.record_id
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
                btmm_setup_record_id=btmm_setup_record_id,
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
