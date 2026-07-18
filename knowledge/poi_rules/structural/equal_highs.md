# Equal Highs

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bearish (buy-side liquidity rests above; used as a bearish liquidity-grab trigger leading toward a bearish POI).

## Source pages

"3. Equal highs - Equal lows" (paragraphs 603-617).

## Book definition

Price levels where the market has reached "the same high area" more than once; buy-side liquidity is assumed to rest above.

## Required market location

Two or more highs reached at a similar level.

## Formation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional (Ambiguity 5): at least 2 confirmed swing points, using confirmed swing-high wick prices, all from the same timeframe (never combined across timeframes). Swing points must come from an expert-labelled, manually confirmed, or otherwise explicitly approved confirmed-swing source - the automatic swing-detection method itself remains unresolved under Ambiguity 10 and is not invented here. Equal Highs Cluster Spread (highest qualifying swing-high wick price minus lowest qualifying swing-high wick price) must be <= Equality Tolerance, where Equality Tolerance = MAX(2 x minimum price ticks for the instrument, 0.10 x Reference ATR), and Reference ATR = median ATR(14) across all qualifying swing-touch candles (same symbol/timeframe, confirmed candles only). See knowledge/MEASUREMENT_STANDARDS.md, "Equal Highs and Equal Lows Tolerance and Drawing Standard" (provisional, pending calibration).

## Confirmation conditions

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: the pattern is **CONFIRMED** only when at least 2 qualifying swing points exist, all are from the same timeframe, the latest swing point has itself been confirmed, and the cluster spread remains within Equality Tolerance. Before the latest swing confirms, the pattern is only **FORMING**. The book's own recommendation still applies on top of this: treat Equal Highs as an entry TRIGGER leading to another POI, not a direct entry zone - wait for the liquidity grab (a sweep beyond the level) first, then look for confirmation at the main POI the sweep leads toward. SWEPT and BROKEN states are reserved for later but not defined now.

## Origin candle or level

The repeated confirmed swing-high wick points (at least 2, same timeframe).

## Upper boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Top = highest qualifying swing-high wick price. An optional Reference Level (median of all qualifying swing-high wick prices) may also be drawn but must not replace the Zone Top/Zone Bottom boundaries.

## Lower boundary

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: Zone Bottom = lowest qualifying swing-high wick price (this now gives Equal Highs a real two-sided zone rather than "not applicable," since the standard defines both a Zone Top and Zone Bottom from the cluster's wick-price spread).

## Wick treatment

Resolved under Equal Highs and Equal Lows Standard V1 — Provisional: confirmed swing-high **wick** prices are explicitly used (not close prices) for both the equality comparison and the Zone Top/Zone Bottom boundaries.

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

Central to the concept (buy-side liquidity above). Liquidity expectation is now formalized under Equal Highs and Equal Lows Standard V1 — Provisional: liquidity is expected **above Zone Top**. No numeric sizing rule (how much liquidity) is defined - only the expected location.

## Timeframe requirement

More reliable on higher timeframes (stronger liquidity) - stated generally, no explicit ranking list like Order Block's.

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

Conceptually related to Swing High and to the Previous/Current Period High-Low family (all are 'prior highs' that attract liquidity) - the book does not give a formal hierarchy distinguishing them.

## Positive example

Yes (paragraphs 608-612). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - equality tolerance, Reference ATR, Cluster Spread, strength classification, Zone Top/Bottom drawing, and the FORMING/CONFIRMED states are now all testable under Equal Highs and Equal Lows Standard V1 — Provisional, **provided** confirmed swing points are already supplied by an approved external source (expert-labelled or manually confirmed). Not testable end-to-end: the automatic swing-detection step itself (Ambiguity 10, unresolved), SWEPT/BROKEN states, and all lifecycle behavior (freshness, mitigation, invalidation, expiration).

## Unresolved questions

The automatic swing-detection algorithm (Ambiguity 10, still open - this standard consumes confirmed swing points but does not produce them); SWEPT and BROKEN state definitions; reclaim, invalidation, expiration, freshness, and mitigation rules; Equal Highs and Equal Lows Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different volatility regimes, and different market sessions before it can be considered final.

## Author decision

Equality tolerance, Reference ATR, Cluster Spread formulas, strength classification, drawing boundaries, and FORMING/CONFIRMED states are approved (provisionally) - see Equal Highs and Equal Lows Standard V1 — Provisional. Swing-detection method (Ambiguity 10), SWEPT/BROKEN states, and freshness/mitigation/invalidation/expiration remain pending.

## Approval status

PARTIAL
