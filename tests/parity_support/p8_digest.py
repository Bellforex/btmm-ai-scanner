"""P8 real-event-stream digest: (H1, H2) over a captured, ordered event
sequence, comparable to the SAME digest folded from a Python oracle replay
of the identical captured state.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics. Reuses the P2 dual-hash primitives unchanged, for
the same reason `p5_digest.py` already gave: every field this digest folds
is already a plain integer or a Pine event-type string mapped to a fixed
integer code -- no price/ratio normalisation is needed at this layer.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p8", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2
encode_int = _D.encode_int
hash_sequence = _D.hash_sequence

SCHEMA_VERSION = 1

#: Fixed, stable integer code per V1 event type -- deliberately NOT reusing
#: Python's own `hash()` or enum ordinal (neither is a frozen wire
#: contract); this table is the digest's own frozen encoding, independent
#: of how `P8EventType`/Pine's log text happen to spell each type.
EVENT_TYPE_CODE: dict[str, int] = {
    "POI_ACTIVATED": 0,
    "BTMM_VALIDATED": 1,
    "PERMISSION_ENTERED_ACTIONABLE": 2,
    "PERMISSION_LOST_ACTIONABLE": 3,
    "POI_TERMINAL": 4,
}

#: The fields folded into one event's record, in this fixed order: the
#: join key (bar, poiIdx, event type) first so a reordering or a
#: wrong-event substitution changes the digest, then the remaining payload
#: fields.
EVENT_FIELDS: tuple[str, ...] = (
    "bar_ms",
    "poi_idx",
    "event_type",
    "poi_bullish",
    "tier",
    "btmm_valid",
    "permission",
    "lifecycle",
)


def event_record(event: Any) -> tuple[int, ...]:
    """One event's `EVENT_FIELDS`, canonically integer-encoded. Accepts
    either a `p8_alert_oracle.AlertEvent` or a `p8_capture_log.P8Event` --
    both dataclasses expose the same field names."""
    return (
        encode_int(int(event.bar_ms)),
        encode_int(int(event.poi_idx)),
        encode_int(EVENT_TYPE_CODE[str(event.event_type)]),
        encode_int(1 if event.poi_bullish else 0),
        encode_int(int(event.tier)),
        encode_int(1 if event.btmm_valid else 0),
        encode_int(int(event.permission)),
        encode_int(int(event.lifecycle)),
    )


def capture_digest(events: list[Any]) -> tuple[int, int]:
    """(H1, H2) over `events` in the EXACT order given -- callers sort by
    (bar_ms, poi_idx, a fixed event-type priority) first, matching the
    same deterministic order `AlertEngine.process` and the Pine P8 alert
    block both already produce, so a real capture's own emission order and
    a Python replay's reconstruction order fold identically."""
    records = [event_record(e) for e in events]
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


__all__ = ["EVENT_FIELDS", "EVENT_TYPE_CODE", "SCHEMA_VERSION", "capture_digest", "event_record"]
