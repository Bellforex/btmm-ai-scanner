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

---

# THE AUTHOR'S M15 REGION — THE EXACT GATE, FOUND

`artifacts/rc5_m15_screenshot_capture/rc5_ohlc_m15_eurusd.csv`, 300 FX:EURUSD
M15 bars, 2026-09-18 09:45 → 2026-09-23 12:30 UTC, sha256 `2c482f01…`. Read
from the chart model read-only under `bellcare1994` on BAH-RC5-LAB; `bellforex`
was not opened and the red reference line was not touched.

Bases the current standard finds in this window: **4**
(1 × RALLY_BASE_RALLY, 2 × DROP_BASE_DROP, 1 with no arrival candle available).

**Near-miss windows — every Base gate passes except the small-candle /
departure-ratio pair: 3, and 2 of them carry a candle-pattern detection.**

## The case, bar by bar

**2026-09-21 19:15 UTC**, two compact bars into a bearish departure:

| idx | time (UTC) | open | high | low | close | body | range | body/range | RC5 emits |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 134 | 09-21 19:15 | 1.14673 | 1.14688 | 1.14673 | 1.14679 | 0.00006 | 0.00015 | 0.40 | **BEARISH_PRESSURE_WICK, EVENING_STAR** |
| 135 | 09-21 19:30 | 1.14679 | 1.14693 | 1.14672 | 1.14678 | **0.00001** | 0.00021 | **0.05** | EVENING_STAR |
| dep | 09-21 19:45 | 1.14678 | 1.14678 | 1.14643 | 1.14644 | 0.00034 | 0.00035 | — | — |

base height 0.00021 · ATR gate PASS · height/departure PASS · midpoint drift
PASS · pairwise overlap PASS · departure direction PASS (bearish, closes below
the base) · arrival direction bearish → would be **DROP_BASE_DROP**, a standard
family.

**departure / max_base_range = 1.667, and the gate requires ≥ 2.0.**

## Item 17 — the exact gate that rejects the author's Base

**The small-candle ratio** (identically, the departure ratio — they are the same
condition expressed as reciprocals). Nothing else fails.

**And the mechanism is exactly the wick hypothesis.** Bar 135 has a body of
0.00001 against a range of 0.00021: it is **95% wick**. By body it is an
extremely compact base candle — by total range, which is what the gate measures,
it is 0.60 × the departure and so breaches the 0.50 limit.

So the author sees a Base; the engine sees a BEARISH_PRESSURE_WICK and an
EVENING_STAR over those same two bars and **no Base at all** — because the base
candles' WICKS carry them over the size threshold while their BODIES are tiny.
This is the "Shooting Star where a Base should be" class, reproduced from real
bars.

## Item 19 — does the Base detector require correction?

**The implementation does not. The standard's measurement basis is the open
question, and it is an author decision.**

The code faithfully implements Base Formation Standard V1, which explicitly
mandates Total Range (High − Low) "without modification". The standard is also
explicitly **provisional, pending calibration against expert-approved
examples** — and this capture is precisely such an example.

The question the evidence raises, stated without acting on it:

> Should the base-candle size test measure **total range** (current, approved,
> wick-inclusive) or the **body**, given that a base candle's defining quality
> is a compact body and that on these hosts the median candle is 53–54% wick?

No constant has been changed. Changing this one would alter the Base population
on every host and must not be done to "make more bases" — but it is the single
lever the data points at, and the author's own example is now a fixture that can
adjudicate it.

---

# A/B — BASE-CANDLE SIZE: TOTAL RANGE vs BODY

`PoiConfiguration.base_size_uses_body`, **default OFF**. It switches the size
basis and nothing else: thresholds stay 2.0 / 3.0 / 0.50 / 0.3333, the POI zone
stays wick-inclusive, and the ATR height, height/departure, midpoint-drift and
pairwise-overlap gates are untouched. Implemented identically in `detect_bases`
and `_evaluate_new_bases`.

A zero body is treated as **maximal compactness**, not a degenerate case: the
ratio becomes `None` and every ratio test passes. It is only reachable under the
body basis (`max_base_range == 0` is already guarded), so no new numeric
convention enters the approved path and no minimum doji body was invented.

## The golden formation — 2026-09-21 19:15 UTC

