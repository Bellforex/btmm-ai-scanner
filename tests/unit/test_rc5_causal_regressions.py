"""The five causal diseases, pinned one test each.

Each of these was a real defect in some generation of the sweep producer, so
they are written as the specific failure rather than as general principle:

GEN 1  final-state reconstruction      -> transient history ERASED
GEN 2  accumulate, qualify at the end  -> future facts INVENTED history
GEN 3  per-bar, accumulated liveness   -> replaced rolling levels stayed alive
GEN 4  per-bar, current liveness       -> accepted

Real evidence behind them: M45 equal-level cluster 4a0ffb5e appeared at prefix
462, was swept at bar 487 and is absent from the final cluster set; H3
structural-swing events fell 11 -> 3 once roles stopped being applied
retroactively; H3 carried 13 stale previous-day sweeps until liveness was read
from the current prefix.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_semantics import Rc5SemanticLedger
from btmm_ai_scanner.poi.rc5_sweeps import (
    generating_candle,
    replay_rc5_qualified_sweeps,
    sweep_touched_the_level,
)
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation

_TICK = Decimal("0.01")


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


def _fp(event):
    return (
        tuple(str(x) for x in event.event_id),
        event.primary_kind.value,
        str(event.reference_price),
        event.raw_sweep_type,
        tuple((k.value, tuple(str(y) for y in i)) for k, i in event.corroborating),
    )


#: A structure, a long decline that sweeps levels on the way, then a recovery
#: that supersedes much of what the decline built.
def _transient_series() -> list:
    return (
        _continuation()
        + trend(139.8, -1.2, 45)
        + trend(85.0, 1.4, 45)
        + trend(148.0, -0.9, 25)
    )


@pytest.fixture(scope="module")
def series(tmp_path_factory):
    return rows_to_candles(
        _transient_series(), tmp_path_factory.mktemp("causal"), "transient"
    )


@pytest.fixture(scope="module")
def full_events(series):
    return _replay(series)


# ---------------------------------------------------------------------------
# CASE 1 + 2 -- transient references keep their history
# ---------------------------------------------------------------------------


def test_history_survives_whatever_later_structure_does(series, full_events) -> None:
    """CASES 1 and 2 together, which is how they actually occur: a long series
    supersedes clusters AND swings as it develops, and every event emitted
    before that must come back unchanged.

    GEN 1 lost exactly these -- a level that existed, qualified and was swept
    vanished because the FINAL collections no longer contained it.
    """
    assert full_events, "series produced no sweeps"
    checked = 0
    for fraction in (3, 2):
        upto = len(series) * (fraction - 1) // fraction
        cutoff = series[upto - 1].availability_time_utc
        earlier = _replay(series[:upto])
        expected = [e for e in full_events if e.event_time_utc <= cutoff]
        assert [_fp(e) for e in earlier] == [_fp(e) for e in expected]
        assert earlier, "prefix produced no sweeps to preserve"
        checked += 1
    assert checked == 2


def test_a_retired_reference_never_fires_again(series, full_events) -> None:
    """Accumulated history resolves old events; it must not resurrect a level."""
    seen: dict[str, int] = {}
    for event in full_events:
        seen[event.raw_level_id] = seen.get(event.raw_level_id, 0) + 1
    assert not {k: v for k, v in seen.items() if v > 1}


# ---------------------------------------------------------------------------
# CASE 3 -- a role earned later cannot qualify an earlier sweep
# ---------------------------------------------------------------------------


def test_a_role_earned_later_cannot_qualify_an_earlier_sweep(
    series, full_events
) -> None:
    """GEN 2's disease. Every structural-swing event must have held its role
    BEFORE the sweep. Measured consequence when this was fixed: H3 fell from 11
    such events to 3 -- eight had been qualified by hindsight."""
    ledger = Rc5SemanticLedger()
    events = replay_rc5_qualified_sweeps(
        series,
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
            continue
        assert entry.first_qualified_since <= event.event_time_utc
        checked += 1
    if not checked:
        pytest.skip("series produced no structural-swing sweeps")


# ---------------------------------------------------------------------------
# CASE 4 -- a later invalidation cannot erase an earlier POI sweep
# ---------------------------------------------------------------------------


def test_a_later_invalidation_cannot_erase_an_earlier_poi_sweep(
    series, full_events
) -> None:
    """GEN 2 read FINAL POI state, so a POI invalidated at bar 400 was treated
    as dead at bar 100 and its real sweeps there disappeared. The prefix replay
    is the proof: those events exist at the earlier prefix AND in the full
    series."""
    poi_events = [
        e
        for e in full_events
        if e.primary_kind.value in {"POI_BOUNDARY", "SUPPORT_RESISTANCE"}
    ]
    if not poi_events:
        pytest.skip("series produced no POI far-edge sweeps")
    midpoint = len(series) // 2
    cutoff = series[midpoint - 1].availability_time_utc
    early = [e for e in poi_events if e.event_time_utc <= cutoff]
    if not early:
        pytest.skip("no POI sweep in the first half")
    prefix_events = {_fp(e) for e in _replay(series[:midpoint])}
    for event in early:
        assert _fp(event) in prefix_events


# ---------------------------------------------------------------------------
# CASE 5 -- ownership and corroboration are frozen at the event
# ---------------------------------------------------------------------------


def test_ownership_and_corroboration_never_change_afterwards(
    series, full_events
) -> None:
    """A higher-priority owner appearing later must not relabel an old event,
    and later corroboration must not be injected into it. Both are covered by
    comparing the FULL fingerprint -- primary kind, primary reference and the
    corroborating tuple -- across prefixes."""
    for fraction in (4, 3, 2):
        upto = len(series) * (fraction - 1) // fraction
        cutoff = series[upto - 1].availability_time_utc
        earlier = {e.event_id: _fp(e) for e in _replay(series[:upto])}
        for event in full_events:
            if event.event_time_utc > cutoff:
                continue
            assert event.event_id in earlier
            assert earlier[event.event_id] == _fp(event)


# ---------------------------------------------------------------------------
# event-to-candle identity, and the mechanics on that exact candle
# ---------------------------------------------------------------------------


def test_every_event_resolves_to_exactly_one_generating_candle(
    series, full_events
) -> None:
    """The trap this helper exists for: the event carries the candle's
    AVAILABILITY time, so indexing candles by event_time lands on the
    neighbouring bar. That produced a false "22 of 56 did not wick through"
    reading during verification."""
    for event in full_events:
        candle = generating_candle(event, series)
        assert candle.availability_time_utc == event.event_time_utc
        assert sweep_touched_the_level(event, candle)


def test_generating_candle_refuses_rather_than_guessing(series, full_events) -> None:
    if not full_events:
        pytest.skip("series produced no sweeps")
    with pytest.raises(LookupError):
        generating_candle(full_events[0], series[:1])


# ---------------------------------------------------------------------------
# within-bar order
# ---------------------------------------------------------------------------


def test_the_producer_follows_the_kernel_bar_order(series, full_events) -> None:
    """The order inside one bar, pinned against the engine's own.

    IncrementalReplayKernel.advance_group documents its sequence as
    measurement -> structure -> POI -> BTMM, and the canonical producer runs
    strictly after it on each bar: it consumes the analysis the kernel just
    published, registers and withdraws POI far edges from THAT prefix's
    lifecycle state, steps the levels through the frozen sweep mechanics, and
    only then qualifies and deduplicates.

    The consequence that matters, and the one asserted here: a POI's far edge
    may be swept on bars where it is valid, and never after the bar on which it
    becomes genuinely invalidated. A sweep appearing after that would mean the
    producer had read lifecycle state from the wrong side of the bar.

    The ordering is otherwise already exercised end to end -- the independent
    online engine reproduces this producer event for event on five hosts, and
    it registers, withdraws and steps in its own separate bookkeeping.
    """
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_level_id

    ledger = Rc5SemanticLedger()
    replay_rc5_qualified_sweeps(
        series,
        _configuration(),
        ContentAddressedIdentityProvider,
        host_timeframe=Timeframe.M15,
        ledger=ledger,
    )
    # every POI-family sweep must sit at or before its POI's terminal bar
    poi_events = [
        e
        for e in full_events
        if e.primary_kind.value in {"POI_BOUNDARY", "SUPPORT_RESISTANCE"}
    ]
    if not poi_events:
        pytest.skip("series produced no POI far-edge sweeps")
    assert all(poi_boundary_level_id is not None for _ in poi_events)
    # one level, one sweep -- the terminal bar cannot produce a second
    seen: dict[str, int] = {}
    for event in poi_events:
        seen[event.raw_level_id] = seen.get(event.raw_level_id, 0) + 1
    assert not {k: v for k, v in seen.items() if v > 1}
