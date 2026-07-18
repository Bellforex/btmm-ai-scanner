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
- Ambiguity 6 (Pressure Wick wick:body proportion)
- Ambiguity 13 ("clear reversal" distance for Buy-to-Sell/Sell-to-Buy)
- Any other still-open item in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`

(Ambiguity 2, the "small candle" volatility baseline, is resolved — see "Small Candle and Recent Market Context Standard" below.)

Those remain pending separate author decisions.

---

## Small Candle and Recent Market Context Standard

**Status:** Approved — Small Candle Standard Version 1 (resolves Ambiguity 2 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Does not modify Candle Measurement Standard Version 1 above — it builds directly on the same `Candle Total Range = High − Low` primitive.

### 1. Total Range (unchanged)

```
Candle Total Range = High − Low
```

Continues to use the Candle Measurement Standard V1 definition exactly as-is.

### 2. Relative Smallness — the main POI validation requirement

A candle qualifies as **small relative to a key candle** when:

```
Small Candle Total Range ≤ 0.50 × Key Candle Total Range
```

Equivalently:

```
Key Candle Total Range ≥ 2 × Small Candle Total Range
```

### 3. Strong Volume-Switch Relationship

A **strong** volume-switch relationship exists when:

```
Small Candle Total Range ≤ 0.3333 × Key Candle Total Range
```

Equivalently:

```
Key Candle Total Range ≥ 3 × Small Candle Total Range
```

These two thresholds (0.50 and 0.3333) are the same 2×/3× relationship already used by Candle Measurement Standard V1's Size Ratio classification, expressed from the small candle's side of the comparison rather than the key candle's side.

### 4. Recent Market Context — a separate, secondary measurement

Recent market context is calculated independently of the relative-smallness rule:

```
Recent Median Range = median Total Range of the previous 20 confirmed candles,
                       excluding the current candidate candle
```

Context classifications:

| Candle Range vs. Recent Median Range | Classification |
|---|---|
| ≤ 0.75 × Recent Median Range | Contextually Small |
| > 0.75× and ≤ 1.25 × Recent Median Range | Contextually Normal |
| > 1.25 × Recent Median Range | Contextually Large |

### 5. Relative vs. Contextual — Two Separate Fields, Never Merged

- **Relative smallness** (SS2–SS3 above) is the **main POI validation requirement** — this is what determines whether a candle satisfies a POI's formation rule.
- **Contextual classification** (SS4 above) is a **secondary market-context and quality measurement only**. It must **never** automatically reject a pattern that already satisfies the book's relative-size rule. The two fields are tracked and reported separately; contextual classification is informational/quality-scoring, not a gating condition.

### 6. No Fixed Pip/Point Measurements

This standard uses only ratios (of Total Range to Total Range, and of Total Range to a rolling median Total Range) — never a fixed pip, point, or dollar floor. This is deliberate so the same rule applies unmodified across XAUUSD, EURUSD, GBPUSD, and every timeframe in scope (per `docs/PROJECT_SCOPE.md`), without needing a separate calibration per symbol.

### 7. POI-Specific Application

| POI | Key candle | Small/reference candle for comparison |
|---|---|---|
| Order Block | Displacement candle | The immediately preceding (smaller) candle |
| Bullish or Bearish Engulfing | Engulfing candle | The immediately preceding candle |
| Fair Value Gap | Displacement candle | The largest Total Range among the relevant preceding-candle group |
| Base Rally or Base Drop | Departure candle | The largest Total Range among all candles forming the base |
| Buy-to-Sell or Sell-to-Buy | Failed directional candle | The largest Total Range among the relevant preceding-candle group |

Pressure Wick / Liquidity Wick, Hammer, Shooting Star, Morning Star, and Evening Star are **not** included in this table — none of them appear in the approved POI-specific application list, so this standard is not referenced in those rule files. Their wick/body and doji-size questions remain separately unresolved (Ambiguity 6 and related open items).

### 8. Important Limitation — What This Decision Does *Not* Yet Define

This standard fixes the ratio/classification math only. It explicitly does **not** yet define:
- The number of preceding candles in a comparison group (relevant to Fair Value Gap and Buy-to-Sell/Sell-to-Buy).
- The number of candles forming a valid base (relevant to Base Rally/Base Drop).
- The minimum or maximum base duration (relevant to Base Rally/Base Drop).
- Reversal confirmation after a Buy-to-Sell or Sell-to-Buy candle (Ambiguity 13, unchanged).

These remain separate unresolved decisions and must not be inferred from this standard.

---

## Volume, Momentum, and Price-Activity Proxy Standard

**Status:** Approved — Volume and Momentum Proxy Standard Version 1 (resolves Ambiguity 3 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on, and does not modify, Candle Measurement Standard V1 and Small Candle Standard V1 above.

### 1. Primary Evidence — Price and Candle Behaviour

The primary interpretation of volume, momentum, buying pressure, selling pressure, and activity switch comes from price and candle behaviour, not from an external indicator. Five measurements are calculated and preserved as **separate fields** — they are not combined into a single score at this stage:

**A. Relative Size Ratio** (reuses Candle Measurement Standard V1 / Small Candle Standard V1 directly — no new formula):

```
Relative Size Ratio = Key Candle Total Range ÷ Reference Candle Total Range
```

**B. Range Context Ratio:**

```
Range Context Ratio = Key Candle Total Range ÷
                       Median Total Range of the previous 20 confirmed candles
