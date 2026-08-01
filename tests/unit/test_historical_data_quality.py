import hashlib
from datetime import UTC, datetime
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.csv_parser import (
    FileRejected,
    parse_candle_rows,
)
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DataQualityClassification,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.identity import CandleIdentityCollisionTracker
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

_MANDATORY_MAPPING_WITH_VOLUME = (
    *_MANDATORY_MAPPING,
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.VOLUME, source_column="VOLUME"
    ),
)


def _entry(**overrides: object) -> HistoricalFileEntry:
    fields: dict[str, object] = {
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
        "expected_end": datetime(2024, 1, 3, tzinfo=UTC),
        "expected_row_count": 2,
        "sha256": "a" * 64,
        "volume_available": False,
        "complete_candles_only": True,
    }
    fields.update(overrides)
    return HistoricalFileEntry.model_validate(fields)


def _manifest(
    file_entries: tuple[HistoricalFileEntry, ...],
    created_at_utc: datetime | None = None,
) -> DatasetManifest:
    return DatasetManifest.model_validate(
        {
            "dataset_id": "dataset-1",
            "dataset_version": "1.0.0",
            "provider": "FXCM",
            "source_description": "unit-test fixture",
            "source_timezone": "UTC",
            "created_at_utc": created_at_utc or datetime(2024, 1, 3, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": (InternalSymbol.XAUUSD,),
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


def _write_dataset(
    tmp_path: Path,
    entry: HistoricalFileEntry,
    text: str,
    created_at_utc: datetime | None = None,
) -> Path:
    csv_path = tmp_path / entry.relative_path
    csv_path.write_bytes(text.encode("utf-8"))
    entry = entry.model_copy(
        update={"sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest()}
    )
    manifest = _manifest((entry,), created_at_utc=created_at_utc)
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))
    return tmp_path


def test_incomplete_candle_excluded_from_confirmed_history_batch(
    tmp_path: Path,
) -> None:
    entry = _entry(expected_row_count=2, complete_candles_only=True)
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-01 00:01:00,2000.10,2000.60,1999.60,2000.20\n"
    )
    root = _write_dataset(
        tmp_path, entry, text, created_at_utc=datetime(2024, 1, 1, 0, 1, 30, tzinfo=UTC)
    )
    dataset = load_historical_dataset(root, HistoricalDatasetConfiguration())
    candles = dict(dataset.timeframe_inputs_by_symbol)[InternalSymbol.XAUUSD]
    total_candles = sum(len(bundle.candles) for bundle in candles)
    assert total_candles == 1
    incomplete_issues = [
        issue
        for issue in dataset.data_quality_report.issues
        if issue.reason_code == "INCOMPLETE_CANDLE_EXCLUDED"
    ]
    assert len(incomplete_issues) == 1


def test_duplicate_identical_row_rejected_keeping_first_occurrence() -> None:
    entry = _entry(expected_row_count=2)
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    )
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert result.duplicate_rows_rejected == 1
    assert len(result.records) == 1


def test_duplicate_differing_row_rejects_whole_file() -> None:
    entry = _entry(expected_row_count=2)
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-01 00:00:00,2001.00,2001.50,2000.50,2001.10\n"
    )
    with pytest.raises(FileRejected) as exc_info:
        parse_candle_rows(
            decoded_text=text,
            entry=entry,
            manifest=manifest,
            identity_tracker=CandleIdentityCollisionTracker(),
        )
    assert exc_info.value.reason_code == "DUPLICATE_TIMESTAMP_DIFFERING_OHLCV"


def test_invalid_ohlc_geometry_row_rejected() -> None:
    entry = _entry(expected_row_count=1)
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.05,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 0
    assert result.issues[0].reason_code == "INVALID_OHLC_GEOMETRY"
    assert result.issues[0].classification == DataQualityClassification.REJECT_ROW


def test_missing_volume_retained_as_unknown_kind(tmp_path: Path) -> None:
    entry = _entry(header_mapping=_MANDATORY_MAPPING_WITH_VOLUME, expected_row_count=1)
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE,VOLUME\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10,\n"
    root = _write_dataset(tmp_path, entry, text)
    dataset = load_historical_dataset(root, HistoricalDatasetConfiguration())
    candles = dict(dataset.timeframe_inputs_by_symbol)[InternalSymbol.XAUUSD]
    all_candles = [candle for bundle in candles for candle in bundle.candles]
    assert len(all_candles) == 1
    assert all_candles[0].volume is None
    assert all_candles[0].volume_kind == CandleVolumeKind.UNKNOWN


def test_row_outside_manifest_declared_range_rejected() -> None:
    entry = _entry(expected_row_count=1)
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2025-06-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 0
    assert result.issues[0].reason_code == "TIMESTAMP_OUTSIDE_EXPECTED_RANGE"


def test_unexpected_row_count_reported_as_warning_only(tmp_path: Path) -> None:
    entry = _entry(expected_row_count=5)
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    root = _write_dataset(tmp_path, entry, text)
    dataset = load_historical_dataset(root, HistoricalDatasetConfiguration())
    warning_issues = [
        issue
        for issue in dataset.data_quality_report.issues
        if issue.reason_code == "UNEXPECTED_ROW_COUNT"
    ]
    assert len(warning_issues) == 1
    assert warning_issues[0].classification == DataQualityClassification.WARNING
