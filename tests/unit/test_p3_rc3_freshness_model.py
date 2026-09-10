"""Phase 25/26 tests for the RC3 first-reaction lifecycle and qualification split.

These pin the proposed contract, including the two mutants the brief names
explicitly: same-bar self-mitigation and an ignored boundary touch. They also
pin the real FXCM H4 reference formations so the audit's numbers cannot drift
silently.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tests.parity_support.p3_freshness_model import (
    Bar,
    LifecycleState,
    PoiInterval,
    TerminalReason,
    body_engulfs,
    intersects,
    qualify_engulfing,
    qualify_frozen,
    qualify_with_range_engulfment,
    range_engulfs,
    resolve_lifecycle,
)


def _bar(index: int, o: str, h: str, low: str, c: str) -> Bar:
    return Bar(index, Decimal(o), Decimal(h), Decimal(low), Decimal(c))


ZONE = PoiInterval(top=Decimal("100"), bottom=Decimal("90"), availability_index=1)


# ---- the availability bar never consumes its own POI ------------------------


def test_availability_bar_sitting_inside_the_zone_does_not_mitigate() -> None:
    bars = [_bar(1, "95", "99", "91", "98")]
    assert resolve_lifecycle(bars, ZONE).state is LifecycleState.VALIDATED_FRESH


def test_bars_before_availability_do_not_mitigate() -> None:
    bars = [_bar(0, "95", "99", "91", "98"), _bar(1, "95", "99", "91", "98")]
    assert resolve_lifecycle(bars, ZONE).state is LifecycleState.VALIDATED_FRESH


def test_next_bar_touching_the_zone_mitigates() -> None:
    bars = [_bar(1, "95", "99", "91", "98"), _bar(2, "120", "125", "99", "119")]
    result = resolve_lifecycle(bars, ZONE)
    assert result.state is LifecycleState.MITIGATED
    assert result.terminal_index == 2
    assert result.terminal_reason is TerminalReason.FIRST_REACTION


# ---- how price makes contact does not matter --------------------------------


@pytest.mark.parametrize(
    ("label", "bar"),
    [
        ("wick only", _bar(2, "120", "125", "100", "119")),
        ("body penetration", _bar(2, "120", "126", "95", "97")),
        ("full traversal", _bar(2, "120", "126", "80", "82")),
        ("boundary touch exactly on top", _bar(2, "120", "125", "100", "121")),
        ("boundary touch exactly on bottom", _bar(2, "85", "90", "80", "84")),
    ],
)
def test_every_contact_shape_counts_as_one_reaction(label: str, bar: Bar) -> None:
    result = resolve_lifecycle([_bar(1, "95", "99", "91", "98"), bar], ZONE)
    assert result.state is LifecycleState.MITIGATED, label
    assert result.terminal_index == 2


def test_a_bar_clearing_the_zone_entirely_is_not_a_reaction() -> None:
    bars = [_bar(1, "95", "99", "91", "98"), _bar(2, "120", "130", "101", "129")]
    assert resolve_lifecycle(bars, ZONE).state is LifecycleState.VALIDATED_FRESH


# ---- invalidation without contact -------------------------------------------


def test_gap_clean_through_the_far_boundary_invalidates_without_touching() -> None:
    bars = [_bar(1, "95", "99", "91", "98"), _bar(2, "85", "89", "80", "82")]
    result = resolve_lifecycle(bars, ZONE)
    assert result.state is LifecycleState.INVALIDATED
    assert result.terminal_reason is TerminalReason.FAR_BOUNDARY_BREACH_WITHOUT_CONTACT


def test_a_bearish_poi_invalidates_upward_instead() -> None:
    zone = PoiInterval(Decimal("100"), Decimal("90"), 1, bullish=False)
    bars = [_bar(1, "95", "99", "91", "98"), _bar(2, "110", "115", "101", "114")]
    assert resolve_lifecycle(bars, zone).state is LifecycleState.INVALIDATED


# ---- terminal states are terminal, and identity survives them ---------------


def test_mitigation_is_not_undone_by_later_bars() -> None:
    bars = [
        _bar(1, "95", "99", "91", "98"),
        _bar(2, "120", "125", "99", "119"),
        _bar(3, "200", "210", "195", "205"),
    ]
    result = resolve_lifecycle(bars, ZONE)
    assert result.terminal_index == 2
    assert not result.display_eligible
    assert not result.downstream_eligible


def test_terminal_resolution_still_carries_geometry_and_availability() -> None:
    bars = [_bar(1, "95", "99", "91", "98"), _bar(2, "120", "125", "99", "119")]
    result = resolve_lifecycle(bars, ZONE)
    assert (result.top, result.bottom) == (ZONE.top, ZONE.bottom)
    assert result.availability_index == ZONE.availability_index


def test_only_a_fresh_poi_is_display_and_downstream_eligible() -> None:
    fresh = resolve_lifecycle([_bar(1, "95", "99", "91", "98")], ZONE)
    assert fresh.display_eligible and fresh.downstream_eligible


# ---- mutants the brief names explicitly -------------------------------------


def test_mutant_same_bar_self_mitigation_would_kill_every_poi() -> None:
    """If scanning started at the availability bar, nothing could ever be fresh."""
    availability_bar = _bar(1, "95", "99", "91", "98")
    assert intersects(availability_bar, ZONE)
    assert resolve_lifecycle([availability_bar], ZONE).state is (
        LifecycleState.VALIDATED_FRESH
    )


def test_mutant_ignoring_the_boundary_touch_would_miss_a_real_reaction() -> None:
    """Exclusive comparisons would call this untouched; inclusive ones do not."""
    grazing = _bar(2, "120", "125", "100", "121")
    assert intersects(grazing, ZONE)
    assert grazing.low == ZONE.top


# ---- qualification is a separate axis from lifecycle ------------------------


_SOURCE = _bar(0, "10", "12", "8", "9")


def test_exact_two_point_zero_ratio_qualifies() -> None:
    departure = _bar(1, "9", "13", "5", "12")
    assert (departure.high - departure.low) / (_SOURCE.high - _SOURCE.low) == Decimal(2)
    assert qualify_engulfing(_SOURCE, departure) is LifecycleState.VALIDATED_FRESH


def test_just_below_two_point_zero_stays_a_candidate() -> None:
    departure = _bar(1, "9", "12.9", "5", "12")
    assert qualify_engulfing(_SOURCE, departure) is LifecycleState.CANDIDATE


def test_just_above_two_point_zero_qualifies() -> None:
    departure = _bar(1, "9", "13.1", "5", "12")
    assert qualify_engulfing(_SOURCE, departure) is LifecycleState.VALIDATED_FRESH


def test_mutant_one_point_five_threshold_would_accept_a_rejected_pattern() -> None:
    departure = _bar(1, "9", "12.9", "5", "12")
    assert not qualify_frozen(_SOURCE, departure, Decimal("2.0"))
    assert qualify_frozen(_SOURCE, departure, Decimal("1.5"))


def test_a_zero_range_source_can_never_qualify() -> None:
    flat = _bar(0, "10", "10", "10", "10")
    with pytest.raises(ValueError, match="not a bullish engulfing shape"):
        qualify_engulfing(flat, _bar(1, "10", "13", "5", "12"))


def test_a_same_colour_pair_is_not_an_engulfing_shape_at_all() -> None:
    bullish_source = _bar(0, "8", "12", "8", "11")
    with pytest.raises(ValueError, match="not a bullish engulfing shape"):
        qualify_engulfing(bullish_source, _bar(1, "9", "13", "5", "12"))


# ---- the real FXCM H4 reference formations ----------------------------------

#: Reference A, the author's lower/earlier example. Source 2026-08-05 18:00Z,
#: departure 2026-08-05 22:00Z, captured live from FX:XAUUSD on 2026-09-10.
REF_A_SOURCE = _bar(144, "4250.18", "4268.13", "4243.08", "4247.07")
REF_A_DEPARTURE = _bar(145, "4247.07", "4302.67", "4245.48", "4286.39")

#: Reference B, the author's upper/later example. Source 2026-09-02 06:00Z,
#: departure 2026-09-02 10:00Z.
REF_B_SOURCE = _bar(261, "4319.90", "4331.58", "4304.77", "4308.47")
REF_B_DEPARTURE = _bar(262, "4308.47", "4385.47", "4301.64", "4385.25")


def test_both_references_pass_the_frozen_two_point_zero_total_range_rule() -> None:
    """The author's own 2x rule does not separate the two examples."""
    for source, departure in (
        (REF_A_SOURCE, REF_A_DEPARTURE),
        (REF_B_SOURCE, REF_B_DEPARTURE),
    ):
        ratio = (departure.high - departure.low) / (source.high - source.low)
        assert ratio >= Decimal("2.0")
        assert qualify_engulfing(source, departure) is LifecycleState.VALIDATED_FRESH


