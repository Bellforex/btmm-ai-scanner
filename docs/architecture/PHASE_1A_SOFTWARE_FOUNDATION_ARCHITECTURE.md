# Phase 1A — Software-Foundation Architecture

**Document status:** ENGINEERING-RECOMMENDED planning document. No item in this document is implemented. No technology has been installed or configured. Every architecture and technology decision below carries an explicit governance label and, where applicable, an "Author approval required" flag. Nothing here overrides, redefines, or supersedes any Phase 0G trading-rule content.

---

## 1. Purpose

This document defines the proposed software-foundation architecture for the BTMM AI Scanner project, prior to any implementation. Its purpose is to give the author a single place to review and approve (or reject/amend) the structural decisions that must be settled before Phase 1B (repository scaffold creation) can begin. It is a planning artifact only.

## 2. Phase 0G Baseline Dependency

This plan depends entirely on the Phase 0G controlled baseline approved in commit `23f43676abf6e032a5e96c4077d230cc2283f9b6`:

- Phase 0G status: **AUTHOR-APPROVED CONTROLLED BASELINE**.
- Knowledge Gate status: **OPEN FOR CONTROLLED FOUNDATION WORK** (not "OPEN" unconditionally — foundation/annotation-infrastructure work only).
- Historical identified blockers: **21**. Active unresolved blockers: **15**. Active P0 blockers: **0**. Minimum Phase 0G closure set: **EMPTY**.
- Condition 3 = **NOT MET**; Condition 4 = **MET**; Condition 7 = **PARTIALLY MET** (non-passing). All 36 POI specifications remain `Status: PARTIAL`. Eighteen bounded directional POIs remain propagated under the shared lifecycle standard.
- Every deferred limitation recorded in `knowledge/FINAL_PHASE_0G_KNOWLEDGE_GAP_AUDIT.md` remains binding on this architecture: mitigation/degradation are undefined; Equal High/Low and Trendline specialized lifecycles are formally deferred; HH/HL/LH/LL/BOS/CHoCH are formally deferred and undefined; automatic trend/market-structure detection is deferred; empirical calibration and out-of-sample validation are outstanding for every provisional standard; entry/risk rules are deferred.

This architecture must be built so that none of these open items are silently assumed, hard-coded, or foreclosed — every module boundary below is drawn specifically so that later resolution of any Phase 0G-deferred item does not require re-architecting the foundation.

## 3. Scope

In scope for Phase 1A: architecture planning documents only — logical layering, module boundaries, data flow, data-contract shapes (documentation, not executable schemas), identity policy, provenance/validation/audit strategy, deterministic-testing strategy, a technology-stack decision register, a versioning plan, and the Phase 1B entry-gate list.

## 4. Explicit Non-Scope

Not in scope for Phase 1A, and not performed by this document: writing application code; creating the repository scaffold; implementing schemas (executable/validated); implementing POI detectors; implementing data ingestion; implementing a database; implementing AI/ML components; implementing signals; implementing entry, stop-loss, take-profit, position-sizing, or risk logic; implementing Telegram, MT4, MT5, or web-platform integrations; installing or configuring any tool, dependency, or CI system; approving a final technology stack (this document only recommends).

## 5. Architecture Principles

1. **Immutability of raw evidence.** Once a raw record is captured, it is never mutated — corrections happen by creating a new, versioned record, never by overwriting history.
2. **Determinism.** Given the same raw inputs, rule versions, and schema versions, every derived output must be exactly reproducible.
3. **Non-repainting.** No derived value may be exposed to downstream consumers, backtests, or replay before its own approved availability time (this mirrors the Phase 0G non-repainting principle already established for POIs, swings, and trendlines).
4. **Separation over convenience.** Every concept the Phase 0G knowledge base treats as separate (see SS6) must remain separate in code — no shortcut may merge them for implementation convenience.
5. **Provenance is mandatory, not optional.** Every record must be traceable to its source (raw feed, rule version, schema version, and — for manual evidence — the reviewer).
6. **No premature commitment.** Where Phase 0G left a rule deferred (freshness thresholds, mitigation, Equal High/Low sweep, Trendline final invalidation, HH/HL/LH/LL/BOS/CHoCH), the architecture must have an explicit extension point, not a hard-coded assumption.
7. **Foundation before intelligence.** No AI, detector, or execution logic is built before the data contracts, provenance, and validation layers exist and are stable.

## 6. Separation of Concerns

Per `docs/PROJECT_SCOPE.md` SS7 and every Phase 0G standard, the following remain structurally distinct domain concepts, each requiring its own record type and its own identity (detailed in the Data-Contract Plan):

| Concept | Must never be merged with |
|---|---|
| Raw market data | Normalized market data |
| Normalized market data | Derived measurements |
| Derived measurements | POI detection |
| POI detection | POI validity |
| POI validity | POI lifecycle |
| POI lifecycle | BTMM validity |
| BTMM validity | Entry validity |
| Entry validity | Trade outcome |
| Manual expert evidence | Automatic detector evidence |
| Automatic detector evidence | AI-generated evidence |

