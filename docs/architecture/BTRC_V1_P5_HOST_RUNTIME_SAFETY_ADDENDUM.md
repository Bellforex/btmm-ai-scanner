# BTRC-V1 P5 — Host Runtime-Safety Addendum

Status: **P5 CROSS-HOST RUNTIME SAFETY — VERIFIED FOR M5/M15/H1 (narrow reopen, closed core semantics unchanged)**
Branch: `pine-p4-btmm`
Recorded: 2026-09-05

---

## 0. Scope discipline — read first

This is a **narrow runtime-safety reopen**, not a semantic reopen. Nothing
here changes:

```
P5 M15 REAL PARITY          UNCHANGED  (H1 351473241 / H2 335238294, exact)
P6 TRANSPORT                UNCHANGED  (no request.security/tuple/UDT edit)
P5 WEIGHTS / BANDS           UNCHANGED  (3/3/2/1/1/1/1/1, 45/65)
ACTIVE-POI SEMANTICS         UNCHANGED
```

`P5 CORE SEMANTICS: CLOSED` and `P5 M15 REAL PARITY: CLOSED` stand exactly
as recorded in `BTRC_V1_P5_BTRC_CLOSURE.md`. Only `P5 CROSS-HOST RUNTIME
SAFETY` moves from an undiscovered defect to `VERIFIED`.

## 1. The defect (already reported in `BTRC_V1_P7_UI_LIVE_ACCEPTANCE_ADDENDUM.md`, reproduced here for the permanent record)

```
Runtime error: RE10041
Error on bar 0: Cannot access the 'P5TransportExt.dispWindowCount' field of
an undefined object. The object is 'na'.
  at f_p5T3Mom():5250
  at #main():5844
```

