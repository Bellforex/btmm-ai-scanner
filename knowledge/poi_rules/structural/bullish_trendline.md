# Bullish Trendline

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bullish (ascending; acts as a buying POI).

## Source pages

"Trendlines" (paragraphs 576-589).

## Book definition

A diagonal form of support where price has reacted at least twice; a bullish trendline can act as a buying POI.

## Required market location

Diagonal, connecting swing lows within an uptrend. Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional (Ambiguity 11): only CONFIRMED_MEANINGFUL_SWING_LOW events (per the Meaningful Swing Standard, Ambiguity 10) are eligible anchors - FORMING, LOCAL_SWING_CANDIDATE, and SUPERSEDED records cannot anchor a trendline. A plateau counts as one anchor. Both anchors must share the same symbol, data provider, and timeframe. See knowledge/MEASUREMENT_STANDARDS.md, "Bullish and Bearish Trendline Detection and Validation Standard" (provisional, pending calibration).

## Formation conditions

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: connects two distinct confirmed meaningful Swing Lows where Anchor 2 Price > Anchor 1 Price + Pivot Tie Tolerance (if within tolerance, the pair is a HORIZONTAL_CANDIDATE, not a trendline - reserved for a separate, not-yet-defined Support standard). Anchor 2 must occur at least 5 confirmed bars after Anchor 1. Raw Slope = (Anchor 2 Price - Anchor 1 Price) / (Anchor 2 Bar Index - Anchor 1 Bar Index) must be > 0. Every confirmed candle strictly between the two anchors must not close below the projected line by more than Trendline Pierce Tolerance (inter-anchor integrity; a wick-only crossing within tolerance does not reject the pair). An anchor pair passing all conditions (eligible anchors, shared symbol/provider/timeframe, directional price condition, >=5-bar spacing, correct slope sign, VALID_SLOPE classification per Strength classification, inter-anchor integrity) becomes DRAFT_TRENDLINE, available to downstream logic only from Anchor 2's meaningful_confirmation_time (prevents look-ahead bias).

## Confirmation conditions

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: a DRAFT_TRENDLINE becomes CONFIRMED_TRENDLINE when a third distinct confirmed meaningful Swing Low touches the projected line (Bullish Touch Difference = Third Swing Low Pivot Price - Projected Line Price at that bar; qualifying touch when ABS(difference) <= Trendline Touch Tolerance, or a controlled pierce when difference is between -Touch Tolerance and -Pierce Tolerance). A third swing outside Pierce Tolerance does not confirm the line, and is usable only from its own meaningful_confirmation_time. The book's own note still applies on top of this: the third or fourth touch can create a buy opportunity.

**Non-repainting behavior:** once created, anchor IDs/prices/times never move, Raw Slope is never silently recalculated, and a third or fourth touch never refits the original line (a new anchor pair creates a new trendline candidate instead). The system may preserve multiple trendline candidates on the same timeframe simultaneously - older candidates are never silently deleted or replaced by a newer anchor pair, and no "Best/Primary Trendline" or composite ranking score is created. Backtests access DRAFT_TRENDLINE only from candidate_available_time, CONFIRMED_TRENDLINE only from confirmation_time, and STRONG_TRENDLINE only from strong_confirmation_time - later-confirmed states are never exposed at earlier historical candles.

## Origin candle or level

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: the two (or more) connected confirmed meaningful Swing Low pivots (Anchor 1, Anchor 2, and any later qualifying touches) - not a single candle. Anchor Bar Index = the pivot candle index (or Plateau End Bar Index for a plateau anchor); the Anchor Price is the swing's approved Pivot Price.

## Upper boundary

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: the trendline itself is a diagonal level, not a zone - drawn via Line Price(t) = Anchor 1 Price + Raw Slope x (t - Anchor 1 Bar Index). Touch tolerance is now quantified (see Wick treatment).

## Lower boundary

Not applicable - a trendline is a single diagonal price level at each bar (Line Price(t) above), not a two-sided zone.

## Wick treatment

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: Trendline Touch Tolerance = MAX(2x Minimum Price Tick, 0.10x ATR(14)) and Trendline Pierce Tolerance = MAX(2x Minimum Price Tick, 0.20x ATR(14)), both using ATR(14)/tick from the confirmed interaction candle. These tolerances apply only to Trendlines, never replacing POI zone/Support/Resistance/Equal-Highs-Lows tolerances. A wick-only crossing within Pierce Tolerance does not reject an anchor pair or break the line (see Formation/Confirmation conditions).

