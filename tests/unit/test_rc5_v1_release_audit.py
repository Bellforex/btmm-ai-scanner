"""RC5 EXECUTION DOCTRINE V1 — the offline release audit, as tests.

A document claiming that six places agree about `InpRiskPercent` is worth less
than a test that reads all six and fails when they stop agreeing. So this file
IS the audit: it reads the MQL5 source, the tester `.set` files, the doctrine
document and the Python mirror, and asserts they say the same thing.

It covers:

* **Track A** — every V1 parameter, one row per source.
* **Track B** — the locked gate order, in the MQL5 pipeline itself.
* **Tracks C/D/E** — deterministic execution TRACES for the two goldens, the
  stale POI and the zero-height case, pinned so "risk was never sized because
  proximity refused first" is machine-checkable rather than asserted.
* **Track F** — margin PENDING semantics, and the line between a synthetic
  unit-vector margin and a real broker one.
"""

from __future__ import annotations

import re
from decimal import Decimal
from pathlib import Path

import pytest

from tools.rc5_ea_fixtures import (  # type: ignore[import-not-found]
    MAX_ENTRY_DISTANCE_SPREADS,
    MAX_MARGIN_FRACTION,
    MAX_SPREAD_TO_RISK,
    BrokerSpec,
    SetupFixture,
    decide,
    plan_for,
    signal_id,
)

_REPO = Path(__file__).resolve().parents[2]
_EA = _REPO / "mt5" / "Experts" / "RC5_EA.mq5"
_DOCTRINE = (
    _REPO / "docs" / "validation" / "BTRC_V1_RC5_EXECUTION_DOCTRINE_V1.md"
)
_TESTER = _REPO / "mt5" / "Tester"


def _ea() -> str:
    return _EA.read_text(encoding="utf-8-sig")


def _doctrine() -> str:
    return _DOCTRINE.read_text(encoding="utf-8")


def _ea_default(name: str) -> str:
    """The `input` default as the compiler sees it."""
    match = re.search(
        rf"^input\s+\w+\s+{re.escape(name)}\s*=\s*([^;]+);", _ea(), re.MULTILINE
    )
    assert match, f"{name} is not an input in the EA"
    return match.group(1).strip()


def _set_value(symbol: str, name: str) -> str:
    """The value a tester profile overrides it with."""
    text = (_TESTER / f"RC5_{symbol}m.set").read_text(encoding="utf-8")
    match = re.search(rf"^{re.escape(name)}=([^|\r\n]*)", text, re.MULTILINE)
    assert match, f"{name} missing from RC5_{symbol}m.set"
    return match.group(1).strip()


# ---------------------------------------------------------------------------
# TRACK A — parameter consistency, one assertion per source
# ---------------------------------------------------------------------------

#: parameter -> (expected EA default, expected tester value, python mirror)
V1_PARAMETERS: tuple[tuple[str, str, str, Decimal | None], ...] = (
    ("InpRiskPercent", "0.5", "0.5", Decimal("0.5")),
    ("InpRewardRisk", "2.0", "2.0", Decimal("2.0")),
    ("InpMaxSpreadToRisk", "0.25", "0.25", MAX_SPREAD_TO_RISK),
    ("InpMaxMarginFraction", "0.20", "0.20", MAX_MARGIN_FRACTION),
    (
        "InpMaxEntryDistanceSpreads",
        "1.0",
        "1.0",
        MAX_ENTRY_DISTANCE_SPREADS,
    ),
    ("InpExecutionEnabled", "false", "true", None),
    ("InpAllowLiveExecution", "false", "false", None),
    #: Safety-critical and DELIBERATELY different between sources: the EA
    #: default is false and only a tester profile sets it true. It is
    #: inert on a live chart regardless -- see test_rc5_licensing.
    ("InpLicenseTesterBypass", "false", "true", None),
)


