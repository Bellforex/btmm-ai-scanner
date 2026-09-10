# H4 POI QUALIFICATION + FRESHNESS CORRECTION REPORT

Branch `rc3-poi-semantics-dev`, based on the closed RC2 release commit
`bec3ed82273acb81f42458e04f756fdbc4bb72b1`. RC2 is unmodified.

**Headline.** The author's two H4 reference formations are **not** separated by
the 2x size rule. Both satisfy it, on the authoritative metric and on the
alternative. They are separated cleanly by **freshness**: the lower example was
consumed by the very next bar and has been stale for 35 days; the upper example
stayed untouched for 36 bars. Every one of the 8 zones RC2 is drawing on H4
right now has already been reacted to.

---

## A — VALIDATION HOLD

| # | Item | State |
| --- | --- | --- |
| 1 | Materiality process | **STOPPED** (task `b97i1nzcl`); 0 python processes remained |
| 2 | Characterization results | **UNOPENED** — `m5_materiality_result.json` was never written, so there is no aggregate to quarantine; `BTRC_V1_V1A_CHARACTERIZATION_SUMMARY.md` inspected by metadata only (sha256 `2dd40714…c99f57`, 1104 bytes, mtime Sep 10 04:47) |
| 3 | OOS | **UNOPENED** |

No A/B/C classification was made. The materiality implementation and its 17
tests are preserved untouched.

---

## B — H4 REFERENCES

Identification was mechanical, not visual. RC2's live drawing store on the H4
host holds exactly two bullish-engulfing zones, and their labels and geometry
were read straight out of the study's own primitives. They match the author's
descriptions on every stated axis: earlier/lower versus later/upper, and the
later one sits immediately after the Aug 26 → Sep 2 decline from 4640 to 4301.

Source data: `artifacts/rc3_h4/FX_XAUUSD_H4_LIVE_20260910.csv`, sha256
`9dd9ce5f…65f837c`, 299 confirmed FXCM H4 bars captured live from FX:XAUUSD on
account bellcare1994, chart `6cu1b2O7`. No OANDA, no screenshot-derived prices.

### Reference A — lower / earlier

| # | Field | Value |
| --- | --- | --- |
| 4 | Timestamps | source opens 2026-08-05 18:00Z, departure opens 2026-08-05 22:00Z and closes 2026-08-06 02:00Z |
| 5 | Source OHLC | 4250.18 / 4268.13 / 4243.08 / 4247.07 |
| 6 | Departure OHLC | 4247.07 / 4302.67 / 4245.48 / 4286.39 |
| 7 | Body ratio | 39.32 / 3.11 = **12.6431** |
| 8 | Range ratio | 57.19 / 25.05 = **2.2830** |
| 9 | Current detector | PASS, registry created, tier STANDARD, zone 4243.08–4268.13, availability 2026-08-06 02:00Z |
| 10 | Corrected verdict | **Unchanged on size. Terminal on freshness** — mitigated 2026-08-06 02:00Z, the first bar after availability |

Departure close sits at 0.7153 of its own range; body efficiency 0.6875.

### Reference B — upper / later

| # | Field | Value |
| --- | --- | --- |
| 11 | Timestamps | source opens 2026-09-02 06:00Z, departure opens 2026-09-02 10:00Z and closes 2026-09-02 14:00Z |
| 12 | Source OHLC | 4319.90 / 4331.58 / 4304.77 / 4308.47 |
| 13 | Departure OHLC | 4308.47 / 4385.47 / 4301.64 / 4385.25 |
| 14 | Body ratio | 76.78 / 11.43 = **6.7174** |
| 15 | Range ratio | 83.83 / 26.81 = **3.1268** |
| 16 | Current detector | PASS, registry created, tier STRONG, zone 4304.77–4331.58, availability 2026-09-02 14:00Z |
| 17 | Corrected verdict | **VALIDATED**, and fresh for 36 bars until first contact on 2026-09-10 10:00Z |

Departure close sits at 0.9974 of its own range; body efficiency 0.9159.

---

## C — SIZE RULE

