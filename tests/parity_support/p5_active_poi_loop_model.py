"""The P5 active-POI evaluation loop: an EXTERNAL orchestration Pine's
integration needs, wrapped around the unmodified, single-POI-in/single-
result-out `assess_confluence`.

Test/parity tooling only — nothing in `src/` imports this, and it changes no
production semantics. `assess_confluence` itself is untouched; this module
only decides WHICH POIs it gets called with, on which bar, and what carries
forward to the next one.

THIS IS NOT A SOURCE PORT — IT IS A FROZEN CONTRACT, IMPLEMENTED
----------------------------------------------------------------------
Unlike T1-T5, there is no existing production function this differentials
against: `latest_poi()` picks exactly one POI per call, by design, and
`assess_confluence` has no opinion on what "the active set" means. The loop
below is new orchestration logic, per the project's own explicit contract
(already frozen, not an open author decision):

* evaluate ALL active/non-terminal POIs on every eligible confirmed bar --
  never "pick one best POI" as the live universe;
* a POI active entering a bar that becomes terminal ON that bar still gets
  its final evaluation THIS bar, then is excluded from the NEXT bar's set;
* canonical P3 identity only (`PoiObservation.record_id`) -- no second BTRC
  identity scheme;
* stable, deterministic iteration order.

THE SOURCED DEFINITION OF "TERMINAL"
-----------------------------------------
Not invented here. `terminal = True` is set in exactly one place across the
whole POI package (`analyzer.py`, `lifecycle.py`, `lifecycle_cursor.py`,
`cursor_fast_forward.py`, all four sites identical): when
`final_status == PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED`. No other
`PoiLifecycleStatus` member is ever treated as terminal anywhere in the
source. `CurrentPoiState` does not itself expose a `terminal: bool` field --
only `poi_lifecycle_status` -- so this module derives terminality the same
way the source's own internal callers do: a direct equality check.

WHY THE ELIGIBLE SET IS A UNION, NOT JUST "CURRENTLY NON-TERMINAL"
------------------------------------------------------------------------
Filtering `current_poi_states` by "non-terminal right now" alone would DROP
a POI on the exact bar it goes terminal -- but Phase 11's contract requires
that bar's evaluation to still happen. So the eligible set for a bar is the
union of (a) every POI the loop already considered active entering the bar,
and (b) every POI whose CURRENT status this bar is non-terminal (which also
naturally picks up brand-new POIs the instant they first appear in
`current_poi_states` -- already gated on availability by the scanner's own
point-in-time discipline, not re-checked here).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from btmm_ai_scanner.btrc import assess_confluence
from btmm_ai_scanner.btrc.t5_configuration import ConfluenceConfiguration
from btmm_ai_scanner.btrc.t5_decision import BtrcDecision
from btmm_ai_scanner.btrc.t5_engine import ConfluenceBarContext
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.framework import FrameworkTracker
from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiTerminalReason
from btmm_ai_scanner.poi.observation import PoiObservation
from btmm_ai_scanner.scanner.analysis import ScannerAnalysis

_TERMINAL_STATUS = PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED


@dataclass(frozen=True)
class ActiveLoopResult:
    """One bar's worth of active-loop output."""

    decisions_by_poi_id: dict[UUID, BtrcDecision]
    next_bar_active_ids: frozenset[UUID]
    evaluated_order: tuple[UUID, ...]


def _current_status_by_id(
    analysis: ScannerAnalysis,
) -> dict[UUID, PoiLifecycleStatus]:
    return {
        s.poi_record_id: s.poi_lifecycle_status
        for s in analysis.poi_analysis.current_poi_states
    }


def _observation_by_id(analysis: ScannerAnalysis) -> dict[UUID, PoiObservation]:
    return {o.record_id: o for o in analysis.poi_analysis.poi_observations}


