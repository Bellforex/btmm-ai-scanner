# BTRC-V1 — P2 Structure Architecture and Contract

Status: **DESIGN CANDIDATE — NOT IMPLEMENTED.** Awaiting author review.

Branch `pine-p2-structure`, cut from the frozen P1 checkpoint
`21502e182b729e8a7e365076c7defef2b3e90b3d`.

This is a **design** document. It contains no implementation evidence and makes
no claim of Pine correctness. Nothing in `tradingview/` has been modified.

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
| **TD-A** | BOS protected-fallback **TAKEN** branch (`_most_recent_unbroken` returns `None`, so the existing protected level is retained) | **P2-I5 (BOS) may not be accepted until this is directly tested** | OPEN |
| **TD-B** | Explicit weak-re-arm-after-boundary fixture (a new same-type swing with `pivot_bar_index > boundary` re-arms the cleared weak level) | **P2-I6 (weak re-arm) may not be accepted until this is directly tested** | OPEN |

Both are reachable by the same swing-exhaustion pattern that made the CHOCH abort
constructible (§14.3); neither blocks P2-I1 or P2-I2.
