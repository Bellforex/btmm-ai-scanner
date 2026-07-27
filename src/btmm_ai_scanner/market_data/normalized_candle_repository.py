from datetime import datetime
from uuid import UUID

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import to_utc
from btmm_ai_scanner.market_data.raw_candle_repository import (
    InvalidTimeRangeError,
    RecordIdentityConflictError,
)


def _normalize_range_bound(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    try:
        return to_utc(value)
    except ValueError as exc:
        raise InvalidTimeRangeError(str(exc)) from exc


class InMemoryNormalizedCandleRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, NormalizedCandle] = {}

    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None:
        existing = self._records.get(normalized_candle.record_id)
        if existing is not None:
            if existing.content_fingerprint == normalized_candle.content_fingerprint:
                return
            raise RecordIdentityConflictError(
                f"record_id {normalized_candle.record_id} is already stored with"
                " different content."
            )
        self._records[normalized_candle.record_id] = normalized_candle

    def find_by_symbol_timeframe_range(
        self,
        symbol: InternalSymbol,
        timeframe: Timeframe,
        start_time_utc: datetime | None,
        end_time_utc: datetime | None,
    ) -> tuple[NormalizedCandle, ...]:
        start = _normalize_range_bound(start_time_utc)
        end = _normalize_range_bound(end_time_utc)
        if start is not None and end is not None and start > end:
            raise InvalidTimeRangeError(
                "start_time_utc must not be later than end_time_utc."
            )

        matches = [
            candle
            for candle in self._records.values()
            if candle.symbol == symbol
            and candle.timeframe == timeframe
            and (start is None or candle.event_time_utc >= start)
            and (end is None or candle.event_time_utc < end)
        ]
        matches.sort(key=lambda candle: (candle.event_time_utc, candle.record_id))
        return tuple(matches)

    def all_normalized_candles(self) -> tuple[NormalizedCandle, ...]:
        matches = sorted(
            self._records.values(),
            key=lambda candle: (candle.event_time_utc, candle.record_id),
        )
        return tuple(matches)
