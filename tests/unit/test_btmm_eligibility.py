from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    NOT_APPLICABLE_LIFECYCLE_POI_TYPES,
    PERIOD_LEVEL_POI_TYPES,
    PoiType,
)
from btmm_ai_scanner.poi.transport_codes import (
    FROZEN_TRANSPORT_CODES,
    RC5_ONLY_TRANSPORT_CODES,
)

_CONTEXT_ONLY_TYPES = frozenset(
    {PoiType.EQUAL_HIGHS_LIQUIDITY, PoiType.EQUAL_LOWS_LIQUIDITY}
)

_DEFERRED_TYPES_NEVER_APPEAR = frozenset(
    {"BULLISH_TRENDLINE", "BEARISH_TRENDLINE", "SWING_HIGH", "SWING_LOW"}
)


def test_exact_18_frozen_btmm_eligible_poi_types() -> None:
    """The RC3/RC4 lifecycle-eligible family is exactly 18. RC5 adds DOJI; the
    frozen 18 must stay exactly what they were."""
    frozen_eligible = LIFECYCLE_ELIGIBLE_POI_TYPES - set(RC5_ONLY_TRANSPORT_CODES)
    assert len(frozen_eligible) == 18
    assert all(isinstance(member, PoiType) for member in LIFECYCLE_ELIGIBLE_POI_TYPES)


def test_rc5_adds_doji_to_the_lifecycle_eligible_family() -> None:
    assert PoiType.DOJI in LIFECYCLE_ELIGIBLE_POI_TYPES
    assert len(LIFECYCLE_ELIGIBLE_POI_TYPES) == 19


def test_equal_highs_and_lows_classified_context_only() -> None:
    assert _CONTEXT_ONLY_TYPES.isdisjoint(LIFECYCLE_ELIGIBLE_POI_TYPES)
    assert _CONTEXT_ONLY_TYPES.issubset(NOT_APPLICABLE_LIFECYCLE_POI_TYPES)
    assert len(_CONTEXT_ONLY_TYPES) == 2


def test_12_period_level_types_classified_not_applicable() -> None:
    assert len(PERIOD_LEVEL_POI_TYPES) == 12
    assert PERIOD_LEVEL_POI_TYPES.issubset(NOT_APPLICABLE_LIFECYCLE_POI_TYPES)
    assert PERIOD_LEVEL_POI_TYPES.isdisjoint(LIFECYCLE_ELIGIBLE_POI_TYPES)


def test_deferred_poi_absent_specifications_never_appear() -> None:
    all_type_names = {member.value for member in PoiType}
    assert _DEFERRED_TYPES_NEVER_APPEAR.isdisjoint(all_type_names)


def test_eligibility_set_matches_poi_lifecycle_eligible_set_by_cross_reference() -> (
    None
):
    total_classified = LIFECYCLE_ELIGIBLE_POI_TYPES | NOT_APPLICABLE_LIFECYCLE_POI_TYPES
    assert total_classified == frozenset(PoiType), "every PoiType must be classified"
    # frozen space stays 32; RC5 adds exactly its own types on top
    frozen = set(FROZEN_TRANSPORT_CODES)
    assert len(frozen) == 32
    assert len(total_classified) == 32 + len(RC5_ONLY_TRANSPORT_CODES)
    assert (
        LIFECYCLE_ELIGIBLE_POI_TYPES & NOT_APPLICABLE_LIFECYCLE_POI_TYPES
    ) == frozenset()
