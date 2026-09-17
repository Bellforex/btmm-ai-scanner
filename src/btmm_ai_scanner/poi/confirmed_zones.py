"""RC3 final semantic lock: confirmed SUPPORT / RESISTANCE ZONEs are immutable.

Author decision (2026-09-17): once a POI has passed its confirmation gate and
become available, its historical existence is immutable. The measurement
support/resistance frontier is a *current-state* projection -- a zone can be
replaced or dropped when later swings re-shape it -- so a POI built straight from
it could disappear retroactively (observed on real FXCM M15 data, while Pine,
which never removes a registry POI, kept and mitigated it).

The SUPPORT_ZONE / RESISTANCE_ZONE POI therefore snapshots each zone the first
time it appears (source, geometry, availability) and never removes or changes it; it still ends through the normal
lifecycle. EQUAL_HIGHS / EQUAL_LOWS liquidity stay P3 context (not lifecycle
POIs) and keep following the current measurement.

* Incremental replay: ``lock_reference_candidates`` on every recomputation.
* Batch: ``immutable_reference_candidates`` replays the frozen incremental
  measurement (identical to the batch measurement at every prefix) and applies
  the same lock at every prefix where the zone set can change.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.analyzer import (
    DerivedOutputIdentityProvider,
    MarketMeasurementAnalysis,
    _advance_measurement_replay_state,
    _create_initial_measurement_replay_state,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.reference_zones import (
    ReferenceZoneCandidate,
    detect_reference_zones,
)

__all__ = [
    "LOCKED_REFERENCE_TYPES",
    "immutable_reference_candidates",
    "lock_reference_candidates",
]

LOCKED_REFERENCE_TYPES = frozenset({PoiType.SUPPORT_ZONE, PoiType.RESISTANCE_ZONE})


def _key(candidate: ReferenceZoneCandidate) -> tuple[Any, ...]:
    return (candidate.poi_type, candidate.source_zone_record_id)


def lock_reference_candidates(
    locked: tuple[ReferenceZoneCandidate, ...],
    current: Sequence[ReferenceZoneCandidate],
) -> tuple[ReferenceZoneCandidate, ...]:
    """Append every S/R zone not seen before; already-locked zones are kept
    exactly as first seen. The zone keeps its own availability even when the
    measurement discovers it after that close (reaction windows confirm late):
    the frozen reference-zone backfill contract (be1df56), which Pine mirrors."""
    keys = {_key(c) for c in locked}
    added: list[ReferenceZoneCandidate] = []
    for candidate in current:
        if candidate.poi_type not in LOCKED_REFERENCE_TYPES:
            continue
        key = _key(candidate)
        if key in keys:
            continue
        keys.add(key)
        added.append(candidate)
    return (*locked, *added) if added else locked


def immutable_reference_candidates(
    candles: Sequence[NormalizedCandle],
    final_measurement: MarketMeasurementAnalysis,
    measurement_configuration: MarketMeasurementConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> tuple[ReferenceZoneCandidate, ...]:
    """Locked S/R zone POIs over every prefix + the current equal-level context."""
    state = _create_initial_measurement_replay_state(
        identity_provider, measurement_configuration
    )
    locked: tuple[ReferenceZoneCandidate, ...] = ()
    previous: tuple[Any, ...] | None = None
    for candle in candles:
        state = _advance_measurement_replay_state(
            state, candle, measurement_configuration
        )
        zones = state.support_resistance_zones_so_far
        swing_end = {
            s.record_id: s.pivot_end_time_utc for s in state.confirmed_swings_so_far
        }
        signature = tuple(
            (
                z.record_id,
                z.content_fingerprint,
                swing_end.get(z.origin_swing_record_id),
            )
            for z in zones
        )
        if signature == previous:
            continue
        previous = signature
        locked = lock_reference_candidates(
            locked,
            detect_reference_zones(zones, (), state.confirmed_swings_so_far),
        )
    if candles and [
        (z.record_id, z.content_fingerprint)
        for z in state.support_resistance_zones_so_far
    ] != [
        (z.record_id, z.content_fingerprint)
        for z in final_measurement.support_resistance_zones
    ]:
        raise ValueError(
            "support/resistance zones do not match the measurement configuration"
            " or identity provider used to replay their prefixes"
        )
    context = tuple(
        detect_reference_zones(
            (),
            final_measurement.equal_level_clusters,
            final_measurement.confirmed_swings,
        )
    )
    return (*locked, *context)
