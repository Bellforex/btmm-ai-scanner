# BTRC V1 — RC3 context-aware POI engine

Branch `rc3-ob-origin-revision`. Commits `d6118dd` (confirmed S/R zones immutable),
`3ec6820` (qualification), then performance + docs.

## Pipeline

```
RAW PATTERN CANDIDATE        frozen detectors (poi/*.py), auditable
  -> PATTERN VALIDATION      detector geometry + frozen standards
  -> TYPE-SPECIFIC QUALITY   FVG: gap >= 0.35 x ATR-14 (departure)        [implemented]
  -> SAME-ORIGIN ARBITRATION pattern primary over its own FVG            [implemented]
  -> STRUCTURE (OB)          leg origin from P2 breaks (poi/leg_origin)  [implemented]
  -> MARKET CONTEXT          leg role / retracement / confluence         [measured, not gated]
  -> QUALIFIED MAPPED POI    immutable once available (OB, S/R locks)    [implemented]
  -> LIFECYCLE -> P5 (source TF) -> P8
```

Reason codes (`poi/qualification.py`): `MAPPED`, `QUALITY_REJECT`,
`SAME_ORIGIN_SUPPRESSED`. `CONTEXT_REJECT` is reserved: no authority exists for a
context gate (`BTRC_V1_RC3_MARKET_CONTEXT_AUDIT.md`).

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

## Interim aligned parity (qualified engine; NOT final authority)

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
