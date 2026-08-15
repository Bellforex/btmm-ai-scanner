"""A6-F6: permanent tests for the persistent ordered-map primitive.

Covers insert / replace / delete / get, deterministic ordered traversal,
structural sharing, branch independence, rollback (ancestor unchanged), and --
mandatorily -- that the treap priority (and therefore tree shape and ordered
output) is reproducible across independent processes, i.e. NOT dependent on
Python's per-process randomized ``hash()``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

from btmm_ai_scanner.poi.persistent_ordered_map import PersistentOrderedMap


def _shape(node: object) -> tuple[object, ...]:
    """Pre-order (key, priority) serialization of the internal treap -- fully
    determines the tree shape (a treap is unique given its {key: priority})."""
    if node is None:
        return ()
    return (
        (node.key, node.priority),  # type: ignore[attr-defined]
        _shape(node.left),  # type: ignore[attr-defined]
        _shape(node.right),  # type: ignore[attr-defined]
    )


def test_insert_get_len() -> None:
    m: PersistentOrderedMap[int, str] = PersistentOrderedMap()
    m = m.insert(3, 3, "c").insert(1, 1, "a").insert(2, 2, "b")
    assert len(m) == 3
    assert m.get(1) == "a"
    assert m.get(2) == "b"
    assert m.get(3) == "c"
    assert m.get(4) is None


def test_ordered_traversal() -> None:
    m: PersistentOrderedMap[tuple[int, int], int] = PersistentOrderedMap()
    keys = [(5, 0), (1, 9), (3, 3), (1, 2), (4, 4)]
    for i, k in enumerate(keys):
        m = m.insert(k, i + 1, i)
    ordered = m.ordered_values()
    expected_keys = sorted(keys)
    got_keys = [keys[v] for v in ordered]
    assert got_keys == expected_keys


def test_replace_existing_key_keeps_size_and_order() -> None:
    m: PersistentOrderedMap[int, str] = PersistentOrderedMap()
    m = m.insert(1, 1, "a").insert(2, 2, "b")
    m2 = m.insert(1, 1, "A")  # replace value at existing key
    assert len(m2) == 2
    assert m2.get(1) == "A"
    assert m2.ordered_values() == ("A", "b")
    # original unchanged
    assert m.get(1) == "a"
    assert m.ordered_values() == ("a", "b")


def test_delete() -> None:
    m: PersistentOrderedMap[int, int] = PersistentOrderedMap()
    for i in range(10):
        m = m.insert(i, i + 1, i)
    m2 = m.delete(5)
    assert len(m2) == 9
    assert m2.get(5) is None
    assert m2.ordered_values() == (0, 1, 2, 3, 4, 6, 7, 8, 9)
    # deleting a missing key is a no-op returning the same object
    assert m2.delete(999) is m2


def test_structural_sharing_and_rollback() -> None:
    m: PersistentOrderedMap[int, int] = PersistentOrderedMap()
    for i in range(500):
        m = m.insert(i, i + 1, i)
    snapshot = m.ordered_values()
    root_before = m.root_identity()

    # Mutate into a descendant; ancestor must remain byte-identical and share its
    # root object (no in-place mutation of published nodes).
    descendant = m.insert(1000, 1001, 1000).delete(250)
    assert m.root_identity() is root_before
    assert m.ordered_values() == snapshot
    assert len(m) == 500
    # descendant reflects the change independently
    assert len(descendant) == 500
    assert 250 not in descendant.ordered_values()
    assert 1000 in descendant.ordered_values()


def test_branch_independence() -> None:
    base: PersistentOrderedMap[int, int] = PersistentOrderedMap()
    for i in range(100):
        base = base.insert(i, i + 1, i)
    left = base.insert(1000, 1001, 1000)
    right = base.insert(2000, 2001, 2000)
    assert 1000 in left.ordered_values() and 2000 not in left.ordered_values()
    assert 2000 in right.ordered_values() and 1000 not in right.ordered_values()
    assert base.ordered_values() == tuple(range(100))


def test_priority_is_deterministic_not_hash_based() -> None:
    # Same (key, seed) data always yields the same tree shape in-process,
    # regardless of key type (string keys are hash-randomized by Python but the
    # priority derives from the integer seed, never from hash()).
    def build() -> tuple[object, ...]:
        m: PersistentOrderedMap[str, int] = PersistentOrderedMap()
        for i, k in enumerate(["delta", "alpha", "charlie", "bravo", "echo"]):
            m = m.insert(k, (i + 1) * 1_000_003, i)
        return _shape(m.root_identity())

    assert build() == build()


_CROSS_PROCESS_SCRIPT = textwrap.dedent(
    """
    import hashlib
    from btmm_ai_scanner.poi.persistent_ordered_map import PersistentOrderedMap

    def shape(node):
        if node is None:
            return ()
        return ((repr(node.key), node.priority), shape(node.left), shape(node.right))

    m = PersistentOrderedMap()
    data = [("m",5),("a",1),("z",9),("q",3),("b",2),("m",7),("c",4),("a",8)]
    for i,(k,s) in enumerate(data):
        m = m.insert(k, s*2654435761, (i,k))
    sig = repr((shape(m.root_identity()), m.ordered_values()))
    print(hashlib.sha256(sig.encode()).hexdigest())
    """
)


def _run_in_process_with_hashseed(seed: str) -> str:
    env = dict(os.environ, PYTHONHASHSEED=seed)
    out = subprocess.run(
        [sys.executable, "-c", _CROSS_PROCESS_SCRIPT],
        capture_output=True,
        text=True,
        env=env,
        check=True,
    )
    return out.stdout.strip()


def test_priority_and_order_reproducible_across_processes() -> None:
    # MANDATORY: two independent processes with DIFFERENT hash randomization
    # seeds must build byte-identical tree shape + ordered output. Proves the
    # persistent map's shape/order does not depend on Python's randomized hash().
    digest_a = _run_in_process_with_hashseed("0")
    digest_b = _run_in_process_with_hashseed("12345")
    digest_c = _run_in_process_with_hashseed("random")
    assert digest_a == digest_b == digest_c
    assert len(digest_a) == 64
