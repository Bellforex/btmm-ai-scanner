# POI Lifecycle Applicability Audit

## 1. Purpose and Scope

This document is the authoritative output of the **Cross-POI Lifecycle Applicability and Consistency Audit**. Its sole purpose is to determine, for every existing individual POI specification under `knowledge/poi_rules/`, whether the approved [POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional](POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) (resolves Ambiguity 15) can safely apply **directly**, **conditionally**, or **not at all**.

This is an audit and classification exercise only. It does **not**:
- Propagate the lifecycle rules into any individual POI file.
- Invent any family-specific override.
- Change any trading formula, threshold, POI formation condition, confirmation condition, boundary formula, strength classification, or lifecycle rule.
- Approve, calibrate, validate, or make production-ready any POI.

Classification recorded here does not alter any POI rule. `DIRECT_GENERIC_INHERITANCE` does not mean empirically validated. `CONDITIONAL_GENERIC_INHERITANCE` does not authorize automatic propagation. No POI becomes APPROVED or production-ready as a result of this audit. **The final knowledge gate remains CLOSED.**

## 2. Audit Date

2026-07-19

## 3. Evidence Status

All lifecycle decisions referenced by this audit remain:

- **AUTHOR-APPROVED**
- **AUTHOR-ADDED PROJECT TERMINOLOGY** where applicable
- **ENGINEERING-PROVISIONAL**
- **NOT YET EMPIRICALLY CALIBRATED**
- **NOT YET OUT-OF-SAMPLE VALIDATED**
- **NOT PRODUCTION-APPROVED**

This audit does not prove that any POI, classification, or lifecycle rule is profitable or production-ready. It is a documentation-consistency and applicability exercise only.

## 4. Source Files Reviewed

