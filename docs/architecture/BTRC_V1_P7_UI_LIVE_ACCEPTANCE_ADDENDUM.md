# BTRC-V1 P7-A — Live Acceptance Addendum

Status: **P7-A — PARTIAL: M5 + pan/zoom/scale + reload ACCEPTED; H1 BLOCKED by a
genuine, pre-existing, P5-inherited defect (out of P7 scope); zero-active
state NOT naturally observed (synthetic proof relied on)**
Branch: `pine-p4-btmm`
References: implementation closure `5c53370`
Addendum recorded: 2026-09-04

---

## 1. Source freeze — confirmed, unmodified throughout this session

```
HEAD                 5c53370 (unchanged throughout this addendum)
git status --short   (clean at every checkpoint)
P7 source SHA256      856b6c46ca3d8b02d9429ecd964987faffa5ec91b19829b0bdaf616b157bd20e
                       (identical before and after every live test in this addendum)
```

**No source edits were made.** Every observation below is against exactly
the script closed at `5c53370`.

## 2. Zero-active-POI live state — NOT OBSERVED, per the documented fallback

The live host POI registry held 89–134 active POIs across every timeframe
and pan/zoom state exercised this session (see Section 4). No natural
zero-active window was reachable without altering semantic configuration,
which this addendum was explicitly told not to do. Per the governing
brief's own fallback rule, this is recorded as:

```
LIVE ZERO STATE = NOT OBSERVED
```

Reliance is placed on the existing synthetic proof instead — not a new
directed 5→2→0 test, but the combination already on record: (a) the
`array.clear(p7PoiIdx)` and its seven sibling-array clears are unconditional
source statements at the top of every `barstate.isconfirmed` pass (confirmed
present by direct reading, `tradingview/btmm_poi_btrc_scanner_p7_dev.pine`,
immediately before the active-POI loop), and (b) the summary table's
zero-state branch (`else: for r = 3 to 11: f_row(..., "-", "-")`, gated on
`p7HasData`) is present and reachable by inspection. This is disclosed as
static/source-level evidence, not a live observation — exactly the
distinction Section 6 of `BTRC_V1_P7_UI_CLOSURE.md` already drew.

## 3. M15 baseline

Feed `FXCM:XAUUSD`, layout `bellforex`. Recorded twice this session (once
before, once after a full reload — see Section 8): active count **89** both
times, POI index range **522–577**, footer `8 shown / 89 active`. Summary
panel: Breakout `EXPLOSIVE BREAK`, Pullback `NONE`, Session
`LONDON/NY OVERLAP`, Volatility `HIGH (abnormal)`. Both tables rendered
exactly once, correctly positioned (top-left / bottom-right).

## 4. M15 → M1 → M5 → M15 — PASS

An accidental first click landed on **1m**, not 5m (adjacent toolbar
buttons) — kept as extra evidence rather than discarded, since it is a more
aggressive timeframe change than M5 alone:

* **M1**: host TF display updated to `1`. Active count **125**, entirely
  different POI index range (**239–253**) from the M15 baseline. Summary
  panel refreshed (`DECELERATING` / `EXPLOSIVE BREAK` / `NONE` /
  `LONDON/NY OVERLAP` / `HIGH`). No M15-stale cells, no duplicate table.
* **M5** (the requested case): host TF display updated to `5`. Active count
  **134**, a third distinct POI index range (**2–12**, low indices — a
  fresh POI history at this host resolution). Summary panel refreshed
  (`EXPLOSIVE BREAK` / `NONE` / `LONDON/NY OVERLAP` / `NORMAL`). Footer
  read `8 shown / 134 active`. No M1-stale cells, no duplicate table.
* **Return to M15**: host TF display back to `15`. Active count **89** —
  exactly the Section 3 baseline, POI range back to **522–577** — proving
  the M15 state was not corrupted by the M1/M5 excursions, and that the
  panel is genuinely re-deriving its state from the current host context
  each time, not carrying stale values forward.

**M5 timeframe requirement: PASS.**

