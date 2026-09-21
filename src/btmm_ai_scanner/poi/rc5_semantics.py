"""RC5 semantic sidecar: the provenance that caused a POI to qualify.

Author decision, 2026-09-21. ``PoiObservation`` is a frozen ``ContractModel``
whose ``content_fingerprint`` is part of published P3/P5/P8 evidence, so RC5
must not add fields to it. The provenance lives here instead, keyed by a stable
POI identity.

WHY A SIDECAR AND NOT A LOOKUP
------------------------------
Structural roles are **per prefix**. Asking the final structural context "what
role does this POI have now?" is the wrong question and gives the wrong answer:
the author's M45 B2S qualifies through a swing that holds no role by the end of
the window. The right question is "what provenance caused this POI to qualify,
and when?", and that can only be answered by recording it at the moment it
happened. Once written it is historical evidence and is never rewritten from
later structure.

THE KEY
-------
``stable_poi_key`` is ``(poi_type, source_candle_record_ids)`` -- the same
``_formation_key`` the leg-origin gate already uses to lock and de-duplicate
formations, so this introduces no parallel identity system. It names the
*formation*: no availability time, no lifecycle state, no score, no runtime
index, nothing that can change after qualification. Batch and incremental
produce it identically, which is what makes the two paths comparable.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from btmm_ai_scanner.poi.authority import AuthorityReason, OriginClusterKey
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiType
from btmm_ai_scanner.poi.structural_role import StructuralRole

__all__ = [
    "DisplayHiddenReason",
    "Rc5PoiSemanticRecord",
    "Rc5SemanticLedger",
    "StablePoiKey",
    "SuppressionTimeline",
    "active_display_pois",
    "authoritative_rc5_pois",
    "display_hidden_reason",
    "is_rc5_active_for_display",
    "stable_poi_key",
    "suppressed_record_ids",
    "suppression_timelines",
]

#: ``(poi_type, source_candle_record_ids)``.
StablePoiKey = tuple[Any, ...]


def stable_poi_key(candidate: Any) -> StablePoiKey:
    """The formation's identity. Mirrors ``leg_origin._formation_key`` exactly;
    kept here so callers outside the gate do not reach into a private name."""
    return (candidate.poi_type, tuple(candidate.source_candle_record_ids))


@dataclass(frozen=True)
class Rc5PoiSemanticRecord:
    """What was true about a POI's structure when it qualified.

    The structural fields are immutable historical evidence. ``authority_*`` is
    assigned later, once clustering can see every member of an origin, and is
    the only part of this record that is ever filled in after the fact.
    """

    stable_poi_key: StablePoiKey
    poi_type: PoiType
    #: the formation bar -- never the qualifying bar
    source_time_utc: datetime
    #: when this POI became usable, i.e. when its evidence existed
    availability_time_utc: datetime

    #: structural provenance, exactly as the qualifying prefix resolved it
    structural_role: StructuralRole | None = None
    origin_swing_id: Any | None = None
    broken_swing_id: Any | None = None
    break_candle_id: Any | None = None
    #: when the role became true; always a real structural event's availability
    structural_since_utc: datetime | None = None

    #: filled by arbitration, not by qualification
    origin_cluster: OriginClusterKey | None = None
    authority_status: AuthorityReason | None = None
    authority_winner_key: StablePoiKey | None = None

    @property
    def is_suppressed(self) -> bool:
        return self.authority_status in (
            AuthorityReason.SAME_ORIGIN_SUBORDINATE,
            AuthorityReason.SUBORDINATE_IMBALANCE,
        )

    @property
    def is_authoritative(self) -> bool:
        """Only authoritative POIs are independent trading opportunities. A POI
        that never entered a cluster is authoritative by default -- authority
        only ever *removes* standing."""
        return not self.is_suppressed


@dataclass
class Rc5SemanticLedger:
    """Write-once provenance, keyed by stable POI identity.

    First write wins. A candidate is locked by the gate the first time it
    qualifies, and that is the prefix whose facts we want; later prefixes see
    the same POI again and must not overwrite what was recorded then.
    """

    records: dict[StablePoiKey, Rc5PoiSemanticRecord] = field(default_factory=dict)

    def record(self, entry: Rc5PoiSemanticRecord) -> None:
        self.records.setdefault(entry.stable_poi_key, entry)

    def get(self, key: StablePoiKey) -> Rc5PoiSemanticRecord | None:
        return self.records.get(key)

    def assign_authority(
        self,
        key: StablePoiKey,
        *,
        reason: AuthorityReason,
        cluster: OriginClusterKey | None = None,
        winner_key: StablePoiKey | None = None,
    ) -> None:
        """Arbitration result. Structural provenance is untouched."""
        entry = self.records.get(key)
        if entry is None:
            return
        self.records[key] = replace(
            entry,
            authority_status=reason,
            origin_cluster=cluster if cluster is not None else entry.origin_cluster,
            authority_winner_key=winner_key,
        )

    def authoritative_keys(self) -> frozenset[StablePoiKey]:
        return frozenset(k for k, v in self.records.items() if v.is_authoritative)

    def suppressed_keys(self) -> frozenset[StablePoiKey]:
        return frozenset(k for k, v in self.records.items() if v.is_suppressed)


def _cluster_key(record: Rc5PoiSemanticRecord, direction: Any) -> OriginClusterKey:
    """A structural decision origin, built from PERSISTED provenance.

    Never from a final-context lookup: roles are per-prefix, and the fact that
    qualified a POI is the one recorded when it qualified.
    """
    return OriginClusterKey(
        direction=direction,
        transition_break_candle_id=record.break_candle_id,
        transition_broken_swing_id=record.broken_swing_id,
        origin_swing_id=record.origin_swing_id,
    )


def assign_origin_authority(
    observations: Any,
    ledger: Rc5SemanticLedger,
) -> dict[OriginClusterKey, list[StablePoiKey]]:
    """Group qualified POIs by their recorded structural origin and arbitrate.

    Returns the clusters that actually contained more than one member, for
    forensics. Every member's ``authority_status`` is written back to the
    ledger; structural provenance is left untouched.

    A POI with no recorded origin swing has no structural cluster and is left
    alone -- authority only ever *removes* standing, never grants it.
    """
    from btmm_ai_scanner.poi.authority import arbitrate_cluster

    by_cluster: dict[OriginClusterKey, list[Any]] = {}
    for observation in observations:
        record = ledger.get(stable_poi_key(observation))
        if record is None or record.origin_swing_id is None:
            continue
        by_cluster.setdefault(_cluster_key(record, observation.direction), []).append(
            observation
        )

    multi: dict[OriginClusterKey, list[StablePoiKey]] = {}
    for cluster, members in by_cluster.items():
        if len(members) < 2:
            continue
        decisions = arbitrate_cluster(list(members), cluster)
        winner = next(
            (d for d in decisions if d.reason is AuthorityReason.PRIMARY), None
        )
        winner_key = stable_poi_key(winner.candidate) if winner else None
        for decision in decisions:
            key = stable_poi_key(decision.candidate)
            ledger.assign_authority(
                key,
                reason=decision.reason,
                cluster=cluster if decision.cluster is not None else None,
                winner_key=winner_key if key != winner_key else None,
            )
        multi[cluster] = [stable_poi_key(m) for m in members]
    return multi


def replay_rc5_semantic_provenance(
    candles: Any,
    configuration: Any,
    identity_provider: Any,
) -> Rc5SemanticLedger:
    """Replay ``candles`` through the canonical causal frontier and return the
    provenance it records.

    Author decision, 2026-09-21 (option A). RC5 provenance is **event history**:
    it is recorded when the causal event happens and never reconstructed from
    final state. Three separate defects came from deriving it from the final
    structural context -- a lapsing role, a role upgrade moving ``since`` later,
    and defended levels dated from swing confirmation moving it earlier -- so
    the frontier replay, which is also what live execution runs, is now the one
    producer.

    This reuses the existing incremental primitives exactly: the same
    measurement replay, the same detector frontier, the same leg-origin
    frontier. There is no second detector and no second structure walk here.

    Batch keeps its optimized frozen-observation path untouched; only the RC5
    sidecar comes from here, and the two are joined on ``_formation_key``.
    """
    from btmm_ai_scanner.domain.analyzer import (
        _advance_measurement_replay_state,
        _create_initial_measurement_replay_state,
        _measurement_replay_state_to_view,
    )
    from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
    from btmm_ai_scanner.poi.analyzer import (
        _advance_poi_replay_state,
        _create_initial_poi_replay_state,
    )

    ledger = Rc5SemanticLedger()
    measurement_configuration = MarketMeasurementConfiguration(
        minimum_price_tick=configuration.minimum_price_tick
    )
    measurement_state = _create_initial_measurement_replay_state(
        identity_provider, measurement_configuration
    )
    poi_state = _create_initial_poi_replay_state(identity_provider, configuration)
    for candle in candles:
        measurement_state = _advance_measurement_replay_state(
            measurement_state, candle, measurement_configuration
        )
        poi_state = _advance_poi_replay_state(
            poi_state,
            candle,
            _measurement_replay_state_to_view(measurement_state),
            configuration,
            ledger,
        )
    return ledger


class Rc5MissingProvenanceError(RuntimeError):
    """An authority-relevant POI has no canonical semantic record.

    Loud by design. The whole point of option A is that there is no silent
    fallback to final-context reconstruction, so a join failure must stop RC5
    analysis rather than quietly produce path-dependent authority.
    """


def join_semantic_records(
    observations: Any,
    ledger: Rc5SemanticLedger,
    *,
    required_types: Any,
) -> dict[StablePoiKey, Rc5PoiSemanticRecord]:
    """Join frozen observations to canonical provenance on ``_formation_key``.

    ``required_types`` are the families authority actually ranks. Context-only
    records -- period levels, equal-level liquidity, structural zones -- never
    pass the structural gate and so legitimately have no reversal provenance;
    they are excluded rather than faked.
    """
    joined: dict[StablePoiKey, Rc5PoiSemanticRecord] = {}
    missing: list[StablePoiKey] = []
    for observation in observations:
        if observation.poi_type not in required_types:
            continue
        key = stable_poi_key(observation)
        record = ledger.get(key)
        if record is None:
            missing.append(key)
            continue
        joined[key] = record
    if missing:
        raise Rc5MissingProvenanceError(
            f"{len(missing)} authority-relevant POIs have no canonical semantic"
            f" record; first: {missing[0][0]}"
        )
    return joined


def authoritative_rc5_pois(
    observations: Any, ledger: Rc5SemanticLedger
) -> tuple[Any, ...]:
    """The normal scanner-facing RC5 population.

    Qualified POIs minus same-origin detector synonyms. A POI with no ledger
    record is kept: context records (period levels, equal-level liquidity,
    structural zones) never enter authority, and authority only ever *removes*
    standing from something it ranked.

    The frozen observations are untouched and the suppressed records stay in
    the ledger for forensics -- this is a view, not a deletion.
    """
    suppressed = ledger.suppressed_keys()
    return tuple(o for o in observations if stable_poi_key(o) not in suppressed)


@dataclass(frozen=True)
class SuppressionTimeline:
    """Evidence that one suppression used no future information."""

    subordinate_key: StablePoiKey
    winner_key: StablePoiKey
    subordinate_source_utc: datetime
    subordinate_available_utc: datetime
    winner_source_utc: datetime
    winner_available_utc: datetime

    @property
    def resolvable_utc(self) -> datetime:
        """The first moment both members exist, i.e. when the cluster can be
        arbitrated at all."""
        return max(self.subordinate_available_utc, self.winner_available_utc)

    @property
    def is_causal(self) -> bool:
        """True when the winner was already available as soon as the
        subordinate was, so suppression never rewrites a period in which the
        subordinate was legitimately actionable and the winner did not exist."""
        return self.winner_available_utc <= self.subordinate_available_utc

    @property
    def actionable_window(self) -> timedelta:
        """How long the subordinate stood alone before its winner existed.
        Zero for a causal suppression."""
        if self.is_causal:
            return timedelta(0)
        return self.winner_available_utc - self.subordinate_available_utc


def suppression_timelines(ledger: Rc5SemanticLedger) -> list[SuppressionTimeline]:
    """One timeline per suppression, for the causality audit."""
    out: list[SuppressionTimeline] = []
    for key in sorted(ledger.suppressed_keys(), key=str):
        record = ledger.records[key]
        winner_key = record.authority_winner_key
        winner = ledger.records.get(winner_key) if winner_key else None
        if winner is None or winner_key is None:
            continue
        out.append(
            SuppressionTimeline(
                subordinate_key=key,
                winner_key=winner_key,
                subordinate_source_utc=record.source_time_utc,
                subordinate_available_utc=record.availability_time_utc,
                winner_source_utc=winner.source_time_utc,
                winner_available_utc=winner.availability_time_utc,
            )
        )
    return out


def suppressed_record_ids(
    observations: Any, ledger: Rc5SemanticLedger
) -> frozenset[Any]:
    """The ``PoiObservation.record_id`` of every same-origin subordinate.

    The ledger is keyed by ``_formation_key`` because that is stable at
    qualification time, before a record id exists. Downstream layers key by
    ``record_id``, so this bridges the two using the observations themselves.
    """
    suppressed = ledger.suppressed_keys()
    return frozenset(
        o.record_id for o in observations if stable_poi_key(o) in suppressed
    )


class DisplayHiddenReason(StrEnum):
    """Why a POI is not drawn as an active zone. Forensic only -- the record
    itself is never removed from history."""

    AUTHORITY_SUPPRESSED = "AUTHORITY_SUPPRESSED"
    MITIGATED = "MITIGATED"
    INVALIDATED = "INVALIDATED"
    TERMINAL = "TERMINAL"


def display_hidden_reason(
    observation: Any,
    state: Any | None,
    ledger: Rc5SemanticLedger,
) -> DisplayHiddenReason | None:
    """Why this POI should not render as an active zone, or ``None`` if it
    should.

    The author's complaint was that dead zones still look tradeable, so this is
    deliberately one predicate for every lifecycle-eligible family rather than
    a per-type rule, and it is meant to govern the zone box, the POI label and
    the active table row together -- hiding a label while leaving the rectangle
    is exactly the failure being fixed.

    A POI with no lifecycle state yet has not been interacted with, so it shows.
    History is untouched: this is a view.
    """
    record = ledger.get(stable_poi_key(observation))
    if record is not None and record.is_suppressed:
        return DisplayHiddenReason.AUTHORITY_SUPPRESSED
    if state is None:
        return None
    reason = getattr(state, "terminal_reason", None)
    if reason is not None:
        # MITIGATED means price used the zone; INVALIDATED means it failed.
        return (
            DisplayHiddenReason.MITIGATED
            if reason.value == "MITIGATED"
            else DisplayHiddenReason.INVALIDATED
        )
    if (
        getattr(state, "poi_lifecycle_status", None)
        is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    ):
        return DisplayHiddenReason.INVALIDATED
    if getattr(state, "terminal_time_utc", None) is not None:
        return DisplayHiddenReason.TERMINAL
    # Everything else is either fresh or inside an open interaction episode,
    # both of which the author wants visible.
    return None


def is_rc5_active_for_display(
    observation: Any,
    state: Any | None,
    ledger: Rc5SemanticLedger,
) -> bool:
    return display_hidden_reason(observation, state, ledger) is None


def active_display_pois(
    observations: Any,
    states_by_poi_id: Any,
    ledger: Rc5SemanticLedger,
) -> tuple[Any, ...]:
    """The POIs a student should see as live zones right now."""
    return tuple(
        o
        for o in observations
        if is_rc5_active_for_display(o, states_by_poi_id.get(o.record_id), ledger)
    )
