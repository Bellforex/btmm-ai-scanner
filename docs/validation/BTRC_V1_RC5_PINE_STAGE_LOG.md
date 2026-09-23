# BTRC-V1 RC5 — Pine port stage log

One section per semantic stage. Every stage must record the source identity, a
TradingView compile, a live attach, a live runtime observation, and an EXACT
token measurement. No stage is closed on a compile alone.

Scratch layout `BAH-RC5-LAB` (`fn3ash9L`), account `bellcare1994`, host M15,
symbol `FX:EURUSD`. The protected `bellforex` layout is not touched by any
stage here.

## The token oracle

TradingView reports the compiled token count only inside compile error
`CE10117`. The measurement procedure, unchanged from the RC4 work:

* pad block = `\nif barstate.islast\n    log.info("padK")\n`, **97 tokens each**;
* `POST https://pine-facade.tradingview.com/pine-facade/save/next/<USER;id>/`
  with `FormData{name, source}` and `credentials: 'include'`, fired against a
  DISPOSABLE script so the real build is never contaminated;
* read `outputILLength` out of the error **ctx**, not the message — the message
  carries a literal `{outputILLength}` placeholder and the code `10117`, so a
  loose regex returns `10117` and looks plausible.

`translate_light` is NOT a token gate. It returned `success: true` for source
the real compiler rejected at 110,249 tokens.

A measurement is accepted only when three points agree exactly:
`C(n+1) - C(n) == 97 * (N(n+1) - N(n))` for both intervals, and
`BASE = C - 97*N` identical at all three. No averaging, no rounding.

## Stage A — DOJI (POI type code 33)

Adds `C_POI_DOJI = 33`, the `DOJI` input, the 33-entry `p7zTypeOn` filter array
and the local DOJI label at the two `bahui.poiTypeLabel` call sites.

### Source identity

| | |
| --- | --- |
| file | `tradingview/btmm_poi_btrc_scanner_rc5_user.pine` |
| lines | 6,771 |
| raw SHA-256 | `74e1db7ce5f9ffa086257370c89736f9d21652457482f3e211076505ee04b54e` |
| LF-normalised SHA-256 | `45dfd2b55fbba062f929242fffcaa800b0bf5facdcadfb17df571f9f37683a32` |
| TradingView script | `USER;e2b236547ce4445681c1f3d582906de2` |
| saved version | **9.0** |
| deployed == local | yes, LF-normalised SHA equal, zero pad blocks present |

The base build it derives from is
`tradingview/btmm_poi_btrc_scanner_rc5_base_library_backed.pine`
(`0175ab6a1574333a6b0db4fd3130bc90db3fa30fa7e9c8f30d78263ea80c3082`, 6,765
lines).

### Token measurement

Disposable oracle script `RC5 TOKEN ORACLE - STAGE A`
(`USER;a35251d296f64495a173d66a2e55ea9f`), Stage-A source plus N pad blocks.

| N | reported `outputILLength` | `C - 97N` |
| --- | --- | --- |
| 60 | 101,827 | 96,007 |
| 80 | 103,767 | 96,007 |
| 100 | 105,707 | 96,007 |

`103,767 - 101,827 = 1,940 = 97 x 20` — exact.
`105,707 - 103,767 = 1,940 = 97 x 20` — exact.
`BASE1 == BASE2 == BASE3 = 96,007` — identical.

| | |
| --- | --- |
| **Stage-A tokens** | **96,007** |
| limit | 100,256 |
| **headroom** | **4,249** |
| utilisation | 95.762% |

### Runtime gate

| check | result |
| --- | --- |
| compiles on TradingView | pass, no `CE10117` |
| attached to `BAH-RC5-LAB` M15 | pass |
| legend unambiguous | pass — exactly two studies, `[RC4 MARKET FRAMEWORK]` and `[RC5 USER]` |
| compile/runtime error on `[RC5 USER]` | none |
| Stage-A semantics visible at runtime | **DOJI present as the 19th POI type filter**, after `RESISTANCE ZONE` |
| renders with RC4 hidden | pass — POI zone bands, Market Framework box (46 active), P7 POI table (8 shown / 46 active) |

Hiding RC4 is what makes the render attributable: every object left on the
chart is `[RC5 USER]`'s own output, so "the chart is still showing RC4" cannot
be mistaken for a passing RC5 runtime.

A third scanner study, a stale `[RC4 MARKET FRAMEWORK] . 4.0` attach carrying
`CE10117`, was removed. The Basic plan caps two indicators per chart, so the
third attach was also the cause of the legend's error markers.

### Open, carried forward

`[RC4 MARKET FRAMEWORK]` on this chart raises
`Error on bar 1799: The requested historical offset (863) is beyond the
historical buffer's limit (862)`. It is on RC4, not RC5, and belongs to the
later RC4-to-BAH parity stage rather than to Stage A. The frozen RC4 artifact
(`USER;2ec15aca50de466c9a1f911f91b07e9b`, v16.0) is unmodified.

## Stage B — VALIDITY, and the layer below DISPLAY

Ports `Rc5Validity` / `rc5_validity` / the display half of
`display_hidden_reason` from `poi/rc5_semantics.py`. Authority is the other
half and arrives in Stage E; until then the display gate is validity alone.

### What changed, and why it is not cosmetic

RC3/RC4 filtered the visual layer on `poiFreshActive`, which drops at the FIRST
TOUCH. So a zone disappeared the moment price entered it. The frozen lifecycle
sets `poiTermReason = C_POI_TERM_MITIGATED` at that first contact and the
earliest cause wins, which means a POI that was touched and only later broke
down still records MITIGATED — "was mitigated" says only that price has been in
the zone, never that the zone failed.

RC5 splits the axes. `poiFreshActive` keeps its frozen RC4 meaning and is no
longer read for display. Visibility is now:

| state | drawn | carrier in Pine |
| --- | --- | --- |
| fresh | yes | — |
| mitigated / re-mitigated | **yes** | `C_POI_TERM_MITIGATED` is ignored |
| far-side break, then reclaimed | **yes** | `FALSE_INVALIDATION_CONFIRMED`, never sets `poiTerminal` |
| genuine far-side failure | no | `poiTerminal` |
| engulfing superseded by its own ORDER BLOCK | no | `C_POI_TERM_PROMOTED` |

