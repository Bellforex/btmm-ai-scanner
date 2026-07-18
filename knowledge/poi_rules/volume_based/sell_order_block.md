# Sell Order Block

## Alternative book name

"Bearish Order Block" (informal narrative usage) alongside the formal term "Sell Order Block" used in the validation appendix. Same concept.

## Family

Volume-Based POI

## Direction

Bearish

## Source pages

Chapter 1, Volume-Based POI, "Order blocks (OB)" (paragraphs 199-237); formal appendix "Sell Order Block Validation Conditions" (paragraphs 872-908).

## Book definition

A two-candle pattern usually found at the end/origin of a prior bullish move, right before the market reverses downward: a smaller first candle followed by a larger bearish displacement candle showing a volume switch.

## Required market location

Must be located at the beginning/origin of a significant bearish price movement - not randomly in the middle of an existing move.

## Formation conditions

Two consecutive candles: a smaller first candle, then a larger bearish displacement candle with strong, aggressive downward momentum that initiates a significant move away from the first candle.

## Confirmation conditions

No separate confirmation step distinct from the formation/size rule itself is given.

## Origin candle or level

The smaller (first) of the two candles.

## Upper boundary

High of the smaller first candle.

## Lower boundary

Low of the smaller first candle.

## Wick treatment

Full high-to-low range of the smaller candle is used for the zone; wicks are included, per Candle Measurement Standard V1 SS5.

## Body treatment

Not required for zone-drawing; Body Efficiency may be tracked separately per Measurement Standard V1 SS4 but is not required for validity.

## Candle-size requirement

Size Ratio (Total Range basis) >= 2.0 for a standard pattern, >= 3.0 for a strong pattern vs. the smaller candle. Formula: Bearish Displacement Candle Size >= 2 x Previous Candle Size. Resolved under Candle Measurement Standard V1 (Ambiguity 1). The "smaller candle" itself is now also governed by Small Candle Standard V1 (Ambiguity 2, resolved): Small Candle Total Range <= 0.50x the displacement candle's Total Range (standard) / <= 0.3333x (strong volume-switch); a separate, secondary Recent Market Context classification (vs. the 20-candle median range) does not override this. Comparison target: the immediately preceding (smaller) candle. See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

General POI framework note only.

## Market-structure requirement

General framework note only; no Sell-Order-Block-specific structural precondition is stated.

## Liquidity requirement

Not defined as an Order-Block-specific rule.

## Timeframe requirement

Explicit strength ranking: Weekly > Daily > 4H > 1H > 15-minute Sell Order Block.

## Strength classification

Standard (2.0-<3.0) vs. Strong (>=3.0); Higher-timeframe vs. Lower-timeframe (lower TF may require additional confirmation).

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

NOT DEFINED IN BOOK.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Explicitly distinguished from Bearish Engulfing by location (origin of a move vs. within a move).

## Positive example

Yes - captioned chart examples (paragraphs 223-228, 939-941 region). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - geometry/size rule testable now; lifecycle behavior not testable (undefined).

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds (Body Efficiency, Close Position, Relative Tick Volume, displacement distance, final price_activity_score/weights) are not yet set; no freshness/mitigation/invalidation/expiration rule.

## Author decision

Pending.

## Approval status

PARTIAL
