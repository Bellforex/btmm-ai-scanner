# Final Post-Group-3 Phase 0G Knowledge-Gap Audit

## 1. Purpose

This audit is the final, comprehensive knowledge-gap review following the completion and propagation of Group 1, Group 2, and Group 3 POI lifecycle work. Its purpose is to produce a single, authoritative, dated inventory of every remaining gap that stands between the current documentation and Phase 0G closure (the author's approval that the knowledge base is complete enough to begin software implementation).

This audit does **not** resolve any blocker it identifies. It does **not** invent, approve, or implement any new trading rule of any kind. It does **not** begin software implementation. It does **not** silently resolve any contradiction it finds — every contradiction found is recorded as a blocker instead. It does **not** write, modify, or execute any code (scanner, Pine Script, database, API, Telegram, AI/ML model, backtesting, or MT4/MT5). It does **not** stage, commit, push, amend, or open a pull request. It changes exactly three files: this document, `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (current-state summary only), and `docs/PROJECT_STATE.md` (current-state summary only).

## 2. Scope

In scope: every one of the 36 individual POI rule files; the shared POI lifecycle standard and its three completed propagation rounds (Group 1, Group 2, Group 3); Equal Highs/Equal Lows; Bullish/Bearish Trendline; the market-structure coverage matrix (HH/HL/LH/LL/BOS/CHoCH); the BTMM state machine; freshness, expiration, and repeated-tap treatment; provider/symbol/timeframe policy; volume/data-contract treatment; provenance and authority consistency across all knowledge files; internal consistency between historical narrative paragraphs and current-state facts; and the boundary between knowledge documentation and software/entry/risk concerns.

Out of scope: any new rule definition of any kind; any software design or specification beyond classifying an item as requiring one; any entry, stop-loss, take-profit, risk-to-reward, lot-sizing, or news-restriction rule (these are catalogued as deferred, not resolved); any empirical calibration or backtesting; any resolution of a previously open ambiguity.

## 3. Audit Date

2026-07-20.

## 4. Current Repository Checkpoint

- Latest commit at audit start: `df164fd7056b444296c1cc6c12a4b00ce73f61e8` — "Complete Group 3 candlestick lifecycle propagation."
- Working tree: clean at audit start (no uncommitted changes prior to this audit's own three-file edit).
- `origin/main`: synchronized with local `main` at audit start.
- 36 of 36 POI rule files exist, all carry `Status: PARTIAL`. Zero POIs are `APPROVED`. Zero POIs are `NEEDS AUTHOR DECISION`.
- 18 bounded directional POIs inherit the shared POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard: 4 from Group 1 (`DIRECT_GENERIC_INHERITANCE`), 8 from Group 2 (`CONDITIONAL_GENERIC_INHERITANCE`), 6 from Group 3 (formerly `BLOCKED_INCOMPLETE_SPECIFICATION`).
- Equal Highs, Equal Lows, Bullish Trendline, and Bearish Trendline are explicitly excluded from that shared standard and retain their own, separately unresolved lifecycle questions.
- 14 structures (Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants) are single price levels, not zones, and are `NOT_APPLICABLE` to the bounded-zone lifecycle standard.
- Knowledge Completion Gate status: **CLOSED** (only condition 1 of 8 fully met, per `knowledge/KNOWLEDGE_COMPLETION_GATE.md` prior to this audit's own update).
- Phase 0G: **unapproved**.
- The private source book (`references/private/BTMM_AND_POI_TRADING_BIBLE.docx`) remains git-ignored (`.gitignore:2:references/private/*`) and was not modified by this audit.

## 5. Sources Reviewed

| Source | Review depth this audit |
|---|---|
| `knowledge/POI_COVERAGE_MATRIX.md` | Full read plus programmatic column-by-column verification (36 rows × 26 columns) |
| `knowledge/KNOWLEDGE_COMPLETION_GATE.md` | Full read |
| `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md` | Full read (tail/closing section, cross-checked against earlier full reads in prior tasks this project) |
| `knowledge/MEASUREMENT_STANDARDS.md` | Full read (1,873 lines, all 11 approved standards including the POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard) |
| `knowledge/SOURCE_INDEX.md` | Full read |
| `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` | Reviewed via its `MEASUREMENT_STANDARDS.md` summary and prior-task authorship in this conversation |
| `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md` | Reviewed via prior-task authorship in this conversation |
| `knowledge/poi_lifecycle/CONDITIONAL_LIFECYCLE_RECONCILIATION_AUDIT.md` | Reviewed via prior-task authorship in this conversation |
| `knowledge/poi_lifecycle/BLOCKED_CANDLESTICK_POI_COMPLETION_AUDIT.md` | Reviewed via prior-task authorship in this conversation |
| `knowledge/btmm/BTMM_STATE_MACHINE.md` | Full read |
| `knowledge/btmm/BTMM_MASTER_SUMMARY.md` | Reviewed (M1/M5/M15 role text cross-checked against `PROJECT_SCOPE.md` and the state machine) |
| `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md` | Full read |
| `knowledge/poi_rules/structural/equal_highs.md`, `equal_lows.md` | Full read |
| `knowledge/poi_rules/structural/bullish_trendline.md` | Full read (Bearish Trendline confirmed to mirror it structurally from prior-task authorship) |
| All 36 individual POI rule files under `knowledge/poi_rules/` | Reviewed via prior-task authorship/editing across this entire conversation, plus this audit's targeted re-checks of Order Block, Engulfing, and Base Rally/Drop timeframe-ranking language |
| `docs/PROJECT_SCOPE.md` | Full read (Sections 1-7) |
| `docs/PROJECT_STATE.md` | Full read prior to this audit (pre-audit content) |
| Repository-wide grep for "H6"/"H8"/"H12", stale-count phrases, and provenance-relevant terms | Performed |

## 6. Provenance Definitions

Each rule, standard, or claim in the knowledge base carries exactly one primary provenance label (secondary labels may also apply, but never replace the primary):

| Label | Meaning |
|---|---|
| `BOOK-EXPLICIT` | Stated directly in the private source book with no author interpretation required. |
| `BOOK-IMPLIED` | Reasonably inferable from the book's narrative/examples but not stated as an explicit numeric rule. |
| `AUTHOR-APPROVED` | Not present in the book; an engineering proposal that the author has explicitly approved as a project rule. |
| `AUTHOR-ADDED PROJECT TERMINOLOGY` | A name, state, or field invented for this project (not a book term) and explicitly author-approved. |
| `CURRENT-DOCUMENTATION-ONLY` | Exists only as internal documentation narrative (e.g., an audit's own classification) with no trading-rule content of its own. |
| `ENGINEERING-PROVISIONAL` | Author-approved but explicitly marked as requiring empirical calibration and out-of-sample validation before production use. |
| `EMPIRICAL-DECISION-REQUIRED` | Cannot be resolved by author decision alone — requires calibration against real market data/examples. |
| `NOT_DEFINED` | No rule, formula, or standard exists anywhere in the documentation for this item. |
| `CONFLICTING_EVIDENCE` | Two or more documented sources disagree and have not been reconciled. |

## 7. Phase 0G Disposition Definitions

| Code | Category | Meaning |
|---|---|---|
| A | `PHASE_0G_AUTHOR_DECISION_BLOCKER` | A qualitative trading concept must receive an explicit author decision before the knowledge gate can close. |
| B | `PHASE_0G_DOCUMENTATION_BLOCKER` | The concept itself is resolved, but the documentation describing it is incomplete, inconsistent, or stale and must be corrected. |
| C | `EMPIRICAL_CALIBRATION_ITEM` | The concept's shape/structure is already decided; what remains is calibrating thresholds/weights against real data. |
| D | `SOFTWARE_IMPLEMENTATION_SPECIFICATION` | The knowledge-level decision is complete; what remains is a software/data-contract specification, not a new trading rule. |
| E | `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED` | Explicitly out of scope for POI/BTMM knowledge — belongs to a later entry/risk phase, deliberately deferred by every relevant standard's own text. |
| F | `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` | Already has a documented, working fallback (e.g., manual/expert-labelled) and does not block current-phase work. |
| G | `HISTORICAL_OR_RESOLVED` | Previously open, now confirmed resolved by existing documentation; recorded for completeness, not as an open blocker. |

## 8. Priority Definitions

| Priority | Meaning |
|---|---|
| P0 | Must resolve before any Phase 0G approval decision. |
| P1 | Must resolve before deterministic historical annotation. |
| P2 | Must resolve before scanner implementation. |
| P3 | Must resolve before AI training/validation. |
| P4 | Must resolve before paper/live trading. |
| DEFERRED | Explicitly outside the current phase; no current dependency forces resolution. |

Priorities are assigned strictly by dependency (what blocks what), never by perceived trading importance.

## 9. Verified POI Inventory

36 rule files confirmed present and non-duplicated: 10 volume-based (`knowledge/poi_rules/volume_based/`), 6 price-action (`knowledge/poi_rules/price_action/`), 20 structural (`knowledge/poi_rules/structural/`). Every row in `knowledge/POI_COVERAGE_MATRIX.md` has a corresponding file; every file has a corresponding row. No orphan file and no missing row were found.

## 10. 36-POI Completeness Matrix

Programmatic column verification of `knowledge/POI_COVERAGE_MATRIX.md` (all 36 rows) produced the following exact counts, used as the basis for this section and cross-checked against each field's narrative status in condition-by-condition review:

| Matrix column | Value counts across 36 POIs |
|---|---|
| Definition available | Yes: 36 |
| Required location defined | Yes: 22, Partial: 2, N/A: 12 |
| Formation rule defined | Yes: 36 |
| Confirmation rule defined | Yes: 18, Partial: 6, No: 12 |
| Exact drawing boundary defined | Yes: 36 |
| Candle-size rule defined | Yes: 12, N/A: 24 |
| Wick/body rule defined | Yes: 36 |
| Trend requirement defined | Yes: 6, Partial: 6, No: 24 |
| Market-structure requirement defined | Yes: 4, Partial: 2, No: 30 |
| Liquidity requirement defined | Yes: 16, Partial: 8, No: 12 |
| Timeframe rule defined | Yes: 26, Partial: 2, No: 8 |
| Strength classification defined | Yes: 20, Partial: 16 |
| Freshness rule defined | No: 36 |
| Partial mitigation defined | No: 36 |
| Full mitigation defined | No: 36 |
| Invalidation defined | Partial: 20, No: 16 |
| Expiration defined | No: 36 |
| Positive example available | Yes: 36 |
| Negative example available | No: 36 |
| Machine-testable now | Partial: 36 |
| Author clarification required | Yes: 36 |
| Status | PARTIAL: 36 |

**Synthesized per-POI disposition, using the required field vocabulary** (`COMPLETE_FOR_PHASE_0G`/`PARTIAL`/`BLOCKED`/`EXCLUDED_BY_DESIGN`/`NOT_APPLICABLE`/`DEFERRED`/`NOT_DEFINED`/`CONFLICTING`), grouped by applicability class because every POI within a class shares identical values for the shared/generic fields (freshness, expiration, mitigation, generic lifecycle applicability):

| Group | POIs (count) | poi_name / family | boundary_status | formation_status | lifecycle_availability_status | generic_lifecycle_applicability | invalidation_status | freshness_status | expiration_status | repeated_tap_effect_status | overall recommended_disposition |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Group 1 — `DIRECT_GENERIC_INHERITANCE` | Bullish Pressure Wick, Bearish Pressure Wick, Buy-to-Sell Candle, Sell-to-Buy Candle (4) | volume_based/price_action | COMPLETE_FOR_PHASE_0G | COMPLETE_FOR_PHASE_0G | COMPLETE_FOR_PHASE_0G | INHERITED (propagated) | PARTIAL (generic breach/reclaim/invalidation defined; family-specific override research not yet performed) | NOT_DEFINED | NOT_DEFINED | PARTIAL (counted as evidence only, no degradation model) | PARTIAL — remaining blockers are freshness/expiration/repeated-tap-degradation, shared across all 18 propagated POIs (see Part 11) |
| Group 2 — `CONDITIONAL_GENERIC_INHERITANCE` | Buy Order Block, Sell Order Block, Buy Fair Value Gap, Sell Fair Value Gap, Base Rally, Base Drop, Support, Resistance (8) | volume_based/structural | COMPLETE_FOR_PHASE_0G | COMPLETE_FOR_PHASE_0G | COMPLETE_FOR_PHASE_0G (RECON-D1/D2/D5) | INHERITED (propagated, RECON-D3/D4 confirmed no override needed) | PARTIAL (same as Group 1) | NOT_DEFINED | NOT_DEFINED | PARTIAL (same as Group 1) | PARTIAL — same remaining blockers as Group 1 |
| Group 3 — formerly `BLOCKED_INCOMPLETE_SPECIFICATION` | Bullish Engulfing, Bearish Engulfing, Hammer, Shooting Star, Morning Star, Evening Star (6) | price_action | COMPLETE_FOR_PHASE_0G (GROUP3-D1/D5/D8) | COMPLETE_FOR_PHASE_0G (GROUP3-D3/D7) | COMPLETE_FOR_PHASE_0G (GROUP3-D2/D6/D9) | INHERITED (propagated, GROUP3-D4 confirmed bounded-POI role for Hammer/Shooting Star) | PARTIAL (same as Group 1) | NOT_DEFINED | NOT_DEFINED | PARTIAL (same as Group 1) | PARTIAL — same remaining blockers as Group 1 |
| Excluded — Equal High/Low liquidity | Equal Highs, Equal Lows (2) | structural | COMPLETE_FOR_PHASE_0G (Ambiguity 5) | COMPLETE_FOR_PHASE_0G | NOT_DEFINED | EXCLUDED_BY_DESIGN | NOT_DEFINED (SWEPT/BROKEN reserved, undefined) | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | BLOCKED — sweep/reclaim/invalidation lifecycle entirely undefined (see P0G-B004) |
| Excluded — Trendline | Bullish Trendline, Bearish Trendline (2) | structural | COMPLETE_FOR_PHASE_0G (Ambiguity 11) | COMPLETE_FOR_PHASE_0G | NOT_DEFINED | EXCLUDED_BY_DESIGN | NOT_DEFINED (`TRENDLINE_BREAK_CANDIDATE` defined; final invalidation is not) | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | BLOCKED — final invalidation/retest/reclaim/expiration entirely undefined (see P0G-B005) |
| Not applicable | Swing High, Swing Low, and 12 Previous/Current Period High/Low variants (14) | structural | NOT_APPLICABLE (single price level, not a zone) | COMPLETE_FOR_PHASE_0G (swings) / N/A (period levels, mechanically derived) | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE | NOT_APPLICABLE to bounded-zone lifecycle; no blocker — by design |

This table is a synthesis; `knowledge/POI_COVERAGE_MATRIX.md` remains the authoritative field-by-field source and was not modified by this audit.

## 11. 18-Propagated-POI Lifecycle Audit

All 18 propagated POIs (4 + 8 + 6) share, verbatim, the same inherited lifecycle mechanics from `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`: Close Breach Candidate detection, a 3-bar Reclaim window, a 3-bar Displacement-After-Reclaim window, the False Invalidation sequence, Sustained Breach, Genuine Invalidation (`poi_lifecycle_status = INVALIDATED`, never reactivated), Failed Reclaim, and Repeated Tap counting/classification (evidence only, no automatic degradation). This mechanism itself is fully and consistently documented for all 18 — no gap was found in the mechanism's internal consistency across the three propagation groups.

What remains open for all 18, confirmed identical across every one of them (per `MEASUREMENT_STANDARDS.md` SS19 "What Remains Unresolved," verbatim-consistent with each POI's own "Remaining limitations" section):
- Statistical repeated-tap degradation by POI family (`NOT_DEFINED`, disposition C).
- POI freshness scoring (`NOT_DEFINED`, disposition A).
- POI expiration by age (`NOT_DEFINED`, disposition A).
- Partial/full mitigation (`NOT_DEFINED` for all 36 POIs generally, not specific to the 18 — disposition A, subsumed under the freshness/mitigation blocker since the book never distinguishes the two concepts numerically).
- POI-family-specific invalidation overrides beyond RECON-D3/RECON-D4's confirmed "no override needed" findings for Order Block/Base and Support/Resistance respectively (`NOT_DEFINED` for the remaining families — disposition C).
- Entry confirmation, stop loss, take profit, risk-to-reward, lot sizing, news restrictions (disposition E, unchanged).
- Empirical calibration and out-of-sample validation of the entire lifecycle standard (disposition C).

No inconsistency was found between the three propagation groups' documentation of these shared open items — the "Remaining limitations" language is uniform across all 18 files.

## 12. Equal Highs / Equal Lows Findings

Both fully specify formation (Ambiguity 5 + Ambiguity 10 swing-source dependency), Equality Tolerance (`MAX(2×MinTick, 0.10×RefATR)`), strength tiers (STRONG/STANDARD/NOT_EQUAL), and zone drawing boundaries. Both explicitly reserve four states — FORMING, CONFIRMED, SWEPT, BROKEN — of which only FORMING and CONFIRMED are defined; **SWEPT and BROKEN are explicitly undefined by design**, not merely incomplete. Freshness, mitigation, invalidation, and expiration are all explicitly "NOT DEFINED IN BOOK" per the standard's own SS11. This is a genuine, named `PHASE_0G_AUTHOR_DECISION_BLOCKER` — see P0G-B004.

## 13. Trendline Findings

Both Bullish and Bearish Trendline fully specify anchor eligibility, slope classification (HORIZONTAL_CANDIDATE/VALID_SLOPE/TOO_STEEP), touch/pierce tolerances, and DRAFT/CONFIRMED/STRONG_TRENDLINE progression (Ambiguity 11). `TRENDLINE_BREAK_CANDIDATE` is defined but explicitly documented as "not final invalidation." Final invalidation, required retest, reclaim, false break, sweep, expiration, maximum trendline age, repeated-touch degradation, and entry confirmation are all explicitly listed as unresolved in the trendline rule files themselves. HH/HL/LH/LL/BOS/CHoCH are explicitly out of scope for trendline construction. This is a genuine `PHASE_0G_AUTHOR_DECISION_BLOCKER` — see P0G-B005.

## 14. Market-Structure Findings

Per `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`: Higher High, Higher Low, Lower High, and Lower Low each have **zero** occurrences anywhere in the private book. Change of Character has **zero** occurrences. Break of Structure is mentioned **exactly once**, with zero elaboration. The file's own governing rule states these are "not adopted as official project rules by this document... unless the author explicitly approves." 0 of 22 audited trend/structure concepts have a full numeric book definition; all 22 require author methodology; 7 of 22 reach "Partial" readiness via already-approved standards (Swing detection, Trendline construction/touches, Support, Resistance, Higher-timeframe alignment, Lower-timeframe confirmation) but still require further decisions or calibration. This is a genuine `PHASE_0G_AUTHOR_DECISION_BLOCKER` — see P0G-B003, gated by the more foundational P0G-B002.

## 15. BTMM State-Machine Findings

`knowledge/btmm/BTMM_STATE_MACHINE.md` fully and consistently defines: 5 primary states, 6 formation stages, 10 mandatory confirmation gates, cancellation-reason taxonomy, non-repainting/no-retroactive-rewriting rules, and the complete required field list. It explicitly does **not** define: HH/HL/LH/LL/BOS/CHoCH; automatic market-direction, analytical-framework, or session detection (Context Gate inputs may come from expert labels, approved external context modules, or explicit manual review until automatic rules are approved — a documented, working fallback already exists); maximum POI dwell; entry/risk rules; freshness/mitigation/expiration; repeated-touch degradation. The Volume Pillar Gate requires a `SUPPORTS` status but has no final composite `price_activity_score` formula. The Liquidity Gate requires at least one **reviewed** liquidity-evidence event and correctly integrates `RULE_BASED_REVIEWED` from Ambiguity 15 without altering pre-existing `RULE_BASED`/`MODEL_PROPOSED` values. No internal inconsistency was found in the state machine's own documentation. Automatic context detection is `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` (disposition F) because a working manual fallback already exists — see P0G-B010/P0G-B011. The `price_activity_score` composite is an `EMPIRICAL_CALIBRATION_ITEM` (disposition C) — see P0G-B012.

## 16. Freshness, Expiration, and Repeated-Tap Findings

Programmatically confirmed: **Freshness rule defined = No for all 36 POIs. Expiration defined = No for all 36 POIs. Partial mitigation defined = No for all 36 POIs. Full mitigation defined = No for all 36 POIs.** These are not partial or POI-specific gaps — they are complete, project-wide absences, consistent across every shared standard's own "What Remains Unresolved" section (Candle Measurement Standard V1, Base Formation Standard V1, Equal Highs/Lows Standard V1, Pressure Wick Standard V1, Market Speed Standard V1, POI Zone Interaction Standard V1, POI Reaction Strength Standard V1, Support/Resistance Standard V1, Buy-to-Sell/Sell-to-Buy Standard V1, BTMM Lifecycle Standard V1, and the POI Boundary Breach Standard V1 all independently list freshness/expiration/mitigation as unresolved, with zero contradiction between them). Repeated-tap counting/classification is defined and consistently documented for the 18 propagated POIs (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`, evidence only); the standard's own text explicitly frames any further degradation weighting as "an empirical-calibration question," not an open shape decision. These are P0G-B006 (freshness/mitigation), P0G-B007 (expiration), and P0G-B008 (repeated-tap degradation calibration).

## 17. Empirical-Override Findings

RECON-D3 (Fair Value Gap) and RECON-D4 (Support/Resistance) each explicitly resolved their specific family-override question — RECON-D3 confirmed no minimum-width override is needed; RECON-D4 confirmed the pre-existing break-candidate terminology and the generic breach event coexist as independent, non-merged signals. No equivalent family-specific override research has been performed for the remaining families sharing the generic lifecycle (Pressure Wick, Buy-to-Sell/Sell-to-Buy, Order Block, Base Rally/Drop, Engulfing, Hammer/Shooting Star, Morning/Evening Star) — the standard's own SS19 lists "POI-family-specific invalidation overrides" as unresolved in general, and this has not been re-examined per-family beyond the two Group 2 items already closed. This is `EMPIRICAL_CALIBRATION_ITEM` (disposition C) — see P0G-B020.

## 18. Provider/Symbol/Timeframe Findings

`docs/PROJECT_SCOPE.md` establishes a canonical provider/symbol policy (`FXCM:XAUUSD`, `FXCM:EURUSD`, `FXCM:GBPUSD`, TradingView+FXCM as the canonical chart reference) and a Section 3 timeframe-role table: Strong POI analysis = H3/H4/D1/W1; Market-structure breakdown = H1/M15; BTMM formation/execution = M15/M5/M1. Repository-wide grep for "H6"/"H8"/"H12" found **zero occurrences** — no conflict on those specific timeframes. `knowledge/btmm/BTMM_MASTER_SUMMARY.md`'s M1/M5/M15 role text is fully consistent with `PROJECT_SCOPE.md` and `BTMM_STATE_MACHINE.md`.

**A genuine, previously unrecorded inconsistency was found**: individual POI rule files for Order Block, Engulfing, and Base Rally/Base Drop each contain their own timeframe strength-ranking text that explicitly includes H1 and M15 (e.g., Order Block: "Weekly > Daily > 4H > 1H > 15-minute"). `PROJECT_SCOPE.md` Section 3 assigns H1 only to "Market-structure breakdown" and M15 only to "BTMM formation/execution" — neither appears in the "Strong POI analysis" row (H3/H4/D1/W1 only). This is a genuine documentation inconsistency (same POI-strength concept, described with two different timeframe sets in two different files), not a trading-rule conflict — no formation/boundary/lifecycle rule differs between the files. Recorded as `CONFLICTING_EVIDENCE` (secondary label) / `PHASE_0G_DOCUMENTATION_BLOCKER` (primary disposition) — see P0G-B014.

## 19. Volume/Data-Contract Findings

The Volume, Momentum, and Price-Activity Proxy Standard V1 correctly treats price/candle behavior as primary evidence and tick volume as secondary/contextual only, explicitly stating missing tick volume must never automatically invalidate a POI, and that tick-volume data must remain tied to its provider/source without cross-provider merging. Five price-activity fields (`relative_size_ratio`, `range_context_ratio`, `body_efficiency`, `directional_close_position`, `relative_tick_volume`, `tick_volume_status`) are defined as separate, non-combined fields; the final `price_activity_score` composite formula and weights are explicitly not invented. No formal data-contract specification exists yet for missing-candle handling, provider outages, weekend/session gaps, duplicate or revised candles, or multi-timeframe confirmed-candle synchronization — these are `SOFTWARE_IMPLEMENTATION_SPECIFICATION` items (disposition D), not open trading-rule questions — see P0G-B017. The single-provider (FXCM-only, no fallback) policy is an explicit, already-made author choice per `PROJECT_SCOPE.md`; what remains open is the software-level fallback/outage behavior, also disposition D — see P0G-B018.

## 20. Provenance/Authority Consistency Findings

Every approved standard in `knowledge/MEASUREMENT_STANDARDS.md` carries an explicit, consistent status block (Approved / Provisional / Author-Approved / Engineering-Provisional / NOT YET empirically calibrated / NOT YET out-of-sample validated / NOT production-approved) and correctly cross-references, rather than duplicates, the authoritative source file where one exists (e.g., the POI Boundary Breach summary cross-references `poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`). No standard was found claiming `BOOK-EXPLICIT` status for content that is actually `AUTHOR-APPROVED`/`AUTHOR-ADDED PROJECT TERMINOLOGY` — the "Book-Supported Underlying Concept" vs. "Author-Added Project Terminology" vs. "Engineering-Provisional Operational Definition" three-label discipline introduced for Ambiguity 15 is applied correctly and is not contradicted elsewhere. No provenance mislabeling was found in this audit.

## 21. Historical-Document-Consistency Findings

Two categories of finding:

**(a) Confirmed correct, not stale.** `KNOWLEDGE_COMPLETION_GATE.md` and `docs/PROJECT_STATE.md` both use an intentional append-only historical-paragraph pattern: earlier paragraphs describing smaller propagated-POI counts (e.g., "4 POIs," "12 POIs") are legitimate historical narrative, each followed later in the same file by a paragraph stating the current, correct total ("Eighteen bounded directional POIs now explicitly inherit the shared lifecycle in total"). This audit confirms this pattern is internally consistent in both files and does not constitute a documentation blocker. Separately, this audit confirms that `support.md`/`resistance.md`'s own stale "reclaim/invalidation entirely undefined" wording (present before Group 2 propagation) was correctly removed during that propagation and is not stale today.

**(b) Confirmed genuinely stale — new findings, not previously recorded.**
1. `KNOWLEDGE_COMPLETION_GATE.md` condition 2's current text states exact drawing boundary is "No for Bullish/Bearish Pressure Wick, both Trendlines, Support, Resistance, Equal Highs, Equal Lows, Swing High, and Swing Low (10 of 36 POIs)." Programmatic verification of `knowledge/POI_COVERAGE_MATRIX.md` (column "Exact drawing boundary defined") shows **all 36 rows = Yes**, including every POI named in that sentence. This claim is completely stale and self-contradicts the matrix it cites as its own source. See P0G-B001.
2. The Order Block / Engulfing / Base Rally-Drop timeframe-ranking vs. `PROJECT_SCOPE.md` Section 3 inconsistency described in Part 18. See P0G-B014.

No other stale-count or contradictory-claim pattern was found across the reviewed files.

## 22. Entry/Risk/Trade-Outcome Separation

`docs/PROJECT_SCOPE.md` Section 7 ("Separation of Validity Concepts") and every reviewed lifecycle/BTMM standard consistently treat POI validity, BTMM validity, and entry validity as four structurally separate concepts, with entry confirmation, stop loss, take profit, risk-to-reward, lot sizing, and news restrictions explicitly and repeatedly deferred (never silently assumed or partially invented) across every standard reviewed in this audit. No violation of this separation was found anywhere in the knowledge base. This is confirmed `HISTORICAL_OR_RESOLVED` in the sense that the separation principle itself is fully and consistently documented; the deferred content itself is `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED` (disposition E) — see P0G-B016.

## 23. Full Blocker Register

| ID | Title | Disposition | Priority |
|---|---|---|---|
| P0G-B001 | Gate condition 2 boundary-status text contradicts the coverage matrix | B | P0 |
| P0G-B002 | Sufficiency of manual/expert-label fallback vs. required automatic detection for trend/market-structure gate condition | A | P0 |
| P0G-B003 | HH/HL/LH/LL/BOS/CHoCH adoption decision | A | P0 |
| P0G-B004 | Equal High/Equal Low sweep lifecycle (SWEPT/BROKEN states, reclaim, invalidation) | A | P0 |
| P0G-B005 | Trendline final invalidation, retest, reclaim, false-break, and expiration lifecycle | A | P0 |
| P0G-B006 | POI freshness and mitigation model decision (all 36 POIs) | A | P0 |
| P0G-B007 | POI expiration-by-age model decision (all 36 POIs) | A | P0 |
| P0G-B008 | Repeated-tap/repeated-touch statistical degradation model | C | P3 |
| P0G-B009 | STRONG_SWING material-breach sub-rule (Meaningful Swing Standard residual) | F | DEFERRED |
| P0G-B010 | Automatic BTMM market-direction/analytical-framework context detection | F | DEFERRED |
| P0G-B011 | Automatic BTMM session-schedule detection | F | DEFERRED |
| P0G-B012 | Volume Pillar / `price_activity_score` composite threshold and weights | C | P3 |
| P0G-B013 | Gate condition 4 negative-example sufficiency policy — book provides zero negative/counter-examples for any of the 36 POIs | A | P0 |
| P0G-B014 | Timeframe role-table (`PROJECT_SCOPE.md` SS3) vs. individual POI files' own H1/M15-inclusive strength rankings | B | P2 |
| P0G-B015 | Blanket empirical calibration and out-of-sample validation across every provisional standard | C | P3 |
| P0G-B016 | Entry, stop-loss, take-profit, risk-to-reward, lot-sizing, and news-restriction rules | E | P4 |
| P0G-B017 | Data-contract specification (missing candles, provider outages, session gaps, duplicate/revised candles, multi-timeframe sync) | D | P2 |
| P0G-B018 | Provider fallback/outage behavior under the single-source (FXCM-only) policy | D | P2 |
| P0G-B019 | Author sign-off of the coverage matrix (gate condition 8) | A | P0 |
| P0G-B020 | Family-specific empirical-override research beyond RECON-D3/RECON-D4 for the remaining 16 propagated POI families | C | P3 |
| P0G-B021 | Negative/counter-example sourcing and annotation dataset creation | F | DEFERRED |

### Full Blocker Records

---

**P0G-B001 — Gate condition 2 boundary-status text contradicts the coverage matrix**
- Affected domain: Documentation consistency, `KNOWLEDGE_COMPLETION_GATE.md`.
- Affected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 2), `knowledge/POI_COVERAGE_MATRIX.md` (source of truth).
- Affected POIs/modules: All 36 (the stale text names 10 specific POIs, but the correction affects the condition's overall status statement).
- Current evidence: Condition 2 text states boundary is "No" for 10 named POIs. Programmatic verification of `POI_COVERAGE_MATRIX.md`'s "Exact drawing boundary defined" column returns `{'Yes': 36}` — zero "No" values exist.
- Primary provenance status: `CURRENT-DOCUMENTATION-ONLY`.
- Current ambiguity: None on the underlying fact (the matrix is unambiguous); the ambiguity is purely that the gate file's prose has not been updated to match.
- Why it matters: A future reader (including the author, during sign-off) could be misled into believing 10 POIs lack boundaries they already have, or could distrust the matrix due to the contradiction.
- Phase 0G disposition: B — `PHASE_0G_DOCUMENTATION_BLOCKER`.
- Author decision required: No — this is a factual correction, not a judgment call.
- Documentation correction required: Yes — condition 2's status text must be rewritten to match the matrix (boundary defined = Yes for all 36; condition 2 should instead explain why it is still not fully "MET," e.g., citing confirmation-rule gaps or other unmet sub-items if any remain relevant, or reclassifying the condition's remaining blocking reason accurately).
- Empirical calibration required: No.
- Software specification required: No.
- Dependencies: None.
- Recommended next controlled task: A dedicated, narrowly-scoped documentation-correction task limited to condition 2's text in `KNOWLEDGE_COMPLETION_GATE.md`.
- Rules that must remain unchanged: No POI rule, boundary, or lifecycle value changes — this is a prose-only correction.
- Risk of resolving incorrectly: Low — but incorrectly implying condition 2 is now fully "MET" would be wrong, since drawing boundaries are only one of several sub-requirements bundled into that condition historically.
- Gate impact: Removes a factual self-contradiction from the gate document; does not by itself change the gate's overall CLOSED status.

---

**P0G-B002 — Sufficiency of manual/expert-label fallback vs. required automatic detection for trend/market-structure gate condition**
- Affected domain: BTMM Context Gate, market-structure detection.
- Affected files: `knowledge/btmm/BTMM_STATE_MACHINE.md`, `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`, `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 5).
- Affected POIs/modules: BTMM Context Gate (market_direction_status, analytical_framework_status).
- Current evidence: `BTMM_STATE_MACHINE.md` explicitly allows Context Gate inputs to come from "expert labels, approved external context modules, or explicit manual review" until automatic rules are approved.
- Primary provenance status: `AUTHOR-APPROVED` (the fallback mechanism itself) / `NOT_DEFINED` (whether this fallback is sufficient for Phase 0G closure, or whether an automatic rule is mandatory before closure).
- Current ambiguity: The gate's own condition 5 says "NOT MET" without stating whether a manual/expert-label-only approach could ever satisfy it, or whether full automation is mandatory.
- Why it matters: This determines whether P0G-B003 (HH/HL/LH/LL/BOS/CHoCH) must be resolved before Phase 0G closes, or can be deferred behind a manual-labeling workflow.
- Phase 0G disposition: A — `PHASE_0G_AUTHOR_DECISION_BLOCKER`.
- Author decision required: Yes — whether manual/expert-labelled market-direction and analytical-framework context is acceptable for Phase 0G closure (and for how long), or whether an automatic rule is a hard prerequisite.
- Documentation correction required: No (pending the decision).
- Empirical calibration required: No.
- Software specification required: No.
- Dependencies: Gates P0G-B003.
- Recommended next controlled task: A dedicated author-decision task presenting exactly this question with no rule invention.
- Rules that must remain unchanged: The existing fallback mechanism itself (already approved) must not be altered by this decision alone.
- Risk of resolving incorrectly: Deciding "automatic required" prematurely could block progress indefinitely; deciding "manual sufficient" without limits could let permanently-manual context data silently become a permanent architecture decision without review.
- Gate impact: Directly determines whether condition 5 can close via a manual workflow or requires further author-decision work (P0G-B003) first.

---

**P0G-B003 — HH/HL/LH/LL/BOS/CHoCH adoption decision**
- Affected domain: Market structure.
- Affected files: `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`, `knowledge/btmm/BTMM_STATE_MACHINE.md` (Market Direction Gate).
- Affected POIs/modules: Market Direction Gate; indirectly affects any POI file whose "Market-structure requirement defined" or "Trend requirement defined" columns are currently No/Partial (30 of 36 rows are No for market-structure requirement).
- Current evidence: HH/HL/LH/LL/CHoCH have zero book occurrences; BOS has exactly one, unelaborated. The coverage matrix's own governing rule states these are "not adopted... unless the author explicitly approves."
- Primary provenance status: `NOT_DEFINED`.
- Current ambiguity: Whether the project adopts a specific HH/HL/LH/LL/BOS/CHoCH methodology at all, and if so, whose (there is no single universally agreed definition in the wider trading community, and the book does not supply one).
- Why it matters: Blocks a fully rule-based Market Direction Gate and any deterministic trend/structure classification used elsewhere.
- Phase 0G disposition: A.
- Author decision required: Yes — adopt/do-not-adopt, and if adopted, the exact operational definition.
- Documentation correction required: No.
- Empirical calibration required: Not at decision time; any adopted numeric threshold would need it afterward.
- Software specification required: No.
- Dependencies: Gated by P0G-B002.
- Recommended next controlled task: A dedicated author-decision task, scoped only to this question, after P0G-B002 is resolved.
- Rules that must remain unchanged: No existing swing/trendline/support/resistance rule may be silently redefined to imply HH/HL/LH/LL.
- Risk of resolving incorrectly: Adopting an internally inconsistent or ill-specified definition would propagate errors into every downstream structure-dependent rule.
- Gate impact: Directly blocks condition 5.

---

**P0G-B004 — Equal High/Equal Low sweep lifecycle (SWEPT/BROKEN states, reclaim, invalidation)**
- Affected domain: Structural POI lifecycle.
- Affected files: `knowledge/poi_rules/structural/equal_highs.md`, `equal_lows.md`, `knowledge/MEASUREMENT_STANDARDS.md` (Equal Highs/Lows section).
- Affected POIs/modules: Equal Highs, Equal Lows (2).
- Current evidence: Equality Tolerance, strength tiers, and zone boundaries are fully defined (Ambiguity 5). SWEPT and BROKEN states are explicitly reserved but undefined; freshness, mitigation, invalidation, expiration are explicitly "NOT DEFINED IN BOOK."
- Primary provenance status: `NOT_DEFINED`.
- Current ambiguity: What price behavior constitutes a "sweep" vs. a "break," what happens to the POI's status afterward, and whether/how these liquidity structures ever invalidate. The Phase 0G requirement is an explicit author decision between completion and formal deferral — Phase 0G does **not** automatically require building the entire specialized lifecycle now. The author decision must choose between at least two legitimate paths:
  - **Option A — Define specialized lifecycle now, or approve a separate follow-on task to define it**, later covering: SWEPT, BROKEN, Reclaim, False sweep or false break, Invalidation, Reactivation or no-reactivation, New structure identity, Non-repainting timing, and BTMM interaction.
  - **Option B — Explicitly defer the specialized lifecycle.** Formally preserve Equal Highs/Lows as liquidity-reference structures excluded from lifecycle-based use until a later module is approved. This option must also require documentation of: their exact exclusion from lifecycle-dependent BTMM gates; the temporary gate exemption or limitation; which operations remain permitted; which operations remain prohibited; and that no fallback lifecycle is silently inferred in the meantime.
  
  No option is approved by this correction. Existing geometry, tolerance, and strength rules (Ambiguity 5) remain unchanged either way.
- Why it matters: Equal Highs/Lows are excluded from the generic bounded-zone lifecycle standard by design (they are liquidity references, not directional zones); without either a specialized lifecycle (Option A) or a formally documented deferral (Option B), they cannot reach `COMPLETE_FOR_PHASE_0G`.
- Phase 0G disposition: A.
- Author decision required: Yes — the completion-versus-deferral choice above (Option A or Option B), not automatically the full lifecycle design itself.
- Documentation correction required: No.
- Empirical calibration required: Any resulting thresholds, yes, afterward, only if Option A is chosen and only once its formulas are defined.
- Software specification required: No.
- Dependencies: None.
- Included in minimum Phase 0G closure set: Yes — the Option A/Option B decision itself.
- Recommended next controlled task: A dedicated author-decision task presenting Option A and Option B exactly as described above; if Option A is chosen, a separate follow-on documentation task mirroring the process used for the bounded-zone POI Boundary Breach Standard (Ambiguity 15), scoped only to Equal Highs/Lows.
- Rules that must remain unchanged: Equality Tolerance, strength tiers, and zone-boundary formulas (Ambiguity 5) must not change as a side effect of either option.
- Risk of resolving incorrectly: Silently reusing the bounded-zone Overshoot/Reclaim tolerances for a liquidity-reference structure would misapply directional-zone logic to a non-directional reference level; silently inferring a fallback lifecycle under Option B without documenting the required exclusions would be an unauthorized rule invention.
- Gate impact: Directly blocks conditions 3 and 7 for these 2 POIs until the author selects and documents Option A or Option B.

---

**P0G-B005 — Trendline final invalidation, retest, reclaim, false-break, and expiration lifecycle**
- Affected domain: Structural POI lifecycle.
- Affected files: `knowledge/poi_rules/structural/bullish_trendline.md`, `bearish_trendline.md`, `knowledge/MEASUREMENT_STANDARDS.md` (Trendline section).
- Affected POIs/modules: Bullish Trendline, Bearish Trendline (2).
- Current evidence: Anchor eligibility, slope classification, touch/pierce tolerances, and DRAFT/CONFIRMED/STRONG progression are fully defined (Ambiguity 11). `TRENDLINE_BREAK_CANDIDATE` exists but is explicitly "not final invalidation." Final invalidation, retest, reclaim, false break, expiration, maximum age, and repeated-touch degradation are explicitly unresolved.
- Primary provenance status: `NOT_DEFINED`.
- Current ambiguity: What confirms a trendline is genuinely broken (vs. a false break), whether/how a broken trendline can be "reclaimed," and whether trendlines expire with age. The Phase 0G requirement is the author's explicit completion-versus-deferral decision — it is not an automatic requirement to design the entire lifecycle now. The author decision must choose between at least two legitimate paths:
  - **Option A — Define a specialized Trendline lifecycle now, or approve a separate follow-on task to define it**, with later decisions covering: Final break confirmation, Retest, Reclaim, False break, Invalidation, Reactivation, New Trendline identity, Expiration, BTMM interaction, and Non-repainting timing.
  - **Option B — Explicitly defer the specialized lifecycle.** Preserve Trendlines as analytical/reference structures whose existing DRAFT, CONFIRMED, STRONG, and `TRENDLINE_BREAK_CANDIDATE` states remain usable only within their documented limits. This option must require documentation of: lifecycle-dependent operations that remain prohibited; the temporary gate exemption or limitation; that no automatic reclaim, invalidation, or reactivation is inferred; and that no generic bounded-zone lifecycle inheritance occurs.
  
  No option is approved by this correction. Existing anchor, slope, tolerance, touch, and strength rules (Ambiguity 11) remain unchanged either way.
- Why it matters: Trendlines are excluded from the generic bounded-zone lifecycle by design (they are lines, not zones); without either a specialized lifecycle (Option A) or a formally documented deferral (Option B), they cannot reach `COMPLETE_FOR_PHASE_0G`.
- Phase 0G disposition: A.
- Author decision required: Yes — the completion-versus-deferral choice above (Option A or Option B), not automatically the full lifecycle design itself.
- Documentation correction required: No.
- Empirical calibration required: Any resulting thresholds, afterward, only if Option A is chosen and only once its formulas are defined.
- Software specification required: No.
- Dependencies: None.
- Included in minimum Phase 0G closure set: Yes — the Option A/Option B decision itself.
- Recommended next controlled task: A dedicated author-decision task presenting Option A and Option B exactly as described above; if Option A is chosen, a separate follow-on documentation task mirroring the Ambiguity 15 process, scoped only to Trendlines.
- Rules that must remain unchanged: Anchor/slope/touch-tolerance/progression formulas (Ambiguity 11) must not change as a side effect of either option.
- Risk of resolving incorrectly: Conflating `TRENDLINE_BREAK_CANDIDATE` with final invalidation would prematurely discard valid trendlines on a single wick/close event; silently inferring reclaim/invalidation/reactivation under Option B without documenting the required prohibitions would be an unauthorized rule invention.
- Gate impact: Directly blocks conditions 3 and 7 for these 2 POIs until the author selects and documents Option A or Option B.

---

**P0G-B006 — POI freshness and mitigation model decision (all 36 POIs)**
- Affected domain: Cross-POI lifecycle.
- Affected files: `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`, all 36 individual POI files, `knowledge/POI_COVERAGE_MATRIX.md`.
- Affected POIs/modules: All 36.
- Current evidence: Programmatically confirmed "Freshness rule defined = No" and "Partial mitigation defined = No" and "Full mitigation defined = No" for all 36 rows, with zero exceptions.
- Primary provenance status: `NOT_DEFINED`.
- Current ambiguity: Whether freshness/mitigation are separate concepts or one concept viewed two ways; what determines a POI is "fresh" (untouched) vs. "mitigated" (partially/fully consumed); whether mitigation is measured by touch count, penetration depth, dwell time, or a combination.
- Why it matters: Named directly in the gate's own condition 3 as a reason it remains unmet; affects every POI, not just the 18 propagated ones.
- Phase 0G disposition: A.
- Author decision required: Yes — the shape of a freshness/mitigation model (likely reusing existing Zone Interaction penetration measurements as inputs, but the classification/scoring logic itself is undecided).
- Documentation correction required: No.
- Empirical calibration required: Yes, after the shape decision.
- Software specification required: No.
- Dependencies: None (independent of B004/B005/B007, though a unified design covering all three would be efficient).
- Recommended next controlled task: A dedicated author-decision and documentation task defining a Freshness and Mitigation Standard, reusing the already-approved POI Zone Interaction Standard's penetration/overshoot measurements as inputs, without inventing new geometry.
- Rules that must remain unchanged: Zone Interaction Standard V1's Contact/Overshoot Tolerance formulas must not change.
- Risk of resolving incorrectly: Defining mitigation too strictly could cause valid POIs to be discarded after their first legitimate touch; too loosely could let genuinely exhausted POIs remain "fresh" indefinitely.
- Gate impact: Directly blocks condition 3 for all 36 POIs.

---

**P0G-B007 — POI expiration-by-age model decision (all 36 POIs)**
- Affected domain: Cross-POI lifecycle.
- Affected files: Same as P0G-B006.
- Affected POIs/modules: All 36.
- Current evidence: Programmatically confirmed "Expiration defined = No" for all 36 rows.
- Primary provenance status: `NOT_DEFINED`.
- Current ambiguity: Whether POIs expire by elapsed time, elapsed bar count, or never expire absent a lifecycle event; whether expiration varies by timeframe or POI family.
- Why it matters: Without an expiration rule, POI inventories could grow unbounded and stale zones could remain "active" indefinitely.
- Phase 0G disposition: A.
- Author decision required: Yes.
- Documentation correction required: No.
- Empirical calibration required: Yes, after the shape decision.
- Software specification required: No.
- Dependencies: None (can be resolved independently of, or jointly with, P0G-B006).
- Recommended next controlled task: A dedicated author-decision and documentation task, potentially combined with P0G-B006 into one "POI Freshness, Mitigation, and Expiration Standard" author-decision session.
- Rules that must remain unchanged: No existing lifecycle state or formula.
- Risk of resolving incorrectly: An expiration window that is too short could discard POIs that remain valid on higher timeframes (H3/H4/D1/W1); too long could let long-stale zones falsely trigger BTMM formations.
- Gate impact: Directly blocks condition 3 for all 36 POIs.

---

**P0G-B008 — Repeated-tap/repeated-touch statistical degradation model**
- Affected domain: Cross-POI lifecycle, empirical calibration.
- Affected files: `knowledge/MEASUREMENT_STANDARDS.md` (POI Boundary Breach section SS11-12), the 18 propagated POI files.
- Affected POIs/modules: The 18 propagated POIs (repeated-tap counting already exists for these; Equal Highs/Lows and Trendlines have their own separate, still-undefined touch-degradation questions covered under B004/B005).
- Current evidence: `tap_count`/`tap_classification` (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) are fully defined as evidence-only fields; the standard's own text calls further degradation "an empirical-calibration question," not an undecided shape.
- Primary provenance status: `EMPIRICAL-DECISION-REQUIRED`.
- Current ambiguity: None on the current V1 rule (no automatic degradation) — the open question is only whether/how much a 2nd, 3rd, etc. tap should reduce expected reaction strength, which requires real trade-outcome data to answer.
- Why it matters: Affects any future scoring or entry-confidence model, but does not block the current documentation phase since V1 already has a complete, working (non-degrading) rule.
- Phase 0G disposition: C — `EMPIRICAL_CALIBRATION_ITEM`.
- Author decision required: No (shape already decided); a future calibration decision, yes.
- Documentation correction required: No.
- Empirical calibration required: Yes.
- Software specification required: No.
- Dependencies: Requires historical annotated data (depends on P1-level annotation work being complete first).
- Recommended next controlled task: Deferred until backtesting/annotation data exists; not a Phase 0G blocker.
- Rules that must remain unchanged: The V1 "evidence only, no automatic degradation" rule must not be silently overridden.
- Risk of resolving incorrectly: Premature degradation weighting without data could bias the model before validation is possible.
- Gate impact: Does not block Phase 0G closure (V1 rule is already complete); relevant before AI training/validation (P3).

---

**P0G-B009 — STRONG_SWING material-breach sub-rule (Meaningful Swing Standard residual)**
- Affected domain: Swing detection, feeding Equal Highs/Lows, Trendlines, Support/Resistance strength classification.
- Affected files: Meaningful Swing High/Low Detection Standard section of `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/poi_rules/structural/swing_high.md`, `swing_low.md`.
- Affected POIs/modules: Swing High, Swing Low directly; indirectly, Equal Highs/Lows and Trendline STRONG-tier classification, which consume swing strength.
- Current evidence: The Meaningful Swing Standard (Ambiguity 10) is otherwise fully defined (5-candle pivot window, Pivot Tie Tolerance, plateau handling, Meaningful Reversal Threshold, SUPERSEDED handling, non-repainting timing) except for the exact numerical meaning of "materially breached" that partially gates the optional STRONG_SWING upgrade — named explicitly as unresolved in `KNOWLEDGE_COMPLETION_GATE.md`'s Shared Standards Status section. `STANDARD_SWING` classification (the mandatory, gate-relevant tier) is unaffected and remains fully defined and usable without this residual.
- Primary provenance status: `NOT_DEFINED` (narrow residual within an otherwise-resolved standard).
- Current ambiguity: The precise distance/ratio threshold for "material breach" of a prior swing, relevant only to the optional STRONG_SWING upgrade.
- Why it matters: Narrower than B004/B005 — STANDARD_SWING classification (the mandatory baseline used by Equal Highs/Lows, Trendlines, Support/Resistance) already works fully without it; only the optional STRONG-tier enhancement is affected. It does not gate any Phase 0G closure condition.
- Phase 0G disposition: F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G`. (Reclassified from an earlier disposition-A draft of this audit: the record's own evidence — STANDARD-tier swing detection is unaffected, and the item was already listed among explicitly deferrable items — showed it does not meet disposition A's "must block Phase 0G closure" test. No working fallback needed to be documented for this reclassification, since the mandatory STANDARD_SWING tier already functions as the complete, non-degraded baseline in its place.)
- Author decision required: No author decision is required for Phase 0G closure. A later, narrowly scoped author decision may be required before the optional STRONG_SWING material-breach tier is implemented.
- Documentation correction required: No.
- Empirical calibration required: Yes, after that later decision, if and when the STRONG_SWING tier is pursued.
- Software specification required: No.
- Dependencies: None.
- Included in minimum Phase 0G closure set: No.
- Recommended next controlled task: Defer until the project begins specialized swing-strength refinement or historical calibration work. Preserve STANDARD-tier meaningful-swing detection unchanged in the meantime.
- Rules that must remain unchanged: The rest of the Meaningful Swing Standard (pivot window, tolerances, SUPERSEDED handling, STANDARD_SWING classification).
- Risk of resolving incorrectly: An overly loose "material breach" threshold could over-award STRONG_SWING status; overly strict could make the tier practically unreachable — relevant only once this deferred item is later taken up.
- Gate impact: None on Phase 0G closure. Blocks only the optional STRONG_SWING upgrade tier, which is not required by any of the 8 gate conditions; STANDARD-tier swing detection remains fully available and unaffected.

---

**P0G-B010 — Automatic BTMM market-direction/analytical-framework context detection**
- Affected domain: BTMM Context Gate.
- Affected files: `knowledge/btmm/BTMM_STATE_MACHINE.md`.
- Affected POIs/modules: BTMM Context Gate (`market_direction_status`, `analytical_framework_status`).
- Current evidence: A working manual/expert-label/approved-external-module fallback is already explicitly documented and permitted "until automatic rules are approved."
- Primary provenance status: `AUTHOR-APPROVED` (fallback) / `NOT_DEFINED` (automatic version).
- Current ambiguity: Whether/when an automatic version will ever be required.
- Why it matters: Lower urgency than P0G-B002/B003 because a working fallback already exists and nothing currently depends on automating it.
- Phase 0G disposition: F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G`.
- Author decision required: Not currently — deferred by design.
- Documentation correction required: No.
- Empirical calibration required: No, not yet.
- Software specification required: Eventually, if automated.
- Dependencies: Related to, but distinct from, P0G-B002 (which asks whether the fallback is *sufficient for gate closure*, not whether automation will ever happen).
- Recommended next controlled task: None required now; revisit only if/when the author wants to automate context detection.
- Rules that must remain unchanged: The existing fallback mechanism.
- Risk of resolving incorrectly: N/A (deferred).
- Gate impact: None while the manual fallback remains acceptable per P0G-B002's resolution.

---

**P0G-B011 — Automatic BTMM session-schedule detection**
- Affected domain: BTMM Context Gate (`session_status`).
- Affected files: `knowledge/btmm/BTMM_STATE_MACHINE.md`, `docs/PROJECT_SCOPE.md`.
- Affected POIs/modules: BTMM Active Session Gate.
- Current evidence: Same manual-fallback mechanism as P0G-B010 applies to session detection; no automatic session-schedule rule exists yet.
- Primary provenance status: `NOT_DEFINED` (automatic version) / `AUTHOR-APPROVED` (fallback).
- Current ambiguity: Exact session boundaries/time zones for automatic detection, if ever adopted.
- Why it matters: Same reasoning as P0G-B010.
- Phase 0G disposition: F.
- Author decision required: Not currently.
- Documentation correction required: No.
- Empirical calibration required: No.
- Software specification required: Eventually, if automated.
- Dependencies: None blocking.
- Recommended next controlled task: None required now.
- Rules that must remain unchanged: The existing fallback mechanism.
- Risk of resolving incorrectly: N/A (deferred).
- Gate impact: None while the manual fallback remains acceptable.

---

**P0G-B012 — Volume Pillar / `price_activity_score` composite threshold and weights**
- Affected domain: BTMM Volume Pillar Gate.
- Affected files: `knowledge/MEASUREMENT_STANDARDS.md` (Volume/Momentum/Price-Activity Proxy Standard), `knowledge/btmm/BTMM_STATE_MACHINE.md`.
- Affected POIs/modules: BTMM Volume Pillar Gate.
- Current evidence: Five separate, non-combined price-activity fields are defined; the standard explicitly states the final `price_activity_score` formula and feature weights "remain unresolved and are not invented here." The state machine allows POI-specific approved candle rules, expert-labelled evidence, or reviewed hybrid evidence as a working substitute today.
- Primary provenance status: `NOT_DEFINED` (composite formula) / `AUTHOR-APPROVED` (component fields and interim fallback).
- Current ambiguity: What weights/thresholds combine the five fields (and optionally tick volume) into a pass/fail `SUPPORTS` determination.
- Why it matters: Needed for a fully rule-based, non-manual Volume Pillar Gate; a working interim fallback already exists.
- Phase 0G disposition: C — `EMPIRICAL_CALIBRATION_ITEM` (the fields/shape are decided; the composite requires data-driven weighting).
- Author decision required: An initial shape decision may still be useful (e.g., whether weights are linear or rule-based-AND); ultimate values require calibration.
- Documentation correction required: No.
- Empirical calibration required: Yes.
- Software specification required: No.
- Dependencies: Depends on annotated historical data (P3-level).
- Recommended next controlled task: Deferred until annotation/backtesting data exists.
- Rules that must remain unchanged: The five separate component fields and the interim fallback rule.
- Risk of resolving incorrectly: A premature composite formula could bias which BTMM setups pass the gate before validation data exists.
- Gate impact: Does not block Phase 0G closure (interim fallback already works); relevant before AI training/validation (P3).

---

**P0G-B013 — Gate condition 4 negative-example sufficiency policy**
- Affected domain: Knowledge-gate governance and evidence sufficiency (condition 4).
- Affected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 4), `knowledge/POI_COVERAGE_MATRIX.md`, `knowledge/SOURCE_INDEX.md`.
- Affected POIs/modules: All 36.
- Current evidence: Programmatically confirmed "Positive example available = Yes" for all 36 rows and "Negative example available = No" for all 36 rows — no image or example anywhere in the private book is captioned as a negative/invalid counter-example, even where narrative text describes a weaker "Scenario B."
- Primary provenance status: `NOT_DEFINED` for the sufficiency policy itself, with `BOOK-EXPLICIT` evidence that the private book does not contain the required negative/counter-example set.
- Current ambiguity: Gate Condition 4 requires positive **and** negative examples for every POI, but the private book does not supply a complete negative-example set. This blocker is the author's policy choice on how to treat that gap — it is **not** a request to build a negative-example dataset. Present only the policy options already identified:
  - **Option A:** Redefine or waive the negative-example requirement for Phase 0G.
  - **Option B:** Require external negative-example sourcing before Condition 4 can close.
  - **Option C:** Accept the current positive examples for Phase 0G and formally defer negative-example collection to the annotation and validation phase.
- Why it matters: As currently worded, condition 4 is unsatisfiable using only the source material already reviewed — leaving it as-is would keep the gate permanently CLOSED on this condition regardless of any other work completed. The P0 blocker is only the author's policy choice among the three options above; it does not automatically require building a negative-example dataset. If Option B is selected, the resulting dataset-creation work is tracked separately as `P0G-B021`, not as part of this blocker.
- Phase 0G disposition: A — `PHASE_0G_AUTHOR_DECISION_BLOCKER`.
- Author decision required: Yes — which of the three policy options to adopt.
- Documentation correction required: Possibly, depending on the approved policy (condition 4's wording may need to change to reflect the chosen option).
- Empirical calibration required: No.
- Software specification required: No.
- Dependencies: None. (`P0G-B021` depends on this blocker's outcome, not the reverse.)
- Included in minimum Phase 0G closure set: Yes — the policy decision only.
- Recommended next controlled task: Present the three evidence-sufficiency options to the author in a dedicated decision task. No example sourcing performed until the author decides. No option is approved by this correction.
- Rules that must remain unchanged: No POI rule. The permanent fact is the absence of negative examples in the book, not the permanence of this blocker — a fast author decision (Option A or C) can close it within Phase 0G.
- Risk of resolving incorrectly: Silently treating the condition as "met" without an explicit author decision would violate this audit's own no-silent-resolution rule; silently sourcing new negative examples without authorization would exceed this project's markdown-only/no-unapproved-content scope and would improperly fold `P0G-B021`-scope work into a P0 governance decision.
- Gate impact: Directly blocks condition 4, pending the policy decision only.

---

**P0G-B014 — Timeframe role-table vs. individual POI files' own H1/M15-inclusive strength rankings**
- Affected domain: Documentation consistency, timeframe policy.
- Affected files: `docs/PROJECT_SCOPE.md` (Section 3), `knowledge/poi_rules/volume_based/buy_order_block.md`, `sell_order_block.md`, `knowledge/poi_rules/price_action/bullish_engulfing.md`, `bearish_engulfing.md`, `knowledge/poi_rules/volume_based/base_rally.md`, `base_drop.md` (and any other POI file with its own timeframe-ranking language).
- Affected POIs/modules: Order Block, Engulfing, Base Rally/Drop.
- Current evidence: `PROJECT_SCOPE.md` Section 3 assigns "Strong POI analysis" to H3/H4/D1/W1 only, with H1 reserved for "Market-structure breakdown" and M15 for "BTMM formation/execution." Several individual POI files independently state a strength ranking that includes H1 and M15 (e.g., "Weekly > Daily > 4H > 1H > 15-minute").
- Primary provenance status: `CONFLICTING_EVIDENCE` (secondary) / `CURRENT-DOCUMENTATION-ONLY` (primary — no trading formula differs, only descriptive scope text).
- Current ambiguity: Whether the individual-POI rankings are simply loosely-worded historical text (predating the Section 3 table) that should be tightened to reference H3/H4/D1/W1 only, or whether the author intends POI strength ranking to legitimately span a wider timeframe set than "Strong POI analysis" implies (in which case `PROJECT_SCOPE.md` Section 3's table, not the POI files, would need updating).
- Why it matters: Could confuse a future scanner-timeframe configuration decision about which timeframes actually feed "Strong POI analysis."
- Phase 0G disposition: B — `PHASE_0G_DOCUMENTATION_BLOCKER`.
- Author decision required: A small clarifying decision on which document is authoritative for this scope question (not a new trading rule — the underlying POI formation/boundary rules are identical either way).
- Documentation correction required: Yes, once the author clarifies which side is correct.
- Empirical calibration required: No.
- Software specification required: No.
- Dependencies: None.
- Recommended next controlled task: A small, narrowly-scoped documentation-consistency task once the author states which document is authoritative.
- Rules that must remain unchanged: No POI formation/boundary/lifecycle rule.
- Risk of resolving incorrectly: Guessing which document to change without asking could silently narrow or widen a POI's intended analysis scope.
- Gate impact: Minor; relevant before scanner timeframe-configuration work (P2), not a Phase 0G approval blocker.

---

**P0G-B015 — Blanket empirical calibration and out-of-sample validation across every provisional standard**
- Affected domain: All 11 approved standards in `knowledge/MEASUREMENT_STANDARDS.md` plus the BTMM state machine and POI Boundary Breach standard.
- Affected files: `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/btmm/BTMM_STATE_MACHINE.md`, `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`.
- Affected POIs/modules: All 36, indirectly.
- Current evidence: Every provisional standard's own status block already states it is "NOT YET empirically calibrated" and "NOT YET out-of-sample validated." This is a consistent, self-declared limitation, not a contradiction.
- Primary provenance status: `ENGINEERING-PROVISIONAL`.
- Current ambiguity: None — this is a known, explicitly declared limitation, not an open question about what the rule should be.
- Why it matters: No numeric threshold in the entire knowledge base has been tested against real market data yet; this affects the reliability of every formula, not any specific one.
- Phase 0G disposition: C — `EMPIRICAL_CALIBRATION_ITEM`.
- Author decision required: No (already explicitly acknowledged everywhere).
- Documentation correction required: No.
- Empirical calibration required: Yes, universally, before production use.
- Software specification required: No.
- Dependencies: Requires backtesting/annotation infrastructure that does not yet exist.
- Recommended next controlled task: Not a Phase 0G blocker; relevant once AI training/validation begins (P3).
- Rules that must remain unchanged: All current provisional thresholds, pending calibration.
- Risk of resolving incorrectly: Treating provisional thresholds as production-final without calibration would be the actual risk this item guards against — hence its explicit declared status throughout.
- Gate impact: None on Phase 0G closure itself (already fully and consistently disclosed); relevant before AI training/validation.

---

**P0G-B016 — Entry, stop-loss, take-profit, risk-to-reward, lot-sizing, and news-restriction rules**
- Affected domain: Trade management (explicitly outside POI/BTMM knowledge scope).
- Affected files: None yet created; would be new files under a future `knowledge/` or `docs/` risk/entry area, not yet in scope.
- Affected POIs/modules: N/A — applies after a BTMM setup is confirmed, not to POI/BTMM validity itself.
- Current evidence: `docs/PROJECT_SCOPE.md` Section 7 and every reviewed standard consistently and repeatedly defer this content; `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`'s closing "still open outside this decision" list names it explicitly.
- Primary provenance status: `NOT_DEFINED` (by design — deliberately deferred, not overlooked).
- Current ambiguity: None yet raised — this is simply not yet started.
- Why it matters: Required before any paper or live trading, but not before Phase 0G knowledge closure, which concerns POI/BTMM validity only.
- Phase 0G disposition: E — `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED`.
- Author decision required: Eventually, as its own dedicated future phase.
- Documentation correction required: No.
- Empirical calibration required: Eventually.
- Software specification required: Eventually.
- Dependencies: Logically follows POI/BTMM/market-structure closure.
- Recommended next controlled task: Not applicable to Phase 0G; a distinct future phase.
- Rules that must remain unchanged: N/A.
- Risk of resolving incorrectly: N/A at this phase.
- Gate impact: None on Phase 0G; blocks paper/live trading (P4).

---

**P0G-B017 — Data-contract specification (missing candles, provider outages, session gaps, duplicate/revised candles, multi-timeframe sync)**
- Affected domain: Software/data layer (not yet built).
- Affected files: None yet — would become a future software specification document, out of scope for this knowledge-only phase.
- Affected POIs/modules: All POIs indirectly, via ATR/tick-volume/candle-confirmation inputs referenced throughout `MEASUREMENT_STANDARDS.md`.
- Current evidence: `MEASUREMENT_STANDARDS.md` repeatedly notes "Minimum Price Tick is sourced from instrument metadata once the software layer is built" and similar forward references; no formal data-contract document exists yet.
- Primary provenance status: `NOT_DEFINED` (software specification, not a trading rule).
- Current ambiguity: None on trading logic; purely an unbuilt software-layer specification.
- Why it matters: Needed before scanner implementation can begin, since every formula in `MEASUREMENT_STANDARDS.md` assumes clean, available candle/tick data.
- Phase 0G disposition: D — `SOFTWARE_IMPLEMENTATION_SPECIFICATION`.
- Author decision required: No new trading rule; a technical specification decision when software work begins.
- Documentation correction required: No.
- Empirical calibration required: No.
- Software specification required: Yes.
- Dependencies: Follows Phase 0G closure; not itself a knowledge-gate blocker.
- Recommended next controlled task: Deferred to the scanner-implementation phase (P2), outside this project's current markdown-only scope.
- Rules that must remain unchanged: All existing formula definitions that assume this data contract.
- Risk of resolving incorrectly: N/A at this phase.
- Gate impact: None on Phase 0G; relevant before scanner implementation (P2).

---

**P0G-B018 — Provider fallback/outage behavior under the single-source (FXCM-only) policy**
- Affected domain: Software/data layer.
- Affected files: `docs/PROJECT_SCOPE.md` (existing provider policy), future software specification.
- Affected POIs/modules: All, indirectly.
- Current evidence: `PROJECT_SCOPE.md` establishes FXCM as the canonical, single provider for XAUUSD/EURUSD/GBPUSD; no fallback-provider or outage-handling behavior is specified.
- Primary provenance status: `AUTHOR-APPROVED` (single-provider policy) / `NOT_DEFINED` (outage/fallback behavior).
- Current ambiguity: What the scanner should do if FXCM data is temporarily unavailable — this is a software behavior question, not a change to the provider policy itself.
- Why it matters: Needed before scanner implementation; not a knowledge-gate blocker.
- Phase 0G disposition: D — `SOFTWARE_IMPLEMENTATION_SPECIFICATION`.
- Author decision required: No new trading rule; a technical specification decision later.
- Documentation correction required: No.
- Empirical calibration required: No.
- Software specification required: Yes.
- Dependencies: Follows Phase 0G closure.
- Recommended next controlled task: Deferred to the scanner-implementation phase (P2).
- Rules that must remain unchanged: The existing single-provider policy itself.
- Risk of resolving incorrectly: N/A at this phase.
- Gate impact: None on Phase 0G; relevant before scanner implementation (P2).

---

**P0G-B019 — Author sign-off of the coverage matrix (gate condition 8)**
- Affected domain: Governance/process.
- Affected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 8), `knowledge/POI_COVERAGE_MATRIX.md`, `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`.
- Affected POIs/modules: All 36, plus market-structure concepts.
- Current evidence: Condition 8 explicitly states the matrices "have been produced by this audit but have not yet been reviewed or signed off by the author."
- Primary provenance status: `NOT_DEFINED` (as to timing) — this is an action, not a rule.
- Current ambiguity: None on what is required (an explicit author review/approval act); only when it happens is open.
- Why it matters: This is the final, literal act that must occur for Phase 0G to close — every other blocker in this register feeds into what the author is signing off on.
- Phase 0G disposition: A — `PHASE_0G_AUTHOR_DECISION_BLOCKER` (closest fit: it requires the author's own explicit approval action, distinct from a passive documentation state).
- Author decision required: Yes — the sign-off act itself.
- Documentation correction required: No.
- Empirical calibration required: No.
- Software specification required: No.
- Dependencies: Logically last — should follow resolution of the other P0 items (P0G-B001 through P0G-B007, P0G-B013), since signing off on a matrix that is itself stale (P0G-B001) or structurally incomplete (P0G-B013) would be premature.
- Recommended next controlled task: The final step of the recommended controlled sequence (Part 24), performed only after the other P0 items are addressed.
- Rules that must remain unchanged: N/A.
- Risk of resolving incorrectly: Signing off before other P0 blockers are resolved would open the gate on an incomplete/contradictory basis.
- Gate impact: Directly blocks condition 8, and by extension, final Phase 0G closure.

---

**P0G-B020 — Family-specific empirical-override research beyond RECON-D3/RECON-D4 for the remaining 16 propagated POI families**
- Affected domain: Cross-POI lifecycle, empirical calibration.
- Affected files: `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`, `knowledge/MEASUREMENT_STANDARDS.md` SS19, the 16 propagated POI files not covered by RECON-D3/RECON-D4 (Bullish/Bearish Pressure Wick, Buy-to-Sell/Sell-to-Buy Candle, Buy/Sell Order Block, Base Rally/Drop, Bullish/Bearish Engulfing, Hammer, Shooting Star, Morning Star, Evening Star).
- Affected POIs/modules: 16 of the 18 propagated POIs (Fair Value Gap and Support/Resistance already closed via RECON-D3/D4).
- Current evidence: The generic lifecycle standard's own SS19 lists "POI-family-specific invalidation overrides" as unresolved in general; only FVG (RECON-D3) and Support/Resistance (RECON-D4) have had this question explicitly examined and closed with a "no override needed" finding.
- Primary provenance status: `EMPIRICAL-DECISION-REQUIRED`.
- Current ambiguity: Whether any of the remaining 16 families has a structural reason (like FVG's potential narrow-width issue) that the generic tolerances might not handle correctly.
- Why it matters: Lower urgency than the P0 items — the generic rule already applies and produces defined, working behavior for all 18 POIs; this is about verifying no hidden family-specific edge case exists, which is best done empirically.
- Phase 0G disposition: C — `EMPIRICAL_CALIBRATION_ITEM`.
- Author decision required: Not immediately — could be resolved either by a quick per-family review (similar in kind to RECON-D3/D4) or deferred to calibration-stage testing.
- Documentation correction required: No.
- Empirical calibration required: Likely, to surface any real edge cases.
- Software specification required: No.
- Dependencies: None blocking; can proceed independently of other items.
- Recommended next controlled task: A future, narrowly-scoped review task, one family (or small group) at a time, modeled on the Group 2 reconciliation process, once P0 items are closed.
- Rules that must remain unchanged: The generic lifecycle standard's formulas.
- Risk of resolving incorrectly: Skipping this entirely could leave an undiscovered family-specific edge case (e.g., a POI type with typically very small zone heights) silently misclassified by the generic tolerances.
- Gate impact: Does not block Phase 0G closure at P0; relevant before AI training/validation (P3).

---

**P0G-B021 — Negative/counter-example sourcing and annotation dataset creation**
- Affected domain: Future annotation dataset and validation evidence.
- Affected files: None yet — would become future annotation-data artifacts, out of scope for this knowledge-only phase.
- Affected POIs/modules: All 36, only if this task is ever activated.
- Current evidence: `P0G-B013` established that the private book supplies zero negative/counter-example images for any of the 36 POIs. This record exists to hold the separate, potential future task of sourcing, creating, or annotating negative examples outside the book, split out of `P0G-B013` so that a fast P0 policy decision is never conflated with a potentially large, non-P0 data-creation effort.
- Primary provenance status: `NOT_DEFINED` / future data requirement.
- Current ambiguity: None yet raised — this task is not started and may never be required, depending on `P0G-B013`'s outcome.
- Why it matters: Only becomes relevant if (a) `P0G-B013` selects external sourcing (Option B) as mandatory before or after Phase 0G, or (b) the later annotation and validation plan requires negative examples for model training/validation.
- Phase 0G disposition: F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G`.
- Author decision required: Not for Phase 0G closure. This task becomes active only if `P0G-B013` selects external sourcing as mandatory, or the later annotation/validation plan requires negative examples.
- Documentation correction required: No current correction required beyond recording this dependency.
- Empirical calibration required: No, although the resulting dataset would later support empirical work (e.g., `P0G-B008`, `P0G-B012`, `P0G-B015`, `P0G-B020`).
- Software specification required: Not at this knowledge-audit stage.
- Dependencies: `P0G-B013` policy decision.
- Included in minimum Phase 0G closure set: No.
- Recommended next controlled task: Defer to the future annotation-data preparation phase. Define sourcing, labelling, quality-control, and provenance requirements at that stage — not during this audit or this correction.
- Rules that must remain unchanged: Existing POI rules; existing positive-example evidence; current lifecycle standards; current gate status.
- Risk of resolving incorrectly: Sourcing or fabricating negative examples without explicit author authorization would exceed this project's markdown-only/no-unapproved-content scope; this correction does not source, generate, copy, or annotate any negative example.
- Gate impact: None on Phase 0G closure; relevant only if activated by `P0G-B013`'s outcome or the later annotation/validation phase.

## 24. Blocker Counts by Disposition

**Correction note (post-verification):** this audit originally (before its own read-only consistency verification) classified P0G-B009 as disposition A / priority P1 and treated P0G-B013 as one combined record covering both the Phase 0G evidence-sufficiency policy decision and any potential future negative-example dataset work. The verification found both classifications internally inconsistent with this audit's own disposition definitions (Part 7) and its no-bundling rule. Both have since been corrected: P0G-B009 is reclassified to disposition F / priority DEFERRED (Part 23), and P0G-B013 has been split into the policy-only decision (retained as P0G-B013) and a new, separate deferred blocker, `P0G-B021`, covering only the potential future dataset-creation work. No trading rule was changed by either correction, and no blocker was resolved — both remain open, un-approved items; only their classification and record boundaries were corrected. The counts below reflect the corrected, 21-blocker register.

| Disposition | Count | Blocker IDs |
|---|---|---|
| A — `PHASE_0G_AUTHOR_DECISION_BLOCKER` | 8 | B002, B003, B004, B005, B006, B007, B013, B019 |
| B — `PHASE_0G_DOCUMENTATION_BLOCKER` | 2 | B001, B014 |
| C — `EMPIRICAL_CALIBRATION_ITEM` | 4 | B008, B012, B015, B020 |
| D — `SOFTWARE_IMPLEMENTATION_SPECIFICATION` | 2 | B017, B018 |
| E — `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED` | 1 | B016 |
| F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` | 4 | B009, B010, B011, B021 |
| G — `HISTORICAL_OR_RESOLVED` | 0 | (none — no open blocker qualifies; historical/resolved items are recorded narratively in Part 21(a) and Part 22, not as numbered blockers) |
| **Total** | **21** | |

## 25. Blocker Counts by Priority

| Priority | Count | Blocker IDs |
|---|---|---|
| P0 | 9 | B001, B002, B003, B004, B005, B006, B007, B013, B019 |
| P1 | 0 | (none — no blocker remains P1; P0G-B009, the only former P1 item, is now DEFERRED) |
| P2 | 3 | B014, B017, B018 |
| P3 | 4 | B008, B012, B015, B020 |
| P4 | 1 | B016 |
| DEFERRED | 4 | B009, B010, B011, B021 |
| **Total** | **21** | |

## 26. Exact P0 Blocker IDs

P0G-B001, P0G-B002, P0G-B003, P0G-B004, P0G-B005, P0G-B006, P0G-B007, P0G-B013, P0G-B019 — **9 blockers**, unchanged by this correction.

## 27. Minimum Phase 0G Closure Set

The minimum set that must be resolved before any Phase 0G approval decision remains exactly the same **9 P0 blockers** listed in Part 26, unchanged in membership by this correction. This is not a claim that every one of the 21 registered blockers must be resolved before Phase 0G — only these 9 are P0; the remaining 12 are P1-P4 or DEFERRED and may legitimately remain open after Phase 0G closes.

- **P0G-B009 is excluded** because the STRONG_SWING material-breach residual is now formally classified `F — EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` / priority DEFERRED: it affects only the optional STRONG_SWING upgrade, not the mandatory STANDARD_SWING baseline that Equal Highs/Lows, Trendlines, and Support/Resistance actually depend on, and no Phase 0G gate condition requires it.
- **P0G-B021 is excluded** because negative/counter-example dataset creation is deferred — it is not required to make the P0G-B013 policy decision, and only becomes active if that decision (or the later annotation/validation plan) calls for it.
- **P0G-B013 includes only the policy decision** (which of Options A/B/C to adopt for condition 4's evidence-sufficiency requirement) — it does not include, and is not satisfied by, constructing an actual negative-example dataset; that potential future work is `P0G-B021`, outside the closure set.
- **P0G-B019 remains logically last** in the set, since signing off on the coverage matrix presupposes the other 8 P0 items are already addressed.

Dependency ordering within the set:

1. P0G-B001 (documentation-only correction; no dependency on any other item; can be done first or in parallel).
2. P0G-B002 (must be resolved before P0G-B003, since it determines whether automatic market-structure detection is even required for gate closure).
3. P0G-B003 (depends on P0G-B002's outcome).
4. P0G-B004 and P0G-B005 (Equal High/Low sweep lifecycle and Trendline lifecycle; each independent of the others; each resolved via its own Option A/Option B author decision; may proceed in parallel with each other and with items 1-3 and 5-6).
5. P0G-B006 and P0G-B007 (POI freshness/mitigation and POI expiration; independent of the others; may proceed in parallel with each other, or be combined into one author-decision session).
6. P0G-B013 (the evidence-sufficiency policy decision for condition 4; independent of all others).
7. P0G-B019 (author sign-off; after all other P0 blockers, since it should only occur once P0G-B001 through P0G-B007 and P0G-B013 are addressed).

## 28. Items Explicitly Deferrable

- P1: none — no blocker in the corrected register remains P1.
- P2: P0G-B014 (timeframe-table documentation consistency), P0G-B017 (data-contract specification), P0G-B018 (provider fallback specification).
- P3: P0G-B008 (repeated-tap degradation calibration), P0G-B012 (Volume Pillar composite calibration), P0G-B015 (blanket empirical calibration/validation), P0G-B020 (remaining family-specific override research).
- P4: P0G-B016 (entry/risk/trade-management rules).
- DEFERRED: P0G-B009 (STRONG_SWING material-breach threshold — narrow residual affecting only the optional STRONG tier; STANDARD-tier swing detection is unaffected and no gate condition requires it), P0G-B010 (automatic market-direction/analytical-framework detection — working manual fallback already documented and approved), P0G-B011 (automatic session detection — working manual fallback already documented and approved), P0G-B021 (negative/counter-example sourcing and annotation dataset creation — activates only if P0G-B013 selects external sourcing, or the later annotation/validation plan requires it).

## 29. Recommended Controlled Task Sequence

**Task 1**
- Blocker IDs: P0G-B001
- Purpose: Correct gate condition 2's stale boundary-status text to match the coverage matrix.
- Expected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md` only.
- Author decision required: No.
- Commit boundary: Single, small, documentation-only commit.

**Task 2**
- Blocker IDs: P0G-B013 (policy decision only; `P0G-B021` activates separately, later, only if Option B is chosen)
- Purpose: Author decision among Option A (redefine/waive), Option B (require external sourcing), or Option C (accept positive-only, defer negative-example collection) for gate condition 4's evidence-sufficiency requirement, then update condition 4's text accordingly. No example sourcing performed as part of this task regardless of which option is chosen.
- Expected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md`, possibly `knowledge/SOURCE_INDEX.md` (informational note only).
- Author decision required: Yes.
- Commit boundary: Single commit following explicit author approval. If Option B is selected, activating `P0G-B021` is a separate, later, distinct task with its own commit boundary — not part of this one.

**Task 3**
- Blocker IDs: P0G-B002, then P0G-B003 (sequential, not parallel)
- Purpose: Decide whether manual/expert-labelled market-direction context is sufficient for Phase 0G closure; then, separately, decide the HH/HL/LH/LL/BOS/CHoCH adoption question.
- Expected files: `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`, possibly a new market-structure standard file, `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 5 update).
- Author decision required: Yes, twice (two separate decisions, not bundled).
- Commit boundary: Likely two separate commits, one per decision, following the project's established one-decision-per-record discipline.

**Task 4**
- Blocker IDs: P0G-B004
- Purpose: Author decision between Option A (define the Equal High/Equal Low sweep lifecycle — SWEPT/BROKEN states, reclaim, invalidation — now, or approve a follow-on task to define it) and Option B (formally document Equal Highs/Lows as excluded, liquidity-reference-only structures with no lifecycle, until a later module is approved). If Option A is selected, a separate follow-on documentation task defines the actual formulas.
- Expected files: `knowledge/poi_rules/structural/equal_highs.md`, `equal_lows.md`, `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/POI_COVERAGE_MATRIX.md`.
- Author decision required: Yes.
- Commit boundary: The Option A/Option B decision itself is one commit; if Option A is chosen, the full lifecycle definition mirroring the Ambiguity 15 process is a separate, later, approved-propagation commit.

**Task 5**
- Blocker IDs: P0G-B005
- Purpose: Author decision between Option A (define the Trendline final invalidation, retest, reclaim, false-break, and expiration lifecycle now, or approve a follow-on task to define it) and Option B (formally document Trendlines as usable only within their existing DRAFT/CONFIRMED/STRONG/`TRENDLINE_BREAK_CANDIDATE` states, with no reclaim/invalidation/reactivation inferred, until a later module is approved). If Option A is selected, a separate follow-on documentation task defines the actual formulas.
- Expected files: `knowledge/poi_rules/structural/bullish_trendline.md`, `bearish_trendline.md`, `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/POI_COVERAGE_MATRIX.md`.
- Author decision required: Yes.
- Commit boundary: The Option A/Option B decision itself is one commit; if Option A is chosen, the full lifecycle definition mirroring the Ambiguity 15 process is a separate, later, approved-propagation commit.

**Task 6**
- Blocker IDs: P0G-B006, P0G-B007 (may be combined into one author-decision session, but recorded as two separate decisions)
- Purpose: Author decision and documentation of a POI Freshness, Mitigation, and Expiration Standard applicable to all 36 POIs.
- Expected files: `knowledge/MEASUREMENT_STANDARDS.md`, `knowledge/POI_COVERAGE_MATRIX.md`, all 36 individual POI files (propagation phase only, after approval).
- Author decision required: Yes.
- Commit boundary: Audit/decision record commit, then a separate approved-propagation commit — following the established verify-then-commit rhythm.

**Task 7**
- Blocker IDs: P0G-B019
- Purpose: Author reviews the current `knowledge/POI_COVERAGE_MATRIX.md` and `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md` (post Tasks 1-6) and formally signs off, or identifies further gaps.
- Expected files: `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (condition 8 status update only, upon actual sign-off).
- Author decision required: Yes — the sign-off act itself.
- Commit boundary: Single commit recording the sign-off, only after Tasks 1-6 are complete and approved.

## 30. Knowledge-Gate Recommendation

The knowledge gate should remain **CLOSED**. Nine P0 blockers stand between the current state and any Phase 0G approval decision, none of which this audit is authorized to resolve. The recommended sequence in Part 29 should be followed one task at a time, each with its own dedicated author-decision step and its own dedicated verify-then-commit cycle, consistent with the pattern already established across the Group 1, Group 2, and Group 3 propagation work.

## 31. Software-Readiness Boundary

No software of any kind (scanner, Pine Script, database, API, Telegram integration, AI/ML model, backtesting engine, or MT4/MT5 execution) may begin until: (a) all 9 P0 blockers in Part 26 are resolved, (b) the author has signed off per P0G-B019, and (c) `knowledge/KNOWLEDGE_COMPLETION_GATE.md` records the gate as **OPEN**. P2-priority items (P0G-B014, P0G-B017, P0G-B018) become relevant only once software implementation actually begins — they do not block Phase 0G knowledge closure itself, but must be addressed before scanner coding starts.

## 32. Limitations

This audit is a documentation-and-classification exercise performed by re-reading existing knowledge files and running read-only verification against `knowledge/POI_COVERAGE_MATRIX.md`; it did not consult the private source book directly (no new book extraction was performed), relying instead on the book-derived content already captured in `knowledge/SOURCE_INDEX.md` and the individual rule/standard files from prior tasks in this project. It does not independently verify claims made in earlier audits about book content beyond what was already documented. It does not perform any market-data analysis, backtesting, or empirical testing. The blocker register reflects this audit's own judgment on disposition/priority classification and remains subject to author review and correction.

## 33. Audit Conclusion

This audit creates one new file (`knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md`) and updates the current-state summaries of exactly two existing files (`knowledge/KNOWLEDGE_COMPLETION_GATE.md`, `docs/PROJECT_STATE.md`). It resolves zero blockers. It approves zero new trading rules. It modifies zero POI specifications and zero lifecycle standards. It does not begin, specify, or reference any software implementation beyond classifying items as eventually requiring one. All 36 POI specifications remain `Status: PARTIAL`. All 18 propagated POIs remain propagated, unchanged. The knowledge gate remains **CLOSED**. Phase 0G remains **unapproved**. No file is staged, committed, or pushed by this audit — those actions require a separate, explicit future user instruction, exactly as with every prior task in this project.

**Post-verification correction record:** following this audit's own dedicated read-only consistency verification, two internal classification defects were found and corrected within this same document, without resolving any trading-rule blocker, approving Phase 0G, or defining any new rule: (1) `P0G-B009` was reclassified from disposition A / priority P1 to disposition F / priority DEFERRED, since its own evidence showed it does not block Phase 0G closure (it affects only the optional STRONG_SWING upgrade, not the mandatory STANDARD_SWING baseline, and no gate condition requires it); (2) the original combined `P0G-B013` record was split into a policy-only decision (retained as `P0G-B013`, disposition A / priority P0, unchanged in closure-set membership) and a new, separate, deferred blocker `P0G-B021` (disposition F / priority DEFERRED) covering only the potential future negative-example dataset-creation task. `P0G-B004` and `P0G-B005` were each revised to explicitly present both a completion path (Option A) and a formal-deferral path (Option B), clarifying that Phase 0G requires only the author's completion-versus-deferral decision, not automatic construction of a full specialized lifecycle. **The corrected register now totals 21 blockers** (disposition A=8, B=2, C=4, D=2, E=1, F=4, G=0; priority P0=9, P1=0, P2=3, P3=4, P4=1, DEFERRED=4). **The minimum Phase 0G closure set remains unchanged at exactly 9 P0 blockers.** No POI, lifecycle, market-structure, BTMM, or measurement-standard file was touched by this correction; no matrix row or status changed; no example was sourced or created; no option was selected for any author-decision blocker; the knowledge gate remains **CLOSED** and Phase 0G remains **unapproved**.

## 34. Explicit Non-Approval Statement

This document does not approve Phase 0G. It does not approve software implementation. It does not approve the scanner, database, AI model, backtesting engine, Telegram integration, or MT4/MT5 execution. It does not define any new POI formation, boundary, lifecycle, invalidation, freshness, expiration, repeated-tap, Equal High/Low sweep, Trendline lifecycle, HH/HL/LH/LL/BOS/CHoCH, BTMM gate, timeframe policy, provider policy, symbol policy, entry, stop-loss, take-profit, risk, news, session, composite-score, software-architecture, database-schema, annotation-schema, or AI-model-design rule. It records findings only.

---

## Post-Audit Resolution — P0G-B001

**Date: 2026-07-20.**

Parts 1-34 above are preserved unchanged as the **original, historical audit snapshot** — including the Part 23 summary-table row and full record for `P0G-B001` (disposition B, priority P0), and the Part 24-27 counts and closure set as they stood at the time the audit was completed and subsequently corrected for `P0G-B009`/`P0G-B013`/`P0G-B021`. None of that historical content is deleted, rewritten, or presented as though it never existed. This section records what has changed **since** that snapshot, as a separate, dated, append-only resolution.

**What happened:** `P0G-B001` was a documentation-only contradiction — `knowledge/KNOWLEDGE_COMPLETION_GATE.md` condition 2 claimed 10 of 36 POIs lacked exact drawing boundaries, while `knowledge/POI_COVERAGE_MATRIX.md` already showed boundaries defined for all 36. This task re-verified the coverage matrix programmatically (all 36 rows inspected: "Exact drawing boundary defined" = Yes for 36 of 36, No for 0, Partial for 0, no other value present) and then corrected only the stale condition 2 wording in `knowledge/KNOWLEDGE_COMPLETION_GATE.md` to match the matrix.

**No POI specification changed. No boundary formula changed. No lifecycle rule changed. No trading rule was approved.** This resolution is purely a documentation correction of a contradiction the audit itself had already found and flagged but explicitly declined to fix at the time (per the audit's own no-silent-resolution rule).

**`P0G-B001` is now RESOLVED.** Its current disposition is **G — `HISTORICAL_OR_RESOLVED`** (previously B — `PHASE_0G_DOCUMENTATION_BLOCKER` in the original snapshot above). It is removed from the active minimum Phase 0G closure set and no longer carries an active priority (it is not P0, P1-P4, or DEFERRED — those labels apply only to open items).

**Historical audit blocker count identified: 21** (`P0G-B001` through `P0G-B021`, as fixed by the original audit and its post-verification correction — unchanged).

**Current active unresolved blocker count: 20** (`P0G-B001` excluded; `P0G-B002` through `P0G-B021` remain open).

**Current disposition counts across all 21 identified items** (including the now-resolved `P0G-B001`): A=8, B=1, C=4, D=2, E=1, F=4, G=1 — total 21. (Compare to the original snapshot's B=2, G=0; `P0G-B001` moved from B to G, all other counts unchanged.)

**Current active unresolved blockers exclude the one G item:** active unresolved disposition counts are A=8, B=1, C=4, D=2, E=1, F=4 — total 20.

**Current active priority counts:** P0=8, P1=0, P2=3, P3=4, P4=1, DEFERRED=4 — total active unresolved = 20. (Compare to the original snapshot's P0=9; `P0G-B001` is no longer counted under any active priority.)

**The minimum Phase 0G closure set now contains exactly 8 active blockers**, all still P0:
1. `P0G-B002`
2. `P0G-B003`
3. `P0G-B004`
4. `P0G-B005`
5. `P0G-B006`
6. `P0G-B007`
7. `P0G-B013`
8. `P0G-B019`

`P0G-B001` is removed from this set because it is resolved. `P0G-B009` remains excluded (deferred outside Phase 0G — STRONG_SWING material-breach residual, optional tier only). `P0G-B021` remains excluded (deferred annotation-dataset work, dependent on `P0G-B013`). `P0G-B019` remains logically last.

**Current dependency order within the active closure set:**
1. `P0G-B002`
2. `P0G-B003` (after `P0G-B002`)
3. `P0G-B004` and `P0G-B005` (each independent, each its own Option A/Option B decision)
4. `P0G-B006` and `P0G-B007` (each independent, may be combined)
5. `P0G-B013` (the evidence-sufficiency policy decision)
6. `P0G-B019` (after all other active P0 blockers)

**No other blocker was resolved by this task.** `P0G-B002` through `P0G-B021` remain exactly as classified in Parts 23-27 above, with the `P0G-B009`/`P0G-B013`/`P0G-B021` corrections from the prior verification pass still in effect. No option was selected for `P0G-B004`, `P0G-B005`, or `P0G-B013`. No Equal High/Low lifecycle, Trendline lifecycle, freshness rule, expiration rule, or HH/HL/LH/LL/BOS/CHoCH rule was defined. No composite score was created. No software implementation began.

All 36 POI specifications remain `Status: PARTIAL`. All 18 propagated POIs (4 Group 1 + 8 Group 2 + 6 Group 3) remain propagated, unchanged. **The knowledge gate remains CLOSED — resolving one documentation-only blocker does not open the gate. Phase 0G remains unapproved.** Nothing was staged, committed, or pushed by this task.

---

## Post-Audit Author Decisions — P0G-B002 through P0G-B007 and P0G-B013

**Date: 2026-07-20.**

The original blocker records and historical snapshots in Parts 1-34 and the "Post-Audit Resolution — P0G-B001" section above are preserved unchanged. This section records seven further author decisions, as a separate, dated, append-only addition. None of these decisions approve Phase 0G; none resolve `P0G-B019`; none write software.

**Decision 1 — `P0G-B002` (manual context fallback vs. automatic detection).** Approved: the reviewed manual/expert-label fallback is sufficient for Phase 0G; automatic trend and market-structure detection is deferred to a later specialized module and is not required for knowledge-gate closure. `context_input_source = MANUAL_EXPERT_LABEL` is the permitted source; an automatic detector is not required for Phase 0G, not yet approved, and remains required later only for autonomous operation. This decision does not define HH/HL/LH/LL/BOS/CHoCH, does not change a BTMM gate, and does not approve scanner implementation, automatic detection, or Phase 0G. Documented in `knowledge/btmm/BTMM_STATE_MACHINE.md`, "Phase 0G Input-Source Policy," and `knowledge/btmm/BTMM_MASTER_SUMMARY.md`. **Status: RESOLVED. Disposition: G — `HISTORICAL_OR_RESOLVED`. No active priority.**

**Decision 2 — `P0G-B003` (HH/HL/LH/LL/BOS/CHoCH adoption).** Approved: HH, HL, LH, LL, BOS, and CHoCH are formally deferred outside Phase 0G — not mandatory machine concepts for the current knowledge phase. Permitted reviewed context labels: `context_direction = BULLISH | BEARISH | NEUTRAL | UNCLEAR`, `context_alignment = ALIGNED | MISALIGNED | UNCLEAR` (supplementary reviewed-evidence annotations only, documented in `knowledge/btmm/BTMM_STATE_MACHINE.md`, "Phase 0G Input-Source Policy" — they do not replace or redefine the existing `market_direction_status`/`analytical_framework_status` gate fields). Existing Meaningful Swing rules (Ambiguity 10) are unchanged. None of the six deferred terms (HH, HL, LH, LL, BOS, CHoCH) is defined by this decision. **Status: active deferred item. Disposition: F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G`. Priority: DEFERRED. Removed from the minimum Phase 0G closure set.**

**Decision 3 — `P0G-B004` (Equal Highs/Equal Lows specialized lifecycle).** Approved: Option B — formally defer the specialized Equal High/Low lifecycle outside Phase 0G. Equal Highs and Equal Lows remain confirmed liquidity-reference structures. Permitted: detect and confirm the structure; record its zone; record its strength; use it as reviewed liquidity-location evidence; use reviewed manual expert liquidity-event labels (`liquidity_event_source = MANUAL_EXPERT_LABEL`). Prohibited: automatically declaring SWEPT or BROKEN; automatically declaring reclaim or false sweep; automatically invalidating or reactivating the structure; applying the generic bounded lifecycle; treating the structure as a bullish/bearish entry zone; silently inferring an event from a wick or close; allowing the structure alone to satisfy a BTMM liquidity-event gate. Documented in `knowledge/poi_rules/structural/equal_highs.md` and `equal_lows.md`, "Phase 0G Specialized Lifecycle Deferral." Existing geometry, tolerance, confirmation, and strength rules (Ambiguity 5) unchanged. **Status: active deferred item. Disposition: F. Priority: DEFERRED. Removed from the minimum closure set.**

**Decision 4 — `P0G-B005` (Trendline specialized lifecycle).** Approved: formally defer the specialized Trendline lifecycle outside Phase 0G. Permitted: construct Bullish/Bearish Trendlines; record DRAFT/CONFIRMED/STRONG/BREAK_CANDIDATE; use Trendlines as reviewed analytical context; use reviewed manual expert event labels (`trendline_event_source = MANUAL_EXPERT_LABEL`). Prohibited: treating BREAK_CANDIDATE as final invalidation; automatically confirming a final break; automatically declaring retest, reclaim, or false break; automatically invalidating, reactivating, or expiring a Trendline; applying the generic bounded lifecycle; silently creating a new Trendline identity; allowing an unresolved Trendline event to satisfy a BTMM gate. Documented in `knowledge/poi_rules/structural/bullish_trendline.md` and `bearish_trendline.md`, "Phase 0G Specialized Lifecycle Deferral." Existing anchors, slopes, tolerances, touches, and states unchanged. **Status: active deferred item. Disposition: F. Priority: DEFERRED. Removed from the minimum closure set.**

**Decision 5 — `P0G-B006` (POI freshness and mitigation model).** Approved: observational freshness only. `freshness_status = FRESH | INTERACTED | NOT_AUTOMATICALLY_EVALUATED | NOT_APPLICABLE`. A bounded directional POI is `FRESH` from its approved availability time; the first qualifying interaction (reusing the existing approved interaction and Contact Tolerance rules) changes it to `INTERACTED`; a Near Miss does not remove freshness; `INTERACTED` cannot return to `FRESH` for the same POI identity; a newly formed POI requires a new POI ID and its own freshness state. Freshness is descriptive only and does not automatically change strength, validity, lifecycle status, BTMM eligibility, entry validity, invalidation, or expiration. For Equal Highs/Lows and Trendlines, `freshness_status = NOT_AUTOMATICALLY_EVALUATED` while their specialized lifecycles remain deferred. `PARTIALLY_MITIGATED`, `FULLY_MITIGATED`, and any degradation effect remain undefined. Documented in `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`. **Status: RESOLVED. Disposition: G. No active priority.**

**Decision 6 — `P0G-B007` (POI expiration-by-age model).** Approved: track POI age descriptively with no automatic age-based expiration. `age_start_time = approved_poi_available_time`; permitted descriptive fields `age_in_confirmed_bars`, `elapsed_time_since_availability`; `automatic_age_expiration = DISABLED`; `age_effect = DESCRIPTIVE_ONLY`. Age alone never causes weakening, expiration, invalidation, BTMM rejection, entry prohibition, strength reduction, or a new POI identity. Day/week/month reference structures continue their own existing period-rollover and identity rules, unchanged. For Equal Highs/Lows and Trendlines, `expiration_status = NOT_AUTOMATICALLY_EVALUATED`. No candle-count, elapsed-time, or family-specific expiration threshold is defined. Documented in `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`. **Status: RESOLVED. Disposition: G. No active priority.**

**Decision 7 — `P0G-B013` (negative-example sufficiency policy).** Approved: positive examples, explicit mandatory rules, and explicit rejection criteria are sufficient for Phase 0G. For each POI, Phase 0G documentation must establish what qualifies, which mandatory condition causes rejection, how boundaries are drawn, when confirmation occurs, and what remains unresolved or deferred. A comprehensive negative/counter-example dataset is deferred to the annotation and validation phase; `P0G-B021` remains responsible for later negative examples, near-miss examples, ambiguous examples, rejected candidates, provenance, and reviewer labels. No example was sourced, created, copied, or annotated by this decision. Documented in `knowledge/btmm/BTMM_MASTER_SUMMARY.md`, "Phase 0G Input-Source Policy." **Status: RESOLVED. Disposition: G. No active priority.**

**`P0G-B021` remains unaffected by these seven decisions: Disposition F, Priority DEFERRED, active deferred item, dependent on `P0G-B013`'s outcome (now resolved as above) — its own dataset-creation work remains deferred to the future annotation-data preparation phase and was not performed here.**

**Current disposition counts across all 21 identified blockers, after these seven decisions:**

| Disposition | Count | Blocker IDs |
|---|---|---|
| A — `PHASE_0G_AUTHOR_DECISION_BLOCKER` | 1 | B019 |
| B — `PHASE_0G_DOCUMENTATION_BLOCKER` | 1 | B014 |
| C — `EMPIRICAL_CALIBRATION_ITEM` | 4 | B008, B012, B015, B020 |
| D — `SOFTWARE_IMPLEMENTATION_SPECIFICATION` | 2 | B017, B018 |
| E — `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED` | 1 | B016 |
| F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` | 7 | B003, B004, B005, B009, B010, B011, B021 |
| G — `HISTORICAL_OR_RESOLVED` | 5 | B001, B002, B006, B007, B013 |
| **Total** | **21** | |

**Current active unresolved blocker total: 16** (the 5 G items — `P0G-B001`, `P0G-B002`, `P0G-B006`, `P0G-B007`, `P0G-B013` — are excluded).

**Current active priority counts:**

| Priority | Count | Blocker IDs |
|---|---|---|
| P0 | 1 | B019 |
| P1 | 0 | (none) |
| P2 | 3 | B014, B017, B018 |
| P3 | 4 | B008, B012, B015, B020 |
| P4 | 1 | B016 |
| DEFERRED | 7 | B003, B004, B005, B009, B010, B011, B021 |
| **Total active unresolved** | **16** | |

**The only active P0 blocker is `P0G-B019`.** **The current minimum Phase 0G closure set is exactly one blocker: `P0G-B019`** — the author's final review and sign-off of the coverage matrix and Phase 0G knowledge package. This section does not resolve `P0G-B019`, does not approve Condition 8, and does not approve Phase 0G.

No POI boundary, formation rule, or generic lifecycle applicability was changed by these seven decisions. No Equal High/Low sweep, Trendline final-break, reclaim, or false-break rule was defined. No HH/HL/LH/LL/BOS/CHoCH rule was defined. No automatic freshness-degradation or age-expiration threshold was introduced. No negative example was sourced, created, copied, or annotated. All 36 POI specifications remain `Status: PARTIAL`; all 18 propagated POIs remain unchanged. **The knowledge gate remains CLOSED. Phase 0G remains unapproved.** Nothing was staged, committed, or pushed by this task.

---

## Post-Decision Clarifications — P0G-B006 Interaction Timing and P0G-B013A Rejection Applicability

**Date: 2026-07-20.**

Two Author-Approved corrective clarifications were applied to the documentation package already recorded above, following the read-only verification that identified the "post-availability interaction" ambiguity and the Pressure Wick/period-reference rejection-applicability gaps. Neither clarification reopens, reverses, or changes the disposition of any blocker; both remain within the scope of already-RESOLVED items.

**`P0G-B006` interaction-timing clarification:**
- Machine rule: `qualifying_interaction_time > poi_availability_time` — the interaction must be strictly later than the POI's own approved availability time.
- Formation candles and availability/confirmation candles are excluded from counting as the first qualifying interaction; an event whose time exactly equals `poi_availability_time` does not qualify.
- Documented in `knowledge/poi_lifecycle/POI_FRESHNESS_AND_AGE_STANDARD.md`, "7. First Qualifying Interaction."
- No interaction threshold, Contact Tolerance formula, or Zone Interaction Standard geometry was changed — only the timing gate was clarified.
- No age-counting convention (0-vs-1 bar indexing) was introduced.
- `P0G-B006` remains **RESOLVED**. Disposition remains **G — `HISTORICAL_OR_RESOLVED`**. No blocker-count change.

**`P0G-B013A` rejection-applicability clarification:**
- Explicit rejection criteria remain required for candidate-based and pattern-based POIs (unchanged).
- `rejection_criterion_status = NOT_APPLICABLE` is now explicitly recorded for exactly the 12 deterministic calendar-reference POIs (Current Day High/Low, Previous Day High/Low, Current Week High/Low, Previous Week High/Low, Current Month High/Low, Previous Month High/Low) — documented in each file's own new "Phase 0G Rejection-Criterion Applicability" section, reasoning that a completed or active calendar period necessarily has a high and a low, so no candidate-rejection concept applies.
- `rejection_criterion_status = EXPLICIT` is now explicitly recorded for both Bullish and Bearish Pressure Wick — documented as a clarification of the pre-existing "all of" mandatory-condition structure (Lower/Upper Wick Share, Body Efficiency, wick-ratio, Close Position): if any mandatory threshold is not satisfied, the candle does not become a confirmed Pressure Wick POI. No new numeric threshold, lifecycle state, or `REJECTED` status was introduced.
- The remaining 22 candidate/pattern-based POIs already carried explicit, machine-identifiable rejection language in their existing text prior to this task (e.g., "the candidate is rejected," `INVALID BASE`, `REJECTED_ORIGIN_CANDIDATE`, `TOO_STEEP`, `NOT EQUAL`, `REJECTED_CANDIDATE_CANDLE`, `REJECTED_DIRECTIONAL_CONTINUATION`, `REJECTED_INSUFFICIENT_REVERSAL`) and were not modified by this task.
- This clarification does not remove rejection requirements from any pattern-based POI, does not resolve rollover timing, does not change any period-identity rule, boundary, confirmation/availability rule, or interaction rule, and does not create any entry or risk rule.
- `P0G-B013` remains **RESOLVED**. Disposition remains **G**. `P0G-B021` remains deferred for dataset creation, unaffected. No new blocker was created. No blocker-count change.

**36-POI rejection-applicability result:** `EXPLICIT = 24` (22 pre-existing + 2 Pressure Wick newly tagged), `NOT_APPLICABLE = 12` (period-reference POIs newly tagged), `MISSING = 0`. Total = 36.

**Blocker arithmetic — unchanged by this task:**

| | |
|---|---|
| Historical identified | 21 |
| Active unresolved | 16 |
| Disposition A | 1 (`P0G-B019`) |
| Disposition B | 1 (`P0G-B014`) |
| Disposition C | 4 |
| Disposition D | 2 |
| Disposition E | 1 |
| Disposition F | 7 |
| Disposition G | 5 |
| **Total** | **21** |
| Active priority P0 | 1 (`P0G-B019`) |
| Active priority P1 | 0 |
| Active priority P2 | 3 |
| Active priority P3 | 4 |
| Active priority P4 | 1 |
| Active priority DEFERRED | 7 |
| **Total active** | **16** |

**Only active P0 blocker: `P0G-B019`. Minimum Phase 0G closure set: `P0G-B019` only.** `P0G-B019` is **not resolved** by this task. No POI status changed from `PARTIAL`. No numeric trading threshold changed. No lifecycle state was created. No mitigation percentage, mitigation state, repeated-tap degradation, automatic expiration, age threshold, or period-rollover-timing rule was defined or modified. All 18 propagated POIs remain unchanged. **The knowledge gate remains CLOSED. Phase 0G remains unapproved.** Nothing was staged, committed, or pushed by this task.

---

## Post-Audit Resolution — P0G-B019 Final Author Sign-Off

**Date: 2026-07-21.**

Parts 1-34 and every prior append-only section above (including the historical Part 23 full record for `P0G-B019`, disposition A / priority P0) are preserved unchanged. This section records the final author decision on `P0G-B019` — the author's own coverage-matrix sign-off act, gate condition 8 — as a separate, dated, append-only resolution.

1. **The author approved `P0G-B019` Option A.** The current Phase 0G knowledge package (36 POI specifications, the 18-POI shared-lifecycle propagation, all Author-Approved standards in `knowledge/MEASUREMENT_STANDARDS.md`, the BTMM state machine, the POI Boundary Breach standard, the freshness/age standard, and every decision recorded in this audit through `P0G-B013A`) is accepted as the **AUTHOR-APPROVED CONTROLLED BASELINE**.
2. **The current knowledge package is accepted as the controlled Phase 0G baseline** — reviewed, sufficient to authorize *controlled foundation work only* (see `knowledge/KNOWLEDGE_COMPLETION_GATE.md` for the exact permitted/prohibited scope), not as a claim of technical completeness.
3. **`P0G-B019` is RESOLVED.**
4. **`P0G-B019` moves from disposition A to disposition G — `HISTORICAL_OR_RESOLVED`.**
5. **`P0G-B019` has no active priority** (not P0, P1-P4, or DEFERRED).
6. **The minimum Phase 0G closure set is now empty** — zero active P0 blockers remain.
7. **Active unresolved blockers reduce from 16 to 15** (`P0G-B019` excluded as resolved).
8. **Historical identified blockers remain 21**, unchanged.
9. **Conditions 3 and 7 retain their technical statuses** — Condition 3 remains `NOT MET`; Condition 7 remains `PARTIALLY MET` and is explicitly treated as non-passing for gate-condition purposes. Neither was altered by this sign-off.
10. **All 36 POI specifications remain `Status: PARTIAL`.** None became `APPROVED`.
11. **This sign-off is not production approval.** It is not an empirical-validation claim, not an out-of-sample-validation claim, and not a profitability or production-readiness claim.
12. **Every deferred blocker remains active and binding** — `P0G-B003` (HH/HL/LH/LL/BOS/CHoCH), `P0G-B004` (Equal High/Low specialized lifecycle), `P0G-B005` (Trendline specialized lifecycle), `P0G-B008/B012/B015/B020` (empirical-calibration items), `P0G-B009/B010/B011/B021` (explicitly deferred items), `P0G-B014` (documentation blocker), `P0G-B016` (entry/risk, deferred), `P0G-B017/B018` (software specifications) are all unresolved and unaffected by this decision.

**Governance distinction — three separate concepts, never merged:**
- **Phase 0G transition approval** (this section): the author's explicit decision to accept the current knowledge package as a controlled baseline and open the gate for controlled foundation work only.
- **Technical completion of all deferred requirements**: NOT achieved by this section — mitigation, family-specific overrides, Equal High/Low and Trendline specialized lifecycles, automatic trend/market-structure detection, empirical calibration, and out-of-sample validation all remain open, tracked exactly as before.
- **Production approval**: NOT granted by this section, and not implied by it. No live trading, automated execution, or AI training is authorized.

**Current disposition counts across all 21 identified blockers, after this decision:**

| Disposition | Count | Blocker IDs |
|---|---|---|
| A — `PHASE_0G_AUTHOR_DECISION_BLOCKER` | 0 | (none) |
| B — `PHASE_0G_DOCUMENTATION_BLOCKER` | 1 | B014 |
| C — `EMPIRICAL_CALIBRATION_ITEM` | 4 | B008, B012, B015, B020 |
| D — `SOFTWARE_IMPLEMENTATION_SPECIFICATION` | 2 | B017, B018 |
| E — `ENTRY_RISK_OR_TRADE_MANAGEMENT_DEFERRED` | 1 | B016 |
| F — `EXPLICITLY_DEFERRED_OUTSIDE_PHASE_0G` | 7 | B003, B004, B005, B009, B010, B011, B021 |
| G — `HISTORICAL_OR_RESOLVED` | 6 | B001, B002, B006, B007, B013, B019 |
| **Total** | **21** | |

**Active unresolved blocker total: 15** (the 6 G items excluded).

**Current active priority counts:**

| Priority | Count | Blocker IDs |
|---|---|---|
| P0 | 0 | (none) |
| P1 | 0 | (none) |
| P2 | 3 | B014, B017, B018 |
| P3 | 4 | B008, B012, B015, B020 |
| P4 | 1 | B016 |
| DEFERRED | 7 | B003, B004, B005, B009, B010, B011, B021 |
| **Total active unresolved** | **15** | |

**Minimum Phase 0G closure set: EMPTY.** Zero active P0 blockers remain.

**Governance statuses, effective this date:**

```
Phase 0G Status        = AUTHOR-APPROVED CONTROLLED BASELINE
Knowledge Gate Status   = OPEN FOR CONTROLLED FOUNDATION WORK
Gate Opening Basis      = AUTHOR-APPROVED BASELINE EXCEPTION
```

**Permitted controlled foundation scope**: repository and package structure; configuration models; data contracts; candle schemas; POI and event schemas; annotation structures; provenance structures; deterministic unit-test fixtures; historical-data ingestion planning; validation infrastructure; audit infrastructure.

**Still prohibited**: live trading; automated order execution; MT4 bots; MT5 bots; Telegram trading signals; production deployment; autonomous trend detection; automatic Equal High/Low sweep detection; automatic Trendline final-break detection; AI model training; unreviewed self-learning; entry automation; stop-loss automation; take-profit automation; position-sizing automation; risk automation; profitability claims; production-readiness claims.

No blocker other than `P0G-B019` was resolved by this decision. No POI, lifecycle, boundary, formation, or invalidation rule was changed. No numeric trading threshold was changed. No software implementation began. All 36 POI specifications remain `Status: PARTIAL`; all 18 propagated POIs remain unchanged. **The knowledge gate is now `OPEN FOR CONTROLLED FOUNDATION WORK` only — not approved for production, trading automation, or AI training.** Nothing was staged, committed, or pushed by this task.
