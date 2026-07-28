from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import SwingRelationshipLabel
from btmm_ai_scanner.structure.relationships import detect_swing_relationships

_PROVENANCE_ID = UUID("0193f410-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = StructureConfiguration()


def _record_id(index: int) -> UUID:
    return UUID(f"0193f410-1234-7abc-8def-{index:012x}")


def _swing(
    index: int,
    swing_type: SwingType,
    price: str,
    pivot_bar_index: int,
    pivot_minutes_offset: int,
    confirmation_minutes_offset: int,
    reference_atr: str = "1.0",
) -> ConfirmedSwing:
    pivot_time = _BASE_TIME + timedelta(minutes=pivot_minutes_offset)
    confirmation_time = _BASE_TIME + timedelta(minutes=confirmation_minutes_offset)
    return ConfirmedSwing(
        record_id=_record_id(index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_bar_index=pivot_bar_index,
        pivot_candle_record_ids=(_record_id(index),),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=1),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=_record_id(index + 1000),
        pivot_reference_atr=Decimal(reference_atr),
        pivot_tie_tolerance=Decimal("0.02"),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def test_swing_relationship_confirms_higher_high() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0, 0, 1),
        _swing(2, SwingType.SWING_HIGH, "101.00", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.HIGHER_HIGH


def test_swing_relationship_confirms_lower_high() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0, 0, 1),
        _swing(2, SwingType.SWING_HIGH, "99.00", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.LOWER_HIGH


def test_swing_relationship_confirms_higher_low() -> None:
    swings = (
        _swing(1, SwingType.SWING_LOW, "90.00", 0, 0, 1),
        _swing(2, SwingType.SWING_LOW, "91.00", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.HIGHER_LOW


def test_swing_relationship_confirms_lower_low() -> None:
    swings = (
        _swing(1, SwingType.SWING_LOW, "90.00", 0, 0, 1),
        _swing(2, SwingType.SWING_LOW, "89.00", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.LOWER_LOW


def test_swing_relationship_confirms_equal_high_within_tolerance() -> None:
    swings = (
        _swing(1, SwingType.SWING_HIGH, "100.00", 0, 0, 1),
        _swing(2, SwingType.SWING_HIGH, "100.05", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.EQUAL_HIGH


def test_swing_relationship_confirms_equal_low_within_tolerance() -> None:
    swings = (
        _swing(1, SwingType.SWING_LOW, "90.00", 0, 0, 1),
        _swing(2, SwingType.SWING_LOW, "90.05", 10, 10, 11),
    )
    results = detect_swing_relationships(swings, _CONFIG)
    assert len(results) == 1
    assert results[0].label == SwingRelationshipLabel.EQUAL_LOW


def test_swing_relationships_use_source_chronology_not_confirmation_order() -> None:
    # Swing A pivots first (bar index 0) but confirms LAST (minute 50).
    # Swing B pivots second (bar index 10) but confirms FIRST (minute 11).
    swing_a = _swing(1, SwingType.SWING_HIGH, "100.00", 0, 0, 50)
    swing_b = _swing(2, SwingType.SWING_HIGH, "105.00", 10, 10, 11)
    # Supplied in canonical source-chronology order (by pivot_bar_index): A, B.
    swings = (swing_a, swing_b)

    results = detect_swing_relationships(swings, _CONFIG)

    assert len(results) == 1
    relationship = results[0]
    # B (source-later) is compared against A (source-earlier), never the reverse,
    # regardless of which one confirmed first.
    assert relationship.current_swing_record_id == swing_b.record_id
    assert relationship.predecessor_swing_record_id == swing_a.record_id
    assert relationship.label == SwingRelationshipLabel.HIGHER_HIGH
    # Availability is the max of both, not simply B's own (earlier) confirmation.
    assert relationship.availability_time_utc == max(
        swing_a.availability_time_utc, swing_b.availability_time_utc
    )
    assert relationship.availability_time_utc == swing_a.availability_time_utc


def test_swing_relationship_waits_for_unavailable_source_predecessor() -> None:
    # A smaller prefix in which the true source-chronology predecessor has not
    # yet confirmed: only the later HIGH swing is present.
    later_high = _swing(2, SwingType.SWING_HIGH, "105.00", 10, 10, 11)
    small_prefix = (later_high,)
    small_results = detect_swing_relationships(small_prefix, _CONFIG)
    assert small_results == ()

    # A larger, more complete prefix in which the true predecessor has since
    # confirmed and is now supplied, inserted at its correct source position.
    earlier_high = _swing(1, SwingType.SWING_HIGH, "100.00", 0, 0, 5)
    large_prefix = (earlier_high, later_high)
    large_results = detect_swing_relationships(large_prefix, _CONFIG)

    assert len(large_results) == 1
    assert large_results[0].current_swing_record_id == later_high.record_id
    assert large_results[0].predecessor_swing_record_id == earlier_high.record_id
