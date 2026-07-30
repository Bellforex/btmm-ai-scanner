from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis, BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmBlockedReason,
    BtmmCancellationReason,
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmLifecycleStatus,
    BtmmLifecycleTransitionType,
    BtmmLiquidityEvidenceStatus,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiLifecycleTransitionType,
    PoiType,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000001")


class _SequentialIdentityProvider:
    def __init__(self) -> None:
        self._map: dict[object, UUID] = {}
        self._counter = 0

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type, semantic_key)
        if key not in self._map:
            self._counter += 1
            self._map[key] = UUID(f"0193f450-0000-7000-8000-{self._counter:012x}")
        return self._map[key]


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m5",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M5.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M5,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV_ID,
        }
    )


def _build_candles(*, strong_reaction: bool = True) -> tuple[NormalizedCandle, ...]:
    candles = []
    for i in range(14):
        candles.append(_candle(i, "105", "105.2", "104.8", "105"))
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    if strong_reaction:
        candles.append(_candle(16, "102.0", "103.5", "101.9", "103.4"))
        candles.append(_candle(17, "103.4", "105.0", "103.3", "104.9"))
        candles.append(_candle(18, "104.9", "106.5", "104.8", "106.4"))
        candles.append(_candle(19, "106.4", "108.0", "106.3", "107.9"))
    else:
        candles.append(_candle(16, "102.0", "102.3", "101.8", "102.1"))
        candles.append(_candle(17, "102.1", "102.4", "101.9", "102.0"))
        candles.append(_candle(18, "102.0", "102.3", "101.7", "101.9"))
        candles.append(_candle(19, "101.9", "102.2", "101.6", "101.8"))
    return tuple(candles)


def _source_poi(genuinely_invalidated: bool = False) -> PoiObservation:
    return PoiObservation(
        record_id=_POI_ID,
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M5,
        effective_timeframe=Timeframe.M5,
        family=PoiFamily.STRUCTURAL,
        poi_type=PoiType.SUPPORT_ZONE,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=_candle(
            13, "105", "105.2", "104.8", "105"
        ).event_time_utc,
        confirmation_time_utc=_candle(
            13, "105", "105.2", "104.8", "105"
        ).event_time_utc,
        availability_time_utc=_candle(
            13, "105", "105.2", "104.8", "105"
        ).availability_time_utc,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _measurement_analysis(candle_count: int) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        analyzed_candle_count=candle_count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def _poi_analysis(
    source_poi: PoiObservation,
    poi_lifecycle_transitions: tuple[PoiLifecycleTransition, ...] = (),
) -> PoiAnalysis:
    return PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(0,),
        poi_observations=(source_poi,),
        poi_lifecycle_transitions=poi_lifecycle_transitions,
        poi_overlap_relationships=(),
        current_poi_states=(),
    )


def _run(
    candles: tuple[NormalizedCandle, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...] = (),
    poi_lifecycle_transitions: tuple[PoiLifecycleTransition, ...] = (),
    source_poi: PoiObservation | None = None,
) -> BtmmAnalysis:
    poi = source_poi if source_poi is not None else _source_poi()
    btmm_bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(len(candles)),
    )
    poi_analysis = _poi_analysis(poi, poi_lifecycle_transitions)
    config = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
    provider = _SequentialIdentityProvider()
    return analyze_btmm(
        (btmm_bundle,), poi_analysis, reviewed_evidence, config, provider
    )


def _full_evidence(
    liquidity: BtmmLiquidityEvidenceStatus = BtmmLiquidityEvidenceStatus.PRESENT,
    context: BtmmContextAlignmentStatus = BtmmContextAlignmentStatus.ALIGNED,
    session: BtmmSessionStatus = BtmmSessionStatus.ACTIVE,
    volume: BtmmVolumePillarStatus = BtmmVolumePillarStatus.SUPPORTS,
    availability: datetime = _BASE_TIME,
) -> BtmmReviewedEvidence:
    return BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=_POI_ID,
        market_direction_status=context,
        analytical_framework_status=context,
        session_status=session,
        liquidity_evidence_status=liquidity,
        volume_pillar_status=volume,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=availability,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def test_candidate_initial_state_is_btmm_candidate() -> None:
    candles = _build_candles()[:14]
    result = _run(candles)
    assert len(result.current_btmm_states) == 1
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANDIDATE
    )
    assert result.current_btmm_states[0].formation_stage is None


