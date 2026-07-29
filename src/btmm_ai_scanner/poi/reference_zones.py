from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.domain.enums import EqualLevelType, SupportResistanceType
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


class ReferenceZoneCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    source_zone_record_id: UUID
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime


def detect_reference_zones(
    support_resistance_zones: tuple[SupportResistanceZone, ...],
    equal_level_clusters: tuple[EqualLevelCluster, ...],
) -> tuple[ReferenceZoneCandidate, ...]:
    results: list[ReferenceZoneCandidate] = []

    for zone in support_resistance_zones:
        if zone.zone_type == SupportResistanceType.SUPPORT:
            poi_type = PoiType.SUPPORT_ZONE
            direction = PoiDirection.BULLISH
        else:
            poi_type = PoiType.RESISTANCE_ZONE
            direction = PoiDirection.BEARISH
        results.append(
            ReferenceZoneCandidate(
                symbol=zone.symbol,
                timeframe=zone.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=zone.zone_top,
                zone_bottom=zone.zone_bottom,
                source_zone_record_id=zone.record_id,
                candidate_event_time_utc=zone.confirmation_time_utc,
                confirmation_time_utc=zone.confirmation_time_utc,
                availability_time_utc=zone.availability_time_utc,
            )
        )

    for cluster in equal_level_clusters:
        if cluster.cluster_type == EqualLevelType.EQUAL_HIGH:
            poi_type = PoiType.EQUAL_HIGHS_LIQUIDITY
            direction = PoiDirection.BEARISH
        else:
            poi_type = PoiType.EQUAL_LOWS_LIQUIDITY
            direction = PoiDirection.BULLISH
        results.append(
            ReferenceZoneCandidate(
                symbol=cluster.symbol,
                timeframe=cluster.timeframe,
                poi_type=poi_type,
                direction=direction,
                zone_top=cluster.zone_top,
                zone_bottom=cluster.zone_bottom,
                source_zone_record_id=cluster.record_id,
                candidate_event_time_utc=cluster.confirmation_time_utc,
                confirmation_time_utc=cluster.confirmation_time_utc,
                availability_time_utc=cluster.availability_time_utc,
            )
        )

    return tuple(results)
