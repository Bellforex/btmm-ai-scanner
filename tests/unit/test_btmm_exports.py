import btmm_ai_scanner.btmm as btmm_package

_EXPECTED_EXPORTS = [
    "BtmmDirection",
    "BtmmGateStatus",
    "BtmmContextAlignmentStatus",
    "BtmmSessionStatus",
    "BtmmInteractionClass",
    "BtmmReactionClassification",
    "BtmmLiquidityLocation",
    "BtmmEvidenceSource",
    "BtmmLifecycleStatus",
    "BtmmFormationStage",
    "BtmmLifecycleTransitionType",
    "BtmmCancellationReason",
    "BtmmBlockedReason",
    "BtmmVolumePillarStatus",
    "BtmmLiquidityEvidenceStatus",
    "BtmmObservation",
    "BtmmLifecycleTransition",
    "CurrentBtmmState",
    "BtmmAnalysis",
    "BtmmReviewedEvidence",
    "BtmmConfiguration",
    "BtmmTimeframeInput",
    "InvalidBtmmConfigurationError",
    "DuplicateBtmmTimeframeInputError",
    "UnsortedBtmmTimeframeInputError",
    "InputPrefixMismatchError",
    "MissingSourcePoiRecordError",
    "ImpossibleBtmmLifecycleTransitionError",
    "analyze_btmm",
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


def test_btmm_package_imports_successfully() -> None:
    for name in _EXPECTED_EXPORTS:
        assert hasattr(btmm_package, name)


def test_exact_29_export_surface_in_order() -> None:
    assert btmm_package.__all__ == _EXPECTED_EXPORTS
    assert len(btmm_package.__all__) == 29


def test_no_entry_stop_target_risk_or_trade_result_field_anywhere() -> None:
    for contract_name in (
        "BtmmObservation",
        "BtmmLifecycleTransition",
        "CurrentBtmmState",
        "BtmmReviewedEvidence",
    ):
        contract_class = getattr(btmm_package, contract_name)
        assert _FORBIDDEN_TRADE_FIELD_NAMES.isdisjoint(contract_class.model_fields)


def test_no_domain_structure_poi_or_measurements_reexport() -> None:
    forbidden_names = {
        "MarketMeasurementAnalysis",
        "StructureAnalysis",
        "PoiObservation",
        "PoiAnalysis",
        "DerivedOutputIdentityProvider",
        "LegSpeedClassification",
    }
    assert forbidden_names.isdisjoint(set(btmm_package.__all__))


def test_no_btmm_pattern_type_enum_exists() -> None:
    assert not hasattr(btmm_package, "BtmmPatternType")
    assert "BtmmPatternType" not in btmm_package.__all__
