"""An offline, pure-Python model of P7-Z's POI-zone box/label lifecycle:
identity-stable creation, right-edge extension, terminal freeze, and
bounded-window eviction, built on top of the SAME eligibility and ordering
contracts `p7_ui_display_model.py` already proved for the P7 active-POI
table.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics.

WHY THIS REUSES `resolve_eligible_and_next` AND ASCENDING-INDEX ORDERING
-------------------------------------------------------------------------
P7-Z draws ONLY what the already-closed P3/P5/P7 engine already decided is
active — it introduces no second detector, no second eligibility rule, and
no new ranking. `resolve_eligible_and_next` (the frozen P5 active-loop
contract) and the plain `sorted(eligible_ids)` ascending-index order (P7's
own, unsorted, "stable order: ascending POI-registry index" convention,
`btmm_poi_btrc_scanner_p7_dev.pine:6040-6043`) are reused verbatim, exactly
as `p7_ui_display_model.render_bar` already does for the table. This
module's own, NEW job is narrower: given that same selected set, decide
which POIs get a box THIS bar, whether an existing box extends or freezes,
and which boxes must be torn down.

THE ADOPTED TERMINAL-RETENTION POLICY (V1) -- READ BEFORE CHANGING
-------------------------------------------------------------------------
`BTRC_V1_P7Z_POI_VISUALIZATION_CLOSURE.md` gives the full reasoning; the
short version: a POI leaves `resolve_eligible_and_next`'s eligible set
exactly one bar after it goes terminal (its "final pass" bar) — that is the
closed, frozen P5 loop contract, not something P7-Z may extend. Reusing
that same eligible set (as every phase of the P7-Z brief requires) therefore
means a terminal POI's box can be shown, frozen (not extended), for its one
final-pass bar, and is torn down the bar after, when the POI genuinely
leaves eligibility. Long-lived historical retention beyond that one-bar
grace would need P7-Z to remember geometry for POIs the engine itself has
already stopped tracking as active — a real, separate design decision,
deliberately deferred rather than invented silently here.

WHY LEFT EDGE = AVAILABILITY TIME, NOT CANDIDATE TIME
-------------------------------------------------------------------------
`poiCandTime` (the pattern's first source candle) precedes the bar the
scanner could have known the POI existed; `poiAvailTime` (== `poiConfirmTime`
for every production detector) is the bar the P3 registry itself creates
the entry. The one existing drawing precedent in this codebase (the P2
support/resistance box, `btmm_poi_btrc_scanner_p8_dev.pine:2172`) anchors
its left edge at `confirmationTime`, not the pattern's earlier source
candle. This module follows that same precedent for consistency and to
avoid ANY appearance of drawing a zone before the bar the engine actually
confirmed it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .p5_active_poi_loop_model import resolve_eligible_and_next

#: The 18 lifecycle-eligible P3 POI type codes and their V1 display labels
#: (`BTRC_V1_P7Z_POI_VISUALIZATION_CLOSURE.md` Phase 11 mapping), mirroring
#: `C_POI_*` in `btmm_poi_btrc_scanner_p8_dev.pine:2319-2336` exactly.
POI_TYPE_LABEL: dict[int, str] = {
    1: "BUY OB",
    2: "SELL OB",
    3: "BUY FVG",
    4: "SELL FVG",
    5: "B2S",
    6: "S2B",
    7: "BASE RALLY",
    8: "BASE DROP",
    9: "BULL PRESSURE",
    10: "BEAR PRESSURE",
    11: "BULL ENGULF",
    12: "BEAR ENGULF",
    13: "HAMMER",
    14: "SHOOTING STAR",
    15: "MORNING STAR",
    16: "EVENING STAR",
    17: "SUPPORT",
    18: "RESISTANCE",
}
UNKNOWN_TYPE_LABEL = "UNKNOWN"

DIRECTION_BULLISH = 1
DIRECTION_BEARISH = -1

TIER_NA = 0
TIER_STANDARD = 1
TIER_STRONG = 2


def type_label(poi_type: int) -> str:
    """Deterministic, total mapping — anything outside the closed 18-type
    core (including the liquidity/period-level types 19-32, which P7-Z does
    not visualize per the brief's explicit exclusion list) maps to
    `UNKNOWN_TYPE_LABEL`, never to a real POI name."""
    return POI_TYPE_LABEL.get(poi_type, UNKNOWN_TYPE_LABEL)


def zone_label(poi_type: int, tier: int, timeframe: str) -> str:
    """`"{TF} • {TYPE}"`, with `"• STRONG"` appended only for
    `TIER_STRONG`. `timeframe` is always the HOST chart timeframe: P3's POI
    registry carries no per-POI origin-timeframe field (P3 is single-
    timeframe by construction — see the closure doc's MTF section), so
    every POI's true origin timeframe IS the chart it was detected on."""
    label = f"{timeframe} • {type_label(poi_type)}"
    if tier == TIER_STRONG:
        label += " • STRONG"
    return label


@dataclass(frozen=True)
class PoiGeometry:
    """One POI's already-computed P3 registry fields — the same values
    `poiZoneTop`/`poiZoneBottom`/`poiAvailTime`/`poiType`/`poiDirection`/
    `poiTier` hold in the real Pine source, keyed by registry index."""

    idx: int
    poi_type: int
    direction: int
    zone_top: float
    zone_bottom: float
    avail_time_ms: int
    tier: int


@dataclass(frozen=True)
class ZoneBox:
    """One drawn (or about-to-be-drawn) box's full state — everything a
    Pine `box.new`/`box.set_right` pair needs, plus enough to prove
    identity, freeze, and eviction are all correct."""

    idx: int
    zone_top: float
    zone_bottom: float
    left_time_ms: int
    right_time_ms: int
    direction: int
    label_text: str
    frozen: bool  # true once the POI has gone terminal; right no longer moves


@dataclass(frozen=True)
class BarZoneRender:
    """One bar's zone-drawing outcome: what's shown, plus the exact
    create/update/remove bookkeeping a real `map<int, box>` must perform."""

    active_count: int
    shown_count: int
    boxes: tuple[ZoneBox, ...]
    created_ids: frozenset[int]
    updated_ids: frozenset[int]
    removed_ids: frozenset[int]


class P7ZDisplayState:
    """Stateful, multi-bar simulation of the real Pine `var map<int, box>` /
    `var map<int, label>` pair: `advance_bar` is the per-bar
    select-create-update-evict step, called once per confirmed bar."""

    def __init__(self, max_visible: int, timeframe: str = "M15") -> None:
        self._previously_active: frozenset[int] = frozenset()
        self._boxes: dict[int, ZoneBox] = {}
        self.max_visible = max_visible
        self.timeframe = timeframe

    def advance_bar(
        self,
        status_by_idx: dict[int, bool],  # idx -> is_terminal
        geometry_by_idx: dict[int, PoiGeometry],
        bar_time_ms: int,
        *,
        known_ids: frozenset[int] | None = None,
    ) -> BarZoneRender:
        from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

        terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
        non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
        status_map = {
            idx: (terminal if is_term else non_terminal)
            for idx, is_term in status_by_idx.items()
        }

        eligible, next_active = resolve_eligible_and_next(
            status_map, self._previously_active, known_ids=known_ids
        )
        self._previously_active = next_active

        ordered = sorted(eligible)
        active = len(ordered)
        shown = min(active, self.max_visible)
        selected = ordered[:shown]
        selected_ids = frozenset(selected)

        removed_ids = frozenset(self._boxes) - selected_ids
        for idx in removed_ids:
            del self._boxes[idx]

        created_ids: set[int] = set()
        updated_ids: set[int] = set()
        for idx in selected:
            geo = geometry_by_idx[idx]
            is_terminal_now = status_by_idx.get(idx, False)
            label = zone_label(geo.poi_type, geo.tier, self.timeframe)
            existing = self._boxes.get(idx)
            if existing is None:
                self._boxes[idx] = ZoneBox(
                    idx=idx,
                    zone_top=geo.zone_top,
                    zone_bottom=geo.zone_bottom,
                    left_time_ms=geo.avail_time_ms,
                    right_time_ms=bar_time_ms,
                    direction=geo.direction,
                    label_text=label,
                    frozen=is_terminal_now,
                )
                created_ids.add(idx)
            else:
                new_right = existing.right_time_ms if existing.frozen else bar_time_ms
                self._boxes[idx] = replace(
                    existing,
                    right_time_ms=new_right,
                    frozen=existing.frozen or is_terminal_now,
                    # Geometry/label are re-read every bar (matches the real
                    # loop re-reading the same arrays every bar) rather than
                    # frozen at creation, in case tier/type bookkeeping ever
                    # changes upstream -- direction/top/bottom/type do not
                    # actually mutate post-creation in the real registry, so
                    # this is a no-op in practice but not assumed here.
                    zone_top=geo.zone_top,
                    zone_bottom=geo.zone_bottom,
                    direction=geo.direction,
                    label_text=label,
                )
                updated_ids.add(idx)

        rows = tuple(self._boxes[i] for i in selected)
        return BarZoneRender(
            active_count=active,
            shown_count=shown,
            boxes=rows,
            created_ids=frozenset(created_ids),
            updated_ids=frozenset(updated_ids),
            removed_ids=removed_ids,
        )


class _P7ZDisplayStateNeverEvicts:
    """MUTANT: never removes a box once created (an unbounded object leak).
    Used only to prove the test suite would catch that mutation."""

    def __init__(self, max_visible: int, timeframe: str = "M15") -> None:
        self._previously_active: frozenset[int] = frozenset()
        self._boxes: dict[int, ZoneBox] = {}
        self.max_visible = max_visible
        self.timeframe = timeframe

    def advance_bar(
        self,
        status_by_idx: dict[int, bool],
        geometry_by_idx: dict[int, PoiGeometry],
        bar_time_ms: int,
        *,
        known_ids: frozenset[int] | None = None,
    ) -> BarZoneRender:
        from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

        terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
        non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
        status_map = {
            idx: (terminal if is_term else non_terminal)
            for idx, is_term in status_by_idx.items()
        }
        eligible, next_active = resolve_eligible_and_next(
            status_map, self._previously_active, known_ids=known_ids
        )
        self._previously_active = next_active
        ordered = sorted(eligible)
        active = len(ordered)
        shown = min(active, self.max_visible)
        selected = ordered[:shown]
        for idx in selected:
            if idx not in self._boxes:
                geo = geometry_by_idx[idx]
                self._boxes[idx] = ZoneBox(
                    idx=idx,
                    zone_top=geo.zone_top,
                    zone_bottom=geo.zone_bottom,
                    left_time_ms=geo.avail_time_ms,
                    right_time_ms=bar_time_ms,
                    direction=geo.direction,
                    label_text=zone_label(geo.poi_type, geo.tier, self.timeframe),
                    frozen=status_by_idx.get(idx, False),
                )
        # BUG: nothing is ever removed from self._boxes.
        rows = tuple(self._boxes[i] for i in selected)
        return BarZoneRender(
            active_count=active,
            shown_count=shown,
            boxes=rows,
            created_ids=frozenset(),
            updated_ids=frozenset(),
            removed_ids=frozenset(),
        )


class _P7ZDisplayStateUsesCapAsEligibility:
    """MUTANT: applies `max_visible` INSIDE the eligibility computation
    (i.e. lets the display cap limit what's considered active), the exact
    defect Phase 3/21 forbid. Used only to prove the test suite would catch
    it."""

    def __init__(self, max_visible: int, timeframe: str = "M15") -> None:
        self._previously_active: frozenset[int] = frozenset()
        self.max_visible = max_visible
        self.timeframe = timeframe

    def advance_bar(
        self,
        status_by_idx: dict[int, bool],
        geometry_by_idx: dict[int, PoiGeometry],
        bar_time_ms: int,
        *,
        known_ids: frozenset[int] | None = None,
    ) -> tuple[BarZoneRender, int]:
        """Returns `(render, engine_active_count)` — the mutant's bug is
        visible only by comparing the two: a correct implementation's
        engine_active_count is unaffected by `max_visible`."""
        from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

        terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
        non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
        status_map = {
            idx: (terminal if is_term else non_terminal)
            for idx, is_term in status_by_idx.items()
        }
        eligible, next_active = resolve_eligible_and_next(
            status_map, self._previously_active, known_ids=known_ids
        )
        # BUG: truncate the ELIGIBLE (engine) set itself, not just display.
        truncated_eligible = frozenset(sorted(eligible)[: self.max_visible])
        self._previously_active = frozenset(next_active & truncated_eligible)
        ordered = sorted(truncated_eligible)
        rows = tuple(
            ZoneBox(
                idx=i,
                zone_top=geometry_by_idx[i].zone_top,
                zone_bottom=geometry_by_idx[i].zone_bottom,
                left_time_ms=geometry_by_idx[i].avail_time_ms,
                right_time_ms=bar_time_ms,
                direction=geometry_by_idx[i].direction,
                label_text=zone_label(
                    geometry_by_idx[i].poi_type, geometry_by_idx[i].tier, self.timeframe
                ),
                frozen=status_by_idx.get(i, False),
            )
            for i in ordered
        )
        return (
            BarZoneRender(
                active_count=len(truncated_eligible),
                shown_count=len(rows),
                boxes=rows,
                created_ids=frozenset(),
                updated_ids=frozenset(),
                removed_ids=frozenset(),
            ),
            len(eligible),  # the TRUE engine-eligible count, for comparison
        )


__all__ = [
    "DIRECTION_BEARISH",
    "DIRECTION_BULLISH",
    "POI_TYPE_LABEL",
    "TIER_NA",
    "TIER_STANDARD",
    "TIER_STRONG",
    "UNKNOWN_TYPE_LABEL",
    "BarZoneRender",
    "P7ZDisplayState",
    "PoiGeometry",
    "ZoneBox",
    "_P7ZDisplayStateNeverEvicts",
    "_P7ZDisplayStateUsesCapAsEligibility",
    "type_label",
    "zone_label",
]


# =========================================================================
# RC1-POI CORRECTIVE — PROXIMITY-TO-CURRENT-PRICE DISPLAY SELECTION
# =========================================================================
# PRESENTATION ONLY. This selects which of the ALREADY-ACTIVE POIs get a
# drawn box; it does not create, retire, re-rank, score, or filter any POI.
# The engine universe is untouched: the active registry, the P5 evaluation
# loop and P8 monitoring all continue to see EVERY active POI. Only the
# bounded set handed to `box.new` changes.
#
# WHY THIS EXISTS: the frozen RC1 rule is `sorted(eligible)[:capacity]` --
# ascending registry index, i.e. the OLDEST surviving POIs. P3 has no
# expiry, so after ~1800 bars of price drift those oldest POIs sit many ATR
# away from current price and the trader sees no zones near the market even
# though ~157 are active. Measured on the frozen FXCM M15 capture
# (anchor 1788267600000, close 4329.33, ATR14 11.78): the 12 displayed POIs
# were 199.01-259.06 away (~17-22 ATR) while 4 active POIs CONTAINED price;
# overlap between the displayed 12 and the nearest 12 was ZERO.
#
# This is NOT POI quality scoring, trade ranking, BTRC ranking or signal
# ranking -- distance to current price carries no directional or quality
# meaning here, it is purely "is this zone on the trader's screen".


def zone_distance(close: float, zone_top: float, zone_bottom: float) -> float:
    """Author-frozen zone distance: 0 when price is INSIDE the zone,
    otherwise the gap to the NEAREST boundary.

    Nearest-boundary, deliberately NOT midpoint: a wide zone containing
    price must rank ahead of a narrow zone price has not reached, and
    midpoint distance would invert exactly that case."""
    if close < zone_bottom:
        return zone_bottom - close
    if close > zone_top:
        return close - zone_top
    return 0.0


def select_nearest(
    eligible: frozenset[int] | set[int] | list[int],
    geometry_by_idx: dict[int, PoiGeometry],
    close: float,
    capacity: int,
) -> list[int]:
    """The proposed P7-Z display selection: the `capacity` active POIs
    nearest current price, ascending distance.

    TIEBREAK (frozen): equal distance falls back to ascending registry
    index -- the SAME canonical stable POI ordering P7 already uses. No
    tier, BTRC, BTMM or timeframe weighting is introduced."""
    ordered = sorted(
        eligible,
        key=lambda idx: (
            zone_distance(
                close,
                geometry_by_idx[idx].zone_top,
                geometry_by_idx[idx].zone_bottom,
            ),
            idx,
        ),
    )
    return ordered[: min(len(ordered), capacity)]


def select_registry_order(
    eligible: frozenset[int] | set[int] | list[int],
    geometry_by_idx: dict[int, PoiGeometry],
    close: float,
    capacity: int,
) -> list[int]:
    """The FROZEN RC1 rule, kept verbatim as the differential baseline the
    corrective is measured against. `close`/`geometry_by_idx` are accepted
    and ignored -- that ignoring IS the defect."""
    ordered = sorted(eligible)
    return ordered[: min(len(ordered), capacity)]


# ---- mutants of the NEW rule, used only to prove the new tests bite -------


def _select_first_n(eligible, geometry_by_idx, close, capacity):
    """MUTANT: first N registry entries (this is literally frozen RC1)."""
    return sorted(eligible)[:capacity]


def _select_last_n(eligible, geometry_by_idx, close, capacity):
    """MUTANT: last N registry entries (newest, not nearest)."""
    ordered = sorted(eligible)
    return ordered[-capacity:] if capacity <= len(ordered) else ordered


def _select_midpoint_distance(eligible, geometry_by_idx, close, capacity):
    """MUTANT: rank by distance to zone MIDPOINT instead of nearest
    boundary -- silently demotes wide zones that already contain price."""

    def mid(idx: int) -> float:
        g = geometry_by_idx[idx]
        return abs(close - (g.zone_top + g.zone_bottom) / 2.0)

    return sorted(eligible, key=lambda i: (mid(i), i))[:capacity]


# =========================================================================
# RC1-POI-V2 — TIMEFRAME LABEL CONTRACT
# =========================================================================
# Pine's `timeframe.period` is a RAW token: "1", "5", "15", "60", "D", "W".
# Rendering it directly produced labels like "1 • BUY FVG" on an M1 chart,
# which reads as a quantity rather than a timeframe. The frozen user-facing
# vocabulary is M1/M5/M15/H1/H4/D1/W1, so the raw token is formatted here.
# Presentation only: no POI carries an origin-timeframe field, so this is
# always the HOST chart timeframe, exactly as `zone_label` already assumed.

UNKNOWN_TF_LABEL = "TF?"


def timeframe_label(period: str) -> str:
    """Pine `timeframe.period` -> frozen user-facing timeframe token.

    Minutes below an hour become M<n>; whole hours below a day become H<n>;
    the calendar tokens map to D1/W1/MN1; a trailing "S" is seconds."""
    if period is None:
        return UNKNOWN_TF_LABEL
    p = period.strip().upper()
    if not p:
        return UNKNOWN_TF_LABEL
    if p == "D":
        return "D1"
    if p == "W":
        return "W1"
    if p == "M":
        return "MN1"
    if p.endswith("S") and p[:-1].isdigit():
        return f"S{int(p[:-1])}"
    if p.endswith("D") and p[:-1].isdigit():
        return f"D{int(p[:-1])}"
    if p.endswith("W") and p[:-1].isdigit():
        return f"W{int(p[:-1])}"
    if p.endswith("M") and p[:-1].isdigit():
        return f"MN{int(p[:-1])}"
    if p.isdigit():
        minutes = int(p)
        if minutes <= 0:
            return UNKNOWN_TF_LABEL
        if minutes < 60:
            return f"M{minutes}"
        if minutes < 1440 and minutes % 60 == 0:
            return f"H{minutes // 60}"
        if minutes == 1440:
            return "D1"
        return f"M{minutes}"
    return UNKNOWN_TF_LABEL


def zone_label_v2(poi_type: int, tier: int, period: str) -> str:
    """`zone_label` with the raw Pine period formatted first. This is the
    label the RC1-POI-V2 corrective renders."""
    return zone_label(poi_type, tier, timeframe_label(period))


# =========================================================================
# RC1-POI-V2 — EXACT-GEOMETRY VISUAL DEDUPLICATION (presentation only)
# =========================================================================
# Measured on the live FX:XAUUSD M1 capture of 2026-09-09 (258 POIs): 28
# groups of POIs share IDENTICAL top/bottom/availability/direction, covering
# 56 registry entries. Drawing all 56 stacks two identical rectangles per
# group for no information gain. Typical pairs are BUY OB + BULL ENGULF (the
# order block and the engulfing both anchor on the same origin candle) and
# HAMMER + BULL PRESSURE.
#
# Registry identity is NOT merged: P3, P5 and P8 continue to see every POI
# separately. Only the DRAWN object count collapses, and the label names
# every contributing type so nothing is hidden from the trader.


def geometry_key(geo: PoiGeometry) -> tuple:
    """Two POIs share a drawn box only when all four match exactly. Type is
    deliberately excluded -- differing types is the whole point -- and so is
    tier, which only decorates the label."""
    return (geo.zone_top, geo.zone_bottom, geo.avail_time_ms, geo.direction)


def group_exact_duplicates(
    selected: list[int], geometry_by_idx: dict[int, PoiGeometry]
) -> list[list[int]]:
    """Collapse an ordered selection into groups of exact-geometry twins.

    Group order follows the FIRST appearance of each key in `selected`, and
    members keep `selected`'s order, so the result is a deterministic
    function of the proximity ordering that produced it."""
    order: list[tuple] = []
    members: dict[tuple, list[int]] = {}
    for idx in selected:
        key = geometry_key(geometry_by_idx[idx])
        if key not in members:
            members[key] = []
            order.append(key)
        members[key].append(idx)
    return [members[key] for key in order]


def combined_zone_label(
    group: list[int], geometry_by_idx: dict[int, PoiGeometry], period: str
) -> str:
    """One label for a merged box: `"M1 • BUY OB + BULL ENGULF"`.

    Type names appear in the group's own order with duplicates removed, so a
    group is labelled identically however many POIs share the geometry. The
    STRONG suffix is applied when ANY contributing POI is strong, since the
    box represents all of them."""
    names: list[str] = []
    strong = False
    for idx in group:
        geo = geometry_by_idx[idx]
        name = type_label(geo.poi_type)
        if name not in names:
            names.append(name)
        if geo.tier == TIER_STRONG:
            strong = True
    label = f"{timeframe_label(period)} • {' + '.join(names)}"
    return label + " • STRONG" if strong else label


# =========================================================================
# RC1-POI-V2 — FVG VISUAL CLUSTERING (presentation only, author-authorized)
# =========================================================================
# P3 correctly detects several distinct FVGs in one price area. They stay
# distinct in P3/P5/P8 and in the registry; only the DRAWN objects group.
#
# A cluster requires ALL of: FVG family, same direction, same origin
# timeframe, simultaneously eligible, and price intervals that OVERLAP OR
# TOUCH. Membership is transitive (connected components), so A-B and B-C
# put A, B and C in one cluster even when A and C do not themselves touch.
#
# Cluster geometry is the ENVELOPE of its members -- min bottom, max top,
# earliest member origin. Never an average, never a midpoint-derived
# synthetic zone.

FVG_TYPES = frozenset({3, 4})  # BUY_FAIR_VALUE_GAP, SELL_FAIR_VALUE_GAP


def _touches_or_overlaps(a: PoiGeometry, b: PoiGeometry) -> bool:
    """Closed-interval intersection: touching at a single price counts."""
    return a.zone_bottom <= b.zone_top and b.zone_bottom <= a.zone_top


def fvg_connected_components(
    members: list[int], geometry_by_idx: dict[int, PoiGeometry]
) -> list[list[int]]:
    """Transitive overlap-or-touch grouping of same-direction FVGs.

    `members` must already be one direction and one timeframe. Each component
    is internally sorted, so MEMBERSHIP is a pure function of geometry.

    NOTE: the ORDER of the returned components follows internal union-find
    root ids and is NOT contracted. A root is not always a component's lowest
    member: merging b into a sets `parent[find(b)] = find(a)`, so an
    already-merged smaller root can be re-parented under a larger one.
    Callers must not depend on this order -- `build_visual_groups` re-sorts
    every group by (distance, lowest member). `fvg_components_sweep` does
    guarantee lowest-member order."""
    ordered = sorted(members)
    parent = {i: i for i in ordered}

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a_pos, a in enumerate(ordered):
        for b in ordered[a_pos + 1 :]:
            if _touches_or_overlaps(geometry_by_idx[a], geometry_by_idx[b]):
                ra, rb = find(a), find(b)
                if ra != rb:
                    parent[rb] = ra

    buckets: dict[int, list[int]] = {}
    for i in ordered:
        buckets.setdefault(find(i), []).append(i)
    return [sorted(v) for _, v in sorted(buckets.items())]


def cluster_geometry(
    group: list[int], geometry_by_idx: dict[int, PoiGeometry]
) -> tuple[float, float, int]:
    """(top, bottom, left_time) envelope of a visual group. No averaging."""
    tops = [geometry_by_idx[i].zone_top for i in group]
    bottoms = [geometry_by_idx[i].zone_bottom for i in group]
    lefts = [geometry_by_idx[i].avail_time_ms for i in group]
    return (max(tops), min(bottoms), min(lefts))


def fvg_cluster_label(
    group: list[int], geometry_by_idx: dict[int, PoiGeometry], period: str
) -> str:
    """`"M1 • BUY FVG"`, or `"M1 • BUY FVG ×3"` for a multi-member cluster.
    Registry ids are deliberately absent from normal UI text."""
    name = type_label(geometry_by_idx[group[0]].poi_type)
    base = f"{timeframe_label(period)} • {name}"
    return base if len(group) == 1 else f"{base} ×{len(group)}"


def build_visual_groups(
    active: list[int] | frozenset[int],
    geometry_by_idx: dict[int, PoiGeometry],
    close: float,
    capacity: int,
    period: str,
) -> list[dict]:
    """The full V2 presentation projection.

    Grouping runs over the WHOLE active set before capacity is applied, so a
    cluster can never be split by the display cut. Groups are then ordered by
    their nearest member's distance to `close` (ties by lowest registry
    index) and the first `capacity` GROUPS are drawn -- capacity counts
    visual groups, not semantic POIs, so a 4-member FVG cluster costs one
    slot."""
    ids = sorted(active)
    groups: list[list[int]] = []

    # FVG family: connected components, partitioned by direction.
    for direction in (DIRECTION_BULLISH, DIRECTION_BEARISH):
        fam = [
            i
            for i in ids
            if geometry_by_idx[i].poi_type in FVG_TYPES
            and geometry_by_idx[i].direction == direction
        ]
        groups.extend(fvg_connected_components(fam, geometry_by_idx))

    # everything else: exact-geometry duplicates only (no overlap merging).
    non_fvg = [i for i in ids if geometry_by_idx[i].poi_type not in FVG_TYPES]
    groups.extend(group_exact_duplicates(non_fvg, geometry_by_idx))

    out = []
    for group in groups:
        top, bottom, left = cluster_geometry(group, geometry_by_idx)
        dist = min(
            zone_distance(
                close, geometry_by_idx[i].zone_top, geometry_by_idx[i].zone_bottom
            )
            for i in group
        )
        is_fvg = geometry_by_idx[group[0]].poi_type in FVG_TYPES
        label = (
            fvg_cluster_label(group, geometry_by_idx, period)
            if is_fvg
            else combined_zone_label(group, geometry_by_idx, period)
        )
        out.append(
            {
                "members": group,
                "top": top,
                "bottom": bottom,
                "left_time_ms": left,
                "direction": geometry_by_idx[group[0]].direction,
                "label": label,
                "distance": dist,
            }
        )

    out.sort(key=lambda g: (g["distance"], min(g["members"])))
    return out[: min(capacity, len(out))]


# =========================================================================
# RC1-POI-V2 HOTFIX — OPTIMIZED PRESENTATION PROJECTION (SORT + SWEEP)
# =========================================================================
# WHY: the V2 grouping ran inside `if barstate.isconfirmed`, so it executed on
# EVERY confirmed bar -- roughly 1800 times per full recalculation, not once.
# Its envelope-growth closure is O(n^2) in the active-POI count, and on M5
# (1800 bars spanning ~6.25 days of structure, so a far larger active
# population than M1's 30 hours) that exceeded TradingView's 20-second
# execution budget and raised RE10110, leaving the study drawing nothing.
#
# The fix must NOT bound the active set before grouping: a seemingly distant
# FVG can connect transitively through overlapping neighbours, so truncating
# first can change component membership, geometry, distance and the final
# top-K selection.
#
# Instead: partition -> sort -> sweep. Sorting by lower edge and sweeping with
# a running maximum upper edge is the classic interval-merge, and it computes
# exactly the same connected components as union-find over overlap-or-touch,
# in O(n log n) instead of O(n^2).
#
# `OpCount` is diagnostic only. Semantic equality with the frozen oracle is
# the gate.


class OpCount:
    """Counts the comparisons each implementation actually performs."""

    def __init__(self) -> None:
        self.compares = 0
        self.sorts = 0


def fvg_components_sweep(
    members: list[int],
    geometry_by_idx: dict[int, PoiGeometry],
    ops: OpCount | None = None,
) -> list[list[int]]:
    """Sort-and-sweep equivalent of `fvg_connected_components`.

    `members` must already be one direction and one timeframe. Returns
    components ordered by lowest registry index, each internally sorted, so
    the result is identical to the union-find oracle's."""
    if not members:
        return []
    ordered = sorted(
        members,
        key=lambda i: (
            geometry_by_idx[i].zone_bottom,
            geometry_by_idx[i].zone_top,
            i,
        ),
    )
    if ops is not None:
        ops.sorts += 1

    comps: list[list[int]] = []
    current = [ordered[0]]
    current_top = geometry_by_idx[ordered[0]].zone_top
    for idx in ordered[1:]:
        geo = geometry_by_idx[idx]
        if ops is not None:
            ops.compares += 1
        if geo.zone_bottom <= current_top:
            # overlaps or touches the running component envelope
            current.append(idx)
            if geo.zone_top > current_top:
                current_top = geo.zone_top
        else:
            comps.append(sorted(current))
            current = [idx]
            current_top = geo.zone_top
    comps.append(sorted(current))
    return sorted(comps, key=lambda c: c[0])


def group_exact_duplicates_keyed(
    selected: list[int],
    geometry_by_idx: dict[int, PoiGeometry],
    ops: OpCount | None = None,
) -> list[list[int]]:
    """Hash-keyed equivalent of `group_exact_duplicates` -- O(n), no
    all-pairs scan. Group order follows first appearance, members keep input
    order, exactly as the oracle does."""
    order: list[tuple] = []
    members: dict[tuple, list[int]] = {}
    for idx in selected:
        key = geometry_key(geometry_by_idx[idx])
        if ops is not None:
            ops.compares += 1
        if key not in members:
            members[key] = []
            order.append(key)
        members[key].append(idx)
    return [members[key] for key in order]


def build_visual_groups_fast(
    active: list[int] | frozenset[int],
    geometry_by_idx: dict[int, PoiGeometry],
    close: float,
    capacity: int,
    period: str,
    ops: OpCount | None = None,
) -> list[dict]:
    """Optimized twin of `build_visual_groups`. Must match it exactly.

    Grouping still runs over the WHOLE active set before capacity is applied;
    only the algorithm changed, never the contract."""
    ids = sorted(active)
    groups: list[list[int]] = []

    for direction in (DIRECTION_BULLISH, DIRECTION_BEARISH):
        fam = [
            i
            for i in ids
            if geometry_by_idx[i].poi_type in FVG_TYPES
            and geometry_by_idx[i].direction == direction
        ]
        groups.extend(fvg_components_sweep(fam, geometry_by_idx, ops))

    non_fvg = [i for i in ids if geometry_by_idx[i].poi_type not in FVG_TYPES]
    groups.extend(group_exact_duplicates_keyed(non_fvg, geometry_by_idx, ops))

    out = []
    for group in groups:
        top, bottom, left = cluster_geometry(group, geometry_by_idx)
        dist = min(
            zone_distance(
                close, geometry_by_idx[i].zone_top, geometry_by_idx[i].zone_bottom
            )
            for i in group
        )
        is_fvg = geometry_by_idx[group[0]].poi_type in FVG_TYPES
        label = (
            fvg_cluster_label(group, geometry_by_idx, period)
            if is_fvg
            else combined_zone_label(group, geometry_by_idx, period)
        )
        out.append(
            {
                "members": group,
                "top": top,
                "bottom": bottom,
                "left_time_ms": left,
                "direction": geometry_by_idx[group[0]].direction,
                "label": label,
                "distance": dist,
            }
        )

    out.sort(key=lambda g: (g["distance"], min(g["members"])))
    return out[: min(capacity, len(out))]
