from decimal import Decimal

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.scanner.enums import LabelMatchStatus
from btmm_ai_scanner.scanner.labels import ReviewedScannerCase
from btmm_ai_scanner.scanner.matching import LabelMatch, match_btmm_detections


class BtmmValidationReport(ContractModel):
    expected_count: int
    detected_count: int
    matched_count: int
    missed_count: int
    unexpected_count: int
    unreviewed_count: int
    mean_candidate_timing_delay_seconds: Decimal | None
    mean_forming_timing_delay_seconds: Decimal | None
    mean_confirmation_or_cancellation_timing_delay_seconds: Decimal | None
    interaction_agreement_count: int
    reaction_agreement_count: int
    final_state_agreement_count: int
    matches: tuple[LabelMatch, ...]


def _mean(values: list[Decimal]) -> Decimal | None:
    if len(values) == 0:
        return None
    return sum(values, Decimal("0")) / Decimal(len(values))


def build_btmm_validation_report(
    case: ReviewedScannerCase, btmm_analysis: BtmmAnalysis
) -> BtmmValidationReport:
    detections = tuple(
        observation
        for observation in btmm_analysis.btmm_observations
        if observation.symbol == case.symbol
    )
    matches = match_btmm_detections(
        case.symbol, case.expected_btmm_labels, detections, case.btmm_labels_complete
    )

    matched = [m for m in matches if m.status == LabelMatchStatus.MATCHED]
    missed_count = sum(1 for m in matches if m.status == LabelMatchStatus.MISSED)
    unexpected_count = sum(
        1 for m in matches if m.status == LabelMatchStatus.UNEXPECTED
    )
    unreviewed_count = sum(
        1 for m in matches if m.status == LabelMatchStatus.UNREVIEWED
    )

    observations_by_id = {
        observation.record_id: observation for observation in detections
    }
    states_by_setup_id = {
        state.btmm_setup_record_id: state for state in btmm_analysis.current_btmm_states
    }
    labels_by_id = {label.label_id: label for label in case.expected_btmm_labels}

    candidate_delays: list[Decimal] = []
    forming_delays: list[Decimal] = []
    confirmation_or_cancellation_delays: list[Decimal] = []
    interaction_agreement_count = 0
    reaction_agreement_count = 0
    final_state_agreement_count = 0

    for match in matched:
        assert match.expected_label_id is not None
        assert match.detected_record_id is not None
        label = labels_by_id[match.expected_label_id]
        observation = observations_by_id[match.detected_record_id]
        state = states_by_setup_id.get(match.detected_record_id)

        if label.expected_candidate_availability_time_utc is not None:
            candidate_delays.append(
                abs(
                    Decimal(
                        (
                            observation.availability_time_utc
                            - label.expected_candidate_availability_time_utc
                        ).total_seconds()
                    )
                )
            )

        if state is None:
            continue

        if label.expected_forming_availability_time_utc is not None:
            forming_delays.append(
                abs(
                    Decimal(
                        (
                            state.availability_time_utc
                            - label.expected_forming_availability_time_utc
                        ).total_seconds()
                    )
                )
            )

        if label.expected_confirmation_or_cancellation_time_utc is not None:
            confirmation_or_cancellation_delays.append(
                abs(
                    Decimal(
                        (
                            state.availability_time_utc
                            - label.expected_confirmation_or_cancellation_time_utc
                        ).total_seconds()
                    )
                )
            )

        if (
            label.expected_interaction_classification is not None
            and state.interaction_class == label.expected_interaction_classification
        ):
            interaction_agreement_count += 1

        if (
            label.expected_reaction_classification is not None
            and state.reaction_classification == label.expected_reaction_classification
        ):
            reaction_agreement_count += 1

        if state.primary_state == label.expected_final_primary_state:
            final_state_agreement_count += 1

    return BtmmValidationReport(
        expected_count=len(case.expected_btmm_labels),
        detected_count=len(detections),
        matched_count=len(matched),
        missed_count=missed_count,
        unexpected_count=unexpected_count,
        unreviewed_count=unreviewed_count,
        mean_candidate_timing_delay_seconds=_mean(candidate_delays),
        mean_forming_timing_delay_seconds=_mean(forming_delays),
        mean_confirmation_or_cancellation_timing_delay_seconds=_mean(
            confirmation_or_cancellation_delays
        ),
        interaction_agreement_count=interaction_agreement_count,
        reaction_agreement_count=reaction_agreement_count,
        final_state_agreement_count=final_state_agreement_count,
        matches=matches,
    )
