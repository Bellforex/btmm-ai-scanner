"""Source-valid history generators for the P5 transport differential.

Test/parity tooling only.

THE ORDERING INVARIANT THESE GENERATORS MAINTAIN
-------------------------------------------------
The authoritative oracle sorts by ``(availability_time_utc, event_time_utc,
str(record_id))``; the Pine-equivalent model cannot sort at all, because Pine
has no record ids and appends events as bars confirm. The two agree only when
arrival order already IS sorted order.

Every generator here emits strictly increasing availability times, which makes
the oracle's sort a no-op and the assumption explicit. A fixture that violates
it is a fixture describing something the scanner cannot produce -- one
timeframe's structure walk emits at most one event per confirmed bar -- and
`test_the_arrival_order_assumption_is_the_only_ordering_risk` pins that as the
single ordering hazard rather than leaving it unsaid.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
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

from .p5_transport_records import (
    DisplacementRec,
    StateRec,
    SwingRec,
    TransitionRec,
)

BASE = datetime(2026, 1, 1, tzinfo=UTC)
STEP = timedelta(minutes=15)

TRANSITION_TYPES = (
    StructureTransitionType.BULLISH_BOS,
    StructureTransitionType.BEARISH_BOS,
    StructureTransitionType.BULLISH_CHOCH,
    StructureTransitionType.BEARISH_CHOCH,
)
CLASSIFICATIONS = (
    DisplacementClassification.NORMAL,
    DisplacementClassification.FAST,
    DisplacementClassification.VERY_FAST,
)
DIRECTIONS = (DisplacementDirection.BULLISH, DisplacementDirection.BEARISH)


def moment(index: int) -> datetime:
    return BASE + STEP * index


def swing(
    index: int, swing_type: SwingType, price: str | Decimal, *, start: int | None = None
) -> SwingRec:
    """A confirmed swing whose pivot starts one step before it becomes available
    unless ``start`` overrides -- the boundary the pullback split turns on."""
    start_index = index - 1 if start is None else start
    return SwingRec(
        record_id=f"s{index:04d}",
        swing_type=swing_type,
        pivot_price=Decimal(price),
        pivot_start_time_utc=moment(start_index),
        availability_time_utc=moment(index),
    )


def transition(index: int, kind: StructureTransitionType) -> TransitionRec:
    return TransitionRec(
        record_id=f"t{index:04d}",
        transition_type=kind,
        event_time_utc=moment(index),
        availability_time_utc=moment(index),
    )


def displacement(
    index: int,
    direction: DisplacementDirection,
    classification: DisplacementClassification,
    ratio: str | Decimal,
    *,
    availability: int | None = None,
    suffix: str = "",
) -> DisplacementRec:
    at = index if availability is None else availability
    return DisplacementRec(
        record_id=f"d{index:04d}{suffix}",
        direction=direction,
        classification=classification,
        range_speed_ratio=Decimal(ratio),
        event_time_utc=moment(at),
        availability_time_utc=moment(at),
    )


def state(
    direction: StructureDirection, index: int, swing_count: int = 8
) -> StateRec:
    return StateRec(
        direction=direction,
        analyzed_swing_count=swing_count,
        availability_time_utc=moment(index),
    )


def random_history(
    rng: random.Random,
) -> tuple[
    list[SwingRec], list[TransitionRec], list[DisplacementRec], StateRec | None
]:
    """One source-valid random history: chronological, alternating-ish swings.

    Swings mostly alternate, as real pivots do, but repeat sometimes: both
    `_exhaustion` and `_retracement_depth` filter by swing type, so a history
    that never repeats a type would leave their "two most recent OF THIS TYPE"
    logic indistinguishable from "the two most recent".
    """
    clock = 0

    swings: list[SwingRec] = []
    n_swings = rng.randint(0, 12)
    swing_type = rng.choice((SwingType.SWING_HIGH, SwingType.SWING_LOW))
    for _ in range(n_swings):
        clock += rng.randint(1, 3)
        price = Decimal(rng.randint(400000, 460000)) / Decimal(100)
        swings.append(swing(clock, swing_type, price))
        if rng.random() < 0.8:
            swing_type = (
                SwingType.SWING_LOW
                if swing_type is SwingType.SWING_HIGH
                else SwingType.SWING_HIGH
            )

    transitions: list[TransitionRec] = []
    n_transitions = rng.randint(0, 9)
    for _ in range(n_transitions):
        clock += rng.randint(1, 3)
        transitions.append(transition(clock, rng.choice(TRANSITION_TYPES)))

    displacements: list[DisplacementRec] = []
    n_displacements = rng.randint(0, 8)
    transition_times = [t.availability_time_utc for t in transitions]
    for _ in range(n_displacements):
        clock += rng.randint(1, 3)
        ratio = Decimal(rng.randint(0, 400)) / Decimal(100)
        displacements.append(
            displacement(
                clock, rng.choice(DIRECTIONS), rng.choice(CLASSIFICATIONS), ratio
            )
        )
    # Give `_displacement_at` something to find often enough to matter: without
    # this it would answer "absent" in nearly every random case and the field
    # would be untested by the campaign.
    if transition_times and displacements and rng.random() < 0.6:
        target = rng.choice(transitions)
        victim = rng.randrange(len(displacements))
        old = displacements[victim]
        displacements[victim] = DisplacementRec(
            record_id=old.record_id,
            direction=old.direction,
            classification=old.classification,
            range_speed_ratio=old.range_speed_ratio,
            event_time_utc=target.availability_time_utc,
            availability_time_utc=target.availability_time_utc,
        )
        displacements.sort(key=lambda o: (o.availability_time_utc, o.event_time_utc))

    current_state: StateRec | None
    if rng.random() < 0.1:
        current_state = None
    else:
        clock += 1
        current_state = state(
            rng.choice(
                (
                    StructureDirection.BULLISH,
                    StructureDirection.BEARISH,
                    StructureDirection.UNDETERMINED,
                )
            ),
            clock,
            swing_count=len(swings),
        )
    return swings, transitions, displacements, current_state
