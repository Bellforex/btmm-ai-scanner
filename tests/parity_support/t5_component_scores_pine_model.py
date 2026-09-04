"""The PINE-EQUIVALENT T5 component-score / trend-alignment formulas.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY THIS IS VERIFIED BY TRANSCRIPTION, NOT BY CALLING A PRODUCTION HELPER
------------------------------------------------------------------------
Unlike T1-T4, `t5_engine.assess_confluence` never factors its component-score
arithmetic into separately-callable private functions (`_weighted_final`,
`_permission` and `_lifecycle` ARE separable, and this campaign's differential
against them lives in `test_t5_aggregator_sufficiency.py`). The eight
component-score formulas are inline in one long function body operating on a
full `ScannerAnalysis` + `PoiObservation`, which -- with only a single required
timeframe (matching this repo's existing Layer-2 harness in
`test_btrc_t5_confluence.py`) -- can only ever produce `global_direction ==
NEUTRAL` (no D1/W1/H4 assessment exists to feed `_resolve_global`), so an
end-to-end integration differential could never actually exercise the
ALIGNED/PARTIAL/COUNTER_TREND branches at all.

So `test_t5_component_scores_sufficiency.py` verifies each formula below by
the SAME already-accepted method `test_p5_aggregator_arithmetic.py` (commit
`9dc5792`) established for `_weighted_final` itself: transcribe the exact
source text, assert the transcription's characteristic lines are literally
present in `t5_engine.py` (so a source edit that changes the formula fails
loudly rather than silently), and differential-test THIS module against a
literal Python transcription of that verified text across many combinations
-- plus a handful of genuine end-to-end `assess_confluence` integration
checks, to catch a wiring mistake (wrong field, wrong default) neither
transcription alone would catch.

EVERY INPUT HERE IS ALREADY WIRE-PROVEN OR ALREADY AN EXISTING PINE INPUT
---------------------------------------------------------------------------
`global_direction`/`operational_context` come from T5's own trend resolver
(`t5_trend_pine_model.py`, itself wire-derived from T1). `regime` is T2's own
output. `momentum_direction`/`momentum_score` are T3's. `breakout_score` is
T3's. `volatility_suitability` is T4's. `poi_bullish`/`poi_strength_tier` are
P3 POI outputs; `btmm_valid`/`btmm_bullish` are P4 BTMM outputs -- both
already-existing Pine values from earlier, already-closed phases. So no new
transport field is needed here either.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import (
    Direction,
    MomentumDirection,
    Regime,
    TrendAlignment,
)
from btmm_ai_scanner.poi.enums import PoiStrengthTier

_BULLISH_SIDE = frozenset({Direction.STRONG_BULLISH, Direction.BULLISH})
_BEARISH_SIDE = frozenset({Direction.STRONG_BEARISH, Direction.BEARISH})
_STRONG_SIDE = frozenset({Direction.STRONG_BULLISH, Direction.STRONG_BEARISH})

#: `t5_engine._REGIME_SCORE`, transcribed verbatim.
REGIME_SCORE: dict[Regime, int] = {
    Regime.TREND: 90,
    Regime.EXPANSION: 80,
    Regime.BREAKOUT_PENDING: 65,
    Regime.DECELERATION: 50,
    Regime.COMPRESSION: 45,
    Regime.TRANSITION: 40,
    Regime.RANGE: 35,
    Regime.UNCERTAIN: 30,
}


def trend_alignment(
    global_direction: Direction, operational_context: Direction, poi_bullish: bool
) -> TrendAlignment:
    poi_side = _BULLISH_SIDE if poi_bullish else _BEARISH_SIDE
    opposite_side = _BEARISH_SIDE if poi_bullish else _BULLISH_SIDE
    if global_direction in poi_side:
        return (
            TrendAlignment.PARTIAL
            if operational_context in opposite_side
            else TrendAlignment.ALIGNED
        )
    if global_direction in opposite_side:
        return TrendAlignment.COUNTER_TREND
    return TrendAlignment.NEUTRAL


def trend_score(alignment: TrendAlignment, global_direction: Direction) -> int:
    if alignment is TrendAlignment.ALIGNED:
        return 100 if global_direction in _STRONG_SIDE else 80
    return {
        TrendAlignment.PARTIAL: 60,
        TrendAlignment.NEUTRAL: 50,
        TrendAlignment.COUNTER_TREND: 20,
    }[alignment]


def regime_score(regime: Regime) -> int:
    return REGIME_SCORE[regime]


def momentum_score(
    momentum_direction: MomentumDirection | None,
    momentum_momentum_score: int,
    poi_bullish: bool,
) -> int:
    if momentum_direction is None:
        return 50
    dv = momentum_direction.value
    if (dv.endswith("BULLISH")) == poi_bullish and "NEUTRAL" not in dv:
        return min(100, 50 + momentum_momentum_score // 2)
    if "NEUTRAL" in dv:
        return 50
    return max(0, 50 - momentum_momentum_score // 2)


def breakout_score(breakout_breakout_score: int | None) -> int:
    return breakout_breakout_score if breakout_breakout_score is not None else 40


def poi_score(strength_tier: PoiStrengthTier | None) -> int:
    if not strength_tier:
        return 50
    return {PoiStrengthTier.STRONG: 85, PoiStrengthTier.STANDARD: 60}.get(strength_tier, 50)


def btmm_score(btmm_valid: bool, btmm_bullish: bool, poi_bullish: bool) -> int:
    if not btmm_valid:
        return 25
    return 85 if btmm_bullish == poi_bullish else 70


def liquidity_score(btmm_valid: bool) -> int:
    return 60 if btmm_valid else 40


def volatility_score(suitability_score: int | None) -> int:
    return suitability_score if suitability_score is not None else 50
