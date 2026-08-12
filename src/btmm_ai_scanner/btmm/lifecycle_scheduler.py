"""A6-B2-B: event-driven persistent BTMM setup scheduler.

Standalone foundation only — NOT wired into ``_advance_btmm_replay_state`` or any
production hot path (see ``btmm.analyzer``, unmodified). Mirrors the accepted
A6-B1-B POI scheduler's design (``poi.lifecycle_scheduler``): the B2-A cursor
(``btmm.lifecycle_cursor``, unmodified) owns all lifecycle semantics; this module
owns *which* setups could change this candle and wakes only those, carrying every
other setup forward by reference in persistent (path-copying) structures.

Wake sources, derived from reading ``advance_btmm_cursor`` / ``materialize_btmm_
cursor`` (both unmodified) rather than assumed:

* WAIT_FORMING and WAIT_INTERACTION are true index-driven wake sources — a
  non-triggering candle is a PROVEN no-op for both (see ``cursor_fast_forward``'s
  module docstring), so they are indexed and skipped candles are fast-forwarded
  in O(1).
* WAIT_REACTION_START is NOT index-driven: ``running_anchor`` accumulates
  ``min``/``max`` over every candle since interaction whether or not the
  reaction starts that candle, so a setup in this stage — like the bounded
  reaction-window buffer — is scheduled every candle via the due-bar registry
  (the same mechanism the accepted POI scheduler uses for its own must-see-every-
  candle states). This is a deliberate, disclosed choice over inventing a second
  index: the total work is identical either way (one ``advance_btmm_cursor`` call
  per candle in the gap); the due-bucket is simply the already-proven mechanism.
* Automatic-evidence and reviewed-evidence resolution, and the source-POI
  genuine-invalidation override, are NOT candle scans at all (``materialize_btmm_
  cursor`` is a fixed-cost function over the cached price-stage results plus the
  current evidence/transition inputs) — they are event-driven: a setup watches
  its own source POI (keyed by ``source_poi_record_id``) and is woken only when a
  NEW transition or reviewed-evidence record for that exact POI arrives, never by
  scanning every setup every candle.
* A GENUINE_INVALIDATION_CONFIRMED transition can retroactively cancel a setup
  regardless of its current price stage (the batch tail logic in ``materialize_
  btmm_cursor`` truncates the walk at the invalidation time unconditionally), so
  every price-open setup ALSO watches its source POI, and a genuine-invalidation
  event forces re-materialization even mid-price-stage.

No historical scan anywhere: setup creation/change/removal arrives as an explicit
bounded ``BtmmSetupDelta`` (see ``setup_delta.py``), and POI-transition / reviewed-
evidence events arrive as explicit bounded per-candle lists — never a walk of the
full setup or POI-transition history.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.cursor_fast_forward import fast_forward_btmm_cursor
from btmm_ai_scanner.btmm.enums import BtmmLifecycleStatus
from btmm_ai_scanner.btmm.interaction import ELIGIBLE_INTERACTION_CLASSES
from btmm_ai_scanner.btmm.lifecycle import LifecycleWalkResult
from btmm_ai_scanner.btmm.lifecycle_cursor import (
    BtmmLifecycleCursor,
    advance_btmm_cursor,
    create_btmm_lifecycle_cursor,
    materialize_btmm_cursor,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.btmm.setup_delta import BtmmSetupDelta
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.persistent_interval_index import (
    PersistentIntervalTouchIndex,
    create_persistent_interval_index,
)
from btmm_ai_scanner.poi.persistent_map import PersistentMap

_NEG_INF = Decimal("-Infinity")
_EMPTY_SETUP_DELTA = BtmmSetupDelta()

_RELEVANT_POI_TRANSITION_TYPES: frozenset[PoiLifecycleTransitionType] = frozenset(
    {
        PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
    }
)


def _time_key(dt: datetime) -> Decimal:
    """A monotonic Decimal projection of a UTC datetime, used only as an ordering
    key inside the (price-typed) persistent interval index reused here for the
    forming-due threshold. Microsecond precision matches every timestamp this
    codebase produces (candle availability times), so no ordering collision is
    possible between distinct instants."""
    return Decimal(int(dt.timestamp() * 1_000_000))


class BtmmSchedulerStage(Enum):
    """Scheduler-private wake-registration stage. Derived from the B2-A cursor's
    own private fields (never from the public ``BtmmLifecycleStatus`` enum alone —
    ``CONFIRMED``/``CANCELLED`` still require the source-POI watch distinction
    ``BtmmLifecycleStatus`` cannot express)."""

    WAIT_FORMING = "WAIT_FORMING"
    WAIT_INTERACTION = "WAIT_INTERACTION"
    WAIT_REACTION_START = "WAIT_REACTION_START"
    REACTION_DUE = "REACTION_DUE"
    EVIDENCE_WAIT = "EVIDENCE_WAIT"
    CONFIRMED_SOURCE_WATCH = "CONFIRMED_SOURCE_WATCH"
    SOURCE_POI_WATCH = "SOURCE_POI_WATCH"
    FROZEN = "FROZEN"


def _price_stage(cursor: BtmmLifecycleCursor) -> BtmmSchedulerStage | None:
    """The cursor's currently-open price stage, or ``None`` if price scanning is
    fully resolved (interaction determined ineligible, or the reaction window
    filled). Pure function of the B2-A cursor's own fields."""
    if cursor.entered_forming_index is None:
        return BtmmSchedulerStage.WAIT_FORMING
    if cursor.interaction_index is None:
        return BtmmSchedulerStage.WAIT_INTERACTION
    if cursor.interaction_class not in ELIGIBLE_INTERACTION_CLASSES:
        return None
    if cursor.reaction_start_index is None:
        return BtmmSchedulerStage.WAIT_REACTION_START
    if cursor.tier_result is None:
        return BtmmSchedulerStage.REACTION_DUE
    return None


