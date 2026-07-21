# Repository Scaffold Plan

**Document status:** ENGINEERING-RECOMMENDED planning document. This is a **proposed directory plan only**. No directory described here is created by this document, except `docs/architecture/` (already created to hold this and its sibling planning documents). Nothing here is implemented.

---

## 1. Purpose

Propose the future top-level repository structure that would implement the layers defined in `docs/architecture/PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md`, for author review before Phase 1B scaffold creation.

## 2. Proposed Top-Level Structure

```
btmm-ai-scanner/
├── docs/                     (existing)
├── knowledge/                (existing — untouched by this plan)
├── references/               (existing — untouched by this plan)
├── src/                      (proposed, Phase 1B)
│   └── btmm_ai_scanner/         (proposed application package)
│       ├── config/
│       ├── contracts/
│       ├── ingestion/
│       ├── normalization/
│       ├── measurements/
│       ├── domain/
│       ├── poi/
│       ├── lifecycle/
│       ├── btmm/
│       ├── annotations/
│       ├── provenance/
│       ├── validation/
│       ├── replay/
│       └── audit/
├── tests/                    (proposed, Phase 1B)
│   ├── fixtures/
│   ├── unit/
│   ├── integration/
│   └── replay/
├── scripts/                  (proposed, Phase 1B — operator-run utility scripts only)
├── migrations/                (proposed, deferred — only once a database is adopted per Decision Gate #6)
└── .github/                  (proposed, Phase 1B — CI workflow only, per Decision Gate #20)
```

## 3. Per-Directory Documentation

For each proposed directory: purpose, what may live there, what must not live there, allowed dependency direction, and whether creation is recommended in Phase 1B.

### `src/btmm_ai_scanner/config/`
- **Purpose:** Symbol/provider/timeframe enums, environment settings, active rule/schema version pointers.
- **May contain:** config loader code, config schema, environment-variable mapping.
- **Must not contain:** trading rules, POI logic, secrets in plain text.
- **Allowed dependency direction:** none (lowest layer; nothing below it).
- **Phase 1B creation:** Recommended.

