from decimal import Decimal

from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.scanner.enums import LabelMatchStatus
from btmm_ai_scanner.scanner.labels import ReviewedScannerCase
from btmm_ai_scanner.scanner.matching import LabelMatch, match_poi_detections


class PoiValidationReport(ContractModel):
    expected_count: int
    detected_count: int
    matched_count: int
    missed_count: int
    unexpected_count: int
    unreviewed_count: int
    type_match_count: int
    direction_match_count: int
    mean_boundary_error_ticks: Decimal | None
    mean_overlap_ratio: Decimal | None
    mean_confirmation_delay_seconds: Decimal | None
    lifecycle_agreement_count: int
    final_state_agreement_count: int
    matches: tuple[LabelMatch, ...]


def _mean(values: list[Decimal]) -> Decimal | None:
    if len(values) == 0:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def build_poi_validation_report(
    case: ReviewedScannerCase, poi_analysis: PoiAnalysis
) -> PoiValidationReport:
    detections = tuple(
        observation
        for observation in poi_analysis.poi_observations
        if observation.symbol == case.symbol
    )
    matches = match_poi_detections(
        case.symbol, case.expected_poi_labels, detections, case.poi_labels_complete
    )

    matched = [m for m in matches if m.status == LabelMatchStatus.MATCHED]
    missed_count = sum(1 for m in matches if m.status == LabelMatchStatus.MISSED)
    unexpected_count = sum(
        1 for m in matches if m.status == LabelMatchStatus.UNEXPECTED
    )
    unreviewed_count = sum(
        1 for m in matches if m.status == LabelMatchStatus.UNREVIEWED
    )

    boundary_errors = [
        m.boundary_error_ticks for m in matched if m.boundary_error_ticks is not None
    ]
    overlap_ratios = [m.overlap_ratio for m in matched if m.overlap_ratio is not None]
    delays = [m.availability_delay for m in matched if m.availability_delay is not None]

    states_by_poi_record_id = {
        state.poi_record_id: state for state in poi_analysis.current_poi_states
    }
    labels_by_id = {label.label_id: label for label in case.expected_poi_labels}

    final_state_agreement_count = 0
    for match in matched:
        assert match.expected_label_id is not None
        assert match.detected_record_id is not None
        label = labels_by_id[match.expected_label_id]
        if label.expected_final_lifecycle_status is None:
            continue
        state = states_by_poi_record_id.get(match.detected_record_id)
        if (
            state is not None
            and state.poi_lifecycle_status == label.expected_final_lifecycle_status
        ):
            final_state_agreement_count += 1

    # PoiObservation/CurrentPoiState carry a single terminal lifecycle-status
    # concept; a richer per-transition-sequence reviewed label would be needed
    # to distinguish "lifecycle agreement" from "final-state agreement".
    lifecycle_agreement_count = final_state_agreement_count

    return PoiValidationReport(
        expected_count=len(case.expected_poi_labels),
        detected_count=len(detections),
        matched_count=len(matched),
        missed_count=missed_count,
        unexpected_count=unexpected_count,
        unreviewed_count=unreviewed_count,
        type_match_count=len(matched),
        direction_match_count=len(matched),
        mean_boundary_error_ticks=_mean(boundary_errors),
        mean_overlap_ratio=_mean(overlap_ratios),
        mean_confirmation_delay_seconds=_mean(delays),
        lifecycle_agreement_count=lifecycle_agreement_count,
        final_state_agreement_count=final_state_agreement_count,
        matches=matches,
    )
