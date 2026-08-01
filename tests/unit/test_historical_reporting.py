import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest import reporting as reporting_module
from btmm_ai_scanner.historical_backtest.data_quality import HistoricalDataQualityReport
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.execution import (
    HistoricalBacktestExecutionResult,
    execute_scanner_backtest,
)
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
from btmm_ai_scanner.historical_backtest.reporting import (
    HistoricalReportWriteError,
    write_backtest_report,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_TICK = Decimal("0.01")

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


def _uid(seed: str) -> UUID:
    return _uuid_from_canonical_bytes(seed.encode("utf-8"))


def _candle(
    symbol: InternalSymbol, timeframe: Timeframe, minute_offset: int
) -> NormalizedCandle:
    event_time = datetime(2024, 1, 15, 9, 30, tzinfo=UTC) + timedelta(
        minutes=minute_offset
    )
    return NormalizedCandle(
        record_id=_uid(f"record-{symbol.value}-{minute_offset}"),
        content_fingerprint="a" * 64,
        raw_candle_id=_uid(f"raw-{symbol.value}-{minute_offset}"),
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
        provenance_id=_uid(f"provenance-{symbol.value}"),
    )


def _build_execution_result() -> HistoricalBacktestExecutionResult:
    entry = HistoricalFileEntry.model_validate(
        {
            "relative_path": "xauusd.csv",
            "symbol": InternalSymbol.XAUUSD,
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
    manifest = DatasetManifest.model_validate(
        {
            "dataset_id": "dataset-1",
            "dataset_version": "1.0.0",
            "provider": "FXCM",
            "source_description": "unit-test fixture",
            "source_timezone": "UTC",
            "created_at_utc": datetime(2024, 1, 20, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": (InternalSymbol.XAUUSD,),
            "timeframes": (Timeframe.M1,),
            "file_entries": (entry,),
            "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
            "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
            "volume_convention": CandleVolumeKind.TICK,
            "reviewed_case_file": None,
            "reviewed_case_sha256": None,
            "notes": "",
            "schema_version": SemVer.parse("0.1.0"),
        }
    )
    dataset = LoadedHistoricalDataset(
        manifest=manifest,
        timeframe_inputs_by_symbol=(
            (
                InternalSymbol.XAUUSD,
                (
                    ScannerTimeframeInput(
                        timeframe=Timeframe.M1,
                        candles=tuple(
                            _candle(InternalSymbol.XAUUSD, Timeframe.M1, i)
                            for i in range(5)
                        ),
                    ),
                ),
            ),
        ),
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
    scanner_configuration = ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=_TICK
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=_TICK),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=_TICK),
        required_timeframes=frozenset({Timeframe.M1}),
        optional_timeframes=frozenset(),
    )
    return execute_scanner_backtest(
        dataset,
        scanner_configuration,
        ReplayConfiguration(),
        ContentAddressedIdentityProvider(),
    )


def test_json_report_writer_is_deterministic_and_atomic(tmp_path: Path) -> None:
    result = _build_execution_result()
    first_write = write_backtest_report(result, tmp_path / "run-1")
    second_write = write_backtest_report(result, tmp_path / "run-2")

    first_dir = Path(first_write.execution_directory)
    second_dir = Path(second_write.execution_directory)
    for file_name in first_write.written_file_paths:
        assert (first_dir / file_name).read_bytes() == (
            second_dir / file_name
        ).read_bytes()

    assert "checksums.json" not in first_write.written_file_paths
    checksums_payload = json.loads((first_dir / "checksums.json").read_bytes())
    checksum_names = {entry[0] for entry in checksums_payload["files"]}
    assert "checksums.json" not in checksum_names
    assert (first_dir / "checksums.json").is_file()
    assert not list(first_dir.glob("*.tmp-*"))


def test_json_report_writer_refuses_to_overwrite_existing_execution(
    tmp_path: Path,
) -> None:
    result = _build_execution_result()
    write_backtest_report(result, tmp_path)
    with pytest.raises(HistoricalReportWriteError):
        write_backtest_report(result, tmp_path)


def test_execution_summary_contains_no_profit_or_entry_fields(tmp_path: Path) -> None:
    result = _build_execution_result()
    write_result = write_backtest_report(result, tmp_path)
    execution_summary_path = (
        Path(write_result.execution_directory) / "execution_summary.json"
    )
    payload_text = execution_summary_path.read_text(encoding="utf-8")

    forbidden_field_names = (
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_reward",
        "position_size",
        "trade_outcome",
    )
    for field_name in forbidden_field_names:
        assert field_name not in payload_text


def test_json_report_writer_cleans_up_temporary_file_after_failed_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result = _build_execution_result()
    real_write_json_file = reporting_module._write_json_file
    call_count = {"n": 0}

    def _flaky_write(payload: object, final_path: Path) -> str:
        call_count["n"] += 1
        if call_count["n"] == 2:
            raise reporting_module.HistoricalReportWriteError("simulated failure")
        return real_write_json_file(payload, final_path)

    monkeypatch.setattr(reporting_module, "_write_json_file", _flaky_write)

    with pytest.raises(HistoricalReportWriteError):
        write_backtest_report(result, tmp_path)

    execution_directory = tmp_path / result.dataset_id / str(result.execution_id)
    assert not execution_directory.exists()
    assert not list(tmp_path.rglob("*.tmp-*"))
    assert not list(tmp_path.rglob("checksums.json"))
