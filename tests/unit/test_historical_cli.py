import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.raw_candle import CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.historical_backtest import cli as cli_module
from btmm_ai_scanner.historical_backtest import (
    process_metrics as process_metrics_module,
)
from btmm_ai_scanner.historical_backtest.cli import (
    EXIT_DATASET_REJECTION,
    EXIT_REPLAY_FAILURE,
    EXIT_SUCCESS,
    EXIT_UNSAFE_RETENTION_POLICY,
    main,
)
from btmm_ai_scanner.historical_backtest.direct_batch_worker import (
    DirectBatchVerificationStatus,
    _DirectBatchVerificationOutcome,
)
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

_TIMEFRAME_STEP = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
}


def _build_valid_dataset(root: Path) -> None:
    file_entries = []
    for timeframe, step in _TIMEFRAME_STEP.items():
        rows = ["TIMESTAMP,OPEN,HIGH,LOW,CLOSE"]
        base = datetime(2024, 1, 15, 0, 0, 0)
        price = 2000.0
        for i in range(3):
            ts = base + step * i
            rows.append(
                f"{ts:%Y-%m-%d %H:%M:%S},{price:.2f},{price + 0.5:.2f},{price - 0.5:.2f},{price + 0.1:.2f}"
            )
            price += 0.1
        text = "\n".join(rows) + "\n"
        relative_path = f"xauusd_{timeframe.value.lower()}.csv"
        (root / relative_path).write_bytes(text.encode("utf-8"))
        sha256 = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
        file_entries.append(
            HistoricalFileEntry.model_validate(
                {
                    "relative_path": relative_path,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": timeframe,
                    "format": HistoricalFileFormat.CSV_CANONICAL_V1,
                    "header_mapping": _MANDATORY_MAPPING,
                    "timestamp_semantics": CandleTimestampConvention.CANDLE_OPEN_TIME,
                    "timestamp_format": "%Y-%m-%d %H:%M:%S",
                    "calendar_close_day_offset": None,
                    "calendar_close_time_local": None,
                    "timezone": "UTC",
                    "expected_start": datetime(2024, 1, 1, tzinfo=UTC),
                    "expected_end": datetime(2024, 1, 20, tzinfo=UTC),
                    "expected_row_count": 3,
                    "sha256": sha256,
                    "volume_available": False,
                    "complete_candles_only": True,
                }
            )
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
            "timeframes": tuple(_TIMEFRAME_STEP),
            "file_entries": tuple(file_entries),
            "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
            "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
            "volume_convention": CandleVolumeKind.TICK,
            "reviewed_case_file": None,
            "reviewed_case_sha256": None,
            "notes": "",
            "schema_version": SemVer.parse("0.1.0"),
        }
    )
    (root / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))


def test_cli_exit_code_zero_on_success(tmp_path: Path) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    output_root = tmp_path / "output"

    exit_code = main(["--dataset", str(dataset_root), "--output", str(output_root)])
    assert exit_code == EXIT_SUCCESS


def test_cli_exit_code_precedence_uses_earliest_failing_pipeline_stage(
    tmp_path: Path,
) -> None:
    empty_dataset_root = tmp_path / "empty_dataset"
    empty_dataset_root.mkdir()
    output_root = tmp_path / "output"

    exit_code = main(
        ["--dataset", str(empty_dataset_root), "--output", str(output_root)]
    )
    assert exit_code == EXIT_DATASET_REJECTION


def test_cli_has_no_interactive_prompts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    output_root = tmp_path / "output"

    def _forbidden_input(*args: object, **kwargs: object) -> str:
        raise AssertionError("CLI must never prompt interactively.")

    monkeypatch.setattr("builtins.input", _forbidden_input)
    exit_code = main(["--dataset", str(dataset_root), "--output", str(output_root)])
    assert exit_code == EXIT_SUCCESS


