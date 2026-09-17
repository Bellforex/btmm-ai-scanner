# BTRC V1 — RC3 final semantic lock: OB leg origin, immutability, P5 source TF

Branch `rc3-ob-origin-revision`, commit `e80dade` on top of `4739844`. This
supersedes the movement-origin gate (`BTRC_V1_RC3_OB_MOVEMENT_ORIGIN_REVISION.md`,
Rule M) and keeps every other RC3 decision (Doji rule, 18 canonical types, type
filters, annotation integrity, FVG / S/R / T3 corrections, P6).

## 1. Author decisions (2026-09-17)

| # | decision |
|---|---|
| 1 | ORDER BLOCK = ACTUAL LEG ORIGIN, from structural leg identity; no new numeric threshold |
| 2 | a confirmed POI never disappears retroactively; it still ends through its lifecycle |
| 3 | P5 POI-specific scoring uses `source_timeframe`; higher-TF overlap is explicit derived context |
| — | no 19th DOJI type; Doji rule, star Doji middle, hammer / shooting star unchanged |

## 2. Leg identity (`poi/leg_origin.py`)

Built only from frozen primitives: P1 confirmed swings and the P2 structure walk
(`structure/transitions.run_structure_walk`).

* A bullish leg is **confirmed** by a bullish break (BULLISH_BOS / BULLISH_CHOCH),
  which breaks one confirmed swing high. `leg_id` = that break.
* Its **origin** is the lowest confirmed SWING_LOW whose pivot lies after the
  broken swing high and before the break candle, confirmed no later than the
  break. For a BOS that is the pullback terminal; for a CHOCH the bottom of the
  bearish leg that ended. Exact price ties go to the latest pivot.
* The **BUY ORDER BLOCK** is the earliest frozen raw OB formation (2.0 size
  rule, colours, close beyond origin extreme, Doji rule) with a source candle on
  the origin swing's pivot candles, complete by the break. At most one per leg.
  Availability = the break (never before formation, origin confirmation or
  break).
* Every other raw formation is **ENGULFING only**: mid-leg formations, and
  formations sitting on a later confirmed higher low inside the same leg.
* SELL mirrors (highest SWING_HIGH between the broken swing low and a bearish
  break).
* The engulfing of a promoted formation still ends with
  `PROMOTED_TO_ORDER_BLOCK` at the ORDER BLOCK availability unless an earlier
  terminal cause (first touch / invalidation) stands.

## 3. H4 author regression

`tests/fixtures/rc3_leg_origin_h4_author.json`: the first 34 real FXCM H4 bars
after the sealed range (unmodified) plus a labelled synthetic pre-context
(timestamps before the seal) that only seeds ATR and an established bullish
structure. The frozen engine reproduces the real swing sequence exactly.

| field | value |
|---|---|
| formation | origin 2026-08-04 18:00 UTC, displacement 22:00, zone 4074.70–4088.96 |
| old type (Rule M, `4739844`) | BUY ORDER BLOCK (its displacement candle is the confirmed swing low 4065.46) |
| new type | **BULLISH ENGULFING** |
| actual leg origin | SWING LOW 4019.03 at 2026-08-03 10:00 |
| leg-confirming break | BULLISH BOS 2026-08-05 02:00 close (fixture); live FXCM chart BOS 08-05 10:00 |
| candidate position | after the origin, on a higher low inside the already-running bullish leg |
| engulfing availability | 2026-08-05 02:00 (displacement close) |
| second example | 08-05 06:00, 4153.11–4179.50: **BULLISH ENGULFING** (locked too) |

Live PARITY DEV v10 on FX:XAUUSD H4 (full chart history, P3LIFE registry):
both formations are type 11 BULLISH ENGULFING; no BUY ORDER BLOCK row exists for
either source time.

## 4. Immutability

* Incremental kernel: every ORDER BLOCK the gate produces is locked the first
  time it appears, with availability = max(gated availability, that candle).
  The locked set is append-only (no REMOVED / CHANGED deltas).
* Batch engine: reproduces exactly that union over all prefixes. It replays the
  prefix swing sets with the frozen incremental swing primitives
  (`iter_prefix_swing_candidates`, equal to `detect_confirmed_swings` at every
  prefix) and recomputes the walk only on prefixes whose swing or swing-
  relationship inputs differ from the final set restricted to what was
  available; on every other prefix the gate output equals the final output
  restricted by availability.
* Tests: supersession fixture (origin swing superseded by a lower low in the
  same pivot run, the break disappears from a fresh recomputation) keeps the
  ORDER BLOCK with its first-seen availability and geometry at every later
  prefix; lifecycle continues (terminal after the breach); kernel == batch at
  every prefix (BUY / SELL / reversal / supersession); restart determinism.
