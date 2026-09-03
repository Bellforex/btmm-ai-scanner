"""How much M15 history the oracle must be given, settled before any capture.

THE AMBIGUITY THIS REMOVES
--------------------------
Measured live on FX:XAUUSD with an M15 host, all six requested contexts running
the SAME projection at the SAME request envelope:

    W1 / D1 / H4 / H1 / M5    dataset 1251   confirmed 1250
    M15                       dataset 1800   confirmed 1799

The asymmetry is not in the source. `C_P6_REQUEST_CALC_BARS` is one derived
constant used by all six `request.security` calls, and the projection function is
literally the same function. It is TradingView behaviour: requesting the chart's
OWN timeframe does not create a reduced context, so M15 runs over the host's
1800-bar envelope instead of the 1251 it asked for.

That has a direct consequence for the capture, and getting it wrong would be
invisible. The oracle computes ONE continuous Wilder recurrence over every candle
it is handed. Hand it the last 1251 M15 bars when Pine actually ran over 1799 and
the ATR series differs from the first bar onward — which shifts every ATR-scaled
swing tolerance, and can move swings, equal levels and the whole P2 walk with it.
The comparison would then be measuring the wrong thing while looking like an
honest mismatch, and the ownership hunt would start in the wrong place.

So the rule this module pins is:

    each timeframe's captured input must be exactly the confirmed bars THAT
    context processed -- 1250 for the five requested contexts, the host's full
    confirmed history for M15

The tests below also MEASURE how much margin there is, and the answer is
uncomfortable: dropping 120 warm-up bars changes every ATR value and still leaves
this stream's projection bit-identical. So an approximate slice can agree with
Pine for reasons unrelated to the port being correct. That is an argument for
exactness, not against it -- the margin is real but unquantified, and a borderline
tolerance case is exactly where it would run out.
"""

from __future__ import annotations

import importlib.util
import re
import sys
from pathlib import Path
from typing import Any

_REPO = Path(__file__).resolve().parents[2]
P6_DEV = _REPO / "tradingview" / "btmm_poi_btrc_scanner_p6_dev.pine"


def _load(name: str, relpath: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, _REPO / relpath)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ORACLE = _load("_p6_oracle_m15", "tests/parity_support/p6_projection_oracle.py")
STREAMS = _load("_p6_streams_m15", "tests/unit/test_p6_six_timeframe_projection.py")

