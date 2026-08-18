# BTRC-V1 — BTMM Trend & Regime Confluence Layer — T0 Architecture & Contract Freeze

Status: **T0 (architecture / contract freeze)** — no strategy logic, no thresholds,
no execution. Base: validated scanner `main @ 70235b63cda9959416eb55cb631c6cfc1b0a1d5d`.
Branch: `btrc-v1`.

BTRC-V1 is an **additional supervisory analytical layer**. It evaluates whether an
otherwise-valid BTMM/POI opportunity is aligned with the prevailing direction,
regime, momentum, breakout, liquidity and volatility environment. It **never**
creates trades, and **never** invalidates a POI or BTMM setup. A valid POI stays
valid when BTRC rejects execution alignment; a valid BTMM setup stays valid when
BTRC classifies it counter-trend. **No module silently overrides another.**

All numeric thresholds, weights, score bands and cutoffs in this document are
**ENGINEERING-PROVISIONAL** and are not production-approved. Enum *names* are the
frozen interface (see `src/btmm_ai_scanner/btrc/enums.py`); their *semantics* are
finalized in T1..T5 under separate authorization.

---

## 1. Reuse matrix — existing validated capabilities BTRC consumes (never duplicates)

| Concept | Reused from (file · symbol) | BTRC use |
|---|---|---|
| Meaningful/confirmed swings, HH/HL/LH/LL | `domain/swings.py`; `domain/enums.py::SwingType`; `domain/analyzer.py::analyze_market_measurements` (`confirmed_swings`) | primary trend input |
| BOS / structure transitions / persistence | `structure/transitions.py`; `structure/analyzer.py`; `structure/enums.py::{StructureTransitionType,StructureDirection}`; `structure/current_state.py`; `structure/relationships.py` | trend & regime evidence |
| Displacement | `domain/displacement.py`; measurement analysis `displacement_observations` | momentum/breakout input |
| Market speed / legs / candle metrics | `measurements/legs.py`; `measurements/candle_metrics.py` | momentum/acceleration input |
| Equal highs/lows (liquidity pools) | `domain/equal_levels.py`; `domain/enums.py` (`EqualLevelCluster`) | liquidity input |
| Support/resistance | `domain/support_resistance.py` | price-location vs levels |
| Trendlines | `domain/trendlines.py` | structural context |
| ATR | `measurements/atr.py` (`compute_atr_series`, incremental ATR) | volatility engine seed |
| Fair value gaps | `poi/fair_value_gaps.py` | POI (already scored) |
| Order blocks | `poi/order_blocks.py` | POI |
| Base formation | `poi/bases.py` | POI |
| Pressure wicks | `poi/pressure_wicks.py` | POI |
| Candlestick confirmation | `poi/engulfing.py`, `poi/single_candle_reversals.py`, `poi/three_candle_stars.py`, `poi/reversal_candles.py`, `poi/reference_zones.py`, `poi/period_levels.py` | POI confirmation |
| POI detection | `poi/analyzer.py`; `poi/observation.py::PoiObservation`; `poi/detector_frontier.py` | POI identity/quality |
| POI merge / cross-TF inheritance | `poi/overlap.py::resolve_merges` (effective_timeframe, `merged_source_poi_record_ids`) | cross-TF context |
| POI lifecycle (breach/reclaim/invalidation/taps) | `poi/lifecycle.py`; `poi/lifecycle_scheduler.py`; `poi/lifecycle_cursor.py`; `poi/enums.py::{PoiLifecycleStatus,PoiLifecycleTransitionType,PoiTapClassification}`; `poi/breach_index.py`; `poi/current_state.py` (`tap_count`, freshness) | POI state input |
| Overshoot / breach / reclaim / invalidation | `poi/enums.py` transition types (`CLOSE_BREACH_CANDIDATE`, `RECLAIM_*`, `FALSE/GENUINE_INVALIDATION_CONFIRMED`) | POI interaction state |
| Liquidity | `btmm/liquidity.py` | liquidity state |
| BTMM detection | `btmm/analyzer.py`; `btmm/observation.py::BtmmObservation`; `btmm/setup_delta.py` | BTMM state |
| BTMM lifecycle | `btmm/lifecycle.py`; `btmm/lifecycle_scheduler.py`; `btmm/enums.py`; `btmm/reaction.py`; `btmm/interaction.py`; `btmm/reviewed_evidence.py` | BTMM state |
| Cross-timeframe rank/combine | `scanner/replay.py::_TIMEFRAME_RANK`; `scanner/analyzer.py::scan_market`; `poi/analyzer.py` combine | multi-TF orchestration |
| Timeframe registry | `config/enums.py::Timeframe`; `market_data/source_mapping.py` | TF authority |
| Availability / causality | `contracts/normalized_candle.py::availability_time_utc`; `scanner/replay.py` availability grouping; `historical_backtest/csv_parser.py::_derive_event_and_availability` (availability = open + duration) | no-lookahead guarantee |

