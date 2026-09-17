# BTRC V1 — RC3 non-FVG same-origin arbitration matrix

Author decision B (2026-09-17): HAMMER overrides a same-candle BULLISH PRESSURE
WICK, SHOOTING STAR overrides a same-candle BEARISH PRESSURE WICK. The pressure
wick stays raw (`SAME_ORIGIN_SUPPRESSED`, `primary_type` = the named formation).
No other non-FVG pair is ordered unless it is a strict specialization.

"Same origin" = same final source candle and same direction (`origin_key`).
FVG arbitration (leg-origin OB > engulfing > FVG, and every candle pattern ending
on the departure candle > FVG) is unchanged — see
`BTRC_V1_RC3_SAME_ORIGIN_ARBITRATION.md`.

## Specialization test

A pair (A, B) is a strict specialization only when, on the same candle and
direction, A is B with an additional named-shape constraint AND describes the
same price zone, so mapping both draws one reaction zone twice. Measured on raw
detector outputs, unsealed FXCM (`tests/parity_support/rc3_non_fvg_pair_audit.py`,
data `artifacts/rc3_qual_aligned_v12`, output `artifacts/rc3_non_fvg_pairs`).

Columns: co-occurrences / identical zone / A ⊆ B / B ⊆ A.

| Pair (same candle, same direction) | D1 | H4 | H1 | M15 | M5 | Decision |
|---|---|---|---|---|---|---|
| HAMMER + BULLISH PRESSURE WICK | 9/9/9/9 | 11/11/11/11 | 6/6/6/6 | 13/13/13/13 | 19/19/19/19 | **HAMMER primary** (author) |
| SHOOTING STAR + BEARISH PRESSURE WICK | 13/13/13/13 | 7/7/7/7 | 14/14/14/14 | 16/16/16/16 | 21/21/21/21 | **SHOOTING STAR primary** (author) |
| BASE + ENGULFING | 3/0/0/3 | 16/4/4/16 | 13/5/5/13 | 10/2/2/10 | 7/1/1/7 | keep both |
| BASE + STAR | 1/0/0/1 | 3/0/0/3 | 0 | 3/0/0/3 | 0 | keep both |
| BASE + PRESSURE WICK | 0 | 1/0/0/0 | 1/0/0/0 | 1/0/0/0 | 1/0/0/0 | keep both |
| ENGULFING + PRESSURE WICK | 6/0/0/0 | 5/0/0/0 | 5/0/0/0 | 4/0/0/0 | 5/0/0/0 | keep both |
| ENGULFING + HAMMER / SHOOTING STAR | 2/0/0/0 | 0 | 1/0/0/0 | 0 | 0 | keep both |
| PRESSURE WICK + MORNING / EVENING STAR | 7/0/2/0 | 6/0/1/0 | 7/0/2/0 | 9/0/3/0 | 9/0/2/0 | keep both |
| HAMMER / SHOOTING STAR + STAR | 0 | 1/0/0/0 | 1/0/0/0 | 2/0/0/0 | 2/0/0/0 | keep both |
| B2S / S2B + any | 0 | 0 | 0 | 0 | 0 | keep both |

Raw totals for scale (M15): HAMMER 57, SHOOTING STAR 62, BULL PW 121, BEAR PW
116, MORNING 35, EVENING 28, BULL ENG 34, BEAR ENG 38, BASE RALLY 16, BASE DROP 9,
B2S 6, S2B 2.

## Why only the author pair

* HAMMER / SHOOTING STAR vs pressure wick: identical zone in 100 % of
  co-occurrences on every timeframe (both are the candle's rejection wick
  range). One reaction zone, two labels → the named formation is primary.
* Every other pair describes different price zones (0 identical zones except
  BASE + ENGULFING, where the zone is identical in a minority of cases and the
  base is a multi-candle consolidation whose zone always contains the
  engulfing). They are different formations (1 vs 2 vs 3 vs N candles) with
  different reaction levels, and REG §35L / KB say "preserved separately", so no
  ordering is introduced without an author decision.
* Not every HAMMER is a pressure wick (M15: 13 of 57), so the rule is a
  same-candle override, not a detector merge; independent pressure wicks on other
  candles stay mapped (test `test_pressure_wick_on_another_candle_stays_mapped`).

## Pipeline position

RAW → TYPE QUALITY → SAME-ORIGIN ARBITRATION (FVG rules + decision B) →
STRUCTURAL CONTEXT GATE → MAPPED. The suppressed pressure wick never reaches the
context gate; the named formation is gated like any other pattern. The pressure
wick's origin key still counts for FVG arbitration (the named formation carries
the same key, so the outcome is identical).

## Implementation

* Python: `poi/qualification.py` (`_PRESSURE_WICKS`, `_WICK_SPECIALIZATIONS`).
* Pine USER / PARITY: `f_poiEmit` records `poiNamedKey` (= `srcLastT × direction`)
  for HAMMER / SHOOTING STAR; single-candle reversals are detected before pressure
  wicks on each bar, so a same-candle pressure wick finds the key and is not
  mapped.
* Tests: `tests/unit/test_rc3_poi_context_gate.py`.
