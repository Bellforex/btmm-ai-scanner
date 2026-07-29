from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType

_RAW_CANDLE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int, open_: str, high: str, low: str, close: str
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
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def test_bullish_engulfing_requires_size_ratio_at_least_two() -> None:
    engulfed = _candle(0, "100", "100", "99", "99")
    weak_engulfing = _candle(1, "99", "100.4", "99", "100.3")
    strong_engulfing = _candle(1, "99", "101", "99", "101")

    assert detect_engulfing((engulfed, weak_engulfing), _CONFIG) == ()
    candidates = detect_engulfing((engulfed, strong_engulfing), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BULLISH_ENGULFING
    assert candidates[0].direction == PoiDirection.BULLISH


def test_bullish_engulfing_zone_uses_engulfed_candle_full_range() -> None:
    engulfed = _candle(0, "100", "100", "99", "99")
    engulfing = _candle(1, "99", "101", "99", "101")

    (candidate,) = detect_engulfing((engulfed, engulfing), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99")


def test_bearish_engulfing_requires_size_ratio_at_least_two() -> None:
    engulfed = _candle(0, "99", "100", "99", "100")
    weak_engulfing = _candle(1, "100", "100", "98.7", "98.8")
    strong_engulfing = _candle(1, "100", "100", "98", "98")

    assert detect_engulfing((engulfed, weak_engulfing), _CONFIG) == ()
    candidates = detect_engulfing((engulfed, strong_engulfing), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BEARISH_ENGULFING
    assert candidates[0].direction == PoiDirection.BEARISH


def test_bearish_engulfing_zone_uses_engulfed_candle_full_range() -> None:
    engulfed = _candle(0, "99", "100", "99", "100")
    engulfing = _candle(1, "100", "100", "98", "98")

    (candidate,) = detect_engulfing((engulfed, engulfing), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99")


def test_engulfing_availability_equals_engulfing_candle_close_for_both_directions() -> (
    None
):
    bullish_engulfed = _candle(0, "100", "100", "99", "99")
    bullish_engulfing = _candle(1, "99", "101", "99", "101")
    bearish_engulfed = _candle(2, "99", "100", "99", "100")
    bearish_engulfing = _candle(3, "100", "100", "98", "98")

    (bullish_result,) = detect_engulfing((bullish_engulfed, bullish_engulfing), _CONFIG)
    (bearish_result,) = detect_engulfing((bearish_engulfed, bearish_engulfing), _CONFIG)

    assert (
        bullish_result.availability_time_utc == bullish_engulfing.availability_time_utc
    )
    assert (
        bullish_result.confirmation_time_utc == bullish_engulfing.availability_time_utc
    )
    assert (
        bearish_result.availability_time_utc == bearish_engulfing.availability_time_utc
    )
    assert (
        bearish_result.confirmation_time_utc == bearish_engulfing.availability_time_utc
    )
