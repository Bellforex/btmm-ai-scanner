# BTRC-V1 P5 — Confluence Layer: Pine Architecture (AUDIT ONLY)

Status: **P5-A0 architecture audit — complete and AUTHOR-ACCEPTED.**
Branch: `pine-p4-btmm`
Predecessor: [P4 BTMM CORE closure](BTRC_V1_P4_BTMM_CLOSURE.md)

Every claim below was read out of production source. Where a conclusion reverses
a plausible assumption, the source proof is quoted.

---

## 1. The headline: P5 is genuinely multi-timeframe, and P4 was not

This is the opposite of the P4 finding, and it matters more than anything else
here.

For P4, a `tuple[BtmmTimeframeInput, ...]` signature *looked* multi-timeframe and
was not: each setup observed only its own POI's timeframe, and a combined call
equalled the union of independent single-timeframe calls. That let P4 ship as a
faithful single-chart port with no `request.security`.

BTRC does not have that property. `trend_engine._resolve_global` reads three
timeframes **at once** and reduces them to a single `global_direction`:

```python
def _resolve_global(direction_by_tf: dict[Timeframe, Direction]) -> Direction:
    """Deterministic authority resolver. D1 is primary; W1 macro + H4 operational
    agreement can strengthen it; H1/M15/M5 NEVER change global direction."""
    d1 = direction_by_tf.get(Timeframe.D1)
    w1 = direction_by_tf.get(Timeframe.W1)
    h4 = direction_by_tf.get(Timeframe.H4)
    if d1 in _BULLISH_SIDE:
        if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
            return Direction.STRONG_BULLISH
        return Direction.BULLISH
    ...
```

`global_direction` is not a per-timeframe fact assembled later. It is a value that
does not exist until W1, D1 and H4 are all in hand, and it feeds `TrendAlignment`,
which feeds `AnalyticalPermission` — the layer's primary output.

```
P5_REQUIRES_P6 = TRUE
```

with source proof. A single-chart Pine port of P5 cannot produce
`global_direction`, and therefore cannot produce `analytical_permission`, without
cross-timeframe transport. **P6 is a hard prerequisite for P5 CORE**, not an
optimisation.

The authority set is explicit and already narrower than the enum vocabulary:

```python
# T1 authority hierarchy (validated timeframes only; H6/H8/H12 deferred).
_AUTHORITY_TIMEFRAMES = (W1, D1, H4, H1, M15, M5)
```

Six timeframes, of which three (W1, D1, H4) are load-bearing for the global
resolve. Note that **P4's supported set is {M1, M5, M15}** and P5's authority set
is {W1, D1, H4, H1, M15, M5} — they overlap only at M5 and M15. A P5 port needs
timeframes P4 never touches.

---

## 2. Entry point and shape

| | |
|---|---|
| Package | `src/btmm_ai_scanner/btrc/` — 17 files, 2281 lines |
| Final entry | `t5_engine.assess_confluence(analysis, poi, *, candles_by_timeframe, evaluation_time_utc, configuration) -> BtrcDecision` |
| Component entries | `assess_trend`, `assess_regime`, `assess_momentum`, `assess_breakout`, `assess_pullback`, `assess_volatility`, `assess_session` |
| Output | `BtrcDecision` — 27 fields, of which `ComponentScores` is 8 |
| Vocabulary | 14 enums |

**BTRC is not wired into the scanner.** `assess_confluence` has no caller in
`src/` outside the package's own `__init__` re-export; every invocation in the
repository is from tests. It is a standalone supervisory layer that takes a
finished `ScannerAnalysis` plus one POI and returns one decision. That is a
scoping fact a Pine port has to reckon with: there is no existing production
orchestration to mirror.

---

## 3. Dependency matrix

Read from actual attribute access, not from imports.

