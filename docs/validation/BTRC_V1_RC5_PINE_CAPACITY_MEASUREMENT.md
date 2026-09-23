# BTRC-V1 RC5 — Pine capacity measurement

**Capacity measurement only.** Nothing here was implemented into the production
`[RC5 USER]` script, which stays at v11.0 = Stage C. Nothing was published, no
library was modified, `bellforex` was not touched, nothing was merged, no
Python RC5 code was changed.

Every number below comes from the real TradingView compiler through the
validated CE10117 oracle. No estimate is presented as a measurement.

## Method, and one correction to it

The oracle appends N pad blocks of exactly 97 tokens and reads `outputILLength`
out of the compile error's `ctx`. A build that ALREADY exceeds the limit reports
its count directly at pad 0, needing no padding and no arithmetic.

Having both readings on one build exposed a constant the earlier stage log did
not account for:

| Stage C + G | tokens |
| --- | --- |
| derived from pads (N = 20 / 40 / 60, all exact) | 100,552 |
| read directly at pad 0 | 100,511 |
| **difference** | **41** |

41 tokens is the ONE-OFF cost of introducing the first `if barstate.islast` pad
block. It is constant, so every derived figure carries it. The two methods agree
exactly once it is removed, which cross-validates both.

**True counts are therefore `derived - 41`.** Stage deltas are unaffected,
because every stage was measured the same way. Corrected absolutes:

| stage | derived | **true** | headroom |
| --- | --- | --- | --- |
| A — DOJI | 96,007 | 95,966 | 4,290 |
| B — validity / display | 96,043 | 96,002 | 4,254 |
| C — provenance | 96,523 | **96,482** | **3,774** |

## 1-5. The Stage-G answer

Stage G was ported onto the measured Stage-C base with no simplification: level
identity threaded onto framework levels and sweep events; POI far edges
registered and withdrawn from the CURRENT prefix; per-family qualification
(structural swings must be swings the walk used, trendlines need BOTH anchors
meaningful, equal-level pools and confirmed range boundaries always qualify);
semantic deduplication by shared level source AND exactly equal price, with no
tolerance; owner priority and corroboration; DISTRACTION reading qualified
sweeps only. DELAY and WIPEOUT untouched.

| | tokens |
| --- | --- |
| **1. Stage C exact** | **96,482** |
| **2. Stage C headroom** | **3,774** |
| 3a. G1 — meaningful swings (shared with Stage D) | **+357** |
| 3b. G2 — qualified liquidity, dedup, events, DISTRACTION | **+3,672** |
| **3. Stage G total delta** | **+4,029** |
| **4. Stage C + G total** | **100,511** |
| limit | 100,256 |
| **5. OVER BY** | **255** |

Stage G alone exhausts the budget, with Stages D, E, F and H not yet written
and `f_rc5Authoritative` still a stub returning true.

Three-point validation on Stage C + G: N = 20 / 40 / 60 gave 102,492 / 104,432 /
106,372. Both intervals exactly `97 x 20 = 1,940`; all three bases identical at
100,552.

## 6. What D, E, F and H still cost

**Stage D was MEASURED, not estimated**, because it is the fork that prompted
this exercise. A faithful block-at-emission prototype was built on Stage C + G1
— pivot-candle-to-swing maps per side, the meaningful-swing test, and the
range / liquidity / trendline reach test — wired as a conjunct in `f_poiEmit`'s
existing admission test, exactly where Python's `lock_candidate` refuses. A
refused reversal candidate never enters the registry, as in Python.

| | tokens |
| --- | --- |
| Stage C + G1 | 96,839 |
| **Stage C + G1 + D (faithful, blocking)** | **98,907** |
| **Stage D marginal cost** | **+2,068** |

+2,068 for one boolean gate is the inline tax again: `f_poiEmit` has nine call
sites, so the whole predicate body is emitted nine times.

E, F and H are ESTIMATES, flagged as such:

| stage | estimate | basis |
| --- | --- | --- |
| E — authority (cluster + ladder) | 600–1,000 | runs as one per-bar pass over the registry, so it is NOT inline-multiplied; comparable in shape to the Stage-B display pass plus a ladder |
| F — P5/P8 terminal alignment | 50–150 | changes one predicate; comparable to Stage B's measured +36 |
| H — HH/HL/LH/LL + readability | 400–800 | labels plus a read of the existing structural walk; adds no detector |
| **total** | **1,050–1,950** | |

**Projection, all faithful:**

| | tokens |
| --- | --- |
| Stage C + G (measured) | 100,511 |
| + D (measured) | 102,579 |
| + E, F, H (estimated) | **103,629 – 104,529** |
| limit | 100,256 |
| **shortfall to recover** | **3,373 – 4,273**, before any safety margin |

## 7. Extraction candidates, measured

Each candidate was deleted from the over-limit Stage-C+G build and recompiled,
so each recovery is a real compiler reading, not a line count. **Deletion
measures the block's full weight, which is the UPPER BOUND on what moving it to
the BAH library recovers** — a library call still costs its arguments at the
call site. The previously measured BAH extraction recovered 3,614 tokens, so
roughly 70–80% of a deletion figure is the realistic yield.

| candidate | lines | **recovered** | public-safe? |
| --- | --- | --- | --- |
| **e1** RC4 framework display layer — range lines, level lines, BSL/SSL and SWEEP labels | 26 | **1,340** | **Yes.** Pure drawing from already-computed values; the file's own comment states nothing above reads it. |
| **e2** P7 summary + POI tables — cell rendering and row formatting | 76 | **2,684** | **Yes.** Takes finished strings and colours; no rule, threshold or decision crosses the boundary. |
| **e3** P7-Z zone boxes, labels and the visual group projection | 416 | **4,542** | **Mostly.** Box and label construction, the interval-merge grouping and the nearest-first selection are all generic. The POI semantics deciding WHICH zones are eligible stay in the script and must not move. |
| sum of individual recoveries | | 8,566 | |

Deliberately not separated: the P5 row string, `f.txt` and the P8 alert message
construction are already thin `bahui.*` calls, so their remaining weight is
argument marshalling that extraction cannot remove.

e2's first cut left a dangling `if` and failed with CE10144; the boundary was
corrected and re-measured, and the figure above is from the corrected variant.

## 8. Is faithful single-script RC5 feasible?

**Not as the code stands, and not by compaction.** But it is not ruled out.

Needed: 3,373–4,273 tokens plus margin. Available by extraction: 8,566 measured
as deletion, realistically 6,000–6,800 in the library at 70–80% yield.

The arithmetic closes, but only just. e1 + e2 alone measure 4,024 by deletion
(~2,800–3,200 realistic), which does not clear the shortfall on its own, so e3
is required as well and the remaining margin is on the order of 2,000 tokens.

**Faithful single-script RC5 is feasible ONLY if the whole presentation layer
moves into the BAH library, and the result will be tight.**

## 9. Why the two-script partition does NOT work

Worth stating plainly, because it is the obvious fallback and it fails for a
structural reason rather than a budgetary one.

**Pine scripts cannot share state.** No channel exists by which a companion
study receives another study's computed values, so every script must recompute
everything it draws or decides.

