# BTRC-V1 P7-Z — POI Zone Visualization: CLOSURE

Status: **P7-Z POI ZONE VISUALIZATION — CLOSED**
Branch: `pine-p4-btmm`
Closed: 2026-09-06

---

## 1. What P7-Z is

P7-Z draws real, bounded rectangular zone boxes (plus optional labels) for
POIs the closed P3 registry already detects, P5 already evaluates, and P7
already tables. It detects nothing new: it consumes exactly the same
`p7PoiIdx` active-set array P7's own table already builds, and reads
`poiZoneTop`/`poiZoneBottom`/`poiAvailTime`/`poiType`/`poiDirection`/
`poiTier`/`poiTerminal` — the closed P3 registry's own parallel arrays —
directly, with zero new computation.

Source: `tradingview/btmm_poi_btrc_scanner_p8z_dev.pine` (6346 lines,
`sha256 f62be2d2…`), built as `tradingview/btmm_poi_btrc_scanner_p8_dev.pine`
(the closed P8 lineage, commit `fa87199`) plus one title change and one
additive block — Section 9 gives the mechanical proof of that claim.

## 2. Source-of-truth registry — no second detector

Confirmed by research before any code was written: **no POI zone-drawing
code existed anywhere in this codebase** prior to this phase (the only
prior `box.new` is the unrelated P2 support/resistance zone). P7-Z reuses,
verbatim, without re-deriving:

| P7-Z need | Reused from | Type |
|---|---|---|
| Active-POI set + order | `p7PoiIdx` (P7's own transient array, ascending registry index, cleared/rebuilt every confirmed bar) | `array<int>` |
| Upper price | `poiZoneTop` | `array<float>` |
| Lower price | `poiZoneBottom` | `array<float>` |
| Left-edge anchor | `poiAvailTime` | `array<int>` (ms) |
| Type code | `poiType` | `array<int>` (`C_POI_*`, 1-18 core) |
| Direction | `poiDirection` | `array<int>` (`C_POI_DIR_BULLISH`/`BEARISH`) |
| Tier | `poiTier` | `array<int>` (`C_POI_TIER_*`) |
| Terminal flag | `poiTerminal` | `array<bool>` |

No second order-block/FVG/engulfing/BTMM/support-resistance detector was
written. `test_p8z_semantic_equivalence.py::test_p7z_block_calls_no_decision_function`
mechanically proves the new block calls none of the 18 closed P5 decision
functions.

## 3. Display-selection contract

**Selection rule**: `p7zShown = min(p7zActive, p7zMaxVisibleZones)`, where
`p7zActive = array.size(p7PoiIdx)`. The **first** `p7zShown` entries of
`p7PoiIdx` (ascending registry index — the lowest-index, longest-standing
still-eligible POIs) are drawn — the exact same rule and the exact same
array P7's own active-POI table already uses for its own `p7Shown`/
`p7MaxVisiblePois` cap. No new ranking, score, or ordering was introduced.

**"Displayed" is explicitly not "best" or "newest"**: because indices only
increase (the P3 registry is append-only) and eligibility only shrinks
(never re-admits a lower index once it exits), a brand-new POI with a
higher index than the current window waits — potentially indefinitely — for
an older POI ahead of it to terminate and free a slot. This is a direct,
intentional consequence of reusing P7's own convention rather than
inventing a "closest to price" or "highest score" selection, which the
brief flagged as a separate product decision requiring explicit
authorization. `test_p7z_zone_model.py::test_newest_poi_waits_for_a_slot_when_capacity_is_full_ascending_order`
documents this exact behavior.

**Engine vs. display separation (Phase 3/21)**: `p5N`, the P5 evaluation
loop bound, and `p7PoiIdx`'s full population are computed identically
whether or not P7-Z is even enabled. `test_p7z_block_never_indexes_p7poiidx_beyond_its_own_selection`
asserts the new block never references `p5N` and never mutates
`p7PoiIdx` — the display cap (`p7zMaxVisibleZones`) can only ever bound
what is *drawn*, never what P5/P7/P8 evaluate or alert on. Live-observed:
the P7 table's own footer reported **95, 97, and 133 real active POIs**
across the M15/H1/M5 sessions below, while P7-Z drew at most its own
12-zone cap in every case.

## 4. Capacity

`btmm_poi_btrc_scanner_p8_dev.pine`'s indicator declaration already
reserves `max_lines_count = 500`, `max_labels_count = 500`,
`max_boxes_count = 500`; prior to this phase exactly 1 box, 1 label, and 2
lines were ever created (all P2 structure). This left effectively the full
budget open. `p7zMaxVisibleZones` (`input.int`, default **12**, range
1-30) is deliberately far below that ceiling — headroom was measured, not
guessed, and the cap is a presentation-only setting (`grpP7Z` input group),
never referenced by any P1-P8 semantic code.

## 5. Box geometry

- **Top / bottom**: `poiZoneTop`/`poiZoneBottom` verbatim — no padding, no
  ATR expansion, no snapping. Direction never swaps which field is top vs.
  bottom (`test_box_geometry_is_exact_p3_boundaries_never_swapped_by_direction`).
- **Left edge**: `poiAvailTime` — the bar the P3 registry itself created
  the entry (== `poiConfirmTime` for every production detector), **not**
  the pattern's earlier source/candidate candle. This follows the one
  existing drawing precedent in this codebase (the P2 support/resistance
  box anchors at `confirmationTime`) and avoids any appearance that the
  scanner "knew" about a zone before it was actually confirmed.
- **Right edge**: `time_close`, re-set via `box.set_right` every confirmed
  bar while the POI is non-terminal; frozen (stop extending) the exact bar
  the POI goes terminal, but the box remains visible at that final extent
  through that bar.
- **Coordinate system**: `xloc = xloc.bar_time` (real timestamps, not
  `bar_index`) throughout — the same convention the closed
  `BTRC_V1_P7_VISUAL_ANCHOR_DEFECT.md` fix already established as required
  for correct anchoring across timeframe switches.

## 6. Label contract

Format: `"{originTF} • {TYPE}"`, with `"• STRONG"` appended only for
`C_POI_TIER_STRONG`. All 18 core type codes map to a fixed, human-readable
name (`f_p7zTypeLabel`, mirroring `tests/parity_support/p7z_zone_model.py`'s
`POI_TYPE_LABEL` table exactly — both are tested, `test_p8z_semantic_equivalence.py`
and `test_p7z_zone_model.py` respectively). Any code outside the closed
18-type core (including the RESERVED liquidity/period-level types 19-32)
maps to `"UNKNOWN"`, never to a real POI name. No raw registry index,
sentinel, wire code, or transport field is ever shown in a label — only
the type/timeframe/tier vocabulary already used elsewhere in this project's
UI. Direction is conveyed by box/border color (bullish = lime, bearish =
red — the project's existing convention), not by label text.

## 7. Lifecycle and the terminal-retention decision (an explicit author-decision flag)

Reusing `p7PoiIdx`'s own eligibility (`not isTerminal or not finalDone` —
the closed P5 active-loop contract) means a terminal POI is eligible for
exactly **one** more bar (its final-pass bar) after going terminal, then
permanently exits `p7PoiIdx`. P7-Z's box for that POI is created/extended
normally while non-terminal, **frozen** (no further `box.set_right`) on the
final-pass bar, and **removed** the bar after, when the POI exits
`p7PoiIdx` for good.

The brief's Phase 9 asked for a decision among: (A) disappear immediately,
(B) stop extending but remain historically visible, (C) remain for a
bounded historical window — preferring (B) unless it conflicts with the
resource/source architecture, in which case: **stop and flag for author
decision**. That conflict is real: true long-term retention (showing a
terminated POI's box for hours/days after its final pass) would require
P7-Z to remember geometry for POIs the engine itself has already stopped
tracking as active — new, P7-Z-only state independent of the reused P5/P7
eligibility contract. The adopted V1 behavior is the middle ground: **stop
extending on terminal (satisfying B's core intent — "show where the
reaction occurred" — for the terminal bar itself), removed shortly after
via the same one-bar grace already built into the reused contract.** This
is flagged explicitly here, per the brief's own instruction, as the one
open design question a future phase may revisit if longer-lived historical
zones are wanted; it was not decided silently.

## 8. MTF anchoring — resolved by the registry's own architecture, not by new code

Research (before any Pine was written) established: **P3's POI registry
carries no origin-timeframe field at all** — P3 is single-timeframe by
construction (no `request.security` anywhere in P1-P3; every POI is a
product of whichever timeframe the host chart itself is running on). There
is therefore no such thing as "a D1 POI displayed on an M15 host" in the
current closed system — every POI's true origin timeframe **is** the host
chart's timeframe. `f_p7zZoneLabel`'s `originTf` parameter is passed
`timeframe.period` directly for exactly this reason — this is not an
approximation, it is the only correct value given the registry's actual
contract. The brief's Phase 24/25 MTF-coordinate-drift concern is
consequently moot for V1: since every POI is host-timeframe-native, there
is no cross-timeframe coordinate mapping to get wrong. `xloc.bar_time` (a
real timestamp) is used regardless, so a genuine future MTF-POI feature
would still anchor correctly if ever added.

## 9. Mechanical proof — additive-only (`test_p8z_semantic_equivalence.py`, 12 tests)

Diff-based, not a manual read, mirroring the exact method already
established for P7→P8:

- Only the indicator title line differs from P8 DEV; every other removed
  line is that same title.
- Every added `:=` reassignment targets a `p7z`-prefixed variable.
- Plot-family count (63) and `request.security` count (6): unchanged.
- `alertcondition()` count (0) and `alert()` count (5): unchanged — P7-Z
  never touches P8's alert surface.
- `box.new` call sites: 1 → 2 (the one new zone box); `label.new`: 1 → 2
  (the one new, `p7zShowLabels`-conditional zone label); `line.new`:
  unchanged at 2.
- No forbidden execution term (`entry`, `stopLoss`, `takeProfit`,
  `positionSize`, `strategy.*`, ...) in any added code line.
- The P7-Z block calls none of the 18 closed P5 decision functions and
  never references `p5N` or mutates `p7PoiIdx`.
- **A permanent regression test for the real defect below**
  (`test_both_p7zshown_loops_are_guarded_against_zero_active`) asserts
  both `for r = 0 to p7zShown - 1` loop sites remain wrapped in an explicit
  `if p7zShown > 0` guard.

## 10. A real defect, caught live, fixed, and permanently regression-tested

Live TradingView deployment surfaced a genuine runtime error the offline
Python model (`p7z_zone_model.py`, 53 tests, all passing before deployment)
could not have caught: **`RE10045`** — `array.get(p7PoiIdx, 0)` on an
empty array, "index 0 out of bounds, size 0".

**Root cause**: Pine's `for r = 0 to p7zShown - 1` does **not** silently
skip execution when `p7zShown == 0` (unlike Python's `range(0)`, which the
offline model relies on) — it still executes at least once. This is the
same "Pine backwards-`for` hazard" class of defect documented earlier in
this campaign (P3), now recurring in new code. The closed P5 active-loop
already guards its own identical-shaped loop with `if p5N > 0` before
`for i = 0 to p5N - 1` — this exact defensive pattern was missed on first
write for the two new `p7zShown` loops and is now applied to both.

This is disclosed explicitly because it is the clearest evidence in this
closure that the offline Python reference model, while necessary and
valuable (53 tests covering selection, geometry, identity, eviction,
freeze, overflow, and two adversarial mutants), is **not sufficient** on
its own for a Pine port — live compilation and live runtime observation
remain required, and did their job here.

## 11. Live TradingView validation (real FXCM, account bellcare1994, chart `6cu1b2O7`)

- **Compile**: 0 errors after the fix (confirmed via the study's own
  `isFailed()`/`status()` state, queried directly through TradingView's
  in-page chart-model API — more reliable than screenshots alone this
  session, given several transient renderer-paint-staleness incidents
  unrelated to Pine, recovered via the documented fresh-tab and
  `resetLayoutSizes`/`resize`/`paint` recipe).
- **M15**: real zone boxes visually confirmed — multiple stacked bearish
  (red) rectangles with labels of the form `"15 • <TYPE>"` rendered at
  their correct price levels near real, live FXCM price action. P7's own
  table reported **95 real active POIs** the same moment.
- **M5**: `failed: false`, 1266+ bars, real recomputed active count
  (**133**), zone boxes visually confirmed at the correct M5 price levels.
- **H1**: `failed: false`, **zero `RE10041`** (the pre-existing, separately
  -fixed P5 H1 defect this P8/P8-Z lineage already inherits the fix for —
  confirmed again here since P7-Z adds no timeframe-conditional code path
  of its own), 1800/1800 bars, real recomputed active count (**97**).
  Reload-while-H1 (the load-bearing case per the P5 fix precedent) also
  confirmed clean.
- **Remove / re-add**: performed via the Object Tree row's explicit
  right-click → **Remove** (never the ambiguous legend-row trash icon —
  the cause of a disclosed incident in the prior P8-A session). Saved
  script confirmed present in "My scripts" before every re-add; each
  re-attach produced a clean, error-free instance.
- **Host-timeframe matrix executed**: M15 → M5 → M15 (baseline) → H1 →
  (reload) → M15, zero errors at every step.

**Not independently re-verified this session**: dedicated pan/wheel-zoom/
price-scale-drag interaction testing beyond what the above host-switch and
remove/re-add sequence already exercised, and a live green (bullish) zone
example specifically (the currently-active POI population sampled
happened to be bearish-heavy at the moments checked). Direction-color
symmetry is separately proven for both directions in the offline model
(`test_box_geometry_is_exact_p3_boundaries_never_swapped_by_direction`
constructs one bullish and one bearish POI in the same call and asserts
both render correctly), and the color-selection code itself
(`bullish ? lime : red`) is a single, unconditional ternary with no
per-timeframe or per-count branching — there is no code path by which
bearish-only observation would have hidden a bullish-specific defect.

## 12. Resource counts (confirmed, Section 9)

| Metric | P8 DEV | P8Z DEV | Delta |
|---|---|---|---|
| `plot`/`plotshape`/`plotchar` | 63 | 63 | 0 |
| `request.security` | 6 | 6 | 0 |
| `box.new` | 1 | 2 | +1 |
| `label.new` | 1 | 2 | +1 (conditional on `p7zShowLabels`) |
| `line.new` | 2 | 2 | 0 |
| `alert(` | 5 | 5 | 0 |
| `alertcondition(` | 0 | 0 | 0 |

## 13. Non-regression — P5/P6/P8

- **P8 real Pine↔Python event parity**: re-run this session, unchanged —
  456/456 events exact, digest `(H1=294719549, H2=35571918)` match.
- **P8 semantic equivalence** (vs. its own P7 ancestor): 9/9 unchanged.
- **P5 real-data replay digest**: re-run this session, unchanged —
  `test_p5_atomic_capture_replay_parity.py::test_global_digest_matches`
  passes (`H1=351473241, H2=335238294`, 240,850/240,850 field matches).
- **P6 real-data parity**: re-run this session, unchanged —
  `test_p6_real_data_parity.py::test_the_global_digest_is_exact` passes.
- No P1-P6 or P8 source file changed this session — only the new
  `btmm_poi_btrc_scanner_p8z_dev.pine` and its Python-side companions
  (`p7z_zone_model.py`, `test_p7z_zone_model.py`,
  `test_p8z_semantic_equivalence.py`) were added.

## 14. Quality gates

- Full repository test suite: **3624 passed** (3559 prior + 65 new: 53
  offline model + 12 mechanical equivalence).
- `ruff check` / `ruff format --check`: clean on all new files.
- `mypy --explicit-package-bases`: clean on all new files (the one
  pre-existing, unrelated `tests` packaging ambiguity and the pre-existing
  `resolve_eligible_and_next` UUID/int generic-typing looseness — both
  already disclosed in the P8-A session's records — are untouched by this
  phase and reproduce identically on files predating it).
- `git diff --check`: clean.

## 15. Deferred / explicitly not decided here

- **Long-lived historical retention of terminal zones** beyond the current
  one-bar grace (Section 7) — a real, disclosed open design question, not
  a silent omission.
- **A "closest to price" or score-based display-selection rule** — never
  considered; the brief explicitly forbade inventing new trading-relevant
  ranking without separate authorization, and the reused P7-table
  ascending-index rule satisfies every stated V1 requirement.
- **Dedicated pan/zoom/price-scale-drag regression testing** beyond the
  host-switch/remove-readd sequence already performed.
- P3 Context and P4 Reviewed-Evidence Transport remain deferred, unchanged
  from every prior phase's verdict.

## 16. Formal status

- P7-Z POI VISUALIZATION = CLOSED
- P3 SEMANTICS = UNCHANGED
- P4 SEMANTICS = UNCHANGED
- P5 SEMANTICS = UNCHANGED
- P6 SEMANTICS = UNCHANGED
- P7 TABLE UI = UNCHANGED
- P8 ALERT EVENT ENGINE = UNCHANGED
- VISIBLE POI ZONES = VERIFIED on M5/M15/H1 (real FXCM data, zero runtime
  errors after one real defect was caught live and fixed)

PRODUCTION APPROVED = FALSE

## 17. Safety

No P1-P8 semantic was read, changed, or recomputed by this phase beyond
what P7-Z's own presentation logic reads (already-computed registry state).
No new `request.security`. No execution capability (entry/SL/TP/sizing) in
any box, label, or code path. No broker integration. No live trading. No
push, no merge to `main`, no publish.
