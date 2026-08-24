# BTRC-V1 — P1-PERF-1 Pine Performance Optimization

Status, in two parts:

- **P1-PERF-1 — RUNTIME-VALIDATED IN TRADINGVIEW (2026-08-20).** Zero `RE10110`
  across M1/M5/M15/H1/H4/D1 on a Basic plan; §10a records the result and exactly
  what the evidence does and does not cover. Committed as `f88011e`.
- **P1-CLOSEOUT S/R correction (§12) + P1-SR-PERF-2 frontier (§14) + P1-SR-PERF-3
  transcription (§17) + PERF-4/4A capacity (§18) — IMPLEMENTED, LOCALLY
  VALIDATED, AND RUNTIME-VALIDATED IN TRADINGVIEW (2026-08-23).** Uncommitted.
  §12's brute-force form reintroduced intermittent `RE10110` on M1 and was
  replaced by §14 rather than shipped.

**Python↔Pine parity is now complete as well.** All nine P1 measurement fields
are resolved, and the live closed-bar / non-repaint gate has passed. Every
observed difference traced to the TradingView FXCM historical feed having been
revised since the frozen oracle was exported; **no Pine semantic defect was
established anywhere in P1.** The full evidence chain — nine-field matrix,
full-precision S/R boundary proof, and the live M1 gate — is recorded in
`BTRC_V1_P1_VALIDATION_EVIDENCE.md`.

P2 stays blocked: this is P1 scanner-measurement closure only, and carries no
production or live-trading approval.

Baseline: `9dfc3ec` (`fix(pine): correct P1 runtime and swing initialization`),
itself on `05a8989`. Semantic authority remains the Python measurement layer,
which is **untouched** by this work.

---

## 1. Observed RE10110 evidence

TradingView browser runtime testing of the corrected P1 port, account plan
**Basic**, symbol `OANDA:XAUUSD` (the FXCM feed was unavailable that session):

| Timeframe | Result | Analytical output |
|---|---|---|
| M1 | `RE10110` timeout (reproduced twice) | none — all plots `na` |
| M5 | intermittent `RE10110` | one clean run with full output; later runs timed out |
| M15 | clean (reproduced twice) | swings, equal levels, S/R, trendlines, displacement |
| H1 | `RE10110` timeout | none |
| H4 | clean | swings, equal levels (low), S/R, trendlines, displacement |
| D1 | `RE10110` timeout | none |

Verbatim TradingView text:

> Runtime error: RE10110 — The script takes too long to execute. The time limit
> is 20 seconds. To increase this limit, upgrade your plan.

Secondary symptom: whenever the script timed out, the whole chart pane stalled —
crosshair, Data Window and last-bar OHLC froze for minutes at a time.

No `RE10045`, no array out-of-bounds, and no drawing-object-limit errors occurred
in any run. **This is a cost problem, not a correctness problem.**

## 2. Runtime budget observed

TradingView applies a per-script execution budget. On the **Basic** plan the
message states **20 seconds**. The budget covers the whole historical pass, so
cost scales with `bars_on_chart × per-bar work`. That is why the same script
passes on M15/H4 (fewer bars loaded) and fails on M1/H1/D1 (many more): nothing
about the *analysis* differs between those timeframes.

**We are not trying to evade the limit.** The objective is for P1 to be
algorithmically efficient enough that it does not need a raised limit.

## 3. Pre-optimization complexity analysis

Let `N` = confirmed bars Pine executes, `W` = `lookbackWindow` (300),
`R` = `C_WINDOW_RADIUS` (2), `P` = single-candle pivots in the window,
`M` = merged pivots (`≤ P`), `C` = supersede survivors, `S` = confirmed swings in
the window (observed ≈ 10–40 on the tested charts).

Everything below sits inside `if barstate.isconfirmed`, so "per call" means
**per confirmed bar** unless the change gate says otherwise.

| Function | Call frequency | Window touched | Primary loop | Nested | Array allocs | Sorts | Drawing | Dependents | Opportunity |
|---|---|---|---|---|---|---|---|---|---|
| `f_median` | every median | — | O(m log m) | — | 1 copy per call | 1 per call | — | all detectors | consume caller's array |
| `f_medianRange` | 1×/bar | 20 bars | O(20) | — | 1 per call | via median | — | displacement | reuse scratch |
| `f_latestDisplacement` | 1×/bar | 20 bars | O(20) | — | 2 | 1 | — | parity plots | already bar-local |
| `f_detectSwings` → pivot scan | **1×/bar** | **full W** | O(W) | ×(2R+1) | 6 | — | — | everything | **verdict is final once a bar has R bars to its right** |
| `f_detectSwings` → plateau merge | 1×/bar | pivot list | O(P) | — | 6 + 1/merge | — | — | swings | fold group-by-type into one ordered pass |
| `f_detectSwings` → order sort | 1×/bar | merged list | **O(M²)** insertion | — | 1 | 1 (manual) | — | swings | **input is already ordered** |
| `f_detectSwings` → supersede | 1×/bar | merged list | O(M) | — | 6 | — | — | swings | none needed |
| `f_detectSwings` → confirmation | 1×/bar | **full W per candidate** | O(C·W) | — | — | — | — | swings | **start the scan at its lower bound** |
| `f_sweepEqualType` | on change, ×2 | swing list | O(S²) insertion sort + O(S²) cluster rebuild | — | 2/candidate | 1 (manual) | — | equal levels | small S; left as-is |
| `f_evaluateReaction` | **O(S²) times** on change | **full W** | O(W) | leg O(win) | 1 | 1 | — | S/R | **never breaks after the first hit** |
| `f_measureLeg` | per reaction | leg span | O(span) | — | 1 | 1 | — | S/R | consume median |
| `f_detectSR` | on change | window + swings | O(S) origins | × O(S) touches × (O(S) opposite scan + O(W) reaction) | several | 1 (manual) | — | parity plots | breaks + reaction break |
| `f_detectTrendlines` | on change | window + swings | **O(S²) anchor pairs** | × O(span) ATR rebuild + O(span log span) median + O(span) integrity + O(S) confirmation | 1/pair | 1/pair | — | parity plots | incremental slice + breaks |
| debug drawings | on change, if `debugMode` | bounded | O(min(k, cap)) | — | — | — | yes | — | already gated |
| parity table | `barstate.islast` | — | O(1) | — | **1 table always** | — | yes | — | build only in debug |

### Change gate as it stood

`changed = na(lastSwingCount) or newCount != lastSwingCount or newConfTime != lastSwingConfTime`

This kept equal levels / S/R / trendlines off most bars, so the **unconditional**
cost was `f_detectSwings` + displacement.

## 4. Dominant hot path

Two unconditional per-bar costs dominated, and both recomputed an answer they
already had:

1. **Full-window single-candle pivot rescan** — `O(W · (2R+1))` ≈ 1,500 index
   tests, ~4,400 array reads, on **every** bar. But `_find_single_candle_pivots`
   reads only `highs/lows/atr[idx-R .. idx+R]`, so a candle's verdict is **final**
   once it has `R` closed bars to its right. Re-deriving the whole window meant
   computing the identical verdict up to `W` times per candle.

2. **Meaningful-reversal search prefix** — the confirmation loop was written as
   `for [j, _] in lows` + `if j < searchStart: continue`. Python's original is
   `for j in range(search_start, n)`. The Pine form walked the window **from index
   0** for every candidate before reaching the first index it could use: with
   `searchStart` averaging ≈ W/2 and `C` ≈ 30 candidates, ~4,500–9,000 wasted
   iterations per bar, against a productive part that usually terminates in a
   handful of bars.

Together these put the always-on path at roughly **10k–20k elementary array
operations per confirmed bar**, i.e. `O(N · W)` overall — quadratic in chart
length for a fixed window ratio. That is the shape that blows a fixed
wall-clock budget as bar count grows, and it matches the observed
M15-passes/M1-fails split exactly.

On the change-gated path the two worst offenders were `f_evaluateReaction`
(scanned to the end of the window even after `reactionStart` was fixed — the
`if na(reactionStart)` guard turned every later iteration into a no-op) and the
trendline pair loop (rebuilt, re-allocated and re-sorted the anchor ATR slice for
every one of `O(S²)` candidate pairs).

## 5. Optimization architecture

Ten changes. Every one preserves the computed values exactly; the argument for
each is given in §7.

| # | Change | Complexity before → after |
|---|---|---|
| O1 | Incremental single-candle **pivot frontier** (persistent, absolute-indexed) | `O(W·(2R+1))`/bar → `O(2R+1)`/bar |
| O2 | Plateau merge in one ordered pass; **insertion sort removed** | `O(M²)` → `O(M)` |
| O3 | Reversal search bounded at `searchStart` (`while`, not skip-prefix) | `O(C·W)` → `O(C·k)`, k = bars-to-confirmation |
| O4 | `f_evaluateReaction` breaks at the first qualifying close | `O(W)` → `O(distance-to-reaction)` |
| O5 | S/R "opposite swing between" existence scan breaks at first witness | `O(S)` → early |
| O6 | Trendline integrity scan and confirmation scan break | `O(span)`, `O(S)` → early |
| O7 | Trendline anchor ATR slice grown incrementally into one reused buffer | `O(S²·span)` rebuild + `O(S²)` sorts → `O(S·W)` pushes |
| O8 | Change gate fingerprints the **whole** swing set | same cost, strictly more sensitive |
| O9 | `f_median` consumes its argument; scratch buffers replace per-call `array.new` | −1 alloc, −1 copy per median |
| O10 | Parity table constructed only under `debugMode` | −1 persistent object in client mode |

### Resulting per-bar shape

- **Unconditional (every confirmed bar):** advance the pivot frontier `O(2R+1)`;
  merge + supersede over the pivot list `O(P)`; confirmation `O(C·k)`; swing
  summary scan (early-exit, backwards) `O(S)`; displacement `O(20)`; fingerprint
  `O(S)`. All of these walk **tens** of entries, not the 300-bar window.
- **On swing-set change only:** equal levels, S/R, trendlines — now with early
  exits and no per-pair reallocation.

## 6. Incremental state model

```
NEW CONFIRMED BAR
   │
   ├─ incremental Wilder ATR                     (already incremental — unchanged)
   ├─ push candle into rolling window, prune to lookbackWindow
   ├─ displacement for this candle                (bar-local, 20-bar baseline)
   │
   ├─ PIVOT FRONTIER  ── decide exactly ONE candle (window index n-1-R)
   │                  └─ retire pivots older than absFirst + R
   │
   ├─ swing pipeline over the PIVOT LIST (not the candle window)
   │     merge plateaus → supersede same-direction runs
   │     → alternation + meaningful-reversal confirmation
   │
   ├─ swing-set fingerprint
   │     └─ unchanged → keep cached equal levels / S/R / trendlines
   │     └─ changed   → recompute those three
   │
   └─ publish latest-confirmed parity values (+ bounded debug drawings)
```

