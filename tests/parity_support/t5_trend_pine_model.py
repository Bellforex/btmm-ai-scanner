"""The PINE-EQUIVALENT global trend resolution T5's `trend_score` needs.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY THIS IS A THIRD, DISTINCT AUTHORITY PATTERN
--------------------------------------------------
T1 has its own per-timeframe authority list (`_AUTHORITY_TIMEFRAMES`, used
only to pick which timeframes get assessed at all). T2 has `_PRIMARY_ORDER`,
a textually different six-timeframe "first present wins" scan. `_resolve_global`
is neither: it is a FIXED three-timeframe FORMULA -- D1 primary, W1+H4 either
strengthen a D1-led direction to STRONG or (D1 absent/neutral) can themselves
provide a provisional non-strong direction on their own agreement, and H1/M15/
M5 never participate at all. Confusing this with either of the other two
orders would be wrong in a way none of the T1/T2 differentials could catch,
since none of them touch `_resolve_global`.

WHAT `assess_trend` NEEDS FROM T1 THAT T5 ALSO NEEDS
--------------------------------------------------------
`global_direction = _resolve_global(direction_by_tf)` and
`operational_context = direction_by_tf.get(Timeframe.H4, Direction.NEUTRAL)`
are both pure functions of the per-timeframe `Direction`s that
`t1_trend_pine_model.assess_trend_from_transport` already proves reconstructible
from the wire -- so, like T2, this needs no new P6 field, only D1/W1/H4's own
wire-derived directions fed into this fixed formula.
"""

from __future__ import annotations

from btmm_ai_scanner.btrc.enums import Direction

_BULLISH_SIDE = frozenset({Direction.STRONG_BULLISH, Direction.BULLISH})
_BEARISH_SIDE = frozenset({Direction.STRONG_BEARISH, Direction.BEARISH})


def resolve_global_direction(
    d1: Direction | None, w1: Direction | None, h4: Direction | None
) -> Direction:
    """`trend_engine._resolve_global`, reconstructed from exactly the three
    per-timeframe directions it reads. D1 absent/NEUTRAL falls through to the
    W1+H4-agreement branch, matching the source's own `dict.get` semantics for
    a timeframe that supplied no assessment at all."""
    if d1 in _BULLISH_SIDE:
        if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
            return Direction.STRONG_BULLISH
        return Direction.BULLISH
    if d1 in _BEARISH_SIDE:
        if w1 in _BEARISH_SIDE and h4 in _BEARISH_SIDE:
            return Direction.STRONG_BEARISH
        return Direction.BEARISH
    if w1 in _BULLISH_SIDE and h4 in _BULLISH_SIDE:
        return Direction.BULLISH
    if w1 in _BEARISH_SIDE and h4 in _BEARISH_SIDE:
        return Direction.BEARISH
    return Direction.NEUTRAL


def operational_context(h4: Direction | None) -> Direction:
    return h4 if h4 is not None else Direction.NEUTRAL
