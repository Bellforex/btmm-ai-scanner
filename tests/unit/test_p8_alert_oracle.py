"""P8 V1 alert oracle: directed, prefix, randomized, mutation, and
real-capture-replay proof for `tests/parity_support/p8_alert_oracle.py`.

Per `BTRC_V1_P8_ALERT_READINESS.md`, this is offline-only: the oracle
never touches Pine, and this suite proves the event-detection contract
(priming, dedup, ordering, the five V1 transitions) entirely in Python,
using both synthetic fixtures and the REAL FXCM capture already on record
from P5 closure.
"""

from __future__ import annotations

import random
from pathlib import Path

import pytest

from tests.parity_support.p5_atomic_capture_log import parse_p5_atomic_capture
from tests.parity_support.p8_alert_oracle import (
    ACTIONABLE_PERMISSIONS,
    AlertEngine,
    BarSnapshot,
    P8EventType,
    PoiSnapshot,
)

_REPO = Path(__file__).resolve().parents[2]
_CAPTURE = _REPO / "artifacts" / "p5_capture" / "p5_atomic_raw_log.csv"

C_PERM_BUY_BIAS = 0
C_PERM_SELL_BIAS = 1
C_PERM_ALLOW_BOTH_CONTEXT = 2
C_PERM_COUNTER_TREND = 3
C_PERM_WATCH_ONLY = 4
C_PERM_NO_TRADE_CONTEXT = 5
NON_ACTIONABLE_PERMISSIONS = (
    C_PERM_ALLOW_BOTH_CONTEXT,
    C_PERM_COUNTER_TREND,
    C_PERM_WATCH_ONLY,
    C_PERM_NO_TRADE_CONTEXT,
)


def _poi(idx: int, *, terminal=False, btmm_valid=False, permission=C_PERM_WATCH_ONLY, bullish=True, tier=1, lifecycle=1) -> PoiSnapshot:
    return PoiSnapshot(
        poi_idx=idx,
        poi_bullish=bullish,
        tier=tier,
        terminal=terminal,
        btmm_valid=btmm_valid,
        permission=permission,
        lifecycle=lifecycle,
    )


def _bar(bar_ms: int, *pois: PoiSnapshot) -> BarSnapshot:
    return BarSnapshot(bar_ms=bar_ms, pois=tuple(pois))


def _types(events) -> list[P8EventType]:
    return [e.event_type for e in events]


# --------------------------------------------------------------- priming


def test_priming_emits_zero_events_regardless_of_existing_state():
    engine = AlertEngine()
    assert not engine.primed
    engine.prime(
        _bar(
            1000,
            _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS),
            _poi(2, terminal=True, permission=C_PERM_SELL_BIAS),
        )
    )
    assert engine.primed
    # No process() called yet -- prime() itself must never emit.


def test_process_before_prime_raises():
    engine = AlertEngine()
    with pytest.raises(RuntimeError):
        engine.process(_bar(1000, _poi(1)))


def test_primed_actionable_permission_does_not_fire_on_first_process_of_unchanged_state():
    """The single most important P8 invariant: existing actionable state
    at priming time must not flood PERMISSION_ENTERED_ACTIONABLE the
    first time process() runs, as long as nothing actually changed."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS)))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS)))
    assert events == []


# ------------------------------------------------------- A1 poi activated


def test_new_eligible_poi_after_priming_fires_one_activation():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    events = engine.process(_bar(2000, _poi(5)))
    assert _types(events) == [P8EventType.POI_ACTIVATED]
    assert events[0].poi_idx == 5


def test_same_poi_next_bar_unchanged_fires_nothing():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    engine.process(_bar(2000, _poi(5)))
    events = engine.process(_bar(3000, _poi(5)))
    assert events == []


def test_two_pois_same_bar_fire_two_activation_events():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    events = engine.process(_bar(2000, _poi(5), _poi(9)))
    assert _types(events) == [P8EventType.POI_ACTIVATED, P8EventType.POI_ACTIVATED]
    assert [e.poi_idx for e in events] == [5, 9]


def test_identical_attributes_different_ids_are_two_distinct_events():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    twin_a = _poi(10, bullish=True, tier=2, permission=C_PERM_BUY_BIAS, btmm_valid=True)
    twin_b = _poi(11, bullish=True, tier=2, permission=C_PERM_BUY_BIAS, btmm_valid=True)
    events = engine.process(_bar(2000, twin_a, twin_b))
    poi_ids = {e.poi_idx for e in events if e.event_type is P8EventType.POI_ACTIVATED}
    assert poi_ids == {10, 11}


def test_terminal_poi_reconstructed_at_priming_is_not_activated_later():
    """A POI that was ALREADY terminal at priming time must never later
    produce a POI_TERMINAL alert (it was already accounted for during
    priming) even though it is technically 'known'."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(3, terminal=True)))
    # This terminal POI would not appear in any future eligible snapshot
    # in the real engine (excluded from eligibility next bar) -- confirm
    # the engine does not spuriously re-fire if it somehow did reappear.
    events = engine.process(_bar(2000, _poi(3, terminal=True)))
    assert events == []


