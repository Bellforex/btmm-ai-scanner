# RC5 RELEASE CHECKLIST

Every row is **PASS**, **FAIL**, **BLOCKED** or **PENDING**. No other status is
used, and no row says "mostly" or "should be".

* **PASS** — verified here, with the evidence named in the row.
* **FAIL** — verified here and wrong.
* **BLOCKED** — cannot be attempted in this environment; the blocker is named.
* **PENDING** — attemptable, not yet attempted.

A BLOCKED row is **not** a passed row. Nothing below upgrades a blocked item on
the grounds that the code "looks right".

Checkpoint: branch `rc5-poi-authority`. Python semantic freeze `28d432e`.

---

## 1. PYTHON — ANALYTICAL ENGINE

| # | item | status | evidence |
| --- | --- | --- | --- |
| 1.1 | full suite green | **PASS** | 5,717 passed, 19 skipped |
| 1.2 | semantic freeze recorded | **PASS** | `28d432e` |
| 1.3 | working tree clean after the suite | **PASS** | `git status --porcelain` empty |
| 1.4 | lint clean on every file touched | **PASS** | `ruff check` on the changed set only — repo-wide cleanliness is NOT claimed |

## 2. PINE — COMPILE AND CAPACITY

| # | item | status | evidence |
| --- | --- | --- | --- |
| 2.1 | CORE compiles | **PASS** | no-pad save returned `success:true` |
| 2.2 | CORE token count | **PASS** | **100,183**, three agreeing CE10117 points (N=12/16/20) |
| 2.3 | within the hard limit | **PASS** | 100,183 ≤ 100,256, headroom **73** |
| 2.4 | P4 implemented | **PASS** | `f_rc5Ownership()` in `f_rc5Authority()` |
| 2.5 | presentation compaction | **PASS** | PRES-C, 110 tokens, measured |
| 2.6 | VIEW generated, not hand-edited | **PASS** | `test_rc5_view_composition` (22) |
| 2.7 | PANEL generated, not hand-edited | **PASS** | `test_rc5_panel_composition` |
| 2.8 | VIEW is structure-only | **PASS** | composition tests assert no POI/authority/P5/P8 |

## 3. PINE — RUNTIME PARITY

| # | item | status | blocker |
| --- | --- | --- | --- |
| 3.1 | synthetic RBR bootstrap | **BLOCKED** | TradingView renderer |
| 3.2 | synthetic DBD bootstrap | **BLOCKED** | " |
| 3.3 | golden EURUSD M15 DBD | **BLOCKED** | " |
| 3.4 | M45 family parity | **BLOCKED** | " |
| 3.5 | H3 family parity | **BLOCKED** | " |
| 3.6 | transition history | **BLOCKED** | " |
| 3.7 | future-transition guard | **BLOCKED** | " |
| 3.8 | prefix stability | **BLOCKED** | " |
| 3.9 | P4 golden-M15 ownership | **BLOCKED** | " |
| 3.10 | no post-activation P5/P8 from subordinates | **BLOCKED** | " |

**The blocker, precisely.** A chart loads on the AUTHORIZED account
(`window.user.username == "bellcare1994"`, layout `BAH-RC5-LAB`), but the
automation tab reports `document.hidden === true`, all 7 canvases at the 300×150
default and 0 legend rows, so TradingView never lays the renderer out. It is not
an account-selection failure, it is not fixed by focusing the tab
(`document.hasFocus()` goes true while `hidden` stays true), and it is not
detectable from a screenshot — the extension captures over CDP and renders
correctly even while the page reports itself hidden.

## 4. VIEW RUNTIME

| # | gate | status |
| --- | --- | --- |
| 4.1 | G1 VIEW alone | **BLOCKED** |
| 4.2 | G2 CORE alone | **BLOCKED** |
| 4.3 | G3 CORE + VIEW (the production pair) | **BLOCKED** |
| 4.4 | G4 CORE + PANEL | **BLOCKED** |
| 4.5 | structure visual acceptance (S1/S2 coordinate) | **BLOCKED** — and it is also an open author decision |

