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
