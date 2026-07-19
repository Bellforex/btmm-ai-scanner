# Base Rally

## Alternative book name

"Rally-Base-Rally" is used in the introductory chapter (paragraphs 187, 342), while "Base Rally" is the label used in the formal validation appendix (paragraphs 972 onward). Same concept, two labels used in different parts of the same book - recorded as an internal naming duplication, not two POIs.

## Family

Volume-Based POI

## Direction

Bullish

## Source pages

"4. Rally base rally / Drop base drop" (paragraphs 342-358); formal appendix "Base Rally Validation Conditions" (paragraphs 972-993) within "Base Drop and Base Rally POI Validation Conditions" (paragraphs 942-1049).

## Book definition

Price makes a strong upward move, pauses in a small horizontal 'base,' then breaks out again strongly upward; the base itself is the POI.

## Required market location

The base must be a distinct pause/consolidation after an existing bullish move, before the breakout.

## Formation conditions

Resolved under Base Formation Standard V1 — Provisional (Ambiguity 4): 2 to 6 consecutive confirmed closed candles (more than 6 is initially classified as consolidation, not a precise Base Rally POI); every base candle's Total Range <= 0.50x the departure candle's Total Range (<= 0.3333x for Strong Base), compared against the largest base candle; Base Height (Highest High - Lowest Low of all base candles) <= 0.75x ATR(14) (same symbol/timeframe) AND <= 0.60x the departure candle's Total Range; Base Midpoint Drift (using candle midpoints = (High+Low)/2) <= 0.25x Base Height, to reject a directional staircase; and, for each consecutive base-candle pair, Overlap Ratio >= 0.50. See knowledge/MEASUREMENT_STANDARDS.md, "Base Formation, Compactness, and Departure Standard" (provisional, pending calibration against expert-approved/rejected examples across symbols, timeframes, and volatility regimes).

## Confirmation conditions

Resolved under Base Formation Standard V1 — Provisional: the departure candle must be bullish, close above the base's Highest High (Departure Close > Highest High of all base candles), be at least 2x the largest base candle (>=3x for Strong Base), and separate decisively from the base. Departure-candle momentum/volume evidence is evaluated using the approved Volume, Momentum, and Price-Activity Proxy Standard (no separate momentum rule invented here).

## Origin candle or level

The full group of 2 to 6 base candles (not a single candle) - the candle-count bounds are now fixed by Base Formation Standard V1 — Provisional.

## Upper boundary

Base High = highest high of all base candles (unchanged formula; the candle group is now bounded to 2-6 candles by Base Formation Standard V1 — Provisional).

## Lower boundary

Base Low = lowest low of all base candles (unchanged formula; same 2-6 candle-count bound applies).

## Wick treatment

Base High/Low both explicitly use candle highs/lows (wicks included), matching Measurement Standard V1 SS5.

## Body treatment

Not defined as a separate zone-drawing rule (only Total Range is used for Base High/Low).

## Candle-size requirement

Departure candle Size Ratio >= 2.0 (standard) / >= 3.0 (strong) vs. the LARGEST individual base candle (not an average). Formula: Bullish Departure Candle Size >= 2x (or 3x) Size of the Largest Base Candle. Resolved under Candle Measurement Standard V1 SS7 (Base Rally/Drop row) and Small Candle Standard V1 (Ambiguity 2). The number of candles forming a valid base (2-6) and the base's compactness (size, height, midpoint drift, overlap) are now also resolved under Base Formation Standard V1 — Provisional (Ambiguity 4) - see knowledge/MEASUREMENT_STANDARDS.md, "Base Formation, Compactness, and Departure Standard." This standard remains provisional pending calibration against expert-approved/rejected examples.

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bullish Close Position of the departure candle), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. Base Formation Standard V1 — Provisional explicitly incorporates this proxy standard as the departure candle's momentum evidence (no separate momentum rule invented for bases). See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these fields have been set yet.

## Trend requirement

Must follow an existing strong upward move - stated explicitly.

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

Not defined in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved RECON-D2):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, available only from `base_available_time` onward. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Base Formation Standard rule (candle count, compactness, height, drift, overlap, departure, or strength).

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `CONDITIONAL_GENERIC_INHERITANCE` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved RECON-D2, see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is required and is guaranteed by the Base Formation Standard's Base Height requirement (a positive-height base of 2-6 candles).

**Expected direction:** BULLISH.

**Zone Top mapping:** Base High = highest high of all base candles (the already-approved Base Rally boundary — unchanged by this inheritance, used exactly as documented above).

**Zone Bottom mapping:** Base Low = lowest low of all base candles (unchanged by this inheritance).

**Entry Boundary mapping:** Zone Top.

**Far Boundary mapping:** Zone Bottom.

**Lifecycle availability time (RECON-D2, approved):** `base_available_time = qualifying_departure_candle_close_time` — the close time of the first confirmed departure candle satisfying the approved Base Formation Standard (bullish close, close above Base High, Size Ratio >= 2.0/3.0 versus the largest base candle, decisive separation from the base). The POI becomes lifecycle-eligible **only** at this time — **not** at the first base candle, **not** at the final base candle, and **not** at a future first return to the zone. This decision does not change base candle count, compactness, Base Height, Overlap Ratio, departure-size ratio, directional close requirements, boundaries, or strength classification.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard, evaluated only from `base_available_time` onward.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes below Zone Bottom by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or above `Zone Bottom + Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close above `Zone Top + Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Top) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before `base_available_time`.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle, including the RECON-D2 availability-timing decision, is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. General proxy thresholds (pre-existing open question) also remain unresolved.

## Overlap with other POIs

Shares the 'small candles' language with Fair Value Gap's pre-displacement candles, but Base Rally requires a horizontally-aligned multi-candle base rather than a 3-candle gap.

## Positive example

Yes (paragraphs 347-352, 358, 1050-1053). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption (weak base is described narratively only).

## Machine-testable criteria

Partial - Base High/Low, candle count (2-6), base-candle size, Base Height, midpoint drift, overlap ratio, and departure-candle ratio/close-outside-base are now all testable under Base Formation Standard V1 — Provisional, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `base_available_time` onward — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable. Not testable: freshness, mitigation, and expiration - none of it is defined, and the provisional thresholds themselves still await calibration.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds (Body Efficiency, Close Position, Relative Tick Volume, price_activity_score) are not yet set; no freshness/expiration rule; Base Formation Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, H3/H4/D1/W1, and different volatility regimes before it can be considered final. (General invalidation and lifecycle availability timing are now resolved provisionally via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Base Formation formula.)

## Author decision

Base candle count (2-6), base-candle size/height/drift/overlap, and departure-candle confirmation are approved (provisionally) - see Base Formation Standard V1 — Provisional. Inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard, including the RECON-D2 availability-timing decision (`base_available_time = qualifying_departure_candle_close_time`), is also approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness/mitigation/expiration and final proxy thresholds remain pending.

## Approval status

PARTIAL
