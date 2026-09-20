"""RC5 transport contract: the frozen 1-32 space and the DOJI extension.

The point of this file is that adding a POI type can never silently rewrite the
wire vocabulary every RC3/RC4 capture and parity report was produced against.
"""

from __future__ import annotations

from btmm_ai_scanner.poi.enums import (
    LIFECYCLE_ELIGIBLE_POI_TYPES,
    NOT_APPLICABLE_LIFECYCLE_POI_TYPES,
    PoiType,
)
from btmm_ai_scanner.poi.transport_codes import (
    CANONICAL_POI_TYPES,
    FROZEN_TRANSPORT_CODES,
    RC5_ONLY_TRANSPORT_CODES,
    RC5_TRANSPORT_CODES,
    transport_code,
)

#: The RC3/RC4 wire vocabulary, written out literally. If a future change
#: renumbers anything, this fixture fails rather than the history silently
#: becoming unreadable.
EXPECTED_FROZEN: dict[str, int] = {
    "BUY_ORDER_BLOCK": 1,
    "SELL_ORDER_BLOCK": 2,
    "BUY_FAIR_VALUE_GAP": 3,
    "SELL_FAIR_VALUE_GAP": 4,
    "BUY_TO_SELL_CANDLE": 5,
    "SELL_TO_BUY_CANDLE": 6,
    "BASE_RALLY": 7,
    "BASE_DROP": 8,
    "BULLISH_PRESSURE_WICK": 9,
    "BEARISH_PRESSURE_WICK": 10,
    "BULLISH_ENGULFING": 11,
    "BEARISH_ENGULFING": 12,
    "HAMMER": 13,
    "SHOOTING_STAR": 14,
    "MORNING_STAR": 15,
    "EVENING_STAR": 16,
    "SUPPORT_ZONE": 17,
    "RESISTANCE_ZONE": 18,
    "EQUAL_HIGHS_LIQUIDITY": 19,
    "EQUAL_LOWS_LIQUIDITY": 20,
    "CURRENT_DAY_HIGH": 21,
    "CURRENT_DAY_LOW": 22,
    "CURRENT_WEEK_HIGH": 23,
    "CURRENT_WEEK_LOW": 24,
    "CURRENT_MONTH_HIGH": 25,
    "CURRENT_MONTH_LOW": 26,
    "PREVIOUS_DAY_HIGH": 27,
    "PREVIOUS_DAY_LOW": 28,
    "PREVIOUS_WEEK_HIGH": 29,
    "PREVIOUS_WEEK_LOW": 30,
    "PREVIOUS_MONTH_HIGH": 31,
    "PREVIOUS_MONTH_LOW": 32,
}


# --------------------------------------------------------------------------
# legacy frozen contract
# --------------------------------------------------------------------------


def test_frozen_space_is_exactly_the_rc3_rc4_vocabulary() -> None:
    assert {t.value: c for t, c in FROZEN_TRANSPORT_CODES.items()} == EXPECTED_FROZEN


def test_frozen_codes_are_1_to_32_contiguous_and_distinct() -> None:
    codes = sorted(FROZEN_TRANSPORT_CODES.values())
    assert codes == list(range(1, 33))
    assert len(set(codes)) == 32


def test_no_rc5_type_is_inside_the_frozen_space() -> None:
    assert set(FROZEN_TRANSPORT_CODES).isdisjoint(RC5_ONLY_TRANSPORT_CODES)


# --------------------------------------------------------------------------
# RC5 extension contract
# --------------------------------------------------------------------------


def test_doji_exists_and_its_transport_code_is_33() -> None:
    assert PoiType.DOJI in RC5_ONLY_TRANSPORT_CODES
    assert transport_code(PoiType.DOJI) == 33


def test_rc5_codes_start_after_the_frozen_space_without_collision() -> None:
    assert min(RC5_ONLY_TRANSPORT_CODES.values()) > max(FROZEN_TRANSPORT_CODES.values())
    assert len(set(RC5_TRANSPORT_CODES.values())) == len(RC5_TRANSPORT_CODES)


def test_rc5_map_extends_the_frozen_map_without_altering_it() -> None:
    for poi_type, code in FROZEN_TRANSPORT_CODES.items():
        assert RC5_TRANSPORT_CODES[poi_type] == code


def test_every_poi_type_has_a_transport_code() -> None:
    assert set(RC5_TRANSPORT_CODES) == frozenset(PoiType)


# --------------------------------------------------------------------------
# canonical position is NOT the wire code
# --------------------------------------------------------------------------


def test_doji_is_canonical_type_19_but_transport_code_33() -> None:
    assert len(CANONICAL_POI_TYPES) == 19
    assert CANONICAL_POI_TYPES[18] is PoiType.DOJI  # 19th, 0-indexed
    assert transport_code(PoiType.DOJI) == 33  # NOT 19
    # code 19 belongs to a context record and must stay there
    assert transport_code(PoiType.EQUAL_HIGHS_LIQUIDITY) == 19


def test_the_first_18_canonical_types_keep_codes_1_to_18() -> None:
    assert [transport_code(t) for t in CANONICAL_POI_TYPES[:18]] == list(range(1, 19))


def test_canonical_types_are_all_lifecycle_eligible() -> None:
    assert set(CANONICAL_POI_TYPES) == set(LIFECYCLE_ELIGIBLE_POI_TYPES)
    assert set(CANONICAL_POI_TYPES).isdisjoint(NOT_APPLICABLE_LIFECYCLE_POI_TYPES)
