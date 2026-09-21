"""One driver that walks a series and compares the terminal oracle to P8.

Kept here rather than in a script so the permanent regression test and the
real-data host matrix exercise byte-identical code. The authoritative set comes
from ``LevelABar.suppressed_poi_ids`` -- never rebuilt locally.

It also reports COVERAGE: which lifecycle situations the series actually
exercised. A terminal proof run over a series where nothing is ever mitigated,
re-mitigated, suppressed or invalidated passes every assertion while proving
nothing, so the regression asserts coverage as well as cleanliness.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from tests.parity_support.level_a_replay import (
    build_scanner_configuration,
    iter_level_a_bars,
)
from tests.parity_support.rc5_terminal_oracle import (
    TerminalComparison,
    TerminalOracle,
    compare_terminals,
)

__all__ = ["TerminalProbe", "probe_terminals"]

_TICK = Decimal("0.01")

#: Every lifecycle situation a non-vacuous terminal proof must exercise.
REQUIRED_COVERAGE = frozenset(
    {
        "mitigation",
        "re_mitigation",
        "genuine_invalidation",
        "authority_suppression",
        "emitted_terminal",
    }
)


@dataclass(frozen=True)
class TerminalProbe:
    comparison: TerminalComparison
    #: POIs touched at least once while not genuinely invalidated.
    mitigated_and_alive: int = 0
    #: POIs touched more than once -- the re-mitigation case.
    re_mitigated: int = 0
    #: POIs that broke the far side and reclaimed it.
    false_break_reclaimed: int = 0
    #: POIs whose zone actually failed.
    genuinely_invalidated: int = 0
    #: POIs removed as same-origin subordinates on at least one bar.
    authority_suppressed: int = 0
    bars: int = 0
    exercised: frozenset[str] = field(default_factory=frozenset)

    @property
    def emitted_terminals(self) -> int:
        return self.comparison.actual_events

    @property
    def missing_coverage(self) -> frozenset[str]:
        return REQUIRED_COVERAGE - self.exercised


def probe_terminals(
    host_timeframe: Timeframe,
    host_series: Sequence[NormalizedCandle],
    context_series: Mapping[Timeframe, Sequence[NormalizedCandle]] | None = None,
) -> TerminalProbe:
    base = build_scanner_configuration(
        required_timeframes=frozenset({host_timeframe, *(context_series or {})}),
        optional_timeframes=frozenset(),
        minimum_price_tick=_TICK,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=_TICK, rc5_structural_origin=True
            )
        }
    )
    oracle = TerminalOracle()
    events: list = []
    poi_idx_by_id: dict = {}

    mitigated_alive: set = set()
    re_mitigated: set = set()
    false_break: set = set()
    genuine: set = set()
    suppressed_ever: set = set()
    bars = 0

    for bar in iter_level_a_bars(
        host_timeframe=host_timeframe,
        host_series=host_series,
        context_series=context_series or {},
        configuration=configuration,
        rc3_freshness=True,
        rc4_framework=True,
        rc5_authority=True,
    ):
        bars += 1
        oracle.observe(
            bar.bar_index,
            bar.availability_time_utc,
            bar.state_by_id,
            bar.evaluated_order,
            bar.suppressed_poi_ids,
        )
        suppressed_ever.update(bar.suppressed_poi_ids)
        for poi_id, state in bar.state_by_id.items():
            status = state.poi_lifecycle_status
            taps = int(getattr(state, "tap_count", 0) or 0)
            if status is PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED:
                genuine.add(poi_id)
                continue
            if status is PoiLifecycleStatus.FALSE_INVALIDATION_CONFIRMED:
                false_break.add(poi_id)
            if taps >= 1:
                mitigated_alive.add(poi_id)
            if taps >= 2:
                re_mitigated.add(poi_id)
        events.extend(bar.events)
        poi_idx_by_id.update(bar.poi_idx_by_id)

    comparison = compare_terminals(oracle, events, poi_idx_by_id)
    exercised = {
        name
        for name, seen in (
            ("mitigation", mitigated_alive),
            ("re_mitigation", re_mitigated),
            ("false_break_reclaim", false_break),
            ("genuine_invalidation", genuine),
            ("authority_suppression", suppressed_ever),
        )
        if seen
    }
    if comparison.actual_events:
        exercised.add("emitted_terminal")
    return TerminalProbe(
        comparison=comparison,
        mitigated_and_alive=len(mitigated_alive),
        re_mitigated=len(re_mitigated),
        false_break_reclaimed=len(false_break),
        genuinely_invalidated=len(genuine),
        authority_suppressed=len(suppressed_ever),
        bars=bars,
        exercised=frozenset(exercised),
    )
