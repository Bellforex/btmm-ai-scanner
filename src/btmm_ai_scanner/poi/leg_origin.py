"""RC3 FINAL: ORDER BLOCK = ACTUAL LEG ORIGIN, with confirmed-POI immutability.

Author decisions (2026-09-17, final semantic lock):

1. **Leg identity** comes from the frozen P2 structure walk
   (``structure/transitions.run_structure_walk`` over the frozen P1 swings);
   no second swing or structure engine and no numeric threshold.

   A bullish leg is confirmed by a bullish structure break (BULLISH_BOS or
   BULLISH_CHOCH), which breaks one confirmed swing high. The leg departed from
   the most extreme (lowest) confirmed SWING_LOW whose pivot lies after that
   broken high and before the break candle: for a BOS the terminal of the
   pullback from the broken high, for a CHOCH the bottom of the bearish leg
   that ended. That swing is the leg **origin**; exact price ties go to the
   latest pivot (where the move actually departs). ``leg_id`` = the break.

   A BUY ORDER BLOCK is the earliest frozen raw OB formation (2.0 size rule,
   colours, close beyond origin extreme, Doji rule) whose origin or
   displacement candle is a pivot candle of that origin swing and that was
   complete by the break. At most one per leg. Every other raw formation --
   anchored on a later, higher swing low inside the leg, or on no swing at all
   -- stays BULLISH ENGULFING. SELL mirrors (highest SWING_HIGH between
   bearish breaks).

   Availability = the confirming break's availability (never before the
   formation, the origin swing's confirmation or the break itself).

2. **Immutability.** Once an ORDER BLOCK has been available at some prefix it
   exists forever with the source, geometry, type and availability it had
   when it first appeared. A later swing supersession that removes its origin
   swing or its break from a fresh recomputation never deletes it. It still
   ends through the normal lifecycle (mitigation / invalidation).

   Incremental replay locks every ORDER BLOCK the first time the gate
   produces it (availability = max(gated availability, that candle's
   availability)). The batch engine reproduces exactly that union over all
   prefixes: it replays the prefix swing sets with the frozen incremental swing
   primitives and only recomputes the structure walk on prefixes whose swing
   or swing-relationship inputs differ from the final set restricted to what
   was available; on every other prefix the gate output provably equals the
   final gate output restricted by availability.
"""

from __future__ import annotations

import bisect
import uuid
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.analyzer import (
    _atr_incremental_step,
    _AtrIncrementalState,
    _derive_confirmed_swing_candidates,
    _update_confirmation_trackers,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import (
    _WINDOW_RADIUS,
    ConfirmedSwing,
    ConfirmedSwingCandidate,
    _find_single_candle_pivots,
    _merge_adjacent_plateaus,
    _Pivot,
    _supersede_same_direction_runs,
)
from btmm_ai_scanner.poi.authority import REVERSAL_TYPES
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.order_blocks import OrderBlockCandidate
from btmm_ai_scanner.poi.structural_role import StructuralRole
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    SwingRelationshipLabel,
)
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import (
    StructureWalkResult,
    run_structure_walk,
)

__all__ = [
    "ContextDecision",
    "ContextReason",
    "LegOriginFrontier",
    "StructuralContext",
    "StructuralRoleFact",
    "advance_leg_origin_frontier",
    "immutable_leg_origin_order_blocks",
    "immutable_structure_gate",
    "iter_prefix_swing_candidates",
    "leg_origin_order_blocks",
    "structural_role_of",
    "structure_context_decisions",
]

_STRUCTURE_CONFIGURATION = StructureConfiguration()
_OB_TYPES = frozenset({PoiType.BUY_ORDER_BLOCK, PoiType.SELL_ORDER_BLOCK})


def _formation_key(formation: OrderBlockCandidate) -> tuple[Any, ...]:
    return (formation.poi_type, formation.source_candle_record_ids)


# ---------------------------------------------------------------------------
# The rule (pure function of candles, swings, raw formations and candidates)
# ---------------------------------------------------------------------------


class ContextReason(StrEnum):
    MAPPED_TREND_ALIGNED = "MAPPED_TREND_ALIGNED"
    MAPPED_REVERSAL_CONTEXT = "MAPPED_REVERSAL_CONTEXT"
    CONTEXT_REJECT_COUNTER_TREND = "CONTEXT_REJECT_COUNTER_TREND"
    CONTEXT_REJECT_NEUTRAL = "CONTEXT_REJECT_NEUTRAL"
    #: RC5 only: the pattern is real but sits in mid-leg texture rather than at
    #: a structural decision point. Not a refusal of a late confirmation -- a
    #: candidate rejected on this prefix may earn a role on a later one.
    CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN = "CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN"


#: Precedence when a candidate's source candles touch several used swings.
_ROLE_RANK: dict[StructuralRole, int] = {
    StructuralRole.LEG_ORIGIN: 0,
    StructuralRole.SWING_HIGH_ORIGIN: 1,
    StructuralRole.SWING_LOW_ORIGIN: 1,
    StructuralRole.PULLBACK_HIGH: 2,
    StructuralRole.PULLBACK_LOW: 2,
}