| | |
| --- | --- |
| max base **total range** | 0.00021 |
| max base **body** | 0.00006 |
| departure size | 0.00035 |
| **OLD** ratio dep/range | **1.667 → FAIL** (needs ≥ 2.0) |
| **NEW** ratio dep/body | **5.833 → PASS** |
| A result | **no Base on these bars** |
| B result | **BASE_DROP, zone 1.14672–1.14693** |

The zone is the real market extremes, wicks included — unchanged by the
experiment, exactly as directed.

## But the family is RALLY_BASE_DROP, and that is the second half of the defect

| bar | time | close vs open |
| --- | --- | --- |
| 130 | 18:15 | DOWN |
| 131 | 18:30 | DOWN |
| 132 | 18:45 | UP |
| **133** | **19:00 (arrival)** | **UP** |
| 134–135 | base | — |
| 136 | 19:45 (departure) | DOWN |

The arrival proxy reads the **single preceding candle**, which closes UP, so the
family is **RALLY_BASE_DROP** — not a standard family, therefore gated out of
Base authority and owning nothing. A human reading the book's *"after an
existing bearish move"* would see 18:15 and 18:30 both closing down and call
this **DROP_BASE_DROP**; bars 132–133 are a two-candle bounce inside that move.

**So the body rule fixes DETECTION but the arrival proxy then denies AUTHORITY,
and the author's visual complaint is still not resolved end-to-end.** The proxy
is single-candle because no approved multi-bar arrival definition exists —
Standard V1 §8 leaves it unresolved — so this cannot be corrected without a
doctrine decision.

## Population change

| host | A bases | B bases | new |
| --- | --- | --- | --- |
| M15 EURUSD (300 bars) | 4 | **7** | 3 |
| M45 bars XAUUSD (529) | 4 | **10** | 6 |
| H3 XAUUSD (300) | 6 | **9** | 3 |

Ownership subordinations after the change: **M15 0, M45 1 (a HAMMER), H3 0.**
The body rule alone does **not** make the ownership layer live.

Doji harness corrected — real confirmed swings are now passed, so these are
engine facts: **M15 8, M45 13, H3 3** Doji detections (previously reported as 0,
which was a harness artefact).

## False-positive review — and a flaw in my own heuristic

Every one of the 12 newly accepted Bases tripped my `envelope > 0.5 × departure`
flag. That is **my heuristic being mis-calibrated, not evidence of bad
geometry**: the approved `base_height_departure_multiplier` already permits up
to 0.60×, so flagging at 0.50× flags nearly everything that legitimately passes.
Reported as a defect in the review tool rather than dressed up as a finding.

The one case that is genuinely worth the author's eye:

> **H3 2026-08-26 16:00** — 2 bars, max range 19.08, **max body 2.25**, departure
> 34.72. Old ratio 1.82, new ratio **15.43**. Both base candles are **>80% wick**.

That is the shape the author warned about: tiny bodies with very large wicks
producing a wide Base zone. The ATR-height gate did not reject it. It is the
strongest argument for keeping the body rule experimental until more examples
are reviewed.

## Acceptance status

| criterion | result |
| --- | --- |
| 1. author's M15 formation becomes the expected DBD | **NO** — it becomes a Base, but RALLY_BASE_DROP, not DBD |
| 2. geometry remains correct | YES — zone wick-inclusive, unchanged |
| 3. false-positive review acceptable | **UNPROVEN** — one >80%-wick case; my flag was mis-calibrated |
| 4. ownership behaves causally | YES — unchanged, still causal |
| 5. batch == incremental | pending re-run |
| 6. type/geometry invariants green | YES |
| 7. full suite green | pending |
| 8. impact understood | partially — populations measured, arrival proxy now the open question |

**BODY-SIZE RULE: remains EXPERIMENTAL.** Criterion 1 fails, and it fails for a
reason outside the body rule itself.

---

# Unit 12 — the arrival leg is STRUCTURAL

The acceptance table above closed with criterion 1 failing "for a reason
outside the body rule itself". That reason is now fixed.

## What was wrong

`classify_base_family` read the **single candle before the base** and called it
bullish when `close >= open`. That is the displacement engine's per-candle
test, applied to a question that is not per-candle. A Base is the middle of
`arrival leg -> base -> departure leg`, and a leg is a multi-candle structural
fact.

The detector cannot see it. `detect_bases` scans a window of
`base_min_candles .. base_max_candles + 1` bars; the leg that brought price to
the area is usually outside it entirely.

## What replaced it

