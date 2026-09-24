"""Compose the RC5 PANEL and the RC5 VIEW from the RC5 CORE source.

WHY THIS EXISTS
---------------
RC5 does not fit in one Pine script. Measured on the real TradingView compiler,
the faithful single-script build is 101,757 tokens against a 100,256 limit. The
release is therefore two scripts:

    RC5 CORE   scanner semantics + POI and trendline drawing   98,335 tokens
    RC5 VIEW   HH/HL/LH/LL and BOS/CHOCH drawing only
    RC5 PANEL  screen-space diagnostics

VIEW is the newest of the three and exists for capacity: the structure overlay
cost CORE 1,036 measured tokens, and it is the only renderer that can leave,
because it reads `p3Swings` / `p3Events` and nothing downstream of them. The
TRENDLINE renderer deliberately stayed in CORE -- its one-visible-line winner
reads `rc5TlHit`, which the qualified sweep engine writes from POI references,
so a structure-only VIEW could not pick the same line.

Pine cannot read another script's private state, so PANEL has to compute the
same semantics CORE does. That is a drift hazard: two files, one meaning, and
nothing but discipline keeping them equal. Hand-copying the engine into a second
file would make the hazard permanent.

So PANEL is not written. It is COMPOSED. CORE is the one canonical semantic
source; this module applies a fixed, declarative transform to it:

    PANEL = CORE
              - the chart-space renderers (structure overlay, structural
                trendlines, P7-Z zone boxes, the BTMM cycle marker)
              + the screen-space diagnostics from the presentation part file

Every semantic line in PANEL is therefore literally CORE's own line, byte for
byte, because it IS CORE's line. A semantic change is authored once, in CORE,
and regenerating PANEL carries it across. `tests/unit/test_rc5_panel_composition.py`
fails if the committed PANEL is not exactly what this module produces from the
committed CORE, so the two cannot silently diverge.

WHAT THIS MODULE MAY NOT DO
---------------------------
It may not compute, simplify or reinterpret anything. Its only edits are:
delete a named chart-renderer region, and insert presentation text that lives in
`tradingview/rc5_panel_presentation.pine`. If a change needs more than that, it
belongs in CORE, not here.

The PARITY build is not composed here yet; it still descends from its own
lineage, and saying otherwise would overstate what is wired.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CORE = REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_user.pine"
PART = REPO / "tradingview" / "rc5_panel_presentation.pine"
PANEL = REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_panel.pine"
VIEW = REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_view.pine"
VIEW_PART = REPO / "tradingview" / "rc5_view_presentation.pine"

#: Chart-space renderers PANEL must not contain, as (first line, last line,
#: description). Both markers are matched by `startswith` and the first must
#: occur exactly once, so a rename fails loudly instead of silently cutting the
#: wrong region.
CHART_RENDERERS: list[tuple[str, str, str]] = [
    (
        "    // ---- RC5 STRUCTURAL TRENDLINE LAYER",
        "                tlKeepA2 := 0",
        "structural trendline layer",
    ),
    (
        "    // P7-Z — POI zone visualization (informational, presentation-only).",
        # was `box.set_text` until the presentation compaction removed it: the
        # text cannot change for an existing box, because a POI's type is
        # immutable once registered.
        "                        box.set_right(array.get(p7zBoxes, slot), p7zRightEdge)",
        "P7-Z zone boxes and labels",
    ),
]

#: PANEL carries its own study title. Both scripts are attached to the same
#: chart during QA, and two legend rows reading "[RC5 USER]" is a trap: it is
#: impossible to tell which one drew what, or which version each is on.
CORE_TITLE = '"BTMM + POI + BTRC Scanner [RC5 USER]"'
VIEW_TITLE = '"BTMM + POI + BTRC Scanner [RC5 VIEW]"'
PANEL_TITLE = '"BTMM + POI + BTRC Scanner [RC5 PANEL]"'

#: The BTMM cycle marker is a single chart plot, so it is replaced rather than
#: cut as a region.
BTMM_MARKER = (
    'plotshape(dspBtmm and fwCyc > 0, "BTMM cycle valid", shape.diamond, '
    "location.bottom, color.orange, size = size.tiny)"
)


class CompositionError(RuntimeError):
    """A marker did not match exactly once. Never guess; fail and say where."""


def _cut_regions(lines: list[str]) -> list[str]:
    for first, last, note in CHART_RENDERERS:
        starts = [i for i, line in enumerate(lines) if line.startswith(first)]
        if len(starts) != 1:
            raise CompositionError(
                f"{note}: start marker matched {len(starts)} lines, expected 1"
            )
        ends = [i for i in range(starts[0], len(lines)) if lines[i].startswith(last)]
        if not ends:
            raise CompositionError(
                f"{note}: end marker never occurs after the start marker"
            )
        lines = [
            *lines[: starts[0]],
            f"    // RC5 PANEL: {note} is drawn by RC5 CORE.",
            *lines[ends[0] + 1 :],
        ]
    return lines


def _parse_part(text: str) -> tuple[list[tuple[str, str]], tuple[str, str] | None]:
    """Read the presentation part file into (insert-before blocks, marker block)."""
    inserts: list[tuple[str, str]] = []
    marker: tuple[str, str] | None = None
    anchor: list[str] = []
    body: list[str] = []
    mode: str | None = None

    for line in text.split("\n"):
        if line.startswith("//#INSERT-BEFORE"):
            mode, anchor, body = "insert", [], []
        elif line.startswith("//#REPLACE"):
            mode, anchor, body = "marker", [], []
        elif line.startswith("//#ANCHOR "):
            anchor.append(line[len("//#ANCHOR ") :])
        elif line.startswith("//#END"):
            if mode == "insert":
                inserts.append(("\n".join(anchor) + "\n", "\n".join(body) + "\n"))
            elif mode == "marker":
                marker = ("\n".join(anchor) + "\n", "\n".join(body) + "\n")
            mode = None
        elif mode is not None:
            body.append(line)

    return inserts, marker


def compose(core_text: str, part_text: str) -> str:
    """CORE source + presentation part -> PANEL source. Pure; no file access."""
    newline = "\r\n" if "\r\n" in core_text else "\n"
    core = core_text.replace("\r\n", "\n")

    panel = "\n".join(_cut_regions(core.split("\n")))

    # the banner line that sat above the P7-Z region is now orphaned
    panel = panel.replace(
        "    // =========================================================================\n"
        "    // RC5 PANEL: P7-Z zone boxes and labels is drawn by RC5 CORE.\n",
        "    // RC5 PANEL: P7-Z zone boxes and labels are drawn by RC5 CORE.\n",
        1,
    )

    if panel.count(CORE_TITLE) < 1:
        raise CompositionError("the CORE study title was not found")
    panel = panel.replace(CORE_TITLE, PANEL_TITLE, 1)

    if panel.count(BTMM_MARKER) != 1:
        raise CompositionError("the BTMM cycle marker did not occur exactly once")
    panel = panel.replace(
        BTMM_MARKER,
        "// RC5 PANEL: the BTMM cycle marker is a chart visual and belongs to CORE.",
        1,
    )

    inserts, marker = _parse_part(part_text.replace("\r\n", "\n"))
    for anchor, block in inserts:
        found = panel.count(anchor)
        if found != 1:
            raise CompositionError(
                f"anchor matched {found} times, expected 1:\n{anchor}"
            )
        panel = panel.replace(anchor, block + anchor, 1)

    if marker is None:
        raise CompositionError("the presentation part declares no //#REPLACE block")
    marker_lines, block = marker
    if panel.count(marker_lines) != 1:
        raise CompositionError(f"replace anchor matched != 1 time:\n{marker_lines}")
    panel = panel.replace(marker_lines, block, 1)

    return panel.replace("\n", newline) if newline == "\r\n" else panel


# ---------------------------------------------------------------------------
# RC5 VIEW — structure presentation only
# ---------------------------------------------------------------------------
#
# VIEW draws HH/HL/LH/LL and BOS/CHOCH and NOTHING else. It is CORE with every
# non-structural region cut, which is why it is generated rather than written:
# the structure engine is not function-encapsulated, it runs inline in the
# per-bar flow, so the regions are statement ranges and must be marked.
#
# The trendline renderer deliberately STAYS IN CORE. Its one-visible-line winner
# reads `rc5TlHit`, which the qualified sweep/reaction engine writes from POI
# references -- so a structure-only VIEW cannot reproduce the same winner, and
# importing the sweep engine would make VIEW a second scanner. That is a
# semantic boundary, not a capacity choice.

#: Marker pairs delimiting what VIEW removes. Markers, never line numbers.
VIEW_CUT_MARKERS = (
    "NON_STRUCTURAL_ENGINES",
    "MAIN_DISPLACEMENT",
    "MAIN_NON_STRUCTURAL",
    "EVERYTHING_BELOW_STRUCTURE",
)


def _cut_marked(lines: list[str], name: str) -> list[str]:
    begin = [i for i, x in enumerate(lines) if x.strip() == f"//#VIEW-CUT-BEGIN {name}"]
    end = [i for i, x in enumerate(lines) if x.strip() == f"//#VIEW-CUT-END {name}"]
    if len(begin) != 1 or len(end) != 1:
        raise CompositionError(
            f"{name}: expected exactly one BEGIN and one END marker, "
            f"got {len(begin)} and {len(end)}"
        )
    if end[0] < begin[0]:
        raise CompositionError(f"{name}: END marker precedes BEGIN marker")
    return [*lines[: begin[0]], *lines[end[0] + 1 :]]


VIEW_RENDER_ANCHOR = "    //#VIEW-RENDER-ANCHOR"


def compose_view(core: str, part: str) -> str:
    """CORE minus every non-structural region, with the renderer spliced in.

    CORE no longer carries the structure overlay at all -- it lives in
    `rc5_view_presentation.pine` and is spliced back here, so there is exactly
    one copy of it in the repository and CORE cannot draw it.
    """
    lines = core.split("\n")
    for name in VIEW_CUT_MARKERS:
        lines = _cut_marked(lines, name)
    anchors = [i for i, x in enumerate(lines) if x.startswith(VIEW_RENDER_ANCHOR)]
    if len(anchors) != 1:
        raise CompositionError(
            f"VIEW render anchor matched {len(anchors)} lines, expected 1"
        )
    body = [
        x for x in part.split("\n") if not x.lstrip().startswith("//") and x.strip()
    ]
    if not body:
        raise CompositionError("VIEW presentation part carried no renderer")
    lines = [*lines[: anchors[0]], *body, *lines[anchors[0] + 1 :]]
    out = "\n".join(lines)
    if out.count(CORE_TITLE) != 1:
        raise CompositionError("CORE title marker did not match exactly once")
    return out.replace(CORE_TITLE, VIEW_TITLE)


def compose_from_repo() -> str:
    return compose(
        CORE.read_bytes().decode("utf-8"),
        PART.read_bytes().decode("utf-8"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="exit non-zero if the committed PANEL is not what CORE composes to",
    )
    args = parser.parse_args()

    composed = compose_from_repo()
    if args.check:
        stale = []
        if PANEL.read_bytes().decode("utf-8") != composed:
            stale.append("PANEL")
        view = compose_view(
            CORE.read_bytes().decode("utf-8"), VIEW_PART.read_bytes().decode("utf-8")
        )
        if not VIEW.exists() or VIEW.read_bytes().decode("utf-8") != view:
            stale.append("VIEW")
        if stale:
            print(
                f"RC5 {' and '.join(stale)} out of date with RC5 CORE; "
                "run tools/rc5_compose.py"
            )
            return 1
        print("RC5 PANEL and VIEW match RC5 CORE")
        return 0

    PANEL.write_bytes(composed.encode("utf-8"))
    print(f"wrote {PANEL.relative_to(REPO)} ({len(composed.splitlines())} lines)")
    view = compose_view(
        CORE.read_bytes().decode("utf-8"), VIEW_PART.read_bytes().decode("utf-8")
    )
    VIEW.write_bytes(view.encode("utf-8"))
    print(f"wrote {VIEW.relative_to(REPO)} ({len(view.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
