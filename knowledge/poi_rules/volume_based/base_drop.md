# Base Drop

## Alternative book name

"Drop-Base-Drop" is used in the introductory chapter (paragraphs 188, 342); "Base Drop" is used in the formal validation appendix. Same concept, two labels. Also note: the intro summary list at paragraph 174 contains an apparent typo, "drop base trop," instead of "drop base drop" - recorded as a book-internal typo.

## Family

Volume-Based POI

## Direction

Bearish

## Source pages

"4. Rally base rally / Drop base drop" (paragraphs 342-358); formal appendix "Base Drop Validation Conditions" (paragraphs 994-1015) within "Base Drop and Base Rally POI Validation Conditions" (paragraphs 942-1049).

## Book definition

Price makes a strong downward move, pauses in a small horizontal 'base,' then breaks out again strongly downward; the base itself is the POI.

## Required market location

The base must be a distinct pause/consolidation after an existing bearish move, before the breakout.

## Formation conditions

Resolved under Base Formation Standard V1 — Provisional (Ambiguity 4): 2 to 6 consecutive confirmed closed candles (more than 6 is initially classified as consolidation, not a precise Base Drop POI); every base candle's Total Range <= 0.50x the departure candle's Total Range (<= 0.3333x for Strong Base), compared against the largest base candle; Base Height (Highest High - Lowest Low of all base candles) <= 0.75x ATR(14) (same symbol/timeframe) AND <= 0.60x the departure candle's Total Range; Base Midpoint Drift (using candle midpoints = (High+Low)/2) <= 0.25x Base Height, to reject a directional staircase; and, for each consecutive base-candle pair, Overlap Ratio >= 0.50. See knowledge/MEASUREMENT_STANDARDS.md, "Base Formation, Compactness, and Departure Standard" (provisional, pending calibration against expert-approved/rejected examples across symbols, timeframes, and volatility regimes).

## Confirmation conditions

Resolved under Base Formation Standard V1 — Provisional: the departure candle must be bearish, close below the base's Lowest Low (Departure Close < Lowest Low of all base candles), be at least 2x the largest base candle (>=3x for Strong Base), and separate decisively from the base. Departure-candle momentum/volume evidence is evaluated using the approved Volume, Momentum, and Price-Activity Proxy Standard (no separate momentum rule invented here).

## Origin candle or level

The full group of 2 to 6 base candles - the candle-count bounds are now fixed by Base Formation Standard V1 — Provisional.

## Upper boundary

Base High = highest high of all base candles (unchanged formula; the candle group is now bounded to 2-6 candles by Base Formation Standard V1 — Provisional).

## Lower boundary

Base Low = lowest low of all base candles (unchanged formula; same 2-6 candle-count bound applies).

## Wick treatment

Base High/Low use candle highs/lows (wicks included), per Measurement Standard V1 SS5.

## Body treatment

Not defined as a separate zone-drawing rule.

## Candle-size requirement

Departure candle Size Ratio >= 2.0 (standard) / >= 3.0 (strong) vs. the LARGEST individual base candle. Resolved under Candle Measurement Standard V1 SS7 and Small Candle Standard V1 (Ambiguity 2). The number of candles forming a valid base (2-6) and the base's compactness (size, height, midpoint drift, overlap) are now also resolved under Base Formation Standard V1 — Provisional (Ambiguity 4) - see knowledge/MEASUREMENT_STANDARDS.md, "Base Formation, Compactness, and Departure Standard." This standard remains provisional pending calibration against expert-approved/rejected examples.

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position of the departure candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. Base Formation Standard V1 — Provisional explicitly incorporates this proxy standard as the departure candle's momentum evidence (no separate momentum rule invented for bases). See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

Must follow an existing strong downward move.

## Market-structure requirement

Not defined beyond the base itself.

## Liquidity requirement

Not defined as base-specific.

## Timeframe requirement

Explicit ranking: Weekly base > Daily base > 4H base > 1H base > 15-minute base.

## Strength classification

Resolved under Base Formation Standard V1 — Provisional: **COMPACT BASE** (passes all standard base conditions - candle count, size, height, drift, overlap, departure ratio >=2x and close-outside-base); **STRONG BASE** (every base candle <= 0.3333x the departure candle's Total Range, departure candle >= 3x the largest base candle, and all other compactness/height/overlap/close-outside conditions pass); **INVALID BASE** (any mandatory condition fails - fewer than 2 or more than 6 base candles, excessive Base Height, excessive midpoint drift, insufficient overlap, an oversized base candle, an undersized departure candle, a departure candle that fails to close outside the base range, or wrong direction). This replaces the book's informal Standard/Strong/Weak language with the same 2x/3x logic made precise. Still provisional pending calibration.

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

Shares the 'small candles' language with Fair Value Gap; distinguished by the horizontally-aligned multi-candle base requirement.

## Positive example

Yes (paragraphs 347-352, 358, 1050-1053). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - Base High/Low, candle count (2-6), base-candle size, Base Height, midpoint drift, overlap ratio, and departure-candle ratio/close-outside-base are now all testable under Base Formation Standard V1 — Provisional. Lifecycle behavior (freshness, mitigation, invalidation, expiration) remains untestable because none of it is defined, and the provisional thresholds themselves still await calibration.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds (Body Efficiency, Close Position, Relative Tick Volume, price_activity_score) are not yet set; no invalidation/freshness/expiration rule; Base Formation Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, H3/H4/D1/W1, and different volatility regimes before it can be considered final.

## Author decision

Base candle count (2-6), base-candle size/height/drift/overlap, and departure-candle confirmation are approved (provisionally) - see Base Formation Standard V1 — Provisional. Freshness/mitigation/invalidation/expiration and final proxy thresholds remain pending.

## Approval status

PARTIAL
