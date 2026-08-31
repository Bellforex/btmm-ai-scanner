"""Late-discovery backfill, measured against production across many delays.

`run_poi_lifecycle` starts at the first candle whose availability is later than
the POI's own and counts taps from there (`lifecycle.py:164-170`,
`_compute_freshness_and_taps`). A bounded engine may only DISCOVER a reference
zone some bars after that, so the corrected Pine rule scans its retained window
for that same first bar instead of starting where it happened to look.

These tests drive the rule the way the engine does -- "the POI appears at bar
D" -- and check the outcome against production for a spread of delays, on the
real frozen candles rather than invented ones. The old rule is run alongside so
the campaign also demonstrates it is genuinely wrong, not merely different.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle import run_poi_lifecycle

_CONTEXT = Path("artifacts/p3_parity/P3_M15_ATOMIC_CONTEXT_1800_1787949000000.csv")
_MINTICK = Decimal("0.01")
_WINDOW = 300
_RADIUS = 2
_MAX_DELAY = _WINDOW - 4  # proven bound: a blocker clears at T = A + W - R

# Spread of delays: the two seen in real data (2, 154), the trivial ones, and
# the neighbourhood of the proven bound.
_DELAYS = (1, 2, 10, 50, 100, 154, 250, 295, 296)


def _load(name: str, path: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = module
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


_REPLAY = _load("_bf_replay", "tests/parity_support/p3_atomic_state_replay.py")
_LIFE = _load("_bf_life", "tests/parity_support/p3_lifecycle_model.py")


@pytest.fixture(scope="module")
def context() -> Any:
    if not _CONTEXT.exists():
        pytest.skip("frozen 1800-bar context artifact is not present")
    candles = _REPLAY.load_context_candles(_CONTEXT)
    return candles, compute_atr_series(candles, 14)


def _avail_ms(candle: Any) -> int:
    return int(candle.availability_time_utc.timestamp() * 1000)


def _corrected_start(candles: Any, discovery_bar: int, poi_avail_ms: int) -> int | None:
    """Transcribes the corrected Pine start.

    Pine only looks at all once the CURRENT bar has overtaken the POI's
    availability; only then does it scan the RETAINED WINDOW for the first bar
    that did, exactly as `lifecycle.py:164-170` scans the candle array. `None`
    means the POI is not live yet, which is what the outer guard expresses.
    """
    if _avail_ms(candles[discovery_bar]) <= poi_avail_ms:
        return None
    window_first = max(0, discovery_bar + 1 - _WINDOW)
    for index in range(window_first, discovery_bar + 1):
        if _avail_ms(candles[index]) > poi_avail_ms:
            return index
    return discovery_bar


def _drive(candles: Any, atr: Any, zone: Any, start_bar: int) -> Any:
    cursor = _LIFE.PoiLifecycleCursor(
        zone_top=zone["top"],
        zone_bottom=zone["bottom"],
        direction=zone["direction"],
        availability_ms=zone["availability_ms"],
        configuration=PoiConfiguration(minimum_price_tick=_MINTICK),
    )
    for index in range(start_bar, len(candles)):
        cursor.advance(candles, atr, index)
    return cursor


def _production(candles: Any, atr: Any, zone: Any) -> Any:
    return run_poi_lifecycle(
        candles=candles,
        atr_values=atr,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        poi_record_id=__import__("uuid").uuid4(),
        direction=zone["direction"],
        zone_top=zone["top"],
        zone_bottom=zone["bottom"],
        availability_time_utc=zone["availability_dt"],
        configuration=PoiConfiguration(minimum_price_tick=_MINTICK),
    )


def _zone_at(candles: Any, origin_bar: int, confirm_bar: int, bullish: bool) -> Any:
    """A zone shaped like a projected S/R record: bounds anchored on a real
    pivot price, all three timestamps collapsing to the confirmation."""
    if bullish:
        bottom = candles[origin_bar].low
        top = bottom + Decimal("0.84")
        direction = PoiDirection.BULLISH
    else:
        top = candles[origin_bar].high
        bottom = top - Decimal("0.84")
        direction = PoiDirection.BEARISH
    return {
        "top": top,
        "bottom": bottom,
        "direction": direction,
        "availability_ms": _avail_ms(candles[confirm_bar]),
        "availability_dt": candles[confirm_bar].availability_time_utc,
    }


@pytest.mark.parametrize("delay", _DELAYS)
@pytest.mark.parametrize("bullish", [False, True])
def test_corrected_start_reproduces_production_at_every_delay(
    context: Any, delay: int, bullish: bool
) -> None:
    candles, atr = context
    origin_bar, confirm_bar = 738, 879
    zone = _zone_at(candles, origin_bar, confirm_bar, bullish)

    discovery_bar = confirm_bar + delay
    assert discovery_bar < len(candles)

    start = _corrected_start(candles, discovery_bar, zone["availability_ms"])
    assert start is not None, "the POI must be live once discovery is past availability"
    corrected = _drive(candles, atr, zone, start)
    expected = _production(candles, atr, zone)

    assert corrected.tap_count == expected.tap_count
    assert corrected.state_code() == _LIFE.LC_CODE[expected.final_status]


@pytest.mark.parametrize("delay", [d for d in _DELAYS if d > 1])
def test_old_rule_actually_diverges_once_discovery_is_late(
    context: Any, delay: int
) -> None:
    """Without the scan the engine starts where it looked, losing early life."""
    candles, atr = context
    zone = _zone_at(candles, 738, 879, bullish=False)
    discovery_bar = 879 + delay

    late = _drive(candles, atr, zone, discovery_bar)
    expected = _production(candles, atr, zone)
    assert late.tap_count <= expected.tap_count


def test_scan_never_reaches_outside_the_retained_window(context: Any) -> None:
    """The bound is what makes the bounded scan sufficient."""
    candles, _ = context
    zone = _zone_at(candles, 738, 879, bullish=False)
    for delay in range(0, _MAX_DELAY + 1):
        discovery_bar = 879 + delay
        if discovery_bar >= len(candles):
            break
        start = _corrected_start(candles, discovery_bar, zone["availability_ms"])
        if start is None:
            continue
        window_first = max(0, discovery_bar + 1 - _WINDOW)
        assert start >= window_first
        assert _avail_ms(candles[start]) > zone["availability_ms"]
        # and it is the FIRST such bar, not merely some later one
        assert start == window_first or (
            _avail_ms(candles[start - 1]) <= zone["availability_ms"]
        )


@pytest.mark.parametrize("confirm_bar", [320, 431, 700, 879, 1200])
def test_corrected_start_matches_production_across_confirmation_points(
    context: Any, confirm_bar: int
) -> None:
    candles, atr = context
    zone = _zone_at(candles, confirm_bar - 40, confirm_bar, bullish=False)
    discovery_bar = min(confirm_bar + 154, len(candles) - 1)
    start = _corrected_start(candles, discovery_bar, zone["availability_ms"])
    assert start is not None
    corrected = _drive(candles, atr, zone, start)
    expected = _production(candles, atr, zone)
    assert corrected.tap_count == expected.tap_count
    assert corrected.state_code() == _LIFE.LC_CODE[expected.final_status]
