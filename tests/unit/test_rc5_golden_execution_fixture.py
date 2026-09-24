"""THE GOLDEN EA EXECUTION FIXTURES — the first real `LIQUIDITY_VALIDATED` setups.

Produced by a targeted walk over the two proven favourable-regime windows, with
the full W1+D1+H4+H1+M5 context and the real pipeline throughout. These are not
synthetic: every Layer-A field below came out of the frozen engine.

## Why THESE two, and not the first trigger found

The very first trigger the walk produced was a `HAMMER` with zone 308.75-312.85
while the host bar closed near 4,400 — a POI formed when gold traded near $310,
still registered because the W1 context carries about 38 years, never breached,
and therefore still VALID. V1 accepts it (see
`test_rc5_ea_doctrine_vectors.py`), which is a real finding and a bad fixture.

The two frozen here are the FIRST trigger in each window where **price is
inside the zone** — a setup the execution layer is actually interacting with.

## What is asserted, and what is deliberately absent

Layer-A fields and the entry-INDEPENDENT execution geometry (distal, stop) are
exact and pinned. Everything downstream of the entry — R, take profit, volume,
margin, both quality gates — depends on the first tradable price AFTER
confirmation, which exists only at runtime. Those are `ENTRY_PRICE_PENDING_TESTER`.

The bar's close is NOT used as a proxy entry. It is a hindsight price the
execution layer could never have traded at, and substituting it would quietly
convert a pending value into a fabricated one.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from tools.rc5_ea_fixtures import (  # type: ignore[import-not-found]
    BrokerSpec,
    SetupFixture,
    fixture_line,
    plan_for,
    signal_id,
)

#: Exness Standard gold, as the EA reads it at runtime. Pinned so the geometry
#: below is reproducible; the EA hardcodes nothing.
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

#: GOLDEN 1 — 2026-08-30 22:45 UTC. HAMMER, price inside the zone.
GOLDEN_HAMMER = SetupFixture(
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

#: GOLDEN 2 — 2026-09-08 14:45 UTC. MORNING_STAR, price inside the zone.
GOLDEN_MORNING_STAR = SetupFixture(
    symbol="XAUUSD",
    timeframe_minutes=15,
    bar_time_epoch=1788878700,
    poi_id="MORNING_STAR~cf5314af21ab",
    poi_type=1,
    direction=1,
    zone_top=Decimal("4399.54"),
    zone_bottom=Decimal("4391.07"),
    authoritative=True,
    validity=0,
    p5_permission=True,
    lifecycle=7,
)

#: The analytical evidence each one carried, recorded for the parity table.
#: Not consumed by the EA — it reads the twelve transported fields — but it is
#: what makes these setups reproducible from the engine rather than asserted.
GOLDEN_EVIDENCE = {
    "HAMMER~82c481350728": {
        "bar_time_utc": "2026-08-30T22:45:00+00:00",
        "host_close": Decimal("4461.29"),
        "btmm_valid": True,
        "trend_alignment": "ALIGNED",
        "regime": "TREND",
        "momentum_direction": "BULLISH",
        "momentum_score": 69,
        "liquidity_score": 70,
        "permission": "BUY_BIAS",
    },
    "MORNING_STAR~cf5314af21ab": {
        "bar_time_utc": "2026-09-08T14:45:00+00:00",
        "host_close": Decimal("4398.65"),
        "btmm_valid": True,
        "trend_alignment": "ALIGNED",
        "regime": "TREND",
        "momentum_direction": "STRONG_BULLISH",
        "momentum_score": 72,
        "liquidity_score": 70,
        "permission": "BUY_BIAS",
    },
}

GOLDEN = (GOLDEN_HAMMER, GOLDEN_MORNING_STAR)


# ---------------------------------------------------------------------------
# Layer A — exactly what the engine produced
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", GOLDEN, ids=lambda f: f.poi_id)
def test_the_golden_setup_satisfies_every_eligibility_gate(
    fixture: SetupFixture,
) -> None:
    assert fixture.authoritative
    assert fixture.validity == 0
    assert fixture.p5_permission
    assert fixture.lifecycle == 7
    assert fixture.direction == 1


@pytest.mark.parametrize("fixture", GOLDEN, ids=lambda f: f.poi_id)
def test_price_was_inside_the_zone(fixture: SetupFixture) -> None:
    """The property that separates these from the first trigger found.

    A setup the layer is interacting with, rather than a decades-old level
    thousands of points away.
    """
    close = GOLDEN_EVIDENCE[fixture.poi_id]["host_close"]
    assert isinstance(close, Decimal)
    assert fixture.zone_bottom <= close <= fixture.zone_top


@pytest.mark.parametrize("fixture", GOLDEN, ids=lambda f: f.poi_id)
def test_momentum_agreed_with_the_poi_direction(fixture: SetupFixture) -> None:
    """Every earlier `REGIME_VALIDATED` POI was counter-momentum; these are not,
    which is precisely why they cleared the momentum rung."""
    evidence = GOLDEN_EVIDENCE[fixture.poi_id]
    assert "BULLISH" in str(evidence["momentum_direction"])
    assert int(str(evidence["momentum_score"])) >= 60
    assert int(str(evidence["liquidity_score"])) >= 60


# ---------------------------------------------------------------------------
# transport
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("fixture", GOLDEN, ids=lambda f: f.poi_id)
def test_the_golden_setup_transports_to_the_ea_intact(
    fixture: SetupFixture,
) -> None:
    parts = fixture_line(fixture).split("|")
    assert len(parts) == 12
    assert parts[0] == "XAUUSD"
    assert Decimal(parts[6]) == fixture.zone_top
    assert Decimal(parts[7]) == fixture.zone_bottom
    assert int(parts[11]) == 7


def test_the_two_golden_setups_are_different_signals() -> None:
    assert signal_id(GOLDEN_HAMMER) != signal_id(GOLDEN_MORNING_STAR)


# ---------------------------------------------------------------------------
# Layer B — the entry-INDEPENDENT geometry, which is all that can be fixed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("fixture", "distal", "stop"),
    [
        (GOLDEN_HAMMER, Decimal("4450.54"), Decimal("4450.53")),
        (GOLDEN_MORNING_STAR, Decimal("4391.07"), Decimal("4391.06")),
    ],
    ids=lambda v: str(v)[:24],
)
def test_the_distal_and_stop_are_exact(
    fixture: SetupFixture, distal: Decimal, stop: Decimal
) -> None:
    """BULLISH -> distal is the zone BOTTOM, stop one executable tick below.

    Both are pure functions of the zone and the direction, so unlike everything
    downstream of the entry they can be pinned exactly.
    """
    # entry supplied only so the plan gets far enough to report the geometry;
    # any price above the stop yields the same distal and stop
    plan = plan_for(XAUUSD, fixture, Decimal("4460.00"), Decimal("10000"))
    assert plan.distal == distal
    assert plan.stop == stop


@pytest.mark.parametrize("fixture", GOLDEN, ids=lambda f: f.poi_id)
def test_everything_entry_dependent_is_pending_not_invented(
    fixture: SetupFixture,
) -> None:
    """R, take profit, volume, margin and both quality gates need the first
    tradable price AFTER confirmation, which exists only at runtime.

    The bar close is NOT used as a proxy: it is a hindsight price the layer
    could never have traded at.
    """
    plan = plan_for(XAUUSD, fixture, Decimal("4460.00"), Decimal("10000"))
    assert plan.entry_note == "ENTRY_PRICE_PENDING_TESTER"
    # no spread and no broker margin offline, so neither gate claims to pass
    assert plan.spread_gate == "PENDING_TESTER"
    assert plan.margin_gate == "PENDING_TESTER"
