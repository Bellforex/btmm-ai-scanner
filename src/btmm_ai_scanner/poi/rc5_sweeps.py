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
    "generating_candle",
    "replay_rc5_qualified_sweeps",
    "sweep_touched_the_level",
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


def _candidate_for_framework_event(
    event: Any,
    *,
    host: Rc5HostIdentity,
    ledger: Any,
    swings_by_id: Any,
    clusters_by_id: Any,
    trendlines_by_id: Any,
    ranges_by_id: Any,
) -> QualifiedSweepCandidate | None:
    """One framework sweep, qualified against the records known SO FAR."""
    built = build_sweep_candidates(
        (event,),
        (),
        host=host,
        ledger=ledger,
        swings_by_id=swings_by_id,
        clusters_by_id=clusters_by_id,
        trendlines_by_id=trendlines_by_id,
        ranges_by_id=ranges_by_id,
        observations_by_level_id={},
    )
    return built[0] if built else None


def replay_rc5_qualified_sweeps(
    candles: Any,
    configuration: Any,
    identity_provider_factory: Any,
    *,
    host_timeframe: Any,
    ledger: Any,
) -> tuple[QualifiedSweepEvent, ...]:
    """The canonical causal producer of RC5 qualified sweeps.

    WHY THIS EXISTS. The batch framework route builds liquidity levels from the
    FINAL swing / cluster / trendline collections, so anything that existed at
    an earlier prefix and was later superseded is invisible to it -- including
    levels that were genuinely swept while alive. Measured on M45: equal-level
    cluster 4a0ffb5e appeared at prefix 462, was swept at bar 487, and is absent
    from the final cluster set. Raw framework sweeps were 102 batch vs 123
    incremental, and the gap survived qualification as a real event present in
    one path only.

    EVERYTHING HERE IS DECIDED AT THE BAR IT HAPPENS, which is the part a
    whole-series pass gets wrong:

    * a sweep is qualified against the records discovered up to THAT prefix;
    * a POI far edge is registered, withdrawn and stepped per bar against the
      lifecycle state AS IT WAS THEN. A POI invalidated at bar 400 was still
      live at bar 100, and its sweep there is real;
    * deduplication runs over the candidates of that bar only, so a semantic
      link appearing later can never retroactively merge two historical events
      or move a primary owner. If a structural swing was the only qualified
      owner at event time, an equal pool forming later does not relabel it.

    Historical records are accumulated so a transient reference stays
    RESOLVABLE after it disappears. That is not the same as keeping it ACTIVE:
    the framework retires a level once it is swept or accepted through, and
    nothing here re-registers one.

    COST, stated rather than hidden: this walks the kernel one candle at a
    time. RC5 batch already pays that for provenance, and causal correctness is
    not negotiable against speed.
    """
    from btmm_ai_scanner.framework.engine import (
        FrameworkTracker,
        LiquidityLevel,
        advance_levels,
        framework_context_for,
    )
    from btmm_ai_scanner.framework.model import FrameworkConfiguration
    from btmm_ai_scanner.poi.rc5_host_identity import host_identity_from_candles
    from btmm_ai_scanner.poi.rc5_liquidity import (
        _POI_CARRIER_KIND,
        poi_boundary_level_id,
        poi_boundary_liquidity,
        poi_reference_is_active,
    )
    from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel

    candles = tuple(candles)
    if not candles:
        return ()

    host = host_identity_from_candles(host_timeframe, candles)
    tick = configuration.poi_configuration.minimum_price_tick
    framework_configuration = FrameworkConfiguration(minimum_price_tick=tick)
    kernel = IncrementalReplayKernel(
        (host_timeframe,), configuration, identity_provider_factory(), (), ledger
    )
    tracker = FrameworkTracker()

    # Historical resolution only -- first sighting wins, never resurrects.
    swings_by_id: dict[str, Any] = {}
    clusters_by_id: dict[str, Any] = {}
    trendlines_by_id: dict[str, Any] = {}
    ranges_by_id: dict[str, Any] = {}
    observations_by_level_id: dict[str, Any] = {}

    poi_active: list[Any] = []
    poi_registered: set[str] = set()
    framework_seen = 0
    events: list[QualifiedSweepEvent] = []

    for index, candle in enumerate(candles):
        kernel.advance_group({host_timeframe: (candle,)})
        analysis = kernel.finalize()
        context = framework_context_for(
            analysis, host_timeframe, candles[: index + 1], tracker
        )
        prefix = next(
            m for m in analysis.measurement_analyses if m.timeframe == host_timeframe
        )
        for swing in prefix.confirmed_swings:
            swings_by_id.setdefault(str(swing.record_id), swing)
        for cluster in prefix.equal_level_clusters:
            clusters_by_id.setdefault(str(cluster.record_id), cluster)
        for line in prefix.trendlines:
            trendlines_by_id.setdefault(str(line.record_id), line)
        for found in getattr(context, "ranges", ()) or ():
            ranges_by_id.setdefault(found.range_id, found)

        poi_analysis = analysis.poi_analysis
        states = {s.poi_record_id: s for s in poi_analysis.current_poi_states}
        for observation in poi_analysis.poi_observations:
            observations_by_level_id.setdefault(
                poi_boundary_level_id(observation), observation
            )

        # -- POI far edges, decided with THIS prefix's lifecycle state ------
        poi_raw: list[Any] = []
        for observation in sorted(
            poi_analysis.poi_observations,
            key=lambda o: (o.availability_time_utc, str(o.record_id)),
        ):
            if observation.availability_time_utc > candle.event_time_utc:
                continue
            level_id = poi_boundary_level_id(observation)
            if level_id in poi_registered:
                continue
            state = states.get(observation.record_id)
            if not poi_reference_is_active(observation, state, ledger):
                continue
            boundary = poi_boundary_liquidity(
                observation.direction, observation.zone_top, observation.zone_bottom
            )
            poi_registered.add(level_id)
            poi_active.append(
                LiquidityLevel(
                    level_id,
                    _POI_CARRIER_KIND[boundary.side],
                    boundary.side,
                    boundary.price,
                    observation.availability_time_utc,
                )
            )
        # Liveness is judged against THIS prefix's observations, never the
        # accumulated map. The accumulation exists to RESOLVE a historical
        # record, and using it here kept dead zones sweepable forever.
        #
        # Previous-day / previous-week levels are the proof: they are ROLLING.
        # Only two are live at any prefix on H3 while 88 distinct ones exist
        # across the walk, because each day's is replaced by a new record.
        # Resolving liveness through the accumulated map left yesterday's
        # previous-day high sweepable long after it stopped being the previous
        # day's high -- 13 such events on H3, each of which also stole the
        # dedup from the structural swing that legitimately owned the level.
        current_by_level_id = {
            poi_boundary_level_id(o): o for o in poi_analysis.poi_observations
        }
        still_live = []
        for level in poi_active:
            observation = current_by_level_id.get(level.level_id)
            if observation is None:
                continue
            if poi_reference_is_active(
                observation, states.get(observation.record_id), ledger
            ):
                still_live.append(level)
        poi_active = advance_levels(
            still_live, index, candle, None, framework_configuration, poi_raw
        )

        # -- qualify everything NEW on this bar ----------------------------
        new_framework = context.events[framework_seen:]
        framework_seen = len(context.events)

        bar_candidates: list[QualifiedSweepCandidate] = []
        for event in new_framework:
            candidate = _candidate_for_framework_event(
                event,
                host=host,
                ledger=ledger,
                swings_by_id=swings_by_id,
                clusters_by_id=clusters_by_id,
                trendlines_by_id=trendlines_by_id,
                ranges_by_id=ranges_by_id,
            )
            if candidate is not None:
                bar_candidates.append(candidate)
        if poi_raw:
            bar_candidates.extend(
                build_sweep_candidates(
                    (),
                    poi_raw,
                    host=host,
                    ledger=ledger,
                    swings_by_id=swings_by_id,
                    clusters_by_id=clusters_by_id,
                    trendlines_by_id=trendlines_by_id,
                    ranges_by_id=ranges_by_id,
                    observations_by_level_id=observations_by_level_id,
                )
            )

        # Dedup within THIS bar only: a link discovered later must never merge
        # events that are already history.
        if bar_candidates:
            events.extend(deduplicate_sweep_candidates(bar_candidates))

    return tuple(events)


