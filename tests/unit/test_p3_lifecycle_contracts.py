"""P3-I0 — lifecycle boundary hardening for the semantics P3 will port.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT.

Companion to `test_p3_core_contracts.py` (detector boundaries, dead states,
source-as-is guards). Here every reachable lifecycle edge is pinned at the
exact inequality, because Pine will re-implement these comparisons and a
one-tick disagreement is the difference between a real setup and a phantom.

All fixtures use zone [99.6, 100.4] (height 0.80) with a constant injected ATR
of 1.00, so the production tolerances are exact and hand-checkable
(lifecycle.py:179-186):

    overshoot = max(2*0.01, min(0.10*1.00, 0.25*0.80)) = 0.10
    contact   = max(2*0.01, min(0.05*1.00, 0.10*0.80)) = 0.05

Therefore, for a BULLISH zone: breach iff `close < 99.50` STRICTLY; reclaim iff
`close >= 99.65`; displacement iff `close >= 100.45` with a FAST leg. The
BEARISH mirror is asserted alongside.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiLifecycleStatus,
    PoiLifecycleTransitionType,
)
from btmm_ai_scanner.poi.lifecycle import LifecycleWalkResult, run_poi_lifecycle


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_C = _load("_p3lc_contracts", "test_p3_core_contracts.py")

_zone_candles = _C._zone_candles

_TOP, _BOTTOM = "100.4", "99.6"

# Reusable candle shapes, all valid under the NormalizedCandle OHLC invariants.
_INSIDE = ("100", "100.4", "99.6", "100")  # overlaps the zone
_ABOVE = ("101", "101.5", "100.8", "101.2")  # entirely above: no touch
_BELOW = ("99", "99.4", "98.5", "99")  # entirely below: no touch
_BREACH = ("99.6", "99.7", "99.4", "99.49")  # 0.11 > 0.10 -> breach
_SUSTAINED = ("99.4", "99.5", "99.2", "99.30")  # breaches again


def _run(
    candles: tuple[NormalizedCandle, ...],
    direction: PoiDirection,
    atr: str = "1.00",
    zone_top: str = _TOP,
    zone_bottom: str = _BOTTOM,
) -> LifecycleWalkResult:
    """The authoritative walk, called directly so the contract stays explicit."""
    return run_poi_lifecycle(
        candles,
        tuple(Decimal(atr) for _ in candles),
        InternalSymbol.XAUUSD,
        Timeframe.M1,
        _C._POI_RECORD_ID,
        direction,
        Decimal(zone_top),
        Decimal(zone_bottom),
        candles[0].event_time_utc,
        _C._CONFIG,
    )


def _bull(candles: tuple[NormalizedCandle, ...]) -> LifecycleWalkResult:
    return _run(candles, PoiDirection.BULLISH)


def _bear(candles: tuple[NormalizedCandle, ...]) -> LifecycleWalkResult:
    return _run(candles, PoiDirection.BEARISH)


def _kinds(result: LifecycleWalkResult) -> set[PoiLifecycleTransitionType]:
    return {t.transition_type for t in result.transitions}


# ---------------------------------------------------------------------------
# Interaction — inclusive wick overlap, independent of closes
# ---------------------------------------------------------------------------


def test_interaction_counts_inclusive_wick_overlap_not_closes() -> None:
    """lifecycle.py:111-114 is `low <= top and high >= bottom` — wick only."""
    grazing = ("99", "99.6", "98.5", "99")  # high touches zone_bottom exactly
    assert _bull(_zone_candles([_ABOVE, grazing, _ABOVE])).tap_count == 1
    missing = ("99", "99.59", "98.5", "99")  # one tick short of contact
    assert _bull(_zone_candles([_ABOVE, missing, _ABOVE])).tap_count == 0


def test_consecutive_touching_candles_are_one_tap_run() -> None:
    """Taps count MAXIMAL RUNS, never individual touching candles."""
    assert _bull(_zone_candles([_INSIDE, _INSIDE, _INSIDE])).tap_count == 1
    assert (
        _bull(_zone_candles([_INSIDE, _ABOVE, _INSIDE, _ABOVE, _INSIDE])).tap_count == 3
    )


# ---------------------------------------------------------------------------
# Breach — strict, close-only, at the exact tolerance boundary
# ---------------------------------------------------------------------------


def test_breach_is_close_only_so_a_wick_through_never_breaches() -> None:
    deep_wick = ("100", "100.4", "90", "100")  # low far below, close inside
    result = _bull(_zone_candles([_INSIDE, deep_wick, _INSIDE]))
    assert result.final_status == PoiLifecycleStatus.NO_BREACH
    assert result.transitions == ()


def test_breach_exactly_at_the_tolerance_boundary_is_not_a_breach() -> None:
    """`(zone_bottom - close) > overshoot` is STRICT: exactly 0.10 is not >."""
    at_boundary = ("99.6", "99.7", "99.4", "99.50")
    assert (
        _bull(_zone_candles([_INSIDE, at_boundary, _INSIDE])).final_status
        == PoiLifecycleStatus.NO_BREACH
    )


def test_breach_one_tick_beyond_the_tolerance_boundary_is_a_breach() -> None:
    result = _bull(_zone_candles([_INSIDE, _BREACH, _INSIDE]))
    assert PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE in _kinds(result)


def test_bearish_breach_boundary_is_the_exact_mirror() -> None:
    at_boundary = ("100.4", "100.6", "100.3", "100.50")  # exactly 0.10
    past = ("100.4", "100.6", "100.3", "100.51")  # 0.11 > 0.10
    assert (
        _bear(_zone_candles([_INSIDE, at_boundary, _INSIDE])).final_status
        == PoiLifecycleStatus.NO_BREACH
    )
    assert PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE in _kinds(
        _bear(_zone_candles([_INSIDE, past, _INSIDE]))
    )


# ---------------------------------------------------------------------------
# Reclaim — non-strict boundary, 3-bar window, breach candle excluded
# ---------------------------------------------------------------------------


def test_reclaim_exact_boundary_is_accepted_and_one_tick_short_is_not() -> None:
    """`close >= zone_bottom + contact` is NON-strict: 99.65 reclaims.

    The trailing bars must stay BELOW the reclaim line, otherwise they would
    reclaim later in the same 3-bar window and mask the boundary under test.
    """
    exactly = ("99.5", "99.8", "99.4", "99.65")
    short = ("99.5", "99.8", "99.4", "99.64")
    low = ("99.4", "99.5", "99.3", "99.45")  # never reaches 99.65
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED in _kinds(
        _bull(_zone_candles([_INSIDE, _BREACH, exactly, low, low]))
    )
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED not in _kinds(
        _bull(_zone_candles([_INSIDE, _BREACH, short, low, low]))
    )


def test_reclaim_window_is_exactly_three_bars_after_the_breach() -> None:
    """The breach candle itself is excluded; a 4th-bar recovery is too late."""
    low = ("99.4", "99.5", "99.3", "99.45")
    recover = ("99.5", "99.8", "99.4", "99.70")
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED in _kinds(
        _bull(_zone_candles([_INSIDE, _BREACH, low, low, recover, _ABOVE]))
    )
    assert PoiLifecycleTransitionType.RECLAIM_CONFIRMED not in _kinds(
        _bull(_zone_candles([_INSIDE, _BREACH, low, low, low, recover, _ABOVE]))
    )


# ---------------------------------------------------------------------------
# False invalidation — reclaim followed by a FAST leg through the far side
# ---------------------------------------------------------------------------


def test_false_invalidation_requires_reclaim_then_a_fast_displacement_leg() -> None:
    reclaim = ("99.5", "99.8", "99.4", "99.70")
    fast = ("99.7", "103", "99.6", "102.9")  # close >= 100.45 and fast
    result = _bull(_zone_candles([_INSIDE, _BREACH, reclaim, fast, _ABOVE]))
    kinds = _kinds(result)
    assert PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED in kinds
    assert PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED in kinds
    assert result.final_status == PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED


def test_reclaim_without_a_qualifying_leg_is_reclaim_without_displacement() -> None:
    reclaim = ("99.5", "99.8", "99.4", "99.70")
    drift = ("99.7", "99.9", "99.65", "99.8")  # never clears 100.45
    result = _bull(
        _zone_candles([_INSIDE, _BREACH, reclaim, drift, drift, drift, _ABOVE])
    )
    assert PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT in _kinds(result)


def test_false_invalidation_is_not_terminal_a_later_breach_reopens_a_episode() -> None:
    """Only GENUINE invalidation is terminal (lifecycle.py:366)."""
    reclaim = ("99.5", "99.8", "99.4", "99.70")
    fast = ("99.7", "103", "99.6", "102.9")
    result = _bull(
        _zone_candles([_INSIDE, _BREACH, reclaim, fast, _INSIDE, _BREACH, _INSIDE])
    )
    breaches = [
        t
        for t in result.transitions
        if t.transition_type == PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE
    ]
    assert len(breaches) == 2


# ---------------------------------------------------------------------------
# Genuine invalidation — the only terminal state
# ---------------------------------------------------------------------------


def test_genuine_invalidation_needs_a_full_window_and_a_sustained_bar_three() -> None:
    neutral = ("99.5", "99.6", "99.45", "99.55")  # inside tolerance, no breach
    genuine = _bull(
        _zone_candles([_INSIDE, _BREACH, _SUSTAINED, _SUSTAINED, _SUSTAINED, _BELOW])
    )
    assert genuine.final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    not_genuine = _bull(
        _zone_candles([_INSIDE, _BREACH, _SUSTAINED, _SUSTAINED, neutral, _BELOW])
    )
    assert not_genuine.final_status != PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED


def test_genuine_invalidation_is_terminal_and_cannot_be_resurrected() -> None:
    """The walk freezes: later recovery candles change nothing (Phase 21)."""
    recovery = ("99.5", "104", "99.4", "103.9")
    frozen = _bull(
        _zone_candles(
            [
                _INSIDE,
                _BREACH,
                _SUSTAINED,
                _SUSTAINED,
                _SUSTAINED,
                recovery,
                recovery,
                recovery,
            ]
        )
    )
    assert frozen.final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    genuine_events = [
        t
        for t in frozen.transitions
        if t.transition_type
        == PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED
    ]
    assert len(genuine_events) == 1


# ---------------------------------------------------------------------------
# No expiry; taps independent of the frozen walk
# ---------------------------------------------------------------------------


def test_age_grows_without_any_expiry_ever_occurring() -> None:
    """There is NO production expiry: age is descriptive only."""
    result = _bull(_zone_candles([_INSIDE] + [_ABOVE] * 60))
    assert result.age_in_confirmed_bars == 61
    assert result.final_status == PoiLifecycleStatus.NO_BREACH


def test_taps_keep_accumulating_after_a_terminal_invalidation() -> None:
    result = _bull(
        _zone_candles(
            [
                _INSIDE,
                _BREACH,
                _SUSTAINED,
                _SUSTAINED,
                _SUSTAINED,
                _ABOVE,
                _INSIDE,
                _ABOVE,
                _INSIDE,
            ]
        )
    )
    assert result.final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    assert result.tap_count >= 3


def _walk_with_atr(
    candles: tuple[NormalizedCandle, ...],
    atr: str,
    *,
    zone_top: str,
    zone_bottom: str,
) -> LifecycleWalkResult:
    """Same walk, but with a chosen constant ATR so the tolerance branch varies."""
    return _run(
        candles,
        PoiDirection.BULLISH,
        atr=atr,
        zone_top=zone_top,
        zone_bottom=zone_bottom,
    )


def test_zero_height_zone_falls_back_to_the_atr_bound_not_the_tick_floor() -> None:
    """lifecycle.py:185 — when `zone_height <= 0`, `bound_b := bound_a`.

    So a point zone uses the full ATR-derived tolerance (0.10 at ATR 1.00),
    NOT the two-tick floor. A 0.03 excursion therefore does not breach.
    """
    near_miss = ("99.99", "100.05", "99.9", "99.97")  # 0.03 below the point
    result = _walk_with_atr(
        _zone_candles([_INSIDE, near_miss, _INSIDE]),
        "1.00",
        zone_top="100.00",
        zone_bottom="100.00",
    )
    assert result.final_status == PoiLifecycleStatus.NO_BREACH


def test_two_tick_floor_binds_only_when_the_atr_bound_is_smaller() -> None:
    """`max(2*min_tick, min(bound_a, bound_b))` — at ATR 0.10 the floor wins.

    bound_a = 0.10*0.10 = 0.01, bound_b = 0.25*0.80 = 0.20, so the tolerance
    is max(0.02, 0.01) = 0.02 exactly.
    """
    at_floor = ("99.6", "99.7", "99.5", "99.58")  # 0.02, not > 0.02
    past_floor = ("99.6", "99.7", "99.5", "99.57")  # 0.03 > 0.02
    assert (
        _walk_with_atr(
            _zone_candles([_INSIDE, at_floor, _INSIDE]),
            "0.10",
            zone_top=_TOP,
            zone_bottom=_BOTTOM,
        ).final_status
        == PoiLifecycleStatus.NO_BREACH
    )
    assert PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE in _kinds(
        _walk_with_atr(
            _zone_candles([_INSIDE, past_floor, _INSIDE]),
            "0.10",
            zone_top=_TOP,
            zone_bottom=_BOTTOM,
        )
    )
    assert Decimal("0.02") == 2 * _C._CONFIG.minimum_price_tick
