"""P5-I0: the remaining contract a Pine port of BTRC must carry.

SCOPE — WHAT IS NOT HERE
------------------------
`test_p6_mtf_contract` already pins the T1 authority order, the T2 primary order
and that it differs, T2's dependency on T1, the flat POI lifecycle, session as a
pure function of time, volatility taking candles rather than analysis, the
provisional weights and bands, and the per-component input table. Repeating any
of that here would add lines and no coverage.

This module fills the gaps that remain before a port can begin.

THE ONE THAT MATTERS MOST
-------------------------
`assess_confluence` takes ONE POI. The authoritative source contains no loop over
a POI universe at all, so **which** POIs get evaluated per bar is a port-level
decision, not a source semantic. That distinction is worth pinning because it is
exactly the kind of thing a later reader would "discover" in the source and
implement as if it were authoritative. The author has frozen the decision
separately: evaluate active / non-terminal POIs, with the final evaluation on the
terminal-transition bar itself.

The scoring keys are the second trap. The weight table names `liquidity`, not
`pullback`, and carries **no** `session` key — session participates as a missing
reason and a gate, never as a weighted score. A port that scored session, or
that spelled the pullback weight `pullback`, would silently change every final
number while looking correct.
"""

from __future__ import annotations

import inspect
from pathlib import Path

from btmm_ai_scanner.btrc.regime_engine import assess_regime
from btmm_ai_scanner.btrc.t3_engine import (
    assess_breakout,
    assess_momentum,
    assess_pullback,
)
from btmm_ai_scanner.btrc.t4_engine import assess_session, assess_volatility
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_engine import assess_confluence
from btmm_ai_scanner.btrc.trend_engine import assess_trend

_REPO = Path(__file__).resolve().parents[2]
_T5 = _REPO / "src" / "btmm_ai_scanner" / "btrc" / "t5_engine.py"

#: The seven assessments T5 invokes, with the module each lives in. Frozen so a
#: port cannot quietly gain or lose one.
SEVEN_ASSESSMENTS: tuple[tuple[str, str], ...] = (
    ("assess_trend", "trend_engine"),
    ("assess_regime", "regime_engine"),
    ("assess_momentum", "t3_engine"),
    ("assess_breakout", "t3_engine"),
    ("assess_pullback", "t3_engine"),
    ("assess_volatility", "t4_engine"),
    ("assess_session", "t4_engine"),
)

#: The exact keys `_weighted_final` scores, in source order.
SCORED_COMPONENTS: tuple[str, ...] = (
    "btmm",
    "poi",
    "trend",
    "regime",
    "momentum",
    "breakout",
    "liquidity",
    "volatility",
)


# ---------------------------------------------------------------------------
# The seven assessments
# ---------------------------------------------------------------------------


def test_there_are_exactly_seven_assessments() -> None:
    assert len(SEVEN_ASSESSMENTS) == 7


def test_every_named_assessment_exists_and_is_invoked_by_t5() -> None:
    source = _T5.read_text(encoding="utf-8")
    for name, _module in SEVEN_ASSESSMENTS:
        assert f"{name}(" in source, f"T5 never calls {name}"


def test_the_assessments_live_where_the_inventory_says() -> None:
    for fn, (name, module) in zip(
        (
            assess_trend,
            assess_regime,
            assess_momentum,
            assess_breakout,
            assess_pullback,
            assess_volatility,
            assess_session,
        ),
        SEVEN_ASSESSMENTS,
        strict=True,
    ):
        assert fn.__name__ == name
        assert fn.__module__.endswith(module), (fn.__module__, module)


def test_the_t3_assessments_return_one_result_per_timeframe() -> None:
    """T3 fans out across timeframes and T5 then selects the POI's own, which is
    why the port must not collapse them to a single value."""
    for fn in (assess_momentum, assess_breakout, assess_pullback):
        annotation = str(inspect.signature(fn).return_annotation)
        assert "tuple" in annotation, (fn.__name__, annotation)


def test_trend_and_regime_return_a_single_assessment() -> None:
    for fn in (assess_trend, assess_regime):
        annotation = str(inspect.signature(fn).return_annotation)
        assert "tuple" not in annotation, (fn.__name__, annotation)


