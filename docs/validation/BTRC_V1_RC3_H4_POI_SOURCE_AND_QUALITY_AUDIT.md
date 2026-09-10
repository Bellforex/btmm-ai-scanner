# RC3 H4 POI SOURCE + QUALITY AUDIT REPORT

Branch `rc3-poi-semantics-dev`, from `5e7705f58aebe2675b255b6049545b44151cfee0`.

**Headline, and it is a correction.** The previous audit identified the wrong
Reference A. Re-derived mechanically from the author's own drawn rectangle, the
lower golden is the **2026-08-06 18:00Z** formation, not 2026-08-05 18:00Z. Its
range ratio is **1.6105**, so the frozen 2.0 rule already rejects it. With the
correct pair, the existing single ratio produces exactly the split the author
expects, and **no new quality threshold is needed**.

The one real geometry defect is the drawn origin, and it affects all 18 POI
types through a single line. Zone top and bottom were never wrong.

---

## THE CORRECTION, IN FULL

The earlier report matched Reference A to the nearest *qualifying* bullish
engulfing and reported 2.2830 / 12.6431. That search was biased: it only ever
considered formations the detector already admitted, so it could not find a
golden that the detector rejects. Scoring **every** H4 candle against the drawn
band instead gives an unambiguous answer.

| Candidate for Reference A | Price error vs the drawn band | Left edge matches? |
| --- | --- | --- |
| **2026-08-06 18:00Z**, H 4251.26 L 4232.85 | **2.05** | **yes, exactly** |
| 2026-08-06 22:00Z | 9.96 | no |
| 2026-08-06 10:00Z | 24.09 | no |
| 2026-08-05 18:00Z (previously reported) | 29.15 | no, 6 bars early |

Two independent locators agree on 2026-08-06 18:00Z: the price band matches to
2.05 across both edges, and the rectangle's left edge is that candle's exact
opening time. The previously reported candidate matched neither.

Everything downstream of that identification in the prior report changes.
Reference B is unaffected and re-confirms at an error of 0.94.

---

## A — SOURCE MAPPING

| # | Reference A | Value |
| --- | --- | --- |
| 1 | Source timestamp | **2026-08-06 18:00Z** (closes 22:00Z) |
| 2 | Source OHLC | 4247.06 / 4251.26 / 4232.85 / 4239.43 |
| 3 | Current registry geometry | **none** — no `BULLISH_ENGULFING` record exists |
| 4 | Intended source geometry | top 4251.26, bottom 4232.85, left edge 2026-08-06 18:00Z |
| 5 | Geometry mismatch | **N/A** — nothing is registered to mismatch |

Departure: 2026-08-06 22:00Z, O 4239.43 H 4259.24 L 4229.59 C 4256.83.

The nearest registry entry overlapping that candle is a `HAMMER` at
4230.36–4266.96, availability 2026-08-06 14:00Z — a different type, a different
candle and a wider zone. That is what "the indicator currently recognizes/maps
it" was pointing at: an unrelated POI drawn across the same screen area, not an
engulfing POI at the marked geometry.

| # | Reference B | Value |
| --- | --- | --- |
| 6 | Source timestamp | **2026-09-02 06:00Z** (closes 10:00Z) |
| 7 | Source OHLC | 4319.90 / 4331.58 / 4304.77 / 4308.47 |
| 8 | Current registry geometry | top **4331.58**, bottom **4304.77**, availability 2026-09-02 14:00Z, tier STRONG |
| 9 | Intended source geometry | top 4331.58, bottom 4304.77, left edge 2026-09-02 06:00Z |
| 10 | Geometry mismatch | **FALSE for top/bottom** (delta 0.00 on both), **TRUE for the left edge** |

Departure: 2026-09-02 10:00Z, O 4308.47 H 4385.47 L 4301.64 C 4385.25.

### The detector already anchors to the right candle

Traced end to end for Reference B: `detect_engulfing` takes the pair
`(candles[i], candles[i+1])`, requires `candles[i]` bearish and `candles[i+1]`
bullish, and sets `zone_top = engulfed.high`, `zone_bottom = engulfed.low`. The
engulfed candle *is* the small opposite candle immediately preceding the
departure. Both deltas against the source candle's own high and low are exactly
zero. **P3 GEOMETRY DEFECT for top/bottom = FALSE.**