@dataclass(frozen=True)
class _Reg:
    source_poi_record_id: UUID
    stage: BtmmSchedulerStage
    zone_top: Decimal
    zone_bottom: Decimal
    forming_key: Decimal
    in_forming: bool
    in_interaction: bool
    in_poi_watch: bool


@dataclass(frozen=True)
class BtmmSetupEventScheduler:
    configuration: BtmmConfiguration
    total_count: int
    forming_index: PersistentIntervalTouchIndex
    interaction_index: PersistentIntervalTouchIndex
    cursors: PersistentMap[BtmmLifecycleCursor]
    regs: PersistentMap[_Reg]
    due: PersistentMap[frozenset[UUID]]
    source_poi_watch: PersistentMap[frozenset[UUID]]
    poi_transitions: PersistentMap[tuple[PoiLifecycleTransition, ...]]
    reviewed_evidence: PersistentMap[BtmmReviewedEvidence]
    poi_to_setup: PersistentMap[UUID]
    max_availability: datetime | None = None
    # Instrumentation for the last advance only (not part of the persistent
    # state; proves live-engine behaviour and feeds the optional benchmark).
    woken_ids: frozenset[UUID] = frozenset()
    rebuilt: int = 0
    last_walks: dict[UUID, LifecycleWalkResult] = field(default_factory=dict)

    def materialize_cursor(self, setup_id: UUID) -> BtmmLifecycleCursor | None:
        """The raw cursor for ``setup_id`` as currently stored. Dormant cursors'
        ``total_count``/``prev_candle`` may be behind the scheduler's own
        ``total_count`` — harmless, since ``materialize_btmm_cursor`` never reads
        either field; only ``advance_btmm_cursor`` (a write path) needs them
        caught up, and that always fast-forwards immediately before advancing."""
        return self.cursors.get(setup_id.int)

    def materialize_walk(self, setup_id: UUID) -> LifecycleWalkResult | None:
        """The exact current ``LifecycleWalkResult`` for ``setup_id`` — O(1)
        fixed-cost, safe to call at any price stage (mirrors what ``analyze_btmm``
        would compute for this setup from the current candle/evidence/transition
        state, without any candle re-scan)."""
        cursor = self.cursors.get(setup_id.int)
        if cursor is None:
            return None
        transitions = (
            self.poi_transitions.get(cursor.source_poi_record_id.int, ()) or ()
        )
        evidence = self.reviewed_evidence.get(cursor.source_poi_record_id.int)
        return materialize_btmm_cursor(
            cursor, transitions, evidence, self.configuration
        )

    def stage_of(self, setup_id: UUID) -> BtmmSchedulerStage | None:
        reg = self.regs.get(setup_id.int)
        return reg.stage if reg is not None else None


