# BTRC-V1 P6 — Cross-Timeframe Substrate: CLOSURE

Status: **P6 MTF CORE — CLOSED**
Branch: `pine-p4-btmm`
Closed: 2026-09-03

---

## 1. The frozen contract

```
P1 semantic minimum      1250 CONFIRMED bars
P6 request envelope      C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS + 1 = 1251
Host envelope            calc_bars_count = 1800
Provider                 FXCM (FX:XAUUSD), asserted on every observation
Transported surfaces     five, and only five
P3 lifecycle             one flat symbol-level collection
Lookahead                none: all state advances on barstate.isconfirmed only
```

The request envelope is **derived**, never written as a literal, so it cannot
drift from the semantic minimum. Guards fail if anyone sets it back to 1250.

The five transported surfaces are `confirmed_swings`, `equal_level_clusters`,
`displacement_observations` (P1) and `structure_transitions`, `current_state`
(P2). Excluded and proven excludable: `support_resistance_zones`, `trendlines`
(leaves — consumed by nothing) and `swing_relationships` (never referenced).

## 2. Why 1251 and not 1250

`calc_bars_count` counts the bars a context is GIVEN, and one is always the
current forming bar. Measured live at 1250: dataset 1250, **confirmed 1249**. The
host publication guard is `confirmedBarCount >= C_P1_MIN_CALC_BARS`, so a
1250-bar request could never make a context warm — it would publish nothing, on
every higher timeframe, silently. 1251 is the minimal envelope yielding 1250
confirmed. This is a transport correction; no P1–P4 semantics moved.

## 3. Semantic input is confirmed bars only — proven from source

Traced directly through `f_p6TfProjection`: **zero** `:=` assignments outside
`if barstate.isconfirmed`, and the only statement before that gate is
`int qDataset = last_bar_index + 1`, which is returned and never read. The
forming bar therefore reaches no array, no ATR recurrence and no detector.

Consequence for the capture: the semantic input is exactly the confirmed bars —
1250 for the five requested contexts, and the host confirmed count for M15,
which is **measured at the anchor rather than hard-coded**.

## 4. The M15 asymmetry, and the lesson that shaped the capture

M15 confirms 1799 bars against 1250 for the others. The asymmetry is
TradingView behaviour, not a source special case: one derived constant, six
identical call sites, one projection function — requesting the chart own
timeframe does not create a reduced context.

An experiment that dropped 120 warm-up bars changed **every ATR value** and left
the discrete projection **bit-identical**, because the Wilder recurrence had
converged past the tolerance that flips a swing. The conclusion is not that
shorter input is acceptable; it is that **output equality is not input
identity**. Closure therefore requires exact input replay, and acceptance is
decided on identity dimensions, never on whether outputs happened to agree.

## 5. Evidence

### 5a. Architecture and statics

* Dependency closure: S/R and trendlines are leaves (`test_p6_dependency_closure`).
* Purity: `f_advancePivotFrontier`, `f_detectSwings`, `f_detectEqualLevels`,
  `f_measureLeg`, `f_latestDisplacement`, `f_medianRange` and all five P2
  functions — including the 201-line `f_p2StructureWalk` — reference **zero** of
  the file 176 globals. So the requested contexts CALL the closed functions; no
  algorithm is re-implemented.
* Host/request maintenance equivalence, at statement level: the Wilder
  recurrence, the seven-array window and its prune bound, `absFirst`, and all six
  frontier/detector hand-offs (`test_p6_projection_matches_host_maintenance`).

### 5b. Live

* Compile: 0 errors. Runtime matrix **72/72** on FXCM, 8 operation points ×
  9 invariants, every point asserting the feed.
* Staleness: 131 s with a static host bar moved **zero** fields while the forming
  bar price ticked.
* Isolation: `P6_ALIAS_HITS = 0`, and the P2 direction is differentiated (H4
  bearish against five bullish) — which an aliased projection cannot produce.

### 5c. Real-data parity — the capture

