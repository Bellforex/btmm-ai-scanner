"""Strict parser for the P9 full-system capture: `P9TRACE` (one row per
POI per bar, for every POI in the P5 active-POI set that bar) and
`P8EVENT` (Pine's own real fired alert events, the same five V1 types
`p8_alert_oracle.py` already models) log lines.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics.

WHY A SEPARATE PARSER FROM `p8_capture_log`/`p8_real_state_log`
------------------------------------------------------------------------
The P9 DEV capture (`btmm_poi_btrc_scanner_p9_dev.pine`, real FX:XAUUSD M15
data) runs `p9DebugLog` and `p8DebugLog` simultaneously, so one capture
carries BOTH tags interleaved. `P8EVENT`'s own wire format here is
byte-identical to `p8_capture_log.P8Event`'s (same field names, same
`poiDir=BULL/BEAR` textual encoding) -- this module parses it itself
rather than importing that module, exactly as `p8_real_state_log.py`
parses its own `P5EVAL` tag independently of `p5_atomic_capture_log.py`.
`P9TRACE` is a NEW tag this module alone understands: unlike `P8EVENT`'s
`poiDir=BULL/BEAR`, `P9TRACE`'s `poiDir` field is the raw `-1`/`1` integer
`P9BarInput.direction` already expects (`DIRECTION_BULLISH=1`,
`DIRECTION_BEARISH=-1` in `p9_integrated_model.py`) -- no conversion
needed, confirmed against real capture lines before this module was
written.

NO `tier`/`align` FIELDS ON `P9TraceRow`
------------------------------------------------------------------------
The real `P9TRACE` emitter does not log `poiTier`/`poiAlign` (by design --
see `tests/unit/test_p9_real_pine_parity.py`'s module docstring for the
full verification that neither field ever gates eligibility/visibility in
`p7_ui_display_model.py`, `p7z_zone_model.py`, or `p8_alert_oracle.py`, and
that `P9Record` itself carries neither field). This parser therefore has
no `tier`/`align` fields to extract; callers construct `P9BarInput` with a
placeholder value for both.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_LOG_PREFIX = re.compile(r"^.*?(?=P9TRACE\||P8EVENT\|)")

_EVENT_TYPES = frozenset(
    {
        "POI_ACTIVATED",
        "BTMM_VALIDATED",
        "PERMISSION_ENTERED_ACTIONABLE",
        "PERMISSION_LOST_ACTIONABLE",
        "POI_TERMINAL",
    }
)


class P9CaptureError(ValueError):
    """A P9 full-system capture is malformed or from the wrong feed."""


def _strip(line: str) -> str:
    return _LOG_PREFIX.sub("", line.strip(), count=1)


def _fields(body: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for part in body.split("|"):
        if "=" in part:
            key, _, value = part.partition("=")
            if key in out:
                raise P9CaptureError(f"duplicate field {key!r} in {body!r}")
            out[key] = value
    return out


def _bool(raw: dict[str, str], field: str, line: str) -> bool:
    value = raw[field]
    if value not in ("true", "false"):
        raise P9CaptureError(f"{field} has non-boolean value {value!r}: {line[:160]!r}")
    return value == "true"


@dataclass(frozen=True)
class P9TraceRow:
    """One POI's full state for one bar, exactly as `P9TRACE` logs it --
    every field a real `P9BarInput` needs except `tier`/`align` (never
    logged; see module docstring) and `origin_tf` (the fixed host
    timeframe, not per-POI)."""

    bar_ms: int
    poi_idx: int
    poi_type: int
    direction: int  # raw -1/1, matches DIRECTION_BULLISH/DIRECTION_BEARISH directly
    zone_top: float
    zone_bottom: float
    avail_time_ms: int
    terminal: bool
    btmm_valid: bool
    final_score: int
    permission: int
    lifecycle: int
    p7_visible: bool
    p7z_visible: bool


@dataclass(frozen=True)
class P9Event:
    """One real, Pine-fired P8 alert event, captured alongside `P9TRACE`
    in the same buffer. Field names/shape mirror `p8_capture_log.P8Event`
    exactly (same wire format), but this dataclass is independent -- see
    module docstring for why it is not simply imported."""

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
        """Mirrors `AlertEvent.event_key`/`P8Event.event_key` exactly --
        the canonical identity a Pine event and a Python-oracle event are
        compared on."""
        return (self.event_type, self.poi_idx, self.bar_ms)


def _parse_trace_line(line: str) -> P9TraceRow:
    body = line[len("P9TRACE|") :]
    raw = _fields(body)
    required = (
        "bar",
        "poiIdx",
        "poiType",
        "poiDir",
        "zoneTop",
        "zoneBottom",
        "availTime",
        "terminal",
        "btmmValid",
        "finalScore",
        "permission",
        "lifecycle",
        "p7Visible",
        "p7zVisible",
    )
    missing = [f for f in required if f not in raw]
    if missing:
        raise P9CaptureError(f"P9TRACE line missing fields {missing}: {line[:160]!r}")
    if raw["poiDir"] not in ("-1", "1"):
        raise P9CaptureError(f"P9TRACE line has unknown poiDir {raw['poiDir']!r}: {line[:160]!r}")
    return P9TraceRow(
        bar_ms=int(raw["bar"]),
        poi_idx=int(raw["poiIdx"]),
        poi_type=int(raw["poiType"]),
        direction=int(raw["poiDir"]),
        zone_top=float(raw["zoneTop"]),
        zone_bottom=float(raw["zoneBottom"]),
        avail_time_ms=int(raw["availTime"]),
        terminal=_bool(raw, "terminal", line),
        btmm_valid=_bool(raw, "btmmValid", line),
        final_score=int(raw["finalScore"]),
        permission=int(raw["permission"]),
        lifecycle=int(raw["lifecycle"]),
        p7_visible=_bool(raw, "p7Visible", line),
        p7z_visible=_bool(raw, "p7zVisible", line),
    )


def _parse_event_line(line: str) -> P9Event:
    body = line[len("P8EVENT|") :]
    raw = _fields(body)
    required = ("type", "bar", "poiIdx", "poiDir", "poiTier", "btmmValid", "permission", "lifecycle")
    missing = [f for f in required if f not in raw]
    if missing:
        raise P9CaptureError(f"P8EVENT line missing fields {missing}: {line[:160]!r}")
    if raw["type"] not in _EVENT_TYPES:
        raise P9CaptureError(f"P8EVENT line has unknown type {raw['type']!r}")
    if raw["poiDir"] not in ("BULL", "BEAR"):
        raise P9CaptureError(f"P8EVENT line has unknown poiDir {raw['poiDir']!r}")
    return P9Event(
        event_type=raw["type"],
        bar_ms=int(raw["bar"]),
        poi_idx=int(raw["poiIdx"]),
        poi_bullish=raw["poiDir"] == "BULL",
        tier=int(raw["poiTier"]),
        btmm_valid=_bool(raw, "btmmValid", line),
        permission=int(raw["permission"]),
        lifecycle=int(raw["lifecycle"]),
    )


@dataclass(frozen=True)
class P9Capture:
    #: bar timestamp (ms) -> every `P9TRACE` row logged for that bar, in
    #: emission order (never re-sorted here).
    trace_by_bar: dict[int, tuple[P9TraceRow, ...]]
    #: Every real `P8EVENT`, in emission order (Pine's own per-bar,
    #: ascending-poi_idx, fixed-priority order).
    events: tuple[P9Event, ...]


def parse_p9_capture(text: str) -> P9Capture:
    trace_by_bar: dict[int, list[P9TraceRow]] = {}
    events: list[P9Event] = []
    seen_trace_lines: set[str] = set()
    seen_event_lines: set[str] = set()

    for raw_line in text.splitlines():
        line = _strip(raw_line)
        if line.startswith("P9TRACE|"):
            if line in seen_trace_lines:
                # A byte-identical duplicate emission (the same reload/tick
                # re-render phenomenon already documented for P5X/P5EVAL/P8)
                # is collapsed, not treated as a second real row.
                continue
            seen_trace_lines.add(line)
            row = _parse_trace_line(line)
            trace_by_bar.setdefault(row.bar_ms, []).append(row)
        elif line.startswith("P8EVENT|"):
            if line in seen_event_lines:
                continue
            seen_event_lines.add(line)
            events.append(_parse_event_line(line))

    return P9Capture(
        trace_by_bar={bar: tuple(rows) for bar, rows in trace_by_bar.items()},
        events=tuple(events),
    )


__all__ = [
    "P9Capture",
    "P9CaptureError",
    "P9Event",
    "P9TraceRow",
    "parse_p9_capture",
]
