# THE PRESSURE-WICK QUESTION -- ANSWERED NUMERICALLY

**Run configuration**, recorded because a previous comparison was invalidated by
not recording it:

| | |
| --- | --- |
| symbol / timeframe | `OANDA:XAUUSD` H4 |
| capture | 795 bars, 2026-03-23 -> 2026-09-24 |
| `rc5_structural_origin` | **False** (production default) |
| all other inputs | defaults |

---

## 1. THE ACTUAL RULE -- NOT A TEXTBOOK ONE

From `poi/pressure_wicks.py`. A **bearish** pressure wick needs ALL four:

| predicate | threshold |
| --- | --- |
| `upper_wick / total_range` | >= **0.40** |
| `body_efficiency` | >= **0.25** |
| dominance: `upper_wick >= k * lower_wick` (or `lower_wick == 0`) | k = **2.0** |
| `bearish_close_position` | >= **0.60** |

And the **zone is the upper wick only**: `top = high`, `bottom = max(open, close)`.
Not the whole candle.

## 2. THE PROJECT ALREADY HAS A STRENGTH CONCEPT

`PoiStrengthTier` is **STRONG** when all five of these also hold:

| predicate | strong threshold |
| --- | --- |
| wick share | >= 0.50 |
| body efficiency | >= 0.30 |
| dominance | >= **3.0x** |
| close position | >= 0.70 |
| range context (candle range / 20-bar median) | >= **1.25** |

So "how strong is this wick" is **already measured and stored**. Nothing needs
inventing.

## 3. THE TWO CANDIDATES

30 bearish pressure wicks were detected on this capture. The two that matter
sit almost exactly on top of each other:

| | displayed | the stronger one |
| --- | --- | --- |
| time | 2026-09-06 21:00 | 2026-09-10 05:00 |
| zone top / bottom | 4435.255 / 4422.495 | 4435.045 / 4408.725 |
| **tier** | **STANDARD** | **STRONG** |
| upper-wick share | 0.507 | **0.620** |
| body efficiency | 0.386 | 0.322 |
| dominance | 4.76x | **10.68x** |
| bearish close position | 0.893 | **0.942** |
| range context | 0.838 | **1.488** |

Both **pass every standard predicate**. Both are **live** (`NO_BREACH`).

### Verdicts

* displayed wick (4435.255/4422.495): **CORRECT TRUE POSITIVE.** It is not a
  weak accident -- it clears every threshold, with a 4.76x dominance and a
  0.893 close position. It simply is not the *strongest* one available;
* the stronger wick (4435.045/4408.725): **NOT a false negative.** It is
  detected, tiered STRONG, and lifecycle-valid. It is not missing from the
  engine at all.

**So the detector is not the problem.** Neither a false positive nor a false
negative is present.

## 4. THE REAL FINDING -- DISPLAY RANKING IGNORES STRENGTH

The zone renderer selects which POIs to draw like this:

```
array.push(p7zDist, bahui.bandDistance(close, poiZoneTop[pZ], poiZoneBottom[pZ]))
p7zSelected := bahui.nearestFirst(p7zDist, p7zVisibleIdx, ..., p7zShown)
```

`p7zDist` is **distance from current price, and nothing else**. `nearestFirst`
ranks on it. The strength tier is never consulted -- `poiTier` appears once in
the whole P7-Z block and not in the selection path.

> **A STANDARD wick nearer price outranks a STRONG wick further away, always.**

That is exactly the author's complaint, stated mechanically: *minor zones
visible, stronger zones not*. It is a **DISPLAY-RANKING** characteristic, not a
detector defect.

It is also why these two look like one box on the chart: their zones overlap
(4422--4435 and 4408--4435), so whichever is drawn covers the other.

## 5. WHAT I DID NOT DO

I did **not** change the ranking. The current rule -- nearest to price -- is a
defensible choice for a trading scanner, and the RC1 corrective that
established it was a deliberate fix for a real defect (the renderer had been
drawing the *oldest* records off-screen).

Changing it to rank by tier, or to break ties by tier, is an **author
decision** with three options:

1. **keep nearest-first** -- what matters is what price can reach next;
2. **tier-then-distance** -- STRONG wicks outrank STANDARD ones within the
   visible quota, so the strongest nearby zone always survives the cut;
3. **distance, tie-broken by tier** -- only reorders genuine ties, the smallest
   possible change.

Option 2 or 3 would need a token measurement against the 45 remaining CORE
headroom before being promised. Option 3 is almost certainly the cheaper.

No quality metric needs inventing for any of them -- `strength_tier` is already
transported.
