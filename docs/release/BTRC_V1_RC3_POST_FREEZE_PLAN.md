# BTRC V1 — RC3 post-freeze plan (branches, bot handoff, demo runbook)

Written while the final authority runs. Nothing here is executed until the
freeze is recorded and the author approves. No merge, no publication, no live
broker, ever, without an explicit author instruction.

## 1. Branch policy after the freeze

`rc3-ob-origin-revision` @ `3f9f790` carries the RC3 semantics. Once the freeze
is recorded it stays closed to semantic edits. Everything else starts fresh from
that SHA:

| branch | purpose | may change |
|---|---|---|
| `rc3-post-freeze-diagnostics` | diagnostic fields and analytics that never alter mapping, freshness, mitigation, P5 or P8 | new read-only fields, audit tooling, reports |
| `bot-dryrun-integration` | dry-run bot pinned to the frozen scanner | bot code only (`botdryrun/`), never `src/btmm_ai_scanner/` |
| `rc3-post-freeze-visual` | presentation and labels | display layer only |

The first item queued for `rc3-post-freeze-diagnostics` is the author's optional
`pre_confirmation_touched` field: it records that price entered a POI's zone
between its source time and its availability. It is evidence only — it must not
feed freshness, mitigation, P5 scores/permissions or P8 events in RC3, and the
period digests must stay byte-identical with the flag present but unused.

A genuine semantic blocker is the only reason to reopen RC3: stop, record it,
fix on a new branch, rerun the authority once on the new SHA.

## 2. Bot continuation plan (paper / dry-run only)

Current state: `botdryrun/` on branch `bot-dryrun-v1` (`231cf73`). Its
`scanner_adapter.py` consumes the Level-A replay's
`analysis.poi_analysis.current_poi_states` plus P5 permissions and P8-style
actionability — qualified, mapped, context-gated POIs. It imports no detector
and re-implements no POI semantics. Its 55 tests pass against `3f9f790`
(read-only verification, throwaway worktree, no branch modified).

Next steps, in order:

1. Create `bot-dryrun-integration` from `3f9f790`, merge `bot-dryrun-v1` into
   it (bot files only), and record the pinned scanner SHA in
   `botdryrun/config.py` (or a `PINNED_SCANNER_SHA` constant) plus the README.
2. Add a bot-side assertion that the scanner SHA it was pinned to matches the
   repo it is running against; refuse to start on a mismatch.
3. Re-run the bot suite plus the real-scanner integration test against the
   pinned SHA; record counts.
4. Dry-run session on captured/historical bars, then paper forward-run on live
   data with the journals enabled.
5. Health/journal review after the first full session: POI intake counts,
   permission transitions, event-sourced restart recovery.

Hard constraints carried forward: PAPER / DRY-RUN / SIMULATION ONLY, no live
broker orders, no real-money execution, no profitability tuning, no
outcome-based rule optimization. The bot consumes semantics; it never defines
them.

## 3. Event / demo runbook (TradingView, live chart)

Preconditions: FXCM gold, ticker `FX:XAUUSD`, layout `bellforex`, chart
`/chart/6cu1b2O7/`, Basic plan (2 indicators / 2 live connections — work from
exactly one tab). Expect USER `[RC3 POI SEMANTICS DEV]` v30 attached; PARITY
`[RC3 PARITY DEV]` v13 may stay attached or be removed for a cleaner demo.

1. **Verify the build.** Pine Editor → script menu → the version footer must
   read v30; or in the console, `getAllStudies()` → `metaInfo().pine.version`.
2. **Acceptance sweep.** Step M1 → M5 → M15 → H1 → H4 → D1 → W1, allowing each
   to finish (`status().type === 2`). Every timeframe must show labelled zones
   and no runtime error. Recorded result: 8 boxes, 0 unlabeled, on all seven.
3. **What to show.**
   * M1: the clutter reduction — counter-trend and unstructured patterns stay
     raw, so the chart shows the structural POIs only.
   * M15 / H1: a pressure wick without its suppressed same-origin FVG, and a
     hammer replacing its pressure wick (decision B).
   * H4 / D1: a counter-trend pattern that only appears at the CHOCH that
     confirms its leg (decision A reversal context) — point at the box's
     availability, not its candle.
4. **Do not** change inputs mid-demo (each change re-runs the script), do not
   detach via the legend trash icon (use Object Tree → right-click → Remove),
   and do not open the Publish dialog.
5. **Recovery during a demo.** A blank pane usually means the tab was in the
   background while loading: bring the window forward and let the study finish.
   "Chart Not Found" means the wrong browser profile, not a lost session.

## 4. Artifact / report generators available for the demo or a review

```bash
.venv/Scripts/python.exe -m tests.parity_support.rc3_authority_verify artifacts/rc3_authority_freeze artifacts/rc3_authority_freeze_partial_killed
```

```bash
.venv/Scripts/python.exe -m tests.parity_support.rc3_authority_diff artifacts/rc3_context_delta/before_300 artifacts/rc3_context_delta/after_fix_300
```

```bash
.venv/Scripts/python.exe -m tests.parity_support.rc3_context_gate_audit
```

```bash
.venv/Scripts/python.exe -m tests.parity_support.rc3_non_fvg_pair_audit
```

All four read artifacts or replay unsealed captures; none of them is part of the
scanner runtime.