@dataclass(frozen=True)
class StructuralRoleFact:
    """A swing's meaning to the walk, and the availability from which that
    meaning exists. ``since`` is what makes the RC5 gate causal: it is always a
    real structural event's ``availability_time_utc``, never a later prefix's
    hindsight."""

    role: StructuralRole
    since: datetime
    origin_swing_id: Any
    broken_swing_id: Any | None
    break_candle_id: Any | None

    @property
    def rank(self) -> int:
        return _ROLE_RANK[self.role]


@dataclass(frozen=True)
class ContextDecision:
    candidate: Any
    reason: ContextReason
    structure_direction: StructureDirection
    mapped: Any | None  # the mapped candidate (reversal: re-timed to its break)
    #: RC5 provenance, set only where the gate actually resolved it -- i.e. on
    #: MAPPED_REVERSAL_CONTEXT, where a specific break named a specific origin.
    #: These are the existing frozen identifiers, never fabricated ones.
    origin_swing_id: Any | None = None
    broken_swing_id: Any | None = None
    break_candle_id: Any | None = None
    structural_role: StructuralRole | None = None


@dataclass(frozen=True, eq=False)
class StructuralContext:
    """What the frozen structure walk already knows, surfaced for RC5.

    ``_gate`` resolves all of this to place ORDER BLOCKS and to map reversal
    candidates, then throws it away. RC5 needs the same facts to decide whether
    *any* reversal candidate sits at a decision origin, so the gate now returns
    them instead. Nothing here is recomputed and no identifier is invented:
    every id is a frozen swing ``record_id`` or candle ``record_id``.

    ``eq=False`` keeps :class:`LegOriginFrontier` hashable despite the maps.

    CAUSALITY WARNING. Every entry here is established by a structure *break*,
    so it is only true from that break's ``availability_time_utc`` onwards. The
    frontier's context is the state of its own prefix and is therefore safe to
    read directly. The batch gate returns the FINAL prefix's context, which
    knows about breaks that had not happened yet when an earlier candidate
    formed -- reading it to promote an earlier candidate would be look-ahead.
    Batch consumers must go through the prefix replay in
    ``immutable_structure_gate``, exactly as ORDER BLOCKS already do.
    """

    #: pivot candle id -> the origin swing a confirmed break departed from
    leg_origin_candle_ids: dict[Any, Any]
    #: origin swing id -> the break candle that confirmed its leg (the leg id)
    leg_id_by_origin_swing: dict[Any, Any]
    #: origin swing id -> the swing that break broke
    broken_swing_by_origin: dict[Any, Any]
    #: pivot candle id -> confirmed swing id, per side
    swing_high_candle_ids: dict[Any, Any]
    swing_low_candle_ids: dict[Any, Any]
    #: RC5: what the walk makes of each swing it actually uses, and the
    #: availability from which that became true. Empty outside RC5 callers is
    #: not a thing -- it is always built; only the gate consults it.
    role_by_swing: dict[Any, StructuralRoleFact]
    #: confirmed swings the walk broke -- price actually took them
    broken_swing_ids: frozenset[Any]
    #: everything the walk did not break. NOT a promotion signal on its own:
    #: in any trending leg most swings are unbroken texture.
    unbroken_swing_ids: frozenset[Any]
    #: the walk's live protected / weak levels at this prefix -- the unbroken
    #: swings that currently define structure, as opposed to the rest
    live_structure_swing_ids: frozenset[Any]

    @classmethod
    def empty(cls) -> StructuralContext:
        return cls({}, {}, {}, {}, {}, {}, frozenset(), frozenset(), frozenset())


