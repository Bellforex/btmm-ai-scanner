from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals

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


def test_hammer_requires_lower_wick_share_body_efficiency_and_opposite_wick_thresholds() -> (
    None
):
    weak = _candle(0, "99.7", "100", "99.5", "99.9")
    hammer = _candle(0, "99.85", "100", "99", "99.95")

    assert detect_single_candle_reversals((weak,), _CONFIG) == ()
    candidates = detect_single_candle_reversals((hammer,), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.HAMMER
    assert candidates[0].direction == PoiDirection.BULLISH


def test_hammer_zone_uses_rejection_wick_only() -> None:
    hammer = _candle(0, "99.85", "100", "99", "99.95")

    (candidate,) = detect_single_candle_reversals((hammer,), _CONFIG)

    assert candidate.zone_top == Decimal("99.85")
    assert candidate.zone_bottom == Decimal("99")


def test_shooting_star_requires_upper_wick_share_body_efficiency_and_opposite_wick_thresholds() -> (
    None
):
    weak = _candle(0, "99.6", "99.9", "99", "99.4")
    shooting_star = _candle(0, "99.15", "100", "99", "99.05")

    assert detect_single_candle_reversals((weak,), _CONFIG) == ()
    candidates = detect_single_candle_reversals((shooting_star,), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.SHOOTING_STAR
    assert candidates[0].direction == PoiDirection.BEARISH


def test_shooting_star_zone_uses_rejection_wick_only() -> None:
    shooting_star = _candle(0, "99.15", "100", "99", "99.05")

    (candidate,) = detect_single_candle_reversals((shooting_star,), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99.15")


def test_hammer_and_shooting_star_confirm_on_own_candle_close() -> None:
    hammer = _candle(0, "99.85", "100", "99", "99.95")
    shooting_star = _candle(1, "99.15", "100", "99", "99.05")

    (hammer_result,) = detect_single_candle_reversals((hammer,), _CONFIG)
    (star_result,) = detect_single_candle_reversals((shooting_star,), _CONFIG)

    assert hammer_result.availability_time_utc == hammer.availability_time_utc
    assert hammer_result.confirmation_time_utc == hammer.availability_time_utc
    assert star_result.availability_time_utc == shooting_star.availability_time_utc
    assert star_result.confirmation_time_utc == shooting_star.availability_time_utc
