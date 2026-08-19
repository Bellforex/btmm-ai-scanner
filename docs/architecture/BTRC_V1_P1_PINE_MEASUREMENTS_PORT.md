# BTRC-V1 — P1 Pine Measurements Port

Status: **P1 implemented on `pine-v1`.** First actual Pine implementation phase.
Source: [`tradingview/btmm_poi_btrc_scanner_v1.pine`](../../tradingview/btmm_poi_btrc_scanner_v1.pine).
Pine **v6**, `indicator(...)` (never `strategy`). Current chart feed / timeframe
only. **No** BOS/CHOCH, POI, BTMM, BTRC, multi-timeframe, canonical FXCM, entries,
SL/TP, risk, or orders. **Compiler status: `NOT_COMPILED_IN_TRADINGVIEW`** — the
author performs the manual compile/visual gate (§ "Manual validation") before P2.

The Python scanner is the **semantic source of truth**. Every ported detector is
cited below to exact Python functions. Data structures are adapted; analytical
meaning is preserved.

## Python sources audited (source of truth)
| Concern | Python file · function |
|---|---|
| Candle metrics, `range_speed_ratio`, `median_total_range` | `measurements/candle_metrics.py` |
| Wilder ATR | `measurements/atr.py` (`_true_range`, `compute_atr_series`, `advance_incremental_atr`) |
| Leg measurement | `measurements/legs.py` (`measure_leg`) |
| Meaningful/confirmed swings | `domain/swings.py` (`detect_confirmed_swings` + `_find_single_candle_pivots`, `_merge_adjacent_plateaus`, `_supersede_same_direction_runs`) |
| Displacement | `domain/displacement.py` (`detect_displacement_observations`, `_classify`) |
| Equal highs/lows | `domain/equal_levels.py` (`detect_equal_level_clusters`, `_sweep_one_type`) |
| Support/resistance | `domain/support_resistance.py` (`detect_support_resistance_zones`, `_evaluate_reaction`) |
| Trendlines | `domain/trendlines.py` (`detect_trendlines`) |
| Parameters | `domain/configuration.py` (`MarketMeasurementConfiguration` defaults) |
| Availability semantics | `contracts/normalized_candle.py`; `historical_backtest/csv_parser.py` (`_derive_event_and_availability`) |

## Closed-bar / non-repaint implementation
All confirmed analytical state advances **only** inside `if barstate.isconfirmed`.
On historical bars every bar is confirmed once; on realtime the block fires only at
bar close, so the forming candle never creates or mutates a confirmed swing,
equal-level, S/R, displacement, or trendline. No `[-n]` future indexing, no
`request.security`, no `lookahead`. The realtime bar is never drawn as confirmed
state (optional preview visuals are out of scope for P1).

## Python availability semantics → Pine
Python: `availability_time_utc = event_time_utc + timeframe_duration` for intraday
(`csv_parser._derive_event_and_availability`, byte-cited lines 148-149), i.e. a
candle is analytically available at its **close**. The `NormalizedCandle` contract
enforces `availability_time_utc > event_time_utc`. Pine mapping:
- **bar open time** → `time` (stored as `wOpenT`; the swing *anchor*), and
- **availability / confirmation time** → `time_close` (stored as `wAvailT`), used
  for `local_confirmation_time`, `meaningful_confirmation_time`, cluster and zone
  confirmation times.

Parity records prefer **timestamps** over `bar_index`. `bar_index` is never used as
identity; window indices are used only internally within a single recompute.

## Internal Pine types
`SwingRec, EqualLevelRec, SRRec, TrendlineRec` (user-defined types) carry semantic
content only — price, direction/type, anchor/confirmation **times**, tolerances,
and already-defined strengths. No UUIDs, no content fingerprints, no provenance.
The Python `_Pivot` NamedTuple is represented as parallel arrays inside the swing
pipeline (a mechanical adaptation).