def _structural_context(
    swings: tuple[ConfirmedSwing, ...],
    walk: StructureWalkResult,
    legs: Sequence[tuple[Any, ConfirmedSwing, PoiDirection]],
) -> StructuralContext:
    """Everything the walk resolved on THIS prefix, with the availability from
    which each fact became true. Built once per ``_gate`` call so that batch and
    incremental see identical structure for identical inputs."""
    leg_origin_candle_ids: dict[Any, Any] = {}
    leg_id_by_origin_swing: dict[Any, Any] = {}
    broken_swing_by_origin: dict[Any, Any] = {}
    role_by_swing: dict[Any, StructuralRoleFact] = {}

    # The first break to name a swing owns it; later breaks that reach back to
    # the same swing do not re-date the leg.
    for transition, origin, _direction in legs:
        if origin.record_id in leg_id_by_origin_swing:
            continue
        leg_id_by_origin_swing[origin.record_id] = transition.break_candle_id
        broken_swing_by_origin[origin.record_id] = transition.broken_swing_id
        for candle_id in origin.pivot_candle_record_ids:
            leg_origin_candle_ids.setdefault(candle_id, origin.record_id)
        role_by_swing[origin.record_id] = StructuralRoleFact(
            StructuralRole.LEG_ORIGIN,
            transition.availability_time_utc,
            origin.record_id,
            transition.broken_swing_id,
            transition.break_candle_id,
        )

    by_id = {s.record_id: s for s in swings}
    # A swing a break TOOK held real liquidity. Available from that break.
    for transition in walk.transitions:
        broken = by_id.get(transition.broken_swing_id)
        if broken is None or broken.record_id in role_by_swing:
            continue
        role_by_swing[broken.record_id] = StructuralRoleFact(
            StructuralRole.SWING_HIGH_ORIGIN
            if broken.swing_type == SwingType.SWING_HIGH
            else StructuralRole.SWING_LOW_ORIGIN,
            transition.availability_time_utc,
            broken.record_id,
            broken.record_id,
            transition.break_candle_id,
        )

    # The levels the walk DEFENDS -- unbroken, but load-bearing, unlike the rest
    # of the unbroken swings, which are leg texture.
    #
    # MONOTONICITY. "Currently protected" is not usable here: the walk stops
    # defending a level when structure moves on, so a role read from the final
    # prefix could be ABSENT where an earlier prefix had it. Every other part of
    # this engine relies on the final gate output being a superset of every
    # prefix's -- that is how ``immutable_structure_gate`` avoids replaying the
    # walk on most bars -- and a lapsing role silently breaks it, which showed
    # up as the M45 B2S being locked at an arbitrary much later bar.
    #
    # A swing the walk EVER defended was meaningful at the time it defended it,
    # and this engine never retracts what was once true. Each transition records
    # the level it protected and the weak level it armed, so the whole history
    # is available from the final walk and accumulates monotonically. ``since``
    # stays the moment that fact became true, so availability stays causal.
    defended: list[tuple[Any, datetime]] = []
    for transition in walk.transitions:
        defended.append(
            (transition.protected_swing_id, transition.availability_time_utc)
        )
        if transition.weak_swing_id is not None:
            defended.append(
                (transition.weak_swing_id, transition.availability_time_utc)
            )
    for swing in (
        walk.protected_high,
        walk.protected_low,
        walk.weak_high,
        walk.weak_low,
    ):
        if swing is not None:
            defended.append((swing.record_id, swing.meaningful_confirmation_time_utc))

    for swing_id, since in defended:
        swing = by_id.get(swing_id)
        if swing is None or swing_id in role_by_swing:
            continue
        role_by_swing[swing_id] = StructuralRoleFact(
            StructuralRole.PULLBACK_HIGH
            if swing.swing_type == SwingType.SWING_HIGH
            else StructuralRole.PULLBACK_LOW,
            max(since, swing.meaningful_confirmation_time_utc),
            swing_id,
            None,
            None,
        )

    swing_high_candle_ids: dict[Any, Any] = {}
    swing_low_candle_ids: dict[Any, Any] = {}
    for swing in swings:
        side = (
            swing_high_candle_ids
            if swing.swing_type == SwingType.SWING_HIGH
            else swing_low_candle_ids
        )
        for candle_id in swing.pivot_candle_record_ids:
            side.setdefault(candle_id, swing.record_id)

    broken_swing_ids = frozenset(t.broken_swing_id for t in walk.transitions)
    return StructuralContext(
        leg_origin_candle_ids,
        leg_id_by_origin_swing,
        broken_swing_by_origin,
        swing_high_candle_ids,
        swing_low_candle_ids,
        role_by_swing,
        broken_swing_ids,
        frozenset(s.record_id for s in swings) - broken_swing_ids,
        frozenset(
            swing_id
            for swing_id, fact in role_by_swing.items()
            if fact.role in (StructuralRole.PULLBACK_HIGH, StructuralRole.PULLBACK_LOW)
        ),
    )


def _rc5_blocks(
    candidate: Any, context: StructuralContext, rc5_structural_origin: bool
) -> bool:
    """Would the RC5 structural-origin gate refuse this candidate on the prefix
    ``context`` describes? Used by the two fast paths, which skip the walk
    because structure is unchanged and so may read their carried context."""
    return (
        rc5_structural_origin
        and candidate.poi_type in REVERSAL_TYPES
        and structural_role_of(candidate, context) is None
    )


def structural_role_of(
    candidate: Any, context: StructuralContext
) -> StructuralRoleFact | None:
    """The candidate's structural role at ``context``'s prefix, or ``None`` if
    it is mid-leg texture.

    The candidate must touch a swing **on the side it claims to defend** -- a
    bullish reversal at a swing high is not a bullish decision point -- and that
    swing must be one the walk actually uses. Looking the candle up in only the
    matching-side pivot map is what enforces the side.
    """
    pivots = (
        context.swing_low_candle_ids
        if candidate.direction is PoiDirection.BULLISH
        else context.swing_high_candle_ids
    )
    best: StructuralRoleFact | None = None
    # The formation span, where a detector records one, is the candidate's own
    # extent -- for B2S/S2B the source candle through the candle that confirmed
    # the reversal. The structural extreme that COMPLETES a reversal is often
    # carried by a later bar of the formation rather than by its source candle,
    # so both are consulted. Families that record no span fall back to their
    # source candles exactly as before.
    span: tuple[Any, ...] = getattr(candidate, "formation_span_candle_record_ids", ())
    for candle_id in (*candidate.source_candle_record_ids, *span):
        swing_id = pivots.get(candle_id)
        if swing_id is None:
            continue
        fact = context.role_by_swing.get(swing_id)
        if fact is not None and (best is None or fact.rank < best.rank):
            best = fact
    return best


