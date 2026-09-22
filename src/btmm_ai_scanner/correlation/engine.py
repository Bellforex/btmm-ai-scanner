"""Correlation-V1 (T0) — the top-down correlation engine's main entry point.

``evaluate_top_down_setup`` is a pure function of an existing ``ScannerAnalysis``
(itself a pure function of the accepted candle history) plus a requested
``TradingMode`` — deterministic, no network, no randomness, no wall-clock
dependency beyond ``analysis.availability_time_utc``. It never re-detects
anything the scanner or BTRC already computed; it only classifies, filters,
ranks and explains.
"""

from __future__ import annotations

from datetime import datetime

from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.correlation.candidate import (
    RankedCandidate,
    collect_candidates,
    select_candidate,
)
from btmm_ai_scanner.correlation.configuration import CorrelationConfiguration
from btmm_ai_scanner.correlation.enums import (
    SetupVerdict,
    TradingMode,
)
from btmm_ai_scanner.correlation.mode_trend import (
    ModeAuthorityAssessment,
    assess_mode_authority,
)
from btmm_ai_scanner.correlation.profiles import TradingModeProfile, profile_for
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK

# The project's own convention (already used by btrc/regime_engine.py,
# btrc/t3_engine.py and btrc/trend_engine.py) is to import this one shared,
# module-private rank dict from scanner.replay rather than maintain a fourth
# duplicate copy — see the Timeframe audit note in
# docs/WEB_TOP_DOWN_CORRELATION.md "Timeframe ordering".
_RANK = _TIMEFRAME_RANK


class InsufficientTopDownDataError(ValueError):
    """Raised only for a genuinely invalid call (e.g. an unknown mode); a
    normal "not enough supplied timeframes" case is reported as
    SetupVerdict.INSUFFICIENT_DATA in the returned decision, never raised."""


class TopDownCorrelationDecision(ContractModel):
    """The full internal analytical result — the versioned WEB contract
    (``btmm_ai_scanner.correlation.contract``) is built FROM this, not the
    other way around. Kept separate so the analytical engine's own output
    never has to match a web-serialization shape 1:1.
    """

    mode: TradingMode
    profile: TradingModeProfile
    authority: ModeAuthorityAssessment
    candidates: tuple[RankedCandidate, ...]
    selected_candidate: RankedCandidate | None
    verdict: SetupVerdict
    verdict_reasons: tuple[str, ...]
    evaluated_at_utc: datetime
    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")


def evaluate_top_down_setup(
    analysis: ScannerAnalysis,
    mode: TradingMode,
    profile: TradingModeProfile | None = None,
    correlation_configuration: CorrelationConfiguration | None = None,
    confluence_configuration: ConfluenceConfiguration | None = None,
) -> TopDownCorrelationDecision:
    profile = profile or profile_for(mode)
    correlation_config = correlation_configuration or CorrelationConfiguration()

    authority = assess_mode_authority(analysis, mode, profile)

    # --- INSUFFICIENT_DATA gate (Phase 13D / 18): the mode profile's own
    # minimum supplied-timeframe requirement, PLUS at least one context/
    # authority timeframe AND at least one execution timeframe among what
    # was actually supplied — three context-only timeframes satisfy a bare
    # count but can never produce a meaningful top-down result. ---
    supplied_authority = [tf for tf in authority.supplied_timeframes if tf in profile.authority_timeframes]
    supplied_execution = [tf for tf in authority.supplied_timeframes if tf in profile.execution_timeframes]
    if (
        len(authority.supplied_timeframes) < profile.minimum_timeframe_count
        or len(supplied_authority) < correlation_config.minimum_resolved_authority_timeframes
        or not supplied_execution
    ):
        return TopDownCorrelationDecision(
            mode=mode,
            profile=profile,
            authority=authority,
            candidates=(),
            selected_candidate=None,
            verdict=SetupVerdict.INSUFFICIENT_DATA,
            verdict_reasons=(
                "insufficient supplied timeframes for this mode's minimum"
                f" requirements (need >= {profile.minimum_timeframe_count} total,"
                f" >= {correlation_config.minimum_resolved_authority_timeframes}"
                " authority/context, and >= 1 execution timeframe)",
            ),
            evaluated_at_utc=analysis.availability_time_utc,
        )

    candidates = collect_candidates(
        analysis,
        profile,
        authority.mode_direction,
        authority.correlation_state,
        correlation_config,
        confluence_configuration,
    )
    selected = select_candidate(candidates, _RANK)

    if selected is None:
        reasons = (
            ("no eligible execution-timeframe POI was found",)
            if not candidates
            else ("every candidate policy-resolved to NO_VALID_SETUP",)
        )
        return TopDownCorrelationDecision(
            mode=mode,
            profile=profile,
            authority=authority,
            candidates=candidates,
            selected_candidate=None,
            verdict=SetupVerdict.NO_VALID_SETUP,
            verdict_reasons=reasons,
            evaluated_at_utc=analysis.availability_time_utc,
        )

    return TopDownCorrelationDecision(
        mode=mode,
        profile=profile,
        authority=authority,
        candidates=candidates,
        selected_candidate=selected,
        verdict=selected.policy_result.verdict,
        verdict_reasons=selected.policy_result.reasons,
        evaluated_at_utc=analysis.availability_time_utc,
    )
