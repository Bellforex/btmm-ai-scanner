# BTRC-V1 P5 — BTRC Confluence Engine: CLOSURE

Status: **P5 BTRC CONFLUENCE — CLOSED (wire-normalized)**
Branch: `pine-p4-btmm`
Closed: 2026-09-04

---

## 1. Parity authority — read this section before any other claim below

Per the governing instruction for this phase, **the parity authority for
this closure is PINE ↔ WIRE-NORMALIZED PYTHON**, not Pine ↔ original
high-precision Python:

> **PINE ↔ WIRE-NORMALIZED PYTHON: VERIFIED**
> **HIGH-PRECISION PYTHON ↔ PINE UNIVERSAL DECISION PARITY: NOT ESTABLISHED
> / FALSE, DUE TO A DOCUMENTED WIRE LIMITATION**

The two claims are deliberately kept separate below and must never be
collapsed into one "exact parity" statement. Section 5 is the wire-normalized
proof; Section 6 is the high-precision disclosure it does not resolve.

## 2. The frozen contract

```
Active-POI loop        eligible iff NOT terminal, or terminal on EXACTLY
                        this bar (one-time final evaluation) — new Pine-side
                        orchestration, not a source port (assess_confluence
                        stays single-POI-in/single-result-out in production)
Weights (provisional)  BTMM 3, POI 3, Trend 2, Regime 1, Momentum 1,
                        Breakout 1, Liquidity 1, Volatility 1
Bands (provisional)    watch-only >= 45, high-confluence >= 65
Extreme-vol downgrade  enabled by default (BUY/SELL -> WATCH_ONLY on EXTREME)
Wire (unchanged)       the same closed P6 26-field P5TransportExt, read for
                        exactly the four contexts T1/T5-global/T3/T4 use
                        (D1, W1, H4, M15) — zero new request.security calls
```

Weights and bands remain **ENGINEERING-PROVISIONAL**: nothing in this
closure claims calibration optimality, profitability, or production
approval. See [`BTRC_V1_P5_COMPLETION_MATRIX.md`](BTRC_V1_P5_COMPLETION_MATRIX.md)
for the full Python-side, pre-Pine sufficiency proof (17 rows, all ✅) this
closure builds on.

## 3. Two Pine scripts, one contract

* **P5 DEV** (`tradingview/btmm_poi_btrc_scanner_p5_dev.pine`, 5742 lines,
  `sha256 312994af…`) — the production-shaped script: P6 DEV's closed
  foundation plus T1–T5 and the active-POI loop, debug-gated `P5EVAL`
  logging only, zero new plots.
* **P5 ATOMIC PARITY** (`tradingview/btmm_poi_btrc_scanner_p5_atomic_parity.pine`,
  5796 lines, `sha256 4d50b16c…`) — P5 DEV plus one additive block:
  `f_p5WireExt`/`P5WIRE`, an unconditional per-confirmed-bar log of the same
  D1/W1/H4/M15 wire already in scope, joinable to that bar's `P5EVAL` rows by
  `bar=`. Built because the existing `P5X` emitter (already closed, 156/156
  real parity) fires once per script **restart**, not once per bar — fine for
  a live smoke check, insufficient to pair a specific bar's wire inputs to
  that bar's decision for a real replay.

Both compile with 0 errors. Resources: **6** `request.security` calls
(unchanged from P6 DEV — the four contexts P5 reads were already requested;
none are new), **61** `plot`-family calls (well under the 64 limit; P5 itself
adds none — all P5 output is `log.info`), confirming the additive design
never touched P6's resource budget.

## 4. Real FXCM runtime — the capture

```
feed              FX:XAUUSD (FXCM), bellforex layout, M15
script             BTMM + POI + BTRC Scanner [P5 ATOMIC PARITY]
capture file       artifacts/p5_capture/p5_atomic_raw_log.csv (gitignored)
P5WIRE bars        105  (one script-restart's worth of confirmed-bar wire)
P5EVAL bars        106
P5EVAL rows        9,634  (after collapsing byte-identical duplicate
                    emissions from the log's own reload/tick re-render —
                    see `p5_atomic_capture_log.py`'s dedup note)
distinct POIs       142
parse/field errors  0
```

