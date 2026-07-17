# Project Scope — BTMM AI Scanner

Status: Phase 0A (knowledge extraction only). No scanner, indicator, AI model, database, website, API, backtest engine, Telegram integration, or MT4/MT5 execution exists yet.

## 1. Final Project Vision

The final system will become an AI-powered Forex and metal scanner that will:

- Identify all Point of Interest (POI) types taught in the book *BTMM and POI Trading Bible* by Ronny Rostand (`references/private/BTMM_AND_POI_TRADING_BIBLE.docx`).
- Detect BTMM manipulation patterns around valid POIs (liquidity creation before/within/after a POI, volume, speed, accuracy).
- Identify and confirm trend direction.
- Draw trendlines.
- Map market structure.
- Analyze liquidity (equal highs/lows, swing points, previous/current day-week-month highs/lows).
- Later consider economic news (fundamental/news filter — not yet implemented).
- Later send Telegram signals with chart images (not yet implemented).
- Later support historical and forward backtesting (not yet implemented).
- Later support MT5 and MT4 automated execution (not yet implemented).
- Later support a multi-user web platform (not yet implemented).

The book is the primary authority for all trading definitions used by this project. Generic ICT, SMC, smart-money, candlestick, or internet definitions must never silently replace or override the book's definitions. Where the book is silent on a widely-known concept (e.g. it does not use terms like "reclaim" or "false invalidation"), the project must treat that concept as undefined rather than importing an outside definition — see [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md) and [PROJECT_STATE.md](PROJECT_STATE.md).

## 2. Initial Markets

Phase 1+ scanner development (not yet started) will target exactly these three symbols, using the TradingView/FXCM feed as the canonical price reference:

- `FXCM:XAUUSD`
- `FXCM:EURUSD`
- `FXCM:GBPUSD`

No other symbols are in scope until the author explicitly expands this list.

## 3. Timeframe Roles

The book's own timeframe guidance (see [SOURCE_INDEX.md](../knowledge/SOURCE_INDEX.md)) assigns different jobs to different chart timeframes. This project adopts the following role split:

| Role | Timeframes | Purpose |
|---|---|---|
| Strong POI analysis | H3, H4, D1, W1 | Identifying the highest-quality Order Blocks, Fair Value Gaps, liquidity/pressure wicks, Morning/Evening Stars, trendlines, and previous/current high-low levels. The book repeatedly states that POIs on higher timeframes (Weekly > Daily > 4H > 1H > 15m) are stronger and more significant. |
| Market-structure breakdown | H1, M15 | Mapping swing highs/lows, breaks of structure, and the trend/consolidation framework a POI must agree with before it is used. |
| BTMM formation and execution | M15, M5, M1 | The book explicitly states BTMM formation, creation, and execution are best observed on the 1-minute, 5-minute, and 15-minute timeframes — M1 for precise execution, M5/M15 for confirming the formation. |

## 4. Canonical Chart Reference

TradingView, using the **FXCM** data feed, is the canonical chart reference for this project. All future candle data, backtests, and screenshots should be sourced from or reconciled against TradingView:FXCM symbols for the three initial markets.

## 5. AI Training Data Hierarchy

1. **Primary training data:** Raw candle data (OHLC/volume series) plus structured annotations (machine-readable labels of POIs, BTMM states, trend/structure, liquidity, derived from the rules in `knowledge/`).
2. **Secondary training data:** Chart images (screenshots/renders), used to support or validate visual pattern recognition, but not the primary source of truth.

Structured, rule-based annotations derived from the book take priority over image-based pattern learning.

## 6. No Live Trading Before Validation

No live trading, and no automated order execution of any kind, may be built or enabled before the system has passed, in this order:

1. Historical backtesting
2. Forward testing (simulated/live-market, no real orders)
3. Paper trading

MT4/MT5 automated execution is a later phase and is explicitly out of scope until the above validation stages are complete and the author authorizes it.

## 7. Separation of Validity Concepts

The system must keep the following four concepts structurally and logically separate — a POI can be valid while a BTMM setup around it is not, a BTMM setup can be confirmed while an entry trigger is not yet valid, and an entry can be valid while the eventual trade outcome differs from what validity predicted:

- **POI validity** — whether a zone meets the book's structural/volume/price-action criteria to be classified as a POI at all (e.g. Order Block candle-size ratio, FVG three-candle displacement rule).
- **BTMM validity** — whether liquidity creation, speed, volume, and accuracy around that POI meet the BTMM strategy's conditions.
- **Entry validity** — whether the specific trade-trigger/confirmation conditions for taking an entry are met.
- **Trade outcome** — the realized result of a trade (win/loss/breakeven), which must never be used to retroactively redefine whether the POI, BTMM setup, or entry was "valid."

## 8. Explicit Non-Goals for This Phase (Phase 0A)

Not built, and not to be built, during Phase 0A:
- Scanner code of any kind
- Pine Script
- AI/ML models
- Databases
- Websites or APIs
- Backtesting engines
- TradingView connections
- Telegram bot integration
- MT4/MT5 execution code

See [PROJECT_STATE.md](PROJECT_STATE.md) for the current confirmation that these restrictions have been respected.
