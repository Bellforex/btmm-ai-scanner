"""RC4 market framework (author decisions 2026-09-19).

BTMM pre-trade cycle: DISTRACTION before the POI, DELAY inside it, WIPEOUT
slightly beyond it with reclaim; true acceptance beyond the POI is a failure.
Liquidity sweeps: wick sweep, close-through + reclaim, accepted break (no
sweep). Range model, range position, Fibonacci location, append-only tracker.
"""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.framework import (
    BtmmPretradeReason,
    FibBucket,
    FrameworkConfiguration,
    FrameworkKind,
    InteractionEpisode,
    LiquidityKind,
    LiquidityScope,
    LiquiditySide,
    RangePosition,
    RangeState,
    SweepEvent,
    SweepType,
    TradingRange,
    evaluate_poi_framework,
)
from btmm_ai_scanner.framework.engine import (
    FrameworkBarContext,
    _Level,
    _sweep_step,
    active_range_at,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.enums import PoiDirection
from tests.parity_support.ob_origin_series import rows_to_candles

D = Decimal
CFG = FrameworkConfiguration()
BULL = PoiDirection.BULLISH
BEAR = PoiDirection.BEARISH


def _context(rows, tmp_path: Path, name: str, *, events=(), ranges=(), swings=()):
    candles = rows_to_candles(rows, tmp_path, name)
    return FrameworkBarContext(
        candles=candles,
        atr=compute_atr_series(candles, 14),
        swings=tuple(swings),
        ranges=tuple(ranges),
        events=tuple(events),
        event_times=tuple(e.availability_time_utc for e in events),
        availability_index=tuple(c.availability_time_utc for c in candles),
        config=CFG,
    )


def _flat(n: int, price: float = 110.0) -> list[tuple[float, float, float, float]]:
    return [(price, price + 0.5, price - 0.5, price)] * n


def _event(candles, index, *, side, price, kind=LiquidityKind.SWING_LOW):
    c = candles[index]
    return SweepEvent(
        kind=kind,
        side=side,
        level_price=D(str(price)),
        level_id=f"L{index}",
        sweep_type=SweepType.WICK_SWEEP,
        scope=LiquidityScope.UNSCOPED,
        bar_index=index,
        event_time_utc=c.event_time_utc,
        availability_time_utc=c.availability_time_utc,
    )


# ---- BTMM pre-trade cycle -------------------------------------------------------

ZONE_TOP, ZONE_BOTTOM = D("100"), D("98")


def _touch_rows(tail):
    # 20 flat bars above the zone, then the interaction tail
    return _flat(20) + tail


def _evaluate(ctx, *, touch_index, availability_index=0, direction=BULL):
    candles = ctx.candles
    return evaluate_poi_framework(
        ctx,
        direction=direction,
        zone_top=ZONE_TOP,
        zone_bottom=ZONE_BOTTOM,
        availability_time_utc=candles[availability_index].availability_time_utc,
        first_touch_time_utc=(
            candles[touch_index].availability_time_utc
            if touch_index is not None
            else None
        ),
        source_time_utc=candles[availability_index].event_time_utc,
    )


def test_distraction_is_an_approach_path_sweep_before_the_touch(tmp_path: Path) -> None:
    rows = _touch_rows([(99.5, 100.5, 99.0, 100.2)])  # touch at 20
    probe = rows_to_candles(rows, tmp_path, "probe")
    # sell-side low ABOVE a bullish POI, swept at bar 10 (before the touch)
    inducement = _event(probe, 10, side=LiquiditySide.SELL_SIDE, price=105)
    ctx = _context(rows, tmp_path, "d1", events=(inducement,))
    result = _evaluate(ctx, touch_index=20)
    assert result.distraction and result.pretrade_valid
    assert result.pretrade_reason is BtmmPretradeReason.DISTRACTION
    # a sweep BELOW the bullish POI is not on the approach path: not distraction
    elsewhere = _event(probe, 10, side=LiquiditySide.SELL_SIDE, price=90)
    ctx = _context(rows, tmp_path, "d2", events=(elsewhere,))
    assert not _evaluate(ctx, touch_index=20).distraction
    # a buy-side sweep is not bullish inducement either
    buy = _event(probe, 10, side=LiquiditySide.BUY_SIDE, price=112)
    ctx = _context(rows, tmp_path, "d3", events=(buy,))
    assert not _evaluate(ctx, touch_index=20).distraction


def test_distraction_after_the_touch_bar_does_not_count(tmp_path: Path) -> None:
    rows = _touch_rows([(99.5, 100.5, 99.0, 100.2), *_flat(4, 101.0)])
    probe = rows_to_candles(rows, tmp_path, "probe2")
    late = _event(probe, 22, side=LiquiditySide.SELL_SIDE, price=105)
    ctx = _context(rows, tmp_path, "late", events=(late,))
    assert not _evaluate(ctx, touch_index=20).distraction


def test_delay_needs_two_inside_closes(tmp_path: Path) -> None:
    one = _touch_rows([(100.5, 100.8, 99.0, 99.5), (99.5, 102.0, 99.4, 101.8)])
    ctx = _context(one, tmp_path, "one")
    assert not _evaluate(ctx, touch_index=20).delay  # a single candle is not delay
    two = _touch_rows(
        [
            (100.5, 100.8, 99.0, 99.5),
            (99.5, 99.9, 98.6, 99.2),
            (99.2, 102.0, 99.1, 101.8),
        ]
    )
    ctx = _context(two, tmp_path, "two")
    result = _evaluate(ctx, touch_index=20)
    assert result.delay and result.poi_dwell_bars == 2
    assert result.pretrade_reason is BtmmPretradeReason.DELAY


def test_delay_by_reentry(tmp_path: Path) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 99.6, 100.4),  # touch, closes above
            (100.4, 101.5, 100.3, 101.2),  # left the zone
            (101.2, 101.3, 99.8, 100.9),  # re-enters
        ]
    )
    ctx = _context(rows, tmp_path, "reentry")
    result = _evaluate(ctx, touch_index=20)
    assert result.poi_reentry_count == 1 and result.delay


