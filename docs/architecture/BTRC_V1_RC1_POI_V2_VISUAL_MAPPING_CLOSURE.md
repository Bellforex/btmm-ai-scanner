# BTRC V1 — RC1 POI V2 VISUAL MAPPING CLOSURE

**Status:** live on `bellcare1994`, chart `6cu1b2O7`, `FX:XAUUSD` (exchange FXCM).
**Chart configuration:** `BTMM + POI + BTRC Scanner [P6 DEV]` +
`BTMM + POI + BTRC Scanner [RC1 POI V2 DEV]`.

**RC1 is unchanged.** SHA256
`143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54`.
RC1 was removed from the *chart* via the explicit context-menu Remove and
remains saved in My Scripts.

**V2 DEV** SHA256 `35220e1952f1528afadbfacdeb656e7d1dbe29149616e2d7827d59df1f8c1215`,
6609 lines.

**V1-A remains PAUSED. OOS remains UNOPENED. P3 semantics are unchanged**, so the
RC1 semantic validation baseline stays intact.

---

## 1. THE DEFECT

Screenshots showed 101–136 active POIs and no usable zones near price.

Frozen RC1 selected zones as `p7PoiIdx[0 .. capacity-1]`, ascending POI-registry
index. The registry is append-only and P3 has no expiry, so the first entries are
the oldest POIs that were never invalidated. Measured on the frozen FXCM M15
capture (close 4329.33, ATR14 11.78, 157 active): the 12 drawn zones sat
199.01–259.06 from price, roughly 17–22 ATR, while **four active POIs contained
price**, and the overlap between drawn and nearest was **zero**. The P7 table
shared the identical rule at capacity 8, also with zero overlap.

On M1 the failure mode differs: old POIs invalidate quickly, so first-by-registry
lands on recent POIs anyway. There the problem was clutter, unreadable labels
piled at the right edge, and a solid green fill.

---

## 2. WHAT CHANGED (PRESENTATION ONLY)

| Area | RC1 | V2 |
| --- | --- | --- |
| Zone selection | first N by registry index | N nearest to current close |
| Capacity meaning | 12 raw zones | **8 visual groups** |
| Timeframe token | raw `timeframe.period` (`1`, `60`) | `M1` … `W1` |
| Co-located POIs | one box each | one box, combined label |
| Same-direction FVGs | one box each | overlap-or-touch clusters |
| Label anchor | `time_close` (all stacked) | zone origin |
| Fill | directional, 85% | neutral gray, 92% |
| P7 table order | registry index | same proximity projection |

**Distance** is 0 inside the zone, else the gap to the nearest boundary.
Ascending, ties by lowest registry index. No tier, BTRC, BTMM or timeframe
weighting, and no bull/bear quota.

**Grouping runs over the whole active set before capacity is applied**, so a
cluster can never be split by the display cut.

**The engine universe is untouched.** `p7PoiIdx` still holds every active POI;
P5 evaluates and P8 monitors all of them; no registry identity is merged.

---

## 3. FVG CLUSTERING

A cluster requires all of: FVG family, same direction, same origin timeframe,
simultaneously eligible, and intervals that overlap **or touch**. Membership is
transitive. Geometry is the envelope — min bottom, max top, earliest origin —
never an average and never a midpoint-derived synthetic zone.

**The author's golden M1 area decomposes into FOUR singletons, not one cluster.**
Computed, not assumed:

| Pair | Gap |
| --- | --- |
| 176 → 177 | 0.07 |
| 177 → 178 | 1.24 |
| 178 → 179 | 0.23 |

None touch, so none merge. A golden test pins this so a later change that
silently merges them fails. Only idx 176 was still active at that capture's last
bar; 177–179 had gone terminal.

The rule does cluster where geometry earns it. On the latest 500 M1 bars it
produced `M1 • BUY FVG ×4` and `M1 • SELL FVG ×4`, and live on H1 it rendered
`H1 • SELL FVG ×2`.