Every `P5WIRE` bar has a matching `P5EVAL` bar (0 mismatches); the single
extra `P5EVAL` bar with no `P5WIRE` counterpart is the oldest bar in the
capture, whose `P5WIRE` line rolled out of TradingView's ~10,000-line log
ring buffer before download — not a parity failure, a buffer-capacity
artifact, and excluded from the replay (only bars with both a wire and an
eval side are compared).

This capture spans real reload/attach/settings-toggle cycles across this and
the prior session (fresh attach, live-log verification, chart reload, M5
switch, M15 switch-back, ATOMIC-twin creation and re-attach) — 106 distinct
confirmed-bar observations and 9,634 distinct POI-evaluation observations,
both well past the 72+ FXCM runtime observation requirement.

## 5. Wire-normalized real parity — the proof

`tests/parity_support/p5_wire_normalized_replay.py` reconstructs, from
**only** a captured `P5WIRE` line, every T1 (×3 contexts)/T2/T3-momentum/
T3-breakout/T3-pullback/T4-session/T5-global decision using the SAME
already-proven-sufficient pine-model functions this campaign differential-
tested against production (`t1_trend_pine_model`, `t2_regime_pine_model`,
`t3_pine_model`, `t5_trend_pine_model`) — no recomputation from
higher-precision (Decimal) source data anywhere in this path. It
re-encodes every result through the exact Pine integer-code tables
transcribed from the deployed source, so the comparison against a real
`P5EVAL` row is a plain `==`. A second, wire-free layer
(`compute_poi_level`) reconstructs the POI-level aggregator (alignment, all
eight component scores, the weighted final, permission, lifecycle) from
only that row's own already-logged fields, using
`t5_component_scores_pine_model`/`t5_aggregator_pine_model` directly.

`tests/unit/test_p5_atomic_capture_replay_parity.py` runs this against the
real capture:

```
bar-level fields checked     13 fields x 9,634 rows   = 125,242 comparisons
POI-level fields checked     12 fields x 9,634 rows   = 115,608 comparisons
mismatches                   0
global digest (Pine)         H1 351473241  H2 335238294
global digest (Python)       H1 351473241  H2 335238294
digest match                 EXACT
```

The global digest (`tests/parity_support/p5_digest.py`, reusing the P2 dual-
hash primitives unchanged) folds every row's join key
(`bar`, `poiIdx`) plus all 25 decision fields, in (bar, poiIdx) order, from
both Pine's own logged values and the independent Python replay — proving
not just per-field equality but that no row was reordered, dropped, or
duplicated between the two sides.

**What this layer deliberately does not attempt**: T4 volatility
(`p5VolState`/`p5VolAbnormal`/`p5VolSuitability`) is a same-process host
computation over the M15 candle window's own 300-bar ATR history — never
carried on the 26-field MTF transport wire this capture records, so there is
no "wire" for this layer to normalize against. Its logged value is
consumed as an opaque, already-Pine-computed input at the POI level, exactly
how `t5_component_scores_pine_model.volatility_score` treats it in
production (pass-through). This is a scope boundary of what `P5WIRE` was
designed to capture (P5's own frozen contract already classified T4
volatility's wire as "none needed" — see `BTRC_V1_P5_COMPLETION_MATRIX.md`
row 6), not a gap papered over.

## 6. High-precision disclosure — read together with Section 5, never instead of it

Per `BTRC_V1_P5_FLOAT64_BOUNDARY_CLASSIFICATION.md` (exhaustive search,
15,552,000 combinations, project-owner decision 2026-09-04: **accept and
disclose**):

