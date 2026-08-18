"""Append-only accepted-candle journal (A7A).

The journal is the AUTHORITATIVE forward input history: replaying its accepted
candles through a fresh ``IncrementalReplayKernel`` deterministically rebuilds
scanner state (identity is content-addressed, so no serialized Python object
graph is the recovery truth). Writes are crash-safe (flush + fsync); a
partially-written trailing line is tolerated on load (ignored), never corrupting
recovery.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle


class AcceptedCandleJournal:
    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._sequence = 0

    @property
    def sequence(self) -> int:
        return self._sequence

    def append(self, candle: NormalizedCandle) -> int:
        """Append one accepted candle; returns its 1-based sequence number.
        Crash-safe: the record is flushed and fsync'd before returning."""
        self._sequence += 1
        record = {
            "sequence": self._sequence,
            "candle": candle.model_dump(mode="json"),
        }
        line = json.dumps(record, separators=(",", ":"))
        with open(self._path, "a", encoding="utf-8") as handle:
            handle.write(line + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return self._sequence

    def load(self) -> tuple[NormalizedCandle, ...]:
        """Load accepted candles in journal order. A trailing partially-written
        line (no newline terminator, or invalid JSON at EOF) is ignored so a
        crash mid-append never breaks recovery. Sequence numbers must be a
        contiguous 1..N run over the intact records."""
        if not self._path.exists():
            return ()
        raw = self._path.read_bytes()
        if not raw:
            return ()
        text = raw.decode("utf-8", errors="strict")
        lines = text.split("\n")
        # A final element that is "" means the last real line was newline-
        # terminated (intact). A non-empty final element is an unterminated
        # (partial) trailing write and is dropped.
        if lines and lines[-1] == "":
            lines = lines[:-1]
        elif lines:
            lines = lines[:-1]  # drop the unterminated trailing partial line
        candles: list[NormalizedCandle] = []
        expected_sequence = 0
        for line in lines:
            if not line:
                continue
            record = json.loads(line)
            expected_sequence += 1
            if int(record["sequence"]) != expected_sequence:
                raise ValueError(
                    "accepted-candle journal sequence is not contiguous at "
                    f"{record['sequence']!r} (expected {expected_sequence})."
                )
            # Round-trip through JSON so the strict contract model coerces the
            # dumped strings back to Decimal / datetime / enum types.
            candles.append(
                NormalizedCandle.model_validate_json(json.dumps(record["candle"]))
            )
        self._sequence = expected_sequence
        return tuple(candles)
