# BTRC V1 — RC3 POI classification overlap audit (Phases 1, 9–12)

Evidence: real FXCM XAUUSD same-session exports (W1/D1/H4/H1/M15/M5,
`artifacts/rc3_aligned/ohlc_*.csv`, window proven by RUNMETA). Candles touching
the sealed out-of-sample range are removed and each series is split around it;
nothing there is detected or reported. Tools:
`tests/parity_support/rc3_poi_overlap_audit.py`,
`tests/parity_support/rc3_fvg_pipeline_audit.py`
(output `artifacts/rc3_poi_quality/`).

## 1. Detector overlap classes

Pairs are formed only within the same timeframe and direction.

- **A — SAME SEMANTIC FORMATION:** identical source candles and identical
  zone.
- **B — DISTINCT POIs WITH OVERLAPPING GEOMETRY:** different source candles,
  intersecting zones.
- **C — AMBIGUOUS / SHARED SOURCE:** at least one shared candle, but a
  different span or zone.

### Class A (same formation described twice)

| timeframe | SELL OB = BEAR ENGULF | BUY OB = BULL ENGULF | HAMMER = BULL PRESSURE WICK | SHOOTING STAR = BEAR PRESSURE WICK |
|---|---|---|---|---|
| W1 | 39 | 33 | 15 | 14 |
| D1 | 45 | 41 | 9 | 13 |
| H4 | 61 | 63 | 11 | 7 |
| H1 | 39 | 34 | 6 | 13 |
| M15 | 41 | 32 | 13 | 16 |
| M5 | 46 | 36 | 22 | 20 |

**Every order block is an identical formation to an engulfing** — W1 72/72,
D1 86/86, H4 124/124, H1 73/73, M15 73/73, M5 82/82. This is structural, not
statistical: `detect_order_blocks` applies exactly `detect_engulfing`'s
conditions on the same two candles plus one extra condition (displacement
close beyond the origin extreme) and emits the same zone
(`BTRC_V1_RC3_ORDER_BLOCK_STRUCTURAL_CONTRACT.md`). That is the source of every
"BUY ORDER BLOCK + BULLISH ENGULFING" / "SELL ORDER BLOCK + BEARISH ENGULFING"
label: P7-Z groups exact-geometry twins into one box and lists both names.

Engulfings that are *not* also order blocks are rare: H4 6 bullish / 6 bearish,
M15 6 / 7, D1 5 / 7.

