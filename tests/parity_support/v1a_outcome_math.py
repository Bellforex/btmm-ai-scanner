"""V1-A forward-outcome measurement math (test/validation tooling only).

Pure, stateless functions implementing
``docs/validation/BTRC_V1_VALIDATION_PROTOCOL.md`` §5-§11 exactly:
EVENT_CLOSE_REFERENCE, directional return, MFE/MAE, ATR-normalized
threshold-reach with path ordering, and POI zone-geometry outcomes.

Nothing here re-implements or second-guesses any scanner/BTRC detection or
scoring logic — every function takes already-known prices (from the DEV
M15 OHLC series) and already-known POI/event fields (from the reused
scanner/BTRC engines) and does only arithmetic the protocol itself
specifies. This module has no dependency on ``scanner.replay`` or
``btrc`` at all, by design — it is the one piece of the harness cheap and
pure enough to carry the bulk of the protocol §17 oracle/mutation test
burden without needing the full (expensive) scanner replay in the loop.

FROZEN HORIZON GRID (protocol §6)
----------------------------------
``[1, 2, 3, 4, 8, 12, 24, 48]`` M15 bars. A horizon of N bars means
"through and including the N-th confirmed bar after the event bar
(horizon 0)". If fewer than N forward bars exist in the DEV set, that
horizon cell is ``censored`` (``None``), never padded or truncated.

FROZEN ATR THRESHOLD GRID (protocol §18)
------------------------------------------
``[0.25, 0.50, 1.00, 1.50, 2.00, 3.00]`` ATR multiples, favorable and
adverse tracked separately, each cell either a bar offset (1-indexed:
the offset of the first forward bar reaching the threshold) or
``censored`` if the threshold is never reached before the DEV set ends.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import NamedTuple

HORIZONS: tuple[int, ...] = (1, 2, 3, 4, 8, 12, 24, 48)
ATR_THRESHOLDS: tuple[Decimal, ...] = (
    Decimal("0.25"),
    Decimal("0.50"),
    Decimal("1.00"),
    Decimal("1.50"),
    Decimal("2.00"),
    Decimal("3.00"),
)

_HUNDRED = Decimal(100)


class ForwardBar(NamedTuple):
    """The only fields any outcome computation in this module needs from a
    forward M15 candle: its own high/low/close. Kept as a lightweight
    NamedTuple (not a full NormalizedCandle) so oracle tests can construct
    thousands of synthetic bars cheaply."""

    high: Decimal
    low: Decimal
    close: Decimal


def favorable_extreme(bar: ForwardBar, bullish: bool) -> Decimal:
    """The favorable-side price extreme of one bar for a given direction
    (protocol §8: high for a bullish event, low for a bearish event)."""
    return bar.high if bullish else bar.low


def adverse_extreme(bar: ForwardBar, bullish: bool) -> Decimal:
    """The adverse-side price extreme of one bar (protocol §9: low for a
    bullish event, high for a bearish event)."""
    return bar.low if bullish else bar.high


def directional_return(
    reference: Decimal, close_at_horizon: Decimal, *, bullish: bool
) -> Decimal:
    """Protocol §7: sign(direction) * (close[N] - EVENT_CLOSE_REFERENCE)."""
    sign = Decimal(1) if bullish else Decimal(-1)
    return sign * (close_at_horizon - reference)


def directional_return_pct(
    reference: Decimal, close_at_horizon: Decimal, *, bullish: bool
) -> Decimal:
    return (
        directional_return(reference, close_at_horizon, bullish=bullish)
        / reference
        * _HUNDRED
    )


@dataclass(frozen=True)
class HorizonReturn:
    horizon: int
    directional_return: Decimal
    directional_return_pct: Decimal
    censored: bool


def compute_directional_returns(
    reference: Decimal,
    forward_bars: tuple[ForwardBar, ...],
    *,
    bullish: bool,
    horizons: tuple[int, ...] = HORIZONS,
) -> tuple[HorizonReturn, ...]:
    """``forward_bars[0]`` is the bar 1 confirmed bar after the event bar
    (event bar itself, "horizon 0", is deliberately never included — protocol
    §6/§17 horizon-off-by-one integrity)."""
    results: list[HorizonReturn] = []
    for horizon in horizons:
        if horizon > len(forward_bars):
            results.append(
                HorizonReturn(
                    horizon=horizon,
                    directional_return=Decimal(0),
                    directional_return_pct=Decimal(0),
                    censored=True,
                )
            )
            continue
        close_n = forward_bars[horizon - 1].close
        results.append(
            HorizonReturn(
                horizon=horizon,
                directional_return=directional_return(reference, close_n, bullish=bullish),
                directional_return_pct=directional_return_pct(
                    reference, close_n, bullish=bullish
                ),
                censored=False,
            )
        )
    return tuple(results)


@dataclass(frozen=True)
class ExcursionResult:
    horizon: int
    value: Decimal
    pct: Decimal
    atr_units: Decimal | None
    censored: bool


def _excursion(
    reference: Decimal,
    forward_bars: tuple[ForwardBar, ...],
    *,
    bullish: bool,
    horizon: int,
    atr_at_event: Decimal | None,
    favorable: bool,
) -> ExcursionResult:
    if horizon > len(forward_bars):
        return ExcursionResult(
            horizon=horizon,
            value=Decimal(0),
            pct=Decimal(0),
            atr_units=None,
            censored=True,
        )
    window = forward_bars[:horizon]
    extremes = [
        (favorable_extreme(bar, bullish) if favorable else adverse_extreme(bar, bullish))
        for bar in window
    ]
    sign = Decimal(1) if bullish else Decimal(-1)
    if favorable:
        # best price movement IN the event's favor.
        best = max(sign * (extreme - reference) for extreme in extremes)
    else:
        # worst price movement AGAINST the event's favor.
        best = max(sign * (reference - extreme) for extreme in extremes)
    pct = best / reference * _HUNDRED
    atr_units = (best / atr_at_event) if atr_at_event is not None and atr_at_event != 0 else None
    return ExcursionResult(horizon=horizon, value=best, pct=pct, atr_units=atr_units, censored=False)


def compute_mfe(
    reference: Decimal,
    forward_bars: tuple[ForwardBar, ...],
    *,
    bullish: bool,
    atr_at_event: Decimal | None,
    horizons: tuple[int, ...] = HORIZONS,
) -> tuple[ExcursionResult, ...]:
    """Protocol §8: Maximum Favorable Excursion per horizon."""
    return tuple(
        _excursion(
            reference,
            forward_bars,
            bullish=bullish,
            horizon=h,
            atr_at_event=atr_at_event,
            favorable=True,
        )
        for h in horizons
    )


def compute_mae(
    reference: Decimal,
    forward_bars: tuple[ForwardBar, ...],
    *,
    bullish: bool,
    atr_at_event: Decimal | None,
    horizons: tuple[int, ...] = HORIZONS,
) -> tuple[ExcursionResult, ...]:
    """Protocol §9: Maximum Adverse Excursion per horizon."""
    return tuple(
        _excursion(
            reference,
            forward_bars,
            bullish=bullish,
            horizon=h,
            atr_at_event=atr_at_event,
            favorable=False,
        )
        for h in horizons
    )


@dataclass(frozen=True)
class ThresholdReachCell:
    threshold_atr: Decimal
    bar_offset: int | None  # 1-indexed offset of first bar reaching threshold; None = censored


@dataclass(frozen=True)
class ThresholdReachGrid:
    favorable: tuple[ThresholdReachCell, ...]
    adverse: tuple[ThresholdReachCell, ...]
    atr_unavailable: bool


def compute_threshold_reach_grid(
    reference: Decimal,
    forward_bars: tuple[ForwardBar, ...],
    *,
    bullish: bool,
    atr_at_event: Decimal | None,
    thresholds: tuple[Decimal, ...] = ATR_THRESHOLDS,
) -> ThresholdReachGrid:
    """Protocol §18 ATR-normalized threshold-reach grid, favorable and
    adverse tracked separately, over the FULL available forward window
    (bounded only by how much DEV data remains, not by the horizon grid).
    """
    if atr_at_event is None or atr_at_event == 0:
        return ThresholdReachGrid(
            favorable=tuple(ThresholdReachCell(t, None) for t in thresholds),
            adverse=tuple(ThresholdReachCell(t, None) for t in thresholds),
            atr_unavailable=True,
        )

    sign = Decimal(1) if bullish else Decimal(-1)
    running_favorable_best = Decimal("-Infinity")
    running_adverse_best = Decimal("-Infinity")
    favorable_hit: dict[Decimal, int] = {}
    adverse_hit: dict[Decimal, int] = {}
    for offset, bar in enumerate(forward_bars, start=1):
        fav_extreme = favorable_extreme(bar, bullish)
        adv_extreme = adverse_extreme(bar, bullish)
        running_favorable_best = max(
            running_favorable_best, sign * (fav_extreme - reference)
        )
        running_adverse_best = max(
            running_adverse_best, sign * (reference - adv_extreme)
        )
        fav_atr = running_favorable_best / atr_at_event
        adv_atr = running_adverse_best / atr_at_event
        for threshold in thresholds:
            if threshold not in favorable_hit and fav_atr >= threshold:
                favorable_hit[threshold] = offset
            if threshold not in adverse_hit and adv_atr >= threshold:
                adverse_hit[threshold] = offset

    return ThresholdReachGrid(
        favorable=tuple(
            ThresholdReachCell(t, favorable_hit.get(t)) for t in thresholds
        ),
        adverse=tuple(ThresholdReachCell(t, adverse_hit.get(t)) for t in thresholds),
        atr_unavailable=False,
    )


PathOrdering = str  # "favorable_first" | "adverse_first" | "neither" | "tie" | "censored"


def compute_path_ordering(grid: ThresholdReachGrid) -> dict[Decimal, PathOrdering]:
    """Protocol §18 path ordering: favorable-first vs. adverse-first vs.
    neither, per paired threshold (same ATR multiple on both sides)."""
    result: dict[Decimal, PathOrdering] = {}
    fav_by_threshold = {c.threshold_atr: c.bar_offset for c in grid.favorable}
    adv_by_threshold = {c.threshold_atr: c.bar_offset for c in grid.adverse}
    for threshold in fav_by_threshold:
        if grid.atr_unavailable:
            result[threshold] = "censored"
            continue
        fav = fav_by_threshold[threshold]
        adv = adv_by_threshold[threshold]
        if fav is None and adv is None:
            result[threshold] = "neither"
        elif fav is not None and (adv is None or fav < adv):
            result[threshold] = "favorable_first"
        elif adv is not None and (fav is None or adv < fav):
            result[threshold] = "adverse_first"
        else:
            result[threshold] = "tie"
    return result


@dataclass(frozen=True)
class PoiGeometryOutcome:
    touched: bool
    first_touch_offset: int | None  # None if never touched (censored) within DEV data
    max_penetration_price: Decimal | None
    max_penetration_atr: Decimal | None
    far_boundary_crossed: bool
    censored_no_forward_data: bool


def compute_poi_touch_outcome(
    zone_top: Decimal,
    zone_bottom: Decimal,
    *,
    bullish: bool,
    forward_bars: tuple[ForwardBar, ...],
    atr_lookup: tuple[Decimal | None, ...],
) -> PoiGeometryOutcome:
    """Protocol §10: touch = low[i] <= zone_top AND high[i] >= zone_bottom
    for any bar after the POI's own availability. Penetration depth is how
    far price moved past the NEAR boundary into (and potentially past) the
    zone; far-boundary-crossed is whether price reached the opposite edge.
    ``atr_lookup[i]`` must be the ATR value aligned to ``forward_bars[i]``
    (``None`` entries produce ``max_penetration_atr=None`` at that bar,
    never a fabricated value).
    """
    if len(forward_bars) == 0:
        return PoiGeometryOutcome(
            touched=False,
            first_touch_offset=None,
            max_penetration_price=None,
            max_penetration_atr=None,
            far_boundary_crossed=False,
            censored_no_forward_data=True,
        )

    # Near boundary: the edge price approaches first for this direction.
    # A bullish POI's price approaches zone_top from above; a bearish POI's
    # price approaches zone_bottom from below.
    near_boundary = zone_top if bullish else zone_bottom
    far_boundary = zone_bottom if bullish else zone_top

    first_touch_offset: int | None = None
    max_penetration_price: Decimal | None = None
    max_penetration_atr: Decimal | None = None
    far_crossed = False

    for offset, bar in enumerate(forward_bars, start=1):
        touches_now = bar.low <= zone_top and bar.high >= zone_bottom
        if touches_now and first_touch_offset is None:
            first_touch_offset = offset
        if touches_now:
            # Penetration depth: how far the bar's price went past the NEAR
            # boundary, toward/through the far boundary.
            penetration = (
                (near_boundary - bar.low) if bullish else (bar.high - near_boundary)
            )
            if penetration > 0 and (
                max_penetration_price is None or penetration > max_penetration_price
            ):
                max_penetration_price = penetration
                atr_here = atr_lookup[offset - 1]
                max_penetration_atr = (
                    (penetration / atr_here) if atr_here is not None and atr_here != 0 else None
                )
            crossed_now = (bar.low <= far_boundary) if bullish else (bar.high >= far_boundary)
            if crossed_now:
                far_crossed = True

    return PoiGeometryOutcome(
        touched=first_touch_offset is not None,
        first_touch_offset=first_touch_offset,
        max_penetration_price=max_penetration_price,
        max_penetration_atr=max_penetration_atr,
        far_boundary_crossed=far_crossed,
        censored_no_forward_data=False,
    )
