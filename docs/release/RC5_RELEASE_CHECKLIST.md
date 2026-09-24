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

## 1. PYTHON — ANALYTICAL ENGINE

| # | item | status | evidence |
| --- | --- | --- | --- |
| 1.1 | full suite green | **PASS** | 5,717 passed, 19 skipped |
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
| 6.1 | deterministic vectors | **PASS** | 64 passed |
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
| 6.16 | proximity requirement | **PENDING** | V1 has NONE — a stale POI 4,000 points away is eligible; see §13 |

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
| 8.3 | tester execution | **BLOCKED** — a terminal launch with `/config:` is denied in this sandbox |
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
| 10.8 | release backup | **PENDING** |

---

## 11. THE V1 TRIGGER IS REACHABLE — OBSERVED

**Status: PASS.** A targeted walk over the proven favourable-regime window
produced a real `LIQUIDITY_VALIDATED` setup. The conjunction occurs.

### The walk

60 host bars from 2026-08-28 15:00, full W1+D1+H4+H1+M5 context, one regime
segment throughout (**TREND**, 24 bars of data spanning to 2026-08-30 22:00).

| | |
| --- | --- |
| candidates evaluated | 6,735 |
| `btmm_valid` | **41** |
| favourable regime | 6,735 (all) |
| `momentum_score >= 60` | 4,053 |
| `liquidity_score >= 60` | 26 |
| reached `REGIME_VALIDATED` | 40 |
| reached **`LIQUIDITY_VALIDATED`** | **1** |

`btmm_valid` remains the dominant filter: 41 of 6,735, about 0.6%. Of the 40
that reach rung 5, one clears momentum AND liquidity together.

### The setup that triggered

| field | value |
| --- | --- |
| bar | **2026-08-30 22:00 UTC** (epoch 1788127200) |
| POI | `HAMMER`, BULLISH |
| zone | 308.75 – 312.85 |
| authority / validity | authoritative / VALID |
| btmm / alignment / regime | true / ALIGNED / TREND |
| momentum | BULLISH, score 66 |
| liquidity | score 70 |
| permission / lifecycle | `BUY_BIAS` / `LIQUIDITY_VALIDATED` |

### It is NOT usable as the golden execution fixture

The host bar closed near **4,400**; the zone is at **308–312**. A zone that low
exists in no series but **W1**, which carries 2,000 bars — about 38 years — so
this is a POI formed when gold traded near $310, never breached, and still
registered.

Executing it would be a buy at 4,400 with a stop at 308.74 and a take profit at
12,582.52. **V1 accepts it**, and so do both new gates. See §13.

So: reachability is PROVEN and this candidate is REJECTED as the golden
fixture. A second walk collecting every trigger in the window is running, to
find a contemporaneous one.

---

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

## 13. SAFETY FINDING 2 — STALE POIs (macro-R) — NOT GATED

The mirror image, and the spread gate is blind to it by construction: a
pathologically LARGE R makes the spread ratio trivially small.

Measured on the trigger above, entry 4,400, equity 10,000:

| | |
| --- | --- |
| R | **4,091.26** |
| take profit | **12,582.52** |
| volume | 0.01 |
| realized risk | 40.91 of 50.00 |
| spread / R | 0.00005 |
| margin fraction | 0.05 |
| **verdict** | **ELIGIBLE** |

**The gap is that V1 has no proximity requirement.** Executing "at a POI"
implies price is interacting with it, but the entry rule says only "the first
tradable price AFTER confirmation". Entry 4,400 and entry 312 are both accepted
against the same zone.

Author decisions, recorded in
`docs/validation/BTRC_V1_RC5_EXECUTION_DOCTRINE_V1.md`: whether to require
proximity and how to express it; whether to bound context history so
decades-old POIs never register; and whether a maximum R or TP distance is
warranted independently.

---

## What a reader should conclude

The BUILD is complete and internally verified: Python, Pine compile and
capacity, EA compile, EA doctrine vectors and the Layer-A projection all PASS.

One item is neither environment nor build: **§13, the missing proximity rule.**
V1 will currently execute a decades-old POI four thousand points from price,
and both new gates pass it. That is an open author decision, not a blocked
task, and it is the only item on this list that could produce a wrong trade
rather than no trade.

**Every other remaining item is an EXECUTION-ENVIRONMENT item**, and there are
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
