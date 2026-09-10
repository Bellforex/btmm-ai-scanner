# RC3 POI FRESHNESS SEMANTIC IMPLEMENTATION REPORT

Branch `rc3-poi-semantics-dev`, based on `1a3dc9b88ecb09535a1d7c11d1199085d0afa1f4`
(itself based on the closed RC2 release commit `bec3ed82273acb81f42458e04f756fdbc4bb72b1`).

**Headline.** The frozen 2.0 total-range qualification is untouched. Freshness is
now a real lifecycle axis in the canonical Python engine, ported to Pine, and
live on H4. On the genuine FXCM H4 capture it takes the active POI universe from
173 to 12 and removes 5692 of 8197 P5 evaluations. Both author references behave
exactly as the contract says they must, and the reason they differ is time, not
size.

---

## A — AUTHOR DECISIONS

| # | Item | Value |
| --- | --- | --- |
| 1 | Qualification threshold retained | **2.0** (and 3.0 strong tier, unchanged) |
| 2 | Size metric | **FULL CANDLE RANGE** |
| 3 | Wick engulfment mandatory | **FALSE** |
| 4 | Freshness first-touch enabled | **TRUE** |
| 5 | `POI_TERMINAL` retained | **TRUE** |
| 6 | `terminal_reason` added | **TRUE** (`MITIGATED` / `INVALIDATED`) |

No detector was re-tuned. `detect_engulfing`, its thresholds, its zone geometry
and its availability rule are byte-identical to RC2.

---

## B — H4 REFERENCES

Both were re-derived from the genuine capture through the real engine, not from
a model of it. Reference B was additionally confirmed against the author's own
manual rectangle read out of the chart's drawing objects: the marked band is
4305.32–4331.97 against the registry's 4304.77–4331.58, a hand-drawn error of
0.94 total across both edges.

| # | Reference A — lower / earlier | Value |
| --- | --- | --- |
| 7 | Creation verdict | **CREATED**, `BULLISH_ENGULFING` tier STANDARD, plus a `BUY_ORDER_BLOCK` at identical geometry |
| 8 | First reaction | **2026-08-06 06:00Z, +1 bar after availability** |
| 9 | Terminal reason | **MITIGATED** |

| # | Reference B — upper / later | Value |
| --- | --- | --- |
| 10 | Creation verdict | **CREATED**, `BULLISH_ENGULFING` tier STRONG, plus a `BUY_ORDER_BLOCK` at identical geometry |
| 11 | First reaction | **2026-09-10 14:00Z, +36 bars after availability** |
| 12 | Terminal reason | **MITIGATED** |

Both reproduce the previously measured +1 / +36 exactly under canonical replay,
so no diagnosis was required.

### One thing the author needs to know

Phase 19 asks that Reference B be *shown* on the live chart. It is not, and that
is the contract working rather than failing. Price traded back into
4304.77–4331.58 on the H4 bar opening **2026-09-10 10:00Z** (low 4324.02 against
a zone top of 4331.58), which is today. Under the first-reaction rule the author
specified, that consumes it. Reference B was fresh and visible for 36 bars and
stopped being fresh a few hours before this build went live.

---

## C — LIFECYCLE

Measured on `artifacts/rc3_h4/FX_XAUUSD_H4_LIVE_20260910.csv`, 299 confirmed
FXCM H4 bars, sha256 `9dd9ce5f…65f837c`.

| # | Item | Value |
| --- | --- | --- |
| 13 | RC2 active count | **173** |
| 14 | RC3 fresh-active count | **12** |
| 15 | Mitigated count | **161** |
| 16 | Invalidated count | **0** |
| 17 | Stale displayed before | **8 of 8** |
| 18 | Stale displayed after | **0 of 8** |

Invalidated is zero for a reason worth stating: every POI that eventually broke
down had already been touched first, so mitigation took the terminal cause. That
is the precedence rule doing its job, not an unreachable branch — the unit tests
construct the gap case that reaches `INVALIDATED` and pin it.

### The contract as implemented

`resolve_terminal` in `poi/lifecycle.py` is the single ranking function. Both the
batch walk and the incremental replay path call it, which is what stops them
drifting: they disagree about how to *find* the two candidate times, never about
how to rank them.

