"""The PINE-EQUIVALENT T4 volatility / session classification.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY THIS MODULE DOES NOT TOUCH THE P5/P6 TRANSPORT AT ALL
-----------------------------------------------------------
Every other T-phase in this campaign reads the 26-field wire because the
scanner's full swing/transition/displacement HISTORY is not something Pine
can hold. T4 is different in kind: `assess_volatility`'s `volatility_window`
default (50) and `atr_period` (14) are both far larger than any transport
window this campaign has needed, but neither needs to CROSS a
`request.security` boundary at all -- they read the POI timeframe's OWN
candle history, which for the P6 host contexts already means Pine's own
in-context `high[i]`/`low[i]`/`close[i]` series (or the ATR P1 already
computes on that same context). `assess_session` needs even less: only the
evaluation timestamp itself, which Pine always has as `time`. So this module
proves independent-reimplementation equivalence against the FULL production
functions, exactly like the original P1-P4 campaigns did before the P5
transport pattern existed -- not wire sufficiency.

WHAT STAYS INDEPENDENT VS. WHAT IS DELIBERATELY REUSED
---------------------------------------------------------
ATR itself (`compute_atr_series`) is a proven, already-ported P1 measurement
-- re-deriving it here would test nothing new and risks silently drifting from
the one true implementation. `total_range`/`median_total_range` are one-line
arithmetic on already-available OHLC, reused for the same reason. What this
module writes INDEPENDENTLY is the T4-specific part: the percentile rank, the
band thresholds, the abnormal-spike test, and the session precedence
ordering -- the parts an actual port could get subtly wrong.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from btmm_ai_scanner.btrc.enums import SessionContext, VolatilityState

_ZERO = Decimal("0")

_SUITABILITY: dict[VolatilityState, int] = {
    VolatilityState.VERY_LOW: 40,
    VolatilityState.LOW: 75,
    VolatilityState.NORMAL: 100,
    VolatilityState.HIGH: 60,
    VolatilityState.EXTREME: 20,
}


# ------------------------------------------------------------------ volatility
@dataclass(frozen=True)
class T4VolatilityConfig:
    atr_period: int = 14
    volatility_window: int = 50
    percentile_very_low_max: Decimal = Decimal("0.10")
    percentile_low_max: Decimal = Decimal("0.30")
    percentile_normal_max: Decimal = Decimal("0.70")
    percentile_high_max: Decimal = Decimal("0.90")
    abnormal_spike_multiplier: Decimal = Decimal("2.5")


@dataclass(frozen=True)
class VolatilityResult:
    volatility_state: VolatilityState
    abnormal_spike: bool
    suitability_score: int


def _median(values: list[Decimal]) -> Decimal:
    if not values:
        return _ZERO
    ranked = sorted(values)
    mid = len(ranked) // 2
    if len(ranked) % 2 == 1:
        return ranked[mid]
    return (ranked[mid - 1] + ranked[mid]) / Decimal(2)


def _band(percentile: Decimal, config: T4VolatilityConfig) -> VolatilityState:
    if percentile < config.percentile_very_low_max:
        return VolatilityState.VERY_LOW
    if percentile < config.percentile_low_max:
        return VolatilityState.LOW
    if percentile < config.percentile_normal_max:
        return VolatilityState.NORMAL
    if percentile < config.percentile_high_max:
        return VolatilityState.HIGH
    return VolatilityState.EXTREME


def volatility_from_window(
    ranges: list[Decimal],
    config: T4VolatilityConfig | None = None,
) -> VolatilityResult:
    """`ranges` is the trailing `volatility_window` candles' `high - low`,
    oldest first, newest last -- exactly what a Pine rolling array of
    `high - low` already holds once `volatility_window` bars have confirmed.
    Insufficient-history is decided by the CALLER (the window not yet being
    full), matching `assess_volatility`'s own `len(ordered) < atr_period` gate
    on the raw history rather than the trimmed window.
    """
    cfg = config or T4VolatilityConfig()
    current = ranges[-1]
    median = _median(ranges)
    at_or_below = sum(1 for r in ranges if r <= current)
    percentile = Decimal(at_or_below) / Decimal(len(ranges))
    abnormal = median > _ZERO and current >= cfg.abnormal_spike_multiplier * median
    state = _band(percentile, cfg)
    return VolatilityResult(state, abnormal, _SUITABILITY[state])


# --------------------------------------------------------------------- session
@dataclass(frozen=True)
class T4SessionConfig:
    london_timezone: str = "Europe/London"
    new_york_timezone: str = "America/New_York"
    london_preopen_start: tuple[int, int] = (7, 0)
    london_open: tuple[int, int] = (8, 0)
    london_close: tuple[int, int] = (16, 30)
    new_york_preopen_start: tuple[int, int] = (7, 0)
    new_york_open: tuple[int, int] = (8, 0)
    new_york_close: tuple[int, int] = (17, 0)
    asian_start_hour_utc: int = 22
    asian_end_hour_utc: int = 6


def _minutes(hm: tuple[int, int]) -> int:
    return hm[0] * 60 + hm[1]


def session_from_evaluation_time(
    evaluation_time_utc: datetime,
    config: T4SessionConfig | None = None,
) -> SessionContext:
    cfg = config or T4SessionConfig()
    ldn = evaluation_time_utc.astimezone(ZoneInfo(cfg.london_timezone))
    ny = evaluation_time_utc.astimezone(ZoneInfo(cfg.new_york_timezone))
    ldn_min = ldn.hour * 60 + ldn.minute
    ny_min = ny.hour * 60 + ny.minute

    london_active = _minutes(cfg.london_open) <= ldn_min < _minutes(cfg.london_close)
    london_preopen = (
        _minutes(cfg.london_preopen_start) <= ldn_min < _minutes(cfg.london_open)
    )
    ny_active = _minutes(cfg.new_york_open) <= ny_min < _minutes(cfg.new_york_close)
    ny_preopen = (
        _minutes(cfg.new_york_preopen_start) <= ny_min < _minutes(cfg.new_york_open)
    )

    utc_hour = evaluation_time_utc.astimezone(ZoneInfo("UTC")).hour
    in_asian = utc_hour >= cfg.asian_start_hour_utc or utc_hour < cfg.asian_end_hour_utc

    if london_active and ny_active:
        return SessionContext.LONDON_NY_OVERLAP
    if ny_active:
        return SessionContext.NEW_YORK
    if ny_preopen:
        return SessionContext.NEW_YORK_PREOPEN
    if london_active:
        return SessionContext.LONDON
    if london_preopen:
        return SessionContext.LONDON_PREOPEN
    if in_asian:
        return SessionContext.ASIAN
    return SessionContext.POST_NY
