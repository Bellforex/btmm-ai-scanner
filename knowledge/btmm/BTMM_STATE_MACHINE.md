# BTMM Lifecycle and Confirmation State Machine

**BTMM Lifecycle and Confirmation State Machine Version 1 — Provisional.** This is the authoritative, dedicated specification for the approved state machine that resolves Ambiguity 14 in [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md). It is summarized and cross-referenced (not duplicated) from [MEASUREMENT_STANDARDS.md](../MEASUREMENT_STANDARDS.md), "BTMM Lifecycle, Gates, State Transitions, and Confirmation Timing Standard," and from [BTMM_MASTER_SUMMARY.md](BTMM_MASTER_SUMMARY.md).

## Evidence Status

This standard is:

- **AUTHOR-APPROVED**
- **ENGINEERING-PROVISIONAL**
- **NOT YET EMPIRICALLY CALIBRATED**
- **NOT YET OUT-OF-SAMPLE VALIDATED**
- **NOT PRODUCTION-APPROVED**

Do not present the numerical thresholds or gate structure as a proven profitable trading system. It must later be tested with expert-approved BTMM examples, expert-rejected BTMM examples, across XAUUSD, EURUSD, GBPUSD, on M1, M5, M15, different sessions, different volatility regimes, liquidity before/within/after POIs, and different POI families, before it can be considered final or production-approved.

## Purpose and Scope

This standard gives a BTMM setup discrete, auditable, non-repainting lifecycle states so a scanner can raise and clear a signal in a reproducible way. It formalizes *when* a BTMM setup may be considered `BTMM_CONFIRMED`, `BTMM_BLOCKED`, or `BTMM_CANCELLED` — it does **not** define entry rules, risk management, POI invalidation, freshness, mitigation, expiration, or any of the Ambiguity 15 terminology. See "Required Conceptual Separation" below.

## Required Conceptual Separation

The following remain independent concepts. A BTMM setup's lifecycle state never collapses them into one another:

- POI validity
- BTMM setup validity
- Liquidity evidence
- BTMM pillar evidence (Volume / Speed / Accuracy)
- Entry validity
- Risk approval
- Trade outcome

`BTMM_CONFIRMED` must **not** automatically mean:

- Enter a trade.
- Use a particular lot size.
- The POI cannot fail.
- The trade will be profitable.

## Setup Identity

Each BTMM setup belongs to exactly:

- One POI
- One POI interaction event
- One BTMM direction
- One formation timeframe
- One symbol
- One data provider

A `btmm_setup_id` is created and preserved for each setup. A later eligible interaction with the same POI creates a **new** setup record — an older cancelled setup is never overwritten or reactivated. Repeated-touch degradation (whether repeated interactions weaken or strengthen a POI over time) remains unresolved.

## BTMM Direction

| POI direction | BTMM direction |
|---|---|
| Bullish POI | `BULLISH_BTMM` |
| Bearish POI | `BEARISH_BTMM` |

Direction comes from the selected POI and an approved analytical-context input. This standard does not invent HH, HL, LH, LL, BOS, or CHoCH rules to derive direction.

## Primary Lifecycle States

Exactly five primary states are used:

| State | Meaning |
|---|---|
| `BTMM_CANDIDATE` | A validated POI interaction event exists and is eligible to begin BTMM evaluation. |
| `BTMM_FORMING` | Evaluation is underway; gates are being checked as evidence becomes available. |
| `BTMM_BLOCKED` | Mandatory information is unavailable, but no market-based cancellation condition has occurred. |
| `BTMM_CONFIRMED` | Every mandatory gate has passed. |
| `BTMM_CANCELLED` | A market-based or context-based condition has terminally rejected the setup. |

The primary lifecycle state is kept separate from the detailed formation stage (below) — e.g. `primary_state = BTMM_FORMING` with `formation_stage = POI_INTERACTION` are two independent fields, never merged into one opaque value.

## Formation Stages

While `primary_state = BTMM_FORMING`, exactly one of six formation stages is preserved:

1. `CONTEXT_CHECK`
2. `LIQUIDITY_MONITORING`
3. `APPROACH_MONITORING`
4. `POI_INTERACTION`
5. `REACTION_MONITORING`
6. `FINAL_GATE_EVALUATION`

## BTMM Candidate Creation

A `BTMM_CANDIDATE` is created only when all of the following hold:

- A POI has been identified.
- POI direction is known.
- The POI record is available without look-ahead bias (i.e., only from its own confirmation time, per each POI's own non-repainting rule).
- The POI has not been rejected by its own formation standard.
- Symbol, provider, timeframe, and price metadata are valid.

The POI's own evidence status (e.g. Author-Approved/Engineering-Provisional) is preserved alongside the setup. The POI does not need to be production-approved during this knowledge phase, but its provisional status must remain visible on the setup record.

## Context Gate

Preserved fields: `market_direction_status`, `analytical_framework_status`, `session_status`.

| Field | Allowed values |
|---|---|
| `market_direction_status` | `PENDING`, `ALIGNED`, `MISALIGNED`, `UNKNOWN` |
| `analytical_framework_status` | `PENDING`, `ALIGNED`, `MISALIGNED`, `UNKNOWN` |
| `session_status` | `PENDING`, `ACTIVE`, `INACTIVE`, `UNKNOWN` |

Progress beyond `CONTEXT_CHECK` requires all three: `market_direction_status = ALIGNED`, `analytical_framework_status = ALIGNED`, `session_status = ACTIVE`.

Until automatic context rules are approved, these inputs may come from expert labels, approved external context modules, or explicit manual review. This standard does not invent moving-average, HH/HL, BOS, CHoCH, or other market-direction rules, and does not invent automatic session schedules.

### Context Cancellation

| Condition | Result |
|---|---|
| `market_direction_status = MISALIGNED` | `BTMM_CANCELLED`, `cancellation_reason = CONTEXT_REJECTED` |
| `analytical_framework_status = MISALIGNED` | `BTMM_CANCELLED`, `cancellation_reason = CONTEXT_REJECTED` |
| `session_status = INACTIVE` | `BTMM_CANCELLED`, `cancellation_reason = SESSION_INACTIVE` |

This cancels the current BTMM setup only — it must not invalidate the underlying POI.

## Liquidity Gate

Preserved liquidity locations: `LIQUIDITY_BEFORE_POI`, `LIQUIDITY_WITHIN_POI`, `LIQUIDITY_AFTER_POI`, `MULTIPLE_LOCATIONS`, `NONE_OBSERVED`, `NOT_YET_EVALUATED`.

Preserved evidence source: `EXPERT_LABELLED`, `RULE_BASED`, `MODEL_PROPOSED`, `HYBRID_REVIEWED`, `RULE_BASED_REVIEWED`.

At least one **reviewed** liquidity-evidence event is mandatory for final BTMM confirmation. Only reviewed evidence may satisfy the final liquidity gate — a `MODEL_PROPOSED` event that has not been reviewed must not independently pass the gate.

**Compatibility note (Ambiguity 15 integration):** `RULE_BASED_REVIEWED` is the reviewed form of the pre-existing `RULE_BASED` source, introduced by the POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional (Ambiguity 15). The pre-existing `RULE_BASED` and `MODEL_PROPOSED` values are unchanged and not deleted or replaced — an unreviewed event under either value still cannot satisfy the gate on its own.

**Liquidity-after-POI integration (Ambiguity 15):** a confirmed `FALSE_INVALIDATION_CONFIRMED` event (see [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md)) may be recorded as `liquidity_location = LIQUIDITY_AFTER_POI` with `liquidity_event_type = FALSE_INVALIDATION_CONFIRMED`. It may satisfy this Liquidity Gate only when its evidence source is reviewed — `EXPERT_LABELLED`, `RULE_BASED_REVIEWED`, or `HYBRID_REVIEWED`; an unreviewed `MODEL_PROPOSED` event still cannot satisfy the gate alone. A False Invalidation event does not automatically satisfy the Volume Pillar Gate, Reaction Gate, Reaction Speed Gate, or Formation Timeframe Gate, and does not itself establish entry validity or risk approval.

Liquidity evidence may appear before POI interaction, during POI dwell, during controlled movement around or beyond the POI, or before completion of the five-bar reaction window. At `FINAL_GATE_EVALUATION`, the gate requires `liquidity_evidence_status = PRESENT`. If the full reaction window closes with no reviewed evidence present, use `BTMM_CANCELLED`, `cancellation_reason = NO_LIQUIDITY_EVIDENCE`. A later market event creates a new `btmm_setup_id`; the cancelled setup is never rewritten.

Exact automatic detection of general liquidity terminology and events beyond the reviewed False Invalidation pathway above remains dependent on further author decisions outside this standard. This standard's own gates, states, and transitions are unchanged by the POI Boundary Breach, Reclaim and Invalidation Standard.

## Delay Inside the POI

When price remains inside the POI without immediate reaction, the setup retains `primary_state = BTMM_FORMING`, `formation_stage = REACTION_MONITORING`. Preserved fields: `poi_dwell_bars`, `first_touch_time`, `reaction_start_time`. A setup must not be cancelled solely because of dwell or delay — no maximum dwell time is defined.

## Accuracy Gate

Uses the approved POI Zone Interaction Standard (Ambiguity 8).

| Interaction class | Accuracy Gate |
|---|---|
| `EDGE_TOUCH`, `PARTIAL_ENTRY`, `DEEP_ENTRY`, `FAR_BOUNDARY_TOUCH`, `CONTROLLED_OVERSHOOT` | PASS |
| `NO_CONTACT`, `NEAR_MISS`, `NONCANONICAL_SIDE_INTERACTION`, `EXCESSIVE_OVERSHOOT` | FAIL |

Failure produces `BTMM_CANCELLED`, `cancellation_reason = INTERACTION_INELIGIBLE`. This must not automatically invalidate the POI.

## Volume Pillar Gate

Preserved field: `volume_pillar_status`, values `PENDING`, `SUPPORTS`, `FAILS`, `MISSING_DATA`, `UNRESOLVED`.

Primary evidence must come from the approved price/candle-behaviour measurements (Volume and Momentum Proxy Standard, Ambiguity 3). Tick volume is secondary contextual evidence only and alone must not satisfy the gate.

BTMM confirmation requires `volume_pillar_status = SUPPORTS`. Until the final `price_activity_score` formula is approved, the gate may use POI-specific approved candle rules, expert-labelled volume-switch evidence, or reviewed hybrid evidence. This standard does not invent a composite price-activity score.

| Condition | Result |
|---|---|
| Volume pillar definitively fails | `BTMM_CANCELLED`, `cancellation_reason = VOLUME_PILLAR_FAILED` |
| Evidence unavailable or still awaiting review | `BTMM_BLOCKED` (never silently passed or cancelled) |

## Approach-Speed Evidence

Preserved separately: `approach_speed_classification`, `approach_normalized_speed_per_bar`, `approach_directional_efficiency`, `approach_directional_candle_share` (per the approved Market Speed and Displacement Standard, Ambiguity 7).

Approach speed is supporting evidence only — a slow approach must not automatically cancel the setup. Approach speed and reaction speed remain separate fields, never merged.

## Reaction Gate

Uses the approved POI Reaction Strength Standard (Ambiguity 9).

| Reaction classification | Reaction Gate |
|---|---|
| `STANDARD_REACTION`, `STRONG_REACTION` | PASS |
| `WEAK_REACTION` (completed five-bar window) | `BTMM_CANCELLED`, `cancellation_reason = WEAK_REACTION` |

This cancellation must not invalidate the POI.

## Reaction-Speed Gate

Uses the approved Market Speed and Displacement Standard (Ambiguity 7).

| Reaction speed classification | Reaction Speed Gate |
|---|---|
| `FAST`, `STRONG_FAST` | PASS |
| `SLOW_OR_UNCLEAR` (completed reaction window) | `BTMM_CANCELLED`, `cancellation_reason = REACTION_SPEED_FAILED` |

This mandatory speed gate is engineering-provisional and must later be calibrated.

## Formation Timeframe Gate

BTMM observation may occur on M1, M5, or M15. For Version 1, final confirmation requires an approved formation confirmation on **M5 or M15**. M1 may provide precision evidence, execution refinement, or additional supporting confirmation, but an M1-only setup must remain `BTMM_FORMING` or `BTMM_BLOCKED` — it must not independently become `BTMM_CONFIRMED`.

## Final BTMM Confirmation Gate

A setup becomes `BTMM_CONFIRMED` only when **every** mandatory gate passes:

1. POI Gate = PASS
2. Market Direction Gate = PASS
3. Analytical Framework Gate = PASS
4. Active Session Gate = PASS
5. Liquidity Gate = PASS
6. Accuracy Gate = PASS
7. Volume Pillar Gate = PASS
8. Reaction Gate = PASS
9. Reaction Speed Gate = PASS
10. Formation Timeframe Gate = PASS

No weighting, majority vote, average score, or composite confirmation score is used. One failed mandatory gate prevents confirmation.

## Confirmation Timing (Non-Repainting)

`BTMM_CONFIRMED` becomes available only after: the complete five-bar POI reaction window has closed, all mandatory gate inputs are available, and `FINAL_GATE_EVALUATION` passes. `btmm_confirmation_time` is stored.

`BTMM_CONFIRMED` must **not** be exposed historically at POI creation time, manipulation time, first POI touch, or reaction-start time. This is required to prevent look-ahead bias.

## Blocked State

`BTMM_BLOCKED` is used when mandatory information is unavailable but no market-based cancellation condition has occurred. Allowed blocked-reason examples: `MISSING_ATR`, `MISSING_PRICE_METADATA`, `CONTEXT_UNKNOWN`, `LIQUIDITY_REVIEW_PENDING`, `VOLUME_REVIEW_PENDING`, `FORMATION_TIMEFRAME_NOT_CONFIRMED`. The blocked reason is preserved separately (`blocked_reason`). A blocked setup may return to `BTMM_FORMING` when the missing evidence becomes available. `BTMM_BLOCKED` must never be represented as confirmed or cancelled.

## Cancellation Reasons

One primary terminal state, `BTMM_CANCELLED`, is used; the reason is preserved separately (`cancellation_reason`) rather than creating a separate opaque terminal state per reason:

- `POI_REJECTED`
- `CONTEXT_REJECTED`
- `SESSION_INACTIVE`
- `INTERACTION_INELIGIBLE`
- `DIRECTIONAL_CONTINUATION`
- `WEAK_REACTION`
- `REACTION_SPEED_FAILED`
- `VOLUME_PILLAR_FAILED`
- `NO_LIQUIDITY_EVIDENCE`
- `MANUAL_REVIEW_REJECTED`

**POI-invalidation trigger (Ambiguity 15 integration):** the pre-existing `POI_REJECTED` cancellation reason above is also used when a `GENUINE_INVALIDATION_CONFIRMED` event (see [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md)) sets `poi_lifecycle_status = INVALIDATED` on the linked POI. Any active BTMM setup connected to that POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED`. This does not add a new cancellation reason, does not rewrite historical BTMM records or earlier valid interactions, does not change an existing trade outcome, and does not invalidate a different POI. A later reaction from the same general price area requires a new POI record and, where applicable, a new BTMM setup record — an invalidated POI is never reactivated.

## Allowed and Forbidden Transitions

**Allowed:**

```
BTMM_CANDIDATE → BTMM_FORMING → BTMM_CONFIRMED
BTMM_CANDIDATE → BTMM_CANCELLED
BTMM_FORMING → BTMM_BLOCKED → BTMM_FORMING
BTMM_FORMING → BTMM_CANCELLED
```

**Forbidden:**

```
BTMM_CANCELLED → BTMM_CONFIRMED
BTMM_CONFIRMED → BTMM_CANCELLED
```

A new market cycle or later eligible interaction requires a new `btmm_setup_id` — it never reuses or reactivates an existing one.

## Non-Repainting and No-Retroactive-Rewriting Rules

Once confirmed:

- `btmm_setup_id` must not change.
- `poi_id` must not change.
- `poi_interaction_id` must not change.
- Direction must not change.
- Confirmation time must not move.
- Evidence used at confirmation must remain auditable.
- A later losing trade must not change `BTMM_CONFIRMED` to cancelled.
- A later profitable trade must not upgrade an unconfirmed setup.

Once cancelled:

- Cancellation time must not move.
- Cancellation reason must not be silently replaced.
- A later event must create a new setup.

## Entry/Risk Separation

After `BTMM_CONFIRMED`, a separate execution and risk module may later evaluate `entry_validity`, `stop_loss`, `take_profit`, `risk_to_reward`, `lot_size`, `account_risk`, news restrictions, spread, and slippage. None of those rules are defined by this decision, and `BTMM_CONFIRMED` must not be presented as an automatic trade instruction.

## Required Fields

Preserved independently (no composite score):

`btmm_setup_id`, `poi_id`, `poi_interaction_id`, `btmm_direction`, `primary_state`, `formation_stage`, `state_entered_time`, `previous_state`, `poi_gate_status`, `market_direction_status`, `analytical_framework_status`, `session_status`, `liquidity_evidence_status`, `liquidity_location`, `liquidity_evidence_source`, `volume_pillar_status`, `approach_speed_classification`, `approach_normalized_speed_per_bar`, `approach_directional_efficiency`, `approach_directional_candle_share`, `accuracy_gate_status`, `reaction_classification`, `reaction_speed_classification`, `formation_timeframe`, `execution_timeframe`, `poi_dwell_bars`, `first_touch_time`, `reaction_start_time`, `btmm_confirmation_time`, `cancellation_time`, `cancellation_reason`, `blocked_reason`, `evidence_version`, `symbol`, `data_provider`, `created_at`, `updated_at`.

A complete append-only state-transition history is preserved for every setup. No composite BTMM score is created.

## Ambiguity 15 Dependency

This standard references `liquidity_evidence_status`, `liquidity_location`, and `liquidity_evidence_source` as evidence fields. Reclaim, displacement after reclaim, repeated taps, false invalidation, and genuine invalidation are now defined provisionally by the **POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional** (resolves Ambiguity 15; see [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md)) — a separate shared standard for bounded directional POIs. This BTMM state machine does not itself define or duplicate those terms; it only integrates two of their outcomes (a reviewed False Invalidation event as `LIQUIDITY_AFTER_POI` evidence, and a Genuine Invalidation event triggering `BTMM_CANCELLED`/`POI_REJECTED` on the linked setup), as documented in "Liquidity Gate" and "Cancellation Reasons" above. No BTMM primary state, formation stage, mandatory gate, transition, or cancellation-reason taxonomy was changed by that integration.

## Calibration Requirements

All states, gates, transitions, and thresholds above must later be tested against expert-approved BTMM examples, expert-rejected BTMM examples, across XAUUSD, EURUSD, GBPUSD, on M1, M5, M15, different sessions, different volatility regimes, liquidity before/within/after POIs, and different POI families. The states, gates, transitions, and cancellation rules are not to be changed casually outside that calibration process.

## What Remains Unresolved

This standard fixes lifecycle states, formation stages, mandatory gates, blocked/cancellation behavior, confirmation timing, and allowed/forbidden transitions only. It explicitly does **not** define:

- Reclaim, displacement after reclaim, repeated taps, false invalidation, or genuine invalidation (now resolved separately under Ambiguity 15 — see [POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md](../poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md) — this standard only integrates two of their outcomes as described above).
- Automatic market-direction logic (HH, HL, LH, LL, BOS, CHoCH, moving averages, or any other invented structure rule).
- Automatic analytical-framework context detection.
- Automatic session schedules.
- Maximum POI dwell time.
- Entry confirmation, stop loss, take profit, risk-to-reward, lot sizing, or news restrictions.
- Final POI invalidation, freshness, mitigation, or expiration.
- Repeated-touch degradation.
- Empirical calibration or out-of-sample validation.
- Production approval.

These remain separate, pending decisions.
