# Bullish Pressure Wick

## Alternative book name

"Pressure wick" is the section heading (paragraph 359); "liquidity wick" is used interchangeably throughout the same section, including the heading "HOW TO SELECT THE BEST TYPE OF LIQUIDITY WICK" (paragraph 369). Same POI, two names used interchangeably by the author, not two concepts.

## Family

Volume-Based POI

## Direction

Bullish (acts as a future buying zone when price returns to it).

## Source pages

"5. Pressure wick" (paragraphs 359-373).

## Book definition

A strong rejection wick where price pushes down into a zone, collects liquidity, and is strongly rejected upward, while the candle still closes with a body that has "good proportion" (real participation, not just a bare wick).

## Required market location

Not location-restricted beyond appearing where price has pushed into a zone and been rejected; best identified on higher timeframes (2H/3H/4H and above, per author experience stated in the book).

## Formation conditions

Resolved under Pressure Wick Standard V1 — Provisional (Ambiguity 6): on a confirmed closed candle (Total Range = High - Low must be > 0), all of: Lower Wick Share (Lower Wick / Total Range) >= 0.40; Body Efficiency (Body / Total Range) >= 0.25; Lower Wick >= 2x Upper Wick; Bullish Close Position ((Close - Low) / Total Range) >= 0.60. The candle may close bullish or bearish - candle colour alone does not determine direction. See knowledge/MEASUREMENT_STANDARDS.md, "Pressure Wick Measurement, Drawing, and Classification Standard" (provisional, pending calibration).

## Confirmation conditions

Resolved under Pressure Wick Standard V1 — Provisional: status is **CANDIDATE** before the candle closes and becomes **CONFIRMED** once the candle closes and all mandatory formation conditions pass. RETESTED, MITIGATED, SWEPT, BROKEN, and EXPIRED are not defined by this decision. The book's own recommendation still applies on top of this: do not enter blindly when price returns to the wick - drop to a lower timeframe for confirmation and a more precise entry (this remains a qualitative, not formally defined, entry-confirmation rule - see "Still unresolved" below).

## Origin candle or level

The single confirmed wick candle.

## Upper boundary

Resolved under Pressure Wick Standard V1 — Provisional: Zone Top = MIN(Open, Close). This zone contains only the lower rejection wick; the candle body is never automatically included.

## Lower boundary

Resolved under Pressure Wick Standard V1 — Provisional: Zone Bottom = Candle Low.

## Wick treatment

Resolved under Pressure Wick Standard V1 — Provisional: Lower Wick = MIN(Open, Close) - Low; Lower Wick Share = Lower Wick / Total Range must be >= 0.40; Lower Wick must be >= 2x Upper Wick (>= 3x for STRONG). A Wick Dominance Ratio (Rejection Wick / MAX(Opposite Wick, Minimum Price Tick)) provides division-by-zero protection; the Minimum Price Tick is sourced from instrument metadata once the software layer exists. This is still separate from, and does not replace, the standard displacement/size-ratio rule that other POIs use (Measurement Standard V1 SS7 continues to exempt Pressure Wick from that rule).

## Body treatment

Resolved under Pressure Wick Standard V1 — Provisional: Body Efficiency (Body / Total Range) must be >= 0.25 (>= 0.30 for STRONG). This replaces the book's qualitative "good proportion" language with a precise threshold, resolving Ambiguity 6.

## Candle-size requirement

Not a 2x/3x multi-candle displacement ratio (Pressure Wick remains exempted from that rule per Measurement Standard V1 SS7). Range Context is now defined instead: Range Context Ratio = Candidate Total Range / Median Total Range of the previous 20 confirmed candles (current candle excluded) must be >= 1.25 for STRONG classification only (not required for STANDARD). See knowledge/MEASUREMENT_STANDARDS.md, "Pressure Wick Measurement, Drawing, and Classification Standard."

## Volume or momentum proxy

Resolved under Pressure Wick Standard V1 — Provisional: Pressure Wicks now reference the approved Volume, Momentum, and Price-Activity Proxy Standard - price/candle behaviour is primary evidence, tick volume is secondary and never mandatory, missing tick volume never invalidates a Pressure Wick, and external indicators (RSI, MACD, Stochastic, ADX, Rate of Change) are not mandatory. No final price_activity_score formula or new indicator threshold is invented.

## Trend requirement

Not defined as wick-specific.

## Market-structure requirement

Not defined as wick-specific.

## Liquidity requirement

Central to the concept by name ("collects liquidity... strong rejection") but no numeric rule for how much liquidity or how the rejection is measured.

## Timeframe requirement

Explicitly recommended on 2H, 3H, 4H and above for identification; a lower timeframe is used only for entry confirmation, not for identifying the wick itself. Resolved under Pressure Wick Standard V1 — Provisional: H3, H4, D1, and W1 receive higher-timeframe **contextual priority only** (not a numerical score); a candle that fails the mandatory formation conditions remains invalid regardless of timeframe.

## Strength classification

Resolved under Pressure Wick Standard V1 — Provisional: **STRONG** requires all of Lower Wick Share >= 0.50, Body Efficiency >= 0.30, Lower Wick >= 3x Upper Wick, Bullish Close Position >= 0.70, and Range Context Ratio >= 1.25. A candidate passing the standard formation conditions but not every STRONG condition is **STANDARD**. No additional tiers are defined. Still provisional pending calibration.

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

Conceptually close to the long-wick concept used in Hammer. Resolved under Pressure Wick Standard V1 — Provisional: Pressure Wick remains a Volume-Based POI and Hammer remains a Price-Action POI; one candle may independently qualify for both labels, which must be preserved separately and never silently merged into one POI type. The Hammer rule file itself was not modified by this decision - the wick:body proportions approved here do not apply to Hammer (see scope limitation).

## Positive example

Yes (paragraphs 364-368). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - wick/body proportions, close-position threshold, zone-drawing boundaries, strength classification (STANDARD/STRONG), and the CANDIDATE/CONFIRMED states are now all testable under Pressure Wick Standard V1 — Provisional. Not testable: proof of liquidity collection, required approach speed, nearby structural-zone requirement, retest confirmation, and all lifecycle behavior (freshness, mitigation, invalidation, expiration) - none of it is defined.

## Unresolved questions

Proof of liquidity collection; required preceding market approach speed; required nearby support/resistance/trendline/structural zone; retest confirmation; freshness; partial/full mitigation; sweep rules; general invalidation; expiration; trade-entry confirmation; minimum Body Efficiency/Close Position/Relative Tick Volume thresholds from the Volume/Momentum Proxy Standard remain unset. Pressure Wick Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different sessions, and different volatility regimes before it can be considered final.

## Author decision

Wick/body proportions (Lower Wick Share, Body Efficiency, wick-dominance ratio, Bullish Close Position), zone-drawing boundaries, STANDARD/STRONG strength classification, and CANDIDATE/CONFIRMED states are approved (provisionally) - see Pressure Wick Standard V1 — Provisional. Liquidity collection proof, approach speed, structural-zone requirement, retest, freshness, mitigation, sweep, invalidation, and expiration remain pending.

## Approval status

PARTIAL
