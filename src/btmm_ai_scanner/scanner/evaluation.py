import hashlib
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis
from btmm_ai_scanner.btmm.enums import BtmmLifecycleStatus, BtmmLifecycleTransitionType
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.scanner.btmm_validation import (
    BtmmValidationReport,
    build_btmm_validation_report,
)
from btmm_ai_scanner.scanner.enums import LabelMatchStatus
from btmm_ai_scanner.scanner.health import (
    ScannerHealthReport,
    build_scanner_health_report,
)
from btmm_ai_scanner.scanner.labels import ReviewedScannerCase
from btmm_ai_scanner.scanner.lifecycle_validation import (
    LifecycleValidationReport,
    build_lifecycle_validation_report,
)
from btmm_ai_scanner.scanner.matching import LabelMatch
from btmm_ai_scanner.scanner.poi_validation import (
    PoiValidationReport,
    build_poi_validation_report,
)
from btmm_ai_scanner.scanner.replay import ScannerReplayResult

_CANCELLATION_TRANSITION_TYPES: frozenset[BtmmLifecycleTransitionType] = frozenset(
    {
        BtmmLifecycleTransitionType.POI_REJECTED,
        BtmmLifecycleTransitionType.CONTEXT_REJECTED,
        BtmmLifecycleTransitionType.SESSION_INACTIVE,
        BtmmLifecycleTransitionType.VOLUME_PILLAR_FAILED,
        BtmmLifecycleTransitionType.NO_LIQUIDITY_EVIDENCE,
    }
)
_FORMING_TRANSITION_TYPES: frozenset[BtmmLifecycleTransitionType] = frozenset(
    {
        BtmmLifecycleTransitionType.ENTERED_FORMING,
        BtmmLifecycleTransitionType.RESUMED_FORMING,
    }
)


class ScannerBacktestReport(ContractModel):
    poi_validation_report: PoiValidationReport
    btmm_validation_report: BtmmValidationReport
    lifecycle_validation_report: LifecycleValidationReport
    health_report: ScannerHealthReport
    replay_result: ScannerReplayResult


@dataclass(frozen=True)
class _ReviewedLifecycleEvent:
    record_id: UUID
    btmm_setup_record_id: UUID | None
    poi_record_id: UUID | None
    transition_type: str
    event_time_utc: datetime
    availability_time_utc: datetime