@pytest.mark.parametrize(
    ("name", "ea_default", "tester_value", "mirror"),
    V1_PARAMETERS,
    ids=[p[0] for p in V1_PARAMETERS],
)
def test_every_v1_parameter_agrees_across_every_source(
    name: str, ea_default: str, tester_value: str, mirror: Decimal | None
) -> None:
    assert _ea_default(name) == ea_default, "EA default drifted"
    for symbol in ("XAUUSD", "EURUSD", "GBPUSD"):
        assert _set_value(symbol, name) == tester_value, f"{symbol} .set drifted"
    if mirror is not None:
        # the documentation states the number, and the Python mirror uses it
        assert str(mirror) in _doctrine() or f"{mirror:g}" in _doctrine()
        assert Decimal(ea_default) == mirror, "EA and Python mirror disagree"


def test_execution_is_armed_in_the_tester_and_nowhere_else() -> None:
    """The one parameter that is DELIBERATELY different between sources."""
    assert _ea_default("InpExecutionEnabled") == "false"
    assert _ea_default("InpAllowLiveExecution") == "false"
    for symbol in ("XAUUSD", "EURUSD", "GBPUSD"):
        assert _set_value(symbol, "InpExecutionEnabled") == "true"
        # and the second arm is NEVER set in a profile, which is what makes a
        # tester file unable to arm a live account
        assert _set_value(symbol, "InpAllowLiveExecution") == "false"


def test_no_v1_threshold_exists_that_the_audit_does_not_cover() -> None:
    """A new `Inp*` threshold must be added to `V1_PARAMETERS` deliberately.

    Catches the failure mode where a parameter is introduced, documented
    nowhere, and quietly diverges between the EA and a tester profile.
    """
    declared = set(re.findall(r"^input\s+\w+\s+(Inp\w+)", _ea(), re.MULTILINE))
    audited = {p[0] for p in V1_PARAMETERS}
    #: Inputs that are not execution-policy thresholds.
    infrastructure = {
        "InpSymbolRoots",
        "InpHostTF",
        "InpMagic",
        "InpSlippagePoints",
        "InpSetupFile",
        "InpMaxSpreadPoints",
        "InpVerbose",
        # Licensing: transport and cadence, not execution policy. The one
        # licence input that IS cross-source (InpLicenseTesterBypass) is
        # audited in V1_PARAMETERS above; the rest are covered by
        # tests/unit/test_rc5_licensing.py.
        "InpLicenseKey",
        "InpLicenseUrl",
        "InpLicenseRecheckMinutes",
        "InpLicenseLeaseHours",
    }
    assert declared - audited - infrastructure == set()


# ---------------------------------------------------------------------------
# TRACK B — the locked gate order, proven against the MQL5 source
# ---------------------------------------------------------------------------

#: The author-locked V1 order. Position matters: everything from index 4 on is
#: EXPENSIVE (a market quote, a risk model, `OrderCalcMargin`) and must not run
#: for a signal the two cheap invariant guards already refused.
LOCKED_ORDER: tuple[str, ...] = (
    "RC5PlanEligibility(",
    "RC5PlanGuards(",
    "RC5PlanPrices(",
    "RC5SpreadGate(",
    "RC5PlanRisk(",
    "RC5MarginGate(",
    "SubmitOrder(",
)


def test_the_mql5_pipeline_follows_the_locked_order() -> None:
    body = _ea().split("bool RC5ProcessSetup(", 1)[1][:1600]
    positions = [body.index(step) for step in LOCKED_ORDER]
    assert positions == sorted(positions), LOCKED_ORDER


def test_the_cheap_guards_come_before_any_expensive_work() -> None:
    """The regression that matters: if someone moves quote, risk or margin
    work ahead of the duplicate/concurrency guards, this fails."""
    body = _ea().split("bool RC5ProcessSetup(", 1)[1][:1600]
    guards = body.index("RC5PlanGuards(")
    for expensive in ("RC5PlanPrices(", "RC5PlanRisk(", "RC5MarginGate("):
        assert body.index(expensive) > guards, expensive


