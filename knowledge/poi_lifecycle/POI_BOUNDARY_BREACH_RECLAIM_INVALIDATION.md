# POI Boundary Breach, Reclaim and Invalidation Standard

**POI Boundary Breach, Reclaim and Invalidation Standard Version 1 — Provisional.** This is the authoritative, dedicated specification for the approved standard that resolves Ambiguity 15 in [AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md](../AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md). It is summarized and cross-referenced (not duplicated) from [MEASUREMENT_STANDARDS.md](../MEASUREMENT_STANDARDS.md), "POI Boundary Breach, Reclaim, Repeated Tap, and Invalidation Standard."

## Provenance Labels

Every citation of this standard must carry all three provenance labels:

1. **BOOK-SUPPORTED UNDERLYING CONCEPT** — the private BTMM/POI source material supports the underlying market concepts this standard formalizes: fake mitigation, stop hunting, delayed reactions, false breakouts, confusing price movement around POIs, and liquidity creation before, within, or after a POI.
2. **AUTHOR-ADDED PROJECT TERMINOLOGY** — the exact project terms (`RECLAIM_CONFIRMED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED`, `REPEATED_TAP`, etc.), windows, and numerical thresholds below are engineering definitions added by the author. They are not direct quotations from the book.
3. **ENGINEERING-PROVISIONAL OPERATIONAL DEFINITION** — these are working definitions that require empirical calibration and out-of-sample validation before production use.

## Evidence Status

This standard is:

- **AUTHOR-APPROVED**
- **AUTHOR-ADDED PROJECT TERMINOLOGY**
- **ENGINEERING-PROVISIONAL**
- **NOT YET EMPIRICALLY CALIBRATED**
- **NOT YET OUT-OF-SAMPLE VALIDATED**
- **NOT PRODUCTION-APPROVED**

Do not present these terms, windows, or formulas as direct quotations from the book, or as universal trading laws. It must later be tested against expert-approved examples, expert-rejected examples, across XAUUSD, EURUSD, GBPUSD, relevant timeframes, different sessions, different volatility regimes, and different POI families before it can be considered final or production-approved.

## Purpose and Scope

This standard gives bounded directional POIs a discrete, auditable, non-repainting lifecycle for boundary breach, reclaim, false invalidation, genuine invalidation, and repeated-tap tracking — concepts the book gestures at narratively (fake mitigation, stop hunts, delayed reactions, false breakouts) but never formalizes into project terminology or numeric rules.

## Applicability and Exclusions

This standard applies **only** to bounded directional POIs that have `zone_top`, `zone_bottom`, and `expected_direction`. Applicable examples may include: Bullish and Bearish Order Blocks, Bullish and Bearish Fair Value Gaps, Buy-to-Sell Candle zones, Sell-to-Buy Candle zones, directional Base formations, Support, Resistance, and other bounded bullish or bearish POIs.

This standard does **not** automatically apply to:

- Equal Highs
- Equal Lows
- Bullish Trendline
- Bearish Trendline
- Other unbounded structural references

Equal Highs and Equal Lows remain liquidity structures requiring their own sweep lifecycle (unresolved). Trendlines require line-specific break, reclaim, and invalidation rules (unresolved). The bounded-zone formulas below must not be silently applied to these excluded structures. A dedicated cross-POI applicability audit is required before any individual POI rule file formally inherits this standard — see [KNOWLEDGE_COMPLETION_GATE.md](../KNOWLEDGE_COMPLETION_GATE.md).

## Required Conceptual Separation

The following remain independent concepts, never collapsed into one another:

- POI interaction
- Boundary breach candidate
- Reclaim
- Displacement after reclaim
- False invalidation
- Genuine invalidation
- Repeated taps
- Liquidity evidence
- BTMM confirmation
- Entry validity
- Trade outcome

A reclaim does **not** automatically prove continued POI validity, BTMM confirmation, entry validity, a guaranteed reversal, or a profitable trade.

## Directional Boundaries

| POI direction | Entry Boundary | Far Boundary | Expected Reaction Direction |
|---|---|---|---|
| Bullish | Zone Top | Zone Bottom | Bullish |
| Bearish | Zone Bottom | Zone Top | Bearish |

Requires `Zone Top > Zone Bottom`. Invalid, zero-height, missing-boundary, or directionless zone geometry is rejected.

## Reused Tolerance Formulas

No separate generic tolerance formula is created. This standard reuses the approved POI Zone Interaction Standard (Ambiguity 8):

```
Zone Height = Zone Top − Zone Bottom
Contact Tolerance = MAX(2 × Minimum Price Tick, MIN(0.05 × ATR(14), 0.10 × Zone Height))
Overshoot Tolerance = MAX(2 × Minimum Price Tick, MIN(0.10 × ATR(14), 0.25 × Zone Height))
```

