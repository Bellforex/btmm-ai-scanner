"""The P6 projection across six genuinely distinct timeframe streams.

WHAT THIS MODULE HONESTLY PROVES, AND WHAT IT DOES NOT
------------------------------------------------------
Pine cannot run locally, so nothing here compares Pine against Python. The
Pine-vs-Python differential for P6 is the atomic capture, and it is the only
thing that can settle it.

What this module does establish is the other half of that comparison being
worth anything:

* the oracle produces all five transported surfaces on all six of BTRC's
  authority timeframes, from streams whose behaviour genuinely differs;
* the outputs are non-vacuous and DIFFERENTIATED across timeframes, so a
  comparison against captured Pine values cannot pass by everything being
  trivially equal or trivially empty;
* the comparison is SENSITIVE — the mutation tests below deliberately break the
  execution model one fault at a time (window length, ATR continuity, the
  reduction that picks the last swing) and require the projection to move.
  A comparison that survived those mutations would prove nothing when run
  against real Pine output.

The mutations matter more than they look. Each corresponds to a way the Pine
section could be wrong while still compiling and still looking reasonable:
pruning to the wrong length, restarting the Wilder recurrence per window instead
of carrying it, or reducing a collection from the wrong end.

Streams are built with each timeframe's NATURAL bar spacing and its own price
behaviour — not one series retimed six times, which would make cross-timeframe
differentiation vacuous by construction.
"""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

_REPO = Path(__file__).resolve().parents[2]


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORACLE = _load("_p6_oracle_uut", "tests/parity_support/p6_projection_oracle.py")

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe  # noqa: E402
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle  # noqa: E402
from btmm_ai_scanner.contracts.raw_candle import (  # noqa: E402
    CandleCompleteness,
    CandleVolumeKind,
)
from btmm_ai_scanner.contracts.types import SemVer  # noqa: E402
from btmm_ai_scanner.domain.configuration import (  # noqa: E402
    MarketMeasurementConfiguration,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series  # noqa: E402

#: BTRC's authority hierarchy with each timeframe's natural bar length.
AUTHORITY: dict[Timeframe, int] = {
    Timeframe.W1: 7 * 24 * 60,
    Timeframe.D1: 24 * 60,
    Timeframe.H4: 4 * 60,
    Timeframe.H1: 60,
    Timeframe.M15: 15,
    Timeframe.M5: 5,
}

_T0 = datetime(2000, 1, 3, tzinfo=UTC)  # a Monday, so W1 bars start cleanly
_FP = "b" * 64
_PROV = UUID("0193f450-6666-7abc-8def-abcdefabcd66")
_RAW = UUID("0193f450-6666-7abc-8def-abcdefabcd67")

#: Per-timeframe price behaviour. Deliberately different shapes, so the six
#: streams cannot agree by construction: differing trend slope, cycle lengths,
#: amplitude and shock cadence.
_BEHAVIOUR: dict[Timeframe, tuple[float, float, float, float, int]] = {
    #            slope   cycle   ripple  amplitude  shock every N bars
    Timeframe.W1: (0.55, 41.0, 7.0, 55.0, 37),
    Timeframe.D1: (-0.30, 29.0, 5.0, 40.0, 23),
    Timeframe.H4: (0.18, 17.0, 3.5, 28.0, 19),
    Timeframe.H1: (-0.09, 23.0, 2.5, 22.0, 29),
    Timeframe.M15: (0.04, 11.0, 1.8, 15.0, 13),
    Timeframe.M5: (-0.02, 7.0, 1.2, 11.0, 11),
}

BARS = 420


def _candle(
    index: int, timeframe: Timeframe, values: tuple[Decimal, ...]
) -> NormalizedCandle:
    step = timedelta(minutes=AUTHORITY[timeframe])
    event = _T0 + step * index
    open_, high, low, close = values
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193{index:04x}-0000-7abc-8def-{index:012x}"),
            "content_fingerprint": _FP,
            "raw_candle_id": _RAW,
            "provider": "FXCM",
            "source_reference": "fxcm",
            "source_symbol": "XAUUSD",
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": event,
            "availability_time_utc": event + step,
            "processing_time_utc": event + step,
            "original_event_time": event,
            "original_availability_time": event + step,
            "original_timezone": "UTC",
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV,
        }
    )


