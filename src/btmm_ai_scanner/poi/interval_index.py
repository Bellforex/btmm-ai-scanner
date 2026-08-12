"""A6-B1-B1: exact dynamic interval-stabbing index (zone-touch discovery).

An augmented treap keyed by ``(zone_bottom, record_id)`` with a per-subtree
``max(zone_top)`` augmentation, supporting O(log n) expected insert/delete and
an ``overlaps(qlo, qhi)`` query that returns exactly the intervals overlapping
``[qlo, qhi]`` in O(k + log n) expected (k = number returned), by pruning any
subtree whose ``max(zone_top) < qlo`` and any right subtree whose keys exceed
``qhi``. No maximum-zone-width assumption, no backward scan, no whole-set scan.

Treap priorities are derived deterministically from ``record_id`` (not random),
so structure and iteration are reproducible run-to-run. Overlap here means
``zone_bottom <= qhi and zone_top >= qlo`` — identical to
``_touches_zone(poi, candle)`` with ``qlo = candle.low``, ``qhi = candle.high``.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


def _priority(record_id: UUID) -> int:
    return int.from_bytes(hashlib.sha256(record_id.bytes).digest()[:8], "big")


@dataclass
class _Node:
    zone_bottom: Decimal
    zone_top: Decimal
    record_id: UUID
    priority: int
    max_top: Decimal
    left: _Node | None = None
    right: _Node | None = None


def _pull(node: _Node) -> None:
    m = node.zone_top
    if node.left is not None and node.left.max_top > m:
        m = node.left.max_top
    if node.right is not None and node.right.max_top > m:
        m = node.right.max_top
    node.max_top = m


def _key(zone_bottom: Decimal, record_id: UUID) -> tuple[Decimal, str]:
    return (zone_bottom, str(record_id))


def _rotate_right(node: _Node) -> _Node:
    left = node.left
    assert left is not None
    node.left = left.right
    left.right = node
    _pull(node)
    _pull(left)
    return left


def _rotate_left(node: _Node) -> _Node:
    right = node.right
    assert right is not None
    node.right = right.left
    right.left = node
    _pull(node)
    _pull(right)
    return right


def _insert(node: _Node | None, new: _Node) -> _Node:
    if node is None:
        return new
    if _key(new.zone_bottom, new.record_id) < _key(node.zone_bottom, node.record_id):
        node.left = _insert(node.left, new)
        if node.left.priority < node.priority:
            node = _rotate_right(node)
    else:
        node.right = _insert(node.right, new)
        if node.right.priority < node.priority:
            node = _rotate_left(node)
    _pull(node)
    return node


def _delete(node: _Node | None, zone_bottom: Decimal, record_id: UUID) -> _Node | None:
    if node is None:
        return None
    target = _key(zone_bottom, record_id)
    here = _key(node.zone_bottom, node.record_id)
    if target < here:
        node.left = _delete(node.left, zone_bottom, record_id)
    elif target > here:
        node.right = _delete(node.right, zone_bottom, record_id)
    else:
        if node.left is None:
            return node.right
        if node.right is None:
            return node.left
        # Rotate the smaller-priority child up, recurse.
        if node.left.priority < node.right.priority:
            node = _rotate_right(node)
            node.right = _delete(node.right, zone_bottom, record_id)
        else:
            node = _rotate_left(node)
            node.left = _delete(node.left, zone_bottom, record_id)
    _pull(node)
    return node


class IntervalTouchIndex:
    """Exact dynamic interval index for zone-touch wake discovery."""

    def __init__(self) -> None:
        self._root: _Node | None = None
        self._zone_by_id: dict[UUID, tuple[Decimal, Decimal]] = {}

    def __len__(self) -> int:
        return len(self._zone_by_id)

    def insert(self, record_id: UUID, zone_bottom: Decimal, zone_top: Decimal) -> None:
        if record_id in self._zone_by_id:
            self.remove(record_id)
        self._zone_by_id[record_id] = (zone_bottom, zone_top)
        self._root = _insert(
            self._root,
            _Node(
                zone_bottom=zone_bottom,
                zone_top=zone_top,
                record_id=record_id,
                priority=_priority(record_id),
                max_top=zone_top,
            ),
        )

    def remove(self, record_id: UUID) -> None:
        zone = self._zone_by_id.pop(record_id, None)
        if zone is None:
            return
        self._root = _delete(self._root, zone[0], record_id)

    def overlaps(self, query_low: Decimal, query_high: Decimal) -> set[UUID]:
        """Exactly the record_ids whose ``[zone_bottom, zone_top]`` overlaps
        ``[query_low, query_high]`` (``zone_bottom <= query_high`` and
        ``zone_top >= query_low``)."""
        result: set[UUID] = set()
        self._collect(self._root, query_low, query_high, result)
        return result

    def _collect(
        self,
        node: _Node | None,
        qlo: Decimal,
        qhi: Decimal,
        out: set[UUID],
    ) -> None:
        if node is None or node.max_top < qlo:
            # Whole subtree has every zone_top < qlo: no interval can reach qlo.
            return
        # Left subtree may contain overlapping intervals (smaller zone_bottom).
        self._collect(node.left, qlo, qhi, out)
        if node.zone_bottom <= qhi:
            if node.zone_top >= qlo:
                out.add(node.record_id)
            # Right subtree keys have zone_bottom >= this node's; still <= qhi is
            # possible, so recurse.
            self._collect(node.right, qlo, qhi, out)
        # else: node.zone_bottom > qhi => all right keys > qhi, skip right.
