"""BTRC-T1 trend assessment output contracts.

Immutable, explainable trend results. They carry Direction/TrendState (frozen
T0 dimensions), human-readable supporting/opposing evidence, and provenance
references (record ids of the exact scanner structure/swing records consulted).
They contain NO confluence score, NO entry/stop/target, and NO trade
instruction — trend classification is supervisory only.
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.enums import Direction, TrendState
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel


class TimeframeTrendAssessment(ContractModel):
    timeframe: Timeframe
    direction: Direction
    trend_state: TrendState
    evaluation_time_utc: datetime | None
    # deterministic structural evidence (counts, not scores)
    analyzed_swing_count: int
    continuation_streak: int
    # explainability
    supporting_evidence: tuple[str, ...]
    opposing_evidence: tuple[str, ...]
    # provenance: record ids of the structure transitions / swings consulted
    structure_reference_ids: tuple[str, ...]


class TrendAssessment(ContractModel):
    symbol: InternalSymbol | None
    evaluation_time_utc: datetime | None
    global_direction: Direction
    macro_context: Direction  # W1 direction (or NEUTRAL if absent)
    operational_context: Direction  # H4 direction (or NEUTRAL if absent)
    timeframe_assessments: tuple[TimeframeTrendAssessment, ...]
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]
