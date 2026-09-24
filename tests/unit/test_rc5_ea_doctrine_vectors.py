"""RC5 Execution Doctrine V1 — pinned vectors, and the MQL5 source that must agree.

There is no MQL5 unit-test runner here and the Strategy Tester cannot be
launched in this environment, so NO RUNTIME MQL5 TEST IS CLAIMED. What this
file does instead is two things that are actually checkable offline:

1. pin the V1 arithmetic in Python against hand-computed vectors, so a change
   to the doctrine has to be deliberate;
2. read `mt5/Experts/RC5_EA.mq5` and assert the MQL5 implementation states the
   same rules. A drift in either direction fails here rather than on a chart.

The terminal-event policy is the part most worth protecting: `MITIGATED` is set
at the FIRST TOUCH, and an execution layer that enters AT a POI touches it by
entering, so treating mitigation as terminal would close every trade at its own
entry.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from tools.rc5_ea_fixtures import (  # type: ignore[import-not-found]
    APPROVED_CLOSE_EVENTS,
    FIXTURE_FIELDS,
    NEVER_CLOSE_EVENTS,
    STATE_MIGRATION_EVENTS,
    BrokerSpec,
    SetupFixture,
    decide,
    fixture_line,
    plan_for,
    proximity_tolerance,
    signal_id,
    zone_distance,
)

_EA = Path(__file__).resolve().parents[2] / "mt5" / "Experts" / "RC5_EA.mq5"


def _ea_source() -> str:
    return _EA.read_text(encoding="utf-8-sig")


# Exness Standard shapes. Pinned so the vectors below are reproducible; the EA
# itself reads these from SymbolInfo and hardcodes nothing.
EURUSD = BrokerSpec(
    name="EURUSDm",
    digits=5,
    point=Decimal("0.00001"),
    tick_size=Decimal("0.00001"),
    tick_value_loss=Decimal("0.1"),
    volume_min=Decimal("0.01"),
    volume_max=Decimal("200"),
    volume_step=Decimal("0.01"),
)
XAUUSD = BrokerSpec(
    name="XAUUSDm",
    digits=2,
    point=Decimal("0.01"),
    tick_size=Decimal("0.01"),
    tick_value_loss=Decimal("0.01"),
    volume_min=Decimal("0.01"),
    volume_max=Decimal("100"),
    volume_step=Decimal("0.01"),
)


def _confirmed(**over: object) -> SetupFixture:
    base = dict(
        symbol="EURUSD",
        timeframe_minutes=15,
        bar_time_epoch=1788214500,
        poi_id="BASE_DROP~1788213600",
        poi_type=31,
        direction=-1,
        zone_top=Decimal("1.14693"),
        zone_bottom=Decimal("1.14672"),
        authoritative=True,
        validity=0,
        p5_permission=True,
        lifecycle=7,
    )
    base.update(over)
    return SetupFixture(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# eligibility: the trigger, and what is NOT the trigger
# ---------------------------------------------------------------------------


def test_p5_permission_alone_never_triggers() -> None:
    """The whole point of the two-layer split."""
    plan = plan_for(
        EURUSD, _confirmed(lifecycle=6), Decimal("1.14690"), Decimal("10000")
    )
    assert not plan.eligible
    assert plan.deny_reason == "NOT_CONFIRMED"


@pytest.mark.parametrize(
    ("over", "reason"),
    [
        ({"authoritative": False}, "NOT_AUTHORITATIVE"),
        ({"validity": 1}, "NOT_VALID"),
        ({"validity": 2}, "NOT_VALID"),
        ({"p5_permission": False}, "NO_P5"),
        ({"lifecycle": 0}, "NOT_CONFIRMED"),
        ({"direction": 0}, "NO_DIRECTION"),
    ],
)
def test_every_gate_denies_with_its_own_reason(over: dict, reason: str) -> None:
    plan = plan_for(EURUSD, _confirmed(**over), Decimal("1.14690"), Decimal("10000"))
    assert not plan.eligible
    assert plan.deny_reason == reason


def test_the_full_set_is_eligible() -> None:
    assert plan_for(
        EURUSD, _confirmed(), Decimal("1.14690"), Decimal("10000")
    ).eligible


# ---------------------------------------------------------------------------
# geometry: distal, stop, R, target
# ---------------------------------------------------------------------------


def test_bearish_stop_is_one_tick_above_the_zone_top() -> None:
    plan = plan_for(EURUSD, _confirmed(), Decimal("1.14690"), Decimal("10000"))
    assert plan.distal == Decimal("1.14693")
    assert plan.stop == Decimal("1.14694")
    assert plan.r == Decimal("0.00004")
    # 2R BELOW entry for a sell. 2R is V1 EXECUTION POLICY, not RC5 doctrine.
    assert plan.take == Decimal("1.14682")


def test_bullish_stop_is_one_tick_below_the_zone_bottom() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(direction=1, poi_type=30),
        Decimal("1.14680"),
        Decimal("10000"),
    )
    assert plan.distal == Decimal("1.14672")
    assert plan.stop == Decimal("1.14671")
    assert plan.r == Decimal("0.00009")
    assert plan.take == Decimal("1.14698")


def test_a_stop_on_the_wrong_side_is_denied_not_flipped() -> None:
    """Price already through the zone. There is no V1 trade, not a wider one."""
    plan = plan_for(EURUSD, _confirmed(), Decimal("1.14700"), Decimal("10000"))
    assert not plan.eligible
    assert plan.deny_reason == "STOP_WRONG_SIDE"


def test_a_broker_minimum_distance_denies_rather_than_widening() -> None:
    tight = BrokerSpec(
        name="EURUSDm",
        digits=5,
        point=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        tick_value_loss=Decimal("0.1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("200"),
        volume_step=Decimal("0.01"),
        stops_level=50,
    )
    plan = plan_for(tight, _confirmed(), Decimal("1.14690"), Decimal("10000"))
    assert not plan.eligible
    assert plan.deny_reason == "BROKER_STOP_INVALID"
    # the stop it WOULD have used is still reported, unwidened
    assert plan.stop == Decimal("1.14694")


# ---------------------------------------------------------------------------
# risk
# ---------------------------------------------------------------------------


def test_volume_comes_from_equity_and_stop_distance_only() -> None:
    plan = plan_for(EURUSD, _confirmed(), Decimal("1.14690"), Decimal("10000"))
    # 0.5% of 10,000 = 50.00; 4 ticks x 0.1 = 0.4 per lot; 50 / 0.4 = 125 lots,
    # capped by nothing here and quantized to the 0.01 step.
    assert plan.risk_money == Decimal("50.000")
    assert plan.volume == Decimal("125.00")
    assert plan.realized_risk == Decimal("50.000")


def test_risk_never_rounds_up_to_the_minimum_lot() -> None:
    """The volume counterpart of never silently widening the stop."""
    plan = plan_for(XAUUSD, _confirmed(
        symbol="XAUUSD",
        zone_top=Decimal("2400.00"),
        zone_bottom=Decimal("2380.00"),
    ), Decimal("2390.00"), Decimal("10"))
    assert not plan.eligible
    assert plan.deny_reason == "RISK_BUDGET_EXCEEDED"
    assert plan.realized_risk is not None
    assert plan.realized_risk > plan.risk_money


def test_no_prior_result_can_influence_size() -> None:
    """Structural, not a setting: `plan_for` has no place to put one."""
    import inspect

    params = set(inspect.signature(plan_for).parameters)
    assert params == {
        "spec",
        "fixture",
        "entry",
        "equity",
        "risk_percent",
        "reward_risk",
        "spread",
        "required_margin",
        "max_spread_to_risk",
        "max_margin_fraction",
        "confirmation_close",
        "entry_is_executable",
        "max_entry_distance_spreads",
    }
    # the point of the assertion, stated so a future addition cannot pass by
    # simply being appended to the set above
    for forbidden in (
        "last",
        "previous",
        "prior",
        "streak",
        "loss",
        "win",
        "consecutive",
        "multiplier",
    ):
        assert not any(forbidden in name for name in params), forbidden


# ---------------------------------------------------------------------------
# the fixture line the EA parses
# ---------------------------------------------------------------------------


def test_fixture_line_round_trips_the_field_order_the_ea_reads() -> None:
    line = fixture_line(_confirmed())
    assert line.count("|") == len(FIXTURE_FIELDS) - 1
    assert line.startswith("EURUSD|15|1788214500|")


def test_a_poi_id_containing_the_delimiter_is_refused_loudly() -> None:
    """Found by this suite: the first sample id used `|` as its own separator,
    which would have produced a thirteen-field line the EA silently skips."""
    with pytest.raises(ValueError, match="delimiter"):
        fixture_line(_confirmed(poi_id="BASE_DROP|1788213600"))


def test_the_ea_parser_reads_exactly_this_many_fields() -> None:
    src = _ea_source()
    assert f"StringSplit(line, '|', f) != {len(FIXTURE_FIELDS)}" in src


def test_offline_entry_price_is_marked_pending_not_invented() -> None:
    plan = plan_for(EURUSD, _confirmed(), Decimal("1.14690"), Decimal("10000"))
    assert plan.entry_note == "ENTRY_PRICE_PENDING_TESTER"


# ---------------------------------------------------------------------------
# the MQL5 source has to say the same thing
# ---------------------------------------------------------------------------


def _policy_map() -> dict[str, str]:
    """Parse RC5TerminalPolicy's switch into {event: policy}."""
    src = _ea_source()
    body = src.split("int RC5TerminalPolicy(const int ev)", 1)[1]
    body = body.split("string RC5TerminalName", 1)[0]

    mapping: dict[str, str] = {}
    pending: list[str] = []
    for line in body.splitlines():
        case = re.search(r"case\s+RC5_TE_([A-Z_]+):", line)
        if case:
            pending.append(case.group(1))
            continue
        ret = re.search(r"return\s+(RC5_TP_[A-Z_]+);", line)
        if ret and pending:
            for event in pending:
                mapping[event] = ret.group(1)
            pending = []
    return mapping


