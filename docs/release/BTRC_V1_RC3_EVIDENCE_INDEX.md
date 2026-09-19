# BTRC V1 — RC3 evidence index (SEMANTIC FREEZE READY = TRUE)

Every claim behind the RC3 freeze, with where it is proven. No executable
scanner code is referenced by change here.

**SEMANTIC CODE SHA: `3f9f790`** (branch `rc3-ob-origin-revision`, pushed, not
merged). Documentation commits that follow do NOT rerun the authority.

## 1. Author decisions frozen in RC3

| decision | rule | code | tests |
|---|---|---|---|
| A — structural context gate | a candle pattern maps only when the frozen P2 direction at its availability agrees, or a later break confirms a leg it formed inside (available at the break); else raw | `poi/leg_origin.py` (`ContextReason`, `structure_context_decisions`, `immutable_structure_gate`) | `test_rc3_poi_context_gate.py` (8), `test_rc3_order_block_leg_origin.py` (15) |
| B — named formation over its pressure wick | HAMMER > same-candle BULLISH PRESSURE WICK, SHOOTING STAR > same-candle BEARISH PRESSURE WICK | `poi/qualification.py` (`_WICK_SPECIALIZATIONS`) | `test_rc3_poi_context_gate.py` (decision-B cases) |
| C — FVG minimum gap frozen | gap ≥ 0.35 × Wilder ATR-14 of the departure candle; 0.349999 rejects | `poi/qualification.py` (`fvg_passes_quality`) | `test_rc3_poi_qualification.py` (13, incl. the frozen-boundary test) |
| lifecycle contract (author, 2026-09-17) | source = formation origin, availability = structural confirmation, freshness strictly after availability; pre-availability touches never mitigate | unchanged `poi/lifecycle.py` | `test_p3_rc3_freshness_model.py`, `test_p3_rc3_mitigation_lifecycle.py` |

Preserved from earlier freezes: RC1/RC2 builds, P6 closed, T3 correction, S/R
source/availability contract, Doji exclusion, confirmed-POI non-repaint, 2.0
engulfing displacement, P5 terminal-bar inclusion, P8 native ordering.

## 2. Documentation of record

| topic | document |
|---|---|
| freeze summary + measurements | `docs/validation/BTRC_V1_RC3_SEMANTIC_FREEZE.md` |
| pipeline and context gate | `docs/architecture/BTRC_V1_RC3_CONTEXT_AWARE_POI_ENGINE.md` |
| per-type qualification matrix | `docs/architecture/BTRC_V1_RC3_POI_QUALIFICATION_MATRIX.md` |
| FVG threshold evidence | `docs/validation/BTRC_V1_RC3_FVG_QUALITY_AUDIT.md` |
| FVG same-origin arbitration | `docs/validation/BTRC_V1_RC3_SAME_ORIGIN_ARBITRATION.md` |
| non-FVG pair decisions | `docs/validation/BTRC_V1_RC3_NON_FVG_ARBITRATION_MATRIX.md` |
| context / leg audit + trend story | `docs/validation/BTRC_V1_RC3_MARKET_CONTEXT_AUDIT.md` |

## 3. Test evidence (not rerun for the freeze; recorded 2026-09-17)

* Full suite `--ignore=tests/unit/test_v1a_m5_materiality.py`: **4 875 passed,
  0 failed** (240 unit test modules).
* ruff (src + every changed file) clean; mypy `src` clean (141 files);
  `git diff --check` clean.
* Author fixtures: `tests/fixtures/rc3_qualification_fxcm.json` (M15 weak/valid
  FVG pair, H1 pressure-wick case), `rc3_fvg_reference_fxcm_m15.json`,
  `rc3_leg_origin_h4_author.json`, `rc3_doji_fxcm_h4.json`,
  `rc3_confirmed_zone_m15.json`, `rc3_visual_dominance_fxcm_h4.json`.
