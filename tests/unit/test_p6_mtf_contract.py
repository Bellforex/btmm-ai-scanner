"""P6-I0: the cross-timeframe contract BTRC actually requires.

P6 exists only to feed P5, so its contract is whatever P5 reads and nothing
more. These tests freeze that surface from production source before any Pine
transport is designed against it, because every one of the facts below is the
kind that a plausible-sounding port would get subtly wrong.

Nothing here changes production semantics; it is contract hardening only.
"""

from __future__ import annotations

import inspect

import pytest

from btmm_ai_scanner.btrc import (
    regime_engine,
    t3_engine,
    t4_engine,
    t5_engine,
    trend_engine,
)
from btmm_ai_scanner.btrc.enums import Direction
from btmm_ai_scanner.config.enums import Timeframe

_BULL = Direction.BULLISH
_BEAR = Direction.BEARISH
_NEUTRAL = Direction.NEUTRAL


# ---------------------------------------------------------------------------
# The required timeframe set, and the fact that two engines rank it differently
# ---------------------------------------------------------------------------


def test_t1_authority_order_is_frozen() -> None:
    assert trend_engine._AUTHORITY_TIMEFRAMES == (
        Timeframe.W1,
        Timeframe.D1,
        Timeframe.H4,
        Timeframe.H1,
        Timeframe.M15,
        Timeframe.M5,
    )


def test_t2_primary_order_is_frozen_and_differs_from_t1() -> None:
    """A trap for the port. T2 ranks D1 above H4 above W1; T1 lists W1 first.

    Reusing one ordering for both engines would be an easy and invisible error,
    so the difference is pinned rather than left to be noticed.
    """
    assert regime_engine._PRIMARY_ORDER == (
        Timeframe.D1,
        Timeframe.H4,
        Timeframe.W1,
        Timeframe.H1,
        Timeframe.M15,
        Timeframe.M5,
    )
    assert regime_engine._PRIMARY_ORDER != trend_engine._AUTHORITY_TIMEFRAMES
    assert set(regime_engine._PRIMARY_ORDER) == set(trend_engine._AUTHORITY_TIMEFRAMES)


def test_p5_never_requires_m1() -> None:
    """P4's supported set is {M1, M5, M15}; P5's authority set contains no M1 at
    all. P6 must not transport it, and P4 must not be asked for W1/D1/H4."""
    assert Timeframe.M1 not in trend_engine._AUTHORITY_TIMEFRAMES
    assert Timeframe.M1 not in regime_engine._PRIMARY_ORDER


# ---------------------------------------------------------------------------
# Which timeframes are load-bearing for the fusion
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", [Timeframe.H1, Timeframe.M15, Timeframe.M5])
@pytest.mark.parametrize("direction", [_BULL, _BEAR, _NEUTRAL])
def test_lower_timeframes_never_change_global_direction(
    timeframe: Timeframe, direction: Direction
) -> None:
    """The docstring claims "H1/M15/M5 NEVER change global direction". Proven
    rather than trusted: with W1/D1/H4 held fixed, no value of a lower timeframe
    moves the result."""
    base = {Timeframe.D1: _BULL, Timeframe.W1: _BULL, Timeframe.H4: _BULL}
    expected = trend_engine._resolve_global(dict(base))
    assert trend_engine._resolve_global({**base, timeframe: direction}) == expected


def test_d1_alone_decides_the_side() -> None:
    assert trend_engine._resolve_global({Timeframe.D1: _BULL}) is Direction.BULLISH
    assert trend_engine._resolve_global({Timeframe.D1: _BEAR}) is Direction.BEARISH


def test_w1_and_h4_agreement_strengthens_d1() -> None:
    strong = trend_engine._resolve_global(
        {Timeframe.D1: _BULL, Timeframe.W1: _BULL, Timeframe.H4: _BULL}
    )
    assert strong is Direction.STRONG_BULLISH
    # either one missing or disagreeing drops it back to plain BULLISH
    assert (
        trend_engine._resolve_global({Timeframe.D1: _BULL, Timeframe.W1: _BULL})
        is Direction.BULLISH
    )
    assert (
        trend_engine._resolve_global(
            {Timeframe.D1: _BULL, Timeframe.W1: _BULL, Timeframe.H4: _BEAR}
        )
        is Direction.BULLISH
    )


def test_w1_plus_h4_give_a_provisional_direction_when_d1_is_absent() -> None:
    """The branch a port is most likely to drop: with no D1 at all, W1+H4
    agreement still yields a direction -- but never a STRONG one."""
    assert (
        trend_engine._resolve_global({Timeframe.W1: _BULL, Timeframe.H4: _BULL})
        is Direction.BULLISH
    )
    assert (
        trend_engine._resolve_global({Timeframe.W1: _BEAR, Timeframe.H4: _BEAR})
        is Direction.BEARISH
    )


