# Ambiguities Requiring Author Decision

Every entry below follows the same structure: (1) what the book says, (2) why it cannot yet be coded precisely, (3) possible numerical measurements to consider, (4) **no threshold is chosen here**, (5) status = requires author approval.

None of these are invented rules — each is a direct reflection of language the book itself uses without a supplied number. Once the author picks values, they should be moved into the relevant `knowledge/` file as a confirmed rule and removed from this register. Items marked **✅ RESOLVED** below have been decided by the author and are kept in this register (rather than deleted) as a record of the decision; the authoritative, implementation-ready version of each resolved rule lives in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) or the relevant POI/BTMM file.

---

### 1. "Strong candle" / "Large candle" (general displacement/momentum candles) — ✅ RESOLVED

- **Book says:** Across Order Blocks, Fair Value Gaps, Buy-to-Sell/Sell-to-Buy candles, Base Rally/Drop, and Engulfing patterns, the displacement candle must be "significantly bigger," "strong and aggressive," or "much bigger" than the reference candle(s) — quantified only as a ratio (≥2×, ideally ≥3×) with no definition of *how size is measured*.
- **Why it couldn't be coded precisely before:** "Size" could mean full candle range (high−low), body-only (open−close), or body-only excluding wicks. These give different results on wicky candles. The book never states which.
- **Possible numerical measurements that were considered:** (a) full high-low range ratio; (b) body-only (open-close) ratio; (c) body ratio with a minimum wick-exclusion filter; (d) ATR-normalized size instead of raw candle-to-candle ratio.
- **Decision (Candle Measurement Standard Version 1, approved by the author):**
  - Candle size is measured as the **complete high-to-low total range** (option (a) above), not body-only and not ATR-normalized: `Candle Total Range = High − Low`.
  - Size comparisons use `Size Ratio = Key Candle Total Range ÷ Reference Candle Total Range`.
  - Classification: Size Ratio < 2.0 → does not satisfy the size requirement; 2.0 ≤ Size Ratio < 3.0 → valid/standard pattern; Size Ratio ≥ 3.0 → strong pattern.
  - Candle body (`|Close − Open|`) and Body Efficiency (`Body ÷ Total Range`) are tracked as a **separate** quality measurement and must not replace the total-range ratio rule.
  - Wicks are never excluded from the total-range measurement; wick quality is evaluated separately per POI type (e.g., Pressure Wick, resolved separately under Ambiguity 6).
  - ATR is not used to normalize or replace the 2×/3× rule; ATR is reserved for later use only as a secondary cross-symbol/cross-timeframe/cross-volatility-regime normalization measurement.
  - Full formulas, classification table, and POI-by-POI application are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md).
- **Status:** Resolved — Candle Measurement Standard Version 1 approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule.

### 2. "Small candle" (base candles, engulfed candles, pre-FVG candles) — ✅ RESOLVED

- **Book says:** Base candles must be "short in height," "small in total range"; engulfed candles must be "relatively small"; pre-FVG candles must be "noticeably smaller" than the displacement candle — again, no ratio or absolute size given for what counts as "small" on its own (only the *relative* 2–3× multiple to the following candle is numeric).
- **Why it couldn't be coded precisely before:** "Small" was defined only in relation to the next candle, never against a market-volatility baseline (e.g., average true range), so on a low-volatility day "small" and "large" would both shrink together and the ratio rule alone might misfire.
- **Possible numerical measurements that were considered:** (a) size relative to a rolling ATR; (b) size relative to the symbol's recent N-candle average range; (c) a fixed pip/point floor per symbol.
- **Decision (Small Candle Standard Version 1, approved by the author):**
  - Continues using Candle Total Range = High − Low from Candle Measurement Standard V1 (not modified).
  - A candle qualifies as small relative to a key candle when Small Candle Total Range ≤ 0.50 × Key Candle Total Range (equivalent to Key Candle Total Range ≥ 2 × Small Candle Total Range).
  - A strong volume-switch relationship exists when Small Candle Total Range ≤ 0.3333 × Key Candle Total Range (equivalent to Key Candle Total Range ≥ 3 × Small Candle Total Range).
  - This relative rule is supplemented — never replaced — by a separate, secondary **Recent Market Context** classification: Recent Median Range = the median Total Range of the previous 20 confirmed candles (excluding the candidate candle); a candle is Contextually Small (≤0.75× median), Contextually Normal (>0.75× to ≤1.25× median), or Contextually Large (>1.25× median). The contextual classification must not automatically reject a pattern that already satisfies the relative 2×/3× rule.
  - No fixed pip/point measurements are used, so the rule works unmodified across XAUUSD, EURUSD, GBPUSD, and all timeframes.
  - POI-specific comparison targets: Order Block compares the displacement candle to the immediately preceding smaller candle; Engulfing compares the engulfing candle to the immediately preceding candle; Fair Value Gap compares the displacement candle to the largest Total Range among the relevant preceding-candle group; Base Rally/Base Drop compares the departure candle to the largest Total Range among all base candles; Buy-to-Sell/Sell-to-Buy compares the failed directional candle to the largest Total Range among the relevant preceding-candle group.
  - Full formulas, classification tables, and POI-by-POI application are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md).
