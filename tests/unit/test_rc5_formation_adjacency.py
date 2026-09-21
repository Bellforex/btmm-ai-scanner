"""RC5 formation adjacency: a B2S/S2B is matched to structure across its own
formation span, not by its source candle alone.

Author decision, 2026-09-21. A BUY-TO-SELL candle *is* the last up-candle
before the turn, so the swing high that completes the reversal forms on a later
bar of the formation. Matching by source candle alone can therefore never
qualify this family -- it refused the author's M45 fixture (2026-09-04 07:00,
zone 4461.42-4486.42), whose swing high sits on the very next bar at 4490.85.

The span is the detector's **own** confirmation window: the source candle
through the candle that confirmed the reversal, inclusive. It is bounded by the
formation's geometry, so it introduces no distance, tolerance, bar count,
nearest-swing search or forward test. Every other family records no span and is
therefore untouched.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.leg_origin import (
    StructuralContext,
    StructuralRoleFact,
    structural_role_of,
)
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.structural_role import StructuralRole
from tests.parity_support.ob_origin_series import mirror, rows_to_candles
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_TICK = Decimal("0.01")
_CONFIG = PoiConfiguration(minimum_price_tick=_TICK)
_RC5 = PoiConfiguration(minimum_price_tick=_TICK, rc5_structural_origin=True)
_MEASUREMENT = MarketMeasurementConfiguration(minimum_price_tick=_TICK)

_SERIES = {
    "continuation": _continuation,
    "continuation_sell": lambda: mirror(_continuation()),
    "reversal": _reversal,
    "reversal_sell": lambda: mirror(_reversal()),
}


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def candles(request: pytest.FixtureRequest, tmp_path: Path):
    return rows_to_candles(_SERIES[request.param](), tmp_path, request.param)


# ---------------------------------------------------------------------------
# the span is the detector's own confirmation window
# ---------------------------------------------------------------------------


def test_the_span_starts_at_the_source_candle_and_is_contiguous(candles) -> None:
    order = {c.record_id: i for i, c in enumerate(candles)}
    found = False
    for candidate in detect_reversal_candles(candles, _CONFIG):
        span = [order[c] for c in candidate.formation_span_candle_record_ids]
        assert span, "a reversal candle must record its formation span"
        found = True
        # starts at its own source candle
        assert span[0] == order[candidate.source_candle_record_ids[0]]
        # contiguous bars, no gaps
        assert span == list(range(span[0], span[0] + len(span)))
    if not found:
        pytest.skip("series produces no reversal candles")


def test_the_span_never_outruns_the_detectors_confirmation_window(candles) -> None:
    """Bounded by formation geometry: source + at most the 3-bar confirmation
    probe. This is what keeps adjacency from becoming a +/-N bar search."""
    for candidate in detect_reversal_candles(candles, _CONFIG):
        assert 1 <= len(candidate.formation_span_candle_record_ids) <= 4


def test_the_span_ends_on_the_candle_that_confirmed_the_reversal(candles) -> None:
    by_id = {c.record_id: c for c in candles}
    for candidate in detect_reversal_candles(candles, _CONFIG):
        last = by_id[candidate.formation_span_candle_record_ids[-1]]
        assert last.availability_time_utc == candidate.availability_time_utc


# ---------------------------------------------------------------------------
# negative controls: nothing else may move
# ---------------------------------------------------------------------------


def test_only_reversal_candles_record_a_span(candles) -> None:
    """Single-candle and two-candle families have no confirmation window, so
    they record no span and adjacency cannot reach past them. This is what
    keeps the H3 pressure-wick staircase out of it."""
    for detector in (
        detect_pressure_wicks,
        detect_engulfing,
        detect_single_candle_reversals,
    ):
        for candidate in detector(candles, _CONFIG):
            assert not getattr(candidate, "formation_span_candle_record_ids", ())


def test_the_span_never_touches_source_time_geometry_or_identity(candles) -> None:
    for candidate in detect_reversal_candles(candles, _CONFIG):
        source = candidate.source_candle_record_ids
        assert len(source) == 1
        # the span is provenance only; the formation itself is unchanged
        assert candidate.candidate_event_time_utc is not None
        assert candidate.zone_top >= candidate.zone_bottom
        assert source[0] == candidate.formation_span_candle_record_ids[0]


def test_a_swing_outside_the_span_confers_no_role(candles) -> None:
    """The span is a closed set. A pivot that is not in it -- however near --
    cannot qualify the formation."""
    candidates = detect_reversal_candles(candles, _CONFIG)
    if not candidates:
        pytest.skip("series produces no reversal candles")
    candidate = candidates[0]
    order = {c.record_id: i for i, c in enumerate(candles)}
    span = {order[c] for c in candidate.formation_span_candle_record_ids}
    outside = next(c for i, c in enumerate(candles) if i not in span and i > max(span))
    # a context whose ONLY pivot is a bar outside the span
    context = StructuralContext(
        {},
        {},
        {},
        {outside.record_id: "sw"},
        {outside.record_id: "sw"},
        {},
        frozenset(),
        frozenset(),
        frozenset(),
    )
    assert structural_role_of(candidate, context) is None


# ---------------------------------------------------------------------------
# the families adjacency must not disturb
# ---------------------------------------------------------------------------


def test_non_reversal_families_are_bit_identical_across_the_change(candles) -> None:
    """FVG, bases and structural zones obey their own location rules; the
    adjacency fix must not reach them."""
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(candles, _MEASUREMENT, identity)
    untouched = {
        PoiType.BUY_FAIR_VALUE_GAP,
        PoiType.SELL_FAIR_VALUE_GAP,
        PoiType.BASE_RALLY,
        PoiType.BASE_DROP,
        PoiType.SUPPORT_ZONE,
        PoiType.RESISTANCE_ZONE,
        PoiType.BUY_ORDER_BLOCK,
        PoiType.SELL_ORDER_BLOCK,
    }

    def run(configuration: PoiConfiguration):
        return {
            (o.poi_type, o.source_candle_record_ids): (
                o.zone_top,
                o.zone_bottom,
                o.candidate_event_time_utc,
                o.availability_time_utc,
            )
            for o in analyze_pois(
                (PoiTimeframeInput(Timeframe.M15, candles, measurement),),
                configuration,
                ContentAddressedIdentityProvider(),
            ).poi_observations
            if o.poi_type in untouched
        }

    assert run(_CONFIG) == run(_RC5)


# ---------------------------------------------------------------------------
# the fixture topology, reproduced synthetically
# ---------------------------------------------------------------------------

#: The shape of the author's M45 case: a big up-candle, then the swing high on
#: the NEXT bar, then the bar that closes below the midpoint and confirms the
#: reversal. Crucially the swing high (105.5) is ABOVE the formation's zone
#: top (104.00), exactly as 4490.85 sits above the real fixture's 4486.42 --
#: so no zone-containment or tolerance rule could ever have matched it.
_B2S_ROWS = [
    (100.0, 100.5, 99.5, 100.0),
    (100.0, 100.6, 99.6, 100.1),
    (100.1, 100.7, 99.7, 100.0),
    (100.0, 104.0, 99.8, 103.8),  # 3  the BUY-TO-SELL candle (source)
    (103.8, 105.5, 103.0, 103.2),  # 4  the swing high that completes the turn
    (103.2, 103.5, 101.0, 101.5),  # 5  closes below the midpoint -> confirms
    (101.5, 102.0, 100.5, 101.0),
]


@pytest.fixture
def b2s(tmp_path: Path):
    candles = rows_to_candles(_B2S_ROWS, tmp_path, "b2s_adjacency")
    (candidate,) = detect_reversal_candles(candles, _CONFIG)
    return candles, candidate


def test_the_fixture_topology_is_reproduced(b2s) -> None:
    candles, candidate = b2s
    order = {c.record_id: i for i, c in enumerate(candles)}
    assert candidate.poi_type is PoiType.BUY_TO_SELL_CANDLE
    assert order[candidate.source_candle_record_ids[0]] == 3
    assert [order[c] for c in candidate.formation_span_candle_record_ids] == [3, 4, 5]


def test_the_completing_swing_is_outside_the_zone_so_only_the_span_can_match(
    b2s,
) -> None:
    candles, candidate = b2s
    assert candles[4].high > candidate.zone_top


def test_a_swing_on_the_span_qualifies_the_formation(b2s) -> None:
    """The regression: source-candle matching returns nothing, span matching
    finds the swing that completes the reversal."""
    candles, candidate = b2s
    swing = "completing-swing"
    fact = StructuralRoleFact(
        StructuralRole.PULLBACK_HIGH,
        candles[4].availability_time_utc,
        swing,
        None,
        None,
    )
    context = StructuralContext(
        {},
        {},
        {},
        {candles[4].record_id: swing},
        {},
        {swing: fact},
        frozenset(),
        frozenset(),
        frozenset({swing}),
    )
    resolved = structural_role_of(candidate, context)
    assert resolved is not None
    assert resolved.role is StructuralRole.PULLBACK_HIGH
    assert resolved.origin_swing_id == swing
    # and the source candle alone genuinely could not have found it
    assert candles[4].record_id not in candidate.source_candle_record_ids


def test_a_swing_one_bar_past_the_span_still_does_not_qualify(b2s) -> None:
    """Adjacency is the formation's own extent, not a neighbourhood."""
    candles, candidate = b2s
    swing = "too-late"
    fact = StructuralRoleFact(
        StructuralRole.PULLBACK_HIGH,
        candles[6].availability_time_utc,
        swing,
        None,
        None,
    )
    context = StructuralContext(
        {},
        {},
        {},
        {candles[6].record_id: swing},
        {},
        {swing: fact},
        frozenset(),
        frozenset(),
        frozenset({swing}),
    )
    assert structural_role_of(candidate, context) is None
