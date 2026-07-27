from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.provenance_record import EvidenceClassification
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType, TrendlineOrientation
from btmm_ai_scanner.domain.swings import ConfirmedSwing
from btmm_ai_scanner.domain.trendlines import detect_trendlines

_RAW_CANDLE_ID = UUID("0193f330-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f330-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)
_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))

_Prices = list[tuple[float, float, float, float]]


def _record_id(index: int) -> UUID:
    return UUID(f"0193f330-1234-7abc-8def-{index:012x}")


def _candle(
    index: int,
    o: float,
    h: float,
    low: float,
    c: float,
    event_time: datetime | None = None,
) -> NormalizedCandle:
    if event_time is None:
        event_time = _BASE_TIME + timedelta(minutes=index)
    availability = event_time + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": _record_id(index),
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": _RAW_CANDLE_ID,
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": InternalSymbol.XAUUSD,
            "timeframe": Timeframe.M1,
            "event_time_utc": event_time,
            "availability_time_utc": availability,
            "processing_time_utc": availability,
            "original_event_time": event_time,
            "original_availability_time": availability,
            "original_timezone": "UTC",
            "open": Decimal(str(o)),
            "high": Decimal(str(h)),
            "low": Decimal(str(low)),
            "close": Decimal(str(c)),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _linear_path(
    warm_up_count: int,
    start_price: float,
    slope: float,
    rise_count: int,
    tail_count: int,
) -> _Prices:
    prices: _Prices = []
    for _ in range(warm_up_count):
        prices.append((start_price, start_price + 0.2, start_price - 0.2, start_price))
    prev_close = start_price
    for i in range(rise_count):
        target = start_price + slope * i
        o = prev_close
        c = target
        h = max(o, c) + 0.2
        low = min(o, c) - 0.2
        prices.append((o, h, low, c))
        prev_close = c
    last_price = prev_close
    for _ in range(tail_count):
        prices.append((last_price, last_price + 0.2, last_price - 0.2, last_price))
    return prices


def _build(prices: _Prices) -> tuple[NormalizedCandle, ...]:
    return tuple(_candle(i, *p) for i, p in enumerate(prices))


def _swing(
    swing_index: int,
    swing_type: SwingType,
    price: float,
    pivot_candle_index: int,
    candles: tuple[NormalizedCandle, ...],
    tie_tolerance: str = "0.02",
) -> ConfirmedSwing:
    pivot_time = candles[pivot_candle_index].event_time_utc
    confirmation_time = pivot_time + timedelta(minutes=6)
    return ConfirmedSwing(
        record_id=_record_id(1000 + swing_index),
        content_fingerprint="a" * 64,
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M1,
        swing_type=swing_type,
        pivot_price=Decimal(str(price)),
        pivot_bar_index=pivot_candle_index,
        pivot_candle_record_ids=(candles[pivot_candle_index].record_id,),
        pivot_start_time_utc=pivot_time,
        pivot_end_time_utc=pivot_time,
        local_confirmation_time_utc=pivot_time + timedelta(minutes=2),
        meaningful_confirmation_time_utc=confirmation_time,
        confirmation_candle_id=candles[pivot_candle_index].record_id,
        pivot_reference_atr=Decimal("2.0"),
        pivot_tie_tolerance=Decimal(tie_tolerance),
        reversal_threshold=Decimal("0.5"),
        reversal_excursion=Decimal("1"),
        availability_time_utc=confirmation_time,
        rule_version=SemVer.parse("1.0.0"),
        contract_version=SemVer.parse("0.1.0"),
        schema_version=SemVer.parse("0.1.0"),
        evidence_classification=EvidenceClassification.ENGINEERING_PROVISIONAL,
        provenance_id=_PROVENANCE_ID,
    )


def _base_fixture() -> tuple[
    tuple[NormalizedCandle, ...], ConfirmedSwing, ConfirmedSwing, ConfirmedSwing
]:
    prices = _linear_path(20, 100.0, 0.05, 21, 4)
    candles = _build(prices)
    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 100.5, 30, candles)
    touch = _swing(3, SwingType.SWING_LOW, 101.0, 40, candles)
    return candles, anchor1, anchor2, touch


def test_trendline_requires_two_confirmed_meaningful_swing_anchors() -> None:
    candles, anchor1, _anchor2, _touch = _base_fixture()
    trendlines = detect_trendlines(candles, (anchor1,), _CONFIG)
    assert trendlines == ()


