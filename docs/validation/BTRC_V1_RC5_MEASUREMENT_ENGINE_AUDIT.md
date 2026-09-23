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

---

# ARRIVAL LEG — AN APPROVED RULE EXISTS, AND IT IS DIRECTIONAL

The instruction was to search the repository for an author-approved arrival rule
and, failing that, to leave arrival strength unresolved. **One exists.**

`knowledge/MEASUREMENT_STANDARDS.md`, "Base Formation, Compactness, and
Departure Standard" (Base Formation Standard V1 — Provisional):

> **Scope:** Applies only to Base Rally (**Rally-Base-Rally**) and Base Drop
> (**Drop-Base-Drop**).

and its INVALID BASE row includes:

> *"direction does not match Base Rally or Base Drop."*

Each POI rule file states the location requirement directly —
`knowledge/poi_rules/volume_based/base_drop.md`:

> **Required market location:** *"The base must be a distinct pause/consolidation
> after an existing bearish move, before the breakout."*

and `base_rally.md` the same with *"an existing bullish move"*.

## What that settles, and what it does not

* **Arrival DIRECTION is approved and required**, and it must MATCH the
  departure. The book defines exactly two Base POIs and both are same-direction.
* **Arrival STRENGTH is not defined anywhere.** §8 "What Remains Unresolved"
  confirms the standard "fixes base geometry, compactness, and
  departure-confirmation math only". No constant was invented.

## The consequence, which is an author decision

Under the approved standard, **DROP_BASE_RALLY and RALLY_BASE_DROP are not valid
Bases at all** — they are the "direction does not match" case. The current
detector emits them as `BASE_RALLY` / `BASE_DROP` regardless of the preceding
move, so it **over-produces**.

On the frozen FXCM captures the over-production is most of the population:

| host | RBR | DBD | **DBR** | **RBD** | unknown |
| --- | --- | --- | --- | --- | --- |
| M45 bars (529) | 0 | 1 | **2** | **1** | 0 |
| H3 (300 bars) | 1 | 3 | **0** | **1** | 1 |

Applying the approved directional rule would remove **3 of 4** M45 Bases and
**1 of 6** H3 Bases. That is a population change, so it is reported rather than
applied: the latest instruction mapped all four families onto the two transport
codes, which implies DBR and RBD are valid, while the approved standard says
they are not. **Those two positions conflict and only the author can settle it.**

---

# FORMATION OWNERSHIP — BUILT, AND IT FIRES ZERO TIMES ON REAL DATA

`poi/formation_ownership.py` is a side-car layer keyed by the existing stable
formation identity. It never mutates or relabels: a Doji subordinate to a
Drop-Base-Drop is still `PoiType.DOJI` with its own geometry and transport code.

Ownership requires the member's **complete** source span to lie inside the
owner's **base** candles (the departure is excluded — it is the impulse, not the
pause), the directions to agree, and both records to be causally available.
`active_from_utc` is the later of the two availabilities, so a Base discovered
later can never retroactively suppress a pattern that was actionable first.

FVG is deliberately not ownable. Order Block and B2S/S2B are deliberately not
ownable pending forensics — absence here is a recorded "not yet decided", and a
test asserts it so the omission cannot silently become a doctrine.

## The measurement that matters

| host | bases | candle patterns | **subordinated** |
| --- | --- | --- | --- |
| M45 bars (529) | 4 | 121 | **0** |
| H3 (300 bars) | 6 | 61 | **0** |

**Zero.** Not one candle pattern on either real capture has its complete source
span inside a Base's base candles — and the reason is structural, not a bug in
the layer: a Base requires every base candle to be ≤ 0.50× the departure range
and tightly overlapped, i.e. **small and quiet**, while a Shooting Star, Hammer
or Pressure Wick requires a **large rejection wick** and an Engulfing a **large
body**. Those requirements are very nearly mutually exclusive.

## Which defect the author actually saw

The brief asked these to be separated, and the data separates them:

> *existing code currently fails Base detection* **or** *Base exists but loses
> authority*

**The evidence points at the first.** Only 4 Bases in 529 M45 bars and 6 in 300
H3 bars is a very low population, and none of them contains a candle pattern. So
the Shooting Star the author saw was almost certainly **not inside a Base the
engine detected** — the engine never found a Base there at all. Formation
ownership is necessary and now exists, but on this evidence it is **not
sufficient** to explain the observation, and the next forensic step belongs in
the Base detector's compactness rules rather than in authority.

Caveat stated rather than buried: the impact harness passes
`confirmed_swings=()` to `detect_dojis`, so the DOJI population reads 0 on both
hosts. That is a harness limitation, not an engine fact, and Doji-inside-Base
remains unmeasured on real data.

---

# BASE DETECTOR FORENSICS — ONE GATE REJECTS 97%

## The exact formulas, as implemented

