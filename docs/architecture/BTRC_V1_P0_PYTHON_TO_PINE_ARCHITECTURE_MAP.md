# BTRC-V1 — P0 Python → Pine Scanner Architecture / Parity Map

Status: **P0 — documentation / feasibility / translation planning only.** No Pine
source is written. Python remains the **authoritative master / automation
foundation**; the future Pine product is a **client-facing analytical scanner** on
TradingView that must reproduce the relevant analytical semantics of Python as
closely as practical. This document precedes any Pine implementation (P1+); it does
not authorize it.

## 1. Product purpose & target client experience
A user opens TradingView, selects a symbol (e.g. `FXCM:XAUUSD`) and timeframe, adds
the private indicator, and sees: market structure, POIs + POI lifecycle, BTMM, trend,
regime, momentum, breakout, pullback, volatility, confluence, analytical bias, and
alerts. The Pine product is analytical only — **no broker order execution** in the
Pine phase.

## 2. Feed modes (designed, NOT implemented)
- **Mode A — Chart feed / universal:** compute from the current chart's TradingView
  feed. Works with whichever broker/exchange chart the user opens. **Disclosure:**
  different broker/exchange OHLC may produce different analytical results.
- **Mode B — Canonical FXCM:** where TradingView/Pine permits, request the approved
  FXCM symbol explicitly (`request.security` with a fixed symbol) to maximize alignment
  with the canonical project reference. Neither mode is implemented in P0.

## 3. Module portability map
Legend: **EXACT** = PINE_PORTABLE_EXACT, **ADAPT** = PINE_PORTABLE_WITH_ADAPTATION,
**PYTHON** = PYTHON_ONLY (analytics need not reproduce), **VALIDATE** =
REQUIRES_VALIDATION (feasible but parity must be proven in P9).

| Capability | Python source | Pine portability | Note |
|---|---|---|---|
| Candles / availability semantics | `contracts/normalized_candle`, `csv_parser._derive_event_and_availability` | ADAPT | availability = bar close; use confirmed (`barstate.isconfirmed`) bars only |
| Meaningful swings | `domain/swings` | VALIDATE | pivot + meaningful-reversal (ATR) logic reconstructed bar-by-bar |
| HH/HL/LH/LL | `structure/enums.SwingRelationshipLabel` | ADAPT | swing comparison |
| BOS / CHOCH | `structure/transitions` | VALIDATE | protected/weak swing tracking as persistent state |
| Displacement | `domain/displacement` | ADAPT | `range_speed_ratio` arithmetic |
| Market speed / legs | `measurements/legs`, `candle_metrics` | ADAPT | normalized speed / efficiency |
| Equal highs/lows | `domain/equal_levels` | ADAPT | ATR-tolerance clustering |
| Support/resistance | `domain/support_resistance` | ADAPT | zone tracking |
| Trendlines | `domain/trendlines` | ADAPT | line fit + touch/pierce tolerances |
| FVG | `poi/fair_value_gaps` | EXACT | 3-candle gap geometry |
| Order blocks | `poi/order_blocks` | ADAPT | |
| Bases | `poi/bases` | ADAPT | |
| Pressure wicks | `poi/pressure_wicks` | ADAPT | |
| Candlestick confirmation | `poi/engulfing`, `single_candle_reversals`, `three_candle_stars`, `reversal_candles` | EXACT/ADAPT | candle-geometry patterns |
| POI creation | `poi/analyzer`, `observation` | VALIDATE | |
| POI merge / cross-TF inheritance | `poi/overlap.resolve_merges` | VALIDATE | multi-TF `request.security`; canonical child ordering (see T3 fix) |
| POI lifecycle | `poi/lifecycle*` | VALIDATE | persistent per-POI state machine |
| Interaction / overshoot / breach / reclaim / invalidation | `poi/enums`, `breach_index`, `current_state` | VALIDATE | tap counting + freshness |
| Liquidity | `btmm/liquidity` | VALIDATE | |
| BTMM setup + lifecycle | `btmm/analyzer`, `lifecycle*`, `reaction`, `interaction` | VALIDATE | |
| T1 Trend | `btrc/trend_engine` | ADAPT | direction + trend-state + global resolver |
| T2 Regime | `btrc/regime_engine` | ADAPT | trend-state + displacement mapping |
| T3 Momentum | `btrc/t3_engine.assess_momentum` | ADAPT | displacement window |
| T3 Breakout | `btrc/t3_engine.assess_breakout` | ADAPT | structural break + displacement (no LIQUIDITY_SWEEP yet) |
| T3 Pullback | `btrc/t3_engine.assess_pullback` | ADAPT | impulse-leg retracement |
| T4 Volatility | `btrc/t4_engine.assess_volatility` | ADAPT | `ta.atr`, percentile of ranges |
| T4 Sessions | `btrc/t4_engine.assess_session` | ADAPT | `time`/timezone; DST via exchange time |
| T5 Confluence | `btrc/t5_engine` | ADAPT | component scores + weighted final |
| T5 Analytical permission | `btrc/t5_engine._permission` | ADAPT | bias/watch classification |

## 4. Python-only machinery Pine does NOT reproduce
UUID/content-fingerprint identity, filesystem persistence, JSONL journals, Pydantic
contract models, isolated worker-process execution, the 120-min historical timeout,
host-RAM monitoring, and offline git-bundle mechanics are **PYTHON_ONLY** — engineering
scaffolding whose *analytical semantics* (determinism, no-lookahead, causal lifecycle)
Pine must preserve, but whose *implementation* Pine must not copy. Pine keeps state in
`var`/`array`/`matrix`/user-defined-types instead.