```

The current candidate candle is excluded from the 20-candle baseline.

**C. Body Efficiency:**

```
Body Efficiency = |Close − Open| ÷ (High − Low)
```

**D. Bullish Close Position:**

```
Bullish Close Position = (Close − Low) ÷ (High − Low)
```

**E. Bearish Close Position:**

```
Bearish Close Position = (High − Close) ÷ (High − Low)
```

These five fields must remain separate. **They are not combined into a final weighted score during this decision.**

### 2. Secondary Evidence — Tick Volume (When Available)

Tick volume, where the data source provides it, is a **secondary, contextual** measurement only:

```
Relative Tick Volume = Current Candle Tick Volume ÷
                        Median Tick Volume of the previous 20 confirmed candles
```

The current candidate candle is excluded from the baseline.

Tick-volume status is reported as one of:

- **SUPPORTS**
- **NEUTRAL**
- **CONTRADICTS**
- **MISSING**

Rules governing tick volume:
- Tick volume must **not** initially be a mandatory POI-validity requirement.
- Missing tick volume must **not** automatically invalidate a POI.
- Tick-volume data must remain associated with its provider/source. Values from unrelated providers must never be silently compared or merged.

### 3. Excluded External Indicators

The core project must **not** use RSI, MACD, Stochastic, ADX, Rate of Change, or any other external momentum indicator as a mandatory POI rule. Such indicators may only be evaluated later as optional research features, and may be adopted only if they demonstrate measurable improvement on locked unseen data and receive author approval.

### 4. Field Separation — Price Activity vs. Tick Volume

Price-activity evidence and tick-volume evidence must remain separate fields, never merged. Future data fields are named here for forward reference only — none of them are computed, weighted, or thresholded by this decision:

- `relative_size_ratio`
- `range_context_ratio`
- `body_efficiency`
- `directional_close_position`
- `relative_tick_volume`
- `tick_volume_status`
- `price_activity_score`

The final `price_activity_score` formula and its feature weights remain unresolved and are **not** invented here.

### 5. What Remains Unresolved

This standard fixes *which measurements to calculate and how to calculate them*. It explicitly does **not** yet set:
- Minimum Body Efficiency
- Minimum Bullish or Bearish Close Position
- Minimum Relative Tick Volume
- Minimum displacement distance
- The final momentum-quality score (`price_activity_score`)
- Final feature weights
- Any hard pass/fail threshold

These remain subject to future author decisions, annotation evidence, and validation testing.

### 6. POI-Specific Application

Apply this standard's fields in: Buy Order Block, Sell Order Block, Buy Fair Value Gap, Sell Fair Value Gap, Base Rally, Base Drop, Buy-to-Sell Candle, Sell-to-Buy Candle, Bullish Engulfing, Bearish Engulfing.

**Do not apply this standard to Pressure Wick yet** — Pressure Wick proportions remain under Ambiguity 6, unresolved.

---

## Base Formation, Compactness, and Departure Standard

**Status:** Approved, **Provisional** — Base Formation Standard Version 1 — Provisional (resolves Ambiguity 4 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on Candle Measurement Standard V1, Small Candle Standard V1, and the Volume/Momentum/Price-Activity Proxy Standard above; does not modify any of them.

**Scope:** Applies only to Base Rally (Rally-Base-Rally) and Base Drop (Drop-Base-Drop). Not automatically extended to unrelated consolidation, accumulation, distribution, support, resistance, or any other POI.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, the H3/H4/D1/W1 timeframes, and different volatility regimes. The thresholds are not to be changed casually outside that calibration process.

### 1. Base Candle Count

- Minimum: 2 consecutive confirmed closed candles.
- Maximum: 6 consecutive confirmed closed candles.
- One candle alone is not a complete base.
- More than 6 candles is initially classified as **consolidation**, not a precise Base Rally/Drop POI.

### 2. Base-Candle Size

Uses Candle Total Range (`High − Low`) from Candle Measurement Standard V1 without modification. Every candle inside the base must satisfy:

```
Base Candle Total Range ≤ 0.50 × Departure Candle Total Range      (standard)
Base Candle Total Range ≤ 0.3333 × Departure Candle Total Range    (Strong Base)
```

The comparison uses the **largest** Total Range among all candles inside the base (not an average), consistent with Small Candle Standard V1.

### 3. Complete Base Height

```
Base Height = Highest High of all base candles − Lowest Low of all base candles
```

A valid base must satisfy **both**:

```
Base Height ≤ 0.75 × ATR(14)
Base Height ≤ 0.60 × Departure Candle Total Range
```

ATR(14) must be computed on the same symbol and timeframe as the candidate base.

### 4. Horizontal Compactness (Midpoint Drift)

For every base candle:

```
Candle Midpoint = (High + Low) ÷ 2
```

```
Base Midpoint Drift = |Last Base Candle Midpoint − First Base Candle Midpoint|
```

A valid base must satisfy:

```
Base Midpoint Drift ≤ 0.25 × Base Height
```

This is what prevents a small directional staircase from being misclassified as a horizontal base.

### 5. Base-Candle Overlap

For each pair of consecutive base candles:

```
Overlap High = MIN(candle A high, candle B high)
Overlap Low  = MAX(candle A low, candle B low)
Overlap Range = MAX(0, Overlap High − Overlap Low)
Previous Candle Range = Previous Candle High − Previous Candle Low
Overlap Ratio = Overlap Range ÷ Previous Candle Range
```

Each new base candle must satisfy:

```
Overlap Ratio ≥ 0.50
```

### 6. Departure Candle Requirements

The departure candle must:
- Be at least 2× the largest base candle's Total Range (≥ 3× for stronger classification).
- Close outside the complete base range.
- Move in the expected direction.
- Be evaluated using the approved Volume, Momentum, and Price-Activity Proxy Standard (SS above) — no separate momentum rule is invented here.

Direction-specific close condition:

```
Base Rally: Departure Close > Highest High of all base candles
Base Drop:  Departure Close < Lowest Low of all base candles
```

### 7. Classification

| Classification | Conditions |
|---|---|
| **COMPACT BASE** | Passes all standard base conditions (SS1–SS6 at the standard/non-strong thresholds). |
| **STRONG BASE** | Every base candle ≤ 0.3333× the departure candle's Total Range, **and** the departure candle is ≥ 3× the largest base candle, **and** all other compactness/height/overlap/close-outside conditions pass. |
| **INVALID BASE** | Any mandatory condition fails — including: fewer than 2 or more than 6 base candles; excessive Base Height; excessive midpoint drift; insufficient candle overlap; a base candle larger than permitted; departure candle below the required ratio; departure candle fails to close outside the complete base range; direction does not match Base Rally or Base Drop. |

### 8. What Remains Unresolved

This standard fixes base geometry, compactness, and departure-confirmation math only. It does **not** resolve:
- Freshness, partial mitigation, full mitigation, or expiration for Base Rally/Drop (still not defined in the book at all).
- The final `price_activity_score` formula/weights or any hard pass/fail threshold for the departure candle's momentum evidence (Volume/Momentum Proxy Standard SS5, unchanged).
- Any threshold for POIs outside Base Rally/Drop.

---

## Equal Highs and Equal Lows Tolerance and Drawing Standard

**Status:** Approved, **Provisional** — Equal Highs and Equal Lows Standard Version 1 — Provisional (resolves Ambiguity 5 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Does not modify any prior standard above.

**Scope:** Applies only to Equal Highs and Equal Lows. Not automatically extended to Support, Resistance, Trendlines, Swing Highs/Lows, Previous-period highs/lows, Order Blocks, Fair Value Gaps, or any other POI.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, relevant project timeframes, different volatility regimes, and different market sessions. The thresholds are not to be changed casually outside that calibration process.

### 1. Minimum Qualifying Points

A valid Equal Highs or Equal Lows pattern requires at least **2 confirmed swing points**:
- Equal Highs must use confirmed swing-high wick prices.
- Equal Lows must use confirmed swing-low wick prices.

The automatic swing-detection method remains **unresolved under Ambiguity 10**. Until Ambiguity 10 is resolved, this standard relies on expert-labelled swing points, manually confirmed swing points, or another explicitly approved confirmed-swing source. No swing-detection algorithm is invented by this standard.

### 2. Same-Timeframe Rule

All qualifying swing points in one Equal Highs or Equal Lows cluster must come from the **same timeframe**. Swing prices from different timeframes must never be combined into one equality cluster.

### 3. Reference ATR

For every qualifying swing-touch candle, ATR(14) is calculated on the same symbol and timeframe:

```
Reference ATR = Median ATR(14) value across all qualifying swing-touch candles
```

Only confirmed candles are used.

### 4. Equality Tolerance

```
Equality Tolerance = MAX(2 × minimum price ticks for the instrument, 0.10 × Reference ATR)
```

The minimum price tick is sourced from instrument metadata once the software layer is built. No fixed pip or point tolerance by symbol is used.

### 5. Equal Highs Validation

```
Equal Highs Cluster Spread = Highest qualifying swing-high wick price − Lowest qualifying swing-high wick price
```

Qualifies when:

```
Equal Highs Cluster Spread ≤ Equality Tolerance
```

### 6. Equal Lows Validation

```
Equal Lows Cluster Spread = Highest qualifying swing-low wick price − Lowest qualifying swing-low wick price
```

Qualifies when:

```
Equal Lows Cluster Spread ≤ Equality Tolerance
```

### 7. Strength Classification

| Classification | Condition |
|---|---|
| **STRONG** | Cluster Spread ≤ 0.05 × Reference ATR (minimum-tick floor from SS4 still applies to the overall equality tolerance) |
| **STANDARD** | Cluster Spread > 0.05 × Reference ATR **and** ≤ 0.10 × Reference ATR (minimum-tick floor still applies) |
| **NOT EQUAL** | Cluster Spread > Equality Tolerance |

No additional strength tiers are defined.

### 8. Drawing Boundaries

**Equal Highs:**
```
Zone Bottom = Lowest qualifying swing-high wick price
Zone Top = Highest qualifying swing-high wick price
Liquidity expectation: above Zone Top
Optional Reference Level = Median of all qualifying swing-high wick prices
```

**Equal Lows:**
```
Zone Bottom = Lowest qualifying swing-low wick price
Zone Top = Highest qualifying swing-low wick price
Liquidity expectation: below Zone Bottom
Optional Reference Level = Median of all qualifying swing-low wick prices
```

The Reference Level is optional and must not replace the zone boundaries (Zone Bottom/Zone Top).

### 9. Confirmation

A pattern becomes **CONFIRMED** only when:
- At least 2 qualifying swing points exist.
- All qualifying points are from the same timeframe.
- The latest swing point has itself been confirmed.
- The cluster spread remains within Equality Tolerance.

Before the latest swing is confirmed, the pattern may only be described as **FORMING**.

### 10. State Limitations

Four states are reserved for the future: FORMING, CONFIRMED, SWEPT, BROKEN. **Only FORMING and CONFIRMED are defined by this decision.** SWEPT, BROKEN, reclaim, invalidation, expiration, freshness, and mitigation remain unresolved and are not invented here.

### 11. What Remains Unresolved

This standard fixes equality-tolerance, drawing-boundary, strength-classification, and FORMING/CONFIRMED-state math only. It explicitly does **not** resolve:
- The automatic swing-detection algorithm (Ambiguity 10, unchanged).
- SWEPT and BROKEN state definitions.
- Reclaim, invalidation, expiration, freshness, or mitigation rules for Equal Highs/Lows.
- Any threshold for POIs outside Equal Highs/Equal Lows.

These remain separate, pending decisions.

These remain separate, pending decisions.

---

## Pressure Wick Measurement, Drawing, and Classification Standard

**Status:** Approved, **Provisional** — Pressure Wick Standard Version 1 — Provisional (resolves Ambiguity 6 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on Candle Measurement Standard V1 and the Volume/Momentum/Price-Activity Proxy Standard above; does not modify either.

**Scope:** Applies only to Bullish Pressure Wick and Bearish Pressure Wick. Not automatically extended to Hammer, Shooting Star, pin bars generally, Order Blocks, Fair Value Gaps, Engulfing candles, Base Rally, Base Drop, or other POIs.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, relevant project timeframes, different sessions, and different volatility regimes. The thresholds are not to be changed casually outside that calibration process.

### 1. Candle Measurements

Uses only confirmed closed candles for final validation.

```
Total Range = High − Low
Body = |Close − Open|
Upper Wick = High − MAX(Open, Close)
Lower Wick = MIN(Open, Close) − Low
```

A candle with Total Range ≤ 0 is invalid and must not be classified as a Pressure Wick.

```
Body Efficiency = Body ÷ Total Range
Upper Wick Share = Upper Wick ÷ Total Range
Lower Wick Share = Lower Wick ÷ Total Range
```

### 2. Bullish Pressure Wick (Lower-Price Rejection)

A confirmed candidate must satisfy **all** of:

- Lower Wick Share ≥ 0.40
- Body Efficiency ≥ 0.25
- Lower Wick ≥ 2 × Upper Wick
- Bullish Close Position ≥ 0.60, where `Bullish Close Position = (Close − Low) ÷ Total Range`

The candle may close bullish or bearish — candle colour alone must not determine Pressure Wick direction.

### 3. Bearish Pressure Wick (Higher-Price Rejection)

A confirmed candidate must satisfy **all** of:

- Upper Wick Share ≥ 0.40
- Body Efficiency ≥ 0.25
- Upper Wick ≥ 2 × Lower Wick
- Bearish Close Position ≥ 0.60, where `Bearish Close Position = (High − Close) ÷ Total Range`

The candle may close bullish or bearish — candle colour alone must not determine Pressure Wick direction.

### 4. Strong and Standard Classification

**STRONG** requires **all** of:

- Rejection Wick Share ≥ 0.50
- Body Efficiency ≥ 0.30
- Rejection Wick ≥ 3 × Opposite Wick
- Directional Close Position ≥ 0.70
- Range Context Ratio ≥ 1.25, where `Range Context Ratio = Candidate Total Range ÷ Median Total Range of the previous 20 confirmed candles` (current candidate excluded from the baseline)

Direction mapping:

| Direction | Rejection Wick | Opposite Wick | Directional Close Position |
|---|---|---|---|
| Bullish Pressure Wick | Lower Wick | Upper Wick | Bullish Close Position |
| Bearish Pressure Wick | Upper Wick | Lower Wick | Bearish Close Position |

A candidate that passes the standard conditions (SS2 or SS3) but not every STRONG condition is classified **STANDARD**. No additional strength tiers are defined.

### 5. Numerical Protection (Zero-Range / Zero-Wick Safety)

```
Wick Dominance Ratio = Rejection Wick ÷ MAX(Opposite Wick, Minimum Price Tick)
```

This prevents division by zero when the opposite wick is exactly zero. The Minimum Price Tick must eventually come from instrument metadata once the software layer is built — no fixed pip or point value is invented by this documentation task.

### 6. Drawing Boundaries

**Bullish Pressure Wick:**
```
Zone Bottom = Candle Low
Zone Top = MIN(Open, Close)
```
This zone contains only the lower rejection wick.

**Bearish Pressure Wick:**
```
Zone Bottom = MAX(Open, Close)
Zone Top = Candle High
```
This zone contains only the upper rejection wick.

The candle body must never be automatically included in the Pressure Wick POI zone.

### 7. Candidate and Confirmed States

- **CANDIDATE** — before the candidate candle closes.
- **CONFIRMED** — after the candle closes and all mandatory conditions (SS2 or SS3) pass.

RETESTED, MITIGATED, SWEPT, BROKEN, and EXPIRED are **not** defined by this decision — they depend on later freshness, mitigation, liquidity, sweep, invalidation, and expiration standards.

### 8. Volume and Momentum Treatment

Pressure Wicks reference the approved Volume, Momentum, and Price-Activity Proxy Standard (above):
- Price and candle behaviour are the primary evidence.
- Tick volume is secondary, contextual evidence only.
- Missing tick volume must **not** automatically invalidate a Pressure Wick.
- RSI, MACD, Stochastic, ADX, Rate of Change, or other external indicators must **not** be mandatory.

No final `price_activity_score` formula or new indicator threshold is invented by this standard.

### 9. Timeframe Treatment

H3, H4, D1, and W1 receive higher-timeframe **contextual priority only** — not a numerical score. A candle that fails the mandatory Pressure Wick measurements (SS2/SS3) remains invalid regardless of timeframe.

### 10. Relationship with Hammer and Shooting Star

Pressure Wicks remain Volume-Based POIs; Hammer and Shooting Star remain Price-Action POIs. One candle may independently qualify for both a Pressure Wick label and a Hammer/Shooting Star label — the system must preserve these labels separately and must never silently merge them into one POI type. The Hammer and Shooting Star rule files are **not** modified by this standard.

### 11. What Remains Unresolved

This standard fixes wick/body proportions, drawing boundaries, strength classification, and CANDIDATE/CONFIRMED-state math only. It explicitly does **not** resolve:
- Proof of liquidity collection.
- Required preceding market approach speed.
- Required nearby support, resistance, trendline, or structural zone.
- Retest confirmation.
- Freshness, partial mitigation, full mitigation.
- Sweep rules.
- General invalidation.
- Expiration.
- Trade-entry confirmation.

These remain separate, pending decisions.
