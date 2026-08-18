"""BTRC-V1 frozen state dimensions (T0).

Each dimension is INDEPENDENT and separately observable — direction is not
trend-state, trend-state is not regime, regime is not volatility, momentum is
not trend. These enums freeze the interface only; they carry no thresholds, no
transition logic, and no strategy. Members marked ENGINEERING-PROVISIONAL in the
T0 architecture doc may be revised before T1..T5 are approved, but the enum
NAMES are the contract downstream engines and the Pine port target.
"""

from enum import StrEnum


class Direction(StrEnum):
    """Directional bias of a single observed context (per timeframe or global).
    Independent of trend-state and regime."""

    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class TrendState(StrEnum):
    """Structural trend PHASE, direction-neutral by design (a TRENDING state
    carries no direction — direction is reported separately)."""

    UNKNOWN = "UNKNOWN"
    FORMING = "FORMING"
    TRENDING = "TRENDING"
    EXHAUSTING = "EXHAUSTING"
    TRANSITION = "TRANSITION"
    RANGE = "RANGE"


class Regime(StrEnum):
    """Volatility/expansion REGIME of price behaviour. Not a direction and not a
    volatility magnitude."""

    COMPRESSION = "COMPRESSION"
    BREAKOUT_PENDING = "BREAKOUT_PENDING"
    EXPANSION = "EXPANSION"
    TREND = "TREND"
    DECELERATION = "DECELERATION"
    RANGE = "RANGE"
    TRANSITION = "TRANSITION"
    UNCERTAIN = "UNCERTAIN"


class MomentumDirection(StrEnum):
    """Momentum bias — distinct from structural Direction (momentum can oppose
    the structural direction during a pullback)."""

    STRONG_BULLISH = "STRONG_BULLISH"
    BULLISH = "BULLISH"
    NEUTRAL = "NEUTRAL"
    BEARISH = "BEARISH"
    STRONG_BEARISH = "STRONG_BEARISH"


class MomentumAcceleration(StrEnum):
    """Rate-of-change state of momentum (separate axis from momentum direction)."""

    ACCELERATING = "ACCELERATING"
    STEADY = "STEADY"
    DECELERATING = "DECELERATING"


class BreakoutState(StrEnum):
    """Classification of a structural break event. Absence of a break is modelled
    as ``None`` in the decision object (no NONE member)."""

    WEAK_BREAK = "WEAK_BREAK"
    VALID_BREAK = "VALID_BREAK"
    STRONG_BREAK = "STRONG_BREAK"
    EXPLOSIVE_BREAK = "EXPLOSIVE_BREAK"
    FAILED_BREAK = "FAILED_BREAK"
    LIQUIDITY_SWEEP = "LIQUIDITY_SWEEP"


class PullbackState(StrEnum):
    """Classification of a retracement. Absence of a pullback is modelled as
    ``None`` in the decision object (no NONE member)."""

    SHALLOW_PULLBACK = "SHALLOW_PULLBACK"
    HEALTHY_PULLBACK = "HEALTHY_PULLBACK"
    DEEP_PULLBACK = "DEEP_PULLBACK"
    STRUCTURAL_FAILURE = "STRUCTURAL_FAILURE"


class VolatilityState(StrEnum):
    """Volatility magnitude band. Never determines direction; for the FUTURE bot
    it may gate permission/sizing/management (none implemented in T0)."""

    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class SessionContext(StrEnum):
    """Trading-session context. Never independently triggers a trade."""

    ASIAN = "ASIAN"
    LONDON_PREOPEN = "LONDON_PREOPEN"
    LONDON = "LONDON"
    NEW_YORK_PREOPEN = "NEW_YORK_PREOPEN"
    NEW_YORK = "NEW_YORK"
    LONDON_NY_OVERLAP = "LONDON_NY_OVERLAP"
    POST_NY = "POST_NY"


