# BTRC-V1 — P2 Structure Architecture and Contract

Status: **PARTIALLY IMPLEMENTED.** §1–§13 are the original design; §14 is the
P2-I0 test-proven contract; §15–§19 record what has actually shipped.

Branch `pine-p2-structure`, cut from the frozen P1 checkpoint
`21502e182b729e8a7e365076c7defef2b3e90b3d`.

| phase | content | state |
|---|---|---|
| P2-I0 | contract hardening (tests only) | committed `0cac239` |
| P2-I1 / P2-I2 | structure codes, records, canonical swing adapter | committed `0df061f` |
| P2-I3 | relationship classification (§15) | committed `26bc64d` |
| P2-I4 | initial direction bootstrap (§16) | committed `5707034` |
| P2-I5-PRE | TD-A BOS protected-fallback contract (§17) | **TD-A RESOLVED** — author-accepted |
| P2-I5 | BOS (§18) | committed `8be961d` |
| P2-I6-PRE | TD-B weak re-arm contract (§19) | tests + docs, **uncommitted**, awaiting author review |
| P2-I6 | weak re-arm | **not started**; TD-B now CLOSED, so unblocked |
| P2-I7 | CHOCH | **not started** |

§1–§13 were written before implementation and are preserved as the design of
record; where a detail was refined by testing, §14–§19 are authoritative.

---

## 1. Scope

P2 ports the **validated Python market-structure engine** —
`src/btmm_ai_scanner/structure/` — onto Pine v6, consuming the P1 measurement
layer as its input.

### 1.1 In scope (because Python production implements it)

| concept | Python home |
|---|---|
| Swing relationship labels — HH / LH / EH / HL / LL / EL | `relationships.py` |
| Structure direction — UNDETERMINED / BULLISH / BEARISH | `enums.py` |
| Protected high / protected low | `transitions.py`, `current_state.py` |
| Weak high / weak low | `transitions.py`, `current_state.py` |
| BOS — BULLISH_BOS / BEARISH_BOS | `transitions.py` |
| CHOCH — BULLISH_CHOCH / BEARISH_CHOCH | `transitions.py` |
| Direction bootstrap from first agreeing relationship pair | `transitions.py` |
| Event-ordered, availability-keyed walk | `transitions.py` |
| Incremental replay equivalent to batch | `analyzer.py` |

### 1.2 Explicitly NOT in scope — absent from Python production

These are **NOT_IMPLEMENTED** and must not be added to P2 merely because they are
common in market-structure literature:

| concept | status |
|---|---|
| **RANGE / NEUTRAL structure state** | **NOT_IMPLEMENTED** — the only states are UNDETERMINED, BULLISH, BEARISH |
| **MSS (market structure shift)** | **NOT_IMPLEMENTED** — zero occurrences in `src/` |
| Internal vs external structure | NOT_IMPLEMENTED |
| Major vs minor swing tiers | NOT_IMPLEMENTED |
| Explicit structure-invalidation event | NOT_IMPLEMENTED (invalidation is implicit: a broken swing enters `broken_ids`) |
| Wick-based breaks | NOT_IMPLEMENTED — breaks are close-only |
| ATR tolerance on breaks | NOT_IMPLEMENTED — tolerance applies only to relationship labels |
| Multi-timeframe structure | NOT_IMPLEMENTED — deferred to P6 |

> **Audit note.** An initial concept sweep reported zero hits for CHOCH, HH and
> RANGE. That was a **tooling error**: the pattern used `\|` under `grep -E`,
> where `\|` matches a literal pipe rather than acting as alternation. Re-run
> with real ERE, BOS appears in 7 files and CHOCH in 6. Any future audit of this
> repository should verify its own regex dialect before concluding absence.

### 1.3 Hard non-scope

P3 POI, P4 BTMM, P5 BTRC, P6 MTF orchestration, and any entry / SL / TP / risk /
order logic. P2 adds **no** `request.security`.

---

## 2. Python contract — exact semantics

### 2.1 Relationship labels (`relationships.py`)

```
tolerance = 0.10 * current.pivot_reference_atr          # CURRENT swing's ATR
if current.pivot_price >  predecessor.pivot_price + tolerance -> HIGHER_HIGH / HIGHER_LOW
if current.pivot_price <  predecessor.pivot_price - tolerance -> LOWER_HIGH  / LOWER_LOW
otherwise                                                     -> EQUAL_HIGH  / EQUAL_LOW
```

Four properties that must be reproduced exactly:

1. The tolerance uses the **current** swing's `pivot_reference_atr` — not the
   predecessor's, not a median of the pair. It is therefore asymmetric.
2. The comparison is **strict** (`>`, `<`), so both tolerance edges fall into the
   EQUAL band.
3. Swings are grouped **by type first**, then compared to the immediate
   predecessor *within that type* (`group[index-1]`).

   **Refinement after direct testing.** `detect_swing_relationships` itself does
   not require alternation, but the public entry point does: `_validate_swings`
   raises `UnsortedSwingSequenceError` on *"confirmed_swings must alternate
   between SWING_HIGH and SWING_LOW in source chronology"*. Since P1's detector
   enforces the same alternation via its own gate, **the within-type predecessor
   is always exactly two positions back in source order** — a simplification Pine
   may rely on. An earlier draft of this document claimed two consecutive
   same-type swings could be compared directly; that is unreachable through the
   production API.
4. `availability_time_utc = max(current.availability, predecessor.availability)`.

The tolerance constant is `StructureConfiguration.
swing_relationship_equal_tolerance_atr_multiplier = 0.10`.

> **Correction to an earlier draft of this document**, which called the value
> "provisional, not architecture-approved". That was imprecise. Per
> `PHASE_1B_AUTHOR_DECISION_REGISTER.md` §34D/§34K the value is **AUTHOR-APPROVED
> by reuse**: it is "copied verbatim from 1B-H's approved
> `equal_level_tolerance_atr_multiplier` (same conceptual test — *are these two
> price points effectively equal*)", explicitly so that no new threshold is
> invented. `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` marks the milestone
> **AUTHOR-APPROVED**. The `ENGINEERING_PROVISIONAL` marker is the *evidence tier*
> carried on derived outputs — the same default every configuration in the repo
> uses, including the `MarketMeasurementConfiguration` that P1 already shipped on.
> Evidence tier and value approval are separate things.

### 2.2 Direction bootstrap

Only fires while `direction == UNDETERMINED`, and only on a RELATIONSHIP event:

```
if latest_high_label == HIGHER_HIGH and latest_low_label == HIGHER_LOW:
    direction      = BULLISH
    protected_low  = latest_low_swing
    weak_high      = latest_high_swing
elif latest_high_label == LOWER_HIGH and latest_low_label == LOWER_LOW:
    direction      = BEARISH
    protected_high = latest_high_swing
    weak_low       = latest_low_swing
```

`latest_*_label` is a per-type "most recent relationship seen so far" register, so
an EQUAL label on either side blocks the bootstrap until superseded. Direction is
never reset to UNDETERMINED once established.

### 2.3 Break semantics — close-only, no tolerance

Evaluated on every CANDLE event:

```
CHOCH candidates
  BEARISH and close > protected_high.pivot_price -> BULLISH_CHOCH
  BULLISH and close < protected_low.pivot_price  -> BEARISH_CHOCH

BOS candidates
  BULLISH and close > weak_high.pivot_price      -> BULLISH_BOS
  BEARISH and close < weak_low.pivot_price       -> BEARISH_BOS
```

| question | answer |
|---|---|
| wick or close? | **close** |
| intrabar? | no — closed candles only |
| ATR tolerance? | **none** |
| exact equality? | **not a break** — comparison is strict |
| CHOCH vs BOS precedence? | **CHOCH wins**; it is handled first and `continue`s past the BOS check |
| repeated firing? | prevented — the broken swing enters `broken_ids` and the weak side is cleared |

**CHOCH can abort.** If no unbroken opposite-side swing exists to become the new
protected level, the handler `continue`s: no transition, no state change — and
the BOS check for that candle is skipped too. Pine must reproduce this
abort-and-skip, not merely the happy path.

### 2.4 State updates

On **CHOCH** — direction flips; the broken swing is consumed; the new protected
level is `_most_recent_unbroken(opposite type)`; **both** weak levels clear; the
weak boundary index for the new direction is set to the break candle's index.

