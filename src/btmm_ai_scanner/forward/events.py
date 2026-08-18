"""Forward scanner alert events (A7A).

Scanner-INFORMATION events only. There is deliberately no BUY/SELL, entry, SL,
TP, or order concept here — alerts describe what the scanner observed, nothing
about trading actions.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel


class ScannerEventType(StrEnum):
    NEW_POI = "NEW_POI"
    POI_RETEST = "POI_RETEST"
    POI_BREACH = "POI_BREACH"
    POI_RECLAIM = "POI_RECLAIM"
    POI_INVALIDATION = "POI_INVALIDATION"
    NEW_BTMM_SETUP = "NEW_BTMM_SETUP"
    BTMM_LIFECYCLE_TRANSITION = "BTMM_LIFECYCLE_TRANSITION"
    DATA_QUALITY_WARNING = "DATA_QUALITY_WARNING"


class ScannerAlert(ContractModel):
    """One forward scanner-information event, tied to the availability-group
    sequence at which it was observed (proving what the scanner knew when)."""

    event_type: ScannerEventType
    group_sequence: int
    availability_time_utc: datetime
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    record_id: str | None
    detail: str
