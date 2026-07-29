import btmm_ai_scanner.poi as poi

_EXPECTED_EXPORTS = [
    "PoiFamily",
    "PoiDirection",
    "PoiType",
    "PoiStrengthTier",
    "PoiLifecycleStatus",
    "PoiLifecycleTransitionType",
    "PoiFreshnessStatus",
    "PoiTapClassification",
    "PoiOverlapRelationshipType",
    "PoiObservation",
    "PoiLifecycleTransition",
    "PoiOverlapRelationship",
    "CurrentPoiState",
    "PoiAnalysis",
    "PoiConfiguration",
    "PoiTimeframeInput",
    "InvalidPoiConfigurationError",
    "DuplicatePoiTimeframeInputError",
    "UnsortedPoiTimeframeInputError",
    "InputPrefixMismatchError",
    "MissingSourceRecordError",
    "ImpossiblePoiLifecycleTransitionError",
    "analyze_pois",
]


def test_poi_exports_import_successfully() -> None:
    assert hasattr(poi, "analyze_pois")
    assert hasattr(poi, "PoiObservation")


def test_poi_exports_exact_twenty_three_name_surface() -> None:
    assert poi.__all__ == _EXPECTED_EXPORTS
    assert len(poi.__all__) == 23
    for name in _EXPECTED_EXPORTS:
        assert hasattr(poi, name)


def test_poi_contracts_expose_no_btmm_entry_trade_or_structure_source_fields() -> None:
    forbidden_substrings = (
        "btmm",
        "entry",
        "stop_loss",
        "take_profit",
        "trade",
        "structure_analysis",
        "source_structure_record_ids",
        "validity_status",
    )
    contract_classes = (
        poi.PoiObservation,
        poi.PoiLifecycleTransition,
        poi.PoiOverlapRelationship,
        poi.CurrentPoiState,
        poi.PoiAnalysis,
    )
    for contract_class in contract_classes:
        for field_name in contract_class.model_fields:
            lowered = field_name.lower()
            for forbidden in forbidden_substrings:
                assert forbidden not in lowered


def test_poi_type_enum_contains_no_deferred_or_placeholder_members() -> None:
    forbidden_members = {
        "BULLISH_TRENDLINE",
        "BEARISH_TRENDLINE",
        "SWING_HIGH",
        "SWING_LOW",
    }
    member_names = {member.name for member in poi.PoiType}
    assert forbidden_members.isdisjoint(member_names)
    assert len(poi.PoiType) == 32


def test_poi_package_never_imports_btmm_or_execution_modules() -> None:
    import btmm_ai_scanner.poi.analyzer as analyzer_module

    module_source_names = set(dir(analyzer_module))
    forbidden = {"btmm", "execution", "broker", "entry_signal"}
    assert forbidden.isdisjoint({name.lower() for name in module_source_names})
