from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiStrengthTier, PoiType
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks

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


def test_buy_order_block_candidate_requires_size_ratio_at_least_two() -> None:
    origin = _candle(0, "100", "100", "99", "99")
    weak_displacement = _candle(1, "99", "100.5", "99", "100.3")
    strong_displacement = _candle(1, "99", "101", "99", "101")

    assert detect_order_blocks((origin, weak_displacement), _CONFIG) == ()
    candidates = detect_order_blocks((origin, strong_displacement), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BUY_ORDER_BLOCK


def test_buy_order_block_zone_uses_full_range_of_smaller_candle() -> None:
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")

    (candidate,) = detect_order_blocks((origin, displacement), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99")
    assert candidate.direction == PoiDirection.BULLISH


def test_buy_order_block_availability_equals_displacement_candle_close() -> None:
    origin = _candle(0, "100", "100", "99", "99")
    displacement = _candle(1, "99", "101", "99", "101")

    (candidate,) = detect_order_blocks((origin, displacement), _CONFIG)

    assert candidate.availability_time_utc == displacement.availability_time_utc
    assert candidate.confirmation_time_utc == displacement.availability_time_utc


def test_buy_order_block_strong_classification_requires_size_ratio_at_least_three() -> (
    None
):
    origin = _candle(0, "100", "100", "99", "99")
    standard_displacement = _candle(1, "99", "101", "99", "101")
    strong_displacement = _candle(1, "99", "102", "99", "102")

    (standard_candidate,) = detect_order_blocks(
        (origin, standard_displacement), _CONFIG
    )
    (strong_candidate,) = detect_order_blocks((origin, strong_displacement), _CONFIG)

    assert standard_candidate.strength_tier == PoiStrengthTier.STANDARD
    assert strong_candidate.strength_tier == PoiStrengthTier.STRONG


def test_sell_order_block_candidate_requires_size_ratio_at_least_two() -> None:
    origin = _candle(0, "99", "100", "99", "100")
    weak_displacement = _candle(1, "100", "100", "98.5", "98.7")
    strong_displacement = _candle(1, "100", "100", "98", "98")

    assert detect_order_blocks((origin, weak_displacement), _CONFIG) == ()
    candidates = detect_order_blocks((origin, strong_displacement), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.SELL_ORDER_BLOCK


def test_sell_order_block_zone_uses_full_range_of_smaller_candle() -> None:
    origin = _candle(0, "99", "100", "99", "100")
    displacement = _candle(1, "100", "100", "98", "98")

    (candidate,) = detect_order_blocks((origin, displacement), _CONFIG)

    assert candidate.zone_top == Decimal("100")
    assert candidate.zone_bottom == Decimal("99")
    assert candidate.direction == PoiDirection.BEARISH


def test_sell_order_block_availability_equals_displacement_candle_close() -> None:
    origin = _candle(0, "99", "100", "99", "100")
    displacement = _candle(1, "100", "100", "98", "98")

    (candidate,) = detect_order_blocks((origin, displacement), _CONFIG)

    assert candidate.availability_time_utc == displacement.availability_time_utc
    assert candidate.confirmation_time_utc == displacement.availability_time_utc


def test_sell_order_block_strong_classification_requires_size_ratio_at_least_three() -> (
    None
):
    origin = _candle(0, "99", "100", "99", "100")
    standard_displacement = _candle(1, "100", "100", "98", "98")
    strong_displacement = _candle(1, "100", "100", "97", "97")

    (standard_candidate,) = detect_order_blocks(
        (origin, standard_displacement), _CONFIG
    )
    (strong_candidate,) = detect_order_blocks((origin, strong_displacement), _CONFIG)

    assert standard_candidate.strength_tier == PoiStrengthTier.STANDARD
    assert strong_candidate.strength_tier == PoiStrengthTier.STRONG
