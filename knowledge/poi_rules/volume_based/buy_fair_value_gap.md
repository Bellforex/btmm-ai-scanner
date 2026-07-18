# Buy Fair Value Gap

## Alternative book name

Front-matter abbreviation list defines "1. Bear Value Gap = BFVG," but this label is never reused anywhere in the body text - the body consistently says "Fair Value Gap"/"FVG" for both directions. Recorded as a naming inconsistency, not a second concept (see AMBIGUITIES/PROJECT_STATE contradiction note). Related abbreviations PCH (Previous/first Candle High) and NCL (Next/third Candle Low) are used in the gap-geometry description.

## Family

Volume-Based POI

## Direction

Bullish

## Source pages

Front matter abbreviations (paragraphs 52-58); Chapter 1, "2. Fair Value Gap" (paragraphs 238-287); formal appendix "Buy Fair Value Gap Validation Conditions" (paragraphs 688-704).

## Book definition

A three-candle price imbalance formed when the market displaces very fast upward, leaving an empty/inefficient zone between candle 1 and candle 3; price may later return to rebalance it.

## Required market location

Formed within a directional (non-choppy, non-sideways) price movement; the book does not require it to sit at the 'origin' or 'middle' of a move the way Order Block/Engulfing are distinguished.

## Formation conditions

Candles preceding the gap show clear directional movement and are noticeably smaller than the middle displacement candle; the middle candle shows strong, aggressive bullish displacement. Resolved under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7): the displacement candle's speed is now separately measurable via Range Speed Ratio (candidate Total Range / median Total Range of the previous 20 confirmed candles, candidate excluded), classified NORMAL (<1.50), FAST (>=1.50 and <2.00), or VERY FAST (>=2.00). This speed measurement is a separate, optional quality signal - it does not replace or gate the strict three-candle FVG gap geometry, which remains independently mandatory (see Confirmation conditions). See knowledge/MEASUREMENT_STANDARDS.md, "Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard" (provisional, pending calibration).

## Confirmation conditions

Gap geometry is itself the confirmation: low of the third candle must remain above the high of the first candle. The candle following the displacement candle may be of any size and does not invalidate the gap. This strict three-candle geometry remains an independent mandatory requirement, unchanged by the speed standard. Resolved under Market Speed and Displacement Standard V1 — Provisional: an additional, optional STANDARD FAST / STRONG FAST classification is now available for displacement candles that also pass speed/expansion/body/close-position thresholds (see Strength classification) - a fast candle without valid FVG geometry is not an FVG, and a valid geometric FVG that fails the speed thresholds remains a valid (weaker) FVG candidate, not silently deleted.

## Origin candle or level

The 3-candle sequence (PCH = first/previous candle high; NCL = third/next candle low).

## Upper boundary

Low of the third candle (book: 'Buy FVG Zone = First Candle High to Third Candle Low').

## Lower boundary

High of the first candle.

## Wick treatment

The boundary itself uses the first candle's high and the third candle's low directly - wick extremes define the gap edges, they are not excluded.

## Body treatment

Not defined as a separate requirement beyond the displacement candle needing 'strong and aggressive bullish displacement' (a momentum descriptor, not a body-ratio formula) for basic FVG validity. Resolved under Market Speed and Displacement Standard V1 — Provisional, but only for the optional speed tiers: Body Efficiency (Body / Total Range) must be >= 0.60 for STANDARD FAST classification, >= 0.70 for STRONG FAST classification. Not required for a plain (non-fast) valid FVG.

## Candle-size requirement

Preceding candles must be 'noticeably smaller' than the displacement candle. Ambiguity 2 is resolved via Small Candle Standard V1: the displacement candle qualifies against the reference group when the reference's Total Range <= 0.50x the displacement candle's Total Range (standard) / <= 0.3333x (strong volume-switch), with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group. Resolved further under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7): for the speed-specific Displacement Expansion Ratio, the comparison window is now fixed at the 3 confirmed candles immediately before the displacement candle (Pre-Displacement Maximum Range = largest Total Range among those 3 candles; Displacement Expansion Ratio = displacement candle Total Range / Pre-Displacement Maximum Range). This gives FVG a concrete, usable answer to the previously open "how many preceding candles" question, specifically for the speed/expansion calculation.

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bullish Close Position of the displacement candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet. The Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7) adds a distinct, separate FVG Displacement Speed measurement (Range Speed Ratio, Displacement Expansion Ratio) - this is kept as its own field and is not merged into the Volume/Momentum Proxy Standard's fields or vice versa.

## Trend requirement

General POI framework note only.

## Market-structure requirement

General framework note only.

## Liquidity requirement

Not defined as FVG-specific.

## Timeframe requirement

No FVG-specific timeframe ranking is stated (contrast with Order Block's explicit Weekly>Daily>4H>1H>15m list).

## Strength classification

"Scenario A" (small candles then a big displacement candle = best/strongest) vs. "Scenario B" (preceding candles similar size to the displacement candle = weaker) - described narratively by the book, not numerically ranked. Resolved under Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7), as an additional, optional speed-based tier layered on top of a geometrically valid FVG: **STANDARD FAST** (Range Speed Ratio >=1.50, Displacement Expansion Ratio >=2.00, Body Efficiency >=0.60, Bullish Close Position >=0.70, valid FVG geometry); **STRONG FAST** (Range Speed Ratio >=2.00, Displacement Expansion Ratio >=3.00, Body Efficiency >=0.70, Bullish Close Position >=0.80, valid FVG geometry). A geometrically valid FVG that does not meet these speed thresholds remains a valid (non-fast) FVG candidate - it is not deleted or downgraded to invalid. No additional speed tiers are defined. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

One narrow rule is given: the size of the candle following the displacement candle does 'not invalidate' the FVG. This is the only invalidation-adjacent statement in the book for this POI, and it only rules out one specific non-invalidating condition - it supplies no general invalidation rule.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Order Block (both rely on a displacement candle) but distinguished by the 3-candle gap-geometry requirement, which Order Block does not have.

## Positive example

Yes (paragraphs 247-252, 287, 726-730). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption (Scenario B is described in text only).

## Machine-testable criteria

Partial - the 3-candle gap geometry, Range Speed Ratio, Displacement Expansion Ratio, Body Efficiency, and Bullish Close Position (including the STANDARD FAST / STRONG FAST tiers) are now all testable under Market Speed and Displacement Standard V1 — Provisional. Not testable: BTMM Approach/Reaction Speed and POI Dwell for this POI depend on expert-labelled anchors (Ambiguity 14, unresolved); minimum proxy thresholds (Body Efficiency/Close Position/Relative Tick Volume outside the speed tiers) remain unset; all lifecycle behavior (freshness, mitigation, invalidation, expiration) is undefined.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds outside the speed tiers are not yet set; no general invalidation/freshness/expiration rule beyond the one narrow note above; Ambiguity 14 (BTMM state machine) and the automatic anchors it would enable remain unresolved and were not touched by this decision; Market Speed and Displacement Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility regimes before it can be considered final.

## Author decision

Range Speed Ratio, Displacement Expansion Ratio (3-candle pre-displacement window), Body Efficiency, Bullish Close Position, and STANDARD FAST/STRONG FAST classification are approved (provisionally) - see Market Speed and Displacement Standard V1 — Provisional. This is layered on top of, and does not replace, the strict three-candle FVG gap geometry. Freshness/mitigation/invalidation/expiration, general proxy thresholds, and BTMM-anchor-dependent measurements (Ambiguity 14) remain pending.

## Approval status

PARTIAL