Outside the FVG family, **overlap alone merges nothing**. Only exact-geometry
twins share a box.

---

## 4. GOLDEN: BASE RALLY

Registry index **170**, `BASE_RALLY`, top **4349.17**, bottom **4347.78**,
origin 01:41 Europe/London, active. The author's visual read of 4348–4350
brackets it exactly. It renders as `M1 • BASE RALLY` and never joins an FVG
cluster (a test enforces that).

**Not visually re-traced in this pass.** At the time of testing price was near
4396, roughly 48 above the zone, so it is not in the nearest 8. Selection is
anchored to current close rather than viewport, so panning to it does not pull it
into view. Production defaults were left untouched rather than raised.

---

## 5. LIVE ACCEPTANCE

### Host matrix

| Host | Studies | RE10041 | RE10045 | Other RE |
| --- | --- | --- | --- | --- |
| M1 | 2 | 0 | 0 | 0 |
| M5 | 2 | 0 | 0 | 0 |
| M15 | 2 | 0 | 0 | 0 |
| H1 | 2 | 0 | 0 | 0 |

Switch sequence M1 → M5 → M15 → H1 → M15 → M1 passed with no stale studies.

### Reload matrix

Reloaded directly on M1, M5, M15 and H1. Every reload reconstructed with exactly
**2** studies, correct resolution and bars, and zero runtime errors. Study count
stayed at exactly 2 across all reloads, so no instance accumulation.

### Rendered labels observed live

`H1 • SELL FVG ×2`, `H1 • SELL OB + BEAR ENGULF • STRONG`,
`H1 • SHOOTING STAR + BEAR PRESSURE`, `M1 • B2S`, `M1 • EVENING STAR • STRONG`,
`M1 • BULL PRESSURE • STRONG`. Zones render gray with thin directional borders
and candles read clearly through them.

---

## 6. 500-BAR M1 MARKET AUDIT

Latest 500 genuine FXCM M1 bars, 2026-09-10 00:45Z to 10:24Z, close 4395.86.

| Measure | Value |
| --- | --- |
| POIs created | 307 |
| Active | 63 |
| Terminal | 244 |
| Exact-geometry duplicate groups | 30 (covering 62 POIs) |
| Visual groups over active | 49 |
| Multi-member groups | 8 (4 of them FVG clusters) |

Counts by type:

| Type | n | Type | n |
| --- | --- | --- | --- |
| BUY OB | 13 | SELL OB | 9 |
| BUY FVG | 62 | SELL FVG | 76 |
| BULL ENGULF | 14 | BEAR ENGULF | 13 |
| MORNING STAR | 8 | EVENING STAR | 11 |
| HAMMER | 10 | SHOOTING STAR | 7 |
| BULL PRESSURE | 37 | BEAR PRESSURE | 31 |
| B2S | 0 | S2B | 0 |
| BASE RALLY | 5 | BASE DROP | 2 |
| SUPPORT | 6 | RESISTANCE | 3 |

B2S and S2B produced **zero** POIs in this window. That is a property of the
window, not a defect: the frozen reversal detector needs a candidate at least
2.0x the largest of the prior three bars plus a 0.6 body efficiency, which this
range-bound session never produced. Recorded so a future zero is not mistaken for
a regression.

---

## 7. PROXIMITY PROJECTION, MEASURED

At close 4395.86 with 63 active POIs and capacity 8:

| # | Label | Dir | Top | Bottom | Distance |
| --- | --- | --- | --- | --- | --- |
| 1 | `M1 • BEAR PRESSURE` | bear | 4397.26 | 4396.61 | 0.75 |
| 2 | `M1 • BUY FVG ×4` | bull | 4395.07 | 4393.06 | 0.79 |
| 3 | `M1 • SELL FVG ×4` | bear | 4399.52 | 4397.17 | 1.31 |
| 4 | `M1 • BULL PRESSURE` | bull | 4394.52 | 4393.87 | 1.34 |
| 5 | `M1 • BUY FVG` | bull | 4397.86 | 4397.26 | 1.40 |
| 6 | `M1 • BEAR PRESSURE` | bear | 4398.37 | 4397.28 | 1.42 |
| 7 | `M1 • BEAR PRESSURE` | bear | 4399.30 | 4398.16 | 2.30 |
| 8 | `M1 • BUY FVG` | bull | 4398.37 | 4398.16 | 2.30 |

