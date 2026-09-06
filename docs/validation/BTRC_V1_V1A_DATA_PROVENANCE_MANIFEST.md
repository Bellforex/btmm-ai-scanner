# V1-A — Data Provenance Manifest

Frozen before any aggregate outcome was examined. Every file below is
gitignored (`artifacts/`) real market data — this document is the
committed, permanent record of what it is, where it came from, and its
exact hash, per the project's existing convention for real captures.

## Acquisition method

Extracted directly from the TradingView chart's own main-series data
(`window._exposed_chartWidgetCollection` → active chart widget → `model()
.mainSeries().bars()`), independent of any Pine script's `calc_bars_count`
— this is the underlying provider feed, not a Pine-computed series. Full
available history was force-loaded via repeated
`timeScale().scrollToFirstBar()` calls (with `setBarSpacing(minBarSpacing
())` first) until `bars.size()` stopped growing across three consecutive
attempts, then every bar in the loaded range was walked via `bars.valueAt
(i)` and exported as `time,open,high,low,close,volume` (epoch-ms) through
a genuine browser download (`Blob` + object URL + a real `<a download>`
click — not an artifact-sandboxed download). Never fabricated, never
interpolated: every row is a value the provider itself returned.

Chart: `6cu1b2O7` (`bellforex` layout). Provider: **FXCM**. Symbol:
**XAUUSD** (ticker `FX:XAUUSD`).

## Files

| File | Timeframe | Rows | First bar (UTC) | Last bar (UTC) | SHA-256 |
|---|---|---|---|---|---|
| `v1a_raw_ohlc_full_loaded.csv` | M15 | 6406 | 2026-05-31T22:00:00 | 2026-09-04T20:30:00 | `9f5322c3ba82eaf667f7bfef6a2c111670c4152f33d9c7cc824e0a3fa69c9029` |
| `v1a_raw_ohlc_W1.csv` | W1 | 2754 | 1970-02-22T23:00:00 | 2026-08-30T22:00:00 | `dc8a061392e586b447ff0858000dd35e8b6150a8fa1dcee931c871f08f3d3ae7` |
| `v1a_raw_ohlc_D1.csv` | D1 | 901 | 2023-03-13T22:00:00 | 2026-09-03T22:00:00 | `e9ed832c6316ca48d823b83bce658cac2b7e41ce1dff79b12d1f57164efe50e0` |
| `v1a_raw_ohlc_H4.csv` | H4 | 5685 | 2023-01-02T23:00:00 | 2026-09-04T18:00:00 | `f3789b1020fabca317a2ceb0d2dfa00c065d3db7f8ff177b0b2626c704e84a57` |
| `v1a_raw_ohlc_H1.csv` | H1 | 9927 | 2025-01-02T05:00:00 | 2026-09-04T20:00:00 | `44bf23f8e43c83f937188c9f380e93932e1132231797e5f5bdd2df55a02a84d2` |

All under `artifacts/v1a_validation/`.

## Data quality (verified directly, not assumed)

For every file above: **0 duplicate timestamps, 0 non-monotonic steps, 0
OHLC consistency violations** (`low <= open,close <= high` for every
row). M15 step-size histogram: 6335 bars at the expected 15-minute step,
57 at 75 minutes (5×, short intraday gaps), 11 at ~49.5 hours (weekend
closures), 2 slightly longer (holiday-adjacent weekends) — all consistent
with genuine FX market-hours behavior, no corruption signature.

## M5 — deliberately excluded from this cycle's characterization window, with evidence

A sixth file, M5 candles, was also extracted and force-load-tested the
same way. Its available history plateaus at **2026-08-09T22:00:00 UTC**
(5508 bars) — genuinely shorter than M15's depth on this same feed, and
**later** than the boundary below. M5 is therefore NOT usable as a
BTRC-context input for the fresh characterization window (§ below),
since no M5 data exists that far back. This was verified empirically (six
repeated force-load attempts, stable at the same boundary) before being
treated as a real constraint, not assumed from a first attempt.

This is not a blocking gap: `btrc.trend_engine.assess_trend`
/`regime_engine.assess_regime` (`src/btmm_ai_scanner/btrc/trend_engine.py:
295-297`, `regime_engine.py:114-136`) iterate only over whatever
timeframes are actually present in the `ScannerAnalysis` snapshot and
skip any timeframe with no data — no forced requirement for all six
`_AUTHORITY_TIMEFRAMES`, and M15/M5/H1 are not in the "authority" set
used for trend confirmation anyway (`trend_engine.py:345`: authority =
`{W1, D1, H4}` only). V1-A's per-bar BTRC scoring therefore supplies
**W1, D1, H4, H1, M15** (five of six) and omits M5, which degrades the
confluence context only marginally (one fewer non-authority timeframe in
the global-direction resolution mix) rather than invalidating it.

## Already-used development/parity window — excluded from characterization

Every prior P2–P9 real-data capture in `artifacts/` falls between
**2026-08-03T07:00:00 UTC** (earliest OHLC row across all atomic-context
captures) and **2026-09-06** (today). This window is reserved for
harness pipeline-sanity validation only (V1-A Phase 44) — it must never
be used to draw a characterization conclusion, since it is not a
blind/unseen sample of the scanner's own behavior in the sense this
program requires.

## Frozen chronological split (before any aggregate result was examined)

The **fresh** M15 window — every bar strictly before the already-used
boundary above — is split 70/30 by bar count, earliest-first:

| Set | Bars | Start (UTC) | End (UTC) |
|---|---|---|---|
| **DEV / characterization** | 2903 | 2026-05-31T22:00:00 | 2026-07-14T17:00:00 |
| **OOS holdout** | 1244 | 2026-07-14T17:15:00 | 2026-08-03T06:45:00 |

Split rule: `split_idx = round(0.70 * n_fresh)`, `n_fresh = 4147`, giving
`split_idx = 2903`. No shuffling — pure chronological order preserved.

**The OOS set is LOCKED as of this commit.** It is not opened, summarized,
plotted, or inspected in any way during V1-A characterization. Its own
row count and hash are recorded here specifically so a later session can
verify it was never touched: OOS is M15 bars 2903..4146 (0-indexed) of
`v1a_raw_ohlc_full_loaded.csv`, i.e. every row with
`1780264800000 + ... ` — precisely, every row with `time >= 1784136900000`
(2026-07-14T17:15:00 UTC) `AND time < 1785740400000` (the already-used
boundary).

## Symbol/timeframe scope note

This manifest and V1-A characterization use **XAUUSD only**. EURUSD/GBPUSD
were explicitly out of scope for P10's optional smoke test and remain out
of scope here — no data for either was acquired this cycle.