### Capabilities NOT present today (BTRC builds these in later T-phases — NOT T0)
- Aggregated **trend direction/state** across swings/BOS (T1).
- **Regime** classification (compression/expansion/etc.) (T2).
- **Momentum/breakout/pullback** *named-state* classification — raw displacement/speed exist, the classified states (`WEAK/VALID/STRONG/EXPLOSIVE/FAILED_BREAK`, pullback bands) do not (T3).
- **Volatility state** bands + percentile/abnormal-spike (ATR exists; classification does not) (T4).
- **Session context** — no session logic anywhere (T4).
- **Confluence scoring / analytical permission / decision object** (T5).
- Timeframes **H12/H8/H6** — not in `Timeframe` (see §2).

---

## 2. Timeframe support matrix

`Timeframe` (config/enums.py) = {M1, M5, M15, H1, H3, H4, D1, W1}. Registry
(`market_data/source_mapping.py`) maps the same set for FXCM. Every measurement /
structure / POI / BTMM engine is timeframe-generic (keyed by `Timeframe`), so any
*supported* timeframe is fully wired; unsupported timeframes need an enum + rank
extension (a scanner change — **out of T0 scope**).

| Proposed BTRC TF | Role | Contract supported | Measurements | Structure | POI | BTMM relevance | Missing |
|---|---|---|---|---|---|---|---|
| W1 | structural macro | **TRUE** | yes | yes | yes | context | — |
| D1 | primary bias | **TRUE** | yes | yes | yes | context | — |
| H12 | intermediate | **FALSE** | — | — | — | — | add `Timeframe.H12` + `_TIMEFRAME_RANK` |
| H8 | intermediate | **FALSE** | — | — | — | — | add `Timeframe.H8` |
| H6 | intermediate | **FALSE** | — | — | — | — | add `Timeframe.H6` |
| H4 | operational trend | **TRUE** | yes | yes | yes | context | — |
| H1 | execution momentum | **TRUE** | yes | yes | yes | supporting | — |
| M15 | entry/context | **TRUE** | yes | yes | yes | formation | — |
| M5 | precision confirm | **TRUE** | yes | yes | yes | supporting | — |
| H3 | (available, unused by hierarchy) | TRUE | yes | yes | yes | — | BTRC may adopt or ignore |

**Finding (non-blocking):** H12/H8/H6 are not representable today. T1 ships on the
supported subset {W1, D1, H4, H1, M15, M5}; adding H12/H8/H6 is a small, separate,
scanner-level enum/rank amendment gated on author approval (it changes a validated
contract, so it is deliberately excluded from T0).

**Global vs local distinction (required):** `global_direction` is computed from the
higher-authority timeframes; each timeframe additionally reports its own
`(Direction, TrendState)`. Thus `GLOBAL_DIRECTION = BULLISH` while
`H1 = (BEARISH, TRENDING)` (a bearish retracement) is representable without mutating
global direction — the decision object carries both a global field and a per-TF map.

---

## 3. Frozen state dimensions (independent axes)

Implemented as pure enums in `src/btmm_ai_scanner/btrc/enums.py` (no logic). Axes are
independent: **Direction ≠ TrendState ≠ Regime ≠ Volatility ≠ Momentum.**