Nothing new was built. The engine already maintains exactly one causal
structural-direction mechanism, in `poi/leg_origin.py`:

| item | answer |
| --- | --- |
| producer | `_direction_timeline(walk, relationships)`, built inside `_gate` |
| upstream | `structure.relationships.detect_swing_relationships` -> `structure.transitions.run_structure_walk` |
| direction field | `StructureTransitionCandidate.direction_after` (plus the walk bootstrap: first HH+HL / LH+LL pair) |
| availability | every entry keyed by `availability_time_utc`; `_direction_at` uses `bisect_right`, so direction at *t* is the last change **<= t** |
| batch | `_gate` line 566 builds it, line 615 reads it per candidate |
| incremental | the slow path calls the SAME `_gate` and stores the result in `LegOriginFrontier.timeline`; the fast path reads `state.timeline`, and is only taken when the swing signature is unchanged **and** `_may_break` is false — i.e. when no transition can appear, so the carried timeline is provably the same one |
| prefix stability | transitions are append-only along the frozen walk; a later prefix can append later entries but cannot alter an earlier one |

Both functions are now exported as `structure_direction_timeline` /
`structure_direction_at`. No new structure walk, no new constant, no new
detector.

`poi/base_arrival.py` assigns the family from that timeline, read at the Base's
**own first candle's event time** — the instant price arrived:

```
BaseArrivalFact(base_key, arrival_reference_utc, arrival_direction,
                arrival_leg_id, arrival_known_from_utc, family)
```

`arrival_known_from_utc <= arrival_reference_utc` always. That is the causality
receipt, and it is asserted on all three captures.

`detect_bases` and `_evaluate_new_bases` now both emit `base_family=None`.
`None` means *not yet resolved*, and an unresolved arrival is never
authoritative (`is_standard_base_family(None)` is False). **There is no
last-candle fallback anywhere.**

## The author's formation, resolved

FX:EURUSD M15, base starting 2026-09-21 19:15:

| reading | arrival | family | authoritative |
| --- | --- | --- | --- |
| retired single-candle proxy (19:00 closes up) | "rally" | RALLY_BASE_DROP | no |
| structural leg | **BEARISH** | **DROP_BASE_DROP** | **yes** |

The establishing leg is a `BEARISH_BOS` available **2026-09-21 18:00**, which
broke 1.14665 on a 1.14663 close. Nothing changed direction between then and
19:15.

And the original complaint closes with it. Those bars emit a
`BEARISH_PRESSURE_WICK` (19:15) and a `DOJI` (19:30). Under the proxy the Base
had no authority, so those two fragments were the only things on the chart —
"I see a Base, RC5 shows a Shooting Star". Under the structural arrival the
Base **owns both**, from 2026-09-21 20:00.

## It matters with the experiment OFF

The proxy also failed in the opposite direction — it **granted** authority it
should not have:

> **H3 2026-08-20 04:00**, approved size basis, no experiment flag. The candle
> before the base closes down, so the proxy returned DROP_BASE_DROP:
> authoritative. The structural leg into the area is **BULLISH**, making it
> RALLY_BASE_DROP — a counter-trend pause the approved standard does not
> recognise as a Base at all.

## Populations, all four arms

Arms: size basis (range | body) x arrival (retired proxy | structural).
A = range+proxy, B = body+proxy, C = range+structural, D = body+structural.
Arm A is byte-identical to RC4 (`2f1d2b9`) — verified by running the RC4
detector over the same bars: 4/4 bases, identical geometry tuples.

| capture | arm | bases | families | ownership subordinations |
| --- | --- | --- | --- | --- |
| M15 EURUSD | A | 4 | DBD 2, RBR 1, UNKNOWN 1 | 0 |
| | B | 7 | DBD 3, RBD 2, RBR 1, UNKNOWN 1 | 0 |
| | C | 4 | DBD 1, UNKNOWN 3 | 0 |
| | **D** | **7** | **DBD 4, UNKNOWN 3** | **2** (BEARISH_PRESSURE_WICK, DOJI) |
| M45 XAUUSD | A | 4 | DBD 1, DBR 2, RBD 1 | 0 |
| | B | 10 | DBD 4, DBR 3, RBD 1, RBR 1, UNKNOWN 1 | 1 (HAMMER) |
| | C | 4 | DBD 2, DBR 2 | 0 |
| | D | 10 | DBD 4, DBR 4, RBD 1, UNKNOWN 1 | 0 |
| H3 XAUUSD | A | 6 | DBD 3, RBD 1, RBR 1, UNKNOWN 1 | 0 |
| | B | 9 | DBD 4, DBR 2, RBD 1, RBR 1, UNKNOWN 1 | 0 |
| | C | 6 | DBD 3, RBD 1, UNKNOWN 2 | 0 |
| | D | 9 | DBD 3, RBD 2, RBR 2, UNKNOWN 2 | 0 |