Pivots are keyed by **absolute confirmed-bar index**, not window index, so a
window shift cannot invalidate them; `f_detectSwings` subtracts `absFirst` on
read. Persistent state added: `confirmedBarCount`, `pvAbs`, `pvType`, `pvPrice`,
`pvAtr`, `pvTie`, `lastSwingFingerprint`, and two scratch buffers.

**No Python engineering machinery was ported** — no UUIDs, no JSON, no event
ledger, no worker processes, no host-memory gates, no filesystem journal. Pine
holds only the analytical state it needs. Identity remains semantic
(time / price / direction anchors), per the P0/P1 identity strategy; nothing
random was introduced.

## 7. Preserved semantics — equivalence arguments

**O1 — pivot frontier ≡ full rescan.** The batch scans window indices
`[R, n-1-R]`, i.e. absolute `[absFirst+R, absFirst+n-1-R]`. Absolute index `k` is
decided by the frontier on the bar where `confirmedBarCount == k+1+R`, at which
point `n ≥ 2R+1`, so every `k ≥ R` is evaluated **exactly once** and none is
skipped. Retirement drops `abs < absFirst + R`, which is precisely the batch's
lower bound. The verdict itself is unchanged (same 5-bar test, same tie
tolerance) and cannot change later because it reads only `[k-R, k+R]`, all of
which are closed by then. ATR at a given bar is fixed once computed, so the
stored `referenceAtr` and `tieTolerance` are the same values the batch would
read. ⇒ identical pivot multiset.

**O2 — one ordered merge pass ≡ group-by-type + merge + sort.** The frontier list
is ascending by index and holds **at most one pivot per candle**. Two same-type
pivots at consecutive indices are therefore necessarily *neighbours* in the mixed
list — nothing can sit between them. Conversely, if the immediate next entry has
a different type, no same-type pivot exists at `idx+1`, so no merge was available
in the type group either. The greedy two-at-a-time rule is preserved, and the
merged records come out already ascending by start index — which is exactly what
`swings.py:179` sorts for, with unique starts so stability is irrelevant. ⇒
identical merged records in identical order. The two-element median is written as
the pair's mean, which is its definition.

**O3 — bounded scan ≡ skip-prefix scan.** Both visit `j ∈ [searchStart, n)` in
ascending order and break on the same condition. The running min/max seed
(`lows[localConfIdx]` / `highs[localConfIdx]`) is unchanged.

**O4/O5/O6 — early exit on a settled result.** In each case the loop variable was
already latched (`if na(reactionStart)`, `oppositeBetween`, `integrityOk`,
`if na(confTime)`), so every iteration after the first hit was a no-op. Breaking
returns the same value.

**O7 — incremental ATR slice.** For a fixed first anchor, `si` is ascending by
`pivotEndIdx`, so the slice `[a1Idx .. a2Idx]` only grows. The median depends on
the **multiset**, not on insertion order, so extending one buffer yields the same
value as rebuilding it. `na` ATRs are skipped identically.

**O8 — strictly more sensitive gate.** The old fingerprint could miss a change
confined to the *middle* of the swing list, which the window's left edge can
cause because the alternation chain is re-seeded there every bar. The new
fingerprint folds every member in. It can only cause **more** recomputation, and
every recomputation produces the batch-faithful answer. See §9 for the disclosed
behaviour delta.

**O9/O10 — allocation and instrumentation.** `f_medianConsume` sorts the caller's
array instead of copying it; every call site builds a fresh (or scratch) array
and never reads it again, verified site by site. Building the parity table inside
the `debugMode` branch changes nothing analytical.

**Untouched by design:** swing definition, plateau/supersession rules,
alternation, meaningful-reversal threshold and timing, displacement thresholds
and classification, equal-level tolerance and clustering, S/R zone depth /
touch / pierce / reaction gates, trendline spacing, slope band, pierce and touch
tolerances, availability semantics, and the `barstate.isconfirmed` mutation
boundary. Every `C_*` constant is byte-identical. `lookbackWindow` stays at 300
(§B17) and is guarded by a test.

## 8. Pine-specific adaptations

- `while` replaces counted `for` in the bounded scans. Pine's `for a to b` counts
  **downwards** when `a > b` (the RE10045 class fixed in `9dfc3ec`); a `while`
  with an explicit lower bound has no direction hazard at all.
- Pivots are stored in **parallel arrays** rather than a UDT array — Pine has no
  struct-of-arrays optimisation and the frontier is mutated by `array.shift` from
  the front on retirement.
- Absolute indexing exists because Pine gives no stable identity to a window slot.
- `array.sort` is used in place, so the median helper is split into
  `f_medianOfSorted` (O(1)) and `f_medianConsume` (sort + read).

## 9. Remaining complexity and disclosed behaviour deltas

**Remaining complexity.** The change-gated detectors are still batch functions
over the window: `f_detectSR` is `O(S²)` reaction evaluations and
`f_detectTrendlines` is `O(S²)` anchor pairs. They are much cheaper per unit now,
but they are not incremental. If a future profile shows them dominating, the next
step is a genuine S/R and trendline frontier — a design task, not a tuning task.

**Behaviour delta vs the `9dfc3ec` baseline (disclosed, intentional).** The
strengthened fingerprint (O8) refreshes equal levels / S/R / trendlines on bars
where the old gate held stale values. Data-Window values on those bars will now
differ from the previous build. This moves output *toward* the batch-faithful
intent; it is not a change to any analytical rule.

**Pre-existing deviation — RESOLVED in P1-CLOSEOUT, see §12.** The paragraph
below is the P1-PERF-1-era finding, kept for the record; §12 supersedes it with
the audit verdict and the correction.

**Pre-existing deviation, NOT fixed here (audit finding).** `f_detectSR` calls
`f_evaluateReaction`, which scans forward to the end of the window. A reaction can
therefore first qualify on a bar where the swing set did **not** change — and the
change gate suppresses recomputation on exactly those bars, delaying that S/R
confirmation until the swing set next changes. Trendlines and equal levels are
**not** exposed to this: their confirmation comes from a touch *swing*, so it
cannot appear without a swing-set change. Fixing this properly means an
incremental S/R frontier (new bars re-test pending zones cheaply); forcing S/R to
run every bar instead would reintroduce the cost this cycle removes. Flagged for
a decision, deliberately left unchanged so P1-PERF-1 alters no semantics.

## 10. Runtime-validation protocol

No success may be claimed until all of this is executed in TradingView:

1. Load the working-tree source into the private DEV script; verify a byte-equal
   round trip. Require **0 compiler errors**.
2. `OANDA:XAUUSD` (or the canonical feed if it is available again). For each of
   **M1, M5, M15, H1, H4, D1**, with analytical inputs untouched, record:
   compile, load, runtime error, timeout, object-limit, swing output observed,
   displacement output observed.
3. **Pass condition: no `RE10110` on any of the six timeframes**, with
   `P1_swing_*` and `P1_disp_*` populated where history qualifies. M5's
   intermittency means each timeframe needs at least two loads.
4. **Equivalence spot-check against `9dfc3ec`** on M15 and H4 — the two
   timeframes the baseline completes. Compare `P1_swing_high_price`,
   `P1_swing_low_price`, `P1_disp_code`, `P1_disp_ratio`, `P1_equal_high`,
   `P1_equal_low`, `P1_sr_top`, `P1_sr_bottom`, `P1_tl_norm_slope` on the same
   confirmed bars. Expect equality except where §9's disclosed gate delta applies
   (S/R and trendline values may refresh earlier than the baseline).
5. Repeat with `P1 Debug Mode` **on** and **off**; confirm the drawings and parity
   table appear only when enabled.
6. Closed-bar observation on a chart that is *not* stalling — sample the forming
   bar twice while its high/low extends and confirm the published values do not
   move. This is the item the previous gate had to return INCONCLUSIVE.

## 10a. Runtime-validation result (TradingView, 2026-08-20)

Plan: **Basic**. Script saved as private DEV **version 4**; the editor buffer was
compared against the working tree byte-for-byte **before and after** testing —
identical both times, so no browser-only edit exists. Compile: **0 errors**.
`lookbackWindow` left at **300**; Python source untouched.

Primary feed: **`FXCM:XAUUSD`, which has recovered** — it carried real OHLC this
session (`O 4,514.34 H 4,514.56 L 4,513.94 C 4,514.35`), unlike the empty feed
seen on 2026-08-19. `OANDA:XAUUSD` was used additionally for H4/D1 and for one
debug-ON M1 run, deliberately, because the pre-optimization failures were
measured on OANDA.

**Zero `RE10110` on every timeframe.** Also zero array errors, zero
object-limit errors, and no other runtime error.

| TF | Attempt 1 | Attempt 2 | RE10110 | Responsiveness | Evidence |
|---|---|---|---|---|---|
| M1 | PASS (FXCM) | PASS (FXCM) | none | RESPONSIVE | all `P1_*` populated |
| M5 | PASS (FXCM) | PASS (FXCM) | none | RESPONSIVE | all `P1_*` populated |
| M15 | PASS (FXCM) | PASS (FXCM) | none | RESPONSIVE | all `P1_*` populated |
| H1 | PASS (FXCM) | not obtained | none | RESPONSIVE | all `P1_*` populated |
| H4 | PASS (OANDA) | not obtained | none | canvas suspended | DOM only — see below |
| D1 | PASS (OANDA) | not obtained | none | canvas suspended | DOM only — see below |

Before → after: **4 timeframes timed out (M1, M5 intermittently, H1, D1) → 0.**

The most direct comparison is **M1 on OANDA with Debug Mode ON**: the exact
configuration that previously hard-failed `RE10110` with no output now loads
completely, drawing swing labels, displacement markers, equal-level lines, an S/R
zone and trendlines, plus the parity table and all nine `P1_*` values.

Measurement families, post-optimization: swing engine **active**, swing sequence
**continues** (many alternating confirmed swings across history), displacement
**active** (non-zero codes ±1/±2 with numeric ratios observed), equal levels
**active**, support/resistance **active**, trendlines **active**.

### What this evidence does NOT cover

- **H4 and D1 rest on DOM evidence only** — indicator present, **no error badge**,
  legend emitting values. That is enough to rule out `RE10110`, but it is thinner
  than the M1–H1 evidence, which included live crosshair-driven Data Window reads.
- **H1 attempt 2 and the H4/D1 repeat attempts were not obtained.**
- Partway through the session the Chrome window became occluded and the browser
  **suspended the chart canvas and data pipeline**. Bars stopped painting and each
  timeframe took minutes to resolve. This is a browser-environment problem, not a
  Pine fault: it occurred with no `RE10110` present and equally blocked plain
  symbol switching. It is what cost the items above.
- **Closed-bar / no-repaint observation remains INCONCLUSIVE** for a second
  consecutive gate — rendering stopped before a forming bar could be sampled twice.
  Every state write is still inside `if barstate.isconfirmed` and every plot reads
  `var` state, but that is a code argument, not an observation.
