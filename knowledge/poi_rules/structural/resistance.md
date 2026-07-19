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

Not defined in the book. Resolved partially under Support and Resistance Detection and Validation Standard V1 — Provisional: RESISTANCE_BREAK_CANDIDATE is recorded when a confirmed candle closes above Zone Top by more than Horizontal Pierce Tolerance - but this is explicitly **not** final invalidation. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15; propagated following author-approved RECON-D4):** this POI inherits the shared bounded-directional-POI lifecycle for final invalidation — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level. `RESISTANCE_BREAK_CANDIDATE` (Horizontal Pierce Tolerance) is preserved as a separate, deeper, Resistance-specific breach observation and is **not** an alias of `CLOSE_BREACH_CANDIDATE` (Overshoot Tolerance) — only `CLOSE_BREACH_CANDIDATE` starts the shared Reclaim/Invalidation lifecycle; `RESISTANCE_BREAK_CANDIDATE` does not independently start a separate lifecycle and does not independently confirm Genuine Invalidation. Confirmed break, retest, false break, sweep, and role reversal (Resistance becoming Support) remain unresolved and are not defined by this standard. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any origin-eligibility, boundary, touch-tolerance, or DRAFT/CONFIRMED/STRONG classification formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `CONDITIONAL_GENERIC_INHERITANCE` (original classification, see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`) → **`GENERIC_LIFECYCLE_INHERITANCE_APPROVED`** (this propagation, following author-approved RECON-D4, see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone). `Zone Top > Zone Bottom` is guaranteed by the approved `Horizontal Zone Depth = MAX(2 × Minimum Price Tick, 0.10 × Creator Reference ATR)` formula, which is always positive.

**Expected direction:** BEARISH.

**Zone Top mapping:** Origin Swing High Pivot Price (the already-approved Resistance boundary — unchanged by this inheritance, used exactly as documented above).

**Zone Bottom mapping:** `Zone Top − Horizontal Zone Depth` (unchanged by this inheritance).

**Entry Boundary mapping:** Zone Bottom.

**Far Boundary mapping:** Zone Top.

**Lifecycle availability time:** unchanged from the already-approved Support and Resistance Detection and Validation Standard — DRAFT_RESISTANCE (and its fixed Zone Top/Bottom) becomes available only after the origin-reaction classification is complete, never exposed historically at the original pivot time. No separate RECON-D availability decision was required for Support/Resistance; this timing was already explicit and sufficient (see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`, Section 12).

**Dual-event distinction (RECON-D4, approved):** two separate, non-aliased breach events are preserved:

| Event | Condition | Tolerance | Effect |
|---|---|---|---|
| `CLOSE_BREACH_CANDIDATE` (generic lifecycle trigger) | Confirmed close above Zone Top by more than the approved generic Overshoot Tolerance | `Overshoot Tolerance = MAX(2×MinTick, MIN(0.10×ATR14, 0.25×ZoneHeight))` | **Starts** the shared three-bar Reclaim window and the full Reclaim/Displacement/False-Invalidation/Genuine-Invalidation lifecycle. |
| `RESISTANCE_BREAK_CANDIDATE` (family-specific deeper observation) | The already-approved Resistance condition: confirmed close above Zone Top by more than Horizontal Pierce Tolerance | `Horizontal Pierce Tolerance = MAX(2×MinTick, 0.15×ATR14)` (unchanged) | Deeper Resistance-specific breach evidence only. Does **not** start a separate lifecycle, does **not** independently confirm Genuine Invalidation, and does **not** override or replace `CLOSE_BREACH_CANDIDATE`. |

Both events and both tolerance formulas are preserved unmodified and evaluated independently; neither formula was changed. Genuine Invalidation still requires the approved three-bar Sustained Breach sequence under `CLOSE_BREACH_CANDIDATE`, regardless of whether `RESISTANCE_BREAK_CANDIDATE` has also fired.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard. `RESISTANCE_BREAK_CANDIDATE` remains a separate, pre-existing Ambiguity-12 event, not one of these ten states.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes above Zone Top by more than the approved Overshoot Tolerance (see dual-event table above).

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or below `Zone Top − Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close below `Zone Bottom − Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. A later valid reaction in the same general price area requires a new POI record and a new POI ID, per the pre-existing initial-creator principle. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Bottom) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count. This is separate from, and does not replace, the pre-existing DRAFT/CONFIRMED/STRONG_RESISTANCE touch-count classification.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard, consistent with the pre-existing Resistance non-repainting behavior (origin/ATR/boundaries never move or get recalculated).

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle, including the RECON-D4 dual-event decision, is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved** — the same evidence status as the pre-existing Support and Resistance Detection and Validation Standard. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** freshness, expiration, repeated-touch degradation, partial/full mitigation, retest, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance. Role reversal (Resistance becoming Support), zone merging, zone ranking, HH/HL/LH/LL, BOS/CHoCH, and BTMM state transitions (Ambiguity 14, pre-existing open questions) also remain unresolved.

