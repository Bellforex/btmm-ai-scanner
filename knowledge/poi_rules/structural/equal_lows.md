# Equal Lows

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bullish (sell-side liquidity rests below; used as a bullish liquidity-grab trigger leading toward a bullish POI).

## Source pages

"3. Equal highs - Equal lows" (paragraphs 603-617).

## Book definition

Price levels where the market has reached "the same low area" more than once; sell-side liquidity is assumed to rest below.

## Required market location

Two or more lows reached at a similar level.

## Formation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional (Ambiguity 5): at least 2 confirmed swing points, using confirmed swing-low wick prices, all from the same timeframe (never combined across timeframes). **Swing-source dependency resolved under Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10):** the qualifying swing points must be two distinct **CONFIRMED_MEANINGFUL_SWING_LOW** events (an adjacent plateau counts as one event); **LOCAL_SWING_CANDIDATE** and **SUPERSEDED** records do not qualify; at least one opposite confirmed meaningful swing (a CONFIRMED_MEANINGFUL_SWING_HIGH) must exist between two same-type Equal-Low swing events. See knowledge/MEASUREMENT_STANDARDS.md, "Meaningful Swing High and Swing Low Detection Standard." Equal Lows Cluster Spread (highest qualifying swing-low wick price minus lowest qualifying swing-low wick price) must be <= Equality Tolerance, where Equality Tolerance = MAX(2 x minimum price ticks for the instrument, 0.10 x Reference ATR), and Reference ATR = median ATR(14) across all qualifying swing-touch candles (same symbol/timeframe, confirmed candles only) - **this Equality Tolerance/Reference ATR formula and the 0.05x/0.10x strength thresholds are unchanged by the swing-source update.** See knowledge/MEASUREMENT_STANDARDS.md, "Equal Highs and Equal Lows Tolerance and Drawing Standard" (provisional, pending calibration).

## Confirmation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: the pattern is **CONFIRMED** only when at least 2 qualifying swing points exist, all are from the same timeframe, the latest swing point has itself been confirmed, and the cluster spread remains within Equality Tolerance. Before the latest swing confirms, the pattern is only **FORMING**. The book's own recommendation still applies on top of this: treat Equal Lows as an entry trigger leading to another POI, not a direct entry zone - wait for the liquidity grab first, then confirmation at the main POI. SWEPT and BROKEN states are reserved for later but not defined now.

## Origin candle or level

The repeated confirmed swing-low wick points (at least 2, same timeframe).

## Upper boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Top = highest qualifying swing-low wick price (this now gives Equal Lows a real two-sided zone rather than "not applicable," since the standard defines both a Zone Top and Zone Bottom from the cluster's wick-price spread).

## Lower boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Bottom = lowest qualifying swing-low wick price. An optional Reference Level (median of all qualifying swing-low wick prices) may also be drawn but must not replace the Zone Top/Zone Bottom boundaries.

## Wick treatment

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: confirmed swing-low **wick** prices are explicitly used (not close prices) for both the equality comparison and the Zone Top/Zone Bottom boundaries.

## Body treatment

Not defined in the book.

## Candle-size requirement

Not applicable / not defined.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

Not defined beyond the general POI framework note.

## Market-structure requirement

Not defined beyond the general POI framework note.

## Liquidity requirement

Central to the concept (sell-side liquidity below). Liquidity expectation is now formalized under Equal Highs and Equal Lows Standard V1 — Provisional: liquidity is expected **below Zone Bottom**. No numeric sizing rule (how much liquidity) is defined - only the expected location.

## Timeframe requirement

More reliable on higher timeframes - stated generally.

## Strength classification

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: **STRONG** (Cluster Spread <= 0.05x Reference ATR), **STANDARD** (> 0.05x and <= 0.10x Reference ATR), **NOT EQUAL** (Cluster Spread > Equality Tolerance). The minimum-tick floor from the Equality Tolerance formula still applies throughout. No additional tiers are defined. Still provisional pending calibration.

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

Related to Swing Low and to the Previous/Current Period High-Low family.

## Positive example

Yes (paragraphs 608-612). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - equality tolerance, Reference ATR, Cluster Spread, strength classification, Zone Top/Bottom drawing, the FORMING/CONFIRMED states, and now (Ambiguity 10, provisional) the swing-source detection itself (local pivot window, meaningful-reversal confirmation, plateau/SUPERSEDED handling) are all testable under the combined Equal Highs and Equal Lows Standard V1 — Provisional and Meaningful Swing High and Swing Low Detection Standard V1 — Provisional. Not testable end-to-end: STRONG_SWING's material-breach condition (undefined, affects swing strength but not Equal-Lows eligibility itself), SWEPT/BROKEN states, and all lifecycle behavior (freshness, mitigation, invalidation, expiration).

## Unresolved questions

The swing-source detection method is now resolved (provisionally) via Meaningful Swing High and Swing Low Detection Standard V1 (Ambiguity 10), but that standard's own material-breach sub-rule for STRONG_SWING remains undefined; SWEPT and BROKEN state definitions; reclaim, invalidation, expiration, freshness, and mitigation rules; both standards are explicitly provisional and require future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different volatility regimes, and different market sessions before they can be considered final.

## Author decision

Equality tolerance, Reference ATR, Cluster Spread formulas, strength classification, drawing boundaries, and FORMING/CONFIRMED states are approved (provisionally) - see Equal Highs and Equal Lows Standard V1 — Provisional. The swing-source dependency is now also approved (provisionally) - see Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10). SWEPT/BROKEN states, the material-breach sub-rule, and freshness/mitigation/invalidation/expiration remain pending.

## Approval status

PARTIAL
