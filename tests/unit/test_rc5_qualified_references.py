"""RC5 qualified liquidity: which references deserve sweep authority.

THE ARCHITECTURE QUESTION, ANSWERED BY THE EXISTING ENGINE. The hazard is that
write-once qualification lets dead references keep producing sweeps forever.
For every family that flows through ``framework/engine.py::_levels()`` the
framework already prevents it:

* ``_sweep_step`` drops a level closed through and not reclaimed within
  ``sweep_reclaim_bars`` -- consumed, no event;
* a level that DOES fire a sweep is not appended to the survivors either, so
  each level fires at most ONE sweep and then retires;
* both range registration sites guard on a seen-key set, so a consumed range
  boundary is never re-registered.

So a raw ``SweepEvent`` existing at all proves its level was live on that bar,
and RC5 only has to answer the HISTORICAL question. Adding a second activity
test would duplicate the framework's lifecycle and risk disagreeing with it.
These tests pin that reading of the engine, because the whole design rests on
it. POI far edges are the exception and carry their own activity rule.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.framework.engine import framework_context_for
from btmm_ai_scanner.framework.model import LiquiditySide, SweepType
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.rc5_host_identity import host_identity_of
from btmm_ai_scanner.poi.rc5_liquidity import (
    RejectionReason,
    SweepReferenceKind,
    qualify_sweep_reference,
    reference_kind_of_level_id,
)
from btmm_ai_scanner.poi.rc5_semantics import Rc5SemanticLedger
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import mirror, rows_to_candles, trend
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")
_HOST = host_identity_of(Timeframe.M15)

_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "collapse": lambda: _continuation() + trend(139.8, -1.2, 40),
    "collapse_mirror": lambda: mirror(_continuation() + trend(139.8, -1.2, 40)),
}


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def replayed(request: pytest.FixtureRequest, tmp_path: Path):
    candles = rows_to_candles(_SERIES[request.param](), tmp_path, request.param)
    base = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=True
            )
        }
    )
    ledger = Rc5SemanticLedger()
    analysis = scan_market(
        (ScannerTimeframeInput(Timeframe.M15, candles),),
        (),
        configuration,
        ContentAddressedIdentityProvider(),
        ledger,
    )
    measurement = next(
        m for m in analysis.measurement_analyses if m.timeframe is Timeframe.M15
    )
    context = framework_context_for(analysis, Timeframe.M15, candles, None)
    return context, ledger, measurement


def _qualify(context, ledger, measurement):
    swings_by_id = {str(s.record_id): s for s in measurement.confirmed_swings}
    trendlines_by_id = {str(t.record_id): t for t in measurement.trendlines}
    return [
        (
            event,
            qualify_sweep_reference(
                event,
                ledger,
                _HOST,
                swings_by_id=swings_by_id,
                trendlines_by_id=trendlines_by_id,
            ),
        )
        for event in context.events
    ]


# ---------------------------------------------------------------------------
# the engine's own lifecycle -- what the design rests on
# ---------------------------------------------------------------------------


def test_a_level_fires_at_most_one_sweep(replayed) -> None:
    """``_sweep_step`` never returns a level that produced an event, so a
    second sweep of the same level_id is impossible. If this ever fails, the
    "existence proves activity" argument collapses and RC5 needs its own
    activity view for these families."""
    context, _, _ = replayed
    seen: dict[str, int] = {}
    for event in context.events:
        seen[event.level_id] = seen.get(event.level_id, 0) + 1
    repeated = {k: v for k, v in seen.items() if v > 1}
    assert not repeated, repeated


def test_every_raw_sweep_maps_to_a_known_reference_kind(replayed) -> None:
    context, _, _ = replayed
    for event in context.events:
        assert isinstance(
            reference_kind_of_level_id(event.level_id), SweepReferenceKind
        )


# ---------------------------------------------------------------------------
# qualification doctrine
# ---------------------------------------------------------------------------


def test_every_refusal_names_a_reason(replayed) -> None:
    """No vague "noise": a rejected raw sweep must say exactly why."""
    for _event, verdict in _qualify(*replayed):
        if not verdict.is_qualified:
            assert verdict.rejected_because in set(RejectionReason)


def test_a_texture_swing_never_qualifies(replayed) -> None:
    """A swing the structure walk never used is internal liquidity."""
    context, ledger, measurement = replayed
    swings_by_id = {str(s.record_id): s for s in measurement.confirmed_swings}
    checked = 0
    for event in context.events:
        if reference_kind_of_level_id(event.level_id) is not (
            SweepReferenceKind.STRUCTURAL_SWING
        ):
            continue
        swing = swings_by_id.get(event.level_id[1:])
        if swing is None or ledger.swing_role(swing.record_id) is not None:
            continue
        verdict = qualify_sweep_reference(
            event, ledger, _HOST, swings_by_id=swings_by_id
        )
        assert not verdict.is_qualified
        assert verdict.rejected_because is RejectionReason.TEXTURE_SWING
        checked += 1
    if not checked:
        pytest.skip("series swept no texture swing")


def test_a_trendline_needs_both_anchors_meaningful(replayed) -> None:
    """Touch count is unusable -- ``qualifying_touch_swing_record_ids`` is
    length 1 for all 437 trendlines measured on M15 and H4 -- so the anchors
    carry the decision."""
    context, ledger, measurement = replayed
    trendlines_by_id = {str(t.record_id): t for t in measurement.trendlines}
    checked = 0
    for event in context.events:
        if reference_kind_of_level_id(event.level_id) is not (
            SweepReferenceKind.TRENDLINE
        ):
            continue
        line = trendlines_by_id[event.level_id[1:]]
        anchors = (line.anchor_1_swing_record_id, line.anchor_2_swing_record_id)
        expected = all(
            (entry := ledger.swing_role(a)) is not None and entry.is_meaningful
            for a in anchors
        )
        verdict = qualify_sweep_reference(
            event, ledger, _HOST, trendlines_by_id=trendlines_by_id
        )
        assert verdict.is_qualified is expected
        checked += 1
    if not checked:
        pytest.skip("series swept no trendline")


def test_equal_pools_and_ranges_qualify_without_a_structural_role(replayed) -> None:
    """A pool of equal highs IS liquidity; it does not have to also be a
    structural origin. Same for a confirmed range boundary."""
    for event, verdict in _qualify(*replayed):
        kind = reference_kind_of_level_id(event.level_id)
        if kind in (
            SweepReferenceKind.EQUAL_HIGH_LOW,
            SweepReferenceKind.RANGE_BOUNDARY,
        ):
            assert verdict.is_qualified


# ---------------------------------------------------------------------------
# side authority
# ---------------------------------------------------------------------------


def test_side_is_taken_from_the_framework_never_re_derived(replayed) -> None:
    """One authority for BSL/SSL. If RC5 computed it independently the two
    layers could disagree about which side was swept."""
    for event, verdict in _qualify(*replayed):
        if verdict.is_qualified:
            assert verdict.reference.side is event.side
            assert verdict.reference.label == (
                "BSL" if event.side is LiquiditySide.BUY_SIDE else "SSL"
            )


def test_qualification_never_invents_a_price(replayed) -> None:
    for event, verdict in _qualify(*replayed):
        if verdict.is_qualified:
            assert verdict.reference.price == event.level_price


def test_reclaim_mechanics_are_untouched(replayed) -> None:
    """RC5 changes WHICH references deserve sweep authority, never HOW a sweep
    is detected. Both frozen sweep types must survive qualification."""
    context, _, _ = replayed
    kinds = {event.sweep_type for event in context.events}
    assert kinds <= {SweepType.WICK_SWEEP, SweepType.CLOSE_THROUGH_RECLAIM}


# ---------------------------------------------------------------------------
# host locality
# ---------------------------------------------------------------------------


def test_references_carry_the_semantic_host(replayed) -> None:
    for _event, verdict in _qualify(*replayed):
        if verdict.is_qualified:
            assert verdict.reference.host.label == "M15"
            assert "M15" in verdict.reference.key


# ---------------------------------------------------------------------------
# POI far edges -- the only family with an RC5-owned activity rule
# ---------------------------------------------------------------------------


class _Obs:
    """Only what the boundary code reads."""

    def __init__(self, direction, top, bottom, available, tag="a") -> None:
        from btmm_ai_scanner.poi.enums import PoiType

        self.poi_type = PoiType.BUY_ORDER_BLOCK
        self.source_candle_record_ids = (tag,)
        self.record_id = tag
        self.direction = direction
        self.zone_top = top
        self.zone_bottom = bottom
        self.availability_time_utc = available


class _St:
    def __init__(self, status, reason=None) -> None:
        self.poi_lifecycle_status = status
        self.terminal_reason = reason


def _bull_obs(candles, tag="a"):
    from btmm_ai_scanner.poi.enums import PoiDirection

    return _Obs(
        PoiDirection.BULLISH,
        Decimal("102.00"),
        Decimal("100.00"),
        candles[0].availability_time_utc,
        tag,
    )


def _series(rows, tmp_path, name):
    return rows_to_candles(rows, tmp_path, name)


_DIP_AND_RECOVER = [
    (105.0, 105.5, 104.5, 105.0),
    (105.0, 105.2, 100.5, 100.8),  # into the zone, holds above the far edge
    (100.8, 104.0, 100.7, 103.5),
    (103.5, 106.0, 103.2, 105.5),
    (105.5, 105.7, 99.50, 100.90),  # wick BELOW the far edge, closes back in
    (100.9, 104.0, 100.8, 103.6),
]


def test_a_valid_poi_far_edge_can_be_swept(tmp_path: Path) -> None:
    from btmm_ai_scanner.framework.model import FrameworkConfiguration
    from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_sweeps

    candles = _series(_DIP_AND_RECOVER, tmp_path, "dip")
    observation = _bull_obs(candles)
    events = poi_boundary_sweeps(
        candles,
        [observation],
        {observation.record_id: _St(PoiLifecycleStatus.NO_BREACH)},
        Rc5SemanticLedger(),
        FrameworkConfiguration(minimum_price_tick=_TICK),
    )
    assert events, "a live POI far edge produced no sweep"
    assert all(e.side is LiquiditySide.SELL_SIDE for e in events)
    assert all(e.level_id.startswith("P") for e in events)
    assert all(
        reference_kind_of_level_id(e.level_id) is SweepReferenceKind.POI_BOUNDARY
        for e in events
    )


def test_an_invalidated_poi_far_edge_cannot_be_swept(tmp_path: Path) -> None:
    """THE NEGATIVE CONTROL.

    The same price action, the same reference, the same mechanics -- but the
    POI is genuinely invalidated. Its history is untouched; it simply stops
    holding liquidity, so it must not produce a sweep. Without this, a
    write-once qualification would let dead zones keep generating events
    forever, which is the stale-zone problem in liquidity form.
    """
    from btmm_ai_scanner.framework.model import FrameworkConfiguration
    from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_sweeps

    candles = _series(_DIP_AND_RECOVER, tmp_path, "dip-dead")
    observation = _bull_obs(candles)
    dead = _St(PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED)
    events = poi_boundary_sweeps(
        candles,
        [observation],
        {observation.record_id: dead},
        Rc5SemanticLedger(),
        FrameworkConfiguration(minimum_price_tick=_TICK),
    )
    assert events == ()


def test_a_mitigated_poi_far_edge_still_holds_liquidity(tmp_path: Path) -> None:
    """MITIGATION IS NOT TERMINATION. The frozen lifecycle sets
    terminal_reason=MITIGATED on the FIRST TOUCH, so keying off it would
    retire the zone the moment price used it."""
    from btmm_ai_scanner.framework.model import FrameworkConfiguration
    from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiTerminalReason
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_sweeps

    candles = _series(_DIP_AND_RECOVER, tmp_path, "dip-mit")
    observation = _bull_obs(candles)
    used = _St(PoiLifecycleStatus.NO_BREACH, PoiTerminalReason.MITIGATED)
    events = poi_boundary_sweeps(
        candles,
        [observation],
        {observation.record_id: used},
        Rc5SemanticLedger(),
        FrameworkConfiguration(minimum_price_tick=_TICK),
    )
    assert events, "a mitigated but valid POI stopped holding liquidity"


def test_a_suppressed_poi_has_no_independent_far_edge(tmp_path: Path) -> None:
    """A same-origin subordinate is not an independent opportunity, so it must
    not contribute a second reference to the same physical level."""
    from btmm_ai_scanner.framework.model import FrameworkConfiguration
    from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_sweeps
    from btmm_ai_scanner.poi.rc5_semantics import stable_poi_key

    candles = _series(_DIP_AND_RECOVER, tmp_path, "dip-sup")
    observation = _bull_obs(candles)

    class _Suppressed:
        is_suppressed = True

    ledger = Rc5SemanticLedger()
    key = stable_poi_key(observation)
    ledger.get = lambda k: _Suppressed() if k == key else None  # type: ignore[method-assign]

    events = poi_boundary_sweeps(
        candles,
        [observation],
        {observation.record_id: _St(PoiLifecycleStatus.NO_BREACH)},
        ledger,
        FrameworkConfiguration(minimum_price_tick=_TICK),
    )
    assert events == ()