## Bounded state
Python retains full history; Pine retains a rolling **`lookbackWindow`** (input,
default 300, ENGINEERING-PROVISIONAL — a Pine practical retention bound, not a
strategy parameter). The window holds confirmed OHLC, open/availability times, and
the per-candle ATR. Pruning removes only the oldest candles; it does not change the
interpretation of records still inside the window. **Disclosed limitation:** a swing
whose meaningful-reversal confirmation would require looking back further than the
window is not reproduced. ATR is carried **incrementally** (Wilder IIR state) from
the chart's first bar, so ATR values are exact regardless of the window edge (they
are *not* re-seeded from the window).

## Algorithm ports (meaning preserved)
- **ATR** — `_true_range` (uses previous close; first bar = high−low) + Wilder
  recurrence with SMA seed at the `period`-th sample (`na` before). Implemented as
  incremental `var` state mirroring `advance_incremental_atr`.
- **Swings** — single-candle pivots over a ±`_WINDOW_RADIUS`(=2) window with
  `pivot_tie_tolerance = 0.02·ATR`; simultaneous high+low ⇒ emit neither (register
  §33I); plateau merge of adjacent same-type pivots within tolerance;
  same-direction-run supersede (extreme survives); then alternation + meaningful
  reversal (`0.50·ATR` excursion) with `local_confirmation_index = pivot_end + 2`.
  Confirmation and local times use availability (close) times.
- **Displacement** — direction by `close ≥ open`; classification from
  `range_speed_ratio = total_range / median_total_range(preceding 20)` vs bands
  FAST `1.50`, VERY_FAST `2.00`; zero-range ⇒ ratio 0 / NORMAL.
- **Legs** — `measure_leg`: net directional distance / (bars·median ATR),
  directional efficiency, directional candle share → SLOW/FAST/STRONG_FAST.
- **Equal levels** — per type, ordered by meaningful-confirmation time; grow a
  cluster while `spread ≤ 0.10·median(ATR)`; emit clusters with ≥2 members.
- **Support/resistance** — origin zone (`0.10·ATR` depth) confirmed by the standard
  reaction gate (`_evaluate_reaction`: close clears zone, MFE ≥ `0.75·ATR`, zone
  clearance ≥ `1.00·height`, leg efficiency ≥ `0.50`, leg share ≥ `0.60`); touches
  require an **opposite swing between** and their own passing reaction.
- **Trendlines** — same-type anchor pairs, spacing ≥ 5 bars, monotonic progression
  beyond tie tolerance, normalized slope in `[0.02, 0.35]`, close-price integrity
  within `0.20·ATR` pierce, and one qualifying forward touch.

## Parity keys (semantic, UUID-independent)
| Record | Key |
|---|---|
| Swing | `swingType + pivotEndTime + price + meaningfulConfTime` |
| Displacement | `barOpenTime + sign(direction) + classificationCode` |
| Equal level | `clusterType + representativePrice + firstTime + confirmationTime` |
| S/R | `zoneType + zoneTop + zoneBottom + confirmationTime` |
| Trendline | `orientation + anchor1(time,price) + anchor2(time,price) + confirmationTime` |

## Debug / parity interface
`P1 Debug Mode` (off by default). Machine-readable **Data Window** plots expose the
latest confirmed values: `P1_swing_high_price, P1_swing_low_price, P1_disp_code,
P1_disp_ratio, P1_equal_high, P1_equal_low, P1_sr_top, P1_sr_bottom,
P1_tl_norm_slope`. A compact latest-state table renders on the last bar. Bounded
visuals (swing labels, equal-level lines, S/R boxes, trendline lines) are capped by
`maxDrawPerFamily` and per-family toggles, redrawn only when the swing set changes.

## Pine adaptations (mechanical; meaning unchanged)
- Python `Decimal` → Pine `float` (precision adaptation; see limitations).
- Python UUID identity → semantic time/price keys.
- `dict`/NamedTuple → arrays / user-defined types.
- Full history → bounded rolling window.
- Equal-level `record_id` tiebreak → deterministic `(time, pivotEndTime, price)`
  order (ordering deterministic; cluster content unchanged).

