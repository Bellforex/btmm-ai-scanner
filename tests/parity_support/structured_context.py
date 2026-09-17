"""Bullish market-structure prefix for small scanner fixtures (RC3 context gate).

Test tooling only. Since the structural context gate (author decision A,
2026-09-17) a candle pattern maps only inside confirmed structure, so a bare
two-candle engulfing no longer produces a POI. ``bullish_structure_prefix``
returns OHLC string rows (the RC3 continuation series shifted down by 23) that
confirm a BULLISH structure before its last row; fixtures append their own
engulfed / engulfing pair after it. The prefix itself maps no candle pattern
(its only engulfing forms before the structure has a direction).
"""

from __future__ import annotations

from tests.parity_support.ob_origin_series import trend

__all__ = ["PREFIX_LENGTH", "bullish_structure_prefix"]

_SHIFT = -23.0


def _rows() -> list[tuple[float, float, float, float]]:
    rows = trend(100, 1.0, 16)
    rows += trend(116, -1.0, 6)
    rows += trend(110, 1.0, 12)
    rows += trend(122, -1.0, 6)
    rows += [(116.0, 116.3, 114.5, 115.0)]
    rows += [(115.0, 119.5, 114.8, 119.0)]
    rows += trend(119, 1.0, 1)
    rows += [(120.0, 122.1, 119.7, 121.0)]  # high reaches the fixture pair: no FVG
    rows += trend(121, 1.0, 1)
    return rows


def bullish_structure_prefix() -> list[tuple[str, str, str, str]]:
    return [
        tuple(f"{p + _SHIFT:.2f}" for p in row)  # type: ignore[misc]
        for row in _rows()
    ]


PREFIX_LENGTH = len(_rows())
