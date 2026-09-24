# MT5 — RC5 broker adapter groundwork

Environment confirmed on this machine:

| item | path |
| --- | --- |
| MetaEditor | `C:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe` |
| Terminal | `C:\Program Files\MetaTrader 5 EXNESS\terminal64.exe` |
| Strategy Tester agent | `C:\Program Files\MetaTrader 5 EXNESS\metatester64.exe` |
| Data directory | `%APPDATA%\MetaQuotes\Terminal\53785E099C927DB68A545C249CDBCE06` |

The terminal is running (live Exness Standard account). **Algo trading stays
off and nothing here places an order.**

## `Scripts/RC5_SpecCapture.mq5`

A **Script**, deliberately not an Expert Advisor: scripts cannot trade, and this
one contains no `OrderSend`, no `CTrade`, no `PositionClose` — nothing that
could touch the live account. It reads `SymbolInfo` / `AccountInfo` and writes
one CSV to `MQL5\Files\RC5_broker_spec.csv`.

It exists because the EA must adapt to the broker's ACTUAL contract — tick
size, tick value, volume step, stops level, filling mask — rather than to
account marketing labels. Nothing hardcodes an unsuffixed symbol: the defaults
are `XAUUSDm,EURUSDm,GBPUSDm`, and `InpDiscover` strips a lowercase suffix and
scans Market Watch for the root, so a different server's suffix is discovered
rather than assumed.

### Compile

```
"C:\Program Files\MetaTrader 5 EXNESS\MetaEditor64.exe" /compile:"%APPDATA%\MetaQuotes\Terminal\53785E099C927DB68A545C249CDBCE06\MQL5\Scripts\RC5_SpecCapture.mq5" /log:"%TEMP%\rc5_spec_compile.log"
```

Result: **0 errors, 0 warnings**, `RC5_SpecCapture.ex5` produced. (MetaEditor
exits non-zero as a matter of convention; the log is the authority.)

### Running it — the one manual step

Compiling can be driven from the command line; **executing cannot**. A script
runs when it is attached to a chart, so this needs one action in the terminal:

> Navigator → Scripts → **RC5_SpecCapture** → drag onto any chart → OK.

It writes `MQL5\Files\RC5_broker_spec.csv` and prints a summary line per symbol
to the Experts tab. No chart, symbol or timeframe matters — it queries symbols
by name.

Automating this would mean relaunching the terminal with a startup config
against a LIVE account, which was not done unilaterally.
