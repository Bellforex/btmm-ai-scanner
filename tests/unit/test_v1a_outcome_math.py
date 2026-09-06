"""Protocol §17 oracle/mutation/directed tests for the V1-A outcome-measurement
math (``tests/parity_support/v1a_outcome_math.py``).

This module carries the bulk of V1-A's determinism/integrity burden because
it is the cheap, pure, dependency-free half of the harness (no scanner
replay needed) — see that module's own docstring for why.
"""

from __future__ import annotations

import random
from decimal import Decimal

import pytest

from tests.parity_support.v1a_outcome_math import (
    ATR_THRESHOLDS,
    HORIZONS,
    ForwardBar,
    adverse_extreme,
    compute_directional_returns,
    compute_mae,
    compute_mfe,
    compute_path_ordering,
    compute_poi_touch_outcome,
    compute_threshold_reach_grid,
    directional_return,
    directional_return_pct,
    favorable_extreme,
)

D = Decimal


def _bar(high: str, low: str, close: str) -> ForwardBar:
    return ForwardBar(high=D(high), low=D(low), close=D(close))


# ---------------------------------------------------------------------------
# Directed tests: directional return
# ---------------------------------------------------------------------------


def test_directional_return_bullish_positive_move() -> None:
    assert directional_return(D("100"), D("105"), bullish=True) == D("5")


def test_directional_return_bullish_negative_move() -> None:
    assert directional_return(D("100"), D("95"), bullish=True) == D("-5")


def test_directional_return_bearish_positive_move() -> None:
    # Price falling is a WIN for a bearish event -> positive directional return.
    assert directional_return(D("100"), D("95"), bullish=False) == D("5")


def test_directional_return_bearish_negative_move() -> None:
    assert directional_return(D("100"), D("105"), bullish=False) == D("-5")


def test_directional_return_pct() -> None:
    assert directional_return_pct(D("100"), D("110"), bullish=True) == D("10")


# ---------------------------------------------------------------------------
# Directed tests: favorable/adverse extreme selection
# ---------------------------------------------------------------------------


def test_favorable_extreme_bullish_is_high() -> None:
    bar = _bar("110", "90", "100")
    assert favorable_extreme(bar, True) == D("110")
    assert adverse_extreme(bar, True) == D("90")


def test_favorable_extreme_bearish_is_low() -> None:
    bar = _bar("110", "90", "100")
    assert favorable_extreme(bar, False) == D("90")
    assert adverse_extreme(bar, False) == D("110")


# ---------------------------------------------------------------------------
# Directed tests: MFE / MAE, bullish and bearish
# ---------------------------------------------------------------------------


def test_mfe_bullish_tracks_running_max_high() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100.5"), _bar("103", "100", "102"), _bar("102", "101", "101.5"))
    result = compute_mfe(reference, bars, bullish=True, atr_at_event=None, horizons=(1, 2, 3))
    assert result[0].value == D("1")  # bar1 high 101 - 100
    assert result[1].value == D("3")  # bar2 high 103 - 100 (new max)
    assert result[2].value == D("3")  # bar3 high 102 doesn't beat 103


def test_mae_bullish_tracks_running_min_low() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100.5"), _bar("103", "97", "102"), _bar("102", "98", "101.5"))
    result = compute_mae(reference, bars, bullish=True, atr_at_event=None, horizons=(1, 2, 3))
    assert result[0].value == D("1")  # 100 - 99
    assert result[1].value == D("3")  # 100 - 97 (new worst)
    assert result[2].value == D("3")  # 98 doesn't beat 97


def test_mfe_bearish_tracks_running_min_low() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "99.5"), _bar("102", "97", "98"), _bar("100", "98", "99"))
    result = compute_mfe(reference, bars, bullish=False, atr_at_event=None, horizons=(1, 2, 3))
    assert result[0].value == D("1")  # 100 - 99
    assert result[1].value == D("3")  # 100 - 97 (best for bearish)
    assert result[2].value == D("3")


