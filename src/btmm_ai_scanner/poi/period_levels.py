from collections.abc import Callable, Sequence
from datetime import datetime, timedelta
from decimal import Decimal
from typing import NamedTuple
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType


class PeriodLevelCandidate(NamedTuple):
    symbol: InternalSymbol
    timeframe: Timeframe
    poi_type: PoiType
    direction: PoiDirection
    representative_price: Decimal
    source_candle_record_ids: tuple[UUID, ...]
    period_start_time_utc: datetime
    period_end_time_utc: datetime
    candidate_event_time_utc: datetime
    confirmation_time_utc: datetime
    availability_time_utc: datetime


class _Window(NamedTuple):
    start: datetime
    end: datetime
    candles: tuple[NormalizedCandle, ...]


def _day_window(event_time_utc: datetime) -> tuple[datetime, datetime]:
    start = event_time_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


def _iso_week_window(event_time_utc: datetime) -> tuple[datetime, datetime]:
    day_start = event_time_utc.replace(hour=0, minute=0, second=0, microsecond=0)
    start = day_start - timedelta(days=day_start.weekday())
    return start, start + timedelta(days=7)


def _month_window(event_time_utc: datetime) -> tuple[datetime, datetime]:
    start = event_time_utc.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def _group_by_window(
    candles: Sequence[NormalizedCandle],
    window_fn: Callable[[datetime], tuple[datetime, datetime]],
) -> list[_Window]:
    windows: list[_Window] = []
    current_start: datetime | None = None
    current_end: datetime | None = None
    current_candles: list[NormalizedCandle] = []

    for candle in candles:
        start, end = window_fn(candle.event_time_utc)
        if current_start is None or start != current_start:
            if current_start is not None and current_end is not None:
                windows.append(
                    _Window(current_start, current_end, tuple(current_candles))
                )
            current_start = start
            current_end = end
            current_candles = []
        current_candles.append(candle)

    if current_start is not None and current_end is not None:
        windows.append(_Window(current_start, current_end, tuple(current_candles)))

    return windows


def _extreme_candidates(
    window: _Window,
    high_type: PoiType,
    low_type: PoiType,
    availability_time_utc: datetime,
) -> tuple[PeriodLevelCandidate, PeriodLevelCandidate]:
    highest = window.candles[0]
    for candle in window.candles[1:]:
        if candle.high > highest.high:
            highest = candle
    lowest = window.candles[0]
    for candle in window.candles[1:]:
        if candle.low < lowest.low:
            lowest = candle

    symbol = window.candles[0].symbol
    timeframe = window.candles[0].timeframe

    high_candidate = PeriodLevelCandidate(
        symbol=symbol,
        timeframe=timeframe,
        poi_type=high_type,
        direction=PoiDirection.BEARISH,
        representative_price=highest.high,
        source_candle_record_ids=(highest.record_id,),
        period_start_time_utc=window.start,
        period_end_time_utc=window.end,
        candidate_event_time_utc=highest.event_time_utc,
        confirmation_time_utc=availability_time_utc,
        availability_time_utc=availability_time_utc,
    )
    low_candidate = PeriodLevelCandidate(
        symbol=symbol,
        timeframe=timeframe,
        poi_type=low_type,
        direction=PoiDirection.BULLISH,
        representative_price=lowest.low,
        source_candle_record_ids=(lowest.record_id,),
        period_start_time_utc=window.start,
        period_end_time_utc=window.end,
        candidate_event_time_utc=lowest.event_time_utc,
        confirmation_time_utc=availability_time_utc,
        availability_time_utc=availability_time_utc,
    )
    return high_candidate, low_candidate


_GRANULARITIES: tuple[
    tuple[
        Callable[[datetime], tuple[datetime, datetime]],
        PoiType,
        PoiType,
        PoiType,
        PoiType,
    ],
    ...,
] = (
    (
        _day_window,
        PoiType.CURRENT_DAY_HIGH,
        PoiType.CURRENT_DAY_LOW,
        PoiType.PREVIOUS_DAY_HIGH,
        PoiType.PREVIOUS_DAY_LOW,
    ),
    (
        _iso_week_window,
        PoiType.CURRENT_WEEK_HIGH,
        PoiType.CURRENT_WEEK_LOW,
        PoiType.PREVIOUS_WEEK_HIGH,
        PoiType.PREVIOUS_WEEK_LOW,
    ),
    (
        _month_window,
        PoiType.CURRENT_MONTH_HIGH,
        PoiType.CURRENT_MONTH_LOW,
        PoiType.PREVIOUS_MONTH_HIGH,
        PoiType.PREVIOUS_MONTH_LOW,
    ),
)


def detect_period_levels(
    candles: tuple[NormalizedCandle, ...],
    configuration: PoiConfiguration,
) -> tuple[PeriodLevelCandidate, ...]:
    del configuration
    if len(candles) == 0:
        return ()

    results: list[PeriodLevelCandidate] = []
    for (
        window_fn,
        current_high_type,
        current_low_type,
        previous_high_type,
        previous_low_type,
    ) in _GRANULARITIES:
        windows = _group_by_window(candles, window_fn)
        if len(windows) == 0:
            continue

        current_window = windows[-1]
        current_high, current_low = _extreme_candidates(
            current_window,
            current_high_type,
            current_low_type,
            current_window.candles[-1].availability_time_utc,
        )
        results.append(current_high)
        results.append(current_low)

        if len(windows) >= 2:
            previous_window = windows[-2]
            rollover_availability = current_window.candles[0].availability_time_utc
            previous_high, previous_low = _extreme_candidates(
                previous_window,
                previous_high_type,
                previous_low_type,
                rollover_availability,
            )
            results.append(previous_high)
            results.append(previous_low)

    return tuple(results)
