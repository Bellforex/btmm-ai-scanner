# BTRC V1 — RC4 Market Framework: seminar candidate evidence

Status: **RC4 EVENT / DEMO candidate**. Not production. Not merged to `main`.
Not published on TradingView. No live broker. No profitability claim: every
number below counts analytical states, never trade outcomes.

Branch `rc4-market-framework` (from RC3 freeze record `d96db40`; RC3 semantic
SHA `3f9f790` untouched). Bot: branch `bot-dryrun-integration`.

## 0. Seminar closure (final state)

| item | value |
|---|---|
| final RC4 semantic SHA | `e228c5d` (interaction-episode contract locked; evidence fields only, P3/P5/P8 digests unchanged vs `a15c199`) |
| USER build | `[RC4 MARKET FRAMEWORK]` v14, saved source `1279474b…`, token count ≈ 100 240–100 255 of 100 256 (headroom ≈ 0) |
| PARITY build | `[RC4 PARITY]` v1, saved source `127f775c…` |
| bot | `bot-dryrun-integration` `c5199d5`, pinned to `e228c5d` (digest `c0d4bb15…`), context lookback inherited from the scanner (250) |

### RC4 interaction-episode contract (RC4 profile only; RC3 unchanged)

POI available → waits untouched → the first qualifying post-availability
touch (the P3 first-touch; never a self-interaction of the source or
availability bar) **opens** an episode; the POI stays in P5 / P8 evaluation.
The episode ends at the **earliest** of: (1) true failure — beyond the far edge
by more than the BTMM overshoot tolerance and no reclaim within 3 bars (P8
reason INVALIDATED); (2) the end of the 5-bar BTMM reaction window
(MITIGATED). Invalidation before any touch and order-block promotion stay
immediately terminal (RC3). Recorded per decision: `first_touch_time_utc`,
`episode_start_time_utc`, `episode_end_time_utc`, `interaction_episode`.
Locked by `tests/unit/test_rc4_interaction_episode.py`: truth table; small
penetration inside tolerance ≠ wipeout; deeper penetration + reclaim = WIPEOUT;
no reclaim = FAILED at the earliest cause; continued acceptance stays failed;
a late reclaim does not undo a failure; on real FXCM M15 data RC3 terminal =
first touch (no episode), RC4 terminal within the 5-bar window with the POI
evaluable meanwhile, POI_TERMINAL exactly once and no event after it in both
profiles; incremental tracker == batch timeline for swing-level sweeps.

A valid BTMM cycle (DISTRACTION, DELAY or WIPEOUT) never creates a trade by
itself: a trade context still needs a qualified POI, location, P5 permission
and a P8 actionable transition.

### Framework mapping

The three frameworks feed one POI → P5 → P8 pipeline: market structure /
impulse-correction (reported `TREND`: location = retracement of the POI's own
origin impulse, not "POI direction == trend"); consolidation / range
(`RANGE`: high, low, midpoint, premium = upper third, discount = lower third,
INTERNAL / EXTERNAL liquidity scope on every sweep; middle-third POIs stay in
P3 and score 35); trendline / naked analysis (trendlines built by P1 from
confirmed swing anchors act as liquidity levels — their sweeps feed
DISTRACTION and the sweep bonus; never mandatory).

### Displays

All 18 POI type switches (default ON), Show POI Zones / Text, Show Market
Structure / Trendlines / Consolidation-Range / Liquidity / BTMM Cycle, Show
Dashboard, Show POI Table — each verified on the live chart by counting drawn
objects (all 18 types off → 0 zones; zones off → 0 boxes; text off → boxes
without text; dashboard + table off → 0 tables, clean chart). BTMM Cycle =
a compact diamond on the bar a POI's cycle becomes valid; the reason
(DIS / DEL / WIP) is in the POI table. Not in USER (token budget at the
limit): a functional Debug switch (debug output is the PARITY build; the
legacy "P9 integrated trace log" input in USER is inert), text DIS/DEL/WIP
markers on the chart, EQ-high/low and internal/external labels (present in
the Python evidence). The P5 weights and permission bands are USER constants
with unchanged values (3/3/2/1/1/1/1/1, 45/65, extreme-volatility downgrade on).

## 1. What RC4 adds (author decisions 2026-09-19)