On **BOS** — direction unchanged; the broken weak swing is consumed; protected is
replaced by `_most_recent_unbroken(opposite type)` **falling back to the existing
protected level** if none is found; the weak side clears; its boundary index moves
to the break candle.

`_most_recent_unbroken` picks `max` by
`(pivot_bar_index, pivot_start_time_utc, str(record_id))` — fully deterministic,
no dictionary-ordering dependence.

### 2.5 Weak-level re-arming

On a SWING_VISIBLE event, a weak level re-arms only when **all** hold: the swing
type matches the direction (high↔BULLISH, low↔BEARISH); the weak slot is `None`;
`swing.pivot_bar_index > weak_boundary_index`; and the swing is not in
`broken_ids`. The boundary index is what prevents a pre-break swing from
immediately re-arming the level that was just broken.

---

## 3. Event timing and the non-repaint guarantee

`run_structure_walk` merges three event streams and sorts by
`(availability_time, kind, tiebreak)`:

| kind | ordinal | time key | tiebreak |
|---|---|---|---|
| CANDLE | 0 | `candle.availability_time_utc` | `(event_time_utc, record_id)` |
| SWING_VISIBLE | 1 | `swing.meaningful_confirmation_time_utc` | `(pivot_bar_index, pivot_start_time_utc, record_id)` |
| RELATIONSHIP | 2 | `relationship.availability_time_utc` | `(pivot_bar_index, record_id)` |

**This is already a no-look-ahead design**, and it is the single most important
property to preserve. A swing becomes visible to the structure walk at its
*meaningful confirmation* time, not at its pivot time — so structure can never
react to a pivot before the market confirmed it.

Verified: for a `ConfirmedSwing`, `availability_time_utc` is *assigned from*
`meaningful_confirmation_time_utc` (`domain/analyzer.py:318`), so the sort key and
the published availability are the same value. No skew.

**No future-data leakage was found.** Every event enters the timeline at the
moment its inputs were knowable.

Publication timestamps on a transition:
`event_time_utc` = break candle's event time;
`availability_time_utc` = `max(candle.availability, broken_swing.availability)`.

---

## 4. Dependency on P1 — what is reusable

| P2 requirement | P1 status |
|---|---|
| Confirmed meaningful swings (type, price, ordering) | **DIRECTLY_AVAILABLE** — `SwingRec` |
| `pivot_price` | **DIRECTLY_AVAILABLE** |
| `pivot_reference_atr` (relationship tolerance) | **DIRECTLY_AVAILABLE** — `SwingRec.referenceAtr` |
| `meaningfulConfTime` (visibility gate) | **DIRECTLY_AVAILABLE** |
| `pivotEndTime` / `pivotStartIdx` / `pivotEndIdx` | **DIRECTLY_AVAILABLE** |
| Candle close (break test) | **DIRECTLY_AVAILABLE** — `wClose` |
| Candle availability time | **DIRECTLY_AVAILABLE** — `wAvailT` |
| **Stable swing identity** (`broken_ids` membership) | **AVAILABLE_BUT_REQUIRES_METADATA_EXTENSION** |
| **`pivot_bar_index`** (absolute, for `_most_recent_unbroken` and boundary tests) | **AVAILABLE_BUT_REQUIRES_METADATA_EXTENSION** |
| Equal-level clusters, trendlines, S/R, displacement | **NOT REQUIRED** — structure does not consume them |

**Recomputation required: FALSE.** P2 must **not** build a second swing detector.
The Python structure engine consumes `ConfirmedSwing` from the same
`detect_confirmed_swings` that P1 already ports; a parallel detector would be a
second source of truth and is explicitly rejected.

### 4.1 The two missing pieces

`SwingRec` currently carries `pivotStartIdx` / `pivotEndIdx` as **window-relative**
indices and has no stable identity field.

1. **Stable identity.** Python uses `record_id` (UUID) for `broken_ids`. Pine has
   no UUIDs, but `pivotEndTime` is already documented in P1 as *"the stable
   semantic swing identity"* and is used exactly that way by `SRCand.key`. **Reuse
   `pivotEndTime` as the structure identity key.** No new field needed.
2. **Absolute bar index.** `_most_recent_unbroken` orders by `pivot_bar_index`, and
   weak re-arming compares against a boundary index. Window-relative indices shift
   as the window slides. `SRCand` already solves this with `pivotEndAbs`
   (*"ABSOLUTE pivot-end index, so a window shift cannot stale it"*). P2 needs the
   same on its swing view — derivable as `absFirst + pivotStartIdx` **without
   modifying `SwingRec`**.

Both are satisfiable in the P2 adapter layer. **No change to P1 production
records is required** — an important property, since P1 is frozen and pushed.

---

## 5. Incremental Pine model

Python already ships a **tested** incremental replay
(`_advance_structure_replay_state`, `_StructureWalkCheckpoint`,
`_build_sorted_structure_events`), proven equivalent to the batch walk by
`tests/unit/test_structure_batch_replay_equivalence.py`. **Pine should transcribe
that model rather than invent one** — the same discipline that made the P1 S/R
frontier defensible.

Proposed Pine state:

```
type StructRelRec                 // one relationship
    int   swingType
    int   label                   // HH / LH / EH / HL / LL / EL as int
    int   currentKey              // pivotEndTime
    int   predecessorKey
    float currentPrice
    float predecessorPrice
    int   availabilityTime

type StructEventRec               // an emitted BOS / CHOCH
    int   transitionType
    int   directionBefore
    int   directionAfter
    int   brokenKey
    float brokenLevelPrice
    float breakClosePrice
    int   protectedKey
    int   breakCandleTime
    int   availabilityTime

// scalar frontier
var int   structDirection        = DIR_UNDETERMINED
var int   protectedHighKey       = na
var int   protectedLowKey        = na
var int   weakHighKey            = na
var int   weakLowKey             = na
var int   weakHighBoundaryAbs    = -1
var int   weakLowBoundaryAbs     = -1
var array<int> brokenKeys                 // ascending, binary-searchable
var array<int> visibleHighKeys / visibleLowKeys
```

`brokenKeys` kept ascending allows the `broken_ids` membership test to be a binary
search rather than a linear scan — the same technique `f_srFind` already uses in
P1.

### 5.1 Closed-bar gating

P1's confirmed-bar contract is validated live and **P2 inherits it unchanged**:

| element | evaluate on forming bar | publish on forming bar |
|---|---|---|
| relationship labels | NO | NO |
| direction bootstrap | NO | NO |
| BOS / CHOCH detection | NO | NO |
| protected / weak levels | NO | NO |
| every `P2_*` output | NO | NO |

**Default and rule: no P2 output may change while a bar is forming.** The Python
contract supports this directly — breaks test `candle.close`, and a forming bar
has no final close. No exception is proposed.

---

## 6. History, capacity and pruning

**Does P2 require raising `calc_bars_count` above 1800? Proposed answer: NO.**

Structure consumes only swings and closes, both already inside P1's 300-bar
analytical window and 1800-bar execution horizon. It adds no new lookback.

The genuine risk is **unbounded accumulation**, not history depth. In the Python
batch walk, `visible_swings_by_type` is append-only and `broken_ids` is add-only,
with no pruning. That is safe in Python — the caller bounds the window — but a
naive Pine transcription would grow arrays without limit across a 1800-bar
execution.

Proposed bound, to be validated before implementation:

| array | bound | rationale |
|---|---|---|
| `visibleHighKeys` / `visibleLowKeys` | retirement below `absFirst + C_WINDOW_RADIUS` | mirrors `f_advancePivotFrontier`'s existing retirement rule |
| `brokenKeys` | retire alongside the swing it refers to | a key outside the window can never be re-broken |
| relationship records | one per swing per type; same retirement | |
| emitted events | ring buffer, size TBD by output contract | only the latest event is published |

**Worst-case swing density must be measured, not assumed.** P1's own performance
history is the cautionary precedent: the analytical cost was in per-bar rebuilds,
not in window size.

---

## 7. Performance risk table

| risk | severity | mitigation |
|---|---|---|
| `_most_recent_unbroken` is an O(n) scan per break | medium | maintain a per-type descending frontier; breaks are rare |
| `broken_ids` linear membership test | medium | ascending `brokenKeys` + binary search (as `f_srFind`) |
| Rebuilding the merged event list every bar | **high** | append-only timeline; only new events since last bar |
| Recomputing all relationships every bar | **high** | one new relationship per newly visible swing |
| Unbounded array growth | **high** | retirement rule in §6 |
| Extra plots pushing toward the 64 limit | medium | P1 uses 11; P2 budget in §8 keeps total ≤ 25 |
| Re-deriving swings independently | **critical** | forbidden — consume P1 canonical swings |

