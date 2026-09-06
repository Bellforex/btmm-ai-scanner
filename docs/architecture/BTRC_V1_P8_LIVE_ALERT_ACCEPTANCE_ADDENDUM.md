# BTRC-V1 P8-A — Live Alert Acceptance Addendum

Status: **P8 PLATFORM ACCEPTANCE — CLOSED WITH ONE DISCLOSED GAP (real Alert-object delivery)**
Branch: `pine-p4-btmm`
Addendum date: 2026-09-06
Supersedes/corrects: `BTRC_V1_P8_ALERT_CLOSURE.md` Sections 6 and 10 (H1 status — see those sections' inline correction markers)

This addendum records the MEGA-AUTONOMOUS-27 acceptance campaign: closing the
real-platform evidence gaps left after `BTRC_V1_P8_ALERT_CLOSURE.md` — an
actual TradingView Alert object, and live priming/reload/host-switch
behavior across M5/M15/H1. It does not reopen the event engine, the five V1
events, or P1-P7. No source code changed this session.

## 1. Baseline

- Branch: `pine-p4-btmm`
- HEAD at session start: `f0a80004b86fbd44b89702d08928dbab90fb71c4`
- `git status --short --untracked-files=all`: clean
- `git diff --check`: clean
- P8 DEV source: `sha256 80b330c6f14501c4796c41dfd19040b0af394e90e9e829e64331915983b1edb4` (unchanged from closure)
- Confirmed via ancestry (`git merge-base --is-ancestor`) that the P5 H1
  runtime-safety fix (`5b428ab` P5, `917976a` P7, `a4a8b91` docs) is an
  ancestor of the P8 DEV creation commit (`88037ff`) — **P8 DEV has always
  contained the H1 `na(ext)` guards**; this was never actually at risk, only
  mis-stated in the original closure document.

## 2. Regression freeze (Phase 1)

`tests/unit/test_p8_real_pine_parity.py` re-run standalone and re-derived
independently in this session: **456 / 456 events exact**, digest
`(H1=294719549, H2=35571918)` on both sides — unchanged from closure. Full
P8 suite (`test_p8_alert_oracle.py`, `test_p8_capture_log.py`,
`test_p8_semantic_equivalence.py`, `test_p8_real_pine_parity.py`): **80
passed**. No event-engine code was touched.

## 3. Actual TradingView Alert object — BLOCKED by a real platform limit

Using the standard "Add alert on BTMM + POI + BTRC Scanner [P8 DEV]"
workflow (condition: `Any alert() function call`, interval: same as chart,
webhook explicitly unchecked and empty, notifications: in-app/toast/sound
only):

- TradingView's own upsell dialog stated: *"Right now, you have a limit of
  **0 technical alerts** in your plan"* (Basic plan, account bellcare1994).
- Clicking **Create** anyway produced a real, reproducible failure:
  **"Error! Alert saving failed. Please, try again."**
- The Alerts panel confirmed **zero existing alerts** — this is not a quota
  already consumed elsewhere; the Basic plan simply does not include any
  technical/indicator alert capacity on this account.
- Resolving this requires a paid plan upgrade (Premium, $400/yr shown in
  the upsell) — a real purchase this session will not make without
  explicit user authorization, per this project's standing safety rules.

**User decision (asked explicitly this session): skip the real alert,
proceed with the remaining phases using the already-established
`p8DebugLog` proxy log stream as the evidence source.** This is the same
methodology `BTRC_V1_P8_ALERT_CLOSURE.md` already used for its own
priming/reload/host-switch evidence (Section 3's canonical, untoggled
`P8EVENT`/`P8PRIME` stream mirrors exactly what every `alert()` call in the
same bar would have fired — same `p8Primed` gate, same per-bar conditions).

**Consequence**: Phases 4-7, 16, and 19 of the original brief (create a
real Alert object, observe its first genuine firing, compare its payload
to the simultaneous `P8EVENT` record, toggle one alert class, verify
Alert-object persistence across reload/remove-readd, and delete the test
alert) are **not verified this session** — there is no Alert object to
observe. Everything else (priming, reload, M5/M15/H1 host-switch, H1
reload, remove/re-add, no-flood, no-`RE10041`) is verified via the debug
log proxy below, on the exact same code path (`p8Primed`, the four
`p8Known`/`p8Prev*`/`p8TerminalAlerted` caches, and the `if p8Enable*`
gates immediately preceding each `alert()` call) the real Alert mechanism
would use.

## 4. Priming — fresh attach and reload (Phases 5, 8)

Configuration: `p8DebugLog` enabled via Settings on an already-fresh
instance is insufficient to observe priming (settings-only changes do not
reinitialize `var` state — established both architecturally and
empirically last session). To observe a genuinely fresh `p8Primed` cycle
under debug logging, P8 DEV was removed (context-menu **Remove**, never the
trash icon) and re-attached with `p8DebugLog` enabled immediately after.

- **Fresh attach**: the resulting `P8EVENT` stream showed events spread
  across genuine historical bars (`2026-09-04T19:00`, `T19:30`, `T20:15`,
  ...) at their true first-occurrence bars — not a single burst of every
  known POI dumped at once. Error-only log filter: **"No criteria
  matches"** (zero runtime errors).
- **Reload** (same instance, `p8DebugLog` still enabled, layout saved
  first): after a full browser reload, the same spread pattern held (now
  `T19:00`, `T18:00`, `T19:00`, `T21:00` reflecting the moment's real data),
  with zero runtime errors. This confirms reload reinitializes `var` state
  identically to a fresh attach without flooding — consistent with the
  architecture in `BTRC_V1_P8_ALERT_CLOSURE.md` Section 3.

No `P8PRIME` burst was directly observed in either case (the priming bar's
own log lines age out of the live panel's rolling view faster than the
subsequent real event stream accumulates — the same practical limitation
already disclosed in the original closure's Section 7/10). This does not
weaken the finding: a broken priming implementation would manifest as a
mass-flood of `POI_ACTIVATED` for every already-known POI at once, which
was not observed in either case.

## 5. Host-timeframe matrix (Phases 9-14)

All transitions performed on the live chart (account bellcare1994,
FXCM:XAUUSD, `p8DebugLog` enabled throughout), Error-only log filter
checked after every transition:

| Transition | Errors | Event spacing observed | Notes |
|---|---|---|---|
| M15 (baseline) | 0 | 15-min bars | clean before any switch |
| M15 → M5 | 0 | 5-min bars (`T20:15`,`T20:20`,`T20:25`,`T20:30`,`T20:40`) | no flood |
| M5 → M15 | 0 | 15-min bars, resumed | clean reprime |
| M15 → H1 | **0 — zero `RE10041`** | hourly bars (`T16:00`,`T18:00`,`T19:00`,`T21:00`) | **the corrected result** |
| H1 → reload (host=H1) | **0 — zero `RE10041`** | same hourly pattern preserved after reload | the "load-bearing" case per the P5 fix precedent |
| H1 → M15 | 0 | 15-min bars, resumed | clean reprime |

**H1 status is corrected here**: the original closure document's "H1 was
intentionally not tested" was stale at the time it was written — the
`RE10041` defect it referenced was already fixed (2026-09-05, before P8 DEV
was even created) and P8 DEV inherits that fix by direct ancestry (Section
1). H1, H1-reload, and H1→M15 are now all live-verified clean.

No naturally-occurring live event was observed to fire in real time during
either H1 pass (Phase 13) — per the brief, none was fabricated. The already
-observed historical H1-spaced event stream (above) is accepted as
sufficient evidence of correct hourly-boundary behavior.

## 6. Remove / re-add (Phase 15)

Performed twice more this session (in addition to the priming-observation
cycle in Section 4), always via the Object Tree row's right-click →
**Remove** — never the ambiguous legend-row trash icon (the cause of last
session's disclosed script-deletion incident). Each time:

- The saved script `BTMM + POI + BTRC Scanner [P8 DEV]` was confirmed still
  present in the Indicators dialog's "My scripts" list before re-adding.
- Re-attaching produced a clean, error-free instance with **script
  defaults** (not the previous instance's custom settings — TradingView
  does not carry per-instance settings across a remove/re-add, only across
  a page reload of an already-attached instance; this is the same
  distinction already established and now reconfirmed).

## 7. Alert-object persistence (Phase 16) — not applicable

No Alert object exists (Section 3), so its persistence behavior across
reload/remove-readd could not be observed this session. This remains an
open question for whenever the plan limit is resolved.

## 8. Multiple same-bar events and permission-volume observation (Phases 17-18)

Computed directly from the real 460-event FXCM capture
(`artifacts/p8_capture/p8_dev_raw_log.csv`, already the closure's evidence
base — no new live data needed for this specific check):

- **60 distinct (bar, POI) pairs** produced more than one canonical event
  type on the same bar (e.g., `POI_ACTIVATED` + `BTMM_VALIDATED` +
  `PERMISSION_ENTERED_ACTIONABLE` co-occurring for one POI at its
  first-ever confirmed bar).
- **The busiest single bar produced 41 real events across all POIs**
  (`bar=1788508800000`) — far beyond P7's 8-row display cap. All 41 parsed
  intact from the capture with zero loss, direct evidence the underlying
  `P8EVENT`/`alert()` emission path is never bounded by
  `p7MaxVisiblePois` (mechanically proven already in
  `test_p8_semantic_equivalence.py`; this is the real-data confirmation).
- **Permission-class events dominate volume**: `PERMISSION_ENTERED_ACTIONABLE`
  (33.5%) + `PERMISSION_LOST_ACTIONABLE` (30.4%) = **63.9% of all real
  events**, versus `POI_ACTIVATED` (12.8%), `BTMM_VALIDATED` (12.8%), and
  `POI_TERMINAL` (10.4%). Operationally, a user with all five alert classes
  enabled would see roughly two out of every three notifications be a
  permission-band transition. This is recorded as a genuine usability
  observation, not a defect — no change to the V1 semantic oracle was made
  or is proposed here. Any future coalescing/rate-limiting of permission
  notifications belongs to a separate UX-layer decision, not this closure.

## 9. Cleanup and final live state (Phases 19-20)

No test Alert object was created (Section 3), so none required deletion.
Final chart state: `BTMM + POI + BTRC Scanner [P8 DEV]` attached with
verified production defaults (`p8DebugLog` unchecked, `Calculated bars =
1800`, all five `p8Enable*` toggles on, `Enable P8 alerts (master)` on),
host timeframe M15, zero error badges, zero unsaved Pine edits. `[P6 DEV]`
remains the other attached indicator (Basic plan's 2-indicator cap).

## 10. Regressions re-confirmed (Phase 23)

- P8 real parity: 456/456, digest match — Section 2.
- P8 semantic equivalence vs. P7: 9/9 passed (no source changed).
- Full repository suite: not re-run in full this session (no source
  changed since the closure commit's full-suite green run of 3495 passed);
  the targeted P8 suite (80 tests, Section 2) is the regression evidence
  for this addendum specifically.

## 11. Quality gates (Phase 24)

- `git status --short`: only this addendum and the closure-document
  correction are new/changed.
- `git diff --check`: clean.
- No Python source changed this session — no ruff/mypy delta to report
  beyond the already-clean state recorded in the closure document.

## 12. Formal status (Phase 25)

- P8 ALERT ORACLE = CLOSED (unchanged)
- P8 PINE EVENT ENGINE = CLOSED (unchanged)
- P8 REAL PINE↔PYTHON EVENT PARITY = VERIFIED (reconfirmed: 456/456, digest match)
- **P8 ACTUAL TRADINGVIEW ALERT DELIVERY = NOT VERIFIED — blocked by a real
  0-technical-alert plan limit on the test account; not a code defect**
- P8 FRESH-ATTACH PRIMING = VERIFIED (via debug-log proxy; no flood, zero errors)
- P8 RELOAD PRIMING = VERIFIED (via debug-log proxy; no flood, zero errors)
- P8 M5 HOST REPRIMING = VERIFIED (zero errors, correctly-spaced events)
- P8 M15 HOST REPRIMING = VERIFIED (zero errors, correctly-spaced events)
- **P8 H1 HOST REPRIMING = VERIFIED (zero `RE10041`, zero other errors — corrected from the original closure's stale "not tested")**
- **P8 H1 RELOAD = VERIFIED (zero `RE10041`, the load-bearing case)**
- **P8 = CLOSED WITH ONE DISCLOSED GAP**: everything reachable without a
  paid plan upgrade is verified; real Alert-object delivery is the one
  remaining open item, blocked by platform economics, not code.

P3 CONTEXT = DEFERRED (unchanged)
P4 REVIEWED EVIDENCE = DEFERRED (unchanged)

PROFITABILITY = NOT ESTABLISHED
PRODUCTION APPROVED = FALSE

## 13. Safety (Phase 25, Section I)

- Webhook execution: FALSE (explicitly verified unchecked and empty in the attempted Create Alert dialog before it failed)
- Broker integration: FALSE
- Entry/SL/TP/position-sizing in any payload: FALSE (unchanged from closure)
- Push: FALSE
- Merge to main: FALSE
- Publish: FALSE
- Live trading: FALSE

## 14. Commit

Documentation/evidence-only commit (this addendum plus the inline
correction markers in `BTRC_V1_P8_ALERT_CLOSURE.md`). No Pine or Python
source changed. No push, no merge to `main`.

## 15. Stop

**P9 is not started.** The one remaining open item (real Alert-object
delivery) requires either a plan upgrade the user has not authorized, or a
different TradingView account/plan with technical-alert capacity — a
decision for the user, not something to route around.
