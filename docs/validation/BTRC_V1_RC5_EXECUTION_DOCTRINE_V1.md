# RC5 EXECUTION DOCTRINE V1

**This is a NEW downstream layer. None of it existed in RC5.**

The scanner frozen at `28d432e` deliberately defines no entry, stop, target,
sizing or order semantics — see
`BTRC_V1_RC5_EXECUTION_CONTRACT_AUDIT.md`. Everything below is authored here,
for **Strategy Tester and research only**, and must never be described as an
RC5 scanner semantic.

| layer | owns | authority |
| --- | --- | --- |
| **A — RC5 analytical engine** | structure, POIs, authority, validity, P5, P8, BTMM, lifecycle | `28d432e`, unchanged |
| **B — Execution Doctrine V1** | entry, SL, TP, sizing, concurrency, exit | this document |

## The lifecycle boundary — and why it settles the V1 trigger

`src/btmm_ai_scanner/btrc/enums.py` defines `SignalLifecycleState` with a
boundary marked **in the source itself**:

> States DETECTED..LIQUIDITY_VALIDATED are the ANALYTICAL BTRC scope;
> RISK_VALIDATED..CLOSED are **FUTURE PYTHON-BOT scope and are frozen here only
> so the interface is complete (not implemented in T0)**.

| state | scope | implemented |
| --- | --- | --- |
| `DETECTED` | analytical | yes |
| `STRUCTURALLY_VALIDATED` | analytical | yes |
| `BTMM_VALIDATED` | analytical | yes |
| `POI_VALIDATED` | analytical | yes |
| `TREND_VALIDATED` | analytical | yes |
| `REGIME_VALIDATED` | analytical | yes |
| `MOMENTUM_VALIDATED` | analytical | yes |
| **`LIQUIDITY_VALIDATED`** | **analytical — LAST** | **yes** |
| `RISK_VALIDATED` | future bot | **no** |
| `EXECUTION_READY` | future bot | **no** |
| `TRIGGERED` | future bot | **no** |
| `MANAGED` | future bot | **no** |
| `CLOSED` | future bot | **no** |

The tuple `ANALYTICAL_LIFECYCLE_STATES` makes that split machine-checkable, and
a T0 contract test pins it.

### Selected V1 confirmation trigger

**`LIQUIDITY_VALIDATED`** — the final analytical state. It is the existing
state that means *"the analytical setup has now received causal confirmation"*,
and nothing beyond it is implemented. No event was invented.

`EXECUTION_READY` and `TRIGGERED` are exactly the states Layer B must supply;
they are names with no behaviour behind them today. V1 therefore implements the
transition `LIQUIDITY_VALIDATED -> (risk sizing) -> order`, which is precisely
the seam the freeze anticipated.

**P5 is permission, not an order command** — `t5_engine.py` says it "never
produces entry/stop/target/order semantics". V1 treats P5 as a *precondition*
and `LIQUIDITY_VALIDATED` as the *trigger*.

## V1 rules (execution layer, authored here)

| rule | V1 value |
| --- | --- |
| eligibility | authoritative POI **and** valid **and** direction agrees **and** required P5 permission **and** `LIQUIDITY_VALIDATED` |
| entry | first tradable price AFTER confirmation; never an unfinished bar, never a retrospective fill |
| direction | BUY only on bullish authoritative direction; SELL only on bearish; no inversion |
| stop loss | POI distal boundary ± **one executable tick** (`SYMBOL_TRADE_TICK_SIZE`, never `_Point`) |
| broker stop | if it violates `STOPS_LEVEL` / `FREEZE_LEVEL`: **deny and log `BROKER_STOP_INVALID`** — never silently widened |
| take profit | **2.0 R**, `InpRewardRisk` configurable. **An execution-layer V1 rule, not an RC5 semantic.** |
| risk | **0.5 %** equity, `InpRiskPercent`. Sizing from real tick size / tick value / contract size; volume normalized to min/max/step |
| concurrency | **max one active position per broker symbol**; no pyramiding, no averaging down |
| identity | one execution per RC5 semantic identity (symbol, timeframe, POI identity, direction, confirmation instance) |
| re-entry | none from the same POI identity; a genuinely new POI may create a new setup |
| exit | SL, TP, or a causal terminal/invalidation event on the owning POI |
| opposite signal | does **not** reverse a live position; a new opposite trade is blocked while one is active |
| prohibited | martingale, grid, averaging down, lot multiplication after losses, recovery sizing |
| live execution | `InpExecutionEnabled` defaults **FALSE**; tester configs may enable it |

## Unresolved, and deliberately not guessed

1. **Which "POI distal boundary"** — zone bottom for a BUY and zone top for a
   SELL is the obvious reading, but a POI whose direction and zone orientation
   disagree has no stated rule. V1 uses the directional reading and logs it.
2. **Terminal-event mapping.** The exact set of terminal / invalidation events
   that should close a live position has not yet been enumerated against the
   lifecycle module. V1 must not close on "an opposite pattern appeared", so
   this list has to be explicit before EA2-B.
3. **Whether `LIQUIDITY_VALIDATED` is reachable for every POI family**, or only
   those carrying liquidity evidence. If some families never reach it, V1 would
   silently never trade them — that must be measured, not assumed.

These are execution-layer questions. None of them justifies changing `28d432e`.
