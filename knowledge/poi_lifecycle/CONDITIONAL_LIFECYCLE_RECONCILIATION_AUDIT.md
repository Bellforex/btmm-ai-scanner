# Conditional POI Lifecycle Reconciliation Audit — Group 2

## 1. Purpose and Scope

This document is the authoritative output of the **Conditional POI Lifecycle Reconciliation Audit (Group 2)**. Its sole purpose is to review the 8 POIs classified `CONDITIONAL_GENERIC_INHERITANCE` in [POI_LIFECYCLE_APPLICABILITY_AUDIT.md](POI_LIFECYCLE_APPLICABILITY_AUDIT.md) and determine exactly what must be clarified before the approved [POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional](POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) can be propagated into their individual specifications.

This is a **documentation-only reconciliation audit**. It does **not**:
- Propagate lifecycle inheritance into any individual POI file.
- Invent or approve any family-specific override.
- Alter any existing formation, boundary, confirmation, strength, invalidation, or lifecycle formula.
- Approve, calibrate, validate, or make production-ready any POI.

No result in this document may be described as empirically proven or production-ready.

## 2. Audit Date

2026-07-19

## 3. Evidence Status

All standards referenced by this audit remain:

- **AUTHOR-APPROVED**
- **AUTHOR-ADDED PROJECT TERMINOLOGY** where applicable
- **ENGINEERING-PROVISIONAL**
- **NOT YET EMPIRICALLY CALIBRATED**
- **NOT YET OUT-OF-SAMPLE VALIDATED**
- **NOT PRODUCTION-APPROVED**

## 4. Source Files Reviewed

- `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (authoritative shared standard; not modified).
- `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md` (Group 1 audit; not modified by this task except an appended dated section — see Part 10 / Section 20 below).
- `knowledge/MEASUREMENT_STANDARDS.md` (Support/Resistance Horizontal Touch/Pierce/Zone-Depth formulas; not modified).
- `knowledge/POI_COVERAGE_MATRIX.md` (reconciled against; append-only note, see Section 19).
- `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (reconciled against; updated separately, see Part 12).
- `docs/PROJECT_STATE.md` (reconciled against; updated separately, see Part 13).
- The 8 individual POI files listed in Section 5 (read in full; **not modified**).

## 5. Exact Eight-POI Inventory

| poi_name | file_path | matches POI_COVERAGE_MATRIX.md row |
|---|---|---|
| Buy Order Block | `knowledge/poi_rules/volume_based/buy_order_block.md` | Yes |
| Sell Order Block | `knowledge/poi_rules/volume_based/sell_order_block.md` | Yes |
| Buy Fair Value Gap | `knowledge/poi_rules/volume_based/buy_fair_value_gap.md` | Yes |
| Sell Fair Value Gap | `knowledge/poi_rules/volume_based/sell_fair_value_gap.md` | Yes |
| Base Rally | `knowledge/poi_rules/volume_based/base_rally.md` | Yes |
| Base Drop | `knowledge/poi_rules/volume_based/base_drop.md` | Yes |
| Support | `knowledge/poi_rules/structural/support.md` | Yes |
| Resistance | `knowledge/poi_rules/structural/resistance.md` | Yes |

All 8 files exist and match their corresponding `POI_COVERAGE_MATRIX.md` row identity (name, family, direction). **No discrepancy found.**

## 6. Reconciliation Classification Definitions

| Code | Name | Meaning |
|---|---|---|
| A | `READY_FOR_AUTHOR_APPROVAL` | Boundaries, direction, and availability timing already fully documented; generic lifecycle can apply without changing formation rules; only explicit author approval to propagate remains. |
| B | `NEEDS_TERMINOLOGY_RECONCILIATION` | Generic lifecycle appears applicable, but existing event names / break-candidate names / lifecycle wording conflict or overlap; resolvable via aliases or precedence rules; no formula changed yet. |
| C | `NEEDS_AVAILABILITY_TIMING_DECISION` | Boundaries and direction exist, but it is unclear exactly when the zone becomes available to the lifecycle without look-ahead bias. |
| D | `NEEDS_FAMILY_SPECIFIC_OVERRIDE_DECISION` | Direct inheritance could incorrectly alter the POI's intended behavior; a family-specific lifecycle override may be necessary; decision belongs to the author. |
| E | `BLOCKED_INCOMPLETE_SPECIFICATION` | Required boundaries, direction, geometry, or availability information is missing; safe inheritance cannot be assessed without completing the POI specification. |

No additional primary classification was created. No classification listed above was left unused by necessity — only B, C, and D were needed for these 8 POIs (see Section 7).

## 7. Full Eight-POI Reconciliation Matrix