The three `high` items are all the same failure P1 hit: full rebuild per bar. The
architecture must be incremental from the first commit, not optimised later.

---

## 8. Output contract

| output | class |
|---|---|
| `P2_structure_direction` (0 undetermined / 1 bullish / −1 bearish) | PRODUCT |
| `P2_protected_high` / `P2_protected_low` | PRODUCT |
| `P2_weak_high` / `P2_weak_low` | PRODUCT |
| `P2_last_transition_type` | PRODUCT |
| `P2_last_transition_level` | PRODUCT |
| `P2_last_transition_time` | PARITY_DEBUG |
| `P2_last_high_label` / `P2_last_low_label` | PARITY_DEBUG |
| `P2_analyzed_swing_count` | PARITY_DEBUG |
| `brokenKeys`, boundary indices, event ring | INTERNAL |

Roughly 11 additional plots → ~22 total with P1's 11, comfortably under the 48
guard and the 64 hard limit. No UI, labels, lines or boxes are proposed at this
stage.

---

## 9. Parity methodology

Reuse the P1 infrastructure, with the feed lesson applied from the outset.

1. **Oracle** — extend the frozen July-2026 FXCM M15 dataset with a structure
   oracle CSV. Proposed columns: `timestamp_utc`, `bar_index`, `selected`,
   `csv_open/high/low/close`, `python_direction`, `python_protected_high`,
   `python_protected_low`, `python_weak_high`, `python_weak_low`,
   `python_last_transition_type`, `python_last_transition_level`,
   `python_last_transition_time`, `python_last_high_label`,
   `python_last_low_label`, `python_analyzed_swing_count`,
   `structure_event`, `oracle_state_description`.
   **Not generated in this task** — proposed for author approval first.
2. **High-value timestamps** — every BOS, every CHOCH, the bootstrap bar, the bar
   before and after each transition, and bars where a weak level re-arms.
3. **Comparison rules** — direction, labels and transition types compare
   **exactly** (they are enums). Prices compare **display-rounding-aware**, using
   the interval model P1 established. Timestamps compare exactly.
4. **Feed divergence must be assumed, not hoped away.** P1's entire parity effort
   turned out to be feed revision, and structure is *more* sensitive: a 0.10×ATR
   relationship tolerance and strict close comparisons mean one revised close can
   flip a label or fire a break. Every P2 mismatch investigation must begin by
   substituting measured current-TradingView values into production Python and
   re-running — the counterfactual-replay method, not inspection.

---

## 10. Test plan

### 10.1 Existing coverage

| area | tests | verdict |
|---|---|---|
| API validation, determinism, provenance | 10 | covered |
| Direction bootstrap (0/1/2/3 swings, bull, bear, contradictory, latest-non-equal) | 8 | **well covered** |
| Batch ↔ replay equivalence, record-id stability, fingerprints | 6 | **well covered** |
| Delta/event-identity reuse | 2 | covered |
| Configuration, exports | 10 | covered |

### 10.2 The gap

**There is no test anywhere for BOS or CHOCH.** Bootstrap is thoroughly tested;
the break machinery — the part P2 must port most carefully — is not. Missing:

| # | case | why |
|---|---|---|
| T1 | BULLISH_BOS fires on close above weak high | core path untested |
| T2 | BEARISH_BOS fires on close below weak low | core path untested |
| T3 | BULLISH_CHOCH flips BEARISH→BULLISH | core path untested |
| T4 | BEARISH_CHOCH flips BULLISH→BEARISH | core path untested |
| T5 | close **exactly equal** to the level → no break | strict comparison |
| T6 | wick through, close back inside → no break | close-only rule |
| T7 | CHOCH takes precedence when both candidates arm | ordering |
| T8 | CHOCH aborts when no unbroken opposite swing exists (and BOS is skipped) | the `continue` path |
| T9 | repeated break of the same swing suppressed | `broken_ids` |
| T10 | weak level does not re-arm from a pre-boundary swing | boundary index |
| T11 | weak level re-arms from a post-boundary swing | boundary index |
| T12 | BOS protected fallback when no replacement exists | fallback branch |
| T13 | `_most_recent_unbroken` tie-break ordering | determinism |
| T14 | relationship tolerance uses **current** swing's ATR | asymmetry |
| T15 | tolerance edges classify as EQUAL (both sides) | strictness |
| T16 | two consecutive same-type swings compare directly | no alternation requirement |

**These should be written against Python before any Pine is written** — they
define the contract Pine will be held to, and they close a real gap in the
existing suite regardless of P2.

### 10.3 Synthetic fixture matrix

Follow the established pattern (`_candle` / `_swing` helpers, ~20-bar ATR warm-up,
explicit `reference_atr`), deriving expected values from production formulas
rather than hardcoding them.

| fixture | swing sequence | exercises |
|---|---|---|
| F1 | L→H→L→H rising | bootstrap BULLISH |
| F2 | H→L→H→L falling | bootstrap BEARISH |
| F3 | rising then equal high | EQUAL blocks bootstrap |
| F4 | F1 + close above weak high | T1 |
| F5 | F1 + close exactly at weak high | T5 |
| F6 | F1 + wick above, close below | T6 |
| F7 | F1 + close below protected low | T3/T4 |
| F8 | F7 with no unbroken opposite swing | T8 |
| F9 | F4 + second close above same level | T9 |
| F10 | F4 + new high before/after boundary | T10/T11 |
| F11 | two consecutive highs, no intervening low | T16 |
| F12 | prefix-growing replay of F1–F11 | batch ↔ incremental |

---

## 11. Known unknowns

1. Worst-case swing density over 1800 bars — measured, not assumed, before array
   bounds are fixed.
2. Whether retiring a swing that is still the active protected level can occur,
   and what the correct Pine behaviour is (Python never retires).
3. Whether the frozen July-2026 window contains enough BOS/CHOCH events to be a
   useful parity target, or whether a second window is needed.
4. Whether the `0.10` relationship tolerance stays `ENGINEERING_PROVISIONAL` or
   gets promoted before P2 ships.

---

## 12. Implementation plan

Each phase ends at a stop condition; none may be skipped.

| phase | deliverable | acceptance | stop condition |
|---|---|---|---|
| **P2-I0** | Python BOS/CHOCH tests T1–T16 + fixtures F1–F12 | all pass against unmodified Python | any test reveals a Python defect → STOP, report |
| **P2-I1** | Pine records + enums (`StructRelRec`, `StructEventRec`, direction/label/transition ints) | compiles; no behaviour | — |
| **P2-I2** | Swing adapter: P1 `SwingRec` → structure view with `pivotEndTime` identity and absolute index | adapter unit-tested; **P1 records unchanged** | any need to modify `SwingRec` → STOP, re-architect |
| **P2-I3** | Relationship classification | matches Python on F1–F3, F11 | label mismatch → STOP |
| **P2-I4** | Direction bootstrap | matches Python on F1–F3 | — |
| **P2-I5** | Break detection (BOS + CHOCH, precedence, abort path) | matches Python on F4–F9 | — |
| **P2-I6** | Weak re-arm + boundary indices | matches F10 | — |
| **P2-I7** | Incremental frontier + bounded retirement | batch ↔ incremental identical on F12 | any divergence → STOP |
| **P2-I8** | Parity outputs (§8) | plot budget ≤ 25 | budget exceeded → split the probe |
| **P2-I9** | Structure oracle + Python↔Pine parity run | documented per-field result | unexplained mismatch → counterfactual replay before any Pine change |
| **P2-I10** | Live closed-bar gate for P2 outputs | all frozen on forming bars | any forming-bar change → STOP |

**Recommended first task: P2-I0.** It is pure Python test authoring against
frozen production, it closes a real existing coverage gap, and it is the only
phase that can still discover a contract problem cheaply — before any Pine
exists.

---

## 13. Stop conditions (whole phase)

- Any change to P1 production Pine or to `src/`.
- Any Python defect discovered in the structure engine.
- Any need for a second swing detector.
- Any output that cannot be frozen on a forming bar.
- Any requirement to raise `calc_bars_count` above 1800.
- Any drift into P3+ scope.

