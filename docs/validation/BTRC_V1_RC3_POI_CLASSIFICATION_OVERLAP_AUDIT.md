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
| F/G drawing / geometry | live boxes match selection; geometry locked by fixtures |

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