def _direction_timeline(
    walk: StructureWalkResult, relationships: Sequence[Any]
) -> tuple[list[datetime], list[StructureDirection]]:
    """Structure direction as the frozen walk sets it: the first HH+HL / LH+LL
    relationship pair (walk bootstrap, same event order), then each break's
    direction_after at its availability. Direction at t = last change <= t."""
    times: list[datetime] = []
    dirs: list[StructureDirection] = []
    latest: dict[SwingType, Any] = {}
    for r in sorted(
        relationships,
        key=lambda r: (
            r.availability_time_utc,
            r.current_swing.pivot_bar_index,
            str(r.current_swing_record_id),
        ),
    ):
        latest[r.swing_type] = r.label
        hi = latest.get(SwingType.SWING_HIGH)
        lo = latest.get(SwingType.SWING_LOW)
        if (
            hi == SwingRelationshipLabel.HIGHER_HIGH
            and lo == SwingRelationshipLabel.HIGHER_LOW
        ):
            times.append(r.availability_time_utc)
            dirs.append(StructureDirection.BULLISH)
            break
        if (
            hi == SwingRelationshipLabel.LOWER_HIGH
            and lo == SwingRelationshipLabel.LOWER_LOW
        ):
            times.append(r.availability_time_utc)
            dirs.append(StructureDirection.BEARISH)
            break
    for transition in walk.transitions:
        times.append(transition.availability_time_utc)
        dirs.append(transition.direction_after)
    return times, dirs


def _direction_at(
    timeline: tuple[list[datetime], list[StructureDirection]], t: datetime
) -> StructureDirection:
    times, dirs = timeline
    k = bisect.bisect_right(times, t)
    return dirs[k - 1] if k else StructureDirection.UNDETERMINED


def _classify_aligned(candidate: Any, direction: StructureDirection) -> ContextReason:
    if direction is StructureDirection.UNDETERMINED:
        return ContextReason.CONTEXT_REJECT_NEUTRAL
    bullish = candidate.direction is PoiDirection.BULLISH
    if (direction is StructureDirection.BULLISH) == bullish:
        return ContextReason.MAPPED_TREND_ALIGNED
    return ContextReason.CONTEXT_REJECT_COUNTER_TREND


