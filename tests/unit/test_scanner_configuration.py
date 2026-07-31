from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analyzer import InvalidScannerCandleInputError, scan_market
from btmm_ai_scanner.scanner.configuration import (
    InvalidScannerConfigurationError,
    ScannerConfiguration,
    validate_configuration,
)
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


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    timeframe: Timeframe = Timeframe.M1,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(seconds=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
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
            "open": Decimal("100"),
            "high": Decimal("100.5"),
            "low": Decimal("99.5"),
            "close": Decimal("100.2"),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV_ID,
        }
    )


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


def test_default_scanner_configuration_composes_upstream_configurations() -> None:
    config = _config()
    assert isinstance(config.measurement_configuration, MarketMeasurementConfiguration)
    assert isinstance(config.structure_configuration, StructureConfiguration)
    assert isinstance(config.poi_configuration, PoiConfiguration)
    assert isinstance(config.btmm_configuration, BtmmConfiguration)
    assert config.rule_version == SemVer.parse("0.1.0")
    assert config.contract_version == SemVer.parse("0.1.0")
    assert config.schema_version == SemVer.parse("0.1.0")

    # 1B-L-SCANNER-A1: the composed upstream configurations must share one
    # canonical minimum_price_tick; structure_configuration is excluded since
    # it owns no such field.
    validate_configuration(config)
    assert (
        config.measurement_configuration.minimum_price_tick
        == config.poi_configuration.minimum_price_tick
        == config.btmm_configuration.minimum_price_tick
        == Decimal("0.01")
    )

    mismatched_config = _config(
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.02"))
    )
    with pytest.raises(InvalidScannerConfigurationError):
        validate_configuration(mismatched_config)


def test_required_and_optional_timeframes_must_be_disjoint() -> None:
    config = _config(
        required_timeframes=frozenset({Timeframe.M1, Timeframe.M5, Timeframe.M15}),
        optional_timeframes=frozenset({Timeframe.M15, Timeframe.H1}),
    )
    with pytest.raises(InvalidScannerConfigurationError):
        validate_configuration(config)


def test_missing_required_timeframe_raises_error() -> None:
    from btmm_ai_scanner.scanner.analyzer import MissingRequiredTimeframeError

    config = _config()
    bundle_m1 = ScannerTimeframeInput(timeframe=Timeframe.M1, candles=(_candle(0),))
    bundle_m5 = ScannerTimeframeInput(timeframe=Timeframe.M5, candles=())
    with pytest.raises(MissingRequiredTimeframeError):
        scan_market((bundle_m1, bundle_m5), (), config, _SequentialIdentityProvider())

    # Valid-empty scan: when required_timeframes is itself empty, an empty
    # timeframe_inputs tuple is accepted and returns an empty ScannerAnalysis
    # carrying the epoch empty-result sentinel, never confused with a real
    # replay availability (which is always strictly after 1970-01-01).
    empty_config = _config(
        required_timeframes=frozenset(), optional_timeframes=frozenset()
    )
    empty_result = scan_market((), (), empty_config, _SequentialIdentityProvider())
    assert empty_result.symbol is None
    assert empty_result.processed_timeframes == ()
    assert empty_result.availability_time_utc == datetime(1970, 1, 1, tzinfo=UTC)


def test_unsupported_timeframe_rejected() -> None:
    config = _config(
        required_timeframes=frozenset({Timeframe.M1, Timeframe.M5, Timeframe.M15}),
        optional_timeframes=frozenset(),
    )
    bundle_m1 = ScannerTimeframeInput(timeframe=Timeframe.M1, candles=())
    bundle_m5 = ScannerTimeframeInput(timeframe=Timeframe.M5, candles=())
    bundle_m15 = ScannerTimeframeInput(timeframe=Timeframe.M15, candles=())
    bundle_h1 = ScannerTimeframeInput(
        timeframe=Timeframe.H1, candles=(_candle(0, timeframe=Timeframe.H1),)
    )
    with pytest.raises(InvalidScannerCandleInputError):
        scan_market(
            (bundle_m1, bundle_m5, bundle_m15, bundle_h1),
            (),
            config,
            _SequentialIdentityProvider(),
        )


def test_enabled_symbols_default_to_all_three_internal_symbols() -> None:
    config = _config()
    assert config.enabled_symbols == frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )
    assert config.required_timeframes == frozenset(
        {Timeframe.M1, Timeframe.M5, Timeframe.M15}
    )
    assert config.optional_timeframes == frozenset(
        {Timeframe.H1, Timeframe.H3, Timeframe.H4, Timeframe.D1, Timeframe.W1}
    )


def test_scanner_configuration_is_immutable() -> None:
    config = _config()
    with pytest.raises(ValidationError):
        config.enabled_symbols = frozenset({InternalSymbol.XAUUSD})