def test_mae_bearish_tracks_running_max_high() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "99.5"), _bar("104", "97", "98"), _bar("102", "98", "99"))
    result = compute_mae(reference, bars, bullish=False, atr_at_event=None, horizons=(1, 2, 3))
    assert result[0].value == D("1")  # 101 - 100
    assert result[1].value == D("4")  # 104 - 100 (worst for bearish)
    assert result[2].value == D("4")


# ---------------------------------------------------------------------------
# Fixed horizons / partial / censored horizon
# ---------------------------------------------------------------------------


def test_all_frozen_horizons_present_in_output() -> None:
    reference = D("100")
    bars = tuple(_bar("101", "99", "100") for _ in range(48))
    result = compute_directional_returns(reference, bars, bullish=True)
    assert tuple(r.horizon for r in result) == HORIZONS


def test_partial_horizon_is_censored_not_truncated() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100.5"), _bar("102", "100", "101"))  # only 2 bars available
    result = compute_directional_returns(reference, bars, bullish=True, horizons=(1, 2, 3, 4))
    assert result[0].censored is False
    assert result[1].censored is False
    assert result[2].censored is True
    assert result[3].censored is True
    # a censored cell must carry a neutral zero, never a fabricated/truncated value
    assert result[2].directional_return == D("0")


def test_complete_horizon_never_marked_censored() -> None:
    reference = D("100")
    bars = tuple(_bar("101", "99", "100") for _ in range(4))
    result = compute_directional_returns(reference, bars, bullish=True, horizons=(1, 2, 3, 4))
    assert all(r.censored is False for r in result)


def test_mfe_mae_censored_when_horizon_exceeds_available_bars() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100"),)
    mfe = compute_mfe(reference, bars, bullish=True, atr_at_event=D("1"), horizons=(1, 2))
    assert mfe[0].censored is False
    assert mfe[1].censored is True
    assert mfe[1].value == D("0")
    assert mfe[1].atr_units is None


# ---------------------------------------------------------------------------
# ATR normalization
# ---------------------------------------------------------------------------


def test_mfe_atr_normalized_divides_by_event_atr() -> None:
    reference = D("100")
    bars = (_bar("102", "99", "101"),)
    result = compute_mfe(reference, bars, bullish=True, atr_at_event=D("2"), horizons=(1,))
    assert result[0].value == D("2")
    assert result[0].atr_units == D("1")


def test_mfe_atr_units_none_when_atr_unavailable() -> None:
    reference = D("100")
    bars = (_bar("102", "99", "101"),)
    result = compute_mfe(reference, bars, bullish=True, atr_at_event=None, horizons=(1,))
    assert result[0].atr_units is None
    assert result[0].value == D("2")  # raw value still computed


# ---------------------------------------------------------------------------
# Threshold reach + path ordering
# ---------------------------------------------------------------------------


def test_threshold_reach_exact_bar_offset() -> None:
    reference = D("100")
    atr = D("1")
    # favorable excursion reaches 1.0 ATR (=1.00 price unit) at bar 3.
    bars = (
        _bar("100.5", "99.5", "100"),
        _bar("100.8", "99.5", "100"),
        _bar("101.0", "99.5", "100"),
        _bar("101.0", "99.5", "100"),
    )
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=atr)
    cell = next(c for c in grid.favorable if c.threshold_atr == D("1.00"))
    assert cell.bar_offset == 3
    cell_never = next(c for c in grid.favorable if c.threshold_atr == D("3.00"))
    assert cell_never.bar_offset is None


def test_threshold_reach_censored_when_atr_unavailable() -> None:
    reference = D("100")
    bars = (_bar("110", "99", "100"),)
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=None)
    assert grid.atr_unavailable is True
    assert all(c.bar_offset is None for c in grid.favorable)
    assert all(c.bar_offset is None for c in grid.adverse)


def test_path_ordering_favorable_first() -> None:
    reference = D("100")
    atr = D("1")
    bars = (
        _bar("101.0", "99.9", "100"),  # favorable 1.0 ATR reached bar 1
        _bar("100.5", "98.9", "100"),  # adverse 1.0 ATR reached bar 2
    )
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=atr)
    ordering = compute_path_ordering(grid)
    assert ordering[D("1.00")] == "favorable_first"


