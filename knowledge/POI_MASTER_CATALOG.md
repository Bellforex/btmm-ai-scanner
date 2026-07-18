# POI Master Catalog

Source: `references/private/BTMM_AND_POI_TRADING_BIBLE.docx` (English/French bilingual book by Ronny Rostand). This catalog lists **only** POIs explicitly taught in the book. No ICT/SMC/generic definitions have been substituted or added.

**Note on location references:** The source `.docx` contains no embedded page-number metadata (Word computes pagination at print/render time, and no PDF/page-accurate renderer — LibreOffice/pandoc — was available in this environment). Locations below are given as **book section** (chapter/heading, matching the book's own structure) plus a paragraph reference number into the plain-text working extraction described in [SOURCE_INDEX.md](SOURCE_INDEX.md). If the author can supply a paginated PDF/print copy later, these can be upgraded to exact page numbers.

The book defines three official POI categories (Chapter 1, "The Three Main Types of POI in This Book"): **Volume-Based POI**, **Price Action POI**, **Structural POI**.

**Project-wide note — POI Zone Interaction Standard (resolves Ambiguity 8, provisional):** Any POI with clearly defined upper and lower zone boundaries (Zone Top and Zone Bottom, giving `Zone Height = Zone Top − Zone Bottom > 0`) must use the approved **POI Zone Interaction, Penetration, and Overshoot Standard Version 1 — Provisional** — see `knowledge/MEASUREMENT_STANDARDS.md`, "POI Zone Interaction, Penetration, and Overshoot Standard" — for measuring how price touches, penetrates, and overshoots that zone (EDGE_TOUCH / PARTIAL_ENTRY / DEEP_ENTRY / FAR_BOUNDARY_TOUCH / CONTROLLED_OVERSHOOT / EXCESSIVE_OVERSHOOT, plus NEAR_MISS / NO_CONTACT / NONCANONICAL_SIDE_INTERACTION). A few important limits on what this standard does:

- It measures **interaction geometry only** — how the candle's wick and close relate to the zone boundaries. It does **not** independently determine reaction strength, BTMM validity, entry validity, freshness, mitigation, or final invalidation; those remain separate, unresolved decisions.
- **Support, Resistance, and Trendlines retain their own, separate tolerance rules** (still open under Ambiguities 11 and 12) and do not automatically inherit this standard.
- POIs without a valid, clearly defined zone (Zone Height ≤ 0, or no upper/lower boundary at all — e.g. the twelve Previous/Current Period High-Low levels, which are single price points rather than zones) cannot use these penetration formulas.
- This note does **not** redefine any individual POI's own boundary formula recorded in its catalog entry below or in its `knowledge/poi_rules/` file — it only adds a shared, common way to measure interactions with whatever boundary each POI already has. No individual POI rule file was modified when this note was added; that per-POI application happens later during the full individual POI specification phase.

---

## Category 1 — Volume-Based POI

### 1.1 Order Block (OB)

- **English name:** Order Block
- **French name:** Order block / Bloc d'ordres
- **Category:** Volume-Based POI
- **Bullish version:** Buy Order Block — forms at the origin of a bullish move
- **Bearish version:** Sell Order Block — forms at the origin of a bearish move
- **Short definition:** A two-candle pattern found at the end/origin of a prior move, right before the market reverses or displaces strongly in a new direction. The first (small) candle is the actual OB zone; the second (large) candle shows the volume switch that powers the new move.
- **Main validation condition:**
  - Two-candle structure: smaller candle followed by a larger displacement candle.
  - Displacement candle size ≥ 2× the smaller candle (stronger ≥ 3×).
  - Located at the **beginning/origin** of a significant impulsive move (not in the middle of one — this is what distinguishes it from an engulfing pattern).
  - Drawn zone = full high-to-low range of the smaller candle.
- **Recommended timeframe:** No single timeframe mandated for validity, but strength is explicitly ranked: Weekly OB > Daily OB > 4H OB > 1H OB > 15-min OB. Fits the book's "Strong POI analysis" role (H3/H4/D1/W1).
- **Section:** Chapter 1 → Volume-Based POI → "Order blocks (OB)" (¶199–237) and the later formal appendix "Order Block Validation Conditions" (¶829–939).
- **Precise enough for coding:** Yes — explicit numeric ratio (≥2×, ≥3×) and explicit location rule (origin vs. middle).
- **Author clarification needed:** Minor — "size" is not defined as body-only, wick-to-wick range, or a specific price-difference formula (see ambiguity register: "candle size measurement").

### 1.2 Fair Value Gap (FVG)

- **English name:** Fair Value Gap
- **French name:** Déséquilibre de juste valeur
- **Category:** Volume-Based POI
- **Bullish version:** Buy Fair Value Gap
- **Bearish version:** Sell Fair Value Gap (book's front-matter abbreviation list labels this "Bear Value Gap = BFVG" — see contradiction note in [PROJECT_STATE.md](../docs/PROJECT_STATE.md))
- **Short definition:** A three-candle price imbalance created when the market moves too fast in one direction, leaving an empty/inefficient zone between the first and third candle. Price may later return to rebalance the gap.
- **Main validation condition:**
  - Candles preceding the gap must show clear directional displacement (not choppy/sideways).
  - Preceding candles must be noticeably smaller than the middle (displacement) candle.
  - Middle candle: strong, aggressive bullish (buy) or bearish (sell) displacement.
  - Candle following the displacement candle can be any size — does not invalidate the gap.
  - **Buy FVG zone:** low of 3rd candle > high of 1st candle → zone = 1st-candle-high to 3rd-candle-low.
  - **Sell FVG zone:** high of 3rd candle < low of 1st candle → zone = 3rd-candle-high to 1st-candle-low.
  - Best-quality FVGs form after a run of small (weak-volume) candles, immediately followed by the big displacement candle (book's "Scenario A" vs. weaker "Scenario B").
- **Recommended timeframe:** Not fixed to one timeframe; strength scales with timeframe like other volume-based POIs.
- **Section:** Chapter 1 → Volume-Based POI → "2. Fair Value Gap" (¶238–287), formal appendix "Buy/Sell Fair Value Gap Validation Conditions" (¶688–730). Related abbreviations: PCH/PCL (previous/first candle high-low), NCH/NCL (next/third candle high-low) — front matter (¶52–58).
- **Precise enough for coding:** Yes — the three-candle gap condition is a strict, numeric price relationship.
- **Author clarification needed:** "Noticeably smaller" / "clear directional displacement" for the preceding candles is not given a numeric ratio (unlike the 2×/3× rule used for OB/engulfing/base patterns). See ambiguity register.

### 1.3 Buy-to-Sell Candle / Sell-to-Buy Candle

- **English name:** Buy-to-Sell Candle (bearish reversal) / Sell-to-Buy Candle (bullish reversal)
- **French name:** Chandelier achat vers vente / Chandelier vente vers achat
- **Category:** Volume-Based POI
- **Bullish version:** Sell-to-Buy candle (a failed strong bearish candle that reverses upward)
- **Bearish version:** Buy-to-Sell candle (a failed strong bullish candle that reverses downward)
- **Short definition:** A strong, high-volume candle in the direction of the existing move that looks like continuation but is immediately followed by a reversal in the opposite direction — a trap/institutional-reaction candle that becomes a POI because price may revisit it.
- **Main validation condition:**
  - Must appear within an existing directional move (uptrend for Buy-to-Sell; downtrend for Sell-to-Buy).
  - Candle ≥ 2× the average size of preceding candles (stronger ≥ 3×).
  - Original direction must **fail to continue**, followed by a clear reversal in the opposite direction.
  - Zone = full high-to-low range of the failed candle.
- **Recommended timeframe:** Strength scales with timeframe (Weekly > Daily > 4H > 1H > 15-min), same ranking pattern as other volume-based POIs.
- **Section:** Chapter 1 → Volume-Based POI → "3. Buy-to-sell zones/Sell-to-buy zones" (¶288–341), formal appendix "Buy-to-Sell and Sell-to-Buy Candle Validation Conditions" (¶1054–1161).
- **Precise enough for coding:** Yes — explicit ratio and explicit two-part logic (strong candle + failed continuation + reversal).
- **Author clarification needed:** How much opposite movement counts as "a clear reversal" (no minimum distance/close condition given).

### 1.4 Rally-Base-Rally (Base Rally) / Drop-Base-Drop (Base Drop)

- **English name:** Rally-Base-Rally (bullish) / Drop-Base-Drop (bearish); the pause itself is called "the base"
- **French name:** Hausse-base-hausse / Baisse-base-baisse
- **Category:** Volume-Based POI
- **Bullish version:** Base Rally (base breaks out upward)
- **Bearish version:** Base Drop (base breaks out downward)
- **Short definition:** Price makes a strong directional move, pauses in a small horizontal "base" of overlapping candles (temporary balance/low activity), then breaks out again strongly in the same direction. The base itself is the POI.
- **Main validation condition:**
  - Base = 2+ candles, short, small range, positioned close together, relatively uniform, horizontally aligned (not forming a staircase).
  - Base Zone = Base Low (lowest low of all base candles) to Base High (highest high of all base candles).
  - Departure (breakout) candle must be bullish (Base Rally) or bearish (Base Drop) and larger than **every** individual base candle.
  - Departure candle ≥ 2× the largest base candle (stronger ≥ 3×).
  - Departure must be decisive — weak/hesitant separation from the base does not qualify as a "perfect" base.
- **Recommended timeframe:** Strength scales with timeframe: Weekly base > Daily base > 4H base > 1H base > 15-min base.
- **Section:** Chapter 1 → Volume-Based POI → "4. Rally base rally / Drop base drop" (¶342–358), formal appendix "Base Drop and Base Rally POI Validation Conditions" (¶942–1053). Abbreviations BH/BL defined in front matter (¶54–56).
- **Precise enough for coding:** Yes — numeric departure-candle ratio and an explicit Base High/Low formula.
- **Author clarification needed:** "Short," "small," "relatively uniform," and "close together" for base candles have no numeric thresholds (e.g., max range as a % of ATR). See ambiguity register.

### 1.5 Pressure Wick / Liquidity Wick

- **English name:** Pressure Wick (also called Liquidity Wick)
- **French name:** Mèche de pression / Mèche de liquidité
- **Category:** Volume-Based POI
- **Bullish version:** Bullish liquidity wick → acts as a future buying zone
- **Bearish version:** Bearish liquidity wick → acts as a future selling zone
- **Short definition:** A strong rejection wick (on a bullish or bearish candle) formed when price pushes into a zone, collects liquidity, and is strongly rejected — but the candle still closes with a meaningful body (not just a long wick), showing genuine two-sided participation.
- **Main validation condition:**
  - Long rejection wick **plus** a body that "still has a good proportion" (i.e. not purely a wick with a negligible body).
  - Best identified on higher timeframes: 2H, 3H, 4H and above (book's own stated preference, based on author experience).
  - Execution approach: once price returns to a higher-timeframe wick, drop to a lower timeframe for confirmation/precise entry rather than entering blindly.
- **Recommended timeframe:** Explicitly stated: 2-hour, 3-hour, 4-hour and higher for identification; lower timeframe for entry timing.
- **Section:** Chapter 1 → Volume-Based POI → "5. Pressure wick" (¶359–373).
- **Precise enough for coding:** Partially — the rejection-wick requirement is directional and visual but "good body proportion" has no numeric wick:body ratio.
- **Author clarification needed:** Yes — needs a minimum wick-to-body or wick-to-range ratio. See ambiguity register ("good candle proportion").

---

## Category 2 — Price Action POI

### 2.1 Bullish Engulfing Candle / Bearish Engulfing Candle

- **English name:** Bullish Engulfing (Candlestick) Pattern / Bearish Engulfing (Candlestick) Pattern
- **French name:** Chandelier engulfing haussier / Chandelier engulfing baissier
- **Category:** Price Action POI
- **Bullish version:** Bullish engulfing (sell-to-buy reaction)
- **Bearish version:** Bearish engulfing (buy-to-sell reaction)
- **Short definition:** A two-candle reversal pattern where a larger candle's body fully covers (engulfs) the prior, smaller, opposite-colored candle's body, showing a change in control between buyers and sellers. Stronger when it appears at a meaningful location (support/resistance, POI, liquidity sweep, premium/discount zone, pullback) rather than randomly mid-chart.
- **Main validation condition:**
  - Previous candle relatively small; engulfing candle ≥ 2× previous candle (stronger ≥ 3×).
  - Engulfing candle's body covers/engulfs the previous candle's body (stronger version also engulfs the wicks).
  - Engulfing candle must close in its own direction (bullish closes above open; bearish closes below open).
  - **Location rule:** must appear within/in the middle of an existing price movement — this is the explicit distinction from an Order Block, which sits at the origin of a movement.
- **Recommended timeframe:** Strength scales with timeframe: Daily > 4H > 1H > 15-min (explicitly stated).
- **Section:** Chapter 1 → Price Action POI → "Bullish engulfing candle — Bearish engulfing candle" (¶413–474), formal appendix "Engulfing Pattern" / "Bearish Engulfing Pattern" / "Engulfing Pattern Strength Classification" (¶731–828).
- **Precise enough for coding:** Yes — explicit ratio, explicit close-direction rule, explicit location rule vs. Order Block.
- **Author clarification needed:** None beyond the general "candle size measurement" ambiguity shared with other patterns.

### 2.2 Hammer / Shooting Star

- **English name:** Hammer (a.k.a. Pin Bar) / Shooting Star
- **French name:** Marteau / Étoile filante
- **Category:** Price Action POI
- **Bullish version:** Hammer — appears at a support zone, signals possible buy rejection
- **Bearish version:** Shooting Star — appears at a resistance zone, signals possible sell rejection
- **Short definition:** Single-candle rejection patterns: Shooting Star = long upper wick + small body at resistance (sellers rejected an upward push); Hammer = long lower wick + small body at support (buyers rejected a downward push).
- **Main validation condition:**
  - Long wick (upper for Shooting Star, lower for Hammer) with a small body.
  - Candle close color changes the strength/next step: a Shooting Star closing bearish (red) is a stronger sell signal; closing bullish means wait for a bearish confirmation candle before selling. A Hammer closing bullish (green) is a stronger buy signal; closing bearish means wait for a bullish confirmation candle before buying.
- **Recommended timeframe:** Not explicitly stated for this pattern (contrast with Morning/Evening Star, where higher timeframes are explicitly recommended).
- **Section:** Chapter 1 → Price Action POI → "2. Hammer — Shooting star" (¶475–496).
- **Precise enough for coding:** Partially — the close-color logic is precise, but "long wick" and "small body" have no numeric ratio.
- **Author clarification needed:** Yes — needs a numeric wick-to-body ratio (see ambiguity register).

### 2.3 Morning Star / Evening Star

- **English name:** Morning Star / Evening Star
- **French name:** Étoile du matin / Étoile du soir
- **Category:** Price Action POI
- **Bullish version:** Morning Star — at demand/support, sellers → doji/indecision → strong buyers
- **Bearish version:** Evening Star — at supply/resistance, buyers → doji/indecision → strong sellers
- **Short definition:** Three-candle reversal pattern: a strong candle in the prior direction, a small/doji indecision candle, then a strong candle in the new direction, showing a full volume switch.
- **Main validation condition:**
  - Candle 1: strong candle in the prior direction (bearish for Morning Star, bullish for Evening Star).
  - Candle 2: small candle or doji (loss of momentum / indecision).
  - Candle 3: strong candle in the new direction, ideally ≥ 2–3× the size of the middle doji candle.
- **Recommended timeframe:** Explicitly recommended on higher timeframes: 2H, 3H, 4H and above, for stronger rejection/institutional signal.
- **Section:** Chapter 1 → Price Action POI → "2. Morning star — Evening star" (¶497–523).
- **Precise enough for coding:** Yes for the 3-candle structure and the ≥2–3× ratio on the final candle.
- **Author clarification needed:** "Small candle or doji" for candle 2 has no numeric body-size threshold.

---

## Category 3 — Structural POI

### 3.1 Trendline

- **English name:** Trendline
- **French name:** Ligne de tendance
- **Category:** Structural POI
- **Bullish version:** Bullish (ascending) trendline → buying POI
- **Bearish version:** Bearish (descending) trendline → selling POI
- **Short definition:** A diagonal form of support/resistance confirmed by at least two touches; later touches (3rd/4th) can offer buy/sell opportunities. Classified as a structural POI because liquidity/attention accumulates around it.
- **Main validation condition:**
  - Requires at least two touches to be considered "confirmed."
  - Should not be "too steep" (no numeric angle given — see ambiguity register).
  - Should connect to "meaningful swing points" where price clearly reacted (no numeric swing-size threshold given).
- **Recommended timeframe:** Stronger/more reliable on higher/intraday timeframes, explicitly the 4-hour chart and above; timeframe choice should match trade type (scalp = lower TF trendline, day/swing trade = stronger TF trendline).
- **Section:** Chapter 1 → Structural POI → "Trendlines" (¶576–589).
- **Precise enough for coding:** Partially — the "at least two touches" rule is codable; "too steep" and "meaningful swing" are not quantified.
- **Author clarification needed:** Yes — needs a maximum slope/angle rule and a definition of a qualifying "touch." See ambiguity register ("trendline too steep").

### 3.2 Support Levels / Resistance Levels

- **English name:** Support Level / Resistance Level
- **French name:** Niveau de support / Niveau de résistance
- **Category:** Structural POI
- **Bullish version:** Support (buying opportunities, or break-and-retest-to-the-upside)
- **Bearish version:** Resistance (selling opportunities, or break-and-retest-to-the-downside)
- **Short definition:** Classic horizontal levels where price has reacted before. Used both for reversals and for break-and-retest continuation trades. Attract orders/stop-losses from both retail and institutional traders, creating liquidity around them.
- **Main validation condition:** Not formally quantified in the book beyond "a level where price has shown meaningful reaction before" — no explicit touch-count or price-tolerance rule (unlike trendlines, which get an explicit "at least two touches" rule).
- **Recommended timeframe:** Not explicitly stated for this specific POI (general higher-timeframe-is-stronger principle applies across the book).
- **Section:** Chapter 1 → Structural POI → "2. Support levels — Resistance levels" (¶590–602).
- **Precise enough for coding:** No — the concept itself (what counts as a valid support/resistance level, tolerance band, number of touches) is left implicit.
- **Author clarification needed:** Yes — needs a definition of level tolerance (price band width) and minimum touch count. See ambiguity register.

### 3.3 Equal Highs / Equal Lows

- **English name:** Equal Highs / Equal Lows
- **French name:** Plus hauts égaux / Plus bas égaux
- **Category:** Structural POI
- **Bullish version:** Equal lows (sell-side... actually buy-side liquidity rests below — see definition) — used as a bullish liquidity-grab trigger leading toward a bullish POI
- **Bearish version:** Equal highs — buy-side liquidity rests above; used as a bearish liquidity-grab trigger leading toward a bearish POI
- **Short definition:** Price levels where the market has reached "the same high area" or "the same low area" more than once. Buy-side liquidity is assumed above equal highs; sell-side liquidity is assumed below equal lows. The book explicitly recommends treating these as **entry triggers leading to another POI** (support, resistance, supply, demand, OB, FVG) rather than as direct entry zones themselves.
- **Main validation condition:**
  - Two or more touches at "the same" (i.e. near-equal, not necessarily identical) high or low.
  - Wait for the liquidity grab (a sweep beyond the level) first; only then look for confirmation at the main POI the sweep leads toward.
- **Recommended timeframe:** More reliable on higher timeframes (stronger liquidity).
- **Section:** Chapter 1 → Structural POI → "3. Equal highs — Equal lows" (¶603–617).
- **Precise enough for coding:** No — "same" / "near-equal" has no explicit price tolerance (pips/points/%) given.
- **Author clarification needed:** Yes — needs a numeric equality tolerance. See ambiguity register.

### 3.4 Swing Highs / Swing Lows

- **English name:** Swing High / Swing Low
- **French name:** Sommet de swing / Creux de swing
- **Category:** Structural POI
- **Bullish version:** Swing low (rejection upward)
- **Bearish version:** Swing high (rejection downward)
- **Short definition:** A previous market high where price rejected and moved down (swing high), or a previous market low where price rejected and moved up (swing low). Structural liquidity zones because retail stop-losses/pending orders cluster around them.
- **Main validation condition:** Not formally quantified — no explicit rule for how many candles/what price move defines a qualifying "rejection" (contrast with e.g. Order Block's explicit 2×/3× candle-size rule).
- **Recommended timeframe:** Not explicitly stated for this specific POI beyond the book's general higher-timeframe-is-stronger principle.
- **Section:** Chapter 1 → Structural POI → "4. Swing highs — Swing lows" (¶618–626).
- **Precise enough for coding:** No — the underlying swing-detection rule (fractal window size, minimum retracement, etc.) is not defined.
- **Author clarification needed:** Yes — needs an explicit swing-detection rule (e.g. N-candle fractal, or minimum retracement %). See ambiguity register.

### 3.5 Previous/Current Period High-Low Levels

- **English name:** Previous Day High / Previous Day Low, Previous Week High / Previous Week Low, Previous Month High / Previous Month Low, High of the Day / Low of the Day, High of the Week / Low of the Week, High of the Month / Low of the Month (12 named variants, one family of POI)
- **French name:** Plus haut/bas du jour précédent, de la semaine précédente, du mois précédent; plus haut/bas du jour, de la semaine, du mois
- **Category:** Structural POI
- **Bullish version:** Any "Low" variant — liquidity rests below; a sweep-and-reverse there is bullish
- **Bearish version:** Any "High" variant — liquidity rests above; a sweep-and-reverse there is bearish
- **Short definition:** The extreme price of a given prior or current calendar period. All twelve variants share the same logic: liquidity (stop-losses, breakout orders, take-profits) accumulates on the far side of the level; price may sweep that liquidity before reversing, or break through and continue if the underlying pressure is strong enough.
- **Main validation condition:** Mechanically well-defined (each is simply the period's high or low price) — the interpretive/subjective part is only in reading whether the market will "sweep-then-reverse" vs. "break-and-continue," which the book says depends on market direction, trend, and confirmation from the timeframe/context — not on a standalone numeric rule.
- **Recommended timeframe:** Explicit ranking: monthly level > weekly level > daily level (higher timeframe = stronger, more liquidity).
- **Section:** Chapter 1 → Structural POI → "4. High and low of the following: ..." (¶627–686).
- **Precise enough for coding:** Yes for detecting the levels themselves (they are pure price extremes over a defined calendar window); No for automatically predicting sweep-vs-break behavior (this is explicitly left to market context/confirmation, not a formula).
- **Author clarification needed:** Only for the sweep-vs-break decision logic, which the book treats as contextual rather than rule-based.

---

## Summary Table

| # | POI | Category | Precise Enough to Code? | Needs Author Clarification? |
|---|---|---|---|---|
| 1.1 | Order Block | Volume-Based | Yes | Minor (candle-size measurement method) |
| 1.2 | Fair Value Gap | Volume-Based | Yes (gap geometry) | Yes ("noticeably smaller" not quantified) |
| 1.3 | Buy-to-Sell / Sell-to-Buy Candle | Volume-Based | Yes | Yes ("clear reversal" distance undefined) |
| 1.4 | Rally-Base-Rally / Drop-Base-Drop | Volume-Based | Yes (breakout ratio) | Yes (base candle "small/uniform" undefined) |
| 1.5 | Pressure Wick / Liquidity Wick | Volume-Based | Partially | Yes (wick:body ratio undefined) |
| 2.1 | Bullish/Bearish Engulfing | Price Action | Yes | No (beyond shared candle-size ambiguity) |
| 2.2 | Hammer / Shooting Star | Price Action | Partially | Yes (wick:body ratio undefined) |
| 2.3 | Morning Star / Evening Star | Price Action | Yes (3-candle ratio) | Yes (doji size undefined) |
| 3.1 | Trendline | Structural | Partially | Yes (steepness, "meaningful swing" undefined) |
| 3.2 | Support / Resistance | Structural | No | Yes (level tolerance, touch count undefined) |
| 3.3 | Equal Highs / Equal Lows | Structural | No | Yes (equality tolerance undefined) |
| 3.4 | Swing Highs / Swing Lows | Structural | No | Yes (swing-detection rule undefined) |
| 3.5 | Previous/Current Period High-Low | Structural | Yes (level detection) | Only for sweep-vs-break prediction |

No POI outside this list appears in the book. See [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md) for the full detail behind every "needs clarification" flag above, and [SOURCE_INDEX.md](SOURCE_INDEX.md) for section-by-section sourcing.
