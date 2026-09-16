# BTRC-V1 RC3 — Order Block Structural Contract (Phase 2)

**Status:** documentation/analysis only. No code, test, Pine or register change.
**Authority:** the Python engine (`src/btmm_ai_scanner/`) is the semantic authority; author decisions are in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md` (cited "REG:line"); the knowledge base is `knowledge/` (cited "MS:line" for `knowledge/MEASUREMENT_STANDARDS.md`, "OB-KB:line" for `knowledge/poi_rules/volume_based/buy_order_block.md`, "ENG-KB:line" for `knowledge/poi_rules/price_action/bullish_engulfing.md`, "CAT:line" for `knowledge/POI_MASTER_CATALOG.md`). Code paths are relative to `src/btmm_ai_scanner/`.
**Scope:** recover existing definitions only. Nothing here recommends a trading rule.

---

## 1. Movement / up-move / down-move (legs)

- **No automated up-move/down-move object exists.** `measurements/legs.py:39-125` (`measure_leg`) measures a caller-supplied candle sequence; it never decides where a move starts or ends.
- Leg formulas: start = first candle open, end = last candle close (`legs.py:64-66`); Reference ATR = median of known ATRs (`legs.py:68-69`); path = sum of Total Ranges (`legs.py:71`); Directional Candle Share counts `close >= open` (bullish) / `close <= open` (bearish) (`legs.py:73-82`); speed = distance / (bars x ATR), efficiency = distance / path (`legs.py:96-99`); `STRONG_FAST` / `FAST` / `SLOW_OR_UNCLEAR` (`legs.py:101-114`), thresholds 0.50/0.60/0.67 and 0.75/0.75/0.80 (`domain/configuration.py:55-60`), matching MS:735-741.
- KB: BTMM movement legs use **expert-labelled anchors only** until automatic anchor detection is approved (MS:721). Speed "must never approve or reject a POI" (MS:743). The speed standard is "Not automatically extended to Order Blocks ... Engulfing candles" (MS:652).
- Callers that choose leg boundaries themselves: S/R reaction legs (`domain/support_resistance.py:127-145`), POI lifecycle reclaim-to-displacement legs (`poi/lifecycle.py:320`, `poi/lifecycle_cursor.py:198`), BTMM reaction (`btmm/reaction.py:108,170`).
- The only swing-anchored "impulse" in code is the BTRC pullback (section 3).

## 2. Swing (`domain/swings.py`, KB MS:1035-1167)

| Aspect | Code | KB |
|---|---|---|
| Window radius | `_WINDOW_RADIUS = 2` (`swings.py:20`); candidates only at `2 <= i < n-2` (`swings.py:91`) | 2 left + candidate/plateau + 2 right (MS:1043) |
| Extreme used | wick high/low (`swings.py:102-110`) | wick only (MS:1047,1051) |
| ATR prerequisite | pivot skipped if ATR(14) at pivot is `None` (`swings.py:92-94`) | MS:1091 |
| Tie tolerance | `0.02 x ATR` (`swings.py:95`; `domain/configuration.py:27`); neighbours must satisfy `high_j <= high_i + tol` / `low_j >= low_i - tol` | `MAX(2 x tick, 0.02 x ATR(14))` (MS:1056) |
| Dual qualification | a candle that is both high and low candidate emits neither (`swings.py:112-116`, register §33I) | — |
| Plateau merge | adjacent same-type pivots (`start == end+1`) within the first pivot's tolerance merge pairwise; price = max high / min low; ATR = median (`swings.py:139-180`) | MS:1063-1070, MS:1080 |
| Same-direction supersession | within a run of same-type pivots not interrupted by an opposite-type raw pivot, only the most extreme survives (`swings.py:183-205`) | "Before meaningful confirmation, a higher high replaces..." (MS:1111) |
| Local confirmation | index `pivot.end_index + 2`; time = that candle's `availability_time_utc` (`swings.py:224-226,276`) | LOCAL_SWING_CANDIDATE after 2 right-side closes (MS:1074) |
| Meaningful confirmation | threshold `0.50 x pivot_reference_atr` (`swings.py:231-233`; `domain/configuration.py:28`); search starts at `local_index + 1` (`swings.py:237`); first candle where pivot minus lowest low (high) / highest high minus pivot (low) `>= threshold` (`swings.py:238-255`); time = that candle's availability (`swings.py:277`) | `MAX(2 x tick, 0.50 x ATR)` (MS:1088); MS:1095-1107 |
| Alternation | a pivot whose type equals the last confirmed type is skipped (`swings.py:228-229,285`) | MS:1119 |
| Availability | `availability_time_utc = meaningful_confirmation_time_utc` (`domain/analyzer.py:318`) | MS:1115 |
| Unconfirmed pivots | dropped (`swings.py:257-258`); no SUPERSEDED / LOCAL records emitted | MS:1144 lists those states |

Incremental twin: `domain/analyzer.py:581-600` reproduces the same loop and states the walk "must be redone each candle" because an earlier pivot's confirmation can flip later and changes every later skip/attempt outcome.

## 3. Pullback (BTRC-T3, `btrc/t3_engine.py`)

- Input: `confirmed_swings` per timeframe plus `CurrentStructureState` (`t3_engine.py:477-489`). Swings ordered by `(availability_time_utc, pivot_start_time_utc, record_id)` (`t3_engine.py:78-86`).
- No state if structure is `None`/`UNDETERMINED` (`t3_engine.py:294-307`).
- **Bullish** (`t3_engine.py:369-393`): impulse top = last `SWING_HIGH`; origin = last `SWING_LOW` with `pivot_start <= top.pivot_start`; pullback swing = last `SWING_LOW` with `pivot_start > top.pivot_start`; `leg = top.price - origin.price` (must be > 0); `depth = (top.price - pullback.price) / leg`. **Bearish** mirrors (`t3_engine.py:395-418`).
- States (`btrc/enums.py:82-89`; `t3_engine.py:334-349`): `depth > 1` -> `STRUCTURAL_FAILURE`; `depth <= 0.382` -> `SHALLOW_PULLBACK`; `<= 0.618` -> `HEALTHY_PULLBACK`; else `DEEP_PULLBACK` (bands `t3_configuration.py:43-44`). No counter-swing -> `pullback_state=None` (`t3_engine.py:312-320`).
- POI genuine invalidation is recorded as supporting evidence only and never alone yields `STRUCTURAL_FAILURE` (`t3_engine.py:322-329,338-339`).

## 4. Terminal candle

**No definition exists.** No register section, knowledge-base standard or source module defines a "terminal candle" (a candle that ends a move). The only `terminal` identifiers in `src/` are POI-lifecycle terminal reasons (`poi/scheduler_walk.py:12-13,52-59`), unrelated to candle location.

## 5. Structural break (P2 BOS/CHoCH, `structure/`; REG §34, REG:3695-4250)

- Relationship labels HH/LH/EH and HL/LL/EL against the previous same-type swing with tolerance `0.10 x ATR` (`structure/relationships.py:53-72`; `structure/configuration.py:10`); availability = max of both swings (`relationships.py:95-97`).
- Event walk sorts candles (by availability), swings (visible at `meaningful_confirmation_time_utc`) and relationships (`structure/transitions.py:100-135`).
- Bootstrap: direction from `UNDETERMINED` to `BULLISH` on latest HH+HL, `BEARISH` on LH+LL; no transition record (`transitions.py:363-381`; REG:3829).
- Breaks are **close-only, strict**: CHoCH when close crosses the active protected level against the direction; BOS when close crosses the active weak level with the direction (`transitions.py:170-181`; REG:3890-3898).
- CHoCH has priority; one transition per candle (`transitions.py:183-253`; REG:3906). Guarded CHoCH: no emission if no unbroken opposite swing can become protected (`transitions.py:189-190,223-224`; REG:3900).
- Transition availability = `max(break candle availability, broken swing availability)` (`transitions.py:192-194,257-259`).
- New weak level only from a swing that becomes visible after the last break candle (`transitions.py:328-353`).
- Register: structure outputs are **not consumed by any POI detector** (REG:4258, REG:4578).

## 6. Order Block (REG §35K, `poi/order_blocks.py`)

Code (`order_blocks.py:27-84`), for each adjacent pair `(origin=i, displacement=i+1)`:
1. `total_range(origin) != 0` (`:39-41`).
2. `ratio = total_range(displacement) / total_range(origin) >= 2.0` (`:42-44`; `poi/configuration.py:23`).
3. BUY: origin `close < open`, displacement `close > open`, **and** `displacement.close > origin.high` (`:46-53`). SELL mirrors with `displacement.close < origin.low` (`:54-58`).
4. Tier `STRONG` if `ratio >= 3.0`, else `STANDARD` (`:62-66`; `poi/configuration.py:24`).
5. Zone `[origin.low, origin.high]` (`:74-75`); availability = confirmation = displacement `availability_time_utc` (`:79-80`); source ids `(origin, displacement)` (`:77`).

Register: size ratio 2.0/3.0, zone = origin full range, availability = displacement close (REG:4503). Frozen location statement, quoted exactly:

> **No "origin vs. middle of an existing move" automated gate is implemented** — this location distinction is stated qualitatively only in the book (a warning: "must be located at the beginning/origin... not randomly in the middle") with **no numeric or structural rule anywhere in the approved knowledge base to detect it automatically** (REG:4503)

and "**Required displacement, structure context:** none beyond the size-ratio rule; **no BOS is required**" (REG:4503). Approved as decision item 13, "the explicit, disclosed absence of an automated 'origin vs. middle' gate (§35K)" (REG:5014). KB: location "Must be located at the beginning/origin ... not randomly in the middle" (OB-KB:25); OB and Engulfing are "Same two-candle shape, different location rule" (OB-KB:147; CAT:38).

Non-suppression, quoted exactly: "detection itself never suppresses one because the other also matched" (REG:4503). Code: all detectors run independently and are concatenated; the only filter is `enabled_poi_types` (`poi/analyzer.py:389-409`). §35X reports cross-type overlap but never merges it (REG:4653).

## 7. Engulfing (REG §35L, `poi/engulfing.py`)

Code (`engulfing.py:27-82`), for each adjacent pair `(engulfed=i, engulfing=i+1)`:
1. `total_range(engulfed) != 0` (`:39-41`).
2. `ratio >= order_block_size_ratio_standard` (2.0) (`:42-44`); same configuration field as Order Block; no engulfing-specific field exists (`poi/configuration.py:23-24`).
3. BULLISH: engulfed `close < open` and engulfing `close > open` (`:46-53`); BEARISH mirrors (`:54-56`).
4. Tier `STRONG` if `ratio >= 3.0` (`:60-64`).
5. Zone `[engulfed.low, engulfed.high]` (`:72-73`); availability = confirmation = engulfing candle availability (`:77-78`).

Frozen statement, quoted exactly: "**"Middle of an existing move" is likewise not an automated gate** — same disclosed limitation as Order Block's "origin," for the same reason" (REG:4507). KB location "Must appear WITHIN/in the middle of an existing price movement" (ENG-KB:25).

## 8. Facts relevant to a terminal-location gate (mechanical)

**F1 — OB conditions are a strict superset of Engulfing conditions on the same pair, with identical zone geometry.** From sections 6 and 7: zero-range guard, ratio expression, 2.0 threshold field, colour conditions, 3.0 tier, zone (`first.high/first.low`), candidate time (first candle event time), confirmation/availability (second candle availability) and source ids are identical (`order_blocks.py:39-80` vs `engulfing.py:39-78`). The only extra OB condition is `displacement.close > origin.high` (BUY, `order_blocks.py:51`) / `< origin.low` (SELL, `:55`). So every OB pair also emits an Engulfing of the same direction, zone, tier and availability; the reverse does not hold.

Orchestrator-supplied measurements (real FXCM XAUUSD, same session, sealed range excluded; not re-derived here):

| TF | OBs identical to an Engulfing formation | OBs whose origin or displacement candle is a confirmed opposite swing pivot |
|---|---|---|
| W1 | 72/72 | — |
| D1 | 86/86 | 26/86 |
| H4 | 124/124 | 31/124 |
| H1 | 73/73 | 30/73 |
| M15 | 73/73 | 29/73 |
| M5 | 82/82 | — |

H4 counts: BUY_ORDER_BLOCK 63, SELL_ORDER_BLOCK 61, BULLISH_ENGULFING 69, BEARISH_ENGULFING 67 (consistent with F1: OB count <= Engulfing count per direction). For the swing-anchored OBs, meaningful confirmation arrived 2–3 host bars after the displacement close (H4: 7 at +2, 24 at +3).

**F2 — Earliest swing confirmation relative to the displacement close (index `d`, origin `d-1`).** From `swings.py:224,237-255`:

| Pivot located at | Local confirmation (close of) | Earliest meaningful confirmation (close of) |
|---|---|---|
| origin candle (`d-1`, single) | `d+1` (= displacement close + 1 bar) | `d+2` (+2 bars) |
| displacement candle (`d`, single) | `d+2` (+2 bars) | `d+3` (+3 bars) |
| plateau ending at `d` or later | `end+2` | `end+3` or later |

Meaningful confirmation can never share a candle with local confirmation, because the search starts at `local_index + 1` (`swings.py:237`). This matches the +2/+3 distribution above. **At the displacement close, no swing pivot at the origin or displacement candle can be locally or meaningfully confirmed.** The pivot also needs a non-`None` ATR at its index (`swings.py:92-94`).

**F3 — A swing pivot can be superseded or dropped later.** In a longer prefix: (a) a later, more extreme same-type raw pivot with no opposite-type raw pivot between them replaces the earlier one (`swings.py:183-205`); (b) alternation (`swings.py:228-229`) is re-evaluated over the whole pivot list, so an earlier pivot confirming later can make a previously confirmed later pivot be skipped (`domain/analyzer.py:586-600`). Neither step checks whether the earlier pivot was already meaningfully confirmed. A synthetic random-walk probe (60 series x 270 prefixes, default configuration, scratch only) found swings that were meaningfully confirmed in prefix `n` and absent in prefix `n+1` (for example, pivot index 116 confirmed at candle 119, removed when a higher raw pivot at 122 appeared). This conflicts with KB non-repainting (MS:1115; see section 10).

**F4 — Uses only information available at the displacement close to say a candle ends a move:** none found. Swings need 2–3 later bars (F2). Buy-to-Sell/Sell-to-Buy needs up to 3 later bars and its "existing trend" context is explicitly unautomated (REG:4515; MS:1512). Hammer/Pressure Wick are same-candle patterns, but their context ("around a support/resistance zone") is qualitative, not gating (REG:4509). CHoCH marks a structure break at the break candle, not the candle that ended the prior move (`transitions.py:170-175`). Structure is not a POI input (REG:4578,4584).

## 9. Author decisions a terminal-location gate would require

1. **Definition source:** which approved construct defines "origin/end of a move" (confirmed meaningful swing, local pivot, structure CHoCH/protected level, or a new standard). REG:4503 marks any BOS/CHoCH-based gate as "an unapproved rule addition".
2. **Availability/identity timing:** whether OB availability stays at the displacement close (RECON-D1, REG:4503; OB-KB:121) or moves to the gate's confirmation time (+1..+3 bars per F2), and whether record identity/semantic key changes as a result.
3. **Supersession handling:** what happens to an OB when its anchoring swing is later superseded or dropped (F3): retract, freeze at the first qualifying prefix, or ignore.
4. **Same-formation Engulfing fallback identity:** since every OB pair is also an Engulfing (F1), whether a pair that fails the gate stays an Engulfing only, whether a pair that passes stays both (the current non-suppression rule, REG:4503), and whether the Engulfing "middle of move" gate (REG:4507) becomes the complement.
5. **Hammer/Pressure-Wick coexistence (§35L):** whether "may coexist with a Pressure Wick label on the same candle without precedence" (REG:4509) and general non-suppression stay as they are once a location gate exists.
6. **Origin-candle colour and close-beyond condition:** whether the code-only OB condition `displacement.close > origin.high` (section 10) becomes the approved OB/Engulfing split, stays, or is removed.

## 10. Code / register / KB disagreements found in this scope

| # | Item | Code | Register / KB |
|---|---|---|---|
| D1 | OB extra conditions | origin opposite colour + displacement close beyond origin extreme (`order_blocks.py:51,55`) | size ratio only, "none beyond the size-ratio rule" (REG:4503); OB-KB:29 names displacement direction, not origin colour or close-beyond |
| D2 | Engulfing body coverage | not checked (`engulfing.py:46-58`) | "Core rule: the engulfing candle's body must cover/engulf the previous candle's body" (ENG-KB:53; CAT:134); REG:4507 omits it |
| D3 | Swing supersession after confirmation | possible (F3) | "must not be deleted because a later candle creates a more extreme price" (MS:1115) |
| D4 | Tick floors | tie tolerance and meaningful threshold have no `2 x tick` floor (`swings.py:95,231-233`) | `MAX(2 x tick, ...)` (MS:1056,1088) |
| D5 | BTRC pullback comment | engine: POI invalidation never alone yields STRUCTURAL_FAILURE (`t3_engine.py:322-324`) | config comment says it does (`btrc/t3_configuration.py:40-42`); engine docstring is ambiguous (`t3_engine.py:11-13`). Code-internal only |
