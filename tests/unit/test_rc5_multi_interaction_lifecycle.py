"""RC5 multi-interaction lifecycle: a POI survives being used.

Author correction, 2026-09-21. These run the REAL ``run_poi_lifecycle`` over
constructed candles -- no mocked state -- so they pin the doctrine against the
frozen mechanics rather than against my reading of them.

The single most important fact these lock in: in EVERY case below, including
the ones where the POI is perfectly healthy, the frozen record reports
``terminal_reason = MITIGATED`` and ``fresh_active = False``, because the
lifecycle sets those on the FIRST TOUCH. Reading those fields alone would kill
a POI that price merely used. Only ``GENUINE_INVALIDATION_CONFIRMED`` means the
zone actually failed.

Geometry used throughout: a zone 100.00-102.00. For a bullish POI the far
(invalidating) side is the BOTTOM; for a bearish POI it is the TOP.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiLifecycleStatus,
    PoiTerminalReason,
)
from btmm_ai_scanner.poi.lifecycle import run_poi_lifecycle
from btmm_ai_scanner.poi.rc5_semantics import (
    DisplayHiddenReason,
    Rc5SemanticLedger,
    display_hidden_reason,
    interaction_count,
    is_rc5_active_for_display,
)
from tests.parity_support.ob_origin_series import rows_to_candles

_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_TOP = Decimal("102.00")
_BOTTOM = Decimal("100.00")
_LEAD = [(105.0, 105.5, 104.5, 105.0)]
_BEAR_LEAD = [(97.0, 97.5, 96.5, 97.0)]

_GENUINE = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
_FALSE = PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED


class _Observation:
    """Only what the RC5 view reads."""

    def __init__(self) -> None:
        self.poi_type = "X"
        self.source_candle_record_ids = (uuid4(),)
        self.record_id = uuid4()


class _State:
    def __init__(self, walk) -> None:
        self.poi_lifecycle_status = walk.final_status
        self.terminal_reason = walk.terminal_reason
        self.terminal_time_utc = walk.terminal_time_utc
        self.tap_count = walk.tap_count


def _walk(rows, direction: PoiDirection, tmp_path: Path, name: str):
    candles = rows_to_candles(rows, tmp_path, name)
    atr = [Decimal("1.0")] * len(candles)
    return run_poi_lifecycle(
        candles,
        atr,
        candles[0].symbol,
        Timeframe.M15,
        uuid4(),
        direction,
        _TOP,
        _BOTTOM,
        candles[0].availability_time_utc,
        _CONFIG,
    )


def _visible(walk) -> bool:
    return is_rc5_active_for_display(_Observation(), _State(walk), Rc5SemanticLedger())


# ---------------------------------------------------------------------------
# bullish: far side is the BOTTOM
# ---------------------------------------------------------------------------

_BULL_TOUCH = [
    *_LEAD,
    (105.0, 105.2, 101.0, 101.5),  # dips into the zone
    (101.5, 104.0, 101.4, 103.8),  # reacts up
    (103.8, 106.0, 103.5, 105.5),
]
_BULL_DEEP = [
    *_LEAD,
    (105.0, 105.2, 100.5, 100.8),  # deep, still above the far edge
    (100.8, 104.0, 100.7, 103.5),
    (103.5, 106.0, 103.2, 105.5),
]
_BULL_WICK_THROUGH = [
    *_LEAD,
    (105.0, 105.2, 99.20, 100.9),  # wick below the far edge, closes back inside
    (100.9, 104.0, 100.8, 103.5),
    (103.5, 106.0, 103.2, 105.5),
]
_BULL_CLOSE_THROUGH_RECLAIM = [
    *_LEAD,
    (105.0, 105.2, 99.00, 99.50),  # CLOSES below the far edge
    (99.5, 101.5, 99.40, 101.2),  # reclaims back inside
    (101.2, 104.0, 101.0, 103.5),
    (103.5, 106.0, 103.2, 105.5),
]
_BULL_FAILURE = [
    *_LEAD,
    (105.0, 105.2, 99.00, 99.20),
    (99.2, 99.4, 97.0, 97.2),
    (97.2, 97.5, 95.0, 95.2),
    (95.2, 95.4, 93.0, 93.2),
]
_BULL_EPISODES_THEN_FAILURE = [
    *_LEAD,
    (105.0, 105.2, 101.0, 101.5),  # episode 1
    (101.5, 104.5, 101.4, 104.2),
    (104.2, 105.0, 104.0, 104.8),
    (104.8, 105.0, 100.6, 100.9),  # episode 2, deeper
    (100.9, 104.0, 100.8, 103.6),
    (103.6, 104.0, 103.4, 103.8),
    (103.8, 104.0, 99.00, 99.20),  # episode 3, real failure
    (99.2, 99.4, 97.0, 97.2),
    (97.2, 97.5, 95.0, 95.2),
    (95.2, 95.4, 93.0, 93.2),
]


@pytest.mark.parametrize(
    ("name", "rows"),
    [
        ("A1-first-mitigation", _BULL_TOUCH),
        ("A2-deeper-mitigation", _BULL_DEEP),
        ("A4a-wick-through-far-edge", _BULL_WICK_THROUGH),
        ("A4b-close-through-then-reclaim", _BULL_CLOSE_THROUGH_RECLAIM),
    ],
)
def test_a_used_bullish_poi_survives(name: str, rows, tmp_path: Path) -> None:
    """Touch, deep entry, a wick through the far edge and even a CLOSE through
    it followed by a valid reclaim all leave the POI alive and on the chart."""
    walk = _walk(rows, PoiDirection.BULLISH, tmp_path, name)
    assert walk.final_status is not _GENUINE
    # the frozen record would have killed it on the first touch
    assert walk.terminal_reason is PoiTerminalReason.MITIGATED
    assert walk.fresh_active is False
    # RC5 keeps it
    assert _visible(walk), name
    assert interaction_count(_State(walk)) >= 1


def test_a_reclaimed_close_through_is_recorded_as_a_false_invalidation(
    tmp_path: Path,
) -> None:
    """The false-break case the author asked to preserve, by name."""
    walk = _walk(
        _BULL_CLOSE_THROUGH_RECLAIM, PoiDirection.BULLISH, tmp_path, "false-break"
    )
    assert walk.final_status is _FALSE
    assert _visible(walk)


def test_a_bullish_break_below_the_far_edge_invalidates(tmp_path: Path) -> None:
    walk = _walk(_BULL_FAILURE, PoiDirection.BULLISH, tmp_path, "bull-fail")
    assert walk.final_status is _GENUINE
    assert not _visible(walk)
    assert (
        display_hidden_reason(_Observation(), _State(walk), Rc5SemanticLedger())
        is DisplayHiddenReason.INVALIDATED
    )


def test_several_successful_episodes_then_one_failure(tmp_path: Path) -> None:
    """A11: the POI is used twice, survives both, and dies only on the break."""
    walk = _walk(
        _BULL_EPISODES_THEN_FAILURE, PoiDirection.BULLISH, tmp_path, "episodes"
    )
    assert walk.tap_count >= 2, "the series must exercise more than one episode"
    assert walk.final_status is _GENUINE
    assert not _visible(walk)


def test_the_poi_is_still_visible_after_the_earlier_episodes(
    tmp_path: Path,
) -> None:
    """The same series truncated before the failure: still alive, having been
    used twice. This is what separates episode end from POI end."""
    walk = _walk(
        _BULL_EPISODES_THEN_FAILURE[:7], PoiDirection.BULLISH, tmp_path, "eps-trunc"
    )
    assert walk.tap_count >= 2
    assert walk.final_status is not _GENUINE
    assert _visible(walk)


# ---------------------------------------------------------------------------
# bearish mirror: far side is the TOP
# ---------------------------------------------------------------------------

_BEAR_TOUCH = [
    *_BEAR_LEAD,
    (97.0, 101.0, 96.8, 100.5),  # up into the zone
    (100.5, 100.8, 97.0, 97.5),  # reacts down
    (97.5, 98.0, 95.0, 95.5),
]
_BEAR_DEEP = [
    *_BEAR_LEAD,
    (97.0, 101.8, 96.8, 101.5),  # deep, still below the far edge
    (101.5, 101.7, 97.5, 98.0),
    (98.0, 98.5, 95.5, 96.0),
]
_BEAR_FAILURE = [
    *_BEAR_LEAD,
    (97.0, 103.0, 96.8, 102.8),
    (102.8, 105.0, 102.6, 104.8),
    (104.8, 107.0, 104.6, 106.8),
    (106.8, 109.0, 106.6, 108.8),
]


@pytest.mark.parametrize(
    ("name", "rows"),
    [("A6-first-mitigation", _BEAR_TOUCH), ("A7-deeper-mitigation", _BEAR_DEEP)],
)
def test_a_used_bearish_poi_survives(name: str, rows, tmp_path: Path) -> None:
    walk = _walk(rows, PoiDirection.BEARISH, tmp_path, name)
    assert walk.final_status is not _GENUINE
    assert _visible(walk), name


def test_a_bearish_break_above_the_far_edge_invalidates(tmp_path: Path) -> None:
    walk = _walk(_BEAR_FAILURE, PoiDirection.BEARISH, tmp_path, "bear-fail")
    assert walk.final_status is _GENUINE
    assert not _visible(walk)


# ---------------------------------------------------------------------------
# the asymmetry that makes all of this necessary
# ---------------------------------------------------------------------------


def test_the_frozen_fields_alone_would_hide_every_healthy_poi(
    tmp_path: Path,
) -> None:
    """Why the RC5 view exists. terminal_reason and fresh_active are set on the
    FIRST TOUCH, so a rule reading them cannot tell "price used this zone" from
    "this zone failed"."""
    for index, rows in enumerate(
        (_BULL_TOUCH, _BULL_DEEP, _BULL_WICK_THROUGH, _BEAR_TOUCH)
    ):
        direction = (
            PoiDirection.BEARISH if rows is _BEAR_TOUCH else PoiDirection.BULLISH
        )
        walk = _walk(rows, direction, tmp_path, f"asym{index}")
        assert walk.terminal_reason is PoiTerminalReason.MITIGATED
        assert walk.fresh_active is False
        assert walk.final_status is not _GENUINE
        assert _visible(walk)
