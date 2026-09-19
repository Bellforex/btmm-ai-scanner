# BTRC V1 — RC4 Market Framework: seminar candidate evidence

Status: **RC4 EVENT / DEMO candidate**. Not production. Not merged to `main`.
Not published on TradingView. No live broker. No profitability claim: every
number below counts analytical states, never trade outcomes.

Branch `rc4-market-framework` (from RC3 freeze record `d96db40`; RC3 semantic
SHA `3f9f790` untouched). Bot: branch `bot-dryrun-integration`.

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
| RC4 Pine source contract (`tests/unit/test_rc4_pine_sources.py`, 8) | pass |
| full suite (`--ignore=tests/unit/test_v1a_m5_materiality.py`) | exit 0 on the Python RC4 commit; bot branch 4 786 passed / 179 skipped / 0 failed |
| no-lookahead | unit: a past assessment is unchanged by future candles; Pine and Python both evaluate on confirmed bars only |
| determinism | repeat bounded runs identical; aligned replay period digests P3 `946b6a9c…`, P5 `e72e6f97…`, P8 `9d24dd57…` |
| incremental = batch | RC3 kernel contract unchanged. The RC4 framework is defined incrementally (append-only, first-seen levels never retracted, so it never repaints); a separate batch-rebuild equivalence is **not** claimed |

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

Live acceptance (USER on FX:XAUUSD): M1, M5, M15, H1, H4, D1, W1 all complete
with no runtime error. Display switches verified on M15 by counting drawn
objects: all layers off → 0 lines / 0 labels; on → market structure
(BOS / CHOCH / SH / SL), range (high, low, dotted midpoint), trendline,
liquidity pools (BSL / SSL) and sweeps drawn; Dashboard and POI table toggle
independently; 18 per-type switches present.

## 5. Bounded backtest (analytical counts only)

FXCM V1-A dataset, window from 2026-08-09 22:00 (in-sample; the sealed
out-of-sample range was never replayed). Final decision per POI.

| run | POIs | DISTRACTION | DELAY | WIPEOUT | TRUE FAIL | RANGE / TREND | P8 BTMM_VALIDATED | P8 ENTERED_ACTIONABLE |
|---|---|---|---|---|---|---|---|---|
| M15 120 | 269 | 83 | 37 | 32 | 5 | 0 / 141 | 125 | 159 |
| M15 300 | 503 | 130 | 134 | 82 | 33 | 145 / 178 | 255 | 643 |
| H1 120 | 600 | 115 | 132 | 123 | 39 | 0 / 334 | 255 | 436 |
| H4 120 | 1 405 | 166 | 304 | 337 | 138 | 261 / 459 | 512 | 1 015 |

Reports: `artifacts/rc4_backtest/<run>/report.json`. The 500-bar runs were
still in progress when this record was written.

## 6. Dry-run bot (paper only)

Branch `bot-dryrun-integration` (`9e3f22c`), pinned to scanner `a15c199`
(fingerprint of 160 imported source files; mismatch refuses to run). Live
broker: **none** (`LiveBrokerDisabled`). 71 bot tests pass; crash / restart
rebuild reproduces identical digests.

Replay 2026-08-10 with `--context-lookback-bars 250` (the authority default;
the bot's own default of 40 starves the D1 / W1 trend context and produced no
actionable permission): 92 bars, 24 PERMISSION_ENTERED_ACTIONABLE events
consumed, 12 trade intents, 5 paper orders, 1 closed paper trade. These are
plumbing checks, not a strategy result.

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
