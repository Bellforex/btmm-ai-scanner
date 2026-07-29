from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest
from pydantic import ValidationError

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import (
    InvalidPoiConfigurationError,
    PoiConfiguration,
    validate_configuration,
)
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    open_: str,
    high: str,
    low: str,
    close: str,
    volume_kind: CandleVolumeKind = CandleVolumeKind.TICK,
    volume: str | None = "10",
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M1.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
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
            "volume": Decimal(volume) if volume is not None else None,
            "volume_kind": volume_kind,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def test_poi_configuration_default_values_match_approved_standards() -> None:
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

    assert config.order_block_size_ratio_standard == Decimal("2.0")
    assert config.order_block_size_ratio_strong == Decimal("3.0")
    assert config.small_candle_ratio_standard == Decimal("0.50")
    assert config.small_candle_ratio_strong == Decimal("0.3333")
    assert config.base_min_candles == 2
    assert config.base_max_candles == 6
    assert config.reclaim_window_bars == 3
    assert config.displacement_window_bars == 3
    assert config.doji_body_efficiency_standard == Decimal("0.10")
    assert len(config.enabled_poi_types) == 32
    assert config.supported_symbols == frozenset(
        {InternalSymbol.XAUUSD, InternalSymbol.EURUSD, InternalSymbol.GBPUSD}
    )


def test_poi_configuration_is_frozen_and_immutable() -> None:
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

    with pytest.raises(ValidationError):
        config.minimum_price_tick = Decimal("0.02")


def test_poi_configuration_rejects_non_positive_thresholds() -> None:
    config = PoiConfiguration(minimum_price_tick=Decimal("-1"))
    with pytest.raises(InvalidPoiConfigurationError):
        validate_configuration(config)

    zero_ratio_config = PoiConfiguration(
        minimum_price_tick=Decimal("0.01"),
        order_block_size_ratio_standard=Decimal("0"),
    )
    with pytest.raises(InvalidPoiConfigurationError):
        validate_configuration(zero_ratio_config)


def test_poi_configuration_evidence_classification_is_engineering_provisional() -> None:
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

    assert (
        config.evidence_classification == EvidenceClassification.ENGINEERING_PROVISIONAL
    )


def test_poi_configuration_has_no_strong_poi_timeframes_field() -> None:
    assert "strong_poi_timeframes" not in PoiConfiguration.model_fields


def test_volume_family_poi_types_use_option_b_price_action_proxies() -> None:
    origin = _candle(
        0,
        "100",
        "100.5",
        "99.5",
        "99.6",
        volume_kind=CandleVolumeKind.UNKNOWN,
        volume=None,
    )
    displacement = _candle(
        1,
        "99.6",
        "103",
        "99.5",
        "102.8",
        volume_kind=CandleVolumeKind.UNKNOWN,
        volume=None,
    )
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

    candidates = detect_order_blocks((origin, displacement), config)

    assert len(candidates) == 1


def test_proxy_metrics_are_computed_internally_and_never_exposed_publicly() -> None:
    forbidden_fields = {
        "relative_size_ratio",
        "range_context_ratio",
        "body_efficiency",
        "directional_close_position",
        "relative_tick_volume",
        "tick_volume_status",
    }

    assert forbidden_fields.isdisjoint(PoiObservation.model_fields)
