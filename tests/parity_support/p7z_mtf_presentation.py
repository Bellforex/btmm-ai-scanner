"""RC3 presentation contracts: timeframe rank, host eligibility, annotation collision.

Test-side oracle only. Nothing in ``src/`` imports this, and none of it touches
detection, geometry, lifecycle or scoring. Every rule here decides what is
*drawn*, never what exists.

WHY A HOST-ELIGIBILITY FILTER EXISTS AT ALL
-------------------------------------------
P3 is single-timeframe by construction: the registry carries no per-POI origin
timeframe, so today every POI on a daily chart is a daily POI and the filter is
a no-op. It is written and tested anyway because the contract is the author's,
and because the day P3 gains genuine multi-timeframe POIs the filter is the only
thing standing between a daily chart and a pile of one-minute boxes. A no-op
with tests is cheap; retrofitting the rule under pressure is not.

The direction is deliberate and asymmetric. Higher-timeframe structure may
legitimately project down onto a lower host; lower-timeframe detail must never
climb onto a higher one.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

__all__ = [
    "TF_RANK",
    "AnnotationDecision",
    "ZoneForDisplay",
    "collision_groups",
    "host_eligible",
    "resolve_annotations",
    "timeframe_rank",
]

#: Canonical ordering of every timeframe token the release formatter can emit.
#: Ranks are ordinal only — the gaps carry no meaning, and nothing outside this
#: module may treat them as durations.
TF_RANK: dict[str, int] = {
    "S1": 0,
    "S5": 1,
    "S15": 2,
    "S30": 3,
    "M1": 10,
    "M2": 11,
    "M3": 12,
    "M5": 13,
    "M10": 14,
    "M15": 15,
    "M30": 16,
    "M45": 17,
    "H1": 20,
    "H2": 21,
    "H3": 22,
    "H4": 23,
    "H6": 24,
    "H8": 25,
    "H12": 26,
    "D1": 30,
    "D2": 31,
    "D3": 32,
    "W1": 40,
    "MN1": 50,
    "MN3": 51,
    "MN12": 52,
}


def timeframe_rank(token: str) -> int | None:
    """Ordinal rank of a canonical timeframe token, or None if unrecognised.

    Returning None rather than a sentinel number is the point: an unrecognised
    token must not silently sort as "very small" or "very large". The caller has
    to decide, and the release caller's decision is to not draw it.
    """
    return TF_RANK.get(token)


def host_eligible(source_token: str, host_token: str) -> bool:
    """May a POI originating on `source_token` be drawn on a `host_token` chart?

    True when the origin is the host timeframe or higher. An unrecognised token
    on either side is False: a POI whose timeframe cannot be named cannot be
    labelled honestly, so release mode suppresses it instead of rendering "TF?".
    """
    source_rank = timeframe_rank(source_token)
    host_rank = timeframe_rank(host_token)
    if source_rank is None or host_rank is None:
        return False
    return source_rank >= host_rank


@dataclass(frozen=True)
class ZoneForDisplay:
    """One visual group as it reaches the annotation layer.

    `stable_id` is the canonical registry index of the group's representative
    POI. It is the final tie-break and must be stable across bars, which is why
    it is the registry index and never a position in a per-bar array.
    """

    stable_id: int
    source_token: str
    top: float
    bottom: float
    source_time: int
    distance: float


def _price_overlap(a: ZoneForDisplay, b: ZoneForDisplay) -> bool:
    """Inclusive interval intersection on price.

    Horizontal overlap is not tested. Every fresh zone projects to the right
    edge, so any two of them share horizontal space by construction and the
    price interval is the only discriminating axis. If bounded projection is
    ever reintroduced this is where the second condition belongs.
    """
    return a.bottom <= b.top and b.bottom <= a.top


def collision_groups(zones: Sequence[ZoneForDisplay]) -> list[list[int]]:
    """Connected components of zones whose annotations would overlap.

    Returns lists of indices into `zones`, each list sorted ascending, and the
    components ordered by their lowest member. Transitivity is deliberate: if A
    overlaps B and B overlaps C, all three share one annotation slot even when A
    and C do not touch, because B's text sits between them either way.

    Sorting by lower edge and sweeping would be O(n log n), but this layer runs
    over at most the visual capacity — eight groups by default — so the direct
    pairwise pass is both faster in practice and obviously correct.
    """
    n = len(zones)
    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[max(ra, rb)] = min(ra, rb)

    for i in range(n):
        for j in range(i + 1, n):
            if _price_overlap(zones[i], zones[j]):
                union(i, j)

    buckets: dict[int, list[int]] = {}
    for i in range(n):
        buckets.setdefault(find(i), []).append(i)
    return [sorted(v) for _, v in sorted(buckets.items())]


@dataclass(frozen=True)
class AnnotationDecision:
    """Which zones print their text, and which stay silent."""

    owners: frozenset[int]
    suppressed: frozenset[int]
    groups: tuple[tuple[int, ...], ...]


def _owner_key(z: ZoneForDisplay) -> tuple:
    """Presentation priority, in the author's stated order.

    Higher timeframe first, then nearer to price, then newer source, then the
    lowest stable id. This is a READABILITY ordering and carries no claim about
    trade quality: it decides whose text survives a pile-up, not whose setup is
    better. An unranked token sorts last rather than crashing, though release
    mode should already have filtered it out.
    """
    rank = timeframe_rank(z.source_token)
    return (
        -(rank if rank is not None else -1),
        z.distance,
        -z.source_time,
        z.stable_id,
    )


def resolve_annotations(zones: Sequence[ZoneForDisplay]) -> AnnotationDecision:
    """Pick exactly one annotation owner per collision group.

    Boxes are untouched. A suppressed zone keeps its rectangle, its geometry and
    its registry identity; it only stops drawing text, and the P7 table still
    lists it. Nothing is merged and nothing is deleted, which is what keeps this
    a presentation layer rather than a second grouping rule.
    """
    groups = collision_groups(zones)
    owners: set[int] = set()
    suppressed: set[int] = set()
    for group in groups:
        winner = min(group, key=lambda i: _owner_key(zones[i]))
        owners.add(winner)
        suppressed.update(i for i in group if i != winner)
    return AnnotationDecision(
        owners=frozenset(owners),
        suppressed=frozenset(suppressed),
        groups=tuple(tuple(g) for g in groups),
    )
