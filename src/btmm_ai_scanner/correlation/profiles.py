"""Correlation-V1 (T0) — the BellForex top-down trading-mode profiles.

Product policy (which timeframes belong to which mode, in what order, which
are authority/context vs execution, and the recommended minimal set) lives
HERE, as data, not scattered across if-statements in the engine. See
``docs/WEB_TOP_DOWN_CORRELATION.md`` "Trading modes" for the product
rationale behind each profile's timeframe choice.
"""

from __future__ import annotations

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.types import ContractModel, SemVer
from btmm_ai_scanner.correlation.enums import TradingMode


class InvalidTradingModeProfileError(ValueError):
    pass


class TradingModeProfile(ContractModel):
    """A frozen, versioned description of one trading mode's timeframe
    policy. ``top_down_order`` is the full analysis universe, ordered from
    highest (authority) to lowest (execution) — every timeframe in
    ``authority_timeframes`` and ``execution_timeframes`` must appear in it,
    and the two must partition it exactly (a timeframe is either authority/
    context or execution, never both, never neither).
    """

    mode: TradingMode
    top_down_order: tuple[Timeframe, ...]
    authority_timeframes: frozenset[Timeframe]
    execution_timeframes: frozenset[Timeframe]
    recommended_timeframes: tuple[Timeframe, ...]
    minimum_timeframe_count: int
    # Every timeframe in top_down_order is a valid presentation choice — the
    # web layer may ask for the top-down result to be rendered on any of
    # them without changing the analytical decision (see
    # ``docs/WEB_TOP_DOWN_CORRELATION.md`` "Presentation timeframe policy").
    presentation_timeframes: frozenset[Timeframe]
    # Reserved for a future, explicitly-authorized alternate policy; T0 ships
    # exactly one deterministic countertrend policy
    # (``btmm_ai_scanner.correlation.policy``) and this flag is always True.
    strict_countertrend_policy: bool = True

    rule_version: SemVer = SemVer.parse("0.1.0")
    contract_version: SemVer = SemVer.parse("0.1.0")
    schema_version: SemVer = SemVer.parse("0.1.0")


def _validate_profile(profile: TradingModeProfile) -> TradingModeProfile:
    order_set = frozenset(profile.top_down_order)
    if len(order_set) != len(profile.top_down_order):
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: top_down_order contains a duplicate timeframe."
        )
    partition = profile.authority_timeframes | profile.execution_timeframes
    if partition != order_set:
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: authority_timeframes | execution_timeframes must"
            " equal the full set of timeframes in top_down_order."
        )
    if not profile.authority_timeframes.isdisjoint(profile.execution_timeframes):
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: authority_timeframes and execution_timeframes"
            " must be disjoint."
        )
    if not frozenset(profile.recommended_timeframes).issubset(order_set):
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: recommended_timeframes must be a subset of"
            " top_down_order."
        )
    if profile.minimum_timeframe_count < 1:
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: minimum_timeframe_count must be at least 1."
        )
    if profile.minimum_timeframe_count > len(order_set):
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: minimum_timeframe_count cannot exceed the size of"
            " top_down_order."
        )
    if not profile.presentation_timeframes.issubset(order_set):
        raise InvalidTradingModeProfileError(
            f"{profile.mode}: presentation_timeframes must be a subset of"
            " top_down_order."
        )
    return profile


