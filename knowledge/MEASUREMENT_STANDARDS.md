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
| Buy-to-Sell / Sell-to-Buy | Failed directional candle | (average size of preceding candles, per existing POI catalog rule) | Total Range used for the Size Ratio; reversal confirmation afterward is evaluated as its own separate condition (resolved separately under Ambiguity 13 — see "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard" below), not merged into the size measurement. |
| Engulfing Pattern | Engulfing candle | Previous (engulfed) candle | Two separate conditions required: (1) body engulfment — the engulfing candle's body must cover the previous candle's body; (2) Total Range Size Ratio per the classification table. Both must hold; neither substitutes for the other. |
| Pressure Wick / Liquidity Wick | — | — | This standard's ordinary displacement/body rule does **not** apply. Pressure Wick proportions (wick-to-body ratio) are handled separately under Ambiguity 6 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`, which remains unresolved. |

### 8. What Remains Unresolved

This standard fixes *how to measure and classify candle size and body*. It does **not** resolve:
- Ambiguity 6 (Pressure Wick wick:body proportion)
- Any other still-open item in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`

(Ambiguity 13, the "clear reversal" distance for Buy-to-Sell/Sell-to-Buy, is now resolved separately — see "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard" below; this did not change any Candle Measurement Standard formula.)

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
- The number of preceding candles in a comparison group (relevant to Fair Value Gap; for Buy-to-Sell/Sell-to-Buy this is now resolved separately as exactly 3 candles — see "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard" below).
- The number of candles forming a valid base (relevant to Base Rally/Base Drop).
- The minimum or maximum base duration (relevant to Base Rally/Base Drop).

These remain separate unresolved decisions and must not be inferred from this standard. (Reversal confirmation after a Buy-to-Sell or Sell-to-Buy candle, Ambiguity 13, is now resolved separately — see "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard" below; this did not change any formula in this standard.)

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

---

## Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard

**Status:** Approved, **Provisional** — Market Speed and Displacement Standard Version 1 — Provisional (resolves Ambiguity 7 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on Candle Measurement Standard V1, Small Candle Standard V1, and the Volume/Momentum/Price-Activity Proxy Standard above; does not modify any of them.

**Scope:** FVG displacement thresholds apply only to Buy Fair Value Gap and Sell Fair Value Gap. BTMM movement-leg formulas apply only to explicitly labelled BTMM Approach Legs and BTMM Reaction Legs. Not automatically extended to Order Blocks, Base Rally, Base Drop, Engulfing candles, Pressure Wicks, Trendlines, Support/Resistance, or other POIs.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, M1/M5/M15 BTMM formations, H1/M15 market structure, H3/H4/D1/W1 POIs, different sessions, and different volatility regimes. The thresholds are not to be changed casually outside that calibration process.

### 1. Required Concept Separation

Four concepts must be preserved separately and never combined into one unexplained score:

- **FVG Displacement Speed** — how fast the displacement candle expanded relative to recent candles.
- **BTMM Approach Speed** — how fast price moved toward a POI during an approach leg.
- **BTMM Reaction Speed** — how fast price moved away from a POI during a reaction leg.
- **POI Dwell Time** — how long price remained inside a POI zone.

### 2. Single-Candle Speed Measurement

For a confirmed candidate candle:

```
Range Speed Ratio = Candidate Total Range ÷ Median Total Range of the previous 20 confirmed candles
```

The current candidate candle is excluded from the 20-candle baseline.

| Classification | Condition |
|---|---|
| **NORMAL** | Range Speed Ratio < 1.50 |
| **FAST** | Range Speed Ratio ≥ 1.50 and < 2.00 |
| **VERY FAST** | Range Speed Ratio ≥ 2.00 |

### 3. FVG Comparison Window

For Buy and Sell Fair Value Gaps, use the three confirmed candles immediately before the displacement candle:

```
Pre-Displacement Maximum Range = Largest Total Range among the previous 3 confirmed candles
Displacement Expansion Ratio = Displacement Candle Total Range ÷ Pre-Displacement Maximum Range
```

This speed rule does **not** replace the strict three-candle FVG gap geometry (Buy: 3rd-candle-low > 1st-candle-high; Sell: 3rd-candle-high < 1st-candle-low), which remains an independent mandatory requirement.

### 4. Standard Fast FVG

A displacement candle qualifies as **STANDARD FAST** only when **all** pass:

- Range Speed Ratio ≥ 1.50
- Displacement Expansion Ratio ≥ 2.00
- Body Efficiency ≥ 0.60
- Directional Close Position ≥ 0.70
- A valid strict three-candle FVG gap independently exists

```
Buy FVG:  Directional Close Position = (Close − Low) ÷ Total Range
Sell FVG: Directional Close Position = (High − Close) ÷ Total Range
```

### 5. Strong Fast FVG

A displacement candle qualifies as **STRONG FAST** only when **all** pass:

- Range Speed Ratio ≥ 2.00
- Displacement Expansion Ratio ≥ 3.00
- Body Efficiency ≥ 0.70
- Directional Close Position ≥ 0.80
- A valid strict three-candle FVG gap independently exists

A fast candle without valid FVG geometry is **not** an FVG. A valid geometric FVG that fails the speed thresholds may remain a weaker FVG candidate — it must **not** be silently deleted solely for failing speed classification. No additional speed tiers are defined.

### 6. BTMM Movement-Leg Measurements

Until automatic anchors are approved (dependent on Ambiguity 14), use **expert-labelled movement-leg anchors only**. For each labelled BTMM approach or reaction leg:

```
Leg Bar Count = Number of confirmed candles in the movement leg
Net Directional Distance = |End Price − Start Price|
Reference ATR = Median ATR(14) across the confirmed candles in the leg
Normalized Speed Per Bar = Net Directional Distance ÷ (Leg Bar Count × Reference ATR)
Leg Path Distance = Sum of Total Ranges of every candle in the leg
Directional Efficiency = Net Directional Distance ÷ Leg Path Distance
Directional Candle Share = Number of candles closing in the movement direction ÷ Total candles in the leg
```

**Zero-denominator protection:** a movement leg with zero candles, zero Reference ATR, or zero Leg Path Distance cannot receive a valid speed classification.

### 7. BTMM Speed Classification

| Classification | Conditions (all required) |
|---|---|
| **FAST** | Normalized Speed Per Bar ≥ 0.50, Directional Efficiency ≥ 0.60, Directional Candle Share ≥ 0.67 |
| **STRONG FAST** | Normalized Speed Per Bar ≥ 0.75, Directional Efficiency ≥ 0.75, Directional Candle Share ≥ 0.80 |
| **SLOW_OR_UNCLEAR** | Otherwise |

Speed classification alone must **never** approve or reject a POI, a BTMM formation, an entry, or a trade.

### 8. POI Dwell Measurement

```
POI Dwell Bars = Number of consecutive confirmed candles intersecting the POI,
                 from first touch until price exits the zone
