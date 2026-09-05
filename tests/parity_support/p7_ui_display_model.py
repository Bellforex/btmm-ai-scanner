"""An offline, pure-Python model of P7's per-bar display-array behavior:
clear-and-repopulate, the overflow ("N shown / M active") policy, and stable
ascending-index ordering.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics.

WHY THIS REUSES `resolve_eligible_and_next` RATHER THAN RE-DERIVING IT
------------------------------------------------------------------------
The set of POIs a bar is ELIGIBLE to evaluate (`not isTerminal or not
finalDone`) is not a P7 invention -- it is the already-frozen, already
22-test-proven P5 active-POI loop contract
(`p5_active_poi_loop_model.resolve_eligible_and_next`). P7 copies that exact
boolean into its own display arrays inside the SAME Pine loop iteration
(`array.push(p7PoiIdx, i)` etc., right after the P5EVAL log line) -- it does
not recompute eligibility a second time. So this module's job is narrower
and different: given the SAME eligible set the P5 loop already decided,
prove the DISPLAY layer (clear, repopulate, cap, order, render) behaves
correctly. Reusing `resolve_eligible_and_next` here means a change to the
real eligibility contract is caught by the ALREADY-existing P5 test suite,
not silently duplicated (and potentially drifting) in a second copy.

WHY INTEGER INDICES, NOT UUIDS
-----------------------------------
`resolve_eligible_and_next` is generic over any hashable ID. The real Pine
source's identity for a P7 display row is the raw P3 registry array index
(`array.push(p7PoiIdx, i)`, where `i` is the `for i = 0 to p5N - 1` loop
variable) -- not a UUID, and not sorted by availability time the way the
Python-side `_stable_order` orders POIs for `assess_confluence` calls. This
module therefore does NOT reuse `_stable_order`: Pine's own row order is the
simpler, different contract "ascending registry index", which is exactly
`sorted(eligible_ids)` on plain `int`s.
"""

from __future__ import annotations

from dataclasses import dataclass

from .p5_active_poi_loop_model import resolve_eligible_and_next

#: Mirrors `POI_TIER_BY_CODE`/`PERMISSION_CODE`/etc. in
#: `p5_wire_normalized_replay.py` -- the same wire-integer domains P7's own
#: `f_p7*Label` functions switch on. Duplicated as plain ints here (this
#: module has no dependency on that module) so a change to either is only
#: noticed through a differential, never silently inherited.
TIER_CODES: tuple[int, ...] = (0, 1, 2)  # NA, STANDARD, STRONG
ALIGN_CODES: tuple[int, ...] = (0, 1, 2, 3)  # ALIGNED, PARTIAL, NEUTRAL, COUNTER_TREND
PERMISSION_CODES: tuple[int, ...] = (0, 1, 2, 3, 4, 5)
LIFECYCLE_CODES: tuple[int, ...] = (1, 3, 4, 5, 6, 7)  # 0, 2 structurally unreachable, see P5 closure


@dataclass(frozen=True)
class PoiDecision:
    """One POI's already-computed P5 decision -- the same fields
    `array.push(p7Poi*, ...)` copies in the real Pine source, keyed by its
    P3 registry index."""

    idx: int
    poi_bullish: bool
    tier: int
    btmm_valid: bool
    align: int
    final_score: int
    permission: int
    lifecycle: int


@dataclass(frozen=True)
class BarRender:
    """One bar's rendered active-POI table: the rows actually drawn, plus
    the overflow-policy accounting."""

    active_count: int
    shown_count: int
    rows: tuple[PoiDecision, ...]
    footer: str


def render_bar(
    decisions_by_idx: dict[int, PoiDecision],
    eligible_ids: frozenset[int],
    max_visible: int,
) -> BarRender:
    """The render step alone: given ALREADY-CLEARED-AND-REPOPULATED arrays
    (i.e. `eligible_ids` IS this bar's full p7PoiIdx content, nothing more,
    nothing less), compute what the table shows. Ascending index order,
    first `max_visible` rows shown, footer reports the true total."""
    ordered = sorted(eligible_ids)
    active = len(ordered)
    shown = min(active, max_visible)
    rows = tuple(decisions_by_idx[i] for i in ordered[:shown])
    return BarRender(
        active_count=active,
        shown_count=shown,
        rows=rows,
        footer=f"{shown} shown / {active} active",
    )


class P7DisplayState:
    """Stateful, multi-bar simulation of the real Pine `var array<...>
    p7Poi*` declarations: `advance_bar` is the per-bar clear-then-repopulate
    step, mirroring `array.clear(p7PoiIdx)` (etc.) followed by the
    active-POI loop's `array.push` calls -- called once per confirmed bar,
    exactly like the real `if barstate.isconfirmed` block."""

    def __init__(self) -> None:
        self._previously_active: frozenset[int] = frozenset()

    def advance_bar(
        self,
        status_by_idx: dict[int, bool],  # idx -> is_terminal
        decisions_by_idx: dict[int, PoiDecision],
        *,
        known_ids: frozenset[int] | None = None,
        max_visible: int = 8,
    ) -> BarRender:
        # `resolve_eligible_and_next` takes a status->enum map; P7's own
        # source only ever reads the boolean `poiTerminal`, so this module
        # models status as that same boolean directly (True == terminal),
        # matching the real Pine `bool isTerminal = array.get(poiTerminal, i)`.
        from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

        terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
        non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
        status_map = {idx: (terminal if is_term else non_terminal) for idx, is_term in status_by_idx.items()}

        eligible, next_active = resolve_eligible_and_next(
            status_map, self._previously_active, known_ids=known_ids
        )
        self._previously_active = next_active
        # The "clear, then repopulate with exactly this bar's eligible set"
        # step -- there is no accumulation across bars in the correct model.
        return render_bar(decisions_by_idx, eligible, max_visible)


class _P7DisplayStateNoClear:
    """MUTANT: omits the array.clear() step, accumulating every bar's rows
    forever (the exact regression `array.clear` in the real source guards
    against). Used only to prove the test suite below would catch that
    mutation if it were ever introduced."""

    def __init__(self) -> None:
        self._previously_active: frozenset[int] = frozenset()
        self._accumulated: set[int] = set()

    def advance_bar(
        self,
        status_by_idx: dict[int, bool],
        decisions_by_idx: dict[int, PoiDecision],
        *,
        known_ids: frozenset[int] | None = None,
        max_visible: int = 8,
    ) -> BarRender:
        from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

        terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
        non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
        status_map = {idx: (terminal if is_term else non_terminal) for idx, is_term in status_by_idx.items()}

        eligible, next_active = resolve_eligible_and_next(
            status_map, self._previously_active, known_ids=known_ids
        )
        self._previously_active = next_active
        self._accumulated |= eligible  # BUG: never cleared
        return render_bar(decisions_by_idx, frozenset(self._accumulated), max_visible)


__all__ = [
    "ALIGN_CODES",
    "LIFECYCLE_CODES",
    "PERMISSION_CODES",
    "TIER_CODES",
    "BarRender",
    "P7DisplayState",
    "PoiDecision",
    "_P7DisplayStateNoClear",
    "render_bar",
]
