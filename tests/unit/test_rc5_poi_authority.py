"""RC5 authority ladder: the author's §21 regression matrix, plus the two live
cases that defined the contract.

Every case here is stated in the author's own terms ("B2S + Shooting Star same
origin -> B2S only"). The cluster itself is supplied by the caller; this module
is the arbitration, so the fixtures construct the cluster explicitly and assert
what the ladder does with it.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btmm_ai_scanner.poi.authority import (
    AuthorityReason,
    OriginClusterKey,
    arbitrate_cluster,
    contains_zone,
    ladder_rank,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType

BASE = datetime(2026, 9, 4, 7, 0, tzinfo=UTC)
CLUSTER = OriginClusterKey(
    direction=PoiDirection.BEARISH,
    transition_break_candle_id=uuid.uuid4(),
    transition_broken_swing_id=uuid.uuid4(),
    origin_swing_id=uuid.uuid4(),
)
BULL_CLUSTER = OriginClusterKey(
    direction=PoiDirection.BULLISH,
    transition_break_candle_id=uuid.uuid4(),
    transition_broken_swing_id=uuid.uuid4(),
    origin_swing_id=uuid.uuid4(),
)


@dataclass(frozen=True)
class Cand:
    poi_type: PoiType
    direction: PoiDirection
    zone_bottom: Decimal
    zone_top: Decimal
    candidate_event_time_utc: datetime
    source_candle_record_ids: tuple[uuid.UUID, ...]


def _c(
    poi_type: PoiType,
    bottom: str,
    top: str,
    minutes: int = 0,
    direction: PoiDirection = PoiDirection.BEARISH,
) -> Cand:
    return Cand(
        poi_type,
        direction,
        Decimal(bottom),
        Decimal(top),
        BASE + timedelta(minutes=minutes),
        (uuid.uuid4(),),
    )


def _by_type(decisions: list) -> dict[PoiType, AuthorityReason]:
    return {d.candidate.poi_type: d.reason for d in decisions}


# --------------------------------------------------------------------------
# author §21 regression matrix
# --------------------------------------------------------------------------


def test_b2s_plus_shooting_star_same_origin_leaves_only_b2s() -> None:
    b2s = _c(PoiType.BUY_TO_SELL_CANDLE, "4461.42", "4486.42")
    star = _c(PoiType.SHOOTING_STAR, "4473.92", "4478.83", minutes=45)
    got = _by_type(arbitrate_cluster([star, b2s], CLUSTER))
    assert got[PoiType.BUY_TO_SELL_CANDLE] is AuthorityReason.PRIMARY
    assert got[PoiType.SHOOTING_STAR] is AuthorityReason.SAME_ORIGIN_SUBORDINATE


def test_s2b_plus_hammer_same_origin_leaves_only_s2b() -> None:
    s2b = _c(PoiType.SELL_TO_BUY_CANDLE, "4000", "4040", direction=PoiDirection.BULLISH)
    hammer = _c(
        PoiType.HAMMER, "4010", "4030", minutes=45, direction=PoiDirection.BULLISH
    )
    got = _by_type(arbitrate_cluster([hammer, s2b], BULL_CLUSTER))
    assert got[PoiType.SELL_TO_BUY_CANDLE] is AuthorityReason.PRIMARY
    assert got[PoiType.HAMMER] is AuthorityReason.SAME_ORIGIN_SUBORDINATE


def test_evening_star_beats_same_origin_pressure_wick() -> None:
    star = _c(PoiType.EVENING_STAR, "4374.99", "4432.08")
    wick = _c(PoiType.BEARISH_PRESSURE_WICK, "4398.77", "4412.75", minutes=45)
    got = _by_type(arbitrate_cluster([wick, star], CLUSTER))
    assert got[PoiType.EVENING_STAR] is AuthorityReason.PRIMARY
    assert got[PoiType.BEARISH_PRESSURE_WICK] is AuthorityReason.SAME_ORIGIN_SUBORDINATE


def test_shooting_star_beats_same_origin_pressure_wick() -> None:
    star = _c(PoiType.SHOOTING_STAR, "4460", "4500")
    wick = _c(PoiType.BEARISH_PRESSURE_WICK, "4470", "4490", minutes=45)
    got = _by_type(arbitrate_cluster([wick, star], CLUSTER))
    assert got[PoiType.SHOOTING_STAR] is AuthorityReason.PRIMARY
    assert got[PoiType.BEARISH_PRESSURE_WICK] is AuthorityReason.SAME_ORIGIN_SUBORDINATE


def test_engulfing_beats_contained_shooting_star() -> None:
    """The live H3 pair: both on source 2026-08-25 19:00, the star contained."""
    eng = _c(PoiType.BEARISH_ENGULFING, "4653.31", "4668.96")
    star = _c(PoiType.SHOOTING_STAR, "4657.56", "4668.96")
    got = _by_type(arbitrate_cluster([star, eng], CLUSTER))
    assert got[PoiType.BEARISH_ENGULFING] is AuthorityReason.PRIMARY
    assert got[PoiType.SHOOTING_STAR] is AuthorityReason.SAME_ORIGIN_SUBORDINATE


def test_b2s_keeps_an_independent_fvg() -> None:
    """The live M45 counterexample: the SELL FVG extends 37 points below the
    B2S zone, so it carries an imbalance region of its own."""
    b2s = _c(PoiType.BUY_TO_SELL_CANDLE, "4461.42", "4486.42")
    fvg = _c(PoiType.SELL_FAIR_VALUE_GAP, "4424.02", "4464.46", minutes=270)
    got = _by_type(arbitrate_cluster([b2s, fvg], CLUSTER))
    assert got[PoiType.BUY_TO_SELL_CANDLE] is AuthorityReason.PRIMARY
    assert got[PoiType.SELL_FAIR_VALUE_GAP] is AuthorityReason.INDEPENDENT


def test_b2s_suppresses_a_subordinate_same_formation_fvg() -> None:
    b2s = _c(PoiType.BUY_TO_SELL_CANDLE, "4461.42", "4486.42")
    fvg = _c(PoiType.SELL_FAIR_VALUE_GAP, "4470.00", "4480.00", minutes=45)
    got = _by_type(arbitrate_cluster([b2s, fvg], CLUSTER))
    assert got[PoiType.SELL_FAIR_VALUE_GAP] is AuthorityReason.SUBORDINATE_IMBALANCE


def test_two_spatially_separate_reversals_in_one_cluster_both_remain() -> None:
    """Author rule: a structurally/spatially separate reversal survives even at
    a shared origin. Sharing an origin swing is not enough -- the two must also
    describe the same price decision, which here they do not."""
    first = _c(PoiType.SHOOTING_STAR, "4430.00", "4448.92")
    second = _c(PoiType.SHOOTING_STAR, "4406.95", "4419.56", minutes=4320)
    got = [d.reason for d in arbitrate_cluster([first, second], CLUSTER)]
    assert got[0] is AuthorityReason.PRIMARY
    assert got[1] is AuthorityReason.INDEPENDENT


def test_an_overlapping_reversal_that_is_not_contained_is_still_subordinate() -> None:
    """The author's real M45 shape, which strict containment gets wrong.

    The BEARISH PRESSURE WICK sits on the swing that COMPLETES the reversal, so
    its top (4490.85) is ABOVE the B2S zone top (4486.42). Neither zone contains
    the other, yet they overlap and describe one decision.
    """
    b2s = _c(PoiType.BUY_TO_SELL_CANDLE, "4461.42", "4486.42")
    wick = _c(PoiType.BEARISH_PRESSURE_WICK, "4485.61", "4490.85", minutes=45)
    got = _by_type(arbitrate_cluster([b2s, wick], CLUSTER))
    assert got[PoiType.BUY_TO_SELL_CANDLE] is AuthorityReason.PRIMARY
    assert got[PoiType.BEARISH_PRESSURE_WICK] is (
        AuthorityReason.SAME_ORIGIN_SUBORDINATE
    )


def test_two_shooting_stars_in_one_cluster_leave_one_primary() -> None:
    outer = _c(PoiType.SHOOTING_STAR, "4460.00", "4500.00")
    inner = _c(PoiType.SHOOTING_STAR, "4470.00", "4490.00", minutes=45)
    decisions = arbitrate_cluster([outer, inner], CLUSTER)
    assert sum(d.reason is AuthorityReason.PRIMARY for d in decisions) == 1
    # the earlier formation wins the tie at equal rank; the contained one loses
    assert decisions[0].candidate is outer
    assert decisions[0].reason is AuthorityReason.PRIMARY
    assert decisions[1].candidate is inner
    assert decisions[1].reason is AuthorityReason.SAME_ORIGIN_SUBORDINATE


# --------------------------------------------------------------------------
# contract properties
# --------------------------------------------------------------------------


def test_exactly_one_primary_per_cluster() -> None:
    members = [
        _c(PoiType.BEARISH_PRESSURE_WICK, "4470", "4480"),
        _c(PoiType.SHOOTING_STAR, "4465", "4485", minutes=45),
        _c(PoiType.BEARISH_ENGULFING, "4462", "4488", minutes=90),
        _c(PoiType.EVENING_STAR, "4461", "4489", minutes=135),
        _c(PoiType.BUY_TO_SELL_CANDLE, "4460", "4490", minutes=180),
    ]
    decisions = arbitrate_cluster(members, CLUSTER)
    assert sum(d.reason is AuthorityReason.PRIMARY for d in decisions) == 1
    primary = next(d for d in decisions if d.reason is AuthorityReason.PRIMARY)
    assert primary.candidate.poi_type is PoiType.BUY_TO_SELL_CANDLE
    assert all(
        d.reason is AuthorityReason.SAME_ORIGIN_SUBORDINATE
        for d in decisions
        if d.reason is not AuthorityReason.PRIMARY
    )


def test_ladder_order_is_the_author_order() -> None:
    order = [
        PoiType.BUY_TO_SELL_CANDLE,
        PoiType.SELL_ORDER_BLOCK,
        PoiType.EVENING_STAR,
        PoiType.BEARISH_ENGULFING,
        PoiType.SHOOTING_STAR,
        PoiType.BEARISH_PRESSURE_WICK,
    ]
    ranks = [ladder_rank(t) for t in order]
    assert ranks == sorted(ranks)
    assert len(set(ranks)) == len(ranks)
    # the bullish mirror ranks identically
    assert ladder_rank(PoiType.SELL_TO_BUY_CANDLE) == ladder_rank(
        PoiType.BUY_TO_SELL_CANDLE
    )
    assert ladder_rank(PoiType.HAMMER) == ladder_rank(PoiType.SHOOTING_STAR)


def test_a_non_reversal_only_cluster_keeps_everything() -> None:
    members = [
        _c(PoiType.SELL_FAIR_VALUE_GAP, "4424", "4464"),
        _c(PoiType.RESISTANCE_ZONE, "4470", "4480", minutes=45),
    ]
    assert all(
        d.reason is AuthorityReason.INDEPENDENT
        for d in arbitrate_cluster(members, CLUSTER)
    )


def test_opposite_direction_member_is_never_subordinate() -> None:
    b2s = _c(PoiType.BUY_TO_SELL_CANDLE, "4460", "4490")
    hammer = _c(
        PoiType.HAMMER, "4470", "4480", minutes=45, direction=PoiDirection.BULLISH
    )
    got = _by_type(arbitrate_cluster([b2s, hammer], CLUSTER))
    assert got[PoiType.HAMMER] is AuthorityReason.INDEPENDENT


def test_containment_is_inclusive_on_both_edges() -> None:
    outer = _c(PoiType.BEARISH_ENGULFING, "4653.31", "4668.96")
    flush = _c(PoiType.SHOOTING_STAR, "4653.31", "4668.96")
    above = _c(PoiType.SHOOTING_STAR, "4657.56", "4673.71")
    assert contains_zone(outer, flush)
    assert not contains_zone(outer, above)


# --------------------------------------------------------------------------
# author cluster-identity guard: structural identifiers take precedence
# --------------------------------------------------------------------------

FORMATION_CLUSTER = OriginClusterKey(
    direction=PoiDirection.BEARISH,
    formation_candle_id=uuid.uuid4(),
)


def test_structural_provenance_is_reported() -> None:
    assert CLUSTER.is_structural
    assert not FORMATION_CLUSTER.is_structural


def test_a_same_candle_cluster_never_subordinates_an_fvg() -> None:
    """One candle can produce a reversal AND its own imbalance. Without
    structural provenance the FVG must survive even when contained."""
    star = _c(PoiType.SHOOTING_STAR, "4460", "4500")
    fvg = _c(PoiType.SELL_FAIR_VALUE_GAP, "4470", "4490")
    got = _by_type(arbitrate_cluster([star, fvg], FORMATION_CLUSTER))
    assert got[PoiType.SHOOTING_STAR] is AuthorityReason.PRIMARY
    assert got[PoiType.SELL_FAIR_VALUE_GAP] is AuthorityReason.INDEPENDENT


def test_a_same_candle_cluster_still_arbitrates_reversal_synonyms() -> None:
    """The legitimate same-candle case: a HAMMER drawn inside its own
    BULLISH ENGULFING is one formation described twice."""
    eng = _c(
        PoiType.BULLISH_ENGULFING,
        "3285.11",
        "3297.55",
        direction=PoiDirection.BULLISH,
    )
    hammer = _c(PoiType.HAMMER, "3285.11", "3294.40", direction=PoiDirection.BULLISH)
    got = _by_type(
        arbitrate_cluster(
            [hammer, eng],
            OriginClusterKey(
                direction=PoiDirection.BULLISH, formation_candle_id=uuid.uuid4()
            ),
        )
    )
    assert got[PoiType.BULLISH_ENGULFING] is AuthorityReason.PRIMARY
    assert got[PoiType.HAMMER] is AuthorityReason.SAME_ORIGIN_SUBORDINATE
