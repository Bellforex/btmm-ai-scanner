from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.reviewed_evidence import BtmmReviewedEvidence
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.health import build_scanner_health_report
from btmm_ai_scanner.scanner.replay import ScannerReplayResult, run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class _SequentialIdentityProvider:
    def __init__(self) -> None:
        self._map: dict[object, UUID] = {}
        self._counter = 0

    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        key = (output_type, semantic_key)
        if key not in self._map:
            self._counter += 1
            self._map[key] = UUID(f"0193f450-0000-7000-8000-{self._counter:012x}")
        return self._map[key]


def _candle(
    index: int,
    timeframe: Timeframe,
    minutes_offset: int,
    open_: str = "100",
    high: str = "100.5",
    low: str = "99.5",
    close: str = "100.2",
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=minutes_offset)
    availability = event_time + timedelta(seconds=1)
    tag = {Timeframe.M1: 1, Timeframe.M5: 2, Timeframe.M15: 3}[timeframe]
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f450-1234-7abc-8{tag:03x}-{index:012x}"),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": timeframe.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": timeframe,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(open_),
            "high": Decimal(high),
            "low": Decimal(low),
            "close": Decimal(close),
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV_ID,
        }
    )


def _config() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
    )


def _inputs() -> tuple[ScannerTimeframeInput, ...]:
    engulfed = _candle(0, Timeframe.M1, 0, "100", "100", "99", "99")
    engulfing = _candle(1, Timeframe.M1, 1, "99", "101", "99", "101")
    return (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=(engulfed, engulfing)),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5, candles=(_candle(0, Timeframe.M5, 0),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_candle(0, Timeframe.M15, 0),)
        ),
    )


def _replay_result(
    reviewed_evidence: tuple[BtmmReviewedEvidence, ...] = (),
) -> ScannerReplayResult:
    replay_config = ReplayConfiguration(
        snapshot_retention=SnapshotRetentionPolicy.ALL,
        verify_against_direct_batch=True,
    )
    return run_scanner_replay(
        _inputs(),
        reviewed_evidence,
        _config(),
        replay_config,
        _SequentialIdentityProvider(),
    )


def test_health_report_counts_candles_and_availability_groups_processed() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.candles_processed == 4
    assert report.availability_groups_processed == len(replay.snapshots)


def test_health_report_counts_symbols_and_timeframes_processed() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.symbols_processed == 1
    assert report.timeframes_processed == 3


def test_health_report_counts_gaps_duplicates_and_invalid_candles_rejected() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.gaps_encountered == 0
    assert report.duplicates_rejected == 0
    assert report.invalid_candles_rejected == 0


def test_health_report_counts_reviewed_evidence_records_consumed() -> None:
    replay_without_evidence = _replay_result()
    report_without = build_scanner_health_report(
        replay_without_evidence, Decimal("0.01")
    )
    assert report_without.reviewed_evidence_consumed == 0

    baseline_state = (
        replay_without_evidence.final_snapshot.btmm_analysis.current_btmm_states[0]
    )
    consumed_state = baseline_state.model_copy(
        update={
            "reviewed_evidence_availability_time_utc": baseline_state.availability_time_utc
        }
    )
    updated_btmm_analysis = (
        replay_without_evidence.final_snapshot.btmm_analysis.model_copy(
            update={"current_btmm_states": (consumed_state,)}
        )
    )
    updated_final_snapshot = replay_without_evidence.final_snapshot.model_copy(
        update={"btmm_analysis": updated_btmm_analysis}
    )
    updated_replay = replay_without_evidence.model_copy(
        update={"final_snapshot": updated_final_snapshot}
    )
    report_with = build_scanner_health_report(updated_replay, Decimal("0.01"))
    assert report_with.reviewed_evidence_consumed == 1


def test_health_report_counts_retained_snapshots() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.retained_snapshot_count == len(replay.snapshots)


def test_health_report_counts_replay_mismatches_and_identity_collisions() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.replay_mismatch_count == len(replay.detection_mismatches)
    assert report.identity_collision_count == 0


def test_health_report_counts_typed_errors_encountered() -> None:
    replay = _replay_result()
    report = build_scanner_health_report(replay, Decimal("0.01"))
    assert report.typed_error_count == 0


def test_health_report_runtime_is_informational_and_excluded_from_equality() -> None:
    replay = _replay_result()
    report_a = build_scanner_health_report(replay, Decimal("0.001"))
    report_b = build_scanner_health_report(replay, Decimal("999.999"))
    comparable_a = report_a.model_dump(exclude={"runtime_seconds"})
    comparable_b = report_b.model_dump(exclude={"runtime_seconds"})
    assert comparable_a == comparable_b
    assert report_a.runtime_seconds != report_b.runtime_seconds