Measured on the frozen captures, that is M5 6 mitigated + 14 re-mitigated + 8
reclaimed, H4 10 + 16 + 1, M15 3 + 12 + 3 — all of which RC3/RC4 hid on first
contact.

`poiTerminal` is the Pine carrier of `GENUINE_INVALIDATION_CONFIRMED`: it is
written in exactly ONE place, immediately after
`status := C_POI_LC_GENUINE_INVALIDATION_CONFIRMED`, so it — not the terminal
cause — is what Python's first branch tests. `poiInvalT` is likewise written
only under that branch, so `C_POI_TERM_INVALIDATED` implies `poiTerminal`; the
predicate tests both anyway, matching the Python structure rather than relying
on the implication.

### The dependency Stage B had to break

The visual layer selected from `p7PoiIdx`. That is the set P5 still EVALUATES,
and the RC4 rule removes a POI from it once its final P5 row is emitted — so
selecting from it would have deleted a mitigated zone from the chart no matter
what the validity gate decided, and Stage B would have measured as a no-op.
Python has no such narrowing: `active_display_pois` walks every observation.

Display therefore now reads the POI REGISTRY directly. This is sound because
the zone projection consumes only registry geometry — `poiType`,
`poiDirection`, `poiZoneTop`, `poiZoneBottom`, `poiCandTime` — and never a P5
field. The P5 loop already iterates the whole registry (`p5N =
array.size(poiStatus)`), so availability is unchanged. `p7zFreshIdx` was
renamed `p7zVisibleIdx`, because it no longer holds fresh POIs.

The P7 POI TABLE still selects from `p7PoiIdx` and so still follows the RC4
terminal rule. That is deliberate — the table's rows are P5 decisions — and it
is Stage F's subject. Until Stage F lands, the table and the zones are allowed
to disagree.

### Token measurement

Same disposable oracle, Stage-B source.

| N | reported `outputILLength` | `C - 97N` |
| --- | --- | --- |
| 60 | 101,863 | 96,043 |
| 80 | 103,803 | 96,043 |
| 100 | 105,743 | 96,043 |

Both intervals exactly `97 x 20 = 1,940`; all three bases identical.

| | |
| --- | --- |
| **Stage-B tokens** | **96,043** |
| delta vs Stage A | **+36** |
| **headroom** | **4,213** |
| utilisation | 95.798% |

### Source identity

| | |
| --- | --- |
| lines | 6,819 |
| raw SHA-256 | `87e9d8c52065c4713a57f3898847822533822287d88fe38e8fd9b5d0a81b8eca` |
| LF-normalised SHA-256 | `4ee1890ae16a3651bfffb93286db736f085f4916744aea5f40048da474df2ffe` |
| saved version | **10.0** |
| deployed == local | yes, LF SHA equal, zero pad blocks |

Transferred by `iconv -t UTF-16LE | clip.exe`, hashed IN THE PAGE before the
editor was touched, then posted from that verified string — so the deployed
bytes are proven equal to the repo file rather than assumed.

### Runtime gate

| check | result |
| --- | --- |
| compiles | pass, `success: true` at pad 0 |
| M15 attach after reload | pass, no compile or runtime error on either study |
| renders | pass — markedly more zones retained, including zones price has already traded through |
| **M5 attach** | **pass, no error** |
| RC4 alongside | no error |

M5 is checked explicitly because Stage B is what makes it risky. Widening the
selection from `p7PoiIdx` to every valid POI enlarges the input to the zone
GROUPING pass, and grouping is the code that previously raised RE10110 by
exceeding TradingView's 20-second budget on M5. It did not recur.

The exact size of the display-set change is NOT claimed here. The same-viewport
RC4-vs-RC5 comparison is confounded by autoscale, and a screenshot is not a
census; the numeric display set is established in the Python-to-Pine parity
stage, not asserted from a picture.

### Correction to the Stage-A record

Stage A recorded `[RC4 MARKET FRAMEWORK]`'s historical-buffer runtime error as
a stale-state artifact because it did not return after that reload. That was
wrong, and Stage C's cold load shows it: the error RECURS on a cold load and
clears once the chart settles. It remains an RC4 issue, not an RC5 one, and
still belongs to the RC4-to-BAH parity stage — but it is a real recurring
condition, not a one-off.

## Stage C — structural provenance

Ports the structural half of `Rc5PoiSemanticRecord`: the `OriginClusterKey`
STRUCTURAL triple — (confirming transition break candle, broken swing, origin
swing) — written once when the formation locks and never rewritten from later
structure. It is the input Stage E arbitrates on.

It is a sidecar for the same reason it is one in Python: structural facts are
PER PREFIX, so asking the final context "what is this POI's origin?" gives the
wrong answer. Only recording it as it happens answers the right question.

### The design that had to be thrown away — measured, not guessed

The obvious port threads the triple through `f_poiEmit` and pushes three
parallel arrays in `f_poiAppend`, mirroring the existing registry. It was built
and MEASURED:

| design | base tokens | delta vs Stage B |
| --- | --- | --- |
| triple threaded through `f_poiEmit` / `f_poiAppend` | 98,081 | **+2,038** |
| triple in three maps, written at the two sites that know it | **96,523** | **+480** |

**Pine inlines user functions.** `f_poiEmit` has nine call sites and
`f_poiAppend` is inlined inside it, so each added parameter and each added
`array.push` is paid again at every expansion. Against a 4,213-token budget,
+2,038 for provenance alone was not affordable. The map design carries the same
facts for 480 and leaves 3,733.

Only two sites in the engine ever know a structural origin — the ORDER BLOCK
emission and the counter-trend release, both inside `f_poiGateOrderBlocks`'s
`if not na(best)` — so a map keyed by registry index is the natural shape. The
registry is append-only ("emitted POIs are never removed"), which is what makes
the index a stable key.

