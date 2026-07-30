import json
from datetime import datetime

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
from btmm_ai_scanner.domain.analyzer import DerivedOutputIdentityProvider
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput

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
    availability_time_utc: datetime
    evidence_classification: EvidenceClassification
    rule_version: SemVer
    contract_version: SemVer
    schema_version: SemVer


_IDENTIFIED_CONCEPT_RECORD_IDS: frozenset[str] = frozenset(
    {
        "poi_observations",
        "poi_lifecycle_transitions",
        "current_poi_states",
        "btmm_observations",
        "btmm_lifecycle_transitions",
        "current_btmm_states",
    }
)


def _canonical_dump(items: tuple[object, ...]) -> str:
    return json.dumps(
        [item.model_dump(mode="json") for item in items],  # type: ignore[attr-defined]
        separators=(",", ":"),
    )


def _record_ids(items: tuple[object, ...]) -> tuple[UUIDv7, ...]:
    return tuple(item.record_id for item in items)  # type: ignore[attr-defined]


def _compare_concept(
    concept_type: str,
    expected_items: tuple[object, ...],
    actual_items: tuple[object, ...],
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> DetectionMismatch | None:
    expected_dump = _canonical_dump(expected_items)
    actual_dump = _canonical_dump(actual_items)
    if expected_dump == actual_dump:
        return None

    source_record_ids: tuple[UUIDv7, ...] = ()
    if concept_type in _IDENTIFIED_CONCEPT_RECORD_IDS:
        combined = {*_record_ids(expected_items), *_record_ids(actual_items)}
        source_record_ids = tuple(sorted(combined, key=str))

    return DetectionMismatch(
        concept_type=concept_type,
        expected_content_fingerprint=None,
        actual_content_fingerprint=None,
        expected_summary=expected_dump,
        actual_summary=actual_dump,
        availability_group_time_utc=group_time,
        source_record_ids=source_record_ids,
        message=(
            f"direct-batch versus replay content differs for concept '{concept_type}'"
            f" at availability {group_time.isoformat()}."
        ),
        rule_version=replay_configuration.rule_version,
        contract_version=replay_configuration.contract_version,
        schema_version=replay_configuration.schema_version,
    )


def _compare_snapshots(
    expected: ScannerAnalysis,
    actual: ScannerAnalysis,
    group_time: datetime,
    replay_configuration: ReplayConfiguration,
) -> tuple[DetectionMismatch, ...]:
    comparisons: list[tuple[str, tuple[object, ...], tuple[object, ...]]] = [
        (
            "measurement_analyses",
            expected.measurement_analyses,
            actual.measurement_analyses,
        ),
        ("structure_analyses", expected.structure_analyses, actual.structure_analyses),
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
        ("setup_summaries", expected.setup_summaries, actual.setup_summaries),
    ]

    mismatches: list[DetectionMismatch] = []
    for concept_type, expected_items, actual_items in comparisons:
        mismatch = _compare_concept(
            concept_type, expected_items, actual_items, group_time, replay_configuration
        )
        if mismatch is not None:
            mismatches.append(mismatch)
    return tuple(mismatches)


def run_scanner_replay(
    historical_inputs: tuple[ScannerTimeframeInput, ...],
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...],
    scanner_configuration: ScannerConfiguration,
    replay_configuration: ReplayConfiguration,
    identity_provider: DerivedOutputIdentityProvider,
) -> ScannerReplayResult:
    if len(historical_inputs) == 0:
        empty_snapshot = scan_market((), (), scanner_configuration, identity_provider)
        return ScannerReplayResult(
            symbol=None,
            snapshots=(),
            final_snapshot=empty_snapshot,
            detection_mismatches=(),
            direct_batch_verified=False,
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
            elif (
                len(snapshots) == 0
                or snapshots[-1].setup_summaries != snapshot.setup_summaries
            ):
                snapshots.append(snapshot)

    assert final_snapshot is not None

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
        availability_time_utc=final_snapshot.availability_time_utc,
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        rule_version=replay_configuration.rule_version,
        contract_version=replay_configuration.contract_version,
        schema_version=replay_configuration.schema_version,
    )