| # | Item | Answer |
| --- | --- | --- |
| 18 | Authoritative size metric | **FULL CANDLE RANGE** (high − low) |
| 19 | Threshold | **2.0** standard, **3.0** strong |
| 20 | Ambiguity | **FALSE** — `ENGULFING_SIZE_METRIC_DECISION_REQUIRED = FALSE` |

Four independent sources agree and none dissents:

- `knowledge/MEASUREMENT_STANDARDS.md` §2: *Size Ratio = Key Candle Total Range
  ÷ Reference Candle Total Range*.
- `knowledge/poi_rules/price_action/bullish_engulfing.md`, Candle-size
  requirement: *Size Ratio (Total Range) >= 2.0 (standard) / >= 3.0 (strong)*.
- `PHASE_1B_AUTHOR_DECISION_REGISTER.md` §GROUP3-D1/D2, recorded
  author-approved final.
- Both implementations already compute it this way, in `poi/engulfing.py` and
  in the RC2 Pine detector block.

### The rule does not do what the campaign expects of it

This is the finding that changes the plan, so it is stated plainly.

| Axis | Reference A | Reference B | Separates them? |
| --- | --- | --- | --- |
| Total-range ratio vs 2.0 | 2.2830 PASS | 3.1268 PASS | no |
| Body ratio vs 2.0 | 12.6431 PASS | 6.7174 PASS | no, and it ranks A **above** B |
| Body engulfment | true | true | no |
| Full-range (wick) engulfment | **false** | **true** | **yes** |
| First reaction after availability | **+1 bar** | +36 bars | **yes** |

Phase 5 asks that A fail and B pass. No threshold set at 2.0 on either metric
produces that. A threshold between 2.28 and 3.13 would, but choosing one would
be exactly the outcome-tuning the brief forbids, so none was chosen.

Two axes do produce the author's split without inventing a number, and both are
already written down somewhere authoritative:

**Option 1 — freshness only.** Already an explicit requirement of this same
brief (Phase 9). Needs no change to qualification at all. A is rejected because
price consumed it 35 days ago, which is also why it looks wrong on the chart.

**Option 2 — freshness plus mandatory full-range engulfment.** The knowledge
base already describes this clause: *"a stronger version also engulfs the
previous candle's entire range including wicks"*, recorded under Confirmation
conditions and Wick treatment. It is currently optional by explicit statement:
*"this is not required for the baseline valid pattern."* Promoting it to
mandatory is a real author decision, so it is implemented but not enabled.

> **AUTHOR DECISION REQUIRED — `ENGULFING_QUALIFICATION_PREDICATE`.**
> Choose `qualify_frozen` (Option 1) or `qualify_with_range_engulfment`
> (Option 2). Both are implemented and tested. No default was applied.

### One known deviation, currently inert

Frozen RC2 has no body-engulfment test at all — it checks the range ratio and
opposite candle colours only, which the Pine source already documents in a
comment. On this H4 window it changes nothing: all 15 detected bullish-engulfing
pairs pass body engulfment anyway. Reported for completeness, not proposed as
the fix.

---

## D — GEOMETRY

| # | Item | Value |
| --- | --- | --- |
| 21 | Reference A canonical zone | top **4268.13**, bottom **4243.08** |
| 22 | Reference B canonical zone | top **4331.58**, bottom **4304.77** |
| 23 | Source-candle mapping | the **first (engulfed, smaller, bearish) candle's full high-to-low range** |
| 24 | Old mapping defect count | **0** |

The five candidate geometries were compared against what RC2 actually draws:

| Candidate | Reference A | Reference B |
| --- | --- | --- |
| A. source candle full high–low | 4243.08–4268.13 | 4304.77–4331.58 |
| B. source candle body only | 4247.07–4250.18 | 4308.47–4319.90 |
| C. departure candle high–low | 4245.48–4302.67 | 4301.64–4385.47 |
| D. union of both | 4243.08–4302.67 | 4301.64–4385.47 |
| E. what RC2 draws | 4243.08–4268.13 | 4304.77–4331.58 |

