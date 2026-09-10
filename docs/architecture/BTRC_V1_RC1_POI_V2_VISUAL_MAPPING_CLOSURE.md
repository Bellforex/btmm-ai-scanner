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

## 12. OUTSTANDING

Not performed, and not claimed:

- Pan, wheel zoom, price-scale and vertical-move tests (need a foreground tab;
  the tab was hidden for the later part of this pass and hidden tabs do not paint).
- Visual re-trace of the golden Base Rally (section 4).
- Remove / re-add of the V2 study.
- Object-leak stress beyond study-count checks across reloads.

**M1 host support: NOT YET CLOSED.** Runtime, reload, host switching, registry
behaviour, table, zones, geometry, naming and clustering all pass. The visual
interaction gates above do not yet have evidence.
