import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.btmm.analyzer import BtmmTimeframeInput, analyze_btmm
from btmm_ai_scanner.btmm.lifecycle import BtmmLifecycleTransition
from btmm_ai_scanner.btmm.observation import BtmmObservation
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.types import (
    ContractModel,
    SemVer,
    SHA256Fingerprint,
    UUIDv7,
)
from btmm_ai_scanner.domain.analyzer import (
    DerivedOutputIdentityProvider,
    _advance_measurement_replay_state,
    _create_initial_measurement_replay_state,
    _measurement_replay_state_to_analysis,
    _MeasurementReplayState,
)
from btmm_ai_scanner.domain.displacement import DisplacementObservation
from btmm_ai_scanner.domain.equal_levels import EqualLevelCluster
from btmm_ai_scanner.domain.support_resistance import SupportResistanceZone
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.domain.trendlines import Trendline
from btmm_ai_scanner.poi.analyzer import (
    PoiTimeframeInput,
    _advance_poi_replay_state,
    _create_initial_poi_replay_state,
    _PoiReplayState,
    analyze_pois,
)
from btmm_ai_scanner.poi.lifecycle import PoiLifecycleTransition
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import (
    _all_symbol,
    _build_setup_summaries,
    _empty_scanner_analysis,
    _max_candle_availability,
    scan_market,
)
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
    canonical_minimum_price_tick,
    validate_configuration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.analyzer import (
    _advance_structure_replay_state,
    _create_initial_structure_replay_state,
    _structure_replay_state_to_analysis,
    _StructureReplayState,
)
from btmm_ai_scanner.structure.transitions import StructureTransition

_TIMEFRAME_RANK: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}


class DetectionMismatch(ContractModel):
    concept_type: str
    expected_content_fingerprint: SHA256Fingerprint | None
    actual_content_fingerprint: SHA256Fingerprint | None
    expected_summary: str
    actual_summary: str
    availability_group_time_utc: datetime
    source_record_ids: tuple[UUIDv7, ...]
    message: str
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer


class ScannerReplayResult(ContractModel):
    symbol: InternalSymbol | None
    snapshots: tuple[ScannerAnalysis, ...]
    final_snapshot: ScannerAnalysis
    detection_mismatches: tuple[DetectionMismatch, ...]
    direct_batch_verified: bool
    minimum_price_tick: Decimal
    availability_time_utc: datetime
    evidence_classification: EvidenceClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer


def _canonical_dump_one(item: object) -> str:
    return json.dumps(
        item.model_dump(mode="json"),  # type: ignore[attr-defined]
        separators=(",", ":"),
    )


def _canonical_dump_many(items: tuple[object, ...]) -> str:
    return json.dumps(
        [item.model_dump(mode="json") for item in items],  # type: ignore[attr-defined]
        separators=(",", ":"),
    )