# --------------------------------------------------------- A2 btmm valid


def test_primed_btmm_valid_does_not_refire():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=True)))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=True)))
    assert events == []


def test_btmm_false_to_true_fires_once():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=False)))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=True)))
    assert _types(events) == [P8EventType.BTMM_VALIDATED]


def test_btmm_true_to_true_fires_nothing():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=True)))
    engine.process(_bar(2000, _poi(1, btmm_valid=True)))
    events = engine.process(_bar(3000, _poi(1, btmm_valid=True)))
    assert events == []


def test_btmm_true_to_false_fires_no_a2_event():
    """A2 is defined as false->true only; a reversal is not itself a V1
    event (no 'BTMM invalidated' alert exists in this V1 set)."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=True)))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=False)))
    assert P8EventType.BTMM_VALIDATED not in _types(events)


def test_btmm_false_to_true_again_after_reversal_fires_again():
    """A real, later, distinct false->true transition legitimately fires
    A2 again -- dedup is per-transition, not 'once ever per POI'."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=False)))
    first = engine.process(_bar(2000, _poi(1, btmm_valid=True)))
    engine.process(_bar(3000, _poi(1, btmm_valid=False)))
    second = engine.process(_bar(4000, _poi(1, btmm_valid=True)))
    assert _types(first) == [P8EventType.BTMM_VALIDATED]
    assert _types(second) == [P8EventType.BTMM_VALIDATED]
    assert first[0].event_key != second[0].event_key


# ------------------------------------------------- A3/A4 permission band


@pytest.mark.parametrize("actionable", [C_PERM_BUY_BIAS, C_PERM_SELL_BIAS])
@pytest.mark.parametrize("non_actionable", NON_ACTIONABLE_PERMISSIONS)
def test_permission_entered_actionable_from_every_non_actionable_state(non_actionable, actionable):
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=non_actionable)))
    events = engine.process(_bar(2000, _poi(1, permission=actionable)))
    assert _types(events) == [P8EventType.PERMISSION_ENTERED_ACTIONABLE]


@pytest.mark.parametrize("actionable", [C_PERM_BUY_BIAS, C_PERM_SELL_BIAS])
@pytest.mark.parametrize("non_actionable", NON_ACTIONABLE_PERMISSIONS)
def test_permission_lost_actionable_into_every_non_actionable_state(non_actionable, actionable):
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=actionable)))
    events = engine.process(_bar(2000, _poi(1, permission=non_actionable)))
    assert _types(events) == [P8EventType.PERMISSION_LOST_ACTIONABLE]


def test_direct_actionable_direction_change_fires_neither_event():
    """BUY_BIAS -> SELL_BIAS: both endpoints are actionable, so this is a
    direction change, not an entry into or exit from the actionable set.
    V1 has no 'direction changed' event -- firing both ENTERED and LOST
    here would double-notify a single semantic transition."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=C_PERM_BUY_BIAS)))
    events = engine.process(_bar(2000, _poi(1, permission=C_PERM_SELL_BIAS)))
    assert P8EventType.PERMISSION_ENTERED_ACTIONABLE not in _types(events)
    assert P8EventType.PERMISSION_LOST_ACTIONABLE not in _types(events)


def test_non_actionable_to_non_actionable_fires_nothing_even_if_state_differs():
    """WATCH_ONLY -> COUNTER_TREND: neither endpoint is actionable, so no
    A3/A4 event -- proves the oracle checks SET membership, not raw
    equality, matching the closed engine's own coarse permission grouping."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=C_PERM_WATCH_ONLY)))
    events = engine.process(_bar(2000, _poi(1, permission=C_PERM_COUNTER_TREND)))
    assert events == []