E equals A in both cases, which is what GROUP3-D1 specifies. Read directly from
the study's box primitives, the drawn top and bottom are bit-identical to the
canonical POI bounds — no padding, no midpoint expansion, no union, no ATR
enlargement. **Phase 8's requirement already holds in RC2.** The geometry
complaint in the brief is not reproducible on the engulfing family; the zones
that look wrong are wrong because they are stale, not because they are
mis-anchored.

Two of the eight displayed zones are wick-only families (pressure wick, hammer,
shooting star) whose bounds are a documented subset of the source candle rather
than its full range. That is their specification, not a defect.

---

## E — FRESHNESS

| # | Item | Value |
| --- | --- | --- |
| 25 | Current active POIs (H4, frozen P3) | **173** |
| 26 | Already reacted among them | **161** |
| 27 | New fresh POIs | **12** |
| 28 | Mitigated count | **161** (plus 0 invalidated) |
| 29 | First-touch rule | as specified below |

**Reaction contract.** A validated POI becomes MITIGATED on the first confirmed
bar strictly after its availability bar whose range intersects the POI
interval, where intersection is `bar.high >= poi.bottom and bar.low <= poi.top`.
Both comparisons are inclusive, so a boundary touch counts. The availability bar
never consumes its own POI. A POI whose far boundary is cleared by a bar that
never touches the zone at all becomes INVALIDATED instead; on this H4 window
that case never occurs.

**States.** CANDIDATE, VALIDATED_FRESH, MITIGATED, INVALIDATED. Terminal states
are terminal and are never reopened by later bars. Registry identity, both
timestamps, geometry and the terminal reason are all preserved — mitigation
removes a POI from the *fresh and eligible* set, it never deletes evidence.

### The eight zones RC2 is drawing on H4 right now

Read live from the study's drawing primitives on 2026-09-10, then resolved
against the captured bars.

| Source bar (UTC) | Label | Top | Bottom | First reaction | State |
| --- | --- | --- | --- | --- | --- |
| 2026-08-05 18:00 | BUY OB + BULL ENGULF | 4268.13 | 4243.08 | 2026-08-06 02:00, +1 bar | reacted |
| 2026-08-28 18:00 | BEAR PRESSURE | 4472.13 | 4456.77 | 2026-08-30 22:00, +1 bar | reacted |
| 2026-09-02 06:00 | BUY OB + BULL ENGULF • STRONG | 4331.58 | 4304.77 | 2026-09-10 10:00, +36 bars | reacted |
| 2026-09-04 10:00 | SHOOTING STAR • STRONG | 4448.92 | 4416.51 | 2026-09-04 14:00, +1 bar | reacted |
| 2026-09-07 06:00 | HAMMER | 4402.65 | 4381.04 | 2026-09-07 10:00, +1 bar | reacted |
| 2026-09-07 10:00 | SHOOTING STAR | 4419.56 | 4406.95 | 2026-09-07 14:00, +1 bar | reacted |
| 2026-09-09 02:00 | BEAR PRESSURE | 4412.75 | 4398.83 | 2026-09-09 06:00, +1 bar | reacted |
| 2026-09-09 14:00 | EVENING STAR • STRONG | 4431.74 | 4375.13 | 2026-09-10 02:00, +1 bar | reacted |

**Displayed fresh: 0. Displayed already-reacted: 8.** This is the lifecycle
defect, measured rather than asserted.

Six of the eight were consumed by the very next bar. That is expected for
single-candle reversal families, whose zone is a wick the market is usually
still trading inside when the next bar opens, and it is the strongest argument
that the fresh/reacted distinction is what the chart has been missing.

Applying the contract to the whole H4 registry takes the active universe from
**173 to 12**. The survivors are 4 buy fair-value gaps, 2 buy order blocks, 2
bullish engulfings, 2 sell fair-value gaps, 1 morning star and 1 evening star.

Twelve fresh POIs still exceeds the visual capacity of 8, so capacity remains
binding and proximity selection still does real work. **No capacity change is
proposed.**

### Per-type behaviour across the whole window

Fourteen of the eighteen P3 classes occur here. Base rally, support zone,
resistance zone and sell-to-buy candle produce no instance in this window, so
their first-reaction behaviour is untested by this data.