| poi_name | status | direction | zone_top | zone_bottom | entry_boundary | far_boundary | availability_time_documented | formation_confirmation_time | non_repainting_status | break_candidate_terminology | invalidation_wording | conflict_with_generic | stale_ambiguity_15_wording | family_geometry_concern | unresolved_dependency | changes_formation_meaning | changes_existing_boundaries | classification |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Buy Order Block | PARTIAL | Bullish | High of smaller (origin) candle | Low of smaller (origin) candle | Zone Top | Zone Bottom | NO | Displacement candle close (implied by size-ratio rule; not labeled) | UNCLEAR | None | "NOT DEFINED IN BOOK" | None (no competing formula); backdating risk only | None found | None identified | Volume/Momentum proxy thresholds (Ambiguity 3, unset) | No | No | **C** |
| Sell Order Block | PARTIAL | Bearish | High of smaller (origin) candle | Low of smaller (origin) candle | Zone Bottom | Zone Top | NO | Displacement candle close (implied; not labeled) | UNCLEAR | None | "NOT DEFINED IN BOOK" | None; backdating risk only | None found | None identified | Same as Buy Order Block | No | No | **C** |
| Buy Fair Value Gap | PARTIAL | Bullish | Low of third candle | High of first candle | Zone Top | Zone Bottom | NO (geometrically implied at 3rd-candle close) | Third candle close (gap geometry is itself the confirmation) | UNCLEAR | None | Narrow non-invalidation note only (trailing-candle size ≠ invalidation) | No formula conflict; narrow-zone tolerance behavior open (see Section 9, RECON-D3) | None found | **YES** — no enforced minimum FVG width; generic tolerance floor can equal/exceed Zone Height for a very narrow but valid gap | General proxy thresholds (Ambiguity 3); BTMM-anchor measurements (Ambiguity 14) | No | No (behavioral effect only, not a formula change) | **D** |
| Sell Fair Value Gap | PARTIAL | Bearish | High of third candle | Low of first candle | Zone Bottom | Zone Top | NO (geometrically implied at 3rd-candle close) | Third candle close | UNCLEAR | None | Same narrow note as Buy FVG | Same as Buy FVG | None found | Same as Buy FVG | Same as Buy FVG | No | No | **D** |
| Base Rally | PARTIAL | Bullish | Base High (highest high of base candles) | Base Low (lowest low of base candles) | Zone Top | Zone Bottom | NO | Departure candle close (implied by Confirmation conditions; not labeled) | UNCLEAR | None | "Not defined in the book." | None; backdating risk only | None found | Minor — Base Height has an explicit maximum but no explicit minimum, though ≥2-candle/Overlap-Ratio≥0.50 structure limits how thin it can realistically become (not treated as blocking) | General proxy thresholds (Ambiguity 3) | No | No | **C** |
| Base Drop | PARTIAL | Bearish | Base High | Base Low | Zone Bottom | Zone Top | NO | Departure candle close (implied; not labeled) | UNCLEAR | None | "Not defined in the book." | None; backdating risk only | None found | Same minor note as Base Rally | Same as Base Rally | No | No | **C** |
| Support | PARTIAL | Bullish | Zone Bottom + Horizontal Zone Depth | Origin Swing Low Pivot Price | Zone Top | Zone Bottom | **YES** — explicit ("never exposed historically at the original pivot time") | Origin-reaction classification completion | **YES** — explicit non-repainting section | `SUPPORT_BREAK_CANDIDATE` (`Zone Bottom − Close > Horizontal Pierce Tolerance`) | Explicitly "not final invalidation" | **YES** — terminology/tolerance overlap with `CLOSE_BREACH_CANDIDATE` (see Section 9, RECON-D4) | **YES** — recorded in Group 1 audit Section 15 #1 (already flagged, not re-fixed here) | None beyond RECON-D4 | Meaningful Swing Standard (Ambiguity 10) material-breach sub-rule; POI Reaction Strength Standard calibration | No | No | **B** |
| Resistance | PARTIAL | Bearish | Origin Swing High Pivot Price | Zone Top − Horizontal Zone Depth | Zone Bottom | Zone Top | **YES** — explicit | Origin-reaction classification completion | **YES** — explicit non-repainting section | `RESISTANCE_BREAK_CANDIDATE` (`Close − Zone Top > Horizontal Pierce Tolerance`) | Explicitly "not final invalidation" | **YES** — same overlap, mirrored | **YES** — same as Support | None beyond RECON-D4 | Same as Support | No | No | **B** |

**Cross-cutting finding:** for all 8 POIs, generic lifecycle inheritance — if and when propagated — would **not** change any existing formation rule or existing boundary formula. This mirrors the Group 1 (`DIRECT_GENERIC_INHERITANCE`) finding: the open questions below are about *when the lifecycle clock starts* (timing), *what an existing overlapping term means relative to the generic term* (terminology), or *whether the generic tolerance formulas behave as intended at one family's characteristic zone geometry* (family-specific), never about redefining an already-approved formation or boundary rule.

## 8. Classification Counts

| Classification | Count | POIs |
|---|---|---|
| A. READY_FOR_AUTHOR_APPROVAL | 0 | — |
| B. NEEDS_TERMINOLOGY_RECONCILIATION | 2 | Support, Resistance |
| C. NEEDS_AVAILABILITY_TIMING_DECISION | 4 | Buy Order Block, Sell Order Block, Base Rally, Base Drop |
| D. NEEDS_FAMILY_SPECIFIC_OVERRIDE_DECISION | 2 | Buy Fair Value Gap, Sell Fair Value Gap |
| E. BLOCKED_INCOMPLETE_SPECIFICATION | 0 | — |
| **Total** | **8** | |

**None of the 8 POIs is classified `READY_FOR_AUTHOR_APPROVAL`** — every one has at least one open reconciliation question. **None is `BLOCKED_INCOMPLETE_SPECIFICATION`** — all 8 already have complete zone boundaries, direction, and formation/confirmation rules; the open questions concern lifecycle-specific timing, terminology, or geometry behavior, not missing specification.

## 9. Order Block Findings (Part 4)

**Buy Order Block / Sell Order Block.**

1. **Exact current boundaries:** Upper boundary = High of the smaller (first/origin) candle; Lower boundary = Low of the smaller (first/origin) candle. Unchanged by this audit.
2. **Exact expected reaction direction:** Buy Order Block = Bullish; Sell Order Block = Bearish. Already explicit in both files.
3. **Lifecycle-eligibility timing candidates evaluated against current file evidence:**
   - *At initial candle identification* — the raw High/Low numbers of the first candle are known at its own close, **but** at that point it is not yet known whether a valid Order Block exists at all (the pattern requires the second candle to be a qualifying displacement candle).
   - *After impulse (displacement) confirmation* — **this is the only timing option with direct textual support.** "Formation conditions" requires "a larger [bullish/bearish] displacement candle with strong, aggressive momentum," and "Candle-size requirement" requires the displacement candle's Size Ratio ≥ 2.0 (standard) / ≥ 3.0 (strong) versus the first candle. Both are only knowable once the second (displacement) candle closes.
   - *After BOS or another confirmation* — **not evaluated; BOS is undefined in this project** (see item 3 below). Not used as a timing candidate.
   - *After return to the zone* — **no textual support.** Neither file mentions a "return to zone" requirement for basic validity.
   - *Another documented time* — none found.
