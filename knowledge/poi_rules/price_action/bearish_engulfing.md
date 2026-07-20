# Bearish Engulfing Candle

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Price Action POI

## Direction

Bearish

## Source pages

"Bullish engulfing candle - Bearish engulfing candle" intro/selection (paragraphs 413-474); formal appendix "Bearish Engulfing Pattern" validation (paragraphs 765-798, 799-828).

## Book definition

A two-candle reversal pattern where a larger bearish candle's body covers/engulfs the prior smaller bullish candle's body, showing buyers losing control to sellers.

## Required market location

Must appear WITHIN/in the middle of an existing price movement - distinguishing it from Order Block.

## Formation conditions

Previous candle relatively small and bullish; engulfing candle bearish and larger, covering the previous candle's body.

## Confirmation conditions

Engulfing candle must close bearish (close below open) with aggressive selling pressure; stronger version also engulfs the previous candle's wicks.

## Origin candle or level

The two-candle pair.

## Upper boundary

**Resolved (GROUP3-D1, Author-Approved):** Zone Top = High of the first (smaller, engulfed bullish) candle. The POI is the complete High-to-Low range of the first candle that is engulfed by the qualifying second (engulfing) candle — not the engulfing candle itself, and not the combined two-candle range.

## Lower boundary

**Resolved (GROUP3-D1, Author-Approved):** Zone Bottom = Low of the first (smaller, engulfed bullish) candle. The second (engulfing) candle is preserved as pattern-confirmation and displacement evidence only — it is not included in the POI boundary.

## Wick treatment

Body-engulfment is the baseline rule; stronger version also engulfs wicks.

## Body treatment

Core rule: the engulfing candle's body must cover/engulf the previous candle's body.

## Candle-size requirement

Size Ratio (Total Range) >= 2.0 (standard) / >= 3.0 (strong) vs. the previous candle, per Measurement Standard V1. The previous (engulfed) candle's "smallness" is now also governed by Small Candle Standard V1 (Ambiguity 2, resolved): its Total Range <= 0.50x the engulfing candle's Total Range (standard) / <= 0.3333x (strong), with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the immediately preceding candle. See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position of the engulfing candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

Stronger after a pullback in a downtrend - contextual.

## Market-structure requirement

Explicit warning against trading every bearish engulfing pattern without checking market structure, trend, liquidity, and location.

## Liquidity requirement

Stronger at resistance/supply/POI/liquidity sweep/premium zone - contextual, no formal numeric rule.

## Timeframe requirement

Explicit ranking: Daily > 4H > 1H > 15-minute.

## Strength classification

Standard (>=2x) / Strong (>=3x); Higher-timeframe vs. Lower-timeframe.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved GROUP3-D1 and GROUP3-D2):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, available only from `engulfing_poi_available_time` onward. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Engulfing formation, size-ratio, strength, location, or body-engulfment formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `BLOCKED_INCOMPLETE_SPECIFICATION` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved GROUP3-D1 and GROUP3-D2, see `knowledge/poi_lifecycle/BLOCKED_CANDLESTICK_POI_COMPLETION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is guaranteed because the first candle's High and Low are, by definition, distinct prices for any candle with positive Total Range.

**Expected direction:** BEARISH.

**Zone Top mapping:** High of the first (smaller, engulfed bullish) candle (GROUP3-D1, approved).

**Zone Bottom mapping:** Low of the first (smaller, engulfed bullish) candle (GROUP3-D1, approved).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Pattern confirmation time:** `engulfing_pattern_confirmation_time = qualifying_engulfing_candle_close_time` — the close of the second (engulfing) candle, when direction, body-engulfment, and the 2x/3x size ratio are all evaluable (GROUP3-D2, approved).

**POI lifecycle availability time (GROUP3-D2, approved):** `engulfing_poi_available_time = qualifying_engulfing_candle_close_time`. Before the second candle closes: status remains FORMING/UNCONFIRMED, the first candle's prices may be measurable but no confirmed Engulfing POI exists, and no lifecycle event may begin or be backdated. At the second candle's close, all existing mandatory Engulfing conditions are evaluated; the confirmed POI is created only if every mandatory condition passes. If the second candle fails, the candidate is rejected — no Engulfing POI and no lifecycle event are created. No third confirmation candle, first return to the zone, BOS, or entry confirmation is required.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard, evaluated only from `engulfing_poi_available_time` onward.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before `engulfing_poi_available_time`.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the completed specification and inherited lifecycle, including the GROUP3-D1 and GROUP3-D2 decisions, are **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. General proxy thresholds (pre-existing open question) also remain unresolved.

## Overlap with other POIs

Explicitly distinguished from Order Block by location.

## Positive example

Yes (paragraphs 460-467, 474, 828). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - engulfment + size-ratio rule testable now, zone boundaries and lifecycle availability timing are now testable under GROUP3-D1/GROUP3-D2 (see "Shared POI Boundary Lifecycle Inheritance" above), and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `engulfing_poi_available_time` onward) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable. Not testable: minimum proxy thresholds (Ambiguity 3, general), freshness, mitigation, and expiration - none of it is defined.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds are not yet set; no freshness/mitigation/expiration rule. (Zone-drawing formula, lifecycle availability timing, and general invalidation are now resolved provisionally via GROUP3-D1, GROUP3-D2, and inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Engulfing formation formula.)

## Author decision

GROUP3-D1 (zone boundary source: first/engulfed candle's range) and GROUP3-D2 (lifecycle availability: `engulfing_poi_available_time = qualifying_engulfing_candle_close_time`) are approved - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness, mitigation, expiration, and general proxy thresholds remain pending.

## Approval status

PARTIAL
