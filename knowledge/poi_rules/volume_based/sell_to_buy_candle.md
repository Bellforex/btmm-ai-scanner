# Sell-to-Buy Candle

## Alternative book name

NOT DEFINED IN BOOK.

## Family

Volume-Based POI

## Direction

Bullish (produces a buy opportunity; begins life as a failed strong bearish/sell candle).

## Source pages

"3. Buy-to-sell zones/Sell-to-buy zones" (paragraphs 288-341); formal appendix "Sell-to-Buy Candle Validation Conditions" (paragraphs 1091-1124); drawing/strength rules (paragraphs 1125-1159).

## Book definition

A strong bearish candle within an existing downtrend that fails to produce further bearish continuation, followed by a bullish reversal - becomes a POI because price may revisit it before another strong buy move.

## Required market location

Must appear within an active, existing downward price movement (selling pressure already underway before the candle forms).

## Formation conditions

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional (Ambiguity 13): **Author-Approved, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated.** A Sell-to-Buy candidate must be a confirmed closed bearish candle (Close < Open) appearing within an existing downward-price context (the full quantitative definition of that context remains unresolved - not defined using HH, HL, BOS, CHoCH, a moving average, or any other invented structure rule). Bearish Close Position = (High − Close) ÷ Total Range. `STANDARD_SELL_TO_BUY_CANDIDATE` requires Candidate Size Ratio >= 2.00, Body Efficiency >= 0.60, Bearish Close Position >= 0.70; `STRONG_SELL_TO_BUY_CANDIDATE` requires >= 3.00 / >= 0.70 / >= 0.80. A zero-range or invalid candle cannot qualify. See knowledge/MEASUREMENT_STANDARDS.md, "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard."

## Candidate-candle requirements

Bearish Close Position, Body Efficiency, and Candidate Size Ratio must all clear the STANDARD or STRONG tier thresholds above; a candidate failing them becomes `REJECTED_CANDIDATE_CANDLE` and cannot proceed to the reversal window.

## Preceding comparison group

Preceding Maximum Range = the largest Total Range among exactly the 3 confirmed candles immediately before the candidate candle; Candidate Size Ratio = Candidate Total Range ÷ Preceding Maximum Range, guarded against a missing/zero Preceding Maximum Range. This resolves the previously open question of how many preceding candles form "the relevant preceding-candle group" (fixed at 3, not changed by this decision).

## Confirmation conditions

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: within the 3-bar post-candidate reversal window, `STANDARD_PATTERN` requires at least one confirmed post-candidate close above Candidate Midpoint, Opposite Close Displacement Ratio >= 0.50, Directional Efficiency >= 0.50, Directional Candle Share >= 0.67, and no `REJECTED_DIRECTIONAL_CONTINUATION` event; `STRONG_PATTERN` additionally requires a Strong candidate candle, at least one confirmed post-candidate close above Candidate High, Opposite Close Displacement Ratio >= 1.00, Directional Efficiency >= 0.60, and Reversal Speed Classification FAST or STRONG FAST. Overall pattern strength is limited by the weaker of the candidate-candle tier and the reversal tier. A candidate without at least Standard Reversal confirmation is rejected; a large candle alone is never a confirmed POI. The book's own "buyers have taken control" narrative is not itself formalized beyond this - it remains a qualitative description.

## Three-bar reversal window

Exactly 3 confirmed candles immediately after the candidate candle are evaluated (confirmation bar 1, 2, 3). Confirmation may occur on any of the three bars once all required conditions are first satisfied; the earliest such confirmed candle time is stored as `reversal_confirmation_time`. If bar 3 closes without Standard Reversal conditions met, classify `REJECTED_INSUFFICIENT_REVERSAL`. The window is not extended beyond three candles.

## Continuation rejection

