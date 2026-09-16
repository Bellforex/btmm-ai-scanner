# BTMM + POI + BTRC Scanner — RC3 EVENT DEMO (2026-09-16)

**Demonstration build. NOT production-approved. NOT an autotrading product.
No profitability claim of any kind.**

## Build identity

| item | value |
|---|---|
| Pine source | `btmm_poi_btrc_scanner_rc3_event_demo.pine` (this folder) |
| sha256 | `58750a8ec6a1512463fe0aff464a08eadd67dc881707bd211c0525cf9110e7b8` |
| identical to | `tradingview/btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine` |
| last source change | commit `8010e63` (semantics-neutral compaction) on `rc3-highram-continuation` |
| TradingView script | "BTMM + POI + BTRC Scanner [RC3 POI SEMANTICS DEV]", saved version 15 |
| compiled tokens | 99 319 (limit 100 256) |
| provider | **FXCM XAUUSD only** — TradingView ticker `FX:XAUUSD` |

The script title still reads `[RC3 POI SEMANTICS DEV]`; the build is the same
bytes, not a renamed variant.

## Supported hosts

Compiled and run live on FX:XAUUSD with no runtime failure and no `TF?`
label on: **M1, M5, M15, H1, H4, D1, W1**.

The P5 authority timeframes are W1 / D1 / H4 / H1 / M15 / M5. On M1 (outside
that set) the momentum and breakout components take production's
missing-component scores (50 / 40) by design.

## What it shows

- Fresh POI zones as boxes: green = bullish, red = bearish, centred
  "`TF • TYPE`" text, projected to the right while fresh; a zone disappears
  once price reacts to it (RC3 freshness).
- A support/resistance zone's left edge is its origin swing candle.
- P7 summary table (top-left) and nearest active POIs table (bottom-right).

## Known limitations (read before the event)

1. **Cross-timeframe merge is not in Pine.** The production Python engine
   promotes a POI's effective timeframe when it overlaps a same-type,
   same-direction POI on a higher timeframe, and scores it on that timeframe.
   This single-timeframe Pine build scores every POI on the chart timeframe.
   For those POIs the table's score, permission and state can differ from
   the Python engine. **Author decision pending** (see
   `docs/validation/BTRC_V1_RC3_TODAY_CLOSURE_SPRINT.md`).
2. Visual capacity is 8 zone groups (input, max 30); the table lists all
   eligible POIs.
3. Needs ≥ 1 800 bars of chart history plus 1 251 bars on each of the six
   context timeframes; very young symbols or thin history will not warm up.
4. Basic TradingView plan: at most 2 indicators / live connections per chart.
5. Any scores and permissions are analytical context only, not trade
   instructions.

## Parity status (evidence level, not a marketing claim)

- Level A = independent Python from FXCM OHLC; Level B = this scanner's Pine
  output, captured in one run and aligned bar-for-bar (window proven by
  count + OHLC checksum).
- For POIs **not** affected by limitation 1: P3, P5 and P8 matched exactly on
  every bar compared (no missing, extra or differing values). The only other
  difference is the order of same-bar events between POIs registered on the
  same bar (identity and content identical).
- For POIs affected by limitation 1: P5 scores / permission and the resulting
  P8 permission events differ. **P3/P5/P8 parity is therefore NOT closed.**
- P6 (cross-timeframe substrate) remains CLOSED and byte-locked.

## Test status

Full repository suite on the RC3 branch: 4 710 passed, 0 failed, 0 skipped.
`ruff` clean on `src/` and all new tooling; `mypy src` clean.

## Not included / not claimed

No broker connection, no order placement, no alert-to-order automation, no
production approval, no backtest or profitability result.
