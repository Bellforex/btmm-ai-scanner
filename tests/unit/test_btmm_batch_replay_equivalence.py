import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm import analyzer as btmm_analyzer
from btmm_ai_scanner.btmm.analyzer import BtmmAnalysis, BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
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
from btmm_ai_scanner.domain import analyzer as domain_analyzer
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi import analyzer as poi_analyzer_module
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.structure import analyzer as structure_analyzer

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_POI_ID = UUID("0193f450-aaaa-7000-8000-000000000001")


class _HashIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        payload = output_type.value + "|" + "|".join(semantic_key)
        digest = hashlib.sha256(payload.encode("utf-8")).digest()[:16]
        as_int = int.from_bytes(digest, "big")
        as_int &= ~(0xF << 76)
        as_int |= 7 << 76
        as_int &= ~(0x3 << 62)
        as_int |= 0x2 << 62
        return UUID(int=as_int)


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


def _full_candles() -> tuple[NormalizedCandle, ...]:
    candles = [_candle(i, "105", "105.2", "104.8", "105") for i in range(14)]
    candles.append(_candle(14, "105", "105.1", "100.5", "100.8"))
    candles.append(_candle(15, "100.8", "102.2", "100.7", "102.0"))
    candles.append(_candle(16, "102.0", "103.5", "101.9", "103.4"))
    candles.append(_candle(17, "103.4", "105.0", "103.3", "104.9"))
    candles.append(_candle(18, "104.9", "106.5", "104.8", "106.4"))
    candles.append(_candle(19, "106.4", "108.0", "106.3", "107.9"))
    return tuple(candles)


def _source_poi() -> PoiObservation:
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


def _poi_analysis() -> PoiAnalysis:
    return PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(0,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )


def _measurement_analysis(count: int) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        analyzed_candle_count=count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def _config() -> BtmmConfiguration:
    return BtmmConfiguration(minimum_price_tick=Decimal("0.01"))


def _run(
    candles: tuple[NormalizedCandle, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...] = (),
) -> BtmmAnalysis:
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(len(candles)),
    )
    return analyze_btmm(
        (bundle,),
        _poi_analysis(),
        reviewed_evidence,
        _config(),
        _HashIdentityProvider(),
    )


def test_batch_and_replay_produce_identical_observations_and_transitions() -> None:
    full = _full_candles()
    batch_result = _run(full)

    prefix_result = _run(full[:17])
    final_result = _run(full)

    assert (
        final_result.btmm_observations[0].record_id
        == prefix_result.btmm_observations[0].record_id
    )
    assert len(final_result.btmm_lifecycle_transitions) >= len(
        prefix_result.btmm_lifecycle_transitions
    )
    assert batch_result.btmm_observations == final_result.btmm_observations


def test_stable_identity_across_growing_prefixes() -> None:
    full = _full_candles()
    result_short = _run(full[:15])
    result_long = _run(full)
    assert (
        result_short.btmm_observations[0].record_id
        == result_long.btmm_observations[0].record_id
    )
    assert (
        result_short.current_btmm_states[0].record_id
        == result_long.current_btmm_states[0].record_id
    )


def test_current_state_fingerprint_changes_only_with_content() -> None:
    full = _full_candles()
    result_a = _run(full)
    result_b = _run(full)
    assert (
        result_a.current_btmm_states[0].content_fingerprint
        == result_b.current_btmm_states[0].content_fingerprint
    )

    result_incomplete = _run(full[:15])
    assert (
        result_incomplete.current_btmm_states[0].content_fingerprint
        != result_a.current_btmm_states[0].content_fingerprint
    )


def test_reviewed_evidence_is_availability_gated_and_never_leaks_backward() -> None:
    full = _full_candles()
    late_evidence = BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=_POI_ID,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=full[19].availability_time_utc + timedelta(hours=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )
    result = _run(full, reviewed_evidence=(late_evidence,))
    state = result.current_btmm_states[0]
    assert (
        state.reviewed_evidence_availability_time_utc
        == late_evidence.availability_time_utc
    )
    assert state.availability_time_utc >= late_evidence.availability_time_utc
    blocked_transitions = [
        t
        for t in result.btmm_lifecycle_transitions
        if t.transition_type.value == "BLOCKED"
    ]
    assert len(blocked_transitions) == 1
    assert (
        blocked_transitions[0].availability_time_utc
        < late_evidence.availability_time_utc
    )


def test_four_way_serializer_equivalence() -> None:
    sample_fields: dict[str, object] = {
        "a_decimal": Decimal("1.230"),
        "a_zero_decimal": Decimal("0"),
        "an_enum": PoiType.SUPPORT_ZONE,
        "a_uuid": _POI_ID,
        "a_datetime": _BASE_TIME,
        "a_semver": SemVer.parse("1.2.3"),
        "a_tuple": (Decimal("1"), "text", None),
        "a_none": None,
        "a_bool": True,
        "an_int": 42,
        "a_string": "hello",
    }

    domain_result = domain_analyzer._compute_content_fingerprint(dict(sample_fields))
    structure_result = structure_analyzer._compute_content_fingerprint(
        dict(sample_fields)
    )
    poi_result = poi_analyzer_module._compute_content_fingerprint(dict(sample_fields))
    btmm_result = btmm_analyzer._compute_content_fingerprint(dict(sample_fields))

    assert domain_result == structure_result == poi_result == btmm_result

    nested_fields = {"nested": (Decimal("2.5"), PoiType.BUY_ORDER_BLOCK)}
    assert domain_analyzer._compute_content_fingerprint(
        dict(nested_fields)
    ) == btmm_analyzer._compute_content_fingerprint(dict(nested_fields))
