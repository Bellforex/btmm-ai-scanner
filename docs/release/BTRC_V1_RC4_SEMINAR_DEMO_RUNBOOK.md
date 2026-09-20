# RC4 seminar demo runbook

Build: TradingView USER `[RC4 MARKET FRAMEWORK]` v14 (saved source `1279474b…`),
scanner semantics `2f1d2b9`, paper bot `bot-dryrun-integration`.
Educational demonstration only: paper / simulation, no live broker, no
profitability claim. Status: RC4 EVENT / DEMO READY; full RC4 authority,
production approval, main merge and TradingView publication are all still
pending.

## 0. Before the session (5 minutes)

1. Chrome: exactly **one** TradingView tab, chart `FX:XAUUSD`, **M15**, in the
   foreground (a background tab stops painting the chart).
2. Chart carries **USER v14 only** (Object Tree: one study). No PARITY, no
   exporter, no drawings.
3. Student default: POI zones ON, POI text ON, all 18 POI type filters ON,
   Dashboard ON, POI Table ON, Market Structure / Trendlines / Range /
   Liquidity / BTMM Cycle OFF.
4. Slides: `artifacts/seminar_screenshots/` — `A_poi_only.png`, `B_market_structure.png`, `C_range_liquidity.png`, `D_btmm.png`,
   `E_full_framework.png` (FX:XAUUSD M15, USER v14).

Settings live in the indicator's Settings → Inputs: group **Display layers**
(Market Structure, BTMM Cycle, Trendlines, Consolidation / Range, Liquidity),
**POI type filters** (18 switches), the P7 group (Dashboard, POI Table) and
the P7-Z group (POI Zones, POI Text). Turn ONE layer on at a time while
teaching; turn it off again before the next step.

## 1. The story, step by step

| step | switch to show | what to say |
|---|---|---|
| **1. Market framework** | Dashboard; then **Market Structure** | The scanner first decides *where we are*: trend (impulse → correction, BOS / CHOCH, SH / SL) or consolidation. The dashboard row **Market framework** reads `RANGE low – high` when the BTRC RANGE rule fires (≥ 3 CHOCH in the last 4 transitions), otherwise `TREND / impulse`. |
| **2. POI** | POI zones + text (default) | Every zone is one of the 18 canonical POI types (order blocks, FVGs, engulfings, stars, hammer / shooting star, pressure wicks, B2S / S2B, base rally / drop, support / resistance). Each type has its own on/off switch — presentation only; the engine still evaluates every POI. |
| **3. Fibonacci / location** | POI Table, column *Cycle / Location / Liq* | Trend POIs are graded by how deep the correction sits inside **the impulse that created the POI**: < 50 % → 40, 50–61.8 → 65, 61.8–79 → 80, > 79 → 55. Range POIs: correct side (buy lower third / sell upper third) 75, middle 35, wrong side 20. A POI is never deleted for its location — P5 downgrades it. |
| **4. Liquidity** | **Liquidity**, then **Consolidation / Range**, then **Trendlines** | BSL (orange) = buy-side pools above price, SSL (teal) = sell-side below; SWEEP = a wick through and back, or a close through reclaimed within 3 bars (an unreclaimed close-through is an accepted break, not a sweep). Range: high, low, dotted midpoint. Trendlines are built from confirmed swing anchors and act as liquidity; they are never required. An approach-side sweep adds +15 to location. |
| **5. BTMM DIS / DEL / WIP** | **BTMM Cycle** + POI Table | The pre-trade cycle is valid on ANY of: **DIS**traction (approach-path liquidity swept before the touch), **DEL**ay (≥ 2 closes inside the zone or ≥ 1 re-entry), **WIP**eout (beyond the far edge, reclaim within 3 bars, departure). A diamond marks the bar a POI's cycle became valid; the table shows the reason. After the first touch the POI stays under observation for the 5-bar interaction episode; accepted beyond the zone without reclaim = **true failure** (POI invalidated). |
| **6. P5** | POI Table (Score, Permission, State) | P5 combines BTMM 85 / 55 / 25, POI, trend, regime, momentum, breakout, location and volatility into one score; ≥ 65 with trend alignment → BUY BIAS / SELL BIAS, 45–65 → WATCH ONLY. BTMM is a *score*, not a gate. Weights and bands are fixed for RC4. |
| **7. P8** | (alerts) | P8 announces transitions only: POI activated → BTMM validated → permission entered / lost actionable → POI terminal (at the end of the episode). |
| **8. Paper order** | terminal (below) | The paper bot consumes only P5 / P8. A *permission entered actionable* event becomes a trade intent; the practice policy places a paper limit at the zone edge, stop beyond the zone, target at 2R, and skips intents when exposure limits are reached. |

Full-framework slide (E): everything on at once — use it to recap, not to
teach.

## 2. Paper bot demo (terminal, repo worktree of `bot-dryrun-integration`)

```bash
cd C:/Users/user/Desktop/btmm-ai-scanner/.claude/worktrees/agent-ace65295b822c898e
```

```bash
PYTHONPATH="$(pwd -W)/src;$(pwd -W)" /c/Users/user/Desktop/btmm-ai-scanner/.venv/Scripts/python.exe -m botdryrun replay --state-dir artifacts/seminar_demo --trading-day 2026-08-10 --dataset-root C:/Users/user/Desktop/btmm-ai-scanner/artifacts/v1a_validation
```

* Context lookback defaults to **250** (inherited from the scanner; 40 starved
  the higher-timeframe trend context). Scanner pin **`2f1d2b9`**: the run
  refuses to start on any other scanner source. Execution mode **PAPER**;
  there is no broker code.
* One trading day ≈ 30 s. Show `status`, `health`, then the journals in
  `artifacts/seminar_demo/journals/`: `trade_intent_journal.csv`,
  `order_journal.csv`, `trade_journal.csv`.
* Restart safety (optional): `replay … --max-bars 40`, then `restart
  --state-dir artifacts/seminar_demo` — the bot rebuilds the processed bars in
  a new process, verifies every digest, and continues.

Reference run (2026-08-10 → 08-12, 276 bars): 532 actionable events → 532
intents, 42 paper orders, 1 closed paper trade. Explainability table:
`artifacts/bot_final_rc4_explain.csv`.

Worked example (from that table, 2026-08-10 11:30 UTC, M15 host):
SHORT **EVENING_STAR** (M5 source) zone 4337.56–4340.66 · framework TREND ·
retracement 67.08 % (61.8–79 band) · no sweep · BTMM reason NONE (the
permission came from the other components — BTMM is a score, not a gate) ·
P5 65 **SELL BIAS** · P8 PERMISSION_ENTERED_ACTIONABLE → paper limit 4337.56,
stop 4340.66, target 4331.36 → closed at target. One paper trade on
historical data is plumbing evidence, **not** evidence of an edge.

## 3. Things to say plainly

* Everything shown runs on confirmed bars only — no repainting, no lookahead.
* Python and TradingView agree exactly on a real FXCM M15 capture
  (P3 108 POIs, P5 1 874 rows, P8 471 events, 0 mismatches).
* RC4 is a demo build: the full RC4 authority run, production approval and
  publication are still pending. No live trading.

## 4. After the session

Restore the student default (section 0, step 3). Do not add indicators (the
plan allows 2 per chart, and the USER build is at TradingView's token limit).
