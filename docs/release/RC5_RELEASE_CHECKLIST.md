# RC5 RELEASE CHECKLIST

Every row is **PASS**, **FAIL**, **BLOCKED** or **PENDING**. No other status is
used, and no row says "mostly" or "should be".

* **PASS** — verified here, with the evidence named in the row.
* **FAIL** — verified here and wrong.
* **BLOCKED** — cannot be attempted in this environment; the blocker is named.
* **PENDING** — attemptable, not yet attempted.

A BLOCKED row is **not** a passed row. Nothing below upgrades a blocked item on
the grounds that the code "looks right".

Checkpoint: branch `rc5-poi-authority`. Python semantic freeze `28d432e`.

---

## 0. VERIFICATION LEVEL MATRIX

Eight levels, because "verified" on its own hides the distinction that matters:
a thing can be provably correct in source and still never have run.

| level | means |
| --- | --- |
| IMPLEMENTED | the code exists |
| COMPILED | a compiler accepted it |
| SOURCE-VERIFIED | a test reads the source and asserts its structure |
| VECTOR-VERIFIED | deterministic inputs produce asserted outputs |
| RUNTIME-VERIFIED | it has actually run in its own runtime |
| TESTER-VERIFIED | it has run in the MT5 Strategy Tester against real quotes |
| VISUALLY-VERIFIED | a human has looked at what it drew |
| LIVE-PRODUCTION-VALIDATED | it has run on a funded account |

| component | highest level reached | next level, and what blocks it |
| --- | --- | --- |
| **Python analytical engine** | **VECTOR-VERIFIED** | — (5,800 tests; it IS the reference) |
| **Pine CORE / P4** | **SOURCE-VERIFIED** + COMPILED + token-verified | RUNTIME-VERIFIED — TradingView renderer |
| **Pine VIEW / PANEL** | **SOURCE-VERIFIED** (generated, anti-drift tested) | RUNTIME-VERIFIED — same |
| **EA — broker adapter** | **COMPILED** | TESTER-VERIFIED — process launch denied |
| **EA — Execution Doctrine V1** | **VECTOR-VERIFIED** + SOURCE-VERIFIED | TESTER-VERIFIED — same |
| **Layer-A → EA transport** | **VECTOR-VERIFIED** on real OHLC | TESTER-VERIFIED — same |
| **Stage-2 entry proximity** | **VECTOR-VERIFIED** | RUNTIME-VERIFIED — **never observed against a real quote** |
| **Structure coordinates S1/S2** | IMPLEMENTED (unchanged) | VISUALLY-VERIFIED — TradingView renderer |
| **Live production** | — | **NOT APPROVED** |

**The row that must not be rounded up.** Stage-2 proximity has never run
against a real tester quote. Its logic is pinned by vectors and its MQL5 form
compiles; that is VECTOR-VERIFIED, and it stays there until a tester run
happens.


---

## 1. PYTHON — ANALYTICAL ENGINE

| # | item | status | evidence |
| --- | --- | --- | --- |
| 1.1 | full suite green | **PASS** | 5,800 passed, 19 skipped |
| 1.2 | semantic freeze recorded | **PASS** | `28d432e` |
| 1.3 | working tree clean after the suite | **PASS** | `git status --porcelain` empty |
| 1.4 | lint clean on every file touched | **PASS** | `ruff check` on the changed set only — repo-wide cleanliness is NOT claimed |

## 2. PINE — COMPILE AND CAPACITY

| # | item | status | evidence |
| --- | --- | --- | --- |
| 2.1 | CORE compiles | **PASS** | no-pad save returned `success:true` |
| 2.2 | CORE token count | **PASS** | **100,183**, three agreeing CE10117 points (N=12/16/20) |
| 2.3 | within the hard limit | **PASS** | 100,183 ≤ 100,256, headroom **73** |
| 2.4 | P4 implemented | **PASS** | `f_rc5Ownership()` in `f_rc5Authority()` |
| 2.5 | presentation compaction | **PASS** | PRES-C, 110 tokens, measured |
| 2.6 | VIEW generated, not hand-edited | **PASS** | `test_rc5_view_composition` (22) |
| 2.7 | PANEL generated, not hand-edited | **PASS** | `test_rc5_panel_composition` |
| 2.8 | VIEW is structure-only | **PASS** | composition tests assert no POI/authority/P5/P8 |

## 3. PINE — RUNTIME PARITY

| # | item | status | blocker |
| --- | --- | --- | --- |
| 3.1 | synthetic RBR bootstrap | **BLOCKED** | TradingView renderer |
| 3.2 | synthetic DBD bootstrap | **BLOCKED** | " |
| 3.3 | golden EURUSD M15 DBD | **BLOCKED** | " |
| 3.4 | M45 family parity | **BLOCKED** | " |
| 3.5 | H3 family parity | **BLOCKED** | " |
| 3.6 | transition history | **BLOCKED** | " |
| 3.7 | future-transition guard | **BLOCKED** | " |
| 3.8 | prefix stability | **BLOCKED** | " |
| 3.9 | P4 golden-M15 ownership | **BLOCKED** | " |
| 3.10 | no post-activation P5/P8 from subordinates | **BLOCKED** | " |

