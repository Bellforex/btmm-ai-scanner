"""A6-B1-B4/B5/B6: event-driven POI lifecycle scheduler.

Replaces the per-candle ``for every historical POI: advance its cursor`` loop with
index-driven wake discovery + gated advancement. The scheduler owns which POIs
*could* interact with a candle (the persistent touch and breach indexes) and which
*must* be processed regardless of price (the due registry); the accepted B1-A
cursor still owns all lifecycle semantics. Only woken cursors are advanced; every
other cursor is carried forward unchanged by reference (its stale ``total_count``
is reconciled lazily by ``fast_forward_poi_cursor`` when a snapshot reads it).

Exactness. The set of woken cursors at each candle is a superset of the cursors
whose B1-A state changes semantically that candle (zero false negatives), proven
by the permanent differential test against a brute-force ``advance every cursor``
oracle at every prefix. Registration is derived from private cursor state, not
public lifecycle status:

* ``in_touch``  = the cursor has started (``start_index`` set) — tap accounting
  runs for every started cursor, INCLUDING terminal ones, so a terminal POI stays
  in the touch index (its taps still evolve). This is the ``TERMINAL: register
  nowhere`` subtlety §7 warns about.
* ``in_breach`` = started AND not terminal (the breach walk is frozen at terminal).
* ``due_next``  = pre-start (must re-check its first eligible bar), or mid-tap-run
  (``in_tap`` — must see the run's end), or mid-window (non-empty suffix buffer —
  must see every candle until the reclaim/displacement window resolves).

Transactionality. Every structure is persistent (path-copying): an advance builds
a new scheduler sharing all untouched subtrees, so a raised advance leaves the
prior scheduler valid and identical by object identity — no O(P) snapshot.

Scope. New/changed/removed POIs are supplied to ``advance_scheduler`` as explicit
deltas; the scheduler performs no O(P) scan of the full POI set. A new or
reference-changed POI's cursor is (re)built from its own history (§9's bounded
per-replacement rebuild), which is the same feed the accepted analyzer already
performs on first appearance.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.persistent_map import PersistentMap
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.cursor_fast_forward import fast_forward_poi_cursor
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult
from btmm_ai_scanner.poi.lifecycle_cursor import (
    PoiLifecycleCursor,
    advance_poi_cursor,
    create_poi_lifecycle_cursor,
)
from btmm_ai_scanner.poi.persistent_breach_index import (
    PersistentBreachIndex,
    create_persistent_breach_index,
)
from btmm_ai_scanner.poi.persistent_interval_index import (
    PersistentIntervalTouchIndex,
    create_persistent_interval_index,
)


@dataclass(frozen=True)
class PoiSpec:
    """The lifecycle-relevant fields of a lifecycle-eligible POI observation."""

    record_id: UUID
    symbol: InternalSymbol
    timeframe: Timeframe
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    availability_time_utc: datetime


def _in_touch(cursor: PoiLifecycleCursor) -> bool:
    return cursor.start_index is not None


def _in_breach(cursor: PoiLifecycleCursor) -> bool:
    return cursor.start_index is not None and not cursor.terminal


def _due_next(cursor: PoiLifecycleCursor) -> bool:
    return cursor.start_index is None or cursor.in_tap or len(cursor.candle_buffer) > 0


@dataclass
class _SchedulerOps:
    """Permanent per-advance operation counters (A6-F6E). Not part of any
    published contract; they prove the delta-driven behaviour (a no-event candle
    touches zero history-proportional structures) and feed the benchmark. The
    prior registration state each candle is derived from the stored cursor, so a
    woken POI whose registration is unchanged incurs no touch/breach index write
    at all -- only its cursor (which genuinely advanced) is rewritten."""

    cursor_writes: int = 0
    cursor_deletes: int = 0
    touch_index_writes: int = 0
    breach_index_writes: int = 0
    due_writes: int = 0


@dataclass(frozen=True)
class PoiEventScheduler:
    configuration: PoiConfiguration
    total_count: int
    touch_index: PersistentIntervalTouchIndex
    breach_index: PersistentBreachIndex
    cursors: PersistentMap[PoiLifecycleCursor]
    due: PersistentMap[frozenset[UUID]]
    # Max availability_time over all candles processed so far. A new POI whose
    # availability is >= this is pre-start w.r.t. every candle seen (no candle is
    # eligible to start it), so its cursor is constructed in O(1) instead of fed
    # from history. Exact and assumption-free (no availability-monotonicity needed).
    max_availability: datetime | None = None
    # Instrumentation for the last advance (proves the live-engine behaviour and
    # feeds the benchmark; not part of any published contract). ``woken_ids`` are
    # the pre-existing cursors advanced by wake discovery; ``rebuilt`` counts the
    # new/changed cursors (re)built from history this candle.
    woken_ids: frozenset[UUID] = frozenset()
    rebuilt: int = 0
    # The exact LifecycleWalkResult produced this advance for each cursor that was
    # advanced (woken + new/changed rebuilt). A dormant cursor is absent here; its
    # walk is reconstructed on read from its materialized state (its last_seen is
    # the current candle), which the walk adapter does exactly. Transient
    # per-advance output; not part of the persistent state.
    last_walks: dict[UUID, LifecycleWalkResult] = field(default_factory=dict)
    # Per-advance operation counts (A6-F6E instrumentation; see _SchedulerOps).
    ops: _SchedulerOps = field(default_factory=lambda: _SchedulerOps())

    def materialize_cursor(self, record_id: UUID) -> PoiLifecycleCursor | None:
        """The cursor for ``record_id`` reconciled to the current candle count —
        exactly ``run_poi_lifecycle`` / sequential ``advance_poi_cursor`` at this
        prefix. Reads never mutate the scheduler."""
        cursor = self.cursors.get(record_id.int)
        if cursor is None:
            return None
        return fast_forward_poi_cursor(cursor, self.total_count)


def create_scheduler(configuration: PoiConfiguration) -> PoiEventScheduler:
    return PoiEventScheduler(
        configuration=configuration,
        total_count=0,
        touch_index=create_persistent_interval_index(),
        breach_index=create_persistent_breach_index(configuration),
        cursors=PersistentMap(),
        due=PersistentMap(),
    )


@dataclass
class _Mut:
    """A local mutable working copy of the persistent structures, committed into a
    fresh immutable scheduler only at the end of a successful advance."""

    touch_index: PersistentIntervalTouchIndex
    breach_index: PersistentBreachIndex
    cursors: PersistentMap[PoiLifecycleCursor]
    due: PersistentMap[frozenset[UUID]]
    ops: _SchedulerOps = field(default_factory=_SchedulerOps)

    def _unregister(self, record_id: UUID) -> None:
        # Registration state is derived from the stored cursor rather than a
        # parallel ``regs`` map: start_index / terminal / zone are all invariant
        # under fast_forward, so a lazily-stale stored cursor reports the exact
        # registration that is live in the indexes.
        cursor = self.cursors.get(record_id.int)
        if cursor is None:
            return
        if _in_touch(cursor):
            self.touch_index = self.touch_index.remove(record_id, cursor.zone_bottom)
            self.ops.touch_index_writes += 1
        if _in_breach(cursor):
            self.breach_index = self.breach_index.unregister(
                record_id, cursor.direction, cursor.zone_top, cursor.zone_bottom
            )
            self.ops.breach_index_writes += 1
        self.cursors = self.cursors.delete(record_id.int)
        self.ops.cursor_deletes += 1

    def _reregister(self, record_id: UUID, cursor: PoiLifecycleCursor) -> None:
        """Apply only the minimal index changes for this advance. The previous
        registration is read from the previously stored cursor (still present in
        ``self.cursors`` until the set below), so an unchanged registration writes
        NOTHING to the touch/breach indexes -- the old ``regs`` map (unchanged in
        92-97% of advances) is gone entirely. Only the cursor, which genuinely
        advanced this candle, is rewritten."""
        prev_cursor = self.cursors.get(record_id.int)
        prev_touch = _in_touch(prev_cursor) if prev_cursor is not None else False
        prev_breach = _in_breach(prev_cursor) if prev_cursor is not None else False
        nt = _in_touch(cursor)
        nb = _in_breach(cursor)
        zt = cursor.zone_top
        zb = cursor.zone_bottom
        if nt and not prev_touch:
            self.touch_index = self.touch_index.insert(record_id, zb, zt)
            self.ops.touch_index_writes += 1
        elif prev_touch and not nt:
            self.touch_index = self.touch_index.remove(record_id, zb)
            self.ops.touch_index_writes += 1
        if nb and not prev_breach:
            self.breach_index = self.breach_index.register(
                record_id, cursor.direction, zt, zb
            )
            self.ops.breach_index_writes += 1
        elif prev_breach and not nb:
            self.breach_index = self.breach_index.unregister(
                record_id, cursor.direction, zt, zb
            )
            self.ops.breach_index_writes += 1
        self.cursors = self.cursors.set(record_id.int, cursor)
        self.ops.cursor_writes += 1

    def _schedule_due(
        self, record_id: UUID, cursor: PoiLifecycleCursor, next_bar: int
    ) -> None:
        if _due_next(cursor):
            bucket = self.due.get(next_bar, frozenset())
            assert bucket is not None
            self.due = self.due.set(next_bar, bucket | {record_id})
            self.ops.due_writes += 1


def advance_scheduler(
    scheduler: PoiEventScheduler,
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    *,
    new_pois: Sequence[PoiSpec] = (),
    changed_pois: Sequence[PoiSpec] = (),
    removed_ids: Sequence[UUID] = (),
) -> PoiEventScheduler:
    """Advance the scheduler by exactly one appended candle (``candles[-1]``) plus
    its full-prefix ATR-14 value (``atr_values[-1]``). ``candles`` / ``atr_values``
    are the full visible prefix (needed to (re)build a new or changed POI's cursor
    from its own history). Transactional: a fresh scheduler is returned and the
    input one is never mutated."""
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
        touch_index=scheduler.touch_index,
        breach_index=scheduler.breach_index,
        cursors=scheduler.cursors,
        due=scheduler.due,
    )

    changed_ids = {spec.record_id for spec in changed_pois}
    removed_set = set(removed_ids)

    # 1. Removals and changed-POI teardown first (so their stale index entries
    #    never appear in this candle's wake queries).
    for rid in removed_set:
        mut._unregister(rid)
    for rid in changed_ids:
        mut._unregister(rid)

    # 2. Discover the wake set among the surviving registered cursors.
    touch_wake = mut.touch_index.overlaps(candle.low, candle.high)
    breach_wake = mut.breach_index.breach_wake_set(candle, atr)
    due_wake = scheduler.due.get(m, frozenset()) or frozenset()
    wake = set(touch_wake) | set(breach_wake) | set(due_wake)
    # due_wake may name POIs removed earlier this candle or already gone.
    wake = {rid for rid in wake if rid.int in mut.cursors}

    last_walks: dict[UUID, LifecycleWalkResult] = {}

    # 3. Advance each woken (surviving, pre-existing) cursor exactly once.
    for rid in wake:
        cursor = mut.cursors.get(rid.int)
        assert cursor is not None
        cursor = fast_forward_poi_cursor(cursor, m)
        cursor, walk = advance_poi_cursor(cursor, candle, atr, config)
        last_walks[rid] = walk
        mut._reregister(rid, cursor)
        mut._schedule_due(rid, cursor, next_bar)

    # 4. (Re)build new and changed POIs. A brand-new POI whose availability is at
    #    least the max availability of every candle seen has no eligible candle to
    #    start it — it is pre-start w.r.t. the whole prefix, so its cursor is
    #    constructed in O(1) (fresh + a pre-start fast-forward), exactly equal to
    #    feeding it every candle as a pre-start no-op. Otherwise (a changed POI, or
    #    the rare POI whose availability precedes an already-seen candle) the cursor
    #    is rebuilt from its own history (§9's bounded per-replacement rebuild).
    for spec in list(changed_pois) + list(new_pois):
        cursor = create_poi_lifecycle_cursor(
            spec.symbol,
            spec.timeframe,
            spec.record_id,
            spec.direction,
            spec.zone_top,
            spec.zone_bottom,
            spec.availability_time_utc,
        )
        is_new = spec.record_id not in changed_ids
        if is_new and spec.availability_time_utc >= new_max_availability:
            # Pre-start on-time POI: its walk is the empty pre-start walk, which the
            # read-time adapter reconstructs exactly, so no capture is needed.
            cursor = fast_forward_poi_cursor(cursor, next_bar)
        else:
            feed_walk: LifecycleWalkResult | None = None
            for idx in range(0, m + 1):
                cursor, feed_walk = advance_poi_cursor(
                    cursor, candles[idx], atr_values[idx], config
                )
            if feed_walk is not None:
                last_walks[spec.record_id] = feed_walk
        mut._reregister(spec.record_id, cursor)
        mut._schedule_due(spec.record_id, cursor, next_bar)

    # 5. Drop the consumed due bucket for this bar.
    new_due = mut.due.delete(m)

    return PoiEventScheduler(
        configuration=config,
        total_count=next_bar,
        touch_index=mut.touch_index,
        breach_index=mut.breach_index,
        cursors=mut.cursors,
        due=new_due,
        max_availability=new_max_availability,
        woken_ids=frozenset(wake),
        rebuilt=len(changed_ids) + len(new_pois),
        last_walks=last_walks,
        ops=mut.ops,
    )
