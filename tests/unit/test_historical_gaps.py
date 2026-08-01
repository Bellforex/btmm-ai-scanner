import hashlib
from datetime import UTC, datetime
from pathlib import Path

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.data_quality import detect_gap
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.loader import load_historical_dataset
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
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


def test_gap_report_records_missing_bars_without_synthesizing_candles(
    tmp_path: Path,
) -> None:
    entry = HistoricalFileEntry.model_validate(
        {
            "relative_path": "data.csv",
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
            "expected_row_count": 2,
            "sha256": "a" * 64,
            "volume_available": False,
            "complete_candles_only": True,
        }
    )
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-15 09:30:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-15 09:35:00,2000.10,2000.60,1999.60,2000.20\n"
    )
    csv_path = tmp_path / "data.csv"
    csv_path.write_bytes(text.encode("utf-8"))
    entry = entry.model_copy(
        update={"sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest()}
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
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
    candles = dict(dataset.timeframe_inputs_by_symbol)[InternalSymbol.XAUUSD]
    total_candles = sum(len(bundle.candles) for bundle in candles)
    assert total_candles == 2

    assert len(dataset.data_quality_report.gaps) == 1
    gap = dataset.data_quality_report.gaps[0]
    assert gap.missing_bar_count == 4


def test_weekend_gap_flagged_likely_market_closure() -> None:
    friday_close = datetime(2024, 1, 12, 22, 0, tzinfo=UTC)
    monday_open = datetime(2024, 1, 15, 0, 0, tzinfo=UTC)
    gap = detect_gap(InternalSymbol.XAUUSD, Timeframe.M1, friday_close, monday_open)
    assert gap is not None
    assert gap.likely_market_closure is True

    weekday_previous = datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
    weekday_current = datetime(2024, 1, 15, 9, 40, tzinfo=UTC)
    weekday_gap = detect_gap(
        InternalSymbol.XAUUSD, Timeframe.M1, weekday_previous, weekday_current
    )
    assert weekday_gap is not None
    assert weekday_gap.likely_market_closure is False


def test_no_forward_fill_or_interpolation_anywhere_in_gap_handling() -> None:
    previous_time = datetime(2024, 1, 15, 9, 30, tzinfo=UTC)
    current_time = datetime(2024, 1, 15, 9, 40, tzinfo=UTC)
    gap = detect_gap(InternalSymbol.XAUUSD, Timeframe.M1, previous_time, current_time)
    assert gap is not None
    assert gap.missing_bar_count == 9
    assert gap.gap_start_event_time_utc == previous_time
    assert gap.gap_end_event_time_utc == current_time
