"""Forward scanner runner (A7A).

Drives ONE ``IncrementalReplayKernel`` from arriving CLOSED candles under the
project's production availability semantics, without touching scanner logic:

  closed-candle gate -> idempotency -> ordering -> gap observation
  -> causal availability grouping -> advance_group -> alert delta
  -> accepted-candle journal.

Grouping is causal: a candle at availability ``A`` is buffered and its group is
emitted only once a strictly-later availability arrives (so a same-``A`` candle
on another timeframe can still join it) -- identical to how
``run_scanner_replay`` batches equal-availability candles. ``flush()`` closes any
remaining buffered group. Recovery replays the journal through a fresh kernel,
which is byte-identical by construction (content-addressed identity).
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from enum import StrEnum

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.forward.alerts import AlertSink
from btmm_ai_scanner.forward.candle_factory import (
    ForwardCandleRejection,
    build_forward_closed_candle,
)
from btmm_ai_scanner.forward.events import ScannerAlert, ScannerEventType
from btmm_ai_scanner.forward.journal import AcceptedCandleJournal
from btmm_ai_scanner.forward.transport import ProviderCandle
from btmm_ai_scanner.historical_backtest.direct_batch_worker import _snapshot_checksum
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.market_data.gap_observation import observe_potential_gap
from btmm_ai_scanner.poi.enums import PoiLifecycleTransitionType
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
from btmm_ai_scanner.scanner.replay import _TIMEFRAME_RANK, IncrementalReplayKernel

_POI_EVENT_BY_TRANSITION: Mapping[PoiLifecycleTransitionType, ScannerEventType] = {
    PoiLifecycleTransitionType.CLOSE_BREACH_CANDIDATE: ScannerEventType.POI_BREACH,
    PoiLifecycleTransitionType.RECLAIM_PENDING: ScannerEventType.POI_RECLAIM,
    PoiLifecycleTransitionType.RECLAIM_CONFIRMED: ScannerEventType.POI_RECLAIM,
    PoiLifecycleTransitionType.DISPLACEMENT_AFTER_RECLAIM_CONFIRMED: (
        ScannerEventType.POI_RECLAIM
    ),
    PoiLifecycleTransitionType.RECLAIM_WITHOUT_DISPLACEMENT: (
        ScannerEventType.POI_RECLAIM
    ),
    PoiLifecycleTransitionType.RECLAIM_FAILED: ScannerEventType.POI_INVALIDATION,
    PoiLifecycleTransitionType.FALSE_INVALIDATION_CONFIRMED: (
        ScannerEventType.POI_RECLAIM
    ),
    PoiLifecycleTransitionType.GENUINE_INVALIDATION_CONFIRMED: (
        ScannerEventType.POI_INVALIDATION
    ),
}


class ForwardIngestOutcome(StrEnum):
    ACCEPTED = "ACCEPTED"
    EXACT_DUPLICATE = "EXACT_DUPLICATE"
    CONFLICTING_REVISION = "CONFLICTING_REVISION"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    FORMING_REJECTED = "FORMING_REJECTED"
    UNSUPPORTED_REJECTED = "UNSUPPORTED_REJECTED"


class ForwardIngestResult(ContractModel):
    outcome: ForwardIngestOutcome
    reason_code: str | None
    record_id: str | None
    groups_flushed: int


_SourceIdentity = tuple[str, str, str, datetime]


class ForwardScannerRunner:
    def __init__(
        self,
        tracked_timeframes: tuple[Timeframe, ...],
        scanner_configuration: ScannerConfiguration,
        *,
        alert_sink: AlertSink,
        journal: AcceptedCandleJournal | None = None,
    ) -> None:
        self._tracked = tuple(
            sorted(tracked_timeframes, key=lambda tf: _TIMEFRAME_RANK[tf])
        )
        self._config = scanner_configuration
        self._alert_sink = alert_sink
        self._journal = journal
        self._kernel = IncrementalReplayKernel(
            self._tracked,
            scanner_configuration,
            ContentAddressedIdentityProvider(),
            (),
        )
        self._accepted_fingerprint: dict[_SourceIdentity, str] = {}
        self._last_event_by_tf: dict[Timeframe, datetime] = {}
        self._last_candle_by_tf: dict[Timeframe, NormalizedCandle] = {}
        self._pending: dict[datetime, list[NormalizedCandle]] = {}
        self._last_flushed_availability: datetime | None = None
        self._group_sequence = 0
        self._seen_poi_obs: set[str] = set()
        self._seen_poi_lt: set[str] = set()
        self._tap_count_by_poi: dict[str, int] = {}
        self._seen_btmm_obs: set[str] = set()
        self._seen_btmm_lt: set[str] = set()

    # -- public API -------------------------------------------------------
    @property
    def group_sequence(self) -> int:
        return self._group_sequence

    def ingest(
        self, row: ProviderCandle, *, ingestion_time_utc: datetime
    ) -> ForwardIngestResult:
        try:
            candle = build_forward_closed_candle(
                row, ingestion_time_utc=ingestion_time_utc
            )
        except ForwardCandleRejection as rejection:
            if rejection.reason_code == "FORMING_CANDLE_REJECTED":
                return ForwardIngestResult(
                    outcome=ForwardIngestOutcome.FORMING_REJECTED,
                    reason_code=rejection.reason_code,
                    record_id=None,
                    groups_flushed=0,
                )
            self._warn(
                rejection.reason_code,
                ingestion_time_utc,
                None,
                None,
                None,
                rejection.reason_code,
            )
            return ForwardIngestResult(
                outcome=ForwardIngestOutcome.UNSUPPORTED_REJECTED,
                reason_code=rejection.reason_code,
                record_id=None,
                groups_flushed=0,
            )
        return self._accept_normalized(candle)

    def flush(self) -> int:
        """Close all buffered availability groups (e.g. at shutdown). Returns the
        number of groups emitted."""
        return self._flush_pending(boundary=None)

    def finalize(self) -> ScannerAnalysis:
        return self._kernel.finalize()

    def snapshot_checksum(self) -> str:
        return _snapshot_checksum(self._kernel.finalize().model_dump(mode="json"))

    @classmethod
    def recover_from_journal(
        cls,
        journal: AcceptedCandleJournal,
        tracked_timeframes: tuple[Timeframe, ...],
        scanner_configuration: ScannerConfiguration,
        *,
        alert_sink: AlertSink,
    ) -> ForwardScannerRunner:
        """Rebuild a runner deterministically from the accepted-candle journal.
        The journal is authoritative forward input history; replaying it through a
        fresh kernel yields identical semantic state (content-addressed identity).
        Does NOT re-append to the journal (recovery is read-only over history)."""
        candles = journal.load()
        runner = cls(
            tracked_timeframes,
            scanner_configuration,
            alert_sink=alert_sink,
            journal=None,
        )
        for candle in candles:
            runner._accept_normalized(candle, journal_append=False)
        runner.flush()
        runner._journal = journal
        return runner

    # -- internals --------------------------------------------------------
    def _accept_normalized(
        self, candle: NormalizedCandle, *, journal_append: bool = True
    ) -> ForwardIngestResult:
        identity: _SourceIdentity = (
            candle.provider,
            candle.symbol.value,
            candle.timeframe.value,
            candle.event_time_utc,
        )
        existing = self._accepted_fingerprint.get(identity)
        if existing is not None:
            if existing == candle.content_fingerprint:
                return ForwardIngestResult(
                    outcome=ForwardIngestOutcome.EXACT_DUPLICATE,
                    reason_code="EXACT_DUPLICATE",
                    record_id=str(candle.record_id),
                    groups_flushed=0,
                )
            self._warn(
                "CONFLICTING_REVISION_DETECTED",
                candle.availability_time_utc,
                candle.symbol,
                candle.timeframe,
                str(candle.record_id),
                "conflicting revision for an already-accepted candle identity;"
                " quarantined (not fed to scanner).",
            )
            return ForwardIngestResult(
                outcome=ForwardIngestOutcome.CONFLICTING_REVISION,
                reason_code="CONFLICTING_REVISION_DETECTED",
                record_id=str(candle.record_id),
                groups_flushed=0,
            )

        if (
            self._last_flushed_availability is not None
            and candle.availability_time_utc <= self._last_flushed_availability
        ):
            self._warn(
                "OUT_OF_ORDER_AFTER_GROUP_CLOSE",
                candle.availability_time_utc,
                candle.symbol,
                candle.timeframe,
                str(candle.record_id),
                "candle availability precedes an already-emitted group; rejected.",
            )
            return ForwardIngestResult(
                outcome=ForwardIngestOutcome.OUT_OF_ORDER,
                reason_code="OUT_OF_ORDER_AFTER_GROUP_CLOSE",
                record_id=str(candle.record_id),
                groups_flushed=0,
            )
        last_event = self._last_event_by_tf.get(candle.timeframe)
        if last_event is not None and candle.event_time_utc <= last_event:
            self._warn(
                "OUT_OF_ORDER_TIMEFRAME",
                candle.availability_time_utc,
                candle.symbol,
                candle.timeframe,
                str(candle.record_id),
                "candle event time is not strictly after the last accepted"
                " candle on its timeframe; rejected.",
            )
            return ForwardIngestResult(
                outcome=ForwardIngestOutcome.OUT_OF_ORDER,
                reason_code="OUT_OF_ORDER_TIMEFRAME",
                record_id=str(candle.record_id),
                groups_flushed=0,
            )

        previous_candle = self._last_candle_by_tf.get(candle.timeframe)
        if previous_candle is not None:
            gap = observe_potential_gap(previous_candle, candle)
            if gap is not None:
                self._warn(
                    "POTENTIAL_GAP",
                    candle.availability_time_utc,
                    candle.symbol,
                    candle.timeframe,
                    str(candle.record_id),
                    f"potential gap: {gap.missing_interval_count} missing"
                    f" {candle.timeframe.value} interval(s) before this candle.",
                )

        groups_flushed = self._flush_pending(boundary=candle.availability_time_utc)
        self._pending.setdefault(candle.availability_time_utc, []).append(candle)
        self._accepted_fingerprint[identity] = candle.content_fingerprint
        self._last_event_by_tf[candle.timeframe] = candle.event_time_utc
        self._last_candle_by_tf[candle.timeframe] = candle
        if journal_append and self._journal is not None:
            self._journal.append(candle)
        return ForwardIngestResult(
            outcome=ForwardIngestOutcome.ACCEPTED,
            reason_code=None,
            record_id=str(candle.record_id),
            groups_flushed=groups_flushed,
        )

    def _flush_pending(self, *, boundary: datetime | None) -> int:
        flushed = 0
        for availability in sorted(self._pending):
            if boundary is not None and availability >= boundary:
                break
            candles = self._pending.pop(availability)
            self._advance_and_alert(availability, candles)
            self._last_flushed_availability = availability
            flushed += 1
        return flushed

    def _advance_and_alert(
        self, availability: datetime, candles: list[NormalizedCandle]
    ) -> None:
        by_tf: dict[Timeframe, tuple[NormalizedCandle, ...]] = {
            tf: tuple(c for c in candles if c.timeframe == tf) for tf in self._tracked
        }
        self._kernel.advance_group(by_tf)
        self._group_sequence += 1
        self._emit_alert_delta(availability)

    def _emit_alert_delta(self, availability: datetime) -> None:
        snapshot = self._kernel.finalize()
        seq = self._group_sequence
        poi = snapshot.poi_analysis
        for observation in poi.poi_observations:
            rid = str(observation.record_id)
            if rid not in self._seen_poi_obs:
                self._seen_poi_obs.add(rid)
                self._emit(
                    ScannerEventType.NEW_POI,
                    seq,
                    availability,
                    observation.symbol,
                    observation.source_timeframe,
                    rid,
                    f"new POI {observation.poi_type.value}",
                )
        for state in poi.current_poi_states:
            key = str(state.poi_record_id)
            prior = self._tap_count_by_poi.get(key, 0)
            if state.tap_count > prior:
                self._tap_count_by_poi[key] = state.tap_count
                self._emit(
                    ScannerEventType.POI_RETEST,
                    seq,
                    availability,
                    state.symbol,
                    state.timeframe,
                    key,
                    f"POI tap_count {prior} -> {state.tap_count}",
                )
        for transition in poi.poi_lifecycle_transitions:
            rid = str(transition.record_id)
            if rid not in self._seen_poi_lt:
                self._seen_poi_lt.add(rid)
                event_type = _POI_EVENT_BY_TRANSITION.get(transition.transition_type)
                if event_type is not None:
                    self._emit(
                        event_type,
                        seq,
                        availability,
                        transition.symbol,
                        transition.timeframe,
                        str(transition.poi_record_id),
                        f"POI lifecycle {transition.transition_type.value}",
                    )
        btmm = snapshot.btmm_analysis
        for setup in btmm.btmm_observations:
            rid = str(setup.record_id)
            if rid not in self._seen_btmm_obs:
                self._seen_btmm_obs.add(rid)
                self._emit(
                    ScannerEventType.NEW_BTMM_SETUP,
                    seq,
                    availability,
                    setup.symbol,
                    setup.source_timeframe,
                    rid,
                    "new BTMM setup",
                )
        for btmm_transition in btmm.btmm_lifecycle_transitions:
            rid = str(btmm_transition.record_id)
            if rid not in self._seen_btmm_lt:
                self._seen_btmm_lt.add(rid)
                self._emit(
                    ScannerEventType.BTMM_LIFECYCLE_TRANSITION,
                    seq,
                    availability,
                    btmm_transition.symbol,
                    btmm_transition.timeframe,
                    str(btmm_transition.btmm_setup_record_id),
                    f"BTMM lifecycle {btmm_transition.transition_type.value}",
                )

    def _emit(
        self,
        event_type: ScannerEventType,
        group_sequence: int,
        availability: datetime,
        symbol: InternalSymbol | None,
        timeframe: Timeframe | None,
        record_id: str | None,
        detail: str,
    ) -> None:
        self._alert_sink.emit(
            ScannerAlert(
                event_type=event_type,
                group_sequence=group_sequence,
                availability_time_utc=availability,
                symbol=symbol,
                timeframe=timeframe,
                record_id=record_id,
                detail=detail,
            )
        )

    def _warn(
        self,
        reason_code: str,
        at_time: datetime,
        symbol: InternalSymbol | None,
        timeframe: Timeframe | None,
        record_id: str | None,
        detail: str,
    ) -> None:
        self._emit(
            ScannerEventType.DATA_QUALITY_WARNING,
            self._group_sequence,
            at_time,
            symbol,
            timeframe,
            record_id,
            f"{reason_code}: {detail}",
        )
