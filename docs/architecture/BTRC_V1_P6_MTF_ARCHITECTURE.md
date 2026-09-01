# BTRC-V1 P6 — Cross-Timeframe Substrate: Architecture

Status: **P6-A0 architecture — derived. Implementation GATED on a feasibility experiment.**
Branch: `pine-p4-btmm`
Predecessor: [P5 BTRC architecture (author-accepted)](BTRC_V1_P5_BTRC_ARCHITECTURE.md)

P6 exists for exactly one reason: `P5_REQUIRES_P6 = TRUE`. It is scoped to what
P5 actually reads and nothing else. Every requirement below was read out of
production source.

---

## 1. The requirement, from source

`trend_engine._resolve_global` reduces three timeframes to one value:

```python
d1 = direction_by_tf.get(Timeframe.D1)
w1 = direction_by_tf.get(Timeframe.W1)
h4 = direction_by_tf.get(Timeframe.H4)
if d1 in _BULLISH_SIDE:
    if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
        return Direction.STRONG_BULLISH
    return Direction.BULLISH
...
```

`global_direction` feeds `TrendAlignment`, which feeds `AnalyticalPermission` —
P5's primary output. It does not exist until W1, D1 and H4 are all in hand.

## 2. `P5_REQUIRED_TFS` and roles

```python
_AUTHORITY_TIMEFRAMES = (W1, D1, H4, H1, M15, M5)
```

| TF | role | changes `global_direction`? |
|---|---|---|
| **W1** | macro context; also reported as `macro_context` | yes — strengthens to `STRONG_*`, and with H4 can set a provisional direction when D1 is neutral |
| **D1** | **primary authority** | yes — alone decides BULLISH / BEARISH |
| **H4** | operational context; reported as `operational_context` | yes — same two roles as W1 |
| **H1** | per-timeframe assessment only | **no** |
| **M15** | per-timeframe assessment only | **no** |
| **M5** | per-timeframe assessment only | **no** |

The docstring is explicit: *"H1/M15/M5 NEVER change global direction."* They still
populate `direction_by_tf` and the per-timeframe assessment list, so they are
required — but only three timeframes are load-bearing for the fusion.

Note the overlap with P4: P4's supported set is `{M1, M5, M15}`; P5's authority
set is `{W1, D1, H4, H1, M15, M5}`. **They meet only at M5 and M15.** P5 needs
four timeframes P4 never touches, and needs no M1.

## 3. What must be transported per timeframe

Derived from what each engine reads off `ScannerAnalysis`:

| engine | reads | per-TF? |
|---|---|---|
| T1 trend | `measurement_analyses.confirmed_swings`, `structure_analyses.structure_transitions`, `structure_analyses.current_state` | all 6 |
| T2 regime | `measurement_analyses` | all 6 |
| T3 momentum / breakout / liquidity | `measurement_analyses`, `structure_analyses`, `poi_analysis` | per POI timeframe |
| T4 volatility / session | raw candles via `candles_by_timeframe` | POI timeframe only |
| T5 aggregation | the above + `btmm_analysis.btmm_observations` | — |

So P6 must supply, on six timeframes: **P1 `MarketMeasurementAnalysis` and P2
`StructureAnalysis`**, plus candles for T4.

This is the central scope fact: P6 is not a thin projection. It is the P1 and P2
substrate, six times over.

## 4. Chronology, staleness and absence — source behaviour

**Absence degrades; it never raises.**

```python
for timeframe in _AUTHORITY_TIMEFRAMES:
    if timeframe not in swings_by_tf and timeframe not in state_by_tf:
        continue
```

A timeframe with neither swings nor structure state is skipped: no assessment,
and it is absent from `direction_by_tf`. `_resolve_global` then reads it as
`None`, and `None` is in neither `_BULLISH_SIDE` nor `_BEARISH_SIDE`, so:

* D1 absent → falls through to the W1+H4 branch;
* W1 or H4 absent → no `STRONG_*`, and no provisional direction from that branch;
* all three absent → `Direction.NEUTRAL`.

There is no exception, no sentinel, and no "unknown" state. A Pine port must
reproduce exactly this degradation rather than blocking on a missing feed.

**Staleness** is implicit and must be preserved: a W1 assessment computed at the
last W1 close remains the W1 direction for every intervening lower-timeframe bar.
Hold-last-confirmed is the required transport semantic.

**Ordering** inside `assess_trend` is deterministic and independent of arrival:
the loop walks `_AUTHORITY_TIMEFRAMES` in fixed order and the assessment list is
then sorted by `_TIMEFRAME_RANK`. Simultaneous closes therefore cannot reorder
the result — a useful property, because it means P6 does not have to reproduce a
same-timestamp arrival order.

## 5. The feasibility gate — why implementation is not yet authorized

The existing Pine engine keeps **128 global `var array<...>`** structures that it
mutates once per confirmed bar: the analytical window, the pivot frontier, the
S/R trackers and fold caches, the structure walk, the POI registry, the BTMM
registry. That design is what made P1–P4 provable, and it is exactly what makes
naive cross-timeframe transport not work.

`request.security(sym, tf, expr)` evaluates *an expression* in another
timeframe's context. It does not re-run a script's global per-bar array
mutations six times. So "add six `request.security` calls" is not a design — the
question of how (or whether) a six-timeframe P1+P2 substrate can exist inside one
Pine script is open and must be **measured**, not reasoned about.

Phase 22 of the campaign is the right instrument: small isolated experiment
scripts that establish, for the six required timeframes,

* whether the P1/P2 computation can be expressed inside `request.security` at all,
  given its array-mutating shape;
* closed-bar semantics and absence of lookahead at each timeframe boundary;
* history depth actually delivered for W1/D1/H4 under `calc_bars_count`;
* the unique `request.*` budget and whether packing keeps it inside limits;
* behaviour on gaps, weekends and reload.

Until those numbers exist, any P6 implementation plan would be speculation.

**Second gate, equally serious:** P1 and P2 are closed **on M15 only**; P3 was
extended to M5. The parity artifacts on disk cover `M15`, `M5` and `M1` and
nothing else. W1, D1, H4 and H1 have **never been parity-verified at any layer**.
P6 would be standing six P1+P2 substrates up on four timeframes with no
established correctness baseline, so extending P1/P2 real-data parity to at least
W1, D1 and H4 is a prerequisite of P6 closure, not a follow-up.

## 6. Minimal P6 scope, when authorized

**P6 CORE**: transport of P1 `MarketMeasurementAnalysis` and P2
`StructureAnalysis` for `{W1, D1, H4, H1, M15, M5}`, with hold-last-confirmed
staleness, source-exact absence degradation, and candles for the POI timeframe.

**P6 DEFERRED**: anything not read by P5 — no generic MTF framework, no
timeframes outside the authority set, no M1 (P5 never reads it).

## 7. Status

```
P6 ARCHITECTURE            DERIVED
P5_REQUIRED_TFS            W1, D1, H4, H1, M15, M5
LOAD-BEARING FOR FUSION    W1, D1, H4
PER-TF PAYLOAD             P1 measurements + P2 structure (+ candles for T4)
ABSENCE BEHAVIOUR          degrade to NEUTRAL, never raise
STALENESS                  hold-last-confirmed
SAME-TIMESTAMP ORDER       not observable (fixed authority order + rank sort)
FEASIBILITY EXPERIMENT     NOT RUN  <-- implementation gate
P1/P2 PARITY ON W1/D1/H4   NOT ESTABLISHED  <-- closure gate
P6 IMPLEMENTATION          NOT STARTED
```
