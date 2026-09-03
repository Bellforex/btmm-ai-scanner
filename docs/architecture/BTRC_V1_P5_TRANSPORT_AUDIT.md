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
| `altCount4` | int | `_alternation_count(window=4)` | CHOCH count among the last 4 transitions |
| `priorOppStreak` | int | `_prior_opposite_streak` | backward scan from the second-to-last transition while type == opposing BOS |
| `exhaustFlag` | int | `_exhaustion` | bullish: last SWING_HIGH price < previous SWING_HIGH price; bearish: mirrored on lows |

`current_state.direction` and `analyzed_swing_count` are already transported
(`p2Dir`, `swingCount`).

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
| `prevTransType` | int | `ordered_transitions[-2].transition_type`, for the FAILED_BREAK whipsaw test |
| `dispClsAtTrans` | int | `_displacement_at(displacements, last_transition)` — the classification at the breaking candle |

`p2LastTrans` (last transition type) is already transported.

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

## 4. Size, and the one thing to verify first

Roughly **20 additional values per timeframe**, taking the projection tuple from
14 to about 34.

**That tuple width is the implementation risk and must be measured before the
port is written.** Pine's limit on `request.security` tuple arity is not
something to assume — the largest this campaign has proven is 14. If 34 does not
compile, the fallback is to pack related small integers into single values
(direction and classification are 2-3 bits each) rather than to add request
contexts, which the author has declined.

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