## 5. M15 → H1 — BLOCKED by a genuine, pre-existing, P5-inherited defect

Switching the host timeframe to **H1** produced a **real runtime error**
on `BTMM + POI + BTRC Scanner [P7 DEV]`'s legend row (a red "!" icon, not a
rendering artifact — clicking it opened TradingView's own runtime-error
popup):

```
Runtime error: RE10041
Error on bar 0: Cannot access the 'P5TransportExt.dispWindowCount' field of
an undefined object. The object is 'na'.
  at f_p5T3Mom():5250
  at #main():5844
```

**This is not a P7 defect.** `f_p5T3Mom` is a P5 function; the exact crash
site (`int n = ext.dispWindowCount`, line 5249 of both files) was confirmed
byte-identical between `btmm_poi_btrc_scanner_p5_dev.pine` and
`btmm_poi_btrc_scanner_p7_dev.pine` by direct comparison. P7 never modifies
this function (already mechanically proven in
`tests/unit/test_p7_semantic_equivalence.py`). The mechanism, as best can
be inferred without editing anything to test it further: `f_p5T3Mom` is
called with `m15Ext`, the UDT payload from the M15 `request.security`
context; on bar 0 of an **H1-hosted** chart, that sub-context has
apparently not yet delivered its first value, so `m15Ext` is still `na` at
the moment `f_p5T3Mom` first runs. Every prior closure in this campaign
(P1 through P7) was built and tested exclusively with **M15 as the host
timeframe** — this session's H1 test appears to be the first time this
exact host/sub-context timing edge has ever been exercised.

Per the explicit standing instruction not to touch P5, **no fix was
attempted.** The chart was returned to M15 immediately (confirmed clean:
no error icon, active count back to 89) rather than left in a failed state.

```
H1 timeframe requirement: FAIL (real, reproducible, pre-existing defect;
                                  inherited from the closed P5, not
                                  introduced by P7; out of this addendum's
                                  scope to fix)
```

This finding is recorded here as a durable pointer for a future P5-scoped
session — it is a real defect, not environment noise, and should not be
waved away by the Section 7-of-the-closure-doc "environment finding"
narrative.

## 6. Pan / zoom / vertical-scale matrix — PASS (M15)

All four exercised on the M15 baseline, using the chart's own zoom
in/out controls, a horizontal click-drag, a price-scale drag, and a
vertical chart drag:

* **Horizontal pan**: candles shifted under the fixed tables; both P7
  tables stayed pinned at `top_left`/`bottom_right` throughout; active
  count updated live (91) as the pan revealed different history; no
  table duplication, no drift.
* **Wheel/control zoom out**: candle spacing compressed (visible date
  range widened from `9–4` to `19–…–Sep 3`); tables remained fixed; no
  detached labels/lines/boxes.
* **Zoom in**: control clicks registered but produced no visually
  distinguishable change from the zoomed-out state in this pass (a
  measurement gap, not a failure — the tables' anchoring, the property
  actually under test, was unaffected either way).
* **Price-scale (vertical) zoom**: a drag on the right-side price axis
  compressed/expanded the visible price range (`4,280–4,520` →
  `4,220–4,580`, TradingView's own auto-scale `A`/`L` indicators
  appeared); no second price scale appeared; both tables stayed exactly
  in place.
* **Vertical chart movement**: a vertical drag on the canvas (TradingView
  interpreted it as a measure-tool action, which is itself informative —
  it still produced a real price/time cross-reference) left both tables
  undisturbed.
* **Return to normal**: "Reset chart view" + "scroll to most recent bar"
  restored a working, rendering chart with both tables intact (the
  custom price-scale drag was not fully reverted by "reset chart view" —
  expected TradingView behavior, since that button resets time-axis
  zoom/pan, not a user's own price-scale drag, and is not evidence of any
  P7 defect).

**No second price scale appeared at any point** — the specific symptom the
already-closed `BTRC_V1_P7_VISUAL_ANCHOR_DEFECT.md` closed. **That defect
remains closed.**