# ---------------------------------------------------------------------------
# The evaluation universe is a PORT decision, not a source semantic
# ---------------------------------------------------------------------------


def test_confluence_is_evaluated_per_poi() -> None:
    """One POI in, one decision out."""
    parameters = inspect.signature(assess_confluence).parameters
    assert "poi" in parameters
    annotation = str(parameters["poi"].annotation)
    assert "PoiObservation" in annotation
    assert "Sequence" not in annotation and "list" not in annotation


def test_the_source_contains_no_poi_universe_loop() -> None:
    """So a port cannot claim source authority for whichever set it evaluates.

    `poi_observations` and `current_poi_states` ARE read -- to find the latest
    observation and to look up one lifecycle status -- but nothing iterates a
    universe of POIs producing many decisions.
    """
    source = _T5.read_text(encoding="utf-8")
    code = "\n".join(
        line
        for line in source.split("\n")
        if not line.strip().startswith("#")
    )
    assert "for poi in" not in code
    assert "for observation in" not in code


def test_the_poi_lifecycle_status_is_available_to_gate_the_active_set() -> None:
    """The port evaluates active / non-terminal POIs, and this is the field it
    must gate on. If T5 stopped reading a lifecycle status, the port would have
    nothing to decide the active set with -- so the read is pinned here rather
    than assumed."""
    source = _T5.read_text(encoding="utf-8")
    assert "poi_lifecycle_status" in source
    assert "current_poi_states" in source


# ---------------------------------------------------------------------------
# The scoring keys -- the trap a port would fall into
# ---------------------------------------------------------------------------


def test_the_scored_components_are_exactly_these_eight() -> None:
    source = _T5.read_text(encoding="utf-8")
    block = source[source.index("def _weighted_final") :]
    block = block[: block.index("total_weight")]
    found = [line.split('"')[1] for line in block.split("\n") if line.strip().startswith('"')]
    assert tuple(found) == SCORED_COMPONENTS, found


def test_the_pullback_component_is_weighted_as_liquidity() -> None:
    """Not `pullback`. A port using the obvious name would drop the weight to
    zero via `weights.get(k, 0)` and change every final score."""
    weights = ConfluenceConfiguration().weights
    assert "liquidity" in weights
    assert "pullback" not in weights


def test_session_carries_no_weight() -> None:
    """Session is a gate and a missing-reason, never a scored component."""
    weights = ConfluenceConfiguration().weights
    assert "session" not in weights
    assert "session" not in SCORED_COMPONENTS


def test_every_scored_component_has_a_weight() -> None:
    weights = ConfluenceConfiguration().weights
    assert set(weights) == set(SCORED_COMPONENTS)


def test_the_frozen_weight_values() -> None:
    assert ConfluenceConfiguration().weights == {
        "btmm": 3,
        "poi": 3,
        "trend": 2,
        "regime": 1,
        "momentum": 1,
        "breakout": 1,
        "liquidity": 1,
        "volatility": 1,
    }


def test_a_missing_weight_silently_drops_a_component() -> None:
    """Why the key names are pinned: `weights.get(k, 0)` does not raise."""
    source = _T5.read_text(encoding="utf-8")
    assert "weights.get(k, 0)" in source


def test_the_score_is_a_weighted_mean_rounded() -> None:
    source = _T5.read_text(encoding="utf-8")
    assert "round(weighted / total_weight)" in source


def test_zero_total_weight_yields_zero_not_a_division_error() -> None:
    source = _T5.read_text(encoding="utf-8")
    block = source[source.index("def _weighted_final") :]
    assert "if total_weight == 0:" in block
    assert "return 0" in block


# ---------------------------------------------------------------------------
# Calibration status
# ---------------------------------------------------------------------------


def test_the_bands_are_the_frozen_provisional_ones() -> None:
    config = ConfluenceConfiguration()
    assert config.high_confluence_min == 65
    assert config.watch_only_min == 45


def test_the_calibration_is_marked_provisional_in_source() -> None:
    """Parity with these numbers proves the MECHANISM, never that the
    calibration is production-approved."""
    text = (
        _REPO / "src" / "btmm_ai_scanner" / "btrc" / "t5_configuration.py"
    ).read_text(encoding="utf-8")
    assert "ENGINEERING-PROVISIONAL" in text
