from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmInteractionClass
from btmm_ai_scanner.btmm.interaction import find_first_interaction
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.poi.enums import PoiDirection

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
_ZONE_TOP = Decimal("101")
_ZONE_BOTTOM = Decimal("100")


def _record_id(index: int) -> UUID:
    return UUID(f"0193f450-1234-7abc-8def-{index:012x}")


def _candle(
    index: int, open_: str, high: str, low: str, close: str
) -> NormalizedCandle:
    event_time = _BASE_TIME + timedelta(minutes=5 * index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m5",
            "source_symbol": InternalSymbol.XAUUSD.value,
            "source_timeframe": Timeframe.M5.value,
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M5,
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
            "volume": None,
            "volume_kind": CandleVolumeKind.UNKNOWN,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROV_ID,
        }
    )


def test_bullish_entry_far_boundary_mapping() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")
    touch = _candle(1, "103", "103.1", "100.9", "101")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.EDGE_TOUCH


def test_bearish_entry_far_boundary_mapping() -> None:
    prior = _candle(0, "98", "98.2", "97.8", "98")
    touch = _candle(1, "98", "100.1", "97.9", "98")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BEARISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.EDGE_TOUCH


def test_edge_touch_partial_entry_deep_entry_ratio_boundaries() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")

    edge = _candle(1, "103", "103.1", "100.75", "101")
    edge_result = find_first_interaction(
        (prior, edge),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert edge_result is not None
    assert edge_result.interaction_class == BtmmInteractionClass.EDGE_TOUCH

    partial = _candle(1, "103", "103.1", "100.6", "101")
    partial_result = find_first_interaction(
        (prior, partial),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert partial_result is not None
    assert partial_result.interaction_class == BtmmInteractionClass.PARTIAL_ENTRY

    deep = _candle(1, "103", "103.1", "100.3", "101")
    deep_result = find_first_interaction(
        (prior, deep),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert deep_result is not None
    assert deep_result.interaction_class == BtmmInteractionClass.DEEP_ENTRY


def test_far_boundary_touch_exact_ratio_one() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")
    touch = _candle(1, "103", "103.1", "100.0", "100.5")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.FAR_BOUNDARY_TOUCH


def test_controlled_overshoot_within_tolerance() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")
    touch = _candle(1, "103", "103.1", "99.97", "100.5")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.CONTROLLED_OVERSHOOT


def test_excessive_overshoot_beyond_tolerance() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")
    touch = _candle(1, "103", "103.1", "95.0", "100.5")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.EXCESSIVE_OVERSHOOT


def test_near_miss_and_no_contact_distinguished_by_contact_tolerance() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")

    near_miss = _candle(1, "103", "103.2", "101.01", "103")
    near_miss_result = find_first_interaction(
        (prior, near_miss),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert near_miss_result is None

    no_contact = _candle(1, "103", "103.2", "102.9", "103")
    no_contact_result = find_first_interaction(
        (prior, no_contact),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert no_contact_result is None


def test_noncanonical_side_interaction_recorded() -> None:
    prior = _candle(0, "99", "99.2", "98.8", "99")
    touch = _candle(1, "99", "100.5", "98.9", "99")
    result = find_first_interaction(
        (prior, touch),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert (
        result.interaction_class == BtmmInteractionClass.NONCANONICAL_SIDE_INTERACTION
    )


def test_wick_and_close_penetration_tracked_independently() -> None:
    prior = _candle(0, "103", "103.2", "102.8", "103")
    deep_wick_shallow_close = _candle(1, "103", "103.1", "100.3", "102.9")
    result = find_first_interaction(
        (prior, deep_wick_shallow_close),
        1,
        (None, None),
        _ZONE_TOP,
        _ZONE_BOTTOM,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert result.interaction_class == BtmmInteractionClass.DEEP_ENTRY
    assert deep_wick_shallow_close.close > _ZONE_TOP
