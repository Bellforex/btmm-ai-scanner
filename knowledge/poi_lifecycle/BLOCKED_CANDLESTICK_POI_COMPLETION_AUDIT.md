# Blocked Candlestick POI Specification Completion Audit — Group 3

## 1. Purpose and Scope

This document is the authoritative output of the **Blocked Candlestick POI Specification Completion Audit (Group 3)**. Its sole purpose is to review the 6 POIs classified `BLOCKED_INCOMPLETE_SPECIFICATION` in [POI_LIFECYCLE_APPLICABILITY_AUDIT.md](POI_LIFECYCLE_APPLICABILITY_AUDIT.md) and determine exactly what is missing from each specification, cite the exact source evidence for every finding, and prepare (but not answer) the author decisions required before any of these six could even be considered for lifecycle-inheritance review.

This is a **documentation audit and author-decision preparation task only**. It does **not**:
- Modify any file under `knowledge/poi_rules/`.
- Complete any candlestick specification.
- Propagate the shared lifecycle to any POI.
- Invent a zone-drawing formula, formation threshold, confirmation timing rule, or pattern precedence rule.
- Approve, calibrate, validate, or make production-ready any POI.

No result in this document may be described as empirically proven or production-ready.

**Correction note (2026-07-19):** this document was corrected following a completed read-only consistency verification. The original version misclassified Bullish and Bearish Engulfing as `B. NEEDS_ZONE_BOUNDARY_DECISION` and bundled the zone-boundary source and lifecycle-availability-timing questions into single decision records for Engulfing (GROUP3-D1), Hammer/Shooting Star (GROUP3-D3), and Morning/Evening Star (GROUP3-D5). This correction reclassifies all 6 POIs as `E. NEEDS_MULTIPLE_AUTHOR_DECISIONS` and replaces the original 5 bundled decision records with 9 clean, single-category records (GROUP3-D1 through GROUP3-D9), 7 unconditional and 2 conditional. No option within any decision record was resolved by this correction.

## 2. Audit Date

2026-07-19 (corrected 2026-07-19)

## 3. Evidence Status

All standards referenced by this audit remain:

- **AUTHOR-APPROVED**
- **AUTHOR-ADDED PROJECT TERMINOLOGY** where applicable
- **ENGINEERING-PROVISIONAL**
- **NOT YET EMPIRICALLY CALIBRATED**
- **NOT YET OUT-OF-SAMPLE VALIDATED**
- **NOT PRODUCTION-APPROVED**

## 4. Sources Reviewed

