# Deterministic Testing and Fixture Plan

**Document status:** ENGINEERING-RECOMMENDED planning document. **No fixture file is created by this document or this task.** This is a plan for a future testing hierarchy only.

---

## 1. Purpose

Define the future testing hierarchy and fixture taxonomy needed to validate every layer in `docs/architecture/PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md` deterministically — without depending on live or historical market data for unit-level correctness.

## 2. Future Testing Hierarchy

| Test category | Validates | Depends on |
|---|---|---|
| Contract validation tests | Every data contract in `DATA_CONTRACTS_AND_SCHEMA_PLAN.md` accepts valid records and rejects invalid ones. | Minimal synthetic fixtures. |
| Candle normalization tests | Raw → Normalized transformation (timezone canonicalization, OHLC ordering, confirmed-candle flagging). | Time-ordering, missing-data, duplicate-data fixtures. |
| Measurement tests | Every formula in `knowledge/MEASUREMENT_STANDARDS.md` (Candle Measurement Standard V1, Small Candle Standard V1, Pressure Wick Standard V1, etc.) computes exactly as specified. | Positive, negative, boundary fixtures. |
| POI geometry tests | Each of the 36 POI types' formation/boundary rules produce the exact documented zone. | Positive, negative, near-miss, boundary fixtures. |
| Availability-timing tests | Every POI's `*_available_time` is set exactly per its approved rule, never earlier (non-repainting). | Boundary and time-ordering fixtures. |
| Interaction-classification tests | EDGE_TOUCH/PARTIAL_ENTRY/DEEP_ENTRY/FAR_BOUNDARY_TOUCH/CONTROLLED_OVERSHOOT/NEAR_MISS/NO_CONTACT classification matches the POI Zone Interaction Standard exactly. | Boundary, near-miss fixtures. |
| Lifecycle-transition tests | The ten-state Boundary Breach/Reclaim/Invalidation state machine only allows the documented transitions and rejects forbidden ones (e.g., `GENUINE_INVALIDATION_CONFIRMED → FALSE_INVALIDATION_CONFIRMED`). | Lifecycle-transition fixtures. |
| Manual-source-label tests | Manual annotation records are correctly tagged `MANUAL_EXPERT_LABEL` and are never conflated with an automatic source. | Ambiguous fixtures (to confirm manual review is actually required, not silently bypassed). |
| Provenance tests | Every record produced by every layer carries a complete, correct lineage chain back to its raw source. | Any fixture set, checked end-to-end. |
| Historical replay determinism tests | Re-running the pipeline against the same pinned raw data and versions produces byte-identical output. | Any fixture set, run twice. |
| Regression tests | A rule-version or schema-version change does not silently alter the interpretation of records produced under a prior version. | Versioned fixture snapshots. |
| Negative and near-miss fixture tests | Rejection criteria (per `P0G-B013A`: `EXPLICIT` for 24 candidate/pattern POIs, `NOT_APPLICABLE` for the 12 period-reference POIs) correctly reject invalid candidates and correctly treat period-reference levels as always-present. | Negative, near-miss fixtures. |
| Cross-timeframe isolation tests | A POI or measurement computed on one timeframe never leaks into or is silently substituted for another timeframe's calculation. | Fixtures spanning multiple timeframes (H3/H4/D1/W1/H1/M15/M5/M1). |
| Provider consistency tests | Records are correctly rejected or flagged when provider/symbol metadata does not match the canonical `FXCM:XAUUSD`/`FXCM:EURUSD`/`FXCM:GBPUSD` list. | Provider-metadata fixtures. |

## 3. Fixture Categories