- **Still open (explicitly not resolved by this decision):** the number of preceding candles in a comparison group; the number of candles forming a valid base; minimum/maximum base duration; and reversal confirmation distance after a Buy-to-Sell/Sell-to-Buy candle (Ambiguity 13). These remain separate unresolved decisions.
- **Status:** Resolved — Small Candle Standard Version 1 approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule.

### 3. "High volume" / "Strong momentum" / "Clear displacement" — ✅ RESOLVED

- **Book says:** These phrases recur constantly (e.g., "strong buying pressure," "clear directional price movement," "strong and aggressive bullish displacement") to describe the qualifying move for OB, FVG, engulfing, and buy-to-sell/sell-to-buy candles.
- **Why it couldn't be coded precisely before:** The book has no real trade-volume data source in view (retail Forex feeds don't carry true exchange volume) — it is describing *price-action proxies* for volume/momentum (candle size, speed of movement) rather than an actual volume indicator. It never states which proxy (candle size ratio, ATR multiple, momentum oscillator, tick volume) should be used computationally, beyond the specific 2×/3× candle-size rules already captured per-POI in `POI_MASTER_CATALOG.md`.
- **Possible numerical measurements that were considered:** (a) treat "volume switch" purely as the already-specified candle-size ratio (no separate volume proxy needed); (b) add tick-volume or broker volume as a secondary confirmation filter; (c) use a momentum indicator (e.g., rate-of-change) as a supplementary aggressiveness score.
- **Decision (Volume and Momentum Proxy Standard Version 1, approved by the author):**
  - Volume/momentum/pressure/activity-switch is interpreted primarily from **price and candle behaviour**, using five separate, non-combined measurements: Relative Size Ratio (reuses Candle Measurement Standard V1 / Small Candle Standard V1), Range Context Ratio (`Key Candle Total Range ÷ Median Total Range of the previous 20 confirmed candles`, current candle excluded from the baseline), Body Efficiency (`|Close − Open| ÷ (High − Low)`), Bullish Close Position (`(Close − Low) ÷ (High − Low)`), and Bearish Close Position (`(High − Close) ÷ (High − Low)`). These fields are **not** combined into a weighted score at this stage.
  - Tick volume, where available, is a **secondary** contextual measurement only: `Relative Tick Volume = Current Candle Tick Volume ÷ Median Tick Volume of the previous 20 confirmed candles` (current candle excluded), reported as a status of SUPPORTS / NEUTRAL / CONTRADICTS / MISSING. Tick volume is **not** a mandatory POI-validity requirement, and missing tick volume must **not** automatically invalidate a POI. Tick-volume values must stay tagged to their provider/source and must never be silently compared or merged across unrelated providers.
  - External momentum indicators (RSI, MACD, Stochastic, ADX, Rate of Change, or similar) are **excluded** from the core project as mandatory POI rules. They may only be explored later as optional research features, adoptable solely if they show measurable improvement on locked unseen data and receive author approval.
  - Future data fields are named but not yet weighted or thresholded: `relative_size_ratio`, `range_context_ratio`, `body_efficiency`, `directional_close_position`, `relative_tick_volume`, `tick_volume_status`, `price_activity_score` (the `price_activity_score` formula and feature weights remain unresolved and are not invented by this decision).
  - Full formulas, field-separation rules, tick-volume policy, and indicator exclusions are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md), "Volume, Momentum, and Price-Activity Proxy Standard."
  - Applies to: Buy/Sell Order Block, Buy/Sell Fair Value Gap, Base Rally, Base Drop, Buy-to-Sell Candle, Sell-to-Buy Candle, Bullish Engulfing, Bearish Engulfing (10 rule files referenced). **Does not** apply to Pressure Wick yet — Pressure Wick proportions remain under Ambiguity 6, unresolved.
