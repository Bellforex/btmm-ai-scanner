from datetime import datetime

from btmm_ai_scanner.btmm.enums import BtmmDirection
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


class BtmmObservation(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    source_timeframe: Timeframe
    btmm_direction: BtmmDirection
    source_poi_record_id: UUIDv7
    source_poi_type: PoiType
    source_poi_direction: PoiDirection
    candidate_event_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
