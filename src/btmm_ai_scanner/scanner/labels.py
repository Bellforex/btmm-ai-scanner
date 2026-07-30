from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.btmm.enums import (
    BtmmDirection,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmReactionClassification,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus, PoiType


class InvalidReviewedLabelError(ValueError):
    pass


class ExpectedPoiLabel(ContractModel):
    label_id: str
    expected_poi_type: PoiType
    expected_direction: PoiDirection
    expected_timeframe: Timeframe
    expected_zone_top: Decimal
    expected_zone_bottom: Decimal
    earliest_valid_availability_time_utc: datetime
    latest_acceptable_availability_time_utc: datetime
    expected_final_lifecycle_status: PoiLifecycleStatus | None


class ExpectedBtmmLabel(ContractModel):
    label_id: str
    source_poi_label_id: str
    expected_direction: BtmmDirection
    expected_timeframe: Timeframe
    expected_candidate_availability_time_utc: datetime | None
    expected_forming_availability_time_utc: datetime | None
    expected_confirmation_or_cancellation_time_utc: datetime | None
    expected_final_primary_state: BtmmLifecycleStatus
    expected_reaction_classification: BtmmReactionClassification | None
    expected_interaction_classification: BtmmInteractionClass | None


class ReviewedScannerCase(ContractModel):
    case_id: str
    dataset_version: str
    reviewer_id: str
    review_version: str
    symbol: InternalSymbol
    evaluation_start_time_utc: datetime
    evaluation_end_time_utc: datetime
    required_timeframes: tuple[Timeframe, ...]
    expected_poi_labels: tuple[ExpectedPoiLabel, ...]
    expected_btmm_labels: tuple[ExpectedBtmmLabel, ...]
    poi_labels_complete: bool
    btmm_labels_complete: bool
    notes: str


def validate_reviewed_scanner_case(case: ReviewedScannerCase) -> None:
    if case.evaluation_start_time_utc >= case.evaluation_end_time_utc:
        raise InvalidReviewedLabelError(
            "evaluation_start_time_utc must be strictly before evaluation_end_time_utc."
        )

    seen_poi_label_ids: set[str] = set()
    for poi_label in case.expected_poi_labels:
        if poi_label.label_id in seen_poi_label_ids:
            raise InvalidReviewedLabelError(
                f"duplicate ExpectedPoiLabel.label_id {poi_label.label_id!r} within"
                " one ReviewedScannerCase."
            )
        seen_poi_label_ids.add(poi_label.label_id)

        if poi_label.expected_zone_top <= poi_label.expected_zone_bottom:
            raise InvalidReviewedLabelError(
                f"ExpectedPoiLabel {poi_label.label_id!r} has expected_zone_top"
                f" ({poi_label.expected_zone_top}) <= expected_zone_bottom"
                f" ({poi_label.expected_zone_bottom}); a reviewed zone must have"
                " strictly positive height."
            )

        if (
            poi_label.earliest_valid_availability_time_utc
            > poi_label.latest_acceptable_availability_time_utc
        ):
            raise InvalidReviewedLabelError(
                f"ExpectedPoiLabel {poi_label.label_id!r} has"
                " earliest_valid_availability_time_utc after"
                " latest_acceptable_availability_time_utc."
            )

    seen_btmm_label_ids: set[str] = set()
    for btmm_label in case.expected_btmm_labels:
        if btmm_label.label_id in seen_btmm_label_ids:
            raise InvalidReviewedLabelError(
                f"duplicate ExpectedBtmmLabel.label_id {btmm_label.label_id!r}"
                " within one ReviewedScannerCase."
            )
        seen_btmm_label_ids.add(btmm_label.label_id)

        if btmm_label.source_poi_label_id not in seen_poi_label_ids:
            raise InvalidReviewedLabelError(
                f"ExpectedBtmmLabel {btmm_label.label_id!r} references"
                f" source_poi_label_id {btmm_label.source_poi_label_id!r}, which is"
                " not present in this case's own expected_poi_labels."
            )
