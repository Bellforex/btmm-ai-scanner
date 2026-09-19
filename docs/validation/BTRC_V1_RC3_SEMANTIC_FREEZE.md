# BTRC V1 — RC3 semantic freeze (READY = TRUE, recorded 2026-09-19)

Branch `rc3-ob-origin-revision`. Starting point `be9bae1`; freeze candidate
`3f9f790` (pushed, not merged). Author decisions A (structural context gate),
B (HAMMER / SHOOTING STAR over same-candle pressure wick), C (FVG gap ≥ 0.35 ×
ATR-14 frozen). Paper / dry-run only; P6 closed; sealed V1-A material untouched.

## Commits

| commit | content |
|---|---|
| `6400352` | Python context gate + decision B + boundary test; Pine USER v30 / PARITY v13 port; source locks |
| `c53d3ac` | small scanner / POI / authority fixtures given a confirmed structure |
| `68c03db` | docs, non-FVG matrix, context-gate and pair audit tools |
| `3f9f790` | BTMM incremental replay: FALSE POI invalidation is not terminal (seed 43) |

## Pine

| build | version | source sha256 (saved, via pine-facade) | status |
|---|---|---|---|
| USER DEV `[RC3 POI SEMANTICS DEV]` | 30 | `a24672606520e561…` | compiled, saved, running M1..W1 |
| PARITY DEV `[RC3 PARITY DEV]` | 13 | `84d3f7e7874870af…` | compiled, saved, capture run |

Both equal the repo files byte-for-byte (in-page SHA of the editor buffer and of
the saved source). Only pre-existing shadowing warnings.

## Gates

* Full suite (excluding the sealed `tests/unit/test_v1a_m5_materiality.py`):
  **4 875 passed, 0 failed** (after the BTMM fix; 4 873 before it).
* ruff (src + changed files) clean; mypy src clean; `git diff --check` clean.
* Kernel == batch at every prefix: leg-origin, qualification, context-gate and
  frontier differential tests.

## Fresh aligned parity (context-gated engine)

Same-session capture 2026-09-17 15:24 UTC, FX:XAUUSD, M15 host, PARITY v13;
`artifacts/rc3_freeze_aligned/pine_m15_run5.csv` sha256 `acb1bf8015e53315…`
(1 RUNMETA, 424 P3LIFE, 2 779 P8EVENT, 300 P5C). RUNMETA host 1 799 bars from
2026-08-21 00:30; contexts W1/D1/H4/H1 1 250, M5 1 249 — all selected from the
same-session exports by count + checksum (m15 `e4bff4a1…`, m5 `a558f7b5…`,
h1 `00d7302b…`, h4 `ca4eaf47…`, d1 `a6bbea3f…`, w1 `3abe1683…`). Level-A replay
over 500 host bars (10 m 52 s), `rc3_aligned_compare`:

| stage | compared | Python-only | Pine-only | mismatches |
|---|---|---|---|---|
| P3 | 105 POIs | 0 | 0 | **0** |
| P5 | 814 rows on 300 bars (618 higher-TF context, 196 host) | 0 | 0 | **0** |
| P8 | 439 events | 0 missing | 0 extra | **0 payload, 0 ordering** |

The replayed registry holds 486 POIs, 121 of them candle patterns mapped late by
reversal context (M15..W1), so the Pine `ctPending` rescue is exercised. The
`be9bae1` result (P3 150 / P5 1 049 / P8 657, 0 mismatches) is kept as
PRE-CONTEXT-GATE evidence. P5WIRE was not used (diagnostic only).

## Semantic impact vs `be9bae1` (daily authority, 300 M15 bars from 2026-08-10)

| | `be9bae1` | freeze candidate |
|---|---|---|
| distinct POIs | 519 (513 by identity) | 503 (497) |
| P3 / P5 rows | 35 904 | 48 197 |
| P8 events | 1 545 | 1 649 |
| terminal MITIGATED / PROMOTED | 295 / 2 | 224 / 2 |
| period digests P3 / P5 / P8 | `866db7db` / `b7c742f8` / `ec749d88` | `c8f7080b` / `aa8f3f91` / `65882649` |

* 69 POI identities present only before (context-rejected patterns and wicks
  under a hammer / shooting star) and 53 present only after (identity includes
  source time and zone, not availability; not individually classified).
* Rows grow because reversal-context POIs become available at the confirming
  break: first-touch mitigation is only counted after availability, so they stay
  fresh longer (e.g. M15 SELL FVG 2026-08-11 02:15: 3 rows → 108).
