from datetime import UTC, datetime
from uuid import UUID

from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmLiquidityEvidenceStatus,
    BtmmLiquidityLocation,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.liquidity import find_automatic_liquidity_evidence
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition

_FINGERPRINT = "a" * 64
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000001")
_CANDLE_ID = UUID("0193f450-bbbb-7000-8000-000000000001")


def _poi_transition(
    transition_type: PoiLifecycleTransitionType, poi_record_id: UUID = _POI_ID
) -> PoiLifecycleTransition:
    return PoiLifecycleTransition(
        record_id=UUID("0193f450-cccc-7000-8000-000000000001"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=poi_record_id,
        transition_type=transition_type,
        triggering_candle_record_id=_CANDLE_ID,
        event_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _evidence(
    liquidity_status: BtmmLiquidityEvidenceStatus,
    availability: datetime = _BASE_TIME,
) -> BtmmReviewedEvidence:
    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=_POI_ID,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=liquidity_status,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def test_false_invalidation_confirmed_produces_liquidity_after_poi_rule_based() -> None:
    transition = _poi_transition(
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED
    )
    result = find_automatic_liquidity_evidence(_POI_ID, (transition,))
    assert result is not None
    assert result.liquidity_location == BtmmLiquidityLocation.LIQUIDITY_AFTER_POI
    assert result.liquidity_evidence_source == BtmmEvidenceSource.RULE_BASED


def test_liquidity_before_within_and_automatic_rule_based_never_treated_as_reviewed() -> (
    None
):
    transition = _poi_transition(
        PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED
    )
    result = find_automatic_liquidity_evidence(_POI_ID, (transition,))
    assert result is not None
    assert result.liquidity_evidence_source != BtmmEvidenceSource.RULE_BASED_REVIEWED
    assert result.liquidity_evidence_source != BtmmEvidenceSource.EXPERT_LABELLED

    no_evidence = find_automatic_liquidity_evidence(
        _POI_ID, (_poi_transition(PoiLifecycleTransitionType.RECLAIM_CONFIRMED),)
    )
    assert no_evidence is None


def test_equal_highs_and_lows_not_treated_as_automatic_evidence() -> None:
    unrelated = _poi_transition(PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE)
    result = find_automatic_liquidity_evidence(_POI_ID, (unrelated,))
    assert result is None


def test_liquidity_gate_pass_requires_approved_supporting_evidence() -> None:
    present = _evidence(BtmmLiquidityEvidenceStatus.PRESENT)
    assert present.liquidity_evidence_status == BtmmLiquidityEvidenceStatus.PRESENT

    pending = _evidence(BtmmLiquidityEvidenceStatus.PENDING)
    assert pending.liquidity_evidence_status == BtmmLiquidityEvidenceStatus.PENDING


def test_missing_liquidity_evidence_remains_unresolved() -> None:
    pending_evidence = _evidence(BtmmLiquidityEvidenceStatus.PENDING)
    assert (
        pending_evidence.liquidity_evidence_status
        != BtmmLiquidityEvidenceStatus.PRESENT
    )


def test_no_liquidity_evidence_cancellation_at_window_close() -> None:
    assert find_automatic_liquidity_evidence(_POI_ID, ()) is None


def test_reviewed_liquidity_evidence_status_uses_exact_vocabulary() -> None:
    members = set(BtmmLiquidityEvidenceStatus)
    assert members == {
        BtmmLiquidityEvidenceStatus.PENDING,
        BtmmLiquidityEvidenceStatus.PRESENT,
    }
    assert len(members) == 2


def test_liquidity_evidence_presence_does_not_automatically_pass_gate() -> None:
    evidence = _evidence(BtmmLiquidityEvidenceStatus.PRESENT)
    assert evidence.volume_pillar_status == BtmmVolumePillarStatus.SUPPORTS
    assert evidence.liquidity_evidence_status == BtmmLiquidityEvidenceStatus.PRESENT
    assert BtmmReviewedEvidence.model_fields["liquidity_evidence_status"] is not None
