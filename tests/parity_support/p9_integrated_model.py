"""P9 — the full-system integration harness: one canonical per-bar,
per-POI record (`P9Record`) combining P3's static fields, P5's dynamic
per-bar state, P7's table-visibility flag, P7-Z's zone-visibility flag, and
P8's fired event types for that exact POI.

THIS DOES NOT DUPLICATE ANY SEMANTIC ENGINE
--------------------------------------------------------------------------
Every sub-decision here is delegated to the SAME already-closed, already-
tested module the real system already ports from Pine line-for-line:

- `p5_active_poi_loop_model.resolve_eligible_and_next` (via the three
  sub-models below, each calling it independently but on the SAME inputs
  every bar -- a pure function called three times with identical arguments
  produces identical results, so this is reuse, not drift risk)
- `p7_ui_display_model.P7DisplayState` — the P7 active-POI table's own
  clear/repopulate/cap/order contract
- `p7z_zone_model.P7ZDisplayState` — the P7-Z zone box/label lifecycle
- `p8_alert_oracle.AlertEngine` — the P8 event oracle

This module's own, NEW job is narrower: given one bar's already-computed
per-POI state (`P9BarInput`, the same fields a real `P5EVAL` log line
already carries plus the P3-only geometry fields `P5EVAL` never needed),
adapt that ONE shared input into each sub-model's own expected shape, run
all three, and fold the results into one canonical `P9Record` per POI.

WHY inputs_by_idx MAY CONTAIN POIs THAT ARE NOT ELIGIBLE THIS BAR
--------------------------------------------------------------------------
`P9IntegratedState.advance_bar` iterates and emits a record for every key
in `inputs_by_idx`, not just the sub-models' own computed eligible sets.
This is deliberate: a POI that has already exited eligibility (its final
pass happened on an earlier bar) can still be passed in, and the resulting
record's `p7_visible=False, p7z_visible=False, event_types=()` is itself a
real, testable invariant (Phase 16's "a POI not visually selected may
still correctly alert" and Phase 11's "excluded from active universe next
bar" both need exactly this shape of assertion).
"""

from __future__ import annotations

from dataclasses import dataclass

from .p5_active_poi_loop_model import resolve_eligible_and_next
from .p7_ui_display_model import P7DisplayState
from .p7_ui_display_model import PoiDecision as P7PoiDecision
from .p7z_zone_model import P7ZDisplayState
from .p7z_zone_model import PoiGeometry as P7ZPoiGeometry
from .p8_alert_oracle import AlertEngine, BarSnapshot
from .p8_alert_oracle import PoiSnapshot as P8PoiSnapshot

DIRECTION_BULLISH = 1
DIRECTION_BEARISH = -1


@dataclass(frozen=True)
class P9BarInput:
    """One POI's full already-computed state for one bar — the union of
    P3's static registry fields and P5's per-bar dynamic output. Every
    field here is something a real `P5EVAL` log line (or, for the four
    P3-only geometry fields, the P3 registry itself) already carries; none
    is computed by this module."""

    idx: int
    poi_type: int
    direction: int
    zone_top: float
    zone_bottom: float
    avail_time_ms: int
    tier: int
    terminal: bool
    btmm_valid: bool
    align: int
    final_score: int
    permission: int
    lifecycle: int


@dataclass(frozen=True)
class P9Record:
    """One canonical, cross-layer system record: everything Phase 3/4's
    static+dynamic field contract and the Phase 2 system question (Q1-Q8)
    need to answer for one POI on one bar."""

    bar_ms: int
    idx: int
    poi_type: int
    direction: int
    origin_tf: str
    zone_top: float
    zone_bottom: float
    avail_time_ms: int
    terminal: bool
    btmm_valid: bool
    final_score: int
    permission: int
    lifecycle: int
    p7_visible: bool
    p7z_visible: bool
    event_types: tuple[str, ...]


