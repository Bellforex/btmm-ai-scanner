# Phase 1B Exact Scaffold File Scope

**Document status:** `ENGINEERING-RECOMMENDED`. `NOT YET AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`. **This document creates no repository scaffold, no source file, no test file, no configuration file, no manifest file, no CI workflow, and installs no technology.** It proposes the exact file-level scope that a future, separately-authorized implementation task would create.

---

## 1. Purpose

Define, at exact file-path granularity, the proposed initial repository scaffold implied by the Phase 1A architecture and the Phase 1B author-approved technology and policy decisions — so that the author can review and approve (or amend) package identity, blocking implementation sub-decisions, batch boundaries, and the complete file inventory **before** any scaffold file is created.

## 2. Baseline Commits

| Commit | Milestone |
|---|---|
| `23f43676abf6e032a5e96c4077d230cc2283f9b6` | Phase 0G sign-off — "Approve Phase 0G controlled baseline" |
| `a142da371c766bbc3489d7d9ae26e6421527c6c9` | Phase 1A architecture planning — "Document Phase 1A software foundation architecture" |
| `52c2139708a2582d0cbc04067be67fc3051a526b` | Phase 1B author decisions — "Document Phase 1B author decisions" |

## 3. Approved Decision Dependencies

This plan depends on, and does not re-decide, the following author-approved items from `PHASE_1B_AUTHOR_DECISION_REGISTER.md`:

- **Group 1:** Python 3.12; uv; `pyproject.toml`; committed `uv.lock`; Pydantic v2; pytest; mypy; Ruff formatter; Ruff linter.
- **Group 2:** Parquet (bulk tabular) + JSONL (append-only) role separation; no initial database; append-only/immutable/partitioned/provider-traceable raw storage; no migration system until a database is approved.
- **Group 3:** canonical UTC time zone; canonical symbols/timeframes with explicit provider-mapping fields; YAML + versioned manifest configuration with a three-level precedence order; environment-variable secrets with dev-only `.env`.
- **Group 4:** UUIDv7 record identity; SHA-256 `content_fingerprint` (separate from identity); MAJOR.MINOR.PATCH versioning; the approved lineage field set; JSONL append-only audit.
- **Group 5:** stdlib structured-JSON logging (separate from audit); GitHub Actions with Ruff/mypy/pytest checks; `pyproject.toml`/`uv.lock` discipline; deferred containerization.
- **Group 6:** `candle_completeness_status`, `duplicate_classification`, `gap_status` enums (policy level).
- **Group 7:** provider-neutral `MarketDataSourcePort`, `INTERFACE_ONLY` scaffold position, `OFFLINE_FILE`-only early retrieval.
- **Group 8:** canonical UTF-8 JSON manifest format; rule/schema manifest field sets; `BACKWARD_COMPATIBLE`/`BREAKING`/`DOCUMENTATION_ONLY` compatibility classes.

None of these approvals is re-opened here. This document only maps them onto exact file paths and identifies what remains blocking before those paths can be created.

## 4. Explicit Implementation Non-Scope

This document does not, and no companion edit made alongside it does:

- Create the repository scaffold, any source directory, test directory, configuration directory, manifest directory, CI directory, fixture directory, data directory, migration directory, or adapter
- Create `pyproject.toml`, `uv.lock`, `.python-version`, any Python file, any YAML file, any JSON manifest, any JSON Schema file, any GitHub Actions workflow, or any `.env` file
- Install Python, uv, or any package
- Stage, commit, or push anything

## 5. Scaffold Design Principles

- **Conservative by default.** The initial scaffold contains only what an approved decision or an approved batch (Part 14/Section 14) actually requires — never a module "because it may be useful later."
- **No speculative placeholders.** No empty directory is proposed for POI detectors, BTMM detectors, AI, Telegram, MT4, MT5, execution, risk, web platform, or live provider adapters. None of these has an approved implementation decision yet.
- **No `.gitkeep`.** A directory is proposed for creation only when at least one reviewed file will exist inside it at creation time.
- **Every file traces to an approved decision.** Section 9's inventory cross-references the Technology Register item, Decision Group, or Data Contract letter that authorizes each file's existence.
- **Batches are independently reviewable and independently committable.** A later batch never silently depends on an unapproved earlier-batch detail.
- **Approval is not implementation.** Nothing in this document, once author-approved, is thereby implemented — a separate, explicit instruction is required to create each batch's files.

## 6. Blocking Implementation Sub-Decisions

| # | Decision | Recommended option | Alternatives | Reason | Risk | Blocking scaffold | Evidence status | Author approval required | Batch affected |
|---|---|---|---|---|---|---|---|---|---|
| 1 | Exact Python 3.12 patch version | `Python 3.12.13` — **RESOLVED** | `3.12.10` (rejected — older patch, superseded on security fixes) | Determinism (Phase 1A SS13) requires one exact pinned version; 3.12.13 is the current 3.12 security release, installed via uv rather than a python.org Windows installer | None significant now that the installation source (uv-managed) is also resolved | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 2 | Distribution/project name | `btmm-ai-scanner` — **RESOLVED** | `btmm-scanner`, `btmm-ai` (rejected) | Matches the existing GitHub repository name | None significant; the existing repo name was not itself treated as sufficient approval — this decision was separately, explicitly author-approved (Section 7) | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 3 | Python import-package name | `btmm_ai_scanner` — **RESOLVED** | `btmm_scanner` (SUPERSEDED — previously used illustratively in `REPOSITORY_SCAFFOLD_PLAN.md` Section 2; that document's illustrative tree has now been renamed throughout to `btmm_ai_scanner` per this approval) | Mirrors the distribution name closely, avoids future ambiguity | The rename across `REPOSITORY_SCAFFOLD_PLAN.md` has now been applied (Part 2 of this correction) | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 4 | src-layout vs. flat-layout | src-layout (`src/<package>/`) — **RESOLVED** | Flat layout (`<package>/` at repo root) (rejected) | Prevents accidental import of an uninstalled package; matches the existing illustrative tree | None significant | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 5 | Build backend | `uv_build` — **RESOLVED**, constrained as `uv_build>=0.11.30,<0.12` | `hatchling`, `setuptools` (rejected) | uv (already approved) does not itself mandate a PEP 517 backend, but the author has now selected uv's own backend, version-bound to match the approved `uv==0.11.30` family | None significant — both the backend choice and its version constraint are now resolved | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 6 | Whether to create `.python-version` | Yes — **RESOLVED, REQUIRED in Batch 1B-A**; exact content = `3.12.13` — **RESOLVED** (via item #1) | Rely on `pyproject.toml`'s `requires-python` only (rejected) | Pins the exact local/dev interpreter for uv | None significant — both inclusion and content are now resolved | NO — RESOLVED | AUTHOR-APPROVED | YES — APPROVED | 1B-A |
| 7 | Exact runtime dependency versions | **Batch 1B-A: NONE required — RESOLVED.** Batch 1B-B: Pydantic v2 constraint remains `Not chosen here` | Loosely-pinned ranges vs. exact pins (still open for 1B-B) | Batch 1B-A's `config/enums.py`/`config/loader.py` are standard-library-only (see Section 17's Batch 1B-A Dependency Baseline note below); no runtime dependency is needed until Batch 1B-B's executable contracts | Batch 1B-A: none (no dependency exists to pin). Batch 1B-B: unpinned/loose versions would reduce determinism | NO for 1B-A (nothing to resolve); YES for 1B-B (Pydantic constraint still open) | AUTHOR-APPROVED (Batch 1B-A = NONE) / REQUIRES AUTHOR DECISION (Batch 1B-B Pydantic constraint) | YES | 1B-A (resolved: none) / 1B-B (still open) |
| 8 | Exact development dependency versions | **RESOLVED:** `pytest>=9.1.1,<10`; `mypy>=2.3.0,<3`; `ruff>=0.15.22,<0.16` | Exact pins vs. bounded ranges (bounded ranges chosen) | Bounded ranges express intent while `uv.lock` supplies the exact reproducible resolution | None significant | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A / 1B-F |
| 9 | `pyproject.toml` metadata fields | **RESOLVED — full field set decided:** `name = "btmm-ai-scanner"`; `version = "0.1.0"`; `description = "Deterministic software foundation for the BTMM and POI AI scanner."`; `authors = [{ name = "Bellforex" }]`; `requires-python = ">=3.12,<3.13"`; `dependencies = []`; `license = "LicenseRef-Proprietary"` (see item 11); `classifiers` = the six approved values (Decision Group 3). **Explicitly omitted from Batch 1B-A, by decision, not by gap:** `readme`, `license-files`, `maintainers`, `keywords`, `project.urls`, `project.scripts`, entry points, `dynamic`, `optional-dependencies`, GUI metadata, CLI metadata | A larger metadata set (urls, keywords, readme, maintainers, etc.) — rejected for Batch 1B-A | Minimum viable metadata for a private, pre-release package; every omitted field is a deliberate decision, not an oversight | None significant — every field's fate (populate or omit) is now decided | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 10 | Minimum supported operating systems | **RESOLVED:** Windows 11 x64 is the validated initial development environment. **Package compatibility claim: NOT YET ESTABLISHED** — Batch 1B-A uses only portable Python standard-library functionality (no Windows-only filesystem assumptions, no registry access, no COM integration, no shell-specific implementation), but OS-independence is not *claimed* until actually tested. No operating-system classifier is included. Linux and macOS validation remain deferred | Restrict to Windows only (rejected — would falsely claim a restriction that isn't technically required); claim full cross-platform support now (rejected — untested) | Affects CI matrix and classifiers; avoids an unverified compatibility claim | None significant — the *position* (what to claim and what not to claim) is now decided, even though the underlying multi-OS testing itself remains future work | NO — RESOLVED (position); the actual cross-platform validation itself remains a future CI/testing task, not a scaffold blocker | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A / 1B-F |
| 11 | License-field position | **RESOLVED:** `license = "LicenseRef-Proprietary"` — a PEP 639 license-expression string in `[project]`, with **no `LICENSE`/`LICENCE` file** created in Batch 1B-A (the file itself is an explicit omission, per Decision Group 3) | SPDX expression + a `LICENSE` file (rejected for Batch 1B-A — no licence file is created); license text embedded only in `pyproject.toml` (closer to what was chosen, minus a file) | Matches the project's proprietary, non-public-release status without requiring a separate licence-file artifact this batch | None significant | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 12 | Initial package version | `0.1.0` — **RESOLVED** | `0.0.1` (rejected) | SemVer pre-1.0 convention for unreleased software | None significant | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 13 | Exact YAML configuration filenames | Not chosen here | `config/default.yaml` + `config/<environment>.yaml`, vs. one monolithic file | Must match the approved three-level precedence | Filename collision with the `config/` **code** module if unresolved | YES | REQUIRES AUTHOR DECISION | YES | Deferred beyond 1B-A–1B-F (see Part 17) |
| 14 | Exact configuration-directory placement | Not chosen here | Top-level `config/` (currently a protected path for this task) vs. package-internal `src/<package>/config/defaults/` | Top-level `config/` is explicitly protected/off-limits during this planning task | Choosing wrong risks colliding with the protected-path list | YES | REQUIRES AUTHOR DECISION | YES | Deferred |
| 15 | Exact manifest filenames | Not chosen here | `<rule_family>_v<version>.json` pattern vs. other | Must be reviewed before any manifest is created (Part 11 rule) | Wrong naming requires a rename after real content exists | YES | REQUIRES AUTHOR DECISION | YES | Deferred (post-1B-F) |
| 16 | Exact manifest-directory behavior | Create only when the first real, reviewed manifest exists — no empty directory, no `.gitkeep` | Pre-create empty `manifests/rules/` and `manifests/schemas/` now | Matches Section 5's design principle and Part 11's explicit rule | Pre-creating empty dirs invites unreviewed placeholder content later | NO (principle already settled) | ENGINEERING-RECOMMENDED (already effectively approved via Section 5) | YES (already covered) | Deferred |
| 17 | Avoid empty manifest directories until real manifest exists | Yes | No | Same as #16 | Same as #16 | NO | ENGINEERING-RECOMMENDED | YES (already covered) | Deferred |
| 18 | Exact validation-status enum | Not chosen here | `PASS \| FAIL \| QUARANTINED` vs. a finer-grained set | `PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md` SS9a left this `REQUIRES AUTHOR DECISION` | Wrong enum granularity requires a breaking schema change later | YES | REQUIRES AUTHOR DECISION | YES | 1B-C |
| 19 | Exact contract module boundaries | One module per contract letter under `contracts/` | One monolithic `contracts.py` | Matches the 18-contract structure in `DATA_CONTRACTS_AND_SCHEMA_PLAN.md` | A monolithic file becomes unwieldy as contracts grow | YES | ENGINEERING-RECOMMENDED / REQUIRES AUTHOR DECISION | YES | 1B-B |
| 20 | Exact canonical JSON serialization approach | Not chosen here | Sorted-key, separator-normalized `json.dumps` vs. a canonical-JSON library | Needed for deterministic `content_fingerprint` computation | Wrong approach breaks fingerprint reproducibility across environments | YES | REQUIRES AUTHOR DECISION | YES | 1B-B / deferred (manifests) |
| 21 | Exact SHA-256 fingerprint field sets | Not chosen here | Fingerprint the full record vs. a defined subset per contract | `DATA_CONTRACTS_AND_SCHEMA_PLAN.md` SS4 left this deferred | Wrong field set breaks duplicate/integrity detection later | YES | REQUIRES AUTHOR DECISION | YES | 1B-B |
| 22 | Exact raw provider-payload encoding | Not chosen here | Store raw bytes vs. a normalized intermediate | `PHASE_1A...` Part 7 item 11 left the physical encoding open | Wrong encoding may lose provider-native fidelity | YES | REQUIRES AUTHOR DECISION | YES | Deferred beyond 1B-A–1B-F |
| 23 | Exact partition naming | Not chosen here | `symbol/timeframe/date` vs. other schemes | Affects raw-storage layout | Wrong naming complicates later retrieval/replay | YES | REQUIRES AUTHOR DECISION | YES | Deferred |
| 24 | Retention policy | Not chosen here | Indefinite retention (current default principle) vs. a defined limit | `PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md` SS23 left this open | No retention enforcement exists in any of Batches 1B-A–1B-F | NO for these batches; YES before real ingestion | REQUIRES AUTHOR DECISION | YES | Deferred |
| 25 | Exact candle-close timestamp convention | Not chosen here | Inclusive vs. exclusive boundary | `DATA_CONTRACTS_AND_SCHEMA_PLAN.md` Contracts A/B leave this `REQUIRES AUTHOR DECISION` | Wrong convention causes off-by-one boundary errors | NO for the contract *shape* (field can exist, marked provisional); YES for correctness | ENGINEERING-PROVISIONAL / REQUIRES AUTHOR DECISION | YES | 1B-B (shape only) |
| 26 | Provider completion-evidence representation | Not chosen here | Provider-supplied "closed" flag vs. wall-clock inference (already rejected as sole proof) | Group 6 approved the enum, not the detection mechanism | Wrong mechanism could misclassify incomplete candles as complete | NO for the enum shape; YES for real detection | REQUIRES AUTHOR DECISION | YES | 1B-C (shape only) |
| 27 | Exact canonical candle key | Not chosen here | `(provider, provider_symbol, provider_timeframe, candle_open_time)` (already named in Group 6) vs. an expanded key | Duplicate-key final field set was explicitly left deferred | Wrong key causes false-positive or false-negative duplicate detection | NO for the shape; YES for the final field set | REQUIRES AUTHOR DECISION | YES | 1B-C (shape only) |
| 28 | CI trigger policy | Not chosen here | On push to `main` + on pull request, vs. push-only | Determines when Batch 1B-F's workflow runs | Overly broad triggers waste CI minutes; overly narrow triggers miss regressions | YES | REQUIRES AUTHOR DECISION | YES | 1B-F |
| 29 | Branch-protection policy | Not chosen here | Require passing CI before merge vs. no protection | This is a GitHub repository **setting**, not a file this scaffold creates | Not enforcing it allows an unreviewed merge to bypass CI | YES (as a policy), but **not a file-creation matter** | REQUIRES AUTHOR DECISION | YES | Outside file scope (repository setting) |
| 30 | Mandatory pull-request policy | Not chosen here | Require PR review before merge vs. direct pushes allowed | Same nature as #29 | Same as #29 | YES (as a policy), but **not a file-creation matter** | REQUIRES AUTHOR DECISION | YES | Outside file scope (repository setting) |

