# Sell Order Block

## Alternative book name

"Bearish Order Block" (informal narrative usage) alongside the formal term "Sell Order Block" used in the validation appendix. Same concept.

## Family

Volume-Based POI

## Direction

Bearish

## Source pages

Chapter 1, Volume-Based POI, "Order blocks (OB)" (paragraphs 199-237); formal appendix "Sell Order Block Validation Conditions" (paragraphs 872-908).

## Book definition

A two-candle pattern usually found at the end/origin of a prior bullish move, right before the market reverses downward: a smaller first candle followed by a larger bearish displacement candle showing a volume switch.

## Required market location

Must be located at the beginning/origin of a significant bearish price movement - not randomly in the middle of an existing move.

## Formation conditions

Two consecutive candles: a smaller first candle, then a larger bearish displacement candle with strong, aggressive downward momentum that initiates a significant move away from the first candle.

## Confirmation conditions

No separate confirmation step distinct from the formation/size rule itself is given.

## Origin candle or level

The smaller (first) of the two candles.

## Upper boundary

High of the smaller first candle.

## Lower boundary

Low of the smaller first candle.

## Wick treatment

Full high-to-low range of the smaller candle is used for the zone; wicks are included, per Candle Measurement Standard V1 SS5.

## Body treatment

Not required for zone-drawing; Body Efficiency may be tracked separately per Measurement Standard V1 SS4 but is not required for validity.

## Candle-size requirement

Size Ratio (Total Range basis) >= 2.0 for a standard pattern, >= 3.0 for a strong pattern vs. the smaller candle. Formula: Bearish Displacement Candle Size >= 2 x Previous Candle Size. Resolved under Candle Measurement Standard V1 (Ambiguity 1). The "smaller candle" itself is now also governed by Small Candle Standard V1 (Ambiguity 2, resolved): Small Candle Total Range <= 0.50x the displacement candle's Total Range (standard) / <= 0.3333x (strong volume-switch); a separate, secondary Recent Market Context classification (vs. the 20-candle median range) does not override this. Comparison target: the immediately preceding (smaller) candle. See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

General POI framework note only.

## Market-structure requirement

General framework note only; no Sell-Order-Block-specific structural precondition is stated.

## Liquidity requirement

Not defined as an Order-Block-specific rule.

## Timeframe requirement

Explicit strength ranking: Weekly > Daily > 4H > 1H > 15-minute Sell Order Block.

## Strength classification

Standard (2.0-<3.0) vs. Strong (>=3.0); Higher-timeframe vs. Lower-timeframe (lower TF may require additional confirmation).

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved RECON-D1):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, available only from `order_block_available_time` onward. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Order Block formation, location, candle-size, or strength formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `CONDITIONAL_GENERIC_INHERITANCE` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved RECON-D1, see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is required and is guaranteed here because the origin candle's High and Low are, by definition, distinct prices for any candle with positive Total Range.

**Expected direction:** BEARISH.

**Zone Top mapping:** High of the smaller (origin) candle (the already-approved Sell Order Block boundary — unchanged by this inheritance, used exactly as documented above).

**Zone Bottom mapping:** Low of the smaller (origin) candle (unchanged by this inheritance).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Lifecycle availability time (RECON-D1, approved):** `order_block_available_time = qualifying_displacement_candle_close_time` — the close time of the first confirmed displacement candle satisfying the existing approved Order Block formation conditions (Size Ratio >= 2.0, or >= 3.0 for Strong, versus the origin candle). The POI becomes lifecycle-eligible **only** at this time. Lifecycle availability is **not** backdated to the origin (candidate) candle's close, does not require BOS (undefined in this project and not invoked here), does not wait for a first return to the zone, and does not require entry confirmation. This decision does not change Order Block boundaries, candle-size, displacement, formation, confirmation, or strength formulas.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard, evaluated only from `order_block_available_time` onward.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before `order_block_available_time`.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle, including the RECON-D1 availability-timing decision, is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. Volume/Momentum Proxy Standard minimum thresholds (pre-existing open question) also remain unresolved.

## Overlap with other POIs

Explicitly distinguished from Bearish Engulfing by location (origin of a move vs. within a move).

## Positive example

Yes - captioned chart examples (paragraphs 223-228, 939-941 region). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - geometry/size rule testable now, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `order_block_available_time` onward — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable. Not testable: freshness, mitigation, expiration, and repeated-tap degradation - none of it is defined.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds (Body Efficiency, Close Position, Relative Tick Volume, displacement distance, final price_activity_score/weights) are not yet set; no freshness/mitigation/expiration rule. (General invalidation and lifecycle availability timing are now resolved provisionally via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Order Block formula.)

## Author decision

Inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard, including the RECON-D1 availability-timing decision (`order_block_available_time = qualifying_displacement_candle_close_time`), is approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness, mitigation, expiration, and final proxy thresholds remain pending.

## Approval status

PARTIAL
