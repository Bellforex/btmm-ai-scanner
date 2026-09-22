"""RC5 qualified sweeps are CAUSAL HISTORY, not a final-state reconstruction.

The batch framework route builds liquidity levels from the FINAL swing /
cluster / trendline collections, so a level that existed, qualified and was
swept before being superseded simply vanishes from it. Measured on M45:
equal-level cluster 4a0ffb5e appeared at prefix 462, was swept at bar 487, and
is absent from the final cluster set; raw framework sweeps were 102 batch vs
123 incremental.

``replay_rc5_qualified_sweeps`` is therefore the one producer, and everything
it decides is decided AT THE BAR IT HAPPENS. These tests pin the three ways a
whole-series pass gets that wrong, each of which this code did at some point:

* qualifying a sweep using a structural role the swing only earned LATER;
* judging a POI far edge by its FINAL lifecycle state, so a POI invalidated at
  bar 400 was treated as dead at bar 100 too;
* merging or relabelling a historical event because a semantic link appeared
  afterwards.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_semantics import Rc5SemanticLedger
from btmm_ai_scanner.poi.rc5_sweeps import replay_rc5_qualified_sweeps
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")

_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "collapse": lambda: _continuation() + trend(139.8, -1.2, 40),
    "collapse_mirror": lambda: mirror(_continuation() + trend(139.8, -1.2, 40)),
}


def _configuration():
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    return base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=True
            )
        }
    )


def _replay(candles):
    return replay_rc5_qualified_sweeps(
        candles,
        _configuration(),
        ContentAddressedIdentityProvider,
        host_timeframe=Timeframe.M15,
        ledger=Rc5SemanticLedger(),
    )


def _fingerprint(event):
    return (
        tuple(str(p) for p in event.event_id),
        event.event_time_utc.isoformat(),
        event.side.value,
        event.primary_kind.value,
        tuple(str(p) for p in event.primary_reference_id),
        str(event.reference_price),
        event.raw_sweep_type,
        event.raw_level_id,
        tuple((k.value, tuple(str(x) for x in i)) for k, i in event.corroborating),
    )


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def candles(request: pytest.FixtureRequest, tmp_path: Path):
    return rows_to_candles(_SERIES[request.param](), tmp_path, request.param)


# ---------------------------------------------------------------------------
# determinism
# ---------------------------------------------------------------------------


def test_repeated_replay_is_identical(candles) -> None:
    """No state leaks between runs -- fresh kernel, fresh tracker, fresh
    ledger every time."""
    first, second = _replay(candles), _replay(candles)
    assert [_fingerprint(e) for e in first] == [_fingerprint(e) for e in second]


def test_event_ids_are_unique_and_host_local(candles) -> None:
    events = _replay(candles)
    if not events:
        pytest.skip("series produced no qualified sweeps")
    assert len({e.event_id for e in events}) == len(events)
    for event in events:
        assert event.host.label == "M15"
        assert "M15" in event.event_id


# ---------------------------------------------------------------------------
# prefix stability -- the primary correctness proof
# ---------------------------------------------------------------------------


def test_history_never_moves_as_the_series_grows(candles) -> None:
    """Replay to a prefix, then to the full series: every event that had
    already happened must come back byte-identical, including corroboration.

    This is what makes the output HISTORY. If a later bar could change an
    earlier event, the whole causal argument collapses.
    """
    full = _replay(candles)
    if not full:
        pytest.skip("series produced no qualified sweeps")
    checked = 0
    for fraction in (2, 3, 4):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        cutoff = candles[upto - 1].availability_time_utc
        prefix_events = _replay(candles[:upto])
        expected = [e for e in full if e.event_time_utc <= cutoff]
        assert [_fingerprint(e) for e in prefix_events] == [
            _fingerprint(e) for e in expected
        ], f"history moved at prefix {upto}"
        checked += 1
    assert checked, "no usable prefix"


def test_a_prefix_never_sees_a_future_event(candles) -> None:
    for fraction in (2, 3):
        upto = len(candles) * (fraction - 1) // fraction
        if upto < 30:
            continue
        cutoff = candles[upto - 1].availability_time_utc
        for event in _replay(candles[:upto]):
            assert event.event_time_utc <= cutoff


# ---------------------------------------------------------------------------
# no future leakage in the qualification itself
# ---------------------------------------------------------------------------


def test_a_structural_role_is_never_used_before_it_existed(candles) -> None:
    """A swing that only becomes a leg origin LATER must not retroactively
    qualify a sweep that happened before. Measured consequence on H3:
    structural-swing events fell from 11 to 3 once qualification became
    per-prefix -- the other 8 were qualified by roles discovered after the
    sweep."""
    ledger = Rc5SemanticLedger()
    events = replay_rc5_qualified_sweeps(
        candles,
        _configuration(),
        ContentAddressedIdentityProvider,
        host_timeframe=Timeframe.M15,
        ledger=ledger,
    )
    checked = 0
    for event in events:
        if event.primary_kind.value != "STRUCTURAL_SWING":
            continue
        entry = ledger.swing_role(event.primary_reference_id[0])
        if entry is None:
            # resolved through a record that is no longer in the sidecar view
            continue
        assert entry.first_qualified_since <= event.event_time_utc
        checked += 1
    if not checked:
        pytest.skip("series produced no structural-swing sweeps")


def test_every_event_lands_on_a_candle_that_traded_through_it(candles) -> None:
    """The frozen mechanics, verified end to end. A WICK_SWEEP fires on the bar
    that traded through; a CLOSE_THROUGH_RECLAIM fires on the reclaim bar, and
    both must be real. Note the event carries the candle's AVAILABILITY time --
    keying on event_time instead compares the neighbouring bar and invents
    failures."""
    by_availability = {c.availability_time_utc: c for c in candles}
    events = _replay(candles)
    if not events:
        pytest.skip("series produced no qualified sweeps")
    for event in events:
        candle = by_availability.get(event.event_time_utc)
        assert candle is not None
        if event.side.value == "BUY_SIDE":
            assert candle.high > event.reference_price
        else:
            assert candle.low < event.reference_price


# ---------------------------------------------------------------------------
# historical records resolve, but dead references do not resurrect
# ---------------------------------------------------------------------------


def test_a_level_never_fires_twice(candles) -> None:
    """The framework retires a level when it is swept or accepted through, and
    accumulating historical records for RESOLUTION must not re-register one."""
    seen: dict[str, int] = {}
    for event in _replay(candles):
        seen[event.raw_level_id] = seen.get(event.raw_level_id, 0) + 1
    assert not {k: v for k, v in seen.items() if v > 1}
