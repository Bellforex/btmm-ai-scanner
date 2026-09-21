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
    "Rc5Validity",
    "StablePoiKey",
    "SuppressionTimeline",
    "active_display_pois",
    "authoritative_rc5_pois",
    "display_hidden_reason",
    "interaction_count",
    "is_rc5_active_for_display",
    "rc5_poi_is_valid",
    "rc5_validity",
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


class Rc5Validity(StrEnum):
    """Whether the ZONE ITSELF still stands, independent of who may trade it.

    This is the bottom of three nested layers, and keeping them apart is the
    point:

    * VALIDITY (here) -- a structural fact about price. Does this zone still
      exist as a level that has not been confirmed broken? It does not care
      about authority, availability, or whether anyone is allowed to act.
    * DISPLAY eligibility -- valid AND the authoritative record for its origin.
      A same-origin subordinate is a perfectly valid zone that simply must not
      be drawn twice.
    * P5 ACTIONABILITY -- display-eligible AND available AND admitted by the
      eligibility algebra.

    Each layer is a subset of the one before it. The author's requirement to
    SEPARATE OPPORTUNITY EVALUATION FROM TERMINAL MONITORING is exactly this
    split: terminal monitoring watches VALIDITY, so it keeps watching a POI
    that is suppressed or not currently actionable, and a zone can therefore
    die correctly even while nobody was allowed to trade it.
    """

    VALID = "VALID"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"


def rc5_validity(state: Any | None) -> Rc5Validity:
    """The canonical validity of one POI, read from the frozen lifecycle only.

    Deliberately takes no ledger and no observation: validity must not depend
    on authority, or the two could disagree about whether a zone exists.

    MITIGATION IS NOT TERMINATION. ``terminal_reason = MITIGATED`` is set at
    the FIRST TOUCH and says only that price has been in the zone. A zone dies
    on confirmed failure through its FAR side
    (``GENUINE_INVALIDATION_CONFIRMED``); a far-side break that was reclaimed
    lands on ``FALSE_INVALIDATION_CONFIRMED`` and stays VALID.
    """
    if state is None:
        return Rc5Validity.VALID
    if (
        getattr(state, "poi_lifecycle_status", None)
        is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    ):
        return Rc5Validity.INVALIDATED
    reason = getattr(state, "terminal_reason", None)
    if reason is not None:
        name = reason.value
        if name == "INVALIDATED":
            return Rc5Validity.INVALIDATED
        if name == "PROMOTED_TO_ORDER_BLOCK":
            # NOT a failure, and NOT merely a display preference. The frozen
            # RC3 rule (poi/enums.py) is explicit: the engulfing record of a
            # formation confirmed as a leg origin ENDS when its ORDER BLOCK
            # record becomes available, "so one formation never has two live
            # records". The promoted record therefore ceases to be a standalone
            # lifecycle entity -- the ORDER BLOCK is the live record of that
            # same formation from here on. It stays in history; it is not a
            # live zone, so it is not VALID.
            return Rc5Validity.SUPERSEDED
        # MITIGATED and anything else coarse: the zone was used, not broken.
    return Rc5Validity.VALID


def rc5_poi_is_valid(state: Any | None) -> bool:
    """The zone still stands. This is what TERMINAL MONITORING watches."""
    return rc5_validity(state) is Rc5Validity.VALID


class DisplayHiddenReason(StrEnum):
    """Why a POI is not drawn as an active zone. Forensic only -- the record
    itself is never removed from history."""

    AUTHORITY_SUPPRESSED = "AUTHORITY_SUPPRESSED"
    INVALIDATED = "INVALIDATED"
    SUPERSEDED = "SUPERSEDED"


def display_hidden_reason(
    observation: Any,
    state: Any | None,
    ledger: Rc5SemanticLedger,
) -> DisplayHiddenReason | None:
    """Why this POI should not render as an active zone, or ``None`` if it
    should.

    MITIGATION IS NOT TERMINATION (author correction, 2026-09-21). The frozen
    lifecycle sets ``terminal_reason = MITIGATED`` at the FIRST TOUCH of the
    zone -- ``resolve_terminal(first_touch_time, invalidation_time_utc)`` --
    and because the earliest cause wins, a POI that was touched and only later
    broke down still records MITIGATED. So "was mitigated" says only that price
    has been in the zone at least once. It says nothing about whether the zone
    failed.

    A POI stays valid through any number of interaction episodes. It dies only
    when price confirms failure through its FAR side, which the frozen breach
    walk already decides: ``GENUINE_INVALIDATION_CONFIRMED``. A far-edge break
    that was reclaimed lands on ``FALSE_INVALIDATION_CONFIRMED`` instead and
    deliberately stays visible -- preserving exactly the false-break case the
    author asked to keep.

    No new threshold is introduced. Penetration depth, tap count and episode
    boundaries are analytics; visibility is governed by valid vs confirmed
    invalidated. There is no time expiry.

    This reads the frozen records without mutating them, so RC4 is untouched.

    DISPLAY IS VALIDITY PLUS AUTHORITY, and it is computed that way rather
    than re-derived, so the drawn set can never disagree with the set terminal
    monitoring is watching. Authority is checked FIRST: a subordinate is not a
    separate opportunity however healthy its own lifecycle is.
    """
    record = ledger.get(stable_poi_key(observation))
    if record is not None and record.is_suppressed:
        return DisplayHiddenReason.AUTHORITY_SUPPRESSED
    validity = rc5_validity(state)
    if validity is Rc5Validity.INVALIDATED:
        return DisplayHiddenReason.INVALIDATED
    if validity is Rc5Validity.SUPERSEDED:
        # drawing both this and the ORDER BLOCK would duplicate one zone.
        return DisplayHiddenReason.SUPERSEDED
    return None


def is_rc5_active_for_display(
    observation: Any,
    state: Any | None,
    ledger: Rc5SemanticLedger,
) -> bool:
    return display_hidden_reason(observation, state, ledger) is None


def interaction_count(state: Any | None) -> int:
    """Completed interaction episodes, from the frozen tap count. Diagnostic
    evidence for later backtesting -- it changes no trade rule and no
    visibility."""
    return 0 if state is None else int(getattr(state, "tap_count", 0) or 0)


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
