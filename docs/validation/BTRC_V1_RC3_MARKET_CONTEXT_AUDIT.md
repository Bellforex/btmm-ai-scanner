# BTRC V1 — RC3 market-context audit of mapped POIs

Tool: `tests/parity_support/rc3_poi_context_audit.py`. Real FXCM XAUUSD, all
unsealed segments, mapped core POIs of the qualified engine. Every value is known
at the POI's availability. **Diagnostic only — no context gate is implemented**:
project authority states no automated structural / trend / location gate for
these POI types (REG §35S; KB context statements are qualitative).

## Model

* **Leg** = latest frozen P2 break (BOS / CHOCH) available at the POI's
  availability; `leg_id` = its break time; leg direction = direction after.
* **Role**: TREND_ALIGNED (POI direction = leg direction), COUNTER_TREND
  (opposite), STRUCTURAL_NEUTRAL (no break yet). Counter-trend POIs are kept and
  labelled, never deleted.
* **Retracement**: zone midpoint depth inside the latest confirmed swing range
  (bullish measured down from the swing high).
* **Confluence**: overlap with an available S/R zone or equal-level cluster; an
  available trendline projecting into the zone ± 0.10 × anchor ATR at the POI's
  source bar.

## Results

| TF | mapped | TREND_ALIGNED | COUNTER_TREND | NEUTRAL | <50 % | 50–61.8 % | 61.8–79 % | 79–100 % | outside range | S/R | equal level | trendline |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M15 | 656 | 321 | 331 | 4 | 179 | 66 | 94 | 73 | 241 | 71 | 128 | 437 |
| H1 | 529 | 285 | 229 | 15 | 140 | 38 | 62 | 61 | 218 | 32 | 23 | 235 |
| H4 | 637 | 318 | 301 | 18 | 145 | 61 | 81 | 80 | 257 | 46 | 77 | 319 |

Observations:

* About half of mapped POIs are counter to the current leg.
* 34–41 % sit outside the latest swing range (formed while price extends
  beyond it, i.e. inside a running impulse).
* The trendline flag is broad (45–67 %): many trendlines and a ±0.10 ATR band;
  it needs a tighter author-defined proximity before it can carry meaning.
* Only 5–11 % overlap an S/R zone.

## Decisions required before any gate