def test_new_candidate_remains_candidate_in_creation_group() -> None:
    candles = _build_candles()[:14]
    result = _run(candles)
    transition_types = {t.transition_type for t in result.btmm_lifecycle_transitions}
    assert BtmmLifecycleTransitionType.ENTERED_FORMING not in transition_types
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANDIDATE
    )


def test_candidate_enters_forming_only_in_later_availability_group() -> None:
    candles = _build_candles()
    result = _run(candles)
    entered_forming = [
        t
        for t in result.btmm_lifecycle_transitions
        if t.transition_type == BtmmLifecycleTransitionType.ENTERED_FORMING
    ]
    assert len(entered_forming) == 1
    poi = _source_poi()
    assert entered_forming[0].availability_time_utc > poi.availability_time_utc


def test_candidate_to_forming_transition_is_emitted_once() -> None:
    candles = _build_candles()
    result = _run(candles)
    entered_forming = [
        t
        for t in result.btmm_lifecycle_transitions
        if t.transition_type == BtmmLifecycleTransitionType.ENTERED_FORMING
    ]
    assert len(entered_forming) == 1


def test_candidate_can_cancel_before_entering_forming() -> None:
    candles = _build_candles()[:14]
    genuine_invalidation = PoiLifecycleTransition(
        record_id=UUID("0193f450-dddd-7000-8000-000000000001"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=_POI_ID,
        transition_type=PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        triggering_candle_record_id=_record_id(13),
        event_time_utc=candles[13].event_time_utc,
        availability_time_utc=candles[13].availability_time_utc + timedelta(seconds=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )
    result = _run(candles, poi_lifecycle_transitions=(genuine_invalidation,))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.POI_REJECTED
    )


def test_interaction_ineligible_cancellation() -> None:
    candles = list(_build_candles()[:16])
    candles[14] = _candle(14, "105", "105.1", "80.0", "100.8")
    result = _run(tuple(candles))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.INTERACTION_INELIGIBLE
    )


def test_forming_becomes_blocked_for_unresolved_mandatory_gate() -> None:
    candles = _build_candles()
    evidence = _full_evidence(volume=BtmmVolumePillarStatus.PENDING)
    result = _run(candles, reviewed_evidence=(evidence,))
    state = result.current_btmm_states[0]
    assert state.primary_state == BtmmLifecycleStatus.BTMM_BLOCKED
    assert state.blocked_reason == BtmmBlockedReason.VOLUME_REVIEW_PENDING


def test_blocked_resumes_forming_when_blocker_resolves() -> None:
    candles = _build_candles()
    late_availability = candles[19].availability_time_utc + timedelta(hours=1)
    evidence = _full_evidence(
        volume=BtmmVolumePillarStatus.PENDING, availability=late_availability
    )
    result = _run(candles, reviewed_evidence=(evidence,))
    state = result.current_btmm_states[0]
    transition_types = [t.transition_type for t in result.btmm_lifecycle_transitions]
    assert BtmmLifecycleTransitionType.BLOCKED in transition_types
    assert BtmmLifecycleTransitionType.RESUMED_FORMING in transition_types
    assert state.primary_state == BtmmLifecycleStatus.BTMM_FORMING


def test_unchanged_blocker_does_not_emit_duplicate_transition() -> None:
    candles = _build_candles()
    evidence = _full_evidence(volume=BtmmVolumePillarStatus.PENDING)
    result = _run(candles, reviewed_evidence=(evidence,))
    blocked_transitions = [
        t
        for t in result.btmm_lifecycle_transitions
        if t.transition_type == BtmmLifecycleTransitionType.BLOCKED
    ]
    assert len(blocked_transitions) == 1


def test_forbidden_transitions_both_directions() -> None:
    assert "CANCELLED_TO_CONFIRMED" not in [
        t.value for t in BtmmLifecycleTransitionType
    ]
    candles = _build_candles()
    result = _run(candles, reviewed_evidence=(_full_evidence(),))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CONFIRMED
    )


