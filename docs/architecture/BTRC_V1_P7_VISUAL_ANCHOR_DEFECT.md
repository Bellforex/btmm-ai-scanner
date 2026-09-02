# BTRC-V1 P7 — Visual Anchor Defect

Status: **OPEN**
Raised by: the author, from direct observation on TradingView
Recorded: 2026-09-01
Branch: `pine-p4-btmm`

This note exists so the defect cannot be lost behind the P5/P6 work. It records
the symptom, what the source already does correctly, and where the cause is
therefore most likely to be. **No fix is attempted here**, and no semantic code
may be touched to address it.

---

## 1. Symptom

When the chart is moved — panned, or repositioned vertically — the scanner's
candle-related markers **do not move with their candles**. Markers observed to
detach include the `SH` / `SL` swing labels and the displacement triangles.

The top-right diagnostics table is a TradingView `table`, which is
screen-anchored by design and is **not** part of this defect.

## 2. What must stay attached, and what may not

| Element | Primitive | Must track the candle? |
|---|---|---|
| `SH` / `SL` swing labels | `label.new` | **yes** |
| equal-level lines | `line.new` | **yes** |
| trendlines | `line.new` | **yes** |
| S/R zone boxes | `box.new` | **yes** |
| displacement triangles | `plotshape` | **yes** |
| diagnostics table | `table.new` | no — screen-fixed is correct |

Acceptance rule, frozen now:

> same semantic event + same timestamp + same price = same chart anchor

under pan left, pan right, vertical move, price-scale drag, zoom in, zoom out,
history loading, timeframe change and return, and reload. Moving the viewport
must never move a marker independently of its source candle.

## 3. What the source already does — and why that matters

Read out of `tradingview/btmm_poi_btrc_scanner_p4_dev.pine`:

```
indicator(..., overlay = true, ...)

label.new(x = s.pivotEndTime,  y = s.price,          xloc = xloc.bar_time, ...)
line.new (x1 = e.firstTime,    y1 = e.representativePrice,
          x2 = e.confirmationTime, y2 = e.representativePrice,
                                                     xloc = xloc.bar_time, ...)
line.new (x1 = tl.anchor1Time, y1 = tl.anchor1Price,
          x2 = tl.anchor2Time, y2 = tl.anchor2Price, xloc = xloc.bar_time, ...)
box.new  (left = srd.confirmationTime, top = srd.zoneTop,
          right = time_close,          bottom = srd.zoneBottom,
                                                     xloc = xloc.bar_time, ...)
plotshape(..., location = location.belowbar, ...)
plotshape(..., location = location.abovebar, ...)
```

Every drawn object already uses:

* **x = a semantic timestamp** with `xloc.bar_time` — never `bar_index`, and
  never a rolling-window array index. A local window index used as a permanent
  anchor is the classic cause of this symptom, and it is **not** what this source
  does.
* **y = a real price** — `s.price`, `representativePrice`, `anchor1Price`,
  `zoneTop` / `zoneBottom` — never an indicator-local numeric value.
* Shapes use `location.abovebar` / `location.belowbar`, which TradingView anchors
  to the bar automatically.

All **29** `plot()` calls are `display = display.data_window`, so none of them
contributes to the visible price scale. The script therefore publishes no
plotted series that could pull the scale away from the candles' range.

**This narrows the diagnosis considerably.** The coordinates are already the
correct ones, so the defect is unlikely to be a coordinate-choice bug in the
Pine and is most likely a question of *which price scale the objects are being
interpreted against*.

## 4. Candidate owners, most likely first

1. **Scale ownership (leading hypothesis).** If the indicator is pinned to its
   own scale — "Pin to left scale" / "Pin to right scale" / "No scale" in the
   TradingView object tree, or an equivalent layout setting — then its price
   coordinates are mapped onto a different vertical axis than the candles.
   Dragging the price scale or moving vertically then moves the two
   independently, which is exactly the reported symptom. This is a chart/layout
   property, not necessarily a source property.
2. **A stale duplicate study on the layout.** An older copy of the scanner left
   attached would draw from its own state and drift. The layout is known to have
   carried several scanner versions during P2–P4.
3. **`force_overlay` / pane assignment** on individual objects.
4. **Object rebuild identity** — objects re-created against a re-derived anchor
   rather than the original semantic time. The source keeps drawing-object arrays
   (`swingLabelObjs`, `eqLineObjs`, `srBoxObjs`, `tlLineObjs`); their rebuild path
   is worth reading even though the anchors themselves are semantic.

Ruled out by reading the source, unless the live check contradicts it:
`bar_index` anchoring, rolling-window index anchoring, indicator-local y values,
and scale distortion from a plotted series.

## 4a. MEASURED: the study is on a different price scale from the candles

Read live from the chart model on `bellcare1994` / `bellforex` / FX:XAUUSD M15:

```
mainSeries            priceScale id = ivPMGXXDSKBJ    autoScale = false
P3 DEV scanner        priceScale id = KAzaqt6eQw3n    autoScale = true
P6 FEASIBILITY LAB    priceScale id = 0Yabu85nIh35    autoScale = true
```

