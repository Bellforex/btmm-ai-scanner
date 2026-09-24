"""LAYER A -> EA: project the frozen engine's analytical state into EA fixtures.

WHAT THIS PROVES, AND WHAT IT DOES NOT.

It produces, from real broker OHLC and the frozen engines only, the exact
twelve Layer-A fields the MQL5 EA consumes: symbol, timeframe, bar time, POI
identity, POI type, direction, both zone edges, authority, validity, P5
permission and lifecycle. Nothing here reads a Pine log or an MT5 log, so a
later comparison against the EA is a real claim rather than a tautology.

It does NOT prove the EA agrees. The EA cannot be executed in this environment
-- the Strategy Tester needs a terminal launch the sandbox denies -- so what is
checkable offline is TRANSPORT parity: that every line this emits parses back,
under the EA's own splitting rule, to the same twelve values. Behavioural
parity is a tester result and is not claimed here.

Layer B is deliberately absent from this module. The expectation for each
fixture (distal, stop, R, target, volume) belongs to
`tools.rc5_ea_fixtures`, and mixing the two is exactly the confusion the
author's "do not mix analytical mismatch with execution-policy differences"
instruction warns against.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.btrc.enums import AnalyticalPermission, SignalLifecycleState
from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.rc5_semantics import Rc5Validity, rc5_validity
from tests.parity_support.level_a_replay import (
    build_scanner_configuration,
    iter_level_a_bars,
)
from tools.rc5_ea_fixtures import SetupFixture  # type: ignore[import-not-found]

__all__ = ["LayerAProjection", "project_layer_a", "write_fixture_file"]

_TICK = Decimal("0.01")

#: The EA's integer lifecycle codes, in the frozen engine's own order. Only the
#: ANALYTICAL states exist: RISK_VALIDATED..CLOSED are Layer B's to assign and
#: the engine never produces them.
LIFECYCLE_CODE: Mapping[SignalLifecycleState, int] = {
    SignalLifecycleState.DETECTED: 0,
    SignalLifecycleState.STRUCTURALLY_VALIDATED: 1,
    SignalLifecycleState.BTMM_VALIDATED: 2,
    SignalLifecycleState.POI_VALIDATED: 3,
    SignalLifecycleState.TREND_VALIDATED: 4,
    SignalLifecycleState.REGIME_VALIDATED: 5,
    SignalLifecycleState.MOMENTUM_VALIDATED: 6,
    SignalLifecycleState.LIQUIDITY_VALIDATED: 7,
}

VALIDITY_CODE: Mapping[Rc5Validity, int] = {
    Rc5Validity.VALID: 0,
    Rc5Validity.INVALIDATED: 1,
    Rc5Validity.SUPERSEDED: 2,
}

#: `PoiType` is a StrEnum; the EA needs an int. The ORDER of the enum is the
#: contract, not a lookup table maintained by hand, so a new type cannot
#: silently renumber an old one as long as it is appended.
POI_TYPE_CODE: Mapping[PoiType, int] = {t: i for i, t in enumerate(PoiType)}

DIRECTION_CODE: Mapping[PoiDirection, int] = {
    PoiDirection.BULLISH: 1,
    PoiDirection.BEARISH: -1,
}

#: `AnalyticalPermission` is a BIAS, not a boolean, so "P5 permission is true"
#: had to be derived from how t5_engine assigns it rather than assumed.
#:
#: BUY_BIAS / SELL_BIAS are issued ONLY when trend alignment is ALIGNED or
#: PARTIAL **and** the final confluence clears `high_confluence_min`, and they
#: carry the POI's own direction (`poi_bullish`), so a directional bias always
#: agrees with its POI by construction. Everything else is an explicit
#: downgrade in that same function: WATCH_ONLY is what moderate confluence and
#: extreme volatility fall back to, NO_TRADE_CONTEXT is low confluence, and
#: COUNTER_TREND is commented "execution priority low".
DIRECTIONAL_PERMISSION: Mapping[int, AnalyticalPermission] = {
    1: AnalyticalPermission.BUY_BIAS,
    -1: AnalyticalPermission.SELL_BIAS,
}

#: Neither a permission nor obviously a refusal. Counted and REPORTED rather
#: than silently folded either way -- see `LayerAProjection.arguable`.
ARGUABLE_PERMISSIONS = frozenset(
    {
        AnalyticalPermission.ALLOW_BOTH_CONTEXT,
        AnalyticalPermission.COUNTER_TREND,
    }
)


def _p5_permits(permission: AnalyticalPermission, direction: int) -> bool:
    """The STRICT reading: a directional, high-confluence bias that agrees."""
    return DIRECTIONAL_PERMISSION.get(direction) is permission


@dataclass(frozen=True)
class LayerAProjection:
    """One bar's worth of Layer-A state, plus why it is interesting."""

    fixtures: tuple[SetupFixture, ...]
    bars: int
    #: How many POIs reached LIQUIDITY_VALIDATED at all. A run where nothing
    #: ever confirms passes every assertion while proving nothing.
    confirmed: int
    #: How many were authoritative AND valid AND permitted AND confirmed --
    #: the setups Execution Doctrine V1 would actually act on.
    actionable: int
    #: Confirmed, authoritative, valid setups whose permission was
    #: ALLOW_BOTH_CONTEXT or COUNTER_TREND. Under the strict reading these are
    #: NOT permitted; the count exists so the author can see what that costs.
    arguable: int