def _gate(
    formations: Sequence[OrderBlockCandidate],
    candles: Sequence[NormalizedCandle],
    swings: tuple[ConfirmedSwing, ...],
    candidates: Sequence[Any] = (),
    *,
    rc5_structural_origin: bool = False,
) -> tuple[
    tuple[OrderBlockCandidate, ...],
    StructureWalkResult,
    tuple[ContextDecision, ...],
    tuple[list[datetime], list[StructureDirection]],
    StructuralContext,
]:
    relationships = detect_swing_relationships(swings, _STRUCTURE_CONFIGURATION)
    walk = run_structure_walk(tuple(candles), swings, relationships)
    timeline = _direction_timeline(walk, relationships)
    by_candle: dict[tuple[PoiDirection, object], list[OrderBlockCandidate]] = {}
    for formation in formations:
        for candle_id in formation.source_candle_record_ids:
            by_candle.setdefault((formation.direction, candle_id), []).append(formation)

    by_id = {s.record_id: s for s in swings}

    # ---- pass 1: the leg each break confirmed, and where it departed from --
    # Frozen RC3 rule, unchanged; hoisted out of the placement loop so the
    # structural roles below can be built before candidates are classified.
    legs: list[tuple[Any, ConfirmedSwing, PoiDirection]] = []
    for transition in walk.transitions:
        bullish = transition.direction_after == StructureDirection.BULLISH
        broken = by_id[transition.broken_swing_id]
        want = SwingType.SWING_LOW if bullish else SwingType.SWING_HIGH
        pool = [
            s
            for s in swings
            if s.swing_type == want
            and s.pivot_start_time_utc > broken.pivot_end_time_utc
            and s.pivot_end_time_utc < transition.event_time_utc
            and s.meaningful_confirmation_time_utc <= transition.availability_time_utc
        ]
        if not pool:
            continue
        origin = min(
            pool,
            key=lambda s: (
                s.pivot_price if bullish else -s.pivot_price,
                -s.pivot_start_time_utc.timestamp(),
            ),
        )
        legs.append(
            (
                transition,
                origin,
                PoiDirection.BULLISH if bullish else PoiDirection.BEARISH,
            )
        )

    context = _structural_context(swings, walk, legs)

    # ---- pass 2: classify each candidate on this prefix's structure --------
    decisions: dict[tuple[Any, ...], ContextDecision] = {}
    roles: dict[tuple[Any, ...], StructuralRoleFact | None] = {}
    counter: dict[PoiDirection, list[Any]] = {}
    for candidate in candidates:
        key = _formation_key(candidate)
        structure_dir = _direction_at(timeline, candidate.availability_time_utc)
        reason = _classify_aligned(candidate, structure_dir)
        fact: StructuralRoleFact | None = None
        if rc5_structural_origin and candidate.poi_type in REVERSAL_TYPES:
            fact = structural_role_of(candidate, context)
            roles[key] = fact
            if fact is None:
                # RC5: a reversal pattern in mid-leg texture is not a POI at
                # all. It may still earn a role on a later prefix.
                decisions[key] = ContextDecision(
                    candidate,
                    ContextReason.CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN,
                    structure_dir,
                    None,
                )
                continue
        mapped = candidate if reason is ContextReason.MAPPED_TREND_ALIGNED else None
        if (
            mapped is not None
            and fact is not None
            and fact.since > (candidate.availability_time_utc)
        ):
            # Detected at its own source time, usable only once the break that
            # gives it structural meaning has happened. Source time, source
            # candles, geometry and identity are untouched -- only availability
            # moves. See ``ContextReason.CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN``.
            mapped = candidate._replace(
                confirmation_time_utc=fact.since, availability_time_utc=fact.since
            )
        decisions[key] = ContextDecision(
            candidate,
            reason,
            structure_dir,
            mapped,
            origin_swing_id=fact.origin_swing_id if fact else None,
            broken_swing_id=fact.broken_swing_id if fact else None,
            break_candle_id=fact.break_candle_id if fact else None,
            structural_role=fact.role if fact else None,
        )
        if reason is ContextReason.CONTEXT_REJECT_COUNTER_TREND:
            counter.setdefault(candidate.direction, []).append(candidate)

    # ---- pass 3: reversal context, then ORDER BLOCK placement -------------
    gated: list[OrderBlockCandidate] = []
    used: set[object] = set()
    for transition, origin, direction in legs:
        # Reversal context: this break confirms a leg departing from `origin`.
        # A counter-trend candidate of the leg's direction formed inside that leg
        # (source at or after the origin pivot, complete by the break) belongs to
        # the confirmed impulse; it maps at the break. Earlier ones stay raw.
        for c in counter.get(direction, ()):
            key = _formation_key(c)
            if (
                decisions[key].mapped is not None
                or c.candidate_event_time_utc < origin.pivot_start_time_utc
                or c.availability_time_utc > transition.availability_time_utc
            ):
                continue
            fact = roles.get(key)
            available = max(
                c.availability_time_utc,
                origin.meaningful_confirmation_time_utc,
                transition.availability_time_utc,
                *((fact.since,) if fact is not None else ()),
            )
            decisions[key] = ContextDecision(
                c,
                ContextReason.MAPPED_REVERSAL_CONTEXT,
                decisions[key].structure_direction,
                c._replace(
                    confirmation_time_utc=available, availability_time_utc=available
                ),
                origin_swing_id=origin.record_id,
                broken_swing_id=transition.broken_swing_id,
                break_candle_id=transition.break_candle_id,
                structural_role=fact.role if fact else None,
            )
        if origin.record_id in used:
            continue
        used.add(origin.record_id)
        anchored = {
            _formation_key(f): f
            for candle_id in origin.pivot_candle_record_ids
            for f in by_candle.get((direction, candle_id), ())
            if f.availability_time_utc <= transition.availability_time_utc
        }
        if not anchored:
            continue
        first = min(
            anchored.values(),
            key=lambda f: (
                f.candidate_event_time_utc,
                tuple(map(str, f.source_candle_record_ids)),
            ),
        )
        available = max(
            first.availability_time_utc,
            origin.meaningful_confirmation_time_utc,
            transition.availability_time_utc,
        )
        gated.append(
            first._replace(
                confirmation_time_utc=available, availability_time_utc=available
            )
        )
    return tuple(gated), walk, tuple(decisions.values()), timeline, context


def leg_origin_order_blocks(
    formations: Iterable[OrderBlockCandidate],
    candles: Sequence[NormalizedCandle],
    confirmed_swings: Iterable[ConfirmedSwing],
) -> tuple[OrderBlockCandidate, ...]:
    """The leg-origin gate on ONE set of inputs (no immutability)."""
    return _gate(tuple(formations), candles, tuple(confirmed_swings))[0]


def structure_context_decisions(
    candidates: Iterable[Any],
    candles: Sequence[NormalizedCandle],
    confirmed_swings: Iterable[ConfirmedSwing],
    *,
    rc5_structural_origin: bool = False,
) -> tuple[ContextDecision, ...]:
    """Context decisions on ONE set of inputs (audit; no immutability)."""
    return _gate(
        (),
        candles,
        tuple(confirmed_swings),
        tuple(candidates),
        rc5_structural_origin=rc5_structural_origin,
    )[2]


# ---------------------------------------------------------------------------
# Prefix swing replay (frozen incremental primitives of domain/analyzer.py)
# ---------------------------------------------------------------------------