- **Still open (explicitly not resolved by this decision):** minimum Body Efficiency; minimum Bullish/Bearish Close Position; minimum Relative Tick Volume; minimum displacement distance; the final momentum-quality/`price_activity_score` formula and feature weights; and any hard pass/fail threshold. These remain subject to future author decisions, annotation evidence, and validation testing.
- **Status:** Resolved — Volume and Momentum Proxy Standard Version 1 approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule.

### 4. "Close together" / "Horizontal base" (Base Rally / Base Drop) — ✅ RESOLVED (PROVISIONAL)

- **Book says:** Base candles must be "positioned close to one another," "relatively uniform in size," "overlapping or closely connected," within "a compact horizontal price range."
- **Why it couldn't be coded precisely before:** No maximum spread between base-candle highs/lows was given, and no minimum/maximum candle count for a "compact" base was specified (only "two or more candles").
- **Possible numerical measurements that were considered:** (a) max range of (Base High − Base Low) as a fraction of the departure candle's size; (b) max range as a multiple of ATR; (c) a maximum candle count (e.g., 2–6 candles) before a base is considered too extended to qualify.
- **Decision (Base Formation Standard Version 1 — Provisional, approved by the author):**
  - Candle count: minimum 2, maximum 6 consecutive confirmed closed candles. More than 6 is initially classified as consolidation, not a precise Base Rally/Drop POI.
  - Base-candle size: every base candle's Total Range ≤ 0.50× the departure candle's Total Range (standard) / ≤ 0.3333× (Strong Base), compared against the largest Total Range among all base candles — consistent with Candle Measurement Standard V1 and Small Candle Standard V1.
  - Base Height (`Highest High − Lowest Low` of all base candles) must satisfy both ≤ 0.75× ATR(14) (same symbol/timeframe as the candidate base) **and** ≤ 0.60× the departure candle's Total Range.
  - Horizontal compactness: Base Midpoint Drift (`|Last Base Candle Midpoint − First Base Candle Midpoint|`, where Midpoint = (High+Low)/2) ≤ 0.25× Base Height — this is what rejects a small directional staircase.
  - Overlap: for each consecutive base-candle pair, Overlap Ratio (`Overlap Range ÷ Previous Candle Range`) ≥ 0.50.
  - Departure candle: ≥ 2× the largest base candle (≥ 3× for stronger classification), must close outside the complete base range, must move in the expected direction, and is evaluated using the approved Volume, Momentum, and Price-Activity Proxy Standard. Base Rally requires Departure Close > base's Highest High; Base Drop requires Departure Close < base's Lowest Low.
  - Classification: COMPACT BASE (passes all standard conditions), STRONG BASE (all base candles ≤ 0.3333× departure range, departure ≥ 3× largest base candle, all other conditions pass), INVALID BASE (any mandatory condition fails).
  - **This standard is explicitly labeled "Base Formation Standard Version 1 — Provisional"** — it still requires future calibration against expert-approved/expert-rejected examples across XAUUSD/EURUSD/GBPUSD, H3/H4/D1/W1, and different volatility regimes. The thresholds above are not to be changed casually; they await that calibration pass.
  - **Scope limitation:** applies only to Base Rally/Rally-Base-Rally and Base Drop/Drop-Base-Drop. It is not automatically extended to unrelated consolidation, accumulation, distribution, support, resistance, or other POIs.
  - Full formulas and classification rules are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md), "Base Formation, Compactness, and Departure Standard."
- **Status:** Resolved (provisional) — Base Formation Standard Version 1 — Provisional approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule. Remains subject to future calibration; not yet a final, locked standard.

