# Buy-to-Sell Candle

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Volume-Based POI

## Direction

Bearish (produces a sell opportunity; begins life as a failed strong bullish/buy candle).

## Source pages

"3. Buy-to-sell zones/Sell-to-buy zones" (paragraphs 288-341); formal appendix "Buy-to-Sell Candle Validation Conditions" (paragraphs 1057-1090); drawing/strength rules (paragraphs 1125-1159).

## Book definition

A strong bullish candle within an existing uptrend that fails to produce further bullish continuation, followed by a bearish reversal - becomes a POI because price may revisit it before another strong sell move.

## Required market location

Must appear within an active, existing upward price movement (buying pressure already underway before the candle forms).

## Formation conditions

A strong bullish candle with clear, aggressive buying momentum forms, noticeably larger than the candles immediately preceding it.

## Confirmation conditions

After the candle, bullish continuation must fail (no sustained move higher), followed by a bearish reversal showing sellers have taken control from the candle's location.

## Origin candle or level

The single failed strong bullish candle itself.

## Upper boundary

High of the candle.

## Lower boundary

Low of the candle.

## Wick treatment

Full candle range (high-low) used for the zone; wicks included, per Measurement Standard V1 SS5.

## Body treatment

Not separately specified for zone-drawing; body relevant only to establishing the candle 'closed bullish' with strong momentum.

## Candle-size requirement

Size Ratio (Total Range) >= 2.0 (standard), >= 3.0 (stronger), per Measurement Standard V1. Ambiguity 2 is now resolved via Small Candle Standard V1: the failed directional candle qualifies against the preceding group when the group's reference Total Range <= 0.50x (standard) / <= 0.3333x (strong) the failed candle's Total Range, with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group (this supersedes the earlier informal "average size of preceding candles" description). **Still open:** exactly how many preceding candles make up "the relevant preceding-candle group" is not defined. See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard."

## Volume or momentum proxy

Same open question as Ambiguity 3.

## Trend requirement

Must occur within an existing uptrend - stated explicitly for this POI (stronger requirement than the general framework note given to most other POIs).

## Market-structure requirement

Not defined beyond 'existing bullish price movement.'

## Liquidity requirement

Not defined as specific to this POI; liquidity context comes from the BTMM layer.

## Timeframe requirement

Explicit ranking: Weekly > Daily > 4H > 1H > 15-minute.

## Strength classification

Standard (>=2x) / Strong (>=3x) / Weak ("only slightly larger... or the market hesitates without producing a clear reversal" - explicitly disqualified as high-quality).

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined as a standing post-formation rule; the 'weak pattern' description is a formation-time disqualifier, not an invalidation rule for an already-valid POI.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Order Block and Engulfing (all involve candle-size disparity) but distinguished by requiring the reference candle's OWN direction to fail and reverse, rather than a takeover by the following candle.

## Positive example

Yes (paragraphs 304-309, 341, 1161). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - ratio and fail-then-reverse logic are testable in principle, but the minimum 'clear reversal' distance is undefined (Ambiguity 13, open).

## Unresolved questions

Minimum reversal distance/candle count (Ambiguity 13, still open); how many preceding candles make up the comparison group (not resolved by Small Candle Standard V1); volume/momentum proxy (Ambiguity 3); no invalidation/freshness/expiration rule.

## Author decision

Pending.

## Approval status

NEEDS AUTHOR DECISION
