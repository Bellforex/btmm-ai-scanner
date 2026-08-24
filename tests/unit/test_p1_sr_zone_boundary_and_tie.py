"""S/R regression tests for the two behaviours that decided the P1 Jul-31 case.

The July-31 resistance-anchor investigation turned on two contract details that
had no direct coverage:

1. **Touch-boundary inclusivity.** A resistance zone accepts a qualifying touch
   when ``touch_price >= zone_bottom - 0.05 * origin_atr``. The Jul-31 zone hung
   on roughly 0.02 of price, so whether that comparison is inclusive, and where
   exactly the floor sits, is load-bearing.

2. **Equal-confirmation tie-breaking.** When two same-type zones share a
   ``confirmation_time_utc``, ``detect_support_resistance_zones`` ends with a
   STABLE ``sort``, so insertion order survives: origins are iterated ascending
   by ``meaningful_confirmation_time_utc``, hence the LATER-ORIGIN zone lands
   last and is what ``[-1]`` publishes. Pine reproduces this with an explicit
   ``(confirmationTime, insertionIndex)`` key; if either side ever changed, the
   published zone would silently flip.

Expected values are DERIVED from the production formulas, never hardcoded.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SupportResistanceType, SwingType
from btmm_ai_scanner.domain.support_resistance import (
    detect_support_resistance_zones,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series

# `tests/unit` is not a package and is not on sys.path, so the sibling module
# that owns the synthetic-candle helpers and the Pine walk transcription is
# loaded by path rather than imported by name.
_SIBLING = importlib.util.spec_from_file_location(
    "_p1_sr_frontier_model",
    Path(__file__).with_name("test_pine_p1_sr_frontier_model.py"),
)
assert _SIBLING is not None and _SIBLING.loader is not None
_frontier = importlib.util.module_from_spec(_SIBLING)
# @dataclass resolves annotations via sys.modules[cls.__module__], so the module
# must be registered before its body executes.
sys.modules[_SIBLING.name] = _frontier
_SIBLING.loader.exec_module(_frontier)

_batch_walk = _frontier._batch_walk
_project = _frontier._project
_candle = _frontier._candle
_swing = _frontier._swing

CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

ORIGIN_ATR = Decimal("2.0")
ORIGIN_PRICE = Decimal("100.00")
# production geometry, resistance branch (support_resistance.py:206-207, 219-227)
ZONE_TOP = ORIGIN_PRICE
ZONE_BOTTOM = ZONE_TOP - CONFIG.support_resistance_zone_depth_atr_multiplier * ORIGIN_ATR
TOUCH_FLOOR = (
    ZONE_BOTTOM - CONFIG.support_resistance_touch_tolerance_atr_multiplier * ORIGIN_ATR
)
EPS = Decimal("0.01")

# Second origin, confirming LATER than the first but geometrically overlapping,
# so a single touch can qualify for both and force an equal-confirmation tie.
ORIGIN2_PRICE = Decimal("99.95")


# Wilder ATR(14) must be warm before any reaction can be evaluated
# (_evaluate_reaction returns None while atr_values[reaction_start] is None),
# so the structure is preceded by a quiet warm-up block.
WARMUP = 20
I_ORIGIN = WARMUP + 4          # the resistance origin high
I_OPPOSITE = WARMUP + 10       # opposite-type swing between origin and touch
I_TOUCH = WARMUP + 14          # the retest high whose price the tests move


def _series() -> tuple:
    """Warm-up, origin high, bearish leg, retest, second bearish leg.

    Both bearish legs are clean and one-directional so the reaction's
    directional-efficiency and directional-candle-share gates pass.
    """
    bars: list = []
    for i in range(WARMUP):                                   # quiet ATR warm-up
        base = 98.0 + (0.1 if i % 2 else 0.0)
        bars.append(_candle(i, base, base + 0.30, base - 0.30, base + 0.05))
    bars.append(_candle(WARMUP + 0, 98.0, 98.35, 97.9, 98.2))
    bars.append(_candle(WARMUP + 1, 98.2, 98.65, 98.1, 98.5))
    bars.append(_candle(WARMUP + 2, 98.5, 99.05, 98.4, 98.9))
    bars.append(_candle(WARMUP + 3, 98.9, 99.55, 98.8, 99.4))
    bars.append(_candle(WARMUP + 4, 99.4, 100.05, 99.3, 99.6))        # origin
    for i, (o, c) in enumerate(
        [(99.6, 99.0), (99.0, 98.4), (98.4, 97.8), (97.8, 97.2), (97.2, 96.6), (96.6, 96.0)]
    ):
        bars.append(_candle(WARMUP + 5 + i, o, o + 0.05, c - 0.05, c))
    for i, (o, c) in enumerate(
        [(96.0, 96.9), (96.9, 97.8), (97.8, 98.7), (98.7, 99.6)]
    ):
        bars.append(_candle(WARMUP + 11 + i, o, c + 0.05, o - 0.05, c))
    for i, (o, c) in enumerate(
        [(99.6, 99.0), (99.0, 98.4), (98.4, 97.8), (97.8, 97.2), (97.2, 96.6), (96.6, 96.0)]
    ):
        bars.append(_candle(WARMUP + 15 + i, o, o + 0.05, c - 0.05, c))
    return tuple(bars)


def _scenario(touch_price: Decimal, *, second_origin: bool = False) -> tuple:
    candles = _series()
    swings = [
        _swing(1, SwingType.SWING_HIGH, str(ORIGIN_PRICE), I_ORIGIN, candles,
               reference_atr=str(ORIGIN_ATR), confirmation_offset_minutes=2),
        # opposite-type swing strictly between origin and touch confirmations
        _swing(2, SwingType.SWING_LOW, "96.00", I_OPPOSITE, candles,
               reference_atr=str(ORIGIN_ATR), confirmation_offset_minutes=2),
        _swing(3, SwingType.SWING_HIGH, str(touch_price), I_TOUCH, candles,
               reference_atr=str(ORIGIN_ATR), confirmation_offset_minutes=2),
    ]
    if second_origin:
        # confirms AFTER origin 1 but BEFORE the touch, so both zones take the
        # same first qualifying touch and therefore the same confirmation time
        swings.insert(
            1,
            _swing(4, SwingType.SWING_HIGH, str(ORIGIN2_PRICE), I_ORIGIN, candles,
                   reference_atr=str(ORIGIN_ATR), confirmation_offset_minutes=3),
        )
    return candles, tuple(swings)


def _resistance(candles: tuple, swings: tuple) -> list:
    zones = detect_support_resistance_zones(candles, swings, CONFIG)
    return [z for z in zones if z.zone_type == SupportResistanceType.RESISTANCE]


def _tops(zones: list) -> list[Decimal]:
    return [z.zone_top for z in zones]


# --------------------------------------------------------------------------
# geometry the tests are built on
# --------------------------------------------------------------------------

def test_derived_geometry_matches_the_production_formulas() -> None:
    """Guards the constants above against a configuration change."""
    assert ZONE_BOTTOM == Decimal("99.800")
    assert TOUCH_FLOOR == Decimal("99.700")
    assert CONFIG.support_resistance_zone_depth_atr_multiplier == Decimal("0.10")
    assert CONFIG.support_resistance_touch_tolerance_atr_multiplier == Decimal("0.05")


def test_scenario_builds_a_zone_at_all() -> None:
    """Sanity: comfortably inside the band must produce exactly one zone."""
    candles, swings = _scenario(ZONE_BOTTOM + Decimal("0.05"))
    zones = _resistance(candles, swings)
    assert len(zones) == 1, "baseline scenario must construct a resistance zone"
    assert zones[0].zone_top == ZONE_TOP
    assert zones[0].zone_bottom == ZONE_BOTTOM


# --------------------------------------------------------------------------
# TEST B / C / D — touch boundary
# --------------------------------------------------------------------------

def test_b_touch_immediately_below_floor_does_not_construct() -> None:
    candles, swings = _scenario(TOUCH_FLOOR - EPS)
    assert _resistance(candles, swings) == []


def test_c_touch_exactly_at_floor_does_construct() -> None:
    """`>=` is inclusive — the boundary value itself qualifies."""
    candles, swings = _scenario(TOUCH_FLOOR)
    zones = _resistance(candles, swings)
    assert len(zones) == 1, "boundary touch must qualify (comparison is >=)"
    assert zones[0].zone_bottom == ZONE_BOTTOM


def test_d_touch_immediately_above_floor_does_construct() -> None:
    candles, swings = _scenario(TOUCH_FLOOR + EPS)
    assert len(_resistance(candles, swings)) == 1


@pytest.mark.parametrize(
    ("offset", "expected"),
    [(Decimal("-0.02"), 0), (Decimal("-0.01"), 0), (Decimal("0"), 1),
     (Decimal("0.01"), 1), (Decimal("0.02"), 1)],
)
def test_boundary_is_a_step_function_at_the_floor(offset: Decimal, expected: int) -> None:
    candles, swings = _scenario(TOUCH_FLOOR + offset)
    assert len(_resistance(candles, swings)) == expected


# --------------------------------------------------------------------------
# TEST A / F — equal-confirmation tie and competing zones
# --------------------------------------------------------------------------

def test_a_f_equal_confirmation_tie_publishes_the_later_origin_zone() -> None:
    """Two resistance zones, same confirmation time: later ORIGIN publishes.

    This is the exact shape of the Jul-31 case, where Zone B (origin
    2026-07-30T16:15Z) outranks Zone A (origin 2026-07-29T19:00Z) despite Zone A
    having been created first.
    """
    candles, swings = _scenario(TOUCH_FLOOR + EPS, second_origin=True)
    zones = _resistance(candles, swings)
    assert len(zones) == 2, "both origins must construct a zone"

    times = {z.confirmation_time_utc for z in zones}
    assert len(times) == 1, "the shared touch must give both zones one confirmation time"

    ordered = sorted(zones, key=lambda z: z.confirmation_time_utc)  # production key
    published = ordered[-1]
    assert published.zone_top == ORIGIN2_PRICE, (
        "on an equal-confirmation tie the LATER-ORIGIN zone must publish; "
        f"got {published.zone_top}"
    )


def test_a_tie_break_survives_the_full_detector_ordering() -> None:
    """The stable sort inside detect_support_resistance_zones must not reorder."""
    candles, swings = _scenario(TOUCH_FLOOR + EPS, second_origin=True)
    zones = detect_support_resistance_zones(candles, swings, CONFIG)
    res = [z for z in zones if z.zone_type == SupportResistanceType.RESISTANCE]
    assert _tops(res) == [ORIGIN_PRICE, ORIGIN2_PRICE], (
        "resistance zones must stay in ascending origin-confirmation order"
    )
    assert zones[-1].zone_top == ORIGIN2_PRICE


# --------------------------------------------------------------------------
# TEST E — incremental / transcription parity across the boundary
# --------------------------------------------------------------------------

@pytest.mark.parametrize(
    "offset", [Decimal("-0.02"), Decimal("-0.01"), Decimal("0"),
               Decimal("0.01"), Decimal("0.02")]
)
def test_e_pine_transcription_matches_production_across_the_boundary(
    offset: Decimal,
) -> None:
    """The Pine walk transcription must agree with production at every step
    of the boundary, not merely away from it."""
    candles, swings = _scenario(TOUCH_FLOOR + offset)
    atr = compute_atr_series(candles, CONFIG.atr_period)
    mine = _batch_walk(candles, atr, swings, CONFIG)
    theirs = tuple(_project(z) for z in detect_support_resistance_zones(candles, swings, CONFIG))
    assert mine == theirs


def test_e_transcription_agrees_on_the_competing_zone_tie() -> None:
    candles, swings = _scenario(TOUCH_FLOOR + EPS, second_origin=True)
    atr = compute_atr_series(candles, CONFIG.atr_period)
    mine = _batch_walk(candles, atr, swings, CONFIG)
    theirs = tuple(_project(z) for z in detect_support_resistance_zones(candles, swings, CONFIG))
    assert mine == theirs
    assert mine[-1] == theirs[-1], "both must agree on the PUBLISHED zone"


# --------------------------------------------------------------------------
# TEST G — Jul-31 shaped fixture, ratios taken from the real case
# --------------------------------------------------------------------------

def test_g_july31_shaped_fixture_reproduces_the_observed_flip() -> None:
    """Zone A older-origin/earlier-confirming, Zone B newer-origin, one shared
    touch sitting just above Zone B's floor -> Zone B publishes.

    Mirrors the measured relationship: Pine's sr_top equals the NEWER origin's
    price, not the older zone Python published before the touch qualified.
    """
    candles, swings = _scenario(TOUCH_FLOOR + EPS, second_origin=True)
    zones = detect_support_resistance_zones(candles, swings, CONFIG)
    published = sorted(zones, key=lambda z: z.confirmation_time_utc)[-1]
    depth = CONFIG.support_resistance_zone_depth_atr_multiplier * ORIGIN_ATR
    assert published.zone_top == ORIGIN2_PRICE
    assert published.zone_bottom == ORIGIN2_PRICE - depth
    # Origin 2 sits lower, so its floor is lower too; dropping the touch below
    # BOTH floors collapses the set to nothing.
    origin2_floor = (
        ORIGIN2_PRICE
        - CONFIG.support_resistance_zone_depth_atr_multiplier * ORIGIN_ATR
        - CONFIG.support_resistance_touch_tolerance_atr_multiplier * ORIGIN_ATR
    )
    assert origin2_floor < TOUCH_FLOOR
    candles2, swings2 = _scenario(origin2_floor - EPS, second_origin=True)
    assert _resistance(candles2, swings2) == []
    # between the two floors only the lower-origin zone survives
    candles3, swings3 = _scenario(TOUCH_FLOOR - EPS, second_origin=True)
    survivors = _resistance(candles3, swings3)
    assert [z.zone_top for z in survivors] == [ORIGIN2_PRICE]
