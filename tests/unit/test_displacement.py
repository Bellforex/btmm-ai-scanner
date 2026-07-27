from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.displacement import detect_displacement_observations
from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
)

_RAW_CANDLE_ID = UUID("0193f2f0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2f0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


def _record_id(index: int) -> UUID:
    return UUID(f"0193f2f0-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(
    prices: list[tuple[float, float, float, float]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(
        _candle(i, str(o), str(h), str(low), str(c))
        for i, (o, h, low, c) in enumerate(prices)
    )


def test_displacement_detection_classifies_normal_range_speed() -> None:
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    candles = _build([*baseline, (100.0, 101.2, 99.0, 100.5)])
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 1
    assert observations[0].classification == DisplacementClassification.NORMAL


def test_displacement_detection_classifies_fast_range_speed() -> None:
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    candles = _build([*baseline, (100.0, 102.8, 99.0, 102.5)])
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 1
    assert observations[0].range_speed_ratio >= _CONFIG.displacement_fast_ratio
    assert observations[0].range_speed_ratio < _CONFIG.displacement_very_fast_ratio
    assert observations[0].classification == DisplacementClassification.FAST


def test_displacement_detection_classifies_very_fast_range_speed() -> None:
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    candles = _build([*baseline, (100.0, 105.0, 99.0, 104.5)])
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 1
    assert observations[0].range_speed_ratio >= _CONFIG.displacement_very_fast_ratio
    assert observations[0].classification == DisplacementClassification.VERY_FAST


def test_displacement_detection_excludes_candidate_candle_from_its_own_baseline() -> (
    None
):
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    huge_candidate = (100.0, 150.0, 50.0, 149.0)
    candles = _build([*baseline, huge_candidate])
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 1
    # A baseline median of ~2.0 (huge candidate excluded) makes the ratio huge.
    assert observations[0].range_speed_ratio > Decimal("10")


def test_displacement_detection_classifies_zero_range_candle_as_normal_without_division_error() -> (
    None
):
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    candles = _build([*baseline, (100.0, 100.0, 100.0, 100.0)])
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 1
    assert observations[0].total_range == Decimal("0")
    assert observations[0].range_speed_ratio == Decimal("0")
    assert observations[0].classification == DisplacementClassification.NORMAL


def test_displacement_detection_assigns_bullish_or_bearish_direction() -> None:
    baseline = [(100.0, 101.0, 99.0, 100.0)] * 20
    candles = _build(
        [*baseline, (100.0, 102.0, 99.0, 101.5), (101.5, 103.0, 100.0, 100.2)]
    )
    observations = detect_displacement_observations(candles, _CONFIG)

    assert len(observations) == 2
    assert observations[0].direction == DisplacementDirection.BULLISH
    assert observations[1].direction == DisplacementDirection.BEARISH
