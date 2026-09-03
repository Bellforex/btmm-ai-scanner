# BTRC-V1 — Complete P5 transport-dependency audit

Status: **AUDIT COMPLETE — no new semantic engine required**
Purpose: extend the P6 projection ONCE, not per component
Branch: `pine-p4-btmm`
Date: 2026-09-03

Author decision recorded: **Option A** — extend the existing P6 requested-context
projection additively. Option B (six additional stateful P5 request engines) was
declined.

---

## 1. Result

Every input the seven assessments, the three direct score components and the
aggregator need resolves to one of:

| category | meaning | count |
|---|---|---|
| **A** | already transported by P6 | 3 kinds |
| **B** | available locally, outside P6 | 5 kinds |
| **C** | derivable inside the EXISTING P6 request context | ~20 fields per TF |
| **D** | would require a new semantic engine | **none** |

`P6_TO_P5_TRANSPORT_COMPLETE` is therefore **achievable additively**. No second
swing detector, P2 walker, ATR engine or structure engine is needed, and the
request architecture (six contexts, envelope 1251, host 1800) does not change.

## 2. Category B — needs no P6 field at all

| consumer | input | why it is local |
|---|---|---|
| `assess_session` | `evaluation_time_utc` only | pure datetime; London/New York offsets. **Port risk, not a transport gap**: Python uses `ZoneInfo`, so DST transitions must match exactly. |
| `assess_volatility` | raw candles at the POI timeframe | P4 partitions by timeframe and the host is M15, so the POI timeframe IS the host timeframe. The host already holds those candles. |
| `assess_pullback` | `poi_lifecycle_transitions` | shared flat symbol-level collection, as already frozen |
| BTMM direct component | BTMM validity + direction | P4 output, local |
| POI direct component | `poi.strength_tier` | the POI object itself, local |
| liquidity placeholder | `btmm_valid` | local; `60 if btmm_valid else 40` |

## 3. Category C — the additive field list

Per requested timeframe. Every one is a bounded reduction of arrays the context
already maintains.

### 3a. For `assess_trend` (T1)

| field | type | source meaning | Pine derivation |
|---|---|---|---|
| `stateAvailT` | int ms | `current_state.availability_time_utc` | the walk's own availability time |
| `contStreak` | int | `_continuation_streak` | backward scan of transitions while type == continuation BOS for the current direction |
| `priorOppStreak` | int | `_prior_opposite_streak` | backward scan from the **second-to-last** transition while type == opposing BOS |
| `exhaustFlag` | int | `_exhaustion` | bullish: last SWING_HIGH price < previous SWING_HIGH price; bearish: mirrored on lows |
| `transWindowCount`, `trans1Type`…`trans4Type` | int | the last 4 transition types, oldest → newest | see the correction below |

`current_state.direction` and `analyzed_swing_count` are already transported
(`p2Dir`, `swingCount`).

**CORRECTION (found while freezing the contract).** The first draft transported
`altCount4`, the CHOCH count among the last four transitions. That is a
calibration verdict, not a raw value: `_alternation_count(transitions, window)`
takes its window from `TrendEngineConfiguration.range_window`, and the result is
then compared against `range_choch_count`. Shipping the count would freeze the
first constant inside P6 invisibly — raise `range_window` to 5 and every
timeframe silently keeps answering for 4.

So the transport carries the last four transition TYPES and P5 counts CHOCHs
itself. The same window also supplies `ordered_transitions[-2]` for breakout's
whipsaw test, so one bounded window replaces two separate fields.

**Capacity is not calibration.** The remaining window sizes (4 transitions, 3
displacements) are transport CAPACITY. The distinction matters because a baked
threshold is undetectable from outside, whereas a capacity that is too small is
detectable: P5 knows its own configured window and asserts it fits
(`test_p5_configuration_fits_the_transport_capacity`). Today the defaults fill
the capacity exactly, with zero slack.

### 3b. For `assess_regime` (T2) and `assess_momentum`

Both read the most recent displacements, and their windows coincide
(`recent_displacement_window = 3`, `momentum_window = 3`), so ONE window serves
both. The detector emits an observation for **every** candle, including
`NORMAL`, so the window is always full once history exists.

| field | type | source meaning |
|---|---|---|
| `dispCount` | int | `len(window)` — `min(3, n)` |
| `disp1Dir`, `disp2Dir`, `disp3Dir` | int | `DisplacementDirection` per observation, oldest → newest |
| `disp1Cls`, `disp2Cls`, `disp3Cls` | int | `DisplacementClassification` (0 NORMAL / 1 FAST / 2 VERY_FAST) |
| `disp1Ratio`, `disp2Ratio`, `disp3Ratio` | float | `range_speed_ratio` |
| `dispAvailT` | int ms | `window[-1].availability_time_utc` |

