# Buy Order Block

## Alternative book name

"Bullish Order Block" (used informally in narrative prose, e.g. paragraph 428) alongside the formal term "Buy Order Block" used in the validation appendix. Same concept, no contradiction.

## Family

Volume-Based POI

## Direction

Bullish

## Source pages

Chapter 1, Volume-Based POI, "Order blocks (OB)" (paragraphs 199-237); formal appendix "Buy Order Block Validation Conditions" (paragraphs 829-871).

## Book definition

A two-candle pattern usually found at the end/origin of a prior bearish move, right before the market reverses upward: a smaller first candle followed by a larger bullish displacement candle showing a volume switch.

## Required market location

Must be located at the beginning/origin of a significant bullish price movement - not randomly in the middle of an existing move.

## Formation conditions

Two consecutive candles: a smaller first candle, then a larger bullish displacement candle with strong, aggressive upward momentum that initiates a significant move away from the first candle.

## Confirmation conditions

No separate confirmation step distinct from the formation/size rule itself is given - validity rests on the two-candle size-and-location structure alone.

## Origin candle or level

The smaller (first) of the two candles.

## Upper boundary

High of the smaller first candle.

## Lower boundary

Low of the smaller first candle.

## Wick treatment

Full high-to-low range of the smaller candle is used for the zone; wicks are included, per Candle Measurement Standard V1 SS5 (knowledge/MEASUREMENT_STANDARDS.md).

## Body treatment

Not required for zone-drawing (the whole candle range is the zone). Body Efficiency may be tracked as a separate quality signal per Measurement Standard V1 SS4, but the book does not require it for Buy Order Block validity.

## Candle-size requirement

Size Ratio (Total Range basis) >= 2.0 vs. the smaller candle for a standard pattern, >= 3.0 for a strong pattern. Formula: Bullish Displacement Candle Size >= 2 x Previous Candle Size. Resolved under Candle Measurement Standard V1 (Ambiguity 1).

## Volume or momentum proxy

Not defined beyond the candle-size ratio itself (Ambiguity 3, open).

## Trend requirement

General POI framework note only: a POI must agree with the trend/consolidation framework in use (see 'Before You Use POIs, Know This').

## Market-structure requirement

General framework note only; no Buy-Order-Block-specific structural precondition is stated.

## Liquidity requirement

Not defined as an Order-Block-specific rule; liquidity context is applied afterward through the BTMM layer, not the POI definition itself.

## Timeframe requirement

No single mandated timeframe. Explicit strength ranking: Weekly > Daily > 4H > 1H > 15-minute Buy Order Block.

## Strength classification

Standard (Size Ratio 2.0-<3.0) vs. Strong (>=3.0); Higher-timeframe vs. Lower-timeframe (lower TF 'may require confirmation from a higher-timeframe POI, market structure, trend direction, liquidity behaviour, or displacement').

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

Explicitly distinguished from Bullish Engulfing: Engulfing is located within/in the middle of a move; Order Block is located at the origin of a move. Same two-candle shape, different location rule.

## Positive example

Yes - captioned chart examples follow the text (paragraphs 223-228, 939-941). Image content itself was not visually reviewed for this audit; only presence/captions were checked.

## Negative example

No image or example in the extracted text is captioned as a negative/invalid Buy Order Block counter-example.

## Machine-testable criteria

Partial - the two-candle size/location/geometry rule is fully testable now using Measurement Standard V1. Lifecycle behavior (freshness, mitigation, invalidation, expiration) is not testable because none of it is defined.

## Unresolved questions

How to define a separate volume/momentum proxy (Ambiguity 3); no freshness/mitigation/invalidation/expiration rule exists at all for this POI.

## Author decision

Pending - none of the unresolved questions above have been decided.

## Approval status

PARTIAL
