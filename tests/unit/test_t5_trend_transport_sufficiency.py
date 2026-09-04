"""Does the wire-derived per-timeframe direction suffice to reproduce
`_resolve_global` / `operational_context`, the two T1 outputs T5's
`trend_score` actually needs?

Exhaustive rather than randomized: the domain is exactly 6 possible values
per timeframe (5 `Direction` members plus "absent"), so every combination of
D1/W1/H4 -- 216 cases -- is checked, not sampled.
"""

from __future__ import annotations

from itertools import product

from btmm_ai_scanner.btrc.enums import Direction
from btmm_ai_scanner.btrc.trend_engine import _resolve_global
from btmm_ai_scanner.config.enums import Timeframe
from tests.parity_support.t5_trend_pine_model import (
    operational_context,
    resolve_global_direction,
)

_VALUES: tuple[Direction | None, ...] = (*Direction, None)


def test_exhaustive_global_direction_sufficiency() -> None:
    mismatches = []
    for d1, w1, h4 in product(_VALUES, repeat=3):
        direction_by_tf: dict[Timeframe, Direction] = {}
        if d1 is not None:
            direction_by_tf[Timeframe.D1] = d1
        if w1 is not None:
            direction_by_tf[Timeframe.W1] = w1
        if h4 is not None:
            direction_by_tf[Timeframe.H4] = h4
        real = _resolve_global(direction_by_tf)
        wire = resolve_global_direction(d1, w1, h4)
        if real != wire:
            mismatches.append((d1, w1, h4, real, wire))
    assert mismatches == [], mismatches[:10]


def test_exhaustive_operational_context_sufficiency() -> None:
    for h4 in _VALUES:
        direction_by_tf: dict[Timeframe, Direction] = {}
        if h4 is not None:
            direction_by_tf[Timeframe.H4] = h4
        real = direction_by_tf.get(Timeframe.H4, Direction.NEUTRAL)
        wire = operational_context(h4)
        assert real == wire


# ---------------------------------------------------------------------------
# Directed: the strengthening rule specifically
# ---------------------------------------------------------------------------


def test_d1_bullish_alone_is_not_strong() -> None:
    assert resolve_global_direction(Direction.BULLISH, None, None) == Direction.BULLISH


def test_d1_bullish_with_w1_and_h4_agreement_is_strong() -> None:
    assert (
        resolve_global_direction(Direction.BULLISH, Direction.BULLISH, Direction.STRONG_BULLISH)
        == Direction.STRONG_BULLISH
    )


def test_d1_bullish_with_only_w1_agreement_stays_plain() -> None:
    assert (
        resolve_global_direction(Direction.BULLISH, Direction.BULLISH, Direction.BEARISH)
        == Direction.BULLISH
    )


def test_d1_absent_w1_h4_agreement_gives_provisional_direction() -> None:
    assert (
        resolve_global_direction(None, Direction.BEARISH, Direction.STRONG_BEARISH)
        == Direction.BEARISH
    )


def test_d1_neutral_and_no_w1_h4_agreement_is_global_neutral() -> None:
    assert resolve_global_direction(Direction.NEUTRAL, Direction.BULLISH, None) == Direction.NEUTRAL


def test_h1_m15_m5_never_participate() -> None:
    """Not directly testable through this 3-argument signature -- which IS the
    point: `_resolve_global` never reads them, so this module correctly has no
    parameter for them at all. Pinned here as an explicit statement rather
    than left implicit."""
    import inspect

    params = list(inspect.signature(resolve_global_direction).parameters)
    assert params == ["d1", "w1", "h4"]
