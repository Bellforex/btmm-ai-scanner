"""BTRC-T2 deterministic regime engine.

Regime is a direction-INDEPENDENT behaviour dimension. It reuses the T1
trend-state (itself direction-neutral) as the structural backbone and refines the
non-directional forming phase with existing scanner displacement evidence
(``range_speed_ratio`` / ``total_range``). It never re-derives structure or
displacement, never mutates a scanner record, and never encodes bullish/bearish
polarity.

Deterministic precedence (highest first):
    UNCERTAIN > TRANSITION > TREND > DECELERATION > RANGE
    > EXPANSION > BREAKOUT_PENDING > COMPRESSION
so simultaneous evidence never depends on dict/event arrival order.
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import Regime, TrendState
from btmm_ai_scanner.btrc.regime_assessment import (
    RegimeAssessment,
    TimeframeRegimeAssessment,
)
from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.trend_assessment import TimeframeTrendAssessment
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import assess_trend
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK

# Primary-regime authority order (D1 primary, then operational/macro, then lower).
_PRIMARY_ORDER: tuple[Timeframe, ...] = (
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.W1,
    Timeframe.H1,
    Timeframe.M15,
    Timeframe.M5,
)


def _recent_displacements(
    observations: tuple[DisplacementObservation, ...], window: int
) -> list[DisplacementObservation]:
    ordered = sorted(
        observations,
        key=lambda o: (o.availability_time_utc, o.event_time_utc, str(o.record_id)),
    )
    return ordered[-window:]


def _regime_for_timeframe(
    trend: TimeframeTrendAssessment,
    displacements: tuple[DisplacementObservation, ...],
    config: RegimeEngineConfiguration,
) -> TimeframeRegimeAssessment:
    supporting: list[str] = []
    opposing: list[str] = []
    recent = _recent_displacements(displacements, config.recent_displacement_window)
    recent_count = len(recent)

    # Non-forming states map 1:1 from the (direction-neutral) T1 trend state, by
    # the documented precedence. Forming is refined by displacement.
    if trend.trend_state is TrendState.UNKNOWN:
        regime = Regime.UNCERTAIN
        supporting.append("insufficient structure to classify regime")
    elif trend.trend_state is TrendState.TRANSITION:
        regime = Regime.TRANSITION
        supporting.append("confirmed structural transition; prior regime failed")
    elif trend.trend_state is TrendState.TRENDING:
        regime = Regime.TREND
        supporting.append(
            f"persistent directional structure ({trend.continuation_streak} BOS)"
        )
    elif trend.trend_state is TrendState.EXHAUSTING:
        regime = Regime.DECELERATION
        supporting.append("directional structure valid but continuation weakening")
    elif trend.trend_state is TrendState.RANGE:
        regime = Regime.RANGE
        supporting.append("alternating / bounded non-directional structure")
    else:  # TrendState.FORMING
        fast = [
            d for d in recent if d.range_speed_ratio >= config.expansion_speed_ratio
        ]
        if fast:
            regime = Regime.EXPANSION
            supporting.append(
                f"recent range expansion (speed ratio >= {config.expansion_speed_ratio})"
            )
        elif recent_count > 0:
            regime = Regime.BREAKOUT_PENDING
            supporting.append(
                f"{recent_count} recent displacement(s) building; break unconfirmed"
            )
        else:
            regime = Regime.COMPRESSION
            supporting.append("no recent displacement; contained / contracting")

    return TimeframeRegimeAssessment(
        timeframe=trend.timeframe,
        regime=regime,
        trend_state=trend.trend_state,
        evaluation_time_utc=trend.evaluation_time_utc,
        recent_displacement_count=recent_count,
        supporting_evidence=tuple(supporting),
        opposing_evidence=tuple(opposing),
        structure_reference_ids=trend.structure_reference_ids,
    )


def assess_regime(
    analysis: ScannerAnalysis,
    trend_configuration: TrendEngineConfiguration | None = None,
    regime_configuration: RegimeEngineConfiguration | None = None,
) -> RegimeAssessment:
    config = regime_configuration or RegimeEngineConfiguration()
    trend = assess_trend(analysis, trend_configuration)
    displacements_by_tf: dict[Timeframe, tuple[DisplacementObservation, ...]] = {}
    for measurement in analysis.measurement_analyses:
        if measurement.timeframe is not None:
            displacements_by_tf[measurement.timeframe] = (
                measurement.displacement_observations
            )

    timeframe_regimes: list[TimeframeRegimeAssessment] = []
    regime_by_tf: dict[Timeframe, Regime] = {}
    for tf_trend in trend.timeframe_assessments:
        assessment = _regime_for_timeframe(
            tf_trend, displacements_by_tf.get(tf_trend.timeframe, ()), config
        )
        timeframe_regimes.append(assessment)
        regime_by_tf[assessment.timeframe] = assessment.regime
    timeframe_regimes.sort(key=lambda a: _TIMEFRAME_RANK[a.timeframe])

    primary_timeframe = next((tf for tf in _PRIMARY_ORDER if tf in regime_by_tf), None)
    primary_regime = (
        regime_by_tf[primary_timeframe]
        if primary_timeframe is not None
        else Regime.UNCERTAIN
    )
    supporting_reasons: tuple[str, ...] = ()
    if primary_timeframe is not None:
        supporting_reasons = (
            f"{primary_timeframe.value} regime {primary_regime.value} (primary)",
        )

    evaluation_time: datetime | None = analysis.availability_time_utc
    return RegimeAssessment(
        symbol=analysis.symbol,
        evaluation_time_utc=evaluation_time,
        regime=primary_regime,
        timeframe_regimes=tuple(timeframe_regimes),
        supporting_reasons=supporting_reasons,
        opposing_reasons=(),
    )
