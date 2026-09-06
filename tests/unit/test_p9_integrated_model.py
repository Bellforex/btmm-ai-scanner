"""P9 full-system integration hardening: offline, randomized, mutation-
tested proof that one canonical P3 POI identity flows correctly through
P4/P5 (dynamic state) → P7 (table visibility) → P7-Z (zone visibility) →
P8 (events), with display capacity never limiting engine participation.

WHY OFFLINE FIRST
---------------------------------------------------------
Real TradingView captures (`BTRC_V1_P9_FULL_SYSTEM_PARITY_CLOSURE.md`)
prove the integrated system behaves correctly across whatever real active
counts occur during a live session. They cannot cheaply exercise identity
collisions, exact display-overflow boundaries, or adversarial mutants a
broken build must never pass unnoticed. This suite gives that at
effectively zero marginal cost per run, and is the gate a live capture is
compared AGAINST, not a duplicate of it.
"""

from __future__ import annotations

import random

from tests.parity_support.p8_alert_oracle import P8EventType
from tests.parity_support.p9_digest import integrated_digest
from tests.parity_support.p9_integrated_model import (
    DIRECTION_BEARISH,
    DIRECTION_BULLISH,
    P9BarInput,
    P9IntegratedState,
    P9Record,
    resolve_eligible_ids,
)


def _inp(
    idx: int,
    *,
    poi_type: int = 1,
    direction: int = DIRECTION_BULLISH,
    zone_top: float | None = None,
    zone_bottom: float | None = None,
    avail_time_ms: int | None = None,
    tier: int = 1,
    terminal: bool = False,
    btmm_valid: bool = False,
    align: int = 1,
    final_score: int = 50,
    permission: int = 4,  # WATCH_ONLY -- non-actionable default
    lifecycle: int = 1,
) -> P9BarInput:
    return P9BarInput(
        idx=idx,
        poi_type=poi_type,
        direction=direction,
        zone_top=100.0 + idx if zone_top is None else zone_top,
        zone_bottom=90.0 + idx if zone_bottom is None else zone_bottom,
        avail_time_ms=1_000_000 + idx * 900_000
        if avail_time_ms is None
        else avail_time_ms,
        tier=tier,
        terminal=terminal,
        btmm_valid=btmm_valid,
        align=align,
        final_score=final_score,
        permission=permission,
        lifecycle=lifecycle,
    )


def _by(*inputs: P9BarInput) -> dict[int, P9BarInput]:
    return {i.idx: i for i in inputs}


ACTIONABLE = 0  # C_PERM_BUY_BIAS
NON_ACTIONABLE = 4  # C_PERM_WATCH_ONLY


# ---------------------------------------------------------- activation chain


def test_activation_chain_new_poi_gets_activated_event_and_is_visible() -> None:
    state = P9IntegratedState(p7_max_visible=8, p7z_max_visible=12)
    state.advance_bar(1_000_000, _by(_inp(0)))  # priming bar, no events possible
    records = state.advance_bar(2_000_000, _by(_inp(0), _inp(1)))
    by_idx = {r.idx: r for r in records}
    assert by_idx[1].event_types == ("POI_ACTIVATED",)
    assert by_idx[1].p7_visible is True
    assert by_idx[1].p7z_visible is True
    assert by_idx[0].event_types == ()  # already known, no re-activation


# ----------------------------------------------------------------- BTMM chain


def test_btmm_validation_chain_agrees_across_p7_and_p8() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, btmm_valid=False)))
    records = state.advance_bar(2_000_000, _by(_inp(0, btmm_valid=True)))
    record = records[0]
    assert record.btmm_valid is True
    assert "BTMM_VALIDATED" in record.event_types
    assert record.p7_visible is True  # P7's table reflects the SAME record's state


def test_btmm_validation_fires_exactly_once_not_every_bar_it_stays_valid() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, btmm_valid=False)))
    r1 = state.advance_bar(2_000_000, _by(_inp(0, btmm_valid=True)))
    r2 = state.advance_bar(3_000_000, _by(_inp(0, btmm_valid=True)))
    assert "BTMM_VALIDATED" in r1[0].event_types
    assert "BTMM_VALIDATED" not in r2[0].event_types


# ------------------------------------------------------ permission-entry chain


def test_permission_entry_chain_same_poi_same_bar() -> None:
    state = P9IntegratedState()
    state.advance_bar(
        1_000_000, _by(_inp(0, permission=NON_ACTIONABLE, final_score=40))
    )
    records = state.advance_bar(
        2_000_000, _by(_inp(0, permission=ACTIONABLE, final_score=70))
    )
    record = records[0]
    assert record.permission == ACTIONABLE
    assert record.final_score == 70
    assert "PERMISSION_ENTERED_ACTIONABLE" in record.event_types
    assert record.bar_ms == 2_000_000


