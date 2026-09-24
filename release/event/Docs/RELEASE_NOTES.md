# RC5 — v1.0 EVENT RELEASE

| | |
| --- | --- |
| build date | 2026-09-24 |
| git SHA | see `Checksums/MANIFEST.txt` |
| Pine CORE | **100,183 tokens** (limit 100,256, headroom 73) |
| EA | `RC5_EA.ex5`, compiled 0 errors / 0 warnings |
| Python suite | see `Checksums/MANIFEST.txt` |

## Products

**RC5 Scanner** — TradingView, invite-only. CORE + VIEW.

**RC5 EA** — MetaTrader 5, EX5 only, licence-controlled.

## What is verified, and how

| area | level |
| --- | --- |
| Python analytical engine | full suite green; it is the reference implementation |
| Pine CORE / P4 | compiled and token-verified by three agreeing measurements |
| EA execution doctrine | **TESTER-VERIFIED** on real Exness XAUUSDm history |
| EA licensing | unit-verified; tester run proves it does not alter execution |

Strategy Tester acceptance placed **real orders on real historical quotes**:
entries taken at the actual ask, stops exactly one tick beyond the zone
boundary, 2R targets, 0.5% risk sizing, and broker-calculated margin.

## Known limitations — stated, not hidden

* **Pine runtime visual acceptance is PENDING.** CORE and VIEW compile and are
  source-verified; they have not been visually accepted on a rendered chart in
  this environment.
* **Structure label coordinates (S1/S2) are unverified visually.** The question
  affects only multi-candle pivots — 2 of 69 on the reference capture — and
  nothing was changed without seeing it.
* **The EA's terminal-event close path has no runtime event source yet.** Both
  approved invalidation exits are implemented and unit-verified, but nothing
  currently triggers them at runtime; positions close on stop, target, or
  manually.
* **FX execution is unproven.** Symbol resolution and broker-contract reading
  are verified on EURUSDm and GBPUSDm, but no FX order has been placed — order
  path and margin are verified on gold only.
* **`MARGIN_EXPOSURE_INVALID` cannot fire on a 1:500 account.** Proved
  algebraically: the spread/R gate refuses first. It becomes reachable below
  roughly 1:107 leverage.

## No performance claim

Two tester trades exist and both stopped out. That is **not** a performance
result: the sample is two, they are test fixtures, and nothing was tuned. The
one thing it verifies is the risk model — predicted risk 92.30, realized loss
92.30.

Nothing in this release claims profitability, and nothing should be represented
as doing so.