### 5. "Equal highs" / "Equal lows" (equality tolerance) — ✅ RESOLVED (PROVISIONAL)

- **Book says:** "Equal highs are price levels where the market has reached the same high area more than once" (similarly for equal lows) — "same area," not "identical price."
- **Why it couldn't be coded precisely before:** Real price data almost never touches the exact same price twice; some tolerance band was implied ("area") but never quantified.
- **Possible numerical measurements that were considered:** (a) fixed pip/point tolerance per symbol (e.g., 3–5 pips on EURUSD/GBPUSD, a larger $ tolerance on XAUUSD); (b) tolerance as a percentage of ATR; (c) tolerance as a percentage of the swing range being compared.
- **Decision (Equal Highs and Equal Lows Standard Version 1 — Provisional, approved by the author):**
  - Requires at least 2 confirmed swing points (confirmed swing-high wick prices for Equal Highs, confirmed swing-low wick prices for Equal Lows). Swing points must come from an expert-labelled, manually confirmed, or otherwise explicitly approved confirmed-swing source — **not** an invented swing-detection algorithm (the automatic swing-detection method itself remains Ambiguity 10, unresolved).
  - All qualifying swing points in one cluster must come from the same timeframe; swing prices must never be combined across timeframes.
  - Reference ATR = median ATR(14) across all qualifying swing-touch candles (same symbol/timeframe, confirmed candles only).
  - Equality Tolerance = `MAX(2 × minimum price tick for the instrument, 0.10 × Reference ATR)` — no fixed pip/point tolerance by symbol; the minimum-tick floor is sourced from instrument metadata once the software layer exists.
  - Equal Highs Cluster Spread = highest qualifying swing-high wick price − lowest qualifying swing-high wick price; qualifies when ≤ Equality Tolerance. Equal Lows Cluster Spread mirrors this for swing-low wick prices.
  - Strength classification: STRONG (Cluster Spread ≤ 0.05× Reference ATR), STANDARD (> 0.05× and ≤ 0.10× Reference ATR), NOT EQUAL (> Equality Tolerance) — no additional tiers.
  - Drawing boundaries: Equal Highs Zone Bottom/Top = lowest/highest qualifying swing-high wick price, liquidity expected above Zone Top, optional Reference Level = median of qualifying swing-high wick prices (does not replace the zone boundaries). Equal Lows mirrors this below Zone Bottom.
  - Confirmation: CONFIRMED only when ≥2 qualifying swing points exist, all from the same timeframe, the latest swing point is itself confirmed, and the cluster spread is within tolerance; before the latest swing confirms, the pattern is only FORMING. SWEPT and BROKEN states are reserved for later but not defined now.
  - Full formulas, drawing rules, and state limitations are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md), "Equal Highs and Equal Lows Tolerance and Drawing Standard."
  - **This standard is explicitly labeled "Equal Highs and Equal Lows Standard Version 1 — Provisional"** — it requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different volatility regimes, and different market sessions. Thresholds are not to be changed casually outside that calibration process.
  - **Scope limitation:** applies only to Equal Highs and Equal Lows. Not automatically extended to Support, Resistance, Trendlines, Swing Highs/Lows, Previous-period highs/lows, Order Blocks, Fair Value Gaps, or other POIs.
- **Still open (explicitly not resolved by this decision):** the automatic swing-detection algorithm (Ambiguity 10, unchanged); SWEPT and BROKEN state rules; reclaim; invalidation; expiration; freshness; mitigation — none of these are defined for Equal Highs/Lows by this decision.
- **Status:** Resolved (provisional) — Equal Highs and Equal Lows Standard Version 1 — Provisional approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule. Remains subject to future calibration; not yet a final, locked standard.

### 6. "Good candle proportion" (Pressure Wick / Liquidity Wick) — ✅ RESOLVED (PROVISIONAL)

