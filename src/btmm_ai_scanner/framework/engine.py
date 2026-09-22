"""RC4 market framework engine (host / chart timeframe).

The framework is evaluated on the HOST timeframe — the timeframe being traded —
for POIs of every timeframe. That keeps it expressible in the Pine build
without new P6 transport (P6 stays CLOSED).

Causality: a structure transition, swing, cluster or trendline is a level from
the first bar whose OPEN is at or after its availability; a sweep is known at
the close (availability) of the bar that completes it.
"""

from __future__ import annotations

from bisect import bisect_right
from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.enums import EqualLevelType, SwingType, TrendlineOrientation
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.domain.trendlines import Trendline
from btmm_ai_scanner.framework.model import (
    BtmmPretradeReason,
    FibBucket,
    FrameworkConfiguration,
    FrameworkKind,
    InteractionEpisode,
    LiquidityKind,
    LiquidityScope,
    LiquiditySide,
    PoiFrameworkAssessment,
    RangePosition,
    RangeState,
    SweepEvent,
    SweepType,
    TradingRange,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.structure.enums import StructureDirection
from btmm_ai_scanner.structure.transitions import StructureTransition

__all__ = [
    "FrameworkBarContext",
    "FrameworkTracker",
    "LiquidityLevel",
    "advance_levels",
    "build_framework_bar_context",
    "detect_ranges",
    "evaluate_poi_framework",
    "framework_context_for",
    "sweep_timeline",
]

_HUNDRED = Decimal(100)
_EPS = timedelta(microseconds=1)
_THIRD = Decimal(1) / Decimal(3)
_TWO_THIRDS = Decimal(2) / Decimal(3)


# ---------------------------------------------------------------------------
# Range model
# ---------------------------------------------------------------------------


def detect_ranges(
    transitions: Sequence[StructureTransition], config: FrameworkConfiguration
) -> tuple[TradingRange, ...]:
    """A range is confirmed at the transition that completes >= range_choch_count
    CHOCHs among the last range_window transitions (the BTRC RANGE rule). Its
    high / low are the extreme levels those alternating breaks broke. It ends at
    the first later BOS (persistent break = accepted breakout) or is superseded
    by the next range confirmation."""
    ordered = sorted(
        transitions,
        key=lambda t: (t.availability_time_utc, t.event_time_utc, str(t.record_id)),
    )
    found: list[tuple[int, TradingRange]] = []
    for k in range(config.range_window - 1, len(ordered)):
        window = ordered[k - config.range_window + 1 : k + 1]
        chochs = sum(1 for t in window if "CHOCH" in t.transition_type.value)
        if chochs < config.range_choch_count:
            continue
        highs = [t for t in window if t.direction_after is StructureDirection.BULLISH]
        lows = [t for t in window if t.direction_after is StructureDirection.BEARISH]
        if not highs or not lows:
            continue
        top = max(highs, key=lambda t: t.broken_level_price)
        bottom = min(lows, key=lambda t: t.broken_level_price)
        if top.broken_level_price <= bottom.broken_level_price:
            continue
        found.append(
            (
                k,
                TradingRange(
                    range_id=f"R{ordered[k].availability_time_utc.isoformat()}",
                    start_time_utc=window[0].event_time_utc,
                    confirmation_time_utc=ordered[k].availability_time_utc,
                    range_high=top.broken_level_price,
                    range_low=bottom.broken_level_price,
                    range_midpoint=(top.broken_level_price + bottom.broken_level_price)
                    / 2,
                    upper_source=str(top.broken_swing_id),
                    lower_source=str(bottom.broken_swing_id),
                    state=RangeState.ACTIVE,
                    end_time_utc=None,
                ),
            )
        )
    ranges: list[TradingRange] = []
    for position, (k, rng) in enumerate(found):
        next_k = found[position + 1][0] if position + 1 < len(found) else len(ordered)
        state, end = RangeState.ACTIVE, None
        for t in ordered[k + 1 : next_k + 1]:
            if "BOS" in t.transition_type.value:
                state = (
                    RangeState.BROKEN_UP
                    if t.direction_after is StructureDirection.BULLISH
                    else RangeState.BROKEN_DOWN
                )
                end = t.availability_time_utc
                break
        if state is RangeState.ACTIVE and position + 1 < len(found):
            end = found[position + 1][1].confirmation_time_utc  # superseded
        ranges.append(replace(rng, state=state, end_time_utc=end))
    return tuple(ranges)


def active_range_at(
    ranges: Sequence[TradingRange], moment: datetime
) -> TradingRange | None:
    """The range confirmed at or before ``moment`` and not yet ended."""
    current = None
    for rng in ranges:
        if rng.confirmation_time_utc <= moment and (
            rng.end_time_utc is None or rng.end_time_utc > moment
        ):
            current = rng
    return current


# ---------------------------------------------------------------------------
# Liquidity levels and sweeps
# ---------------------------------------------------------------------------


@dataclass
class _Level:
    level_id: str
    kind: LiquidityKind
    side: LiquiditySide
    price: Decimal
    known_from: datetime  # the level exists for bars opening at/after this
    slope: Decimal = Decimal(0)  # trendline price change per bar
    anchor_index: int = 0
    through_at: int | None = None  # bar index of a pending close-through

    def price_at(self, index: int) -> Decimal:
        if self.kind is LiquidityKind.TRENDLINE:
            return self.price + self.slope * (index - self.anchor_index)
        return self.price


def _levels(
    swings: Sequence[ConfirmedSwing],
    clusters: Sequence[EqualLevelCluster],
    trendlines: Sequence[Trendline],
) -> list[_Level]:
    out: list[_Level] = []
    for s in swings:
        high = s.swing_type is SwingType.SWING_HIGH
        out.append(
            _Level(
                f"S{s.record_id}",
                LiquidityKind.SWING_HIGH if high else LiquidityKind.SWING_LOW,
                LiquiditySide.BUY_SIDE if high else LiquiditySide.SELL_SIDE,
                s.pivot_price,
                s.meaningful_confirmation_time_utc,
            )
        )
    for c in clusters:
        high = c.cluster_type is EqualLevelType.EQUAL_HIGH
        out.append(
            _Level(
                f"E{c.record_id}",
                LiquidityKind.EQUAL_HIGHS if high else LiquidityKind.EQUAL_LOWS,
                LiquiditySide.BUY_SIDE if high else LiquiditySide.SELL_SIDE,
                c.zone_top if high else c.zone_bottom,
                c.availability_time_utc,
            )
        )
    for t in trendlines:
        bullish = t.orientation is TrendlineOrientation.BULLISH_TRENDLINE
        out.append(
            _Level(
                f"T{t.record_id}",
                LiquidityKind.TRENDLINE,
                LiquiditySide.SELL_SIDE if bullish else LiquiditySide.BUY_SIDE,
                t.anchor_1_price,
                t.availability_time_utc,
                slope=t.raw_slope,
                anchor_index=t.anchor_1_bar_index,
            )
        )
    out.sort(key=lambda lv: (lv.known_from, lv.level_id))
    return out


def _scope(
    side: LiquiditySide, price: Decimal, rng: TradingRange | None
) -> LiquidityScope:
    if rng is None:
        return LiquidityScope.UNSCOPED
    if side is LiquiditySide.BUY_SIDE:
        return (
            LiquidityScope.EXTERNAL
            if price >= rng.range_high
            else LiquidityScope.INTERNAL
        )
    return (
        LiquidityScope.EXTERNAL if price <= rng.range_low else LiquidityScope.INTERNAL
    )


def _sweep_step(
    active: list[_Level],
    index: int,
    candle: NormalizedCandle,
    rng: TradingRange | None,
    config: FrameworkConfiguration,
    events: list[SweepEvent],
) -> list[_Level]:
    """Advance every live level by one candle; append sweeps; return survivors."""
    survivors: list[_Level] = []
    for level in active:
        price = level.price_at(index)
        buy = level.side is LiquiditySide.BUY_SIDE
        beyond_close = candle.close > price if buy else candle.close < price
        beyond_wick = candle.high > price if buy else candle.low < price
        sweep_type = None
        if level.through_at is not None:
            if not beyond_close:
                sweep_type = SweepType.CLOSE_THROUGH_RECLAIM
            elif index - level.through_at >= config.sweep_reclaim_bars:
                continue  # accepted beyond: level consumed, no sweep
        elif beyond_close:
            level.through_at = index
        elif beyond_wick:
            sweep_type = SweepType.WICK_SWEEP
        if sweep_type is None:
            survivors.append(level)
            continue
        events.append(
            SweepEvent(
                kind=level.kind,
                side=level.side,
                level_price=price,
                level_id=level.level_id,
                sweep_type=sweep_type,
                scope=_scope(level.side, price, rng),
                bar_index=index,
                event_time_utc=candle.event_time_utc,
                availability_time_utc=candle.availability_time_utc,
            )
        )
    return survivors


#: A liquidity level, exposed so RC5 can add reference families of its own
#: WITHOUT re-implementing sweep mechanics. RC4's own level set is unaffected.
LiquidityLevel = _Level


def advance_levels(
    active: list[_Level],
    index: int,
    candle: NormalizedCandle,
    rng: TradingRange | None,
    config: FrameworkConfiguration,
    events: list[SweepEvent],
) -> list[_Level]:
    """Public seam over ``_sweep_step``.

    RC5 adds reference families the framework does not build -- POI far edges
    chief among them -- and those must be swept by exactly the same rules:
    the same wick test, the same close-through test, the same reclaim window,
    the same "accepted beyond consumes the level" behaviour. Re-implementing
    any of that would create a second set of mechanics that could drift.

    So RC5 supplies its own levels and calls THIS, which is literally the
    function RC4 uses. Nothing about RC4's own level set changes.
    """
    return _sweep_step(active, index, candle, rng, config, events)


def sweep_timeline(
    candles: Sequence[NormalizedCandle],
    swings: Sequence[ConfirmedSwing],
    clusters: Sequence[EqualLevelCluster],
    trendlines: Sequence[Trendline],
    ranges: Sequence[TradingRange],
    config: FrameworkConfiguration,
) -> tuple[SweepEvent, ...]:
    """Every sweep, in bar order. A level is swept once:
    WICK_SWEEP — the bar trades through the level and closes back on its side;
    CLOSE_THROUGH_RECLAIM — a close through the level followed, within
    ``sweep_reclaim_bars``, by a close back on its side. A close-through that is
    not reclaimed in time consumes the level with no event (accepted break)."""
    pending_levels = _levels(swings, clusters, trendlines)
    active: list[_Level] = []
    range_levels: dict[str, _Level] = {}
    events: list[SweepEvent] = []
    next_level = 0
    for index, candle in enumerate(candles):
        opened = candle.event_time_utc
        while (
            next_level < len(pending_levels)
            and pending_levels[next_level].known_from <= opened
        ):
            active.append(pending_levels[next_level])
            next_level += 1
        rng = active_range_at(ranges, opened)
        if rng is not None:
            for kind, side, price in (
                (LiquidityKind.RANGE_HIGH, LiquiditySide.BUY_SIDE, rng.range_high),
                (LiquidityKind.RANGE_LOW, LiquiditySide.SELL_SIDE, rng.range_low),
            ):
                key = f"{rng.range_id}:{kind.value}"
                if key not in range_levels:
                    level = _Level(key, kind, side, price, rng.confirmation_time_utc)
                    range_levels[key] = level
                    active.append(level)
        active = _sweep_step(active, index, candle, rng, config, events)
    return tuple(events)


# ---------------------------------------------------------------------------
# Per-bar context (POI independent) and per-POI assessment
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FrameworkBarContext:
    candles: tuple[NormalizedCandle, ...]
    atr: tuple[Decimal | None, ...]
    swings: tuple[ConfirmedSwing, ...]
    ranges: tuple[TradingRange, ...]
    events: tuple[SweepEvent, ...]
    event_times: tuple[datetime, ...]
    availability_index: tuple[datetime, ...]
    config: FrameworkConfiguration
    #: RC5 ONLY. ``(raw_level_id, availability_time)`` of every sweep that
    #: survived causal qualification and deduplication. ``None`` means RC4,
    #: which keeps consuming raw sweeps exactly as before.
    #:
    #: Deduplication is inherited rather than re-done: a merged group keeps
    #: only its PRIMARY raw level, so one physical liquidity action contributes
    #: once and corroborating references cannot multiply the evidence.
    rc5_qualified_sweeps: frozenset[tuple[str, datetime]] | None = None


def build_framework_bar_context(
    candles: Sequence[NormalizedCandle],
    swings: Sequence[ConfirmedSwing],
    clusters: Sequence[EqualLevelCluster],
    trendlines: Sequence[Trendline],
    transitions: Sequence[StructureTransition],
    config: FrameworkConfiguration | None = None,
) -> FrameworkBarContext:
    config = config or FrameworkConfiguration()
    candles = tuple(candles)
    ranges = detect_ranges(transitions, config)
    events = sweep_timeline(candles, swings, clusters, trendlines, ranges, config)
    return FrameworkBarContext(
        candles=candles,
        atr=compute_atr_series(candles, config.atr_period),
        swings=tuple(
            sorted(
                swings,
                key=lambda s: (s.meaningful_confirmation_time_utc, str(s.record_id)),
            )
        ),
        ranges=ranges,
        events=events,
        event_times=tuple(e.availability_time_utc for e in events),
        availability_index=tuple(c.availability_time_utc for c in candles),
        config=config,
    )


class FrameworkTracker:
    """Append-only framework state for ONE timeframe, advanced once per bar.

    Measurement swings, clusters, trendlines and structure transitions can be
    revised as later bars arrive. The framework must not repaint (RC3
    non-repaint principle), so every level and every range is registered the
    first time it is seen and never retracted, candles are processed exactly
    once in order, and sweep events are only ever appended. This is also how the
    Pine build holds the same state (bar-by-bar ``var`` arrays)."""

    def __init__(self, config: FrameworkConfiguration | None = None) -> None:
        self.config = config or FrameworkConfiguration()
        self._seen_levels: set[str] = set()
        self._pending: list[_Level] = []
        self._active: list[_Level] = []
        self._range_levels: set[str] = set()
        self._ranges: dict[str, TradingRange] = {}
        self._swings: dict[str, ConfirmedSwing] = {}
        self._events: list[SweepEvent] = []
        self._next_index = 0

    def advance(
        self,
        candles: Sequence[NormalizedCandle],
        swings: Sequence[ConfirmedSwing],
        clusters: Sequence[EqualLevelCluster],
        trendlines: Sequence[Trendline],
        transitions: Sequence[StructureTransition],
    ) -> FrameworkBarContext:
        config = self.config
        candles = tuple(candles)
        for level in _levels(swings, clusters, trendlines):
            if level.level_id not in self._seen_levels:
                self._seen_levels.add(level.level_id)
                self._pending.append(level)
        self._pending.sort(key=lambda lv: (lv.known_from, lv.level_id))
        for swing in swings:
            self._swings.setdefault(str(swing.record_id), swing)
        for found in detect_ranges(transitions, config):
            locked = self._ranges.get(found.range_id)
            if locked is None:
                self._ranges[found.range_id] = found
            elif locked.end_time_utc is None and found.end_time_utc is not None:
                # an ending is new information; boundaries stay as first seen
                self._ranges[found.range_id] = replace(
                    locked, state=found.state, end_time_utc=found.end_time_utc
                )
        ranges = tuple(
            sorted(
                self._ranges.values(),
                key=lambda r: (r.confirmation_time_utc, r.range_id),
            )
        )
        for index in range(self._next_index, len(candles)):
            candle = candles[index]
            opened = candle.event_time_utc
            while self._pending and self._pending[0].known_from <= opened:
                self._active.append(self._pending.pop(0))
            rng = active_range_at(ranges, opened)
            if rng is not None:
                for kind, side, price in (
                    (LiquidityKind.RANGE_HIGH, LiquiditySide.BUY_SIDE, rng.range_high),
                    (LiquidityKind.RANGE_LOW, LiquiditySide.SELL_SIDE, rng.range_low),
                ):
                    key = f"{rng.range_id}:{kind.value}"
                    if key not in self._range_levels:
                        self._range_levels.add(key)
                        self._active.append(
                            _Level(key, kind, side, price, rng.confirmation_time_utc)
                        )
            self._active = _sweep_step(
                self._active, index, candle, rng, config, self._events
            )
        self._next_index = len(candles)
        events = tuple(self._events)
        return FrameworkBarContext(
            candles=candles,
            atr=compute_atr_series(candles, config.atr_period),
            swings=tuple(
                sorted(
                    self._swings.values(),
                    key=lambda s: (
                        s.meaningful_confirmation_time_utc,
                        str(s.record_id),
                    ),
                )
            ),
            ranges=ranges,
            events=events,
            event_times=tuple(e.availability_time_utc for e in events),
            availability_index=tuple(c.availability_time_utc for c in candles),
            config=config,
        )


def _fib_bucket(pct: Decimal) -> FibBucket:
    if pct < 50:
        return FibBucket.BELOW_50
    if pct < Decimal("61.8"):
        return FibBucket.B50_618
    if pct <= 79:
        return FibBucket.B618_79
    return FibBucket.ABOVE_79


def _origin_impulse(
    context: FrameworkBarContext,
    *,
    source_time_utc: datetime,
    zone_top: Decimal,
    zone_bottom: Decimal,
    now: datetime,
    bullish: bool,
) -> tuple[Decimal, Decimal] | None:
    """(extreme, origin) of the impulse the POI belongs to — the pullback
    theorem: impulse A creates the POI, correction B returns into it.

    Bullish: origin = the latest confirmed swing low at or before the POI's
    source candle (or the POI's own bottom if it lies lower — a POI that IS the
    leg origin); extreme = the highest high printed since the source candle.
    Bearish mirror. Everything is known at ``now``."""
    known = [
        s
        for s in context.swings
        if s.meaningful_confirmation_time_utc <= now
        and s.pivot_start_time_utc <= source_time_utc
        and s.swing_type is (SwingType.SWING_LOW if bullish else SwingType.SWING_HIGH)
    ]
    after = [
        c
        for c in context.candles
        if c.event_time_utc >= source_time_utc and c.availability_time_utc <= now
    ]
    if not after:
        return None
    if bullish:
        origin = zone_bottom
        if known:
            latest = max(
                known, key=lambda s: (s.pivot_start_time_utc, str(s.record_id))
            )
            origin = min(origin, latest.pivot_price)
        return max(c.high for c in after), origin
    origin = zone_top
    if known:
        latest = max(known, key=lambda s: (s.pivot_start_time_utc, str(s.record_id)))
        origin = max(origin, latest.pivot_price)
    return min(c.low for c in after), origin


def evaluate_poi_framework(
    context: FrameworkBarContext,
    *,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
    availability_time_utc: datetime,
    first_touch_time_utc: datetime | None,
    source_time_utc: datetime | None = None,
) -> PoiFrameworkAssessment:
    cfg = context.config
    candles = context.candles
    now_index = len(candles) - 1
    now = candles[now_index].availability_time_utc if candles else availability_time_utc
    bullish = direction is PoiDirection.BULLISH
    mid = (zone_top + zone_bottom) / 2
    evidence: list[str] = []

    # --- episode start: first host bar whose close is at/after the P3 touch ---
    start_index: int | None = None
    if first_touch_time_utc is not None:
        start_index = bisect_right(
            context.availability_index, first_touch_time_utc - _EPS
        )
        if start_index > now_index:
            start_index = None

    # --- DISTRACTION (inducement): after the POI became available and before
    # the bar where price reaches it, a sweep of the liquidity resting on the
    # approach path — sell-side lows ABOVE a bullish POI, buy-side highs BELOW
    # a bearish POI. It traps early entries and builds the liquidity the real
    # POI reaction feeds on. A sweep elsewhere on the chart is not distraction.
    lo = bisect_right(context.event_times, availability_time_utc)
    hi_time = (
        candles[start_index].availability_time_utc if start_index is not None else now
    )
    approach_side = LiquiditySide.SELL_SIDE if bullish else LiquiditySide.BUY_SIDE
    pre_touch = [
        e
        for e in context.events[lo:]
        if (
            e.availability_time_utc < hi_time
            or (start_index is None and e.availability_time_utc <= now)
        )
        and e.side is approach_side
        and (e.level_price > zone_top if bullish else e.level_price < zone_bottom)
        # RC5: only a causally qualified, deduplicated sweep is inducement. A
        # texture swing or an unqualified trendline being clipped is not.
        # RC4 passes None here and is unaffected.
        and (
            context.rc5_qualified_sweeps is None
            or (e.level_id, e.availability_time_utc) in context.rc5_qualified_sweeps
        )
    ]
    distraction = bool(pre_touch)
    if distraction:
        first = pre_touch[0]
        evidence.append(
            f"DISTRACTION {first.sweep_type.value} of {first.kind.value} "
            f"{first.level_price} at {first.event_time_utc.isoformat()}"
        )

    # --- DELAY / WIPEOUT inside the interaction episode ---
    delay = wipeout = true_failure = False
    dwell = touches = reentries = 0
    episode = InteractionEpisode.NOT_TOUCHED
    episode_start: datetime | None = None
    episode_end: datetime | None = None
    if start_index is not None:
        episode_start = candles[start_index].availability_time_utc
        end_index = start_index + cfg.episode_bars - 1
        last = min(now_index, end_index)
        atr = context.atr[start_index] or Decimal(0)
        height = zone_top - zone_bottom
        tolerance = max(
            2 * cfg.minimum_price_tick,
            min(
                cfg.overshoot_atr_multiplier * atr,
                cfg.overshoot_height_multiplier * height,
            ),
        )
        run = 0
        left = False
        penetrated_at: int | None = None
        reclaimed = False
        for j in range(start_index, last + 1):
            c = candles[j]
            touching = c.low <= zone_top and c.high >= zone_bottom
            touches += touching
            inside_close = zone_bottom <= c.close <= zone_top
            dwell += inside_close
            run = run + 1 if inside_close else 0
            if run >= cfg.delay_inside_closes:
                delay = True
            left_zone = c.close > zone_top if bullish else c.close < zone_bottom
            if left and touching:
                reentries += 1  # left the zone, then came back into it
                left = False
            if left_zone:
                left = True
            # wipeout: trade beyond the far edge by more than the tolerance,
            # then reclaim (close back at/inside the far edge) and depart
            beyond = (
                c.low < zone_bottom - tolerance
                if bullish
                else c.high > zone_top + tolerance
            )
            if beyond and penetrated_at is None:
                penetrated_at = j
            if penetrated_at is not None and not reclaimed and not true_failure:
                back = c.close >= zone_bottom if bullish else c.close <= zone_top
                if back:
                    reclaimed = True
                elif j - penetrated_at >= cfg.sweep_reclaim_bars:
                    true_failure = True
                    episode_end = c.availability_time_utc
                    evidence.append(
                        f"TRUE_FAILURE accepted beyond the POI at {c.event_time_utc.isoformat()}"
                    )
            if reclaimed and not wipeout:
                departed = c.close > zone_top if bullish else c.close < zone_bottom
                if departed:
                    wipeout = True
                    evidence.append(
                        f"WIPEOUT penetration beyond far edge then reclaim and departure "
                        f"at {c.event_time_utc.isoformat()}"
                    )
            if true_failure:
                break
        if reentries >= cfg.delay_reentries:
            delay = True
        if delay:
            evidence.append(f"DELAY dwell={dwell} reentries={reentries}")
        if true_failure:
            episode = InteractionEpisode.FAILED
        elif now_index >= end_index:
            episode = InteractionEpisode.ENDED
            episode_end = candles[end_index].availability_time_utc
        else:
            episode = InteractionEpisode.ACTIVE

    actions = [
        name
        for name, seen in (
            ("DISTRACTION", distraction),
            ("DELAY", delay),
            ("WIPEOUT", wipeout),
        )
        if seen
    ]
    pretrade_valid = bool(actions) and not true_failure
    reason = (
        BtmmPretradeReason.NONE
        if not pretrade_valid
        else BtmmPretradeReason.MULTIPLE
        if len(actions) > 1
        else BtmmPretradeReason(actions[0])
    )

    # --- location ---
    rng = active_range_at(context.ranges, now)
    retracement = None
    fib = None
    position = None
    if rng is not None:
        framework = FrameworkKind.RANGE
        span = rng.range_high - rng.range_low
        rel = (mid - rng.range_low) / span
        position = (
            RangePosition.LOWER
            if rel < _THIRD
            else RangePosition.UPPER
            if rel > _TWO_THIRDS
            else RangePosition.MIDDLE
        )
        correct = RangePosition.LOWER if bullish else RangePosition.UPPER
        location = (
            cfg.range_correct_side_score
            if position is correct
            else cfg.range_middle_score
            if position is RangePosition.MIDDLE
            else cfg.range_wrong_side_score
        )
    else:
        impulse = _origin_impulse(
            context,
            source_time_utc=source_time_utc or availability_time_utc,
            zone_top=zone_top,
            zone_bottom=zone_bottom,
            now=now,
            bullish=bullish,
        )
        if impulse is None:
            framework = FrameworkKind.NONE
            location = cfg.no_framework_score
        else:
            framework = FrameworkKind.TREND
            extreme, origin = impulse
            span = extreme - origin if bullish else origin - extreme
            if span <= 0:
                framework = FrameworkKind.NONE
                location = cfg.no_framework_score
            else:
                depth = (extreme - mid) if bullish else (mid - extreme)
                retracement = (depth / span * _HUNDRED).quantize(Decimal("0.01"))
                fib = _fib_bucket(retracement)
                location = cfg.fib_scores[fib]
    wanted_side = LiquiditySide.SELL_SIDE if bullish else LiquiditySide.BUY_SIDE
    since = [e for e in context.events[lo:] if e.availability_time_utc <= now]
    sweep_before = any(e.side is wanted_side for e in since)
    trendline_sweep = any(e.kind is LiquidityKind.TRENDLINE for e in since)
    if sweep_before:
        location = min(100, location + cfg.sweep_bonus)

    # --- liquidity around the POI: nearest unswept swing level each side ---
    swept_ids = {e.level_id for e in context.events if e.availability_time_utc <= now}
    above = [
        s.pivot_price
        for s in context.swings
        if s.meaningful_confirmation_time_utc <= now
        and s.swing_type is SwingType.SWING_HIGH
        and s.pivot_price > zone_top
        and f"S{s.record_id}" not in swept_ids
    ]
    below = [
        s.pivot_price
        for s in context.swings
        if s.meaningful_confirmation_time_utc <= now
        and s.swing_type is SwingType.SWING_LOW
        and s.pivot_price < zone_bottom
        and f"S{s.record_id}" not in swept_ids
    ]
    return PoiFrameworkAssessment(
        framework=framework,
        range_id=rng.range_id if rng is not None else None,
        range_position=position,
        retracement_pct=retracement,
        fib_bucket=fib,
        sweep_before_poi=sweep_before,
        trendline_sweep=trendline_sweep,
        location_score=location,
        distraction=distraction,
        delay=delay,
        wipeout=wipeout,
        true_failure=true_failure,
        pretrade_valid=pretrade_valid,
        pretrade_reason=reason,
        poi_dwell_bars=dwell,
        poi_touch_count=touches,
        poi_reentry_count=reentries,
        episode=episode,
        liquidity_above=min(above) if above else None,
        liquidity_below=max(below) if below else None,
        evidence=tuple(evidence),
        first_touch_time_utc=first_touch_time_utc if start_index is not None else None,
        episode_start_time_utc=episode_start,
        episode_end_time_utc=episode_end,
    )


def framework_context_for(
    analysis: Any,
    timeframe: Timeframe,
    candles: Sequence[NormalizedCandle] | None,
    tracker: FrameworkTracker | None,
) -> FrameworkBarContext | None:
    """The framework context of ONE timeframe from a scanner analysis.

    RC4 evaluates the framework on the HOST / chart timeframe only. It reads that
    timeframe's own swings, equal-level clusters, trendlines and structure
    transitions — collections the host computes natively — so no new
    higher-timeframe transport is needed and the closed P6 contract (what BTRC
    requires from context timeframes) is unchanged."""
    if not candles:
        return None
    measurement = next(
        (m for m in analysis.measurement_analyses if m.timeframe == timeframe), None
    )
    if measurement is None:
        return None
    structure = next(
        (s for s in analysis.structure_analyses if s.timeframe == timeframe), None
    )
    transitions = structure.structure_transitions if structure is not None else ()
    if tracker is not None:
        return tracker.advance(
            candles,
            measurement.confirmed_swings,
            measurement.equal_level_clusters,
            measurement.trendlines,
            transitions,
        )
    return build_framework_bar_context(
        candles,
        measurement.confirmed_swings,
        measurement.equal_level_clusters,
        measurement.trendlines,
        transitions,
    )