Partitioning A–F into one script and G–H into another therefore does not split
the cost. Stage G's liquidity families include ACTIVE POI FAR EDGES, whose
activity is `rc5_validity` plus authority standing — so the companion would need
the POI detector, the full lifecycle, validity, provenance and authority. That
is substantially all of script one, plus G. The companion ends up larger than
the script it was meant to relieve.

Dropping POI far edges from the companion would make it fit, and is exactly the
semantic weakening that is not on the table.

Two further constraints make the split worse in practice: the Basic plan caps
two indicators per chart, so two RC5 scripts leave no slot for
`[RC4 MARKET FRAMEWORK]` alongside, and the same plan caps two live connections.

## Recommendation

1. **Extract, measuring after each step**, in ascending risk: e1 (1,340), then
   e2 (2,684), then e3 (4,542). Each is display-only and public-safe, and none
   changes a scanner rule. Re-measure after each so the yield is known rather
   than assumed.
2. **Then implement D–H faithfully**, in the author's order, with the same
   per-stage three-point measurement.
3. **Keep the single script.** The two-script partition does not reduce total
   compiled tokens, for the reason in section 9, and costs a chart slot.
4. If extraction falls short of the measured requirement, the decision returns
   to the author with real numbers rather than a guess. The honest options at
   that point are reducing the DRAWN surface — not the computed semantics — or
   accepting a Pine layer that renders a subset of RC5 while Python remains the
   authority.

## Artifacts

Measurement builds are disposable and live in the session scratchpad, not in the
repository. The production `[RC5 USER]` script is unchanged at v11.0 (Stage C,
LF SHA `7c0e5045974977a41e57837f8108a9e3706bea08cd0a2a339627d6d1709564d1`).


---

# E1-A — Surface A measured

Built privately. **Nothing was published**; the currently published BAH v1 is
untouched. The candidate lives at
`tradingview/libraries/bah_pine_ui_helpers_candidate.pine`, beside the
unmodified published source.

## The four exports

| export | arguments | what crosses the boundary |
| --- | --- | --- |
| `drawPriceBand(sink, leftTime, rightTime, hi, lo, col)` | 6 | three lines, midline dotted |
| `drawLevelRay(sink, x1, y1, x2, y2, family, side)` | 7 | one ray; `family`/`side` select colour and style |
| `drawTagLabel(sink, x, y, txt, side)` | 5 | one left-anchored text tag |
| `drawSweepMarker(sink, t, y, side)` | 4 | one marker, pointing by `side` |

`family` and `side` are opaque integers. The library is told WHICH style to
draw and can derive nothing about what a level is or how it was arrived at.

## Measured recovery

| N | reported | `C - 97N` |
| --- | --- | --- |
| 60 | 102,094 | 96,274 |
| 80 | 104,034 | 96,274 |
| 100 | 105,974 | 96,274 |

Both intervals exactly `97 x 20`; all three bases identical.

| | tokens |
| --- | --- |
| RC5 before Surface A | 96,376 |
| **RC5 after Surface A** | **96,233** |
| **recovered, measured** | **143** |
| recovered, scaffold-adjusted | **~209** |
| new headroom | 4,023 (was 3,880) |
| BAH library impact | +4 exports, +58 lines; not published, so no compiled-token figure exists for it |

The measurement build keeps the call sites but replaces the four bodies with
local stubs that consume every argument. It therefore carries roughly 66 tokens
of scaffolding a real library call would not have (the stub bodies, the
`_xs := _xs +` accumulation at four call sites, and one liveness statement), so
the true recovery is about 209 rather than 143. Both figures are reported; the
conservative one is the measurement.

**Dead-code self-check.** A full deletion of the block would land at 95,036.
The measured build is 96,233 — 1,197 ABOVE that — so Pine did not optimise the
argument expressions away and the measurement is valid rather than silently
collapsing to the deletion ceiling.

## The correction this confirms, with a number

| | |
| --- | --- |
| e1 deletion ceiling | 1,340 |
| e1 actual library yield | **143 - 209** |
| **yield ratio** | **11% - 16%** |

The capacity report assumed 70-80%, carried over from the earlier BAH
extraction. **That assumption is now measured and wrong for this surface.** The
earlier extraction moved helpers taking strings, numbers and colours. e1 is
mostly a LOOP over script-local UDTs (`FwLv`, `FwEv`) with the geometry
computed inline; a library cannot consume a private UDT, so the loops, the
`na` guards, the per-family caps and every coordinate expression stay in the
scanner. Only four object constructors and their style ternaries left.

## What this means for the campaign

Surface A closes about **4-5%** of the 4,373-5,273 token gap (faithful D-H plus
the 1,000 reserve). It is not close to sufficient on its own.

It also forces a re-reading of the remaining ceilings, which were measured by
deletion and are NOT recoveries:

| surface | deletion ceiling | expected yield character |
| --- | --- | --- |
| e1 RC4 display layer | 1,340 | **measured 143-209** — UDT-bound loop, little moves |
| e2 P7 tables | 2,684 | likely the BEST ratio: `table.cell` calls with primitive args, the same shape as the existing `renderRow` export |
| e3 P7-Z zones | 4,542 | mixed — box construction is primitive-friendly, but the grouping pass walks script-local `P7zG`, so it hits e1's wall unless the type moves |

Extrapolating e1's ratio to everything would be as unsound as extrapolating the
old 70-80%. e2 and e3 must be measured, not assumed.


---

# Surface B measured — and the extraction campaign's answer

Built privately. **Nothing published.** BAH v1 is untouched; the candidate is
`tradingview/libraries/bah_pine_ui_helpers_candidate.pine`.

## Oracle formula, locked

```
BASE = CE10117_TOTAL - (97 x N) - 41
```

The 41 is the fixed one-off cost of introducing the first pad block. Every
figure below uses it, and every variant was validated at three pad points.

## Field classification, done before any DTO was designed

Exporting `FwLv` verbatim would have leaked two fields. This is why the DTO
route was taken rather than moving the internal type:

| field | meaning | classification |
| --- | --- | --- |
| `FwLv.p` | price at anchor | PUBLIC-SAFE — a y coordinate |
| `FwLv.s` | price change per bar | PUBLIC-SAFE — slope, pure drawing geometry |
| `FwLv.a` | anchor bar index | PUBLIC-SAFE — an x coordinate |
| `FwLv.d` | buy-side / sell-side | PUBLIC-SAFE **only as an opaque side code** |
| `FwLv.k` | known-from / availability | **PRIVATE** — when the scanner treats a level as available |
| `FwLv.x` | bar of a pending close-through | **PRIVATE** — retire / reclaim mechanics |
| `FwLv.t` | level family | PUBLIC-SAFE **only as an opaque style code**, meanings undocumented publicly |
| `FwEv.t` / `.d` / `.p` / `.o` | time, side, price, bar open | PUBLIC-SAFE — coordinates and an opaque code |

`k` and `x` never cross the boundary. Visibility is resolved on the RC5 side
and only a finished coordinate set, two opaque codes and a finished string are
handed over.

## The three variants

Decomposed so the surfaces do not overlap and cannot be double counted:

- **A-only** — band, ray, tag and marker each via a Surface-A primitive.
- **B-only** — band left INLINE; levels and markers through the DTO bulk
  renderers. Isolates B's own contribution.