# ------------------------------------------------------- permission-loss chain


def test_permission_loss_chain_same_poi_same_bar() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, permission=ACTIONABLE)))
    records = state.advance_bar(2_000_000, _by(_inp(0, permission=NON_ACTIONABLE)))
    record = records[0]
    assert record.permission == NON_ACTIONABLE
    assert "PERMISSION_LOST_ACTIONABLE" in record.event_types


def test_direction_change_between_actionable_bands_fires_neither_event() -> None:
    """BUY_BIAS <-> SELL_BIAS: both endpoints are actionable -- V1's
    deliberate no-op, inherited unchanged from the closed P8 oracle."""
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, permission=0)))  # BUY_BIAS
    records = state.advance_bar(2_000_000, _by(_inp(0, permission=1)))  # SELL_BIAS
    assert records[0].event_types == ()


# -------------------------------------------------------------- terminal chain


def test_terminal_chain_full_sequence_on_one_canonical_identity() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, terminal=False)))
    # Final-pass bar: still eligible, terminal now true.
    final_pass = state.advance_bar(2_000_000, _by(_inp(0, terminal=True)))
    record = final_pass[0]
    assert record.terminal is True
    assert "POI_TERMINAL" in record.event_types
    assert record.p7_visible is True  # still represented on its final bar
    assert record.p7z_visible is True
    # Next bar: excluded from the active universe entirely.
    excluded = state.advance_bar(3_000_000, {})
    assert excluded == ()


def test_terminal_event_fires_exactly_once() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, terminal=False)))
    r1 = state.advance_bar(2_000_000, _by(_inp(0, terminal=True)))
    assert "POI_TERMINAL" in r1[0].event_types
    # A defensive re-pass (should not happen in practice, but the closed
    # P8 oracle's own known_ids exclusion already prevents resurrection).
    # A record IS still emitted (advance_bar emits for every passed-in
    # key, by design -- see the module docstring), but it must show no
    # renewed visibility and no re-fired event.
    r2 = state.advance_bar(
        3_000_000, _by(_inp(0, terminal=True)), known_ids=frozenset({0})
    )
    assert len(r2) == 1
    assert r2[0].event_types == ()
    assert r2[0].p7_visible is False
    assert r2[0].p7z_visible is False


# --------------------------------------------------- non-visible alert case


def test_non_visible_poi_can_still_alert_display_never_gates_engine() -> None:
    """Phase 16: 20 active, P7 shows 8, P7-Z shows 12 -- POI #17 (by
    ascending order, the 18th of 20) is visible in neither, but still
    fully evaluated and can still fire a real P8 event."""
    state = P9IntegratedState(p7_max_visible=8, p7z_max_visible=12)
    bar1 = {i: _inp(i, permission=NON_ACTIONABLE) for i in range(20)}
    state.advance_bar(1_000_000, bar1)
    bar2 = dict(bar1)
    bar2[17] = _inp(17, permission=ACTIONABLE)  # transition on POI #17
    records = state.advance_bar(2_000_000, bar2)
    by_idx = {r.idx: r for r in records}
    assert len(records) == 20
    assert by_idx[17].p7_visible is False
    assert by_idx[17].p7z_visible is False
    assert "PERMISSION_ENTERED_ACTIONABLE" in by_idx[17].event_types
    # And the visible ones really are the lowest 8 / lowest 12 indices.
    assert {r.idx for r in records if r.p7_visible} == set(range(8))
    assert {r.idx for r in records if r.p7z_visible} == set(range(12))


# --------------------------------------------------------------- geometry


def test_geometry_flows_unchanged_and_never_swapped_by_direction() -> None:
    state = P9IntegratedState()
    bull = _inp(0, direction=DIRECTION_BULLISH, zone_top=120.0, zone_bottom=110.0)
    bear = _inp(1, direction=DIRECTION_BEARISH, zone_top=95.0, zone_bottom=85.0)
    records = state.advance_bar(1_000_000, _by(bull, bear))
    by_idx = {r.idx: r for r in records}
    assert by_idx[0].zone_top == 120.0
    assert by_idx[0].zone_bottom == 110.0
    assert by_idx[1].zone_top == 95.0
    assert by_idx[1].zone_bottom == 85.0
    assert by_idx[0].zone_top > by_idx[0].zone_bottom
    assert by_idx[1].zone_top > by_idx[1].zone_bottom


def test_origin_tf_is_the_host_timeframe_for_every_poi() -> None:
    state = P9IntegratedState(timeframe="H1")
    records = state.advance_bar(1_000_000, _by(_inp(0), _inp(1)))
    assert all(r.origin_tf == "H1" for r in records)


# ---------------------------------------------------------- table score/perm