def iter_prefix_swing_candidates(
    candles: Sequence[NormalizedCandle],
    configuration: MarketMeasurementConfiguration,
) -> Iterator[tuple[int, tuple[ConfirmedSwingCandidate, ...]]]:
    """Yield ``(index, detect_confirmed_swings(candles[: index + 1]))`` for
    every prefix, advanced with the same incremental swing primitives the
    measurement replay uses (differentially tested against the batch
    detector)."""
    atr_state = _AtrIncrementalState()
    atr_values: list[Any] = []
    raw: list[_Pivot] = []
    pivots: list[_Pivot] = []
    trackers: dict[Any, Any] = {}
    so_far: list[NormalizedCandle] = []
    chain: tuple[tuple[Any, ...], ...] | None = None
    result: tuple[ConfirmedSwingCandidate, ...] = ()
    for index, candle in enumerate(candles):
        so_far.append(candle)
        atr_state, atr_value = _atr_incremental_step(
            atr_state, candle, configuration.atr_period
        )
        atr_values.append(atr_value)
        grew = False
        if index >= 2 * _WINDOW_RADIUS:
            start = index - 2 * _WINDOW_RADIUS
            for pivot in _find_single_candle_pivots(
                so_far[start:], atr_values[start:], configuration
            ):
                raw.append(
                    _Pivot(
                        pivot.start_index + start,
                        pivot.end_index + start,
                        pivot.swing_type,
                        pivot.price,
                        pivot.reference_atr,
                        pivot.tie_tolerance,
                    )
                )
                grew = True
        if grew:
            pivots = _supersede_same_direction_runs(_merge_adjacent_plateaus(list(raw)))
        trackers = _update_confirmation_trackers(
            trackers, pivots, so_far, configuration
        )
        # The confirmed chain, exactly as _derive_confirmed_swing_candidates
        # walks it; the full candidates are rebuilt only when it changes.
        n = len(so_far)
        last_type = None
        keys: list[tuple[Any, ...]] = []
        for pivot in pivots:
            if pivot.end_index + _WINDOW_RADIUS >= n or pivot.swing_type == last_type:
                continue
            tracker = trackers[(pivot.start_index, pivot.end_index, pivot.swing_type)]
            if tracker.confirmed_at_index is None:
                continue
            keys.append(
                (pivot, tracker.confirmed_at_index, tracker.confirmation_excursion)
            )
            last_type = pivot.swing_type
        if chain is None or tuple(keys) != chain:
            chain = tuple(keys)
            result = _derive_confirmed_swing_candidates(
                pivots, trackers, so_far, configuration
            )
        yield index, result


def _swing_key(swing: Any) -> tuple[Any, ...]:
    return (
        swing.swing_type,
        tuple(swing.pivot_candle_record_ids),
        swing.confirmation_candle_id,
        swing.pivot_price,
        swing.pivot_bar_index,
        swing.meaningful_confirmation_time_utc,
        swing.pivot_reference_atr,
    )


def _as_swing(candidate: ConfirmedSwingCandidate) -> ConfirmedSwing:
    key = "|".join(map(str, _swing_key(candidate)))
    record_id = uuid.uuid5(uuid.NAMESPACE_OID, key)
    return ConfirmedSwing.model_construct(
        record_id=record_id,
        content_fingerprint="0" * 64,
        availability_time_utc=candidate.meaningful_confirmation_time_utc,
        **candidate._asdict(),
    )


def _relationship_keys(
    swings: tuple[Any, ...], until: datetime | None
) -> tuple[tuple[Any, ...], ...]:
    keyed = {s.record_id: _swing_key(s) for s in swings}
    return tuple(
        (
            r.swing_type,
            r.label,
            keyed[r.current_swing_record_id],
            keyed[r.predecessor_swing_record_id],
            r.availability_time_utc,
        )
        for r in detect_swing_relationships(swings, _STRUCTURE_CONFIGURATION)
        if until is None or r.availability_time_utc <= until
    )


