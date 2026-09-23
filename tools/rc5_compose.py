"""Compose the RC5 DIAGNOSTICS PANEL from the RC5 CORE source.

WHY THIS EXISTS
---------------
RC5 does not fit in one Pine script. Measured on the real TradingView compiler,
the faithful single-script build is 101,757 tokens against a 100,256 limit. The
release is therefore two scripts:

    RC5 CORE   market-space chart visuals   98,726 tokens
    RC5 PANEL  screen-space diagnostics     97,056 tokens

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

#: Chart-space renderers PANEL must not contain, as (first line, last line,
#: description). Both markers are matched by `startswith` and the first must
#: occur exactly once, so a rename fails loudly instead of silently cutting the
#: wrong region.
CHART_RENDERERS: list[tuple[str, str, str]] = [
    (
        "    // ---- RC3 market-structure overlay (presentation only)",
        "                    array.set(msPrevHL, msHigh ? 0 : 1, sw.price)",
        "structure overlay (BOS/CHOCH + HH/HL/LH/LL)",
    ),
    (
        "    // ---- RC5 STRUCTURAL TRENDLINE LAYER",
        "                tlKeepA2 := 0",
        "structural trendline layer",
    ),
    (
        "    // P7-Z — POI zone visualization (informational, presentation-only).",
        "                        box.set_text(array.get(p7zBoxes, slot), p7zBoxTxt)",
        "P7-Z zone boxes and labels",
    ),
]

#: PANEL carries its own study title. Both scripts are attached to the same
#: chart during QA, and two legend rows reading "[RC5 USER]" is a trap: it is
#: impossible to tell which one drew what, or which version each is on.
CORE_TITLE = '"BTMM + POI + BTRC Scanner [RC5 USER]"'
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
        current = PANEL.read_bytes().decode("utf-8")
        if current != composed:
            print("RC5 PANEL is out of date with RC5 CORE; run tools/rc5_compose.py")
            return 1
        print("RC5 PANEL matches RC5 CORE")
        return 0

    PANEL.write_bytes(composed.encode("utf-8"))
    print(f"wrote {PANEL.relative_to(REPO)} ({len(composed.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