**Nearest omitted group:** `M1 • SELL OB + BEAR ENGULF • STRONG` at 2.39.

Eight slots cover 14 semantic POIs. Every drawn zone is within 2.30 of price,
against RC1's 199–259.

**Directional mix: 4 bull / 4 bear.** Descriptive only; no quota exists. An
earlier M15 measurement gave 12/0, so one-sidedness is data-dependent rather than
structural.

---

## 8. TABLE / BOX CONSISTENCY

The table stays semantic-POI oriented at capacity 8; boxes are group oriented at
capacity 8. On the live data all **8** table POIs are covered by the box set, and
the table carries registry indices rather than group ids.

A hazard was found and fixed here. The table's parallel arrays are keyed by **row
position**, not registry index, so reordering rows without re-keying every read
makes a row show one POI's identity with another's data. The first cut of the
patch did exactly that on three of nine fields. A permanent parametrized test now
asserts every printed row's payload belongs to its own POI.

---

## 9. SAMPLING AND LABEL AUDITS

Twenty randomly sampled visual groups traced back to registry fields:

| Check | Result |
| --- | --- |
| Identity errors | 0 |
| Top/bottom errors | 0 |
| Direction errors | 0 |
| Naming errors | 0 |
| Every active POI in exactly one group | true |

Across all 49 visual groups: **0** bare-numeric timeframes, **0**
`RALLY BASE RALLY`, **0** duplicate separators, **0** `UNKNOWN` rendered.
Specifically 0 labels beginning `1 •`, `5 •`, `15 •` or `60 •`.

---

## 10. SOURCE DIFF CLASSIFICATION

RC1 → V2 is **15 hunks**, all presentation. Mechanically: **0** writes to any
engine array (`poiType`, `poiZoneTop`, `poiZoneBottom`, P5 or P8 state) appear in
the diff. All 31 removed lines are the indicator title, the capacity input, stale
comments describing the old rule, the old selection loop, per-POI geometry reads
replaced by group reads, fill and border colors, label placement, and the table's
row-keyed parallel reads.

Categories used: proximity presentation, table projection, timeframe naming,
visual grouping, FVG cluster presentation, combined labels, label placement,
fill/border styling. **No semantic changes.**

---

## 11. DEFECTS FOUND IN MY OWN WORK

Recorded because each was caught by a check rather than by luck.

1. **`str.tonumber(p) == na`** — invalid in Pine v6. Caught by the TradingView
   compiler, not by offline tests, which exercise the Python model rather than
   Pine syntax.
2. **`• STRONG` appended to FVG cluster labels** — FVGs are TIER_NA so it is
   meaningless. Caught by the randomized Pine-port differential.
3. **Table parallel-array desync** on three of nine fields (section 8).
4. **UTF-16 BOM pasted as U+FFFD**, which silently broke `//@version=6` so the
   script compiled as Pine v1 and attached as "Untitled Script".

---

## 11a. GATE 2D — BASE RALLY MECHANICAL TRACE (COMPLETE)

The full chain, rendered group back to source candles, on the frozen live M1
capture:

| Field | Value |
| --- | --- |
| Registry index | **170** |
| Type | `BASE_RALLY` (code 7), bullish |
| Timeframe | M1 (host chart; P3 is single-timeframe) |
| Zone top | **4349.17** |
| Zone bottom | **4347.78** |
| Candidate time | 01:41 Europe/London |
| Availability | 01:44 Europe/London |
| Status | 1 — active |
| Rendered label | `M1 • BASE RALLY` |
| Merged into an FVG cluster | **no** |
| Group members | `[170]` — a singleton |

