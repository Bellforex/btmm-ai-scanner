"""BTRC-T3 momentum / breakout / pullback assessment contracts.

Immutable, explainable, per-timeframe. Categorical states stand alone; the 0-100
scores are provisional research rankings, never a trade instruction. Breakout and
pullback states are ``| None`` (absence is modelled as None, matching the frozen
T0 enums which have no NONE member).
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import (
    BreakoutState,
    MomentumAcceleration,
    MomentumDirection,
    PullbackState,
)
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.types import ContractModel


class TimeframeMomentumAssessment(ContractModel):
    timeframe: Timeframe
    direction: MomentumDirection
    acceleration: MomentumAcceleration
    momentum_score: int  # 0-100 provisional research ranking
    evaluation_time_utc: datetime | None
    displacement_count: int
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    provenance_ids: tuple[str, ...]


class TimeframeBreakoutAssessment(ContractModel):
    timeframe: Timeframe
    breakout_state: BreakoutState | None
    breakout_score: int  # 0-100 provisional; 0 when no active breakout
    evaluation_time_utc: datetime | None
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    provenance_ids: tuple[str, ...]


class TimeframePullbackAssessment(ContractModel):
    timeframe: Timeframe
    pullback_state: PullbackState | None
    evaluation_time_utc: datetime | None
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    provenance_ids: tuple[str, ...]
