# BTRC-V1 — T2 Deterministic Regime Engine

Status: **T2 implemented** on `btrc-v1`. Regime is a **direction-INDEPENDENT**
behaviour dimension — it never encodes bullish/bearish polarity, never decides POI/
BTMM validity, and never mutates a scanner record. Code:
`btrc/regime_engine.py`, `regime_assessment.py`, `regime_configuration.py`. Entry:
`assess_regime(analysis, trend_config?, regime_config?) -> RegimeAssessment`.

## Inputs (reused; never re-derived)
- **T1** per-timeframe `TrendState` (direction-neutral) via `assess_trend` — the
  structural backbone.
- `measurement_analyses[tf].displacement_observations` (`range_speed_ratio`,
  `total_range`, `direction`) — refines the non-directional forming phase.
- (Available for future refinement, not required in V1: equal-level clusters, SR
  zones, trendlines.)

## Regime states (frozen `Regime` enum, used exactly)
`COMPRESSION, BREAKOUT_PENDING, EXPANSION, TREND, DECELERATION, RANGE, TRANSITION,
UNCERTAIN`. No polarity token appears in any member.

## Deterministic per-timeframe mapping
Backbone from the (direction-neutral) T1 trend state; the forming phase is refined
by recent displacement:
- `UNKNOWN → UNCERTAIN`
- `TRANSITION → TRANSITION` (confirmed structural failure; replacement unconfirmed)
- `TRENDING → TREND` (persistent directional structure)
- `EXHAUSTING → DECELERATION` (direction valid, continuation weakening — no reversal)
- `RANGE → RANGE` (alternating / bounded)
- `FORMING →`
  - `EXPANSION` if any of the last `recent_displacement_window` displacements has
    `range_speed_ratio >= expansion_speed_ratio` (genuine range expansion);
  - else `BREAKOUT_PENDING` if recent displacement exists but is only building;
  - else `COMPRESSION` (no recent displacement — contained/contracting).

## Precedence / conflict resolution (deterministic)
`UNCERTAIN > TRANSITION > TREND > DECELERATION > RANGE > EXPANSION >
BREAKOUT_PENDING > COMPRESSION`. Because the backbone comes from a single
direction-neutral trend-state and the forming refinement is a total order over
displacement evidence, the result never depends on dict iteration or event arrival
order (tested). Primary regime = the D1 regime (or the highest-authority present, in
order D1, H4, W1, H1, M15, M5).

## Direction independence
Regime is derived only from the **direction-neutral** T1 trend-state axis plus
non-directional displacement magnitude, so `(BULLISH, COMPRESSION)`,
`(BEARISH, EXPANSION)`, `(NEUTRAL, RANGE)` are all representable (tested). No regime
member carries BULL/BEAR.

## Determinism / causality / state transitions
`assess_regime` is a pure function of the `ScannerAnalysis` (which is a pure function
of accepted candles): same prefix → same regime; no wall-clock; no lookahead;
incremental (`run_scanner_replay` FINAL_ONLY) == batch (`scan_market`) (tested).
Regime **transitions** are observed by comparing successive assessments (the engine
is stateless within one snapshot); the target progression
`COMPRESSION → BREAKOUT_PENDING → EXPANSION → TREND → DECELERATION → RANGE` and the
non-linear jumps (`TRANSITION`, `UNCERTAIN`) all emerge from the mapping without
forcing every market through every state.

## Provisional parameters (ENGINEERING-PROVISIONAL, centralized)
`recent_displacement_window=3`, `expansion_speed_ratio=1.50` — in
`RegimeEngineConfiguration`. Not production-approved; swept in T9.

## Explainability / provenance
`TimeframeRegimeAssessment` carries `regime`, reused `trend_state` context,
`recent_displacement_count`, `supporting_evidence`, `structure_reference_ids`.
`RegimeAssessment` carries the primary regime + per-TF regimes + reasons. No score,
no trade instruction.

## Pine portability
- Regime enum + trend-state→regime mapping + precedence: **PINE_PORTABLE_WITH_ADAPTATION**.
- Recent-displacement `range_speed_ratio` gating: **PINE_PORTABLE_WITH_ADAPTATION**
  (depends on the Pine displacement port; parity validated in P9).

## Known limitations
- Regime backbone is trend-state-derived; richer COMPRESSION/EXPANSION detection from
  ATR-normalized range distribution and SR-band width is a later refinement (T4
  volatility can feed it).
- Only displacement is used for the forming refinement in V1 (equal-levels/SR reserved).
- No momentum/breakout/pullback/volatility/session/score/permission (T3..T5).
