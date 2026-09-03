"""Frozen P6 cross-timeframe parity digest contract.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

This REUSES the P2 dual-hash primitives (`p2_digest.py`) unchanged: same moduli,
same bases, same canonical integer encoding, same tick-normalised prices, same
order-sensitive accumulation. Only the record shapes are new. Reusing them
matters for a reason beyond tidiness — those primitives are integer-only, which
is what lets Pine reproduce them exactly, and P2 closure already proved it does.

TWO DIGEST LAYERS, AND WHY BOTH ARE NEEDED
-------------------------------------------
**INPUT digest.** Hashes a timeframe's ordered candles. Its job is to lock the
raw candles handed to Python to the exact candles the Pine semantic execution
consumed. That lock is what makes a sequential capture sound: the six raw
exports happen in separate executions, and without it the M5/M15 windows could
silently shift by a bar between runs — "historical bars are immutable" does NOT
cover that, because the 1251-bar window slides forward as new bars confirm.

**OUTPUT digests.** Five per timeframe, one per transported surface, plus a
combined. Their job is the actual parity comparison.

WHAT THE OUTPUT DIGESTS COVER
------------------------------
Exactly the eleven fields P6 transports, grouped by surface. That is the whole
contract as implemented: a `request.security` tuple cannot carry a collection,
so the Pine transports a REDUCTION of each surface (count, plus the last
element's semantic fields) rather than the collection itself. Hashing more than
is transported would compare something the port does not produce; hashing less
would let a real difference through.

The grouping is not cosmetic. When a combined digest mismatches, the surface
digests say immediately WHICH of the five is responsible, which is the
difference between a one-line diagnosis and re-deriving the whole capture.

ABSENT VALUES
-------------
Pine keeps two distinct spellings of "nothing here", and so does this contract:
`na` for prices and times that were never set, and the `C_ST_NA` (-99) sentinel
for integer codes. They encode differently, so a port that confused them would
change the digest rather than pass quietly.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p6", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2

encode_int = _D.encode_int
encode_price = _D.encode_price
hash_record = _D.hash_record
hash_sequence = _D.hash_sequence
encode_input_bar = _D.encode_input_bar

SCHEMA_VERSION = 1

#: Pine's integer "absent" sentinel, identical to the P2/P3/P4 contracts.
C_ST_NA = -99

#: Default instrument tick. FX:XAUUSD quotes to two decimals.
MINTICK = Decimal("0.01")

#: Stable timeframe codes. Deliberately NOT the Pine resolution strings ("W",
#: "240"), because those are display spellings; a numeric code cannot be
#: accidentally reformatted between the two runtimes.
TF_CODE: dict[str, int] = {
    "W1": 10080,
    "D1": 1440,
    "H4": 240,
    "H1": 60,
    "M15": 15,
    "M5": 5,
}

#: The transported surfaces, in canonical order, with the fields each covers and
#: how each field is encoded. Mirrored exactly by the Pine probe's row emission.
SURFACE_FIELDS: dict[str, tuple[tuple[str, str], ...]] = {
    "SWINGS": (
        ("swing_count", "INTEGER"),
        ("last_swing_type", "INTEGER"),
        ("last_swing_price", "PRICE"),
        ("last_conf_time", "INTEGER"),
    ),
    "EQUAL": (("equal_level_count", "INTEGER"),),
    "DISP": (
        ("disp_code", "INTEGER"),
        ("disp_ratio", "RATIO"),
    ),
    "P2_TRANS": (
        ("p2_transition_count", "INTEGER"),
        ("p2_last_transition_code", "INTEGER"),
        ("p2_last_broken_level", "PRICE"),
    ),
    "P2_STATE": (("p2_direction", "INTEGER"),),
}

SURFACE_ORDER: tuple[str, ...] = ("SWINGS", "EQUAL", "DISP", "P2_TRANS", "P2_STATE")

#: The displacement ratio is a bare ratio, not a price, so it has no tick to
#: normalise against. It is quantised to a fixed scale instead, which both
#: runtimes can reproduce with integer arithmetic.
RATIO_SCALE = Decimal("1000000")


def encode_ratio(value: Decimal | float | None) -> int:
    """Ratio -> fixed-scale integer -> canonical encoding."""
    if value is None:
        return 0
    scaled = _D.pine_round(Decimal(str(value)) * RATIO_SCALE)
    return encode_int(scaled)


def _encode_field(kind: str, raw: Any, mintick: Decimal | float) -> int:
    if kind == "PRICE":
        return encode_price(raw, mintick)
    if kind == "RATIO":
        return encode_ratio(raw)
    return encode_int(raw)


# ---------------------------------------------------------------------------
# INPUT digest -- locks raw candles to the semantic execution
# ---------------------------------------------------------------------------


def input_records(
    bars: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    mintick: Decimal | float = MINTICK,
) -> list[tuple[int, ...]]:
    """Encode ordered candles (OLDEST -> NEWEST) as input records.

    Each bar is a mapping with `time_ms`, `open`, `high`, `low`, `close` and
    `time_close_ms`, matching the frozen P2 input record exactly.
    """
    return [
        encode_input_bar(
            time_ms=bar["time_ms"],
            open_=bar["open"],
            high=bar["high"],
            low=bar["low"],
            close=bar["close"],
            time_close_ms=bar["time_close_ms"],
            mintick=mintick,
        )
        for bar in bars
    ]


def input_digest(
    bars: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    mintick: Decimal | float = MINTICK,
) -> tuple[int, int]:
    """(INPUT_H1, INPUT_H2) over one timeframe's ordered candles."""
    records = input_records(bars, mintick=mintick)
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