```

Preserved as separate fields: First Touch Time, Exit Time, Dwell Duration, Exit Direction, POI Dwell Bars. No maximum permitted dwell time is set by this standard. A delayed reaction inside a POI must **not** automatically invalidate BTMM. Dwell may later be interpreted using liquidity-generation and BTMM-state rules (not defined here).

### 9. Independent Future Data Fields

Named for forward reference only — none are computed, weighted, or combined into a composite score by this decision:

- `range_speed_ratio`
- `displacement_expansion_ratio`
- `normalized_speed_per_bar`
- `directional_efficiency`
- `directional_candle_share`
- `poi_dwell_bars`
- `speed_classification`

No composite market-speed score or weighting formula is defined.

### 10. Anchor Limitation

Automatic detection of the following remains unresolved: manipulation endpoint, approach starting price, POI first-touch price, reaction starting point, reaction endpoint. Their automatic detection depends on Ambiguity 14 (the BTMM state machine), which is **not** resolved or modified by this decision. Until Ambiguity 14 is resolved, BTMM movement-leg speed testing uses expert-labelled or otherwise explicitly approved anchors only.

### 11. What Remains Unresolved

This standard fixes single-candle speed, FVG displacement, BTMM movement-leg, and POI dwell **measurement** math only. It explicitly does **not** resolve:
- Ambiguity 14 (BTMM state machine) or the automatic anchors that depend on it.
- Any composite/weighted final speed or activity score.
- BTMM Accuracy (Ambiguity 8, resolved separately below).
- Freshness, mitigation, invalidation, or expiration for any POI.

These remain separate, pending decisions.

---

## POI Zone Interaction, Penetration, and Overshoot Standard

**Status:** Approved, **Provisional** — POI Zone Interaction, Penetration, and Overshoot Standard Version 1 — Provisional (resolves Ambiguity 8 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Does not modify any prior standard above.

### 1. Scope

Applies only to POIs with clearly defined upper and lower zone boundaries.

```
Zone Height = Zone Top − Zone Bottom
```

A zone with Zone Height ≤ 0 is invalid for interaction measurement. Support, Resistance, and Trendline tolerance remain separate decisions and must not automatically inherit this standard.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, H3/H4/D1/W1 POIs, H1/M15 market structure, M15/M5/M1 BTMM execution, different sessions, and different volatility regimes. The thresholds are not to be changed casually outside that calibration process.

### 2. Directional Entry and Far Boundaries

| POI direction | Entry Boundary | Far Boundary | Interaction Price |
|---|---|---|---|
| Bullish (approached from above) | Zone Top | Zone Bottom | Candle Low |
| Bearish (approached from below) | Zone Bottom | Zone Top | Candle High |

An approach from the opposite side is recorded as **NONCANONICAL_SIDE_INTERACTION** and must not be silently treated as a normal first touch.

### 3. Contact Tolerance

ATR(14) is calculated using the POI symbol and the interaction timeframe.

```
Contact Tolerance = MAX(2 × Minimum Price Tick, MIN(0.05 × ATR(14), 0.10 × Zone Height))
```

Contact Tolerance is used only to identify a close near miss. It must not enlarge or redefine the actual POI boundaries. The Minimum Price Tick is sourced from instrument metadata once the software layer exists. No fixed pip or point tolerances are used.

### 4. Overshoot Tolerance

```
Overshoot Tolerance = MAX(2 × Minimum Price Tick, MIN(0.10 × ATR(14), 0.25 × Zone Height))
```

Overshoot Tolerance does not redefine the zone boundaries.

### 5. Near-Miss and No-Contact Treatment

When price does not intersect the zone:
- **NEAR_MISS** applies only when Distance to Entry Boundary ≤ Contact Tolerance. NEAR_MISS is not an actual touch and must not increment the confirmed interaction count.
- **NO_CONTACT** applies when Distance to Entry Boundary > Contact Tolerance.

### 6. Bullish POI Penetration Measurements

```
Wick Penetration Distance = CLAMP(Zone Top − Candle Low, 0, Zone Height)
Wick Penetration Ratio = Wick Penetration Distance ÷ Zone Height
Wick Overshoot Distance = MAX(0, Zone Bottom − Candle Low)

Close Penetration Distance = CLAMP(Zone Top − Candle Close, 0, Zone Height)
Close Penetration Ratio = Close Penetration Distance ÷ Zone Height
Close Overshoot Distance = MAX(0, Zone Bottom − Candle Close)
```

### 7. Bearish POI Penetration Measurements

```
Wick Penetration Distance = CLAMP(Candle High − Zone Bottom, 0, Zone Height)
Wick Penetration Ratio = Wick Penetration Distance ÷ Zone Height
Wick Overshoot Distance = MAX(0, Candle High − Zone Top)