| POI type | n | fresh | mitigated | invalidated | median bars to first reaction |
| --- | --- | --- | --- | --- | --- |
| BASE_DROP | 2 | 0 | 2 | 0 | 7 |
| BEARISH_ENGULFING | 9 | 0 | 9 | 0 | 3 |
| BEARISH_PRESSURE_WICK | 16 | 0 | 16 | 0 | 1 |
| BULLISH_ENGULFING | 15 | 2 | 13 | 0 | 2 |
| BULLISH_PRESSURE_WICK | 5 | 0 | 5 | 0 | 4 |
| BUY_FAIR_VALUE_GAP | 40 | 4 | 36 | 0 | 2 |
| BUY_ORDER_BLOCK | 15 | 2 | 13 | 0 | 2 |
| BUY_TO_SELL_CANDLE | 1 | 0 | 1 | 0 | 1 |
| EVENING_STAR | 10 | 1 | 9 | 0 | 1 |
| HAMMER | 6 | 0 | 6 | 0 | 1 |
| MORNING_STAR | 6 | 1 | 5 | 0 | 1 |
| SELL_FAIR_VALUE_GAP | 32 | 2 | 30 | 0 | 1 |
| SELL_ORDER_BLOCK | 7 | 0 | 7 | 0 | 6 |
| SHOOTING_STAR | 9 | 0 | 9 | 0 | 1 |
| **total** | **173** | **12** | **161** | **0** |  |

Every single-candle family has a median of one bar, which is the quantitative
form of the observation above: their zones are wicks price has not finished
trading through.

---

## F — VISUAL

| # | Item | State |
| --- | --- | --- |
| 30 | Bullish colour | **NOT IMPLEMENTED** — RC2 draws neutral gray fill at 92% with a directional border, an author decision frozen during the V2 campaign; Phase 16 reverses it to green fill |
| 31 | Bearish colour | **NOT IMPLEMENTED** — same, to light red |
| 32 | Centered annotation | **NOT IMPLEMENTED** — labels are anchored at the zone origin outside the box; the box primitives already carry `horizontalTextAlignment: center` and `verticalTextAlignment: center` with empty text, so box-integrated text is available and is the safe route |
| 33 | Full names | **NOT IMPLEMENTED** — currently abbreviated, e.g. `H4 • BUY OB + BULL ENGULF • STRONG` |
| 34 | Future extension | **NOT IMPLEMENTED** — every drawn box reads `extend: "n"` with `right` pinned to the current bar |
| 35 | Reacted zones hidden | **NOT IMPLEMENTED** — see section E |

All six are Pine presentation work in the RC3 DEV script, and all six are
blocked behind the qualification decision in section C, because the script has
to be written once against the approved semantics rather than twice.

---

## G — H4 SUPPORT

| # | Item | Result |
| --- | --- | --- |
| 36 | H4 runtime | **PASS** — RC2 + P6 DEV on host 240, `isFailed` false, `isCompleted` true, 8 boxes / 8 labels / 2 tables, zero RE10110, RE10041 or RE10045 |
| 37 | H4 reload | **NOT RUN** |
| 38 | H4 cold boot | **NOT RUN** |
| 39 | H4 support verdict | **NOT YET SUPPORTED** — runtime is clean, but the semantic correction that H4 support is conditioned on has not been made |

Warm-up, P3, P4, P5, P6 transport, P7 and P8 on H4 were not separately audited;
they belong to the RC3 acceptance run, which cannot start before the semantics
are fixed.

---

## H — SEMANTICS

| # | Item | Answer |
| --- | --- | --- |
| 40 | P3 changed | **FALSE so far** — no `src/` file was modified; the RC3 contract exists as a test-side oracle only |
| 41 | P5 impact | If mitigation gates eligibility, the H4 active-POI loop drops from 173 to 12 POIs. Every P5 evaluation of the other 161 stops after its first-reaction bar |
| 42 | P8 impact | See below |
| 43 | Old validation stale | **TRUE once RC3 changes P3** |

