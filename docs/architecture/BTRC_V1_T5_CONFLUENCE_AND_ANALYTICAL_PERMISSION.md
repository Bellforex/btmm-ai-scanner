# BTRC-V1 — T5 Confluence + Analytical-Permission Engine

Status: **T5 implemented** on `btrc-v1`. Combines every supervisory dimension into
independent component scores, a final confluence ranking, a trend-alignment class,
and an ANALYTICAL permission — explainable, never a black-box trade generator, and
with **no** entry/stop/target/order semantics. Code: `btrc/t5_engine.py`,
`t5_decision.py`, `t5_configuration.py`. Entry: `assess_confluence(analysis, poi, *,
candles_by_timeframe?, evaluation_time_utc?, config?) -> BtrcDecision`;
`latest_poi(analysis)` picks the primary candidate.

## Independent component scores (0–100)
`BTMM_SCORE, POI_SCORE, TREND_SCORE, REGIME_SCORE, MOMENTUM_SCORE, BREAKOUT_SCORE,
LIQUIDITY_SCORE, VOLATILITY_SCORE` — each retained in `ComponentScores` (never
collapsed irreversibly). `FINAL_CONFLUENCE_SCORE` is their weighted average
(`ConfluenceConfiguration.weights`, BTMM+POI weighted highest as the strategy core).
Pullback contributes transparently through momentum/POI context (its state is carried
in the decision object, not hidden).

## Hard analytical truth vs soft score (mandatory separation)
`poi_valid` and `btmm_valid` come from the scanner and are **never** changed by any
score: a large trend score cannot revalidate an absent BTMM or an invalid POI (tested
`test_btmm_valid_reflects_scanner_data_not_scores`, incl. a 1000× trend weight). BTRC
is supervisory — it **never sets `poi_valid=False`** (tested
`test_btrc_never_invalidates_the_poi`). Confirmed states (structure/regime/volatility)
are recorded as hard fields alongside the soft ranking.

## Trend alignment & counter-trend
`TrendAlignment` from POI direction vs `global_direction` (with `PARTIAL` when global
aligns but the operational H4 opposes): `ALIGNED` / `PARTIAL` / `NEUTRAL` /
`COUNTER_TREND`. A valid, counter-trend POI/BTMM stays valid; the result is
`COUNTER_TREND` (or `WATCH_ONLY` at low confluence) — the setup is never deleted.

## Analytical permission (not broker authorization)
`AnalyticalPermission`: aligned + high confluence → `BUY_BIAS`/`SELL_BIAS`; aligned +
moderate → `WATCH_ONLY`; aligned + low → `NO_TRADE_CONTEXT`; neutral → `ALLOW_BOTH_
CONTEXT`/`WATCH_ONLY`; counter-trend → `COUNTER_TREND`/`WATCH_ONLY`. **EXTREME
volatility downgrades a directional bias to `WATCH_ONLY` without changing direction**
(tested). Missing components are recorded in `missing_components` and fail safe (neutral
placeholders never inflate the score; tested). These are analytical classifications, not
`ALLOW_BUY`/`EXECUTE_SELL` orders.

## Decision object & lifecycle
`BtrcDecision` carries symbol/time, hard truths (POI identity/type/direction/validity/
lifecycle, BTMM validity, global direction, regime), the T3/T4 states, the component
scores + final, trend alignment, analytical permission, the reached
`SignalLifecycleState`, and supporting/opposing/missing/rejection reasons + provenance.
**No entry/stop/target/lot/order/ticket/execution field exists** (tested
`test_decision_has_no_execution_fields`). Only the ANALYTICAL lifecycle is computed
(`DETECTED → … → LIQUIDITY_VALIDATED`, stopping at the first unmet gate); `RISK_VALIDATED
… CLOSED` remain FUTURE python-bot states and are not implemented.

## Provisional parameters (ENGINEERING-PROVISIONAL, centralized)
Weights `{btmm:3, poi:3, trend:2, regime:1, momentum:1, breakout:1, liquidity:1,
volatility:1}`, `high_confluence_min=65`, `watch_only_min=45`, per-regime score map,
score anchors — all in `ConfluenceConfiguration` / `t5_engine`; not optimized against
history; swept in T9.

## Determinism / integrated stack / Pine
`assess_confluence` is a pure function of the `ScannerAnalysis` (+ optional candles/
time) → deterministic, no-lookahead, incremental == batch across the whole T1→T5 stack
(tested). Pine: scoring + permission mapping = **PINE_PORTABLE_WITH_ADAPTATION** (depends
on the underlying dimension ports; parity validated in P9).

## Known limitations
- `LIQUIDITY_SCORE` is a provisional presence-based proxy (60 with BTMM, else 40) until
  genuine per-candidate liquidity-take evidence is exposed (see T3 sweep limitation).
- One primary candidate per call (`latest_poi`); multi-candidate ranking is a later
  refinement.
- Weights/bands are research baselines pending T9 out-of-sample validation and stability
  sweeps; nothing is production-approved.
