from datetime import datetime

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis
from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmDirection,
    BtmmInteractionClass,
    BtmmLifecycleStatus,
    BtmmLiquidityEvidenceStatus,
    BtmmReactionClassification,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, UUIDv7
from btmm_ai_scanner.domain.analyzer import MarketMeasurementAnalysis
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiType
from btmm_ai_scanner.structure.analyzer import StructureAnalysis


class ScannerSetupSummary(ContractModel):
    source_btmm_observation_record_id: UUIDv7
    source_poi_record_id: UUIDv7
    symbol: InternalSymbol
    btmm_direction: BtmmDirection
    source_poi_type: PoiType
    timeframe: Timeframe
    poi_lifecycle_status: PoiLifecycleStatus | None
    btmm_primary_state: BtmmLifecycleStatus
    interaction_class: BtmmInteractionClass | None
    reaction_classification: BtmmReactionClassification | None
    liquidity_evidence_status: BtmmLiquidityEvidenceStatus
    market_direction_status: BtmmContextAlignmentStatus
    analytical_framework_status: BtmmContextAlignmentStatus
    volume_pillar_status: BtmmVolumePillarStatus
    availability_time_utc: datetime
    evidence_classification: EvidenceClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer


class ScannerAnalysis(ContractModel):
    symbol: InternalSymbol | None
    processed_timeframes: tuple[Timeframe, ...]
    measurement_analyses: tuple[MarketMeasurementAnalysis, ...]
    structure_analyses: tuple[StructureAnalysis, ...]
    poi_analysis: PoiAnalysis
    btmm_analysis: BtmmAnalysis
    setup_summaries: tuple[ScannerSetupSummary, ...]
    availability_time_utc: datetime
    evidence_classification: EvidenceClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