- **Book says:** A pressure/liquidity wick "closes with a candle body that still has a good proportion... it also maintains a meaningful body, showing that there was real pressure," distinguishing it from a candle that is "only" a long wick with a negligible body.
- **Why it couldn't be coded precisely before:** No wick-to-body ratio, or body-to-range percentage, was given to separate a qualifying "pressure wick" from a plain long-wicked doji.
- **Possible numerical measurements that were considered:** (a) minimum body size as % of total candle range (e.g., body ≥ 20–30% of range); (b) maximum wick-to-body ratio (e.g., wick ≤ 3–4× body); (c) a combined rule requiring both a minimum wick length (vs. ATR) and a minimum body %.
- **Decision (Pressure Wick Standard Version 1 — Provisional, approved by the author):**
  - Uses only confirmed closed candles. Total Range = High − Low; Body = |Close − Open|; Upper Wick = High − MAX(Open, Close); Lower Wick = MIN(Open, Close) − Low. A candle with Total Range ≤ 0 is invalid. Body Efficiency = Body ÷ Total Range; Upper/Lower Wick Share = Upper/Lower Wick ÷ Total Range.
  - **Bullish Pressure Wick** (lower-price rejection) requires all of: Lower Wick Share ≥ 0.40; Body Efficiency ≥ 0.25; Lower Wick ≥ 2× Upper Wick; Bullish Close Position `(Close − Low) ÷ Total Range` ≥ 0.60. Candle colour alone does not determine direction.
  - **Bearish Pressure Wick** (higher-price rejection) requires all of: Upper Wick Share ≥ 0.40; Body Efficiency ≥ 0.25; Upper Wick ≥ 2× Lower Wick; Bearish Close Position `(High − Close) ÷ Total Range` ≥ 0.60. Candle colour alone does not determine direction.
  - **STRONG** classification requires all of: Rejection Wick Share ≥ 0.50; Body Efficiency ≥ 0.30; Rejection Wick ≥ 3× Opposite Wick; Directional Close Position ≥ 0.70; Range Context Ratio (candidate Total Range ÷ median Total Range of the previous 20 confirmed candles, current candle excluded) ≥ 1.25. A candidate meeting the standard conditions but not every STRONG condition is **STANDARD**. No additional tiers.
  - **Wick Dominance Ratio** = Rejection Wick ÷ MAX(Opposite Wick, Minimum Price Tick) — division-by-zero protection; the Minimum Price Tick is sourced from instrument metadata once the software layer exists (not invented as a fixed pip/point value here).
  - **Drawing boundaries:** Bullish Pressure Wick zone = Candle Low to MIN(Open, Close) (lower rejection wick only); Bearish Pressure Wick zone = MAX(Open, Close) to Candle High (upper rejection wick only). The candle body is never automatically included in the zone.
  - **States:** only CANDIDATE (before the candle closes) and CONFIRMED (after close, all mandatory conditions pass) are defined. RETESTED, MITIGATED, SWEPT, BROKEN, EXPIRED are not defined — they depend on later freshness/mitigation/liquidity/sweep/invalidation/expiration standards.
  - **Volume/momentum:** references the approved Volume, Momentum, and Price-Activity Proxy Standard — price/candle behaviour is primary evidence, tick volume is secondary and never mandatory, missing tick volume never invalidates a Pressure Wick, and external indicators (RSI/MACD/Stochastic/ADX/RoC) are not mandatory. No final `price_activity_score` formula or new indicator threshold is invented.
  - **Timeframe:** H3/H4/D1/W1 receive higher-timeframe contextual priority only (not a numerical score); a candle failing the mandatory measurements stays invalid regardless of timeframe.
  - **Relationship with Hammer/Shooting Star:** Pressure Wicks remain Volume-Based POIs; Hammer/Shooting Star remain Price-Action POIs. One candle may independently qualify for both labels, which must be preserved separately, never silently merged. The Hammer and Shooting Star rule files were **not** modified by this decision.
  - Full formulas, states, and classification rules are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md), "Pressure Wick Measurement, Drawing, and Classification Standard."
  - **This standard is explicitly labeled "Pressure Wick Standard Version 1 — Provisional"** — it requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different sessions, and different volatility regimes. Thresholds are not to be changed casually outside that calibration process.
  - **Scope limitation:** applies only to Bullish Pressure Wick and Bearish Pressure Wick. Not automatically extended to Hammer, Shooting Star, pin bars generally, Order Blocks, Fair Value Gaps, Engulfing candles, Base Rally, Base Drop, or other POIs.
