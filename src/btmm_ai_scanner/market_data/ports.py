from collections.abc import Iterator, Sequence
from datetime import datetime
from typing import Protocol

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import RawCandle


class RawCandleSink(Protocol):
    def store_raw_candle(self, raw_candle: RawCandle) -> None: ...


class NormalizedCandleSink(Protocol):
    def store_normalized_candle(self, normalized_candle: NormalizedCandle) -> None: ...


class CandleReadRepository(Protocol):
    def find_raw_candles_by_source_identity(
        self,
        provider: str,
        source_reference: str,
        source_symbol: str,
        source_timeframe: str,
        event_time_utc: datetime,
    ) -> Sequence[RawCandle]: ...


class HistoricalReplaySource(Protocol):
    def replay(self) -> Iterator[NormalizedCandle]: ...