* Context-gate fixtures: synthetic continuation / reversal series
  (`tests/parity_support/ob_origin_series.py`) and the structured prefix
  `tests/parity_support/structured_context.py`.
* BTMM seed regression:
  `test_scanner_replay_incremental_equivalence.py::test_btmm_genuine_invalidation_after_a_false_invalidation_reaches_confirmed_setups`
  (fails without `3f9f790`).
* Pine source locks: `test_rc3_poi_context_gate.py`, `test_rc3_poi_qualification.py`,
  `test_rc3_ob_origin_pine_port.py`, `test_rc3_pine_block_immutability.py`,
  `test_rc3_visual_source_locks.py`.

## 4. Pine builds

| build | version | saved source sha256 | evidence |
|---|---|---|---|
| USER `[RC3 POI SEMANTICS DEV]` | 30 | `a24672606520e561…` | editor-buffer SHA == repo file; pine-facade saved-source SHA == repo file |
| PARITY `[RC3 PARITY DEV]` | 13 | `84d3f7e7874870af…` | same, plus the capture run below |
| RC1 (frozen) | — | file `143c0f8817c78bf4…` | untouched since `2eff3e6` |
| RC2 (frozen) | — | file `381f2fc2463c4eaa…` | untouched since `bec3ed8` |

## 5. Parity (fresh, context-gated engine)

Capture `artifacts/rc3_freeze_aligned/pine_m15_run5.csv` sha256
`acb1bf8015e53315…`; six same-session OHLC exports selected by RUNMETA count +
checksum; Level-A replay 500 host bars.

| stage | compared | mismatches |
|---|---|---|
| P3 | 105 POIs | 0 |
| P5 | 814 rows / 300 bars | 0 |
| P8 | 439 events | 0 payload, 0 ordering |

P6 remains CLOSED and was not reopened: 30/30 real-data parity
(`tests/unit/test_p6_real_data_parity.py`, recorded in
`docs/architecture/BTRC_V1_P5_HOST_RUNTIME_SAFETY_ADDENDUM.md`), digests H1
`74231825` / H2 `124714621` (`docs/architecture/BTRC_V1_P5_TRANSPORT_AUDIT.md`). P5WIRE is diagnostic only and
was not used as evidence.

## 6. Authority artifacts

| artifact | path |
|---|---|
| final full run (1 836 bars, complete) | `artifacts/rc3_authority_freeze_final/` (+ `verification.json`, `determinism.json`) |
| Witness A (killed, 1 102 bars / 12 days) | `artifacts/rc3_authority_freeze_partial_killed/` |
| Witness B (killed, 1 745 bars / 19 days) | `artifacts/rc3_authority_freeze/` |
| 300-bar before/after + BTMM-fix comparison | `artifacts/rc3_context_delta/` |
| fresh aligned parity | `artifacts/rc3_freeze_aligned/` |
| context-gate + leg audit | `artifacts/rc3_context_gate/` |
| non-FVG pair audit | `artifacts/rc3_non_fvg_pairs/` |
| M1 clutter before/after | `artifacts/rc3_m1_clutter/` |
| verifier output | `<run>/verification.json` |

Verification tooling (artifact readers only, no engine import):
`tests/parity_support/rc3_authority_verify.py`,
`rc3_authority_diff.py`, `rc3_aligned_capture.py`, `rc3_aligned_compare.py`,
`rc3_context_gate_audit.py`, `rc3_non_fvg_pair_audit.py`,
`rc3_qualification_coverage.py`.

## 7. Sealed material (never opened this campaign)

`docs/validation/BTRC_V1_V1A_CHARACTERIZATION_SUMMARY.md`,
`tests/parity_support/v1a_m5_materiality.py`,
`tests/unit/test_v1a_m5_materiality.py` — untracked, unstaged, unread. The OOS
window 2026-07-14T17:15Z → 2026-08-03T06:45Z was never replayed, inspected or
reported; the authority window (2026-08-09 22:00 → 2026-09-04 20:30) and every
capture window are outside it.
