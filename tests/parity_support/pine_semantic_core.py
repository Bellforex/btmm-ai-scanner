"""Extract the SEMANTIC CORE of the RC3 USER Pine build.

Test/validation tooling only. The semantic core is every executable line of
the script EXCEPT the presentation layer: the P7-Z zone drawing block, the P7
panel render, the RC3 display-layer inputs and overlays, the display-only
input titles and the debug-only P8 event log (which lives in the PARITY build).
Comments and blank lines are dropped.

Two builds whose cores are equal compute the same P1-P6 values, P3 registry
and lifecycle, P4 BTMM state, P5 assessments and P8 alert conditions; only
what is drawn (and the USER-side debug log) can differ. This is a source-level
proof, not a runtime capture, and is stated as such wherever it is used.
"""

from __future__ import annotations

import hashlib

__all__ = ["semantic_core", "semantic_core_sha256"]

_P7Z_START = "P7-Z — POI zone visualization"
_P7Z_END = "P9 — full-system integration trace"
_P7_RENDER = "P7 — panel render."

#: Statements whose whole indented body is presentation or debug logging.
_BLOCK_HEADS = ("if dspMs", "if p8DebugLog")

#: Single presentation / display-title lines.
_LINE_PREFIXES = (
    "grpView",
    "dspFvg",
    "dspSR",
    "dspMs",
    "dspBtmm",
    "var array<line>  msLines",
    "var array<label> msLabels",
    "float p4dGate",
    "float p4dForm",
    "plotshape(dspBtmm",
    "p7ShowUi ",
    "p7ShowActivePois ",
    "p7zShowZones ",
    "p7zShowLabels ",
    "p8DebugLog ",
)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def semantic_core(source: str) -> str:
    text = source.replace("\r\n", "\n")
    start = text.index(_P7Z_START)
    start = text.rindex("\n", 0, start) + 1
    end = text.index(_P7Z_END)
    end = text.rindex("\n", 0, end) + 1
    text = text[:start] + text[end:]
    text = text[: text.rindex("\n", 0, text.index(_P7_RENDER)) + 1]

    out: list[str] = []
    skip_indent: int | None = None
    for raw in text.split("\n"):
        code = raw.split("//")[0].rstrip() if "//" in raw else raw.rstrip()
        if '"' in raw and "//" in raw:
            code = raw.rstrip()  # never cut inside a string literal
            if code.lstrip().startswith("//"):
                code = ""
        if not code.strip():
            continue
        if skip_indent is not None:
            if _indent(code) > skip_indent:
                continue
            skip_indent = None
        stripped = code.strip()
        if stripped.startswith(_BLOCK_HEADS):
            skip_indent = _indent(code)
            continue
        if stripped.startswith(_LINE_PREFIXES):
            continue
        out.append(code)
    return "\n".join(out)


def semantic_core_sha256(source: str) -> str:
    return hashlib.sha256(semantic_core(source).encode("utf-8")).hexdigest()
