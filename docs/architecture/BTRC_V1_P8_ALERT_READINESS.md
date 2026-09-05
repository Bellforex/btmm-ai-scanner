# BTRC-V1 P8 — Alert Readiness + Dependency Audit

Status: **AUDIT ONLY — GO for a V1 alert set built entirely from closed
P1–P7 state. Neither P3 CONTEXT nor P4 REVIEWED-EVIDENCE TRANSPORT is
required. No Pine or Python implementation performed in this audit.**
Branch: `pine-p4-btmm`
Recorded: 2026-09-05

---

## 1. Baseline

```
branch          pine-p4-btmm
HEAD            4eb3a4ee6ee499d0f171a73f5a3a8cd32e20b570
git status      clean
git diff --check clean
tests collected 3415
```

P1–P7 all CLOSED (P3 CORE and P4 CORE closed; P3 CONTEXT and P4
REVIEWED-EVIDENCE TRANSPORT remain the two deliberately-deferred items
this audit evaluates). P5 cross-host safety VERIFIED for M5/M15/H1
(`BTRC_V1_P5_HOST_RUNTIME_SAFETY_ADDENDUM.md`). P7 FULLY CLOSED
(`BTRC_V1_P7_UI_CLOSURE.md`, `BTRC_V1_P7_UI_LIVE_ACCEPTANCE_ADDENDUM.md`,
`BTRC_V1_P7_DURATION_COMPLIANCE_ADDENDUM.md`).

## 2. What already exists — recovered, not invented

No frozen P8 contract exists. The closest prior art:

* **`BTRC_V1_P0_PYTHON_TO_PINE_ARCHITECTURE_MAP.md` §12 "Alerts plan"** (a
  pre-P1 architecture map, never revisited since): a candidate event list —
  `NEW_POI, POI_RETEST, POI_BREACH, POI_RECLAIM, POI_INVALIDATION,
  NEW_BTMM_SETUP, BTMM_LIFECYCLE_CHANGE, TREND_CHANGE, REGIME_CHANGE,
  HIGH_CONFLUENCE_CONTEXT, COUNTER_TREND_WARNING` — explicitly scoped as
  "scanner information only, no automatic broker order execution." Treated
  here as a **strong prior**, not a ratified contract — several of these
  (`POI_RETEST`, `POI_BREACH`, `POI_RECLAIM`) name P3 lifecycle-transition
  concepts that were themselves refined after this doc was written; Section
  5 below re-derives the V1 set from the CURRENT closed state rather than
  importing this list uncritically.
* **`BTRC_V1_P3_POI_LIFECYCLE_ARCHITECTURE.md`**: P3 deliberately reserved
  internal lifecycle-transition codes "for a future P8" but specifies no
  alert format or mechanism.
* No file matches `docs/architecture/*ALERT*` or `*P8*` — this is the first
  dedicated P8 document.
* No existing dedup/cooldown/debounce decision exists anywhere in the repo.
* `test_p7_semantic_equivalence.py::test_no_alertcondition_calls_p8_not_started`
  is a guard-rail confirming P8 hasn't started — not a spec.

## 3. Alertable state inventory — what closed P5/P7 actually computes

Per-POI, recomputed every confirmed bar inside the existing active-POI loop
(`p7_dev.pine:5899-5977`), from arrays already read by P5/P7's confluence
code:

```
permission  (C_PERM_*): BUY_BIAS=0, SELL_BIAS=1, ALLOW_BOTH_CONTEXT=2,
                         COUNTER_TREND=3, WATCH_ONLY=4, NO_TRADE_CONTEXT=5
lifecycle   (C_LC_*):   DETECTED=0, STRUCTURALLY_VALIDATED=1,
                         [BTMM_VALIDATED=2 unreachable, no constant],
                         POI_VALIDATED=3, TREND_VALIDATED=4,
                         REGIME_VALIDATED=5, MOMENTUM_VALIDATED=6,
                         LIQUIDITY_VALIDATED=7
finalScore  int, 0-100
align       (C_AL_*): ALIGNED/PARTIAL/NEUTRAL/COUNTER_TREND
```

Plus the P3 registry fields every eligible POI already carries:
`poiDirection`, `poiTier`, `poiStatus`, `poiTerminal` — and P4's
`btmmSetupByPoi`/`btmmDir` (setup registered + its direction).