The +2,038 measurement was taken at a single pad point and is reported here as
the reason a design was rejected. It is NOT an accepted stage count and was
never three-point validated; only the design that ships is.

### Write-once, and what absence means

`f_rc5Provenance` refuses to overwrite an existing entry, because the Python
record is immutable historical evidence. A negative index means the emission
deduplicated against an existing POI, whose provenance was already recorded at
ITS qualifying prefix — so skipping is correct, not a dropped write.

A POI ABSENT from these maps carries no structural origin. Stage E must then
use the weaker FORMATION_CANDLE key, which `poi/authority.py` restricts to
reversal synonyms and forbids from touching an FVG. Absence must never be read
as "origin unknown, cluster anyway".

### Token measurement

| N | reported `outputILLength` | `C - 97N` |
| --- | --- | --- |
| 60 | 102,343 | 96,523 |
| 80 | 104,283 | 96,523 |
| 100 | 106,223 | 96,523 |

Both intervals exactly `97 x 20`; all three bases identical.

| | |
| --- | --- |
| **Stage-C tokens** | **96,523** |
| delta vs Stage B | **+480** |
| **headroom** | **3,733** |

### Source identity and runtime

| | |
| --- | --- |
| lines | 6,860 |
| raw SHA-256 | `804b47383228963092c59aaa6decef80867dba9e6ae831ad18b9d0d1e793624a` |
| LF-normalised SHA-256 | `7c0e5045974977a41e57837f8108a9e3706bea08cd0a2a339627d6d1709564d1` |
| saved version | **11.0** |
| deployed == local | yes, LF SHA equal, zero pads |
| compiles | pass at pad 0 |
| M15 attach after cold reload | pass, no error on `[RC5 USER]`, renders |

## Headroom trajectory

| stage | tokens | headroom | delta |
| --- | --- | --- | --- |
| A — DOJI | 96,007 | 4,249 | — |
| B — validity / display | 96,043 | 4,213 | +36 |
| C — structural provenance | 96,523 | 3,733 | +480 |

Remaining: D structural origin, E authority, F P5/P8 terminal, G causal
qualified liquidity + sweeps + DISTRACTION, H structure labels + readability.

**G is the risk.** In Python it is `poi/rc5_liquidity.py` plus
`poi/rc5_sweeps.py` — six reference families, POI far edges, semantic
deduplication and a per-bar causal producer. Stage C's lesson is that a Pine
port's cost is dominated by inline expansion rather than by source length, so
the remaining budget cannot be allocated from Python line counts. It is
measured stage by stage, and where a stage does not fit, that is reported as a
measured wall rather than absorbed by quietly dropping semantics.

## Stage D — the structural-origin gate: a measured architectural fork

Stage D refuses a reversal-family candidate that does not sit at a structural
extreme in the direction it claims (`poi/structural_role.py`). The algorithm is
self-contained and every primitive it needs already exists in the Pine build --
confirmed swings, break events with their broken swing, the framework range,
liquidity levels, trendlines.

The problem is not the algorithm. It is WHERE it has to run.

In Python the gate runs at `lock_candidate`: a refused candidate is never
mapped, so it produces NO `PoiObservation`, no P5 row and no P8 event. The
measured POI counts in `BTRC_V1_RC5_FINAL_PYTHON_IMPACT.md` (M15 218, M5 249)
are POST-gate.

The Pine equivalent of `lock_candidate` is the emission path, and Stage C
established what that costs: **Pine inlines user functions**, so anything added
to `f_poiEmit` is paid at all nine call sites and anything added to
`f_poiAppend` at each of its expansions. Stage C's threaded triple -- three
ints -- cost 2,038 tokens there. The role computation is far larger than three
ints: a per-side pivot lookup across the source candles and formation span,
then three `zone_reaches` sweeps over range, liquidity and trendline levels.

Two designs, and they are NOT semantically equal:

**(a) Block at emission, as Python does.** Faithful: refused candidates never
enter the registry, so POI counts match Python exactly. Estimated at roughly
1,200-1,800 tokens of the 3,733 remaining, and the estimate is soft precisely
because inline expansion -- not source length -- dominates.

**(b) Refuse by suppression in one per-bar pass.** The candidate is appended,
then a single pass over the registry marks it structurally refused, and
validity/display, the authority set and P5/P8 all honour the mark. Cheap,
because it runs once per bar rather than at nine inlined sites. But the record
still EXISTS, so Pine's raw POI count exceeds Python's, and "Python-to-Pine
parity" would have to be defined on the authoritative set rather than on the
registry. That is a change to what parity means, not an implementation detail.

### Why this is reported rather than decided

Even under (a), the remaining budget after D and E is very unlikely to hold
Stage G -- the causal qualified liquidity, the six reference families, semantic
deduplication and the per-bar sweep producer, which in Python is
`poi/rc5_liquidity.py` plus `poi/rc5_sweeps.py`. Spending the rest of a
hard-capped 3,733 tokens on D and E and only then discovering G does not fit
would waste the budget on the wrong stages.

The honest position: the full RC5 semantic set does not obviously fit in one
Pine script, and the allocation of what remains is an author decision.


## Phase V1 — the neutral POI visual contract (presentation only)

Author requirement: every visible POI zone is drawn NEUTRAL GRAY with BLACK
annotation text at size 31, whatever its direction.

### What changed

One block, in the single POI drawing path:

| | before | after |
| --- | --- | --- |
| fill | `color.new(bullish ? green : red, 90)` | `color.new(color.gray, 60)` |
| border | `color.new(hue, 25)` | `color.new(color.gray, 20)` |
| text | `color.new(hue, 10)` | `color.black` |
| text size | `size.auto` | `31` |

The direction local that fed the hue was deleted, because the hue was its only
reader. That is what makes the contract structural rather than a style tweak:
there is now NO direction branch anywhere in the zone drawing, so bullish,
bearish, DOJI, FVG, engulfing, pressure wick, star, B2S/S2B and reference-zone
families cannot diverge in colour. They share one `box.new`.

**Direction is not lost.** It remains in the engine, the P7 table's Dir column,
P5 permissions, P8 events and every RC5 semantic layer. It simply stops being
carried by colour.

