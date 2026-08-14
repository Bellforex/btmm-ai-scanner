"""A6-F6: a persistent (path-copying) ordered map keyed by an arbitrary
comparable order key, with a *deterministic* treap priority.

This generalizes :mod:`poi.persistent_map` (which keys strictly by ``int``) to
canonical composite order keys -- e.g. the public observation/transition sort
tuples ``(availability_time, timeframe, ..., record_id)`` -- so replay state can
maintain records in exact canonical order with O(log n) insert/delete/replace
and structural sharing, materializing the ordered tuple only on demand.

Determinism (register F6 §3): the treap priority is NEVER derived from Python's
per-process randomized ``hash()``. It is a fixed SHA-256 digest of an integer
*priority seed* supplied by the caller (the record's ``record_id.int`` -- itself
a deterministic content-addressed id), so the tree shape, and therefore the
in-order traversal for equal-priority ties, is reproducible across processes.
Ordering is by ``order_key`` alone; the seed only breaks treap heap ties.

Every mutation returns a NEW map sharing all untouched subtrees with the prior
one in O(log n) new nodes; the prior map is never mutated, giving the same
rollback/persistence guarantee as ``PersistentMap``: a discarded (failed)
advance leaves the previously published map valid and identical by object
identity.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


def _priority(seed: int) -> int:
    length = max(1, (seed.bit_length() + 7) // 8)
    return int.from_bytes(
        hashlib.sha256(seed.to_bytes(length, "big")).digest()[:8], "big"
    )


@dataclass(frozen=True)
class _Node[K, V]:
    key: K
    priority: int
    value: V
    left: _Node[K, V] | None
    right: _Node[K, V] | None


def _with[K, V](
    node: _Node[K, V], left: _Node[K, V] | None, right: _Node[K, V] | None
) -> _Node[K, V]:
    return _Node(node.key, node.priority, node.value, left, right)


def _set[K, V](
    node: _Node[K, V] | None, key: K, priority: int, value: V
) -> _Node[K, V]:
    if node is None:
        return _Node(key, priority, value, None, None)
    if key == node.key:
        return _Node(key, node.priority, value, node.left, node.right)
    if key < node.key:  # type: ignore[operator]
        nl = _set(node.left, key, priority, value)
        if nl.priority < node.priority:
            return _with(nl, nl.left, _with(node, nl.right, node.right))
        return _with(node, nl, node.right)
    nr = _set(node.right, key, priority, value)
    if nr.priority < node.priority:
        return _with(nr, _with(node, node.left, nr.left), nr.right)
    return _with(node, node.left, nr)


def _merge[K, V](
    left: _Node[K, V] | None, right: _Node[K, V] | None
) -> _Node[K, V] | None:
    if left is None:
        return right
    if right is None:
        return left
    if left.priority <= right.priority:
        return _with(left, left.left, _merge(left.right, right))
    return _with(right, _merge(left, right.left), right.right)


def _delete[K, V](node: _Node[K, V] | None, key: K) -> _Node[K, V] | None:
    if node is None:
        return None
    if key == node.key:
        return _merge(node.left, node.right)
    if key < node.key:  # type: ignore[operator]
        return _with(node, _delete(node.left, key), node.right)
    return _with(node, node.left, _delete(node.right, key))


def _get[K, V](node: _Node[K, V] | None, key: K) -> _Node[K, V] | None:
    while node is not None:
        if key == node.key:
            return node
        node = node.left if key < node.key else node.right  # type: ignore[operator]
    return None


def _values[K, V](node: _Node[K, V] | None, out: list[V]) -> None:
    if node is None:
        return
    _values(node.left, out)
    out.append(node.value)
    _values(node.right, out)


@dataclass(frozen=True)
class PersistentOrderedMap[K, V]:
    """Immutable ordered map keyed by a comparable ``order_key``; every mutation
    returns a new map sharing all untouched subtrees. In-order traversal yields
    values in ascending ``order_key`` order."""

    _root: _Node[K, V] | None = None
    _size: int = 0

    def __len__(self) -> int:
        return self._size

    def get(self, key: K) -> V | None:
        node = _get(self._root, key)
        return node.value if node is not None else None

    def insert(
        self, key: K, priority_seed: int, value: V
    ) -> PersistentOrderedMap[K, V]:
        present = _get(self._root, key) is not None
        return PersistentOrderedMap(
            _root=_set(self._root, key, _priority(priority_seed), value),
            _size=self._size + (0 if present else 1),
        )

    def delete(self, key: K) -> PersistentOrderedMap[K, V]:
        if _get(self._root, key) is None:
            return self
        return PersistentOrderedMap(
            _root=_delete(self._root, key), _size=self._size - 1
        )

    def ordered_values(self) -> tuple[V, ...]:
        out: list[V] = []
        _values(self._root, out)
        return tuple(out)

    def root_identity(self) -> Any:
        """The internal root node (or None) -- for structural-sharing tests only."""
        return self._root
