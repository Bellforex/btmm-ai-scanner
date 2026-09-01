# BTRC-V1 P4 — BTMM Setup Engine: Pine Architecture

Status: **P4-I0 (contract audit) COMPLETE — implementation authorized**
Branch: `pine-p4-btmm`
Predecessor: [P3 POI CORE closure](BTRC_V1_P3_POI_CORE_CLOSURE.md)

Every claim below was measured against the production Python source or pinned by
a test committed on this branch. Where a claim is enforced by a test, the test is
named. Nothing here is inferred from naming.

---

## 1. The two-layer architecture (author decision D-1)

`analyze_btmm` takes four inputs, and the fourth — `reviewed_evidence` — is one
the scanner never computes. It is supplied by the caller, and
`BtmmReviewedEvidence` validates that its sources are human-reviewed. Both
`BTMM_CONFIRMED` assignments (`lifecycle.py:503`, `lifecycle.py:592`) sit
downstream of `_resolve_final_gates`, whose signature takes a **non-optional**
evidence record. A run with no evidence therefore takes the branch at
`lifecycle.py:407-414` and cancels:

```
primary_state      = BTMM_CANCELLED
cancellation_reason = NO_LIQUIDITY_EVIDENCE
formation_stage     = FINAL_GATE_EVALUATION
```

That is not a gap to be closed. It is the contract, and P4 ports it as two
layers:

| | Layer A — the engine | Layer B — the runtime adapter |
|---|---|---|
| What it is | the complete BTMM state machine | the TradingView indicator |
| Evidence input | fixtures supplied to the oracle | `reviewed_evidence = ()` |
| Reaches `BTMM_CONFIRMED` | yes | **no, by construction** |
| Proven against | `analyze_btmm(..., evidence)` | `analyze_btmm(..., ())` |
| Coverage metric | `ENGINE_REACHABLE_COVERAGE` | `NO_EVIDENCE_RUNTIME_REACHABLE_COVERAGE` |

Layer A implements all 5 statuses, all 15 transition types, and every gate.
Layer B supplies no evidence because TradingView has no authorized transport for
human review. A Layer B run that never confirms is **correct behaviour**, and the
two coverage figures are reported separately and never summed.

The measured matrix, from `test_btmm_reviewed_evidence_contract.py`:

| Timeframe | `reviewed_evidence = ()` | full aligned evidence |
|---|---|---|
| M15 | `BTMM_CANCELLED` / `NO_LIQUIDITY_EVIDENCE` | **`BTMM_CONFIRMED`** |
| M5 | `BTMM_CANCELLED` / `NO_LIQUIDITY_EVIDENCE` | **`BTMM_CONFIRMED`** |
| M1 | `BTMM_CANCELLED` / `NO_LIQUIDITY_EVIDENCE` | `BTMM_BLOCKED` / `FORMATION_TIMEFRAME_NOT_CONFIRMED` |

all at stage `FINAL_GATE_EVALUATION`. M1 is supporting-only; the difference is
the formation rule and nothing else.

### 1.1 The integrity seam

Production *does* derive one liquidity fact automatically. A P3
`FALSE_INVALIDATION_CONFIRMED` transition on the source POI yields
`LIQUIDITY_AFTER_POI` with source `RULE_BASED` (`liquidity.py:16-29`). This is
legitimate, Pine-computable, and must be ported.

It cannot substitute for review, and the reason is structural rather than
conventional:

* automatic evidence writes `liquidity_location` and `liquidity_evidence_source`
  **only** (`lifecycle.py:391-401`);
* the gate reads `liquidity_evidence_status` (`lifecycle.py:153`), which is
  assigned from reviewed evidence alone (`lifecycle.py:455-456`, `544-545`);
* `RULE_BASED` is absent from `CONTEXT_AND_LIQUIDITY_ALLOWED_SOURCES`, so it can
  never arrive *as* review either.

So a derived sweep describes **where** liquidity was taken; it can never assert
**that** liquidity evidence was reviewed. When review does arrive, its source
supersedes `RULE_BASED`, so no confirmed record ever claims to rest on a
machine-derived sweep.

This seam is held open end-to-end and whole-record by
`test_automatic_liquidity_describes_location_but_never_confirms` and
`test_derived_liquidity_does_not_change_the_no_evidence_outcome`. It is exactly
the seam a well-meaning "make the scanner confirm something" change would close,
which is why it is pinned rather than documented.

---

## 2. Upstream dependency matrix

Measured by import and attribute-access scan across `src/btmm_ai_scanner/btmm/`.

| Upstream | What P4 consumes | Verdict |
|---|---|---|
| **P1 measurements** | `MarketMeasurementAnalysis.symbol`, `.timeframe`, `.analyzed_candle_count` | **metadata only** |
| P1 detectors | swings, displacements, equal levels, S/R zones, trendlines | **not read at all** |
| P1 functions | `measurements.atr` (ATR series), `measurements.legs.measure_leg` | computed in-place from candles |
| **P2 structure** | — | **zero imports** |
| **P3 POI** | `poi_observations`, `poi_lifecycle_transitions` | **primary input** |
| Candles | `NormalizedCandle` OHLC + times | primary input |

Two consequences for the port:

1. **P4 does not depend on the P1 detector outputs or on P2 at all.** The
   reference-zone frontier that dominated P3 is not in P4's path. The Pine port
   needs P3's POI observations and lifecycle transitions, raw candles, and ATR.
2. `LegSpeedClassification` enters `CurrentBtmmState` from `measurements.legs`,
   so leg speed must be ported as a function, not as a P1 record lookup.

### 2.1 Timeframe partition (already proven and pinned)

`analyze_btmm` takes `tuple[BtmmTimeframeInput, ...]`, which reads like a
multi-timeframe algorithm. It is not: each setup observes only its own POI's
`source_timeframe`, and the tuple is a batch container. A combined call equals
the union of independent single-bundle calls, whole-record, across 6 seeds —
`test_btmm_timeframe_partition.py` (12 tests, commit `c296b9f`).

**This is what allows a single-chart Pine port with no `request.security` and no
cross-timeframe transport.** An earlier audit of mine concluded the opposite;
the invariant is now a permanent test so the question cannot be reopened by
reading a signature.

---

## 3. Setup admission and identity

```
for source_poi in poi_analysis.poi_observations:
    if source_poi.poi_type not in configuration.eligible_poi_types:   continue
    if source_poi.source_timeframe not in (formation | supporting_only): continue
    -> exactly one BTMM setup
```

* `eligible_poi_types` defaults to `LIFECYCLE_ELIGIBLE_POI_TYPES` — **all 18**
  P3 CORE types.
* `formation_timeframes = {M5, M15}`, `supporting_only_timeframes = {M1}`,
  required disjoint by `validate_configuration`.
* Setup `record_id` = content-addressed identity of
  `(symbol, source_timeframe, source_poi.record_id, rule_version)` under
  `DerivedOutputType.BTMM_OBSERVATION`. The POI's `record_id` is the natural key:
  one setup per eligible POI, permanently.
* `candidate_event_time_utc = source_poi.confirmation_time_utc`;
  `availability_time_utc = source_poi.availability_time_utc`. **A setup begins at
  its POI's availability, not at its confirmation** — the same semantic
  availability rule frozen in P3.

---

## 4. Vocabulary: produced, pass-through, reserved

The BTMM enums declare more than the engine assigns. Conflating the two would
inflate every coverage number in the closure report, so the real denominators are
asserted in `test_btmm_vocabulary_reachability.py` (24 tests).

| Enum | Declared | Produced | Reserved (not implemented by production) |
|---|---|---|---|
| `BtmmLifecycleStatus` | 5 | **5** | — |
| `BtmmLifecycleTransitionType` | 15 | **15** | — |
| `BtmmCancellationReason` | 8 | **8** | — |
| `BtmmBlockedReason` | 4 | **4** | — |
| `BtmmGateStatus` | 3 | **3** | — |
| `BtmmDirection` | 2 | **2** | — |
| `BtmmLiquidityEvidenceStatus` | 2 | **2** | — |
| `BtmmInteractionClass` | 9 | **7** | `NO_CONTACT`, `NEAR_MISS` |
| `BtmmFormationStage` | 6 | **3** | `CONTEXT_CHECK`, `LIQUIDITY_MONITORING`, `APPROACH_MONITORING` |
| `BtmmReactionClassification` | 5 | **3** | `AWAITING_REACTION`, `REACTION_IN_PROGRESS` |
| `BtmmLiquidityLocation` | 6 | **1** | the other five |
| `BtmmEvidenceSource` | 5 | **4** | `MODEL_PROPOSED` |
| `BtmmContextAlignmentStatus` | 4 | 3 + pass-through | `UNKNOWN` (pass-through) |
| `BtmmSessionStatus` | 4 | 3 + pass-through | `UNKNOWN` (pass-through) |
| `BtmmVolumePillarStatus` | 5 | 3 + pass-through | `MISSING_DATA`, `UNRESOLVED` (pass-through) |

