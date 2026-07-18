# Buy Fair Value Gap

## Alternative book name

Front-matter abbreviation list defines "1. Bear Value Gap = BFVG," but this label is never reused anywhere in the body text - the body consistently says "Fair Value Gap"/"FVG" for both directions. Recorded as a naming inconsistency, not a second concept (see AMBIGUITIES/PROJECT_STATE contradiction note). Related abbreviations PCH (Previous/first Candle High) and NCL (Next/third Candle Low) are used in the gap-geometry description.

## Family

Volume-Based POI

## Direction

Bullish

## Source pages

Front matter abbreviations (paragraphs 52-58); Chapter 1, "2. Fair Value Gap" (paragraphs 238-287); formal appendix "Buy Fair Value Gap Validation Conditions" (paragraphs 688-704).

## Book definition

A three-candle price imbalance formed when the market displaces very fast upward, leaving an empty/inefficient zone between candle 1 and candle 3; price may later return to rebalance it.

## Required market location

Formed within a directional (non-choppy, non-sideways) price movement; the book does not require it to sit at the 'origin' or 'middle' of a move the way Order Block/Engulfing are distinguished.

## Formation conditions

Candles preceding the gap show clear directional movement and are noticeably smaller than the middle displacement candle; the middle candle shows strong, aggressive bullish displacement.

## Confirmation conditions

Gap geometry is itself the confirmation: low of the third candle must remain above the high of the first candle. The candle following the displacement candle may be of any size and does not invalidate the gap.

## Origin candle or level

The 3-candle sequence (PCH = first/previous candle high; NCL = third/next candle low).

## Upper boundary

Low of the third candle (book: 'Buy FVG Zone = First Candle High to Third Candle Low').

## Lower boundary

High of the first candle.

## Wick treatment

The boundary itself uses the first candle's high and the third candle's low directly - wick extremes define the gap edges, they are not excluded.

## Body treatment

Not defined as a separate requirement beyond the displacement candle needing 'strong and aggressive bullish displacement' (a momentum descriptor, not a body-ratio formula).

## Candle-size requirement

Preceding candles must be 'noticeably smaller' than the displacement candle. Ambiguity 2 is now resolved via Small Candle Standard V1: the displacement candle qualifies against the reference group when the reference's Total Range <= 0.50x the displacement candle's Total Range (standard) / <= 0.3333x (strong volume-switch), with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group. **Still open:** exactly how many preceding candles make up "the relevant preceding-candle group" is not defined by the book or by this decision - see knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard," Important Limitation.

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bullish Close Position of the displacement candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

General POI framework note only.

## Market-structure requirement

General framework note only.

## Liquidity requirement

Not defined as FVG-specific.

## Timeframe requirement

No FVG-specific timeframe ranking is stated (contrast with Order Block's explicit Weekly>Daily>4H>1H>15m list).

## Strength classification

"Scenario A" (small candles then a big displacement candle = best/strongest) vs. "Scenario B" (preceding candles similar size to the displacement candle = weaker) - described narratively, not numerically ranked.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

One narrow rule is given: the size of the candle following the displacement candle does 'not invalidate' the FVG. This is the only invalidation-adjacent statement in the book for this POI, and it only rules out one specific non-invalidating condition - it supplies no general invalidation rule.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Order Block (both rely on a displacement candle) but distinguished by the 3-candle gap-geometry requirement, which Order Block does not have.

## Positive example

Yes (paragraphs 247-252, 287, 726-730). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption (Scenario B is described in text only).

## Machine-testable criteria

Partial - the 3-candle gap geometry is precisely testable; the 'noticeably smaller' preceding-candle rule and the momentum descriptor are not yet.

## Unresolved questions

How many preceding candle(s) make up the comparison group (not resolved by Small Candle Standard V1); which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds are not yet set; no invalidation/freshness/expiration rule beyond the one narrow note above.

## Author decision

Pending.

## Approval status

PARTIAL
