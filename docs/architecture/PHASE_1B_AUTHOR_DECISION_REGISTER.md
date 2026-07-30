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

## 34. Structure State and Transition Foundation — Architecture (Implemented, Closed)

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** (See §34Y for the author approval record and §34Z for the implementation, audit, and closure record.)

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

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** All 61 items approved without modification (see §34Y) have since been implemented exactly as approved, with one Ruff/mypy-only correction cycle (see §34Z).

### 34Y. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected `1B-I-STRUCTURE` Structure State and Transition Foundation architecture exactly as documented (§34A–§34X), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Exact approved scope:** 16 total affected paths (15 new, 1 modified); 7 new source files; 8 new test files; 1 modified existing source file (`src/btmm_ai_scanner/domain/enums.py`, +3 `DerivedOutputType` members); 60 new top-level test functions (380 combined with the existing 320); 12 structure-owned public exports, no `domain` re-exports; inventory 98 → 113 under batch tag `1B-I-STRUCTURE`, creation order 98–112; no dependency change; no existing `market_data` Protocol modification.

The author approved, without modification, all 61 items listed in the approval message: the identifier and title (1–2); the input boundary and source-chronology/availability separation (3–7); the swing relationship model and its ATR-normalized tolerance, with no new ATR calculation or minimum-price-tick rule (8–11); the generalized latest-relationship bootstrap rule and its exact bullish/bearish initial protected/weak assignments (12–18); the transition-sensitive, symmetrically unbroken-filtered protected/weak lifecycle, including exclusivity and the equal-relationship non-interference rule (19–25); the phased availability-group processing order and its no-retroactive-break consequence (26–29); the strict close-based break policy with separate `broken_level_price`/`break_close_price` fields (30–37); the exact bullish/bearish BOS and CHoCH prerequisite/effect rules, including no-automatic-replacement retirement and the guarded no-impossible-partial-CHoCH rule (38–42); the one-transition-per-candle, CHoCH-priority, no-chaining policy (43–46); the immutable-fact/stable-snapshot semantics for all three output types and the corrected current-state semantic key (47–49); reuse of `DerivedOutputIdentityProvider`/`DerivedOutputType`, the disclosed local duplication of the canonical serializer with its required byte-equivalence test (50–53); the unambiguous `ENGINEERING_PROVISIONAL`-only evidence policy, distinct from document-level approval-status vocabulary (54–55); the exact public API signature (56); the exact 12-name export surface with no `domain` re-exports (57–58); the exact eight test files, 60-name test plan, and 5+8+8+6+12+10+6+5 distribution, including the 12 named required-coverage areas (59–60); and the complete exclusion list (61).

**This approval authorizes exactly one complete implementation cycle** covering all 16 approved paths at once (no per-file decision groups), followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started — this remains a documentation-only approval.**

### 34Z. Implementation, Final Audit, and Closure Record

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

**Implementation commit:** `74fd50c6a44c208153769d2f1947bdfa7ff0d3cf`. **Commit message:** "Implement 1B-I-STRUCTURE foundation". **Push:** succeeded to `origin/main`. Preflight baseline: `debcd4f43053a54ad928fabcfe6fcd0e65f0aa4f` (the approval commit, §34Y).

**Implemented scope:** exactly 16 committed paths — 7 new source files (`structure/__init__.py`, `structure/enums.py`, `structure/configuration.py`, `structure/relationships.py`, `structure/transitions.py`, `structure/current_state.py`, `structure/analyzer.py`), 8 new test files, 1 modified existing path (`domain/enums.py`, +3 `DerivedOutputType` members, verified byte-exact against the approved 3-member extension via `git diff`). Source/test split 7/8; new/modified split 15/1. No dependency or lockfile change. No `market_data` or `domain` Protocol modification.

**Final architectural audit verdict: one genuine correction cycle applied (Ruff/mypy findings only), then `A. PASS — READY TO COMMIT`.** No architecture, contract, test-name, test-count, path, export, dependency, or Protocol change occurred in the correction cycle:

1. `ruff check` findings: an unused `StructureDirection` import in `structure/analyzer.py`; an unused `AmbiguousEventTimeAnalysisError` import in `tests/unit/test_structure_analyzer_api.py`; a tuple-concatenation style nit (`RUF005`) in `tests/unit/test_break_and_transitions.py`, corrected to iterable unpacking. All three removed/corrected with no behavioral change.
2. `mypy` findings: in `structure/transitions.py`, the event-processing loop's local variables (`candle`, `swing`, `relationship`) collided with earlier same-named loop variables of narrower declared types from the event-construction loops earlier in the same function, causing three "incompatible types in assignment" errors; corrected by renaming the event-construction loop variables (`event_candle`, `event_swing`, `event_relationship`) rather than altering any runtime logic. In `structure/analyzer.py`, the `# type: ignore[call-arg]` comment on the manual `CurrentStructureState(...)` construction no longer matched the actual reported error code once the generic `_finalize` path was excluded from comparison; corrected to `# type: ignore[arg-type]`, matching the established precedent from `domain/analyzer.py`.

No other defect was found. Every other approved control was audited and confirmed exactly as designed: source-chronology `(pivot_bar_index, pivot_start_time_utc, record_id)` as the sole comparison basis for relationship classification, bootstrap, and protected/weak derivation, fully decoupled from confirmation/availability ordering (§34B/§34C); the merged three-kind chronological event-timeline walk achieving strict no-look-ahead and same-timestamp activation-group immunity without an explicit "group" data structure (§34C/§34G, verified by `test_level_cannot_break_in_activation_availability_group`); the generalized latest-relationship bootstrap rule and its exact bullish/bearish initial protected/weak assignments (§34D); the transition-sensitive, symmetrically unbroken-filtered protected/weak lifecycle, including no-automatic-replacement retirement to `None` and the equal-relationship non-interference rule (§34F); the strict close-only break policy with separate `broken_level_price`/`break_close_price` fields, no wick-only break, no equality break (§34G); the exact bullish/bearish BOS and CHoCH prerequisite/effect rules, including guarded CHoCH no-op when no eligible opposite protected candidate exists (§34H); the one-transition-per-candle, CHoCH-priority, no-chaining policy (§34J, verified by `test_choch_priority_prevents_same_candle_bos`); the corrected `SWING_RELATIONSHIP` (both-ID), `STRUCTURE_TRANSITION`, and `CURRENT_STRUCTURE_STATE` (singleton) semantic keys (§34K); the locally-duplicated canonical-fingerprint/identity-resolver implementation verified byte-identical to `1B-H-MEASUREMENTS`'s own `domain/analyzer.py` implementation via a dedicated cross-package equivalence test (§34K/§34R); the single-value `ENGINEERING_PROVISIONAL` evidence policy on every output (§34K); the exact 9-error vocabulary (§34N); replay-prefix equivalence for transitions and current state, including record_id stability across growing prefixes and fingerprint-changes-only-with-content (§34O); and the exact 12-name `structure/__init__.py` export surface with no `domain` re-exports (§34S).

**Verification results:** full suite **458 passed**; original baseline suite **34 passed**; new top-level test functions **60** (5+8+8+6+12+10+6+5 across the 8 new files, exact approved distribution); existing top-level test functions **320**; combined top-level test functions **380** (AST-verified); full pytest-collected test total **458** (398 existing + 60 new — no `@pytest.mark.parametrize` used by any of the 8 new files, so the combined and collected totals match exactly); public exports **12** (exact approved order, all import successfully); `uv lock --check` passes; `ruff format --check .` passes; `ruff check .` passes; `mypy src tests` passes with no issues across 89 source files.

**Inventory:** before **98**, new rows **15**, final **113**, batch tag `1B-I-STRUCTURE`, creation order **98–112** — unchanged by this closure. No inventory row was added, removed, renamed, or renumbered beyond what was already recorded at approval time.

**No dependency change. No `market_data` or `domain` Protocol change. No production approval granted by this record.** The milestone remains `NOT PRODUCTION-APPROVED`.

**Next controlled action:** define the **POI Detection Foundation**, using the completed measurement and structure foundations. This next architecture definition should cover, without implementing yet: POI candidate identity; POI type taxonomy; order-block candidates; fair-value-gap candidates; support/resistance POI references; trendline POI references where approved; equal-level liquidity references; candlestick-pattern POIs; structural context requirements; strong-timeframe precedence; POI overlap and merge rules; POI confirmation; POI validity; POI breach; POI reclaim; POI invalidation; POI availability time; no-look-ahead behavior; deterministic identity and fingerprinting; and historical replay equivalence. That milestone must not yet include BTMM manipulation lifecycle, entry signals, stop loss, take profit, position sizing, visualization, Telegram alerts, broker execution, AI inference, or production approval. That milestone is not started by this record.

**Next action:** commit and push this documentation-only author approval, then implement all 16 approved paths in one complete controlled cycle, followed by one final architectural audit, at most one correction cycle for a genuine defect, one implementation commit, and one compact closure commit.

## 35. POI Detection and Lifecycle Foundation — Architecture (Implemented, Closed)

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** (See §35AP for the author approval record and §35AQ for the implementation, final audit, and closure record.) This was a single, compact, accelerated architecture definition for `1B-J-POI`, handled as one decision group (no per-POI-family approval cycles), per the completed and closed `1B-H-MEASUREMENTS` (§33) and `1B-I-STRUCTURE` (§34) foundations. This section was corrected in one consolidated documentation-only correction pass following a focused read-only architectural audit; the author approved the corrected architecture in full (§35AP), and the approved architecture has since been implemented, verified, architecturally audited, committed, pushed, and closed (§35AQ).

### 35A. Milestone Identity, Scope Honesty, and Title

**Batch identifier: `1B-J-POI`.**

**Title decision:** the two candidate titles offered were "POI Detection Foundation" (A) and "POI Detection and Lifecycle Foundation" (B). **This architecture selects B.** The already-approved `POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` standard (Ambiguity 15) and the already-approved `POI_FRESHNESS_AND_AGE_STANDARD.md` (`P0G-B006`/`P0G-B007`) together define a complete, deterministic, publicly-observable state machine — `CLOSE_BREACH_CANDIDATE` → `RECLAIM_CONFIRMED`/`GENUINE_INVALIDATION_CONFIRMED` → `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`/`RECLAIM_WITHOUT_DISPLACEMENT`/`RECLAIM_FAILED` → `FALSE_INVALIDATION_CONFIRMED`, plus repeated-tap counting and `FRESH`/`INTERACTED` freshness tracking — that this milestone implements and exposes as public `PoiLifecycleTransition` records and `CurrentPoiState` fields for **exactly 18 of the 32 implementable POI specifications** (10 volume + 6 price-action + Support + Resistance; the 2 Equal-Level and 12 Period-Level types are permanently `NOT_APPLICABLE`, §35D/§35V). **Corrected by the focused audit:** earlier drafts of this section stated this count as "32" or "30" in four places — both were arithmetic errors; the correct figure, 18, is derived as `32 implementable − 2 equal-level reference types − 12 period-level types = 18`, and not coincidentally matches the already-approved "18 propagated POIs" figure from the Phase 0G lifecycle work. Even at the corrected, smaller figure of 18, calling this milestone "Detection" only would still misdescribe its actual public behavior — 18 types with a full public breach/reclaim/invalidation state machine remains substantial. Title: **POI Detection and Lifecycle Foundation.**

**Initial status (historical — superseded by author approval, §35AP):** `ARCHITECT-RECOMMENDED`, `AUTHOR-DECISION REQUIRED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`. **Current status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**What this milestone completes:** it is the first milestone to consume `1B-H-MEASUREMENTS` (`ConfirmedSwing`, `DisplacementObservation`, `EqualLevelCluster`, `SupportResistanceZone`, `Trendline`, `analyze_market_measurements()`), transforming its outputs plus raw `NormalizedCandle` sequences into POI candidates, confirmed POI observations, lifecycle transitions, and a current POI state snapshot per symbol/timeframe. **Corrected by the focused audit (Part 5): `1B-I-STRUCTURE`'s outputs (`StructureAnalysis`, `SwingRelationship`, `StructureTransition`, `CurrentStructureState`) are not consumed by this milestone at all** — no implementable POI type's approved rule requires them (§35S); they remain available for direct use and for a possible later milestone that identifies a genuine need.

### 35B. Primary Domain Boundary and Concept Separation

**Corrected by the focused audit (Part 5 — Option B adopted): `StructureAnalysis` is removed from the primary boundary and from every public input.** The audit found that no detector for any of the 32 implementable types uses `StructureAnalysis` for candidacy, confirmation, or lifecycle gating anywhere in §35J-§35R — its only described effect was a structural consistency check, making it a required input with no deterministic effect (a design smell). Structural context (`StructureDirection`/`SwingRelationship`/`StructureTransition`/`CurrentStructureState`) may be added in a **later milestone**, and only for the specific POI types whose approved rule is found to genuinely require it — never as a blanket, always-required input carried "just in case."

**Exact deterministic boundary:**

```
multi-timeframe canonical NormalizedCandle inputs
  + MarketMeasurementAnalysis inputs (per timeframe)
  -> source-family POI candidates (per detector family, §35J-§35R)
  -> POI confirmation (§35T)
  -> cross-family and cross-timeframe normalization (shared PoiObservation contract, §35E)
  -> overlap/merge handling (§35X)
  -> strong-timeframe precedence handling (§35I)
  -> immutable/current-snapshot PoiObservation records (§35E)
  -> PoiLifecycleTransition records, for the 18 lifecycle-eligible types only (§35V)
  -> current CurrentPoiState snapshot per confirmed POI instance (§35Z)
  -> PoiAnalysis aggregate (§35Z)
```

**Five structurally separate concepts, never conflated (per `docs/PROJECT_SCOPE.md` §7, unmodified by this milestone):**

1. **POI detection/confirmation** — did a candidate satisfy its own approved formation/candle-geometry rule; a public `PoiObservation` exists at all only once this passes (this milestone; candidate/confirmation model, §35T; there is no separate public "validity" axis, §35U).
2. **POI lifecycle status** — is the confirmed POI currently `FRESH`/`INTERACTED`, and has it been breached/reclaimed/invalidated (this milestone, for **exactly 18** of the 32 implementable specifications — 10 volume + 6 price-action + Support + Resistance; the remaining 14 — 2 equal-level + 12 period-level — are permanently `PoiLifecycleStatus = NOT_APPLICABLE`, §35D/§35V).
3. **BTMM-pattern validity** — the 10-gate BTMM state machine (`knowledge/btmm/BTMM_STATE_MACHINE.md`) is explicitly out of scope for this milestone; a `PoiObservation`/`CurrentPoiState` never carries a BTMM field.
4. **Entry validity** — stop loss, take profit, position sizing, entry confirmation: out of scope.
5. **Trade outcome** — profitability, win/loss, risk-to-reward: out of scope.

**A confirmed, `FRESH` `PoiObservation` implies none of:** a valid BTMM manipulation setup; a valid trade entry; a profitable outcome; production readiness. Every one of these remains a separate, later, unimplemented concept.

### 35C. Exact 36-POI Coverage and Implementability Gate

**Total approved POI specifications in the book: 36** (10 volume-based, 6 price-action, 20 structural), verified against `knowledge/POI_COVERAGE_MATRIX.md` and `knowledge/POI_MASTER_CATALOG.md` — every row has a corresponding `knowledge/poi_rules/` file and every file has a corresponding row; no orphan and no omission.

**Readiness gate outcome (Part 36): Option A selected** — implement every fully deterministic specification in one milestone; keep the 4 genuinely non-deterministic specifications documented, excluded from the public `PoiType` enum, and explicitly deferred. **32 of 36 IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL; 4 of 36 DEFERRED; 0 of 36 BLOCKED.** Every one of the 32 implementable specifications required at least one already-completed, already-author-approved engineering gap-fill (candle-size ratios, small-candle ratios, tolerance formulas, availability timing, zone-source decisions) — none is "book-exact" without that prior approved work, so none is tagged plain `IMPLEMENTABLE`; all 32 are tagged `IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL`, and the gap-fills are already-approved (Ambiguities 1-15, RECON-D1-D5, GROUP3-D1-D9), not newly invented here.

