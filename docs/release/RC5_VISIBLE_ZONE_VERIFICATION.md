# EVERY VISIBLE ZONE IS STILL ACTIVE -- VERIFIED

**Run configuration:** `OANDA:XAUUSD` H4, 795-bar capture,
`rc5_structural_origin = False` (production default), quota
`p7zMaxVisibleZones = 8`, last close **4271.600**. Full pipeline replayed:
eligibility -> P4 -> type toggle -> overlap-cluster winner -> nearest-8 quota.

---

## 1. THE FUNNEL

| stage | count |
| --- | --- |
| excluded: **GENUINE_INVALIDATION_CONFIRMED** | **142** |
| excluded: P4 subordinate | 2 |
| excluded: liquidity/reference layer (codes 19--32) | 15 |
| **eligible** | **45** |
| after same-direction overlap-cluster arbitration | **12** |
| **drawn (quota 8)** | **8** |

The validity gate is doing the heavy lifting: **142 dead zones removed before
anything reaches the visual layer.**

## 2. THE VISIBLE-ZONE TABLE

| # | type | dir | top | bottom | tier | taps | lifecycle | terminal | verdict |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BUY_FAIR_VALUE_GAP | BULL | 4301.015 | 4269.215 | NA | 7 | RECLAIM_WITHOUT_DISPLACEMENT | MITIGATED | **C** reclaim, still valid |
| 2 | BULLISH_PRESSURE_WICK | BULL | 4262.100 | 4247.240 | STANDARD | 5 | FALSE_INVALIDATION_CONFIRMED | MITIGATED | **C** false break, still valid |
| 3 | BUY_FAIR_VALUE_GAP | BULL | 4237.000 | 4213.540 | NA | 2 | NO_BREACH | MITIGATED | **B** mitigated + holding |
| 4 | SELL_FAIR_VALUE_GAP | BEAR | 4333.320 | 4320.565 | NA | 0 | NO_BREACH | -- | **A** fresh + valid |
| 5 | BEARISH_PRESSURE_WICK | BEAR | 4369.560 | 4363.610 | STANDARD | 0 | NO_BREACH | -- | **A** fresh + valid |
| 6 | BEARISH_PRESSURE_WICK | BEAR | 4435.045 | 4408.725 | STRONG | 0 | NO_BREACH | -- | **A** fresh + valid |
| 7 | BEARISH_ENGULFING | BEAR | 4490.895 | 4460.155 | STRONG | 0 | NO_BREACH | -- | **A** fresh + valid |
| 8 | BULLISH_ENGULFING | BULL | 4034.250 | 4014.515 | STRONG | 0 | NO_BREACH | -- | **A** fresh + valid |

### Verdict counts

* **A -- fresh and valid: 5**
* **B -- mitigated but holding: 1**
* **C -- reclaim / false break, still valid: 2**
* **D -- genuinely invalidated: 0**
* **E -- superseded / other terminal: 0**
* **F -- duplicate or stale graphic: 0**

> **INVALIDATED ZONES IN THE VISIBLE SET: 0.**

Every drawn box is in a class the doctrine says to keep. Rows 1 and 2 are
precisely the false-break / reclaim cases the author asked to retain -- one has
7 taps and one 5, and both are still live because neither broke its far side.

## 3. WHY A DEAD ZONE CANNOT BE DRAWN

This is structural, not incidental. The only path into the visible set is
guarded by:

```
f_rc5Validity(pI) == C_RC5_VALID and not map.contains(rc5Subordinate, pI)
  and array.get(p7zTypeOn, ty - 1) and not (isFvg and ...dominated)
```

and `f_rc5Validity` returns `C_RC5_INVALIDATED` when `poiTerminal` is set **or**
the reason is `INVALIDATED`. `test_rc5_type_filter_matrix.py` asserts there is
**exactly one** `array.push(p7zVisibleIdx, pI)` in CORE and that it sits behind
that conjunction, so no second route exists.

Object cleanup is equally structural: the renderer **evicts before it draws** --
any box whose POI is no longer selected is `box.delete`d and dropped from the
pool on the same bar. A terminal POI leaves the eligible set, so its box is
removed in the same update. There is no deferred sweep that could lag.

## 4. TAP COUNT IS NOT A DEATH SENTENCE -- SHOWN IN THE DATA

Rows 1--3 carry 7, 5 and 2 taps and remain visible. Row 2 even reached
`FALSE_INVALIDATION_CONFIRMED`. That is the doctrine working as specified:
touched is not dead, and a reclaimed far-side break is explicitly retained.

Meanwhile 142 zones that genuinely broke are gone. The two behaviours coexist
correctly.

## 5. LIMITS OF THIS VERIFICATION

* it replays the **Python** pipeline over the captured bars and models the Pine
  cluster stage; it is not a read of Pine's own runtime box list, which Pine
  does not expose;
* the chart currently runs **CORE v20**, not v21. For this question they are
  identical -- the v21 delta is the S/R *display origin* only and touches no
  lifecycle or eligibility logic;
* the capture is 795 bars while the live chart had 534 loaded at the time of
  checking, so the live set may differ in membership. The **classification**
  result does not depend on window length: the gate excludes invalidated
  records whatever the window.
