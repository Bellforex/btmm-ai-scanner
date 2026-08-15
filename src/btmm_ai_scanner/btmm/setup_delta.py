"""A6-B2-B: exact incremental BTMM setup identity + delta.

``analyze_btmm`` creates exactly one setup per source POI that is BTMM-eligible
(``poi_type in configuration.eligible_poi_types`` and
``source_timeframe in formation_timeframes | supporting_only_timeframes``), keyed
by the POI's own stable ``record_id`` — the setup's own ``record_id`` is the
content-addressed identity of ``(symbol, source_timeframe, source_poi.record_id,
rule_version)`` under ``DerivedOutputType.BTMM_OBSERVATION`` (see
``btmm.analyzer.analyze_btmm`` / ``_advance_btmm_replay_state``, unmodified).

Setup fields used by the lifecycle walk (``zone_top``/``zone_bottom``/
``direction``) are read live off the current ``PoiObservation`` every time
``run_btmm_lifecycle`` is called (there is no frozen copy) — so a POI whose
zone content changes (only ``SUPPORT_ZONE``/``RESISTANCE_ZONE``, the two mutable
members of ``LIFECYCLE_ELIGIBLE_POI_TYPES``; see ``poi.detector_frontier``'s
reference-zone diff) must have its setup's cursor **rebuilt from its own candle
history with the new zone** — an unchanged identity, changed content. A POI that
disappears from the current candidate universe (again, only possible for the
mutable reference-zone family; append-only POIs are permanent) makes its setup
disappear from ``analyze_btmm``'s output going forward exactly like batch (batch
simply never iterates it again) — this module does not resolve a removed POI's
setup identity (it no longer has the symbol/timeframe/zone needed), it forwards
the POI's own record_id and leaves resolution to the scheduler's own
``poi_record_id -> setup_record_id`` registry (built when the setup was created).

Derivation touches only the bounded per-candle delta already computed upstream
(the POI incremental engine's own NEW/CHANGED/REMOVED spec lists) — never a scan
of the full historical POI or setup universe (historical setup-diff loops = 0).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.domain import DerivedOutputIdentityProvider
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.observation import PoiObservation


@dataclass(frozen=True)
class BtmmSetupSpec:
    """The setup-construction-relevant fields of one BTMM-eligible source POI."""

    setup_record_id: UUID
    symbol: InternalSymbol
    source_timeframe: Timeframe
    source_poi_record_id: UUID
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    candidate_availability_time_utc: datetime


@dataclass(frozen=True)
class BtmmSetupDelta:
    """The exact per-candle change to the setup universe, derived from the POI
    engine's own bounded NEW/CHANGED/REMOVED delta — never by diffing the full
    historical setup list. ``removed_source_poi_ids`` names the disappearing
    POIs themselves (not setup ids): this module cannot recompute a removed
    POI's setup identity (the symbol/timeframe are gone with it), so resolution
    to a setup id is the scheduler's job via its own registry."""

    new_setups: tuple[BtmmSetupSpec, ...] = ()
    changed_setups: tuple[BtmmSetupSpec, ...] = ()
    removed_source_poi_ids: tuple[UUID, ...] = ()


def setup_record_id_for_poi(
    identity_provider: DerivedOutputIdentityProvider,
    symbol: InternalSymbol,
    source_timeframe: Timeframe,
    source_poi_record_id: UUID,
    rule_version_text: str,
) -> UUID:
    """The exact setup identity ``analyze_btmm`` would assign this source POI —
    byte-identical semantic key to ``analyze_btmm``'s own
    ``DerivedOutputType.BTMM_OBSERVATION`` resolution."""
    semantic_key = (
        symbol.value,
        source_timeframe.value,
        str(source_poi_record_id),
        rule_version_text,
    )
    return identity_provider.identify(
        output_type=DerivedOutputType.BTMM_OBSERVATION, semantic_key=semantic_key
    )


def is_btmm_eligible(poi: PoiObservation, configuration: BtmmConfiguration) -> bool:
    supported_timeframes = (
        configuration.formation_timeframes | configuration.supporting_only_timeframes
    )
    return (
        poi.poi_type in configuration.eligible_poi_types
        and poi.source_timeframe in supported_timeframes
    )


def _spec(
    poi: PoiObservation,
    identity_provider: DerivedOutputIdentityProvider,
    rule_version_text: str,
) -> BtmmSetupSpec:
    setup_id = setup_record_id_for_poi(
        identity_provider,
        poi.symbol,
        poi.source_timeframe,
        poi.record_id,
        rule_version_text,
    )
    return BtmmSetupSpec(
        setup_record_id=setup_id,
        symbol=poi.symbol,
        source_timeframe=poi.source_timeframe,
        source_poi_record_id=poi.record_id,
        direction=poi.direction,
        zone_top=poi.zone_top,
        zone_bottom=poi.zone_bottom,
        candidate_availability_time_utc=poi.availability_time_utc,
    )


def derive_btmm_setup_delta(
    new_pois: Sequence[PoiObservation],
    changed_pois: Sequence[PoiObservation],
    removed_poi_ids: Sequence[UUID],
    identity_provider: DerivedOutputIdentityProvider,
    rule_version_text: str,
    configuration: BtmmConfiguration,
) -> BtmmSetupDelta:
    """Filter the POI engine's own bounded per-candle NEW/CHANGED/REMOVED delta
    down to the BTMM-eligible subset and map it onto setup identity. Touches
    only the supplied (bounded) delta lists — never the full POI or setup
    universe."""
    new_setups = tuple(
        _spec(poi, identity_provider, rule_version_text)
        for poi in new_pois
        if is_btmm_eligible(poi, configuration)
    )
    changed_setups = tuple(
        _spec(poi, identity_provider, rule_version_text)
        for poi in changed_pois
        if is_btmm_eligible(poi, configuration)
    )
    return BtmmSetupDelta(
        new_setups=new_setups,
        changed_setups=changed_setups,
        removed_source_poi_ids=tuple(removed_poi_ids),
    )