def test_path_ordering_adverse_first() -> None:
    reference = D("100")
    atr = D("1")
    bars = (
        _bar("100.5", "98.9", "100"),  # adverse 1.0 ATR reached bar 1
        _bar("101.5", "99.9", "100"),  # favorable 1.0 ATR reached bar 2
    )
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=atr)
    ordering = compute_path_ordering(grid)
    assert ordering[D("1.00")] == "adverse_first"


def test_path_ordering_neither_when_threshold_never_reached() -> None:
    reference = D("100")
    atr = D("10")
    bars = (_bar("100.1", "99.9", "100"),)
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=atr)
    ordering = compute_path_ordering(grid)
    assert ordering[D("1.00")] == "neither"


def test_path_ordering_tie_same_bar() -> None:
    reference = D("100")
    atr = D("1")
    # A single bar whose high and low both cross the 1.0 ATR line the same bar.
    bars = (_bar("101.5", "98.5", "100"),)
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=atr)
    ordering = compute_path_ordering(grid)
    assert ordering[D("1.00")] == "tie"


def test_threshold_grid_covers_frozen_atr_grid() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100"),)
    grid = compute_threshold_reach_grid(reference, bars, bullish=True, atr_at_event=D("1"))
    assert tuple(c.threshold_atr for c in grid.favorable) == ATR_THRESHOLDS
    assert tuple(c.threshold_atr for c in grid.adverse) == ATR_THRESHOLDS


# ---------------------------------------------------------------------------
# POI touch geometry
# ---------------------------------------------------------------------------


def test_poi_touch_detected_and_first_touch_offset() -> None:
    zone_top, zone_bottom = D("105"), D("100")
    bars = (
        _bar("99", "97", "98"),  # no touch (fully below the zone: high 99 < zone_bottom 100)
        _bar("106", "104", "105"),  # touch (high 106 >= 100, low 104 <= 105)
        _bar("108", "107", "107.5"),
    )
    outcome = compute_poi_touch_outcome(
        zone_top, zone_bottom, bullish=True, forward_bars=bars, atr_lookup=(D("1"), D("1"), D("1"))
    )
    assert outcome.touched is True
    assert outcome.first_touch_offset == 2


def test_poi_never_touched_is_censored_not_defaulted() -> None:
    zone_top, zone_bottom = D("200"), D("195")
    bars = (_bar("103", "101", "102"),)
    outcome = compute_poi_touch_outcome(
        zone_top, zone_bottom, bullish=True, forward_bars=bars, atr_lookup=(D("1"),)
    )
    assert outcome.touched is False
    assert outcome.first_touch_offset is None
    assert outcome.max_penetration_price is None


def test_poi_no_forward_data_is_censored() -> None:
    outcome = compute_poi_touch_outcome(
        D("105"), D("100"), bullish=True, forward_bars=(), atr_lookup=()
    )
    assert outcome.censored_no_forward_data is True
    assert outcome.touched is False


def test_poi_far_boundary_crossed_bullish() -> None:
    # bullish POI: near boundary = zone_top, far boundary = zone_bottom.
    zone_top, zone_bottom = D("105"), D("100")
    bars = (_bar("106", "99", "100"),)  # low 99 <= far boundary 100 -> crossed
    outcome = compute_poi_touch_outcome(
        zone_top, zone_bottom, bullish=True, forward_bars=bars, atr_lookup=(D("1"),)
    )
    assert outcome.far_boundary_crossed is True


def test_poi_penetration_depth_atr_normalized() -> None:
    zone_top, zone_bottom = D("105"), D("100")
    bars = (_bar("106", "103", "104"),)  # penetrates 2 units past zone_top (105 - 103)
    outcome = compute_poi_touch_outcome(
        zone_top, zone_bottom, bullish=True, forward_bars=bars, atr_lookup=(D("2"),)
    )
    assert outcome.max_penetration_price == D("2")
    assert outcome.max_penetration_atr == D("1")