| Upstream | What P5 reads |
|---|---|
| **P1 measurements** | `confirmed_swings`, `displacement_observations`, `equal_level_clusters`, `timeframe` — **per timeframe** |
| **P2 structure** | `structure_transitions`, `current_state`, `timeframe` — **per timeframe** |
| **P3 POI** | `poi_observations`, `current_poi_states`, `poi_lifecycle_transitions` |
| **P4 BTMM** | `btmm_analysis.btmm_observations` — **only** |
| Candles | `candles_by_timeframe` (optional, for T4 volatility/session) |

Three consequences:

1. **P5 depends heavily on P1 and P2, unlike P4.** P4 read no P1 detector output
   and nothing from P2. P5 reads swings, displacements, equal-level clusters,
   structure transitions and current structure state — per timeframe. A P5 port
   therefore re-inherits the entire P1+P2 surface across six timeframes.

2. **`P5_REQUIRES_P3_CONTEXT = FALSE`.** T3 does consume `equal_level_clusters`
   to distinguish `LIQUIDITY_SWEEP`, but it takes them from
   `MarketMeasurementAnalysis` (P1), not from the deferred P3 CONTEXT POI types.
   Searching the package for `EQUAL_HIGHS_LIQUIDITY`, `PREVIOUS_DAY_*`,
   `CURRENT_WEEK_*` and the other calendar levels returns nothing. **P3 CONTEXT
   can stay deferred.**

3. **`P4_TO_P5_CONTRACT_COMPLETE = TRUE`.** BTRC reads
   `btmm_analysis.btmm_observations` and nothing else from P4:

   ```python
   btmm = next((b for b in analysis.btmm_analysis.btmm_observations
                if b.source_poi_record_id == poi.record_id), None)
   btmm_valid = btmm is not None
   ```

   From a matched observation it uses exactly three attributes: **existence**
   (`btmm_valid`), **`btmm_direction`** (`t5_engine.py:178`, for the bullish /
   bearish side), and **`record_id`** (`t5_engine.py:260`, for provenance). An
   earlier draft of this section called that "one field", which understated it —
   it is one collection read yielding three used attributes.

   What matters is what it does NOT read. Searching the whole `btrc` package for
   `BtmmLifecycleStatus`, `BTMM_CONFIRMED`, `current_btmm_states` and
   `btmm_lifecycle` returns **nothing**. BTRC never reads BTMM lifecycle state.
   All three attributes it does use live on `BtmmObservation`, which P4 already
   produces and which is already real-data parity-verified on M15, M5 and M1, so
   the P4 projection satisfies P5 completely.

---

## 4. Reviewed evidence does not reach P5

Searching the whole package for `reviewed`, `BtmmReviewedEvidence` and
`EvidenceSource` returns **nothing**.

BTRC consumes neither reviewed-evidence source metadata nor the final BTMM gate
outcome — it consumes only whether a BTMM observation exists for the POI. So the
deferred reviewed-evidence transport is **not** a P5 blocker, and a future
transport would not change any BTRC input. That is worth stating plainly because
the opposite would have coupled two deferred problems together.

---

## 5. Component independence

`ComponentScores` holds eight independent 0-100 rankings, and the final score is
a plain weighted mean:

```python
total_weight = sum(weights.get(k, 0) for k in values)
weighted = sum(values[k] * weights.get(k, 0) for k in values)
return round(weighted / total_weight)
```

No component reads another component's score. Each is computed from upstream
semantic facts and then combined once. The weights are declared in one place:

| component | weight | | component | weight |
|---|---|---|---|---|
| btmm | 3 | | momentum | 1 |
| poi | 3 | | breakout | 1 |
| trend | 2 | | liquidity | 1 |
| regime | 1 | | volatility | 1 |

`t5_configuration.py` labels these **ENGINEERING-PROVISIONAL research baselines —
NOT production-approved, never optimized against historical results**. A Pine port
must carry that label with them; they are not a tuned model.

Bands: `high_confluence_min = 65`, `watch_only_min = 45`.

