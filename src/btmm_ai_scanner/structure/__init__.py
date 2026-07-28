"""Deterministic, no-look-ahead market-structure state and transitions."""

from btmm_ai_scanner.structure.analyzer import (
    InvalidStructureConfigurationError,
    InvalidSwingReferenceError,
    StructureAnalysis,
    UnsortedSwingSequenceError,
    analyze_structure_state,
)
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
    SwingRelationshipLabel,
)
from btmm_ai_scanner.structure.relationships import SwingRelationship
from btmm_ai_scanner.structure.transitions import StructureTransition

__all__ = [  # noqa: RUF022 -- order is an approved contract, not alphabetical
    "StructureDirection",
    "SwingRelationshipLabel",
    "StructureTransitionType",
    "SwingRelationship",
    "StructureTransition",
    "CurrentStructureState",
    "StructureAnalysis",
    "StructureConfiguration",
    "InvalidSwingReferenceError",
    "UnsortedSwingSequenceError",
    "InvalidStructureConfigurationError",
    "analyze_structure_state",
]
