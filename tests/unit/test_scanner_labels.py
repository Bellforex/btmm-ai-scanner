import inspect
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.btmm.enums import BtmmDirection, BtmmLifecycleStatus
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.labels import (
    ExpectedBtmmLabel,
    ExpectedPoiLabel,
    InvalidReviewedLabelError,
    ReviewedScannerCase,
    validate_reviewed_scanner_case,
)
from btmm_ai_scanner.scanner.replay import run_scanner_replay

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _poi_label(
    label_id: str = "poi-1",
    zone_top: str = "101",
    zone_bottom: str = "100",
) -> ExpectedPoiLabel:
    return ExpectedPoiLabel(
        label_id=label_id,
        expected_poi_type=PoiType.BULLISH_ENGULFING,
        expected_direction=PoiDirection.BULLISH,
        expected_timeframe=Timeframe.M1,
        expected_zone_top=Decimal(zone_top),
        expected_zone_bottom=Decimal(zone_bottom),
        earliest_valid_availability_time_utc=_BASE_TIME,
        latest_acceptable_availability_time_utc=_BASE_TIME + timedelta(hours=1),
        expected_final_lifecycle_status=None,
    )


def _btmm_label(
    label_id: str = "btmm-1", source_poi_label_id: str = "poi-1"
) -> ExpectedBtmmLabel:
    return ExpectedBtmmLabel(
        label_id=label_id,
        source_poi_label_id=source_poi_label_id,
        expected_direction=BtmmDirection.BULLISH_BTMM,
        expected_timeframe=Timeframe.M1,
        expected_candidate_availability_time_utc=_BASE_TIME,
        expected_forming_availability_time_utc=None,
        expected_confirmation_or_cancellation_time_utc=None,
        expected_final_primary_state=BtmmLifecycleStatus.BTMM_CANDIDATE,
        expected_reaction_classification=None,
        expected_interaction_classification=None,
    )


def _case(**overrides: object) -> ReviewedScannerCase:
    fields: dict[str, object] = {
        "case_id": "case-1",
        "dataset_version": "v1",
        "reviewer_id": "reviewer-42",
        "review_version": "1",
        "symbol": InternalSymbol.XAUUSD,
        "evaluation_start_time_utc": _BASE_TIME,
        "evaluation_end_time_utc": _BASE_TIME + timedelta(days=1),
        "required_timeframes": (Timeframe.M1, Timeframe.M5, Timeframe.M15),
        "expected_poi_labels": (_poi_label(),),
        "expected_btmm_labels": (_btmm_label(),),
        "poi_labels_complete": True,
        "btmm_labels_complete": True,
        "notes": "",
    }
    fields.update(overrides)
    return ReviewedScannerCase(**fields)  # type: ignore[arg-type]


def test_reviewed_scanner_case_requires_valid_fields() -> None:
    case = _case()
    validate_reviewed_scanner_case(case)
    assert case.case_id == "case-1"


def test_dataset_version_and_case_id_are_immutable_identifiers() -> None:
    case = _case()
    with pytest.raises(ValidationError):
        case.case_id = "other"
    with pytest.raises(ValidationError):
        case.dataset_version = "v2"


def test_reviewer_id_is_a_stable_pseudonymous_identifier() -> None:
    case = _case(reviewer_id="reviewer-42")
    assert case.reviewer_id == "reviewer-42"
    assert "reviewer_name" not in ReviewedScannerCase.model_fields
    assert "reviewer_email" not in ReviewedScannerCase.model_fields


def test_poi_and_btmm_completeness_flags_are_independent() -> None:
    case = _case(poi_labels_complete=True, btmm_labels_complete=False)
    assert case.poi_labels_complete is True
    assert case.btmm_labels_complete is False


def test_expected_poi_label_validates_zone_geometry() -> None:
    case = _case(expected_poi_labels=(_poi_label(zone_top="99", zone_bottom="100"),))
    with pytest.raises(InvalidReviewedLabelError):
        validate_reviewed_scanner_case(case)


def test_expected_btmm_label_references_valid_source_poi_label() -> None:
    case = _case(
        expected_btmm_labels=(_btmm_label(source_poi_label_id="does-not-exist"),)
    )
    with pytest.raises(InvalidReviewedLabelError):
        validate_reviewed_scanner_case(case)


def test_invalid_evaluation_time_window_rejected() -> None:
    case = _case(
        evaluation_start_time_utc=_BASE_TIME + timedelta(days=1),
        evaluation_end_time_utc=_BASE_TIME,
    )
    with pytest.raises(InvalidReviewedLabelError):
        validate_reviewed_scanner_case(case)


def test_zero_height_expected_poi_zone_rejected() -> None:
    case = _case(expected_poi_labels=(_poi_label(zone_top="100", zone_bottom="100"),))
    with pytest.raises(InvalidReviewedLabelError):
        validate_reviewed_scanner_case(case)


def test_future_label_availability_never_influences_earlier_evaluation() -> None:
    assert "reviewed_cases" not in inspect.signature(scan_market).parameters
    assert "reviewed_cases" not in inspect.signature(run_scanner_replay).parameters


def test_reviewed_labels_are_not_accepted_by_scan_market_or_run_scanner_replay() -> (
    None
):
    scan_market_params = set(inspect.signature(scan_market).parameters)
    replay_params = set(inspect.signature(run_scanner_replay).parameters)
    assert scan_market_params.isdisjoint({"reviewed_cases", "expected_poi_labels"})
    assert replay_params.isdisjoint({"reviewed_cases", "expected_poi_labels"})
