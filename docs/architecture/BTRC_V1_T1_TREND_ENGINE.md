# BTRC-V1 — T1 Deterministic Multi-Timeframe Trend Engine

Status: **T1 implemented** on branch `btrc-v1`. Supervisory only — the trend
engine labels prevailing direction/state; it never decides whether a POI or BTMM
setup is valid and never mutates any scanner record. All persistence/agreement
counts are **ENGINEERING-PROVISIONAL** (centralized in `TrendEngineConfiguration`)
and not production-approved.

Code: `src/btmm_ai_scanner/btrc/trend_engine.py`, `trend_assessment.py`,
`trend_configuration.py`. Entry point: `assess_trend(scanner_analysis, config?) ->
TrendAssessment`.

## Reused scanner inputs (consumed, never re-derived)
Per timeframe, read from a `ScannerAnalysis`:
- `measurement_analyses[tf].confirmed_swings` — `ConfirmedSwing` (swing_type,
  pivot_price, availability_time_utc). Used for exhaustion (lower-high / higher-low).
- `structure_analyses[tf].structure_transitions` — `StructureTransition`
  (BULLISH_BOS/BEARISH_BOS = continuation; BULLISH_CHOCH/BEARISH_CHOCH = change of
  character; direction_before/after; availability_time_utc). Primary trend evidence.
- `structure_analyses[tf].current_state` — `CurrentStructureState` (`direction`:
  UNDETERMINED/BULLISH/BEARISH; `analyzed_swing_count`). The scanner's own confirmed
  structural direction.

No moving average / RSI / MACD / ADX is used. Market structure is primary.

## Per-timeframe Direction
From `current_state.direction`: UNDETERMINED→NEUTRAL, BULLISH→BULLISH,
BEARISH→BEARISH. Upgraded to **STRONG_** only when the timeframe is TRENDING and the
same-direction continuation-BOS streak `>= strong_streak` (default 3). Direction is
CONFIRMED-only (a single candle/swing cannot set it — it requires a scanner-confirmed
CHOCH/BOS).

## Per-timeframe TrendState (deterministic transitions)
Let `dir` = current_state.direction, `streak` = consecutive most-recent same-dir
continuation BOS, `alternation` = CHOCH count in the last `range_window` transitions.

- **UNKNOWN** — no current_state, or `analyzed_swing_count < min_swings_for_assessment`.
- **FORMING** — `dir` UNDETERMINED (swings building, no confirmed break); OR a
  fresh CHOCH into `dir` whose prior opposite trend was not established.
- **TRANSITION** — a CHOCH into `dir` that reversed an **established** opposite trend
  (prior opposite BOS streak `>= trend_min_streak`); new trend not yet confirmed.
- **TRENDING** — `streak >= trend_min_streak` (default 1) continuation BOS in `dir`
  and no exhaustion.
- **EXHAUSTING** — TRENDING-level structure still valid but the latest same-type swing
  weakened (lower high while bullish / higher low while bearish) without a confirmed
  reversal.
- **RANGE** — `alternation >= range_choch_count` (whipsaw / alternating character).

```
UNKNOWN --(enough swings, no break)--> FORMING
FORMING --(CHOCH into dir)------------> FORMING | TRANSITION   (TRANSITION iff prior opposite trend established)
        --(continuation BOS)----------> TRENDING
TRENDING --(lower-high/higher-low)----> EXHAUSTING --(continuation BOS)--> TRENDING
TRENDING --(opposing CHOCH)-----------> TRANSITION --(continuation BOS in new dir)--> TRENDING (new direction)
any      --(alternating CHOCH >= N)---> RANGE
```
Direction and TrendState are **independent axes**: a timeframe can be
`(BULLISH, EXHAUSTING)` or `(BEARISH, RANGE)`.

