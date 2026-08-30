# BTRC-V1 — P3 POI / Lifecycle Architecture and Contract Audit

Status: **ARCHITECTURE APPROVED (P3-ACCEL-1). ALL SIX AUTHOR DECISIONS
RESOLVED. ALL SIX BLOCKER-B ITEMS TEST-HARDENED. P3 CORE IMPLEMENTATION
AUTHORIZED; P3 CONTEXT DEFERRED.**

The audit below (Sections 1-31) is preserved as written. Sections 32-35
record the author decisions, the frozen CORE/CONTEXT split, the parity
ordering contract and the contract-hardening evidence, and supersede the
open questions in Sections 25 and 30 where they differ.

Produced by P3-ARCH-0 (2026-08-30) from repository HEAD
`7828e4f8495c00a9e1c9a7ec6bd7aa7fc21696d0` (P1 CLOSED, P2 CLOSED). Every
substantive claim cites production source (`file:line` at this HEAD) or a
test. Book/knowledge documents are cited only as *divergence* evidence — the
authoritative side is always `src/btmm_ai_scanner/poi/`.

---

## 1. Scope

P3 ports the validated Python POI subsystem — detection, canonical records,
and lifecycle — onto Pine v6, consuming the closed P1 measurement layer. This
document is the contract audit and Pine-native design. Explicit non-goals in
§31.

## 2. Authoritative Python source map

| path | role | class |
|---|---|---|
| `poi/analyzer.py` (1829) | entry `analyze_pois` + batch oracle + private incremental replay engine | production |
| `poi/enums.py` (167) | 32 `PoiType`, families, lifecycle enums, eligibility sets | production, frozen contract |
| `poi/observation.py` / `current_state.py` / `lifecycle.py:29-43` | `PoiObservation` (23 fields) / `CurrentPoiState` (21) / `PoiLifecycleTransition` (14) | production contracts |
| `poi/configuration.py` (160) | `PoiConfiguration` — ~40 constants, ALL `ENGINEERING_PROVISIONAL` (L73-75) | production |
| `poi/order_blocks.py`, `fair_value_gaps.py`, `bases.py`, `engulfing.py`, `pressure_wicks.py`, `reversal_candles.py`, `single_candle_reversals.py`, `three_candle_stars.py`, `reference_zones.py`, `period_levels.py` | the 10 detector modules | production |
| `poi/lifecycle.py` (399) | `run_poi_lifecycle` — the lifecycle oracle | production |
| `poi/overlap.py` (184) | overlap classification + `resolve_merges` | production |
| `poi/lifecycle_cursor.py`, `lifecycle_scheduler.py`, `scheduler_walk.py`, `cursor_fast_forward.py`, `persistent_*`, `interval_index.py`, `breach_index.py`, `detector_frontier.py` | A6 incremental engine (proven byte-identical to batch) | production (incremental path) |
| `measurements/candle_metrics.py` | body/wick/close-position/median-range primitives | production (P1) |
| `knowledge/poi_rules/` (36 md files) | book-derived rules | **docs only — NOT authoritative**; includes trendline POIs that do not exist in production (§25 D-blockers) |
| `tests/unit/test_{order_blocks,fair_value_gaps,bases,engulfing,pressure_wicks,reversal_candles,single_candle_reversals,three_candle_stars,reference_zones,period_levels,poi_analyzer_api,poi_overlap_merge_and_precedence,poi_lifecycle_and_freshness,poi_configuration,poi_exports,poi_batch_replay_equivalence,a6b1_lifecycle_cursor,...}.py` | contract pins | tests |

Entry: `analyze_pois(timeframe_inputs, configuration, identity_provider) -> PoiAnalysis`
(analyzer.py:487-491); invoked from `scanner/analyzer.py:246-250`. Call graph:
scanner → measurements (P1) → **POI detection → merge → overlap → lifecycle**
→ BTMM → BTRC. `detector_frontier.py` and the scheduler/cursor modules are the
incremental replay path only; batch `analyze_pois` never uses them
(analyzer.py:518 vs :1162-1164).

## 3. POI type matrix — counts verified from source

`PoiType` has exactly **32 members** (enums.py:15-46).
`LIFECYCLE_ELIGIBLE_POI_TYPES` = exactly **18** (enums.py:99-120);
`NOT_APPLICABLE_LIFECYCLE_POI_TYPES` = **14** (enums.py:122-139: EQH/EQL
liquidity + 12 period levels). **The historical "32 total / 18 eligible"
claim is CONFIRMED from source.** Families via `_FAMILY_BY_POI_TYPE`
(analyzer.py:88, all 32 mapped): VOLUME = OB×2, FVG×2, B2S/S2B×2, BASE×2,
PW×2 (10); PRICE_ACTION = ENG×2 + HAMMER + SHOOTING_STAR + MORNING/EVENING_STAR
(6); STRUCTURAL = S/R×2 + EQH/EQL×2 + period levels×12 (16).

Categories: (A) production-detected: all 32 (10 detectors, §5); (B)
context/reference: the 14 NOT_APPLICABLE; (C) lifecycle-eligible: 18; (D)
docs/tests-only types: trendline POIs (knowledge only, no enum member); (E)
reserved: none in the enum; two lifecycle enum states are dead (§9).
Machine-readable matrix: `artifacts/p3_arch/poi_type_matrix.csv`.

## 4. Canonical POI data model

`PoiObservation` (observation.py:15-38), 23 fields: record_id (UUIDv7),
content_fingerprint, symbol, source_timeframe, effective_timeframe, family,
poi_type, direction, zone_top (Decimal), zone_bottom (Decimal),
representative_price (Decimal|None — period levels only, analyzer.py:443-449),
strength_tier (PoiStrengthTier|None — None for FVG/reference/period),
source_candle_record_ids, source_measurement_record_ids,
merged_source_poi_record_ids, candidate_event_time_utc, confirmation_time_utc,
availability_time_utc, rule/contract/schema_version, evidence_classification,
provenance_id.

