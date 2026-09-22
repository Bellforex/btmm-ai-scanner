"""RC5 DISTRACTION consumes qualified sweeps only.

DISTRACTION is inducement: liquidity taken on the approach path before price
reaches the POI. RC4 credited it from ANY raw sweep, which on these hosts means
a texture swing or an unqualified trendline being clipped counted as a trap.

RC5 requires the sweep to have survived causal qualification AND deduplication.
Nothing else changes -- the approach-side rule, the before-touch rule, DELAY and
WIPEOUT are untouched, and RC4 (which passes no qualified set) is unaffected.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btmm_ai_scanner.framework.engine import (
    FrameworkBarContext,
    evaluate_poi_framework,
)
from btmm_ai_scanner.framework.model import (
    FrameworkConfiguration,
    LiquidityKind,
    LiquiditySide,
    SweepEvent,
    SweepType,
)
from btmm_ai_scanner.poi.enums import PoiDirection

_START = datetime(2026, 9, 21, 0, 0, tzinfo=UTC)
_TICK = Decimal("0.01")


class _Candle:
    def __init__(self, index: int, price: float) -> None:
        self.event_time_utc = _START + timedelta(minutes=15 * index)
        self.availability_time_utc = self.event_time_utc + timedelta(minutes=15)
        self.open = self.close = Decimal(str(price))
        self.high = Decimal(str(price + 1))
        self.low = Decimal(str(price - 1))


def _sweep(index: int, price: str, side: LiquiditySide, level_id: str) -> SweepEvent:
    candle = _Candle(index, 100.0)
    return SweepEvent(
        kind=(
            LiquidityKind.SWING_LOW
            if side is LiquiditySide.SELL_SIDE
            else LiquidityKind.SWING_HIGH
        ),
        side=side,
        level_price=Decimal(price),
        level_id=level_id,
        sweep_type=SweepType.WICK_SWEEP,
        scope=None,
        bar_index=index,
        event_time_utc=candle.event_time_utc,
        availability_time_utc=candle.availability_time_utc,
    )


def _context(events, qualified=None) -> FrameworkBarContext:
    candles = tuple(_Candle(i, 100.0) for i in range(12))
    return FrameworkBarContext(
        candles=candles,
        atr=tuple(Decimal("1") for _ in candles),
        swings=(),
        ranges=(),
        events=tuple(events),
        event_times=tuple(e.availability_time_utc for e in events),
        availability_index=tuple(c.availability_time_utc for c in candles),
        config=FrameworkConfiguration(minimum_price_tick=_TICK),
        rc5_qualified_sweeps=qualified,
    )


def _assess(context, *, first_touch=None):
    return evaluate_poi_framework(
        context,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("100.00"),
        zone_bottom=Decimal("98.00"),
        availability_time_utc=_START,
        first_touch_time_utc=first_touch,
    )


#: sell-side liquidity resting ABOVE a bullish POI, swept before the touch
_INDUCEMENT = _sweep(2, "110.00", LiquiditySide.SELL_SIDE, "Sgood")


def test_rc4_still_credits_any_raw_sweep() -> None:
    """The baseline that must not move: with no qualified set, behaviour is
    exactly as before."""
    assert _assess(_context([_INDUCEMENT])).distraction


def test_rc5_credits_a_qualified_sweep() -> None:
    qualified = frozenset({("Sgood", _INDUCEMENT.availability_time_utc)})
    assert _assess(_context([_INDUCEMENT], qualified)).distraction


def test_rc5_refuses_an_unqualified_sweep() -> None:
    """A texture swing clipped on the approach is not inducement."""
    assert not _assess(_context([_INDUCEMENT], frozenset())).distraction


def test_a_deduplicated_group_contributes_once() -> None:
    """Three references describing ONE physical action: only the primary's raw
    level survives dedup, so corroboration cannot multiply the evidence."""
    same_bar = [
        _INDUCEMENT,
        _sweep(2, "110.00", LiquiditySide.SELL_SIDE, "Ecluster"),
        _sweep(2, "110.00", LiquiditySide.SELL_SIDE, "Ttrendline"),
    ]
    qualified = frozenset({("Sgood", _INDUCEMENT.availability_time_utc)})
    assessment = _assess(_context(same_bar, qualified))
    assert assessment.distraction
    credited = [e for e in assessment.evidence if e.startswith("DISTRACTION")]
    assert len(credited) == 1


def test_a_sweep_after_the_touch_is_not_retroactive_inducement() -> None:
    """The temporal rule is unchanged: inducement precedes the touch."""
    touch = _Candle(1, 100.0).availability_time_utc
    late = _sweep(8, "110.00", LiquiditySide.SELL_SIDE, "Slate")
    qualified = frozenset({("Slate", late.availability_time_utc)})
    assert not _assess(_context([late], qualified), first_touch=touch).distraction


def test_the_wrong_approach_side_is_not_inducement() -> None:
    """Buy-side liquidity below a bullish POI is not on its approach path."""
    wrong = _sweep(2, "110.00", LiquiditySide.BUY_SIDE, "Swrong")
    qualified = frozenset({("Swrong", wrong.availability_time_utc)})
    assert not _assess(_context([wrong], qualified)).distraction


def test_a_sweep_on_the_wrong_side_of_the_zone_is_not_inducement() -> None:
    below = _sweep(2, "90.00", LiquiditySide.SELL_SIDE, "Sbelow")
    qualified = frozenset({("Sbelow", below.availability_time_utc)})
    assert not _assess(_context([below], qualified)).distraction


@pytest.mark.parametrize("qualified", [None, frozenset()])
def test_delay_and_wipeout_are_untouched_by_qualification(qualified) -> None:
    """Qualification gates DISTRACTION and nothing else."""
    assessment = _assess(_context([_INDUCEMENT], qualified))
    assert assessment.delay is False
    assert assessment.wipeout is False
