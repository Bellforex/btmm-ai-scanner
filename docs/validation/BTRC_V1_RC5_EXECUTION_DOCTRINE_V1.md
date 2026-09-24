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

---

# Unresolved item 1 — RESOLVED: the trigger is family-agnostic

Traced rather than counted, which is the stronger answer.

## The transition path

There is exactly ONE place in the entire engine that assigns any
`SignalLifecycleState`: `btrc/t5_engine.py::_lifecycle`. Every one of the eight
analytical states is assigned there and nowhere else — verified by search, one
occurrence each outside the enum definition.

```python
def _lifecycle(*, has_structure, btmm_valid, alignment,
               favorable_regime, momentum_aligned, liquidity_ok)
        -> SignalLifecycleState
```

A monotone ladder, six gates, early return at the first failure:

| gate | reaches |
| --- | --- |
| `has_structure` | `STRUCTURALLY_VALIDATED` |
| `btmm_valid` | `BTMM_VALIDATED` -> `POI_VALIDATED` (unconditional step: *"poi is the evaluated candidate"*) |
| `alignment in (ALIGNED, PARTIAL)` | `TREND_VALIDATED` |
| `favorable_regime` | `REGIME_VALIDATED` |
| `momentum_aligned` | `MOMENTUM_VALIDATED` |
| `liquidity_ok` | **`LIQUIDITY_VALIDATED`** |

## The finding

**The function takes six booleans and no POI type, kind or family.** There is
no family branch, no family whitelist and no family-specific early return
anywhere on the path.

So **no POI family is structurally excluded from `LIQUIDITY_VALIDATED`.** Its
reachability is a function of market conditions — structure, BTMM validity,
trend alignment, regime, momentum, liquidity — and never of what kind of POI is
being evaluated.

## Verdict — CASE A

**The V1 confirmation trigger stays `LIQUIDITY_VALIDATED`.** The concern that
some families might silently never trade does not hold at the semantic level:
the ladder cannot discriminate by family because it is never told the family.

This is a stronger result than a reachability count would have been. A count
says "family X did not reach it in this capture", which confuses *absence of
opportunity* with *structural impossibility*. The source says the second cannot
happen.

### The smaller question that remains

The ladder is family-blind, but two of its INPUTS are computed upstream:
`btmm_valid` and `liquidity_ok`. If either is itself family-dependent, a family
could still be effectively excluded one level up. That is a narrower question
than the original, and it is the one worth measuring next — not whether the
trigger discriminates, but whether its inputs do.

Nothing here changes `28d432e`.

## Upstream input audit — CASE A confirmed end to end

The ladder is family-blind; the remaining question was whether its six inputs
are. Traced at the single call site, `btrc/t5_engine.py:378`:

| input | expression | source dimension | uses POI type/kind/family? |
| --- | --- | --- | --- |
| `has_structure` | `bool(trend.timeframe_assessments)` | T1 trend | **no** |
| `btmm_valid` | `btmm is not None` (line 222) | BTMM setup presence | **no** |
| `alignment` | trend-direction comparison (lines 240-252) | T1 trend | **no** |
| `favorable_regime` | `regime_value in _FAVORABLE_REGIME` | T2 regime | **no** |
| `momentum_aligned` | `momentum_score >= 60` | T3 momentum | **no** |
| `liquidity_ok` | `liquidity_score >= 60` | liquidity dimension | **no** |

Every one is a supervisory BTRC dimension — trend, regime, momentum, liquidity
— or a presence check on the BTMM setup object. **Not one is computed from the
POI's type, kind or family.**

### FINAL VERDICT — CASE A

**`LIQUIDITY_VALIDATED` is the FINAL Execution Doctrine V1 confirmation
trigger.** No POI family is structurally excluded, at the ladder or above it.
Unresolved item 1 is closed.

Reachability is therefore purely a market-conditions question: a family trades
when trend, regime, momentum and liquidity agree and a BTMM setup exists — and
never fails to trade because of what kind of POI it is.

## Pine capacity — candidate REJECTED on reasoning, not measured

`f_rc5IsReversal` (a 13-term `or` chain) and `f_rc5LadderRank(ty) < 99` were
proved to cover **exactly the same 13 types** — the Pine ladder's seven rank
groups enumerate precisely the 13 members of Python's `REVERSAL_LADDER`. So the
merge is semantically sound.

It is still **rejected**: `f_rc5IsReversal` has ONE call site, and Pine inlines
user functions, so replacing a 13-term chain with an inlined 13-comparison,
7-ternary ladder is a wash at best and probably a loss. Recorded here so a
later unit does not spend compiler round-trips rediscovering it.

Candidates 1 and 4-7 (dead locals, zone-equality, source-span, authority
temporaries, dead legacy) remain unmeasured.

---

# Unresolved item 2 — RESOLVED: the distal boundary is already defined

Not assumed from "bullish = bottom". Read out of the frozen lifecycle, which
already has to answer exactly this question to decide when a POI dies.

`src/btmm_ai_scanner/poi/lifecycle.py`:

```python
def _is_breach(candle, direction, zone_top, zone_bottom, overshoot_tolerance):
    if direction == PoiDirection.BULLISH:
        return (zone_bottom - candle.close) > overshoot_tolerance
    return (candle.close - zone_top) > overshoot_tolerance

def _is_displacement(candle, direction, zone_top, zone_bottom, contact_tolerance):
    if direction == PoiDirection.BULLISH:
        return candle.close >= zone_top + contact_tolerance
    return candle.close <= zone_bottom - contact_tolerance
```

`_is_breach` is the FAR side — the edge whose violation the engine treats as a
genuine failure of the zone. `_is_displacement` is the near side, the direction
the POI is supposed to push price. Together they define proximal and distal
without a word of interpretation:

| direction | proximal (displacement side) | **distal (breach side)** | source |
| --- | --- | --- | --- |
| BULLISH | `zone_top` | **`zone_bottom`** | `lifecycle.py` `_is_displacement` / `_is_breach` |
| BEARISH | `zone_bottom` | **`zone_top`** | same |

## No family is ambiguous

All three boundary functions take `(candle, direction, zone_top, zone_bottom,
tolerance)`. **None of them receives a POI type, kind or family**, and none
branches on one — the same shape as the lifecycle ladder. So the mapping is
uniform across every executable family by construction, and the
per-family ambiguity table has one row:

| POI family | direction | proximal | distal | ambiguous |
| --- | --- | --- | --- | --- |
| **all executable families** | BULLISH | `zone_top` | `zone_bottom` | **no** |
| **all executable families** | BEARISH | `zone_bottom` | `zone_top` | **no** |

`_is_reclaim` uses the same edges as `_is_breach` (bullish `zone_bottom`,
bearish `zone_top`), which corroborates the reading: breach and reclaim are
the two directions across one boundary, and that boundary is the distal one.

## V1 stop rule — LOCKED

```
BUY   SL = zone_bottom - 1 executable tick
SELL  SL = zone_top    + 1 executable tick
```

one tick via `SYMBOL_TRADE_TICK_SIZE`, never `_Point`.

This is a stronger result than picking a convention. **The V1 stop sits exactly
one tick beyond the boundary whose violation the frozen engine already calls
genuine invalidation.** The execution layer and the analytical layer therefore
agree by construction: the trade dies at the same price the POI does, not at a
number the execution layer invented.

Unresolved item 2 is closed.
