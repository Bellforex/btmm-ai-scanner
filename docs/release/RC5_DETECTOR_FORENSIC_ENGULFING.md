# THE ENGULFING QUESTION -- ANSWERED NUMERICALLY

Same run configuration as the pressure-wick forensic: `OANDA:XAUUSD` H4, 795
bars (2026-03-23 -> 2026-09-24), `rc5_structural_origin = False` (production
default), all other inputs default.

---

## 1. RC5 ENGULFING IS NOT THE TEXTBOOK PATTERN

From `poi/engulfing.py`. A **bearish** engulfing needs:

| predicate | requirement |
| --- | --- |
| size | `total_range(engulfing) / total_range(engulfed)` >= **2.0** |
| neither candle is a Doji | `body_efficiency > 0.10` for **both** |
| direction | engulfed **bullish**, engulfing **bearish** |
| zone | **the ENGULFED candle's high/low** |
| STRONG tier | ratio >= **3.0** |

Two things are worth stating plainly because they surprise people:

* **there is no body-engulfment test at all.** The rule is a *range-size* ratio
  plus a direction flip. A candle whose body does not cover the prior body can
  still qualify;
* **the zone is the engulfed candle, not the engulfing one.**

Anyone auditing this against a textbook definition will reach the wrong verdict.

## 2. THE TWO CANDIDATES

18 bearish engulfings were detected. The relevant pair:

| | displayed | the stronger one |
| --- | --- | --- |
| engulfed bar | 2026-09-10 01:00 | 2026-09-04 05:00 |
| zone top / bottom | 4421.170 / 4400.185 | 4490.895 / 4460.155 |
| **tier** | **STANDARD** | **STRONG** |
| **range ratio** | **2.02** | **3.36** |
| engulfed body efficiency | 0.363 | 0.136 |
| engulfing body efficiency | 0.322 | 0.816 |

**The displayed one passes by 0.02.** Threshold 2.0, actual 2.02 -- the
narrowest margin of any bearish engulfing in the whole six-month capture. The
author's instinct that it looks minor is quantitatively correct.

### Verdicts

* displayed engulfing: **CORRECT TRUE POSITIVE.** Marginal, but it clears the
  frozen threshold. Rejecting it would require changing the threshold, which is
  a doctrine change, not a bug fix;
* stronger engulfing (3.36, STRONG): **NOT a false negative.** Detected,
  tiered, and lifecycle-valid.

## 3. SAME ROOT CAUSE AS THE PRESSURE WICK

Current price on this capture is ~4288.

| zone | nearest edge | distance |
| --- | --- | --- |
| displayed (4421.170 / 4400.185) | 4400.185 | **~112** |
| stronger (4490.895 / 4460.155) | 4460.155 | ~172 |

Selection is `bandDistance(close, top, bottom)` ranked by `nearestFirst`. The
weaker zone is nearer, so it wins the visible quota. **The strength tier is
never consulted.**

This is the second independent confirmation of the same mechanism, on a
different detector family. That makes it a characteristic of the display layer
rather than a coincidence of one formation.

## 4. THE DECISION THIS FORCES

The scanner currently answers *"which valid zones is price closest to?"*. The
author is asking it to answer *"which valid zones are the strongest?"* -- and
those are different questions that can disagree, as both forensics show.

Options, unchanged from the pressure-wick write-up:

1. **keep nearest-first** -- proximity is what price can actually reach next;
2. **tier-then-distance** -- STRONG always beats STANDARD inside the quota;
3. **distance, tie-broken by tier** -- smallest possible change.

`strength_tier` is already computed and transported for both families, so no
new metric is needed. Any of these needs a CE10117 measurement against the
**45** remaining CORE tokens before it is promised.

**Nothing was changed.** Both detectors are behaving exactly as specified.