def test_the_two_approved_exits_close_in_mql5() -> None:
    policy = _policy_map()
    assert policy["GENUINE_INVALIDATION_CONFIRMED"] == "RC5_TP_CLOSE"
    assert policy["INVALIDATED"] == "RC5_TP_CLOSE"
    assert APPROVED_CLOSE_EVENTS == {
        e for e, p in policy.items() if p == "RC5_TP_CLOSE"
    }


def test_mitigation_and_false_invalidation_never_close_in_mql5() -> None:
    policy = _policy_map()
    for event in NEVER_CLOSE_EVENTS:
        assert policy[event] == "RC5_TP_NO_ACTION", event


def test_the_three_state_migrations_are_recognized_and_never_close() -> None:
    """Author-locked V1 policy: all three migrate the RECORD, not the trade."""
    policy = _policy_map()
    for event in STATE_MIGRATION_EVENTS:
        assert policy[event] == "RC5_TP_STATE_MIGRATION", event
    src = _ea_source()
    assert "_STATE_MIGRATION " in src
    # the interim "pending doctrine" wording must be gone, so the log cannot
    # claim the question is still open after the author closed it
    assert "TERMINAL_POLICY_UNRESOLVED" not in src
    assert "RC5_TP_UNRESOLVED" not in src


def test_state_migration_is_a_distinct_policy_from_plain_no_action() -> None:
    """MITIGATED and a promotion both decline to close, for different reasons,
    and the log has to be able to tell them apart."""
    policy = _policy_map()
    assert policy["MITIGATED"] == "RC5_TP_NO_ACTION"
    assert policy["PROMOTED_TO_ORDER_BLOCK"] == "RC5_TP_STATE_MIGRATION"


