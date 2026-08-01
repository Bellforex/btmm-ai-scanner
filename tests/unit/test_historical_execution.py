import socket
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest import execution as execution_module
from btmm_ai_scanner.historical_backtest.data_quality import HistoricalDataQualityReport
from btmm_ai_scanner.historical_backtest.enums import (
    BacktestQualityGateStatus,
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.execution import execute_scanner_backtest
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
    _uuid_from_canonical_bytes,
)
from btmm_ai_scanner.historical_backtest.loader import LoadedHistoricalDataset
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.replay import ScannerReplayResult
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_TICK = Decimal("0.01")


def _uid(seed: str) -> UUID:
    return _uuid_from_canonical_bytes(seed.encode("utf-8"))


def _candle(
    symbol: InternalSymbol, timeframe: Timeframe, minute_offset: int
) -> NormalizedCandle:
    event_time = datetime(2024, 1, 15, 9, 30, tzinfo=UTC) + timedelta(
        minutes=minute_offset
    )
    record_id = _uid(f"record-{symbol.value}-{minute_offset}")
    raw_id = _uid(f"raw-{symbol.value}-{minute_offset}")
    provenance_id = _uid(f"provenance-{symbol.value}")
    return NormalizedCandle(
        record_id=record_id,
        content_fingerprint="a" * 64,
        raw_candle_id=raw_id,
        provider="FXCM",
        source_reference=f"ref-{minute_offset}",
        source_symbol=symbol.value,
        source_timeframe=timeframe.value,
        symbol=symbol,
        timeframe=timeframe,
        event_time_utc=event_time,
        availability_time_utc=event_time + timedelta(minutes=1),
        processing_time_utc=event_time + timedelta(minutes=1),
        original_event_time=event_time,
        original_availability_time=event_time + timedelta(minutes=1),
        original_timezone="UTC",
        open=Decimal("2000.00"),
        high=Decimal("2000.50"),
        low=Decimal("1999.50"),
        close=Decimal("2000.10"),
        volume=None,
        volume_kind=CandleVolumeKind.UNKNOWN,
        completeness=CandleCompleteness.CONFIRMED_COMPLETE,
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        provenance_id=provenance_id,
    )


_MANDATORY_MAPPING = (
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.TIMESTAMP, source_column="TIMESTAMP"
    ),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.OPEN, source_column="OPEN"),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.HIGH, source_column="HIGH"),
    HeaderMappingEntry(canonical_field=CanonicalCandleField.LOW, source_column="LOW"),
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.CLOSE, source_column="CLOSE"
    ),
)


def _dataset(symbols: tuple[InternalSymbol, ...]) -> LoadedHistoricalDataset:
    file_entries = tuple(
        HistoricalFileEntry.model_validate(
            {
                "relative_path": f"{symbol.value.lower()}.csv",
                "symbol": symbol,
                "timeframe": Timeframe.M1,
                "format": HistoricalFileFormat.CSV_CANONICAL_V1,
                "header_mapping": _MANDATORY_MAPPING,
                "timestamp_semantics": CandleTimestampConvention.CANDLE_OPEN_TIME,
                "timestamp_format": "%Y-%m-%d %H:%M:%S",
                "calendar_close_day_offset": None,
                "calendar_close_time_local": None,
                "timezone": "UTC",
                "expected_start": datetime(2024, 1, 1, tzinfo=UTC),
                "expected_end": datetime(2024, 1, 20, tzinfo=UTC),
                "expected_row_count": 5,
                "sha256": "a" * 64,
                "volume_available": False,
                "complete_candles_only": True,
            }
        )
        for symbol in symbols
    )
    manifest = DatasetManifest.model_validate(
        {
            "dataset_id": "dataset-1",
            "dataset_version": "1.0.0",
            "provider": "FXCM",
            "source_description": "unit-test fixture",
            "source_timezone": "UTC",
            "created_at_utc": datetime(2024, 1, 20, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": tuple(sorted(symbols, key=lambda s: s.value)),
            "timeframes": (Timeframe.M1,),
            "file_entries": file_entries,
            "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
            "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
            "volume_convention": CandleVolumeKind.TICK,
            "reviewed_case_file": None,
            "reviewed_case_sha256": None,
            "notes": "",
            "schema_version": SemVer.parse("0.1.0"),
        }
    )
    timeframe_inputs_by_symbol = tuple(
        (
            symbol,
            (
                ScannerTimeframeInput(
                    timeframe=Timeframe.M1,
                    candles=tuple(_candle(symbol, Timeframe.M1, i) for i in range(5)),
                ),
            ),
        )
        for symbol in symbols
    )
    return LoadedHistoricalDataset(
        manifest=manifest,
        timeframe_inputs_by_symbol=timeframe_inputs_by_symbol,
        reviewed_cases=(),
        data_quality_report=HistoricalDataQualityReport(
            blank_rows_skipped=0,
            unsorted_rows_resorted=0,
            duplicate_rows_rejected=0,
            issues=(),
            gaps=(),
            checksum_verified=True,
            checksum_mismatched_files=(),
            timeframe_coverage=(),
        ),
        file_checksums=(),
    )


def _scanner_configuration() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=_TICK
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=_TICK),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=_TICK),
        required_timeframes=frozenset({Timeframe.M1}),
        optional_timeframes=frozenset(),
    )


