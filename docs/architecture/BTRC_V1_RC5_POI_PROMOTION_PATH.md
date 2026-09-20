# BTRC-V1 RC5 — THE POI PROMOTION PATH AND ITS ONE RC5 INSERTION POINT

Traced 2026-09-20 before wiring structural provenance, so RC5 logic lands in
one place per execution path rather than being scattered across ten detectors.

## The path, per stage

| stage | batch | incremental |
|---|---|---|
| raw detectors | `poi/analyzer.py::_detect_bundle_candidates` L407-415 | `poi/detector_frontier.py::_new_local_candidates` (called from `advance_detector_frontier` L594) |
| formation quality + same-origin arbitration | `poi/qualification.py::qualify_candidates` (analyzer L419) | same function, `detector_frontier` L606 |
| structural-context / leg-origin gate | `poi/leg_origin.py::immutable_structure_gate` (analyzer L435) | `poi/leg_origin.py::advance_leg_origin_frontier` → `.newly_mapped` (`detector_frontier` L625-632) |
| RC4 FVG pre-availability filter | analyzer L444-457 | `detector_frontier` L636-642 |
| type-switch filter | analyzer L464 `enabled_poi_types` | equivalent downstream |
| **PoiObservation creation** | `analyzer.py::analyze_pois` L612-634 | `analyzer.py::_advance_poi_replay_state` L1318-1341 |
| cross-timeframe merge | `poi/overlap.py::resolve_merges` (L639 / L1929) | same |
| lifecycle attachment | `analyzer.py::_advance_poi_lifecycle` L978 | same |
| P5 | `btrc/t5_engine.py` | same |
| P8 | `tests/parity_support/p8_alert_oracle.py` + Pine | same |

Every detector family flows through the **same** `qualify_candidates` →
leg-origin gate → observation sequence. Detector-specific logic stops at the
detector.

## The authoritative RC5 insertion point

The earliest common location satisfying all four requirements — raw identity
known, structural context in hand, availability causality intact, and nothing
yet written into P3/P5/P8 — is **immediately after the leg-origin gate and
before the mapped list is assembled**:

* **batch:** `poi/analyzer.py::_detect_bundle_candidates`, between L435
  (`immutable_structure_gate`) and L457 (`mapped = [...]`)
* **incremental:** `poi/detector_frontier.py::advance_detector_frontier`,
  between L625 (`advance_leg_origin_frontier`) and L644 (`new_append_only`)

Two sites, one per execution path, and they already mirror each other exactly
(the RC4 FVG correction was applied at these same two points). `PoiObservation`
is not constructed until `analyze_pois` L612 / `_advance_poi_replay_state`
L1318, so nothing downstream is contaminated.

## What blocks provenance today

`poi/leg_origin.py::_gate` already holds, inside its reversal-context loop,
exactly the identifiers RC5 needs: the confirming `transition` (with
`broken_swing_id`, `break_candle_id`, `event_time_utc`,
`availability_time_utc`) and the `origin` swing (`record_id`), plus the leg
`direction`. **They are discarded.**

* `ContextDecision` carries only `(candidate, reason, structure_direction,
  mapped)`.
* `immutable_structure_gate` returns `(order_blocks, context_mapped)` and drops
  `final_decisions` after reading `.mapped`.
* `LegOriginFrontier` carries no decisions at all.

So Phase 2 is: extend `ContextDecision` with the cluster components and surface
them from both gates. No new IDs are fabricated and no second structure engine
is created — the values already exist in scope.

## Family divergence

Reversal family (gated by structural role): B2S, S2B, BUY/SELL_ORDER_BLOCK,
MORNING/EVENING_STAR, BULLISH/BEARISH_ENGULFING, HAMMER, SHOOTING_STAR,
BULL/BEAR_PRESSURE_WICK, and DOJI when it lands.

Not gated by structural role, and not to be regressed: BUY/SELL_FAIR_VALUE_GAP
(keeps the RC4 correction — material gap, FAST displacement, predecessor
expansion, no pre-availability consumption), BASE_RALLY, BASE_DROP,
SUPPORT_ZONE, RESISTANCE_ZONE. `poi/authority.py::REVERSAL_TYPES` already
encodes this split and `structural_role.assign_structural_roles` already skips
non-reversal families.

## Causality rule for the gate

`candidate_event_time_utc` stays the formation bar. `availability_time_utc`
stays whatever the existing causal structure assigned. The structural-origin
gate may **delay or refuse** promotion; it must never move availability earlier
or use a later bar's information to justify an earlier one.

## Separation of concerns

The structural-origin gate answers *"is this a meaningful POI at all?"*. The
authority ladder answers *"which of several meaningful candidates owns this
origin?"*. The gate must **not** reject valid same-origin subordinates just to
produce the desired final chart — on the M45 case the B2S, both SHOOTING STARs
and the BEAR PRESSURE WICK may all legitimately pass the gate, and authority
then leaves the B2S.
