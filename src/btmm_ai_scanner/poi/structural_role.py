"""RC5 STRUCTURAL ORIGIN GATE: a reversal pattern is only a POI where the
market actually made a decision.

Author decision, 2026-09-20. RC5 profile only; RC4 (``2f1d2b9``) stays frozen.

WHY THIS IS SEPARATE FROM AUTHORITY ARBITRATION
------------------------------------------------
The two filters answer different questions and neither can do the other's job:

* this module answers *"is this pattern a meaningful POI at all?"*
* ``poi/authority.py`` answers *"when several meaningful patterns describe one
  decision event, which owns it?"*

The live H3 registry proved they are not interchangeable. Availability
2026-08-31 04:00 released a descending staircase of six BEARISH PRESSURE WICKs
(4673 -> 4588) spread over three days. They share no zone, so no authority
ladder can touch them -- yet none of them marks a decision point. They are
mid-leg texture and must be refused HERE, by structural role. Conversely the
author's M45 B2S and its two contained SHOOTING STARs all sit at a genuine
origin, so this gate passes all three and the ladder decides between them.

NO SECOND SWING ENGINE
----------------------
Every role below is read from primitives that already exist: the frozen
confirmed swings (``domain/swings.py``), the frozen structure walk and its
breaks (``structure/transitions.py``) and the RC4 framework's ranges and
liquidity levels (``framework/``). This module adds no threshold and no
detector of its own.

THE RULE
--------
A reversal-family candidate is promoted only if its formation touches a
structural extreme in the direction it claims:

* ``LEG_ORIGIN`` -- a pivot candle of the swing a confirmed break named as the
  origin of the leg it confirmed (the strongest role; it is exactly what
  ``poi/leg_origin.py`` already computes for ORDER BLOCKS);
* ``SWING_HIGH_ORIGIN`` / ``SWING_LOW_ORIGIN`` -- a pivot candle of a confirmed
  swing of the matching extreme;
* ``PULLBACK_HIGH`` / ``PULLBACK_LOW`` -- a confirmed swing that the walk did
  not break, i.e. the terminal of a correction inside the prevailing leg;
* ``RANGE_HIGH`` / ``RANGE_LOW`` -- the candidate's zone reaches a detected
  consolidation boundary;
* ``LIQUIDITY_EXTREME`` -- the candidate's zone reaches a tracked liquidity
  pool (equal highs / lows, session or period extreme);
* ``TRENDLINE_EXTREME`` -- the candidate's zone reaches a detected trendline
  at the formation bar.

A geometrically perfect reversal candle in the middle of an established leg
matches none of these and stays a RAW PATTERN.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from btmm_ai_scanner.poi.authority import REVERSAL_TYPES
from btmm_ai_scanner.poi.enums import PoiDirection

__all__ = [
    "BEARISH_ROLES",
    "BULLISH_ROLES",
    "StructuralOriginDecision",
    "StructuralRole",
    "assign_structural_roles",
    "role_matches_direction",
    "zone_reaches",
]


class StructuralRole(StrEnum):
    LEG_ORIGIN = "LEG_ORIGIN"
    SWING_HIGH_ORIGIN = "SWING_HIGH_ORIGIN"
    SWING_LOW_ORIGIN = "SWING_LOW_ORIGIN"
    PULLBACK_HIGH = "PULLBACK_HIGH"
    PULLBACK_LOW = "PULLBACK_LOW"
    RANGE_HIGH = "RANGE_HIGH"
    RANGE_LOW = "RANGE_LOW"
    LIQUIDITY_EXTREME = "LIQUIDITY_EXTREME"
    TRENDLINE_EXTREME = "TRENDLINE_EXTREME"
    #: not a role -- the refusal
    MID_LEG = "MID_LEG"


#: A bullish reversal claims a low is defended, so it must sit at a low-side
#: extreme. Range / liquidity / trendline / leg-origin roles are side-neutral:
#: the detector's own direction already fixes which side it reacts from.
BULLISH_ROLES = frozenset(
    {
        StructuralRole.LEG_ORIGIN,
        StructuralRole.SWING_LOW_ORIGIN,
        StructuralRole.PULLBACK_LOW,
        StructuralRole.RANGE_LOW,
        StructuralRole.LIQUIDITY_EXTREME,
        StructuralRole.TRENDLINE_EXTREME,
    }
)
BEARISH_ROLES = frozenset(
    {
        StructuralRole.LEG_ORIGIN,
        StructuralRole.SWING_HIGH_ORIGIN,
        StructuralRole.PULLBACK_HIGH,
        StructuralRole.RANGE_HIGH,
        StructuralRole.LIQUIDITY_EXTREME,
        StructuralRole.TRENDLINE_EXTREME,
    }
)


@dataclass(frozen=True)
class StructuralOriginDecision:
    candidate: Any
    role: StructuralRole
    #: the swing whose pivot the formation touches, when the role is a swing role
    origin_swing_id: UUID | None = None

    @property
    def promoted(self) -> bool:
        return self.role is not StructuralRole.MID_LEG


def role_matches_direction(role: StructuralRole, direction: PoiDirection) -> bool:
    allowed = BULLISH_ROLES if direction is PoiDirection.BULLISH else BEARISH_ROLES
    return role in allowed


def zone_reaches(candidate: Any, level: Decimal, tolerance: Decimal) -> bool:
    """Does the candidate's zone reach ``level`` within ``tolerance``? Used for
    range boundaries, liquidity pools and trendlines, which are lines rather
    than candles and so cannot be matched by candle identity."""
    return (
        Decimal(candidate.zone_bottom) - tolerance
        <= level
        <= Decimal(candidate.zone_top) + tolerance
    )


def assign_structural_roles(
    candidates: Iterable[Any],
    *,
    leg_origin_candle_ids: Mapping[UUID, UUID] | None = None,
    swing_high_candle_ids: Mapping[UUID, UUID] | None = None,
    swing_low_candle_ids: Mapping[UUID, UUID] | None = None,
    unbroken_swing_ids: frozenset[UUID] = frozenset(),
    range_levels: Sequence[tuple[Decimal, StructuralRole]] = (),
    liquidity_levels: Sequence[Decimal] = (),
    trendline_levels: Sequence[Decimal] = (),
    level_tolerance: Decimal = Decimal("0"),
) -> list[StructuralOriginDecision]:
    """Assign each reversal-family candidate its structural role, or MID_LEG.

    The maps are ``candle record_id -> swing record_id`` for the pivot candles
    of, respectively, the leg-origin swings a break named, confirmed swing
    highs and confirmed swing lows. ``unbroken_swing_ids`` are the confirmed
    swings the structure walk never broke, which makes their terminals
    pullback extremes rather than leg origins.

    Non-reversal families are returned untouched with ``LEG_ORIGIN`` withheld:
    they are simply not gated here (an imbalance, a base and a structural zone
    each obey their own location rules).
    """
    legs = leg_origin_candle_ids or {}
    highs = swing_high_candle_ids or {}
    lows = swing_low_candle_ids or {}
    out: list[StructuralOriginDecision] = []

    for candidate in candidates:
        if candidate.poi_type not in REVERSAL_TYPES:
            continue
        bullish = candidate.direction is PoiDirection.BULLISH
        role = StructuralRole.MID_LEG
        swing_id: UUID | None = None

        for candle_id in candidate.source_candle_record_ids:
            if candle_id in legs:
                role, swing_id = StructuralRole.LEG_ORIGIN, legs[candle_id]
                break
            pivots = lows if bullish else highs
            if candle_id in pivots:
                swing_id = pivots[candle_id]
                if swing_id in unbroken_swing_ids:
                    role = (
                        StructuralRole.PULLBACK_LOW
                        if bullish
                        else StructuralRole.PULLBACK_HIGH
                    )
                else:
                    role = (
                        StructuralRole.SWING_LOW_ORIGIN
                        if bullish
                        else StructuralRole.SWING_HIGH_ORIGIN
                    )
                break

        if role is StructuralRole.MID_LEG:
            for level, boundary in range_levels:
                if boundary is (
                    StructuralRole.RANGE_LOW if bullish else StructuralRole.RANGE_HIGH
                ) and zone_reaches(candidate, level, level_tolerance):
                    role = boundary
                    break
        if role is StructuralRole.MID_LEG:
            for level in liquidity_levels:
                if zone_reaches(candidate, level, level_tolerance):
                    role = StructuralRole.LIQUIDITY_EXTREME
                    break
        if role is StructuralRole.MID_LEG:
            for level in trendline_levels:
                if zone_reaches(candidate, level, level_tolerance):
                    role = StructuralRole.TRENDLINE_EXTREME
                    break

        if role is not StructuralRole.MID_LEG and not role_matches_direction(
            role, candidate.direction
        ):
            role, swing_id = StructuralRole.MID_LEG, None
        out.append(StructuralOriginDecision(candidate, role, swing_id))
    return out