---

## 14. P2-I0 — TEST-PROVEN CONTRACT

Everything above §14 is **SOURCE-DERIVED CONTRACT**. This section is
**TEST-PROVEN CONTRACT**: each statement is now asserted by a permanent test in
`tests/unit/test_structure_transitions_contract.py` (50 tests) against
**unmodified** production Python.

Before P2-I0 the structure suite had **zero direct BOS or CHOCH tests**.

### 14.1 BOS — proven

| behaviour | proof |
|---|---|
| close strictly above weak high → `BULLISH_BOS` | `test_bos_b1_*` |
| close **exactly equal** to weak high → **no break** | `test_bos_b2_*` |
| wick above, close below → no break | `test_bos_b3_*` |
| open/high above, close not above → no break | `test_bos_b4_*` |
| break consumes the weak swing | `test_bos_b5_*` |
| same swing cannot break twice | `test_bos_b6_*`, `test_bos_r6_*` |
| protected replaced by most-recent-unbroken opposite | `test_bos_b7_*`, `test_bos_r7_*` |
| direction does **not** flip on BOS | asserted in b1 / r1 |
| bearish mirror of all of the above | `test_bos_r1..r7` |

### 14.2 CHOCH — proven

| behaviour | proof |
|---|---|
| BULLISH + close below protected low → `BEARISH_CHOCH`, flips to BEARISH | `test_choch_c1_*` |
| BEARISH + close above protected high → `BULLISH_CHOCH`, flips to BULLISH | `test_choch_c2_*` |
| close exactly at protected level → no CHOCH (both directions) | `test_choch_c3_*` |
| wick through, close back → no CHOCH (both directions) | `test_choch_c4_*` |
| CHOCH clears **both** weak levels | `test_choch_c5_*` |
| direction flips exactly once per break | `test_choch_c6_*` |
| opposite-side replacement chosen correctly | `test_choch_c7_*` |
| consumed level cannot re-emit | `test_choch_c10_*` |
| **CHOCH takes precedence over BOS on the same candle** | `test_choch_precedence_*` |

The precedence test needs a weak high placed *below* the protected low — the only
configuration where one close satisfies both predicates. Unnatural, but the
contract imposes no ordering on those levels, and inverted precedence is a
realistic Pine transcription error.

### 14.3 The CHOCH abort path — REACHABLE, and now pinned

The abort was the biggest transcription hazard, and it is **not dead code**. It
requires a chain of CHOCHs that consumes *every* swing on one side:

```
bootstrap BEARISH   protected_high = H2 108, weak_low = L2 98
bar 10  close 109 > 108  -> BULLISH_CHOCH   breaks H2, protected_low = L2  98
bar 12  close  97 <  98  -> BEARISH_CHOCH   breaks L2, protected_high = H1 110
bar 14  close 111 > 110  -> BULLISH_CHOCH   breaks H1, protected_low = L1 100
bar 16  close  99 < 100  -> candidate TRUE, but H1 and H2 are both consumed
                         -> ABORT: no transition, no mutation, BOS skipped
```

Verified non-vacuous: at bar 16 the CHOCH predicate is `99 < 100 = True`, yet only
three transitions are emitted. `test_choch_chain_emits_exactly_three_transitions_then_aborts`
and `test_choch_abort_leaves_state_completely_unmutated` pin this.

The abort `continue` sits at L190/L224, **before** `broken_ids.add` at L191/L225 —
so on abort nothing mutates. Pine must place its guard in the same position.

### 14.4 Relationship tolerance — boundaries and ATR asymmetry proven

With `tol = 0.10 × current ATR = 0.20`:

| delta from predecessor | label |
|---|---|
| +0.21 | HIGHER_HIGH |
| **+0.20 (exactly +tol)** | **EQUAL_HIGH** |
| 0.00 | EQUAL_HIGH |
| **−0.20 (exactly −tol)** | **EQUAL_HIGH** |
| −0.21 | LOWER_HIGH |

The fixture gives the predecessor ATR `50.0` (band ±5.00) and the current ATR
`2.0` (band ±0.20). A +0.21 delta is outside the current band but deep inside the
predecessor band, so `HIGHER_HIGH` can only arise if the **current** swing's ATR
is used. A median or predecessor-ATR implementation fails the test.

### 14.5 Event timing — proven

`transition.event_time_utc` = break candle's event time;
`availability_time_utc` = `max(candle.availability, broken_swing.availability)`.
The test additionally asserts those two inputs **differ**, so equality cannot mask
a wrong choice. A separate test places a would-be break *before* the weak swing's
confirmation and asserts nothing fires — the visibility gate.

### 14.6 Batch ↔ incremental and randomized campaign

Nine named break scenarios (bullish/bearish BOS, bullish/bearish CHOCH, abort
chain, repeat-suppressed, equal-no-break, bootstrap-then-BOS,
bootstrap-then-CHOCH) are replayed over **every growing prefix**, asserting
identical direction, transition sequence and content fingerprint, and that the
transition count is **monotonic** — a transition once emitted is never retracted.

Deterministic campaign, 6 fixed seeds covering all three structural modes
(bull / bear / equal) twice each:

```
seeds 6   prefix comparisons 144   transitions 8   mismatches 0
directions seen : BEARISH, BULLISH, UNDETERMINED
kinds seen      : BULLISH_BOS, BEARISH_BOS, BULLISH_CHOCH, BEARISH_CHOCH
```

Both EQUAL-mode seeds correctly remain `UNDETERMINED`, which independently
confirms the tolerance band blocks bootstrap. A diversity guard fails the suite if
the campaign ever degenerates below 3 directions and 3 transition kinds — the
first version of this campaign *did* degenerate (4 of 6 seeds hit one mode), which
is why the guard exists.

### 14.7 Tolerance decision — ENGINEERING DECISION

**Recommendation: B — keep `0.10` and port it exactly for parity.**

- The value is **author-approved by reuse** from 1B-H (§2.1), not an unreviewed
  invention.
- It is **not serialized** onto `SwingRelationship` outputs — only its *effect*
  (the label) is recorded. Changing it silently rewrites historical labels with no
  trace in the output, so it should not be changed casually.
- `test_structure_configuration.py` already locks it at `0.10`, and the model is
  frozen.
- Changing it now would alter bootstrap, all six labels, and therefore BOS/CHOCH
  indirectly — invalidating any P2 parity baseline built beforehand.

Option A (promote to frozen) is defensible but unnecessary for P2 and would be a
contract change during a port. Option C (block) is not warranted — nothing about
the value is ambiguous. **Whatever its provenance tier, P2 must reproduce current
production semantics exactly**; that is the porting obligation, independent of
whether the constant is later revisited.

### 14.8 Python defect audit — result

**No production defect found.** Specifically checked and cleared: CHOCH abort
skipping a legitimate BOS (correct per contract — the `continue` is deliberate),
protected fallback selecting an already-broken swing (cannot: the fallback is the
current protected level, which is unbroken by construction in its own direction),
weak level not clearing, boundary-index off-by-one, availability earlier than
required, double consumption of one swing, unstable tie ordering, float equality
(no floats — Decimal throughout), and timezone handling (explicit UTC).

No production Python or Pine was modified.

### 14.9 Implementation readiness

**READY FOR P2-I1.** The remaining ambiguity that mattered — the abort path, the
precedence order, the equality boundaries, and which ATR feeds the tolerance — is
now pinned by tests rather than by reading. Two design refinements came out of the
testing and are recorded above: alternation is an input requirement (§2.1), and
the tolerance's approval status was mis-stated in the first draft (§2.1).

Verification at P2-I0 close: new contract file **50 tests**, all structure tests
**136**, full suite **1501 passed / 0 failed**. Production Python and Pine
unchanged (`git diff -- src/` and `git diff -- tradingview/` both empty).

### 14.10 CARRIED-FORWARD TEST DEBT — must not be lost

Two production branches are exercised only indirectly by P2-I0. Each is a
**hard gate on the implementation phase that would rely on it**:

| # | branch | blocks | status |
|---|---|---|---|
| **TD-A** | BOS protected-fallback **TAKEN** branch (`_most_recent_unbroken` returns `None`, so the existing protected level is retained) | ~~P2-I5 (BOS) may not be accepted until this is directly tested~~ — superseded, see §17.7 | **RESOLVED (§17)** |
| **TD-B** | Explicit weak-re-arm-after-boundary fixture (a new same-type swing with `pivot_bar_index > boundary` re-arms the cleared weak level) | ~~P2-I6 may not be accepted until this is directly tested~~ — satisfied, see §19 | **CLOSED / TEST-PROVEN (§19)** |

