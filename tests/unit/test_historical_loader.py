import hashlib
from datetime import UTC, datetime, time
from decimal import Decimal
from pathlib import Path
from typing import cast

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.data_quality import warm_up_floor_bars
from btmm_ai_scanner.historical_backtest.enums import (
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.loader import (
    _resolve_and_validate_path,
    load_historical_dataset,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration

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

_MANDATORY_MAPPING_WITH_COMPLETE = (
    *_MANDATORY_MAPPING,
    HeaderMappingEntry(
        canonical_field=CanonicalCandleField.COMPLETE, source_column="COMPLETE"
    ),
)


def _entry(**overrides: object) -> dict[str, object]:
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
        "expected_row_count": 1,
        "sha256": "a" * 64,
        "volume_available": False,
        "complete_candles_only": True,
    }
    fields.update(overrides)
    return fields


def _manifest_dict(file_entries: tuple[dict[str, object], ...]) -> dict[str, object]:
    symbols_present = {cast(InternalSymbol, entry["symbol"]) for entry in file_entries}
    timeframes_present = {cast(Timeframe, entry["timeframe"]) for entry in file_entries}
    symbols = tuple(sorted(symbols_present, key=lambda s: s.value))
    timeframes = tuple(sorted(timeframes_present, key=lambda t: t.value))
    return {
        "dataset_id": "dataset-1",
        "dataset_version": "1.0.0",
        "provider": "FXCM",
        "source_description": "unit-test fixture",
        "source_timezone": "UTC",
        "created_at_utc": datetime(2024, 1, 3, tzinfo=UTC),
        "partition": DatasetPartition.DEVELOPMENT,
        "symbols": symbols,
        "timeframes": timeframes,
        "file_entries": tuple(
            HistoricalFileEntry.model_validate(entry) for entry in file_entries
        ),
        "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
        "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
        "volume_convention": CandleVolumeKind.TICK,
        "reviewed_case_file": None,
        "reviewed_case_sha256": None,
        "notes": "",
        "schema_version": SemVer.parse("0.1.0"),
    }


def _write_csv_and_hash(path: Path, text: str) -> str:
    path.write_bytes(text.encode("utf-8"))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_unsupported_symbol_rejects_dataset() -> None:
    with pytest.raises(ValidationError):
        HistoricalFileEntry.model_validate(_entry(symbol="NOTREAL"))


def test_unsupported_timeframe_rejects_dataset() -> None:
    with pytest.raises(ValidationError):
        HistoricalFileEntry.model_validate(_entry(timeframe="NOTREAL"))


def test_loader_result_ordering_independent_of_filesystem_enumeration_order(
    tmp_path: Path,
) -> None:
    xauusd_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    gbpusd_text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,1.20,1.21,1.19,1.205\n"
    )
    xauusd_sha = _write_csv_and_hash(tmp_path / "z_xauusd.csv", xauusd_text)
    gbpusd_sha = _write_csv_and_hash(tmp_path / "a_gbpusd.csv", gbpusd_text)

    gbpusd_entry = _entry(
        relative_path="a_gbpusd.csv", symbol=InternalSymbol.GBPUSD, sha256=gbpusd_sha
    )
    xauusd_entry = _entry(
        relative_path="z_xauusd.csv", symbol=InternalSymbol.XAUUSD, sha256=xauusd_sha
    )
    manifest_dict = _manifest_dict((gbpusd_entry, xauusd_entry))
    manifest = DatasetManifest.model_validate(manifest_dict)
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
    ordered_symbols = [symbol.value for symbol, _ in dataset.timeframe_inputs_by_symbol]
    assert ordered_symbols == ["XAUUSD", "GBPUSD"]


def test_warm_up_floor_computed_from_configuration_not_hardcoded() -> None:
    measurement_configuration = MarketMeasurementConfiguration(
        minimum_price_tick=Decimal("0.01"), atr_period=99
    )
    btmm_configuration = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
    poi_configuration = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    floor = warm_up_floor_bars(
        measurement_configuration, btmm_configuration, poi_configuration
    )
    assert floor == 99


