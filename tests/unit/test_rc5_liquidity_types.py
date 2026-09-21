"""RC5 qualified-liquidity reference types.

These pin the bridge back to the frozen framework contract. The framework
assigns ``level_id`` prefixes and ``LiquiditySide`` already; RC5 must READ both
rather than re-derive them, or the two layers can disagree about what was swept
and which side it rested on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.framework.model import LiquidityKind, LiquiditySide
from btmm_ai_scanner.poi.rc5_host_identity import Rc5HostIdentity, host_identity_of
from btmm_ai_scanner.poi.rc5_liquidity import (
    KIND_TO_REFERENCE,
    QualifiedLiquidityReference,
    SweepReferenceKind,
    reference_kind_of_level_id,
    side_of_reference,
)

_NOW = datetime(2026, 9, 21, 12, 0, tzinfo=UTC)


def _reference(**overrides) -> QualifiedLiquidityReference:
    base = {
        "kind": SweepReferenceKind.STRUCTURAL_SWING,
        "side": LiquiditySide.BUY_SIDE,
        "price": Decimal("4500.00"),
        "source_identity": ("swing-1",),
        "level_id": "Sswing-1",
        "host": host_identity_of(Timeframe.M15),
        "known_from_utc": _NOW,
        "reason": "LEG_ORIGIN",
    }
    return QualifiedLiquidityReference(**{**base, **overrides})


# ---------------------------------------------------------------------------
# every LiquidityKind maps -- no silent drops
# ---------------------------------------------------------------------------


def test_every_liquidity_kind_has_a_reference_kind() -> None:
    """A new LiquidityKind must not fall out of qualification unnoticed."""
    assert set(KIND_TO_REFERENCE) == set(LiquidityKind)


def test_reference_kinds_cover_the_two_rc5_additions() -> None:
    mapped = set(KIND_TO_REFERENCE.values())
    unmapped = set(SweepReferenceKind) - mapped
    assert unmapped == {
        SweepReferenceKind.POI_BOUNDARY,
        SweepReferenceKind.SUPPORT_RESISTANCE,
    }


# ---------------------------------------------------------------------------
# level_id -> reference kind
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("level_id", "expected"),
    [
        ("S0198f2c1-0000-7000-8000-000000000001", SweepReferenceKind.STRUCTURAL_SWING),
        ("E0198f2c1-0000-7000-8000-000000000002", SweepReferenceKind.EQUAL_HIGH_LOW),
        ("T0198f2c1-0000-7000-8000-000000000003", SweepReferenceKind.TRENDLINE),
        ("R2026-09-21T12:00:00+00:00:RANGE_HIGH", SweepReferenceKind.RANGE_BOUNDARY),
        ("R2026-09-21T12:00:00+00:00:RANGE_LOW", SweepReferenceKind.RANGE_BOUNDARY),
    ],
    ids=["swing", "equal", "trendline", "range-high", "range-low"],
)
def test_level_ids_map_to_their_reference_kind(
    level_id: str, expected: SweepReferenceKind
) -> None:
    assert reference_kind_of_level_id(level_id) is expected


def test_a_range_boundary_is_not_mistaken_for_a_swing() -> None:
    """The trap: ``range_id`` is ``R<isoformat>``, so a range level_id ALSO
    starts with a letter prefix. The ':' test must win, or every range
    boundary is silently classified as a structural swing."""
    range_level = "R2026-09-21T12:00:00+00:00:RANGE_HIGH"
    assert range_level.startswith("R")
    assert reference_kind_of_level_id(range_level) is (
        SweepReferenceKind.RANGE_BOUNDARY
    )


def test_an_unknown_level_id_is_refused() -> None:
    with pytest.raises(ValueError, match="unrecognised framework level_id"):
        reference_kind_of_level_id("Z-nope")


# ---------------------------------------------------------------------------
# BSL / SSL
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "side"),
    [
        (LiquidityKind.SWING_HIGH, LiquiditySide.BUY_SIDE),
        (LiquidityKind.EQUAL_HIGHS, LiquiditySide.BUY_SIDE),
        (LiquidityKind.RANGE_HIGH, LiquiditySide.BUY_SIDE),
        (LiquidityKind.SWING_LOW, LiquiditySide.SELL_SIDE),
        (LiquidityKind.EQUAL_LOWS, LiquiditySide.SELL_SIDE),
        (LiquidityKind.RANGE_LOW, LiquiditySide.SELL_SIDE),
    ],
)
def test_highs_are_buy_side_and_lows_are_sell_side(
    kind: LiquidityKind, side: LiquiditySide
) -> None:
    assert side_of_reference(kind) is side


def test_a_trendline_has_no_side_from_its_kind_alone() -> None:
    """Its side follows from its slope, which the framework already decided
    per level. Answering here would create a second, disagreeing source."""
    with pytest.raises(ValueError, match="no side that follows from its kind"):
        side_of_reference(LiquidityKind.TRENDLINE)


def test_the_student_facing_label_is_bsl_or_ssl() -> None:
    assert _reference(side=LiquiditySide.BUY_SIDE).label == "BSL"
    assert _reference(side=LiquiditySide.SELL_SIDE).label == "SSL"
    assert _reference(side=LiquiditySide.BUY_SIDE).is_buy_side


# ---------------------------------------------------------------------------
# host-local identity
# ---------------------------------------------------------------------------


def test_references_on_hosts_sharing_a_carrier_do_not_collide() -> None:
    """The M45/M15 trap, at the level that actually stores things."""
    m15 = _reference(host=host_identity_of(Timeframe.M15))
    m45 = _reference(host=Rc5HostIdentity("M45", 45, Timeframe.M15))
    assert m15.host.carrier is m45.host.carrier
    assert m15.key != m45.key
    assert "M45" in m45.key


def test_the_key_uses_stable_identity_not_a_runtime_index() -> None:
    reference = _reference(source_identity=("swing-1",))
    assert "swing-1" in reference.key
    assert all(not isinstance(part, int) or part in (15,) for part in reference.key)


def test_two_references_to_the_same_source_share_a_key() -> None:
    """What deduplication relies on: identity, never price proximity."""
    first = _reference(price=Decimal("4500.00"))
    second = _reference(price=Decimal("4500.25"))
    assert first.key == second.key
    assert first.price != second.price


# ---------------------------------------------------------------------------
# POI boundaries -- the far edge, derived not assumed
# ---------------------------------------------------------------------------


def test_a_bullish_poi_offers_its_bottom_as_sell_side_liquidity() -> None:
    from btmm_ai_scanner.poi.enums import PoiDirection
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_liquidity

    boundary = poi_boundary_liquidity(
        PoiDirection.BULLISH, Decimal("102.00"), Decimal("100.00")
    )
    assert boundary.price == Decimal("100.00")
    assert boundary.edge == "zone_bottom"
    assert boundary.side is LiquiditySide.SELL_SIDE
    assert boundary.label == "SSL"


def test_a_bearish_poi_offers_its_top_as_buy_side_liquidity() -> None:
    from btmm_ai_scanner.poi.enums import PoiDirection
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_liquidity

    boundary = poi_boundary_liquidity(
        PoiDirection.BEARISH, Decimal("102.00"), Decimal("100.00")
    )
    assert boundary.price == Decimal("102.00")
    assert boundary.edge == "zone_top"
    assert boundary.side is LiquiditySide.BUY_SIDE
    assert boundary.label == "BSL"


def test_the_far_edge_is_the_lifecycle_invalidation_boundary() -> None:
    """The derivation, asserted against the frozen breach rule rather than
    restated. lifecycle._is_breach uses close < zone_bottom for BULLISH and
    close > zone_top for BEARISH, so the edge this function returns must be
    the edge that actually breaches."""
    from btmm_ai_scanner.poi.enums import PoiDirection
    from btmm_ai_scanner.poi.lifecycle import _is_breach
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_liquidity

    top, bottom = Decimal("102.00"), Decimal("100.00")
    zero = Decimal("0")
    for direction in (PoiDirection.BULLISH, PoiDirection.BEARISH):
        boundary = poi_boundary_liquidity(direction, top, bottom)
        beyond = (
            boundary.price - Decimal("1")
            if direction is PoiDirection.BULLISH
            else boundary.price + Decimal("1")
        )
        assert _is_breach(_Candle(beyond), direction, top, bottom, zero)
        # and the PROXIMAL edge does not breach: being used is not failing
        inside = (
            bottom + Decimal("0.5")
            if direction is PoiDirection.BULLISH
            else top - Decimal("0.5")
        )
        assert not _is_breach(_Candle(inside), direction, top, bottom, zero)


class _Candle:
    def __init__(self, close: Decimal) -> None:
        self.close = close


def test_an_unknown_direction_is_refused() -> None:
    from btmm_ai_scanner.poi.rc5_liquidity import poi_boundary_liquidity

    with pytest.raises(ValueError, match="no far edge"):
        poi_boundary_liquidity("SIDEWAYS", Decimal("2"), Decimal("1"))
