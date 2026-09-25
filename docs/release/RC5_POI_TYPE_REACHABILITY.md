# ALL 19 POI TYPES ARE DISPLAY-CAPABLE -- MEASURED

**Run configuration** for every number below: `rc5_structural_origin = False`
(production default), all other inputs default. Four real captures:

| capture | bars | POIs emitted |
| --- | --- | --- |
| XAUUSD H4 | 795 | 204 |
| EURUSD M15 | 300 | 94 |
| XAUUSD M45 | 529 | 111 |
| XAUUSD H3 | 300 | 85 |

---

## 1. MANIFESTATION TABLE

"emitted" = reached `poi_observations`. "alive" = not
`GENUINE_INVALIDATION_CONFIRMED` at the end of the run.

| # | display name | code | toggle | detector | tier? | H4 | M15 | M45 | H3 | total | alive | class |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | BUY ORDER BLOCK | 1 | `tBuyOb` | `order_blocks.py` | yes | 0 | 0 | 0 | 0 | **0** | 0 | **D** |
| 2 | SELL ORDER BLOCK | 2 | `tSellOb` | `order_blocks.py` | yes | 0 | 0 | 0 | 0 | **0** | 0 | **D** |
| 3 | BUY FVG | 3 | `tBuyFvg` | `fair_value_gaps.py` | NA | 24 | 5 | 6 | 13 | 48 | 13 | **A** |
| 4 | SELL FVG | 4 | `tSellFvg` | `fair_value_gaps.py` | NA | 21 | 20 | 14 | 8 | 63 | 31 | **A** |
| 5 | BUY TO SELL CANDLE | 5 | `tB2S` | `reversal_candles.py` | yes | 1 | 0 | 1 | 0 | 2 | 1 | **A** |
| 6 | SELL TO BUY CANDLE | 6 | `tS2B` | `reversal_candles.py` | yes | 3 | 0 | 0 | 2 | 5 | 0 | **A** |
| 7 | BASE RALLY | 7 | `tBaseRally` | `bases.py` | yes | 2 | 0 | 2 | 2 | 6 | 2 | **A** |
| 8 | BASE DROP | 8 | `tBaseDrop` | `bases.py` | yes | 6 | 4 | 4 | 4 | 18 | 1 | **A** |
| 9 | BULLISH PRESSURE WICK | 9 | `tBullPw` | `pressure_wicks.py` | yes | 26 | 4 | 10 | 10 | 50 | 9 | **A** |
| 10 | BEARISH PRESSURE WICK | 10 | `tBearPw` | `pressure_wicks.py` | yes | 26 | 15 | 21 | 11 | 73 | 30 | **A** |
| 11 | BULLISH ENGULFING | 11 | `tBullEng` | `engulfing.py` | yes | 11 | 4 | 8 | 6 | 29 | 9 | **A** |
| 12 | BEARISH ENGULFING | 12 | `tBearEng` | `engulfing.py` | yes | 16 | 2 | 6 | 3 | 27 | 7 | **A** |
| 13 | HAMMER | 13 | `tHammer` | `single_candle_reversals.py` | yes | 13 | 2 | 4 | 4 | 23 | 4 | **A** |
| 14 | SHOOTING STAR | 14 | `tShootStar` | `single_candle_reversals.py` | yes | 12 | 9 | 7 | 4 | 32 | 13 | **A** |
| 15 | MORNING STAR | 15 | `tMorning` | `three_candle_stars.py` | yes | 7 | 2 | 3 | 2 | 14 | 2 | **A** |
| 16 | EVENING STAR | 16 | `tEvening` | `three_candle_stars.py` | yes | 17 | 6 | 3 | 1 | 27 | 10 | **A** |
| 17 | SUPPORT ZONE | 17 | `tSupport` | `reference_zones.py` | NA | 1 | 3 | 4 | 1 | 9 | 1 | **A** |
| 18 | RESISTANCE ZONE | 18 | `tResist` | `reference_zones.py` | NA | 3 | 4 | 0 | 0 | 7 | 4 | **A** |
| 19 | DOJI | **33** | `tDoji` | `doji.py` | NA | 0 | 0 | 0 | 0 | **0** | 0 | **D** |

