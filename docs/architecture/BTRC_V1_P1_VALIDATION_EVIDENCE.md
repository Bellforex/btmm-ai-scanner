# BTRC-V1 — P1 Validation Evidence

Status: **ALL MANDATORY P1 VALIDATION GATES COMPLETE (2026-08-23).** Uncommitted.

This document is the permanent record of P1's *validation*. It is deliberately
separate from the three other P1 documents, which serve different purposes:

| document | role |
|---|---|
| `BTRC_V1_P0_PYTHON_TO_PINE_ARCHITECTURE_MAP.md` | **contract** — what the port must mean |
| `BTRC_V1_P1_PINE_MEASUREMENTS_PORT.md` | **implementation** — how it was ported |
| `BTRC_V1_P1_PERFORMANCE_OPTIMIZATION.md` | **performance evidence** — PERF-1/3/4/4A |
| **this file** | **parity evidence, feed limitation, live closed-bar validation** |

Scope: P1 scanner-measurement closure only. **No production or live-trading
approval is expressed or implied.** P2 remains blocked.

---

## 1. Headline result

**No Pine semantic defect was established anywhere in P1.**

All nine measurement fields diverged from the frozen Python oracle at some point
during parity testing. Every one of those differences was traced to a single
external cause: **the TradingView FXCM historical feed has been revised since the
oracle was exported.** Given the current feed values, production Python
reproduces Pine's output.

---

## 2. The feed limitation (the finding that explains almost everything)

The frozen oracle (`P1_M15_PARITY_ORACLE_JULY_2026.csv`,
sha256 `b18b6e9a…d802a3`) was built from
`DATASETS/xauusd_2026_07_pilot`, whose manifest declares
`provider: FXCM`, `source_description: "FXCM XAUUSD native TradingView CSV
reference exports"`, `created_at_utc: 2026-08-02`.

**Both sides of the comparison are therefore FXCM read through TradingView.**
This is not a cross-provider difference — it is the *same* provider and platform
at two different export vintages, roughly twenty days apart.

Measured across the 11 originally sampled M15 bars:

| component | exact | mean abs Δ | max abs Δ | sign |
|---|---|---|---|---|
| open | 8/11 | 0.0055 | 0.03 | mixed |
| **high** | **0/11** | **0.1273** | **0.42** | **all ≥ 0** |
| low | 3/11 | 0.0209 | 0.11 | **all ≤ 0** |
| close | 8/11 | 0.0136 | 0.10 | all ≥ 0 |

TradingView's bars **strictly contain** the oracle's: highs never lower, lows
never higher. This is the signature of TradingView replacing realtime-built bars
with server-side backfilled bars — wicks are exactly what changes.

Two consequences matter analytically:

1. **Wider bars ⇒ larger Wilder ATR.** Every decision threshold in the engine is
   `k × ATR`, so the *tolerances themselves* move with the feed.
2. The oracle is **not** mis-aggregated. M1 → M5 → M15 → oracle reproduce each
   other exactly on all sampled bars (22/22 extremes, full 15/15 M1 coverage per
   bar). Aggregation error, missing bars and resampling defects are excluded.

---

## 3. Nine-field parity matrix (final)

| field | frozen Python | observed Pine | root cause | classification |
|---|---|---|---|---|
| `swing_high_price` | 4037.89 / 4060.18 | 4037.93 / 4060.21 | pivot-candle high revised upward | **FEED_CAUSALITY_ESTABLISHED** |
| `swing_low_price` | 4050.67 / 4050.60 / 4021.07 | 4050.54 / 4050.59 / 4020.76 | pivot-candle low revised downward; pivot identity unchanged | **FEED_CAUSALITY_ESTABLISHED** |
| `disp_code` | — | — | never mismatched (11/11) | **NO_MISMATCH** |
| `disp_ratio` | 0.95134 | 0.94 | pure OHLC: `(H−L) / median₂₀(H−L)` | **FEED_CAUSALITY_ESTABLISHED** |
| `equal_high` | 4119.535 | 4119.58 | both cluster member highs revised | **FEED_CAUSALITY_ESTABLISHED** |
| `equal_low` | `na` ×7, 4098.625 ×4 | 4070.75 ×7, 4072.88 ×4 | separator pivot lost → supersession re-partition | **FEED_CAUSALITY_ESTABLISHED** |
| `sr_top` | 4116.46 | 4119.15 | Zone-B touch crosses its floor (§5) | **FEED_CAUSALITY_ESTABLISHED** |
| `sr_bottom` | 4114.87 | 4117.93 | same | **FEED_CAUSALITY_ESTABLISHED** |
| `tl_norm_slope` | 0.0235963 | 0.02 | inside `[0.015, 0.025)` | **DISPLAY_COMPATIBLE** |