```
Pan/zoom/scale requirement: PASS
```

## 7. Resource / runtime status (unchanged from the implementation closure)

```
plots                63  (unchanged)
request.security      6  (unchanged)
P7 new plots           0
P7 new semantic requests  0
table.new              3  (P5 DEV baseline 1 + P7's 2)
label.new / line.new / box.new   1 / 2 / 1 (unchanged from P5 DEV)
```

Runtime warnings observed: the pre-existing "Heavy script... close to your
plan's runtime limit (20s)" banner, on M15/M1/M5 — expected, already
classified GO by P5/P6 precedent. Runtime **failures** observed: **one**
(`RE10041` on H1 — Section 5). No other runtime failure was observed on
M15, M1, or M5 across this entire addendum.

## 8. Reload confirmation

A final full page reload (`F5`), on M15, with only P6 DEV + P7 DEV
attached: candles rendered, both tables reconstructed exactly once each
(no duplicates), Object Tree confirmed the identical attached set
(`BTMM + POI + BTRC Scanner [P6 DEV]`, `BTMM + POI + BTRC Scanner [P7 DEV]`,
plus the same 11 baseline drawing objects — 6 Text, 1 Rectangle, 2
Trendline, 1 Horizontal ray — unchanged in count).

## 9. Regression

```
tests/unit/test_p5_atomic_capture_replay_parity.py   PASS (P5 digest H1 351473241 / H2 335238294 unchanged)
tests/unit/test_p6_real_data_parity.py                 PASS (30/30 exact)
tests/unit/test_p7_semantic_equivalence.py              PASS (8/8 -- source is byte-identical to 5c53370)
full suite                                              see commit log for the exact count recorded at commit time
```

No source file changed during this addendum, so no new run against P5/P6/P7
Pine sources was needed beyond confirming the SHA256 in Section 1.

## 10. Gate

```
P7_SOURCE_UNCHANGED_THIS_SESSION          TRUE   (SHA256 identical throughout)
P7_ZERO_ACTIVE_LIVE_OBSERVED              FALSE  (not naturally reachable; synthetic proof relied on, Section 2)
P7_M5_LIVE_MATRIX                         PASS
P7_M1_LIVE_MATRIX                         PASS   (bonus: not required, exercised anyway)
P7_H1_LIVE_MATRIX                         FAIL   (RE10041, real, pre-existing, P5-inherited, out of scope)
P7_PAN_ZOOM_SCALE_LIVE_MATRIX             PASS
P7_RELOAD_CONFIRMATION                    PASS
P7_VISUAL_ANCHOR_DEFECT                   REMAINS CLOSED (no second price scale observed at any point)
P5_SEMANTICS_UNCHANGED                    TRUE   (digest unchanged; the H1 defect is a PRE-EXISTING P5 defect this
                                                    session discovered, not a regression -- P5's own closure evidence
                                                    was never gathered on an H1 host chart)
P6_SEMANTICS_UNCHANGED                    TRUE   (30/30 unchanged)
```

**P7 FULLY CLOSED: FALSE.** One of the three disclosed evidence gaps
(H1) resolved to a genuine, reproducible defect rather than a pass — that
is a real result, not a process failure, and is recorded honestly rather
than suppressed to force a clean "fully closed" status. M5 and pan/zoom/
scale are genuinely closed. Zero-active state remains unverified live
(fallback proof only, as pre-authorized).

## 11. What should happen next (not performed here — out of this
addendum's authorized scope)

* A P5-scoped session (explicitly authorized to touch P5, which this one
  was not) should investigate `RE10041` on non-M15 host timeframes and
  decide whether P5's closure needs a documented host-timeframe
  restriction (e.g. "M15 host only, by design") or an actual fix to
  `f_p5T3Mom`'s `na`-guard. Until then, **P7 DEV / P5 DEV should not be
  attached to a non-M15 host chart.**
* If P5 is later fixed or the M15-only restriction is formally documented,
  re-run Section 5's H1 test to complete this addendum.