**Correction.** This section originally asserted that *both* debts "are reachable
by the same swing-exhaustion pattern that made the CHOCH abort constructible
(§14.3)". For TD-A that claim is **wrong**, and §17 gives the proof: the
swing-exhaustion pattern cannot reach the BOS fallback, because exhausting the
protected side necessarily flips the direction. TD-B is unaffected: it is
genuinely reachable, and it was reached and closed at P2-I6-PRE (§19).

---

## 15. P2-I1 / P2-I2 / P2-I3 — DELIVERED

### 15.1 What shipped

| phase | content | commit |
|---|---|---|
| **P2-I1** | Structure enum codes (`C_ST_DIR_*`, `C_ST_REL_*`, `C_ST_TR_*`, `C_ST_NA`) and records (`StructSwingView`, `StructRelRec`, `StructEventRec`), declarations only | `0df061f` |
| **P2-I2** | `f_p2BuildSwingView` — canonical adapter from P1's confirmed `SwingRec` list | `0df061f` |
| **P2-I3** | `C_ST_REL_EQUAL_TOL_ATR`, `f_p2ClassifyRelationship`, `f_p2BuildRelationships`, 3 debug diagnostics | (this section) |

I3 introduces **no** bootstrap, direction mutation, protected/weak state, BOS,
CHOCH or `StructEventRec` construction. It emits labels and nothing else.

### 15.2 Relationship semantics as implemented

```
tol   = 0.10 x CURRENT swing referenceAtr      (relationships.py:59-61)
delta > +tol  ->  HIGHER      (strict, :63)
delta < -tol  ->  LOWER       (strict, :69)
otherwise     ->  EQUAL       (:74)
availability  =  max(current.meaningfulConfTime, previous.meaningfulConfTime)   (:95)
predecessor   =  previous swing OF THE SAME TYPE
```

Both comparisons are **strict**, so a delta of exactly `+tol` or exactly `-tol`
lands in the EQUAL band. The tolerance is scaled by the **current** swing's ATR —
not the predecessor's, not a median, not the bar ATR. That asymmetry is
observable and is pinned by test.

### 15.3 NON-OBVIOUS FACT 1 — API ORDER IS NOT EVENT CHRONOLOGY

`detect_swing_relationships` filters `highs` first, then `lows`, and appends in
that order (`relationships.py:86-91`). Its **returned candidate tuple** is
therefore:

> **ALL HIGH relationships, followed by ALL LOW relationships.**

This is **Python API/output ordering**. It is emphatically **NOT** structure-event
chronology. A LOW relationship can become available strictly *earlier* in time
than a HIGH relationship that precedes it in the tuple.

Neither consumer reads that order as chronology, and neither publishes it:

* `run_structure_walk` re-sorts every event by `(availability_time, kind,
  tiebreak)` (`transitions.py:135`);
* `analyze_structure_state` re-sorts for publication by `(pivot_bar_index,
  pivot_start_time_utc, record_id)` (`analyzer.py:346-353`), so
  `StructureAnalysis.swing_relationships` is chronological, **not**
  highs-then-lows.

So the highs-then-lows order is an internal serialization artifact that reaches no
consumer in that form. **Any phase that consumes relationships as a time-ordered
event stream must re-sort under the merged event key — never iterate the raw tuple
and call it chronology.** `f_p2BuildRelationships` reproduces the raw order
because that is the function it is porting; P2-I4 sorts before walking (§16.2).

### 15.4 NON-OBVIOUS FACT 2 — LEFT-EDGE SEMANTICS

Relationships are derived **only** from the bounded canonical P1 swing view.

Python classifies exactly the bounded input it is handed. When P1's window
advances and the oldest same-type swing drops out of `views`, the new first swing
of that type has no predecessor and yields **no relationship** — precisely what
Python returns for the same bounded input.

**Pine must not secretly remember a predecessor that has left the bounded input.**
Retaining one would produce a relationship Python does not produce, and would
diverge silently and permanently. `f_p2BuildRelationships` holds no persistent
state: the output array is rebuilt from `views` on every confirmed bar and
discarded. This is a hard invariant, guarded by test.

### 15.5 I3 proof

| measure | value |
|---|---|
| deterministic seeds | 8 |
| prefix comparisons | 56 |
| relationships compared | 32 |
| relationship labels reached | **6 / 6** (HH, LH, EH, HL, LL, EL) |
| mismatches | **0** |
| Pine foundation guards | 45 passed |
| relationship parity tests | 32 passed |
| full suite | **1578 passed / 0 failed** |
| plot consumers | 20 / 64 |

Parity method: a test-side transcription of the Pine algorithm is compared
against **production** `detect_swing_relationships` on every case, asserting
relationship code, current swing identity, predecessor identity **and**
availability — production is always the reference side.

### 15.6 Test debt

Neither TD-A nor TD-B is touched by I1, I2 or I3. Both were discharged later:
TD-A **RESOLVED** at P2-I5-PRE (§17), TD-B **CLOSED** at P2-I6-PRE (§19).

---

## 16. P2-I4 — INITIAL DIRECTION BOOTSTRAP (delivered, uncommitted)

### 16.1 Scope

`UNDETERMINED -> BULLISH | BEARISH`, once only, plus the initial protected/weak
references Python assigns at that moment. **No BOS, no CHOCH, no
`StructEventRec`, no broken-level bookkeeping, no weak re-arm.**

### 16.2 Source contract — exact

| element | location |
|---|---|
| merged event key | `transitions.py:99-135` |
| relationship sub-key | `transitions.py:122-133` |
| bootstrap branch | `transitions.py:355-381` |
| direction/protected/weak publication | `analyzer.py:418-436` |

```
on RELATIONSHIP event r (walked in merged order):
    latest_label[r.swing_type] = r.label            # UNCONDITIONAL (:358)
    latest_swing[r.swing_type] = r.current_swing    # UNCONDITIONAL (:359-361)
    if direction == UNDETERMINED:                                   # (:363)
        if latest_label[HIGH] == HIGHER_HIGH and latest_label[LOW] == HIGHER_LOW:
            direction      = BULLISH                                # (:366-373)
            protected_low  = latest_swing[LOW]
            weak_high      = latest_swing[HIGH]
        elif latest_label[HIGH] == LOWER_HIGH and latest_label[LOW] == LOWER_LOW:
            direction      = BEARISH                                # (:374-381)
            protected_high = latest_swing[HIGH]
            weak_low       = latest_swing[LOW]
        last_change_availability = r.availability_time_utc
```

Answers to the questions the phase brief required be derived, not assumed:

| question | answer |
|---|---|
| latest relationship per side? | **Yes** — unconditional dict overwrite |
| does EQUAL replace prior directional evidence? | **Yes**, and therefore blocks bootstrap |
| does later contradictory evidence replace earlier? | **Yes** — same overwrite |
| which event triggers bootstrap? | the relationship event that **completes** a qualifying pair, either side |
| protected/weak assigned | BULL: `protected_low`, `weak_high`. BEAR: `protected_high`, `weak_low`. The opposite two stay unset |
| does bootstrap emit a transition? | **NO** — `transitions.append` is absent from the branch |
| once-only? | **Yes** — the `UNDETERMINED` guard; flips are CHOCH (I5+) |

The swing that becomes protected/weak is the latest relationship's **current**
swing for that side, which may originate in an *earlier* event than the one that
triggers the bootstrap. `last_change_availability` is the **triggering** event's
own availability, not a max of the two contributing relationships.

### 16.3 EVENT CHRONOLOGY — the highest-risk detail

Restricted to relationships (all share `kind = _EVENT_RELATIONSHIP`), Python's key
is:

```
(availability_time_utc, current_swing.pivot_bar_index, str(current_swing_record_id))
```

**The `record_id` leg is unreachable in production.**
`_find_single_candle_pivots` emits at most one pivot per candle index and skips
any index qualifying as both a high and a low (`swings.py:112-114`), so
`pivot_bar_index` is unique across confirmed swings and
`(availability, pivot_bar_index)` is already a **total** order. Pine reproduces it
exactly with `(availabilityTime, currentPivotStartAbs)` — no UUID surrogate is
needed, and none was invented. `_validate_swings` would *permit* a synthetic tie
across types, so this is pinned by test rather than assumed.