Each was proven by substituting the *measured* current-TradingView values into
production Python and re-running the full dependency chain — never by adjusting
Pine, and never by inventing an input. Each replay was preceded by a fidelity
gate requiring exact reproduction of the frozen oracle first.

### 3.1 Retired hypotheses

These were entertained during the investigation and are **positively refuted**.
They must not be reintroduced without new evidence:

| retired hypothesis | why it fell |
|---|---|
| equal-low **adjacency** defect | Pine's swing list genuinely differed; clustering never paired non-adjacent swings |
| **low-side concentration** | backwards — the feed is *high*-side dominant (high 0/11 exact, mean 0.127; low 3/11, mean 0.021) |
| equal-high **near-zero tolerance margin** | used bar ATR instead of the cluster's median *member* ATR; real margin is 0.427, not 0.0213 |
| Zone B **"constructed but outranked"** | Python does not construct Zone B at the oracle values, and when it does construct it, it *wins* |
| possible S/R **semantic defect** | refuted by the full-precision boundary read (§5) |
| `disp_ratio` **inherits swing_low error** | `disp_ratio` is pure OHLC and has no swing dependency |

---

## 4. Why display precision was insufficient

TradingView's Data Window renders analytical values at 2 decimals. For most
fields that is harmless. For the final S/R boundary it was not, and this was
proven rather than assumed, using exact rational arithmetic:

```
zone_top    displays 4119.15 -> [4119.145000, 4119.155000)
zone_bottom displays 4117.93 -> [4117.925000, 4117.935000)
touch_high  displays 4117.32 -> [4117.315000, 4117.325000)

implied ATR   = 10*(top-bottom)        -> (12.100000, 12.300000)
touch FLOOR   = 1.5*bottom - 0.5*top   -> (4117.310000, 4117.330000)
```

The floor interval and the touch interval **overlap**, so the displayed values
admit *both* "qualifies" and "does not qualify". No reasoning over 2-decimal
readouts could settle it — which is why full-precision instrumentation
(scaled-integer outputs, `value × 100000`) was built.

---

## 5. Full-precision S/R boundary proof

Read from the forensic probe at `2026-07-31T14:30:00Z`:

```
Zone B  origin 2026-07-30T16:15Z
  ATR         = 12.22956
  touch floor = 4117.31557        (= zone_bottom - 0.05*ATR)
  touch high  = 4117.32000        (2026-07-30T20:00Z)
  margin      = +0.00443
  touch_qualifies   = TRUE
  zone_constructed  = TRUE
  confirmation_time = 2026-07-30T21:00:00Z
  publication_rank  = 1
  published         = TRUE
  zone = 4119.15000 / 4117.92704  -> displays 4119.15 / 4117.93

Zone A  origin 2026-07-29T19:00Z
  constructed = TRUE
  confirmation_time = 2026-07-30T21:00:00Z
  publication_rank  = 0
  published         = FALSE
```

Both zones tie on `confirmation_time_utc`. `detect_support_resistance_zones`
ends with a **stable** sort, so insertion order survives: origins are iterated
ascending by `meaningful_confirmation_time_utc`, the later-origin zone lands
last, and `[-1]` publishes it. Pine reproduces this with an explicit
`(confirmationTime, insertionIndex)` key. **Zone B therefore publishes, in both
implementations, for the same reason.**

### 5.1 Named caveat — this margin is narrow

The qualifying margin is **+0.00443**, under half a cent. The conclusion is
correct **for the measured feed vintage**. It is *not* robust to future
TradingView historical-feed revisions: a further downward revision of the
`2026-07-30T20:00Z` high by more than 0.00443 would drop Zone B and republish
Zone A.

This is a property of the market data, not a defect, and it is fail-visible
rather than silent. It is recorded here so that a future re-run reporting
`4116.46 / 4114.87` is recognised as a feed revision rather than a regression.

---

## 6. Live M1 closed-bar / non-repaint gate

Subject: production `BTMM + POI + BTRC Scanner [P1 DEV]`, inputs 20 / 300 /
1800, Debug OFF, FXCM:XAUUSD M1.

```
forming candle   2026-08-23T22:08:00Z  (chart 23:08 UTC+1)
observation      20.04 s, 6 samples
HIGH   4613.44 -> 4613.46 -> 4613.54 -> 4614.61     CHANGED
LOW    4613.44 -> 4612.85                            CHANGED
```

All nine outputs held **exactly** frozen for the whole forming bar:

