from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
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


def _rally_base(count: int) -> list[NormalizedCandle]:
    return [_candle(i, "100", "100.2", "99.9", "100.1") for i in range(count)]


def _drop_base(count: int) -> list[NormalizedCandle]:
    return [_candle(i, "100", "100.1", "99.8", "99.9") for i in range(count)]


def test_base_rally_requires_two_to_six_compact_base_candles() -> None:
    single_base = _rally_base(1)
    departure = _candle(len(single_base), "100.1", "101", "100", "101")
    assert detect_bases((*single_base, departure), _CONFIG) == ()

    two_base = _rally_base(2)
    departure_two = _candle(len(two_base), "100.1", "101", "100", "101")
    candidates_two = detect_bases((*two_base, departure_two), _CONFIG)
    assert len(candidates_two) == 1
    assert candidates_two[0].poi_type == PoiType.BASE_RALLY

    six_base = _rally_base(6)
    departure_six = _candle(len(six_base), "100.1", "101", "100", "101")
    candidates_six = detect_bases((*six_base, departure_six), _CONFIG)
    assert any(c.poi_type == PoiType.BASE_RALLY for c in candidates_six)


def test_base_rally_zone_spans_base_low_to_base_high() -> None:
    base = _rally_base(2)
    departure = _candle(len(base), "100.1", "101", "100", "101")

    (candidate,) = detect_bases((*base, departure), _CONFIG)

    assert candidate.zone_top == Decimal("100.2")
    assert candidate.zone_bottom == Decimal("99.9")
    assert candidate.direction == PoiDirection.BULLISH


def test_base_rally_departure_candle_requires_size_ratio_at_least_two() -> None:
    base = _rally_base(2)
    weak_departure = _candle(len(base), "100.1", "100.4", "100", "100.35")
    strong_departure = _candle(len(base), "100.1", "101", "100", "101")

    assert detect_bases((*base, weak_departure), _CONFIG) == ()
    assert len(detect_bases((*base, strong_departure), _CONFIG)) == 1


def test_base_rally_availability_equals_departure_candle_close() -> None:
    base = _rally_base(2)
    departure = _candle(len(base), "100.1", "101", "100", "101")

    (candidate,) = detect_bases((*base, departure), _CONFIG)

    assert candidate.availability_time_utc == departure.availability_time_utc
    assert candidate.confirmation_time_utc == departure.availability_time_utc


def test_base_drop_requires_two_to_six_compact_base_candles() -> None:
    single_base = _drop_base(1)
    departure = _candle(len(single_base), "99.9", "100", "99", "99")
    assert detect_bases((*single_base, departure), _CONFIG) == ()

    two_base = _drop_base(2)
    departure_two = _candle(len(two_base), "99.9", "100", "99", "99")
    candidates_two = detect_bases((*two_base, departure_two), _CONFIG)
    assert len(candidates_two) == 1
    assert candidates_two[0].poi_type == PoiType.BASE_DROP

    six_base = _drop_base(6)
    departure_six = _candle(len(six_base), "99.9", "100", "99", "99")
    candidates_six = detect_bases((*six_base, departure_six), _CONFIG)
    assert any(c.poi_type == PoiType.BASE_DROP for c in candidates_six)


def test_base_drop_zone_spans_base_low_to_base_high() -> None:
    base = _drop_base(2)
    departure = _candle(len(base), "99.9", "100", "99", "99")

    (candidate,) = detect_bases((*base, departure), _CONFIG)

    assert candidate.zone_top == Decimal("100.1")
    assert candidate.zone_bottom == Decimal("99.8")
    assert candidate.direction == PoiDirection.BEARISH


def test_base_drop_departure_candle_requires_size_ratio_at_least_two() -> None:
    base = _drop_base(2)
    weak_departure = _candle(len(base), "99.9", "100", "99.65", "99.7")
    strong_departure = _candle(len(base), "99.9", "100", "99", "99")

    assert detect_bases((*base, weak_departure), _CONFIG) == ()
    assert len(detect_bases((*base, strong_departure), _CONFIG)) == 1


def test_base_drop_availability_equals_departure_candle_close() -> None:
    base = _drop_base(2)
    departure = _candle(len(base), "99.9", "100", "99", "99")

    (candidate,) = detect_bases((*base, departure), _CONFIG)

    assert candidate.availability_time_utc == departure.availability_time_utc
    assert candidate.confirmation_time_utc == departure.availability_time_utc