def create_btmm_scheduler(configuration: BtmmConfiguration) -> BtmmSetupEventScheduler:
    return BtmmSetupEventScheduler(
        configuration=configuration,
        total_count=0,
        forming_index=create_persistent_interval_index(),
        interaction_index=create_persistent_interval_index(),
        cursors=PersistentMap(),
        regs=PersistentMap(),
        due=PersistentMap(),
        source_poi_watch=PersistentMap(),
        poi_transitions=PersistentMap(),
        reviewed_evidence=PersistentMap(),
        poi_to_setup=PersistentMap(),
    )


@dataclass
class _Mut:
    forming_index: PersistentIntervalTouchIndex
    interaction_index: PersistentIntervalTouchIndex
    cursors: PersistentMap[BtmmLifecycleCursor]
    regs: PersistentMap[_Reg]
    due: PersistentMap[frozenset[UUID]]
    source_poi_watch: PersistentMap[frozenset[UUID]]
    poi_transitions: PersistentMap[tuple[PoiLifecycleTransition, ...]]
    reviewed_evidence: PersistentMap[BtmmReviewedEvidence]
    poi_to_setup: PersistentMap[UUID]

    def _watch_poi(self, setup_id: UUID, poi_id: UUID) -> None:
        bucket = self.source_poi_watch.get(poi_id.int, frozenset())
        assert bucket is not None
        self.source_poi_watch = self.source_poi_watch.set(
            poi_id.int, bucket | {setup_id}
        )

    def _unwatch_poi(self, setup_id: UUID, poi_id: UUID) -> None:
        bucket = self.source_poi_watch.get(poi_id.int)
        if not bucket:
            return
        remaining = bucket - {setup_id}
        if remaining:
            self.source_poi_watch = self.source_poi_watch.set(poi_id.int, remaining)
        else:
            self.source_poi_watch = self.source_poi_watch.delete(poi_id.int)

    def _unregister_indexes(self, setup_id: UUID) -> None:
        reg = self.regs.get(setup_id.int)
        if reg is None:
            return
        if reg.in_forming:
            self.forming_index = self.forming_index.remove(setup_id, reg.forming_key)
        if reg.in_interaction:
            self.interaction_index = self.interaction_index.remove(
                setup_id, reg.zone_bottom
            )
        if reg.in_poi_watch:
            self._unwatch_poi(setup_id, reg.source_poi_record_id)
        self.regs = self.regs.delete(setup_id.int)

    def _full_remove(self, setup_id: UUID) -> None:
        """The setup's source POI disappeared from the current universe: drop the
        setup entirely (cursor, every index/watch registration, and its POI's
        transition/evidence caches — nothing can reference that POI again)."""
        reg = self.regs.get(setup_id.int)
        self._unregister_indexes(setup_id)
        self.cursors = self.cursors.delete(setup_id.int)
        if reg is not None:
            poi_id = reg.source_poi_record_id
            self.poi_to_setup = self.poi_to_setup.delete(poi_id.int)
            self.poi_transitions = self.poi_transitions.delete(poi_id.int)
            self.reviewed_evidence = self.reviewed_evidence.delete(poi_id.int)


