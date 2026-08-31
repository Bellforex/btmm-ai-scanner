"""P3 reference-zone availability timing.

Production's `run_poi_lifecycle` derives its start by SCANNING the candle array
for the first bar whose availability is later than the POI's own
(`lifecycle.py:164-170`), and counts taps from that same index
(`_compute_freshness_and_taps`). It has no notion of when an engine happened to
discover the POI.

Pine used to start such a POI at the bar it was registered on. For the sixteen
candle-derived CORE types that bar IS the first qualifying bar, so the two rules
agree and the difference never showed. Reference zones are the exception: they
are a copy of P1's published S/R, and a zone whose origin is outranked by an
earlier same-direction pivot stays invisible until that pivot leaves the scan
range. The window can therefore hand P3 a zone whose availability is already far
behind, and starting it late silently skips its early life.

These tests pin the rule itself rather than any single captured number.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection

_CONTEXT = Path("artifacts/p3_parity/P3_M15_ATOMIC_CONTEXT_1800_1787949000000.csv")
_MINTICK = Decimal("0.01")
_LOOKBACK = 300
_RADIUS = 2

# The zone this whole investigation turned on: confirmed at bar 879, but the
# bounded window cannot see its origin (bar 738) until the higher same-direction
# pivot at bars 734-735 leaves the scan range at bar 1033.
_RZ2_ORIGIN_BAR = 738
_RZ2_BLOCKER_END_BAR = 735
_RZ2_CONFIRM_BAR = 879
_RZ2_DISCOVERY_BAR = 1033


def _load(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_REPLAY = _load("_rztime_replay", "tests/parity_support/p3_atomic_state_replay.py")
_LIFE = _load("_rztime_life", "tests/parity_support/p3_lifecycle_model.py")

_PINE_SOURCES = (
    "tradingview/btmm_poi_btrc_scanner_p3_dev.pine",
    "tradingview/btmm_poi_btrc_scanner_p3_atomic_parity_bundle.pine",
)


@pytest.fixture(scope="module")
def context() -> Any:
    if not _CONTEXT.exists():
        pytest.skip("frozen 1800-bar context artifact is not present")
    candles = _REPLAY.load_context_candles(_CONTEXT)
    return candles, compute_atr_series(candles, 14)


def _run_cursor(candles: Any, atr: Any, zone: Any, first_bar: int) -> Any:
    """Drive a cursor, pretending the engine only saw the POI at `first_bar`."""
    cursor = _LIFE.PoiLifecycleCursor(
        zone_top=zone["top"],
        zone_bottom=zone["bottom"],
        direction=zone["direction"],
        availability_ms=zone["availability_ms"],
        configuration=PoiConfiguration(minimum_price_tick=_MINTICK),
    )
    for index in range(first_bar, len(candles)):
        cursor.advance(candles, atr, index)
    return cursor


def _rz2_zone(candles: Any) -> dict[str, Any]:
    top = candles[_RZ2_ORIGIN_BAR].high
    return {
        "top": top,
        "bottom": top - Decimal("0.84"),
        "direction": PoiDirection.BEARISH,
        "availability_ms": int(
            candles[_RZ2_CONFIRM_BAR].availability_time_utc.timestamp() * 1000
        ),
    }


def test_discovery_delay_is_bounded_by_the_window_not_unbounded() -> None:
    """A hidden origin resurfaces once its blocker leaves the scan range.

    The scan covers [T-W+1+R, T-R], so the blocker at bar A is gone at
    T = A + W - R, and the delay from a confirmation at C is A + W - R - C.
    With C > A that is strictly less than the window, which is what makes a
    bounded backfill safe at all.
    """
    predicted = _RZ2_BLOCKER_END_BAR + _LOOKBACK - _RADIUS
    assert predicted == _RZ2_DISCOVERY_BAR
    delay = predicted - _RZ2_CONFIRM_BAR
    assert 0 < delay < _LOOKBACK
    assert delay <= _LOOKBACK - 4


def test_late_start_loses_lifecycle_history_that_production_keeps(
    context: Any,
) -> None:
    """The defect itself: the two start rules disagree for a late-seen zone."""
    candles, atr = context
    zone = _rz2_zone(candles)

    on_time = _run_cursor(candles, atr, zone, 0)
    late = _run_cursor(candles, atr, zone, _RZ2_DISCOVERY_BAR)

    assert on_time.tap_count != late.tap_count or on_time.transition_count() != (
        late.transition_count()
    ), "RZ-2 must actually exercise the difference between the two start rules"
    assert on_time.tap_count > late.tap_count


def test_starting_from_semantic_availability_matches_production(
    context: Any,
) -> None:
    """Feeding the cursor from bar 0 is what production does, and the start gate
    makes every earlier bar a no-op, so the semantic availability -- not the
    discovery bar -- is what decides where life begins."""
    candles, atr = context
    zone = _rz2_zone(candles)

    from_zero = _run_cursor(candles, atr, zone, 0)
    availability_bar = _RZ2_CONFIRM_BAR + 1
    from_availability = _run_cursor(candles, atr, zone, availability_bar)

    assert from_zero.tap_count == from_availability.tap_count
    assert from_zero.transition_count() == from_availability.transition_count()
    assert from_zero.state_code() == from_availability.state_code()


@pytest.mark.parametrize("path", _PINE_SOURCES)
def test_pine_scans_for_the_first_qualifying_bar(path: str) -> None:
    """Guard the correction in source: Pine must SCAN, not pin the current bar."""
    text = Path(path).read_text(encoding="utf-8")
    body = text[text.index("f_poiAdvanceAllLifecycles(") :]
    body = body[: body.index("\n// ===")]

    assert "for j = 0 to nW - 1" in body, "the production scan is missing"
    assert "startAbs := absFirst + j" in body
    assert "array.set(poiResumeIdx, i, startAbs)" in body
    # the old rule pinned the boundary to the current bar
    assert "array.set(poiResumeIdx, i, cbc - 1)" not in body


@pytest.mark.parametrize("path", _PINE_SOURCES)
def test_pine_backfills_taps_over_the_skipped_bars(path: str) -> None:
    """Taps are counted per arriving bar, so the skipped range needs replaying."""
    text = Path(path).read_text(encoding="utf-8")
    body = text[text.index("f_poiAdvanceAllLifecycles(") :]
    body = body[: body.index("\n// ===")]

    assert "for k = startAbs to cbc - 2" in body, "tap backfill is missing"
    assert "array.set(poiTapCount, i, array.get(poiTapCount, i) + 1)" in body
    # Pine counts a `for` DOWNWARDS when `to` < `from`; an empty backfill must
    # not silently walk backwards off the window.
    assert "if startAbs <= cbc - 2" in body


@pytest.mark.parametrize("path", _PINE_SOURCES)
def test_backfill_scan_stays_inside_the_retained_window(path: str) -> None:
    text = Path(path).read_text(encoding="utf-8")
    body = text[text.index("f_poiAdvanceAllLifecycles(") :]
    body = body[: body.index("\n// ===")]
    assert "int nW = array.size(wAvailT)" in body
    assert "array.get(wAvailT, j)" in body
