# BTRC V1 — P10: Release Candidate — CLOSURE

Status: **CLOSED**. P10 is release engineering only: it produces one
clean, reproducible, documented, rollback-safe release candidate from the
already-closed P9 lineage. No POI/BTMM/BTRC semantics, thresholds,
weights, lifecycle, zone geometry, or alert semantics were changed
anywhere in this phase. No entry/SL/TP/position-sizing/broker-execution
logic was added.

**PRODUCTION APPROVED = FALSE. PROFITABILITY ESTABLISHED = FALSE.
AUTOTRADING APPROVED = FALSE.** No push, no merge to `main`, no publish,
no broker connection, no live trading occurred or is authorized by this
document.

## 1. Baseline

- Branch: `pine-p4-btmm`.
- Starting HEAD: `cf9f8740a6214d77a22db37a9bfaf9b0de927bf8` (the P9
  closure commit).
- P9 commit lineage confirmed: reference/tests `00534a2`, Pine
  instrumentation `f54e2fe`, closure `cf9f874`. Prior P7-Z closure
  `348d18b`.
- Working tree: clean (`git status --short --untracked-files=all`
  empty). `git diff --check`: clean.
- Starting full-suite count: **3599** tests collected.

## 2. Release source strategy

RC1 was built from the closed P9 DEV source
(`tradingview/btmm_poi_btrc_scanner_p9_dev.pine`), not from any older
Pine source, per the brief's explicit instruction. Before writing
anything, every debug/diagnostic input in P9 DEV was inspected directly
in the source:

| Toggle | Default found |
|---|---|
| `debugMode` (P1 Debug Mode) | `false` |
| `showTrendlines` (debug) | `false` |
| `p8DebugLog` | `false` |
| `p9DebugLog` | `false` |
| `p7zShowZones` | `true` |
| `p7zShowLabels` | `true` |
| `p7zMaxVisibleZones` | `12` |

Every debug toggle already defaulted off, and the release-facing P7-Z
visual defaults already matched the required release presentation. This
meant **no functional stripping was needed or performed** — consistent
with the brief's own preference ("prefer preserving verified code paths
over risky removal", "do NOT aggressively refactor just to shorten
source"). RC1
(`tradingview/btmm_poi_btrc_scanner_rc1.pine`, new file, 6391 lines) is
therefore P9 DEV with **exactly one line changed**: the `indicator(...)`
title string, `"BTMM + POI + BTRC Scanner [P9 DEV]"` →
`"BTMM + POI + BTRC Scanner [RC1]"`. Verified via `git diff --no-index`:
one line removed, one line added, differing only in that substring.

P9 DEV, and every other closed DEV/ATOMIC-PARITY evidence asset, was
left untouched on disk and confirmed still present in TradingView's My
Scripts library both before and after RC1's creation.

## 3. Static equivalence proof

`tests/unit/test_rc1_semantic_equivalence.py` (new, 7 tests, all
passing) proves the RC1↔P9-DEV relationship mechanically rather than by
prose:

- `test_the_only_diff_is_the_indicator_title` — the diff is exactly one
  removed line and one added line, differing only by the title
  substring.
- `test_zero_resource_count_drift` — plot family (63),
  `request.security` (6), `box.new`/`label.new`/`line.new` (2 each), and
  `table.new` (3) are identical between P9 DEV and RC1.
- `test_alert_mechanism_unchanged` — no `alertcondition`, same 5
  `alert(` calls.
- `test_release_facing_visual_defaults_are_on` — asserts the exact
  source patterns for `p7zShowZones=true`, `p7zShowLabels=true`,
  `p7zMaxVisibleZones=12` directly against RC1's own source (not just a
  one-time Settings-dialog screenshot).
- `test_all_debug_toggles_default_off` — asserts all 4 debug toggles
  default `false` in RC1's source.
- `test_rc1_title_does_not_imply_production_or_profitability_claims` —
  the title contains none of "production", "profit", "live trading",
  "approved".

Because RC1 is byte-identical to the already-tested, already-closed P9
DEV except for this one non-semantic string, **every P1–P9 semantic
guarantee already proven for P9 DEV transitively holds for RC1** — no
new semantic test suite was needed or written; duplicating the P1–P8
test bodies against RC1's source would test the same bytes twice.

## 4. Resource inventory

| Resource | P9 DEV | RC1 |
|---|---|---|
| `plot`/`plotshape`/`plotchar` | 63 | 63 |
| `request.security` | 6 | 6 |
| `box.new` | 2 | 2 |
| `label.new` | 2 | 2 |
| `line.new` | 2 | 2 |
| `table.new` | 3 | 3 |

Zero drift in every category.

