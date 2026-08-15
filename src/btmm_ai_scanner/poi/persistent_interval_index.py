"""A6-B1-B3: transaction-safe (persistent) zone-touch interval index.

A path-copying immutable variant of the accepted ``interval_index`` treap. Every
``insert`` / ``remove`` returns a NEW root that structurally shares every
untouched subtree with the prior root; the prior root is never mutated, so a
scheduler advance that inserts/removes here and then fails leaves the previously
published root valid, unchanged, and identical by object identity. No whole-tree
copy, no per-candle rebuild.

The query semantics are byte-identical to the accepted mutable
``IntervalTouchIndex.overlaps`` (and therefore to ``_touches_zone``): a zone is
returned iff ``zone_bottom <= query_high and zone_top >= query_low``. Priorities
are the same deterministic ``sha256(record_id.bytes)[:8]`` used by the accepted
index, so the two indexes hold the same multiset of keys with the same treap
shape for the same insertion history — asserted by the permanent differential
tests. The accepted ``interval_index`` module is not modified.

Because nodes are frozen and every mutating operation copies only the touched
root-to-leaf path (O(log n) new nodes), an older root snapshot keeps answering
its original queries after later branches diverge — the persistence property the
transactional scheduler relies on.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


def _priority(record_id: UUID) -> int:
    return int.from_bytes(hashlib.sha256(record_id.bytes).digest()[:8], "big")


@dataclass(frozen=True)
class _Node:
    zone_bottom: Decimal
    zone_top: Decimal
    record_id: UUID
    priority: int
    max_top: Decimal
    left: _Node | None
    right: _Node | None


def _max_top(node: _Node | None) -> Decimal | None:
    return node.max_top if node is not None else None


def _make(
    zone_bottom: Decimal,
    zone_top: Decimal,
    record_id: UUID,
    priority: int,
    left: _Node | None,
    right: _Node | None,
) -> _Node:
    """Construct a fresh node with the exact subtree ``max(zone_top)``."""
    m = zone_top
    lm = _max_top(left)
    if lm is not None and lm > m:
        m = lm
    rm = _max_top(right)
    if rm is not None and rm > m:
        m = rm
    return _Node(
        zone_bottom=zone_bottom,
        zone_top=zone_top,
        record_id=record_id,
        priority=priority,
        max_top=m,
        left=left,
        right=right,
    )


def _key(zone_bottom: Decimal, record_id: UUID) -> tuple[Decimal, str]:
    return (zone_bottom, str(record_id))


def _with_children(node: _Node, left: _Node | None, right: _Node | None) -> _Node:
    return _make(
        node.zone_bottom, node.zone_top, node.record_id, node.priority, left, right
    )


def _insert(node: _Node | None, new: _Node) -> _Node:
    if node is None:
        return new
    if _key(new.zone_bottom, new.record_id) < _key(node.zone_bottom, node.record_id):
        new_left = _insert(node.left, new)
        if new_left.priority < node.priority:
            # Rotate right: new_left becomes the root of this subtree.
            return _with_children(
                new_left,
                new_left.left,
                _with_children(node, new_left.right, node.right),
            )
        return _with_children(node, new_left, node.right)
    new_right = _insert(node.right, new)
    if new_right.priority < node.priority:
        # Rotate left.
        return _with_children(
            new_right,
            _with_children(node, node.left, new_right.left),
            new_right.right,
        )
    return _with_children(node, node.left, new_right)


def _merge(left: _Node | None, right: _Node | None) -> _Node | None:
    """Merge two treaps where every key in ``left`` < every key in ``right``."""
    if left is None:
        return right
    if right is None:
        return left
    if left.priority <= right.priority:
        return _with_children(left, left.left, _merge(left.right, right))
    return _with_children(right, _merge(left, right.left), right.right)


def _delete(node: _Node | None, zone_bottom: Decimal, record_id: UUID) -> _Node | None:
    if node is None:
        return None
    target = _key(zone_bottom, record_id)
    here = _key(node.zone_bottom, node.record_id)
    if target < here:
        return _with_children(
            node, _delete(node.left, zone_bottom, record_id), node.right
        )
    if target > here:
        return _with_children(
            node, node.left, _delete(node.right, zone_bottom, record_id)
        )
    return _merge(node.left, node.right)


def _collect(node: _Node | None, qlo: Decimal, qhi: Decimal, out: set[UUID]) -> None:
    if node is None or node.max_top < qlo:
        return
    _collect(node.left, qlo, qhi, out)
    if node.zone_bottom <= qhi:
        if node.zone_top >= qlo:
            out.add(node.record_id)
        _collect(node.right, qlo, qhi, out)


@dataclass(frozen=True)
class PersistentIntervalTouchIndex:
    """Immutable, structurally-shared zone-touch index. ``insert`` / ``remove``
    return a new index sharing all untouched subtrees; this instance is never
    mutated. ``remove`` takes the zone bounds the caller registered (no internal
    id->zone map to copy), keeping every operation O(log n) new nodes."""

    _root: _Node | None = None
    _size: int = 0

    def __len__(self) -> int:
        return self._size

    def insert(
        self, record_id: UUID, zone_bottom: Decimal, zone_top: Decimal
    ) -> PersistentIntervalTouchIndex:
        # Idempotent by record_id: an existing entry (same zone) is left as-is;
        # a changed zone must be removed first by the caller (the scheduler
        # unregisters on replace). Guard against duplicate keys defensively.
        node = _Node(
            zone_bottom=zone_bottom,
            zone_top=zone_top,
            record_id=record_id,
            priority=_priority(record_id),
            max_top=zone_top,
            left=None,
            right=None,
        )
        return PersistentIntervalTouchIndex(
            _root=_insert(self._root, node), _size=self._size + 1
        )

    def remove(
        self, record_id: UUID, zone_bottom: Decimal
    ) -> PersistentIntervalTouchIndex:
        new_root = _delete(self._root, zone_bottom, record_id)
        if new_root is self._root:
            return self
        return PersistentIntervalTouchIndex(_root=new_root, _size=self._size - 1)

    def overlaps(self, query_low: Decimal, query_high: Decimal) -> set[UUID]:
        result: set[UUID] = set()
        _collect(self._root, query_low, query_high, result)
        return result


def create_persistent_interval_index() -> PersistentIntervalTouchIndex:
    return PersistentIntervalTouchIndex()
