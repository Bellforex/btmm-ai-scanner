# Sell-to-Buy Candle

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Volume-Based POI

## Direction

Bullish (produces a buy opportunity; begins life as a failed strong bearish/sell candle).

## Source pages

"3. Buy-to-sell zones/Sell-to-buy zones" (paragraphs 288-341); formal appendix "Sell-to-Buy Candle Validation Conditions" (paragraphs 1091-1124); drawing/strength rules (paragraphs 1125-1159).

## Book definition

A strong bearish candle within an existing downtrend that fails to produce further bearish continuation, followed by a bullish reversal - becomes a POI because price may revisit it before another strong buy move.

## Required market location

Must appear within an active, existing downward price movement (selling pressure already underway before the candle forms).

## Formation conditions

A strong bearish candle with clear, aggressive selling momentum forms, noticeably larger than the candles immediately preceding it.

## Confirmation conditions

After the candle, bearish continuation must fail, followed by a bullish reversal showing buyers have taken control from the candle's location.

## Origin candle or level

The single failed strong bearish candle itself.

## Upper boundary

High of the candle.

## Lower boundary

Low of the candle.

## Wick treatment

Full candle range used for the zone; wicks included, per Measurement Standard V1 SS5.

## Body treatment

Not separately specified; body relevant only to establishing the candle 'closed bearish' with strong momentum.

## Candle-size requirement

Size Ratio (Total Range) >= 2.0 (standard) / >= 3.0 (stronger), per Measurement Standard V1. Ambiguity 2 is now resolved via Small Candle Standard V1: the failed directional candle qualifies against the preceding group when the group's reference Total Range <= 0.50x (standard) / <= 0.3333x (strong) the failed candle's Total Range, with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group (this supersedes the earlier informal "average size of preceding candles" description). **Still open:** exactly how many preceding candles make up "the relevant preceding-candle group" is not defined. See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position of the failed bearish candle itself), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet, and this does not resolve reversal-confirmation distance (Ambiguity 13).

## Trend requirement

Must occur within an existing downtrend - stated explicitly.

## Market-structure requirement

Not defined beyond 'existing bearish price movement.'

## Liquidity requirement

Not defined as specific to this POI.

## Timeframe requirement

Explicit ranking: Weekly > Daily > 4H > 1H > 15-minute.

## Strength classification

Standard (>=2x) / Strong (>=3x) / Weak (disqualified as high-quality).

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined as a standing post-formation rule.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Order Block and Engulfing; distinguished by the fail-then-reverse requirement on the reference candle itself.

## Positive example

Yes (paragraphs 304-309, 341, 1161). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - ratio and fail-then-reverse logic testable in principle; minimum reversal distance undefined (Ambiguity 13).

## Unresolved questions

Minimum reversal distance/candle count (Ambiguity 13, still open); how many preceding candles make up the comparison group (not resolved by Small Candle Standard V1); which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds are not yet set; no invalidation/freshness/expiration rule.

## Author decision

Pending.

## Approval status

NEEDS AUTHOR DECISION
