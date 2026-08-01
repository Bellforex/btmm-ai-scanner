from btmm_ai_scanner.historical_backtest.cli import main
from btmm_ai_scanner.historical_backtest.configuration import (
    HistoricalDatasetConfiguration,
)
from btmm_ai_scanner.historical_backtest.data_quality import (
    ChecksumMismatchError,
    DataQualityIssue,
    GapRecord,
    HistoricalDataQualityReport,
    TimeframeCoverage,
)
from btmm_ai_scanner.historical_backtest.enums import (
    BacktestQualityGateStatus,
    CandleCompletenessConvention,
    CandleTimestampConvention,
    CanonicalCandleField,
    DataQualityClassification,
    DatasetPartition,
    HistoricalFileFormat,
)
from btmm_ai_scanner.historical_backtest.execution import (
    HistoricalBacktestExecutionResult,
    execute_scanner_backtest,
)
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.historical_backtest.loader import (
    DatasetManifestNotFoundError,
    LoadedHistoricalDataset,
    ReviewedCaseDocument,
    load_historical_dataset,
)
from btmm_ai_scanner.historical_backtest.manifest import (
    DatasetManifest,
    HeaderMappingEntry,
    HistoricalFileEntry,
    InvalidDatasetManifestError,
)
from btmm_ai_scanner.historical_backtest.reporting import (
    HistoricalReportWriteError,
    ReportWriteResult,
    write_backtest_report,
)

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
    "DatasetPartition",
    "CandleTimestampConvention",
    "CandleCompletenessConvention",
    "HistoricalFileFormat",
    "CanonicalCandleField",
    "DataQualityClassification",
    "BacktestQualityGateStatus",
    "HistoricalDatasetConfiguration",
    "HeaderMappingEntry",
    "HistoricalFileEntry",
    "DatasetManifest",
    "InvalidDatasetManifestError",
    "DataQualityIssue",
    "GapRecord",
    "TimeframeCoverage",
    "HistoricalDataQualityReport",
    "ChecksumMismatchError",
    "ReviewedCaseDocument",
    "LoadedHistoricalDataset",
    "DatasetManifestNotFoundError",
    "load_historical_dataset",
    "ContentAddressedIdentityProvider",
    "HistoricalBacktestExecutionResult",
    "execute_scanner_backtest",
    "ReportWriteResult",
    "HistoricalReportWriteError",
    "write_backtest_report",
    "main",
]