Candidate Reference ATR = ATR(14) on the candidate candle (same symbol/provider/timeframe); Continuation Close Tolerance = MAX(2 × Minimum Price Tick, 0.10 × Candidate Reference ATR). Before reversal confirmation, `REJECTED_DIRECTIONAL_CONTINUATION` is recorded when any post-candidate confirmed close falls below Candidate Low by more than Continuation Close Tolerance. A wick beyond Candidate Low is stored separately as `continuation_wick_excursion` and never alone triggers rejection - confirmed close continuation is the primary rejection evidence. Once rejected before confirmation, the candidate cannot later become confirmed from the same three-bar window.

## Opposite close displacement

Highest Reversal Close = the highest confirmed close observed so far in the reversal window; Opposite Close Displacement = Highest Reversal Close − Candidate Close (never negative); Opposite Close Displacement Ratio = that displacement ÷ Candidate Total Range. Close displacement is the approved confirmation measurement; opposite-direction wick excursion may be stored separately if later required.

## Candidate midpoint

Candidate Midpoint = (Candidate High + Candidate Low) ÷ 2, used as the Standard Reversal close-through threshold.

## Directional efficiency

Calculated via the already-approved Market Speed and Displacement Standard V1 — Provisional over the opposite-direction (bullish) reversal leg from confirmation bar 1 through the current evaluated bar; preserved independently, never merged into a composite score.

## Directional candle share

Calculated via the same Market Speed and Displacement Standard fields, preserved independently alongside Directional Efficiency.

## Reversal speed

Reversal Speed Classification (NORMAL/FAST/VERY FAST equivalents per the Market Speed and Displacement Standard) is required at FAST or STRONG FAST for Strong Reversal confirmation only; not required for Standard Reversal. The approved Market Speed formulas/thresholds are unchanged by this decision.

## Origin candle or level

The single failed strong bearish candle itself (`failed_candle_id`). Non-repainting: candidate OHLC values never move once set.

## Upper boundary

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: Zone Top = Candidate Candle High, fixed after successful reversal confirmation - the complete failed-candle range, never refined, shrunk, averaged, or recentered.

## Lower boundary

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: Zone Bottom = Candidate Candle Low, fixed after successful reversal confirmation.

## Wick treatment

Full candle range used for the zone; wicks included, per Measurement Standard V1 SS5.

## Body treatment

Not separately specified; body relevant only to establishing the candle 'closed bearish' with strong momentum.

## Candle-size requirement

Size Ratio (Total Range) >= 2.0 (standard) / >= 3.0 (stronger), per Measurement Standard V1. Ambiguity 2 is now resolved via Small Candle Standard V1: the failed directional candle qualifies against the preceding group when the group's reference Total Range <= 0.50x (standard) / <= 0.3333x (strong) the failed candle's Total Range, with a separate secondary Recent Market Context classification that does not override this. Comparison target per the approved standard: the largest Total Range among the relevant preceding-candle group (this supersedes the earlier informal "average size of preceding candles" description). The preceding-candle-group count is now resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional (Ambiguity 13): exactly 3 confirmed candles immediately before the candidate candle (Preceding Maximum Range). See knowledge/MEASUREMENT_STANDARDS.md, "Small Candle and Recent Market Context Standard" and "Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard."

## Volume or momentum proxy

Resolved under Volume and Momentum Proxy Standard V1 (Ambiguity 3): primary evidence is price/candle behaviour (Relative Size Ratio, Range Context Ratio, Body Efficiency, Bearish Close Position of the failed bearish candle itself), with tick volume as secondary-only evidence (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING; never mandatory). External indicators (RSI, MACD, etc.) are excluded as mandatory rules. See knowledge/MEASUREMENT_STANDARDS.md, "Volume, Momentum, and Price-Activity Proxy Standard." No minimum thresholds for these general proxy fields have been set yet. Reversal-confirmation distance is now resolved separately under Ambiguity 13 (see Formation/Confirmation conditions above).

## Trend requirement

Must occur within an existing downtrend - stated explicitly.

## Market-structure requirement

Not defined beyond 'existing bearish price movement.'

## Liquidity requirement

Not defined as specific to this POI.

## Timeframe requirement