* P5 on common rows: 12 changed, 0 component-score changes, **0 permission
  changes**.
* Changed P3 fields on common rows: availability / confirmation / age (3 365),
  `effective_timeframe` (1 194), lifecycle fields (2).
* The BTMM fix changes nothing on this window (0 P3 / P5 / P8 diffs; identical
  digests on two runs → determinism).

## M1 clutter (live FX:XAUUSD, 342 confirmed M1 bars, 2026-09-17 08:20–14:01 UTC)

Python batch on the same bars: mapped POIs **144 → 79** (`be9bae1` → freeze);
fresh 19 → 25. Of 190 raw gated candle patterns: 35 quality rejects (FVG gap),
24 same-origin suppressed (17 FVG, **7 pressure wicks under hammer / shooting
star**), then context: 59 aligned + 14 reversal mapped, **48 counter-trend and
10 neutral stay raw**. Live USER v30 draws 8 labelled boxes on each of M1, M5,
M15, H1, H4, D1, W1 (status OK, 0 unlabeled).

## BTMM seed investigation (bounded)

Seeds 0–79 with / without evidence: only seed 43 diverged (incremental ≠ batch
from bar 109). Stage: P4 BTMM replay. Cause: three BTMM_CONFIRMED setups whose
source POI had FALSE_INVALIDATION_CONFIRMED (18:15) and later
GENUINE_INVALIDATION_CONFIRMED (03:15). The incremental path relayed one relevant
transition per POI and froze confirmed setups after any invalidation, so the
genuine invalidation never cancelled them (batch: POI_REJECTED). Small,
unambiguous fix in `btmm/analyzer.py` + `btmm/lifecycle_scheduler.py`;
regression test fails without it. Batch semantics unchanged. Pine P4
re-materializes from the POI's latest transition code and does not share this
path.

## Bot adapter compatibility

`botdryrun/scanner_adapter.py` (branch `bot-dryrun-v1`) consumes
`analysis.poi_analysis.current_poi_states` and P5 permissions from the Level-A
replay — qualified, mapped, context-gated POIs only; no raw detector or chart
label input. Its 55 tests pass against this branch's `src` + parity support
(throwaway worktree). PAPER / DRY-RUN only.

## Performance (indicative)

300-bar daily authority wall time: `be9bae1` 4 m 40 s (run under the full test
suite), freeze candidate 3 m 36 s / 3 m 24 s. No optimization was made in this
campaign, so no digest-equality proof is needed; the gate's prefix walk runs
only on diverged prefixes or possible-break closes.

## SHA policy