def test_a_promoted_record_can_never_open_a_new_position() -> None:
    """No new rule was needed: SUPERSEDED is not VALID."""
    plan = plan_for(
        EURUSD, _confirmed(validity=2), Decimal("1.14690"), Decimal("10000")
    )
    assert not plan.eligible
    assert plan.deny_reason == "NOT_VALID"


def test_the_mql5_trigger_is_liquidity_validated() -> None:
    src = _ea_source()
    assert "#define RC5_LC_LIQUIDITY_VALIDATED     7" in src
    assert "s.lifecycle != RC5_LC_LIQUIDITY_VALIDATED" in src


def test_the_mql5_stop_uses_tick_size_and_never_point() -> None:
    src = _ea_source()
    assert "SYMBOL_TRADE_TICK_SIZE" in src
    assert "distal - spec.tickSize : distal + spec.tickSize" in src


def test_every_order_send_is_behind_the_execution_gate() -> None:
    """Two OrderSend calls, both inside functions that open with the gate."""
    src = _ea_source()
    assert src.count("OrderSend(") == 2
    for fn in ("bool SubmitOrder(", "bool CloseRC5Position("):
        body = src.split(fn, 1)[1][:400]
        assert "CanExecuteHere()" in body, fn


def test_live_execution_stays_disabled_by_default() -> None:
    src = _ea_source()
    assert "input bool   InpExecutionEnabled = false;" in src
    assert "input bool   InpAllowLiveExecution = false;" in src


def test_no_martingale_vocabulary_in_executable_mql5() -> None:
    """Comments say there is none; this checks the CODE, with prose stripped.

    Written the other way round first, it failed on the EA's own comment -- a
    reminder that grepping a source file finds documentation as readily as
    behaviour.
    """
    code = " ".join(
        line.split("//", 1)[0] for line in _ea_source().splitlines()
    ).lower()
    for banned in ("martingale", "grid", "averagedown", "recoverymultiplier"):
        assert banned not in code, banned


# ---------------------------------------------------------------------------
# the duplicate and concurrency guards
# ---------------------------------------------------------------------------


def test_the_signal_id_matches_the_ea_format_field_for_field() -> None:
    fixture = _confirmed()
    assert signal_id(fixture) == "EURUSD|15|BASE_DROP~1788213600|31|-1|1788214500"
    src = _ea_source()
    assert 'StringFormat("%s|%d|%s|%d|%d|%I64d"' in src


def test_two_pois_confirming_on_the_same_bar_are_different_signals() -> None:
    """Why a bar timestamp alone is not the identity."""
    a = _confirmed(poi_id="BASE_DROP~1788213600")
    b = _confirmed(poi_id="EVENING_STAR~1788213600")
    assert a.bar_time_epoch == b.bar_time_epoch
    assert signal_id(a) != signal_id(b)


def test_a_reconfirmation_on_a_later_bar_is_a_new_signal() -> None:
    a = _confirmed()
    b = _confirmed(bar_time_epoch=a.bar_time_epoch + 900)
    assert signal_id(a) != signal_id(b)


def test_a_consumed_signal_is_denied() -> None:
    fixture = _confirmed()
    plan = decide(
        EURUSD,
        fixture,
        Decimal("1.14690"),
        Decimal("10000"),
        consumed_signal_ids={signal_id(fixture)},
    )
    assert not plan.eligible
    assert plan.deny_reason == "SIGNAL_ALREADY_EXECUTED"


def test_a_symbol_that_already_holds_a_position_is_denied() -> None:
    plan = decide(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        symbols_with_open_position={"EURUSDm"},
    )
    assert not plan.eligible
    assert plan.deny_reason == "SYMBOL_POSITION_ACTIVE"


def test_concurrency_is_keyed_on_the_BROKER_symbol_not_the_logical_one() -> None:
    """The fixture says EURUSD; the position is on EURUSDm. Same instrument."""
    assert _confirmed().symbol == "EURUSD"
    assert EURUSD.name == "EURUSDm"
    blocked = decide(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        symbols_with_open_position={"EURUSDm"},
    )
    assert blocked.deny_reason == "SYMBOL_POSITION_ACTIVE"
    # an unrelated symbol must not block it
    allowed = decide(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        symbols_with_open_position={"XAUUSDm"},
    )
    assert allowed.eligible