- **A+B** — the band additionally moves via `drawPriceBand`, on top of B.

| variant | N=60 | N=80 | N=100 | linear | **BASE** | vs clean | headroom |
| --- | --- | --- | --- | --- | --- | --- | --- |
| clean RC5 | — | — | — | — | **96,376** | — | 3,880 |
| A-only | 102,094 | 104,034 | 105,974 | yes | **96,233** | **+143** | 4,023 |
| B-only | 102,290 | 104,230 | 106,170 | yes | **96,429** | **-53** | 3,827 |
| A+B | 102,182 | 104,122 | 106,062 | yes | **96,321** | **+55** | 3,935 |

Every interval is exactly `97 x 20 = 1,940`; all three bases within each
variant are identical.

## Two results that matter

**Surface B is a net LOSS of 53 tokens.** Moving the draw loop behind generic
DTOs costs more than it saves. Constructing `DisplayLevel.new(...)` with six
arguments plus the tag ternary costs about as much as the two draw calls it
replaced, and the RC5 side still pays for the iteration, the `na` guard, the
availability check and now two array allocations as well.

**A+B (+55) is WORSE than A alone (+143).** Arithmetic on the individual
recoveries would predict +90; the combined build measures +55. The surfaces are
not additive, and adding B to A actively destroys value.

**The best measured configuration is Surface A alone: 96,233, headroom 4,023.**

## Capacity ledger at the best configuration

| item | tokens | basis |
| --- | --- | --- |
| base (A-only) | 96,233 | measured |
| **headroom** | **4,023** | |
| Stage D — structural origin, blocking | 2,068 | **measured prototype** |
| Stage G — qualified liquidity + sweeps + DISTRACTION | 4,029 | **measured prototype** |
| Stage E — authority | 600–1,000 | estimate |
| Stage F — P5/P8 terminal | 50–150 | estimate |
| Stage H — HH/HL/LH/LL | 400–800 | estimate |
| POI anchoring correction | unmeasured | new work item |
| required final reserve | 1,000 | author requirement |
| **total required** | **8,147–9,047** plus the anchor fix | |
| **SHORTFALL** | **4,124–5,024** plus the anchor fix | |

## The campaign's verdict

The remaining presentation deletion ceilings are e2 P7 tables 2,684 and e3 P7-Z
4,542, totalling 7,226. But **deletion ceilings are not recoveries**: e1's
ceiling was 1,340 and its best real extraction yielded 143 — **10.7%**. e2 is
structurally more favourable (it is `table.cell` calls over primitive
arguments, the same shape as the existing `renderRow` export) so its ratio
should be higher, but even a generous 40% across e2 and e3 gives roughly 2,900
— still short of 4,124–5,024, and that assumes e3's zone selection can move,
which it cannot without taking semantics with it.

**Library extraction cannot close this gap.** That is now measured on two
independent surfaces rather than argued.

## What remains, stated without weakening semantics

The author's constraints rule out the semantic escapes, and section 9 already
ruled out the two-script split on structural grounds. What is left is the one
lever the author explicitly allowed: **reduce the DRAWN surface, not the
computed semantics.** Measured prices for that are already in hand:

| drawing feature | measured cost | what is lost | semantics affected |
| --- | --- | --- | --- |
| RC4 framework display layer (e1) — range lines, level rays, BSL/SSL tags, SWEEP markers | **1,340** | the RC4-era raw-level picture | **none** — RC5's qualified liquidity is computed either way |
| P7-Z visual group projection (part of e3) — interval merge, nearest-first selection, per-group capacity | up to **4,542** for the whole block | grouped/merged zone boxes; a simpler nearest-N renderer keeps the locked gray boxes | **none** — POI eligibility is decided before this runs |

Dropping e1 alone (1,340 measured) plus a simplified zone renderer would close
the shortfall using numbers already measured, and neither touches detection,
authority, lifecycle, validity, qualified liquidity, dedup, DISTRACTION or
HH/HL/LH/LL.

## Security review — Surface B

Scanned across code, comments, type names, field names, parameter names and
docs. The only vocabulary hits were two substrings of `color.orange`.

| public symbol | purpose | public-safe | why |
| --- | --- | --- | --- |
| `DisplayLevel` | a drawable line | **Yes** | coordinates and opaque codes only |
| `DisplayMarker` | a drawable marker | **Yes** | coordinates and opaque codes only |
| `drawLevels` | draw a list under two draw budgets | **Yes** | iterates finished data; decides nothing |
| `drawMarkers` | draw the last N markers | **Yes** | iterates finished data |

| field | type | why public-safe |
| --- | --- | --- |
| `DisplayLevel.ax` | int | an x coordinate |
| `DisplayLevel.ay` | float | a y coordinate |
| `DisplayLevel.slope` | float | y change per x step; drawing geometry |
| `DisplayLevel.styleCode` | int | opaque; no meaning documented publicly |
| `DisplayLevel.side` | int | opaque; selects a colour and an anchor direction |
| `DisplayLevel.tag` | string | text the caller already composed; `""` means draw none |
| `DisplayMarker.at` | int | an x coordinate, in bar time |
| `DisplayMarker.y` | float | a y coordinate |
| `DisplayMarker.side` | int | opaque; selects which way the marker points |
| `DisplayMarker.txt` | string | text the caller already composed |

Surface B contains **no string literal at all** except `""`. It is on that axis
cleaner than Surface A, which still hardcodes `"SWEEP"` inside
`drawSweepMarker`; under B that word is supplied by the caller.

Two naming corrections were forced by the compiler and are worth recording:
`text` and `style` are reserved in Pine and cannot be field names. They are
`txt` and `styleCode`.

## Recommendation

1. **Do not publish BAH v2.** Surface A's 143 tokens do not justify a public
   version change, Surface B is a net loss, and A+B is worse than A. Both
   candidates stay private.
2. **Stop the extraction campaign here.** Two measured surfaces on the same
   block returned 10.7% and a negative yield. Spending more cycles on e2/e3 to
   chase roughly 2,900 against a 4,124–5,024 shortfall is not a good use of the
   remaining budget, and the arithmetic does not close even if it succeeds.
3. **Bring the drawn surface to the author as the decision**, priced with the
   measurements already taken. This is the only remaining lever that costs no
   semantics.

---

# Presentation simplification measured — four variants

Author-approved prototypes. Nothing applied to the live build; nothing published.

## Oracle refinement found during this run

`BASE = TOTAL - 97N - 41` held at N = 60/80/90/100 but BROKE at N = 120:
N=120 gave a base 20 higher than N=80/90/100. The cause is the pad label
itself — at N >= 101 the indices become three digits (`pad100`), and a longer
string literal costs one more token, which is exactly the +20 observed across
twenty such pads.

**Keep N <= 100 so pad indices stay at two digits.** Outside that range the
97-token constant is wrong and the derived base drifts upward.

## Results

