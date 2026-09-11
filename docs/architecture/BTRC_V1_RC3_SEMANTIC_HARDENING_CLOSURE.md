# BTRC V1 — RC3 OVERNIGHT MASTER HARDENING REPORT

**Headline.** The daily chart's two release blockers are fixed and measured:
`TF?` annotations went 8 → 0, overlapping annotations 3 pairs → 0. Both were
presentation defects with mechanical causes, and neither was multi-timeframe
contamination. RC3 is **not** promotion-ready: no new P3, P5 or P8 parity
authority was generated, which the campaign itself names as a closure condition.

---

## A — BASELINE

| # | Item | Value |
| --- | --- | --- |
| 1 | Branch | `rc3-poi-semantics-dev` |
| 2 | Start HEAD | `b1f4c38a5a0a0e85c610d9269176d21ad4b68437` |
| 3 | End HEAD | `55473ca` plus this closure commit |
| 4 | RC3 DEV sha256 | `4f3852e1765d2e3d5aefbaf7ff7b4264a9666ce3f755e24f6dc91accde0367ba` |
| 5 | Baseline tests | 4542 passed |

Sealed artifacts untouched: the characterization summary and both materiality
files remain untracked and were never opened.

---

## B — GOLDENS

| # | Reference A | Value |
| --- | --- | --- |
| 6 | Source | **2026-08-06 18:00Z**, closes 22:00Z |
| | Source OHLC | 4247.06 / 4251.26 / 4232.85 / 4239.43 |
| | Departure | 2026-08-06 22:00Z, O 4239.43 H 4259.24 L 4229.59 C 4256.83 |
| 7 | Range ratio | **1.6105** |
| 8 | Admission | **REJECTED**, reason `RANGE_RATIO_BELOW_2` |
| 9 | Nearby unrelated POI | `HAMMER` 4230.36–4266.96, availability 2026-08-06 14:00Z — a different type at different geometry, correctly kept |

| # | Reference B | Value |
| --- | --- | --- |
| 10 | Source | **2026-09-02 06:00Z**, closes 10:00Z |
| | Source OHLC | 4319.90 / 4331.58 / 4304.77 / 4308.47 |
| 11 | Range ratio | **3.1268** |
| 12 | Admission | **ADMITTED**, tier STRONG, zone 4304.77–4331.58 |
| 13 | First reaction | **+36 H4 bars**, 2026-09-10 14:00Z |
| 14 | Terminal reason | **MITIGATED** |

Both reproduce exactly under canonical replay. Reference B's source time
(06:00Z) and availability time (14:00Z) sit two bars apart, which is the
source-versus-availability separation made visible.

Both are now locked as permanent fixtures with their OHLC embedded, including an
explicit assertion that Reference A is **not** the formation the superseded
audit named. That earlier misidentification happened because the search only
considered formations the detector already admits, so it could never find a
golden the detector rejects.

---

## C — ENGULFING

| # | Item | Answer |
| --- | --- | --- |
| 15 | Body-engulfment authority | Described as the core rule in the knowledge file ("the engulfing candle's body must cover/engulf the previous candle's body"), but never frozen as a mandatory admission condition anywhere in the decision register, the measurement standards or the tests |
| 16 | Mandatory | **PENDING — classification B** |
| 17 | 2.0 threshold unchanged | **TRUE** (3.0 strong tier also unchanged, in its existing role) |
| 18 | New quality gates | **FALSE** — none added |

Because the classification is B, admission was not touched. Adding body
engulfment would take the bullish admitted set from 205 to 191 across 1411 real
candidates, and it would not change either golden: Reference A fails on size
first, Reference B passes both.

Range context was measured and is explicitly **not** an admission gate, in
keeping with the standing instruction that contextual classification "must never
automatically reject a pattern that already satisfies the book's relative-size
rule".

---

## D — SOURCE

| # | Item | Answer |
| --- | --- | --- |
| 19 | All-18 source audit | complete across the families present in the H4 registry |
| 20 | Origin mismatches before | **173 of 173** |
| 21 | Origin mismatches after | **0** |
| 22 | Source ≠ availability verified | **TRUE** |