def test_proximity_runs_before_geometry_inside_the_pricing_step() -> None:
    prices = _ea().split("bool RC5PlanPrices(", 1)[1][:2200]
    positions = [
        prices.index("RC5ConfirmationProximity("),
        prices.index("RC5EntryProximity("),
        prices.index("RC5Distal(s)"),
    ]
    assert positions == sorted(positions)


def test_order_calc_margin_is_called_exactly_once_and_late() -> None:
    src = _ea()
    assert src.count("OrderCalcMargin(") == 1
    body = src.split("bool RC5ProcessSetup(", 1)[1][:1600]
    assert body.index("RC5MarginGate(") > body.index("RC5PlanRisk(")


# ---------------------------------------------------------------------------
# TRACKS C / D / E — deterministic execution traces
# ---------------------------------------------------------------------------

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


def _gold(**over: object) -> SetupFixture:
    base = dict(
        symbol="XAUUSD",
        timeframe_minutes=15,
        bar_time_epoch=1788129900,
        poi_id="HAMMER~82c481350728",
        poi_type=0,
        direction=1,
        zone_top=Decimal("4467.06"),
        zone_bottom=Decimal("4450.54"),
        authoritative=True,
        validity=0,
        p5_permission=True,
        lifecycle=7,
    )
    base.update(over)
    return SetupFixture(**base)  # type: ignore[arg-type]


GOLDEN_1 = _gold()
GOLDEN_2 = _gold(
    bar_time_epoch=1788878700,
    poi_id="MORNING_STAR~cf5314af21ab",
    poi_type=1,
    zone_top=Decimal("4399.54"),
    zone_bottom=Decimal("4391.07"),
)
GOLDEN_CLOSE = {
    GOLDEN_1.poi_id: Decimal("4461.29"),
    GOLDEN_2.poi_id: Decimal("4398.65"),
}

#: TRACK C. The offline trace STOPS at the entry, because offline there is no
#: fill price. Anything past this point would be fabricated.
EXPECTED_GOLDEN_TRACE = (
    "ANALYTICAL_ELIGIBLE",
    "LIQUIDITY_VALIDATED",
    "DUPLICATE_CLEAR",
    "CONCURRENCY_CLEAR",
    "CONFIRMATION_PROXIMITY_PASS",
    "ENTRY_PRICE_PENDING_TESTER",
)


@pytest.mark.parametrize("fixture", (GOLDEN_1, GOLDEN_2), ids=lambda f: f.poi_id)
def test_the_golden_offline_trace_stops_at_the_entry(
    fixture: SetupFixture,
) -> None:
    plan = decide(
        XAUUSD,
        fixture,
        Decimal("4460.00"),  # hypothetical, and declared as such
        Decimal("10000"),
        confirmation_close=GOLDEN_CLOSE[fixture.poi_id],
    )
    assert plan.trace[: len(EXPECTED_GOLDEN_TRACE)] == EXPECTED_GOLDEN_TRACE
    assert plan.confirmation_gate == "PASS"
    assert plan.entry_gate == "PENDING_TESTER"
    # the pipeline is PENDING, never READY, without a real fill
    assert "EXECUTION_READY" not in plan.trace
    assert plan.trace[-1] == "PENDING_TESTER"


#: TRACK D. The stale POI. Everything after proximity is ABSENT, which is the
#: whole point: risk, volume and margin never run.
EXPECTED_STALE_TRACE = (
    "ANALYTICAL_ELIGIBLE",
    "LIQUIDITY_VALIDATED",
    "DUPLICATE_CLEAR",
    "CONCURRENCY_CLEAR",
    "CONFIRMATION_PROXIMITY_INVALID",
)

