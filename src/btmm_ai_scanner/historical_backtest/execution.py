import json
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from time import monotonic, perf_counter
from uuid import UUID, uuid4

from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.domain.analyzer import DerivedOutputIdentityProvider
from btmm_ai_scanner.historical_backtest import process_metrics
from btmm_ai_scanner.historical_backtest.data_quality import HistoricalDataQualityReport
from btmm_ai_scanner.historical_backtest.direct_batch_worker import (
    DirectBatchVerificationStatus,
    _run_isolated_direct_batch_verification,
)
from btmm_ai_scanner.historical_backtest.enums import BacktestQualityGateStatus
from btmm_ai_scanner.historical_backtest.loader import LoadedHistoricalDataset
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.configuration import (
    InvalidScannerConfigurationError,
    ReplayConfiguration,
    ScannerConfiguration,
    canonical_minimum_price_tick,
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
# Matches the isolated worker's 90-minute ceiling (§44AN/§44AF); enforced here
# on the in-process incremental replay, which the worker gate never covered.
_INCREMENTAL_REPLAY_TIMEOUT_SECONDS = 5400.0
_BOUNDED_RETENTION_POLICIES = frozenset(
    {SnapshotRetentionPolicy.ALL, SnapshotRetentionPolicy.CHANGED_ONLY}
)

# A6-F6H EMPIRICALLY-CALIBRATED offline historical ceiling. The former 90-minute
# gate was AUTHOR-APPROVED + ENGINEERING-PROVISIONAL and assumed a near-linear
# replay architecture; the decisive synthetic N=18,474 batch experiment measured
# 100.71 min / 647.3 MB, proving BOTH historical engines are super-linear. The
# ceiling is therefore superseded (not "wrong" — provisional and empirically
# recalibrated) by 120 minutes, and applies ONLY to the authoritative batch
# HISTORICAL_FINAL_ONLY path. The incremental streaming path keeps its 90-minute
# in-process gate. Memory ceiling stays 6 GB; the 4 GB host floor is unchanged.
_HISTORICAL_FINAL_ONLY_TIMEOUT_SECONDS = 7200.0
_HISTORICAL_WORKER_MEMORY_CEILING_BYTES = 6 * 1024**3


class HistoricalExecutionMode(Enum):
    """A6-F6H: which engine owns a historical backtest run.

    FINAL_ONLY historical validation is the authoritative BATCH ``scan_market``
    path (the independent semantic oracle, run in the isolated worker under the
    120-minute EMPIRICALLY-CALIBRATED ceiling). Every other mode -- ALL and
    CHANGED_ONLY snapshot retention, and by extension streaming / forward-test /
    debug per-prefix replay -- is owned by the ``IncrementalReplayKernel``. Batch
    execution never substitutes for streaming behaviour."""

    BATCH_HISTORICAL_FINAL_ONLY = "batch_historical_final_only"
    INCREMENTAL_STREAMING = "incremental_streaming"


def resolve_historical_execution_mode(
    snapshot_retention: SnapshotRetentionPolicy,
) -> HistoricalExecutionMode:
    """Route a snapshot-retention policy to its owning engine (the A6-F6H
    responsibility split). Pure and total over the policy enum."""
    if snapshot_retention == SnapshotRetentionPolicy.FINAL_ONLY:
        return HistoricalExecutionMode.BATCH_HISTORICAL_FINAL_ONLY
    return HistoricalExecutionMode.INCREMENTAL_STREAMING


class InsufficientHostMemoryError(Exception):
    """Raised before any expensive replay/verification work when the host's
    available physical RAM is below the 4 GB run-level floor (register §44Z/
    §44AF). A run that trips this gate publishes no report and no checksums —
    exactly the exhaustion path the isolated worker and this floor exist to
    prevent."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class HistoricalBatchExecutionError(Exception):
    """Raised when the authoritative isolated batch worker for a
    HISTORICAL_FINAL_ONLY run returns any non-SUCCESS status (timeout, memory
    ceiling, crash, corrupt response) for any symbol (A6-F6H). Like the host-
    floor and incremental-abort gates, a run that trips it publishes no report
    and no checksums — the atomic-publication contract is unchanged; only the
    authoritative engine differs."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class IncrementalReplayAbortedError(Exception):
    """Raised from the per-group replay gate when the in-process incremental
    replay exceeds the 90-minute runtime ceiling or drops the host below the
    4 GB available-RAM floor mid-run (register §44AF). The audit found the
    isolated worker had a 90-minute gate but the incremental replay itself did
    not; this closes that gap so a genuine attempt cannot run indefinitely. A
    run that trips it publishes no report and no checksums."""

    def __init__(self, message: str) -> None:
        super().__init__(message)


class _IncrementalReplayGate:
    """Per-availability-group cooperative abort boundary for the in-process
    incremental replay. ``run_scanner_replay`` invokes ``__call__`` once before
    each group; it samples the monotonic clock and host RAM (via the shared
    ``process_metrics`` collector) and raises ``IncrementalReplayAbortedError``
    the moment the runtime ceiling or host-RAM floor is breached. It also tracks
    the minimum available RAM observed during the replay — operational metadata
    only, never part of any scanner identity/fingerprint (§44Z)."""

    def __init__(
        self,
        timeout_seconds: float = _INCREMENTAL_REPLAY_TIMEOUT_SECONDS,
        host_memory_floor_bytes: int = _HOST_MEMORY_FLOOR_BYTES,
    ) -> None:
        self._deadline = monotonic() + timeout_seconds
        self._floor = host_memory_floor_bytes
        self.minimum_available_ram_bytes = process_metrics.available_system_ram_bytes()

    def __call__(self) -> None:
        available = process_metrics.available_system_ram_bytes()
        if available is not None:
            self.minimum_available_ram_bytes = (
                available
                if self.minimum_available_ram_bytes is None
                else min(self.minimum_available_ram_bytes, available)
            )
            if available < self._floor:
                raise IncrementalReplayAbortedError(
                    f"available host RAM {available} bytes fell below the "
                    f"{self._floor}-byte floor during incremental replay; "
                    "aborting with no report."
                )
        if monotonic() > self._deadline:
            raise IncrementalReplayAbortedError(
                "incremental replay exceeded the "
                f"{_INCREMENTAL_REPLAY_TIMEOUT_SECONDS}-second runtime ceiling; "
                "aborting with no report."
            )


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

    # Pre-replay run-level gate + retention cap (§44AF), before any expensive
    # work. The per-group gate below then enforces the same 4 GB floor plus the
    # 90-minute runtime ceiling *during* the replay itself.
    _enforce_host_memory_floor()
    _enforce_retention_safety_cap(
        ordered_symbols, bundles_by_symbol, replay_configuration
    )
    replay_gate = _IncrementalReplayGate()

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
            group_gate=replay_gate,
        )
        replay_elapsed_seconds += perf_counter() - replay_start

        symbols_processed.append(symbol)
        replay_results.append(replay_result)
        retained_snapshot_count += len(replay_result.snapshots)
        final_replay_result_bytes += len(
            replay_result.final_snapshot.model_dump_json().encode("utf-8")
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
        minimum_available_system_ram_bytes=replay_gate.minimum_available_ram_bytes,
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


def _reconstruct_batch_replay_result(
    analysis: ScannerAnalysis,
    minimum_price_tick: Decimal,
) -> ScannerReplayResult:
    """Wrap the authoritative batch ``ScannerAnalysis`` (from the isolated
    worker) in a ``ScannerReplayResult`` shaped exactly as the FINAL_ONLY
    incremental path would publish it: one retained snapshot that is also the
    final snapshot, no detection mismatches (batch IS the direct-batch oracle,
    so ``direct_batch_verified`` is True), and the version/classification fields
    carried verbatim from the analysis. Byte-identical content to the
    incremental FINAL_ONLY result (proven by the permanent every-prefix batch↔
    replay equivalence suite)."""
    return ScannerReplayResult(
        symbol=analysis.symbol,
        snapshots=(analysis,),
        final_snapshot=analysis,
        detection_mismatches=(),
        direct_batch_verified=True,
        minimum_price_tick=minimum_price_tick,
        availability_time_utc=analysis.availability_time_utc,
        evidence_classification=analysis.evidence_classification,
        rule_version=analysis.rule_version,
        contract_version=analysis.contract_version,
        schema_version=analysis.schema_version,
    )


def execute_scanner_backtest_batch_historical(
    dataset: LoadedHistoricalDataset,
    scanner_configuration: ScannerConfiguration,
) -> HistoricalBacktestExecutionResult:
    """A6-F6H authoritative HISTORICAL_FINAL_ONLY execution: run the unmodified
    batch ``scan_market`` oracle for each symbol inside the isolated direct-batch
    worker (120-minute EMPIRICALLY-CALIBRATED timeout, 6 GB working-set ceiling),
    and build the execution result from the worker's verified snapshots. The
    incremental kernel is NOT run on this path -- that is the whole point of the
    split: batch is faster for the one-shot historical job.

    Safety is unchanged: the 4 GB host floor is enforced before any work, and any
    non-SUCCESS worker outcome raises ``HistoricalBatchExecutionError`` so the
    caller publishes no report and no checksums (atomic-publication contract).
    ``_run_isolated_direct_batch_verification`` is referenced as a module global
    so tests can substitute a deterministic synthetic worker."""
    started_at_utc = datetime.now(UTC)
    _enforce_host_memory_floor()

    ordered_symbols = sorted(
        (symbol for symbol, _ in dataset.timeframe_inputs_by_symbol),
        key=lambda s: _SYMBOL_ORDER[s],
    )
    bundles_by_symbol = dict(dataset.timeframe_inputs_by_symbol)
    minimum_price_tick = canonical_minimum_price_tick(scanner_configuration)

    symbols_processed: list[InternalSymbol] = []
    replay_results: list[ScannerReplayResult] = []
    backtest_reports: list[ScannerBacktestReport | None] = []
    processed_group_count = 0
    retained_snapshot_count = 0
    final_replay_result_bytes = 0
    worker_elapsed_seconds = 0.0
    worker_peak_working_set_bytes: int | None = None

    for symbol in ordered_symbols:
        bundles = bundles_by_symbol[symbol]
        processed_group_count += availability_group_count(bundles)

        outcome = _run_isolated_direct_batch_verification(
            bundles,
            (),
            scanner_configuration,
            _HISTORICAL_FINAL_ONLY_TIMEOUT_SECONDS,
            _HISTORICAL_WORKER_MEMORY_CEILING_BYTES,
        )
        worker_elapsed_seconds += outcome.elapsed_seconds
        if outcome.peak_working_set_bytes is not None:
            worker_peak_working_set_bytes = (
                outcome.peak_working_set_bytes
                if worker_peak_working_set_bytes is None
                else max(worker_peak_working_set_bytes, outcome.peak_working_set_bytes)
            )

        if (
            outcome.status is not DirectBatchVerificationStatus.SUCCESS
            or outcome.final_snapshot_json is None
        ):
            raise HistoricalBatchExecutionError(
                "authoritative batch historical worker returned "
                f"{outcome.status.value} for symbol {symbol.value}; "
                "aborting with no report."
            )

        # The worker returns a JSON-mode dump (lists / ISO strings / enum values);
        # round-trip through JSON so the strict contract models coerce back to
        # their exact tuple / datetime / enum types.
        analysis = ScannerAnalysis.model_validate_json(
            json.dumps(outcome.final_snapshot_json)
        )
        replay_result = _reconstruct_batch_replay_result(analysis, minimum_price_tick)

        symbols_processed.append(symbol)
        replay_results.append(replay_result)
        retained_snapshot_count += len(replay_result.snapshots)
        final_replay_result_bytes += len(
            replay_result.final_snapshot.model_dump_json().encode("utf-8")
        )

        symbol_cases = tuple(
            case for case in dataset.reviewed_cases if case.symbol == symbol
        )
        backtest_reports.append(
            None
            if len(symbol_cases) == 0
            else evaluate_scanner(replay_result, symbol_cases)
        )

    quality_gate_status = (
        BacktestQualityGateStatus.PASSED
        if dataset.data_quality_report.checksum_verified
        else BacktestQualityGateStatus.FAILED
    )

    performance_metrics = HistoricalPerformanceMetrics(
        processed_availability_group_count=processed_group_count,
        replay_elapsed_seconds=worker_elapsed_seconds,
        peak_working_set_bytes=process_metrics.peak_working_set_bytes(),
        minimum_available_system_ram_bytes=process_metrics.available_system_ram_bytes(),
        retained_snapshot_count=retained_snapshot_count,
        final_replay_result_bytes=final_replay_result_bytes,
        metrics_platform=process_metrics.metrics_platform(),
        direct_batch_elapsed_seconds=worker_elapsed_seconds,
        direct_batch_peak_working_set_bytes=worker_peak_working_set_bytes,
        direct_batch_verification_status=(DirectBatchVerificationStatus.SUCCESS.value),
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
        warnings=(),
        production_status="NOT_PRODUCTION_APPROVED",
        performance_metrics=performance_metrics,
    )