Explicit ranking: Weekly > Daily > 4H > 1H > 15-minute.

## Strength classification

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: candidate-candle tier (Standard >=2x / Strong >=3x, per the book's original ratio language) is now combined with the reversal tier (Standard/Strong Reversal, per Confirmation conditions above) into an overall pattern strength: Standard candidate + Standard reversal = `STANDARD_PATTERN`; Standard candidate + Strong reversal = `STANDARD_PATTERN`; Strong candidate + Standard reversal = `STANDARD_PATTERN`; Strong candidate + Strong reversal = `STRONG_PATTERN`. Overall strength is limited by the weaker component. "Weak" remains explicitly disqualified as high-quality; a candidate without at least Standard Reversal confirmation is rejected.

## Non-repainting availability

Resolved under Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional: a confirmed POI becomes available to downstream logic only at `reversal_confirmation_time`, never historically at the candidate candle's original time. Once confirmed, candidate OHLC, zone boundaries, and reversal confirmation time never move, and later price action never retrospectively alters the original pattern classification.

## Freshness

NOT DEFINED IN BOOK.

## Partial mitigation

NOT DEFINED IN BOOK.

## Full mitigation

NOT DEFINED IN BOOK.

## Invalidation

Not defined as a standing post-formation rule. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** this POI directly inherits the shared bounded-directional-POI lifecycle — Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, and Genuine Invalidation are now defined at the shared-standard level, as a standing post-formation rule. See "Shared POI Boundary Lifecycle Inheritance" below and `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` for the complete, authoritative formulas and event transitions. This does not change any Ambiguity 13 formation, confirmation, boundary, or pattern-strength formula.

## Expiration

NOT DEFINED IN BOOK.

## Shared POI Boundary Lifecycle Inheritance

**Applicability classification:** `DIRECT_GENERIC_INHERITANCE` (see `knowledge/poi_lifecycle/POI_LIFECYCLE_APPLICABILITY_AUDIT.md`).

**Authoritative shared standard:** `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15). This section cross-references that standard's formulas and event transitions rather than duplicating or altering them.

**Bounded-zone status:** Bounded (two-sided zone; the complete candidate candle range). `Zone Top > Zone Bottom` is required for valid bounded-zone geometry, per the shared standard — structurally guaranteed here since a confirmed candle's High is always greater than its Low.

**Expected direction:** BULLISH.

**Zone Top mapping:** Candidate Candle High, fixed after successful reversal confirmation (the already-approved Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 boundary — unchanged by this inheritance).

**Zone Bottom mapping:** Candidate Candle Low, fixed after successful reversal confirmation (the already-approved Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 boundary — unchanged by this inheritance). The complete candidate-candle range remains the fixed POI zone.

**Entry Boundary mapping:** Zone Top.

**Far Boundary mapping:** Zone Bottom.

**Inherited event states:** `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — all defined by, and inherited unmodified from, the authoritative shared standard.

**Inherited Close Breach direction:** `CLOSE_BREACH_CANDIDATE` occurs when a confirmed candle closes below Zone Bottom by more than the approved Overshoot Tolerance.

**Inherited Reclaim direction:** `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone at or above `Zone Bottom + Contact Tolerance`, within the shared standard's 3-bar reclaim window.

**Inherited displacement direction:** `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` requires both a confirmed close above `Zone Top + Contact Tolerance` and a reclaim-to-displacement leg classified FAST or STRONG_FAST (via the approved Market Speed and Displacement Standard), within the shared standard's 3-bar displacement window.

**False Invalidation meaning:** `FALSE_INVALIDATION_CONFIRMED` requires the complete Close Breach Candidate → Reclaim Confirmed → Displacement After Reclaim Confirmed sequence; a breach alone or a reclaim alone is never sufficient. May be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate under the terms defined in the shared standard.

**Genuine Invalidation effect:** `GENUINE_INVALIDATION_CONFIRMED` (Close Breach Candidate + no qualifying reclaim within the 3-bar window + a passed Sustained Breach requirement) sets `poi_lifecycle_status = INVALIDATED` for this specific POI instance; the POI is never reactivated. Any active linked BTMM setup connected to this POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM reason — no new reason created).

**Repeated Tap handling:** taps are counted (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`) as evidence only, using this POI's Entry Boundary (Zone Top) for the separation condition. No automatic degradation, upgrade, freshness, or entry-validity determination is created by tap count.

