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
