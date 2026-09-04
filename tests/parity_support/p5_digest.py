"""P5 global parity digest: (H1, H2) over the whole real capture's decisions.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

Reuses the P2 dual-hash primitives unchanged (same moduli, same bases, same
canonical integer encoding, same order-sensitive accumulation) -- the same
choice `p6_digest.py` made and for the same reason: those primitives are
integer-only, and every field this digest folds is already a Pine integer
code (there are no prices or ratios at the P5 decision layer to normalise).

WHAT THIS DIGEST IS FOR
------------------------
The per-field differential in `test_p5_atomic_capture_replay_parity.py`
already proves every P5EVAL row matches its wire-normalized Python replay
exactly, field by field. This digest is not a SUBSTITUTE for that -- a digest
match alone would never be accepted as the evidence, per the project's own
established convention (`P5TransportRecord.differing_fields`'s docstring
makes the same point for the transport contract). It is a compact, single
number that Pine's own log line and Python's replay can each be reduced to
independently, and folds EVERY row from EVERY bar into one order-sensitive
accumulation -- so it also catches a whole-row reordering or a
dropped/duplicated row that a per-field loop keyed by (bar, poiIdx) would not
by itself surface as a "mismatch" (it would surface as a row-count
difference instead, which this digest also implicitly covers by including
`poiIdx` and `bar` in the record).
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p5", Path(__file__).with_name("p2_digest.py")
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

#: The fields folded into one row's record, in this fixed order: the join key
#: (bar, poiIdx) first so a reordering or a wrong-POI substitution changes the
#: digest, then every bar-level field, then every POI-level field -- the
#: UNION of `BAR_LEVEL_EVAL_FIELDS` and `POI_LEVEL_EVAL_FIELDS` from
#: `p5_wire_normalized_replay.py`, plus `poiIdx`/`bar` themselves.
ROW_FIELDS: tuple[str, ...] = (
    "bar",
    "poiIdx",
    "d1Trend",
    "w1Trend",
    "h4Trend",
    "regime",
    "momDir",
    "momAccel",
    "momRaw",
    "brk",
    "brkScoreRaw",
    "pb",
    "session",
    "globalDir",
    "operCtx",
    "align",
    "sTrend",
    "sRegime",
    "sMomentum",
    "sBreakout",
    "sPoi",
    "sBtmm",
    "sLiquidity",
    "sVolatility",
    "final",
    "permission",
    "lifecycle",
)


def row_record(values: dict[str, Any]) -> tuple[int, ...]:
    """One row's `ROW_FIELDS`, canonically integer-encoded. Every field here
    is already a Pine integer code or a plain int (bar ms, poiIdx) -- no
    price/ratio normalisation is needed at this layer."""
    return tuple(encode_int(int(values[name])) for name in ROW_FIELDS)


def capture_digest(rows: list[dict[str, Any]]) -> tuple[int, int]:
    """(H1, H2) over rows in the EXACT order given -- callers sort by
    (bar, poiIdx) first so Pine's own emission order and the replay's
    reconstruction order fold identically regardless of dict iteration
    order elsewhere."""
    records = [row_record(row) for row in rows]
    return (
        hash_sequence(records, BASE1, MOD1),
        hash_sequence(records, BASE2, MOD2),
    )


__all__ = ["ROW_FIELDS", "SCHEMA_VERSION", "capture_digest", "row_record"]
