"""Correlation-V1 (T0) — the deterministic setup-verdict policy.

No LLM, no probability, no randomness. This is the PRIMARY ARCHITECTURAL RULE
enforcement point: a lower-timeframe countertrend candidate must never be
presented as ``VALID_SETUP`` against a clear higher-timeframe mode authority
(see ``docs/WEB_TOP_DOWN_CORRELATION.md`` "Hard countertrend protection").

This never touches or reinterprets the existing BTRC hard truths
(``poi_valid``, ``btmm_valid``, ``analytical_permission``,
``trend_alignment``) — it only adds a further, mode-aware gate on top of
them. A candidate BTRC already marked ``NO_TRADE_CONTEXT``/``WATCH_ONLY``
never becomes ``VALID_SETUP`` here either, regardless of mode alignment.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import AnalyticalPermission, Direction
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.correlation.configuration import CorrelationConfiguration
from btmm_ai_scanner.correlation.enums import SetupVerdict, TopDownCorrelationState

_BULLISH_SIDE = frozenset({Direction.BULLISH, Direction.STRONG_BULLISH})
_BEARISH_SIDE = frozenset({Direction.BEARISH, Direction.STRONG_BEARISH})
_STRONG_SIDE = frozenset({Direction.STRONG_BULLISH, Direction.STRONG_BEARISH})
_BLOCKING_PERMISSIONS = frozenset({AnalyticalPermission.NO_TRADE_CONTEXT})
_SOFTENING_CORRELATION_STATES = frozenset(
    {TopDownCorrelationState.MIXED, TopDownCorrelationState.INSUFFICIENT_CONTEXT}
)


class CandidatePolicyResult(ContractModel):
    """The verdict THIS candidate would receive if it were the selected
    candidate, plus short, deterministic, machine-readable reasons —
    intended to be spoken by the BellForex avatar later, never prose
    generated here."""

    verdict: SetupVerdict
    reasons: tuple[str, ...]


def _result(verdict: SetupVerdict, reasons: list[str]) -> CandidatePolicyResult:
    return CandidatePolicyResult(verdict=verdict, reasons=tuple(reasons))


def evaluate_candidate_policy(
    *,
    mode_direction: Direction,
    correlation_state: TopDownCorrelationState,
    poi_bullish: bool,
    btrc_decision: BtrcDecision,
    configuration: CorrelationConfiguration | None = None,
) -> CandidatePolicyResult:
    config = configuration or CorrelationConfiguration()
    reasons: list[str] = []
    candidate_side = _BULLISH_SIDE if poi_bullish else _BEARISH_SIDE
    opposite_side = _BEARISH_SIDE if poi_bullish else _BULLISH_SIDE
    score = btrc_decision.final_confluence_score

    # --- rule A/B: clear authority in the candidate's OWN direction may
    # proceed; clear authority AGAINST it is the hard countertrend gate. ---
    if mode_direction in opposite_side:
        reasons.append(
            f"execution direction opposes mode authority ({mode_direction.value})"
        )
        strong_opposition = mode_direction in _STRONG_SIDE
        if (
            strong_opposition
            or correlation_state is TopDownCorrelationState.COUNTER_TREND
            or score < config.minimum_confluence_for_watch
        ):
            reasons.append("countertrend candidate cannot be the primary setup")
            return _result(SetupVerdict.NO_VALID_SETUP, reasons)
        reasons.append(
            "countertrend but authority is not strong; watching for alignment"
        )
        return _result(SetupVerdict.WATCH_FOR_ALIGNMENT, reasons)

    # --- rule C: neutral/unresolved authority never forces a direction. ---
    if mode_direction not in _BULLISH_SIDE and mode_direction not in _BEARISH_SIDE:
        reasons.append("mode authority is neutral or unresolved")
        if score >= config.minimum_confluence_for_watch:
            return _result(SetupVerdict.WATCH_FOR_ALIGNMENT, reasons)
        return _result(SetupVerdict.NO_VALID_SETUP, reasons)

    # --- authority agrees with the candidate's own side. ---
    reasons.append(f"candidate aligns with mode authority ({mode_direction.value})")
    assert mode_direction in candidate_side  # not opposite, not neutral => same side

    # BTRC's own hard/soft truths are never overridden by mode alignment.
    if btrc_decision.analytical_permission in _BLOCKING_PERMISSIONS:
        reasons.append(
            f"BTRC analytical permission is {btrc_decision.analytical_permission.value}"
        )
        return _result(SetupVerdict.NO_VALID_SETUP, reasons)
    if btrc_decision.analytical_permission is AnalyticalPermission.WATCH_ONLY:
        reasons.append("BTRC analytical permission is WATCH_ONLY")
        return _result(SetupVerdict.WATCH_FOR_ALIGNMENT, reasons)

    # Internal authority disagreement (mixed/insufficient) softens an
    # otherwise-aligned candidate to a watch, even though the anchor itself
    # agrees with it (Phase 10/14: distinguishes execution-vs-authority
    # conflict from higher-timeframe internal conflict).
    if correlation_state in _SOFTENING_CORRELATION_STATES:
        reasons.append(f"correlation state is {correlation_state.value}")
        if score >= config.minimum_confluence_for_watch:
            return _result(SetupVerdict.WATCH_FOR_ALIGNMENT, reasons)
        return _result(SetupVerdict.NO_VALID_SETUP, reasons)

    if score >= config.minimum_confluence_for_valid_setup:
        reasons.append(f"confluence score {score} meets the valid-setup threshold")
        return _result(SetupVerdict.VALID_SETUP, reasons)
    if score >= config.minimum_confluence_for_watch:
        reasons.append(f"confluence score {score} below the valid-setup threshold")
        return _result(SetupVerdict.WATCH_FOR_ALIGNMENT, reasons)
    reasons.append(f"confluence score {score} too low")
    return _result(SetupVerdict.NO_VALID_SETUP, reasons)