STALE = _gold(
    poi_id="HAMMER~38983f2ef82a",
    zone_top=Decimal("312.85"),
    zone_bottom=Decimal("308.75"),
    bar_time_epoch=1788127200,
)


def test_the_stale_poi_trace_ends_at_proximity_and_costs_nothing_more() -> None:
    plan = decide(
        XAUUSD,
        STALE,
        Decimal("4400.00"),
        Decimal("10000"),
        spread=Decimal("0.20"),
        required_margin=Decimal("500"),
        confirmation_close=Decimal("4400.00"),
    )
    assert plan.trace == EXPECTED_STALE_TRACE
    assert plan.deny_reason == "CONFIRMATION_PROXIMITY_INVALID"
    # PROOF, not narration: no later stage appears in the trace at all
    for later in (
        "DISTAL_SL_OK",
        "R_POSITIVE",
        "SPREAD_TO_RISK_PASS",
        "RISK_SIZED",
        "VOLUME_LEGAL",
        "MARGIN_PASS",
    ):
        assert later not in plan.trace, later
    assert plan.r is None
    assert plan.volume is None
    assert plan.required_margin is None


#: TRACK E. The zero-height micro-R case: proximity passes, spread/R refuses,
#: and margin is never evaluated.
EXPECTED_ZERO_HEIGHT_TRACE = (
    "ANALYTICAL_ELIGIBLE",
    "LIQUIDITY_VALIDATED",
    "DUPLICATE_CLEAR",
    "CONCURRENCY_CLEAR",
    "CONFIRMATION_PROXIMITY_PASS",
    "ENTRY_PROXIMITY_PASS",
    "DISTAL_SL_OK",
    "R_POSITIVE",
    "SPREAD_TO_RISK_INVALID",
)

LEVEL_POI = SetupFixture(
    symbol="EURUSD",
    timeframe_minutes=15,
    bar_time_epoch=1789724700,
    poi_id="CURRENT_DAY_LOW~0c31feb6b40e",
    poi_type=27,
    direction=1,
    zone_top=Decimal("1.14831"),
    zone_bottom=Decimal("1.14831"),
    authoritative=True,
    validity=0,
    p5_permission=True,
    lifecycle=7,
)


def test_the_zero_height_trace_ends_at_spread_and_never_reaches_margin() -> None:
    plan = decide(
        EURUSD,
        LEVEL_POI,
        Decimal("1.14832"),  # R = 2 ticks
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        required_margin=Decimal("1"),
        confirmation_close=Decimal("1.14831"),
        entry_is_executable=True,
    )
    assert plan.trace == EXPECTED_ZERO_HEIGHT_TRACE
    assert plan.deny_reason == "SPREAD_TO_RISK_INVALID"
    for later in ("RISK_SIZED", "VOLUME_LEGAL", "MARGIN_PASS"):
        assert later not in plan.trace, later
    assert plan.required_margin is None


def test_a_consumed_signal_costs_nothing_beyond_the_duplicate_guard() -> None:
    """The cheap-refusal guarantee the locked order exists to provide."""
    plan = decide(
        XAUUSD,
        GOLDEN_1,
        Decimal("4460.00"),
        Decimal("10000"),
        consumed_signal_ids={signal_id(GOLDEN_1)},
        confirmation_close=GOLDEN_CLOSE[GOLDEN_1.poi_id],
    )
    assert plan.trace == (
        "ANALYTICAL_ELIGIBLE",
        "LIQUIDITY_VALIDATED",
        "SIGNAL_ALREADY_EXECUTED",
    )
    assert plan.confirmation_distance is None
    assert plan.r is None


def test_an_occupied_symbol_costs_nothing_beyond_the_concurrency_guard() -> None:
    plan = decide(
        XAUUSD,
        GOLDEN_1,
        Decimal("4460.00"),
        Decimal("10000"),
        symbols_with_open_position={"XAUUSDm"},
        confirmation_close=GOLDEN_CLOSE[GOLDEN_1.poi_id],
    )
    assert plan.trace == (
        "ANALYTICAL_ELIGIBLE",
        "LIQUIDITY_VALIDATED",
        "DUPLICATE_CLEAR",
        "SYMBOL_POSITION_ACTIVE",
    )
    assert plan.confirmation_distance is None


