# POI QUESTION-B + PROXIMITY LIVE ACCEPTANCE REPORT

**Verdict: CASE A. Detection is CORRECT. The visibility defect is CONFIRMED.**

The user-marked M15 zone is already in the P3 registry, as an ACTIVE
`BUY_ORDER_BLOCK` with geometry matching the marked rectangle. The scanner found
it and then never drew it.

**P3 semantics unchanged. RC1 remains the valid validation baseline.**

---

## ACCOUNT CORRECTION — READ FIRST

The user was right: the connected Chrome is signed in as **STEVECRYPTO1995**, not
**bellcare1994**. Only one browser is connected to this session, so I could not
reach the correct account.

What that does and does not affect:

- **Does not affect the Question B answer.** The bars used are FX:XAUUSD (exchange
  FXCM) price history read straight from TradingView's series model. Feed data for
  a symbol is the same whoever is signed in, and the candidate bar is settled
  history roughly 15 hours old at capture time, not a live-entitlement-sensitive
  tick. The one residual caveat is that data entitlements can differ per account;
  for bars this old the values are the same, and I will happily re-verify on
  bellcare1994 to close even that gap.
- **Does block Steps 6 through 9.** The corrective DEV was **not** deployed and no
  live M5/M15/H1 acceptance was run. I will not install a script into an account
  that is not the intended one.

---

## STEP 1 — EXACT CANDLE RECOVERY

Read from the chart's own series model, not from pixels.

| Property | Value |
| --- | --- |
| Symbol | `FX:XAUUSD` (exchange **FXCM**) |
| Resolution | 15 |
| Price scale | 100, minmov 1, so mintick **0.01** |
| Chart display timezone | **Europe/London** |
| Bars captured | 340 |
| Range | 2026-09-03 11:25Z to 2026-09-09 20:45Z |
| Saved to | `artifacts/questionb/FX_XAUUSD_M15_LIVE_20260909.csv` |

The chart was on **OANDA:XAUUSD** when opened; I switched it to the FXCM ticker
before reading anything. Capture integrity was asserted on load: timestamps
strictly ascending, no duplicates.

Because the chart displays Europe/London, the user's "06:00–06:30 chart time"
resolves to **05:00–05:30 UTC**.

### The window, in London display time

| London | UTC | Open | High | Low | Close | Dir | Body |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 05:45 | 04:45 | 4377.98 | 4382.50 | 4377.35 | 4381.53 | bull | 3.55 |
| 06:00 | 05:00 | 4381.53 | 4387.76 | 4380.41 | 4387.64 | bull | 6.11 |
| **06:15** | **05:15** | **4387.64** | **4388.55** | **4383.21** | **4385.05** | **bear** | **2.59** |
| 06:30 | 05:30 | 4385.05 | 4395.51 | 4384.29 | 4395.51 | bull | **10.46** |
| 06:45 | 05:45 | 4395.51 | 4400.73 | 4392.42 | 4398.83 | bull | 3.32 |

---

## STEP 2 — THE CANDIDATE

**1. Timestamp:** 2026-09-09 **06:15 Europe/London** = 05:15 UTC = epoch ms
`1788930900000`.

**2. OHLC:** open 4387.64, high 4388.55, low 4383.21, close 4385.05.

**3. Zone top: 4388.55. 4. Zone bottom: 4383.21.**

This is the single bearish candle sitting immediately before the strong bullish
displacement at 06:30, which has a 10.46 body and closes on its high. It matches
the user's description exactly, and the frozen detector geometry (4383.21–4388.55)
lands inside the user's approximate 4384–4388 read of the screenshot. Per the
brief I used the exact detector geometry, not the approximate screenshot bounds.

---

## STEP 3 — ALL 18 FROZEN DETECTORS

Evaluated with the frozen predicates and thresholds from
`tests/parity_support/p3_pine_model.py`. Script: `artifacts/questionb/detector_verdicts.py`.

