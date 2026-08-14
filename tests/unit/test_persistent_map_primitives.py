"""A6-F6D-M2R: permanent tests for the PersistentMap.floor_item / range
primitives that back the sparse SR checkpoint lookup and the zone-price routing
stabbing query.

``floor_item`` must return the predecessor-or-equal entry (the checkpoint
carried into a resume position when intermediate positions were never stored),
and ``range`` must return exactly the entries inside an inclusive key window in
ascending order. Both are checked against a brute-force reference over random
key sets, and against the map's own ``items()`` for internal consistency.
"""

from __future__ import annotations

import random

from btmm_ai_scanner.persistent_map import PersistentMap


def _build(keys: list[int]) -> PersistentMap[int]:
    m: PersistentMap[int] = PersistentMap()
    for k in keys:
        m = m.set(k, k * 10)
    return m


def test_floor_item_empty_map() -> None:
    m: PersistentMap[int] = PersistentMap()
    assert m.floor_item(0) is None
    assert m.floor_item(5) is None


def test_floor_item_exact_between_and_below_min() -> None:
    m = _build([2, 4, 6, 8])
    assert m.floor_item(4) == (4, 40)  # exact hit
    assert m.floor_item(5) == (4, 40)  # between -> predecessor
    assert m.floor_item(7) == (6, 60)
    assert m.floor_item(100) == (8, 80)  # above max -> largest key
    assert m.floor_item(2) == (2, 20)  # at min
    assert m.floor_item(1) is None  # below min -> None


def test_range_inclusive_boundaries_and_empty_window() -> None:
    m = _build([1, 3, 5, 7, 9])
    assert m.range(3, 7) == [(3, 30), (5, 50), (7, 70)]  # inclusive both ends
    assert m.range(4, 6) == [(5, 50)]  # only interior key
    assert m.range(10, 20) == []  # window past max
    assert m.range(-5, 0) == []  # window below min
    assert m.range(1, 9) == [(1, 10), (3, 30), (5, 50), (7, 70), (9, 90)]
    assert m.range(5, 5) == [(5, 50)]  # degenerate single-point window


def test_floor_and_range_match_bruteforce_over_random_sets() -> None:
    rng = random.Random(20260814)
    # Keys are non-negative (the map's supported domain: uuid.int / bar index /
    # composite price keys), matching how the SR routing index uses it.
    for _ in range(50):
        keys = rng.sample(range(0, 400), rng.randint(0, 40))
        m = _build(keys)
        ordered = sorted(keys)
        for _q in range(20):
            q = rng.randint(0, 420)
            # floor reference
            below = [k for k in ordered if k <= q]
            expected = (below[-1], below[-1] * 10) if below else None
            assert m.floor_item(q) == expected, (keys, q)
            # range reference
            lo, hi = sorted((rng.randint(0, 420), rng.randint(0, 420)))
            expected_range = [(k, k * 10) for k in ordered if lo <= k <= hi]
            assert m.range(lo, hi) == expected_range, (keys, lo, hi)


def test_range_is_consistent_with_items() -> None:
    m = _build([10, 20, 30, 40, 50])
    assert m.range(0, 10**9) == m.items()


def test_new_primitives_do_not_mutate_ancestor() -> None:
    m = _build([1, 5, 9])
    snapshot = m.items()
    _ = m.floor_item(5)
    _ = m.range(1, 9)
    m2 = m.set(7, 70)
    assert m.items() == snapshot  # ancestor untouched by queries or descendant set
    assert m2.floor_item(8) == (7, 70)
