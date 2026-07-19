# Swing Low

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bullish (a prior low where price rejected upward; liquidity clusters below).

## Source pages

"4. Swing highs - Swing lows" (paragraphs 618-626).

## Book definition

A previous market low where price rejected and moved upward; liquidity accumulates below from stop-losses, pending orders, and breakout entries.

## Required market location

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10): a five-candle local window (2 confirmed candles before, the candidate candle/plateau, 2 confirmed candles after). See knowledge/MEASUREMENT_STANDARDS.md, "Meaningful Swing High and Swing Low Detection Standard" (provisional, pending calibration).

## Formation conditions

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: a candle or plateau qualifies as a **local Swing Low candidate** when its wick low is the lowest qualifying extreme within the five-candle window after applying Pivot Tie Tolerance = MAX(2x Minimum Price Tick, 0.02x ATR(14)) (same symbol/provider/timeframe). The candidate is not even LOCAL_SWING_CANDIDATE until the two right-side candles close (for a plateau, the countdown starts after the final plateau candle).

## Confirmation conditions

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: two-stage confirmation. (1) LOCAL_SWING_CANDIDATE after the two right-side candles close - not yet a meaningful structural swing, and unavailable to Equal Lows, Trendlines, Support, Resistance, or other market-structure logic. (2) CONFIRMED_MEANINGFUL_SWING_LOW once price rises from the Pivot Price by at least the Meaningful Reversal Threshold = MAX(2x Minimum Price Tick, 0.50x Pivot Reference ATR) - i.e. Swing Low Reversal Excursion (subsequent Highest High - Pivot Price) >= Meaningful Reversal Threshold. The first candle achieving this is stored as meaningful_confirmation_time. Before meaningful confirmation, a lower low replaces (SUPERSEDES) the prior unconfirmed candidate, with superseded_by_swing_id preserved (never deleted from historical/audit data).

**Non-repainting treatment:** once meaningfully confirmed, Pivot Price/Start Time/End Time never move, and the confirmed swing is never deleted because a later candle creates a more extreme price (that later price becomes a new candidate/structure/sweep/break event instead). The confirmed swing is available to downstream logic and historical backtests only from meaningful_confirmation_time onward, not from the original pivot time - this is explicitly required to prevent look-ahead bias.

## Origin candle or level

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: the pivot candle, or for an adjacent plateau (candles whose wick lows are within Pivot Tie Tolerance of each other), the full plateau - Pivot Price = lowest Low among all plateau candles, with Plateau Start Time and Plateau End Time preserved. Adjacent plateau candles are never counted as separate Equal Low swing events.

## Upper boundary

Not applicable in the same sense - a Swing Low is a single price level (Pivot Price), not a zone. A separate value, the post-pivot Highest High, is tracked only for reversal-excursion confirmation (see Confirmation conditions), not as an upper zone boundary.

## Lower boundary

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: Pivot Price = the wick low of the pivot candle (or the lowest Low among plateau candles). This is a single price level, not a two-sided zone.

## Wick treatment

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: the qualifying Swing Low price is explicitly the candle's **wick low** - never the close, body low, or candle colour.

## Body treatment

Not applicable - this POI's qualifying price is wick-based only (see Wick treatment); the book gives no separate body rule for Swing Lows.

## Candle-size requirement

Not applicable / not defined.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

Central to market-structure mapping generally, but this POI's own detection rule is undefined.

## Market-structure requirement

Same as Trend requirement.

## Liquidity requirement

Liquidity assumed below the swing low - stated narratively.

## Timeframe requirement

Not explicitly ranked for this POI.

## Strength classification

Resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional: **STANDARD_SWING** at reversal excursion >= 0.50x Pivot Reference ATR (the confirmation threshold itself); optional upgrade to **STRONG_SWING** at >= 1.00x Pivot Reference ATR, achieved "before the Pivot Price is materially breached" (strength_confirmation_time recorded). **The exact numerical meaning of "materially breached" remains unresolved** - no breach tolerance, breach-close rule, wick-breach rule, or invalidation threshold is defined, so the STRONG_SWING upgrade is only partially automatable pending that future decision. No additional strength tiers are defined. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Equal Lows and to the Previous/Current Period High-Low family.

## Positive example

Yes (paragraphs 623-626). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - local pivot detection (five-candle window, wick-low comparison, Pivot Tie Tolerance), plateau handling, meaningful-reversal confirmation, non-repainting availability timing, and STANDARD_SWING classification are now all testable under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional. Not testable: STRONG_SWING's material-breach condition (undefined); HH/HL/LH/LL, Break of Structure, Change of Character, sweep/liquidity-grab rules (none defined, and explicitly out of scope for this standard); all lifecycle behavior (freshness, mitigation, invalidation, expiration).

## Unresolved questions

The exact numerical meaning of "materially breached" for STRONG_SWING (blocks full automation of that upgrade); Higher High/Higher Low/Lower High/Lower Low labels; Break of Structure/Change of Character; sweep/liquidity-grab rules; Trendline/Support/Resistance validity (Ambiguities 11-12, unchanged); BTMM state-machine transitions (Ambiguity 14, unchanged); no freshness/mitigation/invalidation/expiration rule. Meaningful Swing Detection Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, M1/M5/M15/H1/H3/H4/D1/W1, sessions, and volatility regimes before it can be considered final.

## Author decision

Local pivot detection (five-candle window, wick-low rule, Pivot Tie Tolerance), plateau handling, meaningful-reversal confirmation (Meaningful Reversal Threshold, Reversal Excursion), candidate-replacement/SUPERSEDED handling, non-repainting availability timing, and STANDARD_SWING classification are approved (provisionally) - see Meaningful Swing High and Swing Low Detection Standard V1 — Provisional. STRONG_SWING's material-breach condition, HH/HL/LH/LL, BOS/CHOCH, sweep rules, and all lifecycle rules remain pending.

## Approval status

PARTIAL
