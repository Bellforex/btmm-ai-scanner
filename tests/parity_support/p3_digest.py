"""Frozen P3 CORE parity digest contract.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

This REUSES the P2 dual-hash primitives (`p2_digest.py`) without modifying
them: same moduli, same bases, same canonical integer encoding, same
tick-normalised prices, same order-sensitive accumulation. Only the record
shape and the ordering are new, because P3 hashes POIs rather than structure
states.

WHAT IS HASHED, AND WHY IT IS THIS AND NOT MORE
-----------------------------------------------
Every field below is either part of the semantic identity a downstream
consumer addresses, part of the geometry it reads, or part of the lifecycle
result P3 owns. Deliberately absent:

* Python UUIDs — Pine cannot compute them, and AD-1 established that no
  downstream consumer of P3 CORE depends on UUID ordering;
* drawing/rendering state — the semantic layer never depends on it;
* freshness/age — descriptive only, with no downstream reader.

ORDERING (AD-1). POIs are sorted by a purely semantic tuple before hashing, so
the digest cannot depend on detection order, array position, or identity
bytes. The bases detector emits nested candidates that share type, bounds and
availability, which is why the candidate time and the identity triple are part
of the key rather than an afterthought.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p3", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2

SCHEMA_VERSION = 1

#: Sentinel for "no value", identical to the structure contract.
C_ST_NA = -99

#: The frozen P3 POI record field order. Mirrored exactly by the Pine probe.
#: `PRICE` fields go through tick normalisation; everything else is an integer,
#: a code, or a millisecond timestamp.
POI_FIELD_ORDER: tuple[tuple[str, str], ...] = (
    ("poi_type", "INTEGER"),
    ("direction", "INTEGER"),
    ("zone_bottom", "PRICE"),
    ("zone_top", "PRICE"),
    ("candidate_time", "TIME"),
    ("confirm_time", "TIME"),
    ("avail_time", "TIME"),
    ("tier", "INTEGER"),
    ("src_first_time", "TIME"),
    ("src_count", "INTEGER"),
    ("src_last_time", "TIME"),
    ("status", "INTEGER"),
    ("transition_count", "INTEGER"),
    ("relevant_count", "INTEGER"),
    ("last_transition_code", "INTEGER"),
    ("last_transition_event", "TIME"),
    ("last_transition_avail", "TIME"),
    ("tap_count", "INTEGER"),
)

#: Detector families, for localising a real-data mismatch to one detector.
FAMILY_OF_TYPE: dict[int, str] = {
    1: "order_block",
    2: "order_block",
    3: "fair_value_gap",
    4: "fair_value_gap",
    5: "reversal_candle",
    6: "reversal_candle",
    7: "base",
    8: "base",
    9: "pressure_wick",
    10: "pressure_wick",
    11: "engulfing",
    12: "engulfing",
    13: "single_candle_reversal",
    14: "single_candle_reversal",
    15: "three_candle_star",
    16: "three_candle_star",
    17: "reference_zone",
    18: "reference_zone",
}

FAMILIES: tuple[str, ...] = (
    "order_block",
    "fair_value_gap",
    "reversal_candle",
    "base",
    "pressure_wick",
    "engulfing",
    "single_candle_reversal",
    "three_candle_star",
    "reference_zone",
)

#: Lifecycle-only fields, hashed separately so a lifecycle divergence does not
#: masquerade as a detector divergence.
LIFECYCLE_FIELDS: tuple[str, ...] = (
    "status",
    "transition_count",
    "relevant_count",
    "last_transition_code",
    "last_transition_event",
    "last_transition_avail",
    "tap_count",
)


@dataclass(frozen=True)
class P3PoiState:
    """One POI's full canonical projection at a given bar."""

    poi_type: int
    direction: int
    zone_bottom: Decimal
    zone_top: Decimal
    candidate_time: int
    confirm_time: int
    avail_time: int
    tier: int
    src_first_time: int
    src_count: int
    src_last_time: int
    status: int
    transition_count: int
    relevant_count: int
    last_transition_code: int
    last_transition_event: int
    last_transition_avail: int
    tap_count: int

    def sort_key(self, mintick: Decimal) -> tuple[int, ...]:
        """The AD-1 semantic ordering. No UUID, no index, no insertion order."""
        return (
            self.avail_time,
            self.poi_type,
            self.direction,
            _D.pine_round(self.zone_bottom / mintick),
            _D.pine_round(self.zone_top / mintick),
            self.candidate_time,
            self.confirm_time,
            self.src_first_time,
            self.src_count,
            self.src_last_time,
        )

    def encoded(self, mintick: Decimal) -> tuple[int, ...]:
        values: list[int] = []
        for name, kind in POI_FIELD_ORDER:
            raw = getattr(self, name)
            if kind == "PRICE":
                values.append(_D.encode_price(raw, mintick))
            else:
                values.append(_D.encode_int(raw))
        return tuple(values)


def order_states(states: list[P3PoiState], mintick: Decimal) -> list[P3PoiState]:
    """Canonical order. Sorting is total by construction, and asserted by test."""
    return sorted(states, key=lambda s: s.sort_key(mintick))


def overall_hashes(states: list[P3PoiState], mintick: Decimal) -> tuple[int, int]:
    records = [s.encoded(mintick) for s in order_states(states, mintick)]
    return (
        _D.hash_sequence(records, BASE1, MOD1),
        _D.hash_sequence(records, BASE2, MOD2),
    )


def family_hashes(states: list[P3PoiState], mintick: Decimal) -> dict[str, int]:
    """One hash per detector family, so a mismatch names the detector."""
    ordered = order_states(states, mintick)
    result: dict[str, int] = {}
    for family in FAMILIES:
        records = [
            s.encoded(mintick) for s in ordered if FAMILY_OF_TYPE[s.poi_type] == family
        ]
        result[family] = _D.hash_sequence(records, BASE1, MOD1)
    return result


def lifecycle_hashes(states: list[P3PoiState], mintick: Decimal) -> dict[str, int]:
    """One hash per lifecycle field across the ordered registry."""
    ordered = order_states(states, mintick)
    index_of = {name: i for i, (name, _kind) in enumerate(POI_FIELD_ORDER)}
    encoded = [s.encoded(mintick) for s in ordered]
    result: dict[str, int] = {}
    for field in LIFECYCLE_FIELDS:
        position = index_of[field]
        accumulator = 0
        for record in encoded:
            accumulator = _D.step(accumulator, record[position], BASE1, MOD1)
        result[field] = accumulator
    return result


def counts(states: list[P3PoiState]) -> tuple[int, int, int]:
    """(registry, active, terminal). Terminal is genuine invalidation only."""
    terminal = sum(1 for s in states if s.status == 10)
    return (len(states), len(states) - terminal, terminal)
