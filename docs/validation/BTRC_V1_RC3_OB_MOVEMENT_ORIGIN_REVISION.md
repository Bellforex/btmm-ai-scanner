# BTRC V1 — RC3 semantic revision: ORDER BLOCK = MOVEMENT ORIGIN

**Type:** intentional semantic revision (not presentation). P3 identity, P5
rows and P8 events change. Branch `rc3-ob-origin-revision`, based on
`e496c31` (display layers). The pushed event build `rc3-highram-continuation`
@ `2a57bc0` is preserved unchanged as historical evidence.

## 1. Author definition and decisions

ORDER BLOCK = end of the previous movement or pullback = beginning of a new
directional leg. A same-direction engulfing inside a leg that has already
started is an ENGULFING, not an order block. Both directions mirror.

Decisions taken with the author on 2026-09-17 (measured options were
presented first):

| # | question | decision |
|---|---|---|
| 1 | which existing primitive defines "movement origin" | **Rule M**: a meaningfully confirmed opposite swing (`domain/swings.py`, including alternation) pivots on the formation's origin or displacement candle |
| 2 | what the formation is while the origin test is pending | **engulfing, then promote**: the engulfing keeps today's timing; on confirmation an ORDER BLOCK record is registered and the engulfing ends with `PROMOTED_TO_ORDER_BLOCK` |

Derived without new thresholds:

* **Source** stays the origin formation (candidate time = origin candle,
  zone = origin candle range, source candles unchanged).
* **Availability** = the anchoring swing's meaningful confirmation, which is
  always after the displacement close (pivot end + 3 bars at the earliest).
* **Priority**: a cause that already ended the engulfing at or before the
  promotion bar (first touch / genuine invalidation) is kept, so a zone price
  already used stays MITIGATED. The ORDER BLOCK record still exists and its
  own freshness starts strictly after its availability (existing rule).
* The OB formation detector itself is unchanged: 2.0 size rule, colour rule,
  close beyond the origin extreme, 3.0 STRONG tier.

## 2. Exact rule (Python is the semantic master)

`poi/order_blocks.apply_movement_origin_gate(formations, confirmed_swings)`:

1. For each formation from `detect_order_blocks` (origin `d-1`,
   displacement `d`): wanted swing = `SWING_LOW` for BUY, `SWING_HIGH` for
   SELL.
2. Candidate anchors = confirmed swings of the wanted type whose
   `pivot_candle_record_ids` contain the origin or displacement candle.
3. None -> no ORDER BLOCK (the engulfing detector still emits the ENGULFING).
4. Otherwise anchor = earliest `meaningful_confirmation_time_utc` (ties by
   record id); ORDER BLOCK availability = confirmation =
   `max(displacement close, anchor confirmation)`.

`poi/lifecycle.apply_order_block_promotion` then ends the engulfing of the same
formation (same timeframe and source candles, matching direction) at the ORDER
BLOCK availability, unless an earlier-or-equal terminal cause exists.

Incremental replay: `detector_frontier` keeps raw formations append-only and
treats gated ORDER BLOCKs as a mutable family rebuilt only when the formation
count or the confirmed-swing signature changes (bounded NEW / CHANGED /
REMOVED deltas to the lifecycle scheduler). The kernel equals the batch engine
at every prefix (`test_replay_kernel_matches_batch_at_every_prefix`).

## 3. Measured effect — real FXCM XAUUSD, sealed range excluded

`tests/parity_support/rc3_ob_origin_counts.py` (real engine, per unsealed
segment):

| TF | BUY OB | SELL OB | reclassified BUY->BULL ENG | reclassified SELL->BEAR ENG | mean / max delay (bars) | engulfings promoted | engulfing already mitigated first | lookahead |
|---|---|---|---|---|---|---|---|---|
| W1 | 33 -> 8 | 39 -> 16 | 25 | 23 | 2.67 / 3 | 16 | 8 | 0 |
| D1 | 41 -> 6 | 45 -> 20 | 35 | 25 | 2.50 / 3 | 16 | 10 | 0 |
| H4 | 63 -> 10 | 61 -> 21 | 53 | 40 | 2.77 / 3 | 14 | 17 | 0 |
| H1 | 34 -> 13 | 39 -> 17 | 21 | 22 | 2.43 / 3 | 18 | 12 | 0 |
| M15 | 32 -> 13 | 41 -> 16 | 19 | 25 | 2.59 / 3 | 14 | 15 | 0 |
| M5 | 36 -> 12 | 46 -> 14 | 24 | 32 | 2.50 / 3 | 9 | 17 | 0 |

Engulfing record counts are unchanged by construction.

## 4. Tests (real engine, synthetic rows, BUY and exact SELL mirror)

`tests/unit/test_rc3_order_block_movement_origin.py`:

* positive: end of an opposite leg -> ORDER BLOCK available at confirmation
  (+2 bars); end of a pullback starting a continuation leg -> ORDER BLOCK;
* negative: two mid-leg engulfings whose raw formations meet every OB
  condition -> ENGULFING only; only the leg origins are order blocks;
* the author's example-1 *pattern* (a radius-2 dip low with no confirmed swing
  high since the leg-start low) -> ENGULFING;
* a first touch before confirmation keeps the engulfing MITIGATED;
* one live record per formation; no ORDER BLOCK before its confirmation bar
  (prefix by prefix); incremental kernel == batch at every prefix.

