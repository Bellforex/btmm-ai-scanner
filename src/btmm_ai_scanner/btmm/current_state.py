from datetime import datetime

from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmContextAlignmentStatus,
    BtmmDirection,
    BtmmEvidenceSource,
    BtmmFormationStage,
    BtmmGateStatus,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLiquidityEvidenceStatus,
    BtmmLiquidityLocation,
    BtmmReactionClassification,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.measurements.legs import LegSpeedClassification
from btmm_ai_scanner.poi.enums import PoiType


class CurrentBtmmState(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    btmm_setup_record_id: UUIDv7
    btmm_direction: BtmmDirection
    source_poi_type: PoiType
    primary_state: BtmmLifecycleStatus
    formation_stage: BtmmFormationStage | None
    market_direction_status: BtmmContextAlignmentStatus
    analytical_framework_status: BtmmContextAlignmentStatus
    session_status: BtmmSessionStatus
    accuracy_gate_status: BtmmGateStatus
    interaction_class: BtmmInteractionClass | None
    reaction_gate_status: BtmmGateStatus
    reaction_classification: BtmmReactionClassification | None
    reaction_speed_gate_status: BtmmGateStatus
    reaction_speed_classification: LegSpeedClassification | None
    formation_timeframe_gate_status: BtmmGateStatus
    volume_pillar_status: BtmmVolumePillarStatus
    liquidity_evidence_status: BtmmLiquidityEvidenceStatus
    liquidity_location: BtmmLiquidityLocation | None
    liquidity_evidence_source: BtmmEvidenceSource | None
    reviewed_evidence_availability_time_utc: datetime | None
    cancellation_reason: BtmmCancellationReason | None
    blocked_reason: BtmmBlockedReason | None
    latest_lifecycle_transition_id: UUIDv7 | None
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