ATR, symbol, data provider, timeframe, and instrument metadata must match the evaluated POI interaction. Where this standard requires candle-specific evaluation (see "Sustained Breach Requirement" below), tolerance must be calculated using that evaluated candle's own ATR(14) — one stale ATR value must not be reused across multiple candles. Guarded against: missing ATR, zero ATR, missing/invalid Minimum Price Tick, missing zone boundaries, `Zone Top ≤ Zone Bottom`, and mismatched symbol/provider/timeframe. No fixed pip or point values are substituted.

## Wick Overshoot

A wick beyond the Far Boundary is stored separately and may retain the approved interaction classifications `CONTROLLED_OVERSHOOT` / `EXCESSIVE_OVERSHOOT`. A wick alone must **not** confirm `GENUINE_INVALIDATION_CONFIRMED`. Only confirmed candle closes may begin the close-breach lifecycle.

## Close Breach Candidate

| POI direction | Condition |
|---|---|
| Bullish | `Zone Bottom − Candle Close > Overshoot Tolerance` |
| Bearish | `Candle Close − Zone Top > Overshoot Tolerance` |

A confirmed candle meeting its condition creates `CLOSE_BREACH_CANDIDATE`. This is **not** Genuine Invalidation. It starts one invalidation-evaluation event identified by a preserved `boundary_breach_event_id`.

## Three-Bar Reclaim Window

Exactly the next 3 confirmed candles after the Close Breach Candidate are evaluated. The breach candle itself is not reclaim-window bar 1 — the first confirmed candle *after* the breach is reclaim-window bar 1, and the third confirmed post-breach candle is reclaim-window bar 3. This three-bar window is Author-Approved and Engineering-Provisional and is not extended.

## Bullish and Bearish Reclaim

| POI direction | Condition (within the 3-bar reclaim window) |
|---|---|
| Bullish (after breach below Zone Bottom) | `Reclaim Close ≥ Zone Bottom + Contact Tolerance` |
| Bearish (after breach above Zone Top) | `Reclaim Close ≤ Zone Top − Contact Tolerance` |

The earliest confirmed candle satisfying the condition is classified `RECLAIM_CONFIRMED`, and its time is stored. A close merely touching the boundary, or remaining outside it or within the tolerance margin, is not sufficient.

`RECLAIM_CONFIRMED` means only that price closed meaningfully back inside the bounded directional POI. It does **not** prove expected-direction exit, sufficient displacement, sufficient speed, sufficient reaction strength, BTMM confirmation, or entry confirmation. After a confirmed reclaim, the event transitions to `DISPLACEMENT_PENDING`.

## Three-Bar Displacement Window

Exactly the next 3 confirmed candles after the Reclaim Confirmation candle are evaluated. The reclaim candle is the displacement anchor; the first confirmed candle after the reclaim is displacement-window bar 1. The window is not extended beyond three confirmed candles.

## Bullish and Bearish Displacement After Reclaim

| POI direction | Requirement 1 (within the 3-bar displacement window) | Requirement 2 |
|---|---|---|
| Bullish | At least one confirmed close above `Zone Top + Contact Tolerance` | Reclaim-to-displacement leg classified `FAST` or `STRONG_FAST` |
| Bearish | At least one confirmed close below `Zone Bottom − Contact Tolerance` | Reclaim-to-displacement leg classified `FAST` or `STRONG_FAST` |

Both requirements must pass for `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`. The leg speed classification uses the already-approved Market Speed and Displacement Standard (Ambiguity 7) without modification — the reclaim close is the leg anchor, and Leg Bar Count, Net Directional Distance, Leg Path Distance, Normalized Speed Per Bar, Directional Efficiency, Directional Candle Share, and Speed Classification are used exactly as approved. No displacement score is created. The earliest post-reclaim candle on which all conditions first pass is stored.

## Reclaim Without Displacement

When `RECLAIM_CONFIRMED` occurs but the three-bar displacement window closes without confirmed displacement, classify `RECLAIM_WITHOUT_DISPLACEMENT`. This is an incomplete recovery event. It must **not** be classified as `FALSE_INVALIDATION_CONFIRMED`, and it must **not** independently satisfy the BTMM Liquidity Gate.

## False Invalidation

`FALSE_INVALIDATION_CONFIRMED` requires the **complete sequence**:

1. `CLOSE_BREACH_CANDIDATE`
2. `RECLAIM_CONFIRMED` within the next 3 confirmed candles
3. `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED` within the next 3 confirmed candles after reclaim

A Close Breach Candidate alone is not False Invalidation. A reclaim alone is not False Invalidation. Displacement without a preceding qualifying breach and reclaim is not False Invalidation. `false_invalidation_confirmation_time` equals `displacement_after_reclaim_confirmation_time` — it is never backdated to breach time, reclaim time, or original POI formation time.