- Contact is `bar.high >= poi.bottom and bar.low <= poi.top`, inclusive on both
  sides, so a wick stopping exactly on a boundary counts.
- Scanning starts strictly after the POI's own availability bar. That bar
  created the POI; letting it consume the POI would make every POI dead on
  arrival.
- Whichever cause lands first in bar order wins and is never replaced. A POI
  touched at bar 3 and genuinely invalidated at bar 40 stays `MITIGATED`, and the
  invalidation transition is still recorded as evidence.
- No time expiry was introduced. A fresh POI stays fresh indefinitely.

### Registry preservation

`fresh_active` is a flag, not a deletion. Every mitigated POI keeps its
`record_id`, type, direction, timeframe, geometry, availability time,
`mitigation_time_utc`, `terminal_time_utc`, `terminal_reason`, full transition
list, tap count and age. A test asserts the breach evidence survives mitigation.

---

## D — P5

| # | Item | Value |
| --- | --- | --- |
| 19 | Changed observations | **8197 → 2505** POI evaluations across the capture; 5692 removed |
| 20 | Post-mitigation exclusion | **enforced**, from the bar after the terminal bar |
| 21 | Terminal-bar ordering | **unchanged** |

The active-loop model gained `resolve_eligible_and_next_rc3`, which substitutes
`not fresh_active` for "the lifecycle status is genuine invalidation" and routes
through the same set algebra as the RC2 entry point. A test asserts the two agree
whenever the terminality inputs agree, in both directions.

The off-by-one the brief warned about is covered explicitly: a POI that mitigates
on the current bar is still in the eligible set for that bar and is absent from
the next one. A separate test shows the naive "filter out anything not fresh"
implementation returns the empty set where the contract returns that POI.

First divergence between RC2 and RC3 eligibility on this capture: bar 5,
2026-07-03 14:00Z, 2 POIs against 1. Final-bar eligible set: 45 against 14.

---

## E — P8

| # | Item | Value |
| --- | --- | --- |
| 22 | `MITIGATED` terminal events | **161** |
| 23 | `INVALIDATED` terminal events | **0** |
| 24 | Duplicate terminal events | **0** |
| 25 | Terminal reason verified | **TRUE** |

`POI_TERMINAL` is kept as the event family and now carries `terminal_reason`.
Dedup is unchanged: `event_key` stays `(event_type, poi_idx, bar_ms)`, so the
reason is payload rather than identity, and a POI that stays terminal for the
rest of the session fires exactly one terminal event. Priming on an
already-terminal POI announces nothing.

`PoiSnapshot` now rejects a non-terminal POI that carries a reason. A terminal
POI with no reason defaults to `INVALIDATED`, which is not a fudge: under RC2
that was the only way to become terminal, so every pre-RC3 fixture keeps its
exact meaning instead of being silently reinterpreted.

### Event volume, corrected

The earlier audit estimated roughly 161 *additional* terminal transitions. That
was an overestimate, because it assumed RC2 emitted none. RC2 emits **128** on
this capture. The real change is:

| | RC2 | RC3 |
| --- | --- | --- |
| `POI_TERMINAL` events | 128 | 161 |
| of which mitigation | 0 | 161 |
| of which invalidation | 128 | 0 |

So 33 events are genuinely new, and 128 change both their cause and, usually,
their timing — they now fire when price first reaches the zone rather than when
the zone later breaks down. No mitigation event was suppressed to reduce volume.

---

## F — VISUAL

Read directly from the live study's box primitives on H4, not from pixels.

| # | Item | Result |
| --- | --- | --- |
| 26 | Centered annotation | **TRUE** — every box carries `horizontalTextAlignment: center` and `verticalTextAlignment: center` |
| 27 | Full naming | **TRUE** — e.g. `H4 • BUY ORDER BLOCK + BULLISH ENGULFING`, `H4 • BEARISH PRESSURE WICK`; no tier text in any zone label |
| 28 | Bullish green | **TRUE** — fill and border colour index `424718156` / `3209736012` on all four bullish zones |
| 29 | Bearish red | **TRUE** — `423966450` / `3208984306` on all four bearish zones |
| 30 | Future extension | **TRUE** — every box reports `extend: "r"` |
| 31 | Canonical geometry | **TRUE** — drawn top/bottom equal the registry's, unchanged from RC2 |
| 32 | Stale zones hidden | **TRUE** — 8 boxes, all fresh; 0 labels |