Two things to read carefully here:

1. **UNKNOWN goes up** under the structural arms. That is correct, not a
   regression: early bars of a capture have no established leg, and the proxy
   was manufacturing an authoritative family out of nothing there (H3
   2026-07-31 16:00 became RALLY_BASE_RALLY on zero structural evidence).
2. **Ownership only becomes live on M15 arm D.** The body basis alone did not
   make it live (measured 0/1/0 previously), and the structural arrival alone
   does not either. Both switches are required for the author's formation.

## A correction to my own earlier reading

I previously reported that the body basis "can only ever admit more". That is
true of the **identity** set and incomplete about the record: `strength_tier`
is computed from the same size basis, so the switch also **re-tiers Bases it
did not newly admit** — 7 of the 14 arm-A bases across the three captures go
STANDARD -> STRONG. The zone and identity never move. Pinned by
`test_the_experiment_also_re_tiers_bases_it_did_not_newly_admit`.

## The >80%-wick watch item, re-read

> **H3 2026-08-26 16:00** — base candles 88.2% and 91.6% wick, max body 2.25
> against ranges of 19.08 / 17.57, departure 34.72. Zone height **20.57**.

Under the structural arrival this is `RALLY_BASE_RALLY` with a BULLISH leg
established 2026-08-21 04:00 — i.e. **standard, and now authoritative**. The
unchanged gates are therefore *not* sufficient protection against this shape;
the structural arrival did not catch it and was never going to, because the
arrival here is genuinely bullish. The tiny-body/huge-wick question is a
**size** question and remains open. No wick threshold has been invented.

## Acceptance status, revised

| criterion | result |
| --- | --- |
| 1. author's M15 formation becomes the expected DBD | **YES** — DROP_BASE_DROP, owning both contained patterns |
| 2. geometry remains correct | YES — zone wick-inclusive, identity preserved across assignment |
| 3. false-positive review acceptable | **UNPROVEN** — the >80%-wick case is now authoritative |
| 4. ownership behaves causally | YES — activation at max(base, pattern) availability |
| 5. batch == incremental | **YES** — arms A/B at the detector, arms C/D on real structure incl. arrival leg id, direction, known-from, family and ownership activation |
| 6. type/geometry invariants green | YES |
| 7. full suite green | YES |
| 8. impact understood | YES — four arms measured on three captures |

**STRUCTURAL ARRIVAL: adopted.** It is not an experiment — the proxy it
replaces was measurably wrong in both directions, including under the approved
size basis.

**BODY-SIZE RULE: remains EXPERIMENTAL** (`base_size_uses_body` default False).
Criterion 3 is still unproven and has got sharper, not softer: the one shape
that worried the author is now authoritative rather than merely detected.

---

# Unit 13 — ownership governs authority, and the body rule is calibrated

## Part A — formation ownership is now FINAL authority

The sidecar decided that a Base owns the patterns it contains. Nothing consumed
that decision, so the contained pattern kept full standing: it entered the
opportunity loop on its own, drew its own zone, and emitted its own lifecycle
events. A Base containing a Pressure Wick still lost the chart to the Pressure
Wick.

### What was added

`AuthorityReason.FORMATION_SUBORDINATE`, assigned by
`rc5_semantics.assign_formation_ownership_authority`, which runs **before**
`assign_origin_authority` at the one call site that drives the opportunity loop
(`tests/parity_support/level_a_replay.py`).

Base is **NOT** in `REVERSAL_LADDER` and must stay out. The two ranking systems
answer different questions and are never merged:

| system | question | Base |
| --- | --- | --- |
| `REVERSAL_LADDER` | which reversal SYNONYM describes this one structural event best? | absent, deliberately |
| formation ownership | is this candle pattern PART of something larger? | the owner |

