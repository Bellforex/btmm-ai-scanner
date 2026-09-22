# BTRC-V1 RC5 — Pine capacity measurement

**Capacity measurement only.** Nothing here was implemented into the production
`[RC5 USER]` script, which stays at v11.0 = Stage C. Nothing was published, no
library was modified, `bellforex` was not touched, nothing was merged, no
Python RC5 code was changed.

Every number below comes from the real TradingView compiler through the
validated CE10117 oracle. No estimate is presented as a measurement.

## Method, and one correction to it

The oracle appends N pad blocks of exactly 97 tokens and reads `outputILLength`
out of the compile error's `ctx`. A build that ALREADY exceeds the limit reports
its count directly at pad 0, needing no padding and no arithmetic.

Having both readings on one build exposed a constant the earlier stage log did
not account for:

| Stage C + G | tokens |
| --- | --- |
| derived from pads (N = 20 / 40 / 60, all exact) | 100,552 |
| read directly at pad 0 | 100,511 |
| **difference** | **41** |

41 tokens is the ONE-OFF cost of introducing the first `if barstate.islast` pad
block. It is constant, so every derived figure carries it. The two methods agree
exactly once it is removed, which cross-validates both.

**True counts are therefore `derived - 41`.** Stage deltas are unaffected,
because every stage was measured the same way. Corrected absolutes:

| stage | derived | **true** | headroom |
| --- | --- | --- | --- |
| A — DOJI | 96,007 | 95,966 | 4,290 |
| B — validity / display | 96,043 | 96,002 | 4,254 |
| C — provenance | 96,523 | **96,482** | **3,774** |

## 1-5. The Stage-G answer

Stage G was ported onto the measured Stage-C base with no simplification: level
identity threaded onto framework levels and sweep events; POI far edges
registered and withdrawn from the CURRENT prefix; per-family qualification
(structural swings must be swings the walk used, trendlines need BOTH anchors
meaningful, equal-level pools and confirmed range boundaries always qualify);
semantic deduplication by shared level source AND exactly equal price, with no
tolerance; owner priority and corroboration; DISTRACTION reading qualified
sweeps only. DELAY and WIPEOUT untouched.

| | tokens |
| --- | --- |
| **1. Stage C exact** | **96,482** |
| **2. Stage C headroom** | **3,774** |
| 3a. G1 — meaningful swings (shared with Stage D) | **+357** |
| 3b. G2 — qualified liquidity, dedup, events, DISTRACTION | **+3,672** |
| **3. Stage G total delta** | **+4,029** |
| **4. Stage C + G total** | **100,511** |
| limit | 100,256 |
| **5. OVER BY** | **255** |

Stage G alone exhausts the budget, with Stages D, E, F and H not yet written
and `f_rc5Authoritative` still a stub returning true.

Three-point validation on Stage C + G: N = 20 / 40 / 60 gave 102,492 / 104,432 /
106,372. Both intervals exactly `97 x 20 = 1,940`; all three bases identical at
100,552.

## 6. What D, E, F and H still cost

**Stage D was MEASURED, not estimated**, because it is the fork that prompted
this exercise. A faithful block-at-emission prototype was built on Stage C + G1
— pivot-candle-to-swing maps per side, the meaningful-swing test, and the
range / liquidity / trendline reach test — wired as a conjunct in `f_poiEmit`'s
existing admission test, exactly where Python's `lock_candidate` refuses. A
refused reversal candidate never enters the registry, as in Python.

| | tokens |
| --- | --- |
| Stage C + G1 | 96,839 |
| **Stage C + G1 + D (faithful, blocking)** | **98,907** |
| **Stage D marginal cost** | **+2,068** |

+2,068 for one boolean gate is the inline tax again: `f_poiEmit` has nine call
sites, so the whole predicate body is emitted nine times.

E, F and H are ESTIMATES, flagged as such:

| stage | estimate | basis |
| --- | --- | --- |
| E — authority (cluster + ladder) | 600–1,000 | runs as one per-bar pass over the registry, so it is NOT inline-multiplied; comparable in shape to the Stage-B display pass plus a ladder |
| F — P5/P8 terminal alignment | 50–150 | changes one predicate; comparable to Stage B's measured +36 |
| H — HH/HL/LH/LL + readability | 400–800 | labels plus a read of the existing structural walk; adds no detector |
| **total** | **1,050–1,950** | |

**Projection, all faithful:**

