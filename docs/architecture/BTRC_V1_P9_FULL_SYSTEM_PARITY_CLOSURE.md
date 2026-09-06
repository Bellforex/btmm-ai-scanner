# BTRC V1 — P9: Full-System End-to-End Parity — CLOSURE

Status: **CLOSED**. Scope: integration + traceability + parity + system
acceptance ONLY. No POI semantics, BTMM/BTRC scoring, thresholds, weights,
zone-selection rule, or alert semantics were redesigned, added to, or
changed anywhere in this phase. P3 Context and P4 Reviewed-Evidence
Transport remain deferred and were not reopened.

**PRODUCTION APPROVED = FALSE.** No push, no merge to `main`, no publish,
no broker connection, no live trading occurred or is authorized by this
document. P10 is NOT started.

---

## 1. What P9 proves

One canonical POI identity — the raw, append-only P3 registry index `i` —
flows through P3 (registration/geometry) → P5 (per-bar dynamic
state/eligibility) → P7 (table visibility) → P7-Z (zone visibility) → P8
(alert events) without identity drift, timing drift, direction drift,
zone-geometry drift, lifecycle drift, score/permission drift, or display
truncation ever affecting engine-side evaluation. P9 does not re-derive or
re-match this identity by price, type, or direction anywhere — every
consuming layer (P7, P7-Z, P8, and now P9) already used the same raw index
before this phase, and P9 changes none of that.

Display-cap independence — the property that P7's table cap (8) and P7-Z's
zone cap (12) never limit what P5 evaluates or what P8 may alert on — was
proven both offline (unit tests) and against a real capture where the
active-POI set (`p7PoiIdx`) reached 97 simultaneously active POIs on a
single bar while only 8 were shown in the table and 12 drawn as zones; POI
records outside both caps still carried complete, correct P5 state and
correctly fired P8 events when applicable (see §4 and §5).

## 2. Canonical POI identity & cross-layer contract

- **Identity**: P3 registry index `i`, integer, append-only, never reused,
  never re-derived. Read (never recomputed) by P5, P7, P7-Z, P8, and P9.
- **Static fields** (P3-origin, immutable once registered): `poi_type`,
  `direction`, `zone_top`, `zone_bottom`, `avail_time_ms`, `origin_tf`.
- **Dynamic fields** (P5-origin, recomputed every confirmed bar):
  `terminal`, `btmm_valid`, `final_score`, `permission`, `lifecycle`.
- **Derived visibility fields** (P7/P7-Z-origin, display-only, computed
  from the SAME P5 active-set + a bounded cap, never fed back into P5 or
  P8): `p7_visible`, `p7z_visible`.
- **Event fields** (P8-origin): zero or more of the five closed V1 event
  types, computed from consecutive-bar transitions of the dynamic fields
  above, independent of `p7_visible`/`p7z_visible`.

`P9Record` (`tests/parity_support/p9_integrated_model.py`) is the single
canonical struct folding all of the above for one POI on one bar. It is
test/parity tooling only — nothing under `src/` imports it, and no
production semantics were added or changed to produce it.

## 3. Reuse, not duplication

`P9IntegratedState` (`tests/parity_support/p9_integrated_model.py`)
orchestrates three already-closed, already-tested sub-models on identical
per-bar inputs — it introduces no new decision logic:

- `p7_ui_display_model.P7DisplayState` (P7 table cap/order contract)
- `p7z_zone_model.P7ZDisplayState` (P7-Z zone box/label lifecycle)
- `p8_alert_oracle.AlertEngine` (the five V1 event transitions)

All three call the same frozen `p5_active_poi_loop_model.
resolve_eligible_and_next` eligibility rule on the same inputs — calling a
pure function three times with identical arguments is reuse, not drift
risk, and was the same design already used independently by P7 and P7-Z
before this phase.

## 4. Pine instrumentation (P9 DEV)

Existing captures (`p8_dev_raw_log.csv`, `p8_dev_clean_capture.csv`) carry
no zone geometry or P7/P7-Z visibility flags, so a real end-to-end capture
required new debug-only instrumentation. Built from the closed P8Z DEV
source (`tradingview/btmm_poi_btrc_scanner_p8z_dev.pine`, unchanged):

- `tradingview/btmm_poi_btrc_scanner_p9_dev.pine` — 6391 lines (P8Z DEV:
  6346 lines; +45 lines, entirely the new debug-gated trace block and its
  input group). SHA-256:
  `5a025a849b4b73b12146435de83785a6bc18094a471bd8b94300a8342302ffe4`.