`StructRelRec` gained one field, `currentPivotStartAbs`, purely to carry that
ordering key; it is the exact Python tiebreak component.

### 16.4 Implementation

| helper | role |
|---|---|
| `f_p2RelIsHigh` | side of the book from the relationship code |
| `f_p2OrderRelationships` | stable insertion sort on `(availabilityTime, currentPivotStartAbs)` |
| `f_p2BootstrapWalk` | the `_EVENT_RELATIONSHIP` branch, returning a 6-tuple |

**Bounded and batch-equivalent.** All three are pure functions over the bounded
live relationship list, rebuilt on every confirmed bar and discarded. No `var`, no
1800-bar traversal, no unbounded accumulation, and no candle access — the walk
inherits P1's confirmed-bar gate through its inputs. I4 is deliberately **not**
the incremental frontier engine; that remains P2-I7.

### 16.5 Left-edge semantics

If the evidence that produced a bootstrap leaves the bounded input, the direction
returns to `UNDETERMINED` — exactly what Python yields for the same bounded input.
Pine retains no predecessor, no label and no direction behind P1's window.

### 16.6 I4 proof

| measure | value |
|---|---|
| deterministic campaign scenarios | 16 |
| prefix comparisons | 90 |
| bullish / bearish / undetermined outcomes | 6 / 4 / 6 (pinned exactly) |
| relationship labels reached | 6 / 6 |
| mismatches | **0** |
| transitions fired anywhere in the campaign | **0** |
| I4 parity tests | 59 passed |
| Pine foundation guards | 53 passed |
| plot consumers | 23 / 64 (target was ≤ 24) |

Parity compares the **full** state — direction plus all four protected/weak
identities — against production `analyze_structure_state`, never direction alone,
and at **every prefix**, so bootstrap *timing* is validated and not just the final
answer.

Two guard-the-guard tests prove the fixtures actually discriminate:
`test_api_order_model_would_have_diverged_*` shows an implementation that walks
the highs-then-lows tuple reaches the **opposite** direction on those fixtures, and
`test_swapping_the_tied_pair_would_change_the_direction` shows the
`pivot_bar_index` tiebreak is load-bearing.

### 16.7 Diagnostics

Five slots added (`P2_direction`, `P2_protected_high`, `P2_protected_low`,
`P2_weak_high`, `P2_weak_low`); two superseded adapter echoes retired
(`P2_last_swing_price`, `P2_last_swing_atr` — both pure restatements of the I2
adapter, which is contract-tested). Net 20 -> 23, under the ≤ 24 target with
headroom for I5. All P2 diagnostics remain `debugMode`-gated and
`display.data_window` only; P1's nine outputs are untouched and un-gated.

### 16.8 Test debt

I4 touches neither debt. TD-A was resolved at P2-I5-PRE (§17) and TD-B was
closed at P2-I6-PRE (§19).

---

## 17. P2-I5-PRE / TD-A — BOS PROTECTED-FALLBACK

Test file: `tests/unit/test_structure_bos_fallback_contract.py` (36 tests).

### 17.1 Result — TD-A RESOLVED (author-accepted)

> **TD-A RESOLVED — BOS protected-fallback branch proven unreachable through
> valid production state; defensive fallback semantics test-pinned in both
> directions.**

The original acceptance criterion — *"TD-A closes only if natural production
execution reaches `replacement == None`"* — is **superseded**, because the
investigation proved that state is impossible under the validated production
invariant. The branch is dead code; specifically, it is *defensive* code, and
P2-I5 reproduces it deliberately (§17.5a).

| criterion (from the phase brief) | outcome |
|---|---|
| direction established, BOS predicate true, weak level valid, BOS emits | **YES** |
| replacement selection is called | **YES** |
| `_most_recent_unbroken` returns `None` | **NO — provably impossible** |
| fallback branch taken | **NO** in production; **YES** under injection |
| existing protected reference retained | **YES** (pinned under injection) |
| broken weak level consumed | **YES** (pinned on both paths) |

### 17.2 Why the branch is unreachable

The invariant is: **while `direction == BULLISH`, `protected_low` is always
visible and always unbroken** (and its bearish mirror). Since
`_most_recent_unbroken` filters only on `broken_ids`, the protected swing is
always at least one eligible candidate, so `None` is impossible.

The invariant holds because of four independent source facts:

1. **Bootstrap runs with `broken_ids` empty.** `broken_ids` only gains entries
   inside CHOCH/BOS handlers, which require a direction; bootstrap only runs while
   `UNDETERMINED`, and direction never returns to `UNDETERMINED`.
2. **A CHOCH that consumes `protected_low` flips the direction in the same step**
   and sets `protected_low = None` (`transitions.py:246-248`). There is no state
   in which a BULLISH direction survives its protected low being broken.
3. **An aborting CHOCH consumes nothing.** The `continue` precedes
   `broken_ids.add` (`:189-191`, `:223-225`), so a failed CHOCH leaves the
   protected level unbroken. *This is the load-bearing detail* — pinned by
   `test_choch_abort_precedes_broken_ids_add`. Reversing that order would make the
   fallback live and reopen TD-A.
4. **A BULLISH BOS consumes a HIGH but searches the LOWS** (`:260-264`), so the
   BOS cannot empty the candidate set it is about to query.

Empirical confirmation: a deterministic sweep of 398 seeds producing **≥ 350
productive walks and ≥ 900 replacement searches**, covering all four transition
types, records a **minimum eligible-candidate count of exactly 1 — never 0**.
The test asserts the minimum is exactly 1, so the sweep also fails if it drifts
away from the boundary and stops being evidence.

The adversarial construction is spelled out in
`test_exhausting_the_lows_flips_direction_instead_of_emptying_the_set`: breaking
the protected low requires a BEARISH CHOCH, which flips to BEARISH and clears it.

### 17.3 The vacuity trap, made explicit

`test_unchanged_protected_id_does_not_imply_fallback` builds a real BULLISH BOS
in which the protected low is **identical before and after** — yet the fallback
was not taken; the search simply found two candidates and re-selected the same
swing. Any TD-A fixture that asserted only "protected id unchanged" would have
passed this and proved nothing. Every assertion in the file therefore also checks
the eligible-candidate set.

### 17.4 Fallback semantics — pinned by injection

`_most_recent_unbroken` is replaced with a stub returning `None` to execute the
defensive expression. This is a deliberate coupling to a private helper, justified
because public state cannot reach the branch; the tests make no reachability
claim.

Both directions are covered and both are **discriminating**: unpatched, the
fixture selects a strictly newer swing (bar 10); patched, it must retain the
pre-BOS protected swing (bar 6). Mutating the production fallback to any other
swing fails both tests.

| under injection | bullish | bearish |
|---|---|---|
| transition still emitted | BULLISH_BOS | BEARISH_BOS |
| `protected_swing_id` | pre-BOS `protected_low` | pre-BOS `protected_high` |
| direction | unchanged BULLISH | unchanged BEARISH |
| broken weak level | consumed (no repeat break) | consumed |

### 17.5 Everything else P2-I5 needs, pinned from reachable state

| element | pinned by |
|---|---|
| BOS predicates, close-only and strict | §14.1 (P2-I0) |
| CHOCH precedence over BOS | §14.2 (P2-I0) |
| replacement key `max(pivot_bar_index, pivot_start_time_utc, str(record_id))` | `test_most_recent_unbroken_key_is_pinned_to_source` |
| newest of several eligible candidates wins | `test_replacement_picks_the_newest_of_several_eligible_candidates` |
| broken candidates are excluded | `test_replacement_skips_broken_candidates` |
| only the BOS's own weak side clears | `test_bos_clears_only_its_own_weak_side` |
| no re-arm inside the BOS handler | `test_bos_does_not_re_arm_the_weak_side_in_its_own_branch` |
| boundary index = break candle index; re-arm gate is `>` | `test_bos_sets_the_weak_boundary_to_the_break_candle_index` |
| transition field values | `test_bos_transition_fields_match_the_break` |
| `availability = max(candle, broken_swing)` | `test_bos_timing_is_the_later_of_candle_and_broken_swing` |
| repeat break suppressed | `test_repeat_break_of_the_same_level_emits_no_second_transition` |
| batch ↔ incremental equivalence | `test_batch_equals_incremental_replay`, `test_replay_totals` |