# ---------------------------------------------------------------------------
# Mutation tests (protocol §17): each proves the REAL function's output
# differs from a deliberately-broken variant on the same scenario, so a
# regression to that bug would be caught by comparing against a fixed oracle
# value, not silently accepted.
# ---------------------------------------------------------------------------


def test_mutation_direction_sign_inversion_is_caught() -> None:
    """Bull/bear sign inversion must change the directional return's sign."""
    reference, close_n = D("100"), D("110")
    correct = directional_return(reference, close_n, bullish=True)
    mutated = directional_return(reference, close_n, bullish=False)  # injected bug
    assert correct == D("10")
    assert mutated == D("-10")
    assert correct != mutated


def test_mutation_mfe_mae_swapped_is_caught() -> None:
    """Swapping MFE<->MAE on an asymmetric bar sequence must be detectable."""
    reference = D("100")
    bars = (_bar("110", "95", "105"),)  # favorable=10, adverse=5 for a bullish event
    mfe = compute_mfe(reference, bars, bullish=True, atr_at_event=None, horizons=(1,))[0]
    mae = compute_mae(reference, bars, bullish=True, atr_at_event=None, horizons=(1,))[0]
    assert mfe.value == D("10")
    assert mae.value == D("5")
    assert mfe.value != mae.value  # a swap bug (mfe==mae value) would be caught here


def test_mutation_horizon_off_by_one_event_bar_included() -> None:
    """A bug that wrongly includes the EVENT bar itself in the horizon-1
    window (instead of the first bar AFTER it) must change the result on a
    sequence where the event bar's own high/low differ from bar 1's."""
    reference = D("100")
    event_bar = _bar("150", "50", "100")  # deliberately extreme, must NEVER be read
    forward_bars_correct = (_bar("101", "99", "100.5"),)
    correct = compute_mfe(reference, forward_bars_correct, bullish=True, atr_at_event=None, horizons=(1,))[0]
    # Simulated bug: horizon window built with the event bar prepended.
    buggy_window = (event_bar, *forward_bars_correct)
    buggy = compute_mfe(reference, buggy_window, bullish=True, atr_at_event=None, horizons=(1,))[0]
    assert correct.value == D("1")
    assert buggy.value == D("50")
    assert correct.value != buggy.value


def test_mutation_partial_horizon_misreported_as_complete() -> None:
    """A bug that forgets to check ``horizon > len(forward_bars)`` would
    report horizon 4 as complete off a 2-bar window. The real function must
    mark it censored, and the two are trivially distinguishable."""
    reference = D("100")
    bars = (_bar("101", "99", "100.5"), _bar("102", "100", "101"))
    result = compute_directional_returns(reference, bars, bullish=True, horizons=(4,))[0]
    assert result.censored is True
    # A "buggy" computation would have read bars[3] (out of range) or silently
    # clamped to the last available bar -- assert the real function does
    # neither by checking the returned value is the neutral zero, not close[1].
    assert result.directional_return == D("0")
    assert result.directional_return != directional_return(reference, bars[-1].close, bullish=True)


def test_mutation_wrong_confirmed_bar_reference() -> None:
    """Using the WRONG reference price (e.g. the bar's open instead of its
    close, or the next bar's close instead of the event bar's own close)
    must produce a detectably different directional return."""
    event_bar_close = D("100")
    wrong_reference = D("99")  # e.g. accidentally used the prior bar's close
    close_n = D("105")
    correct = directional_return(event_bar_close, close_n, bullish=True)
    mutated = directional_return(wrong_reference, close_n, bullish=True)
    assert correct == D("5")
    assert mutated == D("6")
    assert correct != mutated


def test_mutation_event_timing_one_bar_early() -> None:
    """Evaluating horizon N against forward_bars shifted one bar early
    (i.e. off-by-one on which bar is 'bar 1') must diverge whenever
    consecutive bars differ."""
    reference = D("100")
    bars = (_bar("101", "99", "100.2"), _bar("103", "99", "102.5"), _bar("104", "100", "103.5"))
    correct = compute_directional_returns(reference, bars, bullish=True, horizons=(2,))[0]
    shifted = compute_directional_returns(reference, bars[1:], bullish=True, horizons=(2,))[0]
    assert correct.directional_return != shifted.directional_return