class TrendAlignment(StrEnum):
    """How an otherwise-valid POI/BTMM opportunity relates to prevailing trend.
    COUNTER_TREND never invalidates the POI/BTMM — it only lowers execution
    priority (see ExecutionPriority / AnalyticalPermission)."""

    ALIGNED = "ALIGNED"
    PARTIAL = "PARTIAL"
    NEUTRAL = "NEUTRAL"
    COUNTER_TREND = "COUNTER_TREND"


class ExecutionPriority(StrEnum):
    """Analytical priority of an opportunity — NOT an execution instruction."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    WATCH_ONLY = "WATCH_ONLY"


class AnalyticalPermission(StrEnum):
    """Analytical bias/permission context. NOT a broker execution instruction."""

    BUY_BIAS = "BUY_BIAS"
    SELL_BIAS = "SELL_BIAS"
    ALLOW_BOTH_CONTEXT = "ALLOW_BOTH_CONTEXT"
    COUNTER_TREND = "COUNTER_TREND"
    WATCH_ONLY = "WATCH_ONLY"
    NO_TRADE_CONTEXT = "NO_TRADE_CONTEXT"


class SignalLifecycleState(StrEnum):
    """Full candidate lifecycle. States DETECTED..LIQUIDITY_VALIDATED are the
    ANALYTICAL BTRC scope; RISK_VALIDATED..CLOSED are FUTURE PYTHON-BOT scope and
    are frozen here only so the interface is complete (not implemented in T0)."""

    DETECTED = "DETECTED"
    STRUCTURALLY_VALIDATED = "STRUCTURALLY_VALIDATED"
    BTMM_VALIDATED = "BTMM_VALIDATED"
    POI_VALIDATED = "POI_VALIDATED"
    TREND_VALIDATED = "TREND_VALIDATED"
    REGIME_VALIDATED = "REGIME_VALIDATED"
    MOMENTUM_VALIDATED = "MOMENTUM_VALIDATED"
    LIQUIDITY_VALIDATED = "LIQUIDITY_VALIDATED"
    # --- boundary: everything below is FUTURE PYTHON BOT, not BTRC analytics ---
    RISK_VALIDATED = "RISK_VALIDATED"
    EXECUTION_READY = "EXECUTION_READY"
    TRIGGERED = "TRIGGERED"
    MANAGED = "MANAGED"
    CLOSED = "CLOSED"


class PinePortability(StrEnum):
    """Classifies how faithfully a BTRC feature can be reproduced in Pine Script.
    Metadata only — does not authorize Pine implementation."""

    PINE_PORTABLE_EXACT = "PINE_PORTABLE_EXACT"
    PINE_PORTABLE_WITH_ADAPTATION = "PINE_PORTABLE_WITH_ADAPTATION"
    PYTHON_ONLY = "PYTHON_ONLY"
    REQUIRES_VALIDATION = "REQUIRES_VALIDATION"


# Boundary marker (documentation-in-code): the analytical BTRC lifecycle states
# vs the future python-bot states. No behaviour attaches to this tuple; it exists
# so the freeze is machine-checkable by the T0 contract test.
ANALYTICAL_LIFECYCLE_STATES: tuple[SignalLifecycleState, ...] = (
    SignalLifecycleState.DETECTED,
    SignalLifecycleState.STRUCTURALLY_VALIDATED,
    SignalLifecycleState.BTMM_VALIDATED,
    SignalLifecycleState.POI_VALIDATED,
    SignalLifecycleState.TREND_VALIDATED,
    SignalLifecycleState.REGIME_VALIDATED,
    SignalLifecycleState.MOMENTUM_VALIDATED,
    SignalLifecycleState.LIQUIDITY_VALIDATED,
)
FUTURE_BOT_LIFECYCLE_STATES: tuple[SignalLifecycleState, ...] = (
    SignalLifecycleState.RISK_VALIDATED,
    SignalLifecycleState.EXECUTION_READY,
    SignalLifecycleState.TRIGGERED,
    SignalLifecycleState.MANAGED,
    SignalLifecycleState.CLOSED,
)