**A second defensive `max` identified.** BOS availability is
`max(candle.availability, broken_swing.availability)`, but the candle side
**always wins**: a weak level must already be armed for a BOS to fire, so its
availability necessarily precedes the break candle's. The two operands genuinely
differ in the fixture, so the `max` is exercised rather than trivially equal, but
Pine may implement it as either the max or the candle time without divergence.

### 17.5a AUTHOR POLICY — Pine must keep the fallback

Pine I5 **MUST** reproduce the Python fallback defensively even though it is
currently unreachable:

```
replacement = most recent eligible unbroken opposite-side swing
protected   = replacement if replacement exists else existing protected
```

It must **not** be optimised away, and production Pine must **not** carry a
runtime assertion asserting `replacement` can never be absent — the invariant
belongs in tests and in this document, not in the indicator. Rationale:
structural parity with Python, negligible cost, and protection against a future
change to the invariant (see §17.2 fact 3, the load-bearing detail).

### 17.6 Remaining ambiguity for P2-I5

**None.** Every BOS element above is pinned by test, and the fallback policy is
settled by §17.5a.

### 17.7 Status

**TD-A is RESOLVED.** The author accepted the unreachability proof plus the
injected-semantics coverage in place of a natural taken-branch fixture, and
superseded the original criterion. TD-A no longer gates P2-I5.

Accepted evidence: 377 productive walks, 1,096 replacement searches, minimum
eligible replacement count exactly 1, zero natural `replacement == None` cases,
both directional fallback branches exercised by controlled injection,
discriminating mutation tests proving the fallback target matters, and 360
batch/incremental prefix comparisons with 0 mismatch.

**TD-B was OPEN at the time of this section and is now CLOSED — see §19.** It is
genuinely reachable, it was reached, and it never gated P2-I5.

---

## 18. P2-I5 — BOS (delivered, uncommitted)

Test file: `tests/unit/test_p2_bos_parity.py` (51 tests).
**Scope: BOS only.** No CHOCH emission, no direction flip, no weak re-arm.

### 18.1 The merged walk

I4's relationship-only walk is replaced by `f_p2StructureWalk`, a single pass over
the merged event stream, transcribing `run_structure_walk` for the subset
implemented so far:

| event | kind | handled |
|---|---|---|
| CANDLE | 0 | **I5** — BOS predicate, suppression guard, break handling |
| SWING_VISIBLE | 1 | **I5** — registers the replacement candidate. **No weak re-arm** (I6) |
| RELATIONSHIP | 2 | **I4** — direction bootstrap, unchanged |

Each stream is already sorted on its own key — candles chronologically by
construction, swings by `f_p2OrderSwings`, relationships by
`f_p2OrderRelationships` — so this is a **linear 3-way cursor merge**, not a sort
of the combined list. Ties in availability fall to the lower `kind` because the
streams are tested in kind order and only a **strictly** earlier time displaces
the incumbent.

### 18.2 CHOCH PRECEDENCE — the phase-safety problem, and why the guard is exact

Python evaluates CHOCH **before** BOS. An I5-only engine could therefore emit a
BOS on a candle that production Python classifies as CHOCH.

The resolution is exact rather than approximate. Python continues past the BOS
block on **both** CHOCH exits — the successful one (`transitions.py:253`) and the
aborting one (`:190`/`:224`). So the rule governing BOS emission is precisely:

> **CHOCH predicate true implies no BOS on this candle.**

That holds regardless of whether the CHOCH would have succeeded, what it would
have selected, or what it would have mutated. It is a pure price test over state
I5 already tracks, so the guard reproduces Python's **BOS decisions exactly**.

```
if direction == BEARISH and protected_high and close > protected_high.price -> suppress
if direction == BULLISH and protected_low  and close < protected_low.price  -> suppress
```

**This is BOS SUPPRESSION ONLY — it is NOT a CHOCH implementation.** It creates no
transition, flips no direction, consumes no swing and mutates no state; the walk
simply does nothing on such a candle. That is *incomplete* relative to Python
(Python would have emitted a CHOCH and mutated state) but never *wrong about BOS*.
The distinction is enforced by `test_choch_guard_is_suppression_only`, which
asserts the guard writes only its own boolean and the suppression path mutates
only a counter.

**When a candle can satisfy both predicates.** It requires the protected level on
the far side of the weak level — e.g. BULLISH with `protected_low > weak_high`.
`test_the_precedence_fixture_really_satisfies_both_predicates` proves the fixture
fires both, and `test_without_the_guard_a_false_bos_would_be_emitted` proves the
guard is load-bearing by running the same walk with it removed. The fixture is
geometrically extreme (a swing low above a swing high); real adjacent OHLC pivots
would not produce it, but `_validate_swings` accepts it and it isolates the
precedence question. **The guard is justified by Python's control flow, not by
that fixture's realism.**

### 18.3 BOS contract as implemented

```
predicate   BULLISH and close > weak_high.price   -> BULLISH_BOS     (strict, close-only)
            BEARISH and close < weak_low.price    -> BEARISH_BOS
consume     broken_keys += broken weak swing      (BEFORE the replacement search)
replace     protected = most_recent_unbroken(opposite side)
            ... or the EXISTING protected level if none (defensive, 17.5a)
clear       only the BOS's own weak side; the boundary index := break candle index
direction   unchanged
timing      event_time = break candle open time
            availability = max(break candle availability, broken swing availability)
```

`_most_recent_unbroken` is transcribed with **all three key tiers**
(`pivot_bar_index`, `pivot_start_time`, `stableKey`). The lower two are
unreachable for valid production swings, but omitting them would silently bake
that invariant into the port.

The **defensive fallback is present and must stay** (§17.5a). Pine carries no
runtime assertion about the invariant.

The `availability` **max is transcribed structurally** even though the candle
operand always wins (§17.5) — the operands genuinely differ in the fixtures, so
the max is exercised rather than trivially equal.

`StructEventRec` gained one field, `protectedSwingKey`: Python publishes
`protected_swing_id` on every `StructureTransition` (`transitions.py:36`) and it is
not derivable from the other fields on the record.

### 18.4 A structural consequence worth recording

**A second same-direction BOS is unreachable within I5.** After a BOS the weak
side is cleared, and only a later `SWING_VISIBLE` past the boundary can re-arm it
— which is the P2-I6 / TD-B gate. Python agrees on the same input, so parity
holds; `test_a_second_same_direction_bos_requires_weak_re_arm` records this so it
is not later mistaken for a missing feature.

The same fact means the "replacement excludes an already-broken swing" case is not
reachable from BOS alone: `broken_keys` only ever holds weak-side swings, which
are the *opposite* type to the side being searched. It is covered at the Python
level in §17.5 and will become Pine-reachable once CHOCH lands.

### 18.5 I5 proof

| measure | value |
|---|---|
| BOS parity tests | 51 passed |
| campaign scenarios | 13 |
| prefix comparisons | 312 (every candle prefix of every scenario) |
| BOS transitions reproduced | 7 across 7 scenarios |
| suppressed would-be BOS | at least 2 (both directions) |
| mismatches | **0** |
| Pine foundation guards | 61 passed |
| all Structure tests | 233 passed |
| full suite | **1740 passed / 0 failed** |
| plot consumers | 26 / 64 (target 26) |

Required-case coverage: valid BOS both directions; close exactly at the level
(not a break, both sides); wick through with close back inside (both sides); gap
open through with a failing close; repeat suppression (both sides); normal
replacement; newest-of-several replacement; swing not yet visible excluded;
defensive fallback under injection (both directions, discriminating); opposite
weak preserved; boundary index; event time; availability max; CHOCH-precedence
suppression (both directions, plus a guard-the-guard proving it discriminates).

Three source-guard mutations were run against production Pine and each was caught:
optimising away the fallback, relaxing the break predicate to `>=`, and letting
the suppression path mutate state. The file was restored byte-identically each
time.

### 18.6 Resources

| measure | I4 | I5 | delta |
|---|---|---|---|
| lines | 1,986 | 2,199 | +213 |
| bytes | 107,182 | 121,740 | +14,558 |
| plot consumers | 23 | 26 | +3 (4 added, 1 retired) |
| `array.new` | 63 | 67 | +4 |
| for-loops | 55 | 59 | +4 |
| `while` | 20 | 20 | 0 |
| types | 10 | 10 | 0 |