| | tokens |
| --- | --- |
| Stage C + G (measured) | 100,511 |
| + D (measured) | 102,579 |
| + E, F, H (estimated) | **103,629 – 104,529** |
| limit | 100,256 |
| **shortfall to recover** | **3,373 – 4,273**, before any safety margin |

## 7. Extraction candidates, measured

Each candidate was deleted from the over-limit Stage-C+G build and recompiled,
so each recovery is a real compiler reading, not a line count. **Deletion
measures the block's full weight, which is the UPPER BOUND on what moving it to
the BAH library recovers** — a library call still costs its arguments at the
call site. The previously measured BAH extraction recovered 3,614 tokens, so
roughly 70–80% of a deletion figure is the realistic yield.

| candidate | lines | **recovered** | public-safe? |
| --- | --- | --- | --- |
| **e1** RC4 framework display layer — range lines, level lines, BSL/SSL and SWEEP labels | 26 | **1,340** | **Yes.** Pure drawing from already-computed values; the file's own comment states nothing above reads it. |
| **e2** P7 summary + POI tables — cell rendering and row formatting | 76 | **2,684** | **Yes.** Takes finished strings and colours; no rule, threshold or decision crosses the boundary. |
| **e3** P7-Z zone boxes, labels and the visual group projection | 416 | **4,542** | **Mostly.** Box and label construction, the interval-merge grouping and the nearest-first selection are all generic. The POI semantics deciding WHICH zones are eligible stay in the script and must not move. |
| sum of individual recoveries | | 8,566 | |

Deliberately not separated: the P5 row string, `f.txt` and the P8 alert message
construction are already thin `bahui.*` calls, so their remaining weight is
argument marshalling that extraction cannot remove.

e2's first cut left a dangling `if` and failed with CE10144; the boundary was
corrected and re-measured, and the figure above is from the corrected variant.

## 8. Is faithful single-script RC5 feasible?

**Not as the code stands, and not by compaction.** But it is not ruled out.

Needed: 3,373–4,273 tokens plus margin. Available by extraction: 8,566 measured
as deletion, realistically 6,000–6,800 in the library at 70–80% yield.

The arithmetic closes, but only just. e1 + e2 alone measure 4,024 by deletion
(~2,800–3,200 realistic), which does not clear the shortfall on its own, so e3
is required as well and the remaining margin is on the order of 2,000 tokens.

**Faithful single-script RC5 is feasible ONLY if the whole presentation layer
moves into the BAH library, and the result will be tight.**

## 9. Why the two-script partition does NOT work

Worth stating plainly, because it is the obvious fallback and it fails for a
structural reason rather than a budgetary one.

**Pine scripts cannot share state.** No channel exists by which a companion
study receives another study's computed values, so every script must recompute
everything it draws or decides.

Partitioning A–F into one script and G–H into another therefore does not split
the cost. Stage G's liquidity families include ACTIVE POI FAR EDGES, whose
activity is `rc5_validity` plus authority standing — so the companion would need
the POI detector, the full lifecycle, validity, provenance and authority. That
is substantially all of script one, plus G. The companion ends up larger than
the script it was meant to relieve.

Dropping POI far edges from the companion would make it fit, and is exactly the
semantic weakening that is not on the table.

Two further constraints make the split worse in practice: the Basic plan caps
two indicators per chart, so two RC5 scripts leave no slot for
`[RC4 MARKET FRAMEWORK]` alongside, and the same plan caps two live connections.

## Recommendation

1. **Extract, measuring after each step**, in ascending risk: e1 (1,340), then
   e2 (2,684), then e3 (4,542). Each is display-only and public-safe, and none
   changes a scanner rule. Re-measure after each so the yield is known rather
   than assumed.
2. **Then implement D–H faithfully**, in the author's order, with the same
   per-stage three-point measurement.
3. **Keep the single script.** The two-script partition does not reduce total
   compiled tokens, for the reason in section 9, and costs a chart slot.
4. If extraction falls short of the measured requirement, the decision returns
   to the author with real numbers rather than a guess. The honest options at
   that point are reducing the DRAWN surface — not the computed semantics — or
   accepting a Pine layer that renders a subset of RC5 while Python remains the
   authority.

## Artifacts

Measurement builds are disposable and live in the session scratchpad, not in the
repository. The production `[RC5 USER]` script is unchanged at v11.0 (Stage C,
LF SHA `7c0e5045974977a41e57837f8108a9e3706bea08cd0a2a339627d6d1709564d1`).
