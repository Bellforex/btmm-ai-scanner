# BTRC-V1 RC5 — QUALIFIED SWEEP AUDIT

Part B of the addendum says to inspect the existing liquidity engine before
inventing any importance threshold. This is that inspection, measured on the
frozen aligned FXCM capture. **Nothing is implemented yet.**

## The complaint, quantified

| host | bars | sweep events | rate |
|---|---|---|---|
| M15 | 2000 | **580** | 1 per 3.4 bars |
| H4 | 2000 | **558** | 1 per 3.6 bars |

A sweep annotation every three or four candles is the chart the author is
looking at.

## Where they come from

`framework/engine.py::_levels()` turns **every** confirmed swing, **every**
equal-level cluster and **every** trendline into a sweepable liquidity level.
Range boundaries are registered separately and do produce RANGE_HIGH /
RANGE_LOW sweeps.

M15 inputs: 432 swings, 437 trendlines, 18 clusters, 58 transitions, 11 ranges.

| kind | M15 | H4 |
|---|---|---|
| TRENDLINE | 272 (47%) | 297 (53%) |
| SWING_HIGH + SWING_LOW | 284 (49%) | 248 (44%) |
| EQUAL_HIGHS + EQUAL_LOWS | 11 | 10 |
| RANGE_HIGH + RANGE_LOW | 13 | 3 |

Two observations. **Trendlines are the single largest source** — there are 437
of them over 2000 bars, more trendlines than meaningful structures. And the
genuinely pool-like liquidity (equal highs/lows) is only ~11 events per 2000
bars, so it cannot carry the annotation set on its own.

## What the engine already records — Part Q is nearly satisfied

`SweepEvent` already carries `side` (BUY_SIDE/SELL_SIDE → BSL/SSL), `kind`
(reference kind), `level_id` (reference identity), `level_price`, `sweep_type`,
`scope`, `bar_index`, `event_time_utc` and `availability_time_utc` — compact
enums and ids, no verbose strings. Missing only: an **active-POI** reference
kind (`LiquidityKind` has no POI member, so "ACTIVE MAJOR POI boundary" does
not exist as a sweepable level today) and an explicit **event timeframe** on the
record (today it is implicit in the per-timeframe `FrameworkTracker`).

## `scope` alone is not the qualifier

`LiquidityScope` already separates EXTERNAL (at/beyond an active range boundary)
from INTERNAL, which looks like the ready-made importance signal. It is not,
because a confirmed range is only active part of the time:

| host | UNSCOPED | INTERNAL | EXTERNAL | EXTERNAL-only rate |
|---|---|---|---|---|
| M15 | 462 (80%) | 62 | 56 | 1 per 36 bars |
| H4 | 524 (94%) | 25 | 9 | **1 per 222 bars** |

M15 keeps 9% and H4 keeps 1%. That is both too aggressive and wildly unstable
between hosts — H4 would show almost no sweeps at all. `scope` is a useful
*contributor*, not the rule.

## What does work: the RC5 structural role map

The structural-origin gate already computes which swings the frozen walk
actually **uses** — named as a leg origin, taken by a break, or currently
protected/weak (99 of 432 on M15). The same doctrine applies to liquidity: a
swing no break ever took and the walk is not defending is not meaningful
liquidity either. It reuses machinery that already exists, adds no threshold,
and is the rule the author has already accepted for POIs.

Measured, qualifying a sweep when its level is a walk-used swing, OR equal-level
/ range liquidity, OR sits at a range boundary (EXTERNAL):

| host | today | qualified | rate | swing sweeps kept |
|---|---|---|---|---|
| M15 | 580 | **125** | 1 per 16 bars | 68 / 284 (23%) |
| H4 | 558 | **79** | 1 per 25 bars | 60 / 248 (24%) |

The swing retention is **23% and 24%** — nearly identical across two very
different hosts, where the EXTERNAL-only rule gave 9% and 1%. Trendline sweeps
are not abolished, only required to occur at a range boundary: 18 survive on
M15, 5 on H4.

Every surviving event can name what was swept, which is the Part G test.

## Open dependency — this is coupled to the unresolved role-set decision

The proposed qualifier consumes the same role map that **failed its forensic
gate** on the author's M45 B2S fixture (`BTRC_V1_RC5_STRUCTURAL_ROLE_FORENSIC.md`).
Fixing the adjacency defect, and any `IMPULSE_ORIGIN` role added on top, will
change which swings hold a role — and therefore change which liquidity
qualifies and which sweeps are annotated. The numbers above will move.

Closing the role set is therefore a prerequisite for freezing sweep
qualification, not merely adjacent to it.

## Not yet inspected

* **Active-POI boundaries as liquidity.** Requires a new `LiquidityKind` and a
  feed from the P3 lifecycle into the framework engine. Not present today.
* **Trendline quality.** 437 trendlines over 2000 bars is the largest single
  noise source; whether `Trendline` already carries a usable quality measure
  (touch count, span, age) has not been examined.
* **BTMM DISTRACTION coupling.** `framework/engine.py:560` credits DISTRACTION
  from `first.sweep_type` / `first.kind` of the sweep list, so restricting
  qualification automatically restricts DISTRACTION — which is Part R's
  requirement, but the behaviour change must be measured before it is accepted.
* **Host-timeframe locality (Part D/F)** is a Pine object-lifecycle question and
  has not been audited yet.

---

# UPDATE 2026-09-21 — trendline audit, and the qualifier re-measured on the frozen role set

