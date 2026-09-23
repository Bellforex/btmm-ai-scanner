# RC5 MEASUREMENT ENGINE — FORENSIC AUDIT

Opened from `00674d7`. Python first: the reference engine is the semantic
authority, so nothing here proposes a Pine-side visual workaround.

This document records what is **established from the code**. Items still open
are named as open; nothing is asserted that was not read or measured.

---

## 1. THE BASE DETECTOR IMPLEMENTS ONLY HALF THE DOCTRINE

**Doctrine (author):** arrival impulse → compact base → decisive departure.

**Implemented** (`poi/bases.py::detect_bases`), in order:

| check | constant |
| --- | --- |
| base length between min and max | `base_min_candles` 2, `base_max_candles` 6 |
| every base candle small vs departure | `small_candle_ratio_standard` 0.50 |
| departure / largest base range | `order_block_size_ratio_standard` 2.0 |
| base height vs ATR(14) | `base_height_atr_multiplier` 0.75 |
| base height vs departure range | `base_height_departure_multiplier` 0.60 |
| every base midpoint near the base midpoint | `base_midpoint_drift_ratio` 0.25 |
| pairwise overlap of adjacent base candles | `base_overlap_ratio_minimum` 0.50 |
| departure closes beyond the base, with body direction | — |

**MISSING: the arrival leg. Entirely.** `start` iterates every bar; nothing
requires an impulse to have arrived *into* the base. There is no
`arrival_*` constant in `PoiConfiguration` either.

**Consequence — the four families cannot exist.** `PoiType` contains only
`BASE_RALLY` and `BASE_DROP`, assigned purely from the *departure* direction.
Without an arrival leg, **RBR / DBD / RBD / DBR are not distinguishable and are
not produced.** Rally-Base-Rally and Drop-Base-Rally both emit `BASE_RALLY`.

This is reported, not substituted. No new threshold has been invented.

---

## 2. A BASE CAN NEVER HOLD AUTHORITY OVER A CANDLE INSIDE IT

This is the author's observed defect, and it is intentional as built.

`poi/authority.py`:

```python
REVERSAL_LADDER = { B2S/S2B: 1, OB: 2, STARS: 3, ENGULFING: 4,
                    HAMMER/SHOOTING_STAR: 5, DOJI: 6, PRESSURE_WICK: 7 }
REVERSAL_TYPES = frozenset(REVERSAL_LADDER)
```

**`BASE_RALLY` and `BASE_DROP` are not in the ladder**, so they are not
reversal types. In `arbitrate_cluster`:

* `reversals` = ladder members; `others` = everything else, **bases included**
* **the primary is always `reversals[0]`** — a Base can never be primary
* in the `others` loop **only `FVG_TYPES` may be subordinated**; a Base is
  always `INDEPENDENT`

The docstring states the design outright: *"Non-reversal families (imbalances,
bases, structural zones) are never ranked."*

### Item 12 — Base authority pairing table, as the code behaves today

| pairing | primary | Base outcome |
| --- | --- | --- |
| Base vs SHOOTING STAR | **Shooting Star** | INDEPENDENT |
| Base vs PRESSURE WICK | **Pressure Wick** | INDEPENDENT |
| Base vs DOJI | **Doji** | INDEPENDENT |
| Base vs ENGULFING | **Engulfing** | INDEPENDENT |
| Base vs ORDER BLOCK | **Order Block** | INDEPENDENT |
| Base vs B2S / S2B | **B2S / S2B** | INDEPENDENT |
| Base vs FVG | none (no reversal) | both INDEPENDENT |

So a Shooting Star contained in a valid Base is **promoted to primary**, and the
Base is left as an unranked independent record. Downstream, display arbitration
then chooses between two independent same-direction overlapping zones on
tier/score/recency — which is how the inner candle ends up on the chart instead
of the Base. **The misclassification is semantic, in Python, not a renderer
bug**, exactly as the author suspected.

---

## 3. STRUCTURE LABELS: THE CODE HOLDS TWO DIFFERENT "PIVOT CANDLES"

A swing is not always one candle. `ConfirmedSwing` carries
`pivot_candle_record_ids` (**plural**), `pivot_start_time_utc`,
`pivot_end_time_utc` and `pivot_bar_index`.

`domain/swings.py` sets:

```python
pivot_bar_index      = pivot.start_index
pivot_start_time_utc = candles[pivot.start_index].event_time_utc
pivot_end_time_utc   = candles[pivot.end_index].event_time_utc
```

So the **canonical pivot bar is the START** of the pivot group.

But the HH/HL/LH/LL renderer draws at **`sw.pivotEndTime`** — the group's LAST
candle — with the correct `sw.price`. For any pivot spanning more than one
candle the label is therefore **horizontally offset by (end − start) bars from
the canonical pivot bar**, at the right price. That is the reported
"detached from the actual candles/pivots".

The root cause is a category error, not a coordinate typo: **`pivotEndTime` is
the swing's stable IDENTITY key** (used by `rc5SwingRole`, the P2 walk's
`stableKey` and the trendline anchors) **and it is being reused as a drawing
COORDINATE.** Identity and geometry are different things.

**Author decision required, because the fix has reach.** `domain/trendlines.py`
independently uses `pivot_candle_record_ids[-1]` — the group's LAST candle — as
its anchor index. Python and Pine agree there, so trendlines are *not* a parity
defect; but moving the canonical pivot to `start_index` for drawing would make
the codebase answer "which candle is the pivot" two different ways unless
trendline anchoring is revisited at the same time. Reported rather than
silently changed.

The availability/where distinction the author drew is otherwise respected:
`meaningful_confirmation_time_utc` / `availability_time_utc` gate *when* a
record may appear and are separate fields from the pivot coordinates.

---

## 4. TYPE / GEOMETRY INTEGRITY AT THE DETECTOR LAYER — CLEAN

Each family builds its own zone from its own candles. No borrowing found.

| family | zone | source ids |
| --- | --- | --- |
| **DOJI** | defended wick only: bullish `body_low → low`, bearish `high → body_high`, after the structural side is resolved from `pivot_sides`; refused when the defended wick is empty | its own single candle |
| **FVG** | true three-candle imbalance: `third.low → first.high` (buy) or `first.low → third.high` (sell) | all three candles |
| **ORDER BLOCK** | `origin.high → origin.low` | (origin, displacement) |
| **BASE** | `max(high) → min(low)` over the base candles | base candles + departure |

`poi_type=PoiType.DOJI` is assigned at construction and never rewritten in the
detector, so **no Doji is relabelled into another family at detection.**

**Open:** this clears the *detector* layer only. The author's requirement that
displayed type, source ids and zone always come from the SAME formation record
has **no regression test yet**, and the transport/renderer layers have not been
audited for it. That test does not exist and should be written.

---

## OPEN — NOT DONE, NOT ESTIMATED

Screenshot fixture freeze; RC4-vs-RC5 record comparison; the eight Base
regression fixtures; the six structure fixtures; `_formation_key` collision
audit; batch/incremental equality re-proof; and the M5/M15/M45/H3/H4 impact
counts. No corrective code has been written: the three findings above change
detection, authority and rendering, and each needs an author decision before
implementation — particularly the arrival leg (which adds a family axis the
enum does not yet have) and the pivot-coordinate question (which reaches
trendline anchoring).
