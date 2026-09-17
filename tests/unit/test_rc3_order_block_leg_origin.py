"""RC3 final semantic lock: ORDER BLOCK = ACTUAL LEG ORIGIN + immutability.

Rule under test (``poi/leg_origin.py``): each bullish structure break
(BULLISH_BOS / BULLISH_CHOCH of the frozen P2 walk) confirms one leg whose
origin is the lowest confirmed SWING_LOW between the broken swing high and the
break candle. The earliest raw OB formation on that origin swing is the
leg's BUY ORDER BLOCK, available at the break; every other raw formation is a
BULLISH ENGULFING only. SELL mirrors. A confirmed ORDER BLOCK never
disappears when a later recomputation loses its origin swing.

Every case runs the REAL engine on explicit rows (SELL = exact price mirror)
or on the H4 author fixture (real FXCM candles after the sealed range plus a
labelled synthetic pre-context).
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
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import detect_confirmed_swings
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiTerminalReason, PoiType
from btmm_ai_scanner.poi.leg_origin import (
    iter_prefix_swing_candidates,
    leg_origin_order_blocks,
)
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from btmm_ai_scanner.structure.configuration import StructureConfiguration
from btmm_ai_scanner.structure.enums import StructureTransitionType
from btmm_ai_scanner.structure.relationships import detect_swing_relationships
from btmm_ai_scanner.structure.transitions import run_structure_walk
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import (
    Row,
    analyze_rows,
    mirror,
    rows_to_candles,
    trend,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_POI_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_MEASUREMENT_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
BUY = (PoiType.BUY_ORDER_BLOCK, PoiType.BULLISH_ENGULFING)
SELL = (PoiType.SELL_ORDER_BLOCK, PoiType.BEARISH_ENGULFING)
_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "rc3_leg_origin_h4_author.json"
)


# ---- series ------------------------------------------------------------------


def _continuation() -> list[Row]:
    rows = trend(100, 1.0, 16)  # 0-15
    rows += trend(116, -1.0, 6)  # 16-21
    rows += trend(110, 1.0, 12)  # 22-33 higher high 122.3
    rows += trend(122, -1.0, 6)  # 34-39 pullback
    rows += [(116.0, 116.3, 114.5, 115.0)]  # 40 origin: pullback terminal
    rows += [(115.0, 119.5, 114.8, 119.0)]  # 41 displacement
    rows += trend(119, 1.0, 3)  # 42-44
    rows += [(122.0, 122.4, 121.5, 121.6)]  # 45 mid-leg bearish #1
    rows += [(121.6, 124.5, 121.55, 124.3)]  # 46 mid-leg engulfing #1 (BOS close)
    rows += trend(124.3, 1.0, 2)  # 47-48
    rows += [(126.3, 126.7, 125.8, 125.9)]  # 49 mid-leg bearish #2
    rows += [(125.9, 128.9, 125.85, 128.7)]  # 50 mid-leg engulfing #2
    rows += trend(128.7, 1.0, 2)  # 51-52
    rows += [(130.7, 131.1, 130.2, 130.3)]  # 53 mid-leg bearish #3
    rows += [(130.3, 133.3, 130.25, 133.1)]  # 54 mid-leg engulfing #3
    rows += trend(133.1, 1.0, 2)  # 55-56 swing high 135.4
    rows += trend(135.1, -1.0, 6)  # 57-62 pullback
    rows += [(129.1, 129.4, 127.6, 128.1)]  # 63 origin: pullback terminal
    rows += [(128.1, 132.6, 127.9, 132.1)]  # 64 displacement
    rows += trend(132.1, 0.8, 2)  # 65-66 lower high
    rows += trend(133.7, -0.8, 3)  # 67-69
    rows += [(131.3, 131.6, 130.2, 130.5)]  # 70 confirmed HIGHER low (example-1)
    rows += [(130.5, 134.0, 130.3, 133.8)]  # 71 displacement
    rows += trend(133.8, 1.0, 6)  # 72-77 breaks 135.4 (BOS)
    return rows


def _reversal() -> list[Row]:
    rows = trend(200, -1.0, 16)  # 0-15
    rows += trend(184, 1.0, 6)  # 16-21
    rows += trend(190, -1.0, 12)  # 22-33 lower low
    rows += trend(178, 1.0, 6)  # 34-39 lower high 184.3 -> bearish
    rows += trend(184, -1.0, 10)  # 40-49 bearish BOS
    rows += [(174.0, 174.3, 172.5, 173.0)]  # 50 origin: bottom of the bearish leg
    rows += [(173.0, 177.5, 172.8, 177.0)]  # 51 displacement
    rows += trend(177, 1.0, 2)  # 52-53
    rows += [(179.0, 179.4, 178.5, 178.6)]  # 54 mid-leg bearish
    rows += [(178.6, 181.5, 178.55, 181.3)]  # 55 mid-leg engulfing
    rows += trend(181.3, 1.0, 8)  # 56-63 CHOCH of 184.3
    return rows


def _superseded_origin() -> list[Row]:
    rows = _continuation()[:42]  # up to the displacement at 41
    rows += trend(119, 1.0, 2)  # 42-43
    rows += [(121.0, 124.5, 118.0, 124.0)]  # 44 outside bar: BOS close, no pivot
    rows += [(124.0, 124.2, 121.0, 121.5)]  # 45 inside
    rows += [(121.5, 122.0, 119.0, 119.3)]  # 46 inside
    rows += [(119.3, 119.5, 115.0, 115.5)]  # 47
    rows += [(115.5, 116.0, 112.0, 112.5)]  # 48
    rows += [(112.5, 113.0, 110.0, 110.5)]  # 49 lower low, same pivot run
    rows += trend(110.5, 1.0, 6)  # 50-55
    return rows


def _formations(pois, candles) -> dict[tuple[int, ...], dict]:
    index = {c.record_id: i for i, c in enumerate(candles)}
    bar = {c.availability_time_utc: i for i, c in enumerate(candles)}
    states = {s.poi_record_id: s for s in pois.current_poi_states}
    out: dict[tuple[int, ...], dict] = {}
    for o in pois.poi_observations:
        if o.poi_type not in (*BUY, *SELL):
            continue
        key = tuple(index[c] for c in o.source_candle_record_ids)
        s = states[o.record_id]
        out.setdefault(key, {})[o.poi_type] = {
            "available": bar[o.availability_time_utc],
            "zone": (o.zone_bottom, o.zone_top),
            "terminal": s.terminal_reason,
            "terminal_bar": bar.get(s.terminal_time_utc),
        }
    return out


def _order_blocks(f, ob) -> list[tuple[int, ...]]:
    return sorted(k for k, v in f.items() if ob in v)


def _walk(candles, measurement):
    swings = measurement.confirmed_swings
    return run_structure_walk(
        candles, swings, detect_swing_relationships(swings, StructureConfiguration())
    )


# ---- positive: leg origins ----------------------------------------------------


@pytest.fixture(scope="module", params=["BUY", "SELL"])
def continuation(request, tmp_path_factory):
    rows = _continuation() if request.param == "BUY" else mirror(_continuation())
    pois, candles, measurement = analyze_rows(
        rows, tmp_path_factory.mktemp(request.param), request.param
    )
    index = {c.record_id: i for i, c in enumerate(candles)}
    raw = {
        tuple(index[c] for c in f.source_candle_record_ids)
        for f in detect_order_blocks(candles, _POI_CONFIG)
    }
    # every formation reasoned about meets every frozen raw OB condition
    assert {(40, 41), (45, 46), (49, 50), (53, 54), (63, 64), (70, 71)} <= raw
    ob, eng = BUY if request.param == "BUY" else SELL
    return _formations(pois, candles), candles, measurement, ob, eng


def test_pullback_end_starting_a_continuation_leg_is_an_order_block(
    continuation,
) -> None:
    f, candles, measurement, ob, eng = continuation
    breaks = [
        (
            t.transition_type,
            next(i for i, c in enumerate(candles) if c.record_id == t.break_candle_id),
        )
        for t in _walk(candles, measurement).transitions
    ]
    kinds = {StructureTransitionType.BULLISH_BOS, StructureTransitionType.BEARISH_BOS}
    assert [b for k, b in breaks if k in kinds] == [46, 73]
    assert f[(40, 41)][ob]["available"] == 46  # at the confirming break
    assert f[(63, 64)][ob]["available"] == 73
    assert f[(40, 41)][eng]["available"] == 41  # the engulfing keeps its timing


def test_mid_leg_engulfings_one_two_three_are_engulfing_only(continuation) -> None:
    f, _c, _m, ob, eng = continuation
    for pair in ((45, 46), (49, 50), (53, 54)):
        assert ob not in f[pair], pair
        assert eng in f[pair], pair
        assert f[pair][eng]["terminal"] is not PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK


def test_formation_on_a_confirmed_higher_swing_inside_the_leg_is_engulfing(
    continuation,
) -> None:
    """The author's H4 example-1 structure: the formation sits on a CONFIRMED
    swing (so the earlier movement-origin gate made it an ORDER BLOCK), but the
    leg that breaks structure departed from the lower swing before it."""
    f, candles, measurement, ob, eng = continuation
    index = {c.record_id: i for i, c in enumerate(candles)}
    wanted = (
        SwingType.SWING_LOW if ob is PoiType.BUY_ORDER_BLOCK else SwingType.SWING_HIGH
    )
    confirmed = {
        index[s.pivot_candle_record_ids[0]]
        for s in measurement.confirmed_swings
        if s.swing_type == wanted
    }
    assert {63, 70} <= confirmed
    assert ob not in f[(70, 71)]
    assert eng in f[(70, 71)]


def test_only_leg_origins_are_order_blocks(continuation) -> None:
    f, _c, _m, ob, _eng = continuation
    assert _order_blocks(f, ob) == [(40, 41), (63, 64)]


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_end_of_opposite_leg_is_an_order_block_at_the_choch(
    tmp_path: Path, direction: str
) -> None:
    rows = _reversal() if direction == "BUY" else mirror(_reversal())
    pois, candles, measurement = analyze_rows(rows, tmp_path, direction)
    ob, eng = BUY if direction == "BUY" else SELL
    f = _formations(pois, candles)
    chochs = [
        t
        for t in _walk(candles, measurement).transitions
        if t.transition_type
        in (
            StructureTransitionType.BULLISH_CHOCH,
            StructureTransitionType.BEARISH_CHOCH,
        )
    ]
    assert len(chochs) == 1
    assert _order_blocks(f, ob) == [(50, 51)]
    assert f[(50, 51)][ob]["available"] == 59
    assert ob not in f[(54, 55)] and eng in f[(54, 55)]


def test_promoted_engulfing_ends_at_the_order_block_unless_used_first(
    continuation,
) -> None:
    f, _c, _m, ob, eng = continuation
    for pair in ((40, 41), (63, 64)):
        terminal = f[pair][eng]["terminal"]
        assert terminal in (
            PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK,
            PoiTerminalReason.MITIGATED,
        )
        if terminal is PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK:
            assert f[pair][eng]["terminal_bar"] == f[pair][ob]["available"]


# ---- no lookahead -------------------------------------------------------------


def test_order_block_never_exists_before_its_break(tmp_path: Path) -> None:
    rows = _continuation()
    for end in range(42, 49):
        pois, candles, _m = analyze_rows(rows[: end + 1], tmp_path, f"p{end}")
        f = _formations(pois, candles)
        assert (PoiType.BUY_ORDER_BLOCK in f.get((40, 41), {})) == (end >= 46), end


# ---- H4 author regression (real FXCM candles) ---------------------------------


@pytest.fixture(scope="module")
def author(tmp_path_factory):
    doc = json.loads(_FIXTURE.read_text(encoding="utf-8"))
    rows = doc["synthetic_context"] + doc["real"]
    path = tmp_path_factory.mktemp("author") / "h4.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow((r["time"], r["open"], r["high"], r["low"], r["close"], 1))
    candles = load_v1a_csv(
        path,
        Timeframe.H4,
        close_time_ms_by_open_ms={int(r["time"]): int(r["close_time"]) for r in rows},
    )
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(candles, _MEASUREMENT_CONFIG, identity)
    pois = analyze_pois(
        (PoiTimeframeInput(Timeframe.H4, candles, measurement),), _POI_CONFIG, identity
    )
    return doc, candles, measurement, pois


def _utc(candle) -> str:
    return candle.event_time_utc.strftime("%Y-%m-%dT%H:%MZ")


def test_author_fixture_real_bars_follow_the_sealed_range(author) -> None:
    doc, candles, _m, _p = author
    real = candles[len(doc["synthetic_context"]) :]
    assert _utc(real[0]) == "2026-08-03T10:00Z"
    assert all(
        _utc(c) < "2026-07-14T17:15Z" for c in candles[: len(doc["synthetic_context"])]
    )


def test_author_h4_structure_is_the_real_swing_sequence(author) -> None:
    _d, candles, measurement, _p = author
    seq = [
        (s.swing_type.value, _utc(candles[s.pivot_bar_index]), str(s.pivot_price))
        for s in measurement.confirmed_swings
        if _utc(candles[s.pivot_bar_index]) >= "2026-08-03"
    ][:4]
    assert seq == [
        ("SWING_LOW", "2026-08-03T10:00Z", "4019.03"),
        ("SWING_HIGH", "2026-08-04T14:00Z", "4106.14"),
        ("SWING_LOW", "2026-08-04T22:00Z", "4065.46"),
        ("SWING_HIGH", "2026-08-06T02:00Z", "4304.06"),
    ]
    bos = [
        _utc(
            candles[
                next(
                    i for i, c in enumerate(candles) if c.record_id == t.break_candle_id
                )
            ]
        )
        for t in _walk(candles, measurement).transitions
        if t.transition_type is StructureTransitionType.BULLISH_BOS
    ]
    assert "2026-08-05T02:00Z" in bos


@pytest.mark.parametrize(
    ("source", "bottom", "top"),
    [
        ("2026-08-04T18:00Z", "4074.7", "4088.96"),  # author example 1
        ("2026-08-05T06:00Z", "4153.11", "4179.5"),  # author example 2
    ],
)
def test_author_h4_mid_leg_formations_are_bullish_engulfing_not_order_blocks(
    author, source: str, bottom: str, top: str
) -> None:
    _d, candles, _m, pois = author
    by_id = {c.record_id: c for c in candles}
    matches = {
        o.poi_type
        for o in pois.poi_observations
        if _utc(by_id[o.source_candle_record_ids[0]]) == source
        and (str(o.zone_bottom), str(o.zone_top)) == (bottom, top)
    }
    assert PoiType.BULLISH_ENGULFING in matches
    assert PoiType.BUY_ORDER_BLOCK not in matches
    raw = [
        f
        for f in detect_order_blocks(candles, _POI_CONFIG)
        if _utc(by_id[f.source_candle_record_ids[0]]) == source
    ]
    assert len(raw) == 1  # every frozen raw OB condition holds


def test_author_example_1_sits_on_a_confirmed_swing_after_the_leg_origin(
    author,
) -> None:
    """Why the earlier movement-origin gate called it an ORDER BLOCK, and why
    the leg-origin rule does not: its displacement candle IS a confirmed swing
    low (4065.46), but the leg that breaks structure at 08-05 02:00 departed
    from the lower 4019.03 swing (08-03 10:00)."""
    _d, candles, measurement, _p = author
    lows = {
        _utc(candles[s.pivot_bar_index]): s.pivot_price
        for s in measurement.confirmed_swings
        if s.swing_type is SwingType.SWING_LOW
    }
    assert lows["2026-08-04T22:00Z"] == Decimal("4065.46")
    assert lows["2026-08-03T10:00Z"] == Decimal("4019.03")
    assert lows["2026-08-03T10:00Z"] < lows["2026-08-04T22:00Z"]


# ---- immutability --------------------------------------------------------------


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_confirmed_order_block_survives_its_origin_swing_disappearing(
    tmp_path: Path, direction: str
) -> None:
    rows = _superseded_origin() if direction == "BUY" else mirror(_superseded_origin())
    ob = PoiType.BUY_ORDER_BLOCK if direction == "BUY" else PoiType.SELL_ORDER_BLOCK
    snapshot = None
    for end in range(43, len(rows)):
        pois, candles, measurement = analyze_rows(
            rows[: end + 1], tmp_path, f"{direction}{end}"
        )
        f = _formations(pois, candles)
        present = ob in f.get((40, 41), {})
        assert present == (end >= 44), end
        if present:
            fields = (f[(40, 41)][ob]["available"], f[(40, 41)][ob]["zone"])
            snapshot = snapshot or fields
            assert fields == snapshot, end  # source, geometry, availability fixed
    index = {c.record_id: i for i, c in enumerate(candles)}
    # the final recomputation no longer has the origin swing nor the break ...
    assert 40 not in {
        index[s.pivot_candle_record_ids[0]] for s in measurement.confirmed_swings
    }
    assert (
        leg_origin_order_blocks(
            detect_order_blocks(candles, _POI_CONFIG),
            candles,
            measurement.confirmed_swings,
        )
        == ()
    )
    # ... yet the ORDER BLOCK exists with its first-seen availability, and its
    # lifecycle continued normally (price broke through the zone).
    assert snapshot == (44, f[(40, 41)][ob]["zone"])
    assert f[(40, 41)][ob]["terminal"] is not None


def test_prefix_swing_replay_equals_the_batch_detector_every_prefix(
    tmp_path: Path,
) -> None:
    for name, rows in (("c", _continuation()), ("s", _superseded_origin())):
        candles = rows_to_candles(rows, tmp_path, name)
        for index, swings in iter_prefix_swing_candidates(candles, _MEASUREMENT_CONFIG):
            assert swings == detect_confirmed_swings(
                candles[: index + 1], _MEASUREMENT_CONFIG
            )


# ---- incremental kernel == batch at every prefix, and restart determinism -------


def _kernel_run(candles, stop: int | None = None):
    configuration = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=Decimal("0.01"),
    )
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for candle in candles[:stop]:
        kernel.advance_group({Timeframe.M15: (candle,)})
    return kernel, configuration


@pytest.mark.parametrize(
    ("name", "series"),
    [
        ("continuation", _continuation),
        ("continuation_sell", lambda: mirror(_continuation())),
        ("reversal", _reversal),
        ("superseded", _superseded_origin),
        ("superseded_sell", lambda: mirror(_superseded_origin())),
    ],
)
def test_replay_kernel_matches_batch_at_every_prefix(
    tmp_path: Path, name: str, series
) -> None:
    candles = rows_to_candles(series(), tmp_path, name)
    kernel, configuration = _kernel_run(candles, 0)
    for n, candle in enumerate(candles, start=1):
        kernel.advance_group({Timeframe.M15: (candle,)})
        if n < 30:
            continue
        incremental = kernel.finalize().poi_analysis
        batch = scan_market(
            (ScannerTimeframeInput(Timeframe.M15, candles[:n]),),
            (),
            configuration,
            ContentAddressedIdentityProvider(),
        ).poi_analysis
        assert incremental.poi_observations == batch.poi_observations, (name, n)
        assert incremental.current_poi_states == batch.current_poi_states, (name, n)


def test_replay_restart_is_deterministic(tmp_path: Path) -> None:
    candles = rows_to_candles(_superseded_origin(), tmp_path, "restart")
    first, _cfg = _kernel_run(candles)
    second, _cfg = _kernel_run(candles)
    a, b = first.finalize().poi_analysis, second.finalize().poi_analysis
    assert a.poi_observations == b.poi_observations
    assert a.current_poi_states == b.current_poi_states
    assert any(o.poi_type is PoiType.BUY_ORDER_BLOCK for o in a.poi_observations)
