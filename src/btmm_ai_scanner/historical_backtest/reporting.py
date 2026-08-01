import hashlib
import json
import os
from importlib.metadata import version as _package_version
from pathlib import Path

from btmm_ai_scanner.contracts.types import ContractModel, SHA256Fingerprint
from btmm_ai_scanner.historical_backtest.execution import (
    HistoricalBacktestExecutionResult,
)

_INDENT = 2


class HistoricalReportWriteError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)


class ReportWriteResult(ContractModel):
    execution_directory: str
    written_file_paths: tuple[str, ...]
    file_checksums: tuple[tuple[str, SHA256Fingerprint], ...]


def _write_json_file(payload: object, final_path: Path) -> str:
    text = json.dumps(payload, indent=_INDENT, ensure_ascii=False) + "\n"
    tmp_path = final_path.with_name(
        final_path.name + f".tmp-{os.getpid()}-{id(payload)}"
    )
    try:
        with tmp_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, final_path)
    except OSError as exc:
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except OSError:
            pass
        raise HistoricalReportWriteError(
            f"failed to write {final_path}: {exc}"
        ) from exc

    directory_fd = None
    try:
        directory_fd = os.open(final_path.parent, os.O_RDONLY)
        os.fsync(directory_fd)
    except OSError:
        pass
    finally:
        if directory_fd is not None:
            os.close(directory_fd)

    return hashlib.sha256(final_path.read_bytes()).hexdigest()


def write_backtest_report(
    result: HistoricalBacktestExecutionResult,
    output_root: Path,
) -> ReportWriteResult:
    execution_directory = output_root / result.dataset_id / str(result.execution_id)
    if execution_directory.exists():
        raise HistoricalReportWriteError(
            f"execution directory already exists: {execution_directory}."
        )

    try:
        execution_directory.mkdir(parents=True)
    except OSError as exc:
        raise HistoricalReportWriteError(
            f"failed to create execution directory {execution_directory}: {exc}"
        ) from exc

    written_file_paths: list[str] = []
    checksums: list[tuple[str, str]] = []

    try:
        manifest_echo_path = execution_directory / "manifest_echo.json"
        _write_json_file(
            {
                "dataset_id": result.dataset_id,
                "dataset_version": result.dataset_version,
            },
            manifest_echo_path,
        )
        written_file_paths.append(manifest_echo_path.name)

        data_quality_path = execution_directory / "data_quality_report.json"
        _write_json_file(
            result.data_quality_report.model_dump(mode="json"), data_quality_path
        )
        written_file_paths.append(data_quality_path.name)

        for symbol, replay_result in zip(
            result.symbols_processed, result.per_symbol_replay_results, strict=True
        ):
            replay_path = execution_directory / f"replay_result_{symbol.value}.json"
            _write_json_file(replay_result.model_dump(mode="json"), replay_path)
            written_file_paths.append(replay_path.name)

        for symbol, backtest_report in zip(
            result.symbols_processed, result.per_symbol_backtest_reports, strict=True
        ):
            if backtest_report is None:
                continue
            report_path = execution_directory / f"backtest_report_{symbol.value}.json"
            _write_json_file(backtest_report.model_dump(mode="json"), report_path)
            written_file_paths.append(report_path.name)

        execution_summary_payload = result.model_dump(mode="json")
        execution_summary_payload["tzdata_version"] = _package_version("tzdata")
        execution_summary_path = execution_directory / "execution_summary.json"
        _write_json_file(execution_summary_payload, execution_summary_path)
        written_file_paths.append(execution_summary_path.name)

        for file_name in written_file_paths:
            file_path = execution_directory / file_name
            checksums.append(
                (file_name, hashlib.sha256(file_path.read_bytes()).hexdigest())
            )

        checksums_payload = {
            "schema_version": "0.1.0",
            "dataset_id": result.dataset_id,
            "dataset_version": result.dataset_version,
            "execution_id": str(result.execution_id),
            "files": sorted(checksums, key=lambda pair: pair[0]),
        }
        checksums_path = execution_directory / "checksums.json"
        _write_json_file(checksums_payload, checksums_path)
    except HistoricalReportWriteError:
        for file_name in written_file_paths:
            try:
                (execution_directory / file_name).unlink()
            except OSError:
                pass
        try:
            execution_directory.rmdir()
        except OSError:
            pass
        raise

    return ReportWriteResult(
        execution_directory=str(execution_directory),
        written_file_paths=tuple(written_file_paths),
        file_checksums=tuple(sorted(checksums, key=lambda pair: pair[0])),
    )
