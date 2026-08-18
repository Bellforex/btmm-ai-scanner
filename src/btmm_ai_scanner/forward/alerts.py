"""Forward alert sinks (A7A). Provider-neutral scanner-event outputs only — no
trade execution transport exists in this package."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Protocol

from btmm_ai_scanner.forward.events import ScannerAlert


class AlertSink(Protocol):
    def emit(self, alert: ScannerAlert) -> None: ...


class CollectingAlertSink:
    """In-memory sink (development/tests)."""

    def __init__(self) -> None:
        self.alerts: list[ScannerAlert] = []

    def emit(self, alert: ScannerAlert) -> None:
        self.alerts.append(alert)


class JsonlAlertSink:
    """Append-only JSONL file sink, crash-safe (flush + fsync per line)."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def emit(self, alert: ScannerAlert) -> None:
        line = json.dumps(alert.model_dump(mode="json"), separators=(",", ":"))
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
