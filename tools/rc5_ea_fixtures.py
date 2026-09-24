"""RC5 Execution Doctrine V1 — the Python side of the MT5 parity harness.

TWO LAYERS, KEPT APART. Everything RC5 is analytical: the frozen engine decides
POI identity, authority, validity, P5 permission and lifecycle, and it never
specifies an order. Everything here is Execution Doctrine V1, a separate
downstream layer authored after an audit established that RC5 never contained
an execution contract. Nothing in this module is a claim about what the scanner
has always done.

What V1 borrows from RC5 (derived, not invented):

* the trigger is ``LIQUIDITY_VALIDATED``, the last analytical state the frozen
  engine assigns;
* the stop sits one executable tick beyond the DISTAL boundary, which is read
  out of ``poi/lifecycle.py``'s breach rule rather than chosen here;
* the only two events that close are the two the engine calls genuine
  invalidation.

What V1 decides for itself, as EXECUTION POLICY: a 2R target, a 0.5% research
risk fraction and one position per symbol. RC5 has never specified a reward
multiple or a risk fraction.

This module exists so the MQL5 EA can be checked against Python arithmetic
instead of against itself. `tests/unit/test_rc5_ea_doctrine_vectors.py` pins
both the numbers and the MQL5 source that has to agree with them.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_DOWN, ROUND_HALF_UP, Decimal

__all__ = [
    "APPROVED_CLOSE_EVENTS",
    "FIXTURE_FIELDS",
    "MAX_MARGIN_FRACTION",
    "MAX_SPREAD_TO_RISK",
    "NEVER_CLOSE_EVENTS",
    "STATE_MIGRATION_EVENTS",
    "BrokerSpec",
    "SetupFixture",
    "TradePlan",
    "decide",
    "fixture_line",
    "guard_deny",
    "plan_for",
    "signal_id",
]

#: The EA's fixture line, in the exact order `ParseFixtureLine` reads it.
FIXTURE_FIELDS = (
    "symbol",
    "timeframe_minutes",
    "bar_time_epoch",
    "poi_id",
    "poi_type",
    "direction",
    "zone_top",
    "zone_bottom",
    "authoritative",
    "validity",
    "p5_permission",
    "lifecycle",
)

#: Exactly the two events approved as V1 semantic exits.
APPROVED_CLOSE_EVENTS = frozenset(
    {"GENUINE_INVALIDATION_CONFIRMED", "INVALIDATED"}
)

#: MITIGATION IS NOT TERMINATION. It is set at the FIRST TOUCH, and a layer
#: that enters AT a POI touches it by entering -- closing here would close every
#: trade at its own entry. FALSE_INVALIDATION_CONFIRMED leaves the setup VALID,
#: so closing on it exits exactly the trap the doctrine survives.
NEVER_CLOSE_EVENTS = frozenset(
    {"MITIGATED", "FALSE_INVALIDATION_CONFIRMED"}
)

#: RESOLVED as no-close by author decision, and logged distinctly because the
#: POI's RECORD changed even though the position's management did not.
#:
#: The two reclaim states are `PoiLifecycleStatus` members: neither sets
#: `terminal`, the breach walk continues past both, and the POI stays VALID, so
#: closing on them would contradict the analytical layer.
#:
#: `PROMOTED_TO_ORDER_BLOCK` IS terminal, but `rc5_validity` maps it to
#: SUPERSEDED and says outright it is not a failure: the RC3 rule ends an
#: engulfing record once its ORDER BLOCK record exists, so the formation lives
#: on under a new record. NEW entries need no extra rule -- SUPERSEDED is not
#: VALID, so the existing eligibility gate already refuses them.
STATE_MIGRATION_EVENTS = frozenset(
    {
        "RECLAIM_WITHOUT_DISPLACEMENT",
        "RECLAIM_FAILED",
        "PROMOTED_TO_ORDER_BLOCK",
    }
)


@dataclass(frozen=True)
class BrokerSpec:
    """What the EA reads from SymbolInfo at runtime.

    `tick_size` is `SYMBOL_TRADE_TICK_SIZE`, never `point`: point is not the
    tradable increment on every instrument.
    """

    name: str
    digits: int
    point: Decimal
    tick_size: Decimal
    tick_value_loss: Decimal
    volume_min: Decimal
    volume_max: Decimal
    volume_step: Decimal
    stops_level: int = 0
    freeze_level: int = 0
    #: Informational only. The EA asks `OrderCalcMargin` for the authoritative
    #: number; nothing here reimplements MT5's margin engine.
    contract_size: Decimal = Decimal("100000")
    leverage: int = 500


@dataclass(frozen=True)
class SetupFixture:
    """One analytical setup, exactly as the frozen engine reported it."""

    symbol: str
    timeframe_minutes: int
    bar_time_epoch: int
    poi_id: str
    poi_type: int
    direction: int  # +1 bullish, -1 bearish
    zone_top: Decimal
    zone_bottom: Decimal
    authoritative: bool
    validity: int  # 0 VALID, 1 INVALIDATED, 2 SUPERSEDED
    p5_permission: bool
    lifecycle: int  # 7 == LIQUIDITY_VALIDATED


@dataclass(frozen=True)
class TradePlan:
    eligible: bool
    deny_reason: str = ""
    distal: Decimal | None = None
    stop: Decimal | None = None
    take: Decimal | None = None
    r: Decimal | None = None
    volume: Decimal | None = None
    risk_money: Decimal | None = None
    realized_risk: Decimal | None = None
    #: The entry is whatever the market offers AFTER confirmation. Offline
    #: there is no such price, and inventing one would fabricate the result.
    entry_note: str = "ENTRY_PRICE_PENDING_TESTER"
    spread: Decimal | None = None
    spread_to_risk: Decimal | None = None
    required_margin: Decimal | None = None
    margin_fraction: Decimal | None = None
    #: "PASS", "DENY", or "PENDING_TESTER" when the input does not exist
    #: offline. A gate that cannot be evaluated is never silently treated as
    #: passed.
    spread_gate: str = "PENDING_TESTER"
    margin_gate: str = "PENDING_TESTER"


LIQUIDITY_VALIDATED = 7
VALID = 0

#: EXECUTION DOCTRINE V1 PARAMETERS. Not frozen analytical-engine semantics --
#: RC5 specifies neither a spread tolerance nor a margin ceiling.
#:
#: The spread gate exists because the monetary risk budget alone does not
#: describe execution QUALITY: a measured pathological case passed the 0.5%
#: budget with room to spare (40.00 against 50.00) while the spread was about
#: FIVE TIMES R, so the trade was stopped out by transaction cost alone. It is
#: deliberately NOT special-cased to zero-height zones: any setup whose R is
#: small relative to the spread has the same problem.
MAX_SPREAD_TO_RISK = Decimal("0.25")

#: The margin gate exists because the risk budget does not bound GROSS
#: EXPOSURE when the stop is very tight -- the same case sized 200 lots, about
#: a 20,000,000 EUR notional. Broker `volume_max` bounded it, which is a
#: contract limit rather than a risk rule.
MAX_MARGIN_FRACTION = Decimal("0.20")


def fixture_line(fixture: SetupFixture) -> str:
    """Render one line of the EA's `InpSetupFile`.

    The line is pipe-delimited, so NO FIELD MAY CONTAIN A PIPE. A POI id is the
    only free-form field and ids are built by joining parts, so this is a real
    hazard rather than a theoretical one: the EA counts fields and rejects a
    line that does not split into exactly twelve, which turns a malformed id
    into a silently skipped setup. Failing here instead makes it loud.
    """
    parts = [
            fixture.symbol,
            fixture.timeframe_minutes,
            fixture.bar_time_epoch,
            fixture.poi_id,
            fixture.poi_type,
            fixture.direction,
            fixture.zone_top,
            fixture.zone_bottom,
            int(fixture.authoritative),
            fixture.validity,
            int(fixture.p5_permission),
            fixture.lifecycle,
    ]
    rendered = [str(v) for v in parts]
    for name, value in zip(FIXTURE_FIELDS, rendered, strict=True):
        if "|" in value:
            raise ValueError(f"field {name!r} contains the delimiter: {value!r}")
    return "|".join(rendered)


def _to_tick(spec: BrokerSpec, price: Decimal) -> Decimal:
    steps = (price / spec.tick_size).quantize(Decimal(1), rounding=ROUND_HALF_UP)
    return steps * spec.tick_size


def _eligibility(fixture: SetupFixture) -> str:
    """The V1 gate. P5 alone never triggers an order."""
    if not fixture.authoritative:
        return "NOT_AUTHORITATIVE"
    if fixture.validity != VALID:
        return "NOT_VALID"
    if not fixture.p5_permission:
        return "NO_P5"
    if fixture.lifecycle != LIQUIDITY_VALIDATED:
        return "NOT_CONFIRMED"
    if fixture.direction == 0:
        return "NO_DIRECTION"
    return ""


def plan_for(
    spec: BrokerSpec,
    fixture: SetupFixture,
    entry: Decimal,
    equity: Decimal,
    risk_percent: Decimal = Decimal("0.5"),
    reward_risk: Decimal = Decimal("2.0"),
    spread: Decimal | None = None,
    required_margin: Decimal | None = None,
    max_spread_to_risk: Decimal = MAX_SPREAD_TO_RISK,
    max_margin_fraction: Decimal = MAX_MARGIN_FRACTION,
) -> TradePlan:
    """Everything V1 decides, given an entry price the caller supplies.

    The entry is a parameter rather than a computation on purpose: it is the
    first tradable price AFTER confirmation, which exists only at runtime. The
    same is true of `spread` and `required_margin`: when they are not supplied
    the corresponding gate reports PENDING_TESTER rather than PASS, because a
    gate that could not be evaluated has not been satisfied.
    """
    deny = _eligibility(fixture)
    if deny:
        return TradePlan(eligible=False, deny_reason=deny)

    is_buy = fixture.direction > 0
    distal = fixture.zone_bottom if is_buy else fixture.zone_top
    stop = _to_tick(
        spec, distal - spec.tick_size if is_buy else distal + spec.tick_size
    )
    entry = _to_tick(spec, entry)

    if (is_buy and stop >= entry) or (not is_buy and stop <= entry):
        return TradePlan(eligible=False, deny_reason="STOP_WRONG_SIDE", distal=distal)

    r = abs(entry - stop)

    # EXECUTION QUALITY, gate 1 of 2. R must exist before anything is sized
    # against it. Unreachable after the wrong-side check above, and kept as
    # defence in depth because every downstream number divides by it.
    if r <= 0:
        return TradePlan(
            eligible=False, deny_reason="R_ZERO", distal=distal, stop=stop, r=r
        )

    take = _to_tick(spec, entry + r * reward_risk if is_buy else entry - r * reward_risk)

    # The spread gate. `<=` at the boundary, so spread == 25% of R is ACCEPTED.
    spread_to_risk = None if spread is None else spread / r
    if spread is None:
        spread_gate = "PENDING_TESTER"
    elif spread_to_risk is not None and spread_to_risk <= max_spread_to_risk:
        spread_gate = "PASS"
    else:
        return TradePlan(
            eligible=False,
            deny_reason="SPREAD_TO_RISK_INVALID",
            distal=distal,
            stop=stop,
            take=take,
            r=r,
            spread=spread,
            spread_to_risk=spread_to_risk,
            spread_gate="DENY",
        )

    level = max(spec.stops_level, spec.freeze_level)
    if level > 0 and r < level * spec.point:
        return TradePlan(
            eligible=False,
            deny_reason="BROKER_STOP_INVALID",
            distal=distal,
            stop=stop,
            take=take,
            r=r,
            spread=spread,
            spread_to_risk=spread_to_risk,
            spread_gate=spread_gate,
        )

    risk_money = equity * risk_percent / Decimal(100)
    loss_per_lot = (r / spec.tick_size) * spec.tick_value_loss
    if loss_per_lot <= 0:
        return TradePlan(eligible=False, deny_reason="RISK_MODEL_INVALID", r=r)

    desired = risk_money / loss_per_lot
    floored = (desired / spec.volume_step).quantize(
        Decimal(1), rounding=ROUND_DOWN
    ) * spec.volume_step
    if floored < spec.volume_min:
        # Taking the minimum lot would risk MORE than the budget. V1 denies
        # rather than rounding the risk up -- the same refusal as never
        # silently widening the stop.
        return TradePlan(
            eligible=False,
            deny_reason="RISK_BUDGET_EXCEEDED",
            distal=distal,
            stop=stop,
            take=take,
            r=r,
            risk_money=risk_money,
            realized_risk=spec.volume_min * loss_per_lot,
        )

    volume = min(floored, spec.volume_max)
    if volume < spec.volume_min:
        # A broker ceiling BELOW its own floor leaves no legal size. Found by
        # the vector suite: without this the model returned a volume under the
        # minimum while the EA's NormalizeVolume correctly returns 0.0, so the
        # mirror and the EA disagreed.
        return TradePlan(
            eligible=False,
            deny_reason="VOLUME_INVALID",
            distal=distal,
            stop=stop,
            take=take,
            r=r,
            risk_money=risk_money,
        )
    # EXECUTION QUALITY, gate 2 of 2. The risk budget does not bound GROSS
    # EXPOSURE when the stop is tight, so required margin is checked against
    # equity separately. `required_margin` is the BROKER's number (the EA asks
    # OrderCalcMargin); nothing here reimplements MT5's margin engine, and an
    # absent value reports PENDING_TESTER rather than PASS.
    margin_fraction = (
        None if required_margin is None or equity <= 0 else required_margin / equity
    )
    if required_margin is None:
        margin_gate = "PENDING_TESTER"
    elif margin_fraction is not None and margin_fraction <= max_margin_fraction:
        margin_gate = "PASS"
    else:
        return TradePlan(
            eligible=False,
            deny_reason="MARGIN_EXPOSURE_INVALID",
            distal=distal,
            stop=stop,
            take=take,
            r=r,
            volume=volume,
            risk_money=risk_money,
            realized_risk=volume * loss_per_lot,
            spread=spread,
            spread_to_risk=spread_to_risk,
            spread_gate=spread_gate,
            required_margin=required_margin,
            margin_fraction=margin_fraction,
            margin_gate="DENY",
        )

    return TradePlan(
        eligible=True,
        distal=distal,
        stop=stop,
        take=take,
        r=r,
        volume=volume,
        risk_money=risk_money,
        realized_risk=volume * loss_per_lot,
        spread=spread,
        spread_to_risk=spread_to_risk,
        spread_gate=spread_gate,
        required_margin=required_margin,
        margin_fraction=margin_fraction,
        margin_gate=margin_gate,
    )


def signal_id(fixture: SetupFixture) -> str:
    """Mirror of the EA's `RC5SignalId`, field for field.

    A bar timestamp alone is not enough: several POIs can confirm on the same
    bar, so the POI's own identity is part of the key. The confirmation
    instance makes a later re-confirmation of the same POI a DIFFERENT signal,
    which is what "at most once per semantic setup" means.
    """
    return "|".join(
        (
            fixture.symbol,
            str(fixture.timeframe_minutes),
            fixture.poi_id,
            str(fixture.poi_type),
            str(fixture.direction),
            str(fixture.bar_time_epoch),
        )
    )


def guard_deny(
    fixture: SetupFixture,
    consumed_signal_ids: frozenset[str] | set[str],
    symbols_with_open_position: frozenset[str] | set[str],
    broker_symbol: str | None = None,
) -> str:
    """The duplicate and concurrency guards, in the EA's own order.

    Returns the deny reason, or "" when both guards pass. `broker_symbol` is
    the RESOLVED name (XAUUSDm), because concurrency is per broker symbol while
    the signal id is keyed on the LOGICAL one.
    """
    if signal_id(fixture) in consumed_signal_ids:
        return "SIGNAL_ALREADY_EXECUTED"
    name = broker_symbol if broker_symbol is not None else fixture.symbol
    if name in symbols_with_open_position:
        return "SYMBOL_POSITION_ACTIVE"
    return ""


def decide(
    spec: BrokerSpec,
    fixture: SetupFixture,
    entry: Decimal,
    equity: Decimal,
    consumed_signal_ids: frozenset[str] | set[str] = frozenset(),
    symbols_with_open_position: frozenset[str] | set[str] = frozenset(),
    risk_percent: Decimal = Decimal("0.5"),
    reward_risk: Decimal = Decimal("2.0"),
    spread: Decimal | None = None,
    required_margin: Decimal | None = None,
) -> TradePlan:
    """The whole pipeline, in the EA's order: eligibility, guards, prices, risk.

    The ORDER is part of the contract. Guards run before any price is read, so
    a duplicate signal never reports a stop or a volume it was never going to
    use, and the deny reason a log shows is the FIRST one that applied.
    """
    deny = _eligibility(fixture)
    if deny:
        return TradePlan(eligible=False, deny_reason=deny)
    deny = guard_deny(
        fixture,
        consumed_signal_ids,
        symbols_with_open_position,
        spec.name,
    )
    if deny:
        return TradePlan(eligible=False, deny_reason=deny)
    return plan_for(
        spec,
        fixture,
        entry,
        equity,
        risk_percent,
        reward_risk,
        spread=spread,
        required_margin=required_margin,
    )
