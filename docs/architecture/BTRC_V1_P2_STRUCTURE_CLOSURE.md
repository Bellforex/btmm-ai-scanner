# BTRC-V1 — P2 STRUCTURE — CLOSED

Status: **AUTHOR-APPROVED · IMPLEMENTED · SOURCE-AUDITED · BOUNDED-SEMANTICS
TESTED · TRADINGVIEW RUNTIME VERIFIED · COMMON-INPUT VERIFIED · ATOMIC
REAL-DATA PARITY VERIFIED · PYTHON↔PINE PARITY HARD PASS · CLOSED**

Closure date: 2026-08-29 (P2-CLOSURE-1, following the author-accepted
P2-PARITY-STATE-2 HARD PASS).

This record closes the P2 TradingView Structure phase. It makes **no** claim of
production approval, live-trading approval, or a complete scanner — see §7.

Design of record: `BTRC_V1_P2_STRUCTURE_ARCHITECTURE.md` (§1–§13 design,
§14–§22 as-shipped contract). This closure document adds the verification
record; it does not restate or replace the architecture.

---

## 1. Implementation and verification chain (subjects verified against git)

| commit | subject |
|---|---|
| `0cac239ee1d8ccdaf96807b2e4997f1317599a72` | test(structure): harden P2 BOS and CHOCH contract |
| `0df061fc5d80deaac7074d7412971ec31dc57296` | feat(pine): add P2 structure swing foundation |
| `26bc64deea37ec6e295781c099dfc53f47878b07` | feat(pine): add P2 structure relationships |
| `5707034ac87b51f391181203f7bbfbae92ac3e9e` | feat(pine): add P2 structure bootstrap |
| `128919839aec090e739848e371f98228a0c63a79` | test(structure): resolve P2 BOS fallback contract |
| `8be961da7f5d1f90adc666c7020be1d69b3bd804` | feat(pine): add P2 structure BOS transitions |
| `3c855aa2fd7ea384d9124f5d62b2138285304e48` | test(structure): close P2 weak re-arm contract |
| `00c183a0c1e91a9a5822dea4a765e3167f53eed3` | feat(pine): add P2 structure weak re-arm |
| `f43a296b39e5dfaf1d6f9986846a3b4ac4395168` | feat(pine): complete P2 structure CHOCH transitions |
| `54d19db0feb28609417a0c1f8c55188f0908341d` | test(structure): consolidate bounded P2 walk |
| `c8a255cf601e371ca7e25276e553ebd1914f11ec` | chore(pine): distinguish P2 dev scanner |
| `9c2abf3abab49b8c1282968b2a06a941988d87b8` | test(pine): add isolated P2 parity digest probe |
| `c10f74e4f67f50523db3ff10d74955a6a47c8462` | test(pine): add P2 common-input parity tooling |
| `878cf4e7a66bbf8ba61ad7a4e3c910477ef6b42c` | test(pine): add atomic P2 parity bundle |
| `1a090ee6431b14a90991a5df7ac1087719e5c111` | test(structure): add atomic P2 state replay |

Frozen sources at closure (SHA256, byte-verified):

| file | SHA256 |
|---|---|
| `tradingview/btmm_poi_btrc_scanner_v1.pine` (P2 DEV) | `3d6d10df27e4150e6b693cb55bd32bb269478235eabfdf2fecd9aa23d96fa05b` |
| `tradingview/btmm_poi_btrc_scanner_p2_parity_probe.pine` | `17e6d56b5b31c5a8fa4fff4cd4f2f1caff22cbdfdd20917313e2c60c0608b749` |
| `tradingview/p2_m15_common_input_logger.pine` | `73029f425e3655f7923be3d3db936c249a8641a372dd7f99235092279fe823a7` |
| `tradingview/btmm_poi_btrc_scanner_p2_atomic_parity_bundle.pine` | `22eec41e15b8f71eb69f4039fb3c9f69e4c773eec76ebec0813c86b80be4f92c` |

## 2. Frozen bounded Structure contract (summary; source is authoritative)

* Direction: `UNDETERMINED = 0`, `BULLISH = 1`, `BEARISH = -1`.
* Relationships: `HH = 1`, `LH = -1`, `EH = 10`, `HL = 2`, `LL = -2`,
  `EL = 20`; tolerance = `0.10 ×` the **current** swing's reference ATR;
  strict comparisons (exactly ±tol is EQUAL); highs-then-lows output order.
* Transitions: `BULLISH_BOS = 1`, `BEARISH_BOS = -1`, `BULLISH_CHOCH = 2`,
  `BEARISH_CHOCH = -2`.
* Sentinel: `C_ST_NA = -99`, never collapsed into generic `na` (encodes 199 in
  the parity digest contract, vs 0 for `na`).
* BOS: strict close-only break of the weak level. CHOCH: strict close-only
  break of the protected level. CHOCH is evaluated before BOS on the same
  candle, and BOS is skipped on that candle whichever way CHOCH exits.
* Weak re-arm: first qualifying visible swing after the boundary.
* Bounded semantics: 300-bar analytical window (`lookbackWindow`); moving the
  left edge is semantically meaningful (proven by the consolidation suite);
  there is **no** unconditional persistent P2 frontier — the walk is recomputed
  from the bounded view every confirmed bar.

## 3. TradingView runtime gate (author-accepted record)

