# BTRC-V1 P8 — Alerts (Informational Scanner-State Notifications): CLOSURE

Status: **P8 ALERTS V1 — CLOSED**
Branch: `pine-p4-btmm`
Closed: 2026-09-06

---

## 1. What P8 is

P8 adds five informational alert events on top of the closed P1-P7 engine.
It recomputes **nothing**: every event is a pure edge-detection over
already-computed P5/P7 locals (`btmmValid`, `permission`, `isTerminal`,
`finalScore`, `lifecycle`) inside the existing active-POI loop. P8 carries
no execution capability whatsoever — no entry price, stop loss, take
profit, position size, risk percentage, `strategy.*` call, broker order,
or webhook. An alert payload can never be mistaken for a trade instruction.

Source: `tradingview/btmm_poi_btrc_scanner_p8_dev.pine` (6196 lines,
`sha256 80b330c6…`), built as `tradingview/btmm_poi_btrc_scanner_p7_dev.pine`
(the closed P7 ancestor) plus one title change and one additive block —
Section 6 gives the mechanical proof.

Readiness audit: `docs/architecture/BTRC_V1_P8_ALERT_READINESS.md` (GO
verdict; `P3_CONTEXT_REQUIRED_FOR_P8_V1 = FALSE`,
`P4_REVIEWED_EVIDENCE_REQUIRED_FOR_P8_V1 = FALSE` — neither reopened).

## 2. The V1 alert set, unchanged from the readiness audit

| ID | Event | Trigger |
|---|---|---|
| A1 | `POI_ACTIVATED` | POI's `poi_idx` (raw P3 registry index) seen for the first time ever |
| A2 | `BTMM_VALIDATED` | `btmmValid` transitions false → true |
| A3 | `PERMISSION_ENTERED_ACTIONABLE` | `permission` transitions from a non-actionable code into `{BUY_BIAS, SELL_BIAS}` |
| A4 | `PERMISSION_LOST_ACTIONABLE` | `permission` transitions out of `{BUY_BIAS, SELL_BIAS}` |
| A5 | `POI_TERMINAL` | `isTerminal` transitions false → true (once per POI, ever) |

A direct `BUY_BIAS ↔ SELL_BIAS` flip fires **neither** A3 nor A4 (both
endpoints are actionable) — a deliberate, tested V1 policy choice; there is
no "direction changed" event in V1.

## 3. Priming, dedup, and ordering — as implemented

**Priming.** `var bool p8Primed = false` starts false on every script
(re)start — fresh attach, page reload, remove/re-add, or a host-timeframe
switch, each of which reinitializes every `var` in the script identically
(the same Pine-platform property already exploited by `p8Known` /
`p8PrevBtmmValid` / `p8PrevPermission` / `p8TerminalAlerted`, all `var
array<...>`). On the first confirmed bar after any restart, every eligible
POI's state is seeded into those four arrays and `p8Primed` is set true
immediately after the active-POI loop — no `alert()` call and no
`P8EVENT` log line is ever reachable before that flip. A priming bar with
**zero** eligible POIs (the P1 warm-up boundary can coincide with an empty
active set) is a valid, silent priming pass, not a defect — see Section 7.

**Dedup key.** `(event_type, poi_idx, bar_ms)` — deliberately not
`(event_type, poi_idx)` alone, since the same event type legitimately
recurs for a POI at a later, distinct bar.

