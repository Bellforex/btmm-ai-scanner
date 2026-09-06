"""P9 integrated-record digest: (H1, H2) over a full-system canonical
record stream (`P9Record` sequences), comparable to the SAME digest folded
from a Python integrated replay of identical captured state.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics. Reuses the P2 dual-hash primitives unchanged, the
same reason `p5_digest.py`/`p8_digest.py` already gave: every field this
digest folds is already a plain integer, float, string, or bool mapped to
a fixed integer/string encoding — no price/ratio normalisation is needed
at this layer.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p9", Path(__file__).with_name("p2_digest.py")
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

#: P2's own `encode_price` requires a mintick (a real price-precision
#: concern that digest already solves for candle-level data); P9's zone
#: prices need no such normalisation -- they are already exact, unrounded
#: `poiZoneTop`/`poiZoneBottom` floats copied verbatim from the P3
#: registry. Five decimal digits comfortably covers XAUUSD's real tick
#: size with headroom; this is a stable, deterministic integer encoding
#: for hashing, not a precision-loss concern.
_FLOAT_SCALE = 100_000


def encode_float(value: float) -> int:
    return int(encode_int(round(value * _FLOAT_SCALE)))


#: Every `P9Record` field folded into one canonical record, in this fixed
#: order: the join key (bar, idx) first so a reordering or a wrong-record
#: substitution changes the digest, then the remaining payload fields in a
#: stable, frozen order.
RECORD_FIELDS: tuple[str, ...] = (
    "bar_ms",
    "idx",
    "poi_type",
    "direction",
    "zone_top",
    "zone_bottom",
    "avail_time_ms",
    "terminal",
    "btmm_valid",
    "final_score",
    "permission",
    "lifecycle",
    "p7_visible",
    "p7z_visible",
    "event_types",
)

#: Fixed, stable integer code per V1 event type -- deliberately NOT reusing
#: Python's own `hash()`/enum ordinal, mirroring `p8_digest.py`'s own
#: `EVENT_TYPE_CODE` table exactly (same frozen wire contract, reused here
#: rather than re-declared, so the two digests can never silently diverge).
_P8_DIGEST_SPEC = importlib.util.spec_from_file_location(
    "_p8_digest_for_p9", Path(__file__).with_name("p8_digest.py")
)
assert _P8_DIGEST_SPEC is not None and _P8_DIGEST_SPEC.loader is not None
_P8D = importlib.util.module_from_spec(_P8_DIGEST_SPEC)
sys.modules[_P8_DIGEST_SPEC.name] = _P8D
_P8_DIGEST_SPEC.loader.exec_module(_P8D)
EVENT_TYPE_CODE: dict[str, int] = _P8D.EVENT_TYPE_CODE


#: A record can carry MULTIPLE events on one bar (e.g. POI_ACTIVATED +
#: BTMM_VALIDATED simultaneously) -- folded as a fixed-width bitmask over
#: `EVENT_TYPE_CODE`'s 5 codes so the digest is order-independent within
#: one record's own event set (Pine's `p8Base` block always emits them in
#: the same fixed textual order per bar per POI regardless, but the mask
#: makes that assumption unnecessary to prove here).
def _event_mask(event_types: tuple[str, ...]) -> int:
    mask = 0
    for name in event_types:
        mask |= 1 << EVENT_TYPE_CODE[name]
    return mask


def record_key(record: Any) -> tuple[int, int]:
    """The join key a real Pine capture and a Python replay must agree on
    before any other field comparison is meaningful."""
    return (int(record.bar_ms), int(record.idx))


def record_tuple(record: Any) -> tuple[int, ...]:
    """One `P9Record`'s `RECORD_FIELDS`, canonically integer-encoded."""
    return (
        encode_int(int(record.bar_ms)),
        encode_int(int(record.idx)),
        encode_int(int(record.poi_type)),
        encode_int(int(record.direction)),
        encode_float(float(record.zone_top)),
        encode_float(float(record.zone_bottom)),
        encode_int(int(record.avail_time_ms)),
        encode_int(1 if record.terminal else 0),
        encode_int(1 if record.btmm_valid else 0),
        encode_int(int(record.final_score)),
        encode_int(int(record.permission)),
        encode_int(int(record.lifecycle)),
        encode_int(1 if record.p7_visible else 0),
        encode_int(1 if record.p7z_visible else 0),
        encode_int(_event_mask(tuple(record.event_types))),
    )


def integrated_digest(records: list[Any]) -> tuple[int, int]:
    """(H1, H2) over `records` in the EXACT order given -- callers sort by
    (bar_ms, idx) first (the ascending-registry-index order every real
    per-bar emission already uses), so a real capture's own order and a
    Python replay's reconstruction order fold identically."""
    tuples = [record_tuple(r) for r in records]
    return (
        hash_sequence(tuples, BASE1, MOD1),
        hash_sequence(tuples, BASE2, MOD2),
    )


__all__ = [
    "EVENT_TYPE_CODE",
    "RECORD_FIELDS",
    "SCHEMA_VERSION",
    "integrated_digest",
    "record_key",
    "record_tuple",
]