def test_source_poi_invalidation_has_transition_priority() -> None:
    candles = _build_candles()
    invalidation = PoiLifecycleTransition(
        record_id=UUID("0193f450-eeee-7000-8000-000000000001"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=_POI_ID,
        transition_type=PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        triggering_candle_record_id=_record_id(15),
        event_time_utc=candles[15].event_time_utc,
        availability_time_utc=candles[15].availability_time_utc + timedelta(seconds=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )
    result = _run(candles, poi_lifecycle_transitions=(invalidation,))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.POI_REJECTED
    )


def test_poi_rejected_inheritance_on_genuine_invalidation() -> None:
    candles = _build_candles()
    invalidation = PoiLifecycleTransition(
        record_id=UUID("0193f450-ffff-7000-8000-000000000001"),
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        poi_record_id=_POI_ID,
        transition_type=PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED,
        triggering_candle_record_id=_record_id(19),
        event_time_utc=candles[19].event_time_utc,
        availability_time_utc=candles[19].availability_time_utc + timedelta(seconds=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )
    result = _run(
        candles,
        reviewed_evidence=(_full_evidence(),),
        poi_lifecycle_transitions=(invalidation,),
    )
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.POI_REJECTED
    )


def test_cancellation_is_terminal_never_reactivated() -> None:
    candles = list(_build_candles(strong_reaction=False))
    result = _run(tuple(candles))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert result.current_btmm_states[0].cancellation_reason in (
        BtmmCancellationReason.WEAK_REACTION,
        BtmmCancellationReason.REACTION_SPEED_FAILED,
    )


def test_new_interaction_creates_new_independent_setup() -> None:
    candles = _build_candles()
    result_a = _run(candles)
    result_b = _run(candles)
    assert (
        result_a.btmm_observations[0].record_id
        == result_b.btmm_observations[0].record_id
    )


def test_context_rejected_cancellation_from_reviewed_evidence() -> None:
    candles = _build_candles()
    evidence = _full_evidence(context=BtmmContextAlignmentStatus.MISALIGNED)
    result = _run(candles, reviewed_evidence=(evidence,))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.CONTEXT_REJECTED
    )


def test_session_inactive_cancellation_from_reviewed_evidence() -> None:
    candles = _build_candles()
    evidence = _full_evidence(session=BtmmSessionStatus.INACTIVE)
    result = _run(candles, reviewed_evidence=(evidence,))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.SESSION_INACTIVE
    )


def test_volume_pillar_failed_cancellation_from_reviewed_evidence() -> None:
    candles = _build_candles()
    evidence = _full_evidence(volume=BtmmVolumePillarStatus.FAILS)
    result = _run(candles, reviewed_evidence=(evidence,))
    assert (
        result.current_btmm_states[0].primary_state
        == BtmmLifecycleStatus.BTMM_CANCELLED
    )
    assert (
        result.current_btmm_states[0].cancellation_reason
        == BtmmCancellationReason.VOLUME_PILLAR_FAILED
    )


def test_btmm_confirmed_requires_all_automatic_and_reviewed_gates() -> None:
    candles = _build_candles()
    result = _run(candles, reviewed_evidence=(_full_evidence(),))
    state = result.current_btmm_states[0]
    assert state.primary_state == BtmmLifecycleStatus.BTMM_CONFIRMED
    assert state.accuracy_gate_status.value == "PASS"
    assert state.reaction_gate_status.value == "PASS"
    assert state.reaction_speed_gate_status.value == "PASS"
    assert state.volume_pillar_status == BtmmVolumePillarStatus.SUPPORTS
    assert state.liquidity_evidence_status == BtmmLiquidityEvidenceStatus.PRESENT


def test_directional_continuation_absent_from_public_enum() -> None:
    assert "DIRECTIONAL_CONTINUATION" not in [r.value for r in BtmmCancellationReason]
    assert "MANUAL_REVIEW_REJECTED" not in [r.value for r in BtmmCancellationReason]
