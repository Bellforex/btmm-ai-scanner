import btmm_ai_scanner.scanner as scanner_package

_EXPECTED_EXPORTS = [
    "SnapshotRetentionPolicy",
    "LabelMatchStatus",
    "ScannerTimeframeInput",
    "ScannerConfiguration",
    "ReplayConfiguration",
    "ScannerAnalysis",
    "ScannerSetupSummary",
    "ScannerReplayResult",
    "DetectionMismatch",
    "ReviewedScannerCase",
    "ExpectedPoiLabel",
    "ExpectedBtmmLabel",
    "LabelMatch",
    "PoiValidationReport",
    "BtmmValidationReport",
    "LifecycleValidationReport",
    "LifecycleMismatch",
    "ScannerHealthReport",
    "ScannerBacktestReport",
    "MissingRequiredTimeframeError",
    "InvalidScannerConfigurationError",
    "InvalidScannerCandleInputError",
    "InvalidReviewedLabelError",
    "scan_market",
    "run_scanner_replay",
    "evaluate_scanner",
]

_FORBIDDEN_TRADE_FIELD_NAMES = frozenset(
    {
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_reward",
        "position_size",
        "trade_outcome",
        "signal_confidence",
        "ai_score",
    }
)


def test_scanner_exports_match_exact_approved_order() -> None:
    assert scanner_package.__all__ == _EXPECTED_EXPORTS
    for name in _EXPECTED_EXPORTS:
        assert hasattr(scanner_package, name)


def test_scanner_exports_total_exactly_twenty_six() -> None:
    assert len(scanner_package.__all__) == 26


def test_scanner_does_not_reexport_upstream_package_names() -> None:
    forbidden_names = {
        "MarketMeasurementAnalysis",
        "StructureAnalysis",
        "PoiAnalysis",
        "BtmmAnalysis",
        "MixedSymbolAnalysisError",
    }
    assert forbidden_names.isdisjoint(set(scanner_package.__all__))


def test_scanner_does_not_export_identity_protocol() -> None:
    assert "DerivedOutputIdentityProvider" not in scanner_package.__all__
    assert not hasattr(scanner_package, "DerivedOutputIdentityProvider")


def test_scanner_contracts_contain_no_entry_stop_target_or_pnl_field() -> None:
    contract_names = (
        "ScannerAnalysis",
        "ScannerSetupSummary",
        "ScannerReplayResult",
        "DetectionMismatch",
        "ReviewedScannerCase",
        "ExpectedPoiLabel",
        "ExpectedBtmmLabel",
        "LabelMatch",
        "PoiValidationReport",
        "BtmmValidationReport",
        "LifecycleValidationReport",
        "LifecycleMismatch",
        "ScannerHealthReport",
        "ScannerBacktestReport",
    )
    for contract_name in contract_names:
        contract_class = getattr(scanner_package, contract_name)
        assert _FORBIDDEN_TRADE_FIELD_NAMES.isdisjoint(contract_class.model_fields)


def test_scanner_does_not_export_rendering_or_telegram_helpers() -> None:
    forbidden_names = {
        "render_chart",
        "send_telegram_alert",
        "TelegramClient",
        "ChartRenderer",
        "CsvWriter",
    }
    assert forbidden_names.isdisjoint(set(scanner_package.__all__))