**P8, precisely.** Mitigation can ride the existing `POI_TERMINAL` event with
**no new event type and no payload change** — the payload is
`(event_type, poi_idx, bar_ms)` and mitigation simply makes `terminal` observe
true earlier. But the event's *meaning* broadens: today it means the frozen P5
terminal rule fired, and afterwards it would also mean price touched the zone,
with no way for a consumer to tell the two apart from the event alone. On this
H4 window that is 161 additional `POI_TERMINAL` events against a current 12.

> **AUTHOR DECISION REQUIRED — `P8_MITIGATION_EVENT_REPRESENTATION`.**
> Either accept the broadened `POI_TERMINAL`, or add a distinguishing reason.
> Adding one changes the frozen P8 payload, so it was not invented here.

`POI_ACTIVATED` needs no change: a candidate that fails qualification is never
registered as a validated POI, so the event simply does not fire.

---

## I — TESTS

| # | Gate | Result |
| --- | --- | --- |
| 44 | Targeted RC3 lifecycle tests | **29 passed** (`tests/unit/test_p3_rc3_freshness_model.py`) |
| 45 | Full pytest | **4498 passed in 596s**, exit code 0 |
| 46 | Failures | **0** |
| 47 | ruff | clean on both new files, format and check |
| 48 | mypy | clean on the new oracle |
| 49 | `git diff --check` | clean |

The RC2 baseline was 4469 passed. The suite now reports 4498, exactly the 29
new tests and nothing else moved — which is the check that matters here, since
the RC3 contract lives entirely in test-side code and must not have disturbed
any frozen parity assertion.

The 29 tests pin the reaction contract (wick-only, body penetration, full
traversal, both boundary touches, clearing the zone entirely, gap invalidation,
terminal states staying terminal), the qualification boundary at exactly 2.0 and
either side of it, and the two mutants the brief names: same-bar
self-mitigation and an ignored boundary touch. They also pin both real FXCM
reference formations as permanent fixtures, including the fact that body ratio
ranks them the wrong way round.

Not yet built, because they need the approved semantics first: the Pine port
differential, the geometry-swap and union-substitution mutants, the
box-stops-at-current-bar and label-outside-box mutants, and the all-18-type
geometry regression.

**Fixture persistence.** `artifacts/` is gitignored by project convention, as
every prior real capture has been, so the capture itself lives at
`artifacts/rc3_h4/FX_XAUUSD_H4_LIVE_20260910.csv` with its sha256 recorded in
section B, and the durable form of the author-reference fixture is the exact
OHLC of both formations plus their following bars, embedded as constants in the
test module. Those constants are what a future run is checked against.

---

## J — RELEASE

| # | Item | Value |
| --- | --- | --- |
| 50 | RC2 unchanged | **TRUE** — sha256 `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f`, verified after branch creation |
| 51 | RC3 DEV path | **NOT CREATED** — blocked on the section C decision |
| 52 | RC3 promotion performed | **FALSE** |

---

## K — SAFETY

| # | Item | Value |
| --- | --- | --- |
| 53 | push | FALSE |
| 54 | merge | FALSE |
| 55 | publish | FALSE |
| 56 | broker | FALSE |
| 57 | live trading | FALSE |

---

## DISCLOSED LIMITATIONS

- **Reference identification is inferential, not pixel-matched.** No screenshot
  reached this session. The two zones were identified because RC2's live H4
  drawing store contains exactly two bullish-engulfing zones and they match
  every stated locator: earlier/lower versus later/upper, and the later one
  follows the Aug 26 → Sep 2 decline. If the author meant a different pair,
  every number in section B changes and section C should be re-derived.
- **FXCM revised its own history.** 38 of 277 overlapping H4 bars differ between
  the September 6 capture and the September 10 one, all sub-cent wick
  adjustments. One consequence is material: the 2026-09-03 formation's range
  ratio moved from 3.10 to 2.99, flipping it from STRONG to STANDARD without any
  code change. The live capture is treated as authoritative here.
- **The last H4 bar was still forming** and is excluded from every count.
- **Reference B's first reaction landed on 2026-09-10 10:00Z**, plausibly after
  the author's screenshot was taken. Under the proposed contract it is now
  mitigated too. That does not weaken the finding; it is what a working
  freshness rule looks like.
