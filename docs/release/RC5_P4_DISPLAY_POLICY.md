# P4 SUBORDINATES ARE INVISIBLE -- AND THAT IS AN AUTHOR DECISION

Not a defect report. The behaviour is deliberate and self-consistent; it just
conflicts with a second stated requirement, so someone has to choose.

**Nothing was changed. This is a decision pack.**

---

## 1. THE TWO STATEMENTS THAT COLLIDE

The Python doctrine (`poi/formation_ownership.py`) is explicit that ownership
is a *standing* change and that the record survives:

> "It changes STANDING, never IDENTITY. A Doji subordinate to a Drop-Base-Drop
> is still `PoiType.DOJI` with its own geometry and its own transport code;
> nothing is relabelled, nothing is deleted, and **every subordinate record
> stays available** for forensics, parity and historical evidence."

The same file lists the pipeline with **display arbitration as a separate,
later stage** than formation ownership.

But the Pine zone renderer collapses the two. Display eligibility reads:

```
f_rc5Validity(pI) == C_RC5_VALID
  and not map.contains(rc5Subordinate, pI)      <-- here
  and array.get(p7zTypeOn, ty - 1)
  and not (isFvg and ...)
```

So a subordinate is **removed from the chart entirely**, and its type toggle
cannot bring it back. The toggle is step 3; the subordinate gate is step 2.

Against the author's requirement that every implemented POI can manifest and be
inspected through its type switch, that is a genuine conflict.

## 2. HOW MUCH IS ACTUALLY HIDDEN -- MEASURED

Real EURUSD M15 golden window, full scan, ownership and origin authority
applied:

| | |
| --- | --- |
| total POI observations | **94** |
| authoritative | **91** |
| non-authoritative (hidden from the zone renderer) | **3** -- **3.2%** |

Broken down, the entire hidden set is three records:

| type | total detected | hidden |
| --- | --- | --- |
| BEARISH_PRESSURE_WICK | 15 | 1 |
| EVENING_STAR | 6 | 1 |
| BULLISH_ENGULFING | 4 | 1 |

**No type is hidden wholesale.** Every family that was detected still has
visible members; ownership removed single instances, which is exactly what a
containment/co-extension rule should do.

That matters for the decision: this is not "half the library is invisible". It
is three records in ninety-four, and they are the ones a Base already explains.

## 3. THE SAME RUN ANSWERS "CAN EVERY TYPE MANIFEST?"

Twenty-five distinct types appeared in that single window, including the whole
liquidity family:

```
SELL_FAIR_VALUE_GAP 20   BEARISH_PRESSURE_WICK 15   SHOOTING_STAR 9
EVENING_STAR 6           BUY_FAIR_VALUE_GAP 5       BASE_DROP 4
BULLISH_PRESSURE_WICK 4  BULLISH_ENGULFING 4        RESISTANCE_ZONE 4
SUPPORT_ZONE 3           MORNING_STAR 2             HAMMER 2
BEARISH_ENGULFING 2      EQUAL_HIGHS_LIQUIDITY 2    EQUAL_LOWS_LIQUIDITY 2
PREVIOUS_WEEK_HIGH/LOW, PREVIOUS_DAY_HIGH/LOW,
CURRENT_DAY_HIGH/LOW, CURRENT_WEEK_HIGH/LOW,
CURRENT_MONTH_HIGH/LOW                        1 each
```

The liquidity/reference types (codes 19--32) **are detected and registered**.
They do not draw as POI zones because they are not POI-zone types -- they are
the `dspLiq` layer. Detector health and renderer routing are different
questions, and this run separates them.

## 4. THE TWO OPTIONS

### OPTION 1 -- keep it (subordinates hidden)

* the chart shows one zone per market decision, which is the point of ownership;
* no CORE tokens spent; headroom stays at 45;
* the author cannot inspect a subordinate on the chart, only in parity output.

### OPTION 2 -- subordinates drawable when their type switch is on, marked as subordinate

* honours "every implemented POI can manifest and be inspected";
* requires removing `not map.contains(rc5Subordinate, pI)` from the display
  gate and adding a visual distinction so a subordinate never *looks*
  authoritative -- lighter fill, or a dotted border, or a prefixed label;
* **token cost is the blocker.** Headroom is 45 after the S/R fix. Removing the
  gate is roughly free; the visual distinction is not. A third border style plus
  a conditional colour is the kind of change that has cost ~19 tokens elsewhere
  in this same renderer, so it is plausible but tight, and it must be measured
  before it is promised;
* analytical semantics would be **unchanged** either way: P5/P8 already consume
  `suppressed_record_ids`, not the renderer.

### What is NOT on the table

Changing what ownership *means*. A subordinate must stay non-authoritative
analytically in both options -- this is purely about whether it can be drawn.

## 5. RECOMMENDATION

**Option 1 for the event**, Option 2 afterwards if the author wants it.

Not because Option 2 is wrong, but because the measured exposure is three
records in ninety-four, the event is close, and Option 2 spends scarce CORE
headroom on a visual distinction that has to be designed and token-measured
rather than guessed. Shipping a cluttered or mis-signalled hierarchy would cost
more on stage than three invisible subordinates.

If the author wants Option 2, the honest sequence is: measure the border/colour
variant first, confirm it fits in 45 tokens, and only then remove the gate.