1. Should COUNTER_TREND POIs be mapped, labelled, or suppressed (and on which
   timeframe's structure)?
2. A retracement band (e.g. 50–79 %) as a gate, and relative to which swing
   range (current leg vs previous impulse)?
3. Required confluence (S/R, liquidity, trendline) per type, with a trendline
   proximity definition.

Caveat: swings / breaks come from the batch engine filtered by availability;
a structure record superseded later could colour a label (the mapped POIs
themselves are immutable).

## Decision A applied (2026-09-17): structural context gate

The questions above were answered by the author: counter-trend candle patterns
stay raw unless existing structure confirms a reversal; neutral patterns stay
raw; retracement and confluence stay metadata. Implementation and rules:
`docs/architecture/BTRC_V1_RC3_CONTEXT_AWARE_POI_ENGINE.md`. The gate's direction
includes the P2 bootstrap (first HH+HL / LH+LL), so its NEUTRAL share is smaller
than the "no break yet" column above.

Tool: `tests/parity_support/rc3_context_gate_audit.py` (unsealed FXCM,
`artifacts/rc3_qual_aligned_v12`; output `artifacts/rc3_context_gate/`). Counts
are qualified + arbitrated candle patterns (the 14 gated types); "before" = the
same pipeline without the context gate (`be9bae1` semantics plus decision B).

| TF | aligned | reversal | counter-trend reject | neutral reject | gated before → after | P2 segments (BOS / CHOCH / bootstrap) |
|---|---|---|---|---|---|---|
| W1 | 346 | 93 | 172 | 25 | 636 → 439 (-31 %) | 50 / 13 / 1 |
| D1 | 312 | 116 | 141 | 10 | 579 → 428 (-26 %) | 47 / 27 / 1 |
| H4 | 300 | 113 | 169 | 17 | 599 → 413 (-31 %) | 42 / 20 / 2 |
| H1 | 268 | 88 | 124 | 19 | 499 → 356 (-29 %) | 51 / 28 / 2 |
| M15 | 307 | 127 | 191 | 5 | 630 → 434 (-31 %) | 37 / 24 / 1 |
| M5 | 329 | 177 | 137 | 15 | 658 → 506 (-23 %) | 34 / 24 / 1 |

Per type (before → after):

| type | H4 | H1 | M15 | M5 |
|---|---|---|---|---|
| BUY_FAIR_VALUE_GAP | 86 → 68 | 51 → 41 | 75 → 53 | 68 → 62 |
| SELL_FAIR_VALUE_GAP | 59 → 46 | 42 → 40 | 60 → 51 | 71 → 62 |
| BUY_TO_SELL_CANDLE | 4 → 3 | 4 → 3 | 6 → 6 | 4 → 3 |
| SELL_TO_BUY_CANDLE | 7 → 1 | 6 → 1 | 2 → 2 | 8 → 2 |
| BASE_RALLY | 19 → 15 | 12 → 7 | 16 → 6 | 5 → 3 |
| BASE_DROP | 8 → 6 | 12 → 10 | 9 → 8 | 10 → 10 |
| BULLISH_PRESSURE_WICK | 75 → 45 | 92 → 57 | 108 → 63 | 112 → 86 |
| BEARISH_PRESSURE_WICK | 77 → 47 | 85 → 65 | 100 → 74 | 111 → 81 |
| BULLISH_ENGULFING | 56 → 43 | 29 → 15 | 34 → 21 | 32 → 25 |
| BEARISH_ENGULFING | 50 → 35 | 35 → 28 | 38 → 32 | 41 → 32 |
| HAMMER | 54 → 35 | 32 → 18 | 57 → 33 | 63 → 46 |
| SHOOTING_STAR | 39 → 24 | 40 → 32 | 62 → 41 | 63 → 44 |
| MORNING_STAR | 30 → 21 | 35 → 17 | 35 → 23 | 41 → 28 |
| EVENING_STAR | 35 → 24 | 24 → 22 | 28 → 21 | 29 → 22 |

No gated type is eliminated on any timeframe. ORDER BLOCK and S/R ZONE counts
are unchanged by the gate (structural by contract; M15 segment: 66 raw OB
formations → 4 leg-origin ORDER BLOCKs both at `be9bae1` and now).

### Trend story (M15, first segments of the unsealed export)

| from (UTC) | to | direction | opened by | aligned | reversal | counter reject | neutral reject |
|---|---|---|---|---|---|---|---|
| 2026-08-18 17:45 | 2026-08-19 00:30 | UNDETERMINED | START | 0 | 0 | 0 | 5 |
| 2026-08-19 00:30 | 2026-08-19 00:45 | BEARISH | BOOTSTRAP | 0 | 1 | 0 | 0 |
| 2026-08-19 00:45 | 2026-08-19 08:45 | BULLISH | BULLISH_CHOCH | 8 | 0 | 4 | 0 |
| 2026-08-19 08:45 | 2026-08-19 12:45 | BULLISH | BULLISH_BOS | 3 | 0 | 1 | 0 |
| 2026-08-19 12:45 | 2026-08-19 19:15 | BULLISH | BULLISH_BOS | 6 | 0 | 1 | 0 |
| 2026-08-19 19:15 | 2026-08-20 05:30 | BULLISH | BULLISH_BOS | 4 | 6 | 1 | 0 |
| 2026-08-20 05:30 | 2026-08-20 11:45 | BEARISH | BEARISH_CHOCH | 1 | 0 | 3 | 0 |
| 2026-08-20 11:45 | 2026-08-20 14:45 | BEARISH | BEARISH_BOS | 4 | 4 | 0 | 0 |
| 2026-08-20 14:45 | 2026-08-21 04:30 | BULLISH | BULLISH_CHOCH | 7 | 0 | 5 | 0 |
| 2026-08-21 04:30 | 2026-08-21 06:00 | BULLISH | BULLISH_BOS | 0 | 0 | 0 | 0 |
| 2026-08-21 06:00 | 2026-08-21 08:30 | BULLISH | BULLISH_BOS | 0 | 0 | 1 | 0 |
| 2026-08-21 08:30 | 2026-08-21 14:30 | BULLISH | BULLISH_BOS | 3 | 0 | 3 | 0 |
| 2026-08-21 14:30 | 2026-08-21 15:45 | BULLISH | BULLISH_BOS | 0 | 0 | 0 | 0 |
| 2026-08-21 15:45 | 2026-08-24 00:15 | BULLISH | BULLISH_BOS | 2 | 0 | 4 | 0 |

Reading (rows count patterns by the segment in which they became available):
before the bootstrap every pattern is NEUTRAL (5 rejected). Inside a bullish
leg, bullish patterns map as aligned and bearish patterns are counter-trend.
The 6 REVERSAL rows of the 2026-08-19 19:15 → 2026-08-20 05:30 bullish segment
are bearish patterns that formed inside the leg the 05:30 BEARISH CHOCH confirms
(from its origin swing high): they map at the CHOCH, not before. Counter-trend
patterns in corrections that never break structure stay raw.
