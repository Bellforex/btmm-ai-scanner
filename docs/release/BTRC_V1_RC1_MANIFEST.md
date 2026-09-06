# BTRC V1 — RC1 Release Manifest

## Identity

| Field | Value |
|---|---|
| Release name | BTMM + POI + BTRC Scanner **[RC1]** |
| Source file | `tradingview/btmm_poi_btrc_scanner_rc1.pine` |
| Source SHA-256 | `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` |
| Source lines | 6391 |
| Built from | `tradingview/btmm_poi_btrc_scanner_p9_dev.pine` (closed P9 DEV), diff = exactly the `indicator()` title string, see [BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md](../architecture/BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md) §2 |
| Branch | `pine-p4-btmm` |
| Base closure SHAs | P9 reference/tests `00534a2`, P9 Pine instrumentation `f54e2fe`, P9 closure `cf9f874`; P7-Z closure `348d18b` |
| Pine version | `//@version=6` |

## Supported host timeframes (release-validated)

Live-verified in this session, zero runtime errors, on chart `6cu1b2O7`:

- **M5**
- **M15**
- **H1** (including reload-while-attached — the historically load-bearing
  RE10041 regression case)

M1/H4/D1/etc. are **not** advertised as release-supported host
timeframes; internal multi-timeframe (P6) requested contexts are a
separate, already-frozen concern (P6: `30/30` regression) and are
unaffected by this distinction.

## Validated provider / symbol

- Provider: **FXCM** (ticker `FX:XAUUSD`).
- Symbol: **XAUUSD** — the only symbol with real integrated capture
  parity evidence (P9) and real M5/M15/H1 runtime acceptance (P10).
- EURUSD/GBPUSD were **not** smoke-tested in this release cycle (the
  brief marked this optional and instructed not to delay closure for it
  — see closure doc §8). The Pine engine has no symbol-specific branching
  and is architecturally symbol-agnostic, but that is an engineering
  expectation, not release-validated evidence. Treat XAUUSD as the only
  release-validated symbol until a future session repeats the M15/M5/H1
  + capture-parity matrix on another symbol.

## Feature inventory (included in this release)

| Component | Status |
|---|---|
| P1 measurements | Included (closed) |
| P2 structure | Included (closed) |
| P3 POI core (18 lifecycle-eligible types) | Included (closed) |
| P4 BTMM | Included (closed) |
| P5 BTRC confluence | Included (closed) |
| P6 six-timeframe transport/core | Included (closed) |
| P7 summary panel + active-POI table | Included (closed) |
| P7-Z visible POI zones + labels | Included (closed), default ON, cap 12 |
| P8 five informational alert events | Included (closed); `alert()` calls active, technical Alert object creation platform-blocked (see operational notes) |

## Deferred / excluded (NOT part of this release)

- P3 Context (EQH/EQL + 12 calendar/period context types) — deferred,
  not reopened.
- P4 Reviewed-Evidence Transport — deferred, not reopened.
- Any entry/SL/TP logic, position sizing, risk-percent logic, broker
  execution — never implemented, out of scope for this entire project
  phase.
- Profitability claims of any kind.

## Resource inventory (verified identical to closed P9 DEV)

| Resource | Count |
|---|---|
| `plot`/`plotshape`/`plotchar` | 63 |
| `request.security` | 6 |
| `box.new` | 2 |
| `label.new` | 2 |
| `line.new` | 2 |
| `table.new` | 3 |

## Release-facing default configuration (frozen)

| Input | Default |
|---|---|
| Show POI zones | **ON** |
| Show POI labels | **ON** |
| Max visible zones | **12** |
| Max active POIs shown (table) | 8 |
| P1 Debug Mode | OFF |
| Show trendline debug | OFF |
| P8 event/prime debug log | OFF |
| P9 integrated trace log | OFF |
| Calculated bars | 1800 |
| Watch-only min (permission band) | 45 |
| High-confluence min (permission band) | 65 |

No release default was silently changed from its closed-phase value; all
of the above were already the defaults in P9 DEV, verified by direct
source inspection before RC1 was built (no stripping or refactor needed).

## Known limitations (disclosed in full in the closure doc §9)

1. Profitability not established.
2. P5 engineering parameters (weights, liquidity component, 45/65 bands)
   are engineering-provisional, not calibrated/proven optimal.
3. P3 Context deferred.
4. P4 Reviewed-Evidence Transport deferred.
5. TradingView technical Alert object creation is platform/plan-blocked
   on the current Basic account (0 technical alerts available).
6. Real P9 integrated parity capture exists only for M15 (real capture
   window: 103 bars, 9537 trace rows, 456 real events); M5/H1 have live
   runtime acceptance but no equivalent captured field-parity evidence.
7. Release acceptance is deepest on FXCM:XAUUSD; other symbols not
   release-validated this cycle.
8. Historical terminal POI-zone retention remains deferred (P7-Z's
   existing freeze-then-remove terminal behavior, unchanged).
9. P5's high-precision Decimal→float64 universal invariance is not
   claimed (a documented, accepted boundary case exists; see
   `BTRC_V1_P5_FLOAT64_BOUNDARY` in the P5 closure lineage).

## Frozen regression digests (all preserved unchanged through P10)

| Phase | Comparisons | H1 | H2 |
|---|---|---|---|
| P5 | 240850 / 240850 | 351473241 | 335238294 |
| P6 | 30 / 30 | — | — |
| P8 | 456 / 456 | 294719549 | 35571918 |
| P9 | 9473 records, 0 mismatches (9392 fully-verifiable) | 224768619 | 772693120 |

## Test suite

Full pytest suite: **3599 passed, 0 failed** at RC1 commit time (P10 added
offline/release tests only — see closure doc §7 for the P10-specific
delta and final count).

## Formal status

**TECHNICAL RELEASE CANDIDATE.** Not production-approved, not claimed
profitable, not autotrading-approved. See
[BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md](../architecture/BTRC_V1_P10_RELEASE_CANDIDATE_CLOSURE.md)
for the full closure record.
