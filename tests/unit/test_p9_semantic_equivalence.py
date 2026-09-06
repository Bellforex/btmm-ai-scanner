"""P9 mechanical semantic-equivalence gate: P9 DEV vs. the closed P8Z DEV.

Mirrors `test_p8z_semantic_equivalence.py`'s own method exactly: P9 must be
instrumentation-only, adding a single debug-gated integration-trace log
block on top of the closed P1-P8-Z engine, never modifying a line of it and
never introducing a second detector, ranking, decision, or event engine.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P8Z_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p8z_dev.pine"
P9_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p9_dev.pine"

_PLOT_FAMILY = re.compile(r"^(?:plot|plotshape|plotchar)\(", re.M)
_REQUEST_SECURITY = re.compile(r"request\.security\(")
_ALERTCONDITION = re.compile(r"^\s*alertcondition\(", re.M)
_ALERT_CALL = re.compile(r"^\s*alert\(", re.M)
_BOX_NEW = re.compile(r"\bbox\.new\(")
_LABEL_NEW = re.compile(r"\blabel\.new\(")
_LINE_NEW = re.compile(r"\bline\.new\(")
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=")

_FORBIDDEN_PAYLOAD_TERMS = (
    "entry",
    "stopLoss",
    "stop_loss",
    "takeProfit",
    "take_profit",
    "positionSize",
    "position_size",
    "lotSize",
    "riskPercent",
    "strategy.entry",
    "strategy.exit",
    "strategy.order",
)


def _diff_lines() -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--no-index", "--unified=0", str(P8Z_DEV), str(P9_DEV)],
        capture_output=True,
        text=True,
        cwd=_REPO,
    )
    assert result.returncode in (0, 1), result.stderr
    return result.stdout.splitlines()


def _removed_and_added(lines: list[str]) -> tuple[list[str], list[str]]:
    removed = [
        line[1:]
        for line in lines
        if line.startswith("-") and not line.startswith("---")
    ]
    added = [
        line[1:]
        for line in lines
        if line.startswith("+") and not line.startswith("+++")
    ]
    return removed, added


def test_p9_dev_exists_as_a_separate_script_from_p8z_dev() -> None:
    assert P8Z_DEV.exists()
    assert P9_DEV.exists()
    assert P8Z_DEV.read_bytes() != P9_DEV.read_bytes()


def test_every_removed_line_is_the_indicator_title() -> None:
    removed, _added = _removed_and_added(_diff_lines())
    non_title_removals = [line for line in removed if "P8Z DEV" not in line]
    assert non_title_removals == [], non_title_removals


def test_title_is_the_only_thing_changed_on_that_line() -> None:
    removed, added = _removed_and_added(_diff_lines())
    title_removed = [line for line in removed if "P8Z DEV" in line]
    title_added = [line for line in added if "P9 DEV" in line]
    assert len(title_removed) == 1
    assert len(title_added) == 1
    before = title_removed[0].replace("P8Z DEV", "P9 DEV")
    assert before == title_added[0]


def test_every_added_reassignment_targets_a_p9_variable() -> None:
    """P9 may READ any P1-P8Z variable (including `p7PoiIdx`/`poiZoneTop`/
    `p7zBoxPoiIdx`/etc. already exposed) but every `:=` it introduces must
    write into its own `p9`-prefixed namespace."""
    _removed, added = _removed_and_added(_diff_lines())
    non_p9_targets = []
    for line in added:
        match = _ASSIGN.match(line)
        if match and not match.group(1).startswith("p9"):
            non_p9_targets.append(line)
    assert non_p9_targets == [], non_p9_targets


def test_zero_new_plots_boxes_labels_lines_requests() -> None:
    p8z_source = P8Z_DEV.read_text(encoding="utf-8")
    p9_source = P9_DEV.read_text(encoding="utf-8")
    assert (
        len(_PLOT_FAMILY.findall(p9_source))
        == len(_PLOT_FAMILY.findall(p8z_source))
        == 63
    )
    assert (
        len(_REQUEST_SECURITY.findall(p9_source))
        == len(_REQUEST_SECURITY.findall(p8z_source))
        == 6
    )
    assert len(_BOX_NEW.findall(p9_source)) == len(_BOX_NEW.findall(p8z_source)) == 2
    assert (
        len(_LABEL_NEW.findall(p9_source)) == len(_LABEL_NEW.findall(p8z_source)) == 2
    )
    assert len(_LINE_NEW.findall(p9_source)) == len(_LINE_NEW.findall(p8z_source)) == 2


def test_alert_mechanism_unchanged() -> None:
    p8z_source = P8Z_DEV.read_text(encoding="utf-8")
    p9_source = P9_DEV.read_text(encoding="utf-8")
    assert not _ALERTCONDITION.search(p9_source)
    assert (
        len(_ALERT_CALL.findall(p9_source)) == len(_ALERT_CALL.findall(p8z_source)) == 5
    )


def test_no_forbidden_execution_terms_anywhere_in_the_p9_addition() -> None:
    _removed, added = _removed_and_added(_diff_lines())
    code_lines = [line for line in added if not line.strip().startswith("//")]
    added_text = "\n".join(code_lines)
    for term in _FORBIDDEN_PAYLOAD_TERMS:
        assert term not in added_text, (
            f"forbidden execution-related term found in P9 code: {term!r}"
        )


#: Every closed P5 decision function -- the P9 trace block must call none
#: of them; it only reads already-computed `p7Poi*`/`poi*` state.
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

_P9_SECTION_START = "// P9 — full-system integration trace"
_P9_SECTION_END = "// P7 — panel render."


def test_p9_block_calls_no_decision_function() -> None:
    source = P9_DEV.read_text(encoding="utf-8")
    start = source.index(_P9_SECTION_START)
    end = source.index(_P9_SECTION_END, start)
    p9_section = source[start:end]
    assert "log.info(" in p9_section  # sanity: the anchors bound real content
    for decision_fn in _DECISION_FUNCTIONS:
        assert decision_fn not in p9_section, decision_fn


def test_p9_block_emits_no_alert_and_creates_no_drawing_object() -> None:
    """P9 is log-only -- it must never call `alert(`, `box.new(`,
    `label.new(`, or `line.new(`."""
    source = P9_DEV.read_text(encoding="utf-8")
    start = source.index(_P9_SECTION_START)
    end = source.index(_P9_SECTION_END, start)
    p9_section = source[start:end]
    assert "alert(" not in p9_section
    assert "box.new(" not in p9_section
    assert "label.new(" not in p9_section
    assert "line.new(" not in p9_section


def test_p9_loop_is_guarded_against_zero_active() -> None:
    """The same RE10045 class of defect (Pine's `for x = 0 to n - 1` does
    not skip execution when `n == 0`) is guarded here from the start,
    rather than discovered live a second time."""
    source = P9_DEV.read_text(encoding="utf-8")
    start = source.index(_P9_SECTION_START)
    end = source.index(_P9_SECTION_END, start)
    p9_section = source[start:end]
    loop_marker = "for p9Row = 0 to p9Active - 1"
    assert loop_marker in p9_section
    loop_start = p9_section.index(loop_marker)
    preceding_lines = p9_section[:loop_start].splitlines()
    previous_line = preceding_lines[-2]
    assert previous_line.strip() == "if p9Active > 0"