- **Direction** `{STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH}`
- **TrendState** (direction-neutral) `{UNKNOWN, FORMING, TRENDING, EXHAUSTING, TRANSITION, RANGE}`
- **Regime** `{COMPRESSION, BREAKOUT_PENDING, EXPANSION, TREND, DECELERATION, RANGE, TRANSITION, UNCERTAIN}`
- **MomentumDirection** `{STRONG_BULLISH, BULLISH, NEUTRAL, BEARISH, STRONG_BEARISH}` + **MomentumAcceleration** `{ACCELERATING, STEADY, DECELERATING}`
- **BreakoutState** `{WEAK_BREAK, VALID_BREAK, STRONG_BREAK, EXPLOSIVE_BREAK, FAILED_BREAK, LIQUIDITY_SWEEP}` (absence → `None`)
- **PullbackState** `{SHALLOW_PULLBACK, HEALTHY_PULLBACK, DEEP_PULLBACK, STRUCTURAL_FAILURE}` (absence → `None`)
- **VolatilityState** `{VERY_LOW, LOW, NORMAL, HIGH, EXTREME}`
- **SessionContext** `{ASIAN, LONDON_PREOPEN, LONDON, NEW_YORK_PREOPEN, NEW_YORK, LONDON_NY_OVERLAP, POST_NY}`
- **TrendAlignment** `{ALIGNED, PARTIAL, NEUTRAL, COUNTER_TREND}`
- **ExecutionPriority** `{HIGH, MEDIUM, LOW, WATCH_ONLY}` (analytical priority; not an order)
- **AnalyticalPermission** `{BUY_BIAS, SELL_BIAS, ALLOW_BOTH_CONTEXT, COUNTER_TREND, WATCH_ONLY, NO_TRADE_CONTEXT}`
- **SignalLifecycleState** (analytical + future-bot; see §12)
- **PinePortability** `{PINE_PORTABLE_EXACT, PINE_PORTABLE_WITH_ADAPTATION, PYTHON_ONLY, REQUIRES_VALIDATION}`

---

## 4. Trend input contract (T1) — priority order (deterministic)

1. existing market **structure** (`structure/*`).
2. confirmed **meaningful swings** (`domain/swings.py`), HH/HL/LH/LL sequence.
3. **BOS / structural persistence** (`structure/transitions.py`), consecutive-break count.
4. **price location** vs structural levels (SR, swing points).
5. **displacement / market speed** (`domain/displacement.py`, `measurements/legs.py`) as corroboration.
6. **multi-timeframe agreement** (higher-authority TFs weight more).

A moving-average reference may exist **only** as optional secondary evidence and
**never** overrides structure. No EMA/MA parameters are selected in T0.

---

## 5. Trend state machine (contract; thresholds ENGINEERING-PROVISIONAL, none set in T0)

State = `(Direction, TrendState)` pair (kept as two axes). Canonical paths:

```
UNKNOWN
  → FORMING            (first HL after a low / first LH after a high; not yet confirmed)
  → (BULLISH, TRENDING)   entry: >=2 confirmed HH+HL and a bullish BOS
      persistence: new HH/HL continue; no confirmed LL
      → (BULLISH, EXHAUSTING)   exhaustion evidence: momentum deceleration + failure to make new HH
      → TRANSITION              transition evidence: bullish BOS invalidated / first LH+LL forming
      → (BEARISH, TRENDING)     confirmed reversal: bearish BOS + HH/HL sequence broken
  symmetric for bearish
RANGE  entry: repeated equal highs/lows, no directional BOS, low displacement
```

Hard rule: **one opposite candle never flips global trend.** A flip requires a
confirmed opposing BOS *and* a broken prior swing sequence (multi-candle, multi-swing
evidence). `EXHAUSTING`/`TRANSITION` are intermediate and reversible back to
`TRENDING` on renewed continuation.

Fields the contract must expose per state: `entry_conditions`, `persistence_conditions`,
`exhaustion_evidence`, `transition_evidence`, `confirmed_reversal_evidence` (all as
references to existing structure/swing/displacement records; no invented numerics).

---

## 6. Regime state machine (contract)

```
COMPRESSION  (contracting range, low displacement, tightening SR band)
  → BREAKOUT_PENDING   (compression + building displacement at range edge)
  → EXPANSION          (confirmed range break with displacement)
  → TREND              (sustained expansion + trend-state TRENDING)
  → DECELERATION       (displacement/speed falling while price extends)
  → RANGE              (equal highs/lows dominate; no directional BOS)
TRANSITION / UNCERTAIN  (ambiguous or conflicting evidence)
```

Supporting measurements: ATR (`measurements/atr.py`), displacement
(`domain/displacement.py`), equal levels (`domain/equal_levels.py`), SR band width
(`domain/support_resistance.py`), BOS cadence (`structure/transitions.py`). **Regime is
not a direction** — `TREND` regime carries no bullish/bearish token (direction is a
separate axis).

---

## 7. Momentum / breakout / pullback contracts (T3)