## Overlap with other POIs

Related to Trendline (diagonal resistance) and to the Previous/Current Period High-Low family. Resolved under Support and Resistance Detection and Validation Standard V1 — Provisional: **Equal Highs relationship** - Equal Highs != Resistance; the same confirmed meaningful swings may independently satisfy both standards, and both labels are preserved when that happens (the approved Equal Highs/Equal Lows formulas, Ambiguity 5, are unchanged). **Trendline horizontal-candidate relationship** - a Trendline HORIZONTAL_CANDIDATE (Ambiguity 11) may be evaluated under this Resistance standard but never automatically becomes Resistance; it must independently pass origin eligibility, creator boundary, origin reaction, touch tolerance, distinct-touch, and confirmation requirements (the approved Trendline formulas/thresholds are unchanged). Non-repainting behavior: once created, origin swing ID/price/time, Creator Reference ATR, Zone Top/Bottom, and zone depth never move or get recalculated; later touches never recenter/resize the zone; a later origin creates a new zone candidate. Multiple Resistance candidates may coexist per timeframe - nearby zones are never silently merged, and no BEST_RESISTANCE/PRIMARY_ZONE/ranking/composite score is created.

## Positive example

Yes (paragraphs 595-602). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - origin eligibility (via the Meaningful Swing Standard), the initial-creator rule, fixed zone boundaries (Zone Top/Bottom/Depth), origin-reaction gating (via the POI Reaction Strength Standard), Touch/Pierce tolerances, distinct-touch confirmation, DRAFT/CONFIRMED/STRONG progression, RESISTANCE_BREAK_CANDIDATE detection, non-repainting availability, and (via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now all testable. Not testable: confirmed break, retest, false break, role reversal, freshness, repeated-touch degradation, partial/full mitigation, expiration, zone merging, zone ranking, entry confirmation (none defined); HH/HL/LH/LL, BOS, CHoCH (not defined, out of scope). The underlying swing standard's material-breach sub-rule (Ambiguity 10) and the POI Reaction Strength Standard's own thresholds are also inherited dependencies.

## Unresolved questions

Confirmed break; retest; false break; role reversal (Resistance becoming Support); freshness; repeated-touch degradation; partial/full mitigation; expiration; zone merging; zone ranking; entry confirmation; HH/HL/LH/LL; BOS/CHoCH; BTMM state transitions (Ambiguity 14, unchanged). Support and Resistance Detection and Validation Standard V1 is explicitly Author-Approved but Engineering-Provisional - NOT YET empirically calibrated or out-of-sample validated, and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, relevant timeframes, sessions, and volatility/trend regimes before it can be considered final or production-approved. (Final invalidation and reclaim are now resolved provisionally via inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard, with RESISTANCE_BREAK_CANDIDATE preserved as a separate deeper observation — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Resistance formula.)

## Author decision

**Evidence status: Author-Approved, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, NOT Production-Approved.** Origin eligibility, initial-creator principle, Creator Reference ATR, Horizontal Zone Depth, fixed Zone Top/Bottom boundaries, origin-reaction requirement, Touch/Pierce tolerances, distinct-touch confirmation, DRAFT/CONFIRMED/STRONG classification, RESISTANCE_BREAK_CANDIDATE detection, non-repainting behavior, multiple-zone handling, and the Equal Highs/Trendline-horizontal-candidate relationships are approved (provisionally) - see Support and Resistance Detection and Validation Standard V1 — Provisional. Inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard, including the RECON-D4 dual-event decision (RESISTANCE_BREAK_CANDIDATE preserved as a separate, non-aliased, family-specific deeper breach observation; CLOSE_BREACH_CANDIDATE alone starts the shared lifecycle), is also approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. Confirmed break, retest, false break, role reversal, freshness, mitigation, expiration, zone merging, zone ranking, and entry confirmation remain pending.

## Approval status

PARTIAL
