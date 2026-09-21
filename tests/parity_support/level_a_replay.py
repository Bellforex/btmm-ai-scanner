"""The generalized LEVEL-A replay core: arbitrary window, arbitrary
timeframe set, strictly chronological, derived only from raw OHLC.

Test/validation tooling only — nothing in ``src/`` imports this, and it
changes no production semantics.

WHAT "LEVEL A" MEANS HERE
-------------------------
LEVEL A is *independent* Python evidence generated from genuine broker
OHLC by calling the frozen engines in ``src/``. It never reads a Pine log,
a ``P5WIRE`` / ``P5EVAL`` / ``P8EVENT`` capture, or any other Pine-derived
state. The only inputs to this module are CSV candles and the scanner
configuration; everything else is computed. That is what makes a later
LEVEL A == LEVEL B comparison a genuine parity claim rather than a
tautology.

ONE INTERPRETATION OF THE SCANNER RULES
---------------------------------------
This module owns the *orchestration* only — which bar, which POI, in which
order. Every rule decision is delegated:

* detection / structure / POI lifecycle / BTMM -> ``IncrementalReplayKernel``
  (``btmm_ai_scanner.scanner.replay``), the package's own closed incremental
  engine, proven byte-identical to ``scan_market`` over the same prefix;
* the P5 active-POI set + ``assess_confluence`` -> ``run_active_poi_loop``
  (``tests.parity_support.p5_active_poi_loop_model``);
* P8 event derivation -> ``AlertEngine``
  (``tests.parity_support.p8_alert_oracle``).

``v1a_harness.run_dev_replay`` — the pre-existing, frozen V1-A DEV driver —
was refactored onto this same core rather than left as a second copy, so
there is exactly one implementation of the per-bar walk in the repository.
The two callers differ only in the two explicitly parameterised policies
below (``rc3_freshness`` and ``warmup_feed_policy``), never in a rule.

THE TWO PARAMETERISED POLICIES
-------------------------------
``rc3_freshness``
    ``False`` reproduces the RC2 eligibility contract (a POI leaves the P5
    universe only on ``GENUINE_INVALIDATION_CONFIRMED``). ``True`` is the
    RC3 contract (a POI leaves when it stops being ``fresh_active``, which
    also covers first-reaction mitigation). Both route through the SAME set
    algebra in ``p5_active_poi_loop_model``; see that module.

``warmup_feed_policy``
    How pre-window context candles are fed to the kernel before the first
    host bar.

    * ``AVAILABILITY`` (the correct, default policy): a context candle is
      pre-fed only if its own ``availability_time_utc`` is STRICTLY BEFORE
      the first host bar's availability. Everything else is interleaved
      per host bar by availability. Under this policy no candle is ever
      visible to the engine before the instant it actually closed, so the
      replay is point-in-time correct from the very first bar.
    * ``EVENT_TIME`` (legacy): a context candle is pre-fed if its
      ``event_time_utc`` precedes the window start. This is what the frozen
      V1-A DEV harness did, and it is preserved verbatim so that harness's
      already-published digests stay reproducible. It is NOT recommended
      for new work: a W1/D1/H4 bar that OPENED before the window but CLOSES
      inside it is made visible early under this policy.

NO LOOKAHEAD, BY CONSTRUCTION (AVAILABILITY POLICY)
----------------------------------------------------
Every candle handed to the kernel for host bar *N* has
``availability_time_utc <= host[N].availability_time_utc``, and candles are
fed once each, in non-decreasing availability order. The ``visible`` map
passed to ``assess_confluence`` is this module's own append-only accumulator
stepped in lockstep with the kernel, so it can never contain a future
candle. ``tests/unit/test_rc3_daily_authority.py`` proves this empirically
by truncate-and-extend (replay to a cutoff, freeze, append future bars,
re-replay, compare).
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.framework import FrameworkTracker
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.current_state import CurrentPoiState
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.rc5_semantics import (
    Rc5SemanticLedger,
    assign_origin_authority,
    suppressed_record_ids,
)
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis, ScannerSetupSummary
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from tests.parity_support.p5_active_poi_loop_model import (
    rc4_is_terminal,
    rc4_terminal_reason,
    rc5_is_terminal,
    rc5_terminal_reason,
    run_active_poi_loop,
)
from tests.parity_support.p5_wire_normalized_replay import (
    LIFECYCLE_CODE,
    PERMISSION_CODE,
    POI_TIER_BY_CODE,
)
from tests.parity_support.p8_alert_oracle import (
    AlertEngine,
    AlertEvent,
    BarSnapshot,
    PoiSnapshot,
)

__all__ = [
    "DEFAULT_MINIMUM_PRICE_TICK",
    "TIMEFRAME_RANK",
    "LevelABar",
    "WarmupFeedPolicy",
    "build_scanner_configuration",
    "iter_level_a_bars",
    "merge_context_group",
]

#: XAUUSD quote increment used by every V1-A / RC3 validation run.
DEFAULT_MINIMUM_PRICE_TICK = Decimal("0.01")

_TERMINAL_STATUS = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED

#: Coarse-to-fine ordering used whenever a deterministic timeframe order is
#: needed on this side of the wall. The kernel sorts its own tracked set the
#: same way internally; this table exists so callers can present timeframes
#: in a stable order without importing a private name from ``src``.
TIMEFRAME_RANK: dict[Timeframe, int] = {
    Timeframe.W1: 0,
    Timeframe.D1: 1,
    Timeframe.H4: 2,
    Timeframe.H3: 3,
    Timeframe.H1: 4,
    Timeframe.M15: 5,
    Timeframe.M5: 6,
    Timeframe.M1: 7,
}

_TIER_CODE_BY_VALUE = {v: k for k, v in POI_TIER_BY_CODE.items() if v is not None}
_TIER_CODE_BY_VALUE[None] = 0


class WarmupFeedPolicy(StrEnum):
    """See the module docstring, "THE TWO PARAMETERISED POLICIES"."""

    AVAILABILITY = "AVAILABILITY"
    EVENT_TIME = "EVENT_TIME"


def build_scanner_configuration(
    *,
    required_timeframes: frozenset[Timeframe] = frozenset({Timeframe.M15}),
    optional_timeframes: frozenset[Timeframe] = frozenset(),
    minimum_price_tick: Decimal = DEFAULT_MINIMUM_PRICE_TICK,
) -> ScannerConfiguration:
    """The one scanner configuration builder every Level-A caller uses."""
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=minimum_price_tick
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=minimum_price_tick),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=minimum_price_tick),
        required_timeframes=required_timeframes,
        optional_timeframes=optional_timeframes,
    )


def merge_context_group(
    context_candles: Mapping[Timeframe, Sequence[NormalizedCandle]],
    pointers: dict[Timeframe, int],
    bound_availability_utc: datetime,
) -> dict[Timeframe, tuple[NormalizedCandle, ...]]:
    """Consume, from each context series, every candle that has become
    available at or before ``bound_availability_utc``.

    ``pointers`` is mutated in place: each series is a monotonically advanced
    cursor, so no candle is ever consumed twice and none is skipped.
    """
    group: dict[Timeframe, tuple[NormalizedCandle, ...]] = {}
    for timeframe, seq in context_candles.items():
        pointer = pointers[timeframe]
        collected: list[NormalizedCandle] = []
        while (
            pointer < len(seq)
            and seq[pointer].availability_time_utc <= bound_availability_utc
        ):
            collected.append(seq[pointer])
            pointer += 1
        pointers[timeframe] = pointer
        if collected:
            group[timeframe] = tuple(collected)
    return group


@dataclass(frozen=True)
class LevelABar:
    """Everything one confirmed host bar produced.

    Deliberately a *view*, not an archive: ``analysis`` is the live
    ``ScannerAnalysis`` for this bar and is not retained by the iterator, so
    a consumer that only projects the fields it needs never pays to keep
    thousands of full snapshots in memory.
    """

    bar_index: int
    candle: NormalizedCandle
    bar_ms: int
    availability_time_utc: datetime
    analysis: ScannerAnalysis
    observation_by_id: Mapping[UUID, PoiObservation]
    state_by_id: Mapping[UUID, CurrentPoiState]
    setup_by_poi_id: Mapping[UUID, ScannerSetupSummary]
    evaluated_order: tuple[UUID, ...]
    decision_by_id: Mapping[UUID, BtrcDecision]
    poi_idx_by_id: Mapping[UUID, int]
    events: tuple[AlertEvent, ...]
    #: True on the first host bar, where the alert engine is PRIMED from the
    #: pre-existing POI universe instead of announcing it (the frozen
    #: fresh-attach contract — see ``p8_alert_oracle`` "PRIMING").
    primed_this_bar: bool

    def is_terminal(self, poi_id: UUID, *, rc3_freshness: bool) -> bool:
        state = self.state_by_id.get(poi_id)
        if state is None:
            return False
        if rc3_freshness:
            return not state.fresh_active
        return state.poi_lifecycle_status is _TERMINAL_STATUS


def _ordered_tracked(timeframes: frozenset[Timeframe]) -> tuple[Timeframe, ...]:
    return tuple(sorted(timeframes, key=lambda tf: TIMEFRAME_RANK[tf]))


def iter_level_a_bars(
    *,
    host_timeframe: Timeframe,
    host_series: Sequence[NormalizedCandle],
    context_series: Mapping[Timeframe, Sequence[NormalizedCandle]],
    configuration: ScannerConfiguration,
    rc3_freshness: bool,
    warmup_feed_policy: WarmupFeedPolicy = WarmupFeedPolicy.AVAILABILITY,
    rc4_framework: bool = False,
    rc5_authority: bool = False,
) -> Iterator[LevelABar]:
    """Walk ``host_series`` one confirmed bar at a time and yield a
    ``LevelABar`` per bar.

    The iterator is stateful and single-pass: it carries the kernel, the
    visible-candle accumulator, the P5 active set, the POI index assignment
    and the P8 alert engine across bars, which is exactly what makes state
    survive day/week boundaries. Nothing is ever reset mid-walk.
    """
    if len(host_series) == 0:
        return
    if rc4_framework and not configuration.poi_configuration.rc4_fvg_quality:
        # One profile switch: the RC4 market framework always runs the RC4 POI
        # qualification contract (FVG displacement + pre-availability
        # consumption). RC3 callers are untouched.
        configuration = configuration.model_copy(
            update={
                "poi_configuration": configuration.poi_configuration.model_copy(
                    update={"rc4_fvg_quality": True}
                )
            }
        )
    if host_timeframe in context_series:
        raise ValueError(
            f"{host_timeframe} is the host timeframe and must not also appear "
            "in context_series."
        )

    tracked = _ordered_tracked(frozenset({host_timeframe, *context_series}))
    last_availability = host_series[-1].availability_time_utc
    first_availability = host_series[0].availability_time_utc
    window_start_event = host_series[0].event_time_utc

    bounded: dict[Timeframe, list[NormalizedCandle]] = {}
    for timeframe, candles in context_series.items():
        kept = [c for c in candles if c.availability_time_utc <= last_availability]
        kept.sort(key=lambda c: c.availability_time_utc)
        bounded[timeframe] = kept

    def _is_warmup(candle: NormalizedCandle) -> bool:
        if warmup_feed_policy is WarmupFeedPolicy.AVAILABILITY:
            return candle.availability_time_utc < first_availability
        return candle.event_time_utc < window_start_event

    # RC5 provenance accumulates across the whole walk: the kernel records each
    # POI's qualifying facts once, at the bar that qualified it.
    rc5_ledger = Rc5SemanticLedger()
    kernel = IncrementalReplayKernel(
        tracked,
        configuration,
        ContentAddressedIdentityProvider(),
        (),
        rc5_ledger if rc5_authority else None,
    )

    # --- warm-up: feed the pre-window context in availability order, one
    # availability group at a time (never one big group: the kernel's unit of
    # confirmation is the availability instant).
    warmup_flat: list[tuple[datetime, Timeframe, NormalizedCandle]] = []
    for timeframe, candles in bounded.items():
        for candle in candles:
            if _is_warmup(candle):
                warmup_flat.append((candle.availability_time_utc, timeframe, candle))
    warmup_flat.sort(key=lambda row: (row[0], TIMEFRAME_RANK[row[1]]))
    index = 0
    while index < len(warmup_flat):
        group_time = warmup_flat[index][0]
        pending: dict[Timeframe, list[NormalizedCandle]] = {}
        while index < len(warmup_flat) and warmup_flat[index][0] == group_time:
            pending.setdefault(warmup_flat[index][1], []).append(warmup_flat[index][2])
            index += 1
        kernel.advance_group({tf: tuple(v) for tf, v in pending.items()})

    pointers: dict[Timeframe, int] = {}
    visible: dict[Timeframe, list[NormalizedCandle]] = {tf: [] for tf in tracked}
    for timeframe, candles in bounded.items():
        pointer = 0
        while pointer < len(candles) and _is_warmup(candles[pointer]):
            visible[timeframe].append(candles[pointer])
            pointer += 1
        pointers[timeframe] = pointer

    poi_idx_by_id: dict[UUID, int] = {}
    next_poi_idx = 0
    previously_active: frozenset[UUID] = frozenset()
    alert_engine = AlertEngine()
    framework_trackers = {host_timeframe: FrameworkTracker()} if rc4_framework else None

    for bar_index, candle in enumerate(host_series):
        bound = candle.availability_time_utc
        group = merge_context_group(bounded, pointers, bound)
        group[host_timeframe] = (candle,)
        kernel.advance_group(group)
        for timeframe, new_candles in group.items():
            visible[timeframe].extend(new_candles)

        analysis = kernel.finalize()
        if rc5_authority:
            # RC5: arbitrate same-origin synonyms BEFORE the opportunity loop.
            # A subordinate must not be an independent opportunity, so it is
            # removed here rather than filtered out of the results -- that also
            # keeps it out of the P8 stream, which is derived from this loop.
            assign_origin_authority(analysis.poi_analysis.poi_observations, rc5_ledger)
            suppressed = suppressed_record_ids(
                analysis.poi_analysis.poi_observations, rc5_ledger
            )
        else:
            suppressed = frozenset()
        loop = run_active_poi_loop(
            analysis,
            previously_active,
            candles_by_timeframe=visible,
            evaluation_time_utc=analysis.availability_time_utc,
            rc3_freshness=rc3_freshness,
            framework_timeframe=host_timeframe if rc4_framework else None,
            framework_trackers=framework_trackers,
            suppressed_poi_ids=suppressed,
            rc5_validity=rc5_authority,
        )

        observation_by_id = {
            o.record_id: o for o in analysis.poi_analysis.poi_observations
        }
        state_by_id = {
            s.poi_record_id: s for s in analysis.poi_analysis.current_poi_states
        }
        setup_by_poi_id = {s.source_poi_record_id: s for s in analysis.setup_summaries}

        poi_snapshots: list[PoiSnapshot] = []
        for poi_id in loop.evaluated_order:
            poi = observation_by_id[poi_id]
            if poi_id not in poi_idx_by_id:
                poi_idx_by_id[poi_id] = next_poi_idx
                next_poi_idx += 1
            decision = loop.decisions_by_poi_id[poi_id]
            state = state_by_id.get(poi_id)
            if rc5_authority:
                terminal = rc5_is_terminal(state, decision)
                terminal_reason = rc5_terminal_reason(state, decision)
            elif rc4_framework:
                terminal = rc4_is_terminal(state, decision)
                terminal_reason = rc4_terminal_reason(state, decision)
            elif rc3_freshness:
                terminal = state is not None and not state.fresh_active
                terminal_reason = state.terminal_reason if state is not None else None
            else:
                terminal = (
                    state is not None and state.poi_lifecycle_status is _TERMINAL_STATUS
                )
                terminal_reason = None
            poi_snapshots.append(
                PoiSnapshot(
                    poi_idx=poi_idx_by_id[poi_id],
                    poi_bullish=poi.direction.value == "BULLISH",
                    tier=_TIER_CODE_BY_VALUE[poi.strength_tier],
                    terminal=terminal,
                    btmm_valid=decision.btmm_valid,
                    permission=PERMISSION_CODE[decision.analytical_permission],
                    lifecycle=LIFECYCLE_CODE[decision.lifecycle_state],
                    terminal_reason=terminal_reason if terminal else None,
                )
            )

        bar_ms = int(analysis.availability_time_utc.timestamp() * 1000)
        bar_snapshot = BarSnapshot(bar_ms=bar_ms, pois=tuple(poi_snapshots))
        primed_this_bar = not alert_engine.primed
        if primed_this_bar:
            alert_engine.prime(bar_snapshot)
            fired: list[AlertEvent] = []
        else:
            fired = alert_engine.process(bar_snapshot)

        yield LevelABar(
            bar_index=bar_index,
            candle=candle,
            bar_ms=bar_ms,
            availability_time_utc=analysis.availability_time_utc,
            analysis=analysis,
            observation_by_id=observation_by_id,
            state_by_id=state_by_id,
            setup_by_poi_id=setup_by_poi_id,
            evaluated_order=loop.evaluated_order,
            decision_by_id=loop.decisions_by_poi_id,
            poi_idx_by_id=dict(poi_idx_by_id),
            events=tuple(fired),
            primed_this_bar=primed_this_bar,
        )

        previously_active = loop.next_bar_active_ids
