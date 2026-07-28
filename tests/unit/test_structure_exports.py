from pathlib import Path

import btmm_ai_scanner.structure as structure
from btmm_ai_scanner.structure.current_state import CurrentStructureState
from btmm_ai_scanner.structure.enums import StructureDirection, StructureTransitionType
from btmm_ai_scanner.structure.relationships import SwingRelationship
from btmm_ai_scanner.structure.transitions import StructureTransition

_EXPECTED_STRUCTURE_EXPORTS = [
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

_FORBIDDEN_FIELD_NAMES = {
    "poi_id",
    "poi_type",
    "poi_status",
    "bounded_range",
    "boundary_top",
    "boundary_bottom",
    "reclaim_time_utc",
    "invalidation_time_utc",
    "liquidity_references",
}

_STRUCTURE_PACKAGE_DIR = (
    Path(__file__).resolve().parents[2] / "src" / "btmm_ai_scanner" / "structure"
)


def test_structure_exports_import_successfully() -> None:
    assert hasattr(structure, "analyze_structure_state")
    assert hasattr(structure, "StructureDirection")


def test_structure_exports_exact_structure_owned_surface() -> None:
    assert structure.__all__ == _EXPECTED_STRUCTURE_EXPORTS
    assert len(structure.__all__) == 12
    for name in _EXPECTED_STRUCTURE_EXPORTS:
        assert hasattr(structure, name)


def test_structure_contracts_expose_no_poi_or_btmm_fields() -> None:
    contract_classes = (
        SwingRelationship,
        StructureTransition,
        CurrentStructureState,
        structure.StructureAnalysis,
    )
    for contract_class in contract_classes:
        field_names = set(contract_class.model_fields.keys())
        assert field_names.isdisjoint(_FORBIDDEN_FIELD_NAMES)


def test_structure_transitions_never_include_a_transitional_pending_state() -> None:
    assert {member.value for member in StructureTransitionType} == {
        "BULLISH_BOS",
        "BEARISH_BOS",
        "BULLISH_CHOCH",
        "BEARISH_CHOCH",
    }
    assert {member.value for member in StructureDirection} == {
        "UNDETERMINED",
        "BULLISH",
        "BEARISH",
    }


def test_structure_package_never_imports_poi_or_btmm_modules() -> None:
    source_files = sorted(_STRUCTURE_PACKAGE_DIR.glob("*.py"))
    assert len(source_files) > 0
    for source_file in source_files:
        content = source_file.read_text(encoding="utf-8")
        for line in content.splitlines():
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                lowered = stripped.lower()
                assert "poi" not in lowered, f"{source_file.name}: {stripped!r}"
                assert "btmm_ai_scanner.btmm" not in lowered, (
                    f"{source_file.name}: {stripped!r}"
                )
