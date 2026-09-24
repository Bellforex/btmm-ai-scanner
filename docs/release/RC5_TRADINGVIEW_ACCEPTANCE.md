# RC5 — TRADINGVIEW ACCEPTANCE RUNBOOK

Everything needed to run the Pine runtime gates the moment the UI becomes
usable, plus the structure-coordinate decision pack so that question costs one
inspection rather than a debate.

**Current availability: BLOCKED.** A chart loads on the authorized account but
the automation tab reports `document.hidden === true`, all seven canvases at
the 300×150 default and zero legend rows, so TradingView never lays the
renderer out. This is a background-tab/rendering condition, not an
account-selection failure, and it has been re-verified. Do not re-diagnose it.

---

## 0. PRECONDITION — all four, every time

```js
JSON.stringify({
  user: window.user && window.user.username,
  hidden: document.hidden,
  canvases: [...document.querySelectorAll('canvas')].map(c => c.width+'x'+c.height),
  legend: document.querySelectorAll('[data-name="legend-source-item"]').length,
})
```

| requirement | value |
| --- | --- |
| `user` | exactly **`bellcare1994`** |
| `hidden` | **`false`** |
| canvases | real dimensions, **not** `300x150` |
| legend | **> 0** |

Account: **`bellcare1994`**. Layout: **`BAH-RC5-LAB`**.
**Never** a state-changing action as `STEVECRYPTO1995`.

Three traps that make the check non-optional:

* a screenshot is captured over CDP and renders correctly **even while the page
  reports itself hidden**, so it cannot establish that the chart is laid out;
* `document.hasFocus()` can be `true` while `document.hidden` is also `true` —
  focus is not visibility;
* browser display names have changed before. Key on the **deviceId** and verify
  `window.user.username` in the page.

---

## 1. VIEW / CORE GATES

| gate | attach | expect |
| --- | --- | --- |
| G1 | VIEW alone | structure overlay draws; no POI boxes, no tables |
| G2 | CORE alone | POI zones and the trendline layer draw; no structure overlay |
| G3 | **CORE + VIEW** | the production pair — both, no duplicates, no missing objects |
| G4 | CORE + PANEL | tables draw; PANEL draws no market-space objects |

Mind the **2 live connections** cap on the Basic plan, and work from exactly one
tab: a background tab never paints.

## 2. P2 / P3 PARITY

Run in this order. The bootstrap cases come **first** on purpose: a port that
implemented only the transition half would pass every real-data check, because
all three captures have zero Bases in their bootstrap-only window.

1. synthetic RBR bootstrap
2. synthetic DBD bootstrap
3. golden EURUSD M15 DBD
4. M45 families
5. H3 families
6. transition history
7. future-transition guard
8. prefix stability

Output arrives through the compacted `log.info` liveness line
(`bootDir,time:family,…`) at `barstate.islast`. **Nothing may be added to CORE
to make a run easier to read** — 73 tokens of headroom is not development
space.

## 3. P4 GOLDEN OWNERSHIP

On the golden M15 formation:

* `BASE_DROP` / DBD → **PRIMARY**
* `BEARISH_PRESSURE_WICK` → **SUBORDINATE**
* `DOJI` → **SUBORDINATE** where a raw candidate exists
* `EVENING_STAR` → **SUBORDINATE** through exact co-extension
* after activation: **0** independent P5 evaluations and **0** independent P8
  events from any subordinate

---

## 4. STRUCTURE COORDINATE DECISION PACK (S1 / S2)

**Do not change S1 or S2 without visible evidence.** This section exists to
make the eventual decision cost one inspection.

### The question

`brokenSwingKey` is documented at the type as `== SwingRec.pivotEndTime`, so
the HH/HL/LH/LL label (S1) and the BOS/CHOCH connector's left endpoint (S2)
already use the **same** quantity: the open time of the pivot's LAST candle.
Neither uses an availability time, so the "availability controls WHEN, event
controls WHERE" rule already holds.

What is open is *which* event time — the pivot's **first** candle
(`wOpenT[pivotStartIdx]`, which is what Python orders swings by) or its **last**
(`pivotEndTime`, which P1 also calls its swing identity). The codebase argues
both ways and Python publishes no label coordinate at all, because it has no
renderer.

### Why this is cheap to settle — MEASURED

**The two candidates can only differ on a MULTI-CANDLE pivot.** On a
single-candle pivot, start and end are the same bar and nothing moves.

On the author's 300-bar M15 EURUSD capture there are exactly **2 multi-candle
swings out of 69** (2.9%):

| # | swing | price | pivot START | pivot END | availability |
| --- | --- | --- | --- | --- | --- |
| 1 | SWING_HIGH | 1.14691 | **2026-09-18 15:15** | **2026-09-18 15:30** | 2026-09-18 16:30 |
| 2 | SWING_HIGH | 1.14649 | **2026-09-22 06:45** | **2026-09-22 07:00** | 2026-09-22 08:00 |

Every other label on that chart is identical under either rule.

### The inspection

Open the M15 EURUSD chart with the structure overlay and look at **those two
labels only**. For each, the label currently sits on the **END** bar.

> Does the label sit on the bar that visually IS the swing high, or one bar to
> its right?

* If it sits on the visual extreme → current behaviour is correct, **S1 and S2
  close as NO CHANGE**.
* If it sits one bar late → the coordinate should be
  `wOpenT[pivotStartIdx]`, and the correction is **VIEW-only**.

S2 follows automatically: the connector's left endpoint resolves through the
same field, so it can only differ for a broken swing that is itself one of
these multi-candle pivots.

### If a defect is proven

Make the smallest **VIEW-only** change — `rc5_view_presentation.pine`,
regenerated through `tools/rc5_compose.py`. CORE detection is untouched and
CORE's token count must not move. Re-run extraction parity afterwards.

### For reference — the first five transitions in that capture

| transition | break bar | availability |
| --- | --- | --- |
| BULLISH_BOS | 2026-09-18 19:00 | 19:15 |
| BEARISH_CHOCH | 2026-09-20 21:15 | 21:30 |
| BEARISH_BOS | 2026-09-21 03:00 | 03:15 |
| BEARISH_BOS | 2026-09-21 05:30 | 05:45 |
| BULLISH_CHOCH | 2026-09-21 08:15 | 08:30 |

---

## 5. MTF SMOKE, after the gates pass

M5 · M15 · M30 · M45 · H1 · H3 · H4 — no runtime failures, POIs stay anchored
through pan/zoom/reload, structure stays coherent, one external trendline, no
duplicate structure objects, CORE+VIEW compatible.

## 6. WHAT THIS RUNBOOK MAY NOT DO

No publication. No merge. No BAH republish. No modification of the `bellforex`
layout. No state-changing action on `STEVECRYPTO1995`.