The separate label object is gone. The annotation is now the box's own text,
which removes the whole class of defect the V2 campaign kept hitting — labels
drifting to `time_close`, piling onto one x coordinate, or disappearing when a
zone's origin fell outside the loaded window — because the text can no longer be
positioned independently of the rectangle. It also halves the drawing objects per
zone.

**One correction made during live acceptance.** `extend.right` alone was not
enough. Pine lays the centered text out inside `left … right`, and `right` was
still `time_close`, so a zone created on the current bar had a zero-width span to
centre in and its text rendered jammed against the edge. The right edge is now
carried a fixed number of bars past the last close (`p7zProjectBars`, default 12)
*and* `extend.right` is kept. This is the "bounded implementation with equivalent
future projection" the brief allows, and it is presentation only — the semantic
end of a POI's life is still its first reaction, never a bar count.

---

## G — HOSTS

Live on account **bellcare1994**, provider **FXCM**, symbol **FX:XAUUSD**, chart
`6cu1b2O7`, studies RC3 DEV + P6 DEV.

| # | Host | `isFailed` | Boxes | RE10110 | RE10041 | RE10045 | Settle |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 33 | M1 | false | 8 | 0 | 0 | 0 | 20.0 s |
| 34 | M5 | false | 8 | 0 | 0 | 0 | 15.0 s |
| 35 | M15 | false | 8 | 0 | 0 | 0 | 16.0 s |
| 36 | H1 | false | 8 | 0 | 0 | 0 | 17.0 s |
| 37 | H4 | false | 8 | 0 | 0 | 0 | 11.0 s |

| # | Cold boot | Result |
| --- | --- | --- |
| 38 | M5, fresh tab | **PASS** — reconstructed RC3 + P6 DEV, 8 boxes / 0 labels / 2 tables, settled 1257 ms, held on re-read after 34 s |
| 39 | H4, fresh tab | **PASS** — same, settled 8127 ms |

**H4 support verdict: candidate, not yet declared supported.** Runtime, reload,
cold boot and object lifecycle pass. Warm-up, P4, P6 transport and a full P7
audit on H4 were not separately exercised, and no author visual sign-off exists
yet.

---

## H — PARITY

| # | Item | Status |
| --- | --- | --- |
| 40 | New P3 lifecycle authority | **NOT GENERATED** |
| 41 | New P5 authority | **NOT GENERATED** |
| 42 | New P8 authority | **NOT GENERATED** |
| 43 | P6 unchanged if proven | **UNPROVEN** — no P6 file changed, but no mechanical proof was run |

RC2's P3/P5/P8 digests are **not** claimed as RC3 evidence and must not be. RC3
changes the active-POI universe, so every count downstream of it changes by
construction.

### A disclosed cost in the RC3 DEV build

The RC3 additions pushed the compiled script to 101947 tokens against
TradingView's limit of 100256. Three `debugMode`-gated log statements were
removed to fit: **P5EVAL**, **P9TRACE** and **P7DIAG**. None computes anything;
none affects what the study draws or decides. The **P8EVENT / P8PRIME** stream
was kept deliberately, because RC3's terminal-cause evidence depends on it.

The consequence is concrete: an RC3 P5 or P9 parity capture cannot be taken from
this build. Restoring those lines requires finding roughly 500 source tokens
elsewhere first. This is recorded as a limitation, not as a solved problem, and
nothing was masked — `calc_bars_count` is still 1800 and no threshold moved.

---

## I — QUALITY

| # | Gate | Result |
| --- | --- | --- |
| 44 | Targeted RC3 tests | **73 passed** — 27 lifecycle, 17 downstream, 29 oracle |
| 45 | Full pytest | **4542 passed in 629 s**, exit code 0 |
| 46 | Failures | 0 |
| 47 | ruff (changed files) | clean |
| 48 | mypy `src` | clean, 138 files |
| 49 | `git diff --check` | clean |

