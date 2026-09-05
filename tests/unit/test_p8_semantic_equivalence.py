"""P8 mechanical semantic-equivalence gate: P8 DEV vs. the closed P7 DEV.

Mirrors `test_p7_semantic_equivalence.py`'s own method exactly (a diff-based
mechanical proof, not a manual read): P8 must be presentation/notification
-only, adding alert-event detection and `alert()` calls on top of the
closed P1-P7 engine, never modifying a line of it and never introducing a
second decision engine.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P7_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p7_dev.pine"
P8_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p8_dev.pine"

_PLOT_FAMILY = re.compile(r"^(?:plot|plotshape|plotchar)\(", re.M)
_REQUEST_SECURITY = re.compile(r"request\.security\(")
_ALERTCONDITION = re.compile(r"^\s*alertcondition\(", re.M)
_ALERT_CALL = re.compile(r"^\s*alert\(", re.M)
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=")

#: Fields a P8 alert payload must never contain -- no execution capability
#: exists anywhere in this closed engine to expose in the first place, but
#: this is asserted directly against the alert-message-building code as a
#: permanent guard against ever adding one later.
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
        ["git", "diff", "--no-index", "--unified=0", str(P7_DEV), str(P8_DEV)],
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


def test_p8_dev_exists_as_a_separate_script_from_p7_dev() -> None:
    assert P7_DEV.exists()
    assert P8_DEV.exists()
    assert P7_DEV.read_bytes() != P8_DEV.read_bytes()


def test_every_removed_line_is_the_indicator_title() -> None:
    removed, _added = _removed_and_added(_diff_lines())
    non_title_removals = [line for line in removed if "P7 DEV" not in line]
    assert non_title_removals == [], non_title_removals


def test_title_is_the_only_thing_changed_on_that_line() -> None:
    removed, added = _removed_and_added(_diff_lines())
    title_removed = [line for line in removed if "P7 DEV" in line]
    title_added = [line for line in added if "P8 DEV" in line]
    assert len(title_removed) == 1
    assert len(title_added) == 1
    before = title_removed[0].replace("P7 DEV", "P8 DEV")
    assert before == title_added[0]


def test_every_added_reassignment_targets_a_p8_variable() -> None:
    """P8 may READ any P1-P7 variable (including the loop-local
    `btmmValid`/`permission`/`isTerminal`/`finalScore`/`lifecycle` values
    the active-POI loop already computed) but every `:=` it introduces
    must write into its own `p8`-prefixed namespace."""
    _removed, added = _removed_and_added(_diff_lines())
    non_p8_targets = []
    for line in added:
        match = _ASSIGN.match(line)
        if match and not match.group(1).startswith("p8"):
            non_p8_targets.append(line)
    assert non_p8_targets == [], non_p8_targets


def test_plot_family_count_unchanged() -> None:
    p7_count = len(_PLOT_FAMILY.findall(P7_DEV.read_text(encoding="utf-8")))
    p8_count = len(_PLOT_FAMILY.findall(P8_DEV.read_text(encoding="utf-8")))
    assert p8_count == p7_count == 63


def test_request_security_count_unchanged() -> None:
    p7_count = len(_REQUEST_SECURITY.findall(P7_DEV.read_text(encoding="utf-8")))
    p8_count = len(_REQUEST_SECURITY.findall(P8_DEV.read_text(encoding="utf-8")))
    assert p8_count == p7_count == 6


def test_no_alertcondition_calls_alert_function_used_instead() -> None:
    """P8's own resource-tradeoff decision (readiness audit Section 14):
    `alert()` for dynamic per-POI messages at zero plot/request cost, never
    the static, script-level `alertcondition()`."""
    source = P8_DEV.read_text(encoding="utf-8")
    assert not _ALERTCONDITION.search(source)
    assert len(_ALERT_CALL.findall(source)) == 5, "expected exactly the 5 V1 alert() call sites"


def test_no_forbidden_execution_terms_anywhere_in_the_p8_addition() -> None:
    """Checks CODE lines only -- comment/documentation lines are excluded
    deliberately, since this project's own disclosure prose (e.g. "no
    entry price, stop loss...") legitimately names these terms in
    English while explaining that none exist in code; scanning comments
    would false-positive on the very sentence that proves the guard."""
    _removed, added = _removed_and_added(_diff_lines())
    code_lines = [line for line in added if not line.strip().startswith("//")]
    added_text = "\n".join(code_lines)
    for term in _FORBIDDEN_PAYLOAD_TERMS:
        assert term not in added_text, f"forbidden execution-related term found in P8 code: {term!r}"


#: Every closed P5 decision function -- same list `test_p7_semantic_
#: equivalence.py` already checks the P7 label section against. P8's own
#: alert-event/log block must call none of them either: it consumes
#: `btmmValid`/`permission`/`isTerminal`/`finalScore`/`lifecycle` (already
#: computed, in scope from the loop), never recomputes one.
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

_P8_SECTION_START = "// ---- P8: alert-event detection"
_P8_SECTION_END = "if isTerminal\n                    array.set(poiP5FinalDone, i, true)"


def test_p8_alert_block_calls_no_decision_function() -> None:
    source = P8_DEV.read_text(encoding="utf-8")
    start = source.index(_P8_SECTION_START)
    end = source.index(_P8_SECTION_END, start)
    p8_section = source[start:end]
    assert "alert(" in p8_section  # sanity: the anchors bound real content
    for decision_fn in _DECISION_FUNCTIONS:
        assert decision_fn not in p8_section, decision_fn