### No semantic drift

The diff touches 24 lines, all inside the box construction. Detection,
authority, lifecycle, suppression, validity and sweep semantics are untouched,
and so is the Stage-B visibility gate: only valid, display-eligible POIs render,
mitigated-but-still-valid zones stay visible, and genuinely invalidated or
superseded ones stay hidden.

### Token delta

| N | reported | `C - 97N` |
| --- | --- | --- |
| 60 | 102,237 | 96,417 |
| 80 | 104,177 | 96,417 |
| 100 | 106,117 | 96,417 |

Both intervals exactly `97 x 20`; all three bases identical.

| | |
| --- | --- |
| Stage C true | 96,482 |
| **Stage C + visual contract, true** | **96,376** |
| **delta** | **-106, a SAVING** |
| **headroom** | **3,880** (was 3,774) |

Deleting the direction branch and three `color.new` tints costs less than the
two gray literals it leaves behind, so the visual contract IMPROVES the budget.

**No BAH helper change was required.** The edit is entirely local to the
scanner: `box.new` arguments only. The public library was not touched, and no
proprietary logic moved anywhere.

### Source identity

| | |
| --- | --- |
| lines | 6,873 |
| raw SHA-256 | `4a300e8e40cf333c81c09f44ee0fe8c5bbf883f4c9e902cb7eb9c5caa33c2dbd` |
| LF SHA-256 | `4c6451cae185265efc0911bab1e2f12e495e835bac087f67e8fdf727fbabd052` |
| saved version | **12.0** |

### Phase V2 — proof, and the trap that nearly faked it

Verified live on `BAH-RC5-LAB` (`fn3ash9L`), account `bellcare1994`, M15
FX:EURUSD, RC4 hidden so every drawn object is unambiguously RC5's: gray boxes,
black labels, large fixed text, across SELL FVG, RESISTANCE ZONE and BEARISH
PRESSURE WICK.

**The trap.** The first three attempts showed RED zones and looked like a
failed patch. They were not. The tab was `document.hidden`, so TradingView
never repainted and every canvas sat at its 300x150 default — the screenshots
were a STALE FRAME from before the patch. At one point the DOM legend still
listed a study the chart model had already removed.

Two things were needed, and both are worth keeping:

1. the recorded renderer recovery (`resetLayoutSizes` / `resize` / `_adjustSize`
   / `paint`) to size the canvases;
2. spoofing `document.hidden` and `document.visibilityState` so TradingView's
   own render loop runs at all.

**Never verify a visual change from a screenshot without first confirming the
canvas is not 300x150 and `document.hidden` is false.** The chart model
(`dataSources()`, `properties().visible`) is the reliable source of truth; the
legend DOM and the painted canvas both lie when the tab is hidden.

Re-attaching the study from Indicators is what forced the new version to
compile; a reload alone did not, because the hidden tab served cached output.

### Known consequence, reported not hidden

Size 31 is fixed, so where several zones stack closely their labels overlap.
`size.auto` previously avoided this by shrinking text to fit. The author's
contract specifies 31, so this is accepted and flagged for the review pass; it
is a legibility question, not a semantic one.

The symbol was also restored to FXCM (`FX:EURUSD`) on the scratch layout, which
had drifted to an Eightcap feed. `bellforex` was never opened.

## Stage P1 — ARM E BASE SIZE (Python freeze `28d432e`)

The first stage of the RC5 semantic port. Deliberately code-REMOVING and
nothing else: no `BaseFamily`, no arrival classification, no formation
ownership. Those land in P2-P4 only after this is measured.

### What changed

| # | change | site |
| --- | --- | --- |
| 1 | `C_POI_SMALL_CANDLE_STANDARD = 0.50` -> `C_POI_BASE_SIZE_STANDARD = 0.60` | CORE 2389 |
| 2 | `C_POI_SMALL_CANDLE_STRONG` -> `C_POI_BASE_SIZE_STRONG` (value unchanged) | CORE 2390 |
| 3 | **deleted** the reciprocal Base gate and the now-unused `ratio` variable | CORE 3320-3322 |
| 4 | **deleted** the redundant `ratio >= C_POI_OB_RATIO_STRONG` from the strong Base gate | CORE 3367 |

Renaming is token-neutral (an identifier is one token whatever its length); the
saving comes entirely from 3 and 4.

**`C_POI_OB_RATIO_STANDARD` and `C_POI_OB_RATIO_STRONG` are UNTOUCHED** — still
`2.0` / `3.0`, still read at the four ORDER BLOCK and ENGULFING sites (CORE
3027, 3037, 3087, 3097) and nowhere else. The shared constant was never
modified, which is what keeps those two detectors provably unchanged: the only
edited region is inside `f_poiDetectBases`.

Deleting `ratio >= C_POI_OB_RATIO_STRONG` is provably a no-op: the surviving
condition `maxBaseRange <= 0.3333 * departureRange` implies it, because
`0.3333 < 1/3`.

### Source identity

| | |
| --- | --- |
| file | `tradingview/btmm_poi_btrc_scanner_rc5_user.pine` |
| lines | 7,006 (was 7,010) |
| raw SHA-256 (LF) | `21aae4b3ae5f13108177be4ff7bbf2d3de8dd97d2a3b654191d9dbcdeeb69950` |
| oracle script | `USER;a35251d296f64495a173d66a2e55ea9f` (disposable) |
| account | `bellcare1994` (id 57555264), verified before every POST |
| layout | `BAH-RC5-LAB` (`fn3ash9L`) |

Exact source transfer was proven per POST: the clipboard text was hashed
IN-PAGE with `crypto.subtle` and compared to the on-disk SHA-256. All four
transfers matched exactly, and none carried CRLF.

### Token measurement

`MAX_IL_LENGTH` read back from the error ctx: **100,256**.

| N | reported `ctx.outputILLength` | `C - 97N` |
| --- | --- | --- |
| 10 | 100,341 | **99,371** |
| 12 | 100,535 | **99,371** |
| 14 | 100,729 | **99,371** |

