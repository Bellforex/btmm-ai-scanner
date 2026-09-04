"""Does `t5_aggregator_pine_model.py` reproduce `_weighted_final`, `_permission`
and `_lifecycle` from `t5_engine.py`?

Unlike the component-score formulas, these three ARE separately-callable
private functions, so this differentials against them directly -- the same
strength of evidence as T1-T4's own suites. `weighted_final`'s specific
findings (missing-weight exclusion, computed denominator, banker's rounding,
the `<`/`>=` comparator asymmetry) were already traced in
`test_p5_aggregator_arithmetic.py`; this file proves the ACTUAL model
implements them, exhaustively where the domain is small enough (`_permission`,
`_lifecycle`) and by randomized differential where it is not
(`weighted_final`'s continuous score/weight space).
"""

from __future__ import annotations

import random
from itertools import product
from types import SimpleNamespace

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    SignalLifecycleState,
    TrendAlignment,
    VolatilityState,
)
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_decision import ComponentScores
from btmm_ai_scanner.btrc.t5_engine import _lifecycle, _permission, _weighted_final
from tests.parity_support.t5_aggregator_pine_model import (
    SCORED_KEYS,
    lifecycle,
    permission,
    weighted_final,
)

_CFG = ConfluenceConfiguration()


def _scores(**overrides: int) -> ComponentScores:
    base = {
        "btmm_score": 50,
        "poi_score": 50,
        "trend_score": 50,
        "regime_score": 50,
        "momentum_score": 50,
        "breakout_score": 50,
        "liquidity_score": 50,
        "volatility_score": 50,
    }
    base.update(overrides)
    return ComponentScores(**base)


def _values(**overrides: int) -> dict[str, int]:
    base = dict.fromkeys(SCORED_KEYS, 50)
    base.update(overrides)
    return base


def real_permission(
    *, alignment, poi_bullish, final, config, volatility_state
):
    volatility = None if volatility_state is None else SimpleNamespace(volatility_state=volatility_state)
    return _permission(
        alignment=alignment,
        poi_bullish=poi_bullish,
        final=final,
        config=config,
        volatility=volatility,
    )


def wire_permission(*, alignment, poi_bullish, final, config, volatility_state):
    return permission(
        alignment=alignment,
        poi_bullish=poi_bullish,
        final=final,
        watch_only_min=config.watch_only_min,
        high_confluence_min=config.high_confluence_min,
        downgrade_on_extreme_volatility=config.downgrade_on_extreme_volatility,
        volatility_state=volatility_state,
    )


# ---------------------------------------------------------------------------
# weighted_final
# ---------------------------------------------------------------------------


def test_weighted_final_matches_default_config() -> None:
    values = _values(btmm=85, poi=60, trend=50, regime=50, momentum=50, breakout=40, liquidity=60)
    weights = dict(_CFG.weights)
    assert weighted_final(values, weights) == _weighted_final(_scores(
        btmm_score=85, poi_score=60, breakout_score=40, liquidity_score=60,
    ), weights)


def test_weighted_final_empty_weights_is_zero() -> None:
    assert weighted_final(_values(), {}) == 0 == _weighted_final(_scores(), {})


def test_weighted_final_randomized_against_the_real_helper() -> None:
    rng = random.Random(31337)
    mismatches = []
    for _ in range(3000):
        values = {k: rng.randint(0, 100) for k in SCORED_KEYS}
        weights = {k: rng.randint(0, 5) for k in SCORED_KEYS if rng.random() < 0.85}
        scores = ComponentScores(
            btmm_score=values["btmm"],
            poi_score=values["poi"],
            trend_score=values["trend"],
            regime_score=values["regime"],
            momentum_score=values["momentum"],
            breakout_score=values["breakout"],
            liquidity_score=values["liquidity"],
            volatility_score=values["volatility"],
        )
        real = _weighted_final(scores, weights)
        wire = weighted_final(values, weights)
        if real != wire:
            mismatches.append((values, weights, real, wire))
    assert mismatches == [], mismatches[:5]


def test_weighted_final_banker_rounding_ties() -> None:
    # Reconstructs the frozen 9dc5792 finding: dropping volatility's weight
    # makes the denominator 12 (even), reaching an exact .5 tie -- constructed
    # here as weighted=6 (btmm_score=2, weight 3, everything else 0), so
    # 6 / 12 == 0.5 exactly, and Python rounds that HALF-TO-EVEN (0), unlike
    # Pine's math.round which would round it away from zero (1).
    weights = {k: v for k, v in dict(_CFG.weights).items() if k != "volatility"}
    values = {k: 0 for k in SCORED_KEYS}
    values["btmm"] = 2
    scores = ComponentScores(
        btmm_score=2, poi_score=0, trend_score=0, regime_score=0,
        momentum_score=0, breakout_score=0, liquidity_score=0, volatility_score=0,
    )
    assert sum(weights.values()) == 12
    real = _weighted_final(scores, weights)
    wire = weighted_final(values, weights)
    assert real == wire == 0  # banker's rounding: 0.5 -> 0 (nearest even)


# ---------------------------------------------------------------------------
# permission: exhaustive over the enum-sized domain
# ---------------------------------------------------------------------------