- **Still open (explicitly not resolved by this decision):** proof of liquidity collection; required preceding approach speed; nearby support/resistance/trendline/structural-zone requirement; retest confirmation; freshness; partial/full mitigation; sweep rules; general invalidation; expiration; trade-entry confirmation. None of these are defined for Pressure Wick by this decision.
- **Status:** Resolved (provisional) — Pressure Wick Standard Version 1 — Provisional approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule. Remains subject to future calibration; not yet a final, locked standard.

### 7. "Fast movement" / "Speed" (BTMM pillar; also Fair Value Gap creation) — ✅ RESOLVED (PROVISIONAL)

- **Book says:** FVGs form when "the market moves very fast in one direction"; BTMM's "Speed" pillar is "how fast price moves into the POI after manipulation."
- **Why it couldn't be coded precisely before:** No candles-per-unit-time, no minimum pip-per-candle rate, and no reference baseline ("fast" compared to what average) was specified.
- **Possible numerical measurements that were considered:** (a) number of candles taken to reach the POI vs. a baseline average approach speed; (b) price distance covered per candle vs. ATR; (c) a maximum elapsed time (minutes/candles) from manipulation phase to POI reaction.
- **Decision (Market Speed and Displacement Standard Version 1 — Provisional, approved by the author):**
  - Preserves four separate concepts, never combined into one unexplained score: FVG Displacement Speed, BTMM Approach Speed, BTMM Reaction Speed, POI Dwell Time.
  - **Single-candle speed:** Range Speed Ratio = candidate Total Range ÷ median Total Range of the previous 20 confirmed candles (candidate excluded). NORMAL (<1.50), FAST (≥1.50 and <2.00), VERY FAST (≥2.00).
  - **FVG comparison window:** Pre-Displacement Maximum Range = largest Total Range among the 3 confirmed candles immediately before the displacement candle. Displacement Expansion Ratio = displacement candle Total Range ÷ Pre-Displacement Maximum Range. This speed rule does not replace the strict three-candle FVG gap geometry, which remains independently mandatory.
  - **STANDARD FAST FVG** requires all of: Range Speed Ratio ≥1.50; Displacement Expansion Ratio ≥2.00; Body Efficiency ≥0.60; Directional Close Position ≥0.70 (Buy FVG: `(Close−Low)÷Total Range`; Sell FVG: `(High−Close)÷Total Range`); a valid strict three-candle FVG gap independently exists.
  - **STRONG FAST FVG** requires all of: Range Speed Ratio ≥2.00; Displacement Expansion Ratio ≥3.00; Body Efficiency ≥0.70; Directional Close Position ≥0.80; a valid strict three-candle FVG gap independently exists. A fast candle without valid FVG geometry is not an FVG. A valid geometric FVG that fails the speed thresholds may remain a weaker FVG candidate — it must not be silently deleted for failing speed classification alone. No additional speed tiers.
  - **BTMM movement-leg formulas** (using expert-labelled anchors only, until Ambiguity 14 is resolved): Leg Bar Count, Net Directional Distance = |End Price − Start Price|, Reference ATR = median ATR(14) across the leg's candles, Normalized Speed Per Bar = Net Directional Distance ÷ (Leg Bar Count × Reference ATR), Leg Path Distance = sum of Total Ranges of every candle in the leg, Directional Efficiency = Net Directional Distance ÷ Leg Path Distance, Directional Candle Share = candles closing in the movement direction ÷ total candles in the leg. Zero-denominator protection: a leg with zero candles, zero Reference ATR, or zero Leg Path Distance cannot receive a valid speed classification.
  - **BTMM speed classification:** FAST requires Normalized Speed Per Bar ≥0.50, Directional Efficiency ≥0.60, Directional Candle Share ≥0.67 (all three). STRONG FAST requires ≥0.75, ≥0.75, ≥0.80 (all three). Otherwise SLOW_OR_UNCLEAR. Speed classification alone must never approve or reject a POI, a BTMM formation, an entry, or a trade.
  - **POI Dwell:** POI Dwell Bars = consecutive confirmed candles intersecting the POI from first touch until price exits the zone. First Touch Time, Exit Time, Dwell Duration, Exit Direction, and POI Dwell Bars are preserved as separate fields. No maximum permitted dwell time is set. A delayed reaction inside a POI must not automatically invalidate BTMM.
  - **Future fields** (named only, not computed/weighted here): `range_speed_ratio`, `displacement_expansion_ratio`, `normalized_speed_per_bar`, `directional_efficiency`, `directional_candle_share`, `poi_dwell_bars`, `speed_classification`. No composite market-speed score or weighting formula is defined.
  - **Anchor limitation:** automatic detection of the manipulation endpoint, approach starting price, POI first-touch price, reaction starting point, and reaction endpoint all remain unresolved, dependent on Ambiguity 14 (the BTMM state machine, itself unchanged and not resolved by this decision). Until then, movement-leg speed testing uses expert-labelled or otherwise explicitly approved anchors only.
  - Full formulas and classification rules are documented in [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md), "Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard."
  - **This standard is explicitly labeled "Market Speed and Displacement Standard Version 1 — Provisional"** — it requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, M1/M5/M15 BTMM formations, H1/M15 market structure, H3/H4/D1/W1 POIs, different sessions, and different volatility regimes. Thresholds are not to be changed casually outside that calibration process.
  - **Scope limitation:** the FVG displacement thresholds apply only to Buy Fair Value Gap and Sell Fair Value Gap. The BTMM movement-leg formulas apply only to explicitly labelled BTMM Approach Legs and BTMM Reaction Legs. Not automatically extended to Order Blocks, Base Rally, Base Drop, Engulfing candles, Pressure Wicks, Trendlines, Support/Resistance, or other POIs.