Global (bar-level, not per-POI): `p5GlobalDir`, `p5RegimeGlobal`,
`p5MomDir`/`p5MomAccel`, `p5BrkState`, `p5PbState`, `p5SessionCtx`,
`p5VolState`.

**Classification for alert-trigger suitability**:

| State | Class | Why |
|---|---|---|
| `permission` transition | Stable trigger | Coarse (6 values), already the product's headline decision |
| `lifecycle` transition | Stable trigger | Coarse (7 reachable values), monotonic-ish progression |
| POI created / terminal | Stable trigger | Binary, already gates the active-POI loop itself |
| BTMM setup registered | Stable trigger | Binary (`btmmSetupByPoi[i] != -1`) |
| `finalScore` (raw) | Too noisy | Continuous 0-100, moves every bar with T3 momentum's own float64-bounded wobble (see Section 8) |
| `align` transition | Diagnostic-only | Already implied by `permission`'s own branching (Section 5's V1 doesn't need it standalone) |
| Global direction/regime/momentum/session/volatility | Diagnostic-only for V1 | Real, closed, alertable in principle, but not part of the smallest coherent V1 (Section 6) |

## 4. Dependency verdict — the load-bearing finding of this audit

### P3 CONTEXT

`BTRC_V1_P3_POI_LIFECYCLE_ARCHITECTURE.md` AD-6 (§33) defines P3 CONTEXT as
14 `NOT_APPLICABLE_LIFECYCLE_POI_TYPES` (EQH/EQL liquidity + 12
calendar/period highs/lows) — a **disjoint, additional** subset of
`PoiType`, deliberately excluded from the 18-type `P3_CORE_TYPE_SET` the
closed lifecycle engine (and everything P5/P7 read) operates on. Quoting
the closure doc directly: "These are context-only ... and are not consumed
by the CORE contract closed here." Deferring CONTEXT does not remove or
alter any field of any POI already in the registry — it simply means 14
*additional* POI types never get created at all. Every alert this audit
proposes (Section 6) operates on POIs already in the registry, using
fields the registry already carries.

**`P3_CONTEXT_REQUIRED_FOR_P8_V1 = FALSE`**

### P4 REVIEWED-EVIDENCE TRANSPORT

`BTRC_V1_P4_BTMM_CLOSURE.md`: the deferred evidence channel
(`btmmEvHas`/`btmmEv*`) is read by the engine and **written by nothing** —
every setup that would need it cancels with `NO_LIQUIDITY_EVIDENCE` before
ever reaching `C_BTMM_ST_CONFIRMED`. Critically, **P5/P7's own
`f_p5BtmmScoreConfluence` never reads `btmmState`/`C_BTMM_ST_CONFIRMED` at
all** — its `btmmValid` means only "a setup row exists for this POI"
(`btmmSetupByPoi[i] != -1`), which is populated independently of the
deferred evidence channel. So a "BTMM setup registered/validated" alert,
scoped to exactly what the closed confluence engine already means by
"valid," needs nothing from the deferred channel. A hypothetical FUTURE
alert wanting the stricter, human-reviewed `CONFIRMED` state would need it
— but that state is unreachable today regardless of P8, and no V1 alert
proposed here claims to be that state.

**`P4_REVIEWED_EVIDENCE_REQUIRED_FOR_P8_V1 = FALSE`**

**No alert in the V1 set (Section 6) is blocked by either deferred item.
Both remain deferred, untouched, per the governing instruction not to
reopen them merely because they exist.**

## 5. Informational alert vs. trade-entry signal

Every alert in this document is a **state-transition notification about
the scanner's own already-computed output** — never a new decision. None
compute or propose entry price, stop loss, take profit, position size, or
risk percentage; none call `strategy.entry`/`strategy.exit`; none imply a
broker action. Wording must say "permission became BUY_BIAS" / "POI
became active" — descriptive of scanner state, never "buy now."