## Liquidity-Evidence Relationship

A confirmed False Invalidation may be recorded as `liquidity_location = LIQUIDITY_AFTER_POI`, `liquidity_event_type = FALSE_INVALIDATION_CONFIRMED`. It may satisfy the approved BTMM Liquidity Gate only when its evidence source is reviewed and recorded as one of `EXPERT_LABELLED`, `RULE_BASED_REVIEWED`, or `HYBRID_REVIEWED`. An unreviewed `MODEL_PROPOSED` event must not satisfy the gate.

**Compatibility:** the previously approved BTMM State Machine used source values including `RULE_BASED` and `MODEL_PROPOSED`. Those values are not silently replaced or deleted. `RULE_BASED_REVIEWED` is the reviewed form of rule-based liquidity evidence introduced by this standard. No other approved BTMM state, gate, transition, or cancellation rule is changed.

False Invalidation does **not** automatically satisfy the Volume Pillar Gate, Reaction Gate, Reaction Speed Gate, or Formation Timeframe Gate, and does not establish entry validity or risk approval. See [BTMM_STATE_MACHINE.md](../btmm/BTMM_STATE_MACHINE.md), "Liquidity Gate."

## Sustained Breach Requirement

A Close Breach Candidate becomes a sustained breach only when, during its three-bar reclaim window, **all** pass:

1. At least 2 of the 3 confirmed closes remain beyond the Far Boundary by more than the applicable Overshoot Tolerance.
2. Reclaim-window bar 3 closes beyond the Far Boundary by more than its applicable Overshoot Tolerance.
3. No `RECLAIM_CONFIRMED` event occurred.

For a bullish POI, qualifying sustained closes are below Zone Bottom; for a bearish POI, above Zone Top. Overshoot Tolerance is calculated **separately for each evaluated candle** using that candle's own ATR(14), the fixed POI Zone Height, and the approved tolerance formula above — one stale ATR value is never reused for all three closes.

## Genuine Invalidation

`GENUINE_INVALIDATION_CONFIRMED` requires **all**:

- A `CLOSE_BREACH_CANDIDATE` occurred.
- No qualifying Reclaim occurred within the three-bar reclaim window.
- The Sustained Breach requirement passed.

For a bullish POI, sustained closes must be below Zone Bottom; for a bearish POI, above Zone Top. `genuine_invalidation_confirmation_time` is the close time of reclaim-window bar 3. This is the generic Version 1 final-invalidation rule for applicable bounded directional POIs, remains subject to future POI-family-specific override research, and must not be applied to excluded structures (Equal Highs, Equal Lows, Trendlines).

## Failed Reclaim

When a reclaim occurs but a new qualifying Close Breach Candidate happens before displacement is confirmed, classify `RECLAIM_FAILED`. The new breach must create a new `boundary_breach_event_id`, begin a new three-bar reclaim evaluation window, preserve the previous event history, and be evaluated independently — it must independently satisfy the Sustained Breach requirement. Genuine Invalidation is never declared immediately from the first new breach candle.

## Effect on POI Lifecycle

When `GENUINE_INVALIDATION_CONFIRMED` occurs, set `poi_lifecycle_status = INVALIDATED` for that specific POI instance. This must **not**: rewrite historical BTMM records, rewrite earlier valid interactions, change an existing trade outcome, invalidate a different POI, automatically create a reverse-direction POI, or alter the original POI boundaries or formation time. A reverse-direction POI must independently pass its own formation standard.

## Effect on Linked BTMM Setup

Any active BTMM setup connected to the invalidated POI becomes `BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` (the pre-existing BTMM cancellation reason — no new reason is created). See [BTMM_STATE_MACHINE.md](../btmm/BTMM_STATE_MACHINE.md), "Cancellation Reasons."

## No Reactivation

`INVALIDATED → ACTIVE` is not allowed for the same POI instance. A later reaction from the same general price area requires a new POI record, a new POI ID, a new formation time, new evidence, new lifecycle events, and (where applicable) new BTMM setup records. The invalidated POI is never rewritten or reactivated.

## Repeated Tap Definition

One tap equals one distinct POI interaction event; multiple candles belonging to one continuous interaction count as one tap. A later interaction becomes a **new** tap only when all of:

1. Price previously exits the POI in the expected reaction direction.
2. At least one confirmed candle closes beyond the Entry Boundary by more than Contact Tolerance.
3. Price later touches or re-enters the POI.

| POI direction | Separation condition |
|---|---|
| Bullish | Confirmed close above `Zone Top + Contact Tolerance` |
| Bearish | Confirmed close below `Zone Bottom − Contact Tolerance` |

Without this confirmed separation, continued candles inside or around the POI remain part of the same interaction and same tap.

## Repeated Tap Classifications

