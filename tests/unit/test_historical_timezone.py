from datetime import UTC, datetime, time, timedelta

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest.csv_parser import (
    _derive_event_and_availability,
    _RowRejected,
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
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
    _load_bundled_zone,
    validate_historical_file_entry,
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
        "expected_start": datetime(2020, 1, 1, tzinfo=UTC),
        "expected_end": datetime(2030, 1, 1, tzinfo=UTC),
        "expected_row_count": 1,
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
            "source_timezone": file_entries[0].timezone,
            "created_at_utc": datetime(2030, 1, 1, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": (InternalSymbol.XAUUSD,),
            "timeframes": (file_entries[0].timeframe,),
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


def test_source_local_open_timestamp_converts_to_utc() -> None:
    entry = _entry(timezone="America/New_York")
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-01-15 09:30:00,2000.00,2000.50,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 1
    assert result.records[0].event_time_utc == datetime(2024, 1, 15, 14, 30, tzinfo=UTC)


def test_ambiguous_local_open_timestamp_rejected() -> None:
    entry = _entry(timezone="America/New_York")
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-11-03 01:30:00,2000.00,2000.50,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 0
    assert len(result.issues) == 1
    assert result.issues[0].reason_code == "AMBIGUOUS_LOCAL_TIME"


def test_nonexistent_local_open_timestamp_rejected() -> None:
    entry = _entry(timezone="America/New_York")
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n2024-03-10 02:30:00,2000.00,2000.50,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 0
    assert len(result.issues) == 1
    assert result.issues[0].reason_code == "NONEXISTENT_LOCAL_TIME"


def test_intraday_availability_uses_fixed_elapsed_duration() -> None:
    entry = _entry(timeframe=Timeframe.M1, timezone="UTC")
    zone = _load_bundled_zone("UTC")
    naive_open = datetime(2024, 1, 15, 9, 30, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)
    availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry
    )
    assert availability == event_time_utc + timedelta(minutes=1)


def test_d1_availability_uses_local_calendar_day_boundary_not_fixed_24_hours() -> None:
    entry = _entry(
        timeframe=Timeframe.D1,
        timezone="America/New_York",
        calendar_close_day_offset=1,
        calendar_close_time_local=time(17, 0, 0),
    )
    zone = _load_bundled_zone("America/New_York")
    naive_open = datetime(2024, 3, 9, 17, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)
    availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry
    )
    elapsed = availability - event_time_utc
    assert elapsed == timedelta(hours=23)
    assert elapsed != timedelta(hours=24)


def test_w1_availability_uses_local_calendar_week_boundary_not_fixed_168_hours() -> (
    None
):
    entry = _entry(
        timeframe=Timeframe.W1,
        timezone="America/New_York",
        calendar_close_day_offset=7,
        calendar_close_time_local=time(17, 0, 0),
    )
    zone = _load_bundled_zone("America/New_York")
    naive_open = datetime(2024, 10, 27, 17, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)
    availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry
    )
    elapsed = availability - event_time_utc
    assert elapsed == timedelta(hours=169)
    assert elapsed != timedelta(hours=168)


def test_utc_source_timezone_fixed_and_calendar_derivation_coincide() -> None:
    entry = _entry(
        timeframe=Timeframe.D1,
        timezone="UTC",
        calendar_close_day_offset=1,
        calendar_close_time_local=time(0, 0, 0),
    )
    zone = _load_bundled_zone("UTC")
    naive_open = datetime(2024, 3, 9, 0, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)
    availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry
    )
    assert availability - event_time_utc == timedelta(hours=24)


def test_ambiguous_or_nonexistent_derived_calendar_close_rejected() -> None:
    ambiguous_entry = _entry(
        timeframe=Timeframe.D1,
        timezone="America/New_York",
        calendar_close_day_offset=0,
        calendar_close_time_local=time(1, 30, 0),
    )
    zone = _load_bundled_zone("America/New_York")
    naive_open = datetime(2024, 11, 3, 0, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)
    with pytest.raises(_RowRejected) as ambiguous_exc_info:
        _derive_event_and_availability(
            naive_open, event_time_utc, zone, ambiguous_entry
        )
    assert ambiguous_exc_info.value.reason_code == "AMBIGUOUS_LOCAL_CLOSE"

    nonexistent_entry = _entry(
        timeframe=Timeframe.D1,
        timezone="America/New_York",
        calendar_close_day_offset=0,
        calendar_close_time_local=time(2, 30, 0),
    )
    naive_open_2 = datetime(2024, 3, 10, 0, 0, 0)
    event_time_utc_2 = naive_open_2.replace(tzinfo=zone).astimezone(UTC)
    with pytest.raises(_RowRejected) as nonexistent_exc_info:
        _derive_event_and_availability(
            naive_open_2, event_time_utc_2, zone, nonexistent_entry
        )
    assert nonexistent_exc_info.value.reason_code == "NONEXISTENT_LOCAL_CLOSE"


def test_manifest_timestamp_format_controls_parsing() -> None:
    entry = _entry(timestamp_format="%d/%m/%Y %H:%M")
    manifest = _manifest((entry,))
    text = "TIMESTAMP,OPEN,HIGH,LOW,CLOSE\n15/01/2024 09:30,2000.00,2000.50,1999.50,2000.10\n"
    result = parse_candle_rows(
        decoded_text=text,
        entry=entry,
        manifest=manifest,
        identity_tracker=CandleIdentityCollisionTracker(),
    )
    assert len(result.records) == 1
    assert result.records[0].event_time_utc == datetime(2024, 1, 15, 9, 30, tzinfo=UTC)


def test_row_timezone_offset_is_rejected_when_manifest_timezone_is_used() -> None:
    entry_with_offset_format = _entry(timestamp_format="%Y-%m-%d %H:%M:%S%z")
    with pytest.raises(InvalidDatasetManifestError):
        validate_historical_file_entry(entry_with_offset_format)


def test_d1_session_close_metadata_controls_availability() -> None:
    entry_early_close = _entry(
        timeframe=Timeframe.D1,
        timezone="UTC",
        calendar_close_day_offset=0,
        calendar_close_time_local=time(12, 0, 0),
    )
    entry_late_close = _entry(
        timeframe=Timeframe.D1,
        timezone="UTC",
        calendar_close_day_offset=1,
        calendar_close_time_local=time(0, 0, 0),
    )
    zone = _load_bundled_zone("UTC")
    naive_open = datetime(2024, 1, 15, 0, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)

    early_availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry_early_close
    )
    late_availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry_late_close
    )
    assert early_availability == datetime(2024, 1, 15, 12, 0, tzinfo=UTC)
    assert late_availability == datetime(2024, 1, 16, 0, 0, tzinfo=UTC)
    assert early_availability != late_availability


def test_w1_session_close_metadata_controls_availability() -> None:
    entry_short_week = _entry(
        timeframe=Timeframe.W1,
        timezone="UTC",
        calendar_close_day_offset=3,
        calendar_close_time_local=time(0, 0, 0),
    )
    entry_full_week = _entry(
        timeframe=Timeframe.W1,
        timezone="UTC",
        calendar_close_day_offset=7,
        calendar_close_time_local=time(0, 0, 0),
    )
    zone = _load_bundled_zone("UTC")
    naive_open = datetime(2024, 1, 1, 0, 0, 0)
    event_time_utc = naive_open.replace(tzinfo=zone).astimezone(UTC)

    short_availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry_short_week
    )
    full_availability = _derive_event_and_availability(
        naive_open, event_time_utc, zone, entry_full_week
    )
    assert short_availability == datetime(2024, 1, 4, 0, 0, tzinfo=UTC)
    assert full_availability == datetime(2024, 1, 8, 0, 0, tzinfo=UTC)
    assert short_availability != full_availability
