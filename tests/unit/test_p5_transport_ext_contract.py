"""The exact `P5TransportExt` field contract, frozen before the Pine port.

This module is the definition of what crosses the P6 boundary. It is written
against the authoritative Python engines, not against the Pine source, so a port
that drifts fails here rather than at a real-data digest three phases later.

THE CORRECTION THIS AUDIT PASS FOUND
------------------------------------
The first field list proposed transporting `altCount4` -- the CHOCH count among
the last four transitions. That is wrong, and wrong in exactly the way the
"transport raw values, not calibration verdicts" rule was written to prevent.

`_alternation_count(transitions, window)` takes its window from
`TrendEngineConfiguration.range_window`, and the count it returns is then
compared against `range_choch_count`. Both are ENGINEERING-PROVISIONAL P5
configuration. A P6 field called `altCount4` freezes the first of them inside the
MTF layer, invisibly: change `range_window` to 5 and every timeframe silently
keeps answering for 4.

So the transport carries the last four transition TYPES and P5 counts CHOCHs
itself. That also subsumes what breakout needed -- `ordered_transitions[-2]` for
the whipsaw test -- so one bounded window replaces two separate fields.

CAPACITY IS NOT CALIBRATION
---------------------------
The window sizes that remain (4 transitions, 3 displacements) are transport
CAPACITY, not frozen thresholds, and the distinction is load-bearing:

* a baked threshold (ratio >= 1.50) is undetectable from outside -- P5 would
  read a verdict and never know it was computed against a stale constant;
* a capacity that is too small IS detectable -- P5 knows its own configured
  window and can assert it fits.

Hence `test_p5_configuration_fits_the_transport_capacity`. If someone raises
`range_window` past 4 or `momentum_window` past 3, that test fails and names the
capacity that has to grow, instead of the port quietly answering the old
question.

WHAT IS DELIBERATELY NOT TRANSPORTED
------------------------------------
* `equal_level_clusters` -- `_assess_timeframe_breakout` takes the parameter and
  its body never reads it. The source declines to emit LIQUIDITY_SWEEP in V1 and
  documents why. Verified here, because it is a claim the field list depends on.
* the retracement depth ratio -- P6 sends three prices and a validity flag; the
  division and the 0.382 / 0.618 band comparisons stay in P5.
* the momentum score, acceleration and any VERY_FAST verdict -- all are
  functions of `momentum_score_reference_ratio` and
  `momentum_acceleration_margin`, so P6 sends `range_speed_ratio` raw.
"""

from __future__ import annotations

from pathlib import Path

from btmm_ai_scanner.btrc.regime_configuration import RegimeEngineConfiguration
from btmm_ai_scanner.btrc.t3_configuration import (
    MomentumBreakoutPullbackConfiguration,
)
from btmm_ai_scanner.btrc.trend_configuration import TrendEngineConfiguration

_REPO = Path(__file__).resolve().parents[2]
_BTRC = _REPO / "src" / "btmm_ai_scanner" / "btrc"

#: How many most-recent structure transitions the transport carries.
TRANSITION_WINDOW_CAPACITY = 4

#: How many most-recent displacement observations the transport carries.
DISPLACEMENT_WINDOW_CAPACITY = 3

#: The frozen field list: (name, pine type, consumer).
#:
#: Order is the wire order. Fields are APPENDED only; nothing here may be
#: reordered or renamed once the extension ships, for the same reason the old 14
#: scalar positions are immovable.
P5_TRANSPORT_EXT_FIELDS: tuple[tuple[str, str, str], ...] = (
    # --- T1 trend: config-free reductions over the full ordered history ---
    ("stateAvailT", "int", "trend"),
    ("contStreak", "int", "trend"),
    ("priorOppStreak", "int", "trend"),
    ("exhaustFlag", "int", "trend"),
    # --- bounded transition window, oldest -> newest ---
    ("transWindowCount", "int", "trend+breakout"),
    ("trans1Type", "int", "trend+breakout"),
    ("trans2Type", "int", "trend+breakout"),
    ("trans3Type", "int", "trend+breakout"),
    ("trans4Type", "int", "trend+breakout"),
    ("lastTransAvailT", "int", "breakout"),
    # --- bounded displacement window, oldest -> newest ---
    ("dispWindowCount", "int", "regime+momentum"),
    ("disp1Dir", "int", "regime+momentum"),
    ("disp1Cls", "int", "regime+momentum"),
    ("disp1Ratio", "float", "regime+momentum"),
    ("disp2Dir", "int", "regime+momentum"),
    ("disp2Cls", "int", "regime+momentum"),
    ("disp2Ratio", "float", "regime+momentum"),
    ("disp3Dir", "int", "regime+momentum"),
    ("disp3Cls", "int", "regime+momentum"),
    ("disp3Ratio", "float", "regime+momentum"),
    ("dispAvailT", "int", "regime+momentum"),
    # --- breakout ---
    ("dispClsAtTrans", "int", "breakout"),
    # --- pullback ---
    ("pbImpulsePrice", "float", "pullback"),
    ("pbOriginPrice", "float", "pullback"),
    ("pbPullbackPrice", "float", "pullback"),
    ("pbValid", "bool", "pullback"),
)

