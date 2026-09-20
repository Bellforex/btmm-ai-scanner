# BTRC-V1 RC5 — POI AUTHORITY: FORENSIC BASIS

Author campaign, 2026-09-20. Branch `rc5-poi-authority` from RC4 `2f1d2b9`
(frozen). Governing principle: **one structural decision origin → one
authoritative reversal POI.**

Everything below was measured on live FX:XAUUSD registries captured with the
RC4 PARITY build; no case was inferred from a screenshot.

| capture | host | registry | fresh | RUNMETA host checksum |
|---|---|---|---|---|
| `artifacts/rc5_m45_forensic/pine_m45_run1.csv` | M45 | 348 | 23 | `30699360.54000006` |
| `artifacts/rc5_h3h4_forensic/pine_h3_run1.csv` | H3 | 369 | 23 | `32370647.020…` |
| `artifacts/rc5_h3h4_forensic/pine_h4_run1.csv` | H4 | 362 | 39 | `30890790.200…` |

## 1. Why the cluster key is NOT shared availability

The structural-context gate releases a candidate at the bar whose P2 break
makes it available, so candidates released by one late break share a timestamp
even when they are unrelated. Measured:

* **H3, availability 2026-08-31 04:00** — nine bearish candidates. Sources span
  2026-08-25 19:00 → 08-28 19:00; zones span 4433 → 4673 (**240 points**). Six
  are a descending staircase of BEARISH PRESSURE WICKs. Nothing is contained in
  the nominal winner.
* **H4, availability 2026-08-05 18:00** — fifteen bullish candidates, all fresh.
  Sources span **five weeks**; zones span 3959 → 4179 (**220 points**).

Clustering on availability would have destroyed 8 and 14 valid POIs
respectively. Geometry alone fails symmetrically: unrelated POIs months apart
overlap the same price band (M45 idx 224 from 08-19 overlaps the 09-04 B2S by
11.82 points).

**Adopted key:** `direction + confirming transition + broken swing + origin
swing`, then a **formation relationship** (containment). Shared availability is
corroborating evidence only. A shared formation candle is the weak fallback and
may never subordinate a different semantic family.

## 2. Two filters, not one

| question | mechanism |
|---|---|
| Is this pattern a meaningful POI at all? | **structural-origin gate** (`poi/structural_role.py`) |
| Which of several meaningful patterns owns this decision event? | **authority ladder** (`poi/authority.py`) |

The H3 staircase proves they are not interchangeable: those six wicks share no
zone, so no ladder can remove them — only the role gate can. The M45 cluster
proves the converse: all three members sit at a genuine origin, so the gate
passes them and the ladder decides.

## 3. The frozen cases

### M45 — author-confirmed fixture
Primary **B2S** source 2026-09-04 07:00, zone 4461.42–4486.42.
Suppressed: SHOOTING_STAR 09-03 22:00 (4473.92–4478.83, contained),
SHOOTING_STAR 09-04 11:30 (4465.60–4470.54, contained),
BEAR_PRESSURE_WICK 09-04 07:45 (4485.61–4490.85).
Independent: **SELL_FVG** 09-04 11:30, availability 13:45, zone
4424.02–4464.46 — extends 37 points below the B2S zone.

### H3
* **Same-origin collapse:** BEARISH_ENGULFING and SHOOTING_STAR both source
  2026-08-25 19:00; the star (4657.56–4668.96) is contained in the engulfing
  (4653.31–4668.96) → **ENGULFING wins**.
* **Mid-leg staircase:** six BEARISH PRESSURE WICKs, 4673.71 → 4588.67, over
  three days → **all refused by the structural-origin gate**, not the ladder.
* **Independent imbalance:** SHOOTING_STAR (4465.53–4490.85) and SELL_FVG
  (4448.92–4461.42) share source bar 09-04 07:00 and availability 09-14 13:00,
  but the FVG lies entirely below with 4.11 points of clear air → **KEEP both**.

### H4
* **Evening Star owns a contained wick:** availability 09-14 14:00,
  EVENING_STAR 4374.99–4432.08 contains BEAR_PRESSURE_WICK 4398.77–4412.75 and
  SHOOTING_STAR 4406.95–4419.56 → **EVENING STAR wins, both suppressed**.
* **Evening Star does NOT own a separated wick:** availability 09-02 02:00,
  EVENING_STAR 4629.23–4673.71 vs BEAR_PRESSURE_WICK 4606.44–4618.07 — 11
  points of clear air → **not same origin**; that wick is the role gate's job.
* **Two shooting stars, one reversal:** 09-14 cluster, SS 4416.51–4448.92
  extends above the Evening Star (**survives**) while SS 4406.95–4419.56 is
  contained (**suppressed**).
* **Independent SELL_FVGs:** 4387.14–4423.40 (avail 09-02 02:00) and
  4297.64–4321.98 (avail 09-14 14:00) — both share their cluster's availability
  and both sit wholly outside the winner → **KEEP**.

## 4. Doji contract (verified in repo, unchanged)

`poi/configuration.py`: `doji_body_efficiency_standard = 0.10`,
`doji_body_efficiency_strong = 0.05`. Used today only as a suppressor
(`engulfing.py`, `order_blocks.py`) and as the middle-candle rule for
MORNING / EVENING STAR. RC5 reuses both numbers for `PoiType.DOJI`; direction
comes from the structural role, not candle colour.

## 5. Host-timeframe note

M45, H3 and M1 all run as hosts but sit outside the BTRC authority set
`(W1, D1, H4, H1, M15, M5)`, so their P5 momentum = 50, breakout = 40 and
pullback = N/A. This is a documented limitation, not an RC5 regression.
