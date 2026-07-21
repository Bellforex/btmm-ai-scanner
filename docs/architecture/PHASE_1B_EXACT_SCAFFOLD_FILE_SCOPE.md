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
| 1 | Exact Python 3.12 patch version | Not chosen here — recommend pinning the latest stable 3.12.x at implementation time, via review | Pin a specific patch now; float within 3.12 | Determinism (Phase 1A SS13) requires one exact pinned version | Pinning early may miss a security patch; floating breaks determinism | YES | REQUIRES AUTHOR DECISION | YES | 1B-A |
| 2 | Distribution/project name | `btmm-ai-scanner` — **RESOLVED** | `btmm-scanner`, `btmm-ai` (rejected) | Matches the existing GitHub repository name | None significant; the existing repo name was not itself treated as sufficient approval — this decision was separately, explicitly author-approved (Section 7) | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 3 | Python import-package name | `btmm_ai_scanner` — **RESOLVED** | `btmm_scanner` (SUPERSEDED — previously used illustratively in `REPOSITORY_SCAFFOLD_PLAN.md` Section 2; that document's illustrative tree has now been renamed throughout to `btmm_ai_scanner` per this approval) | Mirrors the distribution name closely, avoids future ambiguity | The rename across `REPOSITORY_SCAFFOLD_PLAN.md` has now been applied (Part 2 of this correction) | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 4 | src-layout vs. flat-layout | src-layout (`src/<package>/`) — **RESOLVED** | Flat layout (`<package>/` at repo root) (rejected) | Prevents accidental import of an uninstalled package; matches the existing illustrative tree | None significant | NO — RESOLVED | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 5 | Build backend | `uv_build` — **RESOLVED** | `hatchling`, `setuptools` (rejected) | uv (already approved) does not itself mandate a PEP 517 backend, but the author has now selected uv's own backend | Exact `uv_build` dependency version remains unresolved (see Part 4 remaining-unresolved list) | NO — RESOLVED (backend choice only) | AUTHOR-APPROVED (origin: ENGINEERING-RECOMMENDED) | YES — APPROVED | 1B-A |
| 6 | Whether to create `.python-version` | Yes — **RESOLVED, REQUIRED in Batch 1B-A** (no longer conditional) | Rely on `pyproject.toml`'s `requires-python` only (rejected) | Pins the exact local/dev interpreter for uv | Exact file *content* (the patch value) still depends on unresolved item #1 | PARTIAL — inclusion RESOLVED; exact content still blocking | AUTHOR-APPROVED (inclusion) / REQUIRES AUTHOR DECISION (exact patch content, origin: ENGINEERING-RECOMMENDED) | YES — inclusion APPROVED; content still required | 1B-A |
| 7 | Exact runtime dependency versions | Not chosen here | Loosely-pinned ranges vs. exact pins | Exact versions affect `uv.lock` reproducibility | Unpinned/loose versions reduce determinism | YES | REQUIRES AUTHOR DECISION | YES | 1B-A / 1B-B |
| 8 | Exact development dependency versions | Not chosen here | Same as #7, for pytest/mypy/Ruff | Same as #7 | Same as #7 | YES | REQUIRES AUTHOR DECISION | YES | 1B-A / 1B-F |
| 9 | `pyproject.toml` metadata fields | Minimal PEP 621 set: name, version, description, readme, requires-python, license, authors, classifiers | A larger metadata set (urls, keywords, etc.) | Minimum viable metadata for a private, pre-release package | Missing fields may need later rework | YES | REQUIRES AUTHOR DECISION (exact values) | YES | 1B-A |
| 10 | Minimum supported operating systems | No OS restriction proposed (pure-Python) | Restrict to Windows only, or Linux/CI-only | Affects CI matrix and classifiers | An untested OS could fail silently if later restricted | NO for scaffold itself; YES for CI matrix | REQUIRES AUTHOR DECISION | YES | 1B-F |
| 11 | License-field position | SPDX expression in `[project.license]`, plus a `LICENSE` file at repo root | License text embedded only in `pyproject.toml` | Matches current PEP 639 guidance | None significant | YES (which license, if any, is unresolved) | REQUIRES AUTHOR DECISION | YES | 1B-A |
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

**Recalculated totals, following the Phase 1B-0 Package Identity and Layout decision:**

| Category | Count | Items |
|---|---|---|
| Total blocking-decision rows | 30 | 1–30 |
| Author-approved decisions | 6 | 2 (distribution name), 3 (import package), 4 (layout), 5 (build backend), 6 (`.python-version` inclusion), 12 (initial version) |
| Remaining unresolved decisions (still blocking a near-term batch) | 16 | 1, 7, 8, 9, 10, 11, 18, 19, 20, 21, 25, 26, 27, 28, 29, 30 |
| Deferred decisions (scope beyond the current batches, not yet blocking) | 8 | 13, 14, 15, 16, 17, 22, 23, 24 |

**6 + 16 + 8 = 30.** No decision outside items 2, 3, 4, 5, 6, and 12 was resolved by this correction. Item 6's *inclusion* is resolved; its exact patch-value *content* remains counted among the 16 unresolved items (via item 1). Item 5's backend *choice* is resolved; its exact dependency version remains a separately-tracked unresolved implementation detail (see Part 4 remaining-unresolved list, not a numbered row of its own).

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

**No directory or file in this tree is created by this document.** `measurements/`, `domain/`, `poi/`, `lifecycle/`, `btmm/`, `annotations/`, `replay/`, `scripts/`, `migrations/`, `manifests/rules/`, and `manifests/schemas/` remain correctly absent, matching Section 5's conservative-scaffold principle.

## 9. Exact File Inventory

Every proposed file, one row each. **Creation order** matches Section 15. **Independent commit eligible** reflects whether the file may be committed alone or only as part of its whole batch (Section 14 requires whole-batch review, so no file below is independently committable ahead of its batch — the column records intra-batch groupings only).

| Batch | Exact path | New/Modified | File type | Purpose | Approved decision supported | Required content | Prohibited content | Direct dependencies | Tests required | Blocking unresolved decision | Creation order | Scope status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1B-A | `pyproject.toml` | New | TOML manifest | Project/build metadata, dependency declarations | Register #1–#8, #12–#13; Phase 1B-0 Package Identity and Layout decision (`[project].name = btmm-ai-scanner`, `version = 0.1.0`, package = `btmm_ai_scanner` under `src/`, `[build-system].build-backend = uv_build`) | Build-system table (`uv_build`), project metadata (`btmm-ai-scanner`, `0.1.0`), `src`-layout package discovery pointing at `btmm_ai_scanner`, dependencies, tool config | Secrets, entry/risk fields | None | Import-smoke test passes | #1 (exact patch → `requires-python`), #7–#9, #11 (dependency versions, remaining metadata fields, license) | 1 | Required in initial scaffold |
| 1B-A | `uv.lock` | New | Lockfile | Reproducible dependency resolution | Register #3 | Resolved dependency graph | Secrets | `pyproject.toml` | N/A (generated) | #1, #7–#8 | 2 | Required in initial scaffold |
| 1B-A | `.python-version` | New | Text | Local/dev interpreter pin | Register #1–#2; Phase 1B-0 Package Identity and Layout decision (inclusion) | Exact patch version string | Nothing else | `pyproject.toml`'s `requires-python` | N/A | #1 (exact patch content only — inclusion itself is resolved) | 3 | Required in initial scaffold (inclusion AUTHOR-APPROVED; exact content still blocked on #1) |
| 1B-A | `src/btmm_ai_scanner/__init__.py` | New | Python | Package root, version export | Register #1, #3, #12 | `__version__` constant | Business logic | `pyproject.toml` version | Import smoke test | #3 | 4 | Required in initial scaffold |
| 1B-A | `src/btmm_ai_scanner/config/__init__.py` | New | Python | Marks `config` as a package | Layer: config | Empty/minimal | Business logic | package root | Import smoke test | #3 | 5 | Required in initial scaffold |
| 1B-A | `src/btmm_ai_scanner/config/enums.py` | New | Python | Canonical provider/symbol/timeframe enums | Phase 0G `AUTHOR-APPROVED` lists (`docs/PROJECT_SCOPE.md`); Group 3 | `ProviderEnum`, `SymbolEnum`, `TimeframeEnum` (values from `docs/PROJECT_SCOPE.md`) | Any un-approved symbol/provider/timeframe | None | Config-precedence test (indirect) | None (values already approved) | 6 | Required in initial scaffold |
| 1B-A | `src/btmm_ai_scanner/config/loader.py` | New | Python | Config precedence resolution (defaults → environment → env vars) | Group 3 (configuration precedence) | Precedence-resolution function, env-var override | Any hard-coded secret; any actual YAML file | `config/enums.py` | `test_config_precedence.py` | #13, #14 (no YAML file created until resolved) | 7 | Required in initial scaffold (code only — no YAML data file) |
| 1B-A | `tests/test_import_smoke.py` | New | Python test | Confirms the package imports cleanly | N/A (scaffold integrity) | Single `import btmm_ai_scanner` assertion | Any domain logic | package root | Self | #3 | 8 | Required in initial scaffold |
| 1B-A | `tests/test_config_precedence.py` | New | Python test | Confirms precedence order is honored | Group 3 | Test doubles for the three precedence levels | Real secrets | `config/loader.py` | Self | #13, #14 | 9 | Required in initial scaffold |
| 1B-B | `src/btmm_ai_scanner/contracts/__init__.py` | New | Python | Marks `contracts` as a package | Layer: contracts | Empty/minimal | Business logic | package root | Import smoke test | #19 | 10 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/types.py` | New | Python | UUIDv7 identity type, SHA-256 fingerprint type, SemVer version type | Group 4 (identity, fingerprint, versioning) | Value-type wrappers only | Any entry/risk field | None | `test_identity_and_fingerprint.py`, `test_semver.py` | #20, #21 (canonical serialization / field sets) | 11 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/raw_candle.py` | New | Python | Contract A (Raw Candle Record) shape | Data Contracts Plan Contract A; Group 3/6 fields | Fields per Contract A, `candle_completeness_status`/`duplicate_classification`/`gap_status` placeholders | Normalization logic, entry/risk fields | `contracts/types.py`, `config/enums.py` | `test_raw_candle_contract.py` | #18, #25, #26, #27 (enum/semantics finality) | 12 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/normalized_candle.py` | New | Python | Contract B (Normalized Candle Record) shape | Data Contracts Plan Contract B | Fields per Contract B | Measurement formulas, POI logic | `contracts/raw_candle.py` | `test_normalized_candle_contract.py` | #25 | 13 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/validation_result.py` | New | Python | Contract N (Validation Result) shape | Data Contracts Plan Contract N | Fields per Contract N | POI/BTMM validity fields | `contracts/types.py` | `test_validation_eligibility.py` (Batch C) | #18 (status enum) | 14 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/provenance_record.py` | New | Python | Contract M (Provenance Record) shape | Data Contracts Plan Contract M | Fields per Contract M | Business logic | `contracts/types.py` | Covered by processing-version test | None | 15 | Required in later foundation batch |
| 1B-B | `src/btmm_ai_scanner/contracts/rule_version_manifest.py` | New | Python | Contract Q shape (in-memory type only, no manifest file) | Data Contracts Plan Contract Q; Group 8 | Fields per Contract Q | Actual manifest content/file I/O | `contracts/types.py` | `test_manifest_compatibility_classes.py` | #15, #20 | 16 | Required in later foundation batch (shape only) |
| 1B-B | `src/btmm_ai_scanner/contracts/schema_version_manifest.py` | New | Python | Contract R shape (in-memory type only) | Data Contracts Plan Contract R; Group 8 | Fields per Contract R, compatibility-class enum | Actual manifest content/file I/O | `contracts/types.py` | `test_manifest_compatibility_classes.py` | #15, #20 | 17 | Required in later foundation batch (shape only) |
| 1B-B | `tests/unit/test_identity_and_fingerprint.py` | New | Python test | UUIDv7 vs. SHA-256 distinctness | Group 4 | Assertions that identity ≠ fingerprint | Real production data | `contracts/types.py` | Self | #21 | 18 | Required in later foundation batch |
| 1B-B | `tests/unit/test_semver.py` | New | Python test | MAJOR.MINOR.PATCH parsing/comparison | Group 4 | SemVer parse/compare assertions | N/A | `contracts/types.py` | Self | None | 19 | Required in later foundation batch |
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

**Total proposed files: 49** (all required — `.python-version`'s *inclusion* is no longer conditional, per the Phase 1B-0 Package Identity and Layout decision; only its exact patch-version *content* remains pending Blocking Decision #1). **None is created by this document.** Every row above is either "Required in initial scaffold" (Batch 1B-A, 9 files), "Required in later foundation batch" (Batches 1B-B through 1B-F, 39 files), or explicitly excluded as "Deferred beyond Phase 1B" (manifests, raw-storage I/O, provider adapters — see Section 6) or "Prohibited" (any entry/risk/execution file — none appears above). **No file listed above is marked as already created — every row remains a proposal only.**

## 10. File-by-File Responsibilities

Responsibilities are recorded per-file in Section 9's "Purpose" and "Required content"/"Prohibited content" columns. Summarized by batch:

- **1B-A (Toolchain and Package Shell):** establishes the installable package boundary and configuration-precedence code, with zero domain contracts. Its two tests only prove the package imports and that precedence ordering works — neither touches trading logic.
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

| Batch | Name | Scope (files) | Depends on | Author decisions required | Implementation risks | Tests required | Acceptance criteria | Rollback boundary | Independently committable |
|---|---|---|---|---|---|---|---|---|---|
| 1B-A | Toolchain and Package Shell | 9 files (Section 9) | None (first batch) | Resolved: #2–#6, #12 (package identity, layout, build backend, `.python-version` inclusion, initial version). Still required: #1 (exact patch version), #7–#11 (dependency versions, metadata fields, OS support, license) | Wrong package identity requires a rename across all later batches (identity risk now resolved; remaining risk is limited to unpinned dependency/metadata detail) | `test_import_smoke.py`, `test_config_precedence.py` | Package installs via `uv`; both tests pass; no YAML/config data file exists yet | Revert this batch alone (no later batch exists yet) | YES (it is the first batch) |

**Batch 1B-A remains `NOT YET AUTHOR-APPROVED FOR EXECUTION`.** The Phase 1B-0 Package Identity and Layout decision resolves 6 of the batch's blocking items; the remaining items listed above must still be separately author-approved before any Batch 1B-A file is created.
| 1B-B | Core Foundation Contracts | 13 files | 1B-A | #18–#21, #25 (enum, serialization, fingerprint, timestamp semantics — shape only) | Wrong contract module boundary requires refactor before later batches build on it | 5 contract/type unit tests | All contract shapes construct valid/invalid cases correctly; no entry/risk field exists | Revert to end of 1B-A | YES, once 1B-A is committed |
| 1B-C | Validation and Eligibility Foundation | 12 files | 1B-B | #18, #26–#27 (enum finality, detection mechanism explicitly still deferred) | Premature provider-specific logic could leak in if not reviewed carefully | 7 unit tests | Eligibility gate matches the approved 8-step sequence; zero synthetic-fill code exists | Revert to end of 1B-B | YES, once 1B-B is committed |
| 1B-D | Audit and Operational Logging Foundation | 6 files | 1B-B (contracts/types) | None new (Group 4/5 already approved) | Conflating audit and operational logs would violate an approved separation | 2 unit tests | Audit and log stores remain structurally separate; secret-redaction test passes | Revert to end of 1B-C | YES, once 1B-B is committed (does not require 1B-C) |
| 1B-E | Provider-Neutral Ingestion Boundary | 7 files | 1B-B (contracts) | None new (Group 7 already approved at policy level) | Any accidental provider-specific code would violate `INTERFACE_ONLY`/`OFFLINE_FILE`-only scope | 2 unit tests | Port stays provider-neutral; offline stub makes zero network calls | Revert to end of 1B-D (or 1B-B if 1B-D not yet done) | YES, once 1B-B is committed |
| 1B-F | CI Foundation | 1 file | 1B-A (pyproject/uv.lock must exist for CI to run against) | #28 (trigger policy); #29–#30 (repository settings, not files) | An overly permissive workflow could accidentally gain network/credential access | N/A (workflow itself is the verification layer) | Workflow runs Ruff/mypy/pytest against Batches A–E's code, offline-safe, on the approved trigger | Revert to end of 1B-E (or earliest batch present) | YES, once 1B-A is committed |

**No batch is implemented by this document.** Each requires its own separate, explicit author instruction to create.

## 15. File-Creation Order

Matches Section 9's "Creation order" column exactly: **1–9** (Batch 1B-A) → **10–22** (Batch 1B-B) → **23–34** (Batch 1B-C) → **35–41** (Batch 1B-D) → **42–48** (Batch 1B-E) → **49** (Batch 1B-F). Within 1B-D and 1B-E, either batch may follow 1B-B directly (both depend only on 1B-B, not on each other or on 1B-C) — the numbering above reflects one valid linear order, not an additional dependency.

## 16. Dependency-Installation Order

**No dependency is installed by this document.** The proposed future order, once approved: (1) install Python at the approved patch version; (2) install `uv`; (3) `uv` resolves and locks runtime dependencies (Pydantic v2) into `uv.lock`; (4) `uv` resolves and locks development dependencies (pytest, mypy, Ruff) into the same lockfile; (5) `uv sync` (or equivalent) materializes the environment. No step above is executed by this task.

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

## 18. Rule and Schema Manifest Scope

**No manifest file or manifest directory is created by this document.** Per Part 11's rules (unchanged, reaffirmed here): `manifests/rules/` and `manifests/schemas/` are created only when their first real, reviewed manifest exists — never as empty directories, never via `.gitkeep`. No private-book text may ever enter a manifest. No manifest may approve a trading rule — it only records already-approved knowledge. Canonical JSON serialization (Blocking Decision #20) remains unresolved. **Exact first proposed filenames** (naming requires separate author approval, per Blocking Decision #15): a first rule-version manifest named illustratively `manifests/rules/measurement_standards_v1.json`, and a first schema-version manifest named illustratively `manifests/schemas/raw_candle_record_v1.json` — both illustrative only, neither created, neither approved.

## 19. Data-Contract Stub Scope

Covered file-by-file in Section 9 (Batch 1B-B rows) and Section 10. Summary: `types.py` (identity/fingerprint/version value types), `raw_candle.py` (Contract A), `normalized_candle.py` (Contract B), `validation_result.py` (Contract N), `provenance_record.py` (Contract M), `rule_version_manifest.py`/`schema_version_manifest.py` (Contracts Q/R, shape only — no manifest I/O). Whether Pydantic v2 is actually used for these classes in Batch 1B-B, versus a plain-dataclass placeholder pending Pydantic's dependency-version approval (Blocking Decision #7), is itself part of Blocking Decision #19 (module-boundary/implementation-technology confirmation) and is not silently decided here.

## 20. Validation-Stub Scope

Covered file-by-file in Section 9 (Batch 1B-C rows). Summary: `completeness.py`, `duplicates.py`, `gaps.py` implement the Group 6 enums and *interfaces* only (no provider-specific completion/gap-confirmation mechanism — Blocking Decisions #26–#27 remain open); `eligibility.py` implements the approved 8-step gating sequence. **Kept structurally separate, per the existing Phase 0G/Phase 1A validity-separation principle:** `data_quality_validity` (this batch's actual concern), `poi_validity`, `btmm_validity`, `entry_validity`, and `trade_outcome` (all out of scope for this batch and this scaffold entirely). No automatic conflicting-duplicate winner is designed — `duplicates.py`'s conflicting-duplicate path always routes to `QUARANTINED`, per the already-approved policy.

## 21. Provenance and Audit Stub Scope

Covered file-by-file in Section 9 (Batch 1B-D rows). Summary: `audit/events.py` (Contract O shape), `audit/writer.py` (append-only interface, no physical storage target chosen), `observability/logging_config.py` (structured JSON operational logging, explicitly separate from the audit writer). `provenance_record.py` itself is placed in Batch 1B-B (it is a data contract, Contract M) rather than Batch 1B-D, since every other contract in Batch 1B-B already references provenance lineage.

## 22. Ingestion-Interface Scope

Covered file-by-file in Section 9 (Batch 1B-E rows). Summary: `ingestion/port.py` (`MarketDataSourcePort`, abstract), `ingestion/requests.py`/`results.py` (provider-neutral shapes), `ingestion/offline_file_source.py` (the single permitted concrete implementation — reads one fixed local file, no network access, no credential). No FXCM adapter, no TradingView adapter, and no `HISTORICAL_BATCH`/`POLLING`/`STREAMING` retrieval mode is proposed — all remain explicitly not-yet-authorized per Decision Group 7.

## 23. Test Scope

Exact proposed test paths and names are listed in full in Section 8 (tree) and Section 9 (inventory) — 18 test files across Batches 1B-A through 1B-E: `test_import_smoke.py`, `test_config_precedence.py`, `test_identity_and_fingerprint.py`, `test_semver.py`, `test_raw_candle_contract.py`, `test_normalized_candle_contract.py`, `test_manifest_compatibility_classes.py`, `test_candle_completeness.py`, `test_exact_duplicate.py`, `test_conflicting_duplicate_quarantine.py`, `test_missing_gap.py`, `test_no_synthetic_fill.py`, `test_validation_eligibility.py`, `test_processing_version_preservation.py`, `test_audit_log_separation.py`, `test_secret_redaction.py`, `test_ingestion_port_contract.py`, `test_offline_file_stub.py`. **No fixture or test file is created by this document.**

**Phase 0G lifecycle-test restrictions remain fully binding and are unaffected by this scaffold plan:** full lifecycle tests remain limited to the 18 propagated bounded directional POIs (none of which appear in this scaffold at all — POI/lifecycle modules are entirely out of scope for Batches 1B-A–1B-F); Equal Highs/Equal Lows/both Trendlines remain limited to construction/classification/permitted-state/prohibition tests only, once their module exists (it does not, in this scope); generic bounded-lifecycle tests remain `NOT_APPLICABLE` to the 14 non-bounded reference structures. **No detector test is proposed or needed in this initial scaffold** — no detector module exists in Section 8's tree.

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

## 28. Phase 1B Scaffold Acceptance Criteria

A batch is acceptable for merge only if: (1) every file it adds appears in Section 9's inventory with a matching batch label; (2) every test listed for that batch exists and passes; (3) Ruff format/lint and mypy pass with zero errors; (4) no file outside the batch's declared scope was touched; (5) no entry/risk/execution/POI/BTMM/AI content was introduced; (6) every blocking decision listed against that batch in Section 6 has been separately author-resolved before the batch is implemented; (7) the batch was reviewed and committed on its own, not bundled with a later batch.

## 29. Decisions Requiring Author Approval

All 30 items in Section 6, plus: the package/distribution identity in Section 7; whether to adopt this document's proposed batch boundaries (Section 14) as-is or amend them; whether to adopt the proposed file inventory (Section 9) as-is or amend it before Batch 1B-A begins.

## 30. Approval Status

**`ENGINEERING-RECOMMENDED`. `NOT YET AUTHOR-APPROVED`. `NOT YET IMPLEMENTED`. `NOT PRODUCTION-APPROVED`.** This document proposes a file-level scope; it does not approve itself. No batch may be implemented until the author has separately reviewed and approved: package identity (Section 7), the blocking decisions relevant to that batch (Section 6), and the batch's exact file list (Section 9/14). No file listed anywhere in this document exists as a result of this task.
