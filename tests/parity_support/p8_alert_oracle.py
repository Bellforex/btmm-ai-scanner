"""P8 alert oracle: a pure-Python, stateful event detector over closed
P5/P7 per-bar, per-POI decision snapshots.

Test/parity tooling only — nothing in `src/` imports this, and it changes
no production semantics. This module NEVER recomputes trend, regime,
momentum, breakout, pullback, session, volatility, BTMM validity, POI
tier/status, score, permission, or lifecycle — it only compares
already-computed values across consecutive bars to detect the five V1
transitions authorized in `BTRC_V1_P8_ALERT_READINESS.md`.

WHY THIS IS A SEPARATE ENGINE FROM P5/P7, NOT A SECOND COPY OF ONE
------------------------------------------------------------------------
`BarSnapshot`/`PoiSnapshot` carry exactly the fields the closed active-POI
loop already produces per POI per bar (the same fields `P5EVAL` already
logs: `poiIdx`, `poiDir`, `poiTier`, `poiTerminal`, `btmmValid`,
`permission`, `lifecycle`). `AlertEngine` holds ONLY alert-dedup state
(previous-bar values, per-POI "already alerted" flags) — never a second
copy of the P3/P4/P5 registries themselves.

THE FIVE V1 EVENT TYPES, AND WHY EACH TRIGGER WAS CHOSEN
------------------------------------------------------------------
* `POI_ACTIVATED` — a POI index enters this engine's known set for the
  first time. In the closed P3/P5 architecture, "created" and "first
  eligible for P5 evaluation" are the SAME moment: `GENUINE_INVALIDATION_
  CONFIRMED` (the only terminal status) is never a POI's initial status,
  so `not isTerminal` is trivially true the instant any POI is registered
  — there is no separate "dormant then later activated" state to
  distinguish (see `BTRC_V1_P8_ALERT_READINESS.md` Section on A1). This
  oracle therefore has no separate "created" concept to invent.
* `BTMM_VALIDATED` — `btmmValid` (i.e. `btmmSetupByPoi[i] != -1`, exactly
  what P5/P7's own confluence code already means by "valid") transitions
  `False -> True` for that POI. Never the deferred, unreachable
  `C_BTMM_ST_CONFIRMED` state (readiness audit Section 4).
* `PERMISSION_ENTERED_ACTIONABLE` / `PERMISSION_LOST_ACTIONABLE` —
  `permission` transitions into / out of `{BUY_BIAS, SELL_BIAS}`
  (`ACTIONABLE_PERMISSIONS` below). A direct `BUY_BIAS -> SELL_BIAS`
  transition deliberately produces NEITHER event under this policy: it is
  a direction change, not an entry into or exit from the actionable set
  (both endpoints ARE the actionable set) — V1 has no "direction changed"
  event, and inventing one by firing both LOST and ENTERED on the same
  bar would double-notify for a single semantic transition. See
  `test_direct_actionable_direction_change_fires_neither_event`.
* `POI_TERMINAL` — `terminal` is observed `True` (fires on the SAME bar
  the closed active-POI loop gives that POI its final evaluation, per the
  frozen P5 terminal-current-bar rule — never delayed to "next bar it's
  gone").

DEDUP AND ORDERING
-------------------
`AlertEvent.event_key` is `(event_type, poi_idx, bar_ms)` — the same
event TYPE may legitimately recur for the same POI at a LATER, distinct
bar (e.g. permission lost, then re-entered actionable weeks later), so
dedup is per-transition, never "this event type can only ever happen once
for this POI." Within one bar, events are ordered first by ascending
`poi_idx` (the same order the Pine active-POI loop already iterates in —
never a map/dict incidental order), then by a fixed intra-POI priority
(`_EVENT_PRIORITY` below) reflecting the natural lifecycle chronology
(activated -> BTMM validated -> permission -> terminal).

PRIMING
--------
`AlertEngine.prime()` seeds every previous-state cache from a snapshot
WITHOUT emitting a single event — the load-bearing requirement for a
fresh attach, a page reload, a remove/re-add, or a host-timeframe switch,
every one of which presents this engine with pre-existing state that must
be learned, not announced as new. `process()` must not be called before
`prime()` (raises `RuntimeError` — a real bug class this guards, not
theoretical: silently priming lazily on the first `process()` call would
make "was this engine actually primed on purpose" undetectable from the
caller's side).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from btmm_ai_scanner.poi.enums import PoiTerminalReason


class P8EventType(StrEnum):
    POI_ACTIVATED = "POI_ACTIVATED"
    BTMM_VALIDATED = "BTMM_VALIDATED"
    PERMISSION_ENTERED_ACTIONABLE = "PERMISSION_ENTERED_ACTIONABLE"
    PERMISSION_LOST_ACTIONABLE = "PERMISSION_LOST_ACTIONABLE"
    POI_TERMINAL = "POI_TERMINAL"


#: C_PERM_BUY_BIAS=0, C_PERM_SELL_BIAS=1 -- the exact two permission codes
#: the closed P5/P7 engine can produce that this project's own readiness
#: audit named as "actionable". Never re-derived from score/bands here --
#: `permission` is read as-is from the closed engine's own output.
ACTIONABLE_PERMISSIONS: frozenset[int] = frozenset({0, 1})

#: Deterministic intra-bar, intra-POI tiebreak (Phase 21/24) -- a fixed
#: lifecycle-chronology order, never incidental dict/set iteration order.
_EVENT_PRIORITY: dict[P8EventType, int] = {
    P8EventType.POI_ACTIVATED: 0,
    P8EventType.BTMM_VALIDATED: 1,
    P8EventType.PERMISSION_ENTERED_ACTIONABLE: 2,
    P8EventType.PERMISSION_LOST_ACTIONABLE: 2,
    P8EventType.POI_TERMINAL: 3,
}


@dataclass(frozen=True)
class PoiSnapshot:
    """One POI's per-bar decision state, exactly the fields the closed
    P5/P7 active-POI loop already computes (the same fields `P5EVAL`
    already logs) -- nothing recomputed, nothing added."""

    poi_idx: int
    poi_bullish: bool
    tier: int
    terminal: bool
    btmm_valid: bool
    permission: int
    lifecycle: int
    #: RC3: why this POI is terminal. Required whenever `terminal` is True, so
    #: a consumer never has to guess whether price used the zone or the zone
    #: failed. `None` is only valid for a POI that is not terminal.
    terminal_reason: PoiTerminalReason | None = None

    def __post_init__(self) -> None:
        if not self.terminal and self.terminal_reason is not None:
            raise ValueError(
                f"POI {self.poi_idx} carries a terminal_reason while still active"
            )
        if self.terminal and self.terminal_reason is None:
            # RC2 had exactly one way to become terminal, so an unlabelled
            # terminal POI is unambiguously an invalidation. Defaulting here
            # keeps every pre-RC3 fixture meaningful instead of silently
            # reinterpreting it; RC3 callers pass MITIGATED explicitly.
            object.__setattr__(self, "terminal_reason", PoiTerminalReason.INVALIDATED)


@dataclass(frozen=True)
class BarSnapshot:
    """One confirmed bar's full ELIGIBLE-POI state. `pois` must be every
    POI the closed active-POI loop evaluated this bar (Phase 23: the full
    eligible set, never bounded by P7's display capacity) -- order does
    not matter here, `AlertEngine` re-sorts internally."""

    bar_ms: int
    pois: tuple[PoiSnapshot, ...]


@dataclass(frozen=True)
class AlertEvent:
    event_type: P8EventType
    bar_ms: int
    poi_idx: int
    poi_bullish: bool
    tier: int
    btmm_valid: bool
    permission: int
    lifecycle: int
    #: Set on POI_TERMINAL only; None on every other event type.
    terminal_reason: PoiTerminalReason | None = None

    @property
    def event_key(self) -> tuple[P8EventType, int, int]:
        """Canonical dedup key: event type + POI identity + the bar it
        fired on. Deliberately NOT just (event_type, poi_idx) -- the same
        event type is a legitimate, distinct occurrence at a later bar."""
        return (self.event_type, self.poi_idx, self.bar_ms)


def _event(event_type: P8EventType, bar_ms: int, poi: PoiSnapshot) -> AlertEvent:
    return AlertEvent(
        event_type=event_type,
        bar_ms=bar_ms,
        poi_idx=poi.poi_idx,
        poi_bullish=poi.poi_bullish,
        tier=poi.tier,
        btmm_valid=poi.btmm_valid,
        permission=poi.permission,
        lifecycle=poi.lifecycle,
        terminal_reason=(
            poi.terminal_reason if event_type is P8EventType.POI_TERMINAL else None
        ),
    )


class AlertEngine:
    """Stateful, single-pass P8 event detector. One instance per host
    context (a host-timeframe switch gets its OWN engine / a `reprime`,
    never a shared one spanning two different POI universes)."""

    def __init__(self) -> None:
        self._primed = False
        self._known: set[int] = set()
        self._prev_btmm_valid: dict[int, bool] = {}
        self._prev_permission: dict[int, int] = {}
        self._terminal_alerted: set[int] = set()
        self._last_bar_ms: int | None = None

    @property
    def primed(self) -> bool:
        return self._primed

    def prime(self, snapshot: BarSnapshot) -> None:
        """Seed every previous-state cache from `snapshot` WITHOUT
        emitting a single event. Safe to call more than once (a
        host-timeframe switch re-primes from scratch -- see `reprime`)."""
        self._known = {p.poi_idx for p in snapshot.pois}
        self._prev_btmm_valid = {p.poi_idx: p.btmm_valid for p in snapshot.pois}
        self._prev_permission = {p.poi_idx: p.permission for p in snapshot.pois}
        self._terminal_alerted = {p.poi_idx for p in snapshot.pois if p.terminal}
        self._last_bar_ms = snapshot.bar_ms
        self._primed = True

    def reprime(self, snapshot: BarSnapshot) -> None:
        """A host-timeframe switch (or any other event presenting a
        wholly different, pre-existing POI universe) re-primes exactly
        like a fresh attach -- named separately only so call sites read
        as an intentional context change, not an accidental double-prime."""
        self.prime(snapshot)

    def process(self, snapshot: BarSnapshot) -> list[AlertEvent]:
        """The confirmed-bar step. Must be primed first. Returns every
        genuine transition this bar, in the deterministic order Section
        "DEDUP AND ORDERING" above defines."""
        if not self._primed:
            raise RuntimeError("AlertEngine.process() called before prime()")

        # Phase 28: identical re-processing of the same confirmed bar
        # (repeated realtime evaluation / identical log replay) emits
        # nothing new the second time.
        if snapshot.bar_ms == self._last_bar_ms:
            return []
        if self._last_bar_ms is not None and snapshot.bar_ms < self._last_bar_ms:
            raise ValueError(
                f"AlertEngine.process() called out of order: bar {snapshot.bar_ms} "
                f"precedes the last-processed bar {self._last_bar_ms}"
            )

        raw_events: list[AlertEvent] = []
        for poi in sorted(snapshot.pois, key=lambda p: p.poi_idx):
            is_new = poi.poi_idx not in self._known
            if is_new:
                raw_events.append(_event(P8EventType.POI_ACTIVATED, snapshot.bar_ms, poi))
                self._known.add(poi.poi_idx)

            prev_btmm = self._prev_btmm_valid.get(poi.poi_idx, False)
            if (not prev_btmm) and poi.btmm_valid:
                raw_events.append(_event(P8EventType.BTMM_VALIDATED, snapshot.bar_ms, poi))
            self._prev_btmm_valid[poi.poi_idx] = poi.btmm_valid

            prev_perm = self._prev_permission.get(poi.poi_idx)
            prev_actionable = prev_perm in ACTIONABLE_PERMISSIONS if prev_perm is not None else False
            curr_actionable = poi.permission in ACTIONABLE_PERMISSIONS
            if (not prev_actionable) and curr_actionable:
                raw_events.append(
                    _event(P8EventType.PERMISSION_ENTERED_ACTIONABLE, snapshot.bar_ms, poi)
                )
            elif prev_actionable and not curr_actionable:
                raw_events.append(_event(P8EventType.PERMISSION_LOST_ACTIONABLE, snapshot.bar_ms, poi))
            # prev_actionable and curr_actionable both true (e.g. BUY_BIAS
            # -> SELL_BIAS): deliberately NEITHER event -- see module
            # docstring "direction change" note.
            self._prev_permission[poi.poi_idx] = poi.permission

            if poi.terminal and poi.poi_idx not in self._terminal_alerted:
                raw_events.append(_event(P8EventType.POI_TERMINAL, snapshot.bar_ms, poi))
                self._terminal_alerted.add(poi.poi_idx)

        self._last_bar_ms = snapshot.bar_ms
        # Composite key: ascending poi_idx is PRIMARY (matches the Pine
        # active-POI loop's own iteration order), the fixed lifecycle
        # priority is the SECONDARY tiebreak within one POI's own
        # same-bar events. A single `key=_EVENT_PRIORITY[...]` sort would
        # wrongly group every POI_ACTIVATED event across ALL pois before
        # any POI's BTMM_VALIDATED -- the bug this composite key avoids.
        raw_events.sort(key=lambda e: (e.poi_idx, _EVENT_PRIORITY[e.event_type]))
        return raw_events


__all__ = [
    "ACTIONABLE_PERMISSIONS",
    "AlertEngine",
    "AlertEvent",
    "BarSnapshot",
    "P8EventType",
    "PoiSnapshot",
]