**No item above is silently decided.** Items 16–17 are marked `Blocking scaffold: NO` only because they restate a design principle (Section 5) already implicit in the author-approved "no empty placeholder directories" instruction — they are not new technology or naming decisions.

**Recalculated totals, following the Phase 1B-A Decision Group 3 — Metadata, Configuration Contract, Tests and Git Hygiene decision (supersedes the prior Phase 1B-A Runtime and Dependency Baseline recalculation above it in session history):**

| Category | Count | Items |
|---|---|---|
| Total blocking-decision rows | 30 | 1–30 |
| Fully author-approved decisions (no residual blocking sub-item) | 11 | 1 (exact Python patch), 2 (distribution name), 3 (import package), 4 (layout), 5 (build backend + exact constraint), 6 (`.python-version` inclusion + content), 8 (development dependency versions), 9 (full metadata field set, including explicit omissions), 10 (minimum-OS position), 11 (license-field position), 12 (initial version) |
| Remaining unresolved-and-blocking decisions | 11 | 7 (Batch 1B-A resolved to NONE, but Batch 1B-B's exact Pydantic constraint remains open), 18, 19, 20, 21, 25, 26, 27, 28, 29, 30 |
| Deferred decisions (scope beyond the current batches, not yet blocking) | 8 | 13, 14, 15, 16, 17, 22, 23, 24 |

**11 + 11 + 8 = 30.** This matches the expected result stated in the governing instruction exactly — actual counting confirms it rather than assuming it. Item 7 remains **partially** resolved — Batch 1B-A's own portion is settled (zero runtime dependencies), but Batch 1B-B's exact Pydantic version constraint remains genuinely open, so item 7 stays in the "unresolved-and-blocking" bucket rather than "fully author-approved," to avoid ever presenting Pydantic's constraint as resolved. **This correction newly resolved only items 9, 10, and 11** (previously unresolved or partially unresolved); items 1, 2, 3, 4, 5, 6, 8, and 12 were already resolved by prior decisions and are unchanged here.

**Following Phase 1B-A Decision Group 4 (Interfaces, Tool Configuration, Execution Sequence and Rollback): the 30-row table above and this recalculation remain unchanged — no row was newly resolved, because none of Decision Group 4's items exactly corresponds to any existing numbered row.** Exact function signatures, exact exception classes, exact `__init__.py` contents, exact Ruff configuration, exact mypy configuration, exact pytest configuration, the installation sequence, and the rollback sequence are now resolved — but as a **separate, implementation-specific approval accounting** (Section 6a), not as changes to items 7, 13–17, 20, or 28 above. **Still not silently resolved by any correction to date:** Pydantic's version constraint (item 7, Batch 1B-B), YAML library/filename/placement decisions (items 13–14), manifest filenames/directory behavior (items 15–17), canonical JSON serialization (item 20), raw-payload encoding/partition naming/retention (items 22–24), candle-close/completion/duplicate-key semantics (items 25–27), and CI trigger/branch-protection/PR policy (items 28–30).

**Additional decisions approved by this correction, not modeled as their own numbered row in the table above** (per the "do not change the total row count" instruction, these are recorded here in prose instead of as new rows 31+):
- **Whether uv-managed Python is permitted:** `AUTHOR-APPROVED` — uv-managed Python is permitted and preferred. The existing local Python 3.14.6 (discovered by the Phase 1B-A Runtime and Dependency Environment Audit) must not be removed, modified, or used as the project runtime. A system-installed interpreter is acceptable only when it exactly satisfies the approved runtime (`3.12.13`) and is provenance-recorded. Project execution must use `uv run` or the project virtual environment.
- **Exact uv version policy:** `AUTHOR-APPROVED` — `uv == 0.11.30`, recorded as `[tool.uv] required-version = "==0.11.30"` in the future `pyproject.toml`.
- **Direct-dependency constraint policy (as a policy, distinct from any specific package's version number):** `AUTHOR-APPROVED` — direct dependencies use reviewed bounded ranges in `pyproject.toml`; exact direct and transitive versions are resolved in a committed `uv.lock`; dependency upgrades require review and testing; no fully floating dependency ranges are permitted.
- **Whether configuration modules remain in Batch 1B-A:** `AUTHOR-APPROVED` — yes, `config/__init__.py`, `config/enums.py`, and `config/loader.py` remain in Batch 1B-A, scoped to standard-library-only content (foundational enums, plain mappings, environment-variable reading, deterministic precedence merging, secret-value exclusion) — no YAML parsing, no Pydantic models, no `pydantic-settings`, no filesystem configuration loading, no production/provider-specific configuration, and no credential persistence in this batch.
- **Whether the nine-file Batch 1B-A scope remains unchanged:** **SUPERSEDED by the Phase 1B-A Decision Group 3 revision below** — Batch 1B-A now contains ten changed paths (nine new files plus one modified existing file, `.gitignore`). See Section 14's revised batch row and Section 9's new `.gitignore` inventory row.

**Phase 1B-A Decision Group 3 — Metadata, Configuration Contract, Tests and Git Hygiene (`AUTHOR-APPROVED`):**

- **Project metadata:** the full `[project]` field set is now resolved (Section 6 items 9, 10, 11) — see the pyproject.toml plan following Section 9's inventory table for the exact TOML content.
- **Configuration enums (`src/btmm_ai_scanner/config/enums.py`):** exactly two `StrEnum` classes are approved — `InternalSymbol` (`XAUUSD`, `EURUSD`, `GBPUSD`) and `Timeframe` (`M1`, `M5`, `M15`, `H1`, `H3`, `H4`, `D1`, `W1`), both using uppercase string values. No POI-type, lifecycle-state, BTMM-state, or validation-state enum is introduced; no provider-specific symbol or unsupported timeframe is added; no resampling logic exists. See Section 17 for the full boundary.
- **Configuration loader (`src/btmm_ai_scanner/config/loader.py`):** approved responsibilities are reading approved non-secret runtime environment variables (prefix `BTMM_CONFIG_`, e.g. `BTMM_CONFIG_LOG_LEVEL` → `log_level`), normalizing keys, merging three precedence layers deterministically (project defaults → environment-specific non-secret overrides → runtime environment overrides, later overrides earlier), returning a new mapping without mutating caller-owned input, using the standard library only, and a **shallow top-level merge only** (no nested/deep merge). See Section 17 for the full boundary.
- **Secret boundary:** the loader must reject keys containing indicators such as `password`, `secret`, `token`, `credential`, `api_key`, `private_key`; it must not read `.env`, return credential values, log credential names or values, or create credential defaults; actual secret retrieval remains a separate, future, unbuilt boundary.
- **Test boundaries:** `tests/test_import_smoke.py` and `tests/test_config_precedence.py` — exact approved/prohibited coverage recorded in Section 23.
- **Git hygiene (`.gitignore`):** joins Batch 1B-A as a **modified existing file** (not a new file). Preserves `references/private/*`; adds `.venv/`, `.env`/`.env.*`/`!.env.example`, `__pycache__/`/`*.py[cod]`, `.pytest_cache/`/`.mypy_cache/`/`.ruff_cache/`, `.coverage`/`coverage.xml`/`htmlcov/`, `build/`/`dist/`/`*.egg-info/`. Does **not** ignore `pyproject.toml`, `uv.lock`, `.python-version`, source code, tests, reviewed configuration, reviewed manifests, or documentation. **`.gitignore` is not modified by this documentation task** — see Section 9's new inventory row.
- **Revised Batch 1B-A scope:** ten changed paths total (nine new implementation files + one modified existing file, `.gitignore`). Batch 1B-A remains `NOT YET AUTHOR-APPROVED FOR EXECUTION`.

All items above (both this Decision Group 3 block and the five items preceding it) carry: Recommendation origin `ENGINEERING-RECOMMENDED`; Current author-decision status `AUTHOR-APPROVED`; Implementation status `NOT YET IMPLEMENTED`; Production status `NOT PRODUCTION-APPROVED`.

### 6a. Decision Group 4 — Interfaces, Tool Configuration, Execution Sequence and Rollback (`AUTHOR-APPROVED`)

**None of these items corresponds to an existing row in the 30-row blocking-decision table above — the table's totals (Section 6's recalculation) are therefore left unchanged by this decision round.** They are recorded here as a separate, implementation-specific approval-status accounting, exactly as instructed.

| Item | Detail location | Recommendation origin | Author-decision status | Implementation status | Production status |
|---|---|---|---|---|---|
| Package-root content (`src/btmm_ai_scanner/__init__.py`) | Section 9b | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Configuration package exports (`config/__init__.py`) | Section 17d | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Enum implementation (exact code) | Section 17a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Exception hierarchy | Section 17e | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Loader function interface and behavior | Section 17b | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Private implementation boundary | Section 17f | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Ruff configuration | Section 9a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| mypy configuration | Section 9a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| pytest configuration | Section 9a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Development dependency group | Section 9a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Exact test-function scope | Section 23a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Installation/execution sequence (Stages A–J) | Section 16a | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Rollback procedure | Section 27 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |
| Acceptance criteria | Section 28 | ENGINEERING-RECOMMENDED | AUTHOR-APPROVED | NOT YET IMPLEMENTED | NOT PRODUCTION-APPROVED |

**Batch 1B-A is not thereby represented as execution-authorized.** Every item above is a documented, approved *specification* — none has been implemented, and none carries any production status beyond `NOT PRODUCTION-APPROVED`. Batch 1B-A remains `NOT YET AUTHOR-APPROVED FOR EXECUTION` (Section 14) until a separate, explicit instruction authorizes Stage A of Section 16a.

## 7. Proposed Package and Distribution Identity

**Status: `AUTHOR-APPROVED` (Phase 1B-0 Package Identity and Layout decision). Recommendation origin: `ENGINEERING-RECOMMENDED`. Implementation status: `NOT YET IMPLEMENTED`. Production status: `NOT PRODUCTION-APPROVED`.**

| Field | Author-approved value | Status |
|---|---|---|
| `distribution_name` | `btmm-ai-scanner` | `AUTHOR-APPROVED` |
| `import_package` | `btmm_ai_scanner` | `AUTHOR-APPROVED` |
| `source_package_path` | `src/btmm_ai_scanner/` | `AUTHOR-APPROVED` |
| `layout` | `src` (src-layout, not flat-layout) | `AUTHOR-APPROVED` |
| `build_backend` | `uv_build` | `AUTHOR-APPROVED` |
| `initial_project_version` | `0.1.0` | `AUTHOR-APPROVED` |
| `python_version_file` | `.python-version` — **REQUIRED IN BATCH 1B-A** | `AUTHOR-APPROVED` (inclusion); exact patch content `REQUIRES AUTHOR DECISION` (Blocking Decision #1) |

**Distribution identity and import identity are intentionally different representations, and remain distinct concepts** — the hyphenated distribution name (`btmm-ai-scanner`, used in `pyproject.toml`'s `[project].name`, on PyPI if ever published, and in `uv`/`pip` commands) installs the underscore-based Python import package (`btmm_ai_scanner`, used in `import btmm_ai_scanner` and under `src/`); a distribution name may contain hyphens, but the import package name must be a valid Python identifier, which does not permit hyphens.

**The `src` layout separates importable code from the repository root** — the package lives at `src/btmm_ai_scanner/`, not at a flat `btmm_ai_scanner/` beside `pyproject.toml`, preventing accidental import of an uninstalled package.

**No package directory exists yet.** `src/`, `src/btmm_ai_scanner/`, and every file beneath them remain proposals only — this correction records an approved *decision*, not an implemented artifact.

**No build configuration exists yet.** `uv_build` is the author-approved future build backend; no `pyproject.toml` `[build-system]` table has been written.

**No package has been installed.** Neither Python, uv, nor any dependency has been installed by this or any prior task.

**No version has been published.** `0.1.0` is the author-approved *initial* version value for a future `pyproject.toml`; no package has been built, tagged, or published under that version.

**The existing GitHub repository name (`btmm-ai-scanner`) was not, by itself, treated as sufficient approval of the distribution name.** The distribution name above is now approved via the author's explicit Phase 1B-0 Package Identity and Layout decision, recorded in this section — not merely inferred from the repository's hosting label.

**Renaming impact (resolved):** `docs/architecture/REPOSITORY_SCAFFOLD_PLAN.md` Section 2's proposed tree previously used `src/btmm_scanner/` (without `_ai_`) illustratively. Per this approval, that tree — and every other proposed package-path reference in that document — has now been corrected throughout to `src/btmm_ai_scanner/` (see that document's Section 9). No stale active reference to `src/btmm_scanner/` remains in either document.

## 8. Proposed Exact Directory Tree

**This tree reflects only the batches defined in Section 14 (1B-A through 1B-F) — a deliberately narrow subset of the full 16-layer architecture.** Directories for `measurements/`, `domain/`, `poi/`, `lifecycle/`, `btmm/`, `annotations/`, `replay/`, `scripts/`, and `migrations/` are **not** included below, because no batch in Section 14 places a reviewed file inside them yet (Section 5 principle). `manifests/rules/` and `manifests/schemas/` are likewise excluded until their first real manifest exists (Part 11 rule).

```
btmm-ai-scanner/
├── docs/                                  (existing — unchanged)
├── knowledge/                             (existing — unchanged)
├── references/                            (existing — unchanged)
├── .gitignore                             (existing — proposed MODIFICATION, Batch 1B-A, Decision Group 3 — creation order 0, precedes all other Batch 1B-A files)
├── pyproject.toml                         (proposed, Batch 1B-A — file scope, exact contents in Part 8/Section 17)
├── uv.lock                                (proposed, Batch 1B-A — created only after pyproject.toml and dependency set are approved)
├── .python-version                        (proposed, Batch 1B-A — REQUIRED, inclusion AUTHOR-APPROVED; exact patch content still pending Blocking Decision #1)
├── src/
│   └── btmm_ai_scanner/                    (proposed import package — name AUTHOR-APPROVED, Section 7)
│       ├── __init__.py                    (Batch 1B-A)
│       ├── config/
│       │   ├── __init__.py                (Batch 1B-A)
│       │   ├── enums.py                   (Batch 1B-A — canonical symbol/provider/timeframe enums)
│       │   └── loader.py                  (Batch 1B-A — YAML + precedence loader; no YAML *data* file created — see Blocking Decisions #13–#14)
│       ├── contracts/
│       │   ├── __init__.py                (Batch 1B-B)
│       │   ├── types.py                   (Batch 1B-B — identity/fingerprint/version value types)
│       │   ├── raw_candle.py              (Batch 1B-B — Contract A)
│       │   ├── normalized_candle.py       (Batch 1B-B — Contract B)
│       │   ├── validation_result.py       (Batch 1B-B — Contract N)
│       │   ├── provenance_record.py       (Batch 1B-B — Contract M)
│       │   ├── rule_version_manifest.py   (Batch 1B-B — Contract Q, shape only)
│       │   └── schema_version_manifest.py (Batch 1B-B — Contract R, shape only)
│       ├── validation/
│       │   ├── __init__.py                (Batch 1B-C)
│       │   ├── completeness.py            (Batch 1B-C)
│       │   ├── duplicates.py              (Batch 1B-C)
│       │   ├── gaps.py                    (Batch 1B-C)
│       │   └── eligibility.py             (Batch 1B-C)
│       ├── audit/
│       │   ├── __init__.py                (Batch 1B-D)
│       │   ├── events.py                  (Batch 1B-D — Contract O)
│       │   └── writer.py                  (Batch 1B-D — append-only writer interface)
│       ├── observability/
│       │   ├── __init__.py                (Batch 1B-D)
│       │   └── logging_config.py          (Batch 1B-D)
│       └── ingestion/
│           ├── __init__.py                (Batch 1B-E)
│           ├── port.py                    (Batch 1B-E — MarketDataSourcePort)
│           ├── requests.py                (Batch 1B-E)
│           ├── results.py                 (Batch 1B-E)
│           └── offline_file_source.py     (Batch 1B-E — OFFLINE_FILE stub)
├── tests/
│   ├── test_import_smoke.py               (Batch 1B-A)
│   ├── test_config_precedence.py          (Batch 1B-A)
│   └── unit/
│       ├── test_identity_and_fingerprint.py        (Batch 1B-B)
│       ├── test_semver.py                          (Batch 1B-B)
│       ├── test_raw_candle_contract.py             (Batch 1B-B)
│       ├── test_normalized_candle_contract.py      (Batch 1B-B)
│       ├── test_manifest_compatibility_classes.py  (Batch 1B-B)
│       ├── test_candle_completeness.py             (Batch 1B-C)
│       ├── test_exact_duplicate.py                 (Batch 1B-C)
│       ├── test_conflicting_duplicate_quarantine.py (Batch 1B-C)
│       ├── test_missing_gap.py                     (Batch 1B-C)
│       ├── test_no_synthetic_fill.py               (Batch 1B-C)
│       ├── test_validation_eligibility.py          (Batch 1B-C)
│       ├── test_processing_version_preservation.py (Batch 1B-C)
│       ├── test_audit_log_separation.py            (Batch 1B-D)
│       ├── test_secret_redaction.py                (Batch 1B-D)
│       ├── test_ingestion_port_contract.py         (Batch 1B-E)
│       └── test_offline_file_stub.py               (Batch 1B-E)
└── .github/
    └── workflows/
        └── ci.yml                          (Batch 1B-F)
```

**No directory or file in this tree is created or modified by this document — including `.gitignore`, which remains untouched by this documentation task despite being a proposed Batch 1B-A modification.** `measurements/`, `domain/`, `poi/`, `lifecycle/`, `btmm/`, `annotations/`, `replay/`, `scripts/`, `migrations/`, `manifests/rules/`, and `manifests/schemas/` remain correctly absent, matching Section 5's conservative-scaffold principle.

## 9. Exact File Inventory

Every proposed file, one row each. **Creation order** matches Section 15. **Independent commit eligible** reflects whether the file may be committed alone or only as part of its whole batch (Section 14 requires whole-batch review, so no file below is independently committable ahead of its batch — the column records intra-batch groupings only).

| Batch | Exact path | New/Modified | File type | Purpose | Approved decision supported | Required content | Prohibited content | Direct dependencies | Tests required | Blocking unresolved decision | Creation order | Scope status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1B-A | `.gitignore` | **Modified** (existing file) | Ignore-pattern text | Excludes Python/uv/test/build artifacts from version control | Decision Group 3 (Git Hygiene) | Preserve `references/private/*`; add `.venv/`, `.env`/`.env.*`/`!.env.example`, `__pycache__/`/`*.py[cod]`, `.pytest_cache/`/`.mypy_cache/`/`.ruff_cache/`, `.coverage`/`coverage.xml`/`htmlcov/`, `build/`/`dist/`/`*.egg-info/` | Ignoring `pyproject.toml`, `uv.lock`, `.python-version`, source code, tests, reviewed configuration, reviewed manifests, or documentation | None | N/A (no test exercises `.gitignore` directly) | None — fully resolved | 0 (precedes all other Batch 1B-A files) | **IMPLEMENTED** — modified in commit `47cfd699bb7f4893774579f1693abbbb57b91607`; not modified by this documentation task |
| 1B-A | `pyproject.toml` | New | TOML manifest | Project/build metadata, dependency declarations | Register #1–#8, #12–#13; Phase 1B-0 Package Identity and Layout decision; Phase 1B-A Runtime and Dependency Baseline; Phase 1B-A Decision Group 3 (full metadata field set) | `[project]` table: `name = "btmm-ai-scanner"`, `version = "0.1.0"`, `description = "Deterministic software foundation for the BTMM and POI AI scanner."`, `authors = [{ name = "Bellforex" }]`, `requires-python = ">=3.12,<3.13"`, `dependencies = []`, `license = "LicenseRef-Proprietary"`, `classifiers` (six approved values, Section 6 item 9); `[build-system]` table (`uv_build>=0.11.30,<0.12`); `[tool.uv]` version requirement; `src`-layout package discovery pointing at `btmm_ai_scanner`; a development-dependency group with the three bounded ranges (`pytest`, `mypy`, `ruff`) | Secrets, entry/risk fields, any runtime dependency (Batch 1B-A has none); `readme`, `license-files`, `maintainers`, `keywords`, `project.urls`, `project.scripts`, entry points, `dynamic`, `optional-dependencies` (all explicitly omitted, Section 6 item 9) | None | Import-smoke test passes | None — metadata fully resolved (Section 6 items 9, 10, 11) | 1 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` |
| 1B-A | `uv.lock` | New | Lockfile | Reproducible dependency resolution | Register #3; Phase 1B-A Runtime and Dependency Baseline | Resolved dependency graph for the dev group only (`pytest`, `mypy`, `ruff` and their transitive deps) — no runtime dependency to resolve | Secrets | `pyproject.toml` | N/A (generated) | None — `uv.lock` cannot exist until `uv` and Python 3.12.13 are installed during an authorized implementation task | 2 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607`; generated via `uv lock`, verified via `uv lock --check` |
| 1B-A | `.python-version` | New | Text | Local/dev interpreter pin | Register #1–#2; Phase 1B-0 Package Identity and Layout decision (inclusion); Phase 1B-A Runtime and Dependency Baseline (exact content) | Exact content: `3.12.13` | Nothing else | `pyproject.toml`'s `requires-python` | N/A | None — both inclusion and content are resolved | 3 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` |
| 1B-A | `src/btmm_ai_scanner/__init__.py` | New | Python | Package root docstring only | Register #1, #3, #12; Decision Group 4 (Section 9b) | Module docstring only: `"""Deterministic software foundation for the BTMM and POI AI scanner."""` | `__version__` constant; configuration re-exports; filesystem access; environment-variable access; logging setup; network activity; any import-time initialization; business logic | None | Import smoke test | None — fully resolved | 4 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` |
| 1B-A | `src/btmm_ai_scanner/config/__init__.py` | New | Python | Re-exports the approved public configuration API | Layer: config; Decision Group 4 (Section 17d) | `from .enums import InternalSymbol, Timeframe`; `from .loader import ENV_PREFIX, ConfigurationError, InvalidConfigurationKeyError, SecretConfigurationKeyError, load_configuration`; `__all__` listing all six names | Business logic; any export beyond the six named symbols | `config/enums.py`, `config/loader.py` | Import smoke test (`test_config_public_exports_import`) | None — fully resolved | 5 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` |
| 1B-A | `src/btmm_ai_scanner/config/enums.py` | New | Python (standard-library only) | Canonical internal-symbol/timeframe enums | Phase 0G `AUTHOR-APPROVED` lists (`docs/PROJECT_SCOPE.md`); Group 3; Decision Group 3/4 (Section 17a) | Exactly two `StrEnum` classes: `InternalSymbol` (`XAUUSD`/`EURUSD`/`GBPUSD`), `Timeframe` (`M1`/`M5`/`M15`/`H1`/`H3`/`H4`/`D1`/`W1`) — no separate provider enum | Any un-approved symbol/timeframe; a separate `ProviderEnum`; POI/lifecycle/BTMM/validation-state enums; Pydantic; any third-party import | None | `test_config_public_exports_import` (import), Config-precedence test (indirect usage) | None — fully resolved | 6 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` |
| 1B-A | `src/btmm_ai_scanner/config/loader.py` | New | Python (standard-library only) | Config precedence resolution (defaults → environment → env vars) | Group 3 (configuration precedence); Decision Group 4 (Section 17b/17e/17f — exact signature, exceptions, private helpers) | `ENV_PREFIX`; `load_configuration(project_defaults, environment_overrides, *, environ=None) -> dict`; `ConfigurationError`/`InvalidConfigurationKeyError`/`SecretConfigurationKeyError`; private `_`-prefixed helpers for key validation, secret detection, runtime extraction, shallow merge | Any hard-coded secret; any actual YAML file; YAML parsing; Pydantic models; `pydantic-settings`; filesystem configuration loading; production/provider-specific configuration; credential persistence; recursive/nested merge; a global configuration singleton | `config/enums.py` | `test_config_precedence.py` (11 named tests, Section 23a) | #13, #14 (no YAML file created until resolved) | 7 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607` (code only — no YAML data file, no third-party dependency) |
| 1B-A | `tests/test_import_smoke.py` | New | Python test | Confirms the package imports cleanly, with no side effects | N/A (scaffold integrity); Decision Group 4 (Section 23a); requires only `pytest>=9.1.1,<10` | Exactly three tests: `test_package_imports`, `test_config_public_exports_import`, `test_import_has_no_filesystem_or_network_side_effect` | Any domain logic; POI/BTMM/ingestion/AI/signal/trading/profitability/database/live-provider scope | package root | Self | None — fully resolved | 8 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607`; 3 tests passing |
| 1B-A | `tests/test_config_precedence.py` | New | Python test | Confirms precedence order, normalization, and secret rejection | Group 3; Decision Group 4 (Section 23a); requires only `pytest>=9.1.1,<10` | Exactly 11 named tests (Section 23a) using controlled mappings/monkeypatched environ | Real secrets; any third-party runtime dependency; real machine configuration | `config/loader.py` | Self | #13, #14 | 9 | **IMPLEMENTED** — committed in `47cfd699bb7f4893774579f1693abbbb57b91607`; 31 collected pytest cases from the 11 defined test functions (2 of which are parametrized), all passing |
| 1B-B | `src/btmm_ai_scanner/contracts/__init__.py` | New | Python | Marks `contracts` as a package | Layer: contracts | Empty/minimal | Business logic | package root | Import smoke test | #19 | 10 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/types.py` | New | Python (Pydantic v2) | **Defines** `ContractModel` (shared frozen/strict/forbid-extra base); `UUIDv7` validation-only annotated type; `SHA256Fingerprint` validation-only annotated type; project-owned `SemVer` `RootModel` with full SemVer 2.0.0 grammar and `compare_precedence()`/`same_precedence_as()` API | Group 4 (identity, fingerprint, versioning); Phase 1B-B Decision Group 1 (`PHASE_1B_AUTHOR_DECISION_REGISTER.md` §19); Phase 1B-B Decision Group 2 (§20A–§20F) | Value-type wrappers and shared base model only — **Pydantic v2 required, dataclass placeholder rejected**; exact `ContractModel` config (`extra="forbid"`, `frozen=True`, `strict=True`, `validate_default=True`, `revalidate_instances="always"`, `allow_inf_nan=False`, `str_strip_whitespace=False`, `use_enum_values=False`); UUIDv7 validation-only (no generation); `SHA256Fingerprint` validation-only (64-char lowercase hex, no generation); `SemVer` full grammar/parsing/precedence resolved (§20D/§20E) | Any entry/risk field; **no UUID generator**; **no fingerprint calculation**; **no rich SemVer ordering methods** (`__lt__`/`__le__`/`__gt__`/`__ge__`); **no canonical-JSON functionality**; `validate_assignment`, `arbitrary_types_allowed`, `from_attributes`, `populate_by_name`, alias generators/field aliases, custom `json_encoders` | `pydantic>=2.13.4,<2.14` (approved, not yet added) | `test_identity_and_fingerprint.py` (17 functions), `test_semver.py` (15 functions) | #20, #21 (RESOLVED FOR BATCH 1B-B SCOPE, per §19C/§19D — canonical serialization and fingerprint field sets are explicitly out of this batch); SemVer grammar/parsing/comparison — **RESOLVED FOR BATCH 1B-B SCOPE by Decision Group 2** | 11 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/raw_candle.py` | New | Python | Contract A (Raw Candle Record) shape | Data Contracts Plan Contract A; Group 3/6 fields | Fields per Contract A, `candle_completeness_status`/`duplicate_classification`/`gap_status` placeholders | Normalization logic, entry/risk fields | `contracts/types.py`, `config/enums.py` | `test_raw_candle_contract.py` | #18, #25, #26, #27 (enum/semantics finality) | 12 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/normalized_candle.py` | New | Python | Contract B (Normalized Candle Record) shape | Data Contracts Plan Contract B | Fields per Contract B | Measurement formulas, POI logic | `contracts/raw_candle.py` | `test_normalized_candle_contract.py` | #25 | 13 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/validation_result.py` | New | Python | Contract N (Validation Result) shape | Data Contracts Plan Contract N | Fields per Contract N | POI/BTMM validity fields | `contracts/types.py` | `test_validation_eligibility.py` (Batch C) | #18 (status enum) | 14 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/provenance_record.py` | New | Python | Contract M (Provenance Record) shape | Data Contracts Plan Contract M | Fields per Contract M | Business logic | `contracts/types.py` | Covered by processing-version test | None | 15 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/rule_version_manifest.py` | New | Python (Pydantic v2) | Contract Q shape (**in-memory contract shape only** — no manifest file I/O, no persistence, no manifest directory) | Data Contracts Plan Contract Q; Group 8; Phase 1B-B Decision Group 1 §19G | Fields per Contract Q | Actual manifest content/file I/O; manifest loading; manifest persistence; manifest supersession mechanism; any `manifests/` directory creation | `contracts/types.py` | `test_manifest_compatibility_classes.py` | #15, #20 (RESOLVED FOR BATCH 1B-B SCOPE — canonical JSON serialization deferred beyond this batch, §19D/§19F) | 16 | Required in later foundation batch (shape only) |
| 1B-B | `src/btmm_ai_scanner/contracts/schema_version_manifest.py` | New | Python (Pydantic v2) | Contract R shape (**in-memory contract shape only** — no manifest file I/O, no persistence, no manifest directory, no JSON Schema file export) | Data Contracts Plan Contract R; Group 8; Phase 1B-B Decision Group 1 §19F/§19G | Fields per Contract R, compatibility-class enum (`BACKWARD_COMPATIBLE`/`BREAKING`/`DOCUMENTATION_ONLY`) | Actual manifest content/file I/O; manifest loading; manifest persistence; manifest supersession mechanism; any `manifests/` directory creation; any JSON Schema file, schema-export script, or schema directory | `contracts/types.py` | `test_manifest_compatibility_classes.py` | #15, #20 (RESOLVED FOR BATCH 1B-B SCOPE, same as above) | 17 | Required in later foundation batch (shape only) |
| 1B-B | `tests/unit/test_identity_and_fingerprint.py` | New | Python test | `ContractModel`/UUIDv7/SHA-256 behavior and distinctness | Group 4; Phase 1B-B Decision Group 2 §20G | **Exactly 17 approved test-function names** (§20G): `test_contract_model_is_frozen`, `test_contract_model_forbids_extra_fields`, `test_contract_model_rejects_type_coercion`, `test_contract_model_validates_default_values`, `test_contract_model_revalidates_nested_instances`, `test_contract_model_rejects_nan_and_infinity`, `test_uuidv7_accepts_canonical_string_and_uuid_instance`, `test_uuidv7_rejects_invalid_text`, `test_uuidv7_rejects_nil_and_non_version_seven_values`, `test_uuidv7_rejects_non_rfc_variant`, `test_uuidv7_rejects_noncanonical_text`, `test_uuidv7_serialization_modes`, `test_sha256_fingerprint_accepts_exact_lowercase_hex`, `test_sha256_fingerprint_rejects_invalid_values`, `test_sha256_fingerprint_serializes_without_normalization`, `test_identity_and_fingerprint_are_not_interchangeable`, `test_core_value_types_round_trip_through_json`. Parameterization permitted; fixed UUID values only; no UUID generation | Real production data; any UUID generation; any additional function name without review | `contracts/types.py` | Self | #21 (RESOLVED FOR BATCH 1B-B SCOPE — canonical fingerprint field-set still deferred beyond this batch) | 18 | Required in later foundation batch |
| 1B-B | `tests/unit/test_semver.py` | New | Python test | Full SemVer 2.0.0 grammar and precedence behavior | Group 4; Phase 1B-B Decision Group 2 §20H | **Exactly 15 approved test-function names** (§20H): `test_semver_accepts_valid_semver_2_0_0_values`, `test_semver_rejects_invalid_values`, `test_semver_rejects_leading_zeroes`, `test_semver_preserves_exact_text`, `test_semver_parse_returns_semver`, `test_semver_is_frozen`, `test_semver_serializes_as_json_string`, `test_semver_compares_core_versions`, `test_semver_orders_prerelease_before_release`, `test_semver_compares_prerelease_identifiers`, `test_semver_ignores_build_metadata_for_precedence`, `test_semver_exact_equality_includes_build_metadata`, `test_semver_same_precedence_ignores_build_metadata`, `test_semver_does_not_define_rich_ordering`, `test_semver_round_trips_through_json`. Official SemVer 2.0.0 precedence-chain coverage required; no complete Pydantic error-prose assertions; no additional function name without review | N/A | `contracts/types.py` | Self | None — fully resolved by Decision Group 2 | 19 | Required in later foundation batch |
| 1B-B | `tests/unit/test_raw_candle_contract.py` | New | Python test | Contract A shape validation | Contract A | Positive/negative construction cases | Live market data | `contracts/raw_candle.py` | Self | #18, #25–#27 | 20 | Required in later foundation batch |
| 1B-B | `tests/unit/test_normalized_candle_contract.py` | New | Python test | Contract B shape validation | Contract B | Positive/negative construction cases | Live market data | `contracts/normalized_candle.py` | Self | #25 | 21 | Required in later foundation batch |
| 1B-B | `tests/unit/test_manifest_compatibility_classes.py` | New | Python test | Compatibility-class classification logic | Group 8 | `BACKWARD_COMPATIBLE`/`BREAKING`/`DOCUMENTATION_ONLY` cases | Real manifest files | `contracts/schema_version_manifest.py` | Self | #15, #20 | 22 | Required in later foundation batch |
| 1B-C | `src/btmm_ai_scanner/validation/__init__.py` | New | Python | Marks `validation` as a package | Layer: validation | Empty/minimal | Business logic | package root | Import smoke test | None | 23 | Required in later foundation batch |
| 1B-C | `src/btmm_ai_scanner/validation/completeness.py` | New | Python | `candle_completeness_status` classification logic (shape/interface only) | Group 6 | Enum + classification function signature | Provider-specific detection logic | `contracts/raw_candle.py` | `test_candle_completeness.py` | #26 | 24 | Required in later foundation batch |
| 1B-C | `src/btmm_ai_scanner/validation/duplicates.py` | New | Python | `duplicate_classification` logic (shape/interface only) | Group 6 | Enum + candidate-key function signature | Automatic conflict-winner logic | `contracts/raw_candle.py` | `test_exact_duplicate.py`, `test_conflicting_duplicate_quarantine.py` | #27 | 25 | Required in later foundation batch |
| 1B-C | `src/btmm_ai_scanner/validation/gaps.py` | New | Python | `gap_status` logic (shape/interface only) | Group 6 | Enum + gap-detection function signature | Synthetic-fill logic of any kind | `contracts/raw_candle.py` | `test_missing_gap.py`, `test_no_synthetic_fill.py` | #26 | 26 | Required in later foundation batch |
| 1B-C | `src/btmm_ai_scanner/validation/eligibility.py` | New | Python | 8-step normalization/measurement eligibility gate | `PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md` SS9a | Eligibility-gating function per the approved 8-step sequence | POI/BTMM validity decisions | `validation/completeness.py`, `duplicates.py`, `gaps.py`, `contracts/validation_result.py` | `test_validation_eligibility.py` | #18 | 27 | Required in later foundation batch |
| 1B-C | `tests/unit/test_candle_completeness.py` | New | Python test | Completeness classification correctness | Group 6 | Positive/negative/boundary cases | Live data | `validation/completeness.py` | Self | #26 | 28 | Required in later foundation batch |
| 1B-C | `tests/unit/test_exact_duplicate.py` | New | Python test | Exact-duplicate handling | Group 6 | Preserve-both-records assertions | Live data | `validation/duplicates.py` | Self | #27 | 29 | Required in later foundation batch |
| 1B-C | `tests/unit/test_conflicting_duplicate_quarantine.py` | New | Python test | Conflicting-duplicate quarantine behavior | Group 6 | No-silent-winner assertions | Automatic resolution logic | `validation/duplicates.py` | Self | #27 | 30 | Required in later foundation batch |
| 1B-C | `tests/unit/test_missing_gap.py` | New | Python test | Gap-status transitions | Group 6 | State-transition assertions | Live data | `validation/gaps.py` | Self | #26 | 31 | Required in later foundation batch |
| 1B-C | `tests/unit/test_no_synthetic_fill.py` | New | Python test | No forward/back fill ever occurs | Group 6 | Negative assertions against every fill technique | Any fill implementation | `validation/gaps.py` | Self | None | 32 | Required in later foundation batch |
| 1B-C | `tests/unit/test_validation_eligibility.py` | New | Python test | 8-step gating sequence correctness | SS9a | Step-by-step gating assertions | POI/BTMM logic | `validation/eligibility.py` | Self | #18 | 33 | Required in later foundation batch |
| 1B-C | `tests/unit/test_processing_version_preservation.py` | New | Python test | `processing_version` never silently overwritten | Group 4 | Reprocessing-creates-new-record assertions | Live data | `contracts/types.py` | Self | None | 34 | Required in later foundation batch |
| 1B-D | `src/btmm_ai_scanner/audit/__init__.py` | New | Python | Marks `audit` as a package | Layer: audit | Empty/minimal | Business logic | package root | Import smoke test | None | 35 | Required in later foundation batch |
| 1B-D | `src/btmm_ai_scanner/audit/events.py` | New | Python | Contract O (Audit Event) shape | Contract O | Fields per Contract O | Passwords/tokens/API keys/private-book text | `contracts/types.py` | `test_secret_redaction.py` | None | 36 | Required in later foundation batch |
| 1B-D | `src/btmm_ai_scanner/audit/writer.py` | New | Python | Append-only audit-writer interface (JSONL) | Group 4/5 | Interface only, no live file I/O target chosen | Any mutation of a written event | `audit/events.py` | `test_audit_log_separation.py` | #22 (physical storage encoding, deferred) | 37 | Required in later foundation batch (interface only) |
| 1B-D | `src/btmm_ai_scanner/observability/__init__.py` | New | Python | Marks `observability` as a package | Layer: cross-cutting | Empty/minimal | Business logic | package root | Import smoke test | None | 38 | Required in later foundation batch |
| 1B-D | `src/btmm_ai_scanner/observability/logging_config.py` | New | Python | Structured JSON operational-logging configuration | Group 5 | stdlib `logging` configuration, JSON formatter | Audit-event writing (kept separate) | None | `test_audit_log_separation.py`, `test_secret_redaction.py` | None | 39 | Required in later foundation batch |
| 1B-D | `tests/unit/test_audit_log_separation.py` | New | Python test | Audit and operational logs never conflated | Group 4/5 | Separate-store assertions | N/A | `audit/writer.py`, `observability/logging_config.py` | Self | None | 40 | Required in later foundation batch |
| 1B-D | `tests/unit/test_secret_redaction.py` | New | Python test | No secret ever appears in a log or audit event | Group 4 audit exclusions | Redaction assertions for passwords/tokens/API keys/`.env` content | Any real secret value (only synthetic test doubles) | `audit/events.py`, `observability/logging_config.py` | Self | None | 41 | Required in later foundation batch |
| 1B-E | `src/btmm_ai_scanner/ingestion/__init__.py` | New | Python | Marks `ingestion` as a package | Layer: ingestion | Empty/minimal | Provider-specific code | package root | Import smoke test | None | 42 | Required in later foundation batch |
| 1B-E | `src/btmm_ai_scanner/ingestion/port.py` | New | Python | `MarketDataSourcePort` interface | Group 7 | Abstract interface only | Any concrete provider implementation | `contracts/raw_candle.py` | `test_ingestion_port_contract.py` | None | 43 | Required in later foundation batch |
| 1B-E | `src/btmm_ai_scanner/ingestion/requests.py` | New | Python | Provider-neutral ingestion request shape | Group 7 | Provider-neutral fields only | Provider-specific fields, aliases | `contracts/types.py` | `test_ingestion_port_contract.py` | None | 44 | Required in later foundation batch |
| 1B-E | `src/btmm_ai_scanner/ingestion/results.py` | New | Python | Provider-neutral ingestion result shape | Group 7 | Version references (`adapter_version`, etc.) | Signals, trades, measurements | `contracts/types.py` | `test_ingestion_port_contract.py` | None | 45 | Required in later foundation batch |
| 1B-E | `src/btmm_ai_scanner/ingestion/offline_file_source.py` | New | Python | `OFFLINE_FILE` deterministic stub adapter | Group 7 | Reads a fixed local file only, no network call | Any network call, any credential | `ingestion/port.py` | `test_offline_file_stub.py` | None | 46 | Required in later foundation batch |
| 1B-E | `tests/unit/test_ingestion_port_contract.py` | New | Python test | Port stays provider-neutral | Group 7 | Provider-neutral-only assertions | Provider-specific test doubles beyond `OFFLINE_FILE` | `ingestion/port.py` | Self | None | 47 | Required in later foundation batch |
| 1B-E | `tests/unit/test_offline_file_stub.py` | New | Python test | Deterministic offline behavior, no network | Group 7 | No-network-access assertion | Live network call | `ingestion/offline_file_source.py` | Self | None | 48 | Required in later foundation batch |
| 1B-F | `.github/workflows/ci.yml` | New | YAML (CI workflow) | Runs Ruff format check, Ruff lint, mypy, pytest | Group 5 | Offline-safe job steps only | Credentials, deployment steps, live connections | `pyproject.toml`, `uv.lock` | N/A (the workflow itself is verification) | #28 (trigger policy), #29–#30 (repo settings, outside file scope) | 49 | Required in later foundation batch |

**Total proposed changed paths: 50** (49 files + 1 modified existing file, `.gitignore`, added by the Phase 1B-A Decision Group 3 — Metadata, Configuration Contract, Tests and Git Hygiene correction). `.python-version`'s *inclusion and content* are both fully resolved (`3.12.13`). **`.gitignore` had no prior row in this inventory — this is a newly added row, not a reclassification of an existing one.** **None is created or modified by this document.** Every row above is either "Required in initial scaffold" (Batch 1B-A, now 10 changed paths: 9 new files + 1 modified `.gitignore`), "Required in later foundation batch" (Batches 1B-B through 1B-F, 40 files — see the corrected 1B-D count of 7, not 6, below), or explicitly excluded as "Deferred beyond Phase 1B" (manifests, raw-storage I/O, provider adapters — see Section 6) or "Prohibited" (any entry/risk/execution file — none appears above). **No file listed above is marked as already created or modified — every row remains a proposal only.**

### 9a. Batch 1B-A `pyproject.toml` Metadata Plan (Decision Group 3, `AUTHOR-APPROVED`)

**`pyproject.toml` is not created by this document.** The following is the exact future `[project]` metadata content, once Batch 1B-A is separately authorized for execution:

```toml
[project]
name = "btmm-ai-scanner"
version = "0.1.0"
description = "Deterministic software foundation for the BTMM and POI AI scanner."
authors = [
    { name = "Bellforex" }
]
requires-python = ">=3.12,<3.13"
dependencies = []
license = "LicenseRef-Proprietary"
classifiers = [
    "Development Status :: 2 - Pre-Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3 :: Only",
    "Programming Language :: Python :: 3.12",
    "Private :: Do Not Upload",
]

[build-system]
requires = ["uv_build>=0.11.30,<0.12"]
build-backend = "uv_build"

[tool.uv]
required-version = "==0.11.30"
```

**Explicitly omitted from Batch 1B-A** (a decision, not a gap): `readme` field and no `README.md` file; `license-files` field and no licence file; `maintainers`; `keywords`; `project.urls`; `project.scripts`; entry points; `dynamic` metadata; `optional-dependencies`; GUI metadata; CLI metadata.

**Prohibited classifiers and claims (binding):** no deprecated `License ::` classifier; no operating-system classifier; no public-release classifier; no production-readiness claim; no trading-profitability claim; no AI-performance claim; no financial-product claim.

**Development-dependency group (`AUTHOR-APPROVED`, Decision Group 4):**

```toml
[dependency-groups]
dev = [
    "pytest>=9.1.1,<10",
    "mypy>=2.3.0,<3",
    "ruff>=0.15.22,<0.16",
]
```

**Confirmed: `[project].dependencies` remains empty (`[]`)** — Batch 1B-A has zero runtime dependencies (Section 6 item 7).

**Ruff configuration (`AUTHOR-APPROVED`, Decision Group 4):**

```toml
[tool.ruff]
target-version = "py312"
line-length = 88

[tool.ruff.lint]
select = ["E4", "E7", "E9", "F", "I", "UP", "B", "RUF"]
```

Rules: no preview rules; no ignored rules; no per-file exemptions. Format verification: `ruff format --check .`. Lint verification: `ruff check .`. No automatic fixing during Batch 1B-A verification.

**mypy configuration (`AUTHOR-APPROVED`, Decision Group 4):**

```toml
[tool.mypy]
python_version = "3.12"
strict = true
warn_unused_configs = true
show_error_codes = true
pretty = true
```

Rules: no `ignore_missing_imports`; no plugin; no per-module relaxation; no suppression merely to obtain a passing result. Verification target: `mypy src tests`.

**pytest configuration (`AUTHOR-APPROVED`, Decision Group 4):**

```toml
[tool.pytest]
minversion = "9.1"
testpaths = ["tests"]
addopts = [
    "-ra",
    "--strict-config",
    "--strict-markers",
    "--import-mode=importlib",
]
```

Rules: no coverage plugin; no network plugin; no async-test plugin; no custom markers; no `pythonpath` manipulation. Tests execute against the package installed in the uv project environment.

**Not silently resolved by this plan:** any configuration section, dependency, or tool option beyond the four `[tool.*]`/`[dependency-groups]` blocks recorded above.

### 9b. Batch 1B-A Package-Root Content Plan (Decision Group 4, `AUTHOR-APPROVED`)

**`src/btmm_ai_scanner/__init__.py` is not created by this document.** Its exact future content:

```python
"""Deterministic software foundation for the BTMM and POI AI scanner."""
```

Rules: no `__version__` constant; no configuration re-exports; no filesystem access; no environment-variable access; no logging setup; no network activity; no import-time initialization of any kind. **`pyproject.toml` remains the authoritative project-version source** — the package root does not duplicate or re-derive the version.

## 10. File-by-File Responsibilities

Responsibilities are recorded per-file in Section 9's "Purpose" and "Required content"/"Prohibited content" columns. Summarized by batch:

- **1B-A (Toolchain and Package Shell):** establishes `.gitignore` hygiene, the installable package boundary, and configuration-precedence code, with zero domain contracts. Its two tests only prove the package imports and that precedence ordering works — neither touches trading logic.
- **1B-B (Core Foundation Contracts):** establishes value types (identity, fingerprint, version) and the first five data-contract shapes (A, B, M, N, plus Q/R stubs), with zero executable validation or ingestion logic.
- **1B-C (Validation and Eligibility Foundation):** establishes the Group 6 policy enums and the 8-step eligibility gate as code *interfaces*, explicitly without any provider-specific detection mechanism (Blocking Decisions #26–#27 remain open).
- **1B-D (Audit and Operational Logging Foundation):** establishes the audit-event shape, an append-only writer *interface* (no physical storage target chosen — Blocking Decision #22 remains open), and structured logging configuration, kept strictly separate from audit.
- **1B-E (Provider-Neutral Ingestion Boundary):** establishes `MarketDataSourcePort` and its request/result shapes, plus a single deterministic `OFFLINE_FILE` stub — no provider-specific adapter, no network dependency.
- **1B-F (CI Foundation):** establishes the offline-safe verification workflow that exercises Batches A–E's lint/type/test tooling — no deployment, no credentials, no live connection.

## 11. Permitted Content

- Type/shape definitions matching an already-approved Data Contract letter or Decision Group
- Pure functions and interfaces with no I/O side effects beyond the explicitly named exception (`ingestion/offline_file_source.py` reading one fixed local file)
- Deterministic, synthetic test doubles
- Cross-references (docstrings/comments) citing the specific Phase 0G/Phase 1A/Phase 1B document and section that authorizes the content

## 12. Prohibited Content

- Any entry price, stop loss, take profit, position size, risk percentage, leverage, profit target, trading instruction, composite trading score, or profitability outcome field
- Any POI, BTMM, HH/HL/LH/LL/BOS/CHoCH, or automated market-structure detection logic
- Any live network call, broker credential, FXCM/TradingView connection, or web-scraping code
- Any AI/model inference code
- Any database, migration, or container definition
- Any private-book content or reference to `references/private/` at runtime

## 13. Dependency Direction

Unchanged from `REPOSITORY_SCAFFOLD_PLAN.md` Section 4: `A --> B` means "A depends on B." Within the batches above: `config` has no dependency; `contracts` depends on `config`; `validation` depends on `contracts` and `config`; `audit`/`observability` depend on `contracts`/`config`; `ingestion` depends on `contracts` and `config`. No batch introduces a dependency running the opposite direction, and no cycle is introduced — this is a strict subset of the already-confirmed-acyclic full dependency graph.

## 14. Implementation Batches

| Batch | Name | Scope (changed paths) | Depends on | Author decisions required | Implementation risks | Tests required | Acceptance criteria | Rollback boundary | Independently committable |
|---|---|---|---|---|---|---|---|---|---|
| 1B-A | Toolchain and Package Shell | **10 changed paths** (Section 9): 9 new files + 1 modified existing file (`.gitignore`) — **IMPLEMENTED, committed as `47cfd699bb7f4893774579f1693abbbb57b91607`, pushed to `origin/main`** | None (first batch) | **Fully resolved:** #1–#6, #8–#12 (exact patch version, package identity, layout, build backend, `.python-version`, dependency versions, full metadata field set, OS position, license position, initial version). **Still required:** none for the items this batch actually needs — remaining open items (#7 Batch 1B-B Pydantic constraint; #18–#21, #25–#30) belong to later batches, not to 1B-A itself | Package-identity risk is resolved; remaining risk is limited to exact function signatures/exception classes/tool-configuration sections, none of which was chosen by documentation alone — these are now fixed by the implementation itself | `test_import_smoke.py`, `test_config_precedence.py` | **PASSED** — Package installs via `uv`; both test files pass (34 collected, 34 passed); `.gitignore` correctly excludes build/tool artifacts; no YAML/config data file exists; runtime dependencies remain empty | Revert this batch alone via `git revert 47cfd699bb7f4893774579f1693abbbb57b91607` (no later batch exists yet) | YES (it is the first batch) — **exercised** |

**Batch 1B-A status: `IMPLEMENTED`, `VERIFIED`, `COMMITTED`, `PUSHED`, `NOT PRODUCTION-APPROVED`.** Technical implementation `ACCEPTED`; procedural deviations `DISCLOSED AND EXCEPTIONALLY ACCEPTED` (see `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 18c for full detail). The Python minor-version alias anomaly remains `ACKNOWLEDGED`, `EXTERNAL`, `FUNCTIONALLY LIMITED`, and `NON-BLOCKING FOR THIS EXACT-PATCH PROJECT` — no repair was authorized or performed (Section 18d of the same document). Batches 1B-B through 1B-F remain entirely unimplemented; no Batch 1B-B path exists in this repository.
| 1B-B | Core Foundation Contracts | 13 inventoried files (**current minimum future changed-path count: 15** — the 13 files plus `pyproject.toml` and `uv.lock`, both to be modified to add the approved `pydantic>=2.13.4,<2.14` dependency; **this count remains provisional** pending author decision on two additional candidate test files, `tests/unit/test_validation_result.py` and `tests/unit/test_provenance_record.py`, neither yet added to the inventory) | 1B-A | #18–#21, #25 (enum, serialization, fingerprint, timestamp semantics — shape only); **RESOLVED FOR BATCH 1B-B SCOPE by Decision Group 1** (`PHASE_1B_AUTHOR_DECISION_REGISTER.md` §19): Pydantic dependency range, UUIDv7 validation-only boundary, SHA-256 fingerprint validation-only boundary, canonical-JSON/JSON-Schema/manifest-file deferral | Wrong contract module boundary requires refactor before later batches build on it | 5 contract/type unit tests (possibly 7, pending the two candidate test files above) | All contract shapes construct valid/invalid cases correctly; no entry/risk field exists; `pydantic` resolves within `>=2.13.4,<2.14`; no external UUID, SemVer, or canonical-JSON package appears; no JSON Schema file or manifest file is written | Revert to end of 1B-A | YES, once 1B-A is committed |

**Phase 1B-B Decision Group 1 (`AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`, `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`):** approved future dependency `pydantic>=2.13.4,<2.14` (Pydantic v2 required; dataclass placeholders rejected; `pydantic-settings` deferred; no second validation framework permitted). **No external UUID dependency is approved. No external SemVer dependency is approved. No canonical-JSON dependency is approved.** UUIDv7 and SHA-256 fingerprint types are validation-only in Batch 1B-B (no generation of either). No JSON Schema file is generated in Batch 1B-B. Full detail: `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 19.

**Phase 1B-B Decision Group 2 (`AUTHOR-APPROVED`, `NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`, `BATCH 1B-B NOT AUTHORIZED FOR EXECUTION`):** approved exact `ContractModel` shared base configuration, `UUIDv7`/`SHA256Fingerprint` annotated-type mechanics, and the project-owned `SemVer` type's full grammar, parsing, and precedence behavior — full detail in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 20. **This decision adds no inventory row.** Batch 1B-B remains **13 inventoried files**. Minimum changed-path count remains **15** (13 inventoried files + `pyproject.toml` + `uv.lock`). **Final changed-path count remains unresolved**, pending the same two candidate test files noted under Decision Group 1 (`tests/unit/test_validation_result.py`, `tests/unit/test_provenance_record.py`).
| 1B-C | Validation and Eligibility Foundation | 12 files | 1B-B | #18, #26–#27 (enum finality, detection mechanism explicitly still deferred) | Premature provider-specific logic could leak in if not reviewed carefully | 7 unit tests | Eligibility gate matches the approved 8-step sequence; zero synthetic-fill code exists | Revert to end of 1B-B | YES, once 1B-B is committed |
| 1B-D | Audit and Operational Logging Foundation | **7 files** (corrected from a prior mislabeling of 6 — Section 9 lists `audit/__init__.py`, `audit/events.py`, `audit/writer.py`, `observability/__init__.py`, `observability/logging_config.py`, `test_audit_log_separation.py`, `test_secret_redaction.py`) | 1B-B (contracts/types) | None new (Group 4/5 already approved) | Conflating audit and operational logs would violate an approved separation | 2 unit tests | Audit and log stores remain structurally separate; secret-redaction test passes | Revert to end of 1B-C | YES, once 1B-B is committed (does not require 1B-C) |
| 1B-E | Provider-Neutral Ingestion Boundary | 7 files | 1B-B (contracts) | None new (Group 7 already approved at policy level) | Any accidental provider-specific code would violate `INTERFACE_ONLY`/`OFFLINE_FILE`-only scope | 2 unit tests | Port stays provider-neutral; offline stub makes zero network calls | Revert to end of 1B-D (or 1B-B if 1B-D not yet done) | YES, once 1B-B is committed |
| 1B-F | CI Foundation | 1 file | 1B-A (pyproject/uv.lock must exist for CI to run against) | #28 (trigger policy); #29–#30 (repository settings, not files) | An overly permissive workflow could accidentally gain network/credential access | N/A (workflow itself is the verification layer) | Workflow runs Ruff/mypy/pytest against Batches A–E's code, offline-safe, on the approved trigger | Revert to end of 1B-E (or earliest batch present) | YES, once 1B-A is committed |

**Total across all batches: 50 changed paths** (10 + 13 + 12 + 7 + 7 + 1 = 50), matching Section 9's corrected inventory total.

**Batch 1B-A Runtime and Dependency Baseline (`AUTHOR-APPROVED`):**

| Aspect | Approved value |
|---|---|
| Interpreter | Python `3.12.13` |
| Supported Python range (`requires-python`) | `>=3.12,<3.13` |
| Runtime dependencies | **NONE** |
| Development dependencies | `pytest>=9.1.1,<10`; `mypy>=2.3.0,<3`; `ruff>=0.15.22,<0.16` |
| Build dependency | `uv_build>=0.11.30,<0.12` |
| Tool requirement | `uv==0.11.30` (via `[tool.uv].required-version`) |
| Configuration-module scope | `config/enums.py` and `config/loader.py` are standard-library-only — no YAML parsing, no Pydantic, no `pydantic-settings` |

**Batch 1B-A Metadata, Configuration Contract, Tests and Git Hygiene (Decision Group 3, `AUTHOR-APPROVED`):**

| Aspect | Approved value |
|---|---|
| Project metadata | Full `[project]` field set — see Section 9a |
| Classifiers | Six approved values (Section 6 item 9) |
| Minimum-OS position | Windows 11 x64 validated initial environment; cross-platform compatibility claim `NOT YET ESTABLISHED` |
| License-field position | `license = "LicenseRef-Proprietary"`; no licence file |
| Configuration enums | `InternalSymbol` (3 values), `Timeframe` (8 values) — see Section 17 |
| Configuration loader | `BTMM_CONFIG_` prefix, 3-level precedence, shallow merge, secret-key rejection — see Section 17 |
| Test boundaries | See Section 23 |
| `.gitignore` | Joins Batch 1B-A as a modified existing file — see Section 9 |

**Batch 1B-A remains `NOT YET AUTHOR-APPROVED FOR EXECUTION`.** Package identity, interpreter, build backend, dependency versions, the full metadata field set, the OS position, the license position, and the configuration/test/git-hygiene boundaries are all now resolved; exact function signatures, exact exception classes, exact `__init__.py` contents, exact Ruff/mypy/pytest configuration sections, the installation sequence, and the rollback sequence remain unresolved and are not silently decided here. **Recommendation origin: `ENGINEERING-RECOMMENDED`. Current author-decision status: `AUTHOR-APPROVED` (for the baselines recorded above). Implementation status: `NOT YET IMPLEMENTED`. Production status: `NOT PRODUCTION-APPROVED`.**

**No batch is implemented by this document.** Each requires its own separate, explicit author instruction to create.

## 15. File-Creation Order

Matches Section 9's "Creation order" column exactly: **0** (`.gitignore`, modified first, precedes every other Batch 1B-A path) → **1–9** (Batch 1B-A's nine new files) → **10–22** (Batch 1B-B) → **23–34** (Batch 1B-C) → **35–41** (Batch 1B-D, corrected to 7 files/paths) → **42–48** (Batch 1B-E) → **49** (Batch 1B-F). Within 1B-D and 1B-E, either batch may follow 1B-B directly (both depend only on 1B-B, not on each other or on 1B-C) — the numbering above reflects one valid linear order, not an additional dependency. **`.gitignore`'s order-0 position is a deliberate numbering choice** (preceding order 1 rather than renumbering all 49 subsequent entries) — it does not imply any dependency relationship beyond "modified before the rest of Batch 1B-A."

## 16. Dependency-Installation Order

**No dependency is installed by this document.** The proposed future order, once approved: (1) install Python at the approved patch version; (2) install `uv`; (3) `uv` resolves and locks runtime dependencies (Pydantic v2) into `uv.lock`; (4) `uv` resolves and locks development dependencies (pytest, mypy, Ruff) into the same lockfile; (5) `uv sync` (or equivalent) materializes the environment. No step above is executed by this task.

### 16a. Batch 1B-A Approved Execution Sequence — Stages A–J (Decision Group 4, `AUTHOR-APPROVED`)

**No stage below is executed by this document.** This is the exact future execution sequence, once Batch 1B-A is separately, explicitly authorized. Each stage is a distinct checkpoint; an unexpected result at any stage stops the sequence (Section 27).

**STAGE A — Repository preflight:** (1) verify expected HEAD; (2) verify clean working tree; (3) verify `origin/main` synchronization; (4) verify no Batch 1B-A artifact exists; (5) verify private references remain ignored.

**STAGE B — Install exact uv version.** Future authorized command: `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/0.11.30/install.ps1 | iex"`. Verification: `uv --version`. Required result: `uv 0.11.30`. **Prohibited:** `uv self update`; silent substitution of another uv version.

**STAGE C — Verify Python availability.** Inspect whether uv 0.11.30 can provide exact Python 3.12.13. **Stop when unavailable.** Do not: substitute 3.12.10; substitute another patch; upgrade uv silently; edit repository files before resolution.

**STAGE D — Install managed Python.** Future authorized command: `uv python install 3.12.13 --no-bin`. Rules: verify the managed interpreter exists; do not remove Python 3.14.6; do not replace general Python aliases; do not use `--default`; do not use `--force`; do not use `--upgrade`; do not alter global Python associations.

**STAGE E — Protect generated artifacts.** Modify `.gitignore` before any project-environment command. Preserve `references/private/*`. Add only the approved exclusions (Section 9's `.gitignore` row).

**STAGE F — Create handwritten files.** Do not run `uv init`. Create manually: `pyproject.toml`; `.python-version`; `src/btmm_ai_scanner/__init__.py`; `src/btmm_ai_scanner/config/__init__.py`; `src/btmm_ai_scanner/config/enums.py`; `src/btmm_ai_scanner/config/loader.py`; `tests/test_import_smoke.py`; `tests/test_config_precedence.py`. **`uv.lock` is generated, not handwritten** (Stage G).

**STAGE G — Generate lockfile.** Future commands: `uv lock`; `uv lock --check`.

**STAGE H — Create project environment.** Future command: `uv sync --locked`. Record: `.venv/` must remain ignored; project package and development dependencies are installed from the locked metadata.

**STAGE I — Verification.** Future commands: `uv lock --check`; `uv run --locked python --version`; `uv run --locked python -c "import btmm_ai_scanner; import btmm_ai_scanner.config"`; `uv run --locked ruff format --check .`; `uv run --locked ruff check .`; `uv run --locked mypy src tests`; `uv run --locked pytest`. Required Python result: `Python 3.12.13`. **No Ruff auto-fix is permitted.**

**STAGE J — Git-scope verification.** Confirm exactly ten changed paths: one modified tracked file (`.gitignore`); nine new files, including generated `uv.lock`; `.venv/` absent from Git status; no extra generated file; no private reference; no cache, build, or coverage artifact.

**No command in Stages A–J is executed by this documentation task.**

## 17. Configuration and Secrets Scope

**No configuration or secrets file is created by this document.**

- **Project defaults:** proposed to live in a YAML file whose name and directory placement remain `REQUIRES AUTHOR DECISION` (Blocking Decisions #13–#14) — explicitly **not** placed under the protected top-level `config/` path by default, pending that decision.
- **Environment-specific non-secret configuration:** proposed as a second, environment-named YAML file, layered on top of defaults, per the approved three-level precedence.
- **Runtime environment variables:** the third, highest-precedence layer, per Group 3 — never a file.
- **Development-only local `.env`:** git-ignored, used only for local developer convenience — not created by this document; already covered by the existing `.gitignore` entry.
- **Prohibited values in any YAML file:** passwords, tokens, API keys, broker credentials, or any other secret.
- **Precedence testing:** `tests/test_config_precedence.py` (Batch 1B-A) exercises the precedence order using synthetic test doubles, not real files or real secrets.
- **Resolved-configuration lineage:** proposed to be recorded via a `configuration_version` reference (already named among the ingestion result version references in Decision Group 7), not yet implemented.
- **Secrets exclusion:** enforced structurally by never importing or reading `.env` contents into any YAML file or any manifest, and by `test_secret_redaction.py` (Batch 1B-D) asserting no secret ever reaches a log or audit event.

No production, staging, or live-environment configuration file is proposed — there is no present need at this scaffold stage.

**Batch 1B-A Dependency Baseline note (`AUTHOR-APPROVED`, referenced from Section 6 row 7):** because Batch 1B-A creates no actual YAML file (the filename/placement decisions, #13–#14, remain deferred), `config/enums.py` and `config/loader.py` need nothing beyond the Python standard library to fulfil their Batch 1B-A scope — foundational enums (`enum.Enum`/`StrEnum`), plain dict/mapping merges, `os.environ` reads, deterministic precedence resolution, and secret-value exclusion. **No YAML parser, Pydantic model, or `pydantic-settings` is required, installed, or used in Batch 1B-A.** Pydantic remains approved for executable data contracts beginning in Batch 1B-B (Section 19); its exact version constraint remains unresolved.

### 17a. Configuration Enum Contract (Decision Group 3, `AUTHOR-APPROVED`)

| Field | Detail |
|---|---|
| Exact path | `src/btmm_ai_scanner/config/enums.py` |
| Approved classes | `InternalSymbol` (`StrEnum`); `Timeframe` (`StrEnum`) |
| `InternalSymbol` values | `XAUUSD`, `EURUSD`, `GBPUSD` (uppercase strings, matching the approved values exactly) |
| `Timeframe` values | `M1`, `M5`, `M15`, `H1`, `H3`, `H4`, `D1`, `W1` (uppercase strings, matching the approved values exactly) |
| Permitted content | Two `StrEnum` classes with the values above only |
| Prohibited content | Any POI-type enum; any lifecycle-state enum; any BTMM-state enum; any validation-state enum; any provider-specific symbol; any unsupported timeframe; any resampling logic |
| Standard-library-only requirement | Yes — `enum.StrEnum` (stdlib since Python 3.11) only, no third-party import |
| Required tests | Exercised indirectly by `tests/test_import_smoke.py` (import) and `tests/test_config_precedence.py` (usage in precedence merging) |
| Deferred behavior | Any helper/validation method beyond the enum definitions themselves is not defined here |

**Exact future implementation (`AUTHOR-APPROVED`, Decision Group 4):**

```python
from enum import StrEnum


class InternalSymbol(StrEnum):
    XAUUSD = "XAUUSD"
    EURUSD = "EURUSD"
    GBPUSD = "GBPUSD"


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    H1 = "H1"
    H3 = "H3"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"
```

Rules: no aliases; no auto-generated values (`enum.auto()`); no POI-state enum; no lifecycle-state enum; no BTMM-state enum; no validation-state enum; no provider-specific value; no unsupported timeframe; no resampling behavior.

### 17b. Configuration Loader Contract (Decision Group 3, `AUTHOR-APPROVED`)

| Field | Detail |
|---|---|
| Exact path | `src/btmm_ai_scanner/config/loader.py` |
| Approved responsibilities | Read approved non-secret runtime environment variables; normalize approved environment keys; merge configuration layers deterministically; return a new mapping; preserve caller-owned input mappings; standard library only |
| Environment-variable prefix | `BTMM_CONFIG_` (example: `BTMM_CONFIG_LOG_LEVEL` → `log_level`) |
| Approved precedence (later overrides earlier) | (1) Project defaults; (2) Environment-specific non-secret overrides; (3) Runtime environment overrides |
| Approved merge behavior | **Shallow top-level merge only** — no nested/deep merge |
| Permitted content | Environment reading, key normalization, shallow deterministic merging, returning a new mapping, secret-value exclusion |
| Prohibited content | YAML parsing; filesystem configuration loading; Pydantic models; `pydantic-settings`; nested merge behavior; production configuration; provider-specific configuration; configuration persistence; logging configuration values; credential storage; trading-rule validation |
| Standard-library-only requirement | Yes |
| Required tests | `tests/test_config_precedence.py` |
| Deferred behavior | Nothing remains deferred at the interface level — the exact signature, precedence, merge, key-validation, and runtime-environment behaviors are all recorded below (Decision Group 4). The internal implementation of each private helper is not written here. |

**Exact future public interface (`AUTHOR-APPROVED`, Decision Group 4):**

```python
from collections.abc import Mapping

ENV_PREFIX = "BTMM_CONFIG_"


def load_configuration(
    project_defaults: Mapping[str, object] | None = None,
    environment_overrides: Mapping[str, object] | None = None,
    *,
    environ: Mapping[str, str] | None = None,
) -> dict[str, object]:
    ...
```

**Approved precedence:** `project_defaults` → `environment_overrides` → runtime values extracted from `environ`. Later layers replace earlier values. `None` means an empty layer. `environ=None` reads `os.environ`; a supplied `environ` mapping completely isolates the call from the machine environment. Caller-owned mappings remain unchanged; a new `dict` is returned. Merge behavior is shallow — a later nested mapping **replaces** an earlier nested mapping entirely (no recursive merge).

**Mapping-key rules:** keys must be strings; keys must be non-empty; keys must already use lowercase snake_case (conceptual accepted pattern: `[a-z][a-z0-9_]*`). Invalid keys raise `InvalidConfigurationKeyError`. Mapping keys are never silently renamed.

**Runtime-environment rules:** only keys beginning with the exact, case-sensitive prefix `BTMM_CONFIG_` are considered; the prefix is stripped; the suffix is converted to lowercase; the normalized suffix is validated against the same key rules above; an empty suffix is invalid; duplicate runtime variables that normalize to the same key are invalid; unprefixed variables are ignored; runtime values remain strings.

### 17c. Secret Boundary (Decision Group 3, `AUTHOR-APPROVED`)

The non-secret configuration loader must **reject** any key containing indicators such as: `password`, `secret`, `token`, `credential`, `api_key`, `private_key`. Rules: do not read `.env`; do not return credential values; do not log credential names or values; do not create credential defaults; do not add provider API keys. **Actual secret retrieval remains a separate, future, unbuilt boundary** — this loader only excludes secret-like keys, it does not manage secrets.

**Exact detection behavior (`AUTHOR-APPROVED`, Decision Group 4):** detection is case-insensitive; a match anywhere in the normalized key is rejected; detection applies to all three configuration layers (project defaults, environment-specific overrides, runtime environment); a match raises `SecretConfigurationKeyError`; neither the rejected key nor its value may be exposed (e.g., in an exception message or a log line).

### 17d. Configuration Package Exports (Decision Group 4, `AUTHOR-APPROVED`)

**`src/btmm_ai_scanner/config/__init__.py` is not created by this document.** Its exact future export surface:

```python
from .enums import InternalSymbol, Timeframe
from .loader import (
    ENV_PREFIX,
    ConfigurationError,
    InvalidConfigurationKeyError,
    SecretConfigurationKeyError,
    load_configuration,
)

__all__ = [
    "ENV_PREFIX",
    "ConfigurationError",
    "InternalSymbol",
    "InvalidConfigurationKeyError",
    "SecretConfigurationKeyError",
    "Timeframe",
    "load_configuration",
]
```

**No other public configuration API enters Batch 1B-A.**

### 17e. Exception Hierarchy (Decision Group 4, `AUTHOR-APPROVED`)

**Exact future hierarchy:**

```python
class ConfigurationError(ValueError):
    """Base error for invalid non-secret configuration."""


class InvalidConfigurationKeyError(ConfigurationError):
    """Raised when a configuration key has an invalid form."""


class SecretConfigurationKeyError(ConfigurationError):
    """Raised when a secret-like key enters non-secret configuration."""
```

**Rules:** no custom constructors in Batch 1B-A; no rejected key name in an exception message; no rejected value in an exception message; no provider-specific exception; no trading-domain exception.

**Approved generic messages:**
- `InvalidConfigurationKeyError`: `"Configuration keys must use lowercase snake_case."`
- `SecretConfigurationKeyError`: `"Secret-like keys are not permitted in non-secret configuration."`

### 17f. Private Implementation Boundary (Decision Group 4, `AUTHOR-APPROVED`)

`loader.py` may contain private helpers only for: key validation; secret-indicator detection; runtime-environment extraction; shallow layer merging. **Private helper names must begin with an underscore.**

**Prohibited helpers and facilities:** a YAML reader; a `.env` reader; a recursive or nested merge utility; a secret loader; a provider configuration loader; a global configuration singleton.

## 18. Rule and Schema Manifest Scope

**No manifest file or manifest directory is created by this document.** Per Part 11's rules (unchanged, reaffirmed here): `manifests/rules/` and `manifests/schemas/` are created only when their first real, reviewed manifest exists — never as empty directories, never via `.gitkeep`. No private-book text may ever enter a manifest. No manifest may approve a trading rule — it only records already-approved knowledge. Canonical JSON serialization (Blocking Decision #20) remains unresolved. **Exact first proposed filenames** (naming requires separate author approval, per Blocking Decision #15): a first rule-version manifest named illustratively `manifests/rules/measurement_standards_v1.json`, and a first schema-version manifest named illustratively `manifests/schemas/raw_candle_record_v1.json` — both illustrative only, neither created, neither approved.

## 19. Data-Contract Stub Scope

Covered file-by-file in Section 9 (Batch 1B-B rows) and Section 10. Summary: `types.py` (identity/fingerprint/version value types), `raw_candle.py` (Contract A), `normalized_candle.py` (Contract B), `validation_result.py` (Contract N), `provenance_record.py` (Contract M), `rule_version_manifest.py`/`schema_version_manifest.py` (Contracts Q/R, shape only — no manifest I/O). **Resolved by Phase 1B-B Decision Group 1** (`PHASE_1B_AUTHOR_DECISION_REGISTER.md` §19A): Pydantic v2 (`pydantic>=2.13.4,<2.14`) is required for these classes; a plain-dataclass placeholder is explicitly rejected. The exact Pydantic base-model configuration (`frozen`, `extra`, strict validation, etc.) remains unresolved and is deferred to Decision Group 2.

## 20. Validation-Stub Scope

Covered file-by-file in Section 9 (Batch 1B-C rows). Summary: `completeness.py`, `duplicates.py`, `gaps.py` implement the Group 6 enums and *interfaces* only (no provider-specific completion/gap-confirmation mechanism — Blocking Decisions #26–#27 remain open); `eligibility.py` implements the approved 8-step gating sequence. **Kept structurally separate, per the existing Phase 0G/Phase 1A validity-separation principle:** `data_quality_validity` (this batch's actual concern), `poi_validity`, `btmm_validity`, `entry_validity`, and `trade_outcome` (all out of scope for this batch and this scaffold entirely). No automatic conflicting-duplicate winner is designed — `duplicates.py`'s conflicting-duplicate path always routes to `QUARANTINED`, per the already-approved policy.

## 21. Provenance and Audit Stub Scope

Covered file-by-file in Section 9 (Batch 1B-D rows). Summary: `audit/events.py` (Contract O shape), `audit/writer.py` (append-only interface, no physical storage target chosen), `observability/logging_config.py` (structured JSON operational logging, explicitly separate from the audit writer). `provenance_record.py` itself is placed in Batch 1B-B (it is a data contract, Contract M) rather than Batch 1B-D, since every other contract in Batch 1B-B already references provenance lineage.

## 22. Ingestion-Interface Scope

Covered file-by-file in Section 9 (Batch 1B-E rows). Summary: `ingestion/port.py` (`MarketDataSourcePort`, abstract), `ingestion/requests.py`/`results.py` (provider-neutral shapes), `ingestion/offline_file_source.py` (the single permitted concrete implementation — reads one fixed local file, no network access, no credential). No FXCM adapter, no TradingView adapter, and no `HISTORICAL_BATCH`/`POLLING`/`STREAMING` retrieval mode is proposed — all remain explicitly not-yet-authorized per Decision Group 7.

## 23. Test Scope

Exact proposed test paths and names are listed in full in Section 8 (tree) and Section 9 (inventory) — 18 test files across Batches 1B-A through 1B-E: `test_import_smoke.py`, `test_config_precedence.py`, `test_identity_and_fingerprint.py`, `test_semver.py`, `test_raw_candle_contract.py`, `test_normalized_candle_contract.py`, `test_manifest_compatibility_classes.py`, `test_candle_completeness.py`, `test_exact_duplicate.py`, `test_conflicting_duplicate_quarantine.py`, `test_missing_gap.py`, `test_no_synthetic_fill.py`, `test_validation_eligibility.py`, `test_processing_version_preservation.py`, `test_audit_log_separation.py`, `test_secret_redaction.py`, `test_ingestion_port_contract.py`, `test_offline_file_stub.py`. **No fixture or test file is created by this document.**

**Phase 0G lifecycle-test restrictions remain fully binding and are unaffected by this scaffold plan:** full lifecycle tests remain limited to the 18 propagated bounded directional POIs (none of which appear in this scaffold at all — POI/lifecycle modules are entirely out of scope for Batches 1B-A–1B-F); Equal Highs/Equal Lows/both Trendlines remain limited to construction/classification/permitted-state/prohibition tests only, once their module exists (it does not, in this scope); generic bounded-lifecycle tests remain `NOT_APPLICABLE` to the 14 non-bounded reference structures. **No detector test is proposed or needed in this initial scaffold** — no detector module exists in Section 8's tree.

### 23a. Batch 1B-A Test Boundaries (Decision Group 3, `AUTHOR-APPROVED`)

**`tests/test_import_smoke.py` — approved coverage:**
- `btmm_ai_scanner` imports
- `btmm_ai_scanner.config` imports
- `InternalSymbol` imports
- `Timeframe` imports
- `config.loader` imports
- Importing performs no filesystem write
- Importing performs no network action

**`tests/test_import_smoke.py` — prohibited scope:** POIs; market structure; BTMM; ingestion; AI; signals; trading; profitability; databases; live providers.

**`tests/test_config_precedence.py` — approved coverage:**
1. Defaults remain when no override exists
2. Environment-specific values override defaults
3. Runtime environment values override both earlier layers
4. Input mappings remain unchanged
5. `BTMM_CONFIG_` is stripped
6. Environment keys are normalized
7. Secret-like keys are rejected
8. Merge results are deterministic
9. No YAML or filesystem input is required
10. Tests use controlled mappings or monkeypatched environment values
11. Tests do not depend on real machine credentials or configuration

**Confirmed for both tests:** no detector test enters Batch 1B-A; no ingestion test enters Batch 1B-A; no lifecycle test enters Batch 1B-A; no AI, signal, risk, or execution test enters Batch 1B-A. All Phase 0G testing restrictions (above) remain unchanged.

**Exact test-function inventory (Decision Group 4, `AUTHOR-APPROVED`):**

`tests/test_import_smoke.py` — exactly three test functions:
1. `test_package_imports`
2. `test_config_public_exports_import`
3. `test_import_has_no_filesystem_or_network_side_effect`

**`test_import_has_no_filesystem_or_network_side_effect` must:** avoid importing the package during test-module collection; import from inside the test function; disable bytecode writing for the isolated import; use a temporary working directory; block attempted network connections; verify the temporary directory remains unchanged; restore modified interpreter state.

`tests/test_config_precedence.py` — exactly 11 test functions:
1. `test_defaults_are_preserved`
2. `test_environment_overrides_defaults`
3. `test_runtime_environment_overrides_all_layers`
4. `test_input_mappings_are_not_mutated`
5. `test_runtime_environment_keys_are_normalized`
6. `test_shallow_merge_replaces_nested_value`
7. `test_secret_like_keys_are_rejected`
8. `test_invalid_configuration_key_is_rejected`
9. `test_empty_runtime_suffix_is_rejected`
10. `test_duplicate_normalized_runtime_keys_are_rejected`
11. `test_result_is_deterministic`

**Rules:** `test_secret_like_keys_are_rejected` may be parameterized over the six secret indicators and the three configuration layers. Tests pass controlled `environ` mappings. Tests never rely on real machine configuration or credentials.

## 24. CI Scope

Exact proposed workflow path: `.github/workflows/ci.yml` (Batch 1B-F, the only file in that batch). Planned checks: `uv lock` consistency check, Ruff format check, Ruff lint, mypy, pytest — all offline-safe. **Rules (binding, unchanged from Decision Group 5):** no private-book access; no live credentials; no provider connection; no deployment; no signals; no order execution; no write-back to repository files. **Trigger policy (Blocking Decision #28), branch-protection policy (#29), and mandatory pull-request policy (#30) remain author decisions** — the latter two are GitHub repository *settings*, not files this scaffold creates, and are explicitly out of this document's file-scope authority.

## 25. Documentation Updates

This task updates exactly two existing documents (in addition to creating this one):
- `docs/architecture/REPOSITORY_SCAFFOLD_PLAN.md` — new Section 9, "Phase 1B Exact Scope Planning" (Part 17 below).
- `docs/PROJECT_STATE.md` — new Section 23 (Part 18 below).

No other document is modified.

## 26. Verification Commands

**No command below is executed by this document.** Once Batch 1B-A is separately approved and implemented, the following command *categories* (not exact invocations, since exact dependency/version details remain Blocking Decisions) would verify it: interpreter-version check; `uv` environment sync; `uv run pytest` (import smoke + config precedence); `uv run ruff format --check`; `uv run ruff check`; `uv run mypy`. Exact commands are deferred to Part 16 (Command Plan) at implementation time, not fixed here.

## 27. Rollback and Recovery

Each batch's rollback boundary is recorded in Section 14. General principle: since batches are committed independently and in the strict order of Section 15, rolling back means reverting the single most recent batch's commit(s) — no batch's rollback requires touching an earlier batch's files, because dependencies only ever point to earlier, already-stable batches (Section 13). No batch writes to any file outside `src/btmm_ai_scanner/`, `tests/`, `.github/workflows/`, or the repository-root toolchain files (`pyproject.toml`, `uv.lock`, `.python-version`) — so rollback never risks `docs/`, `knowledge/`, or `references/`.

### 27a. Batch 1B-A Approved Rollback Procedure (Decision Group 4, `AUTHOR-APPROVED`)

**Before commit, on any unexpected result during Stages A–J (Section 16a):** (1) stop; (2) report the discrepancy; (3) do not improvise a version or dependency replacement; (4) do not stage or commit partial work.

**Approved repository rollback:** restore only `.gitignore`; delete only the nine approved new paths; delete only the generated `.venv/` directory; remove empty `src/` and `tests/` directories created solely by the failed batch; verify return to the original clean checkpoint.

**Prohibited rollback commands:** `git reset --hard`; `git clean -fd`; `git clean -fdx`; force push; deleting `references/private/`; broad deletion of unrelated untracked files.

**Installed tooling:** installed `uv` is not automatically removed; installed managed Python is not automatically removed. Removing either requires separate authorization.

**After commit:** use a reviewed `git revert <batch-commit>`. Never rewrite shared history.

## 28. Phase 1B Scaffold Acceptance Criteria

A batch is acceptable for merge only if: (1) every file it adds appears in Section 9's inventory with a matching batch label; (2) every test listed for that batch exists and passes; (3) Ruff format/lint and mypy pass with zero errors; (4) no file outside the batch's declared scope was touched; (5) no entry/risk/execution/POI/BTMM/AI content was introduced; (6) every blocking decision listed against that batch in Section 6 has been separately author-resolved before the batch is implemented; (7) the batch was reviewed and committed on its own, not bundled with a later batch.

### 28a. Batch 1B-A Exact Acceptance Criteria (Decision Group 4, `AUTHOR-APPROVED`)

Batch 1B-A passes implementation review only when: exactly ten approved paths changed; `.gitignore` preserves `references/private/*`; Python is exactly `3.12.13`; `uv` is exactly `0.11.30`; `uv.lock` exists; `uv lock --check` passes; runtime dependencies remain empty; only `pytest`, `mypy`, and Ruff are development dependencies; Ruff format check passes; Ruff lint passes; mypy passes; pytest passes; imports have no filesystem or network side effect; no YAML exists; no Pydantic exists; no provider or ingestion logic exists; no POI or BTMM logic exists; no AI, signal, risk, or execution logic exists; no secret is stored or exposed; **nothing is staged, committed, or pushed before review.**

## 29. Decisions Requiring Author Approval

All 30 items in Section 6, plus: the package/distribution identity in Section 7; whether to adopt this document's proposed batch boundaries (Section 14) as-is or amend them; whether to adopt the proposed file inventory (Section 9) as-is or amend it before Batch 1B-A begins.

## 30. Approval Status

**`ENGINEERING-RECOMMENDED`. `NOT YET AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`.** This document proposes a file-level scope; it does not approve itself. No batch may be implemented until the author has separately reviewed and approved: package identity (Section 7), the blocking decisions relevant to that batch (Section 6), and the batch's exact file list (Section 9/14). No file listed anywhere in this document exists as a result of this task.

**This Section 30 status statement describes the document as originally authored and remains unchanged. Batch 1B-A's actual, current implementation status is recorded separately in Section 31 below — this addition does not alter Section 30's own approval-status text.**

---

## 31. Phase 1B-A Implementation Closure

**Batch 1B-A: `IMPLEMENTED`, `VERIFIED`, `COMMITTED`, `PUSHED`. `NOT PRODUCTION-APPROVED`.**

- **Commit:** `47cfd699bb7f4893774579f1693abbbb57b91607` — "Implement Phase 1B-A software foundation"
- **Exact ten committed paths:** `.gitignore` (modified); `.python-version`, `pyproject.toml`, `src/btmm_ai_scanner/__init__.py`, `src/btmm_ai_scanner/config/__init__.py`, `src/btmm_ai_scanner/config/enums.py`, `src/btmm_ai_scanner/config/loader.py`, `tests/test_config_precedence.py`, `tests/test_import_smoke.py`, `uv.lock` (all new) — **this matches the plan in Section 9 exactly**, with no path added or removed relative to what was documented before implementation.
- **All acceptance criteria (Section 28a) passed:** exactly ten paths changed; `references/private/*` preserved; Python exactly `3.12.13`; `uv` exactly `0.11.30`; `uv.lock` exists and `uv lock --check` passes; runtime dependencies remain empty; only `pytest`/`mypy`/`ruff` are development dependencies; Ruff format check passes; Ruff lint passes; mypy passes; pytest passes (34 collected, 34 passed); imports have no filesystem or network side effect; no YAML; no Pydantic; no provider/ingestion/POI/BTMM/AI/signal/risk/execution logic; no secret stored or exposed.
- **`.venv/` exists locally but remains git-ignored** — confirmed absent from `git status` and matched by the `.gitignore:10:.venv/` rule.
- **No Batch 1B-B path exists** in the repository. **No prohibited scope entered the batch** (confirmed by dedicated forensic review).

**External toolchain state (distinct from repository implementation — none of the following is a repository file or commit):**
- `uv` `0.11.30` installed at `C:\Users\GOLD COMPUTERS\.local\bin\uv.exe` (not on PATH; PATH was not modified).
- uv-managed Python `3.12.13` installed at `C:\Users\GOLD COMPUTERS\AppData\Roaming\uv\python\cpython-3.12.13-windows-x86_64-none\` — confirmed complete and fully functional.
- Pre-existing Python `3.14.6` remains installed and untouched.
- The generic minor-version convenience alias (`cpython-3.12-windows-x86_64-none`) remains a broken/dangling directory junction — **acknowledged, external, functionally limited, non-blocking for this exact-patch project.** No repair was authorized or performed.

**Explicit author exception (governance, not a technical finding):** during the original implementation run, two genuine bugs (a Ruff `RUF100`/`F401` finding and a Windows-specific `tempfile`/`chdir` race) were fixed by directly editing the already-in-scope test file, rather than stopping and requesting separate re-authorization as the governing procedure required. This procedural deviation was disclosed in full via a dedicated forensic review and **accepted by explicit author exception** — the deviation is not hidden, minimized, or retroactively recharacterized as compliant; it is recorded here exactly as it occurred. Full deviation-by-deviation detail is preserved in `PHASE_1B_AUTHOR_DECISION_REGISTER.md` Section 18c.

**Master file inventory (Section 9) total remains 50 rows** — no row was added or removed by this closure; only the 10 Batch 1B-A rows' scope-status column was updated to `IMPLEMENTED`, and the Batch 1B-A summary row in Section 14 was updated accordingly. Batches 1B-B through 1B-F (39 remaining rows) remain exactly as previously documented — no row beyond Batch 1B-A is marked implemented.
