# Measurement Standards

This file holds implementation-ready measurement definitions once an ambiguity in [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md) has been resolved by the author. Each section here is an approved standard, not a candidate option — it supersedes the corresponding "possible measurements" list in the ambiguity register once recorded.

---

## Candle Size, Body, Wick, and Range Measurements

**Status:** Approved — Candle Measurement Standard Version 1 (resolves Ambiguity 1 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`).

### 1. Primary Size Measurement — Total Range

The primary measurement of candle size is the complete high-to-low range:

```
Candle Total Range = High − Low
```

This applies everywhere the book asks for a candle-size comparison (Order Blocks, Fair Value Gaps, Base Rally/Drop, Buy-to-Sell/Sell-to-Buy candles, Engulfing patterns), unless a POI-specific exception is noted below.

### 2. Size Ratio

Candle size comparisons must use the ratio of total ranges:

```
Size Ratio = Key Candle Total Range ÷ Reference Candle Total Range
```

"Key candle" and "reference candle" are defined per POI type (see POI-Specific Application below).

### 3. Classification

| Size Ratio | Classification |
|---|---|
| < 2.0 | Does not satisfy the main size requirement |
| 2.0 to < 3.0 | Valid / standard pattern |
| ≥ 3.0 | Strong pattern |

This directly implements the book's recurring "at least two times, ideally three times" language with a single, consistent numeric rule across all POI types.

### 4. Candle Body — Measured Separately

The candle body is measured independently of total range:

```
Candle Body = |Close − Open|
Body Efficiency = Candle Body ÷ Candle Total Range
```

Body Efficiency is a **separate quality measurement**. It must **not** replace or substitute for the book's two-times/three-times total-range rule above — a candle can pass the Size Ratio test and still be scored separately on Body Efficiency where a POI's rules care about body strength (e.g., engulfment).

### 5. Wicks

Wicks are never excluded from the Total Range measurement — Total Range is always full high-to-low, wicks included. Wick *quality* (e.g., rejection-wick proportion for a Pressure Wick) is evaluated as its own, separate measurement per POI type, not folded into the general Size Ratio rule.

### 6. Role of ATR

ATR (Average True Range) does **not** replace or adjust the 2.0/3.0 Size Ratio thresholds. ATR is reserved for later use only as a secondary normalization and market-context measurement — e.g., comparing typical candle sizes across different symbols (XAUUSD vs. EURUSD vs. GBPUSD), timeframes, or volatility regimes. It is explicitly out of scope for the core size-ratio rule itself.

### 7. POI-Specific Application

| POI | Key candle | Reference candle | Notes |
|---|---|---|---|
| Order Block | Displacement candle | Smaller first candle | Size Ratio computed on Total Range of each; classification table applies directly. |
| Fair Value Gap | Displacement (middle) candle | Relevant preceding candle(s) | Total-range ratio computed as above; Body Efficiency of the displacement candle recorded separately as an additional quality signal, not a replacement condition. |
| Base Rally / Base Drop | Departure candle | Largest Total Range among all base candles (not just one base candle) | Size Ratio must be computed against the base's *largest* candle, per the book's explicit rule. |
| Buy-to-Sell / Sell-to-Buy | Failed directional candle | (average size of preceding candles, per existing POI catalog rule) | Total Range used for the Size Ratio; reversal confirmation afterward is evaluated as its own separate condition (see Ambiguity 13 — still unresolved), not merged into the size measurement. |
| Engulfing Pattern | Engulfing candle | Previous (engulfed) candle | Two separate conditions required: (1) body engulfment — the engulfing candle's body must cover the previous candle's body; (2) Total Range Size Ratio per the classification table. Both must hold; neither substitutes for the other. |
| Pressure Wick / Liquidity Wick | — | — | This standard's ordinary displacement/body rule does **not** apply. Pressure Wick proportions (wick-to-body ratio) are handled separately under Ambiguity 6 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`, which remains unresolved. |

### 8. What Remains Unresolved

This standard fixes *how to measure and classify candle size and body*. It does **not** resolve:
- Ambiguity 2 ("small candle" volatility baseline)
- Ambiguity 6 (Pressure Wick wick:body proportion)
- Ambiguity 13 ("clear reversal" distance for Buy-to-Sell/Sell-to-Buy)
- Any other still-open item in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`

Those remain pending separate author decisions.