### `src/btmm_ai_scanner/contracts/`
- **Purpose:** Data-contract definitions (Raw Candle, Normalized Candle, POI Record, etc. — the executable form of `DATA_CONTRACTS_AND_SCHEMA_PLAN.md`).
- **May contain:** schema/type definitions, schema-version manifest.
- **Must not contain:** business logic, I/O code.
- **Allowed dependency direction:** `config` only.
- **Phase 1B creation:** Recommended (contract definitions only, no executable validation logic required in 1B itself unless the author approves the schema-validation technology in Decision Gate #3).

### `src/btmm_ai_scanner/ingestion/`
- **Purpose:** Raw Data Ingestion Boundary — accepts external market data, writes immutable Raw Candle Records.
- **May contain:** provider-adapter code (once a provider/API is author-approved), raw-record writers.
- **Must not contain:** normalization logic, POI logic, validity decisions of any kind. **Ingestion code must never decide POI validity.**
- **Allowed dependency direction:** `contracts`, `config` only.
- **Phase 1B creation:** Directory only, no adapter implementation (Decision Gate #13 — "ingestion-adapter boundary" — requires more research and is not resolved by Phase 1A).

### `src/btmm_ai_scanner/normalization/`
- **Purpose:** Converts Raw Candle Records into Normalized Candle Records.
- **May contain:** timezone conversion, OHLC canonicalization, confirmed-candle flagging.
- **Must not contain:** measurement formulas, POI logic.
- **Allowed dependency direction:** `contracts`, `config`, `ingestion` (read-only).
- **Phase 1B creation:** Recommended (directory + interface stub only).

### `src/btmm_ai_scanner/measurements/`
- **Purpose:** Implements the already-Author-Approved formulas from `knowledge/MEASUREMENT_STANDARDS.md`.
- **May contain:** Candle Measurement Standard V1, Small Candle Standard V1, Volume/Momentum Proxy Standard V1, Market Speed Standard V1, POI Zone Interaction Standard V1 implementations — nothing beyond what is Author-Approved.
- **Must not contain:** any new, un-approved formula; POI or BTMM logic.
- **Allowed dependency direction:** `normalization` (read-only), `config`.
- **Phase 1B creation:** Directory only, no formula implementation in 1B.

### `src/btmm_ai_scanner/domain/`
- **Purpose:** Meaningful Swing, Trendline, Support/Resistance entities.
- **May contain:** swing-detection, trendline-candidate, support/resistance-zone logic per the already-approved standards.
- **Must not contain:** HH/HL/LH/LL/BOS/CHoCH (formally deferred, `P0G-B003`); any automated Equal High/Low or Trendline specialized lifecycle (formally deferred, `P0G-B004`/`P0G-B005`).
- **Allowed dependency direction:** `measurements`, `config`.
- **Phase 1B creation:** Directory only, no logic implementation in 1B.

### `src/btmm_ai_scanner/poi/`
- **Purpose:** The 36 POI type representations and their formation/boundary rules.
- **May contain:** POI record construction per each POI's approved specification.
- **Must not contain:** trade placement of any kind. **POI detectors must never place trades.**
- **Allowed dependency direction:** `domain`, `measurements`, `config`.
- **Phase 1B creation:** Directory only, no detector implementation in 1B.

### `src/btmm_ai_scanner/lifecycle/`
- **Purpose:** The shared Boundary Breach/Reclaim/Invalidation lifecycle (18 propagated POIs) and the descriptive Freshness/Age standard.
- **May contain:** implementations of `knowledge/poi_lifecycle/POI_BOUNDARY_BREACH_RECLAIM_INVALIDATION.md` and `POI_FRESHNESS_AND_AGE_STANDARD.md`, exactly as approved.
- **Must not contain:** any mitigation percentage/state, any automatic age-expiration threshold, any repeated-tap degradation formula (all remain undefined/deferred).
- **Allowed dependency direction:** `poi`, `config`.
- **Phase 1B creation:** Directory only, no logic implementation in 1B.

### `src/btmm_ai_scanner/btmm/`
- **Purpose:** Future BTMM setup evaluation against the state machine in `knowledge/btmm/BTMM_STATE_MACHINE.md`.
- **May contain:** BTMM state machine implementation, once approved for implementation.
- **Must not contain:** entry, stop-loss, take-profit, position-sizing, or risk logic.
- **Allowed dependency direction:** `poi`, `lifecycle`, `annotations`, `config`.
- **Phase 1B creation:** Directory only, no logic implementation in 1B.

### `src/btmm_ai_scanner/annotations/`
- **Purpose:** Manual expert label capture (`context_input_source`, `liquidity_event_source`, `trendline_event_source`, all `= MANUAL_EXPERT_LABEL`).
- **May contain:** annotation record construction, reviewer-identity capture.
- **Must not contain:** any representation of a manual label as automatic detection.
- **Allowed dependency direction:** `domain`, `poi`, `config`.
- **Phase 1B creation:** Recommended (directory + record shape only — this is one of the explicitly permitted controlled-foundation categories).

### `src/btmm_ai_scanner/provenance/`
- **Purpose:** Cross-cutting lineage tracking for every record in every layer.
- **May contain:** provenance-record construction and lookup.
- **Must not contain:** business/trading logic.
- **Allowed dependency direction:** `config` only; depended upon by every layer above it.
- **Phase 1B creation:** Recommended.

### `src/btmm_ai_scanner/validation/`
- **Purpose:** Cross-cutting data-quality and schema-conformance checks.
- **May contain:** OHLC consistency checks, duplicate/missing/out-of-order candle detection, provider/symbol/timeframe checks.
- **Must not contain:** POI or BTMM validity decisions (data-quality validity and trading validity are different concepts — see `PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md`).
- **Allowed dependency direction:** `contracts`, `config`.
- **Phase 1B creation:** Recommended.

### `src/btmm_ai_scanner/replay/`
- **Purpose:** Historical replay engine — re-runs the pipeline against pinned raw data and pinned rule/schema versions.
- **May contain:** replay orchestration, pinned-version resolution.
- **Must not contain:** any write path back into live/raw records.
- **Allowed dependency direction:** every layer through `poi`/`lifecycle`, read-only.
- **Phase 1B creation:** Directory only, no engine implementation in 1B.

### `src/btmm_ai_scanner/audit/`
- **Purpose:** Aggregates audit events into reviewable reports.
- **May contain:** audit-event aggregation, reporting.
- **Must not contain:** trading-signal generation.
- **Allowed dependency direction:** `provenance`, `validation`.
- **Phase 1B creation:** Recommended.

### `tests/fixtures/`
- **Purpose:** Deterministic synthetic candle sequences (see `DETERMINISTIC_TESTING_AND_FIXTURE_PLAN.md`).
- **May contain:** hand-authored positive/negative/near-miss/boundary/ambiguous fixture data.
- **Must not contain:** private-book content, book screenshots, or anything presented as market-performance evidence.
- **Allowed dependency direction:** `contracts` only.
- **Phase 1B creation:** Directory only; no fixture files created by Phase 1A or 1B per this task's own instruction.

### `tests/unit/`, `tests/integration/`, `tests/replay/`
- **Purpose:** The test hierarchy described in `DETERMINISTIC_TESTING_AND_FIXTURE_PLAN.md`.
- **May contain:** test code exercising each layer.
- **Must not contain:** live network calls to any real provider in unit/integration tests.
- **Allowed dependency direction:** test code may depend on any `src/` layer it is testing, one-directionally (never the reverse).
- **Phase 1B creation:** Directory only, no test files in Phase 1A.

### `scripts/`
- **Purpose:** Operator-run utility scripts (e.g., manual replay trigger, manual annotation import) — never part of the runtime pipeline itself.
- **May contain:** CLI entry points for human operators.
- **Must not contain:** scheduled/autonomous trading logic.
- **Allowed dependency direction:** may depend on any `src/` layer; nothing may depend on `scripts/`.
- **Phase 1B creation:** Directory only.

### `migrations/`
- **Purpose:** Database schema migrations, only once a database is adopted (Decision Gate #6, currently DEFERRED).
- **May contain:** migration scripts, once a database and migration tool are author-approved.
- **Must not contain:** anything, until a database exists.
- **Allowed dependency direction:** N/A until created.
- **Phase 1B creation:** **Not recommended in Phase 1B** — deferred until a database is actually adopted.

### `.github/`
- **Purpose:** CI workflow definitions (Decision Gate #20).
- **May contain:** lint/type-check/deterministic-test workflow, once CI policy is author-approved.
- **Must not contain:** secrets in plain text, deployment/execution automation.
- **Allowed dependency direction:** N/A (external to the dependency graph).
- **Phase 1B creation:** Recommended, once Decision Gate #20 is approved.

## 4. Dependency-Direction Diagram

**Arrow legend for this diagram only: `A --> B` means "A depends on B"** (A's module is permitted to call/import B's module). This is the **opposite** direction from the runtime data-flow diagram in `docs/architecture/PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md`, Section 9 (whose legend states `A → B` means "data produced by A flows into B"). For example: `normalization --> ingestion` below means normalization *depends on* ingestion, while the Section 9 data-flow diagram correctly shows data flowing the other way, from Ingestion to Normalization. Both diagrams are internally consistent; do not read one diagram's arrows using the other diagram's meaning.

```mermaid
flowchart TD
    config[config] 
    contracts[contracts] --> config
    ingestion[ingestion] --> contracts
    ingestion --> config
    normalization[normalization] --> contracts
    normalization --> config
    normalization -.read-only.-> ingestion
    validation[validation] --> contracts
    validation --> config
    measurements[measurements] --> normalization
    measurements --> config
    domain[domain] --> measurements
    domain --> config
    poi[poi] --> domain
    poi --> measurements
    poi --> config
    lifecycle[lifecycle] --> poi
    lifecycle --> config
    annotations[annotations] --> domain
    annotations --> poi
    annotations --> config
    btmm[btmm - future] --> poi
    btmm --> lifecycle
    btmm --> annotations
    btmm --> config
    provenance[provenance] --> config
    audit[audit] --> provenance
    audit --> validation
    replay[replay - read-only] -.read-only.-> poi
    replay -.read-only.-> lifecycle
    replay -.read-only.-> normalization
    replay -.read-only.-> measurements
    replay -.read-only.-> domain

    subgraph future["Future — NOT implemented"]
        detector_iface[Future Detector Interface]
        ai_iface[Future AI Interface]
        exec_boundary[Future Signal/Execution Boundary]
    end
    detector_iface -.interface only.-> poi
    detector_iface -.interface only.-> lifecycle
    ai_iface -.interface only, read-only.-> poi
    ai_iface -.interface only, read-only.-> lifecycle
    ai_iface -.interface only, read-only.-> annotations
    exec_boundary -.interface only, read-only.-> btmm
```

**No arrow may point upward or backward relative to this diagram** — this is the mechanism that prevents circular dependencies and prevents the specific prohibited couplings below.

**Proposed dependency-resolution (topological) order** — each module may be built only after every module it depends on, reading left to right:

```
config
  → contracts, provenance
    → ingestion, validation
      → normalization
        → measurements
          → domain
            → poi
              → lifecycle, annotations
                → audit
                  → btmm (future)
                    → replay (read-only)
                      → detector_iface, ai_iface (interface only)
                        → exec_boundary (interface only, read-only)
```

**Confirmed acyclic:** every dependency arrow in the diagram above points to a module that appears strictly earlier in this ordering; no module depends, directly or transitively, on anything that depends on it. No circular dependency exists in this proposal.

## 5. Explicitly Prevented Couplings

The proposed structure and dependency direction must make each of the following structurally impossible, not merely discouraged by convention:

- **Ingestion code deciding POI validity** — `ingestion/` has no dependency path to `poi/` or `lifecycle/` at all (dependencies point the opposite direction).
- **POI detectors placing trades** — `poi/` has no dependency path to any execution boundary; the execution boundary is a separate, currently-nonexistent, read-only-consumer subsystem.
- **AI modules modifying raw data** — the Future AI Interface is read-only and has no write path into `ingestion/`, `normalization/`, or any earlier layer.
- **Entry logic redefining POI validity** — no entry logic exists yet; when it does, it must consume BTMM/POI validity as read-only input, never write back into `poi/` or `lifecycle/`.
- **Trade outcome retroactively changing setup validity** — matches the already-approved no-retroactive-rewriting rule; the future execution/outcome boundary is append-only and one-directional (reads BTMM validity, never writes back).
- **Manual labels masquerading as automatic detection** — `annotations/` and any future automatic-detector module are structurally separate directories with separate, mutually exclusive source tags (Section 10 of the architecture document); nothing may merge them.
- **Future execution adapters bypassing risk controls** — the execution boundary does not exist yet. When built, it must *depend on* a separate, explicitly author-approved **Future Risk-Control Interface** (a deferred sub-boundary of the Future Signal and Execution Boundary, `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` SS7.16 — not a 17th logical layer of its own) and must never bypass that interface by calling `btmm/` or `poi/` directly. The risk-control interface itself remains entirely unimplemented and out of scope for Phase 1A/1B; in any diagram it is shown only as an isolated, deferred prerequisite, never connected to an active execution path, since no execution path exists yet.
- **Private-book content entering application packages or commits** — `references/private/` remains outside `src/`, outside `tests/fixtures/`, and remains `.gitignore`-protected; no proposed directory reads from it.

## 6. Phase 1B Creation Recommendation Summary

| Directory | Recommended in Phase 1B |
|---|---|
| `src/btmm_ai_scanner/config/` | Yes |
| `src/btmm_ai_scanner/contracts/` | Yes (contract definitions only) |
| `src/btmm_ai_scanner/ingestion/` | Directory only, no adapter |
| `src/btmm_ai_scanner/normalization/` | Directory + interface stub only |
| `src/btmm_ai_scanner/measurements/` | Directory only |
| `src/btmm_ai_scanner/domain/` | Directory only |
| `src/btmm_ai_scanner/poi/` | Directory only |
| `src/btmm_ai_scanner/lifecycle/` | Directory only |
| `src/btmm_ai_scanner/btmm/` | Directory only |
| `src/btmm_ai_scanner/annotations/` | Yes (record shape only) |
| `src/btmm_ai_scanner/provenance/` | Yes |
| `src/btmm_ai_scanner/validation/` | Yes |
| `src/btmm_ai_scanner/replay/` | Directory only |
| `src/btmm_ai_scanner/audit/` | Yes |
| `tests/fixtures/` | Directory only, no fixture files |
| `tests/unit/`, `tests/integration/`, `tests/replay/` | Directory only, no test files |
| `scripts/` | Directory only |
| `migrations/` | Not recommended (deferred) |
| `.github/` | Recommended once Decision Gate #20 approved |

## 7. Approval Status

**ENGINEERING-RECOMMENDED**, pending author review. This document creates no directory except `docs/architecture/` (already present). No directory listed above is created by this task.

## 8. Post-Phase 1A Approved Scaffold Constraints (Decision Groups 1–8)

**Author approval of the following constraints does not create any directory or file described in this document.** Full decision detail (recommendation origin, author-decision status, implementation status, production status) is recorded canonically in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`; this section records only how those approved decisions constrain the scaffold proposed above, once a separate, explicit scaffold-implementation instruction is given.

Approved constraints on the eventual scaffold:

- **Toolchain (Group 1):** Python 3.12 (one pinned patch version); uv as package manager; `pyproject.toml` as the central manifest; `uv.lock` as the committed reproducibility lockfile; Pydantic v2; pytest; mypy; Ruff (formatter and linter).
- **Storage (Group 2):** Parquet for bulk tabular historical records and JSONL for append-only event/audit streams, kept in explicitly separated roles; no initial database (`src/btmm_ai_scanner/` contracts remain file-based); no initial `migrations/` implementation.
- **Ingestion boundary (Groups 3, 7):** `src/btmm_ai_scanner/ingestion/` exposes only a provider-neutral `MarketDataSourcePort` interface (`INTERFACE_ONLY`); early retrieval is restricted to `OFFLINE_FILE` mode; no provider-specific adapter (FXCM, TradingView, or otherwise) and no live connection of any kind.
- **Future Risk-Control Interface:** remains deferred, exactly as stated in Section 5 above and in `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` SS7.16 — unaffected by this decision round.
- **Manifests (Group 8):** the approved future scaffold destinations `manifests/rules/` and `manifests/schemas/` are confirmed as the eventual homes for rule-version and schema-version manifests. **No file is created in either directory by this task.**
- **No containers:** no `Dockerfile`, `docker-compose.yml`, or container-specific assumption is introduced into this plan by these decisions.

**These constraints refine which options within the existing Section 2–6 proposal are now author-approved; they do not add a new proposed directory, and they do not authorize creating any directory or file.** The exact scaffold file set (including `manifests/rules/` and `manifests/schemas/`) remains subject to a separate, explicit implementation-review task before any file is created.

## 9. Phase 1B Exact Scope Planning

**No scaffold has been created by this section.** The exact, file-level implementation scope proposed against this plan is now recorded canonically in `docs/architecture/PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` — this section only cross-references that document; it does not restate its content.

- **Exact-scope document:** `docs/architecture/PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` — defines a 50-changed-path inventory (49 files + 1 modified existing file, `.gitignore`) across six proposed implementation batches (1B-A through 1B-F), each mapped to this plan's directory structure (Sections 1–8 above, now using the author-approved `src/btmm_ai_scanner/` package path throughout).
- **Exact implementation batches remain pending author approval.** Batch boundaries (Toolchain and Package Shell; Core Foundation Contracts; Validation and Eligibility Foundation; Audit and Operational Logging Foundation; Provider-Neutral Ingestion Boundary; CI Foundation) are proposed only.
- **Package identity and layout are now `AUTHOR-APPROVED`** (Phase 1B-0 Package Identity and Layout decision): distribution name `btmm-ai-scanner`; import package `btmm_ai_scanner`; source-package path `src/btmm_ai_scanner/`; `src` layout (not flat layout). **Note:** this plan's own Section 2 illustrative tree, and every per-directory heading in Section 3, previously showed `src/btmm_scanner/` (without `_ai_`); that stale reference has now been corrected throughout this document to `src/btmm_ai_scanner/`.
- **`uv_build` is now `AUTHOR-APPROVED` as the build backend, constrained as `uv_build>=0.11.30,<0.12`.** (Previously unresolved; `hatchling` and `setuptools` were considered and not chosen.)
- **`0.1.0` is now `AUTHOR-APPROVED` as the initial project version.**
- **`.python-version` inclusion in Batch 1B-A is now `AUTHOR-APPROVED`, with exact content `3.12.13` also now `AUTHOR-APPROVED`.** It is no longer optional, conditional, or content-unresolved.
- **Python `3.12.13` is `AUTHOR-APPROVED` as the exact project interpreter** (Phase 1B-A Runtime and Dependency Baseline). **uv-managed Python is permitted and preferred.** The Phase 1B-A Runtime and Dependency Environment Audit discovered the only locally installed Python is `3.14.6` — that installation **remains untouched** and **must not** be used as the project runtime; Python 3.12.13 will be installed separately, through `uv`, only during an explicitly approved implementation task.
- **`uv == 0.11.30` is `AUTHOR-APPROVED`** as the required tool version (`[tool.uv] required-version = "==0.11.30"`).
- **`requires-python = ">=3.12,<3.13"` is `AUTHOR-APPROVED`.**
- **Batch 1B-A has no third-party runtime dependency** — `AUTHOR-APPROVED` as `NONE`. `config/enums.py` and `config/loader.py` remain standard-library-only in this batch (no YAML, no Pydantic, no `pydantic-settings`); Pydantic remains approved for executable contracts beginning in Batch 1B-B only.
- **Batch 1B-A development-dependency constraints are `AUTHOR-APPROVED`:** `pytest>=9.1.1,<10`; `mypy>=2.3.0,<3`; `ruff>=0.15.22,<0.16`.
- **Metadata baseline is `AUTHOR-APPROVED`.** The full future `[project]` field set — `name`, `version`, `description`, `authors`, `requires-python`, `dependencies`, `license`, `classifiers` — is resolved (see `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 9a for the exact TOML content). `readme`, `license-files`, `maintainers`, `keywords`, `project.urls`, `project.scripts`, entry points, `dynamic` metadata, and `optional-dependencies` are explicitly **omitted from Batch 1B-A by decision**, not by gap.
- **Licence expression is `AUTHOR-APPROVED`: `LicenseRef-Proprietary`.** README and licence files are omitted from Batch 1B-A — no `README.md`, `LICENSE`, or `LICENCE` file is proposed for this batch.
- **Approved classifiers are limited to exactly six values:** `Development Status :: 2 - Pre-Alpha`; `Intended Audience :: Developers`; `Programming Language :: Python :: 3`; `Programming Language :: Python :: 3 :: Only`; `Programming Language :: Python :: 3.12`; `Private :: Do Not Upload`. No deprecated License classifier, operating-system classifier, public-release classifier, or production-readiness/trading-profitability/AI-performance/financial-product claim is included.
- **Windows 11 x64 is the validated initial development environment.** Cross-platform (Linux/macOS) compatibility remains **unclaimed** — Batch 1B-A uses only portable Python standard-library functionality (no Windows-only filesystem assumptions, no registry access, no COM integration, no shell-specific implementation), but OS-independence is not asserted before it is actually tested.
- **`InternalSymbol` and `Timeframe` are the only initial configuration enums**, `AUTHOR-APPROVED`: `InternalSymbol` = `XAUUSD`/`EURUSD`/`GBPUSD`; `Timeframe` = `M1`/`M5`/`M15`/`H1`/`H3`/`H4`/`D1`/`W1`, both as `StrEnum`. No POI-type, lifecycle-state, BTMM-state, or validation-state enum is introduced in Batch 1B-A.
- **The configuration loader remains standard-library-only**, `AUTHOR-APPROVED`. Environment prefix `BTMM_CONFIG_`; three-level precedence (project defaults → environment-specific non-secret overrides → runtime environment overrides, later overrides earlier); **shallow, deterministic merging only** (no nested/deep merge); rejects secret-like keys (`password`, `secret`, `token`, `credential`, `api_key`, `private_key`); never reads `.env`; never returns, logs, or defaults credential values.
- **Test boundaries are `AUTHOR-APPROVED`** for `tests/test_import_smoke.py` and `tests/test_config_precedence.py` — full detail in `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 23a. Neither test enters detector, ingestion, lifecycle, AI, signal, risk, or execution scope.
- **`.gitignore` joins Batch 1B-A**, `AUTHOR-APPROVED`, as a **modified existing file** (not a new file) — preserving `references/private/*` and adding Python/uv/test/type-check/Ruff/coverage/build exclusions, without ignoring `pyproject.toml`, `uv.lock`, `.python-version`, source code, tests, reviewed configuration, or reviewed manifests. **`.gitignore` is not modified by this documentation task.**
- **No empty placeholder directories will be created.** Consistent with this plan's existing per-directory documentation (Section 3) and the conservative-scaffold principle in the exact-scope document: a directory is proposed for creation only when at least one reviewed file will exist inside it. `measurements/`, `domain/`, `poi/`, `lifecycle/`, `btmm/`, `annotations/`, `replay/`, `scripts/`, `migrations/`, and `manifests/` remain correctly absent from the near-term proposed scope.
- **No scaffold has been created and no implementation has occurred.** No `src/`, `pyproject.toml`, `uv.lock`, `.python-version`, or any package file exists as a result of any decision recorded here or in this document. No Python, uv, or package was installed. `.gitignore` remains unmodified.
- **Batch 1B-A's earlier nine-file scope is now superseded — it contains exactly ten changed paths (nine new files + one modified existing file, `.gitignore`), and remains unapproved for execution.** Package identity, layout, build backend (including its exact version constraint), initial version, `.python-version` (inclusion and content), the interpreter, `uv`'s required version, `requires-python`, the zero-runtime-dependency baseline, the development-dependency constraints, the full metadata field set, the minimum-OS position, and the license-field position are all now resolved, per `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 6. **Each batch requires separate review and commit** — no batch may be implemented, and no batch's files created, until the author has separately approved every remaining blocking decision relevant to that batch.
- **Package root content is `AUTHOR-APPROVED`:** `src/btmm_ai_scanner/__init__.py` contains only a module docstring (`"""Deterministic software foundation for the BTMM and POI AI scanner."""`) — no `__version__`, no re-exports, no import-time side effects. `pyproject.toml` remains the authoritative version source.
- **Configuration exports are `AUTHOR-APPROVED`:** `config/__init__.py` re-exports exactly `ENV_PREFIX`, `ConfigurationError`, `InternalSymbol`, `InvalidConfigurationKeyError`, `SecretConfigurationKeyError`, `Timeframe`, `load_configuration` — no other public configuration API.
- **Enum implementation is `AUTHOR-APPROVED`:** exact `StrEnum` code for `InternalSymbol` and `Timeframe`, per `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 17a.
- **Exception hierarchy is `AUTHOR-APPROVED`:** `ConfigurationError(ValueError)` → `InvalidConfigurationKeyError`, `SecretConfigurationKeyError`, with fixed generic messages that never expose a rejected key or value.
- **Loader signature and behavior are `AUTHOR-APPROVED`:** `load_configuration(project_defaults, environment_overrides, *, environ=None) -> dict`; three-layer precedence; shallow merge; `BTMM_CONFIG_` normalization; secret-key rejection — full detail in Section 17b/17c.
- **Ruff configuration is `AUTHOR-APPROVED`:** `target-version = "py312"`, `line-length = 88`, `select = ["E4", "E7", "E9", "F", "I", "UP", "B", "RUF"]` — no preview rules, no ignores, no per-file exemptions.
- **mypy configuration is `AUTHOR-APPROVED`:** `python_version = "3.12"`, `strict = true`, `warn_unused_configs = true`, `show_error_codes = true`, `pretty = true` — no `ignore_missing_imports`, no plugin, no per-module relaxation.
- **pytest configuration is `AUTHOR-APPROVED`:** `minversion = "9.1"`, `testpaths = ["tests"]`, `addopts` with `-ra`/`--strict-config`/`--strict-markers`/`--import-mode=importlib` — no coverage/network/async plugin, no custom markers.
- **Development dependency group is `AUTHOR-APPROVED`:** `pytest>=9.1.1,<10`; `mypy>=2.3.0,<3`; `ruff>=0.15.22,<0.16`; `[project].dependencies` remains empty.
- **Exact test-function boundaries are `AUTHOR-APPROVED`:** three named tests in `test_import_smoke.py`; eleven named tests in `test_config_precedence.py` — full list in `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 23a.
- **The installation sequence (Stages A–J) is `AUTHOR-APPROVED`:** repository preflight → install uv 0.11.30 → verify Python 3.12.13 availability → install managed Python (existing 3.14.6 untouched) → modify `.gitignore` → create the nine handwritten files → generate `uv.lock` → `uv sync --locked` → verification → git-scope verification. Full detail in `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 16a.
- **The rollback procedure is `AUTHOR-APPROVED`:** stop-and-report on any unexpected result; restore only `.gitignore`; delete only the nine new paths and generated `.venv/`; no `git reset --hard`/`git clean -fd(x)`/force push; installed uv/Python are not auto-removed. Full detail in Section 27a.
- **Acceptance criteria are `AUTHOR-APPROVED`:** the full exact checklist in `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 28a — including exactly ten changed paths, exact interpreter/tool versions, all four verification gates (Ruff format, Ruff lint, mypy, pytest) passing, and no secret exposure.
- **No implementation has occurred.** No `pyproject.toml`, `uv.lock`, `.python-version`, `src/`, or `tests/` exists. No Python, uv, or package was installed. `.gitignore` remains unmodified. **Batch 1B-A remains ten changed paths and remains not authorized for execution.** *(This bullet described the state at the time of that decision round. It is superseded by Section 10 below, which records that Batch 1B-A has since been implemented, verified, committed, and pushed.)*

This section does not replace or erase the original scaffold proposal in Sections 1–8 above — it only adds the exact-scope cross-reference and the current decision status.

## 10. Phase 1B-A Implementation Closure

- **Commit hash and message:** `47cfd699bb7f4893774579f1693abbbb57b91607` — "Implement Phase 1B-A software foundation".
- **Ten-path scope completed:** `.gitignore` (modified) plus nine new files (`.python-version`, `pyproject.toml`, `src/btmm_ai_scanner/__init__.py`, `src/btmm_ai_scanner/config/__init__.py`, `src/btmm_ai_scanner/config/enums.py`, `src/btmm_ai_scanner/config/loader.py`, `tests/test_config_precedence.py`, `tests/test_import_smoke.py`, `uv.lock`) — matching the previously documented plan exactly.
- **Package shell created:** `src/btmm_ai_scanner/__init__.py` (docstring only, no side effects).
- **Configuration enums and loader created:** `InternalSymbol`/`Timeframe` (`StrEnum`); `load_configuration` with the approved three-layer precedence, shallow merge, key validation, and secret-rejection boundary.
- **Test foundation created:** `test_import_smoke.py` (3 tests) and `test_config_precedence.py` (11 tests, 31 collected cases including parametrization) — 34 collected, 34 passed overall.
- **Lockfile created:** `uv.lock`, generated via `uv lock`, verified via `uv lock --check` (14 resolved packages, zero runtime dependencies, dev dependencies exactly `pytest==9.1.1`/`mypy==2.3.0`/`ruff==0.15.22`).
- **Project environment verified:** `uv sync --locked` created `.venv/` (git-ignored, absent from Git status); all four verification gates (Ruff format, Ruff lint, mypy, pytest) passed.
- **`.gitignore` updated:** approved Python/uv/test/type-check/Ruff/coverage/build exclusions added; `references/private/*` preserved unchanged; no source/test/config/manifest file newly ignored.
- **Runtime dependencies remain empty:** `[project].dependencies = []`, confirmed in both `pyproject.toml` and `uv.lock`.
- **Verification results passed:** all results recorded in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 18b and `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 31.

**Batch 1B-A status: `IMPLEMENTED`. `VERIFIED`. `COMMITTED`. `PUSHED`. `NOT PRODUCTION-APPROVED`.**

**Batch 1B-A is closed. Batches 1B-B through 1B-F remain `NOT YET IMPLEMENTED`; Batch 1B-B has not started.** The procedural exception governing this closure (two in-scope test-file fixes made without pausing for separate re-authorization, subsequently disclosed via forensic review and accepted by explicit author exception) and the external, non-blocking Python minor-version alias anomaly are recorded in full in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Sections 18c–18d — neither is hidden or minimized here.

## 11. Phase 1B-B Decision Group 1 — Approved Dependency and Value-Type Boundary

**Does not alter the Phase 1B-A closed status above.** Batch 1B-A remains `IMPLEMENTED`, `VERIFIED`, `COMMITTED`, `PUSHED`, `NOT PRODUCTION-APPROVED`, `CLOSED`.

- **Pydantic bounded dependency approved:** `pydantic>=2.13.4,<2.14`.
- **Dependency not yet added.** `pyproject.toml` and `uv.lock` remain unchanged by this documentation task.
- **Pydantic contract models required.** Plain-dataclass placeholder contracts are rejected.
- **UUIDv7 validation-only strategy:** Batch 1B-B validates caller-supplied UUIDv7 identities; it does not generate them. No external UUIDv7 package is approved.
- **SHA-256 validation-only strategy:** `SHA256Fingerprint` validates exactly 64 lowercase hexadecimal characters; no fingerprint calculation occurs in Batch 1B-B.
- **No canonical-JSON library approved.** No SemVer package approved — a project-owned `SemVer` value type is planned for `contracts/types.py` instead, with exact grammar/parsing/comparison still unresolved.
- **No JSON Schema file export in Batch 1B-B.** Pydantic models remain the source of truth; any generated schema export is a later, explicitly scoped batch's concern.
- **Manifest contracts remain shape-only** — no manifest file writing, loading, persistence, or supersession mechanism; no `manifests/` directory is created.
- **Current provisional scope = 15 changed paths** (13 inventoried files + `pyproject.toml` + `uv.lock`). **Final scope remains unresolved** pending author decision on two candidate test files (`test_validation_result.py`, `test_provenance_record.py`), neither yet added to the inventory.
- **Batch 1B-B remains unimplemented and unauthorized for execution.**

Full detail: `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 19; `PHASE_1B_EXACT_SCAFFOLD_FILE_SCOPE.md` Section 9 (Batch 1B-B rows) and Section 14 (batch table).
