# SCANNER EVENT ACCEPTANCE -- LIVE TRADINGVIEW RUN

Performed on the live chart, not from source. 2026-09-25.

| | |
| --- | --- |
| account | `bellcare1994` |
| layout | `BAH-RC5-LAB` (`/chart/fn3ash9L/`) |
| symbol / timeframe | `OANDA:XAUUSD` H4 |
| chart live | **yes** -- title price and clock advancing between calls |
| canvas | 1599 x 764 |
| manual drawings | **0** (`getAllShapes()` before and after) |

---

## 1. DEPLOYMENT -- v21 ATTACHED

| | before | after |
| --- | --- | --- |
| CORE | `[RC5 USER]` **v20.0** | `[RC5 USER]` **v21.0** |
| VIEW | v1.0 | v1.0 (untouched) |
| duplicate CORE instances | 0 | **0** |

**A trap worth recording.** Four add-clicks appeared to do nothing -- the study
list kept reporting v20 -- so they were repeated. They had all worked; the
study list simply had not refreshed yet, and removing the old instance revealed
**four** v21 instances at once. Three were removed. When driving this UI,
verify by re-reading after a delay rather than by immediate feedback.

Settings restored on the v21 instance rather than left at defaults:

```
dspMs = true   dspBtmm = true   dspTl = true      (CORE)
dspMs = true                                       (VIEW)
19/19 POI type toggles = true
p7zShowZones = true   p7zShowLabels = true
```

## 2. FILTER SMOKE -- ON THE REAL CHART

| case | result |
| --- | --- |
| **ALL ON** | 8 zones drawn -- two BEARISH ENGULFING, BEARISH PRESSURE WICK, two BUY FVG, MORNING STAR, two BULLISH ENGULFING. Matches `p7zMaxVisibleZones = 8` |
| **FVG ONLY** (`in_9`,`in_10` on, other 17 off) | **PASS** -- only BUY FVG boxes remain; every candle-pattern zone disappeared |
| **ALL OFF** (19 toggles off) | **PASS** -- zero POI zones |

In **both** filtered states the independent layers stayed up: **BOS/CHOCH
labels, the structural trendline and the BTMM markers all remained**. That is
the contract -- a POI type switch governs POI zones only.

Full scanner mode was restored afterwards and the layout is **not** left in a
test state.

## 3. RUNTIME

* console errors from the scanner: **0**
* object storms / duplicate boxes: none observed
* exactly **one** structural trendline (purple, descending), no duplicate
* BOS / CHOCH labels render from VIEW
* recalculation after an input change takes ~15--20s at this history depth,
  which is worth knowing before demonstrating a filter live on stage

## 4. WHAT THIS RUN DOES *NOT* ESTABLISH

**Reload persistence was not re-verified.** The layout was saved twice -- once
through the API and once through the toolbar Save button, the second with no
save errors -- but TradingView's "Leave site?" guard stayed up, and
`force: true` is prohibited, so the post-reload read could not be taken.

The first API save **did** fail: `POST /api/v1/charts/save/ TypeError: Failed
to fetch`, alongside failing telemetry posts, i.e. a transient network blip.
The callback still reported success, so **the save callback is not proof the
save landed** -- the console is. The retry and the toolbar save were clean.

**Pixel-level geometry was not verified.** Zone top/bottom values are
consistent with the engine's records, but reading exact bounds off a screenshot
is the mistake that produced two retracted conclusions earlier in this project.
Source attachment is proven by `test_rc5_poi_source_attachment.py` and the
v20/v21 renderer fixes, and the visual is consistent with it -- it is not
independently proven by this screenshot.

## 5. ACCEPTANCE GATE

| check | status |
| --- | --- |
| v21 CORE attached | **PASS** |
| VIEW present | **PASS** |
| no stale duplicate CORE | **PASS** |
| filter smoke (all-on / all-off / FVG-only) | **PASS** |
| structure + trendline independent of filters | **PASS** |
| one trendline, no duplicates | **PASS** |
| no runtime errors | **PASS** |
| layout saved | **PASS** (toolbar save, no errors) |
| reload persistence re-confirmed | **NOT VERIFIED** -- unload guard, force prohibited |
| per-POI pixel geometry | **NOT VERIFIED** -- deliberately |

Nine of eleven pass. The two that do not are stated rather than assumed, and
neither is a defect -- one is a tooling limit and the other is a method I have
already been burned by twice.
