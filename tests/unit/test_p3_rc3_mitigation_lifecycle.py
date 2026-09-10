"""RC3 — first-reaction mitigation, terminal cause, and fresh-active eligibility.

THIS FILE ASSERTS THE AUTHORITATIVE PRODUCTION CONTRACT, against
`run_poi_lifecycle` itself rather than a model of it.

Fixtures reuse the calibrated zone from `test_p3_lifecycle_contracts.py`:
[99.6, 100.4] with a constant injected ATR of 1.00, so overshoot is exactly
0.10 and a bullish breach means `close < 99.50` strictly. That matters here
because breach is the road to INVALIDATED, and the two terminal causes have to
be raceable against each other on purpose rather than by accident.

Every walk in this file makes the POI available at the close of candle 0, so
scanning starts at candle 1. Candle 0 is therefore the POI's own availability
bar and is the fixture for the self-mitigation guard.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from types import ModuleType

import pytest

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.enums import (
    PoiDirection,
    PoiFreshnessStatus,
    PoiLifecycleStatus,
    PoiTerminalReason,
)
from btmm_ai_scanner.poi.lifecycle import (
    LifecycleWalkResult,
    resolve_terminal,
    run_poi_lifecycle,
)


def _load(name: str, filename: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        name, Path(__file__).with_name(filename)
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_C = _load("_rc3_mitigation_contracts", "test_p3_core_contracts.py")

_TOP, _BOTTOM = "100.4", "99.6"

#: The POI's own availability bar, deliberately sitting right across the zone.
_AVAILABILITY_BAR = ("100", "100.4", "99.6", "100")
#: Entirely above the zone: `low` 100.8 > `top` 100.4, so no contact.
_CLEAR_ABOVE = ("101", "101.5", "100.8", "101.2")
#: Entirely below the zone: `high` 99.4 < `bottom` 99.6, so no contact.
_CLEAR_BELOW = ("99", "99.4", "98.5", "99")
#: Wick down into the zone, body entirely above it.
_WICK_TOUCH = ("101", "101.4", "100.3", "101.1")
#: Body trading inside the zone.
_BODY_TOUCH = ("100.5", "100.6", "99.9", "100.0")
#: Straight through from above to below.
_TRAVERSAL = ("101", "101.2", "99.0", "99.2")
#: `low` exactly on `top`: the inclusive-boundary fixture.
_TOUCH_TOP_EXACTLY = ("101", "101.4", "100.4", "101.1")
#: `high` exactly on `bottom`, from underneath.
_TOUCH_BOTTOM_EXACTLY = ("99.2", "99.6", "99.0", "99.3")
#: close 99.49 is 0.11 below the bottom, past the 0.10 overshoot.
_BREACH = ("99.6", "99.7", "99.4", "99.49")
#: Breaches again without ever re-entering the zone.
_SUSTAINED = ("99.4", "99.5", "99.2", "99.30")
#: A breach that never touches the zone: the whole range sits under `bottom`.
_GAP_BREACH = ("99.4", "99.45", "99.2", "99.30")


def _walk(
    specs: list[tuple[str, str, str, str]],
    direction: PoiDirection = PoiDirection.BULLISH,
    zone_top: str = _TOP,
    zone_bottom: str = _BOTTOM,
) -> LifecycleWalkResult:
    """Run the authoritative walk with the POI available at candle 0's close."""
    candles = _C._zone_candles(specs)
    return run_poi_lifecycle(
        candles,
        tuple(Decimal("1.00") for _ in candles),
        _C.InternalSymbol.XAUUSD,
        _C.Timeframe.M1,
        _C._POI_RECORD_ID,
        direction,
        Decimal(zone_top),
        Decimal(zone_bottom),
        candles[0].availability_time_utc,
        _C._CONFIG,
    )


def _bar(specs: list[tuple[str, str, str, str]], index: int) -> NormalizedCandle:
    return _C._zone_candles(specs)[index]


# ---- fresh on creation ------------------------------------------------------


def test_a_poi_with_no_later_contact_stays_fresh_active() -> None:
    result = _walk([_AVAILABILITY_BAR, _CLEAR_ABOVE, _CLEAR_ABOVE])
    assert result.fresh_active is True
    assert result.terminal_reason is None
    assert result.terminal_time_utc is None
    assert result.mitigation_time_utc is None
    assert result.freshness_status is PoiFreshnessStatus.FRESH


def test_a_poi_whose_history_has_not_started_yet_is_fresh() -> None:
    result = _walk([_AVAILABILITY_BAR])
    assert result.fresh_active is True
    assert result.terminal_reason is None


# ---- the availability bar cannot consume itself -----------------------------


def test_the_availability_bar_sitting_across_the_zone_does_not_mitigate() -> None:
    """Candle 0 overlaps the zone completely and must still leave it fresh."""
    result = _walk([_AVAILABILITY_BAR, _CLEAR_ABOVE])
    assert result.fresh_active is True
    assert result.terminal_reason is None