Close Penetration Distance = CLAMP(Candle Close − Zone Bottom, 0, Zone Height)
Close Penetration Ratio = Close Penetration Distance ÷ Zone Height
Close Overshoot Distance = MAX(0, Candle Close − Zone Top)
```

Invalid or zero Zone Height must be protected against before dividing (see SS1).

### 8. Geometric Interaction Classification

Uses Wick Penetration Ratio and Wick Overshoot Distance for the primary geometric classification.

| Classification | Requirements |
|---|---|
| **EDGE_TOUCH** | Actual zone intersection; Wick Penetration Ratio ≤ 0.25; no excessive overshoot |
| **PARTIAL_ENTRY** | Wick Penetration Ratio > 0.25 and ≤ 0.50; no excessive overshoot |
| **DEEP_ENTRY** | Wick Penetration Ratio > 0.50 and < 1.00; no excessive overshoot |
| **FAR_BOUNDARY_TOUCH** | Wick Penetration Ratio = 1.00; Wick Overshoot Distance = 0 |
| **CONTROLLED_OVERSHOOT** | Wick Overshoot Distance > 0 and ≤ Overshoot Tolerance |
| **EXCESSIVE_OVERSHOOT** | Wick Overshoot Distance > Overshoot Tolerance |

No additional depth or overshoot classes are defined.

### 9. Wick and Close Separation

Preserved independently: `wick_penetration_ratio`, `close_penetration_ratio`, `wick_overshoot_distance`, `close_overshoot_distance`. A wick beyond the far boundary is **not** equivalent to a candle close beyond the far boundary.

When a candle closes beyond the far boundary, record **CLOSE_BREACH_CANDIDATE** — this must not automatically mean final invalidation. **EXCESSIVE_OVERSHOOT** likewise remains only an invalidation *candidate*, not an automatic invalidation. General POI invalidation remains unresolved.

### 10. Geometric Eligibility for Later Reaction Analysis

Eligible for later reaction analysis: EDGE_TOUCH, PARTIAL_ENTRY, DEEP_ENTRY, FAR_BOUNDARY_TOUCH, CONTROLLED_OVERSHOOT.

Never counted as confirmed valid touches: NO_CONTACT, NEAR_MISS, NONCANONICAL_SIDE_INTERACTION, EXCESSIVE_OVERSHOOT. EXCESSIVE_OVERSHOOT is an invalidation candidate, not an automatically invalidated POI.

### 11. Interaction Numbering and Preserved Fields

Every interaction event preserves: `interaction_index`, `first_interaction_time`, `interaction_time`, `interaction_class`, `approach_side`, `wick_penetration_ratio`, `close_penetration_ratio`, `wick_overshoot_distance`, `close_overshoot_distance`.

The first confirmed zone intersection receives `interaction_index = 1`; each later confirmed intersection increments the index. NEAR_MISS and NO_CONTACT never increment the interaction index. This standard does not yet reduce quality because of repeated interactions.

### 12. Required Conceptual Separation

POI interaction geometry must remain separate from: reaction strength, departure speed, BTMM validity, entry validity, POI freshness, mitigation, final invalidation, and trade outcome. No single composite interaction-quality score is created.

### 13. What Remains Unresolved

This standard fixes zone-interaction geometry only. It explicitly does **not** define:
- Whether the reaction is strong.
- Minimum bounce distance.
- Required departure speed after contact.
- Entry confirmation.
- Freshness, partial mitigation, full mitigation.
- Repeated-touch degradation.
- Sweep rules.
- Final invalidation.
- Expiration.
- BTMM confirmation (Ambiguity 14, unchanged).

These remain separate, pending decisions.

---

## POI Reaction Strength, Distance, Efficiency, and Classification Standard

**Status:** Approved, **Provisional** — POI Reaction Strength Standard Version 1 — Provisional (resolves Ambiguity 9 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on the POI Zone Interaction, Penetration, and Overshoot Standard and the Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard above; does not modify either.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, H3/H4/D1/W1 POIs, H1/M15 market structure, M15/M5/M1 BTMM execution, different sessions, and different volatility regimes. The thresholds are not to be changed casually outside that calibration process.

### 1. Eligible Interaction Requirement

Reaction measurement may begin only after one of these eligible POI interaction classes (from the POI Zone Interaction Standard): EDGE_TOUCH, PARTIAL_ENTRY, DEEP_ENTRY, FAR_BOUNDARY_TOUCH, CONTROLLED_OVERSHOOT.

Not eligible: NO_CONTACT, NEAR_MISS, NONCANONICAL_SIDE_INTERACTION, EXCESSIVE_OVERSHOOT.

Eligibility for reaction measurement must not independently determine final POI validity or invalidity.

### 2. Reaction Start

```
Bullish POI: Reaction Start = the first confirmed candle after an eligible interaction that closes above Zone Top
Bearish POI: Reaction Start = the first confirmed candle after an eligible interaction that closes below Zone Bottom
```

Until Reaction Start exists, classify the interaction as **AWAITING_REACTION**. No maximum waiting time is defined. POI dwell time remains separate from reaction strength.

### 3. Reaction Anchor

```
Bullish POI: Reaction Anchor = Lowest Low from the first eligible interaction through the Reaction Start candle
Bearish POI: Reaction Anchor = Highest High from the first eligible interaction through the Reaction Start candle
```

A CONTROLLED_OVERSHOOT may contribute to the Reaction Anchor.

### 4. Five-Bar Evaluation Window

The Reaction Start candle is bar 1 of a five-bar window (Reaction Start + the next 4 confirmed candles). The window begins after Reaction Start is confirmed, not at the original POI interaction — this prevents delayed liquidity creation or POI dwell from being automatically treated as a weak reaction.

During an incomplete window, use **REACTION_IN_PROGRESS**. Record the earliest bar within the window on which Standard Reaction conditions are first achieved, and separately the earliest bar on which Strong Reaction conditions are first achieved. At completion of the fifth confirmed candle, assign the highest reaction tier achieved during the window: 1) STRONG_REACTION, 2) STANDARD_REACTION, 3) WEAK_REACTION.

### 5. Reaction Maximum Favorable Excursion (MFE)

```
Bullish POI: Reaction MFE = Highest High during the five-bar window − Reaction Anchor
Bearish POI: Reaction MFE = Reaction Anchor − Lowest Low during the five-bar window
```

Reaction MFE must not be negative. The candle time at which MFE first occurred is preserved.

### 6. ATR-Normalized Reaction Distance

```
Reference ATR = ATR(14) value on the Reaction Start candle (same instrument, symbol feed, and timeframe as the POI interaction)
ATR Reaction Ratio = Reaction MFE ÷ Reference ATR
```

Reference ATR ≤ 0 blocks a valid ATR Reaction Ratio or final reaction classification. Fixed pip or point thresholds must not replace this.

### 7. Zone Clearance

```
Bullish POI: Zone Clearance Distance = MAX(0, Highest High during the five-bar window − Zone Top)
Bearish POI: Zone Clearance Distance = MAX(0, Zone Bottom − Lowest Low during the five-bar window)
Zone Clearance Ratio = Zone Clearance Distance ÷ Zone Height
```

Zone Height ≤ 0 blocks a valid Zone Clearance Ratio or final reaction classification.

### 8. Reaction-Leg Efficiency and Speed

The reaction leg begins at the Reaction Start candle and ends at the first candle inside the five-bar window that produces the final MFE. Uses the approved Market Speed and Displacement Standard fields, calculated and preserved separately: Leg Bar Count, Net Directional Distance, Reference ATR, Normalized Speed Per Bar, Leg Path Distance, Directional Efficiency, Directional Candle Share, Reaction Speed Classification. All formulas are protected against zero denominators. No composite reaction-speed or reaction-quality score is created.

### 9. Standard Reaction

**STANDARD_REACTION** requires **all**, achieved within the five-bar window:
- ATR Reaction Ratio ≥ 0.75
- Zone Clearance Ratio ≥ 1.00
- Directional Efficiency ≥ 0.50
- Directional Candle Share ≥ 0.60

Does not require FAST or STRONG FAST speed classification.

### 10. Strong Reaction

**STRONG_REACTION** requires **all**, achieved within the five-bar window:
- ATR Reaction Ratio ≥ 1.25
- Zone Clearance Ratio ≥ 1.50
- Directional Efficiency ≥ 0.60
- Directional Candle Share ≥ 0.67
- Reaction Speed Classification is FAST or STRONG FAST

Tick volume remains secondary contextual evidence; missing tick volume must not automatically prevent Strong Reaction classification. RSI, MACD, Stochastic, ADX, Rate of Change, or other external indicators must not be made mandatory.

### 11. Weak Reaction

**WEAK_REACTION** applies when Reaction Start has been confirmed, the complete five-bar window has closed, and Standard Reaction conditions were not achieved. WEAK_REACTION must not automatically invalidate the POI.

### 12. Approved Reaction States

Only these five states are used: AWAITING_REACTION, REACTION_IN_PROGRESS, WEAK_REACTION, STANDARD_REACTION, STRONG_REACTION. FAILED_POI, INVALIDATED, EXPIRED, MITIGATED, SWEPT, and BROKEN are not defined or used as reaction-strength outcomes by this standard.

### 13. Required Independent Fields

Preserved separately: `reaction_start_time`, `reaction_anchor_price`, `reaction_window_bars`, `reaction_mfe`, `reaction_mfe_time`, `reference_atr`, `atr_reaction_ratio`, `zone_clearance_distance`, `zone_clearance_ratio`, `bars_to_standard_reaction`, `bars_to_strong_reaction`, `directional_efficiency`, `directional_candle_share`, `normalized_speed_per_bar`, `reaction_speed_classification`, `reaction_classification`.

When Standard or Strong conditions are not achieved, the corresponding bars-to field must remain unset or null rather than being assigned an invented number. No composite reaction score or weighting formula is created.

### 14. Required Conceptual Separation

Reaction strength must remain separate from: POI validity, BTMM validity, entry validity, trade outcome, trade profitability, final market reversal, POI freshness, partial mitigation, full mitigation, final invalidation, and expiration. A STRONG_REACTION does not independently prove any of these; a WEAK_REACTION does not independently disprove any of them.

### 15. What Remains Unresolved

This standard fixes reaction-strength measurement math only. It explicitly does **not** define:
- Maximum waiting time before Reaction Start.
- Maximum POI dwell time.
- Freshness, repeated-touch degradation.
- Partial mitigation, full mitigation.
- Sweep rules.
- Final POI invalidation.
- Expiration.
- Trade-entry confirmation.
- BTMM state-machine transitions (Ambiguity 14, unchanged).

These remain separate, pending decisions.

---

## Meaningful Swing High and Swing Low Detection Standard

**Status:** Approved, **Provisional** — Meaningful Swing High and Swing Low Detection Standard Version 1 — Provisional (resolves Ambiguity 10 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Does not modify any prior standard above, including the Equal Highs and Equal Lows Tolerance and Drawing Standard's own ATR-tolerance thresholds.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, M1/M5/M15/H1/H3/H4/D1/W1, different sessions, different volatility regimes, and different trend/consolidation conditions. The thresholds are not to be changed casually outside that calibration process.

### 1. Five-Candle Local Structure

A local pivot window = 2 confirmed candles before the candidate + the candidate candle/plateau + 2 confirmed candles after. A possible swing does not become a locally confirmed pivot until the two right-side candles have closed. For a plateau, the two-right-candle countdown begins only after the final plateau candle.

### 2. Local Swing High Candidate

Qualifies when its **wick high** (never close, body high, or candle colour) is the highest qualifying extreme within the five-candle window after applying Pivot Tie Tolerance — the qualifying highs on both sides must be lower after tie-tolerance handling.

### 3. Local Swing Low Candidate

Qualifies when its **wick low** (never close, body low, or candle colour) is the lowest qualifying extreme within the five-candle window after applying Pivot Tie Tolerance — the qualifying lows on both sides must be higher after tie-tolerance handling.

### 4. Pivot Tie Tolerance

```
Pivot Tie Tolerance = MAX(2 × Minimum Price Tick, 0.02 × ATR(14))
```

ATR(14) uses the same symbol, data provider, and timeframe as the candidate pivot. The Minimum Price Tick is sourced from instrument metadata once the software layer exists. No fixed pip or point values are used.

### 5. Adjacent Pivot Plateau

Adjacent candles whose relevant extreme prices are within Pivot Tie Tolerance form one pivot plateau, not multiple independent swing events:

```
Swing High plateau: Pivot Price = Highest High among all plateau candles
Swing Low plateau:  Pivot Price = Lowest Low among all plateau candles
```

Plateau Start Time and Plateau End Time are preserved. Adjacent plateau candles must not be counted as separate Equal High or Equal Low swing events. No maximum plateau length is invented.

### 6. Local Confirmation State

After the two required right-side candles close, the pivot is classified **LOCAL_SWING_CANDIDATE**. Local confirmation alone does not make the pivot a meaningful structural swing — it remains unavailable to Equal Highs, Equal Lows, Trendlines, Support, Resistance, or later market-structure logic until meaningful confirmation.

### 7. Pivot Reference ATR

```
Single-candle pivot: Pivot Reference ATR = ATR(14) value associated with the pivot candle
Plateau:             Pivot Reference ATR = Median ATR(14) across all plateau candles
```

Uses confirmed ATR values from the same symbol, data provider, and timeframe.

### 8. Meaningful Reversal Threshold

```
Meaningful Reversal Threshold = MAX(2 × Minimum Price Tick, 0.50 × Pivot Reference ATR)
```

Protected against missing ATR, zero ATR, or invalid price metadata. A candidate without a valid Pivot Reference ATR must not receive meaningful confirmation automatically.

### 9. Meaningful Swing High Confirmation

```
Swing High Reversal Excursion = Pivot Price − Lowest Low observed after the pivot or plateau
```

A local Swing High candidate becomes **CONFIRMED_MEANINGFUL_SWING_HIGH** when Swing High Reversal Excursion ≥ Meaningful Reversal Threshold. The first confirmed candle time achieving this is stored as `meaningful_confirmation_time`.

### 10. Meaningful Swing Low Confirmation

```
Swing Low Reversal Excursion = Highest High observed after the pivot or plateau − Pivot Price
```

A local Swing Low candidate becomes **CONFIRMED_MEANINGFUL_SWING_LOW** when Swing Low Reversal Excursion ≥ Meaningful Reversal Threshold. The first confirmed candle time achieving this is stored as `meaningful_confirmation_time`.

### 11. Candidate Replacement Before Meaningful Confirmation

Before meaningful confirmation, a higher high replaces an unconfirmed Swing High candidate, and a lower low replaces an unconfirmed Swing Low candidate. The replaced candidate is marked **SUPERSEDED** (with `superseded_by_swing_id` preserved). A superseded candidate never enters the confirmed meaningful swing sequence. Superseded records are never deleted from historical annotations or audit data.

### 12. Non-Repainting Requirement

Once a pivot reaches meaningful confirmation: Pivot Price, Pivot Start Time, and Pivot End Time must not move; the confirmed swing must not be deleted because a later candle creates a more extreme price (later price action becomes a new swing candidate, structure event, sweep candidate, break candidate, or other future event instead). The confirmed swing must not be exposed to historical backtests at the original pivot time — it becomes available to downstream logic only at `meaningful_confirmation_time`, to prevent look-ahead bias.

### 13. Alternating Meaningful Swing Sequence

The confirmed meaningful swing sequence must alternate Swing High / Swing Low / Swing High / Swing Low (or the inverse starting direction). Two same-direction confirmed meaningful swings must not appear consecutively without an opposite confirmed meaningful swing between them. Before an opposite meaningful swing confirms, a more extreme same-direction candidate replaces the prior unconfirmed candidate (SS11). Higher High, Higher Low, Lower High, and Lower Low labels are **not** defined by this standard.

### 14. Swing Strength Classification

| Classification | Condition |
|---|---|
| **STANDARD_SWING** | Reversal excursion ≥ 0.50 × Pivot Reference ATR (the confirmation threshold itself) |
| **STRONG_SWING** | Reversal excursion ≥ 1.00 × Pivot Reference ATR, achieved before the Pivot Price is materially breached |

`strength_confirmation_time` is stored when the STRONG_SWING threshold is first achieved. No additional strength tiers are defined.

**Material-breach limitation:** the exact numerical meaning of "materially breached" remains **unresolved**. No breach tolerance, breach-close rule, wick-breach rule, or invalidation threshold is invented by this standard — the STRONG_SWING upgrade remains partially dependent on that future, separate definition.

### 15. Equal Highs and Equal Lows Dependency

Equal Highs and Equal Lows must use two distinct confirmed meaningful swing events:
- Adjacent plateau candles count as one swing event.
- LOCAL_SWING_CANDIDATE records do not qualify.
- SUPERSEDED candidates do not qualify.
- At least one opposite confirmed meaningful swing must exist between two same-type swing events.

The existing Equal Highs and Equal Lows ATR-tolerance standard (0.05× / 0.10× Reference ATR strength thresholds and drawing boundaries) is **unchanged** by this decision.

### 16. Required States and Labels

Status (kept separate from direction and strength): FORMING, LOCAL_SWING_CANDIDATE, CONFIRMED_MEANINGFUL_SWING, SUPERSEDED. Direction: SWING_HIGH, SWING_LOW. Strength: STANDARD_SWING, STRONG_SWING. These three dimensions are never combined into one opaque field.

### 17. Required Fields

Preserved independently (no composite swing score): `swing_id`, `swing_direction`, `pivot_price`, `pivot_start_time`, `pivot_end_time`, `local_confirmation_time`, `meaningful_confirmation_time`, `pivot_reference_atr`, `pivot_tie_tolerance`, `reversal_threshold`, `reversal_excursion`, `strength_confirmation_time`, `swing_strength`, `swing_status`, `superseded_by_swing_id`, `timeframe`, `symbol`, `data_provider`.

### 18. Same-Timeframe Rule

Swing detection runs independently for every timeframe. An H4 candle must not form part of an M15 swing window. Higher-timeframe and lower-timeframe swings may later be linked or compared, but they remain separate detected events with separate IDs and confirmation times.

### 19. Required Conceptual Separation

Meaningful swing detection must remain separate from: Higher High, Higher Low, Lower High, Lower Low, Break of Structure, Change of Character, Sweep, Liquidity grab, Trendline validity, Support clustering, Resistance clustering, POI validity, POI invalidation, BTMM state transitions, entry confirmation, and trade outcome. None of these are defined by this standard.

### 20. What Remains Unresolved

This standard fixes local pivot detection, plateau handling, meaningful-reversal confirmation, non-repainting availability, and STANDARD/STRONG classification only. It explicitly does **not** define:
- The exact numerical meaning of "materially breached" (blocks a fully automatic STRONG_SWING upgrade).
- Higher High / Higher Low / Lower High / Lower Low labels.
- Break of Structure / Change of Character.
- Sweep / liquidity-grab rules.
- Trendline / Support / Resistance validity (Ambiguities 11–12, unchanged).
- BTMM state-machine transitions (Ambiguity 14, unchanged).

These remain separate, pending decisions.

---

## Bullish and Bearish Trendline Detection and Validation Standard

**Status:** Approved, **Provisional** — Bullish and Bearish Trendline Detection and Validation Standard Version 1 — Provisional (resolves Ambiguity 11 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on the Meaningful Swing High and Swing Low Detection Standard above; does not modify it.

**Calibration status:** This entire standard is provisional. All thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, M1/M5/M15/H1/H3/H4/D1/W1, different sessions, different volatility regimes, trending markets, and consolidating markets. The thresholds are not to be changed casually outside that calibration process.

### 1. Eligible Trendline Anchors

A trendline anchor must be a `CONFIRMED_MEANINGFUL_SWING`. `FORMING`, `LOCAL_SWING_CANDIDATE`, and `SUPERSEDED` records must not serve as anchors. Plateau candles represent one confirmed meaningful swing event and therefore one possible anchor. All anchors of one trendline must share the same symbol, data provider, and timeframe — swing events from different timeframes or providers must never be combined into one trendline.

### 2. Bullish Trendline Anchors

A Bullish Trendline connects two distinct confirmed meaningful Swing Lows:

```
Anchor 1 Price = First Swing Low Pivot Price
Anchor 2 Price = Second Swing Low Pivot Price
```

Anchor 2 must occur later than Anchor 1 and satisfy `Anchor 2 Price > Anchor 1 Price + Pivot Tie Tolerance`. If the two prices are within Pivot Tie Tolerance, classify the pair as **HORIZONTAL_CANDIDATE** — never a Bullish Trendline. It may later be considered under a separate, not-yet-defined Support standard.

### 3. Bearish Trendline Anchors

A Bearish Trendline connects two distinct confirmed meaningful Swing Highs:

```
Anchor 1 Price = First Swing High Pivot Price
Anchor 2 Price = Second Swing High Pivot Price
```

Anchor 2 must occur later than Anchor 1 and satisfy `Anchor 2 Price < Anchor 1 Price − Pivot Tie Tolerance`. If the two prices are within Pivot Tie Tolerance, classify the pair as **HORIZONTAL_CANDIDATE** — never a Bearish Trendline. It may later be considered under a separate, not-yet-defined Resistance standard.

### 4. Anchor Bar Position and Minimum Spacing

```
Single-candle swing: Anchor Bar Index = Pivot Candle Index
Plateau swing:       Anchor Bar Index = Plateau End Bar Index
```

The Anchor Price remains the approved Pivot Price for that swing/plateau. Anchor 2 must be at least **5 confirmed bars** after Anchor 1 — fewer than 5 bars cannot form a valid trendline candidate.

### 5. Trendline Equation

```
Raw Slope = (Anchor 2 Price − Anchor 1 Price) ÷ (Anchor 2 Bar Index − Anchor 1 Bar Index)
Line Price(t) = Anchor 1 Price + Raw Slope × (t − Anchor 1 Bar Index)
```

Bullish Trendline requires Raw Slope > 0; Bearish requires Raw Slope < 0. Zero or invalid bar-index denominators are guarded against.

### 6. Anchor Reference ATR

```
Anchor Reference ATR = Median ATR(14) across all confirmed candles from Anchor 1 through Anchor 2, inclusive
```

Uses the same symbol, data provider, and timeframe as the trendline. Missing, zero, or invalid Anchor Reference ATR blocks automatic slope classification.

### 7. Normalized Slope and Steepness Classification

```
Normalized Slope = ABS(Raw Slope) ÷ Anchor Reference ATR
```

| Classification | Condition |
|---|---|
| **HORIZONTAL_CANDIDATE** | Normalized Slope < 0.02 |
| **VALID_SLOPE** | 0.02 ≤ Normalized Slope ≤ 0.35 |
| **TOO_STEEP** | Normalized Slope > 0.35 |

A `TOO_STEEP` line must not provide valid trendline confirmation; it may be preserved as a rejected research candidate. No additional slope tiers are defined.

### 8. Trendline-Specific Tolerances

For each trendline interaction, using ATR(14) from the confirmed interaction candle:

```
Trendline Touch Tolerance = MAX(2 × Minimum Price Tick, 0.10 × ATR(14))
Trendline Pierce Tolerance = MAX(2 × Minimum Price Tick, 0.20 × ATR(14))
```

ATR and Minimum Price Tick use the same instrument, provider, and timeframe as the interaction. The Minimum Price Tick is sourced from instrument metadata once the software layer exists; no fixed pip/point values are used. **These tolerances apply only to Trendlines** — they must not replace POI zone, Support, Resistance, or Equal Highs/Lows tolerances.

### 9. Inter-Anchor Integrity

Every confirmed candle strictly between Anchor 1 and Anchor 2 is evaluated:

```
Bullish Trendline: reject the pair if Projected Line Price − Candle Close > Trendline Pierce Tolerance for any such candle
Bearish Trendline: reject the pair if Candle Close − Projected Line Price > Trendline Pierce Tolerance for any such candle
```

A wick-only crossing that stays within Trendline Pierce Tolerance does not automatically reject the anchor pair. This rule governs only initial anchor-pair integrity — it does not define final trendline invalidation.

### 10. Draft Trendline

An anchor pair becomes **DRAFT_TRENDLINE** only when all pass: both anchors eligible confirmed meaningful swings; both anchors share symbol/provider/timeframe; correct directional price condition; ≥5-confirmed-bar spacing; correct Raw Slope direction; `VALID_SLOPE` classification; inter-anchor integrity. A draft line becomes available to downstream logic only after Anchor 2 reaches `meaningful_confirmation_time` — it must not appear historically at Anchor 2's pivot time, to prevent look-ahead bias.

### 11. Third-Touch Confirmation

A `DRAFT_TRENDLINE` becomes **CONFIRMED_TRENDLINE** only when a third distinct confirmed meaningful swing of the same anchor direction interacts with the projected line.

```
Bullish: Bullish Touch Difference = Third Swing Low Pivot Price − Projected Line Price at the third swing bar
  Qualifying touch: ABS(Bullish Touch Difference) ≤ Trendline Touch Tolerance
  Controlled pierce: Bullish Touch Difference < −Trendline Touch Tolerance AND ≥ −Trendline Pierce Tolerance