**Provisional-score disclosure (Phase 8, documentation-only — no source
changed by this note):** P5's weights (3/3/2/1/1/1/1/1), the 45/65
permission bands, and the liquidity-component placeholder remain
**ENGINEERING-PROVISIONAL** per `BTRC_V1_P5_BTRC_CLOSURE.md`; no
calibration or profitability claim exists. Any future alert message
referencing `permission`/`finalScore` must describe them as scanner/BTRC
states ("permission entered the BUY_BIAS state under the current
provisional bands"), never as a proven or recommended trading signal.

## 6. Recommended V1 alert set

Five alerts, chosen because each maps to exactly one field already
computed by the closed engine, each is a genuine state TRANSITION (not a
level), and together they cover "a new opportunity appeared," "it
strengthened," "it's now actionable," "it weakened," and "it's gone" —
without duplicating internal diagnostic noise (global direction/regime/
session/volatility deliberately excluded from V1; they are real and
alertable later, not needed for a coherent first release):

| ID | Purpose | Trigger (transition) | Source fields |
|---|---|---|---|
| A | POI new/activated | POI index enters the eligible set for the first time this session | `poiDirection`, `poiTier`, `poiStatus` (existing eligibility test, unchanged) |
| B | BTMM validated at POI | `btmmSetupByPoi[i]` transitions from `-1` to a real setup index | `btmmSetupByPoi`, `btmmDir` |
| C | Permission entered actionable band | `permission` transitions INTO `{BUY_BIAS, SELL_BIAS}` from any other value | `permission` |
| D | Permission downgraded/lost | `permission` transitions OUT OF `{BUY_BIAS, SELL_BIAS}` into any other value | `permission` |
| E | POI terminal/invalidated | `poiTerminal` transitions `false -> true` (fires on the SAME bar the active-POI loop gives that POI its final evaluation — Section 9) | `poiTerminal` |

All five are edge-detected (previous-bar value vs. current-bar value),
never level-checks re-fired every bar a state merely persists.

## 7. Event vs. state, and the confirmed-bar contract

Every trigger above is an EVENT (a transition), never a STATE (a level
that stays true). "Permission is BUY_BIAS" is not itself alertable; "an
eligible POI's permission just became BUY_BIAS this bar" is. This requires
one new piece of state P8 must add (Section 10) — none exists today.

**Confirmed-bar rule (no exception found to override the default):** alert
decisions are made ONLY from `barstate.isconfirmed` state, exactly matching
the active-POI loop's own existing gate (`p7_dev.pine:5899`). The forming/
realtime bar is never evaluated for a transition. This is not a new
restriction — it is the SAME rule the entire P5/P7 engine already uses; P8
adds no new evaluation timing.

## 8. Score-band-entry precision note (ties to the already-disclosed float64 finding)

Alert C/D's trigger is `permission` itself (a `C_PERM_*` code), not
`finalScore` crossing 45/65 directly — this sidesteps re-deriving the exact
band arithmetic in alert logic (a second decision engine, forbidden by
Phase 5's own rule) and inherits, rather than re-litigates, the already-
disclosed and accepted momentum float64 boundary risk
(`BTRC_V1_P5_FLOAT64_BOUNDARY_CLASSIFICATION.md`): if that ≤1-point wire
gap ever nudges `permission` across a band on a given real bar, alert C/D
fires on whatever `permission` the closed engine actually produced — same
as the P7 UI panel already does. P8 does not need to, and must not,
independently re-derive band membership.

## 9. Per-POI dedup key, terminal handling, multiple POIs

**Dedup key**: `(alert_id, poiIdx, transition_identity)` where
`transition_identity` is the specific (from-state, to-state) pair for
score/lifecycle-style alerts, or just presence for one-shot alerts
(new/terminal). `poiIdx` is the SAME raw P3 registry array index the
active-POI loop and P7's display table already use as canonical identity
(`array.push(p7PoiIdx, i)`, confirmed the only per-POI handle Pine has —
no UUID scheme exists in Pine; per `BTRC_V1_P0_PYTHON_TO_PINE_ARCHITECTURE_MAP.md`,
"Content-addressed identity is not reproducible in Pine ... an expected
engineering adaptation, not a defect"). Never key by price/timeframe/
direction alone — two distinct POIs can share all three.

**Terminal current-bar rule**: unchanged from the frozen P5/P7 active-POI
contract — a POI going terminal gets its final evaluation on the bar it
goes terminal, then is excluded next bar. Alert E fires exactly once, on
that same final bar, reading the SAME `poiTerminal` flag the loop already
transitions on — no new terminal-detection logic.

**Multiple POIs same bar**: one alert per POI, per transition, uncapped.
**P7's 8-row display cap has zero authority over the P8 alert universe** —
alerts must be evaluated over the full eligible set (`p5N = array.size
(poiStatus)`), never `p7MaxVisiblePois`. This mirrors the already-proven
"display bounded, evaluation unbounded" invariant from P7's own closure
(`test_p7_ui_display_model.py`).

## 10. New state P8 must add (and what it must NOT duplicate)

Confirmed: **no existing array tracks a previous bar's per-POI
`permission`/`lifecycle`/`btmmSetupByPoi` value** — `poiP5FinalDone` is a
one-time "already finalized" flag, not a previous-value store. P8 needs
exactly:

```
var array<int>  p8PrevPermission   (per registry index, initialized to a sentinel e.g. -1)
var array<bool> p8PrevBtmmValid
var array<bool> p8PrevPoiKnown      (has this index been seen as eligible before)
var array<bool> p8PrevTerminal
```

Each grown/cleared-on-first-sight exactly like `poiP5FinalDone` already is
(`p7_dev.pine:5904-5908` pattern) — additive, no existing array touched.
**No second BTMM/lifecycle/permission engine** — P8 reads the SAME
`permission`/`btmmSetupByPoi`/`poiTerminal` the active-POI loop already
computes this bar, compares to its own previous-value array, done.

## 11. Reload and host-timeframe-switch semantics

**Reload / remove-re-add**: `var` arrays reset on script re-initialization
(the same behavior every existing `var array` in this codebase already
has — P8 adds no new persistence mechanism, so it inherits no new
limitation). Consequence: on a fresh attach or reload, EVERY currently-
eligible POI would look "new" to P8's previous-state arrays on the first
confirmed bar after (re)start, which would misfire alerts A-E as if
transitions just happened. **Required mitigation, to design (not
implement) here**: seed `p8Prev*` from the CURRENT bar's real values on the
very first confirmed bar after (re)start (a one-bar "priming" pass that
observes but does not alert), exactly mirroring how `poiP5FinalDone` avoids
re-flagging already-terminal POIs on first sight. This is a real,
necessary design decision for the implementation phase — flagged here so
it is not rediscovered as a live "bug" later.

**Host-timeframe switch (M15→H1 etc.)**: since P3's POI registry is
host-only (single M15/M5/H1 context per the closed architecture — no MTF
POI registry exists), switching host timeframe is architecturally
equivalent to a fresh attach: an entirely different POI universe (already
observed directly — Section 2 of `BTRC_V1_P7_UI_LIVE_ACCEPTANCE_ADDENDUM.md`
recorded completely disjoint POI index ranges across M15/M1/M5 switches
this campaign). **The same priming-pass mitigation applies**: a host
switch must re-prime, not fire a wave of false "new POI" alerts for what
is actually just a different chart's pre-existing history.

## 12. Testability — Python oracle and real-replay feasibility, without new Pine

**Feasibility: yes, entirely offline, using data already captured.** The
existing `tests/parity_support/p5_atomic_capture_log.py` parser already
extracts, per confirmed bar, every P5EVAL row's `poiIdx`, `poiTerminal`,
`btmmValid`, `permission`, `lifecycle` — exactly the fields Section 6's V1
alerts need. A P8 "alert oracle" can be built as a pure function over the
SAME already-committed `artifacts/p5_capture/p5_atomic_raw_log.csv`
capture (105 wire bars / 9,634 rows, real FXCM data) used to close P5:
group rows by bar (already sorted by the parser), walk bars in order,
maintain the `p8Prev*` maps in Python, and emit the canonical event stream
(`event_type`, `poiIdx`, `bar` timestamp, payload fields) — **no new
TradingView capture is required to prove the oracle logic**; a
Pine-side ATOMIC twin (emitting the same events) would still be needed
later to prove PINE reproduces the oracle's stream, following the exact
P5X/P5WIRE precedent already established twice in this project.

## 13. Message payload contract (for the eventual Pine `alertcondition`/`log.info` design)

Fields: `event_type`, `poiIdx` (canonical identity), `poiDir` (BULL/BEAR),
`poiTier`, `hostTimeframe`, `provider/symbol` (`syminfo.prefix`+
`syminfo.ticker`, matching the existing P7 panel convention), `permission`
(label), `lifecycle` (label), `finalScore`, `barCloseTime`. Excluded:
every T1-T5 diagnostic component score (regime/momentum/breakout/etc. —
available in the P5EVAL log for debugging, not needed in an alert
message), and unconditionally: entry price, stop loss, take profit,
position size — no such fields exist anywhere in the closed engine to
expose in the first place.

## 14. Resource budget

```
plots                       63/64 (P5/P7 unchanged) -- P8 target: 0 new
request.security             6    -- P8 target: 0 new (alerts consume
                                      already-requested MTF state, request
                                      no new context)
```

**Mechanism choice (Phase 18-19, decision deferred to implementation, not
made here)**: TradingView's `alert()` function call (not
`alertcondition()`) supports fully dynamic, per-call message text and
firing from inside a loop — the natural fit for a per-POI event stream
with real payload fields, and it costs **zero** plot/request budget
(unlike `alertcondition()`, which is a fixed, static-message,
script-level declaration unsuited to per-POI dynamic content and would
need one static declaration per alert TYPE rather than per POI). This
audit records the trade-off; the implementation phase makes the final
call and documents it against real compile/runtime evidence.

## 15. Mutation plan (for the future test suite, not built here)

Must be proven to FAIL (i.e., the future test suite must catch each):
alert repeats every bar while state persists; event fires one bar early/
late relative to the real transition; a forming-bar alert; wrong POI
identity (index reused/confused); duplicate emission of the same event;
terminal event omitted; P7's display cap silently limiting the alert
universe; a host-timeframe switch producing false "new" events without
priming; a reload producing duplicate alerts for already-existing POIs;
an unchanged permission incorrectly re-firing; a same-band score wobble
incorrectly treated as a band-entry event; wrong provider/symbol in the
payload.

## 16. Recommended implementation sequence (if/when authorized — not started here)

1. P8 event model + Python oracle (Section 12), built purely from the
   existing P5 capture — no new Pine yet.
2. Directed + randomized/prefix tests against the oracle (mirroring the
   `p7_ui_display_model.py` stress-test discipline already established).
3. Dedup/priming design finalized and tested offline (Section 11).
4. Pine P8 DEV: additive `log.info`/`alert()` block on top of the closed
   P7 engine, zero new plots/requests, following the exact "copy + append"
   pattern every prior phase used.
5. TradingView compile, live observation (debug-gated first).
6. P8 ATOMIC twin if a per-bar+per-event capture is needed beyond what
   debug logging already gives (precedent: P5WIRE).
7. Real parity: Pine event stream vs. Python oracle, on real captured data.
8. P8 closure document, following this project's established evidence
   bar (digest match, live host-matrix, mutation-tested guards).

## 17. Gate

```
P8_EXISTING_REQUIREMENTS_RECOVERED        TRUE   (P0 alerts-plan prior art found, not blindly adopted)
P8_ALERTABLE_STATE_INVENTORIED            TRUE   (permission/lifecycle/poiTerminal/btmmSetupByPoi, exact codes)
P3_CONTEXT_REQUIRED_FOR_P8_V1             FALSE
P4_REVIEWED_EVIDENCE_REQUIRED_FOR_P8_V1   FALSE
P8_V1_ALERT_SET_DEFINED                   TRUE   (5 alerts: A-E, Section 6)
P8_EVENT_VS_STATE_CONTRACT_DEFINED        TRUE
P8_CONFIRMED_BAR_CONTRACT_DEFINED         TRUE   (inherits existing barstate.isconfirmed gate, no new rule)
P8_DEDUP_KEY_DEFINED                      TRUE   (poiIdx + transition identity, no new identity scheme)
P8_RELOAD_HOST_SWITCH_RISK_IDENTIFIED     TRUE   (priming-pass mitigation designed, not yet implemented)
P8_RESOURCE_BUDGET_SAFE                   TRUE   (0 new plots, 0 new request.security -- target, not yet built)
P8_OFFLINE_TESTABILITY_CONFIRMED          TRUE   (existing P5 capture sufficient for the oracle)
P8_NEW_STATE_STORAGE_IDENTIFIED           TRUE   (4 new var arrays, Section 10, no engine duplication)
P8_GO_NO_GO                               GO
P1_THROUGH_P7_CHANGED                     FALSE
P8_IMPLEMENTATION_STARTED                 FALSE
```

**Not claimed here.** That the five V1 alerts are the RIGHT product choice
commercially, or that this audit's design decisions (priming-pass shape,
`alert()` vs `alertcondition()`, exact payload) are final — they are the
audit's recommendation, to be validated against real compile/runtime
evidence when implementation is authorized. No broker/order/entry/SL/TP
capability is proposed anywhere in this document.
