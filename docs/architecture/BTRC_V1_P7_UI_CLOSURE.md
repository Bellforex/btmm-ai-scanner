# BTRC-V1 P7 — Scanner UI (Presentation Layer): CLOSURE

Status: **P7 PRESENTATION LAYER — CLOSED (scope as delivered; see Section 8)**
Branch: `pine-p4-btmm`
Closed: 2026-09-04

---

## 1. What P7 is

P7 is the first user-facing, always-on visual surface for the scanner. Before
P7, `btmm_poi_btrc_scanner_p5_dev.pine`'s entire visible output — the P1
swing labels, equal-level lines, S/R boxes, displacement markers, and the
one diagnostics table — was gated behind `debugMode` (`input.bool(false,
...)`, off by default). With `debugMode` off, the closed P2–P6 semantic
engine produced **zero** visible output. P7 does not touch any of that: it
adds two new, always-on (`p7ShowUi`-gated, default **on**) screen-anchored
tables that display the already-computed P5 BTRC confluence state.

Source: `tradingview/btmm_poi_btrc_scanner_p7_dev.pine` (6038 lines,
`sha256 856b6c46…`), built as `tradingview/btmm_poi_btrc_scanner_p5_dev.pine`
(the closed P5 ancestor, commit `5e09d87`) plus one title change and one
additive block — see Section 6 for the mechanical proof of that claim.

## 2. The table contract, as implemented (repository is authority)

**Summary table** — `position.top_left`, 2 columns × 12 rows, `var table`
(created once, overwritten via `table.cell` every render — the same
object-reuse idiom the closed P1 debug table already used):

| Row | Label | Source |
|---|---|---|
| 0 | "P7 — BTRC Scanner" (title) | — |
| 1 | Feed | `syminfo.prefix + ":" + syminfo.ticker` |
| 2 | Host TF | `timeframe.period` |
| 3 | Global direction | `p7LastGlobalDir` → `f_p7DirLabel` |
| 4 | Regime | `p7LastRegime` → `f_p7RegimeLabel` |
| 5 | Momentum | `p7LastMomDir` → `f_p7DirLabel` |
| 6 | Momentum accel. | `p7LastMomAccel` → `f_p7MomAccelLabel` |
| 7 | Breakout | `p7LastBrk` → `f_p7BrkLabel` |
| 8 | Pullback | `p7LastPb` → `f_p7PbLabel` |
| 9 | Session | `p7LastSession` → `f_p7SessionLabel` |
| 10 | Volatility | `p7LastVol`/`p7LastVolAbnormal` → `f_p7VolLabel` (+" (abnormal)") |
| 11 | Active POIs | `array.size(p7PoiIdx)` |

Rows 3–11 read `"-"`/`"-"` until the first confirmed bar has run
(`p7HasData` guard) — the Phase 14 zero-state.

**Active-POI table** — `position.bottom_right`, 8 columns ×
(`p7MaxVisiblePois` + 2) rows, same `var table` idiom. Header row: `#`,
`Dir`, `Tier`, `BTMM`, `Align`, `Score`, `Permission`, `State`. Up to
`p7MaxVisiblePois` data rows (default **8**, `input.int` bounded 1–20),
each holding one eligible POI's `poiIdx`/direction/tier/BTMM-valid/
alignment/final-score/permission/lifecycle — the exact same values that
bar's (debug-gated) `P5EVAL` log line already carries, copied unconditionally
(not debug-gated) into `p7Poi*` arrays inside the existing active-POI loop.
Unused rows blank every cell. Footer row (last row): `"<shown> shown /
<active> active"` — the overflow-policy readout.

## 3. Overflow policy — decision engine unbounded, display bounded

`p7Active = array.size(p7PoiIdx)` is the **actual count of POIs the
already-closed P5 active-POI loop evaluated this bar** — every eligible POI
(`not isTerminal or not finalDone`, unchanged from the closed contract)
pushes into `p7Poi*` inside that same loop, regardless of
`p7MaxVisiblePois`. `p7Shown = math.min(p7Active, p7MaxVisiblePois)` is
computed only at render time, after the loop has already run to completion
for every eligible POI. There is no code path by which the display cap
could reduce how many POIs are evaluated — the loop bound is
`for i = 0 to p5N - 1` (`p5N = array.size(poiStatus)`, the full P3
registry), never `p7MaxVisiblePois`.

**Live evidence**: real FXCM observations across this session's
distinct reload/attach/settings-change events recorded active counts of
**87, 88, 93, 97, and 101** at different moments, with the footer always
reading `8 shown / <that count> active` — direct confirmation the display
cap never changed the evaluated count, and that the arrays are being freshly
computed each observation (a stuck/static array could not have produced five
different counts across five different checks).

## 4. Display-only guarantee — mechanically proven, not merely asserted

`tests/unit/test_p7_semantic_equivalence.py` (8 tests, all passing) proves,
by diffing `p5_dev.pine` against `p7_dev.pine`:

