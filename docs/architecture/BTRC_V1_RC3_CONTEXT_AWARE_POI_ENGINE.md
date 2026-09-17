# BTRC V1 — RC3 context-aware POI engine

Branch `rc3-ob-origin-revision`. Commits `d6118dd` (confirmed S/R zones immutable),
`3ec6820` (qualification), then performance + docs.

## Pipeline

```
RAW PATTERN CANDIDATE        frozen detectors (poi/*.py), auditable
  -> PATTERN VALIDATION      detector geometry + frozen standards
  -> TYPE-SPECIFIC QUALITY   FVG: gap >= 0.35 x ATR-14 (departure)   [FROZEN, decision C]
  -> SAME-ORIGIN ARBITRATION pattern primary over its own FVG;
                             HAMMER / SHOOTING STAR over same-candle
                             pressure wick                          [decision B]
  -> STRUCTURAL CONTEXT GATE P2 direction at availability; reversal
                             rescue at the confirming break          [decision A]
  -> STRUCTURE (OB)          leg origin from P2 breaks (poi/leg_origin)
  -> QUALIFIED MAPPED POI    immutable once available (OB, S/R, context locks)
  -> LIFECYCLE -> P5 (source TF) -> P8
```

Reason codes: `poi/qualification.py` `MAPPED`, `QUALITY_REJECT`,
`SAME_ORIGIN_SUPPRESSED`; `poi/leg_origin.py` `ContextReason`
`MAPPED_TREND_ALIGNED`, `MAPPED_REVERSAL_CONTEXT`,
`CONTEXT_REJECT_COUNTER_TREND`, `CONTEXT_REJECT_NEUTRAL`.

## Structural context gate (author decision A, 2026-09-17)

Gated types (`CONTEXT_GATED_TYPES`): BUY / SELL FVG, B2S / S2B, BASE RALLY /
DROP, BULLISH / BEARISH PRESSURE WICK, BULLISH / BEARISH ENGULFING, HAMMER,
SHOOTING STAR, MORNING / EVENING STAR. Not gated, because their own contract is
already structural: ORDER BLOCK (exists only as the leg origin of a confirmed P2
break), SUPPORT / RESISTANCE ZONE (confirmed swing levels), period and reference
levels (calendar / swing references, never candle patterns).

Only frozen P2 primitives are read — no second structure engine, no numeric
score, no Fibonacci / trendline / S/R / liquidity gate:

* **Direction timeline** — UNDETERMINED until the first HH+HL (BULLISH) or
  LH+LL (BEARISH) relationship becomes available, then `direction_after` of
  every BOS / CHOCH at its availability (`_direction_timeline`).
* **Aligned** — the direction at the candidate's availability equals its
  direction → `MAPPED_TREND_ALIGNED`, available at its own availability.
* **Neutral** — UNDETERMINED at availability → `CONTEXT_REJECT_NEUTRAL`
  (never mapped later).
* **Counter-trend** — opposite direction → `CONTEXT_REJECT_COUNTER_TREND`
  unless a later break in the candidate's direction confirms a leg whose origin
  swing (the same extreme opposite swing the ORDER BLOCK rule uses) starts at or
  before the candidate's first candle, and the candidate was available by that
  break → `MAPPED_REVERSAL_CONTEXT`, available at
  max(candidate availability, origin confirmation, break availability).
* **Historical impulse POIs** are kept: a mapped POI is locked on first
  appearance (prefix union, identical to the incremental frontier) and never
  removed when later structure changes.
* Fibonacci buckets (<50, 50–61.8, 61.8–79, >79, outside), trendline, S/R and
  liquidity remain audit metadata (`tests/parity_support/rc3_poi_context_audit.py`).

Pine (USER v30 `a2467260…`, PARITY v13 `84d3f7e7…`): `f_poiEmit` records the
arbitration keys first, then maps types 3–16 only when `p2Direction == direction`;
a counter-trend record waits in `ctPending`; `f_poiGateOrderBlocks` rescues it on
a break confirmed on this bar (same origin search as the ORDER BLOCK, before the
OB of that break); neutral records drop; pending records older than the window
are pruned like `obPending`.

Trace per candidate (`QualificationDecision`): candidate (type, direction, source
candles, availability, zone), reason, gap/ATR ratio, primary type. Context fields
(leg_id, leg type, role, retracement bucket, S/R / equal-level / trendline
confluence) come from `tests/parity_support/rc3_poi_context_audit.py`.

## Correctness

* No lookahead: the FVG gate reads the departure candle's ATR (final before the
  third candle closes); arbiters complete at the departure close. Prefix test:
  mapping decided at availability never changes when bars are appended.
