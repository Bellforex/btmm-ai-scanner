# THE RC5 POI LIBRARY -- WHAT EXISTS, WHAT CAN DRAW, AND WHY

Read from `tradingview/btmm_poi_btrc_scanner_rc5_user.pine` at the current
commit. Nothing here is from memory.

---

## 1. THE COUNT IS 19, NOT 18

The brief says "18 type toggles". There are **19**, and all nineteen default
`true`. They are declared at CORE lines 79--97:

| # | input | label | type code |
| --- | --- | --- | --- |
| 1 | `tBuyOb` | BUY ORDER BLOCK | 1 |
| 2 | `tSellOb` | SELL ORDER BLOCK | 2 |
| 3 | `tBuyFvg` | BUY FVG | 3 |
| 4 | `tSellFvg` | SELL FVG | 4 |
| 5 | `tB2S` | BUY TO SELL CANDLE (B2S) | 5 |
| 6 | `tS2B` | SELL TO BUY CANDLE (S2B) | 6 |
| 7 | `tBaseRally` | BASE RALLY | 7 |
| 8 | `tBaseDrop` | BASE DROP | 8 |
| 9 | `tBullPw` | BULLISH PRESSURE WICK | 9 |
| 10 | `tBearPw` | BEARISH PRESSURE WICK | 10 |
| 11 | `tBullEng` | BULLISH ENGULFING | 11 |
| 12 | `tBearEng` | BEARISH ENGULFING | 12 |
| 13 | `tHammer` | HAMMER | 13 |
| 14 | `tShootStar` | SHOOTING STAR | 14 |
| 15 | `tMorning` | MORNING STAR | 15 |
| 16 | `tEvening` | EVENING STAR | 16 |
| 17 | `tSupport` | SUPPORT ZONE | 17 |
| 18 | `tResist` | RESISTANCE ZONE | 18 |
| 19 | `tDoji` | DOJI | **33** |

The first eighteen are the contiguous "core" range
(`C_POI_CORE_TYPE_MIN = 1` .. `C_POI_CORE_TYPE_MAX = 18`). DOJI sits apart at
code 33.

## 2. FOURTEEN TYPE CODES CANNOT DRAW AS ZONES -- BY DESIGN

`p7zTypeOn` (line 98) is indexed `code - 1`. Between the eighteen core toggles
and DOJI it contains **fourteen hardcoded `false` entries**, covering codes
19--32:

```
19 EQUAL_HIGHS_LIQUIDITY   20 EQUAL_LOWS_LIQUIDITY
21 CURRENT_DAY_HIGH        22 CURRENT_DAY_LOW
23 CURRENT_WEEK_HIGH       24 CURRENT_WEEK_LOW
25 CURRENT_MONTH_HIGH      26 CURRENT_MONTH_LOW
27 PREVIOUS_DAY_HIGH       28 PREVIOUS_DAY_LOW
29 PREVIOUS_WEEK_HIGH      30 PREVIOUS_WEEK_LOW
31 PREVIOUS_MONTH_HIGH     32 PREVIOUS_MONTH_LOW
```

These are the **liquidity / reference-level family**. They are detected and
registered like any other POI -- they are simply not drawn by the POI *zone*
renderer, because they belong to the liquidity layer behind
`dspLiq` ("Show Liquidity (BSL / SSL pools, sweeps)", default **false**).

So if someone asks why "previous week high" never appears as a zone: it is not
a broken detector and not a missing toggle. It is a different presentation
layer that is off by default.

## 3. A STALE COMMENT THAT CONTRADICTS THE CODE

The header above the filters (lines 72--77) still says:

> "There is no DOJI type: a Doji is only the star middle-candle test"

`C_POI_DOJI = 33` exists and `tDoji` is wired into `p7zTypeOn`. The comment
predates the DOJI work and is now wrong. **It is documentation drift, not a
functional defect** -- left alone rather than spending CORE edits on a comment,
but it should not be trusted when reading the file.

The Doji *rule* itself is unchanged and still correct: body / total range
<= 0.10.

## 4. WHAT A POI MUST PASS TO BE DRAWN

From the display-eligibility test (CORE line ~6977), in order:

1. `f_rc5Validity(pI) == C_RC5_VALID` -- lifecycle-valid;
2. **not** in `rc5Subordinate` -- P4 ownership hides subordinate members;
3. `array.get(p7zTypeOn, ty - 1)` -- the type toggle;
4. not an FVG dominated by another record at the same origin.

Then selection keeps only the nearest `p7zMaxVisibleZones` (default 8) **to
current price**, via `bahui.nearestFirst`.

This is why "a type is not visible" has at least five distinct causes, and why
a display filter must never be used to hide a broken detector: the filter is
step 3 of 4, and steps 1, 2 and the quota all precede the drawing.

## 5. THE GEOMETRY CONTRACT

Every drawn zone now takes:

| edge | source |
| --- | --- |
| left | `poiSrcFirst` -- the record's **first source candle** |
| top | `poiZoneTop` -- frozen detector measurement |
| bottom | `poiZoneBottom` -- frozen detector measurement |
| right | `p7zRightEdge`, extended while the POI lives |

`tests/unit/test_rc5_poi_source_attachment.py` asserts all of it, and names
`poiAvailTime`, `poiCandTime`, `time_close`, `timenow` and `bar_index`
explicitly as forbidden origins so the defect cannot return quietly.

## 6. ONE KNOWN REMAINING DETACHMENT -- S/R

At the reference-zone emit (CORE line ~3617):

```
f_poiEmit(typeCode, direction, z.zoneTop, z.zoneBottom, C_POI_TIER_NA,
          z.confirmationTime, 1, z.confirmationTime,
          z.originPivotEndTime, z.confirmationTime)
```

`srcFirstTime` and `srcLastTime` are both set to **`z.confirmationTime`**,
while the actual source coordinate, `z.originPivotEndTime`, is passed as
`candidateTime`.

So for SUPPORT_ZONE (17) and RESISTANCE_ZONE (18), anchoring the renderer to
`srcFirstTime` -- correct for every other family -- still lands on the
confirmation bar rather than the originating swing.

**This was deliberately NOT changed.** `srcFirstTime`/`srcCount`/`srcLastTime`
are the POI *identity* triple (`f_poiSameIdentity`, `f_poiFind`), so altering
what S/R stores there changes dedup and record identity, not just presentation.
That is a semantic change and needs an author decision plus a parity re-run --
it is not a renderer fix.