| tap_count | tap_classification |
|---|---|
| 1 | `INITIAL_TAP` |
| 2 | `REPEATED_TAP` |
| ≥3 | `MULTIPLE_REPEATED_TAPS` |

Every tap is preserved as a separate interaction record linked to the same POI; earlier taps are never overwritten.

## No Automatic Degradation

Repeated taps are counted, but Version 1 does **not** assume: a second tap automatically weakens the POI, a third tap automatically invalidates the POI, more taps automatically strengthen the POI, tap count automatically determines freshness, or tap count automatically determines entry validity. `tap_count` is evidence only. This standard does not create a Repeated Tap Strength Score, Freshness Score, Automatic Tap Degradation, Automatic Tap Upgrade, or Automatic Tap-Based Invalidation. Repeated-touch degradation remains an empirical-calibration question. A repeated tap may create a new BTMM setup record under the approved BTMM State Machine.

## Event States

`NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED`.

These are event-level POI lifecycle states and must not replace the approved BTMM primary states (`BTMM_CANDIDATE`/`BTMM_FORMING`/`BTMM_BLOCKED`/`BTMM_CONFIRMED`/`BTMM_CANCELLED`).

## Allowed and Forbidden Transitions

**Allowed:**

```
NO_BREACH → CLOSE_BREACH_CANDIDATE → RECLAIM_PENDING → RECLAIM_CONFIRMED
  → DISPLACEMENT_PENDING → DISPLACEMENT_AFTER_RECLAIM_CONFIRMED
  → FALSE_INVALIDATION_CONFIRMED

RECLAIM_PENDING → GENUINE_INVALIDATION_CONFIRMED

DISPLACEMENT_PENDING → RECLAIM_WITHOUT_DISPLACEMENT

DISPLACEMENT_PENDING → RECLAIM_FAILED → New CLOSE_BREACH_CANDIDATE event
```

**Forbidden (for the same boundary-breach event):**

```
GENUINE_INVALIDATION_CONFIRMED → FALSE_INVALIDATION_CONFIRMED
FALSE_INVALIDATION_CONFIRMED → GENUINE_INVALIDATION_CONFIRMED
```

A later qualifying breach requires a new `boundary_breach_event_id`.

## Timing and Non-Repainting

Preserved: `close_breach_time`, `reclaim_window_end_time`, `reclaim_confirmation_time`, `displacement_window_end_time`, `displacement_confirmation_time`, `false_invalidation_confirmation_time`, `genuine_invalidation_confirmation_time`.

Events become available only after their complete conditions are confirmed. Never backdated: reclaim to breach time; False Invalidation to breach or reclaim time; Genuine Invalidation before reclaim-window bar 3 closes; tap separation before the qualifying separation candle closes. Once recorded: event ID never changes, POI ID never changes, event confirmation time never moves, historical event evidence remains auditable, and later outcomes never rewrite the event classification.

## Required Fields

Preserved independently (no composite score): `boundary_breach_event_id`, `poi_id`, `poi_type`, `poi_direction`, `zone_top`, `zone_bottom`, `zone_height`, `entry_boundary`, `far_boundary`, `breach_candle_id`, `breach_close`, `breach_distance`, `breach_overshoot_tolerance`, `close_breach_time`, `reclaim_status`, `reclaim_close`, `reclaim_contact_tolerance`, `reclaim_confirmation_time`, `reclaim_window_bar_count`, `reclaim_window_end_time`, `displacement_status`, `displacement_direction`, `displacement_window_bar_count`, `displacement_window_end_time`, `displacement_speed_classification`, `displacement_confirmation_time`, `false_invalidation_status`, `false_invalidation_confirmation_time`, `genuine_invalidation_status`, `genuine_invalidation_confirmation_time`, `sustained_breach_close_count`, `tap_id`, `tap_count`, `tap_classification`, `interaction_id`, `liquidity_event_type`, `liquidity_evidence_source`, `event_status`, `evidence_version`, `timeframe`, `symbol`, `data_provider`, `created_at`, `updated_at`.

## Unresolved Exclusions and Calibration Requirements

Even with Ambiguity 15 resolved, the following remain unresolved, incomplete, or require later calibration:

- Statistical repeated-tap degradation by POI family.
- POI freshness scoring.
- POI expiration by age.
- POI-family-specific invalidation overrides.
- Trendline reclaim and final line invalidation.
- Equal High / Equal Low sweep lifecycle.
- Automatic market direction.
- Automatic analytical-framework context.
- Automatic session schedules.
- Entry confirmation, stop loss, take profit, risk-to-reward, lot sizing, news restrictions.
- Spread and slippage rules.
- Empirical calibration.
- Out-of-sample validation.
- Production approval.

The original ambiguity register may close with this decision, but the final knowledge gate remains **CLOSED** — see [KNOWLEDGE_COMPLETION_GATE.md](../KNOWLEDGE_COMPLETION_GATE.md).
