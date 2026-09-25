# WHEN DOES A ZONE DIE? THE FROZEN RULE, RECOVERED

Written before changing anything, because the obvious reading of the annotated
screenshots would lead to a change that breaks the doctrine.

---

## 1. THE EXACT INVALIDATION RULE

From `poi/lifecycle.py`, unmodified:

```python
def _is_breach(candle, direction, zone_top, zone_bottom, overshoot_tolerance):
    if direction == PoiDirection.BULLISH:
        return (zone_bottom - candle.close) > overshoot_tolerance
    return (candle.close - zone_top) > overshoot_tolerance
```

A breach is a **CLOSE beyond the zone's distal side, by more than a tolerance**.
Not a wick. Not a touch. Not a percentage.

The tolerance is the larger effect of two configured multipliers:

| setting | value |
| --- | --- |
| `zone_overshoot_tolerance_atr_multiplier` | 0.10 |
| `zone_overshoot_tolerance_zone_height_multiplier` | 0.25 |
| `reclaim_window_bars` | 3 |

And a single breach does **not** kill the zone. `GENUINE_INVALIDATION_CONFIRMED`
requires, in the 3-bar window after the first breach:

* the window is the full `reclaim_window_bars` length, **and**
* **at least 2** of those candles are qualifying breach closes, **and**
* the **last** candle of the window is itself a breach.

That is the author's "candles settle beyond the zone", expressed exactly. It
was already implemented; it did not need inventing.

## 2. THE DIRECTION TRAP -- READ THIS BEFORE JUDGING A SCREENSHOT

The distal side depends on direction, and it is the opposite of what a glance
suggests:

| zone | direction | dies when |
| --- | --- | --- |
| demand / buy (e.g. BULLISH_ENGULFING, BUY FVG) | BULLISH | **close BELOW zone bottom** |
| supply / sell (e.g. BEARISH_ENGULFING, BEARISH_PRESSURE_WICK) | BEARISH | **close ABOVE zone top** |

So for a **bearish** zone, price falling away below it is **not** failure --
that is the zone doing its job. A supply zone fails by being **overrun to the
upside**.

In the annotated H4 screenshots the questioned zones are BEARISH ENGULFING and
BEARISH PRESSURE WICK, and price sits **below** them. Under the frozen rule
that is not invalidation, and those zones are expected to remain active.

**This is the most likely explanation for "failed zones are still showing", and
it is not a defect.** It has to be settled with OHLC before any code changes,
because "make zones disappear when price passes through them downward" would
invert supply-zone semantics.

## 3. MITIGATION IS NOT DEATH, AND THE ORDER IS RESOLVED DELIBERATELY

Pine's terminal resolution (CORE ~3918):

```
if poiTermReason[i] == C_POI_TERM_NONE
    ftT = poiFirstTouchT[i]        // first touch
    ivT = poiInvalT[i]             // invalidation
    if ivT != NA and (ftT == NA or ivT < ftT)
        poiTermReason[i] = C_POI_TERM_INVALIDATED
    else if ftT != NA
        poiTermReason[i] = C_POI_TERM_MITIGATED
```

with the comment *"Once a cause is set it is never replaced: whichever time is
earlier wins, and ties go to mitigation."*

A touched zone therefore records MITIGATED, and **MITIGATED is not a terminal
state for display**. That is intended: a zone that was tapped and held is still
a live opportunity.

## 4. WHAT THE RENDERER ACTUALLY GATES ON

```
f_rc5Validity(i) =>
    r = poiTermReason[i]
    poiTerminal[i] or r == C_POI_TERM_INVALIDATED ? C_RC5_INVALIDATED
      : r == C_POI_TERM_PROMOTED ? C_RC5_SUPERSEDED
      : C_RC5_VALID
```

and display requires `f_rc5Validity(pI) == C_RC5_VALID`.

Note it checks **`poiTerminal` OR reason == INVALIDATED**. This matters: a zone
that was mitigated first and genuinely invalidated later keeps
`termReason = MITIGATED`, but the breach walk still sets `poiTerminal = true`,
so `f_rc5Validity` returns INVALIDATED and it is correctly hidden. The
"earliest cause wins" ordering does **not** leak an invalidated zone onto the
chart.

## 5. GHOST BOXES -- WHY THEY SHOULD NOT EXIST

The zone renderer evicts before it draws: any box whose POI is no longer in the
selected set is `box.delete`d and removed from the pool. A POI that turns
terminal drops out of the eligible set, so its box is deleted on the same
update. There is no separate cleanup that could lag.

So a genuinely invalidated zone that is still drawn would mean the **engine**
never flipped it, not that the renderer forgot to remove it.

