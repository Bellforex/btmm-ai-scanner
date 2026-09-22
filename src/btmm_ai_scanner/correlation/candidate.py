"""Correlation-V1 (T0) — deterministic candidate selection and ranking.

Reuses the scanner's EXISTING POI and BTRC outputs; it never re-detects a
swing, POI, BOS, CHOCH or FVG, and never re-scores anything BTRC's
``assess_confluence`` already scored — it only filters (by mode execution
timeframe and freshness/lifecycle) and orders what already exists.

Internally called ``selected_candidate`` / ``highest_confluence_candidate``,
deliberately never "best trade" — this is a confluence ranking, not a
probability or a promise (see ``docs/WEB_TOP_DOWN_CORRELATION.md``
"Confluence score is not probability").
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import (
    ANALYTICAL_LIFECYCLE_STATES,
    AnalyticalPermission,
    Direction,
    SignalLifecycleState,
    TrendAlignment,
)
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision
from btmm_ai_scanner.btrc.t5_engine import ConfluenceBarContext, assess_confluence
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.correlation.configuration import CorrelationConfiguration
from btmm_ai_scanner.correlation.enums import SetupVerdict, TopDownCorrelationState
from btmm_ai_scanner.correlation.policy import (
    CandidatePolicyResult,
    evaluate_candidate_policy,
)
from btmm_ai_scanner.correlation.profiles import TradingModeProfile
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.enums import PoiFreshnessStatus, PoiLifecycleStatus
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis

# Terminal lifecycle statuses: a POI in either of these is not a future fresh
# opportunity and must never become the active candidate (Phase 18/21).
_TERMINAL_LIFECYCLE_STATUSES = frozenset(
    {
        PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED,
        PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED,
    }
)

# Deterministic tie-break ranking for analytical_permission (higher first).
_PERMISSION_RANK: dict[AnalyticalPermission, int] = {
    AnalyticalPermission.BUY_BIAS: 5,
    AnalyticalPermission.SELL_BIAS: 5,
    AnalyticalPermission.ALLOW_BOTH_CONTEXT: 4,
    AnalyticalPermission.COUNTER_TREND: 2,
    AnalyticalPermission.WATCH_ONLY: 1,
    AnalyticalPermission.NO_TRADE_CONTEXT: 0,
}
_ALIGNMENT_RANK: dict[TrendAlignment, int] = {
    TrendAlignment.ALIGNED: 3,
    TrendAlignment.PARTIAL: 2,
    TrendAlignment.NEUTRAL: 1,
    TrendAlignment.COUNTER_TREND: 0,
}
_VERDICT_RANK: dict[SetupVerdict, int] = {
    SetupVerdict.VALID_SETUP: 2,
    SetupVerdict.WATCH_FOR_ALIGNMENT: 1,
    SetupVerdict.NO_VALID_SETUP: 0,
    SetupVerdict.INSUFFICIENT_DATA: 0,
}
_LIFECYCLE_RANK: dict[SignalLifecycleState, int] = {
    state: index for index, state in enumerate(ANALYTICAL_LIFECYCLE_STATES)
}


class RankedCandidate(ContractModel):
    """One execution-timeframe POI candidate, already scored by BTRC and
    evaluated by this layer's own countertrend/alignment policy. Ordering
    among a batch of these is what ``select_candidate`` uses to deterministically
    pick the single highest-confluence eligible candidate."""

    poi: PoiObservation
    current_state: CurrentPoiState | None
    btrc_decision: BtrcDecision
    policy_result: CandidatePolicyResult


def _is_eligible_for_consideration(
    poi: PoiObservation,
    current_state: CurrentPoiState | None,
    profile: TradingModeProfile,
) -> bool:
    """Correct execution timeframe, not a terminal/invalidated POI, and
    still a FRESH opportunity — never an already-mitigated or invalidated
    zone (Phase 16/18/21)."""
    if poi.source_timeframe not in profile.execution_timeframes:
        return False
    if current_state is None:
        # No lifecycle record at all (e.g. a period-level/liquidity-reference
        # POI type that is NOT_APPLICABLE for lifecycle) — never eligible as
        # an execution candidate; those types are context, not trade locations.
        return False
    if current_state.poi_lifecycle_status in _TERMINAL_LIFECYCLE_STATUSES:
        return False
    if not current_state.fresh_active:
        return False
    if current_state.freshness_status is not PoiFreshnessStatus.FRESH:
        return False
    return True


def collect_candidates(
    analysis: ScannerAnalysis,
    profile: TradingModeProfile,
    mode_direction: Direction,
    correlation_state: TopDownCorrelationState,
    correlation_configuration: CorrelationConfiguration | None = None,
    confluence_configuration: ConfluenceConfiguration | None = None,
) -> tuple[RankedCandidate, ...]:
    """Every ELIGIBLE execution-timeframe POI, scored and policy-evaluated —
    not yet filtered down to a single winner (that is ``select_candidate``).
    Empty when no eligible candidate exists; this is a normal, valid result.
    """
    correlation_config = correlation_configuration or CorrelationConfiguration()
    states_by_poi = {
        state.poi_record_id: state
        for state in analysis.poi_analysis.current_poi_states
    }
    bar_context = ConfluenceBarContext(
        analysis, evaluation_time_utc=analysis.availability_time_utc
    )

    candidates: list[RankedCandidate] = []
    for poi in analysis.poi_analysis.poi_observations:
        current_state = states_by_poi.get(poi.record_id)
        if not _is_eligible_for_consideration(poi, current_state, profile):
            continue
        decision = assess_confluence(
            analysis,
            poi,
            evaluation_time_utc=analysis.availability_time_utc,
            configuration=confluence_configuration,
            bar_context=bar_context,
        )
        policy_result = evaluate_candidate_policy(
            mode_direction=mode_direction,
            correlation_state=correlation_state,
            poi_bullish=poi.direction.value == "BULLISH",
            btrc_decision=decision,
            configuration=correlation_config,
        )
        candidates.append(
            RankedCandidate(
                poi=poi,
                current_state=current_state,
                btrc_decision=decision,
                policy_result=policy_result,
            )
        )
    return tuple(candidates)


def _rank_key(
    candidate: RankedCandidate, timeframe_rank: dict[Timeframe, int]
) -> tuple[int, int, int, int, int, int]:
    """Deterministic descending sort key — see module docstring / Phase 17
    ordering: verdict eligibility, authority alignment, analytical
    permission, lifecycle readiness, confluence score, then a stable
    timeframe-rank + record-id tie-break so two candidates NEVER compare
    equal ambiguously."""
    decision = candidate.btrc_decision
    return (
        _VERDICT_RANK[candidate.policy_result.verdict],
        _ALIGNMENT_RANK[decision.trend_alignment],
        _PERMISSION_RANK.get(decision.analytical_permission, 0),
        _LIFECYCLE_RANK.get(decision.lifecycle_state, 0),
        decision.final_confluence_score,
        # Higher timeframe first among ties (more reliable/less noisy);
        # negative rank keeps this a "higher is better" descending key.
        -timeframe_rank[decision.poi_timeframe],
        # Final deterministic tie-break: record id, ascending == first when
        # negated is not meaningful for strings, so break ties directly in
        # the sort below instead of encoding string order into this tuple.
    )


def select_candidate(
    candidates: tuple[RankedCandidate, ...], timeframe_rank: dict[Timeframe, int]
) -> RankedCandidate | None:
    """The single highest-confluence ELIGIBLE candidate, deterministically
    ranked — or ``None`` when every candidate policy-resolved to
    NO_VALID_SETUP (a normal, successful analysis outcome; see
    ``docs/WEB_TOP_DOWN_CORRELATION.md`` "NO_VALID_SETUP is a result, not an
    error")."""
    eligible = [
        c for c in candidates if c.policy_result.verdict != SetupVerdict.NO_VALID_SETUP
    ]
    if not eligible:
        return None
    ordered = sorted(
        eligible,
        key=lambda c: (_rank_key(c, timeframe_rank), str(c.poi.record_id)),
        reverse=True,
    )
    return ordered[0]
