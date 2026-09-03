# BTRC-V1 — P5 transport extension: runtime resource attribution

Status: **Classification D (not reliably reproducible), extended P6 DEV completes
every operation tested — GO for extended ATOMIC**
Branch: `pine-p4-btmm`
Date: 2026-09-03

---

## 1. What triggered this investigation

The first live attach of the extended P6 DEV (26-field P5 transport) surfaced:

> "Heavy script. This script is close to your plan's runtime limit (20s)."

The author's instruction was explicit: attribute the cause before touching
anything, and do not bound or approximate proven semantics merely on
suspicion. This document is that attribution.

## 2. Method

A/B comparison, one script attached at a time (per the author's Phase 1
instruction), between:

* **Control** — the pre-extension closed P6 DEV, extracted byte-for-byte from
  commit `6f72b06` (sha256 `168229e8170099bf60c8d2fc6761b36b3bbe586cc5c6142b7e5b11e43876f434`,
  matching the recorded P6 closure hash exactly), retitled and saved as a
  separate TradingView script `P6 CONTROL ORIGINAL (pre-extension, 6f72b06)`
  so it could be attached without overwriting the live P6 DEV.
* **Extended** — the current P6 DEV (26-field `P5TransportExt`), already live.

Both on FX:XAUUSD M15, same account, same layout. **The account plan is
Basic, capped at 2 indicators per chart** — discovered when a third attach was
blocked — which set the isolation methodology: remove one before adding the
other, verified each time via the Object Tree (the small title overlay at
top-left of the chart was found unreliable earlier in this campaign and is
not used as evidence here).

## 3. Operations performed and results

| # | Script | Operation | Warning? | Failure? |
|---|---|---|---|---|
| A1 | Control (isolated) | fresh attach | No | No |
| A2 | Control (isolated) | full page reload | No | No |
| A3 | Control (isolated) | M15 → 45m → 1h → M15 | No | No |
| B1 | Extended (isolated) | fresh attach, then 20s observation | No | No |
| B2 | Extended (isolated) | M15 → 1h | No | No |
| B3 | Extended (isolated) | 1h → M15 | No | No |
| C1 | Both attached | fresh combined attach, 30s observation | No | No |
| B4 | Extended (isolated) | **cold full page reload**, 20s observation | No | No |

Every operation completed with correct output (real, plausible plot / data
window values on both scripts; the earlier live session separately confirmed
the extended script's `P5X` log lines populate correctly on FXCM). **Zero
runtime failures (no RE10110 or equivalent) across eight operations.**

The ONE occurrence of the heavy-script warning happened during the very first
live attach of the extended script, in the prior session (MEGA-AUTONOMOUS-16),
immediately after the paste-and-save that fixed the UDT literal-default
defect. It did **not** reproduce on any of the eight operations run for this
investigation, including a cold reload of the exact same script — the
condition closest to replicating that first occurrence.

## 4. Classification

Per the author's Phase 4 options:

* **A** (pre-existing, unaffected by the extension) — not supported: the
  control never showed the warning across four operations, so it cannot be
  called pre-existing in the sense of "present on both equally."
* **B / C** (extension is a material or contributing cause) — not supported
  either: the SAME extended script, under matching or heavier combined load,
  did not reproduce the warning on seven subsequent attempts.
* **D** (results too unstable to attribute cleanly) — **this is the honest
  classification.** The single occurrence happened only on the extended
  script and never on the control, which is a real, non-dismissible
  observation — but one occurrence out of eight comparable attempts is not a
  reproducible signal, and TradingView's own runtime-limit warning is a
  measured, server-side profile that can vary run to run under matching code.

**What this is not**: a claim that the extension is free. It is a claim that
the live evidence does not support treating it as a *material, reproducible*
cause — which is the specific bar the author set for undertaking a
semantics-adjacent rewrite.

## 5. The operation-count model (Phase 8)

Since TradingView exposes no internal timing API, `tests/parity_support/p6_p5x_operation_count.py`
counts element visits mechanically instead — a platform-independent, exact
measure of algorithmic cost.

Eight per-bar, per-context scans exist in the extension. Two are bounded and
cheap regardless of history (`transWindowCount` capped at 4,
`dispWindowCount` capped at 3). Four scan backward with an early exit
(`contStreak`, `priorOppStreak`, `exhaustFlag`, the pullback impulse search) —
their true cost is bounded by the length of a matching run, not by total
history. **Two cannot exit early**: the pullback role scan (bounded by swing
count — observed 50–90 live) and `dispClsAtTrans`, which scans the full
300-element `lookbackWindow` on every confirmed bar of every context, for as
long as any transition exists.

Using the live capture's observed swing/transition counts (70 and 8):

```
per bar, per context:  533 element visits
  transWindowCount   4
  dispWindowCount    3
  contStreak         8
  priorOppStreak     8
  exhaustFlag       70
  impulse search    70
  role scan         70
  dispClsAtTrans   300   <- the single largest fixed cost, by a wide margin

worst-case total, 1250-bar warm-up, 6 contexts:
  533 x 1250 x 6 = 3,997,500 element visits
```

The scaling is **linear** in warm-up length — verified mechanically
(`test_operation_count_table_at_each_requested_warmup_length`) at 300, 600,
1200, 1250 and 1800 bars — with no quadratic term anywhere in the model. Four
million simple array/integer comparisons is a cost any interpreted runtime
clears in a small fraction of a second, not twenty. This is consistent with —
though does not by itself prove — the live finding that the warning did not
reproduce: the extension's own added cost, even at a pessimistic worst case,
is small in absolute terms.

**If a future capture does show a reproducible, material slowdown**,
`dispClsAtTrans` is where to look first: it is the only scan bounded by the
full 300-element window rather than by actual swing/transition counts, and it
is reducible (a rolling max over a bounded window) without touching any of
the twenty-two other reductions this campaign has already proven correct
against the authoritative oracle.

## 6. Decision

Per the author's Phase 5 branch: *"does extended P6 DEV consistently complete
all required operations? If YES: continue to extended ATOMIC carefully."*

**Yes** — eight consecutive operations, zero failures, correct output every
time, including the cold-reload condition closest to the original trigger.

No reducer was rewritten. No semantics were bounded, approximated, or
touched. The 26-field oracle, the Pine-equivalent model, the mutation
campaign and the field contract are exactly as committed in `a6842a2`.

**Resource classification: D — GO for extended P6 ATOMIC, proceeding
carefully and re-running this same isolation discipline if a warning
resurfaces during that deployment.**