Notes that change what the port must build:

* **The lifecycle spine is fully live.** All 5 statuses, all 15 transitions, all
  8 cancellation reasons and all 4 blocked reasons are produced. Nothing here may
  be skipped.
* **Only one liquidity location is derivable.** `BtmmReviewedEvidence` has no
  `liquidity_location` field at all, and the automatic path returns exactly
  `LIQUIDITY_AFTER_POI`. The port implements one location, not six.
* **Three of six formation stages exist.** The engine reports from
  `POI_INTERACTION` onward; the three monitoring stages are reserved vocabulary.
* **`MODEL_PROPOSED` can never reach an output record** — not produced
  internally, and rejected by every reviewed-source validator. That is the
  product-integrity guarantee stated as a property of the vocabulary.
* **Pass-through members** (`UNKNOWN`, `MISSING_DATA`, `UNRESOLVED`) are copied
  out of reviewed evidence into `CurrentBtmmState`, all resolving to
  `BTMM_BLOCKED`. They exist in Layer A and are unreachable in Layer B.

---

## 5. Record contracts

| Record | Fields |
|---|---|
| `BtmmObservation` | 15 |
| `BtmmLifecycleTransition` | 16 |
| `CurrentBtmmState` | **33** |
| `BtmmReviewedEvidence` (input) | 15 |
| `BtmmAnalysis` (envelope) | 6 |

`CurrentBtmmState` — the port's output surface — in declaration order:

| # | Field | Group |
|---|---|---|
| 1-5 | `record_id`, `content_fingerprint`, `symbol`, `timeframe`, `btmm_setup_record_id` | identity |
| 6-7 | `btmm_direction`, `source_poi_type` | setup |
| 8-9 | `primary_state`, `formation_stage` | lifecycle |
| 10-12 | `market_direction_status`, `analytical_framework_status`, `session_status` | context (evidence) |
| 13-14 | `accuracy_gate_status`, `interaction_class` | accuracy gate |
| 15-16 | `reaction_gate_status`, `reaction_classification` | reaction gate |
| 17-18 | `reaction_speed_gate_status`, `reaction_speed_classification` | speed gate |
| 19 | `formation_timeframe_gate_status` | formation gate |
| 20 | `volume_pillar_status` | volume (evidence) |
| 21-23 | `liquidity_evidence_status`, `liquidity_location`, `liquidity_evidence_source` | liquidity |
| 24 | `reviewed_evidence_availability_time_utc` | evidence chronology |
| 25-26 | `cancellation_reason`, `blocked_reason` | terminal reason |
| 27-28 | `latest_lifecycle_transition_id`, `availability_time_utc` | chronology |
| 29-33 | `rule_version`, `contract_version`, `schema_version`, `evidence_classification`, `provenance_id` | provenance |

Fields 10-12, 20, 21 and 24 are the evidence surface: in Layer B they hold their
`PENDING` defaults, except where the derived path writes 22-23.

---

## 6. The lifecycle pipeline

Four price stages, then a fixed-cost resolution that touches no candles.

