"""RC5 VIEW is GENERATED, and it is structure presentation ONLY.

VIEW exists to give CORE back the 1,036 tokens the HH/HL/LH/LL and BOS/CHOCH
renderer cost. That is only legitimate while VIEW stays a structural subset: the
moment it needs the POI registry, the sweep engine or authority, it stops being
a view and becomes a second scanner, which the Heavy Script warning makes
reckless.

The trendline renderer deliberately STAYED in CORE. Its one-visible-line winner
reads `rc5TlHit`, which the qualified sweep engine writes from POI references,
so a structure-only VIEW cannot reproduce the same winner. That is a semantic
boundary, and these tests pin it so it is not "optimised" away later.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tools.rc5_compose import (  # type: ignore[import-not-found]
    CORE,
    PANEL,
    VIEW,
    VIEW_PART,
    CompositionError,
    compose_view,
)

_TRENDLINE_RENDER = "    // ---- RC5 STRUCTURAL TRENDLINE LAYER"
_STRUCTURE_RENDER = "    // ---- RC3 market-structure overlay (presentation only)"
_POI_RENDER = "    // P7-Z — POI zone visualization"


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def _generated() -> str:
    return compose_view(_read(CORE), _read(VIEW_PART))


# ---------------------------------------------------------------------------
# generation contract
# ---------------------------------------------------------------------------


def test_the_committed_view_is_exactly_what_the_composer_produces() -> None:
    """Stale or hand-edited VIEW fails here rather than on a chart."""
    assert _read(VIEW) == _generated()


def test_generation_is_deterministic() -> None:
    assert _generated() == _generated()


def test_a_hand_edit_to_view_is_detected() -> None:
    edited = _read(VIEW).replace("msPrevHL", "msPrevHL_EDITED", 1)
    assert edited != _read(VIEW), "the token under test no longer occurs"
    assert edited != _generated()


def test_a_missing_marker_fails_loudly_instead_of_cutting_blind() -> None:
    broken = _read(CORE).replace("//#VIEW-CUT-BEGIN MAIN_DISPLACEMENT", "// gone", 1)
    with pytest.raises(CompositionError):
        compose_view(broken, _read(VIEW_PART))


def test_a_missing_render_anchor_fails_loudly() -> None:
    broken = _read(CORE).replace("//#VIEW-RENDER-ANCHOR", "// gone", 1)
    with pytest.raises(CompositionError):
        compose_view(broken, _read(VIEW_PART))


# ---------------------------------------------------------------------------
# ownership: exactly one copy of each renderer, in the right artifact
# ---------------------------------------------------------------------------


def test_core_no_longer_contains_the_structure_renderer() -> None:
    core = _read(CORE)
    assert _STRUCTURE_RENDER not in core
    assert "//#VIEW-RENDER-ANCHOR" in core


def test_view_contains_the_structure_renderer_exactly_once() -> None:
    view = _read(VIEW)
    # the renderer's own state write, which occurs once in the block and nowhere
    # else in the file -- so this counts the renderer, not a coincidence
    assert view.count("array.set(msPrevHL") == 1
    assert view.count("label.style_label_down") == 1
    assert _read(CORE).count("array.set(msPrevHL") == 0


def test_the_trendline_renderer_stays_in_core_and_is_absent_from_view() -> None:
    """The semantic boundary, pinned.

    `rc5TlHit` is written by the sweep engine from POI references, so a
    structure-only VIEW cannot pick the same winner. Moving this renderer would
    require importing POI semantics -- which is exactly what VIEW must not do.
    """
    assert _TRENDLINE_RENDER in _read(CORE)
    assert _TRENDLINE_RENDER not in _read(VIEW)
    assert "rc5TlHit" in _read(CORE)
    assert "rc5TlHit" not in _read(VIEW)


def test_the_poi_renderer_stays_in_core_and_is_absent_from_view() -> None:
    assert _POI_RENDER in _read(CORE)
    assert _POI_RENDER not in _read(VIEW)


def test_panel_remains_tables_only_and_draws_no_market_space() -> None:
    panel = _read(PANEL)
    assert _TRENDLINE_RENDER not in panel
    assert _POI_RENDER not in panel
    assert _STRUCTURE_RENDER not in panel
    assert "table.new(" in panel


def test_view_draws_no_tables() -> None:
    view = _read(VIEW)
    drawn = [
        line
        for line in view.split("\n")
        if not line.lstrip().startswith("//")
        and ("table.new(" in line or "table.cell(" in line)
    ]
    assert drawn == [], drawn


# ---------------------------------------------------------------------------
# VIEW carries no semantics it has no business carrying
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("what", "needle"),
    [
        ("POI detector (bases)", "f_poiDetectBases"),
        ("POI detector (order blocks)", "f_poiDetectOrderBlocks"),
        ("POI registry append", "f_poiAppend"),
        ("POI registry emit", "f_poiEmit"),
        ("reversal authority ladder", "f_rc5LadderRank"),
        ("same-origin authority", "f_rc5SameOrigin"),
        ("qualified sweep engine", "f_rc5Qualifies"),
        ("sweep trendline-hit sidecar", "rc5TlHit"),
        ("BTMM setup engine", "BTMM SETUP ENGINE"),
        ("P5 supervisory confluence", "P5 — BTRC-T1"),
    ],
)
def test_view_contains_no_semantic_block(what: str, needle: str) -> None:
    assert needle not in _read(VIEW), f"VIEW carries {what}"


def test_view_is_materially_smaller_than_core() -> None:
    """A view that is nearly as big as CORE would have bought nothing and would
    double the runtime cost for no reason."""
    core_lines = len(_read(CORE).split("\n"))
    view_lines = len(_read(VIEW).split("\n"))
    assert view_lines < core_lines // 3, (view_lines, core_lines)
