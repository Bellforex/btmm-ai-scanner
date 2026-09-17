# BTRC V1 — RC3 POI type filters, Doji classification, annotation integrity

Branch `rc3-ob-origin-revision`, on top of the ORDER BLOCK movement-origin
revision (`BTRC_V1_RC3_OB_MOVEMENT_ORIGIN_REVISION.md`). Commits `6f79d19`
(semantics + presentation) and `8ba80b4` (Pine if-chain type fix, PARITY debug
strip, coverage tool). RC1 / RC2 and the pushed event build are unchanged.

## 1. Author decisions (2026-09-17)

| # | question | decision |
|---|---|---|
| 1 | Doji as a POI type? | **Suppress only, no new type.** A Doji is not a P3 enum; it only removes primary labels |
| 2 | which candle may not be a Doji | **either candle** — neither the engulfed/origin nor the engulfing/displacement candle |
| 3 | HAMMER / SHOOTING STAR on Doji-bodied candles | **unchanged** |

Doji = `body_efficiency = |close - open| / range <= 0.10`, the already frozen
`doji_body_efficiency_standard` (Pine `C_POI_DOJI_BODY_EFF_STANDARD`). No new
threshold. MORNING STAR / EVENING STAR keep accepting a Doji middle candle.

## 2. Semantic changes (Python master, Pine mirrors)

1. **Doji rule** — `poi/engulfing.py` and `poi/order_blocks.py` skip a pair
   when either candle is a Doji (after the existing ratio check). Mirrored in
   `tests/parity_support/p3_pine_model.py` and both Pine builds.
2. **One ORDER BLOCK per leg origin** — `apply_movement_origin_gate` processes
   formations in (candidate time, source ids) order and lets each anchoring
   swing produce at most one ORDER BLOCK. Later formations on the same swing
   stay ENGULFING. Pine: `var map<int, bool> obSwingUsed`, key = pivot end time
   + swing type. Real data: 0 occurrences today; enforced for determinism.

### Measured (real FXCM XAUUSD, sealed range excluded)

| TF | Doji→engulfing before (first / second candle) | after | Doji→OB before | after |
|---|---|---|---|---|
| H4 | 25 / 7 | 0 | 5 | 0 |

ORDER BLOCKs after Doji + Rule M: W1 BUY 6 / SELL 14, D1 5/17, H4 9/17,
H1 11/14, M15 11/14, M5 10/14. Max availability delay 3 bars; lookahead 0.

120-bar daily authority (M15, 2026-08-10..11), OB-origin engine vs final:
P3 244 rows removed (3 engulfing POIs) + 120 changed; P5 120 rows changed,
76 permission changes; P8 −3 events. Two runs: identical digests (78.5 s /
79.0 s).

Fixtures: `tests/unit/test_rc3_doji_primary.py` with real H4 examples in
`tests/fixtures/rc3_doji_fxcm_h4.json` (Doji first / second candle, bull and
bear engulfing, buy and sell OB origin), stars with a Doji middle, hammer
unchanged, synthetic boundary pairs at exactly 0.10, Pine locks in both builds.

## 3. POI type filters (presentation only, USER build)

Group **POI type filters**: one checkbox per core type, all default ON, in
code order (`p7zTypeOn[code - 1]`): BUY/SELL ORDER BLOCK, BUY/SELL FVG, B2S,
S2B, BASE RALLY/DROP, BULLISH/BEARISH PRESSURE WICK, BULLISH/BEARISH
ENGULFING, HAMMER, SHOOTING STAR, MORNING/EVENING STAR, SUPPORT/RESISTANCE
ZONE. They replace the old `Show FVG` / `Show Support / Resistance`
(no duplicate controls). Masters `Show POI Zones` / `Show POI Text` remain.

* Filters gate the fresh-zone collection, the dominance owners and the POI
  table rows. A hidden owner does not hide its FVG: when BUY OB or BULL
  ENGULFING is switched off, the same-formation BUY FVG reappears (by design;
  dominance only resolves between displayed formations).
* The POI table footer reads `N shown / M active`; the dashboard's Active POIs
  total stays **global** (engine state, not a display count).
* `semantic_core(USER)` contains none of the filter variables (test); the
  registry, freshness, terminal state, P5 and P8 cannot see them.
* No presets were added (not needed; every combination is safe).

## 4. Annotation integrity

Live H4 MORNING STAR lost its text. Cause: **TEXT_OWNER_COLLISION** — the
one-text-owner-per-collision-group rule gave the name to a touching, unrelated
BUY FVG and blanked the star. The rule was removed: every displayed box carries
`TF • NAME` unless `Show POI Text` is off. Exact-geometry groups still merge
names ("A + B") and same-formation dominance still hides the FVG, so a distinct
formation is never silently unnamed. EVENING STAR is mirrored. Edge clipping:
box-native text with `size.auto` (no abbreviation layer).

## 5. Coverage and toggle matrices

`tests/parity_support/rc3_poi_type_coverage.py` (engine + P7-Z model, last
unsealed segment, capacity 30): 0 annotation failures for every type on
W1/D1/H4/H1/M15/M5. H4 example: MORNING STAR detected 4 / fresh 1 /
displayed 1 / annotated 1; EVENING STAR 6 / 1 / 1 / 1.

Live, USER DEV v24 on FX:XAUUSD H4 (cap 30): all 18 filters — OFF removes that
type's boxes to 0 while every other non-FVG type is unchanged, ON restores the
exact base. M1/M5/M15/H1/H4/D1/W1 with USER v24 + PARITY v8: status ready,
0 unannotated boxes, 0 composite labels, TF? = 0, 0 colour mismatches.

## 6. Pine builds

* USER DEV **v24** `e08d0edf…` — Doji, one OB per leg, filters, annotation.
* PARITY DEV **v8** `c919f4a1…` — same semantics. To fit the token ceiling
  (100 605 → under 100 256) the Debug-Mode P1 drawings (swings, equal levels,
  trendlines, S/R boxes, displacement markers) and the P1 debug table were
  removed; they computed nothing. Every capture stream is kept.
  `capture_neutral_core(USER) == capture_neutral_core(PARITY)`.
* Pine CE10235 fix: the gate's if/else chain mixed `array.remove` (element)
  and `k += 1` (int); replaced by a `drop` flag.

## 7. Open items

1. Full daily authority: the run started before the Doji rule and must be
   rerun on the final engine.
2. P3/P5/P8 aligned parity re-capture; higher-TF context in P5; F3 swing
   supersession (see the OB revision doc).
3. Author example 1 (H4 4074.70–4088.96) remains BUY ORDER BLOCK under Rule M.