def test_guards_run_before_any_price_is_read() -> None:
    """Order is part of the contract: a duplicate must not report a stop and a
    volume it was never going to use, and the EA's own pipeline agrees."""
    plan = decide(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        symbols_with_open_position={"EURUSDm"},
    )
    assert plan.stop is None and plan.volume is None

    body = _ea_source().split("bool RC5ProcessSetup(", 1)[1][:900]
    order = [
        body.index("RC5PlanEligibility("),
        body.index("RC5PlanGuards("),
        body.index("RC5PlanPrices("),
        body.index("RC5PlanRisk("),
    ]
    assert order == sorted(order)


# ---------------------------------------------------------------------------
# risk sizing across broker contracts
# ---------------------------------------------------------------------------


def _spec(**over: object) -> BrokerSpec:
    base = dict(
        name="TESTm",
        digits=5,
        point=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        tick_value_loss=Decimal("0.1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("200"),
        volume_step=Decimal("0.01"),
    )
    base.update(over)
    return BrokerSpec(**base)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("spec_over", "equity", "expected_volume"),
    [
        # 4 ticks x 0.1/lot = 0.4 per lot; 0.5% of 1,000 = 5.00 -> 12.5 -> 12.50
        ({}, Decimal("1000"), Decimal("12.50")),
        # a coarser volume step floors, never rounds up (12.5 is already on
        # the 0.1 grid, so it survives intact)
        ({"volume_step": Decimal("0.1")}, Decimal("1000"), Decimal("12.5")),
        # double the tick value halves the size
        ({"tick_value_loss": Decimal("0.2")}, Decimal("1000"), Decimal("6.25")),
        # A coarser tick re-quantizes the STOP as well, so R itself changes:
        # 1.14693 + one 2-point tick snaps to 1.14696, making R 3 coarse ticks
        # rather than 4 fine ones. 5.00 / (3 x 0.1) = 16.66.
        (
            {"tick_size": Decimal("0.00002"), "point": Decimal("0.00002")},
            Decimal("1000"),
            Decimal("16.66"),
        ),
        # the broker's ceiling binds
        ({"volume_max": Decimal("5")}, Decimal("1000"), Decimal("5")),
    ],
)
def test_volume_tracks_the_broker_contract(
    spec_over: dict, equity: Decimal, expected_volume: Decimal
) -> None:
    plan = plan_for(_spec(**spec_over), _confirmed(), Decimal("1.14690"), equity)
    assert plan.eligible
    assert plan.volume == expected_volume


def test_realized_risk_never_exceeds_the_budget_on_any_contract() -> None:
    for step in (Decimal("0.01"), Decimal("0.1"), Decimal("1")):
        for equity in (Decimal("500"), Decimal("1000"), Decimal("25000")):
            plan = plan_for(
                _spec(volume_step=step), _confirmed(), Decimal("1.14690"), equity
            )
            if not plan.eligible:
                assert plan.deny_reason in {"RISK_BUDGET_EXCEEDED", "VOLUME_INVALID"}
                continue
            assert plan.realized_risk is not None and plan.risk_money is not None
            assert plan.realized_risk <= plan.risk_money, (step, equity)


def test_a_volume_max_below_volume_min_has_no_legal_size() -> None:
    plan = plan_for(
        _spec(volume_min=Decimal("1"), volume_max=Decimal("0.5")),
        _confirmed(),
        Decimal("1.14690"),
        Decimal("1000"),
    )
    assert not plan.eligible
    assert plan.deny_reason in {"RISK_BUDGET_EXCEEDED", "VOLUME_INVALID"}


def test_a_wider_stop_takes_a_smaller_size_for_the_same_budget() -> None:
    near = plan_for(EURUSD, _confirmed(), Decimal("1.14690"), Decimal("10000"))
    far = plan_for(EURUSD, _confirmed(), Decimal("1.14650"), Decimal("10000"))
    assert near.r is not None and far.r is not None
    assert far.r > near.r
    assert near.volume is not None and far.volume is not None
    assert far.volume < near.volume


def test_zero_tick_value_is_an_unusable_contract_not_a_free_trade() -> None:
    plan = plan_for(
        _spec(tick_value_loss=Decimal("0")),
        _confirmed(),
        Decimal("1.14690"),
        Decimal("1000"),
    )
    assert not plan.eligible
    assert plan.deny_reason == "RISK_MODEL_INVALID"


# ---------------------------------------------------------------------------
# zero-height zones: real data, and a gap the doctrine does not cover
# ---------------------------------------------------------------------------
#
# Liquidity-level POIs (CURRENT_DAY_LOW, CURRENT_WEEK_HIGH, ...) are LINES, not
# bands: the Layer-A projection emits them with `zone_top == zone_bottom`. The
# tests below do not assert that this is correct or incorrect. They PIN what V1
# as specified actually does with them, because the numbers are surprising and
# an author decision is pending on whether to add a guard.


def _level_poi(**over: object) -> SetupFixture:
    return _confirmed(
        poi_id="CURRENT_DAY_LOW~0c31feb6b40e",
        poi_type=27,
        direction=1,
        zone_top=Decimal("1.14831"),
        zone_bottom=Decimal("1.14831"),
        **over,  # type: ignore[arg-type]
    )


