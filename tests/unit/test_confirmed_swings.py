from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from btmm_ai_scanner.measurements.atr import compute_atr_series

_RAW_CANDLE_ID = UUID("0193f2e0-1234-7abc-8def-abcdefabcdaa")
_PROVENANCE_ID = UUID("0193f2e0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64
_BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _record_id(index: int) -> UUID:
    return UUID(f"0193f2e0-1234-7abc-8def-{index:012x}")


def _candle(index: int, o: str, h: str, low: str, c: str) -> NormalizedCandle:
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
            "open": Decimal(o),
            "high": Decimal(h),
            "low": Decimal(low),
            "close": Decimal(c),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def _build(
    prices: list[tuple[float, float, float, float]],
) -> tuple[NormalizedCandle, ...]:
    return tuple(
        _candle(i, str(o), str(h), str(low), str(c))
        for i, (o, h, low, c) in enumerate(prices)
    )


_WARM_UP = [
    (100 + 0.1 * i, 100.5 + 0.1 * i, 99.6 + 0.1 * i, 100.2 + 0.1 * i) for i in range(16)
]
_ZIGZAG = [
    (100, 101, 99, 100),
    (100, 102, 99.5, 101.5),
    (101.5, 105, 101, 104),
    (104, 104.5, 100, 100.5),
    (100.5, 101, 96, 96.5),
    (96.5, 97, 93, 93.5),
    (93.5, 96, 93, 95.5),
    (95.5, 99, 95, 98.5),
    (98.5, 103, 98, 102.5),
    (102.5, 104, 101, 103.5),
    (103.5, 104, 100, 100.5),
    (100.5, 101, 97, 97.5),
    (97.5, 98, 94, 94.5),
    (94.5, 95, 91, 91.5),
    (91.5, 95, 91, 94.5),
    (94.5, 98, 94, 97.5),
    (97.5, 101, 97, 100.5),
]

_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))


def test_confirmed_swing_detection_confirms_swing_high_after_meaningful_reversal() -> (
    None
):
    candles = _build(_WARM_UP + _ZIGZAG)
    swings = detect_confirmed_swings(candles, _CONFIG)

    highs = [s for s in swings if s.swing_type == SwingType.SWING_HIGH]
    assert len(highs) >= 1
    first_high = highs[0]
    assert first_high.reversal_excursion >= first_high.reversal_threshold


def test_confirmed_swing_detection_confirms_swing_low_after_meaningful_reversal() -> (
    None
):
    candles = _build(_WARM_UP + _ZIGZAG)
    swings = detect_confirmed_swings(candles, _CONFIG)

    lows = [s for s in swings if s.swing_type == SwingType.SWING_LOW]
    assert len(lows) >= 1
    first_low = lows[0]
    assert first_low.reversal_excursion >= first_low.reversal_threshold


def test_confirmed_swing_detection_handles_adjacent_pivot_plateau_as_one_swing() -> (
    None
):
    flat_warm_up = [(100, 101, 99, 100)] * 16
    plateau = [
        (100, 101, 99, 100.5),
        (100.5, 101, 96, 96.5),
        (96.5, 97, 93, 93.5),
        (93.5, 94, 90.05, 93.6),  # first plateau candle
        (93.6, 94.05, 90.08, 93.65),  # second plateau candle, near-identical low
        (93.65, 97, 93, 96.5),
        (96.5, 100, 96, 99.5),
        (99.5, 103, 99, 102.5),
        (102.5, 106, 102, 105.5),
        (105.5, 106, 100, 100.5),
    ]
    candles = _build(flat_warm_up + plateau)
    swings = detect_confirmed_swings(candles, _CONFIG)

    lows = [s for s in swings if s.swing_type == SwingType.SWING_LOW]
    plateau_lows = [s for s in lows if len(s.pivot_candle_record_ids) > 1]
    assert len(plateau_lows) >= 1
    assert plateau_lows[0].pivot_price == Decimal("90.05")


