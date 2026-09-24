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