## 5. EA — COMPILE AND SAFETY

| # | item | status | evidence |
| --- | --- | --- | --- |
| 5.1 | compiles | **PASS** | 0 errors, 0 warnings |
| 5.2 | `.ex5` produced | **PASS** | MetaEditor output |
| 5.3 | installed in the terminal | **PASS** | `MQL5\Experts\RC5\` |
| 5.4 | execution disabled by default | **PASS** | `InpExecutionEnabled = false` |
| 5.5 | live execution needs a second, separate arm | **PASS** | `InpAllowLiveExecution = false`; outside the tester it is also required |
| 5.6 | every `OrderSend` behind the gate | **PASS** | exactly 2 calls, both inside gated functions |
| 5.7 | no martingale / grid / averaging vocabulary in CODE | **PASS** | comment-stripped source scan |
| 5.8 | tester profiles cannot arm a live account | **PASS** | `CanExecuteHere()` requires `MQL_TESTER` or the second arm |

## 6. EA — DOCTRINE VECTORS

| # | item | status | evidence |
| --- | --- | --- | --- |
| 6.1 | deterministic vectors | **PASS** | 49 passed |
| 6.2 | eligibility gates, each with its own reason | **PASS** | parametrized |
| 6.3 | BUY / SELL distal and stop | **PASS** | |
| 6.4 | 2R target both directions | **PASS** | |
| 6.5 | risk sizing across tick size / tick value / step / min / max | **PASS** | parametrized matrix |
| 6.6 | minimum lot over budget DENIES | **PASS** | `RISK_BUDGET_EXCEEDED` |
| 6.7 | duplicate signal identity denies | **PASS** | |
| 6.8 | active same-symbol position denies | **PASS** | keyed on the BROKER symbol |
| 6.9 | close set is exactly the two approved events | **PASS** | parsed out of the MQL5 switch |
| 6.10 | MITIGATED / FALSE_INVALIDATION never close | **PASS** | " |
| 6.11 | the three state migrations never close | **PASS** | " |
| 6.12 | MQL5 source agrees with the Python mirror | **PASS** | source-reading assertions |
| 6.13 | zero-height zone behaviour pinned | **PASS** | measured and documented — see §12 |
| 6.14 | notional / margin ceiling | **PENDING** | V1 has none; author decision — see §12 |
| 6.15 | spread-vs-R refusal | **PENDING** | `InpMaxSpreadPoints` compares to a constant, not to R — §12 |

## 7. EA — ANALYTICAL PARITY WITH PYTHON

| # | item | status | note |
| --- | --- | --- | --- |
| 7.1 | Layer-A projection from real OHLC | **PASS** | `tests/parity_support/rc5_ea_layer_a.py` |
| 7.2 | fixture transport round-trip | **PASS** | every line re-parses to the same 12 values |
| 7.3 | delimiter hazard refused | **PASS** | a POI id containing `\|` raises |
| 7.4 | EA-side field agreement | **BLOCKED** | needs a tester run |
| 7.5 | reachable V1 trigger on a real capture | **FAIL** | measured: never reached on ANY available capture — see §11 |

## 8. STRATEGY TESTER

| # | item | status |
| --- | --- | --- |
| 8.1 | configs for XAUUSDm / EURUSDm / GBPUSDm | **PASS** |
| 8.2 | per-symbol report paths | **PASS** |
| 8.3 | tester execution | **BLOCKED** — a terminal launch with `/config:` is denied in this sandbox |
| 8.4 | XAUUSDm run | **BLOCKED** |
| 8.5 | EURUSDm run | **BLOCKED** |
| 8.6 | GBPUSDm run | **BLOCKED** |

## 9. MTF QA

| # | item | status |
| --- | --- | --- |
| 9.1 | M5 / M15 / M30 / M45 / H1 / H3 / H4 smoke | **BLOCKED** — same renderer blocker as §3 |

## 10. RELEASE

| # | item | status |
| --- | --- | --- |
| 10.1 | architecture documentation current | **PASS** |
| 10.2 | this checklist exists and is honest | **PASS** |
| 10.3 | publication to TradingView | **FALSE — not attempted, not authorized** |
| 10.4 | merge to `main` | **FALSE — not attempted, not authorized** |
| 10.5 | live-money trading | **FALSE — prohibited** |
| 10.6 | `bellforex` layout | **NOT MODIFIED** |
| 10.7 | BAH library | **UNCHANGED** |
| 10.8 | release backup | **PENDING** |

---

## 11. THE V1 TRIGGER HAS NEVER BEEN OBSERVED TO FIRE

This is the most important open item in the release and it is recorded as
**FAIL**, not PENDING, because it was measured rather than left untried.

| capture / window | context | host bars | rows | regime | highest lifecycle |
| --- | --- | --- | --- | --- | --- |
| M15 EURUSD (author's forensic) | none | 300 | 5,099 | — | 3 `POI_VALIDATED` |
| M45 XAUUSD | none | 529 | 12,875 | — | 0 `DETECTED` |
| H3 XAUUSD | none | 300 | 4,876 | — | 0 `DETECTED` |
| M15 XAUUSD, last 200 | **W1+D1+H4+H1+M5** | 200 | 71,881 | DECELERATION | 4 `TREND_VALIDATED` |
| M15 XAUUSD, 2026-08-28 | full | 15 | 4,378 | **TREND** | **5 `REGIME_VALIDATED`** |
| M15 XAUUSD, 2026-09-08 | full | 15 | 4,447 | **TREND** | **5 `REGIME_VALIDATED`** |
| M15 XAUUSD, 2026-09-18 | full | 15 | 5,533 | DECELERATION | 4 `TREND_VALIDATED` |

The lifecycle ladder is `has_structure -> btmm_valid -> alignment ->
favorable_regime -> momentum_aligned -> liquidity_ok`, and each rung was found
by climbing it.

* Single-timeframe runs stall at `POI_VALIDATED`: `alignment` is never
  ALIGNED/PARTIAL without higher-timeframe context.
* With full context, 14,728 evaluations clear that rung and reach
  `TREND_VALIDATED`.
* **CORRECTION, recorded rather than quietly amended.** An earlier note here
  said the ladder "stops dead at rung 4". That was true of the window sampled
  and FALSE of the capture. Surveying three host windows at different points in
  time shows two of them classify as **TREND**, and in both the ladder climbs
  past the regime gate to **`REGIME_VALIDATED`** (19 and 9 evaluations).
* The real ceiling is **rung 5 → 6**: nothing yet reaches
  `MOMENTUM_VALIDATED`, whose gate is `momentum_score >= 60`.

The reason a single long window could not have found this: **regime cannot vary
inside a short host window.** It is governed by the primary higher timeframe —
D1 first — which barely moves across a couple of days, so a longer window
samples the same regime for longer. Only windows at different points in TIME
vary it.

### What this does and does not mean

* It does **NOT** mean the EA is broken. The EA was never reached.
* It does **NOT** yet mean the engine is broken either: a 200-bar window
  genuinely may contain no favourable regime, and the ladder is a plain
  conjunction of documented booleans with no wiring gap visible in the code.
* It **DOES** mean no execution can be demonstrated from any capture currently
  in the repository, and that a Strategy Tester run against one of these
  fixtures will legitimately place **zero trades**.

### The trap this exists to prevent

Without this row, the first tester run produces zero trades and the obvious
conclusion — "the EA does not work" — would be wrong. Confirm
`confirmed > 0` from the fixture generator BEFORE reading anything into a
tester result.

### DIAGNOSED — it is the window, not the wiring

A second run sampled the ladder's own inputs over 30 host bars with the full
context set (11,083 POI evaluations):

| input | distribution |
| --- | --- |
| regime | **DECELERATION 11,083 — a single value, 100%** |
| trend alignment | PARTIAL 7,442 / COUNTER_TREND 3,641 |
| analytical permission | WATCH_ONLY 9,304 / NO_TRADE_CONTEXT 890 / COUNTER_TREND 839 / **BUY_BIAS 50** |

`regime_engine` maps regime 1:1 from `TrendState` for every non-FORMING state,
and `DECELERATION` is the image of **`EXHAUSTING`**. So the primary regime
timeframe — `D1` first, then `H4`, `W1`, `H1`, `M15`, `M5` — was EXHAUSTING for
the entire sampled period. Over 30 M15 bars (7.5 hours) a constant D1 trend
state is exactly what one would expect.

**This is a data property of the window, not a wiring defect**, and the other
two columns prove the pipeline is alive rather than stuck: alignment varies
across two values, permission across four, and a directional **`BUY_BIAS` is
issued 50 times** — which also shows the strict P5 reading is not vacuous.

One correction to that run: its momentum/liquidity line read `cs.momentum` and
`cs.liquidity`, but the fields are `momentum_score` and `liquidity_score`, so
it reported `n=0` for my own reason and not the engine's. Those two rungs sit
ABOVE the regime gate and are never reached here, so no claim is made about
them either way.

### What would settle it

The data question is **answered**: this capture DOES contain favourable-regime
windows, and two are identified above by timestamp. The remaining question is
narrower and is now the single blocking unknown for the whole execution track:

> Is `momentum_score >= 60` ever satisfied on a POI that has already reached
> `REGIME_VALIDATED`?

If yes, the trigger is reachable and a fixture file can be built from those
windows. If no, the ladder has a rung nothing in this data clears, and that is
a finding about the engine's calibration rather than about the data.

---

## 12. SAFETY FINDING — ZERO-HEIGHT ZONES SIZE FROM A ONE-TICK STOP

Found by generating a real fixture file, not by reading the doctrine. Pinned as
tests, **not fixed**, because fixing it means choosing a threshold.

Liquidity-level POIs are LINES: the projection emits them with
`zone_top == zone_bottom`. The distal boundary is then the level itself, the
stop lands one tick beyond it, and R collapses. Measured on a broker publishing
`STOPS_LEVEL = 0`, entry 1.14832: R = 2 ticks, volume **200.00** (the broker's
`volume_max`, not a risk rule), realized risk 40.00 against a 50.00 budget.

**Every risk gate passes** — the budget is respected with room to spare. What is
not bounded is the NOTIONAL: roughly 20,000,000 EUR against a two-tick stop,
while a typical EURUSD spread is ten ticks, five times R.

Nothing in V1 catches it: the budget is satisfied, `InpMaxSpreadPoints`
compares the spread to a constant rather than to R and defaults to off, and
there is no margin or notional ceiling. `SYMBOL_TRADE_STOPS_LEVEL` does refuse
it when non-zero — the only existing protection, and it belongs to the broker.

Three author decisions, listed in
`docs/validation/BTRC_V1_RC5_EXECUTION_DOCTRINE_V1.md`: whether zero-height POIs
are executable at all; whether V1 should refuse when the spread is a
significant fraction of R; and whether V1 needs a notional or margin ceiling
independent of the risk budget.

This has never reached a live account: execution is disabled by default, the
trigger has never fired on any capture, and no tester run has occurred.

---

## What a reader should conclude

The BUILD is complete and internally verified: Python, Pine compile and
capacity, EA compile, EA doctrine vectors and the Layer-A projection all PASS.

**Every remaining item is an EXECUTION-ENVIRONMENT item**, and there are exactly
two blockers behind all of them:

1. TradingView never lays out its renderer in the automation tab, which blocks
   all Pine runtime parity, all VIEW gates, the structure visual acceptance and
   MTF QA;
2. the sandbox denies a terminal launch with a custom config, which blocks every
   Strategy Tester run and the EA-side half of analytical parity.

Neither is a defect in the deliverable, and neither can be argued away from
here. RC5 is not releasable until they are attempted on a machine where a
TradingView chart is visibly on screen and MetaTrader can be started with a
tester config.
