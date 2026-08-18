"""BTRC-T4 deterministic volatility + session-context engines.

Volatility reuses the existing ATR (`compute_atr_series`) and candle-range
(`total_range` / `median_total_range`) implementations — it never re-implements
ATR — and classifies the current range within a trailing percentile distribution.
It never infers direction. Session context is derived from the evaluation
timestamp (never the machine clock) through `zoneinfo`, so London/New-York DST is
correct for every date. Neither engine generates trades.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from zoneinfo import ZoneInfo

from btmm_ai_scanner.btrc.enums import SessionContext, VolatilityState
from btmm_ai_scanner.btrc.t4_assessment import SessionAssessment, VolatilityAssessment
from btmm_ai_scanner.btrc.t4_configuration import VolatilitySessionConfiguration
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.measurements.candle_metrics import median_total_range, total_range

_ZERO = Decimal("0")
_SUITABILITY = {
    VolatilityState.VERY_LOW: 40,
    VolatilityState.LOW: 75,
    VolatilityState.NORMAL: 100,
    VolatilityState.HIGH: 60,
    VolatilityState.EXTREME: 20,
}


def _ordered(candles: Sequence[NormalizedCandle]) -> list[NormalizedCandle]:
    return sorted(
        candles,
        key=lambda c: (c.availability_time_utc, c.event_time_utc, str(c.record_id)),
    )


def _state_for_percentile(
    percentile: Decimal, config: VolatilitySessionConfiguration
) -> VolatilityState:
    if percentile < config.percentile_very_low_max:
        return VolatilityState.VERY_LOW
    if percentile < config.percentile_low_max:
        return VolatilityState.LOW
    if percentile < config.percentile_normal_max:
        return VolatilityState.NORMAL
    if percentile < config.percentile_high_max:
        return VolatilityState.HIGH
    return VolatilityState.EXTREME


def assess_volatility(
    candles: Sequence[NormalizedCandle],
    configuration: VolatilitySessionConfiguration | None = None,
) -> VolatilityAssessment:
    config = configuration or VolatilitySessionConfiguration()
    ordered = _ordered(candles)
    if len(ordered) < config.atr_period:
        return VolatilityAssessment(
            timeframe=ordered[-1].timeframe if ordered else None,
            evaluation_time_utc=ordered[-1].availability_time_utc if ordered else None,
            volatility_state=VolatilityState.NORMAL,
            current_range=None,
            latest_atr=None,
            normalized_range=None,
            percentile=None,
            abnormal_spike=False,
            suitability_score=_SUITABILITY[VolatilityState.NORMAL],
            supporting_evidence=("insufficient history for volatility distribution",),
            opposing_evidence=(),
            provenance_ids=tuple(str(c.record_id) for c in ordered[-1:]),
        )

    window = ordered[-config.volatility_window :]
    ranges = [total_range(c) for c in window]
    current = ranges[-1]
    median = median_total_range(window)
    at_or_below = sum(1 for r in ranges if r <= current)
    percentile = Decimal(at_or_below) / Decimal(len(ranges))
    normalized = current / median if median > _ZERO else None
    abnormal = median > _ZERO and current >= config.abnormal_spike_multiplier * median
    atr_series = compute_atr_series(ordered, config.atr_period)
    latest_atr = next((v for v in reversed(atr_series) if v is not None), None)
    state = _state_for_percentile(percentile, config)

    supporting = [f"range percentile {percentile} over {len(ranges)} candles"]
    if abnormal:
        supporting.append("ABNORMAL_VOLATILITY_SPIKE (current range >> rolling median)")
    return VolatilityAssessment(
        timeframe=window[-1].timeframe,
        evaluation_time_utc=window[-1].availability_time_utc,
        volatility_state=state,
        current_range=current,
        latest_atr=latest_atr,
        normalized_range=normalized,
        percentile=percentile,
        abnormal_spike=abnormal,
        suitability_score=_SUITABILITY[state],
        supporting_evidence=tuple(supporting),
        opposing_evidence=(),
        provenance_ids=(str(window[-1].record_id),),
    )


def _minutes(hm: tuple[int, int]) -> int:
    return hm[0] * 60 + hm[1]


def assess_session(
    evaluation_time_utc: datetime,
    configuration: VolatilitySessionConfiguration | None = None,
) -> SessionAssessment:
    config = configuration or VolatilitySessionConfiguration()
    ldn = evaluation_time_utc.astimezone(ZoneInfo(config.london_timezone))
    ny = evaluation_time_utc.astimezone(ZoneInfo(config.new_york_timezone))
    ldn_min = ldn.hour * 60 + ldn.minute
    ny_min = ny.hour * 60 + ny.minute

    london_active = (
        _minutes(config.london_open) <= ldn_min < _minutes(config.london_close)
    )
    london_preopen = (
        _minutes(config.london_preopen_start) <= ldn_min < _minutes(config.london_open)
    )
    ny_active = (
        _minutes(config.new_york_open) <= ny_min < _minutes(config.new_york_close)
    )
    ny_preopen = (
        _minutes(config.new_york_preopen_start)
        <= ny_min
        < _minutes(config.new_york_open)
    )

    utc_hour = evaluation_time_utc.astimezone(ZoneInfo("UTC")).hour
    start, end = config.asian_start_hour_utc, config.asian_end_hour_utc
    in_asian = utc_hour >= start or utc_hour < end

    # Deterministic precedence. The New-York pre-open (07:00-08:00 NY local) always
    # falls inside London's active window, so it is given precedence over LONDON
    # active (the imminent-NY-open context is the salient one); otherwise active
    # sessions dominate pre-opens. Overlap (both active) dominates everything.
    if london_active and ny_active:
        context = SessionContext.LONDON_NY_OVERLAP
        why = "London and New York sessions both active"
    elif ny_active:
        context = SessionContext.NEW_YORK
        why = "New York session active"
    elif ny_preopen:
        context = SessionContext.NEW_YORK_PREOPEN
        why = "New York pre-open window (salient over concurrent London session)"
    elif london_active:
        context = SessionContext.LONDON
        why = "London session active"
    elif london_preopen:
        context = SessionContext.LONDON_PREOPEN
        why = "London pre-open window"
    elif in_asian:
        context = SessionContext.ASIAN
        why = "Asian session UTC window"
    else:
        context = SessionContext.POST_NY
        why = "after New York close, before Asian window"

    return SessionAssessment(
        evaluation_time_utc=evaluation_time_utc,
        session_context=context,
        london_local_time=ldn.isoformat(),
        new_york_local_time=ny.isoformat(),
        supporting_evidence=(why,),
    )
