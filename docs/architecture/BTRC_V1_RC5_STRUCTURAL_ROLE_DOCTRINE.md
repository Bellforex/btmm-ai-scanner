# BTRC-V1 RC5 — STRUCTURAL ROLE DOCTRINE (FROZEN)

Frozen 2026-09-21, after all three author controls passed. `IMPULSE_ORIGIN`
was **not** added: formation adjacency alone rescued the M45 fixture, and the
author's rule is that no new role ships without evidence that one is needed.

## The doctrine

A reversal-family candidate is a POI only where the market made a structural
decision. It must touch — **on the side it claims to defend** — a swing that
the frozen structure walk actually *uses*:

| role | meaning | available from |
|---|---|---|
| `LEG_ORIGIN` | a break named it as the origin of the leg it confirmed | that break's availability |
| `SWING_HIGH_ORIGIN` / `SWING_LOW_ORIGIN` | a break **took** it — it held real liquidity | that break's availability |
| `PULLBACK_HIGH` / `PULLBACK_LOW` | a level the walk **has defended** — protected or weak, now or at any earlier transition | when it first became defended |

Anything else is `MID_LEG` and stays a raw pattern. **"Confirmed swing" is not
a role** — in a trending leg almost every swing is an unbroken, unused pivot.
On M15, 99 of 432 swings hold a role (23%).

Precedence when a formation touches several used swings: LEG_ORIGIN (0) >
SWING_*_ORIGIN (1) > PULLBACK_* (2).

## Roles must be monotone

`PULLBACK_*` is deliberately "**has** defended", not "**currently** defends".

The first draft used the walk's live protected/weak levels, which lapse when
structure moves on. That makes the role non-monotone, and the rest of the
engine depends on the opposite: `immutable_structure_gate` skips replaying the
walk on most bars precisely because the final gate output is a superset of
every prefix's. A lapsing role breaks that invariant silently — it does not
raise, it just locks the POI at whatever later prefix happened to recompute.

It was caught on the author's own fixture. The gate returned availability
`2026-09-04 13:00` at every prefix, yet the full batch pipeline published the
M45 B2S at `2026-09-07 05:30` — an arbitrary **86-bar** delay with no semantic
meaning. (An earlier report of this campaign stated the fixture had "no delay";
that was measured against the RC4 record rather than the RC5 one and was
wrong. The delay was real until this fix, and is now genuinely zero.)

Each transition records the level it protected and the weak level it armed, so
the whole defended history is available from the final walk and accumulates
monotonically. `since` remains the moment the fact became true, so availability
stays causal. A swing the walk ever defended was meaningful when it defended
it, and this engine never retracts what was once true.

## Formation adjacency

A candidate is matched across its **formation span** — for B2S/S2B the source
candle through the candle that confirmed the reversal, which is the detector's
own confirmation window. Every other family records no span and is matched by
its source candles exactly as before.

This is not a neighbourhood search. A BUY-TO-SELL candle *is* the last
up-candle before the turn, so the swing high that completes the reversal forms
on a **later bar of the formation** — source-candle matching can never qualify
the family. In the author's M45 fixture the completing swing (4490.85) sits
above the formation's own zone top (4486.42), so no containment or tolerance
rule could have matched it either.

The fix is surgical: across 6,829 bars on five hosts it changed exactly **one**
POI — the fixture itself.

## Causality

Detected at source time, qualified when the evidence exists. Only
`availability_time_utc` (and the `confirmation_time_utc` that shadows it) may
move, and only later. `candidate_event_time_utc`, the source candles, the zone
and the formation identity are never rewritten. The gate runs inside the
prefix/frontier replay, so a role is only ever read from the prefix that
established it.

## The three controls, all green

**M45 B2S — PASS.** Source `2026-09-04 07:00`, zone `4461.42–4486.42`, both
unchanged. Matched the swing high `4490.85` on bar 201 via the formation span,
role `PULLBACK_HIGH`; POI availability `2026-09-04 13:00`, **identical to RC4** —
zero delay, verified against the RC5 record itself.

**H3 staircase — PASS.** All six descending BEARISH PRESSURE WICKs still
refused (4× `NOT_A_PIVOT_ON_ITS_OWN_SIDE`, 2× `SWING_NEVER_USED_BY_THE_WALK`).
Pressure wicks are single-candle formations with no confirmation window, so
they record no span and adjacency cannot reach past them — the staircase is
out of scope by construction, not by tuning.

**H4 Evening Star — PASS.** 29 → 6 survive (Morning Star 24 → 2).

## Five-host impact, frozen role set

| host | bars | POI | reversal | refused | delayed | med/max delay |
|---|---|---|---|---|---|---|
| M5 | 2000 | 498 → 186 | 349 → 37 | 312 | 17 | 9 / 24 |
| M15 | 2000 | 455 → 178 | 319 → 42 | 277 | 27 | 13 / 201 |
| M45 | 529 | 100 → 47 | 63 → 10 | 53 | 5 | 16 / 76 |
| H3 | 300 | 82 → 42 | 43 → 3 | 40 | 2 | 14.5 / 20 |
| H4 | 2000 | 483 → 199 | 317 → 33 | 284 | 17 | 10 / 87 |

Zero POIs invented and zero non-reversal families removed on all five.
ORDER BLOCKS unchanged wherever any exist (M5 4→4, M15 4→4, H4 3→3) — the
positive control that the gate reads the same structure the frozen leg-origin
rule reads.

M45 and H3 are plan-capped windows (529 / 300 bars) and are fixture evidence,
not comparable rates.

## Why `IMPULSE_ORIGIN` is not in the doctrine

Measured before proposing it: **84 of 85** M15 mid-leg rejects already had a
FAST/VERY_FAST displacement in their own direction within 40 bars (H4 79/81,
M5 80/82). On gold that predicate is true almost everywhere, so a role built on
"confirmed swing + subsequent impulse" would re-admit the entire rejected
population including the staircase. Adjacency made the question moot.

If a future positive fixture needs it, the only acceptable form is the one the
author specified: a swing from which the existing walk's **next confirmed break
in that direction** originates, available when that break confirms — and it
must be re-run against the staircase before it ships.