def test_exhaustive_permission() -> None:
    finals = (0, 20, 44, 45, 46, 64, 65, 66, 100)
    vol_states = (None, VolatilityState.EXTREME, VolatilityState.NORMAL)
    mismatches = []
    for alignment, poi_bullish, final, downgrade, vol in product(
        TrendAlignment, (True, False), finals, (True, False), vol_states
    ):
        config = ConfluenceConfiguration(downgrade_on_extreme_volatility=downgrade)
        real = real_permission(
            alignment=alignment, poi_bullish=poi_bullish, final=final,
            config=config, volatility_state=vol,
        )
        wire = wire_permission(
            alignment=alignment, poi_bullish=poi_bullish, final=final,
            config=config, volatility_state=vol,
        )
        if real[0] != wire[0]:
            mismatches.append((alignment, poi_bullish, final, downgrade, vol, real[0], wire[0]))
    assert mismatches == [], mismatches[:10]


def test_at_exactly_45_counter_trend_is_not_downgraded() -> None:
    real, _ = real_permission(
        alignment=TrendAlignment.COUNTER_TREND, poi_bullish=True, final=45,
        config=_CFG, volatility_state=None,
    )
    assert real is AnalyticalPermission.COUNTER_TREND


def test_at_exactly_45_neutral_clears_the_band() -> None:
    real, _ = real_permission(
        alignment=TrendAlignment.NEUTRAL, poi_bullish=True, final=45,
        config=_CFG, volatility_state=None,
    )
    assert real is AnalyticalPermission.ALLOW_BOTH_CONTEXT


# ---------------------------------------------------------------------------
# lifecycle: fully exhaustive (128 combinations)
# ---------------------------------------------------------------------------


def test_exhaustive_lifecycle() -> None:
    mismatches = []
    bools = (True, False)
    for has_structure, btmm_valid, alignment, favorable_regime, momentum_aligned, liquidity_ok in product(
        bools, bools, TrendAlignment, bools, bools, bools
    ):
        real = _lifecycle(
            has_structure=has_structure, btmm_valid=btmm_valid, alignment=alignment,
            favorable_regime=favorable_regime, momentum_aligned=momentum_aligned,
            liquidity_ok=liquidity_ok,
        )
        wire = lifecycle(
            has_structure=has_structure, btmm_valid=btmm_valid, alignment=alignment,
            favorable_regime=favorable_regime, momentum_aligned=momentum_aligned,
            liquidity_ok=liquidity_ok,
        )
        if real != wire:
            mismatches.append(
                (has_structure, btmm_valid, alignment, favorable_regime,
                 momentum_aligned, liquidity_ok, real, wire)
            )
    assert mismatches == [], mismatches[:10]


def test_lifecycle_covers_every_reachable_state() -> None:
    """BTMM_VALIDATED is assigned in the source but immediately overwritten by
    POI_VALIDATED with no intervening return -- it is provably unreachable as
    a terminal result, not merely untested. Excluding it here is a stated
    fact about the source, not a gap in this campaign's coverage."""
    seen: set[SignalLifecycleState] = set()
    bools = (True, False)
    for combo in product(bools, bools, TrendAlignment, bools, bools, bools):
        has_structure, btmm_valid, alignment, favorable_regime, momentum_aligned, liquidity_ok = combo
        seen.add(
            _lifecycle(
                has_structure=has_structure, btmm_valid=btmm_valid, alignment=alignment,
                favorable_regime=favorable_regime, momentum_aligned=momentum_aligned,
                liquidity_ok=liquidity_ok,
            )
        )
    assert SignalLifecycleState.BTMM_VALIDATED not in seen
    assert seen == {
        SignalLifecycleState.DETECTED,
        SignalLifecycleState.STRUCTURALLY_VALIDATED,
        SignalLifecycleState.POI_VALIDATED,
        SignalLifecycleState.TREND_VALIDATED,
        SignalLifecycleState.REGIME_VALIDATED,
        SignalLifecycleState.MOMENTUM_VALIDATED,
        SignalLifecycleState.LIQUIDITY_VALIDATED,
    }


# ---------------------------------------------------------------------------
# Mutations
# ---------------------------------------------------------------------------


def test_mutation_lifecycle_btmm_and_poi_validated_are_not_independently_gated() -> None:
    """POI_VALIDATED is reached unconditionally once BTMM_VALIDATED is (the
    evaluated candidate IS the POI) -- a port that added its own extra gate
    there would incorrectly stall some cases at BTMM_VALIDATED."""
    result = lifecycle(
        has_structure=True, btmm_valid=True, alignment=TrendAlignment.COUNTER_TREND,
        favorable_regime=False, momentum_aligned=False, liquidity_ok=False,
    )
    assert result == SignalLifecycleState.POI_VALIDATED
    assert result != SignalLifecycleState.BTMM_VALIDATED


def test_mutation_permission_symmetric_comparator_is_caught() -> None:
    """Guessing `<=` for counter-trend (matching every other branch's `>=`
    the wrong way) flips the result exactly at watch_only_min."""
    real, _ = real_permission(
        alignment=TrendAlignment.COUNTER_TREND, poi_bullish=True, final=_CFG.watch_only_min,
        config=_CFG, volatility_state=None,
    )
    guessed_le = (
        AnalyticalPermission.WATCH_ONLY
        if _CFG.watch_only_min <= _CFG.watch_only_min
        else AnalyticalPermission.COUNTER_TREND
    )
    assert real == AnalyticalPermission.COUNTER_TREND
    assert guessed_le == AnalyticalPermission.WATCH_ONLY
    assert real != guessed_le
