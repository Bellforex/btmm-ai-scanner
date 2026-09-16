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

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.displacement import detect_displacement_observations
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from tests.parity_support.level_a_replay import (
    WarmupFeedPolicy,
    iter_level_a_bars,
    merge_context_group,
)
from tests.parity_support.level_a_replay import (
    build_scanner_configuration as _build_level_a_configuration,
)
from tests.parity_support.v1a_csv_loader import (
    DEFAULT_PRE_DEV_LOOKBACK_BARS,
    load_dev_bounded_context_capped,
    load_dev_only_m15,
)

_CONTEXT_TIMEFRAMES: tuple[Timeframe, ...] = (
    Timeframe.W1,
    Timeframe.D1,
    Timeframe.H4,
    Timeframe.H1,
)
_TRACKED_TIMEFRAMES: tuple[Timeframe, ...] = (*_CONTEXT_TIMEFRAMES, Timeframe.M15)

#: Kept as a module-level name because the V1-A tests import it directly; it
#: is now a thin alias for the shared core's own group merger, so the two
#: drivers can never drift apart on how context candles are consumed.
_merge_context_group = merge_context_group


def build_scanner_configuration() -> ScannerConfiguration:
    """The frozen V1-A configuration: M15 host, W1/D1/H4/H1 context."""
    return _build_level_a_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(_CONTEXT_TIMEFRAMES),
        minimum_price_tick=Decimal("0.01"),
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
    dev_end_availability = dev_m15[-1].availability_time_utc

    context_candles: dict[Timeframe, list[NormalizedCandle]] = {}
    for timeframe, candles in context_full.items():
        bounded = [c for c in candles if c.availability_time_utc <= dev_end_availability]
        bounded.sort(key=lambda c: c.availability_time_utc)
        context_candles[timeframe] = bounded

    config = build_scanner_configuration()

    poi_registry: dict[UUID, PoiRegistryEntry] = {}
    events: list[EventRecord] = []
    availability_to_bar_index: dict[datetime, int] = {}

    # The per-bar walk itself lives in the shared Level-A core; this driver
    # only projects each bar into the frozen V1-A record shapes. The legacy
    # EVENT_TIME warm-up policy is pinned here on purpose: it is what the
    # already-published V1-A digests were produced under (see
    # ``level_a_replay`` "THE TWO PARAMETERISED POLICIES").
    for bar in iter_level_a_bars(
        host_timeframe=Timeframe.M15,
        host_series=dev_m15,
        context_series=context_candles,
        configuration=config,
        rc3_freshness=False,
        warmup_feed_policy=WarmupFeedPolicy.EVENT_TIME,
    ):
        bar_index = bar.bar_index
        availability_to_bar_index[bar.availability_time_utc] = bar_index

        for poi_id in bar.evaluated_order:
            if poi_id in poi_registry:
                continue
            poi = bar.observation_by_id[poi_id]
            poi_registry[poi_id] = PoiRegistryEntry(
                record_id=poi_id,
                poi_idx=bar.poi_idx_by_id[poi_id],
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

        poi_id_by_idx_this_bar = {
            bar.poi_idx_by_id[pid]: pid for pid in bar.evaluated_order
        }
        for alert_event in bar.events:
            poi_id = poi_id_by_idx_this_bar[alert_event.poi_idx]
            decision = bar.decision_by_id[poi_id]
            poi = bar.observation_by_id[poi_id]
            event_dt = bar.availability_time_utc
            bar_ms = bar.bar_ms
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
