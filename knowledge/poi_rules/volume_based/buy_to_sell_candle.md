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

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional (Ambiguity 13): **Author-Approved, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated.** A Buy-to-Sell candidate must be a confirmed closed bullish candle (Close > Open) appearing within an existing upward-price context (the full quantitative definition of that context remains unresolved - not defined using HH, HL, BOS, CHoCH, a moving average, or any other invented structure rule). Bullish Close Position = (Close − Low) ÷ Total Range. `STANDARD_BUY_TO_SELL_CANDIDATE` requires Candidate Size Ratio >= 2.00, Body Efficiency >= 0.60, Bullish Close Position >= 0.70; `STRONG_BUY_TO_SELL_CANDIDATE` requires >= 3.00 / >= 0.70 / >= 0.80. A zero-range or invalid candle cannot qualify. See knowledge/MEASUREMENT_STANDARDS.md, "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard."

## Candidate-candle requirements

Bullish Close Position, Body Efficiency, and Candidate Size Ratio must all clear the STANDARD or STRONG tier thresholds above; a candidate failing them becomes `REJECTED_CANDIDATE_CANDLE` and cannot proceed to the reversal window.

## Preceding comparison group

Preceding Maximum Range = the largest Total Range among exactly the 3 confirmed candles immediately before the candidate candle; Candidate Size Ratio = Candidate Total Range ÷ Preceding Maximum Range, guarded against a missing/zero Preceding Maximum Range. This resolves the previously open question of how many preceding candles form "the relevant preceding-candle group" (fixed at 3, not changed by this decision).

## Confirmation conditions

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: within the 3-bar post-candidate reversal window, `STANDARD_PATTERN` requires at least one confirmed post-candidate close below Candidate Midpoint, Opposite Close Displacement Ratio >= 0.50, Directional Efficiency >= 0.50, Directional Candle Share >= 0.67, and no `REJECTED_DIRECTIONAL_CONTINUATION` event; `STRONG_PATTERN` additionally requires a Strong candidate candle, at least one confirmed post-candidate close below Candidate Low, Opposite Close Displacement Ratio >= 1.00, Directional Efficiency >= 0.60, and Reversal Speed Classification FAST or STRONG FAST. Overall pattern strength is limited by the weaker of the candidate-candle tier and the reversal tier. A candidate without at least Standard Reversal confirmation is rejected; a large candle alone is never a confirmed POI. The book's own "sellers have taken control" narrative is not itself formalized beyond this - it remains a qualitative description.

## Three-bar reversal window

Exactly 3 confirmed candles immediately after the candidate candle are evaluated (confirmation bar 1, 2, 3). Confirmation may occur on any of the three bars once all required conditions are first satisfied; the earliest such confirmed candle time is stored as `reversal_confirmation_time`. If bar 3 closes without Standard Reversal conditions met, classify `REJECTED_INSUFFICIENT_REVERSAL`. The window is not extended beyond three candles.

## Continuation rejection

Candidate Reference ATR = ATR(14) on the candidate candle (same symbol/provider/timeframe); Continuation Close Tolerance = MAX(2 × Minimum Price Tick, 0.10 × Candidate Reference ATR). Before reversal confirmation, `REJECTED_DIRECTIONAL_CONTINUATION` is recorded when any post-candidate confirmed close exceeds Candidate High by more than Continuation Close Tolerance. A wick beyond Candidate High is stored separately as `continuation_wick_excursion` and never alone triggers rejection - confirmed close continuation is the primary rejection evidence. Once rejected before confirmation, the candidate cannot later become confirmed from the same three-bar window.

## Opposite close displacement

Lowest Reversal Close = the lowest confirmed close observed so far in the reversal window; Opposite Close Displacement = Candidate Close − Lowest Reversal Close (never negative); Opposite Close Displacement Ratio = that displacement ÷ Candidate Total Range. Close displacement is the approved confirmation measurement; opposite-direction wick excursion may be stored separately if later required.

## Candidate midpoint

Candidate Midpoint = (Candidate High + Candidate Low) ÷ 2, used as the Standard Reversal close-through threshold.

## Directional efficiency

Calculated via the already-approved Market Speed and Displacement Standard V1 — Provisional over the opposite-direction (bearish) reversal leg from confirmation bar 1 through the current evaluated bar; preserved independently, never merged into a composite score.

## Directional candle share

Calculated via the same Market Speed and Displacement Standard fields, preserved independently alongside Directional Efficiency.

## Reversal speed

