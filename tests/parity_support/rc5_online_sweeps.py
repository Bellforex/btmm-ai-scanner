"""An independently written ONLINE engine for RC5 qualified sweeps.

Phase 18C requires the canonical producer to be checked against a genuinely
online execution rather than against a wrapper around itself. This is that
engine: one candle in, the events for that candle out, no lookahead and no
final-state pass.

WHERE THE INDEPENDENCE ACTUALLY IS. Both sides necessarily drive the same
engines -- there is one kernel and one FrameworkTracker -- and both use the
same deterministic leaf helpers for qualification and dedup, which the author
explicitly allows. What differs is the BOOKKEEPING, which is where the causal
bugs have all lived so far:

* the producer detects new framework sweeps with an integer watermark into
  ``context.events``; this engine tracks them by EVENT IDENTITY, so a
  watermark slip or a re-emitted event shows up as a mismatch rather than
  silently agreeing;
* the producer keeps one POI level book across the whole walk; this engine
  rebuilds its live POI set from the current prefix each bar and diffs it, so
  a stale registration or a missed withdrawal diverges;
* the producer returns one list at the end; this engine emits per bar, so the
  ONLINE property -- events are final when their bar closes -- is structural
  here rather than asserted.

If the two agree exactly, the producer's bookkeeping is right, not merely
self-consistent.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from btmm_ai_scanner.framework.engine import (
    FrameworkTracker,
    LiquidityLevel,
    advance_levels,
    framework_context_for,
)
from btmm_ai_scanner.framework.model import FrameworkConfiguration
from btmm_ai_scanner.poi.rc5_host_identity import Rc5HostIdentity
from btmm_ai_scanner.poi.rc5_liquidity import (
    _POI_CARRIER_KIND,
    poi_boundary_level_id,
    poi_boundary_liquidity,
    poi_reference_is_active,
)
from btmm_ai_scanner.poi.rc5_sweeps import (
    QualifiedSweepEvent,
    build_sweep_candidates,
    deduplicate_sweep_candidates,
)
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel

__all__ = ["Rc5OnlineSweepEngine"]


def _raw_identity(event: Any) -> tuple[Any, ...]:
    """Identity of a raw framework sweep, independent of list position."""
    return (
        event.level_id,
        event.bar_index,
        event.sweep_type.value,
        str(event.level_price),
        event.availability_time_utc.isoformat(),
    )


@dataclass
class Rc5OnlineSweepEngine:
    """Chronological, one candle at a time, no lookahead."""

    configuration: Any
    identity_provider: Any
    host: Rc5HostIdentity
    host_timeframe: Any

    _kernel: Any = field(default=None, init=False)
    _tracker: FrameworkTracker = field(default_factory=FrameworkTracker, init=False)
    _index: int = field(default=0, init=False)
    _candles: list = field(default_factory=list, init=False)
    _seen_raw: set = field(default_factory=set, init=False)
    _poi_levels: dict = field(default_factory=dict, init=False)
    _poi_retired: set = field(default_factory=set, init=False)
    #: historical resolution only -- never re-registers anything
    _swings: dict = field(default_factory=dict, init=False)
    _clusters: dict = field(default_factory=dict, init=False)
    _trendlines: dict = field(default_factory=dict, init=False)
    _ranges: dict = field(default_factory=dict, init=False)
    _observations: dict = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        self._kernel = IncrementalReplayKernel(
            (self.host_timeframe,),
            self.configuration,
            self.identity_provider,
            (),
            self.ledger,
        )

    ledger: Any = None

    def advance(self, candle: Any) -> tuple[QualifiedSweepEvent, ...]:
        """Consume one candle; return the events that became history on it."""
        self._candles.append(candle)
        index = self._index
        self._index += 1

        self._kernel.advance_group({self.host_timeframe: (candle,)})
        analysis = self._kernel.finalize()
        context = framework_context_for(
            analysis, self.host_timeframe, tuple(self._candles), self._tracker
        )
        prefix = next(
            m
            for m in analysis.measurement_analyses
            if m.timeframe == self.host_timeframe
        )
        for swing in prefix.confirmed_swings:
            self._swings.setdefault(str(swing.record_id), swing)
        for cluster in prefix.equal_level_clusters:
            self._clusters.setdefault(str(cluster.record_id), cluster)
        for line in prefix.trendlines:
            self._trendlines.setdefault(str(line.record_id), line)
        for found in getattr(context, "ranges", ()) or ():
            self._ranges.setdefault(found.range_id, found)

        poi_analysis = analysis.poi_analysis
        states = {s.poi_record_id: s for s in poi_analysis.current_poi_states}
        for observation in poi_analysis.poi_observations:
            self._observations.setdefault(
                poi_boundary_level_id(observation), observation
            )

        # -- POI book, rebuilt from THIS prefix and diffed -----------------
        should_be_live: dict[str, Any] = {}
        for observation in poi_analysis.poi_observations:
            if observation.availability_time_utc > candle.event_time_utc:
                continue
            level_id = poi_boundary_level_id(observation)
            if level_id in self._poi_retired:
                continue
            state = states.get(observation.record_id)
            if not poi_reference_is_active(observation, state, self.ledger):
                continue
            should_be_live[level_id] = observation

        for level_id in sorted(set(self._poi_levels) - set(should_be_live)):
            # withdrawn because the POI stopped being a live independent zone
            self._poi_levels.pop(level_id, None)
            self._poi_retired.add(level_id)
        for level_id, observation in sorted(should_be_live.items()):
            if level_id in self._poi_levels:
                continue
            boundary = poi_boundary_liquidity(
                observation.direction, observation.zone_top, observation.zone_bottom
            )
            self._poi_levels[level_id] = LiquidityLevel(
                level_id,
                _POI_CARRIER_KIND[boundary.side],
                boundary.side,
                boundary.price,
                observation.availability_time_utc,
            )

        poi_raw: list = []
        survivors = advance_levels(
            [self._poi_levels[k] for k in sorted(self._poi_levels)],
            index,
            candle,
            None,
            FrameworkConfiguration(
                minimum_price_tick=(
                    self.configuration.poi_configuration.minimum_price_tick
                )
            ),
            poi_raw,
        )
        surviving = {level.level_id for level in survivors}
        for level_id in sorted(set(self._poi_levels) - surviving):
            # consumed by the framework's own mechanics: swept, or accepted
            # through. Retired, and never re-registered.
            self._poi_levels.pop(level_id, None)
            self._poi_retired.add(level_id)

        # -- framework sweeps that are NEW, by identity --------------------
        fresh = []
        for event in context.events:
            identity = _raw_identity(event)
            if identity in self._seen_raw:
                continue
            self._seen_raw.add(identity)
            fresh.append(event)

        candidates = list(
            build_sweep_candidates(
                tuple(fresh),
                tuple(poi_raw),
                host=self.host,
                ledger=self.ledger,
                swings_by_id=self._swings,
                clusters_by_id=self._clusters,
                trendlines_by_id=self._trendlines,
                ranges_by_id=self._ranges,
                observations_by_level_id=self._observations,
            )
        )
        if not candidates:
            return ()
        return deduplicate_sweep_candidates(candidates)