**Non-repainting timing:** all inherited lifecycle events (breach, reclaim, displacement, false/genuine invalidation) become available only after their complete conditions are confirmed, per the shared standard. This is layered on top of, and does not change, the already-approved `reversal_confirmation_time` non-repainting rule for the candidate candle's own formation.

**Linked BTMM effect:** as described under "Genuine Invalidation effect" and "False Invalidation meaning" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy is changed by this inheritance.

**Evidence/provenance status:** the inherited lifecycle is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved** — the same evidence status as the authoritative shared standard. This inheritance does not make this POI production-ready or proven profitable.

**Remaining limitations:** the full quantitative preceding downward-price context (formation precondition), freshness, expiration, repeated-tap degradation, family-specific lifecycle override research, empirical calibration, out-of-sample validation, production approval, retest entry confirmation, BTMM entry logic, and risk rules (stop loss, take profit, risk-to-reward, lot sizing, news restrictions, spread, slippage) all remain unresolved and are not defined by this inheritance.

## Overlap with other POIs

Related to Order Block and Engulfing; distinguished by the fail-then-reverse requirement on the reference candle itself.

## Positive example

Yes (paragraphs 304-309, 341, 1161). Not visually reviewed pixel-by-pixel.

## Negative example

No confirmed negative-example image caption.

## Machine-testable criteria

Partial - candidate-candle qualification, the 3-candle preceding comparison group, the 3-bar reversal confirmation window, directional-continuation rejection, opposite close displacement, STANDARD/STRONG pattern-strength classification, and (via direct inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard — see "Shared POI Boundary Lifecycle Inheritance" above) Close Breach Candidate, Reclaim, Displacement After Reclaim, False Invalidation, Genuine Invalidation, and repeated-tap counting are now all testable. Not testable: the full quantitative preceding downward-price context (formation precondition, still qualitative), freshness, partial/full mitigation, repeated-touch degradation, expiration, retest entry confirmation, BTMM state transitions (none defined by this decision).

## Unresolved questions

The full quantitative definition of the preceding downward-price context (formation precondition); which general proxy fields apply is resolved (Ambiguity 3), but their minimum thresholds are not yet set; freshness; partial/full mitigation; repeated-touch degradation; expiration; retest entry confirmation; BTMM state transitions (Ambiguity 14, unchanged). (Final invalidation, reclaim, displacement after reclaim, false invalidation, and genuine invalidation are now resolved provisionally via direct inheritance of the POI Boundary Breach, Reclaim and Invalidation Standard, Ambiguity 15 — see "Shared POI Boundary Lifecycle Inheritance" above; this did not change any Ambiguity 13 formula.)

## Author decision

**Evidence status: Author-Approved, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, NOT Production-Approved.** Candidate-candle qualification, the 3-candle preceding comparison group, the 3-bar reversal confirmation window, Continuation Close Tolerance and directional-continuation rejection, opposite close displacement, Candidate Midpoint, reversal-leg measurements (via the approved Market Speed and Displacement Standard), STANDARD/STRONG reversal, overall pattern-strength classification, complete candle-range zone boundaries, and non-repainting availability are approved (provisionally) - see Buy-to-Sell and Sell-to-Buy Reversal Confirmation Standard V1 — Provisional. Direct inheritance of the shared POI Boundary Breach, Reclaim and Invalidation Standard is also approved (provisionally) - see "Shared POI Boundary Lifecycle Inheritance" above. The full quantitative preceding-context definition, freshness, mitigation, expiration, and retest entry confirmation remain pending.

## Approval status

PARTIAL
