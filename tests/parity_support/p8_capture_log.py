"""Strict parser for the P8 alert-event capture: `P8EVENT` (a real,
post-priming transition) and `P8PRIME` (a priming-bar observation, never
an alertable event) log lines.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics.

WHY A SEPARATE PARSER FROM `p5_atomic_capture_log`
------------------------------------------------------
`P5EVAL`/`P5WIRE` describe the P5 confluence engine's own per-bar decision
state. `P8EVENT`/`P8PRIME` are a DIFFERENT, additive emitter
(`btmm_poi_btrc_scanner_p8_dev.pine`'s alert-event block) that reads those
already-computed P5 fields but logs a DIFFERENT thing: not "what is the
state this bar" but "did the state transition this bar" — the same
distinction `tests/parity_support/p8_alert_oracle.py`'s `AlertEngine`
draws between a snapshot and an event. A capture can (and normally will)
contain both P5EVAL/P5WIRE and P8EVENT/P8PRIME lines interleaved in one
log buffer; this module only looks for its own two tags and ignores
everything else, exactly like `p5x_capture_log`/`p5_atomic_capture_log`
already do for each other's tags.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_LOG_PREFIX = re.compile(r"^.*?(?=P8EVENT\||P8PRIME\|)")

_EVENT_TYPES = frozenset(
    {
        "POI_ACTIVATED",
        "BTMM_VALIDATED",
        "PERMISSION_ENTERED_ACTIONABLE",
        "PERMISSION_LOST_ACTIONABLE",
        "POI_TERMINAL",
    }
)


class P8CaptureError(ValueError):
    """A P8 alert-event capture is malformed or from the wrong feed."""


def _strip(line: str) -> str:
    return _LOG_PREFIX.sub("", line.strip(), count=1)


def _fields(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            if key in out:
                raise P8CaptureError(f"duplicate field {key!r} in {body!r}")
            out[key] = value
    return out


@dataclass(frozen=True)
class P8Event:
    """One real, post-priming alert-event -- exactly one row per
    `AlertEvent` the Python oracle would also have emitted for the same
    input."""

    event_type: str
    bar_ms: int
    poi_idx: int
    poi_bullish: bool
    tier: int
    btmm_valid: bool
    permission: int
    lifecycle: int

    @property
    def event_key(self) -> tuple[str, int, int]:
        """Mirrors `AlertEvent.event_key` in `p8_alert_oracle.py` exactly
        -- the canonical identity a Pine event and a Python-oracle event
        are compared on."""
        return (self.event_type, self.poi_idx, self.bar_ms)


@dataclass(frozen=True)
class P8Prime:
    """One priming-bar observation -- never an alertable event; kept only
    so a capture's priming bar can be located and its observations can
    seed a Python-side replay identically to how the Pine source primed."""

    bar_ms: int
    poi_idx: int
    btmm_valid: bool
    permission: int
    terminal: bool


def _parse_event_line(line: str) -> P8Event:
    body = line[len("P8EVENT|") :]
    raw = _fields(body)
    required = ("type", "bar", "poiIdx", "poiDir", "poiTier", "btmmValid", "permission", "lifecycle")
    missing = [f for f in required if f not in raw]
    if missing:
        raise P8CaptureError(f"P8EVENT line missing fields {missing}: {line[:120]!r}")
    if raw["type"] not in _EVENT_TYPES:
        raise P8CaptureError(f"P8EVENT line has unknown type {raw['type']!r}")
    if raw["poiDir"] not in ("BULL", "BEAR"):
        raise P8CaptureError(f"P8EVENT line has unknown poiDir {raw['poiDir']!r}")
    if raw["btmmValid"] not in ("true", "false"):
        raise P8CaptureError(f"P8EVENT line has non-boolean btmmValid {raw['btmmValid']!r}")
    return P8Event(
        event_type=raw["type"],
        bar_ms=int(raw["bar"]),
        poi_idx=int(raw["poiIdx"]),
        poi_bullish=raw["poiDir"] == "BULL",
        tier=int(raw["poiTier"]),
        btmm_valid=raw["btmmValid"] == "true",
        permission=int(raw["permission"]),
        lifecycle=int(raw["lifecycle"]),
    )


def _parse_prime_line(line: str) -> P8Prime:
    body = line[len("P8PRIME|") :]
    raw = _fields(body)
    required = ("bar", "poiIdx", "btmmValid", "permission", "terminal")
    missing = [f for f in required if f not in raw]
    if missing:
        raise P8CaptureError(f"P8PRIME line missing fields {missing}: {line[:120]!r}")
    for bool_field in ("btmmValid", "terminal"):
        if raw[bool_field] not in ("true", "false"):
            raise P8CaptureError(f"P8PRIME line has non-boolean {bool_field} {raw[bool_field]!r}")
    return P8Prime(
        bar_ms=int(raw["bar"]),
        poi_idx=int(raw["poiIdx"]),
        btmm_valid=raw["btmmValid"] == "true",
        permission=int(raw["permission"]),
        terminal=raw["terminal"] == "true",
    )


@dataclass(frozen=True)
class P8Capture:
    #: Every real event, in emission order (Pine's own per-bar,
    #: ascending-poi_idx, fixed-priority order -- never re-sorted here, so
    #: a real-vs-oracle ordering mismatch is visible rather than hidden).
    events: tuple[P8Event, ...]
    #: bar timestamp (ms) -> every P8PRIME observation logged for that bar
    #: (there should be exactly one priming bar per capture, but this
    #: keeps the raw structure rather than assuming it).
    prime_by_bar: dict[int, list[P8Prime]]


def parse_p8_capture(text: str) -> P8Capture:
    events: list[P8Event] = []
    prime_by_bar: dict[int, list[P8Prime]] = {}
    seen_event_lines: set[str] = set()

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P8EVENT|"):
            if line in seen_event_lines:
                # A byte-identical duplicate emission (the same reload/tick
                # re-render phenomenon already documented for P5X/P5EVAL)
                # is collapsed, not treated as a second real event.
                continue
            seen_event_lines.add(line)
            events.append(_parse_event_line(line))
        elif line.startswith("P8PRIME|"):
            prime = _parse_prime_line(line)
            prime_by_bar.setdefault(prime.bar_ms, []).append(prime)

    return P8Capture(events=tuple(events), prime_by_bar=prime_by_bar)


__all__ = [
    "P8Capture",
    "P8CaptureError",
    "P8Event",
    "P8Prime",
    "parse_p8_capture",
]
