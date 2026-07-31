from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.enums import LabelMatchStatus
from btmm_ai_scanner.scanner.labels import ExpectedPoiLabel, InvalidReviewedLabelError
from btmm_ai_scanner.scanner.matching import match_poi_detections, zone_overlap_ratio

_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_FINGERPRINT = "a" * 64
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_MINIMUM_PRICE_TICK = Decimal("0.01")


def _label(
    label_id: str = "poi-1",
    zone_top: str = "101",
    zone_bottom: str = "100",
    direction: PoiDirection = PoiDirection.BULLISH,
    timeframe: Timeframe = Timeframe.M1,
) -> ExpectedPoiLabel:
    return ExpectedPoiLabel(
        label_id=label_id,
        expected_poi_type=PoiType.BULLISH_ENGULFING,
        expected_direction=direction,
        expected_timeframe=timeframe,
        expected_zone_top=Decimal(zone_top),
        expected_zone_bottom=Decimal(zone_bottom),
        earliest_valid_availability_time_utc=_BASE_TIME,
        latest_acceptable_availability_time_utc=_BASE_TIME + timedelta(hours=1),
        expected_final_lifecycle_status=None,
    )


def _detection(
    index: int,
    zone_top: str = "101",
    zone_bottom: str = "100",
    direction: PoiDirection = PoiDirection.BULLISH,
    timeframe: Timeframe = Timeframe.M1,
    availability_offset_minutes: int = 5,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    poi_type: PoiType = PoiType.BULLISH_ENGULFING,
) -> PoiObservation:
    availability = _BASE_TIME + timedelta(minutes=availability_offset_minutes)
    return PoiObservation(
        record_id=UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
        content_fingerprint=_FINGERPRINT,
        symbol=symbol,
        source_timeframe=timeframe,
        effective_timeframe=timeframe,
        family=PoiFamily.PRICE_ACTION,
        poi_type=poi_type,
        direction=direction,
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


def test_matching_requires_exact_symbol_timeframe_and_direction() -> None:
    label = _label()
    wrong_timeframe = _detection(0, timeframe=Timeframe.M5)
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (label,), (wrong_timeframe,), True, _MINIMUM_PRICE_TICK
    )
    statuses = {m.status for m in matches}
    assert LabelMatchStatus.MATCHED not in statuses


def test_matching_computes_exact_zone_overlap_ratio() -> None:
    ratio = zone_overlap_ratio(
        Decimal("101"), Decimal("100"), Decimal("101"), Decimal("100")
    )
    assert ratio == Decimal("1")
    partial = zone_overlap_ratio(
        Decimal("102"), Decimal("100"), Decimal("101"), Decimal("99")
    )
    assert partial == Decimal("1") / Decimal("3")
    zero_height_mismatch = zone_overlap_ratio(
        Decimal("100"), Decimal("100"), Decimal("101"), Decimal("101")
    )
    assert zero_height_mismatch == Decimal("0")


def test_matching_requires_availability_inside_expected_interval() -> None:
    label = _label()
    too_late = _detection(0, availability_offset_minutes=1000)
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (label,), (too_late,), True, _MINIMUM_PRICE_TICK
    )
    assert all(m.status != LabelMatchStatus.MATCHED for m in matches)


def test_matching_tie_break_order_is_deterministic() -> None:
    label = _label()
    detection_a = _detection(0, availability_offset_minutes=5)
    detection_b = _detection(1, availability_offset_minutes=5)
    matches_1 = match_poi_detections(
        InternalSymbol.XAUUSD,
        (label,),
        (detection_a, detection_b),
        True,
        _MINIMUM_PRICE_TICK,
    )
    matches_2 = match_poi_detections(
        InternalSymbol.XAUUSD,
        (label,),
        (detection_b, detection_a),
        True,
        _MINIMUM_PRICE_TICK,
    )
    matched_1 = next(m for m in matches_1 if m.status == LabelMatchStatus.MATCHED)
    matched_2 = next(m for m in matches_2 if m.status == LabelMatchStatus.MATCHED)
    assert matched_1.detected_record_id == matched_2.detected_record_id


def test_matching_never_produces_an_ambiguous_result() -> None:
    label = _label()
    detections = tuple(_detection(i, availability_offset_minutes=5) for i in range(5))
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (label,), detections, True, _MINIMUM_PRICE_TICK
    )
    matched = [m for m in matches if m.status == LabelMatchStatus.MATCHED]
    assert len(matched) == 1


def test_unmatched_expected_label_reported_as_missed() -> None:
    label = _label()
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (label,), (), True, _MINIMUM_PRICE_TICK
    )
    assert len(matches) == 1
    assert matches[0].status == LabelMatchStatus.MISSED
    assert matches[0].expected_label_id == "poi-1"


def test_unmatched_detection_reported_as_unexpected_when_case_complete() -> None:
    detection = _detection(0, availability_offset_minutes=5)
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (), (detection,), True, _MINIMUM_PRICE_TICK
    )
    assert len(matches) == 1
    assert matches[0].status == LabelMatchStatus.UNEXPECTED


def test_unmatched_detection_reported_as_unreviewed_when_case_incomplete() -> None:
    detection = _detection(0, availability_offset_minutes=5)
    matches = match_poi_detections(
        InternalSymbol.XAUUSD, (), (detection,), False, _MINIMUM_PRICE_TICK
    )
    assert len(matches) == 1
    assert matches[0].status == LabelMatchStatus.UNREVIEWED


def test_duplicate_expected_label_ids_rejected() -> None:
    from btmm_ai_scanner.scanner.labels import (
        ReviewedScannerCase,
        validate_reviewed_scanner_case,
    )

    duplicate_labels = (_label(label_id="dup"), _label(label_id="dup"))
    case = ReviewedScannerCase(
        case_id="case-x",
        dataset_version="v1",
        reviewer_id="reviewer-1",
        review_version="1",
        symbol=InternalSymbol.XAUUSD,
        evaluation_start_time_utc=_BASE_TIME,
        evaluation_end_time_utc=_BASE_TIME + timedelta(days=1),
        required_timeframes=(Timeframe.M1,),
        expected_poi_labels=duplicate_labels,
        expected_btmm_labels=(),
        poi_labels_complete=True,
        btmm_labels_complete=True,
        notes="",
    )
    try:
        validate_reviewed_scanner_case(case)
        raised = False
    except InvalidReviewedLabelError:
        raised = True
    assert raised


def test_matching_result_independent_of_detection_registration_order() -> None:
    label = _label()
    detection_a = _detection(0, availability_offset_minutes=5)
    detection_b = _detection(1, availability_offset_minutes=6)
    forward = match_poi_detections(
        InternalSymbol.XAUUSD,
        (label,),
        (detection_a, detection_b),
        True,
        _MINIMUM_PRICE_TICK,
    )
    backward = match_poi_detections(
        InternalSymbol.XAUUSD,
        (label,),
        (detection_b, detection_a),
        True,
        _MINIMUM_PRICE_TICK,
    )
    assert sorted(m.status.value for m in forward) == sorted(
        m.status.value for m in backward
    )
