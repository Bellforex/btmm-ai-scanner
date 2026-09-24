# RC5 — DEMONSTRATION PACKAGE

A truthful walkthrough of what exists, usable **even though both runtime
environments are blocked**. Every claim here is backed by something runnable;
every gap is labelled rather than skipped.

> **No real trade has been executed.** No Strategy Tester run has happened, no
> live order has been placed, and no live account has been armed. Where a claim
> needs a runtime, it says `RUNTIME PENDING`.

---

## 1. The architecture, in one picture

```
  LAYER A — RC5 ANALYTICAL ENGINE          LAYER B — EXECUTION DOCTRINE V1
  ───────────────────────────────          ──────────────────────────────
  Python, frozen at 28d432e                MQL5, mt5/Experts/RC5_EA.mq5
  Pine port: CORE / VIEW / PANEL           + tools/rc5_ea_fixtures.py

  produces STATE                           consumes STATE, produces ORDERS
  never specifies an order                 never re-decides analysis
```

The separation is not cosmetic. An audit established that RC5 never contained
an execution contract — no entry rule, no stop rule, no size rule, no exit
rule. Layer B was authored afterwards, and Layer A was **not modified** to make
it easier.

Three sentences that are FALSE and appear nowhere: *"RC5 always used 2R"*,
*"RC5 uses 0.5% risk"*, *"P5 means buy"*.

## 2. Python — the reference

**5,798 tests passing, 19 skipped.** Semantic freeze `28d432e`. Pine and MQL5
are ports of it; where they disagree with it, they are wrong.

## 3. Pine — a hard capacity ceiling, measured not estimated

| | |
| --- | --- |
| CORE | **100,183 tokens** |
| hard limit | 100,256 |
| **headroom** | **73** |

Established by three agreeing CE10117 measurements (N = 12 / 16 / 20, all
→ 100,183) plus a no-pad save returning `success: true` — a compile, not an
inference from the token error.

Worth showing because it explains every later constraint: 73 tokens is not
development space.

## 4. P4 — formation ownership, with the case that motivated it

The author's original complaint: *"I see a Base, RC5 shows a Shooting Star."*

A Base is not a reversal and is deliberately outside `REVERSAL_LADDER`, so
before P4 a candle pattern sitting **inside** a Base outranked nothing and
survived as the visible authoritative record, while the Base that actually
described the decision went unranked.

On the golden M15 formation, after P4:

| record | standing |
| --- | --- |
| `BASE_DROP` / DBD | **PRIMARY** |
| `BEARISH_PRESSURE_WICK` | SUBORDINATE — contained |
| `DOJI` | SUBORDINATE — contained |
| `EVENING_STAR` | SUBORDINATE — **exact co-extension** |

Ownership changes STANDING, never IDENTITY: every subordinate keeps its type,
its geometry and its transport code.

`RUNTIME PENDING` — implemented, compiled and token-verified; Pine runtime
parity is blocked.

## 5. Execution Doctrine V1 — the decision flow

```
analytical eligibility → LIQUIDITY_VALIDATED
  → duplicate identity guard → same-symbol concurrency guard      (cheap, first)
  → confirmation proximity   → obtain executable entry
  → entry proximity          → distal SL → R > 0
  → spread/R → risk sizing → legal volume → margin exposure
  → execution
```

| parameter | value | what it is |
| --- | --- | --- |
| trigger | `LIQUIDITY_VALIDATED` | the last state the frozen engine assigns |
| stop | distal ± one `SYMBOL_TRADE_TICK_SIZE` | **derived** from `poi/lifecycle.py` |
| `InpRiskPercent` | 0.5 | V1 policy |
| `InpRewardRisk` | 2.0 | V1 policy |
| `InpMaxSpreadToRisk` | 0.25 | V1 policy |
| `InpMaxMarginFraction` | 0.20 | V1 policy |
| `InpMaxEntryDistanceSpreads` | 1.0 | V1 policy |

The close set is exactly two events — `GENUINE_INVALIDATION_CONFIRMED` and
`PoiTerminalReason.INVALIDATED` — plus the broker's own SL/TP. `MITIGATED`
never closes, because it is set at the FIRST TOUCH and an execution layer that
enters AT a POI touches it by entering.

## 6. Safety demonstration 1 — the micro-R trap

A liquidity level is a LINE: `zone_top == zone_bottom`. Real exported data:

```
EURUSD|15|1789724700|CURRENT_DAY_LOW~0c31feb6b40e|27|1|1.14831|1.14831|1|0|0|1
```

Entry 1.14832 gives R = 2 ticks. Sized against a 0.5% budget that is **200
lots** — roughly a 20,000,000 EUR notional — at a realized risk of 40.00
against a 50.00 budget. **Every risk gate passed.** What bounded it was
`volume_max`, a broker contract limit, not a risk rule. A typical spread of ten
ticks is **five times R**, so the position is stopped out by transaction cost
alone.

Now **DENIED** by `SPREAD_TO_RISK_INVALID`, and the zero-height POI remains
fully valid *analytically* — V1 refuses to trade it, nothing deletes it.

## 7. Safety demonstration 2 — the macro-R trap

The very first real `LIQUIDITY_VALIDATED` setup the search produced was a
`HAMMER` at **308.75 – 312.85** confirmed while gold traded near **4,400** — a
POI formed when gold was around $310, never breached, still VALID.

It passed the risk gate, the spread/R gate **and** the margin gate
simultaneously. V1 would have bought at 4,400 with a stop at 308.74 and a
target at 12,582.52.

The spread gate is blind here **by construction**: a pathologically large R
makes the spread ratio trivially small.

Now **DENIED** by `CONFIRMATION_PROXIMITY_INVALID` — distance 4087.15 against a
tolerance of 0.20. Kept as a permanent regression fixture.

Two deliberate non-additions, both recorded: **no POI age cap** (age does not
prove irrelevance; a level genuinely revisited passes on its merits) and **no
maximum-R gate** (once proximity passes, R is local geometry). R and TP
distances are logged as diagnostics and never cause a denial.

## 8. The two golden setups — real, from the engine

| | GOLDEN 1 | GOLDEN 2 |
| --- | --- | --- |
| bar | 2026-08-30 22:45 UTC | 2026-09-08 14:45 UTC |
| POI | HAMMER BULLISH | MORNING_STAR BULLISH |
| zone | 4450.54 – 4467.06 | 4391.07 – 4399.54 |
| confirmation close | 4461.29 — **inside** | 4398.65 — **inside** |
| momentum | BULLISH 69 | STRONG_BULLISH 72 |
| liquidity | 70 | 70 |
| **distal / stop** | **4450.54 / 4450.53** | **4391.07 / 4391.06** |
| entry, R, TP, volume, margin | `PENDING_TESTER` | `PENDING_TESTER` |

Both are momentum-ALIGNED — the rung every earlier candidate failed, all of
which were counter-momentum.

**The bar close is not used as an entry.** It proves Stage-1 proximity and
nothing else; it is a hindsight price the layer could never have been filled
at.

## 9. EA — compile evidence

**0 errors, 0 warnings.** `.ex5` built and installed at
`MQL5\Experts\RC5\RC5_EA.ex5`.

Five safety gates, all required, and the fifth only ever tightens:
`InpExecutionEnabled` (default false) · terminal permission · account
permission · expert permission · `MQL_TESTER` **or** `InpAllowLiveExecution`
(default false).

Consequence worth stating: the tester profiles carry
`InpExecutionEnabled=true`, and because of that fifth gate **they cannot arm a
live account even if loaded onto a live chart**.

Exactly two `OrderSend` calls exist in the program — one to open, one to close —
and both sit behind that gate.

## 10. What is NOT claimed

| | status |
| --- | --- |
| a real tester trade has executed | **NO** |
| Stage-2 entry proximity observed against a real quote | **NO** — vector-verified only |
| Pine runtime parity | `RUNTIME PENDING` — TradingView renderer blocked |
| structure coordinates S1/S2 visually accepted | `PENDING` — decision pack ready, two timestamps to inspect |
| profitability | **not measured, not claimed, not pursued** |
| live deployment | **NOT APPROVED** |

The two blockers are environment properties, not defects: TradingView never
lays out its renderer in the automation tab, and the sandbox denies launching
MetaTrader with a tester config.

## 11. If someone asks "so does it work?"

The honest answer: **the analysis is verified, the execution layer is verified
against deterministic vectors and its own source, and neither has been observed
running against live market data.** Two traps that would have produced bad
trades were found and closed by building the verification, not by reasoning
about it — which is the strongest thing this package demonstrates.
