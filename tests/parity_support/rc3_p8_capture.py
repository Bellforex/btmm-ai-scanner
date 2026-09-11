"""Parse a real RC3 Pine P8 event capture and check the RC3 terminal contract.

Test-side tooling. The capture is a Pine Logs export from
`BTMM + POI + BTRC Scanner [RC3 PARITY DEV]`, whose semantic code is
byte-identical to the release DEV apart from its title.

What this proves and what it does not: the invariants below are properties of
the emitted stream, checked against the contract RC3 froze. They are real
evidence that the live Pine behaves as specified. They are NOT a Python-to-Pine
row comparison, because the captured Pine registry spans 1800 H4 bars while the
Python replay fixture spans 299, so the registry indices do not align.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "TERMINAL_REASONS",
    "P8CaptureEvent",
    "capture_invariants",
    "parse_p8_capture",
]

TERMINAL_REASONS = frozenset({"MITIGATED", "INVALIDATED"})

_EVENT = re.compile(r"P8EVENT\|([^\"\n]+)")


@dataclass(frozen=True)
class P8CaptureEvent:
    event_type: str
    bar_ms: int
    poi_idx: int
    terminal_reason: str | None


def _fields(blob: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in blob.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            out[key.strip()] = value.strip()
    return out


def parse_p8_capture(path: Path) -> list[P8CaptureEvent]:
    """Extract the P8 event stream from a Pine Logs CSV export.

    The export wraps each log line in CSV quoting and may wrap long lines, so
    the parse keys off the `P8EVENT|` marker rather than the CSV structure.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    events: list[P8CaptureEvent] = []
    for blob in _EVENT.findall(text):
        f = _fields(blob)
        if "type" not in f or "bar" not in f or "poiIdx" not in f:
            continue
        events.append(
            P8CaptureEvent(
                event_type=f["type"],
                bar_ms=int(f["bar"]),
                poi_idx=int(f["poiIdx"]),
                terminal_reason=f.get("terminalReason"),
            )
        )
    return events


def capture_invariants(events: list[P8CaptureEvent]) -> dict[str, object]:
    """Everything the RC3 P8 contract asserts, computed from a real capture."""
    by_type = Counter(e.event_type for e in events)
    terminals = [e for e in events if e.event_type == "POI_TERMINAL"]
    activated = {e.poi_idx for e in events if e.event_type == "POI_ACTIVATED"}

    terminal_counts = Counter(e.poi_idx for e in terminals)
    duplicates = {poi: n for poi, n in terminal_counts.items() if n > 1}

    missing_reason = [e for e in terminals if e.terminal_reason not in TERMINAL_REASONS]

    # A POI must be activated before it can go terminal. The capture is a
    # window into a longer run, so a terminal whose activation predates the
    # window is expected; what must never happen is an activation AFTER the
    # terminal for the same POI.
    first_activation = {}
    for e in events:
        if e.event_type == "POI_ACTIVATED":
            first_activation.setdefault(e.poi_idx, e.bar_ms)
    out_of_order = [
        e.poi_idx
        for e in terminals
        if e.poi_idx in first_activation and first_activation[e.poi_idx] > e.bar_ms
    ]

    return {
        "events": len(events),
        "by_type": dict(by_type),
        "terminal_events": len(terminals),
        "distinct_terminal_pois": len(terminal_counts),
        "duplicate_terminal_pois": duplicates,
        "terminals_missing_a_reason": len(missing_reason),
        "reason_distribution": dict(Counter(e.terminal_reason for e in terminals)),
        "activated_pois": len(activated),
        "terminal_before_activation": out_of_order,
    }
