# BTMM Master Summary

Source: `references/private/BTMM_AND_POI_TRADING_BIBLE.docx`, section "BTMM Strategy / Stratégie BTMM" (the book's second major segment, following the POI chapter). Location references use book section titles plus paragraph numbers in the plain-text working extraction (see note on missing page numbers in [POI_MASTER_CATALOG.md](../POI_MASTER_CATALOG.md) and [SOURCE_INDEX.md](../SOURCE_INDEX.md)).

This summary strictly follows the required outline below. Where the book does **not** explicitly teach a listed concept, that is stated plainly rather than inventing a definition.

## What BTMM Means in This Book

BTMM is a trading **strategy** (not merely an analytical tool) developed by Ronny Rostand of Bell Forex Academy. It uses institutional "blueprints" around Points of Interest (POIs) to identify where buy-side and sell-side liquidity is created in the Forex market. It is explicitly distinguished from an analytical tool (trendlines, support/resistance, market structure, indicators): a strategy is "a complete set of rules and guidelines that tells a trader when to enter, when to exit, how to manage risk, what market condition to trade, and how to make decisions." BTMM is built on **three pillars**: Volume, Speed, and Accuracy, applied specifically around the "mitigation" of a POI (i.e., the moment price reaches/interacts with the POI). *(Section: "Definition of the BTMM Strategy"; "Strategy vs Analytical Tool.")*

BTMM is used **only** around a POI that has already been validated using the rules in `knowledge/POI_MASTER_CATALOG.md` — it is not applied "anywhere on the chart." *(Section: "Where BTMM Is Used.")*

## The Core Liquidity Mechanic

The book's foundational liquidity principle, stated explicitly:

> Close a buy = sell liquidity created
> Close a sell = buy liquidity created

Because Forex needs two-sided participation to move, the market cannot let everyone simply buy at demand and sell at supply simultaneously — there would be no opposite order flow. So around any POI, the market creates conditions (fake mitigations, stop hunts, delayed reactions, false breakouts, confusing price movement) that push early traders to close positions, and each closure generates the liquidity needed for the "real" institutional move. *(Section: "How Liquidity Gets Created Around a Point of Interest.")*

## Liquidity Before a POI — Early Buying / Early Selling

Traders may enter before price actually reaches the true POI (an "early buy" or "early sell"), get stopped out when the market moves against them, and their forced closure creates the opposite liquidity that then fuels the real move from the actual POI. *(Section: "1. Liquidity Creation Before POI With Early Buy and Early Sell.")*

## Liquidity Inside a POI — Delay

Price does not always react the instant it enters a POI. The market may deliberately "delay" inside the zone, testing trader patience and forcing early-entrants to close positions out of impatience — this closure again creates liquidity, which can then power the real move. The book is explicit that this delay is **not always a weakness** in the setup; it can be a normal part of liquidity creation. *(Section: "3. Liquidity Creation Within POI.")*

## Liquidity Beyond a POI — After the POI

Sometimes price does not react at the POI but instead passes sharply through/beyond it, creating fear and panic in traders who entered early, forcing them to close (again creating opposite liquidity) before price returns in the originally expected direction. The book explicitly states this is **not always considered a failure of the setup** — it can be a manipulation phase before the real institutional move. *(Section: "2. Liquidity Creation After POI.")*

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** the three liquidity locations above are now preserved as `liquidity_location` = `LIQUIDITY_BEFORE_POI` / `LIQUIDITY_WITHIN_POI` / `LIQUIDITY_AFTER_POI` (plus `MULTIPLE_LOCATIONS`, `NONE_OBSERVED`, `NOT_YET_EVALUATED`), each with an evidence source of `EXPERT_LABELLED`, `RULE_BASED`, `MODEL_PROPOSED`, `HYBRID_REVIEWED`, or `RULE_BASED_REVIEWED`. At least one **reviewed** liquidity-evidence event is mandatory for `BTMM_CONFIRMED` (an unreviewed `MODEL_PROPOSED` event cannot pass the gate alone); if the full reaction window closes with no reviewed evidence, the setup is cancelled with `cancellation_reason = NO_LIQUIDITY_EVIDENCE`. Automatic detection of general liquidity events (the terminology and algorithm for recognizing early buy/sell, delay, and overshoot as they happen in real time) remains unresolved outside one specific reviewed pathway: a confirmed False Invalidation event (see "False Invalidation / Genuine Invalidation" below, resolved under Ambiguity 15) may itself be recorded as reviewed `LIQUIDITY_AFTER_POI` evidence. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## Repeated Taps

**Not defined verbatim in the book.** The term "repeated taps" itself does not appear anywhere in the text. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** for bounded directional POIs, one tap equals one distinct POI interaction event (multiple candles in one continuous interaction count as one tap); a later interaction becomes a new tap only after a confirmed exit beyond the Entry Boundary by more than Contact Tolerance followed by a later touch/re-entry. `tap_count = 1` → `INITIAL_TAP`; `2` → `REPEATED_TAP`; `≥3` → `MULTIPLE_REPEATED_TAPS`. `tap_count` is evidence only — Version 1 does not assume a second tap weakens the POI, a third invalidates it, or more taps strengthen it; no Repeated Tap Strength Score, Freshness Score, or automatic degradation/upgrade score is created. Statistical repeated-tap degradation by POI family remains an empirical-calibration question. See [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md). This is **Author-Approved, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated, and NOT production-approved** — author-added project terminology, not a direct book quotation.

## Stop-Loss Hunting

Mentioned, but only briefly and generally: "stop losses placed by traders can also be hunted to generate additional liquidity" — one of several manipulation mechanisms (alongside fake mitigations, delayed reactions, false breakouts) that create the opposite liquidity BTMM depends on. No book-specific detection rule (e.g., minimum wick length beyond a level, minimum reversal speed) is given beyond what's already captured in the Equal-Highs/Equal-Lows and swing-high/low POI entries in the POI catalog. *(Sections: "How Liquidity Gets Created Around a Point of Interest"; "The Pillars of BTMM Strategy.")*

## False Invalidation / Genuine Invalidation

**Not defined verbatim in the book.** These exact terms do not appear in the text; the closest related idea is the "Liquidity Creation After POI" concept above (a sharp move beyond a POI described as *possibly* manipulation rather than failure), which the book never generalizes into formal rules with distinguishing conditions. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** for bounded directional POIs (zone_top/zone_bottom/expected_direction — e.g. Order Blocks, FVGs, Buy-to-Sell/Sell-to-Buy zones, directional Base formations, Support, Resistance; **not** Equal Highs, Equal Lows, or Trendlines), `FALSE_INVALIDATION_CONFIRMED` requires the complete sequence Close Breach Candidate → Reclaim Confirmed (within 3 confirmed candles) → Displacement After Reclaim Confirmed (within 3 confirmed candles after reclaim, using the approved Market Speed and Displacement Standard's FAST/STRONG FAST classification). `GENUINE_INVALIDATION_CONFIRMED` requires a Close Breach Candidate, no qualifying reclaim within its 3-bar window, and a passed Sustained Breach requirement (≥2 of 3 confirmed closes beyond the far boundary by more than that candle's own Overshoot Tolerance, with bar 3 also breaching). Genuine Invalidation sets `poi_lifecycle_status = INVALIDATED` on the POI and cancels any active linked BTMM setup (`BTMM_CANCELLED`/`POI_REJECTED`) without rewriting history or reactivating the POI. See [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) and [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md). **This standard is Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated, and NOT production-approved** — these terms and formulas are engineering additions approved by the author, not direct book definitions.

## Reclaim

**Not defined verbatim in the book.** The word "reclaim" does not appear anywhere in the text. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** for bounded directional POIs, after a Close Breach Candidate, `RECLAIM_CONFIRMED` requires a confirmed close back inside the zone by at least Contact Tolerance (Bullish: `Reclaim Close ≥ Zone Bottom + Contact Tolerance`; Bearish: `Reclaim Close ≤ Zone Top − Contact Tolerance`) within the next 3 confirmed candles. Reclaim proves only that price closed meaningfully back inside the zone — not expected-direction exit, sufficient displacement, sufficient speed, sufficient reaction strength, BTMM confirmation, or entry confirmation. A new qualifying breach before displacement confirms is `RECLAIM_FAILED` (new event ID, new window, independently evaluated). A reclaim whose displacement window closes without confirmation is `RECLAIM_WITHOUT_DISPLACEMENT` — an incomplete recovery, not False Invalidation. See [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md).

## Displacement After Reclaim

**Not defined verbatim in the book**, for the same reason as above — since "reclaim" itself is not a book term, "displacement after reclaim" cannot be sourced from this text. Note: "displacement" *itself* is a well-defined book term (used extensively for Fair Value Gap and Order Block validation — a strong, aggressive, oversized candle that creates a clear imbalance), but it is never combined with a "reclaim" concept anywhere in the book. **Formalized (POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional, resolves Ambiguity 15):** within 3 confirmed candles after a confirmed reclaim, displacement is confirmed when price closes beyond the Entry Boundary by more than Contact Tolerance **and** the reclaim-to-displacement leg is classified `FAST` or `STRONG_FAST` under the already-approved Market Speed and Displacement Standard (unmodified — Leg Bar Count, Net Directional Distance, Leg Path Distance, Normalized Speed Per Bar, Directional Efficiency, Directional Candle Share). No displacement score is created. See [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md).

## Volume

One of the three BTMM pillars. Refers to "the size and strength of the candle moving into the POI" — i.e., the strength of the move as price approaches/reacts at the POI, analogous to the volume-switch concept used throughout the POI catalog (small candles → big candle = strong volume switch). *(Section: "The Pillars of BTMM Strategy.")*

**Evidence sourcing (Volume and Momentum Proxy Standard Version 1, resolves Ambiguity 3):** Since retail Forex data carries no true exchange volume, this pillar's **primary evidence** is price/candle-behaviour measurements — Relative Size Ratio, Range Context Ratio, Body Efficiency, and Bullish/Bearish Close Position, per `knowledge/MEASUREMENT_STANDARDS.md`, "Volume, Momentum, and Price-Activity Proxy Standard." Tick volume, where available, is **secondary** evidence only (reported as SUPPORTS/NEUTRAL/CONTRADICTS/MISSING) and is never mandatory — missing tick volume must not invalidate a POI or a BTMM setup. External momentum indicators (RSI, MACD, Stochastic, ADX, Rate of Change, etc.) are excluded from the core project as mandatory rules. **The final pass/fail threshold for the BTMM Volume pillar is not yet defined** — none of the individual measurement fields have a minimum value set, and no combined `price_activity_score` exists yet. This remains an open decision. The **BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional (resolves Ambiguity 14)** now formally requires `volume_pillar_status = SUPPORTS` as one of ten mandatory gates before `BTMM_CONFIRMED`; until the final threshold above is set, the gate may use POI-specific approved candle rules, expert-labelled volume-switch evidence, or reviewed hybrid evidence, and produces `BTMM_BLOCKED` (not a silent pass) when evidence is unavailable or still under review. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## Speed

One of the three BTMM pillars. Refers to "how fast price moves into the POI after manipulation" — i.e., how quickly price returns to/reacts at the POI once the liquidity-creation phase (early entries, delay, or overshoot) has run its course. *(Section: "The Pillars of BTMM Strategy.")*

**Evidence sourcing (Market Speed and Displacement Standard Version 1 — Provisional, resolves Ambiguity 7):** The book's single "Speed" pillar is split into two separately-tracked measurements that must never be merged into one score: **BTMM Approach Speed** (how fast price moved toward the POI during the approach leg, before/during manipulation) and **BTMM Reaction Speed** (how fast price moved away from the POI during the reaction leg, after manipulation). Both use the same movement-leg formulas: Leg Bar Count, Net Directional Distance (`|End Price − Start Price|`), Reference ATR (median ATR(14) across the leg), Normalized Speed Per Bar (`Net Directional Distance ÷ (Leg Bar Count × Reference ATR)`), Leg Path Distance (sum of candle Total Ranges in the leg), Directional Efficiency (`Net Directional Distance ÷ Leg Path Distance`), and Directional Candle Share (fraction of candles closing in the movement direction). A leg is classified FAST when Normalized Speed Per Bar ≥0.50, Directional Efficiency ≥0.60, and Directional Candle Share ≥0.67 (all three); STRONG FAST at ≥0.75/≥0.75/≥0.80; otherwise SLOW_OR_UNCLEAR. Full formulas in `knowledge/MEASUREMENT_STANDARDS.md`, "Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard."

**POI Dwell Time is a separate concept from both Approach and Reaction Speed.** It measures how long price remains inside a POI zone (POI Dwell Bars = consecutive confirmed candles intersecting the POI from first touch to exit, plus First Touch Time, Exit Time, Dwell Duration, and Exit Direction as separate fields). No maximum permitted dwell time is set. Consistent with the book's own "Liquidity Inside a POI — Delay" concept above, **a delayed reaction inside a POI (long dwell) must not automatically invalidate BTMM.** **Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** dwell without immediate reaction is now explicitly handled by retaining `primary_state = BTMM_FORMING`, `formation_stage = REACTION_MONITORING` — dwell alone never causes cancellation, and no maximum dwell time is set by this decision either. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

**Anchors remain unresolved.** Automatic detection of the manipulation endpoint, approach starting price, POI first-touch price, reaction starting point, and reaction endpoint all remain unresolved. Ambiguity 14 (the BTMM forming/confirmed/cancelled state machine) is now resolved provisionally (see [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md)), but that decision formalizes lifecycle states and gates only — it does not itself define automatic anchor detection. BTMM Approach/Reaction Speed continues to be measured using expert-labelled or otherwise explicitly approved movement-leg anchors only — no automatic anchor-detection algorithm has been invented.

**No final BTMM speed pass threshold may independently validate a complete BTMM formation.** FAST/STRONG FAST/SLOW_OR_UNCLEAR is one input signal only; it must never, by itself, approve or reject a POI, a BTMM formation, an entry, or a trade. This decision does not itself create a BTMM state machine; the BTMM Lifecycle and Confirmation State Machine (Ambiguity 14) is a separate, later-approved decision that references this standard's `FAST`/`STRONG_FAST`/`SLOW_OR_UNCLEAR` classifications directly as its Reaction Speed Gate, without changing any formula here.

## Accuracy

One of the three BTMM pillars. Refers to "how precisely that candle reaches or targets the Point of Interest" — i.e., whether the reaction candle actually hits/respects the drawn POI zone rather than reacting from an unrelated price level. *(Section: "The Pillars of BTMM Strategy.")*

**Evidence sourcing (POI Zone Interaction, Penetration, and Overshoot Standard Version 1 — Provisional, resolves Ambiguity 8):** For any POI with defined zone boundaries, "accuracy" is now measured as geometric zone-interaction classification — EDGE_TOUCH, PARTIAL_ENTRY, DEEP_ENTRY, FAR_BOUNDARY_TOUCH, CONTROLLED_OVERSHOOT, or EXCESSIVE_OVERSHOOT, plus NEAR_MISS/NO_CONTACT/NONCANONICAL_SIDE_INTERACTION for non-touches. Full formulas in `knowledge/MEASUREMENT_STANDARDS.md`, "POI Zone Interaction, Penetration, and Overshoot Standard."

**This interaction geometry is evaluated strictly separately from BTMM reaction strength** — how accurately price *reached* the POI (this standard) is a different question from whether the *reaction away* from the POI was strong (now resolved provisionally, see "Reaction Strength (Post-Interaction)" below, Ambiguity 9). Neither one determines the other.

**NEAR_MISS is not an actual POI touch.** A candle that comes close to but does not intersect the zone (within Contact Tolerance) does not count as a confirmed interaction and must not increment the interaction count used elsewhere in BTMM analysis.

**CONTROLLED_OVERSHOOT may remain eligible for later BTMM/reaction analysis** — a candle that penetrates fully through the zone but overshoots the far boundary only by a small, tolerance-bounded amount is not automatically disqualified. **EXCESSIVE_OVERSHOOT and CLOSE_BREACH_CANDIDATE (a close beyond the far boundary) are invalidation *candidates* only** — neither one automatically invalidates the POI or the BTMM setup; general POI invalidation remains unresolved.

**Final BTMM validity remains unresolved.** This standard supplies only the geometric "did price accurately reach the zone, and how" measurement. It does not, by itself, confirm a BTMM formation, approve an entry, or validate a trade. **Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** this standard's EDGE_TOUCH/PARTIAL_ENTRY/DEEP_ENTRY/FAR_BOUNDARY_TOUCH/CONTROLLED_OVERSHOOT classifications are now used directly as the state machine's Accuracy Gate (pass), with NO_CONTACT/NEAR_MISS/NONCANONICAL_SIDE_INTERACTION/EXCESSIVE_OVERSHOOT as fail — without changing any formula here. Full BTMM confirmation still requires nine further mandatory gates. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

No numeric thresholds are given for any of the three pillars beyond what is now defined for Speed (Ambiguity 7) and Accuracy (Ambiguity 8) above; the Volume pillar's own minimum thresholds also remain unset (see "Volume" above). See ambiguity register.

## Reaction Strength (Post-Interaction)

**Evidence sourcing (POI Reaction Strength Standard Version 1 — Provisional, resolves Ambiguity 9):** Once an eligible POI Zone Interaction has occurred (EDGE_TOUCH, PARTIAL_ENTRY, DEEP_ENTRY, FAR_BOUNDARY_TOUCH, or CONTROLLED_OVERSHOOT), the move away from the POI is classified over a five-bar evaluation window as AWAITING_REACTION, REACTION_IN_PROGRESS, WEAK_REACTION, STANDARD_REACTION, or STRONG_REACTION. Full formulas in `knowledge/MEASUREMENT_STANDARDS.md`, "POI Reaction Strength, Distance, Efficiency, and Classification Standard."

**POI Reaction Strength is separate from BTMM validity.** This standard measures only the geometric strength/distance/efficiency of the post-touch move — it does not, by itself, confirm or deny a BTMM formation, an entry, or a trade.

**AWAITING_REACTION and REACTION_IN_PROGRESS are not failed BTMM states.** They simply mean the five-bar reaction window has not yet started or not yet completed — neither implies the setup has failed.

**Delayed reaction is not automatically invalid.** Consistent with "Liquidity Inside a POI — Delay" above, POI dwell time before Reaction Start may itself be supporting liquidity creation rather than a sign of failure — the reaction window only begins once Reaction Start is confirmed, precisely so dwell is not mistaken for weakness.

**STRONG_REACTION is supporting evidence only** — it does not independently prove POI validity, BTMM validity, entry validity, or trade outcome.

**WEAK_REACTION does not automatically cancel a BTMM setup on its own within this standard** — it is one input signal, not a cancellation rule, as far as this standard alone is concerned.

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** this standard's STANDARD_REACTION/STRONG_REACTION classifications are now used directly as the state machine's Reaction Gate (pass); a completed five-bar window classified WEAK_REACTION now does produce `BTMM_CANCELLED` with `cancellation_reason = WEAK_REACTION` at the state-machine level (without invalidating the POI) — this is a state-machine rule layered on top of, and without changing, this standard's own formulas. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## M15 Role

Explicitly named as one of the three timeframes for observing "BTMM formation, creation, and execution," alongside M5 and M1. M5/M15 are described as helping "confirm the formation." *(Section: "A Must Recommendation for a Perfect Working BTMM Strategy.")*

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** the Formation Timeframe Gate requires an approved formation confirmation on **M5 or M15** before `BTMM_CONFIRMED` is possible. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## M5 Role

Same as M15 — one of the two timeframes (with M15) the author says can "help confirm the formation" of a BTMM setup.

**Formalized:** satisfies the Formation Timeframe Gate on the same terms as M15 (either one suffices; the book does not require both).

## M1 Role

Explicitly described as usable "for precise execution" — the entry-timing timeframe, once M5/M15 have confirmed the formation.

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** M1 may provide precision evidence, execution refinement, or additional supporting confirmation, but an **M1-only setup must remain `BTMM_FORMING` or `BTMM_BLOCKED`** — it must not independently become `BTMM_CONFIRMED`. This matches the book's own M5/M15-confirms, M1-executes role split; it does not change entry-timing rules, which remain unresolved (see "Entry and Risk Remain Separate" below).

## Conditions Showing BTMM Is Forming

The book does not present a single itemized "forming" checklist under that exact heading. Synthesizing only from what is explicitly stated elsewhere in the same section (not inventing new criteria):
- Price has reached a validated POI (per `knowledge/POI_MASTER_CATALOG.md`).
- One or more of the three liquidity-creation behaviors is underway: early buy/sell before the POI, a delay inside the POI, or an overshoot beyond the POI.
- The setup is still being watched for volume, speed, and accuracy — none of the three pillars has yet confirmed.

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** the book's narrative "forming" description above is now formalized as `primary_state = BTMM_FORMING`, with one of six formation stages tracked separately: `CONTEXT_CHECK`, `LIQUIDITY_MONITORING`, `APPROACH_MONITORING`, `POI_INTERACTION`, `REACTION_MONITORING`, `FINAL_GATE_EVALUATION`. See [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## Conditions Showing BTMM Is Confirmed

Again, no single itemized "confirmed" checklist exists verbatim in the book. Based only on explicit statements: a BTMM setup is treated as ready for execution when the trader can clearly identify (1) liquidity creation around the POI (before, within, or after it), (2) the market's overall direction/trend agreeing with the trade direction, (3) volume, speed, and accuracy all present as price reacts at the POI, and (4) the trader is in the correct session with sufficient volume/volatility for the asset. *(Section: "A Must Recommendation for a Perfect Working BTMM Strategy.")*

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** the book's four narrative confirmation conditions above are now formalized as ten mandatory gates that must **all** pass (no weighting, majority vote, average score, or composite score) before `primary_state = BTMM_CONFIRMED`: POI Gate, Market Direction Gate, Analytical Framework Gate, Active Session Gate, Liquidity Gate, Accuracy Gate, Volume Pillar Gate, Reaction Gate, Reaction Speed Gate, and Formation Timeframe Gate. `BTMM_CONFIRMED` becomes available only after the complete five-bar POI reaction window closes and `FINAL_GATE_EVALUATION` passes — never exposed historically at POI creation, manipulation time, first touch, or reaction-start time (non-repainting). Full gate definitions in [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md). **This standard is explicitly Author-Approved, Engineering-Provisional, NOT YET empirically calibrated or out-of-sample validated, and NOT production-approved — `BTMM_CONFIRMED` is not an automatic trade instruction and does not by itself prove the trade will be profitable.**

## Conditions Showing the Setup Is Cancelled

The book does not define explicit cancellation/invalidation criteria for a BTMM setup (consistent with the absent "false/genuine invalidation" concept above). The only explicit negative condition stated is: **"if none of these liquidity creation conditions is present, then the trade should not be taken."** No other cancellation rule (e.g., a maximum time-in-POI, a maximum overshoot distance, or a structural break that cancels the setup) is given.

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** the book's single explicit negative rule above is now one of ten possible `cancellation_reason` values under one terminal state, `BTMM_CANCELLED`: `POI_REJECTED`, `CONTEXT_REJECTED`, `SESSION_INACTIVE`, `INTERACTION_INELIGIBLE`, `DIRECTIONAL_CONTINUATION`, `WEAK_REACTION`, `REACTION_SPEED_FAILED`, `VOLUME_PILLAR_FAILED`, `NO_LIQUIDITY_EVIDENCE`, `MANUAL_REVIEW_REJECTED`. Cancelling a BTMM setup never invalidates the underlying POI, and `BTMM_CANCELLED` can never transition back to `BTMM_CONFIRMED` — a later eligible interaction creates a new, separate setup. A fifth state, `BTMM_BLOCKED`, is used (not cancellation) when mandatory information is simply unavailable. Full definitions in [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md).

## Required Supporting Conditions (also stated as mandatory in the book)

The book's closing recommendation ("A Must Recommendation for a Perfect Working BTMM Strategy") states BTMM only works when combined with:
1. Trading in the direction of market trend (BTMM is not primarily counter-trend).
2. Trading within the right session and on assets with real volume/volatility/liquidity.
3. Using BTMM inside a proper analytical framework (market structure, support/resistance, trendline analysis, etc.) — never standalone.
4. Respecting risk management (lot size, stop loss, risk-to-reward, account protection) regardless of how good the BTMM setup looks.
5. Respecting the M1/M5/M15 timeframe roles described above.
6. Confirming liquidity creation (before/within/after the POI) before executing.

**Formalized (BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional, resolves Ambiguity 14):** conditions 1–3 and 6 above map to the Market Direction, Analytical Framework, Active Session, and Liquidity Gates respectively (all mandatory, none automatic — see "Context Gate" and "Liquidity Gate" in [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md)). Condition 4 (risk management) and condition 5's execution-timing aspect are explicitly **not** defined by this decision — `BTMM_CONFIRMED` triggers a separate, later execution/risk module that may evaluate entry validity, stop loss, take profit, risk-to-reward, lot size, account risk, news restrictions, spread, and slippage; `BTMM_CONFIRMED` is never presented as an automatic trade instruction.

## BTMM Lifecycle and Confirmation State Machine (Ambiguity 14, Resolved Provisionally)

A dedicated, authoritative specification now exists: [BTMM_STATE_MACHINE.md](BTMM_STATE_MACHINE.md) (summarized in `knowledge/MEASUREMENT_STANDARDS.md`, "BTMM Lifecycle, Gates, State Transitions, and Confirmation Timing Standard"). It formalizes:

- **Five primary states:** `BTMM_CANDIDATE`, `BTMM_FORMING`, `BTMM_BLOCKED`, `BTMM_CONFIRMED`, `BTMM_CANCELLED`.
- **Six formation stages** (while `BTMM_FORMING`): `CONTEXT_CHECK`, `LIQUIDITY_MONITORING`, `APPROACH_MONITORING`, `POI_INTERACTION`, `REACTION_MONITORING`, `FINAL_GATE_EVALUATION`.
- **Ten mandatory confirmation gates**, all of which must pass with no weighting/majority-vote/composite score: POI, Market Direction, Analytical Framework, Active Session, Liquidity, Accuracy, Volume Pillar, Reaction, Reaction Speed, Formation Timeframe.
- **Non-repainting confirmation timing:** `BTMM_CONFIRMED` is available only from `btmm_confirmation_time`, after the five-bar POI reaction window closes and `FINAL_GATE_EVALUATION` passes — never at POI creation, manipulation, first touch, or reaction-start time.
- **No retroactive rewriting:** once confirmed or cancelled, setup identity, direction, and timing never change; a later trade outcome never upgrades or downgrades a setup's lifecycle state; a new interaction always creates a new `btmm_setup_id`.
- **Entry/risk separation:** entry validity, stop loss, take profit, risk-to-reward, lot sizing, account risk, news restrictions, spread, and slippage are explicitly out of scope for this decision.

**Ambiguity 15 integration:** the state machine references `liquidity_evidence_status`, `liquidity_location`, and `liquidity_evidence_source` as evidence fields. Reclaim, displacement after reclaim, repeated taps, false invalidation, and genuine invalidation are now resolved provisionally under Ambiguity 15 — see "Repeated Taps," "False Invalidation / Genuine Invalidation," "Reclaim," and "Displacement After Reclaim" above, and [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) for the authoritative specification. The state machine itself is unchanged except for two integration points: a reviewed False Invalidation event may satisfy the Liquidity Gate as `LIQUIDITY_AFTER_POI` evidence, and a Genuine Invalidation event triggers `BTMM_CANCELLED`/`POI_REJECTED` on the linked setup. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy was changed by that integration.

## POI Boundary Breach, Reclaim and Invalidation Standard (Ambiguity 15, Resolved Provisionally)

A dedicated, authoritative specification now exists: [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) (summarized in `knowledge/MEASUREMENT_STANDARDS.md`, "POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard"). It applies only to bounded directional POIs (zone_top/zone_bottom/expected_direction) — not to Equal Highs, Equal Lows, or Trendlines, which retain their own unresolved lifecycle rules. It formalizes:

- **Close Breach Candidate:** a confirmed close beyond the far boundary by more than Overshoot Tolerance (reused from the approved POI Zone Interaction Standard). Not itself invalidation.
- **Reclaim:** a confirmed close back inside the zone by at least Contact Tolerance within 3 confirmed candles. Proves only that price closed back inside — nothing about BTMM, entry, or trade outcome.
- **Displacement after reclaim:** a further close beyond the entry boundary plus a FAST/STRONG FAST reclaim-to-displacement leg within 3 more confirmed candles.
- **False Invalidation:** the complete breach → reclaim → displacement sequence. May count as reviewed `LIQUIDITY_AFTER_POI` evidence for the BTMM Liquidity Gate.
- **Genuine Invalidation:** a breach with no qualifying reclaim and a passed Sustained Breach requirement. Sets the POI to `INVALIDATED` (never reactivated) and cancels any active linked BTMM setup.
- **Repeated taps:** `INITIAL_TAP` / `REPEATED_TAP` / `MULTIPLE_REPEATED_TAPS`, counted as evidence only — no automatic degradation, upgrade, freshness, or strength scoring.

**Provenance and evidence status:** every term above carries three labels — Book-Supported Underlying Concept, Author-Added Project Terminology, and Engineering-Provisional Operational Definition. The standard is **Author-Approved, Author-Added Project Terminology, Engineering-Provisional, NOT YET empirically calibrated, NOT YET out-of-sample validated, and NOT production-approved** — the exact terms, windows, and formulas are project additions, not direct book quotations.

**Remaining exclusions:** statistical repeated-tap degradation by POI family; POI freshness scoring; POI expiration by age; POI-family-specific invalidation overrides; Trendline reclaim and final line invalidation; Equal High/Equal Low sweep lifecycle; automatic market direction/analytical-framework/session detection; entry confirmation, stop loss, take profit, risk-to-reward, lot sizing, news restrictions; empirical calibration; out-of-sample validation; production approval.

**Evidence status:** this standard is **Author-Approved, Engineering-Provisional, NOT YET Empirically Calibrated, NOT YET Out-of-Sample Validated, and NOT Production-Approved.** It must not be presented as a proven profitable trading system, and requires future testing against expert-approved/rejected BTMM examples across XAUUSD/EURUSD/GBPUSD, M1/M5/M15, different sessions, volatility regimes, liquidity before/within/after POIs, and different POI families before it can be considered final or production-approved.
