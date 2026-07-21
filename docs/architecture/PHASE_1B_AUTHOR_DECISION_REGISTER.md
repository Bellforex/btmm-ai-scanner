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

**Partially resolved:**
- **BB-3** — SemVer implementation strategy: **dependency strategy resolved** (no external package; project-owned type in `contracts/types.py`); **grammar, parsing, and comparison behavior remain unresolved** (Section 19E).
- **BB-4** — Base Pydantic model strategy: **Pydantic use resolved** (Pydantic v2, dataclass placeholders rejected); **exact model configuration** (`frozen`, `extra`, strict validation, etc.) **remains unresolved** (Section 19A; see also the prior audit's Part 7 findings).

**No other BB decision is marked resolved by this section.** BB-7 through BB-11, BB-14, and BB-15 remain exactly as previously reported in the Phase 1B-B Core Foundation Contracts Scope Audit.