- The **S/R delayed-confirmation limitation of §9 remains disclosed and unfixed**;
  nothing in this run tested for it.
- Basic caps the chart at **5,000 bars** (TradingView says so explicitly), so the
  pass is against a 5,000-bar ceiling, not unlimited history.
- **No claim of Python↔Pine parity is made.** Runtime testing shows the code paths
  execute within budget and produce output; parity requires a separate comparison
  against the canonical feed with matching candles.

## 11. Known limitations

- **Runtime-validated, but the §7 equivalence arguments are still analytical.**
  §10a shows the script runs within budget; it does not verify that the optimized
  pipeline returns the same records as the pre-optimization batch. The repository
  guards in `tests/unit/test_pine_p1_source_guards.py` are static and do not
  execute Pine. A value-for-value diff against `9dfc3ec` on the same bars is still
  outstanding.
- **Speedup is bounded, not measured.** The always-on path drops from roughly
  10k–20k array operations per bar to order 1k. TradingView exposes no profiler,
  so the only measurement available is pass/fail against the 20 s budget — which
  now passes everywhere it previously failed.
- **The Basic budget could still bind** beyond what was tested: the plan caps the
  chart at 5,000 bars, and every result in §10a sits under that ceiling. If
  `RE10110` reappears on a deeper history, the next lever is an incremental S/R
  and trendline frontier (§9), not a smaller window.
- **The 300-bar window remains ENGINEERING-PROVISIONAL** and unchanged. Records
  needing look-back beyond it are still not reproduced. Reducing it is a semantic
  change requiring its own equivalence analysis.
- **`float` vs `Decimal`** — unchanged from P1; compare parity with a numeric
  tolerance.
- **Parity is still not claimed.** Runtime testing on a non-canonical feed shows
  that code paths execute; it is not parity evidence.

---

## 12. P1-CLOSEOUT (C1) — support/resistance delayed-confirmation audit

Status: **SEMANTIC DEFECT CONFIRMED — corrected, uncommitted, awaiting
TradingView validation.**

### 12.1 Python source of truth

Read at `70235b6` (validated Python main), unmodified by this work.

| Question | Answer | Citation |
|---|---|---|
| Candidate source | Confirmed swings of the origin type, sorted by `meaningful_confirmation_time_utc` | `support_resistance.py:185-192` |
| Candidate availability | An origin enters the walk as soon as it is a confirmed swing | `support_resistance.py:194` |
| Zone geometry | `zone_depth = 0.10 × pivot_reference_atr`, anchored on `pivot_price` | `support_resistance.py:198-207` |
| Reaction-start search | `for index in range(search_start_index, n)` — first close beyond the zone boundary | `support_resistance.py:80-87` |
| Reaction window | `window_end = min(reaction_start_index + reaction_window_bars, n)`, `reaction_window_bars = 5` | `support_resistance.py:100` |
| Confirmation | The MFE bar of that window, once ATR-ratio, zone-clearance, leg efficiency and leg share all pass | `support_resistance.py:147-158` |
| Publication timing | `confirmation_time_utc = first_confirming_candle.availability_time_utc` | `support_resistance.py:299` |
| Recompute trigger | `analyze_market_measurements` recomputes S/R from the **whole candle tuple** on every call — no swing-change gate exists anywhere in the batch path | `analyzer.py:362-364` |

**Can a new candle change S/R with no new swing? YES — stated outright by the
Python incremental analyzer**, `analyzer.py:923-925`:

> "Must run every candle (not only when confirmed_swings changes): a reaction's
> bounded window can newly resolve purely from candle growth with no new swing
> involved."

The incremental machinery agrees structurally: `_advance_reaction_tracker`
(`analyzer.py:761`) is invoked for **every** non-`permanent` tracker on **every**
candle (`analyzer.py:973`, `analyzer.py:1033`), and a tracker only becomes
`permanent` once its 5-bar window is full (`analyzer.py:827-829`). Until then
both `reaction_start_index` and `confirming_candle_index` are re-derived from the
growing candle list, and `confirming_candle_index` may move — or appear — on a
candle that introduces no swing.

### 12.2 Pine evidence

`f_detectSR` was invoked **only inside `if changed`**, the swing-set fingerprint
gate. Its `f_evaluateReaction` scans `while ri < n` where `n = array.size(highs)`
— the window end, which advances on every confirmed bar. So: bar *N+1* closes,
the swing set is unchanged, the gate is false, `f_detectSR` never runs, and a
reaction that first satisfies its gate at *N+1* is withheld until the next swing
mutation — which is unbounded in the future.

### 12.3 Verdict

**B — SEMANTIC DEFECT CONFIRMED.** Pine could delay an S/R state transition that
Python publishes immediately.

Reproduced against the production Python implementation in
`tests/unit/test_pine_p1_sr_candle_growth_semantics.py`: with a **byte-identical
swing tuple** (all three pivots present by candle index 36), the zone is absent
at prefix 38 and present at prefix 39 — a flip caused purely by candle growth,
two candles after the last swing pivot, confirmed at the newest closed candle's
availability time (no lookahead).

### 12.4 Correction (SUPERSEDED by §14 — kept for the record)

> The brute-force correction described here was semantically correct and is
> what proved the defect was fixable, but TradingView exposed intermittent
> `RE10110` on M1 with it in place, so it was never committed. §14 replaces
> it with the incremental reaction frontier. The publication timing below is
> unchanged by that replacement.

Minimal and exact: **S/R is lifted out of the swing-change gate and recomputed on
every confirmed bar**, which is precisely what the Python batch does per candle.
Equal levels and trendlines stay behind the gate — both are pure functions of the
confirmed-swing set, and a trendline's confirmation comes from a touch *swing*,
never from a bar, so the gate is sound for them.

Nothing analytical changed: no threshold, no reaction depth, no pierce/touch
definition, no swing definition, no confirmation timing, no zone boundary, no
direction, no availability rule. `lookbackWindow` stays at 300.

Debug drawing is gated separately on an S/R zone-set fingerprint, so per-bar
recomputation does not become a per-bar clear-and-redraw. That fingerprint is a
**drawing** gate only and is guarded as such.

**Why not the tracker frontier.** C1.4's preferred model — a Pine-native
persistent reaction frontier mirroring `_ReactionTracker` — is a performance
device, not a correctness one; it would produce the same values. Building it is a
substantial new subsystem (per-origin and per-(origin, touch) persistent state,
semantic keys, window-edge retirement) written without a local compiler, in the
same cycle as a correctness fix. This project has deliberately kept correctness
and performance in separate authorised cycles, and that separation is what caught
the last two Pine defects cleanly. It is deferred to a possible P1-PERF-2, to be
opened only if measurement shows it is needed.

### 12.5 Cost of running S/R every bar (measured outcome: too high)

Estimated, not measured — this is the residual risk of the correction and the
thing TradingView validation must settle.

The reaction-start scan is the only potentially unbounded loop, and two facts
bound it in practice: P1-PERF-1 made it break at the first qualifying close, and
a zone is `0.10 × ATR` thick. A support zone's top sits a tenth of an ATR above a
local minimum, so the next close is almost always already beyond it — the scan
resolves in a few bars rather than walking the window. Everything after it is
bounded by `reaction_window_bars = 5`, including the leg measurement.

Per-bar estimate: ~20-30 operations per origin reaction, ~10-20 origins per type,
and a touch loop that only reaches its reaction check after the geometry and
opposite-swing filters pass — order **3-5k operations per bar**, against the
~15-20k that exhausted the budget pre-optimization and the ~1k always-on baseline
after it. That should stay inside the Basic 20 s budget, but it is a real
increase and it has not been measured.

**`RE10110` did reappear** — M1 attempt 1 of 3 on the 2026-08-20 gate, with
M5/M15/H1/H4/D1 and M1 attempts 2 and 3 all clean. Intermittent failure at
the budget boundary is exactly the signature M5 had before P1-PERF-1. The
answer taken was the tracker frontier (§14), not a looser gate: a gate that
can miss a transition is the defect this section fixes.

---

## 13. P1-CLOSEOUT (C2/C3) — validation protocols

### 13.1 Output classification (C3)

Audited over the whole source: **every published output reads only `var latest*`
state, and every write to that state happens inside `if barstate.isconfirmed`.**
There is no live forming-bar diagnostic among the outputs, so all of them are
legitimate evidence for a closed-bar observation.

| Output | Kind | Mutation gate | Expected intrabar behaviour |
|---|---|---|---|
| `P1_swing_high_price` / `P1_swing_low_price` | confirmed state | `barstate.isconfirmed` | frozen for the whole forming bar |
| `P1_disp_code` / `P1_disp_ratio` | confirmed state | `barstate.isconfirmed` | frozen — the forming bar is never pushed into the rolling window, so displacement always describes the last **closed** candle |
| `P1_equal_high` / `P1_equal_low` | confirmed state | `barstate.isconfirmed` + swing-change gate | frozen |
| `P1_sr_top` / `P1_sr_bottom` | confirmed state | `barstate.isconfirmed` (every confirmed bar since C1) | frozen |
| `P1_tl_norm_slope` | confirmed state | `barstate.isconfirmed` + swing-change gate | frozen |
| `Displacement up` / `Displacement down` shapes | confirmed-state display | `barstate.isconfirmed and debugMode and showDisplacement` | not drawn on the forming bar at all |
| Swing labels, equal-level lines, S/R boxes, trendlines | confirmed-state display | inside `barstate.isconfirmed` | not redrawn intrabar |
| Parity table | live **render** of confirmed values | `barstate.islast and debugMode` | re-renders every tick, but the text must not change |

### 13.2 Closed-bar runtime protocol (C3.1)

M1, Chrome kept foregrounded, Debug Mode off, one still-forming candle.

1. Note the forming bar's timestamp and the countdown, and record its current
   `high`/`low` from the chart legend.
2. **Sample A** — record all nine `P1_*` Data Window values.
3. Wait 15-25 s with the **same** bar still open.
4. **Sample B** — record the same nine values, plus the bar's `high`/`low` again.
5. **Sample C** — first recalculation after the bar closes.

Pass condition: **A == B for all nine values**, while the bar's own `high`/`low`
moved between the samples. The moving `high`/`low` is what makes the sample
meaningful — it proves the forming candle evolved and the confirmed state did
not follow it. C may differ from B (a bar closed; that is the point) and equality
of B and C is not required.

Result is one of `CONFIRMED_BAR_BEHAVIOR_CONSISTENT` /
`OBVIOUS_CONFIRMED_BAR_VIOLATION` / `INCONCLUSIVE`. If the bar's `high`/`low` did
not move during the wait, the sample proves nothing — retry.

### 13.3 Value-for-value comparison protocol (C2)

- **REFERENCE** = `9dfc3ec` (P1 correctness checkpoint). Extracted read-only via
  `git show 9dfc3ec:tradingview/btmm_poi_btrc_scanner_v1.pine` into a scratch
  file outside the repository, with **exactly one** line changed — the
  `indicator()` display title, so the two studies are distinguishable in the
  export. The checkpoint commit itself is untouched.
