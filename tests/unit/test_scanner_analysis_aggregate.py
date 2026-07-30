from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
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
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiType
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis, ScannerSetupSummary
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


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


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    timeframe: Timeframe = Timeframe.M1,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(seconds=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm",
            "source_symbol": symbol.value,
            "source_timeframe": timeframe.value,
            "symbol": symbol,
            "timeframe": timeframe,
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


def _flat_candle(index: int, timeframe: Timeframe) -> NormalizedCandle:
    return _candle(index, "100", "100.5", "99.5", "100.2", timeframe=timeframe)


def _config() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
    )


def _bundles_with_engulfing_and_optional_h1() -> tuple[ScannerTimeframeInput, ...]:
    engulfed = _candle(0, "100", "100", "99", "99")
    engulfing = _candle(1, "99", "101", "99", "101")
    return (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=(engulfed, engulfing)),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5, candles=(_flat_candle(0, Timeframe.M5),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_flat_candle(0, Timeframe.M15),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.H1, candles=(_flat_candle(0, Timeframe.H1),)
        ),
    )


def _run() -> ScannerAnalysis:
    return scan_market(
        _bundles_with_engulfing_and_optional_h1(),
        (),
        _config(),
        _SequentialIdentityProvider(),
    )


def _fixture_summary(
    primary_state: BtmmLifecycleStatus, index: int
) -> ScannerSetupSummary:
    return ScannerSetupSummary(
        source_btmm_observation_record_id=UUID(f"0193f450-2222-7000-8000-{index:012x}"),
        source_poi_record_id=UUID(f"0193f450-3333-7000-8000-{index:012x}"),
        symbol=InternalSymbol.XAUUSD,
        btmm_direction=BtmmDirection.BULLISH_BTMM,
        source_poi_type=PoiType.BULLISH_ENGULFING,
        timeframe=Timeframe.M1,
        poi_lifecycle_status=PoiLifecycleStatus.NO_BREACH,
        btmm_primary_state=primary_state,
        interaction_class=BtmmInteractionClass.EDGE_TOUCH,
        reaction_classification=BtmmReactionClassification.STANDARD_REACTION,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        availability_time_utc=_BASE_TIME,
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )


def test_scanner_analysis_reports_correct_symbol() -> None:
    result = _run()
    assert result.symbol == InternalSymbol.XAUUSD


def test_scanner_analysis_reports_processed_timeframes() -> None:
    result = _run()
    assert Timeframe.H1 in result.processed_timeframes
    assert set(result.processed_timeframes) == {
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
        Timeframe.H1,
    }


def test_scanner_analysis_exposes_upstream_measurement_and_structure_analyses() -> None:
    result = _run()
    assert len(result.measurement_analyses) == 4
    assert len(result.structure_analyses) == 4
    h1_poi_observations = [
        obs
        for obs in result.poi_analysis.poi_observations
        if obs.source_timeframe == Timeframe.H1
    ]
    assert len(h1_poi_observations) > 0


def test_scanner_setup_summaries_include_active_pois() -> None:
    result = _run()
    assert any(
        summary.poi_lifecycle_status == PoiLifecycleStatus.NO_BREACH
        for summary in result.setup_summaries
    )


def test_scanner_setup_summaries_include_active_btmm_setups() -> None:
    result = _run()
    assert any(
        summary.btmm_primary_state
        in (BtmmLifecycleStatus.BTMM_CANDIDATE, BtmmLifecycleStatus.BTMM_FORMING)
        for summary in result.setup_summaries
    )


def test_scanner_setup_summaries_include_confirmed_btmm_setups() -> None:
    summaries = (_fixture_summary(BtmmLifecycleStatus.BTMM_CONFIRMED, 1),)
    confirmed = [
        s
        for s in summaries
        if s.btmm_primary_state == BtmmLifecycleStatus.BTMM_CONFIRMED
    ]
    assert len(confirmed) == 1


def test_scanner_setup_summaries_include_blocked_btmm_setups() -> None:
    summaries = (_fixture_summary(BtmmLifecycleStatus.BTMM_BLOCKED, 2),)
    blocked = [
        s for s in summaries if s.btmm_primary_state == BtmmLifecycleStatus.BTMM_BLOCKED
    ]
    assert len(blocked) == 1


def test_scanner_setup_summaries_include_cancelled_btmm_setups() -> None:
    summaries = (_fixture_summary(BtmmLifecycleStatus.BTMM_CANCELLED, 3),)
    cancelled = [
        s
        for s in summaries
        if s.btmm_primary_state == BtmmLifecycleStatus.BTMM_CANCELLED
    ]
    assert len(cancelled) == 1


def test_scanner_analysis_availability_equals_max_of_upstream_availability() -> None:
    result = _run()
    max_candle_availability = max(
        candle.availability_time_utc
        for bundle in _bundles_with_engulfing_and_optional_h1()
        for candle in bundle.candles
    )
    assert result.availability_time_utc == max_candle_availability


def test_scanner_analysis_tuples_use_deterministic_ordering() -> None:
    result_a = _run()
    result_b = _run()
    assert result_a.processed_timeframes == result_b.processed_timeframes
    assert [o.record_id for o in result_a.poi_analysis.poi_observations] == [
        o.record_id for o in result_b.poi_analysis.poi_observations
    ]