# ---------------------------------------------------------------------------
# SCALP: H4 -> H3 -> H2 -> H1 -> M15 -> M5. Context H4/H3/H2/H1, execution
# M15/M5. Recommended minimal set H4 + H1 + M15; M5 adds precision. Minimum
# supplied count is 3, but validation (see ``engine.py``) additionally
# requires at least one context AND one execution timeframe among whatever
# is actually supplied — three context-only timeframes would satisfy the
# bare count but never a meaningful top-down result.
# ---------------------------------------------------------------------------
SCALP_PROFILE = _validate_profile(
    TradingModeProfile(
        mode=TradingMode.SCALP,
        top_down_order=(
            Timeframe.H4,
            Timeframe.H3,
            Timeframe.H2,
            Timeframe.H1,
            Timeframe.M15,
            Timeframe.M5,
        ),
        authority_timeframes=frozenset(
            {Timeframe.H4, Timeframe.H3, Timeframe.H2, Timeframe.H1}
        ),
        execution_timeframes=frozenset({Timeframe.M15, Timeframe.M5}),
        recommended_timeframes=(Timeframe.H4, Timeframe.H1, Timeframe.M15),
        minimum_timeframe_count=3,
        presentation_timeframes=frozenset(
            {
                Timeframe.H4,
                Timeframe.H3,
                Timeframe.H2,
                Timeframe.H1,
                Timeframe.M15,
                Timeframe.M5,
            }
        ),
    )
)

# ---------------------------------------------------------------------------
# DAY_TRADE: D1 -> H12 -> H9 -> H4 -> H1. Context D1/H12/H9/H4, execution H1.
# Recommended minimal set D1 + H4 + H1. Minimum supplied count is 3.
# ---------------------------------------------------------------------------
DAY_TRADE_PROFILE = _validate_profile(
    TradingModeProfile(
        mode=TradingMode.DAY_TRADE,
        top_down_order=(
            Timeframe.D1,
            Timeframe.H12,
            Timeframe.H9,
            Timeframe.H4,
            Timeframe.H1,
        ),
        authority_timeframes=frozenset(
            {Timeframe.D1, Timeframe.H12, Timeframe.H9, Timeframe.H4}
        ),
        execution_timeframes=frozenset({Timeframe.H1}),
        recommended_timeframes=(Timeframe.D1, Timeframe.H4, Timeframe.H1),
        minimum_timeframe_count=3,
        presentation_timeframes=frozenset(
            {Timeframe.D1, Timeframe.H12, Timeframe.H9, Timeframe.H4, Timeframe.H1}
        ),
    )
)

# ---------------------------------------------------------------------------
# SWING: MN1 -> W1 -> D1 -> H12 -> H9 -> H6 -> H4. Context MN1/W1/D1/H12/H9,
# execution H6/H4. Recommended minimal set W1 + D1 + H4. Minimum supplied
# count is 3 — a swing scan may supply W1 + D1 + H4 without MN1 and still be
# valid (the engine reports the highest valid supplied authority timeframe,
# never fabricates MN1 analysis it wasn't given — see ``engine.py``
# ``authority_anchor_timeframe``).
# ---------------------------------------------------------------------------
SWING_PROFILE = _validate_profile(
    TradingModeProfile(
        mode=TradingMode.SWING,
        top_down_order=(
            Timeframe.MN1,
            Timeframe.W1,
            Timeframe.D1,
            Timeframe.H12,
            Timeframe.H9,
            Timeframe.H6,
            Timeframe.H4,
        ),
        authority_timeframes=frozenset(
            {
                Timeframe.MN1,
                Timeframe.W1,
                Timeframe.D1,
                Timeframe.H12,
                Timeframe.H9,
            }
        ),
        execution_timeframes=frozenset({Timeframe.H6, Timeframe.H4}),
        recommended_timeframes=(Timeframe.W1, Timeframe.D1, Timeframe.H4),
        minimum_timeframe_count=3,
        presentation_timeframes=frozenset(
            {
                Timeframe.MN1,
                Timeframe.W1,
                Timeframe.D1,
                Timeframe.H12,
                Timeframe.H9,
                Timeframe.H6,
                Timeframe.H4,
            }
        ),
    )
)

_PROFILES_BY_MODE: dict[TradingMode, TradingModeProfile] = {
    TradingMode.SCALP: SCALP_PROFILE,
    TradingMode.DAY_TRADE: DAY_TRADE_PROFILE,
    TradingMode.SWING: SWING_PROFILE,
}


def profile_for(mode: TradingMode) -> TradingModeProfile:
    return _PROFILES_BY_MODE[mode]
