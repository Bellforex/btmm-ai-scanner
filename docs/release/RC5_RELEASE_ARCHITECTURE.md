# RC5 — RELEASE ARCHITECTURE

Three artifacts, two layers, one canonical source of semantics. This document
says what each part is, what has been verified, and — in the same sentences —
what has not.

> Nothing here claims runtime approval. Where a claim needs a chart or a
> Strategy Tester run, the status is BLOCKED and says so. See
> `RC5_RELEASE_CHECKLIST.md` for the row-by-row status.

---

## 1. THE TWO LAYERS

```
  LAYER A — RC5 ANALYTICAL ENGINE          LAYER B — EXECUTION DOCTRINE V1
  ───────────────────────────────          ──────────────────────────────
  Python, frozen at 28d432e                MQL5, mt5/Experts/RC5_EA.mq5
  Pine port (CORE / VIEW / PANEL)          + tools/rc5_ea_fixtures.py

  produces STATE                           consumes STATE, produces ORDERS
  never specifies an order                 never re-decides analysis
```

**The separation is the point.** An audit established that RC5 never contained
an execution contract: no entry rule, no stop rule, no size rule, no exit rule.
Execution Doctrine V1 was authored afterwards, as a separate downstream layer.
Nothing in Layer B is a statement about what the scanner has always done, and
Layer A was not modified to make Layer B easier.

Three sentences that are FALSE and must never be written: "RC5 always used 2R",
"RC5 uses 0.5% risk", "P5 means buy".

---

## 2. LAYER A — THE PYTHON FREEZE

`28d432e` is the analytical authority. Pine and MQL5 are ports of it; where
they disagree with it, they are wrong.

Suite: **5,688 passed, 19 skipped.**

---

## 3. LAYER A — THE PINE PORT

### 3.1 Stages

| stage | what it carries | status |
| --- | --- | --- |
| P1 | Arm E Base size — one canonical `0.60` constant | implemented, measured |
| P2 | causal structural arrival, INCLUDING the walk bootstrap | implemented, measured |
| P3 | Base family (RBR / DBR / RBD / DBD) at the Base's FIRST candle | implemented, measured |
| P4 | formation ownership | implemented, measured, compiled |

P2's bootstrap is not decoration. Structural direction has two sources — the
walk's initial HH+HL / LH+LL pair, and each later transition's
`direction_after`. A port carrying only the second half would pass **every
real-data check available**, because all three FXCM captures have zero Bases in
their bootstrap-only window. `test_base_arrival_bootstrap_fixture` exists
solely to make that divergence visible.

### 3.2 P4 — formation ownership, the final doctrine

* Owners: **RALLY_BASE_RALLY and DROP_BASE_DROP only.** RBD, DBR and UNKNOWN
  own nothing.
* Ownable members: ladder ranks 3–7 — star, engulfing, hammer/shooting star,
  doji, pressure wick. ORDER BLOCK and B2S/S2B (ranks 1–2) are excluded because
  precedence against a Base is unestablished and must not be frozen by
  omission. FVG is excluded because a departure's imbalance is its own region,
  not a restatement of the Base.
* **Contained:** `mf >= bf and ml < bl` — strictly before the departure. A
  pattern formed ON the departure describes the impulse and keeps independence.
* **Co-extensive:** the same complete formation span, the same source count and
  the same zone on BOTH edges, with no tolerance.
* Direction must agree.
* **Activation:** `max(owner, member)` availability, compared against
  `time_close` because `wAvailT` is defined as the bar CLOSE time. A Base
  discovered later can never retroactively suppress a pattern that was
  actionable before it existed.
* `f_rc5Ownership()` runs inside `f_rc5Authority()` immediately after
  `map.clear(rc5Subordinate)` and BEFORE the same-origin loop, which only ever
  ADDS to that map and so cannot hand standing back.
* Base stays OUT of `REVERSAL_LADDER`.

Ownership changes STANDING, never IDENTITY: a subordinate keeps its type, its
geometry and its transport code.

### 3.3 Capacity — the numbers that bound everything

| | |
| --- | --- |
| CORE before compaction | 99,304 |
| presentation compaction (PRES-C) | −110 |
| optimized pre-P4 CORE | 99,194 |
| **CORE with P4** | **100,183** |
| P4 cost | +989 |
| hard limit | 100,256 |
| **hard headroom** | **73** |

