# BTRC V1 — RC3 POI qualification matrix (18 canonical types)

What each type needs to become a **mapped** P3 POI, with the authority for every
rule. "Detected" = frozen detector output (raw candidate, auditable). "Mapped" =
reaches the P3 registry, lifecycle, P5 and P8. Nothing here is invented: a cell
says **none** when no authority exists.

Authority keys: REG = `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`
(§35J–§35X), MS = `knowledge/MEASUREMENT_STANDARDS.md`, KB =
`knowledge/poi_rules/**`, RC3 = author decisions 2026-09-16/17
(`docs/validation/BTRC_V1_RC3_*.md`). Global: "Mandatory structural context: none"
for the POI families (REG §35S) — superseded for candle patterns by RC3 decision A (2026-09-17, structural context gate; Fibonacci / trendline / S/R / liquidity stay non-gating metadata); STANDARD/STRONG tiers are descriptive, never gates;
speed classification alone never approves or rejects (MS).

| type | raw geometry (detector) | availability | quality gate to map | same-origin role | context gate | authority / status |
|---|---|---|---|---|---|---|
| BUY / SELL ORDER BLOCK | adjacent pair, range ratio ≥ 2.0, opposite colours, close beyond origin extreme, no Doji (`poi/order_blocks.py`) | leg-confirming P2 break | leg origin: earliest raw formation on the extreme swing between broken swing and break (`poi/leg_origin.py`) | primary (always also an engulfing) | the leg-origin gate IS the structural rule | RC3 final lock; immutable once available |
| BUY / SELL FVG | strict 3-candle gap, wick-inclusive (`poi/fair_value_gaps.py`) | third candle close | **gap ≥ 0.35 × ATR-14 of the departure candle** (`poi/qualification.py`) | secondary: suppressed when a same-direction pattern ends on its departure candle | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | RC3 2026-09-17: 0.35 **FROZEN** (decision C); REG §35J expansion NOT adopted (it rejects both author examples) |
| B2S / S2B CANDLE | range ≥ 2.0 × max prev 3, body eff ≥ 0.60, close position ≥ 0.70, midpoint confirmation ≤ 3 bars | confirming close | frozen detector only | never an FVG arbiter (candidate colour is opposite to the POI direction) | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen; KB extra quality items unimplemented (gate report D5) |
| BASE RALLY / DROP | 2–6 base candles, small vs departure, height ≤ 0.75 ATR & ≤ 0.60 departure, drift ≤ 0.25, overlap ≥ 0.50, departure beyond base | departure close | frozen detector only | primary over an FVG departing from its departure candle | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen |
| BULLISH / BEARISH PRESSURE WICK | wick share ≥ 0.40, body eff ≥ 0.25, dominance 2×, close position ≥ 0.60 | own close | frozen detector only | primary over its own FVG (author H1 case); **suppressed by a same-candle HAMMER / SHOOTING STAR** (RC3 B) | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen + RC3 arbitration |
| BULLISH / BEARISH ENGULFING | pair, range ratio ≥ 2.0, opposite colours, no Doji; body coverage NOT required (classification B pending) | engulfing close | frozen detector; ends `PROMOTED_TO_ORDER_BLOCK` when its formation becomes an OB | primary over its own FVG | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen + RC3 |
| HAMMER / SHOOTING STAR | wick share ≥ 0.60, body eff ≤ 0.30, opposite wick ≤ 0.10 | own close | frozen detector only | primary over an FVG departing from it; **primary over the same-candle pressure wick** (RC3 B) | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen + RC3 B |
| MORNING / EVENING STAR | c1/c3 colours, c3 close beyond c1 midpoint, Doji middle ≤ 0.10 | third close | frozen detector only | primary over an FVG departing from its third candle | **structural gate (RC3 A)**: aligned at availability, or reversal context at the confirming break; else raw | frozen; c1-midpoint condition unsourced (gate report D4) |
| SUPPORT / RESISTANCE ZONE | measurement S/R zone 1:1 (origin swing + reacted touch) | zone availability (backfill contract be1df56) | measurement reaction gates | not an FVG arbiter | swing-based by construction | frozen + RC3: **immutable once confirmed** (`poi/confirmed_zones.py`) |

Shared lifecycle for all 18 (REG §35T–§35V + RC3 freshness): first touch after
availability ⇒ MITIGATED; genuine invalidation final; earliest terminal cause wins;
no expiry.

## Author decisions applied 2026-09-17 (freeze campaign)

1. **A — structural context gate** for FVG, B2S/S2B, BASE, PRESSURE WICK,
   ENGULFING, HAMMER/SHOOTING STAR, MORNING/EVENING STAR
   (`BTRC_V1_RC3_CONTEXT_AWARE_POI_ENGINE.md`). ORDER BLOCK and S/R ZONE are
   structural by contract and not re-gated.
2. **B — HAMMER > same-candle BULLISH PRESSURE WICK, SHOOTING STAR > same-candle
   BEARISH PRESSURE WICK**; every other non-FVG pair kept
   (`docs/validation/BTRC_V1_RC3_NON_FVG_ARBITRATION_MATRIX.md`).
3. **C — FVG gap ≥ 0.35 × ATR-14 (departure candle) frozen**; no other FVG
   threshold; displacement metrics diagnostic only.

## Still open (not implemented)

* Engulfing body coverage (classification B), star c1-midpoint condition,
  morning/evening star c3 ratio.
