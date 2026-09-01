"""Which BTMM enum members production can actually produce.

The BTMM enums declare more vocabulary than the engine assigns. Some members
are reserved for a richer review contract that `BtmmReviewedEvidence` does not
carry today; others are simply never reached. That distinction decides what the
Pine port owes:

* PRODUCED members must be implemented and proven at parity;
* PASS-THROUGH members are copied out of reviewed evidence, so they exist in
  the engine (Layer A) and are unreachable in the no-evidence runtime (Layer B);
* RESERVED members are not implemented by production and must not be invented
  by the port.

Reporting "9 of 9 interaction classes" would therefore be false -- production
produces 7 and never assigns NO_CONTACT or NEAR_MISS. These tests fix the real
denominator so the coverage numbers in the P4 report mean something, and so a
later change that starts producing a reserved member has to say so here.
"""

from __future__ import annotations

import enum
import pathlib
import re

import pytest

from btmm_ai_scanner.btmm import enums as btmm_enums
from btmm_ai_scanner.btmm.enums import (
    BtmmEvidenceSource,
    BtmmFormationStage,
    BtmmInteractionClass,
    BtmmLiquidityLocation,
    BtmmReactionClassification,
)
from btmm_ai_scanner.btmm.reviewed_evidence import (
    CONTEXT_AND_LIQUIDITY_ALLOWED_SOURCES,
    VOLUME_ALLOWED_SOURCES,
    BtmmReviewedEvidence,
)

#: Members the engine never assigns anywhere in `src/`. Not a bug list -- it is
#: the declared-but-unimplemented surface, recorded so it stays visible.
RESERVED: dict[str, frozenset[str]] = {
    "BtmmFormationStage": frozenset(
        {"CONTEXT_CHECK", "LIQUIDITY_MONITORING", "APPROACH_MONITORING"}
    ),
    "BtmmInteractionClass": frozenset({"NO_CONTACT", "NEAR_MISS"}),
    "BtmmLiquidityLocation": frozenset(
        {
            "LIQUIDITY_BEFORE_POI",
            "LIQUIDITY_WITHIN_POI",
            "MULTIPLE_LOCATIONS",
            "NONE_OBSERVED",
            "NOT_YET_EVALUATED",
        }
    ),
    "BtmmReactionClassification": frozenset(
        {"AWAITING_REACTION", "REACTION_IN_PROGRESS"}
    ),
    "BtmmEvidenceSource": frozenset({"MODEL_PROPOSED"}),
    # These four are never assigned by the engine but ARE copied through from
    # reviewed evidence, so they are reachable in Layer A only.
    "BtmmContextAlignmentStatus": frozenset({"UNKNOWN"}),
    "BtmmSessionStatus": frozenset({"UNKNOWN"}),
    "BtmmVolumePillarStatus": frozenset({"MISSING_DATA", "UNRESOLVED"}),
}

PASS_THROUGH_ONLY: frozenset[tuple[str, str]] = frozenset(
    {
        ("BtmmContextAlignmentStatus", "UNKNOWN"),
        ("BtmmSessionStatus", "UNKNOWN"),
        ("BtmmVolumePillarStatus", "MISSING_DATA"),
        ("BtmmVolumePillarStatus", "UNRESOLVED"),
    }
)


def _btmm_enum_types() -> list[type[enum.Enum]]:
    return [
        obj
        for obj in vars(btmm_enums).values()
        if isinstance(obj, type)
        and issubclass(obj, enum.Enum)
        and obj.__module__ == btmm_enums.__name__
    ]


def _production_source() -> str:
    root = pathlib.Path(__file__).resolve().parents[2] / "src" / "btmm_ai_scanner"
    return "\n".join(p.read_text(encoding="utf-8") for p in sorted(root.rglob("*.py")))


@pytest.mark.parametrize("enum_type", _btmm_enum_types(), ids=lambda e: e.__name__)
def test_assigned_members_match_the_recorded_inventory(
    enum_type: type[enum.Enum],
) -> None:
    """Scan production for `Enum.MEMBER` and compare against RESERVED."""
    source = _production_source()
    unassigned = {
        member.name
        for member in enum_type
        if not re.search(rf"\b{enum_type.__name__}\.{member.name}\b", source)
    }
    assert unassigned == RESERVED.get(enum_type.__name__, frozenset())


