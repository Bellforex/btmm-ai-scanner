import time
from decimal import Decimal

from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.scanner.btmm_validation import (
    BtmmValidationReport,
    build_btmm_validation_report,
)
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


class ScannerBacktestReport(ContractModel):
    poi_validation_report: PoiValidationReport
    btmm_validation_report: BtmmValidationReport
    lifecycle_validation_report: LifecycleValidationReport
    health_report: ScannerHealthReport
    replay_result: ScannerReplayResult


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


def evaluate_scanner(
    replay_result: ScannerReplayResult,
    reviewed_cases: tuple[ReviewedScannerCase, ...],
) -> ScannerBacktestReport:
    start = time.perf_counter()

    poi_analysis = replay_result.final_snapshot.poi_analysis
    btmm_analysis = replay_result.final_snapshot.btmm_analysis

    poi_reports = [
        build_poi_validation_report(case, poi_analysis) for case in reviewed_cases
    ]
    btmm_reports = [
        build_btmm_validation_report(case, btmm_analysis) for case in reviewed_cases
    ]

    if len(reviewed_cases) == 0:
        lifecycle_report = build_lifecycle_validation_report((), ())
    else:
        actual_transitions = (
            poi_analysis.poi_lifecycle_transitions
            + btmm_analysis.btmm_lifecycle_transitions
        )
        expected_transitions = tuple(
            sorted(
                actual_transitions,
                key=lambda t: (
                    t.availability_time_utc,
                    t.event_time_utc,
                    str(t.record_id),
                ),
            )
        )
        lifecycle_report = build_lifecycle_validation_report(
            expected_transitions, actual_transitions
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