Worst case per confirmed bar: **O(C + S^2 + R^2 + B*S)** — a linear merge over the
bounded window (C is about 300) plus insertion sorts over the live swing and
relationship lists (tens) plus one replacement scan per break. No 1800-bar
traversal, no unbounded accumulation, no nested history explosion. All walk state
is rebuilt from bounded input each confirmed bar and discarded.

`P2_last_swing_type` was retired to fund the BOS slots: swing type is
contract-tested on the adapter and already implied by the relationship codes,
which partition into high-side and low-side values.

### 18.7 Test debt

**TD-A RESOLVED** (§17). TD-B was open at I5 and is now **CLOSED** (§19); no weak
re-arm is implemented in Pine yet — that is P2-I6.

---

## 19. P2-I6-PRE / TD-B — WEAK RE-ARM

Test file: `tests/unit/test_structure_weak_rearm_contract.py` (50 tests).
**Status: TD-B CLOSED / TEST-PROVEN.** The mechanism is genuinely reached through
valid public production state, and every load-bearing condition is pinned.

### 19.1 The exact predicate

All of it lives in the `_EVENT_SWING_VISIBLE` branch (`transitions.py:323-353`).
Each side has exactly **five** conditions:

```
swing.swing_type == SWING_HIGH                 # 1  type matches the weak side
and direction == BULLISH                       # 2  direction matches
and weak_high is None                          # 3  the slot is EMPTY
and swing.pivot_bar_index > boundary_index     # 4  STRICT
and swing.record_id not in broken_ids          # 5  not already consumed
    -> weak_high = swing
```

and the bearish mirror (`SWING_LOW` / `BEARISH` / `weak_low` /
`weak_low_boundary_index`).

There is **no price relation, no relationship label, and no protected-side
relation** — asserted negatively, not just positively.

### 19.2 Four results that "re-arm after boundary" does not tell you

**1. FIRST after the boundary wins — NOT the newest.** Condition 3 fills the slot
on the first qualifying swing and ignores every later one. This is the **opposite**
of protected replacement, where `_most_recent_unbroken` deliberately takes the
newest. Both rules are exercised on the same fixture shape
(`test_the_first_qualifying_swing_wins_not_the_newest` vs
`test_protected_replacement_takes_the_newest_for_contrast`) so the contrast cannot
be lost. **A Pine port that reused the protected-selection helper for re-arm would
be wrong.**

**2. An armed weak level is never replaced, and a passed-over swing never returns.**
A qualifying swing that becomes visible while the slot is still occupied is
discarded outright. Its `SWING_VISIBLE` event has fired and will not fire again,
so it cannot arm later when the slot empties.

**3. Condition 5 is UNREACHABLE** — a second defensive branch of exactly the same
kind as TD-A's protected fallback. Every id in `broken_ids` belongs to a swing that
was serving as a protected or weak level, and both roles require the swing to have
been made visible first; `SWING_VISIBLE` fires once per swing. So a swing can never
already be broken at its own `SWING_VISIBLE`. Proven in two halves: the source half
(`broken_ids.add` is only ever called with a `broken_swing` drawn from
protected/weak) and the empirical half (across the campaign seeds, every
transition's broken swing was confirmed no later than its break candle's
availability). **Per the §17.5a policy, Pine I6 must retain it defensively.**

**4. CHOCH and BOS feed the SAME mechanism.** Both write the same two boundary
variables — CHOCH at `:217`/`:251`, BOS at `:290`/`:320` — and one origin-agnostic
re-arm site reads them. There is exactly one `weak_high = swing` and one
`weak_low = swing` in the whole file, and the branch never inspects transition
origin. Boundaries are **never reset**; they only advance.

### 19.3 Boundary semantics

| pivot vs boundary | result |
|---|---|
| `pivot < boundary` | no re-arm |
| `pivot == boundary` | **no re-arm** (strict `>`) |
| `pivot > boundary` | re-arm |

Proven in both directions. Mutating `>` to `>=` fails the behavioural tests, not
merely the source guard.

The boundary persists across cycles: after a second BOS moves it forward, a swing
that would have qualified against the *old* boundary no longer does.

### 19.4 Event ordering

`_EVENT_CANDLE = 0 < _EVENT_SWING_VISIBLE = 1 < _EVENT_RELATIONSHIP = 2`, sorted
by `(availability_time, kind, tiebreak)`.

**A re-arm can never tie with its own boundary-setting break.** A swing's
confirmation bar is never before its pivot bar, so a swing whose pivot is past the
break bar is always confirmed after it. The CANDLE/SWING_VISIBLE tie therefore
cannot affect re-arm *from that break*.

It can still matter against a **later** candle, and that case is pinned: a high
pivoting at bar 12 and confirming at bar 14 ties exactly with candle 14's
availability. With the shipped order, candle 14 sees an empty weak slot and emits
nothing, then the swing arms — one transition. With `SWING_VISIBLE` moved ahead of
`CANDLE`, the swing arms first and candle 14 immediately breaks it — a spurious
second BOS. `test_swapping_the_order_would_produce_a_spurious_second_bos` runs that
injection to prove the ordering is load-bearing.

### 19.5 The second-BOS cycle

I5 recorded that a repeat same-direction BOS is impossible without re-arm (§18.4).
TD-B closes that loop:

```
bootstrap BULLISH  ->  BOS #1 (breaks H2, boundary := 10, slot empties)
                   ->  H3 (pivot 12 > 10) arms the slot
                   ->  BOS #2 (breaks H3, boundary := 20, protected := newest low)
```

Two distinct BOS transitions, two distinct broken swings, protected replacement
correct at each step, boundary advancing, repeat suppression intact. Proven in both
directions, and `test_the_cycle_actually_passes_through_a_re_arm` asserts the weak
slot trace is exactly `None -> H2 -> None -> H3 -> None` so the two breaks cannot
be an artifact.

The CHOCH-origin cycle is proven too: `BEARISH -> BULLISH_CHOCH (boundary := 10)
-> H3 arms -> BULLISH_BOS`.

### 19.6 Bounded window

Re-arm reads only the supplied swing stream. Removing the re-arming swing from the
bounded input leaves the slot empty and the second BOS does not occur — no hidden
candidate survives outside the stream.

### 19.7 Proof

| measure | value |
|---|---|
| TD-B tests | 50 passed |
| scenarios | 7 |
| prefix comparisons (batch ↔ incremental) | 168 |
| re-arm events | 5 |
| BOS transitions | 9 |
| CHOCH transitions | 1 |
| scenarios reaching a second BOS | 2 |
| mismatches | **0** |

Two source mutations were run against production Python and both were caught
behaviourally: making the boundary comparison non-strict, and allowing an armed
weak level to be replaced. The file was restored byte-identically each time.

### 19.8 SEQUENCING DECISION — **A: implement I6 weak re-arm before CHOCH**

The evidence is that re-arm is **origin-agnostic**. It reads two boundary variables
and never asks which transition kind wrote them, and there is exactly one re-arm
site for each side. Pine already writes both boundary variables from BOS (P2-I5),
so implementing re-arm now is complete and correct for every boundary Pine can
currently produce; when CHOCH lands it will simply write the same two variables and
the existing re-arm code will pick them up unchanged.

Choosing B (CHOCH first) would leave the proven second-BOS cycle unreachable in
Pine for another phase without making re-arm any easier. Choosing C (split) would
create a distinction — BOS-origin vs CHOCH-origin re-arm — that **does not exist in
the source** and would have to be un-invented later.

One consequence to carry into I6: Pine's I5 CHOCH *suppression guard* does not set
a boundary, and must not start doing so. It suppresses a BOS; it is not a CHOCH.
Until CHOCH is implemented, a candle that Python would treat as a CHOCH leaves
Pine's boundaries untouched, so Pine and Python diverge from that candle onward —
exactly the scope limit already recorded in §18.2, unchanged by I6.

### 19.9 Test debt — final state

| # | status |
|---|---|
| **TD-A** | **RESOLVED** (§17) — unreachable, semantics pinned, Pine keeps it defensively |
| **TD-B** | **CLOSED / TEST-PROVEN** (§19) — reachable, reached, every condition pinned |

Both P2 test debts are now discharged. **A third defensive-but-unreachable branch
was found along the way** (re-arm condition 5, §19.2), and is handled the same way:
pinned, documented, and reproduced in Pine rather than optimised away.
