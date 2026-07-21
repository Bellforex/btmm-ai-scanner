# Bearish Pressure Wick

## Alternative book name

"Pressure wick" / "liquidity wick" used interchangeably (paragraphs 359, 369). Same POI, two names.

## Family

Volume-Based POI

## Direction

Bearish (acts as a future selling zone when price returns to it).

## Source pages

"5. Pressure wick" (paragraphs 359-373).

## Book definition

A strong rejection wick where price pushes up into a zone, collects liquidity, and is strongly rejected downward, while the candle still closes with a body that has "good proportion."

## Required market location

Not location-restricted beyond appearing where price has pushed into a zone and been rejected; best identified on 2H/3H/4H and above.

## Formation conditions

Resolved under Pressure Wick Standard V1 — Provisional (Ambiguity 6): on a confirmed closed candle (Total Range = High - Low must be > 0), all of: Upper Wick Share (Upper Wick / Total Range) >= 0.40; Body Efficiency (Body / Total Range) >= 0.25; Upper Wick >= 2x Lower Wick; Bearish Close Position ((High - Close) / Total Range) >= 0.60. The candle may close bullish or bearish - candle colour alone does not determine direction. See knowledge/MEASUREMENT_STANDARDS.md, "Pressure Wick Measurement, Drawing, and Classification Standard" (provisional, pending calibration).

## Confirmation conditions

Resolved under Pressure Wick Standard V1 — Provisional: status is **CANDIDATE** before the candle closes and becomes **CONFIRMED** once the candle closes and all mandatory formation conditions pass. RETESTED, MITIGATED, SWEPT, BROKEN, and EXPIRED are not defined by this decision. The book's own recommendation still applies on top of this: drop to a lower timeframe for confirmation and precise entry once price returns to the wick - do not enter blindly (this remains a qualitative, not formally defined, entry-confirmation rule - see "Still unresolved" below).

**Rejection-criterion clarification (`P0G-B013A`, Author-Approved) — `rejection_criterion_status = EXPLICIT`.** If any mandatory confirmation threshold above (Upper Wick Share, Body Efficiency, Upper Wick vs. Lower Wick ratio, or Bearish Close Position) is not satisfied, the candle does not become a confirmed Bearish Pressure Wick POI. This introduces no new numeric threshold, no new lifecycle state, and no `REJECTED` lifecycle status — it is a documentation clarification of the pre-existing "all of" mandatory-condition structure above. Failure to confirm is not lifecycle invalidation and does not create a POI identity. Standard and Strong thresholds, existing geometry, boundary, availability, and lifecycle inheritance remain unchanged. See `knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md`, "Post-Decision Clarifications — P0G-B006 Interaction Timing and P0G-B013A Rejection Applicability."

## Origin candle or level

The single confirmed wick candle.

## Upper boundary

Resolved under Pressure Wick Standard V1 — Provisional: Zone Top = Candle High.

## Lower boundary

Resolved under Pressure Wick Standard V1 — Provisional: Zone Bottom = MAX(Open, Close). This zone contains only the upper rejection wick; the candle body is never automatically included.

## Wick treatment

Resolved under Pressure Wick Standard V1 — Provisional: Upper Wick = High - MAX(Open, Close); Upper Wick Share = Upper Wick / Total Range must be >= 0.40; Upper Wick must be >= 2x Lower Wick (>= 3x for STRONG). A Wick Dominance Ratio (Rejection Wick / MAX(Opposite Wick, Minimum Price Tick)) provides division-by-zero protection; the Minimum Price Tick is sourced from instrument metadata once the software layer exists. This is still separate from, and does not replace, the standard displacement/size-ratio rule that other POIs use (Measurement Standard V1 SS7 continues to exempt Pressure Wick from that rule).

## Body treatment

Resolved under Pressure Wick Standard V1 — Provisional: Body Efficiency (Body / Total Range) must be >= 0.25 (>= 0.30 for STRONG). This replaces the book's qualitative "good proportion" language with a precise threshold, resolving Ambiguity 6.

## Candle-size requirement

Not a 2x/3x multi-candle displacement ratio (Pressure Wick remains exempted from that rule per Measurement Standard V1 SS7). Range Context is now defined instead: Range Context Ratio = Candidate Total Range / Median Total Range of the previous 20 confirmed candles (current candle excluded) must be >= 1.25 for STRONG classification only (not required for STANDARD). See knowledge/MEASUREMENT_STANDARDS.md, "Pressure Wick Measurement, Drawing, and Classification Standard."