def test_execute_scanner_backtest_runs_one_replay_call_per_symbol(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _dataset((InternalSymbol.XAUUSD, InternalSymbol.GBPUSD))
    call_symbols: list[str] = []
    real_run_scanner_replay = execution_module.run_scanner_replay  # type: ignore[attr-defined]

    def _spy(
        historical_inputs: tuple[ScannerTimeframeInput, ...],
        reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
        scanner_configuration: ScannerConfiguration,
        replay_configuration: ReplayConfiguration,
        identity_provider: ContentAddressedIdentityProvider,
    ) -> ScannerReplayResult:
        call_symbols.append(historical_inputs[0].candles[0].symbol.value)
        return real_run_scanner_replay(
            historical_inputs,
            reviewed_evidence,
            scanner_configuration,
            replay_configuration,
            identity_provider,
        )

    monkeypatch.setattr(execution_module, "run_scanner_replay", _spy)
    execute_scanner_backtest(
        dataset,
        _scanner_configuration(),
        ReplayConfiguration(),
        ContentAddressedIdentityProvider(),
    )
    assert call_symbols == ["XAUUSD", "GBPUSD"]


def test_replay_mismatch_surfaces_as_backtest_execution_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _dataset((InternalSymbol.XAUUSD,))
    real_run_scanner_replay = execution_module.run_scanner_replay  # type: ignore[attr-defined]

    def _mismatched(
        historical_inputs: tuple[ScannerTimeframeInput, ...],
        reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
        scanner_configuration: ScannerConfiguration,
        replay_configuration: ReplayConfiguration,
        identity_provider: ContentAddressedIdentityProvider,
    ) -> ScannerReplayResult:
        real_result = real_run_scanner_replay(
            historical_inputs,
            reviewed_evidence,
            scanner_configuration,
            replay_configuration,
            identity_provider,
        )
        return real_result.model_copy(update={"direct_batch_verified": False})

    monkeypatch.setattr(execution_module, "run_scanner_replay", _mismatched)
    result = execute_scanner_backtest(
        dataset,
        _scanner_configuration(),
        ReplayConfiguration(),
        ContentAddressedIdentityProvider(),
    )
    assert result.quality_gate_status == BacktestQualityGateStatus.FAILED
    assert len(result.warnings) == 1


def test_execute_scanner_backtest_never_opens_a_live_connection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _dataset((InternalSymbol.XAUUSD,))

    def _forbidden_connect(*args: object, **kwargs: object) -> None:
        raise AssertionError(
            "execute_scanner_backtest must never open a network connection."
        )

    monkeypatch.setattr(socket.socket, "connect", _forbidden_connect)
    monkeypatch.setattr(socket, "create_connection", _forbidden_connect)
    execute_scanner_backtest(
        dataset,
        _scanner_configuration(),
        ReplayConfiguration(),
        ContentAddressedIdentityProvider(),
    )


def test_execute_scanner_backtest_performs_no_file_io_of_its_own(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = _dataset((InternalSymbol.XAUUSD,))
    real_open = open

    def _forbidden_open(*args: object, **kwargs: object) -> object:
        raise AssertionError(
            "execute_scanner_backtest must perform no file I/O of its own."
        )

    monkeypatch.setattr("builtins.open", _forbidden_open)
    try:
        execute_scanner_backtest(
            dataset,
            _scanner_configuration(),
            ReplayConfiguration(),
            ContentAddressedIdentityProvider(),
        )
    finally:
        monkeypatch.setattr("builtins.open", real_open)