- **CANDIDATE** = the current `pine-v1` working tree.
- Same chart, same feed (`FXCM:XAUUSD`), same bars, both studies added to the one
  chart. Timeframes **M15** and **H4** — both builds are already known to execute
  there without `RE10110`.
- Export chart data, then compare offline with the scratch comparator, aligning
  strictly by bar timestamp and treating `na` as distinct from any number.
- Compared fields: `P1_swing_high_price`, `P1_swing_low_price`, `P1_disp_code`,
  `P1_disp_ratio`, `P1_equal_high`, `P1_equal_low`, `P1_sr_top`, `P1_sr_bottom`,
  `P1_tl_norm_slope` — every permanent P1 parity plot.
- Tolerance defaults to **exact**; any non-zero tolerance is printed in the
  comparator output so it cannot be applied silently.
- Never compare across providers.

**Expected-delta policy.** All non-S/R fields must be `EXACT_MATCH`; any
`UNEXPECTED_MISMATCH` among swings, displacement, equal levels or trendlines is
**BLOCKING**, because P1-PERF-1 claims to preserve those values exactly.
`P1_sr_top` / `P1_sr_bottom` are allowed to differ, in one direction only:
**reference `na` -> candidate numeric**, i.e. the candidate confirming a zone
*earlier* than the swing-gated reference did. That is the C1 correction working.
A candidate-`na` where the reference had a number, or a different zone price, is
**not** an expected delta and must be investigated.

If the export cannot expose both studies' plots reliably, the fallback is to run
the two builds one at a time on the same chart and export twice
(`--ref` / `--cand`), accepting that the two exports are taken at slightly
different wall-clock times and must therefore be truncated to their common bar
range. Do not substitute screenshots for an export.

---

## 14. P1-SR-PERF-2 — incremental support/resistance reaction frontier

Status: **IMPLEMENTED, LOCALLY VALIDATED, AND RUNTIME-VALIDATED IN TRADINGVIEW
(2026-08-23) — UNCOMMITTED.** Supersedes the brute-force correction of §12.4.

### 14.1 Why the brute-force correction could not ship

§12 established the defect and fixed it: S/R must advance on candle growth, not
on swing-set change. That correction was **semantically right** and is what
proved the fix works — but it recomputed the whole detector on every confirmed
bar, and TradingView Basic answered with an intermittent `RE10110` on M1 (1
failure in 3 loads; M5/M15/H1/H4/D1 clean). Intermittency at the budget boundary
is the same signature M5 had before P1-PERF-1, so it was not committed.

This section keeps the publication timing and removes the rescan.

### 14.2 Python semantics targeted

Read in full at `70235b6`; no production Python was modified.

| Concern | Rule | Source |
|---|---|---|
| Reaction start | first index in `range(search_start, n)` whose close is beyond the zone boundary | `support_resistance.py:80-87` |
| Anchor | `min(low)` / `max(high)` over `[search_start .. reaction_start]` | `support_resistance.py:91-98` |
| Window | `min(reaction_start + reaction_window_bars, n)`, `reaction_window_bars = 5` | `support_resistance.py:100` |
| MFE / clearance | window extremum vs anchor; clearance vs the breached boundary; first extremum wins ties | `support_resistance.py:105-118` |
| Reference ATR | `atr[reaction_start]`, rejected when absent or zero | `support_resistance.py:120-122` |
| Leg | `measure_leg` over `[reaction_start .. mfe_index]` | `support_resistance.py:127-145` |
| Qualification | ATR ratio, clearance ratio, leg efficiency, leg share — all four | `support_resistance.py:147-156` |
| Publication | availability time of the MFE candle | `support_resistance.py:298-299` |
| Tracker state | `search_start`, `zone_top`, `zone_bottom`, `is_support`, `last_checked`, `reaction_start`, `anchor`, `permanent`, `confirming_index` | `analyzer.py:716-739` |
| Tracker advance | catch up over *unchecked* candles only; bounded window re-evaluation; `permanent` once the window is full | `analyzer.py:761-895` |
| Cadence | every candle, for every non-permanent tracker | `analyzer.py:923-925`, `:973`, `:1033` |
| Terminal | `permanent = is_full_window`; `confirming_index` is re-derived until then and may move or clear | `analyzer.py:827-829`, `:890-894` |

### 14.3 State-transition table

`W` = `C_REACTION_WINDOW_BARS` (5). All indices are absolute confirmed-bar
indices, and every transition happens inside `barstate.isconfirmed`.

| State | Event | Condition | State update | Output effect | Terminal | Python |
|---|---|---|---|---|---|---|
| — | walk reaches an origin/touch for the first time | key absent | create at `lastChecked = searchStart-1`, then advance once | none yet | no | `analyzer.py:970`, `:1030` |
| UNSTARTED | new confirmed bar | zone height ≤ 0 | `permanent = true` | never publishes | **yes** | `analyzer.py:772-782` |
| UNSTARTED | new confirmed bar | no close beyond the boundary in `(lastChecked, n)` | `lastChecked = n-1`; anchor extended | none | no | `analyzer.py:789-816` |
| UNSTARTED | new confirmed bar | first breaching close at `j` | `reactionStart = j`; anchor final; evaluate window | may publish immediately | no | `analyzer.py:797-822` |
| STARTED | new confirmed bar | window not yet full | re-evaluate the ≤W slice; `confirming` re-derived | may appear, move, or clear | no | `analyzer.py:824-894` |
| STARTED | new confirmed bar | `windowEnd == reactionStart + W` | `permanent = true` | result frozen | **yes** | `analyzer.py:827-829` |
| any | origin leaves the window | `originAbs < absFirst` | tracker discarded | zone disappears with its origin | — | Pine 300-bar contract |
| PERMANENT | new confirmed bar | — | skipped entirely | carried forward | **yes** | `analyzer.py:769-770` |

### 14.4 Semantic key

`key = originAbs * 2^22 + searchStartAbs`, both absolute confirmed-bar indices.

- **Stable** — an absolute bar index does not move when the window slides, and
  one candle carries at most one pivot, so the pair identifies exactly one
  reaction.
- **Distinguishing** — two origins with different zones keep separate trackers
  for the same touch, because the zone is a function of the origin.
- **Deduplicating** — the same reaction on a later bar resolves to the same key
  and reuses the accumulated state.
- **Not random** — no UUID, no counter, nothing session-dependent.
- **Ordering-bearing** — `originAbs` occupies the high bits, so an ascending key
  array is also ascending by origin, which is what makes retirement a prefix
  removal. The stride bounds the design at 4,194,304 confirmed bars.

### 14.5 Lifecycles

**Candidate** — discovered by the walk, which only runs when the swing set or a
tracker resolution moved. Created lazily and advanced once on creation, exactly
as Python does at `analyzer.py:970`/`:1030`.

**Reaction start** — each candle is examined at most **once per tracker**, never
rescanned, and the anchor accumulates in the same pass. Because the anchor is
carried rather than recomputed, it stays correct after the window's left edge
passes `searchStart`. The FIRST qualifying candle is kept, as Python requires.

**Reaction window** — once started, only `[reactionStart, min(reactionStart+5, n))`
is read, at most 5 times, using the production rules (MFE, clearance, reference
ATR, `f_measureLeg`, four thresholds).

**Confirmation** — the MFE candle's availability time, stored on the tracker when
it resolves; the walk publishes it on that same bar. Not one candle early, not
one late, not at the next swing.

**Rejection vs permanence** — kept distinct, as Python does. `confirming = na`
means "does not currently qualify" and can still change while the window grows;
`permanent = true` means nothing can change it again. A permanent tracker with
`confirming = na` is a settled rejection and is never advanced again.

**Retirement** — a tracker dies when its origin leaves the active window.
Everything a live tracker references satisfies
`originAbs < reactionStartAbs < confirmingAbs < end`, so retiring on the origin
alone is sufficient to guarantee no out-of-window read.

### 14.6 Rolling-300 reconciliation

The frontier targets **`CORRECT_BATCH_SR_RESULT(active window ending at t)`**,
not Python's unbounded history — §4's requirement. That is achievable
incrementally because, while an origin stays in the window, its reaction depends
only on bars at or after `originAbs + 1`, and that set only ever grows at the
right. The left edge can therefore change the answer in exactly one way: by
removing the origin, which is precisely what retirement models.

Two consequences worth stating plainly:

- **The design requires a position-stable ATR.** A tracker pins
  `atr[reactionStart]`. Pine's ATR advances incrementally from the start of the
  chart, so the value at a bar never changes and the pin is safe. Production
  `detect_support_resistance_zones` re-seeds ATR from the first candle of
  whatever slice it is handed, which under a sliding window would move that
  value — so the model and oracle both take one full-history series, and
  `test_frontier_requires_position_stable_atr` pins the difference.
- **Swing reseeding is handled by identity, not by clearing.** A swing that
  vanishes and later reappears finds its tracker still keyed to the same
  absolute pivot; reusing it is not merely safe but identical, since the state
  is a pure function of `(searchStart, zone, candles)`.

### 14.7 Complexity

`A` = same-type confirmed swings in the window, `U` = unresolved trackers,
`T` = live trackers, `W` = 300.

| Stage | Brute force (§12.4) | Tracker frontier | Max active state | Per-bar work | Recomputation trigger |
|---|---|---|---|---|---|
| origin list build + sort | O(A²) insertion, ×2, **every bar** | same, **walk bars only** | `oi` ≤ A | 0 off-walk | swing change / tracker move |
| origin reaction | A × O(scan→W + 5 + leg), **every bar** | O(1) lookup + amortised O(1) advance | 1 tracker per origin | O(U) | new candle |
| "opposite between" | (confirmed origins) × A × O(A) | monotone cursor, amortised O(1) per touch | `opp` ≤ A | 0 off-walk | walk |
| touch reaction | (confirmed origins) × A × O(scan→W + 5 + leg) | O(log T) binary search | ≤ 1 tracker per (origin, touch) that clears geometry + opposite | O(U) | new candle |
| resolved-zone ordering | push order preserved | unchanged | ≤ A per orientation | 0 off-walk | walk |
| array allocations | `oi` ×2 plus a temporary inside every reaction and every leg | **none off-walk**; `oi`, `opp`, `out` on walk bars | — | 0 off-walk | walk |
| sorts | 2 insertion sorts/bar | 2 insertion + 2 `array.sort`, walk bars only | — | 0 off-walk | walk |
| drawing | fingerprint-gated | unchanged | ≤ `maxDrawPerFamily` | 0 unless the zone set changed | zone-set fingerprint |

**Unconditional per-bar cost: O(U)** — one bounded step per unresolved tracker.
The dominant `O(A·W)` and `O(A³)` terms are gone from the per-bar path, and the
`O(A²)` walk survives (as it does in Python, `analyzer.py:919-921`) but now runs
only on bars where the answer can actually differ.