Running ownership first means a subordinate never reaches arbitration, so the
two never have to agree on a single ordering. `Rc5SemanticLedger.assign_authority`
now refuses to overwrite a `FORMATION_SUBORDINATE`, so a later arbitration
cannot hand standing back — the ordering is enforced, not merely scheduled.

### Where the arrival family comes from

Recorded in `leg_origin._semantic_record`, at the moment the gate locks the
candidate, from the timeline the gate already holds. No second structure walk,
and the ledger's write-once discipline makes the family prefix-stable for free.
`PoiObservation` is unchanged — no contract migration was needed.

### Causality: no retroactive erasure

`Rc5PoiSemanticRecord.is_actionable_at(t)` returns **True** before
`formation_subordinate_since_utc`. The golden Pressure Wick confirms 19:30; its
owning Base only exists once the departure closes at 20:00. Between those
instants the wick was a real, independent POI and the record says so.

Because the replay applies ownership **per bar**, this is causal by
construction: on a prefix where the Base does not exist yet, ownership does not
resolve and the pattern keeps its standing on that bar.

### Golden M15 final authority

| item | result |
| --- | --- |
| `BASE_DROP` 2026-09-21 19:15 | family `DROP_BASE_DROP`, **in** the authoritative set |
| `BEARISH_PRESSURE_WICK` 19:15 | `FORMATION_SUBORDINATE`, owner = the Base, **not** in the authoritative set |
| subordinate since | 2026-09-21 20:00 |
| actionable before that instant | **yes** (history preserved) |
| actionable at/after | no |
| reaches `suppressed_record_ids` (the P5/P8 bridge) | yes |

### P5 / P8 consequence, measured bar by bar

Walked through `iter_level_a_bars` with `rc5_authority=True` over the full 300-bar
M15 capture — the same loop P5 and P8 are derived from:

| | |
| --- | --- |
| `BEARISH_PRESSURE_WICK` first P5-evaluated | 2026-09-21 **19:30** |
| first suppressed | 2026-09-21 **20:00** |
| independently actionable for | **0:30:00** (2 bars) — history preserved |
| P5 evaluations while suppressed | **0** |
| P8 events after suppression | **0** |

A second POI, a `BULLISH_ENGULFING`, is suppressed at 2026-09-22 03:30 by the
SAME-ORIGIN path rather than by ownership — the two mechanisms coexist in one
replay without interfering, which is what keeping the ladders separate buys.

### Side-car vs final authority — they agree

Counted through the real scan pipeline, body basis on:

| capture | observations | Bases | standard Bases | ownable patterns | ownership groups | side-car subs | FINAL suppressions | agree |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M15 EURUSD | 94 | 4 | 4 | 44 | 1 | 1 | 1 | **yes** |
| M45 XAUUSD | 111 | 6 | 4 | 62 | 0 | 0 | 0 | **yes** |
| H3 XAUUSD | 85 | 6 | 5 | 41 | 0 | 0 | 0 | **yes** |

The only subordination in the three captures is the M15 `BEARISH_PRESSURE_WICK`.

### A measured distinction that must not be confused with ownership

With `rc5_structural_origin=True` — RC5's own configuration — the contained
patterns **never reach the observation layer at all**. They are rejected
upstream as mid-leg texture (`CONTEXT_REJECT_NO_STRUCTURAL_ORIGIN`). On the
golden bars that leaves `{BASE_DROP}` alone, and ownership therefore applies
nothing there.

With the gate off, `{BASE_DROP, BEARISH_PRESSURE_WICK, EVENING_STAR}` all
survive, and ownership is what removes the wick. Two different mechanisms;
pinned separately so neither is mistaken for the other.

## Part B — RC4 geometry comparison (owed since unit 10)

M15 bars 132–138, frozen capture:

| engine | POI | source bars | source/left time | zone top | zone bottom |
| --- | --- | --- | --- | --- | --- |
| RC4 `2f1d2b9` | Base | — | **none detected** | — | — |
| RC4 `2f1d2b9` | `BEARISH_PRESSURE_WICK` | [134] | 2026-09-21 19:15 | 1.14688 | 1.14679 |
| RC4 `2f1d2b9` | `EVENING_STAR` | [134,135,136] | 2026-09-21 19:15 | **1.14693** | **1.14672** |
| corrected RC5 | `BASE_DROP` / DBD, STRONG | [134,135,136] | 2026-09-21 19:15 | **1.14693** | **1.14672** |