def test_wipeout_with_reclaim_and_true_failure(tmp_path: Path) -> None:
    wipe = _touch_rows(
        [
            (100.5, 100.8, 97.0, 98.4),  # wick well below the far edge (98)
            (98.4, 100.2, 98.2, 99.8),  # reclaimed inside
            (99.8, 102.0, 99.7, 101.5),  # departs above the zone
        ]
    )
    ctx = _context(wipe, tmp_path, "wipe")
    result = _evaluate(ctx, touch_index=20)
    assert result.wipeout and not result.true_failure and result.pretrade_valid
    fail = _touch_rows(
        [
            (100.5, 100.8, 96.0, 96.5),  # closes beyond the far edge
            (96.5, 97.0, 95.0, 95.5),
            (95.5, 96.0, 94.0, 94.5),
            (94.5, 95.0, 93.0, 93.5),  # no reclaim within 3 bars
            (93.5, 94.0, 92.0, 92.5),
        ]
    )
    ctx = _context(fail, tmp_path, "fail")
    result = _evaluate(ctx, touch_index=20)
    assert result.true_failure and not result.wipeout and not result.pretrade_valid
    assert result.episode is InteractionEpisode.FAILED


def test_bearish_mirror_wipeout(tmp_path: Path) -> None:
    rows = [
        *_flat(20, 90.0),
        (97.5, 103.0, 97.2, 101.6),  # spikes above the far edge (100)
        (101.6, 101.8, 99.0, 99.4),  # reclaim below
        (99.4, 99.5, 96.0, 96.5),  # departs below the zone
    ]
    ctx = _context(rows, tmp_path, "bear")
    result = _evaluate(ctx, touch_index=20, direction=BEAR)
    assert result.wipeout


