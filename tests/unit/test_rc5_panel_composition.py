"""RC5 CORE and RC5 PANEL must never drift apart.

RC5 ships as two Pine scripts because the faithful single-script build measures
101,757 tokens against a 100,256 hard limit. CORE draws the chart, PANEL draws
the diagnostic tables, and Pine cannot read another script's private state -- so
PANEL has to compute the same semantics CORE does.

That is the drift hazard this module exists to close. PANEL is not written by
hand; `tools/rc5_compose.py` composes it from CORE by deleting the chart-space
renderers and inserting the screen-space diagnostics. Every semantic line in
PANEL is therefore CORE's own line, byte for byte.

These tests make that a property of the repository rather than of anyone's
memory:

* editing PANEL by hand fails, because it stops matching what CORE composes to;
* editing CORE's semantics without regenerating fails, for the same reason;
* a line that is neither CORE's nor declared presentation fails, so a semantic
  rule cannot be smuggled into PANEL alone.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.rc5_compose import (  # noqa: E402
    CHART_RENDERERS,
    CORE,
    CORE_TITLE,
    PANEL,
    PANEL_TITLE,
    PART,
    CompositionError,
    compose,
)


def _read(path: Path) -> str:
    return path.read_bytes().decode("utf-8")


def test_the_committed_panel_is_exactly_what_core_composes_to() -> None:
    """The one check that makes drift impossible rather than merely unlikely."""
    composed = compose(_read(CORE), _read(PART))
    assert _read(PANEL) == composed, (
        "RC5 PANEL is not the composition of RC5 CORE. Either PANEL was edited "
        "by hand, or CORE changed and PANEL was not regenerated. Run "
        "tools/rc5_compose.py -- do not edit PANEL directly."
    )


def test_composition_is_deterministic(tmp_path: Path) -> None:
    """Same inputs, same bytes. A composer that drifts is not an anti-drift tool."""
    core, part = _read(CORE), _read(PART)
    first = compose(core, part)
    second = compose(core, part)
    assert first == second

    scratch = tmp_path / "panel.pine"
    scratch.write_bytes(first.encode("utf-8"))
    assert scratch.read_bytes().decode("utf-8") == second


def test_every_panel_line_is_either_cores_own_or_declared_presentation() -> None:
    """No semantic rule may exist in PANEL and nowhere else.

    A line PANEL has that CORE does not must come from the presentation part
    file, which holds table rendering and the strings those tables print. If a
    line appears in neither, someone wrote market logic into PANEL alone.
    """
    core_lines = set(_read(CORE).split("\n"))
    part_lines = set(_read(PART).split("\n"))
    # the placeholder comments the composer itself writes where a renderer was
    composed_notes = {
        f"    // RC5 PANEL: {note} is drawn by RC5 CORE."
        for _, _, note in CHART_RENDERERS
    }
    composed_notes |= {
        "    // RC5 PANEL: P7-Z zone boxes and labels are drawn by RC5 CORE.",
        "// RC5 PANEL: the BTMM cycle marker is a chart visual and belongs to CORE.",
    }
    # PANEL's own study title, so two legend rows on one chart are tellable
    # apart. Derived from the composer's constants, not retyped, so a change to
    # either title cannot quietly slip past this check.
    composed_notes |= {
        line.replace(CORE_TITLE, PANEL_TITLE)
        for line in core_lines
        if CORE_TITLE in line
    }

    orphans = [
        line
        for line in _read(PANEL).split("\n")
        if line.strip()
        and line not in core_lines
        and line not in part_lines
        and line not in composed_notes
    ]
    assert orphans == [], f"lines that exist only in PANEL: {orphans[:5]}"


def test_panel_draws_nothing_in_market_space() -> None:
    """CORE owns the chart. Attached together, nothing may be drawn twice."""
    panel = _read(PANEL)
    drawing = [
        line
        for line in panel.split("\n")
        if not line.lstrip().startswith("//")
        and any(
            call in line
            for call in ("box.new(", "line.new(", "label.new(", "plotshape(")
        )
    ]
    assert drawing == [], f"PANEL draws in market space: {drawing[:3]}"


def test_core_draws_no_tables() -> None:
    """...and PANEL owns the screen. The split is symmetric or it is not a split."""
    core = _read(CORE)
    tables = [
        line
        for line in core.split("\n")
        if not line.lstrip().startswith("//")
        and ("table.new(" in line or "table.cell(" in line)
    ]
    assert tables == [], f"CORE renders a table: {tables[:3]}"


def test_a_renamed_chart_renderer_fails_loudly() -> None:
    """Silent mis-cutting is the failure mode that would cost the most.

    If a region marker stops matching, the composer must refuse rather than
    delete whatever happens to sit at that offset.
    """
    core = _read(CORE)
    first_marker = CHART_RENDERERS[0][0]
    broken = core.replace(first_marker, first_marker.replace("RC5", "RC9"), 1)
    assert broken != core, "the marker under test no longer occurs in CORE"
    with pytest.raises(CompositionError):
        compose(broken, _read(PART))
