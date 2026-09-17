"""RC3 final semantic lock: a confirmed SUPPORT / RESISTANCE ZONE never disappears.

Real FXCM M15 bars (``tests/fixtures/rc3_confirmed_zone_m15.json``): the frozen
measurement confirms a 4600.75 SUPPORT zone at bar 468, replaces it with a
same-geometry record at bar 469 and drops it at bar 470. Both confirmed zone
POIs must stay in the registry with their first-seen fields; the lifecycle
continues normally; incremental replay equals batch at every prefix.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "rc3_confirmed_zone_m15.json"
)
_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_BOTTOM = Decimal("4600.75")


@pytest.fixture(scope="module")
def candles(tmp_path_factory):
    rows = json.loads(_FIXTURE.read_text(encoding="utf-8"))["rows"]
    path = tmp_path_factory.mktemp("zone") / "m15.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow((r["time"], r["open"], r["high"], r["low"], r["close"], 1))
    return load_v1a_csv(
        path,
        Timeframe.M15,
        close_time_ms_by_open_ms={int(r["time"]): int(r["close_time"]) for r in rows},
    )


def _analyze(prefix):
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(prefix, _MCONFIG, identity)
    pois = analyze_pois(
        (PoiTimeframeInput(Timeframe.M15, prefix, measurement),), _PCONFIG, identity
    )
    return measurement, pois


def _zone_pois(pois):
    return sorted(
        (
            o
            for o in pois.poi_observations
            if o.poi_type is PoiType.SUPPORT_ZONE and o.zone_bottom == _BOTTOM
        ),
        key=lambda o: o.availability_time_utc,
    )


def test_measurement_confirms_then_drops_the_zone(candles) -> None:
    def zones(n):
        m = analyze_market_measurements(
            candles[:n], _MCONFIG, ContentAddressedIdentityProvider()
        )
        return [z for z in m.support_resistance_zones if z.zone_bottom == _BOTTOM]

    assert len(zones(469)) == 1  # confirmed at bar 468
    assert len(zones(470)) == 1  # replaced by a same-geometry record at 469
    assert zones(469)[0].record_id != zones(470)[0].record_id
    assert zones(471) == []  # the current-state projection drops it at 470


def test_confirmed_zone_pois_survive_with_their_first_seen_fields(candles) -> None:
    _m, at_469 = _analyze(candles[:469])
    _m, at_470 = _analyze(candles[:470])
    measurement, final = _analyze(candles)
    assert not [
        z for z in measurement.support_resistance_zones if z.zone_bottom == _BOTTOM
    ]

    first = _zone_pois(at_469)[0]
    second = _zone_pois(at_470)[1]
    kept = _zone_pois(final)
    assert [o.record_id for o in kept] == [first.record_id, second.record_id]
    for seen, now in zip((first, second), kept, strict=True):
        assert (now.zone_top, now.zone_bottom) == (seen.zone_top, seen.zone_bottom)
        assert now.candidate_event_time_utc == seen.candidate_event_time_utc
        assert now.availability_time_utc == seen.availability_time_utc
    assert kept[0].availability_time_utc == candles[468].availability_time_utc
    assert kept[1].availability_time_utc == candles[469].availability_time_utc

    # its lifecycle continued normally: price came back into the zone
    states = {s.poi_record_id: s for s in final.current_poi_states}
    assert all(states[o.record_id].terminal_reason is not None for o in kept)


def test_replay_kernel_matches_batch_through_the_disappearance(candles) -> None:
    configuration = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=Decimal("0.01"),
    )
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for n, candle in enumerate(candles, start=1):
        kernel.advance_group({Timeframe.M15: (candle,)})
        if n not in (468, 469, 470, 471, 474, len(candles)):
            continue
        incremental = kernel.finalize().poi_analysis
        batch = scan_market(
            (ScannerTimeframeInput(Timeframe.M15, candles[:n]),),
            (),
            configuration,
            ContentAddressedIdentityProvider(),
        ).poi_analysis
        assert incremental.poi_observations == batch.poi_observations, n
        assert incremental.current_poi_states == batch.current_poi_states, n
