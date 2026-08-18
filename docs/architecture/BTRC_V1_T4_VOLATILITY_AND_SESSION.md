# BTRC-V1 — T4 Volatility + Session-Context Engines

Status: **T4 implemented** on `btrc-v1`. Two independent, deterministic, contextual
dimensions. **Neither determines direction; neither generates trades.** Code:
`btrc/t4_engine.py`, `t4_assessment.py`, `t4_configuration.py`. Entry points:
`assess_volatility(candles, config?)`, `assess_session(evaluation_time_utc, config?)`.

## Volatility (frozen `VolatilityState`)
Reuses the existing ATR (`measurements/atr.py::compute_atr_series`) and candle-range
(`measurements/candle_metrics.py::total_range` / `median_total_range`) implementations
— it never re-implements ATR. The current candle's total range is ranked within a
trailing `volatility_window` distribution:
- `percentile < 0.10` → VERY_LOW, `< 0.30` → LOW, `< 0.70` → NORMAL, `< 0.90` → HIGH,
  else EXTREME.
- **Abnormal spike:** `current_range >= abnormal_spike_multiplier × rolling_median`
  → `abnormal_spike=True` (reported as `ABNORMAL_VOLATILITY_SPIKE` — a range fact, not
  a claimed fundamental/news cause; no news API is used).
- Insufficient history (`< atr_period` candles) → `NORMAL` default, `percentile=None`,
  `abnormal_spike=False`.
- **No direction inference:** identical ranges with opposite candle direction yield an
  identical volatility state (tested).
- `suitability_score` (0–100, provisional) is **distinct from the level**: NORMAL is
  most suitable (100), EXTREME least (20), VERY_LOW low (40) — EXTREME volatility means
  "lower suitability for new execution", never a direction.

## Session (frozen `SessionContext`)
Derived from the **evaluation timestamp** (never the machine clock) via `zoneinfo`, so
London (BST/GMT) and New York (EDT/EST) DST are correct for every date. Session windows
are expressed in **exchange-local** time and resolved per-date:
- London 08:00–16:30, London pre-open 07:00–08:00 (Europe/London).
- New York 08:00–17:00, NY pre-open 07:00–08:00 (America/New_York).
- Asian: a UTC window (Tokyo does not observe DST).

Deterministic precedence: `LONDON_NY_OVERLAP` (both active) > `NEW_YORK` > **`NEW_YORK_
PREOPEN`** > `LONDON` > `LONDON_PREOPEN` > `ASIAN` > `POST_NY`. NY pre-open is given
precedence over concurrent London active because it always falls inside London's session
and the imminent-NY-open context is the salient one — otherwise `NEW_YORK_PREOPEN` would
be unreachable. `LONDON_NY_OVERLAP` is derived from the actual configured intervals for
that date, so DST shifts (and mismatched DST weeks, e.g. late October when London is on
GMT while New York is still on EDT) never corrupt it (tested).

## Provisional parameters (ENGINEERING-PROVISIONAL, centralized)
`atr_period=14, volatility_window=50, percentile bands {0.10,0.30,0.70,0.90},
abnormal_spike_multiplier=2.5`; session windows and Asian UTC window (22:00–06:00) — all
in `VolatilitySessionConfiguration`. Session opening/pre-open windows are provisional
engineering assumptions, not author-approved trading rules; swept/reviewed in T9.

## Determinism / Pine portability
Both engines are pure functions of their inputs → deterministic, no-lookahead. Pine:
volatility percentile/ATR = **PINE_PORTABLE_WITH_ADAPTATION** (Pine has `ta.atr`, arrays,
`ta.percentile*`); session/DST = **PINE_PORTABLE_WITH_ADAPTATION** (Pine resolves
exchange/session time via `time`/`timestamp` with timezone strings — parity validated in
P9). No Pine code written.

## Known limitations
- Volatility uses total range percentile; a normalized-ATR percentile is a later
  refinement (both are reserved in the assessment fields).
- Session windows are provisional; the Asian session is a fixed UTC window rather than a
  Tokyo/Sydney exchange calendar.
- No confluence/permission (T5).
