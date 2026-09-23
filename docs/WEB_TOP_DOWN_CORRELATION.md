# Web Top-Down Correlation Layer (Correlation-V1, T0)

A NEW, additional supervisory layer (`btmm_ai_scanner.correlation`) built on
top of the existing, unmodified scanner + BTRC engines, evolving them into a
stable, versioned contract the BellForex website can call in a later,
separate integration phase. **This phase does not touch the website, does
not deploy anything, and adds no network, LLM, image-analysis, or broker
dependency.**

Core principle: **higher timeframes determine the market story; lower
timeframes may refine or confirm it, but must never turn an obvious
countertrend pattern into the primary trade candidate.** The engine is
allowed — and expected — to say `NO_VALID_SETUP` rather than force a trade.
It looks for the *highest-confluence valid setup*, never a guaranteed one.

## What this layer reuses vs. adds

```
existing scanner (scan_market)
    |
existing BTRC (assess_trend, assess_confluence -> BtrcDecision)
    |
NEW: btmm_ai_scanner.correlation
    - mode_trend.py    mode-aware authority direction (per TradingMode)
    - policy.py        deterministic countertrend/setup-verdict policy
    - candidate.py      eligible-candidate collection + ranking
    - engine.py         orchestration -> TopDownCorrelationDecision
    - contract.py       versioned web contract + annotation contract
    - profiles.py       SCALP / DAY_TRADE / SWING timeframe policy (data)
    - enums.py          TradingMode, TopDownCorrelationState, SetupVerdict
```

This layer never re-detects a swing, POI, BOS, CHOCH, FVG, or BTRC decision —
it only classifies, filters, ranks, and explains what the scanner and BTRC
already produced. It never invalidates a POI/BTMM setup and never overrides
`AnalyticalPermission`, `TrendAlignment`, `poi_valid`, or `btmm_valid` — the
same non-authoritative posture BTRC itself already has over POI/BTMM (see
`docs/architecture/BTRC_V1_T0_ARCHITECTURE_AND_CONTRACT_FREEZE.md`).

**`TrendAssessment.global_direction`, `AnalyticalPermission`, and
`TrendAlignment` keep their EXACT existing meaning.** BTRC's own D1 primary /
W1 macro / H4 operational authority resolver
(`btrc/trend_engine.py::_resolve_global`) is untouched and still drives
`assess_confluence()`'s own scoring. This layer's `mode_direction` is a
SEPARATE, additional, mode-aware authority resolution — never a replacement.

## Timeframe identities

`Timeframe` (`config/enums.py`) gained five new members: `H2`, `H6`, `H9`,
`H12`, `MN1`. Existing members (`M1`, `M5`, `M15`, `H1`, `H3`, `H4`, `D1`,
`W1`) and their string values are **unchanged**.

Ordering (`_TIMEFRAME_RANK`, duplicated by the project's own existing
convention in `scanner/replay.py`, `scanner/analyzer.py`, and
`historical_backtest/loader.py` — this layer follows that same convention
rather than inventing a fourth copy) was renumbered 1..13 in full temporal
order (`M1 < M5 < M15 < H1 < H2 < H3 < H4 < H6 < H9 < H12 < D1 < W1 < MN1`).
The renumbering only changes the internal integer VALUES used purely as a
sort key — never serialized on any output record, confirmed by grep before
changing it — so the relative order of the original eight members is
unchanged and no existing behavior depending on that relative order is
affected.

**No internal resampler was added.** The scanner still requires
caller-supplied, already-normalized candles for every timeframe, new ones
included. `H2`/`H6`/`H9`/`H12`/`MN1` candle boundaries are not invented
inside the analytical core — a future web/data-provider integration layer is
responsible for supplying correctly-bounded candles for these timeframes,
with its own session/provider semantics explicitly defined and tested there,
never guessed here.

`btrc/trend_engine.py` gained one new public function,
`assess_supplied_timeframe_trend(analysis, timeframe, configuration=None)`,
which exposes the exact same per-timeframe assessment logic
`assess_trend()` already uses internally for its own fixed six-timeframe
authority set — additively, for ANY supplied timeframe. `assess_trend()`'s
own body, its six-timeframe `_AUTHORITY_TIMEFRAMES` set, and its
`global_direction`/`macro_context`/`operational_context` semantics are
completely unchanged (covered by a regression test supplying new timeframes
alongside the legacy authority set and asserting the legacy result is
identical to before).

## Trading modes

`TradingMode`: `SCALP`, `DAY_TRADE`, `SWING`. Product policy — which
timeframes belong to which mode, their order, which are authority/context
vs. execution, and the recommended minimal set — lives as DATA in
`profiles.py` (`TradingModeProfile`), never scattered across if-statements.

