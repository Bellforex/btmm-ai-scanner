"""RC5 structural-origin gate.

The decisive case is the author's H3 pressure-wick staircase: six BEARISH
PRESSURE WICKs released by one late break, spread over three days and 85
points, none of them at a decision point. No authority ladder can remove them
(they share no zone), so the gate must.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.structural_role import (
    StructuralRole,
    assign_structural_roles,
    role_matches_direction,
    zone_reaches,
)

BASE = datetime(2026, 8, 25, 19, 0, tzinfo=UTC)


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
    candle: uuid.UUID | None = None,
    hours: int = 0,
    direction: PoiDirection = PoiDirection.BEARISH,
) -> Cand:
    return Cand(
        poi_type,
        direction,
        Decimal(bottom),
        Decimal(top),
        BASE + timedelta(hours=hours),
        (candle or uuid.uuid4(),),
    )


def _roles(decisions: list) -> list[StructuralRole]:
    return [d.role for d in decisions]


# --------------------------------------------------------------------------
# the refusal this gate exists for
# --------------------------------------------------------------------------


def test_the_h3_mid_leg_pressure_wick_staircase_is_refused() -> None:
    """Live H3 zones, availability 2026-08-31 04:00. None touches a pivot, a
    range boundary, a liquidity pool or a trendline."""
    staircase = [
        _c(PoiType.BEARISH_PRESSURE_WICK, "4657.56", "4673.71", hours=3),
        _c(PoiType.BEARISH_PRESSURE_WICK, "4622.96", "4632.94", hours=15),
        _c(PoiType.BEARISH_PRESSURE_WICK, "4605.02", "4627.06", hours=27),
        _c(PoiType.BEARISH_PRESSURE_WICK, "4610.27", "4618.07", hours=48),
        _c(PoiType.BEARISH_PRESSURE_WICK, "4600.49", "4611.42", hours=51),
        _c(PoiType.BEARISH_PRESSURE_WICK, "4588.67", "4601.37", hours=54),
    ]
    decisions = assign_structural_roles(staircase)
    assert _roles(decisions) == [StructuralRole.MID_LEG] * 6
    assert not any(d.promoted for d in decisions)


def test_a_pattern_on_a_leg_origin_pivot_is_promoted() -> None:
    candle, swing = uuid.uuid4(), uuid.uuid4()
    candidate = _c(PoiType.BUY_TO_SELL_CANDLE, "4461.42", "4486.42", candle=candle)
    (decision,) = assign_structural_roles(
        [candidate], leg_origin_candle_ids={candle: swing}
    )
    assert decision.role is StructuralRole.LEG_ORIGIN
    assert decision.origin_swing_id == swing
    assert decision.promoted


def test_leg_origin_outranks_a_plain_swing_pivot() -> None:
    candle, leg_swing, other = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    candidate = _c(PoiType.SHOOTING_STAR, "4460", "4500", candle=candle)
    (decision,) = assign_structural_roles(
        [candidate],
        leg_origin_candle_ids={candle: leg_swing},
        swing_high_candle_ids={candle: other},
    )
    assert decision.role is StructuralRole.LEG_ORIGIN
    assert decision.origin_swing_id == leg_swing


# --------------------------------------------------------------------------
# swing / pullback roles
# --------------------------------------------------------------------------


def test_a_bearish_pattern_on_a_broken_swing_high_is_a_swing_high_origin() -> None:
    candle, swing = uuid.uuid4(), uuid.uuid4()
    candidate = _c(PoiType.EVENING_STAR, "4629.23", "4673.71", candle=candle)
    (decision,) = assign_structural_roles(
        [candidate], swing_high_candle_ids={candle: swing}
    )
    assert decision.role is StructuralRole.SWING_HIGH_ORIGIN


def test_an_unbroken_swing_makes_the_terminal_a_pullback_extreme() -> None:
    candle, swing = uuid.uuid4(), uuid.uuid4()
    candidate = _c(PoiType.SHOOTING_STAR, "4460", "4500", candle=candle)
    (decision,) = assign_structural_roles(
        [candidate],
        swing_high_candle_ids={candle: swing},
        unbroken_swing_ids=frozenset({swing}),
    )
    assert decision.role is StructuralRole.PULLBACK_HIGH


def test_a_bullish_pattern_on_a_swing_high_is_not_promoted() -> None:
    """Direction must agree with the side the role defends."""
    candle, swing = uuid.uuid4(), uuid.uuid4()
    candidate = _c(
        PoiType.HAMMER, "4460", "4500", candle=candle, direction=PoiDirection.BULLISH
    )
    (decision,) = assign_structural_roles(
        [candidate], swing_high_candle_ids={candle: swing}
    )
    assert decision.role is StructuralRole.MID_LEG
    assert decision.origin_swing_id is None


def test_a_bullish_pattern_on_a_swing_low_is_promoted() -> None:
    candle, swing = uuid.uuid4(), uuid.uuid4()
    candidate = _c(
        PoiType.HAMMER, "4000", "4040", candle=candle, direction=PoiDirection.BULLISH
    )
    (decision,) = assign_structural_roles(
        [candidate], swing_low_candle_ids={candle: swing}
    )
    assert decision.role is StructuralRole.SWING_LOW_ORIGIN


# --------------------------------------------------------------------------
# level-based roles
# --------------------------------------------------------------------------


def test_a_bearish_pattern_reaching_the_range_high_is_promoted() -> None:
    candidate = _c(PoiType.SHOOTING_STAR, "4465.60", "4470.54")
    (decision,) = assign_structural_roles(
        [candidate],
        range_levels=[(Decimal("4468"), StructuralRole.RANGE_HIGH)],
    )
    assert decision.role is StructuralRole.RANGE_HIGH


def test_a_bearish_pattern_reaching_only_the_range_low_is_refused() -> None:
    candidate = _c(PoiType.SHOOTING_STAR, "4465.60", "4470.54")
    (decision,) = assign_structural_roles(
        [candidate], range_levels=[(Decimal("4468"), StructuralRole.RANGE_LOW)]
    )
    assert decision.role is StructuralRole.MID_LEG


def test_liquidity_and_trendline_levels_promote_either_direction() -> None:
    bear = _c(PoiType.BEARISH_PRESSURE_WICK, "4460", "4470")
    bull = _c(
        PoiType.BULLISH_PRESSURE_WICK, "4460", "4470", direction=PoiDirection.BULLISH
    )
    liq = assign_structural_roles([bear, bull], liquidity_levels=[Decimal("4465")])
    assert _roles(liq) == [StructuralRole.LIQUIDITY_EXTREME] * 2
    tl = assign_structural_roles([bear, bull], trendline_levels=[Decimal("4465")])
    assert _roles(tl) == [StructuralRole.TRENDLINE_EXTREME] * 2


def test_level_tolerance_is_applied_symmetrically() -> None:
    candidate = _c(PoiType.SHOOTING_STAR, "4460", "4470")
    assert not zone_reaches(candidate, Decimal("4472"), Decimal("0"))
    assert zone_reaches(candidate, Decimal("4472"), Decimal("2"))
    assert zone_reaches(candidate, Decimal("4458"), Decimal("2"))


# --------------------------------------------------------------------------
# family scope
# --------------------------------------------------------------------------


def test_non_reversal_families_are_not_gated_here() -> None:
    """An imbalance, a base and a structural zone obey their own location
    rules; this gate must not touch them."""
    members = [
        _c(PoiType.SELL_FAIR_VALUE_GAP, "4424.02", "4464.46"),
        _c(PoiType.BASE_DROP, "4400", "4420"),
        _c(PoiType.RESISTANCE_ZONE, "4500", "4510"),
    ]
    assert assign_structural_roles(members) == []


def test_every_ladder_type_is_gated() -> None:
    from btmm_ai_scanner.poi.authority import REVERSAL_LADDER

    bearish = {
        PoiType.BUY_TO_SELL_CANDLE,
        PoiType.SELL_ORDER_BLOCK,
        PoiType.EVENING_STAR,
        PoiType.BEARISH_ENGULFING,
        PoiType.SHOOTING_STAR,
        PoiType.BEARISH_PRESSURE_WICK,
    }
    for poi_type in REVERSAL_LADDER:
        direction = (
            PoiDirection.BEARISH if poi_type in bearish else PoiDirection.BULLISH
        )
        candidate = _c(poi_type, "4460", "4470", direction=direction)
        (decision,) = assign_structural_roles([candidate])
        assert decision.role is StructuralRole.MID_LEG, poi_type


def test_role_direction_table_is_exhaustive_and_disjoint_where_it_must_be() -> None:
    assert role_matches_direction(StructuralRole.SWING_LOW_ORIGIN, PoiDirection.BULLISH)
    assert not role_matches_direction(
        StructuralRole.SWING_LOW_ORIGIN, PoiDirection.BEARISH
    )
    assert role_matches_direction(
        StructuralRole.SWING_HIGH_ORIGIN, PoiDirection.BEARISH
    )
    assert not role_matches_direction(
        StructuralRole.SWING_HIGH_ORIGIN, PoiDirection.BULLISH
    )
    for side_neutral in (
        StructuralRole.LEG_ORIGIN,
        StructuralRole.LIQUIDITY_EXTREME,
        StructuralRole.TRENDLINE_EXTREME,
    ):
        assert role_matches_direction(side_neutral, PoiDirection.BULLISH)
        assert role_matches_direction(side_neutral, PoiDirection.BEARISH)