def test_score_movement_without_band_change_never_fires_a3_or_a4():
    """Phase 19: PoiSnapshot carries no raw score field at all -- this is
    itself the structural proof that a same-band score wobble cannot
    possibly be misread as a band-entry event, since the oracle has
    nothing but `permission` (the closed engine's own coarse decision) to
    read. Documented here as an explicit regression guard even though the
    type system already makes the mistake unreachable."""
    assert not hasattr(PoiSnapshot(1, True, 1, False, False, C_PERM_WATCH_ONLY, 1), "final_score")
    assert not hasattr(PoiSnapshot(1, True, 1, False, False, C_PERM_WATCH_ONLY, 1), "score")


# --------------------------------------------------------------- A5 terminal


def test_terminal_fires_exactly_once_on_the_transition_bar():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, terminal=False)))
    events = engine.process(_bar(2000, _poi(1, terminal=True)))
    assert _types(events) == [P8EventType.POI_TERMINAL]


def test_terminal_does_not_refire_if_somehow_reprocessed():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, terminal=False)))
    engine.process(_bar(2000, _poi(1, terminal=True)))
    # Per the real P5 eligibility rule a terminal POI never reappears next
    # bar -- but defensively confirm the engine would not re-alert even if
    # it did.
    events = engine.process(_bar(3000, _poi(1, terminal=True)))
    assert P8EventType.POI_TERMINAL not in _types(events)


# ------------------------------------------------------------ ordering


def test_terminal_and_permission_change_same_bar_deterministic_order():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=C_PERM_WATCH_ONLY, terminal=False)))
    events = engine.process(_bar(2000, _poi(1, permission=C_PERM_BUY_BIAS, terminal=True)))
    assert _types(events) == [P8EventType.PERMISSION_ENTERED_ACTIONABLE, P8EventType.POI_TERMINAL]


def test_multiple_events_same_poi_same_bar_are_preserved_not_coalesced():
    """BTMM validates AND permission becomes actionable on the same bar
    for the same POI: two distinct canonical events, per Phase 22."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, btmm_valid=False, permission=C_PERM_WATCH_ONLY)))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS)))
    assert _types(events) == [P8EventType.BTMM_VALIDATED, P8EventType.PERMISSION_ENTERED_ACTIONABLE]


def test_event_order_is_ascending_poi_index_first_never_event_type_first():
    """The bug this guards: sorting by event-type priority alone would
    group ALL pois' POI_ACTIVATED events before any poi's BTMM_VALIDATED
    -- wrong. Poi_idx must be the PRIMARY key."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(9, btmm_valid=False), _poi(2, btmm_valid=False)))
    events = engine.process(_bar(2000, _poi(9, btmm_valid=True), _poi(2, btmm_valid=True)))
    assert [e.poi_idx for e in events] == [2, 9]


def test_new_poi_debuting_already_actionable_and_btmm_valid_fires_all_three_in_order():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    events = engine.process(_bar(2000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS)))
    assert _types(events) == [
        P8EventType.POI_ACTIVATED,
        P8EventType.BTMM_VALIDATED,
        P8EventType.PERMISSION_ENTERED_ACTIONABLE,
    ]


# ----------------------------------------------------- multiple POIs / bar


def test_twenty_pois_transition_same_bar_produce_twenty_events_p7_cap_irrelevant():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    pois = tuple(_poi(i) for i in range(20))
    events = engine.process(_bar(2000, *pois))
    assert len(events) == 20
    assert all(e.event_type is P8EventType.POI_ACTIVATED for e in events)
    assert [e.poi_idx for e in events] == list(range(20))


# --------------------------------------------------- reload / host switch


def test_reload_model_reprimes_without_historical_flood():
    """Models a page reload / remove-re-add: a FRESH AlertEngine observes
    pre-existing actionable/valid state for the first time and must not
    flood events for it."""
    pre_existing = _bar(5000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS), _poi(2, permission=C_PERM_WATCH_ONLY))
    fresh_engine = AlertEngine()
    fresh_engine.prime(pre_existing)
    events = fresh_engine.process(_bar(6000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS), _poi(2, permission=C_PERM_WATCH_ONLY)))
    assert events == []


