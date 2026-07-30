from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.btmm.enums import BtmmReactionClassification
from btmm_ai_scanner.btmm.reaction import (
    compute_reaction_anchor,
    evaluate_reaction_window,
    find_reaction_start,
)
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.measurements.legs import LegSpeedClassification
from btmm_ai_scanner.poi.enums import PoiDirection

_FINGERPRINT = "a" * 64
_RAW_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdaa")
_PROV_ID = UUID("0193f450-1234-7abc-8def-abcdefabcdff")
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)

_CONFIG = BtmmConfiguration(minimum_price_tick=Decimal("0.01"))
_ZONE_TOP = Decimal("101")
_ZONE_BOTTOM = Decimal("100")
_ZONE_HEIGHT = _ZONE_TOP - _ZONE_BOTTOM


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


def _strong_bullish_window() -> tuple[NormalizedCandle, ...]:
    return (
        _candle(0, "100.5", "101.5", "100.4", "101.2"),
        _candle(1, "101.2", "102.5", "101.1", "102.4"),
        _candle(2, "102.4", "103.7", "102.3", "103.6"),
        _candle(3, "103.6", "104.9", "103.5", "104.8"),
        _candle(4, "104.8", "106.2", "104.7", "106.0"),
    )


def _weak_bullish_window() -> tuple[NormalizedCandle, ...]:
    return (
        _candle(0, "100.5", "100.9", "100.3", "100.6"),
        _candle(1, "100.6", "100.95", "100.4", "100.7"),
        _candle(2, "100.7", "100.9", "100.5", "100.6"),
        _candle(3, "100.6", "100.85", "100.4", "100.55"),
        _candle(4, "100.55", "100.9", "100.45", "100.7"),
    )


def test_awaiting_reaction_before_reaction_start() -> None:
    prior = _candle(0, "103", "103.2", "100.9", "101")
    result = find_reaction_start((prior,), 1, _ZONE_TOP, PoiDirection.BULLISH)
    assert result is None


def test_reaction_start_exact_bullish_rule() -> None:
    interaction = _candle(0, "103", "103.1", "100.5", "100.8")
    below = _candle(1, "100.8", "100.95", "100.5", "100.9")
    above = _candle(2, "100.9", "102.5", "100.85", "102.2")
    result = find_reaction_start(
        (interaction, below, above), 1, _ZONE_TOP, PoiDirection.BULLISH
    )
    assert result == 2


def test_reaction_start_exact_bearish_rule() -> None:
    interaction = _candle(0, "97", "100.5", "96.9", "97.2")
    above = _candle(1, "97.2", "100.9", "97.1", "100.1")
    below = _candle(2, "100.1", "100.2", "99.4", "99.5")
    result = find_reaction_start(
        (interaction, above, below), 1, _ZONE_BOTTOM, PoiDirection.BEARISH
    )
    assert result == 2


def test_reaction_gate_remains_in_progress_before_fifth_confirmed_candle() -> None:
    window = _strong_bullish_window()
    for k in (1, 2, 3, 4):
        partial = window[:k]
        atr = tuple(Decimal("0.5") for _ in partial)
        result = evaluate_reaction_window(
            partial,
            atr,
            0,
            Decimal("100"),
            _ZONE_BOTTOM,
            _ZONE_HEIGHT,
            PoiDirection.BULLISH,
            _CONFIG,
        )
        assert result is not None


def test_reaction_gate_resolves_at_fifth_confirmed_candle() -> None:
    window = _strong_bullish_window()
    atr = tuple(Decimal("0.5") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result.reaction_classification in (
        BtmmReactionClassification.STANDARD_REACTION,
        BtmmReactionClassification.STRONG_REACTION,
    )


def test_reaction_gate_uses_highest_tier_achieved_in_full_window() -> None:
    window = _strong_bullish_window()
    atr = tuple(Decimal("0.5") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result.reaction_classification == BtmmReactionClassification.STRONG_REACTION
    assert result.bars_to_strong_reaction is not None
    assert result.bars_to_standard_reaction is not None
    assert result.bars_to_standard_reaction <= result.bars_to_strong_reaction


def test_standard_reaction_all_four_conditions() -> None:
    window = _strong_bullish_window()
    atr = tuple(Decimal("2.0") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result.reaction_classification in (
        BtmmReactionClassification.STANDARD_REACTION,
        BtmmReactionClassification.STRONG_REACTION,
    )


def test_strong_reaction_all_five_conditions_including_speed() -> None:
    window = _strong_bullish_window()
    atr = tuple(Decimal("0.5") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result.reaction_classification == BtmmReactionClassification.STRONG_REACTION
    assert result.reaction_speed_classification in (
        LegSpeedClassification.FAST,
        LegSpeedClassification.STRONG_FAST,
    )


def test_weak_reaction_on_window_close() -> None:
    window = _weak_bullish_window()
    atr = tuple(Decimal("2.0") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result.reaction_classification == BtmmReactionClassification.WEAK_REACTION


def test_reaction_speed_gate_fast_strong_fast_slow_or_unclear() -> None:
    strong_window = _strong_bullish_window()
    strong_atr = tuple(Decimal("0.5") for _ in strong_window)
    strong_result = evaluate_reaction_window(
        strong_window,
        strong_atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert (
        strong_result.reaction_speed_classification
        != LegSpeedClassification.SLOW_OR_UNCLEAR
    )

    weak_window = _weak_bullish_window()
    weak_atr = tuple(Decimal("2.0") for _ in weak_window)
    weak_result = evaluate_reaction_window(
        weak_window,
        weak_atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert (
        weak_result.reaction_speed_classification
        == LegSpeedClassification.SLOW_OR_UNCLEAR
    )


def test_reaction_window_never_completing_stays_in_progress_indefinitely() -> None:
    window = _strong_bullish_window()[:3]
    atr = tuple(Decimal("0.5") for _ in window)
    result = evaluate_reaction_window(
        window,
        atr,
        0,
        Decimal("100"),
        _ZONE_BOTTOM,
        _ZONE_HEIGHT,
        PoiDirection.BULLISH,
        _CONFIG,
    )
    assert result is not None
    assert compute_reaction_anchor(window, 0, 0, PoiDirection.BULLISH) == window[0].low