Bearish: Bearish Touch Difference = Projected Line Price at the third swing bar − Third Swing High Pivot Price
  Qualifying touch: ABS(Bearish Touch Difference) ≤ Trendline Touch Tolerance
  Controlled pierce: Bearish Touch Difference < −Trendline Touch Tolerance AND ≥ −Trendline Pierce Tolerance
```

A third swing outside Trendline Pierce Tolerance must not confirm the line. The third swing is usable only from its own `meaningful_confirmation_time`.

### 12. Strong Trendline

A `CONFIRMED_TRENDLINE` becomes **STRONG_TRENDLINE** after a fourth distinct confirmed meaningful swing of the same anchor direction produces another qualifying touch or controlled pierce. Summary: 2 valid anchors = DRAFT_TRENDLINE; 3 qualifying confirmed meaningful swings = CONFIRMED_TRENDLINE; ≥4 qualifying confirmed meaningful swings = STRONG_TRENDLINE. The qualifying-touch count is structural evidence only — it does not define freshness, remaining trendline strength, repeated-touch degradation, expiration, or entry validity.

### 13. Trendline Break Candidate

```
Bullish: record TRENDLINE_BREAK_CANDIDATE when a confirmed candle closes below the projected line by more than Trendline Pierce Tolerance
Bearish: record TRENDLINE_BREAK_CANDIDATE when a confirmed candle closes above the projected line by more than Trendline Pierce Tolerance
```

A `TRENDLINE_BREAK_CANDIDATE` is **not** final invalidation. Confirmed break, reclaim, retest, false break, sweep, and final invalidation are not defined by this standard.

### 14. Multiple Candidate Trendlines

The system may preserve multiple trendline candidates on the same timeframe. Each preserves its own anchor pair, Raw Slope, Normalized Slope, status, touch history, break-candidate history, and availability time. Older trendlines must never be silently deleted or replaced when a newer anchor pair appears. No "Best Trendline," "Primary Trendline," trendline ranking score, or composite trendline score is created.

### 15. Non-Repainting Requirement

After a trendline candidate is created: anchor IDs, prices, and times never move; Raw Slope is never silently recalculated; a third or fourth touch never refits the original line (a new anchor pair creates a new candidate instead). Backtests access a DRAFT_TRENDLINE only from `candidate_available_time`, a CONFIRMED_TRENDLINE only from `confirmation_time`, and a STRONG_TRENDLINE only from `strong_confirmation_time` — later-confirmed states are never exposed at earlier historical candles.

### 16. Required States and Direction

Status: HORIZONTAL_CANDIDATE, TOO_STEEP, DRAFT_TRENDLINE, CONFIRMED_TRENDLINE, STRONG_TRENDLINE, TRENDLINE_BREAK_CANDIDATE. Direction (kept separate): BULLISH_TRENDLINE, BEARISH_TRENDLINE. Never combined into one opaque field.

### 17. Required Fields

Preserved independently (no composite Trendline score): `trendline_id`, `trendline_direction`, `anchor_1_swing_id`, `anchor_2_swing_id`, `anchor_1_price`, `anchor_2_price`, `anchor_1_bar_index`, `anchor_2_bar_index`, `raw_slope`, `anchor_reference_atr`, `normalized_slope`, `trendline_status`, `candidate_available_time`, `confirmation_time`, `strong_confirmation_time`, `qualifying_touch_count`, `last_touch_time`, `last_touch_difference`, `break_candidate_time`, `timeframe`, `symbol`, `data_provider`.

### 18. Required Conceptual Separation

Trendline detection and validation must remain separate from: Higher High, Higher Low, Lower High, Lower Low, Break of Structure, Change of Character, Support, Resistance, Sweep, Liquidity grab, final trendline invalidation, entry confirmation, BTMM state transitions, and trade outcome. None of these are defined by this standard.

### 19. What Remains Unresolved

This standard fixes anchor eligibility, slope/steepness classification, touch/pierce tolerances, inter-anchor integrity, draft/confirmed/strong progression, and non-repainting availability only. It explicitly does **not** define:
- Final trendline invalidation.
- Required retest after a break.
- Reclaim.
- False break.
- Sweep.
- Trendline expiration.
- Maximum trendline age.
- Repeated-touch degradation.
- Entry confirmation.
- HH, HL, LH, or LL.
- BOS or CHoCH.
- Support clustering.
- Resistance clustering.
- BTMM state transitions.

These remain separate, pending decisions.

---

## Support and Resistance Detection and Validation Standard

**Status:** Approved, **Provisional** — Support and Resistance Detection and Validation Standard Version 1 — Provisional (resolves Ambiguity 12 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on the Meaningful Swing High and Swing Low Detection Standard, the POI Reaction Strength Standard, and (for the horizontal-candidate relationship only) the Trendline standard above; modifies none of them.

**Evidence / provisional status (must accompany every citation of this standard):** this standard is **AUTHOR-APPROVED**, **ENGINEERING-PROVISIONAL**, **NOT YET EMPIRICALLY CALIBRATED**, **NOT YET OUT-OF-SAMPLE VALIDATED**, and **NOT PRODUCTION-APPROVED**. Its thresholds must never be presented as universal trading laws.

**Calibration requirements:** all thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, M1/M5/M15/H1/H3/H4/D1/W1, different sessions, different volatility regimes, trending markets, and consolidating markets. The thresholds are not to be changed casually outside that calibration process.

### 1. Origin Eligibility

A Support origin must be a `CONFIRMED_MEANINGFUL_SWING_LOW`; a Resistance origin must be a `CONFIRMED_MEANINGFUL_SWING_HIGH` (per the Meaningful Swing Standard). `FORMING`, `LOCAL_SWING_CANDIDATE`, and `SUPERSEDED` records must not create a zone. All origin and validation events for one zone must share the same symbol, data provider, and timeframe.

### 2. Initial Creator Principle

The earliest eligible swing that creates the zone becomes `ORIGIN_CREATOR` (`origin_creator_swing_id`, `origin_creator_price`, `origin_creator_time` preserved). Later touches must not move the origin price, replace the origin swing, average the zone with later prices, recalculate the original boundaries, resize the original zone, or recenter the original zone. A separate eligible origin creates a separate candidate zone.

### 3. Creator Reference ATR

```
Single-candle origin: Creator Reference ATR = ATR(14) at the origin swing candle
Origin plateau:       Creator Reference ATR = Median ATR(14) across all plateau candles
```

Uses the same symbol, provider, and timeframe. Guarded against missing ATR, zero ATR, invalid price metadata, or invalid minimum-tick metadata.

### 4. Horizontal Zone Depth

```
Horizontal Zone Depth = MAX(2 × Minimum Price Tick, 0.10 × Creator Reference ATR)
```

The Minimum Price Tick is sourced from instrument metadata once the software layer exists; no fixed pip/point values are used. Horizontal Zone Depth becomes fixed after zone creation.

### 5. Support Boundaries

```
Zone Bottom = Origin Swing Low Pivot Price
Zone Top = Zone Bottom + Horizontal Zone Depth
```

The Support zone extends upward from the original Swing Low extreme.

### 6. Resistance Boundaries

```
Zone Top = Origin Swing High Pivot Price
Zone Bottom = Zone Top − Horizontal Zone Depth
```

The Resistance zone extends downward from the original Swing High extreme. A zone with Zone Top ≤ Zone Bottom must be rejected as invalid geometry.

### 7. Origin Reaction Requirement

The candidate origin is evaluated using the approved POI Reaction Strength Standard. A meaningful origin swing producing only `WEAK_REACTION` becomes `REJECTED_ORIGIN_CANDIDATE`. A meaningful origin swing producing `STANDARD_REACTION` or `STRONG_REACTION` becomes `DRAFT_SUPPORT` or `DRAFT_RESISTANCE` depending on direction. The draft zone becomes available only after the origin reaction has been fully classified — it must not be exposed historically at the original pivot time.

### 8. Horizontal Interaction Tolerances

For each later interaction, using ATR(14) from the confirmed interaction candle:

```
Horizontal Touch Tolerance = MAX(2 × Minimum Price Tick, 0.05 × ATR(14))
Horizontal Pierce Tolerance = MAX(2 × Minimum Price Tick, 0.15 × ATR(14))
```

These tolerances apply only to Support and Resistance — they must not replace Trendline, Equal Highs/Lows, POI zone interaction, or other POI-specific tolerances.

### 9. Qualifying Support Touch

A later Support touch must use a distinct `CONFIRMED_MEANINGFUL_SWING_LOW`:

```
Support Touch Difference = Swing Low Pivot Price − Zone Bottom
```

Geometrically acceptable when both: `Swing Low Pivot Price ≤ Zone Top + Horizontal Touch Tolerance` AND `Swing Low Pivot Price ≥ Zone Bottom − Horizontal Pierce Tolerance`. A geometrically acceptable touch counts only when it produces at least `STANDARD_REACTION`. A `STRONG_REACTION` is supporting evidence but does not replace the distinct-touch requirement.

### 10. Qualifying Resistance Touch

A later Resistance touch must use a distinct `CONFIRMED_MEANINGFUL_SWING_HIGH`. Geometrically acceptable when both: `Swing High Pivot Price ≥ Zone Bottom − Horizontal Touch Tolerance` AND `Swing High Pivot Price ≤ Zone Top + Horizontal Pierce Tolerance`. Counts only when it produces at least `STANDARD_REACTION`. A `STRONG_REACTION` is supporting evidence but does not replace the distinct-touch requirement.

### 11. Distinct-Touch Requirement

A pivot plateau counts as one touch. `LOCAL_SWING_CANDIDATE`, `SUPERSEDED`, `FORMING`, and `NEAR_MISS` do not count. Multiple candles belonging to one interaction event count as one touch. At least one opposite confirmed meaningful swing must exist between two same-type qualifying touches. Not every candle inside the zone is counted as a separate touch.

### 12. Confirmation and Strength

| Qualifying reactions (including origin) | Classification |
|---|---|
| 1 | `DRAFT_SUPPORT` / `DRAFT_RESISTANCE` |
| 2 distinct | `CONFIRMED_SUPPORT` / `CONFIRMED_RESISTANCE` |
| 3 or more distinct | `STRONG_SUPPORT` / `STRONG_RESISTANCE` |

Every counted interaction must produce at least `STANDARD_REACTION`. No additional strength tiers. Touch count is structural evidence only — it does not define freshness, remaining zone quality, repeated-touch degradation, entry validity, or expiration.

### 13. Break Candidate

```
Support:    record SUPPORT_BREAK_CANDIDATE when Zone Bottom − Candle Close > Horizontal Pierce Tolerance
Resistance: record RESISTANCE_BREAK_CANDIDATE when Candle Close − Zone Top > Horizontal Pierce Tolerance
```

These are break candidates only — they must not automatically mean final invalidation. Confirmed break, reclaim, retest, false break, sweep, and role reversal are not defined by this standard.

### 14. Non-Repainting Behavior

After a horizontal zone is created: origin swing ID, origin price, origin time, Creator Reference ATR, Zone Top, Zone Bottom, and zone depth must not move or be recalculated; later touches must not recenter or resize the zone; a later origin creates a new zone candidate. Backtests access DRAFT status only after `candidate_available_time`, CONFIRMED status only after `confirmation_time`, and STRONG status only after `strong_confirmation_time` — later-confirmed statuses are never exposed on earlier candles.

### 15. Multiple Horizontal Zones

Multiple Support and Resistance candidates are preserved on the same timeframe, each keeping its own origin creator, fixed boundaries, touch history, reaction history, status history, and break-candidate history. Nearby zones are never silently merged. No `BEST_SUPPORT`, `BEST_RESISTANCE`, `PRIMARY_ZONE`, zone-ranking score, or composite-strength score is created.

### 16. Relationship with Equal Highs and Equal Lows

Equal Lows ≠ Support; Equal Highs ≠ Resistance. The same confirmed meaningful swings may independently satisfy both standards — when that occurs, both labels are preserved. Equal Highs/Equal Lows primarily describe horizontal liquidity clustering; Support/Resistance require an initial creator, fixed creator-based boundaries, a qualifying origin reaction, and later distinct qualifying reactions. These POI types are never silently merged, and the approved Equal Highs/Equal Lows formulas are unchanged.

### 17. Relationship with Trendline Horizontal Candidates

A `HORIZONTAL_CANDIDATE` from Trendline evaluation may be evaluated under this Support or Resistance standard, but it must not automatically become Support or Resistance — it must independently pass origin eligibility, creator boundary, origin reaction, touch tolerance, distinct-touch, and confirmation requirements. The approved Trendline formulas and thresholds are unchanged.

### 18. Required States

Status: `REJECTED_ORIGIN_CANDIDATE`, `DRAFT_SUPPORT`, `DRAFT_RESISTANCE`, `CONFIRMED_SUPPORT`, `CONFIRMED_RESISTANCE`, `STRONG_SUPPORT`, `STRONG_RESISTANCE`, `SUPPORT_BREAK_CANDIDATE`, `RESISTANCE_BREAK_CANDIDATE`. Zone type (kept separate): `SUPPORT`, `RESISTANCE`. Never combined into one opaque field.

### 19. Required Fields

Preserved independently (no composite score): `horizontal_zone_id`, `zone_type`, `origin_creator_swing_id`, `origin_creator_price`, `origin_creator_time`, `creator_reference_atr`, `zone_top`, `zone_bottom`, `zone_depth`, `zone_status`, `candidate_available_time`, `confirmation_time`, `strong_confirmation_time`, `qualifying_touch_count`, `last_touch_swing_id`, `last_touch_time`, `last_touch_price`, `last_touch_reaction_class`, `break_candidate_time`, `timeframe`, `symbol`, `data_provider`.

### 20. Required Conceptual Separation

Support and Resistance detection must remain separate from: Equal Highs, Equal Lows, Trendlines, HH, HL, LH, LL, BOS, CHoCH, Sweep, Liquidity grab, final invalidation, entry confirmation, BTMM state transitions, and trade outcome. None of these are defined by this standard.

### 21. What Remains Unresolved

This standard fixes origin eligibility, creator-based fixed boundaries, origin-reaction gating, touch/pierce tolerances, distinct-touch confirmation, DRAFT/CONFIRMED/STRONG progression, break-candidate detection, and non-repainting availability only. It explicitly does **not** define:
- Final Support or Resistance invalidation.
- Confirmed break.
- Reclaim.
- Retest.
- False break.
- Role reversal (Support becoming Resistance, or Resistance becoming Support).
- Freshness.
- Repeated-touch degradation.
- Partial mitigation.
- Full mitigation.
- Expiration.
- Zone merging.
- Zone ranking.
- Entry confirmation.
- BTMM state transitions.

These remain separate, pending decisions.

---

## Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard

**Status:** Approved, **Provisional** — Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard Version 1 — Provisional (resolves Ambiguity 13 in `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). Builds on the Candle Measurement Standard, the Small Candle and Recent Market Context Standard, the Volume/Momentum/Price-Activity Proxy Standard, and the Market Speed and Displacement Standard; modifies none of them.