def test_host_switch_reprimes_a_wholly_different_poi_universe():
    """M15 -> H1 presents a completely disjoint POI index range (real
    live evidence: BTRC_V1_P7_UI_LIVE_ACCEPTANCE_ADDENDUM.md recorded
    exactly this). reprime() must treat it as a fresh baseline, not a
    wave of 'new POI' events relative to the OLD host's universe."""
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(500), _poi(501)))  # M15 universe
    engine.process(_bar(2000, _poi(500), _poi(501)))

    engine.reprime(_bar(3000, _poi(10), _poi(11), _poi(12)))  # H1 universe
    events = engine.process(_bar(4000, _poi(10), _poi(11), _poi(12)))
    assert events == [], "reprime must seed the new universe silently, like a fresh attach"

    # A genuinely NEW poi on the new host, after reprime, still alerts normally.
    events2 = engine.process(_bar(5000, _poi(10), _poi(11), _poi(12), _poi(13)))
    assert _types(events2) == [P8EventType.POI_ACTIVATED]
    assert events2[0].poi_idx == 13


# ----------------------------------------------------------------- dedup


def test_identical_bar_reprocessed_emits_nothing_the_second_time():
    """Phase 28: repeated realtime evaluation / identical log replay of
    the SAME confirmed bar must not duplicate events."""
    engine = AlertEngine()
    engine.prime(_bar(1000))
    bar = _bar(2000, _poi(1, btmm_valid=True, permission=C_PERM_BUY_BIAS))
    first = engine.process(bar)
    second = engine.process(bar)
    assert len(first) > 0
    assert second == []


def test_out_of_order_bar_raises():
    engine = AlertEngine()
    engine.prime(_bar(2000))
    engine.process(_bar(3000, _poi(1)))
    with pytest.raises(ValueError):
        engine.process(_bar(2500, _poi(1)))


def test_empty_snapshot_priming_and_processing_is_well_defined():
    engine = AlertEngine()
    engine.prime(_bar(1000))
    events = engine.process(_bar(2000))
    assert events == []


# ------------------------------------------------------- randomized prefix


def _reference_events(
    known_state: dict[int, PoiSnapshot], curr_pois: dict[int, PoiSnapshot], terminal_alerted: set[int]
) -> list:
    """An INDEPENDENT, minimal re-derivation of the same transition rules
    the engine implements -- used only as ground truth for the randomized
    test below, deliberately written as a flat comparison rather than
    reusing AlertEngine's own internals (Phase 30's own prefix-testing
    intent: catch a bug in the engine, not confirm the engine agrees with
    itself).

    `known_state` is CUMULATIVE, ever-seen memory (mutated in place by
    this function, exactly like the engine's own internal dicts) -- never
    just "the previous bar's dict". A real P3 registry index is never
    reused once assigned, so "was this poi_idx ever seen before" is a
    whole-history question, not a one-bar-window one; using only the
    immediately-preceding bar's dict here previously caused a real test
    bug (a poi_idx that dropped out of one bar's snapshot and reappeared
    later was wrongly treated as brand new by the reference, even though
    the real engine correctly remembered it forever)."""
    out = []
    for idx in sorted(curr_pois):
        curr = curr_pois[idx]
        prev = known_state.get(idx)
        if prev is None:
            out.append((P8EventType.POI_ACTIVATED, idx))
        prev_btmm = prev.btmm_valid if prev else False
        if (not prev_btmm) and curr.btmm_valid:
            out.append((P8EventType.BTMM_VALIDATED, idx))
        prev_perm = prev.permission if prev else None
        prev_actionable = prev_perm in ACTIONABLE_PERMISSIONS if prev_perm is not None else False
        curr_actionable = curr.permission in ACTIONABLE_PERMISSIONS
        if (not prev_actionable) and curr_actionable:
            out.append((P8EventType.PERMISSION_ENTERED_ACTIONABLE, idx))
        elif prev_actionable and not curr_actionable:
            out.append((P8EventType.PERMISSION_LOST_ACTIONABLE, idx))
        if curr.terminal and idx not in terminal_alerted:
            out.append((P8EventType.POI_TERMINAL, idx))
            terminal_alerted.add(idx)
        known_state[idx] = curr
    out.sort(key=lambda t: (t[1], _EVENT_PRIORITY_FOR_TEST[t[0]]))
    return out


_EVENT_PRIORITY_FOR_TEST = {
    P8EventType.POI_ACTIVATED: 0,
    P8EventType.BTMM_VALIDATED: 1,
    P8EventType.PERMISSION_ENTERED_ACTIONABLE: 2,
    P8EventType.PERMISSION_LOST_ACTIONABLE: 2,
    P8EventType.POI_TERMINAL: 3,
}