# ---------------------------------------------------------------------------
# TRACK F — margin PENDING semantics
# ---------------------------------------------------------------------------


def test_an_absent_margin_reports_pending_and_never_pass() -> None:
    """No `OrderCalcMargin` exists offline. A gate that could not run has not
    been satisfied, and must not read as though it had."""
    plan = plan_for(
        EURUSD,
        LEVEL_POI,
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),
    )
    assert plan.eligible
    assert plan.margin_gate == "PENDING_TESTER"
    assert plan.required_margin is None
    assert "MARGIN_PASS" not in plan.trace


def test_a_synthetic_margin_is_marked_by_the_caller_not_invented() -> None:
    """A vector may supply a deterministic margin; the mirror never conjures one.

    The distinction that matters: `required_margin` is ALWAYS a value the
    caller passed in. There is no code path that estimates it, so a PASS can
    only ever come from a number someone supplied deliberately.
    """
    plan = plan_for(
        EURUSD,
        LEVEL_POI,
        Decimal("1.14900"),
        Decimal("10000"),
        spread=10 * EURUSD.tick_size,
        confirmation_close=Decimal("1.14831"),
        required_margin=Decimal("1000"),  # synthetic, stated here
    )
    assert plan.margin_gate == "PASS"
    assert plan.required_margin == Decimal("1000")
    assert "MARGIN_PASS" in plan.trace

    source = (_REPO / "tools" / "rc5_ea_fixtures.py").read_text(encoding="utf-8")
    # no margin MODEL anywhere in the mirror
    assert "contract_size *" not in source
    assert "/ leverage" not in source


def test_the_ea_takes_its_margin_from_the_broker() -> None:
    src = _ea()
    assert "OrderCalcMargin(" in src
    assert "MARGIN_UNAVAILABLE" in src, "a broker that will not price it must deny"


# ---------------------------------------------------------------------------
# RELEASE ARTIFACT INTEGRITY
# ---------------------------------------------------------------------------


def test_the_installed_ea_matches_the_repository() -> None:
    """Caught a real one: the terminal held the PRE-FIX build.

    The EA had been recompiled in the repository after the signal-id separator
    changed to `~`, but the copy installed in the MetaTrader data folder was
    never refreshed. Both copies compiled cleanly and described themselves
    identically; only their hashes disagreed. A tester run would have exercised
    the old build and emitted pipe-bearing signal ids the parser now refuses.

    Skips with an explicit reason where no terminal exists, rather than
    reporting success for a check that could not run.
    """
    from tools.rc5_release_integrity import (  # type: ignore[import-not-found]
        check_installed_ea,
        installed_ea_paths,
    )

    if installed_ea_paths() is None:
        pytest.skip("no MetaTrader data folder on this machine")
    result = check_installed_ea()
    assert result.ok, result.detail


def test_view_regenerates_from_core_without_a_diff() -> None:
    """The committed VIEW must be exactly what the composer produces.

    PANEL has its own dedicated suite (`test_rc5_panel_composition.py`); this
    asserts the one artifact the release pair depends on, rather than writing
    a second half-check that could pass vacuously.
    """
    from tools.rc5_compose import (  # type: ignore[import-not-found]
        CORE,
        VIEW,
        VIEW_PART,
        compose_view,
    )

    core = CORE.read_bytes().decode("utf-8")
    part = VIEW_PART.read_bytes().decode("utf-8")
    assert VIEW.read_bytes().decode("utf-8") == compose_view(core, part)