* Immutability: leg-origin ORDER BLOCKs and SUPPORT / RESISTANCE ZONEs are locked
  on first appearance; batch reproduces the prefix union exactly.
* Incremental kernel == batch at every tested prefix (leg origin, S/R lock,
  qualification fixtures, frontier differential tests).
* Determinism: 120-bar authority digests identical across three runs
  (P3 `2cba21fe…`, P5 `793d1668…`, P8 `8011536a…`).
* Daily continuity: unchanged daily-authority harness (state continuous across
  trading days; qualification keeps no per-day state).

## Semantic delta vs `d6118dd` (daily authority, M15 host from 2026-08-10)

| window | P3 rows | distinct POIs | P5 changed common rows | permission changes | P8 events |
|---|---|---|---|---|---|
| 120 bars | 16 740 -> 13 205 (-3 535 FVG) | 363 -> 274 | 0 | 0 | 862 -> 553 |
| 300 bars | 45 085 -> 35 355 (-9 730 FVG) | 702 -> 513 | 2 (S/R BTMM state) | 0 | 2 445 -> 1 545 |

Changed P3 rows: `effective_timeframe` of FVGs whose stronger-timeframe parent FVG
is no longer mapped (906 + 2); S/R availability back to the zone's own
availability (17, frozen backfill contract). No other field changes.

## Performance

Profile (60-bar authority, cProfile): no qualification or leg-origin function
in the top 25; the hot path is per-bar `finalize` materialization
(`_combine_poi_replay_states`, pydantic validation, `_validate_uuidv7` 2.66 M calls).

Optimization: `_validate_uuidv7` accepts a valid UUIDv7 from its integer bits
(identical to the `.version` / `.variant` checks; invalid values take the
original path). Differential: 300 002 UUIDs, 0 accept/error mismatches;
validator 2.1x faster. 120-bar authority replay 53.4 s -> 50.5 s (-5.4 %), all
three period digests identical.

Benchmarks (same window): 120 bars 50.5 s (0.42 s/bar); 300 bars 267.6 s
(0.89 s/bar, measured under load). Remaining hot path: per-bar finalize
materialization (pydantic revalidation of every observation).

## Pine

USER DEV v29 (`20b79415…`), PARITY DEV v11 (`9f9d74ef…`): `C_POI_FVG_MIN_GAP_ATR`,
`poiOriginKey` map filled by `f_poiEmit` for pattern types 7-16, FVG emitted only
if gap quality holds and the departure key is absent. Both compile. Live
FX:XAUUSD: M15 weak FVG absent / valid FVG present; H1 pressure wick drawn
without its same-origin FVG; M1..W1 ready, 0 unannotated boxes.

## PRE-CONTEXT-GATE aligned parity (qualified engine at `be9bae1`; superseded by the context gate, kept as evidence)

Fresh same-session capture 2026-09-17 (PARITY DEV v11, FX:XAUUSD M15 host,
`artifacts/rc3_qual_aligned/pine_m15_run3.csv` sha256 `875f694d…`; RUNMETA +
OHLC checksums verified for all six windows), Level-A replay over 500 host bars
(2026-08-20 22:00 onward), `rc3_aligned_compare`:

| stage | compared | Python-only | Pine-only | mismatches |
|---|---|---|---|---|
| P3 | 149 POIs | 0 | 0 | 0 |
| P5 | 1 041 rows on 300 bars | 0 | 0 | 6 — all `poiStatus` on the POI's own first-touch/terminal bar (Pine wire reports the pre-advance breach status; scores, permission and signal lifecycle equal) |
| P8 | 656 events | 0 | 0 | 0 payload, 0 ordering |

Before qualification (capture run2, same comparator) the S/R zone locks were
also verified: P3 0 mismatches after the comparator's `-99` sentinel fix. The
remaining P5 class is the single open wire-level item.

### After the PARITY P5 wire fix (PARITY DEV v12, `ae2ebc4`)

The remaining P5 class was the capture logging Pine's committed-only
`poiStatus`; Python reports the lifecycle status including the pending breach
window. P5C / P5EVAL now log `poiReported`. Fresh same-session capture run4
(`artifacts/rc3_qual_aligned_v12/pine_m15_run4.csv` sha256 `5dfe2d8f…`, host
2026-08-20 22:30 onward, RUNMETA + checksums verified), Level-A 500 bars:

| stage | compared | mismatches |
|---|---|---|
| P3 | 150 POIs | **0** |
| P5 | 1 049 rows on 300 bars (990 higher-TF-context, 59 host-only) | **0** |
| P8 | 657 events | **0** (0 missing, 0 extra, 0 payload, 0 ordering) |

Interim evidence on a 500-bar window; not the final authority.
