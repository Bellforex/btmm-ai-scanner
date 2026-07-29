from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.reversal_candles import detect_reversal_candles

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


def _baseline(count: int = 3) -> list[NormalizedCandle]:
    return [_candle(i, "100", "101", "100", "100.5") for i in range(count)]


def test_buy_to_sell_candidate_requires_size_ratio_body_efficiency_and_close_position() -> (
    None
):
    baseline = _baseline()
    weak_candidate = _candle(3, "100.5", "101.2", "100.4", "101.1")
    strong_candidate = _candle(3, "100", "104", "100", "104")
    confirmation = _candle(4, "104", "104", "101", "101")

    assert (
        detect_reversal_candles((*baseline, weak_candidate, confirmation), _CONFIG)
        == ()
    )
    candidates = detect_reversal_candles(
        (*baseline, strong_candidate, confirmation), _CONFIG
    )
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.BUY_TO_SELL_CANDLE
    assert candidates[0].direction == PoiDirection.BEARISH


def test_buy_to_sell_zone_uses_candidate_candle_full_range() -> None:
    baseline = _baseline()
    candidate = _candle(3, "100", "104", "100", "104")
    confirmation = _candle(4, "104", "104", "101", "101")

    (result,) = detect_reversal_candles((*baseline, candidate, confirmation), _CONFIG)

    assert result.zone_top == Decimal("104")
    assert result.zone_bottom == Decimal("100")


def test_buy_to_sell_confirms_within_three_bar_reversal_window() -> None:
    baseline = _baseline()
    candidate = _candle(3, "100", "104", "100", "104")
    no_confirmation_within_window = (
        _candle(4, "104", "104.5", "103", "104"),
        _candle(5, "104", "104.5", "103", "104"),
        _candle(6, "104", "104.5", "103", "104"),
    )
    late_confirmation_outside_window = _candle(7, "104", "104", "101", "101")

    assert (
        detect_reversal_candles(
            (
                *baseline,
                candidate,
                *no_confirmation_within_window,
                late_confirmation_outside_window,
            ),
            _CONFIG,
        )
        == ()
    )

    bar3_confirmation = (
        _candle(4, "104", "104.5", "103", "104"),
        _candle(5, "104", "104.5", "103", "104"),
        _candle(6, "104", "104", "101", "101"),
    )
    candidates = detect_reversal_candles(
        (*baseline, candidate, *bar3_confirmation), _CONFIG
    )
    assert len(candidates) == 1


def test_buy_to_sell_availability_equals_reversal_confirmation_time() -> None:
    baseline = _baseline()
    candidate = _candle(3, "100", "104", "100", "104")
    confirmation = _candle(4, "104", "104", "101", "101")

    (result,) = detect_reversal_candles((*baseline, candidate, confirmation), _CONFIG)

    assert result.availability_time_utc == confirmation.availability_time_utc
    assert result.confirmation_time_utc == confirmation.availability_time_utc


def test_sell_to_buy_candidate_requires_size_ratio_body_efficiency_and_close_position() -> (
    None
):
    baseline = _baseline()
    weak_candidate = _candle(3, "100.5", "100.6", "100.2", "100.3")
    strong_candidate = _candle(3, "104", "104", "100", "100")
    confirmation = _candle(4, "100", "103", "100", "103")

    assert (
        detect_reversal_candles((*baseline, weak_candidate, confirmation), _CONFIG)
        == ()
    )
    candidates = detect_reversal_candles(
        (*baseline, strong_candidate, confirmation), _CONFIG
    )
    assert len(candidates) == 1
    assert candidates[0].poi_type == PoiType.SELL_TO_BUY_CANDLE
    assert candidates[0].direction == PoiDirection.BULLISH


def test_sell_to_buy_zone_uses_candidate_candle_full_range() -> None:
    baseline = _baseline()
    candidate = _candle(3, "104", "104", "100", "100")
    confirmation = _candle(4, "100", "103", "100", "103")

    (result,) = detect_reversal_candles((*baseline, candidate, confirmation), _CONFIG)

    assert result.zone_top == Decimal("104")
    assert result.zone_bottom == Decimal("100")


def test_sell_to_buy_confirms_within_three_bar_reversal_window() -> None:
    baseline = _baseline()
    candidate = _candle(3, "104", "104", "100", "100")
    no_confirmation_within_window = (
        _candle(4, "101", "102", "99.5", "100"),
        _candle(5, "101", "102", "99.5", "100"),
        _candle(6, "101", "102", "99.5", "100"),
    )

    assert (
        detect_reversal_candles(
            (*baseline, candidate, *no_confirmation_within_window), _CONFIG
        )
        == ()
    )

    bar3_confirmation = (
        _candle(4, "101", "102", "99.5", "100"),
        _candle(5, "101", "102", "99.5", "100"),
        _candle(6, "100", "103", "100", "103"),
    )
    candidates = detect_reversal_candles(
        (*baseline, candidate, *bar3_confirmation), _CONFIG
    )
    assert len(candidates) == 1


def test_sell_to_buy_availability_equals_reversal_confirmation_time() -> None:
    baseline = _baseline()
    candidate = _candle(3, "104", "104", "100", "100")
    confirmation = _candle(4, "100", "103", "100", "103")

    (result,) = detect_reversal_candles((*baseline, candidate, confirmation), _CONFIG)

    assert result.availability_time_utc == confirmation.availability_time_utc
    assert result.confirmation_time_utc == confirmation.availability_time_utc
