"""RC5 POI AUTHORITY: one structural decision origin -> one primary reversal POI.

Author decision, 2026-09-20. RC5 profile only; RC4 (``2f1d2b9``) stays frozen.

WHY THIS EXISTS
---------------
Every detector that geometrically matches fires, so a single reversal can be
described several times over -- on the author's M45 example one BUY-TO-SELL
transition was accompanied by two SHOOTING STARs drawn *inside* its zone and a
BEARISH PRESSURE WICK on the next bar, and all four were drawn as independent,
tradeable POIs. The chart must render the winner, not every synonym.

THE CLUSTER KEY (author correction, measured, not assumed)
-----------------------------------------------------------
Shared ``availability_time_utc`` is **corroborating evidence only**. It is NOT
the key, and neither is zone overlap. Both were measured against live FXCM data
and both fail:

* H3, availability 2026-08-31 04:00: nine bearish candidates share that bar.
  Their sources span six days and their zones span 240 points -- a descending
  staircase of pressure wicks released by one late break. Clustering on
  availability would have suppressed eight valid POIs.
* H4, availability 2026-08-05 18:00: fifteen bullish candidates share that bar,
  sources spanning five weeks and 220 points.
* Conversely dozens of *unrelated* POIs months apart overlap the same price
  band, so geometry alone is just as wrong.

A cluster therefore requires **all** of:

1. same ``direction``;
2. same structural decision origin -- either the same formation candle, or the
   same ``(confirming transition, origin swing)`` pair that the frozen
   reversal-context gate in ``poi/leg_origin.py`` already computes;
3. a formation relationship -- the subordinate's zone is contained in the
   dominant's zone (or they share the formation candle).

THE LADDER
----------
Applied ONLY inside a proven cluster, and ONLY among candidates that are
themselves valid (a candidate that fails its own qualification cannot suppress
a valid lower-ranked one). A lower-ranked POI at a genuinely separate origin
always survives.

FVG IS NOT IN THE LADDER
------------------------
An imbalance is a different family. It is suppressed only when it shares the
origin AND contributes no imbalance region outside the dominant zone. Both live
counterexamples keep their FVG: the M45 SELL FVG (availability one bar later,
extending 37 points below the B2S zone) and the H3 SHOOTING STAR + SELL FVG
pair that share a source bar but whose zones do not overlap at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any
from uuid import UUID

from btmm_ai_scanner.poi.enums import PoiDirection, PoiType

__all__ = [
    "FVG_TYPES",
    "REVERSAL_LADDER",
    "REVERSAL_TYPES",
    "AuthorityDecision",
    "AuthorityReason",
    "OriginClusterKey",
    "arbitrate_cluster",
    "contains_zone",
    "ladder_rank",
    "zones_overlap",
]


#: Author-directed reversal authority ladder (1 = highest). Applies only inside
#: one proven same-origin cluster; it is NOT a global type ranking.
REVERSAL_LADDER: dict[PoiType, int] = {
    PoiType.BUY_TO_SELL_CANDLE: 1,
    PoiType.SELL_TO_BUY_CANDLE: 1,
    PoiType.BUY_ORDER_BLOCK: 2,
    PoiType.SELL_ORDER_BLOCK: 2,
    PoiType.MORNING_STAR: 3,
    PoiType.EVENING_STAR: 3,
    PoiType.BULLISH_ENGULFING: 4,
    PoiType.BEARISH_ENGULFING: 4,
    PoiType.HAMMER: 5,
    PoiType.SHOOTING_STAR: 5,
    # RC5 adds PoiType.DOJI at rank 6 once the type exists.
    PoiType.BULLISH_PRESSURE_WICK: 7,
    PoiType.BEARISH_PRESSURE_WICK: 7,
}

REVERSAL_TYPES = frozenset(REVERSAL_LADDER)

FVG_TYPES = frozenset({PoiType.BUY_FAIR_VALUE_GAP, PoiType.SELL_FAIR_VALUE_GAP})


class AuthorityReason(StrEnum):
    PRIMARY = "PRIMARY"
    SAME_ORIGIN_SUBORDINATE = "SAME_ORIGIN_SUBORDINATE"
    SUBORDINATE_IMBALANCE = "SUBORDINATE_IMBALANCE"
    INDEPENDENT = "INDEPENDENT"


class ClusterProvenance(StrEnum):
    """How a cluster was identified. STRUCTURAL always wins (author guard,
    2026-09-20): when authoritative structural identifiers exist they take
    precedence, and a same-candle relationship may never override valid
    structural separation."""

    STRUCTURAL = "STRUCTURAL"
    FORMATION_CANDLE = "FORMATION_CANDLE"


@dataclass(frozen=True)
class OriginClusterKey:
    """A structural decision origin.

    ``STRUCTURAL`` provenance names the leg origin the frozen reversal-context
    gate assigns -- ``(confirming transition, broken swing, origin swing)`` --
    and covers the case where the members sit on *different* candles of one
    reversal, as on the author's M45 example.

    ``FORMATION_CANDLE`` is the weak fallback used ONLY when structural
    provenance is unavailable. One candle can legitimately produce a reversal
    formation AND a separate imbalance, so a shared candle alone is never
    enough to merge semantic families: a formation-candle cluster arbitrates
    reversal synonyms only and never touches an FVG.
    """

    direction: PoiDirection
    formation_candle_id: UUID | None = None
    transition_break_candle_id: UUID | None = None
    transition_broken_swing_id: UUID | None = None
    origin_swing_id: UUID | None = None

    @property
    def provenance(self) -> ClusterProvenance:
        if self.origin_swing_id is not None:
            return ClusterProvenance.STRUCTURAL
        return ClusterProvenance.FORMATION_CANDLE

    @property
    def is_structural(self) -> bool:
        """True when the key names a leg origin rather than a single candle."""
        return self.provenance is ClusterProvenance.STRUCTURAL


@dataclass(frozen=True)
class AuthorityDecision:
    candidate: Any
    reason: AuthorityReason
    cluster: OriginClusterKey | None = None
    primary_type: PoiType | None = None


def ladder_rank(poi_type: PoiType) -> int:
    """Authority rank inside a cluster; unranked types sort last."""
    return REVERSAL_LADDER.get(poi_type, 99)


def contains_zone(outer: Any, inner: Any) -> bool:
    """Is ``inner``'s zone wholly inside ``outer``'s? The strict relationship,
    required before an FVG may be called a by-product: an imbalance that is not
    wholly inside the reversal still contributes an imbalance region of its own.
    """
    return Decimal(inner.zone_bottom) >= Decimal(outer.zone_bottom) and Decimal(
        inner.zone_top
    ) <= Decimal(outer.zone_top)


def zones_overlap(a: Any, b: Any) -> bool:
    """Do the two zones share any price? The relationship used between reversal
    synonyms at one structural origin.

    Containment is too strict here, and the author's M45 case is exactly why:
    the BEARISH PRESSURE WICK sits on the swing that COMPLETES the reversal
    (4485.61-4490.85), whose high is above the B2S zone top (4486.42). The two
    describe one decision and overlap, but neither contains the other. The same
    geometry that made source-candle matching fail for B2S makes containment
    fail here.

    Geometry still never clusters on its own -- the members must already share
    a structural origin. This only decides whether two co-origin formations are
    describing the same decision or two separate ones.
    """
    return Decimal(a.zone_bottom) <= Decimal(b.zone_top) and Decimal(
        b.zone_bottom
    ) <= Decimal(a.zone_top)


def _order(candidate: Any) -> tuple[int, str, str]:
    """Deterministic ordering: ladder rank, then earliest formation, then id."""
    return (
        ladder_rank(candidate.poi_type),
        candidate.candidate_event_time_utc.isoformat(),
        "".join(str(c) for c in candidate.source_candle_record_ids),
    )


def arbitrate_cluster(
    members: list[Any],
    cluster: OriginClusterKey,
) -> list[AuthorityDecision]:
    """Pick one primary reversal POI for ``members`` (already proven to share
    ``cluster``) and classify the rest.

    ``members`` must contain only candidates that passed their own
    qualification -- an invalid higher-ranked candidate never reaches here and
    so can never suppress a valid lower-ranked one.

    Non-reversal families (imbalances, bases, structural zones) are never
    ranked. An FVG is refused only when it is geometrically inside the primary
    and therefore contributes no imbalance region of its own.
    """
    reversals = [c for c in members if c.poi_type in REVERSAL_TYPES]
    others = [c for c in members if c.poi_type not in REVERSAL_TYPES]
    decisions: list[AuthorityDecision] = []

    if not reversals:
        return [AuthorityDecision(c, AuthorityReason.INDEPENDENT) for c in members]

    reversals.sort(key=_order)
    primary = reversals[0]
    decisions.append(AuthorityDecision(primary, AuthorityReason.PRIMARY, cluster))

    for candidate in reversals[1:]:
        # Same origin AND overlapping price: one decision described twice.
        # Same origin but spatially separate: two decisions, both survive.
        subordinate = candidate.direction is primary.direction and zones_overlap(
            primary, candidate
        )
        decisions.append(
            AuthorityDecision(
                candidate,
                AuthorityReason.SAME_ORIGIN_SUBORDINATE
                if subordinate
                else AuthorityReason.INDEPENDENT,
                cluster if subordinate else None,
                primary.poi_type if subordinate else None,
            )
        )

    for candidate in others:
        # Author guard: a shared formation candle is NOT authority. One candle
        # can produce a reversal AND an independent imbalance, so only a
        # STRUCTURAL cluster may ever subordinate an FVG.
        by_product = (
            cluster.is_structural
            and candidate.poi_type in FVG_TYPES
            and candidate.direction is primary.direction
            and contains_zone(primary, candidate)
        )
        decisions.append(
            AuthorityDecision(
                candidate,
                AuthorityReason.SUBORDINATE_IMBALANCE
                if by_product
                else AuthorityReason.INDEPENDENT,
                cluster if by_product else None,
                primary.poi_type if by_product else None,
            )
        )
    return decisions