**Ordering.** Composite `(poi_idx, fixed lifecycle-priority)` per bar —
`poi_idx` primary (matching Pine's own loop order), event-type priority
only a same-POI tiebreak. This is a direct, line-by-line port of
`AlertEngine.process`'s own composite sort key (`p8_alert_oracle.py`).

**Resource decision.** `alert()` (dynamic per-POI messages,
`alert.freq_once_per_bar_close`) chosen over `alertcondition()` — zero new
plots, zero new `request.security` calls. A separate, decoupled
`p8DebugLog` input (added this closure phase; see Section 5) gates a
canonical `P8EVENT`/`P8PRIME` log stream independent of the `p8Enable*`
toggles, so a Python parity replay always sees the full, untoggled event
stream regardless of which alerts a user has enabled.

## 4. Python event oracle — hard pass

`tests/parity_support/p8_alert_oracle.py` (`AlertEngine`, `PoiSnapshot`,
`BarSnapshot`, `AlertEvent`) is the authoritative reference implementation
Pine's block is a direct port of. `tests/unit/test_p8_alert_oracle.py` (64
tests) covers: all 5 event types and their negatives, priming/`reprime()`
(reload/host-switch), dedup (identical and out-of-order bars), ordering
(same-bar/same-POI and cross-POI), mutation guards, a 15-seed × 60-bar
randomized prefix test against an independently-derived reference, a
determinism check, and a replay of a real 936-event FXCM capture (zero
duplicates, zero missing terminals, fully deterministic). Two design/test
bugs were caught and fixed before either could reach Pine: an event-type-
only sort key that would have grouped events by type across POIs instead of
per-POI (composite-key fix), and a randomized-test fixture that could
recycle a POI index the real append-only registry never would (fixed via a
monotonic `fresh_index()`).

`tests/parity_support/p8_capture_log.py` (`parse_p8_capture`, 5 directed
tests + a synthetic oracle-replay round-trip) and
`tests/parity_support/p8_digest.py` (dual-hash `(H1, H2)` over a canonical,
fixed-order event record) complete the parity toolchain, reusing the same
`p2_digest.py` primitives and round-trip method the P5/P6 phases already
established.

## 5. Pine port — mechanically proven additive-only

`tests/unit/test_p8_semantic_equivalence.py` (9 tests) diffs
`btmm_poi_btrc_scanner_p8_dev.pine` against the closed
`btmm_poi_btrc_scanner_p7_dev.pine` line-by-line and asserts: every removed
line is the indicator title (P7 DEV → P8 DEV) and nothing else changes on
that line; every added `:=` reassignment targets a `p8`-prefixed variable;
plot-family count (63) and `request.security` count (6) are unchanged;
exactly 5 `alert()` calls exist and zero `alertcondition(`; no forbidden
execution term (`entry`, `stopLoss`, `takeProfit`, `positionSize`,
`strategy.*`, ...) appears in any added **code** line (comment lines are
excluded — the project's own disclosure prose legitimately names these
terms in English); and the P8 alert block calls none of the 18 closed P5
decision functions.

**This closure phase's one source change**: a `p8DebugLog` input
(`input.bool(false, ...)`, own `grpP8` group) was added and the existing
`P8PRIME`/`P8EVENT` log block's gate was switched from the shared
`debugMode` to this new, decoupled toggle — so a real capture is not
drowned out by the much higher-volume `P5EVAL`/`P7DIAG` per-POI-per-bar
log lines (discovered live: at `debugMode`-shared gating, TradingView's
10,000-line download cap was reached by `P5EVAL` volume alone before any
`P8EVENT` line, twice, across two capture attempts). This is the only line
touched inside the P8 block itself; `test_p8_semantic_equivalence.py`
re-passed (9/9) after the change, confirming it stays purely additive and
within the `p8`-prefixed namespace.

## 6. Live TradingView validation (real FXCM, account bellcare1994, chart `6cu1b2O7`)

- **Compile**: 0 errors, 0 warnings beyond the previously-classified
  non-reproducible "heavy script" advisory (established GO precedent from
  P6). Confirmed via Object Tree (clean `(20, 300, ...)` param summary, no
  error badge) immediately after every attach in this session.
- **Host-timeframe switch**: M15 → M5 → M15, each transition re-verified
  clean (Error-only log filter: "No criteria matches" on M5 and on M15
  after switching back). **H1 was intentionally not tested** — a real,
  pre-existing, unrelated P5 defect (`RE10041` on an H1 host, documented in
  memory as `p5-h1-host-timeframe-runtime-error`) predates P8 and is out of
  this closure's scope; P8 adds no H1-specific code path.