`test_frontier_skips_the_walk_on_most_bars` asserts the walk is genuinely
skipped rather than merely intended to be.

### 14.8 State bounds

Trackers are keyed by (origin, searchStart) pairs drawn from confirmed swings
inside the window. A confirmed swing needs `2·C_WINDOW_RADIUS + 1 = 5` candles,
so `A ≤ 60` per type at `lookbackWindow = 300`. The hard bound is therefore
`A × (A + 1)` per orientation — ≤ ~7,300 in a pathological window, and tens in
practice, because a touch tracker is only created after geometry *and* the
opposite-swing test pass. Retirement runs on **every** bar as a prefix removal,
so the arrays cannot grow monotonically across an indefinitely long chart:
`test_frontier_state_stays_bounded_by_the_window` asserts no tracker outlives
its origin.

### 14.9 Local evidence

`tests/unit/test_pine_p1_sr_frontier_model.py` builds the same state machine in
Python and compares it, **at every prefix**, against a walk that calls the
production `_evaluate_reaction`. That oracle transcription is itself pinned to
the fully production `detect_support_resistance_zones`
(`test_batch_walk_transcription_matches_production`), so neither side can drift.

Covered: no candidate; candidate with no reaction start; reaction starting
immediately and several candles later; reaction resolving with no intervening
swing; partial window; resolution exactly at the window boundary; qualifying and
non-qualifying reactions; several concurrent trackers; competing origins and
touches; rejection; permanence; stability after permanence; a new swing arriving
while an older tracker is unresolved; an unchanged swing set across the bars that
resolve a reaction; window rollover at four short lookbacks and at the real 300;
origin eviction changing the outcome; deterministic zone ordering. Plus eight
seeded random streams compared at every prefix, and one 420-candle stream driven
across the real 300-bar rollover. **Oracle mismatches: 0.**

### 14.10 Ordering deviation found while doing this — RESOLVED in §15

Python ends `detect_support_resistance_zones` with
`results.sort(key=lambda c: c.confirmation_time_utc)` (`support_resistance.py:303`).
**The Pine walk has never had that final sort** — it emits all support zones then
all resistance zones, in origin-confirmation order. Since `P1_sr_top` /
`P1_sr_bottom` publish the LAST element, the ordering decides which zone is
published when both directions have qualifying zones.

It predates P1-SR-PERF-2 and was preserved exactly at the time, because that
cycle's brief required the existing ordering to be retained. It was then audited
on its own and **corrected** — see §15.

### 14.11 Remaining risks

- **Not compiled or executed anywhere yet.** The algorithm is validated; the Pine
  transcription is not. Type-level and syntax-level faults are still possible and
  only TradingView can rule them out.
- **The speedup is an operation-count argument, not a measurement.** TradingView
  exposes no profiler; the only observable is pass/fail against the 20 s budget.
- **The `O(A²)` walk survives.** If M1 still fails, the next lever is the walk
  itself (incremental origin/touch reconciliation), not a looser gate.
- **§14.10's ordering deviation is resolved in §15**, which changes which zone the
  parity comparison sees published relative to `9dfc3ec`.


---

## 15. P1-SR-ORDERING — final result ordering and published-zone selection

Status: **ORDERING SEMANTIC DEFECT CONFIRMED — corrected, uncommitted.**

### 15.1 Python's canonical order

| Question | Answer | Source |
|---|---|---|
| Canonical final order | **ascending `confirmation_time_utc`**, stable | `support_resistance.py:303` |
| Anything after the sort? | `_finalize` appends in candidate order and never re-sorts | `analyzer.py:236-276` |
| Pre-sort insertion order | SUPPORT orientation first, then RESISTANCE; within each, origins ascending by `meaningful_confirmation_time_utc` | `support_resistance.py:176-194` |
| Equal confirmation times | `list.sort` is **stable**, so ties keep that insertion order | `support_resistance.py:303` |
| Secondary key on pivot time / price / direction / ID? | **None.** The only tie-break is insertion order | `support_resistance.py:303` |
| Selected "current" support | **Does not exist.** Nothing downstream picks one zone — POI iterates the whole tuple | `poi/reference_zones.py:27-32`, `poi/analyzer.py:359` |
| Selected "current" resistance | same — no per-direction selection anywhere | as above |
| Multiple qualifying zones | all are returned, ordered as above | `support_resistance.py:285-304` |

So Python has **one** ordering rule and **no** selection rule. The incremental
analyzer applies the identical sort (`analyzer.py:1068`), as does the replay
frontier (`analyzer.py:1674`).

### 15.2 What Pine publishes, and why the order matters

`P1_sr_top` / `P1_sr_bottom` are a **P1-only parity interface**: one scalar pair,
taken from the **last element** of the resolved array. Under Python's canonical
order that means *the most recently confirmed zone*, which is the only reading
consistent with the parity table's "latest confirmed" framing.

Pine had **no final sort**. Its last element was therefore "the last RESISTANCE
zone by origin order", or the last support zone when no resistance zone
qualified — not the latest by confirmation time.

### 15.3 Verdict — B, ORDERING SEMANTIC DEFECT CONFIRMED

Demonstrated on a concrete reachable state
(`test_documents_the_ordering_defect_pine_had`): a resistance zone confirming at
00:37 and a support zone confirming at 00:57.

| | published zone | confirmed |
|---|---|---|
| Python canonical (last after the stable sort) | SUPPORT `96.200 / 96` | 00:57 |
| Pine before this fix (last of the unsorted array) | RESISTANCE `104 / 103.800` | 00:37 |

Same two zones, different order, **different published zone** — and Pine's was
the older of the two.

Worth recording: the seeded property streams from §14 **never produce two
simultaneous zones** (0 of 1,121 sampled states), so that coverage could not have
caught this. `test_random_streams_could_not_have_caught_this` asserts that, and
will fail loudly if the streams ever start producing multi-zone states, at which
point the ordering tests should adopt them.

### 15.4 Correction

`f_walkSR` now ends with an explicit ordering pass over an index array using the
composite key **(confirmationTime, insertionIndex)**, ascending. That reproduces
both halves of Python's rule — the primary sort and the stability — without
relying on any incidental Pine array behaviour, which §8 of the brief forbids.
The published scalar still reads the last element; it is now the canonically
latest zone. The debug boxes inherit the same order, so "last `maxDrawPerFamily`"
also matches Python's last N.

Nothing else moved: no threshold, no zone geometry, no confirmation timing, no
direction handling, no swing/ATR/displacement/equal-level/trendline logic,
`lookbackWindow` still 300, closed-bar boundary untouched.

### 15.5 Why it does not undo P1-SR-PERF-2

The sort lives **inside `f_walkSR`**, which runs only when the swing set or a
tracker resolution actually moved — never on the per-bar path. Its input is the
*published zone set*, not the swing set or the candle window: in the sampled
states that is 0-2 records and it is bounded above by the qualifying origins in
the window. An O(Z²) insertion sort over that is negligible, and
`test_pine_sr_ordering_runs_only_when_the_set_is_rebuilt` fails if the sort ever
escapes the walk.

| | Before | After |
|---|---|---|
| Per-bar work | unchanged — O(unresolved trackers) | unchanged |
| Walk-bar work | O(A²) walk | O(A²) walk + O(Z²) order, Z = published zones |
| State | unchanged | unchanged — the order is recomputed, never stored |

### 15.6 Rolling-window behaviour

A published zone disappears exactly when its origin is retired, and the ordering
pass re-runs over whatever remains, so the next published zone is the one a fresh
batch over the current window would select. A stale selection cannot survive:
`test_case_07_rolling_window_removal_of_the_selected_result` drives six
lookbacks and requires eviction to actually change the published zone, and
`test_case_10_candidate_retirement_clears_the_selection` requires an 8-bar window
to publish nothing at all.

### 15.7 Evidence

`tests/unit/test_pine_p1_sr_ordering.py` — 14 tests, every one comparing the
model's **published zone** against the production oracle's on **every prefix**:
one support result; two support results at different times; two resistance
results at different times; both directions at once; three competing results;
equal-timestamp stability; rolling-window removal of the selected result; a newly
resolved result becoming canonical and not becoming canonical; candidate
retirement; semantic-key deduplication; and the 300-bar rollover. Plus the two
tests that pin the defect itself. **Oracle mismatches: 0.**

### 15.8 Effect on the parity comparison

`9dfc3ec` carries the unsorted order, so `P1_sr_top` / `P1_sr_bottom` will differ
from the candidate on any bar where both directions have qualifying zones — a
**second** expected S/R delta, distinct from the earlier-publication one of §12.
Both are corrections toward Python; neither is an unexpected mismatch. The
non-S/R fields are unaffected.

---

## 15. P1-SR-PERF-3 — measurement campaign (2026-08-20, offline)

Status: **MEASURED, NOT IMPLEMENTED.** No Pine source changed in this campaign.
P1 remains open; P2 remains unauthorised.

### 15.1 What triggered it

The P1-SR-PERF-2 candidate passed M1 x2, M5 x2, M15, H1 x2 and H4 on TradingView
Basic with `FXCM:XAUUSD`, then failed **D1 attempt 1**:

> Runtime error: RE10110 — The script takes too long to execute. The time limit
> is 20 seconds. To increase this limit, upgrade your plan.

Two details worth keeping. First, the **"Heavy script — close to your plan's
runtime limit"** banner that version 5 displayed was **absent** on this build,
including on the load that timed out — so that banner is not a usable predictor.
Second, only **one** D1 attempt was made (the stop rule fired), so it is not known
whether the D1 failure is deterministic or intermittent.

### 15.2 Canonical D1 data — NOT AVAILABLE

No FXCM TradingView **D1** export exists locally. The only real dataset is
`BTMM_REAL_DATA/DATASETS/xauusd_2026_07_pilot` — manifest provider `FXCM`,
"FXCM XAUUSD native TradingView CSV reference exports" — and it contains **M1,
M5 and M15 only**. The M1 file's SHA256 matches its manifest entry
(`a49890c8…`), so the dataset is intact; it simply has no daily timeframe.

Per the campaign's own rule, that makes a **measurement-authorised PERF-3
implementation impossible tonight**, and no production optimisation was made.
Everything below is measurement, proof and tooling.

### 15.3 The harness

`tests/performance_support/p1_sr_diagnostics.py` — developer-only, no production
dependency. Replays the validated frontier prefix-by-prefix over an exported CSV
and reports the work counters, with explicit provider/symbol/timeframe/lookback
configuration and a window fingerprint that never mutates the source file. It
labels any non-FXCM-D1 run as a **CONTROL MEASUREMENT**. Ready for tomorrow:

```bash
uv run python -m tests.performance_support.p1_sr_diagnostics \
    --csv <FXCM D1 export> --provider FXCM --symbol XAUUSD --timeframe D1 \
    --lookback 300 --window-bars 300 --json d1.json
```

`tests/performance_support/p1_sr_stress.py` runs the deterministic oracle
campaign described in §15.6.