4. **Does the current file already require BOS or return confirmation?** **No.** "Confirmation conditions" states explicitly: *"No separate confirmation step distinct from the formation/size rule itself is given - validity rests on the two-candle size-and-location structure alone."* Neither BOS nor a return-to-zone requirement is present in either file.
5. **Would generic lifecycle inheritance risk accidentally backdating the POI?** **Yes, if the lifecycle clock were started at the origin candle's own close.** Because pattern validity (the 2×/3× Size Ratio check) is only resolved at the displacement candle's close, evaluating Close Breach/Reclaim/Genuine Invalidation against the zone before that point would evaluate a lifecycle for a zone that might not turn out to be a valid Order Block at all. This is the concrete backdating risk this task is required to surface, not resolve.
6. **Can Close Breach Candidate and Genuine Invalidation apply without changing the Order Block formation rule?** **Yes** — once an availability time is decided, the two-candle size/location formation rule and the Upper/Lower boundary formulas remain completely untouched; only the moment the lifecycle begins evaluating is affected.
7. **Does a family-specific override question exist beyond timing?** **No additional override question was identified.** No conflicting terminology, no narrow-zone geometry concern (the zone is a full single-candle range, structurally similar to the already-propagated Bullish/Bearish Pressure Wick zones).

**Per Part 4 instruction, BOS is not defined here** — `knowledge/poi_rules/structural/support.md`, `resistance.md`, `swing_high.md`, and `swing_low.md` all independently list "BOS/CHoCH" as undefined and out of scope, consistent with this finding.

**Reconciliation classification: C. NEEDS_AVAILABILITY_TIMING_DECISION** for both Buy Order Block and Sell Order Block. See RECON-D1 (Section 10).

## 10. Fair Value Gap Findings (Part 5)

**Buy Fair Value Gap / Sell Fair Value Gap.**

1. **Exact approved three-candle geometry:** Candle 1 (first/previous candle), Candle 2 (displacement candle), Candle 3 (third/next candle). Buy FVG confirmation: `Low of Candle 3 > High of Candle 1`. Sell FVG confirmation: `High of Candle 3 < Low of Candle 1`. This strict geometry is an independent mandatory requirement, unaffected by the optional Market Speed and Displacement Standard speed tiers.
2. **Exact Zone Top and Zone Bottom:** Buy FVG: Zone Top = Low of Candle 3, Zone Bottom = High of Candle 1. Sell FVG: Zone Top = High of Candle 3, Zone Bottom = Low of Candle 1.
3. **Expected reaction direction:** Buy FVG = Bullish, Sell FVG = Bearish. Already explicit.
4. **Are the current labels unambiguous and directionally consistent?** **Yes, numerically.** The field *names* ("Upper boundary" = "Low of the third candle") read counter-intuitively (already recorded as Group-1-audit inconsistency #5, a documentation-clarity note, not a geometry defect), but `Zone Top > Zone Bottom` is structurally guaranteed by the gap-geometry rule itself.
5. **Does a narrow but valid FVG create any lifecycle conflict?** **A behavioral concern, not a formula conflict** — see item 7 below.
6. **Does the current file contain wording implying a narrow zone is invalid, non-invalidation evidence, a minimum width, or no such rule?** The only invalidation-adjacent sentence is: *"the size of the candle following the displacement candle does not invalidate the FVG."* This concerns the size of the **trailing candle after the displacement candle** — an unrelated concept — not the width of the gap zone itself. **No minimum FVG zone width exists anywhere in either file or in `MEASUREMENT_STANDARDS.md`.** This audit does not invent one.
7. **Are the shared tolerance formulas geometrically usable for a very narrow FVG?** **Yes, they remain computable** (the `MAX(2×MinTick, ...)` floor guarantees a defined, non-zero, non-negative tolerance in every case — no division by zero, no undefined result). **However**, because FVG Zone Height has no enforced minimum (a geometrically valid FVG can be as narrow as one price tick), the tolerance floor (`2 × Minimum Price Tick`) can equal or exceed the entire Zone Height for a sufficiently narrow gap. In that case, `Zone Bottom + Contact Tolerance` (bullish reclaim threshold) can sit at or beyond `Zone Top` itself, meaning "reclaim" would effectively require price to close back through the *entire* zone rather than partially re-enter it. This does not happen for the already-propagated Group 1 POIs' zones (single full candle ranges) or for Support/Resistance (Horizontal Zone Depth already includes the same `2×MinTick` floor by construction, so this scenario is already priced into that standard's design) — it is a property specific to FVG's unbounded-minimum gap geometry.
8. **Does inheritance require no override / terminology clarification / minimum-width decision / family-specific override?** This audit identifies the open question but does **not** select an answer. See RECON-D3 (Section 11) for the presented options.

**No FVG formation formula, gap-geometry rule, or minimum width was invented or changed by this finding.**

**Reconciliation classification: D. NEEDS_FAMILY_SPECIFIC_OVERRIDE_DECISION** for both Buy Fair Value Gap and Sell Fair Value Gap. See RECON-D3 (Section 11).

## 11. Base Formation Findings (Part 6)

**Base Rally / Base Drop.**

1. **Exact zone boundaries:** Zone Top = Base High (highest high of all 2-6 base candles); Zone Bottom = Base Low (lowest low of all 2-6 base candles). Unchanged.
2. **Expected direction:** Base Rally = Bullish, Base Drop = Bearish. Already explicit.
3. **Lifecycle-eligibility timing candidates evaluated against current file evidence:**
   - *After the base forms* — the base candle count (2-6) and Base High/Low are only fully known once it is clear no further base candle will extend the group (i.e., once the departure candle appears and breaks out) — the base's own candle count cannot be "closed" by definition until departure occurs, since more than 6 candles reclassifies the group as consolidation, not a Base.
   - *After the departure candle closes* — **this is the only timing option with direct textual support.** "Confirmation conditions" requires the departure candle to close beyond the base extreme, be ≥2×/3× the largest base candle, and "separate decisively from the base" — all only knowable at the departure candle's close.
   - *After reaction confirmation* — no textual support; the POI Reaction Strength Standard is not referenced anywhere in `base_rally.md`/`base_drop.md`.
   - *Another documented time* — none found.