`100,535 - 100,341 = 194 = 97 x 2` — exact.
`100,729 - 100,535 = 194 = 97 x 2` — exact.
All three derive the same base. No averaging, no rounding.

| | |
| --- | --- |
| previous merged CORE | 99,386 |
| **Stage P1 CORE** | **99,371** |
| **delta** | **-15** |
| hard ceiling | 100,256 |
| **hard headroom** | **885** (was 870) |
| strict engineering target | 99,256 |
| **strict reserve deficit** | **115** (was 130) |

### Compile gate

The unpadded P1 source returns `success: true` with no `CE10117`.

### Acceptance, honestly scoped

| check | result |
| --- | --- |
| compiles on TradingView | **pass** |
| exact token delta measured, 3 points agreeing | **pass**, -15 |
| Order Block constant unmodified | **pass** — static proof, `C_POI_OB_RATIO_*` unchanged and read only at OB/Engulfing sites |
| Engulfing constant unmodified | **pass**, same proof |
| strong-gate simplification is a no-op | **pass** — algebraic, `0.3333 < 1/3` |
| golden Base satisfies Arm E *on Pine* | **NOT YET PROVEN HERE** |

The last row is stated plainly rather than implied. Proving the golden Base on
the Pine side needs record-level Python-Pine parity on the frozen M15 capture,
which the port plan schedules after the semantic stages. A compile and a token
count do not demonstrate detector behaviour, and this stage does not claim they
do.

### PANEL

Regenerated from CORE by `tools/rc5_compose.py` (6,800 lines, was 6,804). Not
hand-edited. `test_rc5_panel_composition` and
`test_pine_line_ending_contract` pass.

## Stage P2 — CAUSAL BASE ARRIVAL: design finding, NOT implemented

Investigated before writing code, and it changes the staging.

### What Pine already has

`f_p2StructureWalk` returns `p2bEvents`, held as `p3Events`
(`array<StructEventRec>`, CORE 514/2042). Each record carries
`transitionCode` (`C_ST_TR_*`) and `availabilityTime`, so the direction after
any transition is derivable and a "direction at instant t" lookup is a small
scan over state that ALREADY exists — no second structure engine, exactly as
the port plan requires.

### What Pine does NOT have

1. **`p2Direction` is current-only.** It is a single `var int` (CORE 489),
   assigned once per bar from the walk. A Base is emitted when its DEPARTURE
   closes, so reading `p2Direction` there gives the direction at the departure,
   NOT at the Base's first candle, which is what Python reads. Those coincide
   often and are not the same rule; using the current value would be a silent
   approximation and is refused.

2. **No bootstrap entry.** Python's `_direction_timeline` seeds from the first
   HH+HL / LH+LL relationship pair BEFORE any transition exists. `p3Events`
   holds transitions only. A Base whose first candle falls after the bootstrap
   but before the first transition would therefore be `UNDETERMINED` in Pine
   and a real family in Python.

   On the M15 forensic capture this happens to bite nothing — the bootstrap is
   2026-09-18 18:30, the first transition 19:15, and the three Bases in that
   region all start before 18:30 — but that is a property of one capture, not
   of the rule.

### Why P2 is not independently measurable

Dead code costs **0 tokens** on this compiler (measured in the RC4 work). A
`BaseFamily` that nothing consumes is eliminated, so porting P2 alone would
report a ~0 delta and prove nothing. The family's only consumer is the
standard-family gate, and that gate's only consumer is formation ownership —
P3.

**P2 and P3 must therefore land and be measured together.** Splitting them as
originally staged would produce a meaningless measurement for P2 and load its
entire real cost onto P3.

### Author decision required before P2/P3

Port the bootstrap seed as well (faithful to Python, costs tokens), or accept
`UNDETERMINED` before the first transition and disclose the divergence. The
second is cheaper and is a real semantic difference, so it is not taken here.

### Capacity context for that decision

| | |
| --- | --- |
| Stage P1 CORE | 99,371 |
| hard headroom remaining | **885** |
| strict reserve deficit | 115 |

P2+P3+P4 must all fit inside 885 tokens. The earlier RC5 capacity measurement
put the full set of RC5 additions at 3.4-4.3k tokens over budget, and P1
recovered 15. That gap is the binding risk on this port and is flagged now,
before stages are spent, rather than discovered at the hard stop.

## Capacity recovery audit (author decision 2) — MEASURED

Every number below is a real `CE10117` reading on the disposable oracle
`USER;a35251d296f64495a173d66a2e55ea9f`, account `bellcare1994`, layout
`BAH-RC5-LAB`. Each probe's clipboard text was SHA-256 hashed in-page and
compared to the on-disk digest before the POST; every transfer matched.

### Method, and its one shortcut stated plainly

The pad arithmetic (`BASE = C - 97N`) was validated to three points at Stage P1
(N=10/12/14, both intervals exactly `97 x 2`). The survey below therefore uses
ONE point per probe, with an explicit **control**: unchanged P1 CORE re-measured
at N=50 must return the already-known 99,371.

| control | N | `C` | `C - 97N` |
| --- | --- | --- | --- |
| P1 CORE, unchanged | 50 | 104,221 | **99,371** — matches the 3-point result exactly |

The control passes, so single-point survey readings are trustworthy here. A
build that is actually ADOPTED still gets three points.

### Renderer deletion ceilings

Probes CUT one presentation region and change nothing else. The regions are the
ones `tools/rc5_compose.py` already knows about, so this measures exactly what a
CORE/VIEW split could move.

| probe | region | N | `C` | base | **cost** |
| --- | --- | --- | --- | --- | --- |
| R1+R2 | structure overlay — BOS/CHOCH **and** HH/HL/LH/LL | 50 | 103,185 | 98,335 | **1,036** |
| R3 | external structural trendline renderer | 50 | 103,057 | 98,207 | **1,164** |
| R4 | P7-Z POI zone boxes and labels | 90 | 103,970 | 95,240 | **4,131** |
| R-ALL | all three together | 90 | 101,779 | 93,049 | **6,322** |

R4 first compiled clean at N=50 — the pad could not reach the ceiling — which
is itself the finding that it is the dominant block; it was re-probed at N=90.

