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
from datetime import datetime
from typing import Any

from btmm_ai_scanner.poi.authority import AuthorityReason, OriginClusterKey
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.structural_role import StructuralRole

__all__ = [
    "Rc5PoiSemanticRecord",
    "Rc5SemanticLedger",
    "StablePoiKey",
    "stable_poi_key",
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
