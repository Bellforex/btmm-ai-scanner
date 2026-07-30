from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis
from btmm_ai_scanner.btmm.current_state import CurrentBtmmState
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmContextAlignmentStatus,
    BtmmDirection,
    BtmmGateStatus,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLiquidityEvidenceStatus,
    BtmmReactionClassification,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.observation import BtmmObservation
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.scanner.btmm_validation import build_btmm_validation_report
from btmm_ai_scanner.scanner.labels import ExpectedBtmmLabel, ReviewedScannerCase

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_FINGERPRINT = "a" * 64
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_POI_ID = UUID("0193f450-9999-7abc-8def-000000000001")


def _observation(index: int, availability_offset_minutes: int = 5) -> BtmmObservation:
    availability = _BASE_TIME + timedelta(minutes=availability_offset_minutes)
    return BtmmObservation(
        record_id=UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M1,
        btmm_direction=BtmmDirection.BULLISH_BTMM,
        source_poi_record_id=_POI_ID,
        source_poi_type=PoiType.BULLISH_ENGULFING,
        source_poi_direction=PoiDirection.BULLISH,
        candidate_event_time_utc=availability,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _state(
    observation: BtmmObservation,
    primary_state: BtmmLifecycleStatus = BtmmLifecycleStatus.BTMM_CANDIDATE,
    interaction_class: BtmmInteractionClass | None = None,
    reaction_classification: BtmmReactionClassification | None = None,
    blocked_reason: BtmmBlockedReason | None = None,
    availability_offset_minutes: int | None = None,
) -> CurrentBtmmState:
    availability = (
        _BASE_TIME + timedelta(minutes=availability_offset_minutes)
        if availability_offset_minutes is not None
        else observation.availability_time_utc
    )
    return CurrentBtmmState(
        record_id=UUID(f"0193f450-2222-7abc-8def-{1:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=observation.symbol,
        timeframe=observation.source_timeframe,
        btmm_setup_record_id=observation.record_id,
        btmm_direction=observation.btmm_direction,
        source_poi_type=observation.source_poi_type,
        primary_state=primary_state,
        formation_stage=None,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        accuracy_gate_status=BtmmGateStatus.PASS,
        interaction_class=interaction_class,
        reaction_gate_status=BtmmGateStatus.PASS,
        reaction_classification=reaction_classification,
        reaction_speed_gate_status=BtmmGateStatus.PASS,
        reaction_speed_classification=None,
        formation_timeframe_gate_status=BtmmGateStatus.PASS,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        liquidity_location=None,
        liquidity_evidence_source=None,
        reviewed_evidence_availability_time_utc=None,
        cancellation_reason=None,
        blocked_reason=blocked_reason,
        latest_lifecycle_transition_id=None,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _btmm_analysis(
    observations: tuple[BtmmObservation, ...], states: tuple[CurrentBtmmState, ...]
) -> BtmmAnalysis:
    return BtmmAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M1,),
        analyzed_candle_count_by_timeframe=(2,),
        btmm_observations=observations,
        btmm_lifecycle_transitions=(),
        current_btmm_states=states,
    )


def _label(
    label_id: str = "btmm-1",
    expected_candidate_offset: int | None = 5,
    expected_forming_offset: int | None = None,
    expected_confirmation_offset: int | None = None,
    expected_final_primary_state: BtmmLifecycleStatus = BtmmLifecycleStatus.BTMM_CANDIDATE,
    expected_interaction_classification: BtmmInteractionClass | None = None,
    expected_reaction_classification: BtmmReactionClassification | None = None,
) -> ExpectedBtmmLabel:
    def _time(offset: int | None) -> datetime | None:
        return _BASE_TIME + timedelta(minutes=offset) if offset is not None else None

    return ExpectedBtmmLabel(
        label_id=label_id,
        source_poi_label_id="poi-1",
        expected_direction=BtmmDirection.BULLISH_BTMM,
        expected_timeframe=Timeframe.M1,
        expected_candidate_availability_time_utc=_time(expected_candidate_offset),
        expected_forming_availability_time_utc=_time(expected_forming_offset),
        expected_confirmation_or_cancellation_time_utc=_time(
            expected_confirmation_offset
        ),
        expected_final_primary_state=expected_final_primary_state,
        expected_reaction_classification=expected_reaction_classification,
        expected_interaction_classification=expected_interaction_classification,
    )


def _case(
    labels: tuple[ExpectedBtmmLabel, ...], btmm_labels_complete: bool = True
) -> ReviewedScannerCase:
    return ReviewedScannerCase(
        case_id="case-1",
        dataset_version="v1",
        reviewer_id="reviewer-1",
        review_version="1",
        symbol=InternalSymbol.XAUUSD,
        evaluation_start_time_utc=_BASE_TIME,
        evaluation_end_time_utc=_BASE_TIME + timedelta(days=1),
        required_timeframes=(Timeframe.M1,),
        expected_poi_labels=(),
        expected_btmm_labels=labels,
        poi_labels_complete=True,
        btmm_labels_complete=btmm_labels_complete,
        notes="",
    )


def test_btmm_validation_reports_expected_detected_and_matched_counts() -> None:
    observation = _observation(0)
    state = _state(observation)
    report = build_btmm_validation_report(
        _case((_label(),)), _btmm_analysis((observation,), (state,))
    )
    assert report.expected_count == 1
    assert report.detected_count == 1
    assert report.matched_count == 1


def test_btmm_validation_reports_missed_and_unexpected_counts() -> None:
    report = build_btmm_validation_report(_case((_label(),)), _btmm_analysis((), ()))
    assert report.missed_count == 1

    observation = _observation(0)
    state = _state(observation)
    report_2 = build_btmm_validation_report(
        _case((), btmm_labels_complete=True), _btmm_analysis((observation,), (state,))
    )
    assert report_2.unexpected_count == 1


def test_btmm_validation_verifies_source_poi_linkage() -> None:
    observation = _observation(0)
    assert observation.source_poi_record_id == _POI_ID


def test_btmm_validation_computes_candidate_and_forming_timing_delay() -> None:
    observation = _observation(0, availability_offset_minutes=5)
    state = _state(observation, availability_offset_minutes=15)
    report = build_btmm_validation_report(
        _case((_label(expected_candidate_offset=5, expected_forming_offset=15),)),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.mean_candidate_timing_delay_seconds == Decimal("0")
    assert report.mean_forming_timing_delay_seconds == Decimal("0")


def test_btmm_validation_computes_blocked_and_resumed_timing_delay() -> None:
    observation = _observation(0, availability_offset_minutes=5)
    state = _state(
        observation,
        primary_state=BtmmLifecycleStatus.BTMM_BLOCKED,
        blocked_reason=BtmmBlockedReason.CONTEXT_UNKNOWN,
        availability_offset_minutes=20,
    )
    report = build_btmm_validation_report(
        _case((_label(expected_forming_offset=20),)),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.mean_forming_timing_delay_seconds == Decimal("0")


def test_btmm_validation_computes_confirmation_or_cancellation_timing_delay() -> None:
    observation = _observation(0, availability_offset_minutes=5)
    state = _state(
        observation,
        primary_state=BtmmLifecycleStatus.BTMM_CONFIRMED,
        availability_offset_minutes=30,
    )
    report = build_btmm_validation_report(
        _case(
            (
                _label(
                    expected_confirmation_offset=30,
                    expected_final_primary_state=BtmmLifecycleStatus.BTMM_CONFIRMED,
                ),
            )
        ),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.mean_confirmation_or_cancellation_timing_delay_seconds == Decimal("0")


def test_btmm_validation_reports_interaction_classification_agreement() -> None:
    observation = _observation(0)
    state = _state(observation, interaction_class=BtmmInteractionClass.EDGE_TOUCH)
    report = build_btmm_validation_report(
        _case(
            (
                _label(
                    expected_interaction_classification=BtmmInteractionClass.EDGE_TOUCH
                ),
            )
        ),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.interaction_agreement_count == 1


def test_btmm_validation_reports_reaction_classification_agreement() -> None:
    observation = _observation(0)
    state = _state(
        observation,
        reaction_classification=BtmmReactionClassification.STANDARD_REACTION,
    )
    report = build_btmm_validation_report(
        _case(
            (
                _label(
                    expected_reaction_classification=BtmmReactionClassification.STANDARD_REACTION
                ),
            )
        ),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.reaction_agreement_count == 1


def test_btmm_validation_reports_final_state_agreement() -> None:
    observation = _observation(0)
    state = _state(observation, primary_state=BtmmLifecycleStatus.BTMM_CONFIRMED)
    report = build_btmm_validation_report(
        _case(
            (_label(expected_final_primary_state=BtmmLifecycleStatus.BTMM_CONFIRMED),)
        ),
        _btmm_analysis((observation,), (state,)),
    )
    assert report.final_state_agreement_count == 1


def test_btmm_validation_respects_case_completeness_flag() -> None:
    observation = _observation(0)
    state = _state(observation)
    complete = build_btmm_validation_report(
        _case((), btmm_labels_complete=True), _btmm_analysis((observation,), (state,))
    )
    incomplete = build_btmm_validation_report(
        _case((), btmm_labels_complete=False), _btmm_analysis((observation,), (state,))
    )
    assert complete.unexpected_count == 1
    assert complete.unreviewed_count == 0
    assert incomplete.unexpected_count == 0
    assert incomplete.unreviewed_count == 1