- **Momentum**: `MomentumDirection` + `MomentumAcceleration`, derived from displacement
  magnitude/sign and market-speed change (`measurements/legs.py`, `candle_metrics.py`).
- **Breakout** (`BreakoutState`): classify a structural break by displacement strength,
  follow-through, and whether it swept liquidity (`equal_levels`) vs. held —
  `LIQUIDITY_SWEEP` and `FAILED_BREAK` are explicit non-continuation outcomes.
- **Pullback** (`PullbackState`): classify a retracement by depth vs the impulse leg
  and whether structure held (`SHALLOW/HEALTHY/DEEP`) or broke (`STRUCTURAL_FAILURE`).

Already available: raw displacement observations, leg metrics, ATR, equal-level sweeps.
Needs implementation: the *classification* into the named states above. **No numeric
band is fixed in T0.**

---

## 8. Volatility contract (T4)

Interface for a future volatility engine: ATR, normalized ATR (ATR/price),
rolling volatility, range distribution, volatility percentile, abnormal-spike
detection → `VolatilityState`. Volatility **never** determines direction. For the
FUTURE bot it may gate permission / stop calibration / sizing / management — **none
implemented in T0.**

---

## 9. Session context contract (T4)

`SessionContext` computed from candle availability time in exchange time (DST-aware,
reusing the tz handling in `historical_backtest/csv_parser.py::resolve_local_instants`).
Session context **never** independently triggers a trade; it is context only.

---

## 10. Counter-trend contract (analytical truth preserved)

Given `D1=STRONG_BULLISH, H4=BULLISH`, a valid `M15` bearish POI stays valid. The
decision object expresses:

```
poi_valid = TRUE
btmm_valid = TRUE
trend_alignment = COUNTER_TREND
execution_priority = LOW | WATCH_ONLY
analytical_permission = COUNTER_TREND | WATCH_ONLY
```

BTRC never sets `poi_valid=False` for a counter-trend POI. **Future** additional
evidence required before a counter-trend setup *could* become execution-eligible
(documented, not implemented): confirmed higher-TF exhaustion/transition, an opposing
BOS on the operational TF, a liquidity sweep + reclaim, and momentum alignment — all
gated by the FUTURE risk/execution engines (T6+).

---

## 11. Score architecture (independent families; no weights approved)

Independent, separately-reported scores:
`BTMM_SCORE, POI_SCORE, TREND_SCORE, REGIME_SCORE, MOMENTUM_SCORE, BREAKOUT_SCORE,
LIQUIDITY_SCORE, VOLATILITY_SCORE` → then a `FINAL_CONFLUENCE_SCORE`. Each component is
retained (never collapsed into a black box); the final score records the component
vector and the mapping used. **Weights, score bands, and cutoffs are
ENGINEERING-PROVISIONAL** and not production-approved in T0 (finalized empirically in
T5/T9 with out-of-sample validation).

### Provisional parameters list (all ENGINEERING-PROVISIONAL, none set in T0)
swing-significance threshold; BOS-persistence count; exhaustion displacement-decay
threshold; range detection band; compression/expansion ATR ratios; breakout strength
bands; pullback depth bands; volatility percentile cutoffs; session boundaries;
per-family score weights; final-confluence cutoffs; counter-trend eligibility
thresholds; MA reference period (if ever used).

---

## 12. Analytical permission contract & signal lifecycle separation

`AnalyticalPermission` states are **analytical**, not broker instructions. The
candidate lifecycle is partitioned (machine-checked in `enums.py` +
`test_btrc_enums_contract_freeze.py`):

- **ANALYTICAL BTRC (now/planned T1..T5):** `DETECTED → STRUCTURALLY_VALIDATED →
  BTMM_VALIDATED → POI_VALIDATED → TREND_VALIDATED → REGIME_VALIDATED →
  MOMENTUM_VALIDATED → LIQUIDITY_VALIDATED`.
- **FUTURE PYTHON BOT (T6+, NOT implemented):** `RISK_VALIDATED → EXECUTION_READY →
  TRIGGERED → MANAGED → CLOSED`.

---

## 13. BTRC decision object contract (documentation; frozen as code in T5, not T0)

