from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
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


def _engulfing_candles(
    timeframe: Timeframe = Timeframe.M1,
) -> tuple[NormalizedCandle, NormalizedCandle]:
    engulfed = _candle(0, "100", "100", "99", "99", timeframe=timeframe)
    engulfing = _candle(1, "99", "101", "99", "101", timeframe=timeframe)
    return engulfed, engulfing


def _config(**overrides: object) -> ScannerConfiguration:
    fields: dict[str, object] = {
        "measurement_configuration": MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        "structure_configuration": StructureConfiguration(),
        "poi_configuration": PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        "btmm_configuration": BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
    }
    fields.update(overrides)
    return ScannerConfiguration(**fields)  # type: ignore[arg-type]


def _required_bundles(
    with_engulfing_on_m1: bool = False,
) -> tuple[ScannerTimeframeInput, ...]:
    m1_candles = (
        _engulfing_candles(Timeframe.M1)
        if with_engulfing_on_m1
        else (_flat_candle(0, Timeframe.M1),)
    )
    return (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=m1_candles),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5, candles=(_flat_candle(0, Timeframe.M5),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_flat_candle(0, Timeframe.M15),)
        ),
    )


def test_measurements_computed_before_structure_per_timeframe() -> None:
    config = _config()
    result = scan_market(_required_bundles(), (), config, _SequentialIdentityProvider())
    assert len(result.measurement_analyses) == len(result.structure_analyses)
    for measurement, structure in zip(
        result.measurement_analyses, result.structure_analyses, strict=True
    ):
        assert measurement.timeframe == structure.timeframe
        assert measurement.analyzed_candle_count == structure.analyzed_candle_count


def test_structure_computed_before_poi_analysis() -> None:
    config = _config()
    result = scan_market(_required_bundles(), (), config, _SequentialIdentityProvider())
    assert len(result.structure_analyses) == 3
    assert result.poi_analysis.analyzed_timeframes == result.processed_timeframes


def test_poi_analysis_computed_before_btmm_analysis() -> None:
    config = _config()
    result = scan_market(
        _required_bundles(with_engulfing_on_m1=True),
        (),
        config,
        _SequentialIdentityProvider(),
    )
    assert len(result.poi_analysis.poi_observations) > 0
    assert any(
        obs.poi_type == PoiType.BULLISH_ENGULFING
        for obs in result.poi_analysis.poi_observations
    )
    assert len(result.btmm_analysis.btmm_observations) > 0


def test_measurement_analysis_instance_reused_not_recomputed_for_poi_and_btmm() -> None:
    config = _config()
    result = scan_market(
        _required_bundles(with_engulfing_on_m1=True),
        (),
        config,
        _SequentialIdentityProvider(),
    )
    m1_measurement = next(
        m for m in result.measurement_analyses if m.timeframe == Timeframe.M1
    )
    assert m1_measurement.analyzed_candle_count == 2


def test_structure_analysis_exposed_but_not_passed_to_poi_or_btmm() -> None:
    config = _config()
    result = scan_market(_required_bundles(), (), config, _SequentialIdentityProvider())
    assert len(result.structure_analyses) > 0
    for setup in result.setup_summaries:
        assert not hasattr(setup, "structure_analysis")


def test_poi_timeframe_input_constructed_per_timeframe() -> None:
    config = _config()
    bundles = (
        *_required_bundles(),
        ScannerTimeframeInput(
            timeframe=Timeframe.H1, candles=(_flat_candle(0, Timeframe.H1),)
        ),
    )
    result = scan_market(bundles, (), config, _SequentialIdentityProvider())
    assert Timeframe.H1 in result.processed_timeframes
    assert Timeframe.H1 in result.poi_analysis.analyzed_timeframes
    assert any(
        obs.source_timeframe == Timeframe.H1
        for obs in result.poi_analysis.poi_observations
    )


def test_btmm_timeframe_input_constructed_per_timeframe() -> None:
    config = _config()
    bundles = (
        *_required_bundles(),
        ScannerTimeframeInput(
            timeframe=Timeframe.H1, candles=(_flat_candle(0, Timeframe.H1),)
        ),
    )
    result = scan_market(bundles, (), config, _SequentialIdentityProvider())
    assert set(result.btmm_analysis.analyzed_timeframes) == {
        Timeframe.M1,
        Timeframe.M5,
        Timeframe.M15,
    }
    assert Timeframe.H1 not in result.btmm_analysis.analyzed_timeframes


def test_reviewed_evidence_gated_by_availability_before_btmm_call() -> None:
    from btmm_ai_scanner.btmm.enums import (
        BtmmContextAlignmentStatus,
        BtmmEvidenceSource,
        BtmmLiquidityEvidenceStatus,
        BtmmSessionStatus,
        BtmmVolumePillarStatus,
    )
    from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence

    config = _config()
    bundles = _required_bundles(with_engulfing_on_m1=True)
    baseline = scan_market(bundles, (), config, _SequentialIdentityProvider())
    source_poi = next(
        obs
        for obs in baseline.poi_analysis.poi_observations
        if obs.poi_type == PoiType.BULLISH_ENGULFING
    )

    future_evidence = BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        source_poi_record_id=source_poi.record_id,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=baseline.availability_time_utc + timedelta(days=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )

    gated_result = scan_market(
        bundles, (future_evidence,), config, _SequentialIdentityProvider()
    )
    for state in gated_result.btmm_analysis.current_btmm_states:
        assert state.reviewed_evidence_availability_time_utc is None


def test_scan_market_never_reimplements_upstream_detection() -> None:
    config = _config()
    result = scan_market(
        _required_bundles(with_engulfing_on_m1=True),
        (),
        config,
        _SequentialIdentityProvider(),
    )
    engulfing_observations = [
        obs
        for obs in result.poi_analysis.poi_observations
        if obs.poi_type == PoiType.BULLISH_ENGULFING
    ]
    assert len(engulfing_observations) == 1
    assert engulfing_observations[0].zone_top == Decimal("100")
    assert engulfing_observations[0].zone_bottom == Decimal("99")


def test_mixed_symbol_input_raises_mixed_symbol_analysis_error() -> None:
    from btmm_ai_scanner.domain.analyzer import MixedSymbolAnalysisError

    config = _config()
    bundles = (
        ScannerTimeframeInput(
            timeframe=Timeframe.M1,
            candles=(_flat_candle(0, Timeframe.M1),),
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5,
            candles=(
                _candle(
                    0,
                    "100",
                    "100.5",
                    "99.5",
                    "100.2",
                    Timeframe.M5,
                    InternalSymbol.EURUSD,
                ),
            ),
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_flat_candle(0, Timeframe.M15),)
        ),
    )
    with pytest.raises(MixedSymbolAnalysisError):
        scan_market(bundles, (), config, _SequentialIdentityProvider())
