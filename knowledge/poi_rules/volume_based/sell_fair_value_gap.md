# Sell Fair Value Gap

## Alternative book name

Same "Bear Value Gap = BFVG" front-matter naming inconsistency noted under Buy Fair Value Gap applies here too. Related abbreviations NCH (Next/third Candle High) and PCL (Previous/first Candle Low).

## Family

Volume-Based POI

## Direction

Bearish

## Source pages

Front matter abbreviations (paragraphs 52-58); Chapter 1, "2. Fair Value Gap" (paragraphs 238-287); formal appendix "Sell Fair Value Gap Validation Conditions" (paragraphs 705-720).

## Book definition

A three-candle price imbalance formed when the market displaces very fast downward, leaving an empty/inefficient zone between candle 1 and candle 3.

## Required market location

Formed within a directional (non-choppy) price movement.

## Formation conditions

Candles preceding the gap show clear directional movement and are noticeably smaller than the middle displacement candle; the middle candle shows strong, aggressive bearish displacement. Resolved under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7): the displacement candle's speed is now separately measurable via Range Speed Ratio (candidate Total Range / median Total Range of the previous 20 confirmed candles, candidate excluded), classified NORMAL (<1.50), FAST (>=1.50 and <2.00), or VERY FAST (>=2.00). This speed measurement is a separate, optional quality signal - it does not replace or gate the strict three-candle FVG gap geometry, which remains independently mandatory (see Confirmation conditions). See knowledge/MEASUREMENT_STANDARDS.md, "Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard" (provisional, pending calibration).

## Confirmation conditions

Gap geometry is the confirmation: high of the third candle must remain below the low of the first candle. The candle following the displacement candle may be any size without invalidating the gap. This strict three-candle geometry remains an independent mandatory requirement, unchanged by the speed standard. Resolved under Market Speed and Displacement Standard V1 — Provisional: an additional, optional STANDARD FAST / STRONG FAST classification is now available for displacement candles that also pass speed/expansion/body/close-position thresholds (see Strength classification) - a fast candle without valid FVG geometry is not an FVG, and a valid geometric FVG that fails the speed thresholds remains a valid (weaker) FVG candidate, not silently deleted.

## Origin candle or level

The 3-candle sequence (NCH = third/next candle high; PCL = first/previous candle low).

## Upper boundary

High of the third candle (book: 'Sell FVG Zone = Third Candle High to First Candle Low').

## Lower boundary

Low of the first candle.

## Wick treatment

Boundary uses third-candle-high and first-candle-low directly - wick extremes define the gap edges.

## Body treatment

Not defined as a separate requirement beyond the displacement candle's momentum descriptor for basic FVG validity. Resolved under Market Speed and Displacement Standard V1 — Provisional, but only for the optional speed tiers: Body Efficiency (Body / Total Range) must be >= 0.60 for STANDARD FAST classification, >= 0.70 for STRONG FAST classification. Not required for a plain (non-fast) valid FVG.

## Candle-size requirement

Preceding candles 'noticeably smaller' than the displacement candle. Ambiguity 2 is resolved via Small Candle Standard V1: the displacement candle qualifies against the reference group when the reference's Total Range <= 0.50x the displacement candle's Total Range (standard) / <= 0.3333x (strong volume-switch), with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group. Resolved further under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7): for the speed-specific Displacement Expansion Ratio, the comparison window is now fixed at the 3 confirmed candles immediately before the displacement candle (Pre-Displacement Maximum Range = largest Total Range among those 3 candles; Displacement Expansion Ratio = displacement candle Total Range / Pre-Displacement Maximum Range). This gives FVG a concrete, usable answer to the previously open "how many preceding candles" question, specifically for the speed/expansion calculation.

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position of the displacement candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet. The Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7) adds a distinct, separate FVG Displacement Speed measurement (Range Speed Ratio, Displacement Expansion Ratio) - this is kept as its own field and is not merged into the Volume/Momentum Proxy Standard's fields or vice versa.

## Trend requirement

General POI framework note only.

## Market-structure requirement

General framework note only.

## Liquidity requirement

Not defined as FVG-specific.

## Timeframe requirement

No FVG-specific timeframe ranking stated.

## Strength classification

"Scenario A" (best) vs. "Scenario B" (weaker) - narrative only, from the book. Resolved under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7), as an additional, optional speed-based tier layered on top of a geometrically valid FVG: **STANDARD FAST** (Range Speed Ratio >=1.50, Displacement Expansion Ratio >=2.00, Body Efficiency >=0.60, Bearish Close Position >=0.70, valid FVG geometry); **STRONG FAST** (Range Speed Ratio >=2.00, Displacement Expansion Ratio >=3.00, Body Efficiency >=0.70, Bearish Close Position >=0.80, valid FVG geometry). A geometrically valid FVG that does not meet these speed thresholds remains a valid (non-fast) FVG candidate - it is not deleted or downgraded to invalid. No additional speed tiers are defined. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Same narrow note as Buy FVG: trailing-candle size does not invalidate the gap; no general invalidation rule given.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Order Block via the shared displacement-candle concept; distinguished by the 3-candle gap geometry.

## Positive example

Yes (paragraphs 247-252, 287, 726-730). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - the 3-candle gap geometry, Range Speed Ratio, Displacement Expansion Ratio, Body Efficiency, and Bearish Close Position (including the STANDARD FAST / STRONG FAST tiers) are now all testable under Market Speed and Displacement Standard V1 — Provisional. Not testable: BTMM Approach/Reaction Speed and POI Dwell for this POI depend on expert-labelled anchors (Ambiguity 14, unresolved); minimum proxy thresholds (Body Efficiency/Close Position/Relative Tick Volume outside the speed tiers) remain unset; all lifecycle behavior (freshness, mitigation, invalidation, expiration) is undefined.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds outside the speed tiers are not yet set; no general invalidation/freshness/expiration rule; Ambiguity 14 (BTMM state machine) and the automatic anchors it would enable remain unresolved and were not touched by this decision; Market Speed and Displacement Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility regimes before it can be considered final.

## Author decision

Range Speed Ratio, Displacement Expansion Ratio (3-candle pre-displacement window), Body Efficiency, Bearish Close Position, and STANDARD FAST/STRONG FAST classification are approved (provisionally) - see Market Speed and Displacement Standard V1 — Provisional. This is layered on top of, and does not replace, the strict three-candle FVG gap geometry. Freshness/mitigation/invalidation/expiration, general proxy thresholds, and BTMM-anchor-dependent measurements (Ambiguity 14) remain pending.

## Approval status

PARTIAL
