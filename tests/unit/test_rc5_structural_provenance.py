"""RC5 Phase 2: the leg-origin gate surfaces the structural identifiers it
already resolved, instead of discarding them.

``_gate`` has always known which swing a break named as a leg origin, which
swing that break broke, and which candles are pivots of which confirmed swing --
it needs all of that to place ORDER BLOCKS. RC5 needs the same facts to decide
whether *any* reversal candidate sits at a decision origin, so the gate now
returns a :class:`StructuralContext` and tags reversal-context decisions with
the ids that produced them.

Nothing here changes a promotion. These tests exist to prove that: the gate's
POI output must be byte-identical to RC4's, and every id surfaced must be a
real frozen record id rather than something this layer invented.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.leg_origin import (
    ContextReason,
    LegOriginFrontier,
    StructuralContext,
    _gate,
    immutable_structure_gate,
    leg_origin_order_blocks,
    structure_context_decisions,
)
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import run_structure_walk
from tests.parity_support.ob_origin_series import analyze_rows, mirror
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_POI_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_MEASUREMENT_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

_SERIES = {
    "continuation": _continuation,
    "reversal": _reversal,
    "continuation_mirrored": lambda: mirror(_continuation()),
    "reversal_mirrored": lambda: mirror(_reversal()),
}


@pytest.fixture(params=sorted(_SERIES), ids=sorted(_SERIES))
def gated(request: pytest.FixtureRequest, tmp_path: Path):
    """Run the real batch gate on one explicit series and hand back everything
    a provenance assertion could need."""
    rows = _SERIES[request.param]()
    _pois, candles, measurement = analyze_rows(rows, tmp_path, request.param)
    swings = tuple(measurement.confirmed_swings)
    candidates = detect_engulfing(candles, _POI_CONFIG)
    order_blocks, mapped, context = immutable_structure_gate(
        detect_order_blocks(candles, _POI_CONFIG),
        candidates,
        candles,
        swings,
        _MEASUREMENT_CONFIG,
    )
    walk = run_structure_walk(
        tuple(candles),
        swings,
        detect_swing_relationships(swings, StructureConfiguration()),
    )
    return {
        "series": request.param,
        "candles": candles,
        "swings": swings,
        "swing_ids": {s.record_id for s in swings},
        "candidates": candidates,
        "order_blocks": order_blocks,
        "mapped": mapped,
        "context": context,
        "walk": walk,
        "measurement": measurement,
    }


# ---------------------------------------------------------------------------
# the context is real, complete and internally consistent
# ---------------------------------------------------------------------------


def test_the_batch_gate_returns_a_structural_context(gated) -> None:
    assert isinstance(gated["context"], StructuralContext)


def test_broken_and_unbroken_swings_partition_the_confirmed_swings(gated) -> None:
    context, all_ids = gated["context"], gated["swing_ids"]
    assert context.broken_swing_ids <= all_ids
    assert context.unbroken_swing_ids <= all_ids
    assert context.broken_swing_ids.isdisjoint(context.unbroken_swing_ids)
    assert context.broken_swing_ids | context.unbroken_swing_ids == all_ids


def test_defended_levels_are_monotone_and_include_the_current_ones(gated) -> None:
    """The role gate needs the swings the walk defends -- not every unbroken
    swing (that refuses nothing, see the H3 staircase), and not only the
    CURRENTLY defended ones either.

    "Currently defended" lapses as structure moves on, which makes the role
    non-monotone and silently breaks the replay's superset invariant. Every
    level the walk has ever protected or armed stays in the set.
    """
    walk = gated["walk"]
    context = gated["context"]
    defended = context.live_structure_swing_ids
    assert defended <= gated["swing_ids"]
    # a defended swing may already hold a HIGHER role (leg origin, or a swing
    # a break took), so the check is against the whole role map.
    known = set(context.role_by_swing)
    current = {
        s.record_id
        for s in (
            walk.protected_high,
            walk.protected_low,
            walk.weak_high,
            walk.weak_low,
        )
        if s is not None
    }
    assert current <= known
    historical = {t.protected_swing_id for t in walk.transitions} | {
        t.weak_swing_id for t in walk.transitions if t.weak_swing_id is not None
    }
    assert {s for s in historical if s in gated["swing_ids"]} <= known


def test_a_defended_role_is_never_retracted_by_later_structure(gated) -> None:
    """The invariant the batch replay depends on: the final prefix's role map
    is a superset of every earlier prefix's. When it is not, a POI silently
    lands on whatever later bar happened to recompute the walk."""
    candles, swings = gated["candles"], gated["swings"]
    final = gated["context"].role_by_swing
    for upto in (len(candles) // 2, (3 * len(candles)) // 4):
        now = candles[upto - 1].availability_time_utc
        prefix_swings = tuple(
            s for s in swings if s.meaningful_confirmation_time_utc <= now
        )
        _g, _w, _d, _t, earlier = _gate((), candles[:upto], prefix_swings, ())
        for swing_id in earlier.role_by_swing:
            assert swing_id in final, (
                "a role present on an earlier prefix vanished from the final one"
            )


def test_broken_swings_are_exactly_what_the_frozen_walk_broke(gated) -> None:
    assert gated["context"].broken_swing_ids == frozenset(
        t.broken_swing_id for t in gated["walk"].transitions
    )


def test_every_pivot_candle_maps_to_its_own_confirmed_swing(gated) -> None:
    context = gated["context"]
    for swing in gated["swings"]:
        side = (
            context.swing_high_candle_ids
            if swing.swing_type == SwingType.SWING_HIGH
            else context.swing_low_candle_ids
        )
        for candle_id in swing.pivot_candle_record_ids:
            assert candle_id in side


def test_the_two_pivot_side_maps_never_disagree_about_a_swing(gated) -> None:
    """A candle can be the pivot of both a high and a low run, but whichever
    swing a side map names must actually be a swing of that side."""
    context = gated["context"]
    by_id = {s.record_id: s for s in gated["swings"]}
    for swing_id in context.swing_high_candle_ids.values():
        assert by_id[swing_id].swing_type == SwingType.SWING_HIGH
    for swing_id in context.swing_low_candle_ids.values():
        assert by_id[swing_id].swing_type == SwingType.SWING_LOW


# ---------------------------------------------------------------------------
# leg origins: no invented identifiers
# ---------------------------------------------------------------------------


def test_leg_ids_are_real_break_candles_of_real_transitions(gated) -> None:
    context = gated["context"]
    break_candles = {t.break_candle_id for t in gated["walk"].transitions}
    broken = {t.broken_swing_id for t in gated["walk"].transitions}
    assert set(context.leg_id_by_origin_swing.values()) <= break_candles
    assert set(context.broken_swing_by_origin.values()) <= broken


def test_every_leg_origin_is_a_confirmed_swing_with_a_leg_and_a_broken_swing(
    gated,
) -> None:
    context = gated["context"]
    origins = set(context.leg_id_by_origin_swing)
    assert origins <= gated["swing_ids"]
    assert set(context.broken_swing_by_origin) == origins
    assert set(context.leg_origin_candle_ids.values()) == origins


def test_leg_origin_candles_are_pivot_candles_of_the_swing_they_name(gated) -> None:
    by_id = {s.record_id: s for s in gated["swings"]}
    for candle_id, swing_id in gated["context"].leg_origin_candle_ids.items():
        assert candle_id in by_id[swing_id].pivot_candle_record_ids


def test_every_order_block_sits_on_a_recorded_leg_origin_candle(gated) -> None:
    """The gate places an ORDER BLOCK only on a leg-origin pivot, so the
    provenance map has to cover every ORDER BLOCK it produced. This is the
    check that the map is populated from the same pass, not a re-derivation."""
    legs = gated["context"].leg_origin_candle_ids
    for order_block in gated["order_blocks"]:
        assert any(c in legs for c in order_block.source_candle_record_ids)


# ---------------------------------------------------------------------------
# decision-level provenance
# ---------------------------------------------------------------------------


def test_reversal_context_decisions_carry_all_three_identities(gated) -> None:
    decisions = structure_context_decisions(
        gated["candidates"], gated["candles"], gated["swings"]
    )
    reversal = [
        d for d in decisions if d.reason is ContextReason.MAPPED_REVERSAL_CONTEXT
    ]
    # Only the reversal series puts an engulfing inside a leg that a later
    # break confirms; the continuation series maps its engulfings trend-aligned.
    if gated["series"].startswith("reversal"):
        assert reversal, "the reversal series must map at least one"
    break_candles = {t.break_candle_id for t in gated["walk"].transitions}
    for decision in reversal:
        assert decision.origin_swing_id in gated["swing_ids"]
        assert decision.broken_swing_id in gated["swing_ids"]
        assert decision.break_candle_id in break_candles


def test_decisions_the_gate_did_not_resolve_claim_no_provenance(gated) -> None:
    """Only the reversal-context branch actually resolves an origin. A
    trend-aligned mapping is classified from the direction timeline alone, so
    it must not pretend to know which decision point it belongs to."""
    for decision in structure_context_decisions(
        gated["candidates"], gated["candles"], gated["swings"]
    ):
        if decision.reason is ContextReason.MAPPED_REVERSAL_CONTEXT:
            continue
        assert decision.origin_swing_id is None
        assert decision.broken_swing_id is None
        assert decision.break_candle_id is None


# ---------------------------------------------------------------------------
# the frontier carries it too, and nothing was regressed
# ---------------------------------------------------------------------------


def test_an_empty_frontier_starts_with_an_empty_context() -> None:
    context = LegOriginFrontier().context
    assert isinstance(context, StructuralContext)
    assert not context.leg_origin_candle_ids
    assert not context.broken_swing_ids


def test_surfacing_provenance_did_not_move_a_single_order_block(gated) -> None:
    """RC4 behaviour is frozen: this phase adds return values, nothing else."""
    assert {
        (ob.poi_type, ob.source_candle_record_ids, ob.availability_time_utc)
        for ob in gated["order_blocks"]
    } == {
        (ob.poi_type, ob.source_candle_record_ids, ob.availability_time_utc)
        for ob in leg_origin_order_blocks(
            detect_order_blocks(gated["candles"], _POI_CONFIG),
            gated["candles"],
            gated["swings"],
        )
    }