### 15.4 Control measurements (canonical FXCM data, lookback 300)

900-bar replays, so the rolling window genuinely slides and retirement engages.
All three timeframes passed the data-quality checks (no duplicate timestamps, no
zero prices, no impossible OHLC).

| | M1 | M5 | M15 |
|---|---|---|---|
| swings in window (max / median) | 69 / 56 | 70 / 59 | 73 / 58 |
| **pair visits per bar** (mean / max) | **184.1** / 620 | **174.7** / 560 | **182.1** / 769 |
| tracker advances per bar (mean) | 0.78 | 0.77 | 0.80 |
| walks per bar | 0.56 | 0.52 | 0.55 |
| origin reaction lookups | 25,839 | 24,878 | 26,372 |
| sort invocations / elements | 2,535 / 51,819 | 2,355 / 50,440 | 2,485 / 53,165 |
| new semantic pairs | 243 | 243 | 250 |
| **pair visits per new pair** | **682** | **647** | **656** |
| pair retirements | 163 | 170 | 185 |
| peak active trackers | 84 | 87 | 95 |

Two things stand out.

**The profile is timeframe-independent.** `A` — confirmed swings inside the
window — sits at 50–73 on every timeframe, because it is bounded by the 300-bar
window rather than by the bar duration. So the earlier guess that "D1 fails
because A is larger there" is **not supported**; D1 more likely fails because
TradingView serves it more chart bars, and total cost is bars x per-bar cost.

**The tracker frontier is not the cost.** It advances ~0.8 times per bar. The
cost is the origin x touch walk: ~180 pair visits and ~29 origin lookups per bar,
of which roughly **99.85% re-derive relationships that did not change** (650–680
visits for every genuinely new pair).

### 15.5 Static Pine audit — the O(A²) claim is source-supported

`f_walkSR` (line ~784), per walk, per orientation (x2):

| Step | Line | Work |
|---|---|---|
| build `oi` (same-type origins) | 792 | O(S) |
| insertion-sort `oi` by confirmation time | 796–806 | **O(A²)** worst case |
| build `opp` (opposite confirmation times) | 812 | O(S) |
| `array.sort(opp)` | 815 | O(A log A) |
| outer origin loop | 817 | O(A) |
| tracker lookup per origin | 829 | O(log T) |
| **inner touch loop** | 837 | **O(A) ⇒ O(A²) pair visits** |
| tracker lookup per qualifying pair | 846 | O(log T) |

So the quadratic enumeration is real and is in the production path, not merely
hypothesised. Measured, it fires on ~55% of bars.

A second, smaller finding: `oi` and `opp` — both pure functions of the swing set
— are rebuilt and re-sorted on **every** walk, including the ~32% of walks that
fire because a *tracker* resolved rather than because the swing set changed. That
work is provably redundant on those bars.

### 15.6 Semantic evidence gathered

Deterministic oracle campaign, comparing the frontier model against the
production Python S/R implementation at **every prefix**:

| | |
|---|---|
| streams | 600 (300 seeds x random + structured) |
| prefixes / oracle comparisons | **246,674** |
| **oracle mismatches** | **0** |
| published zones exercised | 406,305 |
| tracker resolutions | 17,476 |
| pair retirements | 8,115 |
| peak active trackers | 98 |
| duration | 192 s |

The purely random streams almost never satisfy the geometric touch test, so a
**structured** generator was added that tiles the zone-forming shape with seeded
jitter. Without it the campaign would have compared empty tuples and proved very
little; with it, publication, ordering, ties and retirement are all exercised.

### 15.7 Hot-path verdict

**A — origin x touch enumeration is the dominant structural cost**, on the
evidence of both the control measurements and the source audit. But the
measurement is on **control** timeframes, not canonical D1, so the campaign's own
rule applies: **PERF-3 is not measurement-authorised and was not implemented.**

When D1 data arrives, the intended architecture is unchanged from §14.4's
deferred plan: a delta-driven candidate-pair frontier keyed on semantic swing
identity, so that a bar with no swing change does **zero** pair discovery. The
cheap first increment, justified by the source audit alone, is to cache the
per-orientation `oi` / `opp` lists while the swing fingerprint is unchanged.

### 15.8 What is still unproven

- D1 behaviour of the current candidate (one failed attempt, no repeat).
- Whether removing the pair-enumeration redundancy is *sufficient* to clear the
  20 s budget on D1 — that needs the D1 measurement.
- Everything requiring the browser: parity against `9dfc3ec`, the S/R oracle
  classification, and the closed-bar observation.

---

## 16. P1-SR-PERF-3 — pair frontier (model implemented, Pine NOT transcribed)

Status: **EXECUTABLE SPECIFICATION COMPLETE AND MEASURED. PINE UNCHANGED.**
The Pine source is byte-identical to the P1-SR-PERF-2 candidate; §16.6 explains
why the transcription was stopped rather than guessed.

### 16.1 D1 data — still unavailable, and why

TradingView Basic gates chart-data export behind a paid plan. The Table view's
**Download data** button opens *"Export data to where you need it — Upgrade your
plan"* (Current plan: Basic, Recommended: Premium). Therefore:

- **no D1 CSV was created**;
- **no Table-view scraping was performed** (that would route around the same
  restriction in substance);
- **no plan upgrade was performed**.

**D1 exact pair-count sizing remains NOT MEASURED.** One correction to §15.2: the
Table view scrolls back past **Aug 2023**, so FXCM daily history is ample — over
300 closed candles exist. Only the download mechanism is blocked.

### 16.2 Architecture (implemented in the model)

Two exact caches replace repeated origin x touch rediscovery.

**Orientation lists.** `oi` (same-type origins, ascending confirmation time) and
`opp` (opposite-type confirmation times) are pure functions of the swing set, so
they survive a walk that fired because a reaction resolved.

**Per-origin fold cache.** Each origin's fold result is retained and re-run only
when:

1. one of **its own** reactions changes resolution — the tracker key is
   `(originAbs, searchStartAbs)`, so a changed tracker names its origin directly;
   or
2. a swing **delta** can reach it, decided semantically:
   - an **opposite-type** add/remove feeds the has-opposite-between test for
     every origin of that orientation, so it invalidates the orientation;
   - a **same-type** add/remove can only alter a fold if the changed swing sits
     inside that origin's zone, because zone geometry is the fold's first gate on
     every touch and depends on nothing else. One O(1) geometric test per
     (origin, delta) pair replaces a full re-fold.

Semantic swing key: `pivotEndTime` (unique per swing, stable while the swing is
valid, no array positions, no UUIDs). Semantic pair key: unchanged from
P1-SR-PERF-2 — `(originAbs, searchStartAbs)`.

Reaction semantics, canonical ordering, the 300-bar contract, retirement and the
closed-bar boundary are all untouched.

### 16.3 Measured effect — canonical FXCM controls, 900-bar replays, lookback 300

| | M1 | M5 | M15 |
|---|---|---|---|
| pair visits before | 165,712 | 157,247 | 163,907 |
| pair visits after | **64,310** | **64,647** | **64,836** |
| **reduction** | **−61.2%** | **−58.9%** | **−60.4%** |
| origin reaction lookups | 25,839 → 9,883 | 24,878 → 9,883 | 26,372 → 10,337 |
| sort invocations | 2,535 → 1,879 | 2,355 → 1,803 | 2,485 → 1,861 |
| mean pair visits / bar | 184.1 → **71.5** | 174.7 → **71.8** | 182.1 → **72.0** |
| median pair visits / bar | 106.5 → **0** | 5.5 → **0** | 19 → **0** |
| fold reuse share | — → **61.7%** | — → 60.3% | — → 60.8% |

Outputs are **byte-identical** before and after: published zones (140 / 684 /
421), resolved zones, pair retirements (161 / 170 / 185) and permanent trackers
(229 / 225 / 236) all match exactly.

The median falling to zero is the §2.7 property: an ordinary confirmed bar now
does no pair work at all.

### 16.4 Semantic evidence

Deterministic campaign against the production Python oracle, every prefix:

| | before PERF-3 | after PERF-3 |
|---|---|---|
| streams / prefix comparisons | 600 / 246,674 | 600 / 246,674 |
| published zones | 406,305 | **406,305** |
| tracker resolutions | 17,476 | **17,476** |
| retirements | 8,115 | **8,115** |
| peak active trackers | 98 | **98** |
| total pair visits | 12,535,961 | **2,772,329 (−77.9%)** |
| **oracle mismatches** | 0 | **0** |

Identical results, 78% less work. Plus 40 unit tests covering the required
scenario matrix, ordering, ties, rollover and bounded state.

### 16.5 Complexity

| | before | after |
|---|---|---|
| ordinary bar (no swing change, no reaction change) | no walk | no walk |
| walk from a reaction resolving | O(A²) + 2 sorts per orientation | O(affected origins x A), lists reused |
| walk from a swing delta | O(A²) + 2 sorts per orientation | orientation rebuild + O(A x delta) geometric tests, then only affected folds |
| state | trackers, window-bounded | trackers + one fold per origin, window-bounded |

### 16.6 Why the Pine transcription was stopped

The model change is exact and measured. Transcribing it needs a new UDT, three
persistent parallel-array caches, an ordered swing snapshot and delta
reconciliation — written without a compiler, **stacked on top of the
P1-SR-PERF-2 Pine frontier that has never yet passed a TradingView gate**. A
first draft of that Pine already carried several defects (a missing sort helper,
an O(A²) snapshot rebuild, `array.remove` inside a descending loop, and
reconstructing `referenceAtr` by dividing `zoneDepth`).

Two large blind Pine layers stacked before either is validated would also make a
D1 failure unattributable. The next step is therefore **D1 x3 against the
existing version 7**, which decides whether the PERF-3 Pine layer is needed at
all and, if it is, gives it a measured baseline. The Pine design is specified
above and in the model; nothing about it is lost by sequencing it second.

---

## 17. P1-SR-PERF-3 Pine Transcription

Status: **TRANSCRIBED, LOCALLY VALIDATED, AND CONFIRMED ON TRADINGVIEW
(2026-08-23) — compiles and runs clean; 12/12 performance matrix, zero
`RE10110`.** Uncommitted.

### 17.1 Why it was deferred once, and what changed

§16.6 stopped at the Pine boundary: the first draft carried four defects and
would have stacked a second unvalidated Pine layer on P1-SR-PERF-2. The author
decided that re-testing version 7 could not validate PERF-3 (version 7 does not
contain it) and authorised the transcription directly. The four defects were
addressed rather than carried forward:

| Early-draft defect | Resolution |
|---|---|
| Referenced a sort helper that was never written | `f_srSortCandByConfTime` implemented, with the `a < 1` prefix guard the counted-loop rule requires |
| O(A²) snapshot rebuild (nested membership search) | Replaced by a two-cursor **O(A) merge**; both lists are ascending by pivot-end time, asserted in `test_confirmed_swings_are_ascending_by_pivot_end_time` |
| `array.remove` inside a descending loop | Removed entirely — retirement rebuilds from survivors into `srFoldKeep`, so no index can be invalidated mid-loop. Guarded by `test_pine_fold_retirement_never_removes_while_iterating` |
| `referenceAtr` recovered as `zoneDepth / ratio` | `SRCand` and `SRFold` both carry `referenceAtr` directly. Guarded by `test_pine_reference_atr_is_stored_not_reconstructed` |

Two further defects were caught during the transcription itself: a ternary that
would have indexed one past the end of the snapshot, and `na`-seeded key scalars
that re-entered Pine's `na`-comparison trap. Both were removed by reading the
keys only inside the branch where both cursors are in range.

### 17.2 Semantic swing key — uniqueness proof

The key is **`pivotEndTime`** alone; no composite was needed.

The classifier emits at most one single-candle pivot per candle index. The
plateau merge combines *disjoint* consecutive same-type pairs, so every pivot
index belongs to exactly one merged record and merged end-indices are distinct.
Supersession keeps a subset, and the confirmation loop emits at most one swing
per survivor. Therefore no two simultaneously valid confirmed swings share a
pivot-end candle, and `pivotEndTime` is unique. Asserted empirically over 36
prefixes in the same test that pins the ordering.

### 17.3 Model → Pine mapping

| Model concept | Pine | State owner | Mutation trigger | Retirement trigger |
|---|---|---|---|---|
| swing snapshot | `srSnap : array<SRCand>`, ascending key | main block | swing fingerprint change | replaced wholesale each delta |
| swing key | `SRCand.key` = `pivotEndTime` | — | — | — |
| delta result | `chgType` / `chgPrice` in `f_srApplyDelta` | local | swing fingerprint change | per call |
| orientation lists | `srCandSupport/Resist`, `srOppSupport/Resist` | main block | swing fingerprint change | rebuilt each delta |
| fold | `SRFold` | `srFold` | fold recompute | delta invalidation |
| fold cache | `srFold : array<SRFold>`, ascending `originKey` | main block | walk | origin leaves swings / delta reaches it |
| pair key | `(originAbs, searchStartAbs)` packed int | `srKeys` | tracker creation | origin leaves window |
| reaction tracker | `SRTracker` | `srTrk` | every confirmed bar | prefix retirement on `srKeys` |
| dirty set | `srDirty : array<int>` | main block | reaction resolution change | cleared each bar |
| canonical order | composite `(confirmationTime, insertionIndex)` sort | end of `f_walkSR` | each walk | — |

### 17.4 Complexity

| | before | after |
|---|---|---|
| ordinary bar | no walk; O(unresolved trackers) | unchanged |
| walk from a reaction resolving | full O(A²) enumeration + 2 sorts/orientation | O(A) cache lookups + only the dirty origins' folds |
| walk from a swing delta | full O(A²) + 2 sorts/orientation | O(A) merge + O(F × |delta|) geometry + only reached folds |
| pair discovery, swings unchanged | O(A²) | **0** |

Bounded state, lookback 300: swings A ≤ 150 theoretical (73 measured), folds
F ≤ A, trackers window-bounded (98 measured peak), snapshot = A. Nothing scales
with lifetime chart history.

### 17.5 Loop and array audit

Every new array access is bounded: binary searches use `lo <= hi` with
`hi = size - 1` (empty array ⇒ body unreachable); `f_srFoldLowerBound` returns
`[0, size]`; the insertion sort writes only to `b + 1 ∈ [0, a]`; the merge reads
each cursor only where it is in range; `array.get(opp, cursor)` is guarded by
`cursor < array.size(opp)`. The only counted loop introduced is `for ot = 0 to 1`.
**No `array.remove`, `array.shift` or `array.pop` in any new code**, and the one
`array.insert` uses a lower-bound index.

### 17.6 Evidence and what is still missing

Model measurements are unchanged by the transcription (M1/M5/M15 pair visits
64,310 / 64,647 / 64,836; campaign 246,674 prefix comparisons, 406,305 published
zones, **0 oracle mismatches**), which confirms no shared helper drifted.

**These are Python model counters. They validate the algorithm, not Pine
runtime.** Still outstanding: TradingView compile, D1 ×3 on Basic, the remaining
timeframe matrix, reference-vs-candidate parity, the S/R oracle classification of
every divergence, and the closed-bar observation. The D1 CSV remains unavailable
because Basic gates chart-data export behind a paid plan.

## 18. P1-PERF-4 — Bounded historical execution (`calc_bars_count`)

### 18.1 What actually failed

PERF-3 compiled on TradingView (version 8, 1,523 lines, 0 compiler errors) and
its first D1 execution on `FXCM:XAUUSD` completed and published all nine parity
outputs, alongside a **Heavy script** warning: *"This script is close to your
plan's runtime limit (20s)."* A later recalculation of the same chart did not
finish inside the budget, the outputs were withdrawn, and the legend entered:

> `Runtime error: RE10110` — "The script takes too long to execute. The time
> limit is 20 seconds. To increase this limit, upgrade your plan."

The script was therefore sitting *on* the limit rather than under it: the same
code both passed and failed the same chart within minutes.

### 18.2 Execution-model correction

An earlier note in this repository speculated that each realtime D1 tick
replayed the whole dataset. **That was wrong**, and PERF-4 is not built on it.
Pine's documented model is: the initial/reload execution processes the
accessible historical bars; afterwards the script re-executes only on the
current realtime bar, using rollback; add/save/refresh and similar reload events
run the historical dataset again. Basic's 20-second budget applies to that
dataset execution.

A static audit confirms the script matches that model. Outside the
`if barstate.isconfirmed` block there is nothing but the declaration, the
inputs, the constants, function *definitions*, nine `plot` calls, two
`plotshape` calls, and the debug table guarded by `barstate.islast and
debugMode`. **REALTIME_HEAVY_PATHS = 0.** So the budget is consumed by
historical execution, and the lever that matters is how many historical bars run
at all — `calc_bars_count`.

### 18.3 The whole historical dependency

The script has **no direct history references** (`series[n]` — zero occurrences)
and **no `ta.*` built-ins**; the Wilder ATR is hand-rolled and incremental. Each
confirmed bar reads `high/low/open/close/time` at offset 0 and pushes them into
its own arrays. So every dependence on older bars is carried in explicit
persistent state, and each piece of that state is bounded:

| State | Bound |
| --- | --- |
| `wHigh/wLow/wOpen/wClose/wOpenT/wAvailT/wAtr` | pruned to `lookbackWindow` (300) |
| `pvAbs/pvType/pvPrice/pvAtr/pvTie` | retired below `absFirst + C_WINDOW_RADIUS` |
| `srKeys/srTrk` | prefix-retired below `absFirst * C_SR_KEY_STRIDE` |
| `srCand*/srSnap/srFold/srFoldKeep/srDirty` | rebuilt/retired from the window's swing set |
| `latest*` publication scalars | sticky, but refreshed whenever the window's swing set changes |
| `atrPrevClose/atrWarmSum/atrWarmCount/atrPrevFinal` | **unbounded — the only true carry** |

Wilder ATR is an IIR recurrence, `atr_t = (atr_{t-1}(P-1) + tr_t)/P`. It never
formally forgets its seed; it only decays toward it. **That single channel is
the entire truncation risk**, and closing it closes all of them: if the
truncated ATR equals the full-history ATR everywhere the protected region reads,
every detector receives byte-identical inputs and must produce identical output.
That makes the horizon a proof obligation rather than a sampling exercise.

### 18.4 Bar-index shift audit

TradingView renumbers bars under `calc_bars_count`: the first calculated bar
becomes `bar_index = 0`. The audit result is unusually clean:

**`bar_index` does not appear anywhere in the source.**

Absolute positions come from `confirmedBarCount`, a script-local counter over
bars the script itself executed — already independent of TradingView's
numbering. Every use is shift-invariant:

- `absFirst + idx` / `- absFirst` — window/counter conversion, differences only.
- `minAbs`, `srMinKey` — retirement thresholds, both derived from `absFirst`.
- `key = originAbs * C_SR_KEY_STRIDE + searchStartAbs` — identity and ordering
  within one run; a constant offset preserves the ordering the binary searches
  rely on. Truncation makes the counter *smaller*, so it also reduces the
  `searchStartAbs < 4194304` headroom requirement rather than straining it.
- Swing, fold, cluster and zone identity is keyed on **UTC times**
  (`pivotEndTime`, `meaningfulConfTime`, `confirmationTime`), which no index
  shift can touch.
- None of the nine published outputs is an index.

**BAR_INDEX_SHIFT_INVARIANT = TRUE.**

### 18.5 Measuring the ATR warm-up

`atr_convergence_bars` returns the number of bars after a truncation point
before the truncated series becomes **identical** (exact `Decimal` equality) to
the full-history series.

| Source | Start positions | K min | K mean | K max |
| --- | --- | --- | --- | --- |
| FXCM M1 | 213 | 719 | 817 | 920 |
| FXCM M5 | 202 | 713 | 835 | 915 |
| FXCM M15 | 134 | 752 | 826 | 898 |
| Adversarial seed distortion (x50 ... x5000) | 6 | 830 | — | **945** |

This matches theory rather than merely happening: at `Decimal` precision 28 the
base cost is `28*ln10 / ln(14/13)` = 870 bars, plus about `13.5*ln(d0/atr)` for
the initial discrepancy — the x5000 fixture predicts 985 and measured 945.

Two consequences worth stating. First, `Decimal(28)` is *stricter* than Pine's
float64 (~15.95 digits, about 496 bars), so a horizon proved here is
conservative for the runtime that will actually execute. Second, the ceiling
adopted below (950) covers seed distortions up to roughly 16,000x.

### 18.6 Choosing the horizon

A bar is analytically valid once the ATR is exact at the **left edge of its
window**, i.e. after `lookbackWindow + K` processed bars:

```
C_P1_MIN_CALC_BARS = 300 (window) + 950 (warm-up ceiling) = 1250
```

The binding bar is the **earliest** protected one, not the last:

```
processed at bar T-300 = N - 299  >=  1250   =>   N >= 1549
```

| N | valid output bars | spare over the 300 protected | D1 reduction |
| --- | --- | --- | --- |
| 1500 | 251 | -49 (too short) | 70% |
| 1600 | 351 | 51 | 68% |
| **1800** | **551** | **251** | **64%** |
| 2000 | 751 | 451 | 60% |

**`P1_CALC_BARS_COUNT = 1800`.** Not the smallest passing number: the first
exactly-matching horizon on real data was 1200 (M1, M5) and 1350 (M15), and
11 of the 20 adversarial fixtures still diverged at 1200. Sitting on the empirical
minimum would have been fitting the horizon to the datasets that happened to be
measured. 1800 clears the structural bound with 251 bars of margin while still
removing roughly two thirds of D1 historical execution.

### 18.7 Real-data truncation results