def immutable_structure_gate(
    formations: Iterable[OrderBlockCandidate],
    candidates: Iterable[Any],
    candles: Sequence[NormalizedCandle],
    confirmed_swings: Iterable[ConfirmedSwing],
    measurement_configuration: MarketMeasurementConfiguration,
    *,
    rc5_structural_origin: bool = False,
) -> tuple[tuple[OrderBlockCandidate, ...], tuple[Any, ...], StructuralContext]:
    """Batch ORDER BLOCKs and context-mapped candidates = the union, over every
    prefix, of the structure gate on that prefix, each snapshotted when it first
    appears. Identical to what ``advance_leg_origin_frontier`` has locked after
    the last candle. The third element is the final-prefix structural context,
    for RC5 promotion decisions (see :class:`StructuralContext`)."""
    formations = tuple(formations)
    candidates = tuple(candidates)
    final_swings = tuple(confirmed_swings)
    final_gated, _walk, final_decisions, _timeline, final_context = _gate(
        formations,
        candles,
        final_swings,
        candidates,
        rc5_structural_origin=rc5_structural_origin,
    )
    final_sorted = sorted(
        [*final_gated, *(d.mapped for d in final_decisions if d.mapped is not None)],
        key=lambda f: (
            f.availability_time_utc,
            f.poi_type.value,
            tuple(map(str, f.source_candle_record_ids)),
        ),
    )
    candidates_by_time = sorted(
        candidates,
        key=lambda c: (
            c.availability_time_utc,
            c.poi_type.value,
            tuple(map(str, c.source_candle_record_ids)),
        ),
    )
    final_by_conf = sorted(
        final_swings, key=lambda s: (s.meaningful_confirmation_time_utc, _swing_key(s))
    )
    final_relationships = _relationship_keys(final_swings, None)

    locked: dict[tuple[Any, ...], Any] = {}
    order: list[tuple[Any, ...]] = []

    def lock(candidate: Any, now: datetime) -> None:
        key = _formation_key(candidate)
        if key in locked:
            return
        available = max(candidate.availability_time_utc, now)
        if available != candidate.availability_time_utc:
            candidate = candidate._replace(
                confirmation_time_utc=available, availability_time_utc=available
            )
        locked[key] = candidate
        order.append(key)

    key_text: dict[Any, str] = {}
    built: dict[Any, ConfirmedSwing] = {}

    def _cached_swing(candidate: ConfirmedSwingCandidate) -> ConfirmedSwing:
        swing = built.get(candidate)
        if swing is None:
            swing = built[candidate] = _as_swing(candidate)
            key_text[candidate] = "|".join(map(str, _swing_key(candidate)))
        return swing

    final_text = ["|".join(map(str, _swing_key(s))) for s in final_by_conf]
    walked: StructureWalkResult | None = None
    walked_timeline: tuple[list[datetime], list[StructureDirection]] = ([], [])
    prefix: tuple[ConfirmedSwingCandidate, ...] = ()
    prefix_swings: tuple[ConfirmedSwing, ...] = ()
    prefix_keys: list[str] = []
    prefix_relationships: tuple[tuple[Any, ...], ...] = ()
    relationships_by_time = sorted(
        range(len(final_relationships)), key=lambda i: final_relationships[i][4]
    )
    swing_pointer = 0
    relationship_pointer = 0
    gated_pointer = 0
    candidate_pointer = 0
    diverged = False
    for index, current in iter_prefix_swing_candidates(
        candles, measurement_configuration
    ):
        now = candles[index].availability_time_utc
        arrived: list[Any] = []
        while (
            candidate_pointer < len(candidates_by_time)
            and candidates_by_time[candidate_pointer].availability_time_utc <= now
        ):
            arrived.append(candidates_by_time[candidate_pointer])
            candidate_pointer += 1
        dirty = False
        if current is not prefix and current != prefix:
            prefix = current
            prefix_swings = tuple(_cached_swing(c) for c in prefix)
            prefix_keys = sorted(key_text[c] for c in prefix)
            prefix_relationships = _relationship_keys(prefix_swings, None)
            walked = None
            dirty = True
        while (
            swing_pointer < len(final_by_conf)
            and final_by_conf[swing_pointer].meaningful_confirmation_time_utc <= now
        ):
            swing_pointer += 1
            dirty = True
        while (
            relationship_pointer < len(relationships_by_time)
            and final_relationships[relationships_by_time[relationship_pointer]][4]
            <= now
        ):
            relationship_pointer += 1
            dirty = True
        if dirty:
            diverged = prefix_keys != sorted(
                final_text[i] for i in range(swing_pointer)
            ) or prefix_relationships != tuple(
                r for r in final_relationships if r[4] <= now
            )
        if diverged:
            # Same swing inputs and no possible break on this close: the gate
            # output cannot change except for candidates arriving now, which
            # are classified on the unchanged structure (see the frontier).
            if walked is None or _may_break(walked, candles[index].close):
                gated, walked, decisions, walked_timeline, walked_context = _gate(
                    tuple(f for f in formations if f.availability_time_utc <= now),
                    candles[: index + 1],
                    prefix_swings,
                    candidates_by_time[:candidate_pointer],
                    rc5_structural_origin=rc5_structural_origin,
                )
                for candidate in gated:
                    lock(candidate, now)
                for decision in decisions:
                    if decision.mapped is not None:
                        lock(decision.mapped, now)
            else:
                for candidate in arrived:
                    reason = _classify_aligned(
                        candidate,
                        _direction_at(walked_timeline, candidate.availability_time_utc),
                    )
                    if reason is not ContextReason.MAPPED_TREND_ALIGNED:
                        continue
                    # Structure is unchanged on this prefix, so the last
                    # walked context is this prefix's context.
                    if _rc5_blocks(candidate, walked_context, rc5_structural_origin):
                        continue
                    lock(candidate, now)
            continue
        walked = None
        while (
            gated_pointer < len(final_sorted)
            and final_sorted[gated_pointer].availability_time_utc <= now
        ):
            gated_pointer += 1
        for candidate in final_sorted[:gated_pointer]:
            lock(candidate, now)
    if sorted(final_text) != prefix_keys:
        raise ValueError(
            "confirmed swings do not match the measurement configuration used"
            " to replay their prefixes"
        )
    obs = tuple(locked[k] for k in order if k[0] in _OB_TYPES)
    mapped = tuple(locked[k] for k in order if k[0] not in _OB_TYPES)
    return obs, mapped, final_context


