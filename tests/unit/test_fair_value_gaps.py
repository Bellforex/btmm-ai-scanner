from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps

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


def test_buy_fair_value_gap_requires_strict_three_candle_gap_geometry() -> None:
    c1 = _candle(0, "100", "101", "99.5", "100.5")
    c2 = _candle(1, "100.5", "103", "100", "102.5")
    gap_c3 = _candle(2, "104", "106", "103.5", "105")
    no_gap_c3 = _candle(2, "102", "103", "100.8", "102.5")

    assert detect_fair_value_gaps((c1, c2, no_gap_c3), _CONFIG) == ()
    candidates = detect_fair_value_gaps((c1, c2, gap_c3), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BUY_FAIR_VALUE_GAP


def test_buy_fair_value_gap_zone_spans_first_candle_high_to_third_candle_low() -> None:
    c1 = _candle(0, "100", "101", "99.5", "100.5")
    c2 = _candle(1, "100.5", "103", "100", "102.5")
    c3 = _candle(2, "104", "106", "103.5", "105")

    (candidate,) = detect_fair_value_gaps((c1, c2, c3), _CONFIG)

    assert candidate.zone_bottom == Decimal("101")
    assert candidate.zone_top == Decimal("103.5")
    assert candidate.direction == PoiDirection.BULLISH


def test_buy_fair_value_gap_availability_equals_third_candle_close() -> None:
    c1 = _candle(0, "100", "101", "99.5", "100.5")
    c2 = _candle(1, "100.5", "103", "100", "102.5")
    c3 = _candle(2, "104", "106", "103.5", "105")

    (candidate,) = detect_fair_value_gaps((c1, c2, c3), _CONFIG)

    assert candidate.availability_time_utc == c3.availability_time_utc
    assert candidate.confirmation_time_utc == c3.availability_time_utc


def test_buy_fair_value_gap_rejected_if_gap_closes_before_third_candle() -> None:
    c1 = _candle(0, "100", "101", "99.5", "100.5")
    c2 = _candle(1, "100.5", "103", "100", "102.5")
    filled_c3 = _candle(2, "103", "104", "100.9", "103.5")

    assert detect_fair_value_gaps((c1, c2, filled_c3), _CONFIG) == ()


def test_sell_fair_value_gap_requires_strict_three_candle_gap_geometry() -> None:
    c1 = _candle(0, "100", "100.5", "99", "99.5")
    c2 = _candle(1, "99.5", "100", "97", "97.5")
    gap_c3 = _candle(2, "96", "96.5", "94", "95")
    no_gap_c3 = _candle(2, "98", "99.2", "96", "97")

    assert detect_fair_value_gaps((c1, c2, no_gap_c3), _CONFIG) == ()
    candidates = detect_fair_value_gaps((c1, c2, gap_c3), _CONFIG)
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.SELL_FAIR_VALUE_GAP


def test_sell_fair_value_gap_zone_spans_third_candle_high_to_first_candle_low() -> None:
    c1 = _candle(0, "100", "100.5", "99", "99.5")
    c2 = _candle(1, "99.5", "100", "97", "97.5")
    c3 = _candle(2, "96", "96.5", "94", "95")

    (candidate,) = detect_fair_value_gaps((c1, c2, c3), _CONFIG)

    assert candidate.zone_top == Decimal("99")
    assert candidate.zone_bottom == Decimal("96.5")
    assert candidate.direction == PoiDirection.BEARISH


def test_sell_fair_value_gap_availability_equals_third_candle_close() -> None:
    c1 = _candle(0, "100", "100.5", "99", "99.5")
    c2 = _candle(1, "99.5", "100", "97", "97.5")
    c3 = _candle(2, "96", "96.5", "94", "95")

    (candidate,) = detect_fair_value_gaps((c1, c2, c3), _CONFIG)

    assert candidate.availability_time_utc == c3.availability_time_utc
    assert candidate.confirmation_time_utc == c3.availability_time_utc


def test_sell_fair_value_gap_rejected_if_gap_closes_before_third_candle() -> None:
    c1 = _candle(0, "100", "100.5", "99", "99.5")
    c2 = _candle(1, "99.5", "100", "97", "97.5")
    filled_c3 = _candle(2, "97", "99.1", "96", "97")

    assert detect_fair_value_gaps((c1, c2, filled_c3), _CONFIG) == ()