- **Page reload**: full browser reload; both `[P6 DEV]` and `[P8 DEV]`
  reattached automatically from the saved chart layout with correct
  default parameters and no error badge.
- **Remove / re-add**: exercised three times this session (via the Object
  Tree row's explicit **Remove** context-menu action — never the ambiguous
  trash icon, see the incident note below), each producing a genuinely
  fresh script instance (confirmed via the Indicators picker / Object Tree
  never retaining prior custom settings across a re-add, which is itself
  the direct evidence that `var` state, including `p8Primed`, truly resets
  on re-add and is not silently carried over).
- **Incident, disclosed**: mid-session, the Object Tree row's trash icon
  (as distinct from the right-click menu's **Remove** item) turned out to
  **delete the saved script**, not merely detach it from the chart — a
  real mistake, caught immediately via a full page reload showing the
  script absent from both the chart and "My scripts". No work was lost:
  the authoritative source lives in this repository, and the script was
  recreated from it (`Save script` under the exact original name,
  auto-suggested from the source's own `indicator()` title) and
  re-attached. This is now a known pitfall for future sessions: use the
  context menu's **Remove**, never the legend row's trash icon, to detach
  an indicator from the chart.

## 7. Real event parity — Pine vs. Python, on real FXCM data

Two real captures (TradingView Pine Logs → Download logs) were used
together, since the noise-isolated (`p8DebugLog`-only) capture needed to
fit under TradingView's 10,000-line download cap never contains `P5EVAL`,
and the plain (`debugMode`-shared) capture that does contain both tags is
itself capped to the same ceiling — the combination neither capture alone
can supply:

- `p8_dev_raw_log.csv` — a plain capture carrying both `P5EVAL` (per-bar
  scanner state) and `P8EVENT` (Pine's own derived alerts) for the same
  103-bar / ~26-hour real FXCM window (2026-09-03T19:00 – 2026-09-04T21:30).
- `p8_dev_clean_capture.csv` — an earlier, wider `p8DebugLog`-only capture
  reaching back to 2026-08-18, used **only** to establish which POIs, BTMM
  states, and actionable-permission states were already true before the
  first capture's window began (a fact the 103-bar window cannot itself
  supply, since it starts mid-stream against Pine's true, weeks-old
  `p8Known`/`p8PrevBtmmValid`/`p8PrevPermission` caches).

`tests/unit/test_p8_real_pine_parity.py` replays `p8_dev_raw_log.csv`'s
`P5EVAL` rows through a fresh `AlertEngine`, seeding its first-bar `prime()`
call with the prior-knowledge facts mined from `p8_dev_clean_capture.csv`
(POIs already known, already BTMM-valid, or already actionable before the
window), then compares the resulting Python event stream against Pine's
own real `P8EVENT` lines from the same 103-bar window (excluding the
window's first bar, whose own boundary transitions are unverifiable from a
capture that starts mid-stream).

**Result: exact match.**

- **456 / 456 events**, identical `(event_type, poi_idx, bar_ms)` triples,
  in identical order, on both sides.
- **Digest match**: `capture_digest` (dual-hash `(H1, H2)`) —
  `H1=294719549, H2=35571918` on both the Python replay and the real Pine
  capture.
- Before the prior-knowledge seeding was added, the naive replay showed 58
  spurious extra Python-side `POI_ACTIVATED`/`BTMM_VALIDATED` events (all
  at the window's second bar) — traced to POIs that were already known to
  Pine from weeks earlier but absent from the window's own first-bar
  snapshot. This was a real, root-caused artifact of the truncated capture
  window, not a defect in either the Pine port or the Python oracle: once
  the missing prior-knowledge facts were supplied from the wider capture,
  the mismatch resolved to zero.

**Dedicated priming-log observation.** A dedicated live test (temporarily
lowering `calc_bars_count` to 1250 and flipping `p8DebugLog`'s default to
`true`, purely as local, uncommitted, reverted-after-use source edits — see
Section 5's contract on `calc_bars_count=1800` being locked to match P7)
produced zero `P8PRIME` lines: the 1250-bar window's first bar coincided
exactly with the P1 warm-up boundary (`C_P1_MIN_CALC_BARS`), where zero
POIs were yet active. This is architecturally correct (Section 3) and not
evidence of a defect — the priming *logic* is proven correct by the Python
oracle's own dedicated priming/`reprime()` test suite and by this Pine
source being a direct, line-by-line port of that logic — but it means this
closure does **not** additionally claim to have observed a non-empty
`P8PRIME` log burst live. The temporary source edits (`calc_bars_count`,
`p8DebugLog` default) were fully reverted before this closure; the
committed source is byte-identical to the pre-edit version
(`sha256 80b330c6…`, confirmed).

## 8. Resource budget — confirmed unchanged vs. P7

| Metric | P7 | P8 | Delta |
|---|---|---|---|
| `plot`/`plotshape`/`plotchar` | 63 | 63 | 0 |
| `request.security` | 6 | 6 | 0 |
| `alertcondition(` | 0 | 0 | 0 |
| `alert(` | 0 | 5 | +5 (the V1 set) |

## 9. Regression — P1-P7 unaffected

Full repository suite: **3495 passed, 0 failed** (real-data-gated tests
included, since both real capture files are present locally; both are
gitignored under `artifacts/`). `ruff check` and `mypy
--explicit-package-bases` are clean on every new/changed P8 file
(`btmm_poi_btrc_scanner_p8_dev.pine`'s Python-side companions
`p8_alert_oracle.py`, `p8_capture_log.py`, `p8_digest.py`,
`p8_real_state_log.py`, and all `test_p8_*.py` files). A pre-existing,
project-wide `mypy src tests` module-identity ambiguity (`tests` has no
`__init__.py`) predates this session (reproduces on files as old as
`p3_pine_model.py`) and is out of this closure's scope.

## 10. Deferred (explicitly, per the standing brief)

- **P3 Context** and **P4 Reviewed-Evidence Transport** remain deferred —
  the readiness audit's verdict that neither is required for the P8 V1
  alert set stands, unchanged and unchallenged by this implementation
  phase.
- **H1 host-timeframe live test** — deferred to whenever the pre-existing,
  unrelated P5 H1 runtime defect (`RE10041`) is separately fixed; P8 adds
  no H1-specific logic and is not the owner of that defect.
- **A live TradingView Alert object** (the "Add Alert" dialog, an actual
  scheduled alert firing to the Alerts panel) was **not** created this
  session — validation relied on the `p8DebugLog` proxy stream, which logs
  exactly what every `alert()` call in the same bar would have fired,
  gated by the identical `p8Primed`/transition conditions. Creating a real
  Alert object and observing a live firing is a lower-risk, purely
  additive follow-up that does not require reopening any P8 code.
- **A live-observed, non-empty `P8PRIME` log burst** was not captured this
  session (Section 7) — the priming logic itself is proven correct by
  code-identity with the oracle and by the real-parity replay's own
  correctness (which depends on priming/re-init actually working, since
  three real remove/re-add cycles this session each produced a
  demonstrably fresh, empty `p8Known` state).

## 11. Safety — unchanged, reaffirmed

No P1-P7 semantic (trend/structure/POI/BTMM/BTRC/MTF) is recomputed
anywhere in P8. No entry price, stop loss, take profit, position size, risk
percentage, `strategy.entry`/`strategy.exit`/`strategy.order`, broker
order, or webhook execution exists in any alert payload or anywhere in the
added code (Section 5, `test_p8_semantic_equivalence.py`'s forbidden-term
guard). No push, no merge to `main`, no publish, no live trading, and no
broker integration occurred this session.

## 12. Closure

P8 Alerts V1 is closed: contract frozen, Python oracle hard-passed, Pine
port mechanically proven additive-only, live-deployed with 0 compile
errors across three attach cycles and two host-timeframe switches, and
real Pine-vs-Python event parity achieved exactly (456/456 events, digest
match) on genuine FXCM data. Per the standing instruction, **P9 is not
auto-started** following this closure.
