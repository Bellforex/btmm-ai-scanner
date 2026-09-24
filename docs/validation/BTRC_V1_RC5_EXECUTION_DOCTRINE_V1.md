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

---

# Unresolved item 3 — RESOLVED: terminal / invalidation event inventory

Source: `poi/enums.py` (`PoiLifecycleStatus`, `PoiTerminalReason`) and
`poi/rc5_semantics.py::rc5_validity`, which is the frozen engine's own answer
to "does this zone still stand?".

## The safety-critical finding

`PoiTerminalReason.MITIGATED` **must not close a V1 position.**

`rc5_validity` says so directly — *"MITIGATION IS NOT TERMINATION.
`terminal_reason = MITIGATED` is set at the FIRST TOUCH and says only that
price has been in the zone."*

For an execution layer that enters AT a POI, first touch **is the entry**.
Closing on `MITIGATED` would close every trade at the moment it opened. This is
the single most dangerous mapping available and it is explicitly wrong.

## Inventory

| state / reason | meaning | cancels pending setup? | invalidates entry permission? | **closes live V1 position?** | rationale |
| --- | --- | --- | --- | --- | --- |
| `NO_BREACH` | zone intact | no | no | **NO** | nothing happened |
| `CLOSE_BREACH_CANDIDATE` | a close went through the far side, unconfirmed | no | no | **NO** | candidate only; the walk has not resolved |
| `RECLAIM_PENDING` / `RECLAIM_CONFIRMED` | price came back through the boundary | no | no | **NO** | reclaim is the zone SURVIVING |
| `DISPLACEMENT_PENDING` / `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` | the move the POI predicted | no | no | **NO** | this is the thesis working |
| `RECLAIM_WITHOUT_DISPLACEMENT` | reclaimed, no follow-through | no | no | **UNRESOLVED** | zone stands but the thesis is weak; V1 has no doctrine for "stale but valid" |
| `RECLAIM_FAILED` | reclaim attempt failed | no | no | **UNRESOLVED** | leads toward genuine invalidation but is not itself terminal |
| `FALSE_INVALIDATION_CONFIRMED` | far-side break that was reclaimed | no | no | **NO** | `rc5_validity` keeps this **VALID** — closing here would exit exactly the trap the doctrine exists to survive |
| **`GENUINE_INVALIDATION_CONFIRMED`** | confirmed failure through the far side | **yes** | **yes** | **YES** | `rc5_validity` -> `INVALIDATED`. The zone failed |
| **`PoiTerminalReason.INVALIDATED`** | coarse form of the above | **yes** | **yes** | **YES** | same event, coarser vocabulary |
| `PoiTerminalReason.MITIGATED` | price traded the zone (FIRST TOUCH) | no | no | **NO — never** | see above; this is the entry itself |
| `PROMOTED_TO_ORDER_BLOCK` | engulfing superseded by its own ORDER BLOCK | no | no | **UNRESOLVED** | `rc5_validity` -> `SUPERSEDED`. The identity changed; the price level did not. Re-labelling is not failure, but V1 has no rule for an owning POI that becomes a different POI |

## Approved V1 close events

Exactly two, and they are the same event at two granularities:

* `PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED`
* `PoiTerminalReason.INVALIDATED`

Nothing else closes a live position. In particular V1 does **not** close on an
opposite pattern, a trend change, a newly authoritative POI, mitigation, or a
false invalidation — none of which the frozen engine treats as the zone failing.

Note the symmetry with Track B: the approved close is confirmed failure through
the **distal** boundary, which is where the V1 stop already sits. So the stop
normally fires first and the event is a backstop, not a parallel exit rule.

## Still unresolved (3, narrow)

1. `RECLAIM_WITHOUT_DISPLACEMENT` — valid but thesis unproven.
2. `RECLAIM_FAILED` — en route to invalidation, not yet terminal.
3. `PROMOTED_TO_ORDER_BLOCK` — owning POI becomes a different POI.

All three are "the zone still exists but something changed" cases. V1
deliberately holds the position in each: the stop and the approved close events
already bound the risk, and inventing an exit here would be exactly the
strategy invention this layer is forbidden to do.

---

## EA2-B — V1 implemented in MQL5

`mt5/Experts/RC5_EA.mq5`. Six blocks, each compiled to **0 errors, 0 warnings**
before the next was written.

| block | what it adds | where |
| --- | --- | --- |
| B1 | eligibility, Layer-B states, `RC5Plan`, signal identity | `RC5PlanEligibility` |
| B2 | entry, distal stop, 2R target, broker level validation | `RC5PlanPrices` |
| B3 | 0.5% risk sizing and volume normalization | `RC5PlanRisk` |
| B4 | one-per-signal and one-per-symbol guards | `RC5PlanGuards` |
| B5 | terminal-event policy table | `RC5TerminalPolicy` |
| B6 | the single execution adapter | `SubmitOrder` / `CloseRC5Position` |
| B7 | reference-state fixture feed (tester/parity only) | `DispatchFixtures` |

