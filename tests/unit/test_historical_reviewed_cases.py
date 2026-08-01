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
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.loader import (
    ReviewedCaseDocument,
    load_historical_dataset,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
)
from btmm_ai_scanner.scanner.labels import (
    InvalidReviewedLabelError,
    ReviewedScannerCase,
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


def _case(**overrides: object) -> ReviewedScannerCase:
    fields: dict[str, object] = {
        "case_id": "case-1",
        "dataset_version": "1.0.0",
        "reviewer_id": "reviewer-1",
        "review_version": "1.0.0",
        "symbol": InternalSymbol.XAUUSD,
        "evaluation_start_time_utc": datetime(2024, 1, 1, tzinfo=UTC),
        "evaluation_end_time_utc": datetime(2024, 1, 2, tzinfo=UTC),
        "required_timeframes": (Timeframe.M1,),
        "expected_poi_labels": (),
        "expected_btmm_labels": (),
        "poi_labels_complete": False,
        "btmm_labels_complete": False,
        "notes": "",
    }
    fields.update(overrides)
    return ReviewedScannerCase.model_validate(fields)


def _write_dataset(
    tmp_path: Path, reviewed_document: ReviewedCaseDocument | None
) -> Path:
    csv_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    csv_path = tmp_path / "data.csv"
    csv_path.write_bytes(csv_text.encode("utf-8"))
    csv_sha = hashlib.sha256(csv_path.read_bytes()).hexdigest()

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
            "expected_end": datetime(2024, 1, 3, tzinfo=UTC),
            "expected_row_count": 1,
            "sha256": csv_sha,
            "volume_available": False,
            "complete_candles_only": True,
        }
    )

    reviewed_case_file = None
    reviewed_case_sha256 = None
    if reviewed_document is not None:
        reviewed_path = tmp_path / "reviewed_cases.json"
        reviewed_path.write_bytes(reviewed_document.model_dump_json().encode("utf-8"))
        reviewed_case_file = "reviewed_cases.json"
        reviewed_case_sha256 = hashlib.sha256(reviewed_path.read_bytes()).hexdigest()

    manifest = DatasetManifest.model_validate(
        {
            "dataset_id": "dataset-1",
            "dataset_version": "1.0.0",
            "provider": "FXCM",
            "source_description": "unit-test fixture",
            "source_timezone": "UTC",
            "created_at_utc": datetime(2024, 1, 3, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": (InternalSymbol.XAUUSD,),
            "timeframes": (Timeframe.M1,),
            "file_entries": (entry,),
            "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
            "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
            "volume_convention": CandleVolumeKind.TICK,
            "reviewed_case_file": reviewed_case_file,
            "reviewed_case_sha256": reviewed_case_sha256,
            "notes": "",
            "schema_version": SemVer.parse("0.1.0"),
        }
    )
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))
    return tmp_path


def test_reviewed_case_document_loads_in_declared_file_order(tmp_path: Path) -> None:
    document = ReviewedCaseDocument(
        schema_version=SemVer.parse("0.1.0"),
        dataset_id="dataset-1",
        cases=(_case(case_id="case-b"), _case(case_id="case-a")),
    )
    root = _write_dataset(tmp_path, document)
    dataset = load_historical_dataset(root, HistoricalDatasetConfiguration())
    assert [case.case_id for case in dataset.reviewed_cases] == ["case-b", "case-a"]


def test_reviewed_case_document_rejects_duplicate_case_id(tmp_path: Path) -> None:
    document = ReviewedCaseDocument(
        schema_version=SemVer.parse("0.1.0"),
        dataset_id="dataset-1",
        cases=(_case(case_id="case-1"), _case(case_id="case-1")),
    )
    root = _write_dataset(tmp_path, document)
    with pytest.raises(InvalidDatasetManifestError):
        load_historical_dataset(root, HistoricalDatasetConfiguration())


def test_invalid_reviewed_case_rejects_whole_file_before_evaluation(
    tmp_path: Path,
) -> None:
    invalid_case = _case(
        evaluation_start_time_utc=datetime(2024, 1, 2, tzinfo=UTC),
        evaluation_end_time_utc=datetime(2024, 1, 1, tzinfo=UTC),
    )
    document = ReviewedCaseDocument(
        schema_version=SemVer.parse("0.1.0"),
        dataset_id="dataset-1",
        cases=(invalid_case,),
    )
    root = _write_dataset(tmp_path, document)
    with pytest.raises(InvalidReviewedLabelError):
        load_historical_dataset(root, HistoricalDatasetConfiguration())
