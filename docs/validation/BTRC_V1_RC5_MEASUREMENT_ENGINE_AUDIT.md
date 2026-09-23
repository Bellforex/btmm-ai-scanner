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
