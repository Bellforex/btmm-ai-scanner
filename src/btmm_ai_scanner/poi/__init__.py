"""Deterministic, no-look-ahead POI detection and lifecycle foundation."""

from btmm_ai_scanner.poi.analyzer import (
    DuplicatePoiTimeframeInputError,
    ImpossiblePoiLifecycleTransitionError,
    InputPrefixMismatchError,
    MissingSourceRecordError,
    PoiAnalysis,
    PoiTimeframeInput,
    UnsortedPoiTimeframeInputError,
    analyze_pois,
)
from btmm_ai_scanner.poi.configuration import (
    InvalidPoiConfigurationError,
    PoiConfiguration,
)
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFamily,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
    PoiOverlapRelationshipType,
    PoiStrengthTier,
    PoiTapClassification,
    PoiType,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.overlap import PoiOverlapRelationship

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
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