Three agreeing CE10117 points (N=12/16/20 → 100,183) plus a no-pad save
returning `success:true`, so this is a compile, not an inference from the token
error.

**73 tokens is the operating constraint.** No diagnostics, no verbose strings,
no plots, no display polish and no experimental logic may be added to CORE.
Presentation work goes to VIEW or PANEL.

### 3.4 PRES-C, and why two obvious candidates were worth zero

| variant | saved |
| --- | --- |
| drop `text_halign` / `text_valign` (both already default) | **0** |
| drop the redundant `box.set_text` | 51 |
| drop the `"M15 • "` timeframe prefix | 59 |
| **PRES-C total** | **110** |

`box.set_text` was provably a no-op: the text is a pure function of the POI
type, and `array.set(poiType, …)` occurs nowhere in CORE, so a registered POI's
type is immutable and an existing box's text can never change.

Compact POI names were **not available**: they come from `bahui.poiTypeLabel()`
in the published BAH library, which is protected, and rebuilding them inside
CORE would ADD tokens. Do not restore the removed verbosity.

### 3.5 CORE / VIEW / PANEL

```
        CORE  (canonical semantics, hand-authored)
          │
          ├── + rc5_view_presentation.pine  ──>  VIEW    structure overlay only
          └── − chart-space renderers       ──>  PANEL   screen-space diagnostics
```

* **CORE + VIEW is the production configuration.** PANEL is optional
  diagnostics.
* VIEW and PANEL are **generated** by `tools/rc5_compose.py` and never
  hand-edited; the composition tests fail on a stale or edited artifact.
* VIEW must stay structure-only. The trendline renderer deliberately stayed in
  CORE: its winner reads `rc5TlHit`, which the qualified sweep engine writes
  from POI references, so a structure-only VIEW cannot reproduce it.
* Adding P4 and PRES-C left VIEW **byte-identical** — both fall inside existing
  cut regions.

---

## 4. LAYER B — EXECUTION DOCTRINE V1

### 4.1 Trigger

`lifecycle == LIQUIDITY_VALIDATED`, the last analytical state the frozen engine
assigns. The states above it (`RISK_VALIDATED`..`CLOSED`) are declared future
bot scope and the engine never produces them.

A setup is eligible only when ALL of: authoritative, `validity == VALID`, P5
permission, `lifecycle == LIQUIDITY_VALIDATED`, and a direction.
**P5 alone never triggers an order.**

### 4.2 Stop geometry — derived, not chosen

Read out of `poi/lifecycle.py`'s breach rule:

| direction | proximal | distal | V1 stop |
| --- | --- | --- | --- |
| BULLISH | `zone_top` | `zone_bottom` | `zone_bottom − 1 tick` |
| BEARISH | `zone_bottom` | `zone_top` | `zone_top + 1 tick` |

All three lifecycle boundary functions take `(candle, direction, zone_top,
zone_bottom, tolerance)` and **no POI family**, so the mapping is uniform with
zero ambiguous families. "Tick" is `SYMBOL_TRADE_TICK_SIZE`, never `_Point`.

A stop that violates `SYMBOL_TRADE_STOPS_LEVEL` or `SYMBOL_TRADE_FREEZE_LEVEL`
is **DENIED** (`BROKER_STOP_INVALID`). It is never silently widened: the distal
boundary is semantic, and moving it would execute a trade the reference engine
did not specify.

### 4.3 Target and risk — V1 EXECUTION POLICY

* `InpRewardRisk = 2.0`. **2R is V1 policy. RC5 specifies no reward multiple.**
* `InpRiskPercent = 0.5`, for tester/research. **RC5 specifies no risk
  fraction.**

Volume is a pure function of equity, stop distance and the broker contract. It
reads nothing about previous trades, and the absence is structural — there is
no prior-result term to switch on. No martingale, no grid, no averaging down,
no loss-recovery multiplier, no progressive escalation.

When the smallest legal lot would risk MORE than the budget, V1 **denies**
(`RISK_BUDGET_EXCEEDED`) rather than rounding the risk up. That is the volume
counterpart of never widening a stop.

### 4.4 Concurrency and identity

