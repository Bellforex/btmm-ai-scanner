# RC5 — EXPECTED GOLDEN RECORDS

The expected-vs-observed template. Every field that can be known offline is
filled in; every field that cannot is `PENDING_TESTER`.

**Rule for filling these in:** replace a `PENDING_TESTER` **only** with a value
actually observed in tester output. The confirmation close is NOT an entry
price — it is a hindsight price the execution layer could never have been
filled at, and substituting it converts a pending value into a fabricated one.

---

## GOLDEN 1 — HAMMER, 2026-08-30 22:45:00 UTC

### Layer A — frozen, produced by the engine

| field | expected | observed |
| --- | --- | --- |
| symbol | `XAUUSD` → resolves to `XAUUSDm` | |
| timeframe | 15 | |
| bar time (epoch) | 1788129900 | |
| POI identity | `HAMMER~82c481350728` | |
| POI type | HAMMER | |
| direction | BULLISH (+1) | |
| zone top | 4467.06 | |
| zone bottom | 4450.54 | |
| authoritative | true | |
| validity | VALID (0) | |
| P5 permission | true (`BUY_BIAS`) | |
| lifecycle | 7 `LIQUIDITY_VALIDATED` | |

Supporting analytical evidence (not transported; reproducible from the engine):
`btmm_valid` true, alignment ALIGNED, regime TREND, momentum BULLISH 69,
liquidity 70.

### Layer B — Execution Doctrine V1

| field | expected | observed |
| --- | --- | --- |
| eligibility | ELIGIBLE | |
| duplicate guard | CLEAR | |
| concurrency guard | CLEAR | |
| confirmation close | **4461.29** | |
| confirmation distance | **0** (inside the zone) | |
| Stage-1 proximity | **PASS** | |
| executable side | **ASK** | |
| entry | `ENTRY_PRICE_PENDING_TESTER` | |
| entry distance | `PENDING_TESTER` | |
| Stage-2 proximity | `PENDING_TESTER` | |
| distal | **4450.54** | |
| stop (SL) | **4450.53** | |
| R | `PENDING_TESTER` (`entry − 4450.53`) | |
| spread | `PENDING_TESTER` | |
| spread / R | `PENDING_TESTER`, must be ≤ 0.25 | |
| risk % | 0.5 | |
| risk money | `PENDING_TESTER` (0.5% of tester equity) | |
| volume | `PENDING_TESTER` | |
| required margin | `PENDING_TESTER` (`OrderCalcMargin`) | |
| margin fraction | `PENDING_TESTER`, must be ≤ 0.20 | |
| TP | `PENDING_TESTER` (`entry + 2R`) | |
| signal id | `XAUUSD~15~HAMMER~82c481350728~0~1~1788129900` | |
| executions | exactly 1 | |

### Offline trace, pinned

```
ANALYTICAL_ELIGIBLE → LIQUIDITY_VALIDATED → DUPLICATE_CLEAR
→ CONCURRENCY_CLEAR → CONFIRMATION_PROXIMITY_PASS
→ ENTRY_PRICE_PENDING_TESTER          ... and STOP
```

Final offline status: **PENDING_TESTER**, never `EXECUTION_READY`.

---

## GOLDEN 2 — MORNING_STAR, 2026-09-08 14:45:00 UTC

### Layer A

| field | expected | observed |
| --- | --- | --- |
| symbol | `XAUUSD` → `XAUUSDm` | |
| timeframe | 15 | |
| bar time (epoch) | 1788878700 | |
| POI identity | `MORNING_STAR~cf5314af21ab` | |
| POI type | MORNING_STAR | |
| direction | BULLISH (+1) | |
| zone top | 4399.54 | |
| zone bottom | 4391.07 | |
| authoritative | true | |
| validity | VALID (0) | |
| P5 permission | true (`BUY_BIAS`) | |
| lifecycle | 7 `LIQUIDITY_VALIDATED` | |

Evidence: `btmm_valid` true, ALIGNED, TREND, momentum **STRONG_BULLISH 72**,
liquidity 70.

### Layer B

| field | expected | observed |
| --- | --- | --- |
| confirmation close | **4398.65** | |
| confirmation distance | **0** (inside) | |
| Stage-1 proximity | **PASS** | |
| executable side | **ASK** | |
| entry / entry distance / Stage-2 | `PENDING_TESTER` | |
| distal | **4391.07** | |
| stop (SL) | **4391.06** | |
| R / spread / spread-R / volume / margin / TP | `PENDING_TESTER` | |
| risk % | 0.5 | |
| signal id | `XAUUSD~15~MORNING_STAR~cf5314af21ab~1~1~1788878700` | |
| executions | exactly 1 | |

Same pinned offline trace, same final status **PENDING_TESTER**.

---

## NEGATIVE — stale HAMMER 308.75–312.85

| field | expected | observed |
| --- | --- | --- |
| confirmation close | ~4400.00 | |
| confirmation distance | **4087.15** | |
| tolerance | **0.20** | |
| Stage-1 proximity | **DENY** | |
| deny reason | `CONFIRMATION_PROXIMITY_INVALID` | |
| R / volume / margin | **never computed** | |
| `OrderCalcMargin` calls | **0** | |
| orders | **0** | |

```
ANALYTICAL_ELIGIBLE → LIQUIDITY_VALIDATED → DUPLICATE_CLEAR
→ CONCURRENCY_CLEAR → CONFIRMATION_PROXIMITY_INVALID   ... and STOP
```

---

## What "PASS" would mean, and what it would not

A completed golden proves the execution layer behaves correctly **on one
setup, on one broker, in the Strategy Tester**. It is not a profitability
claim, not a live-trading claim, and not evidence about any other setup.

Until a run happens, Stage-2 proximity has **never been observed against a real
quote**. Its logic is pinned by vectors and its MQL5 form compiles; that is
`VECTOR-VERIFIED`, not `RUNTIME-VERIFIED`.