#: WHICH TIMESTAMP MEANS WHAT, so forensic code never guesses again.
#:
#: ``QualifiedSweepEvent.event_time_utc`` is the generating candle's
#: ``availability_time_utc`` -- the instant the bar CLOSED and the sweep became
#: knowable. It is NOT the candle's ``event_time_utc`` (its open), and it is not
#: the reference's own source or pivot time.
#:
#: Indexing candles by ``event_time_utc`` and looking a sweep up by its
#: ``event_time_utc`` therefore lands on the NEIGHBOURING bar and invents
#: failures -- it produced a false "22 of 56 events did not wick through"
#: reading during verification. Use this helper instead of hand-rolling the
#: lookup.
def generating_candle(event: Any, candles: Any) -> Any:
    """The exact host candle whose price action produced ``event``.

    Raises rather than returning ``None``: a sweep that cannot be tied to a
    candle is a defect, not a missing optional.
    """
    for candle in candles:
        if candle.availability_time_utc == event.event_time_utc:
            return candle
    raise LookupError(
        f"no host candle closes at {event.event_time_utc.isoformat()} for "
        f"sweep of {event.raw_level_id}"
    )


def sweep_touched_the_level(event: Any, candle: Any) -> bool:
    """Did this candle actually trade through the reference?

    True for both frozen sweep types. A WICK_SWEEP fires on the bar that traded
    through; a CLOSE_THROUGH_RECLAIM fires on the RECLAIM bar, which in this
    engine is also a bar that traded beyond the level, so the same test holds
    for each. No custom mechanics -- this only reads what the frozen stepper
    already decided.
    """
    if event.side is LiquiditySide.BUY_SIDE:
        return candle.high > event.reference_price
    return candle.low < event.reference_price