```
capture_id   002c391ae9d625599e2f60ff57552b9c
feed         FX:XAUUSD (FXCM)      host M15, dataset 1800, confirmed 1799
anchor       1788407100000         aliasHits 0
envelopes    semanticMin 1250  request 1251  host 1800

TF    rows   first            last             input H1     input H2
W1    1250   1031522400000    1787522400000      27898685    408967381
D1    1250   1635976800000    1788300000000     199898738    511630821
H4    1250   1762844400000    1788386400000      51383106    669701320
H1    1250   1781794800000    1788400800000     959311493    516280898
M15   1799   1786020300000    1788405300000     469807677    492791178
M5    1250   1787840100000    1788406500000     288875352    192288908
```

* **Input identity 6/6**, on all five dimensions (rows, first, last, H1, H2).
* **Python independently reproduces the Pine input digest** for all six
  timeframes from the exported rows — the non-tautological half of the lock,
  proving the candles handed to the oracle really are the data the digest covers.
* **Blind replay A/B byte-identical** (`11c1e6b6…`), fresh processes.
* **30/30 surface comparisons exact**: six timeframes × five surfaces, Pine
  digest against a Python digest computed by an oracle that never saw a Pine hash.
* **Global digest exact — H1 = 74231825, H2 = 124714621.**

Cross-check kept for the record: the W1 first bar (`1031522400000`, open 320.15)
is byte-identical to the feasibility probe `CTX|0` row, captured by a different
script on a different run.

Artifacts (gitignored): `artifacts/p6_capture/` — `atomic_all_raw_log.csv`
(4,142,263 bytes), `replay_A.json`, `replay_B.json`,
`P6_REAL_DATA_PARITY.txt`. Re-derived on every run by
`tests/unit/test_p6_real_data_parity.py`, which skips when the capture is absent.

### 5d. Resources (P6 DEV, the production script — not the atomic twin)

```
source            168229e8…  4699 lines, 252,658 bytes, LF
request.security  8    (Pine limit 40)
plot calls        63   (Pine limit 64)   <- one slot spare
global vars       176
UDT types         12
request tuple     14 values per context
```

`P6_RESOURCE_CLASS = WATCH`, solely because plots sit at 63 of 64. Nothing else
is near a limit and no semantics were cut to get there — the atomic twin
deliberately captures through the log rather than through plots for this reason.

**Not measured:** wall-clock timings at 300/600/1200/1800 host bars. TradingView
exposes no timing API to the chart model, and the runtime matrix observed
health and correctness rather than duration. The resource class above rests on
static counts and on 72/72 clean runtime observations, not on a stopwatch.

## 6. Two defects this phase found, and one it inherited

* **Outputs collapsed on forming bars.** The first live run read 0 swings on all
  six timeframes: the projection outputs were per-call locals that reset on any
  bar where the requested context own bar was still forming. Now `var`, which is
  also the staleness rule BTRC needs.
* **The capture anchor was wrong.** Anchored at `islastconfirmedhistory`, M5
  returned 1248 confirmed rows — below the minimum — because the newest bars sit
  in the realtime region unprocessed. Re-anchored to the live edge.
* **Inherited and still open:** the saved TradingView `P4 DEV` script is 41 lines
  short of the repo file and predates the backfill fix `0c8a4c9`. P6 was
  therefore built from the repo source, never from that buffer. **This remains an
  open P4 deployment issue.**

## 7. Gate

```
P6_ATOMIC_INPUT_IDENTITY_ESTABLISHED      TRUE   (6/6, five dimensions)
P6_BLIND_REPLAY_DETERMINISTIC             TRUE   (A == B, byte-identical)
P6_SIX_TF_REAL_DATA_PARITY                TRUE   (30/30 exact)
P6_GLOBAL_DIGEST_EXACT                    TRUE   (H1 74231825 / H2 124714621)
P6_MTF_REAL_DATA_PARITY_ESTABLISHED       TRUE
P6 MTF CORE                               CLOSED
```

**Not claimed here.** T1/T2/T3/T4 input parity is not established: those are P5
constructions over these surfaces and belong to P5 evidence. What P6 closes is
that the five transported surfaces are, on real FXCM data across six timeframes,
exactly what the authoritative Python engine produces.