def test_string_inputs_in_set_files_carry_no_optimization_suffix() -> None:
    """Proved by a real tester run, not by reading the docs.

    With `||...||N` attached, MT5 passed the WHOLE line as the string value:
    `InpSymbolRoots` became `XAUUSD||XAUUSD||XAUUSD||XAUUSD||N`, no symbol
    resolved, and `OnInit` correctly returned INIT_FAILED. Numeric and bool
    inputs parse the suffixed form fine; strings do not.

    The earlier parameter audit was blind to this because `_set_value` splits
    at the first `|` — it read the value I HOPED MT5 would read, rather than
    the whole line MT5 actually reads.
    """
    string_inputs = set(
        re.findall(r"^input\s+string\s+(Inp\w+)", _ea(), re.MULTILINE)
    )
    assert string_inputs, "no string inputs found; the regex has drifted"

    for symbol in ("XAUUSD", "EURUSD", "GBPUSD"):
        text = (_TESTER / f"RC5_{symbol}m.set").read_text(encoding="utf-8")
        for line in text.splitlines():
            if line.startswith(";") or "=" not in line:
                continue
            name = line.split("=", 1)[0].strip()
            if name in string_inputs:
                assert "|" not in line, f"{symbol}: {name} carries a suffix"


# ---------------------------------------------------------------------------
# MARGIN DENY REACHABILITY — proved, not assumed
# ---------------------------------------------------------------------------


def test_margin_deny_is_unreachable_while_the_spread_gate_passes() -> None:
    """MEASURED from the tester's own XAUUSDm spec, then proved algebraically.

    The two gates constrain R in opposite directions:

        spread/R <= 0.25   requires  R >= 4 * spread
        margin   >  0.20*E requires  R <  k / 0.20

    On the observed account those ranges do not overlap, so
    `MARGIN_EXPOSURE_INVALID` cannot fire. That is why no tester harness was
    built to force it: the branch is not merely untested here, it is
    unreachable, and a synthetic case would have verified a situation this
    account cannot produce.

    It becomes reachable at lower leverage, which the test states explicitly so
    the conclusion is scoped rather than absolute.
    """
    tick = Decimal("0.001")  # SYMBOL_TRADE_TICK_SIZE, observed
    tick_value = Decimal("0.1")  # SYMBOL_TRADE_TICK_VALUE_LOSS, observed
    price = Decimal("4461.849")  # observed entry
    contract = Decimal("100")
    leverage = Decimal("500")  # observed 1:500
    equity = Decimal("10000")
    spread = Decimal("0.260")  # observed

    def volume(r: Decimal) -> Decimal:
        return (Decimal("0.005") * equity) / ((r / tick) * tick_value)

    def margin_fraction(r: Decimal) -> Decimal:
        return (volume(r) * price * contract) / (leverage * equity)

    # the model reproduces the observed GOLDEN 1 row
    assert round(volume(Decimal("11.310")), 2) == Decimal("0.04")
    assert round(margin_fraction(Decimal("11.310")), 4) == Decimal("0.0039")

    r_min_allowed = spread / MAX_SPREAD_TO_RISK  # 1.04
    assert r_min_allowed == Decimal("1.04")

    # the LARGEST margin fraction still compatible with the spread gate
    worst = margin_fraction(r_min_allowed)
    assert worst < MAX_MARGIN_FRACTION, worst
    assert round(worst, 4) == Decimal("0.0429")  # 4.29%, against a 20% limit

    # and the R the margin gate would need is far below what spread/R permits
    k = (Decimal("0.005") * equity * tick * price * contract) / (
        tick_value * leverage * equity
    )
    r_needed = k / MAX_MARGIN_FRACTION
    assert r_needed < r_min_allowed
    assert round(r_min_allowed / r_needed, 2) == Decimal("4.66")

    # scope: it IS reachable on a lower-leverage account
    leverage_threshold = leverage * worst / MAX_MARGIN_FRACTION
    assert Decimal("100") < leverage_threshold < Decimal("110")
