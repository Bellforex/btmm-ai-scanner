"""RC3 downstream consequences: P5 active-universe eligibility and P8 terminal cause.

Two things are being pinned. First, that a mitigated POI leaves the active
universe on the bar *after* the one that mitigated it, never on that bar
itself — the terminal-bar rule is older than RC3 and RC3 must not quietly
change it into an off-by-one. Second, that `POI_TERMINAL` now says why,
exactly once, and never twice.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from btmm_ai_scanner.poi.enums import PoiLifecycleStatus, PoiTerminalReason
from tests.parity_support.p5_active_poi_loop_model import (
    resolve_eligible_and_next,
    resolve_eligible_and_next_rc3,
)
from tests.parity_support.p8_alert_oracle import (
    AlertEngine,
    BarSnapshot,
    P8EventType,
    PoiSnapshot,
)

_A = UUID("00000000-0000-4000-8000-00000000000a")
_B = UUID("00000000-0000-4000-8000-00000000000b")
_C = UUID("00000000-0000-4000-8000-00000000000c")


# ---- P5: the terminal-bar rule survives the widened definition --------------


def test_a_fresh_poi_is_eligible_and_stays_active() -> None:
    eligible, nxt = resolve_eligible_and_next_rc3({_A: True}, frozenset())
    assert eligible == {_A}
    assert nxt == {_A}


def test_a_poi_that_mitigates_this_bar_is_still_evaluated_this_bar() -> None:
    """It was active entering the bar, so it gets its final evaluation here."""
    eligible, nxt = resolve_eligible_and_next_rc3({_A: False}, frozenset({_A}))
    assert eligible == {_A}, "the mitigating bar must still evaluate the POI"
    assert nxt == frozenset(), "and it must be gone from the next bar"


def test_a_poi_already_mitigated_before_the_bar_is_not_evaluated() -> None:
    eligible, nxt = resolve_eligible_and_next_rc3({_A: False}, frozenset())
    assert eligible == frozenset()
    assert nxt == frozenset()


def test_mitigation_removes_only_the_mitigated_poi() -> None:
    eligible, nxt = resolve_eligible_and_next_rc3(
        {_A: False, _B: True, _C: True}, frozenset({_A, _B})
    )
    assert eligible == {_A, _B, _C}
    assert nxt == {_B, _C}


def test_an_unknown_previously_active_id_cannot_be_evaluated() -> None:
    eligible, _ = resolve_eligible_and_next_rc3(
        {_B: True}, frozenset({_A, _B}), known_ids=frozenset({_B})
    )
    assert eligible == {_B}


def test_rc3_widens_the_rc2_universe_without_changing_its_shape() -> None:
    """Same algebra, different terminality predicate — check both directions."""
    rc2 = resolve_eligible_and_next(
        {_A: PoiLifecycleStatus.NO_BREACH, _B: PoiLifecycleStatus.NO_BREACH},
        frozenset(),
    )
    rc3_all_fresh = resolve_eligible_and_next_rc3({_A: True, _B: True}, frozenset())
    assert rc2 == rc3_all_fresh

    rc2_invalidated = resolve_eligible_and_next(
        {_A: PoiLifecycleStatus.GENUINE_INVALIDATION_CONFIRMED}, frozenset()
    )
    rc3_invalidated = resolve_eligible_and_next_rc3({_A: False}, frozenset())
    assert rc2_invalidated == rc3_invalidated


def test_mutant_dropping_the_poi_on_its_own_terminal_bar_loses_an_evaluation() -> None:
    """A naive "filter out anything not fresh" would return an empty set here."""
    eligible, _ = resolve_eligible_and_next_rc3({_A: False}, frozenset({_A}))
    naive = frozenset(pid for pid, fresh in {_A: False}.items() if fresh)
    assert eligible != naive
    assert eligible == {_A}


def test_mutant_letting_a_mitigated_poi_stay_active_is_visible_in_next_active() -> None:
    _, nxt = resolve_eligible_and_next_rc3({_A: False}, frozenset({_A}))
    assert _A not in nxt


# ---- P8: one terminal event, and it says why --------------------------------


def _poi(
    idx: int,
    *,
    terminal: bool = False,
    reason: PoiTerminalReason | None = None,
    btmm: bool = False,
    permission: int = 9,
) -> PoiSnapshot:
    return PoiSnapshot(
        poi_idx=idx,
        poi_bullish=True,
        tier=1,
        terminal=terminal,
        btmm_valid=btmm,
        permission=permission,
        lifecycle=0,
        terminal_reason=reason,
    )


def _bar(ms: int, *pois: PoiSnapshot) -> BarSnapshot:
    return BarSnapshot(bar_ms=ms, pois=pois)


def _terminal_events(events: list) -> list:
    return [e for e in events if e.event_type is P8EventType.POI_TERMINAL]


def test_mitigation_emits_one_terminal_event_carrying_its_reason() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0)))
    events = engine.process(
        _bar(2000, _poi(0, terminal=True, reason=PoiTerminalReason.MITIGATED))
    )
    terminals = _terminal_events(events)
    assert len(terminals) == 1
    assert terminals[0].terminal_reason is PoiTerminalReason.MITIGATED


def test_invalidation_emits_one_terminal_event_carrying_its_reason() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0)))
    events = engine.process(
        _bar(2000, _poi(0, terminal=True, reason=PoiTerminalReason.INVALIDATED))
    )
    terminals = _terminal_events(events)
    assert len(terminals) == 1
    assert terminals[0].terminal_reason is PoiTerminalReason.INVALIDATED


def test_a_poi_that_stays_terminal_never_fires_a_second_terminal_event() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0)))
    terminal = _poi(0, terminal=True, reason=PoiTerminalReason.MITIGATED)
    first = engine.process(_bar(2000, terminal))
    assert len(_terminal_events(first)) == 1
    for ms in (3000, 4000, 5000):
        assert _terminal_events(engine.process(_bar(ms, terminal))) == []


def test_two_pois_going_terminal_for_different_reasons_keep_them_apart() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0), _poi(1)))
    events = engine.process(
        _bar(
            2000,
            _poi(0, terminal=True, reason=PoiTerminalReason.MITIGATED),
            _poi(1, terminal=True, reason=PoiTerminalReason.INVALIDATED),
        )
    )
    by_idx = {e.poi_idx: e.terminal_reason for e in _terminal_events(events)}
    assert by_idx == {
        0: PoiTerminalReason.MITIGATED,
        1: PoiTerminalReason.INVALIDATED,
    }


def test_non_terminal_events_carry_no_terminal_reason() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0)))
    events = engine.process(_bar(2000, _poi(0, btmm=True, permission=0)))
    assert events, "expected the BTMM and permission transitions"
    for event in events:
        assert event.event_type is not P8EventType.POI_TERMINAL
        assert event.terminal_reason is None


def test_priming_on_an_already_terminal_poi_announces_nothing() -> None:
    """A fresh attach must learn existing state, not replay it as new alerts."""
    engine = AlertEngine()
    terminal = _poi(0, terminal=True, reason=PoiTerminalReason.MITIGATED)
    engine.prime(_bar(1000, terminal))
    assert _terminal_events(engine.process(_bar(2000, terminal))) == []


# ---- P8 mutants -------------------------------------------------------------


def test_mutant_a_terminal_snapshot_without_a_reason_defaults_to_invalidated() -> None:
    """RC2 had exactly one terminal cause, so the default is its faithful reading."""
    assert _poi(0, terminal=True).terminal_reason is PoiTerminalReason.INVALIDATED


def test_mutant_an_active_poi_may_not_carry_a_terminal_reason() -> None:
    with pytest.raises(ValueError, match="while still active"):
        _poi(0, terminal=False, reason=PoiTerminalReason.MITIGATED)


def test_mutant_mapping_mitigation_onto_invalidation_is_detectable() -> None:
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(0)))
    mitigated = _terminal_events(
        engine.process(
            _bar(2000, _poi(0, terminal=True, reason=PoiTerminalReason.MITIGATED))
        )
    )[0]
    other = AlertEngine()
    other.prime(_bar(1000, _poi(0)))
    invalidated = _terminal_events(
        other.process(
            _bar(2000, _poi(0, terminal=True, reason=PoiTerminalReason.INVALIDATED))
        )
    )[0]
    assert mitigated.terminal_reason is not invalidated.terminal_reason
    assert mitigated.event_key == invalidated.event_key, (
        "the dedup key is deliberately unchanged: the reason is payload, not identity"
    )
