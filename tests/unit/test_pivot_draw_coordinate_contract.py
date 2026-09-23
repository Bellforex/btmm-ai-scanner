"""Pivot IDENTITY is not pivot DRAW COORDINATE.

A swing is not always one candle: `_merge_adjacent_plateaus` merges adjacent
equal-extreme pivots into one group spanning `start_index..end_index`. The
record therefore carries `pivot_candle_record_ids` (plural),
`pivot_start_time_utc`, `pivot_end_time_utc` and `pivot_bar_index`.

`pivot_bar_index` is set to `pivot.start_index`, so the CANONICAL pivot
location is the group's FIRST candle. `pivot_end_time_utc` is the group's LAST
candle and is what the HH/HL/LH/LL renderer was drawing at -- offsetting every
multi-candle pivot's label by `(end - start)` bars at the correct price.

The root cause is a category error rather than a coordinate typo: the swing's
stable IDENTITY key was reused as a drawing COORDINATE. These tests pin the two
concepts apart in Python, before any Pine port, so the renderer contract is
enforced by the reference engine rather than by a comment.

Availability is unaffected and stays causal: confirmation controls WHEN a label
may appear, the pivot coordinates control WHERE.
"""

from __future__ import annotations

from decimal import Decimal

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from tests.unit.test_confirmed_swings import _WARM_UP, _ZIGZAG, _build

_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

#: The already-proven swing fixture. It needs no modification to expose the
#: defect: two of its five confirmed swings are multi-candle pivot GROUPS
#: (canonical bars 21 and 25, group ends 22 and 26), so 40% of its labels were
#: being drawn one bar late.
_SERIES = _WARM_UP + _ZIGZAG


def _swings():
    return detect_confirmed_swings(_build(_SERIES), _CONFIG)


def test_the_canonical_pivot_location_is_the_group_start() -> None:
    """`pivot_bar_index = pivot.start_index`, so the first candle is canonical."""
    candles = _build(_SERIES)
    by_time = {c.event_time_utc: i for i, c in enumerate(candles)}
    swings = _swings()
    assert swings, "fixture produced no confirmed swings"
    for swing in swings:
        assert by_time[swing.pivot_start_time_utc] == swing.pivot_bar_index


def test_the_first_source_candle_is_the_one_at_the_canonical_index() -> None:
    candles = _build(_SERIES)
    by_id = {c.record_id: i for i, c in enumerate(candles)}
    for swing in _swings():
        assert by_id[swing.pivot_candle_record_ids[0]] == swing.pivot_bar_index


def test_identity_and_draw_coordinate_are_different_concepts() -> None:
    """The whole defect in one assertion.

    For a multi-candle pivot the end time is NOT the pivot location. A renderer
    that draws at `pivot_end_time_utc` because that is the stable identity key
    puts the label on the wrong candle.
    """
    multi = [s for s in _swings() if len(s.pivot_candle_record_ids) > 1]
    assert multi, "fixture must contain at least one multi-candle pivot group"
    for swing in multi:
        assert swing.pivot_end_time_utc != swing.pivot_start_time_utc
        # WHERE it is drawn:
        assert swing.pivot_start_time_utc < swing.pivot_end_time_utc


def test_availability_never_precedes_the_pivot() -> None:
    """WHEN it may appear is a separate, later fact from WHERE it is drawn."""
    for swing in _swings():
        assert swing.meaningful_confirmation_time_utc >= swing.pivot_end_time_utc
        assert swing.pivot_start_time_utc <= swing.pivot_end_time_utc


def test_every_swing_price_is_the_group_extreme() -> None:
    """Y is unambiguous; only X was wrong. Guards the other half of the anchor."""
    candles = _build(_SERIES)
    by_id = {c.record_id: c for c in candles}
    for swing in _swings():
        group = [by_id[rid] for rid in swing.pivot_candle_record_ids]
        extremes = {c.high for c in group} | {c.low for c in group}
        assert swing.pivot_price in extremes