def test_mutation_event_timing_one_bar_late() -> None:
    reference = D("100")
    bars = (_bar("101", "99", "100.2"), _bar("103", "99", "102.5"), _bar("104", "100", "103.5"))
    correct = compute_directional_returns(reference, bars, bullish=True, horizons=(2,))[0]
    late = compute_directional_returns(reference, (bars[0], bars[0], *bars[1:]), bullish=True, horizons=(2,))[0]
    assert correct.directional_return != late.directional_return


# ---------------------------------------------------------------------------
# Randomized synthetic-OHLC oracle tests: known monotonic constructions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("seed", range(60))
def test_oracle_monotonic_bullish_rally_mfe_equals_final_high(seed: int) -> None:
    """A strictly monotonically increasing high sequence: MFE at the final
    horizon must equal exactly (max high - reference), computed independently
    here via plain max(), not via the function under test's own internals."""
    rng = random.Random(seed)
    reference = D("100")
    n = rng.randint(1, 20)
    highs = []
    running = D("100")
    bars = []
    for _ in range(n):
        step = D(rng.randint(1, 50)) / D(100)
        running += step
        highs.append(running)
        bars.append(ForwardBar(high=running, low=running - D("0.01"), close=running - D("0.005")))
    bars_t = tuple(bars)
    expected_mfe = max(highs) - reference
    result = compute_mfe(reference, bars_t, bullish=True, atr_at_event=None, horizons=(n,))[0]
    assert result.value == expected_mfe


@pytest.mark.parametrize("seed", range(60))
def test_oracle_monotonic_bearish_selloff_mfe_equals_final_low(seed: int) -> None:
    rng = random.Random(seed)
    reference = D("100")
    n = rng.randint(1, 20)
    lows = []
    running = D("100")
    bars = []
    for _ in range(n):
        step = D(rng.randint(1, 50)) / D(100)
        running -= step
        lows.append(running)
        bars.append(ForwardBar(high=running + D("0.01"), low=running, close=running + D("0.005")))
    bars_t = tuple(bars)
    expected_mfe = reference - min(lows)
    result = compute_mfe(reference, bars_t, bullish=False, atr_at_event=None, horizons=(n,))[0]
    assert result.value == expected_mfe


@pytest.mark.parametrize("seed", range(120))
def test_oracle_random_bars_mfe_mae_match_naive_scan(seed: int) -> None:
    """Randomized OHLC bars: MFE/MAE at horizon N must equal a naive,
    independently-written running-extreme scan over the same bars."""
    rng = random.Random(seed + 10_000)
    reference = D("100")
    bullish = rng.choice([True, False])
    n = rng.randint(1, 48)
    bars = []
    for _ in range(n):
        base = D(rng.randint(9000, 11000)) / D(100)
        spread = D(rng.randint(1, 300)) / D(100)
        high = base + spread
        low = base - spread
        close = base
        bars.append(ForwardBar(high=high, low=low, close=close))
    bars_t = tuple(bars)

    sign = D(1) if bullish else D(-1)
    naive_mfe = max(
        sign * ((b.high if bullish else b.low) - reference) for b in bars_t[:n]
    )
    naive_mae = max(
        sign * (reference - (b.low if bullish else b.high)) for b in bars_t[:n]
    )

    mfe = compute_mfe(reference, bars_t, bullish=bullish, atr_at_event=None, horizons=(n,))[0]
    mae = compute_mae(reference, bars_t, bullish=bullish, atr_at_event=None, horizons=(n,))[0]
    assert mfe.value == naive_mfe
    assert mae.value == naive_mae


@pytest.mark.parametrize("seed", range(60))
def test_oracle_directional_return_matches_naive_formula(seed: int) -> None:
    rng = random.Random(seed + 20_000)
    reference = D(rng.randint(5000, 15000)) / D(100)
    close_n = D(rng.randint(5000, 15000)) / D(100)
    bullish = rng.choice([True, False])
    naive = (close_n - reference) if bullish else (reference - close_n)
    actual = directional_return(reference, close_n, bullish=bullish)
    assert actual == naive
