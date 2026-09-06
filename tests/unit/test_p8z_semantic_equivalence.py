"""P8-Z mechanical semantic-equivalence gate: P8Z DEV vs. the closed P8 DEV.

Mirrors `test_p8_semantic_equivalence.py`'s own method exactly (a diff-based
mechanical proof, not a manual read): P7-Z must be presentation-only,
adding POI zone box/label drawing on top of the closed P1-P8 engine, never
modifying a line of it and never introducing a second detector, ranking, or
decision engine.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P8_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p8_dev.pine"
P8Z_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p8z_dev.pine"

_PLOT_FAMILY = re.compile(r"^(?:plot|plotshape|plotchar)\(", re.M)
_REQUEST_SECURITY = re.compile(r"request\.security\(")
_ALERTCONDITION = re.compile(r"^\s*alertcondition\(", re.M)
_ALERT_CALL = re.compile(r"^\s*alert\(", re.M)
_BOX_NEW = re.compile(r"\bbox\.new\(")
_LABEL_NEW = re.compile(r"\blabel\.new\(")
_LINE_NEW = re.compile(r"\bline\.new\(")
_ASSIGN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*:=")

#: Fields a P7-Z zone/label must never expose -- no execution capability
#: exists anywhere in this closed engine, but this is asserted directly
#: against the new drawing code as a permanent guard against ever adding one
#: later (mirrors `test_p8_semantic_equivalence.py`'s own guard).
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
        ["git", "diff", "--no-index", "--unified=0", str(P8_DEV), str(P8Z_DEV)],
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


def test_p8z_dev_exists_as_a_separate_script_from_p8_dev() -> None:
    assert P8_DEV.exists()
    assert P8Z_DEV.exists()
    assert P8_DEV.read_bytes() != P8Z_DEV.read_bytes()


def test_every_removed_line_is_the_indicator_title() -> None:
    removed, _added = _removed_and_added(_diff_lines())
    non_title_removals = [line for line in removed if "P8 DEV" not in line]
    assert non_title_removals == [], non_title_removals


def test_title_is_the_only_thing_changed_on_that_line() -> None:
    removed, added = _removed_and_added(_diff_lines())
    title_removed = [line for line in removed if "P8 DEV" in line]
    title_added = [line for line in added if "P8Z DEV" in line]
    assert len(title_removed) == 1
    assert len(title_added) == 1
    before = title_removed[0].replace("P8 DEV", "P8Z DEV")
    assert before == title_added[0]


def test_every_added_reassignment_targets_a_p7z_variable() -> None:
    """P7-Z may READ any P1-P8 variable (including `p7PoiIdx`/`poiZoneTop`/
    etc. the active-POI loop and P3 registry already expose) but every `:=`
    it introduces must write into its own `p7z`-prefixed namespace."""
    _removed, added = _removed_and_added(_diff_lines())
    non_p7z_targets = []
    for line in added:
        match = _ASSIGN.match(line)
        if match and not match.group(1).startswith("p7z"):
            non_p7z_targets.append(line)
    assert non_p7z_targets == [], non_p7z_targets


def test_plot_family_count_unchanged() -> None:
    p8_count = len(_PLOT_FAMILY.findall(P8_DEV.read_text(encoding="utf-8")))
    p8z_count = len(_PLOT_FAMILY.findall(P8Z_DEV.read_text(encoding="utf-8")))
    assert p8z_count == p8_count == 63


def test_request_security_count_unchanged() -> None:
    p8_count = len(_REQUEST_SECURITY.findall(P8_DEV.read_text(encoding="utf-8")))
    p8z_count = len(_REQUEST_SECURITY.findall(P8Z_DEV.read_text(encoding="utf-8")))
    assert p8z_count == p8_count == 6


def test_alert_mechanism_unchanged() -> None:
    """P7-Z must not touch P8's alert surface at all."""
    p8_source = P8_DEV.read_text(encoding="utf-8")
    p8z_source = P8Z_DEV.read_text(encoding="utf-8")
    assert not _ALERTCONDITION.search(p8z_source)
    p8_alerts = len(_ALERT_CALL.findall(p8_source))
    p8z_alerts = len(_ALERT_CALL.findall(p8z_source))
    assert p8_alerts == p8z_alerts == 5


def test_exactly_one_new_box_and_one_new_conditional_label_call_site() -> None:
    """P8 DEV already has exactly 1 `box.new` (the P2 support/resistance
    zone) and 1 `label.new` (the P2 swing label), plus 2 `line.new` (P2
    equal-level + trendline). P7-Z adds exactly one new box.new call site
    (the zone box) and one new label.new call site (the zone label,
    conditional on `p7zShowLabels`) -- `line.new` is untouched."""
    p8_source = P8_DEV.read_text(encoding="utf-8")
    p8z_source = P8Z_DEV.read_text(encoding="utf-8")
    assert len(_BOX_NEW.findall(p8_source)) == 1
    assert len(_LABEL_NEW.findall(p8_source)) == 1
    assert len(_LINE_NEW.findall(p8_source)) == 2

    assert len(_BOX_NEW.findall(p8z_source)) == 2
    assert len(_LABEL_NEW.findall(p8z_source)) == 2
    assert len(_LINE_NEW.findall(p8z_source)) == 2


def test_no_forbidden_execution_terms_anywhere_in_the_p8z_addition() -> None:
    """Checks CODE lines only -- comment/documentation lines are excluded
    deliberately, for the same reason `test_p8_semantic_equivalence.py`
    already excludes them (the project's own disclosure prose legitimately
    names these terms in English)."""
    _removed, added = _removed_and_added(_diff_lines())
    code_lines = [line for line in added if not line.strip().startswith("//")]
    added_text = "\n".join(code_lines)
    for term in _FORBIDDEN_PAYLOAD_TERMS:
        assert term not in added_text, (
            f"forbidden execution-related term found in P8-Z code: {term!r}"
        )


#: Every closed P5 decision function -- same list `test_p8_semantic_
#: equivalence.py` already checks the P8 alert block against. P7-Z's own
#: box/label block must call none of them either: it consumes
#: `poiZoneTop`/`poiZoneBottom`/`poiAvailTime`/`poiType`/`poiDirection`/
#: `poiTier`/`poiTerminal`/`p7PoiIdx` (already computed, in scope), never
#: recomputes one.
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

_P7Z_SECTION_START = "// P7-Z — POI zone visualization"
_P7Z_SECTION_END = "// P7 — panel render."


def test_p7z_block_calls_no_decision_function() -> None:
    source = P8Z_DEV.read_text(encoding="utf-8")
    start = source.index(_P7Z_SECTION_START)
    end = source.index(_P7Z_SECTION_END, start)
    p7z_section = source[start:end]
    assert "box.new(" in p7z_section  # sanity: the anchors bound real content
    for decision_fn in _DECISION_FUNCTIONS:
        assert decision_fn not in p7z_section, decision_fn


def test_p7z_block_never_indexes_p7poiidx_beyond_its_own_selection() -> None:
    """A cheap source-level guard against reading past `p7zShown`/`p7Active`
    -- the display cap must never be treated as if it bounded the engine's
    own active set anywhere in this file."""
    source = P8Z_DEV.read_text(encoding="utf-8")
    start = source.index(_P7Z_SECTION_START)
    end = source.index(_P7Z_SECTION_END, start)
    p7z_section = source[start:end]
    assert "p5N" not in p7z_section  # never re-touches the P5 loop bound
    assert "array.clear(p7PoiIdx)" not in p7z_section  # never mutates P7's own array


def test_both_p7zshown_loops_are_guarded_against_zero_active() -> None:
    """Real defect caught during live TradingView validation: Pine's
    `for r = 0 to p7zShown - 1` executes at least once even when
    `p7zShown == 0` (`0 to -1` does not silently skip, unlike Python's
    `range(0)` -- the offline `p7z_zone_model.py` reference could not have
    caught this, since it never re-derives Pine's own loop-bound semantics).
    `array.get(p7PoiIdx, 0)` then throws `RE10045` (index 0, size 0) the
    moment zero POIs are active. Both loop sites must stay wrapped in an
    explicit `if p7zShown > 0` guard, matching the SAME defensive pattern
    the closed P5 active-loop (`if p5N > 0`) already established for the
    identical class of bug."""
    source = P8Z_DEV.read_text(encoding="utf-8")
    start = source.index(_P7Z_SECTION_START)
    end = source.index(_P7Z_SECTION_END, start)
    p7z_section = source[start:end]
    loop_starts = [
        i
        for i in range(len(p7z_section))
        if p7z_section.startswith("for r = 0 to p7zShown - 1", i)
    ]
    assert len(loop_starts) == 2, "expected exactly the two known p7zShown loop sites"
    for loop_start in loop_starts:
        lines_before = p7z_section[:loop_start].splitlines()
        previous_line = lines_before[
            -2
        ]  # [-1] is just the "for" line's own leading indent
        assert previous_line.strip() == "if p7zShown > 0", (
            f"loop at offset {loop_start} is not immediately preceded by an 'if p7zShown > 0' guard: {previous_line!r}"
        )