def test_a_zero_height_zone_is_accepted_and_produces_a_one_tick_stop() -> None:
    """MEASURED, not endorsed.

    With `zone_top == zone_bottom`, the distal boundary IS the level, so the
    stop lands one tick beyond it and R collapses to the distance from entry to
    that single price. Nothing in the doctrine refuses this.
    """
    plan = plan_for(EURUSD, _level_poi(), Decimal("1.14832"), Decimal("10000"))
    assert plan.eligible
    assert plan.distal == Decimal("1.14831")
    assert plan.stop == Decimal("1.14830")
    assert plan.r == Decimal("0.00002")


def test_a_tiny_R_produces_an_enormous_position_bounded_only_by_volume_max() -> None:
    """The risk BUDGET is respected; the NOTIONAL is not bounded by anything.

    0.5% of 10,000 is 50.00, and a 2-tick stop costs 0.2 per lot, so the
    budget alone would buy 250 lots. `volume_max` is what stops it at 200 --
    not a risk rule -- and the realized risk (40.00) is then UNDER budget,
    so no risk gate fires either.

    200 lots of EURUSD is roughly a 20,000,000 EUR notional held against a
    2-tick stop. V1 has no margin check and no notional cap, so the broker's
    own margin rejection is the first thing that would refuse it, at runtime.
    """
    plan = plan_for(EURUSD, _level_poi(), Decimal("1.14832"), Decimal("10000"))
    assert plan.volume == EURUSD.volume_max == Decimal("200")
    assert plan.risk_money == Decimal("50.000")
    assert plan.realized_risk == Decimal("40.0")
    assert plan.realized_risk < plan.risk_money


def test_the_spread_can_exceed_R_entirely_and_nothing_refuses_it() -> None:
    """A typical EURUSD spread is ~10 ticks. R here is 2.

    The trade is therefore stopped out by the spread alone, by construction.
    `InpMaxSpreadPoints` exists and defaults to 0 (off), and V1 compares the
    spread to a FIXED input rather than to R, so the default configuration
    does not catch this.
    """
    plan = plan_for(EURUSD, _level_poi(), Decimal("1.14832"), Decimal("10000"))
    assert plan.r is not None
    typical_spread = 10 * EURUSD.tick_size
    assert typical_spread > plan.r
    assert plan.eligible, "V1 as specified does not refuse it"


def test_a_broker_stop_level_does_refuse_the_tiny_stop() -> None:
    """The one existing protection, and it depends entirely on the broker.

    When `SYMBOL_TRADE_STOPS_LEVEL` is non-zero the 2-tick stop is illegal and
    V1 denies. Exness Standard commonly publishes 0, in which case this
    protection is simply absent.
    """
    with_level = BrokerSpec(
        name="EURUSDm",
        digits=5,
        point=Decimal("0.00001"),
        tick_size=Decimal("0.00001"),
        tick_value_loss=Decimal("0.1"),
        volume_min=Decimal("0.01"),
        volume_max=Decimal("200"),
        volume_step=Decimal("0.01"),
        stops_level=10,
    )
    plan = plan_for(with_level, _level_poi(), Decimal("1.14832"), Decimal("10000"))
    assert not plan.eligible
    assert plan.deny_reason == "BROKER_STOP_INVALID"


# ---------------------------------------------------------------------------
# EXECUTION QUALITY GATES — spread/R and margin/equity
# ---------------------------------------------------------------------------
#
# Both are EXECUTION DOCTRINE V1 PARAMETERS, not analytical semantics. They
# exist because the monetary risk budget provably does not cover either
# problem: the pathological case above passed it with room to spare.
#
# Zero-height POIs stay analytically VALID. These gates refuse to TRADE a
# setup; nothing deletes or invalidates a POI.


def test_the_pathological_case_is_now_denied_by_the_spread_gate() -> None:
    """The exact measured case: R = 2 ticks against a ~10 tick spread."""
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14832"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
    )
    assert not plan.eligible
    assert plan.deny_reason == "SPREAD_TO_RISK_INVALID"
    assert plan.spread_to_risk == Decimal("5")
    assert plan.spread_gate == "DENY"


def test_a_zero_height_poi_with_an_acceptable_spread_is_still_eligible() -> None:
    """Geometry is not the disqualifier — execution quality is.

    Same zero-height POI, entry far enough away that R is 70 ticks, so a 10
    tick spread is 14% of R.
    """
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
    )
    assert plan.eligible
    assert plan.spread_gate == "PASS"
    assert plan.r == Decimal("0.00070")


def test_an_ordinary_zone_with_a_wide_spread_is_denied_too() -> None:
    """Not special-cased to zero-height zones."""
    plan = plan_for(
        EURUSD,
        _confirmed(),  # a real 21-tick band
        Decimal("1.14690"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
    )
    assert plan.r == Decimal("0.00004")
    assert not plan.eligible
    assert plan.deny_reason == "SPREAD_TO_RISK_INVALID"


def test_the_spread_boundary_is_inclusive() -> None:
    """spread == 25% of R is ACCEPTED, one tick more is not."""
    at_boundary = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14870"),  # stop is 1.14830, so R = 40 ticks
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,  # exactly 25%
    )
    assert at_boundary.r == Decimal("0.00040")
    assert at_boundary.spread_to_risk == Decimal("0.25")
    assert at_boundary.eligible
    assert at_boundary.spread_gate == "PASS"

    over = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14870"),
        Decimal("10000"),
        spread=11 * EURUSD.tick_size,
    )
    assert not over.eligible
    assert over.deny_reason == "SPREAD_TO_RISK_INVALID"


