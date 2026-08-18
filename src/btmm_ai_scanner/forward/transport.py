"""Forward market-data transport seam (A7A).

``ForwardCandleTransport`` is the single boundary a real provider (FXCM
ForexConnect: historical rate download + live price streaming) implements. It
yields provider-native CLOSED candle rows only; partial/forming bars must never
be emitted as closed. ``SyntheticTransport`` is the credential-free in-memory
implementation used for development and the permanent test-suite — the live
ForexConnect transport is intentionally absent (it needs an FXCM account).
"""

from __future__ import annotations

from collections import deque
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from typing import Protocol

from btmm_ai_scanner.contracts.types import ContractModel


class ProviderCandle(ContractModel):
    """A provider-native candle row. ``is_closed`` reflects the provider's own
    completion signal; only ``is_closed=True`` rows may reach scanner semantics.
    ``open_time_utc`` is the candle OPEN instant (availability/close is derived
    downstream as open + native timeframe duration)."""

    provider: str
    source_symbol: str
    source_timeframe: str
    open_time_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None
    is_closed: bool


class ForwardCandleTransport(Protocol):
    """Polls the provider for newly-CLOSED candles since the last poll. A live
    FXCM ForexConnect adapter implements this; it must return only closed bars
    and is responsible for reconnect/backfill (delivered rows still flow through
    the runner's idempotency/order/gap rules)."""

    def poll_closed_candles(self) -> Sequence[ProviderCandle]: ...


class SyntheticTransport:
    """Deterministic in-memory transport for development/tests. Rows are dequeued
    in FIFO order; ``poll_closed_candles`` returns the next ``batch_size`` rows.
    No network, no credentials, no order placement."""

    def __init__(
        self, rows: Sequence[ProviderCandle] = (), *, batch_size: int = 1
    ) -> None:
        self._queue: deque[ProviderCandle] = deque(rows)
        self._batch_size = batch_size

    def enqueue(self, *rows: ProviderCandle) -> None:
        self._queue.extend(rows)

    def poll_closed_candles(self) -> Sequence[ProviderCandle]:
        batch: list[ProviderCandle] = []
        while self._queue and len(batch) < self._batch_size:
            batch.append(self._queue.popleft())
        return tuple(batch)

    def empty(self) -> bool:
        return len(self._queue) == 0
