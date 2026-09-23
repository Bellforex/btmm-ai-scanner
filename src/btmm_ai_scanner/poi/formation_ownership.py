"""RC5 FORMATION OWNERSHIP — do two detections describe the SAME formation?

This is a different question from same-origin reversal authority, and it needed
its own layer. `REVERSAL_LADDER` ranks reversal synonyms that share a structural
origin; a Base is not a reversal and is deliberately NOT in that ladder, so
before this module a valid multi-candle Base and a candle pattern sitting
*inside* it both survived as independent POIs — which is how a Shooting Star
contained in a Base became the visible, authoritative record while the Base that
actually described the decision was left unranked.

Pipeline position:

    raw detectors
      -> structural qualification
      -> FORMATION OWNERSHIP        <- here
      -> same-origin reversal authority
      -> lifecycle / validity
      -> P5 / P8
      -> display arbitration

WHAT OWNERSHIP MAY AND MAY NOT DO
---------------------------------
It changes STANDING, never IDENTITY. A Doji subordinate to a Drop-Base-Drop is
still `PoiType.DOJI` with its own geometry and its own transport code; nothing
is relabelled, nothing is deleted, and every subordinate record stays available
for forensics, parity and historical evidence.

It is also not a chart-overlap rule. Price overlap is not evidence: ownership
requires that the member's COMPLETE source span be part of the Base's own base
candles, that directions agree, and that both records are causally available.

CAUSALITY
---------
Ownership begins at `active_from_utc`, the later of the two availability times,
so a Base discovered later can never retroactively suppress a pattern that was
actionable before the Base existed. Consumers must honour `active_from_utc`
rather than treating ownership as timeless.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum
from typing import Any, NamedTuple
from uuid import UUID

from btmm_ai_scanner.poi.enums import PoiType, is_standard_base_family

__all__ = [
    "BASE_TYPES",
    "OWNABLE_PATTERN_TYPES",
    "FormationOwnership",
    "OwnershipReason",
    "OwnershipRelationship",
    "formation_key",
    "resolve_formation_ownership",
]


#: The two frozen Base transport codes. The RC5 family axis (RBR/DBR/RBD/DBD)
#: is metadata on the candidate and is not needed to decide ownership.
BASE_TYPES = frozenset({PoiType.BASE_RALLY, PoiType.BASE_DROP})

#: Candle patterns a Base may own when they are part of the same formation.
#:
#: FVG is deliberately ABSENT. A Base departure legitimately creates an
#: imbalance, and that imbalance is its own region rather than a restatement of
#: the Base, so FVG independence is preserved and only the existing by-product
#: rule in `authority.py` may ever suppress one.
#:
#: ORDER BLOCK and BUY_TO_SELL / SELL_TO_BUY are also absent, pending forensics:
#: precedence against a Base has not been established in either direction and
#: must not be frozen by omission or by guess.
OWNABLE_PATTERN_TYPES = frozenset(
    {
        PoiType.DOJI,
        PoiType.BULLISH_PRESSURE_WICK,
        PoiType.BEARISH_PRESSURE_WICK,
        PoiType.HAMMER,
        PoiType.SHOOTING_STAR,
        PoiType.BULLISH_ENGULFING,
        PoiType.BEARISH_ENGULFING,
        PoiType.MORNING_STAR,
        PoiType.EVENING_STAR,
    }
)


class OwnershipRelationship(StrEnum):
    PRIMARY = "PRIMARY"
    SUBORDINATE = "SUBORDINATE"
    INDEPENDENT = "INDEPENDENT"


class OwnershipReason(StrEnum):
    #: The member's complete source span lies inside the owner's base candles.
    CONTAINED_CANDLE_PATTERN = "CONTAINED_CANDLE_PATTERN"
    #: The member describes the SAME formation as the Base: identical complete
    #: formation span and identical zone. Not overlap -- one market decision
    #: carrying two semantic descriptions (author decision, 2026-09-23).
    CO_EXTENSIVE_FORMATION = "CO_EXTENSIVE_FORMATION"
    #: The owning Base formation itself.
    OWNS_CONTAINED_EVIDENCE = "OWNS_CONTAINED_EVIDENCE"


class FormationOwnership(NamedTuple):
    """One proven owner/member relationship, keyed by stable formation identity.

    A side-car record: no frozen observation is mutated to carry it.
    """

    owner_key: tuple[Any, ...]
    member_key: tuple[Any, ...]
    relationship: OwnershipRelationship
    reason: OwnershipReason
    #: Ownership is inert before this instant. The later of the two
    #: availabilities, so a late Base never suppresses an earlier pattern.
    active_from_utc: datetime


def formation_key(candidate: Any) -> tuple[Any, ...]:
    """The stable formation identity, identical to `leg_origin._formation_key`.

    `test_formation_ownership` asserts the two agree, so this cannot drift.
    """
    return (candidate.poi_type, candidate.source_candle_record_ids)


def _base_candle_ids(base: Any) -> tuple[UUID, ...]:
    """The BASE candles only — the departure is excluded, deliberately.

    `detect_bases` stores `(*base_candles, departure)`. The departure is the
    impulse that confirms the base, not part of the pause, and the ownership
    rule is that a member's source candle must be one of the BASE candles.
    A pattern formed on the departure candle describes the impulse and keeps
    its independence.
    """
    return tuple(base.source_candle_record_ids[:-1])


def _complete_formation_span_ids(base: Any) -> tuple[UUID, ...]:
    """The COMPLETE Base formation: consolidation candles AND the confirming
    departure.

    Deliberately a different concept from `_base_candle_ids`, and deliberately a
    separate function so neither can quietly become the other:

    * `_base_candle_ids` answers "is this pattern INSIDE the pause?"
    * this answers "is this pattern the SAME formation as the whole Base?"

    A pattern that ends on the departure candle is not inside the pause, so the
    containment rule cannot see it -- which is exactly the Evening Star case on
    the author's M15 formation.
    """
    return tuple(base.source_candle_record_ids)


def _is_co_extensive(member: Any, base: Any) -> bool:
    """EXACT equality, with no tolerance anywhere.

    The same complete formation span AND the same zone on both edges. No fuzzy
    price overlap, no ATR tolerance, no "almost the same zone" -- a near miss is
    two different reads of the market and keeps its independence.
    """
    if tuple(member.source_candle_record_ids) != _complete_formation_span_ids(base):
        return False
    return bool(
        member.zone_top == base.zone_top and member.zone_bottom == base.zone_bottom
    )


def _is_contained(member: Any, base_candle_ids: frozenset[UUID]) -> bool:
    """Every source candle of the member, not merely one that intersects."""
    member_ids = tuple(member.source_candle_record_ids)
    if not member_ids:
        return False
    return all(candle_id in base_candle_ids for candle_id in member_ids)


def resolve_formation_ownership(
    candidates: list[Any] | tuple[Any, ...],
    base_families: Mapping[tuple[Any, ...], Any] | None = None,
) -> tuple[FormationOwnership, ...]:
    """Decide, for every Base, which candle patterns it owns.

    Deterministic and side-effect free: returns relationship records sorted by
    (owner key, member key) and mutates nothing.
    """

    # ONLY standard-direction Bases may own evidence. A DROP_BASE_RALLY or
    # RALLY_BASE_DROP is not an authoritative Base under the approved
    # standard, so it must not subordinate anything; it is kept in the
    # candidate set for forensics and nothing more.
    def _family(candidate: Any) -> Any:
        # Downstream records (PoiObservation) do not carry the family: the
        # arrival is structural and is resolved after detection, so callers
        # working from observations pass the ledger's mapping instead.
        if base_families is not None:
            return base_families.get(formation_key(candidate))
        return getattr(candidate, "base_family", None)

    bases = [
        c
        for c in candidates
        if c.poi_type in BASE_TYPES and is_standard_base_family(_family(c))
    ]
    if not bases:
        return ()
    patterns = [c for c in candidates if c.poi_type in OWNABLE_PATTERN_TYPES]
    if not patterns:
        return ()

    records: list[FormationOwnership] = []
    for base in bases:
        base_ids = frozenset(_base_candle_ids(base))
        if not base_ids:
            continue
        owner_key = formation_key(base)
        owned = False
        for pattern in patterns:
            if pattern.direction is not base.direction:
                # "Compatible direction / decision". A pattern defending the
                # opposite side inside the same candles is a different read of
                # the market, not the same decision restated.
                continue
            if _is_contained(pattern, base_ids):
                reason = OwnershipReason.CONTAINED_CANDLE_PATTERN
            elif _is_co_extensive(pattern, base):
                reason = OwnershipReason.CO_EXTENSIVE_FORMATION
            else:
                continue
            records.append(
                FormationOwnership(
                    owner_key=owner_key,
                    member_key=formation_key(pattern),
                    relationship=OwnershipRelationship.SUBORDINATE,
                    reason=reason,
                    active_from_utc=max(
                        base.availability_time_utc, pattern.availability_time_utc
                    ),
                )
            )
            owned = True
        if owned:
            records.append(
                FormationOwnership(
                    owner_key=owner_key,
                    member_key=owner_key,
                    relationship=OwnershipRelationship.PRIMARY,
                    reason=OwnershipReason.OWNS_CONTAINED_EVIDENCE,
                    active_from_utc=base.availability_time_utc,
                )
            )

    records.sort(key=lambda r: (str(r.owner_key), str(r.member_key)))
    return tuple(records)


def subordinated_member_keys(
    ownership: tuple[FormationOwnership, ...], as_of_utc: datetime
) -> frozenset[tuple[Any, ...]]:
    """Members subordinate AS OF an instant. Honours `active_from_utc`."""
    return frozenset(
        record.member_key
        for record in ownership
        if record.relationship is OwnershipRelationship.SUBORDINATE
        and record.active_from_utc <= as_of_utc
    )