def test_a_zero_R_is_refused_before_anything_divides_by_it() -> None:
    """R == 0 means entry sits ON the stop.

    It is denied as STOP_WRONG_SIDE rather than R_ZERO, because the wrong-side
    check runs first and `stop >= entry` is true at equality. Both the mirror
    and the EA keep an explicit `r <= 0` guard anyway, since every downstream
    number divides by R.
    """
    plan = plan_for(
        EURUSD, _confirmed(), Decimal("1.14694"), Decimal("10000")
    )
    assert not plan.eligible
    assert plan.deny_reason == "STOP_WRONG_SIDE"
    assert "R_ZERO" in _ea_source()


def test_margin_above_the_ceiling_is_denied() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=EURUSD.tick_size,
        required_margin=Decimal("2500"),  # 25% of equity
    )
    assert not plan.eligible
    assert plan.deny_reason == "MARGIN_EXPOSURE_INVALID"
    assert plan.margin_fraction == Decimal("0.25")
    assert plan.margin_gate == "DENY"


def test_the_margin_boundary_is_inclusive() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=EURUSD.tick_size,
        required_margin=Decimal("2000"),  # exactly 20%
    )
    assert plan.eligible
    assert plan.margin_fraction == Decimal("0.20")
    assert plan.margin_gate == "PASS"


def test_acceptable_margin_does_not_rescue_an_invalid_risk_size() -> None:
    """Different problems, both required. Margin is never consulted here
    because the risk gate denies first."""
    plan = plan_for(
        XAUUSD,
        _confirmed(
            symbol="XAUUSD",
            zone_top=Decimal("2400.00"),
            zone_bottom=Decimal("2380.00"),
        ),
        Decimal("2390.00"),
        Decimal("10"),
        spread=Decimal("0.01"),
        required_margin=Decimal("0.01"),
    )
    assert not plan.eligible
    assert plan.deny_reason == "RISK_BUDGET_EXCEEDED"


def test_acceptable_risk_does_not_rescue_an_invalid_margin() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=EURUSD.tick_size,
        required_margin=Decimal("9999"),
    )
    assert not plan.eligible
    assert plan.deny_reason == "MARGIN_EXPOSURE_INVALID"
    # the risk side HAD passed; it is not what refused the trade
    assert plan.realized_risk is not None
    assert plan.risk_money is not None
    assert plan.realized_risk <= plan.risk_money


def test_all_three_gates_passing_is_what_eligible_means() -> None:
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        required_margin=Decimal("1000"),
    )
    assert plan.eligible
    assert plan.spread_gate == "PASS"
    assert plan.margin_gate == "PASS"
    assert plan.realized_risk is not None and plan.risk_money is not None
    assert plan.realized_risk <= plan.risk_money


def test_an_unevaluable_gate_reports_pending_not_pass() -> None:
    """Offline there is no bid/ask and no broker margin. A gate that could not
    run has NOT been satisfied, and must not read as though it had."""
    plan = plan_for(EURUSD, _level_poi(), Decimal("1.14900"), Decimal("10000"))
    assert plan.eligible
    assert plan.spread_gate == "PENDING_TESTER"
    assert plan.margin_gate == "PENDING_TESTER"


def test_the_mql5_source_implements_both_gates_in_the_right_order() -> None:
    """Spread before sizing, margin after — margin depends on the volume."""
    src = _ea_source()
    assert "input double InpMaxSpreadToRisk  = 0.25;" in src
    assert "input double InpMaxMarginFraction = 0.20;" in src
    assert "SPREAD_TO_RISK_INVALID" in src
    assert "MARGIN_EXPOSURE_INVALID" in src
    # the broker's own number, not a reimplemented margin model
    assert "OrderCalcMargin(" in src

    body = src.split("bool RC5ProcessSetup(", 1)[1][:1400]
    order = [
        body.index("RC5PlanPrices("),
        body.index("RC5SpreadGate("),
        body.index("RC5PlanRisk("),
        body.index("RC5MarginGate("),
    ]
    assert order == sorted(order)


# ---------------------------------------------------------------------------
# THE MIRROR-IMAGE FAILURE: a STALE POI, whose R is enormous
# ---------------------------------------------------------------------------
#
# Found by the reachability walk, which produced the first real
# LIQUIDITY_VALIDATED setup: a BULLISH HAMMER with zone 308.75-312.85 while the
# host bar closed near 4,400. The W1 context series carries 2,000 bars -- about
# 38 years -- so POIs formed when gold traded near $310 are still registered,
# still VALID (price never came back to breach them), and therefore still
# executable under V1.
#
# The spread/R gate does NOT catch this. A pathologically LARGE R makes the
# spread ratio trivially small, so the gate that protects against micro-R sails
# straight past macro-R. These tests pin that, they do not fix it: the fix is a
# proximity rule and V1 has none.


_STALE = dict(
    symbol="XAUUSD",
    poi_id="HAMMER~38983f2ef82a",
    poi_type=0,
    direction=1,
    zone_top=Decimal("312.85"),
    zone_bottom=Decimal("308.75"),
    bar_time_epoch=1788127200,
)

