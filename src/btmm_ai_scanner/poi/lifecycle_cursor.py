"""A6-B1-A: exact resumable POI lifecycle cursor.

``run_poi_lifecycle`` (the batch oracle, unchanged) re-walks ``candles[anchor:]``
on every candle. This module reproduces it exactly, one appended candle at a
time, without any unbounded history-tail replay.

Design — bounded-suffix replay. The batch outer loop only ever moves its index
forward and, at each breach, inspects a bounded reclaim window
(``reclaim_window_bars``) and displacement window (``displacement_window_bars``).
So the walk's future output depends only on the suffix from the current outer
index. The cursor keeps a *committed floor* ``resume_i`` (a genuine batch
outer-index landing value) plus the status there; everything before it is
committed and immutable. Each candle it re-runs a faithful transcription of the
batch inner loop (``_walk_inner``) over ``candles[resume_i:current]`` and:

* emits the exact per-prefix transitions (committed prefix + the mutable
  provisional tail that the batch itself produces while a window is incomplete);
* advances ``resume_i`` past any window whose full resolution (reclaim +, if
  reclaimed, displacement) is complete — so a window more than
  ``reclaim_window_bars + displacement_window_bars`` candles behind the head is
  always committed and ``resume_i`` stays within that bound of the head.

Tap/freshness counting is a separate maximal-touch-run accumulation that
continues even after the breach walk goes terminal (exactly as the batch's
``_compute_freshness_and_taps`` runs independently of the breach walk).

The result of ``advance_poi_cursor`` at every prefix is byte-identical to
``run_poi_lifecycle(full prefix)`` — asserted by the permanent differential
tests. ``run_poi_lifecycle`` and its helpers are never modified and never called
here.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.legs import LegSpeedClassification, measure_leg
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
    PoiTapClassification,
)
from btmm_ai_scanner.poi.lifecycle import (
    LifecycleWalkResult,
    TransitionCandidate,
    _classify_tap_count,
    _is_breach,
    _is_displacement,
    _is_reclaim,
    _touches_zone,
    _zone_reference_atr,
)

_TWO = Decimal("2")


@dataclass(frozen=True)
class _WalkInnerResult:
    transitions: tuple[TransitionCandidate, ...]
    final_status: PoiLifecycleStatus
    terminal: bool
    last_seen_candle: NormalizedCandle | None
    # Slice-relative index up to which processing is committed (final), and the
    # status/transition-count at that point.
    committed_boundary: int
    committed_status: PoiLifecycleStatus
    committed_transition_count: int


def _walk_inner(
    candles: tuple[NormalizedCandle, ...],
    atr_values: tuple[Decimal | None, ...],
    symbol: InternalSymbol,
    timeframe: Timeframe,
    poi_record_id: UUID,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    zone_height: Decimal,
    min_tick: Decimal,
    start_status: PoiLifecycleStatus,
    configuration: PoiConfiguration,
) -> _WalkInnerResult:
    """Faithful transcription of run_poi_lifecycle's inner while-loop, starting
    at slice index 0 with ``start_status`` (a genuine batch resume point), plus
    committed-boundary tracking. Byte-identical transitions/status to the batch
    for this suffix; ``candles``/``atr_values`` are the aligned suffix."""
    n = len(candles)

    def tolerance(
        index: int, atr_multiplier: Decimal, height_multiplier: Decimal
    ) -> Decimal:
        fallback = candles[index].high - candles[index].low
        reference_atr = _zone_reference_atr(atr_values, index, fallback)
        bound_a = atr_multiplier * reference_atr
        bound_b = height_multiplier * zone_height if zone_height > 0 else bound_a
        return max(_TWO * min_tick, min(bound_a, bound_b))

    transitions: list[TransitionCandidate] = []
    status = start_status
    i = 0
    last_seen_candle: NormalizedCandle | None = None
    terminal = False

    provisional = False
    committed_boundary = 0
    committed_status = start_status
    committed_transition_count = 0

    def commit_to(new_i: int) -> None:
        nonlocal committed_boundary, committed_status, committed_transition_count
        if not provisional:
            committed_boundary = new_i
            committed_status = status
            committed_transition_count = len(transitions)

    while i < n and not terminal:
        candle = candles[i]
        last_seen_candle = candle
        overshoot = tolerance(
            i,
            configuration.zone_overshoot_tolerance_atr_multiplier,
            configuration.zone_overshoot_tolerance_zone_height_multiplier,
        )
        if _is_breach(candle, direction, zone_top, zone_bottom, overshoot):
            status = PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE
            transitions.append(
                TransitionCandidate(
                    symbol,
                    timeframe,
                    poi_record_id,
                    PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE,
                    candle.record_id,
                    candle.event_time_utc,
                    candle.availability_time_utc,
                )
            )

            window_full_end = i + 1 + configuration.reclaim_window_bars
            window_end = min(window_full_end, n)
            reclaim_complete = window_full_end <= n

            reclaim_index: int | None = None
            for j in range(i + 1, window_end):
                contact = tolerance(
                    j,
                    configuration.zone_contact_tolerance_atr_multiplier,
                    configuration.zone_contact_tolerance_zone_height_multiplier,
                )
                if _is_reclaim(candles[j], direction, zone_top, zone_bottom, contact):
                    reclaim_index = j
                    break

            if reclaim_index is not None:
                reclaim_candle = candles[reclaim_index]
                status = PoiLifecycleStatus.RECLAIM_CONFIRMED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.RECLAIM_CONFIRMED,
                        reclaim_candle.record_id,
                        reclaim_candle.event_time_utc,
                        reclaim_candle.availability_time_utc,
                    )
                )

                displacement_full_end = (
                    reclaim_index + 1 + configuration.displacement_window_bars
                )
                displacement_end = min(displacement_full_end, n)
                displacement_complete = displacement_full_end <= n
                displacement_index: int | None = None
                for k in range(reclaim_index + 1, displacement_end):
                    contact_k = tolerance(
                        k,
                        configuration.zone_contact_tolerance_atr_multiplier,
                        configuration.zone_contact_tolerance_zone_height_multiplier,
                    )
                    if not _is_displacement(
                        candles[k], direction, zone_top, zone_bottom, contact_k
                    ):
                        continue
                    leg_candles = candles[reclaim_index + 1 : k + 1]
                    leg_atrs = atr_values[reclaim_index + 1 : k + 1]
                    leg = measure_leg(
                        leg_candles,
                        leg_atrs,
                        is_bullish_direction=(direction == PoiDirection.BULLISH),
                        fast_normalized_speed_per_bar=Decimal("0.50"),
                        fast_directional_efficiency=Decimal("0.60"),
                        fast_directional_candle_share=Decimal("0.67"),
                        strong_fast_normalized_speed_per_bar=Decimal("0.75"),
                        strong_fast_directional_efficiency=Decimal("0.75"),
                        strong_fast_directional_candle_share=Decimal("0.80"),
                    )
                    if leg.classification in (
                        LegSpeedClassification.FAST,
                        LegSpeedClassification.STRONG_FAST,
                    ):
                        displacement_index = k
                        break

                if displacement_index is not None:
                    displacement_candle = candles[displacement_index]
                    status = PoiLifecycleStatus.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED,
                            displacement_candle.record_id,
                            displacement_candle.event_time_utc,
                            displacement_candle.availability_time_utc,
                        )
                    )
                    status = PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED,
                            displacement_candle.record_id,
                            displacement_candle.event_time_utc,
                            displacement_candle.availability_time_utc,
                        )
                    )
                    # FALSE_INVALIDATION is decided (displacement found); the
                    # reclaim's resolution is final.
                    resolution_final = True
                else:
                    status = PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT
                    transitions.append(
                        TransitionCandidate(
                            symbol,
                            timeframe,
                            poi_record_id,
                            PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT,
                            reclaim_candle.record_id,
                            reclaim_candle.event_time_utc,
                            reclaim_candle.availability_time_utc,
                        )
                    )
                    # Provisional until the displacement window is complete (a
                    # later fast displacement would flip this to FALSE_INVALIDATION).
                    resolution_final = displacement_complete

                i = reclaim_index + 1
                if not resolution_final:
                    provisional = True
                commit_to(i)
                continue

            window_candles = candles[i + 1 : window_end]
            qualifying_closes = sum(
                1
                for c_idx, c in zip(
                    range(i + 1, window_end), window_candles, strict=True
                )
                if _is_breach(
                    c,
                    direction,
                    zone_top,
                    zone_bottom,
                    tolerance(
                        c_idx,
                        configuration.zone_overshoot_tolerance_atr_multiplier,
                        configuration.zone_overshoot_tolerance_zone_height_multiplier,
                    ),
                )
            )
            bar3_qualifies = (
                len(window_candles) == configuration.reclaim_window_bars
                and qualifying_closes >= 2
                and _is_breach(
                    window_candles[-1],
                    direction,
                    zone_top,
                    zone_bottom,
                    tolerance(
                        window_end - 1,
                        configuration.zone_overshoot_tolerance_atr_multiplier,
                        configuration.zone_overshoot_tolerance_zone_height_multiplier,
                    ),
                )
            )
            if bar3_qualifies:
                final_candle = window_candles[-1]
                status = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
                        final_candle.record_id,
                        final_candle.event_time_utc,
                        final_candle.availability_time_utc,
                    )
                )
                terminal = True
                i = window_end
                commit_to(i)
                continue

            if len(window_candles) > 0:
                final_candle = window_candles[-1]
                status = PoiLifecycleStatus.RECLAIM_FAILED
                transitions.append(
                    TransitionCandidate(
                        symbol,
                        timeframe,
                        poi_record_id,
                        PoiLifecycleTransitionType.RECLAIM_FAILED,
                        final_candle.record_id,
                        final_candle.event_time_utc,
                        final_candle.availability_time_utc,
                    )
                )
            # No reclaim: the window's RECLAIM_FAILED/none verdict is final only
            # once the reclaim window is complete (else a later candle could
            # reclaim or complete a genuine invalidation).
            i = window_end
            if not reclaim_complete:
                provisional = True
            commit_to(i)
            continue

        i += 1
        commit_to(i)

    return _WalkInnerResult(
        transitions=tuple(transitions),
        final_status=status,
        terminal=terminal,
        last_seen_candle=last_seen_candle,
        committed_boundary=committed_boundary,
        committed_status=committed_status,
        committed_transition_count=committed_transition_count,
    )


@dataclass(frozen=True)
class PoiLifecycleCursor:
    """Private resumable per-POI lifecycle cursor. Immutable; a new instance is
    produced each advance (transactional)."""

    symbol: InternalSymbol
    timeframe: Timeframe
    poi_record_id: UUID
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    zone_height: Decimal
    availability_time_utc: datetime

    total_count: int = 0  # number of candles fed so far (== absolute n)
    start_index: int | None = None
    start_search_next: int = 0

    # Tap / freshness accumulation (continues through terminal).
    tap_count: int = 0
    in_tap: bool = False
    tap_next_index: int = 0

    # Breach-walk resume state.
    resume_i: int = 0
    resume_status: PoiLifecycleStatus = PoiLifecycleStatus.NO_BREACH
    committed_transitions: tuple[TransitionCandidate, ...] = ()
    terminal: bool = False
    terminal_last_seen: NormalizedCandle | None = None

    # Bounded suffix buffers aligned from resume_i.
    candle_buffer: tuple[NormalizedCandle, ...] = ()
    atr_buffer: tuple[Decimal | None, ...] = ()


def create_poi_lifecycle_cursor(
    symbol: InternalSymbol,
    timeframe: Timeframe,
    poi_record_id: UUID,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    availability_time_utc: datetime,
) -> PoiLifecycleCursor:
    return PoiLifecycleCursor(
        symbol=symbol,
        timeframe=timeframe,
        poi_record_id=poi_record_id,
        direction=direction,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
        zone_height=zone_top - zone_bottom,
        availability_time_utc=availability_time_utc,
    )


def advance_poi_cursor(
    cursor: PoiLifecycleCursor,
    candle: NormalizedCandle,
    atr_value: Decimal | None,
    configuration: PoiConfiguration,
) -> tuple[PoiLifecycleCursor, LifecycleWalkResult]:
    """Advance the cursor by one appended candle + its exact full-prefix ATR-14
    value. Returns the new cursor and the exact ``LifecycleWalkResult`` for the
    full visible prefix, byte-identical to ``run_poi_lifecycle`` at this prefix.
    """
    n = cursor.total_count + 1
    m = n - 1  # absolute index of this candle

    # 1. Resolve start_index (first candle strictly after the POI's availability).
    start_index = cursor.start_index
    start_search_next = cursor.start_search_next
    tap_count = cursor.tap_count
    in_tap = cursor.in_tap
    tap_next_index = cursor.tap_next_index

    if start_index is None:
        if candle.availability_time_utc > cursor.availability_time_utc:
            start_index = m
            tap_next_index = m
        else:
            start_search_next = n

    # 2. Tap / freshness accumulation over candles[start_index:] (maximal runs of
    #    zone-touching candles). Only the newly arrived candle is examined.
    if start_index is not None:
        # tap_next_index has already consumed candles before it; consume from
        # tap_next_index..m inclusive (normally just m).
        for _idx in range(tap_next_index, n):
            touching = _touches_zone(candle, cursor.zone_top, cursor.zone_bottom)
            if touching and not in_tap:
                tap_count += 1
                in_tap = True
            elif not touching:
                in_tap = False
        tap_next_index = n

    freshness_status = (
        PoiFreshnessStatus.INTERACTED if tap_count > 0 else PoiFreshnessStatus.FRESH
    )
    tap_classification: PoiTapClassification | None = _classify_tap_count(tap_count)
    age_in_confirmed_bars = max(0, n - start_index) if start_index is not None else 0

    # 3. Breach walk.
    if cursor.terminal:
        # Breach walk frozen; taps/age/freshness still evolve above.
        new_cursor = PoiLifecycleCursor(
            symbol=cursor.symbol,
            timeframe=cursor.timeframe,
            poi_record_id=cursor.poi_record_id,
            direction=cursor.direction,
            zone_top=cursor.zone_top,
            zone_bottom=cursor.zone_bottom,
            zone_height=cursor.zone_height,
            availability_time_utc=cursor.availability_time_utc,
            total_count=n,
            start_index=start_index,
            start_search_next=start_search_next,
            tap_count=tap_count,
            in_tap=in_tap,
            tap_next_index=tap_next_index,
            resume_i=cursor.resume_i,
            resume_status=cursor.resume_status,
            committed_transitions=cursor.committed_transitions,
            terminal=True,
            terminal_last_seen=cursor.terminal_last_seen,
            candle_buffer=(),
            atr_buffer=(),
        )
        result = LifecycleWalkResult(
            transitions=cursor.committed_transitions,
            final_status=PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED,
            freshness_status=freshness_status,
            tap_count=tap_count,
            tap_classification=tap_classification,
            age_in_confirmed_bars=age_in_confirmed_bars,
            last_seen_candle=cursor.terminal_last_seen,
        )
        return new_cursor, result

    if start_index is None:
        # No candle visible after the POI's availability yet: exactly the batch
        # start_index == len(candles) case (empty walk).
        new_cursor = PoiLifecycleCursor(
            symbol=cursor.symbol,
            timeframe=cursor.timeframe,
            poi_record_id=cursor.poi_record_id,
            direction=cursor.direction,
            zone_top=cursor.zone_top,
            zone_bottom=cursor.zone_bottom,
            zone_height=cursor.zone_height,
            availability_time_utc=cursor.availability_time_utc,
            total_count=n,
            start_index=None,
            start_search_next=start_search_next,
            tap_count=tap_count,
            in_tap=in_tap,
            tap_next_index=tap_next_index,
            resume_i=n,
            resume_status=PoiLifecycleStatus.NO_BREACH,
            committed_transitions=(),
            terminal=False,
            terminal_last_seen=None,
            candle_buffer=(),
            atr_buffer=(),
        )
        result = LifecycleWalkResult(
            transitions=(),
            final_status=PoiLifecycleStatus.NO_BREACH,
            freshness_status=PoiFreshnessStatus.FRESH,
            tap_count=0,
            tap_classification=None,
            age_in_confirmed_bars=0,
            last_seen_candle=None,
        )
        return new_cursor, result

    # Extend the bounded suffix buffers. resume_i is an absolute index; the
    # buffers hold candles[resume_i : n].
    resume_i = cursor.resume_i
    if resume_i < start_index:
        resume_i = start_index
    candle_buffer = (*cursor.candle_buffer, candle)
    atr_buffer = (*cursor.atr_buffer, atr_value)
    # Trim any candles before resume_i (defensive; normally already aligned).
    offset = resume_i - (n - len(candle_buffer))
    if offset > 0:
        candle_buffer = candle_buffer[offset:]
        atr_buffer = atr_buffer[offset:]

    walk = _walk_inner(
        candle_buffer,
        atr_buffer,
        cursor.symbol,
        cursor.timeframe,
        cursor.poi_record_id,
        cursor.direction,
        cursor.zone_top,
        cursor.zone_bottom,
        cursor.zone_height,
        configuration.minimum_price_tick,
        cursor.resume_status,
        configuration,
    )

    full_transitions = cursor.committed_transitions + walk.transitions

    terminal = walk.terminal
    if terminal:
        # The walk fully resolved (genuine invalidation is absorbing): everything
        # is now final and frozen.
        new_committed = full_transitions
        new_resume_i = resume_i + walk.committed_boundary
        new_candle_buffer: tuple[NormalizedCandle, ...] = ()
        new_atr_buffer: tuple[Decimal | None, ...] = ()
        terminal_last_seen = walk.last_seen_candle
        new_resume_status = walk.final_status
    else:
        # Advance the committed floor past fully-final windows; replay the
        # bounded provisional tail next candle.
        new_committed = (
            cursor.committed_transitions
            + walk.transitions[: walk.committed_transition_count]
        )
        new_resume_i = resume_i + walk.committed_boundary
        new_candle_buffer = candle_buffer[walk.committed_boundary :]
        new_atr_buffer = atr_buffer[walk.committed_boundary :]
        terminal_last_seen = None
        new_resume_status = walk.committed_status

    new_cursor = PoiLifecycleCursor(
        symbol=cursor.symbol,
        timeframe=cursor.timeframe,
        poi_record_id=cursor.poi_record_id,
        direction=cursor.direction,
        zone_top=cursor.zone_top,
        zone_bottom=cursor.zone_bottom,
        zone_height=cursor.zone_height,
        availability_time_utc=cursor.availability_time_utc,
        total_count=n,
        start_index=start_index,
        start_search_next=start_search_next,
        tap_count=tap_count,
        in_tap=in_tap,
        tap_next_index=tap_next_index,
        resume_i=new_resume_i,
        resume_status=new_resume_status,
        committed_transitions=new_committed,
        terminal=terminal,
        terminal_last_seen=terminal_last_seen,
        candle_buffer=new_candle_buffer,
        atr_buffer=new_atr_buffer,
    )

    result = LifecycleWalkResult(
        transitions=full_transitions,
        final_status=walk.final_status,
        freshness_status=freshness_status,
        tap_count=tap_count,
        tap_classification=tap_classification,
        age_in_confirmed_bars=age_in_confirmed_bars,
        last_seen_candle=walk.last_seen_candle,
    )
    return new_cursor, result
