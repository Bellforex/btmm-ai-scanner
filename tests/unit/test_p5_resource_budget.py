"""The P5 plot budget, settled before any P5 code is written.

THE CONSTRAINT
--------------
Pine allows 64 `plot` calls per script. P6 DEV uses 63. A P5 section that added
its own diagnostics the way earlier phases did would not compile, and the
temptation at that point is to trim something semantic to make room.

THE RESOLUTION, AND WHY IT COSTS NOTHING
-----------------------------------------
P5 needs **zero** new plots. The P6 atomic capture demonstrated that `log.info`
carries arbitrary volume from Pine -- 41,495 rows in one downloaded buffer,
including from inside `request.security` contexts. Everything P5 needs to expose
(seven assessment results, the weight-lookup trace, contributions, score,
permission, per-POI decisions) is strictly richer than a float per bar, so the
data window was never the right channel for it anyway.

So the budget plan is:

* P5 DEV inherits the P6 semantic foundation unchanged, including all 63 plots;
* P5 adds no `plot` call;
* P5 output goes through `log.info` and the existing diagnostics table.

That keeps one plot slot spare, requires no semantic change, and leaves the P6
closure evidence intact -- which matters, because the 72/72 runtime matrix reads
`P6_ALIAS_HITS`, `P6_host_bars_max` and the six `P6_*_bars` plots. Retiring those
to make room would have invalidated the way that evidence is re-derived.

CLASSIFICATION
--------------
No plot is SEMANTICALLY REQUIRED: plots are outputs, and nothing in P1-P6 reads
one back. The meaningful split is what other evidence depends on:

  RUNTIME CONTRACT      P6_ALIAS_HITS, P6_host_bars_max, P6_*_bars (6)
                        -- read by the FXCM runtime matrix
  ENVELOPE EVIDENCE     P6_*_dataset (6)  -- the 1251/1250 measurement
  NON-VACUITY           P6_*_swings (6), P6_*_disp_code (6), P6_*_p2_dir (6)
  CLOSURE-EVIDENCE ONLY P1_* (9), P2_* (15), P4_* (5) -- their phases are closed
                        and their evidence is already recorded
  VISUAL                the two displacement shapes
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"

PINE_PLOT_LIMIT = 64

#: Plots the FXCM runtime matrix reads. Retiring one would break the way that
#: closed evidence is re-derived, so they are named rather than merely counted.
RUNTIME_CONTRACT_PLOTS = (
    "P6_ALIAS_HITS",
    "P6_host_bars_max",
    "P6_W1_bars",
    "P6_D1_bars",
    "P6_H4_bars",
    "P6_H1_bars",
    "P6_M15_bars",
    "P6_M5_bars",
)


def _plot_titles(source: str) -> list[str]:
    return re.findall(r'^plot(?:shape)?\([^\n]*?"([^"]+)"', source, re.M)


def _plot_calls(source: str) -> int:
    return len(re.findall(r"^plot", source, re.M))


def test_p6_dev_sits_one_slot_below_the_limit() -> None:
    source = P6_DEV.read_text(encoding="utf-8")
    calls = _plot_calls(source)
    assert calls == 63
    assert calls < PINE_PLOT_LIMIT


def test_every_plot_is_titled() -> None:
    """An untitled plot cannot be classified, and would be invisible to this
    budget."""
    source = P6_DEV.read_text(encoding="utf-8")
    assert len(_plot_titles(source)) == _plot_calls(source)


def test_the_runtime_contract_plots_are_all_present() -> None:
    """The 72/72 FXCM matrix reads these by title."""
    titles = set(_plot_titles(P6_DEV.read_text(encoding="utf-8")))
    missing = [name for name in RUNTIME_CONTRACT_PLOTS if name not in titles]
    assert missing == [], missing


def test_the_envelope_evidence_plots_are_all_present() -> None:
    titles = set(_plot_titles(P6_DEV.read_text(encoding="utf-8")))
    for timeframe in ("W1", "D1", "H4", "H1", "M15", "M5"):
        assert f"P6_{timeframe}_dataset" in titles, timeframe


def test_the_budget_leaves_room_for_zero_new_plots() -> None:
    """Stated as arithmetic so the plan cannot be misremembered: there is exactly
    one slot, and P5 is not going to spend it."""
    source = P6_DEV.read_text(encoding="utf-8")
    spare = PINE_PLOT_LIMIT - _plot_calls(source)
    assert spare == 1


def test_log_output_is_the_channel_p5_will_use() -> None:
    """Demonstrated by the P6 atomic capture, which carried 41,495 rows -- so the
    data window was never the right channel for per-POI decisions anyway."""
    atomic = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_atomic_parity.pine"
    assert "log.info(" in atomic.read_text(encoding="utf-8")


#: The two P5 scripts that actually exist now (P5 DEV, and its ATOMIC PARITY
#: twin -- see BTRC_V1_P5_BTRC_CLOSURE.md), both built as P6 DEV plus
#: additions. This module's plan held: neither adds a single `plot` call.
P5_SCRIPTS = (
    _REPO / "tradingview" / "btmm_poi_btrc_scanner_p5_dev.pine",
    _REPO / "tradingview" / "btmm_poi_btrc_scanner_p5_atomic_parity.pine",
)


def test_p5_pine_sources_exist() -> None:
    for script in P5_SCRIPTS:
        assert script.exists(), script


def test_p5_adds_zero_new_plot_calls() -> None:
    """The plan's central claim, verified rather than assumed now that the
    implementation exists: P5's plot count equals P6 DEV's exactly -- the one
    spare slot this module reserved was never spent."""
    p6_calls = _plot_calls(P6_DEV.read_text(encoding="utf-8"))
    for script in P5_SCRIPTS:
        assert _plot_calls(script.read_text(encoding="utf-8")) == p6_calls, script


def test_p5_output_goes_through_log_info() -> None:
    """P5EVAL (both scripts) and P5WIRE (the ATOMIC twin only) are the actual
    channels P5 uses -- confirming the plan's `log.info`-only design landed."""
    for script in P5_SCRIPTS:
        source = script.read_text(encoding="utf-8")
        assert '"P5EVAL|' in source, script
    atomic = P5_SCRIPTS[1].read_text(encoding="utf-8")
    assert '"P5WIRE|' in atomic