**Label: AUTHOR-APPROVED** (this separation is a direct, literal restatement of Phase 0G's own already-approved principle — not a new decision).

## 7. Proposed Logical Layers

Sixteen layers are proposed. For each: responsibility, permitted/prohibited dependencies, inputs/outputs, versioning needs, audit requirements, and Phase 1A/1B permission status.

### 7.1 Configuration Layer
- **Responsibility:** Holds symbol/provider/timeframe enums, environment settings, and references to the currently active rule/schema versions. Does not hold trading rules themselves (those live in `knowledge/` and, later, in the Rule-Version Manifest).
- **Permitted dependencies:** none (lowest layer).
- **Prohibited dependencies:** must never depend on Domain, POI, or Lifecycle layers.
- **Inputs:** operator-provided config files/environment.
- **Outputs:** resolved configuration objects consumed by every other layer.
- **Versioning:** its own config-schema version.
- **Audit:** every config load is an audit event (who/when/which version).
- **Permitted in controlled foundation work:** Yes (planning/schema only, no secrets).

### 7.2 Market-Data Contracts Layer
- **Responsibility:** Defines the shape of Raw Candle, Normalized Candle, and their metadata (documentation-level in Phase 1A; executable in Phase 1B+).
- **Permitted dependencies:** Configuration Layer.
- **Prohibited dependencies:** must never depend on POI, Lifecycle, BTMM, or any higher layer.
- **Inputs:** none (pure contract definitions).
- **Outputs:** type/schema definitions consumed by Ingestion and Normalization.
- **Versioning:** Schema Version Manifest entry per contract.
- **Audit:** schema changes are audited/versioned, never silently edited.
- **Permitted in controlled foundation work:** Yes.

### 7.3 Raw Data Ingestion Boundary
- **Responsibility:** Accepts market data from an external source and writes it, unmodified, as an immutable Raw Candle Record. Performs no interpretation, no cleaning, no gap-filling.
- **Permitted dependencies:** Market-Data Contracts Layer, Configuration Layer.
- **Prohibited dependencies:** must never depend on Normalization, Measurement, POI, Lifecycle, BTMM, or any detector/AI/execution layer. **Ingestion code must never decide POI validity.**
- **Inputs:** external feed (provider TBD — no data-provider API is approved or implemented by this document).
- **Outputs:** immutable Raw Candle Records with full source metadata.
- **Versioning:** raw-data version tag per capture batch.
- **Audit:** every ingested batch is an audit event; retrieval time, retrieval method, and feed identity are recorded.
- **Permitted in controlled foundation work:** Planning only — no live adapter is implemented in Phase 1A/1B per this document.

### 7.4 Normalization Layer
- **Responsibility:** Converts Raw Candle Records into Normalized Candle Records (canonical timezone, canonical OHLC ordering, confirmed-candle flagging). Never mutates the raw record.
- **Permitted dependencies:** Market-Data Contracts Layer, Configuration Layer, Raw Data Ingestion Boundary (read-only).
- **Prohibited dependencies:** must never depend on POI, Lifecycle, BTMM, AI, or execution layers.
- **Inputs:** Raw Candle Records.
- **Outputs:** Normalized Candle Records, each referencing its raw source record ID.
- **Versioning:** normalization-version tag, independent of raw-data version.
- **Audit:** every normalization run is an audit event; reproducible from raw + normalization version.
- **Permitted in controlled foundation work:** Yes (contract/logic planning only).

### 7.5 Measurement Layer
- **Responsibility:** Computes the already-approved Phase 0G measurement formulas (Candle Measurement Standard V1, Small Candle Standard V1, Volume/Momentum Proxy Standard V1, Market Speed Standard V1, POI Zone Interaction Standard V1, etc.) from Normalized Candle Records — nothing beyond what `knowledge/MEASUREMENT_STANDARDS.md` already defines.
- **Permitted dependencies:** Normalization Layer (read-only), Configuration Layer.
- **Prohibited dependencies:** must never depend on POI, Lifecycle, BTMM, AI, or execution layers; must never invent a new formula not already Author-Approved in `knowledge/MEASUREMENT_STANDARDS.md`.
- **Inputs:** Normalized Candle Records.
- **Outputs:** Derived Candle Measurement Records.
- **Versioning:** tied to the specific Measurement-Standard version it implements.
- **Audit:** every measurement is traceable to its formula version.
- **Permitted in controlled foundation work:** Yes (documentation/contract only).

### 7.6 Domain Entity Layer
- **Responsibility:** Represents Meaningful Swings, Trendline candidates, Support/Resistance zones — the structural entities defined in Phase 0G, built from Measurement Layer outputs.
- **Permitted dependencies:** Measurement Layer, Configuration Layer.
- **Prohibited dependencies:** must never depend on POI Lifecycle, BTMM, AI, or execution layers; must never implement HH/HL/LH/LL/BOS/CHoCH (formally deferred, `P0G-B003`) or an Equal High/Low or Trendline specialized automated lifecycle (formally deferred, `P0G-B004`/`P0G-B005`).
- **Inputs:** Derived Candle Measurement Records.
- **Outputs:** Swing/Trendline/Support/Resistance domain records.
- **Versioning:** tied to the Meaningful Swing / Trendline / Support-Resistance standard versions.
- **Audit:** every domain-entity confirmation is an audit event with non-repainting availability time.
- **Permitted in controlled foundation work:** Yes (documentation/contract only).

### 7.7 POI and Lifecycle Event Layer
- **Responsibility:** Represents the 36 POI types and, for the 18 propagated POIs, the shared Boundary Breach/Reclaim/Invalidation lifecycle events; for Equal Highs/Lows and Trendlines, only the already-approved geometry/strength — **not** an automated specialized lifecycle (deferred).
- **Permitted dependencies:** Domain Entity Layer, Measurement Layer, Configuration Layer.
- **Prohibited dependencies:** must never depend on BTMM, AI, Signal, or Execution layers. **POI detectors must never place trades.**
- **Inputs:** Domain entities, Derived Candle Measurement Records.
- **Outputs:** POI Records, POI Interaction Events, POI Lifecycle Events.
- **Versioning:** tied to the specific POI-specification version (per-POI, since each of the 36 POIs has its own approval history).
- **Audit:** every POI creation/interaction/lifecycle transition is an audit event; `poi_id` never reused.
- **Permitted in controlled foundation work:** Yes (documentation/contract only).

### 7.8 Manual Annotation Layer
- **Responsibility:** Captures reviewed human/expert labels — `context_direction`/`context_alignment`, `liquidity_event_source = MANUAL_EXPERT_LABEL`, `trendline_event_source = MANUAL_EXPERT_LABEL` — exactly as already defined in `knowledge/btmm/BTMM_STATE_MACHINE.md`'s "Phase 0G Input-Source Policy."
- **Permitted dependencies:** Domain Entity Layer, POI Layer, Configuration Layer.
- **Prohibited dependencies:** must never depend on AI or Execution layers. **Manual labels must never be represented as automatic detection** — this is a hard architectural rule, not a style preference.
- **Inputs:** human reviewer input.
- **Outputs:** Manual Expert Context/Liquidity-Event/Trendline-Event Label records, each tagged with its reviewer and source.
- **Versioning:** annotation-guideline version.
- **Audit:** every label is an audit event recording reviewer identity, timestamp, and guideline version.
- **Permitted in controlled foundation work:** Yes — this is one of the explicitly permitted controlled-foundation categories.

### 7.9 Provenance Layer
- **Responsibility:** Cross-cutting; records the lineage of every record in every other layer (raw → normalized → derived → domain → POI → lifecycle → annotation).
- **Permitted dependencies:** may be depended upon by every layer above Configuration; itself depends only on Configuration.
- **Prohibited dependencies:** must never depend on any layer it serves (no circular dependency).
- **Inputs:** lineage references emitted by every other layer.
- **Outputs:** Provenance Records.
- **Versioning:** its own schema version.
- **Audit:** is itself part of the audit mechanism.
- **Permitted in controlled foundation work:** Yes — explicitly permitted.

### 7.10 Validation Layer
- **Responsibility:** Cross-cutting; checks OHLC consistency, timeframe/provider/symbol correctness, timestamp/timezone sanity, duplicate/missing/out-of-order candle detection, and schema conformance at each layer boundary.
- **Permitted dependencies:** Configuration Layer, Market-Data Contracts Layer.
- **Prohibited dependencies:** must never itself decide POI or BTMM validity — data-quality validation and trading validity are different concepts (see the Provenance/Validation/Audit Plan).
- **Inputs:** records from every layer.
- **Outputs:** Validation Result records (pass/fail/quarantine).
- **Versioning:** its own validation-rule version.
- **Audit:** every validation failure is an audit event.
- **Permitted in controlled foundation work:** Yes — explicitly permitted.

### 7.11 Historical Replay Layer
- **Responsibility:** Re-runs the full pipeline (ingestion → normalization → measurement → domain → POI → lifecycle) against historical raw data, using pinned rule/schema versions, to reproduce past outputs exactly.
- **Permitted dependencies:** every layer through POI/Lifecycle; read-only.
- **Prohibited dependencies:** must never write back into live/raw records (no retroactive rewriting, matching the Phase 0G non-repainting principle).
- **Inputs:** Raw Candle Records, pinned rule/schema versions.
- **Outputs:** Historical Replay Run records.
- **Versioning:** replay-engine version, plus the pinned versions it replays against.
- **Audit:** every replay run is itself an audited, reproducible event.
- **Permitted in controlled foundation work:** Yes — explicitly permitted ("historical replay preparation").

### 7.12 Deterministic Fixture Layer
- **Responsibility:** Holds synthetic, hand-constructed candle sequences (positive/negative/near-miss/boundary/ambiguous) used to test every layer above deterministically, without depending on live or historical data.
- **Permitted dependencies:** Market-Data Contracts Layer only.
- **Prohibited dependencies:** must never contain private-book content or be presented as market-performance evidence.
- **Inputs:** none (hand-authored).
- **Outputs:** fixture datasets consumed by the Testing Layer.
- **Versioning:** fixture-set version.
- **Audit:** fixture provenance (who authored it, against which rule version) is tracked.
- **Permitted in controlled foundation work:** Yes — explicitly permitted.

### 7.13 Audit and Reporting Layer
- **Responsibility:** Aggregates audit events from every layer into queryable, human-reviewable reports.
- **Permitted dependencies:** Provenance Layer, Validation Layer.
- **Prohibited dependencies:** must never itself generate trading signals.
- **Inputs:** audit events.
- **Outputs:** audit reports.
- **Versioning:** its own report-schema version.
- **Audit:** self-referential — its own report generation is logged.
- **Permitted in controlled foundation work:** Yes — explicitly permitted.

### 7.14 Future Detector Interface Layer
- **Responsibility:** A stable interface boundary that a future automatic detector (e.g., an eventual automated Equal High/Low sweep detector, once `P0G-B004` is resolved) would implement, without existing itself yet.
- **Permitted dependencies:** POI and Lifecycle Layer contracts only (interface, not implementation).
- **Prohibited dependencies:** no implementation exists; nothing may depend on it as a working component yet.
- **Inputs/Outputs:** interface signatures only.
- **Versioning:** interface-version, independent of any future implementation.
- **Audit:** N/A until implemented.
- **Permitted in controlled foundation work:** Interface/contract definition only — no implementation. **Automatic Equal High/Low sweep detection and automatic Trendline final-break detection remain explicitly prohibited until their respective Phase 0G blockers (`P0G-B004`, `P0G-B005`) are resolved.**

### 7.15 Future AI Interface Layer
- **Responsibility:** A stable interface boundary for a future AI/ML module to consume POI/Lifecycle/Annotation records as read-only evidence, without the AI module existing yet.
- **Permitted dependencies:** POI, Lifecycle, Annotation, Provenance layers — read-only, via interface only.
- **Prohibited dependencies:** **AI modules must never modify raw data, normalized data, or any record produced by an earlier layer in the Section 9 data-flow order (raw, normalized, measurement, domain, POI, or lifecycle records).** No AI component may be coupled directly into the foundation's write path.
- **Inputs/Outputs:** interface signatures only.
- **Versioning:** model-version placeholder for future use.
- **Audit:** N/A until implemented.
- **Permitted in controlled foundation work:** Interface/contract definition only — no implementation, no training, no model.

### 7.16 Future Signal and Execution Boundary
- **Responsibility:** A stable, isolated boundary where a future signal/execution system (Telegram, MT4, MT5, web platform) would eventually connect — entirely unimplemented.
- **Permitted dependencies:** BTMM validity records (read-only, once BTMM evaluation exists) — via interface only.
- **Prohibited dependencies:** **entry logic must never redefine POI validity; trade outcome must never retroactively change setup validity; future execution adapters must never bypass risk controls.**
- **Inputs/Outputs:** interface signatures only.
- **Versioning:** N/A until implemented.
- **Audit:** N/A until implemented.
- **Permitted in controlled foundation work:** Boundary/interface documentation only — **no implementation of Telegram, MT4, MT5, web-platform integration, or any execution logic.**

**Future Risk-Control Interface (a deferred sub-boundary within this layer, not a 17th logical layer):**
- No execution adapter of any kind may be implemented or activated before a separate risk-control contract is explicitly author-approved.
- Any future execution component must depend on that approved risk-control interface; it must never bypass it by calling `btmm`/`poi` directly (matching the identical prohibition already stated in `REPOSITORY_SCAFFOLD_PLAN.md`'s "Explicitly Prevented Couplings").
- The risk-control interface itself remains entirely unimplemented and out of scope for Phase 1A and Phase 1B.
- Entry, stop-loss, take-profit, position-sizing, and risk rules all remain undefined — this sub-boundary does not define any of them; it only reserves the place they would eventually occupy.
- In any diagram, this sub-boundary is shown only as an isolated, deferred prerequisite — never connected to an active execution path, since no execution path exists.

## 8. Proposed Module Boundaries

**Correction note:** an earlier version of this section used "downward"/"upward" language that could be read inconsistently against this document's own Section 7 ordering. This is now corrected to avoid directional prose entirely, using the same **dependency** vocabulary defined in `docs/architecture/REPOSITORY_SCAFFOLD_PLAN.md`'s "Dependency-Direction Diagram" (SS4): **`A depends on B`** means A's module is permitted to call/import B's module.

Module boundaries mirror the 16 layers above 1:1. A module is permitted to depend on (call/import) only: (a) the specific other modules explicitly named in that layer's "Permitted dependencies" field in Section 7 above, or (b) the cross-cutting Provenance/Validation interfaces. **No module may be depended upon by a module that its own permitted-dependency list does not, directly or transitively, reach** — i.e., dependency is a strict partial order with no cycles, detailed with a full adjacency list and topological order in `docs/architecture/REPOSITORY_SCAFFOLD_PLAN.md`, SS4. Note that "depends on" is the **reverse** of the runtime data-flow direction described in Section 9 below — e.g., the Normalization Layer *depends on* the Raw Ingestion Boundary (it reads ingestion's output), while *data flows* from Ingestion to Normalization. Both statements describe the same relationship from two different, equally valid perspectives; neither section's arrows should be read as meaning the other section's concept.

## 9. Runtime Data-Flow Diagram

**Arrow legend for this diagram only: `A → B` means "data produced by A flows into B" (a runtime data-movement relationship).** This is the opposite direction from the "depends on" relationship used in Section 8 above and in `docs/architecture/REPOSITORY_SCAFFOLD_PLAN.md`'s Dependency-Direction Diagram — see Section 8's clarifying note for the exact correspondence. Do not read this diagram's arrows as dependency/import relationships.

```
External market source (provider/API NOT approved or implemented by this document)
        │
        ▼
Raw Ingestion Boundary  ──────────────► [Immutable Raw Candle Records]
        │
        ▼
Normalization Layer ───────────────────► [Normalized Candle Records]
        │
        ▼
Validation Layer (cross-cutting; may reject/quarantine at this or any later stage)
        │
        ▼
Measurement Layer ─────────────────────► [Derived Candle Measurement Records]
        │
        ▼
Domain Entity Layer (Swings, Trendlines, Support/Resistance)
        │
        ▼
POI and Structural Processing (POI and Lifecycle Event Layer)
        │
        ▼
Lifecycle Events (Boundary Breach / Reclaim / Invalidation, 18 propagated POIs only)
        │
        ├──────────────► Manual Annotation Layer (independent input path — reviewed human labels)
        │
        ▼
BTMM Evaluation (future — not implemented in Phase 1A/1B; consumes POI + Lifecycle + Manual Annotation)
        │
        ▼
Historical Replay and Audit (read-only over all of the above; reproducible via pinned versions)


        ┌─────────────────────────── FUTURE, ISOLATED, NOT IMPLEMENTED ───────────────────────────┐
        │   AI Model  │  Telegram  │  MT5  │  MT4  │  Web Platform  │  Live Execution              │
        │   (read-only interface consumption only — no write path into the foundation above)       │
        └────────────────────────────────────────────────────────────────────────────────────────┘
```

**Label: ENGINEERING-RECOMMENDED.** The overall left-to-right flow and the isolation of future systems is a direct restatement of Phase 0G's own approved concept separation; the specific box names and interface boundaries are engineering proposals requiring author review.

## 10. Evidence-Source Separation

Every record that can carry evidence must carry an explicit, visible source tag, matching the Phase 0G-approved vocabulary:

| Source tag | Meaning | Approved in |
|---|---|---|
| `context_input_source = MANUAL_EXPERT_LABEL` | Reviewed manual/expert context | `P0G-B002` |
| `liquidity_event_source = MANUAL_EXPERT_LABEL` | Reviewed manual Equal High/Low liquidity evidence | `P0G-B004` |
| `trendline_event_source = MANUAL_EXPERT_LABEL` | Reviewed manual Trendline evidence | `P0G-B005` |
| `liquidity_evidence_source` (`EXPERT_LABELLED`/`RULE_BASED`/`MODEL_PROPOSED`/`HYBRID_REVIEWED`/`RULE_BASED_REVIEWED`) | BTMM Liquidity Gate evidence source | Ambiguity 15 |

A future automatic-detector source tag and a future AI-generated source tag must be added to this table only when their respective components are actually approved and implemented — placeholders are not created by this document. **No record may ever be represented as automatically detected if its source tag says `MANUAL_EXPERT_LABEL`, and vice versa.**

## 11. Rule and Schema Versioning

See Part 9 (Versioning Plan) below for the full proposal. Summary principle: every rule (POI spec, lifecycle standard, measurement standard) and every schema (data contract) carries its own independent version identifier. A record always references the exact version(s) used to produce it. Historical records are never reinterpreted under a newer version without an explicit new record.

## 12. Immutability Requirements

Raw Candle Records are immutable once written. Normalized Candle Records are immutable once written (a re-normalization creates a new version, not an edit). POI/Lifecycle event history is append-only (matches the already-approved non-repainting/no-retroactive-rewriting rules in `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md`). Manual annotations, once submitted by a reviewer, are immutable — a correction is a new, superseding annotation record, never an edit of the old one.

## 13. Determinism Requirements

Given identical raw inputs and identical pinned rule/schema versions, every layer's output must be byte-for-byte reproducible. This is the technical prerequisite for the Historical Replay Layer and for empirical calibration work later (`P0G-B008`, `P0G-B012`, `P0G-B015`, `P0G-B020`) — those calibration efforts cannot be trusted if the underlying pipeline is non-deterministic.

## 14. Provider and Symbol Normalization

Canonical symbols (already Author-Approved in `docs/PROJECT_SCOPE.md`): `FXCM:XAUUSD`, `FXCM:EURUSD`, `FXCM:GBPUSD`. Canonical data principle: **FXCM data as displayed through TradingView is the approved visual and market-data reference** — this document does **not** claim any TradingView data API has been approved or implemented; it only affirms TradingView-displayed FXCM data as the reference for correctness comparison. Every raw record must carry: provider, feed, symbol, timeframe, timestamp, timezone, retrieval method, retrieval time, raw-data version, normalization version. **Label: AUTHOR-APPROVED** for the symbol/provider list itself (from `docs/PROJECT_SCOPE.md`); **REQUIRES AUTHOR DECISION** for the actual data-retrieval mechanism/API, which is not chosen here.

## 15. Timeframe Support

All of the following timeframes must be representable and must never be silently excluded: **H3, H4, D1, W1** (Strong POI context); **H1, M15** (Market-structure breakdown); **M15, M5, M1** (BTMM formation/execution). M15 intentionally appears in two roles (market-structure breakdown and BTMM execution) — the architecture must support a single timeframe serving multiple analytical roles without duplication. **Label: AUTHOR-APPROVED** (timeframe list, from `docs/PROJECT_SCOPE.md`); the enum/representation mechanism itself is **ENGINEERING-PROVISIONAL**.

## 16. Time-Zone Policy

A single canonical timezone must be chosen for all normalized/derived records, with the original source timezone preserved in the raw record for audit purposes. **Label: REQUIRES AUTHOR DECISION** — no specific timezone (e.g., UTC, exchange-local, broker-server-time) is chosen by this document.

**None of the following candle-time and calendar semantics are approved facts — every one is an engineering proposal or an open question, not yet decided:**

| Item | Status |
|---|---|
| Candle `event_time` represents candle-open time | ENGINEERING-PROVISIONAL |
| Candle `availability_time` represents confirmed candle-close or provider-confirmation time | ENGINEERING-PROVISIONAL |
| Canonical storage may use UTC while preserving source-timezone metadata | ENGINEERING-PROVISIONAL |
| Exact candle-close timestamp convention (e.g., inclusive/exclusive boundary) | REQUIRES AUTHOR DECISION |
| Daylight-saving-time (DST) normalization | REQUIRES AUTHOR DECISION |
| Trading-day boundary | REQUIRES AUTHOR DECISION |
| Week-start convention | REQUIRES AUTHOR DECISION |
| Month-boundary handling | REQUIRES AUTHOR DECISION |
| Provider-session handling | REQUIRES AUTHOR DECISION |

None of these items resolves the pre-existing, still-open Phase 0G period-rollover question (`P0G-B013A`'s discussion of "rollover/expiration timing for when a 'current' period level becomes a 'previous' period level") — that question remains explicitly unresolved and is not addressed by this section. **This document does not claim that a TradingView data API is available, approved, or implemented** — the Canonical Data Principle (Section 14) affirms only that FXCM data as *displayed through* TradingView is the visual/reference standard, not that any retrieval API exists.

## 17. Validation Strategy

See `docs/architecture/PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md` for the full plan (including its own expanded "Validation Eligibility Gating" section). Summary: validation occurs at every layer boundary (contract conformance), plus dedicated checks for OHLC consistency, duplicate/missing/out-of-order candles, and provider/symbol/timeframe correctness. Numeric tolerances for "acceptable" data anomalies are not chosen here (see that document's threshold labels).

**Explicit processing-eligibility sequence** (governing principle: **a record must not enter Normalization or Measurement merely because it exists — eligibility to proceed must be established by an explicit upstream Validation Result, not by mere presence**):

1. Preserve the received raw payload immutably.
2. Perform source-envelope and contract checks (does the payload match the expected raw shape?).
3. Produce a traceable Validation Result for that payload.
4. Quarantine any record with an unresolved or disqualifying data-quality failure — it does not proceed past this step.
5. Normalize only records the Validation Result explicitly marks eligible for normalization.
6. Validate the resulting Normalized Candle Record.
7. Perform sequencing and cross-record validation (ordering, duplicate, provider/symbol/timeframe checks).
8. Generate Derived Candle Measurement Records only from records explicitly eligible for measurement processing (i.e., that passed steps 5-7).

**Confirmed, restated explicitly:** quarantined records remain preserved (never deleted); no silent repair occurs; raw data is never overwritten; a data-quality rejection is never treated as a POI or BTMM invalidation (those remain separate concepts entirely); Measurement cannot be generated from a record still carrying an unresolved `QUARANTINED` status. **The exact validation-status enum and the specific gating implementation are not defined by this document — both are `REQUIRES AUTHOR DECISION`.**

## 18. Audit Strategy

See `docs/architecture/PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md`. Summary: every layer emits audit events; the Audit and Reporting Layer aggregates them; every audit event is itself immutable and versioned.

## 19. Error-Handling Philosophy

Data-quality failures (malformed source data, missing candles, invalid timestamps) are quarantined, not silently dropped or silently repaired — they become Validation Result records with `status = QUARANTINED`, reviewable by a human. Trading-rule ambiguities (e.g., an undefined Phase 0G item) are never resolved by software default — the architecture must refuse to silently invent a rule Phase 0G has not approved. **Label: ENGINEERING-RECOMMENDED.**

## 20. Logging and Observability Planning

Structured, versioned logging is recommended for every layer boundary (input received, output produced, validation result). No specific logging library or log-aggregation platform is chosen here (see Part 7, Technology-Stack Decision Register). **Label: ENGINEERING-PROVISIONAL.**

## 21. Security and Private-Source Protections

The private source book (`references/private/BTMM_AND_POI_TRADING_BIBLE.docx`) must never enter any application package, fixture, test, log, or commit. **Two distinct claims are separated here, each with its own evidence label:**
- The underlying protection itself — that the private book must remain excluded from version control — is the pre-existing `.gitignore` entry (`references/private/*`), already in force throughout this entire project. **Label: AUTHOR-APPROVED** (this is the existing, already-approved safeguard; no new decision is made here).
- Extending that protection into a *new, broader runtime rule* — "no layer may read from `references/private/` at runtime, and no fixture may embed book excerpts or screenshots" — is a **new architectural proposal** built on top of the approved safeguard, not itself a separately author-approved rule. **Label: ENGINEERING-RECOMMENDED.**

Secrets (API keys, credentials) are out of scope for Phase 1A and must never be committed in plain text; a secrets-management approach is a Phase 1B decision gate (Part 10). **Label: REQUIRES AUTHOR DECISION** (the specific secrets-management mechanism).

## 22. Testing Architecture

See `docs/architecture/DETERMINISTIC_TESTING_AND_FIXTURE_PLAN.md` for the full plan. Summary: every layer has its own deterministic test category, all fixture-based (no dependency on live or historical data for unit-level tests), plus a separate historical-replay-determinism test category.

## 23. Historical Replay Readiness

The architecture's immutability, versioning, and non-repainting requirements exist specifically so that historical replay (re-running the full pipeline against past raw data with pinned versions) produces identical results to the original run. This is a Phase 1A/1B planning requirement, not an implemented capability yet.

## 24. Future AI Isolation

AI/ML components connect only through the Future AI Interface Layer (SS7.15), read-only, and never write into raw, normalized, measurement, domain, POI, or lifecycle records. No AI model is trained, selected, or implemented by this document or by Phase 1B.

## 25. Future Execution-System Isolation

Telegram, MT4, MT5, and web-platform integrations connect only through the Future Signal and Execution Boundary (SS7.16), which does not exist as working code. No live trading, automated order execution, or bot of any kind is authorized by this document or any document it creates. **No execution adapter may be implemented or activated before the Future Risk-Control Interface (SS7.16) is itself a separately author-approved contract; execution must depend on that interface and may never bypass it.**

## 26. Deployment Boundaries

No deployment target, hosting provider, or containerization strategy is chosen or configured by this document (see Part 7, Technology-Stack Decision Register, for recommendations only). No `Dockerfile`, `docker-compose.yml`, or CI configuration is created.

## 27. Proposed Implementation Sequence (Informational Only — Not Authorized by This Document)

1. Author approves the Technology-Stack Decision Register (Part 7) and the Phase 1B entry gates (Part 10).
2. Phase 1B: create the repository scaffold directories only (per `REPOSITORY_SCAFFOLD_PLAN.md`), no logic.
3. Phase 1C (future, not authorized here): implement Configuration, Market-Data Contracts, and Validation layers.
4. Phase 1D (future, not authorized here): implement Raw Ingestion (against a chosen, author-approved data source) and Normalization.
5. Phase 1E (future, not authorized here): implement Measurement and Domain Entity layers.
6. Phase 1F (future, not authorized here): implement POI and Lifecycle Event layers for the 18 already-propagated POIs.
7. Phase 1G (future, not authorized here): implement Manual Annotation, Provenance, Audit, Historical Replay, and Deterministic Fixture layers.
8. Later phases (not planned here): BTMM evaluation, detector interfaces, AI interfaces, execution boundary — each requiring its own dedicated author-approval cycle.

This sequence is illustrative only; it does not authorize any step beyond Phase 1A (this document) and, upon separate approval, Phase 1B scaffold creation.

## 28. Architecture Risks

| Risk | Description | Mitigation (proposed) |
|---|---|---|
| Premature coupling | A detector or AI module could be built directly against raw data, bypassing the layered contracts. | Enforce the dependency-direction rules in `REPOSITORY_SCAFFOLD_PLAN.md`; code review gate. |
| Rule drift | A future engineer could hard-code a Phase 0G-deferred rule (e.g., an HH/HL/LH/LL formula) without an author decision. | Interface-only Future Detector Layer; explicit prohibition documented here and enforced by review. |
| Non-determinism | Reliance on wall-clock time, unpinned library versions, or non-deterministic ordering could break historical replay. | Versioning plan (Part 9); deterministic testing plan. |
| Provenance gaps | A layer could skip recording its source/version, breaking auditability. | Provenance Layer is mandatory input to every other layer's output. |
| Scope creep into trading automation | Foundation work could silently expand into entry/execution logic. | Explicit Future Signal and Execution Boundary with no implementation; this document's own non-scope section. |

## 29. Decisions Requiring Author Approval

See Part 7 (Technology-Stack Decision Register) and Part 10 (Architecture Decision Gates) below for the full, itemized list. At the architecture-principle level, the following require explicit author approval before Phase 1B:
- The full Technology-Stack Decision Register (17 items, Part 7).
- The time-zone canonicalization choice (Section 16).
- The data-retrieval/API mechanism for market data (Section 14).
- The secrets-management mechanism (Section 21).

## 30. Approval Status

**This entire document is ENGINEERING-RECOMMENDED planning content, pending author review.** No item in it is self-approving. Nothing in this document changes Phase 0G's status, resolves any Phase 0G blocker, or authorizes Phase 1B scaffold creation — a separate, explicit author instruction is required for that, exactly as with every prior phase transition in this project.

---

# Part 7 — Technology-Stack Decision Register

**This register contains exactly 17 items** (distinct from, and not to be confused with, the separate 20-item Phase 1B Architecture Decision Gate list in Part 10 below — see Part 10's clarifying note on the difference between a technology *recommendation* and a decision *gate*). For every item: exactly one recommended option, Alternatives considered, Reason, Risks, Evidence label, Author approval required, Current status. **No item is labeled AUTHOR-APPROVED** — every recommendation below is a proposal awaiting explicit author approval.

| # | Decision | Recommended (single option) | Alternatives Considered | Reason | Risks | Label | Approval Required | Current Status |
|---|---|---|---|---|---|---|---|---|
| 1 | Primary language and initial runtime | **Python 3.12** | Other languages: TypeScript/Node, Go, Rust. Other Python versions: 3.11, 3.13 | Python: strong data/ML ecosystem, matches likely future AI work, easy schema/validation tooling. 3.12: current, stable, well-supported release at time of writing | Language choice: slower raw execution than compiled languages; GIL concerns for high-throughput ingestion. Version choice: new minor releases will eventually require a deliberate re-evaluation | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 2 | Runtime-version policy | **Pin one exact Python 3.12 patch version during Phase 1B and update only through reviewed changes** | Floating "latest" | Determinism (Section 13) requires a pinned runtime | Pinning requires periodic, deliberate, reviewed upgrades | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 3 | Package manager | **uv** | Poetry, pip + requirements.txt, Conda | Fast, lockfile-based, single clear tool avoids an unresolved either/or choice | Newer tool than Poetry; smaller (but rapidly growing) ecosystem history | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 4 | Schema and validation | **Pydantic v2** | Marshmallow, JSON Schema + jsonschema, dataclasses + manual validation | Strong typing, good validation-error reporting, widely used with Python data pipelines | Library version pinning required for determinism | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 5 | Testing framework | **pytest** | unittest (stdlib), nose2 | Fixture support, parametrization, wide ecosystem match the Deterministic Testing Plan's needs | None significant | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 6 | Static typing | **mypy** | pyright, no static typing | Supports determinism and contract correctness at development time | Adds friction; requires discipline | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 7 | Formatting | **Ruff formatter** | black, manual style guide only | Single tool covers both formatting and linting (item 8), reducing toolchain surface | None significant | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 8 | Linting | **Ruff linter** | flake8 + plugins, pylint | Fast, combines many checks, same tool as item 7 | None significant | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 9 | Storage formats | **Parquet for bulk tabular historical records; JSONL for append-only event and audit streams** — one recommendation with two explicitly separated roles, not an unresolved either/or choice | CSV, raw provider-native format only, a relational DB from day one | Parquet is efficient for columnar time-series replay; JSONL is efficient for append-only, line-delimited event/audit streams — each format is assigned to the workload it fits | Requires a Parquet-aware toolchain | ENGINEERING-PROVISIONAL | YES | Not yet approved |
| 10 | Initial database strategy | **No database during the initial scaffold; use file-based contracts first** | PostgreSQL from day one, SQLite from day one, a time-series DB (e.g., TimescaleDB/InfluxDB) from day one | Avoids premature infrastructure commitment during foundation-only work | File-based storage will eventually need a migration path | DEFERRED | YES (before any DB is introduced) | **DEFERRED IMPLEMENTATION** |
| 11 | Raw-data storage strategy | **Append-only, immutable, and partitioned file storage** (by symbol/timeframe/date, one immutable file per ingestion batch). Exact physical encoding for provider-native payload preservation remains an implementation decision, not fixed here. | Single growing file, in-place database rows | Matches the immutability requirement (Section 12) directly | File-count growth over time needs a retention/compaction plan | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 12 | Logging | **Python standard library `logging` with structured JSON output** | A dedicated logging framework/service | Simple, no new dependency, structured output supports audit needs | Less feature-rich than a dedicated platform | ENGINEERING-RECOMMENDED | NO (low-risk default, subject to later revision) | Not yet approved |
| 13 | Configuration-file format | **YAML for human-managed configuration, plus a versioned machine-readable manifest for rule/schema versions** | JSON, TOML, environment variables only | Readable, widely supported, good for hierarchical config; the manifest half is separately machine-parseable for versioning | YAML parsing pitfalls (e.g., implicit type coercion) must be guarded against | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 14 | Migration strategy | **No database migration system until a database is approved** (item 10); use append-only schema-version manifests in the interim | A migration-tool-first approach (e.g., Alembic) from day one | No database yet to migrate | N/A | DEFERRED | YES (once a database is chosen) | **DEFERRED IMPLEMENTATION** |
| 15 | CI strategy | **GitHub Actions** running lint + type-check + deterministic tests on every push | No CI initially, a self-hosted CI system | Matches the existing GitHub-hosted repository; free for standard use | Requires secrets-handling discipline for any future credentials | ENGINEERING-RECOMMENDED | YES | Not yet approved |
| 16 | Containerization strategy | **No containerization during the initial scaffold** | Docker from day one | Avoids premature operational complexity during foundation-only work | Will need containerization before any live/production deployment | DEFERRED | YES | **DEFERRED IMPLEMENTATION** |
| 17 | Secrets-management strategy | **Environment variables are the runtime source. A git-ignored local `.env` file may be used only for local development convenience. Secrets must never be committed or embedded in configuration manifests.** | A secrets vault/service (e.g., a cloud secrets manager) | Simplest approach sufficient for a foundation-only, no-live-trading phase | Not sufficient for a production/live-trading deployment; must be revisited before that phase | ENGINEERING-PROVISIONAL | YES | Not yet approved |

**Every row above has exactly one recommended option** (no unresolved either/or choices remain — item 3 now names `uv` alone; item 9 assigns Parquet and JSONL each to a distinct, non-overlapping role rather than presenting them as alternatives to each other; Containerization (item 16) and Secrets-management (item 17) are now separate, independent rows, and Primary language and Initial runtime are now one combined row (item 1)). **No recommendation is labeled AUTHOR-APPROVED.**

---

# Part 8 — Data-Flow Diagram

See Section 9 above for the complete proposed data-flow diagram (identical content, included there per the document's own section numbering; duplicated reference here per the task's Part 8 requirement).

---

# Part 9 — Versioning Plan

| Version type | What it identifies | Reproducibility requirement |
|---|---|---|
| Rulebook version | The overall Phase 0G knowledge-base state (tied to a specific commit hash, e.g., `23f43676...`) | A record must always be interpretable against the rulebook version active when it was produced. |
| Measurement-standard version | Each individual standard in `knowledge/MEASUREMENT_STANDARDS.md` (e.g., "Candle Measurement Standard V1") | Every Derived Candle Measurement Record cites the exact standard version used. |
| POI-specification version | Each of the 36 POI files' own approval history (formation/boundary/lifecycle decisions, e.g., GROUP3-D1 through D9) | Every POI Record cites the exact POI-specification version(s) that produced it. |
| Lifecycle-standard version | `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` and `POI_FRESHNESS_AND_AGE_STANDARD.md` | Every Lifecycle Event cites the exact lifecycle-standard version. |
| Schema version | Each data contract in `DATA_CONTRACTS_AND_SCHEMA_PLAN.md` | Every record cites its own schema version; schema changes are additive/versioned, never silently reinterpreted. |
| Normalization version | The specific normalization logic/version that produced a Normalized Candle Record | Re-normalization creates a new version, never overwrites. |
| Annotation-guideline version | The reviewer instructions in force when a manual annotation was made | Every annotation cites the guideline version used. |
| Model version (future use) | Placeholder only — no model exists yet | Reserved field; not populated until an AI component is approved and implemented. |
| Replay-engine version (future use) | The version of the historical-replay tooling itself | Every Historical Replay Run cites both the replay-engine version and every version it replayed against, pinned at the time of that replay run. |
| **Processing version** (new) | The version of the specific processing logic/component that produced a given record (distinct from `rule_version` and `schema_version` — see below) | Applied to every derived, normalized, validation, annotation, lifecycle, replay, and audit record where processing logic produced the record; reprocessing under a new `processing_version` creates a new record or a new replay output, never overwrites the old one. |

**`processing_version` — proposed field, detailed:**
- **Distinct from `rule_version`:** `rule_version` identifies *which trading-rule/standard* was applied (e.g., "Candle Measurement Standard V1"); `processing_version` identifies *which version of the code/component* executed that rule.
- **Distinct from `schema_version`:** `schema_version` identifies the *shape* of the record; `processing_version` identifies the *logic* that filled that shape in.
- For externally received, immutable raw payload records (contract A, Raw Candle Record), `processing_version` **may be `NOT_APPLICABLE`** for the payload itself (it did not go through processing logic) — but the ingestion-envelope record wrapping that payload must still retain the ingestion-component's own version.
- An old `processing_version` reference is never overwritten; reprocessing always produces a new record (or a new Historical Replay Run output) referencing the new version.
- **The exact version-number format (semantic versioning, sequential integer, hash, etc.) remains `REQUIRES AUTHOR DECISION`** — not chosen here.
- This field is proposed only; **it is not implemented in any executable schema by this document.**

**Binding rule: no document update may silently reinterpret an old record.** A change to any standard, schema, or rule always produces a new version identifier; old records keep pointing at the version they were actually produced under.

---

# Part 10 — Architecture Decision Gates (Required Before Phase 1B Scaffold Implementation)

**This is a separate 20-item list, distinct from the 17-item Technology-Stack Decision Register in Part 7.** A **gate** here describes *whether the author is currently in a position to make a given decision* (its readiness), independent of what that decision's recommended answer might be. A **register item** in Part 7 describes *what is currently recommended* and *when its implementation should happen*. These are answering two different questions, and the word "DEFERRED" is used in each with a different meaning:
- In Part 7, `DEFERRED IMPLEMENTATION` (items 10, 14, 16) means "the recommended answer is to not build this yet."
- In this Part 10 gate table, `DEFERRED BEYOND PHASE 1B` would mean "the author cannot even usefully decide this yet" — a stronger, rarer condition.
- **A gate can be, and often is, `READY FOR AUTHOR DECISION` even when its associated Part 7 recommendation is `DEFERRED IMPLEMENTATION`** — e.g., gate #6 below ("Initial database position") is ready to decide right now, and the recommended answer to that decision (Part 7, item 10) happens to be "defer building a database." Readiness-to-decide and recommended-implementation-timing are not the same axis, and no gate is silently moved between classifications to make them look consistent.

| # | Decision | Classification |
|---|---|---|
| 1 | Primary language and runtime | READY FOR AUTHOR DECISION |
| 2 | Package manager | READY FOR AUTHOR DECISION |
| 3 | Schema-validation technology | READY FOR AUTHOR DECISION |
| 4 | Testing framework | READY FOR AUTHOR DECISION |
| 5 | Initial storage format | READY FOR AUTHOR DECISION |
| 6 | Initial database position (defer vs. adopt now) | READY FOR AUTHOR DECISION — recommended answer is to defer implementation (see Part 7, item 10) |
| 7 | Time-zone canonicalization | READY FOR AUTHOR DECISION |
| 8 | Symbol-normalization convention | READY FOR AUTHOR DECISION |
| 9 | Timeframe-enum convention | READY FOR AUTHOR DECISION |
| 10 | Candle-completeness policy | REQUIRES MORE RESEARCH |
| 11 | Duplicate-candle policy | REQUIRES MORE RESEARCH |
| 12 | Missing-candle policy | REQUIRES MORE RESEARCH |
| 13 | Ingestion-adapter boundary (which provider API, if any) | REQUIRES MORE RESEARCH |
| 14 | Identifier-generation strategy | READY FOR AUTHOR DECISION |
| 15 | Rule-version-manifest format | READY FOR AUTHOR DECISION |
| 16 | Schema-versioning strategy | READY FOR AUTHOR DECISION |
| 17 | Audit-log format | READY FOR AUTHOR DECISION |
| 18 | Configuration hierarchy | READY FOR AUTHOR DECISION |
| 19 | Secret-handling boundary | READY FOR AUTHOR DECISION |
| 20 | CI policy | READY FOR AUTHOR DECISION |

**Totals: READY FOR AUTHOR DECISION = 16. REQUIRES MORE RESEARCH = 4. DEFERRED BEYOND PHASE 1B = 0. Total = 20.** No gate has been moved between classifications from the prior version of this document — these totals are unchanged; only the clarifying note above and gate #6's annotation are new. Migration strategy (Part 7 item 14) and containerization strategy (Part 7 item 16) are Technology-Register decisions only — **they are not separate members of this 20-gate list.**

None of these 20 items is approved by this document. Phase 1B (repository scaffold creation) should not begin until the author has reviewed and approved (or amended) this register and this gate list, per a separate, explicit instruction.

---

# Post-Phase 1A Author Decisions — Phase 1B Groups 1–8

**This section is added after the original Phase 1A planning record above; nothing above it in this document has been rewritten.** Following author review, all eight Decision Groups below were approved. The full detail of every decision, including per-decision recommendation origin, author-decision status, implementation status, and production status, is recorded canonically in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md` — this section summarizes and cross-references that register; it does not restate every field.

**The eight decision groups:**
1. **Core Python Toolchain** — Python 3.12, pinned patch-version policy, uv, `pyproject.toml`, `uv.lock`, Pydantic v2, pytest, mypy, Ruff formatter, Ruff linter.
2. **Storage Foundation** — Parquet + JSONL role separation, no initial database, append-only/immutable/partitioned/provider-traceable raw storage, no migration system until a database is approved.
3. **Time, Symbols and Configuration** — canonical UTC normalization with source-timezone preservation, canonical internal symbols with explicit provider-mapping fields, canonical uppercase timeframe enum, YAML + versioned manifest configuration with a three-level precedence order, environment-variable secrets with dev-only `.env`.
4. **Identity, Versioning and Audit** — UUIDv7 record identity, SHA-256 content fingerprint (kept separate from identity), MAJOR.MINOR.PATCH versioning, the approved lineage field set, JSONL append-only audit storage.
5. **CI, Logging and Reproducibility** — stdlib structured-JSON logging (kept separate from audit), GitHub Actions with Ruff/mypy/pytest checks, `pyproject.toml`/`uv.lock` discipline, deferred containerization.
6. **Candle Data-Quality Policies** — `candle_completeness_status`, `duplicate_classification`, and `gap_status` enums, resolving Gates 10–12 at the policy level.
7. **Ingestion-Adapter Boundary** — a provider-neutral `MarketDataSourcePort` interface, `INTERFACE_ONLY` scaffold position, `OFFLINE_FILE`-only early retrieval, resolving Gate 13 at the architecture-policy level.
8. **Rule and Schema Version Manifests** — canonical UTF-8 JSON manifest format, the rule-version and schema-version manifest field sets, `BACKWARD_COMPATIBLE`/`BREAKING`/`DOCUMENTATION_ONLY` compatibility classes.

**Status of all decisions:** all **17** Technology-Stack Decision Register items (Part 7 above) are now `AUTHOR-APPROVED`. All **20** Architecture Decision Gates (Part 10 above) are now resolved at the author-decision level (`AUTHOR-DECISION RESOLVED`). **Zero are implemented. Zero are production-approved.** *(This "zero implemented" statement described the state at the time of this decision round. It is superseded by the "Phase 1B-A Software Foundation Implementation" section at the end of this document, which records that a specific, limited subset of these decisions has since been implemented via Batch 1B-A.)* Every item's original recommendation origin (`ENGINEERING-RECOMMENDED` / `ENGINEERING-PROVISIONAL` / `DEFERRED`) remains historically visible in Part 7 above and in the Phase 1B register — approval does not erase origin.

**The original readiness snapshot is not silently replaced.** Part 10's historical classification — READY FOR AUTHOR DECISION = 16, REQUIRES MORE RESEARCH = 4, DEFERRED BEYOND PHASE 1B = 0 — remains printed above, unchanged, as the accurate record of gate *readiness* at the time of the Phase 1A commit (`a142da371c766bbc3489d7d9ae26e6421527c6c9`). The *current* post-decision status (20 resolved, 0 pending, 0 implemented, 0 production-approved) is recorded separately in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Part 13, as an addition alongside the historical snapshot, not a replacement of it.

**Unresolved implementation sub-decisions remain binding** — including but not limited to: exact Python patch version, exact raw-payload encoding, retention policy, partition naming, exact fingerprint field sets, canonical JSON serialization procedure, exact validation-status enum, candle-close timestamp convention, DST/trading-day/week-start/month-boundary/provider-session handling, provider-specific adapters, FXCM/TradingView connectivity, data licensing, branch-protection/PR policy, future database/migration/containerization choices, the Future Risk-Control Interface, and all entry/risk/AI/signal/execution logic. The full list is maintained in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Part 14.

**No scaffold has been created by this section or by the decisions it summarizes.** Repository-scaffold creation remains a separate, explicit, future task.

---

# Phase 1B-A Software Foundation Implementation

**This section is an addition; all historical Phase 1A content above (Parts 1–10 and the "Post-Phase 1A Author Decisions" section) is preserved unchanged.** The original planning and readiness tables (Part 10's 16/4/0 snapshot, Part 7's 17-item register) are not modified by this section.

**Implementation commit:** `47cfd699bb7f4893774579f1693abbbb57b91607` — "Implement Phase 1B-A software foundation".

**Exact scope:** ten changed repository paths — `.gitignore` (modified) plus nine new files (`.python-version`, `pyproject.toml`, `src/btmm_ai_scanner/__init__.py`, `src/btmm_ai_scanner/config/__init__.py`, `src/btmm_ai_scanner/config/enums.py`, `src/btmm_ai_scanner/config/loader.py`, `tests/test_config_precedence.py`, `tests/test_import_smoke.py`, `uv.lock`).

**Verification gates (all passed):** `uv lock --check`; package import verification; Ruff format check; Ruff lint; mypy (strict); pytest (34 collected, 34 passed).

**Technologies now present** (a limited subset of Part 7's 17-item register, now with executable repository support): Python 3.12.13 (exact-pinned via `.python-version` and `requires-python`); uv 0.11.30 as package manager (`pyproject.toml` + committed `uv.lock`); pytest 9.1.1; mypy 2.3.0 (strict); Ruff 0.15.22 (formatter + linter); a standard-library-only configuration-precedence mechanism (three-layer merge, secret-key rejection) — this last item is new executable support for part of the Decision Group 3 configuration approach, distinct from, and not to be confused with, the still-unimplemented YAML configuration-file-format decision (Part 7 item 13).

**Technologies still absent:** Pydantic (schema/validation, Part 7 item 4); Parquet/JSONL storage (item 9); any database or migration tooling (items 10, 14); structured JSON logging (item 12); the YAML configuration file and versioned manifest themselves (item 13); GitHub Actions CI (item 15); any containerization (item 16); any actual secret-retrieval/runtime secret-loading boundary beyond the rejection mechanism (item 17, partially implemented only). Full item-by-item justification is recorded in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 18f (technology register) and 18g (gate matrix).

**All Phase 0G restrictions remain binding, unchanged by this implementation.** The Knowledge Gate remains **OPEN FOR CONTROLLED FOUNDATION WORK** only — not unconditionally open. **No trading, ingestion, model, signal, risk, or execution approval exists** — none of that scope is present in, or authorized by, Batch 1B-A. Production status remains **`NOT PRODUCTION-APPROVED`**. Batch 1B-B has not begun.
