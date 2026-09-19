# BTRC V1 — RC3 rollback and recovery

Nothing here is automatic. Every step is a human action; none of it merges,
promotes or publishes anything.

## Restore points

| point | SHA / version | what it is |
|---|---|---|
| RC3 semantic candidate | `3f9f790` | the frozen semantics (context gate, decision B, FVG 0.35, BTMM relay fix) |
| RC3 pre-context-gate | `be9bae1` | qualified engine, no context gate — the state every "before" measurement was taken on |
| RC3 pre-qualification | `5b4d5b9` | leg-origin OB lock, before FVG quality / same-origin arbitration |
| RC2 (frozen release) | `bec3ed8`, file `381f2fc2463c4eaa…` | presentation-only release candidate |
| RC1 (frozen release) | `2eff3e6`, file `143c0f8817c78bf4…` | first release candidate |

## Rolling the Python engine back

```bash
git log --oneline be9bae1..3f9f790
```

```bash
git revert --no-commit 3f9f790 68c03db c53d3ac 6400352
```

Reverting `6400352` alone removes the context gate, decision B and the frozen
FVG boundary test but leaves the fixtures expecting structure, so revert
`c53d3ac` with it. `3f9f790` (BTMM relay) is independent and can be kept.
Re-run the suite after any revert:

```bash
.venv/Scripts/python.exe -m pytest -q --ignore=tests/unit/test_v1a_m5_materiality.py
```

## Rolling the TradingView builds back

Version history is kept per script by TradingView: open the script in the Pine
Editor, use the script-name menu → **Version history…**, and restore USER to v29
or PARITY to v12 (the pre-context-gate builds). Do not delete script versions.
Detach an indicator only via Object Tree → right-click → **Remove** (never the
legend trash icon). RC1 and RC2 are separate saved scripts and are unaffected by
any RC3 rollback.

## Recovering an interrupted authority run

The daily authority writes durable artifacts at every trading-day boundary
(`write_artifacts(..., complete=False)`), so a killed run leaves:

* `daily_authority_manifest.json` / `.csv` — every completed day with its P3 /
  P5 / P8 digests (valid, usable evidence),
* `p3/p5/p8 *.ndjson.gz` — truncated at the kill point; the complete prefix is
  still readable (`rc3_authority_verify._rows` skips a partial final line),
* `replay_progress.log` — last bar and elapsed time.

Recovery: keep the partial directory (rename it, do not delete — it is an
independent-process determinism witness), then start exactly one new run on the
unchanged semantic SHA into a fresh `--output-dir`. There is no resume: the
authority replays the window from its start by design, because state must be
continuous.

Launch it through **Windows Task Scheduler**, never from a Claude/agent shell.
Background processes started from an agent shell (including a "detached"
`Start-Process`) die when the controlling session ends: two RC3 authority
attempts were lost that way (1 100 and 1 745 of 1 836 bars). The proven recipe
(RC3 final run, 2026-09-18/19):

* a Python wrapper OUTSIDE the repository that refuses to run unless HEAD is
  the semantic SHA with an empty `git diff <sha> -- src tradingview`, refuses an
  existing output directory, records start / exit code / finish, and holds a
  per-process keep-awake request (`SetThreadExecutionState`);
* a scheduled task with S4U logon (runs whether or not the user is logged on,
  no stored password), unlimited execution time, `MultipleInstances IgnoreNew`,
  `RestartCount 0`, `Priority 4` (Task Scheduler's default 7 is below-normal);
* do NOT use a PowerShell action: `powershell.exe` hangs at start-up under the
  S4U token on this machine. `cmd.exe` and the venv `python.exe` work;
* run a 2-minute harmless probe task first and confirm its parent is
  `svchost.exe -k netsvcs -p -s Schedule` before launching the long run.

`.venv\Scripts\python.exe` is a launcher shim: expect a launcher process and one
worker process for a single run. A power loss or hard reset still kills any
process; no software setting prevents that.

## If a semantic defect is found after the freeze

1. Stop the authority if one is running, and say so in the report.
2. Fix on a new branch, not by amending `3f9f790`.
3. Restart the authority once, on the new SHA, into a new artifact directory.
4. The old authority artifacts stay as the record of the superseded SHA.

## What must never be done during recovery

Force-push, destructive git cleanup, deleting authority artifacts, opening the
sealed V1-A material, replaying the OOS window 2026-07-14T17:15Z →
2026-08-03T06:45Z, merging to main, publishing to TradingView, or any live
broker action.
