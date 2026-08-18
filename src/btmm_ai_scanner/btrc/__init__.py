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

__all__ = [
    "AnalyticalPermission",
    "BreakoutState",
    "Direction",
    "ExecutionPriority",
    "MomentumAcceleration",
    "MomentumDirection",
    "PinePortability",
    "PullbackState",
    "Regime",
    "SessionContext",
    "SignalLifecycleState",
    "TrendAlignment",
    "TrendState",
    "VolatilityState",
]