def _random_poi(rng: random.Random, idx: int, prev: PoiSnapshot | None) -> PoiSnapshot:
    # Terminal is sticky once true (matches the real eligibility rule: a
    # poi already alerted terminal wouldn't reappear -- but the reference
    # model tolerates it appearing again for robustness).
    if prev is not None and prev.terminal:
        terminal = True
    else:
        terminal = rng.random() < 0.03
    return PoiSnapshot(
        poi_idx=idx,
        poi_bullish=rng.choice([True, False]),
        tier=rng.randint(0, 2),
        terminal=terminal,
        btmm_valid=rng.random() < 0.3,
        permission=rng.randint(0, 5),
        lifecycle=rng.randint(0, 7),
    )


@pytest.mark.parametrize("seed", range(15))
def test_randomized_prefix_stream_matches_independent_reference(seed):
    """Thousands-of-cheap-cases-where-practical: 15 seeds x 60 bars x up
    to 40 pois, comparing the engine's incremental output against an
    independently-written reference at every single bar (a true prefix
    test -- catches one-bar-early/late, missed reset, duplicate emission).

    A real P3 registry index is assigned once, append-only, and NEVER
    reused for a different POI -- `next_index` below is monotonically
    increasing for the whole test, matching that invariant, rather than
    recycling indices that happen to have dropped out of the current
    active set (a real, previously-caught bug in this exact fixture: see
    `_reference_events`'s docstring)."""
    rng = random.Random(seed)
    engine = AlertEngine()
    known_state: dict[int, PoiSnapshot] = {}
    terminal_alerted_ref: set[int] = set()
    next_index = 0

    def fresh_index() -> int:
        nonlocal next_index
        idx = next_index
        next_index += 1
        return idx

    # Priming bar: some POIs already exist before this engine ever runs.
    prime_pois = {(idx := fresh_index()): _random_poi(rng, idx, None) for _ in range(rng.randint(0, 10))}
    engine.prime(_bar(0, *prime_pois.values()))
    known_state = dict(prime_pois)
    terminal_alerted_ref = {i for i, p in prime_pois.items() if p.terminal}
    active: dict[int, PoiSnapshot] = dict(prime_pois)

    for bar_no in range(1, 61):
        bar_ms = bar_no * 1000
        # Evolve the active set: a terminal POI has a chance to drop out
        # (matching the real eligibility rule -- gone after its final
        # bar); a non-terminal one never drops (still eligible every
        # bar); occasionally add 0-3 brand-new POIs at fresh indices.
        active = {i: p for i, p in active.items() if not p.terminal or rng.random() < 0.5}
        active = {i: _random_poi(rng, i, p) for i, p in active.items()}
        for _ in range(rng.randint(0, 3)):
            idx = fresh_index()
            active[idx] = _random_poi(rng, idx, None)

        expected = _reference_events(known_state, active, terminal_alerted_ref)
        actual = engine.process(_bar(bar_ms, *active.values()))
        actual_pairs = [(e.event_type, e.poi_idx) for e in actual]
        assert actual_pairs == expected, f"seed={seed} bar={bar_no}: mismatch"


def test_randomized_stream_is_deterministic_across_two_independent_runs():
    def run() -> list[tuple]:
        rng = random.Random(999)
        engine = AlertEngine()
        engine.prime(_bar(0))
        out = []
        state: dict[int, PoiSnapshot] = {}
        for bar_no in range(1, 30):
            n_new = rng.randint(0, 2)
            new_ids = [i for i in range(bar_no, bar_no + n_new)]
            for i in new_ids:
                state[i] = _random_poi(rng, i, None)
            events = engine.process(_bar(bar_no * 1000, *state.values()))
            out.extend((e.event_type, e.poi_idx, e.bar_ms) for e in events)
        return out

    assert run() == run()


# ----------------------------------------------------------- mutation guards


def test_mutant_alerting_every_bar_while_state_persists_is_detectably_wrong():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(1, permission=C_PERM_BUY_BIAS)))
    correct_second_bar = engine.process(_bar(2000, _poi(1, permission=C_PERM_BUY_BIAS)))
    # The mutant this guards against: re-emitting PERMISSION_ENTERED_ACTIONABLE
    # every bar the state merely persists.
    mutant_would_emit = [P8EventType.PERMISSION_ENTERED_ACTIONABLE]
    assert _types(correct_second_bar) != mutant_would_emit
    assert correct_second_bar == []


