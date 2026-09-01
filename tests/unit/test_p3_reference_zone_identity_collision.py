"""Two reference zones confirmed on the same candle must stay distinct.

Pine's identity contract, frozen at P3 closure, is
`f_poiSameIdentity(typeCode, srcFirst, srcCount, srcLast, lowTicks, highTicks)`
-- type, the contiguous source-candle run, AND the tick-normalised bounds. Its
own comment says why the bounds are in there:

    Reference zones are projections of P1 records and have NO source candles,
    so their (first, count, last) triple degenerates to the confirmation time.
    Two support zones confirmed by the same candle but built from different
    origin swings would then collide. Including the bounds separates them.

The test-side model omitted the bounds, so its dedup collapsed exactly that case
and the replay silently held one POI fewer than Pine.

This was not hypothetical and it was not visible on M15. It surfaced on the P4
M5 atomic capture: Pine reported 938 BTMM setups, the replay 937, and all 937
shared setups were byte-identical across every canonical field. The single extra
was a SUPPORT_ZONE at bounds (443562, 443621) confirmed at 1788161400000, which
production's own detector emits 205 times -- and which the model's dedup dropped
because another support zone, bounds (443418, 443483), was confirmed on the same
candle and claimed the identity first.

Ownership matters here: production is right, the Pine port is right, and the
harness was wrong. These tests pin the model's identity to the Pine contract so
the two cannot drift apart again.
"""

from __future__ import annotations

from decimal import Decimal

from tests.parity_support import p3_pine_model as M


def _zone_poi(
    poi_type: int, bottom: str, top: str, confirm_ms: int
) -> M.ModelPoi:
    """A reference-zone POI exactly as `project_reference_zones` builds one:
    no source candles, so all three time fields are the confirmation time."""
    return M.ModelPoi(
        poi_type,
        M.DIR_BULLISH if poi_type == M.TYPE_SUPPORT_ZONE else M.DIR_BEARISH,
        Decimal(top),
        Decimal(bottom),
        M.TIER_NA,
        confirm_ms,
        1,
        confirm_ms,
        confirm_ms,
        confirm_ms,
    )


#: The real pair, from the M5 atomic capture at anchor 1788272400000.
_CONFIRM = 1788161400000
_KEPT = ("4434.18", "4434.83")
_DROPPED = ("4435.62", "4436.21")


def test_same_candle_different_bounds_are_different_identities() -> None:
    """The regression. Before the fix these two collided and the second was
    silently discarded by every dedup keyed on `identity`."""
    a = _zone_poi(M.TYPE_SUPPORT_ZONE, _KEPT[0], _KEPT[1], _CONFIRM)
    b = _zone_poi(M.TYPE_SUPPORT_ZONE, _DROPPED[0], _DROPPED[1], _CONFIRM)
    assert a.identity != b.identity


def test_a_dedup_keyed_on_identity_keeps_both() -> None:
    """State the consequence directly, in the shape the replay actually uses."""
    a = _zone_poi(M.TYPE_SUPPORT_ZONE, _KEPT[0], _KEPT[1], _CONFIRM)
    b = _zone_poi(M.TYPE_SUPPORT_ZONE, _DROPPED[0], _DROPPED[1], _CONFIRM)

    seen: set[tuple[int, ...]] = set()
    emitted: list[M.ModelPoi] = []
    for poi in (a, b, a, b):  # the projection re-emits each zone every bar
        if poi.identity not in seen:
            seen.add(poi.identity)
            emitted.append(poi)
    assert len(emitted) == 2


def test_identity_carries_the_tick_normalised_bounds() -> None:
    """Mirrors `f_poiSameIdentity`, which compares `f_poiTicks(bound)` rather
    than the raw float, so the model merges and splits where Pine does."""
    poi = _zone_poi(M.TYPE_SUPPORT_ZONE, _DROPPED[0], _DROPPED[1], _CONFIRM)
    assert poi.identity == (
        M.TYPE_SUPPORT_ZONE,
        _CONFIRM,
        1,
        _CONFIRM,
        443562,
        443621,
    )


def test_bounds_are_compared_in_ticks_not_raw_decimals() -> None:
    """Two zones whose bounds differ by less than a tick are the SAME zone to
    Pine, because it compares rounded ticks. Comparing raw Decimals would split
    them and reintroduce the divergence from the other direction."""
    a = _zone_poi(M.TYPE_SUPPORT_ZONE, "4435.620", "4436.210", _CONFIRM)
    b = _zone_poi(M.TYPE_SUPPORT_ZONE, "4435.6201", "4436.2099", _CONFIRM)
    assert a.zone_bottom != b.zone_bottom
    assert a.identity == b.identity


def test_ties_round_away_from_zero_like_pine() -> None:
    """`f_poiTicks` is `math.round`, which is ties-away-from-zero; Python's
    built-in `round` is banker's and would disagree at an exact half tick."""
    poi = _zone_poi(M.TYPE_SUPPORT_ZONE, "4435.625", "4436.215", _CONFIRM)
    assert poi.identity[4] == 443563  # not 443562
    assert poi.identity[5] == 443622  # not 443621


def test_candle_derived_families_are_unaffected() -> None:
    """For every candle family the bounds are a deterministic function of the
    source candles already in the identity, so adding them refines and never
    splits -- which is why this change cannot disturb the closed M15 result."""
    a = M.ModelPoi(
        M.TYPE_BUY_ORDER_BLOCK,
        M.DIR_BULLISH,
        Decimal("100.5"),
        Decimal("100.0"),
        M.TIER_NA,
        1000,
        2,
        2000,
        1000,
        2000,
    )
    b = M.ModelPoi(
        M.TYPE_BUY_ORDER_BLOCK,
        M.DIR_BULLISH,
        Decimal("100.5"),
        Decimal("100.0"),
        M.TIER_NA,
        1000,
        2,
        2000,
        1000,
        2000,
    )
    assert a.identity == b.identity
    assert a.identity[:4] == (M.TYPE_BUY_ORDER_BLOCK, 1000, 2, 2000)


def test_the_model_tick_matches_the_campaign_configuration() -> None:
    """The model has no configuration object, so the tick it normalises with is
    a module constant. Pin it to the value every campaign actually runs, so a
    change of instrument cannot silently desynchronise the model from Pine."""
    from btmm_ai_scanner.poi.configuration import PoiConfiguration

    assert M.IDENTITY_MINTICK == PoiConfiguration(
        minimum_price_tick=Decimal("0.01")
    ).minimum_price_tick