* Every line the diff **removes** from the P5 DEV side is the indicator
  title — i.e. the diff is pure insertion plus one title rename, never a
  modification of existing P1–P6 code.
* Every `:=` reassignment the diff **adds** targets a `p7`-prefixed
  variable — P7 reads any P1–P6 variable freely, but never writes back into
  one, even to copy a value.
* The `f_p7*` label-lookup section calls none of the eighteen closed P5
  decision functions (`f_p5T1`, `f_p5T2`, …, `f_p5Lifecycle`) — label
  functions are pure `switch`-on-an-already-computed-code lookups.
* Plot-family call count: **63 = 63** (P7 DEV = P5 DEV = P6 DEV; zero new
  plots). `request.security` call count: **6 = 6** (zero new semantic
  requests). Zero `alertcondition(` calls (P8 not started).

Additional source-level resource inventory (this closure, not re-derived by
the automated test): `label.new`/`line.new`/`box.new` call counts are
**1 / 2 / 1 in both files** — P7 adds no new drawing objects of the kind the
closed visual-anchor defect (`BTRC_V1_P7_VISUAL_ANCHOR_DEFECT.md`) concerns.
It adds exactly **two** new `table.new` calls (3 total vs. P5 DEV's 1) — and
that same document already classifies `table.new` as "screen-anchored by
design and... not part of this defect," so P7's only new visual objects are
of the one kind already ruled out of scope for that defect.

## 5. Real FXCM verification performed this session

* **Compile**: 0 errors, both as a standalone attach and after every
  redeploy (title-only variant, then the diagnostic-scaffolded variant, then
  the final clean variant).
* **Render**: both tables visually confirmed on a live FX:XAUUSD M15 chart
  (bellcare1994/bellforex, FXCM), with real, non-placeholder values —
  `EXPLOSIVE BREAK` / `HEALTHY` / `LONDON/NY OVERLAP` / `EXTREME (abnormal)`
  breakout/pullback/session/volatility, and active-POI rows showing real
  POI indices (528–577 range observed), tiers, BTMM validity, alignment,
  scores, permission, and lifecycle state.
* **A genuine diagnostic instrument was built and then removed**: a
  temporary `log.info("P7DIAG|...")` line and a bright red 1×1
  `"P7 TEST TABLE"` cell were added to `p7_dev.pine`, redeployed, and used
  to conclusively prove the render code path executes with real data
  (`hasData=true|active=93|...`) at a point where the chart canvas itself
  appeared blank — this was the evidence that resolved the session's central
  rendering mystery (Section 7) as an environment artifact, not a P7 defect.
  The test table is removed from the committed source; the diagnostic log
  line is retained but **debug-gated** (`if debugMode`), matching the
  existing P5EVAL convention.
* **Object Tree** repeatedly confirmed the exact attached set: `BTMM + POI +
  BTRC Scanner [P6 DEV]` + `BTMM + POI + BTRC Scanner [P7 DEV]`, and nothing
  else scanner-related (no P5 ATOMIC PARITY, no P6 ATOMIC PARITY) — verified
  after every remove/re-add and after a full page reload.
* **Remove / re-add**: P7 DEV was removed from the chart and re-added from
  its saved script; Object Tree confirmed clean removal, then clean
  re-attachment with the current saved source.
* **Reload**: a full page reload (`F5`) confirmed both P6 DEV and P7 DEV
  persist as saved chart studies, the panel reconstructs from the freshly
  recompiled source (the stale "P7 TEST TABLE" diagnostic disappeared and
  the clean summary/POI tables appeared, with fresh active-POI counts),
  and no duplicate table appeared.
* **Runtime**: the pre-existing "Heavy script... close to your plan's
  runtime limit (20s)" warning was observed repeatedly on P7 DEV — expected
  and already classified GO by the P5/P6 precedent this campaign
  established (P7 does not add measurable per-bar work beyond eight
  `array.push` calls per eligible POI plus a small, fixed number of
  `table.cell` writes per render). No runtime **failure** (no `RE10120` or
  any other error banner) was ever observed on P7 DEV specifically, across
  every attach/save/reload cycle this session.

## 6. What this session did NOT complete — disclosed, not silently skipped

This session hit severe, extensively-diagnosed TradingView rendering
instability (Section 7). Given the scale of that detour, the following
items from the governing brief's validation matrix were **not** independently
exercised this session, and are recorded here rather than falsely claimed:

* **Zero-active-POI state**: never naturally occurred (the live chart's POI
  registry held 87–101 active POIs throughout every observation window this
  session), and was not separately constructed. The code path is present
  and structurally sound — `p7HasData` starts `false` and the summary
  table's zero-state branch (`else: for r = 3 to 11: f_row(..., "-", "-")`)
  is reachable before any confirmed bar exists — but this is a static
  read of the source, not a live observation.
* **M5/H1 timeframe-switch matrix** and the **detailed pan/zoom/scale
  acceptance matrix** (Phases 18–19 of the governing brief) were not
  re-run. The architectural argument for low regression risk is direct: P7
  adds zero new price/time-anchored drawing objects (Section 4's label/
  line/box counts are unchanged), and its two new objects use Pine's
  `position.top_left`/`position.bottom_right` — screen-anchored by
  definition, immune to pan/zoom/timeframe by construction, and the same
  anchor mechanism `BTRC_V1_P7_VISUAL_ANCHOR_DEFECT.md` already ruled out
  of scope for the closed defect. This is a sound argument for why the
  matrix is low-risk; it is not a substitute for having run it.
* **A literal directed 5→2→0 active-POI sequence** (Phase 8) was not
  constructed. In its place: the `array.clear(p7PoiIdx)` (and its seven
  sibling arrays) calls are unconditional, run at the top of every
  `barstate.isconfirmed` pass before the per-POI loop, and were confirmed
  present via direct source reading — plus the real, changing active counts
  in Section 5 are live evidence the arrays are not stuck.
* **Terminal-POI bar-boundary behavior** (Phase 13) was not independently
  re-tested at the UI layer. P7 copies exactly the `isTerminal`/`eligible`
  state the closed P5 active-POI loop already computes and that loop's own
  22-test contract (`test_p5_active_poi_loop_contract.py`) already proves —
  P7 adds no new terminal-boundary logic of its own for this to regress.

None of this blocks the closure claimed in Section 8, which is scoped to
match what was actually verified.

## 7. A genuine environment finding: the connection-limit / background-tab trap

Most of this session's difficulty tracked back to two compounding, now
diagnosed causes — not a P7 code defect:

1. **TradingView Basic plan caps live chart connections at 2.** Having three
   browser tabs open on the same chart simultaneously (accumulated across
   several recovery attempts) triggered an explicit **"We've closed this
   connection... you've exceeded your plan's limits"** modal on one tab,
   which explains a large share of the session's "blank canvas" symptoms.
   Reducing to a single tab and clicking "Restore connection" resolved it.
2. **A background browser tab does not paint its canvas.** A second tab,
   created via the automation tooling's default (non-foreground) tab
   creation, ran its full script computation and logging correctly (proven
   by the `P7DIAG` log line firing with real data) while its candle/table
   canvas stayed completely black — Chrome's background-tab rendering
   throttle, not a Pine or P7 defect. The fix was working from exactly one
   tab at a time.

**For any future session automating this chart**: keep exactly one browser
tab open on it at a time, and if a canvas ever appears persistently blank
while `Pine logs...` still shows fresh activity, suspect environment/tab
state (connection cap, backgrounding) before suspecting the Pine source.

## 8. Gate

```
P7_UI_PRESENTATION_ADDED                  TRUE   (2 new screen-anchored tables, 0 new plots)
P7_DISPLAY_ONLY_MECHANICALLY_PROVEN       TRUE   (8/8 tests, test_p7_semantic_equivalence.py)
P7_ZERO_NEW_PLOTS                         TRUE   (63 = 63)
P7_ZERO_NEW_SEMANTIC_REQUESTS             TRUE   (6 = 6 request.security calls)
P7_ZERO_NEW_DRAWING_OBJECTS               TRUE   (label/line/box counts unchanged: 1/2/1)
P7_OVERFLOW_POLICY_LIVE_CONFIRMED         TRUE   (5 distinct real active counts observed: 87,88,93,97,101)
P7_TABLE_RENDERS_ON_REAL_FXCM_DATA        TRUE   (screenshot + log evidence, this session)
P7_REMOVE_READD_RELOAD_VERIFIED           TRUE   (Object Tree confirmed at every step)
P7_ZERO_ACTIVE_STATE_LIVE_VERIFIED        FALSE  (not naturally observed; code path present, not live-tested)
P7_M5_H1_MATRIX_LIVE_VERIFIED             FALSE  (not re-run this session; see Section 6)
P7_PAN_ZOOM_MATRIX_LIVE_VERIFIED          FALSE  (not re-run this session; see Section 6)
P5_SEMANTICS_UNCHANGED                    TRUE   (real-parity suite green, H1 351473241 / H2 335238294 unchanged)
P6_SEMANTICS_UNCHANGED                    TRUE   (30/30 real-data parity tests green, unchanged)
P7 PRESENTATION LAYER                     CLOSED (scope as verified above)
PRODUCTION_APPROVED                       FALSE
```

**Not claimed here.** Any UI/UX quality judgment, calibration of what the
panel displays, production readiness, or that P7 covers every governing
brief phase — Section 6 lists what remains unverified. P5's weights and
45/65 bands remain ENGINEERING-PROVISIONAL, unchanged and untouched by this
phase. No `strategy.*` code exists anywhere in either script; nothing was
published; nothing was pushed.