**Full 36-row matrix.** Shared formulas are referenced by name rather than repeated in every cell (full formulas are quoted in full, once, in the family subsections §35J-§35R and in `knowledge/MEASUREMENT_STANDARDS.md`). Legend: **CGI** = `CONDITIONAL_GENERIC_INHERITANCE` (Group 2, RECON-D1/D2/D3/D5), **DGI** = `DIRECT_GENERIC_INHERITANCE` (Group 1), **G3** = Group 3 completed candlestick (GROUP3-D1-D9), **EXCL-EH/L** = excluded by design (`P0G-B004` Option B), **EXCL-TL** = excluded by design (`P0G-B005` Option B), **N/A** = not applicable (single price point, no zone). **Corrected by the focused audit: a new explicit "Lifecycle" column replaces the ambiguous per-row group labels for applicability purposes — every row is now unambiguously `FULL` or `NOT_APPLICABLE`** (the CGI/DGI/G3/EXCL labels are retained alongside, in the "Provenance" column, purely to preserve traceability to which approved decision supplies each row's formulas).

| # | POI | Family | `PoiType` member | Dir. | Zone/level source | Confirmation/availability | Lifecycle | Provenance | Evidence | Readiness | Owner module |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Buy Order Block | VOLUME (Option B proxy, §35Q) | `BUY_ORDER_BLOCK` | Bullish | Full range of smaller (first) candle | `order_block_available_time` = displacement candle close (RECON-D1) | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/order_blocks.py` |
| 2 | Sell Order Block | VOLUME (Option B proxy) | `SELL_ORDER_BLOCK` | Bearish | Full range of smaller (first) candle | Same as #1, mirrored | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/order_blocks.py` |
| 3 | Buy Fair Value Gap | VOLUME (Option B proxy) | `BUY_FAIR_VALUE_GAP` | Bullish | 1st-candle-high to 3rd-candle-low | `fvg_available_time` = 3rd candle close (RECON-D5); rejected if gap no longer valid at that close | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/fair_value_gaps.py` |
| 4 | Sell Fair Value Gap | VOLUME (Option B proxy) | `SELL_FAIR_VALUE_GAP` | Bearish | 3rd-candle-high to 1st-candle-low | Same as #3, mirrored | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/fair_value_gaps.py` |
| 5 | Buy-to-Sell Candle | VOLUME (Option B proxy) | `BUY_TO_SELL_CANDLE` | Bearish | Candidate candle full range | `reversal_confirmation_time` = confirmed post-candidate reversal close within 3-bar window | **FULL** | DGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/reversal_candles.py` |
| 6 | Sell-to-Buy Candle | VOLUME (Option B proxy) | `SELL_TO_BUY_CANDLE` | Bullish | Candidate candle full range | Same as #5, mirrored | **FULL** | DGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/reversal_candles.py` |
| 7 | Base Rally | VOLUME (Option B proxy) | `BASE_RALLY` | Bullish | Base High to Base Low (2-6 candles) | `base_available_time` = departure candle close (RECON-D2) | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/bases.py` |
| 8 | Base Drop | VOLUME (Option B proxy) | `BASE_DROP` | Bearish | Base High to Base Low (2-6 candles) | Same as #7, mirrored | **FULL** | CGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/bases.py` |
| 9 | Bullish Pressure Wick | VOLUME (Option B proxy) | `BULLISH_PRESSURE_WICK` | Bullish | `MIN(Open,Close)` to Candle Low (wick only) | Own candle close (CANDIDATE -> CONFIRMED) | **FULL** | DGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/pressure_wicks.py` |
| 10 | Bearish Pressure Wick | VOLUME (Option B proxy) | `BEARISH_PRESSURE_WICK` | Bearish | Candle High to `MAX(Open,Close)` (wick only) | Same as #9, mirrored | **FULL** | DGI | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/pressure_wicks.py` |
| 11 | Bullish Engulfing | PRICE_ACTION | `BULLISH_ENGULFING` | Bullish | First (engulfed, smaller, bearish) candle's full range | `engulfing_poi_available_time` = engulfing candle close (GROUP3-D2) | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/engulfing.py` |
| 12 | Bearish Engulfing | PRICE_ACTION | `BEARISH_ENGULFING` | Bearish | First (engulfed, smaller, bullish) candle's full range | Same as #11, mirrored | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/engulfing.py` |
| 13 | Hammer | PRICE_ACTION | `HAMMER` | Bullish | `MIN(Open,Close)` to Candle Low (rejection wick only, GROUP3-D5) | Own candle close (GROUP3-D6) | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/single_candle_reversals.py` |
| 14 | Shooting Star | PRICE_ACTION | `SHOOTING_STAR` | Bearish | Candle High to `MAX(Open,Close)` (rejection wick only) | Own candle close | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/single_candle_reversals.py` |
| 15 | Morning Star | PRICE_ACTION | `MORNING_STAR` | Bullish | Middle doji candle's full range (GROUP3-D8) | 3rd candle close (GROUP3-D9) | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/three_candle_stars.py` |
| 16 | Evening Star | PRICE_ACTION | `EVENING_STAR` | Bearish | Middle doji candle's full range | 3rd candle close | **FULL** | G3 | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/three_candle_stars.py` |
| 17 | Bullish Trendline | STRUCTURAL | *(none)* | Bullish | **No finite zone geometry approved — line only** | N/A | N/A | EXCL-TL | N/A | **DEFERRED** | *(none — reference only)* |
| 18 | Bearish Trendline | STRUCTURAL | *(none)* | Bearish | **No finite zone geometry approved — line only** | N/A | N/A | EXCL-TL | N/A | **DEFERRED** | *(none — reference only)* |
| 19 | Support | STRUCTURAL | `SUPPORT_ZONE` | Bullish | Inherited unmodified from `domain.SupportResistanceZone` (`zone_top`/`zone_bottom`) | Inherited `availability_time_utc` | **FULL** | CGI (RECON-D4) | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/reference_zones.py` |
| 20 | Resistance | STRUCTURAL | `RESISTANCE_ZONE` | Bearish | Inherited unmodified from `domain.SupportResistanceZone` | Inherited `availability_time_utc` | **FULL** | CGI (RECON-D4) | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/reference_zones.py` |
| 21 | Equal Highs | STRUCTURAL | `EQUAL_HIGHS_LIQUIDITY` | Bearish (liquidity above) | Inherited unmodified from `domain.EqualLevelCluster` | Inherited `availability_time_utc` | **NOT_APPLICABLE — liquidity reference only, never breached/reclaimed/invalidated** | EXCL-EH/L | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL (detection only) | `poi/reference_zones.py` |
| 22 | Equal Lows | STRUCTURAL | `EQUAL_LOWS_LIQUIDITY` | Bullish (liquidity below) | Inherited unmodified from `domain.EqualLevelCluster` | Inherited `availability_time_utc` | **NOT_APPLICABLE** — same as #21 | EXCL-EH/L | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL (detection only) | `poi/reference_zones.py` |
| 23 | Swing High | STRUCTURAL | *(none)* | Bearish | Single price point — already fully represented by `domain.ConfirmedSwing` | N/A | N/A | N/A | N/A | **DEFERRED — not duplicated** | *(none — use `domain.ConfirmedSwing` directly)* |
| 24 | Swing Low | STRUCTURAL | *(none)* | Bullish | Single price point — already fully represented by `domain.ConfirmedSwing` | N/A | N/A | N/A | N/A | **DEFERRED — not duplicated** | *(none — use `domain.ConfirmedSwing` directly)* |
| 25 | Previous Day High | STRUCTURAL | `PREVIOUS_DAY_HIGH` | Bearish | Zero-height point zone (UTC calendar-day max, §35R) | Period close, UTC half-open `[00:00:00, next-day 00:00:00)` | **NOT_APPLICABLE — deterministic reference level, no candidate to reject** | N/A (`rejection_criterion_status = NOT_APPLICABLE`) | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 26 | Previous Day Low | STRUCTURAL | `PREVIOUS_DAY_LOW` | Bullish | Zero-height point zone (UTC calendar-day min) | Same as #25 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 27 | Previous Week High | STRUCTURAL | `PREVIOUS_WEEK_HIGH` | Bearish | Zero-height point zone (ISO week max) | Period close, ISO week `[Mon 00:00:00 UTC, next Mon 00:00:00 UTC)` | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 28 | Previous Week Low | STRUCTURAL | `PREVIOUS_WEEK_LOW` | Bullish | Zero-height point zone (ISO week min) | Same as #27 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 29 | Previous Month High | STRUCTURAL | `PREVIOUS_MONTH_HIGH` | Bearish | Zero-height point zone (calendar-month max) | Period close, UTC calendar month `[1st 00:00:00, 1st-of-next-month 00:00:00)` | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 30 | Previous Month Low | STRUCTURAL | `PREVIOUS_MONTH_LOW` | Bullish | Zero-height point zone (calendar-month min) | Same as #29 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 31 | Current Day High | STRUCTURAL | `CURRENT_DAY_HIGH` | Bearish | Zero-height point zone (running max, current UTC day, content-evolving snapshot, §35E/§35R) | Updates on every new visible candle within the window; stable identity, changing fingerprint | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 32 | Current Day Low | STRUCTURAL | `CURRENT_DAY_LOW` | Bullish | Zero-height point zone (running min, current UTC day) | Same as #31 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 33 | Current Week High | STRUCTURAL | `CURRENT_WEEK_HIGH` | Bearish | Zero-height point zone (running max, current ISO week) | Same as #31 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 34 | Current Week Low | STRUCTURAL | `CURRENT_WEEK_LOW` | Bullish | Zero-height point zone (running min, current ISO week) | Same as #31 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 35 | Current Month High | STRUCTURAL | `CURRENT_MONTH_HIGH` | Bearish | Zero-height point zone (running max, current calendar month) | Same as #31 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |
| 36 | Current Month Low | STRUCTURAL | `CURRENT_MONTH_LOW` | Bullish | Zero-height point zone (running min, current calendar month) | Same as #31 | **NOT_APPLICABLE** | N/A | ENGINEERING_PROVISIONAL | IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL | `poi/period_levels.py` |

**Totals: 32 IMPLEMENTABLE_WITH_AUTHOR_GAP_FILL (10 volume + 6 price-action + 2 structural reference-zone + 2 structural equal-level [detection-only] + 12 structural period-level); 4 DEFERRED (2 Trendline, 2 Swing High/Low); 0 BLOCKED.** No two distinct approved POI specifications were merged into one row to reduce the count; rows 1-36 map 1:1 to the book's 36 specifications. No row claims full implementability beyond its own genuinely complete deterministic rule set.

**Corrected lifecycle-applicability totals (the focused audit's principal finding): exactly 18 of the 32 implementable types are `FULL` (lifecycle-eligible); exactly 14 are `NOT_APPLICABLE`.** `32 implementable − 2 equal-level reference types (rows 21-22) − 12 period-level types (rows 25-36) = 18 lifecycle-eligible types` — rows 1-16 (all 10 volume + all 6 price-action) plus rows 19-20 (Support, Resistance) = 18. Earlier drafts of this section stated "30" (32−2, omitting the 12 period-level subtraction) or "32" in four locations (§35A, §35B, §35D, §35V) — all four are corrected to 18 by this pass. For the 14 `NOT_APPLICABLE` types: `PoiLifecycleStatus` is fixed at `NOT_APPLICABLE` for the entire lifetime of every such observation; no `PoiLifecycleTransition` is ever emitted; no breach, reclaim, mitigation, or invalidation state machine ever runs against them (§35P for Equal Highs/Lows; §35R for the 12 period levels).

**Why Trendline is deferred, not implemented (Part 17):** `bullish_trendline.md`/`bearish_trendline.md` state explicitly: "a trendline is a single diagonal price level at each bar... not a two-sided zone." Only Touch/Pierce Tolerance *bands* around the moving line are quantified — never a static `zone_top`/`zone_bottom` pair. Inventing a finite zone (e.g., "band width = tolerance") would be an unapproved rule invention, not a reuse of an existing standard. Per Part 17's explicit instruction, this specification is marked deferred rather than inventing a geometry. `TRENDLINE_BREAK_CANDIDATE` and the generic bounded-POI lifecycle standard are both explicitly excluded from Trendlines by the author-approved `P0G-B005` Option B deferral — a POI-typed wrapper would falsely imply lifecycle applicability that the source specification itself prohibits.

**Why Swing High/Swing Low are deferred, not duplicated (Part 3):** both files state explicitly: "a Swing High is a single price level (Pivot Price), not a zone." `domain.ConfirmedSwing` (1B-H-MEASUREMENTS) already is the canonical, immutable, identity-bearing, fingerprinted representation of this exact fact — `swing_type`, `pivot_price`, `pivot_bar_index`, `availability_time_utc`, `evidence_classification` are all already present. Wrapping it in a `SwingHighPoi`/`SwingLowPoi` contract would create a second, parallel identity for the same underlying fact — a duplicate contract this milestone's own Part 3 instruction ("Do not design duplicate contracts where an existing immutable output already provides the required fact") explicitly prohibits. Callers needing "Swing High/Swing Low as a POI" use `domain.ConfirmedSwing` directly; no `PoiType.SWING_HIGH`/`SWING_LOW` member is created.

### 35D. Taxonomy — `PoiFamily`, `PoiDirection`, `PoiType`, and Separated Status Axes

**`PoiFamily`** (`StrEnum`, 3 members, matching the book's own three official categories): `VOLUME`, `PRICE_ACTION`, `STRUCTURAL`.

**`PoiDirection`** (`StrEnum`, 2 members): `BULLISH`, `BEARISH`. **No `NEUTRAL`/`CONTEXTUAL` member is created** — every one of the 32 implementable specifications has an explicit, unconditional book-stated direction (verified row-by-row in §35C); none is genuinely direction-ambiguous. (Equal Highs is bearish-context/liquidity-above; Equal Lows is bullish-context/liquidity-below — both have a fixed, single direction per the book, not a contextual one.)

**`PoiType`** (`StrEnum`, exactly 32 members, one per implementable row in §35C — `BUY_ORDER_BLOCK`, `SELL_ORDER_BLOCK`, `BUY_FAIR_VALUE_GAP`, `SELL_FAIR_VALUE_GAP`, `BUY_TO_SELL_CANDLE`, `SELL_TO_BUY_CANDLE`, `BASE_RALLY`, `BASE_DROP`, `BULLISH_PRESSURE_WICK`, `BEARISH_PRESSURE_WICK`, `BULLISH_ENGULFING`, `BEARISH_ENGULFING`, `HAMMER`, `SHOOTING_STAR`, `MORNING_STAR`, `EVENING_STAR`, `SUPPORT_ZONE`, `RESISTANCE_ZONE`, `EQUAL_HIGHS_LIQUIDITY`, `EQUAL_LOWS_LIQUIDITY`, `PREVIOUS_DAY_HIGH`, `PREVIOUS_DAY_LOW`, `PREVIOUS_WEEK_HIGH`, `PREVIOUS_WEEK_LOW`, `PREVIOUS_MONTH_HIGH`, `PREVIOUS_MONTH_LOW`, `CURRENT_DAY_HIGH`, `CURRENT_DAY_LOW`, `CURRENT_WEEK_HIGH`, `CURRENT_WEEK_LOW`, `CURRENT_MONTH_HIGH`, `CURRENT_MONTH_LOW`). **No placeholder member is created for Trendline, Swing High, or Swing Low** — deferred specifications are absent from the public enum entirely, per Part 7's explicit instruction.

**Three separated axes, never conflated into one enum (per Part 7's explicit instruction). Corrected by the focused audit: a fourth, originally-proposed axis (`PoiValidityStatus`) is removed entirely — see §35U.**

1. **`PoiFamily`/`PoiType`** — what the source detector produced (fixed at candidate time, never changes).
2. **`PoiLifecycleStatus`** (§35V) — the 10-state generic breach/reclaim/invalidation vocabulary, applicable only to **exactly 18** of the 32 implementable POIs marked lifecycle-eligible in §35C (`32 − 2 equal-level − 12 period-level = 18`; the other 14 are `NOT_APPLICABLE` permanently).
3. **Strength classification** — reused verbatim from each family's own already-approved standard (e.g., `STANDARD`/`STRONG` for Order Block/Base/Pressure Wick/Engulfing-adjacent-thresholds/Hammer-ShootingStar; `STRONG`/`STANDARD`/`NOT_EQUAL` for Equal Highs/Lows) — **not** merged into `PoiType` or `PoiLifecycleStatus`. Strength is exposed as a separate field on `PoiObservation`, typed per-family where the source standard already defines its own tier enum, or as a shared `PoiStrengthTier` (`STANDARD`, `STRONG`) `StrEnum` reused across every family whose approved standard uses exactly this two-tier shape (Order Block, Base, Pressure Wick, Buy-to-Sell/Sell-to-Buy, Hammer/Shooting Star "Strong Shape"). Equal Highs/Lows keep their own three-tier `STRONG`/`STANDARD`/`NOT_EQUAL` (reused from `domain.EqualLevelCluster`, not redefined).

**Why `PoiValidityStatus` is removed (Part 6 of the focused audit):** the original 2-member enum (`FORMING`/`CONFIRMED`) conflated a pre-confirmation *candidate* concept (`FORMING`) with an ongoing *validity* concept. Since internal candidates are never exported (§35T) and no public `PoiObservation` exists before confirmation, `FORMING` was never emitted by any detector, meaning every produced record's `validity_status` was always exactly `CONFIRMED` — a public field carrying zero information. Removing it entirely (rather than keeping a single-value enum) is the honest correction; existence of a public `PoiObservation` **is** the confirmation signal, with no separate field needed.

**Detected source type vs. normalized POI type:** identical for this milestone — every `PoiType` member corresponds to exactly one detector algorithm and one book specification; there is no separate "raw detector label" that gets normalized into a different public type.

**Timeframe strength is not part of any enum** — it is a computed, deterministic ordering key over the existing `Timeframe` enum (§35I), never a `PoiType`/`PoiFamily` value.

### 35E. Core POI Observation Contract

**Corrected by the focused audit (Parts 5, 6, 15): 2 fields removed from the originally-proposed 25-field contract — `validity_status` (Part 6, `PoiValidityStatus` removed entirely, §35D/§35U) and `source_structure_record_ids` (Part 5, `StructureAnalysis` removed from the public input, §35B/§35H — this field existed only to carry structure-source IDs that no detector ever populated). The corrected contract has exactly 23 fields.**

**One frozen public `PoiObservation(ContractModel)`**, exact field order:

```
record_id: UUIDv7
content_fingerprint: SHA256Fingerprint
symbol: InternalSymbol
source_timeframe: Timeframe
effective_timeframe: Timeframe
family: PoiFamily
poi_type: PoiType
direction: PoiDirection
zone_top: Decimal
zone_bottom: Decimal
representative_price: Decimal | None
strength_tier: PoiStrengthTier | None
source_candle_record_ids: tuple[UUIDv7, ...]
source_measurement_record_ids: tuple[UUIDv7, ...]
merged_source_poi_record_ids: tuple[UUIDv7, ...]
candidate_event_time_utc: datetime
confirmation_time_utc: datetime
availability_time_utc: datetime
rule_version: SemVer
contract_version: SemVer
schema_version: SemVer
evidence_classification: EvidenceClassification
provenance_id: UUIDv7
```

**Field-by-field resolution:**

- **`zone_top`/`zone_bottom`:** mandatory on every `PoiObservation`, including the 12 period-level and 2 equal-level types. For the 12 single-price-point period levels, `zone_top = zone_bottom = representative_price` (a degenerate, zero-height point zone, §35X's exact point-zone rules) — this is the narrow, justified exception in Part 8's "`representative_price`, if justified" clause: a period level genuinely has no second boundary, and forcing a fake non-zero zone would misrepresent the source specification. `Zone Height = 0` for these 12 only; every interaction/reaction formula that divides by Zone Height (POI Zone Interaction Standard, POI Reaction Strength Standard) is **not** applied to these 12 — they are exposed as reference levels only, consistent with §35C's classification.
- **`representative_price`:** `None` for every bounded-zone POI (rows 1-22 in §35C); set for the 12 period-level rows (25-36).
- **`source_timeframe`/`effective_timeframe`:** distinct fields — `source_timeframe` is the timeframe the detector actually ran on; `effective_timeframe` is the timeframe assigned after strong-timeframe precedence/merge resolution (§35I/§35X). For an un-merged, non-suppressed observation the two are always equal.
- **Multiple source candles:** yes (`source_candle_record_ids`, an ordered tuple) — e.g. Base Rally/Drop reference 2-6 base candles plus the departure candle; FVG references exactly 3.
- **Multiple source measurements:** yes (`source_measurement_record_ids`) — Support/Resistance/Equal-Highs/Equal-Lows reference the originating `domain.SupportResistanceZone`/`domain.EqualLevelCluster` record.
- **No source-structure-facts field:** removed (see correction note above); structural context may be added in a later milestone, and only for the specific POI types whose approved rule is found to genuinely require it (§35B).
- **Multiple merged child POIs:** yes (`merged_source_poi_record_ids`, §35X) — empty for an un-merged observation.
- **No separate validity field:** removed (see correction note above); a `PoiObservation`'s mere existence is the confirmation signal (§35T/§35U).
- **Immutability, with one disclosed exception:** every tuple field is an immutable `tuple[...]`, never a `list`; no mutable internal candidate object is ever exposed as a field value (candidates are `NamedTuple`s, finalized into `PoiObservation` exactly like every prior milestone's `_finalize` pattern, §35G). **`PoiObservation` instances are frozen Python objects for all 32 implementable types without exception** — no field is ever mutated in place on an existing object. However, for **exactly 6 types** — `CURRENT_DAY_HIGH`, `CURRENT_DAY_LOW`, `CURRENT_WEEK_HIGH`, `CURRENT_WEEK_LOW`, `CURRENT_MONTH_HIGH`, `CURRENT_MONTH_LOW` — the semantically "same" period-window observation is **recomputed as a new frozen snapshot** (same `record_id`, per its stable §35F semantic key; different `zone_top`/`zone_bottom`/`representative_price`/`source_candle_record_ids`/`availability_time_utc`/`content_fingerprint`) every time a new visible candle extends the running high/low. This is the **one disclosed exception** to "content never changes after confirmation" among the 32 implementable types — every other type's `PoiObservation` content is fixed forever once confirmed. §35R specifies this exactly; §35F confirms identity stability across recomputation.

### 35F. Candidate Identity — Exact Semantic Keys

Identity is reused structurally unmodified from `DerivedOutputIdentityProvider.identify(output_type, semantic_key) -> UUIDv7` (`domain`, 1B-H). Three new `DerivedOutputType` members are required (§35K below is a forward reference; the exact members are `POI_OBSERVATION`, `POI_LIFECYCLE_TRANSITION`, `CURRENT_POI_STATE`), appended to `domain/enums.py` exactly as `1B-I-STRUCTURE` appended its own 3 members — **the only modified existing source path in this milestone.**

**Identity depends on immutable source semantics only — never on lifecycle status, later touches, current validity, mutable strength, call count, or detection order.** Exact semantic keys per family:

- **Fair Value Gap** (`BUY_FAIR_VALUE_GAP`/`SELL_FAIR_VALUE_GAP`): `(symbol.value, timeframe.value, poi_type.value, str(candle_1_record_id), str(candle_2_record_id), str(candle_3_record_id), rule_version)`.
- **Order Block** (`BUY_ORDER_BLOCK`/`SELL_ORDER_BLOCK`): `(symbol.value, timeframe.value, poi_type.value, str(origin_candle_record_id), str(displacement_candle_record_id), rule_version)`.
- **Buy-to-Sell/Sell-to-Buy Candle:** `(symbol.value, timeframe.value, poi_type.value, str(candidate_candle_record_id), rule_version)`.
- **Base Rally/Base Drop:** `(symbol.value, timeframe.value, poi_type.value, str(departure_candle_record_id), tuple(str(id) for id in sorted_base_candle_record_ids), rule_version)`.
- **Pressure Wick:** `(symbol.value, timeframe.value, poi_type.value, str(candle_record_id), rule_version)`.
- **Engulfing:** `(symbol.value, timeframe.value, poi_type.value, str(engulfed_candle_record_id), str(engulfing_candle_record_id), rule_version)`.
- **Hammer/Shooting Star:** `(symbol.value, timeframe.value, poi_type.value, str(candle_record_id), rule_version)`.
- **Morning/Evening Star:** `(symbol.value, timeframe.value, poi_type.value, str(candle_1_record_id), str(doji_candle_record_id), str(candle_3_record_id), rule_version)`.
- **Support/Resistance reference:** `(symbol.value, timeframe.value, poi_type.value, str(origin_support_resistance_zone_record_id), rule_version)` — a pure reference key onto the already-identity-bearing `domain.SupportResistanceZone.record_id`; never re-derives its own boundary identity.
- **Equal Highs/Equal Lows reference:** `(symbol.value, timeframe.value, poi_type.value, str(origin_equal_level_cluster_record_id), rule_version)` — same reference-only pattern onto `domain.EqualLevelCluster.record_id`.
- **Period Level (12 variants):** `(symbol.value, timeframe.value, poi_type.value, period_start_time_utc.isoformat(), rule_version)` — `period_start_time_utc` is the deterministic calendar-window start (§35Q/§35AN item on the calendar-boundary gap-fill), making one period level per calendar window per symbol/timeframe a stable, non-duplicating identity; a "current" period level's identity does **not** change as new candles extend the window (only its `content_fingerprint` changes, §35G) — it becomes the "previous" period level's identity only at rollover, which creates a **new** record with a **new** `period_start_time_utc`, never a mutation of the prior one.

**`PoiLifecycleTransition` semantic key:** `(symbol.value, timeframe.value, poi_type.value, str(origin_poi_record_id), transition_type.value, str(triggering_candle_record_id), rule_version)` — mirroring `1B-I-STRUCTURE`'s `STRUCTURE_TRANSITION` pattern (one record per distinct triggering event, never mutated retroactively).

**`CurrentPoiState` semantic key:** `(symbol.value, timeframe.value, poi_type.value, str(origin_poi_record_id), rule_version)` — one stable singleton identity per confirmed POI instance (mirroring `CURRENT_STRUCTURE_STATE`'s singleton-per-scope pattern), whose *content* (lifecycle status, freshness, tap count, age fields) changes over time while `record_id` stays fixed.

**No random IDs anywhere.** `DerivedOutputIdentityProvider` is reused structurally unmodified; no new Protocol is introduced.

### 35G. Content Fingerprint Strategy

**Chosen approach: C — duplicate again, with a required exact cross-package equivalence test, matching the precedent already twice-approved and twice-implemented (`1B-H-MEASUREMENTS`'s original `_canonicalize`/`_compute_content_fingerprint`, and `1B-I-STRUCTURE`'s independent, tested-byte-identical duplicate of the same algorithm).** Options A (extract one shared internal utility, retrofitting `domain/analyzer.py` and `structure/analyzer.py` within this milestone's approved path scope) and B (import `structure`'s or `domain`'s private helper directly) were both rejected for the same reason already recorded and accepted twice in this project: `domain/analyzer.py`'s `_canonicalize`/`_compute_content_fingerprint` and `_IdentityResolver`/`_finalize` machinery are private, non-exported implementation details of an already-closed, already-production-adjacent-tested milestone; reopening or importing them privately would either violate `1B-H`/`1B-I`'s own closure (Option A) or create an undisclosed cross-package private dependency with no compile-time contract (Option B). Option C's cost — a third, disclosed, tested-equivalent copy — is small (a handful of private functions, ~60 lines) and the disclosed maintenance risk is identical in kind to `1B-I-STRUCTURE`'s own accepted precedent.

**Path implication:** `poi/analyzer.py` locally re-implements `_canonicalize`/`_compute_content_fingerprint`/`_IdentityResolver`/`_finalize`, byte-identical in algorithm to `domain/analyzer.py`'s and `structure/analyzer.py`'s. A new required test, `test_poi_fingerprint_serializer_matches_domain_and_structure_serializers`, directly exercises all three modules' private `_canonicalize`/`_compute_content_fingerprint` functions against one shared sample-fields dictionary and asserts byte-for-byte equality across all three (extending `1B-I-STRUCTURE`'s two-way equivalence test to a three-way check).

**Fingerprint scope:** every public field on `PoiObservation`/`PoiLifecycleTransition`/`CurrentPoiState` except `record_id` and `content_fingerprint` itself — identical rule to every prior milestone. A lifecycle transition (e.g., `FRESH` -> `INTERACTED`, or a new `poi_lifecycle_status`) changes `CurrentPoiState.content_fingerprint` while `CurrentPoiState.record_id` remains fixed (§35F), mirroring `CurrentStructureState`'s already-proven pattern.

### 35H. Input Model and Validation

**Chosen form: B — immutable tuples of per-timeframe input bundles.** Rejected: (A) a `Mapping[Timeframe, ...]` — a plain dict input would be harder to validate deterministically for duplicate/missing timeframes and does not match this project's consistent `tuple[ContractModel, ...]`-only input convention; (C) one timeframe per call with separate cross-timeframe aggregation — this would push the entire cross-timeframe overlap/precedence problem (§35I/§35X) onto every caller, duplicating logic the analyzer itself must own to be deterministic; (D) rejected as unnecessary — B is already minimal and immutable.

**Corrected by the focused audit (Part 5 — Option B adopted): `structure_analysis` is removed from `PoiTimeframeInput` entirely.** No detector for any of the 32 implementable types used it for any gating purpose; its sole described effect was a consistency check, making it a required input with no deterministic effect. Structural context may be added in a later milestone, and only for specific POI types whose approved rule is found to genuinely require it — never as a standing, always-required field.

**Exact input contract**, a new `PoiTimeframeInput(NamedTuple)` (a caller-assembled input bundle, not a produced output, matching the existing distinction between `NamedTuple` candidates/inputs and `ContractModel` outputs used throughout `domain`/`structure`):

```
symbol: InternalSymbol
timeframe: Timeframe
candles: tuple[NormalizedCandle, ...]
market_measurements: MarketMeasurementAnalysis
```

**Public API signature:** `analyze_pois(timeframe_inputs: tuple[PoiTimeframeInput, ...], configuration: PoiConfiguration, identity_provider: DerivedOutputIdentityProvider) -> PoiAnalysis` (§35AA).

**Exact validation, in order, each with its own typed error (§35AB):**

1. **Mixed symbol** across `timeframe_inputs` — `MixedSymbolAnalysisError` reused unmodified from `domain`.
2. **Duplicate timeframe bundle** — two entries with the same `timeframe` — new `DuplicatePoiTimeframeInputError`.
3. **Unsupported timeframe** — a `timeframe_inputs` entry whose `timeframe` is not one of the 8 existing `Timeframe` members is structurally impossible (Pydantic/enum-typed field), so no runtime check is needed beyond type validity; no new error is required for this case.
4. **Unsorted timeframe bundles** — `timeframe_inputs` must be supplied in a fixed canonical order (ascending `Timeframe` strength per §35I's total order) — new `UnsortedPoiTimeframeInputError` on violation; the analyzer never silently reorders.
5. **Missing candle prefix / measurement-candle mismatch** — for each `PoiTimeframeInput`, `market_measurements.analyzed_candle_count` must equal `len(candles)`, and `market_measurements.symbol` (when non-`None`) must equal the bundle's `symbol` — new `InputPrefixMismatchError` on any violation. This is a structural consistency check only; it does **not** re-run `analyze_market_measurements()` — the caller remains responsible for having produced consistent inputs, exactly as `structure`'s own `analyze_structure_state()` never re-derives `confirmed_swings` from `candles` itself. (Structure-candle/structure-measurement mismatch checks are removed along with the `structure_analysis` field.)
6. **Missing source record** — a detector-internal reference to a candle/measurement record ID not present in the supplied bundle — new `MissingSourceRecordError`.
7. **Duplicate source IDs** — duplicate `record_id` within one bundle's `candles` — reuses `DuplicateCandleRecordError` unmodified from `domain`.
8. **Tied availability groups** — reuses the existing no-look-ahead availability-group event-ordering discipline (§35AD); not a separate validation error, a processing-order guarantee.
9. **Future measurement output** — structurally prevented by check 5 (the measurement aggregate's own `analyzed_candle_count` cannot exceed the supplied candle count) plus the existing `availability_time_utc` no-look-ahead discipline inherited from that source aggregate.

**No hidden repository reads:** `analyze_pois()` never calls `market_data`, never reads a repository, never performs I/O — pure function over its three supplied arguments, identical discipline to `analyze_market_measurements()`/`analyze_structure_state()`.

### 35I. Timeframe Policy and Strong-Timeframe Precedence

**Authoritative source, read directly (per Part 12's explicit instruction), not summarized:** `docs/PROJECT_SCOPE.md` §3's timeframe-role table —

| Role | Timeframes | Purpose |
|---|---|---|
| Strong POI analysis | H3, H4, D1, W1 | Highest-quality Order Blocks, FVGs, liquidity/pressure wicks, Morning/Evening Stars, trendlines, previous/current high-low levels |
| Market-structure breakdown | H1, M15 | Swing highs/lows, structure/trend framework |
| BTMM formation and execution | M15, M5, M1 | BTMM formation/execution (out of scope for this milestone) |

**H3/H6/H8/H12:** grepped project-wide with zero occurrences (confirmed by the Final Phase 0G audit); the existing `Timeframe` enum already has exactly 8 members (`M1`, `M5`, `M15`, `H1`, `H3`, `H4`, `D1`, `W1`) — **no new `Timeframe` member is required**; H6/H8/H12 do not exist anywhere in this project and are not introduced here.

**Approved strong POI timeframes (this milestone): H3, H4, D1, W1.** **Approved weak/formation timeframes: M1, M5, M15, H1** (H1/M15 additionally used for market-structure breakdown, per the table). **P0G-B014 (documented, unresolved, disposition B — a documentation-consistency gap, not a trading-rule conflict):** several individual POI files (Order Block, Engulfing, Base Rally/Drop) state their own strength ranking as "Weekly > Daily > 4H > 1H > 15-minute," which includes H1 and M15 — timeframes the official table does not list under "Strong POI analysis." **This architecture does not silently pick a side of P0G-B014.** It defines the precedence *algorithm* (below) over the full `Timeframe` domain (all 8 members participate in the total order, so an H1/M15 Order Block is still comparable, just weighted lower than H3/H4/D1/W1) and flags the exact numeric strength-weight assignment for H1/M15 relative to H3 as an explicit author decision (§35AN) rather than resolving P0G-B014's prose inconsistency by fiat.

**Total timeframe-strength order (deterministic, `PoiConfiguration`-defined, §35AG):** `_TIMEFRAME_STRENGTH_RANK: dict[Timeframe, int]` — a fixed mapping, `W1=8, D1=7, H4=6, H3=5, H1=4, M15=3, M5=2, M1=1` (strictly by calendar duration, matching the book's own explicit "higher timeframe = stronger" principle uniformly, and consistent with both the official table's H3/H4/D1/W1 "strong" grouping and the individual-file H1/M15 inclusion — since M1 < M5 < M15 < H1 < H3 < H4 < D1 < W1 is the only order consistent with calendar duration and is not itself part of the disputed P0G-B014 prose). **Never uses human-readable timeframe strings for ordering** — always this explicit integer rank mapping.

**Corrected by the focused audit (Part 12): P0G-B014/duration-rank separation stated explicitly, and the unused `strong_poi_timeframes` configuration field is removed (§35AG).** The audit found `strong_poi_timeframes = {H3,H4,D1,W1}` was declared in `PoiConfiguration` but never consulted by any described algorithm — §35I's merge-precedence rule and §35X's merge test both use only `_TIMEFRAME_STRENGTH_RANK`, never a "strong" set-membership check. This field is removed entirely; no replacement unused field is introduced. To be explicit about what remains and what P0G-B014 still leaves open:

- `_TIMEFRAME_STRENGTH_RANK` **is not a resolution of `P0G-B014`.** It is a pure calendar-duration ordering, undisputed by any source, used **solely** to select a deterministic parent among observations that are *already* merge-eligible (same `poi_type`, same `symbol`/direction, overlapping zones, §35X) — it never determines merge eligibility itself.
- This ranking **never labels H1 or M15 as a "strong POI timeframe."** That disputed classification (whether the individual POI files' own "Weekly > Daily > 4H > 1H > 15-minute" language should count H1/M15 among "strong" timeframes, contradicting `PROJECT_SCOPE.md`'s official table) remains `P0G-B014`, explicitly unresolved, and is not touched by this milestone's merge algorithm.
- **No POI is suppressed, hidden, or invalidated by timeframe rank alone** — rank affects only which observation becomes the parent when a merge already independently qualifies; a lower-ranked, non-overlapping observation on a "weak" timeframe is never discarded, deprioritized, or treated as lifecycle-relevant differently because of its timeframe.
- Period-level types (rows 25-36, §35C) may participate in this precedence mechanism only when: `PoiType` matches exactly (e.g., two `CURRENT_DAY_HIGH` observations from different source timeframes — though period levels are typically symbol-scoped rather than timeframe-scoped in practice, the mechanism is defined generally); source timeframes differ; and the exact point-zone overlap rule (§35X) passes for their zero-height zones.

**Precedence algorithm (Part 26):** when two `PoiObservation`s of the **same `poi_type`, same `symbol`, and overlapping zones** (§35X) exist on different timeframes, the stronger-timeframe observation **merges the weaker one as a child** (§35X) rather than replacing, suppressing, or leaving both fully independently observable — `effective_timeframe` on the resulting merged observation is set to the stronger timeframe, and the weaker-timeframe original remains separately queryable via `merged_source_poi_record_ids` (never deleted, never silently hidden). Same-family, cross-`poi_type` overlap (e.g., an FVG overlapping an Order Block) is handled by the separate, non-precedence overlap-only path (§35X) — precedence ranking applies only to same-`poi_type` timeframe conflicts. **Equal-strength ties** (impossible under the current 1-8 strict integer rank, since every `Timeframe` member maps to a distinct integer) are structurally excluded; no tie-break rule is needed.

### 35J. Fair Value Gap Architecture

**Strict three-candle rule (reused verbatim, no invention):** Buy FVG requires `low(candle 3) > high(candle 1)`, zone = `[high(candle 1), low(candle 3)]`; Sell FVG requires `high(candle 3) < low(candle 1)`, zone = `[high(candle 3), low(candle 1)]`. Wick-inclusive on both edges (no wick/body distinction for FVG geometry itself). **No minimum-size threshold** — RECON-D3 explicitly resolved this as "no override; a geometrically valid FVG can be as narrow as one price tick," reusing the generic Contact/Overshoot Tolerance formulas unmodified. **Displacement requirement:** the middle (2nd) candle must satisfy the reused Small-Candle-Standard comparison against the largest of the 3 preceding confirmed candles (`Pre-Displacement Maximum Range`); `Displacement Expansion Ratio = displacement Total Range / Pre-Displacement Maximum Range`; optional `STANDARD FAST`/`STRONG FAST` speed tiers layer on top of, never replace, the mandatory strict gap geometry. **No structure-context requirement** is stated beyond "formed within a directional (non-choppy) price movement" — no BOS/CHoCH/StructureTransition gate is invented, and no structure input exists in this milestone to invent one from (§35S). **Availability = `fvg_available_time = third_candle_close_time`** (RECON-D5); a candidate is rejected outright (no `PoiObservation` created at all) if the strict gap geometry no longer holds at that close. **Immediate/partial/complete mitigation:** not separate FVG-specific concepts — measured via the shared POI Zone Interaction Standard's penetration ratios (§35T) plus the shared breach/reclaim lifecycle (§35V); no FVG-specific mitigation formula is invented. **Overlap with Order Block:** handled generically by §35X, no FVG-specific override. **Multi-timeframe precedence:** §35I, no FVG-specific override. **Identity/fingerprint:** §35F/§35G.

### 35K. Order Block Architecture

**Two-candle structure, reused verbatim:** smaller (origin) candle followed by a displacement candle with `Size Ratio (Total Range) >= 2.0` (standard) `/ >= 3.0` (strong) versus the origin candle, using the project's Candle Measurement Standard V1 (`Total Range = High - Low`, no ATR normalization, no body-only measurement). **Zone = full high-to-low range of the origin (smaller, first) candle**, wick-inclusive. **No "origin vs. middle of an existing move" automated gate is implemented** — this location distinction is stated qualitatively only in the book (a warning: "must be located at the beginning/origin... not randomly in the middle") with **no numeric or structural rule anywhere in the approved knowledge base to detect it automatically** (verified: neither the Order Block file nor the Volume/Momentum Proxy Standard defines one). Inventing a BOS/CHoCH-based "is this the origin" gate here would be an unapproved rule addition, not a reuse of an approved standard — this is an explicit, disclosed limitation (§35AN), not a silent omission; no structure input exists in this milestone to attach as evidence either (§35S). **Required displacement, structure context:** none beyond the size-ratio rule; **no BOS is required** (verified verbatim across both Order Block files: "does not require BOS (undefined in this project and not invoked here)"). **Base-formation interaction:** none — Order Block and Base Rally/Drop remain independently detected patterns; a candle sequence satisfying both is exposed as two separate `PoiObservation`s (deduplication is not invented; §35X's overlap/merge algorithm may later relate them geometrically, but detection itself never suppresses one because the other also matched). **Availability = `order_block_available_time = qualifying_displacement_candle_close_time`** (RECON-D1) — not backdated to the origin candle's close, does not require a first return to the zone, does not require entry confirmation. **First return, mitigation, breach, reclaim, invalidation:** the shared generic lifecycle (§35V), gated from `order_block_available_time` onward. **Overlap with FVG/Support-Resistance:** §35X, no Order-Block-specific override. **Identity/fingerprint:** §35F/§35G.

### 35L. Candlestick-Pattern POIs

**Bullish/Bearish Engulfing (GROUP3-D1/D2, author-approved final):** two-candle pattern; engulfing candle `Size Ratio >= 2.0` (standard) `/ >= 3.0` (strong) versus the engulfed candle (Small-Candle-Standard comparison); engulfing candle must close in its own direction. **Zone = complete high-to-low range of the first, smaller, opposite-direction (engulfed) candle** — the engulfing (second, larger) candle is confirmation/displacement evidence only, never part of the boundary. **Availability = engulfing candle's own close** (`engulfing_poi_available_time = qualifying_engulfing_candle_close_time`); rejected outright (no `PoiObservation`) if the second candle fails any mandatory condition. **"Middle of an existing move" is likewise not an automated gate** — same disclosed limitation as Order Block's "origin," for the same reason (qualitative-only in the book, no numeric rule exists); no structure input exists in this milestone to attach as context (§35S).

**Hammer/Shooting Star (GROUP3-D3/D4/D5/D6, author-approved final):** single-candle. Standard Hammer: `Lower Wick Share >= 0.60`, `Body Efficiency <= 0.30`, `Upper Wick Share <= 0.10`; Strong Shape: `Rejection Wick Share >= 0.70`, `Body Efficiency <= 0.20`, `Opposite Wick Share <= 0.05` (Shooting Star mirrors on the upper wick). **POI role (GROUP3-D4): bounded directional POI** (not signal-only) — pattern validity, signal validity, POI lifecycle validity, and entry validity remain four separate concepts; may coexist with a Pressure Wick label on the same candle without precedence. **Zone (GROUP3-D5): rejection wick only** — Hammer `zone_top = MIN(Open,Close)`, `zone_bottom = Candle Low`; Shooting Star `zone_top = Candle High`, `zone_bottom = MAX(Open,Close)`; the candle body is pattern evidence, never zone content. **Availability (GROUP3-D6) = the candle's own close** — the book's "wait for a confirmation candle before entering" language is entry-timing observation only and does **not** gate POI lifecycle availability. **No context/trend requirement is defined** beyond "around a support/resistance zone" (qualitative, not gating).

**Morning/Evening Star (GROUP3-D7/D8/D9, author-approved final):** three-candle. Middle-candle threshold: `middle_candle_body_efficiency = |Middle Close - Middle Open| / (Middle High - Middle Low)`, invalid when the denominator `<= 0`; Standard Doji `<= 0.10`, Strong Doji `<= 0.05`. Final (third) candle `Size Ratio` vs. the middle doji "ideally >= 2.0-3.0" (not a hard mandatory gate beyond the doji threshold itself — the book's "ideally" is retained as descriptive strength evidence, not a pass/fail rule). **Zone (GROUP3-D8) = complete high-to-low range of the qualifying middle Doji only** — candles 1 and 3 excluded from the boundary; candle 3 is pattern-confirmation evidence only. **Availability (GROUP3-D9) = third candle's own close.** Recommended timeframe (book, descriptive only, no gate): 2H/3H/4H and above.

### 35M. Reversal-Candle and Base-Formation POIs

**Buy-to-Sell / Sell-to-Buy Candle:** single candidate candle; `STANDARD` requires `Candidate Size Ratio >= 2.00`, `Body Efficiency >= 0.60`, directional Close Position `>= 0.70` (vs. the largest of the 3 immediately preceding confirmed candles); `STRONG` requires `>= 3.00` / `>= 0.70` / `>= 0.80` plus a qualifying opposite-direction reversal within the post-candidate window. **Zone = candidate candle's full high-to-low range**, fixed permanently after reversal confirmation — never refined/shrunk/recentered by later price action. **Confirmation:** exactly the next 3 confirmed candles are evaluated for a qualifying opposite-direction close beyond `Candidate Midpoint` (`STANDARD`) or beyond the candidate's own extreme (`STRONG`), with `Continuation Close Tolerance = MAX(2 x Minimum Price Tick, 0.10 x Candidate Reference ATR)` gating a `REJECTED_DIRECTIONAL_CONTINUATION` outcome; the window is never extended beyond 3 candles — a candidate that fails to reverse within 3 candles produces no `PoiObservation` at all (`REJECTED_INSUFFICIENT_REVERSAL`). **Availability = `reversal_confirmation_time`** — never backdated to the candidate candle's original time. **Required preceding trend context** ("existing uptrend"/"existing downtrend") is stated explicitly stronger than most other families but its full quantitative definition is explicitly unresolved in the book/standards; **not automated in this milestone** — same disclosed limitation as §35K/§35L, flagged in §35AN, not silently invented via HH/HL/BOS/CHoCH (explicitly prohibited by the source files themselves: "not defined using HH, HL, BOS, CHoCH, a moving average, or any other invented structure rule").

**Base Rally / Base Drop:** 2-6 consecutive confirmed candles; every base candle's Total Range `<= 0.50x` (standard) `/ <= 0.3333x` (strong) the departure candle's Total Range; `Base Height <= 0.75x ATR(14)` **and** `<= 0.60x` departure candle's Total Range; `Base Midpoint Drift <= 0.25x Base Height`; per-consecutive-pair `Overlap Ratio >= 0.50`; departure candle `Size Ratio >= 2.0`/`3.0` versus the largest base candle, closing beyond the full base range in the expected direction. **Zone = `[Base Low, Base High]`** across all 2-6 base candles. **Availability = `base_available_time = qualifying_departure_candle_close_time`** (RECON-D2) — not the first base candle, not the last base candle, not a future first return. Strength tiers: `COMPACT_BASE` / `STRONG_BASE` / `INVALID_BASE` (any mandatory condition failing produces no `PoiObservation`).

**Bullish/Bearish Pressure Wick:** single candle; Bullish requires `Lower Wick Share >= 0.40`, `Body Efficiency >= 0.25`, `Lower Wick >= 2x Upper Wick`, `Bullish Close Position >= 0.60` (Bearish mirrors on the upper wick); `STRONG` requires `>= 0.50`/`>= 0.30`/`>= 3x`/`>= 0.70`/`Range Context Ratio >= 1.25`. **Zone = rejection wick only** — Bullish `[Candle Low, MIN(Open,Close)]`, Bearish `[MAX(Open,Close), Candle High]`; candle colour never determines direction. **Availability = the candle's own close** (`CANDIDATE` before close, `CONFIRMED` after); no separate `_available_time` variable beyond the candle's own confirmation. **Timeframe:** H3/H4/D1/W1 receive contextual priority only (not a numerical score, per the already-approved resolution) — a candle failing the mandatory formation conditions stays invalid regardless of timeframe.

**Volume/momentum evidence, uniformly across every family in this section — corrected placement (Part 10 of the focused audit):** every detector **computes internally** the reused Volume/Momentum Proxy Standard fields (`relative_size_ratio`, `range_context_ratio`, `body_efficiency`, `directional_close_position`) to evaluate each family's own mandatory candidate/confirmation thresholds (the exact ratios quoted above) — these four fields are **never stored on `PoiObservation`, never exported, never part of any semantic identity key, and never part of any public content fingerprint** (§35Q resolves the placement ambiguity the audit found: earlier drafts said these fields were "computed and stored" with placement deferred to §35Q, but §35Q never specified one — this is now corrected to state explicitly that they are internal-only). No minimum threshold beyond the ones already quoted above is invented; tick volume, where `NormalizedCandle.volume`/`volume_kind` is non-`UNKNOWN`, is likewise computed internally as `relative_tick_volume`/`tick_volume_status` and is never gating, never stored, never exported.

### 35N. Support/Resistance Reference POIs

**No re-detection of Support/Resistance.** `poi/reference_zones.py` consumes `domain.SupportResistanceZone` (produced by the already-implemented, already-closed `analyze_market_measurements()`) directly and unmodified — `zone_top`, `zone_bottom`, `zone_type`, `confirmation_time_utc`, `availability_time_utc`, `evidence_classification` are all inherited byte-for-byte from the source `SupportResistanceZone` record; no new boundary computation, no new confirmation rule, no new availability rule is invented. **`SupportResistanceType.SUPPORT` maps to `PoiDirection.BULLISH`; `SupportResistanceType.RESISTANCE` maps to `PoiDirection.BEARISH`** — a fixed, unconditional mapping (no neutral/contextual case, matching §35D's direction-enum decision). **Every confirmed `SupportResistanceZone` becomes exactly one `PoiObservation`** — no additional structural-context gate is layered on top (the source zone's own `origin_swing_record_id`/reaction-strength gating, already enforced by `1B-H-MEASUREMENTS`, is sufficient; adding a second, POI-level gate would silently duplicate or contradict an already-closed milestone's own approved rule). **POI-specific confirmation = inherited, not re-derived.** **Identity relation to source zone:** the `PoiObservation`'s own identity is a pure reference key onto `origin_support_resistance_zone_record_id` (§35F) — a later touch of the source zone changes the source zone's own `content_fingerprint` (per `1B-H`'s existing rules) and, downstream, this `PoiObservation`'s content fingerprint changes to match, while both record IDs stay fixed. **Breach/reclaim/invalidation:** inherited generic lifecycle (§35V), RECON-D4's coexistence rule preserved exactly — `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` (the family-specific, `Horizontal Pierce Tolerance`-based deeper breach observation, already defined on the source `SupportResistanceZone` concept) remains a separate, non-aliased, parallel signal alongside the generic `CLOSE_BREACH_CANDIDATE` (`Overshoot Tolerance`-based); **only `CLOSE_BREACH_CANDIDATE` drives the shared Reclaim/Displacement/Invalidation state machine** (§35V) — this milestone does not re-derive or duplicate `SUPPORT_BREAK_CANDIDATE`/`RESISTANCE_BREAK_CANDIDATE` itself (those remain `domain`-level facts on `SupportResistanceZone`); `poi/reference_zones.py` only consumes the source zone's already-existing fields plus applies the shared `CLOSE_BREACH_CANDIDATE`-onward lifecycle on top. **Overlap with OB/FVG:** §35X, no Support/Resistance-specific override. **Strong-timeframe precedence:** §35I, no override.

### 35O. Trendline Reference POIs — Deferred

**No Trendline `PoiType` is created; no Trendline-derived `PoiObservation` is ever produced by this milestone.** Per §35C's deferral rationale: the approved Trendline standard defines a line (`Line Price(t) = Anchor 1 Price + Raw Slope x (t - Anchor 1 Bar Index)`) plus Touch/Pierce Tolerance *bands* around that moving line, never a static, finite `[zone_top, zone_bottom]` pair suitable for this milestone's `PoiObservation` contract. Constructing one (e.g., "zone = tolerance band around today's line price") would be a new, unapproved geometry rule, not a reuse of `bullish_trendline.md`/`bearish_trendline.md`'s own approved content, and would also contradict the author-approved `P0G-B005` Option B deferral (which explicitly excludes Trendlines from the shared bounded-POI lifecycle). **This milestone does not resolve `P0G-B005`.** A future, separate, narrowly-scoped architecture task — mirroring how Ambiguity 15 was resolved for bounded zones — remains the correct place to define Trendline-touch-as-POI zone geometry and a specialized Trendline lifecycle, if the author ever approves Option A there. Until then, `domain.Trendline` (1B-H) remains directly queryable by any caller wanting trendline information; no wrapper is created here.

### 35P. Equal-Level Liquidity References

**No re-detection.** `poi/reference_zones.py` consumes `domain.EqualLevelCluster` directly and unmodified — `zone_top`, `zone_bottom`, `cluster_type`, strength tier, `availability_time_utc` are inherited byte-for-byte. **`EqualLevelType.EQUAL_HIGH` maps to `PoiDirection.BEARISH` (buy-side liquidity rests above, a bearish liquidity-grab trigger); `EqualLevelType.EQUAL_LOW` maps to `PoiDirection.BULLISH`** (mirroring the book's own explicit framing). **The cluster itself becomes the `PoiObservation`** — not only a sweep/rejection event (no sweep-detection logic is invented; that is exactly the still-open `P0G-B004` specialized lifecycle this milestone does not resolve). **Lifecycle: detection-only, by design, per `P0G-B004` Option B** (already author-approved) — `PoiLifecycleStatus` for `EQUAL_HIGHS_LIQUIDITY`/`EQUAL_LOWS_LIQUIDITY` observations is fixed at a single value, `NOT_APPLICABLE`, for the observation's entire lifetime; **no `CLOSE_BREACH_CANDIDATE`, `RECLAIM_CONFIRMED`, or `GENUINE_INVALIDATION_CONFIRMED` event is ever emitted for these two types** — the shared bounded-POI lifecycle standard is explicitly prohibited from silent application here, exactly as `equal_highs.md`/`equal_lows.md` themselves state. **This milestone does not implement the BTMM manipulation lifecycle** (sweep-then-reverse-vs-break-and-continue interpretation) anywhere for Equal Highs/Lows or otherwise. **Availability/identity:** §35F/§35G, reference-key pattern identical to §35N.

### 35Q. Volume-Based POI Data Availability Finding

**No volume-data specification is blocking. Corrected by the focused audit (Part 10): Option B is explicitly selected for all 10 VOLUME-family `PoiType` values.** Per Part 5 of the original audit's own option set (A = genuine volume-derived POI; B = rename/reclassify as a price-action/displacement proxy; C = defer; D = block), **Option B is the correct, explicit choice** — `PoiFamily.VOLUME` is preserved as the book's own official taxonomy label (Chapter 1's "Volume-Based POI" category), but detection for all 10 types uses approved price-action, displacement, size-ratio, range-context, body-efficiency, and directional-close-position proxies, never a claim of measured real/traded volume.

`NormalizedCandle.volume: Decimal | None` and `volume_kind: CandleVolumeKind` (`TICK`/`TRADE`/`UNKNOWN`) already exist in the implemented candle contract (1B-B), with `volume` mandatory only when `volume_kind` is `TICK`/`TRADE` and freely `None` under `UNKNOWN` — this already matches the approved Volume/Momentum Proxy Standard's own governing rule exactly: **tick volume is secondary-only evidence, never a mandatory POI-validity requirement, and missing tick volume must never invalidate a POI.** Every one of the 10 volume-based POI specifications is fully detectable using **price-action proxies alone** — real/tick volume is never required, and `UNKNOWN` volume remains fully acceptable whenever the approved price-action proxy rule is otherwise complete.

**Per-specification finding (all 10, Option B):** required field = `NormalizedCandle.volume`/`volume_kind`, read-only, optional, never gating; tick vs. real volume = FXCM tick volume when `volume_kind = TICK` (the project's single approved data source, per `PROJECT_SCOPE.md`), never blended with any other provider's volume; normalization = `relative_tick_volume` (median of the previous 20 confirmed candles, current excluded), reported as `SUPPORTS`/`NEUTRAL`/`CONTRADICTS`/`MISSING`; threshold = none set (matches the approved standard's own explicit "no minimum thresholds... have been set yet"); timeframe = per-family, §35J-§35M; availability = per-family; evidence = `ENGINEERING_PROVISIONAL`; implementation readiness = **not reduced** by volume-data limitations — **this finding does not reduce the 32-POI implementable count.** No candle-range substitute is invented in place of true volume; the price-action proxies already are the approved primary standard, not a substitute for a missing one.

**Corrected field-placement note (resolving the dangling cross-reference the audit found):** the four price-action proxy fields (`relative_size_ratio`, `range_context_ratio`, `body_efficiency`, `directional_close_position`) and the two tick-volume fields (`relative_tick_volume`, `tick_volume_status`) are **computed internally by each detector, used only to evaluate that family's own mandatory candidate/confirmation thresholds, and are never stored on `PoiObservation`, never exported, never part of any semantic identity key, and never part of any public content fingerprint** (§35E's exact 23-field list contains none of them; §35M's cross-reference to this section is now resolved rather than dangling).

### 35R. Period-Level POIs — the 12 Previous/Current Calendar-Window High/Low Levels

**Mechanically well-defined, genuinely new (no existing implemented output computes these today).** Each of the 12 is the running (Current variants) or final (Previous variants) high or low of a fixed calendar window (day/week/month) over confirmed candles for one symbol/timeframe. **Zone: single price point** (`representative_price`, `zone_top = zone_bottom = representative_price`, a zero-height point zone — exact overlap/containment rules in §35X). **No lifecycle** — the `rejection_criterion_status = NOT_APPLICABLE` rule (already author-approved, `P0G-B013A`) applies verbatim: "every valid completed or active period necessarily has a high and a low — there is no candidate to reject," so `PoiLifecycleStatus` is fixed at `NOT_APPLICABLE` permanently for all 12, identical in kind to Equal Highs/Lows' fixed lifecycle value (§35P) but for a structurally different reason (a deterministic reference level, not an excluded liquidity concept). A public `PoiObservation` exists for a period level as soon as its window contains at least one candle (§35T/§35U — existence is the confirmation signal; there is no separate validity axis). **Sweep-vs-break prediction is explicitly not automated** (the book leaves this contextual; no formula exists to invent) — this milestone exposes the level only, never a predicted sweep/break outcome.

**Corrected by the focused audit (Parts 7, 8): the calendar-window boundary gap is resolved with one exact, `ENGINEERING-PROVISIONAL`, `AUTHOR-DECISION-REQUIRED` UTC policy — no longer an unresolved gap-fill.**

**Exact period-window policy (UTC only; no broker-local timezone; no DST adjustment; no hidden session calendar):**

| Period | Window (half-open) |
|---|---|
| Day | `[00:00:00 UTC, next day 00:00:00 UTC)` |
| Week | ISO week: `[Monday 00:00:00 UTC, next Monday 00:00:00 UTC)` |
| Month | Calendar month: `[1st of month 00:00:00 UTC, 1st of next month 00:00:00 UTC)` |

**Exact rules:**
- `event_time_utc` (not `availability_time_utc`, not processing time) determines which window a candle belongs to.
- Weekends and holidays are not special-cased — they simply contain no candles; a period with zero candles emits no level at all (no empty-window `PoiObservation`).
- **"Current period"** means the non-empty window containing the latest visible candle.
- **"Previous period"** means the most recent **earlier, non-empty, completed** window — previous-period resolution skips empty weekend/holiday windows automatically, since it is defined over non-empty windows only, not over every calendar window mechanically.
- A previous-period level becomes available (its `PoiObservation` is confirmed and emitted) only once a later, non-empty period begins — i.e., once the previous window is known to be closed because visible data exists in a subsequent window.
- A current-period level's `zone_top`/`zone_bottom`/`representative_price` update whenever a new visible candle extends the running high/low within that still-open window (§35E's disclosed content-evolving-snapshot exception, exactly 6 of the 12 types: `CURRENT_DAY_HIGH/LOW`, `CURRENT_WEEK_HIGH/LOW`, `CURRENT_MONTH_HIGH/LOW`).
- No incomplete/future candle is ever used — only confirmed, already-visible candles.
- All windows are computed identically under batch and replay (§35AE) — purely a function of `event_time_utc`, never of when the analysis happens to run.
- **Previous-period types (`PREVIOUS_DAY/WEEK/MONTH_HIGH/LOW`) are fixed historical observations once their period closes** — unlike the 6 "Current" types, once a period is confirmed as "previous" (a later non-empty period has begun), its content never changes again.

**Exact semantic identity (§35F, corrected):** `(symbol.value, timeframe.value, poi_type.value, period_start_time_utc.isoformat(), period_end_time_utc.isoformat(), rule_version)` — including both the exact period start **and** end boundary in the key, not only the start, removing any ambiguity about which exact window an identity refers to. For the 6 "Current" types, this identity remains stable throughout the entire open window (the period has not closed, so `period_end_time_utc` is the window's fixed, predetermined boundary, not a moving value) while `content_fingerprint` changes as new extremes appear (§35E/§35G); at rollover, the window closes and becomes eligible for `PREVIOUS_*` treatment as an entirely new record with its own new `period_start_time_utc`/`period_end_time_utc` — never a mutation of the "current" record's identity.

**Explicit labeling (per Part 8's instruction):** this period-window policy is **`ENGINEERING-PROVISIONAL`** — it is a reasonable, deterministic, fully-specified default, not merely a placeholder, but it is **not** described as broker-session-calibrated (FXCM's actual server-day/rollover convention may differ from UTC midnight) and **not** production-approved. **Author-approved (§35AP, item 9):** the author has explicitly ratified this exact policy exactly as documented; `poi/period_levels.py` may now be implemented against it.

### 35S. Structural Context Requirements — Corrected: `StructureAnalysis` Removed from This Milestone Entirely

**Corrected by the focused audit (Part 5, Option B): `StructureAnalysis` is not part of this milestone's public input at all.** The original draft accepted `StructureAnalysis` as a mandatory `PoiTimeframeInput` field while simultaneously stating no detector uses it for any gating purpose — a required input with no deterministic effect. Rather than retain an unused mandatory field, an unused optional field, or a "forward-compatible" placeholder, **the field is removed outright** (§35B/§35E/§35H). This section is retained to record why, not to describe an active input.

**Mandatory structural context: none, for any of the 32 implementable POI types, beyond each family's own candle-geometry rule.** Verified per family in §35J-§35R: no implementable POI specification anywhere in the approved knowledge base makes `StructureDirection`, `SwingRelationship`, `StructureTransition`, `CurrentStructureState`, protected/weak levels, BOS, or CHoCH a *mandatory gate*. This is not an oversight — it is the book's and every already-approved standard's own consistent position (verified verbatim, repeatedly: "not defined using HH, HL, BOS, CHoCH... or any other invented structure rule"; "does not require BOS (undefined in this project and not invoked here)").

**No optional/non-gating structure field either.** The original draft's `PoiObservation.source_structure_record_ids` (intended to let a caller attach `StructureTransition`/`SwingRelationship` record IDs as non-gating evidence) is removed along with the input itself (§35E) — an always-empty field serving no current purpose is not retained "for forward compatibility."

**Prohibited contradictory context:** not applicable — with no structural input at all, there is no "contradictory structure" case to define or reject.

**A future BOS/CHoCH is never treated as confirmation for an earlier POI:** structurally guaranteed even more strongly than before — with `StructureAnalysis` absent from the public input entirely, there is no code path through which any structure fact, past or future, could influence any detector's candidacy or confirmation.

**Structure context in a later milestone:** may be added when an approved POI rule is found to genuinely require it — as a scoped, per-type-documented field added deliberately for that rule, never as a standing, always-required, unused input. This milestone's own explicit exclusions (§35AL) record this as future, not current, work.

**Same-availability-group behavior and no-look-ahead gating:** governed uniformly by §35AD, not per-family; unaffected by the removal of `StructureAnalysis`, since no-look-ahead discipline here concerns candle/measurement availability only.

### 35T. POI Confirmation

**Two separated concepts, never conflated (corrected by the focused audit, Part 6 — a third, originally-proposed "validity" concept is removed):** source-candidate existence (a detector's own internal `*Candidate` `NamedTuple`, **private and unexported**) -> confirmed `PoiObservation` (emitted **only** once the family's exact confirmation rule passes; its mere existence is the confirmation signal, §35F) -> POI lifecycle (§35V, for the 18 lifecycle-eligible types).

**Exact confirmation rule per family** — already fully specified in §35J-§35R; summarized once here for the general pattern: **`availability_time_utc = MAX(availability among every source fact required for confirmation)`**, identical discipline to `1B-H`/`1B-I`. Same-candle candidate+confirmation applies to single-candle families (Pressure Wick, Hammer, Shooting Star); next-candle/multi-candle confirmation applies to multi-candle families (FVG's 3rd candle, Engulfing's 2nd candle, Morning/Evening Star's 3rd candle, Order Block's displacement candle, Base's departure candle, Buy-to-Sell/Sell-to-Buy's 3-bar reversal window). **Structure-transition confirmation and displacement confirmation** are never used as a POI's own confirmation gate (§35S — `StructureAnalysis` is not part of this milestone's input at all) — displacement *is* the candidate-forming event for FVG/OB/Base/reversal-candle families (it is intrinsic to the family's own formation rule, not a separate external confirmation source). **Return-to-zone confirmation** is never required for initial POI confirmation for any of the 32 types (verified per family) — a "first return" only matters later, for lifecycle interaction/reaction measurement (§35V), never for the POI's own existence. **Confirmation cancellation / candidate that never confirms:** every family's candidate rule is a strict pass/fail evaluated once, at its own defined confirmation instant — a candidate failing any mandatory condition produces **no** `PoiObservation` at all (never a cancelled/rejected public record; internal candidates are never exported, per Part 21's explicit instruction).

### 35U. POI Validity — Removed Entirely (Tombstone Section)

**No public "validity" contract or field of any kind exists in the corrected architecture — this section is retained only as a tombstone recording the removal, replacing the originally-proposed "POI Validity" content.** The audit found the original 2-member `PoiValidityStatus` (`FORMING`/`CONFIRMED`) conflated a pre-confirmation *candidate* concept with an ongoing *validity* concept — since `FORMING` was never emitted by any detector, every produced record's `validity_status` was always exactly `CONFIRMED`, a field carrying zero information. **Corrected model (§35T):** an internal candidate is private and unexported; a confirmed `PoiObservation` is emitted only after the exact confirmation rule passes; there is no intermediate public state and no public field recording "confirmed-ness," because existence of the record **is** that fact. This is a genuine simplification, not merely a disclosed one — `PoiObservation` has exactly 23 fields (§35E), none of which is a validity/confirmation-status field. No `PoiValidityStatus` enum, no `validity_status` field, and no export of either exists anywhere in this corrected architecture (§35D/§35E/§35Z/§35AJ).

**What a confirmed `PoiObservation` implies none of:** currently untouched (§35V's `freshness_status` is the separate, correct field for that); currently tradeable; an active BTMM setup; entry readiness (§35B). **What remains correctly resolved without a validity field:** untouched zone = `freshness_status = FRESH` (§35V, a lifecycle field); first/multiple touches = `PoiLifecycleTransition`/tap-count records (§35V, for the 18 lifecycle-eligible types only); partial/full mitigation = **not defined**, per the already-approved `POI_FRESHNESS_AND_AGE_STANDARD.md`'s own explicit scope limit ("It does not define partial mitigation, full mitigation... those remain unresolved and out of scope") — this milestone does not invent one either; structural contradiction = not applicable (§35S, no structural input exists to contradict); age/expiry = descriptive only (§35W); timeframe precedence = affects `effective_timeframe`/merge only (§35I/§35X); merged POI = a merged `PoiObservation` exists at all only because its own family rule independently confirmed — merging never creates or upgrades a candidate; source-output invalidity = a reference `PoiObservation` (Support/Resistance/Equal-Highs/Equal-Lows) whose source `SupportResistanceZone`/`EqualLevelCluster` is later invalidated is unaffected in its own existence (the source's own lifecycle is inherited separately, §35N/§35P) — there is no `PoiObservation`-level validity field to update either way.

### 35V. Breach, Reclaim, and Invalidation

**Reused verbatim, in full, from the already-approved `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` (Ambiguity 15) — no new formula is invented; this milestone is the first to actually *implement* this already-approved standard in code.** Exact reused formulas:

```
Zone Height = Zone Top - Zone Bottom
Contact Tolerance   = MAX(2 x Minimum Price Tick, MIN(0.05 x ATR(14), 0.10 x Zone Height))
Overshoot Tolerance = MAX(2 x Minimum Price Tick, MIN(0.10 x ATR(14), 0.25 x Zone Height))
```

**`PoiLifecycleStatus` (`StrEnum`) — corrected applicability: exactly 18 of the 32 implementable types are lifecycle-eligible (`32 − 2 equal-level − 12 period-level = 18`; §35C/§35D), never "30."** The 10 real states — `NO_BREACH`, `CLOSE_BREACH_CANDIDATE`, `RECLAIM_PENDING`, `RECLAIM_CONFIRMED`, `DISPLACEMENT_PENDING`, `DISPLACEMENT_AFTER_RECLAIM_CONFIRMED`, `RECLAIM_WITHOUT_DISPLACEMENT`, `RECLAIM_FAILED`, `FALSE_INVALIDATION_CONFIRMED`, `GENUINE_INVALIDATION_CONFIRMED` — apply only to the 18: all 10 volume + all 6 price-action + Support + Resistance. An 11th value, `NOT_APPLICABLE`, is permanently fixed for the remaining 14 (Equal Highs, Equal Lows, and all 12 period-level types, §35P/§35R) — none of these 14 ever transitions through any of the 10 real states.

**Corrected restatement of the reclaim-window boundary (Part 13 of the focused audit — this nuance was previously inherited only by reference, now stated explicitly):** the confirmed **breach candle itself is never counted as reclaim-window bar 1.** The first confirmed candle *strictly after* the breach candle is reclaim-window bar 1; the reclaim window contains exactly the next 3 eligible confirmed candles, ordered by canonical event chronology and gated by availability (no same-candle breach-and-reclaim is possible by construction, since bar 1 is defined as a distinct, later candle). If no reclaim occurs within those exact 3 candles, the Sustained Breach / Genuine Invalidation rule below applies. These breach/reclaim/displacement rules apply **only** to the 18 lifecycle-eligible types — they are never applied to Equal Highs/Lows or any period-level observation.

**Exact bullish/bearish inequalities (close-only; a wick alone never confirms breach):**

| Direction | `CLOSE_BREACH_CANDIDATE` condition |
|---|---|
| Bullish | `Zone Bottom - Candle Close > Overshoot Tolerance` |
| Bearish | `Candle Close - Zone Top > Overshoot Tolerance` |

**Reclaim (exactly the next 3 confirmed candles):** Bullish `Reclaim Close >= Zone Bottom + Contact Tolerance`; Bearish `Reclaim Close <= Zone Top - Contact Tolerance`. **Displacement-after-reclaim (exactly the next 3 confirmed candles after reclaim):** at least one close beyond `Zone Top + Contact Tolerance` (bullish) / `Zone Bottom - Contact Tolerance` (bearish), **and** the reclaim-to-displacement leg classified `FAST`/`STRONG_FAST` (reusing the Market Speed Standard's `Leg Bar Count`/`Net Directional Distance`/`Normalized Speed Per Bar`/`Directional Efficiency`/`Directional Candle Share` unmodified). **False Invalidation = the complete sequence** `CLOSE_BREACH_CANDIDATE -> RECLAIM_CONFIRMED (<=3 bars) -> DISPLACEMENT_AFTER_RECLAIM_CONFIRMED (<=3 bars after reclaim)`; `false_invalidation_confirmation_time = displacement_after_reclaim_confirmation_time`, never backdated. **Sustained Breach (required for Genuine Invalidation):** at least 2 of the 3 reclaim-window closes remain beyond the far boundary by more than that candle's own (freshly-computed) Overshoot Tolerance, **and** reclaim-window bar 3 itself qualifies, **and** no `RECLAIM_CONFIRMED` occurred. **Genuine Invalidation = final, non-reactivatable** (verified verbatim: "`INVALIDATED -> ACTIVE` is not allowed for the same POI instance... a later reaction... requires a new POI record, a new POI ID"); `genuine_invalidation_confirmation_time` = reclaim-window bar 3's close time; sets `CurrentPoiState.poi_lifecycle_status = GENUINE_INVALIDATION_CONFIRMED` permanently for that instance. **Failed Reclaim:** a new qualifying breach before displacement confirms starts a **new**, independently-evaluated `boundary_breach_event_id` and reclaim window; Genuine Invalidation is never declared from the first new breach candle alone.

**Forbidden transitions (reused verbatim):** `GENUINE_INVALIDATION_CONFIRMED -> FALSE_INVALIDATION_CONFIRMED` and the reverse, for the same `boundary_breach_event_id`.

**Repeated Tap:** one tap = one distinct interaction event (continuous multi-candle interactions count once); a later interaction becomes a **new** tap only after a qualifying exit-then-re-entry sequence (exact separation condition reused verbatim, §35V's source standard). Classification: `1 -> INITIAL_TAP`, `2 -> REPEATED_TAP`, `>=3 -> MULTIPLE_REPEATED_TAPS` — **evidence only, no automatic degradation** (reused verbatim: "a second tap automatically weakens the POI... automatically invalidates... automatically strengthens... automatically determines freshness... automatically determines entry validity" are all explicitly *not* assumed). Repeated-touch degradation itself remains `P0G-B008`, an unresolved empirical-calibration item explicitly out of scope for this milestone (§35AL).

**`PoiLifecycleTransition(ContractModel)`** — one immutable record per state-machine event (mirroring `StructureTransition`'s accumulating-tuple pattern), exact field order: `record_id`, `content_fingerprint`, `symbol`, `timeframe`, `poi_record_id`, `transition_type: PoiLifecycleTransitionType` (the 9 non-`NO_BREACH`/`NOT_APPLICABLE` event names above), `triggering_candle_record_id`, `event_time_utc`, `availability_time_utc`, `rule_version`, `contract_version`, `schema_version`, `evidence_classification`, `provenance_id`.

**Freshness/age (reused verbatim from the already-approved `POI_FRESHNESS_AND_AGE_STANDARD.md`, a deliberately minimal, observational-only model):** `freshness_status: FRESH | INTERACTED` (2 members only — no `PARTIALLY_MITIGATED`/`FULLY_MITIGATED`, per that standard's own explicit scope limit); `FRESH -> INTERACTED` is permanent, one-directional, triggered by `qualifying_interaction_time > poi_availability_time` (strict inequality; the availability/confirmation candle itself excluded even if it touches the zone; `NEAR_MISS` never qualifies). Descriptive age fields only, on `CurrentPoiState`: `age_start_time_utc = poi_availability_time_utc`, `age_in_confirmed_bars`, `elapsed_time_since_availability` — `automatic_age_expiration = DISABLED` always; age never causes weakening, expiration, invalidation, or strength reduction (§35W).

### 35W. Expiry

**No expiry threshold is invented. `EXPIRED` is absent from every public enum in this milestone** (`PoiLifecycleStatus`, §35V — the only lifecycle-adjacent public enum, since `PoiValidityStatus` was removed entirely, §35D/§35U) — per Part 24's explicit instruction ("If expiry is unresolved, exclude EXPIRED from the public lifecycle enum"). The already-approved `POI_FRESHNESS_AND_AGE_STANDARD.md` resolves `P0G-B007` only as far as "track age descriptively, never derive automatic expiration from it" (`automatic_age_expiration = DISABLED`, exact quote, §35V) — no candle-count, elapsed-time, or POI-family-specific expiration threshold exists anywhere in the approved knowledge base for any POI. A future, separate, explicit author decision and empirical calibration pass remains required before any expiry rule may be added; this milestone does not anticipate or half-implement one.

### 35X. Overlap and Merge

**Same-symbol and same-direction required** for any overlap/merge consideration — a bullish and a bearish observation are never merged regardless of geometric overlap (a documented worked example below shows they may still be reported as overlapping *zones*, but never merged). **Same-timeframe vs. cross-timeframe:** both considered — same-timeframe overlap uses the algorithm below directly; cross-timeframe overlap additionally triggers strong-timeframe precedence (§35I) when the `poi_type` also matches. **Same-family vs. cross-family:** overlap is evaluated across **all** `PoiType` values within the same `symbol`/direction/timeframe scope, not restricted to one family — an FVG legitimately overlaps an Order Block (both volume-family, different types) exactly as readily as it might overlap a Support zone (structural family); family is descriptive metadata on `PoiObservation`, never a filter on the overlap algorithm itself.

**Exact geometric overlap test — corrected by the focused audit (Part 9): the strict interval rule below applies only between two genuine, non-zero-height intervals. Zero-height point zones (all 12 period levels, §35R) require their own explicit rule, given separately below, since the strict inequality alone incorrectly excludes a point lying exactly inside another interval.**

**A. Two non-zero-height intervals:** `[top_a, bottom_a]` and `[top_b, bottom_b]`, both with `top > bottom`, overlap when `min(top_a, top_b) > max(bottom_a, bottom_b)` (strict; boundary-touching alone, i.e. `min(top_a,top_b) == max(bottom_a,bottom_b)`, is recorded as `BOUNDARY_TOUCHING`, a distinct, non-overlapping classification — never silently treated as overlap). **Containment** (`bottom_a <= bottom_b and top_a >= top_b`, one zone's range entirely encloses the other's) is a distinct sub-classification of overlap, `CONTAINS`/`CONTAINED_BY`.

**B. A point zone (`zone_top == zone_bottom == P`) against a non-zero-height interval `[bottom, top]`:** the point **overlaps** the interval when `bottom <= P <= top` — **inclusive of both boundaries**, deliberately not the strict inequality used between two non-zero-height intervals (Part 9's explicit correction: "strict interval intersection normally excludes a point unless explicitly handled"). A point lying inside or exactly on either boundary of the interval is `CONTAINED_BY` that interval; a non-zero-height interval can never be `CONTAINS`-classified by a point (a point cannot enclose a wider range).

**C. Two point zones**, `P_a` and `P_b`: they overlap **only when `P_a == P_b`** exactly (no tolerance is added — each point is already each family's own approved, exact price). Two distinct prices, however close, do not overlap and are not `BOUNDARY_TOUCHING` (that classification applies only to non-zero-height intervals meeting at a shared edge, not to two distinct points).

**Tolerance:** none added to the raw zone boundaries themselves for any of the three overlap cases above (the boundaries are already each family's own approved, tolerance-inclusive geometry, §35J-§35R) — overlap is a pure geometric test on the stored `zone_top`/`zone_bottom` values, not a re-tolerance-adjusted one.

**Mitigation/fill concepts (partial fill, full fill, immediate mitigation) do not apply to period-level point zones** — their `PoiLifecycleStatus` is permanently `NOT_APPLICABLE` (§35R/§35V), so no interaction/reaction/mitigation formula that assumes a non-zero Zone Height is ever evaluated against them.

**Merge eligibility (all required):** same `symbol`; same `PoiDirection`; overlapping or containing zones (per the test above); different `PoiObservation.record_id`s (a POI is never merged with itself). **Merge is *cross-timeframe-triggered only* in this milestone** — same-`poi_type` cross-timeframe overlap always merges (§35I); cross-`poi_type` or same-timeframe overlap is **reported but never merged** (`PoiObservation.merged_source_poi_record_ids` stays empty; the overlap fact itself is exposed via a separate, read-only `PoiOverlapRelationship` observation — see below). **Merge prohibition:** an already-`GENUINE_INVALIDATION_CONFIRMED` observation is never merged as a parent (it may remain listed as an overlapping/contained child fact only); a `FORMING` observation is never merged (§35U notes none are ever emitted, so this is vacuously satisfied in V1).

**Representative boundaries after merge:** the merged (parent, stronger-timeframe) observation's own `zone_top`/`zone_bottom` are used unmodified — merging never recomputes, averages, or widens a boundary; the weaker-timeframe child's boundaries remain independently readable on its own, separately-identified `PoiObservation` record (never deleted). **Effective timeframe:** set to the stronger (parent) timeframe on the merge-result relationship; each individual `PoiObservation.effective_timeframe` field is set only on the record that was actually merged-into-as-a-child (its `effective_timeframe` becomes the parent's timeframe while its own `source_timeframe` stays unchanged) — the parent's own `effective_timeframe` always equals its `source_timeframe`.

**Parent and child identities:** both remain independently resolvable `record_id`s; the child's `PoiObservation` is never deleted or hidden; `merged_source_poi_record_ids` on the parent lists every merged child's `record_id`. **Content fingerprint changes:** the parent's `content_fingerprint` changes when `merged_source_poi_record_ids` changes (it is a public field, §35G); the child's own `content_fingerprint` is unaffected by being merged into a parent (merging is recorded only on the parent side). **Whether merged source POIs remain separately observable:** yes, always — `PoiAnalysis.poi_observations` (§35Z) includes every confirmed observation, merged-into or not; merging never removes an entry from the aggregate. **Whether one source POI may belong to more than one merged parent:** **no** — a child is merged into at most one parent (the single strongest-timeframe same-`poi_type` overlapping observation); if multiple same-timeframe-strength candidates could theoretically both qualify as parent (structurally impossible under §35I's strict distinct-integer-rank total order), the earliest-`availability_time_utc` one wins deterministically — no transitive ambiguity is possible because merge parenthood is a function of a strict total order (timeframe rank, then availability time, then `record_id`), not a graph relation.

**`PoiOverlapRelationship`** — a new, small, immutable read-only observation (not itself identity-bearing beyond a deterministic derived key) recording every non-merge overlap/containment fact (cross-family or same-timeframe): `symbol`, `direction`, `poi_a_record_id`, `poi_b_record_id` (canonically ordered, `poi_a_record_id < poi_b_record_id` as strings, so `A overlaps B` and `B overlaps A` are the same fact, never double-recorded), `relationship_type: PoiOverlapRelationshipType` (`OVERLAPPING`, `CONTAINS`, `CONTAINED_BY`, `BOUNDARY_TOUCHING`), `overlap_top`, `overlap_bottom` (the intersection range), `evaluated_at_time_utc`.

**Worked examples (no transitive ambiguity):**
1. **A overlaps B; B overlaps C; A does not overlap C** — three independent pairwise `PoiOverlapRelationship` facts (`A-B: OVERLAPPING`, `B-C: OVERLAPPING`); no `A-C` record is created, and no transitive "A overlaps C" is ever inferred — overlap is evaluated strictly pairwise over the exact stored geometry, never propagated through an intermediate.
2. **Strong timeframe contains weak timeframe (same `poi_type`)** — merge triggers (§35I); the D1 parent's `merged_source_poi_record_ids` includes the M15 child's `record_id`; both remain independently queryable.
3. **Bullish and bearish zones overlap** — `PoiOverlapRelationship` is **not** created (same-symbol-and-direction is a mandatory precondition for the relationship, not only for merge) — a bullish/bearish geometric overlap is a legitimate, common market fact (e.g., an Order Block and an opposing Engulfing at a reversal point) but is deliberately not tracked as a "relationship" in this milestone, to avoid implying any interaction meaning beyond raw geometry; both observations remain independently queryable and their own `zone_top`/`zone_bottom` are directly comparable by any caller who wants this fact.
4. **FVG overlaps Order Block** — `PoiOverlapRelationship(relationship_type=OVERLAPPING)`, cross-family, cross-`poi_type`, same-timeframe or cross-timeframe (if cross-timeframe and different `poi_type`, no merge, relationship only).
5. **Support overlaps Order Block** — identical treatment to example 4.

### 35Y. Single-Region and Limit Rules

**No visualization-driven analytical limit is implemented.** Any pre-existing "one POI region per timeframe" or "N-POI limit per timeframe" language in the book is a **downstream display/selection concern, never an analytical one** — per Part 27's explicit instruction ("Do not silently discard valid POIs merely because a future chart renderer has a box limit"). `PoiAnalysis` (§35Z) preserves every confirmed, non-superseded `PoiObservation` with no maximum count, no per-timeframe cap, and no silent replacement of an older POI by a newer one of the same type unless the two are geometrically overlapping and generate an actual merge (§35X) — a non-overlapping second Order Block on the same timeframe is simply a second, independent `PoiObservation`, never deleted, replaced, or capped. Any future display-layer limit belongs to a not-yet-designed visualization milestone (explicitly excluded, §35AL), not to this analytical layer.

### 35Z. Output Model

**Four contracts, not five — `MergedPoi` is folded into `PoiObservation` itself (via `merged_source_poi_record_ids`, §35X) rather than being a separate contract,** since a "merged POI" is not a structurally distinct kind of fact — it is exactly a `PoiObservation` whose `merged_source_poi_record_ids` happens to be non-empty; a fifth contract would duplicate every field `PoiObservation` already has.

1. **`PoiObservation`** — §35E.
2. **`PoiLifecycleTransition`** — §35V.
3. **`PoiOverlapRelationship`** — §35X.
4. **`CurrentPoiState`** — one immutable current-snapshot record per confirmed POI instance (mirroring `CurrentStructureState`'s per-scope singleton pattern, but per-*POI-instance* here, not per-symbol/timeframe globally, since a POI package must track many simultaneously-active POIs, not one global direction): exact field order — **corrected: `validity_status` removed (§35D/§35T, `PoiValidityStatus` removed entirely); every field below reflects the corrected 21-field contract** —

```
record_id: UUIDv7
content_fingerprint: SHA256Fingerprint
symbol: InternalSymbol
timeframe: Timeframe
poi_record_id: UUIDv7
poi_type: PoiType
direction: PoiDirection
poi_lifecycle_status: PoiLifecycleStatus
freshness_status: PoiFreshnessStatus
tap_count: int
tap_classification: PoiTapClassification | None
age_start_time_utc: datetime
age_in_confirmed_bars: int
elapsed_time_since_availability: timedelta
latest_lifecycle_transition_id: UUIDv7 | None
availability_time_utc: datetime
rule_version: SemVer
contract_version: SemVer
schema_version: SemVer
evidence_classification: EvidenceClassification
provenance_id: UUIDv7
```

**`PoiAnalysis`** aggregate, exact field order:

```
symbol: InternalSymbol | None
analyzed_timeframes: tuple[Timeframe, ...]
analyzed_candle_count_by_timeframe: tuple[int, ...]
poi_observations: tuple[PoiObservation, ...]
poi_lifecycle_transitions: tuple[PoiLifecycleTransition, ...]
poi_overlap_relationships: tuple[PoiOverlapRelationship, ...]
current_poi_states: tuple[CurrentPoiState, ...]
```

**No field anywhere in any of these five types for:** BTMM pattern, entry, stop loss, take profit, position sizing, trade outcome, signal confidence, or AI score — verified absent by construction (every field above is enumerated exhaustively; none references any excluded concept, §35AL).

### 35AA. Public API

**One exact synchronous entry point, no separate analyzer per POI family** (per Part 29's explicit instruction):

```python
def analyze_pois(
    timeframe_inputs: tuple[PoiTimeframeInput, ...],
    configuration: PoiConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> PoiAnalysis:
    ...
```

**Empty behavior:** `timeframe_inputs == ()` returns `PoiAnalysis(symbol=None, analyzed_timeframes=(), analyzed_candle_count_by_timeframe=(), poi_observations=(), poi_lifecycle_transitions=(), poi_overlap_relationships=(), current_poi_states=())` — identical empty-aggregate discipline to `analyze_market_measurements()`/`analyze_structure_state()`. **Unsupported-spec behavior:** a `PoiConfiguration` may disable individual `PoiType` members (§35AG); a disabled type is simply never detected — no error, no placeholder observation. **Deterministic ordering:** §35AF. **Errors:** §35AB. **Identity-failure behavior:** `DerivedIdentityCollisionError` reused unmodified from `domain`, raised by the shared `_IdentityResolver` (§35G) exactly as in every prior milestone.

### 35AB. Error Vocabulary

**Compact, typed, `ValueError`-based, reusing existing errors wherever semantics genuinely match (4 reused unmodified from `domain`; 6 new; 10 total):**

| Error | Reused/New | Trigger |
|---|---|---|
| `MixedSymbolAnalysisError` | Reused (`domain`) | Mixed `symbol` across `timeframe_inputs` |
| `DuplicateCandleRecordError` | Reused (`domain`) | Duplicate candle `record_id` within one bundle |
| `UnsortedCandleSequenceError` | Reused (`domain`) | A bundle's own `candles` not canonically sorted |
| `DerivedIdentityCollisionError` | Reused (`domain`) | Identity provider returns one ID for two semantic keys |
| `InvalidStructureConfigurationError`-equivalent -> new `InvalidPoiConfigurationError` | New | Non-positive/invalid `PoiConfiguration` field |
| `DuplicatePoiTimeframeInputError` | New | Two `timeframe_inputs` entries share one `Timeframe` |
| `UnsortedPoiTimeframeInputError` | New | `timeframe_inputs` not in ascending timeframe-strength order |
| `InputPrefixMismatchError` | New | A bundle's `MarketMeasurementAnalysis.analyzed_candle_count`/`symbol` disagrees with its own `candles` (narrowed by the focused audit — the `structure_analysis` mismatch case no longer exists, §35H) |
| `MissingSourceRecordError` | New | A detector references a candle/measurement `record_id` absent from the supplied bundle |
| `ImpossiblePoiLifecycleTransitionError` | New | An internal state-machine invariant violation (e.g., a forbidden transition, §35V) is reached — a defensive, internal-consistency guard, not expected to be caller-triggerable given the validated inputs |

**No internal implementation exception is ever exposed publicly** (matching every prior milestone's discipline) — no `*Candidate` construction error, no private helper's `AssertionError`, no merge-graph internal error leaks past `analyze_pois()`'s boundary.

### 35AC. Evidence Classification

**Exactly one `EvidenceClassification` value per public output: `ENGINEERING_PROVISIONAL`**, uniformly across `PoiObservation`, `PoiLifecycleTransition`, `PoiOverlapRelationship`, and `CurrentPoiState` — identical policy to `1B-H`/`1B-I`. **Never `AUTHOR_APPROVED`** (a real, distinct, separately-selectable member of the same enum, verified against `contracts/provenance_record.py` — reused, not redefined) — the underlying *rules* this milestone implements are themselves author-approved (Ambiguities 1-15, RECON-D1-D5, GROUP3-D1-D9, the Freshness/Age standard), but that document-level approval status is a wholly separate axis from the per-record `evidence_classification` field, which describes the record's own calibration/validation state, not whether its governing rule was approved. **Never a compound string.** No `BOOK_SOURCED`/`BOOK_SUPPORTED_UNDERLYING_CONCEPT`/`AUTHOR_ADDED_PROJECT_TERMINOLOGY`/`EMPIRICALLY_CALIBRATED`/`OUT_OF_SAMPLE_VALIDATED`/`PRODUCTION_APPROVED` value is ever emitted by this milestone — every one of those remains either a document-level provenance label (used in prose, in `knowledge/`, never in a `ContractModel` field) or a genuinely future state this milestone has not reached.

### 35AD. No-Look-Ahead

**Exact availability per event, all consistent with the single rule `availability_time_utc = MAX(availability among every required source fact)`, never event-time-only, never processing-time, never a future fact:**

- **Candidate/confirmation:** the family-specific instant defined in §35J-§35R (e.g., FVG's 3rd-candle close, Order Block's displacement-candle close) — never the origin/first-candle time.
- **Merge:** the later of the parent's own availability and the child's own availability (a merge relationship cannot be exposed before both sides individually exist).
- **Strong-timeframe precedence:** evaluated only among observations whose own `availability_time_utc` has already passed at evaluation time — a higher-timeframe candle is never consulted before its own actual close/availability, exactly as `structure`'s merged event-timeline walk already guarantees for candle/swing/relationship events; this milestone's per-timeframe merged walk (§35AE) extends the identical `(timestamp, kind)`-sorted discipline across `PoiTimeframeInput` bundles.
- **First touch, breach, reclaim, invalidation:** each event's own `availability_time_utc` per §35V's exact formulas — a breach can never be "discovered" using a candle that has not yet closed, and reclaim/displacement windows are evaluated only over already-available confirmed candles.
- **Current-state snapshot:** `CurrentPoiState.availability_time_utc` = the latest of the originating POI's own availability and its most recent lifecycle transition's availability — identical pattern to `CurrentStructureState`.

**Multi-timeframe discipline (explicit, per Part 32):** a higher-timeframe candle/POI is never used before its own actual availability, regardless of a lower-timeframe candle's event time being numerically later on the clock but the higher-timeframe candle not yet having closed; an incomplete (still-forming) candle is never treated as a completed POI source for any family (every family's own confirmation rule already requires a *confirmed*, i.e. closed, candle, §35T); no replay availability group is ever partially processed (§35AE). **Same-availability-group phase ordering:** within one merged event-timeline pass, per timestamp, the exact order is (1) candle-close-triggered lifecycle evaluation against pre-existing `CurrentPoiState` only (breach/reclaim/displacement checks use state as of the *start* of that timestamp, mirroring `structure`'s own candle-before-swing-visibility ordering), (2) new-candidate detection/confirmation events, (3) merge/overlap re-evaluation, (4) `CurrentPoiState` finalization for that timestamp — guaranteeing a POI activated at a given timestamp cannot be breached by a candle sharing that same timestamp, identical in spirit to `structure`'s proven activation-group-immunity invariant.

### 35AE. Replay Equivalence Procedure

**Multi-timeframe extension of the already-proven `1B-H`/`1B-I` batch/replay equivalence pattern**, for each global availability group (across all supplied timeframes simultaneously, per Part 33):

1. Append all newly-available candles, across every timeframe, atomically for that availability instant.
2. Recompute (or accept caller-supplied, already-recomputed) `MarketMeasurementAnalysis` for each affected timeframe's growing prefix.
3. Re-invoke `analyze_pois()` on the identical visible `PoiTimeframeInput` state (all timeframes' bundles, each reflecting exactly the candles/measurements available as of that instant — corrected: no `StructureAnalysis` recomputation step, since it is no longer part of the input, §35B/§35H).
4. Compare against an independent, one-shot, direct-batch `analyze_pois()` call over the complete final state — must be identical for the same final visible prefix.
5. Verify stable source-`PoiObservation` identities across growing prefixes (§35F) — an unchanged POI's `record_id` must not change as later, unrelated candles/POIs are appended, including the 6 content-evolving "Current" period-level types (§35E/§35R — identity stable, content and fingerprint change).
6. Verify stable `PoiLifecycleTransition` identities (§35F) across growing prefixes.
7. Verify `CurrentPoiState.content_fingerprint` changes only when its own public content changes (record_id stable, fingerprint reflecting only real content change) — mirroring `1B-I`'s proven test pattern.
8. Verify merge output (`merged_source_poi_record_ids`, §35X) is identical between batch and replay for the same final prefix.
9. Verify strong-timeframe precedence (§35I) is stable — a merge decision made at an earlier prefix is never silently reversed by later data (once a child is merged into a parent, it stays merged into that same parent for the remainder of the analyzed history — a `record_id`-referenced, one-time relationship, not a rolling re-evaluation).
10. Verify no future input affected the result — the standard no-look-ahead replay-equivalence check already proven twice in this project.

**Accepted provisional complexity:** repeated-prefix, full-session, multi-timeframe replay is provisionally superlinear (each `analyze_pois()` call re-scans every timeframe's full visible prefix), explicitly documented as acceptable and non-production, identical in kind to `1B-H`/`1B-I`'s own accepted precedent (§35AK).

### 35AF. Deterministic Ordering

**Total order, no dependency on dictionary/set/file-discovery/detector-registration order (all fields explicit, never implicit iteration order):**

- **Source `PoiObservation`s** (within `PoiAnalysis.poi_observations`): `(availability_time_utc, source_timeframe.value, family.value, poi_type.value, direction.value, zone_bottom, zone_top, str(record_id))`.
- **`PoiLifecycleTransition`s:** `(availability_time_utc, event_time_utc, transition_type.value, str(poi_record_id), str(record_id))`.
- **`PoiOverlapRelationship`s:** `(evaluated_at_time_utc, str(poi_a_record_id), str(poi_b_record_id))`.
- **`CurrentPoiState`s:** `(symbol.value, timeframe.value, poi_type.value, str(poi_record_id))`.

### 35AG. Configuration

**One immutable `PoiConfiguration(ContractModel)`, constructing with exactly one required field (`minimum_price_tick`, matching `MarketMeasurementConfiguration`'s own precedent), every other field defaulted to the exact already-approved value it reuses. Corrected by the focused audit (Part 11): `strong_poi_timeframes` is removed — no described algorithm ever consulted it (§35I's merge-precedence and §35X's merge test both use only the numeric `_TIMEFRAME_STRENGTH_RANK`); no replacement unused field is introduced.**

```
minimum_price_tick: Decimal

enabled_poi_types: frozenset[PoiType] = frozenset(<all 32 implementable members>)
supported_symbols: frozenset[InternalSymbol] = frozenset({XAUUSD, EURUSD, GBPUSD})

order_block_size_ratio_standard: Decimal = Decimal("2.0")
order_block_size_ratio_strong: Decimal = Decimal("3.0")
small_candle_ratio_standard: Decimal = Decimal("0.50")
small_candle_ratio_strong: Decimal = Decimal("0.3333")

base_min_candles: int = 2
base_max_candles: int = 6
base_height_atr_multiplier: Decimal = Decimal("0.75")
base_height_departure_multiplier: Decimal = Decimal("0.60")
base_midpoint_drift_ratio: Decimal = Decimal("0.25")
base_overlap_ratio_minimum: Decimal = Decimal("0.50")

pressure_wick_share_standard: Decimal = Decimal("0.40")
pressure_wick_body_efficiency_standard: Decimal = Decimal("0.25")
pressure_wick_dominance_standard: Decimal = Decimal("2.0")
pressure_wick_close_position_standard: Decimal = Decimal("0.60")
pressure_wick_share_strong: Decimal = Decimal("0.50")
pressure_wick_body_efficiency_strong: Decimal = Decimal("0.30")
pressure_wick_dominance_strong: Decimal = Decimal("3.0")
pressure_wick_close_position_strong: Decimal = Decimal("0.70")
pressure_wick_range_context_strong: Decimal = Decimal("1.25")

hammer_shooting_star_wick_share_standard: Decimal = Decimal("0.60")
hammer_shooting_star_body_efficiency_standard: Decimal = Decimal("0.30")
hammer_shooting_star_opposite_wick_standard: Decimal = Decimal("0.10")
hammer_shooting_star_wick_share_strong: Decimal = Decimal("0.70")
hammer_shooting_star_body_efficiency_strong: Decimal = Decimal("0.20")
hammer_shooting_star_opposite_wick_strong: Decimal = Decimal("0.05")

doji_body_efficiency_standard: Decimal = Decimal("0.10")
doji_body_efficiency_strong: Decimal = Decimal("0.05")

reversal_candidate_size_ratio_standard: Decimal = Decimal("2.0")
reversal_candidate_size_ratio_strong: Decimal = Decimal("3.0")
reversal_body_efficiency_standard: Decimal = Decimal("0.60")
reversal_body_efficiency_strong: Decimal = Decimal("0.70")
reversal_close_position_standard: Decimal = Decimal("0.70")
reversal_close_position_strong: Decimal = Decimal("0.80")

zone_contact_tolerance_atr_multiplier: Decimal = Decimal("0.05")
zone_contact_tolerance_zone_height_multiplier: Decimal = Decimal("0.10")
zone_overshoot_tolerance_atr_multiplier: Decimal = Decimal("0.10")
zone_overshoot_tolerance_zone_height_multiplier: Decimal = Decimal("0.25")

reclaim_window_bars: int = 3
displacement_window_bars: int = 3

rule_version: SemVer = SemVer.parse("1.0.0")
contract_version: SemVer = SemVer.parse("0.1.0")
schema_version: SemVer = SemVer.parse("0.1.0")
evidence_classification: EvidenceClassification = EvidenceClassification.ENGINEERING_PROVISIONAL
```

**No duplication of ATR, market-data validation, structure configuration, or measurement configuration** — `PoiConfiguration` carries only POI-specific thresholds; `ATR(14)` itself is read from the caller-supplied `MarketMeasurementAnalysis`'s already-computed values (via `measurements.compute_atr_series`, reused, never recomputed independently), and structural validity (mixed symbol/timeframe/unsorted candles) is validated once per bundle exactly as `domain`/`structure` already validate their own inputs — `poi/analyzer.py` performs its *own* additional cross-bundle checks (§35H) but never re-derives ATR or re-validates a single bundle's internal candle ordering a second time beyond what `analyze_market_measurements()`/`analyze_structure_state()` already guarantee for a well-formed input.

**No default silently enables a deferred/unsupported POI type:** `enabled_poi_types`'s default `frozenset` contains exactly the 32 implementable `PoiType` members (§35C) — since no Trendline/Swing-High/Swing-Low `PoiType` member exists at all (§35D), there is no way to even attempt enabling a deferred type; `enabled_poi_types` may only ever be a subset of the 32.

### 35AH. Exact File Scope

**18 new source files, 1 modified existing source file, 16 new test files — 35 total changed paths (34 new + 1 modified).** Source/test split 18/16. New/modified split 34/1. This exceeds the 10-18 source-path guidance ceiling by exactly 0 (18, at the top of the range) and the 8-14 test-path guidance by 2 (16) — justified, disclosed, and not arbitrary: 32 implementable `PoiType` members across 10 genuinely distinct detector algorithms is roughly 3x either prior milestone's POI-adjacent scope, and one dedicated test file per detector family (plus 5 cross-cutting files: configuration, lifecycle/freshness, overlap/merge/precedence, analyzer API, replay equivalence, exports) is the minimum honest split that avoids one monolithic test file covering unrelated families.

**18 new source files** (new top-level package `poi/`):

| Creation order | Path |
|---|---|
| 113 | `src/btmm_ai_scanner/poi/__init__.py` |
| 114 | `src/btmm_ai_scanner/poi/enums.py` |
| 115 | `src/btmm_ai_scanner/poi/configuration.py` |
| 116 | `src/btmm_ai_scanner/poi/observation.py` |
| 117 | `src/btmm_ai_scanner/poi/lifecycle.py` |
| 118 | `src/btmm_ai_scanner/poi/current_state.py` |
| 119 | `src/btmm_ai_scanner/poi/order_blocks.py` |
| 120 | `src/btmm_ai_scanner/poi/fair_value_gaps.py` |
| 121 | `src/btmm_ai_scanner/poi/reversal_candles.py` |
| 122 | `src/btmm_ai_scanner/poi/bases.py` |
| 123 | `src/btmm_ai_scanner/poi/pressure_wicks.py` |
| 124 | `src/btmm_ai_scanner/poi/engulfing.py` |
| 125 | `src/btmm_ai_scanner/poi/single_candle_reversals.py` |
| 126 | `src/btmm_ai_scanner/poi/three_candle_stars.py` |
| 127 | `src/btmm_ai_scanner/poi/reference_zones.py` |
| 128 | `src/btmm_ai_scanner/poi/period_levels.py` |
| 129 | `src/btmm_ai_scanner/poi/overlap.py` |
| 130 | `src/btmm_ai_scanner/poi/analyzer.py` |

**1 modified existing path (no new row, annotated in place, identical in kind to `1B-I-STRUCTURE`'s own row-82 annotation):** `src/btmm_ai_scanner/domain/enums.py` — `DerivedOutputType` gains exactly 3 new members (`POI_OBSERVATION`, `POI_LIFECYCLE_TRANSITION`, `CURRENT_POI_STATE`), appended after the existing 8; no existing member renamed, removed, or reordered.

**16 new test files (corrected per-file distribution, Part 17 of the focused audit — same 16 files, same 120 total, redistributed to accommodate every newly-required test):**

| Creation order | Path | Test count |
|---|---|---|
| 131 | `tests/unit/test_poi_configuration.py` | 7 |
| 132 | `tests/unit/test_order_blocks.py` | 8 |
| 133 | `tests/unit/test_fair_value_gaps.py` | 8 |
| 134 | `tests/unit/test_reversal_candles.py` | 8 |
| 135 | `tests/unit/test_bases.py` | 8 |
| 136 | `tests/unit/test_pressure_wicks.py` | 6 |
| 137 | `tests/unit/test_engulfing.py` | 5 |
| 138 | `tests/unit/test_single_candle_reversals.py` | 5 |
| 139 | `tests/unit/test_three_candle_stars.py` | 5 |
| 140 | `tests/unit/test_reference_zones.py` | 7 |
| 141 | `tests/unit/test_period_levels.py` | 8 |
| 142 | `tests/unit/test_poi_lifecycle_and_freshness.py` | 14 |
| 143 | `tests/unit/test_poi_overlap_merge_and_precedence.py` | 9 |
| 144 | `tests/unit/test_poi_analyzer_api.py` | 11 |
| 145 | `tests/unit/test_poi_batch_replay_equivalence.py` | 6 |
| 146 | `tests/unit/test_poi_exports.py` | 5 |

**Total: 35 changed paths.** Creation order 113-146 (34 new-row values, 146-113+1 = 34, correct), bringing the master inventory from 113 rows (creation order 0-112) to 147 rows (creation order 0-146).

**Corrected path-split terminology (Part 3 of the focused audit — both exact splits stated explicitly, never conflated):**

- **NEW-PATH SPLIT:** 18 new source paths / 16 new test paths (34 new paths total).
- **AFFECTED-PATH SPLIT:** 19 source paths (18 new + 1 modified `domain/enums.py`) / 16 test paths (35 affected paths total).

"18/16" is never used alone to describe the complete affected-path source/test split — it describes only the new-path split; the affected-path split is always 19/16.

**Dependency direction — corrected (Part 5, `structure` removed):** `poi/` depends on `domain` (`ConfirmedSwing`, `SwingType`, `DisplacementObservation`, `EqualLevelCluster`, `SupportResistanceZone`, `Trendline`, `MarketMeasurementAnalysis`, `DerivedOutputType`, `DerivedOutputIdentityProvider`, 4 reused errors), `measurements` (`compute_atr_series` and candle-metric helpers, reused unmodified), `contracts`, `config` — does **not** depend on `structure` (removed entirely from this milestone, §35B/§35S) and does **not** depend on `market_data`'s pipeline/repository/replay modules directly (a caller may compose `poi/` with `market_data.InMemoryHistoricalReplaySource` at its own discretion, exactly as `domain` already does).

### 35AI. Exact Test Coverage — 120 New Top-Level Test Functions

**Total: 120 new top-level test functions across 16 files (7+8+8+8+8+6+5+5+5+7+8+14+9+11+6+5). Combined with the existing 380: 500.** Corrected per Part 17 of the focused audit — every removed/obsolete test (mandatory `StructureAnalysis` consistency, `PoiValidityStatus`/`FORMING`, unused `strong_poi_timeframes` behavior, the inaccurate 24-export-count assumption) is replaced with named coverage for a genuinely required behavior; several bullish/bearish-mirror test pairs are consolidated into one combined-assertion test to make room without exceeding 120 or adding a 17th file.

| File | Count | Test names |
|---|---|---|
| `test_poi_configuration.py` | 7 | `test_poi_configuration_default_values_match_approved_standards`, `test_poi_configuration_is_frozen_and_immutable`, `test_poi_configuration_rejects_non_positive_thresholds`, `test_poi_configuration_evidence_classification_is_engineering_provisional`, `test_poi_configuration_has_no_strong_poi_timeframes_field`, `test_volume_family_poi_types_use_option_b_price_action_proxies`, `test_proxy_metrics_are_computed_internally_and_never_exposed_publicly` |
| `test_order_blocks.py` | 8 | `test_buy_order_block_candidate_requires_size_ratio_at_least_two`, `test_buy_order_block_zone_uses_full_range_of_smaller_candle`, `test_buy_order_block_availability_equals_displacement_candle_close`, `test_buy_order_block_strong_classification_requires_size_ratio_at_least_three`, `test_sell_order_block_candidate_requires_size_ratio_at_least_two`, `test_sell_order_block_zone_uses_full_range_of_smaller_candle`, `test_sell_order_block_availability_equals_displacement_candle_close`, `test_sell_order_block_strong_classification_requires_size_ratio_at_least_three` |
| `test_fair_value_gaps.py` | 8 | `test_buy_fair_value_gap_requires_strict_three_candle_gap_geometry`, `test_buy_fair_value_gap_zone_spans_first_candle_high_to_third_candle_low`, `test_buy_fair_value_gap_availability_equals_third_candle_close`, `test_buy_fair_value_gap_rejected_if_gap_closes_before_third_candle`, `test_sell_fair_value_gap_requires_strict_three_candle_gap_geometry`, `test_sell_fair_value_gap_zone_spans_third_candle_high_to_first_candle_low`, `test_sell_fair_value_gap_availability_equals_third_candle_close`, `test_sell_fair_value_gap_rejected_if_gap_closes_before_third_candle` |
| `test_reversal_candles.py` | 8 | `test_buy_to_sell_candidate_requires_size_ratio_body_efficiency_and_close_position`, `test_buy_to_sell_zone_uses_candidate_candle_full_range`, `test_buy_to_sell_confirms_within_three_bar_reversal_window`, `test_buy_to_sell_availability_equals_reversal_confirmation_time`, `test_sell_to_buy_candidate_requires_size_ratio_body_efficiency_and_close_position`, `test_sell_to_buy_zone_uses_candidate_candle_full_range`, `test_sell_to_buy_confirms_within_three_bar_reversal_window`, `test_sell_to_buy_availability_equals_reversal_confirmation_time` |
| `test_bases.py` | 8 | `test_base_rally_requires_two_to_six_compact_base_candles`, `test_base_rally_zone_spans_base_low_to_base_high`, `test_base_rally_departure_candle_requires_size_ratio_at_least_two`, `test_base_rally_availability_equals_departure_candle_close`, `test_base_drop_requires_two_to_six_compact_base_candles`, `test_base_drop_zone_spans_base_low_to_base_high`, `test_base_drop_departure_candle_requires_size_ratio_at_least_two`, `test_base_drop_availability_equals_departure_candle_close` |
| `test_pressure_wicks.py` | 6 | `test_bullish_pressure_wick_requires_lower_wick_share_and_close_position`, `test_bullish_pressure_wick_zone_uses_lower_rejection_wick_only`, `test_bearish_pressure_wick_requires_upper_wick_share_and_close_position`, `test_bearish_pressure_wick_zone_uses_upper_rejection_wick_only`, `test_pressure_wick_strong_classification_requires_higher_thresholds_for_both_directions`, `test_pressure_wick_confirms_on_own_candle_close_for_both_directions` |
| `test_engulfing.py` | 5 | `test_bullish_engulfing_requires_size_ratio_at_least_two`, `test_bullish_engulfing_zone_uses_engulfed_candle_full_range`, `test_bearish_engulfing_requires_size_ratio_at_least_two`, `test_bearish_engulfing_zone_uses_engulfed_candle_full_range`, `test_engulfing_availability_equals_engulfing_candle_close_for_both_directions` |
| `test_single_candle_reversals.py` | 5 | `test_hammer_requires_lower_wick_share_body_efficiency_and_opposite_wick_thresholds`, `test_hammer_zone_uses_rejection_wick_only`, `test_shooting_star_requires_upper_wick_share_body_efficiency_and_opposite_wick_thresholds`, `test_shooting_star_zone_uses_rejection_wick_only`, `test_hammer_and_shooting_star_confirm_on_own_candle_close` |
| `test_three_candle_stars.py` | 5 | `test_morning_star_requires_doji_body_efficiency_threshold`, `test_morning_star_zone_uses_middle_doji_candle_full_range`, `test_evening_star_requires_doji_body_efficiency_threshold`, `test_evening_star_zone_uses_middle_doji_candle_full_range`, `test_morning_and_evening_star_availability_equals_third_candle_close` |
| `test_reference_zones.py` | 7 | `test_support_poi_inherits_zone_boundaries_from_support_resistance_zone`, `test_resistance_poi_inherits_zone_boundaries_from_support_resistance_zone`, `test_support_break_candidate_and_close_breach_candidate_coexist_independently`, `test_equal_highs_and_equal_lows_poi_inherit_zone_boundaries_from_equal_level_cluster`, `test_equal_highs_and_equal_lows_never_emit_lifecycle_transitions`, `test_support_and_resistance_map_to_bullish_and_bearish_direction_respectively`, `test_equal_highs_and_equal_lows_map_to_bearish_and_bullish_direction_respectively` |
| `test_period_levels.py` | 8 | `test_period_level_windows_use_exact_utc_calendar_day_week_and_month_boundaries`, `test_previous_period_skips_empty_weekend_and_holiday_windows`, `test_previous_period_level_content_is_fixed_after_period_closes`, `test_current_period_level_fingerprint_changes_as_new_extreme_appears`, `test_current_day_high_and_low_track_running_extreme_within_the_window`, `test_period_level_lifecycle_status_is_fixed_at_not_applicable`, `test_period_level_identity_is_stable_across_a_growing_window_and_rollover_creates_a_new_record`, `test_all_twelve_period_level_types_are_covered` |
| `test_poi_lifecycle_and_freshness.py` | 14 | `test_close_breach_candidate_requires_close_strictly_beyond_overshoot_tolerance`, `test_wick_beyond_far_boundary_without_close_does_not_confirm_breach`, `test_reclaim_window_excludes_the_breach_candle_and_confirms_within_three_bars`, `test_reclaim_not_confirmed_within_three_bars_allows_genuine_invalidation`, `test_displacement_after_reclaim_requires_fast_or_strong_fast_leg`, `test_reclaim_without_displacement_is_not_false_invalidation`, `test_false_invalidation_requires_the_complete_three_event_sequence`, `test_sustained_breach_requires_two_of_three_reclaim_window_closes_beyond_tolerance`, `test_genuine_invalidation_is_final_and_never_reactivated`, `test_failed_reclaim_starts_a_new_independent_breach_event`, `test_repeated_tap_classification_counts_distinct_interactions`, `test_repeated_tap_does_not_automatically_degrade_the_poi`, `test_freshness_transitions_from_fresh_to_interacted_after_qualifying_touch`, `test_poi_age_fields_are_descriptive_only_and_never_expire_the_poi` |
| `test_poi_overlap_merge_and_precedence.py` | 9 | `test_overlapping_zones_are_detected_via_strict_interval_intersection`, `test_boundary_touching_zones_are_not_classified_as_overlapping`, `test_containment_is_classified_separately_from_overlap`, `test_point_poi_overlaps_interval_when_price_is_inside_or_on_boundary`, `test_distinct_point_pois_do_not_overlap`, `test_same_poi_type_cross_timeframe_overlap_merges_into_the_stronger_timeframe`, `test_cross_poi_type_or_opposing_direction_overlap_is_reported_but_never_merged`, `test_merged_child_poi_remains_independently_observable`, `test_overlap_relationships_are_not_transitively_inferred` |
| `test_poi_analyzer_api.py` | 11 | `test_analyze_pois_returns_empty_aggregate_for_empty_input`, `test_analyze_pois_rejects_mixed_symbol_input`, `test_analyze_pois_rejects_duplicate_or_unsorted_timeframe_input`, `test_analyze_pois_rejects_measurement_candle_count_mismatch`, `test_poi_timeframe_input_has_no_structure_analysis_field`, `test_analyze_pois_rejects_missing_source_record`, `test_unconfirmed_candidate_is_not_exposed_as_poi_observation`, `test_public_poi_observation_exists_only_after_confirmation`, `test_poi_outputs_use_engineering_provisional_evidence`, `test_analyze_pois_disabled_poi_type_is_never_detected`, `test_analyze_pois_is_deterministic_across_repeated_calls` |
| `test_poi_batch_replay_equivalence.py` | 6 | `test_batch_and_replay_produce_identical_poi_observations_for_the_same_prefix`, `test_batch_and_replay_produce_identical_lifecycle_transitions_for_the_same_prefix`, `test_unchanged_poi_observations_retain_the_same_record_id_across_growing_prefixes`, `test_current_poi_state_fingerprint_changes_only_when_public_content_changes`, `test_merge_decisions_are_stable_across_growing_prefixes`, `test_poi_fingerprint_serializer_matches_domain_and_structure_serializers` |
| `test_poi_exports.py` | 5 | `test_poi_exports_import_successfully`, `test_poi_exports_exact_twenty_three_name_surface`, `test_poi_contracts_expose_no_btmm_entry_trade_or_structure_source_fields`, `test_poi_type_enum_contains_no_deferred_or_placeholder_members`, `test_poi_package_never_imports_btmm_or_execution_modules` |

No test class; no generated test; no helper function beginning with `test_`; no `skip`/`xfail`; no vacuous assertion. **Mandatory coverage confirmed present, including every item added by the focused audit's correction:** each implementable `PoiType` (candidate/zone/availability), FVG strict geometry, Order Block source candle, no mandatory structural-context gate (documented, not silently assumed), approved candlestick patterns, Support/Resistance reference, Equal-Level detection-only (no lifecycle), no Trendline defer-vs-implement test needed (Trendline has no `PoiType` at all, verified via `test_poi_type_enum_contains_no_deferred_or_placeholder_members`), volume-family explicit Option B proxy usage, proxy metrics internal-only, `StructureAnalysis` absence from `PoiTimeframeInput`, unconfirmed candidate never public, public observation exists only after confirmation, exact UTC day/ISO-week/UTC-month period boundaries, weekend/holiday empty-period skipping, current-period stable identity and changing fingerprint, previous-period fixed content, zero-height point-inside-interval overlap (boundary-inclusive), distinct point zones never overlapping, no lifecycle transitions for period levels, no lifecycle transitions for equal levels, breach candle excluded from the reclaim-window count, exact three-bar reclaim window, invalidation finality, `strong_poi_timeframes` absence, exact corrected 23-name export surface, no structure-source-id field anywhere, candidate/confirmation availability, strong-timeframe precedence, overlap, containment, transitive-non-inference, opposing-direction non-relationship, breach/reclaim/invalidation/false-invalidation/sustained-breach, repeated tap, stable identity, changed-content fingerprint, merged identity, replay equivalence, static BTMM/entry/trade/structure-source absence.

### 35AJ. Public Exports — Corrected Recount: 23, Not 24

**The focused audit found the original 24-export claim's own category arithmetic (10 enums + 6 contracts/configuration + 6 errors + 1 API = 23) never actually summed to 24 — the discrepancy was `PoiTimeframeInput`, an input bundle miscategorized outside all four named categories. Corrected by (a) removing `PoiValidityStatus` (§35D/§35T — `PoiValidityStatus` no longer exists at all) and (b) explicitly classifying `PoiTimeframeInput` as part of the public API surface (a caller must import it to construct a valid call to `analyze_pois()`, even though it is a `NamedTuple`, not a `ContractModel`). Recounted from the exact ordered list below, category by category:**

```
 1. PoiFamily                                — enum
 2. PoiDirection                              — enum
 3. PoiType                                   — enum
 4. PoiStrengthTier                           — enum
 5. PoiLifecycleStatus                        — enum
 6. PoiLifecycleTransitionType                — enum
 7. PoiFreshnessStatus                        — enum
 8. PoiTapClassification                      — enum
 9. PoiOverlapRelationshipType                — enum
10. PoiObservation                            — contract
11. PoiLifecycleTransition                    — contract
12. PoiOverlapRelationship                    — contract
13. CurrentPoiState                           — contract
14. PoiAnalysis                                — contract
15. PoiConfiguration                          — configuration
16. PoiTimeframeInput                         — API (required to call analyze_pois())
17. InvalidPoiConfigurationError              — error
18. DuplicatePoiTimeframeInputError           — error
19. UnsortedPoiTimeframeInputError            — error
20. InputPrefixMismatchError                  — error
21. MissingSourceRecordError                  — error
22. ImpossiblePoiLifecycleTransitionError     — error
23. analyze_pois                              — API
```

**Category totals, verified: 9 enums + 5 contracts + 1 configuration + 6 errors + 2 API = 23. No duplicated number, no omitted item.** This corrected total of **23** (not 24, not 22, not 25) is used consistently across all four documentation files.

**No `domain`/`structure`/`market_data` re-exports** (the 4 reused errors and `DerivedOutputIdentityProvider` are imported directly from `btmm_ai_scanner.domain` by callers, identical discipline to `structure/__init__.py`'s own precedent — and `structure` is not a dependency of this milestone at all, §35AH). **Not exported:** internal `*Candidate` `NamedTuple`s, the locally-duplicated canonical-fingerprint/identity-resolver helpers, per-family detector functions (only the single `analyze_pois()` entry point is public, per Part 29), merge-graph helpers, serializer helpers, test fixtures, and the removed `PoiValidityStatus`.

### 35AK. Complexity and Performance

Deterministic; per-timeframe candidate detection is a single forward linear scan per detector family (`O(candles)` per family per timeframe, not quadratic); overlap detection across `N` simultaneously-active observations is `O(N log N)` via interval sorting (Part 40's guidance), not `O(N^2)`; merge resolution is a single pass over sorted, pre-ranked candidates; no hidden cache; no global state; no wall clock; no concurrency requirement. Repeated-prefix, full-session, multi-timeframe replay analysis (§35AE) may be provisionally superlinear across a complete session (recomputing `PoiAnalysis` from scratch at every global availability group, across every timeframe), documented as accepted and non-production, identical in kind to `1B-H`/`1B-I`'s own twice-accepted precedent.

### 35AL. Explicit Exclusions

BTMM manipulation lifecycle (the 5-state/6-stage/10-gate state machine, `knowledge/btmm/BTMM_STATE_MACHINE.md`); accumulation/distribution session model; entry signals; stop loss; take profit; risk sizing; trade management; signal confidence; visualization; TradingView rendering; Telegram alerts; news filtering; backtesting statistics; paper trading; broker connectivity; MT5/MT4; AI inference; model training; production approval. Also explicitly excluded from *this* milestone specifically (deferred to a future, separate, narrowly-scoped task, not silently invented here): Trendline-as-POI zone geometry and specialized lifecycle (`P0G-B005`); Equal-High/Low SWEPT/BROKEN sweep lifecycle (`P0G-B004`, beyond the already-approved detection-only exposure); POI freshness/mitigation depth beyond the already-approved observational-only `FRESH`/`INTERACTED` model; POI expiration by age; repeated-tap statistical degradation (`P0G-B008`); the Order-Block/Engulfing "origin vs. middle of an existing move" automated structural gate; empirical calibration and out-of-sample validation of every threshold reused in this milestone.

### 35AM. Baseline, Quality Gates, and Stop Conditions

**Execution baseline / current HEAD and `origin/main`:** `a66225c52fb12ca0bca7761922a6b3bfdb48524c`. Python `3.12.13`; `uv` `0.11.30`; Pydantic `2.13.4`. Full pytest-collected tests: `458`. Original baseline suite: `34 passed`. Existing top-level test functions: `380`. Existing `poi`-adjacent exports: none (no `poi/` package exists). Inventory: `113` rows. No dependency change expected.

Future implementation must pass, unmodified in procedure from every prior milestone: `uv lock --check`; `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy src tests`; `uv run pytest -q` (expect `578` = `458` + `120`, or an exact, explained parametrize-driven discrepancy exactly as documented for every prior milestone); `uv run pytest -q tests/test_import_smoke.py tests/test_config_precedence.py` (expect `34 passed`).

Mandatory stop conditions (unchanged from every prior milestone's discipline): stop and report if any quality gate fails and cannot be fixed by a genuine, disclosed correction; stop if the approved 35-path scope would need to grow; stop if a 19th source file, a 17th test file, or a 121st test function is discovered necessary mid-implementation — report and request a scope amendment rather than silently expanding.

### 35AN. Author Decisions Required — Corrected

**Corrected by the consolidated correction pass following the focused architectural audit.** Every numbered item below requires an explicit author decision before implementation may begin — none is implemented, committed, or authorized by this section alone. Items marked **(new)** were added by the correction pass; all others are carried over, corrected where the audit found an error.

1. The identifier `1B-J-POI` and title "POI Detection and Lifecycle Foundation" (§35A) — corrected justification: exactly 18, not 32 or 30, implementable types are lifecycle-eligible.
2. The primary domain boundary — **corrected: `StructureAnalysis` removed entirely from the boundary and from every public input** (§35B).
3. The 32-implementable/4-deferred/0-blocked readiness gate outcome, and specifically the two deferral rationales — Trendline (no approved zone geometry) and Swing High/Low (duplicate of an existing contract) (§35C).
4. **The corrected lifecycle-eligibility split: exactly 18 `FULL` (10 volume + 6 price-action + Support + Resistance) and exactly 14 `NOT_APPLICABLE` (Equal Highs, Equal Lows, all 12 period-level types)** (§35C/§35D/§35V) — **(new)**, replacing every prior "30" or "32" lifecycle-eligible count.
5. The `PoiFamily`/`PoiDirection`/`PoiType` taxonomy, including the decision to create no `NEUTRAL` direction member and no placeholder `PoiType` member for any deferred specification (§35D) — now three separated axes, not four (`PoiValidityStatus` removed).
6. **Removal of `PoiValidityStatus` and `validity_status` entirely; the corrected candidate/confirmation model (internal, unexported candidates; a `PoiObservation`'s existence is itself the confirmation signal)** (§35D/§35T) — **(new)**.
7. The exact, corrected 23-field `PoiObservation` contract and field order (2 fields removed: `validity_status`, `source_structure_record_ids`), including the `representative_price`/zero-height-point-zone treatment for the 12 period levels and the disclosed content-evolving-snapshot exception for the 6 "Current" period-level types (§35E).
8. The exact per-family semantic keys (corrected for period levels to include both period start and end in the key) and the reuse of `DerivedOutputIdentityProvider` with 3 new `DerivedOutputType` members (§35F).
9. The chosen fingerprint strategy — Option C, a third disclosed duplicate implementation with a required three-way cross-package equivalence test (§35G).
10. The input model (Option B, per-timeframe input tuples) — **corrected: `structure_analysis` field removed from `PoiTimeframeInput`; structure-related validation checks removed** — and the exact validation/error list (§35H).
11. The timeframe-strength total order, **the explicit statement that this order is not a resolution of `P0G-B014` and never labels H1/M15 as strong/weak**, and the removal of the unused `strong_poi_timeframes` configuration field (§35I) — **(new: removal + explicit P0G-B014 separation)**.
12. The FVG architecture, including no minimum-width threshold (RECON-D3 reused) and no structural-context gate (§35J).
13. The Order Block architecture, including the explicit, disclosed absence of an automated "origin vs. middle" gate (§35K).
14. The candlestick-pattern architecture for Engulfing/Hammer/Shooting-Star/Morning-Star/Evening-Star, reusing GROUP3-D1 through GROUP3-D9 exactly (§35L).
15. The Buy-to-Sell/Sell-to-Buy and Base Rally/Drop and Pressure Wick architecture, **with explicit Option B (price-action/displacement proxy) labeling for all 10 volume-family types, and internal-only, never-exported placement for the four proxy metric fields** (§35M) — **(new: Option B label + internal-only placement, resolving a previously dangling cross-reference)**.
16. The Support/Resistance reference-POI architecture — pure reference onto `domain.SupportResistanceZone`, no re-detection, RECON-D4's coexistence rule preserved, `PoiLifecycleStatus = FULL` (§35N).
17. The Trendline deferral itself (§35O) — a decision, not merely a finding.
18. The Equal-Level reference architecture — explicitly a **liquidity-reference POI**, not an entry signal, detection-only, `PoiLifecycleStatus = NOT_APPLICABLE` permanently, no sweep lifecycle invented, no implication of BTMM manipulation validity (§35P) — **(new: explicit liquidity-reference/non-entry-signal clarification)**.
19. The volume-data finding and explicit Option B selection — no volume-based POI is blocked by missing real/tick volume; price-action proxies are primary evidence throughout (§35Q).
20. **The exact, fully-specified UTC period-window policy** — day `[00:00, next-day 00:00)`, ISO week `[Mon 00:00, next-Mon 00:00)`, calendar month `[1st 00:00, next-1st 00:00)`, all UTC, no DST, no broker-local timezone, weekend/holiday windows simply empty, previous-period resolution skips empty windows, current-period content evolves under a stable identity — **(new, replacing the prior unresolved calendar-window gap)**, labeled `ENGINEERING-PROVISIONAL`, not broker-session-calibrated, not production-approved, **now author-approved (§35AP, item 9)** (§35R).
21. The explicit non-gating (indeed, total absence) of any structural input for every implementable POI type (§35S) — corrected from "optional, non-gating" to "removed entirely."
22. The confirmation model and its corrected two-way separation from candidate existence (no third "validity" axis) (§35T).
23. The exact zero-height point-zone overlap/containment rules — a point overlaps an interval when `bottom <= P <= top` (boundary-inclusive); two points overlap only when exactly equal; mitigation/fill concepts never apply to point zones (§35X) — **(new)**.
24. The exact breach/reclaim/displacement/false-invalidation/sustained-breach/genuine-invalidation/failed-reclaim/repeated-tap rules, reused verbatim from the already-approved Ambiguity 15 standard (with the breach-candle-excluded-from-reclaim-window-count nuance now explicitly restated), plus the already-approved observational-only freshness/age model, applicable to exactly 18 types (§35V).
25. The decision to exclude `EXPIRED` from every public enum pending a future, separate expiration-model decision (§35W).
26. The exact overlap/merge/precedence algorithm, including the three-case overlap test (non-zero/non-zero, point/interval, point/point), the decision that cross-`poi_type` and same-timeframe overlap is reported (`PoiOverlapRelationship`) but never merged, and that bullish/bearish overlapping zones never create a relationship at all (§35X).
27. The decision that single-region/limit rules are display-layer concerns, never analytical ones, in this milestone (§35Y).
28. The four-contract output model (`PoiObservation`, `PoiLifecycleTransition`, `PoiOverlapRelationship`, `CurrentPoiState`) plus the `PoiAnalysis` aggregate and exact field orders, with no `MergedPoi` fifth contract, and the corrected 21-field `CurrentPoiState` (§35Z).
29. The exact `analyze_pois()` public API signature and behavior table, with `structure_analysis` removed (§35AA).
30. The exact 10-error vocabulary — 4 reused unmodified, 6 new, with `InputPrefixMismatchError`'s scope narrowed to measurement-only mismatch (§35AB).
31. The single-value `ENGINEERING_PROVISIONAL` evidence policy (§35AC).
32. The exact no-look-ahead availability rules and same-availability-group phase ordering (§35AD).
33. The multi-timeframe replay-equivalence procedure, with the `StructureAnalysis` recomputation step removed (§35AE).
34. The exact deterministic ordering keys for all four output types (§35AF).
35. The exact `PoiConfiguration` fields — **corrected: `strong_poi_timeframes` removed**, every remaining field reusing an already-approved numeric value, none newly invented (§35AG).
36. The exact 35-path file scope with creation order 113-146, **with both the new-path split (18 source/16 test) and the affected-path split (19 source/16 test) stated explicitly and never conflated**, and the corrected `structure`-free dependency direction (§35AH).
37. The exact, redistributed 120 new top-level test names, counts, and per-file distribution (7+8+8+8+8+6+5+5+5+7+8+14+9+11+6+5) (§35AI).
38. **The exact, recounted 23-name `poi/__init__.py` export list and order (corrected from the internally-inconsistent original claim of 24), with no `domain`/`structure` re-exports** (§35AJ).
39. The performance/determinism policy, including the accepted provisional superlinear full-session multi-timeframe replay cost (§35AK).
40. The explicit exclusion list, including the items deferred from this milestone specifically (not merely the standing project-wide exclusions) (§35AL).

### 35AO. Status and Next Action

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.** All 40 items listed in §35AN are approved without modification — see §35AP. All 35 approved paths have since been implemented exactly as approved, with one genuine pre-commit correction (a lifecycle-status-reset defect in `poi/lifecycle.py`) — see §35AQ. **Every blocking and precision finding from the focused architectural audit was resolved in one consolidated documentation-only correction pass:** the lifecycle-eligible count is corrected to 18 everywhere; `StructureAnalysis` is removed from the public input; `PoiValidityStatus` is removed entirely; the UTC period-window policy is fully specified; zero-height point-zone overlap rules are exact; the dangling volume-proxy field-placement cross-reference is resolved; the unused `strong_poi_timeframes` field is removed; the public export count is corrected to 23; the reclaim-window bar-1 exclusion is restated explicitly; the 120-test plan is redistributed to cover every new requirement while remaining at exactly 120 tests across 16 files.

### 35AP. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected `1B-J-POI` POI Detection and Lifecycle Foundation architecture exactly as documented (§35A–§35AO), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

**Exact approved scope:** 35 total affected paths (34 new, 1 modified); 18 new source files; 16 new test files; 1 modified existing source file (`src/btmm_ai_scanner/domain/enums.py`, +3 `DerivedOutputType` members); new-path split 18 source/16 test; affected-path split 19 source/16 test; 120 new top-level test functions (500 combined with the existing 380); 23 public `poi/__init__.py` exports; inventory 113 → 147 under batch tag `1B-J-POI`, creation order 113–146; no dependency change; no lockfile change; no existing `market_data`/`domain` Protocol modification.

The author approved, without modification, all 27 numbered decision groups listed in the approval message: milestone identity and title (1); specification readiness — 32 implementable/4 deferred/0 blocked, with the exact four deferred specifications and no placeholder created for any of them (2); the exact 32-member implementable set (3); the exact 18 `FULL`/14 `NOT_APPLICABLE` lifecycle-applicability split (4); the corrected input boundary with `StructureAnalysis` entirely absent (5); the candidate/confirmation model with no intermediate public state (6); the complete removal of `PoiValidityStatus`/`validity_status` (7); the explicit Option B volume-family policy with internal-only proxy metrics (8); the exact UTC day/ISO-week/calendar-month period-window policy (9); the current-period stable-identity, content-evolving snapshot model as the sole disclosed immutability exception (10); the exact point-zone geometry and overlap/containment rules (11); the exact FVG policy (12); the exact Order Block policy, including the disclosed absence of an automated origin-versus-middle gate (13); the exact six-pattern candlestick POI policy (14); the exact Support/Resistance reference policy (15); the exact Equal-Level liquidity-reference policy (16); the exact `Timeframe` set and duration-rank merge-precedence policy, explicitly separate from `P0G-B014`, with `strong_poi_timeframes` removed (17); the exact overlap/merge algorithm with no transitive graph closure (18); the exact breach/reclaim/invalidation lifecycle for the 18 eligible types, including the breach-candle-excluded-from-reclaim-count rule (19); the exact no-look-ahead availability-group processing order (20); the exact identity/fingerprint strategy, including the mandatory three-way equivalence test (21); the uniform `ENGINEERING_PROVISIONAL` evidence policy (22); the exact corrected 23-field `PoiObservation` and `CurrentPoiState` contracts (23); the exact corrected 23-name export list (24); the exact corrected 120-test plan and per-file distribution (25); the exact 35-path file scope with creation order 113–146 (26); and the complete exclusion list (27).

**This approval authorizes exactly one complete implementation cycle** covering all 35 approved paths at once (no per-file decision groups), followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started — this remains a documentation-only approval.**

### 35AQ. Implementation, Final Audit, and Closure Record

**Status: `AUTHOR-APPROVED`, `IMPLEMENTED`, `VERIFIED`, `ARCHITECTURALLY AUDITED`, `COMMITTED`, `PUSHED`, `CLOSED`, `NOT PRODUCTION-APPROVED`.**

**Implementation commit:** `ebc55e0bdbbef7b7f528d874107daa2d75a5628a`. **Commit message:** "Implement 1B-J-POI foundation". **Push:** `02750b2..ebc55e0 main -> main`, succeeded to `origin/main`. Preflight baseline: `02750b2904638bc9d2cc77f792306c53cf065cfa` (the inventory-lock commit).

**Implemented scope:** exactly 35 committed paths — 18 new source files (`poi/__init__.py`, `poi/enums.py`, `poi/configuration.py`, `poi/observation.py`, `poi/lifecycle.py`, `poi/current_state.py`, `poi/order_blocks.py`, `poi/fair_value_gaps.py`, `poi/reversal_candles.py`, `poi/bases.py`, `poi/pressure_wicks.py`, `poi/engulfing.py`, `poi/single_candle_reversals.py`, `poi/three_candle_stars.py`, `poi/reference_zones.py`, `poi/period_levels.py`, `poi/overlap.py`, `poi/analyzer.py`), 16 new test files, 1 modified existing path (`domain/enums.py`, +3 `DerivedOutputType` members — `POI_OBSERVATION`, `POI_LIFECYCLE_TRANSITION`, `CURRENT_POI_STATE` — verified byte-exact against the approved 3-member extension via `git diff`). New-path split 18 source/16 test; affected-path split 19 source/16 test; new/modified split 34/1. Insertions/deletions: 5,915 insertions, 0 deletions. No documentation included in the implementation commit. No dependency or lockfile change. No `market_data` or `structure` Protocol/module modification.

**Final architectural audit verdict: `B — PASS WITH NON-BLOCKING FINDINGS — READY TO COMMIT`.** One genuine defect was found and corrected before the implementation commit:

1. **Lifecycle-status-reset defect (`poi/lifecycle.py`):** the per-POI breach/reclaim walk unconditionally reset the tracked `status` variable to `NO_BREACH` immediately after resolving a breach event (whether the event ended in `RECLAIM_WITHOUT_DISPLACEMENT`, `FALSE_INVALIDATION_CONFIRMED`, or `RECLAIM_FAILED`), discarding the true terminal-for-that-event status the moment no further candle existed to overwrite it. Corrected by removing the unconditional reset in both resolution branches, so `CurrentPoiState.poi_lifecycle_status` correctly reflects the last real event when no later candle changes it, while still permitting a later, independent breach event to overwrite it exactly as approved. The correction stayed inside the approved 35-path scope; changed no architecture decision, no public contract, no test count, no export count, and no dependency or Protocol.

**One disclosed non-blocking finding, not requiring correction:** the approved no-look-ahead behavior (§35AD) is implemented as availability-time-driven correctness by construction — every output's `availability_time_utc` is computed as the max of its own required source facts' availability, exactly as specified — rather than as a literal procedural six-phase per-availability-group loop. This mirrors the precedent already accepted for `domain/analyzer.py` and `structure/analyzer.py`, neither of which implements a literal phase-stepped event-timeline walk either; their own no-look-ahead guarantee likewise rests on correct per-output availability computation, proven via batch/replay equivalence rather than simulated time-stepping. Replay equivalence, determinism, same-availability-group activation immunity (a newly confirmed POI cannot be breached by a candle sharing its own confirming instant, since the breach walk begins strictly after `availability_time_utc`), and no-future-input behavior are all directly verified by the required test suite. This finding did not alter the final audit verdict and did not require a second correction cycle. It remains a disclosed, non-production engineering simplification, not a silent gap.

No other defect was found. Every other approved control was audited and confirmed exactly as designed: the exact 32-member `PoiType` enum with no Trendline/Swing-High/Swing-Low placeholder (§35C/§35D); the exact 18 `FULL`/14 `NOT_APPLICABLE` lifecycle-eligibility partition, verified disjoint and exhaustive over all 32 implementable types (§35C/§35D/§35V); the candidate/confirmation separation, with every detector's internal `*Candidate` `NamedTuple` private and unexported, and a public `PoiObservation` created only once its family's exact confirmation rule passes (§35T); the complete absence of `PoiValidityStatus`/`validity_status`/`FORMING` anywhere in the corrected architecture (§35D/§35U); the explicit Option B volume-family proxy semantics, verified functional even with `volume_kind = UNKNOWN`/`volume = None` (§35Q); the four internal-only proxy-metric fields absent from every public contract and fingerprint (§35Q/§35AJ); the strict three-candle FVG geometry with no minimum-width threshold and third-candle-close availability (§35J); the exact two-candle Order Block relationship with no BOS/CHoCH prerequisite and no automated origin-versus-middle gate (§35K); the six approved candlestick-pattern POIs (§35L); Support/Resistance/Equal-Highs/Equal-Lows reference POIs consuming, never re-deriving, their source `domain` outputs (§35N/§35P); the exact UTC day/ISO-week/calendar-month period-window policy, empty-window skipping, and the six-type content-evolving current-period snapshot exception (§35E/§35R); the exact three-case zero-height point-zone overlap geometry (§35X); the direct, non-transitive, duration-rank cross-timeframe merge algorithm (§35I/§35X); the exact breach/reclaim/displacement/invalidation state machine for the 18 eligible types, including the breach-candle-excluded-from-reclaim-window-count rule and permanent, final `GENUINE_INVALIDATION_CONFIRMED` (§35V); the locally-duplicated canonical-fingerprint/identity-resolver implementation, verified byte-identical to both `domain/analyzer.py`'s and `structure/analyzer.py`'s implementations via a dedicated three-way cross-package equivalence test (§35G/§35AI); the single-value `ENGINEERING_PROVISIONAL` evidence policy on every output (§35AC); the exact 10-error vocabulary, 4 reused unmodified (§35AB); the exact corrected 23-field `PoiObservation` and 21-field `CurrentPoiState` contracts (§35E/§35Z); replay-prefix equivalence, including stable `record_id`s across growing prefixes and fingerprint-changes-only-with-content for both fixed-source and current-period-evolving observations (§35AE); and the exact corrected 23-name `poi/__init__.py` export surface with no `domain`/`structure` re-exports (§35AJ).

**Verification results:** full suite **578 passed**; original baseline subset (`tests/test_import_smoke.py` + `tests/test_config_precedence.py`) **34 passed**; new top-level test functions **120** (7+8+8+8+8+6+5+5+5+7+8+14+9+11+6+5 across the 16 new files, exact approved distribution); existing top-level test functions **380**; combined top-level test functions **500** (AST-verified); full pytest-collected test total **578** (458 existing + 120 new — no `@pytest.mark.parametrize` used by any of the 16 new files, so the combined and collected totals match exactly); public exports **23** (exact approved order, all import successfully); `uv lock --check` passes; `ruff format --check .` passes; `ruff check .` passes; `mypy src tests` passes with no issues across 123 source/test files.

**Inventory:** before **113**, new rows **34**, final **147**, batch tag `1B-J-POI`, creation order **113–146** — unchanged by this closure. No inventory row was added, removed, renamed, or renumbered beyond what was already recorded at approval and lock time. The one modified existing path (`domain/enums.py`, row 82) keeps its original creation order (82), batch tag (`1B-H-MEASUREMENTS`), and path — only its wording-level annotation changed, exactly as recorded at approval time.

**No dependency change. No `market_data` or `structure` Protocol change. No production approval granted by this record.** The milestone remains `NOT PRODUCTION-APPROVED`.

**Next controlled action:** define the **BTMM Manipulation Lifecycle Foundation** (proposed identifier `1B-K-BTMM`, proposed title "BTMM Manipulation Lifecycle Foundation"), using the completed market-data, measurement, structure-state, and POI detection and lifecycle foundations. This next architecture definition should cover, without implementing yet: POI interaction as a required boundary; manipulation lifecycle states; accumulation and distribution context; liquidity before, within, and after POI interaction; approach to POI; first contact; overshoot; breach; reclaim; rejection; reaction strength; market speed and displacement; pressure behavior; equal-level liquidity interaction; protected and weak structure references; BOS and CHoCH interaction; buy-to-sell manipulation; sell-to-buy manipulation; lifecycle inheritance; conditional lifecycle reconciliation; POI breach/reclaim/invalidation inheritance; deterministic no-look-ahead transition ordering; historical replay equivalence; and the explicit separation of POI validity, BTMM-pattern validity, entry validity, and trade outcome. That milestone must explicitly exclude live entry execution, stop-loss placement, take-profit placement, position sizing, trade management, visualization, Telegram alerts, backtesting statistics, broker connectivity, MT5/MT4, AI inference, and production approval. That milestone requires one compact architecture definition, one focused audit, at most one consolidated correction, explicit author approval, and one complete implementation cycle — none of which is started by this record.

## 36. BTMM Manipulation Lifecycle Foundation — Architecture (Corrected, Architect-Recommended)

**Status (historical — superseded by author approval, §36AT): `ARCHITECT-RECOMMENDED`, `AUTHOR-DECISION REQUIRED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** **Current status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** This is the corrected `1B-K-BTMM` architecture, resolving every blocking and non-blocking finding from the focused architectural audit (and the subsequent narrow consistency review) in one consolidated pass, now explicitly author-approved. It supersedes the original §36 draft in full — the prior draft's content is not preserved separately, since this correction is itself the complete, current statement of the approved architecture. Nothing in this section is implemented, staged, committed, or pushed by this section.

### 36A. Milestone Identity, Scope Honesty, and Title

**Batch identifier: `1B-K-BTMM`.** **Title: BTMM Manipulation Lifecycle Foundation.** Unlike the original draft, `BTMM_CONFIRMED` is now genuinely reachable by this milestone's own deterministic code — not automatically, but through an explicit, approved, caller-supplied reviewed-evidence channel (§36G2/§36S). "Foundation" remains the correct word: this milestone establishes the complete lifecycle scaffolding, every automatable gate, and the exact contract through which reviewed evidence enters the system: it does not itself perform automatic context detection, automatic session-calendar lookup, or an invented Volume Pillar formula.

**This milestone does not implement:** trade entries, entry validity, stop loss, take profit, position sizing, risk-to-reward, trade management, trade outcome, signal confidence, or AI scoring — exactly as `BTMM_STATE_MACHINE.md`'s "Entry/Risk Separation" section requires.

**Initial status (historical — superseded by author approval, §36AT):** `ARCHITECT-RECOMMENDED`, `AUTHOR-DECISION REQUIRED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`. **Current status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.**

### 36B. Primary Domain Boundary and Concept Separation (unchanged from original draft, reconfirmed)

**Corrected deterministic boundary:**

```
canonical multi-timeframe NormalizedCandle inputs (M1/M5/M15 only)
  + MarketMeasurementAnalysis inputs (per timeframe)
  + PoiAnalysis (single, cross-timeframe aggregate)
  + BtmmReviewedEvidence inputs (caller-supplied, optional per source POI, §36G2)
  -> BTMM-eligible POI selection (§36J, unchanged)
  -> BTMM_CANDIDATE creation (§36I, corrected)
  -> deterministic gate evaluation (Accuracy, Reaction, Reaction-Speed, Formation-Timeframe)
  -> reviewed-evidence gate evaluation (Context x3, full Liquidity, Volume Pillar) where supplied
  -> BtmmLifecycleTransition records
  -> CurrentBtmmState snapshot per setup
  -> BtmmAnalysis
```

`StructureAnalysis` remains excluded from this milestone's input entirely (§36F, unchanged, reconfirmed by direct grep of the approved knowledge base during the audit — zero occurrences of BOS/CHoCH/protected/weak-swing as a mandatory or optional gate anywhere).

**Five separated concepts, never conflated, unchanged:** POI validity (resolved by `1B-J-POI`); POI lifecycle status (resolved by `1B-J-POI`); BTMM setup validity (this milestone, now including genuine `BTMM_CONFIRMED` reachability); entry validity (out of scope); trade outcome (out of scope).

### 36C. No Approved BTMM-Level Pattern Taxonomy Beyond Direction (unchanged, reconfirmed)

No approved "Buy-to-Sell manipulation"/"Sell-to-Buy manipulation" pattern concept exists distinct from generic `BtmmDirection` (`BULLISH_BTMM`/`BEARISH_BTMM`). `source_poi_type` + `btmm_direction` together uniquely distinguish a `BUY_TO_SELL_CANDLE`-sourced setup from any other; no `BtmmPatternType` enum is created. This finding survived the audit unchanged.

### 36D. Ten Mandatory Gates — Corrected Reachability

The original draft found 5 gates fully deterministic and 5 gates permanently blocked. **Corrected finding:** all 10 gates are now reachable — 5 automatically (deterministic), and 5 through an explicit, approved, caller-supplied reviewed-evidence channel that was missing from the original draft (audit Finding B3). No automatic detector is invented for any of the 5 reviewed gates; the milestone only accepts already-reviewed facts as typed input, exactly as `BTMM_STATE_MACHINE.md`'s "Phase 0G Input-Source Policy" explicitly permits (`context_input_source = MANUAL_EXPERT_LABEL`, `liquidity_event_source = MANUAL_EXPERT_LABEL`, and the Volume Pillar Gate's own "expert-labelled volume-switch evidence, or reviewed hybrid evidence" allowance).

| Gate | Reachability | Mechanism |
|---|---|---|
| POI Gate | Deterministic | Confirmed, available `PoiObservation` of a BTMM-eligible type |
| Market Direction Gate | Reviewed evidence | `BtmmReviewedEvidence.market_direction_status = ALIGNED` |
| Analytical Framework Gate | Reviewed evidence | `BtmmReviewedEvidence.analytical_framework_status = ALIGNED` |
| Active Session Gate | Reviewed evidence | `BtmmReviewedEvidence.session_status = ACTIVE` |
| Liquidity Gate (full) | Reviewed evidence | `BtmmReviewedEvidence.liquidity_evidence_status = PRESENT` (may itself be grounded in a reviewed `FALSE_INVALIDATION_CONFIRMED` event, or any other reviewed liquidity-event label) |
| Accuracy Gate | Deterministic | Ambiguity 8, exact wick geometry (§36K, unchanged) |
| Volume Pillar Gate | Reviewed evidence only (Option B, §36R corrected) | `BtmmReviewedEvidence.volume_pillar_status = SUPPORTS` |
| Reaction Gate | Deterministic, corrected timing | Ambiguity 9, resolved only at the 5th confirmed reaction candle (§36N, corrected) |
| Reaction Speed Gate | Deterministic | Reuses `measure_leg` over the exactly-defined reaction leg |
| Formation Timeframe Gate | Deterministic | Fixed M5/M15-vs-M1 rule |

**`BTMM_CONFIRMED` is reachable when all 10 rows above resolve simultaneously at `FINAL_GATE_EVALUATION`** (§36S). Missing reviewed evidence never silently passes a gate — an absent or non-`ALIGNED`/non-`ACTIVE`/non-`PRESENT`/non-`SUPPORTS` reviewed value leaves the corresponding gate unresolved (`BTMM_BLOCKED`) or, where the reviewed value is a definitive rejection (`MISALIGNED`, `INACTIVE`, `FAILS`), triggers the matching cancellation reason (§36H2).

### 36E. Accumulation and Distribution — Deferred (unchanged, reconfirmed)

Zero approved definition exists anywhere in the knowledge base for either term. No public enum, field, or output is created for either. Unaffected by this correction.

### 36F. Structural Context — Excluded (unchanged, reconfirmed)

`StructureAnalysis` remains excluded from the input model entirely; no approved rule anywhere makes BOS, CHoCH, or protected/weak swings a precondition for any BTMM concept, reconfirmed by direct grep during the audit.

### 36G. Input Model and Validation (corrected: adds reviewed evidence)

```
BtmmTimeframeInput:
    timeframe: Timeframe
    candles: tuple[NormalizedCandle, ...]
    measurement_analysis: MarketMeasurementAnalysis
```

(Unchanged from the original draft — no `StructureAnalysis` field, no `poi_analysis` field on the per-bundle input.)

**Validation, corrected to include reviewed evidence (all checks below raise the exact 6-error vocabulary of §36AF, broadening existing error triggers rather than adding new error classes):**

- One `InternalSymbol` across all bundles, the supplied `PoiAnalysis`, and every supplied `BtmmReviewedEvidence` record (`MixedSymbolAnalysisError`, reused).
- Canonical ascending timeframe-strength bundle order; duplicate timeframe rejection (`DuplicateBtmmTimeframeInputError`/`UnsortedBtmmTimeframeInputError`, unchanged).
- Per-bundle candle ordering/duplication (`DuplicateCandleRecordError`/`UnsortedCandleSequenceError`, reused, unchanged).
- `measurement_analysis` prefix consistency against its own bundle (`InputPrefixMismatchError`, unchanged trigger).
- Every `PoiObservation` referenced by `source_poi_record_id` (from `PoiAnalysis` or from `BtmmReviewedEvidence`) must exist in the supplied `poi_analysis.poi_observations` tuple (`MissingSourcePoiRecordError`, trigger broadened to cover reviewed-evidence references too).
- **New, corrected — reviewed-evidence-specific validation, folded into `InputPrefixMismatchError`'s existing trigger family rather than a new error class (keeping the error count at exactly 6 new/10 total):** at most one `BtmmReviewedEvidence` record per distinct `source_poi_record_id` in a single `analyze_btmm()` call (duplicate reviewed evidence for one source POI is rejected); each record's `symbol`/`timeframe` must match its referenced source POI's own `symbol`/`source_timeframe`; `availability_time_utc` must be timezone-aware UTC; `availability_time_utc` must not exceed the maximum availability of the visible input prefix (candles + measurement analysis + POI analysis supplied in the same call).
- Unsupported timeframe: any bundle whose `timeframe` is not in `{M1, M5, M15}` is rejected (unchanged).
- Empty bundle tuple / empty `poi_analysis` / empty `reviewed_evidence`: returns the empty `BtmmAnalysis` aggregate. **`reviewed_evidence = ()` is always valid** — an empty tuple means no reviewed evidence is available for any setup, and every reviewed gate simply stays unresolved; it is never treated as invalid input.
- No future source fact: every BTMM output's own `availability_time_utc` formula (§36AA) structurally prevents this, and is now extended to cover reviewed evidence explicitly (§36AA2).

### 36G2. Reviewed-Evidence Input Contract

**One frozen, immutable, caller-supplied input value object — not an engine-generated `DerivedOutput` — because the authoritative standard does not require engine-owned identity for a fact the caller itself originates and vouches for:**

```
BtmmReviewedEvidence:
    symbol: InternalSymbol
    timeframe: Timeframe
    source_poi_record_id: UUIDv7
    market_direction_status: BtmmContextAlignmentStatus
    analytical_framework_status: BtmmContextAlignmentStatus
    session_status: BtmmSessionStatus
    liquidity_evidence_status: BtmmLiquidityEvidenceStatus
    volume_pillar_status: BtmmVolumePillarStatus
    context_input_source: BtmmEvidenceSource
    liquidity_event_source: BtmmEvidenceSource
    volume_evidence_source: BtmmEvidenceSource
    availability_time_utc: datetime
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer
```

**Exactly 15 fields.** No `record_id`, `content_fingerprint`, `provenance_id`, or `evidence_classification` field — these are engine-owned `DerivedOutput` concerns (§36AC) that do not apply to a caller-supplied input fact; the authoritative standard nowhere requires this input itself to carry a derived identity. **`liquidity_evidence_status` is typed `BtmmLiquidityEvidenceStatus`, a dedicated new enum, not `BtmmGateStatus` — corrected in this pass; see §36H1 for the semantic analysis proving these are genuinely distinct concepts, not a mere arithmetic-count decision.**

**Permitted evidence-source values for caller-supplied fields (resolving audit Part 9):** `context_input_source` and `liquidity_event_source` must be one of `EXPERT_LABELLED`, `HYBRID_REVIEWED`, or `RULE_BASED_REVIEWED` — never `RULE_BASED` or `MODEL_PROPOSED`, since those two values denote automatically-generated, unreviewed evidence that this milestone's own analyzer (not a caller) produces internally (e.g., the `FALSE_INVALIDATION_CONFIRMED → LIQUIDITY_AFTER_POI/RULE_BASED` pathway of §36M). `volume_evidence_source` is likewise restricted to `EXPERT_LABELLED`/`HYBRID_REVIEWED` (no `RULE_BASED_REVIEWED` equivalent is defined for Volume Pillar by the approved standard, which only names "expert-labelled volume-switch evidence, or reviewed hybrid evidence"). A `BtmmReviewedEvidence` record carrying a disallowed source value is rejected as malformed input (folded into the same broadened `InputPrefixMismatchError` trigger).

**Caller-supplied reviewed evidence never changes the emitted output-level `EvidenceClassification` (§36AD)** — every `BtmmObservation`/`BtmmLifecycleTransition`/`CurrentBtmmState` this milestone emits still stores exactly `ENGINEERING_PROVISIONAL`, regardless of how much reviewed evidence contributed to it. The reviewed evidence's own source fields (`context_input_source`, `liquidity_event_source`, `volume_evidence_source`) are the correct, separate place to record provenance for the *input fact*; they are not empirical or production validation of the *resulting BTMM output*, and are surfaced read-through on `CurrentBtmmState` (§36W) precisely so this distinction stays visible and auditable.

**Validation and behavioral rules (resolving audit Part 5's exact requirements):**
- Frozen, immutable value object — same `ContractModel`-style base as every other contract in this project.
- One current reviewed-evidence snapshot per source POI per `analyze_btmm()` call — duplicates rejected (§36G).
- `symbol`/`timeframe` must match the referenced source POI exactly (§36G).
- The referenced `source_poi_record_id` must exist in the supplied `PoiAnalysis` (§36G).
- `availability_time_utc` must be timezone-aware UTC (§36G).
- Evidence is never used before its own `availability_time_utc`, and never before the source POI's own availability — enforced by the same-group processing model (§36AA2), not by upfront validation alone.
- Absent reviewed evidence for a given source POI means every reviewed-dependent gate (Context x3, full Liquidity, Volume Pillar) stays at its own `PENDING` value on `CurrentBtmmState` — absence never silently passes a gate.
- The caller may supply an empty `reviewed_evidence` tuple; this is always valid and results in every setup remaining `BTMM_FORMING`/`BTMM_BLOCKED` (never `BTMM_CONFIRMED`), matching the corrected structural behavior when no reviewer channel is used at all.

**No automatic expert-review process is invented.** `BtmmReviewedEvidence` is a pure, passive input contract — this milestone never generates, infers, or upgrades a reviewed-evidence record on its own; it only accepts what the caller supplies.

### 36H. BTMM Taxonomy (corrected — 15 enums)

Unchanged from the original draft: `BtmmDirection` (2), `BtmmInteractionClass` (9), `BtmmReactionClassification` (5), `BtmmLiquidityLocation` (6), `BtmmFormationStage` (6), `BtmmLifecycleStatus` (5), `BtmmBlockedReason` (4, disclosure corrected in §36H3), `BtmmContextAlignmentStatus` (4, values `PENDING`/`ALIGNED`/`MISALIGNED`/`UNKNOWN`, verified byte-for-byte against `BTMM_STATE_MACHINE.md` line 105-106 during the audit), `BtmmSessionStatus` (4, verified against line 107), `BtmmEvidenceSource` (5, unchanged).

**`BtmmGateStatus`** (`StrEnum`, 3 members): `PENDING`, `PASS`, `FAIL` — used for Accuracy, Reaction, Reaction-Speed, and Formation-Timeframe gate statuses only. **`liquidity_evidence_status` is no longer typed `BtmmGateStatus`** — see the new, dedicated `BtmmLiquidityEvidenceStatus` enum below and the semantic analysis in §36H1.

**Corrected `BtmmLifecycleTransitionType`** (`StrEnum`, **15 members**, resolving audit Findings B5): `ENTERED_FORMING`, `ACCURACY_GATE_CONFIRMED`, `INTERACTION_INELIGIBLE`, `REACTION_GATE_CONFIRMED`, `WEAK_REACTION`, `REACTION_SPEED_GATE_CONFIRMED`, `REACTION_SPEED_FAILED`, `BLOCKED`, `RESUMED_FORMING`, `CONFIRMED`, `POI_REJECTED`, `CONTEXT_REJECTED`, `SESSION_INACTIVE`, `VOLUME_PILLAR_FAILED`, `NO_LIQUIDITY_EVIDENCE`. The original draft's `FORMATION_TIMEFRAME_BLOCKED` and `PENDING_REVIEWED_EVIDENCE_BLOCKED` members are removed and replaced by the single generic `BLOCKED` member, matching `BTMM_STATE_MACHINE.md`'s own "the reason is preserved separately (`blocked_reason`)" design for the Blocked state — the same one-state-plus-separate-reason pattern already used for cancellation. `BlockedReason` for a given `BLOCKED` transition is now carried on the transition record itself (§36X, corrected field list), not inferred from the transition type name.

**Corrected `BtmmCancellationReason`** (`StrEnum`, **8 members**, resolving audit Finding B4 and the reviewed-evidence expansion): `POI_REJECTED`, `INTERACTION_INELIGIBLE`, `WEAK_REACTION`, `REACTION_SPEED_FAILED`, `CONTEXT_REJECTED`, `SESSION_INACTIVE`, `VOLUME_PILLAR_FAILED`, `NO_LIQUIDITY_EVIDENCE`. Now that Context/Session/Volume-Pillar/Liquidity gates are reachable via reviewed evidence (§36D), their corresponding *rejection* outcomes (`MISALIGNED`, `INACTIVE`, `FAILS`, window-closed-with-no-evidence) become reachable too, and are included. **`DIRECTIONAL_CONTINUATION` and `MANUAL_REVIEW_REJECTED` remain explicitly excluded and deferred — see §36H4 for the required, fully researched disposition of each.**

**`BtmmVolumePillarStatus`** (`StrEnum`, **5 members, new**, resolving audit Finding B2): `PENDING`, `SUPPORTS`, `FAILS`, `MISSING_DATA`, `UNRESOLVED` — the exact vocabulary from `BTMM_STATE_MACHINE.md` line 170, verified directly against source text. Used for `CurrentBtmmState.volume_pillar_status` and `BtmmReviewedEvidence.volume_pillar_status`. Only `SUPPORTS` satisfies the Volume Pillar confirmation gate; `FAILS` triggers `BTMM_CANCELLED`/`VOLUME_PILLAR_FAILED`; `PENDING`/`MISSING_DATA`/`UNRESOLVED` all leave the gate unresolved and, at `FINAL_GATE_EVALUATION`, park the setup `BTMM_BLOCKED`/`VOLUME_REVIEW_PENDING` — never silently passed, exactly matching `BTMM_STATE_MACHINE.md`'s own "Evidence unavailable or still awaiting review → BTMM_BLOCKED (never silently passed or cancelled)" rule.

**`BtmmLiquidityEvidenceStatus`** (`StrEnum`, **2 members, new**, resolving the narrow-correction audit's liquidity-semantics finding): `PENDING`, `PRESENT`. Used for both `BtmmReviewedEvidence.liquidity_evidence_status` (the caller-supplied input fact) and `CurrentBtmmState.liquidity_evidence_status` (the analyzer's own preserved field of the same name, per `BTMM_STATE_MACHINE.md`'s own "Preserved independently" field list). Only `PRESENT` satisfies the full Liquidity Gate at `FINAL_GATE_EVALUATION`; `PENDING` (the universal not-yet-resolved marker already reused across every other status enum in this architecture, not a value invented specifically for this field) covers every other case — no reviewed evidence supplied yet, or a supplied record that has not yet confirmed presence.

**15 enums total** (11 unchanged + 1 corrected member-count on 2 of them + 2 new: `BtmmVolumePillarStatus`, `BtmmLiquidityEvidenceStatus`).

#### 36H1. Liquidity-Evidence Semantics — Why a Dedicated Enum, Not `BtmmGateStatus` (corrected)

**This section previously described reusing `BtmmGateStatus` for `liquidity_evidence_status` as a disclosed simplification made "to keep the corrected export/enum count at exactly the values required by this correction" — that framing is withdrawn.** A full-text search of every authoritative BTMM source (`BTMM_STATE_MACHINE.md`, `BTMM_MASTER_SUMMARY.md`, `MEASUREMENT_STANDARDS.md`, `AMBIGUITIES_REQUIRING_AUTHOR_DECISION.md`) finds that `liquidity_evidence_status` is named exactly once with an exact value (`BTMM_STATE_MACHINE.md` line 135: "the gate requires `liquidity_evidence_status = PRESENT`") and is never given a complete enumerated value list anywhere — unlike the Volume Pillar Gate's own field (`volume_pillar_status`), which line 170 enumerates completely and explicitly as five named values (`PENDING`/`SUPPORTS`/`FAILS`/`MISSING_DATA`/`UNRESOLVED`). This asymmetry is not an oversight in the source material; it reflects a genuine semantic difference this architecture must respect rather than paper over:

1. **Does `BtmmGateStatus` have exactly the same semantic states as reviewed liquidity evidence? No.** `BtmmGateStatus` (`PENDING`/`PASS`/`FAIL`) encodes a *computed judgment* — something evaluated a rule and produced a pass/fail verdict. The approved Liquidity Gate text never describes a reviewer rendering a "this liquidity evidence fails/rejects the setup" verdict anywhere — the only reviewed-liquidity concept the text describes is *presence* of a reviewed liquidity event (`EXPERT_LABELLED`/`RULE_BASED_REVIEWED`/`HYBRID_REVIEWED`), not a judgment about whether liquidity behavior "supports" or "opposes" the setup the way Volume Pillar's `SUPPORTS`/`FAILS` explicitly does.
2. **Does it distinguish absent/present/supports/rejects/unresolved/missing?** No — the approved text never describes a "reviewed liquidity evidence rejects this setup" concept at all (unlike Volume Pillar's explicit `FAILS`, or Context's explicit `MISALIGNED`). The Liquidity Gate's only defined failure mode is *timing-based absence at window close* (`NO_LIQUIDITY_EVIDENCE`), which is a consequence the *analyzer* derives from the reaction window closing without ever having seen `PRESENT` — not a distinct value the reviewer supplies.
3. **Is "evidence `PRESENT`" semantically identical to "gate `PASS`"?** Functionally yes for the *final*, analyzer-computed field, but the field the approved standard names (`liquidity_evidence_status`) is described once, with one value (`PRESENT`), never as a three-way `PENDING`/`PASS`/`FAIL` judgment — reusing the generic 3-value enum would silently imply a "reviewer says FAIL" semantic the approved text never defines or authorizes, which is exactly the kind of undisclosed invention this project's governance forbids.
4. **Does reviewed evidence need a distinct status from the computed Liquidity Gate result?** The *type* does not need to be distinct in shape (both `BtmmReviewedEvidence.liquidity_evidence_status` and `CurrentBtmmState.liquidity_evidence_status` use the same new enum, mirroring `BTMM_STATE_MACHINE.md`'s own single named field), but the *vocabulary* must be distinct from `BtmmGateStatus`, since `BtmmGateStatus`'s `FAIL` value has no textual grounding for this field at all.

**Resolution: `BtmmLiquidityEvidenceStatus` (2 members: `PENDING`, `PRESENT`) is added**, using only the one literally attested value (`PRESENT`) plus the generic `PENDING` marker already reused throughout this architecture's other enums (`BtmmContextAlignmentStatus`, `BtmmSessionStatus`, `BtmmGateStatus`, `BtmmVolumePillarStatus` all already use `PENDING` as their own "not yet resolved" value) — no new member name is invented. This corrects the export count to **29** (§36AN) and the enum count to **15** — a genuine consequence of the semantic analysis above, not a target preserved for arithmetic convenience.

#### 36H2. Reviewed-Evidence-Driven Cancellation Semantics

- `market_direction_status = MISALIGNED` or `analytical_framework_status = MISALIGNED` (from a supplied `BtmmReviewedEvidence` record) → `BTMM_CANCELLED`, `cancellation_reason = CONTEXT_REJECTED` — verified against `BTMM_STATE_MACHINE.md` lines 117-118.
- `session_status = INACTIVE` → `BTMM_CANCELLED`, `cancellation_reason = SESSION_INACTIVE` — line 119.
- `volume_pillar_status = FAILS` → `BTMM_CANCELLED`, `cancellation_reason = VOLUME_PILLAR_FAILED` — line 178.
- The five-bar reaction window closes (Reaction Gate resolves) with `liquidity_evidence_status` still `PENDING` (no reviewed evidence supplied, or a supplied record that never reached `PRESENT`) → `BTMM_CANCELLED`, `cancellation_reason = NO_LIQUIDITY_EVIDENCE` — line 135 ("If the full reaction window closes with no reviewed evidence present, use `BTMM_CANCELLED`, `cancellation_reason = NO_LIQUIDITY_EVIDENCE`"). **This is the one reviewed-evidence-dependent cancellation with a deterministic *timing* trigger even absent reviewed evidence** — the others (`CONTEXT_REJECTED`/`SESSION_INACTIVE`/`VOLUME_PILLAR_FAILED`) only fire when reviewed evidence is actually supplied and is a definitive rejection; `liquidity_evidence_status` has no such definitive-rejection value at all (§36H1) — its *absence* at window close is itself the only failure mode, handled by timing alone, not by a rejection value the reviewer supplies.
- None of these four cancellations invalidates the underlying POI, consistent with every other cancellation reason in this architecture.

#### 36H3. Blocked-Reason Disclosure (resolving audit Finding N2)

`BtmmBlockedReason` (4 members, unchanged: `CONTEXT_UNKNOWN`, `LIQUIDITY_REVIEW_PENDING`, `VOLUME_REVIEW_PENDING`, `FORMATION_TIMEFRAME_NOT_CONFIRMED`) deliberately omits the approved example values `MISSING_ATR` and `MISSING_PRICE_METADATA`, now explicitly justified against the actual implemented upstream behavior: **`MISSING_ATR` never arises** because `measurements.atr.compute_atr_series`/`poi/lifecycle.py`'s own `_zone_reference_atr` helper (verified in source) always supplies a computable fallback (the candle's own high-low range) whenever a true ATR value is unavailable — there is no code path in this milestone's dependencies where ATR is simply absent. **`MISSING_PRICE_METADATA` never arises as a lifecycle-blocked state** because invalid instrument/price metadata is rejected at the input-validation boundary (raising a typed error such as `InputPrefixMismatchError`) before any `BtmmObservation`/`CurrentBtmmState` is ever created — it is a construction-time validation failure, not a business-level blocked state a confirmed setup could ever occupy.

#### 36H4. `DIRECTIONAL_CONTINUATION` — Researched Disposition (resolving audit Finding B4, Part 15)

**Research performed:** `BTMM_STATE_MACHINE.md` (line 248) and `BTMM_MASTER_SUMMARY.md` (line 143) both list `DIRECTIONAL_CONTINUATION` as one of exactly 10 approved `cancellation_reason` values, by name only — **neither document, nor any other file in the knowledge base, defines a rule, formula, source-fact set, threshold, or triggering condition for a BTMM-level `DIRECTIONAL_CONTINUATION` cancellation.** A full-text search of the knowledge base finds exactly one *other*, textually similar but conceptually and structurally distinct concept: **`REJECTED_DIRECTIONAL_CONTINUATION`**, defined with an exact formula (`MEASUREMENT_STANDARDS.md` §7 of the Buy-to-Sell/Sell-to-Buy Reversal Confirmation Standard, Ambiguity 13: `Post-Candidate Close − Candidate High > Continuation Close Tolerance`) — but this rule operates entirely within **POI-candidate formation**, before any `PoiObservation` exists, deciding whether a `BUY_TO_SELL_CANDLE`/`SELL_TO_BUY_CANDLE` *candidate* is rejected before ever becoming a confirmed POI. A POI rejected this way (`REJECTED_DIRECTIONAL_CONTINUATION`/`REJECTED_INSUFFICIENT_REVERSAL`) never produces a `PoiObservation` at all and therefore can never reach this milestone's input boundary or seed a `BTMM_CANDIDATE` in the first place — it is not, and cannot be, the source of a *BTMM-level* cancellation.

**Outcome selected: B — NOT DETERMINISTIC.** `DIRECTIONAL_CONTINUATION` is **not** added to `BtmmCancellationReason` in this milestone. **Exact missing dependency:** no BTMM-level rule exists anywhere in the approved knowledge base defining what "directional continuation" means once a BTMM setup is already underway (e.g., whether it refers to price continuing in the pre-manipulation direction after `BTMM_CANDIDATE` creation, after Reaction Start, or some other anchor; what tolerance, window, or measurement it would use) — this is a distinct, unresolved concept requiring its own future author decision and its own dedicated standard, not a reuse of Ambiguity 13's already-resolved, structurally unrelated POI-candidate-level rule. **Why the other 7 cancellation reasons remain implementable while this one is not:** `POI_REJECTED`, `INTERACTION_INELIGIBLE`, `WEAK_REACTION`, and `REACTION_SPEED_FAILED` each have a complete, already-implemented or already-approved deterministic formula (Ambiguity 15's invalidation state machine, Ambiguity 8's interaction classification, Ambiguity 9's reaction classification, and the reused `measure_leg` speed classification, respectively); `CONTEXT_REJECTED`, `SESSION_INACTIVE`, and `VOLUME_PILLAR_FAILED` are fully specified as reviewed-evidence outcomes with an exact, named triggering value (`MISALIGNED`/`INACTIVE`/`FAILS`) the caller supplies. `DIRECTIONAL_CONTINUATION` has neither an automatic formula nor an approved reviewed-evidence field to carry it — it is a named placeholder in the approved vocabulary with zero operational content, and this milestone does not invent one. A static export/enum test (§36AM) asserts `DIRECTIONAL_CONTINUATION` is absent from `BtmmCancellationReason` and from every other public enum, confirming the deferral is enforced, not merely stated. **`MANUAL_REVIEW_REJECTED` receives the same Outcome-B treatment for a related but distinct reason:** no field in the minimal `BtmmReviewedEvidence` contract (§36G2) carries a standalone "reviewer rejected this setup outright" signal independent of a specific gate's own MISALIGNED/INACTIVE/FAILS value; adding one was considered and rejected as unnecessary scope expansion beyond the Phase 0G Input-Source Policy's own named fields — a future, separate decision may add it if a dedicated field is approved.

### 36I. BTMM Lifecycle Model (fully corrected)

#### 36I1. Initial Primary State (resolving audit Finding B5, Part 11)

**A newly exposed `BtmmObservation` always begins with `primary_state = BTMM_CANDIDATE`.** Candidate creation (the exact rule is unchanged from the original draft: POI identified, direction known, available without look-ahead, not rejected by its own formation standard, valid metadata — all already guaranteed by a confirmed `PoiObservation`) emits the public observation and its first `CurrentBtmmState` record, but **does not by itself imply `BTMM_FORMING` or `BTMM_CONFIRMED`.** `formation_stage` is `None` while `primary_state = BTMM_CANDIDATE`, exactly matching `BTMM_STATE_MACHINE.md`'s own statement that formation stages are preserved only "while `primary_state = BTMM_FORMING`." **Availability:** `BTMM_CANDIDATE`'s own `availability_time_utc` equals the source POI's own `availability_time_utc` — no additional delay.

#### 36I2. `BTMM_CANDIDATE → BTMM_FORMING` (corrected — resolves a contradiction found in a subsequent narrow consistency review)

**This section previously stated `ENTERED_FORMING` fires in the same processing step as `BTMM_CANDIDATE` creation. That contradicted this architecture's own same-availability-group policy (§36AA2), which requires a newly created candidate to remain `BTMM_CANDIDATE` for the entirety of its own creation group. This section is corrected below; the same-step trigger is withdrawn.**

**Required initial policy (corrected, final):** a newly created `BtmmObservation` ends its own creation availability group in `primary_state = BTMM_CANDIDATE` — it does **not** emit `ENTERED_FORMING` in that same group, under any circumstance, including when reviewed evidence for its source POI already happens to be available at creation time. The earliest an `ENTERED_FORMING` transition may occur is in a **later** availability group.

**Exact deterministic trigger:** `BTMM_STATE_MACHINE.md` names no distinct transition identifier for this step beyond the bare state pair in its "Allowed and Forbidden Transitions" table (`BTMM_CANDIDATE → BTMM_FORMING → BTMM_CONFIRMED`), and defines no explicit entry gate condition distinguishing `BTMM_CANDIDATE` from `BTMM_FORMING` beyond "evaluation is underway; gates are being checked as evidence becomes available." This architecture therefore retains one explicit, disclosed **ENGINEERING-PROVISIONAL author gap-fill**, corrected to the first genuinely *later* newly available formation fact: **the first confirmed candle, in the source POI's own timeframe, whose own `availability_time_utc` is strictly later than the `BTMM_CANDIDATE`'s own `availability_time_utc`.** This mirrors the identical "same-instant immunity, next-instant eligibility" pattern already established and proven in `1B-J-POI`'s own breach-walk `start_index` computation (`poi/lifecycle.py`: a POI cannot be breached by a candle sharing its own confirming instant, only by a strictly later one) — reused here, not invented fresh, for the analogous candidate-to-formation boundary.

**Required source facts:** the one newly available confirmed candle described above; no additional fact is required. **Availability:** the triggering candle's own `availability_time_utc` (not the candidate's own — this transition's availability is genuinely later, by construction). **Semantic identity:** `(symbol.value, timeframe.value, str(btmm_setup_record_id), "ENTERED_FORMING", str(source_poi_record_id), rule_version)` — deterministic given the setup's own identity, so exactly one `ENTERED_FORMING` transition record is ever produced per setup, regardless of how many later candles arrive. **Fingerprint:** standard content-fingerprint over its own fields, unchanged formula. **Duplicate-transition suppression:** since the semantic key above depends only on the setup's own stable identity (not on the triggering candle), the identity resolver (§36AC) itself guarantees exactly one `ENTERED_FORMING` record is ever created for a given setup — a setup already in `BTMM_FORMING` or beyond is simply never re-evaluated against this trigger again.

**If no further candle in the source POI's own timeframe ever becomes available after `BTMM_CANDIDATE` creation** (the input prefix ends at or before the candidate's own last candle), the setup remains `BTMM_CANDIDATE` indefinitely — never force-advanced, never defaulted to `BTMM_FORMING` — exactly mirroring how an incomplete Reaction Gate window remains `REACTION_IN_PROGRESS` indefinitely (§36N) rather than being force-resolved.

**Candidate cancellation before entering `BTMM_FORMING`:** a `BTMM_CANDIDATE` setup is not exempt from source-POI invalidation. If the source POI itself becomes `GENUINE_INVALIDATION_CONFIRMED` while the setup is still `BTMM_CANDIDATE` (i.e., before its own `ENTERED_FORMING` trigger has fired), the setup transitions **directly** `BTMM_CANDIDATE → BTMM_CANCELLED`, `cancellation_reason = POI_REJECTED` — skipping `BTMM_FORMING` entirely — under the same source-POI-invalidation-priority rule that governs every other state (§36AA2 step 2, §36Z). This makes the previously-marked "not reachable in this milestone" `BTMM_CANDIDATE → BTMM_CANCELLED` row of the transition table (§36I7) now genuinely reachable, corrected below.

#### 36I3. `BTMM_FORMING` — Deterministic Gate Sequence (unchanged core rules, retimed Reaction Gate)

Within `BTMM_FORMING`, the deterministic gates evaluate in this order, exactly as the original draft, with the Reaction Gate's timing corrected (§36N):

- `POI_INTERACTION` stage: Accuracy Gate (§36K, unchanged). Ineligible first interaction → `BTMM_CANCELLED`, `INTERACTION_INELIGIBLE`. Eligible → advances to `REACTION_MONITORING`.
- `REACTION_MONITORING` stage: Reaction Gate, resolved **only at the 5th confirmed reaction candle** (§36N, corrected), then Reaction-Speed Gate. `WEAK_REACTION` at window close → `BTMM_CANCELLED`, `WEAK_REACTION`. `STANDARD_REACTION`/`STRONG_REACTION` passes; a subsequent `SLOW_OR_UNCLEAR` reaction-leg speed → `BTMM_CANCELLED`, `REACTION_SPEED_FAILED`; `FAST`/`STRONG_FAST` passes.
- `FINAL_GATE_EVALUATION` stage: **corrected** — every one of the 10 gates in §36D's table is checked against the latest available deterministic facts and the latest available `BtmmReviewedEvidence` snapshot (if any) for this setup's source POI:
  - If **all 10** resolve favorably (POI/Accuracy/Reaction/Reaction-Speed/Formation-Timeframe deterministically PASS, and Market-Direction/Analytical-Framework `ALIGNED`, Session `ACTIVE`, Liquidity `PRESENT`, Volume-Pillar `SUPPORTS` via reviewed evidence) → `BTMM_CONFIRMED` (§36I5).
  - If any reviewed-evidence gate is a **definitive rejection** (`MISALIGNED`/`INACTIVE`/`FAILS`) → `BTMM_CANCELLED` with the matching reason (§36H2).
  - Otherwise (at least one reviewed-evidence gate is absent, `PENDING`, `MISSING_DATA`, or `UNRESOLVED`, with no definitive rejection anywhere) → `BTMM_BLOCKED` (§36I4).
  - If the source POI's own timeframe is `M1` → `BTMM_BLOCKED`, `blocked_reason = FORMATION_TIMEFRAME_NOT_CONFIRMED`, regardless of every other gate's status (per `BTMM_STATE_MACHINE.md`: "an M1-only setup must remain `BTMM_FORMING` or `BTMM_BLOCKED`... it must not independently become `BTMM_CONFIRMED`").

#### 36I4. `BTMM_FORMING ⇄ BTMM_BLOCKED` (resolving audit Finding B5, Part 13)

**`BTMM_FORMING → BTMM_BLOCKED`:** triggered exactly once per distinct unresolved condition, via the single generic `BLOCKED` transition type (§36H, replacing the original draft's 2 reason-specific placeholder types), carrying the specific `blocked_reason` (`CONTEXT_UNKNOWN`, `LIQUIDITY_REVIEW_PENDING`, `VOLUME_REVIEW_PENDING`, or `FORMATION_TIMEFRAME_NOT_CONFIRMED`) as its own field on the `BtmmLifecycleTransition` record (§36X, corrected). **`BTMM_BLOCKED → BTMM_FORMING` (`RESUMED_FORMING`):** triggered exactly when a *new* `BtmmReviewedEvidence` snapshot for this setup's source POI becomes available (a later `availability_time_utc` than any evidence already considered) whose content actually changes at least one previously-unresolved gate's value — a `RESUMED_FORMING` transition is recorded, and the setup re-enters `FINAL_GATE_EVALUATION` in the same or a later availability group (§36AA2), where it may then reach `BTMM_CONFIRMED`, a definitive cancellation, or `BTMM_BLOCKED` again (with a possibly different `blocked_reason`, if a different gate is now the blocking one). **Idempotency (resolving the audit's "repeated-BLOCKED" concern):** if a setup is already `BTMM_BLOCKED` for a given `blocked_reason` and no new reviewed evidence arrives in a later availability group, **no repeated `BLOCKED` transition is emitted** — the setup's `CurrentBtmmState` simply carries forward unchanged (same `content_fingerprint`, since nothing about its public content changed). A setup with no reviewed-evidence channel used at all (`reviewed_evidence = ()`) therefore parks in `BTMM_BLOCKED` exactly once and remains there permanently for the life of the input — this is the disclosed, expected behavior when no reviewer supplies evidence, not an implementation gap.

#### 36I5. `BTMM_FORMING → BTMM_CONFIRMED` (resolving audit Finding B3/B5, Part 8)

Reachable **only** from `BTMM_FORMING` at `FINAL_GATE_EVALUATION` (never directly from `BTMM_BLOCKED`, matching `BTMM_STATE_MACHINE.md`'s transition table exactly — a blocked setup must first `RESUMED_FORMING` before it can confirm). The `CONFIRMED` transition type (§36H) is recorded, `primary_state` becomes `BTMM_CONFIRMED`, `formation_stage` becomes `None` (formation is complete), and `btmm_confirmation_time` (`event_time_utc` on the `CONFIRMED` transition) is stored. **`BTMM_CONFIRMED` is terminal in the forward direction** — `BTMM_CONFIRMED → BTMM_CANCELLED` remains forbidden (§36I6) — but the observation retains **stable conceptual identity** throughout: its `record_id`/semantic key never change on confirmation, and its `content_fingerprint` changes only because the gate-status fields it carries changed value, not because a new record was created.

#### 36I6. Terminal and Forbidden Transitions (unchanged, reconfirmed)

`BTMM_CANCELLED` is terminal — never reactivated; a later eligible interaction with the same POI creates a new, independent `btmm_setup_id`. `BTMM_CANCELLED → BTMM_CONFIRMED` and `BTMM_CONFIRMED → BTMM_CANCELLED` are both forbidden, exactly per `BTMM_STATE_MACHINE.md`. **Source-POI invalidation after confirmation:** a `GENUINE_INVALIDATION_CONFIRMED` event on the source POI, even after `BTMM_CONFIRMED`, still triggers `BTMM_CANCELLED`/`POI_REJECTED` on the linked setup — the "forbidden `CONFIRMED → CANCELLED`" rule governs *market-based/context-based* re-cancellation, not the one, exact, pre-approved POI-invalidation-inheritance path (§36Z), which `BTMM_STATE_MACHINE.md` explicitly carves out ("A later losing trade must not change `BTMM_CONFIRMED` to cancelled" governs trade outcomes, not this inherited POI-rejection path — resolved identically to the original draft's §36Z, unchanged by this correction).

### 36I7. Exact Closed Transition Table (resolving audit Part 14)

| From | May remain | May become | Trigger | Test ownership |
|---|---|---|---|---|
| `BTMM_CANDIDATE` | **Yes — for the entirety of its own creation availability group, and for every subsequent group until a later group's own `ENTERED_FORMING` trigger fires (corrected, §36I2)** | `BTMM_FORMING` | The first confirmed candle, in the source POI's own timeframe, whose own `availability_time_utc` is strictly later than `BTMM_CANDIDATE`'s own `availability_time_utc` — never in the same group as creation (corrected, §36I2) | `test_candidate_enters_forming_only_in_later_availability_group`, `test_new_candidate_remains_candidate_in_creation_group`, `test_candidate_to_forming_transition_is_emitted_once` |
| `BTMM_CANDIDATE` | — | `BTMM_CANCELLED` | **Reachable, corrected from the original draft's "not reachable" claim** — source-POI `GENUINE_INVALIDATION_CONFIRMED` occurring while the setup is still `BTMM_CANDIDATE` (before its own `ENTERED_FORMING` trigger has fired) transitions directly to `BTMM_CANCELLED`/`POI_REJECTED`, skipping `BTMM_FORMING` entirely (§36I2) | `test_candidate_can_cancel_before_entering_forming` |
| `BTMM_FORMING` | Yes (`POI_INTERACTION`/`REACTION_MONITORING`/`FINAL_GATE_EVALUATION` stage progression) | `BTMM_BLOCKED` | `FINAL_GATE_EVALUATION` with ≥1 unresolved reviewed gate, no definitive rejection | `test_forming_becomes_blocked_for_unresolved_mandatory_gate` |
| `BTMM_FORMING` | Yes | `BTMM_CONFIRMED` | `FINAL_GATE_EVALUATION` with all 10 gates favorable | `test_btmm_confirmed_requires_all_automatic_and_reviewed_gates` |
| `BTMM_FORMING` | Yes | `BTMM_CANCELLED` | Accuracy/Reaction/Reaction-Speed Gate failure, or any definitive reviewed-evidence rejection, or source-POI genuine invalidation | `test_source_poi_invalidation_has_transition_priority`, plus per-reason tests |
| `BTMM_BLOCKED` | Yes (unchanged reason) | `BTMM_FORMING` | New reviewed evidence changes a previously-unresolved gate | `test_blocked_resumes_forming_when_blocker_resolves` |
| `BTMM_BLOCKED` | Yes | `BTMM_CANCELLED` | Source-POI genuine invalidation (only; a blocked setup cannot receive a definitive reviewed rejection without first passing through a `RESUMED_FORMING` re-evaluation) | `test_source_poi_invalidation_has_transition_priority` |
| `BTMM_CONFIRMED` | Yes (terminal, forward) | — (no market/context re-cancellation) | N/A | `test_confirmed_forbids_recancellation` (implied by exports/lifecycle test file) |
| `BTMM_CONFIRMED` | — | `BTMM_CANCELLED` (POI-inheritance only) | Source-POI `GENUINE_INVALIDATION_CONFIRMED` | covered under `POI_REJECTED` inheritance tests |
| `BTMM_CANCELLED` | Yes (terminal) | — | N/A (never reactivated) | `test_cancellation_is_terminal_never_reactivated` |

Every transition above has an exact trigger, an exact availability rule (§36AA2), and named test ownership (§36AM).

### 36J. POI Eligibility for BTMM — Exact Matrix (unchanged, reconfirmed against source)

Unchanged from the original draft and reconfirmed during the audit by direct comparison against `src/btmm_ai_scanner/poi/enums.py`'s `LIFECYCLE_ELIGIBLE_POI_TYPES` (byte-for-byte match, 18 members) and `NOT_APPLICABLE_LIFECYCLE_POI_TYPES` (14 members, splitting into 2 `CONTEXT-ONLY` + 12 `NOT_APPLICABLE`). No change.

### 36K. POI Interaction and Overshoot — Accuracy Gate (unchanged, reconfirmed against source)

Unchanged from the original draft; formulas reconfirmed verbatim against `MEASUREMENT_STANDARDS.md` "POI Zone Interaction, Penetration, and Overshoot Standard" during the audit. The audit's non-blocking note (N4) is recorded here: Ambiguity 8's Contact/Overshoot Tolerance formulas share numerically identical multipliers with Ambiguity 15's already-implemented `zone_contact_tolerance_*`/`zone_overshoot_tolerance_*` fields in `poi/configuration.py` (`0.05`/`0.10` ATR, `0.10`/`0.25` zone-height) — **this is confirmed to be a coincidence of the two approved standards sharing a numeric convention, not a copy-paste error**: Ambiguity 8 applies its formula to wick extremes for interaction classification, while Ambiguity 15 applies the same-valued formula to candle close for breach/reclaim detection — different price references, different purposes, verified via direct source comparison during the audit.

### 36L. Approach Behavior — Non-Mandatory, Not Automatically Computed (unchanged)

Unchanged from the original draft.

### 36M. Liquidity Before, Within, and After POI (corrected: full gate now reviewed-evidence-reachable)

The automatic `FALSE_INVALIDATION_CONFIRMED → LIQUIDITY_AFTER_POI/RULE_BASED` pathway is preserved exactly as the original draft (§36M unchanged in this respect) — this remains the only *automatically detected* liquidity fact, and it alone still never satisfies the full Liquidity Gate (an unreviewed `RULE_BASED` event cannot pass the gate, per `BTMM_STATE_MACHINE.md` line 131). **Corrected:** the full Liquidity Gate is now genuinely reachable — not merely disclosed as permanently blocked — through the caller-supplied `BtmmReviewedEvidence.liquidity_evidence_status = PRESENT` field (§36G2), which may itself be grounded in a caller's review of the automatically-detected `RULE_BASED` event (upgrading it to `RULE_BASED_REVIEWED` provenance) or in any other independently reviewed liquidity-event label the caller supplies (`EXPERT_LABELLED`/`HYBRID_REVIEWED`). No sweep detector, density score, or liquidity-before/-within automation is invented — these remain explicitly unautomated, exactly as the original draft stated.

### 36N. Reaction Strength and Reaction-Speed Gates (corrected: window-completion timing, resolving audit Finding B1)

Formulas and thresholds are unchanged and were reconfirmed byte-for-byte against `MEASUREMENT_STANDARDS.md` §9-11 during the audit (`STANDARD_REACTION`: ATR Reaction Ratio ≥ 0.75, Zone Clearance Ratio ≥ 1.00, Directional Efficiency ≥ 0.50, Directional Candle Share ≥ 0.60; `STRONG_REACTION`: ≥ 1.25 / ≥ 1.50 / ≥ 0.60 / ≥ 0.67 plus `FAST`/`STRONG_FAST` speed). **Corrected timing, resolving audit Finding B1:**

- **The reaction window contains exactly five confirmed reaction candles.** For reaction candles 1 through 4 (i.e., while the window remains open), `CurrentBtmmState.reaction_classification = REACTION_IN_PROGRESS` **unconditionally** — even if `STANDARD_REACTION` or `STRONG_REACTION` thresholds are already numerically satisfied on an earlier candle. The Reaction Gate does **not** resolve `PASS`/`FAIL` before window completion, and no `BTMM_CONFIRMED` (or any other public transition depending on the Reaction Gate) may use a reaction result from an incomplete window. This corrects the original draft's ambiguous phrasing ("achieved within the window"), which could be misread as authorizing early resolution.
- **At availability of the fifth confirmed reaction candle:** the complete five-candle window is evaluated as a whole; the **highest** approved reaction tier achieved on **any** candle anywhere within the full window is selected (`STRONG_REACTION` > `STANDARD_REACTION` > `WEAK_REACTION`, per `MEASUREMENT_STANDARDS.md` §4's own "assign the highest reaction tier achieved during the window" rule); `reaction_classification` is finalized to that tier; the Reaction Gate resolves `PASS` (`STANDARD_REACTION`/`STRONG_REACTION`) or `FAIL` (`WEAK_REACTION`) at that same instant.
- **`availability_time_utc`** for the finalized `reaction_classification` (and any transition depending on it) equals the maximum availability among all five required reaction candles and every other required source fact (ATR, leg metrics) — never earlier.
- **The finalized classification does not repaint** — once assigned at the fifth candle, it is never revised by a later candle; a `BtmmLifecycleTransition` recording `REACTION_GATE_CONFIRMED`/`WEAK_REACTION` is immutable exactly like every other transition record in this project.
- **If the five confirmed reaction candles never become available** (e.g., the input prefix ends mid-window): `reaction_classification` remains `REACTION_IN_PROGRESS` indefinitely, the Reaction Gate remains unresolved, and the setup's `primary_state` stays `BTMM_FORMING`/`REACTION_MONITORING` — it is never force-resolved, never defaults to `WEAK_REACTION`, and never blocks (a still-open reaction window is not "missing mandatory information" in the `BTMM_BLOCKED` sense — it is ordinary in-progress evaluation).

### 36O. Pressure Behavior (unchanged)

Unchanged from the original draft.

### 36P. Buy-to-Sell and Sell-to-Buy — Generic Direction, Not Separate Patterns (unchanged)

Unchanged from the original draft.

### 36Q. Structure Interaction — Excluded (unchanged)

Unchanged from the original draft.

### 36R. Volume Pillar Gate — Final Decision (Option B, corrected from author-decision-pending)

**Selected: Option B — no new automatic Volume Pillar formula is implemented; the Volume Pillar is resolved only through the approved reviewed-evidence channel.** The original draft's Option A (reusing price-action proxy fields with a new, disclosed threshold pairing) is **removed from consideration** — it is not implemented and not offered as an alternative, since it would require inventing a SUPPORTS/FAILS threshold mapping the approved standard does not itself specify, which this correction avoids entirely by routing Volume Pillar resolution through `BtmmReviewedEvidence.volume_pillar_status` (§36G2) instead. Price-action/momentum proxy fields already computed internally by POI family detectors are **not** reused for this gate. The gate never silently passes when volume evidence is unavailable — absence leaves `volume_pillar_status = PENDING` (or, if the reviewer explicitly reports missing data, `MISSING_DATA`; or `UNRESOLVED` if reviewed evidence exists but cannot resolve the pillar), and `FINAL_GATE_EVALUATION` parks the setup `BTMM_BLOCKED`/`VOLUME_REVIEW_PENDING` in every one of those three cases.

### 36S. Context Gate — Now Reachable Through Reviewed Evidence (corrected from "structurally unreachable")

**The single most important correction in this pass.** The original draft found `market_direction_status`/`analytical_framework_status`/`session_status` permanently `PENDING`/`UNKNOWN` with no input channel. **Corrected:** these fields are now genuinely settable via `BtmmReviewedEvidence` (§36G2), exactly matching `BTMM_STATE_MACHINE.md`'s own approved "Phase 0G Input-Source Policy" (`context_input_source = MANUAL_EXPERT_LABEL` and equivalents). No automatic detector is invented — `BtmmReviewedEvidence` only accepts already-reviewed facts as typed input; this milestone still never computes a moving average, HH/HL, BOS/CHoCH, or a session calendar itself. **`BTMM_CONFIRMED` is therefore genuinely reachable by `analyze_btmm()`'s own deterministic code, given sufficient caller-supplied reviewed evidence** — not automatically, and not for every setup (a caller supplying `reviewed_evidence = ()` will never see any setup confirm), but reachable in the sense Part 5/Option C of the audit required: the code path exists, is exercised by tests, and does not depend on any future milestone.

### 36T. Formation Timeframe Gate (unchanged)

Unchanged from the original draft.

### 36U. Candidate/Public-Output Separation (unchanged)

Unchanged from the original draft — public existence begins at `BTMM_CANDIDATE` creation (§36I1).

### 36V. BTMM Observation Contract (unchanged, 15 fields, reconfirmed)

Unchanged from the original draft — 15 fields, no entry/SL/TP/trade-outcome/AI-confidence field. Reconfirmed by direct recount during this correction.

### 36W. Current BTMM State Contract (corrected field types and additions)

**33 fields, corrected from the original draft's 32** (net +1: `volume_pillar_status` and `liquidity_evidence_status` are each retyped, not added — the latter now `BtmmLiquidityEvidenceStatus` rather than `BtmmGateStatus`, per the corrected semantic analysis in §36H1; the reviewed-evidence read-through fields below are the actual net additions, offset by removing the two now-redundant blocked-reason-implying transition types from the type system, which does not change contract field count):

```
record_id: UUIDv7
content_fingerprint: SHA256Fingerprint
symbol: InternalSymbol
timeframe: Timeframe
btmm_setup_record_id: UUIDv7
btmm_direction: BtmmDirection
source_poi_type: PoiType
primary_state: BtmmLifecycleStatus
formation_stage: BtmmFormationStage | None
market_direction_status: BtmmContextAlignmentStatus
analytical_framework_status: BtmmContextAlignmentStatus
session_status: BtmmSessionStatus
accuracy_gate_status: BtmmGateStatus
interaction_class: BtmmInteractionClass | None
reaction_gate_status: BtmmGateStatus
reaction_classification: BtmmReactionClassification | None
reaction_speed_gate_status: BtmmGateStatus
reaction_speed_classification: LegSpeedClassification | None
formation_timeframe_gate_status: BtmmGateStatus
volume_pillar_status: BtmmVolumePillarStatus
liquidity_evidence_status: BtmmLiquidityEvidenceStatus
liquidity_location: BtmmLiquidityLocation | None
liquidity_evidence_source: BtmmEvidenceSource | None
reviewed_evidence_availability_time_utc: datetime | None
cancellation_reason: BtmmCancellationReason | None
blocked_reason: BtmmBlockedReason | None
latest_lifecycle_transition_id: UUIDv7 | None
availability_time_utc: datetime
rule_version: SemVer
contract_version: SemVer
schema_version: SemVer
evidence_classification: EvidenceClassification
provenance_id: UUIDv7
```

**Exact recount: 33 fields.** Changes from the original 32-field draft: `volume_pillar_status` is now typed `BtmmVolumePillarStatus` (was `BtmmGateStatus`); one new field, `reviewed_evidence_availability_time_utc: datetime | None`, is added — `None` until at least one `BtmmReviewedEvidence` snapshot has been applied to this setup, otherwise the availability time of the most recent reviewed-evidence snapshot actually applied (read-through provenance timing, distinct from the record's own `availability_time_utc`, which also folds in every deterministic fact). No field implies entry/stop/target/risk/trade-result/AI-confidence. **Stable semantic identity unchanged: `(symbol, timeframe, source_poi_record_id, rule_version)`** — content evolves as gates resolve (including via reviewed evidence) while `record_id` stays fixed; `content_fingerprint` changes whenever any public field's value changes, including `blocked_reason`/`primary_state`/`volume_pillar_status` transitions.

### 36X. Lifecycle Transitions (corrected field list)

**15 fields, +1 field versus the original draft's 14** (adds `blocked_reason`, needed now that `BLOCKED` is a single generic transition type carrying its reason inline, per §36H/§36I4):

```
record_id: UUIDv7
content_fingerprint: SHA256Fingerprint
symbol: InternalSymbol
timeframe: Timeframe
btmm_setup_record_id: UUIDv7
transition_type: BtmmLifecycleTransitionType
blocked_reason: BtmmBlockedReason | None
triggering_candle_record_id: UUIDv7 | None
triggering_reviewed_evidence_availability_time_utc: datetime | None
event_time_utc: datetime
availability_time_utc: datetime
rule_version: SemVer
contract_version: SemVer
schema_version: SemVer
evidence_classification: EvidenceClassification
provenance_id: UUIDv7
```

**Exact recount: 16 fields** (corrected once more after direct enumeration — `blocked_reason` and `triggering_reviewed_evidence_availability_time_utc` are both genuinely new, and `triggering_candle_record_id` is now optional since a `CONTEXT_REJECTED`/`SESSION_INACTIVE`/`VOLUME_PILLAR_FAILED`/`NO_LIQUIDITY_EVIDENCE`/`BLOCKED`/`RESUMED_FORMING`/`CONFIRMED` transition may be triggered by reviewed-evidence availability rather than a specific triggering candle — the field is retained but nullable, and `triggering_reviewed_evidence_availability_time_utc` is populated instead in that case; exactly one of the two triggering-reference fields is non-`None` for any given transition, enforced by construction, not by a separate validation error). `blocked_reason` is `None` for every transition type other than `BLOCKED`.

### 36Y. Cross-POI Applicability Matrix (unchanged)

Unchanged from the original draft.

### 36Z. Lifecycle Reconciliation — POI/BTMM Interplay (unchanged, reconfirmed)

Unchanged from the original draft; **source-POI invalidation priority is now explicit in the same-group ordering model (§36AA2, priority list item 2)** rather than only implied.

### 36AA. Same-Candle and No-Look-Ahead Ordering — Superseded by §36AA2

The original draft's high-level "availability-time-driven correctness by construction" prose is retained as the underlying principle but is now given one exact, closed procedural model in §36AA2, resolving audit Part 17's requirement to replace high-level wording with an exact availability-group model.

### 36AA2. Exact Availability-Group Processing Order (corrected — removes the candidate/forming same-step contradiction)

**This section previously let step 8 create a new `BTMM_CANDIDATE` and its `ENTERED_FORMING` transition in the same step, while step 9 simultaneously claimed a newly created candidate "cannot advance beyond `BTMM_CANDIDATE`/`BTMM_FORMING`" in that group — internally inconsistent, since creating-and-entering-`BTMM_FORMING` in the same group is itself "advancing beyond `BTMM_CANDIDATE`."** Corrected below: candidate creation and the `ENTERED_FORMING` transition are now structurally assigned to different steps that can never apply to the same setup in the same group.

For each global availability group, in this exact order:

1. Bring forward every prior `BtmmObservation` and `CurrentBtmmState` unchanged as the starting point for this group.
2. Apply source-POI genuine invalidation and terminal cancellation first, for every setup whose source POI became `GENUINE_INVALIDATION_CONFIRMED` in this group — `BTMM_CANCELLED`/`POI_REJECTED` takes priority over every other possible transition for that setup in this same group, **including a setup still in `BTMM_CANDIDATE`** (§36I2's corrected candidate-cancellation rule).
3. **For every setup still `BTMM_CANDIDATE` from a *prior* group** (not cancelled in step 2 above), check whether this group contains the first confirmed candle, in its own source POI's timeframe, whose `availability_time_utc` is strictly later than that setup's own `BTMM_CANDIDATE` `availability_time_utc` — if so, emit `ENTERED_FORMING` and move `primary_state` to `BTMM_FORMING`/`formation_stage = CONTEXT_CHECK` (§36I2, corrected). **This step never applies to a setup created in this same group** — see step 8.
4. Apply newly available `BtmmReviewedEvidence` (whose own `availability_time_utc` falls within this group) to every existing `BTMM_FORMING`/`BTMM_BLOCKED` setup referencing the same source POI.
5. Apply newly available deterministic interaction, reaction (non-final), liquidity (`RULE_BASED` automatic fact only), and gate-progress facts to existing `BTMM_FORMING` setups.
6. Complete five-candle Reaction Gate windows where the fifth confirmed reaction candle becomes available in this group (§36N).
7. Select **at most one** primary-state transition per `BtmmObservation` for this group, using this exact priority when more than one condition would otherwise apply simultaneously: **`CANCELLED` > `CONFIRMED` > `BLOCKED` > `RESUMED_FORMING` > `ENTERED_FORMING`.**
8. Create new `BTMM_CANDIDATE` observations for any newly visible, newly eligible BTMM-eligible POI in this group — **these remain `BTMM_CANDIDATE` for the entire remainder of this group; no `ENTERED_FORMING` transition is ever emitted for a setup in the same group it was created, under any circumstance** (corrected — step 3 above only evaluates setups carried forward from a *prior* group, never one created in step 8 of this same group).
9. **Structural guarantee (corrected):** a newly created candidate cannot advance beyond `BTMM_CANDIDATE` in its own creation group — not merely "beyond `BTMM_CANDIDATE`/`BTMM_FORMING`" as the original draft stated. By construction it therefore cannot reach `BTMM_FORMING`, `BTMM_BLOCKED`, or `BTMM_CONFIRMED` in that same group either, since each of those requires having first entered `BTMM_FORMING`, which step 8 explicitly withholds.
10. Finalize `CurrentBtmmState` and deterministic output ordering (§36AH) for the group.

**Consequences, explicitly disclosed:** a newly created candidate always remains `BTMM_CANDIDATE` through the end of its own creation group, full stop — not merely "cannot confirm," but cannot even enter `BTMM_FORMING` — reviewed evidence or not; the earliest `ENTERED_FORMING` transition is structurally guaranteed to occur in a later group (step 3, evaluated only against carried-forward candidates); source-POI invalidation always has priority, including over a still-`BTMM_CANDIDATE` setup (step 2); at most one primary-state transition per observation per group (step 7); no partial group processing (every step applies uniformly across the full visible prefix for the group); no same-group create-and-confirm, and now also no same-group create-and-enter-forming (step 9); no future evidence is ever consulted (every step operates only on facts whose own `availability_time_utc` falls at or before the current group).

### 36AB. Multi-Timeframe Policy (unchanged)

Unchanged from the original draft.

### 36AC. Identity and Fingerprint Strategy — Final Decision (Option B, corrected from author-decision-pending)

**Selected: Option B — a fourth disclosed local canonical serializer implementation.** The original draft's default recommendation (Option A, extracting a shared serializer into a new module and modifying `domain/analyzer.py`/`structure/analyzer.py`/`poi/analyzer.py`) is **removed**. **Reason, exactly as the correction requires:** the measurement, structure, and POI milestones are closed; no correctness defect exists in their existing serializers (verified by direct source comparison during the audit — all three implementations are structurally identical); extracting a shared utility would reopen three closed implementations for a purely cosmetic DRY improvement; the accelerated governance model applied throughout this project prefers zero blast radius on closed work; and four-way equivalence testing provides the required safety net without any shared-file risk. This also matches `1B-J-POI`'s own precedent (its own Option C: a third disclosed duplicate, for the identical reason).

**Requirements, all satisfied by this design:**
- No completed analyzer (`domain/analyzer.py`, `structure/analyzer.py`, `poi/analyzer.py`) is modified by this milestone.
- No shared serializer file is introduced anywhere in the repository.
- `btmm/analyzer.py` owns its own private, local `_canonicalize`/`_compute_content_fingerprint`/`_IdentityResolver`/`_finalize` implementation — a fourth structurally-identical copy.
- **Maintenance risk is disclosed:** four independent copies of the same ~60-line serializer now exist; a future correctness fix to the canonicalization algorithm (e.g., a new value type needing serialization) must be applied to all four locations, and there is no automated enforcement preventing them from silently drifting apart between now and that future fix — this risk is accepted deliberately, in writing, in exchange for zero blast radius on three closed milestones.
- **Four-way equivalence testing is mandatory**, extending `1B-J-POI`'s existing three-way test: `test_four_way_serializer_equivalence` (§36AM) constructs one shared corpus of representative values and asserts `domain._compute_content_fingerprint(fields) == structure._compute_content_fingerprint(fields) == poi._compute_content_fingerprint(fields) == btmm._compute_content_fingerprint(fields)` for every value combination, covering at minimum: `Decimal` (including zero and negative), every relevant `StrEnum` member, `UUIDv7`, a timezone-aware `datetime`, `SemVer`, `tuple` (including empty and nested), `None`, `bool`, `int`, `str`, and at least one nested public contract instance (e.g., a `PoiObservation` or `BtmmObservation` field embedded within a dict-like structure) to confirm recursive canonicalization agrees across all four implementations.
- The corrected 22-path scope (§36AL) reflects Option B cleanly: no existing file outside `btmm/` and `domain/enums.py` is touched.

**Every remaining Option A/Option B uncertainty from the original draft is now removed — Option B is final.**

### 36AD. Evidence Classification (unchanged, reconfirmed)

Unchanged — every emitted output stores exactly `EvidenceClassification.ENGINEERING_PROVISIONAL`; never `AUTHOR_APPROVED`/`BOOK_SOURCED`/a compound value. Reviewed evidence's own provenance fields (§36G2) are a separate axis, reconfirmed non-conflated during this correction.

### 36AE. Output Model and Public API (corrected signature)

**Five contracts:** `BtmmObservation` (§36V), `BtmmLifecycleTransition` (§36X), `CurrentBtmmState` (§36W), `BtmmAnalysis` (aggregate, unchanged shape), `BtmmReviewedEvidence` (§36G2, new) — no `ReactionObservation` sixth contract.

**Corrected public API:**

```python
def analyze_btmm(
    timeframe_inputs: tuple[BtmmTimeframeInput, ...],
    poi_analysis: PoiAnalysis,
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    configuration: BtmmConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> BtmmAnalysis:
    ...
```

`reviewed_evidence` is now a **required** positional parameter (not optional-with-default) — an empty tuple `()` is always valid and is the correct way for a caller with no reviewer channel to call this function, but the parameter itself must always be supplied explicitly, keeping the reviewed-evidence pathway visible at every call site rather than hidden behind a default. **No hidden manual-evidence repository, no global review registry, no wall clock, no I/O, and no future-evidence use** — `reviewed_evidence` is consumed exactly like every other input tuple: read once, validated, and applied only according to its own declared `availability_time_utc` (§36AA2).

**Empty behavior:** `timeframe_inputs == ()` or `poi_analysis.poi_observations == ()` returns the fully-empty `BtmmAnalysis`, unchanged. `reviewed_evidence == ()` is independently valid and does not by itself empty the result — setups still form, interact, and react; they simply never reach `BTMM_CONFIRMED` and eventually park `BTMM_BLOCKED`.

### 36AF. Error Vocabulary (unchanged count: 10 total, 4 reused + 6 new — triggers broadened, no new classes)

| Error | Reused/New | Trigger (corrected/broadened where noted) |
|---|---|---|
| `MixedSymbolAnalysisError` | Reused | Mixed symbol across bundles, `poi_analysis`, **or `reviewed_evidence` (broadened)** |
| `DuplicateCandleRecordError` | Reused | Unchanged |
| `UnsortedCandleSequenceError` | Reused | Unchanged |
| `DerivedIdentityCollisionError` | Reused | Unchanged |
| `InvalidBtmmConfigurationError` | New | Unchanged |
| `DuplicateBtmmTimeframeInputError` | New | Unchanged |
| `UnsortedBtmmTimeframeInputError` | New | Unchanged |
| `InputPrefixMismatchError` | New | Unchanged triggers, **broadened to cover: duplicate `BtmmReviewedEvidence` for one source POI; `BtmmReviewedEvidence.symbol`/`timeframe` disagreeing with its referenced source POI; a naive (non-timezone-aware) `availability_time_utc` on any `BtmmReviewedEvidence`; and a disallowed `BtmmEvidenceSource` value on a caller-supplied evidence field (§36G2)** |
| `MissingSourcePoiRecordError` | New | Unchanged trigger, **broadened to cover a `BtmmReviewedEvidence.source_poi_record_id` referencing no supplied `PoiObservation`** |
| `ImpossibleBtmmLifecycleTransitionError` | New | Unchanged |

**Total unchanged at 10** (4 reused + 6 new) — no new error class was introduced; every reviewed-evidence validation rule was folded into the existing, appropriately-named error triggers above, keeping the export-facing error surface at exactly 6.

### 36AG. Configuration (corrected: no Volume Pillar fields, no reviewed-evidence values)

```
minimum_price_tick: Decimal

eligible_poi_types: frozenset[PoiType] = frozenset(<the 18 BTMM-eligible types>)
supported_symbols: frozenset[InternalSymbol] = frozenset({XAUUSD, EURUSD, GBPUSD})
formation_timeframes: frozenset[Timeframe] = frozenset({M5, M15})
supporting_only_timeframes: frozenset[Timeframe] = frozenset({M1})

interaction_contact_tolerance_atr_multiplier: Decimal = Decimal("0.05")
interaction_contact_tolerance_zone_height_multiplier: Decimal = Decimal("0.10")
interaction_overshoot_tolerance_atr_multiplier: Decimal = Decimal("0.10")
interaction_overshoot_tolerance_zone_height_multiplier: Decimal = Decimal("0.25")
interaction_edge_touch_max_penetration_ratio: Decimal = Decimal("0.25")
interaction_partial_entry_max_penetration_ratio: Decimal = Decimal("0.50")

reaction_window_bars: int = 5
reaction_standard_atr_ratio: Decimal = Decimal("0.75")
reaction_standard_zone_clearance_ratio: Decimal = Decimal("1.00")
reaction_standard_directional_efficiency: Decimal = Decimal("0.50")
reaction_standard_directional_candle_share: Decimal = Decimal("0.60")
reaction_strong_atr_ratio: Decimal = Decimal("1.25")
reaction_strong_zone_clearance_ratio: Decimal = Decimal("1.50")
reaction_strong_directional_efficiency: Decimal = Decimal("0.60")
reaction_strong_directional_candle_share: Decimal = Decimal("0.67")

reaction_speed_fast_normalized_speed_per_bar: Decimal = Decimal("0.50")
reaction_speed_fast_directional_efficiency: Decimal = Decimal("0.60")
reaction_speed_fast_directional_candle_share: Decimal = Decimal("0.67")
reaction_speed_strong_fast_normalized_speed_per_bar: Decimal = Decimal("0.75")
reaction_speed_strong_fast_directional_efficiency: Decimal = Decimal("0.75")
reaction_speed_strong_fast_directional_candle_share: Decimal = Decimal("0.80")

rule_version: SemVer = SemVer.parse("1.0.0")
contract_version: SemVer = SemVer.parse("0.1.0")
schema_version: SemVer = SemVer.parse("0.1.0")
evidence_classification: EvidenceClassification = EvidenceClassification.ENGINEERING_PROVISIONAL
```

**Corrected: no Volume Pillar threshold field of any kind exists** (Option B removes the need entirely, §36R) — the original draft never actually added one either (Option A was left as a non-default alternative), so this is a confirmation, not a removal. **No reviewed-evidence value (e.g., a default `volume_pillar_status`) belongs in configuration** — reviewed gate values live exclusively in `BtmmReviewedEvidence` (§36G2), a per-call input, never a static configuration default; configuration only ever holds deterministic thresholds and structural constants. **No duplicate POI-lifecycle setting** — `ATR(14)` is read via `measurements.compute_atr_series`, reused, never recomputed; POI lifecycle state is consumed from `PoiAnalysis`, never recomputed. Every remaining field is a deterministic threshold required by one of the 5 automatic gates (Accuracy, Reaction, Reaction-Speed) or a structural constant (`formation_timeframes`, `supporting_only_timeframes`, `eligible_poi_types`, `supported_symbols`) genuinely consulted by name.

### 36AH. Deterministic Ordering (unchanged)

Unchanged from the original draft.

### 36AI. Replay Equivalence Procedure (corrected: includes reviewed evidence)

For each global availability group: (1) append newly-available candles atomically; (2) recompute (or accept caller-supplied) `MarketMeasurementAnalysis`; (3) recompute (or accept caller-supplied) `PoiAnalysis` for the identical visible prefix; **(4) expose only `BtmmReviewedEvidence` records whose own `availability_time_utc` has been reached by this group — never earlier-supplied, never future evidence (corrected/new step)**; (5) re-invoke `analyze_btmm()`; (6) compare against an independent, one-shot, direct-batch call over the complete final state, including the complete final `reviewed_evidence` tuple — must be identical; (7) verify stable `BtmmObservation`/`BtmmLifecycleTransition` identities across growing prefixes; (8) verify `CurrentBtmmState.content_fingerprint` changes only when public content changes; (9) **verify reviewed evidence never leaks backward — a setup's state in an earlier prefix must never reflect reviewed evidence whose `availability_time_utc` falls after that prefix's own visible horizon (new)**; (10) **verify no same-group candidate confirmation (new, §36AA2 step 9)**; (11) **verify source-POI invalidation priority (new, §36AA2 step 2)**; (12) verify `POI_REJECTED` inheritance is stable and never reverses a genuine invalidation.

### 36AJ. Implementability Matrix (corrected: 10 of 12 rows now implementable)

| # | Pattern component | Readiness | Missing decision |
|---|---|---|---|
| 1 | POI Gate | **IMPLEMENTABLE** (deterministic) | None |
| 2 | Accuracy Gate | **IMPLEMENTABLE** (deterministic) | None |
| 3 | Reaction Gate | **IMPLEMENTABLE** (deterministic, window-completion timing corrected) | None |
| 4 | Reaction-Speed Gate | **IMPLEMENTABLE** (deterministic) | None |
| 5 | Formation Timeframe Gate | **IMPLEMENTABLE** (deterministic) | None |
| 6 | Liquidity-after-POI automatic evidence | **IMPLEMENTABLE** (deterministic, evidence-only) | None |
| 7 | POI-invalidation inheritance | **IMPLEMENTABLE** (deterministic) | None |
| 8 | Context Gate (Market Direction/Analytical Framework/Active Session) | **IMPLEMENTABLE** (via caller-supplied reviewed evidence, corrected) | None — resolved by `BtmmReviewedEvidence` |
| 9 | Volume Pillar Gate | **IMPLEMENTABLE** (via caller-supplied reviewed evidence only, Option B final) | None — resolved by `BtmmReviewedEvidence` |
| 10 | Full Liquidity Gate (reviewed) | **IMPLEMENTABLE** (via caller-supplied reviewed evidence, corrected) | None — resolved by `BtmmReviewedEvidence` |
| 11 | Accumulation/Distribution | **DEFERRED** (no approved definition anywhere) | Fresh author decision |
| 12 | Approach Speed (non-mandatory) | **DEFERRED** (no approved anchor) | Approach-leg anchor rule |

**Totals: 10 of 12 rows IMPLEMENTABLE; 2 rows DEFERRED (Accumulation/Distribution, Approach Speed), unchanged from the original draft since neither is affected by the reviewed-evidence correction; 0 BLOCKED.**

### 36AK. Exact Initial Implementation Set (corrected)

**10 of 12 pattern components are now implementable** (up from 7 in the original draft) — rows 1-10. Deferred: rows 11-12 (Accumulation/Distribution, Approach Speed), for the same reasons as the original draft, unaffected by this correction. Blocked: 0. **Choice: implement all 10 implementable rows**, including the 3 reviewed-evidence-dependent gates (Context, Volume Pillar, full Liquidity) as genuine, tested, reachable code paths — not merely disclosed-as-deferred placeholders. Every field this milestone emits now has an exact, complete, deterministic-or-reviewed-input rule; the only remaining public-facing absence is the omission of Approach Speed fields entirely (unchanged) and the total absence of any Accumulation/Distribution output (unchanged).

### 36AL. Exact File Scope (corrected: 22 paths)

**Corrected: 22 total affected paths — 11 new source, 1 modified existing source, 10 new test.** New-path split: 11 source / 10 test (21 new paths). Affected-path split: 12 source / 10 test.

**11 new source paths** (new top-level package `btmm/`), corrected creation order **147-157**:

| Order | Path |
|---|---|
| 147 | `src/btmm_ai_scanner/btmm/__init__.py` |
| 148 | `src/btmm_ai_scanner/btmm/enums.py` |
| 149 | `src/btmm_ai_scanner/btmm/configuration.py` |
| 150 | `src/btmm_ai_scanner/btmm/observation.py` |
| 151 | `src/btmm_ai_scanner/btmm/reviewed_evidence.py` |
| 152 | `src/btmm_ai_scanner/btmm/lifecycle.py` |
| 153 | `src/btmm_ai_scanner/btmm/current_state.py` |
| 154 | `src/btmm_ai_scanner/btmm/interaction.py` |
| 155 | `src/btmm_ai_scanner/btmm/reaction.py` |
| 156 | `src/btmm_ai_scanner/btmm/liquidity.py` |
| 157 | `src/btmm_ai_scanner/btmm/analyzer.py` |

**1 modified existing path (unchanged):** `src/btmm_ai_scanner/domain/enums.py` (third narrow `DerivedOutputType` extension: `BTMM_OBSERVATION`, `BTMM_LIFECYCLE_TRANSITION`, `CURRENT_BTMM_STATE`; creation order 82 unchanged; annotated in place, not a new inventory row).

**No conditional scope remains** — Option B (§36AC) means `domain/analyzer.py`, `structure/analyzer.py`, `poi/analyzer.py` are never touched under any circumstance; the 22-path figure is final and unconditional, correcting the original draft's conditional 21-or-24 framing.

**10 new test paths (unchanged file list, redistributed counts again for this narrow correction), corrected creation order 158-167:**

| Order | Path | Count |
|---|---|---|
| 158 | `tests/unit/test_btmm_configuration.py` | 6 |
| 159 | `tests/unit/test_btmm_eligibility.py` | 5 |
| 160 | `tests/unit/test_btmm_interaction.py` | 9 |
| 161 | `tests/unit/test_btmm_reaction.py` | 11 |
| 162 | `tests/unit/test_btmm_liquidity.py` | 8 |
| 163 | `tests/unit/test_btmm_pressure_and_direction.py` | 5 |
| 164 | `tests/unit/test_btmm_lifecycle_and_gates.py` | 19 |
| 165 | `tests/unit/test_btmm_analyzer_api.py` | 9 |
| 166 | `tests/unit/test_btmm_batch_replay_equivalence.py` | 5 |
| 167 | `tests/unit/test_btmm_exports.py` | 5 |

**Total: 82 new top-level test functions (6+5+9+11+8+5+19+9+5+5), preserved exactly from the prior correction's total** by redistributing counts across the same 10 files rather than adding an 11th file, per this narrow correction's explicit instruction. Combined with the existing 500: **582**, unchanged.

**Dependency direction (unchanged):** `btmm/` depends on `domain`, `measurements`, `contracts`, `config`, `poi` — does **not** depend on `structure`, and (per Option B, §36AC) does **not** depend on any shared serializer module, since none is created.

**Inventory: before 147, new rows 21 (11 source + 10 test), final 168, batch tag `1B-K-BTMM`, creation order 147-167.**

### 36AM. Exact Test Coverage — 82 New Top-Level Test Functions (corrected again — redistributed for the candidate/forming timing correction and the new liquidity-evidence enum)

**`test_btmm_configuration.py` (6, unchanged):** `test_configuration_defaults_match_ambiguity_8_thresholds`, `test_configuration_defaults_match_ambiguity_9_thresholds`, `test_configuration_is_frozen_and_immutable`, `test_configuration_rejects_non_positive_thresholds`, `test_configuration_default_evidence_classification_is_engineering_provisional`, `test_configuration_eligible_poi_types_default_matches_exact_18`.

**`test_btmm_eligibility.py` (5, unchanged):** `test_exact_18_btmm_eligible_poi_types`, `test_equal_highs_and_lows_classified_context_only`, `test_12_period_level_types_classified_not_applicable`, `test_deferred_poi_absent_specifications_never_appear`, `test_eligibility_set_matches_poi_lifecycle_eligible_set_by_cross_reference`.

**`test_btmm_interaction.py` (9, unchanged):** `test_bullish_entry_far_boundary_mapping`, `test_bearish_entry_far_boundary_mapping`, `test_edge_touch_partial_entry_deep_entry_ratio_boundaries`, `test_far_boundary_touch_exact_ratio_one`, `test_controlled_overshoot_within_tolerance`, `test_excessive_overshoot_beyond_tolerance`, `test_near_miss_and_no_contact_distinguished_by_contact_tolerance`, `test_noncanonical_side_interaction_recorded`, `test_wick_and_close_penetration_tracked_independently`.

**`test_btmm_reaction.py` (11, unchanged):** `test_awaiting_reaction_before_reaction_start`, `test_reaction_start_exact_bullish_rule`, `test_reaction_start_exact_bearish_rule`, `test_reaction_gate_remains_in_progress_before_fifth_confirmed_candle`, `test_reaction_gate_resolves_at_fifth_confirmed_candle`, `test_reaction_gate_uses_highest_tier_achieved_in_full_window`, `test_standard_reaction_all_four_conditions`, `test_strong_reaction_all_five_conditions_including_speed`, `test_weak_reaction_on_window_close`, `test_reaction_speed_gate_fast_strong_fast_slow_or_unclear`, `test_reaction_window_never_completing_stays_in_progress_indefinitely`.

**`test_btmm_liquidity.py` (8, corrected — +1, resolving the liquidity-evidence semantics finding):** `test_false_invalidation_confirmed_produces_liquidity_after_poi_rule_based`, `test_liquidity_before_within_and_automatic_rule_based_never_treated_as_reviewed` (merged, combining the original draft's separate before/within-automation and rule-based-reviewed-emission assertions into one test), `test_equal_highs_and_lows_not_treated_as_automatic_evidence`, `test_liquidity_gate_pass_requires_approved_supporting_evidence` (renamed from `test_full_liquidity_gate_reachable_via_reviewed_evidence_present` for exact alignment with the required name), `test_missing_liquidity_evidence_remains_unresolved` (renamed from `test_missing_reviewed_evidence_never_passes_liquidity_gate`), `test_no_liquidity_evidence_cancellation_at_window_close`, `test_reviewed_liquidity_evidence_status_uses_exact_vocabulary` (new — asserts `BtmmLiquidityEvidenceStatus` has exactly 2 members, `PENDING`/`PRESENT`, no invented values), `test_liquidity_evidence_presence_does_not_automatically_pass_gate` (new — asserts `PRESENT` on a reviewed-evidence snapshot does not itself mutate `CurrentBtmmState` until the analyzer's own gate-evaluation step consumes it, keeping the input fact and the computed gate result observably distinct).

**`test_btmm_pressure_and_direction.py` (5, corrected — −1, merged):** `test_pressure_wick_sourced_setup_inherits_context_without_bypassing_gates` (merged from the original draft's two separate pressure tests — one function now asserts both that strength tier is inherited unmodified and that the gate sequence is not bypassed), `test_buy_to_sell_candle_produces_bearish_btmm`, `test_sell_to_buy_candle_produces_bullish_btmm`, `test_no_separate_btmm_pattern_type_enum_exists`, `test_direction_derived_purely_from_source_poi_direction_for_other_types`.

**`test_btmm_lifecycle_and_gates.py` (19, corrected — +2, resolving the candidate/forming timing finding):** `test_candidate_initial_state_is_btmm_candidate`, `test_new_candidate_remains_candidate_in_creation_group` (new), `test_candidate_enters_forming_only_in_later_availability_group` (renamed from `test_candidate_enters_forming_through_explicit_transition`, corrected timing), `test_candidate_to_forming_transition_is_emitted_once` (new — asserts identity-resolver-guaranteed dedup across multiple later groups), `test_candidate_can_cancel_before_entering_forming` (new), `test_interaction_ineligible_cancellation`, `test_forming_becomes_blocked_for_unresolved_mandatory_gate`, `test_blocked_resumes_forming_when_blocker_resolves`, `test_unchanged_blocker_does_not_emit_duplicate_transition`, `test_forbidden_transitions_both_directions` (merged, combining the original draft's separate `CANCELLED→CONFIRMED` and `CONFIRMED→CANCELLED` forbidden-transition assertions into one test), `test_source_poi_invalidation_has_transition_priority`, `test_poi_rejected_inheritance_on_genuine_invalidation`, `test_cancellation_is_terminal_never_reactivated`, `test_new_interaction_creates_new_independent_setup`, `test_context_rejected_cancellation_from_reviewed_evidence`, `test_session_inactive_cancellation_from_reviewed_evidence`, `test_volume_pillar_failed_cancellation_from_reviewed_evidence`, `test_btmm_confirmed_requires_all_automatic_and_reviewed_gates`, `test_directional_continuation_absent_from_public_enum`.

**`test_btmm_analyzer_api.py` (9, corrected — −1, merged):** `test_empty_aggregate_for_empty_input`, `test_rejects_mixed_symbol_across_all_inputs_including_reviewed_evidence`, `test_rejects_duplicate_or_unsorted_timeframe_input`, `test_rejects_unsupported_timeframe`, `test_rejects_measurement_prefix_mismatch`, `test_rejects_missing_source_poi_record`, `test_reviewed_evidence_rejects_unknown_or_duplicate_source_poi` (merged, combining the original draft's two separate reviewed-evidence-rejection assertions into one test), `test_ineligible_poi_type_never_creates_a_setup`, `test_deterministic_across_repeated_calls`.

**`test_btmm_batch_replay_equivalence.py` (5, corrected — −1, merged):** `test_batch_and_replay_produce_identical_observations_and_transitions` (merged, combining the original draft's two separate observation/transition-equivalence assertions into one test), `test_stable_identity_across_growing_prefixes`, `test_current_state_fingerprint_changes_only_with_content`, `test_reviewed_evidence_is_availability_gated_and_never_leaks_backward`, `test_four_way_serializer_equivalence`.

**`test_btmm_exports.py` (5, unchanged, one literal name corrected):** `test_btmm_package_imports_successfully`, `test_exact_29_export_surface_in_order` (renamed from `test_exact_28_export_surface_in_order`, corrected for the new export total), `test_no_entry_stop_target_risk_or_trade_result_field_anywhere`, `test_no_domain_structure_poi_or_measurements_reexport`, `test_no_btmm_pattern_type_enum_exists`.

**Recount: 6+5+9+11+8+5+19+9+5+5 = 82, verified by direct arithmetic.** Every literal test name required by this narrow correction is present and matches exactly, with no naming substitution needed this time: `test_new_candidate_remains_candidate_in_creation_group`, `test_candidate_enters_forming_only_in_later_availability_group`, `test_candidate_to_forming_transition_is_emitted_once`, `test_candidate_can_cancel_before_entering_forming` (all in `test_btmm_lifecycle_and_gates.py`); `test_reviewed_liquidity_evidence_status_uses_exact_vocabulary`, `test_liquidity_evidence_presence_does_not_automatically_pass_gate`, `test_liquidity_gate_pass_requires_approved_supporting_evidence`, `test_missing_liquidity_evidence_remains_unresolved` (all in `test_btmm_liquidity.py`). The net +3 from these two files (lifecycle +2, liquidity +1) is offset by merging 3 pairs of closely related assertions into single test functions elsewhere (pressure-and-direction, analyzer-api, batch-replay-equivalence, each −1) — every merge combines two genuinely related assertions into one still-meaningful test function, not a parametrization, a generated test, or a vacuous assertion. **No test class; no generated test; no helper beginning with `test_`; no `skip`/`xfail`; no vacuous assertion.**

### 36AN. Public Exports (corrected: 29, recounted directly)

**Exactly 29 names, in order — 15 enums, 5 contracts/input value objects, 1 configuration, 6 public errors, 2 API/input:**

```
 1. BtmmDirection                          — enum
 2. BtmmGateStatus                         — enum
 3. BtmmContextAlignmentStatus             — enum
 4. BtmmSessionStatus                      — enum
 5. BtmmInteractionClass                   — enum
 6. BtmmReactionClassification             — enum
 7. BtmmLiquidityLocation                  — enum
 8. BtmmEvidenceSource                     — enum
 9. BtmmLifecycleStatus                    — enum
10. BtmmFormationStage                     — enum
11. BtmmLifecycleTransitionType            — enum
12. BtmmCancellationReason                 — enum
13. BtmmBlockedReason                      — enum
14. BtmmVolumePillarStatus                 — enum
15. BtmmLiquidityEvidenceStatus            — enum (new)
16. BtmmObservation                        — contract
17. BtmmLifecycleTransition                — contract
18. CurrentBtmmState                       — contract
19. BtmmAnalysis                           — contract
20. BtmmReviewedEvidence                   — contract/input value object
21. BtmmConfiguration                      — configuration
22. BtmmTimeframeInput                     — API input
23. InvalidBtmmConfigurationError          — error
24. DuplicateBtmmTimeframeInputError       — error
25. UnsortedBtmmTimeframeInputError        — error
26. InputPrefixMismatchError               — error
27. MissingSourcePoiRecordError            — error
28. ImpossibleBtmmLifecycleTransitionError — error
29. analyze_btmm                           — API
```

**Recounted directly from the numbered list above: 29** — 15 enums (lines 1-15) + 5 contracts/input value objects (lines 16-20) + 1 configuration (line 21) + 6 errors (lines 23-28) + 2 API/input (lines 22, 29) = 29. This is a genuine consequence of the liquidity-evidence semantic analysis in §36H1 — `BtmmLiquidityEvidenceStatus` is a real, distinct enum, not preserved or dropped to hit any preset target — **the export count follows the semantics, not the other way around.** No upstream contract, identity Protocol, serializer helper, internal candidate type, or lifecycle helper function is re-exported.

### 36AO. Complexity and Performance (unchanged)

Unchanged from the original draft.

### 36AP. Explicit Exclusions (corrected: removes the now-resolved reviewed-context/liquidity/volume-pillar exclusion)

Live entry execution; stop-loss placement; take-profit placement; position sizing; trade management; trade outcome; signal confidence; visualization; TradingView rendering; Telegram alerts; news filtering; backtesting statistics; paper trading; broker connectivity; MT5/MT4; AI inference; model training; production approval. **Corrected:** the original draft additionally excluded "the reviewed-context/reviewed-liquidity/volume-pillar-formula input channel" from this milestone — that exclusion is now removed, since this correction implements exactly that channel (§36G2). Still explicitly excluded and deferred to a future, separate, narrowly-scoped task: Accumulation/Distribution (§36E); Approach Speed (§36L); `P0G-B014` general timeframe-strength resolution (§36AB); any sweep-lifecycle detector for Equal Highs/Lows (`P0G-B004`, unchanged); an automatic Volume Pillar formula (Option A, permanently removed from consideration by this correction, §36R); `DIRECTIONAL_CONTINUATION` and `MANUAL_REVIEW_REJECTED` cancellation reasons (§36H4).

### 36AQ. Baseline, Quality Gates, and Stop Conditions (corrected counts)

**Baseline:** `HEAD`/`origin/main` = `545d30b9a6e2d5dae94efc582a3792cebc522049`, unchanged throughout this correction. Full pytest-collected baseline: 578. Existing top-level tests: 500. Existing inventory: 147. **Corrected proposed totals: 22 affected paths (11 new source, 1 modified, 10 new test); 82 new top-level tests (unchanged total, redistributed again for this narrow correction); 582 future combined top-level tests (unchanged); inventory 147 → 168, creation order 147-167 (unchanged by this narrow correction); 29 public exports (corrected from 28, adding `BtmmLiquidityEvidenceStatus`).**

**Future gates (at implementation time, unchanged):** `uv lock --check`; `uv run ruff format --check .`; `uv run ruff check .`; `uv run mypy src tests`; `uv run pytest -q`; `uv run pytest -q tests/test_import_smoke.py tests/test_config_precedence.py`.

**Stop conditions re-checked after this narrow correction, all clear:** the candidate-creation and `ENTERED_FORMING` timing no longer contradict — a newly created candidate provably remains `BTMM_CANDIDATE` through its own entire creation availability group, with the earliest possible `ENTERED_FORMING` transition structurally deferred to a later group (§36I2/§36AA2, resolved); the liquidity-evidence input fact and the final Liquidity Gate result are no longer conflated under one borrowed 3-value enum — a dedicated, minimally-scoped `BtmmLiquidityEvidenceStatus` (2 members, both textually grounded) now represents the field's own genuinely distinct semantics (§36H1, resolved); the export count (29) is a direct consequence of that semantic finding, not a preserved arithmetic target; every other finding from the prior consolidated correction remains resolved and unaffected: the implementability matrix stays 10-of-12; `BTMM_CONFIRMED` remains genuinely reachable; `volume_pillar_status` keeps its own exact 5-value vocabulary; `DIRECTIONAL_CONTINUATION` keeps its fully researched Outcome-B disposition; the Reaction Gate still resolves only at window completion; the fingerprint strategy remains Option B.

### 36AR. Author Decisions Required (corrected, consolidated list)

1. Milestone title and identifier (unchanged: "BTMM Manipulation Lifecycle Foundation" / `1B-K-BTMM`).
2. No separate `BtmmPatternType` taxonomy (unchanged, §36C).
3. **Volume Pillar Option B — final, no automatic formula, resolved only via reviewed evidence (§36R).**
4. **Dedicated `BtmmVolumePillarStatus` (5 members, exact approved vocabulary) — final (§36H).**
5. **Reviewed-evidence input contract `BtmmReviewedEvidence` (15 fields, §36G2) — final.**
6. **Corrected `analyze_btmm` signature, with `reviewed_evidence` as a required parameter (§36AE) — final.**
7. **`BTMM_CONFIRMED` reachable through reviewed evidence (§36D/§36S/§36I5) — final, corrected from "structurally unreachable."**
8. **Reaction Gate resolution only after five confirmed candles, using the highest tier achieved in the full window (§36N) — final correction.**
9. **Initial primary state `BTMM_CANDIDATE`, and — corrected in this narrow pass — remains `BTMM_CANDIDATE` throughout its own entire creation availability group (§36I1/§36I2/§36AA2) — final, explicit.**
10. **`ENTERED_FORMING` is possible only in a later availability group than candidate creation, never the same one — corrected in this narrow pass from the prior "same processing step" trigger, which contradicted the same-group policy (§36I2) — requires explicit author sign-off on this corrected timing.**
11. **Exact deterministic trigger for `ENTERED_FORMING`: the first confirmed candle, in the source POI's own timeframe, whose `availability_time_utc` is strictly later than `BTMM_CANDIDATE`'s own (§36I2) — disclosed ENGINEERING-PROVISIONAL author gap-fill, requires explicit author sign-off.**
12. **A candidate genuinely invalidated before its own `ENTERED_FORMING` trigger transitions directly `BTMM_CANDIDATE → BTMM_CANCELLED`/`POI_REJECTED`, skipping `BTMM_FORMING` entirely (§36I2/§36I7, corrected from "not reachable") — final.**
13. **Explicit `BTMM_FORMING → BTMM_BLOCKED` (generic `BLOCKED`, reason-carrying) transition (§36I4) — final.**
14. **Explicit `BTMM_BLOCKED → BTMM_FORMING` (`RESUMED_FORMING`) transition, with idempotency guarantee (§36I4) — final.**
15. **State-transition idempotency guarantee (no repeated `BLOCKED`/`RESUMED_FORMING`/`ENTERED_FORMING` for an unchanged condition, §36I2/§36I4) — final.**
16. **`DIRECTIONAL_CONTINUATION` Outcome B (not deterministic, deferred, exact missing dependency stated, §36H4) — requires explicit author sign-off on the researched disposition.**
17. **Reviewed liquidity evidence is semantically separate from the final Liquidity Gate result in shape only where the approved vocabulary requires it — corrected in this narrow pass: a dedicated `BtmmLiquidityEvidenceStatus` (2 members: `PENDING`, `PRESENT`) is used for both the caller-supplied `BtmmReviewedEvidence.liquidity_evidence_status` field and the analyzer-computed `CurrentBtmmState.liquidity_evidence_status` field, replacing the withdrawn `BtmmGateStatus` reuse (§36H1) — requires explicit author sign-off on this corrected semantic model.**
18. **Exact same-group transition priority (`CANCELLED > CONFIRMED > BLOCKED > RESUMED_FORMING > ENTERED_FORMING`, §36AA2) — final.**
19. **New candidates cannot advance beyond `BTMM_CANDIDATE` in their creation group — corrected in this narrow pass from "beyond `BTMM_CANDIDATE`/`BTMM_FORMING`," a structural (not merely policy-level) guarantee (§36AA2 step 9) — final.**
20. **Fingerprint Option B — final, no shared serializer module, no completed analyzer modified (§36AC).**
21. **Four-way serializer equivalence test requirement (§36AC) — final.**
22. **Corrected 22-path scope (11 new source, 1 modified, 10 new test) — final, unconditional, unaffected by this narrow pass (§36AL).**
23. **Corrected 29-export surface (up from 28 in this narrow pass, adding `BtmmLiquidityEvidenceStatus`), recounted directly (§36AN) — final.**
24. **Exact revised 82-test plan, redistributed again across the same 10 files with literal names (§36AM) — final.**
25. **Inventory 147 → 168, creation order 147-167 — unaffected by this narrow pass, final (§36AL).**
26. `BtmmBlockedReason`'s omission of `MISSING_ATR`/`MISSING_PRICE_METADATA`, explicitly justified against implemented upstream behavior (§36H3) — final, unaffected by this narrow pass.
27. Every item retained unchanged from the prior correction's decision list (POI eligibility matrix, Accuracy/Reaction formula reuse, Pressure policy, Buy-to-Sell/Sell-to-Buy mapping, Structure exclusion, multi-timeframe policy, deterministic ordering, replay-equivalence procedure, evidence-classification policy, complexity policy, exclusion list) remains required as originally listed.

### 36AS. Status and Next Action (corrected twice — consolidated pass, then this narrow consistency pass — historical, superseded by §36AT)

**Status (historical — superseded by author approval, §36AT): `ARCHITECT-RECOMMENDED`, `AUTHOR-DECISION REQUIRED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** **Current status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** The consolidated correction pass resolved B1 (Reaction Gate timing), B2 (`BtmmVolumePillarStatus` vocabulary), B3 (reviewed-evidence input channel and `BTMM_CONFIRMED` reachability), B4 (`DIRECTIONAL_CONTINUATION` researched disposition), B5 (`BTMM_CANDIDATE → BTMM_FORMING` and `BTMM_FORMING ⇄ BTMM_BLOCKED` modeling), N1 (fingerprint Option B), N2 (`BtmmBlockedReason` disclosure), N3 (literal test names), N4 (tolerance-formula coincidence disclosed). The subsequent narrow consistency pass found and resolved two further issues introduced by that same correction: (1) an internal contradiction between `ENTERED_FORMING`'s stated same-step trigger and the same-group policy's requirement that a new candidate cannot advance beyond `BTMM_CANDIDATE` in its own creation group — resolved by moving `ENTERED_FORMING` to a structurally later availability group (§36I2/§36AA2); (2) a semantic conflation of the caller-supplied reviewed-liquidity-evidence input fact with the generic 3-value gate-status enum, previously justified by an explicitly admitted arithmetic-convenience motive — resolved by introducing a dedicated, minimally-scoped `BtmmLiquidityEvidenceStatus` enum grounded only in textually-attested vocabulary (§36H1), which genuinely changes the export count to 29. **This twice-corrected architecture has now been explicitly author-approved in full — see §36AT.** Nothing in this section is implemented, staged, committed, or pushed by this section.

### 36AT. Author Approval Record

**Author decision: `APPROVED`.** The author explicitly approved the corrected `1B-K-BTMM` BTMM Manipulation Lifecycle Foundation architecture exactly as documented (§36A–§36AS, including both the consolidated correction and the subsequent narrow consistency correction), with no modification to any corrected element. **Approved status: `AUTHOR-APPROVED`, `APPROVED FOR CONTROLLED IMPLEMENTATION`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`.** The corrected architecture received audit verdict **A — CORRECTED — READY FOR AUTHOR REVIEW** from the prior narrow consistency correction, and is now explicitly author-approved on that basis.

**Exact approved implementability matrix:** 12 total pattern components — **10 IMPLEMENTABLE** (POI Gate; Accuracy Gate; Reaction Gate; Reaction-Speed Gate; Formation-Timeframe Gate; Liquidity-after-POI rule-based evidence; POI-invalidation inheritance; Context Gate through reviewed evidence; Volume Pillar Gate through reviewed evidence; full Liquidity Gate through reviewed evidence), **2 DEFERRED** (Accumulation/Distribution; Approach Speed), **0 BLOCKED**. This approval authorizes implementation of rows 1-10 only — no public automatic accumulation, distribution, or approach-speed behavior is authorized.

**Exact approved scope:** 22 total affected paths (21 new, 1 modified); 11 new source files (new top-level package `btmm/`, including `reviewed_evidence.py`); 10 new test files; 1 modified existing source file (`src/btmm_ai_scanner/domain/enums.py`, +3 `DerivedOutputType` members: `BTMM_OBSERVATION`, `BTMM_LIFECYCLE_TRANSITION`, `CURRENT_BTMM_STATE`); new-path split 11 source/10 test; affected-path split 12 source/10 test; 82 new top-level test functions (582 combined with the existing 500); 29 public `btmm/__init__.py` exports; inventory 147 → 168 under batch tag `1B-K-BTMM`, creation order 147-167; no dependency change; no lockfile change; no existing `market_data`/`domain`/`structure`/`poi` analyzer file modified (fingerprint Option B, §36AC — no completed analyzer reopened).

**The author approved, without modification, every decision group recorded in §36AR (37 numbered items), including in particular:** the corrected deterministic input boundary with `StructureAnalysis` entirely absent (§36B/§36F); the generic `BtmmDirection`-plus-`source_poi_type` taxonomy with no separate `BtmmPatternType` (§36C); the exact 18 BTMM-eligible/2 CONTEXT-ONLY/12 NOT_APPLICABLE POI-eligibility split, identical to `1B-J-POI`'s own lifecycle-eligibility partition (§36J); the corrected public API with `reviewed_evidence` as a required parameter (§36AE); the `BtmmReviewedEvidence` input contract, 15 fields, no engine-generated `DerivedOutput` identity (§36G2); the dedicated `BtmmVolumePillarStatus` (5 members) and `BtmmLiquidityEvidenceStatus` (2 members) enums, each grounded only in textually-attested vocabulary, replacing the withdrawn generic-enum reuse (§36H/§36H1); Volume Pillar Option B, with automatic-formula Option A permanently removed from consideration (§36R); genuine `BTMM_CONFIRMED` reachability through caller-supplied reviewed evidence, with a reviewed-evidence record never directly setting `BTMM_CONFIRMED` (§36D/§36S/§36I5); the corrected Reaction Gate timing, resolving only at the fifth confirmed reaction candle using the highest tier achieved across the full window, with no repainting (§36N); the explicit initial `primary_state = BTMM_CANDIDATE`/`formation_stage = None` (§36I1); the corrected `ENTERED_FORMING` timing, structurally confined to a later availability group than candidate creation, with duplicate-suppression via stable semantic identity and direct `BTMM_CANDIDATE → BTMM_CANCELLED` cancellation before entering `FORMING` (§36I2); the exact closed transition table covering every state pair (§36I7); the `BTMM_FORMING ⇄ BTMM_BLOCKED` loop with explicit idempotency (§36I4); the corrected 8-member `BtmmCancellationReason`, with `DIRECTIONAL_CONTINUATION` and `MANUAL_REVIEW_REJECTED` researched and explicitly deferred as Outcome B (§36H4); the exact 10-step same-availability-group processing order with explicit transition priority and the structural (not merely policy) guarantee against same-group create-and-form/create-and-confirm (§36AA2); the exact reused Ambiguity 8/9 interaction-and-overshoot and reaction formulas, kept strictly separate from POI-lifecycle breach/reclaim computation (§36K/§36N); the `GENUINE_INVALIDATION_CONFIRMED → BTMM_CANCELLED/POI_REJECTED` inheritance rule (§36Z); pressure as inherited contextual evidence only (§36O); fingerprint Option B, a fourth local private serializer duplicate with mandatory four-way equivalence testing, no completed analyzer reopened (§36AC); the uniform `ENGINEERING_PROVISIONAL` evidence-classification policy (§36AD); the exact corrected 15-field `BtmmObservation`, 16-field `BtmmLifecycleTransition`, 33-field `CurrentBtmmState`, and 15-field `BtmmReviewedEvidence` contracts (§36V-§36X/§36G2); the exact corrected 29-name export list (§36AN); the exact corrected 82-test plan and per-file distribution (§36AM); the exact 22-path file scope with creation order 147-167 (§36AL); and the complete exclusion list (§36AP).

**This approval authorizes exactly one complete implementation cycle** covering all 22 approved paths at once (no per-file decision groups), implementing rows 1-10 of the approved implementability matrix only, followed by one final architectural audit and, only if a genuine defect is found, at most one correction cycle. **This approval does not authorize production use. Implementation has not started — this remains a documentation-only approval.**
