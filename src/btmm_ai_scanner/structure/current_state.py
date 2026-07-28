from datetime import datetime

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.structure.enums import StructureDirection


class CurrentStructureState(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    direction: StructureDirection
    active_protected_high_swing_id: UUIDv7 | None
    active_protected_low_swing_id: UUIDv7 | None
    active_weak_high_swing_id: UUIDv7 | None
    active_weak_low_swing_id: UUIDv7 | None
    latest_transition_id: UUIDv7 | None
    availability_time_utc: datetime
    analyzed_swing_count: int
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
