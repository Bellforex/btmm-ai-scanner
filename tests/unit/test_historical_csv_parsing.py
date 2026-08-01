import hashlib
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.csv_parser import (
    parse_candle_rows,
)
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
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


def _manifest(file_entries: tuple[HistoricalFileEntry, ...]) -> DatasetManifest:
    return DatasetManifest.model_validate(
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


def test_canonical_schema_parses_via_explicit_header_mapping() -> None:
    entry = _entry()
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-01 00:01:00,2000.10,2000.60,1999.60,2000.20\n"
    )
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 2
    assert result.records[0].open_price == Decimal("2000.00")


def test_ohlc_parsed_as_decimal_never_float() -> None:
    entry = _entry()
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        "2024-01-01 00:01:00,2000.10,2000.60,1999.60,2000.20\n"
    )
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    for record in result.records:
        for value in (
            record.open_price,
            record.high_price,
            record.low_price,
            record.close_price,
        ):
            assert isinstance(value, Decimal)
            assert not isinstance(value, float)


def test_blank_rows_skipped_and_counted() -> None:
    entry = _entry(expected_row_count=2)
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        ",,,,\n"
        "2024-01-01 00:01:00,2000.10,2000.60,1999.60,2000.20\n"
    )
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert result.blank_rows_skipped == 1
    assert len(result.records) == 2


def test_duplicate_header_row_rejects_file_only_not_dataset(tmp_path: Path) -> None:
    good_entry = _entry(relative_path="good.csv", expected_row_count=1)
    bad_entry = _entry(relative_path="bad.csv", expected_row_count=1)

    good_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    bad_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE,OPEN\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10,2000.00\n"

    (tmp_path / "good.csv").write_bytes(good_text.encode("utf-8"))
    (tmp_path / "bad.csv").write_bytes(bad_text.encode("utf-8"))

    good_entry = good_entry.model_copy(
        update={
            "sha256": hashlib.sha256((tmp_path / "good.csv").read_bytes()).hexdigest()
        }
    )
    bad_entry = bad_entry.model_copy(
        update={
            "sha256": hashlib.sha256((tmp_path / "bad.csv").read_bytes()).hexdigest()
        }
    )

    manifest = _manifest((good_entry, bad_entry))
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())

    reject_file_issues = [
        issue
        for issue in dataset.data_quality_report.issues
        if issue.relative_path == "bad.csv"
    ]
    assert len(reject_file_issues) == 1
    assert reject_file_issues[0].reason_code == "DUPLICATE_HEADER_COLUMN"

    good_candles = dict(dataset.timeframe_inputs_by_symbol)[InternalSymbol.XAUUSD]
    assert sum(len(bundle.candles) for bundle in good_candles) == 1


def test_unsupported_encoding_rejects_file_only_not_dataset(tmp_path: Path) -> None:
    good_entry = _entry(relative_path="good.csv", expected_row_count=1)
    bad_entry = _entry(relative_path="bad.csv", expected_row_count=1)

    good_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    bad_bytes = b"TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n\xff\xfe\x00\x01,2000.00,2000.50,1999.50,2000.10\n"

    (tmp_path / "good.csv").write_bytes(good_text.encode("utf-8"))
    (tmp_path / "bad.csv").write_bytes(bad_bytes)

    good_entry = good_entry.model_copy(
        update={
            "sha256": hashlib.sha256((tmp_path / "good.csv").read_bytes()).hexdigest()
        }
    )
    bad_entry = bad_entry.model_copy(
        update={
            "sha256": hashlib.sha256((tmp_path / "bad.csv").read_bytes()).hexdigest()
        }
    )

    manifest = _manifest((good_entry, bad_entry))
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())

    reject_file_issues = [
        issue
        for issue in dataset.data_quality_report.issues
        if issue.relative_path == "bad.csv"
    ]
    assert len(reject_file_issues) == 1
    assert reject_file_issues[0].reason_code == "UNSUPPORTED_ENCODING"

    good_candles = dict(dataset.timeframe_inputs_by_symbol)[InternalSymbol.XAUUSD]
    assert sum(len(bundle.candles) for bundle in good_candles) == 1


def test_bom_stripped_transparently_from_first_header() -> None:
    entry = _entry(expected_row_count=1)
    manifest = _manifest((entry,))
    text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    )
    raw_bytes = text.encode("utf-8-sig")
    decoded_text = raw_bytes.decode("utf-8-sig")
    result = parse_candle_rows(
        decoded_text=decoded_text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 1