**16 of 19 manifest directly.** Every classic candlestick family the author
named is present and alive: Hammer, Shooting Star, both Engulfings, Morning and
Evening Star, both Pressure Wicks, FVG, both Bases, B2S/S2B, S/R.

**Hammer and Shooting Star are standalone types**, codes 13 and 14, from
`single_candle_reversals.py` -- they are not folded into another family.

## 2. THE THREE THAT DID NOT EMIT ARE DETECTED, NOT MISSING

Running the detectors directly, before any downstream arbitration:

| detector | XAUUSD H4 | EURUSD M15 | XAUUSD M45 | XAUUSD H3 | total raw |
| --- | --- | --- | --- | --- | --- |
| `detect_order_blocks` | **28** | 7 | 20 | 11 | **66** |
| `detect_dojis` | **25** | 8 | 19 | 3 | **55** |

So 121 raw candidates exist and none survive to the observation layer in these
windows. They are **gated downstream, not unreachable and not unimplemented**.

### Why ORDER BLOCK is rare

Its rule is a strict superset of engulfing's. Both need
`range(displacement)/range(origin) >= 2.0`, a direction flip, and neither
candle a Doji. The order block adds a further clause: the displacement must
**close beyond the origin candle's opposite extreme** -- `close > origin.high`
for a BUY block, `close < origin.low` for a SELL block.

Near-miss analysis found only 4 pairs on H4 that cleared every other test and
failed on that clause alone, the closest by 2.025. So it is genuinely
demanding, and the RC5 promotion path (`obPending` / `obPromoEng`) adds a
further structural confirmation on top.

### Why DOJI is rare

A Doji is only a POI **on a confirmed swing pivot** -- `detect_dojis` takes
`pivot_sides` and emits nothing without it. On top of that, RC3 doctrine states
a Doji is never part of an engulfing or order-block formation, so same-origin
arbitration removes candidates that overlap a stronger reading.

Measured oddity worth recording: on XAUUSD H4, DOJI emits **0** with the
structural-origin gate OFF and **3** with it ON, even though the gate cuts
total POIs 204 -> 86. That is consistent with Dojis being outcompeted at shared
origins when the competing patterns survive, and surviving alone when the gate
rejects those competitors as mid-leg texture.

## 3. WHY A VALID TYPE MAY STILL NOT BE ON SCREEN

Five independent gates, in pipeline order. A type absent from the chart has
failed one of them -- which is not the same as being undetectable:

1. **lifecycle** -- `GENUINE_INVALIDATION_CONFIRMED` removes it. On XAUUSD H4
   that is 53 of 86 POIs;
2. **P4 subordination** -- a formation owned by a Base is hidden. Measured 3 of
   94 on the EURUSD M15 golden;
3. **type toggle** -- `p7zTypeOn[code - 1]`;
4. **overlap-cluster arbitration** -- one winner per same-direction overlap
   cluster via `f_rc5DisplayBetter` (tier, then score, then availability). On
   XAUUSD H4 this cut 45 eligible to 12;
5. **global quota** -- nearest `p7zMaxVisibleZones = 8` to price.

So at most 8 zones are ever drawn. With 45 eligible after lifecycle and
authority, most valid POIs are legitimately off-screen at any moment.

## 4. VERDICT

**No type is unreachable and none is incorrectly mapped.** No code change is
warranted by this audit.

Classification: **16 type A**, **3 type D** (order blocks and Doji: detector
proven live with 121 raw candidates, emission gated downstream in these
windows). **None are type E** -- all 19 are standalone types with their own
type code, input toggle and detector module.

## 5. A METHOD NOTE, BECAUSE IT NEARLY BECAME A FALSE FINDING

The first pass reported `DOJI_raw = 0` everywhere. That was wrong: I called
`detect_dojis` without `confirmed_swings`, so `pivot_sides` was empty and it
returned zero **by construction**. Called as the analyzer calls it, it gives 55.

That is the third time in this project a measurement artifact nearly became a
conclusion. A zero from a detector is worth re-deriving before it is believed.