def test_episode_window_is_the_btmm_reaction_window(tmp_path: Path) -> None:
    rows = _touch_rows([(100.5, 100.8, 99.5, 100.4), *_flat(3, 101.0)])
    ctx = _context(rows, tmp_path, "ep_active")
    assert _evaluate(ctx, touch_index=20).episode is InteractionEpisode.ACTIVE
    rows = _touch_rows([(100.5, 100.8, 99.5, 100.4), *_flat(4, 101.0)])
    ctx = _context(rows, tmp_path, "ep_ended")
    assert _evaluate(ctx, touch_index=20).episode is InteractionEpisode.ENDED
    ctx = _context(_flat(22), tmp_path, "untouched")
    assert _evaluate(ctx, touch_index=None).episode is InteractionEpisode.NOT_TOUCHED


def test_multiple_actions_are_reported_as_multiple(tmp_path: Path) -> None:
    rows = _touch_rows(
        [
            (100.5, 100.8, 99.0, 99.5),
            (99.5, 99.9, 98.6, 99.2),
            (99.2, 102.0, 99.1, 101.8),
        ]
    )
    probe = rows_to_candles(rows, tmp_path, "probe3")
    ind = _event(probe, 8, side=LiquiditySide.SELL_SIDE, price=104)
    ctx = _context(rows, tmp_path, "multi", events=(ind,))
    assert _evaluate(ctx, touch_index=20).pretrade_reason is BtmmPretradeReason.MULTIPLE


# ---- liquidity sweeps ------------------------------------------------------------


def test_sweep_types_and_accepted_break(tmp_path: Path) -> None:
    candles = rows_to_candles(
        [
            (100, 101, 99, 100),
            (100, 106, 99, 104),  # wick through 105, closes back below: WICK_SWEEP
        ],
        tmp_path,
        "wick",
    )
    events: list[SweepEvent] = []
    level = _Level(
        "a",
        LiquidityKind.SWING_HIGH,
        LiquiditySide.BUY_SIDE,
        D(105),
        candles[0].event_time_utc,
    )
    live = [level]
    for i, c in enumerate(candles):
        live = _sweep_step(live, i, c, None, CFG, events)
    assert [e.sweep_type for e in events] == [SweepType.WICK_SWEEP] and live == []

    candles = rows_to_candles(
        [(100, 101, 99, 100), (100, 107, 99, 106), (106, 106.5, 103, 104)],
        tmp_path,
        "reclaim",
    )
    events = []
    live = [
        _Level(
            "b",
            LiquidityKind.SWING_HIGH,
            LiquiditySide.BUY_SIDE,
            D(105),
            candles[0].event_time_utc,
        )
    ]
    for i, c in enumerate(candles):
        live = _sweep_step(live, i, c, None, CFG, events)
    assert [e.sweep_type for e in events] == [SweepType.CLOSE_THROUGH_RECLAIM]

    candles = rows_to_candles(
        [(100, 101, 99, 100), *[(106, 108, 105.5, 107)] * 5], tmp_path, "accepted"
    )
    events = []
    live = [
        _Level(
            "c",
            LiquidityKind.SWING_HIGH,
            LiquiditySide.BUY_SIDE,
            D(105),
            candles[0].event_time_utc,
        )
    ]
    for i, c in enumerate(candles):
        live = _sweep_step(live, i, c, None, CFG, events)
    assert events == [] and live == []  # accepted breakout: consumed, no sweep


# ---- range model and location ----------------------------------------------------


def _range(ctx_candles, *, high=110, low=100) -> TradingRange:
    return TradingRange(
        range_id="R1",
        start_time_utc=ctx_candles[0].event_time_utc,
        confirmation_time_utc=ctx_candles[0].event_time_utc,
        range_high=D(high),
        range_low=D(low),
        range_midpoint=D(high + low) / 2,
        upper_source="h",
        lower_source="l",
        state=RangeState.ACTIVE,
        end_time_utc=None,
    )