def _build_large_m1_dataset(root: Path, m1_rows: int) -> None:
    """Valid dataset whose M1 series alone exceeds the 250 availability-group
    safety cap; M5/M15 carry a few rows so the manifest shape matches the
    accepted fixture."""
    file_entries = []
    counts = {Timeframe.M1: m1_rows, Timeframe.M5: 3, Timeframe.M15: 3}
    for timeframe, step in _TIMEFRAME_STEP.items():
        rows = ["TIMESTAMP,OPEN,HIGH,LOW,CLOSE"]
        base = datetime(2024, 1, 15, 0, 0, 0)
        price = 2000.0
        for i in range(counts[timeframe]):
            ts = base + step * i
            rows.append(
                f"{ts:%Y-%m-%d %H:%M:%S},{price:.2f},{price + 0.5:.2f},"
                f"{price - 0.5:.2f},{price + 0.1:.2f}"
            )
            price += 0.1
        text = "\n".join(rows) + "\n"
        relative_path = f"xauusd_{timeframe.value.lower()}.csv"
        (root / relative_path).write_bytes(text.encode("utf-8"))
        sha256 = hashlib.sha256((root / relative_path).read_bytes()).hexdigest()
        file_entries.append(
            HistoricalFileEntry.model_validate(
                {
                    "relative_path": relative_path,
                    "symbol": InternalSymbol.XAUUSD,
                    "timeframe": timeframe,
                    "format": HistoricalFileFormat.CSV_CANONICAL_V1,
                    "header_mapping": _MANDATORY_MAPPING,
                    "timestamp_semantics": CandleTimestampConvention.CANDLE_OPEN_TIME,
                    "timestamp_format": "%Y-%m-%d %H:%M:%S",
                    "calendar_close_day_offset": None,
                    "calendar_close_time_local": None,
                    "timezone": "UTC",
                    "expected_start": datetime(2024, 1, 1, tzinfo=UTC),
                    "expected_end": datetime(2024, 2, 1, tzinfo=UTC),
                    "expected_row_count": counts[timeframe],
                    "sha256": sha256,
                    "volume_available": False,
                    "complete_candles_only": True,
                }
            )
        )
    manifest = DatasetManifest.model_validate(
        {
            "dataset_id": "dataset-1",
            "dataset_version": "1.0.0",
            "provider": "FXCM",
            "source_description": "unit-test fixture",
            "source_timezone": "UTC",
            "created_at_utc": datetime(2024, 2, 1, tzinfo=UTC),
            "partition": DatasetPartition.DEVELOPMENT,
            "symbols": (InternalSymbol.XAUUSD,),
            "timeframes": tuple(_TIMEFRAME_STEP),
            "file_entries": tuple(file_entries),
            "timestamp_convention": CandleTimestampConvention.CANDLE_OPEN_TIME,
            "candle_completeness_convention": CandleCompletenessConvention.ALL_ROWS_CONFIRMED_COMPLETE,
            "volume_convention": CandleVolumeKind.TICK,
            "reviewed_case_file": None,
            "reviewed_case_sha256": None,
            "notes": "",
            "schema_version": SemVer.parse("0.1.0"),
        }
    )
    (root / "manifest.json").write_bytes(manifest.model_dump_json().encode("utf-8"))


def test_cli_accepts_snapshot_retention_flag_with_all_three_values(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    for value in ("final-only", "all", "changed-only"):
        output_root = tmp_path / f"output-{value}"
        exit_code = main(
            [
                "--dataset",
                str(dataset_root),
                "--output",
                str(output_root),
                "--snapshot-retention",
                value,
            ]
        )
        assert exit_code == EXIT_SUCCESS, value
        assert list(output_root.rglob("checksums.json"))


def test_cli_rejects_invalid_snapshot_retention_value_with_usage_error(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    with pytest.raises(SystemExit) as excinfo:
        main(
            [
                "--dataset",
                str(dataset_root),
                "--output",
                str(tmp_path / "output"),
                "--snapshot-retention",
                "bogus",
            ]
        )
    assert excinfo.value.code == 2


def test_cli_rejects_unsafe_retention_policy_above_the_safety_cap(
    tmp_path: Path,
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_large_m1_dataset(dataset_root, m1_rows=251)
    output_root = tmp_path / "output"
    exit_code = main(
        [
            "--dataset",
            str(dataset_root),
            "--output",
            str(output_root),
            "--snapshot-retention",
            "all",
        ]
    )
    assert exit_code == EXIT_UNSAFE_RETENTION_POLICY
    # Rejected before replay: nothing verified, nothing published.
    assert not list(output_root.rglob("checksums.json"))


def test_cli_blocks_run_when_host_ram_below_floor_and_publishes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    output_root = tmp_path / "output"
    monkeypatch.setattr(
        process_metrics_module, "available_system_ram_bytes", lambda: 3 * 1024**3
    )
    exit_code = main(["--dataset", str(dataset_root), "--output", str(output_root)])
    assert exit_code == EXIT_REPLAY_FAILURE
    assert not list(output_root.rglob("checksums.json"))


def test_cli_denies_publication_when_worker_verification_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    output_root = tmp_path / "output"

    def _crashed(*args: object, **kwargs: object) -> _DirectBatchVerificationOutcome:
        return _DirectBatchVerificationOutcome(
            status=DirectBatchVerificationStatus.CRASHED,
            final_snapshot_json=None,
            checksum=None,
            elapsed_seconds=0.0,
            peak_working_set_bytes=None,
            preserved_log_path=None,
        )

    monkeypatch.setattr(cli_module, "_run_isolated_direct_batch_verification", _crashed)
    exit_code = main(["--dataset", str(dataset_root), "--output", str(output_root)])
    assert exit_code == EXIT_REPLAY_FAILURE
    assert not list(output_root.rglob("checksums.json"))


def test_cli_denies_publication_on_cross_engine_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dataset_root = tmp_path / "dataset"
    dataset_root.mkdir()
    _build_valid_dataset(dataset_root)
    output_root = tmp_path / "output"
    # Worker succeeds, but the incremental snapshot disagrees semantically.
    monkeypatch.setattr(
        cli_module,
        "_cross_engine_equality",
        lambda incremental, worker_json: (False, True, True),
    )
    exit_code = main(["--dataset", str(dataset_root), "--output", str(output_root)])
    assert exit_code == EXIT_REPLAY_FAILURE
    assert not list(output_root.rglob("checksums.json"))
