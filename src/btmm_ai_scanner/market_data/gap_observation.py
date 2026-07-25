from datetime import datetime, timedelta
from enum import StrEnum

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.types import ContractModel, UUIDv7


class GapClassification(StrEnum):
    POTENTIAL_GAP = "POTENTIAL_GAP"


class GapObservation(ContractModel):
    previous_normalized_candle_id: UUIDv7
    current_normalized_candle_id: UUIDv7
    symbol: InternalSymbol
    timeframe: Timeframe
    previous_event_time_utc: datetime
    current_event_time_utc: datetime
    expected_interval: timedelta
    observed_interval: timedelta
    missing_interval_count: int
    classification: GapClassification


_EXPECTED_INTERVAL_BY_TIMEFRAME: dict[Timeframe, timedelta] = {
    Timeframe.M1: timedelta(minutes=1),
    Timeframe.M5: timedelta(minutes=5),
    Timeframe.M15: timedelta(minutes=15),
    Timeframe.H1: timedelta(hours=1),
    Timeframe.H3: timedelta(hours=3),
    Timeframe.H4: timedelta(hours=4),
    Timeframe.D1: timedelta(days=1),
    Timeframe.W1: timedelta(days=7),
}


def observe_potential_gap(
    previous: NormalizedCandle, current: NormalizedCandle
) -> GapObservation | None:
    if previous.symbol != current.symbol:
        raise ValueError("previous and current must share the same symbol.")
    if previous.timeframe != current.timeframe:
        raise ValueError("previous and current must share the same timeframe.")
    if current.event_time_utc <= previous.event_time_utc:
        raise ValueError(
            "current.event_time_utc must be strictly greater than"
            " previous.event_time_utc."
        )

    expected_interval = _EXPECTED_INTERVAL_BY_TIMEFRAME[previous.timeframe]
    observed_interval = current.event_time_utc - previous.event_time_utc

    if observed_interval == expected_interval:
        return None
    if observed_interval < expected_interval:
        raise ValueError(
            "observed_interval must not be shorter than expected_interval."
        )
    if observed_interval % expected_interval != timedelta(0):
        raise ValueError(
            "observed_interval is not an exact multiple of expected_interval"
            " (irregular interval alignment)."
        )

    missing_interval_count = observed_interval // expected_interval - 1

    return GapObservation(
        previous_normalized_candle_id=previous.record_id,
        current_normalized_candle_id=current.record_id,
        symbol=current.symbol,
        timeframe=current.timeframe,
        previous_event_time_utc=previous.event_time_utc,
        current_event_time_utc=current.event_time_utc,
        expected_interval=expected_interval,
        observed_interval=observed_interval,
        missing_interval_count=missing_interval_count,
        classification=GapClassification.POTENTIAL_GAP,
    )