- **Still open (explicitly not resolved by this decision):** Ambiguity 14 (BTMM state machine) and the automatic anchors that depend on it; any composite/weighted `price_activity`- or `speed`-style final score; BTMM Accuracy (Ambiguity 8, separate).
- **Status:** Resolved (provisional) — Market Speed and Displacement Standard Version 1 — Provisional approved. See [MEASUREMENT_STANDARDS.md](MEASUREMENT_STANDARDS.md) for the implementation-ready rule. Remains subject to future calibration; not yet a final, locked standard.

### 8. "Accurate targeting" / "Accuracy" (BTMM pillar)

- **Book says:** "Accuracy refers to how precisely that candle reaches or targets the Point of Interest."
- **Why it can't be coded precisely yet:** No maximum distance/overshoot from the drawn POI boundary is given for a reaction to still count as "accurate."
- **Possible numerical measurements to consider:** (a) maximum overshoot beyond the POI zone as a % of the zone's height; (b) maximum overshoot in pips/points/ATR; (c) requiring the reaction candle's wick (not necessarily the close) to be the only part crossing the boundary.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 9. "Strong reaction" (Previous/Current Period High-Low levels, Support/Resistance, generic POI language)

- **Book says:** Phrases like "a reaction from this level can be very powerful" or "the market may sweep the liquidity ... before reversing" recur without a minimum-move definition of what counts as a qualifying reaction versus noise.
- **Why it can't be coded precisely yet:** No minimum retracement size, candle count, or close-based confirmation is specified for when a "reaction" is real rather than incidental chop.
- **Possible numerical measurements to consider:** (a) minimum retracement as % of the preceding move; (b) minimum number of consecutive candles confirming the new direction; (c) a minimum ATR-multiple move away from the level.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 10. "Meaningful swing" (Trendline connection points, Swing Highs/Lows)

- **Book says:** The best trendlines are "connected to meaningful swing points where price has reacted clearly"; swing highs/lows are described only as "a previous market high/low where price rejected," with no formal detection rule.
- **Why it can't be coded precisely yet:** There is no stated fractal window (e.g., "N candles on each side"), nor a minimum retracement percentage that defines a valid swing point — a scanner needs one or the other to programmatically place swings.
- **Possible numerical measurements to consider:** (a) N-candle fractal (e.g., a high with 2–5 lower highs on each side); (b) ZigZag-style minimum retracement % or ATR-multiple; (c) a hybrid: fractal detection filtered by a minimum retracement.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 11. "Trendline too steep"

