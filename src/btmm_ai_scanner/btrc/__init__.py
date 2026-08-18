"""BTRC-V1 — BTMM Trend & Regime Confluence Layer (T0 interface freeze).

BTRC is an ADDITIONAL supervisory analytical layer over the validated scanner.
It never creates trades, never overrides the POI/BTMM engines, and — as of T0 —
contains NO strategy logic, thresholds, or execution. This package currently
exposes only the frozen, independently-observable state DIMENSIONS (typed
enums) so downstream engines (T1..T5) and the future Pine port share one
interface. All semantic computation is deferred to later authorized phases.
"""

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    BreakoutState,
    Direction,
    ExecutionPriority,
    MomentumAcceleration,
    MomentumDirection,
    PinePortability,
    PullbackState,
    Regime,
    SessionContext,
    SignalLifecycleState,
    TrendAlignment,
    TrendState,
    VolatilityState,
)
from btmm_ai_scanner.btrc.regime_assessment import (
    RegimeAssessment,
    TimeframeRegimeAssessment,
)
from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.regime_engine import assess_regime
from btmm_ai_scanner.btrc.t3_assessment import (
    TimeframeBreakoutAssessment,
    TimeframeMomentumAssessment,
    TimeframePullbackAssessment,
)
from btmm_ai_scanner.btrc.t3_configuration import (
    MomentumBreakoutPullbackConfiguration,
)
from btmm_ai_scanner.btrc.t3_engine import (
    assess_breakout,
    assess_momentum,
    assess_pullback,
)
from btmm_ai_scanner.btrc.t4_assessment import SessionAssessment, VolatilityAssessment
from btmm_ai_scanner.btrc.t4_configuration import VolatilitySessionConfiguration
from btmm_ai_scanner.btrc.t4_engine import assess_session, assess_volatility
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision, ComponentScores
from btmm_ai_scanner.btrc.t5_engine import assess_confluence, latest_poi
from btmm_ai_scanner.btrc.trend_assessment import (
    TimeframeTrendAssessment,
    TrendAssessment,
)
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration
from btmm_ai_scanner.btrc.trend_engine import assess_trend

__all__ = [
    "AnalyticalPermission",
    "BreakoutState",
    "BtrcDecision",
    "ComponentScores",
    "ConfluenceConfiguration",
    "Direction",
    "ExecutionPriority",
    "MomentumAcceleration",
    "MomentumBreakoutPullbackConfiguration",
    "MomentumDirection",
    "PinePortability",
    "PullbackState",
    "Regime",
    "RegimeAssessment",
    "RegimeEngineConfiguration",
    "SessionAssessment",
    "SessionContext",
    "SignalLifecycleState",
    "TimeframeBreakoutAssessment",
    "TimeframeMomentumAssessment",
    "TimeframePullbackAssessment",
    "TimeframeRegimeAssessment",
    "TimeframeTrendAssessment",
    "TrendAlignment",
    "TrendAssessment",
    "TrendEngineConfiguration",
    "TrendState",
    "VolatilityAssessment",
    "VolatilitySessionConfiguration",
    "VolatilityState",
    "assess_breakout",
    "assess_confluence",
    "assess_momentum",
    "assess_pullback",
    "assess_regime",
    "assess_session",
    "assess_trend",
    "assess_volatility",
    "latest_poi",
]