| area | rule (host / chart timeframe, causal, append-only) |
|---|---|
| Range | BTRC RANGE rule: >= 3 CHOCH in the last 4 structure transitions; high / low = the extreme levels those breaks broke; midpoint; ends at the first later BOS or is superseded |
| Liquidity | swing highs / lows, equal-level clusters, trendlines, range high / low; BUY-side above, SELL-side below; INTERNAL / EXTERNAL vs an active range |
| Sweep | WICK_SWEEP (trade through, close back) or CLOSE_THROUGH_RECLAIM (close through, close back within 3 bars); an unreclaimed close-through is an accepted break (level consumed, no sweep) |
| BTMM DISTRACTION | a sweep of approach-path liquidity (sell-side above a bullish POI / buy-side below a bearish POI) after the POI became available and before the touch bar |
| BTMM DELAY | after first entry: >= 2 consecutive closes inside the zone, or >= 1 re-entry |
| BTMM WIPEOUT | trade beyond the far edge by more than the BTMM overshoot tolerance, reclaim within 3 bars, then departure; no reclaim = TRUE FAILURE (reported as INVALIDATED) |
| Interaction episode | after the first touch the POI stays in P5 / P8 for 5 bars (BTMM reaction window) or until a true failure; P3 still records the touch |
| Location | range: correct third 75 / middle 35 / wrong side 20; trend: retracement of the POI's own origin impulse <50 → 40, 50–61.8 → 65, 61.8–79 → 80, >79 → 55; none → 50; +15 for an approach-side sweep (cap 100) |
| P5 | 18 canonical types only: BTMM score 85 (action) / 55 (setup only) / 25 (none) — a score, not a gate; liquidity component = location. Weights and permission bands unchanged |

Period / liquidity reference levels (types 19–32) keep RC3 P5 exactly.
All values are provisional and were never tuned on outcomes.

## 2. Correctness

| check | result |
|---|---|
| RC4 unit tests (`tests/unit/test_rc4_market_framework.py`, 19) | pass |
| RC4 interaction-episode matrix (`tests/unit/test_rc4_interaction_episode.py`, 17) | pass |
| RC4 Pine source contract (`tests/unit/test_rc4_pine_sources.py`, 8) | pass |
| full suite (`--ignore=tests/unit/test_v1a_m5_materiality.py`) on `e228c5d` | **4 919 passed, 0 failed** (exit 0); bot branch `tests/bot` 73 passed |
| ruff (src + RC4 files) / mypy src / git diff --check | all clean / no issues in 144 files / clean |
| no-lookahead | unit: a past assessment is unchanged by future candles; Pine and Python both evaluate on confirmed bars only |
| determinism | repeat bounded runs identical; aligned replay period digests P3 `946b6a9c…`, P5 `e72e6f97…`, P8 `9d24dd57…` |
| incremental = batch | RC3 kernel contract unchanged. RC4: the append-only tracker (incremental) equals a from-scratch batch sweep timeline for every swing-level sweep on real FXCM M15 data (`test_rc4_incremental_equals_batch_for_unrevised_levels`); for levels that P1 later revises (equal-level growth, trendline re-fits) the RC4 contract is first-seen / never-repaint by design, so batch equality is not claimed there |

## 3. Python ↔ Pine parity (RC4 profile, real FXCM data)

Capture `artifacts/rc4_aligned/pine_m15_run1.csv` (sha256 `772ab9d7…`),
PARITY build v1 (saved source `127f775c…`), FX:XAUUSD M15 host window
2026-08-24 07:00 → 2026-09-18 20:30 (1 800 bars). Six same-session OHLC exports
selected by RUNMETA count + checksum. Level-A replay 500 host bars with `--rc4`.

| stage | compared | mismatches |
|---|---|---|
| P3 | 108 POIs | 0 |
| P5 | 1 874 rows / 300 bars | 0 |
| P8 | 471 events | 0 payload, 0 ordering |

RC4 exercised inside the window: BTMM score 85 on 1 191 rows and 55 on 683;
location scores 20 / 35 / 40 / 50 / 55 / 65 / 70 / 75 / 80 / 90 / 95 all
present (range, trend and sweep-bonus paths).

## 4. TradingView builds

| build | saved version | saved source sha256 | compile |
|---|---|---|---|
| USER `[RC4 MARKET FRAMEWORK]` | v14 | `1279474b…` | OK (under the 100 256-token limit) |
| PARITY `[RC4 PARITY]` | v1 | `127f775c…` | OK |

Generated deterministically by `tools/rc4_pine_build/build_rc4_pine.py` from
the frozen RC3 builds (byte-identical regeneration).

Live acceptance (USER v14 on FX:XAUUSD): M1, M5, M15, H1, H4, D1, W1 all complete
with no runtime error. Display switches verified on M15 by counting drawn
objects: all layers off → 0 lines / 0 labels; on → market structure
(BOS / CHOCH / SH / SL), range (high, low, dotted midpoint), trendline,
liquidity pools (BSL / SSL) and sweeps drawn; Dashboard and POI table toggle
independently; 18 per-type switches present.