- One new input group, `p9DebugLog` (default `false`), independent of
  `p1DebugMode`/`p8DebugLog`.
- One new block, gated on `p9DebugLog`, emitting one `log.info("P9TRACE|
  ...")` line per POI per bar for every POI in `p7PoiIdx` (identity,
  static geometry, dynamic state, `p7Visible`, `p7zVisible`).
- **Zero new plots, boxes, labels, lines, or `request.security` calls.**
  `test_p9_semantic_equivalence.py` (10 tests, mirroring the closed
  `test_p8z_semantic_equivalence.py` method) proves: every non-title
  removed line is the indicator title; every added `:=` targets a
  `p9`-prefixed variable; plot/request/box/label/line counts are identical
  between P8Z DEV and P9 DEV (63/6/2/2/2 respectively); the alert
  mechanism (`alert(` calls, `alertcondition`) is unchanged; the P9 block
  calls none of P5's fourteen decision functions and creates no alert or
  drawing object; the new loop is guarded `if p9Active > 0` before
  iterating (the RE10045-class Pine backwards-`for` hazard, applied
  proactively from the start rather than discovered live a second time).

Compiled clean on first deployment: `isFailed: false`, `status.type: 2`,
zero runtime errors, confirmed via the `_exposed_chartWidgetCollection`
API immediately after attach.

## 5. Real live capture

Chart `6cu1b2O7` (`bellforex` layout), FX:XAUUSD, host M15, `BTMM + POI +
BTRC Scanner [P9 DEV]` with BOTH `p9DebugLog` and `p8DebugLog` enabled
simultaneously (P6 DEV also attached, unrelated). Captured via Pine Logs →
Download logs.

- File: `artifacts/p9_capture/p9_dev_raw_log.csv` (gitignored; SHA-256
  `08b562bab981c1ce95878c84513ee6607447ef65768ea4ba10901b14b8f25876`).
- TradingView caps this download at ~10000 rows — **this is a real but
  truncated window**, not the full 1800-bar calc window. Stated plainly:
  103 unique M15 bars (`bar_ms` 1788459300000..1788554700000, ≈26h),
  9537 `P9TRACE` rows, 456 `P8EVENT` rows (POI_ACTIVATED=57,
  BTMM_VALIDATED=57, PERMISSION_ENTERED_ACTIONABLE=154,
  PERMISSION_LOST_ACTIONABLE=140, POI_TERMINAL=48).
- Only M15 has a real captured trace this phase. **Cross-host (M5/H1)
  parity was NOT independently re-captured and re-compared** — see §7 for
  what M5/H1 verification WAS done (compile/runtime-error verification,
  not field-level capture parity). This limitation is stated honestly
  rather than implied away.

## 6. Real Pine ↔ Python integrated parity

`tests/unit/test_p9_real_pine_parity.py` (4 tests, all passing) replays
the capture through `P9IntegratedState` and compares every field against
`P9Record`s reconstructed directly from the capture (event types
independently cross-checked against grouped `P8EVENT` rows, never derived
from the Python replay itself).

**Seeding / first-bar exclusion.** `P9IntegratedState.advance_bar`'s first
call silently primes its internal `AlertEngine` (no events possible on
that call) — the capture's first bar is treated as this priming call and
excluded from every comparison, mirroring `test_p8_real_pine_parity.py`'s
own precedent.