_XAU_LIVE = BrokerSpec(
    name="XAUUSDm",
    digits=2,
    point=Decimal("0.01"),
    tick_size=Decimal("0.01"),
    tick_value_loss=Decimal("0.01"),
    volume_min=Decimal("0.01"),
    volume_max=Decimal("100"),
    volume_step=Decimal("0.01"),
)


def test_a_stale_poi_far_from_price_is_ELIGIBLE_under_V1() -> None:
    """MEASURED on the first real trigger. Every gate passes.

    Entry 4,400 against a zone at 308.75-312.85 gives R = 4,091.26, a take
    profit at 12,582.52 -- nearly three times the current price -- and a
    volume of 0.01 lots. Risk 40.91 of a 50.00 budget, margin 5% of equity,
    spread/R about 0.00005. Nothing refuses it.
    """
    plan = plan_for(
        _XAU_LIVE,
        _confirmed(**_STALE),
        Decimal("4400.00"),
        Decimal("10000"),
        spread=Decimal("0.20"),
        required_margin=Decimal("500"),
    )
    assert plan.eligible
    assert plan.r == Decimal("4091.26")
    assert plan.take == Decimal("12582.52")
    assert plan.volume == Decimal("0.01")
    assert plan.spread_gate == "PASS"
    assert plan.margin_gate == "PASS"


def test_the_spread_gate_cannot_see_this_because_R_is_huge() -> None:
    """The micro-R protection is blind to macro-R, by construction."""
    plan = plan_for(
        _XAU_LIVE,
        _confirmed(**_STALE),
        Decimal("4400.00"),
        Decimal("10000"),
        spread=Decimal("0.20"),
    )
    assert plan.spread_to_risk is not None
    assert plan.spread_to_risk < Decimal("0.0001")
    assert plan.spread_gate == "PASS"


def test_v1_has_no_proximity_requirement_at_all() -> None:
    """The gap, stated as a test rather than as a comment.

    Executing "at a POI" implies price is interacting with it, but the entry
    rule says only "the first tradable price AFTER confirmation". Entry
    4,400 and entry 312 are both accepted against the same zone; only the
    resulting size differs.
    """
    far = plan_for(
        _XAU_LIVE, _confirmed(**_STALE), Decimal("4400.00"), Decimal("10000")
    )
    near = plan_for(
        _XAU_LIVE, _confirmed(**_STALE), Decimal("312.00"), Decimal("10000")
    )
    assert far.eligible and near.eligible
    assert far.r is not None and near.r is not None
    assert far.r > near.r * 1000
    assert far.volume == Decimal("0.01")
    assert near.volume == Decimal("15.33")


# ---------------------------------------------------------------------------
# TWO-STAGE POI PROXIMITY — the gate that closes the stale-POI hole
# ---------------------------------------------------------------------------
#
# STAGE 1 is eligibility, from the causally available confirmation close.
# STAGE 2 is the ACTUAL executable price at the moment of the order.
# Both required. Tolerance = max(tick_size, spread * InpMaxEntryDistanceSpreads).
#
# Analytical validity is untouched: the stale POI below is still a valid POI,
# V1 simply refuses to trade it. There is deliberately NO POI AGE CAP.


def test_zone_distance_is_zero_inside_and_edge_relative_outside() -> None:
    top, bottom = Decimal("4467.06"), Decimal("4450.54")
    assert zone_distance(Decimal("4461.29"), top, bottom) == 0
    assert zone_distance(top, top, bottom) == 0
    assert zone_distance(bottom, top, bottom) == 0
    assert zone_distance(Decimal("4470.06"), top, bottom) == Decimal("3.00")
    assert zone_distance(Decimal("4448.54"), top, bottom) == Decimal("2.00")


def test_the_tolerance_is_broker_derived_not_R_or_price_derived() -> None:
    """One tick floor, one spread otherwise."""
    assert proximity_tolerance(EURUSD, None) == EURUSD.tick_size
    assert proximity_tolerance(EURUSD, Decimal("0.00010")) == Decimal("0.00010")
    # a spread narrower than a tick cannot lower the floor
    assert proximity_tolerance(EURUSD, Decimal("0.000001")) == EURUSD.tick_size


@pytest.mark.parametrize("direction", [1, -1])
def test_a_confirmation_inside_the_zone_passes(direction: int) -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(direction=direction),
        Decimal("1.14690") if direction < 0 else Decimal("1.14680"),
        Decimal("10000"),
        confirmation_close=Decimal("1.14680"),  # inside 1.14672-1.14693
    )
    assert plan.confirmation_gate == "PASS"
    assert plan.confirmation_distance == 0


def test_one_tick_outside_the_zone_passes_on_the_tick_floor() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        confirmation_close=Decimal("1.14694"),  # one tick above 1.14693
    )
    assert plan.confirmation_distance == EURUSD.tick_size
    assert plan.confirmation_gate == "PASS"


def test_exactly_one_spread_away_passes_the_boundary() -> None:
    spread = 10 * EURUSD.tick_size
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=spread,
        confirmation_close=Decimal("1.14703"),  # 10 ticks above the top
    )
    assert plan.confirmation_distance == spread
    assert plan.proximity_tolerance_used == spread
    assert plan.confirmation_gate == "PASS"


def test_one_tick_beyond_the_tolerance_is_denied() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14704"),  # 11 ticks above the top
    )
    assert not plan.eligible
    assert plan.deny_reason == "CONFIRMATION_PROXIMITY_INVALID"
    assert plan.confirmation_gate == "DENY"


