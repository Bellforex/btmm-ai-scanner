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

## Repeated Taps

**Not defined in the book.** The term "repeated taps" (or an equivalent concept of price touching a POI multiple times before the real move) does not appear anywhere in the text. This must not be invented; it requires direct author input if the scanner is expected to detect it. See [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md).

## Stop-Loss Hunting

Mentioned, but only briefly and generally: "stop losses placed by traders can also be hunted to generate additional liquidity" — one of several manipulation mechanisms (alongside fake mitigations, delayed reactions, false breakouts) that create the opposite liquidity BTMM depends on. No book-specific detection rule (e.g., minimum wick length beyond a level, minimum reversal speed) is given beyond what's already captured in the Equal-Highs/Equal-Lows and swing-high/low POI entries in the POI catalog. *(Sections: "How Liquidity Gets Created Around a Point of Interest"; "The Pillars of BTMM Strategy.")*

## False Invalidation / Genuine Invalidation

**Not defined in the book.** These exact terms, or an equivalent explicit two-state model ("this looked broken but wasn't" vs. "this really is broken"), do not appear in the text. The closest related idea is the "Liquidity Creation After POI" concept above — a sharp move beyond a POI is described as *possibly* manipulation rather than failure — but the book never generalizes this into formal "false vs. genuine invalidation" rules with distinguishing conditions. This is a genuine gap requiring author clarification, not something to infer. See [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md).

## Reclaim

**Not defined in the book.** The word "reclaim" does not appear anywhere in the text, and no equivalent concept (price re-entering and closing back inside a broken level/zone) is described under any other name. Must not be invented.

## Displacement After Reclaim

**Not defined in the book**, for the same reason as above — since "reclaim" itself is not a book concept, "displacement after reclaim" cannot be sourced from this text. Note: "displacement" *itself* is a well-defined book term (used extensively for Fair Value Gap and Order Block validation — a strong, aggressive, oversized candle that creates a clear imbalance), but it is never combined with a "reclaim" concept anywhere in the book.

## Volume

One of the three BTMM pillars. Refers to "the size and strength of the candle moving into the POI" — i.e., the strength of the move as price approaches/reacts at the POI, analogous to the volume-switch concept used throughout the POI catalog (small candles → big candle = strong volume switch). *(Section: "The Pillars of BTMM Strategy.")*

**Evidence sourcing (Volume and Momentum Proxy Standard Version 1, resolves Ambiguity 3):** Since retail Forex data carries no true exchange volume, this pillar's **primary evidence** is price/candle-behaviour measurements — Relative Size Ratio, Range Context Ratio, Body Efficiency, and Bullish/Bearish Close Position, per `knowledge/MEASUREMENT_STANDARDS.md`, "Volume, Momentum, and Price-Activity Proxy Standard." Tick volume, where available, is **secondary** evidence only (reported as SUPPORTS/NEUTRAL/CONTRADICTS/MISSING) and is never mandatory — missing tick volume must not invalidate a POI or a BTMM setup. External momentum indicators (RSI, MACD, Stochastic, ADX, Rate of Change, etc.) are excluded from the core project as mandatory rules. **The final pass/fail threshold for the BTMM Volume pillar is not yet defined** — none of the individual measurement fields have a minimum value set, and no combined `price_activity_score` exists yet. This remains an open decision, distinct from (but related to) Ambiguity 14, the BTMM forming/confirmed/cancelled state machine.

## Speed

One of the three BTMM pillars. Refers to "how fast price moves into the POI after manipulation" — i.e., how quickly price returns to/reacts at the POI once the liquidity-creation phase (early entries, delay, or overshoot) has run its course. *(Section: "The Pillars of BTMM Strategy.")*

**Evidence sourcing (Market Speed and Displacement Standard Version 1 — Provisional, resolves Ambiguity 7):** The book's single "Speed" pillar is split into two separately-tracked measurements that must never be merged into one score: **BTMM Approach Speed** (how fast price moved toward the POI during the approach leg, before/during manipulation) and **BTMM Reaction Speed** (how fast price moved away from the POI during the reaction leg, after manipulation). Both use the same movement-leg formulas: Leg Bar Count, Net Directional Distance (`|End Price − Start Price|`), Reference ATR (median ATR(14) across the leg), Normalized Speed Per Bar (`Net Directional Distance ÷ (Leg Bar Count × Reference ATR)`), Leg Path Distance (sum of candle Total Ranges in the leg), Directional Efficiency (`Net Directional Distance ÷ Leg Path Distance`), and Directional Candle Share (fraction of candles closing in the movement direction). A leg is classified FAST when Normalized Speed Per Bar ≥0.50, Directional Efficiency ≥0.60, and Directional Candle Share ≥0.67 (all three); STRONG FAST at ≥0.75/≥0.75/≥0.80; otherwise SLOW_OR_UNCLEAR. Full formulas in `knowledge/MEASUREMENT_STANDARDS.md`, "Market Speed, FVG Displacement, BTMM Movement, and POI Dwell Standard."

