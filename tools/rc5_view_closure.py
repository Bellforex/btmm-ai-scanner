"""Executable dependency closure for the proposed RC5 VIEW artifact.

VIEW is only a legitimate architecture if the code needed to DRAW the structure
overlay and the external trendline reaches nothing downstream of POI analysis.
A comment asserting that is worthless; this computes it.

CRITICAL: this file does NOT encapsulate the structure engine in functions. It
populates state from the top-level per-bar flow (`fwTls := tls`, `p3Events :=
p2bEvents`, ...). A closure over function bodies alone therefore MISSES the code
that produces everything the renderers read, and reports a tiny, false answer.

So the analyser also treats every top-level ASSIGNMENT to a reached variable as
a dependency, and pulls in the identifiers on that statement. It ignores scope
and over-approximates in both directions it can: a clean result is trustworthy,
a dirty one still needs a human look.

Run: python tools/rc5_view_closure.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

CORE = Path(__file__).resolve().parents[1] / (
    "tradingview/btmm_poi_btrc_scanner_rc5_user.pine"
)

#: Top-level declaration forms in this file's dialect.
_FUNC = re.compile(r"^(f_[A-Za-z0-9_]+)\s*\(.*\)\s*=>\s*$")
_TYPE = re.compile(r"^type\s+([A-Za-z0-9_]+)\s*$")
_CONST = re.compile(
    r"^(?:var\s+)?(?:int|float|bool|string|color|line|box|label|table)"
    r"(?:\[\])?\s+([A-Za-z0-9_]+)\s*=",
)
_VARDECL = re.compile(
    r"^var\s+(?:array|map|matrix)\s*<[^>]*>\s+([A-Za-z0-9_]+)\s*=",
)
_VARSIMPLE = re.compile(r"^var\s+[A-Za-z0-9_<>\[\], ]+?\s+([A-Za-z0-9_]+)\s*=")

#: The render regions VIEW would own, as composer markers already used by
#: `tools/rc5_compose.py`. These are the ROOTS of the closure.
VIEW_ROOTS = [
    (
        "    // ---- RC3 market-structure overlay (presentation only)",
        "                    array.set(msPrevHL, msHigh ? 0 : 1, sw.price)",
    ),
    ("    // ---- RC5 STRUCTURAL TRENDLINE LAYER", "                tlKeepA2 := 0"),
]

#: Symbols that must NOT be reachable from VIEW. If any appears, the extraction
#: is pulling semantic machinery across and the architecture is wrong.
#: NOTE `f_poi` is NOT usable as a forbidden prefix: `f_poiRange` is
#: `high - low` and `f_poiBody` is `abs(close - open)`. Those are candle
#: arithmetic that the structure engine legitimately needs; only the naming
#: suggests POI semantics. Detectors are named individually below.
FORBIDDEN_PREFIXES = (
    "f_poiDetect",  # POI detectors
    "f_rc5Ladder",  # reversal authority ranking
    "f_rc5Same",  # same-origin authority
    "f_rc5Zones",  # authority zone overlap
    "f_rc5IsRev",  # reversal family predicates
    "f_p5",  # P5 permission engine
    "f_p8",  # P8 alert engine
    "f_btmm",  # BTMM state
    "f_p7z",  # POI zone renderer
)
FORBIDDEN_EXACT = {
    "rc5Subordinate",
    "f_poiAppend",
    "f_poiEmit",
    "f_poiFind",
}

#: Reached only through single-letter in-flow locals (`ti`, `ty`, `di`, `on`)
#: that collide across scopes. The analyser is scope-blind by design, so these
#: are reported as INCONCLUSIVE rather than silently allowed or silently
#: failed. Resolving them needs either scope-aware parsing or -- definitively --
#: compiling a constructed VIEW and letting the Pine compiler answer.
INCONCLUSIVE = {"poiType", "poiDirection", "f_rc5PoiKind"}


#: Definitions INSIDE the per-bar flow, e.g. `        array<X> tls = f_detect(...)`.
#: They are indented, so a top-level-only index misses them -- and they are
#: exactly the link between a renderer's variable and the engine that fills it
#: (`fwTls := tls` is useless without knowing what produced `tls`).
_LOCAL = re.compile(
    r"^\s+(?:var\s+)?(?:int|float|bool|string|color|line|box|label|table"
    r"|array|map|matrix)\s*(?:<[^>]*>)?(?:\[\])?\s+([A-Za-z_][A-Za-z0-9_]*)\s*=[^=]",
)


def _declarations(lines: list[str]) -> dict[str, tuple[int, int]]:
    """name -> (start, end) for every definition, top-level or in-flow.

    In-flow locals are indexed too. That ignores scope and so OVER-approximates
    (one `ok` stands for every `ok` in the file), which is the safe direction:
    a closure that reaches no forbidden symbol really reaches none.
    """
    out: dict[str, tuple[int, int]] = {}
    for i, line in enumerate(lines):
        if line[:1] in (" ", "\t"):
            m = _LOCAL.match(line)
            if m:
                out.setdefault(m.group(1), (i, i))
            continue
        if not line or line.startswith("//"):
            continue
        name = None
        for pattern in (_FUNC, _TYPE, _VARDECL, _CONST, _VARSIMPLE):
            m = pattern.match(line)
            if m:
                name = m.group(1)
                break
        if name is None:
            continue
        end = i
        for j in range(i + 1, len(lines)):
            nxt = lines[j]
            if nxt.strip() and not nxt.startswith((" ", "\t")):
                break
            end = j
        out.setdefault(name, (i, end))
    return out


def _body(lines: list[str], span: tuple[int, int]) -> str:
    return "\n".join(lines[span[0] : span[1] + 1])


def _region(lines: list[str], first: str, last: str) -> str:
    starts = [i for i, line in enumerate(lines) if line.startswith(first)]
    if len(starts) != 1:
        raise SystemExit(f"root marker matched {len(starts)} lines: {first!r}")
    ends = [i for i in range(starts[0], len(lines)) if lines[i].startswith(last)]
    if not ends:
        raise SystemExit(f"root end marker never occurs: {last!r}")
    return "\n".join(lines[starts[0] : ends[0] + 1])


_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=")


def _producers(lines: list[str]) -> dict[str, list[str]]:
    """variable -> every statement that ASSIGNS it, at any indentation.

    This is what makes the closure honest. The structure engine runs in the
    per-bar flow, so `fwTls` is produced by a bare `fwTls := tls` statement
    that belongs to no function at all; a function-body closure cannot see it.
    """
    out: dict[str, list[str]] = {}
    for line in lines:
        m = _ASSIGN.match(line)
        if m:
            out.setdefault(m.group(1), []).append(line)
    return out


def closure() -> tuple[set[str], dict[str, tuple[int, int]], list[str]]:
    lines = CORE.read_text(encoding="utf-8").split("\n")
    decls = _declarations(lines)
    produced = _producers(lines)
    seeds = [_region(lines, a, b) for a, b in VIEW_ROOTS]

    word = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
    reached: set[str] = set()
    frontier: list[str] = []
    for text in seeds:
        for token in set(word.findall(text)):
            if token in decls:
                frontier.append(token)
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        reached.add(name)
        texts = [_body(lines, decls[name]), *produced.get(name, ())]
        for text in texts:
            for token in set(word.findall(text)):
                if token in decls and token not in reached:
                    frontier.append(token)
    return reached, decls, lines


def main() -> int:
    reached, decls, _lines = closure()
    forbidden = sorted(
        n
        for n in reached
        if (n.startswith(FORBIDDEN_PREFIXES) or n in FORBIDDEN_EXACT)
        and n not in INCONCLUSIVE
    )
    inconclusive = sorted(n for n in reached if n in INCONCLUSIVE)
    functions = sorted(n for n in reached if n.startswith("f_"))
    others = sorted(n for n in reached if not n.startswith("f_"))

    print(f"CORE top-level declarations : {len(decls)}")
    print(f"VIEW closure (over-approx)   : {len(reached)}")
    print(f"  functions : {len(functions)}")
    print(f"  types/vars/consts : {len(others)}")
    print(f"EXCLUDED from VIEW           : {len(decls) - len(reached)}")
    print()
    print("REACHABLE FUNCTIONS:")
    for n in functions:
        print(f"  {n}")
    print()
    if forbidden:
        print("FORBIDDEN SYMBOLS REACHABLE FROM VIEW -- ARCHITECTURE IS WRONG:")
        for n in forbidden:
            print(f"  {n}")
        return 1
    print("No forbidden symbol is reachable: no POI detector, no P5, no P8,")
    print("no reversal authority, no formation ownership, no BTMM, no POI renderer.")
    if inconclusive:
        print()
        print("INCONCLUSIVE (scope-blind collisions, NOT a clean bill of health):")
        for n in inconclusive:
            print(f"  {n}")
        print("The definitive check is compiling a constructed VIEW.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
