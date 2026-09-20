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

## Phase 2 result, and the causality finding that changes Phase 3

Phase 2 shipped: `_gate` now returns a `StructuralContext` (leg-origin candle
map, leg id and broken swing per origin, per-side pivot maps, broken vs unbroken
swings) and tags every `MAPPED_REVERSAL_CONTEXT` decision with
`origin_swing_id` / `broken_swing_id` / `break_candle_id`. All ids are frozen
record ids. No promotion moved.

Trend-aligned decisions deliberately carry **no** provenance: that branch is
classified from the direction timeline alone and genuinely does not know which
decision point the candidate belongs to. Claiming one would be a fabrication.

Tracing that gap produced the finding that reshapes Phase 3:

> **Every structural role is established by a structure break, so it is only
> true from that break's availability onwards.**

`immutable_structure_gate` returns the **final** prefix's context. Reading it to
promote a candidate that formed earlier is look-ahead — the same class of defect
as the P1 replay ATR-scope bug and the P3 reference-zone late start. So the
structural-origin gate **cannot** be a post-filter at the two insertion points
traced above, even though that is where the provenance is available.

It has to run inside the prefix machinery that already exists for exactly this
reason:

* incremental — inside `advance_leg_origin_frontier`, whose `context` field is
  by construction the state of its own prefix;
* batch — inside `immutable_structure_gate`'s prefix replay, which reproduces
  that union over all prefixes.

This is not extra machinery; it is the mechanism ORDER BLOCKS already use. It
does force one author-level semantic choice, because a reversal candidate whose
structural role only materialises at a later break can be handled two ways:

1. **re-time** it to that break, exactly as `MAPPED_REVERSAL_CONTEXT` already
   does — consistent with RC3, but it re-dates candidates that RC4 published at
   formation; or
2. **refuse** it unless the role was already established at its own
   availability — no re-dating, but a genuine leg-origin reversal that is only
   named as such by the break that confirms the leg would never be promoted.

Option 1 is the only one consistent with how the engine already treats ORDER
BLOCKS and reversal context, and option 2 would silently delete most true leg
origins. Phase 3 therefore builds on option 1, and the impact run will report
how many candidates it re-dates.

### Secondary finding: `PULLBACK_*` as drafted accepts everything

`structural_role.py` currently grants `PULLBACK_HIGH` / `PULLBACK_LOW` to any
confirmed swing the walk never broke. On the H3 six-wick staircase each wick is
its own confirmed swing high, so all six would pass and the gate would refuse
nothing. The role set has to be narrowed to structure the walk actually used:
leg origins, swings a break broke, and the walk's live protected / weak levels.