**The blocker, precisely.** A chart loads on the AUTHORIZED account
(`window.user.username == "bellcare1994"`, layout `BAH-RC5-LAB`), but the
automation tab reports `document.hidden === true`, all 7 canvases at the 300×150
default and 0 legend rows, so TradingView never lays the renderer out. It is not
an account-selection failure, it is not fixed by focusing the tab
(`document.hasFocus()` goes true while `hidden` stays true), and it is not
detectable from a screenshot — the extension captures over CDP and renders
correctly even while the page reports itself hidden.

## 4. VIEW RUNTIME

| # | gate | status |
| --- | --- | --- |
| 4.1 | G1 VIEW alone | **BLOCKED** |
| 4.2 | G2 CORE alone | **BLOCKED** |
| 4.3 | G3 CORE + VIEW (the production pair) | **BLOCKED** |
| 4.4 | G4 CORE + PANEL | **BLOCKED** |
| 4.5 | structure visual acceptance (S1/S2 coordinate) | **BLOCKED** — and it is also an open author decision |

## 5. EA — COMPILE AND SAFETY

| # | item | status | evidence |
| --- | --- | --- | --- |
| 5.1 | compiles | **PASS** | 0 errors, 0 warnings |
| 5.2 | `.ex5` produced | **PASS** | MetaEditor output |
| 5.3 | installed in the terminal | **PASS** | `MQL5\Experts\RC5\` |
| 5.4 | execution disabled by default | **PASS** | `InpExecutionEnabled = false` |
| 5.5 | live execution needs a second, separate arm | **PASS** | `InpAllowLiveExecution = false`; outside the tester it is also required |
| 5.6 | every `OrderSend` behind the gate | **PASS** | exactly 2 calls, both inside gated functions |
| 5.7 | no martingale / grid / averaging vocabulary in CODE | **PASS** | comment-stripped source scan |
| 5.8 | tester profiles cannot arm a live account | **PASS** | `CanExecuteHere()` requires `MQL_TESTER` or the second arm |

## 6. EA — DOCTRINE VECTORS

| # | item | status | evidence |
| --- | --- | --- | --- |
| 6.1 | deterministic vectors | **PASS** | 83 vectors + 17 golden + 22 release-audit + 10 parser |
| 6.2 | eligibility gates, each with its own reason | **PASS** | parametrized |
| 6.3 | BUY / SELL distal and stop | **PASS** | |
| 6.4 | 2R target both directions | **PASS** | |
| 6.5 | risk sizing across tick size / tick value / step / min / max | **PASS** | parametrized matrix |
| 6.6 | minimum lot over budget DENIES | **PASS** | `RISK_BUDGET_EXCEEDED` |
| 6.7 | duplicate signal identity denies | **PASS** | |
| 6.8 | active same-symbol position denies | **PASS** | keyed on the BROKER symbol |
| 6.9 | close set is exactly the two approved events | **PASS** | parsed out of the MQL5 switch |
| 6.10 | MITIGATED / FALSE_INVALIDATION never close | **PASS** | " |
| 6.11 | the three state migrations never close | **PASS** | " |
| 6.12 | MQL5 source agrees with the Python mirror | **PASS** | source-reading assertions |
| 6.13 | zero-height zone behaviour pinned | **PASS** | measured and documented — see §12 |
| 6.14 | margin / exposure ceiling | **PASS** | `InpMaxMarginFraction = 0.20`, via `OrderCalcMargin` |
| 6.15 | spread-vs-R refusal | **PASS** | `InpMaxSpreadToRisk = 0.25`, boundary inclusive |
| 6.16 | proximity gate, both stages | **PASS** | `InpMaxEntryDistanceSpreads = 1.0`; stale POI now DENIED — see §13 |
| 6.17 | locked gate order | **PASS** | asserted against the MQL5 pipeline; one documented deviation |
| 6.18 | R / TP diagnostics | **PASS** | recorded, never enforced — no max-R gate in V1 |
| 6.19 | POI age cap | **N/A** | deliberately NONE in V1; proximity covers the case |

## 7. EA — ANALYTICAL PARITY WITH PYTHON

| # | item | status | note |
| --- | --- | --- | --- |
| 7.1 | Layer-A projection from real OHLC | **PASS** | `tests/parity_support/rc5_ea_layer_a.py` |
| 7.2 | fixture transport round-trip | **PASS** | every line re-parses to the same 12 values |
| 7.3 | delimiter hazard refused | **PASS** | a POI id containing `\|` raises |
| 7.4 | EA-side field agreement | **BLOCKED** | needs a tester run |
| 7.5 | reachable V1 trigger on a real capture | **PASS** | OBSERVED 2026-08-30 22:00 UTC — see §11 |

## 8. STRATEGY TESTER

| # | item | status |
| --- | --- | --- |
| 8.1 | configs for XAUUSDm / EURUSDm / GBPUSDm | **PASS** |
| 8.2 | per-symbol report paths | **PASS** |
| 8.3 | tester execution | **BLOCKED** — generic process launch works; MetaTrader process control refused on three independent routes; MT5 allows one instance per data folder |
| 8.3a | acceptance run staged | **PASS** — EA installed byte-identical, fixture file, `.set` and launch config all in place |
| 8.4 | XAUUSDm run | **BLOCKED** |
| 8.5 | EURUSDm run | **BLOCKED** |
| 8.6 | GBPUSDm run | **BLOCKED** |

## 9. MTF QA

| # | item | status |
| --- | --- | --- |
| 9.1 | M5 / M15 / M30 / M45 / H1 / H3 / H4 smoke | **BLOCKED** — same renderer blocker as §3 |

## 10. RELEASE

| # | item | status |
| --- | --- | --- |
| 10.1 | architecture documentation current | **PASS** |
| 10.2 | this checklist exists and is honest | **PASS** |
| 10.3 | publication to TradingView | **FALSE — not attempted, not authorized** |
| 10.4 | merge to `main` | **FALSE — not attempted, not authorized** |
| 10.5 | live-money trading | **FALSE — prohibited** |
| 10.6 | `bellforex` layout | **NOT MODIFIED** |
| 10.7 | BAH library | **UNCHANGED** |
| 10.8 | tester acceptance runbook | **PASS** |
| 10.9 | expected-vs-observed templates | **PASS** |
| 10.10 | journal parser, anti-drift tested | **PASS** |
| 10.11 | TradingView acceptance runbook | **PASS** |
| 10.12 | structure visual decision pack | **PASS** |
| 10.13 | demonstration package | **PASS** |
| 10.14 | parameter consistency audit, 0 mismatches | **PASS** |
| 10.15 | release artifact integrity | **PASS** — `tools/rc5_release_integrity.py`; caught a stale installed EA |
| 10.16 | release backup | **PENDING** |

---

## 11. THE V1 TRIGGER IS REACHABLE — OBSERVED, AND NOT RARE

**Status: PASS.** Both proven favourable-regime windows produce real
`LIQUIDITY_VALIDATED` setups, in quantity.

### The complete walks

60 host bars each, full W1+D1+H4+H1+M5 context, one **TREND** segment across all
60 bars in both windows.

| | 2026-08-28 | 2026-09-08 |
| --- | --- | --- |
| candidates evaluated | 17,689 | 17,903 |
| `btmm_valid` | 3,212 (18%) | 2,996 (17%) |
| favourable regime | 17,689 (all) | 17,903 (all) |
| `momentum_score >= 60` | 8,957 | 5,492 |
| `liquidity_score >= 60` | 6,054 | 5,449 |
| stop at `STRUCTURALLY_VALIDATED` | 14,477 | 14,907 |
| `POI_VALIDATED` | 221 | 612 |
| `REGIME_VALIDATED` | 2,103 | 2,271 |
| `MOMENTUM_VALIDATED` | 0 | 1 |
| **`LIQUIDITY_VALIDATED`** | **888** | **112** |
| of those, price INSIDE the zone | 3 | 5 |

### CORRECTION to the figures reported earlier

An earlier pass reported 6,735 candidates, 41 `btmm_valid` and 1 trigger for
2026-08-28, and concluded that `btmm_valid` was "the dominant filter at 0.6%".
**Both numbers were artefacts of a truncated walk** that stopped at the first
trigger, 24 bars in and mid-bar. The complete walk gives 17,689 candidates and
3,212 `btmm_valid` — **18%, not 0.6%**.

The same artefact explains the earlier 15-bar probes, which showed 99.6%
stalling at `STRUCTURALLY_VALIDATED`. Over 60 bars it is 82%. **Short walks
over-report early-rung stalling**, because the POI registry is still warming up
and most candidates have not yet qualified. Any future reachability figure
should come from a walk long enough to leave warm-up behind.

### The golden execution fixtures

The FIRST trigger the walk produced was unusable — a `HAMMER` at 308.75-312.85
while price was near 4,400 (see §13). The two frozen as golden are the first in
each window where **price is inside the zone**:

| | GOLDEN 1 | GOLDEN 2 |
| --- | --- | --- |
| bar | 2026-08-30 22:45 UTC | 2026-09-08 14:45 UTC |
| epoch | 1788129900 | 1788878700 |
| POI | `HAMMER` BULLISH | `MORNING_STAR` BULLISH |
| zone | 4450.54 – 4467.06 | 4391.07 – 4399.54 |
| host close | 4461.29 (inside) | 4398.65 (inside) |
| authority / validity | authoritative / VALID | authoritative / VALID |
| btmm / alignment / regime | true / ALIGNED / TREND | true / ALIGNED / TREND |
| momentum | BULLISH, 69 | STRONG_BULLISH, 72 |
| liquidity | 70 | 70 |
| permission / lifecycle | `BUY_BIAS` / `LIQUIDITY_VALIDATED` | same |
| **distal / stop** | **4450.54 / 4450.53** | **4391.07 / 4391.06** |

Both are momentum-ALIGNED, which is exactly why they cleared the rung every
earlier `REGIME_VALIDATED` candidate failed — those were all counter-momentum.

Frozen in `tests/unit/test_rc5_golden_execution_fixture.py`. Layer-A fields and
the entry-independent geometry are exact; R, take profit, volume, margin and
both quality gates are `ENTRY_PRICE_PENDING_TESTER`, because they need the
first tradable price AFTER confirmation. **The bar close is deliberately not
used as a proxy entry** — it is a hindsight price the layer could never have
traded at.

## 12. SAFETY FINDING 1 — ZERO-HEIGHT ZONES (micro-R) — NOW GATED

A zero-height liquidity level gave R = 2 ticks against a ~10 tick spread, sized
to 200 lots (~20,000,000 EUR notional) while the 0.5% risk budget passed with
room to spare (40.00 of 50.00).

**Fixed by the spread gate**: `spread <= 0.25 * R`, boundary inclusive, deny
`SPREAD_TO_RISK_INVALID`. Plus a margin gate, `required_margin <= 0.20 *
equity` via `OrderCalcMargin`, deny `MARGIN_EXPOSURE_INVALID`, because the risk
budget does not bound gross exposure and `volume_max` is a contract limit
rather than a risk rule.

Zero-height POIs remain analytically VALID. The gates refuse to TRADE, never to
detect.

---

## 13. SAFETY FINDING 2 — STALE POIs (macro-R) — NOW GATED

The mirror image of §12, and the spread gate was blind to it by construction: a
pathologically LARGE R makes the spread ratio trivially small.

**Closed by a two-stage proximity gate.**

```
distance(price, zone) = 0 inside, else the distance to the nearest edge
tolerance = max(SYMBOL_TRADE_TICK_SIZE, spread * InpMaxEntryDistanceSpreads)
```

`InpMaxEntryDistanceSpreads` defaults to **1.0**. Stage 1 checks the causally
available confirmation close (`CONFIRMATION_PROXIMITY_INVALID`); Stage 2 checks
the ACTUAL executable price at the order (`ENTRY_PROXIMITY_INVALID`). Both
required.

The tolerance is deliberately NOT a fraction of R — a stale far-away zone
produces an enormous R, so an R-relative test would grant more slack the
further away the zone is — and NOT a fraction of price, which behaves
differently on FX and gold. It is built from the tick size and the live spread,
the two quantities the broker publishes.

| case | result |
| --- | --- |
| stale HAMMER 308.75–312.85, confirmation ~4,400 | **DENY**, distance 4087.15 vs tolerance 0.20 |
| GOLDEN 1, close 4461.29 inside the zone | **PASS**, distance 0 |
| GOLDEN 2, close 4398.65 inside the zone | **PASS**, distance 0 |

Two decisions taken deliberately and recorded: **no execution-layer POI age
cap** (age does not prove irrelevance, and proximity already refuses the
distant case), and **no maximum-R or maximum-TP gate** (once proximity passes,
R reflects local geometry; adding a fourth threshold before evidence requires
it would be a guess). R and TP distances are logged as diagnostics on every
eligible trade and **never** cause a denial.

---

## What a reader should conclude

The BUILD is complete and internally verified: Python, Pine compile and
capacity, EA compile, EA doctrine vectors and the Layer-A projection all PASS.

§13 is now CLOSED. The proximity gate refuses the stale-POI case that both
earlier gates passed, so nothing on this list is currently known to produce a
WRONG trade rather than no trade.

**Every remaining item is an EXECUTION-ENVIRONMENT item**, and there are
exactly two blockers behind all of them:

1. TradingView never lays out its renderer in the automation tab, which blocks
   all Pine runtime parity, all VIEW gates, the structure visual acceptance and
   MTF QA;
2. the sandbox denies a terminal launch with a custom config, which blocks every
   Strategy Tester run and the EA-side half of analytical parity.

Neither is a defect in the deliverable, and neither can be argued away from
here. RC5 is not releasable until they are attempted on a machine where a
TradingView chart is visibly on screen and MetaTrader can be started with a
tester config.
