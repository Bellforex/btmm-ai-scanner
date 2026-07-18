# Project State — Phase 0A / Phase 0B Completion Report

## 1. Files Created

Folders:
- `docs/`
- `knowledge/`
- `knowledge/poi_rules/` (created empty — reserved for Phase 0B; the book's POI rules currently live in one consolidated file, `knowledge/POI_MASTER_CATALOG.md`, since the book itself does not split POI rules into separate per-POI documents)
- `knowledge/btmm/`
- `knowledge/trend/` (created empty — the book does not contain a dedicated trend-confirmation methodology chapter; see §5 below)
- `knowledge/market_structure/` (created empty — the book does not contain a dedicated market-structure-mapping chapter beyond the swing-high/low and trend-vs-consolidation notes already captured in `knowledge/POI_MASTER_CATALOG.md` and `knowledge/btmm/BTMM_MASTER_SUMMARY.md`; see §5 below)

Files:
- `docs/PROJECT_SCOPE.md` — vision, markets, timeframe roles, TradingView/FXCM reference, data hierarchy, no-live-trading rule, validity-separation rule.
- `knowledge/POI_MASTER_CATALOG.md` — every POI taught in the book, under Volume-Based / Price Action / Structural, with all required fields.
- `knowledge/btmm/BTMM_MASTER_SUMMARY.md` — full BTMM concept extraction against the required outline, explicitly marking what the book does and does not define.
- `knowledge/SOURCE_INDEX.md` — section-by-section index of every rule/POI/BTMM concept, with image-presence notes and destination-file mapping.
- `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md` — 15 registered ambiguities, each with the book quote, why it can't be coded yet, and candidate numeric measurements. Ambiguity 1 is now marked ✅ RESOLVED (see below); the remaining 14 are still open.
- `knowledge/MEASUREMENT_STANDARDS.md` — **new.** Holds implementation-ready measurement definitions once an ambiguity is resolved. Currently contains one approved standard: "Candle Size, Body, Wick, and Range Measurements" (Candle Measurement Standard Version 1).
- `docs/PROJECT_STATE.md` — this file.

The private source book (`references/private/BTMM_AND_POI_TRADING_BIBLE.docx`) was read-only for this task: it was not modified, moved, or deleted, and remains excluded from git via the pre-existing `.gitignore` entry `references/private/*`.

## 2. All POIs Found (13 catalog entries, 3 categories)

**Volume-Based POI:** Order Block; Fair Value Gap; Buy-to-Sell/Sell-to-Buy Candle; Rally-Base-Rally/Drop-Base-Drop; Pressure Wick (Liquidity Wick).

**Price Action POI:** Bullish/Bearish Engulfing Candle; Hammer/Shooting Star; Morning Star/Evening Star.

**Structural POI:** Trendline; Support/Resistance; Equal Highs/Equal Lows; Swing Highs/Swing Lows; Previous/Current Day-Week-Month High-Low (12 named variants of one family).

Full detail in `knowledge/POI_MASTER_CATALOG.md`.

## 3. Rules Ready for Coding (precise, numeric, book-sourced)

- Order Block: 2-candle structure, displacement candle ≥2×/3× the smaller candle, located at origin of a move, zone = smaller candle's range.
- Fair Value Gap: 3-candle gap geometry (Buy: 3rd-candle-low > 1st-candle-high; Sell: 3rd-candle-high < 1st-candle-low).
- Engulfing Pattern: 2-candle structure, ≥2×/3× ratio, body-covers-body rule, explicit "middle of a move" location rule (vs. Order Block's "origin" rule), timeframe strength ranking.
- Buy-to-Sell/Sell-to-Buy Candle: ≥2×/3× ratio vs. average of preceding candles, explicit fail-then-reverse logic, full-candle-range zone.
- Base Rally/Base Drop: Base High/Base Low formula, departure candle ≥2×/3× the largest base candle, plus (provisional) 2–6 candle count, Base Height, midpoint drift, and overlap-ratio rules from Base Formation Standard V1 — Provisional.
- Morning Star/Evening Star: 3-candle structure, final candle ≥2–3× the middle doji.
- Previous/Current Period High-Low levels (12 variants): pure price-extreme detection over defined calendar windows, explicit timeframe strength ranking (month > week > day).
- Trendline: "at least two touches" confirmation rule (partially precise — steepness and swing quality remain open, see ambiguity register).
- BTMM: the 3-pillar model (Volume/Speed/Accuracy) and the core liquidity mechanic ("close buy = sell liquidity," "close sell = buy liquidity") are structurally precise even though their numeric thresholds are not yet set.

## 4. Rules Requiring Author Clarification (see `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md` for full detail)

**Candle Measurement Standard Version 1 — Approved.** The author has resolved Ambiguity 1 (candle-size measurement method). The approved standard: candle size = total high-to-low range; Size Ratio = key candle range ÷ reference candle range; classification is <2.0 = fails size requirement, 2.0–<3.0 = valid/standard, ≥3.0 = strong. Candle body and body efficiency are tracked separately and do not replace this rule; wicks stay inside the range measurement; ATR is reserved for later cross-symbol/timeframe normalization only, not for replacing the 2×/3× rule. Full formulas and POI-by-POI application are in `knowledge/MEASUREMENT_STANDARDS.md`.

**Small Candle Standard Version 1 — Approved (Phase 0C).** The author has resolved Ambiguity 2 ("small candle" baseline). Approved standard: a candle is small relative to a key candle when its Total Range ≤ 0.50× the key candle's Total Range (standard), or ≤ 0.3333× (strong volume-switch) — the same 2×/3× relationship as Candle Measurement Standard V1, expressed from the small candle's side. A separate, secondary "Recent Market Context" classification (Contextually Small/Normal/Large vs. the median Total Range of the previous 20 confirmed candles) is tracked independently and must never override the relative-size rule. No fixed pip/point floors are used, so the rule holds across XAUUSD/EURUSD/GBPUSD and all timeframes. Applies specifically to Order Block, Engulfing, Fair Value Gap, Base Rally/Drop, and Buy-to-Sell/Sell-to-Buy (10 rule files updated with a reference — see `knowledge/MEASUREMENT_STANDARDS.md`, "Small Candle and Recent Market Context Standard"). Still open: comparison-group candle count, valid base candle count/duration, and Buy-to-Sell/Sell-to-Buy reversal-confirmation distance (Ambiguity 13) — none of these were resolved by this decision. Pressure Wick, Hammer, Shooting Star, Morning Star, and Evening Star are not covered by this standard and remain unchanged.

**Volume and Momentum Proxy Standard Version 1 — Approved.** The author has resolved Ambiguity 3 (volume/momentum proxy choice). Approved standard: volume/momentum/pressure/activity-switch is read primarily from price/candle behaviour — five separate, non-combined fields: Relative Size Ratio (reuses the existing candle-size standards), Range Context Ratio (candle range vs. the 20-candle median), Body Efficiency, Bullish Close Position, and Bearish Close Position. Tick volume, where available, is secondary-only (SUPPORTS/NEUTRAL/CONTRADICTS/MISSING status; never mandatory; missing data never invalidates a POI; never merged across providers). External indicators (RSI, MACD, Stochastic, ADX, Rate of Change, etc.) are excluded from the core project as mandatory rules — optional research-only, subject to locked-unseen-data validation and author approval. Full formulas are in `knowledge/MEASUREMENT_STANDARDS.md`, "Volume, Momentum, and Price-Activity Proxy Standard." Applies to Buy/Sell Order Block, Buy/Sell Fair Value Gap, Base Rally, Base Drop, Buy-to-Sell/Sell-to-Buy Candle, and Bullish/Bearish Engulfing (10 rule files referenced); does **not** apply to Pressure Wick (remains under Ambiguity 6). `knowledge/btmm/BTMM_MASTER_SUMMARY.md`'s Volume pillar now documents this sourcing. Still open: minimum Body Efficiency, minimum Close Position, minimum Relative Tick Volume, minimum displacement distance, the final `price_activity_score` formula/weights, and any hard pass/fail threshold — none of these were set by this decision.

**Base Formation Standard Version 1 — Provisional — Approved.** The author has resolved Ambiguity 4 (base-candle compactness/count), explicitly as a **provisional** standard pending future calibration. Approved standard: a valid base is 2–6 consecutive confirmed closed candles (more than 6 = consolidation, not a precise Base Rally/Drop POI); every base candle's Total Range ≤ 0.50× the departure candle's (≤ 0.3333× for Strong Base), compared against the largest base candle; Base Height (`Highest High − Lowest Low` of all base candles) ≤ 0.75× ATR(14) **and** ≤ 0.60× the departure candle's Total Range; Base Midpoint Drift ≤ 0.25× Base Height (rejects directional staircases); consecutive-candle Overlap Ratio ≥ 0.50; the departure candle must be ≥2× (≥3× for Strong) the largest base candle, close outside the complete base range in the expected direction, and is evaluated via the Volume/Momentum/Price-Activity Proxy Standard. Classifies as COMPACT BASE / STRONG BASE / INVALID BASE. Full formulas in `knowledge/MEASUREMENT_STANDARDS.md`, "Base Formation, Compactness, and Departure Standard." Scope: Base Rally/Base Drop only — not extended to consolidation, accumulation, distribution, support, resistance, or other POIs. This standard **remains provisional** and requires future calibration against expert-approved/rejected examples across XAUUSD/EURUSD/GBPUSD, H3/H4/D1/W1, and different volatility regimes before being finalized. Base Rally and Base Drop rule files and coverage-matrix rows updated accordingly; neither POI is marked APPROVED — freshness, mitigation, invalidation, and expiration remain undefined for both.

11 registered ambiguities remain open, most importantly:
1. ~~Candle-size measurement method~~ — **Resolved**, see above.
2. ~~"Small candle" baseline~~ — **Resolved**, see above.
3. ~~Volume/momentum proxy choice~~ — **Resolved**, see above.
4. ~~Base-candle compactness thresholds (Rally/Drop)~~ — **Resolved (provisional)**, see above.
5. Equal-highs/equal-lows equality tolerance.
6. Pressure/liquidity wick wick-to-body proportion.
7. BTMM "Speed" — no time/candle-count threshold.
8. BTMM "Accuracy" — no max overshoot-from-POI threshold.
9. "Strong reaction" minimum-move definition (previous/current highs-lows, support/resistance).
10. Swing-high/low detection rule (fractal window or retracement %) — currently undefined, blocks market-structure mapping.
11. Trendline steepness threshold.
12. Support/Resistance touch-count and tolerance band.
13. "Clear reversal" distance for Buy-to-Sell/Sell-to-Buy candles.
14. **BTMM forming/confirmed/cancelled state machine** — the single highest-priority gap, since every other threshold feeds into it.
15. Whether to adopt "reclaim," "displacement after reclaim," "repeated taps," and "false/genuine invalidation" as project vocabulary at all — none of these appear in the book.

## 5. Contradictions Found

- **FVG naming inconsistency:** The book's front-matter abbreviation list defines "1. Bear Value Gap = BFVG," but the body of the book never uses "Bear Value Gap" or "BFVG" again — it consistently calls the concept "Fair Value Gap" / "FVG" for both bullish and bearish variants (Buy FVG / Sell FVG). This looks like a typo or leftover draft abbreviation rather than a deliberate second concept. Flagged for author confirmation: should "BFVG" be retired, or does the author intend a distinct "Bear Value Gap" concept that was never written out?
- **Pillar ordering:** The BTMM pillars are listed as "volume, accuracy, and speed" in the strategy definition but as "volume, speed, and accuracy" in "The Pillars of BTMM Strategy" section. This is very likely stylistic (same three pillars, no ordering significance implied), not a substantive contradiction, but is noted for completeness.

## 6. Missing Definitions

- No dedicated trend-confirmation methodology in the book (the book assumes the trader already knows technical/fundamental analysis and market sessions — it explicitly says so in the Introduction). `knowledge/trend/` was created per Task 1 but left empty; a trend-confirmation ruleset will need either author-supplied material or a separate scoping conversation before Phase 0B.
- No dedicated market-structure-mapping methodology beyond the swing-high/low and trend-vs-consolidation notes already folded into `knowledge/POI_MASTER_CATALOG.md` §3.4 and `knowledge/btmm/BTMM_MASTER_SUMMARY.md`. `knowledge/market_structure/` was created per Task 1 but left empty for the same reason.
- No formal BTMM state machine (see ambiguity #14).
- No definitions for "reclaim," "displacement after reclaim," "repeated taps," "false invalidation," or "genuine invalidation" anywhere in the book (see ambiguity #15).
- No economic-news/fundamental-analysis ruleset (explicitly deferred to a later phase per the project vision — not a gap in the book, just out of current scope).

## 7. Confirmation: No Scanner or Bot Code Was Created (Phase 0A)

Phase 0A produced only Markdown knowledge/documentation files under `docs/` and `knowledge/`, plus the folder structure. No scanner, indicator, Pine Script, AI/ML model, database, website, API, backtest engine, TradingView connection, Telegram integration, or MT4/MT5 execution code was written, and none of the private book's content was modified, copied into a public location, or committed to version control. Phase 0A ended there; no further phases were started at that time.

---

## 8. Phase 0B — Coverage Audit (Completed)

Phase 0B re-read the complete private source book to verify the Phase 0A POI inventory against an explicit, expanded checklist, and produced a formal coverage matrix, per-POI rule files, a market-analysis coverage matrix, and a knowledge-completion gate. The Candle Measurement Standard approved in Ambiguity 1 was **not** modified during this audit.

### 8.1 Files Created in Phase 0B

- `knowledge/POI_COVERAGE_MATRIX.md` — one row per verified POI (36 rows) across 25 audit columns (definition, location, formation, confirmation, boundary, candle-size, wick/body, trend, market-structure, liquidity, timeframe, strength, freshness, partial/full mitigation, invalidation, expiration, positive/negative example, machine-testable-now, author-clarification-required, status).
- `knowledge/poi_rules/volume_based/` — 10 rule files (Buy/Sell Order Block, Buy/Sell Fair Value Gap, Buy-to-Sell/Sell-to-Buy Candle, Base Rally, Base Drop, Bullish/Bearish Pressure Wick).
- `knowledge/poi_rules/price_action/` — 6 rule files (Bullish/Bearish Engulfing, Hammer, Shooting Star, Morning Star, Evening Star).
- `knowledge/poi_rules/structural/` — 20 rule files (Bullish/Bearish Trendline, Support, Resistance, Equal Highs, Equal Lows, Swing High, Swing Low, and the 12 Previous/Current Day-Week-Month High-Low variants).
- `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md` — 22 trend/structure/liquidity concepts checked against the book, none fully defined, Break of Structure and Change of Character explicitly **not** adopted as project rules.
- `knowledge/KNOWLEDGE_COMPLETION_GATE.md` — the 8-condition gate; current status: **CLOSED** (only condition 1, rule-file existence, is met).
- `docs/PROJECT_STATE.md` — this section.

### 8.2 Total POIs Verified

**36 POIs** verified against the book (10 Volume-Based + 6 Price Action + 20 Structural, where the 20 Structural rows include the 12 Previous/Current Day-Week-Month High-Low variants as one family). This is a finer-grained count than Phase 0A's "13 catalog entries" because Phase 0B counts each bullish/bearish or buy/sell direction as its own row/file, per the audit brief's own checklist structure. No POI outside the Phase 0A inventory was found; no concept was added that isn't explicitly in the book.

**Naming differences / duplicates recorded during re-verification:**
- "Hammer" and "Pin Bar" are the same POI — the book states "the Hammer or Pin Bar" directly. Filed as one rule file (`hammer.md`), not two.
- The task brief's "Current Day/Week/Month High/Low" corresponds to the book's own "High/Low of the Day/Week/Month" — same concept, different word order. Recorded in each of the six affected rule files' "Alternative book name" field.
- "Rally-Base-Rally"/"Drop-Base-Drop" (used in the book's intro chapter) vs. "Base Rally"/"Base Drop" (used in the book's own formal validation appendix) — same POI, two labels within the same book.
- A likely typo in the book's own intro summary list: "drop base trop" instead of "drop base drop" (paragraph 174).
- "Buy Order Block"/"Sell Order Block" (formal appendix term) vs. informal "bullish/bearish order block" (used once in narrative prose) — same concept.
- The FVG naming inconsistency already logged in section 5 above ("Bear Value Gap = BFVG") continues to apply to both Buy and Sell Fair Value Gap.

### 8.3 Status Breakdown (from `knowledge/POI_COVERAGE_MATRIX.md`)

- **PARTIAL: 20 of 36 POIs** — core detection/boundary geometry is book-defined and precise (helped by the now-approved Candle Measurement Standard), but lifecycle rules (freshness, partial/full mitigation, invalidation, expiration) are undefined for all of them.
- **NEEDS AUTHOR DECISION: 16 of 36 POIs** — blocked by an open core-detection ambiguity (e.g., Pressure Wick/Hammer/Shooting Star wick:body ratio, Trendline steepness/swing detection, Support/Resistance/Equal-Highs-Lows/Swing-High-Low tolerance and detection rules, Buy-to-Sell/Sell-to-Buy reversal-distance, Base Rally/Drop compactness).
- **APPROVED: 0 of 36** — no POI has all mandatory rules complete and author-approved; every single POI is missing at least a freshness, mitigation, or expiration rule, none of which the book defines for any POI.
- **Machine-testable now:** 24 of 36 Partial (detection formula testable, lifecycle not), 12 of 36 No (core detection rule itself still open).

### 8.4 Missing Market-Analysis Rules (from `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`)

Of the 22 audited trend/market-structure/liquidity concepts (bullish/bearish trend, consolidation, higher high/low, lower high/low, swing detection, pullback, continuation, trend reversal, Break of Structure, Change of Character, trendline construction/touches/invalidation, support, resistance, break and retest, liquidity sweep, higher-timeframe alignment, lower-timeframe confirmation): **zero have a full numeric definition in the book.** "Higher high," "higher low," "lower high," "lower low," and "Change of Character" do not appear anywhere in the book at all; "Break of Structure" appears exactly once, in a single unexplained list, and per explicit instruction is **not** being adopted as an official project rule absent author approval. All 22 concepts require author-supplied methodology before they can be coded.

### 8.5 Confirmation: No Scanner or Bot Code Was Created (Phase 0B)

Phase 0B produced only Markdown documentation (a coverage matrix, 36 per-POI rule files, a market-analysis matrix, and a knowledge-completion gate document) plus the three `knowledge/poi_rules/` subfolders. No scanner, indicator, Pine Script, AI/ML model, database, website, API, backtest engine, TradingView connection, Telegram integration, or MT4/MT5 execution code was written. The previously approved Candle Measurement Standard Version 1 was not modified. No other ambiguity was resolved during this audit — all resolution work remains pending author decision. Per `knowledge/KNOWLEDGE_COMPLETION_GATE.md`, scanner coding remains blocked until all 8 gate conditions are met.