4. **Does the approved Base Formation Standard already define sufficient non-repainting availability?** **Not as a labeled statement.** The underlying Confirmation-conditions logic already functionally gates full base validity on the departure candle's close (the same way Order Block's validity gates on its displacement candle), but — unlike Support, Resistance, Bullish/Bearish Pressure Wick, or Buy-to-Sell/Sell-to-Buy Candle — neither `base_rally.md` nor `base_drop.md` contains an explicit "non-repainting availability" section naming this point.
5. **Can the shared lifecycle begin without altering base candle count, compactness, height, overlap, departure requirements, or strength classification?** **Yes.** COMPACT BASE / STRONG BASE / INVALID BASE classification, the 2-6 candle-count bound, Base Height, Base Midpoint Drift, and Overlap Ratio formulas are untouched by any availability-timing decision — only the moment the lifecycle clock starts is affected.
6. **Is a family-specific override needed beyond the timing decision?** **No additional override question was identified as blocking.** A minor, non-blocking observation: Base Height has an explicit maximum (`<= 0.75× ATR(14)` and `<= 0.60×` departure range) but no explicit minimum, so an unusually tight base could in principle also be a narrow zone — however the mandatory ≥2-candle count and ≥0.50 Overlap Ratio requirement structurally limit how thin a Base zone can realistically become, unlike FVG's single-tick-possible gap. This is recorded for completeness, not treated as blocking.

**No departure rule, base-compactness formula, or new confirmation rule was invented or changed by this finding.**

**Reconciliation classification: C. NEEDS_AVAILABILITY_TIMING_DECISION** for both Base Rally and Base Drop. See RECON-D2 (Section 12).

## 12. Support/Resistance Findings (Part 7)

**Support / Resistance.**

### Formula comparison (exact, as currently approved)

| | Formula | Tolerance used | Timing |
|---|---|---|---|
| `SUPPORT_BREAK_CANDIDATE` (Ambiguity 12) | `Zone Bottom − Candle Close > Horizontal Pierce Tolerance` | `Horizontal Pierce Tolerance = MAX(2×MinTick, 0.15×ATR(14))` | Confirmed candle close |
| `RESISTANCE_BREAK_CANDIDATE` (Ambiguity 12) | `Candle Close − Zone Top > Horizontal Pierce Tolerance` | Same formula | Confirmed candle close |
| Generic bullish `CLOSE_BREACH_CANDIDATE` (Ambiguity 15) | `Zone Bottom − Candle Close > Overshoot Tolerance` | `Overshoot Tolerance = MAX(2×MinTick, MIN(0.10×ATR(14), 0.25×Zone Height))` | Confirmed candle close |
| Generic bearish `CLOSE_BREACH_CANDIDATE` (Ambiguity 15) | `Candle Close − Zone Top > Overshoot Tolerance` | Same formula | Confirmed candle close |

**Condition shape is identical** (`Zone Bottom − Close > tolerance` bullish; `Close − Zone Top > tolerance` bearish) and **both evaluate on confirmed candle closes only** — no timing difference exists.

**The tolerance values differ substantially.** For Support/Resistance, Zone Height = Horizontal Zone Depth = `MAX(2×MinTick, 0.10×ATR(14))`. Substituting into the generic Overshoot Tolerance's `0.25 × Zone Height` branch gives approximately `0.25 × 0.10×ATR(14) = 0.025×ATR(14)` whenever the ATR-based branches dominate over the tick floor — roughly **6× smaller** than the `0.15×ATR(14)` Horizontal Pierce Tolerance. This means, in the typical (non-floor) case, **`CLOSE_BREACH_CANDIDATE` fires at a shallower close than `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE`** — the generic event is the *earlier, looser* signal, and the Ambiguity-12 event is the *later, stricter* one. This is the opposite of a simple "early warning" relationship and is more precise than the original Group 1 audit's open framing ("superseded by, parallel to, or merged with").

**Do the events coexist without contradiction?** **Technically yes** — both are independently computed fields with different names and no shared-field collision, so nothing prevents both being recorded simultaneously. **Semantically, only `CLOSE_BREACH_CANDIDATE` is wired into the shared standard's Reclaim / Displacement-After-Reclaim / False-Invalidation / Genuine-Invalidation state machine.** `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` is not connected to any of those downstream states today. Presenting both to a future implementer without an explicit precedence or aliasing decision risks ambiguity about which event actually gates invalidation.

**Classification of the relationship against Part 7's options A-D:** the evidence supports **C (separate events using different tolerance formulas)** most precisely — they are not exact aliases (A, formulas differ), and the Ambiguity-15 event fires *earlier* rather than serving as an earlier family-specific warning ahead of the generic one (so B does not fit as originally framed), and nothing here is contradictory or requires an urgent author decision to avoid an active defect (so this is not classified D). This audit does **not** select an alias, precedence, or override rule — see RECON-D4 (Section 13) for the options presented for author approval.

**Sufficiency for propagation after terminology reconciliation:**

| Requirement | Support | Resistance |
|---|---|---|
| Fixed boundaries | YES — Zone Top/Bottom formulas fixed permanently after zone creation | YES |
| Expected direction | YES — explicit (Bullish / Bearish) | YES |
| Non-repainting availability | YES — explicit section: origin/ATR/boundaries "never move or get recalculated" | YES |
| Confirmation time | YES — origin-reaction classification completion (DRAFT_SUPPORT/RESISTANCE) | YES |
| Existing lifecycle status | PARTIAL — `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` exist but are explicitly not final invalidation | PARTIAL |

