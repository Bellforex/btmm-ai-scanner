"""Minimal `P5EVAL` state-line parser for P8's real-event-parity replay.

`p5_atomic_capture_log.parse_p5_atomic_capture` already parses `P5EVAL`
lines, but it REQUIRES `P5WIRE` lines to be present (it is built for the
P5 "ATOMIC" twin script's combined capture). The P8 DEV capture used for
real Pine-vs-Python event parity is a plain (non-ATOMIC) log: it carries
`P5EVAL` and `P8EVENT` together, with no `P5WIRE` at all. This module
extracts only the seven `P5EVAL` fields `p8_alert_oracle.PoiSnapshot`
needs, tolerant of any other tags (`P8EVENT`, `P7DIAG`, ...) interleaved
in the same buffer -- it simply ignores lines that aren't `P5EVAL`.

Test/parity tooling only — nothing in `src/` imports this.
"""

from __future__ import annotations

from tests.parity_support.p8_alert_oracle import PoiSnapshot

_NEEDED_FIELDS = (
    "bar",
    "poiIdx",
    "poiDir",
    "poiTier",
    "poiTerminal",
    "btmmValid",
    "permission",
    "lifecycle",
)


def parse_p5eval_snapshots(text: str) -> dict[int, list[PoiSnapshot]]:
    """Returns bar_ms -> every `PoiSnapshot` logged for that bar (emission
    order), built only from `P5EVAL` lines. Lines missing any needed field
    are skipped rather than raising -- this parser is deliberately lenient
    since it only feeds a real-data replay, not a strict capture proof."""
    by_bar: dict[int, list[PoiSnapshot]] = {}
    for raw_line in text.splitlines():
        if "P5EVAL|" not in raw_line:
            continue
        body = raw_line.split("P5EVAL|", 1)[1]
        fields: dict[str, str] = {}
        for part in body.split("|"):
            if "=" in part:
                key, _, value = part.partition("=")
                fields[key] = value
        if not all(name in fields for name in _NEEDED_FIELDS):
            continue
        bar_ms = int(fields["bar"])
        snapshot = PoiSnapshot(
            poi_idx=int(fields["poiIdx"]),
            poi_bullish=fields["poiDir"] == "BULL",
            tier=int(fields["poiTier"]),
            terminal=fields["poiTerminal"] == "true",
            btmm_valid=fields["btmmValid"] == "true",
            permission=int(fields["permission"]),
            lifecycle=int(fields["lifecycle"]),
        )
        by_bar.setdefault(bar_ms, []).append(snapshot)
    return by_bar


__all__ = ["parse_p5eval_snapshots"]