## 5. Bounded backtest (analytical counts only)

FXCM V1-A dataset from 2026-08-09 22:00 (in-sample; the sealed out-of-sample
range was never replayed). Final decision per POI; "core" = the 18 canonical
types. H4 120 already spans the whole in-sample dataset (to 2026-09-04), so no
longer H4 window exists; H1 500 was stopped as optional (deadline).

| run | window | POIs raw / core | TREND / RANGE | Fib <50 / 50–61.8 / 61.8–79 / >79 | DIS / DEL / WIP / MULTIPLE (reason) | P5 WATCH / BUY / SELL / COUNTER | P8 ACT / BTMM / ENTER / LOST / TERM |
|---|---|---|---|---|---|---|---|
| M15 120 | 08-09 → 08-11 | 269 / 143 | 141 / 0 | 19 / 8 / 23 / 91 | 79 / 14 / 7 / 25 | 143 / 78 / 5 / 39 | 141 / 125 / 159 / 76 / 59 |
| M15 300 | 08-09 → 08-13 | 503 / 323 | 178 / 145 | 44 / 31 / 43 / 60 | 95 / 58 / 15 / 77 | 227 / 144 / 5 / 123 | 375 / 255 / 643 / 494 / 225 |
| M15 500 | 08-09 → 08-17 | 754 / 476 | 401 / 75 | 79 / 50 / 75 / 197 | 108 / 78 / 29 / 138 | 362 / 206 / 5 / 177 | 626 / 369 / 965 / 754 / 378 |
| H1 120 | 08-09 → 08-17 | 600 / 336 | 334 / 0 | 78 / 36 / 64 / 156 | 87 / 31 / 31 / 98 | 294 / 157 / 4 / 141 | 474 / 255 / 436 / 275 / 219 |
| H1 300 | 08-09 → 08-26 | 1 184 / 683 | 549 / 134 | 187 / 66 / 120 / 176 | 107 / 66 / 53 / 251 | 530 / 313 / 4 / 333 | 1 058 / 512 / 1 319 / 1 002 / 563 |
| H4 120 | 08-09 → 09-04 | 1 405 / 720 | 459 / 261 | 121 / 39 / 66 / 233 | 110 / 29 / 80 / 268 | 663 / 256 / 0 / 472 | 1 293 / 512 / 1 015 / 759 / 550 |

All 18 canonical types occur across the runs (fewest: B2S 6, S2B 10,
SELL_ORDER_BLOCK 20). Reports: `artifacts/rc4_backtest/<run>/report.json`.

## 6. Dry-run bot (paper only)

Branch `bot-dryrun-integration` `c5199d5`: final scanner `e228c5d` merged, pin
`e228c5d` (fingerprint of 160 imported scanner files `c0d4bb15…`; mismatch
refuses to run), context lookback **inherited from the scanner authority
(250)** — the old bot default of 40 starved the D1 / W1 context and produced
zero actionable permissions (regression tests added). No broker code
(`LiveBrokerDisabled`). 73 bot tests pass.

Final paper replay 2026-08-10 → 2026-08-12 (276 M15 bars, default config):
paused at bar 100, restarted in a new process (100 bars rebuilt, digests
verified), completed; health OK. 532 PERMISSION_ENTERED_ACTIONABLE events →
532 trade intents / signals, 42 paper orders (the rest skipped by the practice
risk policy: concurrency / existing exposure), 1 closed paper trade. Each
intent carries symbol, time, POI type / source timeframe / zone, framework,
range position or Fibonacci bucket + retracement, sweep-before-POI, BTMM
reason, interaction episode, P5 score, permission, P8 event id, paper entry /
stop / target and result (`artifacts/bot_final_rc4_explain.csv`). These are
plumbing checks of a practice policy, not a strategy result.

## 7. Performance

Python bounded replay, same window, M15 120 bars: RC3 profile 39 s, RC4
profile 44 s (+13 %); M15 300 bars RC4 207 s. Aligned 500-bar replay 10 min.
No optimisation was applied, so no digest-identity re-verification was needed.
Pine: all seven hosts complete within TradingView's limits.

## 8. Known limits

* Parity is proven on one M15 capture (first 300 P5 bars / 500 replay bars,
  where Pine's 300-bar analytical window equals full history). Later bars can
  in principle differ where an equal-level cluster or trendline anchors on a
  swing older than the 300-bar window; not measured.
* Fibonacci / range-third boundaries are compared in float64 (Pine) vs
  Decimal (Python); an exact-boundary tie could differ (same disclosure as P5).
* The USER build sits just under TradingView's token limit; further features
  need compaction first. The P5 weights / bands are constants in USER.
* The bot's default context lookback (40) should be raised to 250 for demos.
