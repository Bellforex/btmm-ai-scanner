from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiOverlapRelationshipType,
    PoiType,
)
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.overlap import (
    classify_zone_relationship,
    compute_overlap_relationships,
    resolve_merges,
)

_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _observation(
    index: int,
    poi_type: PoiType,
    direction: PoiDirection,
    zone_top: str,
    zone_bottom: str,
    timeframe: Timeframe = Timeframe.M1,
) -> PoiObservation:
    return PoiObservation(
        record_id=_record_id(index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=timeframe,
        effective_timeframe=timeframe,
        family=PoiFamily.VOLUME,
        poi_type=poi_type,
        direction=direction,
        zone_top=Decimal(zone_top),
        zone_bottom=Decimal(zone_bottom),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=_BASE_TIME,
        confirmation_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def test_overlapping_zones_are_detected_via_strict_interval_intersection() -> None:
    result = classify_zone_relationship(
        Decimal("101"), Decimal("99"), Decimal("102"), Decimal("100")
    )
    assert result is not None
    assert result[0] == PoiOverlapRelationshipType.OVERLAPPING

    no_overlap = classify_zone_relationship(
        Decimal("100"), Decimal("99"), Decimal("102"), Decimal("101")
    )
    assert no_overlap is None


def test_boundary_touching_zones_are_not_classified_as_overlapping() -> None:
    result = classify_zone_relationship(
        Decimal("100"), Decimal("99"), Decimal("101"), Decimal("100")
    )
    assert result is not None
    assert result[0] == PoiOverlapRelationshipType.BOUNDARY_TOUCHING


def test_containment_is_classified_separately_from_overlap() -> None:
    contains = classify_zone_relationship(
        Decimal("105"), Decimal("95"), Decimal("101"), Decimal("99")
    )
    contained_by = classify_zone_relationship(
        Decimal("101"), Decimal("99"), Decimal("105"), Decimal("95")
    )

    assert contains is not None
    assert contains[0] == PoiOverlapRelationshipType.CONTAINS
    assert contained_by is not None
    assert contained_by[0] == PoiOverlapRelationshipType.CONTAINED_BY


def test_point_poi_overlaps_interval_when_price_is_inside_or_on_boundary() -> None:
    inside = classify_zone_relationship(
        Decimal("100"), Decimal("100"), Decimal("101"), Decimal("99")
    )
    on_boundary = classify_zone_relationship(
        Decimal("101"), Decimal("101"), Decimal("101"), Decimal("99")
    )
    outside = classify_zone_relationship(
        Decimal("105"), Decimal("105"), Decimal("101"), Decimal("99")
    )

    assert inside is not None
    assert inside[0] == PoiOverlapRelationshipType.CONTAINED_BY
    assert on_boundary is not None
    assert on_boundary[0] == PoiOverlapRelationshipType.CONTAINED_BY
    assert outside is None


def test_distinct_point_pois_do_not_overlap() -> None:
    same_point = classify_zone_relationship(
        Decimal("100"), Decimal("100"), Decimal("100"), Decimal("100")
    )
    different_points = classify_zone_relationship(
        Decimal("100"), Decimal("100"), Decimal("100.01"), Decimal("100.01")
    )

    assert same_point is not None
    assert different_points is None


def test_same_poi_type_cross_timeframe_overlap_merges_into_the_stronger_timeframe() -> (
    None
):
    weak = _observation(
        1, PoiType.BUY_ORDER_BLOCK, PoiDirection.BULLISH, "101", "99", Timeframe.M1
    )
    strong = _observation(
        2, PoiType.BUY_ORDER_BLOCK, PoiDirection.BULLISH, "102", "98", Timeframe.H4
    )

    merged_children, effective_timeframe = resolve_merges((weak, strong))

    assert merged_children[strong.record_id] == (weak.record_id,)
    assert effective_timeframe[weak.record_id] == Timeframe.H4
    assert weak.record_id not in merged_children


def test_cross_poi_type_or_opposing_direction_overlap_is_reported_but_never_merged() -> (
    None
):
    order_block = _observation(
        1, PoiType.BUY_ORDER_BLOCK, PoiDirection.BULLISH, "101", "99", Timeframe.M1
    )
    fvg = _observation(
        2, PoiType.BUY_FAIR_VALUE_GAP, PoiDirection.BULLISH, "102", "98", Timeframe.H4
    )

    merged_children, effective_timeframe = resolve_merges((order_block, fvg))
    relationships = compute_overlap_relationships((order_block, fvg), _BASE_TIME)

    assert merged_children == {}
    assert effective_timeframe == {}
    assert len(relationships) == 1
    assert relationships[0].relationship_type == PoiOverlapRelationshipType.CONTAINED_BY


def test_merged_child_poi_remains_independently_observable() -> None:
    weak = _observation(
        1, PoiType.BUY_ORDER_BLOCK, PoiDirection.BULLISH, "101", "99", Timeframe.M1
    )
    strong = _observation(
        2, PoiType.BUY_ORDER_BLOCK, PoiDirection.BULLISH, "102", "98", Timeframe.H4
    )

    merged_children, _effective = resolve_merges((weak, strong))

    assert weak.record_id in merged_children[strong.record_id]
    assert weak.zone_top == Decimal("101")
    assert weak.zone_bottom == Decimal("99")


def test_overlap_relationships_are_not_transitively_inferred() -> None:
    a = _observation(1, PoiType.SUPPORT_ZONE, PoiDirection.BULLISH, "101", "99")
    b = _observation(2, PoiType.RESISTANCE_ZONE, PoiDirection.BULLISH, "100.5", "98.5")
    c = _observation(3, PoiType.HAMMER, PoiDirection.BULLISH, "98.7", "97")

    relationships = compute_overlap_relationships((a, b, c), _BASE_TIME)
    pairs = {
        frozenset({str(r.poi_a_record_id), str(r.poi_b_record_id)})
        for r in relationships
    }

    assert frozenset({str(a.record_id), str(b.record_id)}) in pairs
    assert frozenset({str(b.record_id), str(c.record_id)}) in pairs
    assert frozenset({str(a.record_id), str(c.record_id)}) not in pairs
