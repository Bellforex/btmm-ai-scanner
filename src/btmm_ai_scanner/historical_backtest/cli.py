import argparse
from collections.abc import Sequence
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.data_quality import ChecksumMismatchError
from btmm_ai_scanner.historical_backtest.direct_batch_worker import (
    DirectBatchVerificationStatus,
    _run_isolated_direct_batch_verification,
)
from btmm_ai_scanner.historical_backtest.execution import (
    HistoricalBacktestExecutionResult,
    HistoricalBatchExecutionError,
    HistoricalExecutionMode,
    IncrementalReplayAbortedError,
    InsufficientHostMemoryError,
    execute_scanner_backtest,
    execute_scanner_backtest_batch_historical,
    resolve_historical_execution_mode,
)
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.historical_backtest.loader import (
    DatasetManifestNotFoundError,
    LoadedHistoricalDataset,
    load_historical_dataset,
)
from btmm_ai_scanner.historical_backtest.manifest import InvalidDatasetManifestError
from btmm_ai_scanner.historical_backtest.reporting import (
    HistoricalReportWriteError,
    write_backtest_report,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.configuration import (
    InvalidScannerConfigurationError,
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.labels import InvalidReviewedLabelError
from btmm_ai_scanner.structure.configuration import StructureConfiguration

EXIT_SUCCESS = 0
EXIT_UNEXPECTED_FAILURE = 1
EXIT_USAGE_ERROR = 2
EXIT_DATASET_REJECTION = 3
EXIT_REPLAY_FAILURE = 4
EXIT_REVIEWED_CASE_FAILURE = 5
EXIT_REPORT_WRITE_FAILURE = 6
EXIT_UNSAFE_RETENTION_POLICY = 7

_MINIMUM_PRICE_TICK = Decimal("0.01")

_RETENTION_BY_CLI_VALUE = {
    "all": SnapshotRetentionPolicy.ALL,
    "changed-only": SnapshotRetentionPolicy.CHANGED_ONLY,
    "final-only": SnapshotRetentionPolicy.FINAL_ONLY,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btmm_ai_scanner.historical_backtest")
    parser.add_argument("--dataset", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--snapshot-retention",
        choices=tuple(_RETENTION_BY_CLI_VALUE),
        default="final-only",
    )
    return parser


def _default_scanner_configuration() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=_MINIMUM_PRICE_TICK
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=_MINIMUM_PRICE_TICK),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=_MINIMUM_PRICE_TICK),
    )


