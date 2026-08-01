from importlib.metadata import version as _package_version

import btmm_ai_scanner.historical_backtest as historical_backtest_package

_EXPECTED_EXPORTS = [
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

_PINNED_TZDATA_VERSION = "2026.3"


def test_historical_backtest_package_exports_exact_public_surface() -> None:
    assert historical_backtest_package.__all__ == _EXPECTED_EXPORTS
    assert len(historical_backtest_package.__all__) == 28
    for name in _EXPECTED_EXPORTS:
        assert hasattr(historical_backtest_package, name)

    assert _package_version("tzdata") == _PINNED_TZDATA_VERSION