**The corrected RC5 Base reproduces RC4's zone exactly** — same source candles,
same left time, same top, same bottom. The author was seeing the right
rectangle under the wrong name.

That also explains why ownership does not subordinate the Evening Star: it is
not *contained* in the Base, it is **co-extensive** with it. `_base_candle_ids`
excludes the departure candle (136), so containment fails by exactly one bar —
and widening containment to swallow it would have hidden a duplicate-geometry
problem rather than solved it.

> **OPEN AUTHOR DECISION 1.** A pattern with the *same* source candles and the
> *same* zone as a Base is a duplicate, not a contained member. Should that be
> resolved by same-origin arbitration, by a co-extensive rule in ownership, or
> at display? Today it keeps full standing. Pinned by
> `test_a_pattern_spanning_the_departure_candle_is_not_contained`.

## Part C — historical Base-wick evidence

Searched `knowledge/`, `docs/`, the RC3/RC4 notes and the rule files. Exact
findings, quoted:

**`knowledge/MEASUREMENT_STANDARDS.md` §2 "Base-Candle Size":**

> Uses Candle Total Range (`High − Low`) from Candle Measurement Standard V1
> **without modification**.

**`knowledge/poi_rules/volume_based/base_rally.md:49` — "Wick treatment":**

> Base High/Low both explicitly use candle highs/lows (wicks included)

**`base_rally.md:53` — "Body treatment":**

> **Not defined as a separate zone-drawing rule** (only Total Range is used for
> Base High/Low).

`base_drop.md` says the same at the same lines.

**There is no wick threshold in the approved material, and no body measurement
at all.** Nothing was silently reinterpreted: `base_size_uses_body` contradicts
§2 as written, rather than filling an unstated gap. It is also true that §2
declares itself provisional and demands calibration against expert-approved and
expert-rejected examples — and **no such example corpus exists anywhere in this
repository**, so that calibration has never been possible.

## Part D — the calibration question, answered by an existing gate

> CAN A VALID BASE HAVE A VERY SMALL BODY AND VERY LARGE WICKS?

**Outcome B — YES, under a condition that is already documented.**

Base Formation Standard V1 **§3** caps `Base Height ≤ 0.60 × departure Total
Range`. Base Height is `max(high) − min(low)` over the base candles, so it is
`≥` the Total Range of **every** base candle. Therefore:

```
max base Total Range ≤ 0.60 × departure Total Range     — under ANY size basis
```

Switching §2 to the body basis does **not** remove the wick bound. It relaxes it
from 0.50 to 0.60, and §3 enforces that. Measured across all 26 bases the body
basis admits on the three captures, the worst observed ratio is **exactly
0.6000** — the bound is tight and never exceeded. Pinned by
`test_the_approved_envelope_gate_still_bounds_wick_size_under_the_body_basis`.

No wick threshold was invented. None is needed to bound this.

## Part E — the H3 >80%-wick case, resolved

> H3 2026-08-26 16:00 — base candles 88.2% / 91.6% wick, max body 2.25 against
> ranges 19.08 / 17.57, departure 34.72, envelope 20.57.

Every approved gate, measured: `h/ATR = 0.658` (≤0.75), `h/departure = 0.592`
(≤0.60), `min overlap = 0.915` (≥0.50), `drift/h = 0.073` (≤0.25). It sits
**inside** the approved envelope on every one.

And the decisive measurement — **the two cases are not separable by size**:

| case | wick % | departure / max range | departure / max body |
| --- | --- | --- | --- |
| GOLDEN M15 19:15 (author-approved) | **95.2%** | 1.667 | 5.83 |
| WATCH H3 2026-08-26 16:00 | 91.6% | **1.820** | **15.43** |

The watch case scores **higher than the author's own approved example on both
bases**. Every threshold that admits the golden formation admits the H3 case
too, by a wider margin — on the Total Range basis and on the body basis alike.

The author's own marked Base is **more** wick-dominated (95.2%) than the case
that worried them (91.6%). So "tiny body, huge wicks" is not a false-positive
signature here; it is the signature of the approved example.

**Conclusion:** the H3 case is not a size false positive and cannot be excluded
by any size rule without also excluding the author's formation. If it must be
excluded, the discriminator has to be something other than base-candle size,
and the approved material supplies none.

> **OPEN AUTHOR DECISION 2.** Accept the H3 case as a valid Base (the evidence
> says the approved gates already govern it), or name a NON-SIZE discriminator.
> No threshold should be invented to split two cases the measurements say are
> not splittable.