The RC2 baseline was 4469 and the prior RC3 audit commit took it to 4498. It is
now 4542: the 44 new tests in this commit and nothing else moved.

The incremental-vs-batch equivalence suite deserves a note. Adding the two new
terminal times to the batch walk immediately broke it at every prefix, because
the event-driven scanner reaches the same semantics through three other code
paths — the resumable cursor, its bounded no-op fast-forward, and the dormant
cursor adapter — each of which rebuilds the cursor field by field. All three had
to carry the new state before the suite went green again. That suite caught a
real divergence rather than a theoretical one.

---

## J — RELEASE

| # | Item | Value |
| --- | --- | --- |
| 50 | RC1 unchanged | **TRUE** — sha256 `143c0f88…64c54` |
| 51 | RC2 unchanged | **TRUE** — sha256 `381f2fc2…7f36cc3f` |
| 52 | RC3 DEV source | `tradingview/btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine`, sha256 `49193e4dc214d04825b972011974402131413e33d36d5945427ca3cda07d2fd3`, 6742 lines |
| 53 | RC3 promoted | **FALSE** |

The accepted V2 DEV source is also unchanged (`bef64353…5d298f34`). On
TradingView the script was created via **Create new → Indicator** and saved under
its own name, so RC1, RC2 and V2 DEV were never the save target.

**One chart-state change was made and is reversible.** The Basic plan caps two
studies per chart, so RC2 was removed from chart `6cu1b2O7` and RC3 DEV attached
in its place, keeping P6 DEV. The layout was then saved so the cold-boot tests
could reconstruct it. Re-adding RC2 restores the previous state; the RC2 script
itself was never opened for editing.

---

## K — VALIDATION

| # | Item | Value |
| --- | --- | --- |
| 54 | Prior materiality execution stale for final validation | **TRUE** |
| 55 | Characterization summary unopened | **TRUE** |
| 56 | OOS unopened | **TRUE** |
| 57 | Materiality infrastructure preserved | **TRUE** — `tests/parity_support/v1a_m5_materiality.py` and its 17 tests untouched |

V1-A0 must be rerun against RC3 semantics once RC3 freezes. It cannot be
inherited: RC3 changes which POIs P5 evaluates at all.

---

## L — SAFETY

| # | Item | Value |
| --- | --- | --- |
| 58 | push | FALSE |
| 59 | merge | FALSE |
| 60 | publish | FALSE |
| 61 | broker | FALSE |
| 62 | live trading | FALSE |

---

## WHAT IS NOT DONE

Stated plainly so none of it is mistaken for finished.

- **No live author visual sign-off.** The chart canvas does not paint in a tab
  this session opens, so the acceptance above is read from the study's own
  drawing primitives rather than from a rendered screenshot. The primitives are
  the stronger evidence for geometry, colour and text alignment; they say
  nothing about whether the author finds the result readable.
- **No all-18-type geometry regression run.** No detector changed, so no
  geometry can have moved, but the regression itself was not executed.
- **No RC3 parity artifacts** for P3 lifecycle, P5 or P8, and no mechanical
  proof that P6 is unaffected.
- **No live P8 terminal-event capture** confirming the Pine `terminal_reason`
  matches the Python oracle on real data. The Pine transcription mirrors
  `resolve_terminal` statement for statement and was reviewed, but it has not
  been differentiated against the oracle on a real capture.

  What does exist is a partial agreement check, worth recording because it was
  not designed for: three of the eight zones the live Pine build draws on H4 are
  also in the twelve the Python replay calls fresh, with bit-identical geometry
  and matching combined names — the morning star at 4026.54–4040.90 and the two
  order-block-plus-engulfing pairs at 4074.70–4088.96 and 4153.11–4179.50. The
  other five originate before the 299-bar capture window, since the study reads
  1800 H4 bars. Two independent implementations agreeing on which zones survived
  is evidence, but it is three cases, not a differential.
- **Reference A's manual rectangle does not match cleanly.** The author's lower
  hand-drawn band is 4231.18–4250.88 against the registry zone 4243.08–4268.13,
  offset by about two thirds of the zone's height, where the upper one matched to
  0.94. The identification rests on it being the only bullish engulfing in that
  price and time neighbourhood. If a different formation was meant, section B's
  Reference A rows change.
