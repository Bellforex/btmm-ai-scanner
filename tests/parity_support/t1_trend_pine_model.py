"""The PINE-EQUIVALENT T1 trend classification, reading ONLY the transport wire.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHAT THIS PROVES THAT THE TRANSPORT CAMPAIGN DID NOT
--------------------------------------------------------
The 26-field campaign proved Pine can COMPUTE and TRANSMIT contStreak,
priorOppStreak, exhaustFlag, the four transition types, stateAvailT and the
old p2Dir/swingCount correctly. It never asked whether those fields are
SUFFICIENT to reproduce `assess_trend`'s classification -- this module answers
that, by classifying from the wire fields alone and requiring agreement with
the real `_assess_timeframe` on the full collections it actually reads.

WHY `altCount4` STAYS UNTRANSPORTED HERE TOO
-------------------------------------------------
`_alternation_count` needs a CHOCH count over the last `range_window`
transitions. The transport carries `trans1Type..trans4Type` (oldest -> newest,
`transWindowCount` valid) precisely so this module can compute that count
itself, over ITS OWN `range_window` -- which the capacity test in
`test_p5_transport_ext_contract.py` guarantees fits, but does not assume stays
frozen at 4 forever. If `range_window` config ever grew past the 4-slot
capacity, `_alternation_from_window` below raises rather than silently
truncating, which is the failure this design was built to surface early.
"""

from __future__ import annotations

from dataclasses import dataclass

from btmm_ai_scanner.btrc.enums import Direction, TrendState

from .p5_transport_contract import (
    DIR_BULLISH,
    DIR_UNDETERMINED,
    TR_BEARISH_CHOCH,
    TR_BULLISH_CHOCH,
    TRANSITION_WINDOW_CAPACITY,
    P5TransportRecord,
)


#: Mirrors `trend_configuration.TrendEngineConfiguration`'s defaults exactly.
#: A distinct dataclass rather than importing the production one: this module
#: reads only wire-transportable scalars, and pinning that boundary in the
#: type signature is deliberate -- Pine cannot receive a Python config object.
@dataclass(frozen=True)
class T1Config:
    min_swings_for_assessment: int = 2
    trend_min_streak: int = 1
    strong_streak: int = 3
    range_window: int = 4
    range_choch_count: int = 3


_CHOCH_CODES = (TR_BULLISH_CHOCH, TR_BEARISH_CHOCH)


def _alternation_from_window(record: P5TransportRecord, window: int) -> int:
    """CHOCH count among the last `window` transitions, computed from the
    bounded wire window -- never from a full history Pine does not have."""
    if window > TRANSITION_WINDOW_CAPACITY:
        raise ValueError(
            f"range_window {window} exceeds the transport's "
            f"{TRANSITION_WINDOW_CAPACITY}-slot capacity"
        )
    slots = [record.trans1Type, record.trans2Type, record.trans3Type, record.trans4Type]
    count = record.transWindowCount
    # The wire window is LEFT-ALIGNED oldest -> newest: slot1..slot{count} are
    # populated (slot{count} is the NEWEST), and everything past `count` is
    # C_ST_NA filler, not older history -- there is no older history on the
    # wire to reach for even if `window` exceeded `count`. A first version of
    # this function assumed the opposite (right-alignment) and silently
    # counted filler slots as transitions; the randomized differential in
    # `test_t1_trend_transport_sufficiency.py` is what caught it.
    populated = slots[:count]
    tail = populated[-window:] if window < len(populated) else populated
    return sum(1 for code in tail if code in _CHOCH_CODES)


@dataclass(frozen=True)
class T1Result:
    trend_state: TrendState
    direction: Direction


def assess_trend_from_transport(
    *,
    p2_direction: int,
    swing_count: int,
    record: P5TransportRecord,
    config: T1Config | None = None,
) -> T1Result:
    """`_assess_timeframe`, reconstructed from exactly the wire fields Pine
    receives: the OLD scalars (p2Dir, swingCount) plus the 26-field extension.
    No full transition or swing history is read -- there is none on the wire.
    """
    cfg = config or T1Config()

    # `_assess_timeframe`'s full check is `current_state is None or
    # analyzed_swing_count < min`. `current_state is None` means this
    # timeframe supplied no structure analysis at all -- unreachable for a
    # warmed P6 requested context, which always calls the structure walk and
    # always gets a real (if UNDETERMINED) state back. The randomized
    # differential below still generates `current_state=None` on the full-data
    # side and requires the wire-side reduction to agree, so this
    # simplification is verified empirically rather than merely asserted.
    if swing_count < cfg.min_swings_for_assessment:
        return T1Result(TrendState.UNKNOWN, Direction.NEUTRAL)

    if p2_direction == DIR_UNDETERMINED:
        return T1Result(TrendState.FORMING, Direction.NEUTRAL)

    is_bullish = p2_direction == DIR_BULLISH
    streak = record.contStreak
    alternation = _alternation_from_window(record, cfg.range_window)

    if alternation >= cfg.range_choch_count:
        trend_state = TrendState.RANGE
    elif streak == 0:
        if record.priorOppStreak >= cfg.trend_min_streak:
            trend_state = TrendState.TRANSITION
        else:
            trend_state = TrendState.FORMING
    elif record.exhaustFlag == 1:
        trend_state = TrendState.EXHAUSTING
    else:
        trend_state = TrendState.TRENDING

    if trend_state is TrendState.TRENDING and streak >= cfg.strong_streak:
        direction = Direction.STRONG_BULLISH if is_bullish else Direction.STRONG_BEARISH
    else:
        direction = Direction.BULLISH if is_bullish else Direction.BEARISH

    return T1Result(trend_state, direction)