def _resolve_from_terminal_flags(
    terminal_by_id: dict[UUID, bool],
    previously_active_ids: frozenset[UUID],
    known_ids: frozenset[UUID] | None,
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    """The set algebra, with terminality already decided by the caller.

    Both the RC2 status-based entry point and the RC3 fresh-active one route
    through this, so the two can never disagree about the terminal-bar
    ordering — they only disagree about what makes a POI terminal.
    """
    available = known_ids if known_ids is not None else frozenset(terminal_by_id)
    non_terminal_now = frozenset(
        poi_id for poi_id, is_terminal in terminal_by_id.items() if not is_terminal
    )
    eligible_ids = (previously_active_ids | non_terminal_now) & available
    next_active = frozenset(
        poi_id for poi_id in eligible_ids if not terminal_by_id.get(poi_id, False)
    )
    return eligible_ids, next_active


def resolve_eligible_and_next_rc3(
    fresh_active_by_id: dict[UUID, bool],
    previously_active_ids: frozenset[UUID],
    *,
    known_ids: frozenset[UUID] | None = None,
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    """RC3 eligibility: a POI leaves the active universe when it stops being fresh.

    Identical set algebra to the RC2 entry point below, with one substitution:
    terminality is `not fresh_active` rather than "the lifecycle status is
    genuine invalidation". That widens terminality to include first-reaction
    mitigation, which is the whole point of RC3, and it preserves the
    terminal-bar rule — a POI that goes terminal ON this bar is still evaluated
    this bar and only drops out of the next one.
    """
    return _resolve_from_terminal_flags(
        {poi_id: not fresh for poi_id, fresh in fresh_active_by_id.items()},
        previously_active_ids,
        known_ids,
    )


def resolve_eligible_and_next(
    status_by_id: dict[UUID, PoiLifecycleStatus],
    previously_active_ids: frozenset[UUID],
    *,
    known_ids: frozenset[UUID] | None = None,
) -> tuple[frozenset[UUID], frozenset[UUID]]:
    """The pure set algebra behind the active-loop contract, independent of
    `ScannerAnalysis`/`assess_confluence` entirely -- everything Phases 8-14
    need to prove is a property of THIS function.

    `known_ids` restricts eligibility to ids that actually have an
    observation to evaluate (a previously-active id whose POI has since
    disappeared from the registry entirely cannot be evaluated); defaults to
    every id `status_by_id` itself knows about.

    Returns `(eligible_ids_this_bar, next_bar_active_ids)`.
    """
    return _resolve_from_terminal_flags(
        {poi_id: status is _TERMINAL_STATUS for poi_id, status in status_by_id.items()},
        previously_active_ids,
        known_ids,
    )


def _stable_order(
    ids: frozenset[UUID], obs_by_id: dict[UUID, PoiObservation]
) -> tuple[UUID, ...]:
    return tuple(
        sorted(
            ids,
            key=lambda poi_id: (obs_by_id[poi_id].availability_time_utc, str(poi_id)),
        )
    )


def run_active_poi_loop(
    analysis: ScannerAnalysis,
    previously_active_ids: frozenset[UUID],
    *,
    candles_by_timeframe: dict[Timeframe, tuple[NormalizedCandle, ...]] | None = None,
    evaluation_time_utc: datetime | None = None,
    configuration: ConfluenceConfiguration | None = None,
    rc3_freshness: bool = False,
    framework_timeframe: Timeframe | None = None,
    framework_trackers: dict[Timeframe, FrameworkTracker] | None = None,
) -> ActiveLoopResult:
    """Evaluate every eligible POI for one confirmed bar's `ScannerAnalysis`,
    using `resolve_eligible_and_next` for the set algebra and calling the
    REAL, unmodified `assess_confluence` once per eligible POI, in a stable
    deterministic order.

    `previously_active_ids` is the loop's own carried-forward state -- pass
    `frozenset()` for the very first bar. The returned
    `next_bar_active_ids` is what the caller must pass back in on the NEXT
    bar's call: this module holds no state of its own between calls,
    matching the scanner's own pure-function-of-inputs discipline.
    """
    obs_by_id = _observation_by_id(analysis)
    if rc3_freshness:
        eligible_ids, next_active = resolve_eligible_and_next_rc3(
            {
                s.poi_record_id: s.fresh_active
                for s in analysis.poi_analysis.current_poi_states
            },
            previously_active_ids,
            known_ids=frozenset(obs_by_id),
        )
    else:
        eligible_ids, next_active = resolve_eligible_and_next(
            _current_status_by_id(analysis),
            previously_active_ids,
            known_ids=frozenset(obs_by_id),
        )
    ordered = _stable_order(eligible_ids, obs_by_id)

    if framework_timeframe is not None:
        # RC4 market-framework profile (author 2026-09-19).
        configuration = (configuration or ConfluenceConfiguration()).model_copy(
            update={
                "market_framework": True,
                "framework_timeframe": framework_timeframe,
            }
        )
    decisions: dict[UUID, BtrcDecision] = {}
    # One POI-independent T1-T4 context per bar, shared by every POI: the
    # decisions are bit-identical to per-POI recomputation (see
    # ConfluenceBarContext).
    bar_context = ConfluenceBarContext(
        analysis,
        candles_by_timeframe=candles_by_timeframe,
        evaluation_time_utc=evaluation_time_utc,
        framework_trackers=framework_trackers,
    )
    for poi_id in ordered:
        poi = obs_by_id[poi_id]
        decisions[poi_id] = assess_confluence(
            analysis,
            poi,
            candles_by_timeframe=candles_by_timeframe,
            evaluation_time_utc=evaluation_time_utc,
            configuration=configuration,
            bar_context=bar_context,
        )

    if framework_timeframe is not None:
        # RC4 interaction episode: a POI mitigated by its first touch stays in
        # the active universe while its BTMM episode is still running, and
        # leaves the NEXT bar after the episode ends (terminal-bar rule kept).
        state_by_id = {
            st.poi_record_id: st for st in analysis.poi_analysis.current_poi_states
        }
        next_active = frozenset(
            poi_id
            for poi_id in eligible_ids
            if not rc4_is_terminal(state_by_id.get(poi_id), decisions[poi_id])
        )

    return ActiveLoopResult(
        decisions_by_poi_id=decisions,
        next_bar_active_ids=next_active,
        evaluated_order=ordered,
    )


def rc4_is_terminal(state: object, decision: BtrcDecision) -> bool:
    """RC4: terminal = no longer fresh AND not inside a running interaction
    episode that began with a first-touch mitigation."""
    if state is None:
        return False
    fresh = getattr(state, "fresh_active", True)
    if fresh:
        return False
    reason = getattr(state, "terminal_reason", None)
    return not (
        reason is PoiTerminalReason.MITIGATED
        and decision.interaction_episode == "ACTIVE"
    )


def rc4_terminal_reason(
    state: object, decision: BtrcDecision
) -> PoiTerminalReason | None:
    """The reason P8 reports when an RC4 POI goes terminal: a true failure
    (price accepted beyond the POI, no reclaim) is an invalidation."""
    if decision.interaction_episode == "FAILED":
        return PoiTerminalReason.INVALIDATED
    reason = getattr(state, "terminal_reason", None)
    return reason if isinstance(reason, PoiTerminalReason) else None
