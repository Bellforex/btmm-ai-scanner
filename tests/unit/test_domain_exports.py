import btmm_ai_scanner.domain as domain
import btmm_ai_scanner.measurements as measurements
from btmm_ai_scanner.domain.analyzer import MarketMeasurementAnalysis
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.domain.trendlines import Trendline

_EXPECTED_DOMAIN_EXPORTS = [
    "SwingType",
    "DisplacementDirection",
    "DisplacementClassification",
    "EqualLevelType",
    "SupportResistanceType",
    "TrendlineOrientation",
    "DerivedOutputType",
    "ConfirmedSwing",
    "DisplacementObservation",
    "EqualLevelCluster",
    "SupportResistanceZone",
    "Trendline",
    "MarketMeasurementAnalysis",
    "MarketMeasurementConfiguration",
    "MixedSymbolAnalysisError",
    "MixedTimeframeAnalysisError",
    "UnsortedCandleSequenceError",
    "DuplicateCandleRecordError",
    "AmbiguousEventTimeAnalysisError",
    "InvalidMarketMeasurementConfigurationError",
    "DerivedIdentityCollisionError",
    "DerivedOutputIdentityProvider",
    "analyze_market_measurements",
]

_EXPECTED_MEASUREMENTS_EXPORTS = [
    "bearish_close_position",
    "body",
    "body_efficiency",
    "bullish_close_position",
    "compute_atr_series",
    "lower_wick",
    "median_total_range",
    "range_speed_ratio",
    "total_range",
    "upper_wick",
]

_FORBIDDEN_FIELD_NAMES = {
    "poi_id",
    "poi_type",
    "poi_status",
    "bounded_range",
    "boundary_top",
    "boundary_bottom",
    "reclaim_time_utc",
    "invalidation_time_utc",
    "structure_state",
    "structure_direction",
    "bos",
    "choch",
    "hh",
    "hl",
    "lh",
    "ll",
    "protected",
    "weak",
    "liquidity_references",
}


def test_measurements_and_domain_exports_import_successfully() -> None:
    assert hasattr(measurements, "total_range")
    assert hasattr(domain, "ConfirmedSwing")


def test_domain_exports_exact_23_names_and_order() -> None:
    assert domain.__all__ == _EXPECTED_DOMAIN_EXPORTS
    assert len(domain.__all__) == 23
    for name in _EXPECTED_DOMAIN_EXPORTS:
        assert hasattr(domain, name)


def test_measurements_exports_exact_names_and_order() -> None:
    assert list(measurements.__all__) == sorted(_EXPECTED_MEASUREMENTS_EXPORTS)
    assert len(measurements.__all__) == 10
    for name in _EXPECTED_MEASUREMENTS_EXPORTS:
        assert hasattr(measurements, name)


def test_domain_contracts_expose_no_poi_btmm_or_structure_transition_fields() -> None:
    contract_classes = (
        ConfirmedSwing,
        SupportResistanceZone,
        Trendline,
        EqualLevelCluster,
        MarketMeasurementAnalysis,
    )
    for contract_class in contract_classes:
        field_names = set(contract_class.model_fields.keys())
        assert field_names.isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_domain_aggregate_field_order_matches_approved_contract() -> None:
    expected_order = [
        "symbol",
        "timeframe",
        "analyzed_candle_count",
        "confirmed_swings",
        "displacement_observations",
        "equal_level_clusters",
        "support_resistance_zones",
        "trendlines",
    ]
    assert list(MarketMeasurementAnalysis.model_fields.keys()) == expected_order