def stream(timeframe: Timeframe, bars: int = BARS) -> tuple[NormalizedCandle, ...]:
    """A deterministic, source-valid stream with this timeframe's own behaviour."""
    slope, cycle, ripple, amplitude, shock = _BEHAVIOUR[timeframe]
    out: list[NormalizedCandle] = []
    for index in range(bars):
        base = (
            4000.0
            + slope * index
            + amplitude * math.sin(index / cycle)
            + ripple * math.sin(index / 2.7 + slope)
        )
        drift = 0.6 * math.cos(index / 3.1)
        # periodic wide-range bars, so displacement is genuinely exercised
        burst = 4.0 if index % shock == 0 else 0.0
        open_ = Decimal(f"{base:.2f}")
        close = Decimal(f"{base + drift + burst:.2f}")
        span = Decimal(f"{0.9 + burst:.2f}")
        high = max(open_, close) + span
        low = min(open_, close) - span
        out.append(_candle(index, timeframe, (open_, high, low, close)))
    return tuple(out)


def project(timeframe: Timeframe, **kwargs: Any) -> Any:
    return ORACLE.project_series(stream(timeframe), terminals=1, **kwargs)[0]


# ---------------------------------------------------------------------------
# Phase 8 -- the streams really are distinct
# ---------------------------------------------------------------------------


def test_the_six_streams_are_genuinely_distinct() -> None:
    """One price series retimed six times would make every cross-timeframe
    claim below vacuous."""
    closes = {tf: tuple(c.close for c in stream(tf)) for tf in AUTHORITY}
    assert len({v for v in closes.values()}) == len(AUTHORITY)
    times = {tf: stream(tf)[1].event_time_utc - stream(tf)[0].event_time_utc for tf in AUTHORITY}
    assert times[Timeframe.W1] > times[Timeframe.D1] > times[Timeframe.H4]
    assert times[Timeframe.H4] > times[Timeframe.H1] > times[Timeframe.M15]
    assert times[Timeframe.M15] > times[Timeframe.M5]


# ---------------------------------------------------------------------------
# Phases 3-7 -- every transported surface is produced, on every timeframe
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("timeframe", list(AUTHORITY))
def test_every_surface_is_produced_on_every_timeframe(timeframe: Timeframe) -> None:
    p = project(timeframe)
    assert p.swing_count > 0, "no swings: the stream cannot exercise P1"
    assert p.last_swing_type in (1, -1)
    assert p.last_swing_price is not None
    assert p.last_conf_time is not None
    assert p.equal_level_count >= 0
    assert p.disp_code != ORACLE.C_ST_NA, "displacement never evaluated"
    assert p.disp_ratio is not None
    assert p.p2_direction in (0, 1, -1)
    assert p.p2_transition_count >= 0


@pytest.mark.parametrize("timeframe", list(AUTHORITY))
def test_the_compare_set_is_exactly_the_transported_fields(
    timeframe: Timeframe,
) -> None:
    """Widening the compare set silently would let an untransported field
    decide a parity verdict."""
    assert set(project(timeframe).compare_values()) == {
        "swing_count",
        "last_swing_type",
        "last_swing_price",
        "last_conf_time",
        "equal_level_count",
        "disp_code",
        "disp_ratio",
        "p2_direction",
        "p2_transition_count",
        "p2_last_transition_code",
        "p2_last_broken_level",
    }


