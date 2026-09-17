# BTRC V1 — RC3 POI qualification matrix (18 canonical types)

What each type needs to become a **mapped** P3 POI, with the authority for every
rule. "Detected" = frozen detector output (raw candidate, auditable). "Mapped" =
reaches the P3 registry, lifecycle, P5 and P8. Nothing here is invented: a cell
says **none** when no authority exists.

Authority keys: REG = `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`
(§35J–§35X), MS = `knowledge/MEASUREMENT_STANDARDS.md`, KB =
`knowledge/poi_rules/**`, RC3 = author decisions 2026-09-16/17
(`docs/validation/BTRC_V1_RC3_*.md`). Global: "Mandatory structural context: none"
for the POI families (REG §35S); STANDARD/STRONG tiers are descriptive, never gates;
speed classification alone never approves or rejects (MS).

| type | raw geometry (detector) | availability | quality gate to map | same-origin role | context gate | authority / status |
|---|---|---|---|---|---|---|
| BUY / SELL ORDER BLOCK | adjacent pair, range ratio ≥ 2.0, opposite colours, close beyond origin extreme, no Doji (`poi/order_blocks.py`) | leg-confirming P2 break | leg origin: earliest raw formation on the extreme swing between broken swing and break (`poi/leg_origin.py`) | primary (always also an engulfing) | the leg-origin gate IS the structural rule | RC3 final lock; immutable once available |
| BUY / SELL FVG | strict 3-candle gap, wick-inclusive (`poi/fair_value_gaps.py`) | third candle close | **gap ≥ 0.35 × ATR-14 of the departure candle** (`poi/qualification.py`) | secondary: suppressed when a same-direction pattern ends on its departure candle | none (REG §35J: no structure gate) | RC3 2026-09-17 author choice; REG §35J middle-candle expansion measured, not adopted |
| B2S / S2B CANDLE | range ≥ 2.0 × max prev 3, body eff ≥ 0.60, close position ≥ 0.70, midpoint confirmation ≤ 3 bars | confirming close | frozen detector only | never an FVG arbiter (candidate colour is opposite to the POI direction) | "existing trend" stated, **not automated** (REG §35M) | frozen; KB extra quality items unimplemented (gate report D5) |
| BASE RALLY / DROP | 2–6 base candles, small vs departure, height ≤ 0.75 ATR & ≤ 0.60 departure, drift ≤ 0.25, overlap ≥ 0.50, departure beyond base | departure close | frozen detector only | primary over an FVG departing from its departure candle | "after a strong move" stated, not automated | frozen |
| BULLISH / BEARISH PRESSURE WICK | wick share ≥ 0.40, body eff ≥ 0.25, dominance 2×, close position ≥ 0.60 | own close | frozen detector only | primary over its own FVG (author H1 case) | liquidity narrative only | frozen + RC3 arbitration |
| BULLISH / BEARISH ENGULFING | pair, range ratio ≥ 2.0, opposite colours, no Doji; body coverage NOT required (classification B pending) | engulfing close | frozen detector; ends `PROMOTED_TO_ORDER_BLOCK` when its formation becomes an OB | primary over its own FVG | "within an existing move" qualitative, not a gate | frozen + RC3 |
| HAMMER / SHOOTING STAR | wick share ≥ 0.60, body eff ≤ 0.30, opposite wick ≤ 0.10 | own close | frozen detector only | primary over an FVG departing from it | "around support" qualitative | frozen; coexists with pressure wick (never merged) |
| MORNING / EVENING STAR | c1/c3 colours, c3 close beyond c1 midpoint, Doji middle ≤ 0.10 | third close | frozen detector only | primary over an FVG departing from its third candle | "around demand/support" descriptive | frozen; c1-midpoint condition unsourced (gate report D4) |
| SUPPORT / RESISTANCE ZONE | measurement S/R zone 1:1 (origin swing + reacted touch) | zone availability (backfill contract be1df56) | measurement reaction gates | not an FVG arbiter | swing-based by construction | frozen + RC3: **immutable once confirmed** (`poi/confirmed_zones.py`) |

Shared lifecycle for all 18 (REG §35T–§35V + RC3 freshness): first touch after
availability ⇒ MITIGATED; genuine invalidation final; earliest terminal cause wins;
no expiry.

## Open author decisions (not implemented, evidence available)

1. Context gates (trend alignment, impulse/correction role, retracement band,
   S/R / liquidity / trendline confluence): measured in
   `BTRC_V1_RC3_MARKET_CONTEXT_AUDIT.md`, no authority to gate.
2. Non-FVG same-origin conflicts (e.g. pressure wick + hammer on one candle,
   engulfing + pressure wick): authority says "preserved separately, never
   merged" (REG §35L / KB); presentation merges exact-geometry boxes.
3. FVG minimum-gap threshold value 0.35 is an author choice from a
   two-example calibration; revisit with more labelled examples.
4. Engulfing body coverage (classification B), star c1-midpoint condition,
   morning/evening star c3 ratio.
