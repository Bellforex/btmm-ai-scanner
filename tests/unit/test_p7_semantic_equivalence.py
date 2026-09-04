"""P7 mechanical semantic-equivalence gate: P7 DEV vs. the closed P5 DEV.

WHAT THIS PROVES
-----------------
P7 is presentation-only (per its own governing brief): it may add tables,
labels, and display-formatting code, but must never modify or delete a line
of the already-closed P1-P6 semantic source, and must never introduce a
second decision engine. This is checked MECHANICALLY here rather than
trusted from a manual diff read:

1. Every line the unified diff REMOVES from P5 DEV's side is the indicator
   title line -- i.e. the diff is a pure insertion plus one title rename,
   never a modification or deletion of existing semantic code.
2. Every `:=` reassignment introduced by the diff targets a `p7`-prefixed
   variable -- P7 never writes back into a P1-P6 variable, even to "just
   copy" a value (it reads P1-P6 state, but only ever assigns into its own
   namespace).
3. The Pine resource budget P7 inherited is unchanged: the same plot count,
   the same `request.security` call count as P5 DEV, and zero
   `alertcondition(` calls (P8 alerts have not started).

WHY THIS IS A SEPARATE FILE FROM `test_p5_resource_budget.py`
------------------------------------------------------------------
That module's claim is P5's OWN budget (P5 adds zero plots vs. P6). This
module's claim is P7's relationship to P5 specifically: an additive diff,
not a resource regression, and not a semantic regression -- a different
pair of scripts and a different property.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P5_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p5_dev.pine"
P7_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p7_dev.pine"

_PLOT_FAMILY = re.compile(r"^(?:plot|plotshape|plotchar)\(", re.M)
_REQUEST_SECURITY = re.compile(r"request\.security\(")
#: A real call statement, not a mention inside a `//` comment (this module's
#: own docstring-style comments name `alertcondition()` when explaining what
#: P7 must NOT add).
_ALERTCONDITION = re.compile(r"^\s*alertcondition\(", re.M)
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=")


def _diff_lines() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--no-index", "--unified=0", str(P5_DEV), str(P7_DEV)],
        capture_output=True,
        text=True,
        cwd=_REPO,
    )
    # `git diff --no-index` exits 1 when the files differ (expected here, not
    # an error) and >1 only on a real failure (e.g. a missing file).
    assert result.returncode in (0, 1), result.stderr
    return result.stdout.splitlines()


def _removed_and_added(lines: list[str]) -> tuple[list[str], list[str]]:
    removed = [
        line[1:] for line in lines if line.startswith("-") and not line.startswith("---")
    ]
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    return removed, added


def test_p7_dev_exists_as_a_separate_script_from_p5_dev() -> None:
    assert P5_DEV.exists()
    assert P7_DEV.exists()
    assert P5_DEV.read_bytes() != P7_DEV.read_bytes()


def test_every_removed_line_is_the_indicator_title() -> None:
    """The only line P7 DEV's diff REMOVES from P5 DEV's side must be the
    `indicator(...)` title -- anything else removed would mean an existing
    P1-P6 line was modified or deleted, which P7 must never do."""
    removed, _added = _removed_and_added(_diff_lines())
    non_title_removals = [line for line in removed if "P5 DEV" not in line]
    assert non_title_removals == [], non_title_removals


def test_title_is_the_only_thing_changed_on_that_line() -> None:
    removed, added = _removed_and_added(_diff_lines())
    title_removed = [line for line in removed if "P5 DEV" in line]
    title_added = [line for line in added if "P7 DEV" in line]
    assert len(title_removed) == 1
    assert len(title_added) == 1
    # Same `indicator(...)` call, only the bracketed suffix in the title
    # string differs.
    before = title_removed[0].replace("P5 DEV", "P7 DEV")
    assert before == title_added[0]


def test_every_added_reassignment_targets_a_p7_variable() -> None:
    """P7 may READ any P1-P6 variable, but every `:=` it introduces must
    write into its own `p7`-prefixed namespace -- never back into a P1-P6
    variable, even to copy a value verbatim."""
    _removed, added = _removed_and_added(_diff_lines())
    non_p7_targets = []
    for line in added:
        match = _ASSIGN.match(line)
        if match and not match.group(1).startswith("p7"):
            non_p7_targets.append(line)
    assert non_p7_targets == [], non_p7_targets


def test_plot_family_count_unchanged() -> None:
    p5_count = len(_PLOT_FAMILY.findall(P5_DEV.read_text(encoding="utf-8")))
    p7_count = len(_PLOT_FAMILY.findall(P7_DEV.read_text(encoding="utf-8")))
    assert p7_count == p5_count == 63


def test_request_security_count_unchanged() -> None:
    p5_count = len(_REQUEST_SECURITY.findall(P5_DEV.read_text(encoding="utf-8")))
    p7_count = len(_REQUEST_SECURITY.findall(P7_DEV.read_text(encoding="utf-8")))
    assert p7_count == p5_count == 6


def test_no_alertcondition_calls_p8_not_started() -> None:
    assert not _ALERTCONDITION.search(P7_DEV.read_text(encoding="utf-8"))


#: Every closed P5 decision function -- T1-T5, alignment, the eight
#: component-score formulas, the aggregator/permission/lifecycle. P7's own
#: label-lookup section (between these two anchors, both exact substrings of
#: the file) must call none of them: label functions consume an
#: already-computed result, they never compute one.
_DECISION_FUNCTIONS = (
    "f_p5T1(",
    "f_p5T2(",
    "f_p5T3Mom(",
    "f_p5T3Brk(",
    "f_p5T3Pb(",
    "f_p5T4Session(",
    "f_p5T4Vol(",
    "f_p5T5Global(",
    "f_p5Alignment(",
    "f_p5TrendScore(",
    "f_p5RegimeScore(",
    "f_p5MomentumScoreConfluence(",
    "f_p5PoiScoreConfluence(",
    "f_p5BtmmScoreConfluence(",
    "f_p5LiquidityScoreConfluence(",
    "f_p5WeightedFinal(",
    "f_p5Permission(",
    "f_p5Lifecycle(",
)

_LABEL_SECTION_START = 'grpP7 = "P7 — Scanner UI"'
_LABEL_SECTION_END = (
    "// Active-POI evaluation loop — additive to the P3 registry, per the project's"
)


def test_p7_label_functions_call_no_decision_function() -> None:
    """The `f_p7*` label-lookup block (bounded by two exact-text anchors
    that existed before and after P7's insert) must contain none of the
    closed P5 decision-function call sites -- these functions may only
    switch on an already-computed integer code."""
    source = P7_DEV.read_text(encoding="utf-8")
    start = source.index(_LABEL_SECTION_START)
    end = source.index(_LABEL_SECTION_END, start)
    label_section = source[start:end]
    assert "f_p7DirLabel(" in label_section  # sanity: the anchors bound real content
    for decision_fn in _DECISION_FUNCTIONS:
        assert decision_fn not in label_section, decision_fn
