# Resistance

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Structural POI

## Direction

Bearish (selling opportunities, or break-and-retest continuation to the downside).

## Source pages

"2. Support levels - Resistance levels" (paragraphs 590-602).

## Book definition

A horizontal level where price has shown meaningful reaction before; used for reversals or break-and-retest continuation.

## Required market location

A horizontal price level above current/recent price action.

## Formation conditions

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional (Ambiguity 12): **Author-Approved, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated.** A Resistance origin must be a CONFIRMED_MEANINGFUL_SWING_HIGH (per the Meaningful Swing Standard, Ambiguity 10) - FORMING, LOCAL_SWING_CANDIDATE, and SUPERSEDED records cannot create a zone. The candidate origin is then evaluated via the approved POI Reaction Strength Standard (Ambiguity 9): a WEAK_REACTION origin becomes REJECTED_ORIGIN_CANDIDATE; a STANDARD_REACTION or STRONG_REACTION origin becomes DRAFT_RESISTANCE, available only after the origin reaction is fully classified (never exposed historically at the original pivot time). See knowledge/MEASUREMENT_STANDARDS.md, "Support and Resistance Detection and Validation Standard."

## Confirmation conditions

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: a later touch must use a distinct CONFIRMED_MEANINGFUL_SWING_HIGH that is geometrically acceptable (Swing High Pivot Price >= Zone Bottom - Horizontal Touch Tolerance AND <= Zone Top + Horizontal Pierce Tolerance) and produces at least STANDARD_REACTION (a STRONG_REACTION is supporting evidence but does not replace the distinct-touch requirement). A pivot plateau counts as one touch; LOCAL_SWING_CANDIDATE, SUPERSEDED, FORMING, and NEAR_MISS never count; at least one opposite confirmed meaningful swing must exist between two same-type qualifying touches. The book's own break-and-retest narrative is not itself formalized by this standard - it remains a qualitative description.

## Origin candle or level

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: the earliest eligible CONFIRMED_MEANINGFUL_SWING_HIGH that creates the zone becomes ORIGIN_CREATOR (origin_creator_swing_id/price/time preserved). **Initial creator principle:** later touches never move the origin price, replace the origin swing, average the zone with later prices, recalculate the original boundaries, resize it, or recenter it - a separate eligible origin creates a separate candidate zone entirely.

## Upper boundary

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: Zone Top = Origin Swing High Pivot Price. Creator Reference ATR = ATR(14) at the origin swing candle (or median ATR(14) across plateau candles for a plateau origin), same symbol/provider/timeframe; guarded against missing/zero/invalid ATR or tick metadata.

## Lower boundary

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: Zone Bottom = Zone Top - Horizontal Zone Depth, where Horizontal Zone Depth = MAX(2x Minimum Price Tick, 0.10x Creator Reference ATR) (fixed permanently after zone creation; no fixed pip/point values).

## Wick treatment

The origin price is the swing's approved Pivot Price, which is itself wick-based per the Meaningful Swing Standard (wick high, never close/body/colour) - inherited, not redefined by this standard.

## Body treatment

Not applicable - origin and touch qualification are price-level (wick-pivot) based, not body-size based; the book gives no separate body rule for Resistance.

## Candle-size requirement

Not applicable / not defined.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

Not defined as a precondition.

## Market-structure requirement

Not defined beyond the general POI framework note.

## Liquidity requirement

Orders/stops/take-profits cluster around the level; no formula.

## Timeframe requirement

Not explicitly ranked for this POI.

## Strength classification

Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: one qualifying origin reaction = DRAFT_RESISTANCE; two distinct qualifying reactions (including the origin) = CONFIRMED_RESISTANCE; three or more distinct qualifying reactions = STRONG_RESISTANCE. Every counted interaction must produce at least STANDARD_REACTION. No additional tiers. Touch count is structural evidence only - it does not define freshness, remaining zone quality, repeated-touch degradation, entry validity, or expiration. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. Resolved partially under Support and Resistance Detection and Validation Standard V1 — Provisional: RESISTANCE_BREAK_CANDIDATE is recorded when a confirmed candle closes above Zone Top by more than Horizontal Pierce Tolerance - but this is explicitly **not** final invalidation. Confirmed break, reclaim, retest, false break, sweep, and role reversal (Resistance becoming Support) remain unresolved and are not defined by this standard.