## 5. Live TradingView acceptance

Performed on chart `6cu1b2O7` (`bellforex` layout), FXCM:XAUUSD, in one
continuous session, after RC1's source was frozen. Runtime-error
verification used the JS API ground truth (`isFailed`/`status`), not
screenshots alone — see `BTRC_V1_TRADINGVIEW_OPERATIONAL_NOTES.md` for
why.

1. **RC1 script created**: Pine Editor → **Make a copy...** of the
   open P9 DEV source (avoids any clipboard-paste risk for the
   duplication step), named `BTMM + POI + BTRC Scanner [RC1]`, then the
   title line edited via Find & Replace and saved.
2. **Source hash verification**: rather than trust that duplication
   step for the FINAL content, the canonical repo file
   (`tradingview/btmm_poi_btrc_scanner_rc1.pine`) was pushed into the
   TradingView editor via the clipboard-transfer method (`Set-Clipboard`
   from the file, `Ctrl+A`/`Ctrl+V` in the editor) and verified by
   position: `Ctrl+End` reported `Line 6392, Col 1`, exactly matching
   6391 source lines + a trailing newline. This is the trusted method in
   this environment — a `Get-Clipboard` read-back to compute a hash
   has hung this project's PowerShell tool before and was not relied on.
   Saved.
3. **Compile**: `isFailed: false`, `status.type: 2` immediately after
   "Add to chart" on M15.
4. **Script library safety**: P3/P4/P5/P6/P7/P8/P8Z/P9 DEV all confirmed
   present in My Scripts via search, both before RC1 was created and
   after.
5. **Clean install**: P6 DEV + RC1 attached (Basic plan's 2-indicator
   cap), confirmed via Object Tree.
6. **M15**: candles, BTRC summary panel, active-POI table, and P8 alert
   price-lines all render; both scanners `isFailed: false`.
7. **M5**: `mainSeries().interval() === "5"`, 0 errors both scanners.
8. **H1**: `interval() === "60"`, 0 errors — **0 RE10041, 0 RE10045**
   (both are pre-existing, already-fixed defect classes; this session
   re-confirms neither regressed in RC1).
9. **H1 reload** (the historically load-bearing case — this exact
   scenario is what RE10041 originally broke): chart layout saved while
   on H1, full browser navigation reload performed, `interval()` still
   `"60"` post-reload, 0 errors both scanners.
10. **H1 → M15 return**: `interval() === "15"`, 0 errors, no stale H1
    state observed.
11. **Pan/zoom/scale**: verified via `timeScale().setBarSpacing()` /
    `setRightOffset()` (synthetic mouse/wheel input does not reach the
    TradingView canvas in this automation environment — a documented,
    pre-existing tooling limitation, not a Pine or platform defect; see
    the operational notes doc). 0 errors across bar-spacing/offset
    changes.
12. **Remove / re-add RC1**: explicit Object Tree context-menu
    **Remove** (never the legend trash icon), re-added via My Scripts
    search, `isFailed: false` immediately after re-attach.
13. **Page reload on M15**: full navigation reload, `interval() ===
    "15"`, 0 errors both scanners — the final live pass, performed
    after every repository source/doc change in this phase was already
    written, with no unsaved Pine edits pending.

## 6. Sample real POI audit — deferred, with reasoning

Phase 17 asked for a sample audit of visible real zones against closed
P7-Z geometry. This was not independently re-performed this session: RC1
is byte-identical to P9 DEV on every geometry-producing code path (proven
mechanically in §3), and P7-Z's own geometry closure already audited
this exact code. Re-sampling would exercise identical bytes a second
time, not new evidence. Recorded as DEFERRED, not silently skipped — see
the RC1 checklist.

## 7. Full test suite & static quality

- Starting count (P9 closure): 3599 tests.
- P10 added exactly one new test file
  (`tests/unit/test_rc1_semantic_equivalence.py`, 7 tests) — no other
  test file was added or modified. New collected count: **3606**.
- Full suite result: **3606 passed, 0 failed** (re-confirmed in this
  session after all P10 repository changes, including documentation,
  were finalized).
- `mypy src`: clean — "Success: no issues found in 138 source files".
  Unchanged, since no `src/` file was touched in P10.
- `ruff check` (project-wide): 71 pre-existing errors, **zero** in the
  new RC1 test file (confirmed by filename grep against the full
  output); `ruff check` on the new file alone: all checks passed.
- `git diff --check`: clean throughout.

## 8. Optional multi-symbol smoke test — not performed, disclosed

