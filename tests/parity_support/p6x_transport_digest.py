"""The additive P5 transport digest — separate from, and never redefining, the
closed P6 digest contract.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics. `p6_digest.py`'s digest definition (the five old
transported surfaces) is untouched: this module folds only the 26 NEW
extension fields, in the frozen contract's wire order, using the SAME
dual-hash primitives P2/P6 already established.

WHY INTEGER ABSENCE ENCODES DIFFERENTLY HERE THAN IN P6's OLD SURFACE
------------------------------------------------------------------------
`p6_digest.encode_int` maps Python `None` to `0` (Pine's `na`) -- the right
rule for the old surface, whose absent integer fields really are `na` on the
Pine side. The 26-field WIRE domain is different by design: its absent
integers are the literal sentinel `C_ST_NA` (-99), never `na`, because Pine
requires `type` field defaults to be compile-time literals (CE10132) and every
comparison/assignment for these fields goes through the named constant. So a
`P5TransportRecord`'s integer fields are never `None` -- they are concrete
`int` always, with `-99` already standing in for absence -- and this module
folds them with the ordinary `encode_int(int)` path, no special-casing. The
float fields (ratios and prices) keep the OLD convention: `None` encodes as
Pine `na` (`0`), matching `pbImpulsePrice=NaN` on the wire.
"""

from __future__ import annotations

import importlib.util
import sys
from decimal import Decimal
from pathlib import Path
from typing import Any

_SPEC = importlib.util.spec_from_file_location(
    "_p6x_digest_base", Path(__file__).with_name("p2_digest.py")
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

from .p5_transport_contract import FIELD_NAMES, FIELDS  # noqa: E402

MINTICK = Decimal("0.01")

#: Ratios are bare numbers, not prices -- quantised to a fixed scale, exactly
#: as `p6_digest.encode_ratio` does for the old DISP surface.
RATIO_SCALE = Decimal("1000000")

#: Fields the contract types as `float` and treats as a PRICE (tick-encoded)
#: rather than a bare ratio.
_PRICE_FIELDS = frozenset({"pbImpulsePrice", "pbOriginPrice", "pbPullbackPrice"})

#: Timeframe codes, identical to `p6_digest.TF_CODE` -- duplicated rather than
#: imported so this module has no dependency on the old digest module at all.
TF_CODE: dict[str, int] = {
    "W1": 10080,
    "D1": 1440,
    "H4": 240,
    "H1": 60,
    "M15": 15,
    "M5": 5,
}


def _encode_ratio(value: float | None) -> int:
    if value is None:
        return 0
    scaled = _D.pine_round(Decimal(str(value)) * RATIO_SCALE)
    return encode_int(int(scaled))


def _encode_field(name: str, value: Any, *, mintick: Decimal | float) -> int:
    field = next(f for f in FIELDS if f.name == name)
    if field.pine_type == "int":
        assert isinstance(value, int) and not isinstance(value, bool), (name, value)
        return encode_int(value)
    if field.pine_type == "bool":
        return encode_int(1 if value else 0)
    # float
    if name in _PRICE_FIELDS:
        return encode_price(value, mintick)
    return _encode_ratio(value)


def transport_record(
    values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> tuple[int, ...]:
    """One timeframe's 26 fields, encoded in frozen wire order."""
    return tuple(_encode_field(name, values[name], mintick=mintick) for name in FIELD_NAMES)


def transport_digest(
    values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> tuple[int, int]:
    """(H1, H2) over one timeframe's 26-field transport record."""
    record = transport_record(values, mintick=mintick)
    return (hash_record(record, BASE1, MOD1), hash_record(record, BASE2, MOD2))


def timeframe_transport_digest(
    timeframe: str, values: dict[str, Any], *, mintick: Decimal | float = MINTICK
) -> tuple[int, int]:
    """(TF_H1, TF_H2): the timeframe code leads, so two timeframes producing
    identical field values still hash differently."""
    if timeframe not in TF_CODE:
        raise KeyError(f"unknown timeframe: {timeframe}")
    records = [(encode_int(TF_CODE[timeframe]),), transport_record(values, mintick=mintick)]
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


def global_transport_digest(
    per_timeframe: dict[str, dict[str, Any]], *, mintick: Decimal | float = MINTICK
) -> tuple[int, int]:
    """(H1, H2) over the whole extension capture, timeframes in authority
    order -- fixed here, not taken from the caller's dict iteration order."""
    records: list[tuple[int, ...]] = []
    for timeframe in ("W1", "D1", "H4", "H1", "M15", "M5"):
        if timeframe not in per_timeframe:
            raise KeyError(f"capture is missing timeframe {timeframe}")
        records.append((encode_int(TF_CODE[timeframe]),))
        records.append(transport_record(per_timeframe[timeframe], mintick=mintick))
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )
