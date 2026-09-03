"""Mutation campaign for the P6 -> P5 transport reduction.

WHAT THIS ANSWERS
-----------------
The directed and randomized differentials say the two implementations agree.
They do not, on their own, say the corpus is strong enough to NOTICE a
disagreement. A campaign of empty histories would also agree.

So each mutation below is a plausible port defect, implemented for real -- not
by nudging a field value, which would only prove that changing a number is
visible. `_continuation_streak_skipping_newest` really does start its scan one
index early, the way a Pine `for i = n - 2 to 0` would. Every one must produce a
mismatch against the authoritative oracle somewhere in the shared corpus.

The control matters as much as the mutations: `test_the_unmutated_model_is_clean`
asserts zero mismatches over the same corpus, so a corpus that failed everything
indiscriminately could not be mistaken for a strong one.

THE MUTATIONS ARE THE FINDINGS OF THE SOURCE AUDIT, MADE EXECUTABLE
--------------------------------------------------------------------
Each maps to a specific thing the audit found and a port could plausibly get
wrong: `[:-1]` on the prior-opposite scan, the `<=` / `>` split in the pullback,
MAX-not-first in `_displacement_at`, same-type-not-last-two in `_exhaustion`,
and the oldest -> newest orientation of both windows.
"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import replace

import pytest

from btmm_ai_scanner.domain.enums import (
    DisplacementClassification,
    DisplacementDirection,
    SwingType,
)
from btmm_ai_scanner.structure.enums import (
    StructureDirection,
    StructureTransitionType,
)
from tests.parity_support.p5_transport_contract import (
    C_ST_NA,
    DISPLACEMENT_WINDOW_CAPACITY,
    TRANSITION_WINDOW_CAPACITY,
    P5TransportRecord,
)
from tests.parity_support.p5_transport_fixtures import (
    displacement,
    random_history,
    state,
    swing,
    transition,
)
from tests.parity_support.p5_transport_oracle import reduce_authoritative
from tests.parity_support.p5_transport_pine_model import (
    _DISP_CLS_CODE,
    _TRANS_CODE,
    reduce_pine_equivalent,
)
from tests.parity_support.p5_transport_records import (
    DisplacementRec,
    StateRec,
    SwingRec,
    TransitionRec,
    epoch_ms,
)

BULL_BOS = StructureTransitionType.BULLISH_BOS
BEAR_BOS = StructureTransitionType.BEARISH_BOS
BULL_CHOCH = StructureTransitionType.BULLISH_CHOCH
BEAR_CHOCH = StructureTransitionType.BEARISH_CHOCH
HIGH = SwingType.SWING_HIGH
LOW = SwingType.SWING_LOW
BULLISH = StructureDirection.BULLISH
BEARISH = StructureDirection.BEARISH
NORMAL = DisplacementClassification.NORMAL
FAST = DisplacementClassification.FAST
VERY_FAST = DisplacementClassification.VERY_FAST
UP = DisplacementDirection.BULLISH
DOWN = DisplacementDirection.BEARISH

History = tuple[
    list[SwingRec], list[TransitionRec], list[DisplacementRec], StateRec | None
]
Mutation = Callable[
    [Sequence[SwingRec], Sequence[TransitionRec], Sequence[DisplacementRec], object],
    P5TransportRecord,
]


# ---------------------------------------------------------------------------
# The shared corpus: directed cases that exercise each reduction, plus random
# ---------------------------------------------------------------------------


def _directed_corpus() -> list[History]:
    cases: list[History] = []

    # long continuation run, and a run interrupted at the newest position
    cases.append(
        (
            [],
            [transition(i + 1, BULL_BOS) for i in range(5)],
            [],
            state(BULLISH, 40),
        )
    )
    cases.append(
        (
            [],
            [transition(1, BULL_BOS), transition(2, BULL_BOS), transition(3, BULL_CHOCH)],
            [],
            state(BULLISH, 40),
        )
    )
    # the prior-opposite fixture: including the newest changes the answer
    cases.append(
        (
            [],
            [
                transition(1, BEAR_BOS),
                transition(2, BEAR_BOS),
                transition(3, BEAR_BOS),
                transition(4, BULL_CHOCH),
            ],
            [],
            state(BULLISH, 40),
        )
    )
    # a four-slot window whose reverse is distinguishable
    cases.append(
        (
            [],
            [
                transition(1, BULL_BOS),
                transition(2, BEAR_BOS),
                transition(3, BULL_CHOCH),
                transition(4, BEAR_CHOCH),
            ],
            [],
            state(BEARISH, 40),
        )
    )
    # a partial window, so front- vs back-padding differ
    cases.append(
        (
            [],
            [transition(1, BULL_BOS), transition(2, BEAR_CHOCH)],
            [],
            state(BEARISH, 40),
        )
    )
    # exhaustion: same-type vs last-two disagree here
    cases.append(
        (
            [
                swing(1, HIGH, "4500.00"),
                swing(2, HIGH, "4450.00"),
                swing(3, LOW, "4000.00"),
            ],
            [],
            [],
            state(BULLISH, 40),
        )
    )
    cases.append(
        (
            [
                swing(1, HIGH, "4400.00"),
                swing(2, LOW, "4300.00"),
                swing(3, HIGH, "4500.00"),
            ],
            [],
            [],
            state(BULLISH, 40),
        )
    )
    # displacement window whose reverse and whose middle-drop are visible
    cases.append(
        (
            [],
            [],
            [
                displacement(1, UP, NORMAL, "0.50"),
                displacement(2, DOWN, FAST, "1.70"),
                displacement(3, UP, VERY_FAST, "2.40"),
            ],
            state(BULLISH, 40),
        )
    )
    cases.append(
        (
            [],
            [],
            [
                displacement(1, UP, NORMAL, "0.50"),
                displacement(2, DOWN, FAST, "1.70"),
                displacement(3, UP, VERY_FAST, "2.40"),
                displacement(4, DOWN, NORMAL, "0.80"),
            ],
            state(BULLISH, 40),
        )
    )
    # displacement-at: first != max, and a later faster one exists elsewhere
    cases.append(
        (
            [],
            [transition(2, BULL_BOS), transition(5, BULL_BOS)],
            [
                displacement(5, UP, NORMAL, "0.90", suffix="a"),
                displacement(5, UP, VERY_FAST, "2.60", suffix="b"),
                displacement(7, DOWN, FAST, "1.80"),
            ],
            state(BULLISH, 40),
        )
    )
    cases.append(
        (
            [],
            [transition(2, BULL_BOS), transition(5, BULL_BOS)],
            [
                displacement(2, UP, VERY_FAST, "2.90"),
                displacement(5, UP, NORMAL, "0.90"),
            ],
            state(BULLISH, 40),
        )
    )
    # pullback: distinct impulse / origin / pullback prices
    cases.append(
        (
            [
                swing(1, LOW, "4300.00", start=0),
                swing(3, HIGH, "4500.00", start=2),
                swing(5, LOW, "4400.00", start=4),
            ],
            [],
            [],
            state(BULLISH, 40),
        )
    )
    # the <= boundary: the only origin candidate sits exactly on it
    cases.append(
        (
            [
                swing(2, LOW, "4300.00", start=2),
                swing(3, HIGH, "4500.00", start=2),
                swing(5, LOW, "4400.00", start=4),
            ],
            [],
            [],
            state(BULLISH, 40),
        )
    )
    # the > boundary: a counter swing exactly on the impulse start must NOT be
    # taken as the pullback
    cases.append(
        (
            [
                swing(1, LOW, "4300.00", start=0),
                swing(3, HIGH, "4500.00", start=2),
                swing(4, LOW, "4450.00", start=2),
                swing(6, LOW, "4400.00", start=5),
            ],
            [],
            [],
            state(BULLISH, 40),
        )
    )
    # bearish mirror
    cases.append(
        (
            [
                swing(1, HIGH, "4500.00", start=0),
                swing(3, LOW, "4300.00", start=2),
                swing(5, HIGH, "4400.00", start=4),
            ],
            [],
            [],
            state(BEARISH, 40),
        )
    )
    # everything at once, so cross-field mutations have somewhere to show
    cases.append(
        (
            [
                swing(1, LOW, "4300.00", start=0),
                swing(3, HIGH, "4500.00", start=2),
                swing(5, LOW, "4400.00", start=4),
                swing(7, HIGH, "4480.00", start=6),
            ],
            [
                transition(2, BEAR_BOS),
                transition(4, BEAR_BOS),
                transition(6, BULL_CHOCH),
                transition(8, BULL_BOS),
            ],
            [
                displacement(4, DOWN, FAST, "1.70"),
                displacement(8, UP, NORMAL, "0.95"),
                displacement(8, UP, VERY_FAST, "2.40", suffix="b"),
            ],
            state(BULLISH, 40),
        )
    )
    return cases


def _corpus() -> list[History]:
    cases = _directed_corpus()
    rng = random.Random(31337)
    for _ in range(600):
        cases.append(random_history(rng))
    return cases


CORPUS = _corpus()


def _mismatch_count(mutation: Mutation) -> int:
    total = 0
    for swings, transitions, displacements, current in CORPUS:
        authoritative = reduce_authoritative(
            swings, transitions, displacements, current
        )
        mutated = mutation(swings, transitions, displacements, current)
        if authoritative.differing_fields(mutated):
            total += 1
    return total


# ---------------------------------------------------------------------------
# Control
# ---------------------------------------------------------------------------


def test_the_unmutated_model_is_clean_on_the_whole_corpus() -> None:
    """Without this, a corpus that rejected everything would look excellent."""
    assert len(CORPUS) > 600
    assert _mismatch_count(reduce_pine_equivalent) == 0  # type: ignore[arg-type]


def test_the_corpus_is_not_degenerate() -> None:
    """At least some cases must fill both windows and produce a valid pullback,
    or the mutations touching those fields could never fire."""
    full_transitions = full_displacements = valid_pullbacks = matched_disp = 0
    for swings, transitions, displacements, current in CORPUS:
        record = reduce_authoritative(swings, transitions, displacements, current)
        full_transitions += record.transWindowCount == TRANSITION_WINDOW_CAPACITY
        full_displacements += record.dispWindowCount == DISPLACEMENT_WINDOW_CAPACITY
        valid_pullbacks += record.pbValid
        matched_disp += record.dispClsAtTrans != C_ST_NA
    assert full_transitions > 50
    assert full_displacements > 50
    assert valid_pullbacks > 20
    assert matched_disp > 20


# ---------------------------------------------------------------------------
# Mutations -- each one really re-implements the defect
# ---------------------------------------------------------------------------


def _base(
    swings: Sequence[SwingRec],
    transitions: Sequence[TransitionRec],
    displacements: Sequence[DisplacementRec],
    current: object,
) -> P5TransportRecord:
    return reduce_pine_equivalent(swings, transitions, displacements, current)  # type: ignore[arg-type]


def mut_continuation_skips_newest(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """`for i = n - 2 to 0`: the classic backwards-loop off-by-one."""
    codes = [_TRANS_CODE[t.transition_type] for t in transitions]
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    target = {
        StructureDirection.BULLISH: _TRANS_CODE[BULL_BOS],
        StructureDirection.BEARISH: _TRANS_CODE[BEAR_BOS],
    }.get(direction)
    streak = 0
    if target is not None:
        index = len(codes) - 2
        while index >= 0 and codes[index] == target:
            streak += 1
            index -= 1
    return replace(_base(swings, transitions, displacements, current), contStreak=streak)


def mut_prior_opposite_includes_newest(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """Scanning `transitions` instead of `transitions[:-1]`."""
    codes = [_TRANS_CODE[t.transition_type] for t in transitions]
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    target = {
        StructureDirection.BULLISH: _TRANS_CODE[BEAR_BOS],
        StructureDirection.BEARISH: _TRANS_CODE[BULL_BOS],
    }.get(direction)
    streak = 0
    if target is not None:
        index = len(codes) - 1
        while index >= 0 and codes[index] == target:
            streak += 1
            index -= 1
    return replace(
        _base(swings, transitions, displacements, current), priorOppStreak=streak
    )


def mut_transition_window_reversed(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    codes = [_TRANS_CODE[t.transition_type] for t in transitions]
    retained = codes[-TRANSITION_WINDOW_CAPACITY:][::-1]
    slots = retained + [C_ST_NA] * (TRANSITION_WINDOW_CAPACITY - len(retained))
    return replace(
        _base(swings, transitions, displacements, current),
        trans1Type=slots[0],
        trans2Type=slots[1],
        trans3Type=slots[2],
        trans4Type=slots[3],
    )


def mut_transition_window_right_aligned(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """Padding at the FRONT, so the newest always lands in slot 4."""
    codes = [_TRANS_CODE[t.transition_type] for t in transitions]
    retained = codes[-TRANSITION_WINDOW_CAPACITY:]
    slots = [C_ST_NA] * (TRANSITION_WINDOW_CAPACITY - len(retained)) + retained
    return replace(
        _base(swings, transitions, displacements, current),
        trans1Type=slots[0],
        trans2Type=slots[1],
        trans3Type=slots[2],
        trans4Type=slots[3],
    )


def mut_transition_window_keeps_oldest(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    codes = [_TRANS_CODE[t.transition_type] for t in transitions]
    retained = codes[:TRANSITION_WINDOW_CAPACITY]
    slots = retained + [C_ST_NA] * (TRANSITION_WINDOW_CAPACITY - len(retained))
    return replace(
        _base(swings, transitions, displacements, current),
        trans1Type=slots[0],
        trans2Type=slots[1],
        trans3Type=slots[2],
        trans4Type=slots[3],
    )


def mut_exhaustion_uses_last_two_swings(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """Ignoring swing type: comparing a high against a low."""
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    flag = 0
    if len(swings) >= 2 and direction in (BULLISH, BEARISH):
        latest, previous = swings[-1], swings[-2]
        if direction is BULLISH:
            flag = 1 if latest.pivot_price < previous.pivot_price else 0
        else:
            flag = 1 if latest.pivot_price > previous.pivot_price else 0
    return replace(_base(swings, transitions, displacements, current), exhaustFlag=flag)


def mut_exhaustion_comparison_reversed(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    base = _base(swings, transitions, displacements, current)
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    if direction not in (BULLISH, BEARISH):
        return base
    wanted = HIGH if direction is BULLISH else LOW
    same = [s for s in swings if s.swing_type is wanted]
    if len(same) < 2:
        return base
    latest, previous = same[-1], same[-2]
    flag = (
        1
        if (
            latest.pivot_price > previous.pivot_price
            if direction is BULLISH
            else latest.pivot_price < previous.pivot_price
        )
        else 0
    )
    return replace(base, exhaustFlag=flag)


def _with_window(
    base: P5TransportRecord, window: Sequence[DisplacementRec]
) -> P5TransportRecord:
    dirs = [1 if o.direction is UP else -1 for o in window]
    clss = [_DISP_CLS_CODE[o.classification] for o in window]
    ratios: list[float | None] = [float(o.range_speed_ratio) for o in window]
    pad = DISPLACEMENT_WINDOW_CAPACITY - len(window)
    dirs += [C_ST_NA] * pad
    clss += [C_ST_NA] * pad
    ratios += [None] * pad
    return replace(
        base,
        dispWindowCount=len(window),
        disp1Dir=dirs[0],
        disp1Cls=clss[0],
        disp1Ratio=ratios[0],
        disp2Dir=dirs[1],
        disp2Cls=clss[1],
        disp2Ratio=ratios[1],
        disp3Dir=dirs[2],
        disp3Cls=clss[2],
        disp3Ratio=ratios[2],
    )


def mut_displacement_window_reversed(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    window = list(displacements[-DISPLACEMENT_WINDOW_CAPACITY:])[::-1]
    return _with_window(_base(swings, transitions, displacements, current), window)


def mut_displacement_window_drops_middle(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    window = list(displacements[-DISPLACEMENT_WINDOW_CAPACITY:])
    if len(window) == 3:
        window = [window[0], window[2]]
    return _with_window(_base(swings, transitions, displacements, current), window)


def mut_displacement_window_shifted_one_older(  # type: ignore[no-untyped-def]
    swings, transitions, displacements, current
):
    window = (
        list(displacements[-DISPLACEMENT_WINDOW_CAPACITY - 1 : -1])
        if len(displacements) > DISPLACEMENT_WINDOW_CAPACITY
        else list(displacements[:DISPLACEMENT_WINDOW_CAPACITY])
    )
    return _with_window(_base(swings, transitions, displacements, current), window)


def mut_ratio_slots_shifted(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    base = _base(swings, transitions, displacements, current)
    return replace(
        base,
        disp1Ratio=base.disp2Ratio,
        disp2Ratio=base.disp3Ratio,
        disp3Ratio=base.disp1Ratio,
    )


def mut_disp_availability_from_oldest(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    window = list(displacements[-DISPLACEMENT_WINDOW_CAPACITY:])
    return replace(
        _base(swings, transitions, displacements, current),
        dispAvailT=epoch_ms(window[0].availability_time_utc) if window else None,
    )


def mut_displacement_at_first_match(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """Early-return on the first match instead of taking the maximum."""
    code = C_ST_NA
    if transitions:
        target = transitions[-1].availability_time_utc
        for observation in displacements:
            if observation.availability_time_utc == target:
                code = _DISP_CLS_CODE[observation.classification]
                break
    return replace(
        _base(swings, transitions, displacements, current), dispClsAtTrans=code
    )


def mut_displacement_at_minimum(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    code = C_ST_NA
    if transitions:
        target = transitions[-1].availability_time_utc
        matches = [
            _DISP_CLS_CODE[o.classification]
            for o in displacements
            if o.availability_time_utc == target
        ]
        if matches:
            code = min(matches)
    return replace(
        _base(swings, transitions, displacements, current), dispClsAtTrans=code
    )


def mut_displacement_at_latest_global(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """The most tempting wrong reading: just use the newest displacement."""
    code = (
        _DISP_CLS_CODE[displacements[-1].classification] if displacements else C_ST_NA
    )
    if not transitions:
        code = C_ST_NA
    return replace(
        _base(swings, transitions, displacements, current), dispClsAtTrans=code
    )


def mut_breakout_uses_previous_transition(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    base = _base(swings, transitions, displacements, current)
    if len(transitions) < 2:
        return base
    target = transitions[-2].availability_time_utc
    matches = [
        _DISP_CLS_CODE[o.classification]
        for o in displacements
        if o.availability_time_utc == target
    ]
    return replace(
        base,
        dispClsAtTrans=max(matches) if matches else C_ST_NA,
        lastTransAvailT=epoch_ms(target),
    )


def mut_state_availability_from_last_transition(  # type: ignore[no-untyped-def]
    swings, transitions, displacements, current
):
    base = _base(swings, transitions, displacements, current)
    return replace(base, stateAvailT=base.lastTransAvailT)


def _pullback_variant(  # type: ignore[no-untyped-def]
    swings, direction, *, origin_cmp, pullback_cmp, swap_roles=None
):
    if direction is BULLISH:
        impulse_type, counter_type = HIGH, LOW
    elif direction is BEARISH:
        impulse_type, counter_type = LOW, HIGH
    else:
        return None, None, None, False
    impulse = None
    for index in range(len(swings) - 1, -1, -1):
        if swings[index].swing_type is impulse_type:
            impulse = swings[index]
            break
    if impulse is None:
        return None, None, None, False
    origin = pullback = None
    for candidate in swings:
        if candidate.swing_type is not counter_type:
            continue
        if origin_cmp(candidate.pivot_start_time_utc, impulse.pivot_start_time_utc):
            origin = candidate
        elif pullback_cmp(candidate.pivot_start_time_utc, impulse.pivot_start_time_utc):
            pullback = candidate
    if origin is None or pullback is None:
        return None, None, None, False
    leg = (
        impulse.pivot_price - origin.pivot_price
        if direction is BULLISH
        else origin.pivot_price - impulse.pivot_price
    )
    if leg <= 0:
        return None, None, None, False
    values = (
        float(impulse.pivot_price),
        float(origin.pivot_price),
        float(pullback.pivot_price),
        True,
    )
    if swap_roles is not None:
        values = swap_roles(values)
    return values


def mut_pullback_origin_boundary_exclusive(  # type: ignore[no-untyped-def]
    swings, transitions, displacements, current
):
    """`<=` narrowed to `<`."""
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    impulse, origin, pullback, valid = _pullback_variant(
        swings, direction, origin_cmp=lambda a, b: a < b, pullback_cmp=lambda a, b: a > b
    )
    return replace(
        _base(swings, transitions, displacements, current),
        pbImpulsePrice=impulse,
        pbOriginPrice=origin,
        pbPullbackPrice=pullback,
        pbValid=valid,
    )


def mut_pullback_boundary_inclusive(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """`>` widened to `>=`, so the boundary swing becomes the pullback."""
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    impulse, origin, pullback, valid = _pullback_variant(
        swings,
        direction,
        origin_cmp=lambda a, b: a < b,
        pullback_cmp=lambda a, b: a >= b,
    )
    return replace(
        _base(swings, transitions, displacements, current),
        pbImpulsePrice=impulse,
        pbOriginPrice=origin,
        pbPullbackPrice=pullback,
        pbValid=valid,
    )


def mut_pullback_impulse_origin_swapped(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    base = _base(swings, transitions, displacements, current)
    return replace(
        base, pbImpulsePrice=base.pbOriginPrice, pbOriginPrice=base.pbImpulsePrice
    )


def mut_pullback_origin_pullback_swapped(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    base = _base(swings, transitions, displacements, current)
    return replace(
        base, pbOriginPrice=base.pbPullbackPrice, pbPullbackPrice=base.pbOriginPrice
    )


def mut_pullback_uses_first_impulse(swings, transitions, displacements, current):  # type: ignore[no-untyped-def]
    """Taking the OLDEST swing of the impulse type instead of the newest."""
    base = _base(swings, transitions, displacements, current)
    direction = getattr(current, "direction", StructureDirection.UNDETERMINED)
    if direction not in (BULLISH, BEARISH):
        return base
    impulse_type = HIGH if direction is BULLISH else LOW
    same = [s for s in swings if s.swing_type is impulse_type]
    if not same:
        return base
    return replace(base, pbImpulsePrice=float(same[0].pivot_price))


MUTATIONS: dict[str, Mutation] = {
    "continuation streak skips the newest transition": mut_continuation_skips_newest,
    "prior-opposite streak includes the newest transition": mut_prior_opposite_includes_newest,
    "transition window reversed": mut_transition_window_reversed,
    "transition window right-aligned": mut_transition_window_right_aligned,
    "transition window keeps the oldest four": mut_transition_window_keeps_oldest,
    "exhaustion uses the last two swings of any type": mut_exhaustion_uses_last_two_swings,
    "exhaustion comparison reversed": mut_exhaustion_comparison_reversed,
    "displacement window reversed": mut_displacement_window_reversed,
    "displacement window drops the middle observation": mut_displacement_window_drops_middle,
    "displacement window shifted one older": mut_displacement_window_shifted_one_older,
    "ratio slots shifted": mut_ratio_slots_shifted,
    "displacement availability taken from the oldest slot": mut_disp_availability_from_oldest,
    "displacement-at takes the first match": mut_displacement_at_first_match,
    "displacement-at takes the minimum": mut_displacement_at_minimum,
    "displacement-at uses the latest displacement overall": mut_displacement_at_latest_global,
    "breakout reads the previous transition": mut_breakout_uses_previous_transition,
    "state availability taken from the last transition": mut_state_availability_from_last_transition,
    "pullback origin boundary narrowed to <": mut_pullback_origin_boundary_exclusive,
    "pullback boundary widened to >=": mut_pullback_boundary_inclusive,
    "pullback impulse and origin swapped": mut_pullback_impulse_origin_swapped,
    "pullback origin and pullback swapped": mut_pullback_origin_pullback_swapped,
    "pullback uses the oldest impulse swing": mut_pullback_uses_first_impulse,
}


@pytest.mark.parametrize("name", sorted(MUTATIONS))
def test_every_mutation_is_caught(name: str) -> None:
    count = _mismatch_count(MUTATIONS[name])
    assert count > 0, f"corpus cannot detect: {name}"


def test_the_campaign_covers_at_least_twenty_defects() -> None:
    assert len(MUTATIONS) >= 20
