"""BTRC-T5 standardized analytical decision object (immutable).

Combines the supervisory analytical dimensions WITHOUT destroying their
independence. Hard analytical truths (``poi_valid``, ``btmm_valid``,
``global_direction``, states) are recorded separately from the SOFT component
scores and ``final_confluence_score``; a soft score never overrides a hard
contract. There are deliberately NO operational fields (entry / stop / target /
lot size / order id / execution command) — those belong to future python-bot
phases only.
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    BreakoutState,
    Direction,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
    Regime,
    SessionContext,
    SignalLifecycleState,
    TrendAlignment,
    VolatilityState,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus, PoiType


class ComponentScores(ContractModel):
    """Independent 0-100 research rankings — never collapsed irreversibly."""

    btmm_score: int
    poi_score: int
    trend_score: int
    regime_score: int
    momentum_score: int
    breakout_score: int
    liquidity_score: int
    volatility_score: int


class BtrcDecision(ContractModel):
    symbol: InternalSymbol | None
    evaluation_time_utc: datetime | None

    # --- hard analytical truths (never overridden by scores) ---
    poi_record_id: str
    poi_timeframe: Timeframe
    # Derived higher-timeframe overlap context (the merged effective timeframe
    # when it differs from the source). Informational: no score reads it.
    higher_tf_context: Timeframe | None = None
    poi_type: PoiType
    poi_direction: PoiDirection
    poi_valid: bool
    poi_lifecycle_status: PoiLifecycleStatus | None
    btmm_valid: bool

    global_direction: Direction
    regime: Regime

    momentum_direction: MomentumDirection | None
    momentum_acceleration: MomentumAcceleration | None
    breakout_state: BreakoutState | None
    pullback_state: PullbackState | None
    volatility_state: VolatilityState | None
    session_context: SessionContext | None

    # --- soft ranking ---
    component_scores: ComponentScores
    final_confluence_score: int

    # --- supervisory classification ---
    trend_alignment: TrendAlignment
    analytical_permission: AnalyticalPermission
    lifecycle_state: SignalLifecycleState

    # --- explainability ---
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]
    missing_components: tuple[str, ...]
    rejection_or_watch_reasons: tuple[str, ...]
    provenance_ids: tuple[str, ...]
    # --- RC4 market framework (defaults when the profile is off) ---
    framework: str | None = None
    fib_bucket: str | None = None
    retracement_pct: str | None = None
    range_position: str | None = None
    sweep_before_poi: bool = False
    btmm_pretrade_reason: str | None = None
    btmm_distraction: bool = False
    btmm_delay: bool = False
    btmm_wipeout: bool = False
    btmm_true_failure: bool = False
    poi_dwell_bars: int = 0
    poi_touch_count: int = 0
    poi_zone_return_count: int = 0
    interaction_episode: str | None = None
    first_touch_time_utc: datetime | None = None
    episode_start_time_utc: datetime | None = None
    episode_end_time_utc: datetime | None = None
    framework_evidence: tuple[str, ...] = ()