## 5. Timeframe / request architecture
Authority hierarchy unchanged: **W1 macro, D1 primary global, H4 operational, H1 local,
M15 / M5 precision** (scanner also supports M1, H3; **H6/H8/H12 deferred**). The Pine
script should request only the timeframes it needs via `request.security`
(D1/W1/H4/H1 + the chart's own), avoiding one request per timeframe where the chart
already provides it. **Switching the visible chart must not change the system's global
trend authority** (D1 stays primary regardless of the chart TF); the chart TF drives the
local/precision context only.

## 6. Chart-timeframe behavior
For a customer viewing M1/M5/M15/H1/H4/D1/W1: the current chart supplies the local
context and visuals; higher authority timeframes (D1 primary, W1 macro, H4 operational)
are always requested for global bias regardless of chart; lower timeframes are requested
only when needed for precision context. Display reflects the chart TF; global bias is
contextual and constant across chart switches.

## 7. Causal / non-repaint contract (strict)
- Production signals use **confirmed/closed** bars only (`barstate.isconfirmed`;
  `request.security(..., lookahead=barmerge.lookahead_off)`), mapping Python
  `availability_time = open + timeframe` onto Pine's closed-bar semantics.
- **No future-bar access**, no accidental higher-timeframe lookahead, no hindsight
  lifecycle rewrites. The forming chart bar is displayed distinctly from the confirmed
  analytical state.
- Anything requiring special adaptation (HTF request alignment, session boundary bars)
  is flagged **VALIDATE** for P9.

## 8. State management (design, not code)
Active POIs, POI lifecycle, BTMM setups + lifecycle, trend state, regime, and breakout
state map to Pine `var` persistent variables, `array`/`matrix` collections, `map` where
practical, and user-defined types mirroring the Python contracts' *fields* (not their
Pydantic machinery).

## 9. Drawing budget (bounded, provisional)
POIs → boxes; structure → lines; labels → BTMM/trend/regime/lifecycle. To avoid one
object per historical event forever: cap active objects (e.g. **N active POI boxes per
timeframe, provisional**), prune historical objects beyond a lookback, provide display
toggles, a max-zones-per-timeframe setting, and separate **debug vs client** modes. All
numeric caps are **ENGINEERING-PROVISIONAL**.

## 10. Client UI dashboard plan
A table with: Symbol · Global Bias · Regime · per-TF (W1/D1/H4/H1/M15/M5) trend · BTMM
state · Active POI · POI state · Liquidity · Momentum · Breakout · Pullback · Volatility ·
Trend Alignment · the eight component scores (BTMM/POI/Trend/Regime/Momentum/Breakout/
Liquidity/Volatility) · Final Confluence · Analytical Permission.

## 11. Client settings plan
Feed mode; canonical-symbol override; show/hide POIs / structure / BTMM labels /
dashboard; show-only-active POIs; minimum visual quality; display timeframes; alert
categories; debug/parity mode. Sensitive implementation internals are not exposed.

## 12. Alerts plan
`NEW_POI, POI_RETEST, POI_BREACH, POI_RECLAIM, POI_INVALIDATION, NEW_BTMM_SETUP,
BTMM_LIFECYCLE_CHANGE, TREND_CHANGE, REGIME_CHANGE, HIGH_CONFLUENCE_CONTEXT,
COUNTER_TREND_WARNING` — scanner information only, **no automatic broker order
execution** in the Pine scanner phase.

## 13. Python ↔ Pine parity program
For controlled FXCM TradingView windows, compare Python vs Pine at matching causal
timestamps across: meaningful swings, structure transitions, POIs + zone boundaries,
POI lifecycle, BTMM setup identities/context + lifecycle, trend, regime, momentum,
breakout, pullback, volatility, component scores, final confluence, analytical
permission. Classify each mismatch as `DATA_FEED_DIFFERENCE`,
`TIMEFRAME_AVAILABILITY_DIFFERENCE`, `PINE_IMPLEMENTATION_DEFECT`,
`SEMANTIC_CONTRACT_AMBIGUITY`, `PRECISION_ROUNDING`, or `EXPECTED_ENGINEERING_ADAPTATION`.

## 14. Debug / parity mode
A Pine development mode exposes deterministic compact values (e.g. a hidden table / plot
of structured numeric codes) comparable to Python exports, so parity acceptance relies on
**structured values**, not visual inspection alone.

## 15. Frozen future port sequence
`P1` Measurements → `P2` Structure → `P3` POI + lifecycle → `P4` BTMM + lifecycle →
`P5` BTRC → `P6` multi-timeframe orchestration → `P7` visual UI → `P8` alerts → `P9`
Python-vs-Pine parity validation → `P10` invite-only client release. **Do not jump to
P10.**

## 16. Hard-parity feasibility notes (disclosed, not silently simplified)
- **Content-addressed identity is not reproducible in Pine** (no UUID/sha256 identity
  scheme); Pine parity is compared on *semantic content* (prices, timestamps, states,
  scores), not on record ids — an expected engineering adaptation, not a defect.
- **Incremental POI merge / lifecycle scheduler** is the highest-risk port (complex
  persistent per-object state); it is **VALIDATE** and gated by the P9 parity harness.
- **Data-feed divergence is inherent** in Mode A (different broker OHLC) and is a
  disclosed product characteristic, not a bug — Mode B mitigates it where TradingView
  permits.
- No hard impossibility for the analytical semantics was found; the strategy is not
  simplified — only the Python engineering scaffolding (identity/persistence/process
  isolation) is intentionally not reproduced.
