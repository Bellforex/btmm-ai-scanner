"""RC3 primary display name for order block / engulfing (author decision 1).

Presentation deduplication only. When the SAME formation is registered as both
an order block and a same-direction engulfing, the zone reads "ORDER BLOCK"
alone. Both registry records survive. Independent POIs that merely overlap
(a different engulfing, an FVG, an S/R zone) keep their own names.
"""

from __future__ import annotations

import hashlib
import re
from decimal import Decimal
from pathlib import Path

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from tests.parity_support.p7z_zone_model import (
    TIER_STANDARD,
    TIER_STRONG,
    PoiGeometry,
    build_visual_groups_fast,
    combined_zone_label,
    same_formation,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_USER = (
    Path(__file__).resolve().parents[2]
    / "tradingview"
    / "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine"
)

BUY_OB, SELL_OB, BUY_FVG = 1, 2, 3
BULL_ENG, BEAR_ENG, EVENING_STAR, RESISTANCE = 11, 12, 16, 18


def _geo(idx, poi_type, top, bottom, avail, direction=1, tier=TIER_STANDARD):
    return PoiGeometry(idx, poi_type, direction, top, bottom, avail, tier)


def _labels(geometry: dict[int, PoiGeometry], close: float = 0.0) -> list[str]:
    groups = build_visual_groups_fast(sorted(geometry), geometry, close, 30, "240")
    return sorted(g["label"] for g in groups)


def _members(geometry: dict[int, PoiGeometry]) -> list[int]:
    groups = build_visual_groups_fast(sorted(geometry), geometry, 0.0, 30, "240")
    return sorted(m for g in groups for m in g["members"])


# ---- model behaviour ----------------------------------------------------


def test_same_formation_buy_ob_and_bullish_engulfing_show_one_primary_name() -> None:
    geo = {
        0: _geo(0, BUY_OB, 10.0, 9.0, 1000),
        1: _geo(1, BULL_ENG, 10.0, 9.0, 1000),
    }
    assert same_formation(geo[0], geo[1])
    assert _labels(geo) == ["H4 • BUY OB"]
    assert _members(geo) == [0, 1]  # both semantic records remain


def test_same_formation_sell_ob_and_bearish_engulfing_show_one_primary_name() -> None:
    geo = {
        4: _geo(4, SELL_OB, 20.0, 19.0, 5000, direction=-1),
        5: _geo(5, BEAR_ENG, 20.0, 19.0, 5000, direction=-1, tier=TIER_STRONG),
    }
    label = combined_zone_label([4, 5], geo, "240")
    assert "ENGULF" not in label and label.startswith("H4 • SELL OB")
    assert _members(geo) == [4, 5]


def test_primary_name_does_not_depend_on_member_order() -> None:
    geo = {
        0: _geo(0, BULL_ENG, 10.0, 9.0, 1000),
        1: _geo(1, BUY_OB, 10.0, 9.0, 1000),
    }
    assert combined_zone_label([0, 1], geo, "240") == "H4 • BUY OB"


def test_different_origin_overlapping_ob_and_engulfing_keep_both_names() -> None:
    geo = {
        0: _geo(0, BUY_OB, 10.0, 9.0, 1000),
        1: _geo(1, BULL_ENG, 9.8, 8.5, 2000),  # overlaps, other formation
    }
    assert not same_formation(geo[0], geo[1])
    assert _labels(geo) == ["H4 • BULL ENGULF", "H4 • BUY OB"]
    assert _members(geo) == [0, 1]


def test_ob_and_fvg_both_remain() -> None:
    geo = {
        0: _geo(0, BUY_OB, 10.0, 9.0, 1000),
        1: _geo(1, BUY_FVG, 9.5, 9.2, 1000),
    }
    assert _labels(geo) == ["H4 • BUY FVG", "H4 • BUY OB"]
    assert _members(geo) == [0, 1]


def test_ob_and_sr_both_remain_even_on_identical_geometry() -> None:
    geo = {
        0: _geo(0, SELL_OB, 20.0, 19.0, 5000, direction=-1),
        1: _geo(1, RESISTANCE, 20.0, 19.0, 5000, direction=-1),
        2: _geo(2, RESISTANCE, 19.5, 18.0, 7000, direction=-1),
    }
    assert _labels(geo) == ["H4 • RESISTANCE", "H4 • SELL OB + RESISTANCE"]
    assert _members(geo) == [0, 1, 2]


def test_independent_pattern_on_the_same_formation_keeps_its_name() -> None:
    geo = {
        0: _geo(0, SELL_OB, 20.0, 19.0, 5000, direction=-1),
        1: _geo(1, BEAR_ENG, 20.0, 19.0, 5000, direction=-1),
        2: _geo(2, EVENING_STAR, 20.0, 19.0, 5000, direction=-1),
    }
    assert _labels(geo) == ["H4 • SELL OB + EVENING STAR"]


def test_engulfing_without_an_order_block_keeps_its_own_name() -> None:
    geo = {0: _geo(0, BEAR_ENG, 20.0, 19.0, 5000, direction=-1)}
    assert _labels(geo) == ["H4 • BEAR ENGULF"]


# ---- the identity invariant, on the real frozen detectors ---------------


def _candles(tmp_path: Path, rows: list[tuple[int, str, str, str, str]]):
    path = tmp_path / "c.csv"
    lines = ["time,open,high,low,close,volume"]
    lines += [f"{t},{o},{h},{lo},{c},1" for t, o, h, lo, c in rows]
    path.write_text("\n".join(lines), encoding="utf-8")
    return load_v1a_csv(path, Timeframe.M15)


def test_real_detectors_same_formation_shares_sources_and_group_key(
    tmp_path: Path,
) -> None:
    step = 900_000
    rows = [
        (0, "100", "101", "99", "100.5"),
        (step, "100.5", "100.8", "99.8", "100.0"),  # bearish origin
        (2 * step, "100.0", "103", "99.9", "102.8"),  # bullish, closes above
        (3 * step, "102.8", "103.5", "102", "103"),
    ]
    candles = _candles(tmp_path, rows)
    config = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
    obs = detect_order_blocks(candles, config)
    engs = detect_engulfing(candles, config)
    assert len(obs) == 1 and len(engs) == 1
    ob, eng = obs[0], engs[0]
    assert ob.source_candle_record_ids == eng.source_candle_record_ids
    assert ob.candidate_event_time_utc == eng.candidate_event_time_utc
    key = (ob.zone_top, ob.zone_bottom, ob.availability_time_utc, "BULLISH")
    assert key == (eng.zone_top, eng.zone_bottom, eng.availability_time_utc, "BULLISH")


# ---- the deployed Pine build --------------------------------------------


def _pine() -> str:
    return _USER.read_text(encoding="utf-8")


def _p7z_block(src: str) -> str:
    start = src.index("P7-Z — POI zone visualization")
    end = src.index("P9 — full-system integration trace")
    return "\n".join(line.split("//")[0] for line in src[start:end].splitlines())


def test_pine_suppresses_engulfing_name_only_inside_an_order_block_group() -> None:
    block = _p7z_block(_pine())
    assert (
        'if not str.contains(nmsCur, nm) and not (str.contains(nm, "ENGULFING") '
        'and str.contains(nmsCur, "ORDER BLOCK"))'
    ) in block
    # The group key is geometry + availability + direction, i.e. formation
    # identity for two-candle patterns; it must not be loosened to overlap.
    assert (
        'string gk = str.tostring(tp) + "|" + str.tostring(bt) + "|" + '
        'str.tostring(lf) + "|" + str.tostring(dr)'
    ) in block


def test_pine_registers_order_blocks_before_engulfing_on_the_same_bar() -> None:
    src = _pine()
    ob = src.index("        f_poiDetectOrderBlocks(p3Wn)")
    eng = src.index("        f_poiDetectEngulfing(p3Wn)")
    assert ob < eng


def test_presentation_change_leaves_every_non_p7z_line_untouched() -> None:
    # P3 detection/lifecycle, P5 and the P8 event stream all live outside the
    # P7-Z block; this hash is the same at 39c0640 (the performance gate) and
    # after the FVG draw fix and the primary-name rule.
    src = _pine()
    start = src.index("P7-Z — POI zone visualization")
    end = src.index("P9 — full-system integration trace")
    outside = hashlib.sha256((src[:start] + src[end:]).encode("utf-8")).hexdigest()
    assert outside == "f041fa85957bafe4e96e0a5256f760826c2e6da1f7f68f05ea08ab8080944a07"
    assert re.search(r"f_poiEmit\(typeCode", src)
