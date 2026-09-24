# RC5 — EXACT RUNTIME PROCEDURES

Everything still outstanding is environment-blocked, not undecided. This file
exists so that the moment either environment becomes available, the work runs
immediately and in a fixed order — no re-derivation, no guessing.

Two blockers, two procedures.

---

## A. STRATEGY TESTER

### A.0 Is it available?

The blocker is launching MetaTrader with a tester config. Availability means
this succeeds:

```bash
"C:/Program Files/MetaTrader 5 EXNESS/terminal64.exe" /config:"<abs path>/RC5_XAUUSDm.ini"
```

If the process launch is denied, the procedure stops here. **Do not retry the
same denied launch** — it has already been attempted and refused.

### A.1 Generate the fixture file FIRST

The EA has no detector. With no `InpSetupFile` it dispatches nothing and a
tester run will correctly place zero trades. Generate reference state before
running anything:

```bash
PYTHONPATH=. .venv/Scripts/python.exe -m tests.parity_support.rc5_ea_layer_a \
  --ohlc artifacts/rc4_aligned_v2/_normalized/m15.csv \
  --timeframe M15 --minutes 15 --symbol XAUUSD --tick 0.01 \
  --out "$APPDATA/MetaQuotes/Terminal/53785E099C927DB68A545C249CDBCE06/MQL5/Files/RC5_fixtures_XAUUSD.csv"
```

The command prints `bars / rows / confirmed / actionable / arguable`. **If
`confirmed` is 0, stop and read §A.2** — a run against that file proves nothing
about execution.

### A.2 The reachability precondition — READ THIS BEFORE BLAMING THE EA

Measured on the author's 300-bar M15 EURUSD capture, single-timeframe: **no POI
ever reaches `LIQUIDITY_VALIDATED`.** The lifecycle ladder tops out at
`POI_VALIDATED` because `TREND_VALIDATED` needs a trend alignment that a single
timeframe with no higher-timeframe context does not produce. The M45 and H3
captures never leave `DETECTED`.

Consequence: **a tester run against a single-timeframe fixture file will place
zero trades, and that is the correct behaviour, not a failure.** Use a
multi-timeframe capture (`artifacts/rc4_aligned_v2/_normalized/` carries
W1/D1/H4/H1/M15/M5) so the trigger is reachable, and confirm `confirmed > 0`
before drawing any conclusion from a tester result.

### A.3 Order, and what the first run is for

1. XAUUSDm 2. EURUSDm 3. GBPUSDm — `Model=0`, every tick based on real ticks.

The first run is **not** about profitability. Do not optimize parameters. It
verifies: initialization, history access, that setups are dispatched at all,
risk sizing, entry timing, legal price normalization, legal lot sizes, no
duplicate orders, one position per symbol, SL/TP attachment, terminal
invalidation handling, and no runtime exceptions.

### A.4 Evidence to record per symbol

symbol · timeframe · date range · tick model · initial deposit · leverage ·
trades · wins · losses · net · profit factor · max drawdown · largest win ·
largest loss · errors · **every rejected trade with its deny reason**.

The deny reasons are the most informative output of a first run: `RC5PLAN`
lines carry them, and the complete set is listed in the Execution Doctrine
document.

### A.5 Safety, restated

`InpExecutionEnabled=true` appears only in the tester `.set` files.
`InpAllowLiveExecution=false` is written explicitly in each of them and must
stay false. Because `CanExecuteHere()` requires `MQL_TESTER` **or** that second
arm, a tester profile cannot arm a live account even if loaded onto a live
chart. No deposits, no withdrawals, no transfers, no live orders.

---

## B. TRADINGVIEW RUNTIME

### B.0 Is it available?

Run this in the tab, and require **all four**:

```js
JSON.stringify({
  user: window.user && window.user.username,     // must be "bellcare1994"
  hidden: document.hidden,                        // must be false
  canvases: [...document.querySelectorAll('canvas')].map(c => c.width+'x'+c.height),
  legend: document.querySelectorAll('[data-name="legend-source-item"]').length,
})
```

| requirement | value |
| --- | --- |
| `user` | exactly `bellcare1994` |
| `hidden` | `false` |
| canvases | real dimensions, **not** `300x150` |
| legend | `> 0` |

**All four, every time, before any state-changing action.** The last observed
state was `bellcare1994` + `hidden: true` + seven `300x150` canvases + `0`
legend rows: the correct account, and still no renderer.

Three traps that make this check non-optional:

* A screenshot is captured over CDP and renders correctly **even while the page
  reports itself hidden**, so a screenshot cannot establish that the chart is
  laid out.
* `document.hasFocus()` can be `true` while `document.hidden` is also `true`;
  focus is not visibility.
* Browser display names have already changed once. Key on the **deviceId**, and
  verify `window.user.username` in the page. Never state-change as
  `STEVECRYPTO1995`.

### B.1 Run order, once all four pass

1. **P2/P3 parity** — synthetic RBR bootstrap, synthetic DBD bootstrap, golden
   EURUSD M15 DBD, M45 families, H3 families, transition history,
   future-transition guard, prefix stability.
   The bootstrap cases come first on purpose: a port that implemented only the
   transition half would pass every real-data check, because all three captures
   have zero Bases in their bootstrap-only window.
2. **P4 parity** on the golden M15 — DBD Base PRIMARY, pressure wick
   subordinate, doji subordinate where a raw candidate exists, evening star
   subordinate through exact co-extension, and no post-activation independent
   P5/P8 from any subordinate.
3. **VIEW gates** — G1 VIEW alone, G2 CORE alone, G3 CORE+VIEW (the production
   pair), G4 CORE+PANEL.
4. **Structure visual acceptance** — see §B.3.
5. **MTF smoke** — M5, M15, M30, M45, H1, H3, H4.

### B.2 How Pine output is read

Everything P2/P3/P4 publishes at runtime goes through the compacted
`log.info` liveness line (`bootDir,time:family,…`) at `barstate.islast`. There
is no data-window budget left, and CORE has **73 tokens** of headroom, so
nothing may be added to make a run easier to read.

### B.3 Structure coordinates — LOOK BEFORE CHANGING

S1 (HH/HL/LH/LL label anchor) and S2 (BOS/CHOCH connector left endpoint) are
**one** question: `brokenSwingKey` is documented as `== SwingRec.pivotEndTime`,
so both already use the same quantity, the open time of the pivot's LAST
candle. Neither uses an availability time, so the "availability controls WHEN,
event controls WHERE" rule already holds.

What is open is *which* event time, and the codebase argues both ways —
`pivotEndTime` is called "P1's own swing identity" in one comment and an
"anchor" in another, while Python orders swings by `pivot_start_time_utc` and
publishes no label coordinate at all. **Do not change these blind.** Inspect the
real rendering against the intended structural swing, and change only if a
visible defect is proven. If it is, make the smallest VIEW-only correction —
detection in CORE is untouched — and re-run extraction parity afterwards.

---

## C. WHAT NEITHER PROCEDURE MAY DO

No publication. No merge to `main`. No BAH republish. No modification of the
`bellforex` layout. No state-changing action on `STEVECRYPTO1995`. No live
orders, deposits, withdrawals or transfers. Algo trading stays disabled until
the author explicitly approves live deployment after testing.