## Part F — body-basis sample review

12 newly admitted Bases across the three captures. Every one is 2 candles, and
every one passes all four unchanged gates. The striking regularity:

| capture | count | `h/departure` range | `R_range` range | tiers |
| --- | --- | --- | --- | --- |
| M15 | 3 | 0.579 – 0.600 | 1.67 – 1.73 | 3 STRONG |
| M45 | 6 | 0.526 – 0.598 | 1.67 – 1.90 | 3 STRONG, 3 STANDARD |
| H3 | 3 | 0.568 – 0.593 | 1.76 – 1.82 | 2 STRONG, 1 STANDARD |

`R_range` never leaves `(1.667, 1.90]`, i.e. `max range / departure` never
leaves `(0.526, 0.600]`. That is Part D's bound showing up in the data: the body
basis admits exactly the narrow band between §2's 0.50 and §3's 0.60, and
nothing else. It is not an open door.

Classification against historical approved examples: **not possible** — no
approved/rejected example corpus exists (Part C). Every record is reported with
its measurements instead, and none is claimed as "matches" or "does not match"
on evidence that does not exist.

## Part G — a better option than the body basis

The primary source, `knowledge/POI_MASTER_CATALOG.md` §1.4 (Bible ¶342–358):

> Base = 2+ candles, short, **small range**, positioned close together,
> relatively uniform, horizontally aligned (not forming a staircase).

> **Author clarification needed:** "Short," "small," "relatively uniform," and
> "close together" for base candles have **no numeric thresholds**.

Two things follow. The book says **small RANGE** for a Base — it talks about
body proportion only for Pressure Wick (§1.5: "still closes with a meaningful
body … not just a long wick"), so the distinction is deliberate in the source.
And **0.50 is the project's constant, not the book's** — the book supplies none.

So the thing rejecting the author's formation is a project constant applied to
the right basis, not the wrong basis.

**Arm E:** keep Total Range, move §2 from 0.50 to **0.60** — already §3's Base
Height / departure cap in the same standard, so no new number enters. By the
Part D bound this makes §2 exactly redundant with §3 rather than bypassed.

| capture | A approved (range 0.50) | B experiment (body) | **E calibrated (range 0.60)** | E == B |
| --- | --- | --- | --- | --- |
| M15 EURUSD | 4 | 7 | **7** | **yes** |
| M45 XAUUSD | 4 | 10 | **10** | **yes** |
| H3 XAUUSD | 6 | 9 | **9** | **yes** |

**Arm E admits exactly the same Bases as the body basis on all three captures**,
including the author's formation with identical geometry (zone
1.14672–1.14693, same source candles).

One difference, and it favours E: strength. The golden formation is **STRONG**
under the body basis and **STANDARD** under arm E, because the 3.0 strong ratio
is still measured on Total Range there. Arm E is the more conservative of the
two everywhere it differs.

> **OPEN AUTHOR DECISION 3.** Arm E reaches the same population while keeping
> the measurement basis the source specifies, introducing no new constant, and
> contradicting nothing. The body basis reaches it by changing the basis the
> source specifies and the standard mandates. **Recommendation: arm E**, as a
> §2 calibration — which is exactly the calibration §2 says it is waiting for.
> Not adopted here: changing an approved constant is the author's call, and
> `base_size_uses_body` stays default FALSE either way.

## Acceptance status

| body-rule approval gate | result |
| --- | --- |
| 1. golden M15 case passes | **YES** |
| 2. structural arrival gives DBD | **YES** |
| 3. formation ownership reaches FINAL authority | **YES** |
| 4. P5/P8 subordinate behaviour correct | **YES** — suppressed via `suppressed_record_ids`, history before activation preserved |
| 5. H3 huge-wick case resolved by existing doctrine | **YES** — §3 governs it; not separable by size |
| 6. real-host sample review acceptable | **YES, with a caveat** — all 12 pass every unchanged gate and fall in a bounded band; no approved corpus exists to compare against |
| 7. batch == incremental | **YES** |
| 8. full suite green | **YES** |

**FORMATION OWNERSHIP INTEGRATION: approved.**

**BODY-SIZE BASIS: `default remains FALSE`.** Gates 1–8 pass, but gate 6 rests
on an absent corpus and Part C shows the switch contradicts §2 as written. That
is an author decision, not one to take by passing a checklist.
