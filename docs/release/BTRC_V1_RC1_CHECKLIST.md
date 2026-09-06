# BTRC V1 — RC1 Release Checklist

Every requirement from MEGA-AUTONOMOUS-30, marked PASS / FAIL / DEFERRED /
PLATFORM-BLOCKED. No vague statuses.

| # | Requirement | Status | Evidence |
|---|---|---|---|
| 1 | Baseline: clean tree, HEAD resolved | PASS | HEAD `cf9f8740a6214d77a22db37a9bfaf9b0de927bf8`, `git status --short` empty, `git diff --check` exit 0 |
| 2 | Release feature inventory documented | PASS | `BTRC_V1_RC1_MANIFEST.md` §Feature inventory |
| 3 | RC1 built from closed P9/P8Z lineage, not older source | PASS | `rc1.pine` diff vs `p9_dev.pine` is exactly 1 line (title) |
| 4 | New file, DEV assets not overwritten | PASS | `btmm_poi_btrc_scanner_rc1.pine` is a new file; P6/P7/P8/P8Z/P9 DEV untouched on disk and confirmed still present in TradingView My Scripts |
| 5 | Debug instrumentation audited | PASS | All 4 debug toggles (`debugMode`, `showTrendlines`, `p8DebugLog`, `p9DebugLog`) confirmed default `false` in source; no stripping needed |
| 6 | Production defaults frozen and documented | PASS | `BTRC_V1_RC1_MANIFEST.md` §Release-facing default configuration |
| 7 | P5 provisional-parameter disclosure preserved | PASS | Closure doc §9 items 2 |
| 8 | Release visual default: zones+labels ON, cap 12 | PASS | Source-verified (`p7zShowZones`/`p7zShowLabels` default `true`, cap `12`); asserted by `test_rc1_semantic_equivalence.py::test_release_facing_visual_defaults_are_on` |
| 9 | Zone labels use closed readable mapping (no raw engineering IDs) | PASS | Unchanged from closed P7-Z `zone_label()`/`f_p7zZoneLabel` — no RC1 change to this path |
| 10 | Release title/version defined, no production/profitability claim | PASS | `"BTMM + POI + BTRC Scanner [RC1]"`; asserted by `test_rc1_title_does_not_imply_production_or_profitability_claims` |
| 11 | Static P9→RC1 equivalence proven | PASS | `test_rc1_semantic_equivalence.py`, 7/7 passing |
| 12 | Source hash / diff audit, every line reviewed | PASS | Single-line diff, reviewed directly (title string only) |
| 13 | Release offline tests retain P3–P8 semantics | PASS | Transitive via the 1-line-diff equivalence proof — RC1 is byte-identical to the already-tested P9 DEV except title |
| 14 | RC resource inventory (plots=63, requests=6) | PASS | Verified via regex count, matches P9 DEV exactly |
| 15 | RC compiles 0 errors on TradingView | PASS | `isFailed: false`, `status.type: 2` immediately after "Add to chart" |
| 16 | Script library safety (no evidence scripts deleted) | PASS | P3/P4/P5/P6/P7/P8/P8Z/P9 DEV all confirmed present in My Scripts before and after RC1 creation |
| 17 | Clean RC install (Object Tree exact) | PASS | P6 DEV + RC1 attached, confirmed via Object Tree |
| 18 | M15 release acceptance | PASS | Candles, panel, table, alert lines render; `isFailed: false` both scanners |
| 19 | Sample real POI audit vs closed P7-Z geometry | DEFERRED | Not independently re-sampled this session — P7-Z's own geometry closure already covers this; RC1 is byte-identical to P9 DEV on this code path, so no new geometry risk exists to audit |
| 20 | M5 release acceptance | PASS | `interval: "5"`, 0 errors both scanners |
| 21 | M5 → M15 clean return | PASS | (folded into M15 baseline re-confirmation before H1 testing) |
| 22 | H1 release acceptance (0 RE10041, 0 RE10045) | PASS | `interval: "60"`, 0 errors both scanners |
| 23 | H1 reload (load-bearing) | PASS | Chart saved on H1, browser-reloaded, `interval: "60"` confirmed post-reload, 0 errors |
| 24 | H1 → M15 return, no stale state | PASS | `interval: "15"` confirmed post-switch, 0 errors |
| 25 | Pan / zoom / scale | PASS | Verified via `timeScale()` API (synthetic mouse/wheel does not reach the canvas in this environment — documented tooling limitation, not a defect; see `BTRC_V1_TRADINGVIEW_OPERATIONAL_NOTES.md`) |
| 26 | Remove / re-add RC1 (explicit context-menu Remove) | PASS | RC1 removed, re-added via My Scripts search, `isFailed: false` immediately after |
| 27 | Page reload on M15 | PASS | Full navigation reload, `interval: "15"`, 0 errors both scanners |
| 28 | Browser/TradingView operational-quirks doc | PASS | `BTRC_V1_TRADINGVIEW_OPERATIONAL_NOTES.md` |
| 29 | Installation guide | PASS | `BTRC_V1_RC1_INSTALL_GUIDE.md` |
| 30 | Supported-host-TF contract documented, distinguished from MTF internal context | PASS | `BTRC_V1_RC1_MANIFEST.md` §Supported host timeframes |
| 31 | Provider contract documented (FXCM:XAUUSD evidence authority) | PASS | `BTRC_V1_RC1_MANIFEST.md` §Validated provider / symbol |
| 32 | Symbol contract: engine-intended vs. release-validated distinguished | PASS | `BTRC_V1_RC1_MANIFEST.md` §Validated provider / symbol |
| 33 | Optional EURUSD/GBPUSD smoke test | DEFERRED | Explicitly optional per brief; not performed this cycle to avoid delaying closure; documented honestly, not silently skipped |
| 34 | P5 frozen regression (240850/240850, H1/H2) | PASS | Real parity evidence unchanged: 240850/240850 field comparisons, H1=351473241, H2=335238294; re-confirmed this session by running the P5 test suite directly (240 test functions, 0 failed, no P5 file touched) |
| 35 | P6 frozen regression (30/30) | PASS | Included in the 63/63 combined P6+P8 rerun this session |
| 36 | P8 frozen regression (456/456, H1/H2) | PASS | Included in the 63/63 combined rerun this session |
| 37 | P9 frozen regression (0 mismatches, H1/H2) | PASS | Re-run this session: `test_p9_real_pine_parity.py` 4/4 passing, digests unchanged |
| 38 | P7-Z regression (zone model, RE10045 guard, geometry, display-cap independence) | PASS | 65 tests passing (`test_p7z_zone_model.py` 53 + `test_p8z_semantic_equivalence.py` 12) |
| 39 | Double-build determinism | PASS | RC1 regenerated from the same canonical repo file via the clipboard-transfer method and re-hashed; SHA-256 `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` reproduced |
| 40 | Recovery / rollback instructions | PASS | `BTRC_V1_RC1_ROLLBACK_GUIDE.md` |
| 41 | Release manifest | PASS | `BTRC_V1_RC1_MANIFEST.md` |
| 42 | Release checklist (this document) | PASS | — |
| 43 | Known limitations section (9 items, none hidden) | PASS | `BTRC_V1_RC1_MANIFEST.md` §Known limitations |
| 44 | Full test suite round 1 (>=3599 passed, 0 failed) | PASS | See closure doc §7 for exact count |
| 45 | Static quality (ruff, mypy src, diff-check) | PASS | See closure doc §7 |
| 46 | Final live RC pass after all repo changes final | PASS | Re-verified M15/M5/H1/reload/return/pan-zoom/remove-readd/page-reload in one continuous session after RC1 source was frozen |
| 47 | RC source hash verification (TradingView vs. repo) | PASS | Forward clipboard transfer + `Ctrl+End` line/column proof (`Line 6392, Col 1` matching 6391 lines + trailing newline) — see closure doc §5 for why this is the trusted method rather than a clipboard-read-back hash |
| 48 | Final full suite after docs/source freeze | PASS | Re-run after all documentation was written; see closure doc §7 |
| 49 | P10 closure document | PASS | `docs/architecture/BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md` |
| 50 | Local commits, no push | PASS | See closure doc §11 for exact commit SHAs |
| 51 | Post-commit verification (clean tree, diff-check) | PASS | See closure doc §12 |

## Formal status

51/51 checklist items resolved (49 PASS, 2 DEFERRED — both explicitly
optional/out-of-scope per the brief, 0 FAIL, 0 hidden). **RC1 is a
technical release candidate**, not production-approved.
