"""BTRC-T5 deterministic confluence + analytical-permission engine.

Combines T1 trend, T2 regime, T3 momentum/breakout/pullback, T4 volatility/session,
plus the scanner's POI and BTMM outputs, into independent component scores and a
final confluence ranking, a trend-alignment classification, and an ANALYTICAL
permission. It is explainable, not a black-box trade generator, and it never
produces entry/stop/target/order semantics.

Hard analytical truth vs soft score: ``poi_valid`` and ``btmm_valid`` come from the
scanner and are NEVER changed by any score — a large trend score cannot make an
absent BTMM valid, and score arithmetic cannot revalidate an invalid POI. A valid
POI that is counter-trend stays valid; the result is COUNTER_TREND / WATCH_ONLY.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime

from btmm_ai_scanner.btrc.enums import (
    AnalyticalPermission,
    Direction,
    Regime,
    SignalLifecycleState,
    TrendAlignment,
    VolatilityState,
)
from btmm_ai_scanner.btrc.regime_engine import assess_regime
from btmm_ai_scanner.btrc.t3_engine import (
    assess_breakout,
    assess_momentum,
    assess_pullback,
)
from btmm_ai_scanner.btrc.t4_engine import assess_session, assess_volatility
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision, ComponentScores
from btmm_ai_scanner.btrc.trend_engine import assess_trend
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis

_BULLISH_SIDE = frozenset({Direction.BULLISH, Direction.STRONG_BULLISH})
_BEARISH_SIDE = frozenset({Direction.BEARISH, Direction.STRONG_BEARISH})
_REGIME_SCORE = {
    Regime.TREND: 90,
    Regime.EXPANSION: 80,
    Regime.BREAKOUT_PENDING: 65,
    Regime.DECELERATION: 50,
    Regime.COMPRESSION: 45,
    Regime.TRANSITION: 40,
    Regime.RANGE: 35,
    Regime.UNCERTAIN: 30,
}
_FAVORABLE_REGIME = frozenset({Regime.TREND, Regime.EXPANSION, Regime.BREAKOUT_PENDING})


def latest_poi(analysis: ScannerAnalysis) -> PoiObservation | None:
    observations = analysis.poi_analysis.poi_observations
    if not observations:
        return None
    return max(
        observations,
        key=lambda o: (o.availability_time_utc, str(o.record_id)),
    )


def assess_confluence(
    analysis: ScannerAnalysis,
    poi: PoiObservation,
    *,
    candles_by_timeframe: Mapping[Timeframe, Sequence[NormalizedCandle]] | None = None,
    evaluation_time_utc: datetime | None = None,
    configuration: ConfluenceConfiguration | None = None,
) -> BtrcDecision:
    config = configuration or ConfluenceConfiguration()
    poi_tf = poi.effective_timeframe
    poi_bullish = poi.direction is PoiDirection.BULLISH

    trend = assess_trend(analysis)
    regime = assess_regime(analysis)
    momentum = {m.timeframe: m for m in assess_momentum(analysis)}.get(poi_tf)
    breakout = {b.timeframe: b for b in assess_breakout(analysis)}.get(poi_tf)
    pullback = {p.timeframe: p for p in assess_pullback(analysis)}.get(poi_tf)

    supporting: list[str] = []
    opposing: list[str] = []
    missing: list[str] = []
    reject_watch: list[str] = []

    # --- hard truths (from the scanner; never overridden) ---
    btmm = next(
        (
            b
            for b in analysis.btmm_analysis.btmm_observations
            if b.source_poi_record_id == poi.record_id
        ),
        None,
    )
    btmm_valid = btmm is not None
    poi_state = next(
        (
            s
            for s in analysis.poi_analysis.current_poi_states
            if s.poi_record_id == poi.record_id
        ),
        None,
    )
    poi_lifecycle_status = poi_state.poi_lifecycle_status if poi_state else None

    global_direction = trend.global_direction

    # --- trend alignment ---
    poi_side = _BULLISH_SIDE if poi_bullish else _BEARISH_SIDE
    opposite_side = _BEARISH_SIDE if poi_bullish else _BULLISH_SIDE
    if global_direction in poi_side:
        operational = trend.operational_context
        alignment = (
            TrendAlignment.PARTIAL
            if operational in opposite_side
            else TrendAlignment.ALIGNED
        )
        supporting.append(f"global {global_direction.value} aligns with POI direction")
    elif global_direction in opposite_side:
        alignment = TrendAlignment.COUNTER_TREND
        opposing.append(
            f"global {global_direction.value} opposes the POI direction (counter-trend)"
        )
    else:
        alignment = TrendAlignment.NEUTRAL

    # --- component scores (independent) ---
    trend_score = {
        TrendAlignment.ALIGNED: 100
        if global_direction
        in {
            Direction.STRONG_BULLISH,
            Direction.STRONG_BEARISH,
        }
        else 80,
        TrendAlignment.PARTIAL: 60,
        TrendAlignment.NEUTRAL: 50,
        TrendAlignment.COUNTER_TREND: 20,
    }[alignment]

    regime_value = regime.regime
    regime_score = _REGIME_SCORE[regime_value]

    if momentum is None:
        momentum_score = 50
        missing.append("momentum")
    elif (momentum.direction.value.endswith("BULLISH")) == poi_bullish and (
        "NEUTRAL" not in momentum.direction.value
    ):
        momentum_score = min(100, 50 + momentum.momentum_score // 2)
    elif "NEUTRAL" in momentum.direction.value:
        momentum_score = 50
    else:
        momentum_score = max(0, 50 - momentum.momentum_score // 2)
        opposing.append("momentum opposes the POI direction")

    breakout_score = breakout.breakout_score if breakout is not None else 40
    if breakout is None:
        missing.append("breakout")

    poi_score = (
        {
            PoiStrengthTier.STRONG: 85,
            PoiStrengthTier.STANDARD: 60,
        }.get(poi.strength_tier, 50)
        if poi.strength_tier
        else 50
    )

    if btmm_valid:
        assert btmm is not None
        btmm_bullish = btmm.btmm_direction.value.startswith("BULLISH")
        btmm_score = 85 if btmm_bullish == poi_bullish else 70
        supporting.append("BTMM setup present for this POI")
    else:
        btmm_score = 25
        opposing.append("no BTMM setup references this POI")

    liquidity_score = 60 if btmm_valid else 40  # provisional; refined in a later phase

    volatility = None
    if candles_by_timeframe is not None and poi_tf in candles_by_timeframe:
        volatility = assess_volatility(list(candles_by_timeframe[poi_tf]))
        volatility_score = volatility.suitability_score
    else:
        volatility_score = 50
        missing.append("volatility")

    session = (
        assess_session(evaluation_time_utc) if evaluation_time_utc is not None else None
    )
    if session is None:
        missing.append("session")

    scores = ComponentScores(
        btmm_score=btmm_score,
        poi_score=poi_score,
        trend_score=trend_score,
        regime_score=regime_score,
        momentum_score=momentum_score,
        breakout_score=breakout_score,
        liquidity_score=liquidity_score,
        volatility_score=volatility_score,
    )
    final = _weighted_final(scores, config.weights)

    # --- analytical permission (soft never overrides hard) ---
    permission, permission_reasons = _permission(
        alignment=alignment,
        poi_bullish=poi_bullish,
        final=final,
        config=config,
        volatility=volatility,
    )
    reject_watch.extend(permission_reasons)

    lifecycle = _lifecycle(
        has_structure=bool(trend.timeframe_assessments),
        btmm_valid=btmm_valid,
        alignment=alignment,
        favorable_regime=regime_value in _FAVORABLE_REGIME,
        momentum_aligned=momentum_score >= 60,
        liquidity_ok=liquidity_score >= 60,
    )

    return BtrcDecision(
        symbol=analysis.symbol,
        evaluation_time_utc=analysis.availability_time_utc,
        poi_record_id=str(poi.record_id),
        poi_timeframe=poi_tf,
        poi_type=poi.poi_type,
        poi_direction=poi.direction,
        poi_valid=True,
        poi_lifecycle_status=poi_lifecycle_status,
        btmm_valid=btmm_valid,
        global_direction=global_direction,
        regime=regime_value,
        momentum_direction=momentum.direction if momentum else None,
        momentum_acceleration=momentum.acceleration if momentum else None,
        breakout_state=breakout.breakout_state if breakout else None,
        pullback_state=pullback.pullback_state if pullback else None,
        volatility_state=volatility.volatility_state if volatility else None,
        session_context=session.session_context if session else None,
        component_scores=scores,
        final_confluence_score=final,
        trend_alignment=alignment,
        analytical_permission=permission,
        lifecycle_state=lifecycle,
        supporting_reasons=tuple(supporting),
        opposing_reasons=tuple(opposing),
        missing_components=tuple(missing),
        rejection_or_watch_reasons=tuple(reject_watch),
        provenance_ids=(str(poi.record_id),)
        + ((str(btmm.record_id),) if btmm is not None else ()),
    )


def _weighted_final(scores: ComponentScores, weights: Mapping[str, int]) -> int:
    values = {
        "btmm": scores.btmm_score,
        "poi": scores.poi_score,
        "trend": scores.trend_score,
        "regime": scores.regime_score,
        "momentum": scores.momentum_score,
        "breakout": scores.breakout_score,
        "liquidity": scores.liquidity_score,
        "volatility": scores.volatility_score,
    }
    total_weight = sum(weights.get(k, 0) for k in values)
    if total_weight == 0:
        return 0
    weighted = sum(values[k] * weights.get(k, 0) for k in values)
    return round(weighted / total_weight)


def _permission(
    *,
    alignment: TrendAlignment,
    poi_bullish: bool,
    final: int,
    config: ConfluenceConfiguration,
    volatility: object,
) -> tuple[AnalyticalPermission, list[str]]:
    reasons: list[str] = []
    if alignment is TrendAlignment.COUNTER_TREND:
        if final < config.watch_only_min:
            reasons.append("counter-trend with low confluence")
            return AnalyticalPermission.WATCH_ONLY, reasons
        reasons.append("valid but counter-trend; execution priority low")
        return AnalyticalPermission.COUNTER_TREND, reasons
    if alignment is TrendAlignment.NEUTRAL:
        if final >= config.watch_only_min:
            return AnalyticalPermission.ALLOW_BOTH_CONTEXT, reasons
        reasons.append("neutral trend with low confluence")
        return AnalyticalPermission.WATCH_ONLY, reasons
    # ALIGNED / PARTIAL
    if final >= config.high_confluence_min:
        permission = (
            AnalyticalPermission.BUY_BIAS
            if poi_bullish
            else AnalyticalPermission.SELL_BIAS
        )
    elif final >= config.watch_only_min:
        reasons.append("aligned but only moderate confluence")
        permission = AnalyticalPermission.WATCH_ONLY
    else:
        reasons.append("aligned but low confluence")
        permission = AnalyticalPermission.NO_TRADE_CONTEXT

    if (
        config.downgrade_on_extreme_volatility
        and isinstance(volatility, object)
        and getattr(volatility, "volatility_state", None) is VolatilityState.EXTREME
        and permission
        in (AnalyticalPermission.BUY_BIAS, AnalyticalPermission.SELL_BIAS)
    ):
        reasons.append("extreme volatility lowers suitability (direction unchanged)")
        permission = AnalyticalPermission.WATCH_ONLY
    return permission, reasons


def _lifecycle(
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
    state = SignalLifecycleState.POI_VALIDATED  # poi is the evaluated candidate
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