The individual costs sum to 6,331 against a measured 6,322 for all three: a
9-token overlap. The regions are effectively independent, which means their
costs can be added when planning a split.

27 source lines cost 1,036 tokens. That is inlining, and it is why these had to
be measured rather than estimated from line counts.

### The proposed split, measured as a build

| probe | N | `C` | base |
| --- | --- | --- | --- |
| CORE minus structure overlay minus trendline renderer | 60 | 102,991 | **97,171** |

Saving **2,200**, exactly `1,036 + 1,164`.

| | value | target | |
| --- | --- | --- | --- |
| CORE after split | **97,171** | <= 97,256 preferred | **met** |
| hard headroom | **3,085** | >= 3,000 | **met** |
| strict headroom (vs 99,256) | **2,085** | >= 2,000 | **met** |

**Extracting structure + trendline PRESENTATION alone hits every capacity
target, and the POI renderer never has to move.** That is the split the port
plan preferred on architectural grounds — POI rendering depends on authority,
validity and ownership, so moving it would duplicate far more machinery — and
the measurement independently says it is also sufficient.

### Local recovery: the flagged duplicate is not a duplicate

`f_rc5IsReversal` and `f_rc5IsReversalE` were recorded as the same family set
expressed twice. They are not the same implementation:

* `f_rc5IsReversal(ty)` — an explicit 13-term `or` chain (CORE 2666), **one**
  call site (CORE 3013);
* `f_rc5IsReversalE(ty)` — `f_rc5LadderRank(ty) < 99` (CORE 2614), two call
  sites.

Collapsing the chain into the ladder form is plausible and cheap, but it is only
sound if `REVERSAL_LADDER` contains exactly those 13 types and nothing else —
a semantic equivalence that must be proven against the frozen Python ladder
first, not assumed from the names. **Not merged, not measured, and not counted
toward recovery.** Doing it on resemblance is exactly the refactor the audit
warned against.

### Conclusion

A third generated VIEW script **is necessary** — local renderer deletion is the
only place the tokens are, and the semantic engines cannot be touched — and at
the structure+trendline scope it is also **sufficient**. It is NOT implemented
here: pricing it was the authorised step, and standing up a third generated
artifact (composer support, anti-drift tests, and a runtime check that VIEW
recomputes only the minimum structural subset) is its own unit.

## VIEW dependency closure — evidence, and what it does NOT prove

The port plan requires an EXECUTABLE dependency report before VIEW is built, not
a comment. `tools/rc5_view_closure.py` is that report. Its history matters as
much as its output.

### Direct inspection: the two renderer dependencies are structural

This part is solid, and was obtained by reading the actual producers rather than
by any tool:

| renderer needs | produced by | verdict |
| --- | --- | --- |
| `rc5SwingRole` | `f_rc5MarkSwing` called only from `p3Events` (transitions) and `p3Swings` (confirmed swings), CORE 6326/6338 | structural |
| `fwTls` | `fwTls := tls` where `tls = f_detectTrendlines(wClose, wAtr, swings, scTlAtr)`, CORE 2179-2181 | P1 only — closes, ATR, swings |

Neither reaches POI analysis, authority, ownership, P5, P8 or BTMM. The
architecture is not obviously wrong, which is what allows the build to proceed.

### Two unsound analyser attempts, reported rather than shipped

**Attempt 1** indexed only top-level declarations and reported a closure of
**20 symbols with no forbidden hits**. That was FALSE and reassuring, which is
the worst combination. This file does not encapsulate the structure engine in
functions: it fills state from the per-bar flow, so `fwTls := tls` was invisible.

**Attempt 2** added assignment producers and still reported 20, because the
producing statement's right-hand side (`tls`) is an INDENTED local that a
top-level index does not contain either.

**Attempt 3** indexes definitions at any indentation. Scope-blind by design, so
it over-approximates — the safe direction for a "reaches nothing forbidden"
claim.

### What attempt 3 actually says

| | |
| --- | --- |
| definitions indexed | 1,449 |
| reachable from the two render roots | **320** |
| excluded | 1,129 |

**22% of the file.** That supports the claim VIEW is a genuine subset rather
than the whole scanner — which is the question the runtime gate cares about.

Two flags it raised, both examined rather than waved through:

* `f_poiRange`, `f_poiBody`, `f_poiUpperWick`, `f_poiLowerWick`, `f_poiBodyEff`,
  `f_poiBullClosePos`, `f_poiBearClosePos` — these are `high - low` and
  `abs(close - open)`. **Candle arithmetic wearing a POI prefix**, legitimately
  needed by the structure engine. The `f_poi` forbidden-prefix rule was too
  blunt and has been narrowed to `f_poiDetect` plus the registry functions by
  name.
* `poiType`, `poiDirection`, `f_rc5PoiKind` — reached ONLY through single-letter
  in-flow locals (`ti`, `ty`, `di`, `on`) that collide across scopes. Reported
  as **INCONCLUSIVE**, not as pass and not as fail.

### The honest limit

A scope-blind analyser cannot settle those three. The definitive dependency
check is the Pine compiler on a constructed VIEW: if VIEW compiles without the
POI registry, it does not depend on it. That is the next step, and it is why
VIEW was not built on the strength of this tool alone.

### Not done in this unit

VIEW composer, anti-drift tests, real generated-CORE measurement, VIEW token
count, and the runtime gates (VIEW alone, CORE+VIEW, CORE+VIEW+PANEL). P2+P3
remain blocked behind them, as the plan requires.

## VIEW extraction — STOP. The trendline renderer is not a structural consumer.

Building VIEW was the authorised next step, and mapping its real boundaries
before generating it found a dependency that neither direct inspection nor the
scope-blind analyser had pinned down. It is a genuine forbidden dependency, so
per the port plan this stops rather than being worked around.

### The path