The drawn left edge read availability where the registry already carried the
source candle's opening time, in one shared assignment, so every family was late
by exactly its own pattern span: 1 bar for single-candle types, 2 for engulfings
and order blocks, 3 for gaps and stars, 4 for buy-to-sell. Confirmed live after
the fix — order-block-plus-engulfing zones moved 2 bars left, stars 3, pressure
wick 1, exactly as predicted per type.

Four families produce no instance in the captured window (base rally, support
zone, resistance zone, sell-to-buy candle), so their origin behaviour is
inferred from the shared assignment rather than observed.

---

## E — FRESHNESS

| # | Item | Value |
| --- | --- | --- |
| 23 | RC2 active | **173** |
| 24 | RC3 fresh | **12** |
| 25 | Mitigated | **161** |
| 26 | Invalidated | **0** |
| 27 | Stale displayed | **0** |
| 28 | Terminal precedence | earliest cause in bar order wins and is never replaced; ties resolve to MITIGATED |

Invalidated is zero because every POI that eventually broke down had been touched
first. The gap case that reaches INVALIDATED is constructed and pinned in the
unit tests.

---

## F — MTF PRESENTATION

| # | Item | Answer |
| --- | --- | --- |
| 29 | Host/source ranking implemented | **TRUE** (`TF_RANK`, ordinal) |
| 30 | Lower-TF hidden on higher host | **TRUE by contract**, no-op in practice — see below |
| 31 | Timestamp `xloc` implemented | **TRUE**, already `xloc.bar_time` throughout |
| 32 | Foreign `bar_index` violations | **0** |
| 33 | `TF?` labels before | **8 of 8 on D1** |
| 34 | `TF?` labels after | **0**, on every reachable host |
| 35 | Stale hanging objects | **0** across 9 host transitions |

**The honest finding.** P3 is single-timeframe by construction: the registry has
no per-POI origin timeframe field, so every POI on a daily chart is a daily POI
and lower-timeframe contamination cannot occur today. The filter is implemented
and tested anyway, because it is the contract and because it is the only thing
that would stand between a daily chart and a pile of one-minute boxes the day
that changes. What the author saw as lower-timeframe boxes hanging on the daily
chart was the origin defect in section D plus the annotation pile in section G.

---

## G — ANNOTATIONS

Measured on the author's daily host, before and after.

| # | Item | Before | After |
| --- | --- | --- | --- |
| 36 | Collision groups | 3 | 3 |
| 37 | Overlapping labels | **3 pairs** | **0** |
| 38 | Annotations printed | 8 | 5 |
| 39 | Suppressed secondary text | 0 | **3** |
| 40 | Semantic boxes preserved | 8 | **8** |
| 41 | Identities preserved in the table | yes | yes |

Three co-located support zones collapsed to one annotation; a base drop
overlapping a sell order block kept the nearer of the two. No box was merged,
moved or deleted.

---

## H — VISUAL

| # | Item | Result |
| --- | --- | --- |
| 42 | Centered full names | TRUE |
| 43 | Bullish green | TRUE |
| 44 | Bearish red | TRUE |
| 45 | Right extension | TRUE, `extend: "r"` on every box plus a bounded projected edge |
| 46 | Fresh-only | TRUE |
| 47 | Candle readability | fill at 90% transparency, border at 25% |

---

## I — HOSTS

| # | Host | Verdict | Evidence |
| --- | --- | --- | --- |
| 48 | M1 | **CLEAN** | settles, 8 boxes, 0 TF?, 0 overlaps, no runtime error |
| 49 | M5 | **CLEAN** | same, plus 3 cold boots |
| 50 | M15 | **CLEAN** | same |
| 51 | H1 | **CLEAN** | same |
| 52 | H4 | **CLEAN** | same, plus 3 cold boots |
| 53 | H6 | **NOT TESTABLE** | the chart silently falls back to D1 on this plan |
| 54 | H8 | **NOT TESTABLE** | same |
| 55 | H12 | **NOT TESTABLE** | same |
| 56 | D1 | **CLEAN** | same, plus 3 cold boots |
| 57 | W1 | **CLEAN** | same, plus 1 cold boot |