def test_THE_STALE_POI_IS_NOW_DENIED() -> None:
    """The permanent regression for the first trigger ever found.

    A HAMMER at 308.75-312.85 confirmed while gold traded near 4,400. It passed
    the monetary risk, spread/R and margin gates simultaneously; proximity is
    what refuses it.
    """
    plan = plan_for(
        _XAU_LIVE,
        _confirmed(**_STALE),
        Decimal("4400.00"),
        Decimal("10000"),
        spread=Decimal("0.20"),
        required_margin=Decimal("500"),
        confirmation_close=Decimal("4400.00"),
    )
    assert not plan.eligible
    assert plan.deny_reason == "CONFIRMATION_PROXIMITY_INVALID"
    assert plan.confirmation_distance == Decimal("4087.15")
    assert plan.proximity_tolerance_used == Decimal("0.20")


def test_stage_2_denies_an_entry_that_jumped_away_after_confirmation() -> None:
    """Confirmation was fine; the fill would not be."""
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14750"),  # far above the zone by the time we can fill
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14680"),
        entry_is_executable=True,
    )
    assert plan.confirmation_gate == "PASS"
    assert not plan.eligible
    assert plan.deny_reason == "ENTRY_PROXIMITY_INVALID"
    assert plan.entry_gate == "DENY"


def test_stage_2_passes_when_the_fill_is_still_at_the_zone() -> None:
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        spread=EURUSD.tick_size,
        confirmation_close=Decimal("1.14680"),
        entry_is_executable=True,
    )
    assert plan.confirmation_gate == "PASS"
    assert plan.entry_gate == "PASS"
    assert plan.eligible


def test_a_hypothetical_entry_never_reports_stage_2_as_passed() -> None:
    """The anti-fabrication rule, as a test."""
    plan = plan_for(
        EURUSD,
        _confirmed(),
        Decimal("1.14690"),
        Decimal("10000"),
        confirmation_close=Decimal("1.14680"),
    )
    assert plan.confirmation_gate == "PASS"
    assert plan.entry_gate == "PENDING_TESTER"


def test_a_zero_height_poi_on_its_level_still_reaches_the_later_gates() -> None:
    """Zero height is not itself disqualifying — the other gates decide."""
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),  # exactly on the level
    )
    assert plan.confirmation_gate == "PASS"
    assert plan.confirmation_distance == 0
    assert plan.eligible


def test_a_zero_height_poi_far_from_its_level_is_denied_on_proximity() -> None:
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.15200"),
    )
    assert not plan.eligible
    assert plan.deny_reason == "CONFIRMATION_PROXIMITY_INVALID"


def test_proximity_passing_does_not_rescue_a_failing_spread_gate() -> None:
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14832"),  # R = 2 ticks
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),
    )
    assert plan.confirmation_gate == "PASS"
    assert not plan.eligible
    assert plan.deny_reason == "SPREAD_TO_RISK_INVALID"


def test_proximity_and_spread_passing_do_not_rescue_a_failing_margin() -> None:
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),
        required_margin=Decimal("9999"),
    )
    assert plan.confirmation_gate == "PASS"
    assert plan.spread_gate == "PASS"
    assert not plan.eligible
    assert plan.deny_reason == "MARGIN_EXPOSURE_INVALID"


def test_r_and_tp_diagnostics_are_recorded_and_never_enforced() -> None:
    """V1 has NO maximum-R and NO maximum-TP gate. These exist so one can be
    calibrated later from evidence rather than guessed at now."""
    plan = plan_for(
        EURUSD,
        _level_poi(),
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),
    )
    assert plan.eligible
    assert plan.r_ticks == Decimal("70")
    assert plan.r_over_entry is not None and plan.r_over_entry > 0
    assert plan.tp_distance == Decimal("0.00140")  # 2R
    assert plan.tp_over_entry is not None
    import inspect

    params = set(inspect.signature(plan_for).parameters)
    assert not any("max_r" in n or "max_tp" in n for n in params)


def test_the_locked_gate_order_is_what_the_mql5_pipeline_does() -> None:
    """Proximity BEFORE geometry and sizing, margin last.

    ONE DOCUMENTED DEVIATION from the numbered list in the instruction: the
    duplicate / concurrency guard runs EARLY here, not at position 12. It is
    the cheapest possible refusal and nothing between eligibility and execution
    can change its answer, so running it late would only spend price, risk and
    margin work on a signal already known to be spent -- which is the same
    rationale given for putting proximity before risk.
    """
    src = _ea_source()
    assert "input double InpMaxEntryDistanceSpreads = 1.0;" in src
    assert "CONFIRMATION_PROXIMITY_INVALID" in src
    assert "ENTRY_PROXIMITY_INVALID" in src

    prices = src.split("bool RC5PlanPrices(", 1)[1][:2000]
    order = [
        prices.index("RC5ConfirmationProximity("),
        prices.index("RC5EntryProximity("),
        prices.index("RC5Distal(s)"),
    ]
    assert order == sorted(order)

    body = src.split("bool RC5ProcessSetup(", 1)[1][:1400]
    pipeline = [
        body.index("RC5PlanEligibility("),
        body.index("RC5PlanGuards("),
        body.index("RC5PlanPrices("),
        body.index("RC5SpreadGate("),
        body.index("RC5PlanRisk("),
        body.index("RC5MarginGate("),
    ]
    assert pipeline == sorted(pipeline)