| variant | pad points | reported | **BASE** | recovery | headroom |
| --- | --- | --- | --- | --- | --- |
| V1 current clean | — | — | **96,376** | — | 3,880 |
| V2 simplified P7-Z | 80 / 90 / 100 | 101,752 / 102,722 / 103,692 | **93,951** | **2,425** | 6,305 |
| V3 legacy RC4 display removed | 60 / 80 / 100 | 100,897 / 102,837 / 104,777 | **95,036** | **1,340** | 5,220 |
| V4 both | 80 / 90 / 100 | 100,412 / 101,382 / 102,352 | **92,611** | **3,765** | **7,645** |

All three points within each variant give an identical base.

**The two surfaces ARE additive here**: 2,425 + 1,340 = 3,765, and the combined
build measures exactly 3,765. That is the opposite of Surfaces A and B, and it
holds because the two blocks share no code.

V3's 1,340 independently reproduces the e1 deletion ceiling measured earlier on
the Stage-C+G build — two different bases, same number.

## Capacity ledger from the combined prototype

| item | tokens | basis |
| --- | --- | --- |
| base after presentation simplification | **92,611** | measured |
| + Stage D | 2,068 | measured prototype |
| + Stage G | 4,029 | measured prototype |
| + Stage E | 600–1,000 | estimate |
| + Stage F | 50–150 | estimate |
| + Stage H | 400–800 | estimate |
| **projected final RC5** | **99,758 – 100,658** | |
| author target (<= 99,256, i.e. 1,000 reserve) | | |
| **SHORTFALL against the target** | **502 – 1,402** | |
| vs the hard 100,256 limit | +498 to **-402** | |

So the combined simplification closes most of the gap — from a 4,124–5,024
shortfall down to 502–1,402 — but does **not** reach the 1,000-token reserve,
and in the pessimistic case does not fit at all.

Per the author's instruction the campaign stops here and returns the exact
shortfall rather than proceeding into Stage D.

## What is left, and why the remainder looks reachable

Not yet spent, all measured or bounded:

| lever | tokens | note |
| --- | --- | --- |
| Surface A library extraction | 143 | measured, private, not published |
| P7 summary + POI table (e2) | up to 2,684 deletion ceiling | user-facing; a simplification rather than a deletion |
| tightening E / F / H | up to 900 | they are estimates spanning 900 tokens; measuring them may remove most of the uncertainty |

The shortfall is 502–1,402 against an unspent e2 ceiling of 2,684, so the
single-indicator architecture is probably still reachable — but that is a
projection, not a measurement, and it is the author's call whether to spend the
P7 table to buy it.

## Anchoring

The simplified renderer draws every zone with `left = poiAvailTime` under
`xloc.bar_time` and uses **no `bar_index` anywhere**. The legacy RC4 display
layer removed in V3 was the only drawing in the file anchored to `bar_index`,
which makes V4 the correct place to have fixed the coordinate path rather than
maintaining two renderers.

---

# Addendum work: overlap arbitration, and the trendline disappearance

## Overlap arbitration — measured

| variant | pad points | **BASE** | delta |
| --- | --- | --- | --- |
| V4 both simplifications | 80 / 90 / 100 | 92,611 | — |
| **V5 = V4 + one visible winner per overlap** | 80 / 90 / 100 → 101,124 / 102,094 / 103,064 | **93,323** | **+712** |

All three points identical.

**Where it lives: the renderer, and nowhere else.** Authority resolves
SAME-ORIGIN duplicates; POIs that merely overlap in price generally come from
different origins and are semantically independent, so suppressing them in the
authority or validity layer would destroy real information. Overlap is a
geometric, presentation-only concern.

**Precedence, using the existing frozen ranking rather than a new heuristic:**
`f_rc5LadderRank` ports `ladder_rank` from `poi/authority.py` — the author's
own reversal ladder (B2S/S2B 1, ORDER BLOCK 2, stars 3, engulfing 4,
hammer/shooting star 5, DOJI 6, pressure wicks 7) including its
`REVERSAL_LADDER.get(type, 99)` "unranked sorts last" rule. Ties break on
STRONG before STANDARD, then on the MOST RECENT availability.

On the author's reported cluster — SELL FVG + RESISTANCE ZONE + SHOOTING STAR
+ BEARISH PRESSURE WICK — the winner is the **SHOOTING STAR** (rank 5), because
the pressure wick is rank 7 and the FVG and the reference zone are both
unranked 99.

**Nothing is destroyed.** Suppressed POIs keep their registry record, their P5
row, their P8 events and their place in the P7 table. A diagnostic counter
`p7zOverlapHidden` reports how many lost. Only the drawing hides them.

**One open question for the author.** The rule currently suppresses across
DIRECTIONS: a bullish zone overlapping a bearish one can be hidden. That
follows "same price area" literally, but hiding a bullish ORDER BLOCK because a
bearish wick overlaps it may be worse than the clutter. Making the rule
per-direction is a one-token change and is offered as a decision, not taken
unilaterally.

## Trendline disappearance — ROOT CAUSE FOUND

**Source: RC4.** The trendline on the chart is drawn by the legacy RC4 display
layer, from `fwLv` entries with family code 2.

**Why it vanished, exactly.** In the framework level step:

```
bool ev = na(l.x) ? not bc and (l.d > 0 ? high > p : low < p) : not bc
if ev
    array.push(fwEv, ...)
if ev or (not na(l.x) and bc and fwNow - l.x >= 3)
    array.remove(fwLv, j)
```

`ev` is true when price did NOT close through the level but DID wick through it
— which is precisely "price touched the trendline and rejected". The very next
statement removes that level from `fwLv`. Because the display draws from
`fwLv`, **the trendline disappears from the chart on the exact bar price
respects it.**

This is not object-limit pruning, not a repaint artefact, not layout drift, and
not hidden-vs-deleted confusion. It is a real display defect with a single
cause.

**Is the removal itself wrong? No — but the drawing source is.** Consuming the
level is correct liquidity doctrine: a framework level fires at most one sweep
in its life and then retires, which is what lets a raw sweep prove its level
was live. What is wrong is drawing a *structural trendline* from a *consumable
liquidity level*. They are different objects with different lifetimes.

**The fix, which changes no semantics.** Draw trendlines from `fwTls`, the
detected trendline collection (declared line 575, populated line 2138), not
from `fwLv`. The sweep still fires, RC5 Stage G still qualifies it, and the
trendline stays visible for as long as it is a detected trendline. Display-only.

This also tells us what the RC5 replacement layer must do: the V3/V4 prototypes
remove the RC4 display layer entirely, so the RC5 trendline layer that replaces
it must read `fwTls`, not `fwLv`, or it would reproduce the same defect.

## Ledger including the overlap fix

| item | tokens |
| --- | --- |
| V5 base (both simplifications + overlap winner) | 93,323 |
| + Stage D (measured) | 2,068 |
| + Stage G (measured) | 4,029 |
| + Stage E / F / H (estimates) | 1,050–1,950 |
| **projected final RC5** | **100,470 – 101,370** |
| hard limit | 100,256 |
| **OVER by** | **214 – 1,114** |

Plus an RC5 trendline layer reading `fwTls`, not yet measured.

Unspent levers: Surface A (143, measured) and the P7 summary + POI table
(2,684 deletion ceiling, a simplification rather than a deletion). The
remaining gap is smaller than that ceiling, so a single indicator still looks
reachable — but that is a projection and the P7 table is the author's to spend.

