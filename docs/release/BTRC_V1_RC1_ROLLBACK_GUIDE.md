# BTRC V1 — RC1 Recovery / Rollback Guide

## If RC1 misbehaves on a live chart

1. **Do not edit the live chart's script source directly.** Any fix
   belongs in the canonical repository file
   (`tradingview/btmm_poi_btrc_scanner_rc1.pine`) first, then
   re-transferred to TradingView — never the reverse. Ad hoc live edits
   diverge from the reviewed, hashed, tested source and defeat the whole
   point of this release process.
2. Detach RC1 from the chart: Object Tree → right-click the RC1 row →
   **Remove**. Never use the legend trash icon (see
   `BTRC_V1_TRADINGVIEW_OPERATIONAL_NOTES.md` — it has permanently
   deleted a saved script in this project before).
3. Re-attach the last known-good closed asset instead:
   - `BTMM + POI + BTRC Scanner [P9 DEV]` (identical engine semantics to
     RC1 — RC1 is a 1-line title diff from this exact script) is the
     safest fallback; every P9 closure evidence still applies to it.
   - Or restore the RC1 source itself from the exact closure commit (see
     "Known-good source SHAs" below) and re-transfer it via the
     clipboard method in the operational notes doc.

## Known-good source SHAs

| Asset | Commit | File SHA-256 |
|---|---|---|
| P9 DEV (fallback engine, identical semantics to RC1) | `f54e2fe` | `5a025a849b4b73b12146435de83785a6bc18094a471bd8b94300a8342302ffe4` |
| RC1 (this release) | see `BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md` §11 for the exact commit | `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` |

## If the repository needs to roll back past RC1 entirely

RC1 introduced no changes to any `src/` file and no changes to any
closed P1–P9 Pine or Python asset — it is purely additive (one new Pine
file, one new test file, documentation). Rolling back is therefore just:

```bash
git log --oneline -- tradingview/btmm_poi_btrc_scanner_rc1.pine
git revert <RC1-commit-sha>   # or reset to the pre-RC1 commit if preferred
```

No data migration, no state to restore, no downstream dependents to
notify — nothing else in the codebase imports or depends on the RC1
Pine file or its release tests.

## If a TradingView-side asset (saved script) is accidentally deleted

1. Do not attempt to "undo" through TradingView's own UI — script
   deletion has no reliable undo in this platform.
2. Re-create the saved script (Pine Editor → **Create new** → Blank
   indicator script), name it exactly as the deleted one was named, and
   paste the exact canonical source from the corresponding file/commit
   SHA in the table above, using the clipboard-transfer + `Ctrl+End`
   line-count verification method.
3. Re-save. Re-attach to the chart if needed. Re-verify compile status
   (`isFailed: false`, `status.type: 2`) via the JS check in the
   operational notes doc before considering it restored.

## General principle

Every asset this project produces is reproducible from the git
repository: every closed Pine DEV/RC source has a recorded SHA-256 and a
commit SHA. If you are ever unsure whether a live TradingView asset
matches what this project intends, regenerate it from the repository
rather than trusting or patching what's currently live.
