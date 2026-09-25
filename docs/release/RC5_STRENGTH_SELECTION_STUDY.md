# STRENGTH-FIRST SELECTION -- MEASURED, AND IT DOES NOT FIT

**Run configuration:** `OANDA:XAUUSD` H4, 795 bars (2026-03-23 -> 2026-09-24),
`rc5_structural_origin = False` (production default), quota
`p7zMaxVisibleZones = 8`, last close 4271.600.

**Outcome: NOT IMPLEMENTED.** It costs **+46 tokens** and CORE compiles at
**100,257** against a hard limit of **100,256**. One token over.

---

## 1. COMPETITION SCOPE, ESTABLISHED FIRST

The quota is **global**: every POI that passes eligibility competes in one
pool. Not per direction, not per family, not per timeframe.

Eligibility, in order (CORE ~6977):

1. `f_rc5Validity(pI) == C_RC5_VALID` (lifecycle);
2. `not map.contains(rc5Subordinate, pI)` (P4);
3. `array.get(p7zTypeOn, ty - 1)` (type toggle);
4. FVG dominance;
5. then a same-direction overlap-cluster winner;
6. then `nearestFirst(p7zDist, ...)`.

Any reordering belongs at step 6 only. Steps 1--4 must keep precedence, so
strength can never resurrect an invalidated, subordinate or disabled record.

## 2. THE TIER VALUES MAKE THE LITERAL INSTRUCTION HARMFUL

```
C_POI_TIER_NA = 0, C_POI_TIER_STANDARD = 1, C_POI_TIER_STRONG = 2
```

"Tier descending" therefore ranks **NA last** -- and **FVGs and reference zones
carry NA**. They carry it because strength is *not applicable* to a gap or a
level, not because they are weak. Treating NA as "weakest" is a category error.

Measured on the real capture, quota 8:

| policy | mean distance of selected | slots changed | FVGs in top 8 |
| --- | --- | --- | --- |
| current nearest-first | **59.90** | -- | 4 |
| **A** STRONG first, everything else by distance | **98.54** | 4 | 3 |
| **B** strict tier descending | **127.58** | 5 | **0** |

**B removes every FVG from the chart.** It is rejected on evidence, not taste.

A is the faithful reading of the intent: promote records whose strength was
actually *measured and found high*, and leave everything else on proximity.

## 3. WHAT A WOULD HAVE DONE TO THE AUTHOR'S TWO CASES

Both forensic cases resolve exactly as intended:

| | under A |
| --- | --- |
| BEARISH_PRESSURE_WICK **STRONG** 4435.045/4408.725 | **promoted into the visible 8** |
| BEARISH_ENGULFING **STRONG** 4490.895/4460.155 | **promoted into the visible 8** |
| BEARISH_ENGULFING STANDARD 4421.170/4400.185 (ratio 2.02) | displaced |

All four STRONG zones on this capture enter the visible set.

## 4. THE OVER-PROMOTION COST, MEASURED

A is not free. The four promoted STRONG zones sit at distances **132, 137, 189
and 237**, displacing zones at **92, 94, 95 and 105**.

So A trades four near-ish zones for four further ones and raises mean distance
by **64%** (59.90 -> 98.54). With only 4 STRONG records against a quota of 8,
the split is half strength-ranked and half proximity-ranked, which is a
defensible balance -- but it is a real change in what the chart is answering.

## 5. THE IMPLEMENTATION, AND WHY IT WAS REVERTED

`nearestFirst` sorts ascending and its third argument is an **exclusion** mask,
not a priority one, so it cannot carry precedence. The cheapest correct
mechanism is to bias the distance:

```pine
array.push(p7zDist, (array.get(poiTier, pZ) == C_POI_TIER_STRONG ? 0.0 : 1000000000.0)
                    + bahui.bandDistance(close, poiZoneTop[pZ], poiZoneBottom[pZ]))
```

No new comparator, no new array, BAH untouched.

**Measured cost: +46 tokens.** CORE goes 100,211 -> **100,257**, and the
compiler refuses: `outputILLength 100257`, limit `100256`.

Reverted. CORE is back at `e08051c2e3908ba6`, 100,211, headroom 45.

## 6. WHAT THE AUTHOR CAN DECIDE

**One token.** That is the entire gap.

1. **Accept nearest-first** -- no change, and the forensics stand as an
   explanation of why a marginal zone can outrank a strong one;
