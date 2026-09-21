"""RC5 deduplication: one physical liquidity action, one user-facing event.

Every rule here was measured on real hosts before it was written. The merge
rule is SHARED LEVEL SOURCE **and** exactly equal price -- both, never either
alone -- and there is no price tolerance anywhere in the module.

The cases that must stay DISTINCT are as important as the ones that merge, and
each is taken from something the collision matrix actually found:

* different prices on one candle (13-22 groups per host);
* two trendlines sharing one anchor, projected to 4645.215 vs 4645.314 on M15;
* same price with no semantic relation -- which never occurred once RC5's own
  level identity was fixed, and must NOT be silently merged if it reappears.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.framework.model import LiquiditySide
from btmm_ai_scanner.poi.rc5_host_identity import Rc5HostIdentity, host_identity_of
from btmm_ai_scanner.poi.rc5_liquidity import SweepReferenceKind
from btmm_ai_scanner.poi.rc5_sweeps import (
    OWNER_PRIORITY,
    QualifiedSweepCandidate,
    deduplicate_sweep_candidates,
)

_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)
_M15 = host_identity_of(Timeframe.M15)
_M45 = Rc5HostIdentity("M45", 45, Timeframe.M15)


def _candidate(
    kind: SweepReferenceKind,
    reference_id: tuple,
    price: str,
    sources: set,
    *,
    host: Rc5HostIdentity = _M15,
    side: LiquiditySide = LiquiditySide.BUY_SIDE,
    when: datetime = _NOW,
) -> QualifiedSweepCandidate:
    return QualifiedSweepCandidate(
        host=host,
        event_time_utc=when,
        side=side,
        kind=kind,
        reference_id=reference_id,
        price=Decimal(price),
        raw_sweep_type="WICK_SWEEP",
        raw_level_id=f"X{reference_id[0]}",
        level_sources=frozenset(sources),
    )


# ---------------------------------------------------------------------------
# what MAY collapse -- each backed by an existing model relationship
# ---------------------------------------------------------------------------


def test_a_swing_and_the_equal_pool_containing_it_are_one_event() -> None:
    """EqualLevelCluster.component_swing_record_ids names the swing, so the
    pool and the swing are the same level described twice."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-1",),
                "4680.89",
                {"swing-1", "candle-9"},
            ),
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-1",),
                "4680.89",
                {"cluster-1", "swing-1"},
            ),
        ]
    )
    assert len(events) == 1
    assert events[0].primary_kind is SweepReferenceKind.EQUAL_HIGH_LOW
    assert events[0].corroborating == (
        (SweepReferenceKind.STRUCTURAL_SWING, ("swing-1",)),
    )


def test_a_swing_and_the_range_boundary_it_sources_are_one_event() -> None:
    """TradingRange.upper_source / lower_source IS a broken swing id."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-7",),
                "4616.59",
                {"swing-7"},
            ),
            _candidate(
                SweepReferenceKind.RANGE_BOUNDARY,
                ("R-1", "RANGE_LOW"),
                "4616.59",
                {"R-1", "swing-7"},
            ),
        ]
    )
    assert len(events) == 1
    assert events[0].primary_kind is SweepReferenceKind.RANGE_BOUNDARY


def test_a_swing_and_a_reversal_poi_on_its_pivot_candle_are_one_event() -> None:
    """A shooting star's far edge IS the swing high it formed -- the POI's
    source candle is the swing's pivot candle."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-3",),
                "4400.19",
                {"swing-3", "candle-42"},
            ),
            _candidate(
                SweepReferenceKind.POI_BOUNDARY,
                ("SHOOTING_STAR", "candle-42"),
                "4400.19",
                {"candle-42"},
            ),
        ]
    )
    assert len(events) == 1
    assert events[0].primary_kind is SweepReferenceKind.POI_BOUNDARY
    assert len(events[0].corroborating) == 1


def test_a_transitive_group_collapses_to_one_event() -> None:
    """A swing links to the pool containing it AND to the range it sources;
    the pool and the range share nothing directly, yet all three are one
    level. Union-find is why this works."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-9",),
                "100.00",
                {"cluster-9", "swing-5"},
            ),
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-5",),
                "100.00",
                {"swing-5"},
            ),
            _candidate(
                SweepReferenceKind.RANGE_BOUNDARY,
                ("R-2", "RANGE_HIGH"),
                "100.00",
                {"R-2", "swing-5"},
            ),
        ]
    )
    assert len(events) == 1
    assert len(events[0].corroborating) == 2


# ---------------------------------------------------------------------------
# what must stay DISTINCT
# ---------------------------------------------------------------------------


def test_different_prices_on_one_candle_stay_separate() -> None:
    """One candle can legitimately sweep several BSL levels."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-a",),
                "4380.77",
                {"swing-a"},
            ),
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-b",),
                "4388.26",
                {"swing-b"},
            ),
        ]
    )
    assert len(events) == 2


def test_two_trendlines_sharing_one_anchor_stay_separate() -> None:
    """Measured on M15: 4645.215135... and 4645.313988... share an anchor swing
    and are different levels. A trendline contributes only ITSELF as a level
    source, which is what keeps them apart."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.TRENDLINE,
                ("anchor-1", "anchor-2"),
                "4645.215135135135135135135135",
                {"line-a"},
            ),
            _candidate(
                SweepReferenceKind.TRENDLINE,
                ("anchor-1", "anchor-3"),
                "4645.313988439306358381502890",
                {"line-b"},
            ),
        ]
    )
    assert len(events) == 2


def test_same_price_with_no_semantic_relation_is_not_merged() -> None:
    """The class that must never be papered over. It occurred zero times on
    all five hosts once RC5's own level identity was fixed -- and the one time
    it appeared it was a defect, not a missing relationship. If it reappears it
    must surface as two events, not be silently joined."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-x",),
                "4407.95",
                {"swing-x"},
            ),
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-y",),
                "4407.95",
                {"cluster-y"},
            ),
        ]
    )
    assert len(events) == 2