**Conclusion: Support and Resistance have every prerequisite for propagation already in place. The single remaining blocker is the terminology/tolerance reconciliation question (RECON-D4) — no boundary, timing, or availability gap exists for either POI.**

**Reconciliation classification: B. NEEDS_TERMINOLOGY_RECONCILIATION** for both Support and Resistance.

## 13. Exact Formula and Terminology Conflicts

| # | Conflict | POIs affected | Nature |
|---|---|---|---|
| 1 | `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` (Horizontal Pierce Tolerance) vs. `CLOSE_BREACH_CANDIDATE` (Overshoot Tolerance) | Support, Resistance | Same condition shape, different tolerance formulas (roughly 6× apart in the typical case); only `CLOSE_BREACH_CANDIDATE` is wired into the Reclaim/Displacement/Invalidation state machine. See Section 12, RECON-D4. |

No other formula-level conflict was found among the 8 POIs. Order Block, FVG, and Base have no existing break-candidate or invalidation terminology at all (each file's "Invalidation" field reads "NOT DEFINED IN BOOK" / "Not defined in the book." / a narrow non-invalidation note), so no naming collision is possible for those six POIs — their open questions are timing (Order Block, Base) and geometry behavior (FVG), not terminology conflict.

## 14. Availability-Timing Questions

| # | Question | POIs affected | Decision |
|---|---|---|---|
| 1 | Should the lifecycle clock start at the origin candle's close or the displacement candle's close? | Buy Order Block, Sell Order Block | RECON-D1 |
| 2 | Should the lifecycle clock start at the departure candle's close (vs. an earlier point in base formation)? | Base Rally, Base Drop | RECON-D2 |

Support and Resistance already have an explicit, sufficient non-repainting availability statement and are **not** included here. Buy/Sell Fair Value Gap's availability point (third-candle close) is geometrically self-evident from the gap-confirmation rule itself and is **not** treated as an open timing question in this audit — FVG's open question is classified under Section 15 (family-specific), not here, because the more consequential open issue for FVG is the narrow-zone tolerance behavior, not *when* the zone exists.

## 15. Family-Specific Override Questions

| # | Question | POIs affected | Decision |
|---|---|---|---|
| 1 | Should the generic tolerance formulas apply to FVGs of any width unmodified, or does an FVG-specific minimum width / tolerance treatment need to be introduced? | Buy Fair Value Gap, Sell Fair Value Gap | RECON-D3 |

This is the only family-specific override question identified for the 8 conditional POIs beyond the timing (Section 14) and terminology (Section 13) questions above.

## 16. Author-Decision Options (Part 8)

### RECON-D1 — Order Block Lifecycle Availability Timing

**Affected POIs:** Buy Order Block, Sell Order Block

**Current conflict:** Neither file contains an explicit "non-repainting availability" statement (unlike Bullish/Bearish Pressure Wick or Buy-to-Sell/Sell-to-Buy Candle, which do). The zone's numeric boundaries (first/origin candle's High/Low) are computable at that candle's own close, but the pattern's validity as an Order Block (≥2×/3× Size Ratio versus the displacement candle) is only resolved once the second (displacement) candle closes.

**Option A:** Availability = displacement candle close (pattern-confirmation time) — the lifecycle clock starts only once the two-candle pattern is fully confirmed valid, mirroring the precedent already used for Pressure Wick (`CANDIDATE`→`CONFIRMED`) and Buy-to-Sell/Sell-to-Buy Candle (`reversal_confirmation_time`).

**Option B:** Availability = origin candle close (earliest possible) — the lifecycle clock starts as soon as the raw boundary numbers exist, even though pattern validity is not yet confirmed.

**Option C, only when genuinely necessary:** A two-stage model — a provisional/candidate zone from origin-candle close, promoted to lifecycle-eligible only at displacement-candle close, tracking both timestamps explicitly.

**Effect of each option:** Option A prevents evaluating breach/reclaim/invalidation against a zone that later turns out not to be a valid Order Block at all, consistent with existing Group 1 precedent; it delays lifecycle tracking by one candle versus Option B. Option B starts tracking earlier but risks recording lifecycle events against a zone retroactively found invalid — exactly what the shared standard's non-repainting rules are designed to prevent. Option C preserves both perspectives but introduces a second timestamp/state not present in the approved standard or any other propagated POI file.

**Recommended engineering option:** Option A.

**Reason for recommendation:** matches the precedent already author-approved for all 4 `DIRECT_GENERIC_INHERITANCE` POIs; avoids inventing a new two-stage state model not currently justified by documented need; is the only option that cannot backdate lifecycle events to an unconfirmed pattern.

**Rules that remain unchanged:** Order Block's two-candle size/location formation rule; the Upper/Lower boundary formulas; the generic lifecycle's event states, tolerances, and transition formulas.

**Risk of choosing incorrectly:** choosing Option B (or any variant that starts the clock too early) could report a "breach," "reclaim," or "genuine invalidation" against a POI that never actually qualified as an Order Block, corrupting downstream BTMM linkage and evidence records.

**ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED**

---

### RECON-D2 — Base Formation Lifecycle Availability Timing

**Affected POIs:** Base Rally, Base Drop

**Current conflict:** Neither file contains an explicit "non-repainting availability" statement. Base High/Low are only fully final once the base candle group can no longer be extended — which, by the approved Base Formation Standard, is only known once the departure candle closes and confirms the base as COMPACT/STRONG (rather than the group silently growing past 6 candles into consolidation, or the departure candle failing its ≥2×/3× ratio or close-outside-base requirement).

**Option A:** Availability = departure candle close (pattern-confirmation time) — matches the same reasoning and precedent as RECON-D1 Option A.

**Option B:** Availability = the close of the last base candle before departure begins (earliest possible, before departure is confirmed).

