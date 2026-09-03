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

THE SCORING MAP IS THE SECOND TRAP, AND IT IS NOT THE OBVIOUS ONE
-----------------------------------------------------------------
Reading the weight table alone suggests `liquidity` is simply the key under
which `assess_pullback` is scored. It is not. Traced through `assess_confluence`:

```
weight key   weight   where the score actually comes from
btmm            3     BTMM validity + direction agreement (P4), not an assessment
poi             3     poi.strength_tier, not an assessment
trend           2     assess_trend
regime          1     assess_regime
momentum        1     assess_momentum, selected at the POI timeframe
breakout        1     assess_breakout, selected at the POI timeframe
liquidity       1     `60 if btmm_valid else 40` -- a PROVISIONAL placeholder
volatility      1     assess_volatility
```

So of the seven assessments only **five** feed a score. `assess_pullback`
contributes `pullback_state` as a reported field and is never weighted;
`assess_session` only appends a missing reason. And the two heaviest components,
`btmm` and `poi` — six of the thirteen weight units — are not assessments at all.

Because the aggregator looks weights up with `weights.get(k, 0)`, every one of
these mistakes is silent: a port that wired pullback into `liquidity`, or scored
session, or omitted btmm/poi, would produce different numbers on every POI while
looking like a faithful reading of the table.
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


def test_liquidity_is_not_fed_by_the_pullback_assessment() -> None:
    """The trap, stated correctly.

    An earlier reading of this code assumed `liquidity` was simply the weight key
    under which `assess_pullback` was scored. It is not. `liquidity_score` is
    computed from BTMM validity alone -- `60 if btmm_valid else 40` -- and the
    source marks it provisional. `assess_pullback` contributes `pullback_state`,
    a REPORTED field, and is never scored.

    A port that wired the pullback assessment into the liquidity weight would
    produce a different number on every POI while looking like a faithful
    reading of the weight table.
    """
    source = _T5.read_text(encoding="utf-8")
    assert "liquidity_score = 60 if btmm_valid else 40" in source
    assert "liquidity_score=liquidity_score" in source
    # the pullback result reaches the decision as state, not as a score
    assert "pullback_state=pullback.pullback_state" in source
    assert "liquidity_score = pullback" not in source


def test_only_five_of_the_seven_assessments_feed_a_score() -> None:
    """trend, regime, momentum, breakout and volatility are scored. Pullback and
    session are not: pullback is reported as state, session only adds a missing
    reason. Porting either as a scored component would change every result."""
    source = _T5.read_text(encoding="utf-8")
    for scored in ("trend_score", "regime_score", "momentum_score",
                   "breakout_score", "volatility_score"):
        assert f"{scored}=" in source, scored
    assert "pullback_score" not in source
    assert "session_score" not in source


def test_session_is_a_missing_reason_not_a_score() -> None:
    weights = ConfluenceConfiguration().weights
    assert "session" not in weights
    assert "session" not in SCORED_COMPONENTS
    source = _T5.read_text(encoding="utf-8")
    assert 'missing.append("session")' in source


def test_the_two_heaviest_components_are_not_assessments_at_all() -> None:
    """btmm (3) and poi (3) carry the most weight and come from P4 and the POI
    itself, not from any of the seven assessments. A port that looked only at the
    assessment list would omit six of the fourteen weight units."""
    weights = ConfluenceConfiguration().weights
    assert weights["btmm"] == 3
    assert weights["poi"] == 3
    assert weights["btmm"] + weights["poi"] == 6
    assert sum(weights.values()) == 13
    assert {name for name, _ in SEVEN_ASSESSMENTS} & {"btmm", "poi"} == set()


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