Hammer / Shooting Star with a Pressure Wick on the same candle is permitted
coexistence by frozen decision §35L ("may coexist with a Pressure Wick label on
the same candle without precedence").

### Class C (shared candle, different geometry)

Dominated by FVG pairs (an FVG's first or third candle is also an order block,
engulfing, wick or star candle) and Base Rally/Drop sharing a departure candle
with an order block or engulfing. These are **distinct POIs** by geometry and
definition. They must not be merged, and the audit gives no reason to.

### Class B (distinct sources, overlapping zones)

Common and expected (for example a fresh FVG inside an older order block). Not
a duplication problem.

## 2. What classification cleanup would and would not touch

Only class A OB/engulfing pairs are the "same formation, two identities" case
the author described. Class B and C must stay separate POIs. Class A
wick/hammer pairs are frozen coexistence and are unchanged unless the author
decides otherwise.

The requested terminal-location rule is **not implementable as a reuse of an
existing standard**:

- The register states explicitly that OB and engulfing have no automated
  "origin vs middle of move" gate, and that neither is ever suppressed
  because the other matched (§35K, §35L).
- The only frozen structure primitive that can express "end of a move" is the
  confirmed swing (`domain/swings.py`). A swing pivot on the pattern can be
  confirmed at the earliest +2 bars (local) or +3 bars (meaningful) after the
  displacement close, and a pivot can still be superseded later.
- Measured effect of "origin or displacement candle is a confirmed opposite
  swing pivot":

  | timeframe | OBs keeping OB | share |
  |---|---|---|
  | H4 | 31 / 124 | 25% |
  | H1 | 30 / 73 | 41% |
  | M15 | 29 / 73 | 40% |
  | D1 | 26 / 86 | 30% |

  The survivors would be classifiable only 2–3 bars after today's
  availability.

This needs the author decisions listed in the structural contract document
before any code changes.

## 3. FVG pipeline (Phase 9), M15 executed window

Window: 2026-08-19 19:15 → 2026-09-16 09:45 UTC (1 799 bars), final close
4338.12.

| stage | result |
|---|---|
| A detection (Python detector over the exact window) | 390 (188 BUY, 202 SELL) |
| B registration (Pine P3 registry) | 390; identity diff Python-only **0**, Pine-only **0** |
| C quality-gate rejection | none exists for FVG in code (see quality-gate report D1) |
| C terminal at run end | **380 mitigated**, 0 invalidated |
| C fresh at run end | 10 |
| D lost in grouping | **0** (10 fresh FVGs → 10 groups) |
| E omitted by display cap | 5 groups, ranks 9, 13, 14, 15, 18 by distance (69.7 – 342.2 points away, 145–536 h old) |
| E selected | 5 of 8 visual slots are FVG groups; nearest FVG group ranks 2nd |
| F/G drawing / geometry | **superseded — see §4: Pine drew no FVG at all** (the model selection was right, the Pine sweep was not); geometry locked by fixtures |

**Conclusion:** FVGs are detected completely and exactly. Grouping does not
lose them and selection does not starve them. An FVG "missing" from the
chart is, in 380 of 390 cases, **already mitigated**: RC3's first-reaction
rule ends freshness on the first touch, and live mode shows fresh zones only.
The remaining gap is the capacity cap on far-away zones (input
`Max visible zone groups`, default 8, max 30). **No display-selection change is
warranted by this evidence**; changing the cap default is a presentation choice
for the author.

Permanent real-data fixtures: `tests/fixtures/rc3_fvg_reference_fxcm_m15.json`
(large BUY/SELL, minimal 0.01 / 0.04 gaps, an overlapping pair, a mitigated
and a fresh example), locked by `tests/unit/test_rc3_fvg_reference_fixtures.py`
together with the FVG mutation tests: 2-candle gap, wrong orientation, wrong
boundaries, source/availability collapse, and a fresh FVG dropped before
selection.

## 4. Live FVG draw audit (acceptance gate item 8), FX:XAUUSD M15, 2026-09-16

§3 row F/G was wrong. It compared live boxes with the *Python model's*
selection on a chart where the model and Pine happened to agree on non-FVG
boxes; nobody checked that a single FVG box existed. None did.

Evidence chain (PARITY DEV v4 registry capture, then temporary log-only
probes in a throw-away copy of USER, removed from the chart afterwards):

| stage | result |
|---|---|
| registered FVGs in the executed window | 394 |
| TERMINAL (mitigated / invalidated) | 387 |
| fresh at run end | **7**, all SELL FVG (tops 4683.99, 4551.27, 4534.18, 4501.58, 4408.87, 4387.09, 4342.53) |
| in USER `p7PoiIdx` / `p7zFreshIdx` with type 4, direction −1 | 7 / 7 |
| groups emitted by the per-direction FVG sort+sweep | **0** |
| GROUPED (lost by merging) | 0 |
| DISPLAY_CAP (cap 30, 6 non-FVG groups) | 0 |
| **DRAW_FAILURE** | **7** |
| DETECTOR_MISS / QUALITY_REJECT | 0 / 0 |

**Failure stage:** the P7-Z FVG sweep. A probe inside the loop showed
`cN := 1` taking effect within one `for k` pass and reading back as `0` on
the next, so the "flush a finished cluster" branch (`cN > 0`) never ran. The
scalar cluster state did not survive loop iterations in TradingView's
runtime, although the same code is correct as written and correct in the
Python model.

**Fix (presentation only, commit ec83d1f):** cluster state lives in arrays
(`cF`, `cI`, `cT`), whose element writes persist. The detector, P3 lifecycle,
selection order, collision ownership and every non-FVG path are unchanged.
Source lock: `test_fvg_sweep_state_is_array_held_not_loop_scalars`.

**Live verification (same chart, same bars, profiler off):** fixed build 13
boxes vs v17 6 boxes. All 6 v17 geometries/colours/extend/alignment/size are
identical; the 7 added boxes are exactly the 7 fresh SELL FVGs, red. One
intended text change follows the existing owner rule: FVG 4324–4342.53
touches the SELL OB 4342.53–4364.07 at one price, is nearer to price, and
therefore owns the text of that collision group (the OB box stays, with
empty text). USER DEV saved as **v19** (sha256 `ee6d8df3…`); after the save
its 14 boxes equal the verified diagnostic build box for box (a new bar had
closed in between).

**Not changed, flagged for the author:** the identical sweep is in the
frozen `btmm_poi_btrc_scanner_rc2.pine` and
`btmm_poi_btrc_scanner_rc1_poi_fix_dev.pine`, so RC1-FIX/RC2 also never drew
an FVG zone. RC2 is a promoted release; it is left untouched.

H4 is not audited to the same depth: its executable 1 800-bar window reaches
the sealed out-of-sample range, which may not be replayed or inspected.

## 5. Author decisions applied for the RC3 event/release build (2026-09-16)

| # | decision | implementation |
|---|---|---|
| 1 | OB / engulfing: no semantic change tonight; primary DISPLAY name only | `dcc888d`. In a P7-Z exact-geometry group (key = top, bottom, availability, direction — formation identity for the two-candle OB and engulfing detectors, which share both source candles, zone and availability) the engulfing name is not appended when the group already carries ORDER BLOCK. Both registry records stay. Different-origin OB + engulfing, OB + FVG, OB + S/R and other patterns keep their names. Locked by `test_rc3_primary_display_label.py`; everything outside the P7-Z block hash-pinned unchanged. Live v18 vs v21 at cap 30, all 7 hosts: composite labels 12 → 0, every box's geometry/colour/extend/alignment identical. |
| 2 | RC1 / RC2 FVG draw bug: do not modify; document | RC1 `143c0f88…`, RC2 `381f2fc2…` unchanged and hash-tested. KNOWN HISTORICAL DISPLAY DEFECT recorded in §4 and the event README; RC3 carries the fix (`ec83d1f`). |
| 3 | canonical P3 identity keeps the source timeframe | Python never mutates `source_timeframe`; `resolve_merges` sets `effective_timeframe`, now treated as derived `higher_tf_context` by the aligned comparator (`8e5804d`). P3 field divergences on the M15 capture 196 → 2. |
| 4 | P8 native order (poiIdx, event priority) is authoritative | Comparator checks Pine's native order and associates Python events by canonical identity; incidental Level-A numbering no longer compared. Ordering-divergent bars 37 → 0; native-order violations 0. |
| 5 | FVG §35J: no semantic change tonight | Not touched. Any future change must first show the frozen §35J text, current Python and Pine behaviour, tests and the expected delta. |
| 6 | accept `size.auto` box text | Kept. Text is box-native, centred and auto-sized on every host (verified by box properties on all 7 hosts; containment verified in the zoom test). |

PARITY DEV has no P7-Z drawing code (inputs only), so the FVG sweep fix had
nothing to mirror there; PARITY v4 (`d49f0624…`) was recompiled on the chart
with no token or runtime error on all 7 hosts, and its P6 block is
byte-identical to RC2's (now also a test).

**Remaining P3/P5/P8 parity blocker (author decision needed, not tooling):**
`btrc/t5_engine.py` evaluates each POI on `poi.effective_timeframe`
(momentum / breakout / pullback / volatility of the higher timeframe) while
single-timeframe Pine evaluates on the host. All 10 961 P5 field and 901 P8
differences on the M15 capture are in that class; host-only POIs are exact.
