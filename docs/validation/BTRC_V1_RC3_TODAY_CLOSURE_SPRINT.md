# BTRC V1 — RC3 today closure sprint (2026-09-16)

Branch `rc3-highram-continuation`, continued from `bfaefe7` (no reset). No
future-day waiting: every "N trading days" requirement was met by replaying
already-completed historical days. **RC3 is not production-approved.**

## 1. Future-day waiting removed

Four shell loops whose only behaviour was polling for "ten trading days"
(`until manifest has 11 lines … sleep 30`) were stopped. The real Level-A
computation (V1-A authority replay) was kept running.

## 2. The comparison was redesigned so it compares one runtime context

The earlier blocker (`BTRC_V1_RC3_HIGHRAM_CONTINUATION_STATUS.md` §5d) was that
the Level-A authority and a live Pine run differ in host, execution window,
initial state, context depth and feed snapshot. Each difference is now removed
mechanically, not assumed away:

| difference | how it is removed |
|---|---|
| host | the formal Pine capture is on **M15**: an H4-aligned replay would replay host bars inside the sealed out-of-sample range, which the validation lock forbids |
| execution window / initial state | the PARITY build logs `RUNMETA` (log-only, default-off): first/last confirmed host bar, count, OHLC checksum |
| context depth | `RUNMETA` records the same four values for every `request.security` context (1250 confirmed bars each) |
| feed snapshot | same-session OHLC export of all six timeframes (`tradingview/btmm_ohlc_exporter.pine`); the replay selects exactly the RUNMETA bars and **proves** them by count and checksum |
| P5 log volume | `P5C` compact stream for a bounded run-bar range, emitted in the SAME run as `P3LIFE` and `P8EVENT` (separate runs slide the window) |

Capture `artifacts/rc3_aligned/pine_m15_run1.csv` (sha256 `ef228c75…e526`),
PARITY DEV v4, FX:XAUUSD M15: one execution, 6 536 log lines (under the buffer
cap) — `RUNMETA` ×1, `P3LIFE` ×953, `P8EVENT` ×5 197, `P5C` run bars 0–299.

Verified window (all six exports match RUNMETA exactly; checksum deltas are
≤ 6e-8, i.e. print-rounding on 2-decimal prices):

| window | first bar (UTC) | bars |
|---|---|---|
| host M15 | 2026-08-19 19:15 | 1 799 |
| W1 / D1 / H4 / H1 / M5 contexts | 2002-09-22 / 2021-11-16 / 2025-11-24 / 2026-07-01 / 2026-09-09 | 1 250 each |

The M15 `request.security` context is the host series itself (identical first
bar, count and checksum). Higher-timeframe context bars dated inside the sealed
calendar range exist only as background history, exactly as Pine itself uses
them; no host bar is in that range (the loader refuses one) and nothing about
those bars is reported.

## 3. Level-A harness defect found and fixed (not a scanner or Pine defect)

The first aligned comparison showed a host-only P5 difference at the 21:00 UTC
host bar (`sRegime` 40 vs 90). Root cause: the Level-A CSV loader derived
candle availability as `open + fixed duration`, but FXCM bars end at the session
close — D1 runs 22:00 → 21:00 UTC, the last H4 bar of a session is 3 h, W1 closes
Friday 20:45. Session-end context bars were visible to Level A late. Pine
switched its D1 trend/regime exactly at the bar's real close.

`load_v1a_csv` gained an optional `close_time_ms_by_open_ms` (the broker's real
close); omitted, the frozen fixed-duration rule is unchanged so every published
V1-A digest reproduces. The aligned loader feeds TradingView `time_close`. The
host-only difference disappeared on re-run.

**Disclosure:** the V1-A continuous authority (`artifacts/rc3_authority/`)
still uses the frozen fixed-duration rule, so its session-end context
visibility is late by up to the session gap. It remains a continuity /
determinism authority; it is not the parity authority.

## 4. Parity results (aligned Level A vs corrected Pine)

