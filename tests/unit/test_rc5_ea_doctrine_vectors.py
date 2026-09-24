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
    signal_id,
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
    }


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
