# Strategy Tester assets — RC5_EA

**Status: TESTER CONFIGURED / EXECUTION ENVIRONMENT BLOCKED.**

Hardened for EA2-B: each symbol now has a `.set` (inputs) AND a `.ini`
(launch config with a per-symbol `Report=`), so three runs cannot overwrite
one another's evidence.

The configs are complete. Launching the tester needs a terminal start with a
custom config, which this session's sandbox denies, and there is no Windows UI
automation available here. That is one step, not a property of the EA.

| symbol | set file | notes |
| --- | --- | --- |
| XAUUSDm | `RC5_XAUUSDm.set` + `.ini` | Exness Standard gold; report `RC5_report_XAUUSDm` |
| EURUSDm | `RC5_EURUSDm.set` + `.ini` | report `RC5_report_EURUSDm` |
| GBPUSDm | `RC5_GBPUSDm.set` + `.ini` | report `RC5_report_GBPUSDm` |

`InpSymbolRoots` carries the ROOT (`XAUUSD`), not the broker name — the EA's
`ResolveSymbol` discovers the suffix at runtime, so the same set file works on a
server with a different convention.

## Execution enabled here, and only here

`InpExecutionEnabled=true` appears in these files because the Strategy Tester
is isolated. The EA's own default is **false**, and `CanExecuteLive()`
additionally requires terminal and account algo permission, so these files
cannot arm the live account.

## Doctrine defaults carried

`InpRiskPercent=0.5` and (when EA2-B lands) `InpRewardRisk=2.0` are **Execution
Doctrine V1** values, not RC5 scanner semantics. See
`docs/validation/BTRC_V1_RC5_EXECUTION_DOCTRINE_V1.md`.

## To run, once the environment permits

```
terminal64.exe /config:<tester.ini>
```
with `[Tester] Expert=RC5\RC5_EA`, `Symbol=XAUUSDm`, `Period=M15`,
`Model=0` (every tick based on real ticks), a date window, and
`ExpertParameters=RC5_XAUUSDm.set`.

## What changed when EA2-B landed

`InpExecutionEnabled=true` in these files is no longer sufficient to trade a
live account, in either direction. `CanExecuteHere()` requires the four
existing permissions AND either `MQL_TESTER` or `InpAllowLiveExecution`, and
`InpAllowLiveExecution=false` is written explicitly in every set file. Loading
a tester profile onto a live chart therefore arms nothing.

New inputs carried by every set file:

| input | tester value | meaning |
| --- | --- | --- |
| `InpRewardRisk` | 2.0 | V1 EXECUTION POLICY. RC5 specifies no reward multiple. |
| `InpMagic` | 5150001 | identifies this EA's positions; nothing else counts as RC5's |
| `InpAllowLiveExecution` | false | required for live execution, never set true here |
| `InpSlippagePoints` | 20 | max deviation on a market order |
| `InpSetupFile` | `RC5_fixtures_<ROOT>.csv` | REFERENCE state exported from the engine |

## The fixture file is not a signal source

`InpSetupFile` points at analytical state the Python engine already decided,
one setup per line, in `RC5LogSetup`'s field order. The EA contains no
detector; with no fixture file it dispatches nothing. `tools/rc5_ea_fixtures.py`
renders these lines and computes the V1 expectation for each, so a tester run
can be diffed against Python rather than judged on its own output.

Entry prices are deliberately absent from the expectation: the entry is the
first tradable price AFTER confirmation, which exists only at runtime. The
Python side marks it `ENTRY_PRICE_PENDING_TESTER` instead of inventing one.
