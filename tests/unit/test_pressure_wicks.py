from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks

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


def test_bullish_pressure_wick_requires_lower_wick_share_and_close_position() -> None:
    weak = _candle(0, "99.5", "100", "99.4", "99.9")
    strong_enough = _candle(0, "99.7", "100", "99", "99.95")

    assert detect_pressure_wicks((weak,), _CONFIG) == ()
    candidates = detect_pressure_wicks((strong_enough,), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BULLISH_PRESSURE_WICK
    assert candidates[0].direction == PoiDirection.BULLISH


def test_bullish_pressure_wick_zone_uses_lower_rejection_wick_only() -> None:
    candle = _candle(0, "99.7", "100", "99", "99.95")

    (candidate,) = detect_pressure_wicks((candle,), _CONFIG)

    assert candidate.zone_top == Decimal("99.7")
    assert candidate.zone_bottom == Decimal("99")


def test_bearish_pressure_wick_requires_upper_wick_share_and_close_position() -> None:
    weak = _candle(0, "99.6", "99.7", "99", "99.1")
    strong_enough = _candle(0, "99.3", "100", "99", "99.05")

    assert detect_pressure_wicks((weak,), _CONFIG) == ()
    candidates = detect_pressure_wicks((strong_enough,), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BEARISH_PRESSURE_WICK
    assert candidates[0].direction == PoiDirection.BEARISH


def test_bearish_pressure_wick_zone_uses_upper_rejection_wick_only() -> None:
    candle = _candle(0, "99.3", "100", "99", "99.05")

    (candidate,) = detect_pressure_wicks((candle,), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99.3")


def test_pressure_wick_strong_classification_requires_higher_thresholds_for_both_directions() -> (
    None
):
    preceding = _candle(0, "100", "100.2", "99.9", "100.05")

    standard_only_bullish = _candle(1, "99.7", "100", "99", "99.95")
    strong_bullish = _candle(1, "99.65", "100", "99", "99.97")

    (standard_result,) = detect_pressure_wicks(
        (preceding, standard_only_bullish), _CONFIG
    )
    strong_results = detect_pressure_wicks((preceding, strong_bullish), _CONFIG)

    assert standard_result.strength_tier == PoiStrengthTier.STANDARD
    assert strong_results[0].strength_tier == PoiStrengthTier.STRONG

    standard_only_bearish = _candle(1, "99.3", "100", "99", "99.05")
    strong_bearish = _candle(1, "99.35", "100", "99", "99.03")

    (standard_bearish_result,) = detect_pressure_wicks(
        (preceding, standard_only_bearish), _CONFIG
    )
    strong_bearish_results = detect_pressure_wicks((preceding, strong_bearish), _CONFIG)

    assert standard_bearish_result.strength_tier == PoiStrengthTier.STANDARD
    assert strong_bearish_results[0].strength_tier == PoiStrengthTier.STRONG


def test_pressure_wick_confirms_on_own_candle_close_for_both_directions() -> None:
    bullish = _candle(0, "99.7", "100", "99", "99.95")
    bearish = _candle(0, "99.3", "100", "99", "99.05")

    (bullish_result,) = detect_pressure_wicks((bullish,), _CONFIG)
    (bearish_result,) = detect_pressure_wicks((bearish,), _CONFIG)

    assert bullish_result.availability_time_utc == bullish.availability_time_utc
    assert bullish_result.confirmation_time_utc == bullish.availability_time_utc
    assert bearish_result.availability_time_utc == bearish.availability_time_utc
    assert bearish_result.confirmation_time_utc == bearish.availability_time_utc
