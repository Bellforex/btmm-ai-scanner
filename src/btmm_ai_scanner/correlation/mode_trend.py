"""Correlation-V1 (T0) — per-mode authority resolution ("mode_direction").

This is intentionally SEPARATE from BTRC's ``TrendAssessment.global_direction``
(``btmm_ai_scanner.btrc.trend_engine``), which stays fixed to its own D1
primary / W1 macro / H4 operational hierarchy regardless of trading mode —
that legacy behavior is unchanged and still drives ``assess_confluence``'s
own ``trend_alignment``/``analytical_permission`` computation. This module
adds a NEW, mode-aware authority resolution on top, using
``assess_supplied_timeframe_trend`` (itself additive, see
``btmm_ai_scanner.btrc.trend_engine``) so every mode-relevant timeframe gets
a real assessment, not just BTRC's fixed six.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import Direction, TrendState
from btmm_ai_scanner.btrc.trend_engine import assess_supplied_timeframe_trend
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.correlation.enums import TopDownCorrelationState, TradingMode
from btmm_ai_scanner.correlation.profiles import TradingModeProfile, profile_for
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis

_BULLISH_SIDE = frozenset({Direction.BULLISH, Direction.STRONG_BULLISH})
_BEARISH_SIDE = frozenset({Direction.BEARISH, Direction.STRONG_BEARISH})


class ModeTimeframeDirection(ContractModel):
    """One supplied timeframe's direction/state within a mode's top-down
    order, plus its role in that mode's profile."""

    timeframe: Timeframe
    direction: Direction
    trend_state: TrendState
    is_authority: bool
    is_execution: bool


class ModeAuthorityAssessment(ContractModel):
    mode: TradingMode
    supplied_timeframes: tuple[Timeframe, ...]
    missing_recommended_timeframes: tuple[Timeframe, ...]
    per_timeframe: tuple[ModeTimeframeDirection, ...]
    authority_anchor_timeframe: Timeframe | None
    authority_anchor_direction: Direction
    mode_direction: Direction
    correlation_state: TopDownCorrelationState
    supporting_reasons: tuple[str, ...]
    opposing_reasons: tuple[str, ...]


def assess_mode_authority(
    analysis: ScannerAnalysis,
    mode: TradingMode,
    profile: TradingModeProfile | None = None,
) -> ModeAuthorityAssessment:
    """Pure function of ``analysis`` and ``mode`` — no network, no
    randomness, no wall-clock dependency beyond what ``analysis`` itself
    already carries (``availability_time_utc``), consistent with the rest of
    the deterministic scanner core.
    """
    profile = profile or profile_for(mode)

    per_timeframe: list[ModeTimeframeDirection] = []
    direction_by_tf: dict[Timeframe, Direction] = {}
    supplied: list[Timeframe] = []
    for timeframe in profile.top_down_order:
        assessment = assess_supplied_timeframe_trend(analysis, timeframe)
        if assessment is None:
            continue
        supplied.append(timeframe)
        direction_by_tf[timeframe] = assessment.direction
        per_timeframe.append(
            ModeTimeframeDirection(
                timeframe=timeframe,
                direction=assessment.direction,
                trend_state=assessment.trend_state,
                is_authority=timeframe in profile.authority_timeframes,
                is_execution=timeframe in profile.execution_timeframes,
            )
        )

    missing_recommended = tuple(
        tf for tf in profile.recommended_timeframes if tf not in direction_by_tf
    )

    # The highest-ranked (per top_down_order, which is already
    # highest-to-lowest) authority timeframe actually supplied and resolved —
    # never the largest POSSIBLE timeframe in the profile, only the highest
    # one this specific scan actually has (Phase 9: "choose the highest valid
    # supplied authority timeframe... report that fact").
    anchor_timeframe: Timeframe | None = None
    for timeframe in profile.top_down_order:
        if timeframe in profile.authority_timeframes and timeframe in direction_by_tf:
            anchor_timeframe = timeframe
            break
    anchor_direction = direction_by_tf.get(anchor_timeframe, Direction.NEUTRAL) if anchor_timeframe else Direction.NEUTRAL

    other_authority_directions = [
        direction_by_tf[tf]
        for tf in profile.authority_timeframes
        if tf in direction_by_tf and tf != anchor_timeframe
    ]
    mode_direction = _resolve_mode_direction(anchor_direction, other_authority_directions)
    correlation_state = _resolve_correlation_state(
        anchor_direction,
        [direction_by_tf[tf] for tf in profile.authority_timeframes if tf in direction_by_tf],
    )
    supporting, opposing = _reasons(profile, direction_by_tf, anchor_timeframe, mode_direction)

    return ModeAuthorityAssessment(
        mode=mode,
        supplied_timeframes=tuple(supplied),
        missing_recommended_timeframes=missing_recommended,
        per_timeframe=tuple(per_timeframe),
        authority_anchor_timeframe=anchor_timeframe,
        authority_anchor_direction=anchor_direction,
        mode_direction=mode_direction,
        correlation_state=correlation_state,
        supporting_reasons=supporting,
        opposing_reasons=opposing,
    )