Source candles. `src_count` is 3, and the **last** source candle is the
departure, not part of the base:

| Bar (London) | Open | High | Low | Close | Role |
| --- | --- | --- | --- | --- | --- |
| 01:41 | 4348.13 | 4349.14 | **4347.78** | 4348.59 | base |
| 01:42 | 4348.59 | **4349.17** | 4348.14 | 4348.92 | base |
| 01:43 | 4348.92 | 4351.88 | 4348.82 | 4351.68 | departure |

`base_high = max(4349.14, 4349.17) = 4349.17` → zone top. **Exact.**
`base_low = min(4347.78, 4348.14) = 4347.78` → zone bottom. **Exact.**
Departure is bullish and closes 4351.68 above base_high 4349.17.

The author's stated golden matches on all three of top, bottom and origin.

**The visual half (2C) is still open.** At the capture's close of 4377.35 the
zone is 28.18 away and ranks **27th of 32** groups, so rendering it needs either
capacity ≥ 27 or a price state near the zone. Price never re-entered the zone
within the capture, and live price has since moved further away. Production
defaults were left at 8.

---

## 11b. GATE 4A/4C — OBJECT ARCHITECTURE AND LIFECYCLE (MODEL LEVEL)

**Architecture:** separate `box` and `label` objects, not box-integrated text.
`box.new` and `label.new` push into the dense parallel arrays `p7zBoxPoiIdx` /
`p7zBoxes` / `p7zLabels`; eviction calls `box.delete` and `label.delete` then
`array.remove` on all three. Declared budget is 500 boxes, 500 labels, 500 lines.
Capacity is 8 zone groups and 8 table rows, so the structural bound is 8 boxes
plus 8 labels from P7-Z, against a 500 budget.

Tables: 3 declared — the P7 summary (top-left), the P7 active-POI table
(bottom-right), and a debug table that is debug-gated.

`tests/unit/test_p7z_v2_object_lifecycle.py` exercises the V2 group projection
over 300 price moves on a 120-POI universe, repeated identical states, shrinking
universes, and a simulated M1→M5→M1→M15→M1→H1→M1 cycle repeated 12 times:

- counts never exceed capacity
- **conservation holds**: created − deleted == live, the invariant a real leak
  breaks
- identical state re-creates nothing
- boxes and labels never desynchronise
- no orphan survives a selection change; an empty selection releases everything
- counts do not drift across identical cycles

**This is model level.** It proves the selection and eviction contract the Pine
port implements; it is not a count of live TradingView chart objects.

---

## 11c. FOUR-GATE LIVE CLOSURE

Live object counting works: the Pine drawing primitives are reachable at
`study.graphics().dwgboxes()` → nested maps → `_primitiveById`, which exposes
each box's `left/right/top/bottom` and each label's `x/y/text`. All counts and
geometry below are read from that store, not from pixels.

**Architecture confirmed live:** V2 holds **8 boxes, 8 labels, 2 tables** at
capacity 8. P6 DEV draws nothing.

### Gate 1 — pan, zoom, scale

| Test | Result | Evidence |
| --- | --- | --- |
| Horizontal pan (~950px into history) | **PASS** | box geometry and labels byte-identical, counts 8/8/2 |
| Wheel zoom in and out | **PASS** | with zero new bars, `fullUnchanged: true` |
| Price-scale compress and expand | **PASS** | geometry and labels byte-identical |
| Vertical move | **PASS** | same, single price scale, no detachment |
| Runtime errors | **0** | |

An earlier run reported changed geometry after zoom. That was **new M1 bars
forming mid-test**, which shifts relative bar indices and advances `right` to the
new `time_close`. Re-run with a bar-delta guard showed geometry identical.
Selection did not re-rank from panning, as required.

### Gate 2 — Base Rally visual re-trace: BLOCKED, with proof