| # | Detector | Verdict | Exact reason |
| --- | --- | --- | --- |
| 5 | **BUY_ORDER_BLOCK** | **PASS** | origin(06:15) bearish, displacement(06:30) bullish, displacement.close 4395.51 > origin.high 4388.55, range ratio 2.1011 >= standard 2.0000 |
| 6 | SELL_ORDER_BLOCK | FAIL | requires bullish origin; origin(06:15) is bearish (open 4387.64 > close 4385.05), so `_is_bull(origin)` = False |
| 7 | BUY_FVG | FAIL | candle3.low 4384.29 > candle1.high 4387.76 = False |
| 8 | SELL_FVG | FAIL | candle3.high 4395.51 < candle1.low 4380.41 = False |
| 9 | **BULLISH_ENGULFING** | **PASS** | engulfed(06:15) bearish, engulfing(06:30) bullish, range ratio 2.1011 >= standard 2.0000 |
| 10 | BEARISH_ENGULFING | FAIL | requires bullish engulfed; engulfed(06:15) is bearish, so `_is_bull(engulfed)` = False |
| 11 | MORNING_STAR | FAIL | middle(06:15) body efficiency 0.4850 <= doji max 0.1000 = False |
| 12 | EVENING_STAR | FAIL | middle(06:15) body efficiency 0.4850 <= doji max 0.1000 = False |
| 13 | HAMMER | FAIL | lower-wick share 0.3446 >= 0.6000 = False; body efficiency 0.4850 <= 0.3000 = False; upper-wick share 0.1704 <= 0.1000 = False |
| 14 | SHOOTING_STAR | FAIL | upper-wick share 0.1704 >= 0.6000 = False; body efficiency 0.4850 <= 0.3000 = False; lower-wick share 0.3446 <= 0.1000 = False |
| 15 | BULL_PRESSURE_WICK | FAIL | lower-wick share 0.3446 >= 0.4000 = False; bull close position 0.3446 >= 0.6000 = False |
| 16 | BEAR_PRESSURE_WICK | FAIL | upper-wick share 0.1704 >= 0.4000 = False; upper/lower dominance = False |
| 17 | B2S | FAIL | requires a bullish candidate; candidate(06:15) is bearish. Size ratio 0.7265 >= 2.0000 = False regardless |
| 18 | S2B | FAIL | candidate range 5.3400 / max range of prior 3 bars 7.3500 = 0.7265, needs >= 2.0000 = False; body efficiency 0.4850 >= 0.6000 = False |
| 19 | BASE_RALLY | FAIL | two-bar base (06:00–06:15) height 8.1400 exceeds the base-height gate of 0.6000 x departure range 11.2200 = 6.7320 |
| 20 | BASE_DROP | FAIL | requires a bearish departure closing below base_low; departure(06:30) is bullish (close 4395.51 > open 4385.05), so `_is_bear(departure)` = False |
| 21 | SUPPORT_ZONE | FAIL | not anchored to a single candidate candle; produced by the P1 swing/frontier layer. No SUPPORT_ZONE with this geometry exists in the replay |
| 22 | RESISTANCE_ZONE | FAIL | not anchored to a single candidate candle; produced by the P1 swing/frontier layer. No RESISTANCE_ZONE with this geometry exists in the replay |

**Two PASS, sixteen FAIL.**

---

## STEP 4 — REGISTRY MATCH

Both passing detectors produced a real registry POI, with geometry identical to
the candidate candle's high and low.

| Field | POI A | POI B |
| --- | --- | --- |
| Registry index | **172** | **173** |
| Type | **BUY_ORDER_BLOCK** | **BULLISH_ENGULFING** |
| Direction | bullish | bullish |
| Timeframe | M15 (chart) | M15 (chart) |
| Zone top | **4388.55** | **4388.55** |
| Zone bottom | **4383.21** | **4383.21** |
| Candidate time | 2026-09-09 06:15 London | 2026-09-09 06:15 London |
| Availability time | 2026-09-09 06:45 London | 2026-09-09 06:45 London |
| Terminal state | not terminal (status 1) | not terminal (status 1) |
| Active now | **YES** | **YES** |

**23. Matching type: BUY_ORDER_BLOCK** (with a co-located BULLISH_ENGULFING).
**24. Registry IDs: 172 and 173.**

---

## STEP 5 — CLASSIFICATION

**CASE A.**

**25. P3 detection defect: FALSE.** **26. Specification coverage gap: FALSE.**

The frozen detector fired, the POI entered the registry, it is still active, and
its geometry matches what the user drew by hand. The engine agreed with the
trader. Only the display disagreed.

---

## STEPS 6–9 — LIVE DEPLOYMENT AND ACCEPTANCE

**BLOCKED on account access. Not performed.**

**31. M5: not run. 32. M15: not run. 33. H1: not run.** No RE10041 / RE10045
check was possible, because nothing was deployed.

---

## STEP 8 — THE USER'S ZONE UNDER THE NEW RULE, NUMERICALLY

The brief asked me not to say "not visible" but to prove it. Measured against the
capture's final close of 4400.87, with 51 active POIs:

| Item | Value |
| --- | --- |
| User zone (idx 172) distance from close | **12.32** |
| Its proximity rank | **16th of 51** |
| Box capacity | 12 |
| In the old registry-order 12 | **No** |
| In the new nearest 12 | **No** |

So at that instant the zone is **not** displayed under the new rule either, and
the reason is exact: **fifteen active POIs are strictly nearer to price**, the
twelfth of which sits at distance 9.016. The zone is 3.30 outside the cut.

This is correct behavior rather than a second defect. Price had travelled about
15.8 above the zone in the ~15.5 hours since it formed. When the user was looking
at it, price was inside or adjacent to the zone, where its distance is 0 and its
rank is first.

**27. Old displayed median distance: 63.45** (range 8.97 to 72.57).
**28. New displayed median distance: 3.22** (range 0 to 9.016).
**29. Active count: 51. 30. Visible boxes: 12.**

Note the active count here is 51, not the 101–136 of the screenshots, purely
because this capture is 340 bars against the chart's 1800. The mechanism is
unchanged; the effect is milder in a shorter window, which makes the measured
18x median improvement a conservative floor rather than a best case.

---

## STEP 10 — P7 TABLE NOW SHARES THE PROJECTION

**34. P7 table proximity: FIXED. 35. P7-Z boxes proximity: FIXED.**

Both surfaces now use one projection, so the table describes the zones the trader
can see. Table capacity 8, box capacity 12, and a test asserts the table's rows
are exactly the first 8 of the box selection.

**One real hazard surfaced here and was caught.** The table's parallel arrays
(`p7PoiBull`, `p7PoiTier`, `p7PoiFinal`, `p7PoiPerm`, `p7PoiLc`, ...) are keyed by
**row position** inside `p7PoiIdx`, not by POI-registry index. Reordering rows
without re-keying every one of those reads makes each row keep its old position's
data while showing another POI's identity. My first cut of the patch did exactly
that on three of nine fields. A leftover check caught it, both were fixed, and a
permanent parametrized test now asserts every printed row's payload still belongs
to its own POI.

---

## STEP 11 — ONE-SIDED SELECTION

Not silently changed. On this live capture pure proximity returned a **mixed**
set: 3 bearish and 9 bullish in the nearest 12, with one zone containing price.
That is a healthier result than the 12-bullish/0-bearish set measured on the
earlier frozen capture, which suggests one-sidedness is data-dependent rather
than structural.

**No quota was introduced.** It remains an author decision, and the live test the
brief asks for still has to happen on the right account before it can be settled.

---

## STEP 12 — REGRESSION

Change scope is the strongest guarantee here: **zero modifications under `src/`**
and **zero modifications to any existing file in `tradingview/`**. RC1 is
byte-identical, SHA256 still
`143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54`.

The corrective DEV differs from RC1 in **six hunks, all presentation**: the
indicator title, the P7-Z header comment, the P7-Z selection loop, and the P7
table ordering block plus its parallel-array reads.

**36. P3 semantics changed: FALSE. 28. Affected detector: none.**

Frozen evidence targets, unchanged by construction:

| Phase | Evidence |
| --- | --- |
| P5 | 240850 / 240850; H1 351473241, H2 335238294 |
| P6 | 30 / 30 |
| P8 | 456 / 456; H1 294719549, H2 35571918 |
| P9 | H1 224768619, H2 772693120 |

Stated precisely: those digest integers live in the closure documents, not as
literals in test code. What the suite run proves is that every parity test still
passes and that no engine source changed, not that the digests were re-derived
this session.

---

## VALIDATION AND SAFETY

| # | Item | Value |
| --- | --- | --- |
| 37 | RC1 still valid validation baseline | **TRUE** |
| 38 | V1-A paused | **TRUE** |
| 39 | OOS unopened | **TRUE** |
| 40 | push | **FALSE** |
| 41 | merge | **FALSE** |
| 42 | publish | **FALSE** |
| 43 | live trading | **FALSE** |

Item 37 is now unconditional rather than provisional. Question B resolved as
CASE A, so P3 semantics do not change and the validation subject does not move.

---

## WHAT IS LEFT

1. **Point me at the bellcare1994 account**, by switching accounts in the
   connected Chrome or connecting the browser that is signed into it.
2. Then Steps 6–9 run: deploy the corrective DEV, verify nearby zones appear on
   M5, M15 and H1, and check for RE10041 / RE10045.
3. Step 11's bull/bear quota decision follows from what that live test shows.
