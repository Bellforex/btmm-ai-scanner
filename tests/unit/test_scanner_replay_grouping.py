import time
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import (
    BtmmContextAlignmentStatus,
    BtmmEvidenceSource,
    BtmmLiquidityEvidenceStatus,
    BtmmSessionStatus,
    BtmmVolumePillarStatus,
)
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
from btmm_ai_scanner.scanner.replay import run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

_TIMEFRAME_TAG: dict[Timeframe, int] = {
    Timeframe.M1: 1,
    Timeframe.M5: 2,
    Timeframe.M15: 3,
    Timeframe.H1: 4,
    Timeframe.H3: 5,
    Timeframe.H4: 6,
    Timeframe.D1: 7,
    Timeframe.W1: 8,
}


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
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(
                f"0193f450-1234-7abc-8{_TIMEFRAME_TAG[timeframe]:03x}-{index:012x}"
            ),
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


def _replay_config(**overrides: object) -> ReplayConfiguration:
    fields: dict[str, object] = {
        "snapshot_retention": SnapshotRetentionPolicy.ALL,
        "verify_against_direct_batch": False,
    }
    fields.update(overrides)
    return ReplayConfiguration(**fields)  # type: ignore[arg-type]


def _three_group_inputs() -> tuple[ScannerTimeframeInput, ...]:
    m1_candles = (
        _candle(0, Timeframe.M1, 0),
        _candle(1, Timeframe.M1, 1),
        _candle(2, Timeframe.M1, 2),
    )
    m5_candles = (_candle(0, Timeframe.M5, 0),)
    m15_candles = (_candle(0, Timeframe.M15, 0),)
    return (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=m1_candles),
        ScannerTimeframeInput(timeframe=Timeframe.M5, candles=m5_candles),
        ScannerTimeframeInput(timeframe=Timeframe.M15, candles=m15_candles),
    )


def test_multi_timeframe_candles_merged_into_global_availability_groups() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    assert len(result.snapshots) == 3
    assert (
        result.final_snapshot.measurement_analyses[
            [m.timeframe for m in result.final_snapshot.measurement_analyses].index(
                Timeframe.M1
            )
        ].analyzed_candle_count
        == 3
    )


def test_availability_group_appended_atomically_across_timeframes() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    first_snapshot = result.snapshots[0]
    m1_analysis = next(
        m for m in first_snapshot.measurement_analyses if m.timeframe == Timeframe.M1
    )
    m5_analysis = next(
        m for m in first_snapshot.measurement_analyses if m.timeframe == Timeframe.M5
    )
    m15_analysis = next(
        m for m in first_snapshot.measurement_analyses if m.timeframe == Timeframe.M15
    )
    assert m1_analysis.analyzed_candle_count == 1
    assert m5_analysis.analyzed_candle_count == 1
    assert m15_analysis.analyzed_candle_count == 1


def test_replay_with_missing_optional_timeframe_still_proceeds() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    assert Timeframe.H1 not in result.final_snapshot.processed_timeframes
    assert result.final_snapshot.symbol == InternalSymbol.XAUUSD


def test_duplicate_availability_group_never_double_processed() -> None:
    m1_candles = (
        _candle(0, Timeframe.M1, 0),
        _candle(1, Timeframe.M1, 1),
    )
    m5_candles = (_candle(0, Timeframe.M5, 1),)
    inputs = (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=m1_candles),
        ScannerTimeframeInput(timeframe=Timeframe.M5, candles=m5_candles),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_candle(0, Timeframe.M15, 0),)
        ),
    )
    result = run_scanner_replay(
        inputs, (), _config(), _replay_config(), _SequentialIdentityProvider()
    )
    assert len(result.snapshots) == 2


def test_changed_only_snapshot_retention_omits_unchanged_snapshots() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(snapshot_retention=SnapshotRetentionPolicy.CHANGED_ONLY),
        _SequentialIdentityProvider(),
    )
    assert len(result.snapshots) <= 1


def test_all_snapshot_retention_keeps_every_group_snapshot() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(snapshot_retention=SnapshotRetentionPolicy.ALL),
        _SequentialIdentityProvider(),
    )
    assert len(result.snapshots) == 3


def test_reviewed_evidence_visible_only_at_or_after_its_own_availability() -> None:
    engulfed = _candle(0, Timeframe.M1, 0, "100", "100", "99", "99")
    engulfing = _candle(1, Timeframe.M1, 1, "99", "101", "99", "101")
    inputs = (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=(engulfed, engulfing)),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5, candles=(_candle(0, Timeframe.M5, 0),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_candle(0, Timeframe.M15, 0),)
        ),
    )
    direct = run_scanner_replay(
        inputs, (), _config(), _replay_config(), _SequentialIdentityProvider()
    )
    source_poi = next(
        obs
        for obs in direct.final_snapshot.poi_analysis.poi_observations
        if obs.poi_type.value == "BULLISH_ENGULFING"
    )
    far_future_evidence = BtmmReviewedEvidence(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        source_poi_record_id=source_poi.record_id,
        market_direction_status=BtmmContextAlignmentStatus.ALIGNED,
        analytical_framework_status=BtmmContextAlignmentStatus.ALIGNED,
        session_status=BtmmSessionStatus.ACTIVE,
        liquidity_evidence_status=BtmmLiquidityEvidenceStatus.PRESENT,
        volume_pillar_status=BtmmVolumePillarStatus.SUPPORTS,
        context_input_source=BtmmEvidenceSource.EXPERT_LABELLED,
        liquidity_event_source=BtmmEvidenceSource.EXPERT_LABELLED,
        volume_evidence_source=BtmmEvidenceSource.EXPERT_LABELLED,
        availability_time_utc=direct.availability_time_utc + timedelta(days=1),
        rule_version=SemVer.parse("0.1.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
    )
    gated = run_scanner_replay(
        inputs,
        (far_future_evidence,),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    for state in gated.final_snapshot.btmm_analysis.current_btmm_states:
        assert state.reviewed_evidence_availability_time_utc is None


def test_replay_runner_uses_no_wall_clock_or_sleep() -> None:
    started = time.perf_counter()
    run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    elapsed = time.perf_counter() - started
    assert elapsed < 2.0


def test_replay_snapshots_are_deterministic_across_runs() -> None:
    result_a = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    result_b = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    assert len(result_a.snapshots) == len(result_b.snapshots)
    assert (
        result_a.final_snapshot.measurement_analyses[0].analyzed_candle_count
        == result_b.final_snapshot.measurement_analyses[0].analyzed_candle_count
    )


def test_replay_produces_one_final_snapshot() -> None:
    result = run_scanner_replay(
        _three_group_inputs(),
        (),
        _config(),
        _replay_config(),
        _SequentialIdentityProvider(),
    )
    assert result.final_snapshot is not None
    assert result.final_snapshot == result.snapshots[-1]