def test_a_bar_before_availability_does_not_mitigate() -> None:
    specs = [_BODY_TOUCH, _AVAILABILITY_BAR, _CLEAR_ABOVE]
    candles = _C._zone_candles(specs)
    result = run_poi_lifecycle(
        candles,
        tuple(Decimal("1.00") for _ in candles),
        _C.InternalSymbol.XAUUSD,
        _C.Timeframe.M1,
        _C._POI_RECORD_ID,
        PoiDirection.BULLISH,
        Decimal(_TOP),
        Decimal(_BOTTOM),
        candles[1].availability_time_utc,
        _C._CONFIG,
    )
    assert result.fresh_active is True


# ---- how contact is made does not matter ------------------------------------


@pytest.mark.parametrize(
    ("label", "contact"),
    [
        ("wick only", _WICK_TOUCH),
        ("body penetration", _BODY_TOUCH),
        ("full traversal", _TRAVERSAL),
        ("low exactly on top", _TOUCH_TOP_EXACTLY),
        ("high exactly on bottom", _TOUCH_BOTTOM_EXACTLY),
    ],
)
def test_every_contact_shape_mitigates(
    label: str, contact: tuple[str, str, str, str]
) -> None:
    specs = [_AVAILABILITY_BAR, _CLEAR_ABOVE, contact, _CLEAR_ABOVE]
    result = _walk(specs)
    assert result.terminal_reason is PoiTerminalReason.MITIGATED, label
    assert result.fresh_active is False, label
    assert result.terminal_time_utc == _bar(specs, 2).availability_time_utc, label


def test_a_bar_that_clears_the_zone_entirely_is_not_contact() -> None:
    assert _walk([_AVAILABILITY_BAR, _CLEAR_ABOVE]).fresh_active is True
    assert _walk([_AVAILABILITY_BAR, _CLEAR_BELOW]).fresh_active is True


# ---- the mitigation timestamp is the first contact, not the last ------------


def test_the_mitigation_timestamp_is_the_first_contact_bar() -> None:
    specs = [
        _AVAILABILITY_BAR,
        _CLEAR_ABOVE,
        _BODY_TOUCH,
        _CLEAR_ABOVE,
        _BODY_TOUCH,
    ]
    result = _walk(specs)
    assert result.mitigation_time_utc == _bar(specs, 2).availability_time_utc
    assert result.terminal_time_utc == result.mitigation_time_utc


def test_repeated_contact_does_not_move_the_terminal_time() -> None:
    short = _walk([_AVAILABILITY_BAR, _BODY_TOUCH])
    long = _walk([_AVAILABILITY_BAR, _BODY_TOUCH, _BODY_TOUCH, _BODY_TOUCH])
    assert short.terminal_time_utc == long.terminal_time_utc


# ---- mitigation vs invalidation, in both orders ------------------------------


def test_a_gap_breach_before_any_contact_invalidates() -> None:
    """The whole breach sequence stays under the zone, so nothing ever touches."""
    specs = [_AVAILABILITY_BAR, _GAP_BREACH, _SUSTAINED, _SUSTAINED, _SUSTAINED]
    result = _walk(specs)
    assert result.final_status is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    assert result.terminal_reason is PoiTerminalReason.INVALIDATED
    assert result.mitigation_time_utc is None
    assert result.fresh_active is False


def test_contact_before_a_breach_keeps_the_cause_as_mitigated() -> None:
    """The invalidation is still recorded; it just does not take the cause."""
    specs = [
        _AVAILABILITY_BAR,
        _BODY_TOUCH,
        _BREACH,
        _SUSTAINED,
        _SUSTAINED,
        _SUSTAINED,
    ]
    result = _walk(specs)
    assert result.final_status is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    assert result.terminal_reason is PoiTerminalReason.MITIGATED
    assert result.terminal_time_utc == _bar(specs, 1).availability_time_utc
    assert result.invalidation_time_utc is not None
    assert result.invalidation_time_utc > result.terminal_time_utc


def test_the_terminal_cause_is_immutable_once_set() -> None:
    """Extending the history past the terminal bar changes neither field."""
    specs = [_AVAILABILITY_BAR, _BODY_TOUCH]
    base = _walk(specs)
    extended = _walk([*specs, _BREACH, _SUSTAINED, _SUSTAINED, _SUSTAINED, _BODY_TOUCH])
    assert extended.terminal_reason is base.terminal_reason
    assert extended.terminal_time_utc == base.terminal_time_utc
    assert extended.mitigation_time_utc == base.mitigation_time_utc


# ---- the precedence helper, pinned directly ---------------------------------


_EARLY = _C._zone_candles([_AVAILABILITY_BAR, _BODY_TOUCH])[0].availability_time_utc
_LATE = _C._zone_candles([_AVAILABILITY_BAR, _BODY_TOUCH])[1].availability_time_utc


