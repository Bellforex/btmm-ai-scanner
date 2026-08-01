from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
    validate_dataset_manifest,
)

_VALID_SHA256 = "a" * 64
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


def _build_file_entry(**overrides: object) -> HistoricalFileEntry:
    fields: dict[str, object] = {
        "relative_path": "xauusd_m1.csv",
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
        "expected_row_count": 10,
        "sha256": _VALID_SHA256,
        "volume_available": True,
        "complete_candles_only": True,
    }
    fields.update(overrides)
    return HistoricalFileEntry.model_validate(fields)


def _build_manifest(**overrides: object) -> DatasetManifest:
    fields: dict[str, object] = {
        "dataset_id": "dataset-1",
        "dataset_version": "1.0.0",
        "provider": "FXCM",
        "source_description": "unit-test fixture",
        "source_timezone": "UTC",
        "created_at_utc": datetime(2024, 1, 3, tzinfo=UTC),
        "partition": DatasetPartition.DEVELOPMENT,
        "symbols": (InternalSymbol.XAUUSD,),
        "timeframes": (Timeframe.M1,),
        "file_entries": (_build_file_entry(),),
        "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
        "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
        "volume_convention": CandleVolumeKind.TICK,
        "reviewed_case_file": None,
        "reviewed_case_sha256": None,
        "notes": "",
        "schema_version": SemVer.parse("0.1.0"),
    }
    fields.update(overrides)
    return DatasetManifest.model_validate(fields)


def test_manifest_rejects_missing_required_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetManifest.model_validate(
            {
                "dataset_id": "dataset-1",
                "dataset_version": "1.0.0",
            }
        )


def test_manifest_rejects_path_traversal_relative_path() -> None:
    manifest = _build_manifest(
        file_entries=(_build_file_entry(relative_path="../escape.csv"),)
    )
    with pytest.raises(InvalidDatasetManifestError):
        validate_dataset_manifest(manifest)


def test_manifest_rejects_symbols_timeframes_summary_mismatch() -> None:
    manifest = _build_manifest(symbols=(InternalSymbol.XAUUSD, InternalSymbol.EURUSD))
    with pytest.raises(InvalidDatasetManifestError):
        validate_dataset_manifest(manifest)


def test_manifest_rejects_empty_file_entries() -> None:
    manifest = _build_manifest(file_entries=())
    with pytest.raises(InvalidDatasetManifestError):
        validate_dataset_manifest(manifest)


def test_manifest_rejects_checksum_mismatch_for_whole_dataset() -> None:
    with pytest.raises(ValidationError):
        _build_file_entry(sha256="not-a-valid-sha256")


def test_manifest_rejects_unsupported_timestamp_convention() -> None:
    with pytest.raises(ValidationError):
        _build_file_entry(timestamp_semantics="NOT_A_REAL_CONVENTION")