## Expiration

NOT DEFINED IN BOOK.

## Overlap with other POIs

Related to Trendline (diagonal resistance) and to the Previous/Current Period High-Low family. Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: **Equal Highs relationship** - Equal Highs != Resistance; the same confirmed meaningful swings may independently satisfy both standards, and both labels are preserved when that happens (the approved Equal Highs/Equal Lows formulas, Ambiguity 5, are unchanged). **Trendline horizontal-candidate relationship** - a Trendline HORIZONTAL_CANDIDATE (Ambiguity 11) may be evaluated under this Resistance standard but never automatically becomes Resistance; it must independently pass origin eligibility, creator boundary, origin reaction, touch tolerance, distinct-touch, and confirmation requirements (the approved Trendline formulas/thresholds are unchanged). Non-repainting behavior: once created, origin swing ID/price/time, Creator Reference ATR, Zone Top/Bottom, and zone depth never move or get recalculated; later touches never recenter/resize the zone; a later origin creates a new zone candidate. Multiple Resistance candidates may coexist per timeframe - nearby zones are never silently merged, and no BEST_RESISTANCE/PRIMARY_ZONE/ranking/composite score is created.

## Positive example

Yes (paragraphs 595-602). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - origin eligibility (via the Meaningful Swing Standard), the initial-creator rule, fixed zone boundaries (Zone Top/Bottom/Depth), origin-reaction gating (via the POI Reaction Strength Standard), Touch/Pierce tolerances, distinct-touch confirmation, DRAFT/CONFIRMED/STRONG progression, RESISTANCE_BREAK_CANDIDATE detection, and non-repainting availability are now all testable under Support and Resistance Detection and Validation Standard V1 — Provisional. Not testable: final invalidation, confirmed break, reclaim, retest, false break, role reversal, freshness, repeated-touch degradation, partial/full mitigation, expiration, zone merging, zone ranking, entry confirmation (none defined); HH/HL/LH/LL, BOS, CHoCH (not defined, out of scope). The underlying swing standard's material-breach sub-rule (Ambiguity 10) and the POI Reaction Strength Standard's own thresholds are also inherited dependencies.

## Unresolved questions

Final Resistance invalidation; confirmed break; reclaim; retest; false break; role reversal (Resistance becoming Support); freshness; repeated-touch degradation; partial/full mitigation; expiration; zone merging; zone ranking; entry confirmation; HH/HL/LH/LL; BOS/CHoCH; BTMM state transitions (Ambiguity 14, unchanged). Support and Resistance Detection and Validation Standard V1 is explicitly Author-Approved but Engineering-Provisional - NOT YET empirically calibrated or out-of-sample validated, and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility/trend regimes before it can be considered final or production-approved.

## Author decision

**Evidence status: Author-Approved, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, NOT Production-Approved.** Origin eligibility, initial-creator principle, Creator Reference ATR, Horizontal Zone Depth, fixed Zone Top/Bottom boundaries, origin-reaction requirement, Touch/Pierce tolerances, distinct-touch confirmation, DRAFT/CONFIRMED/STRONG classification, RESISTANCE_BREAK_CANDIDATE detection, non-repainting behavior, multiple-zone handling, and the Equal Highs/Trendline-horizontal-candidate relationships are approved (provisionally) - see Support and Resistance Detection and Validation Standard V1 — Provisional. Final invalidation, confirmed break, reclaim, retest, false break, role reversal, freshness, mitigation, expiration, zone merging, zone ranking, and entry confirmation remain pending.

## Approval status

PARTIAL