from btmm_ai_scanner.config.enums import Timeframe  # noqa: E402
from btmm_ai_scanner.domain.configuration import (  # noqa: E402
    MarketMeasurementConfiguration,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series  # noqa: E402

#: Measured live, 2026-09-03, FX:XAUUSD, M15 host. Confirmed bars per context.
MEASURED_CONFIRMED: dict[str, int] = {
    "W1": 1250,
    "D1": 1250,
    "H4": 1250,
    "H1": 1250,
    "M15": 1799,
    "M5": 1250,
}

HOST_ENVELOPE = 1800
REQUEST_ENVELOPE = 1251


# ---------------------------------------------------------------------------
# The asymmetry is TradingView's, not the source's
# ---------------------------------------------------------------------------


def test_all_six_requests_use_one_derived_envelope() -> None:
    """If the source special-cased M15, the asymmetry would be ours to fix.
    It does not: one constant, six identical call sites."""
    source = P6_DEV.read_text(encoding="utf-8")
    calls = re.findall(r"request\.security\([^\n]*", source)
    assert len(calls) == 6, len(calls)
    for call in calls:
        assert "calc_bars_count = C_P6_REQUEST_CALC_BARS" in call, call
    assert "int C_P6_REQUEST_CALC_BARS = C_P1_MIN_CALC_BARS + 1" in source


def test_the_same_projection_function_serves_every_timeframe() -> None:
    source = P6_DEV.read_text(encoding="utf-8")
    assert source.count("f_p6TfProjection()") == 7  # one definition, six calls


def test_only_the_host_timeframe_exceeds_the_request_envelope() -> None:
    """M15 is the host timeframe, and it is the only one that ran long."""
    over = {tf: n for tf, n in MEASURED_CONFIRMED.items() if n > REQUEST_ENVELOPE}
    assert set(over) == {"M15"}
    assert MEASURED_CONFIRMED["M15"] == HOST_ENVELOPE - 1
    for timeframe, confirmed in MEASURED_CONFIRMED.items():
        if timeframe != "M15":
            assert confirmed == REQUEST_ENVELOPE - 1, (timeframe, confirmed)


def test_every_context_still_meets_the_semantic_minimum() -> None:
    """The asymmetry is acceptable precisely because the contract is a floor."""
    for timeframe, confirmed in MEASURED_CONFIRMED.items():
        assert confirmed >= 1250, (timeframe, confirmed)


# ---------------------------------------------------------------------------
# How big the margin is -- measured, not assumed
# ---------------------------------------------------------------------------


def test_the_atr_series_differs_under_truncation() -> None:
    """The mechanism: a shorter history restarts the Wilder recurrence earlier,
    so every ATR value downstream is a different number."""
    candles = STREAMS.stream(Timeframe.M15, bars=420)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    full = compute_atr_series(candles, mcfg.atr_period)
    short = compute_atr_series(candles[120:], mcfg.atr_period)
    assert list(full)[-1] != list(short)[-1]


def test_mild_truncation_can_be_invisible_which_is_why_the_rule_is_exactness() -> None:
    """MEASURED, and the reason the capture rule is stated as "exactly what the
    context consumed" rather than "enough bars".

    Dropping 120 warm-up bars changes every ATR value (test above) and yet
    leaves this stream's projection bit-identical: the Wilder recurrence has long
    since converged past the tolerance that would flip a swing. So a capture that
    fed the oracle a merely PLAUSIBLE slice could agree with Pine for reasons
    that have nothing to do with the port being correct -- and would keep
    agreeing right up until a borderline tolerance case made it disagree.

    This test pins the observation, not a guarantee. It says the safety margin is
    real but unquantified, which is exactly why the capture must reproduce the
    context's own history rather than approximate it.
    """
    candles = STREAMS.stream(Timeframe.M15, bars=420)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    full = ORACLE.project_terminal(
        candles, compute_atr_series(candles, mcfg.atr_period), len(candles) - 1
    )
    short = candles[120:]
    truncated = ORACLE.project_terminal(
        short, compute_atr_series(short, mcfg.atr_period), len(short) - 1
    )
    assert full.compare_values() == truncated.compare_values()


def test_truncating_into_the_analytical_window_does_change_the_projection() -> None:
    """The comparison is not blunt: once truncation reaches the 300-bar window
    itself, the projection moves. So the oracle IS sensitive to its input; the
    previous test measures the size of the margin, not an absence of sensitivity.
    """
    candles = STREAMS.stream(Timeframe.M15, bars=420)
    mcfg = MarketMeasurementConfiguration(minimum_price_tick=ORACLE.MINTICK)
    full = ORACLE.project_terminal(
        candles, compute_atr_series(candles, mcfg.atr_period), len(candles) - 1
    )
    inside = candles[-200:]
    cut = ORACLE.project_terminal(
        inside, compute_atr_series(inside, mcfg.atr_period), len(inside) - 1
    )
    assert full.compare_values() != cut.compare_values()


# ---------------------------------------------------------------------------
# The capture rule, stated as data the capture tooling can read
# ---------------------------------------------------------------------------


def required_input_bars(timeframe: str) -> int:
    """Confirmed bars the capture must export for this timeframe."""
    return MEASURED_CONFIRMED[timeframe]


def test_the_capture_rule_names_every_authority_timeframe() -> None:
    assert set(MEASURED_CONFIRMED) == {"W1", "D1", "H4", "H1", "M15", "M5"}
    assert required_input_bars("M15") == 1799
    assert required_input_bars("W1") == 1250