## 6. WHAT IS STILL UNPROVEN

Everything above is recovered from source and is solid. What is **not** yet
done is the OHLC proof on the specific annotated XAUUSD H4 zones: identifying
each record, and walking the candles after its source bar against the breach
predicate.

That needs XAUUSD H4 data the repository does not currently hold as a fixture
(the goldens are EURUSD M15). Until that capture exists, the correct statement
is: **the rule and the wiring are correct by inspection, and the screenshots
are consistent with correct behaviour under the direction rule** -- not that
the zones have been proven valid one by one.

---

# 7. REAL XAUUSD H4 EVIDENCE -- AND WHERE THE RISK ACTUALLY SITS

795 H4 bars captured from the live chart (`OANDA:XAUUSD`, 2026-03-23 ->
2026-09-24) and run through the unmodified Python engine.

## The engine invalidates, and often

| lifecycle transition | count |
| --- | --- |
| CLOSE_BREACH_CANDIDATE | 96 |
| **GENUINE_INVALIDATION_CONFIRMED** | **53** |
| RECLAIM_CONFIRMED | 41 |
| RECLAIM_WITHOUT_DISPLACEMENT | 35 |
| DISPLACEMENT_AFTER_RECLAIM_CONFIRMED | 6 |
| FALSE_INVALIDATION_CONFIRMED | 6 |
| RECLAIM_FAILED | 2 |

239 transitions over 86 POIs. **The detector layer is not the problem** -- 53
zones were genuinely invalidated under the frozen rule.

## But not one record carries INVALIDATED

| `terminal_reason` | count |
| --- | --- |
| MITIGATED | 59 |
| None | 27 |
| **INVALIDATED** | **0** |

`freshness_status` agrees: INTERACTED 59, FRESH 27.

This is **by design**, and `resolve_terminal` says so in its own docstring:

> "POI that was touched and only later broke down stays MITIGATED."

Earliest cause wins. A zone is almost always touched before it is broken, so
the genuinely-broken zones record MITIGATED, not INVALIDATED.

## THE CONSEQUENCE THAT MATTERS

**`terminal_reason` cannot distinguish "touched and holding" from "touched and
then destroyed".** Both read MITIGATED. On this capture that is 59 records
covering both populations, with 53 genuine invalidations hiding inside them.

So any display gate that asked `terminal_reason == INVALIDATED` would show
every failed zone as live. Pine does **not** ask that -- it asks:

```
poiTerminal[i] or r == C_POI_TERM_INVALIDATED
```

The `poiTerminal` flag is set independently by the breach walk when it
concludes terminal. **The entire correctness of the active chart therefore
rests on that single boolean**, not on the terminal reason.

## WHAT IS PROVEN AND WHAT IS NOT

Proven:

* the invalidation rule exists, is close-based and direction-aware, and fires
  53 times on real XAUUSD H4;
* every one of those records reports `terminal_reason = MITIGATED`, so the
  reason field is useless as a display gate;
* Pine's gate reads `poiTerminal` first, which is the only thing that can
  carry these 53 out of the display set.

**Not** proven: that Pine's `poiTerminal` is actually true for those 53 at
runtime. That needs the flag observed on the chart, and it is the single
highest-value next measurement -- if it is false for any of them, failed zones
are live on the chart and the fix is in the Pine breach walk, not the renderer.

The author's complaint is therefore **plausible and has an identified
mechanism**, and it has not been confirmed or refuted yet. It should not be
"fixed" before that flag is read.

---

# 8. PRIORITY 1 ANSWERED -- PINE LIFECYCLE PARITY ON REAL XAUUSD H4

The question was: does Pine mark `terminal` for the same POIs production
invalidates? Answered offline using
`tests/parity_support/p3_lifecycle_model.py`, the test-side transcription of
the Pine P3 persistent lifecycle whose docstring states its reported state at
bar T is identical to `run_poi_lifecycle(candles[0..T])` for every prefix.

## Result

| | |
| --- | --- |
| Pine-model registry (ungated frontier) | 417 POIs |
| Pine-model `terminal = True` | **349** |
| production POIs (RC5 structural-origin gate on) | 86 |
| production `GENUINE_INVALIDATION_CONFIRMED` | 53 |
| identity-matched between the two | **33** |
| **AGREE** | **33** |
| **DISAGREE** | **0** |

**Outcome A: Pine's lifecycle marks terminal correctly.** On every POI whose
identity could be established unambiguously, the Pine model's `terminal` flag
and production's `GENUINE_INVALIDATION_CONFIRMED` agree exactly.

## A false result I caught before reporting it

