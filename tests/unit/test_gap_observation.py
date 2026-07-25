from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.contracts.types import SemVer
from btmm_ai_scanner.market_data.gap_observation import (
    GapClassification,
    observe_potential_gap,
)

_PROVENANCE_ID = UUID("0193f2c0-1234-7abc-8def-abcdefabcdff")
_FINGERPRINT = "a" * 64

_BASE_EVENT_TIME = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)


def _normalized_candle(
    record_id: UUID,
    *,
    event_time_utc: datetime,
    symbol: InternalSymbol = InternalSymbol.XAUUSD,
    timeframe: Timeframe = Timeframe.M1,
) -> NormalizedCandle:
    availability_time = event_time_utc + timedelta(minutes=1)
    return NormalizedCandle.model_validate(
        {
            "record_id": record_id,
            "content_fingerprint": _FINGERPRINT,
            "raw_candle_id": UUID("0193f2c0-1234-7abc-8def-abcdefabcdaa"),
            "provider": "FXCM",
            "source_reference": "fxcm-xauusd-m1",
            "source_symbol": "XAUUSD",
            "source_timeframe": "M1",
            "symbol": symbol,
            "timeframe": timeframe,
            "event_time_utc": event_time_utc,
            "availability_time_utc": availability_time,
            "processing_time_utc": availability_time + timedelta(seconds=1),
            "original_event_time": event_time_utc,
            "original_availability_time": availability_time,
            "original_timezone": "UTC",
            "open": Decimal("100.0"),
            "high": Decimal("101.0"),
            "low": Decimal("99.5"),
            "close": Decimal("100.5"),
            "volume": Decimal("10"),
            "volume_kind": CandleVolumeKind.TICK,
            "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
            "rule_version": SemVer.parse("0.1.0"),
            "contract_version": SemVer.parse("0.1.0"),
            "schema_version": SemVer.parse("0.1.0"),
            "provenance_id": _PROVENANCE_ID,
        }
    )


def test_observe_potential_gap_returns_none_for_correct_consecutive_interval() -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd01"), event_time_utc=_BASE_EVENT_TIME
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd02"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=1),
    )
    assert observe_potential_gap(previous, current) is None


def test_observe_potential_gap_detects_missing_intervals() -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd03"), event_time_utc=_BASE_EVENT_TIME
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd04"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=2),
    )
    observation = observe_potential_gap(previous, current)
    assert observation is not None
    assert observation.classification == GapClassification.POTENTIAL_GAP
    assert observation.missing_interval_count == 1

    current_triple = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd05"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=3),
    )
    triple_observation = observe_potential_gap(previous, current_triple)
    assert triple_observation is not None
    assert triple_observation.missing_interval_count == 2


def test_observe_potential_gap_rejects_different_symbols() -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd06"),
        event_time_utc=_BASE_EVENT_TIME,
        symbol=InternalSymbol.XAUUSD,
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd07"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=1),
        symbol=InternalSymbol.EURUSD,
    )
    with pytest.raises(ValueError, match="symbol"):
        observe_potential_gap(previous, current)


def test_observe_potential_gap_rejects_different_timeframes() -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd08"),
        event_time_utc=_BASE_EVENT_TIME,
        timeframe=Timeframe.M1,
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd09"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=1),
        timeframe=Timeframe.M5,
    )
    with pytest.raises(ValueError, match="timeframe"):
        observe_potential_gap(previous, current)


@pytest.mark.parametrize(
    "current_offset",
    [
        timedelta(minutes=-1),
        timedelta(minutes=0),
        timedelta(seconds=30),
        timedelta(seconds=150),
    ],
)
def test_gap_observation_rejects_out_of_order_same_time_and_irregular_alignment(
    current_offset: timedelta,
) -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd10"), event_time_utc=_BASE_EVENT_TIME
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd11"),
        event_time_utc=_BASE_EVENT_TIME + current_offset,
    )
    with pytest.raises(ValueError):
        observe_potential_gap(previous, current)


def test_observe_potential_gap_computes_expected_interval_per_timeframe() -> None:
    cases: list[tuple[Timeframe, timedelta]] = [
        (Timeframe.M1, timedelta(minutes=1)),
        (Timeframe.M5, timedelta(minutes=5)),
        (Timeframe.M15, timedelta(minutes=15)),
        (Timeframe.H1, timedelta(hours=1)),
        (Timeframe.H3, timedelta(hours=3)),
        (Timeframe.H4, timedelta(hours=4)),
        (Timeframe.D1, timedelta(days=1)),
        (Timeframe.W1, timedelta(days=7)),
    ]
    for index, (timeframe, expected_interval) in enumerate(cases):
        previous = _normalized_candle(
            UUID(f"0193f2c0-1234-7abc-8def-abcdefabce{index:02d}"),
            event_time_utc=_BASE_EVENT_TIME,
            timeframe=timeframe,
        )
        current = _normalized_candle(
            UUID(f"0193f2c0-1234-7abc-8def-abcdefabcf{index:02d}"),
            event_time_utc=_BASE_EVENT_TIME + expected_interval,
            timeframe=timeframe,
        )
        assert observe_potential_gap(previous, current) is None

        gapped_current = _normalized_candle(
            UUID(f"0193f2c0-1234-7abc-8def-abcdefabd0{index:02d}"),
            event_time_utc=_BASE_EVENT_TIME + (expected_interval * 2),
            timeframe=timeframe,
        )
        observation = observe_potential_gap(previous, gapped_current)
        assert observation is not None
        assert observation.expected_interval == expected_interval
        assert observation.missing_interval_count == 1


def test_observe_potential_gap_never_fabricates_or_interpolates() -> None:
    previous = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd12"), event_time_utc=_BASE_EVENT_TIME
    )
    current = _normalized_candle(
        UUID("0193f2c0-1234-7abc-8def-abcdefabcd13"),
        event_time_utc=_BASE_EVENT_TIME + timedelta(minutes=2),
    )
    observation = observe_potential_gap(previous, current)
    assert observation is not None
    assert observation.previous_normalized_candle_id == previous.record_id
    assert observation.current_normalized_candle_id == current.record_id
    # The observation records a gap relationship only; it carries no OHLC,
    # volume, or synthetic candle fields of its own.
    assert not hasattr(observation, "open")
    assert not hasattr(observation, "close")
