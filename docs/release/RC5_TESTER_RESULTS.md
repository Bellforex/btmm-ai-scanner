# RC5 — STRATEGY TESTER ACCEPTANCE RESULTS

**The acceptance run happened.** Real Exness XAUUSDm history, real executable
quotes, real `OrderCalcMargin`. Every number below came out of the tester
journal and was extracted by `tools/rc5_journal_parser.py`, not read by eye.

```
Core 1  XAUUSDm,M15: testing of Experts\RC5\RC5_EA.ex5
        from 2026.08.25 00:00 to 2026.09.12 00:00
        every tick generating · quality of analyzed history 100%
```

Broker contract as the EA read it at runtime:

```
RC5 XAUUSDm digits=3 point=0.001 tick=0.001 tickVal=0.1
            vol[0.01..200.00/0.01] stops=0 freeze=0 fill=3 spread=260
```

`stops=0` matters: the broker imposes **no** minimum stop distance, so the
micro-R protection rests entirely on the V1 gates.

Init line, with the safety state visible:

```
RC5 EA2-B: trigger=LIQUIDITY_VALIDATED | RR=2.00 | risk=0.50% |
           magic=5150001 | tester=1 | liveArmed=0 | canExecute=1
```

`tester=1`, `liveArmed=0` — execution was permitted **because** it was the
Strategy Tester, and the live arm stayed false throughout.

---

## RESULTS — all four fixtures

| fixture | decision | why |
| --- | --- | --- |
| stale HAMMER 308.75–312.85 | **DENIED** | `CONFIRMATION_PROXIMITY_INVALID` |
| zero-height level 4461.374 | **DENIED** | `ENTRY_PROXIMITY_INVALID` |
| GOLDEN 1 HAMMER | **EXECUTED** | all gates passed |
| GOLDEN 2 MORNING_STAR | **EXECUTED** | all gates passed |

Parser: `plans=4 denies=2 setups=4 UNPARSED=0`, **duplicate signal ids = 0**.

### GOLDEN 1 — HAMMER, 2026-08-30 23:00 UTC

| field | observed |
| --- | --- |
| confirmation price (Exness) | inside the zone, `confDist = 0.000` |
| **actual executable ASK** | **4461.849** |
| entry distance / tolerance | 0.000 / 0.260 → **Stage 2 PASS** |
| distal / SL | 4450.540 / **4450.539** — exactly one tick beyond |
| R | 11.310 |
| spread / spread-to-R | 0.260 / **0.0230** ≤ 0.25 |
| risk budget / realized | 50.00 / **45.24** |
| volume | 0.04 |
| **`OrderCalcMargin`** | **35.69** |
| margin fraction | **0.0036** ≤ 0.20 |
| TP | **4484.469** = entry + 2R |
| order | `market buy 0.04 XAUUSDm sl: 4450.539 tp: 4484.469`, deal #2 filled at 4461.849 |
| executions for this identity | **1** |

Closed 2026-08-30 23:37:39 at 4450.459 — stopped out.

### GOLDEN 2 — MORNING_STAR, 2026-09-08 15:00 UTC

| field | observed |
| --- | --- |
| confirmation price | inside the zone, `confDist = 0.000` |
| **actual executable ASK** | **4398.837** |
| entry distance / tolerance | 0.000 / 0.260 → **Stage 2 PASS** |
| distal / SL | 4391.070 / **4391.069** |
| R | 7.768 |
| spread-to-R | **0.0335** ≤ 0.25 |
| risk budget / realized | 49.77 / **46.61** |
| volume | 0.06 |
| **`OrderCalcMargin`** | **52.79** |
| margin fraction | **0.0053** ≤ 0.20 |
| TP | **4414.373** = entry + 2R |
| order | `market buy 0.06 XAUUSDm sl: 4391.069 tp: 4414.373`, deal #4 filled at 4398.837 |
| executions for this identity | **1** |

Closed 2026-09-08 16:08:29 at 4391.046 — stopped out.

### NEGATIVE 1 — the stale POI

```
RC5DENY CONFIRMATION_PROXIMITY_INVALID ...|price=4458.786
        |zone=308.750..312.850|distance=4145.936|spread=0.260
        |tick=0.001|tolerance=0.260
```

Exness put the confirmation price at **4458.786** against a zone at 308–312:
a distance of **4145.936** against a tolerance of **0.260**. Denied at Stage 1.

Short-circuit confirmed: `entry=0.000 sl=0.000 R=0.000 vol=0.00 margin=0.00
spreadToR=0.0000`. Nothing downstream ran, and **`OrderCalcMargin` was never
called**.

### NEGATIVE 2 — the zero-height level

Built from **measured** tester prices, and it took two attempts. The first used
the bid (4461.589) as a proxy for the close and missed by 0.276, denying at
Stage 1 instead. The journal gave the actual close — **4461.374** — and the
rebuilt fixture produced the intended case:

```
RC5DENY ENTRY_PROXIMITY_INVALID ...|price=4461.849
        |zone=4461.374..4461.374|distance=0.475|spread=0.260
        |tick=0.001|tolerance=0.260
```

| | |
| --- | --- |
| confirmation distance | **0.000** → Stage 1 **PASS** |
| actual executable ASK | **4461.849** |
| entry distance / tolerance | **0.475** / 0.260 → Stage 2 **DENY** |
| everything downstream | not evaluated |

**This is better evidence than the case was designed to produce.** The
intention was for spread/R to refuse it; instead **entry proximity refused it
first**, because the ask had moved 0.475 away from the level between
confirmation and execution. The locked gate order did exactly what it exists
for — the cheaper, earlier gate refused, and spread/R never ran
(`spreadToR=0.0000`, `R=0.000`).

---

## VERIFICATION LEVELS — what this run does and does not upgrade

| item | level | evidence |
| --- | --- | --- |
| Stage-1 confirmation proximity | **TESTER-VERIFIED** | PASS ×3 and DENY ×1 observed |
| **Stage-2 entry proximity** | **TESTER-VERIFIED** | PASS ×2 against real ASKs, DENY ×1 at 0.475 vs 0.260 |
| entry timing / executable side | **TESTER-VERIFIED** | ASK used for both BUYs; never the bar close |
| distal stop geometry | **TESTER-VERIFIED** | 4450.539 and 4391.069, exactly one tick beyond |
| 2R target | **TESTER-VERIFIED** | 4484.469 and 4414.373, both exact |
| 0.5% risk sizing | **TESTER-VERIFIED** | budget 50.00/49.77, realized 45.24/46.61 |
| volume normalization | **TESTER-VERIFIED** | 0.04 and 0.06, on the 0.01 step |
| **margin gate** | **TESTER-VERIFIED (PASS direction only)** | real `OrderCalcMargin` 35.69 / 52.79; **a DENY was never triggered** |
| order submission path | **TESTER-VERIFIED** | two market buys with SL/TP attached, both filled |
| **spread/R gate** | **VECTOR-VERIFIED only** | it **never fired at runtime** — entry proximity refused first |
| **duplicate guard** | **NOT EXERCISED** | 0 duplicates occurred, but no signal was ever re-presented |
| **one-position-per-symbol** | **NOT EXERCISED** | GOLDEN 1 closed before GOLDEN 2 opened |
| terminal-event exits | **NOT EXERCISED** | both positions closed on SL, not on an analytical event |

The last four rows are the honest limit of this run. Zero duplicates is not
evidence that the duplicate guard works; it is evidence that nothing tried to
duplicate.

## Runtime exceptions

**None.** No errors, no critical entries, no failed calls in the accepted pass.

## Profitability

Final balance 9,907.70 from 10,000.00 — both trades stopped out. **This is not
a performance result and must not be quoted as one.** Two trades is not a
sample, the purpose was execution correctness, and no parameter was tuned.

The one thing the P&L does verify is the risk model: predicted risk
45.24 + 46.61 = **92.30**, realized loss **92.30**.

---

# PHASE 2 — THE BRANCHES PHASE 1 NEVER REACHED

Same terminal, same config, fixtures built from **measured** tester prices at
bar 1788129900 (close 4461.374, ask 4461.849, spread 0.260, tick 0.001, so
tolerance = 0.260). Integrity gate run before the batch: installed EX5
byte-identical.

Parser: `plans=6 denies=2 setups=6 UNPARSED=0`. Orders: **2 market buys, 4
deals**. Runtime exceptions: **0**.

## 1. SPREAD/R DENY — now TESTER-VERIFIED

A zero-height level at **4461.610** was chosen so that both proximity stages
pass and R lands just under the spread.

```
RC5DENY SPREAD_TO_RISK_INVALID ...CURRENT_DAY_LOW~spreadR00001
        |spread=0.260|R=0.240|ratio=1.0833|max=0.2500
```

| stage | observed |
| --- | --- |
| confirmation distance | **0.236** ≤ 0.260 → PASS |
| entry (real ASK) | **4461.849** |
| entry distance | **0.239** ≤ 0.260 → PASS |
| SL | 4461.609 |
| **R** | **0.240** (> 0) |
| **spread / R** | **1.0833** vs a 0.25 limit → **DENY** |

Predicted before the run: R = 0.240, ratio 1.083. Observed identical.

**Short-circuit proved by the data**: `riskMoney=0.00 vol=0.00 margin=0.00
marginFrac=0.0000`, and `xb=1` — the plan reached the post-pricing state and
went no further. Risk sizing and `OrderCalcMargin` did not run.

## 2. DUPLICATE GUARD — now TESTER-VERIFIED

The same semantic identity was presented twice. The first executed; the second:

```
RC5PLAN DENIED|XAUUSDm~15~HAMMER~82c481350728~0~1~1788129900|...
        |SIGNAL_ALREADY_EXECUTED
```

| | |
| --- | --- |
| presentations of that identity | **2** |
| market orders for it | **1** |
| second decision | `SIGNAL_ALREADY_EXECUTED` |

