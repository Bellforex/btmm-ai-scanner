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