---

# Corrected display-overlap arbitration

The first prototype (V5) used the reversal authority ladder as a global display
rank. **Withdrawn.** That ladder ranks SAME-ORIGIN competitors; used globally it
silently becomes a POI-quality ranking and lets a weak reversal outrank a strong
imbalance purely because imbalances are unranked in it.

## The corrected rule

- **Same direction only.** Bullish competes with bullish, bearish with bearish.
  A bearish wick can no longer hide a bullish order block; opposite-direction
  overlap carries real conflict information and stays visible.
- **Winner by already-computed facts only**, in order: the P5 weighted
  confluence score, then STRONG ahead of STANDARD, then the more recent
  availability, then the registry index so a full tie is still deterministic.
  The renderer computes no market quality of its own.
- **Chained overlap is one cluster** (A-B, B-C travel together), via a sort by
  lower edge and a sweep on a running maximum upper edge. Nothing is merged,
  renamed or counted.
- **No new tolerance.** The existing exact interval relation decides.

The P5 score was computed but never stored, so `FwPoi` gains one `scr` field
written beside the `perm` assignment that already happens. A POI the P5 loop has
not scored carries 0 and loses on quality, which is correct.

## Measurements

| variant | pad points | **BASE** | delta vs V4 |
| --- | --- | --- | --- |
| V4 both simplifications | — | 92,611 | — |
| V5 ladder-based overlap (**withdrawn**) | 80/90/100 | 93,323 | +712 |
| **V6 corrected overlap** | 80/90/100 → 101,631 / 102,601 / 103,571 | **93,830** | **+1,219** |
| V7 single-sweep optimisation attempt | 80 | 93,863 | +1,252 |

The correction costs 507 more than the withdrawn version — direction
partitioning, the comparator, and array-held cluster state (a scalar mutated
across a Pine for-loop reads back as its initial value, the defect that once
left every FVG undrawn).

**The optimisation attempt failed and is reported as such.** Folding direction
into the sort key to replace the two-pass partition with one sweep measured
**33 tokens worse**, because the extra key array and direction tracker cost more
than the partition they removed. V6 stands.

## Visual proof — and what it actually showed

Deployed to `BAH-RC5-LAB` as **v13.0**, confirmed running via the study's own
`pine.version`, with RC4 hidden so every drawn object is RC5's.

The zones render gray with black size-31 text and no `xN` suffixes. But the
capture also shows **three bullish labels colliding** near 1.1640-1.1660 — and
that is NOT an arbitration failure. The arbitration kept all three, which under
exact interval geometry means their ZONES do not overlap. What collides is the
TEXT: at size 31 a label is far taller than these thin zone boxes, so
annotations from disjoint zones still print over one another.

**There are two separate clutter problems, and the overlap rule only solves
one:**

| problem | cause | status |
| --- | --- | --- |
| overlapping ZONES drawn on top of each other | several eligible POIs sharing a price interval | **solved** by the corrected arbitration |
| colliding LABELS on NON-overlapping zones | size-31 text is taller than a thin zone box | **not solved** — this is what the removed annotation-collision pass used to handle |

The author's reported cluster (SELL FVG + RESISTANCE ZONE + SHOOTING STAR +
BEARISH PRESSURE WICK) is the first kind and is addressed. The bullish trio in
this capture is the second kind and needs a separate decision, because the only
honest fixes are a label-collision pass (tokens) or a smaller text size (which
is currently locked at 31).

## Ledger with the corrected overlap

| item | tokens |
| --- | --- |
| V6 base | 93,830 |
| + Stage D (measured) 2,068, + Stage G (measured) 4,029 | 99,927 |
| + Stage E / F / H (estimates) | **100,977 – 101,877** |
| hard limit | 100,256 |
| **OVER by** | **721 – 1,621** |

Before the trendline layer and the anchoring fix. The P7 summary and POI table
(2,684 deletion ceiling) remain the next unspent target.

---

# FwPoi.scr audit, and the structural trendline layer

## 1. What `FwPoi.scr` actually is — answer: B, DYNAMIC

`scr` stores the P5 weighted confluence score. Its eight components and weights:

| component | weight | per-POI? | stable? |
| --- | --- | --- | --- |
| btmmScore | 3 | **yes** | **no** — BTMM validity and direction match move per bar |
| poiScore | 3 | **yes** | **YES** — a pure function of the frozen tier |
| trendScore | 2 | only via direction | no, but identical across a same-direction cluster |
| regimeScore | 1 | no — global | no |
| momentumScore | 1 | only via direction | no, but identical across a same-direction cluster |
| breakoutScore | 1 | no — global | no |
| liquidityScore | 1 | **yes** | **no** — framework location / BTMM validity |
| volatilityScore | 1 | no — global | no |

So **10 of 13 weight is dynamic context**, and only 3 of 13 is static formation
quality.

**But the consequence for the display winner is narrower than that, and this is
the part that matters.** The arbitration only ever compares POIs inside one
SAME-DIRECTION cluster. Within such a cluster, `trendScore`, `regimeScore`,
`momentumScore`, `breakoutScore` and `volatilityScore` are IDENTICAL for every
member — they are global per bar, or depend only on direction. They shift every
member's score by the same amount and therefore **cannot change the ordering**.

The only components that differentiate a cluster are:

| differentiator | weight | stability |
| --- | --- | --- |
| poiScore (tier) | 3 | static |
| btmmScore | 3 | dynamic |
| liquidityScore | 1 | dynamic |

**Reported honestly: the visible winner CAN switch while the underlying POIs
are unchanged.** It happens when a member's BTMM cycle validity flips, or its
framework-location band changes. It does NOT happen from general market
movement, because that moves the whole cluster together.

Whether that is acceptable is an author decision. Two observations to inform it:

* a winner change driven by BTMM validity is arguably a real change in which
  POI is currently the better representative, not noise;
* `poiTier` is currently counted TWICE — once inside the score at weight 3, and
  again as the explicit secondary tie-break. If a more static winner is wanted,
  the cheapest faithful change is to rank on the tier FIRST and use the score
  only to break tier ties, which inverts the current order and costs nothing.

No redesign was performed; this is the proof that was asked for.

## 2. Structural trendline layer — measured

Trendlines are now drawn from `fwTls`, the DETECTED TRENDLINE collection, and
never from the consumable framework level. Both endpoints are anchor TIMES
under `xloc.bar_time`, so the line is market-anchored and uses no `bar_index`.

No expiry, touch-count or slope rule was introduced. Only the trendline engine
can end a trendline; a liquidity sweep consumes the liquidity representation and
leaves the structure alone.

| variant | pad points | **BASE** | delta |
| --- | --- | --- | --- |
| V6 corrected overlap | — | 93,830 | — |
| **V8 = V6 + fwTls trendline layer** | 80/90/100 → 101,954 / 102,924 / 103,894 | **94,153** | **+323** |

Reported separately and NOT folded into the Stage-H estimate.

## 3. Capacity ledger against the strict target

| item | tokens |
| --- | --- |
| V8 base (simplified P7-Z + RC4 display removed + corrected overlap + trendline) | 94,153 |
| + Stage D (measured) | 2,068 |
| + Stage G (measured) | 4,029 |
| + Stage E / F / H (estimates) | 1,050–1,950 |
| **projected final RC5** | **101,300 – 102,200** |
| strict target (1,000 reserve) | 99,256 |
| **SHORTFALL** | **2,044 – 2,944** |

