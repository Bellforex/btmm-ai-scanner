"""Frozen P4 BTMM parity digest contract.

Test/parity tooling only -- nothing in `src/` imports this, and it changes no
production semantics.

This REUSES the P2 dual-hash primitives (`p2_digest.py`) unchanged: same moduli,
same bases, same canonical integer encoding, same tick-normalised prices, same
order-sensitive accumulation. Only the record shape and the ordering are new,
because P4 hashes BTMM setups rather than POIs or structure states.

WHAT IS HASHED, AND WHY IT IS THIS AND NOT MORE
-----------------------------------------------
`CurrentBtmmState` has 33 fields. Five are Python identity and provenance
(`record_id`, `content_fingerprint`, `provenance_id`, and the three version
fields) that Pine cannot compute and that the P3 AD-1 rule already excludes from
parity. `symbol` and `timeframe` are constant for a single-chart partition and
are carried in the bundle meta instead of on every row. `btmm_setup_record_id`
is a UUID; the setup is addressed here by its SOURCE POI's semantic identity,
which is the same addressing P3 froze.

Everything else is hashed, including the fields the no-evidence runtime never
moves off their defaults. Those are not omitted: a change that started moving
them -- which is exactly what quietly satisfying a reviewed gate would look like
-- has to change this digest.

ORDERING
--------
Setups are 1:1 with BTMM-eligible POIs, so the canonical order is the POI's own
semantic sort key, not registry order. That keeps the digest independent of
detection order, array position and identity bytes, exactly as P3's is.

Pine does NOT sort. The probe emits one row per setup in registry order and the
parser sorts on this side, so a mismatch can be localised to a row rather than
appearing only as two unequal integers. The probe's own registry-order hash is
kept as a transport-integrity check on the emitted rows, not as the semantic
comparison.
"""

from __future__ import annotations

import importlib.util
import sys
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

_SPEC = importlib.util.spec_from_file_location(
    "_p2_digest_for_p4", Path(__file__).with_name("p2_digest.py")
)
assert _SPEC is not None and _SPEC.loader is not None
_D = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = _D
_SPEC.loader.exec_module(_D)

MOD1, MOD2 = _D.MOD1, _D.MOD2
BASE1, BASE2 = _D.BASE1, _D.BASE2

SCHEMA_VERSION = 1

#: Sentinel for "no value", identical to the P2/P3 contracts.
C_ST_NA = -99

#: The frozen P4 BTMM setup record field order. Mirrored exactly by the Pine
#: probe's row emission.
BTMM_FIELD_ORDER: tuple[tuple[str, str], ...] = (
    # --- source POI identity: how a setup is addressed ---------------------
    ("poi_type", "INTEGER"),
    ("poi_direction", "INTEGER"),
    ("zone_bottom", "PRICE"),
    ("zone_top", "PRICE"),
    ("candidate_avail_time", "TIME"),
    # --- lifecycle ---------------------------------------------------------
    ("btmm_direction", "INTEGER"),
    ("primary_state", "INTEGER"),
    ("formation_stage", "INTEGER"),
    # --- gates -------------------------------------------------------------
    ("accuracy_gate", "INTEGER"),
    ("interaction_class", "INTEGER"),
    ("reaction_gate", "INTEGER"),
    ("reaction_class", "INTEGER"),
    ("reaction_speed_gate", "INTEGER"),
    ("reaction_speed_class", "INTEGER"),
    ("formation_tf_gate", "INTEGER"),
    # --- evidence surface (all PENDING in the no-evidence runtime) ----------
    ("market_direction", "INTEGER"),
    ("analytical_framework", "INTEGER"),
    ("session", "INTEGER"),
    ("volume", "INTEGER"),
    ("liquidity_status", "INTEGER"),
    ("liquidity_location", "INTEGER"),
    ("liquidity_source", "INTEGER"),
    ("reviewed_evidence_time", "TIME"),
    # --- terminal reasons and chronology ------------------------------------
    ("cancellation_reason", "INTEGER"),
    ("blocked_reason", "INTEGER"),
    ("availability_time", "TIME"),
    # --- transition reduction ------------------------------------------------
    ("transition_count", "INTEGER"),
    ("last_transition_code", "INTEGER"),
    ("last_transition_event", "TIME"),
    ("last_transition_avail", "TIME"),
)

FIELD_NAMES: tuple[str, ...] = tuple(name for name, _kind in BTMM_FIELD_ORDER)

