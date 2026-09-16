"""Scanner adapter — the ONLY module in ``botdryrun`` that drives the scanner.

It wraps ``tests.parity_support.level_a_replay.iter_level_a_bars`` (the one
orchestration of the frozen scanner: incremental kernel -> RC3 freshness ->
P5 active-POI loop -> P8 alert engine) and converts each ``LevelABar`` into a
bot-domain ``ScannerBarSnapshot``. It makes no rule decision of its own:

* POI detection / freshness / terminal reason -> copied from the kernel;
* P5 permission / score / lifecycle -> copied from ``BtrcDecision``;
* P8 events -> copied from the alert engine, in native order;
* the canonical P3/P5/P8 row lines are rendered with the RC3 daily
  authority's own row builders, so the bot's daily digests are the
  authority's daily digests (asserted in ``tests/bot``).

``rc3_freshness=True`` and ``WarmupFeedPolicy.AVAILABILITY`` are fixed: the
RC3 contract is the only contract this bot consumes.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from uuid import UUID

from botdryrun.domain import (
    DecisionView,
    EventView,
    PoiView,
    ScannerBarSnapshot,
    ScannerSource,
    compute_bar_digest,
)
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from tests.parity_support.level_a_replay import (
    DEFAULT_MINIMUM_PRICE_TICK,
    LevelABar,
    WarmupFeedPolicy,
    build_scanner_configuration,
    iter_level_a_bars,
)
from tests.parity_support.p5_wire_normalized_replay import PERMISSION_CODE
from tests.parity_support.p8_alert_oracle import ACTIONABLE_PERMISSIONS
from tests.parity_support.rc3_daily_authority import (
    P3_FIELDS,
    P5_FIELDS,
    P8_FIELDS,
    _canonical_line,
    _p3_row,
    _p5_row,
    trading_day_of,
)

__all__ = ["LevelAScannerSource", "ScannerSource", "build_configuration"]


def build_configuration(
    host_timeframe: Timeframe, context_timeframes: Sequence[Timeframe]
) -> ScannerConfiguration:
    return build_scanner_configuration(
        required_timeframes=frozenset({host_timeframe}),
        optional_timeframes=frozenset(context_timeframes),
        minimum_price_tick=DEFAULT_MINIMUM_PRICE_TICK,
    )


def _iso(value: object) -> str | None:
    if value is None:
        return None
    iso = getattr(value, "isoformat", None)
    return str(iso()) if iso is not None else str(value)


class LevelAScannerSource:
    def __init__(self, context_timeframes: Sequence[Timeframe] | None = None) -> None:
        self._context_timeframes = context_timeframes

    def iterate(
        self,
        host_timeframe: Timeframe,
        host_series: Sequence[NormalizedCandle],
        context_series: Mapping[Timeframe, Sequence[NormalizedCandle]],
    ) -> Iterator[ScannerBarSnapshot]:
        context_tfs = (
            tuple(self._context_timeframes)
            if self._context_timeframes is not None
            else tuple(context_series)
        )
        configuration = build_configuration(host_timeframe, context_tfs)
        seen_registry: set[UUID] = set()
        for bar in iter_level_a_bars(
            host_timeframe=host_timeframe,
            host_series=host_series,
            context_series=context_series,
            configuration=configuration,
            rc3_freshness=True,
            warmup_feed_policy=WarmupFeedPolicy.AVAILABILITY,
        ):
            yield _snapshot(bar, seen_registry)


def _snapshot(bar: LevelABar, seen_registry: set[UUID]) -> ScannerBarSnapshot:
    day = trading_day_of(bar.candle.event_time_utc)

    new_registry = 0
    for record_id in bar.observation_by_id:
        if record_id not in seen_registry:
            seen_registry.add(record_id)
            new_registry += 1

    fresh = mitigated = invalidated = 0
    for state in bar.analysis.poi_analysis.current_poi_states:
        if state.fresh_active:
            fresh += 1
        elif state.terminal_reason is not None:
            if state.terminal_reason.value == "MITIGATED":
                mitigated += 1
            else:
                invalidated += 1

    pois: list[PoiView] = []
    for record_id, poi in bar.observation_by_id.items():
        poi_state = bar.state_by_id.get(record_id)
        pois.append(
            PoiView(
                record_id=str(record_id),
                poi_idx=bar.poi_idx_by_id.get(record_id),
                poi_type=poi.poi_type.value,
                direction=poi.direction.value,
                family=poi.family.value,
                source_timeframe=poi.source_timeframe.value,
                effective_timeframe=poi.effective_timeframe.value,
                zone_top=poi.zone_top,
                zone_bottom=poi.zone_bottom,
                source_time_utc=poi.candidate_event_time_utc.isoformat(),
                availability_time_utc=poi.availability_time_utc.isoformat(),
                fresh_active=poi_state.fresh_active if poi_state is not None else None,
                terminal_reason=(
                    poi_state.terminal_reason.value
                    if poi_state is not None and poi_state.terminal_reason is not None
                    else None
                ),
                terminal_time_utc=(
                    _iso(poi_state.terminal_time_utc) if poi_state is not None else None
                ),
            )
        )

    decisions: list[DecisionView] = []
    p3_lines: list[str] = []
    p5_lines: list[str] = []
    for poi_id in bar.evaluated_order:
        decision = bar.decision_by_id[poi_id]
        code = PERMISSION_CODE[decision.analytical_permission]
        decisions.append(
            DecisionView(
                record_id=str(poi_id),
                poi_idx=bar.poi_idx_by_id[poi_id],
                permission=decision.analytical_permission.value,
                permission_code=code,
                actionable=code in ACTIONABLE_PERMISSIONS,
                final_score=decision.final_confluence_score,
                lifecycle=decision.lifecycle_state.value,
                btmm_valid=decision.btmm_valid,
            )
        )
        p3_lines.append(_canonical_line(P3_FIELDS, _p3_row(bar, poi_id, day)))
        p5_lines.append(_canonical_line(P5_FIELDS, _p5_row(bar, poi_id, day)))

    poi_id_by_idx = {bar.poi_idx_by_id[pid]: pid for pid in bar.evaluated_order}
    events: list[EventView] = []
    p8_lines: list[str] = []
    for sequence, event in enumerate(bar.events):
        poi_id = poi_id_by_idx[event.poi_idx]
        row8: dict[str, object] = {
            "bar_ms": event.bar_ms,
            "trading_day": day,
            "sequence_in_bar": sequence,
            "event_type": event.event_type,
            "poi_idx": event.poi_idx,
            "poi_record_id": poi_id,
            "poi_bullish": event.poi_bullish,
            "tier": event.tier,
            "btmm_valid": event.btmm_valid,
            "permission": event.permission,
            "lifecycle": event.lifecycle,
            "terminal_reason": event.terminal_reason,
        }
        p8_lines.append(_canonical_line(P8_FIELDS, row8))
        events.append(
            EventView(
                event_type=event.event_type.value,
                poi_idx=event.poi_idx,
                bar_ms=event.bar_ms,
                sequence_in_bar=sequence,
                poi_record_id=str(poi_id),
                poi_bullish=event.poi_bullish,
                tier=event.tier,
                btmm_valid=event.btmm_valid,
                permission=event.permission,
                lifecycle=event.lifecycle,
                terminal_reason=(
                    event.terminal_reason.value if event.terminal_reason is not None else None
                ),
            )
        )

    digest = compute_bar_digest(
        bar_index=bar.bar_index,
        bar_ms=bar.bar_ms,
        primed=bar.primed_this_bar,
        registry_size=len(pois),
        new_registry_pois=new_registry,
        fresh_at_close=fresh,
        mitigated_at_close=mitigated,
        invalidated_at_close=invalidated,
        p3_lines=p3_lines,
        p5_lines=p5_lines,
        p8_lines=p8_lines,
    )
    return ScannerBarSnapshot(
        bar_index=bar.bar_index,
        bar_ms=bar.bar_ms,
        candle=bar.candle,
        trading_day=day,
        primed=bar.primed_this_bar,
        pois=tuple(pois),
        decisions=tuple(decisions),
        events=tuple(events),
        new_registry_pois=new_registry,
        fresh_at_close=fresh,
        mitigated_at_close=mitigated,
        invalidated_at_close=invalidated,
        p3_lines=tuple(p3_lines),
        p5_lines=tuple(p5_lines),
        p8_lines=tuple(p8_lines),
        digest=digest,
    )