Plus the POI anchoring fix, still unmeasured.

The P7 summary and POI table remain the largest unspent surface at a 2,684
deletion ceiling. At the optimistic end that would just close the gap; at the
pessimistic end it would not, and a further decision would be needed.

---

# Stabilised display rank, and trendline live QA

## 1. Display winner stabilised — measured at **-14 tokens**

New order: **tier > score > recency > stable id**.

| variant | pad points | **BASE** | delta |
| --- | --- | --- | --- |
| V8 (score-first) | — | 94,153 | — |
| **V9 (tier-first)** | 80/90/100 -> 101,940 / 102,910 / 103,880 | **94,139** | **-14** |

It costs nothing because the tier constants are ordered `NA 0 < STANDARD 1 <
STRONG 2` and now compare directly, replacing two ternaries. That is also **more
correct** than the previous test, which asked only "is it STRONG?" and therefore
treated STANDARD and NA as equal.

Applied to the V6 base the same change gives 93,816, by arithmetic; the -14 is
the measured quantity.

## 2. Trendline live QA — PAN, ZOOM and RELOAD verified

Deployed as **v14.0** and confirmed running via the study's own `pine.version`,
on `BAH-RC5-LAB`, RC4 hidden, `document.hidden = false`, canvas 1408x788.

| step | result |
| --- | --- |
| trendlines render from `fwTls` | **pass** |
| price has traded through several drawn lines | **pass** — visible on the 17th, where a large drop cuts across multiple lines that remain drawn |
| **PAN** | **pass** — lines move WITH the candles, not with the viewport |
| **ZOOM** | **pass** — lines stay on their anchors |
| **RELOAD** | **pass** — after a full reload the layout returns at v14.0 with trendlines on and the lines redrawn |

The "price traded through and the line survived" observation is the direct
refutation of the old defect: under the previous coupling any line price wicked
through without closing through was removed from the level collection on that
very bar, and therefore vanished.

**Not claimed:** a controlled single-trendline before/after through one
identified respect event, with its anchor swing ids and prices recorded. Pine
drawing objects cannot be enumerated from the page, so the anchors could not be
read back programmatically, and the evidence above is positional rather than
per-object. That remains owed.

### Two operational findings worth keeping

* **A chart layout PINS the study version.** After saving a new script version,
  a reload restores the pinned one — the study must be removed and re-added
  AFTER the reload, and then the layout saved, or the next reload reverts it.
  This cost two invalid test runs before it was understood.
* Trendline display is off by default (`in_3`, "Show Trendlines" = false), so an
  empty chart is not evidence of a rendering failure.

## 3. Ledger

| item | tokens |
| --- | --- |
| V9 base (simplification + corrected overlap + tier-first rank + trendlines) | 94,139 |
| + Stage D 2,068, + Stage G 4,029 | 100,236 |
| + Stage E / F / H | **101,286 – 102,186** |
| strict target | 99,256 |
| **SHORTFALL** | **2,030 – 2,930** |

Plus the POI anchoring fix. The P7 summary and POI table (2,684 ceiling) is the
next surface and is now mandatory.

---

# P7 table: T1 audit, T2 compaction, T3 measured as futile

Base for everything below is the accepted V9 prototype, **94,139**.

## T1 — measured sub-costs

| surface | **tokens** | how measured |
| --- | --- | --- |
| whole table block | **2,747** | deleted, recompiled |
| — summary table (top left) | **975** | deleted alone |
| — POI table (bottom right) | **1,772** | by difference |
| row-string construction, in the P5 loop and NOT in the block | **221** | replaced with a placeholder |
| **total table-related surface** | **2,968** | |

The 2,747 independently reproduces the earlier 2,684 ceiling that was measured
on a different base.

## The T1 finding that decides the phase

**The table is already compacted.** The optimisations T2 was asked to attempt
are, with one exception, already in the code and carry RC3 compaction notes
saying so:

| proposed T2 idea | status |
| --- | --- |
| one loop for summary rows instead of nine writes | **already done** |
| header written by one loop | **already done** |
| row cells written by one loop over a pre-composed string | **already done** |
| blank rows written by one loop | **already done** |
| `bahui.renderRow` reused for the summary | **already done** |
| row string composed once, in the P5 loop | **already done** |
| occupied-row and blank-row writes merged into ONE loop | the only remaining idea |
| footer text and its eight blanks merged into ONE loop | the only remaining idea |

## T2 — zero-information-loss compaction, measured

Implemented both remaining ideas. Every column, value, colour, the proximity
ordering and the footer text are unchanged; a row with no POI yields an empty
string and the default colour, exactly as the old blank branch wrote.

| variant | pad points | **BASE** | recovery |
| --- | --- | --- | --- |
| V9 | — | 94,139 | — |
| **T2 compact** | 80 / 90 / 100 -> 101,830 / 102,800 / 103,770 | **94,029** | **110** |

**110 tokens.** Against a 1,920-2,820 shortfall that is not material.

## T3 — measured, and it does NOT work

T3 assumed removing columns saves tokens. **It does not, and this is measured
rather than argued.**

Cells are written by a single `for c = 0 to 8` loop, so a column is not a piece
of code — it is one entry in a header string, one field in the composed row
string, and a higher loop bound. Removing one removes no statement.

| variant | **BASE** | saving |
| --- | --- | --- |
| T2 compact, 9 columns | 94,029 | — |
| T2 compact, **7 columns** (Align and State dropped) | **93,962** | **67, i.e. ~33 per column** |

Dropping **all nine** columns would recover roughly 300 tokens and leave no
table at all. **T3 is therefore not worth presenting as a choice**, and no
column-removal menu is offered: the information loss would be total and the
gain negligible. The table's cost is its construction, its proximity ordering
and its cell-write machinery, not its column count.

## POI anchor defect — ROOT CAUSE FOUND, and the fix is already paid for

Audited every drawing call for its coordinate space.

**Current production source:** exactly **two** `bar_index`-anchored drawings,
both in the legacy RC4 framework display layer — the level rays and their
BSL/SSL tags. `bar_index` is a positional index, not market time, so those
objects do not stay attached to price and time when the chart moves.

**V9 prototype:** **zero** `bar_index` in any drawing. Every object is
`xloc.bar_time` with market timestamps — market-structure lines and labels on
`brokenSwingKey` / `breakTime` / `pivotEndTime`, trendlines on their anchor
times, POI boxes on `poiAvailTime`.

**So the anchor fix costs 0 additional tokens.** It is already contained in the
V3/V4 simplification that removed the RC4 display layer.

One honest qualification. POI BOXES were always `xloc.bar_time`, in both
builds, so the two `bar_index` objects do not by themselves explain a POI box
appearing to detach. There is a second, POI-specific candidate with code
evidence: the OLD renderer anchored each box to its GROUP's `left`
(`p7zGs[g].left`), and a group's membership — and therefore its left edge —
could change as price moved, so a box could jump without its POI changing. The
simplified renderer anchors every box to its OWN `poiAvailTime`, which removes
that class of movement. This is a strong hypothesis, not yet a proven
reproduction, and the pan/zoom/reload matrix on POI boxes is still owed.