### The origin is the real defect, and it is shared

The registry already stores the right value. `candidate_event_time_utc` is the
source candle's opening time, carried into Pine as `poiCandTime`. The P7-Z
visual layer was reading `poiAvailTime` instead, in one shared assignment used
by every POI family. Measured across the 173-POI H4 registry:

| POI type | Bars the drawn left edge was late |
| --- | --- |
| Pressure wicks, hammer, shooting star | 1 |
| Both engulfings, both order blocks | 2 |
| Both fair value gaps, both stars, base drop | 3 |
| Buy-to-sell candle | 4 |

The offset is exactly each pattern's span, which is what a shared availability
anchor produces. **Fixed in this commit**, and confirmed live: the two
`BUY ORDER BLOCK + BULLISH ENGULFING` zones moved from bar 142 to 140 and from
139 to 137, the two stars moved 3 bars, the pressure wick moved 1 — matching the
predicted per-type offsets exactly.

The exact-geometry dedup key deliberately still uses availability, so grouping
behaviour is unchanged. Where a group mixes pattern lengths (3 of 24 groups on
this capture, always a star joining an engulfing pair), the drawn origin is the
earliest defining candle in the group.

### Conflict with a prior decision, declared

`BTRC_V1_P7Z_POI_VISUALIZATION_CLOSURE.md` chose the availability anchor
deliberately, arguing that a source-candle anchor "would draw as if the scanner
knew about the zone before it actually confirmed it". The new contract answers
that objection itself: the box is *drawn from* the source candle's open but only
*comes into existence* once the departure candle confirms, so no information
appears before its availability time. The change was made on that basis and the
prior decision is superseded, not ignored.

---

## B — CURRENT RATIOS

| # | Measure | Reference A | Reference B |
| --- | --- | --- | --- |
| 11, 12 | Range ratio | **1.6105 (FAIL)** | **3.1268 (PASS)** |
| 13, 14 | Body ratio | 2.2805 | 6.7174 |
| 15, 16 | Departure body efficiency | 0.5868 | 0.9159 |
| 17 | Departure / median of previous 20 | **0.8805** | **2.3057** |
| | Departure / median of previous 5 | 0.5707 | 2.4255 |
| | Departure / median of previous 3 | 0.6772 | 1.9089 |
| | Source range / body | 18.41 / 7.63 | 26.81 / 11.43 |
| | Departure range / body | 29.65 / 17.40 | 83.83 / 76.78 |
| | Source body efficiency | 0.4144 | 0.4263 |
| | Departure close position | 0.9187 | 0.9974 |
| | Body engulfment | true | true |
| | Full-range engulfment | true | true |

The brief asked for 3- and 5-bar medians. The project's own authoritative window
is **20** (`MEASUREMENT_STANDARDS.md`, Range Context Ratio), so all three are
reported and the 20-bar figure is the one that carries weight. On it, Reference
A's departure candle is *smaller* than the recent norm at 0.88×, while Reference
B's is 2.31× — the single most direct mechanical statement of why one reads as
displacement and the other does not.

---

## C — QUALITY

| # | Item | Answer |
| --- | --- | --- |
| 18 | Current single ratio sufficient | **TRUE**, for these two goldens |
| 19 | Authoritative features recovered | see below |
| 20 | Unresolved thresholds | see below |
| 21 | Reference A expected admission | **REJECT** — already rejected today |
| 22 | Reference B expected admission | **ADMIT** — already admitted today, tier STRONG |

### Phase 6 reversed

The brief asked me to reproduce A 2.2830 / B 3.1268 and conclude that a single
ratio is insufficient. Those numbers came from the misidentified Reference A, so
they cannot be reproduced and the conclusion drawn from them does not hold. With
the correct pair:

- **2.0 range ratio alone DOES distinguish the goldens.** A fails at 1.6105, B
  passes at 3.1268.
- **Body ratio alone would also rank them correctly** here (2.2805 against
  6.7174), so it does not invert as previously reported. It remains the wrong
  metric by project authority, but not for the reason given before.

