"""BTRC-T2 regime assessment output contracts (immutable, explainable).

Regime is a direction-INDEPENDENT behaviour dimension. These contracts carry no
polarity, no score, no trade instruction. ``trend_state`` is included per
timeframe only as reused T1 context (never as a substitute for regime).
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import Regime, TrendState
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel


class TimeframeRegimeAssessment(ContractModel):
    timeframe: Timeframe
    regime: Regime
    trend_state: TrendState  # reused T1 context, not a regime substitute
    evaluation_time_utc: datetime | None
    recent_displacement_count: int
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    structure_reference_ids: tuple[str, ...]


class RegimeAssessment(ContractModel):
    symbol: InternalSymbol | None
    evaluation_time_utc: datetime | None
    regime: Regime  # primary (D1 / highest-authority present)
    timeframe_regimes: tuple[TimeframeRegimeAssessment, ...]
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]
