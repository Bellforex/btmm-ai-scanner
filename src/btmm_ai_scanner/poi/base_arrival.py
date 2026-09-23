"""Which market leg ARRIVED at a Base -- read from structure, not from a candle.

A Base is the middle of a three-part formation: ``arrival leg -> base ->
departure leg``. The raw detector in :mod:`btmm_ai_scanner.poi.bases` can see
the base and the departure, because both are candle geometry inside the window
it is scanning. It CANNOT see the arrival: the leg that brought price here is a
structural fact spanning many candles, and the candle immediately before the
base is not that leg. A two-candle bounce inside a bearish move closes up, and
a detector reading one candle calls the whole formation a rally arrival.

So the detector emits ``base_family=None``, and this layer assigns the family
from the SAME causal structure timeline the context gate already runs --
``leg_origin.structure_direction_at``. No second structure walk, no new
constant, no new detector.

Where no leg has been established yet the arrival is ``UNDETERMINED`` and the
family stays ``None``. That is a real answer, not a gap to be filled: an
unverifiable Base is not an authoritative Base (see
``enums.is_standard_base_family``), and falling back to the last candle is
exactly the defect this layer exists to remove.
"""

from __future__ import annotations

import bisect
from datetime import datetime
from typing import TYPE_CHECKING, Any, NamedTuple
from uuid import UUID

from btmm_ai_scanner.poi.enums import BaseFamily, PoiType
from btmm_ai_scanner.poi.leg_origin import structure_direction_at
from btmm_ai_scanner.structure.enums import StructureDirection

if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Sequence

    from btmm_ai_scanner.poi.bases import BaseCandidate
    from btmm_ai_scanner.structure.transitions import StructureWalkResult

__all__ = [
    "BaseArrivalFact",
    "assign_base_arrival",
    "base_family_for_arrival",
    "resolve_base_arrival",
]

#: (arrival, departure) -> family. The departure is carried by the POI type the
#: detector already assigned, so this table is total over the four combinations
#: and introduces no new transport code.
_FAMILY: dict[tuple[StructureDirection, PoiType], BaseFamily] = {
    (StructureDirection.BULLISH, PoiType.BASE_RALLY): BaseFamily.RALLY_BASE_RALLY,
    (StructureDirection.BEARISH, PoiType.BASE_RALLY): BaseFamily.DROP_BASE_RALLY,
    (StructureDirection.BULLISH, PoiType.BASE_DROP): BaseFamily.RALLY_BASE_DROP,
    (StructureDirection.BEARISH, PoiType.BASE_DROP): BaseFamily.DROP_BASE_DROP,
}


def base_family_for_arrival(
    arrival: StructureDirection, poi_type: PoiType
) -> BaseFamily | None:
    """The family, or ``None`` when the arrival leg is not yet established."""
    return _FAMILY.get((arrival, poi_type))


class BaseArrivalFact(NamedTuple):
    """Why a Base carries the family it carries, in full.

    ``arrival_leg_id`` is the structure break that put the market into this
    direction -- ``None`` when the direction came from the walk's bootstrap
    (the first HH+HL / LH+LL pair) rather than from a break, and when the
    arrival is ``UNDETERMINED``.

    ``arrival_known_from_utc`` is when that fact became available, which is
    always <= ``arrival_reference_utc``: this is the causality receipt.
    """

    base_key: tuple[Any, ...]
    arrival_reference_utc: datetime
    arrival_direction: StructureDirection
    arrival_leg_id: tuple[str, UUID, UUID] | None
    arrival_known_from_utc: datetime | None
    family: BaseFamily | None


def _base_key(base: BaseCandidate) -> tuple[Any, ...]:
    """The key ``formation_ownership.formation_key`` uses, unchanged."""
    return (base.poi_type, base.source_candle_record_ids)


def _establishing_leg(
    walk: StructureWalkResult | None, known_from: datetime | None
) -> tuple[str, UUID, UUID] | None:
    if walk is None or known_from is None:
        return None
    for transition in reversed(walk.transitions):
        if transition.availability_time_utc == known_from:
            return (
                transition.transition_type.value,
                transition.broken_swing_id,
                transition.break_candle_id,
            )
    return None


def resolve_base_arrival(
    bases: Sequence[BaseCandidate],
    timeline: tuple[list[datetime], list[StructureDirection]],
    walk: StructureWalkResult | None = None,
) -> dict[tuple[Any, ...], BaseArrivalFact]:
    """Arrival facts for every Base, keyed by formation key.

    The reference instant is the Base's FIRST candle's event time -- the moment
    price arrived. Structure known only later cannot reach it, because
    ``structure_direction_at`` bisects on availability.
    """
    times, _ = timeline
    facts: dict[tuple[Any, ...], BaseArrivalFact] = {}
    for base in bases:
        reference = base.candidate_event_time_utc
        direction = structure_direction_at(timeline, reference)
        index = bisect.bisect_right(times, reference)
        known_from = times[index - 1] if index else None
        facts[_base_key(base)] = BaseArrivalFact(
            base_key=_base_key(base),
            arrival_reference_utc=reference,
            arrival_direction=direction,
            arrival_leg_id=_establishing_leg(walk, known_from),
            arrival_known_from_utc=known_from,
            family=base_family_for_arrival(direction, base.poi_type),
        )
    return facts


def assign_base_arrival(
    bases: Sequence[BaseCandidate],
    timeline: tuple[list[datetime], list[StructureDirection]],
    walk: StructureWalkResult | None = None,
) -> tuple[tuple[BaseCandidate, ...], dict[tuple[Any, ...], BaseArrivalFact]]:
    """The Bases with ``base_family`` filled in, plus the facts that justify it.

    Identity is untouched: ``_replace`` keeps the POI type and the source
    candle ids, so the formation key is the same before and after.
    """
    facts = resolve_base_arrival(bases, timeline, walk)
    assigned = tuple(
        base._replace(base_family=facts[_base_key(base)].family) for base in bases
    )
    return assigned, facts