# ---------------------------------------------------------------------------
# OUTPUT digests -- the parity comparison itself
# ---------------------------------------------------------------------------


def surface_record(
    surface: str, values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> tuple[int, ...]:
    """One surface's encoded fields, in this contract's frozen order."""
    fields = SURFACE_FIELDS[surface]
    return tuple(_encode_field(kind, values[name], mintick) for name, kind in fields)


def surface_digest(
    surface: str, values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> int:
    """A single surface digest, under MOD1 -- enough to localise a mismatch."""
    return hash_record(surface_record(surface, values, mintick=mintick), BASE1, MOD1)


def surface_digests(
    values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> dict[str, int]:
    """All five surface digests for one timeframe."""
    return {
        surface: surface_digest(surface, values, mintick=mintick)
        for surface in SURFACE_ORDER
    }


def timeframe_digest(
    timeframe: str, values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> tuple[int, int]:
    """(TF_H1, TF_H2) over one timeframe's whole transported surface set.

    The timeframe code leads the record, so two timeframes that happened to
    produce identical values still hash differently -- otherwise a projection
    that ignored its timeframe could pass.
    """
    if timeframe not in TF_CODE:
        raise KeyError(f"unknown timeframe: {timeframe}")
    records = [(encode_int(TF_CODE[timeframe]),)]
    records += [
        surface_record(surface, values, mintick=mintick) for surface in SURFACE_ORDER
    ]
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


def capture_digest(
    per_timeframe: dict[str, dict[str, Any]],
    *,
    mintick: Decimal | float = MINTICK,
) -> tuple[int, int]:
    """(H1, H2) over the whole capture, timeframes in authority order.

    Authority order is fixed here rather than taken from the caller's dict, so
    the global digest cannot change because of iteration order.
    """
    records: list[tuple[int, ...]] = []
    for timeframe in ("W1", "D1", "H4", "H1", "M15", "M5"):
        if timeframe not in per_timeframe:
            raise KeyError(f"capture is missing timeframe {timeframe}")
        values = per_timeframe[timeframe]
        records.append((encode_int(TF_CODE[timeframe]),))
        records += [
            surface_record(surface, values, mintick=mintick)
            for surface in SURFACE_ORDER
        ]
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


def projection_values(projection: Any) -> dict[str, Any]:
    """Adapt a `P6Projection` from the oracle into this contract's field names."""
    return dict(projection.compare_values())