class P9IntegratedState:
    """Stateful, multi-bar orchestration of the three sub-models. One
    instance per host context — a host-timeframe switch gets a fresh
    instance, exactly like a real Pine attach/reload/remove-readd
    reinitializes every `var` identically (the same property this whole
    campaign has already exploited for P7/P7-Z/P8)."""

    def __init__(
        self, p7_max_visible: int = 8, p7z_max_visible: int = 12, timeframe: str = "M15"
    ) -> None:
        self._p7 = P7DisplayState()
        self._p7z = P7ZDisplayState(max_visible=p7z_max_visible, timeframe=timeframe)
        self._alerts = AlertEngine()
        self._p7_max_visible = p7_max_visible
        self._timeframe = timeframe
        self._primed = False

    @property
    def primed(self) -> bool:
        return self._primed

    def advance_bar(
        self,
        bar_ms: int,
        inputs_by_idx: dict[int, P9BarInput],
        *,
        known_ids: frozenset[int] | None = None,
    ) -> tuple[P9Record, ...]:
        status_by_idx = {idx: inp.terminal for idx, inp in inputs_by_idx.items()}

        p7_decisions = {
            idx: P7PoiDecision(
                idx=idx,
                poi_bullish=inp.direction == DIRECTION_BULLISH,
                tier=inp.tier,
                btmm_valid=inp.btmm_valid,
                align=inp.align,
                final_score=inp.final_score,
                permission=inp.permission,
                lifecycle=inp.lifecycle,
            )
            for idx, inp in inputs_by_idx.items()
        }
        p7_render = self._p7.advance_bar(
            status_by_idx,
            p7_decisions,
            known_ids=known_ids,
            max_visible=self._p7_max_visible,
        )
        p7_visible_ids = {row.idx for row in p7_render.rows}

        p7z_geometry = {
            idx: P7ZPoiGeometry(
                idx=idx,
                poi_type=inp.poi_type,
                direction=inp.direction,
                zone_top=inp.zone_top,
                zone_bottom=inp.zone_bottom,
                avail_time_ms=inp.avail_time_ms,
                tier=inp.tier,
            )
            for idx, inp in inputs_by_idx.items()
        }
        p7z_render = self._p7z.advance_bar(
            status_by_idx, p7z_geometry, bar_ms, known_ids=known_ids
        )
        p7z_visible_ids = {box.idx for box in p7z_render.boxes}

        snapshot = BarSnapshot(
            bar_ms=bar_ms,
            pois=tuple(
                P8PoiSnapshot(
                    poi_idx=idx,
                    poi_bullish=inp.direction == DIRECTION_BULLISH,
                    tier=inp.tier,
                    terminal=inp.terminal,
                    btmm_valid=inp.btmm_valid,
                    permission=inp.permission,
                    lifecycle=inp.lifecycle,
                )
                for idx, inp in inputs_by_idx.items()
            ),
        )
        if not self._primed:
            self._alerts.prime(snapshot)
            events = []
            self._primed = True
        else:
            events = self._alerts.process(snapshot)

        events_by_idx: dict[int, list[str]] = {}
        for e in events:
            events_by_idx.setdefault(e.poi_idx, []).append(e.event_type.value)

        records = []
        for idx in sorted(inputs_by_idx):
            inp = inputs_by_idx[idx]
            records.append(
                P9Record(
                    bar_ms=bar_ms,
                    idx=idx,
                    poi_type=inp.poi_type,
                    direction=inp.direction,
                    origin_tf=self._timeframe,
                    zone_top=inp.zone_top,
                    zone_bottom=inp.zone_bottom,
                    avail_time_ms=inp.avail_time_ms,
                    terminal=inp.terminal,
                    btmm_valid=inp.btmm_valid,
                    final_score=inp.final_score,
                    permission=inp.permission,
                    lifecycle=inp.lifecycle,
                    p7_visible=idx in p7_visible_ids,
                    p7z_visible=idx in p7z_visible_ids,
                    event_types=tuple(events_by_idx.get(idx, [])),
                )
            )
        return tuple(records)


def resolve_eligible_ids(
    status_by_idx: dict[int, bool],
    previously_active: frozenset[int],
    known_ids: frozenset[int] | None = None,
) -> frozenset[int]:
    """Convenience re-export of the frozen P5 eligibility rule, adapted to
    the plain-bool `is_terminal` shape every sub-model here already uses --
    for tests that want to assert the TRUE engine-eligible set independent
    of any single sub-model's own internal bookkeeping."""
    from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

    terminal = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED
    non_terminal = PoiLifecycleStatus.NOT_APPLICABLE
    status_map = {
        idx: (terminal if is_term else non_terminal)
        for idx, is_term in status_by_idx.items()
    }
    eligible, _next_active = resolve_eligible_and_next(
        status_map, previously_active, known_ids=known_ids
    )
    return eligible


__all__ = [
    "DIRECTION_BEARISH",
    "DIRECTION_BULLISH",
    "P9BarInput",
    "P9IntegratedState",
    "P9Record",
    "resolve_eligible_ids",
]