def test_p7_table_never_recomputes_score_or_permission() -> None:
    """The record P7 would display and the record P8 would alert on come
    from the exact same P9Record -- there is no second copy to diverge."""
    state = P9IntegratedState()
    records = state.advance_bar(1_000_000, _by(_inp(0, final_score=73, permission=2)))
    assert records[0].final_score == 73
    assert records[0].permission == 2


# --------------------------------------------------------------- overflow


def test_display_overflow_100_active_p5_evaluates_all_p8_monitors_all() -> None:
    state = P9IntegratedState(p7_max_visible=8, p7z_max_visible=12)
    n = 100
    inputs = {i: _inp(i) for i in range(n)}
    records = state.advance_bar(1_000_000, inputs)
    assert len(records) == n  # engine evaluated every one
    assert sum(1 for r in records if r.p7_visible) == 8
    assert sum(1 for r in records if r.p7z_visible) == 12


# --------------------------------------------------------------- zero active


def test_zero_active_produces_zero_records() -> None:
    state = P9IntegratedState()
    records = state.advance_bar(1_000_000, {})
    assert records == ()


def test_zero_active_after_prior_activity_leaves_no_stale_records() -> None:
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0), _inp(1)))
    records = state.advance_bar(2_000_000, {}, known_ids=frozenset())
    assert records == ()


# --------------------------------------------------- multiple simultaneous


def test_multiple_simultaneous_pois_and_multiple_simultaneous_events() -> None:
    state = P9IntegratedState()
    state.advance_bar(
        1_000_000,
        _by(
            _inp(0, btmm_valid=False, permission=NON_ACTIONABLE),
            _inp(1, btmm_valid=False, permission=NON_ACTIONABLE),
        ),
    )
    # idx 0: BTMM validates AND permission enters actionable, same bar.
    # idx 2: brand new POI, also already BTMM-valid and actionable at birth.
    records = state.advance_bar(
        2_000_000,
        _by(
            _inp(0, btmm_valid=True, permission=ACTIONABLE),
            _inp(1, btmm_valid=False, permission=NON_ACTIONABLE),
            _inp(2, btmm_valid=True, permission=ACTIONABLE),
        ),
    )
    by_idx = {r.idx: r for r in records}
    assert set(by_idx[0].event_types) == {
        "BTMM_VALIDATED",
        "PERMISSION_ENTERED_ACTIONABLE",
    }
    assert by_idx[1].event_types == ()
    assert set(by_idx[2].event_types) == {
        "POI_ACTIVATED",
        "BTMM_VALIDATED",
        "PERMISSION_ENTERED_ACTIONABLE",
    }


# ------------------------------------------------------- identity collision


def test_identity_collision_same_price_type_direction_score_permission_distinct_ids() -> (
    None
):
    state = P9IntegratedState(p7_max_visible=8, p7z_max_visible=12)
    a = _inp(
        3,
        poi_type=1,
        direction=DIRECTION_BULLISH,
        zone_top=100.0,
        zone_bottom=90.0,
        final_score=60,
        permission=2,
    )
    b = _inp(
        9,
        poi_type=1,
        direction=DIRECTION_BULLISH,
        zone_top=100.0,
        zone_bottom=90.0,
        final_score=60,
        permission=2,
    )
    records = state.advance_bar(1_000_000, _by(a, b))
    assert len(records) == 2
    assert {r.idx for r in records} == {3, 9}
    # Both visible, both distinct boxes/rows despite identical everything else.
    assert all(r.p7_visible and r.p7z_visible for r in records)


# -------------------------------------------------------------- determinism


def test_replay_is_byte_identical_across_two_independent_runs() -> None:
    def replay() -> list[P9Record]:
        state = P9IntegratedState()
        out: list[P9Record] = []
        bar_ms = 1_000_000
        known: set[int] = set()
        for step in range(50):
            if step % 3 == 0:
                known.add(len(known))
            terminal_now = {i for i in known if (i + step) % 17 == 0}
            inputs = {
                i: _inp(
                    i,
                    terminal=(i in terminal_now),
                    btmm_valid=(i + step) % 5 == 0,
                    permission=(i + step) % 6,
                )
                for i in known
            }
            out.extend(state.advance_bar(bar_ms, inputs, known_ids=frozenset(known)))
            bar_ms += 900_000
        return out

    a = replay()
    b = replay()
    assert [tuple(r.__dict__.items()) for r in a] == [
        tuple(r.__dict__.items()) for r in b
    ]
    assert integrated_digest(a) == integrated_digest(b)


# ---------------------------------------------------------------- randomized