H6, H8 and H12 were each requested explicitly and each returned `1D`. The
formatter maps `360`, `480` and `720` to H6, H8 and H12 correctly in the Python
differential, so the labels would be right if the plan offered the intervals.
That is a claim about the formatter, not about the hosts.

No host is declared SUPPORTED here. Clean live behaviour is necessary but the
campaign's own closure list also requires parity evidence, which does not exist.

---

## J — COLD BOOTS

Every boot is a genuine page load, read only after all studies report failed or
completed.

| # | Boot | Settled | Result |
| --- | --- | --- | --- |
| 58 | M5 #1 | 3207 ms | PASS |
| 59 | M5 #2 | 6681 ms | PASS |
| 60 | M5 #3 | 8698 ms | PASS |
| 61 | H4 #1 | 1637 ms | PASS |
| 62 | H4 #2 | 1265 ms | PASS |
| 63 | H4 #3 | 6126 ms | PASS |
| 64 | D1 #1 | 1003 ms | PASS |
| 65 | D1 #2 | 1199 ms | PASS |
| 66 | D1 #3 | 4236 ms | PASS |
| 67 | W1 | 6551 ms | PASS |

Every boot: 2 studies, 8 boxes, 0 labels, 2 tables, `isFailed` false, 0 `TF?`,
no runtime code. `calc_bars_count` remains 1800.

---

## K — RUNTIME

| # | Item | Value |
| --- | --- | --- |
| 68 | RE10041 | **0** |
| 69 | RE10045 | **0** |
| 70 | RE10110 | **0** |
| 71 | Other runtime errors | **0** |
| 72 | Object leak | **none** — 8 boxes / 0 labels / 2 tables held constant across 7 hosts, 9 transitions and 10 cold boots |

---

## L, M, N, O — PARITY

| # | Item | Status |
| --- | --- | --- |
| 73–75 | P3 authority | **NOT CAPTURED** — the `P3LIFE` stream exists in the parity build but its first guard was unreachable and the corrected build was not re-captured |
| 76–78 | P5 authority | **NOT CAPTURED** — `P5EVAL` is per-POI per-bar and the P8 stream alone filled the log buffer first |
| 79 | RC2 → RC3 evaluation impact | 8197 → 2505 POI evaluations; 5692 removed |
| 80–82 | P8 authority | **LIVE CONTRACT EVIDENCE**, not a row-for-row differential — 2200 real events, 945 terminals across 945 distinct POIs, 0 duplicates, 0 missing reasons, 0 terminals before activation |
| 83 | MITIGATED events | 945 live (161 on the 299-bar Python replay) |
| 84 | INVALIDATED events | 0 |
| 85 | Duplicate terminal events | **0** |
| 86 | P6 changed | **PROVEN FALSE** — block byte-identical at sha256 `52ceb8ee…`, zero RC3 symbols inside it, zero P3 arrays inside it |
| 87 | P6 authority disposition | **carried forward**, pinned by a test |

**The parity build now exists** and is saved on TradingView as
`BTMM + POI + BTRC Scanner [RC3 PARITY DEV]`. It drops the 402-line P7-Z
drawing block to buy budget, restores `P5EVAL`, and adds a new `P3LIFE` stream.
Its P3, P4 and P6 spans hash identical to the release DEV; P1 differs only by
the indicator title.

RC2's digests are still not RC3 evidence and are not claimed as such. See
`docs/validation/BTRC_V1_RC3_PARITY_STATUS.md` for exactly what was captured,
what was not, and why.

---

## P — STRESS

| # | Item | Value |
| --- | --- | --- |
| 88 | Randomized lifecycle | covered by the existing RC3 lifecycle suite |
| 89 | Randomized MTF/collision | **~3000 synthetic states** across 15 seeds, asserting one owner per group, partition completeness, and order independence |
| 90 | Mutants | **17** presentation mutants, plus the lifecycle and terminal mutants already in place |
| 91 | Real replay coverage | 5684 H4 bars, 1411 bullish and 1410 bearish engulfing candidates, 173-POI registry |

