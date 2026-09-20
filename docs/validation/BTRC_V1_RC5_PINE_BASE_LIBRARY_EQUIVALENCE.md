# BTRC-V1 RC5 — APPROVED PINE BASE: BAH-LIBRARY-BACKED RC4

The RC5 Pine work starts from an RC4-equivalent build whose 24 generic
presentation/utility helpers are imported from a separately compiled public
library instead of being inlined 33 times inside the script.

**This is NOT RC5 semantics.** It is RC4 behaviour with a smaller compiled
footprint, and nothing else.

## The library

`import bellcare1994/bah_pine_ui_helpers/1 as bahui`

Public, open-source, author `bellcare1994`:
<https://www.tradingview.com/script/M2zZQ7xT-BAH-Pine-UI-Helpers/>
Repo source `tradingview/libraries/bah_pine_ui_helpers.pine`,
sha256 `0a5dd947f861d2c655966803b41da40047c54067e6795059238f04dc72e009fb`
(commit `7fb045e`). 24 exports, presentation and textbook algorithms only —
no threshold, score, weight, qualification rule or market decision.

## Why it recovers tokens

Pine **inlines user functions at every call site**, so a small helper with many
call sites is expensive. Imported library bodies are compiled separately and
are effectively free — calling `TradingView/ta/9`'s `supertrend()` from the
real USER build cost **55 tokens** including two `plot()` calls.

The dead end, for the record: converting a 19-branch `switch` to
`array.from` + `array.get` *inside the same script* saved only **102** tokens.

## Measured base

| build | compiled tokens |
|---|---|
| RC4 USER v16, helpers inlined | **99 410** |
| RC4-equivalent, helpers imported | **95 796** |
| recovered | **3 614** |
| **headroom** | **4 460** → CONDITIONAL PASS (4 000–4 999) |

Measured with the CE10117 padded-probe oracle against TradingView's real
compiler (the `save/next` endpoint). `translate_light` is syntax-only and
reports success on source the real compiler rejects — never use it as a gate.

## Equivalence evidence

**Static.** All **23/23** extracted bodies are byte-identical to the originals
after constant inlining. `bandDistance` is the one intentional signature change
(it read the global `close`; the library takes `price`) and is equivalent under
`{close→price, t→top, b→bottom}`; every call site has the shape
`bahui.bandDistance(close, top, bottom)`. 33 call sites rewritten, 0 stray
local definitions.

**Compile.** Real compiler PASS, for each of the eight helper groups
individually (labels, colour, drawing-array clears, table row, nearest-first,
banker's rounding, median, band distance), for a script exercising **all 24
exports by name**, and for the full build.

**Attach.** PASS in the scratch layout `BAH-RC5-LAB`: study loads, **39
inputs** (identical to RC4 USER v16), no compilation or runtime badge.

**Presentation / runtime.** Both builds were attached to the same chart, same
bars, same input values, and captured by alternating visibility:

| | |
|---|---|
| total pixels | 1 269 618 |
| differing pixels | **2 276 (0.1793 %)** |
| diff bounding box | x 176–487, y 10–65 — the legend title only |

Everything outside the legend is **pixel-identical**: POI zones and text, type
names, permission and lifecycle labels, colours, dashboard rows, POI table
rows and ordering, market structure, trendlines, range, liquidity and BTMM
markers. Evidence: `artifacts/rc5_library_equivalence/A_rc4_reference.png`
and `B_bah_backed.png`.

Scope note: this is render-level equivalence, which covers every drawn object
and every POI-table field (score, permission, state, cycle/location). It is not
a log-level P3/P5/P8 record diff — USER emits no capture streams; that remains
available via the PARITY build if a record-level diff is ever required.

## Earlier false alarm

A previous attach attempt showed "Compilation error". Root cause: it reused the
`RC4 TOKEN PROBE` script, whose `kind` had flip-flopped between `library` and
`study` across many overwrites. A clean dedicated script
(`BAH RC5 LAB - library backed RC4`) attaches without error. The library import
was never at fault.

A second hazard found the same day: two Chrome instances are connected with
**different TradingView accounts**, and a tab-group reset can silently hand
back the wrong one. Verify `window.user.username === 'bellcare1994'` before any
state-changing TradingView action.
