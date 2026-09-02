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

### 3a. The minimal transport surface — traced, not assumed

An earlier draft of this section said P6 must supply "P1 and P2, six times
over". Tracing the actual field reads shows that overstates the job, in two ways
that matter.

**P1 publishes five collections; BTRC reads three.**

| P1 collection | read by BTRC? |
|---|---|
| `confirmed_swings` | yes — T1, T3 |
| `displacement_observations` | yes — T2, T3 |
| `equal_level_clusters` | yes — T3 |
| `support_resistance_zones` | **no — zero references** |
| `trendlines` | **no — zero references** |

The two nobody reads are the two most expensive to produce. S/R zones carry the
tracker and fold-cache machinery that dominated P3's difficulty and produced its
hardest divergences, so the higher-timeframe engines P6 stands up do not need
any of it.

**P2 publishes three semantic items; BTRC reads two** — `structure_transitions`
and `current_state`. `swing_relationships` is never referenced.

**P3 does NOT need to run on six timeframes.** T3's pullback assessment binds
`lifecycle = analysis.poi_analysis.poi_lifecycle_transitions` ONCE and hands the
same flat collection to every timeframe, rather than indexing it by timeframe
the way it does for swings and structure state. POI lifecycle transitions are a
symbol-level input, not a per-authority-timeframe one, so P3 stays exactly where
it is today.

So the per-authority-timeframe payload is **five things**:

```
P1: confirmed_swings, displacement_observations, equal_level_clusters
P2: structure_transitions, current_state
```

plus, once and not per authority timeframe:

```
P3: poi_analysis.poi_lifecycle_transitions, current_poi_states   (flat)
P4: btmm_analysis.btmm_observations                              (flat)
raw candles for the POI's timeframe only                         (T4 volatility)
a datetime                                                       (T4 session — no transport at all)
```

Pinned by `test_p6_mtf_contract.py` so a future widening has to be declared.

### 3b. Per-component input table (Phase 19)

§3a says what must be transported; this says which component needs each piece,
which is what determines implementation slicing.

| component | timeframes | P1 | P2 | P3 | P4 | raw candles | datetime |
|---|---|---|---|---|---|---|---|
| **T1** `assess_trend` | all six, authority order | `confirmed_swings` | `structure_transitions`, `current_state` | — | — | — | — |
| **T2** `assess_regime` | all six, **its own** `_PRIMARY_ORDER` | `displacement_observations` | — (inherits `trend_state` from T1) | — | — | — | — |
| **T3** `assess_momentum` | authority set | `displacement_observations` | — | — | — | — | — |
| **T3** `assess_breakout` | union of present | `displacement_observations`, `equal_level_clusters` | `structure_transitions` | — | — | — | — |
| **T3** `assess_pullback` | union of present | `confirmed_swings` | `current_state` | `poi_lifecycle_transitions` **(flat)** | — | — | — |
| **T4** `assess_volatility` | POI timeframe only | — | — | — | — | **yes** | — |
| **T4** `assess_session` | n/a | — | — | — | — | — | **yes** |
| **T5** `assess_confluence` | orchestrates all | via components | via components | `current_poi_states`, `poi_observations` | `btmm_observations` | via T4 | via T4 |

Three consequences for slicing:

* **T2 reads no structure of its own.** It takes displacement plus T1's
  `trend_state`, so implementing T2 before T1 leaves it with no source for its
  own input. The DAG order is not a style preference.
* **`assess_pullback` is the only consumer of POI lifecycle**, and it takes the
  flat collection. No other component references it at all.
* **T5 cannot be sliced early** — it calls all seven assessments, so it is the
  last slice by construction.

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

## 5a. Quantified history requirement — the hard number

P1 declares its own warm-up in the Pine source:

```
C_P1_MIN_CALC_BARS = lookbackWindow + warm-up = 300 + 950 = 1250
C_P1_CALC_BARS     = 1800
```

**1250 confirmed bars per timeframe**, before P1 produces anything. Applied to
the six required timeframes:

| TF | warm-up span at 1250 bars |
|---|---|
| M5 | 4.3 days |
| M15 | 13.0 days |
| H1 | 52.1 days |
| H4 | 208.3 days (~7 months) |
| D1 | 1250 days (**3.4 years**) |
| W1 | 8750 days (**24 years**) |

An M15 chart at `calc_bars_count = 1800` spans **18.75 days — about 2.7 weeks**.

