from datetime import UTC, datetime
from uuid import UUID, uuid4

from btmm_ai_scanner.config.enums import InternalSymbol
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.domain.analyzer import DerivedOutputIdentityProvider
from btmm_ai_scanner.historical_backtest.data_quality import HistoricalDataQualityReport
from btmm_ai_scanner.historical_backtest.enums import BacktestQualityGateStatus
from btmm_ai_scanner.historical_backtest.loader import LoadedHistoricalDataset
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.evaluation import ScannerBacktestReport, evaluate_scanner
from btmm_ai_scanner.scanner.replay import ScannerReplayResult, run_scanner_replay

_SYMBOL_ORDER: dict[InternalSymbol, int] = {
    InternalSymbol.XAUUSD: 1,
    InternalSymbol.EURUSD: 2,
    InternalSymbol.GBPUSD: 3,
}


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

    for symbol in ordered_symbols:
        bundles = bundles_by_symbol[symbol]
        replay_result = run_scanner_replay(
            bundles,
            (),
            scanner_configuration,
            replay_configuration,
            identity_provider,
        )
        symbols_processed.append(symbol)
        replay_results.append(replay_result)

        symbol_cases = tuple(
            case for case in dataset.reviewed_cases if case.symbol == symbol
        )
        if len(symbol_cases) == 0:
            backtest_reports.append(None)
        else:
            backtest_reports.append(evaluate_scanner(replay_result, symbol_cases))

        if (
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
    )
