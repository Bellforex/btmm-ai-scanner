from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmDirection
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import DerivedOutputType
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.scanner.analysis import ScannerSetupSummary
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.configuration import ScannerConfiguration
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
    open_: str,
    high: str,
    low: str,
    close: str,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(seconds=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
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


def _flat_candle(index: int, timeframe: Timeframe = Timeframe.M1) -> NormalizedCandle:
    return _candle(index, "100", "100.5", "99.5", "100.2", timeframe=timeframe)


def _config() -> ScannerConfiguration:
    return ScannerConfiguration(
        measurement_configuration=MarketMeasurementConfiguration(
            minimum_price_tick=Decimal("0.01")
        ),
        structure_configuration=StructureConfiguration(),
        poi_configuration=PoiConfiguration(minimum_price_tick=Decimal("0.01")),
        btmm_configuration=BtmmConfiguration(minimum_price_tick=Decimal("0.01")),
    )


def _summary() -> ScannerSetupSummary:
    engulfed = _candle(0, "100", "100", "99", "99")
    engulfing = _candle(1, "99", "101", "99", "101")
    bundles = (
        ScannerTimeframeInput(timeframe=Timeframe.M1, candles=(engulfed, engulfing)),
        ScannerTimeframeInput(
            timeframe=Timeframe.M5, candles=(_flat_candle(0, Timeframe.M5),)
        ),
        ScannerTimeframeInput(
            timeframe=Timeframe.M15, candles=(_flat_candle(0, Timeframe.M15),)
        ),
    )
    result = scan_market(bundles, (), _config(), _SequentialIdentityProvider())
    return next(
        summary
        for summary in result.setup_summaries
        if summary.source_poi_type == PoiType.BULLISH_ENGULFING
    )


def test_setup_summary_links_source_poi_record_id() -> None:
    summary = _summary()
    assert isinstance(summary.source_poi_record_id, UUID)


def test_setup_summary_links_source_btmm_observation_record_id() -> None:
    summary = _summary()
    assert isinstance(summary.source_btmm_observation_record_id, UUID)
    assert summary.source_btmm_observation_record_id != summary.source_poi_record_id


def test_setup_summary_reports_direction_and_poi_type() -> None:
    summary = _summary()
    assert summary.btmm_direction == BtmmDirection.BULLISH_BTMM
    assert summary.source_poi_type == PoiType.BULLISH_ENGULFING


def test_setup_summary_reports_timeframe() -> None:
    summary = _summary()
    assert summary.timeframe == Timeframe.M1


def test_setup_summary_reports_poi_lifecycle_and_btmm_primary_state() -> None:
    summary = _summary()
    assert summary.poi_lifecycle_status is not None
    assert summary.btmm_primary_state is not None


def test_setup_summary_reports_interaction_and_reaction_classification() -> None:
    summary = _summary()
    assert summary.interaction_class is None or hasattr(
        summary.interaction_class, "value"
    )
    assert summary.reaction_classification is None or hasattr(
        summary.reaction_classification, "value"
    )


def test_setup_summary_reports_liquidity_context_and_volume_pillar_status() -> None:
    summary = _summary()
    assert summary.liquidity_evidence_status is not None
    assert summary.volume_pillar_status is not None
    assert summary.market_direction_status is not None
    assert summary.analytical_framework_status is not None


def test_setup_summary_has_no_entry_stop_target_or_risk_fields() -> None:
    assert _FORBIDDEN_TRADE_FIELD_NAMES.isdisjoint(ScannerSetupSummary.model_fields)