108 / 108 definitive observations across M1, M5, M15, H1, H4, D1 ×
{FRESH_ADD, RELOAD, SWITCH_BACK} × debug {false, true} × 3 repetitions:
0 hard failures, 0 RE10110, 0 Pine runtime errors, 0 array/object errors.

**`INCREMENTAL_FRONTIER_RUNTIME_MANDATORY = FALSE`** — the bounded
recompute-per-bar walk is runtime-viable in the tested environments; the
P2-I8 persistent incremental frontier is therefore **not required** and was
not implemented. No runtime-performance claim is made beyond the tested
environments.

## 4. Real-data parity gate (canonical campaign)

FXCM:XAUUSD, M15, atomic anchor **1787949000000 ms**, captured by ONE Pine
execution of the atomic parity bundle and verified fully offline:

| window | range | dual hashes |
|---|---|---|
| execution context, 1800 closed bars | 1785740400000 → 1787949000000 | H1 `520932393`, H2 `908592287` |
| final-600 input | 1787214600000 → 1787949000000 | H1 `659491478`, H2 `501330745` |
| final-300 Structure state | 1787669100000 → 1787949000000 | H1 `902876790`, H2 `394113019` |

Python replay (blind, deterministic across two fresh processes) reproduced
**15 / 15 per-field Structure digests and 2 / 2 overall state digests
exactly**. Per-field hashes for this anchor (historical verification evidence
only — never production constants): adapted_swing_count `648099550`,
last_pivot_start_abs `973360586`, last_conf_time `115885036`,
relationship_count `104053110`, last_high_relationship `927988638`,
last_low_relationship `126719078`, direction `868419196`, protected_high
`972352409`, protected_low `516336152`, weak_high `561438544`, weak_low
`511989344`, transition_count `124897029`, last_transition_code `349719890`,
last_broken_key `147422692`, last_broken_level `77064170`.

Gitignored evidence (raw market data and Pine logs are deliberately NOT
committed; provenance is by SHA256):

| artifact | SHA256 |
|---|---|
| `artifacts/p2_parity/P2_M15_ATOMIC_BUNDLE_1787949000000.txt` | `d366c9f3ce3c48cb31b3a469809ac711f655239d04763801120b7cb332da0677` |
| `artifacts/p2_parity/P2_M15_ATOMIC_CONTEXT_1800_1787949000000.csv` | `a8735c0522c1cc8aa5ea454eafaa01a0825fb811806e0865aba983c3c8071a07` |
| `artifacts/p2_parity/P2_M15_PYTHON_STATE_TRACE_1787949000000.csv` | `fdb6552c8ae3ccb7b34ab818cde52e01e85ac26d8471b9923e5dc6331f2c8d39` |
| `artifacts/p2_parity/P2_M15_ATOMIC_STRUCTURE_STATE_PARITY_1787949000000.txt` | `91f69fd24cc424d862932e10442b9fc7b48c846338b0f4fe3501fbb5646c12b0` |

The replay harness (`tests/parity_support/p2_atomic_state_replay.py` +
`tests/unit/test_p2_atomic_state_replay.py`, commit `1a090ee`) is
parity-scope orchestration only: it drives the authoritative production
components (continuous Wilder ATR, `detect_confirmed_swings` via the validated
injected-ATR bridge, `detect_swing_relationships`,
`analyze_structure_state`) over Pine's exact bounded execution model and
reimplements no semantic rule. It is blind — it contains none of the Pine
target hashes.

## 5. The feed-revision lesson (parity engineering, not a Structure defect)

TradingView/FXCM historical bars **may revise retroactively**. Two capture
sessions can therefore belong to different feed eras even when their
timestamps are byte-identical — the first extended-context capture attempt
failed exactly this way (retired anchor `1787722200000`; nested-600 hashes
diverged at identical timestamps; evidence preserved under
`artifacts/p2_parity/*_1787722200*`). The resolution was the **atomic
same-execution bundle**: raw context + input digest + state digest captured
from ONE Pine execution. Future parity phases (P3+) should prefer atomic
same-execution evidence whenever market-data revision could create
cross-session ambiguity. The old anchor `1787722200000` is HISTORICAL
EVIDENCE ONLY and is not a valid comparison baseline.

## 6. Phase status after closure

* **P1 Measurements: CLOSED** (see `BTRC_V1_P1_VALIDATION_EVIDENCE.md`,
  `BTRC_V1_P1_PERFORMANCE_OPTIMIZATION.md`).
* **P2 Structure: CLOSED** (this record).
* **P3 POI / Lifecycle: AUTHORIZED FOR ARCHITECTURE / CONTRACT AUDIT ONLY**
  (next task: P3-ARCH-0 — Python POI architecture, frozen POI contracts,
  lifecycle semantics, resource constraints, minimum Pine-native design).
  P3 is NOT implemented, NOT parity-verified, NOT production-ready.

## 7. What P2 closure does NOT prove

P2 closure proves bounded Structure parity on real data and nothing more. It
does **not** prove: P3 POI parity; BTMM parity; BTRC parity; MTF orchestration
parity; final UI behavior; final alert behavior; invite-only release
readiness; production trading readiness; broker execution; entry logic; stop
loss; take profit; risk management; or automated order execution.

**SCANNER OVERALL: NOT COMPLETE · NOT INVITE-ONLY RELEASE READY · NOT
PRODUCTION TRADING APPROVED.**