## Body treatment

Not applicable - trendline interactions are evaluated via candle close (against the tolerance bands) plus wick-tolerance handling, not a body-size rule; the book gives no separate body rule for Trendlines.

## Candle-size requirement

Not applicable / not defined - trendlines are not candle-size-based POIs.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

By definition IS a trend-following tool; requires an underlying directional move to draw from.

## Market-structure requirement

Must connect to 'meaningful swing points where price has reacted clearly' - swing-point detection is now resolved (provisionally) via the Meaningful Swing High and Swing Low Detection Standard V1 (Ambiguity 10); only CONFIRMED_MEANINGFUL_SWING_LOW events qualify as anchors (see Required market location).

## Liquidity requirement

Liquidity is said to build around the trendline from other traders' orders/stops watching it, but no numeric rule is given.

## Timeframe requirement

Stronger on the 4-hour timeframe and above; timeframe choice should match trade type (scalp = lower TF, day/swing = stronger TF).

## Strength classification

Resolved under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional (Ambiguity 11): Normalized Slope = ABS(Raw Slope) / Anchor Reference ATR (Anchor Reference ATR = median ATR(14) across all confirmed candles from Anchor 1 through Anchor 2 inclusive). Classification: HORIZONTAL_CANDIDATE (Normalized Slope < 0.02), VALID_SLOPE (0.02-0.35 inclusive), TOO_STEEP (> 0.35) - a TOO_STEEP line cannot provide valid confirmation but may be preserved as a rejected research candidate. Separately, touch-count progression: 2 valid anchors = DRAFT_TRENDLINE; 3 qualifying confirmed meaningful swings = CONFIRMED_TRENDLINE; 4 or more = STRONG_TRENDLINE. The qualifying-touch count is structural evidence only - it does not define freshness, remaining strength, repeated-touch degradation, expiration, or entry validity. No additional tiers are defined. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. Resolved partially under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional: a TRENDLINE_BREAK_CANDIDATE is recorded when a confirmed candle closes below the projected line by more than Trendline Pierce Tolerance - but this is explicitly **not** final invalidation. Confirmed break, reclaim, retest, false break, sweep, and final invalidation remain unresolved and are not defined by this standard.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Explicitly stated by the book to be conceptually related to Support (a 'diagonal form of support').

## Positive example

Yes (paragraphs 581-585). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - anchor eligibility (via the Meaningful Swing Standard), minimum 5-bar spacing, the trendline equation, Normalized Slope/steepness classification, Touch/Pierce tolerances, inter-anchor integrity, DRAFT/CONFIRMED/STRONG progression, TRENDLINE_BREAK_CANDIDATE detection, and non-repainting availability are now all testable under Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional. Not testable: final invalidation, retest, reclaim, false break, sweep, expiration, repeated-touch degradation, entry confirmation (none defined); HH/HL/LH/LL, BOS, CHoCH (not defined, out of scope); the STRONG_SWING material-breach sub-rule from the underlying swing standard (Ambiguity 10, still open) also indirectly affects anchor strength context.

## Unresolved questions

Final trendline invalidation; required retest after a break; reclaim; false break; sweep; trendline expiration; maximum trendline age; repeated-touch degradation; entry confirmation; HH/HL/LH/LL; BOS/CHoCH; Support clustering (Ambiguity 12, unchanged); Resistance clustering (Ambiguity 12, unchanged); BTMM state transitions (Ambiguity 14, unchanged); the material-breach sub-rule for STRONG_SWING anchors (Ambiguity 10). Bullish and Bearish Trendline Detection and Validation Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility/trend regimes before it can be considered final.

## Author decision

Anchor eligibility, minimum bar spacing, trendline equation, Normalized Slope/steepness classification, Touch/Pierce tolerances, inter-anchor integrity, DRAFT/CONFIRMED/STRONG progression, TRENDLINE_BREAK_CANDIDATE detection, multiple-candidate preservation, and non-repainting behavior are approved (provisionally) - see Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional. Final invalidation, retest, reclaim, false break, sweep, expiration, repeated-touch degradation, and entry confirmation remain pending.

## Approval status

PARTIAL
