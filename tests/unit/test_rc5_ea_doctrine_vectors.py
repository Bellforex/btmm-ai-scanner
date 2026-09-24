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
    UNRESOLVED_EVENTS,
    BrokerSpec,
    SetupFixture,
    fixture_line,
    plan_for,
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


def test_the_three_unresolved_states_are_recognized_and_inert_in_mql5() -> None:
    policy = _policy_map()
    for event in UNRESOLVED_EVENTS:
        assert policy[event] == "RC5_TP_UNRESOLVED", event
    assert "TERMINAL_POLICY_UNRESOLVED" in _ea_source()


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