**The scanner does not share the candles' price scale.** Its labels, lines and
boxes are positioned by real price — §3 confirmed that — but those prices are
mapped onto `KAzaqt6eQw3n`, a *different vertical axis* that auto-scales on its
own, while the candles sit on `ivPMGXXDSKBJ` with autoscaling switched off.

Two axes, scaling independently, is precisely a mechanism that makes correctly
anchored objects drift away from their candles when the viewport moves. This
promotes scale ownership from "leading hypothesis" to **measured fact**, and it
is consistent with every §3 finding: the coordinates were never the problem.

`P7_ROOT_CAUSE_CANDIDATE_PRICE_SCALE = TRUE`

`P7_DUPLICATE_STUDY_PRESENT = TRUE` was also confirmed — `P3 DEV` and
`P3 ATOMIC PARITY` were both attached simultaneously. That is a separate
candidate and is not yet ruled in or out.

### What was changed on the chart, and what was not

To free an indicator slot on the Basic plan (2 maximum) and to test the scale
hypothesis:

* `P3 ATOMIC PARITY` was **removed from the chart**. Its saved script is
  untouched and can be re-added from the editor's script list.
* `P3 DEV` was moved onto the main price scale with
  `study.setPriceScale(mainSeries.priceScale())`, verified: both now report
  `ivPMGXXDSKBJ`. This is a chart/layout property, **not** a source change.
* `P6 FEASIBILITY LAB` was added (it declares `overlay = false`, so it occupies
  its own pane and reshuffles the layout — worth removing before judging the
  visual result).

No Pine source was modified and no saved script was deleted.

### 4b. MEASURED: a freshly added scanner gets the CORRECT scale

The decisive follow-up. Both scanners were removed from the chart and `P4 DEV`
was re-added from its saved script:

```
mainSeries                 ivPMGXXDSKBJ   autoScale false
P4 DEV, freshly added      ivPMGXXDSKBJ   autoScale false   <-- SAME
Dividends / Splits / Earnings (built-in overlays)
                           ivPMGXXDSKBJ   autoScale false
P6 FEASIBILITY LAB (overlay = false)
                           m2VoDvPjBbsY   autoScale true    <-- correctly its own
```

**A freshly added scanner shares the candles' price scale.** So the source
default is correct, and `overlay = true` does what it should. The lab, declared
`overlay = false`, correctly gets its own scale in its own pane — which is the
control showing the measurement distinguishes the two cases.

**This changes the ownership of the defect.** The `KAzaqt6eQw3n` assignment seen
on the P3 DEV instance was **saved-layout state, not a source defect** — the
study had been separated onto its own scale at some point in that layout, very
plausibly during the period when two scanner copies were attached at once
(`P7_DUPLICATE_STUDY_PRESENT = TRUE`), which is exactly when TradingView is
liable to hand the second instance its own axis.

Consequences:

* **No Pine source change is required or justified.** A source "fix" would be
  changing code that already behaves correctly.
* The remedy is layout hygiene: one scanner instance, on the main price scale.
* The two candidate causes are now linked rather than independent — the
  duplicate study is the plausible *origin* of the scale split.

### Current chart state

`P4 DEV` alone, on `ivPMGXXDSKBJ`, status 2, not failed. `P3 DEV`, `P3 ATOMIC
PARITY` and the feasibility lab were removed **from the chart only**; every
saved script is intact.

### Why this is NOT yet a closed defect

The mechanism is gone — one scanner, one shared scale — and the source is
exonerated. But the §2 acceptance matrix (pan, vertical, scale drag, zoom,
history load, timeframe switch, reload) has **not** been run, and a measured
cause plus a corrected state is not a verified fix. The defect stays **OPEN**
until the author confirms markers now track their candles under those
operations, which is a visual judgement the chart is now correctly set up for.

## 5. Investigation plan (P7, remaining)

1. ~~Read the live study's price-scale assignment~~ — **done, see §4a: the
   scanner was on its own scale.**
2. Remove the feasibility lab so the layout is scanner-only, then run the §2
   acceptance matrix with the shared scale in place.
3. If markers still detach, test the duplicate-study candidate by re-adding
   `P3 ATOMIC PARITY` and comparing.
4. Classify the owner: `PRICE_SCALE`, `X_COORDINATE`, `Y_COORDINATE`,
   `OBJECT_REBUILD`, `OVERLAY`, `TABLE_CONFUSION`, `OTHER`.
5. Apply a **rendering-only** correction.
6. Re-run the full semantic suite and the P4 atomic hashes; they must be
   **unchanged**. A visual fix that moves a canonical hash is not a visual fix.
7. Run the anchor matrix in §2 across all listed viewport operations.

## 6. Scope rule

The visual defect is **not** evidence that P1 measurements, P2 structure, P3 POI
or P4 BTMM semantics are wrong. Those are closed against byte-exact real-data
parity, which is computed from semantic records and is entirely independent of
how anything is drawn. Only an explicit semantic-coordinate comparison could
implicate them, and none has been made.

Default classification: **rendering / scale / coordinate ownership.**

## 7. Gate

`P7_VISUAL_ANCHOR_DEFECT = OPEN`

The scanner must not be described as production-ready while this stands, even
though every semantic layer beneath it is closed.