Aligned Level A through 466 host bars (2026-08-19 19:30 → 2026-08-26 close,
5 complete trading days + the partial first day); P5 on the 300 `P5C` bars.

| | POIs / rows / events | Python-only | Pine-only / missing | value mismatches |
|---|---|---|---|---|
| **P3** | 228 matched | 0 | 0 | 196 — all `effective_timeframe` on promoted POIs |
| **P5 host-only POIs** | 104 rows | 0 | 0 | **0** |
| **P5 promoted POIs** | 2 715 rows | 0 | 0 | 10 961 |
| **P8 host-only POIs** | 111 events | 0 | 0 | **0** payload; ordering only (class B) |
| **P8 promoted POIs** | 1 301 events | 41 extra | 652 missing | 208 payload |

P8 structural invariants on the Level-A side: duplicate terminal 0, missing
terminal_reason 0, terminal-before-activation 0.

**Promotion is not an edge case:** 223 of the 228 matched host POIs were promoted
by Level A (W1 80, D1 53, H4 72, H1 18). Class A therefore decides P3/P5/P8
closure for the M15 host.

## 5. Divergence classes (automatic first-divergence)

**A. Cross-timeframe merge promotion — author decision required.**
Production Python (`poi/overlap.py resolve_merges`) promotes a host POI's
`effective_timeframe` to an overlapping same-type, same-direction POI on a
higher timeframe (observed M15 → H4 / D1 / W1). `t5_engine` keys T3 (and the
T4 suitability) on `effective_timeframe`, so the promoted POI is scored on the
parent timeframe's context. The Pine registry is single-timeframe by
construction and cannot see the parent, so it scores the same POI on the host.

First divergence: **2026-08-19 20:30 UTC, stage P5, Pine POI 0 (BUY ORDER
BLOCK 4505.04–4512.02), `sMomentum` Python 100 / Pine 50** (also `sBreakout`
90/0, `sVolatility` 60/100, `final` 76/68). At 21:00 UTC the same POI's
permission differs (Python WATCH ONLY / Pine BUY BIAS) and Python emits a
`PERMISSION_LOST_ACTIONABLE` that Pine does not.

**B. Same-bar native index order — contract clarification required.** When
several POIs are first evaluated on the same bar, each system numbers them in
its own registration order (Pine: order block 0, engulfing 1, base rally 2;
Python: engulfing, base rally, order block). Event identity, payload and
per-POI priority order agree; the cross-system bar-level sequence does not.

## 6. Visual / runtime acceptance (USER DEV v15, FX:XAUUSD)

- Compiles (99 319 tokens, 937 headroom); no runtime failure on **M1, M5, M15,
  H1, H4, D1, W1**; `TF?` labels = 0 on all seven.
- Boxes render with centred text; bullish types green (`#4CAF50`), bearish red
  (`#F23645`) — checked by decoding every box's colour on H4, M5 and M1.
- No text pile: on H4 no two labelled boxes share a price band.
- S/R left edge = origin swing: a live D1 SUPPORT ZONE starts on the candle
  whose low is the zone bottom (M5 resistance zones originate before the
  chart's in-memory bars, so their edge could not be read there).
- The P7 table renders the compacted header/rows correctly; its nearest rows
  (975–977 BULL) are the POIs behind the nearest box (BUY ORDER BLOCK +
  BULLISH ENGULFING twin group). The table lists the whole eligible engine set
  (42); boxes show the fresh subset capped at 8 groups — the documented design.

## 7. Status

- P3 / P5 / P8 parity: **NOT CLOSED.** Exact for every POI outside class A
  (apart from class B ordering); class A needs an author decision.
- Bot: `bot-dryrun-v1` (paper only, live broker impossible) pushed.
- Event demo package: `release/event_demo_rc3_20260916/`.
- Full suite 4 710 passed / 0 failed / 0 skipped; ruff, mypy, diff-check clean.
- Production approval: **FALSE.**
