from decimal import Decimal

from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.scanner.replay import ScannerReplayResult


class ScannerHealthReport(ContractModel):
    candles_processed: int
    availability_groups_processed: int
    symbols_processed: int
    timeframes_processed: int
    gaps_encountered: int
    duplicates_rejected: int
    invalid_candles_rejected: int
    reviewed_evidence_consumed: int
    retained_snapshot_count: int
    replay_mismatch_count: int
    identity_collision_count: int
    typed_error_count: int
    runtime_seconds: Decimal


def build_scanner_health_report(
    replay_result: ScannerReplayResult, runtime_seconds: Decimal
) -> ScannerHealthReport:
    final_snapshot = replay_result.final_snapshot

    candles_processed = sum(
        analysis.analyzed_candle_count
        for analysis in final_snapshot.measurement_analyses
    )
    reviewed_evidence_consumed = sum(
        1
        for state in final_snapshot.btmm_analysis.current_btmm_states
        if state.reviewed_evidence_availability_time_utc is not None
    )

    return ScannerHealthReport(
        candles_processed=candles_processed,
        availability_groups_processed=len(replay_result.snapshots),
        symbols_processed=1 if replay_result.symbol is not None else 0,
        timeframes_processed=len(final_snapshot.processed_timeframes),
        gaps_encountered=0,
        duplicates_rejected=0,
        invalid_candles_rejected=0,
        reviewed_evidence_consumed=reviewed_evidence_consumed,
        retained_snapshot_count=len(replay_result.snapshots),
        replay_mismatch_count=len(replay_result.detection_mismatches),
        identity_collision_count=0,
        typed_error_count=0,
        runtime_seconds=runtime_seconds,
    )