| Mode | Top-down order | Authority/context | Execution | Recommended | Minimum |
| --- | --- | --- | --- | --- | --- |
| SCALP | H4→H3→H2→H1→M15→M5 | H4, H3, H2, H1 | M15, M5 | H4 + H1 + M15 | 3 |
| DAY_TRADE | D1→H12→H9→H4→H1 | D1, H12, H9, H4 | H1 | D1 + H4 + H1 | 3 |
| SWING | MN1→W1→D1→H12→H9→H6→H4 | MN1, W1, D1, H12, H9 | H6, H4 | W1 + D1 + H4 | 3 |

A scan is never required to supply the largest possible timeframe (e.g. a
swing scan may supply `W1 + D1 + H4` without `MN1`); the engine reports the
**highest valid SUPPLIED authority timeframe** as `authority_anchor_timeframe`
and never fabricates analysis for a timeframe that wasn't given.

Minimum supplied count is 3 for every mode, but `evaluate_top_down_setup`
additionally requires **at least one authority/context timeframe AND at
least one execution timeframe** among what was actually supplied — three
context-only timeframes satisfy the bare count but can never produce a
meaningful top-down result, so that alone is not sufficient.

## Presentation timeframe — a UI concern only

`TradingModeProfile.presentation_timeframes` (every timeframe in the mode's
`top_down_order`) is a purely cosmetic choice for where the FINAL result is
rendered — it never changes the POI's real source timeframe, the execution
timeframe, or the authority anchor. `build_web_contract()`'s
`requested_presentation_timeframe` is echoed back in the contract's
`presentation.requested_timeframe` field only when it is one of the mode's
own `presentation_timeframes`; otherwise it is `None` (never silently
substituted with something else). A scalp setup confirmed on M15 can still
be requested for presentation on H1 or H4 without changing anything
analytical about the setup itself.

## Mode-aware authority resolution (`mode_trend.py`)

`assess_mode_authority(analysis, mode)` computes, for every timeframe in the
mode's `top_down_order` that was actually supplied:

- its own `Direction`/`TrendState` (via `assess_supplied_timeframe_trend`);
- `authority_anchor_timeframe` — the highest-ranked authority timeframe
  actually supplied and resolved;
- `mode_direction` — generalized from BTRC's own anchor-plus-agreement
  pattern: the anchor's direction, strengthened to `STRONG_*` only if EVERY
  other supplied authority timeframe agrees; falling back to unanimous
  agreement among the other authority timeframes when the anchor itself is
  neutral/absent; `NEUTRAL` otherwise;
- `correlation_state` (`TopDownCorrelationState`) — how the SUPPLIED
  authority timeframes agree with EACH OTHER (a distinct concept from
  `mode_direction` vs. a candidate's own direction — see "Countertrend
  protection" below):
  - `ALIGNED` — every resolved authority timeframe agrees.
  - `PARTIALLY_ALIGNED` — a clear majority agrees, one dissents or is neutral.
  - `MIXED` — no clear majority; the sides are close to evenly split.
  - `COUNTER_TREND` — a two-sided conflict where the opposing side matches
    or outnumbers the anchor's own side (material conflict against the
    anchor itself).
  - `INSUFFICIENT_CONTEXT` — no authority timeframe resolved to a real
    direction at all.

## Setup verdict and hard countertrend protection

`SetupVerdict`: `VALID_SETUP`, `WATCH_FOR_ALIGNMENT`, `NO_VALID_SETUP`,
`INSUFFICIENT_DATA` — a strictly-additive wrapper ABOVE
`AnalyticalPermission` (never a rename or replacement of it).

The deterministic policy (`policy.py::evaluate_candidate_policy`), no LLM,
no probability:

- **A. Candidate direction matches `mode_direction`:** proceeds to BTRC's
  own hard truths (a `NO_TRADE_CONTEXT`/`WATCH_ONLY` `AnalyticalPermission`
  is never overridden), then to the correlation-state gate (a `MIXED`/
  `INSUFFICIENT_CONTEXT` internal authority state softens an otherwise-valid
  candidate to `WATCH_FOR_ALIGNMENT`), then to the confluence-score
  threshold (`minimum_confluence_for_valid_setup` / `minimum_confluence_for_watch`,
  `CorrelationConfiguration`).