- All 36 files under `knowledge/poi_rules/volume_based/`, `knowledge/poi_rules/price_action/`, `knowledge/poi_rules/structural/` (read in full for this audit; none modified).
- `knowledge/POI_COVERAGE_MATRIX.md` (read for reconciliation; not modified).
- `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (the standard being audited against; not modified).
- `knowledge/MEASUREMENT_STANDARDS.md` (referenced for reused tolerance formulas; not modified).
- `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md` (referenced for Ambiguity 15 scope/exclusions; not modified).

## 5. Inventory Reconciliation

| Check | Result |
|---|---|
| Total POI files found under `knowledge/poi_rules/` | **36** |
| Expected count | 36 |
| Discrepancy | **None** |
| Files by family (`volume_based/`) | 10 |
| Files by family (`price_action/`) | 6 |
| Files by family (`structural/`) | 20 |
| Total POI rows in `knowledge/POI_COVERAGE_MATRIX.md` | **36** |
| Files without a corresponding matrix row | **None** |
| Matrix rows without a corresponding file | **None** |
| Duplicate POI names (within matrix or across files) | **None found** |
| Duplicate file paths | **None found** (verified via directory listing) |
| Naming inconsistencies | Cosmetic only — matrix uses display names (e.g. "Hammer (a.k.a. Pin Bar)", "Base Rally (Rally-Base-Rally)"), files use lowercase slugs (e.g. `hammer.md`, `base_rally.md`); every file's own H1 heading and documented alternative-name field matches its matrix row. Not a blocking inconsistency. |
| Category inconsistencies | Cosmetic only — matrix column says "Volume-Based" / "Price Action" / "Structural"; file field says "Volume-Based POI" / "Price Action POI" / "Structural POI" (matrix drops the "POI" suffix). Every file's family matches its directory and its matrix row. Not a blocking inconsistency. |

**Conclusion: the verified inventory is exactly 36 POIs (10 volume-based, 6 price-action, 20 structural), with a clean 1:1 mapping between files and matrix rows. No forced adjustment was needed — the actual count already equals the expected count.**

## 6. Classification Definitions

| Code | Name | Meaning |
|---|---|---|
| A | `DIRECT_GENERIC_INHERITANCE` | Bounded, directional, Zone Top/Bottom already defined, expected direction defined, Entry/Far Boundary mapping unambiguous, no conflicting lifecycle rule, generic lifecycle applies without modifying formation rules. |
| B | `CONDITIONAL_GENERIC_INHERITANCE` | Bounded and directional, generic lifecycle appears applicable, but a documented family-specific issue, geometry question, or potential override must be reviewed before propagation. |
| C | `BLOCKED_INCOMPLETE_SPECIFICATION` | May eventually be eligible, but required zone boundaries, direction, availability timing, or geometry are missing or ambiguous in the current documented specification. |
| D | `EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY` | Equal Highs / Equal Lows only. Sweep and liquidity lifecycle remains separate and unresolved. |
| E | `EXCLUDED_TRENDLINE` | Bullish Trendline / Bearish Trendline only. Line-specific break, reclaim, retest, and final invalidation remain separate and unresolved. |
| F | `NOT_APPLICABLE_OTHER` | Unbounded, non-directional, a reference point rather than a zone, or otherwise incompatible with the bounded directional lifecycle. |

No additional primary classification names were created.

## 7. Full POI-by-POI Applicability Matrix

Values use: YES / NO / PARTIAL / UNCLEAR / NOT_APPLICABLE. No cell is left blank.

| poi_name | file_path | poi_family | current_poi_status | bounded_zone_status | zone_top_status | zone_bottom_status | expected_direction_status | non_repainting_availability_status | existing_invalidation_status | applicability_classification |
|---|---|---|---|---|---|---|---|---|---|---|
| Buy Order Block | poi_rules/volume_based/buy_order_block.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bullish) | UNCLEAR | NOT_APPLICABLE (none defined) | CONDITIONAL_GENERIC_INHERITANCE |
| Sell Order Block | poi_rules/volume_based/sell_order_block.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bearish) | UNCLEAR | NOT_APPLICABLE (none defined) | CONDITIONAL_GENERIC_INHERITANCE |
| Buy Fair Value Gap | poi_rules/volume_based/buy_fair_value_gap.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bullish) | UNCLEAR | PARTIAL (narrow non-invalidation note only) | CONDITIONAL_GENERIC_INHERITANCE |
| Sell Fair Value Gap | poi_rules/volume_based/sell_fair_value_gap.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bearish) | UNCLEAR | PARTIAL (narrow non-invalidation note only) | CONDITIONAL_GENERIC_INHERITANCE |
| Base Rally | poi_rules/volume_based/base_rally.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bullish) | UNCLEAR | NOT_APPLICABLE (none defined) | CONDITIONAL_GENERIC_INHERITANCE |
| Base Drop | poi_rules/volume_based/base_drop.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bearish) | UNCLEAR | NOT_APPLICABLE (none defined) | CONDITIONAL_GENERIC_INHERITANCE |
| Bullish Pressure Wick | poi_rules/volume_based/bullish_pressure_wick.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bullish) | YES (CANDIDATE→CONFIRMED) | NOT_APPLICABLE (none defined) | DIRECT_GENERIC_INHERITANCE |
| Bearish Pressure Wick | poi_rules/volume_based/bearish_pressure_wick.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bearish) | YES (CANDIDATE→CONFIRMED) | NOT_APPLICABLE (none defined) | DIRECT_GENERIC_INHERITANCE |
| Buy-to-Sell Candle | poi_rules/volume_based/buy_to_sell_candle.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bearish) | YES (explicit `reversal_confirmation_time`) | NOT_APPLICABLE (formation-time disqualifier only) | DIRECT_GENERIC_INHERITANCE |
| Sell-to-Buy Candle | poi_rules/volume_based/sell_to_buy_candle.md | Volume-Based | PARTIAL | YES | YES | YES | YES (Bullish) | YES (explicit `reversal_confirmation_time`) | NOT_APPLICABLE (none defined) | DIRECT_GENERIC_INHERITANCE |
| Bullish Engulfing Candle | poi_rules/price_action/bullish_engulfing.md | Price Action | PARTIAL | NO | NO | NO | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Bearish Engulfing Candle | poi_rules/price_action/bearish_engulfing.md | Price Action | PARTIAL | NO | NO | NO | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Hammer | poi_rules/price_action/hammer.md | Price Action | NEEDS AUTHOR DECISION | NO | NO | NO | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Shooting Star | poi_rules/price_action/shooting_star.md | Price Action | NEEDS AUTHOR DECISION | NO | NO | NO | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Morning Star | poi_rules/price_action/morning_star.md | Price Action | PARTIAL | NO (implied, not stated) | NO | NO | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Evening Star | poi_rules/price_action/evening_star.md | Price Action | PARTIAL | NO (implied, not stated) | NO | NO | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | BLOCKED_INCOMPLETE_SPECIFICATION |
| Swing High | poi_rules/structural/swing_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Swing Low | poi_rules/structural/swing_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Equal Highs | poi_rules/structural/equal_highs.md | Structural | PARTIAL | YES (has Zone Top/Bottom) | YES | YES | YES (Bearish) | NOT_APPLICABLE (excluded regardless) | NOT_APPLICABLE (none defined) | EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY |
| Equal Lows | poi_rules/structural/equal_lows.md | Structural | PARTIAL | YES (has Zone Top/Bottom) | YES | YES | YES (Bullish) | NOT_APPLICABLE (excluded regardless) | NOT_APPLICABLE (none defined) | EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY |
| Bullish Trendline | poi_rules/structural/bullish_trendline.md | Structural | PARTIAL | NO (diagonal line, not a zone) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE (excluded regardless) | PARTIAL (`TRENDLINE_BREAK_CANDIDATE` only) | EXCLUDED_TRENDLINE |
| Bearish Trendline | poi_rules/structural/bearish_trendline.md | Structural | PARTIAL | NO (diagonal line, not a zone) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE (excluded regardless) | PARTIAL (`TRENDLINE_BREAK_CANDIDATE` only) | EXCLUDED_TRENDLINE |
| Support | poi_rules/structural/support.md | Structural | PARTIAL | YES | YES | YES | YES (Bullish) | YES (explicit non-repainting section) | PARTIAL (`SUPPORT_BREAK_CANDIDATE` — different tolerance formula) | CONDITIONAL_GENERIC_INHERITANCE |
| Resistance | poi_rules/structural/resistance.md | Structural | PARTIAL | YES | YES | YES | YES (Bearish) | YES (explicit non-repainting section) | PARTIAL (`RESISTANCE_BREAK_CANDIDATE` — different tolerance formula) | CONDITIONAL_GENERIC_INHERITANCE |
| Previous Day High | poi_rules/structural/previous_day_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Previous Day Low | poi_rules/structural/previous_day_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Previous Week High | poi_rules/structural/previous_week_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Previous Week Low | poi_rules/structural/previous_week_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Previous Month High | poi_rules/structural/previous_month_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Previous Month Low | poi_rules/structural/previous_month_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Day High | poi_rules/structural/current_day_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Day Low | poi_rules/structural/current_day_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Week High | poi_rules/structural/current_week_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Week Low | poi_rules/structural/current_week_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Month High | poi_rules/structural/current_month_high.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bearish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |
| Current Month Low | poi_rules/structural/current_month_low.md | Structural | PARTIAL | NO (single price level) | NOT_APPLICABLE | NOT_APPLICABLE | YES (Bullish) | NOT_APPLICABLE | NOT_APPLICABLE (none defined) | NOT_APPLICABLE_OTHER |

## 8. Summary Counts by Classification

| Classification | Count |
|---|---|
| A. DIRECT_GENERIC_INHERITANCE | **4** |
| B. CONDITIONAL_GENERIC_INHERITANCE | **8** |
| C. BLOCKED_INCOMPLETE_SPECIFICATION | **6** |
| D. EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY | **2** |
| E. EXCLUDED_TRENDLINE | **2** |
| F. NOT_APPLICABLE_OTHER | **14** |
| **Total** | **36** |

## 9. Summary Counts by POI Family

| Family | Direct | Conditional | Blocked | Excluded (Equal H/L) | Excluded (Trendline) | Not Applicable | Family total |
|---|---|---|---|---|---|---|---|
| Volume-Based | 4 | 6 | 0 | 0 | 0 | 0 | 10 |
| Price Action | 0 | 0 | 6 | 0 | 0 | 0 | 6 |
| Structural | 0 | 2 | 0 | 2 | 2 | 14 | 20 |
| **Total** | **4** | **8** | **6** | **2** | **2** | **14** | **36** |

## 10. Direct-Inheritance POIs (A. DIRECT_GENERIC_INHERITANCE)

| poi_name | family_override_required | blocking_gaps | rationale | recommended_next_action | evidence_status |
|---|---|---|---|---|---|
| Bullish Pressure Wick | NO | None identified | Zone Top = MIN(Open,Close), Zone Bottom = Candle Low; Bullish direction explicit; explicit CANDIDATE (pre-close) → CONFIRMED (post-close) availability timing already documented; no existing invalidation rule to conflict with the generic Close Breach/Reclaim/Genuine Invalidation lifecycle. | Eligible for propagation review in the next controlled task, once a family-specific override question (if any) is separately confirmed absent. | AUTHOR-APPROVED, ENGINEERING-PROVISIONAL, NOT YET EMPIRICALLY CALIBRATED (per Pressure Wick Standard V1 and POI Boundary Breach standard) |
| Bearish Pressure Wick | NO | None identified | Mirror of Bullish Pressure Wick: Zone Top = Candle High, Zone Bottom = MAX(Open,Close); Bearish direction explicit; same CANDIDATE→CONFIRMED availability timing; no conflicting invalidation rule. | Same as above. | Same as above. |
| Buy-to-Sell Candle | NO | None identified | Zone Top = Candidate Candle High, Zone Bottom = Candidate Candle Low; Bearish direction explicit; an explicit "Non-repainting availability" section already documents `reversal_confirmation_time`-gated exposure; existing "Invalidation" text is only a formation-time disqualifier note, not a conflicting final-invalidation rule. | Same as above. | AUTHOR-APPROVED, ENGINEERING-PROVISIONAL, NOT YET EMPIRICALLY CALIBRATED (per Buy-to-Sell/Sell-to-Buy Reversal Confirmation Standard V1 and POI Boundary Breach standard) |
| Sell-to-Buy Candle | NO | None identified | Mirror of Buy-to-Sell Candle: Zone Top/Bottom = Candidate Candle High/Low; Bullish direction explicit; same explicit non-repainting section; no conflicting invalidation rule. | Same as above. | Same as above. |

**Note:** "No family-specific override required" reflects the documentation reviewed for this audit only. It does not mean the generic thresholds have been calibrated for these POI families, and it does not authorize propagation by itself — see Section 19.

## 11. Conditional-Inheritance POIs (B. CONDITIONAL_GENERIC_INHERITANCE)

| poi_name | family_override_required | blocking_gaps / condition | rationale | recommended_next_action |
|---|---|---|---|---|
| Buy Order Block | YES | No explicit non-repainting / availability-timing statement in the current file (unlike Buy-to-Sell Candle, Support, or Pressure Wick, which have one). | Zone Top/Bottom, direction, and boundary mapping are all otherwise complete and unambiguous; the sole open question is confirming look-ahead-bias-free availability before propagation. | Confirm/document non-repainting availability timing for Order Block as part of the family-specific override review; do not invent it here. |
| Sell Order Block | YES | Same as Buy Order Block (mirrored). | Same as Buy Order Block. | Same as Buy Order Block. |
| Buy Fair Value Gap | YES | No explicit non-repainting statement; a narrow pre-existing note ("the size of the candle following the displacement candle does not invalidate the FVG") should be reconciled against the generic Close Breach Candidate / Overshoot Tolerance mechanism to confirm no conflict. | Zone Top = Low of 3rd candle, Zone Bottom = High of 1st candle; the gap-geometry rule structurally guarantees Zone Top > Zone Bottom; direction and boundary mapping are otherwise complete. | Confirm availability timing and reconcile the narrow existing note with the new Close Breach Candidate mechanism during the family-specific override review. |
| Sell Fair Value Gap | YES | Same as Buy Fair Value Gap (mirrored). | Same as Buy Fair Value Gap. | Same as Buy Fair Value Gap. |
| Base Rally | YES | No explicit non-repainting / availability-timing statement. | Zone Top = Base High, Zone Bottom = Base Low (both wick-inclusive extremes of the 2–6 candle base); direction and boundary mapping otherwise complete. | Confirm/document non-repainting availability timing for Base formations as part of the family-specific override review. |
| Base Drop | YES | Same as Base Rally (mirrored). | Same as Base Rally. | Same as Base Rally. |
| Support | YES | Pre-existing `SUPPORT_BREAK_CANDIDATE` state (Ambiguity 12, `Zone Bottom − Candle Close > Horizontal Pierce Tolerance`, where Horizontal Pierce Tolerance = `MAX(2×MinTick, 0.15×ATR14)`) overlaps conceptually with, but uses a **different formula** than, the new `CLOSE_BREACH_CANDIDATE` (Ambiguity 15, Overshoot Tolerance = `MAX(2×MinTick, MIN(0.10×ATR14, 0.25×ZoneHeight))`). Both events describe "a close beyond the zone by more than a tolerance," but with different tolerance formulas and different names. | Zone Top/Bottom, direction, and explicit non-repainting behavior are all otherwise fully documented and unambiguous. | Family-specific override question: determine whether `SUPPORT_BREAK_CANDIDATE` is superseded by, runs parallel to, or must be reconciled with `CLOSE_BREACH_CANDIDATE` before any propagation — this determination is explicitly deferred, not made here. |
| Resistance | YES | Same overlap as Support, mirrored (`RESISTANCE_BREAK_CANDIDATE` vs. `CLOSE_BREACH_CANDIDATE`). | Same as Support. | Same as Support. |

## 12. Blocked POIs (C. BLOCKED_INCOMPLETE_SPECIFICATION)

| poi_name | blocking_gaps | rationale | recommended_next_action |
|---|---|---|---|
| Bullish Engulfing Candle | No zone-drawing formula of any kind is documented for this POI ("Upper boundary: Not explicitly given as a standalone zone formula... Recorded as a gap."). | Direction is defined (Bullish), but `zone_top`/`zone_bottom` are entirely absent — the generic lifecycle cannot be evaluated without inventing the missing boundary rule, which this audit is prohibited from doing. | Remains blocked until a zone-drawing formula for Engulfing is separately author-approved. Not a candidate for this audit's propagation task. |
| Bearish Engulfing Candle | Same as Bullish Engulfing (mirrored). | Same as Bullish Engulfing. | Same as Bullish Engulfing. |
| Hammer | No zone-drawing formula ("presumably the candle's own high, but the book does not state this explicitly"); wick:body ratio itself is also undefined (`Approval status: NEEDS AUTHOR DECISION`). | Two independent gaps: missing boundary formula and missing formation-rule threshold. More fundamentally incomplete than Engulfing. | Remains blocked until both the wick:body ratio and a zone-drawing formula are separately author-approved. |
| Shooting Star | Same as Hammer (mirrored). | Same as Hammer. | Same as Hammer. |
| Morning Star | No zone-drawing formula ("implied to be the doji candle's own high, but not stated as a zone rule"); doji body-size threshold for candle 2 is undefined. | Boundary is only implied, never stated as a rule — this audit does not treat an implication as a defined boundary. | Remains blocked until a zone-drawing formula and doji-size threshold are separately author-approved. |
| Evening Star | Same as Morning Star (mirrored). | Same as Morning Star. | Same as Morning Star. |

## 13. Explicitly Excluded POIs (D. EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY, E. EXCLUDED_TRENDLINE)

| poi_name | classification | rationale |
|---|---|---|
| Equal Highs | D. EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY | Explicitly named as excluded in the POI Boundary Breach, Reclaim and Invalidation Standard's Scope section, regardless of the fact that Equal Highs/Lows now have their own Zone Top/Zone Bottom (per the Equal Highs and Equal Lows Standard, Ambiguity 5). Sweep and liquidity lifecycle remain separate and unresolved. |
| Equal Lows | D. EXCLUDED_EQUAL_HIGH_LOW_LIQUIDITY | Mirror of Equal Highs. |
| Bullish Trendline | E. EXCLUDED_TRENDLINE | A trendline is a single diagonal price level at each bar (`Line Price(t)`), not a two-sided zone — explicitly excluded by name in the standard's Scope section regardless. Line-specific break, reclaim, retest, and final invalidation remain separate and unresolved (only a `TRENDLINE_BREAK_CANDIDATE`, not final invalidation, exists today). |
| Bearish Trendline | E. EXCLUDED_TRENDLINE | Mirror of Bullish Trendline. |

## 14. Other Non-Applicable POIs (F. NOT_APPLICABLE_OTHER)

| poi_name | reason |
|---|---|
| Swing High | A single price level (Pivot Price), explicitly documented as "not applicable in the same sense... not a zone" — a reference point, not a bounded zone. |
| Swing Low | Mirror of Swing High. |
| Previous Day High | A calendar-derived single price level ("a level, not a zone - upper and lower boundary collapse to the same single price"). |
| Previous Day Low | Mirror of Previous Day High. |
| Previous Week High | Mirror of Previous Day High. |
| Previous Week Low | Mirror of Previous Day High. |
| Previous Month High | Mirror of Previous Day High. |
| Previous Month Low | Mirror of Previous Day High. |
| Current Day High | Mirror of Previous Day High. |
| Current Day Low | Mirror of Previous Day High. |
| Current Week High | Mirror of Previous Day High. |
| Current Week Low | Mirror of Previous Day High. |
| Current Month High | Mirror of Previous Day High. |
| Current Month Low | Mirror of Previous Day High. |

None of these 14 POIs were inferred to be zones from their name; all 14 explicitly document themselves as single-price levels, consistent with the audit's instruction not to silently convert a point or line into a bounded zone.

## 15. Cross-File Inconsistencies

Recorded without repair, per instruction.

| # | Inconsistency | Files affected | Description |
|---|---|---|---|
| 1 | Stale "reclaim/invalidation entirely undefined" wording | `support.md`, `resistance.md` | Both files' "Unresolved questions," "Machine-testable criteria," and "Author decision" sections still list "reclaim," "final invalidation," "confirmed break," "false break," and "role reversal" as items "not defined by this standard" without qualification. Since Ambiguity 15's resolution, reclaim and final invalidation (as `RECLAIM_CONFIRMED`/`GENUINE_INVALIDATION_CONFIRMED`) are now defined at the shared-standard level for Support/Resistance as an in-scope bounded directional POI family — the individual files were not updated to reflect this (per this task's explicit instruction not to modify `knowledge/poi_rules/`). This is the expected, documented consequence of scoping the shared standard outside individual POI files, not a defect requiring immediate repair. |
| 2 | Stale "terminology questions under Ambiguity 15 (unchanged)" wording | `buy_to_sell_candle.md`, `sell_to_buy_candle.md` | Both files' "Unresolved questions" sections still say "the terminology questions under Ambiguity 15 (unchanged)." Ambiguity 15 is now resolved (provisionally); this phrase is stale. Same root cause as #1 — individual POI files were correctly left untouched by both the Ambiguity 15 task and this audit task. |
| 3 | `SUPPORT_BREAK_CANDIDATE` / `RESISTANCE_BREAK_CANDIDATE` vs. `CLOSE_BREACH_CANDIDATE` terminology overlap | `support.md`, `resistance.md` vs. `POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` | Two independently-approved standards (Ambiguity 12 and Ambiguity 15) each define a "confirmed close beyond the zone by more than a tolerance" event for Support/Resistance, under different names and different tolerance formulas (Horizontal Pierce Tolerance vs. Overshoot Tolerance). Neither standard was modified to resolve this; see Section 16, override question 1. |
| 4 | `POI_COVERAGE_MATRIX.md` "Invalidation defined" column does not distinguish shared-standard-level readiness from individual-file-level readiness | `POI_COVERAGE_MATRIX.md` vs. all 8 Conditional/Direct POIs | The matrix's shared "Invalidation defined" column (currently "Partial" for Order Block, FVG, Base Rally/Drop, Support, Resistance, Buy-to-Sell/Sell-to-Buy) predates this audit and was deliberately left unchanged by the Ambiguity 15 task pending this applicability audit. It does not yet reflect that a shared, generic Genuine/False Invalidation lifecycle is now available (conditionally or directly) for 12 of these POIs at the shared-standard level. This is expected and intentional, not a defect — see Section 17 for the row-level propagation deferral. |
| 5 | Buy/Sell FVG boundary field labels read counter-intuitively | `buy_fair_value_gap.md`, `sell_fair_value_gap.md` | "Upper boundary" is documented as "Low of the third candle" and "Lower boundary" as "High of the first candle" (mirrored for Sell FVG). The field *names* ("Upper"/"Lower") do not immediately signal which candle they come from, but the underlying *numeric* values are correctly ordered (Zone Top > Zone Bottom is structurally guaranteed by the FVG gap-geometry rule itself). This is a documentation-clarity observation, not a geometry defect — recorded for awareness, not treated as blocking. |

No instance of Equal Highs/Lows or Trendlines being incorrectly treated as inheriting the generic bounded-zone lifecycle was found (consistency check #11 in the task instructions). No POI was found marked ready for coding despite missing boundaries, direction, or availability timing (check #12) — the Engulfing/Hammer/Star files consistently self-report their own gaps ("Machine-testable criteria: No" or "Partial" with the gap named).

## 16. Potential Family-Specific Override Questions

Recorded as open questions only. None are answered or invented by this audit.

1. **Support/Resistance break-candidate reconciliation:** should `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` (Ambiguity 12, Horizontal Pierce Tolerance) be superseded by `CLOSE_BREACH_CANDIDATE` (Ambiguity 15, Overshoot Tolerance), kept as a parallel/independent signal, or formally merged into one event with one tolerance formula?
2. **Order Block / Fair Value Gap / Base Rally-Drop non-repainting confirmation:** none of these six POI files contain an explicit "non-repainting availability" statement (unlike Pressure Wick, Buy-to-Sell/Sell-to-Buy Candle, or Support/Resistance, which do). Before propagating the generic lifecycle (which itself requires "the POI's zone becomes available without look-ahead bias"), should an explicit non-repainting statement first be added to these six files, and if so, at what confirmation point (e.g., displacement-candle close for Order Block; third-candle close for FVG; departure-candle close for Base Rally/Drop)?
3. **Fair Value Gap narrow non-invalidation note:** does the book's existing narrow rule ("the size of the candle following the displacement candle does not invalidate the FVG") need explicit reconciliation with the new Sustained Breach / Close Breach Candidate mechanics, or are they orthogonal (the narrow rule concerns candle size, not boundary breach)?
4. **Equal Highs/Equal Lows sweep lifecycle:** unresolved and out of scope for this audit — a separate, dedicated sweep-lifecycle decision remains pending (see Ambiguity register history).
5. **Trendline break/reclaim/invalidation:** unresolved and out of scope for this audit — line-specific rules remain pending (see Ambiguity register history).

## 17. Safe Propagation Candidates

The following 4 POIs have complete, unambiguous documentation against all ten applicability criteria and no identified blocking condition: **Bullish Pressure Wick, Bearish Pressure Wick, Buy-to-Sell Candle, Sell-to-Buy Candle.**

"Safe propagation candidate" here means *safe to bring forward for review in the next controlled propagation task* — it does **not** mean the lifecycle has already been propagated, calibrated, or approved for production use.

## 18. Unsafe Propagation Candidates

- **Do not propagate without further review (8):** Buy Order Block, Sell Order Block, Buy Fair Value Gap, Sell Fair Value Gap, Base Rally, Base Drop, Support, Resistance — each has a specific, named override question (Section 16) that must be resolved first.
- **Cannot propagate — specification incomplete (6):** Bullish Engulfing Candle, Bearish Engulfing Candle, Hammer, Shooting Star, Morning Star, Evening Star — missing zone-boundary formulas (and, for Hammer/Shooting Star, missing formation-rule thresholds) as a prerequisite, independent of this standard.
- **Must never inherit this lifecycle (4):** Equal Highs, Equal Lows, Bullish Trendline, Bearish Trendline — explicitly excluded by the standard's own scope, regardless of any future documentation improvement.
- **Not eligible by structure (14):** Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants — single price levels, not zones; the generic bounded-zone lifecycle does not apply to a reference point.

## 19. Recommended Next Controlled Task

**Propagate approved generic lifecycle inheritance into eligible individual POI specifications and document family-specific exceptions.**

This next task should, at minimum:
- Begin with the 4 `DIRECT_GENERIC_INHERITANCE` POIs identified in Section 10.
- Resolve the 5 named override questions in Section 16 before touching any of the 8 `CONDITIONAL_GENERIC_INHERITANCE` POIs.
- Leave the 6 `BLOCKED_INCOMPLETE_SPECIFICATION` POIs untouched until their independent boundary/formation gaps are separately resolved.
- Continue leaving Equal Highs, Equal Lows, Bullish Trendline, and Bearish Trendline entirely untouched by this lifecycle.
- Continue leaving Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants untouched, as they are not zones.
- Require its own explicit author approval before any individual POI file is edited — this audit does not pre-authorize that work.

## 20. Knowledge-Gate Impact

This audit **does not** change the final knowledge gate status. It is a classification and consistency exercise, not a propagation, calibration, or validation event.

- The final knowledge gate remains **CLOSED**.
- Phase 0G is **not** approved by this audit.
- No POI becomes APPROVED or production-ready as a result of this audit.
- No individual POI rule file, formula, threshold, or lifecycle rule was changed.
- Individual POI inheritance propagation, all 5 family-specific override questions, Trendline lifecycle, Equal High/Low sweep lifecycle, freshness, expiration, repeated-tap degradation calibration, automatic context detection, and entry/risk rules all remain open and unresolved.
- See `knowledge/KNOWLEDGE_COMPLETION_GATE.md` for the complete, authoritative gate status.

## 21. Propagation Status (2026-07-19)

**This section records what has happened since the original audit above. The original audit's classifications, counts, and POI-by-POI matrix (Sections 1–20) remain intact and unaltered by this update.**

Direct generic lifecycle inheritance has been propagated to the 4 POIs classified `DIRECT_GENERIC_INHERITANCE` in Section 10 above. Exact POIs and file paths:

| poi_name | file_path |
|---|---|
| Bullish Pressure Wick | `knowledge/poi_rules/volume_based/bullish_pressure_wick.md` |
| Bearish Pressure Wick | `knowledge/poi_rules/volume_based/bearish_pressure_wick.md` |
| Buy-to-Sell Candle | `knowledge/poi_rules/volume_based/buy_to_sell_candle.md` |
| Sell-to-Buy Candle | `knowledge/poi_rules/volume_based/sell_to_buy_candle.md` |

Each file received a new "Shared POI Boundary Lifecycle Inheritance" section documenting: applicability classification, the authoritative shared standard path, bounded-zone status, expected direction, Zone Top/Zone Bottom mapping, Entry/Far Boundary mapping, inherited event states, inherited Close Breach/Reclaim/Displacement directions, False/Genuine Invalidation meaning and effect, Repeated Tap handling, non-repainting timing, linked BTMM effect, evidence/provenance status, and remaining limitations. Each file's pre-existing "Invalidation," "Machine-testable criteria," "Unresolved questions," and "Author decision" sections were updated to cross-reference this inheritance and to correct stale wording that called reclaim, false invalidation, and genuine invalidation entirely undefined.

**No POI formation, boundary, confirmation, or strength rule was changed.** The already-approved zone mappings (`MIN(Open,Close)`/Candle Low for Bullish Pressure Wick; Candle High/`MAX(Open,Close)` for Bearish Pressure Wick; Candidate Candle High/Low for Buy-to-Sell and Sell-to-Buy Candle) were reused exactly as previously approved, not redefined. The authoritative shared lifecycle standard (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`) **remains Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved** — this propagation does not change that evidence status, and does not make any of the 4 POIs production-ready or proven profitable.

