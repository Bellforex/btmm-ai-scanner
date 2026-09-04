"""The PINE-EQUIVALENT T2 regime classification, reading ONLY the transport wire.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHAT T2 ACTUALLY DEPENDS ON
------------------------------
`_regime_for_timeframe` is a pure function of `(trend_state, displacements,
config)` -- NOT of direction, streak value (used only in a supporting-evidence
STRING, never in the branch logic), or anything else T1 computed. So the wire
inputs T2 needs per timeframe are exactly: T1's own `trend_state` (already
proven reconstructible from the wire in `t1_trend_pine_model`) plus the SAME
shared displacement window the transport already carries for T3's momentum.
No new P6 field, matching the frozen audit finding.

THE ORDER TRAP
-----------------
T2's primary-timeframe order is **D1, H4, W1, H1, M15, M5** --
`regime_engine._PRIMARY_ORDER` -- textually different from T1's own authority
order (W1, D1, H4, H1, M15, M5). Reusing T1's order here would be wrong and
would only be caught by a fixture where the two orders disagree on which
timeframe is picked first; `test_t2_regime_transport_sufficiency.py` builds
exactly that fixture.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from btmm_ai_scanner.btrc.enums import Regime, TrendState

from .p5_transport_contract import P5TransportRecord

#: `regime_engine._PRIMARY_ORDER`, duplicated here as plain strings (Pine has
#: no Timeframe enum) rather than imported, so a change to the production
#: order is only noticed through the differential test -- not silently
#: inherited.
PRIMARY_ORDER: tuple[str, ...] = ("D1", "H4", "W1", "H1", "M15", "M5")


@dataclass(frozen=True)
class T2Config:
    recent_displacement_window: int = 3
    expansion_speed_ratio: Decimal = Decimal("1.50")


def regime_for_timeframe_from_transport(
    trend_state: TrendState,
    record: P5TransportRecord,
    config: T2Config | None = None,
) -> Regime:
    """`_regime_for_timeframe`, reconstructed from the shared displacement
    window already on the wire. Direction-neutral by construction: nothing
    here reads `p2Dir` or `contStreak`'s sign, matching the source's own
    framing of regime as a direction-independent dimension."""
    cfg = config or T2Config()

    if trend_state is TrendState.UNKNOWN:
        return Regime.UNCERTAIN
    if trend_state is TrendState.TRANSITION:
        return Regime.TRANSITION
    if trend_state is TrendState.TRENDING:
        return Regime.TREND
    if trend_state is TrendState.EXHAUSTING:
        return Regime.DECELERATION
    if trend_state is TrendState.RANGE:
        return Regime.RANGE

    # FORMING: refine using the shared last-`recent_displacement_window`
    # window. The wire window is capacity 3, exactly the default config, so
    # every populated slot is "recent" -- there is nothing older to exclude.
    ratios = [record.disp1Ratio, record.disp2Ratio, record.disp3Ratio][
        : record.dispWindowCount
    ][-cfg.recent_displacement_window :]
    recent_count = len(ratios)
    fast = any(r is not None and r >= float(cfg.expansion_speed_ratio) for r in ratios)
    if fast:
        return Regime.EXPANSION
    if recent_count > 0:
        return Regime.BREAKOUT_PENDING
    return Regime.COMPRESSION


def assess_regime_from_transport(
    trend_states: dict[str, TrendState],
    records: dict[str, P5TransportRecord],
    config: T2Config | None = None,
) -> Regime:
    """The GLOBAL regime: the first timeframe in `PRIMARY_ORDER` that has a
    computed regime at all. Every one of the six requested P6 contexts always
    has data once the whole indicator is warm, so in the port's actual
    reachable domain this is always D1 -- but the general "first present"
    logic is still implemented and tested, matching the source exactly."""
    regime_by_tf = {
        tf: regime_for_timeframe_from_transport(trend_states[tf], records[tf], config)
        for tf in trend_states
    }
    for tf in PRIMARY_ORDER:
        if tf in regime_by_tf:
            return regime_by_tf[tf]
    return Regime.UNCERTAIN
