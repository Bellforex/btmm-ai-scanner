"""BTRC-T4 volatility + session assessment contracts (immutable, explainable).

Volatility never determines direction. Session is context only. Neither generates
trades. ``volatility_suitability_score`` is a research ranking distinct from the
volatility LEVEL (EXTREME level = low suitability, not a direction).
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.btrc.enums import SessionContext, VolatilityState
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.types import ContractModel


class VolatilityAssessment(ContractModel):
    timeframe: Timeframe | None
    evaluation_time_utc: datetime | None
    volatility_state: VolatilityState
    current_range: Decimal | None
    latest_atr: Decimal | None
    normalized_range: Decimal | None  # current range / rolling median range
    percentile: Decimal | None
    abnormal_spike: bool
    suitability_score: int  # 0-100 provisional; separate from the level
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    provenance_ids: tuple[str, ...]


class SessionAssessment(ContractModel):
    evaluation_time_utc: datetime
    session_context: SessionContext
    london_local_time: str
    new_york_local_time: str
    supporting_evidence: tuple[str, ...]