A first pass keyed identity on `(direction, zone_top, zone_bottom)` and
reported **4 disagreements**, all of the form *production alive, Pine
terminal*.

They were not real. The Pine registry contains **43 collisions** on that key --
FVGs in particular recur with identical bounds at different times -- so
production POIs were being matched against the wrong Pine record. Adding the
confirmation/availability timestamp to the key removed every one of them and
the disagreement count fell to zero.

The lesson is worth keeping: on this data a zone-bounds key is not an identity.

## What this narrows the problem to

Since the lifecycle fires correctly, a dead zone appearing on the chart cannot
be caused by the breach walk failing. The remaining candidates are:

* the renderer not excluding a terminal record (the gate reads `poiTerminal`,
  which this result says should be set);
* a stale box object surviving its POI;
* a duplicate registry record keeping an older, still-alive copy alive.

The renderer evicts before it draws, so the first is unlikely by construction.

## The honest limits of this proof

* it matched **33 of 86** production POIs. The other 53 could not be keyed
  unambiguously -- mostly because the RC5 structural-origin gate changes which
  records exist, so there is no Pine-model counterpart to compare;
* it exercises the Pine **model**, not the shipped Pine runtime. The model's
  equivalence to production is asserted by the existing prefix campaign, and
  the shipped Pine's equivalence to the model is what the P3 parity campaign
  established at its anchor. Neither was re-run here;
* it says nothing about *timing* beyond final state -- both agree on whether a
  POI ends terminal, not on the bar at which it became so.

So: strong evidence that the lifecycle is not the defect, not a proof that the
chart is correct.

---

# 9. THE ANNOTATED ZONES -- WHAT THE ENGINE SAYS ABOUT THEM

Full POI table for the captured XAUUSD H4 window, last close **4271.600**.

## The live set is textbook-correct

Every surviving zone sits on the correct side of price:

* **supply (BEARISH) above price** -- SELL FVGs at 4834/4830/4773/4766/4737,
  and lower ones at 4392/4380/4333. Status `NO_BREACH` or
  `RECLAIM_WITHOUT_DISPLACEMENT`. Price has never closed above them, so they
  are alive by the frozen rule.
* **demand (BULLISH) below price** -- BUY FVGs at 4237/4146/4134/4100/4085/
  4064/4046, plus a SUPPORT_ZONE at 3987 and a DOJI at 3985. Price has never
  closed below them.
* one BUY FVG at 4301/4269 straddles price, `RECLAIM_WITHOUT_DISPLACEMENT`.

**This is exactly the shape a correct scanner should produce**, and it directly
supports the direction rule in section 2: nothing is invalidated merely for
being on the far side of price.

## But the two annotated types are BOTH dead

In the whole six-month window the engine finds **exactly one** of each:

| type | direction | top | bottom | status |
| --- | --- | --- | --- | --- |
| `BEARISH_PRESSURE_WICK` | BEARISH | 4369.665 | 4349.135 | **GENUINE_INVALIDATION_CONFIRMED** |
| `BEARISH_ENGULFING` | BEARISH | 4354.950 | 4335.165 | **GENUINE_INVALIDATION_CONFIRMED** |

Neither appears anywhere in the live set. Yet the annotated screenshots show
boxes labelled `BEARISH PRESSURE WICK` and `BEARISH ENGULFING` drawn on the
chart.

## Why this is a lead and not yet a verdict

Two things do not line up, and both must be resolved before calling it a defect:

1. **the bounds do not match.** The screenshots put those two boxes at roughly
   4425--4440 and 4400--4425. The engine's records are at 4349--4369 and
   4335--4355, about 70 points lower. A zone's bounds do not move, so these may
   simply be *different records*;
2. **the history windows differ.** This capture is the 795 bars the chart had
   loaded; the Pine runtime uses `calc_bars_count = 1800`. Pine may therefore
   hold bearish pressure-wick and engulfing records this capture never saw,
   and those could legitimately be alive.

The screenshots also span several different moments -- price reads 4413, ~4384,
~4350 and ~3990 across them -- so they are not one view of one instant.

## The decisive next measurement

Read the **Pine runtime's own records** for those two boxes: their zone bounds
and their `poiTerminal`. If Pine's bearish pressure wick is the 4369/4349
record and it is drawn, that is an invalidated zone on the chart and the defect
is real. If Pine holds a different, live record at 4425--4440, the chart is
correct and the capture was simply too short.

Everything needed to tell those apart is one reading of the chart's own POI
table, which needs the browser foreground.

**Do not change the renderer before that reading.** Section 8 showed the
lifecycle itself agrees 33/33, so if a dead zone really is drawn, the cause is
the renderer or a duplicate record -- and which one matters.