def _collect_values_by_key(node: object, key: str) -> list[str]:
    """Recursively gather every string value stored under ``key`` anywhere in a
    JSON-decoded snapshot — used to compare identity (``record_id``) and content
    (``content_fingerprint``) sets explicitly, never via a single opaque
    top-level checksum (register §44AN cross-engine verification)."""
    found: list[str] = []
    if isinstance(node, dict):
        for child_key, child_value in node.items():
            if child_key == key and isinstance(child_value, str):
                found.append(child_value)
            else:
                found.extend(_collect_values_by_key(child_value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_collect_values_by_key(item, key))
    return found


def _cross_engine_equality(
    incremental_final_snapshot: ScannerAnalysis,
    worker_snapshot_json: dict[str, object],
) -> tuple[bool, bool, bool]:
    """Explicit semantic / identity / fingerprint equality of the incremental
    engine's final snapshot against the isolated worker's verified snapshot.

    Semantic equality is complete public ``ScannerAnalysis`` equality over the
    existing canonical serialization; identity and fingerprint equality are
    checked separately over the full multisets of record identities and content
    fingerprints, so neither is merely inferred from the other."""
    incremental_json = incremental_final_snapshot.model_dump(mode="json")
    semantic_equal = incremental_json == worker_snapshot_json
    identity_equal = sorted(_collect_values_by_key(incremental_json, "record_id")) == (
        sorted(_collect_values_by_key(worker_snapshot_json, "record_id"))
    )
    fingerprint_equal = sorted(
        _collect_values_by_key(incremental_json, "content_fingerprint")
    ) == sorted(_collect_values_by_key(worker_snapshot_json, "content_fingerprint"))
    return semantic_equal, identity_equal, fingerprint_equal


def _verify_and_publish(
    dataset: LoadedHistoricalDataset,
    result: HistoricalBacktestExecutionResult,
    scanner_configuration: ScannerConfiguration,
    output_root: Path,
) -> int:
    """Isolated-worker verification, cross-engine comparison, and the single
    authoritative publication gate (register §44AN/§44Y).

    A report — and therefore ``checksums.json`` — is published only when every
    symbol's isolated worker returns ``SUCCESS`` and its snapshot matches the
    incremental engine's semantically, by identity, and by fingerprint. Any
    failure returns ``EXIT_REPLAY_FAILURE`` with no report written at all."""
    bundles_by_symbol = dict(dataset.timeframe_inputs_by_symbol)
    direct_batch_elapsed_seconds = 0.0
    direct_batch_peak_working_set_bytes: int | None = None

    for symbol, replay_result in zip(
        result.symbols_processed, result.per_symbol_replay_results, strict=True
    ):
        outcome = _run_isolated_direct_batch_verification(
            bundles_by_symbol[symbol], (), scanner_configuration
        )
        direct_batch_elapsed_seconds += outcome.elapsed_seconds
        if outcome.peak_working_set_bytes is not None:
            direct_batch_peak_working_set_bytes = (
                outcome.peak_working_set_bytes
                if direct_batch_peak_working_set_bytes is None
                else max(
                    direct_batch_peak_working_set_bytes,
                    outcome.peak_working_set_bytes,
                )
            )

        if (
            outcome.status is not DirectBatchVerificationStatus.SUCCESS
            or outcome.final_snapshot_json is None
        ):
            return EXIT_REPLAY_FAILURE

        semantic_equal, identity_equal, fingerprint_equal = _cross_engine_equality(
            replay_result.final_snapshot, outcome.final_snapshot_json
        )
        if not (semantic_equal and identity_equal and fingerprint_equal):
            return EXIT_REPLAY_FAILURE

    publishable_result = result
    if result.performance_metrics is not None:
        publishable_result = result.model_copy(
            update={
                "performance_metrics": result.performance_metrics.model_copy(
                    update={
                        "direct_batch_elapsed_seconds": direct_batch_elapsed_seconds,
                        "direct_batch_peak_working_set_bytes": (
                            direct_batch_peak_working_set_bytes
                        ),
                        "direct_batch_verification_status": (
                            DirectBatchVerificationStatus.SUCCESS.value
                        ),
                    }
                )
            }
        )

    return _write_report_or_fail(publishable_result, output_root)


def _write_report_or_fail(
    result: HistoricalBacktestExecutionResult, output_root: Path
) -> int:
    """The single atomic publication tail shared by both engines: write the
    report (checksums.json is written last, so a partial run leaves no
    success-claiming checksums), mapping write failures to their exit codes."""
    try:
        write_backtest_report(result, output_root)
    except HistoricalReportWriteError:
        return EXIT_REPORT_WRITE_FAILURE
    except Exception:
        return EXIT_UNEXPECTED_FAILURE
    return EXIT_SUCCESS


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)  # argparse itself exits 2 on a usage/parse error

    scanner_configuration = _default_scanner_configuration()
    # Production flow verifies via the isolated worker, never the in-process
    # oracle (register §44AN, Part 6): the incremental replay runs with
    # verify_against_direct_batch off.
    replay_configuration = ReplayConfiguration(
        snapshot_retention=_RETENTION_BY_CLI_VALUE[args.snapshot_retention],
        verify_against_direct_batch=False,
    )
    identity_provider = ContentAddressedIdentityProvider()

    try:
        dataset = load_historical_dataset(
            args.dataset, HistoricalDatasetConfiguration()
        )
    except (
        DatasetManifestNotFoundError,
        InvalidDatasetManifestError,
        ChecksumMismatchError,
    ):
        return EXIT_DATASET_REJECTION
    except Exception:
        return EXIT_UNEXPECTED_FAILURE

    # A6-F6H execution-mode split: FINAL_ONLY historical validation is owned by
    # the authoritative isolated batch worker (fast, the semantic oracle, 120-min
    # ceiling); ALL / CHANGED_ONLY stay on the incremental kernel with its 90-min
    # in-process gate and per-run direct-batch cross-verification. Streaming /
    # forward-test live execution (not exposed by this offline CLI) is always the
    # incremental kernel.
    execution_mode = resolve_historical_execution_mode(
        replay_configuration.snapshot_retention
    )

    if execution_mode is HistoricalExecutionMode.BATCH_HISTORICAL_FINAL_ONLY:
        try:
            result = execute_scanner_backtest_batch_historical(
                dataset, scanner_configuration
            )
        except (
            InsufficientHostMemoryError,
            HistoricalBatchExecutionError,
        ):
            return EXIT_REPLAY_FAILURE
        except InvalidReviewedLabelError:
            return EXIT_REVIEWED_CASE_FAILURE
        except Exception:
            return EXIT_UNEXPECTED_FAILURE
        # Batch IS the authoritative oracle here, so there is no separate
        # cross-engine verification step; the result publishes directly (still
        # atomic — checksums.json is written last, nothing on any failure above).
        return _write_report_or_fail(result, args.output)

    try:
        result = execute_scanner_backtest(
            dataset, scanner_configuration, replay_configuration, identity_provider
        )
    except InvalidScannerConfigurationError:
        return EXIT_UNSAFE_RETENTION_POLICY
    except (InsufficientHostMemoryError, IncrementalReplayAbortedError):
        return EXIT_REPLAY_FAILURE
    except InvalidReviewedLabelError:
        return EXIT_REVIEWED_CASE_FAILURE
    except Exception:
        return EXIT_UNEXPECTED_FAILURE

    return _verify_and_publish(dataset, result, scanner_configuration, args.output)
