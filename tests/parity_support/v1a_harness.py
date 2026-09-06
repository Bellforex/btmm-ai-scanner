"""V1-A per-bar DEV-set replay driver (test/validation tooling only).

Nothing in ``src/`` imports this, and it changes no production semantics.
Every detection/scoring decision in this module comes from calling the
already-closed, already-tested engines named in
``docs/validation/BTRC_V1_VALIDATION_PROTOCOL.md`` §2 — this module only
orchestrates WHICH bar/POI they are called with and folds their own output
fields into the canonical per-event/per-POI records the protocol's §16/§18
report needs.

WHY THIS DRIVES ``IncrementalReplayKernel`` DIRECTLY INSTEAD OF CALLING
``run_scanner_replay(..., SnapshotRetentionPolicy.ALL)`` ONCE
-------------------------------------------------------------------------
The frozen protocol (§2) names ``run_scanner_replay`` with
``SnapshotRetentionPolicy.ALL`` as the recipe for "one full ScannerAnalysis
per confirmed availability group (bar)". The task brief explicitly leaves
the IMPLEMENTATION technique open ("or drives it incrementally per bar —
your call"), because ``ALL`` retention and a bar-by-bar incremental walk
are two ways to reach the SAME observable contract, not two different
specifications.

They are not equally tractable, though. ``ALL`` retention re-runs the full
batch ``scan_market`` (structure/POI/BTMM re-derived from scratch) at
EVERY availability group over the ever-growing prefix — the exact O(n²)
growth this project's own prior work already identified and named
("A2 kernel performance is quadratic": 18k bars measured at 51-84h,
called "infeasible" without an architectural change). This session
independently re-measured the same super-linear wall-clock growth on
THIS dataset before committing to a design (50→400 M15 bars: 1.1s→107s
for the direct ``ALL`` path).

``IncrementalReplayKernel`` (``scanner/replay.py``) is the SAME package's
own, already-closed answer to that exact problem: its ``advance_group``
is documented O(1) amortized per candle, and it is proven — by this
project's own prior closed differential work (P2/P3/P5/P6 real-data
parity closures; ``test_scanner_replay_incremental_equivalence.py``,
``test_scanner_batch_replay_equivalence.py``) — to materialize a
``ScannerAnalysis`` byte-identical to ``scan_market`` over the same
prefix. This module drives that kernel one availability group at a time
and calls ``finalize()`` after every group to get a genuine per-bar
snapshot (repeated ``finalize()`` reintroduces some of the cost the
kernel's own lazy design tries to avoid, but empirically far less than
the ``ALL`` path — this module's own differential test,
``tests/unit/test_v1a_harness.py::test_kernel_driven_matches_all_retention_replay``,
proves the two techniques produce IDENTICAL ``ScannerAnalysis`` snapshots
on a real DEV-data prefix, so this is a performance substitution, not a
measurement-definition change).

PRE-DEV CONTEXT LOOKBACK
--------------------------
See ``v1a_csv_loader.load_dev_bounded_context_capped`` for the (disclosed,
deliberate) pre-DEV lookback cap on W1/D1/H4/H1 — every bar occurring
DURING the DEV window itself is always included in full, in strict
availability order, with zero lookahead; only the amount of PRE-DEV
warm-up history is bounded, for tractable wall-clock.

NO LOOKAHEAD, BY CONSTRUCTION
--------------------------------
Every candle this module ever hands to the kernel, to
``assess_confluence``, or to any outcome computation is bounded to (a) the
current bar's own ``availability_time_utc`` for anything describing "as of
this bar" state (the kernel only ever sees groups up to and including the
current bar; ``candles_by_timeframe`` passed to ``assess_confluence`` is
this module's own running "visible so far" accumulator, never the full
loaded series), or (b) DEV bars strictly AFTER the event bar for any
FORWARD-looking outcome measurement (MFE/MAE/threshold/geometry), which by
construction can never include the event's own bar or any earlier bar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc.t5_engine import assess_confluence
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import detect_displacement_observations
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from tests.parity_support.p5_active_poi_loop_model import resolve_eligible_and_next
from tests.parity_support.p5_wire_normalized_replay import (
    LIFECYCLE_CODE,
    PERMISSION_CODE,
    POI_TIER_BY_CODE,
)
from tests.parity_support.p8_alert_oracle import (
    AlertEngine,
    BarSnapshot,
    PoiSnapshot,
)
from tests.parity_support.v1a_csv_loader import (
    DEFAULT_PRE_DEV_LOOKBACK_BARS,
    load_dev_bounded_context_capped,
    load_dev_only_m15,
)

_TERMINAL_STATUS = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
_TIER_CODE_BY_VALUE = {v: k for k, v in POI_TIER_BY_CODE.items() if v is not None}
_TIER_CODE_BY_VALUE[None] = 0

_CONTEXT_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.W1,
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.H1,
)
_TRACKED_TIMEFRAMES: tuple[Timeframe, ...] = (*_CONTEXT_TIMEFRAMES, Timeframe.M15)


def build_scanner_configuration() -> ScannerConfiguration:
    tick = Decimal("0.01")
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(minimum_price_tick=tick),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=tick),
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(_CONTEXT_TIMEFRAMES),
    )


@dataclass(frozen=True)
class PoiRegistryEntry:
    record_id: UUID
    poi_idx: int
    poi_type: str
    poi_direction: str
    origin_timeframe: str
    effective_timeframe: str
    zone_top: Decimal
    zone_bottom: Decimal
    strength_tier: str | None
    availability_time_utc: datetime
    first_seen_bar_index: int  # 0-indexed DEV M15 bar


@dataclass(frozen=True)
class EventRecord:
    event_type: str
    bar_index: int  # 0-indexed DEV M15 bar the event fired on
    bar_ms: int
    poi_record_id: str
    poi_idx: int
    poi_type: str
    poi_direction: str
    origin_timeframe: str
    zone_top: str
    zone_bottom: str
    btrc_score: int
    btrc_score_band: str
    btrc_permission: str
    btmm_valid: bool
    trend_alignment: str
    regime: str
    session: str | None
    volatility_state: str | None
    poi_lifecycle_status: str | None
    calendar_day: str
    iso_week: str


@dataclass
class DevReplayProgress:
    bars_processed: int = 0
    events_emitted: int = 0
    pois_seen: int = 0


@dataclass
class DevReplayResult:
    dev_m15: tuple[NormalizedCandle, ...]
    poi_registry: dict[UUID, PoiRegistryEntry]
    events: list[EventRecord]
    atr_series: tuple[Decimal | None, ...]
    displacement_by_bar_index: dict[int, tuple[str, str]]  # bar_index -> (direction, classification)
    availability_to_bar_index: dict[datetime, int]
    exclusions: dict[str, int] = field(default_factory=dict)


def _score_band(score: int) -> str:
    if score < 45:
        return "<45"
    if score < 65:
        return "45-64"
    return ">=65"


def _merge_context_group(
    context_candles: dict[Timeframe, list[NormalizedCandle]],
    pointers: dict[Timeframe, int],
    bound_availability_utc: datetime,
) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
    group: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for timeframe, seq in context_candles.items():
        pointer = pointers[timeframe]
        collected: list[NormalizedCandle] = []
        while pointer < len(seq) and seq[pointer].availability_time_utc <= bound_availability_utc:
            collected.append(seq[pointer])
            pointer += 1
        pointers[timeframe] = pointer
        if collected:
            group[timeframe] = tuple(collected)
    return group


def run_dev_replay(
    *,
    dataset_root: Path,
    pre_dev_lookback_bars: int = DEFAULT_PRE_DEV_LOOKBACK_BARS,
    max_bars: int | None = None,
    progress_every: int = 100,
    progress_callback: object | None = None,
) -> DevReplayResult:
    """Run the full point-in-time DEV replay: one ``ScannerAnalysis`` per
    DEV M15 bar (via the kernel-driven substitution — see module docstring),
    the active-POI loop, ``assess_confluence`` per eligible POI, and P8
    event derivation. Returns the raw ingredients the outcome-measurement
    pass (``compute_outcomes`` below) needs — NOT yet the forward-looking
    MFE/MAE/threshold/geometry tables, which are a separate, cheap,
    pure-math pass over the same DEV M15 series (kept separate so the
    protocol §17 oracle/mutation tests can exercise that math without
    paying the replay's own cost).

    ``max_bars`` truncates the DEV set for smoke-testing only (``None`` =
    the full frozen 2903-bar DEV set).
    """
    dev_m15 = load_dev_only_m15(dataset_root)
    if max_bars is not None:
        dev_m15 = dev_m15[:max_bars]
    context_full = load_dev_bounded_context_capped(
        dataset_root, pre_dev_lookback_bars=pre_dev_lookback_bars
    )
    dev_start = dev_m15[0].event_time_utc
    dev_end_availability = dev_m15[-1].availability_time_utc

    context_candles: dict[Timeframe, list[NormalizedCandle]] = {}
    for timeframe, candles in context_full.items():
        bounded = [c for c in candles if c.availability_time_utc <= dev_end_availability]
        bounded.sort(key=lambda c: c.availability_time_utc)
        context_candles[timeframe] = bounded
    context_pointers = {tf: 0 for tf in _CONTEXT_TIMEFRAMES}

    config = build_scanner_configuration()
    kernel = IncrementalReplayKernel(
        _TRACKED_TIMEFRAMES, config, ContentAddressedIdentityProvider(), ()
    )

    # Bulk-feed the pre-DEV warm-up context (all of it precedes DEV's first
    # bar's availability, so no per-bar interleaving is needed here — this
    # is a straight availability-ordered walk of the context-only prefix).
    pre_dev_flat: list[tuple[datetime, Timeframe, NormalizedCandle]] = []
    for timeframe, candles in context_candles.items():
        for candle in candles:
            if candle.event_time_utc < dev_start:
                pre_dev_flat.append((candle.availability_time_utc, timeframe, candle))
    pre_dev_flat.sort(key=lambda row: row[0])
    index = 0
    while index < len(pre_dev_flat):
        group_time = pre_dev_flat[index][0]
        group: dict[Timeframe, list[NormalizedCandle]] = {}
        while index < len(pre_dev_flat) and pre_dev_flat[index][0] == group_time:
            group.setdefault(pre_dev_flat[index][1], []).append(pre_dev_flat[index][2])
            index += 1
        kernel.advance_group({tf: tuple(v) for tf, v in group.items()})
    for timeframe in _CONTEXT_TIMEFRAMES:
        seq = context_candles[timeframe]
        pointer = 0
        while pointer < len(seq) and seq[pointer].event_time_utc < dev_start:
            pointer += 1
        context_pointers[timeframe] = pointer

    # Running "visible so far" candle accumulator for assess_confluence's
    # own candles_by_timeframe parameter (volatility assessment) -- point
    # -in-time correct by construction: only ever appended to, in step
    # with the kernel's own advance, never containing a future candle.
    visible: dict[Timeframe, list[NormalizedCandle]] = {tf: [] for tf in _TRACKED_TIMEFRAMES}
    for timeframe in _CONTEXT_TIMEFRAMES:
        pre = [c for c in context_candles[timeframe] if c.event_time_utc < dev_start]
        visible[timeframe].extend(pre)

    poi_registry: dict[UUID, PoiRegistryEntry] = {}
    poi_idx_by_id: dict[UUID, int] = {}
    next_poi_idx = 0
    previously_active_ids: frozenset[UUID] = frozenset()
    alert_engine = AlertEngine()
    events: list[EventRecord] = []
    availability_to_bar_index: dict[datetime, int] = {}

    for bar_index, candle in enumerate(dev_m15):
        bound = candle.availability_time_utc
        group = _merge_context_group(context_candles, context_pointers, bound)
        group[Timeframe.M15] = (candle,)
        kernel.advance_group(group)
        for timeframe, new_candles in group.items():
            visible[timeframe].extend(new_candles)

        snapshot = kernel.finalize()
        availability_to_bar_index[snapshot.availability_time_utc] = bar_index

        status_by_id = {
            s.poi_record_id: s.poi_lifecycle_status
            for s in snapshot.poi_analysis.current_poi_states
        }
        obs_by_id = {o.record_id: o for o in snapshot.poi_analysis.poi_observations}
        eligible_ids, next_active = resolve_eligible_and_next(
            status_by_id, previously_active_ids, known_ids=frozenset(obs_by_id)
        )
        ordered = tuple(
            sorted(eligible_ids, key=lambda pid: (obs_by_id[pid].availability_time_utc, str(pid)))
        )

        poi_snapshots: list[PoiSnapshot] = []
        decisions_this_bar: dict[UUID, object] = {}
        for poi_id in ordered:
            poi = obs_by_id[poi_id]
            if poi_id not in poi_idx_by_id:
                poi_idx_by_id[poi_id] = next_poi_idx
                poi_registry[poi_id] = PoiRegistryEntry(
                    record_id=poi_id,
                    poi_idx=next_poi_idx,
                    poi_type=poi.poi_type.value,
                    poi_direction=poi.direction.value,
                    origin_timeframe=poi.source_timeframe.value,
                    effective_timeframe=poi.effective_timeframe.value,
                    zone_top=poi.zone_top,
                    zone_bottom=poi.zone_bottom,
                    strength_tier=poi.strength_tier.value if poi.strength_tier else None,
                    availability_time_utc=poi.availability_time_utc,
                    first_seen_bar_index=bar_index,
                )
                next_poi_idx += 1

            decision = assess_confluence(
                snapshot,
                poi,
                candles_by_timeframe=visible,
                evaluation_time_utc=snapshot.availability_time_utc,
            )
            decisions_this_bar[poi_id] = decision
            status = status_by_id.get(poi_id)
            poi_snapshots.append(
                PoiSnapshot(
                    poi_idx=poi_idx_by_id[poi_id],
                    poi_bullish=poi.direction.value == "BULLISH",
                    tier=_TIER_CODE_BY_VALUE[poi.strength_tier],
                    terminal=status is _TERMINAL_STATUS,
                    btmm_valid=decision.btmm_valid,
                    permission=PERMISSION_CODE[decision.analytical_permission],
                    lifecycle=LIFECYCLE_CODE[decision.lifecycle_state],
                )
            )

        bar_ms = int(snapshot.availability_time_utc.timestamp() * 1000)
        bar_snapshot = BarSnapshot(bar_ms=bar_ms, pois=tuple(poi_snapshots))
        if not alert_engine.primed:
            alert_engine.prime(bar_snapshot)
            fired = []
        else:
            fired = alert_engine.process(bar_snapshot)

        poi_id_by_idx_this_bar = {poi_idx_by_id[pid]: pid for pid in ordered}
        for alert_event in fired:
            poi_id = poi_id_by_idx_this_bar[alert_event.poi_idx]
            decision = decisions_this_bar[poi_id]
            poi = obs_by_id[poi_id]
            event_dt = snapshot.availability_time_utc
            events.append(
                EventRecord(
                    event_type=alert_event.event_type.value,
                    bar_index=bar_index,
                    bar_ms=bar_ms,
                    poi_record_id=str(poi.record_id),
                    poi_idx=alert_event.poi_idx,
                    poi_type=poi.poi_type.value,
                    poi_direction=poi.direction.value,
                    origin_timeframe=poi.source_timeframe.value,
                    zone_top=str(poi.zone_top),
                    zone_bottom=str(poi.zone_bottom),
                    btrc_score=decision.final_confluence_score,
                    btrc_score_band=_score_band(decision.final_confluence_score),
                    btrc_permission=decision.analytical_permission.value,
                    btmm_valid=decision.btmm_valid,
                    trend_alignment=decision.trend_alignment.value,
                    regime=decision.regime.value,
                    session=decision.session_context.value if decision.session_context else None,
                    volatility_state=(
                        decision.volatility_state.value if decision.volatility_state else None
                    ),
                    poi_lifecycle_status=(
                        decision.poi_lifecycle_status.value
                        if decision.poi_lifecycle_status
                        else None
                    ),
                    calendar_day=event_dt.date().isoformat(),
                    iso_week=f"{event_dt.isocalendar().year}-W{event_dt.isocalendar().week:02d}",
                )
            )

        previously_active_ids = next_active

        if progress_callback is not None and (
            (bar_index + 1) % progress_every == 0 or bar_index + 1 == len(dev_m15)
        ):
            progress_callback(  # type: ignore[operator]
                bar_index + 1, len(dev_m15), events, poi_registry
            )

    atr_series = compute_atr_series(dev_m15, period=14)
    measurement_cfg = config.measurement_configuration
    displacement_candidates = detect_displacement_observations(dev_m15, measurement_cfg)
    displacement_by_bar_index: dict[int, tuple[str, str]] = {}
    for candidate in displacement_candidates:
        idx = availability_to_bar_index.get(candidate.availability_time_utc)
        if idx is not None:
            displacement_by_bar_index[idx] = (
                candidate.direction.value,
                candidate.classification.value,
            )

    return DevReplayResult(
        dev_m15=dev_m15,
        poi_registry=poi_registry,
        events=events,
        atr_series=atr_series,
        displacement_by_bar_index=displacement_by_bar_index,
        availability_to_bar_index=availability_to_bar_index,
    )