The golden POI's source bars are **2114 M1 bars back**, and `calc_bars_count` is
**1800** (confirmed in the study's own settings dialog). It is outside the live
calculation window, so it **cannot** be in the live registry.

This was not left as arithmetic. Visual capacity was raised 8 → 30 as the
sanctioned diagnostic; object counts rose to exactly **30 boxes / 30 labels / 2
tables**, and the rendered set contained **no BASE RALLY and no box overlapping
4344–4352**. Capacity was then restored to **8** and counts returned to 8/8/2.

So Gate 2C is impossible today for a reason unrelated to the visual layer. The
mechanical trace (11a) remains complete and exact.

### Gate 3 — remove / re-add

| Step | Result |
| --- | --- |
| V2 present in My Scripts before | **yes**, alongside `[RC1]` |
| Removed via explicit study menu → Remove | **yes** (Object Tree trash never used) |
| P6 DEV remained attached | **yes** |
| V2 still saved in My Scripts after removal | **yes** |
| Re-added from My Scripts | **yes** |
| Duplicate instances | **0** (exactly 1 V2, 2 studies total) |
| Capacity default after re-add | **8** |
| Objects after re-add | 8 boxes / 8 labels / 2 tables |
| Malformed labels | **0** |
| Runtime errors | **0** |

### Gate 4 — object leak

Counts at every checkpoint of the stress sequence:

| Checkpoint | boxes / labels / tables |
| --- | --- |
| M5 post-fix | 8 / 8 / 2 |
| M1 | 8 / 8 / 2 |
| M15 | 8 / 8 / 2 |
| H1 | 8 / 8 / 2 |
| M1 | 8 / 8 / 2 |
| after pan | 8 / 8 / 2 |
| after zoom | 8 / 8 / 2 |
| after price-scale | 8 / 8 / 2 |

Study instances stayed at 2 throughout. Counts also tracked capacity exactly
when it was raised to 30 and restored, which is the bound behaving as designed
rather than accumulating.

Post-stress identity sample of all 8 groups: **0** stale-timeframe labels (every
label `M1 • …`), **8 of 8** labels paired to their own box by matching anchor and
edge price, geometry all within ~3 of price.

**OBJECT_LEAK = FALSE.**

---

## 11d. NEW PRESENTATION DEFECT FOUND AND FIXED DURING GATE 1

Live inspection on M5 showed **8 boxes but only 6 labels**, and every label
sitting at the last bar index while the boxes started at six distinct origins.

Root cause: frozen RC1 calls `label.set_x(existing, time_close)` on every bar for
each already-drawn zone. The V2 corrective had changed label **creation** to
anchor at the zone origin but left that per-bar reposition intact, so only a
label created on the current bar ever sat at its origin and all older ones were
dragged to the right edge. That is the label pile Phase 8 was meant to remove; it
was only half-fixed.

The label-count shortfall had a second cause visible in the same data: when a
zone's origin lies outside the loaded bar range, its label cannot be placed.
Loading more M5 history restored 8 of 8.

**Fix:** the per-bar `label.set_x` was removed. The label now stays where
`label.new` put it for the life of the box; only the box's right edge tracks
`time_close`, which is the lifecycle contract.

**Verified live after redeploy:** label anchors now equal box left edges exactly,
`[-103, -97, -96, -88, -87, -71, 64, 289]` for both, where before the fix the
labels read `[-103, -71, 299, 299, 299, 299, 299, 299]`.

Three permanent tests pin it: the anchor equals the zone origin and never the
current bar; the anchor does not move while the box right edge provably advances;
and distinct origins never collapse onto a shared x.

---

## 11e. BLOCKING FINDING — RE10110 EXECUTION TIMEOUT ON M5

**Found while running the post-fix reload gate. This blocks closure.**

After the label-anchor fix was deployed, the V2 study entered a **failed** state
on **M5** and drew nothing — 0 boxes, 0 labels, 0 tables — while P6 DEV on the
same chart stayed healthy.

The error, read from the study's own status object:

```
RE10110 — "The script takes too long to execute. The time limit is 20 seconds."
```

This is an **execution-time limit**, not a logic error and not a compile error.

### Host map, same session, same chart

| Host | V2 state | Objects |
| --- | --- | --- |
| M1 | OK | 8 / 8 / 2 |
| **M5** | **FAILED (RE10110)** | **0 / 0 / 0** |
| M15 | OK | 8 / 7 / 2 |
| H1 | OK | 8 / 8 / 2 |

Reproduced across two clean reloads and a resolution switch. One intermediate
reading showed `failed: false`; that was a mid-recalculation state which then
settled to `failed: true` with `isCompleted: false`.

### Attribution — stated carefully

The label-anchor fix **removed** a per-bar `label.set_x` call, which can only
make execution cheaper, so it is not the cause. Earlier in the same session, and
before that fix, M5 rendered successfully (8 boxes, 6 labels). Between those two
observations the market fell roughly 90 points, which churns structure and raises
the active-POI population.

The most likely cause is the V2 **grouping loop itself**. Frozen RC1 selected
zones with a first-N slice; V2 forms visual groups by growing each group against
a running envelope until closure, which is roughly quadratic in the active-POI
count per bar. M5 spans about 6.25 days of structure against M1's 30 hours at the
same 1800-bar budget, so its active population is far larger. That puts V2 near
the 20-second ceiling, and market conditions pushed it over.

RE10110's 20-second limit is also **plan-dependent** — this account is on Basic.
A higher tier raises the ceiling, but that does not make the algorithm safe.

### Status

**V2 is NOT cleared for release.** M1, M15 and H1 are healthy, but a visual layer
that can silently render nothing on a supported host is a release blocker. The
grouping loop needs a complexity reduction (or an explicit active-set bound
before grouping) and then a re-run of the host matrix. No such change was made in
this pass: diagnosing it correctly came first, and altering the algorithm under a
closure request would have been the wrong call.

---

## 12. OUTSTANDING

Gates 1, 3 and 4 are now closed with live evidence (11c). Two items remain.

- **Gate 2C — visual re-trace of the golden Base Rally.** Blocked, with proof
  (11c): the POI is 2114 M1 bars back against an 1800-bar calculation window, so
  it is not in the live registry and no capacity setting can surface it. It will
  become testable only against a capture where the zone is inside the window, or
  a bar-replay state near 4347.78–4349.17. The mechanical trace (11a) is
  complete and exact.
- **Reload inside the Gate 4 stress sequence.** The standalone reload matrix
  passed earlier on all four hosts. Repeating it inside the stress run was
  declined: the chart layout carried unsaved state, and force-discarding it
  risked stripping V2 from the user's chart. Not attempted rather than risked.

**M1 host support: VERIFIED** on the visual-behaviour evidence in this document —
runtime, reload, host switching, pan, zoom, price scale, vertical move, remove
and re-add, object lifecycle, registry mapping, table mapping, zone geometry,
naming, clustering and P8 coexistence.

**V2 overall: NOT CLEARED FOR RELEASE**, because of the RE10110 timeout on M5
(11e). That is a separate axis from the visual behaviour above: the mapping,
naming, clustering and lifecycle work is sound and proven, but the grouping
loop's execution cost is not, and it fails closed by drawing nothing.

Also still open:

- **Gate 2C** — visual re-trace of the golden Base Rally. Blocked (11c): the POI
  is 2114 M1 bars back against an 1800-bar window.
- **BASE_RALLY visual type acceptance.** Five genuine BASE_RALLY POIs exist in
  the latest 500-bar M1 window (indices 100, 125, 173, 207, 227), but **all five
  are terminal**, so none is render-eligible at the current close. Verifying the
  type live needs a bar-replay state inside the window where one is still active.
  No synthetic POI was invented.
