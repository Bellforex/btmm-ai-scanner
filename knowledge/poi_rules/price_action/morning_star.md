# Morning Star

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Price Action POI

## Direction

Bullish

## Source pages

"2. Morning star - Evening star" (paragraphs 497-523).

## Book definition

A three-candle reversal pattern at demand/support: strong bearish candle, then a small/doji candle, then a strong bullish candle - a full volume switch from sellers to buyers.

## Required market location

Around a demand zone or support structure.

## Formation conditions

Candle 1: strong bearish. Candle 2: small candle or doji (loss of momentum, indecision). Candle 3: strong bullish.

## Confirmation conditions

The final (third) candle must be very strong, ideally at least 2 to 3 times the size of the middle doji candle. This candle-3 ratio check remains the book's own pattern-confirmation rule; POI lifecycle availability is defined independently below (GROUP3-D9) and coincides with this same close.

## Origin candle or level

The middle doji candle's area is explicitly called out as the POI itself ('the doji area can also serve as a Point of Interest'). **Resolved (GROUP3-D8, Author-Approved):** the POI is the complete High-to-Low range of the qualifying middle Doji candle only — candle 1 and candle 3 are not included in the zone; candle 3 remains pattern-confirmation evidence only.

## Upper boundary

**Resolved (GROUP3-D8, Author-Approved):** Zone Top = Middle Doji High.

## Lower boundary

**Resolved (GROUP3-D8, Author-Approved):** Zone Bottom = Middle Doji Low.

## Wick treatment

Not separately specified for pattern formation. The POI zone (GROUP3-D8) uses the Doji candle's full wick-inclusive High-to-Low range, consistent with the wick-inclusive convention used by every other POI in this project.

## Body treatment

Candle 2 must be "small" or a doji (very small body). **Resolved (GROUP3-D7, Author-Approved — Morning/Evening Star Doji Threshold):** `middle_candle_body_efficiency = ABS(Middle Close − Middle Open) / (Middle High − Middle Low)`. The middle candle is invalid when `Middle High − Middle Low <= 0`. **Standard Doji:** `middle_candle_body_efficiency <= 0.10`. **Strong Doji shape tier:** `middle_candle_body_efficiency <= 0.05`. Morning Star requires a qualifying Doji as candle two; the middle candle may close bullish or bearish, and middle-candle colour is not decisive when the threshold passes.

## Candle-size requirement

Size Ratio (Total Range) of candle 3 vs. candle 2 (the doji) ideally >= 2.0-3.0, per Measurement Standard V1 (candle 3 = key candle, candle 2 = reference candle).

## Volume or momentum proxy

Same open question as Ambiguity 3.

## Trend requirement

Not defined beyond appearing at demand/support.

## Market-structure requirement

Not defined in the book.

## Liquidity requirement

Not defined as Morning-Star-specific.

## Timeframe requirement

Explicitly recommended: 2-hour, 3-hour, 4-hour and above.

## Strength classification

Only the >=2-3x ratio on the final candle is given; no separate standard/strong labels the way Order Block/FVG/Base/Engulfing/Buy-to-Sell get.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved GROUP3-D7, GROUP3-D8, and GROUP3-D9):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, available only from `morning_star_poi_available_time` onward. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Morning Star 3-candle structure, direction, size-ratio, or context formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `BLOCKED_INCOMPLETE_SPECIFICATION` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved GROUP3-D7, GROUP3-D8, and GROUP3-D9, see `knowledge/poi_lifecycle/BLOCKED_CANDLESTICK_POI_COMPLETION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is guaranteed because the qualifying middle Doji candle's `Middle High − Middle Low > 0` is a mandatory validity condition (GROUP3-D7).

**Expected direction:** BULLISH.

**Zone Top mapping:** Middle Doji High (GROUP3-D8, approved).

**Zone Bottom mapping:** Middle Doji Low (GROUP3-D8, approved).

**Entry Boundary mapping:** Zone Top.

**Far Boundary mapping:** Zone Bottom.

**Pattern confirmation time:** `morning_star_pattern_confirmation_time = qualifying_third_candle_close_time` — the close of the third candle, when the >= 2-3x size ratio against the middle Doji is evaluable (GROUP3-D9, approved).

**POI lifecycle availability time (GROUP3-D9, approved):** `morning_star_poi_available_time = qualifying_third_candle_close_time`. Before the qualifying third candle closes: the middle Doji's boundaries may be measurable, but the zone remains inactive, status remains FORMING/UNCONFIRMED, no confirmed Star pattern or POI exists, and no lifecycle event may begin or be backdated. At the third candle's close, every existing mandatory three-candle formation condition is evaluated; the confirmed Star POI is created only when all mandatory conditions pass. If the third candle fails, the candidate is rejected — no confirmed Star pattern, no Star POI, and no lifecycle event are created. No fourth confirmation candle, first return to the zone, Forex price gap, or entry confirmation is required.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard, evaluated only from `morning_star_poi_available_time` onward.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes below Zone Bottom by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or above `Zone Bottom + Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close above `Zone Top + Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Top) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before `morning_star_poi_available_time`.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the completed specification and inherited lifecycle, including the GROUP3-D7, GROUP3-D8, and GROUP3-D9 decisions, are **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. General proxy thresholds (Ambiguity 3, pre-existing open question) also remain unresolved.

## Overlap with other POIs

Uniquely introduces the 'doji as a POI' idea; not stated to overlap formally with any other POI, though a doji zone could visually coincide with a Base if candles cluster similarly. This overlap observation remains open and low-priority; no precedence rule has been created.

## Positive example

Yes (paragraphs 508-516, 522). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - 3-candle structure, final-candle ratio, the Doji body-efficiency threshold (GROUP3-D7), the zone formula (GROUP3-D8), and lifecycle availability timing (GROUP3-D9) are now all testable, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `morning_star_poi_available_time` onward — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable. Not testable: general proxy thresholds (Ambiguity 3), freshness, mitigation, and expiration - none of it is defined.

## Unresolved questions

Which proxy fields to use (Ambiguity 3, general) remain without minimum thresholds; no freshness/mitigation/expiration rule. (Doji body-size threshold, explicit zone formula, and general invalidation are now resolved provisionally via GROUP3-D7, GROUP3-D8, GROUP3-D9, and inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Morning Star 3-candle structure or ratio formula.) GROUP3-D7 through GROUP3-D9 remain Engineering-Provisional and require future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility regimes before they can be considered final.

## Author decision

GROUP3-D7 (Standard/Strong Doji body-efficiency thresholds), GROUP3-D8 (zone = middle Doji's full wick-inclusive range), and GROUP3-D9 (lifecycle availability: `morning_star_poi_available_time = qualifying_third_candle_close_time`) are approved - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness, mitigation, expiration, and general proxy thresholds remain pending.

## Approval status

PARTIAL