def test_randomized_system_history_invariants_hold_for_2000_bars() -> None:
    rng = random.Random(4242)
    p7_max, p7z_max = 8, 12
    state = P9IntegratedState(p7_max_visible=p7_max, p7z_max_visible=p7z_max)
    known: set[int] = set()
    terminal_forever: set[int] = set()
    bar_ms = 1_700_000_000_000
    for _ in range(2000):
        if rng.random() < 0.3:
            known.add(len(known))
        alive = known - terminal_forever
        newly_terminal = {i for i in alive if rng.random() < 0.02}
        inputs = {
            i: _inp(
                i,
                terminal=(i in newly_terminal),
                btmm_valid=rng.random() < 0.4,
                permission=rng.choice([0, 1, 2, 3, 4, 5]),
                final_score=rng.randint(0, 100),
            )
            for i in alive
        }
        records = state.advance_bar(bar_ms, inputs, known_ids=frozenset(alive))
        terminal_forever |= newly_terminal

        # Invariants that must hold on EVERY bar.
        assert sum(1 for r in records if r.p7_visible) <= p7_max
        assert sum(1 for r in records if r.p7z_visible) <= p7z_max
        assert len(records) == len(inputs)  # engine evaluates the full set, always
        ids = [r.idx for r in records]
        assert ids == sorted(ids)
        assert len(set(ids)) == len(ids)
        for r in records:
            assert r.zone_top > r.zone_bottom
            # A visible-but-not-eligible record is impossible.
            if r.p7_visible or r.p7z_visible:
                assert r.idx in inputs
        bar_ms += 900_000


# ----------------------------------------------------------------- mutations


def test_mutant_p7_cap_leaking_into_eligibility_is_detectable() -> None:
    """A correct system's TRUE engine-eligible count (independently
    recomputed via `resolve_eligible_ids`) must equal len(records)
    regardless of how small the display caps are."""
    n = 50
    inputs = {i: _inp(i) for i in range(n)}
    status_by_idx = {i: False for i in range(n)}
    true_eligible = resolve_eligible_ids(status_by_idx, frozenset())
    assert len(true_eligible) == n

    for p7_max, p7z_max in ((1, 1), (8, 12), (200, 200)):
        state = P9IntegratedState(p7_max_visible=p7_max, p7z_max_visible=p7z_max)
        records = state.advance_bar(1_000_000, inputs)
        assert len(records) == n  # NEVER capped by display settings


def test_mutant_stale_record_after_terminal_is_detectable() -> None:
    """A broken implementation that keeps showing a fully-terminated POI
    as visible would be caught by this direct assertion."""
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, terminal=False)))
    state.advance_bar(2_000_000, _by(_inp(0, terminal=True)))  # final pass
    records = state.advance_bar(3_000_000, {}, known_ids=frozenset())
    stale_visible = [
        r for r in records if r.idx == 0 and (r.p7_visible or r.p7z_visible)
    ]
    assert stale_visible == []


def test_mutant_geometry_top_bottom_swap_is_detectable() -> None:
    """A broken port that swaps top/bottom would fail this trivially --
    documents the invariant every real record must satisfy."""
    state = P9IntegratedState()
    records = state.advance_bar(
        1_000_000, _by(_inp(0, zone_top=120.0, zone_bottom=100.0))
    )
    assert records[0].zone_top == 120.0
    assert records[0].zone_bottom == 100.0
    # A mutant swapping these would produce zone_top < zone_bottom here:
    assert not (records[0].zone_top < records[0].zone_bottom)


def test_mutant_wrong_timeframe_label_is_detectable() -> None:
    state_m15 = P9IntegratedState(timeframe="M15")
    state_h1 = P9IntegratedState(timeframe="H1")
    r15 = state_m15.advance_bar(1_000_000, _by(_inp(0)))
    r1h = state_h1.advance_bar(1_000_000, _by(_inp(0)))
    assert r15[0].origin_tf == "M15"
    assert r1h[0].origin_tf == "H1"
    assert r15[0].origin_tf != r1h[0].origin_tf


def test_mutant_event_one_bar_early_is_detectable() -> None:
    """A broken BTMM-validated detector that fires on the SAME bar
    btmm_valid becomes true vs. one bar early (before the transition) is
    directly distinguishable via the record stream."""
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0, btmm_valid=False)))
    still_false = state.advance_bar(2_000_000, _by(_inp(0, btmm_valid=False)))
    assert "BTMM_VALIDATED" not in still_false[0].event_types
    now_true = state.advance_bar(3_000_000, _by(_inp(0, btmm_valid=True)))
    assert "BTMM_VALIDATED" in now_true[0].event_types


def test_event_types_reflect_the_correct_p8_event_type_enum_values() -> None:
    """Sanity: the string values stored in `event_types` are exactly the
    closed `P8EventType` enum's own values, not ad-hoc P9 strings."""
    state = P9IntegratedState()
    state.advance_bar(1_000_000, _by(_inp(0)))
    records = state.advance_bar(2_000_000, _by(_inp(0), _inp(1)))
    all_values = {e.value for e in P8EventType}
    for r in records:
        for event_type in r.event_types:
            assert event_type in all_values