---

## 6. Supervisory semantics — hard truths never overridden by soft scores

This is the design invariant of the layer and the thing a port is most likely to
break. `BtrcDecision` deliberately separates:

* **hard analytical truths** — `poi_valid`, `btmm_valid`, `global_direction`,
  `regime`, the component states;
* **soft ranking** — `component_scores`, `final_confluence_score`;
* **supervisory classification** — `trend_alignment`, `analytical_permission`,
  `lifecycle_state`.

A soft score never overrides a hard contract. `_permission` shows the precedence
exactly:

* `COUNTER_TREND` alignment → `WATCH_ONLY` below `watch_only_min`, otherwise
  `COUNTER_TREND` ("valid but counter-trend; execution priority low") — a
  counter-trend setup is **technically valid**, and is demoted in priority rather
  than rejected;
* `NEUTRAL` → `ALLOW_BOTH_CONTEXT` at/above the band, else `WATCH_ONLY`;
* `ALIGNED`/`PARTIAL` → `BUY_BIAS`/`SELL_BIAS` at/above `high_confluence_min`,
  `WATCH_ONLY` at/above `watch_only_min`, else `NO_TRADE_CONTEXT`;
* extreme volatility downgrades a bias to `WATCH_ONLY` and **never changes
  direction**.

The decision object also carries no operational fields at all — no entry, stop,
target, size or order id — and the enum module marks the boundary in code:
`ANALYTICAL_LIFECYCLE_STATES` (8) versus `FUTURE_BOT_LIFECYCLE_STATES` (5, all
out of scope).

---

## 7. Identity, persistence, resources

**Identity.** A `BtrcDecision` belongs to **one POI**, evaluated against the whole
`ScannerAnalysis` — `assess_confluence(analysis, poi)`. It is not per setup, per
timeframe or per bar. `poi_record_id` and `poi_timeframe` address it.

**Persistence.** Stateless. Every engine derives its result from the supplied
analysis; nothing carries state between evaluations, and there is no cursor or
registry anywhere in the package. That is a genuine simplification versus P3/P4 —
but it is stateless *given* a full multi-timeframe analysis, which is precisely
what Pine does not have.

**Resources.** The cost is not in BTRC's own 2281 lines; it is in what BTRC
requires to exist first. A faithful Pine port needs P1 + P2 evaluated on **six**
timeframes, where P4 needed one. On top of a P4 DEV that is already 4429 lines
running one timeframe, that is the dominant term by a wide margin, and it is a
resource question that has to be answered before any implementation slice is
authorized.

**Pine portability is already a first-class concept in the source**: the
`PinePortability` enum (`PINE_PORTABLE_EXACT`, `PINE_PORTABLE_WITH_ADAPTATION`,
`PYTHON_ONLY`, `REQUIRES_VALIDATION`) exists precisely to classify this, with the
docstring "Metadata only — does not authorize Pine implementation."

---

## 8. Test inventory

| file | tests |
|---|---|
| `test_btrc_t3_momentum_breakout_pullback.py` | 27 |
| `test_btrc_t4_volatility_session.py` | 20 |
| `test_btrc_trend_engine.py` | 19 |
| `test_btrc_t5_confluence.py` | 17 |
| `test_btrc_regime_engine.py` | 14 |
| `test_btrc_enums_contract_freeze.py` | 5 |

102 tests. Coverage is per-engine and contract-level. There is **no** existing
real-data parity harness, no digest contract, and no atomic probe for BTRC —
those would all be new work.

---

## 9. Blockers

| class | count | items |
|---|---|---|
| **A** explicit + tested | 5 | authority hierarchy and global resolve; component independence; weighted aggregation; permission bands and precedence; the hard/soft separation |
| **B** explicit + under-tested | 2 | `candles_by_timeframe` optionality (T4 degrades silently when absent); `missing_components` semantics when an authority timeframe is absent |
| **C** incidental / ambiguous | 0 | both resolved by the author; see below |
| **D** source/docs conflict | 0 | none found |
| **E** Pine / resource | 2 | six-timeframe P1+P2 substrate; W1/D1/H4 history depth under `calc_bars_count` |
| **F** P6 / later | 1 | cross-timeframe transport itself |