**The raw ratios are transported, not a threshold verdict.** T2 compares against
`expansion_speed_ratio` (1.50) and momentum against
`momentum_score_reference_ratio`, both of which are CONFIGURATION. Baking a
comparison into P6 would freeze a P5 calibration constant inside the MTF layer.

### 3c. For `assess_breakout`

`equal_level_clusters` is **not consumed** — the source declines to emit
`LIQUIDITY_SWEEP` in V1 and says so explicitly. No equal-level transport is
needed.

| field | type | source meaning |
|---|---|---|
| `lastTransAvailT` | int ms | `last_transition.availability_time_utc` |
| `dispClsAtTrans` | int | `_displacement_at(displacements, last_transition)` |

`p2LastTrans` (last transition type) is already transported, and the whipsaw
test's `ordered_transitions[-2]` now comes from `trans3Type` in the shared
transition window rather than from a field of its own.

`dispClsAtTrans` is **not** "the classification of the latest displacement". The
source matches every displacement whose `availability_time_utc` equals the
transition's, takes the MAX classification by NORMAL < FAST < VERY_FAST, and
returns `None` when nothing matches — so the field needs a distinct sentinel for
the no-match case.

### 3d. For `assess_pullback`

`_retracement_depth` needs exactly three swings.

| field | type | source meaning |
|---|---|---|
| `pbImpulsePrice` | float | bullish: last SWING_HIGH; bearish: last SWING_LOW |
| `pbOriginPrice` | float | last opposite-type swing at or before the impulse swing's `pivot_start_time_utc` |
| `pbPullbackPrice` | float | last opposite-type swing strictly after it |
| `pbValid` | int | 0 when any of the three is absent or the leg is <= 0 (source returns `None`) |

The depth ratio itself is deliberately NOT computed in P6: it is
`(impulse - pullback) / leg`, and P5 owns that arithmetic so the division and
its band comparisons stay in one place.

## 4. Size — and why the tuple cannot carry it (RESOLVED)

Roughly **20 additional values per timeframe**. The first draft of this section
proposed widening the projection tuple from 14 to about 34 and flagged the arity
as a risk to measure. Measurement settled it: **the scalar widening is
impossible**, and the reason is a script-wide budget rather than a per-call one.

Pine caps the COMBINED tuple elements returned by ALL `request.*` calls in one
script at 127. The measured inventory (`test_p6_request_tuple_budget`):

```
P6 DEV     6 semantic x 14                       =  84
P6 ATOMIC  6 semantic x 14 + 6 capture x 5       = 114   <- compiles today
widened    6 x 34                                = 204   <- impossible
```

**Selected representation:** preserve the 14 scalar positions and append ONE
`P5TransportExt` object per request — 15 elements per context, 90 in P6 DEV.

Two consequences the arithmetic makes visible:

* **The atomic twin, not P6 DEV, is the binding constraint.** It lands at 120 of
  127, so the atomic capture return cannot gain a transport H1/H2 scalar pair
  (that reaches 132). The new digest must ride inside a UDT or through
  `log.info`, which is already how the raw rows travel.
* **114 is a proven-compiling floor**, observed with 0 errors during the P6
  closure run, so the headroom above is measured against a limit this campaign
  has actually approached.

UDT is preferred over bit-packing because the new fields include timestamps,
prices and ratios, where packing would add encoding, overflow and precision risk
for no benefit. Packing is a fallback for small enums only, and only if a real
resource problem survives. If a mixed tuple+UDT return proves unsupported, the
documented fallback is one FULL UDT per request carrying old 14 and new ~20
together — never additional request contexts, which the author has declined.

## 5. Constraints this extension must respect

* append only — existing tuple positions do not move, so the old prefix stays
  byte-comparable;
* no new `request.security` context; envelope stays 1251, host stays 1800;
* no new plot — P6 DEV remains at 63 of Pine's 64;
* no second swing/structure/ATR engine; every new field is a reduction of state
  the context already computes;
* no P5 configuration constant enters P6 — raw values cross the boundary, and
  P5 applies its own thresholds.

## 6. Re-closure obligation

Because `btmm_poi_btrc_scanner_p6_dev.pine` changes, the P6 closure capture must
be re-run. The old thirty surface comparisons and the global digest
(H1 74231825 / H2 124714621) must reproduce **exactly**, which is what
demonstrates the extension is additive rather than semantic. A separate additive
digest covers the new fields; the old digest definition is not redefined.