Downstream requirements (§19 details): BTMM consumes exactly {record_id,
symbol, source_timeframe, poi_type, direction, zone_top, zone_bottom,
confirmation_time_utc, availability_time_utc}; BTRC t5 additionally
{effective_timeframe, strength_tier}; consumed by nothing: family,
representative_price, the three source-id tuples, merged ids, envelope fields
(parity/serialization only).

## 5. Detector family contracts (source-exact; full details in the audit trail)

Common: pure batch functions over `(candles, configuration)`; Decimal
arithmetic; **no detector uses volume**; none uses P2 structure; no
within-detector dedup (analyzer-level identity dedup only); every candidate's
`confirmation_time_utc == availability_time_utc` = confirming candle's
availability (except reference zones, which inherit the P1 record's times).
Primitives from candle_metrics.py (total_range = high−low; body_efficiency;
wick shares; close positions; median_total_range).

| # | detector | types | condition (exact) | zone | visible at | tier |
|---|---|---|---|---|---|---|
| 1 | order_blocks.py:27 | BUY/SELL_ORDER_BLOCK | adjacent pair; ratio=range(disp)/range(origin) ≥ 2.0 (reject `<`, L43); bull: origin red AND disp green AND `disp.close > origin.high` (strict, L51); bear mirror | origin full wick range (L74-75) | displacement close | STRONG iff ratio ≥ 3.0 |
| 2 | fair_value_gaps.py:25 | BUY/SELL_FVG | 3 candles; bull `third.low > first.high` (strict, L41); bear `third.high < first.low`; middle unconstrained; **no minimum gap**; config unused (`del`, L29) | bull [first.high, third.low]; bear [third.high, first.low] | third close | none |
| 3 | reversal_candles.py:36 | BUY_TO_SELL / SELL_TO_BUY | candidate range ≥ 2.0× max range of prior 3; body_eff ≥ 0.60; close_position ≥ 0.70; doji excluded; **naming inversion**: red candle → SELL_TO_BUY (BULLISH), green → BUY_TO_SELL (BEARISH) (L62-69); requires close beyond candidate midpoint within next ≤3 bars else discarded | candidate full range | confirmation candle close (delayed) | STRONG 3.0/0.70/0.80 |
| 4 | bases.py:33 | BASE_RALLY/DROP | window len 2..6 + departure; 9 ordered gates (small-candle ≤0.50×dep; ratio ≥2.0; height ≤0.75×ATR14[last base bar] (fallback: departure range); height ≤0.60×dep; midpoint drift ≤0.25×height; pairwise overlap ≥0.50; departure close beyond base extreme) | base wick envelope | departure close | STRONG ratio≥3.0 AND max base range ≤0.3333×dep |
| 5 | pressure_wicks.py:38 | BULL/BEAR_PRESSURE_WICK | single candle; wick share ≥0.40, body_eff ≥0.25, dominance 2.0× (or opposite wick 0), close_position ≥0.60; baseline = median range of prior ≤20 | wick-only zone (bull: [min(o,c), low]) | own close | STRONG 0.50/0.30/3.0/0.70 AND range ≥1.25× median-20 |
| 6 | engulfing.py:27 | BULL/BEAR_ENGULFING | adjacent opposite-color pair; range ratio ≥ 2.0. **NO body-engulfment comparison exists** (audited: no cross-candle open/close comparison) | engulfed full range | engulfing close | STRONG ratio ≥ 3.0 |
| 7 | single_candle_reversals.py:32 | HAMMER / SHOOTING_STAR | wick share ≥0.60, body_eff ≤0.30, opposite wick ≤0.10; no trend filter | wick-only zone | own close | STRONG 0.70/0.20/0.05 |
| 8 | three_candle_stars.py:29 | MORNING/EVENING_STAR | middle body_eff ≤0.10 (doji); first red/third green with `third.close > first-candle midpoint` (morning; mirror evening); no gap/size rules | middle full range | third close | STRONG middle ≤0.05 |
| 9 | reference_zones.py:26 | SUPPORT/RESISTANCE_ZONE, EQH/EQL_LIQUIDITY | pure 1:1 projection of P1 `support_resistance_zones` + `equal_level_clusters`; no thresholds; SUPPORT→BULLISH, RESISTANCE→BEARISH, **EQH→BEARISH, EQL→BULLISH** | copied verbatim | P1 record's own times | none |
| 10 | period_levels.py:161 | 12 period types | UTC calendar day / ISO week (Mon 00:00 UTC) / calendar month; consecutive-window grouping (previous = previous window WITH candles, weekends skipped); extremes strict >/<, first-wins ties; config `del`'d | point: zone_top = zone_bottom = representative_price | current: last candle of window (re-emitted per new extreme); previous: first candle of next window | none |

Detector execution order (analyzer.py:388-407): OB → FVG → reversal candles →
bases → pressure wicks → engulfing → single-candle reversals → three-candle
stars → reference zones → period levels; then `enabled_poi_types` filter.

Notable source-vs-folklore findings (author attention, §25/§30): the OB
definition is NOT "last opposite candle before impulse" (no lookback, no
structure/displacement requirement — any opposite pair qualifying by ratio +
close-through); ENGULFING has no body-engulfment rule (range ratio + colors
only), so every OB is also an engulfing candidate at the same pair; FVG has no
minimum gap (one tick qualifies); B2S/S2B naming is inverted relative to
candle color.

## 6. Region geometry

Zones are closed price intervals `[zone_bottom, zone_top]` with **no right
edge, no extension logic, no expiry** (lifecycle walks the entire
post-availability suffix; §16). Period levels are degenerate point zones
(top == bottom). Touch = inclusive wick overlap: `candle.low <= zone_top and
candle.high >= zone_bottom` (lifecycle.py:111-114). Breach/reclaim/
displacement are close-only (§13-§15). Overlap classification treats zones as
closed intervals with non-strict containment; exact-boundary sharing =
BOUNDARY_TOUCHING (excluded from both records and merge; overlap.py:58-63,
96-97, 147-148); a point ON an interval boundary is CONTAINED_BY
(overlap.py:44-52).

## 7. Identity

`record_id = identity_provider.identify(POI_OBSERVATION, semantic_key)` with
three key shapes (analyzer.py:410-436): period levels → (symbol, timeframe,
type, period_start_iso, period_end_iso, rule_version); reference zones →
(symbol, timeframe, type, source_zone_record_id, rule_version); all others →
(symbol, timeframe, type, *source candle record ids, rule_version).
**POI_IDENTITY_STABLE = TRUE** — the id is a pure function of the semantic key,
unchanged by merge/interaction/breach/reclaim/invalidation (merge changes only
merged ids + effective_timeframe + fingerprint; analyzer.py:547-561). For Pine,
the feed-anchored equivalent identity is (poi_type, source-candle event
times[, period window]) — timestamps, not execution-origin indices (§40 note:
Pine cannot compute the UUID itself; see blocker C-1 for the ordering
consequence).

## 8. Merge / dedup

`resolve_merges` (overlap.py:114-184) is **provenance annotation, not
consolidation**: eligibility = same (symbol, direction, poi_type), parent on a
STRICTLY stronger timeframe (rank M1=1..W1=8), zones overlapping/contains/
contained (BOUNDARY_TOUCHING excluded). One best parent per child:
`(-rank, availability, str(record_id))`. Child keeps its record/bounds and is
re-stamped `effective_timeframe = parent's`; parent gains
`merged_source_poi_record_ids = tuple(sorted(children, key=str))` — canonical
unordered set (the A6 S1 ordering incident is FIXED at source and test-pinned:
overlap.py:167-184, test_poi_overlap_merge_and_precedence.py:182-234). No
bounds union, no strength transfer, no removal, NOT transitive (chains stay
chains; test :237-250). **No one-region rule exists anywhere** (grep-verified).
Merge is cross-timeframe ONLY — a proven single-timeframe no-op
(analyzer.py:790-794, 1731-1734) → a single-TF P3 core needs NO merge at all.
Merge (batch) runs before lifecycle but lifecycle is unaffected by it
(observation's own bounds and source_timeframe candles; analyzer.py:591-602).

## 9. Lifecycle state machine

States (enums.py:55-66): NOT_APPLICABLE, NO_BREACH (initial,
lifecycle.py:177), CLOSE_BREACH_CANDIDATE, RECLAIM_PENDING†,
RECLAIM_CONFIRMED, DISPLACEMENT_PENDING†, DISPLACEMENT_AFTER_RECLAIM_CONFIRMED,
RECLAIM_WITHOUT_DISPLACEMENT, RECLAIM_FAILED, FALSE_INVALIDATION_CONFIRMED,
GENUINE_INVALIDATION_CONFIRMED. † = **dead: defined but never emitted anywhere
in src** (grep-verified; blocker C-2).

Transitions (lifecycle.py:193-387; episodic — later breaches start new
episodes):
- NO_BREACH/any non-terminal —breach→ CLOSE_BREACH_CANDIDATE (:201-213)
- CBC —reclaim within bars i+1..i+3→ RECLAIM_CONFIRMED (:215-240)
- RC —fast displacement leg within reclaim+1..+3→
  DISPLACEMENT_AFTER_RECLAIM_CONFIRMED → FALSE_INVALIDATION_CONFIRMED
  (back-to-back, same triggering candle, :276-301); resume at reclaim+1
- RC —window elapsed, none→ RECLAIM_WITHOUT_DISPLACEMENT (:302-314; provisional
  until the displacement window completes — cursor :253-255)
- CBC —no reclaim + full 3-bar window + ≥2 qualifying breach closes + bar-3
  breaches→ **GENUINE_INVALIDATION_CONFIRMED — the ONLY terminal state**
  (:337-368; walk frozen; taps/age continue)
- CBC —no reclaim, not genuine, ≥1 window bar→ RECLAIM_FAILED (:370-383;
  partial-window tail is provisional per cursor :329-334); resume at window end
- breach on final candle: stays CLOSE_BREACH_CANDIDATE.

`PoiLifecycleTransition` (lifecycle.py:29-43): record_id, fingerprint, symbol,
timeframe, poi_record_id, transition_type, triggering_candle_record_id,
event_time_utc, availability_time_utc + envelope.

## 10-12. Interaction / overshoot / reaction

**Interaction (taps)**: inclusive wick overlap (§6 formula); maximal runs of
consecutive touching candles = ONE tap (lifecycle.py:127-146); FRESH →
INTERACTED iff tap_count > 0; classification 1/2/≥3 →
INITIAL/REPEATED/MULTIPLE_REPEATED_TAPS. Gap-through without range overlap = no
tap (but can breach — test_a6b1_lifecycle_cursor.py:190-208). Taps are fully
independent of the breach walk, never gate or degrade status, and keep
accumulating after terminal invalidation. **No downstream consumer reads
freshness/taps** (§19) → P3-DEFER.

**Overshoot**: there is no standalone "overshoot" state. The overshoot
tolerance IS the breach threshold: `max(2*min_tick, min(0.10*ATR,
0.25*zone_height))` (lifecycle.py:179-186; config L64-65). A close beyond the
adverse boundary but within tolerance stays NO_BREACH.

**Reaction**: the POI package has NO reaction measurement. The only
speed/reaction concept is the displacement-leg classification inside the
lifecycle (measurements/legs.py via `measure_leg`; §14). BTMM's reaction
concepts (btmm/reaction.py) are P4, not P3.

## 13. Breach

Close-only, strict, adverse far boundary (lifecycle.py:75-84): BULLISH
`(zone_bottom − close) > overshoot_tol`; BEARISH `(close − zone_top) >
overshoot_tol`. Wick-through never breaches. A gap-away candle that never
touches the zone CAN breach. Reference ATR = full-prefix Wilder ATR-14 at the
candle (analyzer.py:568) with fallback to the candle's own range
(lifecycle.py:66-72); tolerance evaluated per bar.

## 14. Reclaim & displacement

Reclaim (lifecycle.py:87-96, window :216-217 `range(i+1, min(i+1+3, n))`):
close-only, NON-strict, near boundary + contact tolerance (`max(2*tick,
min(0.05*ATR, 0.10*height))`): BULLISH `close >= zone_bottom + contact`;
BEARISH `close <= zone_top − contact`. Same-candle reclaim impossible (window
starts at i+1). First qualifying bar wins. Displacement (window reclaim+1..+3):
close beyond the FAR boundary with contact margin AND `measure_leg` classifies
FAST (speed ≥0.50, efficiency ≥0.60, share ≥0.67) or STRONG_FAST
(0.75/0.75/0.80) — thresholds **hard-coded in lifecycle.py:262-267, not
config**. Reclaim does NOT create new identity; downstream BTMM sees reclaimed
POIs only via the FALSE_INVALIDATION_CONFIRMED liquidity event (§19).

## 15. Invalidation

Exactly two confirmed verdicts: FALSE_INVALIDATION_CONFIRMED (breach + reclaim
+ fast displacement; non-terminal) and GENUINE_INVALIDATION_CONFIRMED
(sustained breach; terminal, §9). No other route: no age route, no
opposite-structure route, no fill route, no interaction-count route, no merge
replacement (verified across lifecycle.py — every route enumerated above).

## 16. Expiry / aging

**None.** `age_in_confirmed_bars` and `elapsed_time_since_availability` are
descriptive only (lifecycle.py:389; analyzer.py:604-613; pinned by
test_poi_lifecycle_and_freshness.py:378-384). POIs are never removed by age;
observations and states are retained after invalidation (§18 of audit;
analyzer keeps everything). This drives the persistence decision (§21).

## 17. BTMM eligibility

`BtmmConfiguration.eligible_poi_types` defaults to exactly
`LIFECYCLE_ELIGIBLE_POI_TYPES` (btmm/configuration.py:16; shrink-only,
:102-106) — the 18 zone types. Setup creation additionally requires
`source_timeframe ∈ formation_timeframes {M5, M15} ∪ supporting_only {M1}`
(btmm/analyzer.py:400-412); the 14 NOT_APPLICABLE types never form setups but
do satisfy analyze_btmm's non-empty-POI guard (btmm/analyzer.py:355).
**Prior "18 eligible" claim CONFIRMED.** Full table:
`artifacts/p3_arch/poi_type_matrix.csv`.

## 18. P1 / P2 dependencies

P1: `analyze_pois` consumes ONLY `support_resistance_zones` +
`equal_level_clusters` from `MarketMeasurementAnalysis` (analyzer.py:400-405)
plus raw candles; ATR-14 is recomputed internally from candles
(analyzer.py:568) — the same full-prefix Wilder ATR the Pine P1 engine already
maintains incrementally. Swings, displacement observations, and trendlines are
NOT consumed by POI (audited: unused). Volume: never. Per-family matrix:
`artifacts/p3_arch/poi_dependency_matrix.csv`.

**P2: ZERO.** No `btmm_ai_scanner.structure` import exists anywhere in poi/
(grep-verified). P3 Pine therefore needs NOTHING from the P2 walk — it can be
built purely on P1 arrays + candles. (Coupling direction is reversed: BTRC t3
combines structure with POI transitions — P5 territory.)

## 19. Downstream contract (P3 → P4/P5)

BTMM (P4) consumes exactly: PoiObservation {record_id, symbol,
source_timeframe, poi_type, direction, zone_top, zone_bottom,
confirmation_time_utc, availability_time_utc} (btmm/analyzer.py:409-435,
setup_delta.py:96-126, btmm/lifecycle.py:233-236) + lifecycle transition
events restricted to `_RELEVANT_POI_TRANSITION_TYPES = {GENUINE_INVALIDATION_
CONFIRMED, FALSE_INVALIDATION_CONFIRMED}` (btmm/analyzer.py:644-649) carrying
{poi_record_id, transition_type, availability_time_utc,
triggering_candle_record_id, event_time_utc, symbol, timeframe}
(btmm/analyzer.py:657-687). BTMM reads NO CurrentPoiState and NO overlap
records. BTRC (P5): t3 reads transitions filtered to
GENUINE_INVALIDATION_CONFIRMED + `.timeframe` (t3_engine.py:326-329, 492);
t5 reads latest observation by `(availability, str(record_id))`,
effective_timeframe, direction, poi_type, strength_tier (STRONG→85,
STANDARD→60, None→50; t5_engine.py:59-174) and `(poi_record_id,
poi_lifecycle_status)` from current states. Consumed by NOTHING:
PoiOverlapRelationship (excluded even from replay parity — replay.py:300-392),
freshness/taps/age fields, family, representative_price, source-id tuples,
merged ids.

## 20. Bounded-history analysis

Per family (detection): OB/ENG (2 bars), FVG/stars (3), single-candle (1), PW
(21 incl. baseline), reversal candles (7), bases (7 + full-prefix ATR — the
ATR is persistent P1 state, same as P2's solution) → **SAFE_BOUNDED_REBUILD**
under the proven ≤21-candle frontier ring (detector_frontier.py:71, 308-345).
Reference zones → projection of P1 state (P1 already bounded-proven) →
SAFE_BOUNDED_REBUILD. Period levels → **NEEDS_PREHISTORY as a batch** (a
month ≫ 300 bars; nothing in analyzer bounds the span) but the production
frontier solves it with bounded per-granularity running extrema
(`_PeriodGranularityState`, detector_frontier.py:74-87, 348-508) →
NEEDS_PERSISTENT_IDENTITY-style running state, not raw prehistory.

Lifecycle: **NEEDS_PERSISTENT_LIFECYCLE.** Current status depends on the whole
post-availability suffix (episodic walk, no expiry), but the production cursor
proves the sufficient persistent state is bounded: committed status + resume
index + ≤7-candle open-window buffer + O(1) tap counters
(lifecycle_cursor.py docstring L6-21; buffer bound test :167-168; byte-equal
to batch at every prefix, test :111-130).

## 21. Left-edge counterexamples → persistence decision

(1) A POI genuinely invalidated 400 bars ago: a naive 300-bar rebuild
resurrects it as NO_BREACH — BTMM's POI_REJECTED cancellation would silently
un-happen. (2) A breach at bar −310 with reclaim at −308: rebuild loses the
FALSE_INVALIDATION liquidity evidence BTMM already consumed. (3) A POI whose
origin candles left the window: no expiry exists, so the zone must remain
actionable; rebuild cannot re-detect it. (4) tap history before the left edge
(deferred anyway). (5) previous-month period levels: whole periods precede the
window. Naive bounded rebuild therefore LOSES required semantics.

**P3_PERSISTENT_LIFECYCLE_REQUIRED = TRUE** (and a persistent POI registry
with it). This is the central architectural difference from P2, where bounded
rebuild sufficed and the frontier was proven unnecessary.

## 22-23. Pine record design & semantics/rendering separation

Two-record split mirroring Python's immutable-observation / evolving-state
divide — immutable `PoiRec` + mutable `PoiLife` (single mutable record
rejected: identity/fingerprint semantics and the BTMM contract treat geometry
as frozen):

PoiRec (immutable; from PoiObservation, minimum-first): stableKey (int —
feed-anchored: first source-candle event time; full identity = type + source
times, §7), poiType (int code), direction (int), zoneTop/zoneBottom (float),
candidateTime/confirmTime/availTime (int ms), strengthTier (int: na/1/2),
sourceTf implicit (single-TF core). Derivable, not stored: family (type→family
map), representative_price (== bounds for period levels).

PoiLife (mutable; from cursor state, §20): status (int code), resumeIdx/
committed boundary, openWindow buffer refs (≤7), episode bookkeeping, and —
deferred unless parity requires — tapCount/inTap. Emitted events: only the two
BTMM-relevant transition codes + full status for diagnostics.

Semantic layer = parallel `array<...>` / user-defined types, zero
`box/line/label` dependence; rendering is a later projection of the newest N
active records only (§62 policy). All detection/lifecycle testable via digest
plots alone, exactly like P2.

## 24. Runtime / resource analysis

Current P2 DEV baseline (source-grounded): 2281 lines / 127,631 bytes; 26
`plot(` occurrences; declared `max_lines_count=500, max_labels_count=500,
max_boxes_count=500, calc_bars_count=1800` (v1.pine:44).

P3 estimates (300-bar M15 view, 1800-bar life): detection O(1) amortized per
bar via ring (≤21-candle slices, ≤5 base lengths); lifecycle per bar naive =
O(active POIs) touch/breach checks — with registry growth ~0.2-1 POI/bar over
1800 bars → 400-2000 live records; a full per-bar scan of 2000 zones × cheap
comparisons is the main hotspot (Pine has no treap; the production wake-index
optimization does not port directly). Mitigations to evaluate at P3-I-PERF:
(a) terminal POIs skip the walk (only taps continue — and taps are deferred);
(b) per-bar early exit on price-band partitioning; (c) measured cap +
disclosure if needed (author decision AD-5). Memory: ~2000 records × ~12
fields ≈ 24k array elements — well inside Pine array capacity; risk is CPU,
not memory. RESOURCE RISK: **MEDIUM** (unmeasured registry growth rate is the
unknown; must be measured on real data in the first perf slice).
`request.security`: **0** — nothing in P3 core needs cross-TF data (§41).

## 25. Contract blockers

Counts: **A = 14, B = 6, C = 3, D = 3, E = 2, F = 4.**

BLOCKER-B (explicit but under-tested; fix = P3-I0 REQUIRED, Python test
hardening in a later authorized task — NOT this one): B-1 OB exact-ratio-2.0/
3.0 boundary untested; B-2 FVG exact-touch (`third.low == first.high`) and
one-tick gap untested; B-3 bases real-ATR branch never exercised (all fixtures
< 14 bars → fallback path only); B-4 STRONG tiers untested for engulfing,
stars, reversal candles, single-candle reversals; B-5 pressure-wick dominance
`uw == 0` escape + 20-bar baseline boundary untested; B-6 period-level
December→January rollover + equal-extreme tie untested.

BLOCKER-C (incidental/undocumented behavior needing contract decision): C-1
observation ordering's final tie-break is `str(record_id)` (analyzer.py:732) —
UUIDs Pine cannot compute; ties are only possible for same-bar same-type
same-zone duplicates (rare) but parity ordering needs a feed-anchored
tie-break contract (AD-1). C-2 dead enum states RECLAIM_PENDING /
DISPLACEMENT_PENDING (defined, never emitted) — reserve or prune (AD-2). C-3
RECLAIM_FAILED partial-window "provisional tail" semantics documented only in
cursor comments (lifecycle_cursor.py:329-334) — live-edge behavior contract
should be stated explicitly before Pine.

BLOCKER-D (code/docs conflict; author decision): D-1 engulfing lacks any
body-engulfment rule vs knowledge/poi_rules engulfing docs (AD-3); D-2 OB
definition vs book "last opposite candle before impulse" (AD-3); D-3 trendline
POIs exist in knowledge/poi_rules/structural (bearish/bullish_trendline.md)
but have NO PoiType member — excluded from P3 unless Python adds them first
(AD-4).

BLOCKER-E (Pine adaptation required): E-1 period-level month/week batch
semantics exceed any bounded window → adopt frontier-style running extrema
with origin disclosure (AD-6); E-2 per-bar lifecycle scan over an unbounded
registry (no expiry) needs a Pine-native efficiency strategy (§24, AD-5).

BLOCKER-F (excluded from P3 core; later phases): F-1 overlap relationship
records (zero consumers); F-2 cross-TF merge + effective_timeframe (single-TF
no-op; consumer is BTRC t5 → P5/P6); F-3 freshness/taps/age (zero consumers);
F-4 H4+/MTF orchestration (no such logic exists in POI detection — merge rank
is generic; MTF stays P6).

## 26. Minimum P3 scope

P3-CORE REQUIRED: the 8 pattern detectors (16 types) + SUPPORT/RESISTANCE_ZONE
projection (18 eligible types complete); stable identity; persistent registry;
lifecycle walk (breach/reclaim/displacement/false/genuine) with persistent
cursor state; the two BTMM-relevant transition events; per-POI
poi_lifecycle_status; strength_tier (cheap, detector-native, needed by P5).
P3-CONTEXT REQUIRED: EQH/EQL projection + 12 period levels via running extrema
(satisfy completeness + BTRC t5's latest-POI scan; running-extrema origin
semantics per AD-6). P3-DEFER→P4: nothing (BTMM consumes only core outputs).
P3-DEFER→P5: effective_timeframe (needs merge), CurrentPoiState beyond
(poi_record_id, status). P3-DEFER→P6: cross-TF merge, overlap records, MTF.
UI-ONLY: all rendering, colors, labels. DEFER-INDEFINITE (no consumer):
freshness/taps/age, overlap records, representative_price beyond period
levels, source-id tuples.

## 27. Implementation slices (proposal — not started)

| ID | scope | gates (each: clean baseline → tests → commit → SHA discipline → no next slice until accepted) |
|---|---|---|
| P3-I0 | Python contract-test hardening: the six B-blockers + C-3 live-edge contract + AD resolutions | full suite green; NO semantic changes |
| P3-I1 | Pine PoiRec/PoiLife types + identity + type/direction/tier code vocabulary + diagnostics | compile gate; static equivalence tests vs frozen P2 base |
| P3-I2 | OB + engulfing (2-bar ring) | synthetic Python↔Pine-model parity per family |
| P3-I3 | FVG + three-candle stars (3-bar ring) | same |
| P3-I4 | pressure wicks + hammer/shooting star (1-bar + 20-median baseline) | same |
| P3-I5 | reversal candles (7-bar ring, delayed confirmation) | same |
| P3-I6 | bases (2..6+departure, incremental ATR reuse) | same |
| P3-I7 | reference-zone projection off P1 internal S/R + EQ arrays | same + P1 non-regression |
| P3-I8 | period levels via running extrema + origin disclosure | same |
| P3-I9 | lifecycle walk + persistent cursor state (breach/reclaim/displacement/invalidation) | prefix-parity campaign vs run_poi_lifecycle model |
| P3-I10 | transition relay + current-status outputs (BTMM-facing) | consolidation suite |
| P3-I11 | parity digest instrumentation (atomic probe appendix) | digest contract tests |
| P3-I-PERF | TradingView runtime/resource campaign (registry growth measured on real data) | runtime gate à la P2 (0 errors) |
| P3-PARITY | atomic same-execution real-data bundle + offline replay | 100% digest match gate |

## 28-29. Test & parity strategy

LEVEL 1 (Python): P3-I0 hardening above. LEVEL 2 (synthetic): per-family
Pine-model transcriptions tested against the production oracle exactly as P2
did (fixtures per detector + lifecycle event; prefix parity for the cursor).
LEVEL 3 (real data): **atomic same-execution bundle only** — one Pine
execution hashing raw context + P1-relevant inputs + per-family POI digests +
lifecycle digests; never separate-session captures (P2's feed-revision lesson
is standing policy). Digest design: reuse the frozen p2_digest contract
(MOD/BASE, na→0, signed encoding, tick prices, ms times); hashable per-bar POI
state = ordered active records (stableKey, type, direction, boundsTicks,
confirmTime, status, tier) + counts; ordering = the frozen observation sort
key with a feed-anchored final tie-break (pending AD-1); per-family and
per-field localization hashes like P2's 15. Digest contract must NOT freeze
until AD-1..AD-6 resolve.

**P3_PARITY_MIN_CONTEXT_BARS = 1800** for everything except month-scope period
levels: 1800 M15 bars ≈ 27 calendar days < previous+current month (needs
~2 months ≈ 3800-4400 M15 bars > calc budget). Plan: month-level types get
running-extrema-from-origin semantics with disclosure (AD-6) or a dedicated
higher-TF capture; day/week levels fit inside 1800. Everything else (≤21-bar
detection windows, full-prefix ATR, lifecycle-from-origin) is exactly
reproducible from the same 1800-bar atomic context, replayed origin-aligned as
in P2-PARITY-STATE-2.

## 30. Author decision queue

| ID | question | evidence | options | recommendation | risk if unresolved |
|---|---|---|---|---|---|
| AD-1 | Parity ordering tie-break when `str(record_id)` is unreachable in Pine | analyzer.py:720-734 | (a) add feed-anchored tie-break to the parity digest contract only; (b) add it to Python ordering contract | (a) — instrumentation-only, no production change | rare same-bar duplicates could hash in different orders |
| AD-2 | Dead states RECLAIM_PENDING / DISPLACEMENT_PENDING | enums.py:58,60; zero emit sites | (a) reserve codes in Pine, never emit (mirror Python); (b) prune from Python enum first | (a) | none if reserved; enum drift if pruned later |
| AD-3 | Engulfing has no body-engulfment; OB is not "last opposite before impulse" — port source as-is? | engulfing.py:42-55; order_blocks.py:36-58 vs knowledge/poi_rules | (a) port source verbatim (P2 discipline: source wins); (b) change Python first (separate semantic task) | (a) — any semantic change is its own authorized Python task with tests, BEFORE porting | porting a moving target |
| AD-4 | Trendline POIs (docs only, no PoiType) | knowledge/poi_rules/structural vs enums.py:15-46 | (a) exclude from P3; (b) add to Python first | (a) | none — no downstream consumer |
| AD-5 | Lifecycle registry growth strategy on Pine (no expiry in source) | §16, §24 | (a) exact unbounded registry, perf-gated by measurement; (b) author-approved retention cap with disclosure | (a) first, (b) only with evidence | RE10110-class runtime risk if unmeasured |
| AD-6 | Month/week period levels under bounded execution | period_levels.py:161-201; frontier :348-508 | (a) running extrema from execution origin + published-region disclosure (frontier model); (b) exclude month types from P3 parity gate; (c) higher-TF dedicated capture | (a)+(b) combined | false parity mismatches or silent wrong levels |

## 31. Explicit non-goals

No Pine implementation, no POI boxes/plots/alerts, no `request.security`, no
BTMM (P4), no BTRC (P5), no MTF orchestration (P6), no UI, no alerts (events
reserved as internal codes for a future P8), no changes to Python semantics,
no threshold tuning, no trading/execution logic. Rendering policy (future):
draw only the newest ≤ N active eligible zones (N ≤ 50 boxes suggested),
semantic arrays never truncated by rendering limits; migration target is the
current P2 DEV script extended in place (atomic probe stays
instrumentation-only); eventual dev title "BTMM + POI + BTRC Scanner
[P3 DEV]" via a NEW saved TradingView script copied forward so the P1/P2
saved scripts remain preserved; per-slice rollback discipline identical to P2
(baseline SHA → tests → commit → compile gate → acceptance before next slice).

---

# PART II — P3-ACCEL-1 RESOLUTIONS

Authoritative over Sections 25 and 30 wherever they differ.

## 32. Author decisions — ALL RESOLVED

| ID | resolution | consequence for the port |
|---|---|---|
| **AD-1** | **RESOLVED.** Pine never recreates Python UUIDs. Pine carries a feed-anchored semantic stable key; parity hashing sorts by the semantic tuple in Section 34. | Precondition verified from source: BTMM consumes `record_id` only as an **identity token** (`btmm/analyzer.py:418,516` build semantic keys from `str(...)`), never as a comparison order. The ONLY ordering use of a UUID anywhere downstream is `btrc/t5_engine.py:65` (`max` by `(availability_time_utc, str(record_id))`), which is P5 and deferred. UUID ordering therefore has **no semantic effect on P3 CORE to P4**, so a Pine-reproducible ordering is safe. **Carried forward to P5:** porting BTRC will need its own decision on that tie-break. |
| **AD-2** | **RESOLVED.** `RECLAIM_PENDING` / `DISPLACEMENT_PENDING` are **RESERVED / CURRENTLY UNREACHABLE**. Python enums untouched; Pine reserves the codes and never transitions into them. | Pinned by `test_p3_core_contracts.py::test_dead_lifecycle_states_are_never_emitted_by_any_reachable_path` (all four reachable paths) and `::test_dead_states_remain_defined_in_the_enums`. |
| **AD-3** | **RESOLVED.** Port production **exactly as written**; documentation is corrected toward source, never the reverse. | Pinned by four source-as-is guards: engulfing qualifying without textbook body-engulfment, the adjacent-pair Order Block contract, and both B2S/S2B naming directions. |
| **AD-4** | **RESOLVED.** Trendline "POIs" are **excluded** from P3. No production `PoiType` exists for them; trendlines remain P1 measurement/context. | No Pine work. `knowledge/poi_rules/structural/*trendline*.md` is documentation only and is not a contract. |
| **AD-5** | **RESOLVED.** Bounded detection + **persistent** semantic POI registry + persistent per-POI lifecycle cursor. Immutable `PoiRec` + mutable `PoiLife`. No semantic expiry and no truncation of semantic records; rendering limits stay independent of retention. | Terminal (genuine-invalidated) records may skip future lifecycle work, which is permitted because source already freezes their walk (`lifecycle.py:366`). Registry growth is measured in P3-PERF, never assumed. |
| **AD-6** | **RESOLVED.** The 12 period-level types plus EQH/EQL move to **P3-CONTEXT**, outside the P3 CORE parity gate. `calc_bars_count` stays 1800. | Safe because all 14 are lifecycle-**ineligible** (`poi/enums.py:122-139`) and BTMM never forms setups from them (`btmm/analyzer.py:409-412`). Their semantics are still pinned by `test_p3_period_level_contracts.py`, so the deferral is scheduling rather than an unexamined gap. **`P3 CORE CLOSED` will NOT mean `ALL 32 TYPES CLOSED`.** |
| **C-3** | **RESOLVED.** Closed-bar-only semantics are mandatory: a forming realtime candle must never mutate confirmed P3 state. | Pine gates all P3 state on `barstate.isconfirmed`, exactly as P1/P2 already do. |
| **E-2** | **RESOLVED.** Start semantically exact; optimise only on measured evidence and only with proven output equivalence. | No speculative shortcuts. |

## 33. P3 CORE vs P3 CONTEXT — the frozen split

`P3_CORE_TYPE_SET` — **18 types**, exactly `LIFECYCLE_ELIGIBLE_POI_TYPES`
(`poi/enums.py:99-120`):

    BUY_ORDER_BLOCK, SELL_ORDER_BLOCK,
    BUY_FAIR_VALUE_GAP, SELL_FAIR_VALUE_GAP,
    BUY_TO_SELL_CANDLE, SELL_TO_BUY_CANDLE,
    BASE_RALLY, BASE_DROP,
    BULLISH_PRESSURE_WICK, BEARISH_PRESSURE_WICK,
    BULLISH_ENGULFING, BEARISH_ENGULFING,
    HAMMER, SHOOTING_STAR,
    MORNING_STAR, EVENING_STAR,
    SUPPORT_ZONE, RESISTANCE_ZONE

`P3_CONTEXT_TYPE_SET` — **14 types**, exactly
`NOT_APPLICABLE_LIFECYCLE_POI_TYPES` (`poi/enums.py:122-139`):

    EQUAL_HIGHS_LIQUIDITY, EQUAL_LOWS_LIQUIDITY,
    CURRENT_DAY_HIGH, CURRENT_DAY_LOW,
    CURRENT_WEEK_HIGH, CURRENT_WEEK_LOW,
    CURRENT_MONTH_HIGH, CURRENT_MONTH_LOW,
    PREVIOUS_DAY_HIGH, PREVIOUS_DAY_LOW,
    PREVIOUS_WEEK_HIGH, PREVIOUS_WEEK_LOW,
    PREVIOUS_MONTH_HIGH, PREVIOUS_MONTH_LOW

Set algebra verified against source: `|CORE| = 18`, `|CONTEXT| = 14`,
`CORE union CONTEXT` = all 32 `PoiType` members, `CORE intersect CONTEXT` is
empty. The split IS the lifecycle-eligibility partition, so it is derived from
source rather than chosen. Per-type matrix:
`artifacts/p3_arch/poi_type_matrix.csv`; dependency matrix:
`artifacts/p3_arch/poi_dependency_matrix.csv`.

**P4 safety check for AD-6.** BTMM's eligible set defaults to exactly the 18
CORE types and may only shrink (`btmm/configuration.py:16,102-106`), so no
CONTEXT type can ever produce a BTMM setup. The single coupling is that ANY
POI — including a CONTEXT one — satisfies `analyze_btmm`'s non-empty guard
(`btmm/analyzer.py:355`); that guard is a liveness check, not a semantic
dependency, so deferring CONTEXT does not block P4.

## 34. Parity ordering contract (AD-1, frozen)

POIs are sorted by this **semantic** tuple before hashing. Every component is
computable identically in both engines and no UUID appears:

1. `availability_time_utc` (epoch milliseconds)
2. `poi_type` integer code (the frozen Pine vocabulary)
3. `direction` code (BULLISH = 1, BEARISH = -1)
4. `zone_bottom` in integer ticks (`round(price / mintick)`)
5. `zone_top` in integer ticks
6. `candidate_event_time_utc` (epoch milliseconds) — first source candle
7. `confirmation_time_utc` (epoch milliseconds)

Component 6 is load-bearing: the bases detector emits nested `(start, length)`
candidates (`bases.py:44-48`), so two base candidates can share type, bounds
and availability while differing in where the base began.
`candidate_event_time` separates them without appealing to identity.

**Totality is not assumed.** The parity harness must assert zero collisions
across the entire synthetic suite and on real data before the digest contract
is frozen. If a collision ever appears, the resolution is another
*authoritative identity component* — never an array index.

## 35. Contract-hardening evidence (P3-I0)

All six BLOCKER-B items from Section 25 are now permanently pinned, each at
below / exact / above the production threshold:

| item | subject | tests |
|---|---|---|
| B-1 | Order Block ratio 2.0 and 3.0 boundaries, plus the strict `close > origin.high` | 5 |
| B-2 | FVG strict `>` (an exact touch is not a gap), a one-tick gap qualifying, the unconstrained middle candle, and the bearish mirror | 4 |
| B-3 | **Bases real-ATR branch** (previously zero coverage): a warm 20-bar prefix makes ATR-14 real, proven by a pass/fail pair differing only in base height against that ATR; plus the fallback branch and the `atr_values[end-1]` anchor | 3 |
| B-4 | STRONG tier boundaries for engulfing, three-candle stars, single-candle reversals and reversal candles | 4 |
| B-5 | Pressure wick `uw == 0` dominance escape, the dominance boundary, the 20-bar baseline horizon, and the first-candle self-baseline | 4 |
| B-6 | Period levels: December-to-January year rollover, previous-period availability, the equal-extreme first-wins tie rule with its strict-improvement mirror, and gap-week grouping | 6 |

Plus 4 AD-3 source-as-is guards, 2 AD-2 dead-state guards, and 17 lifecycle
boundary contracts: inclusive wick interaction, maximal tap runs, strict
close-only breach at the exact tolerance boundary in both directions, the
reclaim boundary and its 3-bar window, false invalidation via a FAST leg, the
non-terminality of false invalidation, genuine invalidation requiring a full
window with a sustained bar 3, terminal freeze, absence of expiry, taps
surviving terminality, the zero-height-zone `bound_b := bound_a` fallback, and
the two-tick tolerance floor.

**50 tests, all green, zero production changes.** No P3-I0 CONTRACT
DISCREPANCY was found: every detector and lifecycle claim in Sections 5-16 was
re-verified first-hand against source during hardening, and each one held.

One pre-existing repository defect was repaired to unblock the quality gate.
`tests/parity_support/__init__.py` had been truncated mid-docstring since
commit `9c2abf3`, leaving the package unimportable and causing `mypy` to abort
before checking any file. The docstring is now closed. Nothing semantic
depended on it — parity modules are loaded by file path — and `mypy src` is
clean across 138 source files.