```
stage 1  WAIT_FORMING        candle.availability > candidate_availability
                             -> ENTERED_FORMING
stage 2  WAIT_INTERACTION    find_first_interaction(...)          [zone touch]
                             eligible class   -> ACCURACY_GATE_CONFIRMED
                             ineligible class -> INTERACTION_INELIGIBLE (cancel)
stage 3  WAIT_REACTION_START find_reaction_start(...)             [close beyond entry_boundary]
                             running_anchor accumulates min/max every candle
stage 4  REACTION WINDOW     evaluate_reaction_window(5 bars)
                             WEAK          -> WEAK_REACTION (cancel)
                             STANDARD/STRONG -> REACTION_GATE_CONFIRMED
                                               REACTION_SPEED_GATE_CONFIRMED
                             -> stage = FINAL_GATE_EVALUATION

resolution   (no candle scan)
   automatic liquidity  <- P3 FALSE_INVALIDATION_CONFIRMED   [location/source only]
   reviewed evidence is None -> CANCELLED / NO_LIQUIDITY_EVIDENCE
   else _resolve_final_gates(evidence, is_formation_timeframe):
        liquidity != PRESENT                  -> CANCEL  NO_LIQUIDITY_EVIDENCE
        context MISALIGNED                    -> CANCEL  CONTEXT_REJECTED
        session INACTIVE                      -> CANCEL  SESSION_INACTIVE
        volume FAILS                          -> CANCEL  VOLUME_PILLAR_FAILED
        formation TF and fully aligned        -> CONFIRM
        not formation TF                      -> BLOCK   FORMATION_TIMEFRAME_NOT_CONFIRMED
        context not all ALIGNED/ACTIVE        -> BLOCK   CONTEXT_UNKNOWN
        otherwise                             -> BLOCK   VOLUME_REVIEW_PENDING
   source POI GENUINE_INVALIDATION_CONFIRMED  -> truncates the walk unconditionally
```

Gate precedence is strict and order-sensitive: liquidity, then context, then
session, then volume. A setup failing two gates reports the first.

### 6.1 Thresholds (all from `BtmmConfiguration`, all defaulted)

Interaction tolerance is `max(2 x tick, min(atr_mult x ATR, height_mult x zone_height))`.

| Parameter | Default |
|---|---|
| contact tolerance ATR / zone-height multiplier | 0.05 / 0.10 |
| overshoot tolerance ATR / zone-height multiplier | 0.10 / 0.25 |
| edge-touch max penetration ratio | 0.25 |
| partial-entry max penetration ratio | 0.50 |
| reaction window bars | 5 |
| standard: ATR ratio / clearance / efficiency / candle share | 0.75 / 1.00 / 0.50 / 0.60 |
| strong: ATR ratio / clearance / efficiency / candle share | 1.25 / 1.50 / 0.60 / 0.67 |
| fast speed / efficiency / candle share | 0.50 / 0.60 / 0.67 |
| strong-fast speed / efficiency / candle share | 0.75 / 0.75 / 0.80 |

`STRONG_REACTION` additionally requires leg classification in `{FAST, STRONG_FAST}`.
The reaction tier is evaluated over **every** prefix `k = 1..5` of the window and
takes the highest tier reached; the speed leg is measured to the bar of maximum
favourable excursion, not to the window close.

---

## 7. Ordering and chronology — two traps

**Public ordering.** Outputs are sorted after the walk:

* observations — `(availability_time, source_timeframe, btmm_direction, source_poi_record_id, record_id)`
* transitions — `(availability_time, event_time, transition_type.value, btmm_setup_record_id, record_id)`
* current states — `(symbol, timeframe, btmm_setup_record_id)`

Because `transition_type.value` is a **string** sort key, same-bar transitions are
ordered alphabetically, not by emission. Confirmation shares its bar with both
reaction gates and comes out as `CONFIRMED`, `REACTION_GATE_CONFIRMED`,
`REACTION_SPEED_GATE_CONFIRMED`. Pinned by
`test_transitions_are_ordered_by_time_then_type_not_by_emission`.

**`latest_lifecycle_transition_id` is NOT computed from that order.**
`analyze_btmm` reduces "last write wins" over the **pre-sort, natural
walk-emission** order (`analyzer.py:1020-1032`); the canonical sort happens
strictly afterwards. A port that sorts first and then takes the last element will
disagree on any bar carrying more than one transition. This is the single
highest-risk detail in the P4 port.

---

## 8. Persistence: the port target is the cursor, not the batch

`run_btmm_lifecycle` re-runs the whole cascade over `candles[0:]` on every
candle. Pine cannot, and does not need to: production already contains an exact
resumable cursor, `btmm/lifecycle_cursor.py` (A6-B2-A), which reproduces the
batch result one appended candle at a time without ever re-scanning history.

