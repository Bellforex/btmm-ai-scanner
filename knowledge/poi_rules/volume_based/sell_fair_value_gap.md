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

Same narrow note as Buy FVG: trailing-candle size does not invalidate the gap; no general invalidation rule given. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved RECON-D3 and RECON-D5):** this POI inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, using the generic Contact and Overshoot Tolerances **without modification** (RECON-D3), available only from `fvg_available_time` (third candle close, RECON-D5) onward. This narrow trailing-candle-size note is orthogonal to, and not superseded or altered by, the inherited lifecycle. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any FVG gap-geometry, displacement, or strength formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `CONDITIONAL_GENERIC_INHERITANCE` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved RECON-D3 and RECON-D5, see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is structurally guaranteed by the strict three-candle FVG gap-geometry rule itself (High of Candle 3 < Low of Candle 1, so Zone Top = High of Candle 3 > Zone Bottom = Low of Candle 1).

**Expected direction:** BEARISH.

**Zone Top mapping:** High of the third candle (the already-approved Sell FVG boundary — unchanged by this inheritance, used exactly as documented above).

**Zone Bottom mapping:** Low of the first candle (unchanged by this inheritance).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Lifecycle availability time (RECON-D5, approved):** `fvg_available_time = third_candle_close_time`. A Fair Value Gap is **not valid** while the third candle is still forming — the third candle that completes the strict three-candle FVG structure must close before the FVG can be validated, and this is valid only when the approved strict three-candle FVG geometry (`Zone Top > Zone Bottom`) still exists at that confirmed close. Before the third candle closes: FVG status remains **FORMING/UNCONFIRMED**, no confirmed FVG POI exists, no lifecycle evaluation may begin, no reclaim or invalidation evaluation may begin, no BTMM setup may use the FVG, and no later-interaction (repeated-tap) tracking may begin. If the required gap no longer exists when the third candle closes, the FVG candidate is **rejected** — no confirmed FVG POI and no lifecycle events are created. The FVG becomes available to downstream logic only after all of: (1) the third candle closes, (2) strict three-candle geometry remains valid, (3) Zone Top and Zone Bottom are fixed, and (4) all existing approved FVG formation requirements pass. This decision was made because the pre-existing "Confirmation conditions" text establishes only that gap geometry is the formation-confirmation rule — it does not, by itself, state that this same moment governs *lifecycle* availability for the separate Boundary Breach, Reclaim and Invalidation Standard; RECON-D5 makes that mapping an explicit, Author-Approved decision rather than an unstated inference. No lifecycle event may be backdated to before `fvg_available_time`. This decision does not change strict three-candle FVG geometry, Buy or Sell FVG boundaries, displacement requirements, candle-size requirements, strength classification, the generic Contact/Overshoot Tolerances, the approved no-minimum-width decision (RECON-D3), reclaim formulas, invalidation formulas, entry rules, or risk rules.

**Narrow-zone treatment (RECON-D3, approved):** the generic Contact Tolerance and Overshoot Tolerance are inherited **unmodified** — no minimum FVG width, no FVG-specific lifecycle tolerance, no narrow-zone rejection rule, and no narrow-zone invalidation exemption are introduced. A valid narrow FVG remains lifecycle-eligible whenever the existing strict three-candle FVG geometry is valid, `Zone Top > Zone Bottom`, and ATR/instrument metadata are valid. The approved `MAX(2 × Minimum Price Tick, ...)` floor in both tolerance formulas remains the market-resolution safeguard for narrow gaps; it is not changed or supplemented by this inheritance.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved (unmodified) Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, and never before the third candle's close.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle, including the RECON-D3 narrow-zone decision and the RECON-D5 availability-timing decision, is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved**. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-tap degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. General proxy thresholds and BTMM-anchor-dependent measurements (Ambiguity 14, pre-existing open questions) also remain unresolved.

## Overlap with other POIs

Related to Order Block via the shared displacement-candle concept; distinguished by the 3-candle gap geometry.

## Positive example

Yes (paragraphs 247-252, 287, 726-730). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - the 3-candle gap geometry, Range Speed Ratio, Displacement Expansion Ratio, Body Efficiency, and Bearish Close Position (including the STANDARD FAST / STRONG FAST tiers) are now all testable under Market Speed and Displacement Standard V1 — Provisional, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard from `fvg_available_time` — the confirmed third candle's close under RECON-D5 — onward — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now also testable, including for narrow-gap zones. Not testable: BTMM Approach/Reaction Speed and POI Dwell for this POI depend on expert-labelled anchors (Ambiguity 14, unresolved); minimum proxy thresholds (Body Efficiency/Close Position/Relative Tick Volume outside the speed tiers) remain unset; freshness, mitigation, and expiration remain undefined.

## Unresolved questions

Which proxy fields to use is resolved (Ambiguity 3), but their minimum thresholds outside the speed tiers are not yet set; no freshness/expiration rule beyond the one narrow trailing-candle-size note above; Ambiguity 14 (BTMM state machine) and the automatic anchors it would enable remain unresolved and were not touched by this decision; Market Speed and Displacement Standard V1 is explicitly provisional and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility regimes before it can be considered final. (General invalidation, narrow-zone tolerance treatment, and lifecycle availability timing are now resolved provisionally via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any FVG formula.)

## Author decision

Range Speed Ratio, Displacement Expansion Ratio (3-candle pre-displacement window), Body Efficiency, Bearish Close Position, and STANDARD FAST/STRONG FAST classification are approved (provisionally) - see Market Speed and Displacement Standard V1 — Provisional. This is layered on top of, and does not replace, the strict three-candle FVG gap geometry. Inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard, including the RECON-D3 narrow-zone decision (generic tolerances applied unmodified, no minimum width invented) and the RECON-D5 availability-timing decision (`fvg_available_time = third_candle_close_time`, candidate rejected if the gap no longer exists at that close), is also approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. Freshness/mitigation/expiration, general proxy thresholds, and BTMM-anchor-dependent measurements (Ambiguity 14) remain pending.

## Approval status

PARTIAL