## Global authority resolver
`_resolve_global(direction_by_tf)`:
- **D1 is primary.** D1 bullish-side → global **BULLISH** (→ **STRONG_BULLISH** iff W1
  and H4 are also bullish-side). D1 bearish-side symmetric.
- **D1 NEUTRAL/absent:** only W1+H4 agreement yields a provisional (non-strong)
  global direction; otherwise **NEUTRAL**.
- **H1 / M15 / M5 never change global direction** (local context only).

`macro_context` = W1 direction, `operational_context` = H4 direction.

## Strong-direction rule
STRONG requires *evidence*, not a one-off number: per-timeframe STRONG = TRENDING +
continuation streak `>= strong_streak`; global STRONG = D1 directional + W1 and H4
agreement. Neighbouring values are to be stability-tested in T9; nothing is
production-approved.

## Retracement vs global reversal
Because global comes only from D1/W1/H4 confirmed structure, `global_direction =
BULLISH` while `H1 = (BEARISH, TRENDING/FORMING)` is fully representable (a bearish
local retracement inside a bullish higher-timeframe trend), and vice-versa. There is
no special "retracement" enum — the global/per-timeframe relationship carries that
meaning. Opposing lower-timeframe directions appear in `opposing_reasons` as
"local retracement / does not flip global".

## No single-candle flip (permanent invariant)
Global direction changes only through the D1 confirmed structural direction, which
requires a scanner-confirmed CHOCH (multi-candle, multi-swing) — a single opposite
candle produces no CHOCH and cannot flip it. The required sequence is
`BULLISH → EXHAUSTING/TRANSITION → confirmed bearish structure → BEARISH` (and
symmetric). Tested directly (`test_one_opposite_swing_does_not_flip_a_bullish_timeframe`,
`test_lower_timeframes_never_flip_global`).

## Determinism / causality
`assess_trend` is a pure function of the `ScannerAnalysis`, which is itself a pure
function of the accepted candle history. Therefore: same accepted candles + same
scanner state → identical trend output; no wall-clock dependence; no lookahead (the
prefix-k analysis contains only prefix-k candles). Incremental (`run_scanner_replay`
FINAL_ONLY) and batch (`scan_market`) produce equal `ScannerAnalysis` (proven in the
scanner suite) → equal `TrendAssessment` (tested).

## Explainability / provenance
Each `TimeframeTrendAssessment` carries `supporting_evidence`, `opposing_evidence`,
`continuation_streak`, `analyzed_swing_count`, and `structure_reference_ids` (the exact
transition record ids consulted). `TrendAssessment` carries global
`supporting_reasons` / `opposing_reasons` naming each authority timeframe. No opaque
numeric-only classification; no confluence score (T5).

## Provisional parameters (ENGINEERING-PROVISIONAL)
`min_swings_for_assessment=2`, `trend_min_streak=1`, `strong_streak=3`,
`range_window=4`, `range_choch_count=3`. Centralized in `TrendEngineConfiguration`;
sweep in T9.

## Pine portability
- Direction/TrendState enums + global resolver: **PINE_PORTABLE_WITH_ADAPTATION**.
- Streak / alternation / exhaustion counting over structure records:
  **PINE_PORTABLE_WITH_ADAPTATION** (Pine reconstructs from bar-by-bar structure;
  parity validated in P9).
- Consuming scanner structure/swing records verbatim: **REQUIRES_VALIDATION** (depends
  on the Pine structure port). No Pine code is written in T1.

## Known limitations / deferrals
- Authority timeframes limited to **{W1, D1, H4, H1, M15, M5}**; **H6/H8/H12 are not in
  `config/enums.py::Timeframe`** and are deferred to a separate scanner-contract
  amendment (author approval). H3 exists but is not an authority level in T1.
- Exhaustion uses only the two most recent same-type confirmed swings (a minimal,
  deterministic signal); richer exhaustion is a later refinement.
- No regime/momentum/breakout/pullback/volatility/session/score/permission — those are
  T2..T5 and are not started.