- **B. Candidate direction opposes `mode_direction` (the hard gate):** if the
  opposition is `STRONG_*`, or the authority timeframes are themselves in
  `COUNTER_TREND` correlation, or the candidate's own confluence is below the
  watch threshold — the candidate is **unconditionally** `NO_VALID_SETUP`. A
  milder (non-strong) opposition may still become `WATCH_FOR_ALIGNMENT`
  rather than `NO_VALID_SETUP`, per the master brief's own "according to
  explicit policy" allowance — but it can **never** become `VALID_SETUP`.
- **C. `mode_direction` is `NEUTRAL`/unresolved:** never forces a direction;
  at best `WATCH_FOR_ALIGNMENT`.
- **D. Insufficient supplied timeframes/candles:** `INSUFFICIENT_DATA`,
  never a guess.

Example (the master brief's own core scenario): `H4=BEARISH, H3=BEARISH,
H2=BEARISH, H1=BEARISH` (all authority timeframes agree → `mode_direction =
STRONG_BEARISH`), with an isolated bullish `M5` POI candidate. The candidate
is unconditionally `NO_VALID_SETUP` — the strong opposing authority makes
this deterministic, not merely likely.

Distinguishing execution-vs-authority conflict from higher-timeframe
INTERNAL conflict (the master brief's own worked example): `H4=BULLISH,
H3=BULLISH, H2=NEUTRAL, H1=BEARISH pullback, M15=BULLISH confirmation` — the
anchor (H4) is bullish, `mode_direction` resolves to plain `BULLISH` (not
strengthened, since H1 disagrees), `correlation_state` is
`PARTIALLY_ALIGNED` (a minority dissent, not a majority conflict) — this is
NOT the softening `MIXED`/`INSUFFICIENT_CONTEXT` gate, so a bullish M15
candidate can still reach `VALID_SETUP` on its own confluence merits,
exactly as the brief expects ("could still be a valid aligned scalp").

## Conversation with a natural follow-up (context retention within one scan)

This phase evaluates ONE scan at a time (it is not a conversational/chat
system) — "conversation context" here means: a follow-up-shaped scan (e.g.
the same POI/timeframe set re-evaluated moments later) is handled by the
SAME deterministic function producing the SAME result for the SAME inputs
(see "Determinism" below), not by any hidden state.

## Candidate selection and ranking (`candidate.py`)

Reuses `assess_confluence` (unchanged) for every eligible POI, sharing ONE
`ConfluenceBarContext` per scan (matching the existing project's own
per-bar-not-per-POI optimization pattern) so scoring stays cheap.

**Eligibility** (never selects an invalidated/terminal POI as the active
candidate): the POI's `source_timeframe` must be one of the mode's
`execution_timeframes`; its `CurrentPoiState.poi_lifecycle_status` must not
be `FALSE_INVALIDATION_CONFIRMED`/`GENUINE_INVALIDATION_CONFIRMED`; it must
be `fresh_active` and `freshness_status == FRESH` (an already-mitigated or
already-reacted-to zone is not a future opportunity).

**Ranking** (deterministic, never an invented AI probability), highest
first:
1. `SetupVerdict` eligibility (a candidate whose own policy result is
   `NO_VALID_SETUP` is excluded from selection entirely).
2. The candidate's own BTRC `TrendAlignment` (`ALIGNED` > `PARTIAL` >
   `NEUTRAL` > `COUNTER_TREND`).
3. `AnalyticalPermission` suitability (`BUY_BIAS`/`SELL_BIAS` > `ALLOW_BOTH_CONTEXT`
   > `COUNTER_TREND` > `WATCH_ONLY` > `NO_TRADE_CONTEXT`).
4. `SignalLifecycleState` readiness (its index in BTRC's own
   `ANALYTICAL_LIFECYCLE_STATES` progression).
5. `final_confluence_score` (higher first) — **a confluence score, never a
   probability**; it is never converted into a percentage-sounding claim
   anywhere in this layer.
6. Deterministic tie-break: higher execution timeframe rank, then the POI's
   own `record_id` — two candidates never compare ambiguously.

Internally called `selected_candidate` / the highest-confluence eligible
candidate — deliberately never "best trade" anywhere in code or contract.

## `NO_VALID_SETUP` and `INSUFFICIENT_DATA` are successful outcomes

`selected_candidate = None` with `verdict = NO_VALID_SETUP` is a normal,
successful analysis result — e.g. no fresh execution-timeframe POI exists,
every eligible candidate's own policy resolved to `NO_VALID_SETUP`, or
authority context is against every available candidate. This is never
treated as an engine error and never raises an exception.
`INSUFFICIENT_DATA` is returned (not raised) when the mode profile's own
minimum-supplied-timeframe requirements are not met.

## Technical invalidation vs. a trading stop loss

`CurrentPoiState.poi_lifecycle_status` / `PoiTerminalReason`
(`MITIGATED`/`INVALIDATED`/`PROMOTED_TO_ORDER_BLOCK`) already exist on the
scanner's own POI lifecycle model and are surfaced as-is
(`WebSetupCandidateContract.lifecycle_status`) — this layer never
transforms a technical invalidation into a stop-loss price. Those remain
two separate concepts; see "Trade plan" below.

## Trade plan: not validated in this phase

`WebTradePlanContract.status = "NOT_VALIDATED"` always. The
`source_branch_only_botdryrun` package's `PracticePolicy`/`SignalDecision`
(entry/stop/target on `origin/bot-dryrun-v1`, not present on this branch)
is explicitly a **paper-only, unvalidated exercise of the dry-run plumbing**
— its own module docstring states "no profitability claim of any kind is
made for it," and it imports from `tests.parity_support.*` (test-only
helpers). None of its policy, prices, or claims are copied, promoted, or
exposed here. A future, separate, explicitly-authorized phase would validate
an entry/SL/TP/R:R policy before ever exposing one.

## Web contract (`contract.py`)

`TopDownWebContract` — a NEW, additional, versioned contract for a future
Bell Academy Hub integration. **Does not replace `ScannerAnalysis`.** Every
field is either real scanner/BTRC output or an explicit `null`/empty value —
never a fabricated placeholder. `evaluated_at_utc`/`supplied_timeframes`/
`recommended_timeframes_missing`/`authority`/`correlation`/`setup`/
`technical_context`/`trade_plan`/`presentation`/`provenance` mirror the
review package's own suggested shape, adapted to this codebase's real field
names (confirmed against actual source, never invented from memory).

## Annotation-data contract (`contract.py`)

`AnnotationContract` — price/time coordinates only (Decimal, matching the
rest of the engine), never pixels. At T0 it surfaces the selected
candidate's own POI zone as one box
(`{kind, price_top, price_bottom, timeframe, label}`); broadening this to
every visible candidate/liquidity level is a natural, additive future
extension, not built in this phase.

## Screenshots are not scanner input

The Python engine remains strictly OHLC-based — this phase adds no
image/screenshot analysis, no chart renderer, and no OCR/computer-vision
dependency. The eventual Bell Academy Hub flow is hybrid: user screenshots
are optional VISUAL context for the student, real OHLC candles are the
Python scanner's only input, and the scanner's structured result is what a
future BellForex AI explanation layer narrates — never the other way
around.

## Confluence score is not probability

`final_confluence_score` (BTRC's own `ComponentScores`-derived 0–100 value)
is surfaced as-is on the selected candidate. It is never reworded as a
percentage-sounding claim ("71% probability") anywhere in this layer's code,
tests, or contract — it is a ranking/confluence signal, not a statistical
probability of any outcome.

## Determinism

`evaluate_top_down_setup` is a pure function of `(analysis, mode, profile,
configuration)` — no network, no randomness, no wall-clock dependency beyond
`analysis.availability_time_utc` (itself already part of the deterministic
`ScannerAnalysis`). The same inputs always produce the same verdict and the
same selected candidate (tested directly: five repeated calls on identical
input produce identical results).

## Backward compatibility

- `scan_market(...)` is completely untouched — same signature, same return
  shape, same behavior for every existing supported input.
- `Timeframe`'s existing eight members and their string values are
  unchanged; `TrendAssessment.global_direction`, `AnalyticalPermission`, and
  `TrendAlignment` keep their exact existing meaning.
- `assess_trend()`'s own body and six-timeframe authority resolution are
  unchanged (regression-tested: supplying new timeframes alongside the
  legacy authority set produces an identical legacy result to before this
  change).
- No existing serialized contract's schema changed — `TopDownWebContract`
  is a brand-new, additional contract with its own version fields, not a
  modification of `ScannerAnalysis`/`BtrcDecision`/any existing model.

## Versioning

Every new contract (`TradingModeProfile`, `CorrelationConfiguration`,
`ModeAuthorityAssessment`, `TopDownCorrelationDecision`, `TopDownWebContract`
via its source `TopDownCorrelationDecision`) carries its own
`rule_version`/`contract_version`/`schema_version` `SemVer` fields, defaulted
to `0.1.0` — following the exact same per-record provenance-stamping
convention already used by every existing `*Configuration`/output model in
this codebase, rather than introducing one new global version constant.

## Security

No credentials, no network dependency, no subprocess/shell invocation, no
arbitrary file-path access, no `pickle`, no `eval`/`exec` anywhere in this
package. No new third-party dependency was added.

## HTTP service layer (`btmm_ai_scanner.service`, Phase 2/web-integration)

A thin, additive FastAPI service exposing this engine to Bell Academy Hub's
Laravel backend over an internal-only HTTP boundary. Optional dependency
group (`pip install '.[service]'` / `uv sync --extra service`) — the
analytical core above stays dependency-free beyond pydantic whether or not
this is installed.

```
service/
    identity.py   deterministic content-addressed UUIDv7/fingerprint helpers
    candles.py    RawBar -> NormalizedCandle, built directly (bypasses the
                  FXCM-only market_data/source_mapping.py ingestion chain —
                  see docs/BTMM_SCANNER_WEB_INTEGRATION.md in the Bell
                  Academy Hub repo for why)
    schemas.py    the ONLY types an external caller needs: AnalyzeRequest/
                  AnalyzeResponse/HealthResponse/ErrorResponse
    app.py        POST /v1/analyze, GET /health
```

`POST /v1/analyze` takes a symbol, a `TradingMode`, and a bundle of
already-CLOSED bars per timeframe; it builds `NormalizedCandle`s, calls the
unmodified `scan_market()` then `evaluate_top_down_setup()`, and returns the
existing `TopDownWebContract`/`AnnotationContract`. It never persists
anything and never depends on wall-clock state beyond stamping each
candle's own `processing_time_utc`. `GET /health` returns only
`status`/`scanner_git_sha`/`contract_version`/`schema_version`/`rule_version`
— never environment, filesystem paths, or secrets. Bind to `127.0.0.1` only;
this service has no authentication of its own and must never be reachable
from outside its own host.

A well-formed request that the engine itself resolves to
`SetupVerdict.INSUFFICIENT_DATA` is a normal `200` response (that is a real
analytical verdict, not a service failure); a malformed/unsupported request
(bad symbol, unknown timeframe key, empty bundle) is a `422` with a
structured `ErrorResponse`; an unexpected internal error is a `500` with a
generic message — the caller never sees a Python traceback.

Covered by `tests/unit/test_service_identity.py`,
`test_service_candles.py`, `test_service_schemas.py`, `test_service_app.py`
(identity determinism, `NormalizedCandle` construction, request-schema
validation, and full FastAPI `TestClient` round-trips including a
determinism check across two identical requests).

### Bugs found and fixed while building this layer

Driving real multi-timeframe bars (including the H2/H6/H9/H12 timeframes
added earlier in this phase) through the actual `scan_market()`/`analyze_pois`
pipeline for the first time — rather than the hand-built `ScannerAnalysis`
fixtures the correlation-engine unit tests use — surfaced four private,
differently-named timeframe-rank/duration tables that the original Timeframe
extension's audit missed because they don't share the `_TIMEFRAME_RANK`
substring grepped for at the time:

- `poi/analyzer.py::_TIMEFRAME_STRENGTH_RANK` (would `KeyError` on any POI
  bundle using H2/H6/H9/H12/MN1 — this is what the first end-to-end
  `/v1/analyze` call actually hit)
- `poi/overlap.py::_TIMEFRAME_STRENGTH_RANK` (same bug, POI cross-timeframe
  overlap ranking)
- `poi/rc5_host_identity.py::MINUTES_BY_TIMEFRAME` (RC5 host-identity
  minute-length lookup)
- `historical_backtest/csv_parser.py::_INTRADAY_DURATION`,
  `historical_backtest/data_quality.py::_FIXED_TIMEFRAME_DURATION`, and
  `market_data/gap_observation.py::_EXPECTED_INTERVAL_BY_TIMEFRAME` (the
  latter two guarded with `.get()`/`in` so they degrade rather than crash,
  but all three silently mishandled a new timeframe)

All were extended to the same full 13-member ordering/duration convention
already used by the three `_TIMEFRAME_RANK` tables from the initial
extension (`scanner/analyzer.py`, `scanner/replay.py`,
`historical_backtest/loader.py`). `btmm/analyzer.py::_TIMEFRAME_STRENGTH_RANK`
was deliberately left at its original 3 entries — it is intentionally scoped
to only M1/M5/M15 BTMM-formation bundles, not a missed case. No behavior
changed for any of the original eight timeframes.

The full suite was re-run after these fixes: **17 failed, 5398 passed, 215
skipped**. All 17 failures are in the exact same four files already
documented as pre-existing, order-dependent/flaky
(`test_a6f6h_execution_mode_split.py`, `test_historical_cli.py`,
`test_historical_execution.py`, `test_historical_reporting.py`) — none of
which this phase touches — and match the count from the original baseline
run before any Phase 1/2 change. Zero new failures were introduced.