def test_confirmed_swing_detection_supersedes_unconfirmed_candidate_with_more_extreme_price() -> (
    None
):
    flat_warm_up = [(100, 101, 99, 100)] * 16
    sequence = [
        (100, 101, 99, 100.5),
        (100.5, 102, 100, 101.5),
        (101.5, 104, 101, 103.5),  # first swing-high candidate at 104
        (103.5, 103.8, 102.5, 103),
        (103, 103.5, 102, 102.5),
        (
            102.5,
            106,
            102,
            105.5,
        ),  # second, more extreme candidate at 106, before A confirms
        (105.5, 106, 102, 102.5),
        (102.5, 103, 95, 96),
        (96, 97, 91, 92),
        (92, 93, 87, 88),
        (88, 89, 84, 85),
    ]
    candles = _build(flat_warm_up + sequence)
    swings = detect_confirmed_swings(candles, _CONFIG)

    highs = [s for s in swings if s.swing_type == SwingType.SWING_HIGH]
    assert len(highs) == 1
    assert highs[0].pivot_price == Decimal("106")


def test_confirmed_swing_detection_never_exposes_a_swing_before_meaningful_confirmation_time() -> (
    None
):
    candles = _build(_WARM_UP + _ZIGZAG)
    swings = detect_confirmed_swings(candles, _CONFIG)

    for swing in swings:
        assert swing.meaningful_confirmation_time_utc > swing.pivot_end_time_utc
        assert (
            swing.meaningful_confirmation_time_utc >= swing.local_confirmation_time_utc
        )


def test_confirmed_swing_detection_alternates_swing_high_and_swing_low() -> None:
    candles = _build(_WARM_UP + _ZIGZAG)
    swings = detect_confirmed_swings(candles, _CONFIG)

    for previous, current in pairwise(swings):
        assert previous.swing_type != current.swing_type


def test_confirmed_swing_detection_excludes_first_and_last_two_candles_from_pivot_eligibility() -> (
    None
):
    sequence = [
        (100.0, 200.0, 50.0, 150.0),  # extreme value placed at index 0 of this batch
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 300.0, 25.0, 150.0),  # extreme value placed at the very last index
    ]
    candles = _build(_WARM_UP + sequence)
    swings = detect_confirmed_swings(candles, _CONFIG)

    first_two_ids = {candles[0].record_id, candles[1].record_id}
    last_two_ids = {candles[-1].record_id, candles[-2].record_id}
    for swing in swings:
        for pivot_id in swing.pivot_candle_record_ids:
            assert pivot_id not in first_two_ids
            assert pivot_id not in last_two_ids


def test_confirmed_swing_detection_emits_neither_direction_for_simultaneous_high_and_low_qualification() -> (
    None
):
    sequence = [
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 110.0, 90.0, 100.0),  # simultaneously the highest high and lowest low
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
        (100.0, 101.0, 99.0, 100.0),
    ]
    candles = _build(_WARM_UP + sequence)
    swings = detect_confirmed_swings(candles, _CONFIG)

    ambiguous_index = len(_WARM_UP) + 2
    ambiguous_id = candles[ambiguous_index].record_id
    for swing in swings:
        assert ambiguous_id not in swing.pivot_candle_record_ids


def test_confirmed_swing_detection_derives_pivot_reference_atr_from_wilder_seed_and_recurrence() -> (
    None
):
    candles = _build(_WARM_UP + _ZIGZAG)
    atr_values = compute_atr_series(candles, _CONFIG.atr_period)

    assert all(value is None for value in atr_values[:13])
    assert atr_values[13] is not None

    true_ranges = []
    previous_close: Decimal | None = None
    for candle in candles[:14]:
        high_low = candle.high - candle.low
        if previous_close is None:
            true_ranges.append(high_low)
        else:
            true_ranges.append(
                max(
                    high_low,
                    abs(candle.high - previous_close),
                    abs(candle.low - previous_close),
                )
            )
        previous_close = candle.close
    expected_seed = sum(true_ranges, Decimal(0)) / Decimal(14)
    assert atr_values[13] == expected_seed

    swings = detect_confirmed_swings(candles, _CONFIG)
    assert len(swings) >= 1
    for swing in swings:
        assert swing.pivot_reference_atr > Decimal(0)


def test_confirmed_swing_detection_returns_empty_tuple_when_atr_is_not_yet_available() -> (
    None
):
    short_sequence = _build(_WARM_UP[:10])
    swings = detect_confirmed_swings(short_sequence, _CONFIG)
    assert swings == ()