def _reconcile(
    mut: _Mut,
    setup_id: UUID,
    source_poi_record_id: UUID,
    cursor: BtmmLifecycleCursor,
    configuration: BtmmConfiguration,
    next_bar: int,
    last_walks: dict[UUID, LifecycleWalkResult],
) -> None:
    """Re-derive and apply this setup's exact registration from its current
    cursor + known POI-transition/evidence state. Always unregisters first (a
    clean slate diffed against the fresh decision), so this is idempotent and
    correct regardless of what the setup was previously registered as."""
    mut._unregister_indexes(setup_id)

    poi_transitions = mut.poi_transitions.get(source_poi_record_id.int, ()) or ()
    has_genuine_invalidation = any(
        t.transition_type == PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
        for t in poi_transitions
    )
    # A genuine invalidation retroactively cancels regardless of price stage
    # (materialize_btmm_cursor's tail truncation is unconditional), so it forces
    # immediate re-materialization even while price is still open.
    stage = None if has_genuine_invalidation else _price_stage(cursor)

    # materialize_btmm_cursor is a fixed-cost (O(1), no candle scan) function of
    # the cursor's currently-cached price-stage results plus the known evidence/
    # transition inputs -- it is exact and cheap at ANY stage, not only once
    # price is fully resolved. ENTERED_FORMING and ACCURACY_GATE_CONFIRMED (and
    # any evidence-triggered transitions) can already be present while the
    # cursor is still mid-price-scan, so last_walks must capture them here,
    # every reconcile, not only in the price-resolved branch below.
    evidence = mut.reviewed_evidence.get(source_poi_record_id.int)
    walk = materialize_btmm_cursor(cursor, poi_transitions, evidence, configuration)
    last_walks[setup_id] = walk

    if stage in (BtmmSchedulerStage.WAIT_FORMING, BtmmSchedulerStage.WAIT_INTERACTION):
        if stage is BtmmSchedulerStage.WAIT_FORMING:
            key = _time_key(cursor.candidate_availability_time_utc)
            mut.forming_index = mut.forming_index.insert(setup_id, key, key)
            reg = _Reg(
                source_poi_record_id,
                stage,
                Decimal(0),
                Decimal(0),
                key,
                True,
                False,
                True,
            )
        else:
            mut.interaction_index = mut.interaction_index.insert(
                setup_id, cursor.zone_bottom, cursor.zone_top
            )
            reg = _Reg(
                source_poi_record_id,
                stage,
                cursor.zone_top,
                cursor.zone_bottom,
                Decimal(0),
                False,
                True,
                True,
            )
        mut._watch_poi(setup_id, source_poi_record_id)
        mut.regs = mut.regs.set(setup_id.int, reg)
        return

    if stage in (
        BtmmSchedulerStage.WAIT_REACTION_START,
        BtmmSchedulerStage.REACTION_DUE,
    ):
        bucket = mut.due.get(next_bar, frozenset())
        assert bucket is not None
        mut.due = mut.due.set(next_bar, bucket | {setup_id})
        mut._watch_poi(setup_id, source_poi_record_id)
        mut.regs = mut.regs.set(
            setup_id.int,
            _Reg(
                source_poi_record_id,
                stage,
                Decimal(0),
                Decimal(0),
                Decimal(0),
                False,
                False,
                True,
            ),
        )
        return

    # Price-resolved (naturally or forced by a genuine invalidation): walk was
    # already materialized and captured above.
    poi_terminal = any(
        t.transition_type in _RELEVANT_POI_TRANSITION_TYPES for t in poi_transitions
    )
    primary_state = walk.final_fields.primary_state

    if primary_state == BtmmLifecycleStatus.BTMM_BLOCKED:
        # Always watch: could still be woken by reviewed evidence OR a later
        # genuine invalidation, regardless of whether the POI already has a
        # (non-genuine) terminal transition on file.
        final_stage = BtmmSchedulerStage.EVIDENCE_WAIT
        watch = True
    elif primary_state == BtmmLifecycleStatus.BTMM_CONFIRMED:
        watch = not poi_terminal
        final_stage = (
            BtmmSchedulerStage.CONFIRMED_SOURCE_WATCH
            if watch
            else BtmmSchedulerStage.FROZEN
        )
    else:
        assert primary_state == BtmmLifecycleStatus.BTMM_CANCELLED
        watch = not poi_terminal
        final_stage = (
            BtmmSchedulerStage.SOURCE_POI_WATCH if watch else BtmmSchedulerStage.FROZEN
        )

    if watch:
        mut._watch_poi(setup_id, source_poi_record_id)
    mut.regs = mut.regs.set(
        setup_id.int,
        _Reg(
            source_poi_record_id,
            final_stage,
            Decimal(0),
            Decimal(0),
            Decimal(0),
            False,
            False,
            watch,
        ),
    )


