"""An expected-terminal oracle derived from lifecycle transitions alone.

Author requirement, 2026-09-21: prove P8's terminal events without building a
second event emitter. So this asks a different question of a different code
path and the two answers are compared.

* THE ORACLE asks: for each authoritative POI, what is the first causally
  observable prefix on which it becomes ``GENUINE_INVALIDATION_CONFIRMED``?
  It reads only lifecycle state, never an event.
* P8 asks: when did the active-POI loop observe ``terminal`` true? That runs
  through the eligibility algebra and the alert engine.

They share the replay that produces the bars, which is unavoidable -- there is
one engine -- but nothing downstream of the lifecycle state is shared, which is
where every terminal defect so far has lived.

OBSERVABILITY. A transition only warrants an event when it happens inside the
window AND the POI was seen alive first. Three cases produce no event and are
not failures: a POI already invalidated the first time it is seen (nothing to
observe), one still valid at the end, and one that never entered the event loop
at all. Each is classified rather than waved away.

AUTHORITY COMES FROM THE REPLAY, NOT FROM HERE. Same-origin suppression is
decided against the kernel's own provenance ledger. An early version of this
module rebuilt it from a fresh ``Rc5SemanticLedger``, which has no provenance,
and so produced a DIFFERENT authoritative set from the one P5 actually used --
it counted a suppressed BULLISH_ENGULFING as owed an event and then excused the
absence as "never entered the event loop". The caller now passes
``bar.suppressed_poi_ids`` and suppression is reported as its own class.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from btmm_ai_scanner.poi.enums import PoiLifecycleStatus

__all__ = [
    "ExpectedTerminal",
    "TerminalComparison",
    "TerminalOracle",
    "UnobservableReason",
    "compare_terminals",
]

_GENUINE = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED


class UnobservableReason(StrEnum):
    """Why a genuine invalidation legitimately produces no P8 event."""

    ALREADY_TERMINAL_WHEN_FIRST_SEEN = "ALREADY_TERMINAL_WHEN_FIRST_SEEN"
    AUTHORITY_SUPPRESSED = "AUTHORITY_SUPPRESSED"
    NEVER_ENTERED_THE_EVENT_LOOP = "NEVER_ENTERED_THE_EVENT_LOOP"


@dataclass(frozen=True)
class ExpectedTerminal:
    poi_record_id: UUID
    poi_type: Any
    first_seen_bar: int
    terminal_bar: int
    terminal_time_utc: datetime
    ever_evaluated: bool
    unobservable: UnobservableReason | None


@dataclass
class TerminalOracle:
    """Accumulates lifecycle transitions across a replay."""

    #: POIs whose status has been observed at least once, and what it was first
    first_status: dict[UUID, PoiLifecycleStatus] = field(default_factory=dict)
    first_seen_bar: dict[UUID, int] = field(default_factory=dict)
    poi_type: dict[UUID, Any] = field(default_factory=dict)
    ever_evaluated: set[UUID] = field(default_factory=set)
    terminal_bar: dict[UUID, int] = field(default_factory=dict)
    terminal_time: dict[UUID, datetime] = field(default_factory=dict)
    #: POIs the replay suppressed as same-origin subordinates on the bar they
    #: went terminal. They are not owed an event of their own.
    suppressed_at_terminal: set[UUID] = field(default_factory=set)

    def observe(
        self,
        bar_index: int,
        availability_time_utc: datetime,
        states_by_id: Any,
        evaluated_ids: Any,
        suppressed_ids: Any,
    ) -> None:
        """Record one bar.

        ``suppressed_ids`` must be the replay's OWN decision
        (``LevelABar.suppressed_poi_ids``) -- see the module docstring.
        """
        self.ever_evaluated.update(evaluated_ids)
        for poi_id, state in states_by_id.items():
            status = state.poi_lifecycle_status
            if poi_id not in self.first_status:
                self.first_status[poi_id] = status
                self.first_seen_bar[poi_id] = bar_index
                self.poi_type[poi_id] = state.poi_type
            if status is _GENUINE and poi_id not in self.terminal_bar:
                self.terminal_bar[poi_id] = bar_index
                self.terminal_time[poi_id] = availability_time_utc
                if poi_id in suppressed_ids:
                    self.suppressed_at_terminal.add(poi_id)

    def expected(self) -> list[ExpectedTerminal]:
        out: list[ExpectedTerminal] = []
        for poi_id, bar in sorted(self.terminal_bar.items(), key=lambda kv: kv[1]):
            born_dead = self.first_status[poi_id] is _GENUINE
            evaluated = poi_id in self.ever_evaluated
            reason: UnobservableReason | None = None
            if poi_id in self.suppressed_at_terminal:
                reason = UnobservableReason.AUTHORITY_SUPPRESSED
            elif born_dead:
                reason = UnobservableReason.ALREADY_TERMINAL_WHEN_FIRST_SEEN
            elif not evaluated:
                reason = UnobservableReason.NEVER_ENTERED_THE_EVENT_LOOP
            out.append(
                ExpectedTerminal(
                    poi_record_id=poi_id,
                    poi_type=self.poi_type[poi_id],
                    first_seen_bar=self.first_seen_bar[poi_id],
                    terminal_bar=bar,
                    terminal_time_utc=self.terminal_time[poi_id],
                    ever_evaluated=evaluated,
                    unobservable=reason,
                )
            )
        return out

    def observable(self) -> list[ExpectedTerminal]:
        return [e for e in self.expected() if e.unobservable is None]


@dataclass(frozen=True)
class TerminalComparison:
    expected_total: int
    observable: int
    unobservable: dict[str, int]
    actual_events: int
    matched: int
    missing: list[ExpectedTerminal]
    extra_poi_idx: list[int]
    duplicated_poi_idx: list[int]
    post_terminal_violations: list[tuple[int, str]]

    @property
    def is_clean(self) -> bool:
        return (
            not self.missing
            and not self.extra_poi_idx
            and not self.duplicated_poi_idx
            and not self.post_terminal_violations
        )


def compare_terminals(
    oracle: TerminalOracle,
    events: Any,
    poi_idx_by_id: Any,
) -> TerminalComparison:
    """Match oracle expectations against the real P8 stream.

    ``events`` is the flat P8 event list; ``poi_idx_by_id`` maps POI record ids
    to the ``poi_idx`` the events carry.
    """
    terminals = [e for e in events if e.event_type.value == "POI_TERMINAL"]
    terminal_bar_by_idx: dict[int, int] = {}
    seen: dict[int, int] = {}
    for event in terminals:
        seen[event.poi_idx] = seen.get(event.poi_idx, 0) + 1
        terminal_bar_by_idx.setdefault(event.poi_idx, event.bar_ms)

    observable = oracle.observable()
    expected_idx = {
        poi_idx_by_id[e.poi_record_id]
        for e in observable
        if e.poi_record_id in poi_idx_by_id
    }
    actual_idx = set(seen)

    missing = [
        e for e in observable if poi_idx_by_id.get(e.poi_record_id) not in actual_idx
    ]
    extra = sorted(actual_idx - expected_idx)
    duplicated = sorted(idx for idx, count in seen.items() if count > 1)

    # nothing may follow a terminal for the same POI
    violations: list[tuple[int, str]] = []
    for event in events:
        bar = terminal_bar_by_idx.get(event.poi_idx)
        if bar is None:
            continue
        if event.bar_ms > bar or (
            event.bar_ms == bar and event.event_type.value != "POI_TERMINAL"
        ):
            if event.bar_ms > bar:
                violations.append((event.poi_idx, event.event_type.value))

    counts: dict[str, int] = {}
    for entry in oracle.expected():
        if entry.unobservable is not None:
            counts[entry.unobservable.value] = (
                counts.get(entry.unobservable.value, 0) + 1
            )
    return TerminalComparison(
        expected_total=len(oracle.expected()),
        observable=len(observable),
        unobservable=counts,
        actual_events=len(terminals),
        matched=len(expected_idx & actual_idx),
        missing=missing,
        extra_poi_idx=extra,
        duplicated_poi_idx=duplicated,
        post_terminal_violations=violations,
    )
