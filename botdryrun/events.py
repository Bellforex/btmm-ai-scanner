"""P8 event consumer.

Dedups by the native P8 identity ``(event_type, poi_idx, bar_ms)`` against
the PERSISTED processed-event set, so a restart, a scanner rebuild, or a
replayed duplicate delivery never re-emits an event downstream. Order is
preserved exactly as the scanner emitted it.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from botdryrun.domain import EventView

__all__ = ["ConsumedBatch", "P8EventConsumer"]


@dataclass(frozen=True)
class ConsumedBatch:
    new_events: tuple[EventView, ...]
    duplicates: tuple[EventView, ...]


class P8EventConsumer:
    def __init__(self, processed_event_ids: Iterable[str] = ()) -> None:
        self._processed: set[str] = set(processed_event_ids)

    def is_processed(self, event_id: str) -> bool:
        return event_id in self._processed

    @property
    def processed_count(self) -> int:
        return len(self._processed)

    def consume(self, events: Sequence[EventView]) -> ConsumedBatch:
        fresh: list[EventView] = []
        duplicates: list[EventView] = []
        for event in events:
            if event.event_id in self._processed:
                duplicates.append(event)
                continue
            self._processed.add(event.event_id)
            fresh.append(event)
        return ConsumedBatch(tuple(fresh), tuple(duplicates))