**Conditional candidates (8) remain unpropagated:** Buy Order Block, Sell Order Block, Buy Fair Value Gap, Sell Fair Value Gap, Base Rally, Base Drop, Support, Resistance — each still has its documented family-specific override question (Section 16) unresolved.

**Blocked candidates (6) remain unpropagated:** Bullish Engulfing Candle, Bearish Engulfing Candle, Hammer, Shooting Star, Morning Star, Evening Star — each still has missing zone-boundary formulas (and, for Hammer/Shooting Star, missing formation-rule thresholds) independent of this standard.

**Excluded structures remain excluded:** Equal Highs, Equal Lows, Bullish Trendline, Bearish Trendline. **No family-specific override was introduced** for any POI in this task — the 5 override questions in Section 16 remain open and unanswered.

`knowledge/POI_COVERAGE_MATRIX.md` was updated for these 4 rows only (Invalidation defined: No → Partial); no formation, boundary, confirmation, or strength readiness value was changed, and no POI was marked APPROVED. See `knowledge/KNOWLEDGE_COMPLETION_GATE.md` and `docs/PROJECT_STATE.md` for the corresponding gate and project-state updates. The final knowledge gate remains **CLOSED**; Phase 0G remains unapproved.

## 22. Conditional Reconciliation Status (2026-07-19)

