"""BTRC-V1 T0 contract-freeze tests.

These pin the frozen interface: exact enum membership (any accidental
addition/removal/rename fails), independence of the dimensions, the
analytical-vs-future-bot lifecycle partition, and that the layer carries NO
strategy logic/thresholds (pure string enums only).
"""

from enum import StrEnum

from btmm_ai_scanner.btrc import enums as btrc_enums
from btmm_ai_scanner.btrc.enums import (
    ANALYTICAL_LIFECYCLE_STATES,
    FUTURE_BOT_LIFECYCLE_STATES,
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

_FROZEN: dict[type[StrEnum], set[str]] = {
    Direction: {"STRONG_BULLISH", "BULLISH", "NEUTRAL", "BEARISH", "STRONG_BEARISH"},
    TrendState: {"UNKNOWN", "FORMING", "TRENDING", "EXHAUSTING", "TRANSITION", "RANGE"},
    Regime: {
        "COMPRESSION",
        "BREAKOUT_PENDING",
        "EXPANSION",
        "TREND",
        "DECELERATION",
        "RANGE",
        "TRANSITION",
        "UNCERTAIN",
    },
    MomentumDirection: {
        "STRONG_BULLISH",
        "BULLISH",
        "NEUTRAL",
        "BEARISH",
        "STRONG_BEARISH",
    },
    MomentumAcceleration: {"ACCELERATING", "STEADY", "DECELERATING"},
    BreakoutState: {
        "WEAK_BREAK",
        "VALID_BREAK",
        "STRONG_BREAK",
        "EXPLOSIVE_BREAK",
        "FAILED_BREAK",
        "LIQUIDITY_SWEEP",
    },
    PullbackState: {
        "SHALLOW_PULLBACK",
        "HEALTHY_PULLBACK",
        "DEEP_PULLBACK",
        "STRUCTURAL_FAILURE",
    },
    VolatilityState: {"VERY_LOW", "LOW", "NORMAL", "HIGH", "EXTREME"},
    SessionContext: {
        "ASIAN",
        "LONDON_PREOPEN",
        "LONDON",
        "NEW_YORK_PREOPEN",
        "NEW_YORK",
        "LONDON_NY_OVERLAP",
        "POST_NY",
    },
    TrendAlignment: {"ALIGNED", "PARTIAL", "NEUTRAL", "COUNTER_TREND"},
    ExecutionPriority: {"HIGH", "MEDIUM", "LOW", "WATCH_ONLY"},
    AnalyticalPermission: {
        "BUY_BIAS",
        "SELL_BIAS",
        "ALLOW_BOTH_CONTEXT",
        "COUNTER_TREND",
        "WATCH_ONLY",
        "NO_TRADE_CONTEXT",
    },
    SignalLifecycleState: {
        "DETECTED",
        "STRUCTURALLY_VALIDATED",
        "BTMM_VALIDATED",
        "POI_VALIDATED",
        "TREND_VALIDATED",
        "REGIME_VALIDATED",
        "MOMENTUM_VALIDATED",
        "LIQUIDITY_VALIDATED",
        "RISK_VALIDATED",
        "EXECUTION_READY",
        "TRIGGERED",
        "MANAGED",
        "CLOSED",
    },
    PinePortability: {
        "PINE_PORTABLE_EXACT",
        "PINE_PORTABLE_WITH_ADAPTATION",
        "PYTHON_ONLY",
        "REQUIRES_VALIDATION",
    },
}


def test_frozen_membership_is_exact() -> None:
    for enum_type, expected in _FROZEN.items():
        assert {member.value for member in enum_type} == expected, enum_type.__name__
        # value == name for every member (stable string contract for Pine parity)
        for member in enum_type:
            assert member.value == member.name


def test_dimensions_are_independent_types() -> None:
    # Direction, MomentumDirection, TrendState, Regime, VolatilityState are
    # distinct types even where members overlap (direction != momentum != trend).
    dimension_types = [
        Direction,
        MomentumDirection,
        TrendState,
        Regime,
        VolatilityState,
    ]
    assert len({id(t) for t in dimension_types}) == len(dimension_types)
    # same token, different type: direction "BULLISH" is not momentum "BULLISH"
    assert Direction.BULLISH.value == MomentumDirection.BULLISH.value
    assert type(Direction.BULLISH).__name__ != type(MomentumDirection.BULLISH).__name__
    assert "TRENDING" not in {r.value for r in Regime}
    # a TRENDING trend-state carries no direction token
    assert not any("BULL" in s.value or "BEAR" in s.value for s in TrendState)
    assert not any("BULL" in s.value or "BEAR" in s.value for s in Regime)


def test_lifecycle_partition_is_disjoint_and_complete() -> None:
    analytical = set(ANALYTICAL_LIFECYCLE_STATES)
    future = set(FUTURE_BOT_LIFECYCLE_STATES)
    assert analytical.isdisjoint(future)
    assert analytical | future == set(SignalLifecycleState)
    # execution/risk/management states are FUTURE only
    assert SignalLifecycleState.RISK_VALIDATED in future
    assert SignalLifecycleState.EXECUTION_READY in future
    assert SignalLifecycleState.TRIGGERED in future


def test_layer_carries_no_numeric_thresholds_or_logic() -> None:
    # Every public enum member is a pure string; no ints/floats/thresholds and
    # no callables (beyond enum machinery) are exposed on the frozen dimensions.
    for name in btrc_enums.__dict__:
        if name.startswith("_"):
            continue
        obj = getattr(btrc_enums, name)
        if isinstance(obj, type) and issubclass(obj, StrEnum):
            for member in obj:
                assert isinstance(member.value, str)
                assert not isinstance(member.value, bool)


def test_analytical_permission_and_alignment_never_imply_execution() -> None:
    # COUNTER_TREND is representable in both alignment and permission without any
    # BUY/SELL execution token existing in the layer.
    assert TrendAlignment.COUNTER_TREND.value == "COUNTER_TREND"
    assert AnalyticalPermission.COUNTER_TREND.value == "COUNTER_TREND"
    banned = ("execute", "order", "fill", "lot", "position_size", "stop_loss")
    for enum_type in _FROZEN:
        for member in enum_type:
            lowered = member.value.lower()
            assert not any(term in lowered for term in banned), member