The refusal is **visibly cheap**: `spread=0.000 tol=0.000 confDist=0.000` and
`xb=0`. No quote was read, no geometry computed. That is the locked gate order
showing up in the data rather than in a comment.

## 3. ONE-POSITION-PER-SYMBOL — now TESTER-VERIFIED

A **different** identity (`HAMMER~concurrent001`) with otherwise executable
geometry, presented while GOLDEN 1's position was open:

```
RC5PLAN DENIED|XAUUSDm~15~HAMMER~concurrent001~0~1~1788129900|...
        |SYMBOL_POSITION_ACTIVE
```

Distinct signal id, same broker symbol, denied. Again `spread=0.000`, `xb=0`.
Maximum simultaneous RC5 positions on XAUUSDm across the run: **1**.

## 4. MARGIN DENY — STRUCTURALLY UNREACHABLE, and that is the finding

No harness was built, because the branch cannot occur on this account. Proved
from the measured spec rather than asserted:

```
volume(R)       = 0.005 * E * tick / (R * tickValue)
marginFrac(R)   = volume(R) * price * contract / (leverage * E)
```

The model reproduces the observed GOLDEN 1 row exactly (vol 0.04, marginFrac
0.0039). Then:

| | |
| --- | --- |
| spread gate requires | R ≥ **1.04** |
| margin gate requires | R < **0.2231** |
| **overlap** | **none — a 4.66× gap in R** |
| largest margin fraction the spread gate permits | **4.29%** vs a 20% limit |

`MARGIN_EXPOSURE_INVALID` therefore cannot fire while spread/R passes. It
**becomes reachable below roughly 1:107 leverage**; this account is 1:500. The
conclusion is scoped, not absolute, and is pinned in
`test_margin_deny_is_unreachable_while_the_spread_gate_passes`.

A synthetic harness would have verified a situation this account cannot
produce, so the honest status is **VECTOR-VERIFIED + PROVED UNREACHABLE HERE**,
not "untested".

## 5. TERMINAL EXITS — NOT EXERCISED, and the reason is a real finding

`GENUINE_INVALIDATION_CONFIRMED` and `PoiTerminalReason.INVALIDATED` could not
be exercised because **`RC5OnTerminalEvent` is never called**. The function is
implemented, compiled and vector-verified, but nothing in the EA invokes it:
the fixture transport carries analytical STATE, not lifecycle EVENTS.

Wiring it would mean adding a terminal-event channel to the fixture format —
new production behaviour manufactured solely to claim runtime coverage, which
is exactly what the instruction forbids. So it stays **VECTOR-VERIFIED**, with
the gap named: *the V1 close path has no runtime event source yet.*

The negative controls (`MITIGATED`, `FALSE_INVALIDATION_CONFIRMED`, the three
state migrations) are unreachable for the same reason and keep their vector
verification.

---

# PHASE 2 — THREE-SYMBOL SMOKE

Normal mode, `InpSetupFile` deliberately **empty**. The EA has no detector, so
with no reference state it dispatches nothing: **zero trades is the correct
outcome**, and what the run exercises is initialization, suffix resolution,
broker-spec reading, history access and the bar loop.

| symbol | resolution | history | quality | usable | exceptions |
| --- | --- | --- | --- | --- | --- |
| XAUUSDm | `XAUUSD -> XAUUSDm` | 2025.01.01 → 2026.09.11 | 100% | 1/1 | 0 |
| EURUSDm | `EURUSD -> EURUSDm` | 2025.01.01 → 2026.09.11 | 100% | 1/1 | 0 |
| GBPUSDm | `GBPUSD -> GBPUSDm` | 2025.01.01 → 2026.09.11 | 100% | 1/1 | 0 |

## The EA is not gold-specific — the contracts prove it

| | XAUUSDm | EURUSDm | GBPUSDm |
| --- | --- | --- | --- |
| digits | 3 | **5** | **5** |
| point / tick | 0.001 | **0.00001** | **0.00001** |
| tick value | 0.1 | **1.0** | **1.0** |
| volume min/max/step | 0.01 / 200 / 0.01 | 0.01 / 200 / 0.01 | 0.01 / 200 / 0.01 |
| stops / freeze | 0 / 0 | 0 / 0 | 0 / 0 |
| spread (points) | 260 | **8** | **10** |

Three different contract shapes read correctly at runtime — a hundredfold
difference in tick size and a tenfold one in tick value. Nothing in the EA
assumed gold.

**What the FX runs do NOT establish:** no FX order was placed, so volume
normalization, margin and the order path remain verified on gold only. Building
FX fixtures would need Layer-A state for those symbols, and the available
capture is XAUUSD.

## Performance

Observational only. The Phase-2 batch ended at 9,907.70 from 10,000.00 — the
same two stopped-out goldens as Phase 1, reproduced exactly. **Not a
performance result**: the trades are test cases, the sample is two, and no
parameter was tuned.