**This section records what has happened since Section 21 above. The original audit's classifications, counts, and POI-by-POI matrix (Sections 1–20) and the Section 21 propagation record remain intact and unaltered by this update.**

The **Conditional POI Lifecycle Reconciliation Audit (Group 2)** has been completed and is documented in full at `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`. It reviewed all 8 POIs classified `CONDITIONAL_GENERIC_INHERITANCE` in Section 11 above:

| poi_name | reconciliation classification |
|---|---|
| Buy Order Block | C. NEEDS_AVAILABILITY_TIMING_DECISION |
| Sell Order Block | C. NEEDS_AVAILABILITY_TIMING_DECISION |
| Buy Fair Value Gap | D. NEEDS_FAMILY_SPECIFIC_OVERRIDE_DECISION |
| Sell Fair Value Gap | D. NEEDS_FAMILY_SPECIFIC_OVERRIDE_DECISION |
| Base Rally | C. NEEDS_AVAILABILITY_TIMING_DECISION |
| Base Drop | C. NEEDS_AVAILABILITY_TIMING_DECISION |
| Support | B. NEEDS_TERMINOLOGY_RECONCILIATION |
| Resistance | B. NEEDS_TERMINOLOGY_RECONCILIATION |

Classification counts: B = 2, C = 4, D = 2, A (`READY_FOR_AUTHOR_APPROVAL`) = 0, E (`BLOCKED_INCOMPLETE_SPECIFICATION`) = 0. Total = 8.

