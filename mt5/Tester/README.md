# Strategy Tester assets — RC5_EA

**Status: TESTER CONFIGURED / EXECUTION ENVIRONMENT BLOCKED.**

The configs are complete. Launching the tester needs a terminal start with a
custom config, which this session's sandbox denies, and there is no Windows UI
automation available here. That is one step, not a property of the EA.

| symbol | set file | notes |
| --- | --- | --- |
| XAUUSDm | `RC5_XAUUSDm.set` | Exness Standard gold |
| EURUSDm | `RC5_EURUSDm.set` | |
| GBPUSDm | `RC5_GBPUSDm.set` | |

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
