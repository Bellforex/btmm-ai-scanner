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

### 3. "High volume" / "Strong momentum" / "Clear displacement"

- **Book says:** These phrases recur constantly (e.g., "strong buying pressure," "clear directional price movement," "strong and aggressive bullish displacement") to describe the qualifying move for OB, FVG, engulfing, and buy-to-sell/sell-to-buy candles.
- **Why it can't be coded precisely yet:** The book has no real trade-volume data source in view (retail Forex feeds don't carry true exchange volume) — it is describing *price-action proxies* for volume/momentum (candle size, speed of movement) rather than an actual volume indicator. It never states which proxy (candle size ratio, ATR multiple, momentum oscillator, tick volume) should be used computationally, beyond the specific 2×/3× candle-size rules already captured per-POI in `POI_MASTER_CATALOG.md`.
- **Possible numerical measurements to consider:** (a) treat "volume switch" purely as the already-specified candle-size ratio (no separate volume proxy needed); (b) add tick-volume or broker volume as a secondary confirmation filter; (c) use a momentum indicator (e.g., rate-of-change) as a supplementary aggressiveness score.
- **Threshold chosen:** None.
- **Status:** Requires author approval (specifically: should the scanner rely solely on candle-size ratios already specified per POI, or add a separate volume/momentum proxy?).

### 4. "Close together" / "Horizontal base" (Base Rally / Base Drop)

- **Book says:** Base candles must be "positioned close to one another," "relatively uniform in size," "overlapping or closely connected," within "a compact horizontal price range."
- **Why it can't be coded precisely yet:** No maximum spread between base-candle highs/lows is given, and no minimum/maximum candle count for a "compact" base is specified (only "two or more candles").
- **Possible numerical measurements to consider:** (a) max range of (Base High − Base Low) as a fraction of the departure candle's size; (b) max range as a multiple of ATR; (c) a maximum candle count (e.g., 2–6 candles) before a base is considered too extended to qualify.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 5. "Equal highs" / "Equal lows" (equality tolerance)

- **Book says:** "Equal highs are price levels where the market has reached the same high area more than once" (similarly for equal lows) — "same area," not "identical price."
- **Why it can't be coded precisely yet:** Real price data almost never touches the exact same price twice; some tolerance band is implied ("area") but never quantified.
- **Possible numerical measurements to consider:** (a) fixed pip/point tolerance per symbol (e.g., 3–5 pips on EURUSD/GBPUSD, a larger $ tolerance on XAUUSD); (b) tolerance as a percentage of ATR; (c) tolerance as a percentage of the swing range being compared.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 6. "Good candle proportion" (Pressure Wick / Liquidity Wick)

- **Book says:** A pressure/liquidity wick "closes with a candle body that still has a good proportion... it also maintains a meaningful body, showing that there was real pressure," distinguishing it from a candle that is "only" a long wick with a negligible body.
- **Why it can't be coded precisely yet:** No wick-to-body ratio, or body-to-range percentage, is given to separate a qualifying "pressure wick" from a plain long-wicked doji.
- **Possible numerical measurements to consider:** (a) minimum body size as % of total candle range (e.g., body ≥ 20–30% of range); (b) maximum wick-to-body ratio (e.g., wick ≤ 3–4× body); (c) a combined rule requiring both a minimum wick length (vs. ATR) and a minimum body %.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

### 7. "Fast movement" / "Speed" (BTMM pillar; also Fair Value Gap creation)

- **Book says:** FVGs form when "the market moves very fast in one direction"; BTMM's "Speed" pillar is "how fast price moves into the POI after manipulation."
- **Why it can't be coded precisely yet:** No candles-per-unit-time, no minimum pip-per-candle rate, and no reference baseline ("fast" compared to what average) is specified.
- **Possible numerical measurements to consider:** (a) number of candles taken to reach the POI vs. a baseline average approach speed; (b) price distance covered per candle vs. ATR; (c) a maximum elapsed time (minutes/candles) from manipulation phase to POI reaction.
- **Threshold chosen:** None.
- **Status:** Requires author approval.

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
