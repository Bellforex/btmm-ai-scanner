from datetime import datetime

from pydantic import field_validator

from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmLiquidityEvidenceStatus,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import to_utc
from btmm_ai_scanner.contracts.types import ContractModel, SemVer, UUIDv7

CONTEXT_AND_LIQUIDITY_ALLOWED_SOURCES: frozenset[BtmmEvidenceSource] = frozenset(
    {
        BtmmEvidenceSource.EXPERT_LABELLED,
        BtmmEvidenceSource.HYBRID_REVIEWED,
        BtmmEvidenceSource.RULE_BASED_REVIEWED,
    }
)

VOLUME_ALLOWED_SOURCES: frozenset[BtmmEvidenceSource] = frozenset(
    {
        BtmmEvidenceSource.EXPERT_LABELLED,
        BtmmEvidenceSource.HYBRID_REVIEWED,
    }
)


class BtmmReviewedEvidence(ContractModel):
    symbol: InternalSymbol
    timeframe: Timeframe
    source_poi_record_id: UUIDv7
    market_direction_status: BtmmContextAlignmentStatus
    analytical_framework_status: BtmmContextAlignmentStatus
    session_status: BtmmSessionStatus
    liquidity_evidence_status: BtmmLiquidityEvidenceStatus
    volume_pillar_status: BtmmVolumePillarStatus
    context_input_source: BtmmEvidenceSource
    liquidity_event_source: BtmmEvidenceSource
    volume_evidence_source: BtmmEvidenceSource
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer

    @field_validator("availability_time_utc")
    @classmethod
    def _normalize_availability(cls, value: datetime) -> datetime:
        return to_utc(value)

    @field_validator("context_input_source", "liquidity_event_source")
    @classmethod
    def _validate_context_and_liquidity_source(
        cls, value: BtmmEvidenceSource
    ) -> BtmmEvidenceSource:
        if value not in CONTEXT_AND_LIQUIDITY_ALLOWED_SOURCES:
            raise ValueError(
                "context_input_source and liquidity_event_source must be one of"
                " EXPERT_LABELLED, HYBRID_REVIEWED, or RULE_BASED_REVIEWED; got"
                f" {value!r}."
            )
        return value

    @field_validator("volume_evidence_source")
    @classmethod
    def _validate_volume_source(cls, value: BtmmEvidenceSource) -> BtmmEvidenceSource:
        if value not in VOLUME_ALLOWED_SOURCES:
            raise ValueError(
                "volume_evidence_source must be one of EXPERT_LABELLED or"
                f" HYBRID_REVIEWED; got {value!r}."
            )
        return value
