"""Market measurements and reference-structure contracts and analyzer."""

from btmm_ai_scanner.domain.analyzer import (
    AmbiguousEventTimeAnalysisError,
    DerivedIdentityCollisionError,
    DerivedOutputIdentityProvider,
    DuplicateCandleRecordError,
    InvalidMarketMeasurementConfigurationError,
    MarketMeasurementAnalysis,
    MixedSymbolAnalysisError,
    MixedTimeframeAnalysisError,
    UnsortedCandleSequenceError,
    analyze_market_measurements,
)
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.enums import (
    DerivedOutputType,
    DisplacementClassification,
    DisplacementDirection,
    EqualLevelType,
    SupportResistanceType,
    SwingType,
    TrendlineOrientation,
)
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.domain.trendlines import Trendline

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
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
