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

## 6. S/R -- THE DOCUMENTED EXCEPTION, NOW FIXED IN THE RENDERER

At the reference-zone emit (CORE ~line 3617) S/R deliberately stores its
identity differently from every other family:

```
f_poiEmit(typeCode, direction, z.zoneTop, z.zoneBottom, C_POI_TIER_NA,
          z.confirmationTime, 1, z.confirmationTime,
          z.originPivotEndTime, z.confirmationTime)
```

`(srcFirst, count, srcLast)` are all `confirmationTime`. The source's own
comment explains why, and it is not an oversight:

> "the zone's SOURCE instant is its origin swing's pivot-end candle
> (SRCand.key), not its confirmation ... The (srcFirst, count, srcLast)
> identity triple deliberately stays on confirmationTime -- that is POI
> identity, and the documented collision fix depends on it."

The real source instant is carried in **`candidateTime`**, which receives
`z.originPivotEndTime`. That field is defined as *"event/open time of pivot end
candle (anchor)"* -- a real bar time, not a synthetic id, which is what makes
it usable as a coordinate at all.

So the renderer takes a **display-origin exception** for exactly these two
types:

```
left = array.get(p7zIsSr ? poiCandTime : poiSrcFirst, p7zPoiI)
```

**The identity triple was not touched.** Changing what S/R stores in
srcFirst/srcCount/srcLast would alter `f_poiSameIdentity` and `f_poiFind`, and
therefore dedup -- a semantic change needing a parity re-run, not a renderer
edit. `test_the_sr_identity_triple_was_not_touched` asserts it stays put.

The `p7zIsSr` boolean is computed once and reused by the border style, which
already asked the same question inline, so the change costs less than a fresh
predicate would.

---

## 7. TYPE CODE MAP, 1--33

| code | constant | class | drawn by | toggle | default visible |
| --- | --- | --- | --- | --- | --- |
| 1 | BUY_ORDER_BLOCK | POI zone | P7-Z | `tBuyOb` | yes |
| 2 | SELL_ORDER_BLOCK | POI zone | P7-Z | `tSellOb` | yes |
| 3 | BUY_FAIR_VALUE_GAP | POI zone | P7-Z | `tBuyFvg` | yes |
| 4 | SELL_FAIR_VALUE_GAP | POI zone | P7-Z | `tSellFvg` | yes |
| 5 | BUY_TO_SELL_CANDLE | POI zone | P7-Z | `tB2S` | yes |
| 6 | SELL_TO_BUY_CANDLE | POI zone | P7-Z | `tS2B` | yes |
| 7 | BASE_RALLY | POI zone | P7-Z | `tBaseRally` | yes |
| 8 | BASE_DROP | POI zone | P7-Z | `tBaseDrop` | yes |
| 9 | BULLISH_PRESSURE_WICK | POI zone | P7-Z | `tBullPw` | yes |
| 10 | BEARISH_PRESSURE_WICK | POI zone | P7-Z | `tBearPw` | yes |
| 11 | BULLISH_ENGULFING | POI zone | P7-Z | `tBullEng` | yes |
| 12 | BEARISH_ENGULFING | POI zone | P7-Z | `tBearEng` | yes |
| 13 | HAMMER | POI zone | P7-Z | `tHammer` | yes |
| 14 | SHOOTING_STAR | POI zone | P7-Z | `tShootStar` | yes |
| 15 | MORNING_STAR | POI zone | P7-Z | `tMorning` | yes |
| 16 | EVENING_STAR | POI zone | P7-Z | `tEvening` | yes |
| 17 | SUPPORT_ZONE | POI zone (S/R) | P7-Z, dashed border | `tSupport` | yes |
| 18 | RESISTANCE_ZONE | POI zone (S/R) | P7-Z, dashed border | `tResist` | yes |
| 19 | EQUAL_HIGHS_LIQUIDITY | liquidity / reference | `dspLiq` layer | **hardcoded false** in `p7zTypeOn` | no |
| 20 | EQUAL_LOWS_LIQUIDITY | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 21 | CURRENT_DAY_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 22 | CURRENT_DAY_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 23 | CURRENT_WEEK_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 24 | CURRENT_WEEK_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 25 | CURRENT_MONTH_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 26 | CURRENT_MONTH_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 27 | PREVIOUS_DAY_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 28 | PREVIOUS_DAY_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 29 | PREVIOUS_WEEK_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 30 | PREVIOUS_WEEK_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 31 | PREVIOUS_MONTH_HIGH | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 32 | PREVIOUS_MONTH_LOW | liquidity / reference | `dspLiq` layer | hardcoded false | no |
| 33 | DOJI | POI zone | P7-Z | `tDoji` | yes |

Codes 1--18 are the contiguous core range. 19--32 are the liquidity family and
are **not** POI-zone types -- they are not broken and must not be "fixed" into
boxes. 33 sits outside the core range because DOJI was added later.

## 8. CURRENT CAPACITY

Measured on the real compiler with a single 97-token pad:

| build | padded `outputILLength` | derived BASE |
| --- | --- | --- |
| v19 (before any fix) | 100,289 | 100,192 |
| v20 (global source anchor) | 100,289 | 100,192 |
| **v21 (+ S/R display origin)** | **100,308** | **100,211** |

Limit 100,256, so headroom is now **45**.

The global anchor fix cost **0**; the S/R exception cost **+19**.

The previously recorded 100,183 does not reproduce under this methodology and
should be treated as a historical measurement discrepancy, not current
capacity. Baseline and fixed were measured identically, so the deltas above are
sound even though the absolute differs from the old note.
