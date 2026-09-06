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