**Evidence / provisional status (must accompany every citation of this standard):** this standard is **AUTHOR-APPROVED**, **ENGINEERING-PROVISIONAL**, **NOT YET EMPIRICALLY CALIBRATED**, **NOT YET OUT-OF-SAMPLE VALIDATED**, and **NOT PRODUCTION-APPROVED**. Its thresholds must never be presented as universal trading laws.

**Calibration requirements:** all thresholds below must later be calibrated against expert-approved examples, expert-rejected examples, XAUUSD, EURUSD, GBPUSD, relevant project timeframes, different sessions, different volatility regimes, trending markets, and consolidating markets. The thresholds are not to be changed casually outside that calibration process.

### 1. Required Separation

This standard determines only whether the original failed directional candle forms a valid Buy-to-Sell POI or Sell-to-Buy POI. It is kept strictly separate from: a later revisit to the POI, POI interaction geometry, POI reaction strength after a revisit, freshness, mitigation, final invalidation, BTMM confirmation, entry confirmation, and trade outcome. A later revisit or later trade result must never retroactively confirm the original pattern.

### 2. Preceding Comparison Group

```
Preceding Maximum Range = largest Total Range among the 3 confirmed candles immediately before the candidate candle
Candidate Size Ratio = Candidate Total Range ÷ Preceding Maximum Range
```