**Four author decisions were identified as required** (RECON-D1 Order Block timing, RECON-D2 Base timing, RECON-D3 FVG narrow-zone tolerance treatment, RECON-D4 Support/Resistance break-candidate terminology) — each with engineering recommendations presented but explicitly marked **NOT YET AUTHOR-APPROVED**. Full detail, formula comparisons, and decision options are in `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`.

**No conditional POI was propagated.** No individual POI rule file under `knowledge/poi_rules/` was modified by this reconciliation audit. **No original classification count from Sections 6–14 above was changed.** **No family-specific override was implemented** — RECON-D1 through RECON-D4 remain open questions with recommendations only, not decisions. The 6 `BLOCKED_INCOMPLETE_SPECIFICATION` POIs, the 4 excluded structures (Equal Highs, Equal Lows, Bullish/Bearish Trendline), and the 14 `NOT_APPLICABLE_OTHER` POIs remain untouched and unaffected by this reconciliation. The final knowledge gate remains **CLOSED**; Phase 0G remains unapproved.

## 23. Group 2 Propagation Status (2026-07-19)

**This section records what has happened since Section 22 above. The original 36-POI classification matrix (Sections 1–20) remains historically unchanged and unaltered by this update.**

Following author approval of RECON-D1 through RECON-D5 (see `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md`, Section 22), all 8 POIs classified `CONDITIONAL_GENERIC_INHERITANCE` have been propagated. RECON-D5 (added after Section 22 was first recorded) establishes Fair Value Gap lifecycle availability explicitly at the confirmed third candle's close (`fvg_available_time = third_candle_close_time`), replacing an earlier, insufficiently authorized "geometrically self-evident" framing with an explicit Author-Approved decision, for Buy Fair Value Gap and Sell Fair Value Gap only:

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

**Group 1 propagated count remains 4** (Bullish Pressure Wick, Bearish Pressure Wick, Buy-to-Sell Candle, Sell-to-Buy Candle — unchanged by this task). **Group 2 propagated count is 8.** **Total propagated bounded directional POIs is 12.**

**No original audit count was rewritten** — the Section 8 classification counts (A=4, B=8, C=6, D=2, E=2, F=14, total=36) remain exactly as originally recorded. **No blocked or excluded structure was propagated:**

- **6 `BLOCKED_INCOMPLETE_SPECIFICATION` candidates remain**: Bullish Engulfing Candle, Bearish Engulfing Candle, Hammer, Shooting Star, Morning Star, Evening Star — missing zone-boundary formulas independent of this standard.
- **Equal Highs and Equal Lows remain excluded** pending a separate sweep lifecycle.
- **Bullish and Bearish Trendlines remain excluded** pending line-specific lifecycle rules.
- **14 `NOT_APPLICABLE_OTHER` structures remain non-applicable**: Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants.

The final knowledge gate remains **CLOSED**; Phase 0G remains unapproved.