**Option C, only when genuinely necessary:** A two-stage model mirroring RECON-D1 Option C.

**Effect of each option:** Option A guarantees the lifecycle only evaluates a Base that has already been confirmed COMPACT or STRONG. Option B risks tracking a "base" that later turns out to have more than 6 candles (reclassified as consolidation, not a Base Rally/Drop POI at all) or an insufficient departure candle. Option C adds unrequested complexity.

**Recommended engineering option:** Option A.

**Reason for recommendation:** identical reasoning to RECON-D1 — consistent with Group 1 precedent, avoids backdating, invents no new state model.

**Rules that remain unchanged:** the 2-6 base candle-count bound; Base Height, Base Midpoint Drift, Overlap Ratio, departure-candle ratio, and COMPACT/STRONG/INVALID BASE classification formulas.

**Risk of choosing incorrectly:** choosing Option B risks recording lifecycle events against a candle group that is later reclassified as consolidation rather than a valid Base, corrupting downstream evidence and BTMM linkage.

**ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED**

---

### RECON-D3 — Fair Value Gap Minimum Width / Narrow-Zone Tolerance Treatment

**Affected POIs:** Buy Fair Value Gap, Sell Fair Value Gap

**Current conflict:** FVG zone geometry has no enforced minimum width — a geometrically valid FVG can be as narrow as one price tick. The generic Contact/Overshoot Tolerance formulas floor at `2 × Minimum Price Tick` regardless of Zone Height. For a sufficiently narrow FVG, this floor can equal or exceed the entire Zone Height, so the Reclaim threshold could sit at or beyond the Entry Boundary itself, and the Close Breach threshold could be reached almost immediately after any close beyond the Far Boundary. The formulas remain computable in every case (never undefined); this is a behavioral, not a computability, concern.

**Option A:** No override — apply the generic tolerance formulas to FVGs of any width exactly as already approved for every other bounded POI; accept that very narrow FVGs behave more conservatively (harder to "reclaim" without closing back through most or all of the zone).

**Option B:** Establish a minimum FVG zone width (in ticks or as an ATR fraction) below which a geometrically valid FVG is excluded from lifecycle tracking or handled by a separate rule. This would be a new, author-decided numeric threshold — not invented here.

**Option C, only when genuinely necessary:** A family-specific tolerance formula for FVG only (e.g. a Zone-Height-only fraction with no fixed-tick floor). A genuine family-specific override — not invented here.

**Effect of each option:** Option A requires no new rule and keeps FVG mechanically identical to every other bounded POI; the tradeoff is purely behavioral for the narrow-zone edge case. Option B adds a new gating rule that would make some geometrically valid, book-defined FVGs ineligible for (or differently handled by) the shared lifecycle — a new POI-family carve-out. Option C changes the tolerance formula itself for one POI family only, a larger structural change than a threshold.

**Recommended engineering option:** Option A.

