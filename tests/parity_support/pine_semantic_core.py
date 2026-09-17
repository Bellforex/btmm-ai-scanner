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
    # RC3 POI type filters (presentation only)
    "grpTypes",
    "tBuyOb ",
    "tSellOb ",
    "tBuyFvg ",
    "tSellFvg ",
    "tB2S ",
    "tS2B ",
    "tBaseRally ",
    "tBaseDrop ",
    "tBullPw ",
    "tBearPw ",
    "tBullEng ",
    "tBearEng ",
    "tHammer ",
    "tShootStar ",
    "tMorning ",
    "tEvening ",
    "tSupport ",
    "tResist ",
    "p7zTypeOn = ",
)


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


def semantic_core(source: str) -> str:
    text = source.replace("\r\n", "\n")
    if _P7Z_START in text and _P7Z_END in text:
        start = text.index(_P7Z_START)
        start = text.rindex("\n", 0, start) + 1
        end = text.index(_P7Z_END)
        end = text.rindex("\n", 0, end) + 1
        text = text[:start] + text[end:]
    if _P7_RENDER in text:
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


#: PARITY-build capture instrumentation (log-only by construction) and the
#: USER-only review-time presentation input. Removing these from both builds
#: must leave byte-identical cores.
_CAPTURE_BLOCK_HEADS = (
    "if capRunMeta",
    "if p5cOn",
    "if p9DebugLog and barstate.islastconfirmedhistory",
    "f_capProbe() =>",
    "f_capCtx(",
    # P1/P2/P4 developer instrumentation behind Debug Mode (drawings, debug
    # table, debug data-window plots). The USER build no longer carries it.
    "if debugMode and show",
    "if barstate.islast and debugMode",
)
_CAPTURE_TOKENS = (
    "capBarK",
    "capHostFirst",
    "capHostN",
    "capHostCk",
    "capRunMeta",
    "capP5Compact",
    "capP5FromK",
    "capP5ToK",
    "grpCap",
    "f_capProbe",
    "p5cOn",
    "p5cBuf",
    "p7zAsOf",
    "log.info(",
    "debugMode",
    "p1Dbg",
    "showSwings",
    "showDisplacement",
    "showEqualLevels",
    "showSR ",
    "showTrendlines",
    "swingLabelObjs",
    "eqLineObjs",
    "srBoxObjs",
    "tlLineObjs",
    "dispFastNow",
    "maxDrawPerFamily = input.int(",
    "grpDev = ",
)


def capture_neutral_core(source: str) -> str:
    """The semantic core minus the script title, capture instrumentation and
    debug log statements. Equal for USER and PARITY exactly when the two
    builds compute the same semantics."""
    lines = [
        ln
        for ln in semantic_core(source).split("\n")
        if not ln.startswith("indicator(")
    ]
    kept: list[str] = []
    skip_indent: int | None = None
    for ln in lines:
        if skip_indent is not None:
            if _indent(ln) > skip_indent:
                continue
            skip_indent = None
        stripped = ln.strip()
        if stripped.startswith(_CAPTURE_BLOCK_HEADS) or (
            stripped.startswith("log.info(")
        ):
            skip_indent = _indent(ln)
            continue
        if any(token in ln for token in _CAPTURE_TOKENS):
            continue
        kept.append(ln)
    # Drop block heads left without a body (their whole body was capture code).
    out: list[str] = []
    for i, ln in enumerate(kept):
        nxt = kept[i + 1] if i + 1 < len(kept) else ""
        head = ln.rstrip().endswith("=>") or ln.strip().startswith(
            ("if ", "for ", "else")
        )
        if head and _indent(nxt) <= _indent(ln):
            continue
        out.append(ln)
    return "\n".join(out)
