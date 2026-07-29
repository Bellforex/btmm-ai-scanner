from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars

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


def test_morning_star_requires_doji_body_efficiency_threshold() -> None:
    c1 = _candle(0, "102", "102", "100", "100")
    non_doji_c2 = _candle(1, "100", "100.8", "99.5", "100.6")
    doji_c2 = _candle(1, "100", "100.5", "99.5", "100.05")
    c3 = _candle(2, "100", "102", "100", "102")

    assert detect_three_candle_stars((c1, non_doji_c2, c3), _CONFIG) == ()
    candidates = detect_three_candle_stars((c1, doji_c2, c3), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.MORNING_STAR
    assert candidates[0].direction == PoiDirection.BULLISH


def test_morning_star_zone_uses_middle_doji_candle_full_range() -> None:
    c1 = _candle(0, "102", "102", "100", "100")
    c2 = _candle(1, "100", "100.5", "99.5", "100.05")
    c3 = _candle(2, "100", "102", "100", "102")

    (candidate,) = detect_three_candle_stars((c1, c2, c3), _CONFIG)

    assert candidate.zone_top == Decimal("100.5")
    assert candidate.zone_bottom == Decimal("99.5")


def test_evening_star_requires_doji_body_efficiency_threshold() -> None:
    c1 = _candle(0, "100", "102", "100", "102")
    non_doji_c2 = _candle(1, "100.5", "100.8", "99.2", "99.4")
    doji_c2 = _candle(1, "100", "100.5", "99.5", "99.95")
    c3 = _candle(2, "100", "100", "98", "98")

    assert detect_three_candle_stars((c1, non_doji_c2, c3), _CONFIG) == ()
    candidates = detect_three_candle_stars((c1, doji_c2, c3), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.EVENING_STAR
    assert candidates[0].direction == PoiDirection.BEARISH


def test_evening_star_zone_uses_middle_doji_candle_full_range() -> None:
    c1 = _candle(0, "100", "102", "100", "102")
    c2 = _candle(1, "100", "100.5", "99.5", "99.95")
    c3 = _candle(2, "100", "100", "98", "98")

    (candidate,) = detect_three_candle_stars((c1, c2, c3), _CONFIG)

    assert candidate.zone_top == Decimal("100.5")
    assert candidate.zone_bottom == Decimal("99.5")


def test_morning_and_evening_star_availability_equals_third_candle_close() -> None:
    morning_c1 = _candle(0, "102", "102", "100", "100")
    morning_c2 = _candle(1, "100", "100.5", "99.5", "100.05")
    morning_c3 = _candle(2, "100", "102", "100", "102")

    evening_c1 = _candle(3, "100", "102", "100", "102")
    evening_c2 = _candle(4, "100", "100.5", "99.5", "99.95")
    evening_c3 = _candle(5, "100", "100", "98", "98")

    (morning_result,) = detect_three_candle_stars(
        (morning_c1, morning_c2, morning_c3), _CONFIG
    )
    (evening_result,) = detect_three_candle_stars(
        (evening_c1, evening_c2, evening_c3), _CONFIG
    )

    assert morning_result.availability_time_utc == morning_c3.availability_time_utc
    assert morning_result.confirmation_time_utc == morning_c3.availability_time_utc
    assert evening_result.availability_time_utc == evening_c3.availability_time_utc
    assert evening_result.confirmation_time_utc == evening_c3.availability_time_utc
