# RC5 — EVENT DEMONSTRATION (10–15 minutes)

Deterministic. **Nothing here depends on a live trade appearing during the
talk** — every number is already captured and reproducible.

---

## 1. The scanner on a chart (2 min)

Open TradingView, CORE + VIEW attached.

Point at: HH/HL/LH/LL on confirmed swings, a BOS or CHOCH drawn at the candle
that broke the level, and the POI zones.

**Say:** the scanner marks where the market made a *decision*. It draws zones
on confirmed bars only — nothing appears before the engine could causally have
known it.

## 2. The problem it solves (2 min)

**Say:** a Base with a candle pattern inside it used to show up as the candle
pattern — the small thing won, the structure that actually described the
decision went unranked.

Show formation ownership on the golden M15 formation:

| record | standing |
| --- | --- |
| `BASE_DROP` | **PRIMARY** |
| pressure wick | subordinate — contained |
| doji | subordinate — contained |
| evening star | subordinate — exact co-extension |

**Say:** ownership changes *standing*, never identity. Nothing is deleted.

## 3. Architecture, briefly (1 min)

```
LAYER A — analysis            LAYER B — execution
Python (the reference)        MQL5 EA
Pine CORE / VIEW              Execution Doctrine V1
produces STATE                consumes STATE, produces ORDERS
```

**Say:** the scanner never places an order, and the EA never re-decides the
analysis. That separation is why one can be audited without the other.

## 4. The EA, and its licence (2 min)

Show the Experts log on attach:

```
RC5LIC RC5-ABCDE-***-PQRST LICENSE_VALID | newEntries=ALLOWED
```

**Say three things:**
- the key is masked in every log — it is never printed in full;
- a licence binds to MT5 **login and broker server**;
- **if a licence lapses mid-trade, the trade is not abandoned** — new entries
  stop, and the open position keeps its stop, its target and its exits. That is
  a deliberate choice: an unmanaged live position would be worse than piracy.

## 5. Strategy Tester — the goldens (3 min)

Show the captured journal.

| | GOLDEN 1 | GOLDEN 2 |
| --- | --- | --- |
| entry (real ask) | 4461.849 | 4398.837 |
| stop | 4450.539 | 4391.069 |
| target | 4484.469 | 4414.373 |
| R | 11.310 | 7.768 |
| spread / R | 0.0230 | 0.0335 |
| volume | 0.04 | 0.06 |
| margin (broker) | 35.69 | 52.79 |

**Say:** the entry is the *actual ask* on the next tradable tick, never the bar
close. The stop is exactly one tick beyond the zone boundary — and that
boundary comes from the analytical engine, not from a trading preference.

## 6. The safety demonstrations (3 min)

This is the strongest part of the talk. **Show the refusals.**

**A stale zone.** A valid POI at 308–312 while gold traded near 4,400.

```
RC5DENY CONFIRMATION_PROXIMITY_INVALID |distance=4145.936|tolerance=0.260
```

**Say:** it passed the risk check, the spread check *and* the margin check. The
proximity gate is what refuses it. We found this by running it, not by
imagining it.

**A micro-stop.** A zone so tight the spread swallows the stop.

```
RC5DENY SPREAD_TO_RISK_INVALID |spread=0.260|R=0.240|ratio=1.0833|max=0.2500
```

**Say:** the risk budget was satisfied — 0.5% is 0.5%. But the spread was over
four times the stop, so the trade was lost to cost before it began. The budget
does not describe execution *quality*; this gate does.

## 7. Risk sizing, against reality (1 min)

**Say:** predicted aggregate risk across the two trades was **92.30**. The
realized loss was **92.30**.

Then immediately: **both trades lost, and that is not a result.** Two trades is
not a sample, they are test fixtures, and nothing was tuned. What it verifies is
that the risk model does what it says.

## 8. How customers get access (1 min)

**Scanner:** send your exact TradingView username → added to the invite-only
script with an expiry → **Indicators → Invite-only scripts**.

**EA:** licence key bound to your MT5 login and broker server, with an expiry
we control centrally.

**Say:** scanner access is per TradingView account and cannot be shared — there
is no link that grants someone else access.

---

## If asked "does it make money?"

Answer plainly: **we are not making that claim, and we have not measured it.**
What has been verified is that the analysis is deterministic, that the
execution layer does exactly what it says, and that it refuses trades it should
refuse. Profitability is a separate question requiring a real sample, and the
work to answer it honestly has not been done.

That answer is better for the business than a number you cannot defend.

## Do NOT say

- "uncrackable" — the correct claim is commercial-grade controlled access
- "guaranteed", "risk-free", any win rate
- that live trading has been validated — it has not
