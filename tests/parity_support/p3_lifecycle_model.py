"""Test-side transcription of the Pine P3 persistent POI lifecycle.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics. Production `run_poi_lifecycle` is always the oracle.

THE PROBLEM THIS SOLVES
-----------------------
Production's walk LOOKS AHEAD: a breach at bar `i` is resolved by scanning up
to three bars forward for a reclaim, and then up to three bars past the
reclaim for a fast displacement leg. Pine cannot look ahead — it sees one
confirmed bar at a time — so a naive port would have to re-walk the POI's
whole post-origin history every bar, which is unbounded work and exactly the
thing the architecture forbids.

The resolution is a COMMITTED BOUNDARY. An episode's outcome is final only
once the windows it depends on are complete:

* a bar that does not breach is final immediately;
* a breach whose 3-bar reclaim window is complete is final, because no later
  bar can produce an earlier reclaim;
* a reclaim is final as soon as it is found, for the same reason;
* a reclaim WITHOUT displacement is provisional until the displacement window
  completes, because a later fast leg would upgrade it to a false
  invalidation;
* genuine invalidation requires a full window, so it is final by construction.

`resume_idx` holds the committed boundary and only advances past final
outcomes. Everything after it is re-derived each bar. Since an episode spans
at most 1 + 3 + 3 = 7 bars, the re-walk is bounded by a handful of iterations
per POI per bar rather than by history.

The reported state at bar T is therefore identical to
`run_poi_lifecycle(candles[0..T])`, including the deliberately provisional
tail that production itself produces on a truncated window. That equivalence
is what the prefix campaign asserts, for every prefix.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.legs import LegSpeedClassification, measure_leg
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
)

_ZERO = Decimal("0")
_TWO = Decimal("2")

#: Pine lifecycle status codes, mirroring the C_POI_LC_* constants.
LC_CODE: dict[PoiLifecycleStatus, int] = {
    PoiLifecycleStatus.NOT_APPLICABLE: 0,
    PoiLifecycleStatus.NO_BREACH: 1,
    PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE: 2,
    PoiLifecycleStatus.RECLAIM_PENDING: 3,
    PoiLifecycleStatus.RECLAIM_CONFIRMED: 4,
    PoiLifecycleStatus.DISPLACEMENT_PENDING: 5,
    PoiLifecycleStatus.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED: 6,
    PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT: 7,
    PoiLifecycleStatus.RECLAIM_FAILED: 8,
    PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED: 9,
    PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED: 10,
}

TR_CODE: dict[PoiLifecycleTransitionType, int] = {
    PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE: 2,
    PoiLifecycleTransitionType.RECLAIM_CONFIRMED: 4,
    PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED: 6,
    PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT: 7,
    PoiLifecycleTransitionType.RECLAIM_FAILED: 8,
    PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED: 9,
    PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED: 10,
}

#: The two states production never emits (AD-2).
RESERVED_UNREACHABLE = (
    PoiLifecycleStatus.RECLAIM_PENDING,
    PoiLifecycleStatus.DISPLACEMENT_PENDING,
)


@dataclass(frozen=True)
class ModelTransition:
    """One lifecycle event, in the Pine projection."""

    code: int
    event_ms: int
    availability_ms: int


def _ms(moment: datetime) -> int:
    return int(moment.timestamp() * 1000)


def _reference_atr(
    atr_values: Sequence[Decimal | None], index: int, fallback: Decimal
) -> Decimal:
    value = atr_values[index] if 0 <= index < len(atr_values) else None
    if value is not None and value > _ZERO:
        return value
    return fallback


def _tolerance(
    candles: Sequence[NormalizedCandle],
    atr_values: Sequence[Decimal | None],
    index: int,
    zone_height: Decimal,
    min_tick: Decimal,
    atr_multiplier: Decimal,
    height_multiplier: Decimal,
) -> Decimal:
    fallback = candles[index].high - candles[index].low
    reference_atr = _reference_atr(atr_values, index, fallback)
    bound_a = atr_multiplier * reference_atr
    bound_b = height_multiplier * zone_height if zone_height > _ZERO else bound_a
    return max(_TWO * min_tick, min(bound_a, bound_b))


def _is_breach(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    overshoot: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return (zone_bottom - candle.close) > overshoot
    return (candle.close - zone_top) > overshoot


def _is_reclaim(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    contact: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return candle.close >= zone_bottom + contact
    return candle.close <= zone_top - contact


def _is_displacement(
    candle: NormalizedCandle,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    contact: Decimal,
) -> bool:
    if direction == PoiDirection.BULLISH:
        return candle.close >= zone_top + contact
    return candle.close <= zone_bottom - contact


def _touches(candle: NormalizedCandle, zone_top: Decimal, zone_bottom: Decimal) -> bool:
    return candle.low <= zone_top and candle.high >= zone_bottom


@dataclass
class _WalkOutcome:
    status: PoiLifecycleStatus
    transitions: list[ModelTransition]
    commit_index: int
    commit_status: PoiLifecycleStatus
    commit_count: int
    terminal: bool


@dataclass
class PoiLifecycleCursor:
    """Persistent per-POI lifecycle state — the Pine `PoiLife` record."""

    zone_top: Decimal
    zone_bottom: Decimal
    direction: PoiDirection
    availability_ms: int
    configuration: PoiConfiguration

    status: PoiLifecycleStatus = PoiLifecycleStatus.NO_BREACH
    terminal: bool = False
    resume_index: int | None = None
    committed: list[ModelTransition] = field(default_factory=list)
    tap_count: int = 0
    in_tap: bool = False
    started: bool = False

    #: Provisional tail, re-derived every bar from the committed boundary.
    pending: list[ModelTransition] = field(default_factory=list)
    reported_status: PoiLifecycleStatus = PoiLifecycleStatus.NO_BREACH

    def _walk(
        self,
        candles: Sequence[NormalizedCandle],
        atr_values: Sequence[Decimal | None],
        n: int,
    ) -> _WalkOutcome:
        cfg = self.configuration
        zone_height = self.zone_top - self.zone_bottom
        min_tick = cfg.minimum_price_tick
        assert self.resume_index is not None

        def overshoot_at(index: int) -> Decimal:
            return _tolerance(
                candles,
                atr_values,
                index,
                zone_height,
                min_tick,
                cfg.zone_overshoot_tolerance_atr_multiplier,
                cfg.zone_overshoot_tolerance_zone_height_multiplier,
            )

        def contact_at(index: int) -> Decimal:
            return _tolerance(
                candles,
                atr_values,
                index,
                zone_height,
                min_tick,
                cfg.zone_contact_tolerance_atr_multiplier,
                cfg.zone_contact_tolerance_zone_height_multiplier,
            )

        i = self.resume_index
        status = self.status
        transitions: list[ModelTransition] = []
        terminal = False
        commit_index, commit_status, commit_count = i, status, 0

        while i < n and not terminal:
            candle = candles[i]
            if _is_breach(
                candle,
                self.direction,
                self.zone_top,
                self.zone_bottom,
                overshoot_at(i),
            ):
                status = PoiLifecycleStatus.CLOSE_BREACH_CANDIDATE
                transitions.append(
                    ModelTransition(
                        TR_CODE[PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE],
                        _ms(candle.event_time_utc),
                        _ms(candle.availability_time_utc),
                    )
                )

                window_end = min(i + 1 + cfg.reclaim_window_bars, n)
                window_complete = (i + 1 + cfg.reclaim_window_bars) <= n

                reclaim_index: int | None = None
                for j in range(i + 1, window_end):
                    if _is_reclaim(
                        candles[j],
                        self.direction,
                        self.zone_top,
                        self.zone_bottom,
                        contact_at(j),
                    ):
                        reclaim_index = j
                        break

                if reclaim_index is not None:
                    reclaim_candle = candles[reclaim_index]
                    status = PoiLifecycleStatus.RECLAIM_CONFIRMED
                    transitions.append(
                        ModelTransition(
                            TR_CODE[PoiLifecycleTransitionType.RECLAIM_CONFIRMED],
                            _ms(reclaim_candle.event_time_utc),
                            _ms(reclaim_candle.availability_time_utc),
                        )
                    )
                    displacement_end = min(
                        reclaim_index + 1 + cfg.displacement_window_bars, n
                    )
                    displacement_complete = (
                        reclaim_index + 1 + cfg.displacement_window_bars
                    ) <= n

                    displacement_index: int | None = None
                    for k in range(reclaim_index + 1, displacement_end):
                        if not _is_displacement(
                            candles[k],
                            self.direction,
                            self.zone_top,
                            self.zone_bottom,
                            contact_at(k),
                        ):
                            continue
                        leg = measure_leg(
                            candles[reclaim_index + 1 : k + 1],
                            atr_values[reclaim_index + 1 : k + 1],
                            is_bullish_direction=(
                                self.direction == PoiDirection.BULLISH
                            ),
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
                        dc = candles[displacement_index]
                        status = PoiLifecycleStatus.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
                        transitions.append(
                            ModelTransition(
                                TR_CODE[
                                    PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
                                ],
                                _ms(dc.event_time_utc),
                                _ms(dc.availability_time_utc),
                            )
                        )
                        status = PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED
                        transitions.append(
                            ModelTransition(
                                TR_CODE[
                                    PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED
                                ],
                                _ms(dc.event_time_utc),
                                _ms(dc.availability_time_utc),
                            )
                        )
                        episode_final = True
                    else:
                        status = PoiLifecycleStatus.RECLAIM_WITHOUT_DISPLACEMENT
                        transitions.append(
                            ModelTransition(
                                TR_CODE[
                                    PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT
                                ],
                                _ms(reclaim_candle.event_time_utc),
                                _ms(reclaim_candle.availability_time_utc),
                            )
                        )
                        episode_final = displacement_complete

                    i = reclaim_index + 1
                    if episode_final:
                        commit_index, commit_status = i, status
                        commit_count = len(transitions)
                    continue

                window_candles = candles[i + 1 : window_end]
                qualifying = sum(
                    1
                    for idx in range(i + 1, window_end)
                    if _is_breach(
                        candles[idx],
                        self.direction,
                        self.zone_top,
                        self.zone_bottom,
                        overshoot_at(idx),
                    )
                )
                bar3 = (
                    len(window_candles) == cfg.reclaim_window_bars
                    and qualifying >= 2
                    and _is_breach(
                        window_candles[-1],
                        self.direction,
                        self.zone_top,
                        self.zone_bottom,
                        overshoot_at(window_end - 1),
                    )
                )
                if bar3:
                    final_candle = window_candles[-1]
                    status = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
                    transitions.append(
                        ModelTransition(
                            TR_CODE[
                                PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
                            ],
                            _ms(final_candle.event_time_utc),
                            _ms(final_candle.availability_time_utc),
                        )
                    )
                    terminal = True
                    i = window_end
                    commit_index, commit_status = i, status
                    commit_count = len(transitions)
                    continue

                if len(window_candles) > 0:
                    final_candle = window_candles[-1]
                    status = PoiLifecycleStatus.RECLAIM_FAILED
                    transitions.append(
                        ModelTransition(
                            TR_CODE[PoiLifecycleTransitionType.RECLAIM_FAILED],
                            _ms(final_candle.event_time_utc),
                            _ms(final_candle.availability_time_utc),
                        )
                    )
                i = window_end
                if window_complete:
                    commit_index, commit_status = i, status
                    commit_count = len(transitions)
                continue

            i += 1
            commit_index, commit_status = i, status
            commit_count = len(transitions)

        return _WalkOutcome(
            status,
            transitions,
            commit_index,
            commit_status,
            commit_count,
            terminal,
        )

    def advance(
        self,
        candles: Sequence[NormalizedCandle],
        atr_values: Sequence[Decimal | None],
        bar_index: int,
    ) -> None:
        """Feed one confirmed bar. Mirrors the Pine per-bar cursor step."""
        candle = candles[bar_index]
        if not self.started:
            if _ms(candle.availability_time_utc) <= self.availability_ms:
                return
            self.started = True
            self.resume_index = bar_index

        # Taps are an independent subsystem: they keep counting after a
        # terminal invalidation, exactly as production does.
        touching = _touches(candle, self.zone_top, self.zone_bottom)
        if touching and not self.in_tap:
            self.tap_count += 1
            self.in_tap = True
        elif not touching:
            self.in_tap = False

        if self.terminal:
            self.pending = []
            self.reported_status = self.status
            return

        outcome = self._walk(candles, atr_values, bar_index + 1)
        self.committed.extend(outcome.transitions[: outcome.commit_count])
        self.resume_index = outcome.commit_index
        self.status = outcome.commit_status
        self.pending = outcome.transitions[outcome.commit_count :]
        self.reported_status = outcome.status
        if outcome.terminal:
            self.terminal = True

    def transitions(self) -> list[ModelTransition]:
        return [*self.committed, *self.pending]

    # ---- P3-I7 downstream projection --------------------------------------
    #
    # BTMM reads only two transition types (btmm/analyzer.py:644-649) and
    # addresses an event by POI identity plus its timing, so the projection
    # exposes the tally and the latest event rather than a growing list.

    RELEVANT_CODES = (9, 10)

    def transition_count(self) -> int:
        return len(self.transitions())

    def relevant_count(self) -> int:
        return sum(1 for t in self.transitions() if t.code in (9, 10))

    def last_transition(self) -> tuple[int, int, int]:
        """(code, event ms, availability ms); C_ST_NA triple when none yet."""
        events = self.transitions()
        if not events:
            return (-99, -99, -99)
        last = events[-1]
        return (last.code, last.event_ms, last.availability_ms)

    def downstream_projection(self) -> tuple[int, int, int, tuple[int, int, int]]:
        return (
            self.state_code(),
            self.transition_count(),
            self.relevant_count(),
            self.last_transition(),
        )

    def state_code(self) -> int:
        return LC_CODE[self.reported_status]
