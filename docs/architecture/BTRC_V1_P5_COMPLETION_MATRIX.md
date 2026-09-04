# BTRC V1 — P5 completion matrix

Permanent closure evidence, per MEGA-AUTONOMOUS-20 Phase 2. Every row is a
Python-side wire/reimplementation-sufficiency claim, proven before any Pine
code was written, following the audit → oracle → Pine-model → parity pattern
established across P2–P6.

| Component | Source authority | Wire inputs | Pine model | Directed | Randomized | Prefix / adversarial | Mutation |
|---|---|---|---|---|---|---|---|
| trend (T1) | `trend_engine._assess_timeframe` | 26-field wire (contStreak, priorOppStreak, exhaustFlag, trans1-4Type, transWindowCount) + old p2Dir/swingCount | `t1_trend_pine_model.py` | ✅ | ✅ 2000 cases | ✅ real-data premise + alignment mutation | ✅ window-alignment regression |
| regime (T2) | `regime_engine._regime_for_timeframe` + `assess_regime` | T1 trend_state + shared disp1-3 window | `t2_regime_pine_model.py` | ✅ | ✅ 2000+4000 cases | ✅ order-pin adversarial fixture | ✅ T1-order-reuse, latest-only, classification-vs-ratio |
| momentum (T3) | `t3_engine._assess_timeframe_momentum` | disp1-3 Dir/Cls/Ratio + dispWindowCount | `t3_pine_model.py` | ✅ | ✅ 2000+50000 cases | — | ✅ score/acceleration bound proven |
| breakout (T3) | `t3_engine._assess_timeframe_breakout` | trans1-4Type + transWindowCount + lastTransAvailT + dispClsAtTrans | `t3_pine_model.py` | ✅ | ✅ 2000 cases | ✅ count-relative -2 slot | ✅ MAX-not-first dispClsAtTrans |
| pullback (T3) | `t3_engine._assess_timeframe_pullback` | pbImpulsePrice/pbOriginPrice/pbPullbackPrice/pbValid + p2Dir | `t3_pine_model.py` | ✅ | ✅ 2000 cases | ✅ boundary at 0.382/0.618/1.0 | ✅ bullish-only-formula, POI-lifecycle-invariance |
| session (T4) | `t4_engine.assess_session` | evaluation timestamp only (no wire) | `t4_pine_model.py` | ✅ | ✅ 5000 cases across 8yr / DST | ✅ real GMT→BST transition | ✅ NY-preopen precedence |
| volatility (T4) | `t4_engine.assess_volatility` | POI-timeframe candle history + P1 ATR (no new wire) | `t4_pine_model.py` | ✅ | ✅ 500+2000 cases | — | ✅ percentile strict-vs-nonstrict |
| global resolve (T5) | `trend_engine._resolve_global` + `operational_context` | D1/W1/H4 wire-derived directions (T1) | `t5_trend_pine_model.py` | ✅ | ✅ exhaustive, all 216 combos | — | ✅ T1-order-reuse |
| BTMM component | `t5_engine.assess_confluence` (inline) | btmm_valid + btmm_direction (P4 output) | `t5_component_scores_pine_model.py` | ✅ | ✅ exhaustive | — | ✅ missing-default-vs-zero |
| POI component | `t5_engine.assess_confluence` (inline) | poi.strength_tier (P3 output) | `t5_component_scores_pine_model.py` | ✅ | ✅ exhaustive | — | — |
| liquidity component | `t5_engine.assess_confluence` (inline) | btmm_valid only | `t5_component_scores_pine_model.py` | ✅ | ✅ exhaustive | — | ✅ missing-default-vs-zero |
| aggregator (`_weighted_final`) | `t5_engine._weighted_final` | 8 ComponentScores + weights | `t5_aggregator_pine_model.py` | ✅ | ✅ 3000 cases | ✅ constructed exact .5 tie | — |
| permission (`_permission`) | `t5_engine._permission` | alignment/poi_bullish/final/bands/volatility | `t5_aggregator_pine_model.py` | ✅ | ✅ exhaustive | ✅ 45/65 boundary | ✅ `<`/`>=` asymmetry |
| lifecycle (`_lifecycle`) | `t5_engine._lifecycle` | 6 booleans/alignment | `t5_aggregator_pine_model.py` | ✅ | ✅ exhaustive (128 combos) | — | ✅ BTMM_VALIDATED unreachability |
| seven-assessment integration | (all of T1–T4) | one shared reduction per case | `test_p5_seven_assessment_hard_pass.py` | ✅ | ✅ 3000+4000 cases | — | — |
| float64 decision boundary | `t5_engine._weighted_final`/`_permission` | momentum's proven ≤1 raw-score wire gap | `p5_float64_boundary_study.py` | ✅ witness | ✅ exhaustive 15.55M | ✅ 45/65 adversarial search | — |
| active-POI loop | new contract (not a source port — see below) | P3 identity + P3 `PoiLifecycleStatus` | `p5_active_poi_loop_model.py` | ✅ | ✅ 200-trial multi-bar sim | ✅ terminal/newly-active edges | ✅ 8 mutations |

## Notes

- **"Wire inputs: none"** (session, volatility, global-resolve-inputs) means
  the component reads data Pine already has from an earlier, already-closed
  phase (P1's ATR, the evaluation timestamp, T1's own wire-proven directions)
  — not that the component is unverified.
- **Aggregator/permission/lifecycle** are the one place in T1–T5 verified
  against REAL separately-callable private helpers (`_weighted_final`,
  `_permission`, `_lifecycle`), the same strength of evidence as T1–T4.
  Component scores (BTMM/POI/trend/regime/momentum/breakout/liquidity/
  volatility) are inline in `assess_confluence` and were instead verified by
  source-text transcription plus end-to-end integration sanity checks — see
  `t5_component_scores_pine_model.py`'s module docstring.
- **The active-POI loop is NOT a source port.** `assess_confluence` remains
  single-POI-in/single-result-out in production; the loop is new Pine-side
  orchestration around it, per an explicitly frozen (not open) project
  decision. Its "directed/randomized/mutation" columns above are about
  proving the loop's own set-algebra contract, not differential parity
  against an existing Python function.
- **Float64 decision boundary**: classification B (wire difference CAN
  change canonical output) — see
  `BTRC_V1_P5_FLOAT64_BOUNDARY_CLASSIFICATION.md`. Accepted and disclosed by
  project-owner decision (2026-09-04); does not block Phase 7 onward.

## Regression

All rows' test files pass together as of commit `<recorded at commit time>`.
Full project regression suite green throughout (no P1–P4/P6 semantics
touched).