2. **Recover tokens elsewhere, then re-apply.** The obvious candidate is the
   **dead `dspMs` input in CORE** (declared at line 64, referenced nowhere else
   in CORE since structure moved to VIEW). Removing it would free well over one
   token -- **but it shifts every `in_N` index after it**, which silently
   remaps saved settings on existing chart instances, including the author's.
   That is a worse defect than the one being fixed, so it must not be done
   casually;
3. **Find a genuinely free token elsewhere** in CORE and re-run this exact
   measurement.

I did not choose between these. Option 2's side effect is the kind of thing
that should be decided deliberately, not absorbed into a display tweak.

---

# 7. CORRECTION -- THE SCANNER ALREADY DOES THIS, AND THE CHANGE IS UNNECESSARY

Before recovering tokens for the selector, I read the code path it would have
modified. **Strength already leads display selection**, in the exact place the
author's two examples live.

## `f_rc5DisplayBetter` -- an existing tier-first comparator

CORE ~2907, unchanged and already shipped:

```pine
f_rc5DisplayBetter(int a, int b) =>
    ...
    ta2 != tb2 ? ta2 > tb2 : sa != sb ? sa > sb : va != vb ? va > vb : a > b
```

Tier first, then P5 score, then availability, then index. Its own comment
records that the model I was about to build was already tried and rejected:

> "The tier constants are ordered NA 0 < STANDARD 1 < STRONG 2, so they compare
> directly; that is both more correct than **the previous STRONG-or-not test,
> which treated STANDARD and NA as equal**, and cheaper."

It runs as the **same-direction overlap-cluster winner** rule, one stage before
the quota.

## The forensic cases were already resolved

Simulating the real pipeline order -- eligibility, then cluster winner, then
nearest-first quota -- on the same XAUUSD H4 capture:

| eligible bearish pressure wick | tier | distance | survives clustering |
| --- | --- | --- | --- |
| 4760.990 / 4744.555 | STANDARD | 472.95 | no |
| 4727.030 / 4719.905 | STANDARD | 448.31 | no |
| 4369.560 / 4363.610 | STANDARD | 92.01 | yes |
| **4435.255 / 4422.495** | **STANDARD** | 150.90 | **no -- beaten by the STRONG one** |
| 4383.385 / 4366.900 | STANDARD | 95.30 | no |
| **4435.045 / 4408.725** | **STRONG** | 137.12 | **yes** |

Clustering reduces 45 eligible POIs to **12**, so the quota of 8 barely binds.
The final visible set is:

```
BUY_FAIR_VALUE_GAP     NA        d=  0.00
BULLISH_PRESSURE_WICK  STANDARD  d=  9.50
BUY_FAIR_VALUE_GAP     NA        d= 34.60
SELL_FAIR_VALUE_GAP    NA        d= 48.97
BEARISH_PRESSURE_WICK  STANDARD  d= 92.01
BEARISH_PRESSURE_WICK  STRONG    d=137.12   <- the author's stronger wick
BEARISH_ENGULFING      STRONG    d=188.56   <- the author's stronger engulfing
BULLISH_ENGULFING      STRONG    d=237.35
```

**Both stronger candidates are already displayed. The marginal 2.02-ratio
engulfing is not in the visible set at all.**

## What this retracts

Sections 1--6, and the pressure-wick and engulfing forensics, concluded that
the root cause was "display selection uses distance only". That is **true of
the quota stage and false of the pipeline as a whole**. The cluster stage --
which is where two overlapping wicks compete -- has led on tier all along.

My identification of the *displayed* box as the STANDARD record came from
comparing screenshot pixel bounds, which the directive explicitly warned is not
identity. The simulation over real OHLC through the real pipeline order
contradicts it.

## Consequence

**The +46-token selector is not needed and should not be pursued.** It would
spend the entire CORE headroom, plus borrowed tokens, to change the quota stage
for a case the cluster stage already handles correctly.

No token recovery is required. CORE stays at **100,211**, headroom **45**.

## The honest residual

The quota stage *is* still distance-only, so a STRONG zone that shares no price
overlap with anything could still be displaced by a nearer non-overlapping
STANDARD one. On this capture that does not occur -- clustering leaves 12
survivors for 8 slots and all three STRONG records make the cut.

Whether it matters elsewhere is a question for the 3x3 matrix, not for a code
change now.

## Method note

One caveat on the simulation: the Python port ranks cluster winners by
`(tier, availability)` while Pine uses `(tier, score, availability, index)`.
Tier leads in both and differs in the decisive comparison, so the outcome is
unaffected -- but the ports are not identical and a tie on tier could diverge.
