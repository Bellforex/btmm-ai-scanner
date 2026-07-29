from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.enums import EqualLevelType, SupportResistanceType
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.reference_zones import detect_reference_zones

_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _swing_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _support_resistance_zone(
    zone_type: SupportResistanceType, zone_top: str, zone_bottom: str
) -> SupportResistanceZone:
    confirmation_time = _BASE_TIME + timedelta(minutes=10)
    return SupportResistanceZone(
        record_id=_swing_id(1),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        zone_type=zone_type,
        origin_swing_record_id=_swing_id(2),
        creator_reference_atr=Decimal("1.0"),
        zone_depth=Decimal(zone_top) - Decimal(zone_bottom),
        zone_top=Decimal(zone_top),
        zone_bottom=Decimal(zone_bottom),
        qualifying_touch_swing_record_ids=(_swing_id(3),),
        confirmation_candle_id=_swing_id(4),
        confirmation_time_utc=confirmation_time,
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def _equal_level_cluster(
    cluster_type: EqualLevelType, zone_top: str, zone_bottom: str
) -> EqualLevelCluster:
    confirmation_time = _BASE_TIME + timedelta(minutes=10)
    return EqualLevelCluster(
        record_id=_swing_id(5),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        cluster_type=cluster_type,
        component_swing_record_ids=(_swing_id(6), _swing_id(7)),
        cluster_spread=Decimal("0.05"),
        equality_tolerance=Decimal("0.10"),
        reference_atr=Decimal("1.0"),
        zone_bottom=Decimal(zone_bottom),
        zone_top=Decimal(zone_top),
        representative_price=(Decimal(zone_top) + Decimal(zone_bottom)) / Decimal("2"),
        confirmation_time_utc=confirmation_time,
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def test_support_poi_inherits_zone_boundaries_from_support_resistance_zone() -> None:
    zone = _support_resistance_zone(SupportResistanceType.SUPPORT, "101", "100")

    (candidate,) = detect_reference_zones((zone,), ())

    assert candidate.poi_type == PoiType.SUPPORT_ZONE
    assert candidate.zone_top == zone.zone_top
    assert candidate.zone_bottom == zone.zone_bottom
    assert candidate.availability_time_utc == zone.availability_time_utc


def test_resistance_poi_inherits_zone_boundaries_from_support_resistance_zone() -> None:
    zone = _support_resistance_zone(SupportResistanceType.RESISTANCE, "105", "104")

    (candidate,) = detect_reference_zones((zone,), ())

    assert candidate.poi_type == PoiType.RESISTANCE_ZONE
    assert candidate.zone_top == zone.zone_top
    assert candidate.zone_bottom == zone.zone_bottom
    assert candidate.availability_time_utc == zone.availability_time_utc


def test_support_break_candidate_and_close_breach_candidate_coexist_independently() -> (
    None
):
    zone = _support_resistance_zone(SupportResistanceType.SUPPORT, "101", "100")

    (candidate,) = detect_reference_zones((zone,), ())

    assert "support_break_candidate" not in PoiObservation.model_fields
    assert candidate.source_zone_record_id == zone.record_id


def test_equal_highs_and_equal_lows_poi_inherit_zone_boundaries_from_equal_level_cluster() -> (
    None
):
    equal_high = _equal_level_cluster(EqualLevelType.EQUAL_HIGH, "101", "100.9")
    equal_low = _equal_level_cluster(EqualLevelType.EQUAL_LOW, "99.1", "99")

    high_candidate, low_candidate = detect_reference_zones((), (equal_high, equal_low))

    assert high_candidate.zone_top == equal_high.zone_top
    assert high_candidate.zone_bottom == equal_high.zone_bottom
    assert low_candidate.zone_top == equal_low.zone_top
    assert low_candidate.zone_bottom == equal_low.zone_bottom


def test_equal_highs_and_equal_lows_never_emit_lifecycle_transitions() -> None:
    from btmm_ai_scanner.poi.enums import NOT_APPLICABLE_LIFECYCLE_POI_TYPES

    assert PoiType.EQUAL_HIGHS_LIQUIDITY in NOT_APPLICABLE_LIFECYCLE_POI_TYPES
    assert PoiType.EQUAL_LOWS_LIQUIDITY in NOT_APPLICABLE_LIFECYCLE_POI_TYPES


def test_support_and_resistance_map_to_bullish_and_bearish_direction_respectively() -> (
    None
):
    support = _support_resistance_zone(SupportResistanceType.SUPPORT, "101", "100")
    resistance = _support_resistance_zone(
        SupportResistanceType.RESISTANCE, "105", "104"
    )

    (support_candidate,) = detect_reference_zones((support,), ())
    (resistance_candidate,) = detect_reference_zones((resistance,), ())

    assert support_candidate.direction == PoiDirection.BULLISH
    assert resistance_candidate.direction == PoiDirection.BEARISH


def test_equal_highs_and_equal_lows_map_to_bearish_and_bullish_direction_respectively() -> (
    None
):
    equal_high = _equal_level_cluster(EqualLevelType.EQUAL_HIGH, "101", "100.9")
    equal_low = _equal_level_cluster(EqualLevelType.EQUAL_LOW, "99.1", "99")

    high_candidate, low_candidate = detect_reference_zones((), (equal_high, equal_low))

    assert high_candidate.direction == PoiDirection.BEARISH
    assert low_candidate.direction == PoiDirection.BULLISH