| step | site |
| --- | --- |
| the one-trendline winner tests whether a candidate was already hit | `bool tlHit = map.contains(rc5TlHit, ...)` — CORE 6550 |
| `rc5TlHit` is written by the RC5 sweep/reaction qualification engine | `map.put(rc5TlHit, pr.ref, true)` — CORE 6476 |
| that engine qualifies reactions against EVERY reference kind, POI included | `C_RC5K_POI`, and directly reads `poiDirection`, `poiZoneBottom`, `poiZoneTop`, `poiAvailTime`, `f_rc5PoiKind`, `f_rc5PoiSrc` — CORE 6400-6404 |

So reproducing the trendline winner FAITHFULLY requires the sweep engine, which
requires the POI registry. Not "to make it compile" — to make it pick the same
line.

### This corrects an earlier call of mine

The previous unit flagged `poiType`, `poiDirection` and `f_rc5PoiKind` as
reachable and I classified them INCONCLUSIVE, attributing them to single-letter
local collisions (`ti`, `ty`, `di`, `on`). **That dismissal was wrong.** The
analyser was reaching them for a real reason. The tool's comment now records
the actual path rather than the excuse.

### What this costs

| option | recovery | CORE | hard headroom | verdict |
| --- | --- | --- | --- | --- |
| move R1+R2 **and** R3 (original plan) | 2,200 | 97,171 | 3,085 | **not available** — R3 drags the POI registry into VIEW |
| move R1+R2 only (structure overlay) | 1,036 | 98,335 | **1,921** | available, but **below the 3,000 target** |
| move R3 only | 1,164 | 98,207 | 1,984 | same objection as the first row |

The structure overlay itself is clean: it draws HH/HL/LH/LL and BOS/CHOCH from
`p3Swings` / `p3Events`, and `rc5SwingRole` is written only from those. Moving
it is sound. It just is not enough on its own.

### Options for the author — none taken here

1. **Move R1+R2 only and accept 1,921 hard headroom.** Honest, safe, and below
   the stated target. P2+P3 would proceed on a thinner budget than the plan
   wanted, and P4 almost certainly would not fit.
2. **Re-examine the `tlHit` tiebreak.** If the trendline winner does not truly
   need "was this line already swept", R3 becomes structural and the full 2,200
   is available. That is a DOCTRINE question about the one-trendline rule, not a
   refactor, and it is the author's to answer.
3. **Give VIEW the sweep engine and the POI registry.** Rejected on its face:
   VIEW stops being a minimum structural subset and becomes a second scanner,
   which the plan forbids and the Heavy Script warning makes reckless.
4. **Find capacity elsewhere.** The POI renderer (4,131) is explicitly staying
   in CORE by author decision, so this would mean new ground.

VIEW was NOT generated, NOT compiled and NOT measured, because doing so would
have meant choosing one of these on the author's behalf.

## Stage VIEW — structure-only extraction, generated and measured

Author decision: keep `tlHit` (it is reaction evidence, not display
convenience), move R1+R2 only, leave the trendline renderer in CORE.

### Architecture

Three artifacts from one canonical source, `tools/rc5_compose.py`:

| artifact | contents |
| --- | --- |
| **CORE** | scanner semantics, POI drawing, trendline drawing |
| **VIEW** | HH/HL/LH/LL + BOS/CHOCH drawing, and the structural subset it needs |
| **PANEL** | screen-space diagnostics |

The structure overlay was **moved out of CORE entirely** into
`tradingview/rc5_view_presentation.pine`, so exactly one copy exists in the
repository and CORE physically cannot draw it. VIEW is CORE minus four
marker-delimited regions, with that renderer spliced back at
`//#VIEW-RENDER-ANCHOR`.

Markers, never line numbers:
`NON_STRUCTURAL_ENGINES`, `MAIN_DISPLACEMENT`, `MAIN_NON_STRUCTURAL`,
`EVERYTHING_BELOW_STRUCTURE`. Marker comments cost 0 Pine tokens.

### The compiler settled the dependency question

**VIEW compiles: `success: true`.** It contains no POI registry, no POI
detector, no sweep engine, no authority, no P5, no P8, no BTMM — and the Pine
compiler accepted it. That is the definitive closure proof the scope-blind
analyser could not give.

It also resolves the earlier inconclusive symbols honestly: `poiType`,
`poiDirection` and `f_rc5PoiKind` were reachable **only through the trendline
renderer**, which stayed in CORE. They were never structure-overlay
dependencies.

| | |
| --- | --- |
| VIEW lines | 1,354 (CORE 6,989) |
| VIEW bytes | 75,996 (CORE ~378,000) |

### Real generated CORE — three points

| N | `ctx.outputILLength` | `C - 97N` |
| --- | --- | --- |
| 22 | 100,469 | **98,335** |
| 24 | 100,663 | **98,335** |
| 26 | 100,857 | **98,335** |

Both intervals exactly `97 x 2 = 194`; all three derive the same base.

| | |
| --- | --- |
| P1 CORE | 99,371 |
| **generated CORE** | **98,335** |
| **saving** | **1,036** |
| **hard headroom** | **1,921** |
| strict headroom (vs 99,256) | **921** |

The real generated artifact matched the deletion probe to the token.

### VIEW token count — NOT measured, and why

The oracle only reports a count inside `CE10117`, which fires only ABOVE the
limit. VIEW plus the maximum permitted padding (N=100, +9,700) is nowhere near
100,256, so the ceiling cannot be reached within `N <= 100`. What is proven is a
bound and a compile: **VIEW <= 90,556 and it compiles**. Measuring it exactly
needs a larger pad block with its own 3-point calibration; that is a small piece
of work, not done here rather than guessed.

### Hashes

| file | sha256 (first 16) |
| --- | --- |
| CORE | `b620971542ab86f4` |
| VIEW | (regenerated after the renderer move — see repo) |
| PANEL | (regenerated) |

### Not done in this unit

Runtime gates (VIEW alone, CORE alone, CORE+VIEW, CORE+VIEW+PANEL), extraction
visual parity, and P2+P3. VIEW is therefore **not yet accepted** — it has passed
the compile, capacity and anti-drift gates, and not the runtime or visual ones.

## VIEW exact token count — 10,792, and a new pad family to get it

