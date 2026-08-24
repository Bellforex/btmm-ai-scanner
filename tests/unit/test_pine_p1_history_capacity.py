"""P1-PERF-4A — the history-capacity product gate.

PERF-4 asked one question — "has this bar warmed up?" — and that is not the same
as "did TradingView give this script the horizon the product was validated on?".
A user who lowers the generated *Calculated bars* input, or a symbol with a
short history, produces a run in which a handful of late bars are genuinely warm
while the validated horizon is absent entirely. Publishing those bars would put
a trading signal on screen from an unvalidated execution history.

So publication now requires BOTH:

    p1CapacityOk = (last_bar_index + 1) >= C_P1_CALC_BARS      # 1800
    p1WarmupOk   = confirmedBarCount    >= C_P1_MIN_CALC_BARS  # 1250
    p1HistoryOk  = p1CapacityOk and p1WarmupOk

The rule is modelled here rather than executed in Pine, and every constant is
read back out of the Pine source so the model cannot drift away from the script
it claims to describe.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_PINE = Path("tradingview/btmm_poi_btrc_scanner_v1.pine")

# The capacities named in the PERF-4A authorization as test points.
_CAPACITY_POINTS = (300, 900, 1200, 1249, 1250, 1350, 1549, 1600, 1799, 1800, 2000)


def _source() -> str:
    return _PINE.read_text(encoding="utf-8")


def _declared(name: str) -> int:
    match = re.search(rf"^int {re.escape(name)}\s*=\s*(\d+)$", _source(), re.MULTILINE)
    assert match is not None, f"{name} is not declared in the Pine source"
    return int(match.group(1))


def _calc_bars_count() -> int:
    match = re.search(r"calc_bars_count\s*=\s*(\d+)", _source())
    assert match is not None, "calc_bars_count is missing from the declaration"
    return int(match.group(1))


CAPACITY_REQUIREMENT = _declared("C_P1_CALC_BARS")
WARMUP_FLOOR = _declared("C_P1_MIN_CALC_BARS")


def publishes(dataset_bars: int, confirmed_bar_count: int) -> bool:
    """The Pine publication gate, modelled exactly."""
    capacity_ok = dataset_bars >= CAPACITY_REQUIREMENT
    warmup_ok = confirmed_bar_count >= WARMUP_FLOOR
    return capacity_ok and warmup_ok


def accessible_bars(chart_bars: int, calculated_bars_setting: int) -> int:
    """What ``last_bar_index + 1`` reports.

    TradingView hands the script whichever is smaller: the bars the chart has,
    or the bars the user asked to calculate.
    """
    return min(chart_bars, calculated_bars_setting)


# ---------------------------------------------------------------------------
# Source agreement — the model is only worth anything if it matches the script.
# ---------------------------------------------------------------------------


def test_pine_and_model_agree_on_the_constants() -> None:
    assert CAPACITY_REQUIREMENT == 1800
    assert WARMUP_FLOOR == 1250
    assert _calc_bars_count() == CAPACITY_REQUIREMENT, (
        "the declared calc_bars_count and the capacity requirement must be the "
        "same number; the product asks TradingView for exactly the horizon it "
        "then insists on having"
    )


def test_capacity_requirement_is_not_the_warmup_floor() -> None:
    """The distinction PERF-4A exists to draw."""
    assert CAPACITY_REQUIREMENT > WARMUP_FLOOR
    assert not publishes(dataset_bars=WARMUP_FLOOR, confirmed_bar_count=WARMUP_FLOOR), (
        "a run only as long as the warm-up floor must not publish: it contains "
        "one nominally warm bar and none of the validated horizon"
    )


# ---------------------------------------------------------------------------
# The authorized capacity test points.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("calculated_bars", _CAPACITY_POINTS)
def test_lowered_calculated_bars_setting(calculated_bars: int) -> None:
    """Below the validated capacity nothing publishes, however warm the bar."""
    dataset = accessible_bars(chart_bars=5000, calculated_bars_setting=calculated_bars)
    best_case = publishes(dataset_bars=dataset, confirmed_bar_count=dataset)
    if calculated_bars < CAPACITY_REQUIREMENT:
        assert not best_case, (
            f"Calculated bars = {calculated_bars} is below the validated "
            f"{CAPACITY_REQUIREMENT}-bar horizon but still published"
        )
    else:
        assert best_case, (
            f"Calculated bars = {calculated_bars} meets the validated horizon "
            "but the final bar was suppressed"
        )


def test_a_warm_bar_inside_an_undersized_run_is_still_suppressed() -> None:
    """The case that motivated PERF-4A.

    At 1300 calculated bars the last fifty bars clear the warm-up floor and are
    individually exact — and the run is still outside the validated contract, so
    none of them may reach the client.
    """
    dataset = accessible_bars(chart_bars=5000, calculated_bars_setting=1300)
    assert dataset > WARMUP_FLOOR, "fixture should contain genuinely warm bars"
    assert not publishes(dataset_bars=dataset, confirmed_bar_count=dataset)


# ---------------------------------------------------------------------------
# Short symbol history — fail closed, by author decision.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("chart_bars", (120, 800, 1249, 1799))
def test_short_symbol_history_fails_closed(chart_bars: int) -> None:
    """No partial answer from a chart that never had the horizon.

    PERF-3 would have computed from whatever existed. That result sits outside
    the validated P1 history contract, so it is withheld.
    """
    dataset = accessible_bars(chart_bars, calculated_bars_setting=CAPACITY_REQUIREMENT)
    for confirmed in range(1, dataset + 1):
        assert not publishes(dataset_bars=dataset, confirmed_bar_count=confirmed)


# ---------------------------------------------------------------------------
# Off-by-one / realtime semantics.
# ---------------------------------------------------------------------------


def test_an_open_realtime_bar_cannot_revoke_capacity() -> None:
    """The off-by-one that would break the default configuration.

    ``last_bar_index + 1`` is ``min(chart bars, setting)``. The setting is fixed
    for the run and the chart only grows, so the accessible count is monotonically
    non-decreasing: an opening realtime bar can never drop a passing run below
    the requirement. That is why no downward tolerance is applied.
    """
    setting = CAPACITY_REQUIREMENT
    previous = 0
    for chart_bars in range(1795, 1810):
        dataset = accessible_bars(chart_bars, setting)
        assert dataset >= previous, "accessible bars went backwards"
        previous = dataset
    # Exactly the horizon, market closed: the last bar is historical.
    assert publishes(dataset_bars=1800, confirmed_bar_count=1800)
    # Same chart with an open realtime bar: 1799 confirmed + 1 forming.
    assert publishes(dataset_bars=1800, confirmed_bar_count=1799)
    # A chart that grew past the cap still reports the cap.
    assert accessible_bars(chart_bars=5000, calculated_bars_setting=1800) == 1800


def test_one_bar_below_the_horizon_is_rejected() -> None:
    """No upward tolerance either — 1799 is not 1800.

    A tolerance here would quietly redefine the product contract, and the
    authorization names 1799 as a rejection point.
    """
    assert not publishes(dataset_bars=1799, confirmed_bar_count=1799)
    assert publishes(dataset_bars=1800, confirmed_bar_count=1800)


# ---------------------------------------------------------------------------
# The published region.
# ---------------------------------------------------------------------------


def test_published_region_is_the_region_the_campaign_proved() -> None:
    """Every bar the gate admits must be a bar the truncation proof covered."""
    published = [
        confirmed
        for confirmed in range(1, CAPACITY_REQUIREMENT + 1)
        if publishes(dataset_bars=CAPACITY_REQUIREMENT, confirmed_bar_count=confirmed)
    ]
    assert len(published) == CAPACITY_REQUIREMENT - WARMUP_FLOOR + 1 == 551
    assert published[0] == WARMUP_FLOOR
    assert published[-1] == CAPACITY_REQUIREMENT


def test_nothing_publishes_before_the_warmup_floor() -> None:
    for confirmed in (1, 300, 1000, WARMUP_FLOOR - 1):
        assert not publishes(
            dataset_bars=CAPACITY_REQUIREMENT, confirmed_bar_count=confirmed
        )