#: Types Pine can carry across `request.security` inside a UDT.
REQUESTABLE_PINE_TYPES = frozenset({"int", "float", "bool"})


# ---------------------------------------------------------------------------
# Shape
# ---------------------------------------------------------------------------


def test_the_field_list_is_frozen_at_twenty_six() -> None:
    assert len(P5_TRANSPORT_EXT_FIELDS) == 26


def test_field_names_are_unique() -> None:
    names = [name for name, _type, _consumer in P5_TRANSPORT_EXT_FIELDS]
    assert len(names) == len(set(names))


def test_every_field_is_a_requestable_scalar_type() -> None:
    """No arrays, no nested objects, no strings: the boundary carries scalars."""
    for name, pine_type, _consumer in P5_TRANSPORT_EXT_FIELDS:
        assert pine_type in REQUESTABLE_PINE_TYPES, (name, pine_type)


def test_natural_types_are_used_rather_than_packing() -> None:
    """Timestamps, counts and enum codes stay int; ratios and prices stay float;
    validity stays bool. Packing was rejected while a UDT was available."""
    by_name = {name: t for name, t, _ in P5_TRANSPORT_EXT_FIELDS}
    assert by_name["stateAvailT"] == "int"
    assert by_name["lastTransAvailT"] == "int"
    assert by_name["dispAvailT"] == "int"
    for n in ("disp1Ratio", "disp2Ratio", "disp3Ratio"):
        assert by_name[n] == "float"
    for n in ("pbImpulsePrice", "pbOriginPrice", "pbPullbackPrice"):
        assert by_name[n] == "float"
    assert by_name["pbValid"] == "bool"


def test_the_windows_are_sized_to_their_declared_capacity() -> None:
    names = {name for name, _t, _c in P5_TRANSPORT_EXT_FIELDS}
    for i in range(1, TRANSITION_WINDOW_CAPACITY + 1):
        assert f"trans{i}Type" in names
    assert f"trans{TRANSITION_WINDOW_CAPACITY + 1}Type" not in names
    for i in range(1, DISPLACEMENT_WINDOW_CAPACITY + 1):
        for suffix in ("Dir", "Cls", "Ratio"):
            assert f"disp{i}{suffix}" in names
    assert f"disp{DISPLACEMENT_WINDOW_CAPACITY + 1}Dir" not in names


# ---------------------------------------------------------------------------
# The correction: no P5 calibration constant crosses the boundary
# ---------------------------------------------------------------------------


def test_no_alternation_count_is_transported() -> None:
    """The field this pass removed. `_alternation_count` is parameterised by
    `range_window`, so shipping its result would freeze P5 configuration inside
    P6 where nothing could see it had gone stale."""
    names = {name for name, _t, _c in P5_TRANSPORT_EXT_FIELDS}
    assert "altCount4" not in names
    assert not any("alt" in name.lower() for name in names)


def test_no_retracement_depth_is_transported() -> None:
    """Three prices and a flag cross; the division and the 0.382 / 0.618 bands
    stay with the configuration that defines them."""
    names = {name for name, _t, _c in P5_TRANSPORT_EXT_FIELDS}
    assert not any("depth" in name.lower() or "retrace" in name.lower() for name in names)


def test_no_momentum_score_or_verdict_is_transported() -> None:
    names = {name for name, _t, _c in P5_TRANSPORT_EXT_FIELDS}
    for forbidden in ("score", "expansion", "accel", "strong", "fastflag"):
        assert not any(forbidden in name.lower() for name in names), forbidden


def test_raw_speed_ratios_cross_instead_of_threshold_results() -> None:
    """T2's 1.50 and momentum's 2.00 are configuration; the ratio is evidence."""
    assert RegimeEngineConfiguration().expansion_speed_ratio is not None
    assert MomentumBreakoutPullbackConfiguration().momentum_score_reference_ratio
    names = {name for name, _t, _c in P5_TRANSPORT_EXT_FIELDS}
    assert {"disp1Ratio", "disp2Ratio", "disp3Ratio"} <= names


# ---------------------------------------------------------------------------
# Capacity is checkable, which is the whole point of preferring it
# ---------------------------------------------------------------------------