Immutable output (a future `ContractModel`) containing at least: `symbol`,
`evaluation_time`, `global_direction`, `trend_state`, `regime`, per-timeframe
`(direction, trend_state)` map, `btmm_state`, POI identity/timeframe/direction/state/quality
(referencing existing `PoiObservation.record_id`), `liquidity_state`,
`momentum_direction` + `momentum_score`, `breakout_state` + `breakout_score`,
`pullback_state`, `volatility_state`, `session_context`, the individual score
components, `final_confluence_score`, `trend_alignment`, `analytical_permission`,
`reasons_supporting`, `reasons_against`, `reason_for_rejection_or_watch`, and
provenance/evidence references (record ids from the existing engines). **No** entry /
stop / target / lot-size / order-id fields — those exist only as **FUTURE** extension
fields in this document, never as functionality.

---

## 14. Pine portability matrix

| Feature area | Portability |
|---|---|
| Direction / TrendState / Regime enums + state machines | PINE_PORTABLE_WITH_ADAPTATION |
| Swing/BOS/structure derivation | PINE_PORTABLE_WITH_ADAPTATION (Pine bar-by-bar; parity to be validated) |
| Displacement / market-speed / ATR | PINE_PORTABLE_EXACT (simple arithmetic) |
| Session context | PINE_PORTABLE_EXACT |
| Equal-levels / SR / trendlines | PINE_PORTABLE_WITH_ADAPTATION |
| POI merge / cross-TF inheritance / lifecycle scheduler | REQUIRES_VALIDATION (complex incremental state; parity harness in P9) |
| Content-addressed identity / fingerprints | PYTHON_ONLY (analytics need not reproduce ids in Pine) |
| Confluence scoring (once weights set) | PINE_PORTABLE_WITH_ADAPTATION |

This does **not** authorize Pine implementation.

---

## 15. Data logging contract (research; both accepted and rejected candidates)

Analytical fields (now/planned): timestamp, symbol, timeframe, trend_state, regime,
structure refs, btmm_state, poi identity/type/quality, liquidity_state,
displacement/momentum, breakout, pullback, volatility, individual scores, final score,
analytical_permission, reasons_supporting, reasons_rejecting. **FUTURE bot-only**
fields (clearly marked, not logged in analytics): entry, stop, target, risk, result_R,
MAE, MFE, exit_reason.

---

## 16. Future ablation / validation plan (evidence, not aesthetics)

- **Model A:** BTMM + POI baseline.
- **Model B:** + Trend.  **Model C:** + Regime.  **Model D:** + Momentum/Breakout/Pullback.
- **Model E:** full analytical BTRC.

No BTRC module is declared beneficial for being "logically sound" — acceptance requires
evidence on **unseen** data, and every tunable parameter must be tested for **stability
across reasonable ranges**, not optimized to a single historical optimum.

---

## 17. Dependency-ordered implementation plan

**Analytical (this project):** `T0` freeze (this) → `T1` Trend Engine → `T2` Regime
Engine → `T3` Momentum/Breakout/Pullback → `T4` Volatility/Session → `T5`
Confluence/Analytical-Permission + decision object.
**FUTURE PYTHON BOT (not authorized):** `T6` Risk → `T7` Execution Permission → `T8`
Trade Management. **`T9` Validation** (ablation A–E on unseen data).

**Pine phases (later, not authorized):** `P0` architecture map → `P1` measurements →
`P2` structure → `P3` POI/lifecycle → `P4` BTMM → `P5` BTRC → `P6` multi-TF
orchestration → `P7` visuals → `P8` alerts → `P9` Python-vs-Pine parity → `P10` client
release.

### Exact T1 (Trend Engine) scope — the ONLY next authorized step
- Consume existing `confirmed_swings`, `structure_transitions`/`current_state`, price
  location, and (as corroboration) displacement — **read-only**; no scanner changes.
- Produce, per supported timeframe {W1, D1, H4, H1, M15, M5}, a deterministic
  `(Direction, TrendState)` plus `global_direction`, using the §5 state machine.
- Preserve global-vs-local (retracement representable without flipping global).
- Deterministic, no-lookahead (availability-gated), Pine-portable-with-adaptation.
- Permanent tests incl. incremental-vs-batch determinism and "one opposite candle does
  not flip global trend." Thresholds introduced in T1 are ENGINEERING-PROVISIONAL and
  stability-tested. **No** regime/momentum/volatility/score/permission work in T1.

---

## 18. Scope guarantees (T0)

T0 changed **no** scanner/POI/BTMM/measurement/structure semantics; added only the
`btrc/` enum package (pure interface) + its contract test + this document. No BUY/SELL,
SL/TP, sizing, brokerage, Pine, or genuine-replay work. Main is not merged.
