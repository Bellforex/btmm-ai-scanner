from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from btmm_ai_scanner.contracts.raw_candle import RawCandle, to_utc

_SourceIdentity = tuple[str, str, str, str, datetime]


class RecordIdentityConflictError(ValueError):
    pass


class InvalidTimeRangeError(ValueError):
    pass


def _source_identity(raw_candle: RawCandle) -> _SourceIdentity:
    return (
        raw_candle.provider,
        raw_candle.source_reference,
        raw_candle.source_symbol,
        raw_candle.source_timeframe,
        raw_candle.event_time_utc,
    )


def _normalize_range_bound(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    try:
        return to_utc(value)
    except ValueError as exc:
        raise InvalidTimeRangeError(str(exc)) from exc


class InMemoryRawCandleRepository:
    def __init__(self) -> None:
        self._records: dict[UUID, RawCandle] = {}

    def store_raw_candle(self, raw_candle: RawCandle) -> None:
        existing = self._records.get(raw_candle.record_id)
        if existing is not None:
            if existing.content_fingerprint == raw_candle.content_fingerprint:
                return
            raise RecordIdentityConflictError(
                f"record_id {raw_candle.record_id} is already stored with"
                " different content."
            )
        self._records[raw_candle.record_id] = raw_candle

    def find_raw_candles_by_source_identity(
        self,
        provider: str,
        source_reference: str,
        source_symbol: str,
        source_timeframe: str,
        event_time_utc: datetime,
    ) -> Sequence[RawCandle]:
        target = (
            provider,
            source_reference,
            source_symbol,
            source_timeframe,
            event_time_utc,
        )
        matches = [
            candle
            for candle in self._records.values()
            if _source_identity(candle) == target
        ]
        matches.sort(key=lambda candle: (candle.event_time_utc, candle.record_id))
        return tuple(matches)

    def find_raw_candles_by_source_identity_and_event_time_range(
        self,
        provider: str,
        source_reference: str,
        source_symbol: str,
        source_timeframe: str,
        start_time_utc: datetime | None,
        end_time_utc: datetime | None,
    ) -> tuple[RawCandle, ...]:
        start = _normalize_range_bound(start_time_utc)
        end = _normalize_range_bound(end_time_utc)
        if start is not None and end is not None and start > end:
            raise InvalidTimeRangeError(
                "start_time_utc must not be later than end_time_utc."
            )

        matches = [
            candle
            for candle in self._records.values()
            if candle.provider == provider
            and candle.source_reference == source_reference
            and candle.source_symbol == source_symbol
            and candle.source_timeframe == source_timeframe
            and (start is None or candle.event_time_utc >= start)
            and (end is None or candle.event_time_utc < end)
        ]
        matches.sort(key=lambda candle: (candle.event_time_utc, candle.record_id))
        return tuple(matches)

    def all_raw_candles(self) -> tuple[RawCandle, ...]:
        matches = sorted(
            self._records.values(),
            key=lambda candle: (candle.event_time_utc, candle.record_id),
        )
        return tuple(matches)
