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

__all__ = [
    "DisplacementRec",
    "StateRec",
    "SwingRec",
    "TransitionRec",
    "epoch_ms",
]


def epoch_ms(moment: datetime | None) -> int | None:
    """UTC datetime -> epoch milliseconds, the wire representation for times."""
    if moment is None:
        return None
    return int(moment.timestamp() * 1000)


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