**SEMANTIC CODE SHA: `3f9f790`** — the only SHA the final authority ran on, and
the SHA this freeze applies to. Documentation commits made after the run
(including this file's final section) change no executable scanner code and do
NOT rerun the authority; they are recorded separately as the FREEZE RECORD SHA.
`git diff 3f9f790 -- src tradingview` must stay empty for the freeze to hold.

## Final full authority

### Run history (all on semantic SHA `3f9f790`, identical inputs)

| attempt | launched from | outcome | kept as |
|---|---|---|---|
| 1 | Claude background shell | killed by session teardown at 1 100 / 1 836 bars | **Witness A**: `artifacts/rc3_authority_freeze_partial_killed/` (1 102 bars, 12 days) |
| 2 | detached `Start-Process` from Claude's shell | killed at ~10:52Z 2026-09-18 at 1 745 / 1 836 bars; no Python error, truncated gzip; the machine also hard-reset at 18:56Z (Kernel-Power 41) | **Witness B**: `artifacts/rc3_authority_freeze/` (1 745 bars, 19 days) |
| 3 | **Windows Task Scheduler** task `BTMM_RC3_FINAL_AUTHORITY_3f9f790` | **COMPLETE** | final authority: `artifacts/rc3_authority_freeze_final/` |

Attempt 3 ran outside Claude's process tree: S4U logon (no stored password),
worker `python.exe[15600]` <- venv shim <- wrapper <- `svchost.exe -s Schedule`,
session 0; unlimited time limit, one instance, no automatic restart, normal
priority. The wrapper (`run_authority.py` in `C:/Users/user/btmm_ops/rc3_final/`,
outside the repo) refused to run unless HEAD was `3f9f790` with an empty
semantic diff and the output directory was new. `powershell.exe` hangs at
start-up under the S4U token on this machine, so the wrapper is Python. No
power setting was changed: the machine was already set to never sleep or
hibernate on AC; the wrapper additionally held a per-process keep-awake request.

### Result

| | |
|---|---|
| start / finish | 2026-09-18 19:35:17Z -> 2026-09-19 15:09:43Z (19 h 34 m) |
| bars | **1 836 / 1 836**, 20 trading days, 2026-08-10 -> 2026-09-04 |
| complete | **true** |
| wrapper exit code / Task Scheduler result | **0 / 0** |
| stderr | empty; no traceback |
| registry | 2 328 distinct POIs, 421 607 P3 / P5 rows, 12 104 P8 events |
| P8 by type | POI_ACTIVATED 2 200, BTMM_VALIDATED 1 394, PERMISSION_ENTERED 3 804, PERMISSION_LOST 3 301, POI_TERMINAL 1 405 |
| terminal reasons | MITIGATED 1 399, PROMOTED_TO_ORDER_BLOCK 6 |
| period digests | P3 `f3c6d5e7585e103e...`, P5 `c1f12bccf35668a1...`, P8 `45120200543b38a5...` |

### Frozen seven checks (`tests/parity_support/rc3_authority_verify.py`)

1. **Artifact integrity: PASS.** `complete=true`; 1 836 bars; 20 day
   manifests summing to 1 836 bars; P3 / P5 / P8 gzip streams close and read
   cleanly (21.6 MB / 15.9 MB / 0.16 MB); period digests present; HEAD.txt
   `3f9f790...`; stderr empty.
2. **Determinism: PASS against both independent-process witnesses.** Same
   semantic head and identical inputs (authority version, window, lookback,
   warm-up policy, session offset, all six series with provider / symbol /
   timeframe / file SHA-256). The manifests carry no separate configuration
   field, so configuration identity rests on the identical code SHA.

   | witness | days compared | P3 | P5 | P8 | ten daily counts | bar ranges |
   |---|---|---|---|---|---|---|
   | A (1 102 bars) | 12 (08-10 -> 08-25) | 0 mismatches | 0 | 0 | 0 | 0 |
   | B (1 745 bars) | 19 (08-10 -> 09-03) | 0 mismatches | 0 | 0 | 0 | 0 |

3. **Classified no-lookahead: PASS, 0 violations.** 1 572 STATIC POIs
   (source, availability and geometry immutable), 324 ROLLING PERIOD LEVELs and
   432 CONTEXT LEVELs (causal updates, availability never backwards, geometry
   only with new data, period never ahead of its bar); every P8 event joined to
   a same-bar P3 state and at or after its availability; activation on the first
   evaluated bar unless primed; native (poi_idx, priority) order in every bar;
   no row rewritten.
4. **Lifecycle / terminal: PASS.** 1 405 terminal POIs, 1 405 terminal events,
   exactly one each, every one on the registry terminal bar with a reason;
   terminal-bar inclusion 1 405 / 1 405; 0 rows after a terminal bar.
5. **Liquidity / stream order / primed state: PASS.** 120 equal-high/low
   clusters, 123 state updates, 3 clusters advanced (all causal, none backwards,
   none rewritten, lifecycle NOT_APPLICABLE retained, 0 POI_TERMINAL,
   0 BTMM_VALIDATED); 7 105 permission events, none before its POI's activation
   (565 on the activation bar, correctly ordered); primed set = 128 = run summary,
   160 permission events on 16 primed POIs, all real transitions.
6. **Cross-day continuity: PASS.** 20 contiguous days, no registry shrink,
   128-321 earlier-day POIs evaluated on every day's first bar, 956 of 2 328 POIs
   living across days.
7. **Semantic diff: PASS.** `git diff 3f9f790 -- src tradingview` empty; RC1
   (`143c0f88...`) and RC2 (`381f2fc2...`) untouched; sealed V1-A files untracked,
   unstaged, unread; authority window 2026-08-09 22:00 -> 2026-09-04 20:30 is
   outside the sealed OOS range.

## Verdict

**RC3 SEMANTIC FREEZE READY = TRUE**

* SEMANTIC CODE SHA = `3f9f790`, the only SHA the authority ran on.
* FREEZE RECORD SHA = the documentation / verifier-tooling commit that adds this
  section. The authority did NOT run on it; it changes no executable scanner code.
* PRODUCTION APPROVED = FALSE; MAIN MERGED = FALSE; TRADINGVIEW PUBLISHED =
  FALSE; LIVE BROKER = FALSE. Promotion awaits explicit author approval.
