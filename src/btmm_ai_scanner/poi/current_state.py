from datetime import datetime, timedelta

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiTapClassification,
    PoiType,
)


class CurrentPoiState(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_record_id: UUIDv7
    poi_type: PoiType
    direction: PoiDirection
    poi_lifecycle_status: PoiLifecycleStatus
    freshness_status: PoiFreshnessStatus
    tap_count: int
    tap_classification: PoiTapClassification | None
    age_start_time_utc: datetime
    age_in_confirmed_bars: int
    elapsed_time_since_availability: timedelta
    latest_lifecycle_transition_id: UUIDv7 | None
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