def test_p5_configuration_fits_the_transport_capacity() -> None:
    """If a configured window outgrows the wire, this fails and names the
    capacity to raise -- rather than the port silently answering the old
    question with a short window."""
    trend = TrendEngineConfiguration()
    regime = RegimeEngineConfiguration()
    t3 = MomentumBreakoutPullbackConfiguration()
    assert trend.range_window <= TRANSITION_WINDOW_CAPACITY, (
        f"range_window {trend.range_window} exceeds transition capacity "
        f"{TRANSITION_WINDOW_CAPACITY}"
    )
    assert regime.recent_displacement_window <= DISPLACEMENT_WINDOW_CAPACITY
    assert t3.momentum_window <= DISPLACEMENT_WINDOW_CAPACITY


def test_the_default_windows_exactly_fill_the_capacity() -> None:
    """Stated so the capacity is understood as sized to today's configuration
    with zero slack, not as a comfortable margin."""
    assert TrendEngineConfiguration().range_window == TRANSITION_WINDOW_CAPACITY
    assert (
        RegimeEngineConfiguration().recent_displacement_window
        == DISPLACEMENT_WINDOW_CAPACITY
    )
    assert (
        MomentumBreakoutPullbackConfiguration().momentum_window
        == DISPLACEMENT_WINDOW_CAPACITY
    )


def test_the_two_displacement_windows_really_do_coincide() -> None:
    """The justification for one shared window rather than two."""
    assert (
        RegimeEngineConfiguration().recent_displacement_window
        == MomentumBreakoutPullbackConfiguration().momentum_window
    )


# ---------------------------------------------------------------------------
# The source claims the field list rests on
# ---------------------------------------------------------------------------


def test_breakout_takes_equal_levels_and_never_reads_them() -> None:
    """The reason no equal-level field exists. Checked against the function body
    rather than trusted, because the whole omission depends on it."""
    source = (_BTRC / "t3_engine.py").read_text(encoding="utf-8")
    start = source.index("def _assess_timeframe_breakout(")
    body = source[start : source.index("def _displacement_at(")]
    signature_end = body.index(") -> TimeframeBreakoutAssessment:")
    assert "equal_levels" in body[:signature_end]
    assert "equal_levels" not in body[signature_end:]
    assert "LIQUIDITY_SWEEP is intentionally NOT emitted in V1" in body


def test_displacement_at_matches_on_availability_and_takes_the_max() -> None:
    """`dispClsAtTrans` is not "the classification of the last displacement": it
    is the MAX classification among every displacement sharing the transition's
    availability time, and None when none do."""
    source = (_BTRC / "t3_engine.py").read_text(encoding="utf-8")
    body = source[source.index("def _displacement_at(") :]
    body = body[: body.index("def _assess_timeframe_pullback(")]
    assert "o.availability_time_utc == transition.availability_time_utc" in body
    assert "return None" in body
    assert "max(" in body


def test_prior_opposite_streak_excludes_the_last_transition() -> None:
    """`transitions[:-1]`, not `transitions`. An off-by-one here would make every
    fresh CHOCH look like an established reversal."""
    source = (_BTRC / "trend_engine.py").read_text(encoding="utf-8")
    body = source[source.index("def _prior_opposite_streak(") :]
    body = body[: body.index("def _alternation_count(")]
    assert "reversed(transitions[:-1])" in body


def test_the_pullback_split_is_inclusive_on_one_side_only() -> None:
    """origin uses `<=` and pullback uses `>` against the impulse swing's
    pivot_start_time_utc. Guessing the same comparator for both silently drops or
    duplicates the boundary swing."""
    source = (_BTRC / "t3_engine.py").read_text(encoding="utf-8")
    body = source[source.index("def _retracement_depth(") :]
    assert "s.pivot_start_time_utc <= impulse_top.pivot_start_time_utc" in body
    assert "s.pivot_start_time_utc > impulse_top.pivot_start_time_utc" in body


def test_exhaustion_compares_the_two_most_recent_same_type_swings() -> None:
    source = (_BTRC / "trend_engine.py").read_text(encoding="utf-8")
    body = source[source.index("def _exhaustion(") :]
    body = body[: body.index("def _assess_timeframe(")]
    assert "highs[-1].pivot_price < highs[-2].pivot_price" in body
    assert "lows[-1].pivot_price > lows[-2].pivot_price" in body


def test_ordering_keys_are_the_ones_the_reductions_must_reproduce() -> None:
    """Every reduction reads the LAST elements of an ordered sequence, so the
    ordering key is part of the contract, not an implementation detail."""
    trend = (_BTRC / "trend_engine.py").read_text(encoding="utf-8")
    assert "key=lambda t: (t.availability_time_utc, t.event_time_utc, str(t.record_id))" in trend
    regime = (_BTRC / "regime_engine.py").read_text(encoding="utf-8")
    assert "key=lambda o: (o.availability_time_utc, o.event_time_utc, str(o.record_id))" in regime
