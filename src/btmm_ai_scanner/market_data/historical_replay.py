from collections.abc import Iterable, Iterator
from datetime import datetime
from uuid import UUID

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle

_ReplaySortKey = tuple[datetime, datetime, str, str, str, str, UUID]


def _replay_sort_key(candle: NormalizedCandle) -> _ReplaySortKey:
    return (
        candle.availability_time_utc,
        candle.event_time_utc,
        candle.symbol.value,
        candle.timeframe.value,
        candle.provider,
        candle.source_reference,
        candle.record_id,
    )


class InMemoryHistoricalReplaySource:
    def __init__(self, candles: Iterable[NormalizedCandle]) -> None:
        self._snapshot: tuple[NormalizedCandle, ...] = tuple(
            sorted(candles, key=_replay_sort_key)
        )
        self._position: int = 0

    def replay(self) -> Iterator[NormalizedCandle]:
        return iter(self._snapshot)

    @property
    def position(self) -> int:
        return self._position

    @property
    def is_exhausted(self) -> bool:
        return self._position >= len(self._snapshot)

    def advance_next_availability_group(self) -> tuple[NormalizedCandle, ...]:
        if self.is_exhausted:
            return ()

        next_availability = self._snapshot[self._position].availability_time_utc
        group: list[NormalizedCandle] = []
        index = self._position
        while (
            index < len(self._snapshot)
            and self._snapshot[index].availability_time_utc == next_availability
        ):
            group.append(self._snapshot[index])
            index += 1
        self._position = index
        return tuple(group)

    def reset(self) -> None:
        self._position = 0
