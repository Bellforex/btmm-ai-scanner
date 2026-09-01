# BTRC-V1 P4 — BTMM Setup Engine: CLOSURE

Status: **P4 BTMM CORE — CLOSED**
Branch: `pine-p4-btmm`
Architecture of record: [BTRC_V1_P4_BTMM_ARCHITECTURE.md](BTRC_V1_P4_BTMM_ARCHITECTURE.md)
Predecessor: [P3 POI CORE closure](BTRC_V1_P3_POI_CORE_CLOSURE.md)

Every number below was produced by running the thing it describes. Where a claim
rests on a test, the test is named; where it rests on a captured artifact, the
artifact's hash is given.

---

## 1. What is closed, and what is not

**P4 BTMM CORE: CLOSED.** The complete BTMM state machine is ported to Pine,
compiled, proven against production on real data on all three supported
timeframes, and exercised through a 72/72 runtime matrix.

**P4 REVIEWED-EVIDENCE TRANSPORT: DEFERRED.** The engine implements confirmation;
TradingView has no authorized channel to deliver human-reviewed evidence to it.

The right way to say this, and the only accurate one:

> BTMM confirmation semantics are implemented and verified. The current
> TradingView runtime has no authorized reviewed-evidence transport, so
> no-evidence live execution cannot reach confirmation.

It would be wrong to say "BTMM confirmation is not implemented."

---

## 2. The two-layer result

| | Layer A — the engine | Layer B — the runtime |
|---|---|---|
| Evidence | fixtures supplied to the oracle | `reviewed_evidence = ()` |
| `BTMM_CONFIRMED` | reachable and proven | unreachable **by construction** |
| Proven by | 77 tests, every prefix, both modes | three real-data captures |

Layer B's unreachability is structural, not conventional: the evidence channel
(`btmmEvHas`, `btmmEv*`) is **read** by the engine and **written by nothing**.
`test_p4_pine_foundation.py` asserts there is no `array.set` against any channel
array and that each is seeded exactly once with a neutral value. A change that
started populating them from market data — the one thing this port must never do
— fails that test.

Derived liquidity is the case that makes the boundary real rather than rhetorical.
A P3 `FALSE_INVALIDATION_CONFIRMED` genuinely yields `LIQUIDITY_AFTER_POI` /
`RULE_BASED`, and that is ported. It writes the location and the source and
cannot touch `liquidity_evidence_status`, which is what the gate reads. Derived
evidence says **where** liquidity was taken; only review says **that** it was
reviewed.

---

## 3. Compile and runtime

**Compile: HARD PASS.** P4 DEV compiled on the first attempt, 0 errors. The only
output was two warnings about a local named `volume` shadowing the built-in
series; renamed to `volState` → **0 errors, 0 warnings**. The atomic probe
compiled clean first try.

**Runtime: 72/72 HARD PASS.** 6 timeframes × debug{false,true} ×
{FRESH, RELOAD, SWITCH_BACK} × 2 repetitions. Zero Pine failures, zero RE10110,
zero runtime exceptions, zero array or history errors.

Every supported timeframe produced exactly **one** distinct count tuple across
all six of its debug observations:

| TF | registry | candidate | forming | cancelled | at final gate |
|---|---|---|---|---|---|
| M1 | 1075 | 0 | 35 | 1040 | 79 |
| M5 | 952 | 0 | 29 | 923 | 40 |
| M15 | 966 | 1 | 45 | 920 | 31 |
| H1 / H4 / D1 | 0 | 0 | 0 | 0 | 0 |

`candidate + forming + cancelled = registry` on every supported timeframe, i.e.
**blocked = 0 and confirmed = 0** — the Layer B contract holding on live data
across all 36 supported-timeframe observations.

Reload driver is `chartWidget.setSymbol(<same>)`. `study.restart()` remains
avoided; P3 recorded that it wedges the study, and nothing here re-tested that.

Evidence: `artifacts/p4_runtime/P4_RUNTIME_MATRIX_FINAL.txt`
(`9eb0a6813b1ae6e926e2ca7e3571c8cec8154a7b88565a92308fda8cff7796ca`). One M15
diagnostic read returned `na` while the study was healthy; it is recorded there
rather than smoothed over.

---

## 4. Real-data parity — all three timeframes exact

Oracle is production `analyze_btmm(..., reviewed_evidence=(), ...)`, not the
Pine-shaped model. The model is proven equal to the oracle at every prefix
elsewhere, so using production here makes the claim Pine-against-production.

| TF | anchor | setups | rows | groups | H1 | H2 |
|---|---|---|---|---|---|---|
| M15 | 1788267600000 | 968 | 968/968 identical | 9/9 | 596274171 | 986546192 |
| M5 | 1788272400000 | 938 | 938/938 identical | 9/9 | 817746747 | 538733425 |
| M1 | 1788273060000 | 1079 | 1079/1079 identical | 9/9 | 931339776 | 44739939 |

All three replays are deterministic: two fresh processes produce byte-identical
traces. Every bundle passed the full integrity gate set and declares
`evidence_present=0`, **measured** from the engine's own channel rather than
asserted — and the parser refuses any bundle where it is non-zero.

M1 is worth a note. It is supporting-only (`formationtf=0`), and it still reports
0 confirmed and 0 blocked, because the liquidity gate precedes the
formation-timeframe gate: with no reviewed evidence every setup that reaches the
final gate cancels `NO_LIQUIDITY_EVIDENCE` before
`FORMATION_TIMEFRAME_NOT_CONFIRMED` can be reached. Production does the same.

Evidence: `artifacts/p4_parity/P4_REAL_DATA_PARITY_EVIDENCE.txt`
(`9efb99e604ec2738e245552953f01e301be6cd6035c7b30437e3d14cab77d4c7`).

