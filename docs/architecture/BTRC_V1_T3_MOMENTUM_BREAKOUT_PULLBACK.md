# BTRC-V1 — T3 Momentum / Breakout / Pullback Engines

Status: **T3 implemented** on `btrc-v1`. Three independent, deterministic,
supervisory sub-engines that consume existing scanner price-action outputs and
never re-derive them, never depend on volume, and use no RSI/MACD/ADX. Code:
`btrc/t3_engine.py`, `t3_assessment.py`, `t3_configuration.py`. Entry points:
`assess_momentum`, `assess_breakout`, `assess_pullback` — each returns a per-
timeframe tuple.

## Reused inputs
- Momentum: `measurement_analyses[tf].displacement_observations`
  (`direction`, `range_speed_ratio`, `classification` NORMAL/FAST/VERY_FAST).
- Breakout: `structure_analyses[tf].structure_transitions` (the break) +
  `measurement_analyses[tf].equal_level_clusters` (liquidity) + displacement
  (strength).
- Pullback: `measurement_analyses[tf].confirmed_swings` (impulse leg + retracement)
  + `structure_analyses[tf].current_state` (impulse direction) +
  `poi_analysis.poi_lifecycle_transitions` (genuine invalidation).

## Momentum (frozen `MomentumDirection` + `MomentumAcceleration`)
Over the last `momentum_window` displacements (never a single candle):
- direction: all-same-direction → `STRONG_*` if `count >= momentum_strong_count`
  **or** any `VERY_FAST` (a single VERY_FAST justifies STRONG; a single NORMAL does
  not); majority → `BULLISH`/`BEARISH`; tie/empty → `NEUTRAL`.
- acceleration: mean `range_speed_ratio` of the recent half vs the earlier half,
  compared with `momentum_acceleration_margin` → ACCELERATING / DECELERATING /
  STEADY.
- `momentum_score` (0–100, provisional): `min(1, mean_ratio /
  momentum_score_reference_ratio) × directional_consistency × 100`. The categorical
  state is fully understandable without the score.

## Breakout (frozen `BreakoutState`, `| None` when no active break)
A breakout **requires a confirmed structural transition** (the structural
precondition); displacement alone — however fast — is never a breakout, so
breakout quality is independent of displacement classification (tested
`test_breakout_strength_is_independent_of_displacement`).
- `FAILED_BREAK` on an immediate whipsaw (two opposite-polarity CHOCHs in a row) —
  a confirmed structural reversal, not one candle; it overrides displacement.
- else strength = the confirmed break **modulated** by the displacement observed at
  it: none → `WEAK_BREAK`, NORMAL → `VALID_BREAK`, FAST → `STRONG_BREAK`, VERY_FAST →
  `EXPLOSIVE_BREAK` (displacement is one input on a structural precondition, not an
  alias — a structurally-confirmed break with no displacement is still WEAK_BREAK).
- **`LIQUIDITY_SWEEP` is NOT emitted in V1 (disclosed limitation).** A genuine sweep
  requires evidence of price trading THROUGH a known liquidity level AND failing
  required structural acceptance (rejection/re-entry). The exposed scanner outputs
  cannot distinguish that from a generic equal-level touch/proximity
  (`EqualLevelCluster` is a liquidity REFERENCE, not a sweep event), so V1 classifies
  conservatively and never claims a sweep (tested
  `test_equal_level_proximity_alone_is_not_a_liquidity_sweep`,
  `test_v1_breakout_never_emits_liquidity_sweep`). A future phase can add
  LIQUIDITY_SWEEP once genuine sweep evidence is exposed.
- **Causal lifecycle (VALID → FAILED), no history rewrite:** each assessment is a
  pure function of its prefix analysis, so the break's reading at an early prefix
  stays VALID while a later prefix (after a confirmed reversal) reads FAILED — tested
  (`test_breakout_history_not_rewritten_across_prefixes`).

## Pullback (frozen `PullbackState`, `| None` without an impulse)
Requires a confirmed directional impulse (`current_state.direction`). Depth = the
latest counter-swing retracement as a fraction of the impulse leg (bullish: origin
SWING_LOW → SWING_HIGH, retraced by the following SWING_LOW; bearish symmetric):
- `SHALLOW_PULLBACK` (`depth ≤ pullback_shallow_max`), `HEALTHY_PULLBACK`
  (`≤ pullback_deep_min`), `DEEP_PULLBACK` (`≤ 1.0`).
- **`STRUCTURAL_FAILURE` requires STRUCTURAL evidence only** — the retracement broke
  the impulse origin swing (the structural low/high governing the impulse, `depth >
  1.0`). POI lifecycle truth is a SEPARATE contract: a POI `GENUINE_INVALIDATION_
  CONFIRMED` is recorded as **supporting** evidence but never, on its own, classifies
  STRUCTURAL_FAILURE — a healthy-depth pullback with a POI invalidation but an intact
  impulse stays `HEALTHY_PULLBACK` (tested
  `test_poi_invalidation_alone_does_not_imply_structural_failure`), and structural
  failure classifies with or without any POI invalidation (tested
  `test_pullback_structural_failure_when_origin_exceeded_without_poi_invalidation`).
  A deep-but-structurally-valid retracement stays `DEEP_PULLBACK`. (A confirmed
  opposing CHOCH/BOS would instead flip `current_state.direction`, ending the impulse
  → the pullback engine returns None there rather than mislabelling a reversal.)

## Provisional parameters (ENGINEERING-PROVISIONAL, centralized)
`momentum_window=3, momentum_strong_count=2, momentum_acceleration_margin=0.15,
momentum_score_reference_ratio=2.00, pullback_shallow_max=0.382,
pullback_deep_min=0.618` in `MomentumBreakoutPullbackConfiguration`. Swept in T9.

## Determinism / causality / Pine portability
Pure functions of the `ScannerAnalysis`: deterministic, no-lookahead, incremental
== batch (tested). Pine: momentum/breakout/pullback rules =
**PINE_PORTABLE_WITH_ADAPTATION** (depend on the Pine displacement/structure ports;
parity validated in P9).

## Known limitations
- Breakout strength uses displacement co-timed with the break; richer "acceptance vs
  rejection" (close-beyond, follow-through distance) is a later refinement.
- Pullback POI-return / FVG / OB interaction evidence is reserved for T5 confluence.
- No volatility/session/confluence/permission (T4/T5).