#: Field groups, so a real-data mismatch names the stage that owns it rather
#: than only reporting two unequal integers.
GROUPS: dict[str, tuple[str, ...]] = {
    "identity": (
        "poi_type",
        "poi_direction",
        "zone_bottom",
        "zone_top",
        "candidate_avail_time",
    ),
    "lifecycle": ("btmm_direction", "primary_state", "formation_stage"),
    "accuracy": ("accuracy_gate", "interaction_class"),
    "reaction": ("reaction_gate", "reaction_class"),
    "speed": ("reaction_speed_gate", "reaction_speed_class"),
    "formation": ("formation_tf_gate",),
    "evidence": (
        "market_direction",
        "analytical_framework",
        "session",
        "volume",
        "liquidity_status",
        "liquidity_location",
        "liquidity_source",
        "reviewed_evidence_time",
    ),
    "terminal": ("cancellation_reason", "blocked_reason", "availability_time"),
    "transitions": (
        "transition_count",
        "last_transition_code",
        "last_transition_event",
        "last_transition_avail",
    ),
}


@dataclass(frozen=True)
class P4SetupState:
    """One BTMM setup, in the frozen canonical field order."""

    poi_type: int
    poi_direction: int
    zone_bottom: Decimal
    zone_top: Decimal
    candidate_avail_time: int
    btmm_direction: int
    primary_state: int
    formation_stage: int
    accuracy_gate: int
    interaction_class: int
    reaction_gate: int
    reaction_class: int
    reaction_speed_gate: int
    reaction_speed_class: int
    formation_tf_gate: int
    market_direction: int
    analytical_framework: int
    session: int
    volume: int
    liquidity_status: int
    liquidity_location: int
    liquidity_source: int
    reviewed_evidence_time: int
    cancellation_reason: int
    blocked_reason: int
    availability_time: int
    transition_count: int
    last_transition_code: int
    last_transition_event: int
    last_transition_avail: int

    def encoded(self, mintick: Decimal) -> tuple[int, ...]:
        out: list[int] = []
        for name, kind in BTMM_FIELD_ORDER:
            value = getattr(self, name)
            if kind == "PRICE":
                out.append(_D.encode_price(value, mintick))
            else:
                out.append(_D.encode_int(value))
        return tuple(out)

    def sort_key(self, mintick: Decimal) -> tuple[int, ...]:
        """Total by construction, and asserted by test.

        The source POI's identity is unique per setup because `analyze_btmm`
        creates exactly one setup per eligible POI, so this never has to fall
        back on a positional tiebreak.
        """
        return (
            self.poi_type,
            self.poi_direction,
            _D.encode_price(self.zone_bottom, mintick),
            _D.encode_price(self.zone_top, mintick),
            self.candidate_avail_time,
            self.availability_time,
            self.primary_state,
        )


def order_states(states: list[P4SetupState], mintick: Decimal) -> list[P4SetupState]:
    return sorted(states, key=lambda s: s.sort_key(mintick))


def overall_hashes(states: list[P4SetupState], mintick: Decimal) -> tuple[int, int]:
    records = [s.encoded(mintick) for s in order_states(states, mintick)]
    return (
        _D.hash_sequence(records, BASE1, MOD1),
        _D.hash_sequence(records, BASE2, MOD2),
    )


def group_hashes(states: list[P4SetupState], mintick: Decimal) -> dict[str, int]:
    """One hash per field group, so a mismatch names the stage that owns it."""
    ordered = order_states(states, mintick)
    index = {name: i for i, name in enumerate(FIELD_NAMES)}
    out: dict[str, int] = {}
    for group, names in GROUPS.items():
        picks = [index[n] for n in names]
        records = [tuple(s.encoded(mintick)[i] for i in picks) for s in ordered]
        out[group] = _D.hash_sequence(records, BASE1, MOD1)
    return out


def state_counts(states: list[P4SetupState]) -> dict[str, int]:
    """The counts the runtime diagnostics report, recomputed from the records."""
    from collections import Counter

    by_state = Counter(s.primary_state for s in states)
    by_stage = Counter(s.formation_stage for s in states)
    return {
        "registry": len(states),
        "candidate": by_state.get(1, 0),
        "forming": by_state.get(2, 0),
        "blocked": by_state.get(3, 0),
        "confirmed": by_state.get(4, 0),
        "cancelled": by_state.get(5, 0),
        "at_final_gate": by_stage.get(6, 0),
    }


def trace_rows(states: list[P4SetupState], mintick: Decimal) -> list[list[str]]:
    """One canonical row per setup -- the byte-level determinism artifact.

    Determinism is asserted on THIS, not just on the hashes, so a coincidental
    hash agreement cannot hide a difference in the underlying records.
    """
    return [
        [str(value) for value in state.encoded(mintick)]
        for state in order_states(states, mintick)
    ]