## Ledger

| item | tokens |
| --- | --- |
| T2 base | 94,029 |
| + Stage D (measured) 2,068, + Stage G (measured) 4,029 | 100,126 |
| + Stage E / F / H (estimates) | **101,176 – 102,076** |
| + anchor fix | **0 — already included** |
| strict target | 99,256 |
| **SHORTFALL** | **1,920 – 2,820** |

The presentation campaign is now essentially exhausted: e1, P7-Z, overlap, the
trendline layer and the table have all been measured, and the table returned
110. What remains unspent is Surface A (143) and the E/F/H estimate band itself,
which spans 900 tokens and could be narrowed by measuring those three stages
rather than estimating them.

---

# E, F and H measured exactly — the capacity decision

Every stage is now a compiler measurement. **No estimate remains in the ledger.**

## Base discipline

| base | tokens | what it is |
| --- | --- | --- |
| T2 | 94,029 | simplification + overlap + tier-first + trendlines + compact table |
| B1 = T2 + G1 | 94,386 | G1 is the meaningful-swing map |

G1 measures **+357 here, identical to its +357 on the Stage-C base** — two
unrelated bases, same number, which validates the whole measurement chain.

E and H are measured against **B1** because both consume G1, and G1 is already
inside G's 4,029. Measuring them on B1 is what stops G1 being counted twice.
F needs no swing roles and is measured against T2.

## The three measurements

| stage | measured on | base after | **delta** | vs the old estimate |
| --- | --- | --- | --- | --- |
| **E** same-origin authority | B1 94,386 | 95,756 | **+1,370** | estimate was 600–1,000 — **under-estimated** |
| **F** P5/P8 terminal | T2 94,029 | 93,999 | **-30** | estimate was 50–150 — it is a SAVING |
| **H** HH/HL/LH/LL | B1 94,386 | 94,677 | **+291** | estimate was 400–800 — cheaper |

F saves tokens because `f_rc5Validity(i) != C_RC5_VALID` is shorter than the
compound `poiFreshActive` condition it replaces — the faithful rule is also the
cheaper one.

E is the surprise. The cluster test is a per-bar pass, so it is not
inline-multiplied, but it needs a ladder rank, a three-field origin comparison,
a zone-overlap test and a containment test, and it runs them pairwise.

## The exact final ledger

| step | running total | delta |
| --- | --- | --- |
| T2 base | 94,029 | — |
| + D structural origin | 96,097 | +2,068 |
| + G qualified liquidity (includes G1) | 100,126 | +4,029 |
| + E same-origin authority | 101,496 | +1,370 |
| + F P5/P8 terminal | 101,466 | **-30** |
| + H HH/HL/LH/LL | **101,757** | +291 |
| anchor correction | **+0** | already contained in the V3/V4 removal |
| trendline layer | **+0** | already inside T2, not double counted |

| | |
| --- | --- |
| **FINAL PROJECTED** | **101,757** |
| hard TradingView limit | 100,256 — **OVER by 1,501** |
| strict target (1,000 reserve) | 99,256 — **OVER by 2,501** |

## Summary-table audit — it is NOT redundant

The 975-token summary table was the last hoped-for free saving. Row by row:

| row | value | source | unique? |
| --- | --- | --- | --- |
| 0 | "P7 — BTRC Scanner" | title | chrome |
| 1 | Feed | `syminfo.prefix + ticker` | **duplicated** — the chart header shows it |
| 2 | Host TF | `timeframe.period` | **duplicated** — the chart header shows it |
| 3 | Global direction | `p7LastGlobalDir` | **UNIQUE** |
| 4 | Regime | `p7LastRegime` | **UNIQUE** |
| 5 | Momentum | `p7LastMomDir` | **UNIQUE** |
| 6 | Breakout | `p7LastBrk` | **UNIQUE** |
| 7 | Volatility | `p7LastVol` + abnormal flag | **UNIQUE** |
| 8 | Active POIs | `array.size(p7PoiIdx)` | **duplicated** — the POI table footer prints "N shown / M active" |
| 9 | Market framework | range high/low, or TREND | **UNIQUE** |

**Six of ten rows are unique, and there is no second dashboard to fold them
into.** The summary table is the ONLY place the global BTRC context appears, so
removing it is an information loss, not a redundancy cleanup. S2 as conceived
has no destination.

Even so, the arithmetic is worth stating:

| scenario | total | vs hard limit |
| --- | --- | --- |
| everything, faithful | 101,757 | OVER 1,501 |
| minus the summary table (losing six unique rows) | 100,782 | **still OVER 526** |
| minus summary AND Surface A | 100,639 | **still OVER 383** |

## Verdict: faithful single-indicator RC5 does NOT fit

This is now measured, not projected. Stripping the entire global-context
dashboard AND spending the private Surface-A extraction still leaves the build
**383 tokens over the hard compiler limit**, and 1,383 over the reserve target.

The presentation campaign is exhausted: gray styling, P7-Z simplification,
legacy framework removal, overlap arbitration, the trendline layer, table
compaction, column probes, Surface A and Surface B have all been measured. The
remaining semantic stages are all measured too. There is no unspent surface
large enough.

Per the author's CASE 3, work stops here and the exact shortfall is returned:

> **2,501 tokens to the strict target, 1,501 to the hard limit, with every
> figure a compiler measurement.**

---

# CORE / PANEL split: the CORE fits

## CORE without the diagnostic tables — measured

Removed, and only these: the summary table, the POI table, the row-string
construction whose sole consumer was that table, and the display-only location
strings (`lt`, `f.txt`) that fed it. **`loc` itself is KEPT** — it is the
framework location score feeding `liquidityScore`, so it is semantics, not
presentation. Every semantic field in the engine survives.

| variant | pad points | **BASE** | recovery |
| --- | --- | --- | --- |
| T2 | — | 94,029 | — |
| **CORE no-table** | 98 / 99 / 100 -> 100,338 / 100,435 / 100,532 | **90,791** | **3,238** |

**3,238, not the 2,968 the parts predicted** — exactly why the author said not
to trust the arithmetic. The extra 270 is the `lt` / `f.txt` display strings,
which were never counted in the earlier sub-costs because they live in
`f_fwPoi`, not in the table block.

A precision note worth recording: at N=97 the build was predicted to land at
100,241 against a 100,256 limit and therefore to COMPILE. It compiled. The
oracle is accurate to within 15 tokens at this scale.

## Trendline display filter — measured

Semantics untouched. Every `fwTls` record is kept, the persistence fix stands,
and a displayed line still survives touch, respect, wick-through and a
qualified sweep. Only DISPLAY ELIGIBILITY is added.

**The rule invents nothing.** It is the trendline qualification Stage G already
applies to liquidity — BOTH defining anchors must be swings the structural walk
actually used — applied to drawing. A line built from texture pivots is not a
structural trendline, so it is not drawn. Plus an exact-anchor-pair guard so one
relationship cannot print twice; lines sharing only ONE anchor describe
different relationships and both survive. No angle, touch-count, distance or
price tolerance. No forced maximum, and bullish and bearish remain independent.

