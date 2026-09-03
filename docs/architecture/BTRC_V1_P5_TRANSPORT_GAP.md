# BTRC-V1 P5 — Transport gap blocking the T1 port

Status: **BLOCKED — author decision required**
Found: 2026-09-03, at the start of P5 implementation
Branch: `pine-p4-btmm`

## The gap

`assess_trend` evaluates each authority timeframe from its structure history.
Per timeframe it consumes:

| requirement | kind | in the P6 tuple? |
|---|---|---|
| `current_state.direction` | scalar | yes (`p2_direction`) |
| `current_state.analyzed_swing_count` | scalar | yes (`swing_count`) |
| `current_state.availability_time_utc` | scalar | **no** |
| `_continuation_streak` | trailing run over the transition SEQUENCE | **no** |
| `_alternation_count` over the last `range_window` (4) transitions | bounded window of the SEQUENCE | **no** |
| `_prior_opposite_streak` | run before the latest transition | **no** |
| `_exhaustion` | compares the last TWO same-type swing prices | **no** |

The P6 projection returns:

```
[qBars, swingCount, lastType, lastPrice, lastConfT, eqCount,
 qFingerprint, qDataset, dispCode, dispRatio,
 p2Dir, p2TransCount, p2LastTrans, p2LastBrokenLvl]
```

Counts and LAST-element values. No sequence, no second-to-last swing, no
current-state availability time.

This is not a defect in P6. §3a of the P6 architecture named five *collections*;
a `request.security` tuple cannot carry a collection, so the implementation
transports scalar reductions, and P6 closed on 30/30 parity **of those
reductions**. The reductions are simply not sufficient for T1.

## What is actually missing is small

Every missing quantity is a bounded scalar the requested context could compute
itself, because the context already holds the full transition and swing arrays:

```
continuation_streak      int
alternation_count_4      int
prior_opposite_streak    int
prev_swing_high_price    float   (exhaustion needs the last TWO highs)
prev_swing_low_price     float   (and the last TWO lows)
last_swing_high_price    float
last_swing_low_price     float
state_availability_time  int
```

Roughly eight scalars per timeframe. The tuple would go from 14 to ~22 values,
which Pine supports, and the six request contexts stay at six.

## The options, with costs

**A. Extend the P6 projection tuple.** Cheapest and cleanest at runtime: the
context already has the arrays, so the derived scalars cost almost nothing. But
it edits `btmm_poi_btrc_scanner_p6_dev.pine`, whose SHA the P6 closure evidence
records, so the closure capture would have to be re-run to re-establish
`P6_MTF_REAL_DATA_PARITY_ESTABLISHED` against the new source. The existing five
surfaces would be unchanged and should reproduce their current digests exactly,
which makes the re-capture a confirmation rather than a re-derivation.

**B. Add a separate P5 projection in P5 DEV.** Leaves P6 DEV byte-identical and
its closure untouched. Costs six additional `request.security` contexts (8 -> 14,
against Pine's limit of 40) and re-runs the whole P1/P2 pipeline a second time
per timeframe, roughly doubling the MTF work. It also creates a second context
maintaining the same window, which the host/request maintenance-equivalence
discipline would have to be extended to cover.

**C. Declare T1 out of scope for P5.** Not viable: T2 depends on T1, and T5
weights trend at 2 and regime at 1, so three of the thirteen weight units and the
whole trend-alignment path would be missing.

## Recommendation

**A**, on the grounds that it is a transport addition rather than a semantic
change: no existing transported value moves, so the re-capture should reproduce
the current per-surface digests exactly and would demonstrate that directly. B is
the fallback if the author prefers the P6 closure artifact to stay frozen at its
current SHA, and its cost is runtime, not correctness.

Either way this is the author's call, because it decides whether a closed
artifact is reopened.
