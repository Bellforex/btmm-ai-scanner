# BTRC-V1 — P1-PERF-1 Pine Performance Optimization

Status: **IMPLEMENTED AND RUNTIME-VALIDATED IN TRADINGVIEW (2026-08-20).**
Zero `RE10110` across M1/M5/M15/H1/H4/D1 on a Basic plan — see §10a for the
result and for exactly what the evidence does and does not cover. This is
**runtime validation only, NOT full Python↔Pine parity.** P2 stays blocked.

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