| field | value held |
|---|---|
| `swing_high_price` | 4613.59 |
| `swing_low_price` | 4606.06 |
| `disp_code` | 1.00 |
| `disp_ratio` | 1.94 |
| `equal_high` | 4611.59 |
| `equal_low` | `na` |
| `sr_top` | 4617.71 |
| `sr_bottom` | 4617.48 |
| `tl_norm_slope` | 0.19 |

Zero outputs changed before confirmation. After the bar closed, `disp_ratio`
moved 1.94 → 1.83 — permitted and expected, since the prior M1 bar had then been
confirmed.

**Result: `LIVE_M1_CLOSED_BAR_GATE = PASS`.**

### 6.1 Sampling rule — `KEY_ABSENT != VALUE_CHANGED`

A separate 23:09 attempt appeared to show all nine fields changing at once. Raw
DOM inspection proved the keys were **absent** during a mid-render frame — they
were not present carrying new values.

**A browser sample missing any required key must be discarded and retried. It
must never be used to classify repaint behaviour.** A simultaneous "change" in
every field is the signature of a mid-render read, not of repainting. The
qualifying 23:08 run had 6/6 samples with all keys present.

### 6.2 OPEN transcription inconsistency — recorded, not resolved

The live report states `Initial OPEN — 4615.42` while also stating the candle
open was `4613.44`, matching the first H/L/C. These cannot both be right, and
**no preserved raw evidence resolves which is correct, so no value is asserted
here.**

This does not affect the gate. The pass criterion is: same forming candle +
HIGH/LOW movement + all nine outputs frozen. OPEN is not part of it, and the
three criteria that are were each independently satisfied.

---

## 7. Secondary reference (REF) gate — NOT_REQUIRED

`BTMM P1 CORRECTNESS REFERENCE 9dfc3ec` will **not** be re-compared, deliberately:

- It **predates the S/R ordering correction**. That build "had no final sort at
  all" (§17) and could publish an older zone than Python's canonical latest. It
  cannot be authoritative for corrected S/R semantics.
- The one REF sample captured showed REF and DEV agreeing on all nine fields
  *and diverging from Python identically* — no discriminating power.
- All nine fields are now explained by feed at full precision.
- Re-adding it risks silently loading "current version" instead of the pinned
  build, invalidating the comparison it was meant to provide.

A version-regression gate, if wanted later, is better served by a source-level
diff of the two Pine files than by a chart comparison.

---

## 8. Validation evidence — TradingView runtime and bounded-history equivalence

Everything in this section is **VALIDATION EVIDENCE**: measured outcomes of the
completed P1 validation campaign. These are **not architectural constants** and
carry no normative force — the contract lives in the P0 architecture map, and the
capacity constants live in `BTRC_V1_P1_PERFORMANCE_OPTIMIZATION.md`. If a future
run disagrees with a figure here, the figure is stale evidence, not a violated
requirement.

### 8.1 TradingView runtime matrix

Basic plan, production `[P1 DEV]` study, inputs 20 / 300 / 1800:

| timeframe | runs | result |
|---|---|---|
| D1 | 3 | PASS |
| M1 | 3 | PASS |
| M5 | 2 | PASS |
| M15 | 1 | PASS |
| H1 | 2 | PASS |
| H4 | 1 | PASS |
| **TOTAL** | **12** | **12/12 PASS** |

```
RE10110                          = 0
runtime / array / object errors  = 0
```

### 8.2 Bounded-history equivalence

Truncated execution compared against full-history execution across the
published region:

| corpus | comparisons | mismatches |
|---|---|---|
| FXCM (real M15) | 1,653 | **0** |
| 20 adversarial fixtures | 11,020 | **0** |
| 200 randomized fixtures | 110,200 | **0** |
| **TOTAL** | **122,873** | **0** |

### 8.3 Capacity parameters these results were obtained under

| parameter | value |
|---|---|
| `calc_bars_count` | 1800 |
| warm-up floor (`C_P1_MIN_CALC_BARS`) | 1250 |
| published region | 551 bars |

The warm-up floor derives as `lookbackWindow + measured warm-up = 300 + 950`.
Capacity is enforced **fail-closed**: below it every `P1_*` output publishes
`na` rather than a partially-warmed value.

---

## 9. What this evidence does and does not cover

**Covered:** Python↔Pine measurement parity on FXCM:XAUUSD; the nine P1 fields;
the TradingView historical-feed revision limitation; closed-bar / non-repaint
behaviour on live M1.

**Not covered:** other symbols or providers; multi-timeframe orchestration;
canonical FXCM mode; market structure, POI, BTMM or BTRC layers (all later
phases); any statement about profitability, execution or live trading.
