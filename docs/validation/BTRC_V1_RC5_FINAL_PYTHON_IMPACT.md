# BTRC-V1 RC5 — Final Python semantic impact

Candidate `6c2122c`. Measured on the frozen FXCM captures.

Sweep counts are the canonical causal `QualifiedSweepEvent` totals from the
Phase 18 closure run (see `BTRC_V1_RC5_CAUSAL_LIQUIDITY.md`); every other
column is measured from the same batch analysis in one pass.

| host | bars | POIs | auth | valid | visible | fresh | mitig | re-mitig | false-brk | genuine | DOJI raw/surv | swings | meaningful | HH | HL | LH | LL | BOS | CHOCH | sweeps |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M5 | 2000 | 249 | 243 | 78 | 78 | 58 | 6 | 14 | 8 | 165 | 4/3 | 422 | 132 | 32 | 23 | 30 | 33 | 33 | 27 | 280 |
| M15 | 2000 | 218 | 205 | 73 | 73 | 58 | 3 | 12 | 3 | 132 | 10/2 | 432 | 133 | 33 | 27 | 33 | 32 | 35 | 23 | 272 |
| H3 | 300 | 43 | 43 | 23 | 23 | 18 | 2 | 3 | 0 | 20 | 1/1 | 66 | 25 | 8 | 6 | 4 | 4 | 6 | 5 | 57 |
| H4 | 2000 | 244 | 231 | 83 | 83 | 57 | 10 | 16 | 1 | 148 | 11/4 | 417 | 144 | 43 | 44 | 18 | 28 | 43 | 21 | 442 |
| M45 | 529 | 59 | 56 | 33 | 33 | 27 | 2 | 4 | 0 | 23 | 5/4 | 118 | 49 | 11 | 7 | 9 | 14 | 12 | 6 | 68 |

M45 reports its semantic host as 45 minutes throughout, never the M15 carrier
enum it is driven on.

## What the numbers show

**Mitigation is not termination.** Mitigated and re-mitigated POIs stay valid
and visible on every host — M5 6 + 14, H4 10 + 16, M15 3 + 12 — and false-break
reclaims survive as well (M5 8, M15 3, H4 1). Under the pre-correction rule
every one of those would have been hidden the moment price touched the zone.

**`valid == visible` on all five hosts.** Authority suppression is the only
thing that hides a live zone; nothing else silently removes one.

**Structure narrows hard.** M15 goes 432 confirmed swings → 133 meaningful →
125 user labels, so the chart carries decision points rather than a pivot
forest. H4 is 417 → 144 → 133.

**DOJI survives authority sparingly** — 11 raw to 4 on H4, 10 to 2 on M15 —
which is the ladder working: a Doji loses to any stronger same-origin
reversal.

## Causal-history delta — the two directions are NOT one number

**CAUSAL HISTORY RECOVERED.** Levels that existed, qualified and were genuinely
swept before later supersession. The final-state route erased them: raw
framework sweeps H3 51 → 57, M45 102 → 123, always a strict superset, never
missing.

**FUTURE-LEAK EVENTS REMOVED.** H3 structural-swing events fell 11 → 3 once
qualification became per-prefix; the other eight had been qualified by roles
the swing only earned AFTER the sweep.

**RETROACTIVE OWNER CHANGES PREVENTED.** 13 stale rolling-POI events on H3,
each of which had additionally stolen dedup ownership from the structural swing
that legitimately owned the level.

An increase is not automatically an improvement and a decrease is not
automatically a regression. Both directions above are corrections.

## Gates at candidate time

| gate | result |
| --- | --- |
| full suite, sealed V1-A excluded | 5,519 passed, 19 skipped, 0 failed |
| focused RC5 suites | 248 passed, 0 failed |
| working tree after suite | clean, no test artifacts |
| `git diff --check` | pass |
| ruff / format on changed files | clean |
| mypy on RC5 modules | no issues |
| frozen contracts | 0 lines changed this session |
| transport codes 1–32 | unchanged; DOJI = 33 |
| RC4 | untouched; 37 framework tests pass |

**Differential lint gate: PASS. Pre-existing repository debt unchanged** — 59
ruff errors and 68 format diffs remain in unrelated P2/structure test files,
with zero overlap with the 25 files changed here. This is explicitly NOT a
claim that the repository is ruff-clean.
