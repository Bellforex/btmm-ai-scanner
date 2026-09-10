# BTRC V1 — RC2 AND THE V1-A VALIDATION PROGRAM

**Conclusion: RC2 does not invalidate the paused V1-A protocol or harness work.**

RC2 changes **user-facing presentation only**. The semantic scanner outputs that
V1-A consumes are unchanged.

---

## THE MECHANICAL ARGUMENT

Three independent checks, each verifiable from the repository.

**1. RC2 differs from the accepted V2 source by one line.**
A direct diff of `btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine` against
`btmm_poi_btrc_scanner_rc2.pine` yields exactly two changed lines — the
`indicator()` call before and after — and **zero** non-title differences.

**2. No `src/` file changed across the entire promotion.**
`git diff --name-only` over the promotion commits restricted to `src/` returns
nothing. The Python engine that produces P3/P4/P5/P6/P8 semantics is untouched.

**3. Every Pine change is confined to the P7/P7-Z presentation block.**
The RC1 → V2 diff was mechanically classified: zero writes to any engine array
(`poiType`, `poiZoneTop`, `poiZoneBottom`, P5 or P8 state) appear anywhere in it.

---

## WHAT IS UNCHANGED

| Phase | Contract | Status |
| --- | --- | --- |
| P3 | POI detection, geometry, lifecycle, registry identity | **UNCHANGED** |
| P4 | BTMM two-layer evidence semantics | **UNCHANGED** |
| P5 | BTRC scoring, permission, alignment | **UNCHANGED** |
| P6 | Multi-timeframe transport | **UNCHANGED** |
| P8 | Event and alert semantics | **UNCHANGED** |

Frozen authorities that must therefore still hold:

- P5: 240850 / 240850 field comparisons; H1 351473241, H2 335238294
- P6: 30 / 30
- P8: 456 / 456; H1 294719549, H2 35571918
- P9: H1 224768619, H2 772693120

---

## WHAT RC2 DID CHANGE

Only which already-computed POIs get **drawn**, and how they are **labelled**:

- proximity selection instead of registry order
- capacity counted in visual groups
- timeframe token formatting
- exact-geometry and FVG presentation grouping
- label anchoring and fill styling

The active registry still holds **every** active POI. P5 still evaluates all of
them and P8 still monitors all of them. No registry identity is merged; grouping
collapses drawn objects only.

**One nuance worth stating plainly.** RC2 changes what a human sees on the chart.
If any part of V1-A were ever defined by reading the chart visually rather than
from engine output, that part would be affected. V1-A as written consumes engine
output, so it is not — but that is the boundary, and it is worth checking rather
than assuming if the protocol is ever extended.

---

## VALIDATION STATE — UNCHANGED BY THIS PROMOTION

| Item | Value |
| --- | --- |
| V1-A | **PAUSED** |
| V1-A characterization results | **NOT OPENED** |
| OOS | **UNOPENED** |
| Next checkpoint | **V1-A0 M5 MATERIALITY GATE** |

`docs/validation/BTRC_V1_V1A_CHARACTERIZATION_SUMMARY.md` was not opened during
this promotion, and the V1-A harness files remain untracked and untouched.

Validation resumes only from the previously paused V1-A0 M5 materiality gate,
and only on explicit instruction.

---

## SEMANTIC BASELINE

The RC1 semantic validation baseline remains valid. RC2 supersedes RC1 for
**user-facing release** only; it does not supersede RC1 as the semantic subject,
because the semantics are identical between them.
