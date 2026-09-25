# THE DISPUTED ZONES ARE UNTOUCHED -- MEASURED

**Run configuration:** `OANDA:XAUUSD` H4, 795 bars, `rc5_structural_origin =
False` (production default), all other inputs default, last close 4271.600.

---

## 1. FIRST, A CORRECTION TO THE PREMISE -- WITH EVIDENCE

The three bearish zones visible on the live chart, by semantic record:

| type | zone top / bottom | tier | **taps** | fresh_active | freshness | lifecycle |
| --- | --- | --- | --- | --- | --- | --- |
| BEARISH_ENGULFING | 4490.895 / 4460.155 | STRONG | **0** | True | **FRESH** | NO_BREACH |
| BEARISH_PRESSURE_WICK | 4435.255 / 4422.495 | STANDARD | **0** | True | **FRESH** | NO_BREACH |
| BEARISH_PRESSURE_WICK | 4435.045 / 4408.725 | STRONG | **0** | True | **FRESH** | NO_BREACH |

**`tap_count = 0` on all three.** Price has never traded into any of them since
they formed. They are not mitigated, not re-tested, not consumed and not
invalidated -- they are maximally fresh, untested supply sitting above price.

So the concern that they are "no longer useful as fresh potential reaction
zones" does not hold **for these particular records**. Whatever else is worth
changing, these three are the strongest possible case for being displayed.

## 2. AND THE RENDERER IS ALREADY HIDING THE CONSUMED ONES

From the same run, bearish zones that are **not** on the chart:

```
4708.175 / 4686.650   7 taps   GENUINE_INVALIDATION_CONFIRMED
4635.940 / 4619.915   8 taps   GENUINE_INVALIDATION_CONFIRMED
4535.760 / 4526.855   2 taps   GENUINE_INVALIDATION_CONFIRMED
4513.080 / 4489.095   7 taps   GENUINE_INVALIDATION_CONFIRMED
4452.325 / 4442.035   9 taps   GENUINE_INVALIDATION_CONFIRMED
```

The 4452 wick sits *between* two displayed zones and is correctly absent. The
validity gate is working.

## 3. RC5 DOES MODEL FRESHNESS -- AND DELIBERATELY STOPPED DISPLAYING ON IT

The state exists and is richer than binary:

| field | meaning |
| --- | --- |
| `poiFreshActive` / `fresh_active` | untouched since availability |
| `freshness_status` | FRESH / INTERACTED |
| `poiTapCount` / `tap_count` | **maximal touching runs** -- observed 0 to 17 |
| `poiFirstTouchT` | first post-availability contact |
| `poi_lifecycle_status` | NO_BREACH, RECLAIM_*, FALSE_INVALIDATION_*, GENUINE_INVALIDATION_CONFIRMED |

The renderer used to gate on `poiFreshActive` and was **deliberately changed**.
CORE's own comment (~6936) records why:

> "RC3/RC4 filtered on `poiFreshActive`, so a zone vanished the moment price
> first touched it. That is wrong: a POI is mitigated, re-tested and traded
> again, and a far-side break that was reclaimed is the false-break case **the
> author explicitly asked to keep**. Measured on the frozen captures... M5
> keeps 6 mitigated + 14 re-mitigated + 8 reclaimed zones, H4 keeps 10 + 16 +
> 1, every one of which RC3/RC4 hid on first contact."

`poiFreshActive` goes false on the **first touch**. It is exactly the
"first touch = automatic death" rule the current brief rules out, which is why
it cannot be the display gate.

## 4. THE CURRENT BEHAVIOUR ALREADY MATCHES THE STATED CONTRACT

The requirement, as written:

> display if fresh/untouched, **or** mitigated but genuinely still holding;
> do not display if genuinely failed or consumed.

Mapped onto what the engine actually produces:

| state | example from this run | displayed today | contract wants |
| --- | --- | --- | --- |
| FRESH, 0 taps | the three disputed zones | **yes** | yes |
| INTERACTED, taps > 0, NO_BREACH | 4760.990 / 4744.555, 4 taps | **yes** | yes (mitigated but holding) |
| GENUINE_INVALIDATION_CONFIRMED | 4452.325 / 4442.035, 9 taps | **no** | no |

**All three rows already behave as the contract asks.** No gap is demonstrated
by this data.

## 5. THE ONE GENUINELY UNDEFINED CATEGORY

"**Consumed but not invalidated**" has no definition anywhere in the project.
A zone with 9 taps that never broke its far side is, under current doctrine,
*mitigated and still holding* -- and the brief explicitly says such a zone
should remain.

Distinguishing "tested four times and still holding" from "exhausted" would
need a new rule, and the brief equally forbids inventing one ("no arbitrary
N-touch rule", "freshness must come from the approved doctrine"). Those two
constraints cannot both be satisfied without an author decision that supplies
the missing rule.

`tap_count` is the obvious raw material -- it already counts maximal touching
runs, it is already transported, and it ranges 0..17 on this capture. But what
threshold, if any, means "exhausted" is a doctrine question, not an
engineering one.

## 6. WHAT I DID NOT DO

No code change, no new gate, no threshold. The evidence does not support one:
the zones in question are untouched, and the mechanism that would have hidden
them is the very rule that was removed at the author's own request.

**The scanner is not frozen.** This finding is offered so the freeze decision
rests on measurements rather than on an assumption about those three boxes.
