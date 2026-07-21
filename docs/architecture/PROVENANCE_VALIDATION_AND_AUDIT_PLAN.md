# Provenance, Validation, and Audit Plan

**Document status:** ENGINEERING-RECOMMENDED planning document. No numeric tolerance below is author-approved unless explicitly labeled so; unapproved thresholds are marked `REQUIRES AUTHOR DECISION` or `ENGINEERING-PROVISIONAL`. Nothing here is implemented.

---

## 1. Provenance Objectives

Every record produced by the foundation must be traceable back to: (a) its raw data origin, (b) every transformation applied, (c) the exact rule and schema versions in force at each step, and (d) — for manual evidence — the specific human reviewer and guideline version. This exists so that any output can later be explained, reproduced, and (where a Phase 0G-deferred item is eventually resolved) safely re-evaluated without corrupting historical records. **Label: ENGINEERING-RECOMMENDED.**

## 2. Raw-Data Lineage

Every Raw Candle Record carries: provider, feed, symbol, timeframe, timestamp, source timezone, retrieval method, retrieval time, raw-data version. This field list is proposed by, and required only because of, this Phase 1A planning task's own instruction — it is not itself a pre-existing Phase 0G trading-rule decision, so it is **not** labeled `AUTHOR-APPROVED`. **Label: ENGINEERING-RECOMMENDED.** The specific fields provider/symbol/timeframe values must draw from (`FXCM:XAUUSD`/`FXCM:EURUSD`/`FXCM:GBPUSD`; H3/H4/D1/W1/H1/M15/M5/M1) **are** separately `AUTHOR-APPROVED`, traceable to `docs/PROJECT_SCOPE.md` — only the specific field-list shape here is an engineering proposal. The retrieval mechanism itself is `REQUIRES AUTHOR DECISION`.

## 3. Normalization Lineage

Every Normalized Candle Record references its exact source `raw_candle_id` and its own normalization version. Re-normalization under a new version never overwrites a prior Normalized Candle Record. **Label: ENGINEERING-RECOMMENDED.**

## 4. Derived-Measurement Lineage

Every Derived Candle Measurement Record references its source `normalized_candle_id`, any reference-window candles used, and the exact Measurement Standard version applied. **Label: ENGINEERING-RECOMMENDED.**

## 5. Rule-Version Lineage

Every POI, Lifecycle, Domain-Entity, and BTMM record references the exact rule/specification version(s) that produced it, resolvable via the Rule-Version Manifest (contract Q in `DATA_CONTRACTS_AND_SCHEMA_PLAN.md`). **Label: ENGINEERING-RECOMMENDED.**

## 6. Schema-Version Lineage

Every record references its own schema version, resolvable via the Schema-Version Manifest (contract R). Schema changes are additive/versioned; no schema change silently reinterprets an old record. **Label: ENGINEERING-RECOMMENDED.**

### 6a. Processing-Version Lineage