**Reason for recommendation:** the `2×MinTick` floor already reflects an existing, author-approved design decision in the Zone Interaction Standard (Ambiguity 8) intended to keep tolerances meaningful at broker tick granularity, and it already applies uniformly to every other POI type (including Support/Resistance's own Horizontal Zone Depth, which has the identical floor by construction) — treating FVG differently would be a new, currently unjustified special case.

**Rules that remain unchanged:** the strict three-candle FVG gap-geometry formula; the Contact/Overshoot Tolerance formulas themselves; Body Efficiency, Range Speed Ratio, and Displacement Expansion Ratio thresholds.

**Risk of choosing incorrectly:** choosing Option A without acknowledgment could surprise a future reader who expects "reclaim" to mean the same thing at every zone width; choosing B or C without calibration evidence risks excluding valid, book-defined FVGs based on an arbitrary, uncalibrated numeric threshold.

**ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED**

---

### RECON-D4 — Support/Resistance Break-Candidate Reconciliation

**Affected POIs:** Support, Resistance

**Current conflict:** two independently author-approved standards each define a "confirmed close beyond the zone by more than a tolerance" event: `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` (Ambiguity 12, Horizontal Pierce Tolerance = `MAX(2×MinTick, 0.15×ATR(14))`) and the generic `CLOSE_BREACH_CANDIDATE` (Ambiguity 15, Overshoot Tolerance = `MAX(2×MinTick, MIN(0.10×ATR(14), 0.25×Zone Height))`). Both share the identical condition shape and both evaluate on confirmed candle closes, but — because Support/Resistance's Zone Height is itself `MAX(2×MinTick, 0.10×ATR(14))` — the generic tolerance is typically ~6× smaller than the Ambiguity-12 tolerance, so `CLOSE_BREACH_CANDIDATE` generally fires first. Only `CLOSE_BREACH_CANDIDATE` connects to the Reclaim/Displacement/False-Invalidation/Genuine-Invalidation state machine today.

**Option A:** Treat `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` as fully superseded by `CLOSE_BREACH_CANDIDATE` for lifecycle purposes — retire the Ambiguity-12 event name from the lifecycle role, optionally retained only as a historical/legacy field.

**Option B:** Keep both as independent, parallel signals with distinct meanings (e.g. `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` as a stricter/deeper structural signal, `CLOSE_BREACH_CANDIDATE` as the shallower lifecycle-gating signal) and document explicitly that only `CLOSE_BREACH_CANDIDATE` drives Reclaim/Displacement/Invalidation.

**Option C, only when genuinely necessary:** formally alias the two events to one underlying event, requiring the *stricter* (larger) of the two tolerances to trigger — a merge, not selected here.

**Effect of each option:** Option A removes the terminology overlap entirely but discards a previously author-approved, independently useful signal (Ambiguity 12) without an explicit decision to do so. Option B preserves both and requires no formula change to either standard, but leaves two similarly-named "break candidate" concepts with different trigger distances in the documentation unless clearly labeled. Option C unifies them under the stricter formula but silently changes the effective trigger distance of whichever event currently fires first.

**Recommended engineering option:** Option B.

**Reason for recommendation:** discards nothing already author-approved; requires no formula change to either standard; is consistent with the "keep independently-labeled, non-collapsed concepts" pattern already used elsewhere in this project (e.g., Equal Lows != Support and Equal Highs != Resistance are explicitly kept as independent, non-collapsed labels in the same files, per the already-approved Support/Resistance standard's own "Overlap with other POIs" section).

**Rules that remain unchanged:** `Horizontal Pierce Tolerance`, `Horizontal Touch Tolerance`, `Horizontal Zone Depth` (Ambiguity 12); `Overshoot Tolerance`, `Contact Tolerance` (Ambiguity 15/8); the DRAFT/CONFIRMED/STRONG Support/Resistance classification.

**Risk of choosing incorrectly:** choosing A without deciding to formally retire the Ambiguity-12 signal could silently lose previously-approved structural evidence; choosing C without calibration evidence risks changing the effective trigger distance of an already-approved event without empirical justification.

**ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED**

---

**Four author decisions are required in total** (RECON-D1 through RECON-D4), covering all 8 conditional POIs with no overlap and no POI left uncovered. This is fewer than one decision per POI (8) and more than a single umbrella decision (1) because the evidence genuinely separates into four distinct question types across three POI families — this count was not forced to match any predetermined number.

## 17. Engineering Recommendations Summary (clearly unapproved)

| Decision | Recommended option | Status |
|---|---|---|
| RECON-D1 (Order Block timing) | Option A — availability at displacement-candle close | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| RECON-D2 (Base timing) | Option A — availability at departure-candle close | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| RECON-D3 (FVG narrow-zone) | Option A — no override, apply generic tolerances unmodified | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| RECON-D4 (Support/Resistance terminology) | Option B — keep both events parallel, only `CLOSE_BREACH_CANDIDATE` drives lifecycle | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |

**None of these four recommendations is implemented, approved, or propagated by this audit.** They exist solely to give the author a starting point for each decision.

## 18. Safe Items Requiring No Author Decision

The following are already fully settled and require no further author decision before propagation could technically proceed (pending resolution of the corresponding RECON-D item above):

- All 8 POIs' existing zone boundary formulas (Upper/Lower boundary, Zone Top/Bottom) — none require any change.
- All 8 POIs' existing expected direction — none require any change.
- All 8 POIs' existing formation and confirmation rules (two-candle Order Block geometry, three-candle FVG gap geometry, Base Formation Standard's candle count/compactness/departure rules, Support/Resistance origin-eligibility/creator-boundary rules) — none require any change.
- Support and Resistance's non-repainting availability timing — already explicit and sufficient; RECON-D4 concerns terminology only, not timing.
- The shared standard's tolerance formulas themselves (`Contact Tolerance`, `Overshoot Tolerance`, `Horizontal Touch/Pierce Tolerance`, `Horizontal Zone Depth`) — none require any change under any of the four recommended options above.

## 19. Items That Must Not Be Propagated Yet

- Lifecycle inheritance into any of the 8 conditional POI files — blocked pending RECON-D1 through RECON-D4.
- Any `non-repainting availability` section for Buy/Sell Order Block or Base Rally/Drop — blocked pending RECON-D1/RECON-D2.
- Any FVG minimum-width rule or FVG-specific tolerance formula — blocked pending RECON-D3, and must not be invented regardless of which option the author eventually selects.
- Any Support/Resistance break-candidate alias, precedence rule, or merge — blocked pending RECON-D4.
- Lifecycle inheritance into any of the 6 `BLOCKED_INCOMPLETE_SPECIFICATION` POIs (Bullish/Bearish Engulfing, Hammer, Shooting Star, Morning Star, Evening Star) — out of scope for this task; their missing zone-boundary formulas are independent of this reconciliation.
- Lifecycle inheritance into Equal Highs, Equal Lows, Bullish Trendline, or Bearish Trendline — explicitly and permanently excluded by the shared standard's own scope.

## 20. Recommended Controlled Sequence After Author Approval

This audit recommends, but does not authorize, the following sequence once the author has ruled on RECON-D1 through RECON-D4:

1. Author rules on RECON-D1 (Order Block), RECON-D2 (Base), RECON-D3 (FVG), and RECON-D4 (Support/Resistance) independently — each may be approved, modified, or rejected on its own schedule; none depends on another being resolved first.
2. For each resolved decision, a dedicated propagation task (structured like the completed Group 1 propagation) adds the "Shared POI Boundary Lifecycle Inheritance" section to the corresponding POI file(s), using the author-approved option's exact wording — not the engineering recommendation, unless the author explicitly approved that recommendation as-is.
3. `POI_COVERAGE_MATRIX.md`'s "Invalidation defined" column is updated for only the specific POIs whose decision was resolved and propagated in that task.
4. `POI_LIFECYCLE_APPLICABILITY_AUDIT.md` and this reconciliation audit are updated with a dated propagation-status note, following the same append-only pattern used for Group 1.
5. The 6 `BLOCKED_INCOMPLETE_SPECIFICATION` POIs remain a separate, independent workstream (their own missing zone-boundary formulas must be resolved first, unrelated to any RECON-D decision here).

## 21. Knowledge-Gate Impact

- This audit **does not** propagate lifecycle inheritance into any individual POI file.
- **No recommendation in Section 16/17 is author-approved.**
- **No individual POI rule is changed.**
- **No family-specific override is created.**
- **The knowledge gate remains CLOSED.**
- **Phase 0G remains unapproved.**
- No POI becomes APPROVED or production-ready as a result of this audit.
- See `knowledge/KNOWLEDGE_COMPLETION_GATE.md` for the complete, authoritative gate status.

## 22. Author Decision and Propagation (2026-07-19)

**This section records what has happened since Section 21 above. Sections 1-21 (the original reconciliation findings, matrix, and decision options) remain intact and unaltered by this update.**

RECON-D1 through RECON-D5 have been reviewed and **approved by the author**, exactly as follows:

| Decision | Approved option | Affected POIs |
|---|---|---|
| RECON-D1 | Order Block availability = `qualifying_displacement_candle_close_time` (the engineering-recommended Option A) | Buy Order Block, Sell Order Block |
| RECON-D2 | Base availability = `qualifying_departure_candle_close_time` (the engineering-recommended Option A) | Base Rally, Base Drop |
| RECON-D3 | No family-specific override; generic Contact and Overshoot Tolerances inherited unmodified; no minimum FVG width invented (the engineering-recommended Option A) | Buy Fair Value Gap, Sell Fair Value Gap |
| RECON-D4 | `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` preserved as separate, non-aliased, family-specific deeper breach observations; only `CLOSE_BREACH_CANDIDATE` starts the shared Reclaim/Invalidation lifecycle (the engineering-recommended Option B) | Support, Resistance |
| RECON-D5 | FVG lifecycle availability = `fvg_available_time = third_candle_close_time`; a FVG is not valid while the third candle is still forming; strict three-candle geometry must remain valid at that close; the candidate is rejected if the required gap no longer exists at that close | Buy Fair Value Gap, Sell Fair Value Gap |

**RECON-D5 resolves the availability-time gap identified during final verification of the Group 2 propagation.** That verification found that the propagated Buy/Sell FVG files described third-candle lifecycle availability as "geometrically self-evident" and requiring "no separate availability-timing decision," reasoning this project's own final-verification standard explicitly disallows as sufficient authorization — the pre-existing FVG formation specification directly establishes that `Zone Top`/`Zone Bottom` are undefined before the third candle closes (a mathematical consequence of the boundary formula), but it never explicitly stated that this same moment also governs *lifecycle* availability for the separate Boundary Breach, Reclaim and Invalidation Standard. RECON-D5 makes that specific mapping an explicit, Author-Approved decision, using the same dedicated-decision process already applied to RECON-D1/RECON-D2, rather than leaving it as an unstated inference.

**All 8 Group 2 POIs have been propagated.** Exact file paths updated:

| poi_name | file_path |
|---|---|
| Buy Order Block | `knowledge/poi_rules/volume_based/buy_order_block.md` |
| Sell Order Block | `knowledge/poi_rules/volume_based/sell_order_block.md` |
| Buy Fair Value Gap | `knowledge/poi_rules/volume_based/buy_fair_value_gap.md` |
| Sell Fair Value Gap | `knowledge/poi_rules/volume_based/sell_fair_value_gap.md` |
| Base Rally | `knowledge/poi_rules/volume_based/base_rally.md` |
| Base Drop | `knowledge/poi_rules/volume_based/base_drop.md` |
| Support | `knowledge/poi_rules/structural/support.md` |
| Resistance | `knowledge/poi_rules/structural/resistance.md` |

Each file received a new "Shared POI Boundary Lifecycle Inheritance" section (applicability classification, authoritative shared standard path, bounded-zone status, expected direction, Zone Top/Bottom mapping, Entry/Far Boundary mapping, lifecycle availability time or dual-event distinction as applicable, inherited event states, inherited Close Breach/Reclaim/Displacement directions, False/Genuine Invalidation meaning and effect, Repeated Tap handling, non-repainting timing, linked BTMM effect, evidence/provenance status, and remaining limitations), plus updates to each file's pre-existing "Invalidation," "Machine-testable criteria," "Unresolved questions," and "Author decision" sections to cross-reference the new section.

**No formation, boundary, confirmation, strength, or shared lifecycle formula was changed.** The already-approved zone mappings (Order Block: origin-candle High/Low; FVG: first/third-candle High/Low; Base: Base High/Low; Support/Resistance: origin-swing-derived Zone Top/Bottom via Horizontal Zone Depth) were reused exactly as previously approved. The authoritative shared standard (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`) was not modified. `SUPPORT_BREAK_CANDIDATE`, `RESISTANCE_BREAK_CANDIDATE`, and their `Horizontal Pierce Tolerance` formula (Ambiguity 12) were preserved unmodified, not merged or aliased into `CLOSE_BREACH_CANDIDATE`.

**No unapproved family-specific override was added.** RECON-D3's approved option is explicitly the absence of an override (no minimum width, no FVG-specific tolerance). RECON-D4's approved option preserves both pre-existing and generic events as independent, non-aliased signals rather than introducing a new merge/alias/precedence rule. RECON-D5 introduces no new geometry rule, no BOS/CHoCH, no HH/HL/LH/LL, and no minimum width — it only fixes the moment the already-defined boundaries become lifecycle-eligible.

**All five recommendations are now Author-Approved and Engineering-Provisional** — none has been empirically calibrated, out-of-sample validated, or made production-approved by this propagation. The inherited lifecycle for all 8 POIs carries the same evidence status as the authoritative shared standard: AUTHOR-APPROVED, AUTHOR-ADDED PROJECT TERMINOLOGY, ENGINEERING-PROVISIONAL, NOT YET EMPIRICALLY CALIBRATED, NOT YET OUT-OF-SAMPLE VALIDATED, NOT PRODUCTION-APPROVED.

**Remaining unresolved limitations** (unchanged by this propagation): freshness, expiration, repeated-tap/repeated-touch degradation, empirical calibration, out-of-sample validation, production approval, entry confirmation, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) for all 8 POIs; confirmed break/retest/false break/role reversal for Support/Resistance; general proxy thresholds and BTMM-anchor-dependent measurements (Ambiguity 14) for Order Block/FVG/Base; the 6 `BLOCKED_INCOMPLETE_SPECIFICATION` candlestick POIs remain incomplete and untouched; Equal Highs/Equal Lows/Trendline lifecycle remain excluded and unresolved.

**The final knowledge gate remains CLOSED. Phase 0G remains unapproved.**
