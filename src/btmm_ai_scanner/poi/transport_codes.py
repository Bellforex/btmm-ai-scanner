"""POI transport codes: the frozen RC3/RC4 space (1-32) and the RC5 extension.

Author decision, 2026-09-20.

TWO CONTRACTS, DELIBERATELY SEPARATE
------------------------------------
``FROZEN_TRANSPORT_CODES`` is the RC3/RC4 wire vocabulary. Every capture, every
aligned parity report and every frozen Pine artifact in this repository was
produced against it, so it can never be renumbered, reordered or extended in
place. It is asserted against the frozen P3 DEV Pine source, not against the
live ``PoiType`` enum, precisely so that adding a type to the enum cannot
silently rewrite history.

``RC5_TRANSPORT_CODES`` is the frozen space plus RC5's additions. The first is
``DOJI``.

THE NUMBER THAT CONFUSES PEOPLE
-------------------------------
DOJI is the **19th canonical student POI type** -- the 19th entry in the
per-type filter list a user sees. Its **transport code is 33**, not 19, because
codes 19-32 are already occupied by liquidity and period-level context records
(EQUAL_HIGHS_LIQUIDITY is 19, CURRENT_MONTH_LOW is 32). Canonical position and
wire code are different things and must not be conflated.
"""

from __future__ import annotations

from btmm_ai_scanner.poi.enums import PoiType

__all__ = [
    "CANONICAL_POI_TYPES",
    "FROZEN_TRANSPORT_CODES",
    "RC5_ONLY_TRANSPORT_CODES",
    "RC5_TRANSPORT_CODES",
    "transport_code",
]

#: RC3/RC4 wire vocabulary. FROZEN -- never renumber, never reorder, never
#: extend in place. Mirrors the ``C_POI_*`` constants of the frozen Pine builds.
FROZEN_TRANSPORT_CODES: dict[PoiType, int] = {
    PoiType.BUY_ORDER_BLOCK: 1,
    PoiType.SELL_ORDER_BLOCK: 2,
    PoiType.BUY_FAIR_VALUE_GAP: 3,
    PoiType.SELL_FAIR_VALUE_GAP: 4,
    PoiType.BUY_TO_SELL_CANDLE: 5,
    PoiType.SELL_TO_BUY_CANDLE: 6,
    PoiType.BASE_RALLY: 7,
    PoiType.BASE_DROP: 8,
    PoiType.BULLISH_PRESSURE_WICK: 9,
    PoiType.BEARISH_PRESSURE_WICK: 10,
    PoiType.BULLISH_ENGULFING: 11,
    PoiType.BEARISH_ENGULFING: 12,
    PoiType.HAMMER: 13,
    PoiType.SHOOTING_STAR: 14,
    PoiType.MORNING_STAR: 15,
    PoiType.EVENING_STAR: 16,
    PoiType.SUPPORT_ZONE: 17,
    PoiType.RESISTANCE_ZONE: 18,
    PoiType.EQUAL_HIGHS_LIQUIDITY: 19,
    PoiType.EQUAL_LOWS_LIQUIDITY: 20,
    PoiType.CURRENT_DAY_HIGH: 21,
    PoiType.CURRENT_DAY_LOW: 22,
    PoiType.CURRENT_WEEK_HIGH: 23,
    PoiType.CURRENT_WEEK_LOW: 24,
    PoiType.CURRENT_MONTH_HIGH: 25,
    PoiType.CURRENT_MONTH_LOW: 26,
    PoiType.PREVIOUS_DAY_HIGH: 27,
    PoiType.PREVIOUS_DAY_LOW: 28,
    PoiType.PREVIOUS_WEEK_HIGH: 29,
    PoiType.PREVIOUS_WEEK_LOW: 30,
    PoiType.PREVIOUS_MONTH_HIGH: 31,
    PoiType.PREVIOUS_MONTH_LOW: 32,
}

#: RC5 additions. Codes start after the frozen space.
RC5_ONLY_TRANSPORT_CODES: dict[PoiType, int] = {
    PoiType.DOJI: 33,
}

RC5_TRANSPORT_CODES: dict[PoiType, int] = {
    **FROZEN_TRANSPORT_CODES,
    **RC5_ONLY_TRANSPORT_CODES,
}

#: The canonical, per-type-switchable student POI types, in filter order.
#: 18 in RC3/RC4; DOJI makes 19 in RC5.
CANONICAL_POI_TYPES: tuple[PoiType, ...] = (
    PoiType.BUY_ORDER_BLOCK,
    PoiType.SELL_ORDER_BLOCK,
    PoiType.BUY_FAIR_VALUE_GAP,
    PoiType.SELL_FAIR_VALUE_GAP,
    PoiType.BUY_TO_SELL_CANDLE,
    PoiType.SELL_TO_BUY_CANDLE,
    PoiType.BASE_RALLY,
    PoiType.BASE_DROP,
    PoiType.BULLISH_PRESSURE_WICK,
    PoiType.BEARISH_PRESSURE_WICK,
    PoiType.BULLISH_ENGULFING,
    PoiType.BEARISH_ENGULFING,
    PoiType.HAMMER,
    PoiType.SHOOTING_STAR,
    PoiType.MORNING_STAR,
    PoiType.EVENING_STAR,
    PoiType.SUPPORT_ZONE,
    PoiType.RESISTANCE_ZONE,
    PoiType.DOJI,
)


def transport_code(poi_type: PoiType) -> int:
    """The RC5 wire code for ``poi_type``."""
    return RC5_TRANSPORT_CODES[poi_type]