| variant | **BASE** | delta |
| --- | --- | --- |
| CORE + G1 | 91,149 | — |
| **CORE + G1 + trendline filter** | **91,403** | **+254** |

## The CORE candidate

| step | running total | delta |
| --- | --- | --- |
| CORE no-table | 90,791 | — |
| + D structural origin | 92,859 | +2,068 |
| + G qualified liquidity (includes G1) | 96,888 | +4,029 |
| + E same-origin authority | 98,258 | +1,370 |
| + F P5/P8 terminal | 98,228 | **-30** |
| + H HH/HL/LH/LL | 98,519 | +291 |
| + trendline display filter | **98,773** | +254 |
| anchor correction | **+0** | already contained in the V3/V4 removal |

| | |
| --- | --- |
| **CORE CANDIDATE** | **98,773** |
| hard limit 100,256 | **1,483 under** |
| strict target 99,256 | **483 under** |

**The split works.** The same faithful semantics that were 1,501 OVER the hard
limit as one script are 1,483 UNDER it once the diagnostic tables move out —
and they clear the 1,000-token reserve target as well, with 483 to spare.

Nothing was weakened to achieve this. D, E, F, G and H are the same measured
faithful implementations; only table RENDERING moved.

## Honest status of the composition

The stage deltas are each a compiler measurement, but the CORE candidate is
their composition, not yet a single compiled artifact: D and G were prototyped
on the Stage-C lineage while E/F/H/T2 descend from the live-file lineage, so a
merged build has still to be assembled. Two things make the composition
trustworthy rather than hopeful — G1 measured 357, 357 and 358 on three
unrelated bases, and the N=97 boundary prediction held to 15 tokens — but the
merged CORE must still be built and measured before the architecture is frozen.
That is the next step, and it is the honest caveat on the 98,773.

---

# THE MERGED CORE — the composition becomes a fact

The caveat above is now closed. One artifact was assembled from ONE base,
containing every faithful stage, and measured directly on the real TradingView
compiler.

## How the merge was built

`tools/rc5_compose.py`'s ancestor — a single generator — starts from the
CORE-no-table + G1 + trendline-filter base and applies, in dependency order:

| step | what it adds |
| --- | --- |
| G plumbing | `FwLv` / `FwEv` carry the identity of the level they describe, `RcCand` |
| Stage E | same-origin authority (`rc5Subordinate`, ladder, one pass per bar) |
| Stage D | structural-origin gate, blocking at emission |
| Stage G declarations | kind codes, `RcEv`, qualification, shared-source test |
| Stage D per-bar | pivot candle → swing maps, per side |
| Stage G producer | POI far edges, qualification, deduplication |
| Stage G DISTRACTION | consumes `rc5Ev`, never the raw `fwEv` stream |
| Stage F | terminal means genuine invalidation or supersession |
| Stage H | HH / HL / LH / LL, previous pivot held in an ARRAY |
| Stage E display | the renderer honours semantic authority |

**One semantic join was made that no single-stage prototype could make.** Stage
G's `f_rc5Authoritative` was a `true` stub carrying the comment *"Stage E
supplies this"*. In the merged build Stage E exists, so it is wired to the real
subordinate map: a subordinate POI's far edge is not an independent liquidity
reference, because it is not an independent decision. Authority is also computed
BEFORE Stage G registers far edges, so the ordering is not accidental.

## Exact source transfer

The candidate reached the TradingView page through the clipboard, and the
transfer was PROVEN rather than assumed: the in-page SHA-256 of the received
string is `94e21bbf…`, byte-identical to the file on disk (381,770 chars, CRLF).
A localhost fetch was tried first and is blocked from the page's origin; that is
recorded so the next session does not re-derive it.

## The measurement

Three points, pad N ≤ 100, `BASE = TOTAL − 97·N − 41`:

| N | reported total | derived BASE |
| --- | --- | --- |
| 98 | 108,273 | **98,726** |
| 99 | 108,370 | **98,726** |
| 100 | 108,467 | **98,726** |

C2−C1 = 97, C3−C2 = 97. BASE1 = BASE2 = BASE3. The oracle validates itself.

**A fourth, unpadded save returned `success: true` with an 832,472-character
IL.** The merged CORE does not merely tokenise — it COMPILES on the real
compiler.

| | |
| --- | --- |
| **MERGED CORE** | **98,726** |
| hard limit 100,256 | **1,530 under** |
| strict target 99,256 | **530 under** |
| composed estimate 98,773 | **47 high** — the composition was accurate to 0.05% |

## RC5 PANEL

PANEL is composed from CORE, not written beside it (see
`tools/rc5_compose.py`). It removes the chart-space renderers and restores the
screen-space diagnostics; every semantic line in it is CORE's own line.

| N | reported total | derived BASE |
| --- | --- | --- |
| 98 | 106,603 | **97,056** |
| 99 | 106,700 | **97,056** |
| 100 | 106,797 | **97,056** |

Unpadded save: `success: true`, IL 817,161 characters. **PANEL compiles.**

| | |
| --- | --- |
| **RC5 PANEL** | **97,056** |
| hard limit 100,256 | **3,200 under** |
| strict target 99,256 | **2,200 under** |

The chart-space renderer layer therefore costs **4,908** tokens, and the
diagnostic tables cost **3,238**. Neither script needs the other's half.

## Static merge audit

Every intended block was verified present exactly once in the merged artifact,
and every superseded one verified absent:

* Stage B validity predicate, 5 call sites; Stage C provenance maps and writer
* Stage D gate predicate, its single blocking call site, both pivot maps
* Stage E subordinate map, authority pass, its per-bar call, both consumers
* Stage F new terminal predicate present — **old mitigation predicate absent**
* G1 role map; Stage G kind codes, `RcEv`, `RcCand`, qualification, dedup
* DISTRACTION reads `rc5Ev` — **the raw `fwEv` read is absent**
* Stage H HH/HL/LH/LL present — **the old dense SH/SL label is absent**
* trendline drawn from `fwTls`, display filter, exact-anchor guard
* gray fill / gray border / black text / text size 31
* `xloc.bar_index` occurrences: **0**
* `table.new` / `table.cell` in live code: **0** (four surviving mentions are
  comments)
* duplicate function DEFINITIONS across 127 `f_` functions: **0**

Two near-duplicates are recorded rather than silently merged: `f_rc5IsReversal`
(Stage D) and `f_rc5IsReversalE` (Stage E) express the same reversal-family set
in two forms — D as an explicit disjunction, E as "has a ladder rank". They
agree today. Unifying them would save tokens and remove a drift risk, but it
changes two measured stages at once, so it is offered as an author decision, not
taken unilaterally.

One stale comment is also recorded: the FVG-vs-origin dominance map still says
*"RC5 authority (Stage E) does not exist yet. It is the first thing to delete
once authority resolves those duplicates semantically."* Stage E now exists —
but Stage E refuses an imbalance only when it lies WHOLLY INSIDE the primary,
while the dominance map suppresses on shared candle time and direction
regardless of geometry. They are different rules, so deleting the map would make
some currently hidden FVGs visible. That is a display change the author should
decide; the rule is kept and the comment flagged.