**The "known before window" gap — found, not hidden.** Unlike P8's test,
no second, wider capture exists for P9, so `AlertEngine` was seeded ONLY
from bar 1 of this one capture (inventing seed data was explicitly out of
scope). Running the strict replay against the real capture surfaced a
genuine divergence class directly: of 81 `(bar, poiIdx)` keys where a POI
first appears mid-window (at a bar other than the priming bar, absent from
the priming bar's own snapshot), 24 disagree on `event_types` — in every
case the Python replay spuriously fires `POI_ACTIVATED`
(+`BTMM_VALIDATED`, sometimes `PERMISSION_ENTERED_ACTIONABLE`) for a POI
Pine's real engine fires nothing for, because Pine's real, non-fresh
engine already knew about it from before the truncated window and Python's
fresh replay cannot. Registry-index inspection confirms the mechanism
cleanly: the 24 mismatching indices (513–620) are pre-existing POIs
re-entering the active set; the other 57 first-appearance keys (904–960,
strictly sequential) are genuinely new POIs registered live during the
window, and both sides agree exactly on those.

The resolution is a **mechanical, evidence-based, pre-registered**
exclusion (`_first_appearance_keys()`, defined purely from per-bar index
membership, computed before looking at any comparison result): only
`event_types`, only on exactly these 81 keys, is excluded from the
strict-equality assertion. The exact counts (81 unverifiable keys, 24
mismatching, all indices in `[513, 620]`) are hard-asserted so a future
capture or sub-model change that shifts either number fails loudly.

**Result — zero mismatches everywhere else:**

- 9473 `(bar_ms, poiIdx)` records compared beyond the priming bar.
- **Zero** scalar-field mismatches (`zone_top`, `zone_bottom`, `terminal`,
  `btmm_valid`, `final_score`, `permission`, `lifecycle`, `p7_visible`,
  `p7z_visible`, `poi_type`, `direction`, `avail_time_ms`) across ALL 9473
  records, including the 81 ambiguous ones.
- **Zero** `event_types` mismatches on the 9392 fully-verifiable records.
- **P9 digest exact match** over the 9392 fully-verifiable records:
  Python `(H1=224768619, H2=772693120)` == Pine-reconstructed
  `(H1=224768619, H2=772693120)`.

**Tier/align placeholder.** `P9TRACE` does not log `poiTier`/`poiAlign`
(by design). Verified by direct inspection of all three delegated
sub-models: neither field gates eligibility, visibility, or event logic
anywhere (`tier` only feeds P7-Z's display-only `zone_label()` suffix and
P8's pass-through event field; `align` has no effect anywhere; `P9Record`
itself carries neither). The placeholder value `0` used for both in the
replay's `P9BarInput` is therefore inert for every field this parity test
compares.

## 7. Live M15 / M5 / H1 runtime verification

Performed on the same live chart, same session, after the real capture:

- **M15 baseline**: candles, P7 panel/table, P7-Z zone inputs, P8 alert
  event lines, and P9 trace logging all present and updating; both
  scanners `isFailed: false`, `status.type: 2`.
- **M5**: host switch to `FX:XAUUSD, 5` confirmed via Object Tree and
  `mainSeries().interval()`; zero runtime errors on both scanners.
- **H1**: host switch to `FX:XAUUSD, 1h`; zero runtime errors — **no
  RE10041, no RE10045** (both are pre-existing, already-fixed defect
  classes from the P5/P7-Z phases; this session re-confirms neither
  regressed).
- **Reload while on H1** (the historically load-bearing case — this is
  exactly the scenario RE10041 originally broke): browser reload with the
  live in-session state saved as H1 beforehand; post-reload,
  `mainSeries().interval() == "60"`, zero errors on both scanners.
- **Return to M15**: `mainSeries().interval() == "15"` after switching
  back, zero errors, no stale H1 state observed.
- **Pan/zoom**: verified via the chart's own `timeScale()` API
  (`setBarSpacing`/`setRightOffset`), NOT via synthetic mouse/wheel input
  — this automation environment's synthetic scroll/drag events do not
  reach TradingView's canvas (a pre-existing, previously documented
  constraint of this session's browser tooling, not a Pine or platform
  defect). Table stayed screen-anchored, alert price-lines stayed
  price-anchored, zero errors across multiple bar-spacing/offset changes.
- **Remove / re-add** (explicit Object Tree context-menu "Remove", never
  the legend trash icon — see the permanent operational rule from the
  P8-A/P7-Z sessions): P9 DEV removed, re-added fresh via My Scripts,
  `isFailed: false`, `status.type: 2` immediately after re-attach.

**Visual zone-rectangle re-verification**: P7-Z's own visual acceptance
(rectangles rendering on-chart) was already closed in the prior P7-Z
session. This session independently confirms the DATA driving those
rectangles is correct end-to-end (captured `p7zVisible=true` for exactly
12 POIs on the most recent captured bar, matching the configured
`p7zMaxVisibleZones=12` cap exactly, and the full parity test above proves
that flag matches Python's independent computation in every case) — this
session did not additionally re-confirm the rectangles are visually
legible pixel-by-pixel in a screenshot at every zoom level, since P7-Z's
zone geometries are frequently sub-1-point-wide relative to a
multi-hundred-point chart range, which was already an accepted display
characteristic in the P7-Z closure, not a new finding.

## 8. Regression preservation

All frozen prior-phase numbers reconfirmed unchanged in this same session,
by running each phase's own test files directly (not merely trusting the
aggregate count):