def test_reserved_names_are_real_members() -> None:
    """Guard the guard: a typo here would silently weaken every assertion."""
    by_name = {e.__name__: e for e in _btmm_enum_types()}
    for enum_name, members in RESERVED.items():
        assert enum_name in by_name
        valid = {m.name for m in by_name[enum_name]}
        assert members <= valid, f"{enum_name}: {members - valid}"


def test_pass_through_members_are_a_subset_of_reserved() -> None:
    for enum_name, member_name in PASS_THROUGH_ONLY:
        assert member_name in RESERVED[enum_name]


def test_produced_counts_are_what_the_port_owes() -> None:
    """Denominators for ENGINE_REACHABLE_COVERAGE -- declared minus reserved.

    Asserted rather than described so the P4 report and the code cannot drift.
    """
    produced = {
        e.__name__: len(e) - len(RESERVED.get(e.__name__, frozenset()))
        for e in _btmm_enum_types()
    }
    assert produced == {
        "BtmmBlockedReason": 4,
        "BtmmCancellationReason": 8,
        "BtmmContextAlignmentStatus": 3,
        "BtmmDirection": 2,
        "BtmmEvidenceSource": 4,
        "BtmmFormationStage": 3,
        "BtmmGateStatus": 3,
        "BtmmInteractionClass": 7,
        "BtmmLifecycleStatus": 5,
        "BtmmLifecycleTransitionType": 15,
        "BtmmLiquidityEvidenceStatus": 2,
        "BtmmLiquidityLocation": 1,
        "BtmmReactionClassification": 3,
        "BtmmSessionStatus": 3,
        "BtmmVolumePillarStatus": 3,
    }


def test_the_full_lifecycle_spine_is_live() -> None:
    """Nothing on the lifecycle spine is reserved: all 5 statuses, all 15
    transition types and every terminal reason are produced, so the port must
    implement every one of them."""
    assert "BtmmLifecycleStatus" not in RESERVED
    assert "BtmmLifecycleTransitionType" not in RESERVED
    assert "BtmmCancellationReason" not in RESERVED
    assert "BtmmBlockedReason" not in RESERVED


def test_only_one_liquidity_location_is_derivable() -> None:
    """`find_automatic_liquidity_evidence` returns LIQUIDITY_AFTER_POI and
    nothing else, and reviewed evidence carries no location field at all -- so
    the other five locations cannot appear on any output record."""
    assert "liquidity_location" not in BtmmReviewedEvidence.model_fields
    live = {m.name for m in BtmmLiquidityLocation} - RESERVED["BtmmLiquidityLocation"]
    assert live == {"LIQUIDITY_AFTER_POI"}


def test_engine_stage_vocabulary_is_the_last_three_stages() -> None:
    """The three monitoring stages are reserved; the engine reports only the
    stages from POI interaction onward."""
    live = {m.name for m in BtmmFormationStage} - RESERVED["BtmmFormationStage"]
    assert live == {"POI_INTERACTION", "REACTION_MONITORING", "FINAL_GATE_EVALUATION"}


def test_reaction_vocabulary_is_the_three_terminal_tiers() -> None:
    live = {m.name for m in BtmmReactionClassification} - RESERVED[
        "BtmmReactionClassification"
    ]
    assert live == {"WEAK_REACTION", "STANDARD_REACTION", "STRONG_REACTION"}


def test_interaction_vocabulary_excludes_the_two_non_contact_classes() -> None:
    """`find_first_interaction` returns None when no candle touches the zone --
    it never labels the absence, so NO_CONTACT and NEAR_MISS stay unused."""
    live = {m.name for m in BtmmInteractionClass} - RESERVED["BtmmInteractionClass"]
    assert live == {
        "EDGE_TOUCH",
        "PARTIAL_ENTRY",
        "DEEP_ENTRY",
        "FAR_BOUNDARY_TOUCH",
        "CONTROLLED_OVERSHOOT",
        "EXCESSIVE_OVERSHOOT",
        "NONCANONICAL_SIDE_INTERACTION",
    }


def test_model_proposed_can_never_reach_an_output_record() -> None:
    """It is not produced internally and every reviewed-source validator
    rejects it, so no BTMM record can carry a model-proposed source. This is the
    product-integrity guarantee stated as a property of the vocabulary."""
    assert (
        BtmmEvidenceSource.MODEL_PROPOSED not in CONTEXT_AND_LIQUIDITY_ALLOWED_SOURCES
    )
    assert BtmmEvidenceSource.MODEL_PROPOSED not in VOLUME_ALLOWED_SOURCES
    assert "MODEL_PROPOSED" in RESERVED["BtmmEvidenceSource"]
