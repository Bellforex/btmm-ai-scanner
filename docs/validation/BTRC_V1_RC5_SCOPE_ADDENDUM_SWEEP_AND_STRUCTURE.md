# BTRC-V1 RC5 — SCOPE ADDENDUM: QUALIFIED SWEEPS + READABLE STRUCTURE

Author addendum, 2026-09-20, received mid-implementation. It **extends** the
RC5 campaign; it does not replace the POI-authority work already in progress.

Governing rule: **a sweep must be a sweep of meaningful liquidity.** Not every
local wick is a sweep.

## A. Qualified liquidity sweep (semantic, Python-first)

A user-facing SWEEP requires all three:

1. a **meaningful liquidity reference**,
2. **price penetration** of it,
3. **valid reclaim / sweep behaviour** (existing causal mechanics).

If the engine cannot name *what* was swept, **no sweep annotation and no sweep
event**.

Valid references — reuse existing structures, invent no new numeric importance
threshold before inspecting what the engine already scores:

* an active/major POI boundary
* a qualified SUPPORT or RESISTANCE zone
* confirmed trendline liquidity
* RANGE HIGH / RANGE LOW
* an external liquidity pool
* other already-qualified structural liquidity

A tiny internal swing is **not** automatically major liquidity.

Existing mechanics are preserved unless a bug is proven: wick through and
reclaim → sweep; close through then reclaim inside the authorised window →
sweep; close through with no valid reclaim → accepted break. These only
produce a **user-facing** sweep when the reference itself qualifies.

**This is not a presentation patch.** A semantically rejected sweep must not
reach BTMM, P5, P8, the backtest or the bot as a valid liquidity event.

### Sweep record metadata (compact; enums/IDs, not prose)
`side` (BSL/SSL) · `reference_kind` (POI / SR / TRENDLINE / RANGE / OTHER) ·
`reference identity` · `event host timeframe` · `event time`.

## B. Host-timeframe locality

A sweep event belongs to the **host timeframe it occurred on**.

* M15 chart → M15 sweeps only. Switch to M30/M45/H1/H4 → the M15 sweep
  annotations must be **gone**, and only sweeps the new host independently
  produces may appear.
* A **level** may legitimately persist as context across analysis. The **event
  that swept it** is host-local. Do not conflate the two.
* Pine object lifecycle: on host change, clear old sweep labels/markers and
  host-specific structure annotations, then rebuild from the current host bars.
* QA the transitions M15→M30, M15→M45, M15→H1, H1→H4 **and the reverse**;
  expect zero residue from the previous host.

## C. BTMM consequence

BTMM DIS/DEL/WIP definitions are **not** changed. But **DISTRACTION may no
longer be credited from a micro-wick that fails the qualified-sweep test**. The
RC5 qualified-sweep model feeds BTMM consistently.

## D. Student-facing market structure

Present **HH / HL / LH / LL** plus **BOS / CHOCH**, classified against the
previous qualified swing using existing causal confirmation — never before
confirmation, never with future information.

Internal `SH` / `SL` swing records **stay in the engine**; they simply are not
all printed. Separate *internal swing records* from *student-facing structure
annotations*.

Presentation: readable, high contrast, small but clearly visible, consistently
positioned. Not faint grey, not giant, not cluttered. The visible sequence must
not contradict itself (previous swing → new swing → classification → break →
BOS/CHOCH).

## E. Sweep annotation presentation

Prefer **`BSL SWEEP`** / **`SSL SWEEP`** over a bare `SWEEP` where the side is
unambiguous. Compact, dark enough to read on a white chart, not neon, visually
secondary to POI labels.

## F. Expanded host QA matrix

**M5, M15, M30, M45, H1, H3, H4.** For each: structure classification,
HH/HL/LH/LL rendering, BOS/CHOCH consistency, qualified sweep references, no
excessive SWEEP labels, no stale sweep or structure labels from the previous
host.

M5/M15 matter for scalping; H3/H4 for day trading; M30/M45/H1 are intermediate
diagnostic hosts.

## G. Live sweep forensic

For selected RC5 screenshots, record per visible sweep: host timeframe, event
time, BSL/SSL, reference kind, reference level, penetration, reclaim, why it
qualifies. **If no meaningful reference can be named for a visible SWEEP, that
sweep is a bug.**

## H. The disputed zone

The author's chart is still RC4, so the currently visible problematic zone and
sweep annotations are **not** RC5 failures. Do not patch RC4. When RC5 is
ready, revisit the same region and capture RC4 BEFORE / RC5 AFTER. If RC5
structural-origin / authority / lifecycle says the zone is not active, it must
not appear as an active POI.

## I. Updated RC5 closure gate

RC5 is not AUTHOR REVIEW READY until **all** of:

POI structural-origin corrections · same-origin authority · DOJI · active
terminal display corrected · qualified liquidity sweep logic · BTMM consuming
only qualified sweeps · host-timeframe sweep isolation proven · HH/HL/LH/LL
presentation · BOS/CHOCH consistent · annotations readable · Python/Pine parity
green · token reserve acceptable · all layers ON in TradingView.

## Status facts to keep true

BAH helper library **PUBLISHED** · RC4 USER v16 **on the author chart** · RC5
engine **in development** · RC5 USER **not final** · RC5 scanner **not
published** · vigorous backtest **not started** · scalping EA **not built** ·
day-trading EA **not built** · main merge **FALSE** · live broker **FALSE**.