def _resolve_mode_direction(
    anchor_direction: Direction, other_authority_directions: list[Direction]
) -> Direction:
    """Deterministic mode-authority resolver, generalized from BTRC's own
    ``trend_engine._resolve_global`` pattern (anchor is primary; unanimous
    agreement from the REST of the supplied authority timeframes strengthens
    it to STRONG; execution timeframes never participate in this at all)."""
    if anchor_direction in _BULLISH_SIDE:
        if other_authority_directions and all(
            d in _BULLISH_SIDE for d in other_authority_directions
        ):
            return Direction.STRONG_BULLISH
        return Direction.BULLISH
    if anchor_direction in _BEARISH_SIDE:
        if other_authority_directions and all(
            d in _BEARISH_SIDE for d in other_authority_directions
        ):
            return Direction.STRONG_BEARISH
        return Direction.BEARISH
    # Anchor absent or neutral: fall back to unanimous agreement among
    # whatever OTHER authority timeframes were supplied; otherwise NEUTRAL.
    resolvable = [d for d in other_authority_directions if d in _BULLISH_SIDE or d in _BEARISH_SIDE]
    if resolvable and all(d in _BULLISH_SIDE for d in resolvable):
        return Direction.BULLISH
    if resolvable and all(d in _BEARISH_SIDE for d in resolvable):
        return Direction.BEARISH
    return Direction.NEUTRAL


def _resolve_correlation_state(
    anchor_direction: Direction, authority_directions: list[Direction]
) -> TopDownCorrelationState:
    bullish_count = sum(1 for d in authority_directions if d in _BULLISH_SIDE)
    bearish_count = sum(1 for d in authority_directions if d in _BEARISH_SIDE)
    neutral_count = len(authority_directions) - bullish_count - bearish_count

    if not authority_directions or (bullish_count == 0 and bearish_count == 0):
        return TopDownCorrelationState.INSUFFICIENT_CONTEXT

    if bullish_count > 0 and bearish_count > 0:
        # A real, two-sided conflict exists among the supplied authority
        # timeframes. If the anchor's own side is matched or outnumbered by
        # the opposing side, that is a material conflict directly against
        # the anchor, not a minor internal disagreement.
        if anchor_direction in _BULLISH_SIDE and bearish_count >= bullish_count:
            return TopDownCorrelationState.COUNTER_TREND
        if anchor_direction in _BEARISH_SIDE and bullish_count >= bearish_count:
            return TopDownCorrelationState.COUNTER_TREND
        minority = min(bullish_count, bearish_count)
        majority = max(bullish_count, bearish_count)
        if minority == 1 and majority >= 2:
            return TopDownCorrelationState.PARTIALLY_ALIGNED
        return TopDownCorrelationState.MIXED

    # Every resolved authority timeframe agrees with every other.
    if neutral_count > 0:
        return TopDownCorrelationState.PARTIALLY_ALIGNED
    return TopDownCorrelationState.ALIGNED


def _reasons(
    profile: TradingModeProfile,
    direction_by_tf: dict[Timeframe, Direction],
    anchor_timeframe: Timeframe | None,
    mode_direction: Direction,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    supporting: list[str] = []
    opposing: list[str] = []
    mode_side = (
        _BULLISH_SIDE
        if mode_direction in _BULLISH_SIDE
        else _BEARISH_SIDE
        if mode_direction in _BEARISH_SIDE
        else frozenset()
    )
    if anchor_timeframe is not None:
        anchor_dir = direction_by_tf[anchor_timeframe]
        supporting.append(
            f"{anchor_timeframe.value} {anchor_dir.value} is the authority anchor"
        )
    for timeframe in profile.top_down_order:
        if timeframe == anchor_timeframe or timeframe not in direction_by_tf:
            continue
        direction = direction_by_tf[timeframe]
        role = "authority" if timeframe in profile.authority_timeframes else "execution"
        if not mode_side:
            continue
        if direction in mode_side:
            supporting.append(f"{timeframe.value} {direction.value} confirms anchor ({role})")
        elif direction in _BULLISH_SIDE or direction in _BEARISH_SIDE:
            note = "opposes anchor" if role == "authority" else "does not overturn anchor"
            opposing.append(f"{timeframe.value} {direction.value} ({note})")
    return tuple(supporting), tuple(opposing)
