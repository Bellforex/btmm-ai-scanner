from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel, UUIDv7
from btmm_ai_scanner.poi.enums import PoiDirection, PoiOverlapRelationshipType, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation

_TIMEFRAME_STRENGTH_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}


class PoiOverlapRelationship(ContractModel):
    symbol: InternalSymbol
    direction: PoiDirection
    poi_a_record_id: UUIDv7
    poi_b_record_id: UUIDv7
    relationship_type: PoiOverlapRelationshipType
    overlap_top: Decimal
    overlap_bottom: Decimal
    evaluated_at_time_utc: datetime


def classify_zone_relationship(
    top_a: Decimal, bottom_a: Decimal, top_b: Decimal, bottom_b: Decimal
) -> tuple[PoiOverlapRelationshipType, Decimal, Decimal] | None:
    a_is_point = top_a == bottom_a
    b_is_point = top_b == bottom_b

    if a_is_point and b_is_point:
        if top_a == top_b:
            return PoiOverlapRelationshipType.OVERLAPPING, top_a, top_a
        return None

    if a_is_point and not b_is_point:
        if bottom_b <= top_a <= top_b:
            return PoiOverlapRelationshipType.CONTAINED_BY, top_a, top_a
        return None

    if b_is_point and not a_is_point:
        if bottom_a <= top_b <= top_a:
            return PoiOverlapRelationshipType.CONTAINS, top_b, top_b
        return None

    overlap_top = min(top_a, top_b)
    overlap_bottom = max(bottom_a, bottom_b)
    if overlap_top < overlap_bottom:
        return None
    if overlap_top == overlap_bottom:
        return (
            PoiOverlapRelationshipType.BOUNDARY_TOUCHING,
            overlap_top,
            overlap_bottom,
        )
    if bottom_a <= bottom_b and top_a >= top_b:
        return PoiOverlapRelationshipType.CONTAINS, overlap_top, overlap_bottom
    if bottom_b <= bottom_a and top_b >= top_a:
        return PoiOverlapRelationshipType.CONTAINED_BY, overlap_top, overlap_bottom
    return PoiOverlapRelationshipType.OVERLAPPING, overlap_top, overlap_bottom


def compute_overlap_relationships(
    observations: tuple[PoiObservation, ...],
    evaluated_at_time_utc: datetime,
) -> tuple[PoiOverlapRelationship, ...]:
    by_symbol_direction: dict[
        tuple[InternalSymbol, PoiDirection], list[PoiObservation]
    ] = defaultdict(list)
    for observation in observations:
        by_symbol_direction[(observation.symbol, observation.direction)].append(
            observation
        )

    results: list[PoiOverlapRelationship] = []
    for (symbol, direction), group in by_symbol_direction.items():
        ordered = sorted(group, key=lambda o: str(o.record_id))
        for index_a in range(len(ordered)):
            for index_b in range(index_a + 1, len(ordered)):
                obs_a = ordered[index_a]
                obs_b = ordered[index_b]
                classification = classify_zone_relationship(
                    obs_a.zone_top, obs_a.zone_bottom, obs_b.zone_top, obs_b.zone_bottom
                )
                if classification is None:
                    continue
                relationship_type, overlap_top, overlap_bottom = classification
                if relationship_type == PoiOverlapRelationshipType.BOUNDARY_TOUCHING:
                    continue
                results.append(
                    PoiOverlapRelationship(
                        symbol=symbol,
                        direction=direction,
                        poi_a_record_id=obs_a.record_id,
                        poi_b_record_id=obs_b.record_id,
                        relationship_type=relationship_type,
                        overlap_top=overlap_top,
                        overlap_bottom=overlap_bottom,
                        evaluated_at_time_utc=evaluated_at_time_utc,
                    )
                )

    return tuple(results)


def resolve_merges(
    observations: tuple[PoiObservation, ...],
) -> tuple[dict[UUIDv7, tuple[UUIDv7, ...]], dict[UUIDv7, Timeframe]]:
    merged_children: dict[UUIDv7, list[UUIDv7]] = {}
    effective_timeframe: dict[UUIDv7, Timeframe] = {}

    by_group: dict[
        tuple[InternalSymbol, PoiDirection, PoiType], list[PoiObservation]
    ] = defaultdict(list)
    for observation in observations:
        by_group[
            (observation.symbol, observation.direction, observation.poi_type)
        ].append(observation)

    for group in by_group.values():
        for child in group:
            child_rank = _TIMEFRAME_STRENGTH_RANK[child.source_timeframe]
            eligible_parents: list[PoiObservation] = []
            for parent in group:
                if parent.record_id == child.record_id:
                    continue
                parent_rank = _TIMEFRAME_STRENGTH_RANK[parent.source_timeframe]
                if parent_rank <= child_rank:
                    continue
                classification = classify_zone_relationship(
                    child.zone_top,
                    child.zone_bottom,
                    parent.zone_top,
                    parent.zone_bottom,
                )
                if classification is None:
                    continue
                relationship_type = classification[0]
                if relationship_type == PoiOverlapRelationshipType.BOUNDARY_TOUCHING:
                    continue
                eligible_parents.append(parent)

            if len(eligible_parents) == 0:
                continue

            eligible_parents.sort(
                key=lambda p: (
                    -_TIMEFRAME_STRENGTH_RANK[p.source_timeframe],
                    p.availability_time_utc,
                    str(p.record_id),
                )
            )
            best_parent = eligible_parents[0]
            merged_children.setdefault(best_parent.record_id, []).append(
                child.record_id
            )
            effective_timeframe[child.record_id] = best_parent.source_timeframe

    return {
        parent_id: tuple(children) for parent_id, children in merged_children.items()
    }, effective_timeframe