### Two decisions this layer made, and why

**A minimum lot that would exceed the risk budget is DENIED, not taken.**
`NormalizeVolume` clamps up to `SYMBOL_VOLUME_MIN`, so a small account plus a
wide stop silently produces a trade larger than 0.5%. V1 quantizes DOWN first,
without clamping, and refuses with `RISK_BUDGET_EXCEEDED` when the floor falls
below the minimum lot. That is the volume counterpart of never widening a stop:
the layer does not quietly take a bigger trade than it was authorized to take.

**A fifth execution gate, which only ever tightens.** `CanExecuteHere()` calls
the existing `CanExecuteLive()` (input + terminal + account + expert) and then
requires EITHER `MQL_TESTER` OR `InpAllowLiveExecution`, which defaults false.
The consequence is worth stating plainly: the tester `.set` files carry
`InpExecutionEnabled=true`, and since this gate exists **those files can no
longer arm a live account even if loaded onto a live chart**.

### Deny reasons, complete

`NO_STATE`, `NOT_AUTHORITATIVE`, `NOT_VALID`, `NO_P5`, `NOT_CONFIRMED`,
`NO_DIRECTION`, `SIGNAL_ALREADY_EXECUTED`, `SYMBOL_POSITION_ACTIVE`,
`SPEC_INVALID`, `NO_QUOTE`, `STOP_WRONG_SIDE`, `BROKER_STOP_INVALID`,
`BROKER_TARGET_INVALID`, `SPREAD_TOO_WIDE`, `RISK_MODEL_INVALID`, `NO_EQUITY`,
`RISK_BUDGET_ZERO`, `RISK_BUDGET_EXCEEDED`, `VOLUME_INVALID`,
`EXECUTION_DISABLED`, `ORDER_SEND_FAILED_<retcode>`,
`ORDER_REJECTED_<retcode>`.

### Safe mode is the default, and it is the parity instrument

With execution disabled the ENTIRE pipeline runs and emits `RC5PLAN … 
WOULD_EXECUTE` carrying signal id, symbol, timeframe, direction, confirmation
and decision timestamps, entry, SL, TP, R, risk %, risk money, realized risk,
volume, spread, lifecycle trigger and Layer-B state. The only thing that does
not happen is the `OrderSend`, which is what makes that line a faithful preview.

### The EA has no detector, deliberately

`InpSetupFile` reads analytical state EXPORTED from the reference engine. It is
not a signal source. With no file configured — the default — the EA dispatches
nothing at all, because a third independent implementation of RC5 in MQL5 is
precisely what this architecture is avoiding.

### Not claimed

No MQL5 runtime test was executed and no Strategy Tester run has happened:
launching one needs a terminal start with a custom config, which this
environment denies. `tests/unit/test_rc5_ea_doctrine_vectors.py` pins the
arithmetic in Python and asserts the MQL5 source states the same rules, which
is an offline agreement check, not a runtime proof.

---

## TRACK F — the three unresolved states, TRACED (evidence, not a decision)

The author's instruction stands: **do not invent close behaviour**. V1's
runtime behaviour is unchanged — all three are recognized, logged
`TERMINAL_POLICY_UNRESOLVED`, and neither close nor reverse a position. What
follows is what the FROZEN ENGINE actually does with them, so the decision can
be made from evidence.

### The structural fact that separates them

Two of the three are not terminal reasons at all. `RECLAIM_WITHOUT_DISPLACEMENT`
and `RECLAIM_FAILED` are members of **`PoiLifecycleStatus`**;
`PROMOTED_TO_ORDER_BLOCK` is a member of **`PoiTerminalReason`**. Different
enums, consumed by different code.

| state | enum | sets `terminal`? | `rc5_validity` | what the walk does next |
| --- | --- | --- | --- | --- |
| `RECLAIM_WITHOUT_DISPLACEMENT` | `PoiLifecycleStatus` | **no** | **VALID** | `i = reclaim_index + 1; continue` |
| `RECLAIM_FAILED` | `PoiLifecycleStatus` | **no** | **VALID** | `i = window_end; continue` |
| `PROMOTED_TO_ORDER_BLOCK` | `PoiTerminalReason` | yes | **SUPERSEDED** | record ends; the formation lives on as the OB |

Compare `GENUINE_INVALIDATION_CONFIRMED` in the same walk, which sets
`terminal = True` explicitly. Neither reclaim state does.

### What that means for each of the author's four questions

**`RECLAIM_WITHOUT_DISPLACEMENT`** — far side was breached, price reclaimed the
zone, but no displacement followed. The walk CONTINUES from the reclaim bar and
the POI stays VALID. Evidence says: **state migration only.** It cancels no
pending setup, removes no execution permission and does not touch a position.
It is an intermediate state on the way to either false or genuine invalidation,
and it may still become either.

