# BTRC V1 — RC3 High-RAM Continuation: semantic corrections and live evidence

Continuation from this machine's actual state (`626c522`, branch
`rc3-poi-semantics-dev`) on branch `rc3-highram-continuation`. No reset, no
transfer restore. RC1/RC2 remain byte-frozen and verified.

## 1. Two semantic blockers found, classified, corrected

Both were investigated against frozen authority before any code moved, and
both were classified rather than silently patched.

### T3 evaluation timeframe — **PINE DEFECT** (corrected)

Production Python keys momentum / breakout / pullback on
`poi.effective_timeframe` (`btrc/t5_engine.py:78,83-85`), and the frozen MTF
contract records T3 as **per POI timeframe**
(`BTRC_V1_P6_MTF_ARCHITECTURE.md:62`). Both RC3 builds instead read `m15Ext`
unconditionally (`f_p5T3Mom(m15Ext)`), so every non-M15 host was scored
against a foreign context.

This was invisible to every prior parity capture because all of them were
gathered on an M15 host — the one chart where the defect is exact. The P5
closure doc says so itself: parity evidence *"was, and remains, gathered
exclusively on an M15 host"* (`BTRC_V1_P5_BTRC_CLOSURE.md:199`).

Corrected in both builds: the T3 context is dispatched across the six
authority timeframes (W1/D1/H4/H1/M15/M5), and hosts outside that set
reproduce production's missing-component scores (momentum 50, breakout 40,
pullback NA) instead of borrowing M15.

**Live confirmation on H4.** Re-running the corrected build on FXCM:XAUUSD
H4 changed the active-POI table in place:

| | before | after |
|---|---|---|
| scores | 48, 48, 46, 50, 50, 48, 50, 50 | 41, 43, 39, 45, 45, 43, 45, 45 |
| permissions | COUNTER-TREND / WATCH ONLY | WATCH ONLY / **NO TRADE** |

The defect was real, material, and reached permission state on the exact
host this campaign's parity work targets.

### S/R detection window — **NO ACTUAL DIFFERENCE** (no change made)

Python S/R detection is batch over the full series
(`domain/support_resistance.py:169-234`); Pine bounds it to
`lookbackWindow = 300` (`:61`, pruned at `:1899-1900`). This is a frozen,
explicitly disclosed engineering adaptation, not a defect — the Pine banner's
governing rule states *"unbounded history -> a bounded rolling window.
Analytical MEANING ... is preserved unchanged"* (`:33-36`), and the port
document records the disclosed limitation and the verdict
`PORTED_WITH_ENGINEERING_ADAPTATION (window; recompute-on-change)`
(`BTRC_V1_P1_PINE_MEASUREMENTS_PORT.md:56-65,133`).

The specific "51 vs 42" figure appears nowhere in this repository and could
not be attributed. If it is ever re-measured, the dominant confounder to
control is cold-start ATR — the project's own harness already injects the
continuous ATR for exactly this reason
(`tests/parity_support/p3_atomic_state_replay.py:120-133`). **No code was
changed for this.**

## 2. S/R source instant — corrected on both sides

A `SUPPORT_ZONE` / `RESISTANCE_ZONE` carried the zone's confirmation time in
all five of its time fields, collapsing source into availability: the level
appeared to be born at the moment it confirmed, and its drawn left edge hid
its real age.

Source is now the **origin swing's pivot-end candle** on both sides — Python
resolves it through the swing record, Pine carries it on `SRRec` as
`originPivotEndTime`. Confirmation and availability are unchanged. The
`(srcFirst, count, srcLast)` identity triple deliberately does **not** move:
that is POI identity, and the documented collision fix depends on it.

Python refuses to build an S/R candidate whose origin swing was not supplied
rather than falling back to confirmation — a silent fallback is what made
this invisible.

**Live confirmation (Phase 7).** In the H4 capture below, across **978**
real registry POIs: `srcTime < availTime` for **978**, `srcTime ==
availTime` for **0**. The nine S/R zones specifically:

| poiIdx | type | source → availability delay |
|---|---|---|
| 302 | SUPPORT | 108 h |
| 304 | SUPPORT | 111 h |
| 305 | SUPPORT | 116 h |
| 335 | SUPPORT | 123 h |
| 371 | RESISTANCE | 112 h |
| 402 | SUPPORT | 28 h |
| 456 | SUPPORT | 424 h |
| 459 | SUPPORT | 428 h |
| 595 | SUPPORT | 52 h |

Under the old behaviour every one of these read 0 h. These levels existed
between 1.2 and 17.8 days before they confirmed.

## 3. P3LIFE captured — the blocker the previous session could not clear

`BTRC_V1_RC3_PARITY_STATUS.md` recorded P3 and P5 as **NOT CAPTURED**: the
first P3LIFE attempt was guarded on `barstate.islast` (unreachable inside
`barstate.isconfirmed`), and after the guard was corrected to
`barstate.islastconfirmedhistory` the logs panel would not re-bind to the
parity study, so no capture was taken.

Both obstacles are now cleared:

- The corrected guard **does** emit. P3LIFE produced **978 records** on
  FXCM:XAUUSD H4.
- The log-binding problem is a **study-ambiguity artifact**: with two studies
  attached, the download exported the *P6 DEV* stream regardless of which
  study's panel was open. Removing P6 DEV so only the parity study remains
  makes the download unambiguous. Recorded here so the next session does not
  re-diagnose it.

Capture: `artifacts/rc3_parity/rc3_p3life_h4_corrected.csv` (gitignored),
sha256 `f499318602a4e0a72765f91f1110d16e7b6311e1f10b839e471d3afbf4d41987`,
978 P3LIFE rows, FX:XAUUSD H4, RC3 PARITY DEV version 9.

Isolating the stream also solves the buffer-overflow problem that truncated
earlier runs: enabling only `p9DebugLog` (P3LIFE) and leaving `debugMode`
(P5EVAL) and `p8DebugLog` (P8EVENT) off yields a clean, complete stream.
Guard map for the next session: **P3LIFE = `in_33`, P5EVAL = `in_0`,
P8EVENT = `in_28`.**

## 4. The previous P8 capture is no longer parity evidence

`artifacts/rc3_parity/rc3_parity_logs_h4.csv` (2200 events) was produced on
H4 by the **pre-correction** build, so its permission events were computed
from M15 T3 rather than H4 T3 — demonstrated above to change both score and
permission. Per the campaign's own rule ("do not collect final parity
evidence against a knowingly wrong build") it is superseded and must be
re-captured.

Also recorded: `rc3_p3life_h4.csv` was a byte-identical duplicate of that P8
capture (same sha256 `72b83d33…`) containing **zero** P3LIFE rows. It was a
misnamed copy, not a capture.

## 5. Open blocker — RC3 USER DEV exceeds the Pine token limit

The corrected **USER** build no longer compiles:

> Compiled code contains too many tokens: **100464**. The limit is **100256**
> (CT10117)

It saved (version 8) but cannot run, so **Phase 19 visual acceptance is
blocked**. The **PARITY** build — which omits the 402-line P7-Z drawing
block — compiles clean at version 9, so all parity work is unblocked.

This needs either measured, provably semantics-neutral compaction, or an
author decision about what the USER build drops. It must **not** be resolved
by reverting a semantic correction to fit the budget.

## 6. Verification state

- Baseline before any change: **4660 passed / 0 failed** (11m25s).
- After both corrections: **4671 passed / 0 failed** (11m08s) — +11 lock tests.
- `test_rc3_pine_block_immutability.py`: 28 passed; the P6 block stays
  byte-identical and P6 remains **CLOSED**.
- RC1 sha256 `143c0f88…` and RC2 sha256 `381f2fc2…` both verified unchanged.
- Both RC3 builds are identical line-for-line on every corrected line.

## 7. Not done / still open

P5 and P8 live captures from the corrected build; the field-by-field
comparison of those against the independent Level-A authority; USER-build
token compaction and visual acceptance; RC3 semantic freeze. **RC3 is not
promotion-ready and has not been promoted.**

The sealed V1-A characterization summary, the OOS window, and the untracked
V1-A M5-materiality files remain unopened and unmodified.