The standard 97-token pad cannot measure VIEW: `CE10117` only reports a count
ABOVE the limit, and VIEW is so far below it that enough padding trips a
STRUCTURAL limit first. Two of them, in order:

| attempt | pad shape | result |
| --- | --- | --- |
| 950 blocks of `if barstate.islast` + 1 `log.info` | many top-level blocks | **CE10295** "The main body of the script is too long. Try wrapping code in functions" |
| 50 blocks x 20 `log.info` | fewer blocks, same statements | **CE10295** again — the limit counts statements inside top-level `if`s too |
| 1 function of 900 `log.info` | one huge function | **CE10296** — function body limit |
| **F functions x 100 `log.info`, called once each** | spread across functions | **works** |

The last shape clears both limits: the main body gains F calls, and no function
body approaches its own ceiling.

### Calibration and result

| F (x100 `log.info`) | `ctx.outputILLength` | `C - 7,610F` |
| --- | --- | --- |
| 50 | 391,292 | **10,792** |
| 60 | 467,392 | **10,792** |
| 70 | 543,492 | **10,792** |

`467,392 - 391,292 = 76,100 = 7,610 x 10` — exact.
`543,492 - 467,392 = 76,100 = 7,610 x 10` — exact.

The pad family costs **7,610 tokens per 100-statement function**, calibrated
from the failing points themselves rather than assumed, and all three derive the
same base.

| | |
| --- | --- |
| **RC5 VIEW** | **10,792 tokens** |
| hard limit | 100,256 |
| **hard headroom** | **89,464** |
| utilisation | **10.76%** |

VIEW is 11% of CORE's 98,335. That is the quantitative answer to "is VIEW a
minimum structural subset or a second scanner": it is a subset.

## Runtime gates — BLOCKED, environmentally

Not run, and not faked. The Chrome window this session drives is not visible:

| check | value |
| --- | --- |
| `document.hidden` | **true** (also true in a tab opened with `foreground: true`) |
| canvases | all `300x150` — the unlaid-out default |
| chart legend rows | **0** — the widget never laid out |

The account guard passed (`bellcare1994`) and the facade POSTs worked
throughout, because those are network calls and do not need a rendered page.
But every visual and runtime signal the gates ask for — Heavy Script warning,
object limits, responsiveness, "HH/HL/LH/LL appear", "no POI boxes in VIEW" —
requires a laid-out chart. With a hidden window those readings would be stale
pixels and an empty DOM, which the port plan explicitly forbids treating as
evidence.

Deploying VIEW as its own script is blocked by the same thing: creating a new
script needs the Pine Editor UI, and the editor cannot lay out in a hidden
window.

**To unblock:** the Chrome window needs to be visible on screen (restored, not
minimised, and on the active desktop). Nothing in the repo or the artifacts
needs to change.

### Gate status

| gate | status |
| --- | --- |
| 1. VIEW alone | **BLOCKED** — window hidden |
| 2. CORE alone | **BLOCKED** |
| 3. CORE + VIEW | **BLOCKED** |
| 4. CORE + VIEW + PANEL | **BLOCKED**, and flagged: the Basic plan caps 2 indicators per chart, so this gate may be impossible on this account regardless of visibility |

VIEW therefore remains **NOT ACCEPTED**: it has passed compile, dependency,
capacity and anti-drift; runtime and visual parity are untested.

## Runtime gates — still BLOCKED (re-checked), and the revised matrix

Re-checked at `2f41f06` with all three artifact hashes verified MATCH:

| guard | value |
| --- | --- |
| account | `bellcare1994` — pass |
| `document.hidden` | **true** |
| laid-out canvases | **0 of 7** (all `300x150`) |
| chart legend rows | **0** |

The UI guard fails, so runtime and visual evidence stay unavailable. Nothing in
the repo needs to change; the Chrome window needs to be visible on screen.

Revised matrix, per the author's architecture change — **CORE + VIEW is the
production pair, PANEL is optional diagnostics**:

| gate | status |
| --- | --- |
| G1 VIEW alone | blocked |
| G2 CORE alone | blocked |
| G3 **CORE + VIEW** (production) | blocked |
| G4 CORE + PANEL (diagnostics) | blocked |
| G5 VIEW + PANEL (optional) | blocked |

`CORE + VIEW + PANEL` is no longer an acceptance requirement, which removes the
2-indicator plan cap as a blocker for acceptance.

## P2 bootstrap — Pine already has every ingredient

Done while the UI was unavailable, because it is the piece of P2 that looked
most expensive.

**Python, frozen at `28d432e`** (`leg_origin._direction_timeline`): walk the
relationships sorted by `(availability_time_utc, current_swing.pivot_bar_index,
str(record_id))`, keeping the latest HIGH label and latest LOW label; the first
prefix where `HH and HL` holds emits BULLISH at THAT relationship's
availability, `LH and LL` emits BEARISH, then stop. Transitions follow.

**Pine already carries all three parts:**

| Python part | Pine equivalent | status |
| --- | --- | --- |
| the relationship sort | `f_p2OrderRelationships` | present, and documented as reproducing Python's key exactly — including why the `record_id` leg is unreachable |
| high/low side of a label | `f_p2RelIsHigh` | present |
| the relationship list | `p2Rels` | present |
| transition history | `p3Events` (`transitionCode` + `availabilityTime`) | present |

`f_p2StructureWalk` even computes the bootstrap instant internally — the two
`lastChange := r.availabilityTime` assignments are its two bootstrap branches —
but it is exposed only as `lastChange`, which later transitions overwrite. So
the bootstrap moment is computed and then lost.

**Consequence for P2:** no new structure engine, no new detector, and no change
to the walk's return tuple (which the 127-slot cap makes risky). A small loop
over `p2Rels` in the existing order reproduces the bootstrap pair, and
`f_directionAtTime(t)` is then: last `p3Events` entry with
`availabilityTime <= t`, else the bootstrap if its time `<= t`, else
UNDETERMINED.

That is a far cheaper port than the earlier "Pine has no timeline" reading
suggested, which matters against 1,921 hard headroom. Not implemented here:
P2+P3 remain gated behind runtime acceptance.