No threshold was moved. None needs to be.

### What the repository already defines

| Measure | Where | Status |
| --- | --- | --- |
| Size Ratio on total range, 2.0 / 3.0 | Measurement Standard §2, engulfing knowledge file, GROUP3-D1/D2 | **FROZEN**, and gating for engulfing |
| Relative smallness ≤ 0.50× / ≤ 0.3333× | Small Candle Standard §2–3 | **FROZEN**, but algebraically the same 2×/3× relationship, so it adds no independent gate |
| Range Context Ratio vs median of previous 20 | Proxy Standard §1B | **FROZEN as a measurement**, and explicitly *"never automatically reject a pattern that already satisfies the book's relative-size rule"* — informational, not a gate |
| Body Efficiency | Proxy Standard §1C | **FROZEN as a measurement**, no threshold for engulfing |
| Bullish / Bearish Close Position | Proxy Standard §1D–E | same |
| Body engulfment | engulfing knowledge file, "Body treatment" | **FROZEN as the book's core rule**, and **not implemented** in RC2/RC3 |
| Full-range wick engulfment | same file, "Wick treatment" | **FROZEN as optional** — *"not required for the baseline valid pattern"* |
| Departure ≥ 2× largest base candle, closes outside base range | Base Standard §6 | **FROZEN but scoped to Base Rally/Drop**; §8 states it resolves no threshold for other POI types |

**Unresolved, by the project's own words:** the `price_activity_score` formula
and weights, and any hard pass/fail threshold for departure momentum evidence
(Proxy Standard §5, Base Standard §8). No engulfing-specific threshold exists
beyond 2.0 / 3.0.

**Nothing was invented.** No ATR threshold, body-efficiency threshold,
median-range multiplier or structure-break threshold was added.

---

## D — POPULATION

Source: the long genuine FXCM H4 capture, 5684 bars, 2023-01-02 to 2026-09-04.
Both golden candles are **byte-identical** between that capture and the live one,
so the wick-revision caveat does not touch them.

| # | Item | Value |
| --- | --- | --- |
| 23 | Bullish engulfing candidates (shape only) | **1411** |
| 24 | Bearish engulfing candidates | **1410** |
| 25 | Creation-time features measured | 12 continuous, 4 boolean |

Admitted by the frozen 2.0 rule: 205 bullish (14.5%), 208 bearish (14.8%).

| # 26, 27 — golden ranks within the 1411 bullish candidates | Ref A | pct | Ref B | pct |
| --- | --- | --- | --- | --- |
| Range ratio | 1.6105 | 76.7 | 3.1257 | 94.8 |
| Body ratio | 2.2805 | 69.0 | 6.7227 | 87.5 |
| Departure body efficiency | 0.5868 | 61.7 | 0.9169 | **97.7** |
| Source body efficiency | 0.4144 | 47.5 | 0.4263 | 49.3 |
| Range context vs median 20 | 0.8805 | **38.7** | 2.3057 | **94.8** |
| Departure / median 5 | 0.6772 | 24.3 | 2.4255 | 93.1 |
| Departure / median 3 | 0.6772 | 28.6 | 1.9089 | 87.0 |
| Departure close position | 0.9187 | 83.4 | 0.9984 | **99.3** |

Boolean features, with population base rates:

| Feature | Ref A | Ref B | Population true |
| --- | --- | --- | --- |
| Body engulfment | true | true | 52.1% |
| Full-range engulfment | true | true | 19.6% |
| Departure closes beyond source high | true | true | 34.7% |
| Creates a buy-side imbalance on the next bar | false | true | 16.6% |

**This explains the author's reading mechanically.** Reference B is top-5% on
three independent creation-time axes: how efficiently the departure candle
converts its range into body, how large that range is against the recent norm,
and where it closes within itself. Reference A is middling on all three and
*below* the recent norm on range context. No single boolean separates them —
both engulf on body and on wicks — but every continuous displacement measure
does, and they agree.

---

## E — LIFECYCLE