Positive BUY fixtures 2 (+2 SELL mirrors); negative BUY fixtures 3 (+3 SELL).

## 5. Downstream impact — 120-bar daily authority (M15, 2026-08-10..11)

`tests/parity_support/rc3_authority_diff.py`, before `f9a78fc` engine vs after:

| stage | before | after | change |
|---|---|---|---|
| P3 rows | 18 065 | 16 986 | 1 079 removed (BUY OB 518, SELL OB 155, BULL ENG 284, BEAR ENG 122 — the last two are engulfings that ended earlier by promotion), 412 changed (OB availability / lifecycle) |
| distinct POIs | 385 | 368 | |
| P5 rows | 18 065 | 16 986 | 142 common rows changed (momentum 140, breakout 141, volatility 107, final 126) |
| permissions | | | 76 common rows changed |
| P8 events | 713 | 677 | 46 removed, 10 added; 3 `PROMOTED_TO_ORDER_BLOCK` terminals |

P5 component changes on POIs whose type did not change come from the
higher-timeframe context: fewer ORDER BLOCK records change which POIs the
cross-timeframe merge raises. Performance: 81.1 s -> 81.8 s for the same 120
bars; two runs gave identical P3/P5/P8 digests.

## 6. Pine (USER and PARITY)

Both builds: OB formations are queued (`obPending`); `f_poiGateOrderBlocks`
emits an ORDER BLOCK once a P1 confirmed opposite swing covers the formation
(`p3Swings`, this bar's swings), availability = the swing's
`meaningfulConfTime`; `f_poiApplyPromotions` runs after the lifecycle advance
and sets `C_POI_TERM_PROMOTED` (3, label `PROMOTED_TO_ORDER_BLOCK`) unless an
earlier cause stands. `capture_neutral_core(USER) == capture_neutral_core(PARITY)`
(test).

Token funding: the port cost ~1 240 tokens in USER, which sat at the ceiling.
USER dropped its Debug-Mode developer instrumentation (P1/P2/P4 debug
drawings, debug table, debug data-window plots). None of it computed a value;
the PARITY capture build keeps every capture stream. PARITY needed 15 tokens,
found in two provably equivalent simplifications of the gate.

Live, FX:XAUUSD (provider FXCM): USER DEV **v23**
(`6fc5eca1d3012ad4f845403d1d755aafc6f43b0f5f593dd3e333cbe6d88442ed`) and
PARITY DEV **v5**
(`bb97f19e910855994b15b0c748c866a59c8de182fa01e8c74bce6fde5302d69a`) compiled
and ran together on M1, M5, M15, H1, H4, D1 and W1: status ready, not failed,
FVG zones present, 0 composite labels, TF? = 0, 0 colour mismatches.

## 7. The author's two H4 examples

| example | origin (UTC) | zone | result under Rule M |
|---|---|---|---|
| 2 | 2026-08-05 06:00 | 4153.11–4179.50 | **BULLISH ENGULFING** (neither candle is a swing pivot; leg already running) |
| 1 | 2026-08-04 18:00 | 4074.70–4088.96 | **BUY ORDER BLOCK** |

Example 1 is NOT reclassified. The frozen swing engine confirms SWING LOW
08-03 10:00 (4019.03) -> SWING HIGH 08-04 14:00 (4106.14) -> SWING LOW on the
displacement candle 08-04 22:00 (4065.46) -> SWING HIGH 08-06 02:00 (4304.06).
Under the chosen rule this is the end of a confirmed bearish pullback that
starts a continuation leg, which the author's own definition calls an ORDER
BLOCK. The earlier pre-implementation note that Rule M would reclassify it
assumed no swing high confirms in between; that assumption was wrong. Both
examples sit in the first H4 bars after the sealed window, so neither can be
turned into a permanent Python fixture without the sealed bars the swing ATR
needs; the pattern is covered synthetically instead. **Author decision needed**
if example 1 must be an engulfing (it would need a stricter origin notion than
the confirmed swing, e.g. a minimum pullback depth — a new threshold).

## 8. Known limitations

1. **Swing supersession (F3).** A confirmed swing can later disappear in the
   frozen swing primitive. Python then removes the ORDER BLOCK (mutable
   family); Pine never removes an emitted POI. Measured prefix by prefix: 0 of
   116 anchoring swings (H4 31, H1 30, M15 29, D1 26) disappeared within 40
   bars on real data. A divergence here would be
   a parity blocker for that POI only.
2. About half of promoted formations were already touched before confirmation
   (their engulfing stays MITIGATED); their ORDER BLOCK record is still
   registered fresh after its availability, per the author's lifecycle rule.
3. P3/P5/P8 aligned parity must be re-captured: the captures before this
   revision describe the old OB semantics. The remaining higher-timeframe
   context blocker (P5 on `effective_timeframe`) is unchanged.

## 9. Also in this branch (presentation, `e496c31`)

BTMM lifecycle is now optional **markers** (default OFF): a small diamond at
the bottom of the pane on the bar where a P4 count grows (orange = final gate,
yellow = forming), with a tooltip legend; the earlier full-height background
was removed. Other toggles: Show FVG, Show Support / Resistance, Show Market
Structure (default OFF), Show Dashboard, Show POI Table, Show POI Zones,
Show POI Text.