def test_the_projections_are_differentiated_across_timeframes() -> None:
    """If all six agreed, a parity comparison would pass on a projection that
    ignored its input entirely."""
    projections = {tf: project(tf) for tf in AUTHORITY}
    swing_counts = {p.swing_count for p in projections.values()}
    assert len(swing_counts) > 1, swing_counts
    prices = {p.last_swing_price for p in projections.values()}
    assert len(prices) == len(AUTHORITY), "last swing price should differ per stream"


def test_displacement_is_exercised_beyond_the_neutral_code() -> None:
    """A suite where every displacement read 0 would not test the surface."""
    codes = set()
    for tf in AUTHORITY:
        candles = stream(tf)
        mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
        atr = compute_atr_series(candles, mcfg.atr_period)
        for terminal in range(len(candles) - 60, len(candles)):
            codes.add(
                ORACLE.project_terminal(candles, atr, terminal).disp_code
            )
    assert codes - {0} != set(), f"only neutral displacement produced: {codes}"


def test_p2_transitions_are_exercised() -> None:
    """BOS/CHOCH must actually fire somewhere, or the P2 surface is untested."""
    seen = set()
    for tf in AUTHORITY:
        p = project(tf)
        if p.p2_transition_count > 0:
            seen.add(p.p2_last_transition_code)
    assert seen, "no structure transitions on any timeframe"
    assert seen <= {1, -1, 2, -2}, seen


# ---------------------------------------------------------------------------
# Phase 21 -- sensitivity. The comparison must be able to FAIL.
# ---------------------------------------------------------------------------


def _fields(projection: Any) -> tuple[object, ...]:
    return tuple(projection.compare_values().values())


def test_a_shorter_window_changes_the_projection() -> None:
    """Pine prunes to `lookbackWindow`. Pruning to a different length is a real
    way to be wrong, so the projection must be sensitive to it."""
    candles = stream(Timeframe.H1)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    atr = compute_atr_series(candles, mcfg.atr_period)
    terminal = len(candles) - 1
    correct = ORACLE.project_terminal(candles, atr, terminal, lookback=300)
    shorter = ORACLE.project_terminal(candles, atr, terminal, lookback=150)
    assert _fields(correct) != _fields(shorter)


def test_restarting_the_atr_per_window_changes_the_projection() -> None:
    """The single most consequential modelling choice: Pine carries ONE Wilder
    recurrence across the whole context. Restarting it per window is the
    classic mistake, and it must not be invisible."""
    candles = stream(Timeframe.H4)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    terminal = len(candles) - 1

    continuous = ORACLE.project_terminal(
        candles, compute_atr_series(candles, mcfg.atr_period), terminal
    )
    window_first = max(0, terminal + 1 - ORACLE.LOOKBACK)
    restarted_series = compute_atr_series(
        candles[window_first : terminal + 1], mcfg.atr_period
    )
    # pad so the same slice offsets apply, then project with the wrong ATR
    padded = tuple([None] * window_first) + tuple(restarted_series)
    restarted = ORACLE.project_terminal(candles, padded, terminal)
    assert _fields(continuous) != _fields(restarted)


def test_reducing_from_the_wrong_end_changes_the_projection() -> None:
    """Pine reports the LAST swing of the window. Taking the first is a
    reduction bug that a count-only comparison would miss entirely."""
    candles = stream(Timeframe.D1)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    atr = compute_atr_series(candles, mcfg.atr_period)
    terminal = len(candles) - 1
    window = candles[max(0, terminal + 1 - ORACLE.LOOKBACK) : terminal + 1]
    watr = ORACLE._REPLAY.window_atr(atr, terminal, ORACLE.LOOKBACK)
    with ORACLE._TRUNC.injected_atr(watr):
        swings = ORACLE._DIAG._confirmed_swings(window, mcfg)
    assert len(swings) > 1, "need several swings for this to mean anything"
    assert swings[0].pivot_price != swings[-1].pivot_price


def test_a_different_stream_changes_the_projection() -> None:
    """The baseline sanity check: the projection must depend on its input."""
    assert _fields(project(Timeframe.W1)) != _fields(project(Timeframe.M5))
