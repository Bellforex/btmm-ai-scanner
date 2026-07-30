from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
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


def _random_uuidv7() -> UUID:
    random_bytes = bytearray(uuid4().bytes)
    random_bytes[6] = (random_bytes[6] & 0x0F) | 0x70
    random_bytes[8] = (random_bytes[8] & 0x3F) | 0x80
    return UUID(bytes=bytes(random_bytes))


class _CallOrderDependentIdentityProvider:
    def identify(
        self, *, output_type: DerivedOutputType, semantic_key: tuple[str, ...]
    ) -> UUID:
        del output_type, semantic_key
        return _random_uuidv7()


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


def _batch_and_replay() -> tuple[ScannerAnalysis, ScannerReplayResult]:
    shared_provider = _SequentialIdentityProvider()
    batch = scan_market(_inputs(), (), _config(), shared_provider)
    replay_config = ReplayConfiguration(
        snapshot_retention=SnapshotRetentionPolicy.ALL,
        verify_against_direct_batch=True,
    )
    replay = run_scanner_replay(
        _inputs(), (), _config(), replay_config, shared_provider
    )
    return batch, replay


def test_batch_and_replay_measurement_analyses_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert batch.measurement_analyses == replay.final_snapshot.measurement_analyses


def test_batch_and_replay_structure_analyses_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert batch.structure_analyses == replay.final_snapshot.structure_analyses


def test_batch_and_replay_poi_observations_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert (
        batch.poi_analysis.poi_observations
        == replay.final_snapshot.poi_analysis.poi_observations
    )


def test_batch_and_replay_poi_lifecycle_transitions_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert (
        batch.poi_analysis.poi_lifecycle_transitions
        == replay.final_snapshot.poi_analysis.poi_lifecycle_transitions
    )


def test_batch_and_replay_current_poi_states_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert (
        batch.poi_analysis.current_poi_states
        == replay.final_snapshot.poi_analysis.current_poi_states
    )


def test_batch_and_replay_btmm_observations_and_transitions_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert (
        batch.btmm_analysis.btmm_observations
        == replay.final_snapshot.btmm_analysis.btmm_observations
    )
    assert (
        batch.btmm_analysis.btmm_lifecycle_transitions
        == replay.final_snapshot.btmm_analysis.btmm_lifecycle_transitions
    )


def test_batch_and_replay_current_btmm_states_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert (
        batch.btmm_analysis.current_btmm_states
        == replay.final_snapshot.btmm_analysis.current_btmm_states
    )


def test_batch_and_replay_scanner_setup_summaries_are_identical() -> None:
    batch, replay = _batch_and_replay()
    assert batch.setup_summaries == replay.final_snapshot.setup_summaries


def test_batch_and_replay_identities_and_fingerprints_match() -> None:
    batch, replay = _batch_and_replay()
    assert replay.direct_batch_verified is True
    assert replay.detection_mismatches == ()
    batch_ids = [o.record_id for o in batch.poi_analysis.poi_observations]
    replay_ids = [
        o.record_id for o in replay.final_snapshot.poi_analysis.poi_observations
    ]
    assert batch_ids == replay_ids


def test_mismatched_batch_and_replay_produces_detection_mismatch() -> None:
    replay_config = ReplayConfiguration(
        snapshot_retention=SnapshotRetentionPolicy.ALL,
        verify_against_direct_batch=True,
    )
    result = run_scanner_replay(
        _inputs(), (), _config(), replay_config, _CallOrderDependentIdentityProvider()
    )
    assert len(result.detection_mismatches) > 0
    assert all(
        m.expected_summary != m.actual_summary for m in result.detection_mismatches
    )