Every derived, normalized, validation, annotation, lifecycle, replay, and audit record additionally references a proposed `processing_version` field — the version of the specific processing logic/component that produced it, **distinct from both `rule_version`** (which trading-rule/standard was applied) **and `schema_version`** (the record's shape). For externally received immutable raw payload records, `processing_version` may be `NOT_APPLICABLE` on the payload itself, though the ingestion-envelope record wrapping it must still retain the ingestion component's own version. Reprocessing under a new `processing_version` always creates a new record or a new Historical Replay Run output — an old `processing_version` reference is never overwritten. **The exact version-number format is `REQUIRES AUTHOR DECISION`. Label: ENGINEERING-RECOMMENDED.** This field is proposed only; it is not implemented in any executable schema by this document.

## 7. Manual-Review Lineage

Every Annotation Record (Manual Expert Context/Liquidity-Event/Trendline-Event Label) references the reviewer's identity, the review timestamp, and the annotation-guideline version in force. **Label: ENGINEERING-RECOMMENDED.**

## 8. Evidence-Source Tagging

Every record capable of carrying trading-relevant evidence must carry an explicit, visible, mutually-exclusive source tag from the existing Phase 0G vocabulary (`MANUAL_EXPERT_LABEL`, `RULE_BASED`, `RULE_BASED_REVIEWED`, `EXPERT_LABELLED`, `MODEL_PROPOSED`, `HYBRID_REVIEWED`). No record may carry two conflicting source tags, and no automatic process may silently relabel a `MANUAL_EXPERT_LABEL` record as any other source. **Label: AUTHOR-APPROVED** (vocabulary itself, already approved in Phase 0G); the enforcement mechanism is `ENGINEERING-PROVISIONAL`.

## 9. Validation Levels

Three levels are proposed:
1. **Contract-conformance validation** — does the record match its declared schema (required fields present, correct types)?
2. **Data-quality validation** — is the underlying data internally consistent (OHLC ordering, timestamp monotonicity, no impossible values)?
3. **Cross-record validation** — does this record's provider/symbol/timeframe match its stated parent/source record's provider/symbol/timeframe?

**Label: ENGINEERING-RECOMMENDED.** None of these three levels decides POI or BTMM validity — data-quality validity and trading validity remain structurally separate concepts, matching Phase 0G's own validity-separation principle.

### 9a. Validation Eligibility Gating (Expanded)

**Governing principle: a record must not enter Normalization or Measurement merely because it exists. Eligibility to proceed must be established by an explicit, upstream Validation Result — presence alone is never sufficient.** The full proposed processing sequence:

1. Preserve the received raw payload immutably.
2. Perform source-envelope and contract checks.
3. Produce a traceable Validation Result for that payload (level 1 above).
4. Quarantine any record carrying an unresolved or disqualifying data-quality failure (level 2 above) — it does not proceed past this step.
5. Normalize only records the Validation Result explicitly marks eligible.
6. Validate the resulting Normalized Candle Record.
7. Perform sequencing and cross-record validation (level 3 above).
8. Generate Derived Candle Measurement Records only from records explicitly eligible for measurement processing (i.e., that passed steps 5-7).

**Confirmed:** quarantined records remain preserved, never silently deleted; no silent repair occurs at any step; raw payload values are never overwritten by a normalized or corrected value; a data-quality rejection is never treated as, or converted into, a POI or BTMM invalidation — those remain entirely separate concepts (Section 9 above). Measurements cannot be generated from a record still carrying an unresolved `QUARANTINED` status. **The exact validation-status enum and its gating implementation are not defined here — both are `REQUIRES AUTHOR DECISION`.** No fixed numeric tolerance for any of the three validation levels is chosen by this section.

## 10. Validation Failures

A failed validation produces a Validation Result record with `status = FAIL` or `status = QUARANTINED`; the failing record is never silently dropped or silently auto-corrected. **Label: ENGINEERING-RECOMMENDED.**

## 11. Quarantine Policy

Records that fail data-quality validation are held in a quarantine state, visible to a human reviewer, and excluded from downstream processing (Normalization, Measurement, POI, etc.) until manually resolved. **Exact quarantine-review workflow: REQUIRES AUTHOR DECISION.**

## 12. Duplicate-Data Policy

Proposed principle: a duplicate raw candle (same provider/symbol/timeframe/timestamp as an existing record) is detected and flagged, never silently overwritten and never silently discarded — both records are preserved with a `duplicate_of` reference, and a human/process decides which is authoritative. **Exact detection tolerance and resolution mechanism: REQUIRES AUTHOR DECISION** (Decision Gate #11).

## 13. Missing-Data Policy

Proposed principle: a gap in the expected candle sequence for a given symbol/timeframe is detected and recorded as a Validation Result, never silently interpolated or filled. **Exact gap-detection and handling policy: REQUIRES AUTHOR DECISION** (Decision Gate #12).

## 14. Out-of-Order Candle Policy

Proposed principle: a candle arriving with an event time earlier than an already-processed candle for the same symbol/timeframe is flagged by validation and does not silently retroactively alter any already-produced Normalized/Derived/POI record (matches the non-repainting principle). **Label: ENGINEERING-RECOMMENDED** for the non-repainting consequence; **REQUIRES AUTHOR DECISION** for the exact reconciliation procedure.

## 15. Incomplete-Candle Policy

Proposed principle: a candle that has not yet closed is never treated as "confirmed" or used as input to any formula requiring a confirmed candle (matching every Phase 0G standard's own "confirmed closed candle" requirement, e.g., Pressure Wick Standard V1's `Total Range = High − Low must be > 0` on a confirmed closed candle). **Label: AUTHOR-APPROVED** (the underlying "confirmed candles only" principle, already present throughout `knowledge/MEASUREMENT_STANDARDS.md`); the specific completeness-detection mechanism (e.g., how a "close" event is determined from a live feed) is `REQUIRES AUTHOR DECISION`.

## 16. Time-Zone Validation

Every raw record's source timezone must be explicitly present and validated against an expected set (not silently assumed); normalization to the canonical timezone (Decision Gate #7) must be checked for correctness (e.g., DST transition handling). **Label: ENGINEERING-PROVISIONAL** pending the canonical-timezone decision itself.

**None of the following are approved facts — all are engineering proposals or open questions** (see `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` Section 16 for the full table): candle `event_time`/`availability_time` semantics (`ENGINEERING-PROVISIONAL`); canonical UTC storage with source-timezone preservation (`ENGINEERING-PROVISIONAL`); exact candle-close timestamp convention, DST normalization, trading-day boundary, week-start convention, month-boundary handling, and provider-session handling (all `REQUIRES AUTHOR DECISION`). This section does not resolve the pre-existing Phase 0G period-rollover question (`P0G-B013A`), and does not claim any TradingView data API exists or is approved.

## 17. OHLC Consistency Validation

Proposed checks: `High >= Open, Close, Low`; `Low <= Open, Close, High`; `High >= Low`; no negative prices; no zero-range candle silently treated as valid input to a formula that divides by Total Range (matches the existing Phase 0G "Total Range ≤ 0 is invalid" rule already present in the Pressure Wick and other standards). **Label: AUTHOR-APPROVED** (the underlying zero/negative-range rejection principle, already present in Phase 0G); the full OHLC consistency checklist is `ENGINEERING-RECOMMENDED`.

## 18. Provider-Symbol Validation

Every record must be checked against the canonical, Author-Approved provider/symbol list (`FXCM:XAUUSD`, `FXCM:EURUSD`, `FXCM:GBPUSD`) — an unrecognized symbol or provider is rejected at ingestion, not silently accepted. **Label: AUTHOR-APPROVED** (the list itself); the rejection mechanism is `ENGINEERING-RECOMMENDED`.

## 19. Timeframe Validation

Every record must be checked against the canonical timeframe set (H3, H4, D1, W1, H1, M15, M5, M1) — none of these may be silently excluded, and no unrecognized timeframe is silently accepted. **Label: AUTHOR-APPROVED** (the timeframe list); the enum/validation mechanism is `ENGINEERING-PROVISIONAL`.

## 20. Audit-Event Structure

Every audit event carries: event type, subject record reference(s), actor (system component or human reviewer), timestamp, and the exact rule/schema versions in force at the time of the event. Audit events are themselves immutable and append-only. **Label: ENGINEERING-RECOMMENDED.**

## 21. Reproducibility Requirements

Given the same raw data and the same pinned rule/schema versions, every derived record must be exactly reproducible via the Historical Replay Layer. This is the core justification for the immutability and versioning requirements throughout this plan. **Label: ENGINEERING-RECOMMENDED.** This determinism/reproducibility requirement is a **new architectural proposal** introduced by this Phase 1A planning package — it is not itself a Phase 0G-approved rule, and it does not approve itself merely by being restated in another Phase 1A document. It is, however, deliberately designed to be *consistent with* — and never to contradict — the genuinely Author-Approved Phase 0G non-repainting and no-retroactive-rewriting rules (e.g., `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` SS15, `knowledge/btmm/BTMM_STATE_MACHINE.md`'s non-repainting confirmation timing), which govern *when* a record becomes visible, not *whether* recomputing it yields an identical result — a related but distinct concept from this section's reproducibility claim.

## 22. Historical Replay Audit

Every Historical Replay Run is itself an audited event, recording which pinned versions were used and whether its output matched a prior run of the same range/versions (a determinism self-check). **Label: ENGINEERING-RECOMMENDED.**

## 23. Data-Retention Planning

No specific retention period or deletion policy is chosen here. Proposed default principle: raw data, once ingested, is retained indefinitely unless an explicit, separately-approved retention policy states otherwise — nothing is deleted by default, consistent with the immutability requirement. **Label: REQUIRES AUTHOR DECISION** (any actual retention limit or deletion mechanism).

## 24. Private-Source Protection

The private source book (`references/private/BTMM_AND_POI_TRADING_BIBLE.docx`) remains protected by the existing `.gitignore` entry `references/private/*`. **Label: AUTHOR-APPROVED** for that pre-existing safeguard itself — it is not a new decision, only a restatement of a protection already in force throughout this project. The **new** rule that the book must never be read at runtime by any layer, and never embedded in any fixture, log, or audit event, is a broader extension of that existing safeguard, proposed for the first time by this Phase 1A package. **Label: ENGINEERING-RECOMMENDED** for that extension — it is a hard architectural proposal, not merely a documentation convention, but it is not itself a separately author-approved rule until the author explicitly approves it.

## 25. Tamper-Evidence Planning

Proposed principle: audit events and provenance records should be structured so that a later modification to historical data would be detectable (e.g., via content hashing or an append-only log structure) — the specific mechanism (cryptographic hash chain, write-once storage, etc.) is not chosen here. **Label: ENGINEERING-PROVISIONAL.**

## 26. Approval Status

**ENGINEERING-RECOMMENDED**, pending author review. Every numeric tolerance or specific mechanism not already Author-Approved in Phase 0G is explicitly marked `REQUIRES AUTHOR DECISION` or `ENGINEERING-PROVISIONAL` above — none is silently treated as approved. Nothing in this document is implemented.

## 27. Post-Phase 1A Author Decisions (Decision Groups 1–8)

**Nothing in this section is implemented; this section only records which of the plan's proposals above are now author-approved.** Full decision detail is recorded canonically in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`.

- **Raw storage (Group 2):** append-only, immutable, partitioned raw storage (SS2) is confirmed `AUTHOR-APPROVED` at the policy level; Parquet/JSONL role separation (bulk tabular vs. append-only event/audit streams) is approved as the storage-format pairing referenced throughout this plan.
- **Time semantics (Group 3):** canonical UTC normalization, with source timezone always preserved (SS16), is now `AUTHOR-APPROVED`. The remaining time sub-questions listed in SS16 — exact close-timestamp convention, DST handling, trading-day boundary, week-start convention, month-boundary handling, provider-session handling — remain **`REQUIRES AUTHOR DECISION`**, unresolved by this decision round; this section does not define any provider-session calendar or unresolved time-boundary rule.
- **Identity and fingerprinting (Group 4):** UUIDv7 is approved as the record-identity mechanism referenced implicitly throughout SS2–SS8 and SS20 (Audit-Event Structure); SHA-256 is approved as the `content_fingerprint` mechanism, kept separate from identity, supporting the tamper-evidence planning in SS25.
- **Versioning (Group 4):** the MAJOR.MINOR.PATCH scheme is approved for `rule_version`, `schema_version`, and `processing_version` lineage (SS5, SS6, SS6a).
- **Completeness/duplicate/missing-candle handling (Group 6):** SS15 (Incomplete-Candle Policy) is refined — completeness is now formally tracked via `candle_completeness_status` (`CONFIRMED_COMPLETE`/`INCOMPLETE`/`UNKNOWN`), with only `CONFIRMED_COMPLETE` candles analytically eligible; SS12 (Duplicate-Data Policy) is refined via `duplicate_classification` (`EXACT_DUPLICATE`/`CONFLICTING_DUPLICATE`/`NOT_DUPLICATE`), with conflicting duplicates `QUARANTINED` pending explicit reviewed resolution; SS13 (Missing-Data Policy) is refined via `gap_status` (`POTENTIAL_GAP`/`CONFIRMED_MISSING`/`EXPECTED_NON_TRADING_INTERVAL`/`RESOLVED`), with an explicit prohibition on synthetic candles, forward/back fill, interpolation, previous-close copying, or silent time compression. **Quarantine rules (SS11) apply unchanged** — quarantined records remain visible to a human reviewer and excluded from downstream processing until manually resolved; the exact quarantine-review workflow remains `REQUIRES AUTHOR DECISION`.
- **Ingestion boundary (Group 7):** a provider-neutral ports-and-adapters boundary (`MarketDataSourcePort`, `INTERFACE_ONLY`) is approved as the architecture for future raw-data lineage (SS2); early retrieval is restricted to `OFFLINE_FILE` mode. Transport, parsing, and validation failures are approved as three distinct, separately-tracked failure classes, extending SS10 (Validation Failures) — none may trigger silent repair, silent discard, infinite retry, or credential leakage.
- **Operational logging vs. audit (Group 5):** structured JSON logging via Python's standard `logging` library is approved as the operational-logging mechanism, kept strictly separate from the authoritative, append-only JSONL audit trail described in SS20 — operational logs are diagnostic only and never substitute for an audit event.
- **Audit exclusions (Group 4):** audit records (SS20) must exclude passwords, tokens, API keys, `.env` contents, unredacted credentials, private-book text, and unnecessary personal information — this extends, and does not relax, SS24's private-source protection.
- **Manifest lineage (Group 8):** the Rule-Version and Schema-Version Manifests referenced throughout (SS5, SS6, contracts Q/R) are approved to use canonical UTF-8 JSON serialization, UUIDv7 identity, and SHA-256 content fingerprinting; schema-version changes are approved to use the `BACKWARD_COMPATIBLE`/`BREAKING`/`DOCUMENTATION_ONLY` compatibility-class scheme.

**This section does not define any provider-session calendar, does not resolve any of the remaining time-boundary rules listed in SS16, and does not implement any of the mechanisms above.** All remain `NOT YET IMPLEMENTED` and `NOT PRODUCTION-APPROVED`.