@pytest.mark.parametrize(
    ("top", "bottom", "direction", "position", "score"),
    [
        (102, 101, BULL, RangePosition.LOWER, 75),
        (106, 104, BULL, RangePosition.MIDDLE, 35),
        (109, 108, BULL, RangePosition.UPPER, 20),
        (109, 108, BEAR, RangePosition.UPPER, 75),
        (102, 101, BEAR, RangePosition.LOWER, 20),
    ],
)
def test_range_position_scores(
    tmp_path: Path, top, bottom, direction, position, score
) -> None:
    rows = _flat(20, 105.0)
    candles = rows_to_candles(rows, tmp_path, f"r{top}{direction.value}")
    ctx = _context(
        rows, tmp_path, f"rc{top}{direction.value}", ranges=(_range(candles),)
    )
    result = evaluate_poi_framework(
        ctx,
        direction=direction,
        zone_top=D(top),
        zone_bottom=D(bottom),
        availability_time_utc=candles[0].availability_time_utc,
        first_touch_time_utc=None,
        source_time_utc=candles[0].event_time_utc,
    )
    assert result.framework is FrameworkKind.RANGE
    assert result.range_position is position and result.location_score == score


def test_range_ends_on_bos_and_is_causal(tmp_path: Path) -> None:
    candles = rows_to_candles(_flat(10), tmp_path, "rng")
    rng = replace(
        _range(candles),
        confirmation_time_utc=candles[3].event_time_utc,
        state=RangeState.BROKEN_UP,
        end_time_utc=candles[6].event_time_utc,
    )
    assert (
        active_range_at([rng], candles[2].event_time_utc) is None
    )  # not yet confirmed
    assert active_range_at([rng], candles[4].event_time_utc) is rng
    assert active_range_at([rng], candles[7].event_time_utc) is None  # broken


def test_fib_buckets_follow_the_author_bands() -> None:
    from btmm_ai_scanner.framework.engine import _fib_bucket

    assert _fib_bucket(D("49.99")) is FibBucket.BELOW_50
    assert _fib_bucket(D("50")) is FibBucket.B50_618
    assert _fib_bucket(D("61.8")) is FibBucket.B618_79
    assert _fib_bucket(D("79")) is FibBucket.B618_79
    assert _fib_bucket(D("79.01")) is FibBucket.ABOVE_79
    assert CFG.fib_scores == {
        FibBucket.BELOW_50: 40,
        FibBucket.B50_618: 65,
        FibBucket.B618_79: 80,
        FibBucket.ABOVE_79: 55,
    }


def test_sweep_bonus_is_capped(tmp_path: Path) -> None:
    rows = _flat(20, 105.0)
    candles = rows_to_candles(rows, tmp_path, "bonus")
    ev = _event(candles, 5, side=LiquiditySide.SELL_SIDE, price=100)
    ctx = _context(rows, tmp_path, "bonusc", ranges=(_range(candles),), events=(ev,))
    result = evaluate_poi_framework(
        ctx,
        direction=BULL,
        zone_top=D(102),
        zone_bottom=D(101),
        availability_time_utc=candles[0].availability_time_utc,
        first_touch_time_utc=None,
        source_time_utc=candles[0].event_time_utc,
    )
    assert result.sweep_before_poi and result.location_score == 75 + 15


def test_rc4_profile_is_off_by_default() -> None:
    from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration

    assert ConfluenceConfiguration().market_framework is False


def test_no_lookahead_future_candles_never_change_a_past_assessment(
    tmp_path: Path,
) -> None:
    base = _touch_rows([(100.5, 100.8, 97.0, 98.4), (98.4, 100.2, 98.2, 99.8)])
    grown = [*base, (99.8, 102.0, 99.7, 101.5), *_flat(3, 102.0)]
    early = _evaluate(_context(base, tmp_path, "early"), touch_index=20)
    # the same assessment recomputed on the prefix of the longer series
    late_ctx = _context(grown, tmp_path, "late2")
    prefix = FrameworkBarContext(
        candles=late_ctx.candles[: len(base)],
        atr=late_ctx.atr[: len(base)],
        swings=(),
        ranges=(),
        events=(),
        event_times=(),
        availability_index=late_ctx.availability_index[: len(base)],
        config=CFG,
    )
    assert _evaluate(prefix, touch_index=20) == early
    assert not early.wipeout  # no departure yet: wipeout not claimed early
    assert _evaluate(late_ctx, touch_index=20).wipeout