Guarded against a missing or zero Preceding Maximum Range. This three-candle comparison window is fixed and must not be changed.

### 3. Buy-to-Sell Candidate Candle

Must be a confirmed closed bullish candle (`Close > Open`) appearing within an existing upward-price context. The full quantitative definition of that preceding upward-price context remains unresolved and is **not** defined here using HH, HL, BOS, CHoCH, a moving average, or any other invented structure rule.

```
Bullish Close Position = (Close − Low) ÷ Total Range
```

| Tier | Candidate Size Ratio | Body Efficiency | Bullish Close Position |
|---|---|---|---|
| `STANDARD_BUY_TO_SELL_CANDIDATE` | ≥ 2.00 | ≥ 0.60 | ≥ 0.70 |
| `STRONG_BUY_TO_SELL_CANDIDATE` | ≥ 3.00 | ≥ 0.70 | ≥ 0.80 |

A zero-range or invalid candle cannot qualify.

### 4. Sell-to-Buy Candidate Candle

Must be a confirmed closed bearish candle (`Close < Open`) appearing within an existing downward-price context. The full quantitative definition of that preceding downward-price context remains unresolved and is **not** invented here.

```
Bearish Close Position = (High − Close) ÷ Total Range
```

| Tier | Candidate Size Ratio | Body Efficiency | Bearish Close Position |
|---|---|---|---|
| `STANDARD_SELL_TO_BUY_CANDIDATE` | ≥ 2.00 | ≥ 0.60 | ≥ 0.70 |
| `STRONG_SELL_TO_BUY_CANDIDATE` | ≥ 3.00 | ≥ 0.70 | ≥ 0.80 |

