# BTMM + POI + BTRC Scanner — RC3 EVENT DEMO (2026-09-16)

**Demonstration build. NOT production-approved. NOT an autotrading product.
No profitability claim of any kind.**

## Build identity

| item | value |
|---|---|
| Pine source | `btmm_poi_btrc_scanner_rc3_event_demo.pine` (this folder) |
| sha256 | `f0aa2254ea3664f1138d072ba0993b5f595efc8a1cd239fd270b586ad34fa144` |
| identical to | `tradingview/btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine` |
| last source change | commit `dcc888d` (single primary OB display name) on `rc3-highram-continuation` |
| TradingView script | "BTMM + POI + BTRC Scanner [RC3 POI SEMANTICS DEV]", saved version 21 |
| compiled tokens | under the 100 256 limit (compiles; exact count is only printed when over) |
| provider | **FXCM XAUUSD only** — TradingView ticker `FX:XAUUSD` |
| demo chart | FX:XAUUSD **H4**, `Max visible zone groups` = 8 (default) |

The script title still reads `[RC3 POI SEMANTICS DEV]`; the build is the same
bytes, not a renamed variant. The companion capture build is
`tradingview/btmm_poi_btrc_scanner_rc3_parity_dev.pine` (sha256 `d49f0624…`,
TradingView "RC3 PARITY DEV" version 4); it draws no zones.

## Supported hosts

Live on FX:XAUUSD, 2026-09-16, both USER v21 and PARITY v4 on the chart:
**M1, M5, M15, H1, H4, D1, W1** — no runtime error, no `TF?` label, bullish
zones green / bearish red, FVG zones visible on every host, no
"ORDER BLOCK + … ENGULFING" composite text, box text native and auto-sized.

The P5 authority timeframes are W1 / D1 / H4 / H1 / M15 / M5. On M1 (outside
that set) the momentum and breakout components take production's
missing-component scores (50 / 40) by design.

## What it shows

- Fresh POI zones as boxes: green = bullish, red = bearish, centred
  "`TF • TYPE`" text, projected to the right while fresh; a zone disappears
  once price reacts to it (RC3 freshness).
- Fresh FVGs, grouped per direction when they overlap or touch
  (`SELL FVG ×2`).
- One name per formation: an order block that is also a same-candle engulfing
  reads `BUY ORDER BLOCK` / `SELL ORDER BLOCK`. Independent POIs on other
  candles (FVG, S/R, other patterns) keep their own names.
- A support/resistance zone's left edge is its origin swing candle.
- P7 summary table (top-left) and nearest active POIs table (bottom-right).

## Known limitations (read before the event)

1. **Higher-timeframe context is not in Pine.** The Python engine records,
   for a POI overlapping a same-type same-direction POI on a higher
   timeframe, a raised `effective_timeframe` (derived higher-TF context — the
   POI's source timeframe and identity are unchanged) and P5 scores that POI
   with that timeframe's momentum / breakout / volatility. This single-
   timeframe Pine build scores every POI on the chart timeframe, so for those
   POIs the table's score, permission and state can differ from Python.
2. Visual capacity is 8 zone groups (input, max 30); the table lists all
   eligible POIs.
3. Box text uses `size.auto`: always inside its zone; on very thin zones or at
   extreme compression it becomes tiny. Overlapping zones show one name (the
   nearest zone owns the text).
4. Needs ≥ 1 800 bars of chart history plus 1 251 bars on each of the six
   context timeframes; very young symbols or thin history will not warm up.
5. Basic TradingView plan: at most 2 indicators / live connections per chart,
   and a "heavy script" runtime warning can appear.
6. Any scores and permissions are analytical context only, not trade
   instructions.

## Parity status (evidence level, not a marketing claim)

Level A = independent Python from FXCM OHLC; Level B = the PARITY build's
Pine output, captured in one run and aligned bar-for-bar (window proven by
count + OHLC checksum). M15 run 1, 300 bars compared:

| stage | host-only POIs | POIs with higher-TF context |
|---|---|---|
| P3 identity (canonical = source timeframe) | 228 / 228 matched, 0 Python-only, 0 Pine-only | same set; 2 terminal-time differences |
| P5 rows | 104 rows, **0** field mismatches | 2 715 rows, 10 961 field mismatches |
| P8 events | 111 events, **0** differences | 1 301 Pine events, 901 differences |
| P8 order (Pine native `poiIdx`, priority) | 0 violations | 0 violations |

**P3/P5/P8 parity is NOT closed.** The exact remaining blocker is
limitation 1: `t5_engine.py` evaluates a POI on `poi.effective_timeframe`
while Pine evaluates on the host. Closing it needs an author decision on P5
semantics, not a tooling fix. P6 (cross-timeframe substrate) remains CLOSED
and byte-locked (P6 block sha256 `52ceb8ee…` identical in RC2, USER, PARITY).

## Known historical display defect (RC1-FIX / RC2)

FVG detection and lifecycle worked, but the Pine FVG grouping sweep in the
zone display failed to emit zones (loop-local cluster state did not persist
between iterations), so **no FVG box was ever drawn** by
`btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine` or the promoted
`btmm_poi_btrc_scanner_rc2.pine`. RC3 contains the correction (commit
`ec83d1f`). RC1 and RC2 are frozen and unchanged (sha256 `143c0f88…` /
`381f2fc2…`); a legacy fix would ship as a new RC2.1-style line.

## Test status

Full repository suite at `824cb28`, run with `--ignore=tests/unit/test_v1a_m5_materiality.py` (sealed lock test not collected): **4 740 passed, 0 failed, 0 skipped**. `ruff` clean on `src/` (tests keep the 71 pre-existing findings), `mypy src` clean, `git diff --check` clean.

## Dry-run bot

Branch `bot-dryrun-v1` (`231cf73`, pushed): paper / dry-run only, no broker
connection, live broker impossible by construction. It consumes semantic POI
records from the Python scanner (`poi_type`, P5/P8 rows), never chart labels,
so the display-name change cannot affect it.

## Not included / not claimed

No broker connection, no order placement, no alert-to-order automation, no
production approval, no backtest or profitability result.