| # | Item | Status |
| --- | --- | --- |
| 28 | First-touch semantics retained | **TRUE**, unchanged from `5e7705f` |
| 29 | No-lookahead admission | **TRUE** — every feature above is computable at departure close; the one exception (next-bar imbalance) is labelled and never gated on |
| 30 | Stale zones excluded from release display | **TRUE** |
| 31 | Historical audit mode | **PARTIAL** — the identity mode below reports a POI's terminal state and reason, but a mitigated POI's box is still evicted, so an already-consumed zone cannot be re-drawn from source through mitigation |

Freshness is not used to decide whether a POI was valid at creation, which is
what keeps admission free of lookahead.

---

## F — VISUAL

| # | Item | Result |
| --- | --- | --- |
| 32 | Box derived from the canonical source candle | **TRUE** — top, bottom and now the left edge |
| 33 | Centered full name | **TRUE** |
| 34 | Future extension | **TRUE** — `extend: "r"` plus a bounded projected right edge |
| 35 | Bullish green | **TRUE** |
| 36 | Bearish red | **TRUE** |

### Phase 4 — identity audit mode, implemented

A DEV-only input, `DEV: show POI identity in zone`, default **off**. It replaces
the clean annotation with the POI's mechanical identity, adding no drawing
objects. Verified live:

```
ID 895
H4 BUY ORDER BLOCK + BULLISH ENGULFING
SRC 2026-08-05 06:00
AVL 2026-08-05 14:00
4153.11-4179.5
NONE
```

`SRC` and `AVL` being two bars apart is the origin fix visible in the annotation
itself. Release UI was restored to the clean name and the layout saved.

---

## G — IMPACT

| # | Item | Answer |
| --- | --- | --- |
| 37 | P3 geometry change required | **FALSE** — zone top/bottom already derive from the correct defining candle. The origin defect was in P7-Z and is fixed there |
| 38 | P3 qualification change ready | **NOT REQUIRED** — the frozen 2.0 rule already produces the author's expected split |
| 39 | Author decision still required | **TRUE**, but not for the goldens — see below |
| 40 | Affected POI types | **all 18**, through one shared left-edge assignment; all now anchor to the defining candle |

### The decision that is still open

Two things are separately defensible and neither is needed to satisfy the
goldens, so neither was implemented:

- **Body engulfment as a mandatory condition.** The knowledge file calls it the
  core rule and the detector does not test it. Adding it would take the bullish
  admitted set from 205 to 191 on the population. Reference A fails on size
  first either way.
- **A quality tier using already-frozen measurements.** Body efficiency, range
  context and close position separate the goldens cleanly and are all frozen as
  *measurements* with no thresholds. Range context additionally carries an
  explicit instruction never to gate on it, so promoting it would reverse a
  standing decision.

Distributions are in section D. No threshold should be picked from two examples.

---

## H — VALIDATION

| # | Item | Value |
| --- | --- | --- |
| 41 | V1-A paused | **TRUE** |
| 42 | Characterization unopened | **TRUE** |
| 43 | OOS unopened | **TRUE** |

---

## I — SAFETY

| # | Item | Value |
| --- | --- | --- |
| 44 | RC1 unchanged | **TRUE** — `143c0f88…64c54` |
| 45 | RC2 unchanged | **TRUE** — `381f2fc2…7f36cc3f` |
| 46 | RC3 promoted | **FALSE** |
| 47 | push | FALSE |
| 48 | merge | FALSE |
| 49 | publish | FALSE |
| 50 | live trading | FALSE |

---

## LIMITATIONS

- **Phase 19's annotated screenshot was not produced.** The chart canvas does not
  paint in a tab this session opens, so the source and departure candles could
  not be highlighted visually. The mechanical comparison in section A is
  complete and is the stronger evidence; the picture is not.
- **The population's wicks are the older capture's.** Both goldens are identical
  across captures, but other candidates may carry pre-revision wicks, which can
  move a marginal range ratio slightly. It cannot move a 1.61 or a 3.13.
- **Bearish engulfing was audited symmetrically by construction** — the detector
  mirrors the same code path and the population counts are near-identical — but
  no bearish golden exists to check against.
- **The next-bar imbalance feature is not creation-time information.** It is
  reported at 16.6% population incidence for context only and must never gate
  admission.
