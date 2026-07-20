# Shooting Star

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Price Action POI

## Direction

Bearish

## Source pages

"2. Hammer - Shooting star" (paragraphs 475-496).

## Book definition

A single-candle rejection pattern with a long upper wick and small body, appearing at a resistance zone: buyers pushed price up, sellers rejected it strongly back down.

## Required market location

Around a resistance zone.

## Formation conditions

Long upper wick, small body. **Resolved (GROUP3-D3, Author-Approved — Hammer and Shooting Star Quantitative Formation Thresholds):** on a confirmed closed candle (Total Range = High − Low must be > 0), Standard Shooting Star requires all of: Upper Wick Share (Upper Wick / Total Range) >= 0.60, Body Efficiency (Body / Total Range) <= 0.30, Lower Wick Share (Lower Wick / Total Range) <= 0.10, where Body = ABS(Close − Open), Upper Wick = High − MAX(Open, Close), Lower Wick = MIN(Open, Close) − Low. **Strong Shape tier:** Upper Wick Share (Rejection Wick Share) >= 0.70, Body Efficiency <= 0.20, Lower Wick Share (Opposite Wick Share) <= 0.05. These thresholds are a distinct, Hammer/Shooting-Star-specific field, not a merge with or replacement of the Pressure Wick Standard V1 formulas.

## Confirmation conditions

If the Shooting Star closes bearish (red), it is a stronger standalone sell signal. If it closes bullish (blue/green), the book explicitly says do not sell immediately - wait for a bearish confirmation candle. This "wait for a confirmation candle" language remains an entry-timing observation only (per GROUP3-D6) and does not gate POI lifecycle availability, which is defined independently below.

## Origin candle or level

The single Shooting Star candle.

## Upper boundary

**Resolved (GROUP3-D5, Author-Approved):** Zone Top = Candle High. The zone uses the rejection wick only; the candle body remains pattern and signal evidence but is not included in the POI zone.

## Lower boundary

**Resolved (GROUP3-D5, Author-Approved):** Zone Bottom = MAX(Open, Close).

## Wick treatment

The long upper wick is the primary rejection signal. **Resolved (GROUP3-D3):** Upper Wick = High − MAX(Open, Close); Upper Wick Share = Upper Wick / Total Range must be >= 0.60 (standard) / >= 0.70 (strong, as Rejection Wick Share). Lower Wick Share (Opposite Wick Share) must be <= 0.10 (standard) / <= 0.05 (strong).

## Body treatment

Body must be "small." **Resolved (GROUP3-D3, Author-Approved):** Body Efficiency (Body / Total Range) must be <= 0.30 (standard) / <= 0.20 (strong), where Body = ABS(Close − Open). This is a Hammer/Shooting-Star-specific field, kept distinct from the Pressure Wick Standard V1's own Body Efficiency thresholds even though it reuses the same measurement concept.

## Candle-size requirement

