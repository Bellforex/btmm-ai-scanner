# POI Freshness and Age Standard

## 1. Purpose

This standard resolves `P0G-B006` (POI freshness and mitigation model) and `P0G-B007` (POI expiration-by-age model) from `knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md`. It defines a deliberately minimal, **observational-only** freshness and age model for POIs: whether a POI has been interacted with, and how old it is, tracked descriptively, with no automatic weakening, invalidation, or expiration derived from either fact. It does not define partial mitigation, full mitigation, degradation, or any age-based expiration threshold — those remain unresolved and out of scope for this decision.

## 2. Scope

Applies to every POI with an approved availability time (`*_available_time` fields already defined per POI in the individual rule files) — this includes all 18 bounded directional POIs propagated under the shared POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`), as well as Equal Highs, Equal Lows, Bullish Trendline, and Bearish Trendline, for which this standard's descriptive age fields apply but freshness/expiration are explicitly `NOT_AUTOMATICALLY_EVALUATED` while their specialized lifecycles remain deferred (see `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md` SS11 below and each structure's own "Phase 0G Specialized Lifecycle Deferral" section). Does not apply to Swing High, Swing Low, or the 12 Previous/Current Period High/Low variants, which are single price levels, not persistent zones (`NOT_APPLICABLE`).

## 3. Evidence Status

**AUTHOR-APPROVED. ENGINEERING-PROVISIONAL. NOT YET EMPIRICALLY CALIBRATED. NOT YET OUT-OF-SAMPLE VALIDATED. NOT PRODUCTION-APPROVED.** This standard is not a book quotation — freshness and age tracking are not addressed anywhere in the private source material — and must not be presented as a proven or universal trading rule. It is a deliberately minimal, descriptive-only model; deeper mitigation/degradation research remains a separate, future, empirical-calibration task.

## 4. Definitions

- **Freshness** — whether a POI has been touched (interacted with) since it became available, tracked as one of a small set of observational states (SS5-SS8).
- **Age** — elapsed confirmed-bar count and elapsed time since a POI's approved availability time, tracked descriptively (SS13).
- **Descriptive** — a field that is recorded and exposed for downstream review/analysis but never itself triggers an automatic change to strength, validity, lifecycle status, BTMM eligibility, entry validity, invalidation, or expiration.

## 5. FRESH State

A bounded directional POI's `freshness_status` is `FRESH` from its own approved availability time (e.g. `order_block_available_time`, `fvg_available_time`, `engulfing_poi_available_time`, etc. — each already defined per POI) until its first qualifying interaction. `FRESH` carries no numeric score and does not by itself imply strength, validity, or entry eligibility.

## 6. INTERACTED State

`freshness_status` changes to `INTERACTED` on the POI's first qualifying interaction (SS7). Once `INTERACTED`, this state is permanent for that POI identity (SS9) — it is not re-evaluated per subsequent tap, and it does not, by itself, distinguish `INITIAL_TAP` from `REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS` (that classification remains the separate, unchanged responsibility of the POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard).

## 7. First Qualifying Interaction

A "qualifying interaction" reuses, unmodified, the existing approved POI Zone Interaction Standard's touch/entry classification (EDGE_TOUCH, PARTIAL_ENTRY, DEEP_ENTRY, FAR_BOUNDARY_TOUCH, CONTROLLED_OVERSHOOT) and Contact Tolerance formula (`Contact Tolerance = MAX(2×MinTick, MIN(0.05×ATR14, 0.10×ZoneHeight))`), both from `knowledge/MEASUREMENT_STANDARDS.md`. No new touch geometry, tolerance, or interaction classification is introduced by this standard.

**Post-decision clarification (`P0G-B006` interaction-timing clarification, Author-Approved) — machine-testable timing rule:**

```
qualifying_interaction_time > poi_availability_time
```

1. The interaction must be **strictly later** than the POI's own approved availability time (e.g. `order_block_available_time`, `fvg_available_time`, `engulfing_poi_available_time`, etc.) — a chronological, not merely a candle-count, comparison.
2. **Formation candles are excluded** — any candle that contributed to forming the POI's own pattern is never itself counted as an interaction against the (not-yet-existing) POI.
3. **Pre-availability candles are excluded** — no candle before `poi_availability_time` can trigger `FRESH → INTERACTED`, regardless of whether it geometrically touches the eventual zone.
4. **The availability or confirmation candle itself is excluded** — the specific candle whose close establishes `poi_availability_time` is never silently double-counted as the first qualifying interaction, even if that same candle's price action touches the zone.
5. **Equal timestamps do not qualify** — an event whose time exactly equals `poi_availability_time` does not satisfy `qualifying_interaction_time > poi_availability_time` and does not trigger `FRESH → INTERACTED`.
6. Only a **later** candle or event — one confirmed strictly after `poi_availability_time` — may cause `FRESH → INTERACTED`.
7. The existing, unmodified Zone Interaction Standard and Contact Tolerance formula (above) still determine whether that later event qualifies as EDGE_TOUCH/PARTIAL_ENTRY/DEEP_ENTRY/FAR_BOUNDARY_TOUCH/CONTROLLED_OVERSHOOT — this clarification changes only the timing gate, not the interaction-classification geometry.
8. A `NEAR_MISS` remains non-interaction (SS8, unchanged) regardless of timing.
9. No reverse transition exists for the same POI ID (SS9, unchanged) — this clarification does not alter that rule.
10. **No bar-age counting convention is introduced** by this clarification — whether the availability candle is later described as "age 0" or "age 1" (SS13-14) is untouched here; this section defines only the strict-inequality interaction-timing gate, not an age-counting scheme.

## 8. Near Miss Treatment

A `NEAR_MISS` (per the existing POI Zone Interaction Standard — price approaches within Contact Tolerance but does not intersect the zone) does not qualify as an interaction and does not remove freshness. A POI remains `FRESH` through any number of `NEAR_MISS` or `NO_CONTACT` events.

## 9. No Reverse Transition

`INTERACTED` cannot return to `FRESH` for the same POI identity (`poi_id`), under any circumstance, including a later `RECLAIM_CONFIRMED` or `FALSE_INVALIDATION_CONFIRMED` event from the Boundary Breach standard. Freshness state transitions are one-directional and non-repainting: once recorded, the `interacted_time` never moves or is retroactively cleared.

## 10. New POI Identity

A newly formed POI (a new confirmed pattern occurrence, even of the same POI type at a similar price) requires a new `poi_id` and begins its own, independent `freshness_status = FRESH` and its own age tracking from its own approved availability time. Freshness and age are never inherited, merged, or carried over from a prior POI identity, including a previously invalidated one (per the existing Boundary Breach standard's no-reactivation rule).

## 11. NOT_AUTOMATICALLY_EVALUATED

For Equal Highs, Equal Lows, Bullish Trendline, and Bearish Trendline, `freshness_status` and `expiration_status` are both `NOT_AUTOMATICALLY_EVALUATED` while their own specialized lifecycles remain formally deferred outside Phase 0G (see each structure's "Phase 0G Specialized Lifecycle Deferral" section — `P0G-B004`, `P0G-B005`). This value is distinct from `FRESH`/`INTERACTED`/`NOT_APPLICABLE`: it means the concept may apply in principle once a specialized lifecycle is later defined, but no automatic evaluation is performed against these structures today, and none may be silently inferred.

## 12. NOT_APPLICABLE

For Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants (single price levels, not persistent zones), `freshness_status` and `expiration_status` are both `NOT_APPLICABLE` — this standard does not extend to them, by design, unchanged from their existing classification in `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`.

## 13. Descriptive Age Fields

For every POI in scope (SS2):

```
age_start_time = approved_poi_available_time  (the POI's own already-defined availability timestamp)
age_in_confirmed_bars = number of confirmed candles elapsed since age_start_time, on the POI's own timeframe
elapsed_time_since_availability = current evaluation time − age_start_time
```

Both fields are preserved independently, per POI, and are recalculated only as new confirmed candles close — never backdated, never recalculated retroactively for a candle that has already been evaluated.

## 14. No Automatic Age Expiration

```
automatic_age_expiration = DISABLED
age_effect = DESCRIPTIVE_ONLY
```

Age alone — regardless of `age_in_confirmed_bars` or `elapsed_time_since_availability` — never causes weakening, expiration, invalidation, BTMM rejection, entry prohibition, strength reduction, or the creation of a new POI identity. No candle-count, elapsed-time, or POI-family-specific expiration threshold is defined or implied by this standard. Any such threshold, if ever adopted, requires a separate, explicit, future author decision and empirical calibration.

## 15. Period-Reference Identity Treatment

Day, week, and month reference structures (the 12 Previous/Current Period High/Low variants) are `NOT_APPLICABLE` to this standard (SS12) and continue to follow their own existing period-rollover and identity rules, unmodified — this standard does not touch their boundary, rollover, or naming conventions.

## 16. Separation from Invalidation

Freshness and age are tracked entirely independently of `poi_lifecycle_status` (`ACTIVE`/`INVALIDATED`) and the ten event-level lifecycle states from the POI Boundary Breach standard (`NO_BREACH` through `GENUINE_INVALIDATION_CONFIRMED`). An `INTERACTED` POI is not thereby closer to invalidation; a `GENUINE_INVALIDATION_CONFIRMED` POI's freshness/age fields are simply frozen at their last recorded values (per the Boundary Breach standard's no-reactivation and no-retroactive-rewriting rules) — neither standard modifies the other's fields.

## 17. Separation from Repeated-Tap Degradation

`freshness_status` and `tap_count`/`tap_classification` (from the Boundary Breach standard) are separate fields, tracked independently. `INTERACTED` records only that at least one qualifying interaction occurred; it does not itself count taps, and it does not implement or imply any repeated-tap degradation model — that remains the explicit, separate, unresolved scope of `P0G-B008` (an empirical-calibration item, not addressed here).

## 18. Separation from Entry and Risk

Freshness and age are descriptive evidence fields only. They do not constitute, imply, or substitute for entry confirmation, stop-loss placement, take-profit placement, risk-to-reward calculation, lot sizing, or any other entry/risk rule — all of which remain a separate, deferred, unresolved scope (`P0G-B016`), unaffected by this standard.

## 19. Empirical Research Limitations

This standard fixes only the descriptive shape of freshness/age tracking. It explicitly does not define: `PARTIALLY_MITIGATED` or `FULLY_MITIGATED` states; any mitigation-depth or dwell-based degradation formula; any maximum age or expiration threshold, per-POI-family or otherwise; or any weighting of freshness/age into a composite score. These remain open, future, empirical-calibration questions, not resolved by this document.

## 20. Machine-Testable Summary

Testable now: `freshness_status` transitions (`FRESH` → `INTERACTED`, one-directional, per `poi_id`), `NEAR_MISS`/`NO_CONTACT` non-effect on freshness, `age_in_confirmed_bars`/`elapsed_time_since_availability` computation, `NOT_AUTOMATICALLY_EVALUATED`/`NOT_APPLICABLE` classification per structure type, and the explicit absence of any automatic age-based effect. Not testable / not yet defined: any mitigation-depth state, any degradation formula, any expiration threshold.

## 21. Provenance

`AUTHOR-APPROVED`, `AUTHOR-ADDED PROJECT TERMINOLOGY` (freshness/age vocabulary and states are project additions, not book terms — the private book does not address freshness or age tracking at all), `ENGINEERING-PROVISIONAL`. Reuses, unmodified: the POI Zone Interaction Standard's Contact Tolerance formula and touch classification (`knowledge/MEASUREMENT_STANDARDS.md`); the POI Boundary Breach standard's `poi_id`, non-repainting, and no-reactivation principles (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`). No formula from either source document was modified.

## 22. Approval Status

**Author-Approved. Engineering-Provisional. NOT YET empirically calibrated. NOT YET out-of-sample validated. NOT production-approved.** This standard resolves `P0G-B006` and `P0G-B007` as documentation-only decisions establishing the descriptive shape of freshness and age tracking; it does not itself constitute empirical calibration, does not approve Phase 0G, and does not approve any POI as `APPROVED`. All 36 POI specifications remain `Status: PARTIAL`.
