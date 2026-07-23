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
