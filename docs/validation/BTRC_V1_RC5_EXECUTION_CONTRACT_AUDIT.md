# Execution contract audit — the contract does not exist, by design

Traced against the frozen Python semantic authority `28d432e`, as the gate for
EA2. The result is not "some rules are missing". It is that the engine
**deliberately contains no execution layer at all**, and says so in its own
source.

## The engine's own scope statements

`src/btmm_ai_scanner/btrc/t5_decision.py`:

> There are deliberately NO operational fields (entry / stop / target / lot
> size / order id / execution command) — those belong to **future python-bot
> phases only**.

`src/btmm_ai_scanner/btrc/t5_engine.py`:

> It is explainable, **not a black-box trade generator**, and it **never
> produces entry/stop/target/order semantics**.

`src/btmm_ai_scanner/btrc/trend_assessment.py`:

> They contain NO confluence score, NO entry/stop/target, and NO trade
> instruction — trend classification is **supervisory only**.

## Corroborating search

Across all of `src/`:

```
stop_loss | take_profit | entry_price | position_size | risk_per | lot_size
-> 0 matches
```

Not "few". Zero. There is no order type, no risk model, no sizing formula, no
concurrency rule and no exit rule anywhere in the frozen engine.

## The 25 execution questions

| # | question | status |
| --- | --- | --- |
| 1-2 | what authorizes a BUY / SELL | **UNDEFINED** |
| 3 | does P5 authorize entry, or only permission | **ANALYTICAL PERMISSION ONLY** — `t5_engine` says it never produces order semantics |
| 4 | which P8 event triggers execution | **UNDEFINED** — P8 is an alert/event stream, not an order trigger |
| 5-7 | entry price; market or pending; pending type | **UNDEFINED** |
| 8-10 | SL; TP; RR fixed or structural | **UNDEFINED** |
| 11-12 | what cancels a signal / invalidates permission | **UNDEFINED** as execution; POI *validity* and terminal events exist as ANALYSIS |
| 13-14 | what closes a trade; what a terminal POI event does to a position | **UNDEFINED** |
| 15-18 | opposite signal; multiple positions; per symbol; multiple POIs | **UNDEFINED** |
| 19-21 | risk sizing; max risk per trade; max concurrent exposure | **UNDEFINED** |
| 22-25 | session / spread / news filters; re-entry | **UNDEFINED** |

Every one of the 25 is undefined. The only row that resolves does so by
*denying* the premise: P5 is an analytical permission, explicitly not an entry
authorization.

## What this means for the EA

EA1 was buildable because it is pure broker adaptation — symbol resolution,
tick/volume normalization, stop-distance validation, a safety gate. None of
that needed a strategy, which is exactly why it compiles 0/0 today.

**EA2 and EA3 cannot be built from `28d432e`.** Porting "the executable
semantic subset" presumes such a subset exists. It does not. Writing one would
mean inventing entry, stop, target, sizing, concurrency and exit rules — the
one thing every directive in this campaign has forbidden.

The scanner answers *"this is a valid POI, in this structural context, with
this analytical permission."* It does not answer *"buy here, risk this much,
stop there, target there."* That second layer was scoped as "future python-bot
phases" and has never been written.

## What is needed before EA2

An execution doctrine, authored the way the Base doctrine was: entry trigger,
entry price, order type, stop rule, target rule, cancellation, exit,
concurrency and risk model. Once those exist in Python — and are tested there —
the MQL5 port is mechanical, and EA1 is already waiting for them.

Nothing here blocks EA1, the Pine work, or the Strategy Tester configuration.
