"""A6-B1-B2: exact ATR-invariant POI breach-threshold wake index.

Given a set of registered SCANNING POIs, discovers exactly which of them a new
candle's close breaches (``_is_breach``) without checking all P POIs. The breach
threshold ``max(2*min_tick, min(am*ATR, hm*zone_height))`` moves with the
per-candle ATR, but because ``x > min(q, H) <=> x > q or x > H`` (q = am*ATR the
per-candle scalar, H = hm*zone_height a POI invariant), the candidate set
decomposes into a union of two half-line queries on POI-INVARIANT keys —
``zone_bottom`` and ``zone_bottom - H`` for bullish; the mirror ``zone_top`` and
``zone_top + H`` for bearish — so no per-POI threshold is updated as ATR moves.
Each candidate is re-confirmed by the unchanged batch ``_is_breach`` (which
applies the exact ``2*min_tick`` floor), giving zero false negatives.

This is a standalone, permanently-tested primitive. It is NOT the full
event-driven scheduler (no zone-touch index, due queue, wake-union, registration
manager, or gated advancement live here). ``_is_breach`` remains the unchanged
differential oracle.
"""

from bisect import insort
from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle import _is_breach

_TWO = Decimal("2")


@dataclass(frozen=True)
class _Entry:
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    height_term: Decimal  # hm * zone_height
    breach_key: Decimal


@dataclass
class BreachIndex:
    """Sorted-view index over registered scanning POIs for the exact breach
    query. Mutable; O(P_partition) insert/remove (sorted-list splice) and
    O(k + log P) query."""

    overshoot_atr_multiplier: Decimal
    overshoot_height_multiplier: Decimal
    min_tick: Decimal

    _entries: dict[UUID, _Entry] = field(default_factory=dict)
    _bull_by_bottom: list[tuple[Decimal, UUID]] = field(default_factory=list)
    _bull_by_keybottom: list[tuple[Decimal, UUID]] = field(default_factory=list)
    _bear_by_top: list[tuple[Decimal, UUID]] = field(default_factory=list)
    _bear_by_keytop: list[tuple[Decimal, UUID]] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self._entries)


def create_breach_index(configuration: PoiConfiguration) -> BreachIndex:
    return BreachIndex(
        overshoot_atr_multiplier=configuration.zone_overshoot_tolerance_atr_multiplier,
        overshoot_height_multiplier=(
            configuration.zone_overshoot_tolerance_zone_height_multiplier
        ),
        min_tick=configuration.minimum_price_tick,
    )


def _remove_sorted(
    sorted_list: list[tuple[Decimal, UUID]], key: Decimal, rid: UUID
) -> None:
    try:
        sorted_list.remove((key, rid))
    except ValueError:  # pragma: no cover - defensive
        pass


def register(
    index: BreachIndex,
    record_id: UUID,
    direction: PoiDirection,
    zone_top: Decimal,
    zone_bottom: Decimal,
) -> None:
    """Add/refresh a scanning POI (idempotent by record_id)."""
    unregister(index, record_id)
    height_term = index.overshoot_height_multiplier * (zone_top - zone_bottom)
    breach_key = (
        zone_bottom - height_term
        if direction == PoiDirection.BULLISH
        else zone_top + height_term
    )
    index._entries[record_id] = _Entry(
        direction, zone_top, zone_bottom, height_term, breach_key
    )
    if direction == PoiDirection.BULLISH:
        insort(index._bull_by_bottom, (zone_bottom, record_id))
        insort(index._bull_by_keybottom, (breach_key, record_id))
    else:
        insort(index._bear_by_top, (zone_top, record_id))
        insort(index._bear_by_keytop, (breach_key, record_id))


def unregister(index: BreachIndex, record_id: UUID) -> None:
    entry = index._entries.pop(record_id, None)
    if entry is None:
        return
    if entry.direction == PoiDirection.BULLISH:
        _remove_sorted(index._bull_by_bottom, entry.zone_bottom, record_id)
        _remove_sorted(index._bull_by_keybottom, entry.breach_key, record_id)
    else:
        _remove_sorted(index._bear_by_top, entry.zone_top, record_id)
        _remove_sorted(index._bear_by_keytop, entry.breach_key, record_id)


def _greater_than(sorted_list: list[tuple[Decimal, UUID]], bound: Decimal) -> set[UUID]:
    lo, hi = 0, len(sorted_list)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_list[mid][0] > bound:
            hi = mid
        else:
            lo = mid + 1
    return {rid for _key, rid in sorted_list[lo:]}


def _less_than(sorted_list: list[tuple[Decimal, UUID]], bound: Decimal) -> set[UUID]:
    lo, hi = 0, len(sorted_list)
    while lo < hi:
        mid = (lo + hi) // 2
        if sorted_list[mid][0] < bound:
            lo = mid + 1
        else:
            hi = mid
    return {rid for _key, rid in sorted_list[:lo]}


def breach_wake_set(
    index: BreachIndex,
    candle: NormalizedCandle,
    atr_value: Decimal | None,
) -> set[UUID]:
    """Exact set of registered scanning POIs whose ``_is_breach`` fires for this
    candle. ``atr_value`` is the candle's full-prefix Wilder ATR-14; the batch
    ``tolerance`` uses it when positive, else the candle's own high-low range."""
    close = candle.close
    ref = (
        atr_value
        if (atr_value is not None and atr_value > 0)
        else candle.high - candle.low
    )
    q = index.overshoot_atr_multiplier * ref

    # Bullish: gap = zone_bottom - close. gap>q => zb>close+q; gap>H => zb-H>close.
    candidates = _greater_than(index._bull_by_bottom, close + q)
    candidates |= _greater_than(index._bull_by_keybottom, close)
    # Bearish: gap = close - zone_top. gap>q => zt<close-q; gap>H => zt+H<close.
    candidates |= _less_than(index._bear_by_top, close - q)
    candidates |= _less_than(index._bear_by_keytop, close)

    two_mt = _TWO * index.min_tick
    result: set[UUID] = set()
    for rid in candidates:
        entry = index._entries[rid]
        bound_a = index.overshoot_atr_multiplier * ref
        zone_height = entry.zone_top - entry.zone_bottom
        bound_b = entry.height_term if zone_height > 0 else bound_a
        overshoot = max(two_mt, min(bound_a, bound_b))
        if _is_breach(
            candle, entry.direction, entry.zone_top, entry.zone_bottom, overshoot
        ):
            result.add(rid)
    return result