def advance_btmm_scheduler(
    scheduler: BtmmSetupEventScheduler,
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    *,
    setup_delta: BtmmSetupDelta = _EMPTY_SETUP_DELTA,
    new_poi_transitions: Sequence[PoiLifecycleTransition] = (),
    new_reviewed_evidence: Sequence[BtmmReviewedEvidence] = (),
) -> BtmmSetupEventScheduler:
    """Advance the scheduler by exactly one appended candle (``candles[-1]``) plus
    its full-prefix ATR-14 value, the exact bounded setup delta for this candle,
    and this candle's exact new POI-transition / reviewed-evidence events.
    ``candles`` / ``atr_values`` are the full visible prefix (needed to (re)build
    a new or changed setup's cursor from its own history). Transactional: a fresh
    scheduler is returned and the input one is never mutated."""
    m = scheduler.total_count
    if len(candles) != m + 1:
        raise ValueError("candles length must equal scheduler.total_count + 1")
    candle = candles[m]
    atr = atr_values[m]
    config = scheduler.configuration
    next_bar = m + 1
    prior_max = scheduler.max_availability
    new_max_availability = (
        candle.availability_time_utc
        if prior_max is None
        else max(prior_max, candle.availability_time_utc)
    )

    mut = _Mut(
        forming_index=scheduler.forming_index,
        interaction_index=scheduler.interaction_index,
        cursors=scheduler.cursors,
        regs=scheduler.regs,
        due=scheduler.due,
        source_poi_watch=scheduler.source_poi_watch,
        poi_transitions=scheduler.poi_transitions,
        reviewed_evidence=scheduler.reviewed_evidence,
        poi_to_setup=scheduler.poi_to_setup,
    )

    last_walks: dict[UUID, LifecycleWalkResult] = {}

    # 1. Removals: source POI vanished from the current universe.
    for poi_id in setup_delta.removed_source_poi_ids:
        setup_id = mut.poi_to_setup.get(poi_id.int)
        if setup_id is not None:
            mut._full_remove(setup_id)

    # 2. Changed-setup teardown (index/cursor only; POI transition/evidence
    #    caches are preserved -- still relevant to the rebuilt cursor).
    changed_ids = {spec.setup_record_id for spec in setup_delta.changed_setups}
    for spec in setup_delta.changed_setups:
        mut._unregister_indexes(spec.setup_record_id)
        mut.cursors = mut.cursors.delete(spec.setup_record_id.int)

    # 3. Absorb this candle's new POI-transition / reviewed-evidence events
    #    before any wake/reconcile, so materialize sees the current picture.
    for transition in new_poi_transitions:
        if transition.transition_type in _RELEVANT_POI_TRANSITION_TYPES:
            poi_id = transition.poi_record_id
            existing = mut.poi_transitions.get(poi_id.int, ())
            assert existing is not None
            mut.poi_transitions = mut.poi_transitions.set(
                poi_id.int, (*existing, transition)
            )
    for evidence in new_reviewed_evidence:
        mut.reviewed_evidence = mut.reviewed_evidence.set(
            evidence.source_poi_record_id.int, evidence
        )

    # 4. Wake discovery -- index/due/watch-driven only, no historical setup scan.
    forming_wake = mut.forming_index.overlaps(
        _NEG_INF, _time_key(candle.availability_time_utc)
    )
    interaction_wake = mut.interaction_index.overlaps(candle.low, candle.high)
    due_wake = scheduler.due.get(m, frozenset()) or frozenset()
    price_wake = {
        sid
        for sid in (set(forming_wake) | set(interaction_wake) | set(due_wake))
        if sid.int in mut.cursors
    }

    poi_event_wake: set[UUID] = set()
    for transition in new_poi_transitions:
        if transition.transition_type in _RELEVANT_POI_TRANSITION_TYPES:
            bucket = mut.source_poi_watch.get(transition.poi_record_id.int)
            if bucket:
                poi_event_wake |= set(bucket)
    for evidence in new_reviewed_evidence:
        bucket = mut.source_poi_watch.get(evidence.source_poi_record_id.int)
        if bucket:
            poi_event_wake |= set(bucket)
    poi_event_wake = {sid for sid in poi_event_wake if sid.int in mut.cursors}

    # 5. Advance each woken, surviving, pre-existing cursor exactly once.
    for setup_id in price_wake:
        cursor = mut.cursors.get(setup_id.int)
        assert cursor is not None
        cursor = fast_forward_btmm_cursor(cursor, candles, m)
        cursor = advance_btmm_cursor(cursor, candle, atr, config)
        mut.cursors = mut.cursors.set(setup_id.int, cursor)
        _reconcile(
            mut,
            setup_id,
            cursor.source_poi_record_id,
            cursor,
            config,
            next_bar,
            last_walks,
        )

    # Pure event wakes not already advanced by price this candle: re-materialize
    # only (their price stage, if any, is untouched by this event).
    for setup_id in poi_event_wake - price_wake:
        cursor = mut.cursors.get(setup_id.int)
        assert cursor is not None
        _reconcile(
            mut,
            setup_id,
            cursor.source_poi_record_id,
            cursor,
            config,
            next_bar,
            last_walks,
        )

    # 6. (Re)build new and changed setups. A brand-new setup whose candidate
    #    availability is at least the max availability of every candle seen has
    #    no eligible candle to enter forming yet -- pre-start w.r.t. the whole
    #    prefix, so its cursor is constructed in O(1) (fresh + fast-forward).
    #    Otherwise (a changed setup, or a new setup whose availability precedes
    #    an already-seen candle) the cursor is rebuilt from its own history.
    rebuilt = 0
    for spec in list(setup_delta.changed_setups) + list(setup_delta.new_setups):
        is_new = spec.setup_record_id not in changed_ids
        cursor = create_btmm_lifecycle_cursor(
            spec.symbol,
            spec.source_timeframe,
            spec.setup_record_id,
            spec.source_poi_record_id,
            spec.zone_top,
            spec.zone_bottom,
            spec.direction,
            spec.candidate_availability_time_utc,
            config,
        )
        if is_new and spec.candidate_availability_time_utc >= new_max_availability:
            cursor = fast_forward_btmm_cursor(cursor, candles, next_bar)
        else:
            for idx in range(0, m + 1):
                cursor = advance_btmm_cursor(
                    cursor, candles[idx], atr_values[idx], config
                )
            rebuilt += 1
        mut.cursors = mut.cursors.set(spec.setup_record_id.int, cursor)
        mut.poi_to_setup = mut.poi_to_setup.set(
            spec.source_poi_record_id.int, spec.setup_record_id
        )
        _reconcile(
            mut,
            spec.setup_record_id,
            spec.source_poi_record_id,
            cursor,
            config,
            next_bar,
            last_walks,
        )

    # 7. Drop the consumed due bucket for this bar.
    new_due = mut.due.delete(m)

    # woken_ids names every setup actually reconciled this candle -- price/
    # event wakes plus new/changed setups (built and reconciled in step 6),
    # so a caller can trust it as the exact "touched this candle" set (e.g.
    # for a wake-differential check) without a separate accounting pass.
    touched_ids = (
        price_wake
        | poi_event_wake
        | {spec.setup_record_id for spec in setup_delta.changed_setups}
        | {spec.setup_record_id for spec in setup_delta.new_setups}
    )

    return BtmmSetupEventScheduler(
        configuration=config,
        total_count=next_bar,
        forming_index=mut.forming_index,
        interaction_index=mut.interaction_index,
        cursors=mut.cursors,
        regs=mut.regs,
        due=new_due,
        source_poi_watch=mut.source_poi_watch,
        poi_transitions=mut.poi_transitions,
        reviewed_evidence=mut.reviewed_evidence,
        poi_to_setup=mut.poi_to_setup,
        max_availability=new_max_availability,
        woken_ids=frozenset(touched_ids),
        rebuilt=rebuilt,
        last_walks=last_walks,
    )