* At most **one RC5 position per resolved broker symbol**. No pyramiding, no
  same-symbol hedge.
* At most **one execution per semantic setup**. The signal id is
  `symbol|tf|poiId|poiType|direction|barTime` — a bar timestamp alone is not
  enough, because several POIs can confirm on the same bar.
* Consumption is remembered in memory AND in a terminal GlobalVariable keyed by
  a hash of the id, so an `OnInit` (timeframe change, recompile, reattach) does
  not re-arm a spent signal.

### 4.5 The close set — exactly two events

| event | V1 action | why |
| --- | --- | --- |
| `GENUINE_INVALIDATION_CONFIRMED` | **CLOSE** | the walk sets `terminal` |
| `PoiTerminalReason.INVALIDATED` | **CLOSE** | terminal reason |
| `MITIGATED` | **NO CLOSE** | set at the FIRST TOUCH; a layer entering AT a POI touches it by entering, so this would close every trade at its own entry |
| `FALSE_INVALIDATION_CONFIRMED` | **NO CLOSE** | the engine keeps the setup VALID; closing exits the exact trap the doctrine survives |
| `RECLAIM_WITHOUT_DISPLACEMENT` | **NO CLOSE** | a `PoiLifecycleStatus`, never sets `terminal`, walk continues, POI stays VALID |
| `RECLAIM_FAILED` | **NO CLOSE** | same |
| `PROMOTED_TO_ORDER_BLOCK` | **NO CLOSE** | terminal but SUPERSEDED, explicitly "NOT a failure"; the formation lives on as the ORDER BLOCK record |

Plus the broker's own execution of SL and TP. **Nothing else closes a V1
position automatically** — not an opposite pattern, not a trend change, not a
new authoritative POI.

The three state migrations log `<EVENT>_STATE_MIGRATION`: the RECORD moved, the
trade did not. For `PROMOTED_TO_ORDER_BLOCK`, NEW entries need no extra rule —
SUPERSEDED is not VALID, so the existing eligibility gate already refuses them,
and promotion never opens a second trade.

### 4.6 Safety gates

Five, all required, and the fifth only ever tightens:

1. `InpExecutionEnabled` (default **false**)
2. terminal algo-trading permission
3. account algo-trading permission
4. account expert permission
5. `MQL_TESTER` **or** `InpAllowLiveExecution` (default **false**)

Consequence worth stating: the tester `.set` files carry
`InpExecutionEnabled=true`, and because of gate 5 **they cannot arm a live
account even if loaded onto a live chart**.

Every `OrderSend` in the program — there are exactly two, one to open and one to
close — is inside a function that begins with that gate.

### 4.7 The EA has no detector

`InpSetupFile` reads analytical state EXPORTED from the reference engine, one
setup per line. It is not a signal source. With no file configured — the
default — the EA dispatches nothing, because a third independent implementation
of RC5 in MQL5 is exactly what this architecture avoids.

With execution disabled the whole pipeline still runs and logs
`RC5PLAN … WOULD_EXECUTE` with every field of the intended trade. The only thing
that does not happen is the `OrderSend`, which is what makes that line a
faithful preview.

---

## 5. WHAT IS BLOCKED, AND BY WHAT

| blocked | blocker |
| --- | --- |
| all Pine runtime parity (P2/P3/P4), all VIEW gates, structure visual acceptance, MTF QA | TradingView never lays out its renderer in the automation tab: a chart loads on the authorized account but `document.hidden === true`, 7 canvases at 300×150, 0 legend rows |
| every Strategy Tester run, and the EA-side half of analytical parity | the sandbox denies launching the terminal with a custom `/config:` |

Both are environment properties, not defects in the deliverable, and neither can
be resolved from here.

---

## 6. THE PARITY TABLE

The author asked for `FIXTURE | PYTHON VALUE | EA VALUE | MATCH`. The EA column
cannot be filled in this environment — the Strategy Tester will not launch — so
filling it would be fabrication. What IS provable offline is the field-level
contract and the transport, and that is the table below.