## Volume or momentum proxy

Resolved under Pressure Wick Standard V1 — Provisional: Pressure Wicks now reference the approved Volume, Momentum, and Price-Activity Proxy Standard - price/candle behaviour is primary evidence, tick volume is secondary and never mandatory, missing tick volume never invalidates a Pressure Wick, and external indicators (RSI, MACD, Stochastic, ADX, Rate of Change) are not mandatory. No final price_activity_score formula or new indicator threshold is invented.

## Trend requirement

Not defined as wick-specific.

## Market-structure requirement

Not defined as wick-specific.

## Liquidity requirement

Central to the concept by name; no numeric rule given.

## Timeframe requirement

Explicitly recommended on 2H, 3H, 4H and above for identification. Resolved under Pressure Wick Standard V1 — Provisional: H3, H4, D1, and W1 receive higher-timeframe **contextual priority only** (not a numerical score); a candle that fails the mandatory formation conditions remains invalid regardless of timeframe.

## Strength classification

Resolved under Pressure Wick Standard V1 — Provisional: **STRONG** requires all of Upper Wick Share >= 0.50, Body Efficiency >= 0.30, Upper Wick >= 3x Lower Wick, Bearish Close Position >= 0.70, and Range Context Ratio >= 1.25. A candidate passing the standard formation conditions but not every STRONG condition is **STANDARD**. No additional tiers are defined. Still provisional pending calibration.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** this POI directly inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Pressure Wick formation, confirmation, wick/body, or strength formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `DIRECT_GENERIC_INHERITANCE` (see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is required for valid bounded-zone geometry, per the shared standard — satisfied here because the mandatory Upper Wick Share >= 0.40 condition guarantees a non-zero upper wick separating the Candle High from `MAX(Open, Close)`.

**Expected direction:** BEARISH.

**Zone Top mapping:** Candle High (the already-approved Pressure Wick Standard V1 boundary — unchanged by this inheritance).

**Zone Bottom mapping:** `MAX(Open, Close)` (the already-approved Pressure Wick Standard V1 boundary — unchanged by this inheritance).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard; none are backdated to the original wick candle's time.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved** — the same evidence status as the authoritative shared standard. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, family-specific lifecycle override research, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. Liquidity-collection proof, required approach speed, nearby structural-zone requirement, and retest confirmation (pre-existing open questions for this POI) also remain unresolved.

## Overlap with other POIs

Conceptually close to Shooting Star's long-wick concept. Resolved under Pressure Wick Standard V1 — Provisional: Pressure Wick remains a Volume-Based POI and Shooting Star remains a Price-Action POI; one candle may independently qualify for both labels, which must be preserved separately and never silently merged into one POI type. The Shooting Star rule file itself was not modified by this decision - the wick:body proportions approved here do not apply to Shooting Star (see scope limitation).

## Positive example

Yes (paragraphs 364-368). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - wick/body proportions, close-position threshold, zone-drawing boundaries, strength classification (STANDARD/STRONG), the CANDIDATE/CONFIRMED states, and (via direct inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now all testable. Not testable: proof of liquidity collection, required approach speed, nearby structural-zone requirement, retest confirmation, freshness, partial/full mitigation, expiration, and repeated-tap degradation - none of it is defined.

## Unresolved questions

Proof of liquidity collection; required preceding market approach speed; required nearby support/resistance/trendline/structural zone; retest confirmation; freshness; partial/full mitigation; sweep rules; expiration; trade-entry confirmation; minimum Body Efficiency/Close Position/Relative Tick Volume thresholds from the Volume/Momentum Proxy Standard remain unset. (General invalidation is now resolved provisionally via direct inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Pressure Wick formula.) Pressure Wick Standard V1 and the inherited lifecycle standard are both explicitly provisional and require future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant project timeframes, different sessions, and different volatility regimes before either can be considered final.

## Author decision

Wick/body proportions (Upper Wick Share, Body Efficiency, wick-dominance ratio, Bearish Close Position), zone-drawing boundaries, STANDARD/STRONG strength classification, and CANDIDATE/CONFIRMED states are approved (provisionally) - see Pressure Wick Standard V1 — Provisional. Direct inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard is also approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. Liquidity collection proof, approach speed, structural-zone requirement, retest, freshness, mitigation, sweep, and expiration remain pending.

## Approval status

PARTIAL
