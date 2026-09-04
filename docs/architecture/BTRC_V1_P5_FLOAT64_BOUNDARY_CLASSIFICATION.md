# BTRC V1 — P5 float64 wire-boundary decision-invariance study

**Status: classification B — wire difference CAN change canonical P5 output.
HARD STOP on the decision-invariance claim, per the explicit gate this study
was commissioned to resolve.** This does not reopen P6, and it is not a bug
in any code committed so far — it is a property of averaging any
finite-precision component into a rounded, banded score, discovered and
quantified rather than asserted away.

## The two separate boundaries

1. **Wire parity** — Python replay of the decoded P6 wire vs. actual Pine.
   This is an *implementation* requirement, not a representational limit:
   Pine's port must implement banker's rounding by hand (never call Pine's
   own `math.round`, which rounds ties away from zero), mirroring this
   repo's existing `p2_digest.pine_round`. Made exact by construction once
   implemented correctly. **Not what this document is about.**
2. **High-precision vs. wire-normalized** — the original exact-Decimal Python
   pipeline vs. the same data cast through the P6 wire's float64 encoding.
   `test_t3_transport_sufficiency.py` already bounded this: T3's
   `momentum_score` (0–100) differs by **at most 1**, `direction` is always
   exact, `acceleration` only ever ties into STEADY. **This is what this
   document studies**: does that proven ≤1 gap ever reach a canonical T5
   decision (permission band, lifecycle)?

## Method

`tests/parity_support/p5_float64_boundary_study.py` performs an **exhaustive**
(not sampled) search:

- The seven non-momentum `ComponentScores` fields are each restricted to
  their actual **achievable, source-defined value sets** (not an
  unconstrained 0–100 integer) — e.g. `regime_score` can only ever be one of
  the 8 values in `t5_engine._REGIME_SCORE`, `breakout_score` one of 6 fixed
  values, etc. — traced to their source tables in the study module's
  docstring.
- For every combination of those seven (25,920 combinations), every raw T3
  momentum score 0–99, both momentum directions that matter to scoring
  (BULLISH/STRONG_BULLISH; NEUTRAL is the identity case), and both POI
  sides, the weighted final score is computed twice: once at the raw score,
  once at raw+1 (the proven maximum wire delta).
- A "crossing" is recorded whenever `round(weighted/total_weight)` moves
  from one side of 45 or 65 to the other — i.e. `_permission`'s decision
  changes for at least one `TrendAlignment`, since alignment does not depend
  on momentum at all and the same alignment applies to both sides.

Total space checked: **15,552,000** combinations.

## Result

**21,044 combinations (≈0.135%) cross the 45 or 65 boundary.** A concrete,
reproduced witness (frozen as the first search result in
`test_exhaustive_boundary_crossing_search_is_reproducible_and_nonempty`):

```
others = {trend: 20, regime: 30, breakout: 10, poi: 50, btmm: 70, liquidity: 40, volatility: 20}
momentum_direction = BULLISH, poi_bullish = True
raw_momentum_a = 57  -> final = 44  (below watch_only_min)
raw_momentum_b = 58  -> final = 45  (at watch_only_min)
```

At `raw=57` the T5 momentum component is `50 + 57//2 = 78`; at `raw=58` it is
`50 + 58//2 = 79` — a genuine, source-formula-correct 1-point shift, driven
entirely by the wire's proven ≤1 raw-score uncertainty. With this specific
combination of the other seven components, that single point is exactly
enough to move `round(weighted/13)` from 44 to 45, which (for an ALIGNED or
PARTIAL POI) changes `_permission`'s output from `NO_TRADE_CONTEXT` to
`WATCH_ONLY`.

Every recorded crossing changes `final` by **exactly 1**, never more — proven
directly in `test_every_crossing_is_explained_by_exactly_a_one_point_final_shift`,
consistent with the mechanism: a raw delta of 1 changes the T5 momentum
component by at most 1 (weight 1), which changes the weighted numerator by at
most 1, which changes `round(numerator/13)` by at most 1.

## Why this is not fixable without changing frozen semantics

- **Not a bug**: `_weighted_final`, `_permission`, and T5's momentum-component
  formula are all already proven *exact* ports of the real source
  (`test_t5_aggregator_sufficiency.py`, `test_t5_component_scores_sufficiency.py`).
  Nothing here is wrong — it is the source's own arithmetic, applied to an
  input (the wire-transported momentum ratio) that P6 already closed as
  float64.
- **Not unique to momentum**: the same analysis applies to *any* weighted
  component with *any* representational uncertainty at all, however small —
  rounding a bounded weighted average is inherently sensitive to a ±1 shift
  in any single contributing term near a boundary. Momentum is simply the
  only component this campaign has so far proven to carry a nonzero
  wire-vs-source uncertainty (T1/T2/T3-breakout/T3-pullback/T4 all proved
  *exact*, zero mismatches).
- **Not reachable by redesigning the wire without reopening P6**: the P6
  transport (float64 `disp*Ratio`) is closed, real-FXCM-parity-proven, and
  explicitly frozen absent contradictory P5 evidence. This finding is
  evidence *about* a downstream consequence of that frozen wire, not a defect
  *in* it — P6's own 156/156 real-data parity is untouched.

## What this means for P5 closure

Per the explicit governing instruction, this was surfaced as a decision point
rather than resolved unilaterally. **Decision (project owner, 2026-09-04):
accept and disclose the bounded, quantified residual risk; proceed to Pine
deployment/closure with this disclosure attached.**

Consequently, any future P5 closure document MUST state both of the
following separately, and MUST NOT collapse them into one "exact parity"
claim:

- **Wire-normalized parity: EXACT** — T1/T2/T3-direction/T3-breakout/
  T3-pullback/T4/T5-aggregator/T5-components/T5-global are all proven exact
  ports of the source, operating on the same wire values Pine receives.
- **High-precision-to-wire canonical decision invariance: NOT established** —
  a bounded, quantified residual risk stands: ≈0.135% of an adversarially
  constructed 15,552,000-combination space crosses the 45/65 permission
  boundary by exactly 1 point, driven by momentum's proven ≤1 raw-score wire
  gap. Disclosed and accepted, not eliminated.

This finding does NOT block Phase 7 onward (active-POI loop, Pine DEV,
deploy, real parity, closure) — it changes what the eventual closure document
is permitted to claim.