* Audit of the other P3 types: all candle-pattern families (FVG, engulfing,
  stars, single-candle reversals, pressure wicks, B2S/S2B, bases) are append-only
  and never removed. Reference zones (SUPPORT / RESISTANCE) and period / equal
  levels are *current-state* projections of measurement records by design
  (REPLACE / REMOVE follow upstream) and were not changed here; Pine never
  removes a registry POI in any family.
* Pine: gates only a break that becomes available on the current bar. The
  window walk re-derives older breaks each bar; re-gating them at the window
  edge produced a late SELL ORDER BLOCK (source 07-08, availability 09-11) in a
  first live build, removed before commit.
* Real data (all TFs, unsealed): 0 ORDER BLOCKs restored by immutability
  (prefix union == final gate), i.e. no retroactive disappearance occurs today.

## 5. P5 source timeframe

`btrc/t5_engine.py`: `poi_tf = poi.source_timeframe`. `BtrcDecision.higher_tf_context`
carries the merged effective timeframe when it differs (informational; no score
reads it). P3 identity and `effective_timeframe` are unchanged. Pine was already
host-only, so the host POI's own timeframe is what it scores.

## 6. Measured delta vs `4739844`

Type counts, same-session FXCM exports, all unsealed segments (batch engine):

| TF | BUY OB | SELL OB | BULL ENG | BEAR ENG |
|---|---|---|---|---|
| W1 | 6 → 0 | 14 → 1 | 35 → 35 | 35 → 35 |
| D1 | 5 → 3 | 17 → 4 | 37 → 37 | 45 → 45 |
| H4 | 9 → 1 | 17 → 2 | 56 → 56 | 50 → 50 |
| H1 | 11 → 1 | 14 → 1 | 30 → 30 | 34 → 34 |
| M15 | 11 → 1 | 14 → 3 | 30 → 30 | 35 → 35 |
| M5 | 10 → 1 | 14 → 1 | 36 → 36 | 44 → 44 |

Engulfing records are unchanged by construction. ORDER BLOCKs are now one per
structurally confirmed leg whose origin swing carries a raw formation.

Downstream (120-bar daily authority) — see section 8.

## 7. Live acceptance

USER DEV v27/v28 (`244a2201…`) and PARITY DEV v10 (`e578a07e…`), FX:XAUUSD:
M1, M5, M15, H1, H4, D1, W1 — status ready, 0 unannotated boxes, no `TF?`.
Live ORDER BLOCKs match Python exactly: H1 BUY OB 4349.10–4359.79 (source
1788908400000, availability 1788962400000) and H4 SELL OB 4564.29–4572.91
(source 1779732000000, availability 1779890400000).

## 8. Downstream authority delta (120-bar daily authority, M15 host, 2026-08-10..11)

`4739844` (`artifacts/rc3_lock_delta/old_4739844`, run from a worktree) vs
`e80dade` (`new_e80dade`), `tests/parity_support/rc3_authority_diff.py`:

| stage | before | after | change |
|---|---|---|---|
| P3 rows | 16 742 | 16 740 | 286 removed (BUY OB 166, SELL OB 120), 284 added (BULL ENG 164, BEAR ENG 120 — engulfings no longer ended by promotion), 122 changed (OB availability, 2 engulfing terminals) |
| distinct POIs | 365 | 363 | |
| P5 rows | 16 742 | 16 740 | 8 181 common rows changed (momentum 8 009, breakout 4 802, volatility 4 881, final 7 102) |
| permissions | | | 1 681 common rows changed |
| P8 events | 674 | 862 | 83 removed, 271 added (ENTERED_ACTIONABLE +90, LOST_ACTIONABLE +104) |
| terminal reasons | MITIGATED 156, PROMOTED 3 | MITIGATED 156, PROMOTED 1 | |

Classification of every changed P5 row (`p5_classification.json`): **8 181 /
8 181 = POI with higher-timeframe overlap context, now scored on its source
timeframe** (before: all 8 181 such rows were scored on the raised effective
timeframe; after: 0). No other P5 change exists. Largest permission moves:
WATCH_ONLY→NO_TRADE_CONTEXT 817, WATCH_ONLY→COUNTER_TREND 411,
COUNTER_TREND→WATCH_ONLY 232, BUY_BIAS→WATCH_ONLY 94. Scores were not tuned.

The additional P8 permission events come from the same rescoring: source-TF
T3 values move more often across the permission boundaries than the
higher-timeframe values did.
