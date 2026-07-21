# Data Contracts and Schema Plan

**Document status:** ENGINEERING-RECOMMENDED planning document. All contracts below are **proposed field shapes only — no executable schema (Pydantic model, JSON Schema, database table, etc.) is implemented by this document.** No entry, stop-loss, take-profit, position-size, or risk field is defined anywhere in this document, by explicit instruction.

---

## 1. Purpose

Propose the field-level shape of every record type the software foundation will need, so the author can review data-contract completeness before any executable schema is written in a later phase.

## 2. Common Fields (Present on Every Contract Unless Noted)

| Field | Meaning |
|---|---|
| Identity field | The record's own unique, never-reused identifier. |
| Parent/source identity | The identifier of the record(s) this one was derived from (if any). |
| Symbol | One of `FXCM:XAUUSD`, `FXCM:EURUSD`, `FXCM:GBPUSD`. |
| Provider | Data provider (currently FXCM only, per `docs/PROJECT_SCOPE.md`). |
| Timeframe | One of H3/H4/D1/W1/H1/M15/M5/M1. |
| Event time | The timestamp the record's underlying market event actually occurred. |
| Availability time | The timestamp the record becomes visible to downstream consumers (non-repainting — never earlier than event time, often later). |
| Processing time | The wall-clock timestamp the record was actually computed/written. |
| Rule version | The exact Phase 0G rule/standard version used to produce this record. |
| Schema version | The exact schema version of this record's own shape. |
| Processing version (new — see SS4a) | The exact version of the processing logic/component that produced this record — distinct from both rule version (which rule was applied) and schema version (the record's shape). `NOT_APPLICABLE` for an unprocessed raw payload itself (see contract A). |
| Evidence source | Where applicable: `MANUAL_EXPERT_LABEL`, `RULE_BASED`, `RULE_BASED_REVIEWED`, `EXPERT_LABELLED`, `MODEL_PROPOSED`, `HYBRID_REVIEWED` (reused unmodified from Phase 0G's existing vocabulary — see `knowledge/btmm/BTMM_STATE_MACHINE.md`). |
| Validation status | Reference to a Validation Result record. |
| Provenance reference | Reference to a Provenance Record. |
| Immutable vs. mutable | Which fields, once set, may never change. |
| Required vs. optional | Which fields must always be populated vs. may be absent/null. |

## 3. Proposed Contracts

### A. Raw Candle Record
- **Identity:** `raw_candle_id` (unique per provider/symbol/timeframe/timestamp/raw-data-version tuple).
- **Parent/source:** none (root record).
- **Symbol/Provider/Timeframe:** required.
- **Event time:** the candle's own open time. **(`ENGINEERING-PROVISIONAL` — this specific event-time convention is a proposal, not yet an author-approved fact; see `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` Section 16.)**
- **Availability time:** the candle's own close time (a candle is not "available" until it closes/confirms). **(`ENGINEERING-PROVISIONAL`, same caveat — the exact close/confirmation timestamp convention is `REQUIRES AUTHOR DECISION`.)**
- **Processing time:** ingestion timestamp.
- **Rule version:** N/A (raw data carries no trading-rule interpretation).
- **Schema version:** required.
- **Evidence source:** N/A.
- **Confidence/status:** N/A.
- **Validation status:** required (every raw candle passes through Validation before use).
- **Provenance reference:** required (provider, feed, retrieval method, retrieval time, source timezone).
- **Immutable fields:** all fields, once written.
- **Mutable fields:** none.
- **Required fields:** identity, symbol, provider, timeframe, event time, raw OHLC, source timezone, retrieval method, retrieval time, raw-data version.
- **Optional fields:** raw tick-volume (per the existing Phase 0G rule that tick volume is secondary/optional and never mandatory).

### B. Normalized Candle Record
- **Identity:** `normalized_candle_id`.
- **Parent/source:** `raw_candle_id`.
- **Event/Availability time:** canonicalized to the chosen timezone (Decision Gate #7); availability time = confirmed-close time in canonical timezone. **(`ENGINEERING-PROVISIONAL`/`REQUIRES AUTHOR DECISION` — see `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` Section 16; canonical timezone, DST handling, and exact close-timestamp convention are all not yet approved.)**
- **Processing time:** normalization run timestamp.
- **Rule version:** N/A.
- **Schema/normalization version:** required (independent of raw-data version).
- **Immutable fields:** all, once written; a re-normalization creates a new `normalized_candle_id`, never edits the old one.
- **Required fields:** identity, source raw-candle reference, canonical OHLC, canonical timezone, normalization version, confirmed-candle flag.
- **Optional fields:** none beyond the raw record's own optional fields (tick volume, carried through if present).

### C. Derived Candle Measurement Record
- **Identity:** `measurement_id`.
- **Parent/source:** `normalized_candle_id` (plus any reference-window candles the formula requires, e.g., the prior-20-candle median).
- **Rule version:** the exact Measurement Standard version (e.g., "Candle Measurement Standard V1").
- **Required fields:** identity, source candle reference, the specific computed values (Total Range, Body, Body Efficiency, Size Ratio, Range Context Ratio, Bullish/Bearish Close Position, etc., per `knowledge/MEASUREMENT_STANDARDS.md`), reference-window identifiers used.
- **Immutable fields:** all, once written.

### D. Meaningful Swing Record
- **Identity:** `swing_id`.
- **Parent/source:** the pivot candle's `normalized_candle_id` (or plateau candle set).
- **Rule version:** Meaningful Swing High/Low Detection Standard V1.
- **Required fields:** identity, pivot price, pivot time, direction (High/Low), state (`LOCAL_SWING_CANDIDATE`/`CONFIRMED_MEANINGFUL_SWING_HIGH`/`_LOW`/`SUPERSEDED`), `superseded_by_swing_id` (if applicable), `meaningful_confirmation_time`.
- **Immutable fields:** pivot price/time once confirmed; **`SUPERSEDED` records are never deleted — a new, more-extreme candidate always receives its own new `swing_id`, linked via `superseded_by_swing_id`.**
- **Evidence label for the `SUPERSEDED`-never-deleted rule: `AUTHOR-APPROVED`.** This is not a new invention — it is a direct restatement of the existing, already Author-Approved **Meaningful Swing High and Swing Low Detection Standard V1** (resolves Ambiguity 10; see `knowledge/MEASUREMENT_STANDARDS.md`, "Meaningful Swing High and Swing Low Detection Standard," and `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`). This contract restates that rule; it does not alter it.
- **Note:** `STRONG_SWING`'s material-breach sub-rule remains undefined (open item) — this contract reserves a field for it but does not define its threshold.

### E. POI Record
- **Identity:** `poi_id` — **a newly formed POI must always receive a new `poi_id`; never reused, never reassigned.**
- **Parent/source:** the originating candle(s)/domain-entity reference(s) per the specific POI type (varies by the 36 POI specifications).
- **Rule version:** the exact POI-specification version (per-POI, since each of the 36 has its own approval history).
- **Availability time:** the POI's own approved `*_available_time` field (already named per-POI in Phase 0G, e.g., `order_block_available_time`, `fvg_available_time`).
- **Required fields:** identity, POI type (one of the 36), direction, zone_top/zone_bottom (or single price level for non-zone POIs), formation evidence reference, availability time.
- **Applicability flags:** `generic_lifecycle_applicability` (`INHERITED`/`EXCLUDED_BY_DESIGN`/`NOT_APPLICABLE`), `freshness_status`, `expiration_status`, `rejection_criterion_status` (`EXPLICIT`/`NOT_APPLICABLE`) — all reusing the exact Phase 0G vocabulary, no new values invented.
- **Immutable fields:** identity, type, direction, zone boundaries, availability time — all fixed once the POI is confirmed (non-repainting).

### F. POI Interaction Event
- **Identity:** `interaction_event_id`.
- **Parent/source:** `poi_id`.
- **Required fields:** identity, POI reference, interaction classification (`EDGE_TOUCH`/`PARTIAL_ENTRY`/`DEEP_ENTRY`/`FAR_BOUNDARY_TOUCH`/`CONTROLLED_OVERSHOOT`/`NEAR_MISS`/`NO_CONTACT`/`NONCANONICAL_SIDE_INTERACTION`), interaction time, `tap_count`, `tap_classification` (`INITIAL_TAP`/`REPEATED_TAP`/`MULTIPLE_REPEATED_TAPS`).
- **Timing rule:** per `P0G-B006`'s clarification, a freshness-*changing* interaction must satisfy `qualifying_interaction_time > poi_availability_time` (strictly later); this contract records the interaction regardless, but the *freshness effect* of the interaction (see contract for freshness, folded into the POI Record's `freshness_status` field) applies only when that strict-inequality condition holds.
- **Immutable fields:** all, once recorded (append-only; a new tap is a new `interaction_event_id`, never an edit).

### G. POI Lifecycle Event
- **Identity:** `lifecycle_event_id`.
- **Parent/source:** `poi_id`, `boundary_breach_event_id` (where applicable).
- **Rule version:** POI Boundary Breach, Reclaim and Invalidation Standard V1.
- **Required fields:** identity, POI reference, event state (one of the ten states: `NO_BREACH` through `GENUINE_INVALIDATION_CONFIRMED`), event time, non-repainting confirmation time.
- **Applicability:** only for the 18 propagated POIs; `NOT_APPLICABLE` for Equal Highs/Lows/Trendlines (specialized lifecycle formally deferred) and for the 14 non-applicable reference structures.
- **Immutable fields:** all, once confirmed; forbidden transitions (e.g., `GENUINE_INVALIDATION_CONFIRMED → FALSE_INVALIDATION_CONFIRMED`) must be structurally rejected, not merely discouraged.

### H. BTMM Setup Record
- **Identity:** `btmm_setup_id` — **a later eligible interaction always creates a new setup, never reactivates a cancelled one.**
- **Parent/source:** `poi_id`, `interaction_event_id`.
- **Rule version:** BTMM Lifecycle and Confirmation State Machine V1.
- **Required fields:** identity, primary state (`BTMM_CANDIDATE`/`BTMM_FORMING`/`BTMM_BLOCKED`/`BTMM_CONFIRMED`/`BTMM_CANCELLED`), formation stage, all ten gate statuses, `btmm_confirmation_time` or `cancellation_time`/`cancellation_reason`.
- **Immutable fields:** setup identity, direction, confirmation/cancellation time, gate evidence — once recorded, never retroactively rewritten by a later trade outcome.
- **Evidence label for the "new setup, never reactivate" rule: `AUTHOR-APPROVED`.** This is not a new invention — it is a direct restatement of the existing, already Author-Approved **BTMM Lifecycle and Confirmation State Machine V1** (resolves Ambiguity 14; see `knowledge/btmm/BTMM_STATE_MACHINE.md`, "Setup Identity" and "Non-Repainting and No-Retroactive-Rewriting Rules"). This contract restates that rule; it does not alter it.
- **Note:** this contract is documented for completeness; the BTMM evaluation layer itself is not implemented in Phase 1A/1B.

### I. Manual Expert Context Label
- **Identity:** `context_label_id`.
- **Parent/source:** the BTMM setup or evaluation window it annotates.
- **Evidence source:** `context_input_source = MANUAL_EXPERT_LABEL` (fixed value).
- **Required fields:** identity, `context_direction` (`BULLISH`/`BEARISH`/`NEUTRAL`/`UNCLEAR`), `context_alignment` (`ALIGNED`/`MISALIGNED`/`UNCLEAR`), reviewer identity, review timestamp, annotation-guideline version.
- **Immutable fields:** all, once submitted; a correction creates a new, superseding record.

### J. Manual Liquidity-Event Label
- **Identity:** `liquidity_label_id`.
- **Parent/source:** `poi_id` (Equal Highs/Equal Lows only, per `P0G-B004`).
- **Evidence source:** `liquidity_event_source = MANUAL_EXPERT_LABEL` (fixed value).
- **Required fields:** identity, POI reference, reviewer identity, review timestamp, annotation-guideline version, reviewed event description (free text or a controlled vocabulary, TBD — not defined here since automatic SWEPT/BROKEN detection is deferred).
- **Immutable fields:** all, once submitted.

### K. Manual Trendline-Event Label
- **Identity:** `trendline_label_id`.
- **Parent/source:** the Trendline domain-entity identity (per `P0G-B005`).
- **Evidence source:** `trendline_event_source = MANUAL_EXPERT_LABEL` (fixed value).
- **Required fields:** identity, Trendline reference, reviewer identity, review timestamp, annotation-guideline version.
- **Immutable fields:** all, once submitted.

### L. Annotation Record
- **Identity:** `annotation_id` (a general-purpose superclass/union covering I, J, K, plus any future annotation type).
- **Required fields:** identity, annotation type, reviewer identity, timestamp, guideline version, subject reference.
- **Immutable fields:** all, once submitted.
- **Note:** fixtures built from annotation records must never be treated as AI training data by default (see `DETERMINISTIC_TESTING_AND_FIXTURE_PLAN.md`); `P0G-B021` remains separately responsible for the future reviewed negative-example dataset.

### M. Provenance Record
- **Identity:** `provenance_id`.
- **Parent/source:** the record it documents lineage for.
- **Required fields:** identity, subject record reference, upstream lineage chain (raw → normalized → derived, etc.), rule version(s), schema version(s), provider/feed identity, retrieval method, retrieval time.
- **Immutable fields:** all, once written.

### N. Validation Result
- **Identity:** `validation_result_id`.
- **Parent/source:** the record being validated.
- **Required fields:** identity, subject record reference, validation rule version, pass/fail/quarantine status, failure reason (if applicable), timestamp.
- **Immutable fields:** all, once written (a re-validation produces a new result, not an edit).

### O. Audit Event
- **Identity:** `audit_event_id`.
- **Parent/source:** any record or action being audited.
- **Required fields:** identity, event type, subject reference(s), actor (system/human), timestamp, rule/schema versions in force at the time.
- **Immutable fields:** all, once written — audit events are themselves append-only and tamper-evident (see `PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md`).

### P. Historical Replay Run
- **Identity:** `replay_run_id`.
- **Parent/source:** the raw-data range and pinned rule/schema versions being replayed.
- **Required fields:** identity, replay-engine version, pinned rule/schema versions, input raw-data range, output record references, run timestamp, determinism-check result (whether output matched a prior run, if applicable).
- **Immutable fields:** all, once completed.

### Q. Rule-Version Manifest
- **Identity:** `rule_version_id`.
- **Required fields:** identity, rule/standard name, version number, effective date, source commit hash (e.g., `23f43676...`), summary of what changed from the prior version.
- **Immutable fields:** all, once published — a manifest entry is never edited after the fact; a correction is a new entry.

### R. Schema-Version Manifest
- **Identity:** `schema_version_id`.
- **Required fields:** identity, contract name (one of A-Q above), version number, effective date, field-level change summary (additive vs. breaking).
- **Immutable fields:** all, once published.

## 4. Identity Principles

| Identity | Policy |
|---|---|
| `candle_id` (raw/normalized) | Deterministically derivable from provider+symbol+timeframe+event-time+raw/normalization-version — never reused across a different candle. |
| `measurement_id` | Unique per (source candle + formula + rule version); recomputation under a new rule version produces a new ID, never overwrites. |
| `swing_id` | Unique per pivot; a `SUPERSEDED` swing keeps its own ID permanently — the new candidate gets its own new ID, linked via `superseded_by_swing_id`. **(`AUTHOR-APPROVED` rule — Meaningful Swing High and Swing Low Detection Standard V1, Ambiguity 10; only the generic `swing_id` uniqueness mechanism itself is `REQUIRES AUTHOR DECISION`, per Decision Gate #14.)** |
| `poi_id` | **Globally unique, never reused.** A newly formed POI (even of the same type, at a similar price) always receives a new `poi_id`. An invalidated POI is never reactivated under its old ID — a later valid reaction is a new POI with a new ID. |
| `interaction_event_id` | Unique per tap; taps are never merged or overwritten. |
| `lifecycle_event_id` | Unique per lifecycle-state transition; the full transition history is preserved, never overwritten. |
| `btmm_setup_id` | Unique per (POI + interaction + direction + formation timeframe + symbol + provider); a later eligible interaction always creates a new setup ID, never reactivates a cancelled one. **(`AUTHOR-APPROVED` rule — BTMM Lifecycle and Confirmation State Machine V1, Ambiguity 14; only the generic `btmm_setup_id` uniqueness mechanism itself is `REQUIRES AUTHOR DECISION`, per Decision Gate #14.)** |
| `annotation_id` | Unique per submitted annotation; a correction is a new ID with a reference to the superseded one, never an edit. |
| `provenance_id` | Unique per lineage record; one per subject record (1:1). |
| `replay_run_id` | Unique per replay execution; re-running the same range/versions produces a new run ID for comparison, not an overwrite of the prior run. |
| `rule_version_id` / `schema_version_id` | Unique, monotonically issued per published version; never reused, never deleted. |

**Binding rules:** identity generation must prevent silent reuse (e.g., via UUIDs or a strictly monotonic, collision-checked sequence — exact mechanism is Decision Gate #14, not chosen here). Manual and automatic evidence must remain distinguishable at all times via the `*_source` fields defined above — no contract merges a manual and an automatic evidence record into one row without preserving which is which.

## 4a. Processing-Version Field

A proposed `processing_version` field applies to every derived, normalized, validation, annotation, lifecycle, replay, and audit record where processing logic produced the record (contracts B through R above). It is **distinct from `rule_version`** (identifies which trading-rule/standard was applied) and **distinct from `schema_version`** (identifies the record's shape) — `processing_version` identifies which version of the *code/component* executed the applicable rule. For contract A (Raw Candle Record), `processing_version` **may be `NOT_APPLICABLE`** on the payload itself, since it received no processing; the ingestion-envelope record wrapping that payload still retains the ingestion component's own version separately. Reprocessing under a new `processing_version` always creates a new record (or a new Historical Replay Run output, contract P) — an old `processing_version` reference is never overwritten. **The exact version-number format (semantic versioning, sequential integer, content hash, etc.) is `REQUIRES AUTHOR DECISION`.** This field is proposed only; it is not implemented in any executable schema by this document.

## 5. Explicitly Out of Scope

No entry, stop-loss, take-profit, position-size, or risk field is defined in any contract above, per this task's explicit instruction and per the existing Phase 0G "Separation of Validity Concepts" principle (`docs/PROJECT_SCOPE.md` SS7). These remain a distinct, future, separately-authorized concern.

## 6. Approval Status

**ENGINEERING-RECOMMENDED**, pending author review. No contract above is implemented as executable code or schema. Field names and types are proposals only.

## 7. Post-Phase 1A Approved Decisions Affecting Contracts (Decision Groups 1–8)

**No executable model is created by this section; no approved trading-domain semantic (Sections 2–3 above) is changed by it.** Full decision detail is recorded canonically in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`. The following decisions are now `AUTHOR-APPROVED` (`NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`) and refine how the contracts above are expected to be implemented once a scaffold exists:

- **Identity mechanism (Group 4):** every identity field listed in SS4 above (`raw_candle_id`, `normalized_candle_id`, `measurement_id`, `swing_id`, `poi_id`, `interaction_event_id`, `lifecycle_event_id`, `btmm_setup_id`, `annotation_id`, `provenance_id`, `replay_run_id`, `rule_version_id`, `schema_version_id`) is approved to use **UUIDv7**. This resolves the previously-open "exact mechanism" question in the Identity Principles table (SS4) and Decision Gate #14 — the *never-reused/never-reassigned* rules stated in SS4 remain exactly as written and are unaffected.
- **Fingerprint (Group 4):** a `content_fingerprint` field, computed as **SHA-256**, is approved as a separate field from record identity on every contract — used for duplicate detection, integrity, and idempotency, never as a substitute for the identity field itself. Exact canonical field sets covered by the fingerprint per contract remain deferred to implementation.
- **Versioning scheme (Group 4):** `rule_version`, `schema_version`, and `processing_version` (SS4a) are approved to follow **MAJOR.MINOR.PATCH** semantic versioning: MAJOR = incompatible interpretation/contract change, MINOR = backward-compatible approved expansion, PATCH = clarification that does not alter intended behavior.
- **`processing_version` (SS4a):** unchanged in substance; now explicitly versioned per the MAJOR.MINOR.PATCH scheme above.
- **Time semantics (Group 3):** the canonical normalized time zone is approved as **UTC**, with the original source timezone always preserved on the raw record (Contract A). The exact candle-close timestamp convention, DST handling, trading-day boundary, week-start convention, month-boundary handling, and provider-session handling remain **`REQUIRES AUTHOR DECISION`**, exactly as stated in Contracts A and B above — this decision round resolves only the canonical-zone choice, not these remaining sub-decisions.
- **Canonical symbols and timeframes (Group 3):** the symbol list (`XAUUSD`, `EURUSD`, `GBPUSD`) and timeframe list (M1, M5, M15, H1, H3, H4, D1, W1) used throughout SS2–SS3 are confirmed unchanged; symbol representation is approved to add explicit `internal_symbol` / `provider` / `provider_symbol` / `display_symbol` / `symbol_mapping_version` fields to Contract A and Contract B, each versioned and explicit — no alias may be invented.
- **Completeness, duplicate, and gap statuses (Group 6):** Contract A (Raw Candle Record) and Contract B (Normalized Candle Record) are approved to carry `candle_completeness_status` (`CONFIRMED_COMPLETE` / `INCOMPLETE` / `UNKNOWN`), `duplicate_classification` (`EXACT_DUPLICATE` / `CONFLICTING_DUPLICATE` / `NOT_DUPLICATE`), and `gap_status` (`POTENTIAL_GAP` / `CONFIRMED_MISSING` / `EXPECTED_NON_TRADING_INTERVAL` / `RESOLVED`) fields. Only `CONFIRMED_COMPLETE` candles may become analytically eligible for Contract C (Derived Candle Measurement Record). The exact candidate key for duplicate detection and the exact gap-confirmation mechanism remain deferred to schema design.
- **Ingestion-boundary contracts (Group 7):** a provider-neutral request/result contract pair (not yet named A-R above) is approved in principle for the future `MarketDataSourcePort` interface; it is `INTERFACE_ONLY` and carries no provider-specific fields. This does not add a new lettered contract to SS3 by this document — the exact contract shape is deferred to implementation.
- **Manifest contracts (Group 8):** Contract Q (Rule-Version Manifest) and Contract R (Schema-Version Manifest) are approved to use **canonical UTF-8 JSON** as their machine-readable serialization format, with `rule_version_id`/`schema_version_id` as UUIDv7 and `content_fingerprint` as SHA-256 (per Group 4 above). Contract R's field-level "additive vs. breaking" change summary (SS3) is approved to use the three compatibility classes `BACKWARD_COMPATIBLE` / `BREAKING` / `DOCUMENTATION_ONLY`.
- **Pydantic v2 as source of truth (Group 1/8):** once implemented, Pydantic v2 models are approved as the source of truth for every contract above; any generated JSON Schema is a machine-readable export only and must never become independently edited truth.
- **Append-only supersession (unchanged):** the existing `SUPERSEDED`-swing and cancelled-BTMM-setup identity rules (Contracts D and H, already `AUTHOR-APPROVED` from Phase 0G) are unaffected by this decision round; UUIDv7 governs the *mechanism* of assigning `swing_id`/`btmm_setup_id`, not the *rule* for when a new one is assigned.

**No executable Pydantic model, JSON Schema file, or database table is created by this section.** All fields above remain proposed shapes only.