def immutable_leg_origin_order_blocks(
    formations: Iterable[OrderBlockCandidate],
    candles: Sequence[NormalizedCandle],
    confirmed_swings: Iterable[ConfirmedSwing],
    measurement_configuration: MarketMeasurementConfiguration,
) -> tuple[OrderBlockCandidate, ...]:
    """ORDER BLOCKs only (no context candidates)."""
    return immutable_structure_gate(
        formations, (), candles, confirmed_swings, measurement_configuration
    )[0]


# ---------------------------------------------------------------------------
# Incremental replay frontier
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LegOriginFrontier:
    swing_signature: tuple[Any, ...] = ()
    walk: StructureWalkResult | None = None
    timeline: tuple[list[datetime], list[StructureDirection]] = ([], [])
    locked: tuple[OrderBlockCandidate, ...] = ()
    locked_keys: frozenset[tuple[Any, ...]] = frozenset()
    candidates: tuple[Any, ...] = ()
    mapped: tuple[Any, ...] = ()
    mapped_keys: frozenset[tuple[Any, ...]] = frozenset()
    newly_mapped: tuple[Any, ...] = ()
    #: the structure facts of the last walk, reused verbatim on the fast path
    #: (where nothing structural changed, so nothing in here can have moved)
    context: StructuralContext = field(default_factory=StructuralContext.empty)


def _may_break(walk: StructureWalkResult | None, close: Any) -> bool:
    if walk is None:
        return False
    if walk.direction == StructureDirection.BULLISH:
        return (
            walk.protected_low is not None and close < walk.protected_low.pivot_price
        ) or (walk.weak_high is not None and close > walk.weak_high.pivot_price)
    if walk.direction == StructureDirection.BEARISH:
        return (
            walk.protected_high is not None and close > walk.protected_high.pivot_price
        ) or (walk.weak_low is not None and close < walk.weak_low.pivot_price)
    return False


def advance_leg_origin_frontier(
    state: LegOriginFrontier,
    formations: tuple[OrderBlockCandidate, ...],
    candles: Sequence[NormalizedCandle],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    new_candidates: Sequence[Any] = (),
    *,
    rc5_structural_origin: bool = False,
) -> LegOriginFrontier:
    """Lock the ORDER BLOCKs and context-mapped candidates the gate produces on
    this prefix. The structure walk is recomputed only when the swing inputs
    changed or the newest close can trigger a break of the current protected /
    weak level; otherwise no transition can appear, the direction timeline is
    unchanged, and only the candidates arriving on this candle are classified."""
    signature = tuple((s.record_id, s.content_fingerprint) for s in confirmed_swings)
    candle = candles[-1]
    now = candle.availability_time_utc
    all_candidates = (
        (*state.candidates, *new_candidates) if new_candidates else state.candidates
    )
    mapped = list(state.mapped)
    mapped_keys = set(state.mapped_keys)
    newly: list[Any] = []

    def lock_candidate(candidate: Any) -> None:
        key = _formation_key(candidate)
        if key in mapped_keys:
            return
        available = max(candidate.availability_time_utc, now)
        if available != candidate.availability_time_utc:
            candidate = candidate._replace(
                confirmation_time_utc=available, availability_time_utc=available
            )
        mapped.append(candidate)
        newly.append(candidate)
        mapped_keys.add(key)

    if signature == state.swing_signature and not _may_break(state.walk, candle.close):
        for candidate in new_candidates:
            reason = _classify_aligned(
                candidate,
                _direction_at(state.timeline, candidate.availability_time_utc),
            )
            if reason is not ContextReason.MAPPED_TREND_ALIGNED:
                continue
            # Nothing structural changed, so the carried context IS this
            # prefix's context -- no walk needed and no look-ahead possible.
            if _rc5_blocks(candidate, state.context, rc5_structural_origin):
                continue
            lock_candidate(candidate)
        return LegOriginFrontier(
            state.swing_signature,
            state.walk,
            state.timeline,
            state.locked,
            state.locked_keys,
            all_candidates,
            tuple(mapped) if newly else state.mapped,
            frozenset(mapped_keys) if newly else state.mapped_keys,
            tuple(newly),
            state.context,
        )
    gated, walk, decisions, timeline, context = _gate(
        formations,
        candles,
        confirmed_swings,
        all_candidates,
        rc5_structural_origin=rc5_structural_origin,
    )
    locked = list(state.locked)
    keys = set(state.locked_keys)
    for candidate in gated:
        key = _formation_key(candidate)
        if key in keys:
            continue
        available = max(candidate.availability_time_utc, now)
        locked.append(
            candidate._replace(
                confirmation_time_utc=available, availability_time_utc=available
            )
        )
        keys.add(key)
    for decision in decisions:
        if decision.mapped is not None:
            lock_candidate(decision.mapped)
    return LegOriginFrontier(
        signature,
        walk,
        timeline,
        tuple(locked),
        frozenset(keys),
        all_candidates,
        tuple(mapped),
        frozenset(mapped_keys),
        tuple(newly),
        context,
    )
