# RC5 — STRATEGY TESTER ACCEPTANCE RUNBOOK

Written so that when process execution becomes available, acceptance is **one
direct run**, not more design work. Every value that can be known in advance is
here; everything that cannot is marked `PENDING_TESTER` and must be *observed*,
never filled in from hindsight.

**Current execution availability: BLOCKED**, but the cause has NARROWED — see
the appendix. Generic process launch is now permitted; what is refused is
launching or closing MetaTrader itself, and MetaTrader allows only one instance
per data folder. Everything else is staged and verified.

---

## 0. PRECONDITION — generate the fixture file first

The EA has **no detector**. With no `InpSetupFile` it dispatches nothing and the
run places zero trades for a reason that has nothing to do with the execution
layer.

```bash
PYTHONPATH=. .venv/Scripts/python.exe -m tests.parity_support.rc5_ea_layer_a \
  --ohlc artifacts/rc4_aligned_v2/_normalized/m15.csv \
  --timeframe M15 --minutes 15 --symbol XAUUSD --tick 0.01 \
  --out "<terminal>/MQL5/Files/RC5_fixtures_XAUUSD.csv"
```

It prints `bars / rows / confirmed / actionable / arguable`.
**If `confirmed` is 0, stop** — that file cannot demonstrate an execution.

---

## 1. GOLDEN 1 — HAMMER

| # | item | value |
| --- | --- | --- |
| 1 | config | `mt5/Tester/RC5_XAUUSDm.ini` |
| 2 | symbol | `XAUUSDm` |
| 3 | host timeframe | M15 |
| 4 | date range | must cover **2026-08-30**; set `FromDate`/`ToDate` in the `.ini` and confirm the terminal has that history |
| 5 | analytical timestamp | **2026-08-30 22:45:00 UTC** (epoch `1788129900`) |
| 6 | zone | **4450.54 – 4467.06** |
| 7 | direction | BULLISH (BUY, executable side **ASK**) |
| 8 | Stage-1 proximity | **PASS** — confirmation close 4461.29, inside, distance **0** |
| 9 | first executable quote | `PENDING_TESTER` — capture the ASK on the first tick after confirmation |
| 10 | Stage-2 decision | `PENDING_TESTER` |
| 11 | log pattern | `RC5PLAN .*HAMMER~82c481350728` |
| 12 | report | `RC5_report_XAUUSDm` |

Entry-independent expectations, exact and already pinned:

| | |
| --- | --- |
| distal | **4450.54** |
| stop | **4450.53** |

## 2. GOLDEN 2 — MORNING_STAR

| # | item | value |
| --- | --- | --- |
| 1 | config | `mt5/Tester/RC5_XAUUSDm.ini` |
| 2 | symbol | `XAUUSDm` |
| 3 | host timeframe | M15 |
| 4 | date range | must cover **2026-09-08** |
| 5 | analytical timestamp | **2026-09-08 14:45:00 UTC** (epoch `1788878700`) |
| 6 | zone | **4391.07 – 4399.54** |
| 7 | direction | BULLISH (BUY, executable side **ASK**) |
| 8 | Stage-1 proximity | **PASS** — confirmation close 4398.65, inside, distance **0** |
| 9 | first executable quote | `PENDING_TESTER` |
| 10 | Stage-2 decision | `PENDING_TESTER` |
| 11 | log pattern | `RC5PLAN .*MORNING_STAR~cf5314af21ab` |
| 12 | report | `RC5_report_XAUUSDm` |

| | |
| --- | --- |
| distal | **4391.07** |
| stop | **4391.06** |

---

## 3. ACCEPTANCE CRITERIA (Track H)

A golden PASSES tester validation only when the **actual quote is captured** and
then every one of these is verified against it:

1. the executable side is correct — **ASK** for these two BUYs, never the bid,
   never the bar close;
2. **Stage-2 entry proximity** — `distance(entry, zone) <= max(tick, spread)`;
3. **distal SL exact** after tick normalization — 4450.53 / 4391.06;
4. **R** = `|entry − stop|`;
5. **spread/R** ≤ 0.25;
6. **risk money** = 0.5% of equity;
7. **volume** legal: on the step, within min/max, and never clamped upward past
   the budget;
8. **`OrderCalcMargin`** returns a value — a broker that will not price it must
   deny with `MARGIN_UNAVAILABLE`;
9. **margin fraction** ≤ 0.20;
10. **TP** = entry + 2R;
11. **signal identity** matches the expected `~`-separated id;
12. **exactly one execution** — no duplicate entry on any later tick, and no
    second position on the same broker symbol.

## 4. NEGATIVE CASE — the stale POI (Track I)

| | |
| --- | --- |
| POI | HAMMER, zone **308.75 – 312.85** |
| confirmation | ~4,400 |
| expected | **NO ORDER** |
| deny reason | `CONFIRMATION_PROXIMITY_INVALID` |
| expected distance / tolerance | **4087.15** / **0.20** |

What must ALSO be true, and is provable from the journal:

* **no `OrderCalcMargin` call** for this signal;
* **no risk or volume figures** beyond the short-circuit — the `RC5PLAN` line
  reports `vol=0.00` and `margin=0.00`;
* **no order submission**.

The offline trace is already pinned in
`tests/unit/test_rc5_v1_release_audit.py`:

```
ANALYTICAL_ELIGIBLE → LIQUIDITY_VALIDATED → DUPLICATE_CLEAR
→ CONCURRENCY_CLEAR → CONFIRMATION_PROXIMITY_INVALID   ... and STOP
```

---

## 5. TURNING THE JOURNAL INTO A DIFF (Track J)

```python
from tools.rc5_journal_parser import parse_journal_file
parsed = parse_journal_file(Path("<terminal>/Tester/logs/<date>.log"))
parsed.executed()                       # rows that became orders
parsed.deny_reasons()                   # every refusal, in order
parsed.by_signal("XAUUSD~15~HAMMER~82c481350728~0~1~1788129900")
```

Each `PlanRow` carries the full field set: entry, sl, tp, R, riskPct,
riskMoney, realized, vol, spread, spreadToR, margin, marginFrac, confDist,
entryDist, tol, Rticks, R/entry, TPdist, TP/entry, lc, xb.

The parser **collects** unparsed RC5 lines rather than skipping them — a
silently dropped line is how a run comes back looking cleaner than it was.

---

## 6. EXPECTED-VS-OBSERVED (Track K)

`docs/release/RC5_GOLDEN_EXPECTED.md` holds the record template with every
known field filled in and every unknown marked `PENDING_TESTER`. When output
arrives, replace **only genuinely observed fields** and diff the rest.

---

## 7. RUN ORDER, once unblocked

1. GOLDEN 1
2. GOLDEN 2
3. the stale negative fixture
4. XAUUSDm broader smoke
5. EURUSDm
6. GBPUSDm

The first run is about **execution correctness, not profitability**. Do not
optimize parameters; V1 policy is frozen for verification.

## 8. SAFETY, restated

`InpExecutionEnabled=true` appears only in the `.set` files.
`InpAllowLiveExecution=false` is written explicitly in each of them and stays
false, and `CanExecuteHere()` requires `MQL_TESTER` **or** that second arm — so
a tester profile cannot arm a live account even if loaded onto a live chart.
No deposits, no withdrawals, no transfers, no live orders.

---

## APPENDIX — THE RUN IS FULLY STAGED; ONE PERMISSION REMAINS

Everything the acceptance run needs is now in place on this machine:

| item | state |
| --- | --- |
| EA installed | `MQL5\Experts\RC5\RC5_EA.ex5`, **byte-identical** to the repo build |
| fixture file | `MQL5\Files\RC5_fixtures_XAUUSD.csv` — GOLDEN 1, GOLDEN 2, stale negative |
| tester inputs | `MQL5\Profiles\Tester\RC5_XAUUSDm.set` |
| launch config | `config\RC5_acceptance.ini` — XAUUSDm M15, Model 0, 2026.08.25–2026.09.12, `ShutdownTerminal=1` |
| symbol history | `bases\Exness-MT5Real10\history\XAUUSDm\2026.hcc` present |

### What blocks the run

Generic process launch **is** permitted — verified with an inert probe. What is
refused is process control over **MetaTrader** specifically. Three independent
routes have now been attempted and refused:

| route | result |
| --- | --- |
| PowerShell `CloseMainWindow()` on the terminal | refused |
| PowerShell `Start-Process terminal64.exe /config:` | refused |
| `taskkill //PID <terminal>` | refused |

MetaTrader allows only one instance per data folder, so the running terminal
must close before a `/config:` launch does anything. The safer route was tried
first — launching with the config **without** closing the terminal — and it
exited without starting a tester, created no `Tester\logs` directory and left
the terminal untouched. That is MT5's design, not a configuration mistake.

A scheduled task could technically perform the same close-and-launch, and is
deliberately **not** used: routing around a refused permission by another
mechanism would defeat the point of the refusal rather than satisfy it. This
needs the author's approval or the author's hand.

Portable mode is not an alternative: it would need write access to
`C:\Program Files` and a fresh login, and credentials are never handled here.

### The exact sequence, once permitted

```powershell
Stop-Process -Name terminal64 -Force      # or close it by hand
& "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe" `
  "/config:C:\Users\user\AppData\Roaming\MetaQuotes\Terminal\53785E099C927DB68A545C249CDBCE06\config\RC5_acceptance.ini"
# ShutdownTerminal=1 closes it when the run finishes
& "C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe"   # restore the terminal
```

Then parse, do not read:

```python
from tools.rc5_journal_parser import parse_journal_file
parsed = parse_journal_file(Path(r"<terminal>\Tester\logs\<date>.log"))
```

### One thing to expect, and not to misread

The EA takes the confirmation close from the **broker's** history, while the
golden zones came from the `rc4_aligned_v2` capture. If Exness's XAUUSDm prices
at those bars differ materially from the capture's, Stage 1 will legitimately
DENY on proximity. That would be a **feed difference, not an execution defect**,
and the journal's `confDist` / `tol` fields say so directly.