### Author decisions (C) — BOTH RESOLVED

**C-1 — RESOLVED: port the mechanism, keep the numbers provisional.**
The weights and bands are implemented exactly as production has them, but stay
flagged ENGINEERING-PROVISIONAL in the parity contract and the closure document,
and are excluded from any "approved" claim. Parity then proves the mechanism, not
the calibration — which is the honest claim, since the source says these numbers
were never optimized.

**C-2 — RESOLVED: the Pine runtime evaluates the ACTIVE (non-terminal) POIs.**
Roughly 150 on M15 against a ~950-1079 registry. Terminal POIs cannot produce a
live decision, so excluding them narrows nothing real, and the per-bar cost then
scales with the active set rather than with the whole registry. Evaluating every
POI would cost about seven times as much for decisions that cannot change; gating
on the BTMM final stage (~31-83) would have been cheaper still but would silently
deny a decision to every POI that never reaches the gate.

---

#### Original statement of C-1

**C-1 — Are the provisional weights and bands frozen for a Pine port?**
`t5_configuration.py` says the weights and the 65/45 bands are research baselines,
not production-approved. A Pine port would hard-code them into a parity contract
and make them look settled. Either bless them as the P5 contract, or port the
mechanism with the numbers explicitly marked provisional and excluded from any
"approved" claim.

**C-2 — What is the P5 evaluation identity in a Pine runtime?**
`assess_confluence` takes one POI and returns one decision. Python callers choose
which POI. On a chart there is no caller — the port must decide whether it
evaluates every live POI every bar (cost scales with the ~950-POI registry
measured in P4), only setups at a given BTMM stage, or only a single selected POI.
This is a product question, not a source question; the source does not answer it.

---

## 10. Scope, if and when P5 is authorized

**P5 CORE** would be: the six component engines, the weighted aggregation, the
permission/alignment/lifecycle classification, and the `BtrcDecision` projection.

**Prerequisite:** P6 cross-timeframe transport. Not deferrable — `global_direction`
is undefined without it.

**Not P5:** reviewed-evidence transport (P5 does not consume it), P3 CONTEXT (P5
does not consume it), anything operational.

**Suggested slicing**, for a later authorization:

| slice | scope |
|---|---|
| P5-A0 | this audit — **complete** |
| P6-F0 | cross-timeframe transport feasibility; the real gate |
| P5-I1 | T1 trend per timeframe + authority resolve |
| P5-I2 | T2 regime |
| P5-I3 | T3 momentum / breakout / pullback |
| P5-I4 | T4 volatility / session |
| P5-I5 | T5 aggregation, permission, lifecycle |
| P5-I6 | digest contract + synthetic parity |
| P5-I7 | runtime matrix + atomic real-data parity |

A parity contract would follow the P4 shape: per-component hashes so a mismatch
names the engine that owns it, a score hash, a classification hash, and an
overall dual hash — with the same rule that denominators come from the produced
vocabulary rather than `len(Enum)`.

---

## 11. Status

```
P5 ARCHITECTURE AUDIT      COMPLETE — AUTHOR-ACCEPTED
C BLOCKERS                 0  (C-1, C-2 resolved)
D BLOCKERS                 0
P5 IMPLEMENTATION          NOT STARTED — gated on P6
P5_REQUIRES_P6             TRUE  (source-proven)
P5_REQUIRES_P3_CONTEXT     FALSE
P4_TO_P5_CONTRACT_COMPLETE TRUE
REVIEWED_EVIDENCE_TO_P5    NOT CONSUMED
P6                         NOT STARTED / NOT AUTHORIZED
```