def _sha256_of(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _diff_identified_records(
    concept_type: str,
    expected_items: tuple[object, ...],
    actual_items: tuple[object, ...],
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> list[DetectionMismatch]:
    expected_by_id = {item.record_id: item for item in expected_items}  # type: ignore[attr-defined]
    actual_by_id = {item.record_id: item for item in actual_items}  # type: ignore[attr-defined]
    all_ids = sorted({*expected_by_id, *actual_by_id}, key=str)

    mismatches: list[DetectionMismatch] = []
    for record_id in all_ids:
        expected_item = expected_by_id.get(record_id)
        actual_item = actual_by_id.get(record_id)
        expected_fp = (
            expected_item.content_fingerprint  # type: ignore[attr-defined]
            if expected_item is not None
            else None
        )
        actual_fp = (
            actual_item.content_fingerprint  # type: ignore[attr-defined]
            if actual_item is not None
            else None
        )
        if expected_fp == actual_fp:
            continue
        mismatches.append(
            DetectionMismatch(
                concept_type=concept_type,
                expected_content_fingerprint=expected_fp,
                actual_content_fingerprint=actual_fp,
                expected_summary=(
                    _canonical_dump_one(expected_item)
                    if expected_item is not None
                    else "MISSING"
                ),
                actual_summary=(
                    _canonical_dump_one(actual_item)
                    if actual_item is not None
                    else "MISSING"
                ),
                availability_group_time_utc=group_time,
                source_record_ids=(record_id,),
                message=(
                    f"direct-batch versus replay content differs for {concept_type} "
                    f"record {record_id} at availability {group_time.isoformat()}."
                ),
                rule_version=replay_configuration.rule_version,
                contract_version=replay_configuration.contract_version,
                schema_version=replay_configuration.schema_version,
            )
        )
    return mismatches


def _diff_setup_summaries(
    expected_summaries: tuple[object, ...],
    actual_summaries: tuple[object, ...],
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> list[DetectionMismatch]:
    expected_by_key = {
        s.source_btmm_observation_record_id: s  # type: ignore[attr-defined]
        for s in expected_summaries
    }
    actual_by_key = {
        s.source_btmm_observation_record_id: s  # type: ignore[attr-defined]
        for s in actual_summaries
    }
    all_keys = sorted({*expected_by_key, *actual_by_key}, key=str)

    mismatches: list[DetectionMismatch] = []
    for key in all_keys:
        expected_item = expected_by_key.get(key)
        actual_item = actual_by_key.get(key)
        expected_fp = (
            _sha256_of(_canonical_dump_one(expected_item))
            if expected_item is not None
            else None
        )
        actual_fp = (
            _sha256_of(_canonical_dump_one(actual_item))
            if actual_item is not None
            else None
        )
        if expected_fp == actual_fp:
            continue
        mismatches.append(
            DetectionMismatch(
                concept_type="setup_summaries",
                expected_content_fingerprint=expected_fp,
                actual_content_fingerprint=actual_fp,
                expected_summary=(
                    _canonical_dump_one(expected_item)
                    if expected_item is not None
                    else "MISSING"
                ),
                actual_summary=(
                    _canonical_dump_one(actual_item)
                    if actual_item is not None
                    else "MISSING"
                ),
                availability_group_time_utc=group_time,
                source_record_ids=(key,),
                message=(
                    "direct-batch versus replay content differs for setup_summaries "
                    f"keyed by source_btmm_observation_record_id {key} at availability "
                    f"{group_time.isoformat()}."
                ),
                rule_version=replay_configuration.rule_version,
                contract_version=replay_configuration.contract_version,
                schema_version=replay_configuration.schema_version,
            )
        )
    return mismatches


def _diff_ordered_primitive_tuple(
    concept_type: str,
    expected_items: tuple[object, ...],
    actual_items: tuple[object, ...],
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> DetectionMismatch | None:
    expected_dump = json.dumps(
        [getattr(item, "value", item) for item in expected_items],
        separators=(",", ":"),
    )
    actual_dump = json.dumps(
        [getattr(item, "value", item) for item in actual_items],
        separators=(",", ":"),
    )
    if expected_dump == actual_dump:
        return None
    return DetectionMismatch(
        concept_type=concept_type,
        expected_content_fingerprint=None,
        actual_content_fingerprint=None,
        expected_summary=expected_dump,
        actual_summary=actual_dump,
        availability_group_time_utc=group_time,
        source_record_ids=(),
        message=(
            f"direct-batch versus replay content differs for concept '{concept_type}'"
            f" at availability {group_time.isoformat()}."
        ),
        rule_version=replay_configuration.rule_version,
        contract_version=replay_configuration.contract_version,
        schema_version=replay_configuration.schema_version,
    )


def _flatten(items: tuple[object, ...], attr: str) -> tuple[object, ...]:
    flattened: list[object] = []
    for item in items:
        flattened.extend(getattr(item, attr))
    return tuple(flattened)


def _flatten_current_structure_states(
    structure_analyses: tuple[object, ...],
) -> tuple[object, ...]:
    return tuple(
        analysis.current_state  # type: ignore[attr-defined]
        for analysis in structure_analyses
        if analysis.current_state is not None  # type: ignore[attr-defined]
    )


def _compare_snapshots(
    expected: ScannerAnalysis,
    actual: ScannerAnalysis,
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> tuple[DetectionMismatch, ...]:
    mismatches: list[DetectionMismatch] = []

    ordered_tuple_mismatch = _diff_ordered_primitive_tuple(
        "processed_timeframes",
        expected.processed_timeframes,
        actual.processed_timeframes,
        group_time,
        replay_configuration,
    )
    if ordered_tuple_mismatch is not None:
        mismatches.append(ordered_tuple_mismatch)

    identified_comparisons: list[tuple[str, tuple[object, ...], tuple[object, ...]]] = [
        (
            "confirmed_swings",
            _flatten(expected.measurement_analyses, "confirmed_swings"),
            _flatten(actual.measurement_analyses, "confirmed_swings"),
        ),
        (
            "displacement_observations",
            _flatten(expected.measurement_analyses, "displacement_observations"),
            _flatten(actual.measurement_analyses, "displacement_observations"),
        ),
        (
            "equal_level_clusters",
            _flatten(expected.measurement_analyses, "equal_level_clusters"),
            _flatten(actual.measurement_analyses, "equal_level_clusters"),
        ),
        (
            "support_resistance_zones",
            _flatten(expected.measurement_analyses, "support_resistance_zones"),
            _flatten(actual.measurement_analyses, "support_resistance_zones"),
        ),
        (
            "trendlines",
            _flatten(expected.measurement_analyses, "trendlines"),
            _flatten(actual.measurement_analyses, "trendlines"),
        ),
        (
            "swing_relationships",
            _flatten(expected.structure_analyses, "swing_relationships"),
            _flatten(actual.structure_analyses, "swing_relationships"),
        ),
        (
            "structure_transitions",
            _flatten(expected.structure_analyses, "structure_transitions"),
            _flatten(actual.structure_analyses, "structure_transitions"),
        ),
        (
            "current_structure_states",
            _flatten_current_structure_states(expected.structure_analyses),
            _flatten_current_structure_states(actual.structure_analyses),
        ),
        (
            "poi_observations",
            expected.poi_analysis.poi_observations,
            actual.poi_analysis.poi_observations,
        ),
        (
            "poi_lifecycle_transitions",
            expected.poi_analysis.poi_lifecycle_transitions,
            actual.poi_analysis.poi_lifecycle_transitions,
        ),
        (
            "current_poi_states",
            expected.poi_analysis.current_poi_states,
            actual.poi_analysis.current_poi_states,
        ),
        (
            "btmm_observations",
            expected.btmm_analysis.btmm_observations,
            actual.btmm_analysis.btmm_observations,
        ),
        (
            "btmm_lifecycle_transitions",
            expected.btmm_analysis.btmm_lifecycle_transitions,
            actual.btmm_analysis.btmm_lifecycle_transitions,
        ),
        (
            "current_btmm_states",
            expected.btmm_analysis.current_btmm_states,
            actual.btmm_analysis.current_btmm_states,
        ),
    ]
    for concept_type, expected_items, actual_items in identified_comparisons:
        mismatches.extend(
            _diff_identified_records(
                concept_type,
                expected_items,
                actual_items,
                group_time,
                replay_configuration,
            )
        )

    mismatches.extend(
        _diff_setup_summaries(
            expected.setup_summaries,
            actual.setup_summaries,
            group_time,
            replay_configuration,
        )
    )

    return tuple(mismatches)


# =====================================================================
# Subsystem 2f: private event ledger + incremental availability-group replay
# kernel (register §44P/§44U).
#
# scan_market and every batch analyzer are preserved byte-for-byte and remain
# the sole semantic oracle. The kernel replaces only run_scanner_replay's
# internal per-group scan_market loop for the FINAL_ONLY retention policy — the
# historical-backtest optimized path — advancing the per-timeframe incremental
# measurement (2b), structure (2c), and POI (2d) states one availability group
# at a time instead of re-running scan_market over the complete growing prefix.
# It materializes exactly one final ScannerAnalysis, so no tuple of full
# ScannerAnalysis snapshots is retained per group — removing the historical
# snapshot-memory pathology while POI/BTMM run once (not once per group).
#
# ALL and CHANGED_ONLY keep the existing, unchanged per-group scan_market loop
# (their general-purpose semantics and every existing test are preserved).
#
# Cross-timeframe POI merge/overlap and BTMM span timeframes; the single-
# timeframe 2d/2e engines are validated by their own differential suites, and
# the kernel materializes the cross-timeframe POI/BTMM output via the unchanged
# batch analyze_pois/analyze_btmm at finalization (the exact oracle, run once
# under FINAL_ONLY). measurement_analyses/structure_analyses come from the
# incremental 2b/2c states, so the final ScannerAnalysis is byte-identical to
# scan_market over the full prefix.
# =====================================================================


@dataclass
class _ScannerEventLedger:
    """Private, order-preserving accumulator of the classification-A semantic
    records the final ScannerAnalysis requires (register §44U2 + §44AJ warnings
    field). Built from the incremental domain states and the finalized POI/BTMM
    analyses at materialization; it holds semantic records, never full
    ScannerAnalysis snapshots. `warnings` is present for §44U2 fidelity but is
    always empty — the current scanner emits no warnings (ScannerAnalysis has no
    warnings field). Growth is output-sensitive, not constant."""

    confirmed_swings: tuple[ConfirmedSwing, ...] = ()
    displacement_observations: tuple[DisplacementObservation, ...] = ()
    equal_level_clusters: tuple[EqualLevelCluster, ...] = ()
    support_resistance_zones: tuple[SupportResistanceZone, ...] = ()
    trendlines: tuple[Trendline, ...] = ()
    structure_transitions: tuple[StructureTransition, ...] = ()
    poi_observations: tuple[PoiObservation, ...] = ()
    poi_lifecycle_transitions: tuple[PoiLifecycleTransition, ...] = ()
    btmm_observations: tuple[BtmmObservation, ...] = ()
    btmm_lifecycle_transitions: tuple[BtmmLifecycleTransition, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass
class _ScannerOrchestrationReplayState:
    """Private per-replay kernel state (register §44U). Holds the per-timeframe
    incremental domain states plus the accumulated visible candles — bounded by
    real market output, never a tuple of full ScannerAnalysis snapshots."""

    measurement_states: dict[Timeframe, _MeasurementReplayState]
    structure_states: dict[Timeframe, _StructureReplayState]
    poi_states: dict[Timeframe, _PoiReplayState]
    visible_candles: dict[Timeframe, tuple[NormalizedCandle, ...]]


class IncrementalReplayKernel:
    """Private single-pass availability-group replay engine (register §44P).
    Not exported. Advances per-timeframe measurement→structure→POI incremental
    states one availability group at a time; finalizes exactly one
    ScannerAnalysis identical in public shape to scan_market over the full
    prefix."""

    def __init__(
        self,
        tracked_timeframes: tuple[Timeframe, ...],
        scanner_configuration: ScannerConfiguration,
        identity_provider: DerivedOutputIdentityProvider,
    ) -> None:
        self._config = scanner_configuration
        self._identity_provider = identity_provider
        self._tracked = tracked_timeframes
        measurement_cfg = scanner_configuration.measurement_configuration
        structure_cfg = scanner_configuration.structure_configuration
        poi_cfg = scanner_configuration.poi_configuration
        self._state = _ScannerOrchestrationReplayState(
            measurement_states={
                tf: _create_initial_measurement_replay_state(
                    identity_provider, measurement_cfg
                )
                for tf in tracked_timeframes
            },
            structure_states={
                tf: _create_initial_structure_replay_state(
                    identity_provider, structure_cfg
                )
                for tf in tracked_timeframes
            },
            poi_states={
                tf: _create_initial_poi_replay_state(identity_provider, poi_cfg)
                for tf in tracked_timeframes
            },
            visible_candles=dict.fromkeys(tracked_timeframes, ()),
        )
        self._processed_group_count = 0
        self._ledger = _ScannerEventLedger()

    def advance_group(
        self, new_candles_by_timeframe: dict[Timeframe, tuple[NormalizedCandle, ...]]
    ) -> None:
        """Advance one availability group. Transactional: builds replacement
        domain states in locals and publishes the new orchestration state only
        after every timeframe and every candle succeeds, so a raised exception
        (e.g. a domain failure) leaves the prior kernel state untouched."""
        measurement_cfg = self._config.measurement_configuration
        structure_cfg = self._config.structure_configuration
        poi_cfg = self._config.poi_configuration
        prior = self._state

        new_measurement = dict(prior.measurement_states)
        new_structure = dict(prior.structure_states)
        new_poi = dict(prior.poi_states)
        new_visible = dict(prior.visible_candles)

        for timeframe in self._tracked:
            candles = new_candles_by_timeframe.get(timeframe, ())
            if len(candles) == 0:
                continue
            measurement_state = prior.measurement_states[timeframe]
            structure_state = prior.structure_states[timeframe]
            poi_state = prior.poi_states[timeframe]
            visible = prior.visible_candles[timeframe]
            for candle in candles:
                measurement_state = _advance_measurement_replay_state(
                    measurement_state, candle, measurement_cfg
                )
                measurement = _measurement_replay_state_to_analysis(measurement_state)
                structure_state = _advance_structure_replay_state(
                    structure_state, candle, measurement.confirmed_swings, structure_cfg
                )
                poi_state = _advance_poi_replay_state(
                    poi_state, candle, measurement, poi_cfg
                )
                visible = (*visible, candle)
            new_measurement[timeframe] = measurement_state
            new_structure[timeframe] = structure_state
            new_poi[timeframe] = poi_state
            new_visible[timeframe] = visible

        self._state = _ScannerOrchestrationReplayState(
            measurement_states=new_measurement,
            structure_states=new_structure,
            poi_states=new_poi,
            visible_candles=new_visible,
        )
        self._processed_group_count += 1

    def _ordered_active_timeframes(self) -> tuple[Timeframe, ...]:
        return tuple(sorted(self._tracked, key=lambda tf: _TIMEFRAME_RANK[tf]))

    def finalize(
        self, reviewed_evidence: tuple[BtmmReviewedEvidence, ...]
    ) -> ScannerAnalysis:
        """Materialize exactly one ScannerAnalysis from the final incremental
        measurement/structure states plus the unchanged batch analyze_pois /
        analyze_btmm (the exact cross-timeframe oracle, run once). Byte-identical
        in public shape to scan_market over the full prefix."""
        state = self._state
        config = self._config
        identity_provider = self._identity_provider

        if all(len(state.visible_candles[tf]) == 0 for tf in self._tracked):
            self._ledger = _ScannerEventLedger()
            return _empty_scanner_analysis(config, identity_provider)

        ordered = self._ordered_active_timeframes()
        measurement_analyses = tuple(
            _measurement_replay_state_to_analysis(state.measurement_states[tf])
            for tf in ordered
        )
        structure_analyses = tuple(
            _structure_replay_state_to_analysis(state.structure_states[tf])
            for tf in ordered
        )

        poi_inputs = tuple(
            PoiTimeframeInput(
                timeframe=tf,
                candles=state.visible_candles[tf],
                measurement_analysis=measurement_analyses[index],
            )
            for index, tf in enumerate(ordered)
        )
        poi_analysis = analyze_pois(
            poi_inputs, config.poi_configuration, identity_provider
        )

        btmm_eligible = (
            config.btmm_configuration.formation_timeframes
            | config.btmm_configuration.supporting_only_timeframes
        )
        scanner_bundles = tuple(
            ScannerTimeframeInput(timeframe=tf, candles=state.visible_candles[tf])
            for tf in ordered
        )
        max_candle_availability = _max_candle_availability(scanner_bundles)
        gated_evidence = tuple(
            evidence
            for evidence in reviewed_evidence
            if evidence.availability_time_utc <= max_candle_availability
        )
        btmm_inputs = tuple(
            BtmmTimeframeInput(
                timeframe=tf,
                candles=state.visible_candles[tf],
                measurement_analysis=measurement_analyses[index],
            )
            for index, tf in enumerate(ordered)
            if tf in btmm_eligible
        )
        btmm_analysis = analyze_btmm(
            btmm_inputs,
            poi_analysis,
            gated_evidence,
            config.btmm_configuration,
            identity_provider,
        )

        setup_summaries = _build_setup_summaries(poi_analysis, btmm_analysis)
        symbol = _all_symbol(scanner_bundles)

        self._ledger = _ScannerEventLedger(
            confirmed_swings=tuple(
                swing
                for analysis in measurement_analyses
                for swing in analysis.confirmed_swings
            ),
            displacement_observations=tuple(
                observation
                for analysis in measurement_analyses
                for observation in analysis.displacement_observations
            ),
            equal_level_clusters=tuple(
                cluster
                for analysis in measurement_analyses
                for cluster in analysis.equal_level_clusters
            ),
            support_resistance_zones=tuple(
                zone
                for analysis in measurement_analyses
                for zone in analysis.support_resistance_zones
            ),
            trendlines=tuple(
                trendline
                for analysis in measurement_analyses
                for trendline in analysis.trendlines
            ),
            structure_transitions=tuple(
                transition
                for analysis in structure_analyses
                for transition in analysis.structure_transitions
            ),
            poi_observations=poi_analysis.poi_observations,
            poi_lifecycle_transitions=poi_analysis.poi_lifecycle_transitions,
            btmm_observations=btmm_analysis.btmm_observations,
            btmm_lifecycle_transitions=btmm_analysis.btmm_lifecycle_transitions,
            warnings=(),
        )

        return ScannerAnalysis(
            symbol=symbol,
            processed_timeframes=ordered,
            measurement_analyses=measurement_analyses,
            structure_analyses=structure_analyses,
            poi_analysis=poi_analysis,
            btmm_analysis=btmm_analysis,
            setup_summaries=setup_summaries,
            availability_time_utc=max_candle_availability,
            evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
            rule_version=config.rule_version,
            contract_version=config.contract_version,
            schema_version=config.schema_version,
        )

    def event_ledger(self) -> _ScannerEventLedger:
        return self._ledger

    def processed_group_count(self) -> int:
        return self._processed_group_count


def run_scanner_replay(
    historical_inputs: tuple[ScannerTimeframeInput, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    scanner_configuration: ScannerConfiguration,
    replay_configuration: ReplayConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> ScannerReplayResult:
    validate_configuration(scanner_configuration)
    minimum_price_tick = canonical_minimum_price_tick(scanner_configuration)

    if len(historical_inputs) == 0:
        empty_snapshot = scan_market((), (), scanner_configuration, identity_provider)
        return ScannerReplayResult(
            symbol=None,
            snapshots=(),
            final_snapshot=empty_snapshot,
            detection_mismatches=(),
            direct_batch_verified=False,
            minimum_price_tick=minimum_price_tick,
            availability_time_utc=empty_snapshot.availability_time_utc,
            evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
            rule_version=replay_configuration.rule_version,
            contract_version=replay_configuration.contract_version,
            schema_version=replay_configuration.schema_version,
        )

    tracked_timeframes = tuple(
        sorted(
            (bundle.timeframe for bundle in historical_inputs),
            key=lambda tf: _TIMEFRAME_RANK[tf],
        )
    )

    flat_candles: list[tuple[datetime, datetime, str, Timeframe, NormalizedCandle]] = []
    for bundle in historical_inputs:
        for candle in bundle.candles:
            flat_candles.append(
                (
                    candle.availability_time_utc,
                    candle.event_time_utc,
                    str(candle.record_id),
                    bundle.timeframe,
                    candle,
                )
            )
    flat_candles.sort(key=lambda row: (row[0], row[1], row[2]))

    visible_by_timeframe: dict[Timeframe, list[NormalizedCandle]] = {
        timeframe: [] for timeframe in tracked_timeframes
    }

    snapshots: list[ScannerAnalysis] = []
    final_snapshot: ScannerAnalysis | None = None

    if len(flat_candles) == 0:
        final_snapshot = scan_market(
            historical_inputs, (), scanner_configuration, identity_provider
        )
        snapshots = [final_snapshot]
    elif replay_configuration.snapshot_retention == SnapshotRetentionPolicy.FINAL_ONLY:
        # Historical-backtest optimized path: advance the incremental kernel one
        # availability group at a time (never re-running scan_market over the
        # growing prefix) and materialize exactly one final ScannerAnalysis.
        kernel = IncrementalReplayKernel(
            tracked_timeframes, scanner_configuration, identity_provider
        )
        index = 0
        total = len(flat_candles)
        while index < total:
            group_availability = flat_candles[index][0]
            group_end = index
            group_new_candles: dict[Timeframe, list[NormalizedCandle]] = {
                timeframe: [] for timeframe in tracked_timeframes
            }
            while (
                group_end < total and flat_candles[group_end][0] == group_availability
            ):
                group_new_candles[flat_candles[group_end][3]].append(
                    flat_candles[group_end][4]
                )
                group_end += 1
            index = group_end
            kernel.advance_group(
                {
                    timeframe: tuple(candles)
                    for timeframe, candles in group_new_candles.items()
                }
            )
        final_snapshot = kernel.finalize(reviewed_evidence)
    else:
        index = 0
        total = len(flat_candles)
        while index < total:
            group_availability = flat_candles[index][0]
            group_end = index
            while (
                group_end < total and flat_candles[group_end][0] == group_availability
            ):
                visible_by_timeframe[flat_candles[group_end][3]].append(
                    flat_candles[group_end][4]
                )
                group_end += 1
            index = group_end

            prefix_bundles = tuple(
                ScannerTimeframeInput(
                    timeframe=timeframe,
                    candles=tuple(visible_by_timeframe[timeframe]),
                )
                for timeframe in tracked_timeframes
            )
            gated_evidence = tuple(
                evidence
                for evidence in reviewed_evidence
                if evidence.availability_time_utc <= group_availability
            )

            snapshot = scan_market(
                prefix_bundles, gated_evidence, scanner_configuration, identity_provider
            )
            final_snapshot = snapshot

            if replay_configuration.snapshot_retention == SnapshotRetentionPolicy.ALL:
                snapshots.append(snapshot)
            elif len(snapshots) == 0 or json.dumps(
                snapshots[-1].model_dump(mode="json"), separators=(",", ":")
            ) != json.dumps(snapshot.model_dump(mode="json"), separators=(",", ":")):
                snapshots.append(snapshot)

    assert final_snapshot is not None

    if replay_configuration.snapshot_retention == SnapshotRetentionPolicy.FINAL_ONLY:
        snapshots = [final_snapshot]

    detection_mismatches: tuple[DetectionMismatch, ...] = ()
    if replay_configuration.verify_against_direct_batch:
        direct_batch_snapshot = scan_market(
            historical_inputs,
            reviewed_evidence,
            scanner_configuration,
            identity_provider,
        )
        detection_mismatches = _compare_snapshots(
            direct_batch_snapshot,
            final_snapshot,
            final_snapshot.availability_time_utc,
            replay_configuration,
        )

    return ScannerReplayResult(
        symbol=final_snapshot.symbol,
        snapshots=tuple(snapshots),
        final_snapshot=final_snapshot,
        detection_mismatches=detection_mismatches,
        direct_batch_verified=replay_configuration.verify_against_direct_batch,
        minimum_price_tick=minimum_price_tick,
        availability_time_utc=final_snapshot.availability_time_utc,
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        rule_version=replay_configuration.rule_version,
        contract_version=replay_configuration.contract_version,
        schema_version=replay_configuration.schema_version,
    )