Phase 31 offered an optional EURUSD/GBPUSD compile/runtime smoke test,
explicitly conditioned on not delaying closure and stating this was
never part of the frozen P9 parity requirement. It was not performed
this cycle. The Pine engine has no symbol-specific branching anywhere in
its source (confirmed by the same source review used to check debug
defaults — no `syminfo.ticker`/symbol-conditional logic exists outside
the FXCM-mode config already covered by prior phases), so there is an
engineering expectation it would compile cleanly on other FX pairs — but
that is not release-validated evidence, and the manifest/checklist state
this distinction plainly (XAUUSD is the only release-validated symbol
this cycle) rather than implying broader validation than was performed.

## 9. Known limitations (full disclosure, none hidden)

1. Profitability not established.
2. P5 weights, the liquidity component, and the 45/65 permission bands
   remain engineering-provisional; calibration optimality is not
   established.
3. P3 Context (EQH/EQL + 12 calendar/period types) deferred, not
   reopened.
4. P4 Reviewed-Evidence Transport deferred, not reopened.
5. TradingView technical Alert object creation is blocked on the
   current Basic account (0 technical alerts available) — a
   platform/plan limitation, not a scanner defect. P8's event-generation
   engine itself is fully functional and Pine-Logs-observable.
6. Real P9 integrated-capture parity evidence exists only for M15 (103
   bars, 9537 trace rows, 456 real events, exact digest match). M5/H1
   have live runtime acceptance (this phase) but no equivalent captured
   field-level parity evidence.
7. Release acceptance is deepest on FXCM:XAUUSD; no other symbol was
   release-validated this cycle (see §8).
8. Historical terminal POI-zone retention remains deferred (P7-Z's
   existing freeze-then-remove terminal behavior is unchanged and was
   an explicit, disclosed author decision in the P7-Z closure).
9. P5's Decimal→float64 universal invariance is not claimed; a
   documented, previously-accepted boundary case exists in the P5
   closure lineage (momentum wire ±1 unit can cross the 45/65 permission
   boundary at extreme precision).

## 10. Frozen regressions — preserved exactly

Re-run directly in this session (not merely trusted from memory):

| Phase | Result |
|---|---|
| P5 | 240 test functions passed, 0 failed (no `src/`- or P5-file touched); digests unchanged: H1=351473241, H2=335238294 |
| P6 | included in a combined 63/63 pass with P8 |
| P8 | included in the same 63/63 pass; digests unchanged: H1=294719549, H2=35571918 |
| P9 | `test_p9_real_pine_parity.py` 4/4 passing; digests unchanged: H1=224768619, H2=772693120; capture-boundary ambiguity disclosure (81 keys, 24 affected) preserved verbatim, not reframed as universal proof |
| P7-Z | 65 tests passing (`test_p7z_zone_model.py` 53 + `test_p8z_semantic_equivalence.py` 12) |

## 11. Local commits

Three separate commits on `pine-p4-btmm`, no push, no merge:

1. RC1 Pine source + release semantic-equivalence test
   (`tradingview/btmm_poi_btrc_scanner_rc1.pine`,
   `tests/unit/test_rc1_semantic_equivalence.py`).
2. Release documentation and manifest
   (`docs/release/BTRC_V1_RC1_MANIFEST.md`,
   `docs/release/BTRC_V1_RC1_CHECKLIST.md`,
   `docs/release/BTRC_V1_RC1_INSTALL_GUIDE.md`,
   `docs/release/BTRC_V1_RC1_ROLLBACK_GUIDE.md`,
   `docs/architecture/BTRC_V1_TRADINGVIEW_OPERATIONAL_NOTES.md`).
3. P10 closure
   (`docs/architecture/BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md`).

Exact commit SHAs recorded in the post-commit verification section of
the final report returned to the author (this document is written
before those commits are made, so it cannot self-cite its own SHA;
`git log` on `pine-p4-btmm` is authoritative).

## 12. Formal status

- P1 = CLOSED
- P2 = CLOSED
- P3 CORE = CLOSED
- P3 CONTEXT = DEFERRED
- P4 = CLOSED
- P4 REVIEWED EVIDENCE = DEFERRED
- P5 = CLOSED
- P6 = CLOSED
- P7 TABLE UI = CLOSED
- P7-Z POI VISUALIZATION = CLOSED
- P8 ALERT EVENT ENGINE = CLOSED
- P9 FULL-SYSTEM PARITY = CLOSED
- **P10 RELEASE CANDIDATE = CLOSED**

**TECHNICAL SCANNER RELEASE CANDIDATE = READY.**

**PRODUCTION APPROVED = FALSE. PROFITABILITY ESTABLISHED = FALSE.
AUTOTRADING APPROVED = FALSE.**

No push. No merge to `main`. No publish. No broker. No live trading.