**`RECLAIM_FAILED`** — the reclaim window expired without a qualifying reclaim.
Same shape: status recorded, walk continues, POI stays VALID. Evidence says:
**state migration only.** Note it is NOT the same as invalidation; the walk
reaches `GENUINE_INVALIDATION_CONFIRMED` by a different branch that does set
`terminal`.

**`PROMOTED_TO_ORDER_BLOCK`** — genuinely different. It IS terminal, and
`rc5_validity` maps it to SUPERSEDED, not INVALIDATED, with the explicit
comment that it is "NOT a failure". The RC3 movement-origin rule ends an
engulfing record when its ORDER BLOCK record becomes available so that one
formation never has two live records. `apply_order_block_promotion` also keeps
an EARLIER cause: a zone price had already used stays MITIGATED.

For execution this splits cleanly:

* **New entries are already handled, with no new rule.** V1 requires
  `validity == VALID`, and SUPERSEDED is not VALID, so a promoted record can
  never open a position. That is existing behaviour, not a proposal.
* **An OPEN position is the open question.** The formation did not fail — it
  continues under the ORDER BLOCK record — so closing on promotion would exit a
  setup the engine still considers live, while ignoring it means the position is
  managed against a record that no longer updates.

### What is therefore still the author's to decide

Only one of the three is genuinely open, and only in one direction:

> When a position is open on an engulfing record that is then
> `PROMOTED_TO_ORDER_BLOCK`, does V1 (a) hold on the original stop and target,
> (b) migrate management onto the ORDER BLOCK record, or (c) close?

The two reclaim states have no such question attached: the frozen engine keeps
the POI VALID through both, so a close would contradict the analytical layer.
That is an observation about the code, **not** a doctrine change — V1 still
logs them and does nothing.

---

## SAFETY FINDING — ZERO-HEIGHT ZONES SIZE FROM A ONE-TICK STOP

Found by generating a real fixture file rather than by reading the doctrine.
**Not fixed here**, because fixing it means choosing a threshold, and thresholds
are the author's.

### What the data actually contains

Liquidity-level POIs are LINES, not bands. On the author's M15 EURUSD capture
the projection emits, verbatim:

```
EURUSD|15|1789724700|CURRENT_DAY_LOW~0c31feb6b40e|27|1|1.14831|1.14831|1|0|0|1
EURUSD|15|1789724700|CURRENT_MONTH_HIGH~3b57a668738a|30|-1|1.14865|1.14865|1|0|0|1
```

`zone_top == zone_bottom`. This is not malformed export; it is what a level is.

### What V1 as specified does with one

The distal boundary IS the level, so the stop lands one tick beyond it and R
collapses to the distance from entry to a single price. Measured, on a broker
publishing `STOPS_LEVEL = 0`:

| entry | R | volume | realized risk | budget |
| --- | --- | --- | --- | --- |
| 1.14832 | 2 ticks | **200.00** (`volume_max`) | 40.00 | 50.00 |
| 1.14840 | 10 ticks | 50.00 | 50.00 | 50.00 |
| 1.14900 | 70 ticks | 7.14 | 49.98 | 50.00 |

**Every risk gate passes.** The 0.5% budget is respected — realized risk on the
first row is 40.00 against a 50.00 budget, comfortably UNDER. Nothing is
violated. What bounds the first row is `volume_max`, which is a broker contract
limit, not a risk rule.

200 lots of EURUSD is roughly a 20,000,000 EUR notional held against a two-tick
stop. And a typical EURUSD spread is around ten ticks — **five times R** — so
the position is stopped out by the spread alone, by construction.

### Why nothing catches it

* The risk budget is satisfied, so no risk gate fires.
* `InpMaxSpreadPoints` compares the spread to a FIXED input, not to R, and
  defaults to 0 (off).
* V1 has no margin check and no notional cap, so the first refusal would be the
  broker's own margin rejection — at runtime, as `ORDER_REJECTED_<retcode>`.
* `SYMBOL_TRADE_STOPS_LEVEL` DOES refuse it when non-zero. That is the only
  existing protection, and it belongs to the broker: Exness Standard commonly
  publishes 0, in which case the protection is simply absent.

All four statements are pinned as tests in
`tests/unit/test_rc5_ea_doctrine_vectors.py`, which assert what V1 DOES rather
than what it should do.

### The author decisions this surfaces

1. **Should zero-height POIs be executable at all?** They are authoritative,
   valid analytical records; whether a level is a tradable zone for an
   execution layer is a doctrine question, not an implementation detail.
2. **Should V1 refuse when the spread is a significant fraction of R?** The
   input already exists; it currently compares against a constant rather than
   against R.
3. **Should V1 carry a notional or margin ceiling** independent of the risk
   budget, given that the budget alone does not bound position size when R is
   tiny?

Until these are answered the behaviour above stands, unchanged and documented.
It has never reached a live account: execution is disabled by default, the
trigger has never fired on any available capture, and no tester run has
occurred.