def project_layer_a(
    *,
    host_timeframe: Timeframe,
    host_series: Sequence[NormalizedCandle],
    logical_symbol: str,
    timeframe_minutes: int,
    context_series: Mapping[Timeframe, Sequence[NormalizedCandle]] | None = None,
    minimum_price_tick: Decimal = _TICK,
) -> LayerAProjection:
    """Walk the capture and emit one fixture per POI per confirmed bar.

    Emission is per BAR, not per POI: the EA consumes a stream of analytical
    state, and a POI's authority, validity, permission and lifecycle all move
    over time. Collapsing to a final state would hide exactly the transitions
    the execution layer has to react to.
    """
    base = build_scanner_configuration(
        required_timeframes=frozenset({host_timeframe, *(context_series or {})}),
        optional_timeframes=frozenset(),
        minimum_price_tick=minimum_price_tick,
    )
    configuration = base.model_copy(
        update={
            "poi_configuration": PoiConfiguration(
                minimum_price_tick=minimum_price_tick, rc5_structural_origin=True
            )
        }
    )

    fixtures: list[SetupFixture] = []
    bars = 0
    confirmed = 0
    actionable = 0
    arguable = 0

    for bar in iter_level_a_bars(
        host_timeframe=host_timeframe,
        host_series=host_series,
        context_series=context_series or {},
        configuration=configuration,
        rc3_freshness=True,
        rc4_framework=True,
        rc5_authority=True,
    ):
        bars += 1
        bar_epoch = int(bar.candle.event_time_utc.timestamp())

        for poi_id in bar.evaluated_order:
            decision = bar.decision_by_id.get(poi_id)
            observation = bar.observation_by_id.get(poi_id)
            if decision is None or observation is None:
                continue

            direction = DIRECTION_CODE.get(observation.direction)
            if direction is None:
                continue

            lifecycle = LIFECYCLE_CODE.get(decision.lifecycle_state)
            if lifecycle is None:
                # A Layer-B state on an analytical record would mean the
                # engine produced something it declares it never assigns.
                raise AssertionError(
                    f"non-analytical lifecycle state {decision.lifecycle_state!r}"
                )

            validity = rc5_validity(bar.state_by_id.get(poi_id))
            authoritative = poi_id not in bar.suppressed_poi_ids
            permission = decision.analytical_permission

            fixture = SetupFixture(
                symbol=logical_symbol,
                timeframe_minutes=timeframe_minutes,
                bar_time_epoch=bar_epoch,
                # The EA's free-form id field. Pipe-free by construction: the
                # delimiter is the line separator and `fixture_line` refuses
                # any field that contains one.
                poi_id=f"{observation.poi_type.value}~{poi_id.hex[:12]}",
                poi_type=POI_TYPE_CODE[observation.poi_type],
                direction=direction,
                zone_top=observation.zone_top,
                zone_bottom=observation.zone_bottom,
                authoritative=authoritative,
                validity=VALIDITY_CODE[validity],
                p5_permission=_p5_permits(permission, direction),
                lifecycle=lifecycle,
            )
            fixtures.append(fixture)

            if lifecycle == LIFECYCLE_CODE[SignalLifecycleState.LIQUIDITY_VALIDATED]:
                confirmed += 1
                if authoritative and validity is Rc5Validity.VALID:
                    if fixture.p5_permission:
                        actionable += 1
                    elif permission in ARGUABLE_PERMISSIONS:
                        arguable += 1

    return LayerAProjection(
        fixtures=tuple(fixtures),
        bars=bars,
        confirmed=confirmed,
        actionable=actionable,
        arguable=arguable,
    )


def write_fixture_file(
    projection: LayerAProjection,
    destination: Path,
    *,
    only_confirmed: bool = False,
) -> int:
    """Write the EA's `InpSetupFile`. Returns the number of lines written.

    `only_confirmed` keeps just the rows at `LIQUIDITY_VALIDATED`, which is the
    smallest file that can still trigger V1. The default writes EVERY row,
    because the EA's denial paths are as much of the parity surface as its
    execution path -- a file that only contains setups it will act on cannot
    show that it correctly refuses the rest.
    """
    from tools.rc5_ea_fixtures import fixture_line

    trigger = LIFECYCLE_CODE[SignalLifecycleState.LIQUIDITY_VALIDATED]
    rows = [
        f
        for f in projection.fixtures
        if not only_confirmed or f.lifecycle == trigger
    ]
    header = (
        "# RC5 Layer-A fixtures -- analytical state EXPORTED from the frozen\n"
        "# engine. NOT a signal source: the EA has no detector.\n"
        "# symbol|tf|barTimeEpoch|poiId|poiType|direction|zoneTop|zoneBottom|"
        "authoritative|validity|p5|lifecycle\n"
    )
    destination.write_text(
        header + "\n".join(fixture_line(f) for f in rows) + "\n",
        encoding="ascii",
        newline="\n",
    )
    return len(rows)


if __name__ == "__main__":  # pragma: no cover - operator entry point
    import argparse

    from tests.parity_support.v1a_csv_loader import (
        load_v1a_csv,
    )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ohlc", required=True, type=Path)
    parser.add_argument("--timeframe", required=True)
    parser.add_argument("--minutes", required=True, type=int)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--tick", default="0.01")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--only-confirmed", action="store_true")
    args = parser.parse_args()

    tf = Timeframe(args.timeframe)
    result = project_layer_a(
        host_timeframe=tf,
        host_series=load_v1a_csv(args.ohlc, tf),
        logical_symbol=args.symbol,
        timeframe_minutes=args.minutes,
        minimum_price_tick=Decimal(args.tick),
    )
    written = write_fixture_file(
        result, args.out, only_confirmed=args.only_confirmed
    )
    print(
        f"bars={result.bars} rows={len(result.fixtures)} "
        f"confirmed={result.confirmed} actionable={result.actionable} "
        f"arguable={result.arguable} -> {written} lines in {args.out}"
    )
