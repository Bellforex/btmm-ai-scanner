from datetime import datetime
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.domain.enums import EqualLevelType, SupportResistanceType
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


class UnknownOriginSwingError(ValueError):
    """A support/resistance zone referenced an origin swing that was not
    supplied. The zone's source time is defined as that swing's pivot-end
    candle time, so the candidate cannot be built without it. Never fall
    back to the confirmation time here — that is precisely the collapse of
    source into availability this contract exists to prevent."""


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
    confirmed_swings: tuple[ConfirmedSwing, ...],
) -> tuple[ReferenceZoneCandidate, ...]:
    """SUPPORT_ZONE / RESISTANCE_ZONE source time is the ORIGIN SWING's
    pivot-end candle time, not the zone's own confirmation time: the level
    exists in the market from the moment the swing that defines it ends,
    and only becomes tradeable (available) once the zone confirms. The two
    are distinct instants and must not be collapsed — the visual left edge
    is drawn at the source time, while freshness begins strictly after
    availability.

    Equal-level clusters are P3 CONTEXT types (deferred, never lifecycle-
    eligible) and keep their existing confirmation-time behaviour.
    """
    swing_pivot_end_by_id = {
        swing.record_id: swing.pivot_end_time_utc for swing in confirmed_swings
    }
    results: list[ReferenceZoneCandidate] = []

    for zone in support_resistance_zones:
        source_time = swing_pivot_end_by_id.get(zone.origin_swing_record_id)
        if source_time is None:
            raise UnknownOriginSwingError(
                f"origin swing {zone.origin_swing_record_id} for "
                f"{zone.zone_type.value} zone {zone.record_id} was not supplied"
            )
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
                candidate_event_time_utc=source_time,
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
