"""RC1 mechanical semantic-equivalence gate: the P10 release candidate vs.
the closed P9 DEV source it was built from (MEGA-AUTONOMOUS-30 Phase 9/10).

RC1 is deliberately the SIMPLEST possible release build: every debug toggle
in P9 DEV (`debugMode`/P1 Debug Mode, `showTrendlines`, `p8DebugLog`,
`p9DebugLog`) already defaults to `false`, and the P7-Z release-facing
defaults (`p7zShowZones`/`p7zShowLabels`/`p7zMaxVisibleZones`) already match
the required release presentation (True/True/12) -- verified directly
against the source before this file was written. No debug code needed
stripping and no semantic path needed touching, so RC1 is P9 DEV with
ONLY the `indicator()` title changed. This test proves that mechanically,
the same way the P8Z-vs-P9 and P8Z-vs-P8-DEV equivalence gates already did
for earlier phases, rather than asserting it in prose alone.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P9_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p9_dev.pine"
RC1 = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc1.pine"

_PLOT_FAMILY = re.compile(r"^(?:plot|plotshape|plotchar)\(", re.M)
_REQUEST_SECURITY = re.compile(r"request\.security\(")
_BOX_NEW = re.compile(r"\bbox\.new\(")
_LABEL_NEW = re.compile(r"\blabel\.new\(")
_LINE_NEW = re.compile(r"\bline\.new\(")
_TABLE_NEW = re.compile(r"\btable\.new\(")
_ALERTCONDITION = re.compile(r"^\s*alertcondition\(", re.M)
_ALERT_CALL = re.compile(r"^\s*alert\(", re.M)

#: The exact release-facing defaults required by the P10 brief Phase 6 --
#: asserted directly against RC1's own source so a future edit that
#: silently changes a release default is caught here, not just in prose.
_RELEASE_DEFAULTS = (
    (re.compile(r'p7zShowZones\s*=\s*input\.bool\(true,'), "p7zShowZones must default true"),
    (re.compile(r'p7zShowLabels\s*=\s*input\.bool\(true,'), "p7zShowLabels must default true"),
    (
        re.compile(r'p7zMaxVisibleZones\s*=\s*input\.int\(12,'),
        "p7zMaxVisibleZones must default 12",
    ),
)

#: Every debug/diagnostic toggle in the RC lineage -- all must default off
#: in a release build. Matched by variable name; the exact default-false
#: pattern is asserted per-toggle below.
_DEBUG_TOGGLES = (
    "debugMode",
    "showTrendlines",
    "p8DebugLog",
    "p9DebugLog",
)


def _diff_lines() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--no-index", "--unified=0", str(P9_DEV), str(RC1)],
        capture_output=True,
        text=True,
        cwd=_REPO,
    )
    assert result.returncode in (0, 1), result.stderr
    return result.stdout.splitlines()


def _removed_and_added(lines: list[str]) -> tuple[list[str], list[str]]:
    removed = [line[1:] for line in lines if line.startswith("-") and not line.startswith("---")]
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    return removed, added


def test_rc1_exists_as_a_separate_script_from_p9_dev() -> None:
    assert P9_DEV.exists()
    assert RC1.exists()
    assert P9_DEV.read_bytes() != RC1.read_bytes()


def test_the_only_diff_is_the_indicator_title() -> None:
    """RC1 is P9 DEV with ONLY the `indicator()` title string changed --
    the strongest possible equivalence proof available: a single-line
    diff, not merely "no forbidden pattern found"."""
    removed, added = _removed_and_added(_diff_lines())
    assert len(removed) == 1, removed
    assert len(added) == 1, added
    assert "P9 DEV" in removed[0]
    assert "RC1" in added[0]
    before = removed[0].replace("P9 DEV", "RC1")
    assert before == added[0]


def test_zero_resource_count_drift() -> None:
    p9_source = P9_DEV.read_text(encoding="utf-8")
    rc1_source = RC1.read_text(encoding="utf-8")
    assert len(_PLOT_FAMILY.findall(rc1_source)) == len(_PLOT_FAMILY.findall(p9_source)) == 63
    assert (
        len(_REQUEST_SECURITY.findall(rc1_source)) == len(_REQUEST_SECURITY.findall(p9_source)) == 6
    )
    assert len(_BOX_NEW.findall(rc1_source)) == len(_BOX_NEW.findall(p9_source)) == 2
    assert len(_LABEL_NEW.findall(rc1_source)) == len(_LABEL_NEW.findall(p9_source)) == 2
    assert len(_LINE_NEW.findall(rc1_source)) == len(_LINE_NEW.findall(p9_source)) == 2
    assert len(_TABLE_NEW.findall(rc1_source)) == len(_TABLE_NEW.findall(p9_source)) == 3


def test_alert_mechanism_unchanged() -> None:
    p9_source = P9_DEV.read_text(encoding="utf-8")
    rc1_source = RC1.read_text(encoding="utf-8")
    assert not _ALERTCONDITION.search(rc1_source)
    assert len(_ALERT_CALL.findall(rc1_source)) == len(_ALERT_CALL.findall(p9_source)) == 5


def test_release_facing_visual_defaults_are_on() -> None:
    """Phase 6: the scanner must open with visible POI zones/labels at the
    max-12 cap -- verified as an RC1 source-level invariant, not just a
    one-time Settings-dialog screenshot."""
    source = RC1.read_text(encoding="utf-8")
    for pattern, message in _RELEASE_DEFAULTS:
        assert pattern.search(source), message


def test_all_debug_toggles_default_off() -> None:
    source = RC1.read_text(encoding="utf-8")
    for name in _DEBUG_TOGGLES:
        match = re.search(rf"{name}\s*=\s*input\.bool\((true|false),", source)
        assert match is not None, f"could not find input.bool default for {name!r}"
        assert match.group(1) == "false", f"{name} must default to false in a release build"


def test_rc1_title_does_not_imply_production_or_profitability_claims() -> None:
    """Phase 8: the release title must not imply PRODUCTION APPROVED,
    PROFITABLE, or LIVE TRADING."""
    source = RC1.read_text(encoding="utf-8")
    match = re.search(r'indicator\("([^"]+)"', source)
    assert match is not None
    title = match.group(1).lower()
    for forbidden in ("production", "profit", "live trading", "approved"):
        assert forbidden not in title, (title, forbidden)
