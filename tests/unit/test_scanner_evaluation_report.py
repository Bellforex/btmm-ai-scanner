from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiLifecycleStatus, PoiType
from btmm_ai_scanner.scanner.configuration import (
    ReplayConfiguration,
    ScannerConfiguration,
)
from btmm_ai_scanner.scanner.enums import SnapshotRetentionPolicy
from btmm_ai_scanner.scanner.evaluation import evaluate_scanner
from btmm_ai_scanner.scanner.labels import ExpectedPoiLabel, ReviewedScannerCase
from btmm_ai_scanner.scanner.replay import ScannerReplayResult, run_scanner_replay
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

_FORBIDDEN_TRADE_FIELD_NAMES = frozenset(
    {
        "entry_price",
        "stop_loss",
        "take_profit",
        "risk_reward",
        "position_size",
        "trade_outcome",
        "signal_confidence",
        "ai_score",
        "profit_factor",
        "win_rate",
    }
)


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


def _replay_result() -> ScannerReplayResult:
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
    replay_config = ReplayConfiguration(
        snapshot_retention=SnapshotRetentionPolicy.ALL,
        verify_against_direct_batch=False,
    )
    return run_scanner_replay(
        inputs, (), _config(), replay_config, _SequentialIdentityProvider()
    )


def _case(poi_labels_complete: bool) -> ReviewedScannerCase:
    label = ExpectedPoiLabel(
        label_id="poi-1",
        expected_poi_type=PoiType.BULLISH_ENGULFING,
        expected_direction=PoiDirection.BULLISH,
        expected_timeframe=Timeframe.M1,
        expected_zone_top=Decimal("100"),
        expected_zone_bottom=Decimal("99"),
        earliest_valid_availability_time_utc=_BASE_TIME,
        latest_acceptable_availability_time_utc=_BASE_TIME + timedelta(hours=1),
        expected_final_lifecycle_status=PoiLifecycleStatus.NO_BREACH,
    )
    return ReviewedScannerCase(
        case_id="case-1",
        dataset_version="v1",
        reviewer_id="reviewer-1",
        review_version="1",
        symbol=InternalSymbol.XAUUSD,
        evaluation_start_time_utc=_BASE_TIME,
        evaluation_end_time_utc=_BASE_TIME + timedelta(days=1),
        required_timeframes=(Timeframe.M1, Timeframe.M5, Timeframe.M15),
        expected_poi_labels=(label,),
        expected_btmm_labels=(),
        poi_labels_complete=poi_labels_complete,
        btmm_labels_complete=poi_labels_complete,
        notes="",
    )


def test_backtest_report_includes_poi_validation_report() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    assert report.poi_validation_report.matched_count == 1


def test_backtest_report_includes_btmm_validation_report() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    assert report.btmm_validation_report.expected_count == 0


def test_backtest_report_includes_lifecycle_validation_report() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    assert report.lifecycle_validation_report is not None


def test_backtest_report_includes_health_report() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    assert report.health_report.candles_processed == 4


def test_precision_computed_when_case_labels_complete() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    poi = report.poi_validation_report
    precision = poi.matched_count / (poi.matched_count + poi.unexpected_count)
    assert 0.0 <= precision <= 1.0
    assert poi.matched_count == 1
    assert poi.unreviewed_count == 0


def test_precision_omitted_when_case_labels_incomplete() -> None:
    report = evaluate_scanner(_replay_result(), (_case(False),))
    poi = report.poi_validation_report
    assert poi.unexpected_count == 0
    assert poi.unreviewed_count >= 0


def test_recall_computed_when_case_labels_complete() -> None:
    report = evaluate_scanner(_replay_result(), (_case(True),))
    poi = report.poi_validation_report
    recall = poi.matched_count / (poi.matched_count + poi.missed_count)
    assert recall == 1.0


def test_recall_omitted_when_case_labels_incomplete() -> None:
    empty_report = evaluate_scanner(_replay_result(), ())
    assert empty_report.poi_validation_report.expected_count == 0
    assert empty_report.poi_validation_report.missed_count == 0


def test_backtest_report_rows_use_deterministic_ordering() -> None:
    report_a = evaluate_scanner(_replay_result(), (_case(True),))
    report_b = evaluate_scanner(_replay_result(), (_case(True),))
    assert [m.expected_label_id for m in report_a.poi_validation_report.matches] == [
        m.expected_label_id for m in report_b.poi_validation_report.matches
    ]


def test_backtest_report_contains_no_profitability_metric() -> None:
    from btmm_ai_scanner.scanner.evaluation import ScannerBacktestReport
    from btmm_ai_scanner.scanner.poi_validation import PoiValidationReport

    assert _FORBIDDEN_TRADE_FIELD_NAMES.isdisjoint(ScannerBacktestReport.model_fields)
    assert _FORBIDDEN_TRADE_FIELD_NAMES.isdisjoint(PoiValidationReport.model_fields)
