"""One driver that walks a series and compares the terminal oracle to P8.

Kept here rather than in a script so the permanent regression test and the
real-data host matrix exercise byte-identical code. The authoritative set comes
from ``LevelABar.suppressed_poi_ids`` -- never rebuilt locally.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from decimal import Decimal

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from tests.parity_support.level_a_replay import (
    build_scanner_configuration,
    iter_level_a_bars,
)
from tests.parity_support.rc5_terminal_oracle import (
    TerminalComparison,
    TerminalOracle,
    compare_terminals,
)

__all__ = ["probe_terminals"]

_TICK = Decimal("0.01")


def probe_terminals(
    host_timeframe: Timeframe,
    host_series: Sequence[NormalizedCandle],
    context_series: Mapping[Timeframe, Sequence[NormalizedCandle]] | None = None,
) -> TerminalComparison:
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
    for bar in iter_level_a_bars(
        host_timeframe=host_timeframe,
        host_series=host_series,
        context_series=context_series or {},
        configuration=configuration,
        rc3_freshness=True,
        rc4_framework=True,
        rc5_authority=True,
    ):
        oracle.observe(
            bar.bar_index,
            bar.availability_time_utc,
            bar.state_by_id,
            bar.evaluated_order,
            bar.suppressed_poi_ids,
        )
        events.extend(bar.events)
        poi_idx_by_id.update(bar.poi_idx_by_id)
    return compare_terminals(oracle, events, poi_idx_by_id)
