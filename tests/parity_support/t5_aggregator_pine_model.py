"""The PINE-EQUIVALENT T5 weighted aggregator / permission / lifecycle.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

Unlike the component-score formulas (`t5_component_scores_pine_model.py`),
`_weighted_final`, `_permission` and `_lifecycle` in `t5_engine.py` ARE
separately-callable private functions, so `test_t5_aggregator_sufficiency.py`
differentials this module against the REAL functions directly -- the same
strength of evidence T1-T4 have, not the transcription-based method the
component scores needed.

The exact arithmetic (missing-weight-key exclusion, denominator always
computed, `round()` banker's rounding vs Pine's `math.round`, the `<` vs `>=`
comparator asymmetry at the bands) was already traced and frozen in
`test_p5_aggregator_arithmetic.py` (commit `9dc5792`, predates this module) --
this module is the actual Pine-equivalent implementation of those findings,
not a re-derivation of them.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    SignalLifecycleState,
    TrendAlignment,
    VolatilityState,
)

SCORED_KEYS: tuple[str, ...] = (
    "btmm",
    "poi",
    "trend",
    "regime",
    "momentum",
    "breakout",
    "liquidity",
    "volatility",
)


def weighted_final(values: dict[str, int], weights: dict[str, int]) -> int:
    """`_weighted_final`, reconstructed exactly: a key absent from `weights`
    contributes zero to BOTH the numerator and the denominator (excluded, not
    zeroed), and the denominator is always recomputed, never a hardcoded
    default. `round()` is Python's own banker's rounding -- the SAME behaviour
    Pine's port must implement by hand, since `math.round` in Pine rounds
    ties away from zero instead."""
    total_weight = sum(weights.get(k, 0) for k in values)
    if total_weight == 0:
        return 0
    weighted = sum(values[k] * weights.get(k, 0) for k in values)
    return round(weighted / total_weight)


def permission(
    *,
    alignment: TrendAlignment,
    poi_bullish: bool,
    final: int,
    watch_only_min: int,
    high_confluence_min: int,
    downgrade_on_extreme_volatility: bool,
    volatility_state: VolatilityState | None,
) -> tuple[AnalyticalPermission, list[str]]:
    """`_permission`, reconstructed exactly: COUNTER_TREND's own downgrade
    check uses strict `<`, while every other branch here uses `>=` -- an
    asymmetry the source states as two different comparators, not a rounding
    accident, so this keeps them textually distinct rather than "simplifying"
    to one shared comparison."""
    reasons: list[str] = []
    if alignment is TrendAlignment.COUNTER_TREND:
        if final < watch_only_min:
            reasons.append("counter-trend with low confluence")
            return AnalyticalPermission.WATCH_ONLY, reasons
        reasons.append("valid but counter-trend; execution priority low")
        return AnalyticalPermission.COUNTER_TREND, reasons
    if alignment is TrendAlignment.NEUTRAL:
        if final >= watch_only_min:
            return AnalyticalPermission.ALLOW_BOTH_CONTEXT, reasons
        reasons.append("neutral trend with low confluence")
        return AnalyticalPermission.WATCH_ONLY, reasons

    if final >= high_confluence_min:
        result = AnalyticalPermission.BUY_BIAS if poi_bullish else AnalyticalPermission.SELL_BIAS
    elif final >= watch_only_min:
        reasons.append("aligned but only moderate confluence")
        result = AnalyticalPermission.WATCH_ONLY
    else:
        reasons.append("aligned but low confluence")
        result = AnalyticalPermission.NO_TRADE_CONTEXT

    if (
        downgrade_on_extreme_volatility
        and volatility_state is VolatilityState.EXTREME
        and result in (AnalyticalPermission.BUY_BIAS, AnalyticalPermission.SELL_BIAS)
    ):
        reasons.append("extreme volatility lowers suitability (direction unchanged)")
        result = AnalyticalPermission.WATCH_ONLY
    return result, reasons


def lifecycle(
    *,
    has_structure: bool,
    btmm_valid: bool,
    alignment: TrendAlignment,
    favorable_regime: bool,
    momentum_aligned: bool,
    liquidity_ok: bool,
) -> SignalLifecycleState:
    state = SignalLifecycleState.DETECTED
    if not has_structure:
        return state
    state = SignalLifecycleState.STRUCTURALLY_VALIDATED
    if not btmm_valid:
        return state
    state = SignalLifecycleState.BTMM_VALIDATED
    state = SignalLifecycleState.POI_VALIDATED
    if alignment not in (TrendAlignment.ALIGNED, TrendAlignment.PARTIAL):
        return state
    state = SignalLifecycleState.TREND_VALIDATED
    if not favorable_regime:
        return state
    state = SignalLifecycleState.REGIME_VALIDATED
    if not momentum_aligned:
        return state
    state = SignalLifecycleState.MOMENTUM_VALIDATED
    if not liquidity_ok:
        return state
    return SignalLifecycleState.LIQUIDITY_VALIDATED
