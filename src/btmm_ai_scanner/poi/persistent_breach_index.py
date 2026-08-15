"""A6-B1-B3: transaction-safe (persistent) ATR-invariant breach wake index.

A path-copying immutable variant of the accepted ``breach_index``. The accepted
index keeps four mutable sorted lists (``insort`` / ``list.remove``); this variant
keeps four persistent ordered-set treaps whose nodes carry the POI's zone data,
so ``register`` / ``unregister`` return a NEW index that structurally shares every
untouched subtree with the prior one in O(log n) new nodes — no per-operation
dict copy, no whole-index rebuild. The prior index is never mutated: a scheduler
advance that registers/unregisters here and then fails leaves the previously
published index valid and identical by object identity.

The decomposition and query are byte-identical to the accepted index. The moving
threshold ``max(2*min_tick, min(am*ATR, hm*zone_height))`` decomposes via
``x > min(q, H) <=> x > q or x > H`` into half-line queries on the POI-invariant
keys ``zone_bottom`` / ``zone_bottom - hm*H`` (bullish; mirror ``zone_top`` /
``zone_top + hm*H`` bearish); each candidate is re-confirmed by the unchanged
batch ``_is_breach`` (which applies the exact ``2*min_tick`` floor), giving zero
false negatives. The accepted ``breach_index`` module is not modified.

``register`` assumes ``record_id`` is not already present (the scheduler
unregisters the old zone before re-registering a changed one); ``unregister``
takes the same zone bounds/direction the caller registered, so no id->zone map is
kept and every operation stays O(log n).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection
from btmm_ai_scanner.poi.lifecycle import _is_breach

_TWO = Decimal("2")


def _priority(record_id: UUID) -> int:
    return int.from_bytes(hashlib.sha256(record_id.bytes).digest()[:8], "big")


@dataclass(frozen=True)
class _SetNode:
    key: Decimal  # sort key for this particular tree
    record_id: UUID
    direction: PoiDirection
    zone_top: Decimal
    zone_bottom: Decimal
    height_term: Decimal
    priority: int
    left: _SetNode | None
    right: _SetNode | None


def _okey(key: Decimal, record_id: UUID) -> tuple[Decimal, str]:
    return (key, str(record_id))


def _with(node: _SetNode, left: _SetNode | None, right: _SetNode | None) -> _SetNode:
    return _SetNode(
        node.key,
        node.record_id,
        node.direction,
        node.zone_top,
        node.zone_bottom,
        node.height_term,
        node.priority,
        left,
        right,
    )


def _insert(node: _SetNode | None, new: _SetNode) -> _SetNode:
    if node is None:
        return new
    if _okey(new.key, new.record_id) < _okey(node.key, node.record_id):
        nl = _insert(node.left, new)
        if nl.priority < node.priority:
            return _with(nl, nl.left, _with(node, nl.right, node.right))
        return _with(node, nl, node.right)
    nr = _insert(node.right, new)
    if nr.priority < node.priority:
        return _with(nr, _with(node, node.left, nr.left), nr.right)
    return _with(node, node.left, nr)


def _merge(left: _SetNode | None, right: _SetNode | None) -> _SetNode | None:
    if left is None:
        return right
    if right is None:
        return left
    if left.priority <= right.priority:
        return _with(left, left.left, _merge(left.right, right))
    return _with(right, _merge(left, right.left), right.right)


def _delete(node: _SetNode | None, key: Decimal, record_id: UUID) -> _SetNode | None:
    if node is None:
        return None
    target = _okey(key, record_id)
    here = _okey(node.key, node.record_id)
    if target < here:
        return _with(node, _delete(node.left, key, record_id), node.right)
    if target > here:
        return _with(node, node.left, _delete(node.right, key, record_id))
    return _merge(node.left, node.right)


def _collect_all(node: _SetNode | None, out: dict[UUID, _SetNode]) -> None:
    if node is None:
        return
    _collect_all(node.left, out)
    out[node.record_id] = node
    _collect_all(node.right, out)


def _collect_greater(
    node: _SetNode | None, bound: Decimal, out: dict[UUID, _SetNode]
) -> None:
    """Entries whose key ``> bound`` (strict)."""
    if node is None:
        return
    if node.key > bound:
        out[node.record_id] = node
        _collect_all(node.right, out)
        _collect_greater(node.left, bound, out)
    else:
        _collect_greater(node.right, bound, out)


def _collect_less(
    node: _SetNode | None, bound: Decimal, out: dict[UUID, _SetNode]
) -> None:
    """Entries whose key ``< bound`` (strict)."""
    if node is None:
        return
    if node.key < bound:
        out[node.record_id] = node
        _collect_all(node.left, out)
        _collect_less(node.right, bound, out)
    else:
        _collect_less(node.left, bound, out)


@dataclass(frozen=True)
class PersistentBreachIndex:
    """Immutable, structurally-shared breach wake index over registered scanning
    POIs. ``register`` / ``unregister`` return a new index; this one is never
    mutated."""

    overshoot_atr_multiplier: Decimal
    overshoot_height_multiplier: Decimal
    min_tick: Decimal
    _size: int = 0
    _bull_by_bottom: _SetNode | None = None
    _bull_by_keybottom: _SetNode | None = None
    _bear_by_top: _SetNode | None = None
    _bear_by_keytop: _SetNode | None = None

    def __len__(self) -> int:
        return self._size

    def register(
        self,
        record_id: UUID,
        direction: PoiDirection,
        zone_top: Decimal,
        zone_bottom: Decimal,
    ) -> PersistentBreachIndex:
        height_term = self.overshoot_height_multiplier * (zone_top - zone_bottom)
        breach_key = (
            zone_bottom - height_term
            if direction == PoiDirection.BULLISH
            else zone_top + height_term
        )
        prio = _priority(record_id)

        def node(key: Decimal) -> _SetNode:
            return _SetNode(
                key,
                record_id,
                direction,
                zone_top,
                zone_bottom,
                height_term,
                prio,
                None,
                None,
            )

        if direction == PoiDirection.BULLISH:
            return PersistentBreachIndex(
                overshoot_atr_multiplier=self.overshoot_atr_multiplier,
                overshoot_height_multiplier=self.overshoot_height_multiplier,
                min_tick=self.min_tick,
                _size=self._size + 1,
                _bull_by_bottom=_insert(self._bull_by_bottom, node(zone_bottom)),
                _bull_by_keybottom=_insert(self._bull_by_keybottom, node(breach_key)),
                _bear_by_top=self._bear_by_top,
                _bear_by_keytop=self._bear_by_keytop,
            )
        return PersistentBreachIndex(
            overshoot_atr_multiplier=self.overshoot_atr_multiplier,
            overshoot_height_multiplier=self.overshoot_height_multiplier,
            min_tick=self.min_tick,
            _size=self._size + 1,
            _bull_by_bottom=self._bull_by_bottom,
            _bull_by_keybottom=self._bull_by_keybottom,
            _bear_by_top=_insert(self._bear_by_top, node(zone_top)),
            _bear_by_keytop=_insert(self._bear_by_keytop, node(breach_key)),
        )

    def unregister(
        self,
        record_id: UUID,
        direction: PoiDirection,
        zone_top: Decimal,
        zone_bottom: Decimal,
    ) -> PersistentBreachIndex:
        height_term = self.overshoot_height_multiplier * (zone_top - zone_bottom)
        breach_key = (
            zone_bottom - height_term
            if direction == PoiDirection.BULLISH
            else zone_top + height_term
        )
        if direction == PoiDirection.BULLISH:
            new_bottom = _delete(self._bull_by_bottom, zone_bottom, record_id)
            if new_bottom is self._bull_by_bottom:
                return self
            return PersistentBreachIndex(
                overshoot_atr_multiplier=self.overshoot_atr_multiplier,
                overshoot_height_multiplier=self.overshoot_height_multiplier,
                min_tick=self.min_tick,
                _size=self._size - 1,
                _bull_by_bottom=new_bottom,
                _bull_by_keybottom=_delete(
                    self._bull_by_keybottom, breach_key, record_id
                ),
                _bear_by_top=self._bear_by_top,
                _bear_by_keytop=self._bear_by_keytop,
            )
        new_top = _delete(self._bear_by_top, zone_top, record_id)
        if new_top is self._bear_by_top:
            return self
        return PersistentBreachIndex(
            overshoot_atr_multiplier=self.overshoot_atr_multiplier,
            overshoot_height_multiplier=self.overshoot_height_multiplier,
            min_tick=self.min_tick,
            _size=self._size - 1,
            _bull_by_bottom=self._bull_by_bottom,
            _bull_by_keybottom=self._bull_by_keybottom,
            _bear_by_top=new_top,
            _bear_by_keytop=_delete(self._bear_by_keytop, breach_key, record_id),
        )

    def breach_wake_set(
        self, candle: NormalizedCandle, atr_value: Decimal | None
    ) -> set[UUID]:
        close = candle.close
        ref = (
            atr_value
            if (atr_value is not None and atr_value > 0)
            else candle.high - candle.low
        )
        q = self.overshoot_atr_multiplier * ref

        candidates: dict[UUID, _SetNode] = {}
        _collect_greater(self._bull_by_bottom, close + q, candidates)
        _collect_greater(self._bull_by_keybottom, close, candidates)
        _collect_less(self._bear_by_top, close - q, candidates)
        _collect_less(self._bear_by_keytop, close, candidates)

        two_mt = _TWO * self.min_tick
        result: set[UUID] = set()
        for rid, entry in candidates.items():
            bound_a = self.overshoot_atr_multiplier * ref
            zone_height = entry.zone_top - entry.zone_bottom
            bound_b = entry.height_term if zone_height > 0 else bound_a
            overshoot = max(two_mt, min(bound_a, bound_b))
            if _is_breach(
                candle, entry.direction, entry.zone_top, entry.zone_bottom, overshoot
            ):
                result.add(rid)
        return result


def create_persistent_breach_index(
    configuration: PoiConfiguration,
) -> PersistentBreachIndex:
    return PersistentBreachIndex(
        overshoot_atr_multiplier=configuration.zone_overshoot_tolerance_atr_multiplier,
        overshoot_height_multiplier=(
            configuration.zone_overshoot_tolerance_zone_height_multiplier
        ),
        min_tick=configuration.minimum_price_tick,
    )