def test_trendline_rejects_anchors_within_pivot_tie_tolerance_as_horizontal_candidate() -> (
    None
):
    prices = _linear_path(20, 100.0, 0.05, 21, 4)
    candles = _build(prices)
    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 100.01, 30, candles)
    touch = _swing(3, SwingType.SWING_LOW, 101.0, 40, candles)

    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)
    assert trendlines == ()


def test_trendline_rejects_anchors_closer_than_minimum_bar_spacing() -> None:
    prices = _linear_path(20, 100.0, 0.05, 21, 4)
    candles = _build(prices)
    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 100.15, 23, candles)

    trendlines = detect_trendlines(candles, (anchor1, anchor2), _CONFIG)
    assert trendlines == ()


def test_trendline_classifies_valid_slope() -> None:
    candles, anchor1, anchor2, touch = _base_fixture()
    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)

    assert len(trendlines) == 1
    trendline = trendlines[0]
    assert trendline.orientation == TrendlineOrientation.BULLISH_TRENDLINE
    assert (
        _CONFIG.trendline_horizontal_atr_multiplier
        <= trendline.normalized_slope
        <= _CONFIG.trendline_too_steep_atr_multiplier
    )


def test_trendline_rejects_too_steep_slope() -> None:
    prices = _linear_path(20, 100.0, 0.4, 21, 4)
    candles = _build(prices)
    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 104.0, 30, candles)
    touch = _swing(3, SwingType.SWING_LOW, 108.0, 40, candles)

    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)
    assert trendlines == ()


def test_trendline_rejects_anchor_pair_on_pierce_tolerance_violation() -> None:
    prices = _linear_path(20, 100.0, 0.05, 21, 4)
    o, h, _low, _c = prices[25]
    prices[25] = (o, h, 90.0, 90.0)
    candles = _build(prices)
    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 100.5, 30, candles)
    touch = _swing(3, SwingType.SWING_LOW, 101.0, 40, candles)

    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)
    assert trendlines == ()


def test_trendline_confirms_after_third_qualifying_touch() -> None:
    candles, anchor1, anchor2, touch = _base_fixture()
    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)

    assert len(trendlines) == 1
    trendline = trendlines[0]
    assert trendline.anchor_1_swing_record_id == anchor1.record_id
    assert trendline.anchor_2_swing_record_id == anchor2.record_id
    assert trendline.qualifying_touch_swing_record_ids == (touch.record_id,)


def test_trendline_preserves_multiple_competing_candidates_without_ranking() -> None:
    prices = _linear_path(20, 100.0, 0.05, 41, 4)
    candles = _build(prices)
    swings = (
        _swing(1, SwingType.SWING_LOW, 100.0, 20, candles),
        _swing(2, SwingType.SWING_LOW, 100.5, 30, candles),
        _swing(3, SwingType.SWING_LOW, 101.0, 40, candles),
        _swing(4, SwingType.SWING_LOW, 101.5, 50, candles),
        _swing(5, SwingType.SWING_LOW, 102.0, 60, candles),
    )

    trendlines = detect_trendlines(candles, swings, _CONFIG)

    assert len(trendlines) == 6
    pairs = {(t.anchor_1_bar_index, t.anchor_2_bar_index) for t in trendlines}
    assert len(pairs) == len(trendlines)


def test_trendline_slope_is_price_per_candle_index_not_price_per_time() -> None:
    prices = _linear_path(20, 100.0, 0.05, 21, 4)
    times: list[datetime] = []
    current = _BASE_TIME
    for i in range(len(prices)):
        if i == 26:
            current = current + timedelta(days=30)
        elif i > 0:
            current = current + timedelta(minutes=1)
        times.append(current)
    candles = tuple(_candle(i, *p, event_time=times[i]) for i, p in enumerate(prices))

    anchor1 = _swing(1, SwingType.SWING_LOW, 100.0, 20, candles)
    anchor2 = _swing(2, SwingType.SWING_LOW, 100.5, 30, candles)
    touch = _swing(3, SwingType.SWING_LOW, 101.0, 40, candles)

    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)

    assert len(trendlines) == 1
    assert trendlines[0].raw_slope == Decimal("0.05")


def test_trendline_never_emits_draft_or_break_candidate_status() -> None:
    candles, anchor1, anchor2, touch = _base_fixture()
    trendlines = detect_trendlines(candles, (anchor1, anchor2, touch), _CONFIG)

    assert len(trendlines) == 1
    assert not hasattr(trendlines[0], "status")
    assert {member.value for member in TrendlineOrientation} == {
        "BULLISH_TRENDLINE",
        "BEARISH_TRENDLINE",
    }
