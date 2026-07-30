from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiType,
)
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.labels import ExpectedPoiLabel, ReviewedScannerCase
from btmm_ai_scanner.scanner.poi_validation import build_poi_validation_report

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_FINGERPRINT = "a" * 64
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")


def _observation(
    index: int,
    zone_top: str = "101",
    zone_bottom: str = "100",
    availability_offset_minutes: int = 5,
) -> PoiObservation:
    availability = _BASE_TIME + timedelta(minutes=availability_offset_minutes)
    return PoiObservation(
        record_id=UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M1,
        effective_timeframe=Timeframe.M1,
        family=PoiFamily.PRICE_ACTION,
        poi_type=PoiType.BULLISH_ENGULFING,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal(zone_top),
        zone_bottom=Decimal(zone_bottom),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=availability,
        confirmation_time_utc=availability,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _current_state(
    observation: PoiObservation,
    status: PoiLifecycleStatus = PoiLifecycleStatus.NO_BREACH,
) -> CurrentPoiState:
    return CurrentPoiState(
        record_id=UUID(f"0193f450-2222-7abc-8def-{1:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=observation.symbol,
        timeframe=observation.source_timeframe,
        poi_record_id=observation.record_id,
        poi_type=observation.poi_type,
        direction=observation.direction,
        poi_lifecycle_status=status,
        freshness_status=PoiFreshnessStatus.FRESH,
        tap_count=0,
        tap_classification=None,
        age_start_time_utc=observation.availability_time_utc,
        age_in_confirmed_bars=0,
        elapsed_time_since_availability=timedelta(0),
        latest_lifecycle_transition_id=None,
        availability_time_utc=observation.availability_time_utc,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _poi_analysis(
    *observations: PoiObservation, states: tuple[CurrentPoiState, ...] = ()
) -> PoiAnalysis:
    return PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M1,),
        analyzed_candle_count_by_timeframe=(2,),
        poi_observations=observations,
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=states,
    )


def _label(
    label_id: str = "poi-1",
    zone_top: str = "101",
    zone_bottom: str = "100",
    expected_final_lifecycle_status: PoiLifecycleStatus | None = None,
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
        expected_final_lifecycle_status=expected_final_lifecycle_status,
    )


def _case(
    expected_poi_labels: tuple[ExpectedPoiLabel, ...], poi_labels_complete: bool = True
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
        expected_poi_labels=expected_poi_labels,
        expected_btmm_labels=(),
        poi_labels_complete=poi_labels_complete,
        btmm_labels_complete=True,
        notes="",
    )


def test_poi_validation_reports_expected_detected_and_matched_counts() -> None:
    observation = _observation(0)
    report = build_poi_validation_report(_case((_label(),)), _poi_analysis(observation))
    assert report.expected_count == 1
    assert report.detected_count == 1
    assert report.matched_count == 1


def test_poi_validation_reports_missed_and_unexpected_counts() -> None:
    report = build_poi_validation_report(_case((_label(),)), _poi_analysis())
    assert report.missed_count == 1
    assert report.unexpected_count == 0

    unexpected_observation = _observation(0, availability_offset_minutes=5)
    report_2 = build_poi_validation_report(
        _case((), poi_labels_complete=True), _poi_analysis(unexpected_observation)
    )
    assert report_2.unexpected_count == 1


def test_poi_validation_distinguishes_unreviewed_from_unexpected_detections() -> None:
    observation = _observation(0)
    complete = build_poi_validation_report(
        _case((), poi_labels_complete=True), _poi_analysis(observation)
    )
    incomplete = build_poi_validation_report(
        _case((), poi_labels_complete=False), _poi_analysis(observation)
    )
    assert complete.unexpected_count == 1
    assert complete.unreviewed_count == 0
    assert incomplete.unexpected_count == 0
    assert incomplete.unreviewed_count == 1


def test_poi_validation_reports_exact_type_and_direction_match_counts() -> None:
    observation = _observation(0)
    report = build_poi_validation_report(_case((_label(),)), _poi_analysis(observation))
    assert report.type_match_count == 1
    assert report.direction_match_count == 1


def test_poi_validation_computes_boundary_error_in_ticks() -> None:
    observation = _observation(0, zone_top="101.5", zone_bottom="100")
    report = build_poi_validation_report(
        _case((_label(zone_top="101", zone_bottom="100"),)), _poi_analysis(observation)
    )
    assert report.mean_boundary_error_ticks == Decimal("0.5")


def test_poi_validation_computes_zone_intersection_and_union() -> None:
    from btmm_ai_scanner.scanner.matching import zone_overlap_ratio

    intersection_ratio = zone_overlap_ratio(
        Decimal("101"), Decimal("100"), Decimal("100.5"), Decimal("99.5")
    )
    assert intersection_ratio == Decimal("0.5") / Decimal("1.5")


def test_poi_validation_computes_zone_overlap_ratio() -> None:
    observation = _observation(0, zone_top="101", zone_bottom="100")
    report = build_poi_validation_report(
        _case((_label(zone_top="101", zone_bottom="100"),)), _poi_analysis(observation)
    )
    assert report.mean_overlap_ratio == Decimal("1")


def test_poi_validation_computes_confirmation_timing_delay() -> None:
    observation = _observation(0, availability_offset_minutes=10)
    report = build_poi_validation_report(_case((_label(),)), _poi_analysis(observation))
    assert report.mean_confirmation_delay_seconds == Decimal("600")


def test_poi_validation_denominator_zero_reports_none_not_zero() -> None:
    report = build_poi_validation_report(_case(()), _poi_analysis())
    assert report.mean_boundary_error_ticks is None
    assert report.mean_overlap_ratio is None
    assert report.mean_confirmation_delay_seconds is None


def test_poi_validation_reports_lifecycle_and_final_state_agreement() -> None:
    observation = _observation(0)
    state = _current_state(observation, PoiLifecycleStatus.NO_BREACH)
    report = build_poi_validation_report(
        _case((_label(expected_final_lifecycle_status=PoiLifecycleStatus.NO_BREACH),)),
        _poi_analysis(observation, states=(state,)),
    )
    assert report.final_state_agreement_count == 1
    assert report.lifecycle_agreement_count == 1
