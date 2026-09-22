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
