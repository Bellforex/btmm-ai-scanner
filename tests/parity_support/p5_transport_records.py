"""Minimal duck-typed records the P5 transport reductions actually read.

Test/parity tooling only.

WHY NOT THE FULL CONTRACT MODELS
---------------------------------
``ConfirmedSwing`` carries 24 fields, ``StructureTransition`` 19, and both are
validated pydantic models. Building thousands of them for a randomized campaign
would be slow, and every one of those extra fields is noise: the reductions read
five attributes from a swing, four from a transition, five from a displacement
and three from the structure state, and nothing else.

These records expose exactly those attributes, with the REAL domain enums --
`_exhaustion` and `_retracement_depth` compare with ``is`` against
``SwingType.SWING_HIGH``, so a stand-in enum would silently fail every branch --
and ``Decimal`` prices, because ``_retracement_depth`` compares the impulse leg
against ``Decimal("0")``.

That the reduced shape is faithful is not assumed. The authoritative oracle
drives the REAL engine helpers over these records, and a cross-check builds
genuine ``ConfirmedSwing`` / ``StructureTransition`` / ``DisplacementObservation``
models for a directed fixture and asserts the same answers come back.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)

from .p5_transport_contract import C_ST_NA

__all__ = [
    "DisplacementRec",
    "StateRec",
    "SwingRec",
    "TransitionRec",
    "decode_epoch_ms",
    "epoch_ms",
]


def epoch_ms(moment: datetime | None) -> int:
    """UTC datetime -> epoch milliseconds, the WIRE representation for times.

    `None` (semantic absence) encodes to `C_ST_NA`. This is a one-way transport
    encoding, not a claim that `None` and `-99` are the same thing: a decoder
    inverts it back to `None` wherever a semantic comparison is needed, and nothing
    compares a raw Python `None` against a raw Pine `-99` directly.
    """
    if moment is None:
        return C_ST_NA
    return int(moment.timestamp() * 1000)


def decode_epoch_ms(value: int) -> int | None:
    """Inverse of `epoch_ms`: WIRE sentinel -> semantic absence.

    Used only where a comparison must happen in the semantic domain (never
    needed by the oracle/model differential itself, since both sides already
    encode through `epoch_ms` and so are wire-comparable as-is; provided for the
    live real-data decode step, which starts from Pine's raw wire integers).
    """
    return None if value == C_ST_NA else value


@dataclass(frozen=True)
class SwingRec:
    """Read by `_ordered_swings`, `_exhaustion` and `_retracement_depth`."""

    record_id: str
    swing_type: SwingType
    pivot_price: Decimal
    pivot_start_time_utc: datetime
    availability_time_utc: datetime


@dataclass(frozen=True)
class TransitionRec:
    """Read by `_ordered_transitions`, the streak scans and `_displacement_at`."""

    record_id: str
    transition_type: StructureTransitionType
    event_time_utc: datetime
    availability_time_utc: datetime


@dataclass(frozen=True)
class DisplacementRec:
    """Read by `_recent_displacements` and `_displacement_at`."""

    record_id: str
    direction: DisplacementDirection
    classification: DisplacementClassification
    range_speed_ratio: Decimal
    event_time_utc: datetime
    availability_time_utc: datetime


@dataclass(frozen=True)
class StateRec:
    """The three `CurrentStructureState` attributes the transport depends on."""

    direction: StructureDirection
    analyzed_swing_count: int
    availability_time_utc: datetime
