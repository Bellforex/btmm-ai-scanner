"""RC4 market-framework value types and configuration.

Every default is either REUSED from an existing frozen rule (source named) or
an explicit author decision of 2026-09-19. Values marked PROVISIONAL are not
frozen and were never tuned against outcomes.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

__all__ = [
    "BtmmPretradeReason",
    "FibBucket",
    "FrameworkConfiguration",
    "FrameworkKind",
    "InteractionEpisode",
    "LiquidityKind",
    "LiquidityScope",
    "LiquiditySide",
    "PoiFrameworkAssessment",
    "RangePosition",
    "RangeState",
    "SweepEvent",
    "SweepType",
    "TradingRange",
]


class RangeState(StrEnum):
    ACTIVE = "ACTIVE"
    BROKEN_UP = "BROKEN_UP"
    BROKEN_DOWN = "BROKEN_DOWN"


class LiquiditySide(StrEnum):
    BUY_SIDE = "BUY_SIDE"  # resting above price (highs)
    SELL_SIDE = "SELL_SIDE"  # resting below price (lows)


class LiquidityKind(StrEnum):
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"
    EQUAL_HIGHS = "EQUAL_HIGHS"
    EQUAL_LOWS = "EQUAL_LOWS"
    RANGE_HIGH = "RANGE_HIGH"
    RANGE_LOW = "RANGE_LOW"
    TRENDLINE = "TRENDLINE"


class LiquidityScope(StrEnum):
    INTERNAL = "INTERNAL"  # strictly inside an active range
    EXTERNAL = "EXTERNAL"  # at / beyond an active range boundary
    UNSCOPED = "UNSCOPED"  # no active range


class SweepType(StrEnum):
    WICK_SWEEP = "WICK_SWEEP"
    CLOSE_THROUGH_RECLAIM = "CLOSE_THROUGH_RECLAIM"


class FrameworkKind(StrEnum):
    RANGE = "RANGE"
    TREND = "TREND"
    NONE = "NONE"


class FibBucket(StrEnum):
    BELOW_50 = "LT_50"
    B50_618 = "50_61.8"
    B618_79 = "61.8_79"
    ABOVE_79 = "GT_79"


class RangePosition(StrEnum):
    LOWER = "LOWER_THIRD"
    MIDDLE = "MIDDLE_THIRD"
    UPPER = "UPPER_THIRD"


class BtmmPretradeReason(StrEnum):
    NONE = "NONE"
    DISTRACTION = "DISTRACTION"
    DELAY = "DELAY"
    WIPEOUT = "WIPEOUT"
    MULTIPLE = "MULTIPLE"


class InteractionEpisode(StrEnum):
    NOT_TOUCHED = "NOT_TOUCHED"
    ACTIVE = "ACTIVE"  # first touch seen, episode still running
    ENDED = "ENDED"  # episode window elapsed
    FAILED = "FAILED"  # true acceptance beyond the POI (no reclaim)


@dataclass(frozen=True)
class FrameworkConfiguration:
    # REUSED — BTRC trend engine RANGE rule (btrc/trend_configuration.py):
    # >= 3 change-of-character events in the last 4 structure transitions.
    range_window: int = 4
    range_choch_count: int = 3
    # PROVISIONAL (author 2026-09-19 allowed a non-frozen default): sweep
    # reclaim window reuses the POI lifecycle reclaim window (3 bars).
    sweep_reclaim_bars: int = 3
    # REUSED — BTMM reaction window (btmm/configuration.py reaction_window_bars).
    episode_bars: int = 5
    # AUTHOR 2026-09-19 — DELAY = >= 2 consecutive closes inside the zone
    # OR >= 1 re-entry after leaving.
    delay_inside_closes: int = 2
    delay_reentries: int = 1
    # REUSED — BTMM interaction overshoot tolerance
    # max(2 ticks, min(0.10 x ATR, 0.25 x zone height)).
    overshoot_atr_multiplier: Decimal = Decimal("0.10")
    overshoot_height_multiplier: Decimal = Decimal("0.25")
    minimum_price_tick: Decimal = Decimal("0.01")
    atr_period: int = 14
    # AUTHOR 2026-09-19 — location scores (PROVISIONAL, not profit-tuned).
    fib_scores: dict[FibBucket, int] = field(
        default_factory=lambda: {
            FibBucket.BELOW_50: 40,
            FibBucket.B50_618: 65,
            FibBucket.B618_79: 80,
            FibBucket.ABOVE_79: 55,
        }
    )
    range_correct_side_score: int = 75
    range_middle_score: int = 35
    range_wrong_side_score: int = 20
    no_framework_score: int = 50
    sweep_bonus: int = 15
    # AUTHOR 2026-09-19 — BTMM score: action observed / setup only / none.
    btmm_action_score: int = 85
    btmm_setup_only_score: int = 55
    btmm_none_score: int = 25


@dataclass(frozen=True)
class TradingRange:
    range_id: str
    start_time_utc: datetime
    confirmation_time_utc: datetime
    range_high: Decimal
    range_low: Decimal
    range_midpoint: Decimal
    upper_source: str
    lower_source: str
    state: RangeState
    end_time_utc: datetime | None


@dataclass(frozen=True)
class SweepEvent:
    kind: LiquidityKind
    side: LiquiditySide
    level_price: Decimal
    level_id: str
    sweep_type: SweepType
    scope: LiquidityScope
    bar_index: int
    event_time_utc: datetime
    availability_time_utc: datetime


@dataclass(frozen=True)
class PoiFrameworkAssessment:
    framework: FrameworkKind
    range_id: str | None
    range_position: RangePosition | None
    retracement_pct: Decimal | None
    fib_bucket: FibBucket | None
    sweep_before_poi: bool
    trendline_sweep: bool
    location_score: int
    distraction: bool
    delay: bool
    wipeout: bool
    true_failure: bool
    pretrade_valid: bool
    pretrade_reason: BtmmPretradeReason
    poi_dwell_bars: int
    poi_touch_count: int
    poi_reentry_count: int
    episode: InteractionEpisode
    liquidity_above: Decimal | None
    liquidity_below: Decimal | None
    evidence: tuple[str, ...]
    # RC4 interaction episode (author-accepted RC4 lifecycle contract)
    first_touch_time_utc: datetime | None = None  # P3 first qualifying touch
    episode_start_time_utc: datetime | None = None  # host bar closing at/after it
    episode_end_time_utc: datetime | None = None  # true-failure bar or window end