| # | field | Python source (frozen engine) | EA consumer | transport | EA value |
| --- | --- | --- | --- | --- | --- |
| 1 | symbol | the logical root (`XAUUSD`) | `ResolveSymbol` discovers the suffix | **PASS** | **BLOCKED** |
| 2 | timeframe | host timeframe, in minutes | `RC5Setup.timeframe` | **PASS** | **BLOCKED** |
| 3 | bar time | `LevelABar.candle.event_time_utc`, epoch seconds | `RC5Setup.barTime` | **PASS** | **BLOCKED** |
| 4 | POI identity | `poi_type` + the record uuid prefix | `RC5Setup.poiId` | **PASS** | **BLOCKED** |
| 5 | POI type | `PoiType` enum ORDER | `RC5Setup.poiType` | **PASS** | **BLOCKED** |
| 6 | direction | `PoiObservation.direction` | `RC5_DIR_*` | **PASS** | **BLOCKED** |
| 7 | zone top | `PoiObservation.zone_top` | `RC5Setup.zoneTop` | **PASS** | **BLOCKED** |
| 8 | zone bottom | `PoiObservation.zone_bottom` | `RC5Setup.zoneBottom` | **PASS** | **BLOCKED** |
| 9 | authority | NOT in `LevelABar.suppressed_poi_ids` | `RC5Setup.authoritative` | **PASS** | **BLOCKED** |
| 10 | validity | `rc5_validity(state)` | `RC5_VALID / INVALIDATED / SUPERSEDED` | **PASS** | **BLOCKED** |
| 11 | P5 permission | `BtrcDecision.analytical_permission` | `RC5Setup.p5Permission` | **PASS** | **BLOCKED** |
| 12 | lifecycle | `BtrcDecision.lifecycle_state` | `RC5_LC_*` | **PASS** | **BLOCKED** |

**transport PASS** means: every line the projection emits, for every POI on
every confirmed bar of a real FXCM capture, splits on `|` into exactly twelve
fields that re-read to the identical values — the same rule `ParseFixtureLine`
applies. **EA value BLOCKED** means no EA-side value exists yet; it is not a
pass.

### One derivation worth stating, because it was not obvious

`AnalyticalPermission` is a **bias, not a boolean**, so "P5 permission is true"
had to be derived rather than assumed. `t5_engine` issues `BUY_BIAS` /
`SELL_BIAS` only when trend alignment is ALIGNED or PARTIAL **and** the final
confluence clears `high_confluence_min`, and it stamps them with the POI's own
direction — so a directional bias always agrees with its POI by construction.
Everything else in that same function is an explicit downgrade: `WATCH_ONLY` is
where moderate confluence and extreme volatility land, `NO_TRADE_CONTEXT` is low
confluence, and `COUNTER_TREND` carries the comment "execution priority low".

V1 therefore takes the STRICT reading: a directional, high-confluence bias that
agrees with the POI.

**Two cases are genuinely arguable and are counted rather than silently
folded**: `ALLOW_BOTH_CONTEXT` (neutral trend, adequate confluence) and
`COUNTER_TREND`. `LayerAProjection.arguable` reports how many confirmed,
authoritative, valid setups fall into them, so the author can see what the
strict reading costs before deciding whether to widen it.

### The reachability finding

Measured, and it changes how a tester result must be read: on the author's
300-bar M15 EURUSD capture run single-timeframe, **no POI reaches
`LIQUIDITY_VALIDATED`** — the ladder stops at `POI_VALIDATED`, because
`TREND_VALIDATED` needs a trend alignment that a single timeframe with no
higher-timeframe context does not produce. M45 and H3 never leave `DETECTED`.

A tester run against such a fixture file will place zero trades, and that is
correct behaviour rather than an EA failure.

Diagnosed by climbing the ladder rung by rung. With full context the regime
gate was the first obstacle, but that turned out to be a property of the WINDOW
rather than of the capture: surveying three host windows at different points in
time, two classify as **TREND** and in both the ladder climbs past the regime
gate to **`REGIME_VALIDATED`**.

The reason one long window could not have shown this is worth keeping: **regime
cannot vary inside a short host window**, because it is governed by the primary
higher timeframe (D1 first), which barely moves across a couple of days.

The ceiling is therefore **rung 5 → 6**, `momentum_score >= 60`, and whether
that is ever satisfied on a `REGIME_VALIDATED` POI is the single blocking
unknown for the entire execution track. See `RC5_RELEASE_CHECKLIST.md` §11.