### 5. Three-Bar Reversal Confirmation Window

Evaluate exactly 3 confirmed candles immediately after the candidate candle (confirmation bar 1, 2, 3). The pattern may confirm on bar 1, 2, or 3 once all required conditions are first satisfied; the earliest confirmed candle time at which they were first satisfied is stored. If confirmation bar 3 closes without Standard Reversal conditions met, classify `REJECTED_INSUFFICIENT_REVERSAL`. The confirmation window must not be extended beyond three candles by this standard.

### 6. Candidate Reference ATR and Continuation Close Tolerance

```
Candidate Reference ATR = ATR(14) on the candidate candle
Continuation Close Tolerance = MAX(2 × Minimum Price Tick, 0.10 × Candidate Reference ATR)
```

Same symbol, data provider, and timeframe. The Minimum Price Tick is sourced from instrument metadata once the software layer exists; no fixed pip/point values are used. Guarded against missing, zero, or invalid ATR or tick metadata.

### 7. Directional Continuation Rejection

```
Buy-to-Sell:  REJECTED_DIRECTIONAL_CONTINUATION when Post-Candidate Close − Candidate High > Continuation Close Tolerance
Sell-to-Buy:  REJECTED_DIRECTIONAL_CONTINUATION when Candidate Low − Post-Candidate Close > Continuation Close Tolerance
```

