# BTRC V1 — RC3 same-origin arbitration

Author decision (2026-09-17): one originating formation maps one primary POI.

## Rule (`poi/qualification.py`)

* `origin_key(pattern)` = (final source candle, direction).
* An FVG's origin is its **departure (middle) candle** in its direction.
* If a same-direction candle pattern of ENGULFING, PRESSURE WICK, HAMMER,
  SHOOTING STAR, MORNING / EVENING STAR or BASE RALLY / DROP ends on that candle,
  the pattern is primary and the FVG is `SAME_ORIGIN_SUPPRESSED` (raw, audit
  only). ORDER BLOCK formations are always engulfings too, so a leg-origin OB and
  its engulfing both outrank the FVG.
* Not same origin (both kept): an FVG whose departure is the pattern's first or
  third candle, an opposite-direction pattern, any later independent FVG.
* Geometry overlap alone is never used.
* Causal: every arbiter completes at the departure close, before the FVG
  (third close). Incremental replay needs only the previous step's arbiters.

Pine: `f_poiEmit` records `srcLastT × direction` for pattern types 7–16
(`poiOriginKey`); `f_poiDetectFvg` skips an FVG whose departure key is present.

## Evidence (unsealed FXCM, raw detector outputs)

| TF | FVGs suppressed | by ENGULFING | by PRESSURE WICK | by STAR | by BASE | by HAMMER / SHOOTING STAR | suppressed that would pass gap quality |
|---|---|---|---|---|---|---|---|
| M5 | 95 | 45 | 25 | 19 | 5 | 1 | 34 |
| M15 | 74 | 30 | 22 | 15 | 5 | 2 | 35 |
| H1 | 76 | 37 | 15 | 19 | 5 | 0 | 38 |
| H4 | 97 | 61 | 11 | 19 | 5 | 1 | 42 |

## Author case (H1, 2026-09-17)

BUY FVG sourced 04:00 (4298.89–4304.27) departs from the 05:00 candle, a BULLISH
PRESSURE WICK (4285.37–4297.35). Python: wick mapped, FVG
`SAME_ORIGIN_SUPPRESSED` (primary = BULLISH_PRESSURE_WICK). Live FX:XAUUSD H1
(USER DEV v29): only the pressure-wick box is drawn.

## Non-FVG pairs (author decision B, 2026-09-17)

HAMMER is primary over a same-candle BULLISH PRESSURE WICK and SHOOTING STAR over
a same-candle BEARISH PRESSURE WICK (identical zone in every measured
co-occurrence); the wick stays raw as `SAME_ORIGIN_SUPPRESSED`. All other
non-FVG pairs stay separate mapped POIs. Evidence and per-pair decisions:
`BTRC_V1_RC3_NON_FVG_ARBITRATION_MATRIX.md`.