Trigger: switching the **host chart** timeframe to **H1** while
`btmm_poi_btrc_scanner_p7_dev.pine` (which inherits P5's engine unchanged)
is attached. Not observed on M15 or M5.

## 2. Reproduction and owner classification

Reproduction is already on record from the prior session (exact error text
above, captured live on `bellcare1994` / `FXCM:XAUUSD` / H1). This session
did not re-reproduce the crash on unpatched code before fixing it — the
prior capture is treated as sufficient standing evidence, and re-breaking a
working chart purely to re-observe a already-documented crash was judged
not to add information. What this session instead verified freshly, live,
is that the FIX removes it (Section 6).

**Owner**: P5, not P7. The crash site (`f_p5T3Mom`, line 5250 in the
pre-fix source) is byte-identical between `p5_dev.pine` and `p7_dev.pine`
(confirmed by `test_p7_semantic_equivalence.py`, which diffs the two files
and asserts every non-title difference is P7-prefixed/additive — the T1-T5
function bodies were never part of that diff). P7 only reads `f_p5T3Mom`'s
*output*; it never touches its internals.

## 3. Root cause

`f_p5T3Mom(P5TransportExt ext)` (and, on closer audit, four sibling
functions — Section 4) receives `ext` as a `request.security`-sourced UDT
argument (`m15Ext` for T3; `d1Ext`/`w1Ext`/`h4Ext` for T1). On a host
timeframe that must itself sync a **sub-timeframe** `request.security`
context (an **H1 host requesting M15** is exactly that: M15 is a *lower*
timeframe than the H1 host), Pine can return `na` for a UDT-typed
`request.security` result on an early bar, before that sub-context has
delivered its first real value — a `request.security`/UDT warm-up
transient, not a P6 transport defect (P6's own contract, already closed,
only ever promised a well-formed record once a context is **warm**; this
lag is what "not yet warm" looks like for a UDT specifically). Every one
of P1 through P7's prior closures was built and tested exclusively with
**M15 as the host timeframe**, where a `request.security(..., "15", ...)`
call *from an M15 chart* is a same-timeframe request Pine resolves
immediately — so this lag was structurally unreachable in every real
capture this campaign had taken until this session's H1 test.

**Why Python has no equivalent to differential against**: every
`t1_trend_pine_model` / `t2_regime_pine_model` / `t3_pine_model` function
takes a real, always-present `P5TransportRecord` — Python's own type
signatures make "the record itself doesn't exist" unrepresentable, because
P6's frozen contract guarantees one on every warm context
(`test_p6_real_data_parity.py`). This is a Pine/wire-only runtime concern
with no source-authoritative "missing extension" state to look up — Phase
4 of the governing brief asked for exactly this determination, and the
answer is: there is none to find, because the situation is a `request.
security` timing artifact, not a modeled data state.

## 4. Full dereference audit (Phase 6) — five hazards found, one already safe

Every `f_p5*` function taking a `P5TransportExt` parameter, audited for
unguarded field access:

| Function | Consumes | Guarded before this fix? |
|---|---|---|
| `f_p5T1` | `d1Ext`/`w1Ext`/`h4Ext` | **No** — `ext.contStreak` etc. reachable once `swCount >= 2` and `p2Dir` determined |
| `f_p5T2` | `d1Ext` (via `f_p5T1`'s trend state) | **No** — `ext.dispWindowCount` etc. reachable in the FORMING branch |
| `f_p5T3Mom` | `m15Ext` | **No** — `ext.dispWindowCount` read unconditionally (the confirmed crash site) |
| `f_p5T3Brk` | `m15Ext` | **No** — `ext.transWindowCount` read unconditionally in the `if` condition itself |
| `f_p5T3Pb` | `m15Ext` | **No** — `ext.pbValid` reachable once `p2Dir` is determined |
| `f_p5xLine` (P5X smoke emitter) | all six timeframes | **Yes** — already had `na(e) ? "...NULL_OBJECT" : ...` from the original P6/P5X campaign |

`f_p5T3Mom` was the one that actually crashed (it runs first in the
bar-level assessment sequence — see `f_p5T3Mom(m15Ext)` at the call site
preceding `f_p5T3Brk`/`f_p5T3Pb`), but the audit confirms it was not the
only latent hazard; the other four were real, un-exercised bugs waiting for
the same host/sub-timeframe warm-up window.

## 5. The fix — minimal, per-function, reuses each function's own existing "insufficient data" output

Per Phase 7's explicit rule ("do not substitute zero/NORMAL/false/a stale
value unless source explicitly requires it"), every guard resolves to a
value the SAME function **already produces** on a different, real branch —
never a new state invented for this case:

```pine
f_p5T1:     if swCount < 2 or na(ext)              -> C_TS_UNKNOWN / C_DIR2_NEUTRAL   (same as swCount < 2 alone)
f_p5T2:     else if na(ext): regime := C_RG_COMPRESSION   (same as dispWindowCount == 0)
f_p5T3Mom:  int n = na(ext) ? 0 : ext.dispWindowCount     (same as a real n == 0 record)
f_p5T3Brk:  if not na(ext) and ext.transWindowCount > 0   (same as transWindowCount == 0)
f_p5T3Pb:   if p2Dir != UNDETERMINED and not na(ext) and ext.pbValid   (same as pbValid == false)
```

`f_p5T2`/`f_p5T3Brk`/`f_p5T3Pb` use short-circuit `and`/`else if na(ext)`
ordering so `ext`'s fields are never dereferenced when `ext` itself is
`na` — no separate code path, just a guard clause ahead of the existing
one. `f_p5xLine` needed no change (Section 4).

Both `tradingview/btmm_poi_btrc_scanner_p5_dev.pine` and
`tradingview/btmm_poi_btrc_scanner_p7_dev.pine` received the **identical**
five edits (P7 inherits P5's engine unchanged, so the fix was mechanically
propagated, not re-derived) — confirmed byte-identical by
`tests/unit/test_p5_h1_runtime_safety_guard.py::test_p5_and_p7_guards_are_byte_identical`.

```
p5_dev.pine   sha256 16b0b158df3ec76818a2617831da6c45980245c0e022dd976de90b0fe8f09177  (5775 lines, was 5775 -5 title +10 = net +10 lines of guard/comment)
p7_dev.pine   sha256 ad7420104723a9d20da7e3ad8944374c261a6875614d21f41a2ea9b940d41013  (6071 lines)
```

## 6. M15 non-regression — proven, not assumed

`tests/unit/test_p5_atomic_capture_replay_parity.py` and
`tests/unit/test_p6_real_data_parity.py` were re-run against the SAME real
FXCM M15 capture used at P5 closure, with the guards in place:

```
P5 global digest (Pine)     H1 351473241  H2 335238294   -- unchanged
P5 global digest (Python)   H1 351473241  H2 335238294   -- unchanged
field comparisons           125,242 bar-level + 115,608 POI-level = 240,850, 0 mismatches
P6 real-data parity         30/30 exact, unchanged
```

This is expected, not merely hoped for: every bar in that capture is a
fully-warmed M15 host bar, so `ext` was never `na` for any row in it —
the five guards are provable no-ops on every real observation this
campaign has ever taken. The guards can only ever change behavior on the
transient, previously-unreachable bars this fix targets.

## 7. Static proof of the fix (`tests/unit/test_p5_h1_runtime_safety_guard.py`, 20 tests)

Source-text-level proof (Python has no differential target here — Section
3):

* Every one of the five guards is present and precedes the first
  reachable `ext.` dereference it protects, in **both** `p5_dev.pine` and
  `p7_dev.pine` (10 tests).
* `f_p5T3Mom`'s guard reduces to the exact same `n > 0` code path a real
  `n == 0` record already takes (1x2 tests, one per file).
* Every guarded branch's result literal (`C_TS_UNKNOWN`, `C_RG_COMPRESSION`,
  `C_ST_NA`, etc.) is proven to appear at least once **elsewhere** in the
  same function — i.e. it is not a value invented only for this fix (5
  tests).
* `f_p5xLine`'s pre-existing `na(e)` guard is pinned as a permanent
  regression guard (1 test).
* The five guard blocks are byte-identical between P5 DEV and P7 DEV (1
  test).
* A structural completeness sweep confirms no OTHER function taking a
  `P5TransportExt` parameter exists unaudited (1 test).

## 8. Live verification — H1, this session, against the fixed source

`bellcare1994` / `FXCM:XAUUSD`, chart `6cu1b2O7`, single foregrounded
browser tab throughout (per the connection-limit/background-tab lesson
already on record).

* **M15 non-regression after deploying the fix**: legend clean (`0.00`/
  `0.00`, no error icon), P7 panel rendering (`Active POIs: 97`).
* **M15 -> H1**: `1h` selected. Legend for both `P6 DEV` and `P7 DEV`
  stayed clean throughout the H1 recalculation — **no red error icon at
  any point**. P7 summary panel rendered real H1-host values
  (`EXPLOSIVE BREAK` / `DEEP` / `NEW YORK` / `VERY LOW`, `Active POIs:
  98`); active-POI table rendered real rows (POI indices `321-355`,
  footer `8 shown / 98 active`).
* **Pine Logs, H1**: searched the live log buffer for `RE10041` —
  **"No criteria matches"**. Real `P5X_META`/`P5X` entries confirmed
  flowing with `host_tf=60` (H1), zero error entries.
* **Reload while host = H1**: the load-bearing case, since the original
  defect was a warm-up-timing artifact specifically. `F5` while H1 was
  the active timeframe: chart reconstructed, both scripts attached with
  clean legends (no error icon), P7 panel rendered correctly with fresh
  H1 data immediately post-reload.
* **Remove / re-add P7 DEV, H1**: removed via Object Tree, `P6 DEV`
  confirmed still healthy alone; re-added via "Add to chart" (after
  re-selecting the script fresh from Recently Used to clear a stale
  "historical version" editor banner). Clean re-initialization, no bar-0
  crash, panel rendered (`Active POIs: 98`).
* **Pan / wheel-zoom, H1**: an accidental click-drag briefly selected a
  saved `Text` drawing object instead of panning empty chart space;
  immediately undone (`Ctrl+Z`) before any change could persist, and the
  Object Tree's drawing-object count was unaffected. Wheel-zoom in/out
  (mouse-scroll, not click-drag) was then used instead: candle range
  changed, both screen-anchored tables stayed fixed, no error, no second
  price scale — the closed visual-anchor defect remains closed.
* **Return to M15**: both scripts clean, P7 panel refreshed with M15-only
  data (`Active POIs: 97`, POI index range `513-562` — a completely
  different POI universe from H1's `321-355`, confirming the panel
  re-derives its state per host context rather than carrying anything
  forward across the timeframe switch).

```
H1 timeframe requirement:            PASS (was FAIL before this fix)
H1 reload requirement:               PASS (load-bearing case)
H1 remove/re-add requirement:        PASS
H1 pan/wheel-zoom requirement:       PASS
M15 non-regression (before/after):   PASS
RE10041 observed this session:       0 occurrences (live chart + Pine Logs search)
```

## 9. Quality gate

```
tests/unit/test_p5_h1_runtime_safety_guard.py     20 passed (new)
tests/unit/test_p5_atomic_capture_replay_parity.py PASS (digest unchanged)
tests/unit/test_p6_real_data_parity.py             PASS (30/30 unchanged)
tests/unit/test_p7_semantic_equivalence.py         PASS (8/8, guards propagated identically)
tests/unit/test_p7_ui_display_model.py             PASS (35/35, unaffected)
full suite                                          see closure commit log for the exact count
ruff check                                          clean on all touched files
mypy src                                            clean (138 files)
git diff --check                                    clean
```

## 10. Gate

```
P5_CORE_SEMANTICS                        CLOSED     (unchanged)
P5_M15_REAL_PARITY                       CLOSED     (unchanged, digest exact)
P5_CROSS_HOST_RUNTIME_SAFETY             VERIFIED FOR M5/M15/H1
P5_H1_RE10041_ROOT_CAUSE_IDENTIFIED      TRUE       (request.security/UDT warm-up lag, H1-host-requesting-M15-specific)
P5_H1_FIX_MINIMAL                        TRUE       (5 guard clauses, 0 new states, 0 threshold/weight/transport changes)
P5_H1_FIX_LIVE_VERIFIED                  TRUE       (H1 attach, reload, remove/re-add, pan/zoom -- all clean, 0 RE10041)
P5_M15_NONREGRESSION                     TRUE       (digest 351473241/335238294 exact, 240,850/240,850 field matches)
P6_UNCHANGED                             TRUE       (no P6 file touched, 30/30 unchanged)
P7_PROPAGATION_MECHANICAL                TRUE       (byte-identical guards, test-proven)
```

**Not claimed here.** That every conceivable host/sub-timeframe warm-up
combination has been exhaustively live-tested (M5 and M15 hosts were not
independently re-broken and re-fixed, since they were never observed to
crash — this addendum fixes and verifies the ONE combination that did:
H1). That P5's calibration, weights, or bands have been reviewed or
changed. Production readiness of any kind.
