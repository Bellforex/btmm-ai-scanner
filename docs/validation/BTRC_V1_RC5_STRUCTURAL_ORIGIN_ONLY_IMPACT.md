# BTRC-V1 RC5 — STRUCTURAL-ORIGIN-ONLY IMPACT (INTERIM)

**This is NOT final RC5 impact.** Only the structural-origin gate is on. No
same-origin authority arbitration, no DOJI, no qualified sweeps, no display
eligibility. Each of those changes the numbers again.

Both profiles run the same frozen bars through the same engine; only
`rc5_structural_origin` differs, so every number below is a difference between
two runs of identical code on identical data.

Tool: `tests/parity_support/rc5_structural_origin_impact.py`.
Data: `artifacts/rc4_aligned_v2/_normalized/*.csv` (the frozen aligned FXCM
capture). Reports: `artifacts/rc5_structural_impact/*.json`.

## Headline

| TF | bars | window | POI total | reversal POIs | refused (mid-leg) | delayed |
|---|---|---|---|---|---|---|
| M5 | 2000 | 2026-09-09 → 09-18 | 498 → **183** | 349 → **34** | 315 | 19 |
| M15 | 2000 | 2026-08-20 → 09-18 | 455 → **173** | 319 → **37** | 282 | 24 |
| H4 | 2000 | 2025-06-05 → 2026-09-18 | 483 → **193** | 317 → **27** | 290 | 17 |

Invariants, asserted by the tool on every run and **PASS** on all three:

* `families_invented` = [] — the gate never creates a POI.
* `non_reversal_families_removed` = [] — FVG, bases and S/R zones untouched.

## Availability delay (source → availability)

The gate delays rather than refuses whenever a true origin is confirmed late.

| TF | delayed | median bars | max bars | median hours | max hours |
|---|---|---|---|---|---|
| M5 | 19 | 11 | 179 | 0.92 | 15.9 |
| M15 | 24 | 18 | 201 | 4.5 | 100.5 |
| H4 | 17 | 9 | 87 | 40.0 | 491.0 |

Not optimised — measured only, as instructed. The max values are real: a leg
origin is named by the break that confirms the leg, and some legs take a long
time to confirm.

## By family

M15 (RC4 → RC5, refused, delayed, median/max delay bars):

| family | RC4 | RC5 | refused | delayed | med | max |
|---|---|---|---|---|---|---|
| B2S/S2B | 6 | 1 | 5 | 0 | – | – |
| ORDER BLOCK | 4 | 4 | **0** | 0 | – | – |
| STARS | 47 | 8 | 39 | 7 | 17 | 47 |
| ENGULFING | 53 | 7 | 46 | 5 | 13 | 49 |
| HAMMER/SHOOTING | 72 | 10 | 62 | 7 | 15 | 126 |
| PRESSURE WICK | 137 | 7 | 130 | 5 | 27 | 201 |

M5: B2S 2→1, OB 4→4, STARS 48→3, ENGULFING 60→7, HAMMER/SHOOTING 66→7,
PRESSURE WICK 169→12.
H4: B2S 5→1, OB 3→3, STARS 53→8, ENGULFING 87→3, HAMMER/SHOOTING 66→8,
PRESSURE WICK 103→4.

**ORDER BLOCKS are untouched on all three timeframes**, which is the expected
self-check: an ORDER BLOCK is placed at a leg origin by construction, so the
structural-origin gate can have nothing to say about it. That the number is 0
and not "almost 0" is evidence the gate is reading the same structure the
frozen leg-origin rule reads.

## How aggressive is this, structurally

M15: 2000 bars → 432 confirmed swings → 58 structure breaks → **99 swings hold
a role** (23%): 51 LEG_ORIGIN, 26 SWING_LOW_ORIGIN, 21 SWING_HIGH_ORIGIN,
1 PULLBACK_HIGH.
H4: 417 swings → 64 breaks → 110 roles: 58 LEG_ORIGIN, 34 SWING_HIGH_ORIGIN,
16 SWING_LOW_ORIGIN, 2 PULLBACK.

So the engine finds ~1 structural decision point per 20 bars, and after the
side and pivot-candle match, ~1 qualified reversal POI per 54 M15 bars —
against roughly 1 per 6 under RC4. That is the direction the chart complaint
asked for, but it is a large reduction and it is the author's call whether it
is the right magnitude.

`PULLBACK_*` is now almost empty by design (only the walk's live protected /
weak levels qualify). The earlier draft — "any unbroken confirmed swing" —
would have granted it to ~330 of 432 M15 swings and refused essentially
nothing.

## Known scope limits of this stage

* **RANGE_HIGH / RANGE_LOW, LIQUIDITY_EXTREME and TRENDLINE_EXTREME are not
  yet supplied.** Those references live in the RC4 framework layer, which the
  POI promotion point does not see. A reversal pattern that sits at a range
  boundary or a liquidity pool but not on a walk-used swing is currently
  refused. Wiring them belongs with the qualified-sweep work, which owns those
  references — and it will move these numbers **up**.
* **M45 and H3 are not measured.** There is no raw OHLC capture for either in
  the repo (`artifacts/rc5_m45_forensic/` and `artifacts/rc5_h3h4_forensic/`
  hold decoded Pine P5C logs, not bars). Resampling M5 would not reproduce
  TradingView's session-aware M45/H3 bars, so no number is offered rather than
  a misleading one. Both need a fresh aligned OHLC capture.
* Consequently the **H3 six-wick staircase** and the **M45 B2S** author
  fixtures are not yet replayed under the causal gate. The M15/H4 pressure-wick
  reductions (137→7 and 103→4) are consistent with the staircase being refused,
  but that is inference, not the fixture.

## Why B2S drops 6 → 1 on M15 (the number most worth auditing)

B2S/S2B is the top of the authority ladder, so a large reduction there needs a
reason per case rather than a rate. Per-candidate trace of all six:

| bar | direction | outcome | why |
|---|---|---|---|
| 173 | BULLISH | **KEPT** | LEG_ORIGIN |
| 745 | BEARISH | refused | its candle is not a swing-high pivot at all |
| 991 | BEARISH | refused | its candle is not a swing-high pivot at all |
| 1174 | BEARISH | refused | real SWING_HIGH, but the walk never used it |
| 1180 | BEARISH | refused | its candle is not a swing-high pivot at all |
| 1819 | BEARISH | refused | real SWING_HIGH, but the walk never used it |

Three of the five refusals are B2S patterns that are **not local tops at all** —
a bearish reversal candle sitting mid-move. Those are refusals nobody would
dispute, and they are the class of clutter the chart complaint was about.

The other two are genuine swing highs that no break ever took, that no leg
departed from, and that the walk is not currently protecting. Under the
accepted rule they are texture. **This is the judgement call worth reviewing**:
if the author considers an untaken, unprotected swing high a valid reversal
origin, the role set needs a fourth member and the numbers rise accordingly.