def test_resolve_terminal_ranks_by_time_not_by_kind() -> None:
    assert resolve_terminal(_EARLY, _LATE)[0] is PoiTerminalReason.MITIGATED
    assert resolve_terminal(_LATE, _EARLY)[0] is PoiTerminalReason.INVALIDATED
    assert resolve_terminal(None, _EARLY)[0] is PoiTerminalReason.INVALIDATED
    assert resolve_terminal(_EARLY, None)[0] is PoiTerminalReason.MITIGATED
    assert resolve_terminal(None, None)[0] is None


def test_resolve_terminal_clears_the_mitigation_time_when_invalidation_wins() -> None:
    reason, terminal, mitigation = resolve_terminal(_LATE, _EARLY)
    assert reason is PoiTerminalReason.INVALIDATED
    assert terminal == _EARLY
    assert mitigation is None


def test_a_simultaneous_pair_resolves_to_mitigated() -> None:
    """Equal times cannot arise from one bar, but the tie must still be fixed."""
    assert resolve_terminal(_EARLY, _EARLY)[0] is PoiTerminalReason.MITIGATED


# ---- mutants -----------------------------------------------------------------


def test_mutant_same_bar_self_mitigation_would_kill_the_poi_instantly() -> None:
    """Scanning from the availability bar instead of after it flips the verdict."""
    specs = [_AVAILABILITY_BAR, _CLEAR_ABOVE]
    candles = _C._zone_candles(specs)
    assert candles[0].low <= Decimal(_TOP) and candles[0].high >= Decimal(_BOTTOM)
    assert _walk(specs).fresh_active is True


def test_mutant_ignoring_a_wick_touch_would_leave_a_used_zone_fresh() -> None:
    body_only = Decimal(_WICK_TOUCH[0]), Decimal(_WICK_TOUCH[3])
    assert min(body_only) > Decimal(_TOP)
    assert _walk([_AVAILABILITY_BAR, _WICK_TOUCH]).fresh_active is False


def test_mutant_exclusive_boundary_comparison_would_miss_an_exact_touch() -> None:
    grazing = _C._zone_candles([_TOUCH_TOP_EXACTLY])[0]
    assert grazing.low == Decimal(_TOP)
    assert _walk([_AVAILABILITY_BAR, _TOUCH_TOP_EXACTLY]).fresh_active is False


def test_mutant_keeping_a_mitigated_poi_active_contradicts_the_terminal_field() -> None:
    result = _walk([_AVAILABILITY_BAR, _BODY_TOUCH])
    assert (result.terminal_reason is None) == result.fresh_active


def test_mutant_mapping_mitigation_as_invalidation_would_lose_the_distinction() -> None:
    touched = _walk([_AVAILABILITY_BAR, _BODY_TOUCH])
    gapped = _walk([_AVAILABILITY_BAR, _GAP_BREACH, _SUSTAINED, _SUSTAINED, _SUSTAINED])
    assert touched.terminal_reason is not gapped.terminal_reason


def test_mutant_omitting_the_terminal_reason_is_detectable_from_fresh_active() -> None:
    for result in (
        _walk([_AVAILABILITY_BAR, _BODY_TOUCH]),
        _walk([_AVAILABILITY_BAR, _GAP_BREACH, _SUSTAINED, _SUSTAINED, _SUSTAINED]),
    ):
        assert result.fresh_active is False
        assert result.terminal_reason is not None
        assert result.terminal_time_utc is not None


# ---- registry evidence survives termination ---------------------------------


def test_a_mitigated_poi_keeps_its_transitions_and_tap_history() -> None:
    specs = [
        _AVAILABILITY_BAR,
        _BODY_TOUCH,
        _BREACH,
        _SUSTAINED,
        _SUSTAINED,
        _SUSTAINED,
    ]
    result = _walk(specs)
    assert result.terminal_reason is PoiTerminalReason.MITIGATED
    assert result.transitions, "breach evidence must survive mitigation"
    assert result.tap_count >= 1
    assert result.freshness_status is PoiFreshnessStatus.INTERACTED
    assert result.age_in_confirmed_bars > 0


# ---- the bearish mirror ------------------------------------------------------


def test_the_bearish_direction_mitigates_on_the_same_contact_rule() -> None:
    result = _walk([_AVAILABILITY_BAR, _BODY_TOUCH], direction=PoiDirection.BEARISH)
    assert result.terminal_reason is PoiTerminalReason.MITIGATED


def test_a_bearish_gap_breach_above_the_zone_invalidates() -> None:
    above_breach = ("100.5", "100.6", "100.45", "100.55")
    specs = [
        _AVAILABILITY_BAR,
        above_breach,
        above_breach,
        above_breach,
        above_breach,
    ]
    result = _walk(specs, direction=PoiDirection.BEARISH)
    assert result.final_status is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    assert result.terminal_reason is PoiTerminalReason.INVALIDATED