def _synthetic_uuidv7(seed: str) -> UUID:
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    raw = bytearray(digest[:16])
    raw[6] = (raw[6] & 0x0F) | 0x70
    raw[8] = (raw[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(raw))


def _detected_final_state_label(transition_type: BtmmLifecycleTransitionType) -> str:
    if transition_type == BtmmLifecycleTransitionType.CONFIRMED:
        return str(BtmmLifecycleStatus.BTMM_CONFIRMED)
    if transition_type in _CANCELLATION_TRANSITION_TYPES:
        return str(BtmmLifecycleStatus.BTMM_CANCELLED)
    return str(transition_type)


def _mean_or_none(values: list[Decimal]) -> Decimal | None:
    if len(values) == 0:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def _combine_matches(
    reports_matches: list[tuple[LabelMatch, ...]],
) -> tuple[LabelMatch, ...]:
    combined: list[LabelMatch] = []
    for matches in reports_matches:
        combined.extend(matches)
    combined.sort(
        key=lambda m: (
            m.expected_label_id if m.expected_label_id is not None else "",
            str(m.detected_record_id) if m.detected_record_id is not None else "",
        )
    )
    return tuple(combined)


def _combine_poi_reports(reports: list[PoiValidationReport]) -> PoiValidationReport:
    if len(reports) == 0:
        return PoiValidationReport(
            expected_count=0,
            detected_count=0,
            matched_count=0,
            missed_count=0,
            unexpected_count=0,
            unreviewed_count=0,
            type_match_count=0,
            direction_match_count=0,
            mean_boundary_error_ticks=None,
            mean_overlap_ratio=None,
            mean_confirmation_delay_seconds=None,
            lifecycle_agreement_count=0,
            final_state_agreement_count=0,
            matches=(),
        )

    boundary_errors = [
        m.boundary_error_ticks
        for report in reports
        for m in report.matches
        if m.boundary_error_ticks is not None
    ]
    overlap_ratios = [
        m.overlap_ratio
        for report in reports
        for m in report.matches
        if m.overlap_ratio is not None
    ]
    delays = [
        m.availability_delay
        for report in reports
        for m in report.matches
        if m.availability_delay is not None
    ]

    return PoiValidationReport(
        expected_count=sum(r.expected_count for r in reports),
        detected_count=sum(r.detected_count for r in reports),
        matched_count=sum(r.matched_count for r in reports),
        missed_count=sum(r.missed_count for r in reports),
        unexpected_count=sum(r.unexpected_count for r in reports),
        unreviewed_count=sum(r.unreviewed_count for r in reports),
        type_match_count=sum(r.type_match_count for r in reports),
        direction_match_count=sum(r.direction_match_count for r in reports),
        mean_boundary_error_ticks=_mean_or_none(boundary_errors),
        mean_overlap_ratio=_mean_or_none(overlap_ratios),
        mean_confirmation_delay_seconds=_mean_or_none(delays),
        lifecycle_agreement_count=sum(r.lifecycle_agreement_count for r in reports),
        final_state_agreement_count=sum(r.final_state_agreement_count for r in reports),
        matches=_combine_matches([r.matches for r in reports]),
    )


def _combine_btmm_reports(reports: list[BtmmValidationReport]) -> BtmmValidationReport:
    if len(reports) == 0:
        return BtmmValidationReport(
            expected_count=0,
            detected_count=0,
            matched_count=0,
            missed_count=0,
            unexpected_count=0,
            unreviewed_count=0,
            mean_candidate_timing_delay_seconds=None,
            mean_forming_timing_delay_seconds=None,
            mean_confirmation_or_cancellation_timing_delay_seconds=None,
            interaction_agreement_count=0,
            reaction_agreement_count=0,
            final_state_agreement_count=0,
            matches=(),
        )

    return BtmmValidationReport(
        expected_count=sum(r.expected_count for r in reports),
        detected_count=sum(r.detected_count for r in reports),
        matched_count=sum(r.matched_count for r in reports),
        missed_count=sum(r.missed_count for r in reports),
        unexpected_count=sum(r.unexpected_count for r in reports),
        unreviewed_count=sum(r.unreviewed_count for r in reports),
        mean_candidate_timing_delay_seconds=_mean_or_none(
            [
                value
                for r in reports
                if r.mean_candidate_timing_delay_seconds is not None
                for value in [r.mean_candidate_timing_delay_seconds]
            ]
        ),
        mean_forming_timing_delay_seconds=_mean_or_none(
            [
                value
                for r in reports
                if r.mean_forming_timing_delay_seconds is not None
                for value in [r.mean_forming_timing_delay_seconds]
            ]
        ),
        mean_confirmation_or_cancellation_timing_delay_seconds=_mean_or_none(
            [
                value
                for r in reports
                if r.mean_confirmation_or_cancellation_timing_delay_seconds is not None
                for value in [r.mean_confirmation_or_cancellation_timing_delay_seconds]
            ]
        ),
        interaction_agreement_count=sum(r.interaction_agreement_count for r in reports),
        reaction_agreement_count=sum(r.reaction_agreement_count for r in reports),
        final_state_agreement_count=sum(r.final_state_agreement_count for r in reports),
        matches=_combine_matches([r.matches for r in reports]),
    )


def _build_reviewed_poi_lifecycle_events(
    case: ReviewedScannerCase,
    poi_report: PoiValidationReport,
    poi_analysis: PoiAnalysis,
) -> tuple[list[_ReviewedLifecycleEvent], list[_ReviewedLifecycleEvent]]:
    labels_by_id = {label.label_id: label for label in case.expected_poi_labels}
    states_by_poi_record_id = {
        state.poi_record_id: state for state in poi_analysis.current_poi_states
    }

    expected: list[_ReviewedLifecycleEvent] = []
    actual: list[_ReviewedLifecycleEvent] = []
    for match in poi_report.matches:
        if match.status != LabelMatchStatus.MATCHED:
            continue
        assert match.expected_label_id is not None
        assert match.detected_record_id is not None
        label = labels_by_id[match.expected_label_id]
        if label.expected_final_lifecycle_status is None:
            continue

        key_id = match.detected_record_id
        expected.append(
            _ReviewedLifecycleEvent(
                record_id=key_id,
                btmm_setup_record_id=None,
                poi_record_id=key_id,
                transition_type=str(label.expected_final_lifecycle_status),
                event_time_utc=label.latest_acceptable_availability_time_utc,
                availability_time_utc=label.latest_acceptable_availability_time_utc,
            )
        )
        state = states_by_poi_record_id.get(match.detected_record_id)
        if state is not None:
            actual.append(
                _ReviewedLifecycleEvent(
                    record_id=key_id,
                    btmm_setup_record_id=None,
                    poi_record_id=key_id,
                    transition_type=str(state.poi_lifecycle_status),
                    event_time_utc=state.availability_time_utc,
                    availability_time_utc=state.availability_time_utc,
                )
            )
    return expected, actual


def _build_reviewed_btmm_lifecycle_events(
    case: ReviewedScannerCase,
    btmm_report: BtmmValidationReport,
    btmm_analysis: BtmmAnalysis,
) -> tuple[list[_ReviewedLifecycleEvent], list[_ReviewedLifecycleEvent]]:
    labels_by_id = {label.label_id: label for label in case.expected_btmm_labels}
    observations_by_id = {
        observation.record_id: observation
        for observation in btmm_analysis.btmm_observations
    }
    transitions_by_setup: dict[UUID, list[object]] = {}
    for transition in btmm_analysis.btmm_lifecycle_transitions:
        transitions_by_setup.setdefault(transition.btmm_setup_record_id, []).append(
            transition
        )

    expected: list[_ReviewedLifecycleEvent] = []
    actual: list[_ReviewedLifecycleEvent] = []

    for match in btmm_report.matches:
        if match.status != LabelMatchStatus.MATCHED:
            continue
        assert match.expected_label_id is not None
        assert match.detected_record_id is not None
        label = labels_by_id[match.expected_label_id]
        observation = observations_by_id.get(match.detected_record_id)
        if observation is None:
            continue
        setup_transitions = transitions_by_setup.get(observation.record_id, [])

        if label.expected_candidate_availability_time_utc is not None:
            key_id = observation.record_id
            expected.append(
                _ReviewedLifecycleEvent(
                    record_id=key_id,
                    btmm_setup_record_id=observation.record_id,
                    poi_record_id=None,
                    transition_type=str(BtmmLifecycleStatus.BTMM_CANDIDATE),
                    event_time_utc=label.expected_candidate_availability_time_utc,
                    availability_time_utc=label.expected_candidate_availability_time_utc,
                )
            )
            actual.append(
                _ReviewedLifecycleEvent(
                    record_id=key_id,
                    btmm_setup_record_id=observation.record_id,
                    poi_record_id=None,
                    transition_type=str(BtmmLifecycleStatus.BTMM_CANDIDATE),
                    event_time_utc=observation.candidate_event_time_utc,
                    availability_time_utc=observation.availability_time_utc,
                )
            )

        if label.expected_forming_availability_time_utc is not None:
            forming_transitions = [
                t
                for t in setup_transitions
                if t.transition_type in _FORMING_TRANSITION_TYPES  # type: ignore[attr-defined]
            ]
            if len(forming_transitions) > 0:
                detected = min(
                    forming_transitions,
                    key=lambda t: t.availability_time_utc,  # type: ignore[attr-defined]
                )
                key_id = detected.record_id  # type: ignore[attr-defined]
            else:
                detected = None
                key_id = _synthetic_uuidv7(f"{label.label_id}:forming")
            expected.append(
                _ReviewedLifecycleEvent(
                    record_id=key_id,
                    btmm_setup_record_id=observation.record_id,
                    poi_record_id=None,
                    transition_type=str(BtmmLifecycleStatus.BTMM_FORMING),
                    event_time_utc=label.expected_forming_availability_time_utc,
                    availability_time_utc=label.expected_forming_availability_time_utc,
                )
            )
            if detected is not None:
                actual.append(
                    _ReviewedLifecycleEvent(
                        record_id=key_id,
                        btmm_setup_record_id=observation.record_id,
                        poi_record_id=None,
                        transition_type=str(BtmmLifecycleStatus.BTMM_FORMING),
                        event_time_utc=detected.event_time_utc,  # type: ignore[attr-defined]
                        availability_time_utc=detected.availability_time_utc,  # type: ignore[attr-defined]
                    )
                )

        if label.expected_confirmation_or_cancellation_time_utc is not None:
            terminal_transitions = [
                t
                for t in setup_transitions
                if t.transition_type == BtmmLifecycleTransitionType.CONFIRMED  # type: ignore[attr-defined]
                or t.transition_type in _CANCELLATION_TRANSITION_TYPES  # type: ignore[attr-defined]
            ]
            if len(terminal_transitions) > 0:
                detected = max(
                    terminal_transitions,
                    key=lambda t: t.availability_time_utc,  # type: ignore[attr-defined]
                )
                key_id = detected.record_id  # type: ignore[attr-defined]
            else:
                detected = None
                key_id = _synthetic_uuidv7(f"{label.label_id}:terminal")
            expected.append(
                _ReviewedLifecycleEvent(
                    record_id=key_id,
                    btmm_setup_record_id=observation.record_id,
                    poi_record_id=None,
                    transition_type=str(label.expected_final_primary_state),
                    event_time_utc=label.expected_confirmation_or_cancellation_time_utc,
                    availability_time_utc=label.expected_confirmation_or_cancellation_time_utc,
                )
            )
            if detected is not None:
                actual.append(
                    _ReviewedLifecycleEvent(
                        record_id=key_id,
                        btmm_setup_record_id=observation.record_id,
                        poi_record_id=None,
                        transition_type=_detected_final_state_label(
                            detected.transition_type  # type: ignore[attr-defined]
                        ),
                        event_time_utc=detected.event_time_utc,  # type: ignore[attr-defined]
                        availability_time_utc=detected.availability_time_utc,  # type: ignore[attr-defined]
                    )
                )

    return expected, actual


def evaluate_scanner(
    replay_result: ScannerReplayResult,
    reviewed_cases: tuple[ReviewedScannerCase, ...],
) -> ScannerBacktestReport:
    start = time.perf_counter()

    poi_analysis = replay_result.final_snapshot.poi_analysis
    btmm_analysis = replay_result.final_snapshot.btmm_analysis
    minimum_price_tick = replay_result.minimum_price_tick

    poi_reports = [
        build_poi_validation_report(case, poi_analysis, minimum_price_tick)
        for case in reviewed_cases
    ]
    btmm_reports = [
        build_btmm_validation_report(case, btmm_analysis) for case in reviewed_cases
    ]

    expected_events: list[_ReviewedLifecycleEvent] = []
    actual_events: list[_ReviewedLifecycleEvent] = []
    for case, poi_report in zip(reviewed_cases, poi_reports, strict=True):
        case_expected, case_actual = _build_reviewed_poi_lifecycle_events(
            case, poi_report, poi_analysis
        )
        expected_events.extend(case_expected)
        actual_events.extend(case_actual)
    for case, btmm_report in zip(reviewed_cases, btmm_reports, strict=True):
        case_expected, case_actual = _build_reviewed_btmm_lifecycle_events(
            case, btmm_report, btmm_analysis
        )
        expected_events.extend(case_expected)
        actual_events.extend(case_actual)

    lifecycle_report = build_lifecycle_validation_report(
        tuple(expected_events), tuple(actual_events)
    )

    combined_poi_report = _combine_poi_reports(poi_reports)
    combined_btmm_report = _combine_btmm_reports(btmm_reports)

    runtime_seconds = Decimal(str(time.perf_counter() - start))
    health_report = build_scanner_health_report(replay_result, runtime_seconds)

    return ScannerBacktestReport(
        poi_validation_report=combined_poi_report,
        btmm_validation_report=combined_btmm_report,
        lifecycle_validation_report=lifecycle_report,
        health_report=health_report,
        replay_result=replay_result,
    )