def test_opposite_sides_never_merge() -> None:
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("s",),
                "100.00",
                {"shared"},
                side=LiquiditySide.BUY_SIDE,
            ),
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("c",),
                "100.00",
                {"shared"},
                side=LiquiditySide.SELL_SIDE,
            ),
        ]
    )
    assert len(events) == 2


def test_different_hosts_never_merge() -> None:
    """M45 is not M15 even sharing a carrier enum, the same instant and the
    same price."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("s",),
                "100.00",
                {"shared"},
                host=_M15,
            ),
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("s",),
                "100.00",
                {"shared"},
                host=_M45,
            ),
        ]
    )
    assert len(events) == 2
    assert {e.host.label for e in events} == {"M15", "M45"}
    assert events[0].event_id != events[1].event_id


def test_different_times_never_merge() -> None:
    from datetime import timedelta

    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING, ("s",), "100.00", {"shared"}
            ),
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("s",),
                "100.00",
                {"shared"},
                when=_NOW + timedelta(minutes=15),
            ),
        ]
    )
    assert len(events) == 2


# ---------------------------------------------------------------------------
# determinism and labelling
# ---------------------------------------------------------------------------


def test_the_winner_does_not_depend_on_input_order() -> None:
    members = [
        _candidate(
            SweepReferenceKind.STRUCTURAL_SWING,
            ("swing-1",),
            "100.00",
            {"swing-1"},
        ),
        _candidate(
            SweepReferenceKind.EQUAL_HIGH_LOW,
            ("cluster-1",),
            "100.00",
            {"cluster-1", "swing-1"},
        ),
        _candidate(
            SweepReferenceKind.TRENDLINE,
            ("a", "b"),
            "100.00",
            {"swing-1"},
        ),
    ]
    forward = deduplicate_sweep_candidates(members)
    backward = deduplicate_sweep_candidates(list(reversed(members)))
    assert len(forward) == len(backward) == 1
    assert forward[0].event_id == backward[0].event_id
    assert forward[0].corroborating == backward[0].corroborating


def test_priority_order_is_the_documented_hierarchy() -> None:
    assert (
        OWNER_PRIORITY[SweepReferenceKind.POI_BOUNDARY]
        < (OWNER_PRIORITY[SweepReferenceKind.EQUAL_HIGH_LOW])
    )
    assert (
        OWNER_PRIORITY[SweepReferenceKind.EQUAL_HIGH_LOW]
        < (OWNER_PRIORITY[SweepReferenceKind.RANGE_BOUNDARY])
    )
    assert (
        OWNER_PRIORITY[SweepReferenceKind.STRUCTURAL_SWING]
        < (OWNER_PRIORITY[SweepReferenceKind.TRENDLINE])
    )
    assert set(OWNER_PRIORITY) == set(SweepReferenceKind)


@pytest.mark.parametrize(
    ("side", "label"),
    [(LiquiditySide.BUY_SIDE, "BSL"), (LiquiditySide.SELL_SIDE, "SSL")],
)
def test_every_event_is_bsl_or_ssl(side, label) -> None:
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING, ("s",), "1.00", {"s"}, side=side
            )
        ]
    )
    assert events[0].label == label


def test_no_price_tolerance_exists_in_the_module() -> None:
    """Guard against an epsilon creeping in later. Prices that differ by one
    tick are different levels, full stop."""
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING, ("s",), "100.00", {"shared"}
            ),
            _candidate(SweepReferenceKind.EQUAL_HIGH_LOW, ("c",), "100.01", {"shared"}),
        ]
    )
    assert len(events) == 2, "a price tolerance has been introduced"


def test_the_same_reference_arriving_twice_is_not_corroboration() -> None:
    """An equal-level pool reaches dedup TWICE -- once as the framework's "E"
    level and once as a reference-zone POI carrying the SAME cluster id.
    Measured on M15: primary and "corroborating" held identical ids.

    Listing it would claim two independent references behind the event when
    there is one, which matters because corroboration is the forensic answer
    to "what else confirmed this?".
    """
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-1",),
                "4532.94",
                {"cluster-1", "swing-2"},
            ),
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-1",),
                "4532.94",
                {"cluster-1", "swing-2"},
            ),
        ]
    )
    assert len(events) == 1
    assert events[0].corroborating == ()


def test_genuine_corroboration_is_still_reported() -> None:
    events = deduplicate_sweep_candidates(
        [
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-1",),
                "4680.89",
                {"cluster-1", "swing-1"},
            ),
            _candidate(
                SweepReferenceKind.EQUAL_HIGH_LOW,
                ("cluster-1",),
                "4680.89",
                {"cluster-1", "swing-1"},
            ),
            _candidate(
                SweepReferenceKind.STRUCTURAL_SWING,
                ("swing-1",),
                "4680.89",
                {"swing-1"},
            ),
        ]
    )
    assert len(events) == 1
    assert events[0].corroborating == (
        (SweepReferenceKind.STRUCTURAL_SWING, ("swing-1",)),
    )