def test_absence_degrades_to_neutral_and_never_raises() -> None:
    """P6 transport must reproduce degradation, not block on a missing feed."""
    assert trend_engine._resolve_global({}) is Direction.NEUTRAL
    assert (
        trend_engine._resolve_global({Timeframe.M15: _BULL, Timeframe.M5: _BULL})
        is Direction.NEUTRAL
    )
    # a lone macro or operational timeframe is not enough on its own
    assert trend_engine._resolve_global({Timeframe.W1: _BULL}) is Direction.NEUTRAL
    assert trend_engine._resolve_global({Timeframe.H4: _BULL}) is Direction.NEUTRAL


def test_disagreeing_w1_and_h4_without_d1_is_neutral() -> None:
    assert (
        trend_engine._resolve_global({Timeframe.W1: _BULL, Timeframe.H4: _BEAR})
        is Direction.NEUTRAL
    )


def test_a_neutral_d1_falls_through_rather_than_forcing_neutral() -> None:
    """D1 present-but-NEUTRAL must behave like D1 absent, not short-circuit."""
    with_neutral_d1 = trend_engine._resolve_global(
        {Timeframe.D1: _NEUTRAL, Timeframe.W1: _BULL, Timeframe.H4: _BULL}
    )
    without_d1 = trend_engine._resolve_global(
        {Timeframe.W1: _BULL, Timeframe.H4: _BULL}
    )
    assert with_neutral_d1 is without_d1 is Direction.BULLISH


def test_the_load_bearing_set_is_exactly_three_timeframes() -> None:
    """Stated as a property: perturbing any of W1/D1/H4 can change the result,
    and perturbing any other authority timeframe never can."""
    base = {Timeframe.D1: _BULL, Timeframe.W1: _BULL, Timeframe.H4: _BULL}
    load_bearing = set()
    for timeframe in trend_engine._AUTHORITY_TIMEFRAMES:
        for candidate in (_BULL, _BEAR, _NEUTRAL):
            probe = {**base, timeframe: candidate}
            if trend_engine._resolve_global(probe) != trend_engine._resolve_global(
                dict(base)
            ):
                load_bearing.add(timeframe)
    assert load_bearing == {Timeframe.W1, Timeframe.D1, Timeframe.H4}


# ---------------------------------------------------------------------------
# The component dependency graph
# ---------------------------------------------------------------------------


def test_regime_depends_on_trend() -> None:
    """T2 is NOT independent: `assess_regime` calls `assess_trend` itself. A port
    that computes regime without trend has no source for its trend_state."""
    source = inspect.getsource(regime_engine.assess_regime)
    assert "assess_trend(" in source


def test_trend_momentum_and_volatility_are_independent_roots() -> None:
    """T1, T3 and T4 read upstream analysis (or candles) only -- never another
    BTRC component's output. They may be implemented and proven in any order."""
    for function in (
        trend_engine.assess_trend,
        t3_engine.assess_momentum,
        t3_engine.assess_breakout,
        t4_engine.assess_volatility,
        t4_engine.assess_session,
    ):
        # drop the signature line, or a function trivially "consumes" itself
        body = inspect.getsource(function).splitlines()[1:]
        source = chr(10).join(body)
        for other in ("assess_trend(", "assess_regime(", "assess_confluence("):
            if other.rstrip("(") == function.__name__:
                continue
            assert other not in source, f"{function.__name__} consumes {other}"


def test_session_is_a_pure_function_of_time() -> None:
    """`assess_session` takes only a datetime -- no candles, no analysis. It is
    the one BTRC input P6 does not have to transport at all."""
    parameters = list(inspect.signature(t4_engine.assess_session).parameters)
    assert parameters[0] == "evaluation_time_utc"
    assert "analysis" not in parameters
    assert "candles" not in parameters


def test_volatility_takes_candles_not_analysis() -> None:
    """So P6 must carry raw candles for the POI's timeframe, not only derived
    P1/P2 records."""
    parameters = list(inspect.signature(t4_engine.assess_volatility).parameters)
    assert parameters[0] == "candles"
    assert "analysis" not in parameters


# ---------------------------------------------------------------------------
# The P4 -> P5 contract, restated as a guard
# ---------------------------------------------------------------------------