Not defined as a multi-candle size-ratio rule (this POI's validity rule is about single-candle wick:body shape and close color, not a candle-to-candle size comparison). Unaffected by GROUP3-D3, which defines only the wick:body shape thresholds, not a multi-candle comparison.

## Volume or momentum proxy

Not defined in the book.

## Trend requirement

Not defined beyond appearing 'around a resistance zone.'

## Market-structure requirement

Not defined in the book.

## Liquidity requirement

Not defined as Shooting-Star-specific.

## Timeframe requirement

Not defined for this POI.

## Strength classification

Close-color rule (bearish close = stronger signal; bullish close = wait for confirmation) remains the book's own qualitative signal-strength rule, unchanged. **Resolved (GROUP3-D3, Author-Approved):** a numeric Standard/Strong shape classification is now also defined — **STANDARD** requires Upper Wick Share >= 0.60, Body Efficiency <= 0.30, Lower Wick Share <= 0.10; **STRONG** requires Upper Wick Share >= 0.70, Body Efficiency <= 0.20, Lower Wick Share <= 0.05. The close-color rule and the shape-based Standard/Strong tier are independent, non-overriding signals — a candle may be shape-STRONG with a bullish close, or shape-STANDARD with a bearish close; neither is collapsed into the other.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved GROUP3-D3, GROUP3-D4, GROUP3-D5, and GROUP3-D6):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, available only from `shooting_star_poi_available_time` onward. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Shooting Star shape, direction, or close-color signal rule.

## Expiration

NOT DEFINED IN BOOK.

## POI role (GROUP3-D4, Author-Approved)

**Signal Role:** bearish rejection/reversal evidence — unchanged from the book's own qualitative description. **POI Role:** bounded directional POI (this decision resolves the GROUP3-D4 gating question in favor of a bounded outcome). **Expected Direction:** BEARISH. Pattern validity (the shape/ratio thresholds above) remains conceptually separate from POI lifecycle validity (below), which remains separate from entry validity (the close-color signal-strength rule); a valid pattern does not automatically create an entry. Shooting Star may coexist with a Bearish Pressure Wick label or another label on the same candle when each specification independently passes its own thresholds — no label precedence is created, and neither label is merged into or overridden by the other.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `BLOCKED_INCOMPLETE_SPECIFICATION` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved GROUP3-D3 through GROUP3-D6, see `knowledge/poi_lifecycle/BLOCKED_CANDLESTICK_POI_COMPLETION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is guaranteed because the mandatory Upper Wick Share >= 0.60 condition ensures a non-zero upper wick separating Candle High from `MAX(Open, Close)`.

**Expected direction:** BEARISH.

**Zone Top mapping:** Candle High (GROUP3-D5, approved — rejection wick only, body excluded).

**Zone Bottom mapping:** `MAX(Open, Close)` (GROUP3-D5, approved).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Pattern confirmation time:** `shooting_star_pattern_confirmation_time = qualifying_shooting_star_candle_close_time` — the close of the Shooting Star candle, when Total Range validity, the GROUP3-D3 shape thresholds, and direction/colour/context requirements are all evaluable (GROUP3-D6, approved).

**POI lifecycle availability time (GROUP3-D6, approved):** `shooting_star_poi_available_time = qualifying_shooting_star_candle_close_time`. Before the pattern candle closes: status remains FORMING/UNCONFIRMED, no confirmed pattern or POI exists, and no lifecycle event may begin or be backdated. At the candle's close, valid Total Range, the approved rejection-wick threshold, Body Efficiency, the opposite-wick threshold, existing direction/colour/context requirements, and the approved rejection-wick boundaries are all verified; if any mandatory condition fails, the candidate is rejected — no pattern, no POI, and no lifecycle event are created. No later confirmation candle, first return, or entry confirmation is required for POI lifecycle purposes (the book's own "wait for a confirmation candle" language remains an entry-timing rule only, per GROUP3-D6, and is not converted into a lifecycle-availability requirement).

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard, evaluated only from `shooting_star_poi_available_time` onward.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before `shooting_star_poi_available_time`.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the completed specification and inherited lifecycle, including the GROUP3-D3 through GROUP3-D6 decisions, are **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance.

## Overlap with other POIs

Shares the long-wick concept with Pressure Wick/Liquidity Wick. The book classifies Shooting Star as Price Action and Pressure Wick as Volume-Based; **resolved (GROUP3-D4, Author-Approved, consistent with the already-approved Pressure Wick Standard V1 label-preservation rule):** one candle may independently qualify for both a Shooting Star label and a Bearish Pressure Wick label — the two labels are preserved separately and never silently merged into one POI type, and neither automatically overrides the other.

## Positive example

Yes (paragraphs 490-496). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - wick:body ratio (GROUP3-D3), zone-drawing boundaries (GROUP3-D5), POI role (GROUP3-D4), and lifecycle availability timing (GROUP3-D6) are now all testable, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `shooting_star_poi_available_time` onward — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable. Not testable: freshness, mitigation, and expiration - none of it is defined.

## Unresolved questions

Freshness; partial/full mitigation; expiration; trade-entry confirmation. (Wick:body ratio, zone-drawing formula, POI role, overlap with Pressure Wick classification, and general invalidation are now resolved provisionally via GROUP3-D3, GROUP3-D4, GROUP3-D5, GROUP3-D6, and inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above.) GROUP3-D3 through GROUP3-D6 remain Engineering-Provisional and require future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility regimes before they can be considered final.

## Author decision

GROUP3-D3 (Standard/Strong wick:body shape thresholds), GROUP3-D4 (POI role = bounded directional POI), GROUP3-D5 (zone = rejection wick only: High to `MAX(Open,Close)`), and GROUP3-D6 (lifecycle availability: `shooting_star_poi_available_time = qualifying_shooting_star_candle_close_time`) are approved - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness, mitigation, and expiration remain pending.

## Approval status

PARTIAL