Two consequences, both firm:

1. **Aggregating the higher timeframes from chart bars is impossible.** Building
   W1 candles out of the chart's own 1800 M15 bars yields about **2 W1 bars
   against the 1250 P1 needs** — wrong by three orders of magnitude. The same
   holds for D1 (3.4 years needed, 18.75 days available) and H4. So a
   "bucket the chart bars" design is not merely inefficient, it cannot work.

2. **`request.security` is therefore mandatory for H1, H4, D1 and W1**, which
   makes the two open questions in §5 unavoidable rather than optional: whether
   the array-mutating engine can be evaluated in another timeframe's context at
   all, and whether TradingView will deliver ~1250 W1 bars (24 years of weekly
   XAUUSD) and ~1250 D1 bars to a script whose chart timeframe is M15.

Both are measurable, and neither has been measured. That is the whole of the
implementation gate: not a preference between designs, but an unanswered
question about whether any design exists.

An honest third possibility has to stay on the table — that the P1 warm-up
constant, validated for intraday timeframes, is simply not the right contract
for W1, and that P6 would need an author decision about higher-timeframe warm-up
rather than a Pine trick. That is a semantics question, not an engineering one,
and it is out of scope here.

## 5b. Progress against the two gates

**Gate 2 (P1/P2 unverified on W1/D1/H4/H1) — CLEARED on the Python side.**
`tests/unit/test_p1_p2_higher_timeframe_oracle.py` (commit `35f2e67`) proves on
real bars that P1 and P2 produce identical swings, displacement, equal levels,
S/R zones, structure transitions and current state across all six authority
timeframes. The structural reason is asserted directly too: neither layer
contains a single branch on which timeframe it was given. So M15 correctness
transfers to W1/D1/H4/H1/M5 as a property of the algorithm, and feeding the
engine genuine weekly bars is a DATA problem rather than a correctness one.

What that does not settle is real higher-timeframe market data: it shows the
engine is indifferent to the label, not that weekly gold resembles re-timed M15
gold. Real-data parity per timeframe still needs captures.

**Gate 1 (Pine feasibility) — experiment written, NOT YET RUN.**
`tradingview/p6_feasibility_lab.pine` is ready and answers exactly three
questions, none of which should be reasoned about:

* **Q1 history depth** — does `request.security` hand a script hosted on M15
  the ~1250 W1 and D1 bars P1 requires, or far fewer?
* **Q2 per-context mutable state** — the decisive one. The probe declares a
  `var array<float>` *inside* the requested expression and reports its size. If
  the array is instantiated per security context and accumulates across that
  timeframe's bars, then a six-timeframe P1+P2 substrate is expressible and P6
  has a design. If it is not, P6 needs a different one.
* **Q3 lookahead** — the context bar time is reported alongside the chart time
  so the default can be checked rather than trusted.

It uses six `request.security` calls, well inside Pine's per-script limit.

**Blocked on environment, not on engineering.** The lab needs the
`bellcare1994` session on layout `bellforex`; the browser profile currently has
no TradingView session, and signing in is out of bounds. The moment a session
exists the lab is one paste-and-compile away from settling both questions.

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
PER-TF PAYLOAD             3 P1 collections + 2 P2 items (NOT S/R, NOT trendlines)
P3 PER TF                  NOT REQUIRED (POI lifecycle is read flat)
ABSENCE BEHAVIOUR          degrade to NEUTRAL, never raise
STALENESS                  hold-last-confirmed
SAME-TIMESTAMP ORDER       not observable (fixed authority order + rank sort)
P1 WARM-UP PER TF          1250 bars (W1 = 24 years, D1 = 3.4 years)
CHART-BAR AGGREGATION      IMPOSSIBLE (M15x1800 = 2.7 weeks ~ 2 W1 bars)
request.security           MANDATORY for H1/H4/D1/W1, feasibility UNMEASURED
FEASIBILITY EXPERIMENT     NOT RUN  <-- implementation gate
P1/P2 TIMEFRAME-AGNOSTIC   PROVEN on real bars, all six TFs (35f2e67)
P1/P2 REAL-DATA PER TF     still needs captures for W1/D1/H4/H1
FEASIBILITY LAB            WRITTEN (p6_feasibility_lab.pine), NOT RUN
LAB BLOCKER                no TradingView session in the browser profile
P6 IMPLEMENTATION          NOT STARTED
```