def test_btrc_reads_no_btmm_lifecycle_state() -> None:
    """The reason the deferred reviewed-evidence transport does not block P5.

    If BTRC ever starts reading a lifecycle status, that changes, and this test
    is where it should be noticed.
    """
    import pathlib

    package = pathlib.Path(t5_engine.__file__).parent
    forbidden = (
        "BtmmLifecycleStatus",
        "BTMM_CONFIRMED",
        "current_btmm_states",
        "btmm_lifecycle",
    )
    offenders: list[str] = []
    for path in sorted(package.glob("*.py")):
        text = path.read_text(encoding="utf-8")
        for needle in forbidden:
            if needle in text:
                offenders.append(f"{path.name}: {needle}")
    assert offenders == [], offenders


def test_btrc_reads_exactly_three_attributes_from_a_btmm_observation() -> None:
    source = inspect.getsource(t5_engine.assess_confluence)
    assert "analysis.btmm_analysis.btmm_observations" in source
    assert "btmm_valid = btmm is not None" in source
    assert "btmm.btmm_direction" in source


# ---------------------------------------------------------------------------
# Calibration stays provisional (author decision C-1)
# ---------------------------------------------------------------------------


def test_confluence_calibration_is_marked_provisional_in_source() -> None:
    """C-1: the mechanism is ported, the numbers are not blessed. If this marker
    ever disappears, the parity contract would start implying approval the
    source never gave."""
    from btmm_ai_scanner.btrc import t5_configuration

    doc = t5_configuration.__doc__ or ""
    assert "ENGINEERING-PROVISIONAL" in doc
    assert "NOT production-approved" in doc


def test_the_provisional_weights_and_bands_are_what_the_port_must_carry() -> None:
    from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration

    config = ConfluenceConfiguration()
    assert config.weights == {
        "btmm": 3,
        "poi": 3,
        "trend": 2,
        "regime": 1,
        "momentum": 1,
        "breakout": 1,
        "liquidity": 1,
        "volatility": 1,
    }
    assert config.high_confluence_min == 65
    assert config.watch_only_min == 45


# ---------------------------------------------------------------------------
# The minimal transport surface (Phase 18)
# ---------------------------------------------------------------------------
#
# "P1 + P2, six times over" is what the architecture said before this was
# traced. It overstates the job. P1 publishes five collections and BTRC reads
# three; P2 publishes three semantic items and BTRC reads two. The two P1
# collections nobody reads are also the two most expensive to produce.

P1_COLLECTIONS = (
    "confirmed_swings",
    "displacement_observations",
    "equal_level_clusters",
    "support_resistance_zones",
    "trendlines",
)
P1_REQUIRED = ("confirmed_swings", "displacement_observations", "equal_level_clusters")

P2_ITEMS = ("swing_relationships", "structure_transitions", "current_state")
P2_REQUIRED = ("structure_transitions", "current_state")


def _btrc_sources() -> str:
    import pathlib

    package = pathlib.Path(t5_engine.__file__).parent
    return "\n".join(
        p.read_text(encoding="utf-8") for p in sorted(package.glob("*.py"))
    )


def test_btrc_reads_only_three_of_p1s_five_collections() -> None:
    text = _btrc_sources()
    read = {name for name in P1_COLLECTIONS if name in text}
    assert read == set(P1_REQUIRED)


def test_support_resistance_and_trendlines_are_never_read() -> None:
    """The most valuable exclusion. S/R zones carry the tracker and fold-cache
    machinery that dominated P3's difficulty, and BTRC wants neither them nor
    trendlines -- so the higher-timeframe engines P6 stands up do not have to
    produce either."""
    text = _btrc_sources()
    assert "support_resistance_zones" not in text
    assert "trendlines" not in text


def test_btrc_reads_only_two_of_p2s_three_items() -> None:
    text = _btrc_sources()
    read = {name for name in P2_ITEMS if name in text}
    assert read == set(P2_REQUIRED)


def test_poi_lifecycle_transitions_are_read_flat_not_per_timeframe() -> None:
    """Decisive for P6 scope: P3 does NOT have to run on six timeframes.

    The pullback assessment binds `lifecycle` ONCE from the analysis and hands
    the same flat collection to every timeframe, rather than indexing it by
    timeframe the way it does for swings and structure state.
    """
    source = inspect.getsource(t3_engine)
    assert "lifecycle = analysis.poi_analysis.poi_lifecycle_transitions" in source
    # the per-timeframe dicts exist for P1/P2 inputs, but never for POI lifecycle
    assert "lifecycle_by_tf" not in source


def test_the_transport_surface_is_five_things_per_timeframe() -> None:
    """Stated as one number so a future widening is visible: three P1
    collections plus two P2 items, per authority timeframe."""
    assert len(P1_REQUIRED) + len(P2_REQUIRED) == 5