---

## Q — QUALITY

| # | Gate | Result |
| --- | --- | --- |
| 92 | Targeted tests | 169 across the three touched files |
| 93 | Full suite round 1 | **4613 passed** |
| 94 | Full suite round 2 | **4624 passed in 620 s**, exit code 0 |
| | Full suite round 3, after the parity work | **4660 passed in 626 s**, exit code 0 |
| 95 | Failures | **0** |
| 96 | ruff | clean on every changed file |
| 97 | mypy `src` | clean, 138 files |
| 98 | `git diff --check` | clean |

Round 1 started before the goldens file was written, which is why it collected
4613 of the 4624 now present. Round 2 covers all of them.

---

## R — IMMUTABILITY

| # | Item | Value |
| --- | --- | --- |
| 99 | RC1 sha256 | `143c0f8817c78bf45e6842e16112cedf67ca36dc694c288808b7748096664c54` |
| 100 | RC1 unchanged | **TRUE** |
| 101 | RC2 sha256 | `381f2fc2463c4eaa9dc2eb88943f5bc16a83b55a6d4307c390cce5f87f36cc3f` |
| 102 | RC2 unchanged | **TRUE** |

---

## S — VALIDATION

| # | Item | Value |
| --- | --- | --- |
| 103 | V1-A0 stopped | TRUE |
| 104 | Characterization unopened | TRUE |
| 105 | OOS unopened | TRUE |
| 106 | Materiality rerun required | TRUE, after RC3 freezes |

---

## T — RELEASE

| # | Item | Value |
| --- | --- | --- |
| 107 | RC3 semantic implementation closed | **FALSE** |
| 108 | RC3 promotion ready | **FALSE** |
| 109 | RC3 promoted | **FALSE** |

Against the campaign's own closure list, what is met: both goldens, the 2.0
threshold unchanged, source times correct, availability separate, freshness and
terminal reason correct, P5 exclusion and P8 events correct, `TF?` count zero,
timestamp-safe geometry, no stale objects after a host switch, annotations
resolved, the source audit complete, seven hosts clean, and every cold boot
green.

What is not: the three new parity authorities, the P6 impact proof, and an
honest classification of H6/H8/H12 as tested rather than unreachable.

---

## U — SAFETY

| # | Item | Value |
| --- | --- | --- |
| 110 | push | FALSE |
| 111 | merge | FALSE |
| 112 | publish | FALSE |
| 113 | broker | FALSE |
| 114 | live trading | FALSE |

---

## COMMITS

| Commit | Scope |
| --- | --- |
| `5e7705f` | first-reaction mitigation, terminal cause, live on H4 |
| `b1f4c38` | source-candle origin, identity mode, source and quality audit |
| `e31dbc0` | daily formatter fix, MTF and collision models, golden locks |
| `55473ca` | Pine port of the presentation contracts, documentation |

Local only. Nothing pushed, merged or published.

---

## LIMITATIONS

- **No P3 or P5 capture.** The parity build emits both streams; neither was
  captured. This is the single largest remaining gap and the reason RC3 is not
  promotion-ready.
- **The P8 evidence is contract evidence, not a differential.** Registry
  indices do not align between an 1800-bar Pine run and a 299-bar Python
  fixture.
- **H6, H8 and H12 are unreachable on this plan.** Every attempt fell back to
  D1. Classified NOT TESTABLE.
- **No rendered screenshot.** The chart canvas does not paint in a tab this
  session opens, so every visual claim above is read from the study's own
  drawing primitives — geometry, colour index, text and alignment. That is
  stronger evidence for correctness than a picture and no evidence at all about
  how it feels to read.
- **The in-box identity mode is not in this build.** Removed for 253 tokens so
  the collision resolver could ship. Identities remain in the P7 table.
- **Four POI families have no instance in the captured window**, so their origin
  behaviour is inferred from the shared assignment rather than observed.
- **The host-eligibility filter is a no-op today** and is tested against
  synthetic inputs only, because P3 cannot currently produce a POI whose origin
  timeframe differs from the host.
