"""A6-B1-B3: a minimal persistent (path-copying) ordered map.

Keyed by an integer order key (the scheduler passes ``uuid.int`` for POI-keyed
maps and the bar index for the due map). ``set`` / ``delete`` return a NEW map
that structurally shares every untouched subtree with the prior one in O(log n)
new nodes — so the transactional scheduler updates only the touched entries each
candle instead of copying the whole registry (which would be O(P) per candle and
reintroduce the quadratic cost this slice removes). The prior map is never
mutated, giving the same rollback/persistence guarantee as the persistent
indexes: a discarded (failed) advance leaves the previously published map valid
and identical by object identity.

Treap priorities derive deterministically from the key, so structure is
reproducible run-to-run.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


def _priority(key: int) -> int:
    length = max(1, (key.bit_length() + 7) // 8)
    return int.from_bytes(
        hashlib.sha256(key.to_bytes(length, "big")).digest()[:8], "big"
    )


@dataclass(frozen=True)
class _Node[V]:
    key: int
    value: V
    priority: int
    left: _Node[V] | None
    right: _Node[V] | None


def _with[V](node: _Node[V], left: _Node[V] | None, right: _Node[V] | None) -> _Node[V]:
    return _Node(node.key, node.value, node.priority, left, right)


def _set[V](node: _Node[V] | None, key: int, value: V) -> _Node[V]:
    if node is None:
        return _Node(key, value, _priority(key), None, None)
    if key == node.key:
        return _Node(key, value, node.priority, node.left, node.right)
    if key < node.key:
        nl = _set(node.left, key, value)
        if nl.priority < node.priority:
            return _with(nl, nl.left, _with(node, nl.right, node.right))
        return _with(node, nl, node.right)
    nr = _set(node.right, key, value)
    if nr.priority < node.priority:
        return _with(nr, _with(node, node.left, nr.left), nr.right)
    return _with(node, node.left, nr)


def _merge[V](left: _Node[V] | None, right: _Node[V] | None) -> _Node[V] | None:
    if left is None:
        return right
    if right is None:
        return left
    if left.priority <= right.priority:
        return _with(left, left.left, _merge(left.right, right))
    return _with(right, _merge(left, right.left), right.right)


def _delete[V](node: _Node[V] | None, key: int) -> _Node[V] | None:
    if node is None:
        return None
    if key == node.key:
        return _merge(node.left, node.right)
    if key < node.key:
        return _with(node, _delete(node.left, key), node.right)
    return _with(node, node.left, _delete(node.right, key))


def _get[V](node: _Node[V] | None, key: int) -> _Node[V] | None:
    while node is not None:
        if key == node.key:
            return node
        node = node.left if key < node.key else node.right
    return None


def _items[V](node: _Node[V] | None, out: list[tuple[int, V]]) -> None:
    if node is None:
        return
    _items(node.left, out)
    out.append((node.key, node.value))
    _items(node.right, out)


def _floor[V](node: _Node[V] | None, key: int) -> _Node[V] | None:
    # Greatest node whose key is <= ``key`` (predecessor-or-equal), O(log n).
    best: _Node[V] | None = None
    while node is not None:
        if node.key == key:
            return node
        if node.key < key:
            best = node
            node = node.right
        else:
            node = node.left
    return best


def _range[V](
    node: _Node[V] | None, lo: int, hi: int, out: list[tuple[int, V]]
) -> None:
    # In-order collect of every entry with lo <= key <= hi, pruning subtrees that
    # cannot contain an in-range key -> O(log n + k) for k results.
    if node is None:
        return
    if node.key > lo:
        _range(node.left, lo, hi, out)
    if lo <= node.key <= hi:
        out.append((node.key, node.value))
    if node.key < hi:
        _range(node.right, lo, hi, out)


@dataclass(frozen=True)
class PersistentMap[V]:
    """Immutable ordered map with integer keys; every mutation returns a new map
    sharing all untouched subtrees."""

    _root: _Node[V] | None = None
    _size: int = 0

    def __len__(self) -> int:
        return self._size

    def __contains__(self, key: int) -> bool:
        return _get(self._root, key) is not None

    def get(self, key: int, default: V | None = None) -> V | None:
        node = _get(self._root, key)
        return node.value if node is not None else default

    def set(self, key: int, value: V) -> PersistentMap[V]:
        present = _get(self._root, key) is not None
        return PersistentMap(
            _root=_set(self._root, key, value),
            _size=self._size + (0 if present else 1),
        )

    def delete(self, key: int) -> PersistentMap[V]:
        if _get(self._root, key) is None:
            return self
        return PersistentMap(_root=_delete(self._root, key), _size=self._size - 1)

    def items(self) -> list[tuple[int, V]]:
        out: list[tuple[int, V]] = []
        _items(self._root, out)
        return out

    def floor_item(self, key: int) -> tuple[int, V] | None:
        """The (key, value) of the greatest stored key <= ``key`` (None if the
        map has no such key). O(log n). Used to read the checkpoint carried into
        a resume position when intermediate positions were never stored (a
        geometric-miss touch never changes the sequential state, so the last
        stored checkpoint is exactly the entering value)."""
        node = _floor(self._root, key)
        return (node.key, node.value) if node is not None else None

    def range(self, lo: int, hi: int) -> list[tuple[int, V]]:
        """Every (key, value) with ``lo <= key <= hi`` in ascending key order,
        visiting only O(log n + k) nodes for k results."""
        out: list[tuple[int, V]] = []
        _range(self._root, lo, hi, out)
        return out