def test_period_level_timeframe_coverage_reports_complete_calendar_period_count(
    tmp_path: Path,
) -> None:
    d1_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n" + "".join(
        f"2024-01-{day:02d} 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
        for day in range(1, 4)
    )
    d1_sha = _write_csv_and_hash(tmp_path / "d1.csv", d1_text)
    d1_entry = _entry(
        relative_path="d1.csv",
        timeframe=Timeframe.D1,
        calendar_close_day_offset=1,
        calendar_close_time_local=time(0, 0, 0),
        expected_row_count=3,
        expected_end=datetime(2024, 1, 10, tzinfo=UTC),
        sha256=d1_sha,
    )
    manifest_dict = _manifest_dict((d1_entry,))
    manifest_dict["created_at_utc"] = datetime(2024, 1, 10, tzinfo=UTC)
    manifest = DatasetManifest.model_validate(manifest_dict)
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
    d1_coverage = next(
        c
        for c in dataset.data_quality_report.timeframe_coverage
        if c.timeframe == Timeframe.D1
    )
    assert d1_coverage.complete_calendar_period_count == 3

    m1_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    m1_sha = _write_csv_and_hash(tmp_path / "m1.csv", m1_text)
    m1_entry = _entry(relative_path="m1.csv", sha256=m1_sha)
    manifest_dict_m1 = _manifest_dict((m1_entry,))
    manifest_m1 = DatasetManifest.model_validate(manifest_dict_m1)
    (tmp_path / "manifest.json").write_bytes(
        manifest_m1.model_dump_json().encode("utf-8")
    )
    dataset_m1 = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
    m1_coverage = next(
        c
        for c in dataset_m1.data_quality_report.timeframe_coverage
        if c.timeframe == Timeframe.M1
    )
    assert m1_coverage.complete_calendar_period_count is None

    # Strengthened: an UNKNOWN-completeness D1 candle (complete_candles_only=False,
    # no explicit completeness column) is retained in candle_count but must not be
    # counted as a complete calendar period.
    unknown_root = tmp_path / "unknown_scenario"
    unknown_root.mkdir()
    unknown_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    unknown_sha = _write_csv_and_hash(unknown_root / "d1.csv", unknown_text)
    unknown_entry = _entry(
        relative_path="d1.csv",
        timeframe=Timeframe.D1,
        calendar_close_day_offset=1,
        calendar_close_time_local=time(0, 0, 0),
        expected_row_count=1,
        expected_end=datetime(2024, 1, 10, tzinfo=UTC),
        sha256=unknown_sha,
        complete_candles_only=False,
    )
    unknown_manifest_dict = _manifest_dict((unknown_entry,))
    unknown_manifest_dict["created_at_utc"] = datetime(2024, 1, 10, tzinfo=UTC)
    unknown_manifest = DatasetManifest.model_validate(unknown_manifest_dict)
    (unknown_root / "manifest.json").write_bytes(
        unknown_manifest.model_dump_json().encode("utf-8")
    )
    unknown_dataset = load_historical_dataset(
        unknown_root, HistoricalDatasetConfiguration()
    )
    unknown_d1_coverage = next(
        c
        for c in unknown_dataset.data_quality_report.timeframe_coverage
        if c.timeframe == Timeframe.D1
    )
    assert unknown_d1_coverage.candle_count == 1
    assert unknown_d1_coverage.complete_calendar_period_count == 0

    # Strengthened: an explicitly CONFIRMED_COMPLETE D1 candle whose own
    # availability_time_utc is still after manifest.created_at_utc (the
    # calendar period has not actually closed as of dataset creation) is
    # retained in candle_count but must not be counted as a complete
    # calendar period either.
    future_root = tmp_path / "future_availability_scenario"
    future_root.mkdir()
    future_text = (
        "TIMESTAMP,OPEN,HIGH,LOW,CLOSE,COMPLETE\n"
        "2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10,true\n"
    )
    future_sha = _write_csv_and_hash(future_root / "d1.csv", future_text)
    future_entry = _entry(
        relative_path="d1.csv",
        timeframe=Timeframe.D1,
        header_mapping=_MANDATORY_MAPPING_WITH_COMPLETE,
        calendar_close_day_offset=1,
        calendar_close_time_local=time(0, 0, 0),
        expected_row_count=1,
        expected_end=datetime(2024, 1, 10, tzinfo=UTC),
        sha256=future_sha,
        complete_candles_only=True,
    )
    future_manifest_dict = _manifest_dict((future_entry,))
    # created_at_utc is before the D1 candle's own calendar close (2024-01-02),
    # so the period has not genuinely closed yet despite the explicit override.
    future_manifest_dict["created_at_utc"] = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    future_manifest = DatasetManifest.model_validate(future_manifest_dict)
    (future_root / "manifest.json").write_bytes(
        future_manifest.model_dump_json().encode("utf-8")
    )
    future_dataset = load_historical_dataset(
        future_root, HistoricalDatasetConfiguration()
    )
    future_d1_coverage = next(
        c
        for c in future_dataset.data_quality_report.timeframe_coverage
        if c.timeframe == Timeframe.D1
    )
    assert future_d1_coverage.candle_count == 1
    assert future_d1_coverage.complete_calendar_period_count == 0


def test_insufficient_history_flagged_per_case_not_silently_scored(
    tmp_path: Path,
) -> None:
    m1_text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-01 00:00:00,2000.00,2000.50,1999.50,2000.10\n"
    m1_sha = _write_csv_and_hash(tmp_path / "m1.csv", m1_text)
    m1_entry = _entry(relative_path="m1.csv", sha256=m1_sha)
    manifest_dict = _manifest_dict((m1_entry,))
    manifest = DatasetManifest.model_validate(manifest_dict)
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    dataset = load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
    coverage = dataset.data_quality_report.timeframe_coverage[0]
    assert coverage.candle_count == 1
    assert coverage.meets_warm_up_floor is False


def test_symlink_descendant_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "data.csv").write_text("placeholder")
    original_is_symlink = Path.is_symlink

    def _fake_is_symlink(self: Path) -> bool:
        if self.name == "data.csv":
            return True
        return original_is_symlink(self)

    monkeypatch.setattr(Path, "is_symlink", _fake_is_symlink)
    with pytest.raises(InvalidDatasetManifestError):
        _resolve_and_validate_path(tmp_path, "data.csv")


def test_casefold_path_collision_is_rejected(tmp_path: Path) -> None:
    entry_upper = _entry(relative_path="Data.csv")
    entry_lower = _entry(relative_path="data.csv")
    manifest_dict = _manifest_dict((entry_upper, entry_lower))
    manifest = DatasetManifest.model_validate(manifest_dict)
    (tmp_path / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))

    with pytest.raises(InvalidDatasetManifestError):
        load_historical_dataset(tmp_path, HistoricalDatasetConfiguration())
