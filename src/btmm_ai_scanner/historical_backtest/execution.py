from datetime import UTC, datetime
from time import perf_counter
from uuid import UUID, uuid4

from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.domain.analyzer import DerivedOutputIdentityProvider
from btmm_ai_scanner.historical_backtest import process_metrics
from btmm_ai_scanner.historical_backtest.data_quality import HistoricalDataQualityReport
from btmm_ai_scanner.historical_backtest.enums import BacktestQualityGateStatus
from btmm_ai_scanner.historical_backtest.loader import LoadedHistoricalDataset
from btmm_ai_scanner.scanner.configuration import (
    InvalidScannerConfigurationError,
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.evaluation import ScannerBacktestReport, evaluate_scanner
from btmm_ai_scanner.scanner.replay import ScannerReplayResult, run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput

_SYMBOL_ORDER: dict[InternalSymbol, int] = {
    InternalSymbol.XAUUSD: 1,
    InternalSymbol.EURUSD: 2,
    InternalSymbol.GBPUSD: 3,
}

# Run-level safety gates (register §44AF/§44AM, AUTHOR-APPROVED).
_HOST_MEMORY_FLOOR_BYTES = 4 * 1024**3
_UNSAFE_RETENTION_GROUP_CAP = 250
_BOUNDED_RETENTION_POLICIES = frozenset(
    {SnapshotRetentionPolicy.ALL, SnapshotRetentionPolicy.CHANGED_ONLY}
)


class InsufficientHostMemoryError(Exception):
    """Raised before any expensive replay/verification work when the host's
    available physical RAM is below the 4 GB run-level floor (register §44Z/
    §44AF). A run that trips this gate publishes no report and no checksums —
    exactly the exhaustion path the isolated worker and this floor exist to
    prevent."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class HistoricalPerformanceMetrics(ContractModel):
    """Operational metadata for one historical execution (register §44AO).

    Every field is observational only and never participates in any scanner
    semantic identity, content fingerprint, or deterministic detection output
    (§44Z cross-cutting rule). The ``direct_batch_*`` fields are populated by the
    CLI after the isolated worker runs; at the pure execution layer (which does
    no subprocess work) they remain ``None``."""

    processed_availability_group_count: int
    replay_elapsed_seconds: float
    peak_working_set_bytes: int | None
    minimum_available_system_ram_bytes: int | None
    retained_snapshot_count: int
    final_replay_result_bytes: int
    direct_batch_elapsed_seconds: float | None = None
    direct_batch_peak_working_set_bytes: int | None = None
    direct_batch_verification_status: str | None = None
    metrics_platform: str


class HistoricalBacktestExecutionResult(ContractModel):
    dataset_id: str
    dataset_version: str
    execution_id: UUID
    started_at_utc: datetime
    completed_at_utc: datetime
    symbols_processed: tuple[InternalSymbol, ...]
    per_symbol_replay_results: tuple[ScannerReplayResult, ...]
    per_symbol_backtest_reports: tuple[ScannerBacktestReport | None, ...]
    data_quality_report: HistoricalDataQualityReport
    insufficient_history_case_ids: tuple[str, ...]
    quality_gate_status: BacktestQualityGateStatus
    output_paths: tuple[str, ...]
    warnings: tuple[str, ...]
    production_status: str
    performance_metrics: HistoricalPerformanceMetrics | None = None


def _insufficient_history_case_ids(dataset: LoadedHistoricalDataset) -> tuple[str, ...]:
    coverage_by_key = {
        (coverage.symbol, coverage.timeframe): coverage
        for coverage in dataset.data_quality_report.timeframe_coverage
    }
    flagged: list[str] = []
    for case in dataset.reviewed_cases:
        for timeframe in case.required_timeframes:
            coverage = coverage_by_key.get((case.symbol, timeframe))
            if coverage is None or not coverage.meets_warm_up_floor:
                flagged.append(case.case_id)
                break
    return tuple(flagged)


def availability_group_count(bundles: tuple[ScannerTimeframeInput, ...]) -> int:
    """Number of distinct availability-group times across every candle in a
    symbol's bundles — the exact quantity the §44AM retention cap bounds."""
    group_times = {
        candle.availability_time_utc for bundle in bundles for candle in bundle.candles
    }
    return len(group_times)


def _enforce_host_memory_floor() -> int | None:
    """Sample available host RAM and abort the run if it is below the 4 GB floor
    (register §44Z/§44AF). Returns the sampled value (or ``None`` if the platform
    cannot measure it — in which case the gate cannot fire and the run proceeds,
    consistent with the nullable-never-raises metrics contract)."""
    available = process_metrics.available_system_ram_bytes()
    if available is not None and available < _HOST_MEMORY_FLOOR_BYTES:
        raise InsufficientHostMemoryError(
            "available host RAM "
            f"{available} bytes is below the {_HOST_MEMORY_FLOOR_BYTES}-byte "
            "run-level floor; aborting before replay, publishing nothing."
        )
    return available


def _enforce_retention_safety_cap(
    ordered_symbols: list[InternalSymbol],
    bundles_by_symbol: dict[InternalSymbol, tuple[ScannerTimeframeInput, ...]],
    replay_configuration: ReplayConfiguration,
) -> None:
    """Reject an unbounded retention policy above the exact 250-group cap before
    any replay begins (register §44AM). Raises the existing
    ``InvalidScannerConfigurationError`` — no new exception type — leaving the
    general ``run_scanner_replay`` API's own defaults untouched (§44AM: the cap
    is a historical-backtest business rule only)."""
    if replay_configuration.snapshot_retention not in _BOUNDED_RETENTION_POLICIES:
        return
    for symbol in ordered_symbols:
        group_count = availability_group_count(bundles_by_symbol[symbol])
        if group_count > _UNSAFE_RETENTION_GROUP_CAP:
            raise InvalidScannerConfigurationError(
                "snapshot_retention "
                f"{replay_configuration.snapshot_retention.value} is not permitted "
                f"for symbol {symbol.value}: {group_count} availability groups "
                f"exceeds the historical safety cap of "
                f"{_UNSAFE_RETENTION_GROUP_CAP}."
            )


def execute_scanner_backtest(
    dataset: LoadedHistoricalDataset,
    scanner_configuration: ScannerConfiguration,
    replay_configuration: ReplayConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> HistoricalBacktestExecutionResult:
    started_at_utc = datetime.now(UTC)

    symbols_processed: list[InternalSymbol] = []
    replay_results: list[ScannerReplayResult] = []
    backtest_reports: list[ScannerBacktestReport | None] = []
    warnings: list[str] = []

    ordered_symbols = sorted(
        (symbol for symbol, _ in dataset.timeframe_inputs_by_symbol),
        key=lambda s: _SYMBOL_ORDER[s],
    )
    bundles_by_symbol = dict(dataset.timeframe_inputs_by_symbol)

    # Run-level safety gates, both before any expensive replay work (§44AF).
    minimum_available_ram = _enforce_host_memory_floor()
    _enforce_retention_safety_cap(
        ordered_symbols, bundles_by_symbol, replay_configuration
    )

    processed_group_count = 0
    retained_snapshot_count = 0
    final_replay_result_bytes = 0
    replay_elapsed_seconds = 0.0

    for symbol in ordered_symbols:
        bundles = bundles_by_symbol[symbol]
        processed_group_count += availability_group_count(bundles)

        replay_start = perf_counter()
        replay_result = run_scanner_replay(
            bundles,
            (),
            scanner_configuration,
            replay_configuration,
            identity_provider,
        )
        replay_elapsed_seconds += perf_counter() - replay_start

        symbols_processed.append(symbol)
        replay_results.append(replay_result)
        retained_snapshot_count += len(replay_result.snapshots)
        final_replay_result_bytes += len(
            replay_result.final_snapshot.model_dump_json().encode("utf-8")
        )

        sampled_ram = process_metrics.available_system_ram_bytes()
        if sampled_ram is not None:
            minimum_available_ram = (
                sampled_ram
                if minimum_available_ram is None
                else min(minimum_available_ram, sampled_ram)
            )

        symbol_cases = tuple(
            case for case in dataset.reviewed_cases if case.symbol == symbol
        )
        if len(symbol_cases) == 0:
            backtest_reports.append(None)
        else:
            backtest_reports.append(evaluate_scanner(replay_result, symbol_cases))

        # Only an explicitly requested in-process equivalence check can fail here;
        # the production flow verifies via the isolated worker (verify off), so a
        # not-requested check never counts as a mismatch (register §44Y/§44AN).
        if replay_configuration.verify_against_direct_batch and (
            not replay_result.direct_batch_verified
            or len(replay_result.detection_mismatches) > 0
        ):
            warnings.append(
                f"replay/direct-batch equivalence failed for symbol {symbol.value}."
            )

    quality_gate_status = (
        BacktestQualityGateStatus.PASSED
        if dataset.data_quality_report.checksum_verified and len(warnings) == 0
        else BacktestQualityGateStatus.FAILED
    )

    performance_metrics = HistoricalPerformanceMetrics(
        processed_availability_group_count=processed_group_count,
        replay_elapsed_seconds=replay_elapsed_seconds,
        peak_working_set_bytes=process_metrics.peak_working_set_bytes(),
        minimum_available_system_ram_bytes=minimum_available_ram,
        retained_snapshot_count=retained_snapshot_count,
        final_replay_result_bytes=final_replay_result_bytes,
        metrics_platform=process_metrics.metrics_platform(),
    )

    return HistoricalBacktestExecutionResult(
        dataset_id=dataset.manifest.dataset_id,
        dataset_version=dataset.manifest.dataset_version,
        execution_id=uuid4(),
        started_at_utc=started_at_utc,
        completed_at_utc=datetime.now(UTC),
        symbols_processed=tuple(symbols_processed),
        per_symbol_replay_results=tuple(replay_results),
        per_symbol_backtest_reports=tuple(backtest_reports),
        data_quality_report=dataset.data_quality_report,
        insufficient_history_case_ids=_insufficient_history_case_ids(dataset),
        quality_gate_status=quality_gate_status,
        output_paths=(),
        warnings=tuple(warnings),
        production_status="NOT_PRODUCTION_APPROVED",
        performance_metrics=performance_metrics,
    )