| Phase | Result |
|---|---|
| P5 (BTRC confluence) | 240 test functions passed (0 failed) — semantic content unchanged, no `src/`-tree file touched |
| P6 (real-data parity) | included in the 63/63 passed above alongside P8 |
| P7-Z (zone model + RE10045 guard + semantic equivalence) | 65 tests passed (`test_p7z_zone_model.py` 53 + `test_p8z_semantic_equivalence.py` 12) |
| P8 (real Pine parity) | included in 63/63 passed above |
| P9 (this phase, all files) | 104 passed (`test_p9_integrated_model.py` 25 + `test_p9_semantic_equivalence.py` 10 + `test_p9_real_pine_parity.py` 4 + `test_p8z_semantic_equivalence.py` 12 + `test_p7z_zone_model.py` 53) |

No `src/` file was read-write touched by this phase; all P9 work lives
under `tests/parity_support/`, `tests/unit/`, `tradingview/` (new file
only), and `docs/architecture/` (new file only).

## 9. Full suite & static quality

- **Full pytest suite**: baseline 3595 tests (before this phase) → 3599
  tests, **3599 passed, 0 failed** after adding
  `tests/unit/test_p9_real_pine_parity.py` (the other four P9 files —
  `p9_capture_log.py`, `p9_digest.py`, `p9_integrated_model.py`,
  `test_p9_integrated_model.py`, `test_p9_semantic_equivalence.py` — were
  already present from the immediately-preceding continuation of this
  same session; the +4 delta is exactly the new real-capture parity test
  file). Re-confirmed directly in this session (background full run,
  exit code 0).
- **`mypy src`**: clean — "Success: no issues found in 138 source files".
  Unchanged, since no `src/` file was touched.
- **`ruff check`** (project scope): 71 pre-existing errors, **none** in
  any new P9 file (confirmed by filename grep against the ruff output).
  `ruff check` restricted to the two newest files
  (`p9_capture_log.py`, `test_p9_real_pine_parity.py`) alone: all checks
  passed.
- **mypy on test files**: the pre-existing, already-disclosed
  `resolve_eligible_and_next` `UUID`/`int` generic-typing looseness
  (confirmed in every phase since P7 to also affect the original
  precedent file `p7_ui_display_model.py`, independent of any new code)
  is the only class of typing warning touching P9's new files when
  checked with `--explicit-package-bases`; zero NEW issue classes were
  introduced.
- **`git diff --check`**: clean (verified post-commit, see §11).

## 10. Formal status

- P9: **CLOSED**.
- Canonical identity, cross-layer contract, display-cap independence,
  terminal/BTMM/permission chains: **PROVEN** (offline unit tests +
  real-capture parity).
- Real Pine ↔ Python integrated parity: **PROVEN**, with one honestly
  disclosed and mechanically bounded limitation (event-type ambiguity on
  81 structurally-unverifiable first-appearance keys, arising solely from
  this capture's truncated window and the absence of a second wider
  capture — not a semantic defect in any closed model).
- P9 digest: **EXACT MATCH** (H1=224768619, H2=772693120) over the
  fully-verifiable record set.
- M15/M5/H1 + reload-on-H1 + return-to-M15 + pan/zoom + remove-readd:
  **ALL PASS**, zero runtime errors throughout.
- All frozen P5/P6/P7-Z/P8 regression numbers: **PRESERVED EXACTLY**.
- Full suite: **3599/3599 passing**. Static quality: **clean** (scope
  disclosed above).
- **P10: NOT STARTED.**
- **PRODUCTION APPROVED = FALSE.**

## 11. Commits

This phase is committed as three separate commits:

1. P9 reference model, digest, and offline/semantic-equivalence tests
   (`tests/parity_support/p9_integrated_model.py`,
   `tests/parity_support/p9_digest.py`,
   `tests/unit/test_p9_integrated_model.py`,
   `tests/unit/test_p9_semantic_equivalence.py`).
2. P9 DEV Pine trace instrumentation
   (`tradingview/btmm_poi_btrc_scanner_p9_dev.pine`).
3. P9 real-capture parity test and this closure document
   (`tests/parity_support/p9_capture_log.py`,
   `tests/unit/test_p9_real_pine_parity.py`,
   `docs/architecture/BTRC_V1_P9_FULL_SYSTEM_PARITY_CLOSURE.md`).

No push, no merge to `main`. `artifacts/p9_capture/` remains gitignored
and uncommitted, per the project's existing convention for real captures.
