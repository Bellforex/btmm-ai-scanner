"""The requested-context projection must maintain its bars exactly as the host does.

WHY THIS IS THE TEST THAT MATTERS
---------------------------------
P6's correctness rests on a composition that is already two-thirds proven:

1. the Pine P1 engine equals the production Python engine on M15
   (P1 closure, real-data parity);
2. the production Python engine is timeframe-agnostic -- it branches on no
   timeframe anywhere, proven on real re-timed bars for all six of BTRC's
   authority timeframes (`test_p1_p2_higher_timeframe_oracle`);
3. **the projection feeds those same P1 functions exactly what the host feeds
   them** -- same ATR recurrence, same window, same pruning, same frontier
   arguments, differing only in which context supplies `high`/`low`/`close`.

Only (3) is new in P6, and only (3) can be got wrong without any existing test
noticing. `test_p6_dev_source_contract` proves the projection CALLS the closed
functions and passes `q*` arrays; it does not prove the arrays were BUILT the
same way. A projection that pruned to a different length, seeded the Wilder ATR
differently, or computed `absFirst` off by one would still call the right
functions with the right-looking names and would still compile -- and would
produce subtly wrong swings on every higher timeframe.

So this module extracts the host's confirmed-bar maintenance and the
projection's, renames the projection's identifiers back to the host's, and
requires the operation sequences to be identical. The renaming map is written
out explicitly rather than derived, because a map that guessed (say, by
stripping a leading `q`) could silently equate two genuinely different
variables.

Deliberately NOT asserted here: displacement and the P2 view. The host computes
both in this block; the current P6 slice transports neither, and its banner says
so. When that slice lands, the corresponding sub-blocks belong in this file.
"""

from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
P6_DEV = REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"

#: Projection identifier -> host identifier. Explicit, so that two genuinely
#: different variables can never be equated by a stripping rule.
RENAME: dict[str, str] = {
    "qTr": "tr",
    "qAtrValue": "atrValue",
    "qAtrPrevFinal": "atrPrevFinal",
    "qAtrPrevClose": "atrPrevClose",
    "qAtrWarmSum": "atrWarmSum",
    "qAtrWarmCount": "atrWarmCount",
    "qBars": "confirmedBarCount",
    "qHigh": "wHigh",
    "qLow": "wLow",
    "qOpen": "wOpen",
    "qClose": "wClose",
    "qOpenT": "wOpenT",
    "qAvailT": "wAvailT",
    "qAtr": "wAtr",
    "qAbsFirst": "absFirst",
    "qpAbs": "pvAbs",
    "qpType": "pvType",
    "qpPrice": "pvPrice",
    "qpAtr": "pvAtr",
    "qpTie": "pvTie",
    "qSwings": "swings",
}

#: Lines the projection adds for diagnostics only. They touch no P1 input.
PROJECTION_ONLY = ("qFingerprint",)


def _source() -> str:
    return P6_DEV.read_text(encoding="utf-8")


def _translate(line: str) -> str:
    """Rename projection identifiers to host ones, longest first.

    Longest-first matters: `qAtr` is a prefix of `qAtrValue`, and renaming the
    short one first would corrupt the long one into `atrValue`-nonsense and make
    a real difference look like a match.
    """
    for src in sorted(RENAME, key=len, reverse=True):
        line = re.sub(rf"\b{src}\b", RENAME[src], line)
    return line


def _block(text: str, start: str, end: str, *, occurrence: int = 0) -> list[str]:
    """Normalised statements between two anchors, comments and blanks dropped."""
    positions = [m.start() for m in re.finditer(re.escape(start), text)]
    assert len(positions) > occurrence, f"anchor not found {occurrence}x: {start!r}"
    body = text[positions[occurrence] :]
    stop = body.index(end)
    lines = []
    for raw in body[:stop].splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("//"):
            continue
        lines.append(" ".join(stripped.split()))
    return lines


def _host_atr() -> list[str]:
    return _block(
        _source(), "float tr = f_trueRange(high, low, atrPrevClose)", "atrPrevClose"
    )


def _projection_atr() -> list[str]:
    return _block(
        _source(), "float qTr = f_trueRange(high, low, qAtrPrevClose)", "qAtrPrevClose"
    )


# ---------------------------------------------------------------------------
# (a) the Wilder ATR recurrence
# ---------------------------------------------------------------------------


def test_the_atr_recurrence_is_the_hosts() -> None:
    """A different seeding rule here would shift every ATR on every higher
    timeframe, and every swing that depends on an ATR tolerance with it."""
    host = [ln for ln in _host_atr()]
    proj = [_translate(ln) for ln in _projection_atr()]
    assert proj == host, f"\nhost: {host}\nproj: {proj}"


