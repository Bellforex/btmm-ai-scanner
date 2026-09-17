"""RC3 semantic revision: ORDER BLOCK = MOVEMENT ORIGIN (author, 2026-09-17).

Every case runs the REAL engine (measurement analyzer -> POI analyzer, and the
incremental replay kernel for the timing tests) on explicit synthetic rows.
SELL cases are exact price mirrors of the BUY cases.

Rule under test (``poi/order_blocks.apply_movement_origin_gate``): a frozen OB
formation is an ORDER BLOCK only when a meaningfully confirmed opposite swing
pivots on its origin or displacement candle; availability = that swing's
confirmation. Otherwise the formation is an ENGULFING only. The engulfing of a
promoted formation ends with PROMOTED_TO_ORDER_BLOCK at the OB's availability,
unless price already used it (first touch wins).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.domain.enums import SwingType
from btmm_ai_scanner.domain.swings import _find_single_candle_pivots
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import PoiTerminalReason, PoiType
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.ob_origin_series import (
    Row,
    analyze_rows,
    mirror,
    rows_to_candles,
    trend,
)

_POI_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_MEASUREMENT_CONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
BUY = (PoiType.BUY_ORDER_BLOCK, PoiType.BULLISH_ENGULFING)
SELL = (PoiType.SELL_ORDER_BLOCK, PoiType.BEARISH_ENGULFING)


def _series() -> list[Row]:
    rows = trend(100, 1.0, 16)  # 0-15 rising to 116
    rows += trend(116, -1.0, 10)  # 16-25 bearish leg to 106
    rows += [(106.0, 106.3, 104.5, 105.0)]  # 26 origin: end of bearish leg
    rows += [(105.0, 109.5, 104.8, 109.0)]  # 27 displacement: new bullish leg
    rows += trend(109, 1.0, 7)  # 28-34 leg continues
    rows += [(116.0, 116.8, 115.9, 115.95)]  # 35 mid-leg bearish candle
    rows += [(115.95, 118.2, 115.93, 118.0)]  # 36 mid-leg bullish engulfing
    rows += trend(118, 1.0, 2)  # 37-38
    rows += [(120.0, 120.6, 119.9, 119.95)]  # 39 second mid-leg bearish
    rows += [(119.95, 122.3, 119.92, 122.1)]  # 40 second mid-leg engulfing
    rows += trend(122.1, 1.0, 2)  # 41-42
    rows += trend(124.1, -1.0, 4)  # 43-46 pullback
    rows += [(120.1, 120.4, 118.7, 119.1)]  # 47 origin: end of pullback
    rows += [(119.1, 123.5, 118.9, 123.1)]  # 48 displacement: continuation leg
    rows += trend(123.1, 1.0, 8)  # 49-56
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
            "source_bar": index[o.source_candle_record_ids[0]],
            "available": bar[o.availability_time_utc],
            "terminal": s.terminal_reason,
            "terminal_bar": bar.get(s.terminal_time_utc),
        }
    return out


@pytest.fixture(scope="module", params=["BUY", "SELL"])
def case(request, tmp_path_factory):
    rows = _series() if request.param == "BUY" else mirror(_series())
    tmp = tmp_path_factory.mktemp(request.param)
    pois, candles, _measurement = analyze_rows(rows, tmp, request.param)
    ob, eng = BUY if request.param == "BUY" else SELL
    return _formations(pois, candles), ob, eng


def test_end_of_opposite_leg_is_an_order_block_available_at_confirmation(case) -> None:
    f, ob, eng = case
    reversal = f[(26, 27)]
    assert reversal[ob]["source_bar"] == 26  # source = origin candle
    assert reversal[ob]["available"] == 29  # swing low confirmed 2 bars later
    assert reversal[eng]["available"] == 27  # the engulfing keeps its timing
    assert reversal[eng]["terminal"] is PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK
    assert reversal[eng]["terminal_bar"] == 29
    assert reversal[ob]["terminal"] is None


def test_end_of_pullback_starting_a_continuation_leg_is_an_order_block(case) -> None:
    f, ob, eng = case
    pullback = f[(47, 48)]
    assert pullback[ob]["available"] == 50
    assert pullback[eng]["terminal"] is PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK


@pytest.mark.parametrize("pair", [(35, 36), (39, 40)])
def test_mid_leg_engulfings_are_never_order_blocks(case, pair) -> None:
    f, ob, eng = case
    assert ob not in f[pair]  # the raw formation met every OB condition
    assert eng in f[pair]
    assert f[pair][eng]["terminal"] is not PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK


def test_only_the_leg_origin_is_an_order_block(case) -> None:
    f, ob, _eng = case
    assert sorted(k for k, v in f.items() if ob in v) == [(26, 27), (47, 48)]


def test_one_live_record_per_formation(case) -> None:
    f, _ob, _eng = case
    for types in f.values():
        live = [t for t, v in types.items() if v["terminal"] is None]
        assert len(live) <= 1


# ---- the author's "pullback inside an already-started leg" pattern -----------


def test_local_dip_low_after_a_confirmed_low_is_mid_leg(tmp_path: Path) -> None:
    """The author's H4 example-1 pattern: inside a leg that already started
    from a confirmed low, a shallow dip whose low IS a radius-2 pivot and whose
    pair IS a raw OB formation -- but no swing high has confirmed since that
    low, so the frozen swing primitive never confirms a new low there. The
    formation is mid-leg: ENGULFING only."""
    rows = trend(100, 1.0, 16, 2.0)
    rows += trend(116, -1.0, 10, 2.0)
    rows += [(106.0, 108.0, 102.5, 105.0), (105.0, 116.0, 102.8, 113.0)]  # 26-27
    rows += trend(113.0, 0.5, 3, 0.1)  # 28-30 tight bars
    rows += [(114.5, 114.55, 113.9, 113.95)]  # 31 dip (bearish)
    rows += [(113.95, 116.4, 113.92, 116.35)]  # 32 bullish displacement
    rows += trend(116.35, 0.5, 8, 0.1)
    pois, candles, measurement = analyze_rows(rows, tmp_path, "dip")
    index = {c.record_id: i for i, c in enumerate(candles)}

    raw_pairs = [
        tuple(index[c] for c in ob.source_candle_record_ids)
        for ob in detect_order_blocks(candles, _POI_CONFIG)
    ]
    assert (31, 32) in raw_pairs  # every frozen OB condition holds
    pivots = _find_single_candle_pivots(
        candles, compute_atr_series(candles, 14), _MEASUREMENT_CONFIG
    )
    assert any(
        p.swing_type == SwingType.SWING_LOW and p.start_index in (31, 32)
        for p in pivots
    )  # the dip low is a local pivot
    confirmed = [
        (s.swing_type, index[s.pivot_candle_record_ids[0]])
        for s in measurement.confirmed_swings
    ]
    assert (SwingType.SWING_LOW, 26) in confirmed
    assert not any(t == SwingType.SWING_HIGH and i > 26 for t, i in confirmed)

    f = _formations(pois, candles)
    assert PoiType.BUY_ORDER_BLOCK in f[(26, 27)]
    assert PoiType.BULLISH_ENGULFING in f[(31, 32)]
    assert PoiType.BUY_ORDER_BLOCK not in f[(31, 32)]


# ---- a used zone stays mitigated ---------------------------------------------


def test_first_touch_before_confirmation_keeps_the_engulfing_mitigated(
    tmp_path: Path,
) -> None:
    rows = trend(100, 1.0, 16)
    rows += trend(116, -1.0, 10)
    rows += [(106.0, 106.3, 104.5, 105.0)]  # 26 origin
    rows += [(105.0, 109.5, 104.8, 109.0)]  # 27 displacement
    rows += [(109.0, 109.4, 106.0, 108.8)]  # 28 wicks back into the zone
    rows += trend(108.8, 1.2, 8)
    pois, candles, _m = analyze_rows(rows, tmp_path, "touched")
    f = _formations(pois, candles)
    eng = f[(26, 27)][PoiType.BULLISH_ENGULFING]
    assert eng["terminal"] is PoiTerminalReason.MITIGATED  # not PROMOTED
    assert eng["terminal_bar"] == 28
    # The formation is still a leg origin; its OB record starts after its own
    # availability under the existing lifecycle rule.
    assert f[(26, 27)][PoiType.BUY_ORDER_BLOCK]["available"] == 29


# ---- no lookahead: prefix by prefix ------------------------------------------


def test_order_block_never_exists_before_its_confirmation_bar(tmp_path: Path) -> None:
    rows = _series()
    for end in range(26, 33):
        pois, candles, _m = analyze_rows(rows[: end + 1], tmp_path, f"p{end}")
        f = _formations(pois, candles)
        has_ob = PoiType.BUY_ORDER_BLOCK in f.get((26, 27), {})
        assert has_ob == (end >= 29), end
        if (26, 27) in f:
            eng = f[(26, 27)][PoiType.BULLISH_ENGULFING]
            promoted = eng["terminal"] is PoiTerminalReason.PROMOTED_TO_ORDER_BLOCK
            assert promoted == (end >= 29), end


# ---- the incremental replay kernel equals the batch engine at every bar ------


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_replay_kernel_matches_batch_at_every_prefix(
    tmp_path: Path, direction: str
) -> None:
    rows = _series() if direction == "BUY" else mirror(_series())
    candles = rows_to_candles(rows, tmp_path, direction)
    configuration = build_scanner_configuration(
        required_timeframes=frozenset({Timeframe.M15}),
        optional_timeframes=frozenset(),
        minimum_price_tick=Decimal("0.01"),
    )
    kernel = IncrementalReplayKernel(
        (Timeframe.M15,), configuration, ContentAddressedIdentityProvider(), ()
    )
    order_blocks_seen = 0
    for n, candle in enumerate(candles, start=1):
        kernel.advance_group({Timeframe.M15: (candle,)})
        if n < 24:
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
        order_blocks_seen = sum(
            o.poi_type in (PoiType.BUY_ORDER_BLOCK, PoiType.SELL_ORDER_BLOCK)
            for o in incremental.poi_observations
        )
    assert order_blocks_seen == 2  # the reversal and the pullback origin
