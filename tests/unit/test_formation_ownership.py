"""A valid multi-candle Base owns candle-pattern evidence inside it.

Before this layer, a Base and a Shooting Star sitting *inside* it both survived
as independent POIs, because `REVERSAL_LADDER` ranks only reversals and a Base
is not one. Ownership answers a different question -- do these describe the SAME
formation? -- and answers it from source-candle containment, not price overlap.

Standing changes; identity never does.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, NamedTuple
from uuid import UUID

from btmm_ai_scanner.poi.enums import BaseFamily, PoiDirection, PoiType
from btmm_ai_scanner.poi.formation_ownership import (
    OWNABLE_PATTERN_TYPES,
    OwnershipReason,
    OwnershipRelationship,
    formation_key,
    resolve_formation_ownership,
    subordinated_member_keys,
)
from btmm_ai_scanner.poi.leg_origin import _formation_key

_T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _cid(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


class _Cand(NamedTuple):
    """The minimal duck-typed shape every detector candidate already satisfies."""

    poi_type: PoiType
    direction: PoiDirection
    source_candle_record_ids: tuple[UUID, ...]
    availability_time_utc: datetime
    #: Only Bases carry one; patterns leave it None, exactly as the real
    #: candidates do.
    base_family: BaseFamily | None = None


def _base(
    *,
    base_indices: tuple[int, ...] = (1, 2, 3),
    departure_index: int = 4,
    poi_type: PoiType = PoiType.BASE_DROP,
    direction: PoiDirection = PoiDirection.BEARISH,
    minutes: int = 5,
    base_family: BaseFamily | None = BaseFamily.DROP_BASE_DROP,
) -> _Cand:
    return _Cand(
        poi_type=poi_type,
        direction=direction,
        source_candle_record_ids=(
            *(_cid(i) for i in base_indices),
            _cid(departure_index),
        ),
        availability_time_utc=_T0 + timedelta(minutes=minutes),
        base_family=base_family,
    )


def _pattern(
    poi_type: PoiType,
    indices: tuple[int, ...],
    direction: PoiDirection = PoiDirection.BEARISH,
    minutes: int = 5,
) -> _Cand:
    return _Cand(
        poi_type=poi_type,
        direction=direction,
        source_candle_record_ids=tuple(_cid(i) for i in indices),
        availability_time_utc=_T0 + timedelta(minutes=minutes),
    )


def _relationship(records: Any, member: _Cand) -> OwnershipRelationship | None:
    key = formation_key(member)
    for record in records:
        if record.member_key == key and record.relationship is not (
            OwnershipRelationship.PRIMARY
        ):
            return record.relationship
    return None


# --------------------------------------------------------------------------
# identity
# --------------------------------------------------------------------------


def test_formation_key_matches_leg_origin_exactly() -> None:
    """Ownership must key on the same identity the rest of the engine uses."""
    candidate = _pattern(PoiType.SHOOTING_STAR, (2,))
    assert formation_key(candidate) == _formation_key(candidate)


# --------------------------------------------------------------------------
# 1-4: the Base owns contained candle patterns
# --------------------------------------------------------------------------


def test_dbd_containing_shooting_star() -> None:
    base = _base()
    star = _pattern(PoiType.SHOOTING_STAR, (2,))
    records = resolve_formation_ownership([base, star])

    assert _relationship(records, star) is OwnershipRelationship.SUBORDINATE
    primaries = [r for r in records if r.relationship is OwnershipRelationship.PRIMARY]
    assert [r.owner_key for r in primaries] == [formation_key(base)]
    # identity preserved, not relabelled
    assert star.poi_type is PoiType.SHOOTING_STAR
    assert formation_key(star)[0] is PoiType.SHOOTING_STAR


def test_rbd_containing_bearish_pressure_wick() -> None:
    base = _base()
    wick = _pattern(PoiType.BEARISH_PRESSURE_WICK, (3,))
    records = resolve_formation_ownership([base, wick])
    assert _relationship(records, wick) is OwnershipRelationship.SUBORDINATE


def test_base_containing_doji_keeps_the_doji_identity() -> None:
    base = _base()
    doji = _pattern(PoiType.DOJI, (2,))
    records = resolve_formation_ownership([base, doji])

    assert _relationship(records, doji) is OwnershipRelationship.SUBORDINATE
    subordinate = next(
        r
        for r in records
        if r.relationship is OwnershipRelationship.SUBORDINATE
        and r.member_key == formation_key(doji)
    )
    # transport code 33 survives ownership; standing changed, identity did not
    assert subordinate.member_key[0] is PoiType.DOJI
    assert subordinate.reason is OwnershipReason.CONTAINED_CANDLE_PATTERN


def test_base_containing_engulfing_whose_whole_span_is_inside() -> None:
    base = _base()
    engulfing = _pattern(PoiType.BEARISH_ENGULFING, (2, 3))
    records = resolve_formation_ownership([base, engulfing])
    assert _relationship(records, engulfing) is OwnershipRelationship.SUBORDINATE


# --------------------------------------------------------------------------
# 5-6: independence is the default
# --------------------------------------------------------------------------


def test_pattern_outside_the_base_is_independent() -> None:
    base = _base()
    star = _pattern(PoiType.SHOOTING_STAR, (9,))
    assert _relationship(resolve_formation_ownership([base, star]), star) is None


def test_multi_candle_pattern_only_partly_inside_is_independent() -> None:
    """One intersecting source candle is not containment."""
    base = _base()
    engulfing = _pattern(PoiType.BEARISH_ENGULFING, (3, 9))
    assert (
        _relationship(resolve_formation_ownership([base, engulfing]), engulfing) is None
    )


def test_pattern_on_the_departure_candle_is_independent() -> None:
    """The departure is the impulse that confirms the base, not the pause."""
    base = _base()
    star = _pattern(PoiType.SHOOTING_STAR, (4,))
    assert _relationship(resolve_formation_ownership([base, star]), star) is None


def test_opposite_direction_pattern_is_independent() -> None:
    """A pattern defending the other side is a different decision."""
    base = _base()
    hammer = _pattern(PoiType.HAMMER, (2,), direction=PoiDirection.BULLISH)
    assert _relationship(resolve_formation_ownership([base, hammer]), hammer) is None


# --------------------------------------------------------------------------
# 7: FVG independence is preserved
# --------------------------------------------------------------------------


def test_fvg_is_never_owned_by_a_base() -> None:
    """A Base departure creates a real imbalance; it is its own region."""
    assert PoiType.BUY_FAIR_VALUE_GAP not in OWNABLE_PATTERN_TYPES
    assert PoiType.SELL_FAIR_VALUE_GAP not in OWNABLE_PATTERN_TYPES
    base = _base()
    fvg = _pattern(PoiType.SELL_FAIR_VALUE_GAP, (2, 3))
    assert _relationship(resolve_formation_ownership([base, fvg]), fvg) is None


def test_order_block_and_b2s_precedence_are_not_frozen_by_omission() -> None:
    """Forensics pending: neither may be subordinated until evidence returns."""
    for poi_type in (
        PoiType.BUY_ORDER_BLOCK,
        PoiType.SELL_ORDER_BLOCK,
        PoiType.BUY_TO_SELL_CANDLE,
        PoiType.SELL_TO_BUY_CANDLE,
    ):
        assert poi_type not in OWNABLE_PATTERN_TYPES
    base = _base()
    block = _pattern(PoiType.SELL_ORDER_BLOCK, (2,))
    assert _relationship(resolve_formation_ownership([base, block]), block) is None


# --------------------------------------------------------------------------
# 8-9: causality. No future knowledge may suppress the past.
# --------------------------------------------------------------------------


def test_ownership_is_inert_before_the_base_becomes_available() -> None:
    """The pattern is detectable at minute 2; the Base only confirms at minute 5.

    Between those instants the pattern must stand on its own -- a Base nobody
    could know about yet cannot subordinate it.
    """
    star = _pattern(PoiType.SHOOTING_STAR, (2,), minutes=2)
    base = _base(minutes=5)
    records = resolve_formation_ownership([base, star])

    record = next(
        r for r in records if r.relationship is OwnershipRelationship.SUBORDINATE
    )
    assert record.active_from_utc == base.availability_time_utc

    before = _T0 + timedelta(minutes=4)
    assert subordinated_member_keys(records, before) == frozenset()

    at_confirmation = base.availability_time_utc
    assert formation_key(star) in subordinated_member_keys(records, at_confirmation)


def test_activation_is_the_later_of_the_two_availabilities() -> None:
    """A Base confirmed first cannot own a pattern that does not exist yet."""
    base = _base(minutes=5)
    late = _pattern(PoiType.DOJI, (2,), minutes=9)
    records = resolve_formation_ownership([base, late])
    record = next(
        r for r in records if r.relationship is OwnershipRelationship.SUBORDINATE
    )
    assert record.active_from_utc == late.availability_time_utc


# --------------------------------------------------------------------------
# determinism
# --------------------------------------------------------------------------


def test_resolution_is_deterministic_and_order_independent() -> None:
    base = _base()
    star = _pattern(PoiType.SHOOTING_STAR, (2,))
    doji = _pattern(PoiType.DOJI, (3,))
    forward = resolve_formation_ownership([base, star, doji])
    reversed_ = resolve_formation_ownership([doji, star, base])
    assert forward == reversed_


def test_no_bases_means_no_records() -> None:
    star = _pattern(PoiType.SHOOTING_STAR, (2,))
    assert resolve_formation_ownership([star]) == ()


# --------------------------------------------------------------------------
# only a STANDARD-direction Base is authoritative
# --------------------------------------------------------------------------


def test_a_non_standard_family_base_owns_nothing() -> None:
    """RALLY_BASE_DROP is not a Base under the approved standard.

    It is still detected and still present for forensics -- it simply may not
    subordinate anything, because a formation the standard does not recognise
    cannot outrank one it does.
    """
    base = _base(base_family=BaseFamily.RALLY_BASE_DROP)
    star = _pattern(PoiType.SHOOTING_STAR, (2,))
    assert resolve_formation_ownership([base, star]) == ()


def test_drop_base_rally_also_owns_nothing() -> None:
    base = _base(
        poi_type=PoiType.BASE_RALLY,
        direction=PoiDirection.BULLISH,
        base_family=BaseFamily.DROP_BASE_RALLY,
    )
    hammer = _pattern(PoiType.HAMMER, (2,), direction=PoiDirection.BULLISH)
    assert resolve_formation_ownership([base, hammer]) == ()


def test_a_base_with_no_known_arrival_owns_nothing() -> None:
    """Unverifiable is not authoritative."""
    base = _base(base_family=None)
    star = _pattern(PoiType.SHOOTING_STAR, (2,))
    assert resolve_formation_ownership([base, star]) == ()