---

## 5. Two defects real data found, neither of which synthetic tests could

Both are recorded in full because they are the most useful part of this closure.

### 5.1 Late-discovered setups started at discovery, not availability (P4-owned)

The first M15 capture agreed on **955 of 956** setups. The one disagreement was a
resistance zone whose POI became available at bar 739 but which P3's rolling S/R
projection did not surface until bar 892 — a 153-bar delay — and whose POI was
genuinely invalidated at bar 753, *before the setup existed at all*. Pine reported
`POI_REJECTED` with no formation stage; production had already cancelled it
`INTERACTION_INELIGIBLE` on an excessive overshoot around bar 745.

Semantic availability is not engine discovery. `analyze_btmm` walks a setup from
its POI's availability whatever bar the POI was found on; a setup created at
discovery skips every bar in between. This is the same correction P3 made for POI
lifecycles in `be1df56`; the BTMM cursor needed its own copy.

Fix `0c8a4c9`: a bounded replay over the retained window, starting at the POI's
own availability, excluding the newest bar, with the engine now indexing bars by
the absolute confirmed-bar index so replayed and live bars share an axis. After
it, M15 went byte-identical across all 968 setups.

**No synthetic scenario could have found this** — every synthetic setup exists
from bar zero. The regression therefore asserts both that backfill equivalence
holds *and* that without backfill the two disagree.

### 5.2 The M5 delta was the harness, not the port (P3-tooling-owned)

The first M5 comparison gave Pine 938 setups against 937, with **all 937 shared
setups already byte-identical**. The extra was a `SUPPORT_ZONE` at
`(443562, 443621)` confirmed at `1788161400000` — which production's own detector
emits 205 times.

The replay harness dropped it. The test-side model's POI identity omitted the
zone bounds, and reference zones have no source candles, so their
`(first, count, last)` triple collapses to the confirmation time; a second support
zone confirmed on the same candle claimed the identity first.

Pine never had the bug and its source had anticipated it: `f_poiSameIdentity`
compares tick-normalised bounds and says why in a comment. Fix `f4e12fe`, test
tooling only. No production, P1, P2, P3-Pine or P4 semantics changed, and since no
Pine source changed the captures did not need retaking.

M5 then went exact, and M15 revalidated on its frozen closure context to
registry 959 / active 156 / terminal 803, `H1 925825366` / `H2 836263421` —
the closure values unchanged.

Full diagnosis:
`artifacts/p3_parity/P3_M5_REFERENCE_ZONE_EXTENSION_1788272400000.txt`.

---

## 6. Also fixed before the first compile

`f_btmmSyncSetups` checked only the POI type, so H1/H4/D1 would each have built a
~900-setup registry. `analyze_btmm` skips any POI whose `source_timeframe` is
outside `formation | supporting_only` (`analyzer.py:400-416`), so production
creates none there. Found by reading the admission rule while writing the static
guards; runtime confirms 0 setups on all three (`c5e3913`).

---

## 7. Closure gates

| Gate | Result |
|---|---|
| `BTMM_TIMEFRAME_PARTITION_INVARIANT` | TRUE (`c296b9f`, 12 tests, whole-record, 6 seeds) |
| `P4_COMPLETE_ENGINE_SYNTHETIC_PARITY_ESTABLISHED` | TRUE (77 tests, every prefix, both modes) |
| `P4_COMPILE_HARD_PASS` | TRUE (0 errors, 0 warnings) |
| `P4_RUNTIME_HARD_PASS` | TRUE (72/72) |
| `P4_M15_NO_EVIDENCE_REAL_DATA_PARITY` | TRUE |
| `P4_M5_NO_EVIDENCE_REAL_DATA_PARITY` | TRUE |
| `P4_M1_NO_EVIDENCE_REAL_DATA_PARITY` | TRUE |
| `P4_NO_EVIDENCE_REAL_DATA_PARITY_ESTABLISHED` | TRUE |
| `P4_CORE_REAL_DATA_PARITY_ESTABLISHED` | **TRUE** |

`ENGINE_REACHABLE_COVERAGE` is complete over the **produced** vocabulary: 5/5
statuses, 15/15 transitions, 8/8 cancellations, 4/4 blocked reasons, 7/7
interaction classes, 3/3 reaction tiers, 3/3 speeds, 3/3 stages, 1/1 liquidity
location. Denominators come from
`test_btmm_vocabulary_reachability.py`, not from `len(Enum)` — production declares
more vocabulary than it assigns, and reporting "9 of 9 interaction classes" would
have been false.

`NO_EVIDENCE_RUNTIME_REACHABLE_COVERAGE` is the price-derived half in full (7/7
interactions, 3/3 reactions, 3/3 speeds, 3/3 stages, derived liquidity) and, by
construction, no confirmation and no blocked reason. That absence is asserted, so
it fails if it ever stops being true.

---

## 8. Resource and safety

P4 DEV: 4429 lines, `f35e6780…`. Atomic probe: 4680 lines, `cc5b90ed…`, asserted
to be DEV plus a logging appendix only.

`request.security` 0 · `request.security_lower_tf` 0 · `strategy.*` 0 (outside
comments). No orders, entries, sizing, stops, targets or trade management. No
push, no merge to `main`, no publication.

Suite at closure: **2617 passed**, `mypy src` clean.

---

## 9. Status

```
P1 MEASUREMENTS                     CLOSED
P2 STRUCTURE                        CLOSED
P3 POI CORE                         CLOSED  (+ M5 reference-zone extension verified)
P3 CONTEXT                          DEFERRED
P4 BTMM CORE                        CLOSED
P4 REVIEWED-EVIDENCE TRANSPORT      DEFERRED
P5 BTRC                             ARCHITECTURE NEXT
P6                                  NOT STARTED
```