| Fixture category | Purpose |
|---|---|
| Minimal synthetic fixture | The smallest possible valid input needed to exercise a single contract or formula in isolation. |
| Positive fixture | A candle sequence that should produce a confirmed POI/pattern/state, matching a documented formation rule exactly. |
| Negative fixture | A candle sequence that should fail an explicit rejection criterion (per `P0G-B013A`'s `EXPLICIT` classification for 24 POI types). |
| Near-miss fixture | A candle sequence just outside a tolerance boundary (e.g., a `NEAR_MISS` per Contact Tolerance) — must not be silently treated as a full interaction. |
| Ambiguous fixture | A candle sequence deliberately close to a decision boundary where the "right" answer is not obvious, used to confirm the system defers to the documented rule rather than guessing. |
| Boundary fixture | A candle sequence exactly at a threshold edge (e.g., Size Ratio exactly 2.0, Body Efficiency exactly 0.10) to test inclusive/exclusive boundary handling. |
| Time-ordering fixture | A candle sequence with out-of-order or overlapping timestamps, to test the out-of-order candle policy. |
| Missing-data fixture | A candle sequence with a gap, to test the missing-data policy. |
| Duplicate-data fixture | Two raw records claiming the same provider/symbol/timeframe/timestamp, to test the duplicate-data policy. |
| Provider-metadata fixture | A record with an unrecognized or mismatched provider/symbol, to test provider-symbol validation. |
| Lifecycle-transition fixture | A sequence exercising every allowed transition and at least one forbidden transition attempt, to confirm the state machine rejects the latter. |

## 4. Explicit Recordings

- **Fixtures are not AI training data by default.** A fixture built for deterministic unit testing may only be repurposed as AI training data through a separate, explicit, future author decision — this plan does not authorize that repurposing.
- **Book screenshots or private-book content must not be copied into public fixtures.** Fixtures are entirely synthetic/hand-authored; none may embed excerpts, screenshots, or paraphrased content from `references/private/BTMM_AND_POI_TRADING_BIBLE.docx`.
- **`P0G-B021` remains responsible for the later reviewed negative-example dataset.** This testing plan's "negative fixture" category is a software-testing construct (confirming rejection logic works) and is explicitly distinct from `P0G-B021`'s deferred scope (a reviewed, real-market negative-example dataset for future annotation/validation work) — the two must never be conflated.
- **Synthetic fixtures must not be presented as market-performance evidence.** A fixture passing a test demonstrates the code implements the documented rule correctly; it says nothing about real-market profitability, which remains explicitly out of scope (Phase 0G, `P0G-B016`, and all empirical-calibration items `P0G-B008`/`P0G-B012`/`P0G-B015`/`P0G-B020`).
- **Deterministic tests must not depend on future candles unless the approved rule explicitly requires confirmation bars.** Where a Phase 0G standard explicitly requires a lookahead/confirmation window (e.g., the 3-bar Reclaim window, the 5-bar Meaningful Reversal window), tests may use exactly that many future candles and no more; no test may otherwise assume knowledge of candles beyond what the rule itself requires.
- **Non-repainting rules must be testable.** Every availability-time rule must have a corresponding test that confirms a record is not visible/usable before its documented availability time, and that a later event never retroactively changes an earlier availability time.

## 4a. Testability Limits by POI Category

**`P0G-B004` (Equal High/Low specialized lifecycle) and `P0G-B005` (Trendline specialized lifecycle) remain binding, unresolved, formally deferred blockers.** This testing plan's categories in SS2 above must be understood, and eventually implemented, differently depending on POI category:

- **The 18 propagated bounded directional POIs** (4 Group 1 + 8 Group 2 + 6 Group 3): full, approved "Lifecycle-transition tests" and "Availability-timing tests" may be planned and eventually implemented against the already Author-Approved POI Boundary Breach, Reclaim and Invalidation Standard V1 and the Freshness/Age Standard — these are the only POIs for which the ten-state lifecycle machine and the `qualifying_interaction_time > poi_availability_time` rule are fully specified today.
- **Equal Highs, Equal Lows, and both Trendlines:** only **construction, classification, permitted-state, and prohibition tests** may be planned — e.g., confirming Equality Tolerance/Cluster Spread classification, confirming DRAFT/CONFIRMED/STRONG_TRENDLINE progression, and confirming that the system correctly *refuses* to produce a lifecycle outcome for these structures. **Final specialized lifecycle-transition tests remain deferred** for these four structures. **No test fixture or test case may present an automated SWEPT, BROKEN, final break, reclaim, false-break, invalidation, reactivation, or expiration outcome as approved behavior for Equal Highs, Equal Lows, or either Trendline** — any such fixture would misrepresent a formally deferred, unresolved rule as though it were decided.
- **The 14 non-bounded reference structures** (Swing High, Swing Low, and the 12 Previous/Current Period High/Low variants): the generic bounded-zone lifecycle tests are `NOT_APPLICABLE` — these structures are single price levels, not zones, and were never in scope for that lifecycle standard.

This section clarifies test scope only; **no fixture is created by this clarification**, and no Phase 0G blocker is resolved by it.

## 5. No Fixture Files Created

**This task creates zero fixture files.** This document is a plan only; actual fixture construction is a future, separately-authorized implementation step (Phase 1C or later, per the architecture document's illustrative implementation sequence).

## 6. Approval Status

**ENGINEERING-RECOMMENDED**, pending author review. No test framework is installed (see the Technology-Stack Decision Register in `PHASE_1A_SOFTWARE_FOUNDATION_ARCHITECTURE.md`, item 5, pytest recommended but not yet author-approved). No fixture or test file exists as a result of this document.

## 7. Post-Phase 1A Approved Future Test Environment (Decision Groups 1–8)

**No fixture or test file is created by this section.** Full decision detail is recorded canonically in `docs/architecture/PHASE_1B_AUTHOR_DECISION_REGISTER.md`. The following are now `AUTHOR-APPROVED` (`NOT YET IMPLEMENTED`, `NOT PRODUCTION-APPROVED`) as the future test environment, once a scaffold exists:

- **Runtime and tooling (Group 1):** Python 3.12 (one pinned patch version); pytest as the test runner; mypy for static-type checking; Ruff formatter and Ruff linter for style/lint checks.
- **CI (Group 5):** GitHub Actions running Ruff format check, Ruff lint, mypy, and pytest on every push. CI is offline-safe by default: no live broker/FXCM/TradingView credentials, no private-book access, no deployment, and no order execution may ever be exercised by CI.

**Additional planned test categories** (extending SS2's table above, still zero fixtures/tests created):

| Planned future test category | Validates |
|---|---|
| Candle-completeness tests | `candle_completeness_status` transitions correctly; only `CONFIRMED_COMPLETE` candles become analytically eligible (Decision Group 6). |
| Exact-duplicate tests | `duplicate_classification = EXACT_DUPLICATE` preserves every raw envelope, never creates a second normalized candle, and never overwrites the first record. |
| Conflicting-duplicate quarantine tests | `duplicate_classification = CONFLICTING_DUPLICATE` results in `QUARANTINED` status, preserves every raw record, and never silently picks a winner or produces a measurement. |
| Gap-status tests | `gap_status` transitions (`POTENTIAL_GAP` → `CONFIRMED_MISSING` → `RESOLVED`, and `EXPECTED_NON_TRADING_INTERVAL`) match the approved policy; contiguous windows become ineligible exactly per rule. |
| No-synthetic-fill tests | No forward fill, back fill, interpolation, previous-close copying, invented zero-volume candle, or silent time compression ever occurs. |
| Validation-eligibility tests | The 8-step processing sequence (`PROVENANCE_VALIDATION_AND_AUDIT_PLAN.md` SS9a) gates Normalization and Measurement exactly as specified; presence alone never grants eligibility. |
| Identity-versus-fingerprint tests | UUIDv7 record identity and SHA-256 `content_fingerprint` remain distinct fields; neither substitutes for the other; identity is never silently reused. |
| Manifest compatibility-class tests | `BACKWARD_COMPATIBLE` / `BREAKING` / `DOCUMENTATION_ONLY` classification matches the approved examples (e.g., a required-field removal is always `BREAKING`). |
| Schema/processing-version preservation tests | Historical `schema_version` and `processing_version` references are never silently rewritten; reprocessing always produces a new record or replay output. |
| Provider-neutral ingestion-interface tests | `MarketDataSourcePort` never leaks provider-specific behavior into contract or result shapes; the interface remains provider-neutral. |
| `OFFLINE_FILE` stub-behavior tests | The early, interface-only retrieval mode behaves deterministically against a fixed offline file, with no network access attempted. |
| Audit/log-separation tests | Operational (structured JSON) logs and authoritative JSONL audit events remain in separate stores and are never conflated. |
| Secret-redaction tests | No audit event, validation report, or log line ever contains a password, token, API key, `.env` content, or unredacted credential. |

**All Phase 0G lifecycle-test restrictions from SS4a above remain fully binding and unaffected by this decision round:** `P0G-B004` and `P0G-B005` remain binding, unresolved blockers; full lifecycle tests remain limited to the 18 propagated bounded directional POIs; Equal Highs, Equal Lows, and both Trendlines remain limited to construction/classification/permitted-state/prohibition tests only; generic bounded-lifecycle tests remain `NOT_APPLICABLE` to the 14 non-bounded reference structures. **No fixture file is created by this section.**
