# BTRC V1 — P3 POI CORE — CLOSURE

**Status: P3 POI CORE — CLOSED.**
Not "P3 closed": the CONTEXT half remains deferred (see *Deferred work*).

P3 ports the Python POI engine — detection, persistent identity, and the
persistent lifecycle — onto Pine v6, and proves the port against the Python
production oracle on real market data captured in the same Pine execution.

## What closed

| | |
|---|---|
| CORE POI types | **18 / 18** (the lifecycle-eligible set) |
| Detector families | **9 / 9** real-data hash parity |
| Lifecycle fields | **7 / 7** real-data hash parity |
| Registry / active / terminal | **959 / 156 / 803** — all exact |
| Overall digests | **H1 925825366**, **H2 836263421** — both exact |
| TradingView runtime | **72 / 72**, zero Pine faults |
| Python replay | byte-identical across two fresh processes |

P1 measurements and P2 structure are **unchanged**; the P3 correction lands
after the 2281-line P2 semantic prefix, so `P2_REVALIDATION_REQUIRED = FALSE`.

## The finding this phase turned on

Production `run_poi_lifecycle` (`poi/lifecycle.py:164-170`) starts a POI at the
first candle whose availability is later than **the POI's own availability**,
and `_compute_freshness_and_taps` counts taps from that same index. Production
has **no notion of when an engine happened to discover a POI**.

Pine had been starting a newly registered POI at the bar the registry first saw
it. For the sixteen candle-derived CORE types those two bars coincide, so the
difference was invisible — which is exactly why eight of nine families matched
while one did not.

Reference zones are the exception. They are a projection of P1's published S/R,
and a zone whose origin is outranked by an earlier same-direction pivot stays
invisible to the bounded window until that blocker leaves the scan range. The
window can therefore hand P3 a zone whose availability is already well in the
past.

**The invariant, now frozen:**

> Semantic availability is authoritative. Engine discovery is implementation
> timing. Late discovery must not erase lifecycle history, and discovery time is
> diagnostic only — never part of POI identity or canonical state.

### Why bounded backfill is legal

A blocked origin resurfaces only once the blocker leaves `[T-W+1+R, T-R]`, i.e.
at `T = A + W - R`. With the confirmation `C > A`, the delay `A + W - R - C` is
strictly **less than the window**, at most `W - 4` (296 at W=300). The bar the
lifecycle must start from is therefore always still retained, which is what
makes exact backfill possible rather than an approximation.

The derivation predicted the observed long-delay case exactly: blocker end 735,
confirmation 879, predicted discovery **1033** — which is what the data showed.

Real-data distribution over the frozen 1799-row context: **13 reference zones —
10 at zero delay, and 3 delayed by 1, 2 and 154 bars.**

## Corrections in this phase

| Commit | What |
|---|---|
| `b03b466` | `fix(poi): keep the S/R detector inside the injected ATR` — **parity tooling only.** The replay called `detect_support_resistance_zones` outside `injected_atr`, so it measured a cold-started 300-bar ATR while production (full history) and Pine (`wAtr`) both use the continuous one. Its reaction gate reads those values directly. |
| `be1df56` | `fix(pine): start a late-seen POI at its own availability` — **the one real Pine defect.** `f_poiAdvanceAllLifecycles` now scans the retained window for the first qualifying bar and replays the tap subsystem over the skipped range, guarded so an empty range cannot run backwards (a Pine `for` counts *down* when `to < from`). |
| `7c7871a` | `test(poi): measure the reference-zone backfill against production` — 32-case campaign at delays 1, 2, 10, 50, 100, 154, 250, 295, 296, both directions, five confirmation points. |

Neither correction touched production Python, P1, or P2.

## Evidence

Same-execution atomic capture, anchor **1788214500000**, FX:XAUUSD M15,
account `bellcare1994`, layout `bellforex`.

The capture emitted **1799 confirmed rows** from **1800 Pine execution bars** —
correct, not short: the 1800th bar was still forming and the closed-bar rule
excludes it. Indices 0..1798 with no gaps, 36 chunks, zero failure records.

Canonical sources (committed LF blobs):

- P3 DEV `031b723afc7c79090f0c7f89f93c43944d4eef9e8fcb7d06e443a0dc6a52c4c2`
- P3 ATOMIC `c406f0987b1d74f10fbb7f9f1a966671e6268ce740eea7bdf6c7e266a9b83d12`

Artifacts are gitignored by policy; their SHA256 values are recorded in
`artifacts/p3_parity/P3_CORE_CLOSURE_EVIDENCE_1788214500000.txt`.

## Runtime

72/72 definitive observations — 6 timeframes (M1, M5, M15, H1, H4, D1) × 2 debug
modes × 3 actions × 2 repetitions. Zero Pine failures, zero RE10110, zero
runtime/array/history/object errors. Every observation was read from the study's
model object and required to settle before being recorded, not judged from a
screenshot.

## Deferred work

**P3 CONTEXT remains DEFERRED** — EQH, EQL, and the 12 calendar/period-level
context types. These are context-only (not lifecycle-eligible) and are not
consumed by the CORE contract closed here.

## Engineering notes worth keeping

- **Account vs layout.** The TradingView *account* is `bellcare1994`; `bellforex`
  is the *layout name*. Gating on a username "bellforex" is wrong and cost real
  time.
- **History depth.** A fresh chart gives Pine only ~1036 M15 bars, and synthetic
  mouse events do not pan it. Use the chart model API:
  `timeScale().setBarSpacing(minBarSpacing())` then repeated `scrollToFirstBar()`
  until `study.data().size()` reaches the target. Verify with Pine evidence,
  never visually.
- **`study.restart()` wedges the study** (`restarting=true`, `bars=0`,
  unrecovered). Use `setSymbol(<same>)` for a clean reinitialisation.