Full-history replay vs truncated replay, all nine outputs compared on each of
the final 300 bars. Values are mismatched bars out of 300.

| N | 300 | 450 | 600 | 750 | 900 | 1000 | 1100 | 1200 | 1350 | 1500 | 1600 | 1700 | 2000 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | 300 | 300 | 300 | 300 | 297 | 120 | 120 | **0** | 0 | 0 | 0 | 0 | 0 |
| M5 | 300 | 300 | 300 | 300 | 288 | 288 | 51 | **0** | 0 | 0 | 0 | 0 | 0 |
| M15 | 300 | 300 | 300 | 300 | 300 | 232 | 232 | 232 | **0** | 0 | 0 | 0 | 0 |

`P1_tl_norm_slope` is consistently the last field to converge: trendlines apply
four separate ATR tolerances (horizontal, too-steep, touch, pierce), so they
amplify a residual ATR difference more than any other family. Equal levels and
S/R converge earlier; the swing and displacement scalars earliest.

### 18.8 Adversarial and randomized evidence

Twenty deterministic fixtures place a named structure immediately before the
truncation boundary — swing, plateau, supersession, alternating chain,
displacement leg, equal-high/low straddle, support/resistance origin, reaction
start, five-bar reaction window crossing, canonical S/R result, trendline
anchor, high/low swing density, monotonic leg, compression, exact-equality
plateau, window rollover, multiple simultaneous trackers.

| Horizon | Fixtures clean | Fixtures diverging | Mismatched bars (of 6,000) |
| --- | --- | --- | --- |
| 900 | 0 / 20 | 20 | 5,833 |
| 1200 | 9 / 20 | 11 | 384 |
| 1600 | 20 / 20 | 0 | 0 |
| **1800 (selected)** | **20 / 20** | **0** | **0** |

That the fixtures fail loudly below the bound is what makes their agreement at
the selected horizon meaningful.

At the selected horizon the three canonical FXCM datasets were re-run against
their own FULL-history baselines:

| Dataset | Bars | Protected bars compared | ATR warm-up at the truncation point | Mismatches |
| --- | --- | --- | --- | --- |
| FXCM M1 | 6,914 | 300 | 867 | **0** |
| FXCM M5 | 6,632 | 300 | 839 | **0** |
| FXCM M15 | 4,928 | 300 | 815 | **0** |

Randomized structured streams (fixed seeds 1000..1199, regime-mixed so every
detector family has material): **200 streams, 60,000 protected-bar comparisons,
TRUNCATION_ORACLE_MISMATCHES = 0.**

The whole campaign is reproducible from
``tests/performance_support/p1_truncation_campaign.py``.

### 18.9 Too-few-bars safety

Declaring `calc_bars_count` makes TradingView expose a **Calculated bars** input
defaulting to 1800. Lowering it re-creates exactly the failure mode PERF-4 just
bounded, so the script now refuses to publish rather than publish quietly wrong
values:

```pine
bool p1HistoryOk = confirmedBarCount >= C_P1_MIN_CALC_BARS
plot(p1HistoryOk ? latestSwingHighPrice : na, "P1_swing_high_price", ...)
```

All nine parity plots and the debug displacement marker are gated; the debug
table gains one status row naming the shortfall and the value to restore. The
guard is **publication-only** — it appears nowhere inside the confirmed-bar
block, so it changes no analytical rule, no stored state and no confirmation
timing. A source guard enforces that.

> **Superseded by §19 (P1-PERF-4A).** The guard described here checks warm-up
> only, so a run of 1250-1799 calculated bars would still have published a few
> late bars from a horizon the product was never validated on. PERF-4A adds a
> separate dataset-capacity gate and makes those cases fail closed. §19.5 holds
> the current client behaviour table; the paragraphs above remain as the record
> of why the guard exists at all.

### 18.10 Expected effect, and what it is not

D1 on Basic exposes roughly 5,000 bars. Historical bar executions go from about
5,000 to 1,800 — roughly **64% fewer**. Per-bar cost is bounded (window fixed at
300, tracker and fold state retired to the window), so total work should fall
close to proportionally.

**This is not a guaranteed wall-clock reduction.** It is a count of bar
executions removed. Whether the remaining work fits inside Basic's 20 seconds is
decided by TradingView, not by this document.

### 18.11 Scope and remaining gates

The Pine diff against the PERF-3 candidate is exactly: one declaration
parameter, two named constants, one guard boolean, nine gated plots, one gated
debug marker, one debug table row. **No detector, ordering rule, window,
tolerance or state machine was touched**, and `lookbackWindow` remains 300.
Production Python in `src/` is untouched; the harness supplies the ATR Pine
would have had via a test-only injection whose transparency is asserted against
production output.

Still outstanding, all requiring TradingView: compile of the PERF-4 candidate,
D1 x3 on Basic, the remaining timeframe matrix, reference-vs-candidate parity,
the S/R oracle classification, and the closed-bar observation.

## 19. P1-PERF-4A — Validated history-capacity guard

### 19.1 The question PERF-4 did not ask

PERF-4's guard was `confirmedBarCount >= C_P1_MIN_CALC_BARS`. That answers
*"has this bar warmed up?"* and nothing else. It does **not** establish that
TradingView handed the script the horizon the product was validated on.

The gap is concrete. Set **Calculated bars** to 1300 and the run contains 51
bars whose processed count clears 1250. Each of those bars is individually exact
— and the validated 1800-bar contract is absent entirely. PERF-4 would have
published them. A trading signal drawn from an unvalidated execution history is
exactly what must not reach a client, so PERF-4A separates the two questions and
requires both.

### 19.2 Three numbers, stated plainly

They are easy to conflate, and conflating them is what produced the gap:

| Number | Name | Meaning |
| --- | --- | --- |
| **300** | `lookbackWindow` | The analytical rolling window. A semantic parameter; not a performance knob. |
| **1250** | `C_P1_MIN_CALC_BARS` | The per-bar warm-up floor **inside an adequately sized run** — the point at which a bar's own 300-bar window carries an exact ATR. |
| **1800** | `C_P1_CALC_BARS` | The selected execution horizon, the `calc_bars_count` the declaration requests, **and** the dataset capacity the product requires. |

**Why 1250 is not the minimum allowed Calculated-bars setting.** 1250 describes
a bar's position inside a run; it says nothing about whether the run is the
validated one. Treating it as the product minimum would license the 1300-bar
case above. Capacity is therefore measured against 1800, and warm-up against
1250 — two thresholds because there are two questions.

### 19.3 Capacity from dataset metadata

Pine documents `last_bar_index` as one less than the total number of bars
available to the script, so:

```
accessible bars = last_bar_index + 1 = min(chart bars, "Calculated bars")
```

**Off-by-one derivation.** Both terms of that `min` are monotonically
non-decreasing while the script runs: the setting is fixed for the run, and the
chart only ever gains bars. An opening realtime bar can therefore only raise the
accessible count, never lower it — so a configuration that passes during the
historical pass cannot be revoked by a bar opening, and **no downward tolerance
is required**. Enumerated:

| Situation | accessible | Verdict |
| --- | --- | --- |
| Market closed, last bar historical, default setting | 1800 | pass |
| Market open, 1799 confirmed + 1 forming | 1800 | pass |
| Chart far longer than the cap | 1800 (capped) | pass |
| New realtime bar opens on a passing chart | ≥ 1800 | pass |
| User lowers the setting by one | 1799 | **fail** |
| Symbol has less history than the horizon | < 1800 | **fail** |

No upward tolerance is applied either. 1799 is not 1800; admitting it would
quietly redefine the product contract rather than enforce it.

**One residual unknown, named rather than assumed.** Whether TradingView counts
an open realtime bar inside or outside the `calc_bars_count` cap decides whether
a setting of 1799 reports 1799 or 1800 accessible bars. That is observable only
on TradingView and belongs to the pending gate. It has no correctness
consequence — the difference is one bar of publishable region (550 vs 551), and
every bar in either case is independently warm-gated — so it is a one-bar policy
boundary, not a soundness question. The failure mode is fail-closed and
immediately visible.

### 19.4 The publication gate

```pine
int  p1DatasetBars = last_bar_index + 1
bool p1CapacityOk  = p1DatasetBars >= C_P1_CALC_BARS      // 1800, dataset capacity
bool p1WarmupOk    = confirmedBarCount >= C_P1_MIN_CALC_BARS  // 1250, per-bar warm-up
bool p1HistoryOk   = p1CapacityOk and p1WarmupOk
```

O(1), no scan, no state, no iteration. It sits at the publication interface;
`last_bar_index`, `p1DatasetBars` and `p1CapacityOk` appear nowhere inside the
`barstate.isconfirmed` block, and a source guard fails the build if they do.
`REALTIME_HEAVY_PATHS` remains 0.

### 19.5 Fail-closed behaviour

| Calculated bars | Behaviour |
| --- | --- |
| 1800 (default) | Publishes the 551 bars whose processed count reaches 1250. |
| > 1800 (incl. 0 = all bars) | Publishes; historical execution grows again and RE10110 becomes possible. |
| 1250 – 1799 | **All nine outputs `na`** — some bars are warm, the validated horizon is absent. |
| < 1250 | **All nine outputs `na`.** |
| Symbol shorter than 1800 bars | **All nine outputs `na`.** |

**Short-history symbols fail closed, by author decision.** PERF-3 would have
computed from whatever history existed. That answer is not wrong arithmetic —
it is simply outside the validated P1 history contract, and the product does not
present trading signals from an unvalidated horizon.

The status indication is deliberately one bounded debug-table row reading
`INSUFFICIENT CALCULATED HISTORY`, with the two counts. It does **not** claim the
user lowered a setting: a short symbol history produces the identical state and
the script genuinely cannot tell them apart.

### 19.6 Proving the whole published region

PERF-4 compared the final **300** bars. The gate admits **551**. The 251-bar
difference was structurally implied but unmeasured, so it was measured: every
bar the gate would publish, on all nine outputs, full history versus
`calc_bars_count = 1800`.

| Corpus | Runs | Published bars compared | Mismatches |
| --- | --- | --- | --- |
| FXCM M1 / M5 / M15 | 3 | 1,653 | **0** |
| Adversarial boundary fixtures | 20 | 11,020 | **0** |
| Randomized structured streams | 200 | 110,200 | **0** |
| **Total** | **223** | **122,873** | **0** |

The publication threshold therefore stands at 1250; no correction was needed.
This is the sufficient condition from §18.3 confirmed across the entire region
rather than a fragment of it — reproducible with
`p1_truncation_campaign.py --protected 551`.

### 19.7 Invariants

`last_bar_index` serves capacity metadata and nothing else — it appears in
swing identity, `SRFold` identity, the S/R pair key, `originAbs`,
`searchStartAbs`, trendline identity, canonical ordering and analytical geometry
exactly zero times, all guarded. `lookbackWindow` remains 300, PERF-3 is
untouched, production Python in `src/` is untouched, and the confirmed-bar
boundary is unchanged.