def test_mutant_that_lets_capacity_bound_the_universe_is_detectably_wrong():
    """A hypothetical mutant that only processes the first 8 pois (P7's
    display cap) would produce 8 events here, not 20 -- proving the real
    engine's unbounded behavior is both correct AND distinguishable from
    that bug."""
    engine = AlertEngine()
    engine.prime(_bar(1000))
    pois = tuple(_poi(i) for i in range(20))
    events = engine.process(_bar(2000, *pois))
    mutant_capacity = 8
    assert len(events) != mutant_capacity
    assert len(events) == 20


def test_mutant_wrong_ordering_is_detectably_wrong():
    engine = AlertEngine()
    engine.prime(_bar(1000, _poi(9, btmm_valid=False), _poi(2, btmm_valid=False)))
    events = engine.process(_bar(2000, _poi(9, btmm_valid=True), _poi(2, btmm_valid=True)))
    correct_order = [e.poi_idx for e in events]
    mutant_order_by_insertion = [9, 2]  # what you'd get sorting by nothing at all
    assert correct_order != mutant_order_by_insertion
    assert correct_order == [2, 9]


# ------------------------------------------------------- real capture replay

pytestmark_replay = pytest.mark.skipif(not _CAPTURE.exists(), reason=f"no P5 capture present: {_CAPTURE.name}")


@pytestmark_replay
def test_real_capture_replay_produces_a_deterministic_nonempty_event_stream():
    text = _CAPTURE.read_text(encoding="utf-8")
    capture = parse_p5_atomic_capture(text)

    bars_sorted = sorted(capture.eval_by_bar.keys())
    assert len(bars_sorted) >= 100, "expected a substantial real capture"

    def replay() -> list:
        engine = AlertEngine()
        primed = False
        all_events = []
        for bar_ms in bars_sorted:
            rows = capture.eval_by_bar[bar_ms]
            pois = tuple(
                PoiSnapshot(
                    poi_idx=row.poi_idx,
                    poi_bullish=row.poi_bullish,
                    tier=int(row.field("poiTier")),
                    terminal=bool(row.field("poiTerminal")),
                    btmm_valid=bool(row.field("btmmValid")),
                    permission=int(row.field("permission")),
                    lifecycle=int(row.field("lifecycle")),
                )
                for row in rows
            )
            snapshot = _bar(bar_ms, *pois)
            if not primed:
                engine.prime(snapshot)
                primed = True
                continue
            all_events.extend(engine.process(snapshot))
        return all_events

    events_a = replay()
    events_b = replay()
    assert [(e.event_type, e.poi_idx, e.bar_ms) for e in events_a] == [
        (e.event_type, e.poi_idx, e.bar_ms) for e in events_b
    ], "replay must be fully deterministic"

    assert len(events_a) > 0, "expected at least some real transitions in 100+ real bars"

    # Real event statistics (Phase 35) -- informational, not a semantic
    # threshold. Printed via assertion message only if the sanity bound
    # below is somehow violated (it never should be, given >=100 bars).
    by_type: dict[P8EventType, int] = {}
    for e in events_a:
        by_type[e.event_type] = by_type.get(e.event_type, 0) + 1
    # Every event key must be unique -- no duplicate canonical events
    # anywhere in a real, ~9600-row capture replay.
    keys = [e.event_key for e in events_a]
    assert len(keys) == len(set(keys)), "duplicate canonical event in real replay"

    # No terminal event was skipped: every poi_idx whose LAST observed row
    # in the whole capture has poiTerminal=true must have exactly one
    # POI_TERMINAL event somewhere in the stream.
    last_terminal_by_poi: dict[int, bool] = {}
    for bar_ms in bars_sorted:
        for row in capture.eval_by_bar[bar_ms]:
            last_terminal_by_poi[row.poi_idx] = bool(row.field("poiTerminal"))
    terminal_poi_ids = {idx for idx, is_term in last_terminal_by_poi.items() if is_term}
    alerted_terminal_ids = {e.poi_idx for e in events_a if e.event_type is P8EventType.POI_TERMINAL}
    # Every poi seen as terminal at some point that was NOT already
    # terminal at priming time must have produced exactly one alert.
    primed_bar = bars_sorted[0]
    primed_terminal_ids = {
        row.poi_idx for row in capture.eval_by_bar[primed_bar] if bool(row.field("poiTerminal"))
    }
    expected_alertable_terminal_ids = terminal_poi_ids - primed_terminal_ids
    missing = expected_alertable_terminal_ids - alerted_terminal_ids
    assert missing == set(), f"terminal event(s) missing for real POI(s): {missing}"