def test_the_atr_period_is_the_shared_constant() -> None:
    """Both sides must read C_ATR_PERIOD, not a local copy of its value."""
    text = _source()
    banner = text.index("// P6 — CROSS-TIMEFRAME SUBSTRATE")
    assert "C_ATR_PERIOD" in text[banner:]
    assert not re.search(r"C_P6_ATR_PERIOD\s*=", text[banner:])


# ---------------------------------------------------------------------------
# (b) the rolling window and its pruning
# ---------------------------------------------------------------------------


def _window_ops(text: str, *, projection: bool) -> list[str]:
    marker = "array.push(qHigh, high)" if projection else "array.push(wHigh, high)"
    end = "int qAbsFirst" if projection else "// ---- displacement"
    lines = _block(text, marker, end)
    out = []
    for line in lines:
        if projection and any(tok in line for tok in PROJECTION_ONLY):
            continue
        out.append(_translate(line) if projection else line)
    return out


def test_the_window_is_built_and_pruned_identically() -> None:
    """Same seven arrays, same push order, same prune bound. A missing shift
    would grow one array past the others and desynchronise every index the
    frontier hands to the swing detector."""
    text = _source()
    assert _window_ops(text, projection=True) == _window_ops(text, projection=False)


def test_both_prune_to_the_same_lookback_window() -> None:
    text = _source()
    banner = text.index("// P6 — CROSS-TIMEFRAME SUBSTRATE")
    for region in (text[:banner], text[banner:]):
        assert "while array.size(" in region
        assert "> lookbackWindow" in region, "prune bound must be the shared input"


# ---------------------------------------------------------------------------
# (c) the frontier hand-off
# ---------------------------------------------------------------------------


def test_abs_first_is_computed_the_same_way() -> None:
    """`absFirst` maps window slots to absolute bar numbers. Off by one and the
    frontier retires the wrong pivots -- silently, and only on some bars."""
    text = _source()
    host = re.search(r"int absFirst = ([^\n]+)", text)
    proj = re.search(r"int qAbsFirst = ([^\n]+)", text)
    assert host and proj
    assert _translate(proj.group(1).strip()) == host.group(1).strip()


def _call_sites(text: str, name: str) -> list[list[str]]:
    """Argument lists at CALL sites, excluding the function's own definition.

    A Pine definition reads `f_name(type a, type b) =>`, so it is excluded by
    the trailing `=>` rather than by position -- relying on the definition
    coming first would break the moment the file is reordered.
    """
    sites = []
    for match in re.finditer(rf"{name}\(([^)]*)\)(\s*=>)?", text):
        if match.group(2):  # the definition
            continue
        sites.append([a.strip() for a in match.group(1).split(",")])
    return sites


def test_the_frontier_and_detector_receive_the_same_arguments() -> None:
    """Same arrays, in the same order. Handing the detector the host's window
    from inside a requested context would project host data onto every
    timeframe, and nothing else in the suite would notice."""
    text = _source()
    for call in ("f_advancePivotFrontier", "f_detectSwings"):
        sites = _call_sites(text, call)
        assert len(sites) == 2, f"expected exactly a host and a projection call: {call}"
        host_args, proj_args = sites[0], [_translate(a) for a in sites[1]]
        assert proj_args == host_args, f"{call}\nhost: {host_args}\nproj: {proj_args}"


# ---------------------------------------------------------------------------
# The renaming map itself
# ---------------------------------------------------------------------------


def test_the_rename_map_is_injective() -> None:
    """Two projection variables mapping to one host variable would let a real
    divergence pass as a match."""
    assert len(set(RENAME.values())) == len(RENAME)


def test_every_projection_state_variable_is_mapped() -> None:
    """A new `var` in the projection that this map does not know about is a
    silent hole: it would be compared verbatim against the host and, if it
    happens not to appear in a compared line, never checked at all."""
    text = _source()
    section = text[text.index("// P6 — CROSS-TIMEFRAME SUBSTRATE") :]
    body = section[section.index("f_p6TfProjection()") : section.index("] = request.")]
    declared = set(re.findall(r"var\s+(?:array<\w+>|int|float|bool)\s+(\w+)", body))
    unmapped = {
        name
        for name in declared
        if name.startswith("q") and name not in RENAME and name not in PROJECTION_ONLY
    }
    assert unmapped == set(), f"unmapped projection state: {sorted(unmapped)}"