- **Book says:** "A good trendline POI should not be too steep, because very steep trendlines are often weak, unstable, and easy to break," with no numeric angle, slope, or bars-per-price-unit definition given.
- **Why it can't be coded precisely yet:** "Steepness" on a price chart is not scale-invariant (it depends on the chart's price-per-pixel and time-per-pixel settings), so a raw visual "angle" cannot be transferred directly into a data-driven rule without first defining a normalized slope measure.
- **Possible numerical measurements to consider:** (a) slope normalized as price-move-per-candle relative to ATR; (b) a maximum ratio of (price change) to (number of candles) over the trendline's touches; (c) rejecting trendlines whose average candle-to-candle slope exceeds a multiple of the symbol's typical daily range.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 12. Support/Resistance level tolerance and minimum touch count

- **Book says:** Support/resistance are levels "where price has shown meaningful reaction before" with no explicit minimum number of touches (contrast with the trendline rule, which explicitly requires "at least two touches").
- **Why it can't be coded precisely yet:** Without a touch-count and a price tolerance band, a scanner cannot distinguish a "level" from any random price point that was touched once.
- **Possible numerical measurements to consider:** (a) require ≥2 touches within a tolerance band (mirroring the trendline rule); (b) tolerance band sized as a % of ATR or a fixed pip value per symbol; (c) a decay rule where older touches count less than recent ones.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 13. "Clear reversal" distance (Buy-to-Sell / Sell-to-Buy candle validation)

- **Book says:** After the failed strong candle, "price must begin to move downward [or upward]," and the market "should demonstrate that sellers [or buyers] have taken control" — with no minimum distance or number of confirming candles specified.
- **Why it can't be coded precisely yet:** Any single opposite-colored candle could technically satisfy "begin to move" without representing a genuine reversal; the book gives no minimum move size or close-through condition.
- **Possible numerical measurements to consider:** (a) minimum reversal size as % of the failed candle's range; (b) minimum number of consecutive opposite-direction candles/closes; (c) require price to close beyond the failed candle's open.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 14. BTMM setup state machine ("forming" / "confirmed" / "cancelled")

- **Book says:** The book describes the *ingredients* of a BTMM setup (liquidity creation before/within/after the POI; volume, speed, accuracy pillars; the single explicit negative rule "if none of these liquidity creation conditions is present, then the trade should not be taken") but never lays out formal state-transition rules or a checklist labeled "forming/confirmed/cancelled."
- **Why it can't be coded precisely yet:** A scanner needs discrete states to raise/clear a signal; the book only supplies narrative/qualitative guidance, not a decision table.
- **Possible numerical measurements to consider:** (a) treat "forming" = price inside/approaching a valid POI with at least one liquidity-creation behavior underway; "confirmed" = all three pillars (volume/speed/accuracy) pass their (author-defined) thresholds plus trend/session agreement; "cancelled" = a structural break beyond a defined invalidation distance, or a maximum time-in-zone exceeded without confirmation; (b) alternative: confirmation requires only 2 of 3 pillars; (c) alternative: use a scoring system (0–100) rather than a hard state machine.
- **Threshold chosen:** None.
- **Status:** Requires author approval — this is the single highest-priority item for a working scanner, since every other ambiguity feeds into it.

### 15. Concepts named in the task brief but entirely absent from the book

- **Book says:** Nothing — "reclaim," "displacement after reclaim," "repeated taps," and "false invalidation / genuine invalidation" do not appear anywhere in the full-text extraction (confirmed by direct text search).
- **Why it can't be coded precisely yet:** There is no book-sourced definition at all to make precise — these would have to be authored from scratch or imported from outside the book, which Phase 0A explicitly forbids.
- **Possible numerical measurements to consider:** N/A until the author defines these concepts, if they are wanted at all in this project's vocabulary.
- **Threshold chosen:** None.
- **Status:** Requires author decision on whether these concepts should be added to the book's vocabulary at all, and if so, their definitions.

---

## How to resolve these

For each item, the author should supply a concrete number (or explicit acceptance of one of the "possible measurements" options). Once resolved, update the corresponding entry in `knowledge/POI_MASTER_CATALOG.md` or `knowledge/btmm/BTMM_MASTER_SUMMARY.md`, then remove (or mark resolved in) this file.