## Non-repaint audit (per detector)
For every P1 detector: (A) the source event is a closed candle; (B) confirmation
requires the meaningful-reversal / reaction / touch evidence to already exist in
closed bars; (C) Pine publishes under `barstate.isconfirmed`; (D) historical and
realtime paths are identical (both gated on confirmed bars); (E) **cannot repaint**
confirmed state. Target met: **PRODUCTION CONFIRMED STATE = NON-REPAINTING.**

## Portability findings
| Feature | Result |
|---|---|
| Candle metrics | **PORTED_EXACT** (Decimal→float only) |
| ATR (Wilder, incremental) | **PORTED_EXACT** (Decimal→float only) |
| Displacement | **PORTED_EXACT** (Decimal→float only) |
| Meaningful swings (full pipeline) | **PORTED_WITH_ENGINEERING_ADAPTATION** (bounded window; parallel arrays) |
| Legs (`measure_leg`) | **PORTED_WITH_ENGINEERING_ADAPTATION** (Decimal→float; window-scoped) |
| Equal levels | **PORTED_WITH_ENGINEERING_ADAPTATION** (deterministic tiebreak; window) |
| Support/resistance | **PORTED_WITH_ENGINEERING_ADAPTATION** (window; recompute-on-change) |
| Trendlines | **PORTED_WITH_ENGINEERING_ADAPTATION** (window; debug-only render) |
| BOS/CHOCH, POI, BTMM, BTRC, multi-TF, execution | **DEFERRED** (later phases) |
| Python reference exporter (§23) | **DEFERRED** (optional; omitted to keep P1 focused and the Python suite untouched) |
| Blocked | **NONE** |

No Python semantic defect was discovered; no protected Python logic was modified.

## Known limitations (disclosed)
- `float` vs `Decimal`: Pine has no arbitrary-precision decimals; compare parity
  with a small numeric tolerance, not bit-exact equality.
- Bounded window: records requiring look-back beyond `lookbackWindow` are not
  reproduced. Choose a window comfortably larger than the longest confirmation
  distance you test.
- Performance: the swing pipeline recomputes over the window each confirmed bar
  (derived detectors recompute only on swing-set change). On long histories with a
  large window this may approach Pine's per-bar compute budget; reduce
  `lookbackWindow` or test over a limited bar range if TradingView reports a
  loop/time limit.
- Not yet compiled in TradingView (status above); the static guards in
  `tests/unit/test_pine_p1_source_guards.py` are repository safety checks only.

## Manual TradingView validation procedure (author, before P2)
1. Open TradingView → Pine Editor.
2. Create a new blank indicator; paste the exact contents of
   `tradingview/btmm_poi_btrc_scanner_v1.pine`.
3. Save. Resolve any compiler errors (report them verbatim for the one authorized
   correction cycle).
4. Add to chart. Use **`FXCM:XAUUSD`** for the first controlled review where
   available.
5. First timeframe: **M15** (enough confirmed swing/displacement events for
   inspection, good chart clarity, and no multi-timeframe dependency — appropriate
   for the current-chart-only P1).
6. Open Settings → enable **P1 Debug Mode** (and optionally S/R and trendline
   families).
7. Confirm: swing labels sit at the correct pivots and appear only after their
   confirmation bar (no repaint on realtime); the Data Window shows the `P1_*`
   values; the latest-state table renders.
8. Capture a screenshot / Data-Window values for the parity record.

This is development validation only — no customer publication.

## Not implemented in P1 (explicit)
Market structure (BOS/CHOCH/state) FALSE · POI FALSE · BTMM FALSE · BTRC FALSE ·
multi-timeframe FALSE · entries/SL/TP FALSE · live execution FALSE.