Reversal Speed Classification (NORMAL/FAST/VERY FAST equivalents per the Market Speed and Displacement Standard) is required at FAST or STRONG FAST for Strong Reversal confirmation only; not required for Standard Reversal. The approved Market Speed formulas/thresholds are unchanged by this decision.

## Origin candle or level

The single failed strong bullish candle itself (`failed_candle_id`). Non-repainting: candidate OHLC values never move once set.

## Upper boundary

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: Zone Top = Candidate Candle High, fixed after successful reversal confirmation - the complete failed-candle range, never refined, shrunk, averaged, or recentered.

## Lower boundary

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: Zone Bottom = Candidate Candle Low, fixed after successful reversal confirmation.

## Wick treatment

Full candle range (high-low) used for the zone; wicks included, per Measurement Standard V1 SS5.

## Body treatment

Not separately specified for zone-drawing; body relevant only to establishing the candle 'closed bullish' with strong momentum.

## Candle-size requirement

Size Ratio (Total Range) >= 2.0 (standard), >= 3.0 (stronger), per Measurement Standard V1. Ambiguity 2 is now resolved via Small Candle Standard V1: the failed directional candle qualifies against the preceding group when the group's reference Total Range <= 0.50x (standard) / <= 0.3333x (strong) the failed candle's Total Range, with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group (this supersedes the earlier informal "average size of preceding candles" description). The preceding-candle-group count is now resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional (Ambiguity 13): exactly 3 confirmed candles immediately before the candidate candle (Preceding Maximum Range). See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard" and "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bullish Close Position of the failed bullish candle itself), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these general proxy fields have been set yet. Reversal-confirmation distance is now resolved separately under Ambiguity 13 (see Formation/Confirmation conditions above).

## Trend requirement

Must occur within an existing uptrend - stated explicitly for this POI (stronger requirement than the general framework note given to most other POIs).

## Market-structure requirement

Not defined beyond 'existing bullish price movement.'

## Liquidity requirement

Not defined as specific to this POI; liquidity context comes from the BTMM layer.

## Timeframe requirement

Explicit ranking: Weekly > Daily > 4H > 1H > 15-minute.

## Strength classification

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: candidate-candle tier (Standard >=2x / Strong >=3x, per the book's original ratio language) is now combined with the reversal tier (Standard/Strong Reversal, per Confirmation conditions above) into an overall pattern strength: Standard candidate + Standard reversal = `STANDARD_PATTERN`; Standard candidate + Strong reversal = `STANDARD_PATTERN`; Strong candidate + Standard reversal = `STANDARD_PATTERN`; Strong candidate + Strong reversal = `STRONG_PATTERN`. Overall strength is limited by the weaker component. "Weak" ("only slightly larger... or the market hesitates without producing a clear reversal") remains explicitly disqualified as high-quality; a candidate without at least Standard Reversal confirmation is rejected.

## Non-repainting availability

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: a confirmed POI becomes available to downstream logic only at `reversal_confirmation_time`, never historically at the candidate candle's original time. Once confirmed, candidate OHLC, zone boundaries, and reversal confirmation time never move, and later price action never retrospectively alters the original pattern classification.

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

Partial - candidate-candle qualification, the 3-candle preceding comparison group, the 3-bar reversal confirmation window, directional-continuation rejection, opposite close displacement, and STANDARD/STRONG pattern-strength classification are now all testable under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional. Not testable: the full quantitative preceding upward-price context (formation precondition, still qualitative), freshness, partial/full mitigation, repeated-touch degradation, final invalidation, expiration, retest entry confirmation, BTMM state transitions (none defined).

## Unresolved questions

The full quantitative definition of the preceding upward-price context (formation precondition); which general proxy fields apply is resolved (Ambiguity 3), but their minimum thresholds are not yet set; freshness; partial/full mitigation; repeated-touch degradation; final invalidation; expiration; retest entry confirmation; BTMM state transitions (Ambiguity 14, unchanged); the terminology questions under Ambiguity 15 (unchanged).

## Author decision

**Evidence status: Author-Approved, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, NOT Production-Approved.** Candidate-candle qualification, the 3-candle preceding comparison group, the 3-bar reversal confirmation window, Continuation Close Tolerance and directional-continuation rejection, opposite close displacement, Candidate Midpoint, reversal-leg measurements (via the approved Market Speed and Displacement Standard), STANDARD/STRONG reversal, overall pattern-strength classification, complete candle-range zone boundaries, and non-repainting availability are approved (provisionally) - see Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional. The full quantitative preceding-context definition, freshness, mitigation, final invalidation, expiration, and retest entry confirmation remain pending.

## Approval status

PARTIAL