* T1/T2/T3-direction/T3-breakout/T3-pullback/T4/T5-aggregator/
  T5-components/T5-global are all proven **exact** ports of the source,
  operating on the same wire values Pine receives — this is Section 5's
  claim, and it stands.
* T3 momentum's `momentum_score` crosses a genuine Decimal-vs-float64
  boundary at the wire (proven bounded to **at most 1 point**,
  `test_t3_transport_sufficiency.py`). That bounded ≤1-point gap
  provably reaches the 45/65 permission decision in **≈0.135%** of an
  adversarially constructed combination space (21,044 / 15,552,000) — always
  as an exact ±1-point shift, never more.
* Consequently: **high-precision-to-wire canonical decision invariance is
  NOT established.** A real, quantified, bounded residual risk stands,
  disclosed and accepted rather than eliminated. No claim in this document
  or any downstream summary may assert universal decision parity against
  the original high-precision Python pipeline.

## 7. What did not change

No P1/P2/P3/P4/P6 semantics were touched. `C_P1_MIN_CALC_BARS = 1250`,
`calc_bars_count = 1800`, and the P6 26-field transport are all exactly as
closed. The active-POI loop is additive orchestration around
`assess_confluence`, not a modification of it. No `strategy.*` call exists
anywhere in either script. Nothing was published; nothing was pushed;
no broker/order/position-sizing code exists.

## 8. Gate

```
P5_WIRE_NORMALIZED_INPUT_SUFFICIENCY_PROVEN   TRUE   (17/17 completion-matrix rows)
P5_PINE_DEV_COMPILES                          TRUE   (0 errors, both scripts)
P5_ATOMIC_TWIN_CAPTURES_PAIRED_WIRE_AND_EVAL  TRUE   (105/106 bars, 0 join gaps)
P5_BAR_LEVEL_REPLAY_MATCHES_REAL_CAPTURE      TRUE   (125,242/125,242 fields)
P5_POI_LEVEL_REPLAY_MATCHES_REAL_CAPTURE      TRUE   (115,608/115,608 fields)
P5_GLOBAL_DIGEST_EXACT                        TRUE   (H1 351473241 / H2 335238294)
P5_BTRC_WIRE_NORMALIZED_REAL_PARITY           TRUE
HIGH_PRECISION_UNIVERSAL_DECISION_PARITY      NOT TRUE — see Section 6
P5 BTRC CONFLUENCE ENGINE                     CLOSED (wire-normalized)
```

**Not claimed here.** Calibration quality, profitability, or production
readiness of the 3/3/2/1/1/1/1/1 weights or the 45/65 bands. Universal
decision agreement with the original high-precision Python pipeline (Section
6). Any live trading, order, or broker-integration capability — none exists
in either script.

## 9. Addendum — a narrow, later runtime-safety reopen (this closure's own status is unchanged)

`BTRC_V1_P5_HOST_RUNTIME_SAFETY_ADDENDUM.md` (2026-09-05) documents a real,
reproducible `RE10041` crash found when P5's engine (via P7) is attached to
a **non-M15 host chart** (H1 specifically) — a `request.security`/UDT
warm-up timing artifact, not anything wrong with the wire-normalized parity
proven above (which was, and remains, gathered exclusively on an M15 host).
Fixed with five minimal `na(ext)` guard clauses across
`f_p5T1`/`f_p5T2`/`f_p5T3Mom`/`f_p5T3Brk`/`f_p5T3Pb`; every guard resolves
to that same function's own pre-existing "insufficient data" output, adds
no new state, and changes zero already-reachable M15 output — reconfirmed
by re-running this closure's own real-data replay: digest still exactly
`H1 351473241 / H2 335238294`, all 240,850 field comparisons still exact.
**`P5 BTRC CONFLUENCE ENGINE: CLOSED (wire-normalized)` above is unchanged
and unaffected.** This section exists only so a reader following this
document does not need to separately discover that P5 now also carries a
documented, verified H1-host safety fix.
