from datetime import datetime, timedelta

from btmm_ai_scanner.btmm.configuration import BtmmConfiguration
from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.types import ContractModel
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.enums import DataQualityClassification
from btmm_ai_scanner.poi.configuration import PoiConfiguration

# domain/swings.py's own internal pivot-confirmation radius (module-private,
# `_WINDOW_RADIUS`, currently 2); duplicated here as a plain int since it is not
# exposed as a configuration field. A pivot's own local confirmation requires
# 2 * this radius worth of surrounding context.
_SWING_CONFIRMATION_WINDOW_RADIUS = 2

_WEEKEND_CLOSURE_START_ISOWEEKDAY = 5  # Friday
_WEEKEND_CLOSURE_END_ISOWEEKDAY = 7  # Sunday


class ChecksumMismatchError(ValueError):
    pass


class DataQualityIssue(ContractModel):
    relative_path: str
    row_number: int | None
    symbol: InternalSymbol | None
    timeframe: Timeframe | None
    reason_code: str
    classification: DataQualityClassification


class GapRecord(ContractModel):
    symbol: InternalSymbol
    timeframe: Timeframe
    gap_start_event_time_utc: datetime
    gap_end_event_time_utc: datetime
    missing_bar_count: int
    likely_market_closure: bool


class TimeframeCoverage(ContractModel):
    symbol: InternalSymbol
    timeframe: Timeframe
    candle_count: int
    warm_up_floor_bars: int
    meets_warm_up_floor: bool
    complete_calendar_period_count: int | None


class HistoricalDataQualityReport(ContractModel):
    blank_rows_skipped: int
    unsorted_rows_resorted: int
    duplicate_rows_rejected: int
    issues: tuple[DataQualityIssue, ...]
    gaps: tuple[GapRecord, ...]
    checksum_verified: bool
    checksum_mismatched_files: tuple[str, ...]
    timeframe_coverage: tuple[TimeframeCoverage, ...]


def warm_up_floor_bars(
    measurement_configuration: MarketMeasurementConfiguration,
    btmm_configuration: BtmmConfiguration,
    poi_configuration: PoiConfiguration,
) -> int:
    return max(
        measurement_configuration.atr_period,
        measurement_configuration.range_context_window,
        measurement_configuration.trendline_min_anchor_spacing_bars,
        btmm_configuration.reaction_window_bars,
        poi_configuration.reclaim_window_bars,
        poi_configuration.displacement_window_bars,
        2 * _SWING_CONFIRMATION_WINDOW_RADIUS,
    )


def is_likely_market_closure(
    gap_start_event_time_utc: datetime, gap_end_event_time_utc: datetime
) -> bool:
    return (
        _WEEKEND_CLOSURE_START_ISOWEEKDAY
        <= gap_start_event_time_utc.isoweekday()
        <= _WEEKEND_CLOSURE_END_ISOWEEKDAY
    ) or (
        _WEEKEND_CLOSURE_START_ISOWEEKDAY
        <= gap_end_event_time_utc.isoweekday()
        <= _WEEKEND_CLOSURE_END_ISOWEEKDAY
    )


_FIXED_TIMEFRAME_DURATION: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H3: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=4),
}


def detect_gap(
    symbol: InternalSymbol,
    timeframe: Timeframe,
    previous_event_time_utc: datetime,
    current_event_time_utc: datetime,
) -> GapRecord | None:
    duration = _FIXED_TIMEFRAME_DURATION.get(timeframe)
    if duration is None:
        # D1/W1 calendar-timeframe gap counting is not a fixed elapsed duration;
        # gap detection for calendar timeframes is deferred (no gap is reported).
        return None

    elapsed = current_event_time_utc - previous_event_time_utc
    if elapsed <= duration:
        return None

    missing_bar_count = int(elapsed / duration) - 1
    if missing_bar_count <= 0:
        return None

    return GapRecord(
        symbol=symbol,
        timeframe=timeframe,
        gap_start_event_time_utc=previous_event_time_utc,
        gap_end_event_time_utc=current_event_time_utc,
        missing_bar_count=missing_bar_count,
        likely_market_closure=is_likely_market_closure(
            previous_event_time_utc, current_event_time_utc
        ),
    )