- The 6 individual POI files listed in Section 5 (read in full; **not modified**).
- `references/private/BTMM_AND_POI_TRADING_BIBLE.docx` — read in full for the Engulfing (paragraphs corresponding to the book's "ENGULFING PATTERN," "BEARISH ENGULFING PATTERN," "ENGULFING PATTERN STRENGTH CLASSIFICATION," and "IMPORTANT DISTINCTION BETWEEN AN ENGULFING PATTERN AND AN ORDER BLOCK" sections) and Hammer/Shooting Star/Morning Star/Evening Star ("2.Hammer — Marteau/ Shooting star," "2.Morning star — Evening star," and "HOW TO SELECT THE BEST MORNING/EVENING STAR" sections). **Not modified, not staged, not committed.** Only short, clearly-attributed excerpts are quoted below where necessary to support a provenance finding — this document does not reproduce the book at length.
- `knowledge/SOURCE_INDEX.md` (cross-checked for paragraph citations; not modified).
- `knowledge/MEASUREMENT_STANDARDS.md` (checked for existing shared-standard coverage of these 6 POIs; not modified).
- `knowledge/POI_COVERAGE_MATRIX.md` (reconciled against; history-note-only update).
- `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md` (Group 1/2 audit; append-only update).
- `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (the authoritative shared lifecycle standard these POIs would eventually inherit from; not modified).
- `knowledge/KNOWLEDGE_COMPLETION_GATE.md` (reconciled against; updated separately).
- `docs/PROJECT_STATE.md` (reconciled against; updated separately).

## 5. Exact Six-POI Inventory

| poi_name | file_path | matches POI_COVERAGE_MATRIX.md row |
|---|---|---|
| Bullish Engulfing Candle | `knowledge/poi_rules/price_action/bullish_engulfing.md` | Yes |
| Bearish Engulfing Candle | `knowledge/poi_rules/price_action/bearish_engulfing.md` | Yes |
| Hammer | `knowledge/poi_rules/price_action/hammer.md` | Yes |
| Shooting Star | `knowledge/poi_rules/price_action/shooting_star.md` | Yes |
| Morning Star | `knowledge/poi_rules/price_action/morning_star.md` | Yes |
| Evening Star | `knowledge/poi_rules/price_action/evening_star.md` | Yes |

All 6 files exist and match their corresponding `POI_COVERAGE_MATRIX.md` row identity (name, family, direction). **No discrepancy found.**

## 6. Provenance Definitions

| Label | Meaning |
|---|---|
| `BOOK-EXPLICIT` | The private source material states this fact directly, in words, without inference. |
| `BOOK-IMPLIED` | The private source material strongly suggests this fact (e.g., naming a candle as "the POI" without giving its exact numeric boundary), but does not state it as an explicit rule or formula. |
| `AUTHOR-PREVIOUSLY-APPROVED` | Resolved by a prior, separately author-approved standard (e.g., Candle Measurement Standard V1, Small Candle Standard V1) that already applies to this POI. |
| `CURRENT-FILE-ONLY` | Stated only in the individual POI rule file itself (an engineering observation or cross-reference note), with no direct book or prior-standard support. |
| `ENGINEERING-PROVISIONAL` | A reasonable, evidence-based inference this audit draws from the above sources, explicitly not yet an author decision. |
| `NOT DEFINED` | No source — book, prior standard, or file — defines this fact at all. |

Every material finding below carries exactly one of these six labels.

## 7. Completion-Classification Definitions

| Code | Name | Meaning |
|---|---|---|
| A | `READY_FOR_LIFECYCLE_AFTER_DOCUMENTATION` | Zone boundaries, direction, and availability timing are already sufficiently documented; only explicit author approval to propagate remains. |
| B | `NEEDS_ZONE_BOUNDARY_DECISION` | Pattern and direction are sufficiently defined; **only** the exact POI zone or boundaries require author approval — no other material category (timing, formation, role) is open. |
| C | `NEEDS_CONFIRMATION_TIMING_DECISION` | Pattern and zone are defined; **only** non-repainting confirmation or lifecycle-availability timing is unclear. |
| D | `NEEDS_FORMATION_RULE_DECISION` | A numeric formation threshold (e.g., a ratio) is referenced qualitatively by the book but never quantified, and this is the only open category. |
| E | `NEEDS_MULTIPLE_AUTHOR_DECISIONS` | More than one material category (zone boundary, confirmation/availability timing, formation rule, or POI role/bounded-status) requires approval for the same POI. |
| F | `NOT_A_BOUNDED_POI` | The pattern is better modeled as a signal/confirmation event than as its own bounded zone; no zone-boundary decision should be attempted. |

No additional primary classification was created. **F was not assigned to any of the 6 POIs by this audit** — for Hammer/Shooting Star, whether they should be modeled as signal-only (matching F) or as a bounded zone (matching B/C) is itself an open, gating author decision (GROUP3-D4) rather than settled unilaterally in either direction.

**Correction applied:** the categories above are applied strictly on a per-material-category basis. A POI whose only stated gap is "zone boundary" but which *also* has an independent, unresolved confirmation/availability-timing question does **not** qualify for B — B requires timing to already be sufficiently documented or to follow automatically and unambiguously from the boundary choice with no separate judgment required. Where a plausible boundary choice does not, by itself, mechanically fix the availability moment (i.e., a rational author could approve the same boundary under more than one timing rule), timing is counted as an independent, separate category and the POI is classified E.

## 8. Full Six-POI Matrix

| Field | Bullish Engulfing | Bearish Engulfing | Hammer | Shooting Star | Morning Star | Evening Star |
|---|---|---|---|---|---|---|
| Pattern candle count | 2 | 2 | 1 | 1 | 3 | 3 |
| Expected direction | BULLISH | BEARISH | BULLISH | BEARISH | BULLISH | BEARISH |
| Signal role | YES | YES | YES | YES | YES | YES |
| POI role | YES (location-dependent) | YES (location-dependent) | YES (location-dependent) | YES (location-dependent) | YES (explicit) | YES (explicit) |
| Formation conditions | YES | YES | PARTIAL (qualitative only) | PARTIAL (qualitative only) | PARTIAL (qualitative only) | PARTIAL (qualitative only) |
| Size requirements | YES (2x/3x, AUTHOR-PREVIOUSLY-APPROVED) | YES (2x/3x, AUTHOR-PREVIOUSLY-APPROVED) | NOT_APPLICABLE (no multi-candle ratio) | NOT_APPLICABLE (no multi-candle ratio) | PARTIAL (2-3x candle3 vs. candle2, no formal Standard/Strong split) | PARTIAL (2-3x candle3 vs. candle2, no formal Standard/Strong split) |
| Wick/body requirements | PARTIAL (body engulfment mandatory; wick engulfment strength-only) | PARTIAL (body engulfment mandatory; wick engulfment strength-only) | UNCLEAR (long wick, small body; no ratio) | UNCLEAR (long wick, small body; no ratio) | UNCLEAR (candle 2 "small or doji"; no ratio) | UNCLEAR (candle 2 "small or doji"; no ratio) |
| Required preceding context/location | YES (within/middle of a move, not origin) | YES (within/middle of a move, not origin) | PARTIAL (qualitative "around a support zone") | PARTIAL (qualitative "around a resistance zone") | PARTIAL (qualitative "around demand/support") | PARTIAL (qualitative "around supply/resistance") |
| Confirmation conditions | YES (own-candle close, direction + size) | YES (own-candle close, direction + size) | PARTIAL (close-color rule only) | PARTIAL (close-color rule only) | PARTIAL (candle-3 close + ratio) | PARTIAL (candle-3 close + ratio) |
| Strength classification | YES (Standard/Strong + HTF/LTF) | YES (Standard/Strong + HTF/LTF) | NO (close-color only, no tiers) | NO (close-color only, no tiers) | PARTIAL (ratio only, no named tiers) | PARTIAL (ratio only, no named tiers) |
| Zone source | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | BOOK-IMPLIED (doji/middle candle) | BOOK-IMPLIED (doji/middle candle) |
| Zone Top status | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | BOOK-IMPLIED, not formalized | BOOK-IMPLIED, not formalized |
| Zone Bottom status | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | NOT_DEFINED | BOOK-IMPLIED, not formalized | BOOK-IMPLIED, not formalized |
| Creates a bounded directional zone? | NO (pending decision) | NO (pending decision) | UNCLEAR (pending decision) | UNCLEAR (pending decision) | PARTIAL (pending formula confirmation) | PARTIAL (pending formula confirmation) |
| Pattern confirmation time | BOOK-EXPLICIT / AUTHOR-PREVIOUSLY-APPROVED (engulfing candle's own close: direction, body-engulfment, and size-ratio all evaluable) | BOOK-EXPLICIT / AUTHOR-PREVIOUSLY-APPROVED (engulfing candle's own close) | NOT_DEFINED (candle's own close is `ENGINEERING-PROVISIONAL` only) | NOT_DEFINED (candle's own close is `ENGINEERING-PROVISIONAL` only) | BOOK-EXPLICIT (third-candle close, when the >= 2-3x ratio is evaluable) | BOOK-EXPLICIT (third-candle close) |
| POI lifecycle availability time | NOT_DEFINED (depends on GROUP3-D2) | NOT_DEFINED (depends on GROUP3-D2) | NOT_DEFINED (depends on GROUP3-D4, then GROUP3-D6 if applicable) | NOT_DEFINED (depends on GROUP3-D4, then GROUP3-D6 if applicable) | NOT_DEFINED (depends on GROUP3-D9) | NOT_DEFINED (depends on GROUP3-D9) |
| Existing invalidation readiness | NO | NO | NO | NO | NO | NO |
| Source provenance (overall) | BOOK-EXPLICIT formation/size/location/confirmation; NOT DEFINED boundary and lifecycle availability | BOOK-EXPLICIT formation/size/location/confirmation; NOT DEFINED boundary and lifecycle availability | BOOK-EXPLICIT shape/location; NOT DEFINED ratio, boundary, role, and timing | BOOK-EXPLICIT shape/location; NOT DEFINED ratio, boundary, role, and timing | BOOK-EXPLICIT structure/confirmation; BOOK-IMPLIED boundary; NOT DEFINED doji threshold and lifecycle availability | BOOK-EXPLICIT structure/confirmation; BOOK-IMPLIED boundary; NOT DEFINED doji threshold and lifecycle availability |
| Blocking gaps | 2 (zone boundary; lifecycle availability timing) | 2 (zone boundary; lifecycle availability timing) | 4 (wick:body ratio; POI role/bounded status; zone boundary [conditional]; lifecycle availability timing [conditional]) | 4 (wick:body ratio; POI role/bounded status; zone boundary [conditional]; lifecycle availability timing [conditional]) | 3 (doji threshold; zone boundary; lifecycle availability timing) | 3 (doji threshold; zone boundary; lifecycle availability timing) |
| Author decisions required | GROUP3-D1, GROUP3-D2 | GROUP3-D1, GROUP3-D2 | GROUP3-D3, GROUP3-D4, GROUP3-D5*, GROUP3-D6* | GROUP3-D3, GROUP3-D4, GROUP3-D5*, GROUP3-D6* | GROUP3-D7, GROUP3-D8, GROUP3-D9 | GROUP3-D7, GROUP3-D8, GROUP3-D9 |
| Safe rules requiring no decision | Formation, size ratio, strength tiers, location rule, Order Block distinction, pattern-confirmation time | Formation, size ratio, strength tiers, location rule, Order Block distinction, pattern-confirmation time | Long-wick/small-body shape, close-color signal rule, Pressure Wick label-preservation | Long-wick/small-body shape, close-color signal rule, Pressure Wick label-preservation | 3-candle structure, first/third candle direction, final-candle ratio, HTF recommendation, doji-as-POI concept, pattern-confirmation time | 3-candle structure, first/third candle direction, final-candle ratio, HTF recommendation, doji-as-POI concept, pattern-confirmation time |
| Recommended next action | Resolve GROUP3-D1, then GROUP3-D2 | Resolve GROUP3-D1, then GROUP3-D2 | Resolve GROUP3-D3 and GROUP3-D4; resolve GROUP3-D5/D6 only if GROUP3-D4 approves a bounded POI | Resolve GROUP3-D3 and GROUP3-D4; resolve GROUP3-D5/D6 only if GROUP3-D4 approves a bounded POI | Resolve GROUP3-D7, GROUP3-D8, GROUP3-D9 | Resolve GROUP3-D7, GROUP3-D8, GROUP3-D9 |
| **Completion classification** | **E** | **E** | **E** | **E** | **E** | **E** |

*GROUP3-D5 and GROUP3-D6 are **conditional** — required only if GROUP3-D4 approves Hammer and/or Shooting Star as a bounded directional POI. If GROUP3-D4 selects signal-only, GROUP3-D5 and GROUP3-D6 are `NOT APPLICABLE` for the affected POI.

## 9. Engulfing Findings

**Bullish Engulfing / Bearish Engulfing.**

1. **Exact candle count:** 2. `BOOK-EXPLICIT` ("It is formed by two candles").
2. **Which candle is small:** the first (immediately preceding) candle. `BOOK-EXPLICIT`.
3. **Which candle is large:** the second (engulfing) candle. `BOOK-EXPLICIT`.
4. **Existing approved size ratio:** `Engulfing Candle Size >= 2 × Previous Candle Size` (standard) / `>= 3 ×` (strong), Total Range basis. `BOOK-EXPLICIT` ("Bullish Engulfing Size Condition: Bullish Engulfing Candle Size ≥ 2 × Previous Candle Size... A pattern becomes stronger when: Bullish Engulfing Candle Size ≥ 3 × Previous Candle Size"), formalized via `AUTHOR-PREVIOUSLY-APPROVED` Candle Measurement Standard V1 and Small Candle Standard V1 (`knowledge/MEASUREMENT_STANDARDS.md` Section 7: "Two separate conditions required: (1) body engulfment... (2) Total Range Size Ratio per the classification table. Both must hold; neither substitutes for the other").
5. **Whether body engulfment, total-range engulfment, or both are required:** **body engulfment is baseline-mandatory**; **total-range (wick) engulfment is strength-tier-only, not required for baseline validity.** `BOOK-EXPLICIT` ("Its body should cover or engulf the body of the previous smaller candle. A stronger pattern may also engulf the entire range of the previous candle, including its upper and lower wicks").
6. **Whether wick engulfment matters:** yes, but only as an optional strength signal, never as a baseline validity requirement. `BOOK-EXPLICIT`.
7. **Required location in market movement:** within/in the middle of an existing price movement — explicitly **not** at the origin (the rule that distinguishes it from Order Block). `BOOK-EXPLICIT` ("a valid engulfing pattern should appear: In the middle of a price movement; Between two sections of an existing movement; or During the continuation or internal retracement of a directional move").
8. **Whether it is a signal, POI, or both:** both — a general price-action signal that becomes a POI (a zone worth tracking) only when it appears at a meaningful location. `BOOK-EXPLICIT` ("These candlestick patterns can become Points of Interest when they appear at the right location... a bullish engulfing candle that forms randomly in the middle of the chart may not be very important. But if that same bullish engulfing candle forms at a strong support level... it becomes more meaningful").
9. **Which candle or range forms the POI:** **not stated.** `NOT DEFINED`. The book gives no "Zone = ..." formula for Engulfing anywhere, in contrast to Order Block ("Zone = Smaller Candle Low to High") or Fair Value Gap ("Buy FVG Zone = First Candle High to Third Candle Low"). This absence was directly verified against the book's full Engulfing appendix ("ENGULFING PATTERN," "BEARISH ENGULFING PATTERN," "ENGULFING PATTERN STRENGTH CLASSIFICATION," "IMPORTANT DISTINCTION BETWEEN AN ENGULFING PATTERN AND AN ORDER BLOCK") — no zone-boundary sentence exists there. This is the material basis for **GROUP3-D1**.
10. **Expected direction:** Bullish Engulfing = Bullish; Bearish Engulfing = Bearish. `BOOK-EXPLICIT`.
11. **Pattern confirmation time (distinct from POI lifecycle availability time):** the engulfing (second) candle's own close is when direction, body-engulfment, and the 2x/3x size-ratio are all simultaneously evaluable, and the pattern itself is confirmed valid. `BOOK-EXPLICIT` (each individual condition is book-stated) combined with `AUTHOR-PREVIOUSLY-APPROVED` (the size-ratio math). This is **not** the same question as when the eventual POI zone becomes lifecycle-eligible for the Boundary Breach/Reclaim/Invalidation standard — that is a separate, `NOT DEFINED` question, addressed independently by **GROUP3-D2**, because it is not fixed automatically by pattern-confirmation time alone (see item 12).
12. **Whether POI lifecycle availability time follows automatically from the zone-source decision:** **no.** Even once GROUP3-D1 fixes which candle(s) form the zone, a genuinely separate judgment remains about *when* the resulting zone becomes eligible for lifecycle tracking. If the zone is based on the first (engulfed) candle, its boundary numbers are computable at candle 1's close — before the pattern itself is confirmed valid at candle 2's close — creating exactly the kind of backdating risk RECON-D1 (Order Block) was created to prevent; the safe choice (delay availability to candle 2's close) is not the only logically possible answer and must be decided, not assumed. If the zone is based on the engulfing candle or the combined range, availability plausibly coincides with candle 2's close, but this too is a choice, not a mechanical necessity. This is the material basis for **GROUP3-D2** being a genuinely independent decision from GROUP3-D1, not a trailing consequence of it.
13. **Whether it can become a bounded directional POI:** yes, in principle (direction is defined, and a two-candle price range exists), but **not yet** — neither the zone-boundary source (GROUP3-D1) nor the lifecycle-availability timing (GROUP3-D2) has been decided.

**No boundary source and no availability timing were selected by this audit,** consistent with the instruction not to choose one unless already explicit or author-approved — neither condition is met for either question.

## 10. Hammer and Shooting Star Findings

**Hammer / Shooting Star.**

1. **Candle direction requirements:** none — the book explicitly states pattern identity is not determined by candle body colour; direction is about the *reaction* (bullish for Hammer, bearish for Shooting Star). Close color instead determines *signal strength* (see item 4). `BOOK-EXPLICIT`.
2. **Wick-to-body requirements:** "long lower wick, small body" (Hammer) / "long upper wick, small body" (Shooting Star) — qualitative only, **no numeric ratio anywhere in the book.** `BOOK-EXPLICIT` (qualitative) / `NOT DEFINED` (numeric). This is the material basis for **GROUP3-D3**.
3. **Opposite-wick requirements:** not mentioned at all — the book never discusses an upper-wick constraint for Hammer or a lower-wick constraint for Shooting Star. `NOT DEFINED`. Folded into **GROUP3-D3**.
4. **Close-position requirements:** the candle's close color determines signal strength: a close in the reaction direction is a "stronger standalone" signal; a close against the reaction direction means "wait for a confirmation candle." `BOOK-EXPLICIT`. No numeric close-position ratio (unlike Pressure Wick's `Bullish/Bearish Close Position >= 0.60/0.70`) exists. `NOT DEFINED` (numeric). Folded into **GROUP3-D3**.
5. **Required preceding context:** "around a support zone" (Hammer) / "around a resistance zone" (Shooting Star) — qualitative only, no numeric proximity rule. `BOOK-EXPLICIT` (qualitative).
6. **Signal role and POI role:** both — described first as a rejection *signal*, and separately catalogued as one of the book's six price-action *POI* types. `BOOK-EXPLICIT`. Whether it is signal-only, bounded-POI, or both in this project's model is **not** settled by this book language alone — this is the material basis for **GROUP3-D4**.
7. **Exact POI zone source:** **not stated.** `NOT DEFINED`. No "Zone = ..." formula exists for Hammer or Shooting Star anywhere in the book. This is the material basis for **GROUP3-D5**, which applies only if GROUP3-D4 selects a bounded-POI outcome.
8. **Expected direction:** Hammer = Bullish; Shooting Star = Bearish. `BOOK-EXPLICIT`.
9. **Whether later confirmation is required:** only for the weaker (close-against-reaction) case — "wait for a confirmation candle" is stated explicitly for entry purposes, not for POI formation itself. `BOOK-EXPLICIT`. This is an entry-timing observation, not a lifecycle-availability rule, and this audit does not conflate the two (see Section 16).
10. **Pattern confirmation time vs. POI lifecycle availability time:** the candle's own close is when the qualitative shape (once GROUP3-D3 supplies a numeric threshold) and close-color signal strength are evaluable — `NOT DEFINED` today because GROUP3-D3 itself is unresolved. Even after GROUP3-D3 resolves the ratio, POI lifecycle availability remains a **separate, further** question — addressed by **GROUP3-D6**, conditional on GROUP3-D4 — because, exactly as with Engulfing (Section 9, item 12), a formation ratio being satisfied at a candle's close does not, by itself, mechanically settle whether the resulting zone (if any) is immediately lifecycle-eligible or must wait for something else (e.g., an explicit confirmation candle).
11. **Similarities and differences from Bullish/Bearish Pressure Wick:** both are long-wick, small-body rejection candles. The book itself classifies Pressure Wick as Volume-Based and Hammer/Shooting Star as Price-Action, and the two are documented as **structurally distinct, separately-defined POI types**, not the same pattern under two names — Pressure Wick has an author-approved numeric standard (Lower Wick Share >= 0.40, Body Efficiency >= 0.25, Lower Wick >= 2x Upper Wick, Bullish Close Position >= 0.60, etc.); Hammer/Shooting Star has none of these numeric thresholds. `BOOK-EXPLICIT` (separate classification) + `AUTHOR-PREVIOUSLY-APPROVED` (Pressure Wick Standard V1's own numeric definition, which is *not* extended to Hammer/Shooting Star: `knowledge/MEASUREMENT_STANDARDS.md`, "Scope: Applies only to Bullish Pressure Wick and Bearish Pressure Wick. Not automatically extended to Hammer, Shooting Star...").
12. **Whether both labels may coexist:** **yes — already resolved.** `AUTHOR-PREVIOUSLY-APPROVED`: `knowledge/MEASUREMENT_STANDARDS.md`, "Relationship with Hammer and Shooting Star" — *"One candle may independently qualify for both a Pressure Wick label and a Hammer/Shooting Star label — the system must preserve these labels separately and must never silently merge them into one POI type. The Hammer and Shooting Star rule files are **not** modified by this standard."* This is a settled, prior author decision. **No new author decision is required for this specific overlap question**, and none of GROUP3-D3 through GROUP3-D6 re-opens it.
13. **Whether overlap treatment requires author approval:** no — already approved (see item 12). This audit does not re-open it.
14. **Whether they create bounded directional POIs:** genuinely open — this is precisely **GROUP3-D4**, a gating decision with no A/B/C option recommended (a process/deferral recommendation is provided instead), because the book's own "around a support/resistance zone" phrasing supports both a standalone-zone reading and a confirmation-signal-only reading roughly equally.

**Per the task instruction, Hammer is not silently made identical to Bullish Pressure Wick, and Shooting Star is not silently made identical to Bearish Pressure Wick** — item 11 above documents the concrete numeric and classification differences that keep them distinct.

## 11. Morning Star and Evening Star Findings

**Morning Star / Evening Star.**

1. **Exact candle count:** 3. `BOOK-EXPLICIT`.
2. **Required first-candle direction:** Morning Star = strong bearish; Evening Star = strong bullish. `BOOK-EXPLICIT`.
3. **Middle-candle requirements:** "a small candle or a doji" — qualitative only. `BOOK-EXPLICIT` (qualitative) / `NOT DEFINED` (numeric). This is the material basis for **GROUP3-D7**.
4. **Whether the middle candle must be a Doji, a small candle, or either:** **either** — the book explicitly offers both as acceptable ("often a small candle or a doji," "usually a small candle or a doji") without distinguishing separate rules for the two cases. `BOOK-EXPLICIT`. Folded into **GROUP3-D7**.
5. **Final-candle direction and size:** Morning Star candle 3 = strong bullish; Evening Star candle 3 = strong bearish; ideally >= 2-3x the middle candle's Total Range. `BOOK-EXPLICIT` ("this last candle should be at least two to three times bigger than the middle doji candle"), formalized via `AUTHOR-PREVIOUSLY-APPROVED` Candle Measurement Standard V1 (Size Ratio math), though no dedicated Standard/Strong named-tier split exists the way Order Block/Engulfing/Base have (only the bare "2 to 3 times" range is given).
6. **Required relationship between the first and final candles:** **not stated.** `NOT DEFINED`. The book never requires the third candle to close beyond the first candle's open/close/high/low, or any other cross-candle relationship — only that the third candle be strong relative to the *middle* candle.
7. **Whether Forex gaps are mandatory:** **no — not mentioned at all.** `BOOK-EXPLICIT absence` (a full-text search of the book for "gap up," "gap down," "price gap," and "opening gap" returned zero matches). Classical Western candlestick theory sometimes requires a gap between candles for Morning/Evening Star; this book does not state or imply any such requirement, consistent with continuous Forex/CFD trading having minimal or no gaps on most instruments and timeframes in this project's scope. **This finding is preserved unchanged by this correction — no mandatory Forex gap rule was found or invented.**
8. **Signal role and POI role:** both — described as a reversal signal ("The Morning Star is often considered a buy signal") and explicitly as containing its own POI (see item 9). `BOOK-EXPLICIT`.
9. **Whether the middle Doji or small candle forms the POI:** **yes — explicitly stated.** `BOOK-EXPLICIT`: *"The doji area can also serve as a Point of Interest, because price may later revisit that zone before continuing upward"* (Morning Star); *"The doji area can also become a Point of Interest"* (Evening Star). This is the single most book-explicit boundary-source fact among all 6 audited POIs — unlike Engulfing or Hammer/Shooting Star, the book directly names which candle is the POI.
10. **Whether the whole middle-candle range, body, wick, or full pattern forms the POI:** **not stated as an exact formula.** `BOOK-IMPLIED` only — "the doji area" is never defined as "High to Low," "Open to Close," or any other precise boundary. This audit does **not** assume the doji is the POI without support (it *is* book-supported, per item 9) and does **not** invent the missing exact formula. This is the material basis for **GROUP3-D8**.
11. **Expected direction:** Morning Star = Bullish; Evening Star = Bearish. `BOOK-EXPLICIT`.
12. **Pattern confirmation time (distinct from POI lifecycle availability time):** the third candle's close, when the >= 2-3x ratio against the middle candle can be evaluated. `BOOK-EXPLICIT` (the ratio check itself).
13. **Whether POI lifecycle availability time follows automatically from pattern confirmation time:** **not settled — a genuinely independent question.** `ENGINEERING-PROVISIONAL` only. The book explicitly ties the doji area's significance to the third candle's strength ("When this happens on a higher timeframe, the doji area can become a powerful Point of Interest"), which implies the POI's *significance* is only clear after candle 3, but this audit does not treat that as an already-decided lifecycle-availability rule. This is the material basis for **GROUP3-D9**, kept independent of both the formation threshold (GROUP3-D7) and the boundary formula (GROUP3-D8) — exactly because this project's own prior experience (the FVG RECON-D5 correction, and this document's own prior Engulfing/Hammer misclassification) demonstrated that "the geometry/confirmation implies a timing" is not, by itself, a sufficient substitute for an explicit, separately-recorded author decision.
14. **Whether the pattern creates a bounded directional POI:** yes, in principle and with stronger book support than Engulfing or Hammer/Shooting Star (the book names the POI-forming candle directly), but the doji/small-candle threshold (GROUP3-D7), the exact zone formula (GROUP3-D8), and lifecycle availability timing (GROUP3-D9) all still require independent, explicit author confirmation.

**This audit does not assume the Doji is the POI merely by inference — it is supported by direct book language quoted in item 9 above**, which is a materially stronger evidentiary basis than exists for either Engulfing or Hammer/Shooting Star. That stronger boundary-role evidence does not, however, extend to the availability-timing question, which remains equally open regardless of how well-supported the boundary role is.

## 12. Signal-Versus-POI Findings

All 6 POIs share the same book-explicit dual role: each is introduced as a **candlestick signal** (a pattern that shows a possible change of control between buyers and sellers) that becomes a **Point of Interest** — a zone worth tracking — only when it appears at a meaningful market location. `BOOK-EXPLICIT` for all 6: *"These candlestick patterns can become Points of Interest when they appear at the right location... The candle itself is not enough. The location of the candle is what gives it power."*

This project's existing pattern of separating **formation validity** from **lifecycle validity** (already established for the 12 propagated bounded POIs) applies with extra force here: for these 6 POIs, an additional prior question exists that the 12 propagated POIs did not need to answer — whether the pattern should be modeled as a bounded zone at all, versus a signal that strengthens an *existing* nearby POI (Support, Resistance, Order Block, etc.) without forming its own zone. This is most acute for Hammer/Shooting Star (**GROUP3-D4**) and is explicitly preserved as an open, gating question, not resolved by this audit.

**Correction note:** the original version of this audit additionally under-separated *pattern confirmation time* from *POI lifecycle availability time* for Engulfing and Morning/Evening Star, treating the latter as though it followed automatically once the former (or the zone source) was known. This correction keeps the two explicitly distinct for every POI (see Sections 9–11, and the 9-decision structure in Section 18).

## 13. Boundary Findings

| POI | Boundary source stated? | Exact formula stated? |
|---|---|---|
| Bullish/Bearish Engulfing | No | No |
| Hammer/Shooting Star | No | No |
| Morning/Evening Star | Yes (the doji/middle candle) | No |

No POI among the 6 has a complete, formula-level boundary definition. Per the task instruction, **no boundary source was selected for any of the 6** unless already explicit or author-approved — none meets that bar.

## 14. Direction Findings

All 6 POIs have an explicit, unambiguous expected direction (`BOOK-EXPLICIT` in every case): Bullish Engulfing (Bullish), Bearish Engulfing (Bearish), Hammer (Bullish), Shooting Star (Bearish), Morning Star (Bullish), Evening Star (Bearish). Direction is **not** a blocking gap for any of the 6.

## 15. Formation-Rule Gaps

| POI | Formation rule complete? | Missing numeric threshold |
|---|---|---|
| Bullish/Bearish Engulfing | Yes | None — fully defined via book + Candle Measurement Standard V1 / Small Candle Standard V1 |
| Hammer/Shooting Star | No | Wick:body ratio (long lower/upper wick vs. small body) — `GROUP3-D3` |
| Morning/Evening Star | Partial | Doji/small-candle body-size threshold for candle 2 — `GROUP3-D7` |

Only Hammer/Shooting Star and Morning/Evening Star have an open formation-rule gap; Engulfing's formation rule is complete and requires no decision. **Engulfing's remaining gaps (GROUP3-D1, GROUP3-D2) are both boundary/timing gaps, not formation-rule gaps** — this distinction is why Engulfing is `E` (multiple *non-formation* categories) rather than `D`.

## 16. Confirmation and Availability Gaps

No POI among the 6 has an explicit, book-stated, or author-approved non-repainting availability statement (the kind of explicit section already present for Pressure Wick, Buy-to-Sell/Sell-to-Buy Candle, Support, and Resistance). **Pattern confirmation time and POI lifecycle availability time are two distinct questions for every one of the 6 POIs**, and this audit resolves neither by inference:

| POI | Pattern confirmation time | POI lifecycle availability time |
|---|---|---|
| Bullish/Bearish Engulfing | `BOOK-EXPLICIT`/`AUTHOR-PREVIOUSLY-APPROVED` — engulfing candle's own close | `NOT DEFINED` — `GROUP3-D2` |
| Hammer/Shooting Star | `NOT DEFINED` until `GROUP3-D3` supplies a ratio | `NOT DEFINED` — `GROUP3-D6`, conditional on `GROUP3-D4` |
| Morning/Evening Star | `BOOK-EXPLICIT` — third candle's close | `NOT DEFINED` — `GROUP3-D9` |

For Engulfing and Morning/Evening Star, a plausible availability point can be inferred from existing confirmation language (the pattern's own final candle's close); for Hammer/Shooting Star, availability can only be inferred by analogy to Pressure Wick, and only if the pattern is even approved as bounded. In every case this audit records the inference as `ENGINEERING-PROVISIONAL`, not as a settled fact, and routes it into its own independent GROUP3-D decision rather than assuming it follows automatically from the boundary or formation decision.

**Entry-confirmation is not conflated with lifecycle-availability anywhere in this audit.** Hammer/Shooting Star's book-stated "wait for a confirmation candle" (for a close-against-reaction candle) is an entry-timing observation, not a POI-lifecycle-availability rule — this distinction is preserved explicitly in Section 10, item 9.

## 17. Pattern-Overlap Findings

| Overlap | Status | Provenance |
|---|---|---|
| Engulfing vs. Order Block | Already resolved — distinguished by location (within a move vs. origin of a move) | `BOOK-EXPLICIT` |
| Hammer vs. Bullish Pressure Wick | Already resolved — both labels preserved, never merged | `AUTHOR-PREVIOUSLY-APPROVED` (`knowledge/MEASUREMENT_STANDARDS.md`, "Relationship with Hammer and Shooting Star") |
| Shooting Star vs. Bearish Pressure Wick | Already resolved — same as above, mirrored | `AUTHOR-PREVIOUSLY-APPROVED` |
| Hammer/Shooting Star vs. Support/Resistance | **Open** — both are described as occurring "around" a support/resistance zone; unclear whether Hammer/Shooting Star should be its own bounded POI or a confirmation signal for an existing Support/Resistance zone | `CURRENT-FILE-ONLY` observation, elevated into **GROUP3-D4** |
| Morning/Evening Star vs. Base Rally/Drop | **Open, low-priority** — a doji zone could visually coincide with a Base if candles cluster similarly (already noted in `morning_star.md`'s own "Overlap with other POIs" field) | `CURRENT-FILE-ONLY`, not addressed by the book |
| Engulfing vs. Buy-to-Sell/Sell-to-Buy Candle | **Open, low-priority** — the book does not address this comparison at all; not elevated to a formal decision by this audit | `NOT DEFINED` |
| Any of the 6 vs. any other candlestick pattern | No further overlap identified in the book or existing files | — |

**No precedence rule was created for any overlap.** For each open overlap, the corresponding recommendation is only whether later author approval is required to preserve both labels, select a primary label, use one as supporting evidence, or apply another treatment — never a selection made by this audit.

- **Hammer/Shooting Star vs. Support/Resistance:** author approval required to decide preserve-both / select-primary / supporting-evidence-only / other. Folded into **GROUP3-D4** (the POI-role/bounded-status gating decision).
- **Morning/Evening Star vs. Base Rally/Drop:** author approval would be required only if a concrete conflicting instance is later found; no decision is forced by this audit.
- **Engulfing vs. Buy-to-Sell/Sell-to-Buy Candle:** recorded for awareness only; not blocking.

## 18. Exact Author Decisions Required (Part 8 format)

**Nine decision records identified: seven unconditional and two conditional.** Unconditional: GROUP3-D1, GROUP3-D2, GROUP3-D3, GROUP3-D4, GROUP3-D7, GROUP3-D8, GROUP3-D9. Conditional (on GROUP3-D4 approving a bounded outcome): GROUP3-D5, GROUP3-D6. Each record addresses exactly one material decision category.

### GROUP3-D1 — Engulfing POI Zone Source

**Affected POIs:** Bullish Engulfing Candle, Bearish Engulfing Candle

**Decision category:** ZONE BOUNDARY

**Source evidence:** the book gives no "Zone = ..." formula for Engulfing anywhere in its full validation appendix (`BOOK-EXPLICIT absence`, verified against the complete "ENGULFING PATTERN" / "BEARISH ENGULFING PATTERN" text). The book does give an explicit two-candle structure (small preceding candle, larger engulfing candle) and an explicit distinction from Order Block by location.

**Current ambiguity:** which candle or range forms the Engulfing POI, and its exact Zone Top / Zone Bottom.

**Option A:** Zone = the first (small, engulfed) candle's full range (High to Low), mirroring Order Block's convention.

**Option B:** Zone = the engulfing (second, larger) candle's full range.

**Option C, only when genuinely necessary:** Zone = the complete two-candle range (lowest low to highest high of both candles), or another author-defined source.

**Effect of each option:** Option A mirrors Order Block's boundary precedent most closely. Option B treats the candle that actually demonstrates displacement/momentum as the meaningful zone, consistent with Buy-to-Sell/Sell-to-Buy Candle's precedent. Option C is a materially larger, more inclusive zone not suggested by any existing POI's convention in this project.

**Engineering recommendation:** Option B.

**Reason:** matches the precedent already used for Buy-to-Sell/Sell-to-Buy Candle (a single meaningful candle's own range as the zone).

**Rules that remain unchanged:** the two-candle formation rule, the 2x/3x size-ratio requirement, body-engulfment-as-baseline, wick-engulfment-as-strength-only, and the location rule distinguishing Engulfing from Order Block.

**Risk of choosing incorrectly:** choosing Option A without also resolving GROUP3-D2 with an explicit non-backdating safeguard could let lifecycle events be evaluated against a zone before the pattern is confirmed valid.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

**Does not include lifecycle availability timing** — see GROUP3-D2.

---

### GROUP3-D2 — Engulfing Lifecycle Availability Timing

**Affected POIs:** Bullish Engulfing Candle, Bearish Engulfing Candle

**Decision category:** CONFIRMATION / AVAILABILITY TIMING

**Source evidence:** pattern confirmation time is `BOOK-EXPLICIT`/`AUTHOR-PREVIOUSLY-APPROVED` — the engulfing (second) candle's own close is when direction, body-engulfment, and the 2x/3x size ratio are all evaluable. **POI lifecycle availability time is a separate question and is `NOT DEFINED`** — the book never states when the (still zone-source-dependent) POI becomes eligible for the Boundary Breach/Reclaim/Invalidation lifecycle.

**Current ambiguity:** whether lifecycle eligibility begins at the confirmed engulfing-candle close, waits for another confirmation event, or depends on which boundary GROUP3-D1 selects.

**Option A:** Lifecycle availability = the engulfing (second) candle's close, in every case — the same moment the pattern itself is confirmed, regardless of which candle GROUP3-D1 selects as the zone.

**Option B:** Lifecycle availability depends on the GROUP3-D1 outcome: if the zone is the first (engulfed) candle's range, availability is deliberately delayed to the engulfing candle's close (a non-backdating safeguard, directly analogous to RECON-D1 for Order Block); if the zone is the engulfing candle's own range or the combined range, availability coincides with that same close.

**Option C, only when genuinely necessary:** require an additional confirmation candle beyond the engulfing candle itself before lifecycle tracking begins.

**Effect of each option:** Option A is simplest and needs no cross-reference to GROUP3-D1's outcome, but could backdate lifecycle tracking to before the zone's own boundary is confirmable if GROUP3-D1 selects Option A (first-candle zone). Option B is the most consistent with this project's RECON-D1 precedent but requires the availability rule to branch on the GROUP3-D1 outcome. Option C adds a delay not suggested by any book language or existing project precedent for a two-candle pattern.

**Engineering recommendation:** Option B.

**Reason:** avoids the backdating risk regardless of which GROUP3-D1 option is eventually approved, and mirrors this project's own established RECON-D1/RECON-D2 pattern of tying availability to the candle that actually confirms the pattern's validity.

**Rules that remain unchanged:** the two-candle formation rule, the 2x/3x size-ratio requirement, and whatever boundary GROUP3-D1 ultimately selects (this decision does not redefine Engulfing formation or boundaries).

**Risk of choosing incorrectly:** choosing Option A without regard to the GROUP3-D1 outcome risks silently reintroducing a backdating pathway if GROUP3-D1 selects a first-candle-based zone.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

---

### GROUP3-D3 — Hammer and Shooting Star Quantitative Formation Thresholds

**Affected POIs:** Hammer, Shooting Star

**Decision category:** FORMATION RULES

**Source evidence:** the book states only "long lower wick, small body" (Hammer) / "long upper wick, small body" (Shooting Star) — `BOOK-EXPLICIT` qualitative language, `NOT DEFINED` numerically. No wick:body ratio, no opposite-wick limit, no body-efficiency requirement, and no close-position requirement is given anywhere in the book for these two POIs.

**Current ambiguity:** what numeric threshold(s) distinguish a valid Hammer/Shooting Star from an ordinary candle with a moderately long wick, sufficient to convert the qualitative shape into a machine-testable rule (rejection-wick-to-body ratio; opposite-wick limit; body-efficiency requirement; close-position requirement; or another numeric condition).

**Option A:** Reuse the already-approved Pressure Wick Standard V1 thresholds (Lower/Upper Wick Share >= 0.40, Body Efficiency >= 0.25, opposite-wick ratio >= 2x) as a starting point, tracked under a distinct Hammer/Shooting-Star-specific field name.

**Option B:** Define an independent, Hammer/Shooting-Star-specific set of thresholds, calibrated separately from Pressure Wick.

**Option C, only when genuinely necessary:** leave the ratio deliberately loose/qualitative and rely entirely on downstream reaction/context evidence rather than a fixed geometric threshold.

**Effect of each option:** Option A reuses proven machinery but requires care not to quietly collapse Hammer/Shooting Star into Pressure Wick in all but name — the already-approved overlap rule (Section 10, item 12) prohibits doing so *silently*; an explicit decision to reuse the numbers while keeping the POI types and their evidence trails independently tracked would not violate that rule. Option B preserves maximal independence but requires new calibration work with no book anchor. Option C avoids inventing an unsupported number but leaves the POI permanently non-machine-testable for its core formation rule.

**Engineering recommendation:** Option A, applied as a reused numeric threshold under a distinct field name (not a merge of the two POI types).

**Reason:** avoids inventing an arbitrary uncalibrated number from nothing, and reuses a threshold this project already trusts for a structurally similar wick/body concept.

**Rules that remain unchanged:** Pressure Wick's own thresholds and formulas (untouched, not redefined); Hammer/Shooting Star's book-explicit shape description and close-color signal rule.

**Risk of choosing incorrectly:** choosing B without calibration evidence risks an arbitrary, uncalibrated number; choosing C leaves the POI permanently untestable for its own formation rule.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

**Does not define POI boundaries or lifecycle timing** — see GROUP3-D4, GROUP3-D5, GROUP3-D6.

---

### GROUP3-D4 — Hammer and Shooting Star POI Role / Bounded Status

**Affected POIs:** Hammer, Shooting Star

**Decision category:** POI ROLE (gating decision)

**Source evidence:** no "Zone = ..." formula exists anywhere in the book for these two POIs. Both are described as appearing "around" a support/resistance zone, which supports reading them either as their own zone or as a confirmation signal for an existing nearby zone. `BOOK-EXPLICIT absence` for a formula; `BOOK-EXPLICIT` for the qualitative "around a zone" language; `BOOK-EXPLICIT` for their separate listing as one of the book's six price-action POI types.

**Current ambiguity:** whether each pattern is a signal only, a bounded directional POI, or both.

**Option A:** Bounded directional POI — proceed to GROUP3-D5 (zone source) and GROUP3-D6 (availability timing).

**Option B:** Signal only (`NOT_A_BOUNDED_POI`) — the pattern adds evidence to an *existing* Support/Resistance (or other) POI's reaction strength; GROUP3-D5 and GROUP3-D6 become `NOT APPLICABLE`.

**Option C, only when genuinely necessary:** both — track as a bounded POI only when it does not already coincide with an existing Support/Resistance/Order Block zone, and as supporting evidence only when it does; GROUP3-D5/GROUP3-D6 would then apply conditionally per-instance rather than per-POI-type.

**Effect of each option:** Option A gives Hammer/Shooting Star full parity with Pressure Wick as an independently trackable POI. Option B avoids ever needing a Hammer/Shooting-Star-specific boundary formula or lifecycle inheritance, but discards the book's own listing of Hammer/Shooting Star as one of six price-action *POI* types. Option C is the most book-faithful to the "location gives it power" framing but requires a new conditional-tracking rule not used elsewhere in this project.

**Engineering recommendation:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`. This is a **process recommendation only** — it does not select Option A, B, or C, and it is explicitly **not an approval of Option B (signal-only)** as the final architectural answer. Pending an explicit author decision on POI role, Hammer and Shooting Star should continue to be treated exactly as they are treated today: usable as signals under their existing qualitative, book-supported evidence (long wick, small body, close-color strength), while **not** classified as a bounded directional POI and **not** submitted for lifecycle inheritance. This is not a new restriction — it is the same default that already necessarily holds today, since no zone-boundary formula exists for either POI regardless of which option is eventually chosen. Current blocked status is unchanged by this recommendation; no option is selected; GROUP3-D5 and GROUP3-D6 remain conditional and `NOT APPLICABLE` until this decision is made; no lifecycle propagation occurs as a result of this recommendation.

**Rules that remain unchanged:** Hammer/Shooting Star's shape description, close-color signal rule, and the already-approved Pressure Wick label-preservation rule (Section 10, item 12).

**Risk of choosing incorrectly:** choosing A without first resolving GROUP3-D3 would leave a "bounded" POI with no formation threshold; choosing B without amending the POI catalog's own "six price-action POI types" framing could understate what the book itself claims about these patterns.

**Reason:** the book's own "signal becomes a POI at the right location" framing (Section 12) supports both a standalone-zone reading and a confirmation-signal reading of Hammer/Shooting Star roughly equally, and this document's own correction history (Section 1) demonstrates the risk of presenting an unstated inference as though self-evidently correct in either direction; recommending the deferral itself, rather than guessing, keeps GROUP3-D5/GROUP3-D6 from being attempted prematurely and keeps lifecycle inheritance from being propagated before the author decides.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED` (process/deferral recommendation only; no option among A, B, or C is selected or approved).

**This is a gating decision** — GROUP3-D5 and GROUP3-D6 apply only if this decision selects a bounded outcome (Option A or, per-instance, Option C).

---

### GROUP3-D5 — Hammer and Shooting Star Zone Source

**Affected POIs:** Hammer, Shooting Star

**Decision category:** ZONE BOUNDARY

**Status:** CONDITIONAL ON GROUP3-D4 — required only if GROUP3-D4 approves Hammer and/or Shooting Star as bounded POIs. **If GROUP3-D4 selects signal-only, this decision is recorded as `NOT APPLICABLE` for the affected POI.**

**Source evidence:** no "Zone = ..." formula exists anywhere in the book for Hammer or Shooting Star.

**Current ambiguity (if applicable):** the exact Zone Top / Zone Bottom source.

**Option A:** Entire candle range (High to Low), mirroring Pressure Wick's single-candle convention.

**Option B:** The rejection wick only (excluding the body).

**Option C, only when genuinely necessary:** wick plus body, body only, or another author-defined zone.

**Effect of each option:** Option A is most consistent with the wick-inclusive convention already used by every other POI in this project. Option B isolates the specific rejection element the book emphasizes ("the long wick shows rejection") but would be a narrower reading than any other POI's zone in this project. Option C's sub-variants each depart further from the established convention without direct book support.

**Engineering recommendation:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`. No zone-boundary source is recommended before GROUP3-D4 is resolved — selecting a formula now would risk defining boundaries for a POI type the author may ultimately treat as signal-only. If and when GROUP3-D4 approves a bounded outcome for Hammer and/or Shooting Star, the author's intended zone should be evaluated at that time among the options above (the entire candle range, the rejection wick only, wick plus body, body only, or another author-defined area) — this recommendation does not pre-select or favor any of them. Until GROUP3-D4 is resolved, this decision remains deferred and `NOT APPLICABLE` to any lifecycle propagation.

**Rules that remain unchanged:** Hammer/Shooting Star's shape description and (once resolved) GROUP3-D3's formation threshold.

**Risk of choosing incorrectly:** defining a boundary before GROUP3-D4 is resolved could produce a formula for a POI type the author ultimately treats as signal-only.

**Reason:** the appropriate zone source may itself depend on which POI-role outcome GROUP3-D4 selects (a "signal-only" outcome would make any boundary formula moot), and no boundary formula exists in the book for either candidate reading, so deferring the boundary choice avoids defining a formula for a POI type the author may ultimately treat as signal-only.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED` (conditional deferral recommendation only; no boundary option among A, B, or C is selected or approved); **status CONDITIONAL ON GROUP3-D4**.

**Defines no timing rule** — see GROUP3-D6.

---

### GROUP3-D6 — Hammer and Shooting Star Confirmation and Lifecycle Availability Timing

**Affected POIs:** Hammer, Shooting Star

**Decision category:** CONFIRMATION / AVAILABILITY TIMING

**Status:** CONDITIONAL ON GROUP3-D4 — required only if the pattern is approved as a bounded POI. **If GROUP3-D4 selects signal-only, this decision is recorded as `NOT APPLICABLE` for the affected POI.**

**Source evidence:** `NOT DEFINED`. The book's "wait for a confirmation candle" language (for a close-against-reaction candle) is an entry-timing observation, not a lifecycle-availability rule (Section 10, item 9).

**Current ambiguity (if applicable):** whether the pattern is confirmed at its own candle close, whether a later confirmation candle is mandatory for lifecycle purposes (not just entry purposes), when the bounded POI becomes available to downstream lifecycle logic, and whether any lifecycle event may be backdated.

**Option A:** Availability = the Hammer/Shooting Star candle's own close (CANDIDATE before close, CONFIRMED after), mirroring Pressure Wick's CANDIDATE/CONFIRMED pattern. No lifecycle event is ever backdated to before this close.

**Option B:** Availability = the close of the book-mentioned "confirmation candle" (required only for the weaker, close-against-reaction case) — extending an entry-timing concept into a lifecycle-availability rule.

**Option C, only when genuinely necessary:** a two-tier model — CANDIDATE at the pattern candle's own close, but CONFIRMED (lifecycle-eligible) only after the strength condition (close-color) is evaluated, with a further delay for the weaker case.

**Effect of each option:** Option A mirrors Pressure Wick's precedent exactly and requires no new state model. Option B imports an entry-timing concept into lifecycle availability, which this audit does not do without an explicit decision, since the book itself frames the confirmation candle as being about trade entry, not POI existence. Option C is the most conservative but introduces a new two-tier structure specific to this POI family.

**Engineering recommendation:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`. No lifecycle-availability timing is recommended before **both** GROUP3-D4 establishes bounded-POI status **and** GROUP3-D5 establishes the approved zone source — this decision's correct answer depends on both, since "when the POI becomes available" cannot be fixed until it is known whether a POI exists at all and, if so, what its approved boundaries are. Once both are resolved, the applicable *principle* (consistent with the precedent already established by GROUP3-D1/GROUP3-D2 for Engulfing and GROUP3-D9 for Morning/Evening Star) is to choose the earliest confirmed, non-repainting time at which both the pattern and its author-approved boundaries are fully known, with no lifecycle event ever backdated to an earlier candle. This recommendation does **not** select the candle's own close, a later confirmation candle, or any other specific timing option — that choice is deferred entirely to the author, and can only be meaningfully exercised after GROUP3-D4 and GROUP3-D5 are both resolved.

**Rules that remain unchanged:** the entry-timing "wait for a confirmation candle" rule itself (untouched, not redefined as a lifecycle rule without explicit approval).

**Risk of choosing incorrectly:** choosing B without an explicit decision to convert an entry-timing concept into a lifecycle-availability rule risks conflating two concepts this audit has deliberately kept separate (Section 16).

**Reason:** lifecycle-availability timing cannot be meaningfully fixed until both whether a POI exists at all (GROUP3-D4) and what its approved boundaries are (GROUP3-D5) are known; deferring the exact timing value avoids conflating the book's entry-timing "confirmation candle" concept with a lifecycle-availability rule before either prerequisite decision is made.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED` (dependency-order recommendation only; no timing option among A, B, or C is selected or approved); **status CONDITIONAL ON GROUP3-D4 AND, for the exact timing value, on GROUP3-D5**.

**Defines no zone source** — see GROUP3-D5.

---

### GROUP3-D7 — Morning Star and Evening Star Middle-Candle Threshold

**Affected POIs:** Morning Star, Evening Star

**Decision category:** FORMATION RULES

**Source evidence:** the book states the middle candle must be "a small candle or a doji" — `BOOK-EXPLICIT` qualitative, `NOT DEFINED` numerically. No maximum body-to-range ratio, and no distinction between "small candle" and "doji" thresholds, is given. No required relationship between the middle candle and the first or third candle beyond relative size is stated. **No mandatory Forex gap rule was found** (Section 11, item 7) — this finding is preserved, not re-opened, by this decision.

**Current ambiguity:** whether the middle candle must be a strict Doji, whether a small-bodied candle also qualifies, the exact measurable threshold for either case, and whether any required relationship exists between the middle candle and the first/third candles beyond relative size.

**Option A:** Reuse the already-approved Small Candle Standard V1 definition (Total Range <= 0.50x the adjacent key candle's Total Range, standard / <= 0.3333x, strong) for candle 2 relative to candle 3 (or candle 1).

**Option B:** Define a distinct Doji-specific Body Efficiency threshold (Body / Total Range below some maximum) — a materially different concept from "small candle."

**Option C, only when genuinely necessary:** treat "small candle" and "doji" as two independently qualifying sub-conditions with two separate thresholds, since the book itself offers them as two alternative descriptions ("a small candle **or** a doji").

**Effect of each option:** Option A reuses existing, already-approved machinery with no new invented number, but does not capture the classical "doji" concept (near-equal open/close regardless of Total Range relative to neighbors). Option B captures the doji-specific meaning precisely but introduces a wholly new, uncalibrated numeric field. Option C is the most book-faithful (preserves the book's own "either/or" framing) but is the most complex, requiring two new thresholds instead of one.

**Engineering recommendation:** Option C.

**Reason:** the book's own wording ("small candle or a doji") is explicitly disjunctive, and collapsing it into a single Option A or Option B definition would silently narrow what the book allows to qualify as candle 2.

**Rules that remain unchanged:** the 3-candle structure, first/third candle direction, and the >= 2-3x final-candle ratio.

**Risk of choosing incorrectly:** choosing Option A alone could reject a genuine near-equal-open-close doji that happens to have a larger Total Range than 0.50x its neighbor; choosing Option B alone could reject a genuine small (but not perfectly doji-shaped) candle the book would still accept.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

**Does not define boundaries or timing** — see GROUP3-D8, GROUP3-D9.

---

### GROUP3-D8 — Morning Star and Evening Star POI Zone Source

**Affected POIs:** Morning Star, Evening Star

**Decision category:** ZONE BOUNDARY

**Source evidence:** the book explicitly names the middle (doji) candle's area as the POI (`BOOK-EXPLICIT`, quoted in Section 11, item 9) but never states the exact boundary formula (`BOOK-IMPLIED` only for the exact High/Low mapping).

**Current ambiguity:** the exact meaning of the book-supported statement that the doji/middle-candle area "may serve as the POI" — whether the POI is the entire middle-candle range, the middle-candle body, one or both wicks, a bounded area derived from the middle candle by another rule, or the complete three-candle structure.

**Option A:** Zone Top = doji candle High, Zone Bottom = doji candle Low (full wick-inclusive range), matching the wick-inclusive convention already used by every other POI in this project (Measurement Standard V1 SS5).

**Option B:** Zone = the doji candle's body only (Open to Close), excluding wicks.

**Option C, only when genuinely necessary:** Zone = the full three-candle range (lowest low to highest high across all three candles), or another author-defined zone.

**Effect of each option:** Option A is the most consistent with every other POI's wick-inclusive convention in this project and the most literal reading of "the doji area" as the doji candle itself. Option B would be a genuine departure from this project's established wick-inclusive convention, requiring explicit justification. Option C significantly expands what "the doji area" means beyond the book's own wording, which specifically calls out the doji/middle candle, not the whole three-candle pattern.

**Engineering recommendation:** Option A.

**Reason:** matches the "doji area" language most literally, and is consistent with the wick-inclusive boundary convention already used by all 12 propagated POIs.

**Rules that remain unchanged:** the 3-candle structure, first/third candle direction, the >= 2-3x final-candle ratio, and the higher-timeframe (2H/3H/4H+) recommendation. Exact Zone Top and Zone Bottom values are only fixed after author approval of this decision.

**Risk of choosing incorrectly:** choosing B or C without book support risks defining a POI boundary the book does not actually describe.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

**Does not include confirmation or availability timing** — see GROUP3-D9.

---

### GROUP3-D9 — Morning Star and Evening Star Confirmation and Lifecycle Availability Timing

**Affected POIs:** Morning Star, Evening Star

**Decision category:** CONFIRMATION / AVAILABILITY TIMING

**Source evidence:** pattern confirmation is `BOOK-EXPLICIT` at the third candle's close (when the >= 2-3x ratio is evaluable). POI lifecycle availability is a separate, `NOT DEFINED` question.

**Current ambiguity:** whether pattern confirmation requiring the third candle to close also fixes POI lifecycle availability at that same moment, whether any later confirmation candle is additionally required, whether the middle-candle zone (once GROUP3-D8 defines it) may be recorded before the full pattern confirms, and whether any lifecycle event may be backdated.

**Option A:** Lifecycle availability = the third candle's close, coinciding exactly with pattern confirmation — the doji zone (per GROUP3-D8) is recorded but not lifecycle-eligible until this point, and no lifecycle event is backdated to the doji candle's own (earlier) close.

**Option B:** Lifecycle availability = the doji candle's own close — the zone becomes eligible as soon as its own boundary is known, before the third candle confirms the pattern's overall strength.

**Option C, only when genuinely necessary:** a two-tier model — the zone is recorded as a candidate at the doji candle's close but only becomes lifecycle-CONFIRMED at the third candle's close, tracking both timestamps explicitly.

**Effect of each option:** Option A prevents evaluating breach/reclaim/invalidation against a zone before the 3-candle pattern is confirmed valid, consistent with this project's RECON-D1/RECON-D2/GROUP3-D2 precedent of not backdating lifecycle tracking to before pattern confirmation. Option B starts tracking earlier but risks recording lifecycle events against a zone that later turns out not to be part of a valid Morning/Evening Star at all (e.g., if the third candle fails the size-ratio requirement). Option C preserves both perspectives but introduces a second timestamp/state not present in the approved shared standard or any other propagated POI file.

**Engineering recommendation:** Option A.

**Reason:** matches the precedent already established for RECON-D1 (Order Block), RECON-D2 (Base), and this document's own GROUP3-D2 (Engulfing) — the lifecycle clock starts only once the full pattern is confirmed valid, never at an earlier candle's close.

**Rules that remain unchanged:** the 3-candle structure, first/third candle direction, the >= 2-3x final-candle ratio, the higher-timeframe recommendation, and whatever boundary GROUP3-D8 ultimately selects.

**Risk of choosing incorrectly:** choosing Option B risks recording lifecycle events against a doji zone that is later found not to belong to a valid Morning/Evening Star pattern at all.

**Provenance status:** `ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED`.

**Does not define the zone source** — see GROUP3-D8.

---

**Nine decision records identified: seven unconditional (GROUP3-D1, GROUP3-D2, GROUP3-D3, GROUP3-D4, GROUP3-D7, GROUP3-D8, GROUP3-D9) and two conditional on GROUP3-D4 (GROUP3-D5, GROUP3-D6).** This structure was not forced to any predetermined number — it follows directly from strictly separating each independent material category (zone boundary; confirmation/availability timing; formation rule; POI role) per POI family, rather than bundling co-dependent categories into a single record. GROUP3-D5 and GROUP3-D6 do not count as required decisions for a given POI if GROUP3-D4 selects signal-only for that POI — they are recorded as `NOT APPLICABLE` in that case, not silently dropped or silently treated as still-required.

## 19. Unapproved Engineering Recommendations Summary

| Decision | Category | Recommended option | Status |
|---|---|---|---|
| GROUP3-D1 (Engulfing zone source) | ZONE BOUNDARY | Option B — zone = engulfing candle's own range | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D2 (Engulfing availability timing) | CONFIRMATION/TIMING | Option B — availability tied to the safe/non-backdating pairing for whichever GROUP3-D1 option is chosen | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D3 (Hammer/Shooting Star formation thresholds) | FORMATION RULES | Option A — reuse Pressure Wick thresholds under a distinct field name | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D4 (Hammer/Shooting Star POI role) | POI ROLE (gating) | No option (A/B/C) recommended. Process recommendation only: continue treating both patterns as signals under existing qualitative evidence; do not classify as bounded POIs; do not propagate lifecycle inheritance until the author decides. Not an approval of Option B. | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D5 (Hammer/Shooting Star zone source) | ZONE BOUNDARY | No boundary option recommended. Deferral recommendation only: evaluate the zone source only after GROUP3-D4 approves a bounded outcome. **Conditional on GROUP3-D4.** | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED; CONDITIONAL |
| GROUP3-D6 (Hammer/Shooting Star availability timing) | CONFIRMATION/TIMING | No timing option recommended. Dependency-order recommendation only: choose the earliest non-repainting time at which both pattern and approved boundaries are known, only after GROUP3-D4 and GROUP3-D5 are resolved. **Conditional on GROUP3-D4, and on GROUP3-D5 for the exact value.** | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED; CONDITIONAL |
| GROUP3-D7 (Morning/Evening Star middle-candle threshold) | FORMATION RULES | Option C — two separate sub-thresholds (small-candle + doji) | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D8 (Morning/Evening Star zone source) | ZONE BOUNDARY | Option A — doji candle's full wick-inclusive range | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |
| GROUP3-D9 (Morning/Evening Star availability timing) | CONFIRMATION/TIMING | Option A — availability at the third candle's close | ENGINEERING RECOMMENDATION — NOT YET AUTHOR-APPROVED |

**None of these nine recommendations is implemented, approved, or applied to any POI file by this audit.**

## 20. Safe Rules Requiring No Decision

- All 6 POIs' expected direction — fully defined, requires no decision.
- Bullish/Bearish Engulfing's entire formation rule (2-candle structure, body-engulfment baseline, wick-engulfment strength-only, 2x/3x size ratio, Standard/Strong/HTF/LTF classification, the Order-Block-distinguishing location rule, and pattern-confirmation time) — fully defined, requires no decision. (Zone source and lifecycle-availability timing remain open — GROUP3-D1, GROUP3-D2.)
- Hammer/Shooting Star's qualitative shape description (long wick, small body) and close-color signal-strength rule — fully defined qualitatively, requires no decision to remain valid as-is (only its *numeric threshold*, GROUP3-D3, is open).
- Hammer/Bullish Pressure Wick and Shooting Star/Bearish Pressure Wick label-preservation (never merge) — already author-approved, requires no new decision.
- Morning/Evening Star's 3-candle structure, first/third-candle direction, >= 2-3x final-candle ratio, higher-timeframe (2H/3H/4H+) recommendation, book-explicit "doji area is a POI" concept, and pattern-confirmation time — fully defined, requires no decision beyond the middle-candle threshold (GROUP3-D7), the exact boundary formula (GROUP3-D8), and lifecycle-availability timing (GROUP3-D9).
- The absence of a mandatory Forex gap rule for Morning/Evening Star — confirmed by full-text search, not a gap requiring a decision.
- The shared lifecycle standard's formulas, tolerances, event states, and transitions (`POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`) — untouched, apply unmodified once (and if) any of these 6 POIs is eventually approved for propagation.

## 21. Items Blocking Lifecycle Inheritance

- All 6 POIs remain classified `BLOCKED_INCOMPLETE_SPECIFICATION` and are **not eligible for any lifecycle-inheritance review** until their respective GROUP3-D decisions are made.
- No zone-boundary formula may be assumed for any of the 6 without an author decision, even where the book gives strong implication (Morning/Evening Star).
- No formation-rule threshold (Hammer/Shooting Star wick:body ratio — GROUP3-D3; Morning/Evening Star doji threshold — GROUP3-D7) may be invented.
- No availability-timing rule may be treated as "self-evident" or as automatically following from a boundary or formation decision — every `ENGINEERING-PROVISIONAL` timing inference in this audit is routed into its own independent GROUP3-D decision (GROUP3-D2, GROUP3-D6, GROUP3-D9), never assumed, consistent with the lesson of the RECON-D5 correction to the Group 2 propagation and this document's own correction (Section 1).
- The Hammer/Shooting Star "bounded POI vs. signal-only" question (GROUP3-D4) blocks not just a boundary formula but the more fundamental question of whether a boundary formula should be attempted at all — GROUP3-D5 and GROUP3-D6 cannot proceed until it is resolved.

## 22. Recommended Author-Decision Sequence

This audit recommends, but does not authorize, the following sequence:

1. **GROUP3-D1** — Engulfing zone source.
2. **GROUP3-D2** — Engulfing lifecycle availability timing.
3. **GROUP3-D3** — Hammer/Shooting Star formation thresholds.
4. **GROUP3-D4** — Hammer/Shooting Star POI role.
5. **GROUP3-D5** — Hammer/Shooting Star zone, **only if applicable** (GROUP3-D4 approves a bounded outcome).
6. **GROUP3-D6** — Hammer/Shooting Star timing, **only if applicable** (GROUP3-D4 approves a bounded outcome).
7. **GROUP3-D7** — Morning/Evening Star middle-candle threshold.
8. **GROUP3-D8** — Morning/Evening Star zone.
9. **GROUP3-D9** — Morning/Evening Star timing.

Within each POI family, the zone-boundary decision does not strictly require the timing decision to be resolved first or vice versa, but both are prerequisites before that POI family's specification can be considered complete. For each POI whose decisions are all resolved (and, for Hammer/Shooting Star, only if GROUP3-D4 selects a bounded outcome), a dedicated formation-completion task documents the author-approved formula/threshold directly in that POI's own file — this is a specification-completion task, still distinct from and prior to any lifecycle-inheritance propagation task. Only after a POI's specification is complete should it be re-submitted to a future applicability audit to determine whether it becomes `DIRECT_GENERIC_INHERITANCE`, `CONDITIONAL_GENERIC_INHERITANCE`, or remains excluded/not-applicable — this audit does not pre-classify any of the 6 into those categories. `POI_COVERAGE_MATRIX.md`, `POI_LIFECYCLE_APPLICABILITY_AUDIT.md`, `KNOWLEDGE_COMPLETION_GATE.md`, and `docs/PROJECT_STATE.md` are updated at each stage using the same append-only, cell-scoped patterns already established for Groups 1 and 2.

## 23. Knowledge-Gate Impact

- This audit **does not** modify any individual POI specification.
- **No lifecycle inheritance was propagated.**
- **No recommendation in Section 18/19 is author-approved.**
- **No POI becomes APPROVED** as a result of this audit.
- **All 6 POIs are classified `E. NEEDS_MULTIPLE_AUTHOR_DECISIONS`** (corrected from the original 2×B/4×E split).
- **Nine decision records are identified: seven unconditional and two conditional on GROUP3-D4.**
- **The knowledge gate remains CLOSED.**
- **Phase 0G remains unapproved.**
- Twelve bounded directional POIs remain propagated (4 Group 1 + 8 Group 2) — unaffected and unchanged by this audit or its correction.
- See `knowledge/KNOWLEDGE_COMPLETION_GATE.md` for the complete, authoritative gate status.

## 24. Author Decisions and Propagation (2026-07-19)

**This section records what has happened since Section 23 above. Sections 1–23 (the original audit findings, the corrected six-POI matrix, provenance findings, and all nine decision-record options and engineering recommendations) remain intact and unaltered by this update — no option's text, "Option A/B/C," "Effect of each option," or "Risk of choosing incorrectly" field was deleted.**

**Former audit classification (Sections 7–8, unchanged):** all six POIs were classified `E. NEEDS_MULTIPLE_AUTHOR_DECISIONS`, with nine decision records (seven unconditional, two conditional) required before any could be considered for lifecycle inheritance.

**Current post-decision propagation status (this section):** GROUP3-D1 through GROUP3-D9 have been reviewed and **Author-Approved**, exactly as follows:

| Decision | Approved option (exact) | Affected POIs |
|---|---|---|
| GROUP3-D1 | Zone = complete High-to-Low range of the first, smaller, opposite-direction (engulfed) candle. Bullish Engulfing: Zone Top = High of first bearish candle, Zone Bottom = Low of first bearish candle. Bearish Engulfing: Zone Top = High of first bullish candle, Zone Bottom = Low of first bullish candle. The second (engulfing) candle is confirmation/displacement evidence only, not part of the boundary. | Bullish Engulfing, Bearish Engulfing |
| GROUP3-D2 | `engulfing_pattern_confirmation_time = engulfing_poi_available_time = qualifying_engulfing_candle_close_time`. No third confirmation candle, first return, BOS, or entry confirmation required. Candidate rejected (no POI, no lifecycle event) if the second candle fails any mandatory Engulfing condition. | Bullish Engulfing, Bearish Engulfing |
| GROUP3-D3 | Standard Hammer: Lower Wick Share >= 0.60, Body Efficiency <= 0.30, Upper Wick Share <= 0.10. Standard Shooting Star: Upper Wick Share >= 0.60, Body Efficiency <= 0.30, Lower Wick Share <= 0.10. Strong Shape tier (either pattern): Rejection Wick Share >= 0.70, Body Efficiency <= 0.20, Opposite Wick Share <= 0.05. Tracked as a distinct Hammer/Shooting-Star-specific field, not merged with Pressure Wick Standard V1. | Hammer, Shooting Star |
| GROUP3-D4 | Signal Role = rejection/reversal evidence (bullish for Hammer, bearish for Shooting Star); **POI Role = bounded directional POI** for both. Pattern validity, signal validity, POI lifecycle validity, and entry validity remain four separate concepts. May coexist with a Pressure Wick or other label when each specification independently passes; no label precedence created. | Hammer, Shooting Star |
| GROUP3-D5 | Zone = rejection wick only (body excluded). Hammer: Zone Top = `MIN(Open,Close)`, Zone Bottom = Low. Shooting Star: Zone Top = High, Zone Bottom = `MAX(Open,Close)`. | Hammer, Shooting Star |
| GROUP3-D6 | `hammer_pattern_confirmation_time = hammer_poi_available_time = qualifying_hammer_candle_close_time`; `shooting_star_pattern_confirmation_time = shooting_star_poi_available_time = qualifying_shooting_star_candle_close_time`. No later confirmation candle, first return, or entry confirmation required for lifecycle purposes. Candidate rejected (no pattern, no POI, no lifecycle event) if any mandatory condition (valid Total Range, rejection-wick threshold, Body Efficiency, opposite-wick threshold, direction/colour/context, rejection-wick boundaries) fails at the candle's close. | Hammer, Shooting Star |
| GROUP3-D7 | `middle_candle_body_efficiency = ABS(Middle Close − Middle Open) / (Middle High − Middle Low)`, invalid when `Middle High − Middle Low <= 0`. Standard Doji: `<= 0.10`. Strong Doji shape tier: `<= 0.05`. Middle candle may close bullish or bearish; colour not decisive when the threshold passes. No mandatory Forex gap requirement. | Morning Star, Evening Star |
| GROUP3-D8 | Zone = complete High-to-Low range of the qualifying middle Doji only. Morning Star: Zone Top = Middle Doji High, Zone Bottom = Middle Doji Low. Evening Star: same mapping. Candle 1 and candle 3 excluded from the zone; candle 3 remains pattern-confirmation evidence. | Morning Star, Evening Star |
| GROUP3-D9 | `morning_star_pattern_confirmation_time = morning_star_poi_available_time = qualifying_third_candle_close_time`; `evening_star_pattern_confirmation_time = evening_star_poi_available_time = qualifying_third_candle_close_time`. No fourth confirmation candle, first return, Forex price gap, or entry confirmation required. Candidate rejected (no pattern, no POI, no lifecycle event) if the third candle fails any mandatory three-candle formation condition. | Morning Star, Evening Star |

**All six POI specifications have been completed sufficiently for lifecycle inheritance, and the shared lifecycle has been propagated to all six.** Exact file paths:

| poi_name | file_path |
|---|---|
| Bullish Engulfing Candle | `knowledge/poi_rules/price_action/bullish_engulfing.md` |
| Bearish Engulfing Candle | `knowledge/poi_rules/price_action/bearish_engulfing.md` |
| Hammer | `knowledge/poi_rules/price_action/hammer.md` |
| Shooting Star | `knowledge/poi_rules/price_action/shooting_star.md` |
| Morning Star | `knowledge/poi_rules/price_action/morning_star.md` |
| Evening Star | `knowledge/poi_rules/price_action/evening_star.md` |

Each file received: (a) the approved formation-threshold formula (Hammer/Shooting Star: GROUP3-D3; Morning/Evening Star: GROUP3-D7) documented directly in its "Formation conditions"/"Body treatment"/"Wick treatment"/"Strength classification" sections; (b) the approved zone-boundary formula (GROUP3-D1/D5/D8) documented in "Upper boundary"/"Lower boundary"; (c) for Hammer/Shooting Star, a new "POI role" section documenting the GROUP3-D4 decision; (d) a new "Shared POI Boundary Lifecycle Inheritance" section documenting applicability classification, bounded-zone status, expected direction, Zone Top/Bottom mapping, Entry/Far Boundary mapping, pattern-confirmation time, POI lifecycle-availability time, inherited event states, inherited Close Breach/Reclaim/Displacement directions, False/Genuine Invalidation meaning and effect, Repeated Tap handling, non-repainting timing, linked BTMM effect, evidence/provenance status, and remaining limitations, cross-referencing `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` without duplicating its formulas; and (e) updated "Invalidation," "Machine-testable criteria," "Unresolved questions," and "Author decision" sections cross-referencing the above.

**No formation rule was changed except the explicitly approved GROUP3-D3 (Hammer/Shooting Star wick:body thresholds) and GROUP3-D7 (Morning/Evening Star Doji threshold) additions** — these were previously undefined gaps being filled, not changes to any pre-existing formula. Engulfing's pre-existing formation, size-ratio, strength, and location rules were not altered. No entry, risk, freshness, expiration, or repeated-tap-degradation rule was introduced. No label-precedence rule was introduced — GROUP3-D4's Pressure Wick coexistence finding and GROUP3-D1's Engulfing/Order-Block distinction remain exactly as previously documented. The authoritative shared lifecycle standard (`knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`) was not modified — its Contact Tolerance, Overshoot Tolerance, ten event states, Sustained Breach process, Repeated Tap counting, and no-reactivation rule were inherited unmodified by all six POIs, with no family-specific tolerance override introduced for any of them.

**All six decisions remain Engineering-Provisional.** The evidence status of GROUP3-D1 through GROUP3-D9, and of the inherited shared lifecycle for all six POIs, is unchanged: **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved.** **No POI is production-approved or guaranteed profitable as a result of this propagation.** All six overall POI statuses remain **PARTIAL** — none is marked APPROVED.

`knowledge/POI_COVERAGE_MATRIX.md`, `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`, `knowledge/KNOWLEDGE_COMPLETION_GATE.md`, and `docs/PROJECT_STATE.md` were updated separately to record this propagation. **The final knowledge gate remains CLOSED. Phase 0G remains unapproved.**