| gate | formula | units |
| --- | --- | --- |
| small candle | `max(total_range(c) for c in base) > 0.50 × total_range(departure)` → reject | **full range, wicks included** |
| departure ratio | `total_range(departure) / max_base_range < 2.0` → reject | full range |
| base height vs ATR | `(max(high) − min(low)) > 0.75 × ATR(14)[end-1]` → reject; ATR falls back to the departure range when unavailable | full envelope |
| base height vs departure | `(max(high) − min(low)) > 0.60 × total_range(departure)` → reject | full envelope |
| midpoint drift | for every base candle, `abs(((high+low)/2) − base_midpoint) ≤ 0.25 × base_height` | midpoints of full range |
| pairwise overlap | for each adjacent pair, `max(0, min(h₁,h₂) − max(l₁,l₂)) / min(total_range₁, total_range₂) ≥ 0.50` | **denominator is the smaller candle's full range** |
| departure direction | bullish: `close > open AND close > base_high`; bearish: `close < open AND close < base_low` | — |

`total_range(c) = high − low`. `body(c) = |close − open|`. **`body` is never used
by the Base detector.** Every compactness test is wick-inclusive.

**This matches the approved standard, not a misreading of it.** Base Formation
Standard V1 says the size test "Uses Candle Total Range (`High − Low`) from
Candle Measurement Standard V1 without modification", and `base_drop.md` states
"Base High/Low use candle highs/lows (**wicks included**)". So the author's
hypothesis that the implementation substituted range for body is **disproven** —
the code is faithful; the question is the standard's calibration, which the
standard itself flags as "provisional, pending calibration against
expert-approved examples".

**Two of the listed gates are one gate.** `max_base > 0.50 × departure` and
`departure / max_base < 2.0` are exact reciprocals, so they can never disagree.
The ANY-fail columns below confirm it: identical counts, every time.

## Rejection histogram — current constants, nothing changed

| | M45 (529 bars) | H3 (300 bars) |
| --- | --- | --- |
| candidate windows | 2,625 | 1,480 |
| **PASS all gates** | **4 (0.152%)** | **6 (0.405%)** |
| median wick share of candle range | **0.535** | **0.544** |

FIRST failing gate / ANY failing gate:

| gate | M45 first | M45 any | H3 first | H3 any |
| --- | --- | --- | --- | --- |
| **small candle ratio** | **2,550** | 2,550 | **1,428** | 1,428 |
| departure ratio | 0 | 2,550 | 0 | 1,428 |
| height vs ATR | 63 | 2,544 | 46 | 1,455 |
| height vs departure | 0 | 2,559 | 0 | 1,435 |
| midpoint drift | 5 | 1,728 | 0 | 948 |
| pairwise overlap | 0 | 1,330 | 0 | 690 |
| departure direction | 3 | 1,851 | 0 | 1,052 |

**The small-candle ratio is the first failure for 97.3% of M45 rejections and
96.9% of H3's.** Nothing else is close. The Base population is governed by a
single provisional constant.

And the mechanism the author suspected is visible in the data: **the median
candle spends 53–54% of its range in wicks.** Because the gate measures full
range, a candle with a compact body and ordinary wicks is judged "large", so
the comparison is dominated by wick noise rather than by body compactness — on
these hosts, more than half of what the gate measures is wick.

**No constant has been changed, and none should be on this evidence alone.** A
low count is acceptable if correct; the decisive test is the author's own M15
region, which is the one fixture that can say whether a formation the author
reads as a Base fails this gate.

## DBR / RBD vs the existing reversal families

| | RBD (hypothetical) | BUY_TO_SELL (actual) |
| --- | --- | --- |
| source span | 2–6 base candles + departure | **1 candle** |
| zone | base group high → low | that candle's high → low |
| candle requirement | every base candle **small** | a **strong bullish** candle |
| confirmation | departure closes beyond the base | subsequent bearish reversal |
| arrival | existing bullish move | existing bullish move |

**Classification: RELATED BUT DISTINCT.** They describe the same market event —
an up-move turning down — with incompatible topology: B2S marks one *strong*
candle, RBD would mark a multi-candle *compact* pause. The candle requirements
are opposites, so one cannot be the other. DBR vs SELL_TO_BUY is the mirror,
with the same conclusion.

So DBR/RBD are **not already covered** by B2S/S2B. They remain non-standard
under the approved Base standard, and that is a doctrine gap rather than a
duplication.

## How DBR/RBD are gated

The smallest representation that destabilises nothing: `STANDARD_BASE_FAMILIES
= {RALLY_BASE_RALLY, DROP_BASE_DROP}` plus `is_standard_base_family()`. No
contract, transport code or record shape changed. Detection is untouched — DBR
and RBD candidates are still produced and still carry their family — but
formation ownership now only accepts a standard-family Base as an owner, so a
non-standard Base can subordinate nothing. A Base whose arrival is unknown
(`None`) is likewise not authoritative: unverifiable is not authoritative.