The structural role set is now frozen
(`docs/architecture/BTRC_V1_RC5_STRUCTURAL_ROLE_DOCTRINE.md`). Formation
adjacency changed the *matching* of candidates to swings, not `role_by_swing`
itself, so the swing-liquidity qualifier is unaffected by that change.

## Trendline quality — what the model already carries

`domain/trendlines.py::Trendline` already records `anchor_1_swing_record_id`,
`anchor_2_swing_record_id`, `qualifying_touch_swing_record_ids`, both anchor bar
indices, `raw_slope` / `normalized_slope` / `anchor_reference_atr`, and
`confirmation_candle_id` + `confirmation_time_utc`.

**`qualifying_touch_swing_record_ids` has length exactly 1 for all 437
trendlines on both M15 and H4.** As produced today the touch count carries no
discriminating information at all, so it cannot be the quality signal and no
touch-count threshold should be invented on top of it.

The anchors can. A trendline is drawn *between two swings*, so the frozen role
doctrine applies to it unchanged: a line between two swings the walk actually
uses is meaningful liquidity; a line between two texture pivots is not. No new
threshold, no count tuning.

| host | trendlines | both anchors walk-used | trendline sweeps | qualified |
|---|---|---|---|---|
| M15 | 437 | 40 | 272 | 24 |
| H4 | 437 | 27 | 297 | 21 |

Importantly this does **not** require a range boundary — the provisional audit's
`EXTERNAL` clause was diagnostic only and is now dropped, as the author asked.
A confirmed trendline between two structurally used swings holds liquidity
wherever it sits.

## The qualifier, from existing semantics only

* swing liquidity — the swing holds a role under the frozen doctrine
* equal highs / equal lows — always qualify (genuine pools, they do not have to
  masquerade as structural-origin swings)
* range high / low — always qualify, on the range's existing confirmation
* trendline — both anchor swings hold a role
* active POI boundary — **not yet implemented** (Phase 7; no POI `LiquidityKind`
  exists today)

| host | raw sweeps | rate | qualified | rate | kept | BSL | SSL |
|---|---|---|---|---|---|---|---|
| M5 | 585 | 1 per 3.4 bars | **123** | 1 per 16 bars | 21% | 59 | 64 |
| M15 | 580 | 1 per 3.4 bars | **116** | 1 per 17 bars | 20% | 53 | 63 |
| H4 | 558 | 1 per 3.6 bars | **94** | 1 per 21 bars | 16% | 39 | 55 |

Stable across three very different hosts (21% / 20% / 16%), where the rejected
`EXTERNAL`-only rule gave 9% / 1%. Every surviving event names its reference
kind and `level_id`, so the Part G question — *what was swept?* — is answerable
for all of them.

Internal liquidity is untouched: minor swings remain in the engine for
structure, diagnostics and framework calculations. Only the **user-facing**
sweep set is qualified.

## All five hosts

| host | bars | raw sweeps | rate | qualified | rate | kept | BSL | SSL |
|---|---|---|---|---|---|---|---|---|
| M5 | 2000 | 585 | 1 per 3.4 | **123** | 1 per 16 | 21% | 59 | 64 |
| M15 | 2000 | 580 | 1 per 3.4 | **116** | 1 per 17 | 20% | 53 | 63 |
| M45 | 529 | 102 | 1 per 5.2 | **27** | 1 per 20 | 26% | 12 | 15 |
| H3 | 300 | 51 | 1 per 5.9 | **11** | 1 per 27 | 21% | 2 | 9 |
| H4 | 2000 | 558 | 1 per 3.6 | **94** | 1 per 21 | 16% | 39 | 55 |

Retention 16–26% on five hosts spanning 5 minutes to 4 hours, from a rule with
no tuned constant in it. The chart goes from a sweep label every 3–6 candles to
one every 16–27.

## Still to do

* **Active POI boundaries (Phase 7)** — needs a new `LiquidityKind` member and a
  feed from the P3 lifecycle into the framework engine. Only FRESH/active
  authoritative POIs may contribute, so it also depends on authority wiring.
* **Host timeframe on `SweepEvent` (Phase 11)** — a contract change; today the
  host is implicit in the per-timeframe `FrameworkTracker`.
* **BTMM DISTRACTION delta (Phase 12)** — the coupling is confirmed at
  `framework/engine.py:540-560`: DISTRACTION is credited from `context.events`
  filtered by approach side and price. Adding a qualification flag to
  `SweepEvent` and requiring it there is the minimal change that satisfies Part
  R while leaving DELAY / WIPEOUT / MULTIPLE untouched and keeping internal
  liquidity available. The before/after counts have not been measured yet.

---

# SUPERSEDED, 2026-09-22

Everything above is a PROVISIONAL AUDIT measured through the final-state
framework route. That route was later proven causally lossy and is no longer
RC5 sweep authority.

The retention figures in this document (M5 585→123, M15 580→116, M45 102→27,
H3 51→11, H4 558→94) were measured from FINAL structural context. They
undercount because roles lapse in final state, and they miss transient levels
entirely.

Current authority is `replay_rc5_qualified_sweeps` — per-bar causal history.
See `BTRC_V1_RC5_CAUSAL_LIQUIDITY.md` for the evidence and the closure matrix.

Keep this document for its INPUT analysis, which stands: the trendline
touch-count finding (`qualifying_touch_swing_record_ids` is length 1 for all
437 trendlines on M15 and H4, so touch count carries no information) is what
established that anchors, not counts, decide trendline qualification.