Applies to any post-candidate confirmed candle evaluated before reversal confirmation. A wick beyond Candidate High or Candidate Low is stored separately as `continuation_wick_excursion` and must not alone reject the pattern — confirmed close continuation is the primary rejection evidence. Once `REJECTED_DIRECTIONAL_CONTINUATION` occurs before reversal confirmation, the candidate must not later become confirmed from the same three-bar window.

### 8. Opposite Close Displacement

```
Buy-to-Sell:  Lowest Reversal Close  = lowest confirmed close observed in the reversal window so far
              Opposite Close Displacement = Candidate Close − Lowest Reversal Close
Sell-to-Buy:  Highest Reversal Close = highest confirmed close observed in the reversal window so far
              Opposite Close Displacement = Highest Reversal Close − Candidate Close

Opposite Close Displacement Ratio = Opposite Close Displacement ÷ Candidate Total Range
```

The displacement must not be negative. Close displacement is the approved confirmation measurement; opposite-direction wick excursion may be stored separately if later required.

### 9. Candidate Midpoint

```
Candidate Midpoint = (Candidate High + Candidate Low) ÷ 2
```

### 10. Reversal-Leg Measurements

Using the approved Market Speed and Displacement Standard Version 1 — Provisional, evaluate the opposite-direction reversal movement over the post-candidate candles available from confirmation bar 1 through the current evaluated confirmation bar. Preserve independently: Leg Bar Count, Net Directional Distance, Leg Path Distance, Directional Efficiency, Directional Candle Share, Normalized Speed Per Bar, and Reversal Speed Classification. For Buy-to-Sell the movement direction is bearish; for Sell-to-Buy the movement direction is bullish. No composite reversal score is created, and the approved Market Speed formulas/thresholds are unchanged. Any additional anchor detail not already defined by that standard or this decision is recorded as unresolved rather than invented.

### 11. Standard Reversal

| Direction | Required conditions (all, within the three-bar window) |
|---|---|
| Buy-to-Sell | At least one confirmed post-candidate close below Candidate Midpoint; Opposite Close Displacement Ratio ≥ 0.50; Directional Efficiency ≥ 0.50; Directional Candle Share ≥ 0.67; no `REJECTED_DIRECTIONAL_CONTINUATION` |
| Sell-to-Buy | At least one confirmed post-candidate close above Candidate Midpoint; Opposite Close Displacement Ratio ≥ 0.50; Directional Efficiency ≥ 0.50; Directional Candle Share ≥ 0.67; no `REJECTED_DIRECTIONAL_CONTINUATION` |

The earliest bar on which all requirements were achieved is stored.

### 12. Strong Reversal

| Direction | Required conditions (all, within the three-bar window) |
|---|---|
| Buy-to-Sell | At least one confirmed post-candidate close below Candidate Low; Opposite Close Displacement Ratio ≥ 1.00; Directional Efficiency ≥ 0.60; Directional Candle Share ≥ 0.67; Reversal Speed Classification is FAST or STRONG FAST; no `REJECTED_DIRECTIONAL_CONTINUATION` |
| Sell-to-Buy | At least one confirmed post-candidate close above Candidate High; Opposite Close Displacement Ratio ≥ 1.00; Directional Efficiency ≥ 0.60; Directional Candle Share ≥ 0.67; Reversal Speed Classification is FAST or STRONG FAST; no `REJECTED_DIRECTIONAL_CONTINUATION` |

### 13. Overall Pattern-Strength Rule

The final pattern strength is limited by the weaker required component:

| Candidate candle | Opposite reversal | Pattern strength |
|---|---|---|
| Standard | Standard | `STANDARD_PATTERN` |
| Standard | Strong | `STANDARD_PATTERN` |
| Strong | Standard | `STANDARD_PATTERN` |
| Strong | Strong | `STRONG_PATTERN` |

A candidate candle without at least Standard Reversal confirmation must be rejected. A large candle alone must never be classified as a confirmed Buy-to-Sell or Sell-to-Buy POI.

### 14. Complete Candle-Range Boundaries

```
Zone Bottom = Candidate Candle Low
Zone Top = Candidate Candle High
```

Applies after successful reversal confirmation, using the complete failed-candle range. The zone must not be refined, shrunk, averaged, or recentered by this standard.

### 15. Required States

`FORMING` (candidate candle has not closed); `REVERSAL_PENDING` (candidate closed, candidate requirements pass, three-bar window still evaluating); `STANDARD_PATTERN`; `STRONG_PATTERN`; `REJECTED_CANDIDATE_CANDLE` (candidate fails minimum candle requirements); `REJECTED_DIRECTIONAL_CONTINUATION`; `REJECTED_INSUFFICIENT_REVERSAL`. Pattern direction (`BUY_TO_SELL`/`SELL_TO_BUY`) is kept separate, never combined into one opaque field.

### 16. Non-Repainting Availability

A confirmed POI becomes available to downstream logic only at `reversal_confirmation_time`; it must not appear historically at the candidate candle's original time. Once confirmed: candidate OHLC values must not move, zone boundaries must not move, reversal confirmation time must not move, and later price action must not retrospectively alter the original pattern classification. Later lifecycle events remain separate.

### 17. Required Fields

Preserved independently (no composite score): `failed_candle_id`, `pattern_direction`, `candidate_open`, `candidate_high`, `candidate_low`, `candidate_close`, `candidate_total_range`, `candidate_body_efficiency`, `candidate_directional_close_position`, `preceding_maximum_range`, `candidate_size_ratio`, `candidate_strength`, `candidate_reference_atr`, `continuation_close_tolerance`, `continuation_close_breach`, `continuation_wick_excursion`, `reversal_window_bars`, `opposite_close_displacement`, `opposite_close_displacement_ratio`, `directional_efficiency`, `directional_candle_share`, `normalized_speed_per_bar`, `reversal_speed_classification`, `reversal_confirmation_time`, `reversal_strength`, `pattern_strength`, `pattern_status`, `zone_top`, `zone_bottom`, `timeframe`, `symbol`, `data_provider`.

### 18. Required Conceptual Separation

Pattern confirmation must remain separate from: future POI interaction geometry, future POI reaction strength, freshness, partial mitigation, full mitigation, repeated-touch degradation, final invalidation, expiration, BTMM validity, entry validity, trade profitability, and trade outcome. A `STRONG_PATTERN` does not independently prove any of these.

### 19. What Remains Unresolved

This standard fixes candidate-candle qualification, the three-candle preceding comparison group, the three-bar reversal confirmation window, directional-continuation rejection, opposite close displacement, and STANDARD/STRONG reversal and overall pattern-strength classification only. It explicitly does **not** define:
- The full quantitative preceding upward-price context (Buy-to-Sell).
- The full quantitative preceding downward-price context (Sell-to-Buy).
- Freshness.
- Partial mitigation.
- Full mitigation.
- Repeated-touch degradation.
- Final POI invalidation.
- Expiration.
- Retest entry confirmation.
- BTMM state transitions.
- Trade outcome.

These remain separate, pending decisions.