`BtmmLifecycleCursor` is a 26-field frozen record: 12 immutable setup fields, the
running candle count and previous candle, plus
a committed price-stage frontier (`entered_forming_index`, `interaction_index`,
`interaction_class`, `running_anchor`, `reaction_start_index`, `reaction_anchor`,
the bounded window buffer, `tier_result`, `window_close_candle`). Retained candle
state is the previous candle plus at most 5 window candles.

This is the Pine algorithm, already written and already proven:

* every-prefix differential equality against the batch oracle
  (`test_a6b2a_btmm_cursor.py`, 16 tests) across confirmed, weak-reaction,
  no-evidence, late-evidence, context-rejected, non-formation-blocked,
  automatic-evidence, invalidation-before-and-after-confirmation, ineligible
  interaction, bearish, and randomized streams;
* an event-driven scheduler and O(1) fast-forward for dormant cursors
  (`test_a6b2b_btmm_scheduler.py`, 24 tests).

**Look-ahead is bounded by the reaction window (5 bars).** Unlike P3, whose
committed boundary spans a 7-bar breach/reclaim/displacement cascade, P4's only
unbounded-looking stage is `WAIT_REACTION_START`, and that accumulates rather
than looks ahead. So the Pine commitment delay for a setup is at most
`reaction_window_bars` after reaction start, and the resolution stage is
fixed-cost.

Two stages are **not** skippable and must see every candle:
`WAIT_REACTION_START` (the anchor accumulates `min`/`max` every candle) and the
reaction-window buffer. The other two are proven no-ops on non-triggering
candles.

---

## 9. Coverage definitions for the closure report

Both figures are reported separately and are never combined.

* **`ENGINE_REACHABLE_COVERAGE`** — over the *produced* vocabulary of section 4,
  exercised with evidence fixtures supplied to the oracle. Denominators come from
  `test_produced_counts_are_what_the_port_owes`, not from `len(Enum)`.
* **`NO_EVIDENCE_RUNTIME_REACHABLE_COVERAGE`** — over the subset reachable with
  `reviewed_evidence = ()`. `BTMM_CONFIRMED`, the four evidence-driven
  cancellations, all four blocked reasons and every pass-through member are
  **expected to be absent**, and their absence is a pass, not a shortfall.

Reserved members are excluded from both denominators and named explicitly in the
report.

---

## 10. Implementation plan

| Phase | Scope |
|---|---|
| P4-I0 | contract audit + evidence/vocabulary tests — **complete** (`1ff1796`, `abd47fd`, `c296b9f`) |
| P4-I1 | Pine setup admission, identity, `BtmmObservation` emission |
| P4-I2 | interaction classification (7 produced classes) + accuracy gate |
| P4-I3 | reaction start, anchor accumulation, 5-bar window, tiering |
| P4-I4 | leg speed (`measure_leg` port) + speed gate |
| P4-I5 | derived liquidity from P3 `FALSE_INVALIDATION_CONFIRMED` |
| P4-I6 | evidence channel + `_resolve_final_gates` (Layer A) |
| P4-I7 | `reviewed_evidence = ()` runtime adapter (Layer B) |
| P4-I8 | transition emission, emission-order `latest_lifecycle_transition_id`, canonical sort |
| P4-I9 | persistent cursor + committed frontier |
| P4-I10 | `CurrentBtmmState` 33-field digest + dual-hash parity contract |
| P4-I11 | directed / prefix / randomized parity, both modes |

Then: persistence proof, performance, 72/72 runtime matrix, M15+M5+M1
atomic real-data no-evidence parity, closure.

---

## 11. Out of scope / prohibited

Unchanged from the standing constraints, restated because they bear on this
phase specifically:

* no `strategy.*`, no orders, entries, sizing, stops, targets or trade management;
* no `request.security` / `request.security_lower_tf` — section 2.1 removes the
  only reason one might be wanted;
* no modification of production Python semantics, or of P1 / P2 / P3 semantics;
* no push, no merge to `main`, no publication or invite-only release;
* **no automatic satisfaction of a human-reviewed gate** — no converting market
  data into `EXPERT_LABELLED`, no hard-coded `HYBRID_REVIEWED`, no treating Pine
  calculation as reviewed evidence, no defaulting gate statuses to `PASS`, and no
  confirming when evidence is absent. Section 1.1 is the structural guarantee;
  the tests named there are its enforcement.
