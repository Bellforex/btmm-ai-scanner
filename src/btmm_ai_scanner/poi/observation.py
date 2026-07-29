from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiStrengthTier, PoiType


class PoiObservation(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    source_timeframe: Timeframe
    effective_timeframe: Timeframe
    family: PoiFamily
    poi_type: PoiType
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    representative_price: Decimal | None
    strength_tier: PoiStrengthTier | None
    source_candle_record_ids: tuple[UUIDv7, ...]
    source_measurement_record_ids: tuple[UUIDv7, ...]
    merged_source_poi_record_ids: tuple[UUIDv7, ...]
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
