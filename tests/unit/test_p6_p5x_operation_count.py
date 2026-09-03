"""The operation-count table the resource investigation asked for.

Deterministic, mechanical element-visit counting -- not a claim about Pine's
internal wall-clock, which this platform does not expose. See
`tests/parity_support/p6_p5x_operation_count.py` for what is and is not
counted and why.

This module exists to answer one narrow question honestly: how does the
extension's WORST-CASE per-bar cost scale with warm-up length, using swing and
transition counts actually observed on the live FXCM capture (roughly 50-90
per context) rather than invented numbers.
"""

from __future__ import annotations

from tests.parity_support.p6_p5x_operation_count import (
    LOOKBACK_WINDOW,
    SCANS,
    per_bar_visits,
    total_visits_by_reducer,
    total_visits_over_warmup,
)

#: Observed on the live FXCM capture (MEGA-AUTONOMOUS-16/17 resource report):
#: swing counts ranged roughly 58-73 across the six timeframes, transition
#: (structure event) counts were single digits per context at the captured
#: anchor. Used as the representative case below, not a worst case.
OBSERVED_SWING_COUNT = 70
OBSERVED_TRANSITION_COUNT = 8

WARMUP_LENGTHS = (300, 600, 1200, 1250, 1800)


def test_the_two_bounded_extractions_never_scale_with_history() -> None:
    """transWindowCount and dispWindowCount are the two cheap, bounded window
    extractions -- capped at 4 and 3 respectively regardless of how many
    swings/transitions/displacements have ever accumulated. dispClsAtTrans is
    the OTHER bounded scan and is checked separately below: it is bounded too,
    but at the full 300-element lookbackWindow, not at 3 or 4."""
    visits = per_bar_visits(swing_count=10_000, transition_count=10_000)
    assert visits["transWindowCount extraction"] == 4
    assert visits["dispWindowCount extraction"] == 3


def test_displacement_at_is_the_single_largest_fixed_cost() -> None:
    """The finding: dispClsAtTrans costs more per bar than every swing/
    transition scan combined, once swing/transition counts stay below 300 --
    which they did throughout the observed live capture."""
    visits = per_bar_visits(
        swing_count=OBSERVED_SWING_COUNT, transition_count=OBSERVED_TRANSITION_COUNT
    )
    other_total = sum(v for k, v in visits.items() if k != "dispClsAtTrans")
    assert visits["dispClsAtTrans"] == LOOKBACK_WINDOW
    assert visits["dispClsAtTrans"] > other_total


def test_operation_count_table_at_each_requested_warmup_length() -> None:
    """The table Phase 8 asked for: total worst-case element visits across all
    six contexts, at 300 / 600 / 1200 / 1250 / 1800 confirmed bars."""
    table: dict[int, int] = {}
    for bars in WARMUP_LENGTHS:
        table[bars] = total_visits_over_warmup(
            bars,
            swing_count=OBSERVED_SWING_COUNT,
            transition_count=OBSERVED_TRANSITION_COUNT,
        )
    # Monotonically increasing with warm-up length, and linear in it -- there
    # is no quadratic blow-up here, because every per-bar cost is itself
    # already bounded (by lookbackWindow or by the observed swing/transition
    # count), not by the cumulative bar count.
    assert list(table.values()) == sorted(table.values())
    per_bar_total = table[300] // 300
    for bars in WARMUP_LENGTHS:
        assert table[bars] == per_bar_total * bars


def test_the_per_reducer_breakdown_shows_where_cost_concentrates() -> None:
    breakdown = total_visits_by_reducer(
        1250,
        swing_count=OBSERVED_SWING_COUNT,
        transition_count=OBSERVED_TRANSITION_COUNT,
    )
    ranked = sorted(breakdown.items(), key=lambda kv: kv[1], reverse=True)
    assert ranked[0][0] == "dispClsAtTrans"
    assert ranked[0][1] == LOOKBACK_WINDOW * 1250 * 6
    # exhaustFlag, the pullback impulse search and the pullback role scan are
    # all bounded (in this WORST-CASE model) by the same swing count, so they
    # tie for second -- meaningfully smaller than dispClsAtTrans because 70 is
    # well below the fixed 300-element window, not because any one of them is
    # individually cheaper than the others.
    second_place = {name for name, visits in breakdown.items() if visits == ranked[1][1]}
    assert second_place == {
        "exhaustFlag",
        "pullback impulse search",
        "pullback role scan (origin+pullback)",
    }


def test_every_scan_is_accounted_for_in_the_inventory() -> None:
    assert len(SCANS) == 8
    bounded = [s for s in SCANS if s.bounded]
    unbounded_no_early_exit = [
        s for s in SCANS if not s.early_exit
    ]
    assert {s.name for s in bounded} == {
        "transWindowCount extraction",
        "dispWindowCount extraction",
        "dispClsAtTrans",
    }
    assert {s.name for s in unbounded_no_early_exit} == {
        "pullback role scan (origin+pullback)",
        "dispClsAtTrans",
    }


def test_total_visits_at_the_host_envelope_is_a_finite_measurable_number() -> None:
    """Stated as a concrete number so it can be compared against future
    evidence rather than argued about in the abstract, computed independently
    of `total_visits_over_warmup` from the same per-bar breakdown the other
    tests already pin, so a regression in either has to move both."""
    per_bar = per_bar_visits(
        swing_count=OBSERVED_SWING_COUNT, transition_count=OBSERVED_TRANSITION_COUNT
    )
    # transWindowCount=4, dispWindowCount=3, contStreak=8, priorOppStreak=8,
    # exhaustFlag=70, pullback impulse search=70, pullback role scan=70,
    # dispClsAtTrans=300 -> 4+3+8+8+70+70+70+300 = 533 visits/bar/context.
    assert sum(per_bar.values()) == 533
    total = total_visits_over_warmup(
        1250, swing_count=OBSERVED_SWING_COUNT, transition_count=OBSERVED_TRANSITION_COUNT
    )
    assert total == 533 * 1250 * 6