def test_body_ratio_ranks_the_references_the_wrong_way_round() -> None:
    """Switching the metric to body size makes the weaker example look stronger."""
    a = abs(REF_A_DEPARTURE.close - REF_A_DEPARTURE.open) / abs(
        REF_A_SOURCE.close - REF_A_SOURCE.open
    )
    b = abs(REF_B_DEPARTURE.close - REF_B_DEPARTURE.open) / abs(
        REF_B_SOURCE.close - REF_B_SOURCE.open
    )
    assert a > b


def test_body_engulfment_does_not_separate_the_references_either() -> None:
    assert body_engulfs(REF_A_SOURCE, REF_A_DEPARTURE)
    assert body_engulfs(REF_B_SOURCE, REF_B_DEPARTURE)


def test_full_range_engulfment_does_separate_the_references() -> None:
    assert not range_engulfs(REF_A_SOURCE, REF_A_DEPARTURE)
    assert range_engulfs(REF_B_SOURCE, REF_B_DEPARTURE)


def test_the_range_engulfment_predicate_reproduces_the_authors_split() -> None:
    assert (
        qualify_engulfing(
            REF_A_SOURCE,
            REF_A_DEPARTURE,
            predicate=qualify_with_range_engulfment,
        )
        is LifecycleState.CANDIDATE
    )
    assert (
        qualify_engulfing(
            REF_B_SOURCE,
            REF_B_DEPARTURE,
            predicate=qualify_with_range_engulfment,
        )
        is LifecycleState.VALIDATED_FRESH
    )


def test_reference_a_is_consumed_by_the_very_next_bar() -> None:
    """The bar after availability trades straight back into the zone."""
    zone = PoiInterval(REF_A_SOURCE.high, REF_A_SOURCE.low, availability_index=145)
    next_bar = _bar(146, "4286.39", "4304.06", "4246.68", "4267.21")
    result = resolve_lifecycle([REF_A_DEPARTURE, next_bar], zone)
    assert result.state is LifecycleState.MITIGATED
    assert result.terminal_index == 146


def test_reference_b_survives_the_bars_that_follow_it() -> None:
    zone = PoiInterval(REF_B_SOURCE.high, REF_B_SOURCE.low, availability_index=262)
    following = [
        REF_B_DEPARTURE,
        _bar(263, "4385.25", "4397.69", "4364.36", "4376.85"),
        _bar(264, "4376.85", "4391.47", "4369.16", "4386.52"),
        _bar(265, "4386.52", "4412.47", "4380.97", "4410.34"),
    ]
    assert resolve_lifecycle(following, zone).state is LifecycleState.VALIDATED_FRESH
