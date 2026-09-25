"""The overlap-cluster winner rule -- the thing that actually answers "why is
the weaker zone showing?" -- had no test at all.

It is worth stating why that mattered. Two bearish pressure wicks on real
XAUUSD H4 overlap in price:

    4435.255 / 4422.495   STANDARD
    4435.045 / 4408.725   STRONG

The STANDARD one never reaches the quota: `f_rc5DisplayBetter` resolves the
cluster on TIER first and the STRONG one wins. An earlier analysis concluded
the display pipeline was "distance only" and proposed a +46-token global
selector to fix a case this rule already handled. The rule was invisible
because nothing referenced it.

These are static assertions against the Pine source, because the comparator is
Pine-only: `grep -rl DisplayBetter tests/` returns nothing, no module in
`src/` implements it, and `p7zOverlapHidden` appears in neither. That absence
is itself worth recording -- this stage has no Python parity oracle, so these
tests are the only thing pinning it.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
_CORE = _REPO / "tradingview" / "btmm_poi_btrc_scanner_rc5_user.pine"


def _core() -> str:
    return _CORE.read_text(encoding="utf-8")


def _comparator() -> str:
    src = _core()
    body = src.split("f_rc5DisplayBetter(int a, int b) =>", 1)
    assert len(body) == 2, "f_rc5DisplayBetter is gone"
    return body[1][:600]


def test_THE_CLUSTER_WINNER_IS_DECIDED_BY_TIER_FIRST() -> None:
    """Tier leads. Everything else is a tie-break behind it."""
    body = _comparator()
    assert "array.get(poiTier, a)" in body
    assert "array.get(poiTier, b)" in body
    decision = [
        line for line in body.splitlines() if "?" in line and "ta2" in line
    ]
    assert decision, "the comparator's decision line is missing"
    assert decision[0].strip().startswith("ta2 != tb2 ? ta2 > tb2"), decision[0]


def test_the_tie_breaks_run_score_then_availability_then_index() -> None:
    """The documented order, pinned so a refactor cannot quietly reorder it."""
    decision = next(
        line for line in _comparator().splitlines() if "ta2 != tb2" in line
    )
    # score, then availability, then a stable index tie-break
    assert re.search(r"sa != sb \? sa > sb", decision), decision
    assert re.search(r"va != vb \? va > vb", decision), decision
    assert decision.rstrip().endswith("a > b"), decision


def test_tier_constants_still_order_NA_below_STANDARD_below_STRONG() -> None:
    """The comparator relies on direct integer comparison of these.

    If the values are ever reordered, `ta2 > tb2` silently changes meaning and
    every overlap cluster resolves differently.
    """
    core = _core()
    assert "int C_POI_TIER_NA       = 0" in core
    assert "int C_POI_TIER_STANDARD = 1" in core
    assert "int C_POI_TIER_STRONG   = 2" in core


def test_the_cluster_stage_runs_before_the_quota() -> None:
    """Order matters: clustering first, then nearest-first over survivors.

    If the quota ever ran first, a STRONG zone could be cut before it had the
    chance to beat the overlapping STANDARD one.
    """
    core = _core()
    cluster = core.index("f_rc5DisplayBetter(p, array.get(cBest, 0))")
    quota = core.index("p7zSelected := bahui.nearestFirst(")
    assert cluster < quota, "the overlap cluster must resolve before the quota"


def test_clustering_is_direction_aware() -> None:
    """A bearish wick must never hide a bullish order block."""
    core = _core()
    assert "int want = dirPass == 0 ? C_POI_DIR_BULLISH : C_POI_DIR_BEARISH" in core
    assert "if array.get(poiDirection, pD) == want" in core


def test_the_loser_is_hidden_not_deleted() -> None:
    """Presentation only -- the suppressed record keeps its registry entry."""
    core = _core()
    assert "p7zOverlapHidden := p7zActive - array.size(p7zKept)" in core


def test_this_stage_has_no_python_oracle_and_that_is_recorded() -> None:
    """A guard against a false sense of parity coverage.

    If someone later adds a Python mirror, this test should be updated to
    compare against it rather than deleted -- the point is that the absence is
    deliberate knowledge, not an oversight.
    """
    hits = [
        p
        for p in (_REPO / "src").rglob("*.py")
        if "DisplayBetter" in p.read_text(encoding="utf-8", errors="ignore")
    ]
    assert not hits, (
        "a Python implementation of the display comparator now exists; "
        "point these tests at it instead of the Pine source"
    )
