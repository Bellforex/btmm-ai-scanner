from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.analyzer import (
    BtmmTimeframeInput,
    DuplicateBtmmTimeframeInputError,
    InputPrefixMismatchError,
    MissingSourcePoiRecordError,
    UnsortedBtmmTimeframeInputError,
    analyze_btmm,
)
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
from btmm_ai_scanner.domain import MarketMeasurementAnalysis, MixedSymbolAnalysisError
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.analyzer import PoiAnalysis
from btmm_ai_scanner.poi.enums import PoiDirection, PoiFamily, PoiType
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
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-m5",
            "source_symbol": symbol.value,
            "source_timeframe": Timeframe.M5.value,
            "symbol": symbol,
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


def _measurement_analysis(
    count: int, symbol: InternalSymbol = InternalSymbol.XAUUSD
) -> MarketMeasurementAnalysis:
    return MarketMeasurementAnalysis(
        symbol=symbol,
        timeframe=Timeframe.M5,
        analyzed_candle_count=count,
        confirmed_swings=(),
        displacement_observations=(),
        equal_level_clusters=(),
        support_resistance_zones=(),
        trendlines=(),
    )


def _source_poi(poi_type: PoiType = PoiType.SUPPORT_ZONE) -> PoiObservation:
    return PoiObservation(
        record_id=_POI_ID,
        content_fingerprint=_FINGERPRINT,
        symbol=InternalSymbol.XAUUSD,
        source_timeframe=Timeframe.M5,
        effective_timeframe=Timeframe.M5,
        family=PoiFamily.STRUCTURAL,
        poi_type=poi_type,
        direction=PoiDirection.BULLISH,
        zone_top=Decimal("101"),
        zone_bottom=Decimal("100"),
        representative_price=None,
        strength_tier=None,
        source_candle_record_ids=(),
        source_measurement_record_ids=(),
        merged_source_poi_record_ids=(),
        candidate_event_time_utc=_BASE_TIME,
        confirmation_time_utc=_BASE_TIME,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROV_ID,
    )


def _empty_poi_analysis() -> PoiAnalysis:
    return PoiAnalysis(
        symbol=None,
        analyzed_timeframes=(),
        analyzed_candle_count_by_timeframe=(),
        poi_observations=(),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )


def _config() -> BtmmConfiguration:
    return BtmmConfiguration(minimum_price_tick=Decimal("0.01"))


def test_empty_aggregate_for_empty_input() -> None:
    result = analyze_btmm(
        (), _empty_poi_analysis(), (), _config(), _SequentialIdentityProvider()
    )
    assert result.symbol is None
    assert result.btmm_observations == ()
    assert result.btmm_lifecycle_transitions == ()
    assert result.current_btmm_states == ()


def test_rejects_mixed_symbol_across_all_inputs_including_reviewed_evidence() -> None:
    candles = (
        _candle(0, "105", "105.2", "104.8", "105", symbol=InternalSymbol.EURUSD),
    )
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(1, InternalSymbol.EURUSD),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    with pytest.raises(MixedSymbolAnalysisError):
        analyze_btmm(
            (bundle,), poi_analysis, (), _config(), _SequentialIdentityProvider()
        )


def test_rejects_duplicate_or_unsorted_timeframe_input() -> None:
    candles_m5 = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle_m5_a = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles_m5,
        measurement_analysis=_measurement_analysis(1),
    )
    bundle_m5_b = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles_m5,
        measurement_analysis=_measurement_analysis(1),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    with pytest.raises(DuplicateBtmmTimeframeInputError):
        analyze_btmm(
            (bundle_m5_a, bundle_m5_b),
            poi_analysis,
            (),
            _config(),
            _SequentialIdentityProvider(),
        )

    bundle_m15 = BtmmTimeframeInput(
        timeframe=Timeframe.M15,
        candles=(),
        measurement_analysis=_measurement_analysis(0),
    )
    with pytest.raises(UnsortedBtmmTimeframeInputError):
        analyze_btmm(
            (bundle_m15, bundle_m5_a),
            poi_analysis,
            (),
            _config(),
            _SequentialIdentityProvider(),
        )


def test_rejects_unsupported_timeframe() -> None:
    bundle_h1 = BtmmTimeframeInput(
        timeframe=Timeframe.H1,
        candles=(),
        measurement_analysis=_measurement_analysis(0),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(),
        analyzed_candle_count_by_timeframe=(),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    with pytest.raises(UnsortedBtmmTimeframeInputError):
        analyze_btmm(
            (bundle_h1,), poi_analysis, (), _config(), _SequentialIdentityProvider()
        )


def test_rejects_measurement_prefix_mismatch() -> None:
    candles = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(2),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    with pytest.raises(InputPrefixMismatchError):
        analyze_btmm(
            (bundle,), poi_analysis, (), _config(), _SequentialIdentityProvider()
        )


def test_rejects_missing_source_poi_record() -> None:
    candles = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    evidence = BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M5,
        source_poi_record_id=UUID("0193f450-9999-7000-8000-000000000099"),
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=_BASE_TIME,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    with pytest.raises(MissingSourcePoiRecordError):
        analyze_btmm(
            (bundle,),
            poi_analysis,
            (evidence,),
            _config(),
            _SequentialIdentityProvider(),
        )


def test_reviewed_evidence_rejects_unknown_or_duplicate_source_poi() -> None:
    candles = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )

    def _evidence(availability: datetime) -> BtmmReviewedEvidence:
        return BtmmReviewedEvidence(
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
            availability_time_utc=availability,
            rule_version=SemVer.parse("0.1.0"),
            contract_version=SemVer.parse("0.1.0"),
            schema_version=SemVer.parse("0.1.0"),
        )

    with pytest.raises(InputPrefixMismatchError):
        analyze_btmm(
            (bundle,),
            poi_analysis,
            (_evidence(_BASE_TIME), _evidence(_BASE_TIME + timedelta(minutes=1))),
            _config(),
            _SequentialIdentityProvider(),
        )


def test_ineligible_poi_type_never_creates_a_setup() -> None:
    candles = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(poi_type=PoiType.EQUAL_HIGHS_LIQUIDITY),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    result = analyze_btmm(
        (bundle,), poi_analysis, (), _config(), _SequentialIdentityProvider()
    )
    assert result.btmm_observations == ()


def test_deterministic_across_repeated_calls() -> None:
    candles = (_candle(0, "105", "105.2", "104.8", "105"),)
    bundle = BtmmTimeframeInput(
        timeframe=Timeframe.M5,
        candles=candles,
        measurement_analysis=_measurement_analysis(1),
    )
    poi_analysis = PoiAnalysis(
        symbol=InternalSymbol.XAUUSD,
        analyzed_timeframes=(Timeframe.M5,),
        analyzed_candle_count_by_timeframe=(1,),
        poi_observations=(_source_poi(),),
        poi_lifecycle_transitions=(),
        poi_overlap_relationships=(),
        current_poi_states=(),
    )
    result_a = analyze_btmm(
        (bundle,), poi_analysis, (), _config(), _SequentialIdentityProvider()
    )
    result_b = analyze_btmm(
        (bundle,), poi_analysis, (), _config(), _SequentialIdentityProvider()
    )
    assert (
        result_a.btmm_observations[0].record_id
        == result_b.btmm_observations[0].record_id
    )
    assert (
        result_a.btmm_observations[0].content_fingerprint
        == result_b.btmm_observations[0].content_fingerprint
    )
