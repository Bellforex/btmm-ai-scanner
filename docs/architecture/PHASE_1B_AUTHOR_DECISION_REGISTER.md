# Phase 1B Author Decision Register

**Document status:** This document is a **governance record of author decisions**, not a new engineering proposal. Every decision recorded below was made by the author, in chat, across Decision Groups 1 through 8, following the Phase 1A architecture planning package. **Recording a decision here does not implement it, install any technology, create any file, or authorize production use.** No repository scaffold, application code, executable schema, dependency file, configuration file, manifest file, test file, fixture file, CI workflow, database, migration, container, credential file, or provider adapter is created by this document.

---

## 1. Purpose

Record, in one canonical place, every author-approved Phase 1B architecture decision made across Decision Groups 1–8, and reconcile those decisions against the 17-item Technology-Stack Decision Register and the 20-item Architecture Decision Gate list from `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md`, so that the author-approval status of every item is unambiguous before any scaffold file is created.

## 2. Phase 1A Baseline Dependency

This register depends on, and does not restate or re-derive, the following prior approvals:

- **Phase 0G sign-off commit:** `23f43676abf6e032a5e96c4077d230cc2283f9b6` ("Approve Phase 0G controlled baseline") — Knowledge Gate **OPEN FOR CONTROLLED FOUNDATION WORK** only; all Phase 0G restrictions remain binding.
- **Phase 1A architecture-planning commit:** `a142da371c766bbc3489d7d9ae26e6421527c6c9` ("Document Phase 1A software foundation architecture") — the 16-layer architecture, 18-contract data model, provenance/validation/audit plan, deterministic testing plan, 17-item Technology-Stack Decision Register, and 20-item Architecture Decision Gate table, all as corrected in that commit.

Nothing in this register alters any Phase 0G trading rule, POI specification, lifecycle standard, or BTMM rule. Nothing in this register alters the Phase 1A layer structure, dependency direction, or evidence-label taxonomy — it only resolves specific technology and policy decisions that Phase 1A left open for author review.

## 3. Governance and Status Vocabulary

Every decision below carries **four independent status axes**. Approving a decision on one axis never silently erases or overwrites another axis — in particular, **approving a decision does not erase its engineering origin.**

| Axis | Meaning | Values used in this document |
|---|---|---|
| **Recommendation origin** | How confidently Phase 1A engineering work proposed this answer, before author approval. | `ENGINEERING-RECOMMENDED` (a single, confidently-proposed answer), `ENGINEERING-PROVISIONAL` (a proposed answer with an acknowledged, currently-unresolved sub-question), `DEFERRED` (the proposed answer was explicitly "do not build this yet") |
| **Current author-decision status** | Whether the author has actually decided this item. | `AUTHOR-APPROVED` (every item in this document) |
| **Implementation status** | Whether the decision has been turned into working software. | `NOT YET IMPLEMENTED` (every item in this document — no scaffold exists) |
| **Production status** | Whether the decision, even once implemented, could be used for live/production purposes. | `NOT PRODUCTION-APPROVED` (every item in this document — no production approval has ever been given at any phase) |

**Binding rule:** `AUTHOR-APPROVED` + `NOT YET IMPLEMENTED` + `NOT PRODUCTION-APPROVED` is the status of every decision in this register. None of the three statements substitutes for either of the others.

---

## 4. Decision Group 1 — Core Python Toolchain

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Primary language and initial runtime | Python 3.12 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Runtime-version policy | Pin one exact Python 3.12 patch version during the scaffold task; change only through reviewed updates | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Package manager | uv | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Central project manifest | `pyproject.toml` | ENGINEERING-RECOMMENDED (newly made explicit as its own decision in this group; previously implicit under the package-manager item) | AUTHOR-APPROVED | NOT YET IMPLEMENTED — **the file itself is not created by this document** | NOT PRODUCTION-APPROVED |
| Reproducibility lockfile | `uv.lock`, must be committed once created | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED — **the file itself is not created by this document** | NOT PRODUCTION-APPROVED |
| Schema and validation | Pydantic v2 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Testing | pytest | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Static typing | mypy | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Formatting | Ruff formatter | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Linting | Ruff linter | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

No `pyproject.toml`, `uv.lock`, or any Python file is created by this document.

## 5. Decision Group 2 — Storage Foundation

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Storage formats | Parquet for bulk tabular historical records; JSONL for append-only event and audit streams | ENGINEERING-PROVISIONAL | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Initial database strategy | No database during the initial scaffold; file-based contracts first | DEFERRED (recommended answer was, and remains, "do not build yet") | AUTHOR-APPROVED (the *deferral itself* is now an author-approved position, not merely an engineering suggestion) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Raw-data storage strategy | Append-only, immutable, partitioned, provider-traceable | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Migration strategy | No database migration system until a database is separately approved | DEFERRED | AUTHOR-APPROVED (the deferral itself) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Raw data must preserve** (binding requirement on the raw-data storage strategy decision above): original provider values; provider identity; feed identity; provider symbol; provider timeframe; retrieval metadata; ingestion metadata; quarantine and validation traceability; separation from normalized records.

**Still deferred within this group** (not resolved by this document): exact raw-payload physical encoding; retention periods; partition naming; database selection (once a database is eventually approved). See Part 14 below.

## 6. Decision Group 3 — Time, Symbols and Configuration

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Canonical normalized time zone | UTC | ENGINEERING-PROVISIONAL (Phase 1A labeled canonical-UTC-with-source-preservation `ENGINEERING-PROVISIONAL`) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Canonical internal symbols | XAUUSD, EURUSD, GBPUSD, represented via separate `internal_symbol` / `provider` / `provider_symbol` / `display_symbol` / `symbol_mapping_version` fields | Underlying symbol list: `AUTHOR-APPROVED` pre-existing (Phase 0G, `docs/PROJECT_SCOPE.md`); the field-separation scheme itself: ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Canonical timeframe enum | M1, M5, M15, H1, H3, H4, D1, W1 — uppercase internal enum values | Underlying timeframe list: `AUTHOR-APPROVED` pre-existing (Phase 0G); the enum/representation mechanism itself: ENGINEERING-PROVISIONAL | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Configuration-file format | YAML for human-managed configuration; versioned machine-readable manifest for configuration lineage | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Secrets-management strategy | Environment variables as runtime source; git-ignored local `.env` for development convenience only | ENGINEERING-PROVISIONAL | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Time-zone requirements:** preserve original provider timestamp; preserve source time-zone metadata; never interpret an unknown time zone silently; keep conversions provenance-traceable.

**Symbol/timeframe rules:** provider mappings must be explicit and versioned; preserve provider-native timeframe representations; no silent resampling; no inference when provider metadata conflicts.

**Configuration precedence (author-approved order):** (1) versioned project defaults; (2) versioned environment-specific configuration; (3) runtime environment variables.

**Secrets rules:** no hard-coded secrets; no secrets in YAML or manifests; no secrets in logs, validation reports, or audit events; no silent fallback credentials.

**Still unresolved within this group** (explicitly not resolved by this document): exact candle-close timestamp convention; DST handling; trading-day boundary; week-start convention; month-boundary handling; provider-session handling; Phase 0G period-rollover questions (`P0G-B013A`). See Part 14 below.

## 7. Decision Group 4 — Identity, Versioning and Audit

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Record identity | UUIDv7 | ENGINEERING-RECOMMENDED (newly proposed and approved by this decision group; Phase 1A had left the exact identity mechanism to Decision Gate #14) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Content fingerprint | SHA-256, kept as `content_fingerprint`, separate from record identity | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Versioning scheme | MAJOR.MINOR.PATCH | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Lineage field set | `source_record_id`, `provenance_id`, `schema_version`, `rule_version`, `processing_version`, `created_at`, `supersedes_id` (where applicable), `derived_from_id` (where applicable), `replay_run_id` (where applicable) | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Audit storage/identity | Storage = JSONL; policy = append-only; audit identity = UUIDv7; corrections use new linked events | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**UUIDv7 applies to future:** candles, measurements, swings, POIs, interaction events, lifecycle events, BTMM setups, annotations, provenance records, replay runs, audit events, rule-version manifests, schema-version manifests.

**Identity rules:** immutable; never silently reused; new POI formation receives a new `poi_id`; a cancelled BTMM setup is never reactivated under its former ID; reprocessing creates a new record identity; historical identity is never reassigned.

**Fingerprint rules:** `content_fingerprint` remains separate from record identity; a fingerprint may support duplicate detection, integrity, and idempotency; exact canonical contract field sets covered by the fingerprint remain deferred (see Part 14).

**Versioning meaning:** MAJOR = incompatible interpretation or contract change; MINOR = backward-compatible approved expansion; PATCH = clarification that does not alter intended behavior.

**Versioning rules:** published versions are immutable; historical records retain their original versions; reprocessing creates new outputs; historical parents are not overwritten; corrections and supersession are append-only.

**Audit rules:** audit events describe what happened; audit events do not alter domain truth. Audit records must exclude: passwords; tokens; API keys; `.env` contents; unredacted credentials; private-book text; unnecessary personal information.

## 8. Decision Group 5 — CI, Logging and Reproducibility

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Operational logging | Python standard `logging`, structured JSON output; kept separate from authoritative audit events | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| CI platform | GitHub Actions | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Initial CI checks | Ruff format check; Ruff lint; mypy; pytest | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Manifest / lockfile discipline | Manifest = `pyproject.toml`; lockfile = `uv.lock`, must be committed once created | ENGINEERING-RECOMMENDED (cross-references Group 1) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Containerization strategy | DEFERRED — no containerization during the initial scaffold | DEFERRED | AUTHOR-APPROVED (the deferral itself) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**CI restrictions:** offline-safe by default; no broker credentials; no FXCM credentials; no TradingView credentials; no private-book access; no live accounts; no deployment; no signals; no order execution; CI must not modify files silently.

**Lockfile/manifest rules:** dependency changes require review; lockfile regeneration is reviewed; no silently floating dependency resolution; secrets prohibited from `pyproject.toml`.

**During the initial scaffold:** no `Dockerfile`; no `docker-compose.yml`; no container-specific deployment assumptions.

**Explicit non-implication:** passing CI does not imply profitability, market-data validity, model approval, signal safety, execution authorization, or production readiness.

## 9. Decision Group 6 — Candle Data-Quality Policies

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Candle-completeness policy | `candle_completeness_status = CONFIRMED_COMPLETE \| INCOMPLETE \| UNKNOWN`; only `CONFIRMED_COMPLETE` candles may become analytically eligible | ENGINEERING-RECOMMENDED (resolves Gate #10, previously `REQUIRES MORE RESEARCH`) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Duplicate-candle policy | `duplicate_classification = EXACT_DUPLICATE \| CONFLICTING_DUPLICATE \| NOT_DUPLICATE`; candidate key based on provider + provider_symbol + provider_timeframe + candle_open_time | ENGINEERING-RECOMMENDED (resolves Gate #11, previously `REQUIRES MORE RESEARCH`) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Missing-candle policy | No synthetic candle creation; `gap_status = POTENTIAL_GAP \| CONFIRMED_MISSING \| EXPECTED_NON_TRADING_INTERVAL \| RESOLVED` | ENGINEERING-RECOMMENDED (resolves Gate #12, previously `REQUIRES MORE RESEARCH`) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Completeness rules:** wall-clock time alone does not prove completion; a later completed observation is a new immutable record; completeness is data quality, not trading validity.

**Duplicate rules:** the exact final candidate-key field set remains deferred to schema design (see Part 14). Exact duplicates — preserve every raw envelope; do not create multiple equivalent normalized candles; record duplicate occurrence in validation and audit; do not overwrite the first record. Conflicting duplicates — `QUARANTINED`; preserve every raw record; do not choose a winner silently; do not normalize automatically; do not create measurements; require explicit reviewed resolution.

**Missing-candle rules:** no forward fill; no back fill; no OHLC interpolation; no previous-close copying; no invented zero-volume candles; no silent time compression. A gap becomes `CONFIRMED_MISSING` only under an approved provider/session policy; `POTENTIAL_GAP` and `CONFIRMED_MISSING` make contiguous windows data-ineligible; non-contiguous calculation is allowed only where an approved rule explicitly permits it; gap status affects data eligibility only — it does not automatically invalidate a POI or BTMM setup.

**Clarification (binding on this whole group):** these three policies are resolved at the **policy-decision level**. The provider-specific completion-evidence mechanism, the exact canonical candle-key field set, and any concrete detection implementation remain deferred (see Part 14). **A resolved policy decision does not mean its software exists.**

## 10. Decision Group 7 — Ingestion-Adapter Boundary

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Ingestion architecture | Provider-neutral ports-and-adapters boundary; core interface = `MarketDataSourcePort` | ENGINEERING-RECOMMENDED (resolves Gate #13, previously `REQUIRES MORE RESEARCH`) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Initial scaffold position | `INTERFACE_ONLY` | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Early retrieval mode | `OFFLINE_FILE` only | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Permitted during the scaffold:** provider-neutral request contracts; provider-neutral result contracts; adapter metadata requirements; validation hooks; provenance hooks; deterministic offline test doubles where necessary.

**Not approved (by this or any prior document):** live FXCM adapter; TradingView adapter; TradingView scraping; broker authentication; polling; streaming; automated download; network connector.

**Future, not yet authorized:** `HISTORICAL_BATCH`; `POLLING`; `STREAMING` retrieval modes.

**Approved processing sequence:**

```
Retrieval request
  → provider adapter
    → immutable source envelope
      → raw-payload preservation
        → envelope and contract validation
          → parsed raw-candle candidates
            → completeness, duplicate and gap validation
              → normalization eligibility decision
                → normalization boundary
```

**Adapter rules:** raw payload is preserved before normalization; parsing does not authorize normalization; explicit validation eligibility is required; the adapter preserves the original provider symbol; canonical mapping is explicit and versioned; the adapter may not invent aliases; the adapter may not decide POI, market direction, or BTMM validity; the adapter may not resample or fill gaps; the adapter may not choose conflicting duplicates; the adapter may not create measurements, signals, or trades; the adapter may not modify existing raw records.

**Ingestion result version references:** `adapter_version`, `configuration_version`, `schema_version`, `processing_version`, `symbol_mapping_version`, `validation_policy_version`.

**Failure classes (kept distinct):** `transport_failure`, `parsing_failure`, `validation_failure`. No silent repair, discard, infinite retry, or credential leakage.

**Canonical reference (unchanged from Phase 1A):** FXCM data displayed through TradingView remains the canonical visual/feed reference. This does **not** approve: TradingView API access; scraping; FXCM connectivity; licensing; or any specific retrieval mechanism.

## 11. Decision Group 8 — Rule and Schema Version Manifests

| Decision | Approved value | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Machine-readable manifest format | Canonical UTF-8 JSON | ENGINEERING-RECOMMENDED (resolves Gate #15) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Schema versioning strategy | Compatibility classes `BACKWARD_COMPATIBLE` \| `BREAKING` \| `DOCUMENTATION_ONLY`, mapped to MAJOR/MINOR/PATCH | ENGINEERING-RECOMMENDED (resolves Gate #16) | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Schema source of truth | Pydantic v2 models | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Generated JSON Schema role | Machine-readable export only; must not become independently edited truth | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Manifest identity | `rule_version_id` = UUIDv7; `schema_version_id` = UUIDv7; `content_fingerprint` = SHA-256 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

Human-managed configuration remains YAML (unchanged, Group 3).

**Manifest properties:** immutable; versioned; git-reviewable; deterministically serializable; traceable to source commit; SHA-256 fingerprinted; superseded by newer manifests, never silently edited.

**Rule-version manifest proposed fields:** `manifest_type`, `rule_version_id`, `rule_family`, `version`, `status`, `effective_at_utc`, `source_document_paths`, `source_commit`, `author_approval_reference`, `evidence_labels`, `measurement_standard_versions`, `poi_specification_versions`, `lifecycle_standard_versions`, `dependencies`, `supersedes_version`, `content_fingerprint`, `created_at_utc`.

**Rule-manifest rules:** the manifest records approved knowledge; the manifest does not create or approve a trading rule; source documents must already be governed; no private-book text; historical outputs retain the exact manifest used; a referenced rule change requires a new manifest version.

**Schema-version manifest proposed fields:** `manifest_type`, `schema_version_id`, `schema_family`, `version`, `compatibility_class`, `source_model_paths`, `generated_schema_references`, `source_commit`, `processing_version`, `dependencies`, `supersedes_version`, `content_fingerprint`, `created_at_utc`.

**Breaking-change examples:** removing required fields; renaming fields without compatibility handling; changing field meaning; incompatible type changes; identity-semantics changes; timestamp-semantics changes; enum-meaning changes; making an optional field required.

**Version-bump mapping:** breaking change → new MAJOR version; backward-compatible expansion → normally new MINOR version; documentation-only clarification → PATCH only where validation, interpretation, and behavior do not change. **Adding enum values is not automatically safe.**

**Historical schema policy:** historical `schema_version` remains immutable; historical records are not silently rewritten; reprocessing creates new records or replay outputs; future migrations must be explicit, versioned, and audited.

**Fingerprint scope:** covers canonical serialized manifest content, excluding the fingerprint field itself. **Exact canonical JSON serialization procedure remains deferred to implementation** (see Part 14).

**Approved future scaffold destinations:** `manifests/rules/`, `manifests/schemas/`. **No files are created in those directories by this documentation task.**

---

## 12. Final 17-Item Technology Decision Register

| # | Decision | Approved recommendation | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|---|
| 1 | Primary language and initial runtime | Python 3.12 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 2 | Runtime-version policy | Pin one exact Python 3.12 patch version; change only through reviewed updates | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 3 | Package manager | uv — with `pyproject.toml` as the central project manifest and a committed `uv.lock` reproducibility lockfile | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED — **neither file is created by this document** | NOT PRODUCTION-APPROVED |
| 4 | Schema and validation | Pydantic v2 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 5 | Testing framework | pytest | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 6 | Static typing | mypy | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 7 | Formatting | Ruff formatter | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 8 | Linting | Ruff linter | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 9 | Storage formats | Parquet for bulk tabular historical records; JSONL for append-only event and audit streams | ENGINEERING-PROVISIONAL | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 10 | Initial database strategy | No database during the initial scaffold; file-based contracts first | DEFERRED | AUTHOR-APPROVED (the deferral itself) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 11 | Raw-data storage strategy | Append-only, immutable, partitioned file storage | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 12 | Logging | Python standard library `logging` with structured JSON output | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 13 | Configuration-file format | YAML for human-managed configuration, plus a versioned machine-readable manifest | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 14 | Migration strategy | No database migration system until a database is approved | DEFERRED | AUTHOR-APPROVED (the deferral itself) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 15 | CI strategy | GitHub Actions | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 16 | Containerization strategy | No containerization during the initial scaffold | DEFERRED | AUTHOR-APPROVED (the deferral itself) | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| 17 | Secrets-management strategy | Environment variables as runtime source; git-ignored local `.env` permitted only for local development convenience | ENGINEERING-PROVISIONAL | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Totals: 17 decisions, 17 `AUTHOR-APPROVED`, 17 `NOT YET IMPLEMENTED`, 17 `NOT PRODUCTION-APPROVED`.** Recommendation origins are preserved exactly as they were in `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` Part 7: 12 `ENGINEERING-RECOMMENDED`, 2 `ENGINEERING-PROVISIONAL` (items 9, 17), 3 `DEFERRED` (items 10, 14, 16). No item's engineering origin was erased or upgraded to `AUTHOR-APPROVED` in place of its origin — the two axes are recorded side by side. **No `pyproject.toml` or `uv.lock` file is created by this document.**

---

## 13. Final 20-Gate Resolution Matrix

| # | Gate name | Original readiness classification | Approving decision group | Current decision status | Implementation status | Remaining sub-decisions | Scaffold blocking status |
|---|---|---|---|---|---|---|---|
| 1 | Primary language and runtime | READY FOR AUTHOR DECISION | Group 1 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact Python 3.12 patch version | Not blocking further decision review; blocks scaffold pending separate scaffold-entry instruction |
| 2 | Package manager | READY FOR AUTHOR DECISION | Group 1 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond file creation itself | Same as above |
| 3 | Schema-validation technology | READY FOR AUTHOR DECISION | Group 1 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond model authoring | Same as above |
| 4 | Testing framework | READY FOR AUTHOR DECISION | Group 1 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond test authoring | Same as above |
| 5 | Initial storage format | READY FOR AUTHOR DECISION | Group 2 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact raw-payload physical encoding; partition naming | Same as above |
| 6 | Initial database position | READY FOR AUTHOR DECISION | Group 2 | AUTHOR-DECISION RESOLVED (defer confirmed) | NOT YET IMPLEMENTED | Future database selection (only if/when adopted) | Same as above |
| 7 | Time-zone canonicalization | READY FOR AUTHOR DECISION | Group 3 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact candle-close timestamp convention; DST handling; trading-day boundary; week-start convention; month-boundary handling; provider-session handling | Same as above |
| 8 | Symbol-normalization convention | READY FOR AUTHOR DECISION | Group 3 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond field implementation | Same as above |
| 9 | Timeframe-enum convention | READY FOR AUTHOR DECISION | Group 3 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond enum implementation | Same as above |
| 10 | Candle-completeness policy | REQUIRES MORE RESEARCH | Group 6 | AUTHOR-DECISION RESOLVED (policy level) | NOT YET IMPLEMENTED | Provider completion-evidence mechanism | Same as above |
| 11 | Duplicate-candle policy | REQUIRES MORE RESEARCH | Group 6 | AUTHOR-DECISION RESOLVED (policy level) | NOT YET IMPLEMENTED | Exact canonical candle-key field set | Same as above |
| 12 | Missing-candle policy | REQUIRES MORE RESEARCH | Group 6 | AUTHOR-DECISION RESOLVED (policy level) | NOT YET IMPLEMENTED | Provider/session-specific gap-confirmation mechanism | Same as above |
| 13 | Ingestion-adapter boundary | REQUIRES MORE RESEARCH | Group 7 | AUTHOR-DECISION RESOLVED (policy/architecture level) | NOT YET IMPLEMENTED | Provider-specific adapters; FXCM connectivity; TradingView retrieval/scraping; data licensing; network retry/backoff policy | Same as above |
| 14 | Identifier-generation strategy | READY FOR AUTHOR DECISION | Group 4 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact fingerprint field sets per contract | Same as above |
| 15 | Rule-version-manifest format | READY FOR AUTHOR DECISION | Group 8 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact canonical JSON serialization procedure | Same as above |
| 16 | Schema-versioning strategy | READY FOR AUTHOR DECISION | Group 8 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Exact canonical JSON serialization procedure | Same as above |
| 17 | Audit-log format | READY FOR AUTHOR DECISION | Group 4 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond implementation | Same as above |
| 18 | Configuration hierarchy | READY FOR AUTHOR DECISION | Group 3 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond implementation | Same as above |
| 19 | Secret-handling boundary | READY FOR AUTHOR DECISION | Group 3 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | None beyond implementation | Same as above |
| 20 | CI policy | READY FOR AUTHOR DECISION | Group 5 | AUTHOR-DECISION RESOLVED | NOT YET IMPLEMENTED | Branch-protection policy; mandatory pull-request policy | Same as above |

**Original readiness snapshot, preserved unchanged:** READY FOR AUTHOR DECISION = **16**. REQUIRES MORE RESEARCH = **4**. DEFERRED BEYOND PHASE 1B = **0**. Total = **20**. This historical snapshot is not silently replaced — it remains the accurate description of gate *readiness* as of the Phase 1A commit `a142da371c766bbc3489d7d9ae26e6421527c6c9`.

**Current post-decision status:** AUTHOR-DECISION RESOLVED = **20**. PENDING AUTHOR DECISION = **0**. IMPLEMENTED = **0**. PRODUCTION-APPROVED = **0**.

**Clarification (binding):** Gates 10, 11, 12, and 13 are resolved **at the policy-decision level only**. Provider-specific mechanisms (which provider API, exact completion-evidence source, exact candle-key field set, network retry/backoff behavior, etc.) and all implementation details remain deferred, per Part 14 below. **A resolved decision gate does not mean its software exists.** No gate's `IMPLEMENTED` or `PRODUCTION-APPROVED` count has moved from zero.

---

## 14. Remaining Implementation Sub-Decisions

The following remain unresolved, deferred, or implementation-specific — **none is presented as resolved by this document**:

- Exact Python 3.12 patch version
- Exact raw provider-payload encoding
- Retention policy
- Partition naming
- Exact fingerprint field sets
- Canonical JSON serialization procedure
- Exact validation-status enum
- Validation gating implementation mechanism
- Exact candle-close timestamp convention
- DST normalization details
- Trading-day boundary
- Week-start convention
- Month-boundary handling
- Provider-session handling
- Provider completion-evidence mechanism
- Exact canonical candle-key field set
- Provider-specific adapters
- FXCM connectivity
- TradingView retrieval or scraping
- Data licensing
- Network retry and backoff policy
- Branch-protection policy
- Mandatory pull-request policy
- Future database selection
- Future database migrations
- Future containerization
- Future Risk-Control Interface
- Entry, stop loss, take profit, position sizing and risk rules
- AI, signals and execution

## 15. Prohibited Implementation Scope (This Task)

This document does not, and no companion edit made alongside it does:

- Create the repository scaffold or any application directory (`src/`, `app/`, `tests/`, `config/`, `scripts/`, `.github/`, `manifests/`, `data/`, `fixtures/`, `migrations/`)
- Create application code of any kind
- Create any executable schema (Pydantic model, JSON Schema file, database table)
- Install or configure any technology
- Create `pyproject.toml`, `uv.lock`, any CI workflow file, any source directory, any test directory, any manifest file, any configuration file, any fixture, any database, any migration, any container file, or any `.env` file
- Create a provider adapter of any kind
- Stage, commit, or push anything

## 16. Phase 1B Scaffold-Entry Status

**The Phase 1B repository scaffold has not been created and is not authorized by this document.** Author approval of the decisions recorded in this register resolves *what* the scaffold should eventually contain — it does not itself authorize *creating* any file. A separate, explicit, future instruction is required before any scaffold directory, manifest, dependency file, configuration file, contract stub, validation stub, test file, or CI file is created. The next controlled task is: **Phase 1B repository scaffold implementation — define and review the exact directory, configuration, manifest, contract-stub, validation-stub, test and CI file scope before creating any files.**

## 17. Approval Status

This document is a **governance record**, not an engineering recommendation of its own. It records that the author has approved the decisions in Decision Groups 1 through 8, as stated by the author. It does not itself carry an `ENGINEERING-RECOMMENDED`/`ENGINEERING-PROVISIONAL`/`DEFERRED` label, because it proposes nothing new — every value recorded here traces to either a pre-existing Phase 1A engineering recommendation (Part 7/Part 10 of `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md`) now marked `AUTHOR-APPROVED`, or to a decision the author stated directly in this task's instruction (e.g., UUIDv7, SHA-256, MAJOR.MINOR.PATCH, the candle data-quality enums, the ingestion-adapter boundary, the manifest formats). **No decision in this document is self-approving; every one is attributed to an explicit author statement.** No technology is installed. No scaffold exists. No file outside this document's own creation and the six companion updates listed in the governing task instruction is affected.

---

## 18. Phase 1B-A Implementation Checkpoint

**This section is an addition, not a replacement.** Sections 12 and 13 above remain the accurate historical record of the Phase 1B decision content at the time this register was authored — every row there correctly showed `NOT YET IMPLEMENTED` at that point, and that snapshot is not rewritten. This section records what has since actually been built, verified, committed, and pushed.

### 18a. Implementation Commit

- **Commit hash:** `47cfd699bb7f4893774579f1693abbbb57b91607`
- **Commit message:** "Implement Phase 1B-A software foundation"
- **Exact ten committed paths:** `.gitignore` (modified); `.python-version`, `pyproject.toml`, `src/btmm_ai_scanner/__init__.py`, `src/btmm_ai_scanner/config/__init__.py`, `src/btmm_ai_scanner/config/enums.py`, `src/btmm_ai_scanner/config/loader.py`, `tests/test_config_precedence.py`, `tests/test_import_smoke.py`, `uv.lock` (all new)
- **Commit statistics:** 1 modified file, 9 added files, 596 insertions, 1 deletion

### 18b. Verification Results (as committed and re-verified)

| Check | Result |
|---|---|
| `uv` version | `0.11.30` |
| Python version | `3.12.13` |
| `uv lock --check` | PASS |
| Package import verification | PASS |
| Ruff format check | PASS |
| Ruff lint | PASS |
| mypy (strict) | PASS |
| pytest collection | 34 |
| pytest result | 34 passed |
| Runtime dependency count | 0 |
| `pytest` resolved version | 9.1.1 |
| `mypy` resolved version | 2.3.0 |
| Ruff resolved version | 0.15.22 |

### 18c. Explicit Author Exception (Governance)

**Technical implementation: `ACCEPTED`.** **Procedural deviations: `DISCLOSED AND EXCEPTIONALLY ACCEPTED`** — during the original Batch 1B-A execution, two genuine bugs surfaced during the mandatory verification suite (a Ruff `RUF100`/`F401` finding, and a Windows-specific `PermissionError` from `tempfile.TemporaryDirectory` cleanup racing against a still-active `chdir`). Both were fixed by directly editing the already-in-scope test file rather than stopping and requesting separate author re-authorization, as the governing stop-and-report procedure required. A subsequent, independent, read-only forensic review confirmed both fixes were correct, narrowly scoped to the two already-approved files, and did not weaken any approved assertion. The author reviewed this disclosed deviation and accepted the resulting implementation **by explicit exception**, rather than requiring a rollback or re-execution.

### 18d. Python Minor-Version Alias Anomaly (External Toolchain)

**`ACKNOWLEDGED`, `EXTERNAL`, `FUNCTIONALLY LIMITED`, `NON-BLOCKING FOR THIS EXACT-PATCH PROJECT`.** `uv python install 3.12.13 --no-bin` returned exit code 2 (`Missing expected target directory for Python minor version link`). Forensic review confirmed the exact-version install directory (`cpython-3.12.13-windows-x86_64-none`) is complete and fully functional; only the generic minor-version convenience alias (`cpython-3.12-windows-x86_64-none`) is a dangling junction. This project pins the exact patch via `.python-version` and never references the generic alias, so the anomaly does not affect this repository. It remains an external machine-toolchain condition — **no repair was authorized or performed**, and none is required for this project's own correctness.

### 18e. Production and Next-Phase Status

**Production status: `NOT PRODUCTION-APPROVED`.** No trading, ingestion, model, signal, risk, or execution capability exists or is approved. **Batch 1B-B has not begun.** Knowledge Gate remains **OPEN FOR CONTROLLED FOUNDATION WORK** only; all Phase 0G restrictions remain binding.

### 18f. Updated 17-Item Technology Register — Current Implementation Status

**This table supplements, and does not replace, Section 12's historical snapshot.** "Implementation status" below reflects only what Batch 1B-A actually built; author-decision status is unchanged from Section 12.

| # | Decision | Current implementation status | Justification |
|---|---|---|---|
| 1 | Primary language and initial runtime | **IMPLEMENTED** | Python 3.12.13 installed (externally, via uv) and verified running (`uv run --locked python --version` → `Python 3.12.13`); `.python-version` and `pyproject.toml requires-python` both reference it. |
| 2 | Runtime-version policy | **IMPLEMENTED** | `.python-version` pins the exact patch `3.12.13`; the file is committed and reviewed. |
| 3 | Package manager | **IMPLEMENTED** | `uv` 0.11.30 installed and used throughout; `pyproject.toml` and committed `uv.lock` both exist and verify (`uv lock --check` passes). |
| 4 | Schema and validation | **NOT YET IMPLEMENTED** | Pydantic is not a dependency of Batch 1B-A (zero runtime dependencies); it remains planned for Batch 1B-B only. |
| 5 | Testing framework | **IMPLEMENTED** | `pytest` 9.1.1 installed as a dev dependency; 34 tests collected and passing. |
| 6 | Static typing | **IMPLEMENTED** | `mypy` 2.3.0 installed and configured `strict = true`; passes with zero issues on `src` and `tests`. |
| 7 | Formatting | **IMPLEMENTED** | Ruff formatter configured (`[tool.ruff]`); `ruff format --check .` passes. |
| 8 | Linting | **IMPLEMENTED** | Ruff linter configured (`[tool.ruff.lint]`); `ruff check .` passes. |
| 9 | Storage formats | **NOT YET IMPLEMENTED** | No Parquet or JSONL code exists anywhere in Batch 1B-A — explicitly out of this batch's scope. |
| 10 | Initial database strategy | **NOT YET IMPLEMENTED** | The deferral is a policy position, not an implementation; no database-related code exists. Not marked implemented merely because the deferral holds true. |
| 11 | Raw-data storage strategy | **NOT YET IMPLEMENTED** | No raw-data storage code exists; this belongs to a later batch. |
| 12 | Logging | **NOT YET IMPLEMENTED** | No structured logging code exists; `loader.py` explicitly excludes logging from its own scope. |
| 13 | Configuration-file format | **NOT YET IMPLEMENTED** | No YAML file or versioned manifest exists. The env-var precedence *loader mechanism* now has code support, but that is a distinct Decision Group 3 concern from the YAML file-format decision itself, which remains unbuilt. |
| 14 | Migration strategy | **NOT YET IMPLEMENTED** | No migration tooling or code exists; deferral remains a policy position only. |
| 15 | CI strategy | **NOT YET IMPLEMENTED** | No `.github/workflows/` file exists; CI remains Batch 1B-F scope. |
| 16 | Containerization strategy | **NOT YET IMPLEMENTED** | No container file exists; deferral remains a policy position only. |
| 17 | Secrets-management strategy | **PARTIALLY IMPLEMENTED** | The non-secret configuration loader's secret-*rejection* boundary is fully implemented and tested (18 parametrized cases); actual secret *retrieval*/runtime secret-loading remains a separate, unbuilt, future boundary. |

**Current totals: IMPLEMENTED = 7 (items 1, 2, 3, 5, 6, 7, 8). PARTIALLY IMPLEMENTED = 1 (item 17). NOT YET IMPLEMENTED = 9 (items 4, 9, 10, 11, 12, 13, 14, 15, 16). Total = 17.** No item marked implemented merely because a deferral-by-policy happens to hold true.

### 18g. Updated 20-Gate Matrix — Current Implementation Status

**This table supplements, and does not replace, Section 13's historical snapshot.** The original readiness snapshot (READY FOR AUTHOR DECISION = 16, REQUIRES MORE RESEARCH = 4, DEFERRED BEYOND PHASE 1B = 0) and the "AUTHOR-DECISION RESOLVED = 20 / IMPLEMENTED = 0 / PRODUCTION-APPROVED = 0" historical checkpoint in Section 13 remain unchanged and printed above, exactly as before.

| # | Gate name | Current implementation status | Justification |
|---|---|---|---|
| 1 | Primary language and runtime | **IMPLEMENTED** | Python 3.12.13 installed and verified running. |
| 2 | Package manager | **IMPLEMENTED** | `uv` installed; `pyproject.toml`/`uv.lock` exist and verify. |
| 3 | Schema-validation technology | **NOT YET IMPLEMENTED** | Pydantic not used in Batch 1B-A. |
| 4 | Testing framework | **IMPLEMENTED** | pytest installed; 34 tests passing. |
| 5 | Initial storage format | **NOT YET IMPLEMENTED** | No Parquet/JSONL code exists. |
| 6 | Initial database position | **NOT YET IMPLEMENTED** | No database code exists; deferral is a policy position only. |
| 7 | Time-zone canonicalization | **NOT YET IMPLEMENTED** | No candle/time-handling code exists in Batch 1B-A. |
| 8 | Symbol-normalization convention | **PARTIALLY IMPLEMENTED** | `InternalSymbol` enum now exists in code; the full convention (provider/provider_symbol/display_symbol/symbol_mapping_version fields) is Batch 1B-B data-contract scope. |
| 9 | Timeframe-enum convention | **PARTIALLY IMPLEMENTED** | `Timeframe` enum now exists in code; provider-native preservation and no-resampling enforcement require ingestion/normalization code not yet built. |
| 10 | Candle-completeness policy | **NOT YET IMPLEMENTED** | No candle code exists. |
| 11 | Duplicate-candle policy | **NOT YET IMPLEMENTED** | No candle code exists. |
| 12 | Missing-candle policy | **NOT YET IMPLEMENTED** | No candle code exists. |
| 13 | Ingestion-adapter boundary | **NOT YET IMPLEMENTED** | Batch 1B-E scope, not yet reached. |
| 14 | Identifier-generation strategy | **NOT YET IMPLEMENTED** | No UUIDv7/fingerprint type code exists; Batch 1B-B scope. |
| 15 | Rule-version-manifest format | **NOT YET IMPLEMENTED** | No manifest code exists. |
| 16 | Schema-versioning strategy | **NOT YET IMPLEMENTED** | No schema-versioning code exists. |
| 17 | Audit-log format | **NOT YET IMPLEMENTED** | Batch 1B-D scope, not yet reached. |
| 18 | Configuration hierarchy | **IMPLEMENTED** | The three-level precedence (defaults → environment overrides → runtime environment) is fully coded in `loader.py` and covered by 11 passing tests. |
| 19 | Secret-handling boundary | **PARTIALLY IMPLEMENTED** | Batch 1B-A implements the non-secret configuration rejection boundary and repository hygiene for local `.env` files (secret-like key rejection, fully coded and covered by 18 passing parametrized test cases across 6 indicators × 3 layers; generic non-disclosing exceptions; `.env`/`.env.*` git-ignore protection). The dedicated runtime secret-retrieval boundary and enforcement across future logging, manifests, audit, provider, and production components remain unimplemented. |
| 20 | CI policy | **NOT YET IMPLEMENTED** | No `.github/workflows/` file exists; Batch 1B-F scope. |

**Current totals (corrected): IMPLEMENTED = 4 (gates 1, 2, 4, 18). PARTIALLY IMPLEMENTED = 3 (gates 8, 9, 19). NOT YET IMPLEMENTED = 13 (gates 3, 5, 6, 7, 10, 11, 12, 13, 14, 15, 16, 17, 20). Total = 20.** PRODUCTION-APPROVED remains **0** for every gate. *(Correction note: gate 19 was originally, incorrectly listed as fully `IMPLEMENTED` — it is corrected here to `PARTIALLY IMPLEMENTED`, since only the secret-*rejection* boundary exists; the dedicated runtime secret-retrieval boundary does not. This moves gate 19 from the `IMPLEMENTED` bucket to the `PARTIALLY IMPLEMENTED` bucket; no other gate's classification changed.)*

---

## 19. Phase 1B-B Decision Group 1 — Dependencies and Value-Type Boundary

**Status: `AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`. `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`.** This section records decisions that resolve *what* Batch 1B-B's dependency and value-type boundary will be — it does not create `contracts/`, `tests/unit/`, any schema, any manifest, or any generated file, and it does not modify `pyproject.toml` or `uv.lock`. No dependency is installed or locked by this section.

### 19A. Pydantic Runtime Dependency

**Approved future project dependency:** `pydantic>=2.13.4,<2.14`.

- Pydantic v2 begins in Batch 1B-B.
- Pydantic models are the contract source of truth.
- **Plain-dataclass placeholder contracts are rejected** — this resolves the ambiguity previously recorded in `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 19 ("whether Pydantic v2 is actually used... versus a plain-dataclass placeholder").
- `pydantic-settings` remains deferred.
- No second validation framework is permitted.
- `pyproject.toml` and `uv.lock` will be modified only during an authorized Batch 1B-B implementation — **not by this document**.
- The dependency is approved but not yet added. Runtime dependency count in the repository remains **0**.

### 19B. UUIDv7 Validation-Only Boundary

- Batch 1B-B **validates** caller-supplied UUIDv7 identities.
- Batch 1B-B **does not generate** UUIDv7 identities.
- No external UUIDv7 package is approved.
- No project-owned UUIDv7 generator is approved.
- UUID generation is deferred to a future record-creation or ingestion boundary.
- Tests will use fixed, known-valid UUIDv7 examples.
- Invalid UUID text is rejected.
- Nil UUID is rejected.
- Non-version-7 UUID is rejected.
- Serialization uses the canonical lowercase, hyphenated UUID string.
- Identity values are immutable.

**Project-relevant fact:** Python 3.12.13 does not provide the required standard-library UUIDv7 constructor for project generation, and generation is therefore deliberately outside Batch 1B-B.

### 19C. SHA-256 Fingerprint Validation-Only Boundary

`SHA256Fingerprint` validates exactly:
- 64 characters
- Lowercase only
- Hexadecimal only

Rules:
- Uppercase hexadecimal is rejected.
- Uppercase values are **not** silently normalized.
- Incorrect lengths are rejected.
- Non-hexadecimal characters are rejected.
- Fingerprints are immutable.
- Fingerprints remain separate from UUID identity.
- **Batch 1B-B does not calculate fingerprints.**
- Batch 1B-B does not define canonical fingerprint input fields.
- Batch 1B-B does not decide identity inclusion (in a future fingerprint calculation).
- Batch 1B-B does not decide timestamp inclusion.
- Batch 1B-B does not decide provenance or lineage inclusion.
- Batch 1B-B does not implement record fingerprint generation.

### 19D. Canonical JSON Boundary

- No canonical-JSON dependency enters Batch 1B-B.
- No `compute_fingerprint()` helper is approved.
- No RFC 8785 compliance claim is permitted.
- Pydantic JSON serialization may be used only to test normal contract serialization.
- Canonical persisted serialization and hashing remain unresolved and deferred.

### 19E. SemVer Dependency Strategy

- No external SemVer package enters Batch 1B-B.
- A project-owned immutable SemVer value type is planned for `src/btmm_ai_scanner/contracts/types.py`.
- Exact grammar is unresolved.
- Parsing behavior is unresolved.
- Comparison behavior is unresolved.
- Prerelease support is unresolved.
- Build-metadata support is unresolved.
- Leading-zero rules are unresolved.
- Initial contract and schema versions remain unresolved.
- `test_semver.py` cannot be finalized before Decision Group 2.

### 19F. JSON Schema Boundary

- Pydantic models remain the source of truth.
- In-memory Pydantic schema representations are permitted.
- Batch 1B-B does not write JSON Schema files.
- Batch 1B-B does not create a schema-export script.
- Batch 1B-B does not create a schema directory.
- No generated-schema inventory row is added.
- Formal JSON Schema export belongs to a later, explicitly scoped batch.

### 19G. Manifest Boundary

- Rule-version and schema-version manifest contracts remain shape-only.
- No manifest file writing is approved.
- No manifest loading is approved.
- No manifest directory is created.
- No manifest persistence is approved.
- No manifest supersession mechanism is approved.
- Compatibility-class value contracts remain planned for Batch 1B-B.

### 19H. Blocking Author-Decision Register — Accounting Update

**Resolved for Batch 1B-B scope** (`AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`):
- **BB-1** — Exact Pydantic version range → `pydantic>=2.13.4,<2.14` (Section 19A).
- **BB-2** — UUIDv7 generation strategy for Batch 1B-B → validation-only; no generation, no library (Section 19B).
- **BB-5** — Fingerprint generation boundary → Batch 1B-B does not calculate fingerprints (Section 19C).
- **BB-6** — Fingerprint identity and metadata inclusion boundary for this batch → not decided in this batch; deferred alongside fingerprint calculation itself (Section 19C).
- **BB-12** — Manifest shape-only boundary → confirmed unchanged, shape-only (Section 19G).
- **BB-13** — JSON Schema generation timing → deferred to a later, explicitly scoped batch (Section 19F).

**Partially resolved (as of Decision Group 1):**
- **BB-3** — SemVer implementation strategy: **dependency strategy resolved** (no external package; project-owned type in `contracts/types.py`); **grammar, parsing, and comparison behavior remain unresolved** (Section 19E). *(Superseded — fully resolved by Decision Group 2, Section 20, below.)*
- **BB-4** — Base Pydantic model strategy: **Pydantic use resolved** (Pydantic v2, dataclass placeholders rejected); **exact model configuration** (`frozen`, `extra`, strict validation, etc.) **remains unresolved** (Section 19A; see also the prior audit's Part 7 findings). *(Superseded — fully resolved by Decision Group 2, Section 20, below.)*

**No other BB decision is marked resolved by this section.** BB-7 through BB-11, BB-14, and BB-15 remain exactly as previously reported in the Phase 1B-B Core Foundation Contracts Scope Audit.

---

## 20. Phase 1B-B Decision Group 2 — Base Contract Model, SemVer and Core Value Types

**Status: `AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`. `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`.** This section records the exact design of `src/btmm_ai_scanner/contracts/types.py`'s shared base model, UUIDv7 and SHA-256 value types, and the project-owned `SemVer` type. **No file is created, no dependency is added, and no test is written by this section.**

### 20A. Shared Contract Model

**Location:** `src/btmm_ai_scanner/contracts/types.py`. **Public name:** `ContractModel`.

**Approved conceptual configuration:**

```python
class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
        revalidate_instances="always",
        allow_inf_nan=False,
        str_strip_whitespace=False,
        use_enum_values=False,
    )
```

- Record contracts use `ContractModel`. Record contracts do not use `RootModel`.
- Unknown fields are rejected (`extra="forbid"`).
- Values are not silently coerced (`strict=True`).
- Defaults are validated (`validate_default=True`).
- Nested contract models are revalidated (`revalidate_instances="always"`).
- NaN and positive/negative infinity are rejected (`allow_inf_nan=False`).
- Strings are not globally trimmed or normalized (`str_strip_whitespace=False`).
- Enums remain enum instances in Python mode (`use_enum_values=False`).
- Models are assignment-frozen (`frozen=True`).
- Frozen contracts may use only immutable collection types (e.g., tuples, frozensets) unless a later decision permits otherwise.

**Prohibited configurations:** `validate_assignment`; `arbitrary_types_allowed`; `from_attributes`; `populate_by_name`; alias generators; field aliases; by-alias serialization; custom `json_encoders`; global string conversion; number-to-string coercion.

**Immutability limitation (binding clarification):** `frozen=True` protects normal Python field assignment only. It does **not** establish append-only storage, define lineage, define supersession, or define database immutability. `model_copy(update=...)` remains unapproved. Copying records into new identities remains unresolved. Storage-level mutation rules remain unresolved. *(This directly resolves the "Python object immutability vs. storage immutability" ambiguity flagged in the prior Phase 1B-B Core Foundation Contracts Scope Audit, Part 11 — the two are now explicitly distinguished, though the storage-level rules themselves remain a separate, still-open decision.)*

### 20B. UUIDv7 Representation

**Approved named annotated value type:** `UUIDv7`.

```python
UUIDv7 = Annotated[
    UUID,
    BeforeValidator(_validate_uuidv7),
    PlainSerializer(str, return_type=str, when_used="json"),
]
```

**Accepted inputs:** a `uuid.UUID` instance; a canonical lowercase, hyphenated UUID string.

**Validation requirements:** input must be `UUID` or `str`; string input must already equal the canonical `str(UUID(...))` form; version must be exactly 7; variant must be RFC-compatible; nil UUID is rejected; invalid UUID text is rejected; uppercase UUID text is rejected; compact UUID text is rejected; braced UUID text is rejected; non-version-7 UUID values are rejected; values are **not** silently normalized.

**Runtime representation:** Python representation = `uuid.UUID`; Python-mode dump = `uuid.UUID`; JSON-mode dump = canonical lowercase hyphenated string.

**Record:** no UUID generator is approved; no UUID timestamp extraction is approved; no assumption links the UUIDv7-embedded timestamp to a business timestamp; tests use fixed UUID values. *(This is the value-type contract shape only — Decision Group 1's Section 19B validation-only boundary and "no generation" rule are unaffected and unchanged.)*

### 20C. SHA256Fingerprint Representation

**Approved value type:**

```python
SHA256Fingerprint = Annotated[
    str,
    StringConstraints(
        strict=True,
        min_length=64,
        max_length=64,
        pattern=r"^[0-9a-f]{64}$",
    ),
]
```

**Record:** exactly 64 characters; lowercase ASCII hexadecimal only; strict string input; no whitespace trimming; no uppercase normalization; no `sha256:` prefix; no bytes input; no integer input; no calculation method; no digest recomputation; no record-content comparison; runtime and JSON representations remain the exact string; `UUIDv7` and `SHA256Fingerprint` are non-interchangeable. *(This is the value-type contract shape only — Decision Group 1's Section 19C validation-only boundary and "no calculation" rule are unaffected and unchanged.)*

### 20D. Project-Owned SemVer

**Approved public type:**

```python
class SemVer(RootModel[str]):
    ...

model_config = ConfigDict(
    frozen=True,
    strict=True,
    str_strip_whitespace=False,
)
```

**Full Semantic Versioning 2.0.0 grammar adopted:** `MAJOR.MINOR.PATCH`; `MAJOR.MINOR.PATCH-PRERELEASE`; `MAJOR.MINOR.PATCH+BUILD`; `MAJOR.MINOR.PATCH-PRERELEASE+BUILD`.

**Grammar rules:** major/minor/patch are non-negative integers; core numeric components reject leading zeroes; prerelease identifiers are dot-separated; prerelease identifiers allow ASCII letters, digits, and hyphens; empty prerelease identifiers are rejected; numeric prerelease identifiers reject leading zeroes; build identifiers are dot-separated; build identifiers allow ASCII letters, digits, and hyphens; empty build identifiers are rejected; numeric build identifiers **may** contain leading zeroes; surrounding whitespace is rejected; internal whitespace is rejected; a leading `v` is rejected; partial versions (e.g., `1`, `1.2`) are rejected; exact valid input text is preserved without normalization.

**Approved public API:**
- `SemVer.parse(value: str) -> SemVer`
- `version.compare_precedence(other: SemVer) -> int` — returns `-1` (lower precedence), `0` (same precedence), or `1` (higher precedence)
- `version.same_precedence_as(other: SemVer) -> bool`
- `str(version) -> original validated string`

**Approved read-only properties:** `major: int`; `minor: int`; `patch: int`; `prerelease: tuple[str, ...] | None`; `build_metadata: tuple[str, ...] | None`.

### 20E. SemVer Precedence

**Precedence order:** (1) major numerically; (2) minor numerically; (3) patch numerically; (4) prerelease identifiers.

**Rules:** a release has higher precedence than its matching prerelease; numeric prerelease identifiers compare numerically; numeric identifiers have lower precedence than non-numeric identifiers; non-numeric identifiers compare using ASCII lexical order; when compared identifiers are equal, the version with more prerelease identifiers has higher precedence; **build metadata is ignored for precedence.**

**Equality rules:** exact model equality includes the entire original validated text; build metadata participates in exact equality; build metadata does **not** participate in precedence.

**Example:** `1.0.0+build.1 != 1.0.0+build.2`, but `SemVer.parse("1.0.0+build.1").same_precedence_as(SemVer.parse("1.0.0+build.2"))` is `True`.

**Not implemented or approved:** `__lt__`, `__le__`, `__gt__`, `__ge__`. Callers must use `compare_precedence()`.

**Record:** initial contract version remains unresolved; initial schema version remains unresolved.

### 20F. Serialization Boundary

**Python-mode behavior:** `UUIDv7` remains `uuid.UUID`; `SHA256Fingerprint` remains `str`; `SemVer` dumps as its root string; enums remain enum instances; contract models retain typed values.

**JSON-mode behavior:** `UUIDv7` becomes canonical lowercase UUID text; `SHA256Fingerprint` remains unchanged; `SemVer` becomes the exact validated text; enums serialize to their string values; field names remain unchanged; no aliases are used.

**Round-trip requirement:** `model → model_dump_json() → model_validate_json() → equal model`.

**Explicit non-claim:** this is ordinary Pydantic serialization only, and is **not**: canonical JSON; fingerprint serialization; RFC 8785; a persisted manifest format; stable byte ordering; or cryptographic-hash equivalence. *(Decision Group 1's Section 19D canonical-JSON deferral is unaffected and unchanged.)*

### 20G. Exact Identity and Fingerprint Test Functions (17)

Planned for `tests/unit/test_identity_and_fingerprint.py`:
1. `test_contract_model_is_frozen`
2. `test_contract_model_forbids_extra_fields`
3. `test_contract_model_rejects_type_coercion`
4. `test_contract_model_validates_default_values`
5. `test_contract_model_revalidates_nested_instances`
6. `test_contract_model_rejects_nan_and_infinity`
7. `test_uuidv7_accepts_canonical_string_and_uuid_instance`
8. `test_uuidv7_rejects_invalid_text`
9. `test_uuidv7_rejects_nil_and_non_version_seven_values`
10. `test_uuidv7_rejects_non_rfc_variant`
11. `test_uuidv7_rejects_noncanonical_text`
12. `test_uuidv7_serialization_modes`
13. `test_sha256_fingerprint_accepts_exact_lowercase_hex`
14. `test_sha256_fingerprint_rejects_invalid_values`
15. `test_sha256_fingerprint_serializes_without_normalization`
16. `test_identity_and_fingerprint_are_not_interchangeable`
17. `test_core_value_types_round_trip_through_json`

**Required parameter coverage:** NaN; positive infinity; negative infinity; invalid UUID text; nil UUID; UUIDv4; UUID with non-RFC variant; uppercase UUID text; compact UUID text; braced UUID text; uppercase fingerprint; 63-character fingerprint; 65-character fingerprint; non-hex fingerprint.

**Record:** parameterization is permitted; no additional function name enters this file without review; tests use fixed UUID values; tests do not generate UUIDv7 values.

### 20H. Exact SemVer Test Functions (15)

Planned for `tests/unit/test_semver.py`:
1. `test_semver_accepts_valid_semver_2_0_0_values`
2. `test_semver_rejects_invalid_values`
3. `test_semver_rejects_leading_zeroes`
4. `test_semver_preserves_exact_text`
5. `test_semver_parse_returns_semver`
6. `test_semver_is_frozen`
7. `test_semver_serializes_as_json_string`
8. `test_semver_compares_core_versions`
9. `test_semver_orders_prerelease_before_release`
10. `test_semver_compares_prerelease_identifiers`
11. `test_semver_ignores_build_metadata_for_precedence`
12. `test_semver_exact_equality_includes_build_metadata`
13. `test_semver_same_precedence_ignores_build_metadata`
14. `test_semver_does_not_define_rich_ordering`
15. `test_semver_round_trips_through_json`

**Required valid examples:** `0.1.0`; `1.0.0`; `1.0.0-alpha`; `1.0.0-alpha.1`; `1.0.0-0.3.7`; `1.0.0-x.7.z.92`; `1.0.0+20130313144700`; `1.0.0-beta+exp.sha.5114f85`.

**Required invalid examples:** `1`; `1.2`; `v1.2.3`; `01.2.3`; `1.02.3`; `1.2.03`; `1.0.0-01`; `1.0.0-`; `1.0.0+`; `1.0.0-alpha..1`; `1.0.0 alpha`; a leading-space variant of `1.0.0`.

**Required precedence chain:** `1.0.0-alpha < 1.0.0-alpha.1 < 1.0.0-alpha.beta < 1.0.0-beta < 1.0.0-beta.2 < 1.0.0-beta.11 < 1.0.0-rc.1 < 1.0.0`.

**Record:** tests may be parameterized; tests must not assert complete Pydantic human-readable error prose — stable behavior and relevant error locations may be asserted instead; no additional function name enters this file without review.

### 20I. Decision Accounting — BB-3 and BB-4 Fully Resolved

**BB-3 — SemVer implementation strategy: `AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`.** Project-owned SemVer strategy resolved (Section 20D); full grammar resolved (Section 20D); parsing resolved (Section 20D); precedence resolved (Section 20E); build-metadata behavior resolved (Section 20E); exact API resolved (Section 20D).

**BB-4 — Base Pydantic model strategy: `AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`.** Pydantic `BaseModel` strategy resolved (Section 20A); exact shared `ContractModel` configuration resolved (Section 20A); scalar `SemVer` `RootModel` exception resolved (Section 20D); `UUIDv7` representation resolved (Section 20B); `SHA256Fingerprint` representation resolved (Section 20C); serialization behavior resolved (Section 20F).

**No other BB decision is marked resolved by this section.** BB-7 through BB-11, BB-14, and BB-15 remain exactly as previously reported.

---

## 21. Phase 1B-B Decision Group 3 — Raw Candle and Normalized Candle Contracts

**Status: `AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`. `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`.** This section records the exact field contracts for `RawCandle` (Contract A) and `NormalizedCandle` (Contract B) in `src/btmm_ai_scanner/contracts/raw_candle.py` and `normalized_candle.py`. **No file is created, no dependency is added, and no test is written by this section.**

### 21A. Candle-Specific Enums

Approved future enums in `src/btmm_ai_scanner/contracts/raw_candle.py`:

```python
class CandleCompleteness(StrEnum):
    CONFIRMED_COMPLETE = "CONFIRMED_COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    UNKNOWN = "UNKNOWN"


class CandleVolumeKind(StrEnum):
    TICK = "TICK"
    TRADE = "TRADE"
    UNKNOWN = "UNKNOWN"
```

- No aliases. No automatic values.
- **No `analytically_eligible` enum. No analytical-eligibility Boolean.** Completeness and analytical eligibility remain separate — `CONFIRMED_COMPLETE` does not itself grant analytical eligibility. Analytical eligibility belongs to the later `ValidationResult` boundary.
- `TICK` and `TRADE` describe volume semantics only; `UNKNOWN` does not imply tick volume.

### 21B. Decimal and OHLC Policy

**Python `Decimal` is the exact numeric type** for `open`, `high`, `low`, `close`, `volume`.

- Python-mode input must be `Decimal`; integer, float, and string input are all rejected.
- Binary floating-point is not used internally.
- Prices must be finite and strictly greater than zero.
- Volume must be finite and `>= 0` when present.
- No fixed decimal-place count, no quantization, no rounding — provider precision is preserved.
- JSON round trips must not convert through binary float.

**OHLC invariants:** `high >= open`, `high >= close`, `high >= low`; `low <= open`, `low <= close`, `low <= high`. Open and close must lie inside inclusive `[low, high]`. A doji is valid. Equal high and low are valid when all four OHLC values are equal.

### 21C. Volume Policy

```python
volume: Decimal | None
volume_kind: CandleVolumeKind
```

- `TICK` requires non-`None` volume. `TRADE` requires non-`None` volume.
- `UNKNOWN` permits `Decimal` volume or `None`. **`None` is allowed only when `volume_kind` is `UNKNOWN`.**
- No conversion between tick and trade volume; no assumption that provider volumes are comparable; no volume-unit conversion in Batch 1B-B.

### 21D. RawCandle Exact Field Contract

```python
class RawCandle(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    provider: str
    source_reference: str
    source_symbol: str
    source_timeframe: str

    event_time_utc: datetime
    availability_time_utc: datetime
    processing_time_utc: datetime

    original_event_time: datetime
    original_availability_time: datetime
    original_timezone: str

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: Decimal | None
    volume_kind: CandleVolumeKind
    completeness: CandleCompleteness

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    provenance_id: UUIDv7
```

**Exact field count: 23.** Every field is required; only `volume` may hold `None`. No default `record_id`, fingerprint, version, or `provenance_id`.

### 21E. Raw Source String Policy

Exact strict nonempty strings: `provider`, `source_reference`, `source_symbol`, `source_timeframe`, `original_timezone`.

- Leading, trailing, and whitespace-only values are all rejected.
- Values preserved exactly — no automatic lowercasing/uppercasing, no provider-specific normalization.
- Provider remains provider-neutral: **no FXCM enum, no TradingView enum, no provider-specific identifier type.**

**RawCandle field meanings:** `event_time_utc` = candle-open instant; `availability_time_utc` = candle-close or availability instant; `processing_time_utc` = instant the raw record was received or constructed.

**Binding clarification:** "raw" means provider-facing and not internally normalized. **Raw does not mean unchecked or invalid.**

### 21F. NormalizedCandle Exact Field Contract

```python
class NormalizedCandle(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    raw_candle_id: UUIDv7

    provider: str
    source_reference: str
    source_symbol: str
    source_timeframe: str

    symbol: InternalSymbol
    timeframe: Timeframe

    event_time_utc: datetime
    availability_time_utc: datetime
    processing_time_utc: datetime

    original_event_time: datetime
    original_availability_time: datetime
    original_timezone: str

    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal

    volume: Decimal | None
    volume_kind: CandleVolumeKind
    completeness: CandleCompleteness

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    provenance_id: UUIDv7
```

**Exact field count: 26.** Every field is required; only `volume` may hold `None`. `NormalizedCandle` is provider-traceable, already mapped to `InternalSymbol` and `Timeframe`, already contains canonical UTC timestamps, and already uses the approved numeric types. **The model validates normalized input — it does not perform normalization.**

**Explicitly excluded from this contract:** `RawCandle.to_normalized()`; `NormalizedCandle.from_raw()`; provider-symbol mapping; timeframe mapping; resampling; synthetic candle construction; gap filling; duplicate resolution; filesystem loading; network ingestion.

### 21G. Raw-to-Normalized Lineage

`raw_candle_id: UUIDv7` is the direct parent reference on `NormalizedCandle`.

- `NormalizedCandle` has its own `record_id`, which **must differ** from `raw_candle_id`.
- `NormalizedCandle` has its own caller-supplied `content_fingerprint` — **no fingerprint is calculated.**
- `RawCandle` is not embedded; no Python-object pointer is stored.
- `provenance_id` remains a separate reference. **No generic lineage graph is introduced. No supersession mechanism is introduced.**

### 21H. Timestamp Representation

All timestamp fields are timezone-aware `datetime`.

**Canonical fields:** `event_time_utc`, `availability_time_utc`, `processing_time_utc`. Naive datetime rejected; aware datetime with known UTC offset accepted; canonical fields converted deterministically to UTC; no unknown/missing timezone inferred; UTC instants serialize in ISO 8601 UTC form; microseconds preserved (no second/minute/candle-boundary rounding).

**Original fields:** `original_event_time`, `original_availability_time`, `original_timezone`. Must be timezone-aware; supplied offsets are preserved; `original_timezone` stores the source-provided timezone label, is descriptive only, and is not used to localize a naive datetime; original timestamps are not converted in the stored Python representation.

**Required instant correspondence:** `original_event_time` converted to UTC `==` `event_time_utc`; `original_availability_time` converted to UTC `==` `availability_time_utc`. Original event and availability timestamps may carry different offsets across a daylight-saving transition — no assumption requires their offsets to match.

### 21I. Timestamp Ordering

`availability_time_utc > event_time_utc`; `processing_time_utc >= event_time_utc`. For `CONFIRMED_COMPLETE`: `processing_time_utc >= availability_time_utc`.

- A candle processed before availability cannot be `CONFIRMED_COMPLETE`.
- `INCOMPLETE` and `UNKNOWN` may be processed before or after availability.

**Explicitly deferred:** exact timeframe duration; market-session validation; weekend/holiday validation; daylight-saving session-length rules; provider candle-close conventions; D1 candle-duration rules; trading-calendar membership.

### 21J. Completeness Boundary

`CONFIRMED_COMPLETE` = explicitly confirmed complete by the future provider/data-quality boundary. `INCOMPLETE` = known to be incomplete. `UNKNOWN` = completeness has not been established.

- Completeness is mandatory. Valid OHLC does **not** imply `CONFIRMED_COMPLETE`. Normalization does not upgrade completeness automatically.
- **No `eligible` field. No `valid_for_analysis` field. No `quality_score` field. No `confidence` field.** Analytical eligibility belongs to `ValidationResult`; only a later data-quality process may establish completeness.

### 21K. Version and Provenance Fields

Both contracts require `rule_version`, `contract_version`, `schema_version`, `provenance_id`.

- All version values use `SemVer`. No default versions; initial versions unresolved.
- `rule_version` identifies the construction/normalization rule set; `contract_version` identifies the logical contract version; `schema_version` identifies the validation/schema version. The three versions may differ.
- Historical values remain immutable. `provenance_id` is a UUIDv7 reference only — the provenance record is not embedded, no manifest ID is added, no manifest fingerprint is added.

### 21L. Serialization Boundary

**Python mode:** `record_id`/`raw_candle_id`/`provenance_id` remain `uuid.UUID`; OHLC/volume remain `Decimal`; timestamps remain `datetime`; symbol/timeframe/completeness/volume-kind remain enums; versions remain `SemVer`.

**JSON mode:** UUIDs serialize canonically; `Decimal` exact numeric values preserved without binary-float conversion; canonical timestamps serialize as UTC instants; original timestamps retain explicit offsets; enums serialize to approved strings; `SemVer` serializes to exact validated text; field names unchanged; no aliases.

**Required round trip:** `candle → model_dump_json() → model_validate_json() → equal candle`.

**Explicit non-claims:** not canonical JSON; not fingerprint serialization; not stable cryptographic bytes; not a persisted manifest format; not RFC 8785.

### 21M. Exact RawCandle Test Functions (19)

Planned for `tests/unit/test_raw_candle_contract.py`:
1. `test_raw_candle_accepts_valid_contract`
2. `test_raw_candle_requires_exact_field_set`
3. `test_raw_candle_is_frozen`
4. `test_raw_candle_rejects_extra_fields`
5. `test_raw_candle_requires_strict_decimal_inputs`
6. `test_raw_candle_rejects_nonpositive_prices`
7. `test_raw_candle_enforces_ohlc_bounds`
8. `test_raw_candle_validates_volume_kind_and_value`
9. `test_raw_candle_validates_completeness_values`
10. `test_raw_candle_rejects_naive_timestamps`
11. `test_raw_candle_normalizes_aware_canonical_times_to_utc`
12. `test_raw_candle_preserves_original_timestamp_offsets`
13. `test_raw_candle_requires_original_and_utc_instants_to_match`
14. `test_raw_candle_requires_event_before_availability`
15. `test_raw_candle_requires_processing_not_before_event`
16. `test_raw_candle_rejects_complete_status_before_availability`
17. `test_raw_candle_rejects_blank_or_padded_source_text`
18. `test_raw_candle_requires_version_and_provenance_types`
19. `test_raw_candle_round_trips_through_json`

**Required parameter coverage:** float/integer/string substitutes for `Decimal`; zero price; negative price; open above high; close below low; negative volume; missing volume for `TICK`; missing volume for `TRADE`; `None` volume for `UNKNOWN`; naive datetime; non-UTC aware canonical input; original offset preservation; original/canonical instant mismatch; equal event and availability times; processing before event; `CONFIRMED_COMPLETE` before availability; blank source strings; padded source strings.

**Record:** parameterization permitted; fixed UUIDv7 values only; no fingerprint calculation; no complete Pydantic prose assertions.

### 21N. Exact NormalizedCandle Test Functions (19)

Planned for `tests/unit/test_normalized_candle_contract.py`:
1. `test_normalized_candle_accepts_valid_contract`
2. `test_normalized_candle_requires_exact_field_set`
3. `test_normalized_candle_is_frozen`
4. `test_normalized_candle_rejects_extra_fields`
5. `test_normalized_candle_requires_distinct_raw_and_normalized_identities`
6. `test_normalized_candle_requires_internal_symbol_and_timeframe_enums`
7. `test_normalized_candle_preserves_source_traceability_fields`
8. `test_normalized_candle_requires_strict_decimal_inputs`
9. `test_normalized_candle_rejects_nonpositive_prices`
10. `test_normalized_candle_enforces_ohlc_bounds`
11. `test_normalized_candle_validates_volume_kind_and_value`
12. `test_normalized_candle_validates_completeness_values`
13. `test_normalized_candle_rejects_naive_timestamps`
14. `test_normalized_candle_normalizes_aware_canonical_times_to_utc`
15. `test_normalized_candle_preserves_original_timestamp_offsets`
16. `test_normalized_candle_requires_original_and_utc_instants_to_match`
17. `test_normalized_candle_enforces_timestamp_ordering`
18. `test_normalized_candle_requires_version_and_provenance_types`
19. `test_normalized_candle_round_trips_through_json`

**Record:** no provider API call; no market-data loading; no symbol/timeframe mapping; no synthetic candle creation; fixed UUIDv7 values; no fingerprint calculation; no complete Pydantic prose assertions.

### 21O. Contract Exports

Future exports from `src/btmm_ai_scanner/contracts/__init__.py` — **Decision Group 3 additions:** `CandleCompleteness`, `CandleVolumeKind`, `NormalizedCandle`, `RawCandle`. Alongside Decision Group 2 exports: `ContractModel`, `SHA256Fingerprint`, `SemVer`, `UUIDv7`. **The final complete `__all__` order remains unresolved** until all Batch 1B-B contract files are approved. No implementation export exists yet.

### 21P. Decision Accounting

**Decision Group 3: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** Resolves, for Contracts A and B: exact `RawCandle` fields (§21D); exact `NormalizedCandle` fields (§21F); Decimal numeric policy (§21B); OHLC invariants (§21B); volume representation (§21C); completeness representation (§21A/§21J); provider-neutral source traceability (§21E); UTC normalization mechanics (§21H); original-timezone preservation (§21H); candle timestamp ordering (§21I); raw-to-normalized parent identity (§21G); exact `RawCandle` tests (§21M); exact `NormalizedCandle` tests (§21N).

**BB-7 — Timestamp normalization contract: `PARTIALLY RESOLVED`.**
- **Timestamp contract for RawCandle and NormalizedCandle:** `AUTHOR-APPROVED`, `RESOLVED FOR CONTRACTS A/B`, `NOT YET IMPLEMENTED` (§21H/§21I).
- **Global timestamp policy** (exact candle-close timestamp convention across all future contracts, DST handling, trading-day/week-start/month-boundary handling, provider-session handling — the remaining Phase 1B-A sub-decisions): **`NOT YET RESOLVED`.**

**No other BB decision is marked resolved by this section.**

## 22. Phase 1B-B Decision Group 4 — ValidationResult and ProvenanceRecord Contracts

**Status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`. `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`.**

This section documents author-approved decisions for Contract N (Validation Result) and Contract M (Provenance Record). It does not alter the Phase 1B-A closed status and does not alter Decision Groups 1, 2 or 3. No file under `src/`, `tests/`, or any dependency/config file is created or modified by this section.

### 22A. Validation Classifications

Future enums for `src/btmm_ai_scanner/contracts/validation_result.py`:

```python
class ValidationStatus(StrEnum):
    VALID = "VALID"
    INVALID = "INVALID"
    INDETERMINATE = "INDETERMINATE"


class AnalyticalEligibility(StrEnum):
    ELIGIBLE = "ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
    UNDETERMINED = "UNDETERMINED"
```

- No aliases; no automatic values. `ValidationStatus` and `AnalyticalEligibility` remain separate concepts.
- `VALID` — the subject satisfies the specified validation profile. `INVALID` — the subject fails the specified validation profile. `INDETERMINATE` — evidence is insufficient to decide.
- `ELIGIBLE` — permits later analytical use. `INELIGIBLE` — prohibits later analytical use. `UNDETERMINED` — eligibility has not been established.
- Eligibility does not imply profitability, trade validity, production approval, or execution permission.

### 22B. ValidationResult Exact Field Contract

```python
class ValidationResult(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    subject_record_id: UUIDv7

    validation_profile: str
    status: ValidationStatus
    analytical_eligibility: AnalyticalEligibility
    reason_codes: tuple[str, ...]

    evaluated_at_utc: datetime

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    provenance_id: UUIDv7
```

**Exact field count: 12.**

- Every field is required — no default identifier, fingerprint, timestamp, status, eligibility, version, or provenance ID.
- `record_id` identifies the `ValidationResult`; `subject_record_id` identifies the evaluated record. `record_id` must differ from `subject_record_id`. The subject is not embedded; no mutable Python-object reference is stored.
- `provenance_id` references a separate `ProvenanceRecord` (§22H) by identity only.

### 22C. Validation Profile and Reason Codes

**`validation_profile`:** strict string; nonempty; not whitespace-only; no leading/trailing whitespace; exact text preserved; provider-neutral; no automatic normalization.

**`reason_codes: tuple[str, ...]`:** immutable tuple; unique values; strict strings; order preserved; no automatic sorting. Each code matches `^[A-Z][A-Z0-9_]*$`.

Approved examples: `CANDLE_INCOMPLETE`, `TIMESTAMP_MISMATCH`, `CONFLICTING_DUPLICATE`, `RULE_EVIDENCE_INSUFFICIENT`.

Rejected: lowercase codes; blank codes; whitespace; leading/trailing whitespace; empty strings; malformed codes; duplicate codes.

**Explicitly excluded:** human-readable validation messages; numeric or confidence scores; warning text; free-form notes.

### 22D. Status and Eligibility Consistency

| `status` | Permitted `analytical_eligibility` |
|---|---|
| `VALID` | `ELIGIBLE`, `INELIGIBLE`, `UNDETERMINED` |
| `INVALID` | `INELIGIBLE` only |
| `INDETERMINATE` | `UNDETERMINED` only |

- `ELIGIBLE` requires `status == VALID`.
- `INVALID` requires at least one reason code. `INDETERMINATE` requires at least one reason code.
- `VALID` + `INELIGIBLE` requires at least one reason code. `VALID` + `UNDETERMINED` requires at least one reason code.
- `VALID` + `ELIGIBLE` may have an empty reason-code tuple.
- Structural validity and analytical eligibility remain separate. `ValidationResult` does not upgrade `CandleCompleteness`. `CONFIRMED_COMPLETE` does not automatically mean `ELIGIBLE`. `INCOMPLETE` may still be structurally `VALID` but analytically `INELIGIBLE`.

### 22E. Validation Timestamp

`evaluated_at_utc: datetime` — naive datetime rejected; aware datetime with known offset accepted; deterministically normalized to UTC; microseconds preserved; no rounding.

Represents when the validation result was produced. Does not replace the subject's event, availability, or processing timestamps. No relationship to arbitrary subject timestamps is enforced in Batch 1B-B.

### 22F. Evidence Classification

Future enum for `src/btmm_ai_scanner/contracts/provenance_record.py`:

```python
class EvidenceClassification(StrEnum):
    BOOK_SOURCED = "BOOK-SOURCED"
    BOOK_SUPPORTED_UNDERLYING_CONCEPT = (
        "BOOK-SUPPORTED UNDERLYING CONCEPT"
    )
    AUTHOR_APPROVED = "AUTHOR-APPROVED"
    AUTHOR_ADDED_PROJECT_TERMINOLOGY = (
        "AUTHOR-ADDED PROJECT TERMINOLOGY"
    )
    ENGINEERING_PROVISIONAL = "ENGINEERING-PROVISIONAL"
    EMPIRICALLY_CALIBRATED = "EMPIRICALLY-CALIBRATED"
    OUT_OF_SAMPLE_VALIDATED = "OUT-OF-SAMPLE-VALIDATED"
    PRODUCTION_APPROVED = "PRODUCTION-APPROVED"
```

- Exact project evidence-label strings preserved; no aliases; no automatic values.
- The classification records evidence status; the contract does not prove that the classification was legitimately granted.
- `PRODUCTION-APPROVED` is representable for future records. The current project is not production-approved; Batch 1B-B is not production-approved. Assignment authority remains governed outside the model.

### 22G. Provenance Source Reference

```python
class ProvenanceSourceReference(ContractModel):
    source_reference: str
    source_record_id: UUIDv7 | None
    source_version: SemVer | None
```

**Exact field count: 3.**

- All fields are required (`source_record_id`/`source_version` may hold `None`, but the field itself must be present).
- `source_reference` is strict, nonblank, unpadded; exact text preserved. It may identify a document, rule, repository item, dataset, or other provider-neutral source. It is not interpreted as a filesystem path or a URL; it does not load, open, or contact the source.
- `source_record_id` references an internal UUIDv7 record when one exists. `source_version` uses `SemVer` when the source is versioned. No provider-specific source enum exists.

### 22H. ProvenanceRecord Exact Field Contract

```python
class ProvenanceRecord(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    subject_record_id: UUIDv7

    sources: tuple[ProvenanceSourceReference, ...]
    parent_provenance_ids: tuple[UUIDv7, ...]
    evidence_classification: EvidenceClassification

    created_at_utc: datetime

    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
```

**Exact field count: 10.**

- Every field is required. `sources` must contain at least one entry; `parent_provenance_ids` may be empty.
- No default identifier, fingerprint, classification, timestamp, or version.
- `ProvenanceRecord` deliberately has no `provenance_id` field.

### 22I. Provenance Identity and Local Lineage

- `record_id` identifies the provenance record; `subject_record_id` identifies the record whose origin is described. `record_id` must differ from `subject_record_id`. The subject record is not embedded.
- Exact duplicate `ProvenanceSourceReference` entries are rejected. `parent_provenance_ids` must contain unique UUIDv7 values. `record_id` may not appear in `parent_provenance_ids`.
- `source_record_id` may not equal `ProvenanceRecord.record_id`; `source_record_id` may not equal `subject_record_id`.
- Source order is preserved; parent-provenance order is preserved; no automatic sorting. Multiple parent provenance references are allowed.

**Explicitly excluded enforcement:** global graph acyclicity; cross-record existence; parent-record loading; multi-record transaction consistency; supersession; provenance persistence; database foreign keys.

**Record:** only local direct self-reference and duplicate validation are approved. Global cycle detection belongs to a later lineage or repository boundary.

### 22J. Provenance Timestamp

`created_at_utc: datetime` — naive datetime rejected; aware datetime accepted; deterministically normalized to UTC; microseconds preserved; no rounding.

Represents `ProvenanceRecord` creation time. It is administrative provenance metadata, not the subject's event timestamp. No original-timezone companion is required. It is system-generated canonical time, not provider-supplied market time.

**Record:** Decision Group 4 resolves timestamp mechanics only for `ValidationResult` and `ProvenanceRecord`. It does not establish one universal timestamp field set.

### 22K. Version and Fingerprint Boundary

Both contracts require `content_fingerprint`, `rule_version`, `contract_version`, `schema_version`. `ValidationResult` additionally requires `provenance_id`.

- Fingerprints remain caller-supplied and validation-only; no fingerprint calculation; no canonical JSON hashing.
- No default versions; initial versions remain unresolved. `rule_version`, `contract_version`, and `schema_version` may differ. Historical version values remain immutable.
- `ProvenanceRecord.record_id` is the ID referenced by other records' `provenance_id`. `ProvenanceRecord` does not recursively require another `provenance_id`.

### 22L. Serialization Boundary

**Python mode:** UUIDs remain `uuid.UUID`; timestamps remain `datetime`; enums remain enum instances; versions remain `SemVer`; `sources`/`parent_provenance_ids` remain tuples; fingerprints and reason codes remain strings.

**JSON mode:** UUIDs serialize canonically; UTC timestamps serialize as UTC instants; enum values use their exact approved strings; `SemVer` serializes to exact validated text; tuples serialize as JSON arrays; field names remain unchanged; no aliases.

**Required round trips:** `validation_result → model_dump_json() → model_validate_json() → equal model`; `provenance_record → model_dump_json() → model_validate_json() → equal model`.

**Explicit non-claims:** not canonical JSON; not a persisted manifest format; not fingerprint-byte format; not stable cryptographic serialization.

### 22M. Exact ValidationResult Test Functions (16)

Planned for `tests/unit/test_validation_result.py`:
1. `test_validation_result_accepts_valid_contract`
2. `test_validation_result_requires_exact_field_set`
3. `test_validation_result_is_frozen`
4. `test_validation_result_rejects_extra_fields`
5. `test_validation_result_requires_distinct_record_and_subject_ids`
6. `test_validation_result_rejects_blank_or_padded_profile`
7. `test_validation_result_validates_status_values`
8. `test_validation_result_validates_eligibility_values`
9. `test_validation_result_enforces_status_eligibility_consistency`
10. `test_validation_result_validates_reason_code_format`
11. `test_validation_result_rejects_duplicate_reason_codes`
12. `test_validation_result_requires_reasons_for_noneligible_or_nonvalid_results`
13. `test_validation_result_rejects_naive_evaluated_at`
14. `test_validation_result_normalizes_evaluated_at_to_utc`
15. `test_validation_result_requires_version_and_provenance_types`
16. `test_validation_result_round_trips_through_json`

**Required parameter coverage:** `VALID`+`ELIGIBLE` with empty reasons; `VALID`+`INELIGIBLE`; `VALID`+`UNDETERMINED`; `INVALID`+`INELIGIBLE`; `INDETERMINATE`+`UNDETERMINED`; reject `INVALID`+`ELIGIBLE`; reject `INDETERMINATE`+`ELIGIBLE`; missing required reasons; duplicate reasons; lowercase reason codes; padded reason codes; blank reason codes; malformed reason codes; blank or padded validation profile; naive timestamp; non-UTC aware timestamp normalized to UTC; fixed UUIDv7 values.

**Record:** no fingerprint calculation; no complete Pydantic prose assertions.

### 22N. Exact ProvenanceRecord Test Functions (17)

Planned for `tests/unit/test_provenance_record.py`:
1. `test_provenance_source_reference_accepts_valid_values`
2. `test_provenance_source_reference_requires_exact_field_set`
3. `test_provenance_source_reference_rejects_blank_or_padded_reference`
4. `test_provenance_record_accepts_valid_contract`
5. `test_provenance_record_requires_exact_field_set`
6. `test_provenance_record_is_frozen`
7. `test_provenance_record_rejects_extra_fields`
8. `test_provenance_record_requires_distinct_record_and_subject_ids`
9. `test_provenance_record_requires_nonempty_sources`
10. `test_provenance_record_rejects_duplicate_sources`
11. `test_provenance_record_rejects_self_source_references`
12. `test_provenance_record_validates_evidence_classification`
13. `test_provenance_record_rejects_naive_created_at`
14. `test_provenance_record_normalizes_created_at_to_utc`
15. `test_provenance_record_validates_parent_provenance_ids`
16. `test_provenance_record_requires_version_types`
17. `test_provenance_record_round_trips_through_json`

**Required parameter coverage:** external source with no internal record ID or source version; internal source with UUIDv7 and SemVer; multiple source references; empty sources tuple; exact duplicate sources; self-referencing source IDs; empty parent-provenance tuple; multiple unique parent IDs; duplicate parent IDs; provenance record ID appearing as a parent; every `EvidenceClassification` value; naive timestamp rejection; UTC normalization; fixed UUIDv7 values.

**Record:** no source loading; no network access; no fingerprint calculation.

### 22O. Contract Exports

Future exports from `src/btmm_ai_scanner/contracts/__init__.py` — **Decision Group 4 additions:** `AnalyticalEligibility`, `EvidenceClassification`, `ProvenanceRecord`, `ProvenanceSourceReference`, `ValidationResult`, `ValidationStatus`. These join the previously approved exports from Decision Groups 2 and 3.

**Record:** exact complete `__all__` order remains unresolved until manifest contracts are approved. No implementation export exists yet.

### 22P. Decision Accounting

**Decision Group 4: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** Resolves: exact `ValidationResult` fields (§22B); `ValidationStatus` classification (§22A); `AnalyticalEligibility` classification (§22A); status/eligibility consistency (§22D); reason-code format and requirements (§22C); `ValidationResult` timestamp mechanics (§22E); exact `ProvenanceRecord` fields (§22H); `ProvenanceSourceReference` shape (§22G); `EvidenceClassification` values (§22F); local provenance-lineage rules (§22I); exact dedicated `ValidationResult` tests (§22M); exact dedicated `ProvenanceRecord` tests (§22N); BB-8; BB-14; final Batch 1B-B path count.

**BB-8 — Validation status and analytical eligibility classification scheme: `AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`.**

**BB-14 — ProvenanceRecord shape and local lineage-reference rules: `AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`.**

**BB-7 — Timestamp normalization contract: `PARTIALLY RESOLVED`.**
- Timestamp policy resolved for Contracts A, B, M and N (§21H/§21I and §22E/§22J).
- Global timestamp policy (candle-close convention, DST, trading-day/week/month boundaries, provider-session handling) remains **`NOT YET RESOLVED`.**

**BB-9 — Provenance/lineage graph rules: `PARTIALLY RESOLVED`.**
- Local multi-parent provenance references resolved (§22I).
- Direct self-reference and duplicate validation resolved (§22I).
- Global lineage graph remains **`NOT YET RESOLVED`.** Cycle enforcement remains **`NOT YET RESOLVED`.** Persistence remains **`NOT YET RESOLVED`.**

**No other BB decision is marked resolved by this section.**

## 23. Phase 1B-B Decision Group 5 — Version Manifests, Compatibility, Supersession and Initial Versions

**Status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`. `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`.**

This section documents author-approved decisions for Contract Q (`RuleVersionManifest`) and Contract R (`SchemaVersionManifest`), completing Batch 1B-B's core-foundation contract scope. It does not alter the Phase 1B-A closed status and does not alter Decision Groups 1, 2, 3 or 4. No file under `src/`, `tests/`, or any dependency/config file is created or modified by this section.

### 23A. Compatibility Classification

Future enum for `src/btmm_ai_scanner/contracts/rule_version_manifest.py`:

```python
class CompatibilityClass(StrEnum):
    FULLY_COMPATIBLE = "FULLY_COMPATIBLE"
    BACKWARD_COMPATIBLE = "BACKWARD_COMPATIBLE"
    FORWARD_COMPATIBLE = "FORWARD_COMPATIBLE"
    INCOMPATIBLE = "INCOMPATIBLE"
    UNKNOWN = "UNKNOWN"
```

- **`FULLY_COMPATIBLE`** — old and new versions are mutually consumable.
- **`BACKWARD_COMPATIBLE`** — the newer implementation can consume artifacts produced under the previous version.
- **`FORWARD_COMPATIBLE`** — the previous implementation can consume artifacts produced under the newer version.
- **`INCOMPATIBLE`** — neither compatibility direction is guaranteed.
- **`UNKNOWN`** — compatibility has not been established.

No aliases; no automatic values. Compatibility is relative to the declared previous version. Compatibility classification is separate from SemVer precedence and does not prove testing occurred; it does not imply production approval. A major-version increase does not automatically mean `INCOMPATIBLE`; a patch-version increase does not automatically prove compatibility. Compatibility must be supplied explicitly by the caller.

### 23B. RuleVersionManifest Exact Field Contract

```python
class RuleVersionManifest(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    rule_set_name: str
    rule_version: SemVer
    previous_rule_version: SemVer | None
    compatibility_with_previous: CompatibilityClass
    supersedes_manifest_id: UUIDv7 | None

    effective_at_utc: datetime
    evidence_classification: EvidenceClassification

    manifest_contract_version: SemVer
    manifest_schema_version: SemVer
    provenance_id: UUIDv7
```

**Exact field count: 12.**

- Every field is required — `previous_rule_version` and `supersedes_manifest_id` may hold `None`, but both fields must be present. No default identifier, fingerprint, version, compatibility class, timestamp, evidence classification, or provenance ID.
- `rule_set_name`: strict string; nonempty; not whitespace-only; no leading/trailing whitespace; exact text preserved; provider-neutral; no normalization; no alias mapping.

### 23C. SchemaVersionManifest Exact Field Contract

```python
class SchemaVersionManifest(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint

    schema_name: str
    schema_version: SemVer
    previous_schema_version: SemVer | None
    compatibility_with_previous: CompatibilityClass
    supersedes_manifest_id: UUIDv7 | None

    effective_at_utc: datetime

    target_contract_name: str
    target_contract_version: SemVer
    evidence_classification: EvidenceClassification

    manifest_contract_version: SemVer
    manifest_schema_version: SemVer
    provenance_id: UUIDv7
```

**Exact field count: 14.**

- Every field is required — `previous_schema_version` and `supersedes_manifest_id` may hold `None`, but both fields must be present.
- `schema_name` and `target_contract_name`: nonempty; not whitespace-only; no leading/trailing whitespace; exact text preserved; no automatic normalization; no dynamic import; no target-contract loading or inspection.

### 23D. Initial-Manifest Consistency

Approved initial-manifest combination: `previous version = None`, `supersedes_manifest_id = None`, `compatibility_with_previous = UNKNOWN`.

- **`RuleVersionManifest`:** `previous_rule_version is None` requires `supersedes_manifest_id is None` and `compatibility_with_previous == UNKNOWN`.
- **`SchemaVersionManifest`:** `previous_schema_version is None` requires `supersedes_manifest_id is None` and `compatibility_with_previous == UNKNOWN`.

Initial manifests cannot claim compatibility with a nonexistent predecessor and cannot contain a supersession reference.

### 23E. Successor-Manifest Consistency

Successor manifests require `previous version != None` and `supersedes_manifest_id != None`.

- Both predecessor references must be present together — a previous version without `supersedes_manifest_id` is rejected; `supersedes_manifest_id` without a previous version is rejected.
- `record_id` must differ from `supersedes_manifest_id`.
- Current version must differ from previous version and must have higher SemVer precedence. Version downgrades are rejected; the exact same version is rejected; equal-precedence versions differing only by build metadata are rejected. Skipping versions is permitted. Compatibility may remain `UNKNOWN`.
- The contract does not verify referenced-manifest existence, and does not verify the predecessor contains the declared previous version.

**Permitted examples:** `0.1.0 → 0.1.1`; `0.1.0 → 0.2.0`; `0.9.0 → 1.0.0`.

**Rejected examples:** `0.2.0 → 0.1.0`; `1.0.0 → 1.0.0`; `1.0.0+build.1 → 1.0.0+build.2`.

### 23F. Local Manifest Supersession

`supersedes_manifest_id` represents the direct manifest record being replaced.

**Approved local checks:** self-supersession rejected; initial manifest has no supersession reference; successor manifest requires exactly one supersession reference; only one direct superseded manifest permitted; historical manifests remain immutable; supersession does not delete or mutate the previous manifest.

**Explicitly deferred:** referenced-manifest existence; cross-record version agreement; global supersession-chain completeness; global cycle detection; branch conflict resolution; manifest persistence; database foreign keys; atomic storage transactions; latest-manifest lookup.

### 23G. Manifest Timestamp

Both manifests use `effective_at_utc: datetime` — naive datetime rejected; aware datetime accepted; deterministically normalized to UTC; microseconds preserved; no rounding.

Represents when the manifested version becomes effective. Does not represent record construction time or a market-event time. No original-timezone companion field. Future-dated effective timestamps are permitted. No ordering against predecessor effective time is enforced.

**Record:** Decision Group 5 completes timestamp mechanics for every Batch 1B-B contract.

### 23H. Evidence, Fingerprint and Provenance Boundary

Both manifests require `content_fingerprint`, `evidence_classification`, `provenance_id`.

- Fingerprints remain caller-supplied and validation-only; no manifest fingerprint calculation; no canonical JSON hashing.
- Evidence classification uses the exact approved project labels (§22F); `PRODUCTION-APPROVED` remains representable; the current project is not production-approved; Batch 1B-B is not production-approved.
- `provenance_id` references a separate `ProvenanceRecord` by identity only — provenance is not embedded. The contract does not verify classification authority.

### 23I. Manifest Contract and Schema Versions

Both manifest contracts require `manifest_contract_version` and `manifest_schema_version`.

- These describe the manifest record's own logical contract and schema — distinct from `rule_version`/`schema_version` and distinct from `target_contract_version`. No default is permitted.

### 23J. Initial Batch 1B-B Version Policy

**Author-approved initial values:** initial rule version `0.1.0`; initial logical contract version `0.1.0`; initial schema version `0.1.0`; initial manifest contract version `0.1.0`; initial manifest schema version `0.1.0`.

**Application:** initial `RawCandle.rule_version`/`.contract_version`/`.schema_version` = `0.1.0`; initial `NormalizedCandle` versions = `0.1.0`; initial `ValidationResult` versions = `0.1.0`; initial `ProvenanceRecord` versions = `0.1.0`; initial manifest contract version = `0.1.0`; initial manifest schema version = `0.1.0`; the first `RuleVersionManifest` describes rule version `0.1.0`; the first `SchemaVersionManifest` for each contract describes schema version `0.1.0`; initial schema manifests target contract version `0.1.0`.

**Rules:** values are supplied explicitly by callers; no Pydantic field default; no automatic version injection; no module-level mutable version state. `0.1.0` identifies the first pre-production contract generation and does not imply production readiness. Later changes require explicit version decisions; later versions require new immutable records.

### 23K. Serialization Boundary

**Python mode:** IDs remain `uuid.UUID`; timestamps remain `datetime`; compatibility and evidence values remain enum instances; versions remain `SemVer`; names and fingerprints remain strings.

**JSON mode:** UUID values serialize canonically; effective timestamps serialize as UTC instants; enum values serialize using exact approved strings; `SemVer` values serialize as exact validated text; field names remain unchanged; no aliases.

**Required round trips:** `rule_manifest → model_dump_json() → model_validate_json() → equal rule_manifest`; `schema_manifest → model_dump_json() → model_validate_json() → equal schema_manifest`.

**Explicit non-claims:** not canonical JSON; not a filesystem manifest format; not a persisted wire format; not fingerprint-byte serialization.

### 23L. Exact Manifest Test Functions (29)

**The approved count is 29, not 27.** Planned for `tests/unit/test_manifest_compatibility_classes.py`:

1. `test_compatibility_class_values_are_exact`
2. `test_rule_version_manifest_accepts_initial_manifest`
3. `test_rule_version_manifest_accepts_successor_manifest`
4. `test_rule_version_manifest_requires_exact_field_set`
5. `test_rule_version_manifest_is_frozen`
6. `test_rule_version_manifest_rejects_extra_fields`
7. `test_rule_version_manifest_rejects_blank_or_padded_rule_set_name`
8. `test_rule_version_manifest_enforces_initial_reference_consistency`
9. `test_rule_version_manifest_enforces_successor_reference_consistency`
10. `test_rule_version_manifest_requires_increasing_rule_version`
11. `test_rule_version_manifest_rejects_equal_precedence_successor`
12. `test_rule_version_manifest_rejects_self_supersession`
13. `test_rule_version_manifest_normalizes_effective_at_to_utc`
14. `test_rule_version_manifest_requires_version_evidence_and_provenance_types`
15. `test_rule_version_manifest_round_trips_through_json`
16. `test_schema_version_manifest_accepts_initial_manifest`
17. `test_schema_version_manifest_accepts_successor_manifest`
18. `test_schema_version_manifest_requires_exact_field_set`
19. `test_schema_version_manifest_is_frozen`
20. `test_schema_version_manifest_rejects_extra_fields`
21. `test_schema_version_manifest_rejects_blank_or_padded_names`
22. `test_schema_version_manifest_enforces_initial_reference_consistency`
23. `test_schema_version_manifest_enforces_successor_reference_consistency`
24. `test_schema_version_manifest_requires_increasing_schema_version`
25. `test_schema_version_manifest_rejects_equal_precedence_successor`
26. `test_schema_version_manifest_rejects_self_supersession`
27. `test_schema_version_manifest_normalizes_effective_at_to_utc`
28. `test_schema_version_manifest_requires_target_version_evidence_and_provenance_types`
29. `test_schema_version_manifest_round_trips_through_json`

**Required parameter coverage:** all five `CompatibilityClass` values; initial manifests; successor manifests; previous version without manifest ID; manifest ID without previous version; self-supersession; downgrade; exact same version; equal precedence with different build metadata; valid patch increase; valid minor increase; valid major increase; blank names; padded names; naive timestamp rejection; non-UTC aware timestamp normalized to UTC; every `EvidenceClassification` value; fixed UUIDv7 values; initial version `0.1.0`.

**Record:** no fingerprint calculation; no manifest loading; no persistence; no complete Pydantic prose assertions.

### 23M. Final Contracts Package Exports

Final exact public export order for `src/btmm_ai_scanner/contracts/__init__.py`:

```python
__all__ = [
    "ContractModel",
    "SHA256Fingerprint",
    "SemVer",
    "UUIDv7",
    "CandleCompleteness",
    "CandleVolumeKind",
    "RawCandle",
    "NormalizedCandle",
    "AnalyticalEligibility",
    "ValidationResult",
    "ValidationStatus",
    "EvidenceClassification",
    "ProvenanceRecord",
    "ProvenanceSourceReference",
    "CompatibilityClass",
    "RuleVersionManifest",
    "SchemaVersionManifest",
]
```

**Exact export count: 17.**

**Rules:** no wildcard exports; no private validator exported; no UUID generator exported; no fingerprint-generation function exported; no persistence helper exported; no loading helper exported; no additional public name enters Batch 1B-B without author review.

### 23N. Decision Accounting

**Decision Group 5: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** Resolves: `CompatibilityClass` exact values (§23A); `CompatibilityClass` meanings (§23A); exact `RuleVersionManifest` fields (§23B); exact `SchemaVersionManifest` fields (§23C); initial-manifest consistency (§23D); successor-manifest consistency (§23E); local manifest supersession (§23F); manifest effective-time mechanics (§23G); initial Batch 1B-B version policy (§23J); exact manifest tests (§23L); final contracts package exports (§23M).

**BB-7 — Timestamp normalization contract: `AUTHOR-APPROVED`, `RESOLVED FOR BATCH 1B-B SCOPE`, `NOT YET IMPLEMENTED`.** Timestamp mechanics are now resolved for all Batch 1B-B contracts (Contracts A, B, M, N, Q, R). The global timestamp policy (candle-close convention, DST, trading-day/week/month boundaries, provider-session handling), which spans beyond Batch 1B-B, remains **`NOT YET RESOLVED`.**

**BB-9 — Provenance/lineage graph rules: `PARTIALLY RESOLVED`.**
- **Locally resolved:** raw-to-normalized parent reference (§21G); multi-parent provenance references (§22I); local manifest supersession references (§23F).
- **Globally unresolved:** global lineage graph; cross-record existence; global cycle detection; persistence; supersession-chain repository validation.

**No other BB decision is marked resolved by this section.**

## 24. Phase 1B-B Decision Group 6 — Implementation Sequence, Verification Gates and Rollback Boundary

**Status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`. `BATCH 1B-B IMPLEMENTATION NOT AUTHORIZED`.**

This section documents the author-approved control plan for the future Batch 1B-B implementation — the exact starting baseline, the exact 17-path scope, the dependency-lock procedure, the per-stage construction sequence, the exact test-function boundary, the final quality gates, mandatory stop conditions, the correction boundary, the rollback boundary, and the post-implementation closure sequence. It does not alter Decision Groups 1–5. **No file under `src/`, `tests/`, or any dependency/config file is created or modified by this section, and no implementation action is authorized by it.**

### 24A. Execution Baseline

**Required starting commit:** `9249c1584389993f22a3d5753f9fc37d6e00fc9c`. **Required branch:** `main`.

**Required starting repository state:** working tree clean; nothing staged; HEAD synchronized with `origin/main`; Python `3.12.13`; `uv` `0.11.30`; existing baseline `34` passing tests (`test_import_smoke.py` + `test_config_precedence.py`); runtime dependencies empty; no Batch 1B-B implementation files exist.

**Record:** any mismatch is a mandatory stop condition. Implementation cannot begin from a dirty repository or from a diverged branch. **Decision Group 6 approval alone does not authorize implementation** (§24Q).

### 24B. Exact 17-Path Implementation Scope

**Two modified files:**
1. `pyproject.toml`
2. `uv.lock`

**Fifteen new files:**
3. `src/btmm_ai_scanner/contracts/__init__.py`
4. `src/btmm_ai_scanner/contracts/types.py`
5. `src/btmm_ai_scanner/contracts/raw_candle.py`
6. `src/btmm_ai_scanner/contracts/normalized_candle.py`
7. `src/btmm_ai_scanner/contracts/validation_result.py`
8. `src/btmm_ai_scanner/contracts/provenance_record.py`
9. `src/btmm_ai_scanner/contracts/rule_version_manifest.py`
10. `src/btmm_ai_scanner/contracts/schema_version_manifest.py`
11. `tests/unit/test_identity_and_fingerprint.py`
12. `tests/unit/test_semver.py`
13. `tests/unit/test_raw_candle_contract.py`
14. `tests/unit/test_normalized_candle_contract.py`
15. `tests/unit/test_validation_result.py`
16. `tests/unit/test_provenance_record.py`
17. `tests/unit/test_manifest_compatibility_classes.py`

**Record:** exactly 17 changed paths are authorized for the future implementation; no eighteenth path is authorized. No documentation file may change during implementation. No fixture, JSON Schema, persisted manifest, generated, provider-adapter, ingestion, persistence, or fingerprint-calculator file may be added. Private references remain untouched and ignored. `.venv/` may exist locally only when ignored and must never be staged.

### 24C. Dependency-Lock Procedure

**Exact future runtime dependency:** `pydantic>=2.13.4,<2.14`.

**Approved future procedure:**
1. Verify the clean baseline.
2. Add only the approved Pydantic range.
3. Regenerate `uv.lock` with the recorded `uv` baseline.
4. Synchronize using the resulting lock.
5. Verify the resolved Pydantic version is within the approved range.
6. Verify existing development-tool versions remain unchanged: `pytest 9.1.1`, `mypy 2.3.0`, `Ruff 0.15.22`.
7. Run `uv lock --check`.

**Approved future commands:** `uv add "pydantic>=2.13.4,<2.14"`; `uv lock --check`; `uv sync --locked`.

**Prohibited:** `uv self update`; Python installation or replacement; any dependency-upgrade command; `--upgrade`; a second runtime dependency; any intentional development-tool upgrade; any direct unapproved dependency edit.

**Record:** a dependency-resolution discrepancy requires an immediate stop.

### 24D. Stage A Construction Sequence

**Stage A files:** `contracts/__init__.py`, `contracts/types.py`, `test_identity_and_fingerprint.py`, `test_semver.py`.

**Exact sequence:** (1) create `contracts/__init__.py` as a minimal package boundary; (2) implement `ContractModel`; (3) implement `UUIDv7` validation-only behavior; (4) implement `SHA256Fingerprint` validation-only behavior; (5) implement the project-owned `SemVer`; (6) implement exactly 17 identity/fingerprint test functions; (7) implement exactly 15 SemVer test functions; (8) run only the two Stage A test files; (9) run targeted Ruff and mypy against Stage A files.

**Record:** the final 17-name package export list is not finalized until Stage E. No UUID generator, fingerprint calculator, or canonical JSON helper enters Stage A.

### 24E. Stage B Construction Sequence

**Stage B files:** `raw_candle.py`, `normalized_candle.py`, `test_raw_candle_contract.py`, `test_normalized_candle_contract.py`.

**Exact sequence:** (1) implement `CandleCompleteness`; (2) implement `CandleVolumeKind`; (3) implement the exact 23-field `RawCandle`; (4) implement the exact 26-field `NormalizedCandle`; (5) implement the approved Decimal, OHLC, volume, and timestamp invariants; (6) implement exactly 19 `RawCandle` test functions; (7) implement exactly 19 `NormalizedCandle` test functions; (8) run the two candle test files; (9) re-run all Stage A tests.

**Record:** existing `InternalSymbol` and `Timeframe` enums (`src/btmm_ai_scanner/config/enums.py`) must be reused; their existing names and definitions must be verified before coding; a mismatch requires an immediate stop; replacement symbol or timeframe enums may not be created.

### 24F. Stage C Construction Sequence

**Stage C files:** `provenance_record.py`, `validation_result.py`, `test_provenance_record.py`, `test_validation_result.py`.

**Exact construction order:** (1) `ProvenanceSourceReference`; (2) `EvidenceClassification`; (3) `ProvenanceRecord`; (4) `ValidationStatus`; (5) `AnalyticalEligibility`; (6) `ValidationResult`. Then: implement exactly 17 `ProvenanceRecord` test functions; implement exactly 16 `ValidationResult` test functions; run both dedicated test files; re-run all earlier Batch 1B-B tests.

### 24G. Stage D Construction Sequence

**Stage D files:** `rule_version_manifest.py`, `schema_version_manifest.py`, `test_manifest_compatibility_classes.py`.

**Exact construction order:** (1) `CompatibilityClass`; (2) `RuleVersionManifest`; (3) `SchemaVersionManifest`; (4) exactly 29 manifest test functions.

**Required verification:** initial-manifest consistency; successor-manifest consistency; higher SemVer precedence; build-metadata-only successor rejection; local supersession; `effective_at_utc` normalization; exact `0.1.0` initial-version scenarios.

### 24H. Stage E Final Exports

Stage E finalizes `src/btmm_ai_scanner/contracts/__init__.py` with exactly the approved 17-name export order (§23M).

**Required verification:** every approved export imports successfully; `__all__` contains exactly 17 entries; export order matches the approved order; no private helper, UUID generator, fingerprint calculator, persistence helper, or loader is exported.

### 24I. Exact Test-Function Boundary

**Exactly 132 top-level test functions:** 17 identity/fingerprint + 15 SemVer + 19 RawCandle + 19 NormalizedCandle + 16 ValidationResult + 17 ProvenanceRecord + 29 manifest compatibility = **132**.

**Record:** parameterization is permitted; pytest may collect more than 132 test cases; the 132 limit applies to top-level test-function names. No approved test-function name may be omitted, renamed, or added to. Private helper functions are permitted only when not named `test_*`. Tests do not generate UUIDv7, calculate fingerprints, call providers, access networks, load external files, or assert complete Pydantic human-readable error prose. **A static AST-based function-name and count comparison is mandatory** before the suite is considered complete.

### 24J. Formatting and Quality Gates

**Targeted formatting:** `uv run ruff format <the 15 new source and test files>` — may affect only the 15 new files; broad automatic formatting of unrelated existing files is prohibited.

**Targeted construction linting:** `uv run ruff check <current Batch 1B-B files>`.

**Final repository-wide gates:** `uv lock --check`; `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy src tests`; `uv run pytest -q`.

**Additional import verification:** import all 17 approved names from `btmm_ai_scanner.contracts`; confirm exact `__all__` count and order. All gates must pass before architectural review.

### 24K. Mandatory Stop Conditions

Implementation must stop immediately when any of the following occurs: HEAD differs from the approved baseline; working tree is dirty at the start; local and remote `main` are not synchronized; Python is not `3.12.13`; `uv` is not `0.11.30`; existing baseline tests do not pass or the count is not 34; Pydantic resolves outside the approved range; a locked development tool changes unexpectedly; `InternalSymbol` or `Timeframe` does not match approved assumptions; an approved field name, order, or count cannot be implemented; strict Pydantic behavior conflicts with an approved rule; an eighteenth changed path appears; a documentation or private-reference file changes; a generated schema or persisted manifest file appears; an unapproved helper appears; a stage test fails; Ruff fails; mypy fails; the full test suite fails; exact test names or counts differ; final exports differ in count or order.

**Stop behavior:** do not stage, commit, or push; do not weaken an approved rule; do not silently expand scope; preserve the working diff; report the exact failure and affected files.

### 24L. Correction Boundary

Corrections are permitted only within the authorized 17 paths and only when preserving every approved decision.

**Permitted:** syntax fixes; import fixes; type-annotation fixes; validator implementation fixes; test corrections that restore approved behavior; formatting of new files; Ruff or mypy corrections that do not change policy.

**Prohibited without a new author decision:** renaming a field; reordering fields; changing a field type; adding a default; adding coercion; adding a public export; adding or removing a test function; relaxing strict validation; changing version policy; changing evidence labels; adding a generator, calculation behavior, loader, or persistence; changing the 17-path boundary.

**Record:** a policy contradiction requires a stop and escalation.

### 24M. Rollback Boundary

**Exact approved rollback point:** `9249c1584389993f22a3d5753f9fc37d6e00fc9c`.

**Record:** no automatic rollback is approved; partial work remains available for review unless rollback is explicitly authorized.

**Explicitly prohibited:** `git reset --hard`; `git clean`; blanket repository deletion; force checkout; history rewriting.

**A future explicitly authorized rollback may affect only:** `pyproject.toml`; `uv.lock`; the exact 15 new Batch 1B-B files.

**Rollback requirements:** restore only the two modified dependency files; remove only the exact 15 new files; do not alter documentation or earlier implementation; return to the approved baseline with a clean tree.

### 24N. Successful Implementation Completion State

**HEAD remains:** `9249c1584389993f22a3d5753f9fc37d6e00fc9c`.

**Exactly 17 changed paths** (2 modified, 15 new). **Nothing staged, committed, or pushed.**

**Completion requires:** Pydantic dependency and lock verified; all approved contracts implemented; exactly 132 top-level test functions; full suite passes; Ruff format check passes; Ruff lint passes; mypy passes; import smoke passes; exact export order passes; no unapproved path exists; no documentation file changes; batch remains not production-approved.

**Record:** the implementation report must be submitted for architectural review before any commit instruction is issued.

### 24O. Post-Implementation Closure Sequence

**Approved future sequence:** (1) author explicitly authorizes Batch 1B-B implementation; (2) Claude implements exactly the 17-path scope; (3) Claude stops with 17 unstaged paths; (4) architectural review is performed; (5) exact implementation paths are committed and pushed; (6) a separate documentation-only closure update is prepared; (7) closure documentation is reviewed; (8) closure documentation is committed and pushed; (9) Batch 1B-B is marked closed but not production-approved.

### 24P. Implementation-Authorization Phrase

**Exact future implementation-authorization phrase:** `AUTHORIZE PHASE 1B-B IMPLEMENTATION`.

**Record:** Decision Group 6 approval is not implementation authorization. No dependency or implementation action begins until that separate phrase is provided after Decision Group 6 documentation is committed.

### 24Q. Decision Accounting

**Decision Group 6: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** Resolves: exact 17-path execution boundary (§24B); dependency-lock procedure (§24C); per-file construction sequence (§24D–§24H); incremental test sequence (§24D–§24G); exact 132-test-function boundary (§24I); final quality gates (§24J); mandatory stop conditions (§24K); correction boundary (§24L); rollback boundary (§24M); review-before-commit requirement (§24N); post-implementation closure sequence (§24O).

**Does not authorize:** dependency installation; source creation; test creation; staging; committing; pushing; production approval; Batch 1B-B implementation.

**Batch 1B-B is not marked authorized or started by this section.**

## 25. Phase 1B-B Baseline Correction 6A — Post-Control-Documentation Implementation Baseline

**Status: `AUTHOR-APPROVED`, `DOCUMENTATION CORRECTION ONLY`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

### 25A. Governance Contradiction

Decision Group 6 (§24A, §24M) recorded `9249c1584389993f22a3d5753f9fc37d6e00fc9c` as the implementation starting commit and rollback point. The Decision Group 6 documentation itself was then committed (`70fde0b8e49c2ef48397ea29090f6a36af61899b`, "Document Phase 1B-B implementation controls"), which necessarily advanced the clean, synchronized repository HEAD past the value that document had named as its own baseline. Left uncorrected, Decision Group 6's own mandatory HEAD-match stop condition (§24K) would permanently block implementation — no future clean-tree state could ever equal `9249c15...` again without discarding the committed control documentation, and doing so via reset would itself violate the approved rollback restrictions (§24M: no `git reset --hard`, no history rewriting).

### 25B. Author-Approved Correction

**Corrected implementation starting commit:** `70fde0b8e49c2ef48397ea29090f6a36af61899b`.

**Corrected implementation rollback and clean-tree target:** `70fde0b8e49c2ef48397ea29090f6a36af61899b`.

**`9249c1584389993f22a3d5753f9fc37d6e00fc9c` is now recorded as:** `HISTORICAL PRE-DECISION-GROUP-6 CHECKPOINT ONLY`. It is no longer the implementation starting commit, the rollback target, or the required clean-tree target.

### 25C. Implementation Authorization

The author was asked, before this correction was drafted, whether "the author has already provided `AUTHORIZE PHASE 1B-B IMPLEMENTATION`" (as asserted in the correction request's checkpoint framing) reflected an actual prior instruction in this session — it did not; no such phrase had been sent before that point. The author then explicitly confirmed, in direct response to that question, that the phrase should be treated as granted now, alongside this baseline correction.

**Record, accurately timestamped:** `AUTHORIZE PHASE 1B-B IMPLEMENTATION` was granted by the author during the drafting of Baseline Correction 6A, not before Decision Group 6 was committed. This satisfies §24P's requirement for a separate, explicit authorization distinct from Decision Group 6's own approval. The authorization does not need to be repeated in a later instruction.

**Record:** implementation remains blocked only until this Baseline Correction 6A documentation is itself reviewed, committed, and pushed (so that the corrected baseline commit is the actual HEAD implementation begins from). **Implementation has not started as of this documentation task.**

### 25D. Preserved Decision Group 6 Controls

Correction 6A changes only the baseline and rollback commit references (§25B). Every other Decision Group 6 control remains unchanged: branch `main`; Python `3.12.13`; `uv` `0.11.30`; existing baseline of 34 passing tests; the exact 17 changed-path scope (2 modified dependency files, 15 new implementation files, no 18th path); `pydantic>=2.13.4,<2.14`; the Stage A–E construction sequence; exactly 132 top-level test functions; the mandatory static AST-based test-name and count verification; the Ruff formatting, Ruff lint, mypy, and full pytest gates; the seventeen-name import/export verification; all mandatory stop conditions (§24K, re-anchored to the corrected baseline); the policy-preserving correction boundary (§24L); the prohibition on documentation changes during implementation; the prohibition on automatic rollback, `git reset --hard`, `git clean`, force checkout, and history rewriting; the stop-before-staging requirement; architectural review before the implementation commit; the separate closure-documentation sequence; and the absence of production approval.

**No other approved policy is altered by this correction.**

## 26. Phase 1B-B Baseline Correction 6B — Execution-Captured Baseline Policy

**Status: `AUTHOR-APPROVED`, `DOCUMENTATION CORRECTION ONLY`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

### 26A. The Recurring Baseline Problem

Decision Group 6 (§24A) hard-coded the pre-documentation commit as the future implementation baseline; committing Decision Group 6 moved HEAD and made that baseline stale. Correction 6A (§25B) then hard-coded *its own* pre-commit parent as the future implementation baseline; committing Correction 6A again moved HEAD and made that baseline stale. **Any policy that hard-codes the parent commit before its own documentation commit will reproduce the same contradiction.** Repeated fixed-hash documentation corrections are therefore rejected as a durable solution.

### 26B. Durable Author-Approved Replacement Policy

**ACTIVE IMPLEMENTATION BASELINE:** the clean synchronized HEAD observed immediately before the first Batch 1B-B implementation change, after all approved implementation-control documentation has been committed and pushed.

**EXECUTION ROLLBACK TARGET:** the same full HEAD hash captured immediately before the first Batch 1B-B implementation change.

**Required implementation-start commands:**

```
git status --short --untracked-files=all
git diff --stat
git diff --cached --stat
git rev-parse HEAD
git rev-parse origin/main
```

**Implementation may begin only when:** working tree is clean; nothing is staged; HEAD equals `origin/main`; current HEAD contains all approved implementation-control documentation; no Batch 1B-B implementation path exists; runtime dependencies remain empty before dependency addition; Python is exactly `3.12.13`; `uv` is exactly `0.11.30`; the existing baseline suite passes at exactly 34 passing tests; inventory remains 52 rows; Batch 1B-B remains 15 inventoried files; authorized implementation scope remains 17 changed paths.

**Record:** the full observed HEAD hash must be captured before the first implementation change — that hash becomes both the **execution-captured baseline** and the **execution rollback target**. The captured hash must be included in the implementation completion report. No additional documentation commit is required merely to record the captured hash before implementation. No source, test, or dependency modification may occur before baseline capture. **If HEAD changes before implementation starts, the newly observed clean synchronized HEAD is captured instead.** A dirty, staged, or diverged repository remains a mandatory stop condition.

### 26C. Historical Checkpoint Status

| Commit | Status |
|---|---|
| `9249c1584389993f22a3d5753f9fc37d6e00fc9c` | `HISTORICAL PRE-DECISION-GROUP-6 CHECKPOINT ONLY` |
| `70fde0b8e49c2ef48397ea29090f6a36af61899b` | `HISTORICAL PRE-CORRECTION-6A CHECKPOINT ONLY` |
| `cc43df0dbdc6148567cb33c71a87bf0441f0f351` | `CURRENT CLEAN SYNCHRONIZED CANDIDATE BASELINE AT THE TIME CORRECTION 6B WAS AUTHORED` |

**Record:** `cc43df0d...` becomes the execution baseline only if it is still the clean synchronized HEAD immediately before implementation begins. If another documentation commit moves HEAD, the newer clean synchronized HEAD is captured. **None of these hashes is permanently hard-coded as the future execution baseline.** Historical hashes remain useful audit checkpoints only.

### 26D. Authorization Status

Implementation authorization was confirmed during the drafting of Baseline Correction 6A (§25C). That authorization remains valid; the authorization phrase does not need to be repeated. **Correction 6B does not create a new authorization and does not revoke or replace the existing one.** Implementation remains blocked only until this Correction 6B documentation is reviewed, committed, and pushed. **Implementation has not started.**

### 26E. Preserved Decision Group 6 Controls

Correction 6B changes only the *method* used to establish the active implementation baseline and rollback target (§26B replaces the fixed-hash mechanism of §24A/§24M and §25B). Every other Decision Group 6 control remains unchanged: branch `main`; Python `3.12.13`; `uv` `0.11.30`; existing baseline of 34 passing tests; the exact 17-path implementation scope (2 modified dependency files, 15 new implementation files, no 18th path); `pydantic>=2.13.4,<2.14`; the Stage A–E construction sequence; exactly 132 top-level test functions; the mandatory static AST-based test-name and count verification; the Ruff formatting, Ruff lint, mypy, and full pytest gates; the seventeen-name import/export verification; the policy-preserving correction boundary (§24L); the prohibition on documentation changes during implementation; the prohibition on automatic rollback, `git reset --hard`, `git clean`, force checkout, blanket deletion, and history rewriting; the stop-before-staging requirement; architectural review before the implementation commit; the separate closure-documentation sequence; and the absence of production approval.

**Record:** the prior fixed-hash HEAD-match stop condition is replaced by the execution-captured-baseline verification (§26B). After capture, any unexpected HEAD change during implementation is itself a mandatory stop condition. Rollback remains separately authorized and non-automatic; rollback may affect only `pyproject.toml`, `uv.lock`, and the exact 15 new implementation files. The captured execution baseline must not change during the implementation run.

### 26F. Decision Accounting

**Baseline Correction 6B: `AUTHOR-APPROVED`, `DOCUMENTATION CORRECTION ONLY`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** Replaces the fixed-hash baseline/rollback mechanism of §24A/§24M/§25B with the durable execution-captured-baseline policy (§26B). Does not alter Decision Groups 1–6, Correction 6A's authorization record (§25C), the 17-path scope, the 132-test-function boundary, or any quality gate, stop condition, correction boundary, or rollback restriction not specifically named above.

**Batch 1B-B is not marked authorized or started by this section.**

## 27. Phase 1B-B Implementation Closure

**Status: `AUTHOR-AUTHORIZED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

### 27A. Implementation Commit

**Commit:** `1b8602a5dcc97a89be51ba5ee65ab4940751567a`. **Commit message:** "Implement Phase 1B-B contract foundation". **Execution-captured baseline and rollback target (per Baseline Correction 6B, §26):** `4074a80fe53b7784d3a51a3ac15f2fe85d244104`.

### 27B. Implemented Scope

Exactly **17 committed paths**: 2 modified dependency files (`pyproject.toml`, `uv.lock`), 15 new implementation files (8 new source files, 7 new test files). No eighteenth path. No documentation file included. No private-reference file included.

### 27C. Environment and Dependency Results

Python `3.12.13`; `uv` `0.11.30`; Pydantic `2.13.4` (resolved within the approved `>=2.13.4,<2.14` range). **Direct runtime dependencies:** `pydantic>=2.13.4,<2.14` only. Development-tool versions unchanged: `pytest 9.1.1`, `mypy 2.3.0`, `Ruff 0.15.22`.

### 27D. Implemented Components

**Stage A:** `ContractModel`, `UUIDv7`, `SHA256Fingerprint`, project-owned `SemVer`.
**Stage B:** `CandleCompleteness`, `CandleVolumeKind`, `RawCandle`, `NormalizedCandle`.
**Stage C:** `EvidenceClassification`, `ProvenanceSourceReference`, `ProvenanceRecord`, `ValidationStatus`, `AnalyticalEligibility`, `ValidationResult`.
**Stage D:** `CompatibilityClass`, `RuleVersionManifest`, `SchemaVersionManifest`.
**Stage E:** the exact approved 17-name public export boundary (`src/btmm_ai_scanner/contracts/__init__.py`).

### 27E. Verification Results

Pre-implementation baseline: **34 passed.** Final full suite: **221 passed.** Original baseline tests re-run after implementation: **34 passed.** Exact top-level test-function total: **132**. `uv lock --check`: passed. Ruff format check: passed. Ruff lint: passed. mypy: passed. Direct import verification (all 17 names): passed. Exact `__all__` order verification: passed.

### 27F. Architectural Audit Verdict

**`B. PASS WITH NON-BLOCKING FINDINGS — READY FOR COMMIT REVIEW`.** No blocking finding remained before commit.

### 27G. Pre-Commit Test Correction

**File:** `tests/unit/test_validation_result.py`. **Existing test function:** `test_validation_result_validates_reason_code_format`. **Added invalid padded reason-code parameter:** `" CODE_A"`. No production code changed. `ValidationResult` top-level test-function count remained 16. Grand total top-level test-function count remained 132. Full collected test total increased from 220 to 221. The correction preserved the exact 17-path scope.

**Classification: `POLICY-PRESERVING PRE-COMMIT TEST-COVERAGE CORRECTION`.**

### 27H. Non-Blocking Audit Findings (Accepted)

1. **`RawCandle`/`NormalizedCandle` cross-field validators report the first failing invariant rather than aggregating every failure in one construction attempt.** Disposition: accepted; does not permit validation bypass; no code correction required.
2. **Strict Decimal rejection was tested through a representative field sharing the common validator rather than separately repeating the same test for every OHLC field.** Disposition: accepted; the shared validator was independently inspected; no code correction required.

Neither finding is a production defect.

### 27I. Procedural Deviation

During the implementation's AST verification, Claude temporarily created `scratch_ast_check.py`, which briefly introduced an eighteenth untracked path. The implementation instruction prohibited creating a verification script and required stopping when an eighteenth path appeared; Claude continued rather than stopping immediately. The temporary file was deleted before final verification, was never staged, was never committed, and does not appear in the final 17-path implementation scope. The subsequent read-only architectural audit independently verified all implementation files and found no evidence that the temporary script affected implementation correctness.

**Classification: `DISCLOSED NON-PERSISTENT PROCEDURAL DEVIATION`.**

**Disposition:** accepted for Phase 1B-B closure; no rollback required; no implementation-code correction required; remains visible in the audit trail (this section, and the corresponding sections of `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md`/`REPOSITORY_SCAFFOLD_PLAN.md`/`PROJECT_STATE.md`).

### 27J. Closure Accounting

**Phase 1B-B: `AUTHOR-AUTHORIZED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** Inventory remains 52 rows. Batch 1B-B remains 15 inventoried files. No Phase 1B-C work has begun.

## 28. Phase 1B-C Decision Group 1 — Market-Data Pipeline Architecture

**Status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

This section records an author-approved architecture, not yet an implementation. No file under `src/`, `tests/`, or any dependency/config file is created or modified by this section. It reuses the closed Batch 1B-B contracts (`RawCandle`, `NormalizedCandle`, `ValidationResult`, `ProvenanceRecord`, `RuleVersionManifest`, `SchemaVersionManifest`, `InternalSymbol`, `Timeframe`) without proposing any duplicate candle, symbol, timeframe, validation, or provenance model. `InternalSymbol` (`XAUUSD`/`EURUSD`/`GBPUSD`) and `Timeframe` (`M1`/`M5`/`M15`/`H1`/`H3`/`H4`/`D1`/`W1`) were directly inspected in `src/btmm_ai_scanner/config/enums.py` and already cover every timeframe and symbol named below.

### 28A. Provider, Provider Symbols, and Canonical Visual Reference

**Provider identity:** `FXCM`. **Initial provider symbols** (the provider's own payload-facing symbols): `XAUUSD`, `EURUSD`, `GBPUSD`. **Canonical TradingView visual-comparison references** (a separate, display-only mapping): `FXCM:XAUUSD`, `FXCM:EURUSD`, `FXCM:GBPUSD` — **TradingView is not the execution broker**, and the TradingView ticker must **not** be treated as though it were necessarily the provider payload's raw symbol; the two remain independently mapped. **Internal symbols:** the existing `InternalSymbol.XAUUSD`/`InternalSymbol.EURUSD`/`InternalSymbol.GBPUSD` members (§28 preamble), reused without duplication. The architecture remains provider-neutral so a second source may be added later without redesign.

### 28B. Pipeline Responsibility

**In scope:** receiving provider candle records; preserving source metadata; building `RawCandle` records; validating source candle integrity; mapping source symbols/timeframes; producing `NormalizedCandle` records; detecting exact duplicates; detecting conflicting revisions; detecting potential missing-candle gaps; emitting records to a storage/replay boundary.

**Explicitly out of scope:** POI detection; market-structure detection; BTMM detection; indicator drawing; signal generation; trade execution; risk management; AI model inference.

### 28C. Historical and Live Separation

Two ingestion entry points: **historical ingestion** and **live ingestion**. They share one immutable, provider-neutral `SourceCandleInput` contract and the same strict validation/construction policy, but must not share hidden mutable state.

- **Historical ingestion:** processes bounded candle collections; supports deterministic replay; may process candles faster than real time; must preserve original event and availability timestamps; must not impersonate live arrival behavior.
- **Live ingestion:** processes sequential incoming records; uses actual processing time; must handle delayed, duplicate, and revised candles; must not rewrite historical records silently.

`raw_candle_builder.py` exposes two explicit, stateless public construction entry points implementing this separation: `build_historical_raw_candle` and `build_live_raw_candle` (full detail §28K.4).

### 28D. Raw-to-Normalized Flow

**First-implementation-batch flow (starts at `SourceCandleInput`):** `SourceCandleInput` → structural/input validation → availability-evidence decision (§28H) → `RawCandle` construction → `ValidationResult` → symbol/timeframe mapping → `NormalizedCandle` → idempotency decision → potential-gap observation → storage/replay port boundary.

**Future external flow (explicitly out of the first batch, §28K):** provider payload → future provider adapter/parser → `SourceCandleInput` → first-batch pipeline (above). The first batch never accepts or parses a raw external provider payload directly — it begins at the already-constructed `SourceCandleInput` boundary.

`RawCandle` and `NormalizedCandle` remain immutable (per §21). Corrections create new records rather than mutating earlier records. Validation failure does not silently discard the source input — a `RawCandle` is constructed whenever complete availability evidence and every other requirement pass, and a `ValidationResult` (§22) records `INVALID`/`INDETERMINATE` against it, keeping invalid and indeterminate records auditable rather than dropped. When availability evidence is incomplete, no `RawCandle` is constructed at all (§28H) — the `INDETERMINATE`/`REJECTED` outcome is recorded directly against the `SourceCandleInput` via `IngestionResult` (§28J).

### 28E. Source Mapping

A source-mapping registry boundary maps `(provider, provider_symbol, provider_timeframe)` to `(InternalSymbol, Timeframe)`. Initial approved provider-symbol mappings: `FXCM` `XAUUSD` → `InternalSymbol.XAUUSD`; `FXCM` `EURUSD` → `InternalSymbol.EURUSD`; `FXCM` `GBPUSD` → `InternalSymbol.GBPUSD` — keyed on the **provider payload's own symbol** (§28A), not the TradingView ticker. TradingView visual-reference metadata (`FXCM:XAUUSD` etc.) is a **separate mapping**, used only for canonical visual comparison, and is never consulted by the source-mapping registry that produces `InternalSymbol`/`Timeframe`. **No duplicate symbol or timeframe enum is proposed** — the existing `InternalSymbol`/`Timeframe` members already cover every value needed, including `W1`, `D1`, `H4`, `H3`, `H1`, `M15`, `M5`, `M1`. Synthetic timeframe aggregation (e.g., deriving `H3` from smaller candles) is **not approved for the first implementation batch** and, if ever proposed, must be explicitly separated from source mapping as its own decision.

### 28F. Source Reference Semantics, Idempotency, and Duplicates

**`source_reference` semantics:** a stable logical identifier for the provider feed, data series, or approved source channel from which the candle originated. It must remain stable across replaying or reimporting the same source series; it must **not** be a temporary local filename, an import-session UUID, or a download-batch identifier — file, batch, and import-session identity belong in `ProvenanceRecord` or a later ingestion-metadata record, not in `source_reference`. This stable meaning is required because `source_reference` participates in the source identity key below.

**Source candle identity key** (project-owned, immutable, first batch): `(provider, source_reference, source_symbol, source_timeframe, event_time_utc)`. This identifies a **source-series candle observation**. Content fingerprint alone is **not** used as identity. A canonical candle-slot identity spanning different providers or source references is a separate, later concern and is **not** silently merged in the first batch.

| Identity key | Content fingerprint | Outcome |
|---|---|---|
| Same | Same | `EXACT_DUPLICATE` — replay-safe, no second normalized record required, no error, auditable decision |
| Same | Different | `CONFLICTING_REVISION` — see the quarantine rules below (resolved as RM-1, §28M) |
| New | — | `NEW_RECORD` |

**Idempotency service boundary:** stateless. It receives a candidate `RawCandle` (or source identity) and the existing records for that same source identity (supplied via `CandleReadRepository`, §28I), and returns an explicit idempotency decision. It must not maintain hidden process-global state, implement a database, implement an in-memory production repository, or mutate existing candles. Test-local in-memory doubles are permitted.

### 28G. Missing-Candle Handling

Missing-candle handling is **gap observation, not automatic fabrication**. Gap comparison occurs **only between candles belonging to the same mapped internal symbol and timeframe series**. The first implementation batch: compares consecutive normalized-candle event times using the expected interval for the mapped timeframe; emits a gap observation when an expected interval appears absent; never creates synthetic candle values; never interpolates OHLC or volume; never classifies weekends or closures.

The first implementation batch supports only `POTENTIAL_GAP` (resolved as GAP-1, §28M). `CONFIRMED_GAP` and `EXPECTED_MARKET_CLOSURE` remain unavailable until a trading-session calendar is approved.

### 28H. Availability-Time Semantics

`event_time_utc` represents the candle's market event boundary; `availability_time_utc` represents when the provider made the candle available as a usable record; `processing_time_utc` represents when this system processed it. `RawCandle.availability_time_utc` and `RawCandle.original_availability_time` remain required, non-optional fields (§21D) — Batch 1B-B contracts are closed and no field change is proposed. This representation resolves AT-1 without changing the completed Phase 1B-B `RawCandle` contract.

**`SourceCandleInput` availability keys (corrected):** `availability_time_utc: datetime | None` and `original_availability_time: datetime | None` — **both keys are mandatory on the input structure; their values are explicitly nullable.** Neither field has an automatic default; both must be supplied by the caller; omitting either key entirely is an invalid source-input structure (a structural error, distinct from the availability-evidence decision below). Explicit `None` represents unavailable provider evidence — the pipeline never silently substitutes an omitted field with `None`, and never invents availability evidence.

**Exact availability-evidence decision matrix, evaluated before any `RawCandle` is constructed:**

1. **Both fields present as valid, timezone-aware `datetime` values representing the same instant:** continue approved timestamp validation (naive rejection, UTC normalization, original/canonical instant correspondence, per §21H); `RawCandle` construction may proceed once every other requirement passes.
2. **Both fields explicitly `None`:** outcome `INDETERMINATE`; no `RawCandle` is constructed; no `NormalizedCandle` is constructed; `processing_time_utc` is not substituted; recommended reason code `AVAILABILITY_TIME_UNAVAILABLE`.
3. **Exactly one field is `None` and the other holds a value:** outcome `REJECTED`; no `RawCandle` is constructed; recommended reason code `AVAILABILITY_TIME_PAIR_INCONSISTENT`.
4. **Either supplied availability datetime is naive, malformed, or does not match the corresponding instant:** outcome `REJECTED`; no `RawCandle` is constructed; an explicit validation reason code is used; this is **not** reinterpreted as unavailable evidence (case 2) — a badly formed value is a rejection, not an absence.

**AT-1 status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`** (§28M).

### 28I. Storage and Replay Boundary

Interfaces only in the first implementation batch: `RawCandleSink`, `NormalizedCandleSink`, `CandleReadRepository`, `HistoricalReplaySource`. `CandleReadRepository` is the approved port through which the idempotency service (§28F) later obtains existing records for a source identity. **Not implemented in the first batch:** PostgreSQL, SQLite, Redis, Kafka, cloud storage, database migrations, ORM models. In-memory test doubles only.

### 28J. Error and Result Model

**Recommendation:** one enum (`IngestionOutcome`: `ACCEPTED`, `REJECTED`, `INDETERMINATE`, `EXACT_DUPLICATE`, `CONFLICTING_REVISION`) plus one generic `IngestionResult` model carrying the outcome and a reference to the affected record(s), **combined with a separate, narrowly-scoped `GapObservation` model** for `POTENTIAL_GAP`. Rationale: a gap observation describes a relationship *between two records* (the interval that is missing), not an outcome *of processing one record* — folding it into the same per-record outcome enum would force awkward null/context fields on every other outcome. Unstructured exceptions are not the pipeline's only output; exceptions remain reserved for genuine programming errors, not for expected pipeline decisions.

### 28K. First Implementation Batch (Recommended, Compact)

**Explicitly excluded from the first batch:** network API calls; WebSocket connections; TradingView scraping; database persistence; historical file downloads; live FXCM connectivity; POI logic; BTMM logic; indicator visualization; alerts; backtesting; robot execution. **Also explicitly excluded (corrected first-batch input boundary):** FXCM REST response parsing; FXCM WebSocket parsing; CSV parsing; broker-specific payload adapters; any raw external provider payload parser. **The first batch begins at `SourceCandleInput`** (§28D) — it does not accept or parse raw external provider payload formats directly. A future provider adapter translates raw provider payloads into `SourceCandleInput`; the first batch validates, maps, and processes already-constructed `SourceCandleInput` values only. Controlled fixtures construct `SourceCandleInput` directly for testing.

**Caller-supplied identity and version boundary (binding on every file below):** the pipeline must **not** generate UUIDv7 record IDs, UUIDv7 provenance IDs, SHA-256 content fingerprints, rule versions, contract versions, or schema versions — these remain caller-supplied by controlled fixtures or future adapters. The first batch validates and assembles approved contracts only. **No UUID generator, fingerprint calculator, canonical-JSON hash implementation, or automatic version default may be added.** `SourceCandleInput` must carry, directly or through an explicitly supplied construction context, every value required to construct a `RawCandle` without hidden generation.

**Proposed source files (9):**

| # | Exact path | Responsibility | Direct dependencies | New/Modified | Why in the first batch |
|---|---|---|---|---|---|
| 1 | `src/btmm_ai_scanner/market_data/__init__.py` | Marks `market_data` as a package | package root | New | Minimal package boundary, matching the `contracts/__init__.py` pattern |
| 2 | `src/btmm_ai_scanner/market_data/source_input.py` | Provider-neutral, immutable `SourceCandleInput` shape — mandatory-but-nullable `availability_time_utc`/`original_availability_time` (§28H); caller-supplied identifiers, fingerprints, and versions; no provider networking or payload parsing | none (stdlib only) | New | Establishes the provider-neutral, availability-gated entry point before any `RawCandle` is built (§28H); the first batch's actual starting point (§28D) |
| 3 | `src/btmm_ai_scanner/market_data/source_mapping.py` | FXCM source-mapping registry (policy only): `(provider, provider_symbol, provider_timeframe) → (InternalSymbol, Timeframe)`, separate from the TradingView visual-reference mapping. **Not** an FXCM network adapter or payload parser | `config/enums.py` | New | Required before normalization can assign `InternalSymbol`/`Timeframe` (§28E) |
| 4 | `src/btmm_ai_scanner/market_data/results.py` | `IngestionOutcome` enum, `IngestionResult` model — no gap-relationship model here | none (stdlib + `uuid`) | New | Shared result vocabulary needed by every downstream service |
| 5 | `src/btmm_ai_scanner/market_data/raw_candle_builder.py` | `build_historical_raw_candle`/`build_live_raw_candle` stateless entry points, **each accepting a `SourceCandleInput`, never an arbitrary provider dictionary**; availability-evidence decision (§28H); `RawCandle` construction; `ValidationResult` integration; no hidden generation | `contracts/raw_candle.py`, `contracts/validation_result.py`, `market_data/source_input.py`, `market_data/results.py` | New | First stage of the approved flow, implementing historical/live separation exactly (§28C) |
| 6 | `src/btmm_ai_scanner/market_data/normalization.py` | Produces `NormalizedCandle` from a validated `RawCandle` using `source_mapping.py` | `contracts/raw_candle.py`, `contracts/normalized_candle.py`, `market_data/source_mapping.py` | New | Second stage of the approved flow |
| 7 | `src/btmm_ai_scanner/market_data/idempotency.py` | Stateless source candle identity key and `EXACT_DUPLICATE`/`CONFLICTING_REVISION`/`NEW_RECORD` decision | `contracts/raw_candle.py`, `market_data/results.py` | New | Implements §28F exactly |
| 8 | `src/btmm_ai_scanner/market_data/gap_observation.py` | `GapObservation` model; `POTENTIAL_GAP` classification; expected-interval comparison; no synthetic candle creation | `contracts/normalized_candle.py`, `config/enums.py` | New | Implements §28G exactly (`POTENTIAL_GAP` only) |
| 9 | `src/btmm_ai_scanner/market_data/ports.py` | `RawCandleSink`/`NormalizedCandleSink`/`CandleReadRepository`/`HistoricalReplaySource` protocol interfaces | `contracts/raw_candle.py`, `contracts/normalized_candle.py`, `market_data/results.py` | New | Implements §28I exactly; interfaces only, no concrete storage |

**Proposed test files (8), unit tests only:**

| # | Exact path | Covers | Function count |
|---|---|---|---|
| 1 | `tests/unit/test_source_input_and_results.py` | `SourceCandleInput` shape/immutability; mandatory-but-nullable availability keys; the exact decision matrix (both present/valid; both `None` → `INDETERMINATE`; one `None` → `REJECTED`; naive/malformed/mismatched → `REJECTED`); caller-supplied identity/version boundary; `IngestionOutcome`/`IngestionResult` | 8 |
| 2 | `tests/unit/test_source_mapping.py` | Source mapping, provider-symbol vs. TradingView-reference separation | 7 |
| 3 | `tests/unit/test_raw_candle_builder.py` | Raw candle construction from `SourceCandleInput` only (never an arbitrary provider payload dictionary); UTC/original timestamp preservation; invalid input rejection; no RawCandle without complete availability evidence; historical/live entry points; no provider parser or network adapter invoked | 8 |
| 4 | `tests/unit/test_normalization.py` | Normalization, symbol/timeframe mapping | 7 |
| 5 | `tests/unit/test_idempotency.py` | Exact-duplicate detection, conflicting-revision quarantine, statelessness | 8 |
| 6 | `tests/unit/test_gap_observation.py` | Potential-gap detection, same-series-only comparison, no synthetic fabrication | 7 |
| 7 | `tests/unit/test_ingestion_ports.py` | Interface conformance, in-memory test doubles | 6 |
| 8 | `tests/unit/test_historical_live_separation_and_no_synthetic_fabrication.py` | Historical/live separation, no silent mutation, no synthetic candle fabrication, auditable invalid/indeterminate records | 6 |

**Total proposed new paths: 17** (9 new source files + 8 new test files). **No dependency change is required** — the batch reuses the already-approved Pydantic dependency and the closed Batch 1B-B contracts. **No documentation file would change during that implementation** (matching the Batch 1B-B pattern). **No eighteenth implementation path is proposed.**

### 28L. Test and Quality Boundary

**Recommended exact top-level test-function count: 57**, distributed exactly as the table in §28K: `test_source_input_and_results.py` 8; `test_source_mapping.py` 7; `test_raw_candle_builder.py` 8; `test_normalization.py` 7; `test_idempotency.py` 8; `test_gap_observation.py` 7; `test_ingestion_ports.py` 6; `test_historical_live_separation_and_no_synthetic_fabrication.py` 6 (`8+7+8+7+8+7+6+6 = 57`). This count is a recommendation pending author approval, in the same manner as Batch 1B-B's per-file counts were recommended before being approved.

**Preserved from Batch 1B-B without change:** Ruff; mypy; pytest; `uv lock --check`; strict path-scope verification; stop-before-staging; read-only architectural audit before commit.

### 28M. Open Author Decisions

Each item below is **`AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`** — the author explicitly approved all three resolutions (§28N). None of the three authorizes production use or implementation outside the exact first-batch scope (§28K).

**AT-1 — Availability-time-quality representation. `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**
*Recommended resolution (corrected):* `SourceCandleInput.availability_time_utc`/`.original_availability_time` are mandatory keys with explicitly nullable (`datetime | None`) values, no automatic default, both always supplied by the caller — omitting either key is an invalid input structure, distinct from a supplied `None`. The exact decision matrix (§28H): both present and consistent → continue normal validation, `RawCandle` may be constructed; both explicitly `None` → `INDETERMINATE`, no `RawCandle`/`NormalizedCandle` constructed, reason code `AVAILABILITY_TIME_UNAVAILABLE`; exactly one `None` → `REJECTED`, no `RawCandle` constructed, reason code `AVAILABILITY_TIME_PAIR_INCONSISTENT`; naive/malformed/instant-mismatched values → `REJECTED` via an explicit validation reason code, never reinterpreted as absence. `processing_time_utc` is never silently substituted as `availability_time_utc`; no artificial microsecond or timeframe offset may be invented; no Phase 1B-B candle-contract change is required; a later, author-approved availability-assumption policy with explicit provenance/quality metadata may be introduced by a future provider adapter; controlled historical fixtures may supply known availability times so the first pipeline batch can be implemented and tested. *Alternative rejected:* adding a field directly to `RawCandle` — rejected because Batch 1B-B contracts are closed, and mixing ingestion metadata into the provider-facing domain contract blurs its boundary. *Engineering reason:* keeps `RawCandle` stable while still refusing to invent certainty, and cleanly separates "structurally missing key" from "explicitly declared unavailable" from "malformed value." *Effect on indicator timeline:* does not block the controlled market-data pipeline or historical replay using approved fixtures; actual provider backfills lacking availability metadata remain quarantined until a later adapter policy is approved.

**RM-1 — Conflicting-revision resolution policy. `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**
*Recommended resolution:* for the first implementation batch, same source identity plus a different fingerprint produces `CONFLICTING_REVISION`; the candidate `RawCandle` remains auditable and the existing record reference remains auditable; neither record is silently overwritten; the conflict result must expose both relevant record identifiers/references; the unresolved candidate must not be emitted as an accepted downstream `NormalizedCandle`; no automatic winner is selected; no newest-arrival, highest-volume, or latest-processing-time rule is permitted; revision-resolution policy is deferred to a later controlled decision. *Alternative rejected:* automatic "latest received wins" resolution — rejected because it could silently discard a legitimate provider correction, violating the no-silent-overwrite principle (§28F). *Engineering reason:* the pipeline's job is detection and quarantine, not adjudication. *Effect on indicator timeline:* does not block ordinary non-conflicting candle streams; protects the future indicator from consuming ambiguous revised candles.

**GAP-1 — Trading-session/calendar boundary. `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**
*Recommended resolution:* the first implementation batch supports only `POTENTIAL_GAP`; gap comparison occurs only between candles belonging to the same mapped internal symbol and timeframe series; the service compares consecutive event times against the expected interval; it never fabricates candles, never interpolates OHLC or volume, and does not classify weekends or closures; `CONFIRMED_GAP` and `EXPECTED_MARKET_CLOSURE` remain unavailable until a trading-session calendar is approved by a dedicated future decision group. *Alternative rejected:* hand-rolling an ad hoc weekend-only calendar now — rejected because it would miss holidays/rollovers and risks quietly becoming the de facto calendar without dedicated review. *Engineering reason:* calendar correctness affects gap-quality classification, not candle admission. *Effect on indicator timeline:* does not block the first indicator prototype; potential gaps can be surfaced as data-quality warnings.

**No settled Phase 1B-B decision is reopened by this section.**

### 28N. Author Approval Record

The author explicitly approved Phase 1B-C Decision Group 1 in full, including every correction applied across §28A–§28M. **No further architecture correction is required before implementation-control planning.** Approval covers the complete corrected architecture package: provider/provider-symbol/TradingView-visual-reference separation (§28A); pipeline responsibility boundary (§28B); historical/live separation via stateless builders (§28C); the corrected `SourceCandleInput`-starting flow (§28D); source mapping (§28E); `source_reference` semantics, the source identity key, and stateless idempotency (§28F); `POTENTIAL_GAP`-only gap observation (§28G); the corrected availability-time decision matrix (§28H); the storage/replay port boundary (§28I); the result-model recommendation (§28J); the exact 17-path first-batch scope (§28K); the 57-function test allocation (§28L); and the `AUTHOR-APPROVED` AT-1/RM-1/GAP-1 resolutions (§28M).

**This approval does not authorize production use. This approval does not authorize implementation outside the exact first-batch scope named in §28K. Implementation has not started.**

## 29. Phase 1B-C Decision Group 2 — Exact Market-Data Pipeline Implementation Controls

**Status: `AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

This decision group does not reopen Phase 1B-C Decision Group 1 (§28, `AUTHOR-APPROVED`). It defines every implementation detail necessary to code the approved 17-path first batch (§28K) without improvisation: exact model fields, exact function signatures, exact enum values, exact outcome matrices, exact protocol definitions, exact package exports, and the exact 57 test-function names. This approval authorizes only the exact controlled first implementation batch named in §29A; it does not by itself authorize implementation — implementation begins only after a separate, explicit author authorization naming this decision group (per the execution-captured baseline policy, §26).

### 29A. Exact First-Batch File Scope (Restated, Unchanged From §28K)

No change from the approved 17-path scope. Restated here for a single implementation-ready reference:

| # | Path | Kind |
|---|------|------|
| 1 | `src/btmm_ai_scanner/market_data/__init__.py` | New |
| 2 | `src/btmm_ai_scanner/market_data/source_input.py` | New |
| 3 | `src/btmm_ai_scanner/market_data/results.py` | New |
| 4 | `src/btmm_ai_scanner/market_data/source_mapping.py` | New |
| 5 | `src/btmm_ai_scanner/market_data/raw_candle_builder.py` | New |
| 6 | `src/btmm_ai_scanner/market_data/normalization.py` | New |
| 7 | `src/btmm_ai_scanner/market_data/idempotency.py` | New |
| 8 | `src/btmm_ai_scanner/market_data/gap_observation.py` | New |
| 9 | `src/btmm_ai_scanner/market_data/ports.py` | New |
| 10 | `tests/unit/test_source_input_and_results.py` | New |
| 11 | `tests/unit/test_source_mapping.py` | New |
| 12 | `tests/unit/test_raw_candle_builder.py` | New |
| 13 | `tests/unit/test_normalization.py` | New |
| 14 | `tests/unit/test_idempotency.py` | New |
| 15 | `tests/unit/test_gap_observation.py` | New |
| 16 | `tests/unit/test_ingestion_ports.py` | New |
| 17 | `tests/unit/test_historical_live_separation_and_no_synthetic_fabrication.py` | New |

No `pyproject.toml`/`uv.lock` change. No file outside this list. No modification to any Batch 1B-A/1B-B path or to `src/btmm_ai_scanner/config/enums.py`.

### 29B. `source_input.py` — Exact `SourceCandleInput` Contract

`SourceCandleInput` is a `ContractModel` (reusing the exact Batch 1B-B base: `extra="forbid", frozen=True, strict=True, validate_default=True, revalidate_instances="always", allow_inf_nan=False, str_strip_whitespace=False, use_enum_values=False`). Field order mirrors `RawCandle`'s existing 23-field order exactly, with only `availability_time_utc` and `original_availability_time` becoming nullable:

| # | Field | Type | Validation |
|---|-------|------|------------|
| 1 | `record_id` | `UUIDv7` | reused type |
| 2 | `content_fingerprint` | `SHA256Fingerprint` | reused type |
| 3 | `provider` | `str` | nonblank, unstripped (`require_nonblank_stripped_text`) |
| 4 | `source_reference` | `str` | nonblank, unstripped |
| 5 | `source_symbol` | `str` | nonblank, unstripped |
| 6 | `source_timeframe` | `str` | nonblank, unstripped |
| 7 | `event_time_utc` | `datetime` | aware required, normalized to UTC (`require_aware_datetime` + `to_utc`) |
| 8 | `availability_time_utc` | `datetime \| None` | **key mandatory**; if not `None`: aware required, normalized to UTC; if `None`: passed through unchanged |
| 9 | `processing_time_utc` | `datetime` | aware required, normalized to UTC |
| 10 | `original_event_time` | `datetime` | aware required, offset preserved (no forced UTC normalization) |
| 11 | `original_availability_time` | `datetime \| None` | **key mandatory**; if not `None`: aware required, offset preserved; if `None`: passed through unchanged |
| 12 | `original_timezone` | `str` | nonblank, unstripped |
| 13 | `open` | `Decimal` | `validate_price` |
| 14 | `high` | `Decimal` | `validate_price` |
| 15 | `low` | `Decimal` | `validate_price` |
| 16 | `close` | `Decimal` | `validate_price` |
| 17 | `volume` | `Decimal \| None` | `validate_volume` |
| 18 | `volume_kind` | `CandleVolumeKind` | reused type |
| 19 | `completeness` | `CandleCompleteness` | reused type |
| 20 | `rule_version` | `SemVer` | reused type |
| 21 | `contract_version` | `SemVer` | reused type |
| 22 | `schema_version` | `SemVer` | reused type |
| 23 | `provenance_id` | `UUIDv7` | reused type |

**Corrected validation-layer policy (supersedes the prior "Strong recommendation" text — corrects a contradiction identified in the read-only architectural audit between §29B, §29C and §29E):** `SourceCandleInput` construction owns **all** structural/type validity for every field, including both nullable availability fields: required-key validation (all 23 keys must be supplied, including both nullable availability keys — a missing key is a distinct `ValidationError` from a supplied `None`); strict field-type validation; datetime parsing/type validation; timezone-awareness validation; UTC normalization of canonical timestamp fields; original-offset preservation; structural `Decimal` and string validation. **This includes awareness/format validity of `availability_time_utc`/`original_availability_time` when either is supplied (not `None`):** a malformed or naive availability datetime **cannot construct a `SourceCandleInput`** — it fails with a Pydantic `ValidationError` at the `SourceCandleInput` boundary, before any builder is invoked. Such inputs never reach `build_historical_raw_candle`/`build_live_raw_candle` (§29E), and the builders do not — and structurally cannot — convert an impossible `SourceCandleInput` construction into an `IngestionResult`. A future provider adapter may catch and translate a `SourceCandleInput` `ValidationError` into an external rejected-payload result; that adapter is outside this batch's scope.

**Clarification of Decision Group 1's AT-1 language (§28H/§28M):** AT-1's statement that malformed or naive availability evidence is "`REJECTED`" means **structurally rejected at the `SourceCandleInput` boundary** (a construction-time `ValidationError`) — it does **not** mean "the builder returns `IngestionOutcome.REJECTED`." Only the exactly-one-`None` case and the both-valid-but-mismatched-instant case reach the builder as a graceful `IngestionOutcome.REJECTED` result (§29E). This distinction is now stated explicitly to prevent the two mechanisms from being conflated.

`SourceCandleInput` does **not** enforce the cross-field pairing rule (exactly one `None` is invalid) or the instant-correspondence rule between `availability_time_utc` and `original_availability_time` when both are supplied and both are individually well-formed, aware values — those two specific business-level decision-matrix rules are resolved entirely by `raw_candle_builder.py` (§29E), which inspects a structurally-valid `SourceCandleInput` (one that has already survived all type/format/awareness validation) and returns the appropriate `IngestionOutcome` rather than raising an exception. This keeps a single, non-duplicated location (the builder) for the two cross-field availability-evidence decisions that cannot be expressed as a per-field structural constraint, while every per-field structural/format concern — including awareness and well-formedness of the availability fields themselves — belongs exclusively to `SourceCandleInput`.

Model-level cross-field checks (in a `model_validator(mode="after")`, mirroring `RawCandle`'s existing invariants exactly since these do not depend on availability's presence): OHLC bounds (`low <= min(open, close) <= max(open, close) <= high`); `volume`/`volume_kind` pairing; `original_event_time` corresponds to the same instant as `event_time_utc`. The `original_availability_time`/`availability_time_utc` instant-correspondence check is deliberately **not** performed here (see above); it is a builder responsibility, reachable only when both values are individually well-formed and aware.

`SourceCandleInput` has no `to_raw_candle()` method and constructs no `RawCandle`. It is a pure caller-supplied input value.

**No `SourceCandleInput` field has a default value.** All 23 keys must be supplied by the caller on every construction, including both nullable availability keys (`availability_time_utc`, `original_availability_time`), which must be explicitly supplied as either a well-formed aware `datetime` or `None` — never omitted.

### 29C. `results.py` — Exact `IngestionOutcome` and `IngestionResult`

```python
class IngestionOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    INDETERMINATE = "INDETERMINATE"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_REVISION = "CONFLICTING_REVISION"
```

Exactly the 5 values already fixed by §28J. No `NEW_RECORD` member (resolved in §29G).

```python
class IngestionResult(ContractModel):
    outcome: IngestionOutcome
    reason_codes: tuple[str, ...]
    candidate_raw_candle: RawCandle | None
    candidate_normalized_candle: NormalizedCandle | None
    existing_record_id: UUIDv7 | None
```

Reason-code syntax: reuses the identical policy already approved for `ValidationResult` — pattern `^[A-Z][A-Z0-9_]*$`, unique within the tuple, order-preserving. This is the same regex/helper, applied to a distinct field on a distinct model (no shared runtime state with `ValidationResult`).

**Exact enforceable outcome-to-field matrix**, enforced by a `model_validator(mode="after")` (avoids an "everything optional" model; corrects the prior calling-convention-only language identified in the read-only architectural audit — every rule below is a model-enforced invariant, not merely a documented convention):

**`ACCEPTED`:**
- `candidate_raw_candle` is required (not `None`).
- `candidate_normalized_candle` may be `None` or present.
- `existing_record_id` must be `None`.
- `reason_codes` must be empty.
- When `candidate_normalized_candle` is present, its `raw_candle_id` must equal `candidate_raw_candle.record_id` — enforced by the same `model_validator`.

**`REJECTED`:**
- `reason_codes` must contain at least one approved code (§29C's eight-code vocabulary below).
- `candidate_normalized_candle` must be `None`.
- `existing_record_id` must be `None`.
- `candidate_raw_candle` may be `None` or present, depending on which stage rejected the record (`None` if rejected before `RawCandle` construction; present if rejected at a later stage, e.g. normalization).

**`INDETERMINATE`:**
- `reason_codes` must contain at least one approved code.
- `candidate_normalized_candle` must be `None`.
- `existing_record_id` must be `None`.
- `candidate_raw_candle` must be `None` (only reachable before `RawCandle` construction, per AT-1's corrected structural-vs-builder boundary, §29B).

**`EXACT_DUPLICATE`:**
- `candidate_raw_candle` is required (not `None`).
- `candidate_normalized_candle` must be `None` — the result must not release a second accepted `NormalizedCandle`.
- `existing_record_id` is required (not `None`).
- `reason_codes` may be empty (identified via the identity/fingerprint match itself, not a rejection reason).

**`CONFLICTING_REVISION`:**
- `candidate_raw_candle` is required (not `None`).
- `candidate_normalized_candle` must be `None` — no accepted downstream `NormalizedCandle` is exposed; no automatic winner is selected.
- `existing_record_id` is required (not `None`).
- `reason_codes` must include `CONFLICTING_REVISION_DETECTED` (§29C's vocabulary, below — this code belongs to the authoritative Section 29C list; §29G uses it and does not introduce a separate code).

No other field combination is valid; the `model_validator` rejects any `IngestionResult` construction that does not match its outcome's exact rule set above.

`candidate_normalized_candle` is populated only when the result authorizes downstream emission. For `EXACT_DUPLICATE`/`CONFLICTING_REVISION`, a `NormalizedCandle` may have already been constructed earlier in the pipeline (idempotency runs after normalization per §28D's flow), but it is deliberately **not** carried into the result — this prevents any accidental downstream consumption of a candidate that must not be emitted, satisfying §28F/RM-1's "must not be emitted as an accepted downstream `NormalizedCandle`" requirement by construction rather than by caller discipline.

**Approved reason-code vocabulary for this batch — exactly eight codes, closed list:** `AVAILABILITY_TIME_UNAVAILABLE` (both availability values `None`, §29E outcome 1); `AVAILABILITY_TIME_PAIR_INCONSISTENT` (exactly one availability value `None`, §29E outcome 2); `AVAILABILITY_TIME_INVALID` (both availability values are valid, individually well-formed, aware datetimes but do not represent the same instant, §29E outcome 3 — **applies to the valid-aware instant-mismatch case only**; a naive or malformed availability value never reaches this reason code because it never reaches the builder at all, per §29B's corrected structural boundary); `RAW_CANDLE_VALIDATION_FAILED`; `UNSUPPORTED_PROVIDER`; `UNSUPPORTED_PROVIDER_SYMBOL`; `UNSUPPORTED_PROVIDER_TIMEFRAME`; `CONFLICTING_REVISION_DETECTED` (idempotency-stage conflicting-fingerprint detection, §29G — this code is part of this same authoritative list, not a separate addition). **No reason code outside this exact eight-code list may be emitted by this batch.**

### 29D. `source_mapping.py` — Exact FXCM Mapping API

Public API:

```python
FXCM_PROVIDER: str = "FXCM"

class UnsupportedProviderError(ValueError): ...
class UnsupportedProviderSymbolError(ValueError): ...
class UnsupportedProviderTimeframeError(ValueError): ...

def resolve_internal_symbol(provider: str, provider_symbol: str) -> InternalSymbol: ...
def resolve_timeframe(provider: str, provider_timeframe: str) -> Timeframe: ...
```

Symbol registry (provider-symbol → `InternalSymbol`, FXCM only): `"XAUUSD" → InternalSymbol.XAUUSD`, `"EURUSD" → InternalSymbol.EURUSD`, `"GBPUSD" → InternalSymbol.GBPUSD`.

Timeframe registry (provider-timeframe → `Timeframe`, FXCM only, all 8 existing members, verified against `src/btmm_ai_scanner/config/enums.py`, no invented member): `"M1" → Timeframe.M1`, `"M5" → Timeframe.M5`, `"M15" → Timeframe.M15`, `"H1" → Timeframe.H1`, `"H3" → Timeframe.H3`, `"H4" → Timeframe.H4`, `"D1" → Timeframe.D1`, `"W1" → Timeframe.W1`.

`resolve_internal_symbol`/`resolve_timeframe` raise `UnsupportedProviderError` when `provider != FXCM_PROVIDER`; raise `UnsupportedProviderSymbolError`/`UnsupportedProviderTimeframeError` when the provider is `FXCM_PROVIDER` but the symbol/timeframe key is absent from the registry. Lookup is an exact-match `dict` lookup: **case-sensitive, no whitespace trimming, no normalization** — a padded or differently-cased key simply fails to match, raising the appropriate error without any dedicated padding-detection code.

**No TradingView-reference lookup function exists in this module.** The `FXCM:XAUUSD`/`FXCM:EURUSD`/`FXCM:GBPUSD` visual-reference tickers (§28A) remain documentation-only; no code path in the first batch resolves or validates a TradingView ticker string.

### 29E. `raw_candle_builder.py` — Exact Builder Signatures

```python
def build_historical_raw_candle(source_input: SourceCandleInput) -> IngestionResult: ...
def build_live_raw_candle(source_input: SourceCandleInput) -> IngestionResult: ...
```

Both are stateless and delegate to one shared private helper, `_build_raw_candle_from_source_input(source_input: SourceCandleInput) -> IngestionResult`, which contains the entire availability decision matrix and `RawCandle` construction. In this first batch both public functions have **identical behavior** — the separate names exist so that historical and live call sites remain textually distinct and independently traceable in future batches, even though Batch-1 logic does not yet diverge (consistent with §28C's "explicit, stateless entry points" intent, not a claim that behavior differs today).

`processing_time_utc` originates entirely from `SourceCandleInput.processing_time_utc`, supplied by the caller (a fixture in this batch; a future adapter thereafter). **Neither function calls `datetime.now()` or any wall-clock source.** No `Clock` protocol is introduced — the caller-supplied-value pattern already used throughout §28 makes one unnecessary. **The builders do not generate UUIDs, fingerprints, provenance IDs, or version values** — every such value already exists on the caller-supplied `SourceCandleInput` and is copied into the constructed `RawCandle` unchanged.

**Exact outcome mapping — builder availability decisions own only the four cases below** (a structurally-valid `SourceCandleInput`, per §29B's corrected boundary, is a precondition for every case; malformed or naive availability values never reach this table because they never reach the builder):

| # | Condition | Outcome | `candidate_raw_candle` | Reason code |
|---|---|---|---|---|
| 1 | Both availability values are `None` | `INDETERMINATE` | `None` | `AVAILABILITY_TIME_UNAVAILABLE`; no `RawCandle`, no `NormalizedCandle` |
| 2 | Exactly one availability value is `None` | `REJECTED` | `None` | `AVAILABILITY_TIME_PAIR_INCONSISTENT`; no `RawCandle`, no `NormalizedCandle` |
| 3 | Both values are valid, individually well-formed, aware datetimes but do not represent the same instant | `REJECTED` | `None` | `AVAILABILITY_TIME_INVALID`; no `RawCandle`, no `NormalizedCandle` |
| 4 | Both values are valid aware datetimes representing the same instant | Continue `RawCandle` construction | — | — |

A fifth condition applies after case 4 continues: if availability evidence is sufficient but `RawCandle`'s own construction raises `ValidationError` (e.g. an OHLC/volume invariant unrelated to availability), the outcome is `REJECTED`, `candidate_raw_candle=None`, reason code `RAW_CANDLE_VALIDATION_FAILED`. Otherwise, case 4 produces `ACCEPTED` with `candidate_raw_candle` present.

**Expected versus unexpected errors (boundary restated for clarity):** a Pydantic `ValidationError` raised while constructing `SourceCandleInput` occurs entirely before builder invocation and is never caught or translated by the builder — no statement in this section implies malformed or naive `SourceCandleInput` values reach `build_historical_raw_candle`/`build_live_raw_candle`. Expected `RawCandle`-construction validation failures (case 5 above) are converted to a `REJECTED` `IngestionResult`. Unexpected programming errors, invariant bugs, and programmer type violations not represented by the outcome table above (e.g. passing a non-`SourceCandleInput` object, a `TypeError`) may propagate and are expected to trigger a test failure — the builders must not catch `BaseException`, and must not indiscriminately catch every `Exception`, only the specific expected `ValidationError` case named above.

### 29F. `normalization.py` — Exact Normalization Function

```python
def normalize_raw_candle(
    raw_candle: RawCandle,
    *,
    normalized_record_id: UUIDv7,
    normalized_content_fingerprint: SHA256Fingerprint,
    normalized_rule_version: SemVer,
    normalized_contract_version: SemVer,
    normalized_schema_version: SemVer,
    normalized_provenance_id: UUIDv7,
) -> IngestionResult: ...
```

**Corrected normalized-only caller-supplied value boundary (supersedes the prior 2-parameter signature — corrects a gap identified in the read-only architectural audit):** `NormalizedCandle` requires its own `record_id`, `content_fingerprint`, `rule_version`, `contract_version`, `schema_version`, and `provenance_id`, each **independently caller-supplied** via required keyword-only parameters, typed via the existing `UUIDv7`/`SHA256Fingerprint`/`SemVer` annotated types. Rather than introducing a new input model (which would add an 18th file and duplicate `SourceCandleInput`'s shape), all six normalized-only values are simple required keyword-only parameters on `normalize_raw_candle` itself. **All six are caller-supplied; none is generated by this function; none is silently copied from `RawCandle`.** The normalization step may carry its own version and provenance evidence distinct from the raw-record construction step's evidence — normalization is a distinct processing step and its `NormalizedCandle` is not required to inherit its parent `RawCandle`'s version/provenance identity verbatim. No UUID generator exists in this function. No fingerprint calculator exists in this function. No automatic version default exists.

Behavior: resolves `symbol`/`timeframe` via `source_mapping.resolve_internal_symbol(raw_candle.provider, raw_candle.source_symbol)` / `resolve_timeframe(raw_candle.provider, raw_candle.source_timeframe)`; on success, constructs a `NormalizedCandle` preserving `RawCandle`'s provider/source fields and candle values (OHLC, volume, volume_kind, completeness, timestamps), setting `raw_candle_id=raw_candle.record_id` (preserving lineage), `record_id=normalized_record_id`, `content_fingerprint=normalized_content_fingerprint`, `rule_version=normalized_rule_version`, `contract_version=normalized_contract_version`, `schema_version=normalized_schema_version`, `provenance_id=normalized_provenance_id`, and returns `IngestionResult(outcome=ACCEPTED, candidate_raw_candle=raw_candle, candidate_normalized_candle=normalized, existing_record_id=None, reason_codes=())`. On `UnsupportedProviderError`/`UnsupportedProviderSymbolError`/`UnsupportedProviderTimeframeError`, returns `IngestionResult(outcome=REJECTED, candidate_raw_candle=raw_candle, candidate_normalized_candle=None, existing_record_id=None, reason_codes=(the matching reason code,))` — `UNSUPPORTED_PROVIDER`, `UNSUPPORTED_PROVIDER_SYMBOL`, or `UNSUPPORTED_PROVIDER_TIMEFRAME` respectively. `normalize_raw_candle` never mutates its `raw_candle` argument. No idempotency, gap detection, persistence, POI, or BTMM work occurs in this function.

### 29G. `idempotency.py` — Exact Idempotency Service (Resolves the `NEW_RECORD` Gap)

**Resolution of the conceptual gap named in the task (Part 11):** `IngestionOutcome` (§29C) has no `NEW_RECORD` member. **Chosen resolution: a new, non-duplicate, non-conflicting candidate is reported as `ACCEPTED` at the idempotency stage** — not a separate `IdempotencyOutcome` enum. Reasoning: `IngestionOutcome` is deliberately a single, unified vocabulary shared across every stage of the pipeline (§28J's explicit design intent); a record that idempotency finds to be genuinely new *is* exactly what "accepted for downstream use" means at that point in the flow, so reusing `ACCEPTED` avoids a second enum that would only ever mean the same thing under a different name. Introducing `IdempotencyOutcome` would force every downstream consumer to translate between two outcome vocabularies for no behavioral gain.

```python
SourceCandleIdentity = tuple[str, str, str, str, datetime]
```

A type alias (not a new Pydantic model), representing `(provider, source_reference, source_symbol, source_timeframe, event_time_utc)` — kept as a lightweight internal comparison key, not a public contract; not exported from `market_data/__init__.py`.

```python
def evaluate_idempotency(
    candidate_raw_candle: RawCandle,
    candidate_normalized_candle: NormalizedCandle,
    existing_raw_candles: Sequence[RawCandle],
) -> IngestionResult: ...
```

Pure, stateless function: no persistence, no mutation of `existing_raw_candles` or its elements, no hidden global state, no automatic revision winner.

**Exact algorithm and edge-case resolutions (Part 11):**
- Compute the candidate's `SourceCandleIdentity`. Iterate `existing_raw_candles` in the given sequence order (no re-sorting — **stable ordering** is the input order).
- **Empty existing set:** no identity match possible → `ACCEPTED` (new record), `candidate_normalized_candle=candidate_normalized_candle`, `existing_record_id=None`.
- **Existing records with an identity different from the candidate identity are ignored and do not affect the decision** — they are skipped during iteration and never compared by `content_fingerprint`.
- For each existing record sharing the candidate's identity: if `content_fingerprint` matches, it is an exact-match candidate; if it differs, it is a conflicting-match candidate.
- **Multiple exact matches:** the **first** exact match encountered in sequence order is referenced via `existing_record_id`.
- **Exact match and conflicting match both present for the same identity:** `CONFLICTING_REVISION` takes precedence over `EXACT_DUPLICATE` — the presence of any differing-fingerprint record for the same identity is resolved conservatively (quarantine) regardless of an exact match also being present. The conflicting record referenced is the first conflicting match encountered in sequence order.
- **No match at all for the identity:** `ACCEPTED`.
- **Duplicate existing-record IDs within `existing_raw_candles`:** out of scope for this function to detect or repair; it trusts `CandleReadRepository` (§29I) to supply distinct records for a given identity. Not a defended-against input.
- **Candidate's own `record_id` appearing among `existing_raw_candles`:** no special-cased code path; the same identity+fingerprint comparison naturally classifies it (self-comparison yields `EXACT_DUPLICATE` if fingerprints match, `CONFLICTING_REVISION` if they somehow do not).

Outcome-to-field population: `ACCEPTED` → `candidate_raw_candle` and `candidate_normalized_candle` both present, `existing_record_id=None`, `reason_codes=()`. `EXACT_DUPLICATE` → `candidate_raw_candle` present, `candidate_normalized_candle=None`, `existing_record_id` set to the matched record's `record_id`, `reason_codes=()`. `CONFLICTING_REVISION` → `candidate_raw_candle` present, `candidate_normalized_candle=None`, `existing_record_id` set to the conflicting record's `record_id`, `reason_codes=("CONFLICTING_REVISION_DETECTED",)` — this code is part of the single authoritative eight-code reason-code vocabulary already defined in §29C; this file uses that already-approved code and does not introduce a separate or ninth code.

### 29H. `gap_observation.py` — Exact Gap Model and Function

```python
class GapClassification(StrEnum):
    POTENTIAL_GAP = "POTENTIAL_GAP"
```

Exactly one member, per GAP-1 (§28M). No `CONFIRMED_GAP`/`EXPECTED_MARKET_CLOSURE` placeholder is added ahead of a future approved calendar decision.

```python
class GapObservation(ContractModel):
    previous_normalized_candle_id: UUIDv7
    current_normalized_candle_id: UUIDv7
    symbol: InternalSymbol
    timeframe: Timeframe
    previous_event_time_utc: datetime
    current_event_time_utc: datetime
    expected_interval: timedelta
    observed_interval: timedelta
    missing_interval_count: int
    classification: GapClassification
```

```python
def observe_potential_gap(
    previous: NormalizedCandle,
    current: NormalizedCandle,
) -> GapObservation | None: ...
```

**Exact expected interval per `Timeframe` member** (calendar-agnostic elapsed time, deliberately naive around weekends/holidays per GAP-1): `M1` → 1 minute, `M5` → 5 minutes, `M15` → 15 minutes, `H1` → 1 hour, `H3` → 3 hours, `H4` → 4 hours, `D1` → 1 day, `W1` → 7 days.

**Corrected validation order and missing-interval calculation (supersedes the prior truncating formula — corrects an unvalidated-remainder ambiguity identified in the read-only architectural audit).** Let `observed_interval = current.event_time_utc - previous.event_time_utc` and `expected_interval` be the exact approved `timedelta` for the mapped `Timeframe` (table above). Evaluated in this exact order:

1. **Different `symbol` between `previous`/`current`:** raises `ValueError`. No `GapObservation`. A caller supplying candles from different series is a programming error that must surface immediately, not be swallowed.
2. **Different `timeframe` between `previous`/`current`:** raises `ValueError`. No `GapObservation`.
3. **`current.event_time_utc <= previous.event_time_utc`:** raises `ValueError`. No `GapObservation`. This covers both the strictly-out-of-order case and the same-event-time case — the function requires strictly increasing `event_time_utc`; same-instant duplicate handling is entirely `idempotency.py`'s responsibility (§29G), which runs earlier in the pipeline and is never re-implemented here.
4. **`observed_interval == expected_interval`:** returns `None` (no gap — correct consecutive interval).
5. **`observed_interval < expected_interval`** (and not equal, per case 4): raises `ValueError`. No `GapObservation` — an observed interval shorter than the expected interval is malformed input for this comparison, not a gap.
6. **`observed_interval % expected_interval != timedelta(0)`** (irregular, non-integer-multiple spacing): raises `ValueError`. No `GapObservation`. This case is distinctly classified as **irregular interval alignment** — the remainder is never truncated, rounded, or silently discarded.
7. **`observed_interval` is an exact integer multiple of `expected_interval`, greater than 1×** (i.e., passed cases 4–6): `missing_interval_count = observed_interval // expected_interval - 1`; returns a `GapObservation` with `classification=GapClassification.POTENTIAL_GAP`.

**Worked examples:** 1× expected interval → no gap (case 4). 2× expected interval → `missing_interval_count = 1`. 3× expected interval → `missing_interval_count = 2`. 2.5× expected interval → `ValueError`, no observation (case 6 — not an integer multiple).

Every case-7 gap in this batch is `POTENTIAL_GAP` — including gaps caused by weekends — with no special-case classification, per GAP-1; weekends and closures receive no special treatment and are indistinguishable from any other `POTENTIAL_GAP`. The function never fabricates or interpolates a candle, and never performs OHLC or volume interpolation; it only compares two already-constructed `NormalizedCandle` instances.

### 29I. `ports.py` — Exact Protocol Definitions

```python
class RawCandleSink(Protocol):
    def store_raw_candle(self, raw_candle: RawCandle) -> None: ...

class NormalizedCandleSink(Protocol):
    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None: ...

class CandleReadRepository(Protocol):
    def find_raw_candles_by_source_identity(
        self,
        provider: str,
        source_reference: str,
        source_symbol: str,
        source_timeframe: str,
        event_time_utc: datetime,
    ) -> Sequence[RawCandle]: ...

class HistoricalReplaySource(Protocol):
    def replay(self) -> Iterator[NormalizedCandle]: ...
```

**Not `@runtime_checkable`.** No code path in this batch performs an `isinstance()` check against these protocols; static structural typing via mypy is sufficient, consistent with this project's strict-typing-first style. If a future batch needs a runtime `isinstance` check, that is a separate, explicit decision, not assumed here.

`CandleReadRepository` is read-only by design (no `store_*`/mutation method) — it exists purely to supply `existing_raw_candles` to `evaluate_idempotency` (§29G). **`HistoricalReplaySource` performs no wall-clock waiting, sleeping, or live-stream timing** — `replay()` yields already-available `NormalizedCandle` instances deterministically and as fast as the implementation can produce them; it never blocks to simulate real-time playback. No production implementation of any of the four protocols exists in this batch; only local, test-scoped in-memory doubles defined inside `test_ingestion_ports.py` (§29K) may implement them.

### 29J. `__init__.py` — Exact Package Exports

Exactly 20 public exports, grouped by source file in construction order:

```python
__all__ = [
    "SourceCandleInput",
    "IngestionOutcome",
    "IngestionResult",
    "FXCM_PROVIDER",
    "UnsupportedProviderError",
    "UnsupportedProviderSymbolError",
    "UnsupportedProviderTimeframeError",
    "resolve_internal_symbol",
    "resolve_timeframe",
    "build_historical_raw_candle",
    "build_live_raw_candle",
    "normalize_raw_candle",
    "evaluate_idempotency",
    "GapClassification",
    "GapObservation",
    "observe_potential_gap",
    "RawCandleSink",
    "NormalizedCandleSink",
    "CandleReadRepository",
    "HistoricalReplaySource",
]
```

No private helper (`_build_raw_candle_from_source_input`, `SourceCandleIdentity`, `require_*`/`validate_*` shared helpers, etc.) is exported. Maximum export count for this batch is exactly 20 — any addition is a new, separate decision.

### 29K. Exact 57 Test-Function Names (8 Files)

No class-based tests, no dynamically generated tests, no `test_`-prefixed non-test helper. Parametrization is permitted within a named function (counts as one top-level function per AST). No overlap in responsibility between files.

**`tests/unit/test_source_input_and_results.py` (8)** — pure model/enum unit tests, no pipeline execution:
1. `test_source_candle_input_accepts_valid_construction`
2. `test_source_candle_input_requires_exact_field_set`
3. `test_source_candle_input_is_frozen`
4. `test_source_candle_input_rejects_extra_fields`
5. `test_source_candle_input_requires_availability_keys_present`
6. `test_source_candle_input_accepts_both_availability_values_none`
7. `test_source_candle_input_rejects_naive_availability_values`
8. `test_ingestion_outcome_and_result_values_are_exact` (asserts the 5-member enum and exercises `IngestionResult`'s own outcome-field-matrix validator directly, including invalid combinations)

**`tests/unit/test_source_mapping.py` (7):**
1. `test_resolve_internal_symbol_maps_approved_fxcm_symbols`
2. `test_resolve_timeframe_maps_approved_fxcm_timeframes`
3. `test_resolve_internal_symbol_rejects_unsupported_provider`
4. `test_resolve_internal_symbol_rejects_unsupported_symbol`
5. `test_resolve_timeframe_rejects_unsupported_timeframe`
6. `test_source_mapping_is_case_sensitive`
7. `test_source_mapping_does_not_expose_tradingview_lookup`

**`tests/unit/test_raw_candle_builder.py` (8)** — end-to-end availability-decision-matrix coverage via the real builder functions:
1. `test_build_historical_raw_candle_accepts_complete_evidence`
2. `test_build_live_raw_candle_accepts_complete_evidence`
3. `test_raw_candle_builder_returns_indeterminate_for_both_availability_none`
4. `test_raw_candle_builder_returns_rejected_for_one_availability_none`
5. `test_raw_candle_builder_returns_rejected_for_inconsistent_availability_instant`
6. `test_raw_candle_builder_returns_rejected_for_raw_candle_validation_failure`
7. `test_raw_candle_builder_never_mutates_source_input`
8. `test_raw_candle_builder_never_calls_wall_clock`

**`tests/unit/test_normalization.py` (7):**
1. `test_normalize_raw_candle_accepts_valid_raw_candle`
2. `test_normalize_raw_candle_produces_distinct_normalized_record_id`
3. `test_normalize_raw_candle_preserves_raw_candle_lineage`
4. `test_normalize_raw_candle_rejects_unsupported_symbol_mapping`
5. `test_normalize_raw_candle_rejects_unsupported_timeframe_mapping`
6. `test_normalize_raw_candle_never_mutates_raw_candle`
7. `test_pipeline_reuses_caller_supplied_identity_fingerprint_versions_and_provenance_without_generation` (**renamed and broadened — supersedes the prior `test_normalize_raw_candle_reuses_caller_supplied_identity_and_fingerprint`, correcting a missing-coverage finding from the read-only architectural audit**: asserts the raw builder preserves the caller-supplied raw `record_id`, raw `content_fingerprint`, raw `rule_version`, raw `contract_version`, raw `schema_version`, and raw `provenance_id`; asserts normalization preserves the caller-supplied `normalized_record_id`, `normalized_content_fingerprint`, `normalized_rule_version`, `normalized_contract_version`, `normalized_schema_version`, and `normalized_provenance_id`; and asserts no generated replacement value appears anywhere in either output. Broadens rather than removes the prior identity-and-fingerprint assertions.)

**`tests/unit/test_idempotency.py` (8):**
1. `test_evaluate_idempotency_accepts_new_record_with_empty_existing_set`
2. `test_evaluate_idempotency_detects_exact_duplicate`
3. `test_evaluate_idempotency_detects_conflicting_revision`
4. `test_evaluate_idempotency_conflicting_revision_takes_precedence_over_exact_match`
5. `test_evaluate_idempotency_ignores_different_identity_records`
6. `test_evaluate_idempotency_preserves_stable_ordering_of_matches`
7. `test_evaluate_idempotency_does_not_mutate_existing_records`
8. `test_evaluate_idempotency_does_not_select_automatic_revision_winner`

**`tests/unit/test_gap_observation.py` (7):**
1. `test_observe_potential_gap_returns_none_for_correct_consecutive_interval`
2. `test_observe_potential_gap_detects_missing_intervals`
3. `test_observe_potential_gap_rejects_different_symbols`
4. `test_observe_potential_gap_rejects_different_timeframes`
5. `test_gap_observation_rejects_out_of_order_same_time_and_irregular_alignment` (**renamed — supersedes the prior `test_observe_potential_gap_rejects_out_of_order_candles`, broadened to own the full corrected validation order from §29H — correcting an unvalidated-remainder finding from the read-only architectural audit**: parametrized over exactly the required cases — `current.event_time_utc` earlier than `previous.event_time_utc`; `current.event_time_utc` equal to `previous.event_time_utc`; `observed_interval` less than `expected_interval`; a non-integer-multiple interval such as 2.5× `expected_interval` — asserting `ValueError` and no `GapObservation` in every case)
6. `test_observe_potential_gap_computes_expected_interval_per_timeframe`
7. `test_observe_potential_gap_never_fabricates_or_interpolates`

**`tests/unit/test_ingestion_ports.py` (6):**
1. `test_raw_candle_sink_protocol_conformance`
2. `test_normalized_candle_sink_protocol_conformance`
3. `test_candle_read_repository_protocol_conformance`
4. `test_historical_replay_source_protocol_conformance`
5. `test_candle_read_repository_has_no_mutation_method`
6. `test_historical_replay_source_is_deterministic_and_ordered`

**`tests/unit/test_historical_live_separation_and_no_synthetic_fabrication.py` (6):**
1. `test_historical_and_live_builders_produce_identical_results_for_same_input`
2. `test_historical_and_live_builders_do_not_share_mutable_state`
3. `test_historical_builder_supports_deterministic_replay_ordering`
4. `test_live_builder_uses_supplied_processing_time_only`
5. `test_pipeline_never_fabricates_synthetic_candle_values`
6. `test_pipeline_marks_invalid_and_indeterminate_records_as_auditable_not_discarded`

`8+7+8+7+8+7+6+6 = 57`, matching §28K/§28L exactly. "No network/database/parser implementation" is not covered by a dedicated negative test — it is satisfied structurally (no such import exists anywhere in the 9 source files) and is a read-only-audit concern rather than a unit-test concern, consistent with how other explicitly-excluded scope items were handled in Batch 1B-B.

### 29L. Exact Construction Order (Stages A–E)

Identical staging discipline to Batch 1B-B (targeted tests + `ruff format --check` + `ruff check` + `mypy` after each stage; full stop on any failure before proceeding to the next stage). **This stop condition applies independently after each of Stages A, B, C, D, and E** — a failure at any single stage halts progress before that stage's files are considered complete, regardless of whether an earlier stage already passed; passing Stage A does not exempt Stage B (or any later stage) from its own independent stop condition, and so on through Stage E.

**Stage A:** `source_input.py`, `results.py`, `test_source_input_and_results.py`. Run `pytest tests/unit/test_source_input_and_results.py -q`, `ruff format --check src/btmm_ai_scanner/market_data/source_input.py src/btmm_ai_scanner/market_data/results.py tests/unit/test_source_input_and_results.py`, `ruff check` on the same paths, `mypy src/btmm_ai_scanner/market_data/source_input.py src/btmm_ai_scanner/market_data/results.py tests/unit/test_source_input_and_results.py`.

**Stage B:** `source_mapping.py`, `test_source_mapping.py`. Same command shape, scoped to these two paths.

**Stage C:** `raw_candle_builder.py`, `normalization.py`, `test_raw_candle_builder.py`, `test_normalization.py`. Same command shape, scoped to these four paths.

**Stage D:** `idempotency.py`, `gap_observation.py`, `test_idempotency.py`, `test_gap_observation.py`. Same command shape, scoped to these four paths.

**Stage E:** `ports.py`, `__init__.py`, `test_ingestion_ports.py`, `test_historical_live_separation_and_no_synthetic_fabrication.py`. Same command shape, scoped to these four paths, plus the full-package `__all__`-export verification (§29J).

After Stage E, run the full quality-gate sequence (§29M) across the whole repository, not just `market_data/`.

### 29M. Baseline Policy, Quality Gates, Stop Conditions, Rollback Boundary

**Baseline policy:** unchanged from the execution-captured baseline policy established in Baseline Correction 6B (§26). No commit hash is hard-coded in this document. At implementation time, the clean synchronized HEAD immediately before the first change is captured and becomes both the baseline and the rollback target; it is reported in the implementation completion report, not recorded here.

**Implementation-preflight verification checklist** (must all hold before the first edit): branch `main`; working tree clean; nothing staged; `HEAD == origin/main`; Python 3.12.13; uv 0.11.30; Pydantic `>=2.13.4,<2.14` (unchanged); `uv lock --check` passes; existing full suite collects and passes exactly 221 tests; the original Batch-1B-A baseline files alone collect and pass exactly 34 tests; existing Batch 1B-B top-level test functions total exactly 132 (verified via inline AST parsing, never a temporary script file); `src/btmm_ai_scanner/market_data/` does not exist; no pending diff on `pyproject.toml`/`uv.lock`.

**Final quality gates** (after Stage E, full repository scope): `uv lock --check`; `ruff format --check .`; `ruff check .`; `mypy src tests`; `pytest -q`; `pytest -q` restricted to the two original Batch-1B-A baseline test files (must still show exactly 34 passed). Strict inline AST verification (no temporary script file) must show exactly 57 new top-level test functions across the 8 new test files, and exactly `132 + 57 = 189` combined top-level test functions across all Batch 1B-B + Batch 1B-C-Batch-1 test files. Exact 17-path verification (no 18th path, no fewer than 17). The `market_data/__init__.py` export list must match §29J exactly (20 names, exact order). The final collected pytest case total (which may exceed 189 once parametrized cases are counted) is reported, not required to equal an exact pre-fixed number. **No documentation file may change during implementation. No private-reference file may change. No temporary verification file may be created** — the same disclosed Batch 1B-B `scratch_ast_check.py` deviation (§27I) must not recur; AST verification is performed inline, never via a written-then-deleted script file.

**Mandatory stop conditions** (any one halts implementation immediately, before staging, with the blocker reported): any quality gate above fails; the AST-verified new-test-function count is not exactly 57; the combined total is not exactly 189; an 18th changed path appears; `pyproject.toml`/`uv.lock` show any diff; HEAD moves unexpectedly after baseline capture; any Batch 1B-A/1B-B file requires modification; any attempt to implement POI, BTMM, indicator, alert, replay-engine, backtesting, or robot logic is implied by the work; any ambiguity is discovered in this specification that cannot be resolved by re-reading §29 alone. On any stop: no `git add`, `commit`, `push`, `reset`, `clean`, or `checkout` — the diff is preserved as-is and the exact blocker is reported.

**Rollback boundary:** never automatic. If separately authorized after a stop, rollback affects only the 17 paths named in §29A — never `pyproject.toml`/`uv.lock` (unmodified by this batch), never any Batch 1B-A/1B-B path, never `git reset --hard`, `git clean`, a force checkout, or any history rewrite. A targeted revert/removal of only the 17 new/modified paths is the only permitted rollback shape.

### 29N. Consequences for `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md`

This decision group adds exactly 17 new rows to that document's master file inventory (Section 9), bringing the total from 52 to 69 — see that document's own Section 34 for the added rows. This is a deliberate departure from §28K/§33 of the scaffold-plan document, which explicitly kept the inventory untouched pending this decision group; the inventory addition itself does not constitute implementation and does not change any status field beyond `AUTHOR-APPROVED SCOPE` / `NOT YET IMPLEMENTED` / `NOT PRODUCTION-APPROVED` for each new row.

**No settled Phase 1B-C Decision Group 1 decision (§28) is reopened by this section. This section defines implementation controls only; it does not itself authorize implementation.**

### 29O. Author Approval Record

The author explicitly approved Phase 1B-C Decision Group 2 in full, including every correction applied during the two-round read-only architectural audit and correction cycle (§29B–§29N, corrected). **No further architecture correction is required before implementation.** The final read-only architectural audit verdict was: **A. PASS — READY FOR AUTHOR APPROVAL.** The audit found **no blocking finding**. The audit found **no non-blocking finding**.

This approval authorizes only the exact controlled first implementation batch named in §29A (17 paths: 9 new source files under `src/btmm_ai_scanner/market_data/`, 8 new test files under `tests/unit/`). **This approval does not authorize production use. This approval does not authorize any change outside the exact 17-path scope named in §29A. Implementation has not started.**

## 30. Phase 1B-C Implementation Completion and Closure

**Phase 1B-C Market-Data Pipeline Foundation: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

Decision Group 1 (§28) and Decision Group 2 (§29) were implemented exactly as approved. Neither decision group is "not yet implemented," "awaiting implementation," "awaiting coding," or "pending implementation authorization" — both are now implemented through the controlled Phase 1B-C-MD implementation batch, and remain `AUTHOR-APPROVED` as architecture/implementation-control decisions independent of this closure record.

### 30A. Implementation Record

- **Implementation commit:** `d328776abb5a2c1f42e185b9bc80f0e5a371897e` — "Implement Phase 1B-C market-data pipeline foundation".
- **Push:** succeeded to `origin/main`; local `HEAD` equals `origin/main` at this commit.
- **Exact 17 added paths, every status `A`:** 9 new source files under `src/btmm_ai_scanner/market_data/` (`__init__.py`, `source_input.py`, `source_mapping.py`, `results.py`, `raw_candle_builder.py`, `normalization.py`, `idempotency.py`, `gap_observation.py`, `ports.py`) and 8 new test files under `tests/unit/` (`test_source_input_and_results.py`, `test_source_mapping.py`, `test_raw_candle_builder.py`, `test_normalization.py`, `test_idempotency.py`, `test_gap_observation.py`, `test_ingestion_ports.py`, `test_historical_live_separation_and_no_synthetic_fabrication.py`) — matching §29A exactly, no eighteenth path.
- **Insertions/deletions:** 2276 insertions(+), 0 deletions(-).
- **No existing tracked file was modified.** No `pyproject.toml`/`uv.lock` change. No documentation file included in this commit. No private-reference file changed.

### 30B. Execution Baseline Record

- **Execution-captured baseline:** `1a439f3a1b4b4f6189ec4c209362f5d592910160`.
- **Execution rollback target:** `1a439f3a1b4b4f6189ec4c209362f5d592910160` (identical to the baseline, per the execution-captured baseline policy, §26).
- **Implementation commit:** `d328776abb5a2c1f42e185b9bc80f0e5a371897e`.
- `HEAD` remained at the execution-captured baseline throughout implementation and every subsequent audit/correction/staging review — the implementation was committed only after the controlled audit, correction, and staging-review sequence (§30D) passed in full. **Rollback is not automatic.** Any future rollback remains separately authorized and scoped only to this exact implementation commit or its 17 paths — never to `pyproject.toml`/`uv.lock`, never to any Batch 1B-A/1B-B path, never via `git reset --hard`, `git clean`, a force checkout, or history rewrite.

### 30C. Final Verification Record

**Verified environment:** Python `3.12.13`; `uv` `0.11.30`; Pydantic `2.13.4` (unchanged, within the approved `>=2.13.4,<2.14` range).

**Pre-implementation baseline:** full suite 221 passed; original baseline suite (`test_import_smoke.py` + `test_config_precedence.py`) 34 passed; existing Batch 1B-B top-level test functions 132.

**Final post-implementation verification:** full suite **281 passed**; original baseline suite **34 passed**; corrected targeted suite (`test_source_mapping.py` + `test_source_input_and_results.py`) **15 passed**; new collected test cases **60** (57 top-level functions, one parametrized ×4 replacing 1); new top-level test functions **57**; combined top-level test functions **189** (132 + 57); Ruff format — passed; Ruff lint — passed; mypy — passed; `uv lock --check` — passed; no unexpected warning.

### 30D. Audit History

1. Initial implementation completed inside exactly the approved 17 paths.
2. Initial read-only architectural audit verdict: **C. CORRECTION REQUIRED BEFORE STAGING.**
3. Three blocking findings were corrected, entirely within the approved 17-path boundary:
   - `source_mapping.py`'s FXCM registries changed from plain mutable `dict` objects to `MappingProxyType`-backed immutable mappings.
   - `test_source_input_and_results.py`'s naive-timestamp test coverage broadened from 2 to all 5 applicable fields (`event_time_utc`, `availability_time_utc`, `processing_time_utc`, `original_event_time`, `original_availability_time`).
   - `test_source_input_and_results.py`'s valid-construction test extended with genuine non-UTC (UTC+02:00) canonical-normalization and original-offset-preservation coverage.
4. Final correction audit verdict: **A. PASS — READY FOR STAGING REVIEW.**
5. Staged-diff review verdict: **A. PASS — READY FOR COMMIT REVIEW.**
6. No blocking or non-blocking finding remained at commit authorization.
7. Exactly 17 files were staged (all status `A`) and committed as `d328776abb5a2c1f42e185b9bc80f0e5a371897e`.
8. Post-commit quality gates passed in full (§30C).

**No implementation-policy deviation occurred. No procedural deviation occurred** — every correction stayed inside the approved 17-path scope; no temporary or generated verification file was created at any point in the implementation, audit, correction, or staging sequence.

### 30E. Production and Scope Boundary (Unchanged)

**This closure does not authorize production use, live trading, an indicator, a robot, provider networking, or a persistence backend.** No network adapter, persistence implementation, POI detector, BTMM detector, indicator, alert, backtester, or robot was implemented in this batch. Phase 1B-C is **closed** at the market-data-pipeline-foundation level only — it remains `NOT PRODUCTION-APPROVED`.

## 31. Phase 1B-E Decision Group 1 — Reconciliation with the Completed Market-Data Foundation and Exact Implementation Controls

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

This decision group does not implement any code, test, or dependency change. It exists to (1) reconcile Batch 1B-E's long-standing, policy-level-approved scope (Section 9, rows 44–50 of `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md`) with the market-data pipeline foundation implemented and closed under Phase 1B-C (§28–§30), and (2) define exact implementation controls for `ingestion/requests.py`, `ingestion/results.py`, `ingestion/port.py`, `ingestion/offline_file_source.py`, and `ingestion/__init__.py`, precise enough to implement without further interpretation.

### 31A. Why Reconciliation Is Needed

Batch 1B-E was scoped (Section 6 Group 7, Section 9 rows 44–50) before the market-data pipeline foundation existed. At that time, "provider-neutral ingestion request/result shape" had no sibling contract to be distinguished from. Phase 1B-C-MD has since implemented and closed `market_data.SourceCandleInput` (23-field candle observation contract) and `market_data.IngestionResult` (5-outcome, 8-reason-code pipeline decision contract). Both are now real, `AUTHOR-APPROVED`, `IMPLEMENTED`, `CLOSED` artifacts. Without an explicit reconciliation, `ingestion/requests.py` and `ingestion/results.py` could easily be (mis)implemented as near-duplicates of `SourceCandleInput`/`IngestionResult`, which would violate the layering already established by Phase 1B-C and would create two competing sources of truth for the same concepts. This decision group closes that gap before any ingestion code is written.

### 31B. Architectural Recommendation — Option B: Distinct Source-Adapter Control Contracts

**Recommended and adopted for drafting purposes: ingestion-layer contracts remain structurally and semantically distinct from market-data-pipeline contracts.** `ingestion/` describes *how a candidate set of candle observations was acquired from a source*; `market_data/` describes *what those observations mean once acquired* (raw candle construction, normalization, idempotency, gap observation). Neither layer reaches into the other's outcome vocabulary, field set, or state machine.

**Exact boundary flow:**

```
Provider or deterministic source
    → MarketDataSourcePort.acquire(SourceAcquisitionRequest)
    → SourceAcquisitionResult (source-level outcome + zero or more SourceCandleInput records)
    → Phase 1B-C market-data pipeline (build_historical_raw_candle / build_live_raw_candle, normalize_raw_candle, evaluate_idempotency, observe_potential_gap)
    → RawCandle / NormalizedCandle / market_data.IngestionResult
```

`ingestion/` never constructs a `RawCandle`, a `NormalizedCandle`, or a `market_data.IngestionResult`. It produces `SourceCandleInput` records — already-existing Phase 1B-C-MD contracts — and hands them to the market-data pipeline, which alone decides acceptance, rejection, duplication, or gaps. `ingestion/` owns exactly one question: *did the source acquisition itself succeed, and if so, what candidate observations did it hand back?* It does not own or duplicate any question the market-data pipeline already answers.

**Rejected alternative (Option A — unify the request/result shapes with `SourceCandleInput`/`IngestionResult`):** rejected because it would collapse two distinct concerns (source-level acquisition success/failure vs. pipeline-level candle-observation decisions) into one contract, forcing `SourceCandleInput` to grow acquisition-only fields it does not need (e.g., an unsupported-request reason) and forcing `IngestionResult`'s closed 5-outcome/8-reason-code vocabulary to either grow source-acquisition outcomes it was never designed for or be reused inconsistently. Option A would also make it impossible to represent "the source call itself failed, before any candle was ever seen" without inventing a placeholder `SourceCandleInput`, which contradicts the field-level strictness already established for that contract.

### 31C. Batch 1B-E Inventory — Preserved Exactly, Wording Corrected Across Two Passes

The exact existing 7-row Batch 1B-E inventory (Section 9 rows 44–50) is preserved throughout — **no row was added, removed, renamed, or renumbered, in either the initial reconciliation draft or the subsequent audit-correction pass.** The initial reconciliation draft of this decision group preserved all 7 rows as-is and corrected only row 48's descriptive wording (below). A subsequent read-only architectural audit of that draft found the remaining dependency wording stale relative to the adopted architecture; the audit-correction pass that followed updated that wording in place, without changing any row's identity, order, or count. **The complete, current set of wording corrections against the pre-existing inventory is:**

- **Row 45 (`ingestion/port.py`):** "Direct dependencies" corrected from the stale `contracts/raw_candle.py` (incompatible with §31F's `RawCandle`-free signature) to `ingestion/requests.py`, `ingestion/results.py`, `typing.Protocol`.
- **Row 47 (`ingestion/results.py`):** "Direct dependencies" corrected from `contracts/types.py` alone to `contracts/types.py` (for `ContractModel`) **and** `market_data/source_input.py` (for `SourceCandleInput`).
- **Row 48 (`ingestion/offline_file_source.py`):** responsibility wording corrected from an implied real-file-reading description ("Reads a fixed local file only, no network call") to the deterministic fixture-catalogue behavior adopted in §31F, and its "Direct dependencies" completed to reflect that design (§31F/§31G's full type surface — see the file-scope document's row 48 for the exact list).
- **Section 14's Batch 1B-E summary row:** dependency wording corrected from "1B-B (contracts)" alone to "Batch 1B-B (`contracts/`) and completed Phase `1B-C-MD` (specifically `market_data/source_input.py`'s `SourceCandleInput`)," since `results.py` now carries a tuple of `SourceCandleInput`.

These are wording-only corrections to existing rows. **No row was added. No row was removed. No row was renamed. No row was renumbered. Creation order (44–50) is unchanged. Batch 1B-E remains exactly 7 rows. The total master inventory remains exactly 69 rows.** This is consistent with the precedent established in Phase 1B-C Decision Group 2 (§29's corrections to Section 9 row descriptions without changing row identity or count). Full detail of every corrected cell: `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 9 (rows 45, 47, 48), Section 14 (Batch 1B-E summary row), and Section 36 (which records both the initial reconciliation and the subsequent audit-correction pass as two clearly separated paragraphs).

### 31D. Exact `ingestion/requests.py` Contract

**Model name: `SourceAcquisitionRequest`.** A `ContractModel` (frozen, strict, matching the project-wide contract base). Exactly 4 fields, no defaults:

| Field | Type | Meaning |
|---|---|---|
| `provider` | `str` (nonblank, stripped) | The underlying candle-data provider the requested observations represent — e.g. `"FXCM"`. **Never** the adapter/stub concept (`OFFLINE_FILE` is not a valid example value for this field — see the Provider-Versus-Adapter Identity subsection immediately below). |
| `source_reference` | `str` (nonblank, stripped) | A stable, source-defined reference for the data set (e.g. a fixture catalogue key, a provider feed identifier) — opaque to the port itself. |
| `source_symbol` | `str` (nonblank, stripped) | The symbol exactly as the source names it (pre-mapping — never `InternalSymbol`). |
| `source_timeframe` | `str` (nonblank, stripped) | The timeframe exactly as the source names it (pre-mapping — never `Timeframe`). |

**Rationale for exactly these 4 fields:** they describe acquisition *intent* only — which provider, which reference, which symbol/timeframe as the source names them. This is the smallest field set that lets `MarketDataSourcePort.acquire()` be dispatched deterministically. Reusing the `provider`/`source_symbol`/`source_timeframe` names already established by `SourceCandleInput` is a deliberate naming-consistency choice (the same real-world dimension should have the same field name everywhere in the codebase) — it is not the prohibited duplication, because the request carries none of `SourceCandleInput`'s remaining 19 fields (no OHLC, no volume, no timestamps, no availability pairing, no Decimal price fields).

**Explicitly prohibited fields on `SourceAcquisitionRequest`:** `open`/`high`/`low`/`close`/`volume` (or any OHLC field under any name); `event_time_utc`, `availability_time_utc`, `processing_time_utc`, `original_event_time`, `original_availability_time` (or any timestamp field under any name); `RawCandle`, `NormalizedCandle`, `IngestionResult`, `SourceCandleInput` (no nested candle/result types); any POI or BTMM field; any auto-generated identity, fingerprint, or version field; any provider-specific alias field; any retrieval-mode/source-mode discriminator (`HISTORICAL_BATCH`/`POLLING`/`STREAMING` remain not-yet-authorized per Decision Group 7 — this request shape must not smuggle one in).

No defaults. No caller-optional fields. No arbitrary dict/kwargs payload.

**Correction — Provider Versus Adapter Identity (resolves the audit's Finding 1).** `provider` names the real underlying candle-data provider the observations are attributed to (e.g. `"FXCM"`). It never names which `MarketDataSourcePort` *implementation* served the request. Concretely:

- `OfflineFileSource` is an adapter *implementation* of `MarketDataSourcePort` — not a provider identity. It is selected by the caller choosing which `MarketDataSourcePort` object to construct/call, never by any value placed in `request.provider`.
- A `SourceAcquisitionRequest(provider="FXCM", ...)` may legitimately be served by `OfflineFileSource` — e.g. in a test that stubs FXCM-attributed fixtures without any real FXCM network call.
- `OfflineFileSource` must never rewrite `request.provider`, and must never rewrite `.provider` on any `SourceCandleInput` it returns. Every returned `SourceCandleInput.provider` retains exactly the provider identity the fixture author supplied (e.g. `"FXCM"`) — it is never replaced with `"OFFLINE_FILE"` merely because `OfflineFileSource` happened to serve the request.
- No separate adapter-mode/source-mode field is introduced in this batch (consistent with §31D's existing prohibition on a retrieval-mode discriminator). Adapter selection is a caller-side concern (which `MarketDataSourcePort` object is constructed and called), entirely outside the `SourceAcquisitionRequest`/`SourceAcquisitionResult` contracts.

**Correction — Exact String-Matching Policy (resolves the audit's Finding 3).** All 4 fields are strict `str` values. Leading and trailing whitespace is removed during `SourceAcquisitionRequest` construction (the shared nonblank-stripped-text validator already used throughout this codebase); the stored value must be non-empty after that stripping. Beyond whitespace-stripping, **no other normalization occurs**: matching (both `SourceAcquisitionRequest` value-equality/hashing and `OfflineFileSource`'s catalogue lookup, §31F) uses the stored values exactly, is **case-sensitive**, and applies no `.upper()`, `.lower()`, or `.casefold()` conversion. Consequently `"FXCM"` and `"fxcm"` are different values, `"XAUUSD"` and `"xauusd"` are different values, and an input of `" FXCM "` is stored as `"FXCM"` before any equality check or catalogue lookup. **This request-contract matching policy is independent of, and must not be conflated with, `market_data.source_mapping`'s FXCM symbol/timeframe resolver policy** (§29/§28: also case-sensitive and exact-match, but a separate, already-implemented mechanism operating on already-mapped values downstream of this request contract).

### 31E. Exact `ingestion/results.py` Contract

**Outcome enum name: `SourceAcquisitionOutcome`** (`StrEnum`), exactly 3 members, closed vocabulary, distinct from and non-overlapping with `market_data.IngestionOutcome`'s 5 members:

- `SUCCEEDED` — the source adapter successfully handled the request; it may return zero or more `SourceCandleInput` records (an empty tuple is still `SUCCEEDED` — a source legitimately having nothing new to report is not a failure).
- `UNSUPPORTED` — the adapter cannot serve this exact request at all (e.g. an unrecognized provider, source reference, source symbol, or source timeframe for that adapter).
- `FAILED` — the adapter recognizes and supports the request's *category*, but source acquisition fails for a deterministic, source-level reason (e.g. a future networked adapter's upstream call deterministically errors). **`FAILED` is reserved for future adapters that can genuinely experience acquisition failures; it is never produced by an invalid `SourceAcquisitionRequest`,** because a malformed or internally inconsistent request already fails `SourceAcquisitionRequest` construction itself (a `ValidationError`, per §31D) — it never reaches `acquire()` in the first place, so "malformed request" is not and cannot be a `FAILED` trigger.

**Result model name: `SourceAcquisitionResult`.** A `ContractModel` — **frozen, strict, extra-forbid, and default-validating**, exactly like `SourceAcquisitionRequest` and every other contract model in this codebase (no field permits an out-of-range or non-finite value where such a constraint would apply). Exactly 3 fields, in this fixed order:

| Field | Type | Meaning |
|---|---|---|
| `outcome` | `SourceAcquisitionOutcome` | The source-level acquisition outcome. |
| `source_candle_inputs` | `tuple[SourceCandleInput, ...]` | Immutable tuple of candidate observations handed to the market-data pipeline. |
| `reason_codes` | `tuple[str, ...]` | Source-level reason codes, syntax `^[A-Z][A-Z0-9_]*$` (same syntax convention as `ValidationResult`/`market_data.IngestionResult`, own closed vocabulary — §31E continues below). |

**Closed source-level reason-code vocabulary — exactly 2 codes, never reused from `market_data`'s 8-code vocabulary:**

- `SOURCE_REQUEST_UNSUPPORTED`
- `SOURCE_ACQUISITION_FAILED`

**Per-outcome invariant matrix, enforced by a `model_validator(mode="after")`:**

| Outcome | `source_candle_inputs` | `reason_codes` |
|---|---|---|
| `SUCCEEDED` | may be empty or non-empty | must be empty |
| `UNSUPPORTED` | must be empty | must equal `("SOURCE_REQUEST_UNSUPPORTED",)` |
| `FAILED` | must be empty | must equal `("SOURCE_ACQUISITION_FAILED",)` |

This makes "successful empty acquisition" (`SUCCEEDED` with an empty tuple) and "failure" (`UNSUPPORTED`/`FAILED`, always empty) structurally distinct — a caller can never confuse the two, and the model itself rejects any attempt to attach candle records to a non-`SUCCEEDED` outcome or to omit the mandated reason code from a failure outcome.

**Explicitly prohibited fields on `SourceAcquisitionResult`:** `candidate_raw_candle`, `candidate_normalized_candle`, `existing_record_id` (these belong exclusively to `market_data.IngestionResult`); any duplicate/gap/normalization decision field; any POI or BTMM field; `adapter_version` or any other free-form version/config field not already justified by an approved contract (the Section 9 row-47 note mentioning "`adapter_version`, etc." is not adopted — no version-reference field is added here; if a future batch needs one, it must be separately proposed and approved).

### 31F. Exact `MarketDataSourcePort` Protocol and Resolution of the `OFFLINE_FILE` Contradiction

**Protocol, `ingestion/port.py`:**

```python
class MarketDataSourcePort(Protocol):
    def acquire(self, request: SourceAcquisitionRequest) -> SourceAcquisitionResult: ...
```

- Synchronous (matches every existing port/protocol in this codebase — `market_data.ports` included; nothing in the authoritative roadmap calls for async).
- Provider-neutral: no networking type, no file-handle type, no database/connection type, no `RawCandle`/`NormalizedCandle` type anywhere in the signature.
- No implementation and no mutable state on the Protocol itself (matches the `market_data.ports` precedent of 4 non-`@runtime_checkable` Protocols).
- **Not `@runtime_checkable`**, for the same reason already established for `market_data.ports`: structural conformance is verified by static typing and by direct construction in tests, not by `isinstance` checks at runtime — no justification exists here to depart from that precedent.
- One call, one result: a single `acquire()` call returns a single `SourceAcquisitionResult`, whose `source_candle_inputs` tuple may itself hold zero, one, or many `SourceCandleInput` records. The port does not return an iterator or a stream — that shape is deferred to a `HistoricalReplaySource`-style abstraction if and when batch/streaming retrieval is separately authorized.

**Resolving the `OFFLINE_FILE` contradiction — reported, not silently forced.** The existing Section 9 row 48 and the Section-14-adjacent narrative (line 772) both currently read: *"Reads a fixed local file only, no network call"* / *"reads one fixed local file, no network access, no credential."* Read literally, this describes genuine file I/O (an `open()` call against a real path). That is **incompatible** with the architecture this decision group adopts for the first implementation batch, which requires `OFFLINE_FILE`'s concrete implementation to be a **pure deterministic contract stub**:

- **Class name: `OfflineFileSource`**, implementing `MarketDataSourcePort`.
- Constructed with a caller-supplied `Mapping[SourceAcquisitionRequest, tuple[SourceCandleInput, ...]]`. **Correction — defensive-copy plus `MappingProxyType` (resolves the audit's non-blocking catalogue-mutation gap):** the constructor copies the caller's mapping into a new internal `dict`, then wraps that copy in `types.MappingProxyType` before storing it as the instance's sole catalogue reference; no separately named mutable backing dictionary is retained, and the catalogue is never exposed through any public attribute or method. This guarantees both that caller-side mutation of the original mapping after construction cannot affect behavior, and that the instance's own catalogue cannot be mutated after construction (matching the immutability discipline already established for `source_mapping.py`'s module-level registries, applied here at the instance level).
- `acquire()` performs a dictionary lookup keyed by the exact `SourceAcquisitionRequest` value (frozen `ContractModel`s are value-hashable, and matching follows §31D's case-sensitive, no-normalization policy):
  - **Known request mapped to a non-empty tuple:** returns `SUCCEEDED` with that exact `SourceCandleInput` tuple, unchanged and in catalogue order — the objects are reused, never regenerated.
  - **Known request mapped to an empty tuple:** returns `SUCCEEDED` with an empty tuple (a deliberately documented empty-success fixture, distinct from "unknown").
  - **Unknown request (absent from the catalogue):** returns `UNSUPPORTED` with `reason_codes=("SOURCE_REQUEST_UNSUPPORTED",)`.
  - **`OfflineFileSource` emits only `SUCCEEDED` or `UNSUPPORTED` in this batch — it never emits `FAILED`.** No magic failure key, injected exception text, or artificial failure fixture is introduced to manufacture a `FAILED` result. `SOURCE_ACQUISITION_FAILED` remains defined in the general `SourceAcquisitionResult` contract (§31E) solely for future adapters capable of a genuine, deterministic source-level failure (e.g. a networked adapter); it is simply not reachable through `OfflineFileSource`.
- **Does not call `open()`. Does not read, write, or create any file. Does not perform filesystem discovery, path resolution, CSV/JSON/JSONL/Parquet parsing, or any I/O of any kind.** It never mutates the fixture catalogue, the request, or any returned `SourceCandleInput`. Repeated calls with the same request are guaranteed to return an equal result every time.

**This is a genuine, reportable contradiction against the exact existing inventory wording, not a matter of interpretation.** The resolution adopted here **narrows** the original Group 7 intent ("reads one fixed local file") to "receives caller-supplied immutable fixtures; performs no real file I/O in this first batch." The reason: committing the first `OFFLINE_FILE` implementation to real file parsing would require deciding a fixture file format (CSV vs. JSONL vs. Parquet), a discovery/path-resolution policy, and file-not-found/malformed-file error handling — none of which is scoped, approved, or necessary to prove out the port/request/result contracts. **Real file parsing is deferred to a separately proposed and approved future adapter batch** — the `OfflineFileSource` name is preserved so that a later batch can extend or replace its internals without renaming the class or the row. Per §31C, row 48's description text is corrected to state this narrowed, stub-only meaning; the row's identity, path, and count are unchanged.

### 31G. Exact `ingestion/__init__.py` Exports

Exactly 5 exports, in this fixed order, each annotated below with its defining file — no full `market_data` re-export, no fixture registry, no module-level mutable state, no sixth export:

| # | Export | Defining file |
|---|---|---|
| 1 | `SourceAcquisitionRequest` | `ingestion/requests.py` |
| 2 | `SourceAcquisitionOutcome` | `ingestion/results.py` |
| 3 | `SourceAcquisitionResult` | `ingestion/results.py` |
| 4 | `MarketDataSourcePort` | `ingestion/port.py` |
| 5 | `OfflineFileSource` | `ingestion/offline_file_source.py` |

```python
__all__ = [
    "SourceAcquisitionRequest",
    "SourceAcquisitionOutcome",
    "SourceAcquisitionResult",
    "MarketDataSourcePort",
    "OfflineFileSource",
]
```

### 31H. Exact Test Coverage

**`tests/unit/test_ingestion_port_contract.py` — exactly 8 top-level test functions:**

1. `test_source_acquisition_request_accepts_valid_construction` — **owns the string-matching-policy assertions (resolves the audit's Finding 3):** in addition to valid construction, this test asserts that a padded input (e.g. `" FXCM "`) is stored stripped as `"FXCM"`; that a lowercase value (e.g. `"fxcm"`) is a distinct stored value from its uppercase form (`"FXCM"`) and therefore compares unequal; that `SourceAcquisitionRequest` instances differing only by case are unequal (and thus resolve to different `OfflineFileSource` catalogue entries); and that no `.upper()`/`.lower()`/`.casefold()` conversion is applied anywhere in construction or equality.
2. `test_source_acquisition_request_is_frozen`
3. `test_source_acquisition_request_rejects_extra_fields_and_candle_content`
4. `test_source_acquisition_result_enforces_outcome_matrix`
5. `test_source_acquisition_result_succeeded_may_carry_multiple_source_candle_inputs`
6. `test_source_acquisition_result_distinguishes_empty_success_from_failure`
7. `test_source_acquisition_outcome_and_reason_codes_do_not_duplicate_market_data_vocabulary`
8. `test_market_data_source_port_protocol_conformance`

**`tests/unit/test_offline_file_stub.py` — exactly 8 top-level test functions:**

1. `test_offline_file_source_returns_fixture_for_known_request`
2. `test_offline_file_source_returns_unsupported_for_unknown_request`
3. `test_offline_file_source_is_deterministic_across_repeated_calls`
4. `test_offline_file_source_preserves_source_candle_input_ordering`
5. `test_offline_file_source_never_generates_replacement_values`
6. `test_offline_file_source_never_mutates_fixtures_or_request`
7. `test_offline_file_source_performs_no_file_or_network_access`
8. `test_offline_file_source_never_constructs_raw_or_normalized_candles`

**Total new top-level test functions: 16** (combined with the existing 189: **205**). No `test_`-prefixed non-test helper. No class-based or dynamically generated test. Parametrization, where used (e.g. within test 2 of `test_offline_file_stub.py`, covering unknown-provider/unknown-symbol/unknown-timeframe as distinct parametrized cases), replaces what would otherwise be separate top-level functions and must be called out explicitly in the implementation report, exactly as done for Phase 1B-C-MD (§30C's "60 collected, 57 top-level" precedent).

**Required coverage, mapped to the above:** strict immutable construction of both contracts, including the exact string-stripping/case-sensitive-matching policy of §31D (1, 2 in file 1); structural exclusion of candle/OHLC/timestamp fields from the request and of `RawCandle`/`NormalizedCandle`/pipeline-decision fields from the result (3, 4); the empty-success-vs-failure distinction (6); non-collision with `market_data.IngestionOutcome`/reason-code vocabulary (7); Protocol shape, non-runtime-checkability, and absence of concrete state (8); deterministic, side-effect-free, non-mutating, non-generating, no-I/O behavior of `OfflineFileSource`, including that it emits only `SUCCEEDED`/`UNSUPPORTED` and never `FAILED` (all 8 in file 2).

### 31I. Explicit Exclusions (Unchanged Scope Boundary)

This decision group and the batch it authorizes for future implementation exclude, without exception: any FXCM REST/WebSocket adapter; any TradingView scraping or adapter; any CSV/JSON/JSONL/Parquet parsing; any filesystem discovery or path resolution; any persistence implementation; any concrete `CandleReadRepository` or `HistoricalReplaySource`; any ingestion orchestration beyond a single `acquire()` call; `RawCandle` construction, normalization, idempotency evaluation, or gap observation (these remain exclusively Phase 1B-C-MD's responsibility, invoked by a future caller *after* `ingestion/` hands back `SourceCandleInput` records); validation/eligibility orchestration; POI, market-structure, or BTMM detection; indicators; alerts; backtesting; paper trading; or robot/live-execution of any kind.

### 31J. Deferred Note — Validation-Layer Overlap (Acknowledged, Not Resolved)

A second, unrelated architectural overlap exists between the older, still-unimplemented `validation/` batch (Section 14's distinct "Batch 1B-C," 12 files, e.g. `validation/duplicates.py`, `validation/gaps.py`) and the now-implemented `market_data/idempotency.py`/`market_data/gap_observation.py`. Both pairs address conceptually adjacent problems (duplicate detection, gap detection) at what may turn out to be redundant layers. **This decision group explicitly does not resolve that overlap.** It is noted here only so it is not forgotten: the `validation/` batch must not be authorized for implementation until its relationship to `market_data.idempotency`/`market_data.gap_observation` is separately reconciled, in its own decision group, with its own architect recommendation. No row in the `validation/` batch's Section 9 inventory is added, removed, or reworded by this decision group.

### 31K. Implementation Order (Stage A–D, For Future Use Once Approved)

This order is documented now so that, once §31 is author-approved, implementation can proceed without a further planning step. No stage below is executed by this decision group.

**Correction — exact test creation/execution ownership per stage (resolves the audit's Stage A/B ambiguity):**

- **Stage A — Request/result contracts.** Create `requests.py`, `results.py`. Create `test_ingestion_port_contract.py` containing exactly tests 1–7 (the contract-focused subset) — **test 8 (`test_market_data_source_port_protocol_conformance`) does not exist in the file yet at the end of Stage A.** No placeholder, `xfail`, `skip`, or bare `pass` body for test 8 is created — a not-yet-written test is simply not yet present in the file, which is not a "knowingly incomplete test." Gates: `ruff format --check`, `ruff check`, `mypy`, `pytest -q` targeted at tests 1–7.
- **Stage B — Port.** Create `port.py`. Add test 8 (`test_market_data_source_port_protocol_conformance`) to the existing `test_ingestion_port_contract.py` file, bringing it to its full, final 8 functions. Run all 8 tests in that file. Same gates.
- **Stage C — Offline stub.** Create `offline_file_source.py`; create `test_offline_file_stub.py` containing all 8 tests at once (it has no cross-stage split — every test in this file depends only on `offline_file_source.py`, which exists by this stage). Run all 8 stub tests. Same gates.
- **Stage D — Exports and full verification.** Create `__init__.py` with the exact §31G export list (5 exports, annotated by defining file); run the full test suite, both baseline suites, and all quality gates; verify the exact 7 changed paths and the exact 16 new top-level test functions (8 + 8, fixed at documentation time per §31H — no test is renamed, added, or removed during implementation).

### 31L. Baseline, Quality Gates, and Stop Conditions (For Future Use Once Approved)

**Execution-captured baseline policy applies unchanged (§26):** the baseline is the clean, synchronized `HEAD` captured immediately before the first implementation change of a future, separately authorized implementation turn — currently that would be `7286ceaac6381c06237d332f58af7660d877e499`, but the actual baseline must be re-captured fresh at the start of that turn, not assumed from this document.

**Preflight checklist (future turn):** clean, synchronized `main`; current documentation commit includes this decision group; Python `3.12.13`, `uv` `0.11.30`, Pydantic `>=2.13.4,<2.14`; `uv lock --check` passes; existing full suite passes at whatever its then-current total is (281 as of this writing); existing original baseline suite passes at 34; existing combined top-level test functions at 189; no `ingestion/` path yet exists; no dependency diff pending.

**Final gates (future turn):** `uv lock --check`; `ruff format --check .`; `ruff check .`; `mypy src tests`; `pytest -q` (full suite); `pytest -q` on the two baseline files. **No fixed final collected-pytest-total is mandated in advance** — only the exact 16 new top-level test functions and the exact 7 new/changed paths are mandated, consistent with the "no total until parametrization is documented" policy already used in §30C.

**Mandatory stop conditions (future turn):** dirty or diverged repository; a test total that differs from what this document records at the time review begins; any dependency change; an 8th `ingestion/`-adjacent path becoming necessary; any modification to an existing, already-closed Phase 1B-B or Phase 1B-C-MD file; any documentation change attempted mid-implementation; a genuine need for real file/filesystem parsing inside `OfflineFileSource`; `SourceAcquisitionRequest`/`SourceAcquisitionResult` needing to duplicate `SourceCandleInput`/`IngestionResult` fields; the offline stub needing to generate rather than merely echo candle observations; the exact test names/counts in §31H becoming unsatisfiable; any quality-gate failure; `HEAD` changing after baseline capture; any temporary or generated file; or any newly discovered inventory-vs-recommendation conflict beyond the one already resolved in §31F. On any of these, stop and report — do not improvise a workaround.

### 31M. Document Scope

This decision group touches exactly 4 authoritative documents: this register (§31, including the §31C/§31D/§31E/§31F/§31G/§31H/§31K corrections applied across both the initial reconciliation draft and the subsequent audit-correction pass); `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md`, updated through (1) row 45's dependency correction, (2) row 47's dependency correction, (3) row 48's deterministic-stub responsibility correction (and completed dependency list), (4) Section 14's Batch 1B-E dependency-summary correction, and (5) Section 36 (the reconciliation and audit-correction record, documenting both passes); `REPOSITORY_SCAFFOLD_PLAN.md` (a new section recording this decision group, kept consistent with every correction above); and `PROJECT_STATE.md` (a new section recording status, next controlled action, and the post-audit correction pass). **The inventory's structure itself did not change through any of this: no new documentation file is created, and no inventory row is added, removed, renamed, or renumbered anywhere.**

### 31N. Author Approval Record

**Author decision: `APPROVED`.** **Approval date: 2026-07-26.** The author explicitly approved Phase 1B-E Decision Group 1 exactly as documented (§31A–§31M), with no modification to any approved element. **Approved status: `AUTHOR-APPROVED`, `AUTHORIZED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Final audit verdict: A. PASS — READY FOR AUTHOR APPROVAL.** The final read-only architectural audit found **no blocking finding** and **no non-blocking finding**.

The author approved, without modification:

- **Option B — Distinct Source-Adapter Control Contracts** (§31B), including the exact boundary flow `Provider or deterministic source → MarketDataSourcePort → SourceAcquisitionResult → zero or more SourceCandleInput records → Phase 1B-C market-data pipeline → RawCandle/NormalizedCandle/market_data.IngestionResult`.
- The exact preserved 7-row Batch 1B-E inventory scope (§31C) and its wording corrections (rows 45, 47, 48, and the Section 14 summary row) — no row added, removed, renamed, or renumbered.
- The exact `SourceAcquisitionRequest` contract (§31D): 4 fields, no defaults, the provider-versus-adapter-identity distinction, and the exact whitespace-stripped/case-sensitive string-matching policy.
- The exact `SourceAcquisitionOutcome`/`SourceAcquisitionResult` contracts (§31E): 3 outcomes, 3 result fields in fixed order, the frozen/strict/extra-forbid/default-validating model, the complete per-outcome invariant matrix, and the closed 2-code reason-code vocabulary.
- The exact `MarketDataSourcePort` Protocol and `OfflineFileSource` design (§31F): the `acquire()` signature; the `MappingProxyType`-backed, defensive-copy fixture-catalogue policy; `OfflineFileSource` as a deterministic fixture-catalogue stub only, emitting only `SUCCEEDED` or `UNSUPPORTED` in this batch, with `FAILED` remaining available for future adapters and real file parsing remaining explicitly deferred.
- The exact 5-export `__init__.py` list (§31G), the exact 16 new top-level test names and their coverage/ownership assignments (§31H), the explicit exclusions (§31I), the deferred validation-overlap note (§31J) — provider networking and the `validation/`-layer reconciliation both remain explicitly deferred — the Stage A–D implementation order (§31K), and the baseline/quality-gate/stop-condition definitions (§31L).

### 31O. Implementation Completion and Closure

**Phase 1B-E Provider-Neutral Ingestion Boundary: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

**Implementation commit:** `0a9814eddd1cdeda59cf95dbde8a806f30800b44` — "Implement Phase 1B-E ingestion boundary". Push succeeded to `origin/main`; local `HEAD` equaled `origin/main` at this commit; the working tree was clean afterward. **Exact 7 added paths, every status `A`:** 5 new source files under `src/btmm_ai_scanner/ingestion/` (`__init__.py`, `requests.py`, `results.py`, `port.py`, `offline_file_source.py`) and 2 new test files under `tests/unit/` (`test_ingestion_port_contract.py`, `test_offline_file_stub.py`) — matching §31C's approved scope exactly, no eighth path. Insertions/deletions: 844 insertions(+), 0 deletions(-). No existing tracked file was modified. No `pyproject.toml`/`uv.lock` change. No documentation file was included in the implementation commit. No configuration or private-reference file changed.

**Implemented capabilities, exactly as approved:**

- **`SourceAcquisitionRequest`** (`requests.py`): exactly 4 fields (`provider`, `source_reference`, `source_symbol`, `source_timeframe`), strict/frozen/extra-forbid, no defaults, whitespace stripped at construction, case-sensitive thereafter, `provider` meaning only the underlying data provider (e.g. `"FXCM"`), no adapter-mode field, no candle field.
- **`SourceAcquisitionOutcome`/`SourceAcquisitionResult`** (`results.py`): 3 outcomes (`SUCCEEDED`/`UNSUPPORTED`/`FAILED`); 3 result fields in fixed order (`outcome`, `source_candle_inputs`, `reason_codes`); the complete per-outcome invariant matrix enforced by a real model validator; exactly 2 closed source-level reason codes (`SOURCE_REQUEST_UNSUPPORTED`, `SOURCE_ACQUISITION_FAILED`); no duplication of `market_data.IngestionResult`'s 5-outcome/8-reason-code state machine.
- **`MarketDataSourcePort`** (`port.py`): one synchronous `acquire(request: SourceAcquisitionRequest) -> SourceAcquisitionResult` method; provider-neutral; not `@runtime_checkable`; no state; no networking/filesystem/database/`RawCandle`/`NormalizedCandle` type anywhere in the signature.
- **`OfflineFileSource`** (`offline_file_source.py`): a deterministic fixture-catalogue adapter implementing `MarketDataSourcePort`; constructor accepts `Mapping[SourceAcquisitionRequest, tuple[SourceCandleInput, ...]]`, defensively copied and wrapped in `MappingProxyType`; a known request returns `SUCCEEDED` (with or without records, order preserved); an unknown request returns `UNSUPPORTED`/`SOURCE_REQUEST_UNSUPPORTED`; `FAILED` is never emitted in this batch; `provider` is never rewritten to `"OFFLINE_FILE"`; no file parsing, no network call, no generated candle value, no market-data pipeline processing.
- **`__init__.py`:** exactly 5 exports in fixed order — `SourceAcquisitionRequest`, `SourceAcquisitionOutcome`, `SourceAcquisitionResult`, `MarketDataSourcePort`, `OfflineFileSource`.

**Verification record:** contract tests 8 passed; offline-source tests 8 passed; full suite 297 passed; original baseline suite 34 passed; existing top-level test functions 189; new Phase 1B-E top-level test functions 16; combined top-level test functions 205; Ruff format — passed; Ruff lint — passed; mypy — passed; `uv lock --check` — passed; no unexpected warning.

**Two accepted implementation characteristics (not defects):**

1. `ContractModel`'s `revalidate_instances="always"` config means a nested `SourceCandleInput` value may be re-validated into an equivalent-but-distinct Pydantic instance when wrapped in a `SourceAcquisitionResult`. Exact IDs, fingerprints, timestamps, versions, provenance, and every field value are preserved; Python object identity (`is`) is not part of the contract and is not required by any test.
2. `MarketDataSourcePort` is intentionally not `@runtime_checkable`. Conformance is verified through its structural signature (`inspect.signature`) and through real inheritance/MRO inspection, not through `isinstance()`/`issubclass()`, which raise `TypeError` against any non-runtime-checkable Protocol regardless of actual inheritance.

**Audit history (concise):**

1. Decision Group 1 architecture approved (§31N).
2. Stage A implemented `requests.py`/`results.py` and 7 contract tests.
3. The Stage A audit found one vacuous test assertion (a literal compared to an identical literal).
4. That assertion was removed without changing production behavior or the approved test count.
5. A combined Stage B–D implementation added `port.py`, `offline_file_source.py`, `__init__.py`, the eighth contract test, and all 8 offline-source tests.
6. The final combined audit verdict was **A. PASS — READY TO COMMIT**, with no blocking finding.
7. The implementation was committed and pushed as `0a9814eddd1cdeda59cf95dbde8a806f30800b44`.

**This closure does not authorize production use, live trading, an indicator, a robot, provider networking, or a persistence backend.** No FXCM/TradingView adapter, no real file parser, no persistence implementation, no POI detector, no BTMM detector, no indicator, no alert, no backtester, and no robot was implemented in this batch. Phase 1B-E is **closed** at the provider-neutral ingestion-boundary level only — it remains `NOT PRODUCTION-APPROVED`.

## 32. Historical Repository and Replay Foundation — Architecture and Exact Implementation Controls

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** (See §32P for the implementation, audit, and closure record.)

This decision group defines one compact, accelerated milestone: a deterministic, in-memory, non-production persistence and replay foundation that consumes the completed market-data (Phase 1B-C-MD) and ingestion (Phase 1B-E) contracts. It fulfills the exact deferred promise already recorded in `REPOSITORY_SCAFFOLD_PLAN.md` (line 539): *"Storage/replay boundary is interfaces-only in the first batch (`RawCandleSink`, `NormalizedCandleSink`, `CandleReadRepository`, `HistoricalReplaySource`), with in-memory test doubles — no database, queue, or cloud storage."* This milestone builds exactly those in-memory test doubles — nothing more. It does not create the master scaffold's separate `replay/` top-level package (`REPOSITORY_SCAFFOLD_PLAN.md` §3: *"Historical replay engine — re-runs the pipeline against pinned raw data and pinned rule/schema versions"* — explicitly "Directory only" through Phase 1B, still absent from near-term scope). That fuller, versioned replay engine remains a separate, later, explicitly deferred decision.

### 32A. Existing Protocol Compatibility Audit — No Protocol Modification Required

The exact current signatures in `src/btmm_ai_scanner/market_data/ports.py`:

```python
class RawCandleSink(Protocol):
    def store_raw_candle(self, raw_candle: RawCandle) -> None: ...

class NormalizedCandleSink(Protocol):
    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None: ...

class CandleReadRepository(Protocol):
    def find_raw_candles_by_source_identity(
        self, provider: str, source_reference: str, source_symbol: str,
        source_timeframe: str, event_time_utc: datetime,
    ) -> Sequence[RawCandle]: ...

class HistoricalReplaySource(Protocol):
    def replay(self) -> Iterator[NormalizedCandle]: ...
```

**Findings:**

- `CandleReadRepository` is typed for `RawCandle` only (its method returns `Sequence[RawCandle]`) — it cannot be satisfied by a `NormalizedCandle` repository. Its query is an **exact single-instant match** (`event_time_utc: datetime`, not a range) keyed by the full source identity. **This is deliberate, not a defect**: `Sequence[RawCandle]` (already plural) confirms the original author anticipated multiple `RawCandle` records sharing one source-identity-and-event-time — exactly the "conflicting revisions must remain observable" requirement this milestone must satisfy.
- `HistoricalReplaySource.replay()` is a bare, zero-parameter method returning a plain `Iterator[NormalizedCandle]` — no cursor, no reset, no initialize-from-query parameter, no async.
- All 4 are `typing.Protocol`s, structural, not `@runtime_checkable`.

**Sufficiency result: sufficient, no Protocol extension required.** A Python `Protocol` defines a minimum structural interface, not a maximum — a concrete class may implement a Protocol exactly while exposing additional public methods that are not themselves part of any Protocol. This milestone's concrete classes (§32D–§32F) implement all 4 existing Protocols exactly as defined above, byte-for-byte unchanged, and separately expose richer range-query and cursor-based replay capability as their own additional public methods. **`src/btmm_ai_scanner/market_data/ports.py` is not modified by this milestone.**

### 32B. Exact File Scope — 8 Changed Paths (7 New, 1 Modified)

| # | Path | Status | Purpose |
|---|---|---|---|
| 1 | `src/btmm_ai_scanner/market_data/raw_candle_repository.py` | New | `InMemoryRawCandleRepository`, `RecordIdentityConflictError`, `InvalidTimeRangeError` |
| 2 | `src/btmm_ai_scanner/market_data/normalized_candle_repository.py` | New | `InMemoryNormalizedCandleRepository` |
| 3 | `src/btmm_ai_scanner/market_data/historical_replay.py` | New | `InMemoryHistoricalReplaySource` |
| 4 | `src/btmm_ai_scanner/market_data/__init__.py` | **Modified** | Append 5 new exports |
| 5 | `tests/unit/test_raw_candle_repository.py` | New | 8 tests |
| 6 | `tests/unit/test_normalized_candle_repository.py` | New | 8 tests |
| 7 | `tests/unit/test_historical_replay.py` | New | 8 tests |
| 8 | `tests/unit/test_no_look_ahead.py` | New | 7 tests |

**5 source paths (4 new + 1 modified), 4 test paths — 8 total changed paths.** This is below the 6–10-source/4–7-test guidance range on the source side; per the instruction ("guidance, not permission to invent unnecessary files"), no additional file is invented merely to fill the range. All new files live inside the already-approved `market_data/` package — no new top-level package is created. `RecordIdentityConflictError`/`InvalidTimeRangeError` are defined once in `raw_candle_repository.py` and imported from there wherever needed — no `repository_errors.py` file is created, preserving the exact 8-path scope.

**Existing-file modification, explicitly identified and justified:** `market_data/__init__.py` currently exports exactly 20 names (Phase 1B-C-MD, register §29J). This milestone appends exactly 5 new names to the end of the existing `__all__` list — **the existing 20 names and their order are completely unchanged; no name is removed, renamed, or reordered.** Justification: `market_data/__init__.py` is the package's single established public-import surface; the 5 new symbols are new capabilities of the same package (they directly implement `market_data.ports` Protocols and consume `market_data`'s own `RawCandle`/`NormalizedCandle`), so appending to the same list is the minimal, most consistent choice — matching the same append-only-at-the-end discipline already used for the reason-code/row corrections in Phase 1B-E's own documentation passes. No other existing tracked file is modified.

### 32C. Repository Membership — Three Separate Axes (Correction)

**Correction — repository membership does not imply analytical validity or eligibility.** The prior draft's claim that "invalid/indeterminate records" are "structurally impossible" in repository storage conflated two genuinely distinct axes with a third, unrelated one. This milestone documents all three explicitly:

- **A. Structural contract validity.** `RawCandle` and `NormalizedCandle` are self-validating `ContractModel`s — a constructed instance always satisfies its own field-level and cross-field invariants (OHLC consistency, timestamp ordering, etc.). This is guaranteed by Pydantic construction itself; no instance of either contract can exist in a structurally-invalid state.
- **B. Ingestion construction gating.** The closed `market_data.IngestionResult` outcome matrix (register §29C) prevents a `REJECTED`/`INDETERMINATE` pipeline outcome from ever carrying a `candidate_raw_candle`/`candidate_normalized_candle` through the normal pipeline path (`raw_candle_builder.py`/`normalization.py`). This blocks *that specific pathway* into a repository — it does not, by itself, mean every possible route to repository membership is gated this way.
- **C. Analytical validity and eligibility.** `contracts/validation_result.py` defines a **wholly separate** contract family — `ValidationResult`, `ValidationStatus` (`VALID`/`INVALID`/`INDETERMINATE`), `AnalyticalEligibility` (`ELIGIBLE`/`INELIGIBLE`/`UNDETERMINED`) — linked to a candle only through `subject_record_id`. **It is not embedded in `RawCandle` or `NormalizedCandle`, and it is not part of `market_data.IngestionResult`.**

**Consequently:** `InMemoryRawCandleRepository`/`InMemoryNormalizedCandleRepository` do not receive, store, infer, or enforce `ValidationStatus`, `AnalyticalEligibility`, analytical invalidity, analytical indeterminacy, or detector eligibility — their `store_raw_candle`/`store_normalized_candle` methods have no parameter for any of this. Therefore:

- Repositories store whatever structurally-valid (axis A) candle contract a caller supplies to them.
- Repository membership does **not** imply analytical validity (axis C).
- Repository membership does **not** imply analytical eligibility (axis C).
- Ingestion outcome (axis B) remains separate from repository membership — axis B governs whether the *normal pipeline path* produces a candidate at all; it says nothing about a caller directly supplying a structurally-valid candle obtained by other legitimate means.
- Any future validation/eligibility repository, join, or query against `ValidationResult` remains explicitly deferred and out of scope for this milestone.

### 32D. `InMemoryRawCandleRepository` — Exact Design

Implements `RawCandleSink` and `CandleReadRepository` exactly as defined in §32A, plus additional non-Protocol public methods:

```python
class RecordIdentityConflictError(ValueError): ...
class InvalidTimeRangeError(ValueError): ...

class InMemoryRawCandleRepository:
    def store_raw_candle(self, raw_candle: RawCandle) -> None: ...

    def find_raw_candles_by_source_identity(
        self, provider: str, source_reference: str, source_symbol: str,
        source_timeframe: str, event_time_utc: datetime,
    ) -> Sequence[RawCandle]: ...

    def find_raw_candles_by_source_identity_and_event_time_range(
        self, provider: str, source_reference: str, source_symbol: str,
        source_timeframe: str,
        start_time_utc: datetime | None, end_time_utc: datetime | None,
    ) -> tuple[RawCandle, ...]: ...

    def all_raw_candles(self) -> tuple[RawCandle, ...]: ...
```

`RecordIdentityConflictError` and `InvalidTimeRangeError` (§32I) are defined in this module — the compact shared repository exception vocabulary — and imported from here by `normalized_candle_repository.py`. No `repository_errors.py` is created; this does not add a ninth path.

- **Identity/storage key:** `record_id` (the `RawCandle`'s own `UUIDv7`) — a private `dict[UUID, RawCandle]`, never exposed directly. `record_id` is the repository's *storage*-identity key; it does not replace, and is not compared against, the established five-field `SourceCandleIdentity` (`provider`, `source_reference`, `source_symbol`, `source_timeframe`, `event_time_utc`, `market_data/idempotency.py`) used for idempotency classification.
- **Exact duplicate/revision policy (all 5 cases, per register §32 audit):**
  1. **Same `record_id`, identical complete record** → idempotent no-op; the existing stored record remains; no second entry; no exception.
  2. **Same `record_id`, different complete record** → never overwrite; raises `RecordIdentityConflictError`; the repository remains unchanged. This can only arise from a caller programming error, since `record_id` is a globally unique `UUIDv7` minted once per construction.
  3. **Different `record_id`, same five-field source identity, same `content_fingerprint`** — the existing `EXACT_DUPLICATE` classification (`market_data.evaluate_idempotency`): both records are stored, both are returned by matching queries, deterministic ordering is preserved, neither is silently collapsed.
  4. **Different `record_id`, same five-field source identity, different `content_fingerprint`** — the existing `CONFLICTING_REVISION` classification: both records are stored, both are returned, **no automatic winner is chosen**.
  5. **Different `record_id`, different source identity** — stored independently; no duplicate/revision relationship is inferred.
  The repository does not re-run idempotency logic itself — it stores exactly what a caller (who already ran `market_data.evaluate_idempotency`, typically using a prior call to `find_raw_candles_by_source_identity` as that function's `existing_raw_candles` argument) hands it.
- **Repository membership:** see §32C — structurally-valid candles only; no claim about analytical validity/eligibility.
- **Range query semantics** (`find_raw_candles_by_source_identity_and_event_time_range`):
  - `start_time_utc`/`end_time_utc` are `datetime | None`. `None` on either side means **unbounded** on that side.
  - Any timezone-aware `datetime` is accepted on either bound and is normalized to UTC internally using the established `require_aware_datetime`/`to_utc` conventions (`contracts/raw_candle.py`) — an aware, non-UTC-offset datetime is accepted and normalized; it is **not** an error.
  - A **naive** `start_time_utc` or `end_time_utc` raises `InvalidTimeRangeError`.
  - Both bounds provided and `start < end`: half-open `[start, end)` — start inclusive, end exclusive.
  - Both bounds provided and `start == end`: a **valid** query, returning an empty tuple (not an error).
  - Both bounds provided and `start > end`: raises `InvalidTimeRangeError`.
  - No matching records for an otherwise-valid query: returns an empty tuple.
- **Query ordering:** all multi-result queries return a `tuple`, stable-sorted by `(event_time_utc, record_id)` ascending.
- **Mutation isolation:** every query method constructs and returns a fresh `tuple` each call; repository state is never exposed or mutated by a query.
- **No database, no filesystem, no network.**

### 32E. `InMemoryNormalizedCandleRepository` — Exact Design

Implements `NormalizedCandleSink` exactly. **Does not implement `CandleReadRepository`** — that Protocol is `RawCandle`-typed and cannot be satisfied by a class whose queries return `NormalizedCandle` (a genuine, discovered structural mismatch, not an oversight — see §32A). It exposes its own read API instead, importing `RecordIdentityConflictError`/`InvalidTimeRangeError` from `raw_candle_repository.py`:

```python
class InMemoryNormalizedCandleRepository:
    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None: ...

    def find_by_symbol_timeframe_range(
        self, symbol: InternalSymbol, timeframe: Timeframe,
        start_time_utc: datetime | None, end_time_utc: datetime | None,
    ) -> tuple[NormalizedCandle, ...]: ...

    def all_normalized_candles(self) -> tuple[NormalizedCandle, ...]: ...
```

Same identity key (`record_id`), same five-case exact-duplicate/revision policy, same `RecordIdentityConflictError`/`InvalidTimeRangeError` vocabulary, same `None`-is-unbounded/naive-rejects/half-open/`start==end`-empty/`start>end`-raises range semantics, same `(event_time_utc, record_id)` query ordering, same mutation isolation, and the same §32C repository-membership policy (structurally-valid candles only; no analytical-validity/eligibility claim) as §32D. No synthetic candle, no interpolation, no session/calendar assumption, no automatic gap repair.

### 32F. `InMemoryHistoricalReplaySource` — Exact Design

Implements `HistoricalReplaySource` exactly, plus an atomic availability-group cursor API (no single-candle `advance_one` method exists):

```python
class InMemoryHistoricalReplaySource:
    def __init__(self, candles: Iterable[NormalizedCandle]) -> None: ...

    def replay(self) -> Iterator[NormalizedCandle]: ...

    @property
    def position(self) -> int: ...

    @property
    def is_exhausted(self) -> bool: ...

    def advance_next_availability_group(self) -> tuple[NormalizedCandle, ...]: ...

    def reset(self) -> None: ...
```

- **Replay data boundary:** the constructor accepts a caller-supplied `Iterable[NormalizedCandle]` — the caller runs its own repository query first (e.g. `InMemoryNormalizedCandleRepository.find_by_symbol_timeframe_range(...)`) and hands the result to the replay source. The replay source itself never queries a repository directly and never constructs a `RawCandle`, performs normalization, or evaluates idempotency — it is purely a deterministic sequencer over an already-resolved set of `NormalizedCandle` records.
- **Snapshot, not live-view:** the constructor defensively copies and sorts the supplied candles once, into an immutable `tuple[NormalizedCandle, ...]`, at construction time, using the ordering key in §32H. Later writes to the source repository never retroactively appear in an already-constructed replay source — this is what guarantees no future-candle exposure and identical repeated runs.
- **Cursor representation:** a private integer `_position` — the number of candles already consumed (not the number of groups consumed) — indexing the next unconsumed candle in the immutable snapshot, exposed read-only via `.position`.
- **Atomic availability-group advancement — `advance_next_availability_group()`:**
  - Identifies the next not-yet-consumed `availability_time_utc` instant in the snapshot.
  - Returns **every** `NormalizedCandle` sharing that exact instant, together, as one immutable `tuple`, in the stable order defined by §32H's ordering key (with `availability_time_utc` constant across the group, ordering proceeds by the tuple's remaining fields).
  - Advances `.position` by `len(returned_group)` — the whole group is consumed atomically; no partial group is ever exposed.
  - Returns an empty tuple `()` at end-of-stream — **no exception is raised.**
  - Never creates artificial causal ordering among candles that became available at the same instant.
- **End-of-stream:** `.is_exhausted` is `True` once `.position == len(snapshot)`; `advance_next_availability_group()` returns `()` — no exception, no leaked future record.
- **Reset:** `.reset()` sets `.position` back to `0`. An empty replay begins exhausted (`.is_exhausted` is `True` immediately after construction with no candles). The underlying snapshot tuple is immutable and sorted exactly once at construction, so `.reset()` followed by re-advancing reproduces the identical availability-group sequence every time.
- **`replay()` — Protocol compatibility, no Protocol change:** returns a fresh, stateless `iter()` over the complete immutable snapshot; it does **not** read or mutate `.position`/the stateful cursor. Repeated `replay()` calls always return the same complete deterministic sequence, regardless of any prior `advance_next_availability_group()`/`reset()` activity. `HistoricalReplaySource.replay() -> Iterator[NormalizedCandle]` is preserved unchanged — no Protocol extension is required. `replay()` exists for Protocol compatibility and full deterministic iteration; **availability-sensitive detector progression must consume `advance_next_availability_group()`, not individual `replay()` iterator elements, whenever simultaneous availability can affect a causal decision.**
- **Empty replay:** constructing with an empty iterable is valid; `.is_exhausted` is `True` immediately; `advance_next_availability_group()` returns `()` immediately; `replay()` yields nothing.
- **Synchronous only** — matches `HistoricalReplaySource`'s own `Iterator` (not `AsyncIterator`) return type; no async method anywhere.
- **No wall-clock dependency, no `datetime.now()`/`datetime.utcnow()` anywhere.**
- **Thread-safety scope:** implementations are **not thread-safe**; intended for deterministic single-threaded tests and historical analysis only; no locks; no background tasks; concurrent read/write behavior is unsupported; production concurrency is explicitly deferred.
- **Snapshot/object-identity policy:** none of `InMemoryRawCandleRepository`, `InMemoryNormalizedCandleRepository`, or `InMemoryHistoricalReplaySource` are `ContractModel` (Pydantic) subclasses — they are ordinary Python classes. `ContractModel`'s `revalidate_instances="always"` behavior therefore does not apply to or define these classes' internal mechanics; candle objects are held directly in plain `dict`/`tuple` structures. Nonetheless, **Python object identity (`is`) is not part of the public contract** — exact field-value preservation (IDs, fingerprints, timestamps, versions, provenance) is what is guaranteed, and tests verify equality, not identity, so the internal mechanics remain free to change. No internal list, dict, or mutable catalogue is ever exposed publicly.

### 32G. Replay Visibility and Look-Ahead Protection Policy

**Governing timestamp: `availability_time_utc`, never `event_time_utc` alone and never `processing_time_utc`.** A candle must never be exposed by replay before the instant a real system would have known about it — that instant is `availability_time_utc`, not the candle's own market event time (`event_time_utc`) and not the pipeline's internal processing timestamp (`processing_time_utc`, which records when *this system* finished processing the candle, not when it was legitimately knowable).

**Unavailable-availability policy (timestamp contract validity only — not to be confused with §32C's analytical-eligibility axis):** `SourceCandleInput.availability_time_utc` may be unavailable (`datetime | None`) upstream, at the acquisition stage. `RawCandle.availability_time_utc` and `NormalizedCandle.availability_time_utc` are both **non-nullable** `datetime` fields, and both contracts' own cross-field validators require `availability_time_utc > event_time_utc` unconditionally (`contracts/raw_candle.py`, `contracts/normalized_candle.py`). The closed Phase 1B-C-MD ingestion matrix (register §29B/§29E) guarantees that an unavailable or inconsistent availability pair at the `SourceCandleInput` stage produces `IngestionResult.outcome == INDETERMINATE` or `REJECTED` — **never** a `candidate_raw_candle` or `candidate_normalized_candle` — through the approved pipeline path. Historical replay therefore accepts only `NormalizedCandle` records with valid availability; **no replay-time substitution, inference, or processing-time fallback exists, and no replay-initialization exception is required for a state (`None` availability on a `NormalizedCandle`) that cannot exist in the contract.** This is a statement about timestamp *contract* validity (axis A/B of §32C) — it says nothing about, and must not be confused with, analytical validity or eligibility (axis C of §32C), which remains a separate, unaddressed concern.

**Equal-availability tie-breaking:** when two or more `NormalizedCandle` records share the exact same `availability_time_utc`, `advance_next_availability_group()` (§32F) returns all of them together, in the exact stable order defined by §32H's ordering key — never arbitrarily, never by insertion order into the constructor's input iterable, and never split across two separate advancement calls.

### 32H. Replay Ordering Key (Exact Tuple)

**Replay visibility ordering** (governs both the immutable snapshot's overall order and the internal order within one `advance_next_availability_group()` release):

```
(availability_time_utc, event_time_utc, symbol.value, timeframe.value, provider, source_reference, record_id)
```

Every field exists on `NormalizedCandle` and is comparable: `availability_time_utc`/`event_time_utc` are `datetime`; `symbol.value`/`timeframe.value` are `str` (via the `StrEnum` `InternalSymbol`/`Timeframe`); `provider`/`source_reference` are `str`; `record_id` is a `UUID` (Python `UUID` implements `__lt__`/`__gt__`). The key is total, deterministic, and independent of insertion order. `availability_time_utc` is primary (replay is availability-driven — see §32G); `event_time_utc` is the natural secondary chronological tie-break and can never expose a candle before its availability instant (processing_time_utc never controls visibility at all — it does not appear in this tuple); within one availability group (constant `availability_time_utc`), stable order is determined entirely by the remaining fields. `record_id` (`UUIDv7`, globally unique, immutable, never regenerated) is the absolute final tie-breaker.

**`source_symbol`/`source_timeframe` are deliberately omitted** as additional tie-breakers: `source_reference` is already the stable logical series identifier (by established convention, unique per provider), so `provider`+`source_reference` alone already fully disambiguates the originating series, and `record_id` guarantees a total final ordering regardless — adding the raw source-level symbol/timeframe strings would be redundant.

**Repository query ordering** (governs the order `InMemoryRawCandleRepository`/`InMemoryNormalizedCandleRepository` return multi-record query results — a distinct, simpler concept from replay visibility, with no availability-grouping semantics):

```
(event_time_utc, record_id)
```

Natural chronological read order, tie-broken by the same stable final `record_id` key.

### 32I. Exact Exception Vocabulary — 2 Classes

Exactly two new public exception classes, both `ValueError` subclasses (so existing `except ValueError` handling still works), both defined in `market_data/raw_candle_repository.py` (the designated owner of this compact, shared repository exception vocabulary) and imported from there by `normalized_candle_repository.py`:

- **`RecordIdentityConflictError`** — means only: the same `record_id` is already stored, and the incoming complete candle record differs from the stored record; no overwrite occurred.
- **`InvalidTimeRangeError`** — means: `start_time_utc` is later than `end_time_utc`; **or** a supplied `start_time_utc`/`end_time_utc` is naive. **Not** raised for an aware datetime merely because its offset is not UTC — such a value is accepted and normalized.

"Replay initialization with unreplayable availability" requires no exception: per §32G, a `NormalizedCandle` with unavailable availability cannot exist, so this case is structurally inapplicable rather than unresolved. "End of stream" is not an exception either case — `advance_next_availability_group()` returns `()`.

### 32J. Public Exports — 5 New Names

Exactly 5 new names, appended to the end of `market_data/__init__.py`'s existing 20-name `__all__` (order preserved, nothing removed, no sixth new name):

| # | Export | Defining file |
|---|---|---|
| 21 | `RecordIdentityConflictError` | `market_data/raw_candle_repository.py` |
| 22 | `InvalidTimeRangeError` | `market_data/raw_candle_repository.py` |
| 23 | `InMemoryRawCandleRepository` | `market_data/raw_candle_repository.py` |
| 24 | `InMemoryNormalizedCandleRepository` | `market_data/normalized_candle_repository.py` |
| 25 | `InMemoryHistoricalReplaySource` | `market_data/historical_replay.py` |

No cursor-state field, no private helper, and no unrelated `ingestion` symbol is exported. **Future `market_data` export total: 25** (20 existing + 5 new).

### 32K. Exact Test Coverage — 31 New Top-Level Test Functions

**`tests/unit/test_raw_candle_repository.py` — 8:**

1. `test_in_memory_raw_candle_repository_stores_and_finds_by_source_identity`
2. `test_in_memory_raw_candle_repository_preserves_conflicting_revisions` — owns cases 3 (`EXACT_DUPLICATE`: different `record_id`, same identity, same fingerprint) and 4 (`CONFLICTING_REVISION`: different `record_id`, same identity, different fingerprint); both remain stored and query-visible.
3. `test_in_memory_raw_candle_repository_rejects_silent_overwrite_of_differing_content` — owns case 1 (same `record_id` + identical content → no-op) and case 2 (same `record_id` + different content → `RecordIdentityConflictError`, repository unchanged).
4. `test_in_memory_raw_candle_repository_range_query_boundary_is_half_open` — owns start-inclusive, end-exclusive, `start == end` → empty tuple, and omitted (`None`) bounds → unbounded on that side.
5. `test_in_memory_raw_candle_repository_rejects_invalid_time_range_inputs` — owns `start > end` → `InvalidTimeRangeError`; naive `start` raises; naive `end` raises; aware non-UTC-offset bounds are accepted and normalized (not an error).
6. `test_in_memory_raw_candle_repository_returns_stable_deterministic_ordering`
7. `test_in_memory_raw_candle_repository_query_results_do_not_mutate_stored_state`
8. `test_in_memory_raw_candle_repository_implements_sink_and_read_protocols`

**`tests/unit/test_normalized_candle_repository.py` — 8** (identical ownership divisions, normalized equivalents):

1. `test_in_memory_normalized_candle_repository_stores_and_queries_by_symbol_and_timeframe`
2. `test_in_memory_normalized_candle_repository_preserves_conflicting_revisions`
3. `test_in_memory_normalized_candle_repository_rejects_silent_overwrite_of_differing_content`
4. `test_in_memory_normalized_candle_repository_range_query_boundary_is_half_open`
5. `test_in_memory_normalized_candle_repository_rejects_invalid_time_range_inputs`
6. `test_in_memory_normalized_candle_repository_returns_stable_deterministic_ordering`
7. `test_in_memory_normalized_candle_repository_query_results_do_not_mutate_stored_state`
8. `test_in_memory_normalized_candle_repository_implements_sink_protocol_only`

**`tests/unit/test_historical_replay.py` — 8:**

1. `test_historical_replay_source_orders_by_availability_then_event_time_then_identity`
2. `test_historical_replay_source_advance_next_availability_group_releases_simultaneous_candles_together` — owns: equal-availability records return in one tuple; no partial group exposure; `.position` advances by group length; deterministic order inside the group.
3. `test_historical_replay_source_advance_next_availability_group_returns_empty_tuple_at_end`
4. `test_historical_replay_source_replay_reproduces_the_same_sequence_on_repeated_calls`
5. `test_historical_replay_source_reset_reproduces_the_exact_sequence`
6. `test_historical_replay_source_handles_empty_replay_deterministically`
7. `test_historical_replay_source_implements_protocol_and_exposes_no_extra_state`
8. `test_market_data_repository_and_replay_exports_import_successfully` — owns: existing 20 exports unchanged; exactly 5 appended exports; future total 25; exact new export order (§32J).

**`tests/unit/test_no_look_ahead.py` — 7:**

1. `test_replay_never_exposes_a_candle_before_its_availability_time`
2. `test_replay_exposes_a_candle_exactly_at_its_availability_time`
3. `test_replay_releases_equal_availability_candles_in_stable_tie_broken_order` — verifies atomic grouped release via `advance_next_availability_group()`, not merely adjacent single-candle ordering.
4. `test_event_time_alone_cannot_expose_a_candle_before_availability`
5. `test_processing_time_utc_does_not_control_historical_visibility`
6. `test_end_of_stream_never_leaks_a_future_record`
7. `test_source_cannot_receive_a_normalized_candle_with_unavailable_availability_time`

**Total new: 31** (8 + 8 + 8 + 7). No helper begins with `test_`. No test class. No dynamically generated test. No vacuous literal-to-identical-literal assertion. **Combined with the existing 205: 236.**

### 32L. Explicit Exclusions

SQLite, PostgreSQL, Redis, any cloud database; filesystem persistence; CSV/JSON/Parquet loading; FXCM REST/WebSocket; TradingView scraping; live streaming; session/calendar modeling; market-holiday logic; synthetic candles; interpolation; automatic gap repair; revision-winner selection; POI detection; market-structure detection; BTMM detection; indicators; alerts; Telegram; backtesting metrics; strategy evaluation; paper trading; MT5/MT4 execution; AI inference.

### 32M. Baseline, Quality Gates, and Stop Conditions

**Execution-captured baseline policy applies unchanged (§26):** the baseline is the clean, synchronized `HEAD` captured immediately before the first implementation change of a future, separately authorized implementation turn — currently `c673e66ef942b319006aeff9b8ac775712c5f86a`, re-captured fresh at that turn's start.

**Preflight (future turn):** clean, synchronized `main`; Python `3.12.13`, `uv` `0.11.30`, Pydantic `>=2.13.4,<2.14`; `uv lock --check` passes; existing full suite 297 passed; existing original suite 34 passed; existing combined top-level tests 205; no repository/replay implementation path yet exists; no dependency diff.

**Final gates:** `uv lock --check`; `ruff format --check .`; `ruff check .`; `mypy src tests`; `pytest -q` (full suite); `pytest -q` on the two baseline files. Exact 8 changed paths (7 new + 1 modified); exact 5 new exports; exact 31 new top-level test functions; exact 236 combined total.

**Mandatory stop conditions:** dirty/diverged repository; a test total differing from this document's record at review time; any dependency change; an existing file other than `market_data/__init__.py` needing modification; a genuine Protocol extension becoming necessary; a 9th path becoming necessary (including a `repository_errors.py` file — the two exceptions stay in `raw_candle_repository.py`); any documentation change mid-implementation; a real database/filesystem/network dependency becoming necessary; the exact test names/counts becoming unsatisfiable; any quality-gate failure; `HEAD` changing after baseline capture; any temporary file. On any of these, stop and report.

### 32N. Document Scope

Exactly 4 authoritative documents: this register (§32); `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` (7 new inventory rows under a new batch tag, plus a note on `market_data/__init__.py`'s existing row); `REPOSITORY_SCAFFOLD_PLAN.md` (a new section recording this milestone); `PROJECT_STATE.md` (a new section recording status and next controlled action). No new documentation file is created.

### 32O. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected Historical Repository and Replay Foundation architecture exactly as documented (§32A–§32N), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `AUTHORIZED FOR ONE COMPLETE CONTROLLED IMPLEMENTATION CYCLE`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Exact approved scope:** 8 implementation paths (4 new source files, 4 new test files, 1 existing file modified — `market_data/__init__.py`); 31 new top-level test functions (8 + 8 + 8 + 7); 5 new public exports (20 → 25 total for `market_data`); inventory 69 → 76 rows under batch tag `1B-G-REPLAY`; no dependency change; no Protocol modification.

The author approved, without modification, every corrected architectural decision:

- Repository membership is separated from analytical validity/eligibility (§32C) — the three-axis distinction (structural contract validity, ingestion-outcome construction gating, analytical validity/eligibility via `ValidationResult`/`ValidationStatus`/`AnalyticalEligibility`) is adopted exactly as documented.
- The exact 5-case duplicate/revision policy (§32D) and the closed 2-exception vocabulary — `RecordIdentityConflictError`, `InvalidTimeRangeError` (§32I), both defined in `raw_candle_repository.py`.
- Timezone-aware range-query normalization: `None`-is-unbounded, half-open `[start, end)`, `start == end` valid-empty, `start > end` raises, naive raises, aware non-UTC accepted and normalized (§32D/§32E).
- Atomic availability-group replay advancement via `advance_next_availability_group()` (§32F) — no single-candle `advance_one()` exists.
- `replay()`'s stateless Protocol-compatibility (§32F) — unchanged `HistoricalReplaySource` Protocol, no extension.
- Snapshot semantics (§32F) and the explicit non-thread-safe scope (§32F).
- The exact replay ordering key (§32H), the exact export list and order (§32J), and the exact 31 test names and counts (§32K).

**This approval authorizes exactly one complete implementation cycle** covering all 8 approved paths at once (no per-file decision groups), followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started — this remains a documentation-only approval.**

### 32P. Implementation, Final Audit, and Closure Record

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

**Approval commit:** `0d133fa070f66ceff60016d18cbc531bfff3f0af`. **Implementation commit:** `5a1d8f30ee0eb67d27417fda9fb7407d9a5e8a85`. **Commit message:** "Implement 1B-G-REPLAY foundation". **Push:** succeeded to `origin/main`.

**Implemented scope:** exactly 8 committed paths — 3 new source files (`raw_candle_repository.py`, `normalized_candle_repository.py`, `historical_replay.py`), 1 modified existing file (`market_data/__init__.py`, append-only, 20 → 25 exports, existing 20 unchanged and in order), 4 new test files. Source/test split 4/4. No ninth path. No dependency or lockfile change. No `market_data/ports.py` change — all 4 existing Protocols remain byte-for-byte unchanged.

**Final architectural audit verdict: `B. PASS WITH NON-BLOCKING FINDINGS — READY TO COMMIT`.** One non-blocking finding: `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md`'s Section 9 summary sentence still described Batch `1B-G-REPLAY` as `ARCHITECT-RECOMMENDED, AUTHOR-DECISION REQUIRED`, a wording staleness left over from before the Phase A author approval — corrected as part of this closure pass (Section 9's per-row statuses were already correctly `AUTHOR-APPROVED` throughout; only the batch-level summary sentence lagged). No blocking finding. Every architectural control audited exactly as designed: the three-axis repository-membership distinction (§32C); the exact 5-case duplicate/revision policy and closed 2-exception vocabulary (§32D/§32E/§32I); timezone-aware range-query normalization including `start == end`, `start > end`, naive rejection, and aware non-UTC acceptance (§32D/§32E); atomic `advance_next_availability_group()` replay advancement with no partial-group exposure (§32F); the exact replay ordering key and its subordination of `event_time_utc`/`processing_time_utc` to `availability_time_utc` (§32G/§32H); stateless `replay()` Protocol compatibility (§32F); immutable snapshot semantics; exact Protocol conformance for all 3 classes (§32A); the exact 25-name export list and order (§32J); and the exact 31 new top-level test functions across 4 files, each meaningfully exercising its named behavior with no vacuous or tautological assertion (§32K).

**Verification results:** full suite `328 passed` (297 existing + 31 new); original baseline suite `34 passed`; combined `tests/unit/` top-level test-function count `236` (205 existing + 31 new, confirmed by direct AST parse — the higher pytest-collected count reflects pre-existing `@pytest.mark.parametrize` expansion in unrelated files, not a change to the approved top-level-function boundary); `market_data` public exports `25` (20 existing + 5 new, exact order); `uv lock --check` passes; `ruff format --check .` passes; `ruff check .` passes; `mypy src tests` passes with no issues.

**No dependency change. No Protocol change. No production approval granted by this record.**

**Next controlled action:** begin one combined **Market Measurements and Reference Structures Foundation** milestone — covering meaningful swings, displacement, equal-level clusters, and support/resistance/trendline reference structures — before POI and BTMM detection work begins, and before any future structure-state/transition milestone. That milestone is not started by this record.

## 33. Market Measurements and Reference Structures Foundation — Architecture and Exact Implementation Controls (Corrected)

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** (See §33AB for the author approval record and §33AC for the implementation, audit, and closure record.)

**Batch identifier: `1B-H-MEASUREMENTS`.** This section is a consolidated, documentation-only correction of the originally proposed `1B-H-STRUCTURE` architecture, resolving every blocking finding from the focused architectural audit in one pass. Nothing was implemented or committed under the prior identifier, so this is a rename plus correction, not a new milestone. This decision group defines one compact, accelerated milestone: a deterministic, versioned, no-look-ahead analytical foundation that transforms ordered `NormalizedCandle` sequences into candle/leg measurements and confirmed reference structures required by later structure-state, POI, and BTMM detectors. It consumes the completed market-data (`1B-C-MD`) and replay (`1B-G-REPLAY`) foundations and reuses their contracts unmodified.

### 33A. Purpose and Analysis Boundary

```
ordered NormalizedCandle sequence
  -> candle/leg measurements (Total Range, Body, Wicks, Wilder ATR(14), size/context ratios)
  -> confirmed meaningful swings
  -> displacement observations
  -> equal-level clusters
  -> support/resistance reference zones
  -> confirmed trendlines
  -> one immutable MarketMeasurementAnalysis snapshot
```

This milestone supplies **prerequisites** for future structure, POI, and BTMM engines. It does **not** implement the market-structure transition engine itself, and does **not** perform: market-structure state, HH/HL/LH/LL, Break of Structure, Change of Character, protected/weak swings, POI creation, order-block/FVG/candlestick-pattern creation, BTMM lifecycle detection, trade-signal creation, entry/stop-loss calculation, visualization, alerts, backtesting metrics, or execution.

### 33B. Authoritative Source Audit — What Is and Is Not Approved

Read directly, in full: `knowledge/MEASUREMENT_STANDARDS.md` (1,872 lines), `knowledge/AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`, `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`, `knowledge/btmm/BTMM_STATE_MACHINE.md`, and the implemented `contracts/normalized_candle.py`, `contracts/validation_result.py`, `contracts/provenance_record.py`, `contracts/rule_version_manifest.py`, `config/enums.py`.

**Approved standards this milestone reuses exactly, without modification:** Candle Measurement Standard V1 (Ambiguity 1); Small Candle and Recent Market Context Standard V1 (Ambiguity 2); Volume, Momentum, and Price-Activity Proxy Standard V1 (Ambiguity 3); Market Speed and Displacement Standard V1 — Provisional (Ambiguity 7); Meaningful Swing High and Swing Low Detection Standard V1 — Provisional (Ambiguity 10); Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional (Ambiguity 11); Support and Resistance Detection and Validation Standard V1 — Provisional (Ambiguity 12); Equal Highs and Equal Lows Tolerance and Drawing Standard V1 — Provisional (Ambiguity 5); POI Reaction Strength Standard V1 — Provisional (Ambiguity 9, reused generically for Support/Resistance origin-reaction gating only, never for any POI).

**Explicitly NOT approved and therefore NOT implemented — reserved for a later, separate `Structure State and Transition Foundation` milestone:** Higher High, Higher Low, Lower High, Lower Low, Break of Structure (BOS), Change of Character (CHoCH), protected high/low, weak high/low, and market-structure direction/state generally. `knowledge/market_structure/MARKET_ANALYSIS_COVERAGE_MATRIX.md`'s own governing rule states neither BOS nor CHoCH is adopted as a project rule unless the book defines it (it does not) or the author explicitly approves adding it. `REPOSITORY_SCAFFOLD_PLAN.md`'s `domain/` directory documentation already formally excludes them (`P0G-B003`). **This correction reserves, but does not create any inventory row for, that future milestone.** No threshold for these concepts is invented here.

Also explicitly deferred: automated Equal High/Low or Trendline "specialized lifecycle" (sweep, final invalidation, retest, reclaim, false break, role reversal, expiration — `P0G-B004`/`P0G-B005`); the full Ambiguity-15 POI Boundary Breach/Reclaim/Invalidation state machine (scoped to bounded directional POIs, shared machinery for later POI work).

### 33C. Three Resolved Sub-Decisions Required Before Implementation

1. **Wilder ATR(14) computation method** — fully specified in §33L, labeled `ENGINEERING-PROVISIONAL`, `AUTHOR-DECISION REQUIRED`.
2. **Minimum Price Tick** — a single required, caller-supplied `Decimal` scoped to the one symbol under analysis (§33M), no invented default.
3. **Deterministic non-overlapping Equal-Level cluster-formation algorithm** — fully specified step-by-step in §33I, labeled `ENGINEERING-PROVISIONAL`, `AUTHOR-DECISION REQUIRED`. None of the three is described as book-proven or empirically validated.

### 33D. Processing Model and Ordering Policy (Corrected — Policy A)

**Pure batch analysis over an immutable tuple.** `analyze_market_measurements()` accepts a complete `tuple[NormalizedCandle, ...]` for exactly one `InternalSymbol` and one `Timeframe`. **The analyzer requires canonically pre-sorted input and never silently sorts or normalizes it.** Canonical candle order:

```
(event_time_utc, record_id)
```

If the supplied tuple is not already in this exact order, `UnsortedCandleSequenceError` is raised. **No claim of insertion-order independence is made anywhere in this milestone** — the correct, single claim is: *deterministic output for the same valid, canonically ordered input*. Input order is a caller contract, not something the analyzer discovers or repairs.

**`event_time_utc` values must be strictly increasing.** Two distinct candle records (different `record_id`) sharing the same `event_time_utc` are ambiguous for bar-index arithmetic (pivot windows, ATR sequencing, trendline anchor spacing all assume exactly one candle per instant) and are rejected with `AmbiguousEventTimeAnalysisError` — this is a real, previously-unaddressed case, since `market_data`'s own repository/replay layer legitimately preserves `EXACT_DUPLICATE`/`CONFLICTING_REVISION` pairs sharing one `event_time_utc` (per the 1B-G-REPLAY 5-case duplicate/revision policy). The analyzer does not choose between such candidates — revision selection and eligibility filtering remain an explicit upstream caller responsibility, never performed inside this milestone.

**Replay integration requires no new engine and no new code path.** A caller consuming `InMemoryHistoricalReplaySource.advance_next_availability_group()` appends each returned group atomically to the visible canonical prefix and re-invokes `analyze_market_measurements()` on the longer prefix. Because there is exactly one deterministic engine, batch and replay results are identical **for the same visible candle prefix** — this is not a claim of equality *between* different prefixes (see §33E). The accepted O(n²)-across-a-full-replay-session cost (each checkpoint re-analyzes its full prefix) remains an explicit, documented, non-production tradeoff — an incremental-state optimization is a separate, future improvement, not built here.

### 33E. Snapshot Semantics (Corrected)

`MarketMeasurementAnalysis` is **a current analytical snapshot for exactly the supplied candle prefix** — never an append-only event stream, a lifecycle history, or a revision ledger. No public lifecycle-rewriting or event-history contract is implemented in this milestone.

Across growing prefixes:
- an output may newly appear once its confirming candle(s) become available;
- a snapshot object's content may change where the approved algorithm legitimately grows it (e.g. an `EqualLevelCluster` gaining a member);
- an output whose **semantic key** is unchanged retains the same `record_id` (§33H);
- changed complete content always produces a different `content_fingerprint` (§33H);
- no historical event log or supersession chain is claimed or exposed;
- **batch/replay equivalence means equality for the same visible candle prefix — not equality between different prefixes.**

### 33F. No-Look-Ahead Policy

`output.availability_time_utc` = the latest `availability_time_utc` among all candles required to confirm that output. No result exists before its confirmation candle becomes available. No event-time-only release. No processing-time substitution. No future candle access.

| Output | `availability_time_utc` source |
|---|---|
| `ConfirmedSwing` | `meaningful_confirmation_time_utc` |
| `DisplacementObservation` | the candidate candle's own `availability_time_utc` |
| `EqualLevelCluster` | `confirmation_time_utc` (the latest member swing's own `meaningful_confirmation_time_utc`) |
| `SupportResistanceZone` | `confirmation_time_utc` (the confirming touch's candle availability) |
| `Trendline` | `confirmation_time_utc` (the third qualifying touch's candle availability) |

Multiple outputs confirmed at the same instant are released together in the analyzer's one deterministic pass, in the aggregate's fixed field order (§33K); no output is ever exposed via a partial mid-instant state.

### 33G. Analytical Eligibility Boundary (Corrected — Explicit)

`NormalizedCandle` structural validity does **not** imply `AnalyticalEligibility.ELIGIBLE`. `ValidationResult`/`ValidationStatus`/`AnalyticalEligibility` (`contracts/validation_result.py`) are a wholly separate contract family. `analyze_market_measurements()` receives only `candles: tuple[NormalizedCandle, ...]` — it never receives, inspects, or infers `ValidationStatus` or `AnalyticalEligibility`. The analyzer processes exactly the structurally-valid candles the caller supplies; **the caller is responsible for any eligibility gating and for revision selection among conflicting candles before calling this analyzer.** Repository membership (per `1B-G-REPLAY`'s own §32C three-axis distinction) does not imply analytical eligibility here either. A future validation-join/orchestration layer that combines `NormalizedCandle` with `ValidationResult` remains explicitly deferred and out of this milestone's scope.

### 33H. Output Identity, Fingerprint, and Versioning Policy (Corrected)

No random UUID generation anywhere in this milestone's code. The originally proposed stateful `next_record_id()`/`next_content_fingerprint()` provider is **removed** — a stateful, call-order-dependent generator cannot guarantee identity stability across the different numbers/orders of calls that a one-shot batch analysis versus an incrementally-built replay session would make before reaching the same final prefix.

**Replacement: a pure, content-addressed identity provider.**

```python
class DerivedOutputType(StrEnum):
    CONFIRMED_SWING = "CONFIRMED_SWING"
    DISPLACEMENT_OBSERVATION = "DISPLACEMENT_OBSERVATION"
    EQUAL_LEVEL_CLUSTER = "EQUAL_LEVEL_CLUSTER"
    SUPPORT_RESISTANCE_ZONE = "SUPPORT_RESISTANCE_ZONE"
    TRENDLINE = "TRENDLINE"

class DerivedOutputIdentityProvider(Protocol):
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID: ...
```

**Contract:** synchronous; referentially stable — the same `(output_type, semantic_key)` pair must return the same `UUIDv7`, regardless of call count or call order; repeated batch runs reproduce identities; growing-prefix replay preserves identities for every output whose semantic key is unchanged; no random generation occurs inside the analyzer itself — the caller's provider is solely responsible for deterministic minting (e.g. a canonical-hash-derived UUIDv7, or a caller-maintained idempotent lookup). Every `semantic_key` tuple element is a `str` — UUID components use the canonical lowercase-hyphenated form, `SemVer` components use its canonical string form. If a provider returns the same `UUIDv7` for two different semantic keys within one `analyze_market_measurements()` call, the analyzer raises `DerivedIdentityCollisionError`. Semantic keys, exactly, per output type:

```
CONFIRMED_SWING:
    (symbol.value, timeframe.value, swing_type.value,
     source_candle_id, confirmation_candle_id, rule_version)

DISPLACEMENT_OBSERVATION:
    (symbol.value, timeframe.value, source_candle_id, rule_version)

EQUAL_LEVEL_CLUSTER:
    (symbol.value, timeframe.value, cluster_type.value,
     first_seed_swing_id, second_seed_swing_id, rule_version)

SUPPORT_RESISTANCE_ZONE:
    (symbol.value, timeframe.value, zone_type.value,
     origin_swing_id, confirmation_candle_id, rule_version)

TRENDLINE:
    (symbol.value, timeframe.value, orientation.value,
     first_anchor_swing_id, second_anchor_swing_id,
     confirmation_candle_id, rule_version)
```

Note deliberately: a semantic key never includes mutable fields (e.g. `EqualLevelCluster`'s later-joining members beyond the two seeds) — this is precisely what lets `record_id` stay stable while `content_fingerprint` changes as a snapshot object legitimately grows (§33E).

**Content fingerprint (corrected — analyzer-computed, not caller-supplied).** `content_fingerprint` is computed by the analyzer itself: SHA-256 of the canonical complete public output content, excluding only `record_id` and `content_fingerprint`. Canonical representation: fixed contract field order; enums as `.value`; UUIDs as canonical lowercase-hyphenated strings; `Decimal` as `format(value.normalize(), "f")` with negative zero normalized to `"0"`; `datetime` converted to UTC, ISO-8601 with microseconds and trailing `Z`; `SemVer` as its canonical string; tuples as ordered JSON arrays; `None` as `null`; `bool` as JSON `true`/`false`; integers as decimal integers; UTF-8 JSON; no extra whitespace; separators exactly `(",", ":")`; no unordered mappings anywhere in public analytical content. The fingerprint includes every public content field — evidence classification, rule/contract/schema version, and the complete current snapshot content — so: identical complete content always produces the same fingerprint; any changed member tuple, measurement, confirmation field, or version produces a different fingerprint; `record_id` may remain stable while `content_fingerprint` changes for an evolving snapshot object sharing the same semantic key. **No caller-provided opaque value is ever claimed to prove content integrity — the fingerprint's meaning is exactly this specified canonical hash, nothing else.**

`provenance_id: UUIDv7` on every output remains a caller-supplied pointer to an external `ProvenanceRecord`, mirroring `RawCandle`/`NormalizedCandle`'s own convention — no `ProvenanceRecord`/`RuleVersionManifest` instance is constructed by this milestone's code.

### 33I. Meaningful Swing Contracts (`domain/swings.py`) — Corrected

Reuses the Meaningful Swing High and Swing Low Detection Standard V1 — Provisional exactly. `SwingStrength`/`STRONG_SWING` are **removed entirely** from this milestone — the standard's own "materially breached" qualifier for `STRONG_SWING` has no numeric definition anywhere in the approved standards, and per the principle "do not expose a strength enum value whose required rule is knowingly absent," this milestone emits only fully-approved-rule swings, with no strength classification at all. `STRONG_SWING` remains a candidate for a future milestone once "materially breached" is itself resolved as its own tracked author decision.

```python
class SwingType(StrEnum):
    SWING_HIGH = "SWING_HIGH"
    SWING_LOW = "SWING_LOW"

class ConfirmedSwing(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    swing_type: SwingType
    pivot_price: Decimal
    pivot_bar_index: int
    pivot_candle_record_ids: tuple[UUIDv7, ...]
    pivot_start_time_utc: datetime
    pivot_end_time_utc: datetime
    local_confirmation_time_utc: datetime
    meaningful_confirmation_time_utc: datetime
    confirmation_candle_id: UUIDv7
    pivot_reference_atr: Decimal
    pivot_tie_tolerance: Decimal
    reversal_threshold: Decimal
    reversal_excursion: Decimal
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

`source_candle_id` (the semantic-key component) is `pivot_candle_record_ids[0]` — the plateau's first/opening candle, a stable deterministic single-id reference. Only confirmed swings are emitted (no `FORMING`/`LOCAL_SWING_CANDIDATE`/`SUPERSEDED` records; superseded-candidate audit-trail persistence remains a documented future enhancement).

**Explicit boundary rules (previously undocumented, now stated):** the first two candles of any supplied prefix can never be pivot candidates (no room for the required 2-candle left side); the final two candles of any supplied prefix can never yet be locally confirmed (no room for the required 2-candle right side) — both are structural consequences of the five-candle local pivot window, re-evaluated identically on every longer prefix. **Simultaneous high-and-low qualification:** if one candle's window makes it simultaneously the qualifying local extreme for both a swing high and a swing low, **neither is emitted** — this ambiguous case is excluded rather than arbitrarily resolved by candle color, body, or later price action, preserving the mandatory alternating Swing High/Swing Low sequence.

### 33J. Displacement Contracts (`domain/displacement.py`) — Corrected

Reuses only the single-candle-level portion of the Market Speed and Displacement Standard V1 — Provisional (§2). The shared leg-measurement primitives it and Support/Resistance's origin-reaction gating both need remain in `measurements/legs.py` (§6–§7 of the same standard), avoiding duplication.

```python
class DisplacementDirection(StrEnum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"

class DisplacementClassification(StrEnum):
    NORMAL = "NORMAL"
    FAST = "FAST"
    VERY_FAST = "VERY_FAST"

class DisplacementObservation(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    candle_record_id: UUIDv7
    event_time_utc: datetime
    availability_time_utc: datetime
    total_range: Decimal
    range_speed_ratio: Decimal
    direction: DisplacementDirection
    classification: DisplacementClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

`direction` is `BULLISH` when `close >= open`, else `BEARISH` — a deterministic tie-break for the doji boundary, not an invented threshold. `source_candle_id` (semantic key) = `candle_record_id`. **Zero-total-range candles are safe by construction:** `range_speed_ratio = 0` and `classification = NORMAL` always — no division by zero. No observation is emitted before the 20-candle preceding baseline exists (candle-level `range_speed_ratio` uses the median-range baseline, not ATR, so it is independent of the ATR warm-up window in §33L). An observation is never labeled "institutional" — only `NORMAL`/`FAST`/`VERY_FAST`.

### 33K. Equal-Level Cluster Contracts (`domain/equal_levels.py`) — Corrected, Liquidity Merged In

Reuses the Equal Highs and Equal Lows Tolerance and Drawing Standard V1 — Provisional (§4 tolerance, §5/§6 boundaries) exactly, plus the fully-specified deterministic cluster-formation algorithm below. **The separate `LiquidityReference` contract is removed** — as originally specified it duplicated `EqualLevelCluster` with zero new information (`liquidity_side` is a pure function of `cluster_type`; `reference_price` duplicated an existing boundary). Liquidity expectation is now exposed as computed properties on `EqualLevelCluster` itself.

```python
class EqualLevelType(StrEnum):
    EQUAL_HIGH = "EQUAL_HIGH"
    EQUAL_LOW = "EQUAL_LOW"

class EqualLevelCluster(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    cluster_type: EqualLevelType
    component_swing_record_ids: tuple[UUIDv7, ...]
    cluster_spread: Decimal
    equality_tolerance: Decimal
    reference_atr: Decimal
    zone_bottom: Decimal
    zone_top: Decimal
    representative_price: Decimal
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7

    @property
    def liquidity_side(self) -> str: ...   # "ABOVE_PRICE" for EQUAL_HIGH, "BELOW_PRICE" for EQUAL_LOW
    @property
    def reference_price(self) -> Decimal: ...  # == representative_price
```

**Exact deterministic non-overlapping cluster-formation algorithm** (`ENGINEERING-PROVISIONAL`, `AUTHOR-DECISION REQUIRED` — a grouping procedure, not a new numeric threshold; the approved Equality Tolerance formula is reused unmodified):

Process confirmed swings separately by type (`HIGH` swings only ever cluster with `HIGH` swings; `LOW` only with `LOW`), in canonical `(event_time_utc, record_id)` order:

1. Select the earliest unconsumed same-type swing as the seed.
2. Select the next unconsumed same-type swing.
3. A cluster requires at least two swings; the first two form a cluster only if their full prospective price spread satisfies the approved Equality Tolerance formula.
4. Once a cluster exists, scan later same-type swings in order. For each candidate: `prospective_spread = max(current member prices, candidate price) − min(current member prices, candidate price)`.
5. Add the candidate only when `prospective_spread ≤ equality_tolerance` (the running spread over the **entire current member set**, not merely the newest pair).
6. On the first failing candidate: close the current cluster; the failing candidate becomes the seed of the next candidate cluster.
7. **A swing belongs to at most one cluster; no overlapping clusters; no retroactive reuse of the last member of an already-closed cluster.**
8. At the end of the supplied prefix: emit the active cluster only if it has ≥ 2 members; a lone open seed emits nothing.
9. `representative_price = (zone_bottom + zone_top) / Decimal(2)`; `zone_bottom` = minimum member price; `zone_top` = maximum member price; `component_swing_record_ids` preserve chronological order.

**Worked transitive-chain example** (A within tolerance of B; B within tolerance of C; A *not* within tolerance of C): result is cluster `{A, B}` (closed and emitted), and C begins the next candidate cluster — B is never reused, and no overlapping `{B, C}` cluster is ever formed.

**Prefix-growth stability:** an *active* (not-yet-closed) end-of-prefix cluster may gain members in a later, longer-prefix snapshot re-analysis — its semantic ID stays stable (keyed by its first two seed swings), its `content_fingerprint` changes as membership changes (§33H). **A closed cluster is never reopened, regardless of what a longer prefix later reveals** — this is what preserves non-repainting.

Semantic-key components: `first_seed_swing_id`/`second_seed_swing_id` = the two swings that originally formed the cluster (its first two members, permanently fixed even if later members join). `NOT_EQUAL` candidates (spread beyond tolerance, or a lone seed) are never emitted.

### 33L. Wilder ATR(14) Gap-Fill — Fully Specified (`measurements/atr.py`)

**`ENGINEERING-PROVISIONAL`, `AUTHOR-DECISION REQUIRED`.** `period = 14`, fixed.

```
True Range:
  TR[0] = high[0] - low[0]
  TR[i] = max(high[i] - low[i],
              abs(high[i] - close[i-1]),
              abs(low[i]  - close[i-1]))   for i > 0

Warm-up:
  ATR is unavailable for indices 0 through 12.
  First ATR is available at index 13 (seed):
    ATR[13] = sum(TR[0:14]) / Decimal(14)

Recurrence, for i >= 14:
  ATR[i] = (ATR[i-1] * Decimal(13) + TR[i]) / Decimal(14)
```

`Decimal` only, no `float` conversion at any step; no quantization; no manual rounding; finite values only; `ATR = 0` is permitted where every seed range is genuinely zero. No detector consumes a `pivot_reference_atr`/`creator_reference_atr`/`anchor_reference_atr` value before index 13 exists for the relevant candle — this cascades as a real, now-explicit minimum-history floor (15 candles: 1 previous-close reference + 14 True Range values) into every ATR-consuming detector (swings, support/resistance, trendlines). Displacement's `range_speed_ratio` does **not** depend on ATR (median-baseline only, §33J) and is unaffected by this floor. This method is recorded as provisional — not empirically validated, not production-approved.

### 33M. Configuration and Threshold Provenance (`domain/configuration.py`) — Corrected

```python
class MarketMeasurementConfiguration(ContractModel):
    minimum_price_tick: Decimal

    atr_period: int = 14
    range_context_window: int = 20

    pivot_tie_tolerance_atr_multiplier: Decimal = Decimal("0.02")
    meaningful_reversal_atr_multiplier: Decimal = Decimal("0.50")

    equal_level_tolerance_atr_multiplier: Decimal = Decimal("0.10")

    trendline_min_anchor_spacing_bars: int = 5
    trendline_horizontal_atr_multiplier: Decimal = Decimal("0.02")
    trendline_too_steep_atr_multiplier: Decimal = Decimal("0.35")
    trendline_touch_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    trendline_pierce_tolerance_atr_multiplier: Decimal = Decimal("0.20")

    support_resistance_zone_depth_atr_multiplier: Decimal = Decimal("0.10")
    support_resistance_touch_tolerance_atr_multiplier: Decimal = Decimal("0.05")
    support_resistance_pierce_tolerance_atr_multiplier: Decimal = Decimal("0.15")

    displacement_fast_ratio: Decimal = Decimal("1.50")
    displacement_very_fast_ratio: Decimal = Decimal("2.00")

    reaction_window_bars: int = 5
    reaction_standard_atr_ratio: Decimal = Decimal("0.75")
    reaction_standard_zone_clearance_ratio: Decimal = Decimal("1.00")
    reaction_standard_directional_efficiency: Decimal = Decimal("0.50")
    reaction_standard_directional_candle_share: Decimal = Decimal("0.60")
    reaction_strong_atr_ratio: Decimal = Decimal("1.25")
    reaction_strong_zone_clearance_ratio: Decimal = Decimal("1.50")
    reaction_strong_directional_efficiency: Decimal = Decimal("0.60")
    reaction_strong_directional_candle_share: Decimal = Decimal("0.67")

    leg_fast_normalized_speed_per_bar: Decimal = Decimal("0.50")
    leg_fast_directional_efficiency: Decimal = Decimal("0.60")
    leg_fast_directional_candle_share: Decimal = Decimal("0.67")
    leg_strong_fast_normalized_speed_per_bar: Decimal = Decimal("0.75")
    leg_strong_fast_directional_efficiency: Decimal = Decimal("0.75")
    leg_strong_fast_directional_candle_share: Decimal = Decimal("0.80")

    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = EvidenceClassification.ENGINEERING_PROVISIONAL
```

**`minimum_price_tick` is corrected to a single required `Decimal` field** (replacing the original three per-symbol fields) — since the analyzer already hard-rejects mixed-symbol input, one tick value scoped to the single symbol under analysis is sufficient and simpler; no default, must be strictly greater than zero, finite, `Decimal` only, no broker-precision inference, no `float`, not timeframe-specific. The caller supplies the correct tick for whichever of XAUUSD/EURUSD/GBPUSD is being analyzed in that call. This configuration shape requires explicit author confirmation but is not itself a market threshold. Every multiplier value is copied verbatim from its cited `MEASUREMENT_STANDARDS.md` section (§33I–§33K, §33L cite the exact section per contract/gap-fill). `strong_swing_atr_multiplier` and all `equal_level_strong_atr_multiplier`/`equal_level_standard_atr_multiplier` fields are removed along with the strength classifications they fed (§33I, §33K). `Decimal` throughout, no `float`. Threshold classification for every field: `AUTHOR-APPROVED`, `ENGINEERING-PROVISIONAL` — none is claimed `EMPIRICALLY-CALIBRATED`, `OUT-OF-SAMPLE-VALIDATED`, or `PRODUCTION-APPROVED`.

### 33N. Support and Resistance Contracts (`domain/support_resistance.py`) — Corrected, Confirmed-Only

Reuses the Support and Resistance Detection and Validation Standard V1 — Provisional exactly for origin eligibility, fixed creator-based boundaries, origin-reaction gating (reusing the POI Reaction Strength Standard's formulas generically against the zone's own boundaries, never against any POI), and distinct-touch confirmation. **Corrected scope: this milestone emits only fully confirmed immutable reference zones — no `DRAFT`, `STRONG`, or `*_BREAK_CANDIDATE` status is ever publicly exposed.** `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` is the literal entry point into the still-deferred Ambiguity-15 lifecycle; emitting it with no path to ever resolve what follows would be a dangling signal. Internal candidate tracking (DRAFT-equivalent working state) may exist privately during detection but is never exported or emitted.

```python
class SupportResistanceType(StrEnum):
    SUPPORT = "SUPPORT"
    RESISTANCE = "RESISTANCE"

class SupportResistanceZone(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    zone_type: SupportResistanceType
    origin_swing_record_id: UUIDv7
    creator_reference_atr: Decimal
    zone_depth: Decimal
    zone_top: Decimal
    zone_bottom: Decimal
    qualifying_touch_swing_record_ids: tuple[UUIDv7, ...]
    confirmation_candle_id: UUIDv7
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

A zone is emitted only once it reaches the standard's `CONFIRMED_SUPPORT`/`CONFIRMED_RESISTANCE` threshold (origin + at least one additional distinct qualifying touch, `qualifying_touch_swing_record_ids` therefore always has ≥ 1 entry); `confirmation_candle_id` is the confirming touch's candle. A zone whose origin reaction is only `WEAK_REACTION` is never created. Touch *count* beyond the minimum (informally "strong") remains fully recoverable by a downstream consumer from `len(qualifying_touch_swing_record_ids)` — no separate strength status is needed or exposed. A zone is a bounded price representation (`zone_top`/`zone_bottom`), never a single price; one contract covers both Support and Resistance via `zone_type`. A confirmed zone's public content never mutates because of later touches within this milestone — later touches, break candidates, reclaim, invalidation, and the full Ambiguity-15 lifecycle all remain deferred to a future Lifecycle Foundation milestone.

### 33O. Trendline Contracts (`domain/trendlines.py`) — Corrected, Confirmed-Only

Reuses the Bullish and Bearish Trendline Detection and Validation Standard V1 — Provisional exactly for anchor eligibility, ≥5-bar spacing, the slope equation, Normalized-Slope steepness rejection, inter-anchor integrity, and touch/pierce tolerances. **Corrected scope: emits only a fully confirmed trendline reference — no `DRAFT`, `STRONG`, `BREAK_CANDIDATE`, `BROKEN`, or `INVALIDATED` status is ever publicly exposed.** Break and lifecycle detection remain deferred (Trendlines were already explicitly excluded from Ambiguity-15's scope). `TrendlineSlopeClassification` is also removed — since only `VALID_SLOPE` anchor pairs ever reach a confirmed trendline, a single-value-forever public enum added no information.

```python
class TrendlineOrientation(StrEnum):
    BULLISH_TRENDLINE = "BULLISH_TRENDLINE"
    BEARISH_TRENDLINE = "BEARISH_TRENDLINE"

class Trendline(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    orientation: TrendlineOrientation
    anchor_1_swing_record_id: UUIDv7
    anchor_2_swing_record_id: UUIDv7
    anchor_1_price: Decimal
    anchor_2_price: Decimal
    anchor_1_bar_index: int
    anchor_2_bar_index: int
    raw_slope: Decimal
    anchor_reference_atr: Decimal
    normalized_slope: Decimal
    qualifying_touch_swing_record_ids: tuple[UUIDv7, ...]
    confirmation_candle_id: UUIDv7
    confirmation_time_utc: datetime
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

A `Trendline` is emitted only once a third distinct qualifying touch confirms it (`qualifying_touch_swing_record_ids` always has ≥ 1 entry — the touches beyond the two anchors); `confirmation_candle_id` is the third touch's candle. **Slope units, made explicit (previously implicit only in the formula):** `raw_slope` is **price per candle-index step** — never price per unit time. The x-coordinate is the candle's zero-based sequence index in the analyzed canonical input, not a timestamp:

```
raw_slope = (anchor_2_price - anchor_1_price)
            / Decimal(anchor_2_bar_index - anchor_1_bar_index)
```

The denominator is always strictly positive (the ≥5-bar minimum-spacing rule structurally prevents zero/negative distance — no division-by-zero risk). `Decimal` throughout, no `float`. Multiple competing candidate trendlines are preserved independently, deterministically ordered by `(anchor_1_bar_index, anchor_2_bar_index, anchor_1_swing_record_id)`; none is ever ranked "best," merged, or silently dropped. Trendlines remain reference structures, never bounded POIs.

### 33P. Public API and Error Vocabulary (`domain/analyzer.py`) — Corrected, Renamed

```python
def analyze_market_measurements(
    candles: tuple[NormalizedCandle, ...],
    configuration: MarketMeasurementConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> MarketMeasurementAnalysis: ...
```

Exactly 7 `ValueError` subclasses, defined once in `domain/analyzer.py`:

1. `MixedSymbolAnalysisError` — mixed-symbol input.
2. `MixedTimeframeAnalysisError` — mixed-timeframe input.
3. `UnsortedCandleSequenceError` — input not in canonical `(event_time_utc, record_id)` order (§33D).
4. `DuplicateCandleRecordError` — any repeated `record_id` in the input.
5. `AmbiguousEventTimeAnalysisError` — two distinct records sharing one `event_time_utc` (§33D, new).
6. `InvalidMarketMeasurementConfigurationError` — invalid/missing configuration (defense-in-depth; structurally guarded by required fields).
7. `DerivedIdentityCollisionError` — identity provider returns one `UUIDv7` for two different semantic keys in one call (§33H, new).

Behavior: empty tuple → a valid empty `MarketMeasurementAnalysis` (`symbol = None`, `timeframe = None`, `analyzed_candle_count = 0`, every output tuple empty), never an exception; insufficient history for any one output family → that family's tuple is empty, others populate normally; "unsupported analytical condition" is never a generic exception — each standard's own closed-vocabulary rejection is handled by simply not emitting a record.

### 33Q. Aggregate Result (`domain/analyzer.py`) — Corrected Field Order

```python
class MarketMeasurementAnalysis(ContractModel):
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    analyzed_candle_count: int
    confirmed_swings: tuple[ConfirmedSwing, ...]
    displacement_observations: tuple[DisplacementObservation, ...]
    equal_level_clusters: tuple[EqualLevelCluster, ...]
    support_resistance_zones: tuple[SupportResistanceZone, ...]
    trendlines: tuple[Trendline, ...]
```

`liquidity_references` is removed (§33K). No POI, BTMM, or structure-transition field exists anywhere in this contract or any of its members.

### 33R. Batch/Replay Equivalence Procedure (New, Fully Specified)

For each replay availability group: (1) append the full group atomically to the visible canonical prefix; (2) call `analyze_market_measurements()` on that prefix; (3) independently call direct batch analysis on the identical prefix, using the same deterministic `DerivedOutputIdentityProvider`; (4) compare the complete `MarketMeasurementAnalysis` values — they must be equal; (5) verify every unchanged semantic key retains its `record_id`; (6) verify every changed complete content changes its `content_fingerprint`; (7) verify no future candle affected the result; (8) verify a permutation *inside* one availability group cannot occur, since the visible prefix is always canonical by `event_time_utc` (§33D) regardless of the group's internal delivery order from the replay source.

### 33S. Protocol and Replay Integration Audit

No modification to any existing `market_data` Protocol — `RawCandleSink`, `NormalizedCandleSink`, `CandleReadRepository`, `HistoricalReplaySource` are untouched. This milestone consumes `NormalizedCandle` directly from `contracts/normalized_candle.py`, never from `market_data`. The one new Protocol, `DerivedOutputIdentityProvider`, is local to `domain/analyzer.py`; it is intentionally not `@runtime_checkable`, matching every other Protocol in this codebase, and conformance is verified structurally, never via `isinstance()`/`issubclass()`.

### 33T. Dependency-Direction Correction to `REPOSITORY_SCAFFOLD_PLAN.md`

Unchanged from the original proposal: `measurements/` depends on `contracts`, `config` only; `domain/` depends on `measurements`, `contracts`, `config` only — correcting a Phase-1A drafting gap that predates the `market_data`/`contracts` package split. No other directory's documented dependency direction is touched.

### 33U. Exact File Scope — 22 New Paths, 0 Modified (Renamed, Same Count)

**13 new source paths** (unchanged filenames; corrected contents per §33H–§33Q):

| # | Path | Contents |
|---|---|---|
| 1 | `src/btmm_ai_scanner/measurements/__init__.py` | Package marker, 10 exports |
| 2 | `src/btmm_ai_scanner/measurements/candle_metrics.py` | Total Range, Body, wick shares, close positions, size ratio, range context ratio |
| 3 | `src/btmm_ai_scanner/measurements/atr.py` | Wilder ATR(14), fully specified (§33L) |
| 4 | `src/btmm_ai_scanner/measurements/legs.py` | Shared leg-measurement primitives, FAST/STRONG_FAST/SLOW_OR_UNCLEAR classification |
| 5 | `src/btmm_ai_scanner/domain/__init__.py` | Package marker, 23 exports (§33W) |
| 6 | `src/btmm_ai_scanner/domain/configuration.py` | `MarketMeasurementConfiguration` (§33M) |
| 7 | `src/btmm_ai_scanner/domain/enums.py` | `SwingType`, `DisplacementDirection`, `DisplacementClassification`, `EqualLevelType`, `SupportResistanceType`, `TrendlineOrientation`, `DerivedOutputType` |
| 8 | `src/btmm_ai_scanner/domain/swings.py` | `ConfirmedSwing` + detection (§33I) |
| 9 | `src/btmm_ai_scanner/domain/displacement.py` | `DisplacementObservation` + detection (§33J) |
| 10 | `src/btmm_ai_scanner/domain/equal_levels.py` | `EqualLevelCluster` (liquidity properties merged in) + detection (§33K) |
| 11 | `src/btmm_ai_scanner/domain/support_resistance.py` | `SupportResistanceZone` + detection (§33N) |
| 12 | `src/btmm_ai_scanner/domain/trendlines.py` | `Trendline` + detection (§33O) |
| 13 | `src/btmm_ai_scanner/domain/analyzer.py` | `DerivedOutputIdentityProvider`, 7 exceptions, `MarketMeasurementAnalysis`, `analyze_market_measurements` (§33H, §33P–§33Q) |

**9 new test paths (§33V), one renamed relative to the original proposal:** `tests/unit/test_market_structure_configuration.py` → `tests/unit/test_market_measurement_configuration.py`; the remaining 8 filenames are unchanged. **0 modified existing paths.** Creation order 76–97, unchanged.

### 33V. Exact Test Coverage — 70 New Top-Level Test Functions (Corrected)

**`tests/unit/test_market_measurement_configuration.py` — 6:**
1. `test_market_measurement_configuration_default_values_match_approved_standards`
2. `test_market_measurement_configuration_is_frozen_and_immutable`
3. `test_market_measurement_configuration_requires_minimum_price_tick_with_no_default`
4. `test_market_measurement_configuration_rejects_non_positive_minimum_price_tick`
5. `test_market_measurement_configuration_rejects_non_positive_atr_period`
6. `test_market_measurement_configuration_rejects_non_positive_range_context_window`

**`tests/unit/test_confirmed_swings.py` — 10:**
1. `test_confirmed_swing_detection_confirms_swing_high_after_meaningful_reversal`
2. `test_confirmed_swing_detection_confirms_swing_low_after_meaningful_reversal`
3. `test_confirmed_swing_detection_handles_adjacent_pivot_plateau_as_one_swing`
4. `test_confirmed_swing_detection_supersedes_unconfirmed_candidate_with_more_extreme_price`
5. `test_confirmed_swing_detection_never_exposes_a_swing_before_meaningful_confirmation_time`
6. `test_confirmed_swing_detection_alternates_swing_high_and_swing_low`
7. `test_confirmed_swing_detection_excludes_first_and_last_two_candles_from_pivot_eligibility`
8. `test_confirmed_swing_detection_emits_neither_direction_for_simultaneous_high_and_low_qualification`
9. `test_confirmed_swing_detection_derives_pivot_reference_atr_from_wilder_seed_and_recurrence`
10. `test_confirmed_swing_detection_returns_empty_tuple_when_atr_is_not_yet_available`

**`tests/unit/test_displacement.py` — 6:**
1. `test_displacement_detection_classifies_normal_range_speed`
2. `test_displacement_detection_classifies_fast_range_speed`
3. `test_displacement_detection_classifies_very_fast_range_speed`
4. `test_displacement_detection_excludes_candidate_candle_from_its_own_baseline`
5. `test_displacement_detection_classifies_zero_range_candle_as_normal_without_division_error`
6. `test_displacement_detection_assigns_bullish_or_bearish_direction`

**`tests/unit/test_equal_levels.py` — 9:**
1. `test_equal_level_cluster_confirms_equal_highs_within_tolerance`
2. `test_equal_level_cluster_confirms_equal_lows_within_tolerance`
3. `test_equal_level_cluster_rejects_spread_beyond_tolerance`
4. `test_equal_level_cluster_resolves_transitive_chain_without_forming_an_invalid_cluster`
5. `test_equal_level_cluster_prevents_swing_reuse_across_clusters`
6. `test_equal_level_cluster_requires_distinct_confirmed_meaningful_swings`
7. `test_equal_level_cluster_growth_retains_record_id_and_changes_content_fingerprint`
8. `test_equal_level_cluster_liquidity_side_is_a_computed_property_not_a_separate_object`
9. `test_equal_level_cluster_representative_price_is_the_zone_midpoint`

**`tests/unit/test_support_resistance.py` — 10:**
1. `test_support_resistance_zone_boundaries_derive_from_origin_swing_and_horizontal_depth`
2. `test_support_zone_confirms_after_second_distinct_qualifying_touch`
3. `test_resistance_zone_confirms_after_second_distinct_qualifying_touch`
4. `test_support_resistance_zone_rejects_origin_with_only_weak_reaction`
5. `test_support_resistance_zone_requires_opposite_swing_between_same_type_touches`
6. `test_support_resistance_zone_never_emits_draft_or_break_candidate_status`
7. `test_support_resistance_zone_boundaries_never_move_after_creation`
8. `test_support_resistance_zone_preserves_multiple_independent_candidates`
9. `test_support_resistance_zone_touch_count_is_recoverable_from_qualifying_touch_ids`
10. `test_support_resistance_zone_semantic_identity_is_stable_across_growing_prefixes`

**`tests/unit/test_trendlines.py` — 10:**
1. `test_trendline_requires_two_confirmed_meaningful_swing_anchors`
2. `test_trendline_rejects_anchors_within_pivot_tie_tolerance_as_horizontal_candidate`
3. `test_trendline_rejects_anchors_closer_than_minimum_bar_spacing`
4. `test_trendline_classifies_valid_slope`
5. `test_trendline_rejects_too_steep_slope`
6. `test_trendline_rejects_anchor_pair_on_pierce_tolerance_violation`
7. `test_trendline_confirms_after_third_qualifying_touch`
8. `test_trendline_preserves_multiple_competing_candidates_without_ranking`
9. `test_trendline_slope_is_price_per_candle_index_not_price_per_time`
10. `test_trendline_never_emits_draft_or_break_candidate_status`

**`tests/unit/test_analyzer_api.py` — 8:**
1. `test_analyze_market_measurements_rejects_mixed_symbol_input`
2. `test_analyze_market_measurements_rejects_mixed_timeframe_input`
3. `test_analyze_market_measurements_rejects_unsorted_input`
4. `test_analyze_market_measurements_rejects_duplicate_record_id_input`
5. `test_analyze_market_measurements_rejects_ambiguous_tied_event_time_input`
6. `test_analyze_market_measurements_rejects_missing_instrument_metadata`
7. `test_analyze_market_measurements_returns_empty_aggregate_for_empty_input`
8. `test_analyze_market_measurements_is_deterministic_across_repeated_calls`

**`tests/unit/test_batch_replay_equivalence.py` — 6:**
1. `test_batch_and_replay_produce_identical_confirmed_swings_for_the_same_prefix`
2. `test_batch_and_replay_produce_identical_trendlines_for_the_same_prefix`
3. `test_batch_and_replay_produce_identical_support_resistance_zones_for_the_same_prefix`
4. `test_unchanged_semantic_keys_retain_the_same_record_id_across_growing_prefixes`
5. `test_replay_group_ingestion_processes_simultaneous_availability_candles_together`
6. `test_identity_provider_raises_on_semantic_key_collision_within_one_call`

**`tests/unit/test_domain_exports.py` — 5:**
1. `test_measurements_and_domain_exports_import_successfully`
2. `test_domain_exports_exact_23_names_and_order`
3. `test_measurements_exports_exact_names_and_order`
4. `test_domain_contracts_expose_no_poi_btmm_or_structure_transition_fields`
5. `test_domain_aggregate_field_order_matches_approved_contract`

**Total new: 70** (6+10+6+9+10+10+8+6+5, unchanged distribution). No test classes, no generated tests, no helper beginning with `test_`, no skip/xfail, no vacuous assertion. **Combined with the existing 250 (AST-verified top-level test functions, corrected from a stale 236 baseline predating the `1B-G-REPLAY` test files): 320.** Full pytest-collected total (including pre-existing parametrized cases unrelated to this milestone): 398. Coverage mapping note: several closely related required-behaviors are verified together within one richer test rather than one-test-per-bullet (e.g. ATR seed **and** recurrence in `test_confirmed_swing_detection_derives_pivot_reference_atr_from_wilder_seed_and_recurrence`); "call-order independence" and "same content produces the same fingerprint" are verified as direct corollaries of `test_analyze_market_measurements_is_deterministic_across_repeated_calls` rather than by separate dedicated tests; the analytical-eligibility boundary (§33G) is a documentation-verified structural guarantee (the analyzer's signature has no `ValidationResult` parameter at all), not something a runtime test can meaningfully assert against.

### 33W. Public Exports — Corrected

**`measurements/__init__.py` — unchanged, 10 names:** `total_range`, `body`, `body_efficiency`, `upper_wick`, `lower_wick`, `bullish_close_position`, `bearish_close_position`, `median_total_range`, `range_speed_ratio`, `compute_atr_series`.

**`domain/__init__.py` — corrected, exactly 23 names, in this order:**
1. `SwingType`
2. `DisplacementDirection`
3. `DisplacementClassification`
4. `EqualLevelType`
5. `SupportResistanceType`
6. `TrendlineOrientation`
7. `DerivedOutputType`
8. `ConfirmedSwing`
9. `DisplacementObservation`
10. `EqualLevelCluster`
11. `SupportResistanceZone`
12. `Trendline`
13. `MarketMeasurementAnalysis`
14. `MarketMeasurementConfiguration`
15. `MixedSymbolAnalysisError`
16. `MixedTimeframeAnalysisError`
17. `UnsortedCandleSequenceError`
18. `DuplicateCandleRecordError`
19. `AmbiguousEventTimeAnalysisError`
20. `InvalidMarketMeasurementConfigurationError`
21. `DerivedIdentityCollisionError`
22. `DerivedOutputIdentityProvider`
23. `analyze_market_measurements`

**Total new public exports across both packages: 33** (10 + 23). Removed relative to the original proposal: `SwingStrength` (§33I), `LiquidityReference`/`LiquiditySide`/`LiquidityReferenceStatus` (§33K), `EqualLevelClusterStrength`/`EqualLevelClusterStatus` (§33K), `SupportResistanceZoneStatus` (§33N), `TrendlineSlopeClassification`/`TrendlineStatus` (§33O) — none of these is exported merely to preserve the former count; each removal is a documented, motivated narrowing. No mutable registry, internal candidate, canonical-serialization helper, hash helper, internal analyzer, lifecycle placeholder, or private helper function is exported by either package.

### 33X. Performance and Determinism

Deterministic results for the same canonically-ordered input (never "insertion-order independent" — §33D); stable total ordering via `(event_time_utc, record_id)` and, for Trendlines, `(anchor_1_bar_index, anchor_2_bar_index, anchor_1_swing_record_id)`; no global cache; no hidden parallelism; no thread requirement. ATR/median-range computation is a single linear pass per call; swing/cluster/zone/trendline detection are each linear-to-`n-log-n` in the number of confirmed swings, never quadratic in candle count for a single batch call. The accepted O(n²)-across-a-replay-session cost (§33D) remains a deliberate, non-premature-optimization tradeoff, separate from correctness.

### 33Y. Explicit Exclusions

POI creation; order blocks; FVGs; engulfing/hammer/star POIs; BTMM lifecycle; manipulation detection; trade entries; stop loss; take profit; position sizing; chart drawing; TradingView integration; Telegram; news; AI inference; backtesting performance metrics; paper trading; broker connectivity; MT5/MT4 execution; market-structure state, HH/HL/LH/LL, BOS, CHoCH, protected/weak swings — reserved for a future, separate `Structure State and Transition Foundation` milestone once an approved standard exists (`P0G-B003`); automated Equal High/Low or Trendline specialized lifecycle (`P0G-B004`/`P0G-B005`); the full Ambiguity-15 reclaim/invalidation state machine; `DRAFT`/`STRONG`/`*_BREAK_CANDIDATE` public statuses for Support/Resistance and Trendline (§33N/§33O); production approval.

### 33Z. Baseline, Quality Gates, and Stop Conditions

**Preflight (future implementation turn):** clean, synchronized `main` at `9ce3efb7fce65fbaa0fa96be427db04da5d20503`; Python `3.12.13`, `uv` `0.11.30`, Pydantic `2.13.4`; `uv lock --check` passes; existing full suite 328 passed; existing original suite 34 passed; existing combined top-level tests 250 (corrected post-implementation via AST verification from a stale preflight estimate of 236); no `measurements`/`domain` path yet exists; no dependency diff.

**Final gates:** `uv lock --check`; `ruff format --check .`; `ruff check .`; `mypy src tests`; `pytest -q` (full suite, expected 320 AST-verified top-level test functions / 398 full pytest-collected total including pre-existing parametrized cases). `pytest -q` on the two baseline files (34 passed). Exact 22 changed paths (13 source + 9 test, 0 modified); exact 70 new top-level test functions; exact 33 new public exports across the 2 new packages.

**Mandatory stop conditions:** dirty/diverged repository; a test total differing from this document's record at review time; any dependency change; any existing file modification; a genuine `market_data` Protocol extension becoming necessary; a numeric threshold not traceable to a cited `MEASUREMENT_STANDARDS.md` section or to §33C's three explicitly-labeled gap-fills; any BOS/CHoCH/HH/HL/LH/LL implementation attempt; a stateful call-order-dependent identity mechanism reappearing; an uncanonicalized fingerprint reappearing; `HEAD` changing after baseline capture; any temporary file. On any of these, stop and report.

### 33AA. Author Decisions Still Required

1. Approve milestone rename to `1B-H-MEASUREMENTS` / "Market Measurements and Reference Structures Foundation."
2. Confirm BOS/CHoCH and protected/weak structure-state deferral (`P0G-B003`) and the reservation of a future `Structure State and Transition Foundation` milestone.
3. Approve the pure semantic-key `DerivedOutputIdentityProvider.identify()` contract (§33H).
4. Approve the canonical complete-content fingerprint scheme (§33H).
5. Approve snapshot semantics (§33E) — current-prefix snapshot, not an event stream.
6. Approve strict canonically pre-sorted, strictly-increasing-`event_time_utc` input, with `AmbiguousEventTimeAnalysisError` for ties (§33D).
7. Approve Wilder ATR(14), fully specified, as `ENGINEERING-PROVISIONAL` (§33L).
8. Approve the single required positive `Decimal` `minimum_price_tick` configuration shape (§33M).
9. Approve the deterministic non-overlapping Equal-Level clustering algorithm (§33K).
10. Approve removal of the separate `LiquidityReference` contract in favor of computed properties (§33K).
11. Approve Support/Resistance confirmed-only narrowing — no `DRAFT`/`STRONG`/`*_BREAK_CANDIDATE` (§33N).
12. Approve Trendline confirmed-only narrowing — no `DRAFT`/`STRONG`/`BREAK_CANDIDATE` (§33O).
13. Approve removal of `STRONG_SWING`/`SwingStrength` (§33I).

**Status: `AUTHOR-APPROVED`, `AUTHORIZED FOR ONE COMPLETE CONTROLLED IMPLEMENTATION CYCLE`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** All 13 items above are approved without modification — see §33AB.

### 33AB. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected `1B-H-MEASUREMENTS` Market Measurements and Reference Structures Foundation architecture exactly as documented (§33A–§33AA), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `AUTHORIZED FOR ONE COMPLETE CONTROLLED IMPLEMENTATION CYCLE`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Exact approved scope:** 22 implementation paths (13 source files, 9 test files, 0 modified); 70 new top-level test functions (320 combined with the existing 250, AST-verified; 398 full pytest-collected total); 33 combined public exports (10 `measurements/` + 23 `domain/`); inventory 76 → 98 under batch tag `1B-H-MEASUREMENTS`; no dependency change; no existing `market_data` Protocol modification.

The author approved, without modification, all 13 items listed in §33AA: (1) the rename to `1B-H-MEASUREMENTS`; (2) deferral of BOS, CHoCH, HH/HL/LH/LL, protected/weak swings, and structure direction/state to a future `Structure State and Transition Foundation` (`P0G-B003`); (3) strict canonical pre-sorted input; (4) strictly increasing `event_time_utc`; (5) `AmbiguousEventTimeAnalysisError` for tied event times; (6) snapshot semantics for `MarketMeasurementAnalysis`; (7) the pure semantic-key `DerivedOutputIdentityProvider.identify()` contract, returning `UUIDv7`; (8) analyzer-owned canonical SHA-256 `content_fingerprint`; (9) Wilder ATR(14) as `AUTHOR-APPROVED`/`ENGINEERING-PROVISIONAL`; (10) the single required positive `Decimal` `minimum_price_tick`; (11) the deterministic non-overlapping Equal-Level clustering algorithm; (12) removal of `STRONG_SWING`/`SwingStrength`; (13) removal of the separate `LiquidityReference` contract; plus confirmed-only Support/Resistance and Trendline outputs, and caller responsibility for analytical-eligibility gating and revision selection.

**This approval authorizes exactly one complete implementation cycle** covering all 22 approved paths at once (no per-file decision groups), followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started as of this record — this remains a documentation-only approval.**

**Next action:** commit and push this documentation-only author approval, then implement all 22 approved paths in one complete controlled cycle, followed by one final architectural audit, at most one correction cycle for a genuine defect, one implementation commit, and one compact closure commit.

### 33AC. Implementation, Final Audit, and Closure Record

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

**Approval commit:** `562b3409758c5600cc2aa1601fd09f950f2db8c0`. **Implementation commit:** `a612d4d0cb3ef58509135edc71f459742658b5f9`. **Commit message:** "Implement 1B-H-MEASUREMENTS market measurements foundation". **Push:** succeeded to `origin/main`.

**Implemented scope:** exactly 22 committed paths — 13 new source files (`measurements/__init__.py`, `measurements/candle_metrics.py`, `measurements/atr.py`, `measurements/legs.py`, `domain/__init__.py`, `domain/configuration.py`, `domain/enums.py`, `domain/swings.py`, `domain/displacement.py`, `domain/equal_levels.py`, `domain/support_resistance.py`, `domain/trendlines.py`, `domain/analyzer.py`), 9 new test files, 0 modified existing paths. Source/test split 13/9. No dependency or lockfile change. No `market_data` Protocol modification — `RawCandleSink`, `NormalizedCandleSink`, `CandleReadRepository`, `HistoricalReplaySource` remain byte-for-byte unchanged.

**Final architectural audit verdict: genuine-defect correction cycle applied, then `READY TO COMMIT`.** Two genuine defects were found and corrected in the single authorized correction cycle:

1. `support_resistance.py` originally reassigned its tracked confirming candle to the *most recent* qualifying touch on every loop iteration, so `confirmation_candle_id` (part of the `SUPPORT_RESISTANCE_ZONE` semantic key, §33H) changed as later touches were discovered across a growing prefix — violating the approved "`record_id` stable while content grows" identity guarantee. Corrected to lock `confirmation_candle_id`/`confirmation_time_utc` to the *first* qualifying touch the moment the zone becomes valid, matching `trendlines.py`'s already-correct first-qualifying-touch behavior. Verified via a dedicated growing-prefix probe: `record_id` identical across a 1-touch and a 2-touch prefix, `content_fingerprint` differs.
2. `InvalidMarketMeasurementConfigurationError` was declared in the approved 7-error vocabulary (§33P) but never raised anywhere in `analyzer.py` — an unreachable defense-in-depth guard, contrary to the register's own "defense-in-depth; structurally guarded by required fields" framing, which implies the guard must fire if that structural guarantee is ever bypassed. Corrected by adding a defensive instrument-metadata check in `_validate_candles()` that raises this error if any candle carries a null `symbol`/`timeframe` (reachable only via `NormalizedCandle.model_construct()`, which bypasses Pydantic validation) — exercised by `test_analyze_market_measurements_rejects_missing_instrument_metadata`.

No other defect was found. Every other approved control was audited and confirmed exactly as designed: strict Policy A pre-sorted input and `AmbiguousEventTimeAnalysisError` (§33D); snapshot semantics (§33E); the pure semantic-key `DerivedOutputIdentityProvider`/`_IdentityResolver` (§33H); the analyzer-owned canonical SHA-256 `content_fingerprint` (§33H); Wilder ATR(14) seed/recurrence (§33L); the 9-step deterministic non-overlapping Equal-Level clustering algorithm including the transitive-chain rejection case (§33K); confirmed-only Support/Resistance and Trendline outputs with no `DRAFT`/`STRONG`/`BREAK_CANDIDATE`/`BROKEN`/`INVALIDATED` status anywhere (§33N/§33O); price-per-candle-index trendline slope (§33O); the exact 23-name `domain/__init__.py` export order and unchanged 10-name `measurements/__init__.py` exports (§33W); and batch/replay equivalence for confirmed swings, trendlines, and support/resistance zones using `market_data.InMemoryHistoricalReplaySource` unmodified (§33R/§33S).

**Verification results:** full suite **398 passed**; original baseline suite **34 passed**; new top-level test functions **70** (6+10+6+9+10+10+8+6+5 across the 9 new files, exact approved distribution); existing top-level test functions **250** (corrected via direct AST parse from a stale preflight estimate of 236 that predated the `1B-G-REPLAY` test files); combined top-level test functions **320** (250 existing + 70 new); full pytest-collected test total **398** (328 existing + 70 new — the gap above 320 reflects pre-existing `@pytest.mark.parametrize` expansion in unrelated files, not a change to the approved top-level-function boundary; none of the 9 new files use parametrize); public exports **33** (10 `measurements/` + 23 `domain/`, exact approved order, all import successfully); `uv lock --check` passes; `ruff format --check .` passes; `ruff check .` passes; `mypy src tests` passes with no issues across 74 source files.

**Inventory:** before **76**, new rows **22**, final **98**, batch tag `1B-H-MEASUREMENTS`, creation order **76–97** — unchanged by this closure. No inventory row was added, removed, renamed, or renumbered beyond what was already recorded at approval time.

**No dependency change. No `market_data` Protocol change. No production approval granted by this record.** The milestone remains `NOT PRODUCTION-APPROVED`.

**Next controlled action:** define the **Structure State and Transition Foundation** — one compact architecture definition and author approval covering HH, HL, LH, LL, bullish BOS, bearish BOS, bullish CHoCH, bearish CHoCH, protected high, protected low, weak high, weak low, structure direction and state, and deterministic no-look-ahead transition ordering. These rules require their own compact architecture definition and author approval because they were explicitly deferred from `1B-H-MEASUREMENTS` (§33AA item 2; `P0G-B003`). That milestone is not started by this record.

## 34. Structure State and Transition Foundation — Architecture (Author-Approved)

**Status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** (See §34Y for the author approval record.)

**Batch identifier: `1B-I-STRUCTURE`.** Title: **Structure State and Transition Foundation.** This is the milestone explicitly reserved by `1B-H-MEASUREMENTS` (§33B, §33AB item 2; `P0G-B003`). No prior document anywhere in this project defines HH/HL/LH/LL, BOS, CHoCH, or protected/weak swing rules — every rule below is newly authored in this section, not sourced from any book or knowledge-base standard. This section is one compact, accelerated architecture definition, handled as a single decision group (no per-concept approval cycles for HH/HL, BOS, CHoCH, or protected/weak swings). **This is a consolidated, documentation-only correction of the originally proposed architecture, resolving every blocking finding from the focused read-only architectural audit in one pass** (the inventory creation-order off-by-one; the conflation of source-event chronology with confirmation/availability chronology; the incomplete "2nd-vs-1st swing only" bootstrap rule; the missing unbroken-status filter on weak-level derivation; the undefined same-candle CHoCH-then-fresh-BOS chaining case; the untested duplicate canonical-fingerprint implementation; and the ambiguous compound evidence-classification wording). Nothing was implemented under the prior draft, so this is a correction, not a new milestone.

### 34A. Purpose and Analysis Boundary

Transforms confirmed meaningful swings and ordered `NormalizedCandle` data into a deterministic, no-look-ahead market-structure snapshot:

```
canonical ordered NormalizedCandle tuple
+ confirmed swings from MarketMeasurementAnalysis, ordered by source chronology
→ swing relationship classification (HH/HL/LH/LL/EQUAL_HIGH/EQUAL_LOW), compared by source chronology
→ structure bootstrap (first determinate direction, from the latest classified relationships)
→ protected/weak swing derivation (transition-sensitive, not merely "most recent")
→ break detection (close-based, availability-group-phased)
→ BOS/CHoCH classification (at most one transition per candle)
→ current structure state
→ immutable StructureAnalysis snapshot
```

This milestone completes `P0G-B003` without inventing any unsupported trading signal. **Explicitly excluded, no threshold invented for any of them:** POI creation; order blocks; FVGs; candlestick-pattern POIs; Support/Resistance lifecycle (reclaim/invalidation); Trendline lifecycle; Equal-Level sweep lifecycle; BTMM manipulation detection; trade entries; stop loss; take profit; position sizing; visualization; alerts; backtesting metrics; broker execution; production approval.

### 34B. Input Contract — Corrected: Source Chronology, Not Confirmation Order

**Decision: the analyzer receives `candles: tuple[NormalizedCandle, ...]` and `confirmed_swings: tuple[ConfirmedSwing, ...]` directly (the smallest sufficient input) — not the full `MarketMeasurementAnalysis` aggregate.** Passing the whole aggregate would couple this analyzer to `displacement_observations`, `equal_level_clusters`, `support_resistance_zones`, and `trendlines` fields it never uses, and would require handling `MarketMeasurementAnalysis.symbol`/`.timeframe` being `None` for the empty case redundantly. `confirmed_swings` is exactly the one field of `MarketMeasurementAnalysis` this milestone needs; a caller who already has a `MarketMeasurementAnalysis` passes `measurements.confirmed_swings` directly — no adapter required.

**Corrected canonical swing order — source chronology, not confirmation/availability chronology.** The audit found that `detect_confirmed_swings()`'s own output is ordered by pivot start index (source-event chronology): its confirmation loop processes pivots in that order, but each pivot's inner reversal search is independent and can finish in a different relative order than the pivots started in (an earlier-pivoting swing can take longer to confirm than a later-pivoting same-type swing that reverses quickly). Using confirmation time as the comparison basis for "previous same-type swing" would make relationship/bootstrap/protected-weak answers depend on *which swings happen to have confirmed so far* rather than on fixed price history — unacceptable for a deterministic, replay-stable analyzer. **The caller-provided `confirmed_swings` tuple is therefore canonically ordered by source chronology**, using the exact real `ConfirmedSwing` fields:

```
(
    pivot_bar_index,
    pivot_start_time_utc,
    record_id,
)
```

`pivot_bar_index` and `pivot_start_time_utc` both describe the same candle (the pivot's start), included together for defensive redundancy exactly as 1B-H's own multi-field keys do; `record_id` is the final tie-breaker. Unsorted source chronology raises `UnsortedSwingSequenceError`. Every structural comparison in this milestone (relationship classification, bootstrap, protected/weak "most recent" derivation, BOS/CHoCH source-swing identification) uses this source-chronology order — **never** confirmation/availability order. Availability governs only *when* an output may appear (§34C), never *what* historical swing it refers to.

The analyzer processes exactly one `InternalSymbol`, one `Timeframe`, one canonically ordered candle sequence, and confirmed swings that reference candles in that sequence. Resolved:

- **Mixed-symbol / mixed-timeframe rejection:** evaluated across the union of candles and swings (a swing's `symbol`/`timeframe` must match the candles' single symbol/timeframe too) — reuses `MixedSymbolAnalysisError`/`MixedTimeframeAnalysisError` from `btmm_ai_scanner.domain`, unmodified (§34P).
- **Missing referenced candle / swing reference to an unavailable-or-future candle:** new `InvalidSwingReferenceError` — raised if any `pivot_candle_record_ids` or `confirmation_candle_id` on a supplied swing is absent from the candle tuple, or references a candle whose `availability_time_utc` is later than that swing's own `meaningful_confirmation_time_utc` (§34P).
- **Duplicate swing ID / unsorted source chronology / non-alternating swings:** new `UnsortedSwingSequenceError` — one error covering all three: a duplicate swing `record_id`; swings not canonically ordered by `(pivot_bar_index, pivot_start_time_utc, record_id)`; two consecutive swings (by source chronology) sharing the same `swing_type` (§34P).
- **Duplicate candle ID / tied `event_time_utc` / unsorted candles:** reuses `DuplicateCandleRecordError`/`AmbiguousEventTimeAnalysisError`/`UnsortedCandleSequenceError` from `btmm_ai_scanner.domain`, unmodified — identical validation semantics applied independently to the supplied candle tuple (this analyzer does not call `analyze_market_measurements()` itself, so it re-validates its own candle input).
- **Empty input:** `len(candles) == 0` (implying `len(confirmed_swings) == 0`) returns the empty `StructureAnalysis` aggregate (§34S) — never an exception.
- **Insufficient swings:** fewer than the swings bootstrap requires (§34D) is a *normal*, non-error outcome — `current_state.direction == UNDETERMINED`, not an exception.
- **Measurement-analysis/candle-prefix mismatch:** does not apply — there is no separate `MarketMeasurementAnalysis` parameter to mismatch against, by the input-contract decision above.

No hidden repository reads — the analyzer touches only its two supplied tuples.

### 34C. No-Look-Ahead Policy and Availability-Group Processing Phases — Corrected

Every structure output's `availability_time_utc` equals the **latest** `availability_time_utc` among every candle and confirmed swing required to establish it. Never `event_time_utc`-only release; never `processing_time_utc` substitution; never future-candle access. Source chronology (§34B) determines *what* a comparison refers to; availability determines *when* the resulting output may appear — these are two independent axes, never conflated.

- **`SwingRelationship` availability:** `max(current_swing.availability_time_utc, predecessor_swing.availability_time_utc)` — since the predecessor, by source chronology, is not necessarily the swing that confirmed first (§34B), the simple "classified swing's own availability" shortcut is no longer assumed; the explicit `max()` is required.
- **A swing whose immediately preceding same-type source-chronology swing is not present in the supplied `confirmed_swings` tuple is not yet comparable** — no relationship is emitted for it in this call (never substituted against a later or unrelated same-type swing instead). Once that predecessor appears in a subsequent, more complete call, the relationship becomes emittable using `max()` of both swings' availability. **The semantic key for `SWING_RELATIONSHIP` includes both the current swing's and the predecessor's `record_id` (§34K)** — so a relationship computed against one predecessor is a permanently distinct identity from a relationship of the same current swing against a different predecessor; a previously emitted relationship's predecessor reference therefore never changes — a later, more complete call simply emits a *different*, additional record with a different identity; it never mutates an earlier one. Source chronology itself is immutable and never revised.
- **Bootstrap (initial direction) availability:** `max()` of the availability of the two classified relationships (one HIGH, one LOW) whose agreement completes bootstrap (§34D) — reflected only via `current_state.availability_time_utc`; bootstrap itself emits no `StructureTransition` (§34D).
- **Protected/weak swing availability:** effective availability is always `current_state.availability_time_utc` at the point they were last updated (§34F) — transition-sensitive, not re-derived independently of transitions.
- **BOS/CHoCH confirmation availability:** `max(break_candle.availability_time_utc, broken_swing.availability_time_utc)`.
- **Simultaneous breaks / multiple outputs confirmed by one candle:** all share that candle's `availability_time_utc`; total order among them follows §34J exactly; at most one `StructureTransition` is ever emitted per candle (§34J).
- **Equal availability-time ordering:** broken by the §34J key, never by insertion order.
- **Invalidation or state-change availability:** this milestone has no invalidation/retest concept (that is POI-specific, deferred elsewhere); "state change" = a new `StructureTransition`, governed by the BOS/CHoCH availability rule above.
- **Replay-prefix equivalence:** identical `StructureAnalysis` for the identical visible prefix — full procedure at §34O.

**Corrected: exact availability-group processing phases.** Even in a single one-shot batch call, the supplied candle prefix spans many distinct `availability_time_utc` groups. The analyzer processes them internally in chronological order, one group at a time, exactly as follows — this is the algorithm's own internal procedure, not merely a caller-facing replay recommendation:

1. Identify the candles available in the current availability group.
2. Evaluate those candles' closes only against protected/weak levels that were already active **before this availability group began** — i.e., finalized at the end of the previous group. A level activated during the current group can never be broken by a candle from that same group.
3. Emit at most one `StructureTransition` per candle within this group; CHoCH has priority over BOS (§34J).
4. Apply the selected transition, if any, and retire its broken level.
5. Add swings whose `meaningful_confirmation_time_utc` belongs to this group to the visible swing set.
6. Emit newly available swing relationships, comparing by source chronology among the now-visible same-type swings (§34B).
7. Complete bootstrap if not yet determined, or populate a missing post-transition weak/protected target if an eligible swing (by source chronology, after the relevant transition's break candle) is now visible (§34F).
8. Produce the `CurrentStructureState` snapshot reflecting the state at the end of this group.

**Consequences:** a level activated in step 4/7 of one group cannot be broken by a candle in that same group's step 2 (already evaluated against the prior group's finalized state); a swing's own confirming candle can never retroactively break the level that same confirmation creates; the earliest a newly activated level can be broken is in a strictly later availability group. No detector consumes only part of one availability group.

### 34D. Swing Relationship Classification and Structure Bootstrap — Corrected: Source Chronology, Generalized Bootstrap

**New closed enum `SwingRelationshipLabel`** (exactly the 6 members considered): `HIGHER_HIGH`, `LOWER_HIGH`, `EQUAL_HIGH`, `HIGHER_LOW`, `LOWER_LOW`, `EQUAL_LOW`.

**Comparison basis — corrected to source chronology:** for each available `SWING_HIGH`, compare against the immediately preceding available `SWING_HIGH` **in source chronology** (§34B's `(pivot_bar_index, pivot_start_time_utc, record_id)` order) among the supplied `confirmed_swings`; symmetrically for `SWING_LOW`. "Available" means present in the supplied tuple — if the true source-chronology predecessor is not yet present, the current swing is not yet comparable (§34C) and emits no relationship this call, rather than being compared against a more distant or wrong stand-in.

**Tolerance:** reuses the *value* (not the field) of 1B-H's approved Equal-Level tolerance concept — a new, independent `StructureConfiguration.swing_relationship_equal_tolerance_atr_multiplier: Decimal = Decimal("0.10")` (§34K), applied against the *current* swing's own `pivot_reference_atr` (already populated and guaranteed positive by the completed 1B-H detector — no recomputation, no second ATR implementation, no `measurements.atr` import):

```
tolerance = configuration.swing_relationship_equal_tolerance_atr_multiplier * current_swing.pivot_reference_atr

current.pivot_price > predecessor.pivot_price + tolerance  → HIGHER_HIGH / HIGHER_LOW
current.pivot_price < predecessor.pivot_price - tolerance  → LOWER_HIGH / LOWER_LOW
otherwise                                                   → EQUAL_HIGH / EQUAL_LOW
```

`minimum_price_tick` does not participate in this comparison and is deliberately absent from `StructureConfiguration` — the comparison is already ATR-normalized (scaled by the swing's own reference volatility), so a separate absolute price-tick floor would add nothing and is not invented (§34K).

Strict Decimal-exact comparison is rejected (would almost never trigger against real price data — identical reasoning to 1B-H's own Equal-Level clustering).

**Equal relationships are emitted explicitly** as their own `SwingRelationship` records (not suppressed) **and** are treated as reference-only, non-progressing evidence for bootstrap and BOS/CHoCH purposes (§34D/§34F/§34H) — both of the originally-considered options apply simultaneously, not just one.

**`SwingRelationship` outputs are immutable historical facts** — once emitted (identified by `(current_swing_record_id, predecessor_swing_record_id)`, §34K), never mutated; their meaning never flips (§34C).

**Alternating requirement:** inherited, not re-enforced here — `ConfirmedSwing` sequences supplied to this analyzer are required to already alternate, in source-chronology order (guarded by `UnsortedSwingSequenceError`, §34B); a caller bypassing `detect_confirmed_swings()` to supply a non-alternating sequence is rejected at the input boundary, not silently tolerated inside classification.

**Simultaneous high/low ambiguity:** already excluded upstream by `detect_confirmed_swings()` (a single candle can never qualify as both a swing high and swing low pivot, §33I) — inherited, not re-solved.

**Superseded swing behavior:** already resolved upstream (`_supersede_same_direction_runs`, §33I) — the swings supplied here are the final, confirmed set; no additional supersession occurs in this milestone.

**First available swing of each type:** no `SwingRelationship` is emitted (there is no available predecessor to compare against).

**No inference from candle color** — classification only ever reads `ConfirmedSwing.pivot_price`.

**Bootstrap — corrected: generalized to the latest classified relationships, not a fixed "2nd vs 1st" rule.** The original draft only defined bootstrap for exactly 4 swings ("the 2nd HIGH vs the 1st HIGH, and the 2nd LOW vs the 1st LOW"), leaving 5+-swing sequences and equal-then-later-resolving sequences undefined. Corrected rule:

- **Direction becomes `BULLISH`** when the *latest classified* `SwingRelationship` of HIGH-type is `HIGHER_HIGH` **and** the *latest classified* `SwingRelationship` of LOW-type is `HIGHER_LOW`, simultaneously.
- **Direction becomes `BEARISH`** when the *latest classified* HIGH-type relationship is `LOWER_HIGH` **and** the *latest classified* LOW-type relationship is `LOWER_LOW`, simultaneously.
- **Direction remains `UNDETERMINED`** whenever either relationship is absent (no classifiable predecessor yet, §34D), either latest relationship is equal (`EQUAL_HIGH`/`EQUAL_LOW`, contributing no directional evidence), or the two latest relationships conflict (e.g., a higher low but a lower high — a contracting pattern).

"Latest classified" always means the most recently classified relationship of that type **as of the current call** — this generalizes correctly to any swing count and any interleaving of equal or contradictory intermediate relationships, and a later relationship (once a previously missing predecessor becomes available, or once a new swing arrives) may resolve a previously equal or contradictory state without needing any special-cased "Nth vs (N-1)th" rule.

This is symmetric and sequence-start-agnostic: it bootstraps correctly regardless of whether the visible sequence began with a `SWING_HIGH` or a `SWING_LOW`, since the rule only requires the *latest* relationship of each type to agree, never a fixed starting type or a fixed swing count.

**Exact bootstrap behavior:**

| Condition | Behavior |
|---|---|
| 0 swings | `UNDETERMINED`; no relationships; no transitions |
| 1 swing | `UNDETERMINED`; no relationship emitted (first-of-type) |
| Only 1 HIGH and 1 LOW available | `UNDETERMINED`; zero relationships possible — each is the first of its type |
| Only one type has 2+ available swings | `UNDETERMINED`; exactly one side is classifiable, but bootstrap needs *both* sides |
| Both sides classifiable and agree, non-equal | Resolves to `BULLISH`/`BEARISH` per the rule above |
| Contradictory evidence (higher low, lower high, or vice versa) | `UNDETERMINED` — correct, not a defect |
| Either latest relationship is equal | `UNDETERMINED` persists until a later non-equal relationship of that type resolves it |
| A same-type predecessor is source-chronologically earlier but not yet confirmed/visible | the dependent swing is not yet comparable (§34D); bootstrap simply waits, using whatever *is* currently classifiable |
| Incomplete alternating sequence | cannot occur as valid input — rejected by `UnsortedSwingSequenceError` (§34B), not a bootstrap case |
| Simultaneous bootstrap conditions | cannot occur — the two relationships used are each tied to a distinct classified swing; tied confirmation times across distinct swings are already structurally excluded upstream |

**Before bootstrap completes, `structure_direction = UNDETERMINED`.** No BOS or CHoCH is ever emitted before bootstrap completes — both require an *already-established* direction (§34G/§34H). **No separate initialization/transitional state is introduced for bootstrap** — the bootstrap moment is visible only through `current_state.direction` changing away from `UNDETERMINED`, timestamped by the `max()` of the two resolving relationships' availability (§34C); it never produces a `StructureTransition` record (those are reserved exclusively for BOS/CHoCH, which by definition require a pre-existing direction to continue or reverse).

**Exact initial protected/weak assignment, immediately upon bootstrap (author decision required, previously undefined):**

- **At `BULLISH` bootstrap:** `protected_low` = the LOW swing that was the *current* (classified) swing in the qualifying `HIGHER_LOW` relationship; `weak_high` = the HIGH swing that was the *current* swing in the qualifying `HIGHER_HIGH` relationship; `protected_high = None`; `weak_low = None`.
- **At `BEARISH` bootstrap:** `protected_high` = the HIGH swing that was the *current* swing in the qualifying `LOWER_HIGH` relationship; `weak_low` = the LOW swing that was the *current* swing in the qualifying `LOWER_LOW` relationship; `protected_low = None`; `weak_high = None`.
- Both assigned levels are, by construction, unbroken at the moment of bootstrap (bootstrap only ever considers the two most-recently-classified relationships, which reference the most recent available swings). Equal relationships never contributed to this assignment (§34D) and never create or replace a protected/weak level. One swing cannot simultaneously be active as protected and weak (protected and weak always reference opposite swing types, §34F).

### 34E. Structure Direction and State — Enums and Contracts

**New closed enum `StructureDirection`:** `UNDETERMINED`, `BULLISH`, `BEARISH` — exactly the 3 considered. **No separate structure-state enum is introduced** — "state" is fully captured by direction plus the active protected/weak swing IDs plus the latest transition ID; no `TRENDING`/`RANGING`/`CONSOLIDATING` or similar unapproved classification is invented.

**Two immutable contracts:**

- `StructureTransition` — one per confirmed BOS/CHoCH event; identity-bearing; accumulated as an **immutable ordered tuple** (`structure_transitions`), never mutated once emitted.
- `CurrentStructureState` — **one immutable current-state snapshot** per analysis call; also identity-bearing (see §34I for why).

Plus `SwingRelationship` (§34D) as a third, independent, tuple-accumulated output.

### 34F. Protected and Weak Swings — Corrected: Transition-Sensitive, Symmetric Unbroken Filtering

**Corrected: active levels are not defined as merely "the most recent swing."** The audit found a concrete defect in the original draft: `weak_high`/`weak_low` lacked the "unbroken" filter that `protected_high`/`protected_low` had, so after a BOS retired the active weak level, "most recent SWING_HIGH/LOW" (with no unbroken filter) could still resolve to that *same, already-broken* swing if no newer same-type swing had yet confirmed — risking a second, invalid break attempt against an already-consumed level. Corrected rule: **both protected and weak levels require unbroken status, symmetrically**, and both are **transition-sensitive** (updated only at bootstrap, BOS, or CHoCH — never merely because a newer same-type swing confirms in between).

**BULLISH state:**

- **`protected_low`:** established at bullish bootstrap. Updated only at a bullish BOS or a bullish CHoCH (never merely because a newer low confirms). At a bullish BOS: update to the latest available unbroken `SWING_LOW` whose source chronology falls after the previous structure transition's break candle and before this BOS's own break candle; if no eligible swing qualifies, **retain the existing `protected_low`**.
- **`weak_high`:** established at bullish bootstrap; must always be unbroken. When broken by a bullish BOS, retire it immediately — `weak_high` becomes `None` on that transition (no automatic replacement is invented). The first newly visible unbroken `SWING_HIGH` whose source chronology occurs after the transition's break candle becomes the next `weak_high` (found either within the same batch call, if such a swing already exists in the supplied prefix, or in a later call once one appears). Once active, it is not replaced by another high until it is itself broken and retired.

**BEARISH state — exact mirror:** `protected_high` updates only at bearish bootstrap, bearish BOS, or bearish CHoCH (retaining the existing value if no eligible newer high qualifies); `weak_low` must always be unbroken, is retired immediately upon being broken by a bearish BOS (becoming `None`, no automatic replacement), and the first eligible new low after the transition becomes the next `weak_low`.

**General rules:**

- Broken levels are retained only in immutable transition history (`StructureTransition.broken_swing_id`, §34I) — never return to current state.
- **No BOS is possible while the corresponding weak level is `None`** — a BOS candidate is not evaluated at all until a `weak_high`/`weak_low` exists (§34H).
- **No CHoCH is possible while the corresponding protected level is `None`** — in practice this never arises once a direction is established, since bootstrap and every subsequent transition guarantee a protected level is always assigned when its direction is active (§34D's initial assignment; §34H's CHoCH prerequisite check).
- Equal relationships never create or replace a protected/weak level directly (§34D) — but the swing they classify remains eligible to *become* a protected/weak level through the ordinary transition-sensitive update rule above, exactly like any other swing (its `SwingRelationshipLabel` and its protected/weak eligibility are independent concerns).
- One swing cannot simultaneously be active as protected and weak — protected and weak always reference opposite swing types, and only one `{protected, weak}` pair is active per direction (`UNDETERMINED` nulls all four).
- **Snapshot vs. lifecycle-history semantics:** `CurrentStructureState` is a snapshot of the *active* protected/weak IDs only; the full history of how protection moved over time is recoverable from the ordered `structure_transitions` tuple, each of which records `protected_swing_id`/`weak_swing_id` exactly as they stood immediately after that transition (§34I).
- Does wick penetration change a label? No — protected/weak status changes only via a qualifying close-based break (§34G) or via the transition-sensitive update rule above, never via a bare wick.

### 34G. Break Confirmation Policy — Corrected: Two Separate Price Fields, Activation-Group Timing

**Decision: A — candle close strictly beyond the swing price.** Wick-only penetration is explicitly **not** a break. This is the standard, noise-resistant convention, and it matches how 1B-H's own Support/Resistance reaction logic already gates on `candle.close` (§33N), not the wick.

- **Bullish break inequality** (breaking a high-type level): `candle.close > active_level_price` (strict).
- **Bearish break inequality** (breaking a low-type level): `candle.close < active_level_price` (strict).
- **Equality at the level** (`close == level_price`): not a break.
- **Gap opening beyond a level:** no special case — if `candle.close` already satisfies the strict inequality, the candle qualifies exactly like any other break, gap or not.
- **Candle high/low beyond the level but close inside:** not a break (confirms the wick exclusion).
- **Candle closing beyond multiple levels:** only the currently active protected/weak levels are actionable (at most one high-type + one low-type, §34F); historical, already-retired levels are never re-tested and produce no transitions; a transition references exactly one active broken level.
- **Source break candle:** the first `NormalizedCandle`, scanning forward in canonical order, whose `close` satisfies the strict inequality against a given active level — subject to the availability-group phase rule (§34C): a level cannot be broken by a candle in the same availability group in which that level itself became active.
- **Corrected — two separate fields, not one ambiguous `break_price`:** `StructureTransition.broken_level_price: Decimal` (the broken swing's own `pivot_price` — the level itself) and `StructureTransition.break_close_price: Decimal` (the break candle's exact `close`, recorded verbatim). These are never conflated into a single field.
- **First qualifying break only:** yes — once a level is broken, it is permanently consumed; it can never be broken "again" and is never reopened (§34F's transition-sensitive retirement enforces this: a retired level is `None` until explicitly replaced, and the replacement is a *different* swing).
- **Repeated closes beyond an already-broken (retired) level:** produce no further transition — there is no longer an active level there to break.
- **Overshoot measurement:** not recorded — no invented `break_magnitude`/`overshoot` field; `broken_level_price`/`break_close_price` alone are sufficient, matching 1B-H's minimal-field philosophy.
- **Transition timestamps:** `event_time_utc` = break candle's own `event_time_utc`; `availability_time_utc` = break candle's own `availability_time_utc` (maxed defensively against the broken swing's own availability, §34C).

**POI breach rules are not reused** — this is an independently authored rule; no POI-specific lifecycle document is approved for structure use.

### 34H. BOS and CHoCH Rules — Corrected: No-Replacement Retirement, Guarded CHoCH, One Transition Per Candle

**Bullish BOS** (continuation, bullish structure only): prerequisites — `structure_direction == BULLISH`; an active, unbroken `weak_high` exists (§34F — if `weak_high` is `None`, no BOS candidate is evaluated at all); candle closes strictly above `weak_high.pivot_price`. Result: direction remains `BULLISH`; the broken `weak_high` is retired (`weak_high` becomes `None` on this transition — no replacement is invented at the same instant); `protected_low` updates under §34F's exact transition-sensitive rule (retained if no eligible newer low qualifies); a later, source-chronologically-eligible confirmed `SWING_HIGH` establishes the next `weak_high`. **A BOS can be emitted even when no immediate replacement `weak_high` exists** — the structure simply has no active continuation target until one appears.

**Bearish BOS:** exact mirror — prerequisites `BEARISH` direction and an active unbroken `weak_low`; breaks `weak_low` (`close < weak_low.pivot_price`); direction remains `BEARISH`; `weak_low` retires to `None`; `protected_high` updates under §34F; a later eligible low establishes the next `weak_low`.

**Not every swing break is BOS:** only the two currently *active* levels (`weak_high`/`weak_low` for BOS, `protected_high`/`protected_low` for CHoCH) are ever tested for a break — no other swing's price is ever evaluated at all.

**Bullish CHoCH** (reversal, bearish → bullish): prerequisites — `structure_direction == BEARISH` (the *opposite* existing direction — cannot fire from `UNDETERMINED` or `BULLISH`); an active `protected_high` exists; candle closes strictly above `protected_high.pivot_price`. Result: direction becomes `BULLISH` in one atomic step (no separate transitional/pending-confirmation state, an explicit decision to keep the model minimal); the broken `protected_high` is retired; **new `protected_low`** = the latest available unbroken `SWING_LOW`, by source chronology, before the break candle; `weak_high = None`; `protected_high = None`; `weak_low = None`; a later eligible `SWING_HIGH` establishes the first `weak_high` under the new direction.

**Bearish CHoCH:** exact mirror — prerequisite `BULLISH`; breaches active `protected_low` (`close < protected_low.pivot_price`); direction becomes `BEARISH`; new `protected_high` = latest available unbroken `SWING_HIGH` before the break candle; `weak_low = None`; `protected_low = None`; `weak_high = None`; a later eligible low establishes the first `weak_low`.

**Guarded CHoCH — corrected, previously undefined:** if no eligible opposite-side unbroken swing exists to serve as the new protected level (e.g., no unbroken `SWING_LOW` exists at all to become `protected_low` for a bullish CHoCH — a case bootstrap's own prerequisites make extremely unlikely but not provably impossible in every edge case), **the analyzer does not emit an impossible partial CHoCH**: the candidate is treated as analytically unsupported under this closed rule, the prior direction and state are kept unchanged, and no `StructureTransition` is emitted for that candle's would-be CHoCH. No additional public lifecycle state is created for this case — it is simply "no transition this candle."

**First transition after `UNDETERMINED`:** impossible by construction — bootstrap (§34D) never itself emits a `StructureTransition`; the first transition in any analysis necessarily occurs strictly after bootstrap has already set a non-`UNDETERMINED` direction.

**BOS/CHoCH are mutually exclusive for a single break** — structurally guaranteed: a given price level is *either* the active weak level (same-direction continuation) *or* the active protected level (opposite-direction reversal) for the current direction, never both (§34F's exclusivity).

**Corrected — one transition per candle, no same-candle chaining (§34J):** at most one `StructureTransition` is ever emitted per candle. If a candle qualifies for CHoCH, CHoCH is emitted and **BOS is not re-evaluated for that candle at all** — not even under the newly flipped direction, even if the same close would otherwise qualify as a fresh BOS once the new weak level is assigned. The new direction and any newly assigned levels apply starting with the next candle. This replaces the original draft's undefined "CHoCH-then-revalidate-BOS-under-new-state" language, which left open whether a same-candle chained BOS could follow a CHoCH.

**Repeated-break suppression:** per §34G (first-qualifying-break-only, retirement without automatic replacement).

### 34I. Snapshot and Transition-History Contracts — Corrected Fields

```python
class StructureTransition(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol
    timeframe: Timeframe
    transition_type: StructureTransitionType   # BULLISH_BOS | BEARISH_BOS | BULLISH_CHOCH | BEARISH_CHOCH
    direction_before: StructureDirection
    direction_after: StructureDirection
    broken_swing_id: UUIDv7
    broken_level_price: Decimal    # the broken swing's own pivot_price
    break_close_price: Decimal     # the break candle's exact close (verbatim)
    protected_swing_id: UUIDv7         # active protected swing immediately after this transition — always defined (§34H's guarded-CHoCH rule prevents emission otherwise)
    weak_swing_id: UUIDv7 | None       # active weak swing immediately after this transition — None immediately after a BOS/CHoCH retires it with no eligible replacement yet (§34H)
    break_candle_id: UUIDv7
    event_time_utc: datetime           # the break candle's own event_time_utc
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

**Corrected: `broken_level_price`/`break_close_price` replace the original single, ambiguous `break_price` field (§34G).** `weak_swing_id` is now nullable — the original draft's "always well-defined" claim was invalidated by §34F/§34H's corrected no-automatic-replacement retirement rule; `protected_swing_id` remains non-optional (§34H's guarded-CHoCH rule ensures a CHoCH is never emitted unless its new protected level is defined, and BOS never nulls the protected level).

**New closed enum `StructureTransitionType`:** `BULLISH_BOS`, `BEARISH_BOS`, `BULLISH_CHOCH`, `BEARISH_CHOCH` — exactly 4 members, no `PENDING`/transitional state (§34H).

```python
class CurrentStructureState(ContractModel):
    record_id: UUIDv7
    content_fingerprint: SHA256Fingerprint
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    direction: StructureDirection
    active_protected_high_swing_id: UUIDv7 | None
    active_protected_low_swing_id: UUIDv7 | None
    active_weak_high_swing_id: UUIDv7 | None
    active_weak_low_swing_id: UUIDv7 | None
    latest_transition_id: UUIDv7 | None
    availability_time_utc: datetime
    analyzed_swing_count: int
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
    evidence_classification: EvidenceClassification
    provenance_id: UUIDv7
```

**`CurrentStructureState` does have its own identity/fingerprint** (§34K) — for the same reason every other derived output in this codebase does, and so batch/replay equivalence tests can directly assert `record_id` stability across growing prefixes (§34O).

`current_state` is `None` only for fully empty input (§34S); for any non-empty candle input it is always a real, identity-bearing `CurrentStructureState`, even when `direction == UNDETERMINED` and all four active-swing-ID fields are `None` — `symbol`/`timeframe` alone are sufficient context to mint its singleton identity (§34K).

### 34J. Transition Ordering — Corrected: One Transition Per Candle, No Chaining

Exact deterministic total order for every relationship/transition confirmed at the same `availability_time_utc`:

```
(
    availability_time_utc,
    break_candle_event_time_utc,
    transition_priority,          # 0 = CHoCH (reversal), 1 = BOS (continuation)
    direction_after.value,
    source_swing_pivot_bar_index,
    str(source_swing_record_id),
    str(transition_record_id),    # absolute final tie-breaker
)
```

**Corrected policy — adopted verbatim from the audit's recommended safe policy:** at most one `StructureTransition` is emitted per candle. CHoCH has priority over BOS. If a candle qualifies for CHoCH, CHoCH is emitted and BOS is **not** re-evaluated or emitted for that same candle under the newly flipped direction — every same-candle CHoCH-then-BOS chaining rule from the original draft is removed. The new direction and any newly assigned levels apply to subsequent candles only. At most two *candidate* transitions can ever arise from one candle in the first place (one high-side + one low-side, since only one high-type and one low-type level are ever active simultaneously, §34F) — when both candidates arise from the same candle, CHoCH is selected and the BOS candidate is discarded entirely, never emitted as a second transition. No candle ever emits multiple BOS transitions for multiple crossed historical levels — only the one active broken level is ever referenced (§34G).

`SwingRelationship` classification and break/transition evaluation are independent record types with no shared mutable state between them — relationship classification (a pure comparison, §34D) always completes before break evaluation within the availability-group phase order (§34C, steps 2–6); this is a two-phase processing order, not an ordering conflict.

No output order ever depends on dictionary or set iteration order — implementation uses plain lists sorted by the exact key above.

### 34K. Identity, Fingerprint, Evidence, and Configuration — Corrected: Semantic Keys, Tested Equivalence, Unambiguous Evidence

**The `DerivedOutputIdentityProvider` Protocol and `DerivedOutputType` enum are reused from `btmm_ai_scanner.domain`, structurally unmodified in shape.** `DerivedOutputType` gains exactly 3 new members (the one modified existing path in this milestone, `domain/enums.py`): `SWING_RELATIONSHIP`, `STRUCTURE_TRANSITION`, `CURRENT_STRUCTURE_STATE`. A caller may pass the *same* identity-provider instance to both `analyze_market_measurements()` and `analyze_structure_state()`; each analyzer's own identity resolver checks collisions only within its own call, identical in scope to 1B-H's own already-approved precedent ("the analyzer invokes `identify()` exactly once per emitted output record").

**The canonical fingerprint/identity-resolution *implementation*** (`_canonicalize`, `_compute_content_fingerprint`, `_IdentityResolver`, the generic `_finalize` helper) **is deliberately duplicated locally in `structure/analyzer.py`, not imported from `domain/analyzer.py`.** These are module-private (leading-underscore) helpers in an already-closed, already-audited milestone; importing them across packages would create an undocumented dependency on another milestone's private internals with no compatibility guarantee, and modifying `domain/analyzer.py` to publicize/extract them would reopen closed, audited code for a purely mechanical reason. The duplication is small (~40 lines), behaviorally identical, and explicitly disclosed here as a documented **maintenance risk**: the two implementations must be kept in sync by hand if either is ever changed. **Corrected — this duplication is now a tested guarantee, not an unverified assumption:** a dedicated test, `test_structure_fingerprint_serializer_matches_market_measurement_serializer` (§34R), feeds representative `Decimal`, enum, `UUIDv7`, timezone-aware `datetime`, `SemVer`, tuple, `None`, `bool`, `int`, and `str` values through both `structure/analyzer.py`'s and `domain/analyzer.py`'s private canonicalization functions and asserts byte-identical canonical output and identical resulting fingerprints for equivalent inputs. Neither implementation imports the other merely to make this test pass — both remain fully independent; the test only verifies they agree.

**Exact semantic keys, corrected** (all elements stringified per 1B-H's canonical rule):

```
SWING_RELATIONSHIP:      (symbol.value, timeframe.value, str(current_swing_record_id), str(predecessor_swing_record_id), rule_version)
STRUCTURE_TRANSITION:    (symbol.value, timeframe.value, transition_type.value, str(broken_swing_id), rule_version)
CURRENT_STRUCTURE_STATE: (symbol.value, timeframe.value, rule_version)
```

**`SWING_RELATIONSHIP`'s key is corrected to include both the current swing's and the predecessor's `record_id`.** The original key (current swing's ID alone) could not distinguish "H3 vs H1" from a later-recomputed "H3 vs H2" once a slow-confirming, source-earlier H2 became visible — the audit found this could force an already-emitted relationship's *meaning* to flip, not merely grow, violating replay stability. With the predecessor folded into the key, "H3 vs H1" and "H3 vs H2" are permanently distinct identities: a previously emitted relationship never changes predecessor (§34C); a more complete later call simply emits an *additional*, differently-identified record, never mutating the earlier one. `STRUCTURE_TRANSITION`'s key needs only `broken_swing_id` — §34G's first-qualifying-break-only rule guarantees a given swing is broken at most once, ever, making it a naturally permanent, unique key component (`transition_type.value` is included for defensive redundancy). **`CURRENT_STRUCTURE_STATE`'s key drops the redundant `"CURRENT"` literal from the original draft** — `output_type` is already mixed into the identity payload ahead of the semantic-key tuple (verified against this project's own identity-provider mechanics), so no other output type could ever collide on the same `(symbol, timeframe, rule_version)` tuple; the literal was unnecessary. This key is a **singleton** per `(symbol, timeframe, rule_version)` — one stable `record_id` forever, its `content_fingerprint` changing as the visible prefix grows, exactly mirroring 1B-H's "record_id stable, content changes" pattern for `EqualLevelCluster`/`SupportResistanceZone`.

Identity is stable across repeated batch calls, stable across replay of the same prefix, independent of call order and dictionary ordering, and collision-checked via the reused `DerivedIdentityCollisionError` (§34N). Fingerprint represents complete public snapshot content excluding only `record_id`/`content_fingerprint`, using the identical canonical serialization rules as 1B-H (tested for equivalence, above). No random identity generation anywhere.

**Evidence and versioning — corrected: unambiguous, single stored value.** `EvidenceClassification` was verified directly against `contracts/provenance_record.py`: `AUTHOR_APPROVED` (`"AUTHOR-APPROVED"`) is a real, distinct, selectable member of the *same* enum as `ENGINEERING_PROVISIONAL` — not merely a document-level status label. The original draft's compound "AUTHOR-APPROVED/ENGINEERING-PROVISIONAL" phrasing did not state which single value is actually stored, which the audit flagged as genuinely ambiguous given `AUTHOR_APPROVED` is a real, selectable alternative. **Two separate, non-overlapping axes are defined:**

- **Document decision-status** (this register's own vocabulary — `ARCHITECT-RECOMMENDED`, `AUTHOR-DECISION REQUIRED`, and, once the author explicitly approves this corrected architecture, `AUTHOR-APPROVED`) describes whether a *decision* has been sanctioned. This status is never itself stored in any `ContractModel`'s `evidence_classification` field.
- **Output evidence value** — every emitted `SwingRelationship`, `StructureTransition`, and `CurrentStructureState` stores exactly `EvidenceClassification.ENGINEERING_PROVISIONAL` — never `AUTHOR_APPROVED`, `BOOK_SOURCED`, `EMPIRICALLY_CALIBRATED`, `OUT_OF_SAMPLE_VALIDATED`, `PRODUCTION_APPROVED`, or any other member, and never a compound/dual value. Reason: these HH/HL/LH/LL/BOS/CHoCH/protected/weak rules are newly authored deterministic engineering rules — not book-sourced (no book or knowledge-base source defines them, confirmed by the `P0G-B003` deferral text in three independent sources), not empirically calibrated, not out-of-sample validated, and not production-approved. This holds regardless of whether the author has separately approved the *decision* to adopt each rule — decision-approval and evidence-quality are orthogonal. Rule manifests may separately describe mixed provenance narratively; every `ContractModel` output field nonetheless holds exactly one enum member.

**One immutable `StructureConfiguration(ContractModel)`:**

```python
class StructureConfiguration(ContractModel):
    swing_relationship_equal_tolerance_atr_multiplier: Decimal = Decimal("0.10")
    rule_version: SemVer = SemVer.parse("1.0.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")
    evidence_classification: EvidenceClassification = EvidenceClassification.ENGINEERING_PROVISIONAL
```

Every field has a default — `StructureConfiguration()` constructs with zero required arguments (unlike `MarketMeasurementConfiguration`, which requires `minimum_price_tick`). **`minimum_price_tick` is deliberately absent, explicitly justified:** this milestone invents no price-scale-dependent threshold beyond the one reused, ATR-normalized tolerance value (§34D); the break-confirmation rule (§34G) is a pure strict-inequality comparison against exact swing prices, requiring no tunable tolerance and no tick-scale floor at all. `swing_relationship_equal_tolerance_atr_multiplier` is the *only* numeric threshold in the entire milestone, copied verbatim from 1B-H's approved `equal_level_tolerance_atr_multiplier` (same conceptual test — "are these two price points effectively equal") — no new threshold is invented, no ATR period is duplicated, no Wilder recurrence is redefined, and `MarketMeasurementConfiguration` is not referenced or composed with. Configuration validation remains deterministic and `Decimal`-only wherever numeric (a field validator requires the tolerance multiplier `> 0`, raising standard Pydantic `ValidationError`).

### 34L. Public API and Error Vocabulary

```python
def analyze_structure_state(
    candles: tuple[NormalizedCandle, ...],
    confirmed_swings: tuple[ConfirmedSwing, ...],
    configuration: StructureConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> StructureAnalysis: ...
```

One synchronous entry point — no separate public analyzer for BOS or CHoCH.

- **Empty input** (`len(candles) == 0`): returns the empty `StructureAnalysis` (§34M) — never an exception.
- **Insufficient structure** (too few swings for bootstrap, or resolving to `UNDETERMINED` due to equal/contradictory/not-yet-comparable evidence): a normal, non-error outcome — full `StructureAnalysis` with `current_state.direction == UNDETERMINED`, whatever `swing_relationships` are classifiable, and `structure_transitions == ()`.
- **Mixed input:** raises the appropriate error from §34N.
- **Ordering requirements:** candles canonically pre-sorted `(event_time_utc, record_id)` (`UnsortedCandleSequenceError`, reused); swings canonically ordered by **source chronology** `(pivot_bar_index, pivot_start_time_utc, record_id)` and alternating (`UnsortedSwingSequenceError`, new, corrected from the original confirmation-time-based ordering — §34B).
- **Identity-provider failure behavior:** any exception the caller's `identity_provider.identify()` raises propagates unmodified — no catching or wrapping, identical to 1B-H's behavior.
- **Configuration validation:** `StructureConfiguration` is a frozen Pydantic model with its own field validator (`swing_relationship_equal_tolerance_atr_multiplier` must be `> 0`), raising standard Pydantic `ValidationError` — `InvalidStructureConfigurationError` (§34N) is reserved specifically for the defensive instrument-metadata guard, not for configuration-field validation (identical split to 1B-H's `ValidationError` vs. `InvalidMarketMeasurementConfigurationError`).
- **Deterministic output ordering:** `swing_relationships` ordered by the classified swing's source chronology; `structure_transitions` ordered by the full §34J key.

### 34M. Aggregate Result

```python
class StructureAnalysis(ContractModel):
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    analyzed_candle_count: int
    analyzed_swing_count: int
    swing_relationships: tuple[SwingRelationship, ...]
    structure_transitions: tuple[StructureTransition, ...]
    current_state: CurrentStructureState | None
```

Exactly 7 fields, in this exact order. No POI, BTMM, entry, Support/Resistance-lifecycle, or Trendline-lifecycle field anywhere. For empty input: `symbol=None, timeframe=None, analyzed_candle_count=0, analyzed_swing_count=0, swing_relationships=(), structure_transitions=(), current_state=None` — never an exception.

### 34N. Error Vocabulary

**Reused unmodified from `btmm_ai_scanner.domain`** (identical semantics, same validation applied to this analyzer's own candle/identity input): `MixedSymbolAnalysisError`, `MixedTimeframeAnalysisError`, `UnsortedCandleSequenceError`, `DuplicateCandleRecordError`, `AmbiguousEventTimeAnalysisError`, `DerivedIdentityCollisionError` (6).

**New, defined in `structure/analyzer.py`** (3):

- `InvalidSwingReferenceError(ValueError)` — a supplied swing references a candle `record_id` absent from the candle tuple, or references a candle whose `availability_time_utc` is later than that swing's own `meaningful_confirmation_time_utc`.
- `UnsortedSwingSequenceError(ValueError)` — supplied swings are not canonically ordered by source chronology `(pivot_bar_index, pivot_start_time_utc, record_id)`, contain a duplicate `record_id`, or contain two consecutive entries (by source chronology) sharing the same `swing_type`.
- `InvalidStructureConfigurationError(ValueError)` — defensive guard: a candle or swing carries a null `symbol`/`timeframe` (reachable only via `.model_construct()`, bypassing Pydantic's required-field validation). **Genuinely reachable and tested from the first implementation pass** — unlike 1B-H's original `InvalidMarketMeasurementConfigurationError`, which the final audit found declared but never raised, this milestone wires its analogous guard in from day one.

Total: **9 errors** (6 reused + 3 new). No public error is declared without a genuinely reachable, tested trigger.

### 34O. Replay Equivalence Procedure — Corrected

For each replay availability group:

1. Append the complete candle group to the visible candle prefix.
2. Recompute `MarketMeasurementAnalysis` for that visible prefix (existing `analyze_market_measurements()` call) to obtain the matching `confirmed_swings`.
3. Call `analyze_structure_state(candles=visible_prefix, confirmed_swings=measurements.confirmed_swings, configuration, identity_provider)`.
4. Compare against a direct one-shot batch call of `analyze_structure_state()` over the identical candle prefix and the identical confirmed-swings tuple (obtained via a direct `analyze_market_measurements()` call over that same prefix) — every identity/fingerprint/content field must match exactly.
5. No future swing or candle influences the result, by construction — only the visible prefix is ever supplied.
6. **Unchanged transitions retain their `record_id` and their content** — a `StructureTransition`'s fields are all permanently fixed the instant it is confirmed (§34G/§34H); recomputing against a larger prefix that still contains it reproduces it identically.
7. `current_state`'s `record_id` never changes (singleton per §34K); its `content_fingerprint` changes only when its public content changes (a new confirmed swing that neither breaks an active level, nor completes bootstrap, nor supplies a missing post-transition replacement level, must not change the fingerprint).
8. **A `SwingRelationship` computed against one predecessor is never superseded in place** — if a more complete prefix reveals a source-chronologically-earlier predecessor, the analyzer emits an *additional*, differently-identified relationship (§34K); the originally emitted relationship (identified by its own current-swing/predecessor pair) is reproduced identically, unchanged, at every larger prefix that still contains that same pair.
9. Same-candle transition selection (§34J's CHoCH-priority, at-most-one-per-candle rule) is stable across repeated calls — the same candle always selects the same transition (if any), never a different one and never both.
10. A level activated within one availability group is never broken by a candle from that same group, in either batch or replay mode (§34C) — confirmed identically regardless of whether the group was ingested incrementally (replay) or was already present in a one-shot batch call.

No detector consumes only part of one availability group.

### 34P. Dependency-Direction and Package Placement

**New top-level package `src/btmm_ai_scanner/structure/`** — not `domain/`. `REPOSITORY_SCAFFOLD_PLAN.md` §3's own `domain/` documentation explicitly states "Must not contain: HH/HL/LH/LL/BOS/CHoCH (formally deferred, `P0G-B003`)"; placing this milestone's content there would contradict that standing restriction. A new package is the only non-contradictory location, exactly mirroring how `measurements/`/`domain/` themselves were brand-new packages for `1B-H-MEASUREMENTS`. Allowed dependency direction: `domain`, `measurements`, `contracts`, `config` — read-only, no new dependency on `market_data`'s pipeline/repository/replay modules (a caller may compose this analyzer's input with `market_data.InMemoryHistoricalReplaySource`'s output at its own discretion, exactly as 1B-H already does, §34O). `market_data/ports.py`'s 4 existing Protocols are untouched.

### 34Q. Exact File Scope — 16 Changed Paths (7 New Source, 8 New Test, 1 Modified) — Corrected Creation Order

**Corrected: creation order is 98–112, not 99–113.** Creation order is 0-indexed throughout this project's inventory (row 0 = `.gitignore`); the true highest existing creation-order value after `1B-H-MEASUREMENTS` is **97** (`tests/unit/test_domain_exports.py`, verified directly against the master Section 9 table), giving a pre-existing row *count* of 98 (97 + 1) — the original draft correctly used "98" as the count but incorrectly continued the new range from "98" as if it were the last *used* value, rather than from 97. The corrected range below continues from 97.

**7 new source files** (all under the new `structure/` package):

| Creation order | Path |
|---|---|
| 98 | `src/btmm_ai_scanner/structure/__init__.py` |
| 99 | `src/btmm_ai_scanner/structure/enums.py` |
| 100 | `src/btmm_ai_scanner/structure/configuration.py` |
| 101 | `src/btmm_ai_scanner/structure/relationships.py` |
| 102 | `src/btmm_ai_scanner/structure/transitions.py` |
| 103 | `src/btmm_ai_scanner/structure/current_state.py` |
| 104 | `src/btmm_ai_scanner/structure/analyzer.py` |

**8 new test files:**

| Creation order | Path |
|---|---|
| 105 | `tests/unit/test_structure_configuration.py` |
| 106 | `tests/unit/test_swing_relationships.py` |
| 107 | `tests/unit/test_structure_bootstrap.py` |
| 108 | `tests/unit/test_protected_weak_swings.py` |
| 109 | `tests/unit/test_break_and_transitions.py` |
| 110 | `tests/unit/test_structure_analyzer_api.py` |
| 111 | `tests/unit/test_structure_batch_replay_equivalence.py` |
| 112 | `tests/unit/test_structure_exports.py` |

**1 modified existing path (no new row, no renumbering — annotated in place exactly like `1B-G-REPLAY`'s `market_data/__init__.py` row 66):** `src/btmm_ai_scanner/domain/enums.py` (row 82) — `DerivedOutputType` gains exactly 3 new members, appended after the existing 5; no existing member renamed, removed, or reordered.

**Total: 16 changed paths** (7 new source + 8 new test + 1 modified existing). Source/test split 7/8. New/modified split 15/1. Creation order 98–112 (15 values, 112 − 98 + 1 = 15, correct), bringing the master inventory from 98 rows (creation order 0–97) to 113 rows (creation order 0–112). No path may be introduced silently during implementation — this is the complete, exhaustive list.

`relationships.py` owns `SwingRelationship` + swing-relationship-candidate + `detect_swing_relationships()`. `transitions.py` owns `StructureTransition`, `StructureTransitionType` usage, break-scanning, BOS/CHoCH classification, and protected/weak derivation (§34F/§34G/§34H) — the largest file. `current_state.py` owns `CurrentStructureState`. `analyzer.py` owns the error vocabulary, the locally-duplicated identity/fingerprint helpers (§34K), the `StructureAnalysis` aggregate, and `analyze_structure_state()`. `enums.py` owns `StructureDirection`, `SwingRelationshipLabel`, `StructureTransitionType` (this package's own vocabulary — separate from `domain/enums.py`, which only gains the 3 new `DerivedOutputType` members).

### 34R. Exact Test Coverage — 60 New Top-Level Test Functions — Corrected

| File | Count | Test names |
|---|---|---|
| `test_structure_configuration.py` | 5 | `test_structure_configuration_default_values_match_approved_standards`, `test_structure_configuration_is_frozen_and_immutable`, `test_structure_configuration_rejects_non_positive_tolerance_multiplier`, `test_structure_configuration_evidence_classification_is_engineering_provisional`, `test_structure_configuration_constructs_with_no_required_arguments` |
| `test_swing_relationships.py` | 8 | `test_swing_relationship_confirms_higher_high`, `test_swing_relationship_confirms_lower_high`, `test_swing_relationship_confirms_higher_low`, `test_swing_relationship_confirms_lower_low`, `test_swing_relationship_confirms_equal_high_within_tolerance`, `test_swing_relationship_confirms_equal_low_within_tolerance`, `test_swing_relationships_use_source_chronology_not_confirmation_order`, `test_swing_relationship_waits_for_unavailable_source_predecessor` |
| `test_structure_bootstrap.py` | 8 | `test_structure_bootstrap_remains_undetermined_with_zero_swings`, `test_structure_bootstrap_remains_undetermined_with_one_swing`, `test_structure_bootstrap_remains_undetermined_with_two_swings`, `test_structure_bootstrap_remains_undetermined_with_three_swings`, `test_structure_bootstrap_establishes_bullish_direction`, `test_structure_bootstrap_establishes_bearish_direction`, `test_structure_bootstrap_remains_undetermined_on_contradictory_evidence`, `test_bootstrap_uses_latest_non_equal_relationships` |
| `test_protected_weak_swings.py` | 6 | `test_protected_low_and_weak_high_active_in_bullish_structure`, `test_protected_high_and_weak_low_active_in_bearish_structure`, `test_protected_and_weak_fields_all_none_when_undetermined`, `test_protected_swing_is_mutually_exclusive_with_weak_swing_type`, `test_weak_levels_require_unbroken_swings`, `test_equal_relationship_label_does_not_block_protected_or_weak_assignment` |
| `test_break_and_transitions.py` | 12 | `test_bullish_break_requires_close_strictly_beyond_level`, `test_wick_beyond_level_without_close_does_not_break`, `test_close_exactly_at_level_does_not_break`, `test_bullish_bos_breaks_active_weak_high_and_continues_direction`, `test_bearish_bos_breaks_active_weak_low_and_continues_direction`, `test_bullish_choch_breaks_active_protected_high_and_reverses_direction`, `test_bearish_choch_breaks_active_protected_low_and_reverses_direction`, `test_bos_and_choch_are_mutually_exclusive_for_the_same_break`, `test_repeated_close_beyond_already_broken_level_emits_no_second_transition`, `test_broken_weak_level_cannot_emit_repeated_bos`, `test_level_cannot_break_in_activation_availability_group`, `test_choch_priority_prevents_same_candle_bos` |
| `test_structure_analyzer_api.py` | 10 | `test_analyze_structure_state_returns_empty_aggregate_for_empty_input`, `test_analyze_structure_state_rejects_mixed_symbol_input`, `test_analyze_structure_state_rejects_mixed_timeframe_input`, `test_analyze_structure_state_rejects_unsorted_candles`, `test_analyze_structure_state_rejects_unsorted_swings`, `test_analyze_structure_state_rejects_duplicate_swing_record_id`, `test_structure_outputs_use_engineering_provisional_evidence`, `test_analyze_structure_state_rejects_swing_referencing_missing_candle`, `test_analyze_structure_state_rejects_missing_instrument_metadata`, `test_analyze_structure_state_is_deterministic_across_repeated_calls` |
| `test_structure_batch_replay_equivalence.py` | 6 | `test_batch_and_replay_produce_identical_structure_transitions_for_the_same_prefix`, `test_batch_and_replay_produce_identical_current_state_for_the_same_prefix`, `test_unchanged_structure_transitions_retain_the_same_record_id_across_growing_prefixes`, `test_current_state_record_id_is_stable_across_growing_prefixes`, `test_current_state_fingerprint_changes_only_when_public_content_changes`, `test_structure_fingerprint_serializer_matches_market_measurement_serializer` |
| `test_structure_exports.py` | 5 | `test_structure_exports_import_successfully`, `test_structure_exports_exact_structure_owned_surface`, `test_structure_contracts_expose_no_poi_or_btmm_fields`, `test_structure_transitions_never_include_a_transitional_pending_state`, `test_structure_package_never_imports_poi_or_btmm_modules` |

**Total: 60 new top-level test functions** (5+8+8+6+12+10+6+5, unchanged distribution). Combined with the existing 320: **380**. No test class; no generated test; no helper function beginning with `test_`; no `skip`/`xfail`; no vacuous assertion — each test exercises the named behavior directly, matching every prior milestone's discipline in this project. Every rule corrected by this audit-response pass now has a named test: source-chronology comparison basis, waiting for an unavailable predecessor, latest-relationship bootstrap generalization, unbroken-status filtering on weak levels, no-repeat-break on a retired weak level, no break within a level's own activation availability group, CHoCH-priority same-candle exclusivity, cross-package fingerprint-serializer equivalence, single-value `ENGINEERING_PROVISIONAL` evidence, and the corrected structure-owned-only export surface.

### 34S. Public Exports — Corrected: `structure/__init__.py`, Exactly 12 Structure-Owned Names

```
1.  StructureDirection
2.  SwingRelationshipLabel
3.  StructureTransitionType
4.  SwingRelationship
5.  StructureTransition
6.  CurrentStructureState
7.  StructureAnalysis
8.  StructureConfiguration
9.  InvalidSwingReferenceError
10. UnsortedSwingSequenceError
11. InvalidStructureConfigurationError
12. analyze_structure_state
```

**Corrected from 19 to 12 — no `btmm_ai_scanner.domain` re-exports.** The original draft re-exported the 6 reused error classes plus `DerivedOutputIdentityProvider` from `structure/__init__.py` for "one-stop-import" ergonomics; the audit found this justification weak, since a caller integrating both milestones already imports `btmm_ai_scanner.domain` for `ConfirmedSwing`/`MarketMeasurementConfiguration` regardless. **Callers import the 6 reused errors and `DerivedOutputIdentityProvider` directly from `btmm_ai_scanner.domain`**, where they are already public. Not exported: internal candidate objects, the locally-duplicated canonical-fingerprint/identity-resolver helpers, break-scanning helpers, test fixtures — identical discipline to `domain/__init__.py`.

### 34T. Performance and Determinism

Deterministic; canonical ordered inputs (source chronology for comparisons, availability for exposure timing, §34B/§34C); stable total transition ordering (§34J); no hidden cache; no global state; no parallelism; no thread requirement; no wall clock; relationship classification is a single pass per swing type over the available same-type swings; break/transition detection is a single forward scan over availability groups maintaining the current active levels — O(candles + swings) per batch call, not quadratic. Repeated-prefix replay analysis across a complete session may be provisionally O(n²) in total (recomputing both `MarketMeasurementAnalysis` and `StructureAnalysis` from scratch at every availability group), documented as acceptable and non-production, identical to 1B-H's own accepted precedent (§33X).

### 34U. Explicit Exclusions

POI creation; order blocks; FVGs; candlestick POIs; Equal-Level sweep lifecycle; Support/Resistance lifecycle; Trendline lifecycle; BTMM manipulation; entry signals; stop loss; take profit; risk sizing; TradingView rendering; Telegram alerts; news; backtesting statistics; strategy scoring; paper trading; broker connectivity; MT5/MT4; AI inference; production approval.

### 34V. Baseline, Quality Gates, and Stop Conditions

**Execution baseline / current HEAD and `origin/main`:** `0dc694ad33ee8e1707ea9e2614506da43b37aebb`. Python `3.12.13`; `uv` `0.11.30`; Pydantic `2.13.4`. Full pytest-collected tests: `398`. Original baseline suite: `34 passed`. Existing top-level test functions: `320`. Existing `measurements`/`domain` exports: `33`. Inventory: `98` rows. No dependency change expected.

Future implementation must pass, unmodified in procedure from every prior milestone: `uv lock --check`; `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy src tests`; `uv run pytest -q` (expect `458` = `398` + `60`, or an exact, explained parametrize-driven discrepancy exactly as documented for every prior milestone); `uv run pytest -q tests/test_import_smoke.py tests/test_config_precedence.py` (expect `34 passed`).

Mandatory stop conditions (unchanged from every prior milestone's discipline): stop and report if any quality gate fails and cannot be fixed by a genuine, disclosed correction; stop if the approved 16-path scope would need to grow; stop if a 17th path, an 8th source file, a 9th test file, or a 61st test function is discovered necessary mid-implementation — report and request a scope amendment rather than silently expanding.

### 34W. Author Decisions Required — Corrected

Every numbered item below requires an explicit author decision before implementation may begin — none is implemented, committed, or authorized by this section alone:

1. The identifier `1B-I-STRUCTURE` and title "Structure State and Transition Foundation."
2. The input contract: `candles` + `confirmed_swings` directly, not the full `MarketMeasurementAnalysis` (§34B).
3. **Corrected:** the swing input is canonically ordered by **source chronology** `(pivot_bar_index, pivot_start_time_utc, record_id)`, decoupled from availability/confirmation ordering, which governs only output exposure timing (§34B/§34C).
4. The 6-member `SwingRelationshipLabel` enum, the source-chronology same-type-predecessor comparison basis, and the reused-value `0.10` ATR-multiplier tolerance (§34D).
5. **Corrected:** the generalized bootstrap rule — the *latest classified* HIGH and LOW relationships must agree, non-equal — replacing the original fixed "2nd vs 1st" rule, plus the exact initial protected/weak assignment upon bootstrap (§34D).
6. No separate initialization/transitional state for bootstrap, and no separate transitional state for CHoCH; the guarded-CHoCH no-op when no eligible opposite protected candidate exists (§34D/§34H).
7. The 3-member `StructureDirection` enum and no separate structure-state enum (§34E).
8. **Corrected:** the transition-sensitive, symmetric unbroken-filtered protected/weak derivation rule — updated only at bootstrap/BOS/CHoCH, never merely because a newer swing confirms, and never pointing at an already-retired swing (§34F).
9. Close-based break confirmation only; wick-only penetration is never a break; the two separate `broken_level_price`/`break_close_price` fields (§34G).
10. **Corrected:** the exact bullish/bearish BOS and CHoCH prerequisite/effect rules, including no-automatic-replacement retirement of the broken weak level (§34H).
11. **Corrected:** the exact `StructureTransition`/`CurrentStructureState` contracts and field lists, including `weak_swing_id`'s nullability and `CurrentStructureState` carrying its own identity/fingerprint (§34I).
12. **Corrected:** the exact transition-ordering key and the one-transition-per-candle, CHoCH-priority, no-chaining policy (§34J).
13. Reuse of `DerivedOutputIdentityProvider`/`DerivedOutputType` (3 new members added to `domain/enums.py`), the deliberate local duplication of the canonical-fingerprint/identity-resolver implementation with its documented maintenance risk, and the required cross-package equivalence test (§34K).
14. **Corrected:** the exact semantic keys per output type, including `SWING_RELATIONSHIP`'s corrected (current, predecessor) key and `CURRENT_STRUCTURE_STATE`'s simplified key (§34K).
15. **Corrected:** the unambiguous evidence-classification policy — every output stores exactly `ENGINEERING_PROVISIONAL`, distinct from the register's own document-level approval-status vocabulary — and the one reused (not newly invented) `0.10` tolerance value as the only numeric threshold, with `minimum_price_tick`'s absence explicitly justified (§34K).
16. The exact `analyze_structure_state()` signature and behavior table (§34L).
17. The exact 7-field `StructureAnalysis` aggregate and field order (§34M).
18. The exact 9-error vocabulary — 6 reused unmodified, 3 new, each with a genuinely reachable trigger (§34N).
19. **Corrected:** the replay-equivalence procedure, including relationship non-supersession and activation-group break timing (§34O).
20. The new `structure/` top-level package (not `domain/`) and its dependency direction (§34P).
21. **Corrected:** the exact 16-path file scope with creation order **98–112** (not 99–113) — 7 new source, 8 new test, 1 modified existing (§34Q).
22. **Corrected:** the exact 60 new top-level test names, counts, and per-file distribution, including the 10 tests added for this correction pass (§34R).
23. **Corrected:** the exact 12-name `structure/__init__.py` export list and order, with no `domain` re-exports (§34S).
24. The performance/determinism policy, including the accepted provisional O(n²) full-session replay cost (§34T).
25. The explicit exclusion list (§34U).

### 34X. Status and Next Action

**Status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** All 61 items above are approved without modification — see §34Y.

### 34Y. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected `1B-I-STRUCTURE` Structure State and Transition Foundation architecture exactly as documented (§34A–§34X), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Exact approved scope:** 16 total affected paths (15 new, 1 modified); 7 new source files; 8 new test files; 1 modified existing source file (`src/btmm_ai_scanner/domain/enums.py`, +3 `DerivedOutputType` members); 60 new top-level test functions (380 combined with the existing 320); 12 structure-owned public exports, no `domain` re-exports; inventory 98 → 113 under batch tag `1B-I-STRUCTURE`, creation order 98–112; no dependency change; no existing `market_data` Protocol modification.

The author approved, without modification, all 61 items listed in the approval message: the identifier and title (1–2); the input boundary and source-chronology/availability separation (3–7); the swing relationship model and its ATR-normalized tolerance, with no new ATR calculation or minimum-price-tick rule (8–11); the generalized latest-relationship bootstrap rule and its exact bullish/bearish initial protected/weak assignments (12–18); the transition-sensitive, symmetrically unbroken-filtered protected/weak lifecycle, including exclusivity and the equal-relationship non-interference rule (19–25); the phased availability-group processing order and its no-retroactive-break consequence (26–29); the strict close-based break policy with separate `broken_level_price`/`break_close_price` fields (30–37); the exact bullish/bearish BOS and CHoCH prerequisite/effect rules, including no-automatic-replacement retirement and the guarded no-impossible-partial-CHoCH rule (38–42); the one-transition-per-candle, CHoCH-priority, no-chaining policy (43–46); the immutable-fact/stable-snapshot semantics for all three output types and the corrected current-state semantic key (47–49); reuse of `DerivedOutputIdentityProvider`/`DerivedOutputType`, the disclosed local duplication of the canonical serializer with its required byte-equivalence test (50–53); the unambiguous `ENGINEERING_PROVISIONAL`-only evidence policy, distinct from document-level approval-status vocabulary (54–55); the exact public API signature (56); the exact 12-name export surface with no `domain` re-exports (57–58); the exact eight test files, 60-name test plan, and 5+8+8+6+12+10+6+5 distribution, including the 12 named required-coverage areas (59–60); and the complete exclusion list (61).

**This approval authorizes exactly one complete implementation cycle** covering all 16 approved paths at once (no per-file decision groups), followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started — this remains a documentation-only approval.**

**Next action:** commit and push this documentation-only author approval, then implement all 16 approved paths in one complete controlled cycle, followed by one final architectural audit, at most one correction cycle for a genuine defect, one implementation commit, and one compact closure commit.
