# BTRC-V1 RC5 — Terminal oracle: proving POI_TERMINAL independently

Status: **CLOSED**. All five hosts clean on the corrected path, after one real
defect was found and fixed.

## Why an oracle at all

P8's terminal stream had only ever been asserted against itself. A test that
reads the same code path it is checking proves that the path is consistent, not
that it is right. So this builds a second answer to a different question and
compares the two:

* **The oracle** asks: for each POI, what is the first causally observable
  prefix on which it becomes `GENUINE_INVALIDATION_CONFIRMED`? It reads
  lifecycle state and never reads an event.
* **P8** asks: when did the active-POI loop observe `terminal`? That runs
  through the eligibility algebra and the alert engine.

The independence is real and worth stating precisely, because `rc5_is_terminal`
has **two** causes — a FAILED interaction episode (the RC4 framework's "price
accepted beyond the POI with no reclaim") *or* the lifecycle walk's
`GENUINE_INVALIDATION_CONFIRMED`. The oracle knows only the second. If those
two failure detectors ever disagree, it surfaces as an EXTRA rather than being
quietly absorbed.

## The defect this found first was in the oracle

The first version reported M45 as "20 expected / 19 actual", and explained the
twentieth with a new classification, `NEVER_ENTERED_THE_EVENT_LOOP`.

That was wrong, and the way it was wrong is the useful part.

The oracle rebuilt same-origin authority by constructing a **fresh**
`Rc5SemanticLedger`. That ledger has no provenance records — the real one is
filled by the kernel, which `iter_level_a_bars` passes in — so it clustered
differently from the ledger P5 actually used. It therefore expected a terminal
event for a `BULLISH_ENGULFING` that P5 had already suppressed as a
subordinate of a same-origin `BUY_ORDER_BLOCK`. The missing event was then
covered by an invented class that sounded plausible.

Tracing it on a 118-bar synthetic — small enough to inspect bar by bar — showed
the excuse was false immediately: the POI was alive **and** available for 18
consecutive bars, alongside a POI from the same origin that *was* evaluated.
The 529-bar real capture never made that visible.

### Numbers withdrawn

| Withdrawn | Reason |
| --- | --- |
| M45 `20 expected / 19 actual` | fabricated authoritative set |
| H3 `14 / 14` | same |
| `NEVER_ENTERED_THE_EVENT_LOOP` as a class | artifact of the bug; removed |

### The fix removes the possibility, not the symptom

`level_a_replay` now exposes the suppression decision it actually used as
`LevelABar.suppressed_poi_ids`, and the oracle consumes it. Authority can no
longer be fabricated by a consumer, because a consumer can no longer derive it.
Suppression is reported as its own class instead of hiding inside another.

**Contract safety.** `LevelABar` lives in `tests/parity_support/`, `src/`
imports it zero times, it is a plain dataclass with no `content_fingerprint`,
and it is not a P3/P5/P8 transport model. The added field touches no frozen
contract or fingerprint.

## What the proof now checks

| Check | Question |
| --- | --- |
| missing | a lifecycle invalidation P8 never reported |
| extra | a terminal P8 reported with no lifecycle invalidation behind it |
| duplicate | the same POI going terminal twice |
| post-terminal | any event at all after a POI's terminal, read from the real event stream |
| **time mismatch** | the right POI on the **wrong bar** |
| **non-invalidation reason** | a terminal reported as anything but `INVALIDATED` |

The last two were absent originally. Set agreement said nothing about timing: a
terminal firing on the wrong bar passed silently. The oracle's transition time
and P8's `bar_ms` are the same instant by construction — `level_a_replay`
derives `bar_ms` from `availability_time_utc` — so they compare directly
without re-deriving either.

### Classified exceptions

A genuine invalidation legitimately produces no event in three cases, each
named rather than waved away:

* `ALREADY_TERMINAL_WHEN_FIRST_SEEN` — nothing alive was ever observed.
* `AUTHORITY_SUPPRESSED` — a same-origin subordinate, removed before the
  opportunity loop. **This is the real class behind the M45 twentieth record.**
* `NEVER_ENTERED_THE_EVENT_LOOP` — *retained in the enum but no longer
  produced anywhere.*

A test asserts `expected == observable + sum(exceptions)`, so no expectation
can be quietly dropped.

## Non-vacuity

A terminal proof run over a series where nothing ever dies passes every
assertion while proving nothing. The original synthetic series never
re-mitigated anything.

`episodes_then_collapse` now drives a deep dip that reacts, a deeper dip that
reacts again, a wick through the far edge that closes back inside, and only
then a breakdown. The probe reports which situations a series actually
exercised and a test asserts all five required classes are present:
mitigation, re-mitigation, genuine invalidation, authority suppression, and an
emitted terminal.

`false_break_reclaim` is the one the synthetics do not reliably produce. Rather
than claim coverage, the test records where it *is* proven — the lifecycle
suite, against the real breach walk — and the real M45 capture shows one.

## Host matrix (corrected path only)

Final, after the fix below. **All five hosts clean.**

| Host | bars | expected | suppressed | observable | actual | matched | missing | extra | dup | post | time | reason | clean |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M5 | 2000 | 122 | 6 | 116 | 116 | 116 | 0 | 0 | 0 | 0 | 0 | 0 | **yes** |
| M15 | 2000 | 103 | 12 | 91 | 91 | 91 | 0 | 0 | 0 | 0 | 0 | 0 | **yes** |
| H3 | 300 | 14 | 0 | 14 | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | **yes** |
| H4 | 2000 | 122 | 9 | 113 | 113 | 113 | 0 | 0 | 0 | 0 | 0 | 0 | **yes** |
| M45 *(diag)* | 529 | 20 | 1 | 19 | 19 | 19 | 0 | 0 | 0 | 0 | 0 | 0 | **yes** |

Before the fix M15 had 1 and H4 had 2 time mismatches; every other figure in
this table is unchanged by it. The fix moved three terminals onto the correct
bar and altered nothing else — M5, H3 and M45 re-ran to identical counts.

Every unobservable record on every host is `AUTHORITY_SUPPRESSED` — a
same-origin subordinate, owed no event of its own. H3 has no suppression at
all, so its expected and observable counts coincide.

All five coverage classes are exercised on every 2000-bar host, including real
false-break reclaims (M5 24, M15 15, H4 4, M45 1).

### Closed: three terminals fired EARLY

`missing`, `extra`, `duplicate`, `post-terminal` and `non-invalidation` are
**zero on all five hosts**. The only failures are timing, and they are the
failures the set-only comparison used to hide: the right POI, the wrong bar.

| Host | poi_idx | expected (lifecycle) | actual (P8) | early by |
| --- | --- | --- | --- | --- |
| M15 | 76 | 2026-08-28T16:00Z | 2026-08-28T15:00Z | 1h (4 bars) |
| H4 | 336 | 2025-08-21T02:00Z | 2025-08-20T22:00Z | 4h (1 bar) |
| H4 | 613 | 2025-10-22T02:00Z | 2025-10-21T22:00Z | 4h (1 bar) |

P8 fires EARLIER than the lifecycle transition in every case — 3 of 204
observable terminals (1.5%).

### Traced, and the first hypothesis was wrong

The working hypothesis from code reading — a wick-started framework clock
versus a close-started lifecycle clock — was **disproved** by the trace. Wicks
have nothing to do with it.

Both H4 cases have an identical shape:

| bar | lifecycle status | episode | evaluated | event |
| --- | --- | --- | --- | --- |
| 326 | `CLOSE_BREACH_CANDIDATE` | ACTIVE | yes | — |
| 327 | `RECLAIM_FAILED` | ACTIVE | yes | — |
| 328 | `RECLAIM_FAILED` | **FAILED** | yes | **POI_TERMINAL** |
| 329 | `GENUINE_INVALIDATION_CONFIRMED` | — | **no** | — |

`GENUINE_INVALIDATION_CONFIRMED` requires the full reclaim window, **at least
two of its three bars closing beyond the far edge, AND the last bar closing
beyond** (`poi/lifecycle.py:418-432`). A window that merely fails to reclaim
lands on `RECLAIM_FAILED`, and the walk KEEPS WATCHING — the zone has not
failed and may still survive. The framework's episode rule has no such test.

So `rc5_is_terminal`'s second branch fired `POI_TERMINAL` on a bar where the
lifecycle still said `RECLAIM_FAILED` — a status `rc5_validity` reports as
**VALID**. A POI was simultaneously valid and terminal, which is precisely the
contradiction the validity / display / actionability split exists to prevent.

It was also **self-concealing**: the POI left the active set, so when `GENUINE`
arrived it was no longer evaluated and the CORRECT terminal could never fire.
The false event suppressed the true one.

The M15 trace settles that this was premature rather than merely early. After
the false terminal at bar 599 the zone was **re-tested** — a fresh
`CLOSE_BREACH_CANDIDATE` at bar 600, tap count rising to 2 — and only genuinely
failed at bar 603. It was declared dead while still alive and still being
traded.

### Resolution

Only the frozen breach walk may declare a zone failed. The FAILED-episode
branch was removed from `rc5_is_terminal`; `rc4_is_terminal` is untouched, so
RC4 behaviour is unchanged.

Removing it **loses nothing**, and the matrix proves that rather than asserting
it: `extra` was 0 on all five hosts, so every terminal P8 emitted already had a
lifecycle `GENUINE` behind it. The branch never found a failure the breach walk
missed — it only ever announced one early.

Pinned by three regressions: valid and terminal are mutually exclusive for
every POI on every bar of a replay; `RECLAIM_FAILED` is valid and not terminal
under every episode value; and a FAILED episode alone cannot kill a zone in any
non-`GENUINE` lifecycle state.

**M45 host identity.** M45 has no member in the frozen `Timeframe` enum and
must not gain one, so it is driven through an M15 carrier. `Rc5HostIdentity`
derives the host from the series' own modal bar spacing and records **M45 / 45
minutes**, with the carrier noted separately. A host-local key built from the
carrier would put M45 and M15 in one key space.

## The layers this froze

```
VALIDITY  >=  DISPLAY ELIGIBILITY  >=  P5 ACTIONABILITY
```

`rc5_validity()` owns the bottom layer and takes **no ledger** — a test asserts
that signature, because passing authority in is how the layers would collapse
into one. `display_hidden_reason()` is now validity plus authority rather than
a parallel derivation, so the drawn set cannot disagree with the set terminal
monitoring watches.

### Two relationships that are not what they look like

The tidy nesting "P5 actionable ⇒ display eligible ⇒ valid" is **false as
stated**, and asserting it fails:

1. A POI's terminal is *reported* by evaluating it on the bar it became
   invalid. So an evaluated POI is either still valid, or is being evaluated
   **exactly once** on its own terminal bar. That is the assertion, including
   the "exactly once".
2. Display does not separate from P5 by loop membership — on the measured
   series *every* visible POI is also evaluated. What separates them is the
   **decision**: a visible, evaluated, perfectly valid zone is routinely not
   actionable, because permission is a supervisory verdict about conditions,
   not a property of the zone.

The reverse direction is deliberately not asserted: authority and supersession
legitimately hide valid formations, and a test proves that asymmetry is real
rather than leaving it as a claim.

### `PROMOTED_TO_ORDER_BLOCK` — interpretation B

`poi/enums.py` is explicit: the engulfing record of a formation confirmed as a
leg origin **ends** when its ORDER BLOCK record becomes available, "so one
formation never has two live records".

So the promoted record **ceases to be a standalone lifecycle entity** — the
ORDER BLOCK carries the zone from there on. It remains in history; it is not a
live zone; it is not `VALID`. Chosen from existing architecture, not invented.

Measured consequence: every POI the collapse series suppresses is an engulfing
the lifecycle *independently* marked `PROMOTED_TO_ORDER_BLOCK`. Authority and
supersession reach the same verdict by different routes — a real consistency
check, so it is asserted rather than glossed.
