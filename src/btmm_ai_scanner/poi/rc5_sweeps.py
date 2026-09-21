"""RC5 qualified sweeps: one user-facing event per physical liquidity action.

One real market action can hit several qualified references at once -- a swing
high that is also a member of an equal-high pool, a range boundary whose source
IS that swing, a shooting star whose far edge sits on the same pivot. Printing
"BSL SWEEP" three times for one action is wrong, so those collapse to one
event with the others retained as corroboration.

WHAT MAY COLLAPSE, AND WHAT MAY NOT. Measured on all five hosts before any of
this was written:

* MERGE requires a SHARED LEVEL SOURCE -- a relationship the models already
  carry -- AND exactly equal price. Both, never either alone.
* Same bar is not enough. One candle can legitimately sweep several different
  BSL levels, and 13-22 groups per host do exactly that.
* Partial overlap is not enough. Two trendlines sharing one anchor swing
  projected to 4645.215 and 4645.314 on M15 -- same anchor, different levels.
* Exact price alone is not enough, and is not used alone anywhere here.

NO PRICE TOLERANCE EXISTS IN THIS MODULE. Exact equality is a confirmation on
top of a semantic link, never a proximity test. The measured collision matrix
had zero same-price-without-link cases on M5, M15, H3, H4 and M45, so none is
needed -- and the one time that class appeared it was a defect in RC5's own
level identity, not a missing relationship.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

from btmm_ai_scanner.framework.model import LiquiditySide
from btmm_ai_scanner.poi.rc5_host_identity import Rc5HostIdentity
from btmm_ai_scanner.poi.rc5_liquidity import SweepReferenceKind

__all__ = [
    "OWNER_PRIORITY",
    "QualifiedSweepCandidate",
    "QualifiedSweepEvent",
    "build_sweep_candidates",
    "deduplicate_sweep_candidates",
]

#: Which reference owns the label when several describe one liquidity action.
#: Applied ONLY after identity equivalence is proven -- priority never creates
#: the equivalence, it only resolves an already-proven collision.
#:
#: The ordering follows how directly a reference expresses the liquidity: an
#: active POI far edge is where protective orders actually rest; an equal-level
#: pool expresses "a pool of stops" better than any one of its component
#: swings; a range boundary is a more meaningful level than the swing that
#: happens to source it; and a trendline is the most derived of all.
OWNER_PRIORITY: dict[SweepReferenceKind, int] = {
    SweepReferenceKind.POI_BOUNDARY: 1,
    SweepReferenceKind.EQUAL_HIGH_LOW: 2,
    SweepReferenceKind.RANGE_BOUNDARY: 3,
    SweepReferenceKind.SUPPORT_RESISTANCE: 4,
    SweepReferenceKind.STRUCTURAL_SWING: 5,
    SweepReferenceKind.TRENDLINE: 6,
}


@dataclass(frozen=True)
class QualifiedSweepCandidate:
    """One qualified reference that a raw sweep hit, before deduplication."""

    host: Rc5HostIdentity
    event_time_utc: datetime
    side: LiquiditySide
    kind: SweepReferenceKind
    reference_id: tuple[Any, ...]
    price: Decimal
    raw_sweep_type: str
    raw_level_id: str
    #: Identities of the underlying level this reference stands for -- swing
    #: ids, pivot candle ids, cluster components, a range's source swing. Two
    #: candidates sharing ANY of these name the same level.
    level_sources: frozenset[Any] = field(default_factory=frozenset)
    why_qualified: str = ""


@dataclass(frozen=True)
class QualifiedSweepEvent:
    """One physical liquidity action, as a student should see it."""

    host: Rc5HostIdentity
    event_time_utc: datetime
    side: LiquiditySide
    primary_kind: SweepReferenceKind
    primary_reference_id: tuple[Any, ...]
    reference_price: Decimal
    raw_sweep_type: str
    raw_level_id: str
    #: ``(kind, reference_id)`` for every reference that corroborated this one
    #: action. Internal evidence; the user sees one label.
    corroborating: tuple[tuple[SweepReferenceKind, tuple[Any, ...]], ...] = ()
    why_qualified: str = ""

    @property
    def label(self) -> str:
        """``BSL`` or ``SSL``."""
        return "BSL" if self.side is LiquiditySide.BUY_SIDE else "SSL"

    @property
    def event_id(self) -> tuple[Any, ...]:
        """Stable identity. Host-local by construction, so the same price at
        the same instant on M15 and M45 are different events -- and never a
        runtime index."""
        return (
            *self.host.key,
            self.event_time_utc.isoformat(),
            self.side.value,
            self.primary_kind.value,
            *self.primary_reference_id,
        )


def _merge_groups(candidates: list[QualifiedSweepCandidate]) -> list[list[int]]:
    """Connected components over "shares a level source".

    Union-find rather than pairwise grouping because the relation is
    transitive in practice: a swing links to the pool that contains it and to
    the range boundary it sources, so all three are one level even though the
    pool and the range may share nothing directly.
    """
    parent = list(range(len(candidates)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            if candidates[i].level_sources & candidates[j].level_sources:
                union(i, j)

    components: dict[int, list[int]] = {}
    for index in range(len(candidates)):
        components.setdefault(find(index), []).append(index)
    return [sorted(members) for _, members in sorted(components.items())]


def _order_key(candidate: QualifiedSweepCandidate) -> tuple[Any, ...]:
    """Deterministic ordering: priority first, then stable identity so the
    winner never depends on input order."""
    return (
        OWNER_PRIORITY.get(candidate.kind, 99),
        candidate.kind.value,
        tuple(str(p) for p in candidate.reference_id),
    )


def deduplicate_sweep_candidates(
    candidates: Any,
) -> tuple[QualifiedSweepEvent, ...]:
    """Collapse proven duplicates; keep everything else distinct.

    Grouping is by ``(host, time, side, EXACT price)`` first, which is what
    keeps different levels on one candle apart -- they differ in price, so they
    never reach the same bucket. Within a bucket, only candidates that share a
    level source merge; same-price-but-unrelated candidates stay separate
    rather than being silently joined.
    """
    buckets: dict[tuple[Any, ...], list[QualifiedSweepCandidate]] = {}
    for candidate in candidates:
        key = (
            *candidate.host.key,
            candidate.event_time_utc.isoformat(),
            candidate.side.value,
            str(candidate.price),
        )
        buckets.setdefault(key, []).append(candidate)

    events: list[QualifiedSweepEvent] = []
    for _key, members in sorted(buckets.items()):
        for component in _merge_groups(members):
            group = sorted((members[i] for i in component), key=_order_key)
            primary = group[0]
            # Corroboration is OTHER references that independently named this
            # level. The same reference reaching here through two pipelines is
            # not corroboration: an equal-level pool arrives both as the
            # framework's "E" level and as a reference-zone POI carrying the
            # SAME cluster id, and listing it twice would overstate the
            # evidence behind the event.
            primary_identity = (primary.kind, tuple(primary.reference_id))
            seen: set[tuple[Any, ...]] = {primary_identity}
            corroborating: list[tuple[SweepReferenceKind, tuple[Any, ...]]] = []
            for other in group[1:]:
                identity = (other.kind, tuple(other.reference_id))
                if identity in seen:
                    continue
                seen.add(identity)
                corroborating.append(identity)
            corroborating_final = tuple(corroborating)
            events.append(
                QualifiedSweepEvent(
                    host=primary.host,
                    event_time_utc=primary.event_time_utc,
                    side=primary.side,
                    primary_kind=primary.kind,
                    primary_reference_id=tuple(primary.reference_id),
                    reference_price=primary.price,
                    raw_sweep_type=primary.raw_sweep_type,
                    raw_level_id=primary.raw_level_id,
                    corroborating=corroborating_final,
                    why_qualified=primary.why_qualified,
                )
            )
    events.sort(key=lambda e: (e.event_time_utc, e.side.value, e.event_id))
    return tuple(events)


def _swing_sources(swing: Any) -> set[Any]:
    """A swing's level identities: itself, plus the candles that formed its
    pivot. The pivot candle is what links it to a reversal POI whose far edge
    sits on the same extreme."""
    if swing is None:
        return set()
    return {str(swing.record_id)} | {
        str(c) for c in getattr(swing, "pivot_candle_record_ids", ())
    }


def build_sweep_candidates(
    framework_events: Any,
    poi_events: Any,
    *,
    host: Rc5HostIdentity,
    ledger: Any,
    swings_by_id: Any,
    clusters_by_id: Any,
    trendlines_by_id: Any,
    ranges_by_id: Any,
    observations_by_level_id: Any,
) -> tuple[QualifiedSweepCandidate, ...]:
    """Every qualified reference a raw sweep hit, with its level sources.

    The level sources are what deduplication reasons over, and every one of
    them is an existing relationship read off the models -- never proximity:

    * a structural swing contributes itself and its pivot candles;
    * an equal-level pool contributes its component swings, and their pivot
      candles, because the pool IS those swings' shared level;
    * a range boundary contributes the swing named by ``upper_source`` /
      ``lower_source``, which the framework already records;
    * a POI far edge contributes its own level id, its source candles and its
      ``source_measurement_record_ids`` -- the S/R zone or cluster it came
      from, for reference-zone families.

    A trendline contributes only ITSELF. Its anchors are deliberately excluded:
    two lines sharing one anchor are different levels, measured at 4645.215 vs
    4645.314 on M15, and contributing anchors here would merge them.
    """
    from btmm_ai_scanner.poi.rc5_liquidity import (
        poi_reference_source_identity,
        qualify_sweep_reference,
        reference_kind_of_poi,
    )

    out: list[QualifiedSweepCandidate] = []

    for event in framework_events:
        verdict = qualify_sweep_reference(
            event,
            ledger,
            host,
            swings_by_id=swings_by_id,
            trendlines_by_id=trendlines_by_id,
        )
        if not verdict.is_qualified:
            continue
        reference = verdict.reference
        identity = tuple(str(p) for p in reference.source_identity)
        sources: set[Any] = set(identity)

        if reference.kind is SweepReferenceKind.STRUCTURAL_SWING:
            sources |= _swing_sources(swings_by_id.get(identity[0]))
        elif reference.kind is SweepReferenceKind.EQUAL_HIGH_LOW:
            cluster = clusters_by_id.get(identity[0])
            for swing_id in getattr(cluster, "component_swing_record_ids", ()):
                sources.add(str(swing_id))
                sources |= _swing_sources(swings_by_id.get(str(swing_id)))
        elif reference.kind is SweepReferenceKind.RANGE_BOUNDARY:
            trading_range = ranges_by_id.get(identity[0])
            if trading_range is not None:
                source = (
                    trading_range.upper_source
                    if identity[1] == "RANGE_HIGH"
                    else trading_range.lower_source
                )
                sources.add(str(source))
                sources |= _swing_sources(swings_by_id.get(str(source)))
        # TRENDLINE contributes only itself -- see the docstring.

        out.append(
            QualifiedSweepCandidate(
                host=host,
                event_time_utc=event.availability_time_utc,
                side=event.side,
                kind=reference.kind,
                reference_id=identity,
                price=event.level_price,
                raw_sweep_type=event.sweep_type.value,
                raw_level_id=event.level_id,
                level_sources=frozenset(sources),
                why_qualified=reference.reason,
            )
        )

    for event in poi_events:
        observation = observations_by_level_id.get(event.level_id)
        if observation is None:
            continue
        identity = tuple(str(p) for p in poi_reference_source_identity(observation))
        sources = {event.level_id, *identity}
        sources |= {
            str(c) for c in getattr(observation, "source_candle_record_ids", ())
        }
        sources |= {
            str(s) for s in getattr(observation, "source_measurement_record_ids", ())
        }
        out.append(
            QualifiedSweepCandidate(
                host=host,
                event_time_utc=event.availability_time_utc,
                side=event.side,
                # the SEMANTIC family, not the borrowed stepper kind
                kind=reference_kind_of_poi(observation),
                reference_id=identity,
                price=event.level_price,
                raw_sweep_type=event.sweep_type.value,
                raw_level_id=event.level_id,
                level_sources=frozenset(sources),
                why_qualified="ACTIVE_POI_FAR_EDGE",
            )
        )

    return tuple(out)