**POI Dwell Time is a separate concept from both Approach and Reaction Speed.** It measures how long price remains inside a POI zone (POI Dwell Bars = consecutive confirmed candles intersecting the POI from first touch to exit, plus First Touch Time, Exit Time, Dwell Duration, and Exit Direction as separate fields). No maximum permitted dwell time is set. Consistent with the book's own "Liquidity Inside a POI — Delay" concept above, **a delayed reaction inside a POI (long dwell) must not automatically invalidate BTMM** — dwell may later be interpreted using liquidity-generation and BTMM-state rules that are not yet defined.

**Anchors remain unresolved.** Automatic detection of the manipulation endpoint, approach starting price, POI first-touch price, reaction starting point, and reaction endpoint all depend on Ambiguity 14 (the BTMM forming/confirmed/cancelled state machine), which this decision does **not** resolve or modify. Until Ambiguity 14 is resolved, BTMM Approach/Reaction Speed can only be measured using expert-labelled or otherwise explicitly approved movement-leg anchors — no automatic anchor-detection algorithm has been invented.

**No final BTMM speed pass threshold may independently validate a complete BTMM formation.** FAST/STRONG FAST/SLOW_OR_UNCLEAR is one input signal only; it must never, by itself, approve or reject a POI, a BTMM formation, an entry, or a trade. No BTMM state machine (Ambiguity 14) has been created by this decision.

## Accuracy

One of the three BTMM pillars. Refers to "how precisely that candle reaches or targets the Point of Interest" — i.e., whether the reaction candle actually hits/respects the drawn POI zone rather than reacting from an unrelated price level. *(Section: "The Pillars of BTMM Strategy.")*

No numeric thresholds are given for any of the three pillars (e.g., no candles-per-minute speed threshold, no minimum volume multiple beyond what's already specified per-POI-type, no maximum distance for "accurate" targeting). See ambiguity register.

## M15 Role

Explicitly named as one of the three timeframes for observing "BTMM formation, creation, and execution," alongside M5 and M1. M5/M15 are described as helping "confirm the formation." *(Section: "A Must Recommendation for a Perfect Working BTMM Strategy.")*

## M5 Role

Same as M15 — one of the two timeframes (with M15) the author says can "help confirm the formation" of a BTMM setup.

## M1 Role

Explicitly described as usable "for precise execution" — the entry-timing timeframe, once M5/M15 have confirmed the formation.

## Conditions Showing BTMM Is Forming

The book does not present a single itemized "forming" checklist under that exact heading. Synthesizing only from what is explicitly stated elsewhere in the same section (not inventing new criteria):
- Price has reached a validated POI (per `knowledge/POI_MASTER_CATALOG.md`).
- One or more of the three liquidity-creation behaviors is underway: early buy/sell before the POI, a delay inside the POI, or an overshoot beyond the POI.
- The setup is still being watched for volume, speed, and accuracy — none of the three pillars has yet confirmed.

## Conditions Showing BTMM Is Confirmed

Again, no single itemized "confirmed" checklist exists verbatim in the book. Based only on explicit statements: a BTMM setup is treated as ready for execution when the trader can clearly identify (1) liquidity creation around the POI (before, within, or after it), (2) the market's overall direction/trend agreeing with the trade direction, (3) volume, speed, and accuracy all present as price reacts at the POI, and (4) the trader is in the correct session with sufficient volume/volatility for the asset. *(Section: "A Must Recommendation for a Perfect Working BTMM Strategy.")*

## Conditions Showing the Setup Is Cancelled

The book does not define explicit cancellation/invalidation criteria for a BTMM setup (consistent with the absent "false/genuine invalidation" concept above). The only explicit negative condition stated is: **"if none of these liquidity creation conditions is present, then the trade should not be taken."** No other cancellation rule (e.g., a maximum time-in-POI, a maximum overshoot distance, or a structural break that cancels the setup) is given. This is a confirmed gap requiring author input — see [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md).

## Required Supporting Conditions (also stated as mandatory in the book)

The book's closing recommendation ("A Must Recommendation for a Perfect Working BTMM Strategy") states BTMM only works when combined with:
1. Trading in the direction of market trend (BTMM is not primarily counter-trend).
2. Trading within the right session and on assets with real volume/volatility/liquidity.
3. Using BTMM inside a proper analytical framework (market structure, support/resistance, trendline analysis, etc.) — never standalone.
4. Respecting risk management (lot size, stop loss, risk-to-reward, account protection) regardless of how good the BTMM setup looks.
5. Respecting the M1/M5/M15 timeframe roles described above.
6. Confirming liquidity creation (before/within/after the POI) before executing.
