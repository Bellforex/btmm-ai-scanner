"""RC3 Doji rule (author decisions, 2026-09-17).

* A Doji candle (frozen star threshold: body / range <= 0.10) is never either
  candle of an ENGULFING or ORDER BLOCK formation.
* No DOJI POI type is created ("suppress only"): the pair is simply not an
  engulfing / order block.
* A Doji may still be the middle candle of a MORNING / EVENING STAR, and
  HAMMER / SHOOTING STAR keep their frozen rules unchanged.

Real fixtures are FXCM XAUUSD H4 candles; every "misclassified before" case
asserts the exact pre-rule conditions still hold (size ratio, colours, close
beyond the origin extreme), so the test fails if a fixture stops exercising
the rule.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.measurements.candle_metrics import body_efficiency, total_range
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from btmm_ai_scanner.poi.three_candle_stars import detect_three_candle_stars
from tests.parity_support.ob_origin_series import rows_to_candles
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "rc3_doji_fxcm_h4.json"
_EXAMPLES = json.loads(_FIXTURE.read_text(encoding="utf-8"))["examples"]
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_DOJI = _CONFIG.doji_body_efficiency_standard
_TV = Path(__file__).resolve().parents[2] / "tradingview"


def _candles(name: str, tmp_path: Path):
    rows = _EXAMPLES[name]
    path = tmp_path / f"{name}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow((r["time"], r["open"], r["high"], r["low"], r["close"], 1))
    closes = {int(r["time"]): int(r["close_time"]) for r in rows}
    return load_v1a_csv(path, Timeframe.H4, close_time_ms_by_open_ms=closes)


def _pre_rule_engulfing(a, b) -> bool:
    if total_range(a) == 0:
        return False
    ratio = total_range(b) / total_range(a)
    colours = (a.close < a.open and b.close > b.open) or (
        a.close > a.open and b.close < b.open
    )
    return ratio >= _CONFIG.order_block_size_ratio_standard and colours


def _pre_rule_order_block(a, b) -> bool:
    if not _pre_rule_engulfing(a, b):
        return False
    return (b.close > a.open and b.close > a.high) or (
        b.close < a.open and b.close < a.low
    )


@pytest.mark.parametrize(
    "name",
    [
        "bullish_engulfing_doji_first",
        "bearish_engulfing_doji_first",
        "bullish_engulfing_doji_second",
        "bearish_engulfing_doji_second",
    ],
)
def test_real_doji_pair_is_no_longer_an_engulfing(name: str, tmp_path: Path) -> None:
    a, b = _candles(name, tmp_path)
    assert _pre_rule_engulfing(a, b)  # this pair WAS an engulfing
    assert body_efficiency(a) <= _DOJI or body_efficiency(b) <= _DOJI
    assert detect_engulfing((a, b), _CONFIG) == ()


@pytest.mark.parametrize(
    "name", ["buy_ob_formation_doji_origin", "sell_ob_formation_doji_origin"]
)
def test_real_doji_origin_is_no_longer_an_order_block_formation(
    name: str, tmp_path: Path
) -> None:
    a, b = _candles(name, tmp_path)
    assert _pre_rule_order_block(a, b)  # this pair WAS an OB formation
    assert body_efficiency(a) <= _DOJI
    assert detect_order_blocks((a, b), _CONFIG) == ()
    assert detect_engulfing((a, b), _CONFIG) == ()


@pytest.mark.parametrize(
    ("name", "poi_type"),
    [
        ("morning_star_doji_middle", PoiType.MORNING_STAR),
        ("evening_star_doji_middle", PoiType.EVENING_STAR),
    ],
)
def test_a_doji_is_still_a_valid_star_middle(
    name: str, poi_type: PoiType, tmp_path: Path
) -> None:
    candles = _candles(name, tmp_path)
    assert body_efficiency(candles[1]) <= _DOJI
    stars = detect_three_candle_stars(candles, _CONFIG)
    assert [s.poi_type for s in stars] == [poi_type]


def test_hammer_with_a_doji_body_is_unchanged(tmp_path: Path) -> None:
    candles = _candles("hammer_doji_body", tmp_path)
    assert body_efficiency(candles[-1]) <= _DOJI
    found = detect_single_candle_reversals(candles, _CONFIG)
    assert any(
        c.poi_type == PoiType.HAMMER
        and c.source_candle_record_ids == (candles[-1].record_id,)
        for c in found
    )


# ---- synthetic boundaries ---------------------------------------------------


def _pair(first_body: float, second_body: float, bullish: bool, tmp_path: Path):
    """First candle range 2.0 (100-102); second candle range 6.0 (99-105)."""
    if bullish:
        a = (101.0, 102.0, 100.0, 101.0 - first_body)
        b = (99.0, 105.0, 99.0, 99.0 + second_body)
    else:
        a = (101.0, 102.0, 100.0, 101.0 + first_body)
        b = (105.0, 105.0, 99.0, 105.0 - second_body)
    name = f"p{first_body}_{second_body}_{bullish}"
    return rows_to_candles([a, b], tmp_path, name)


@pytest.mark.parametrize("bullish", [True, False])
def test_bullish_and_bearish_looking_doji_first_candle(
    bullish: bool, tmp_path: Path
) -> None:
    doji = _pair(0.2, 5.5, bullish, tmp_path)  # 0.2 / 2.0 = 0.10 -> Doji
    assert detect_engulfing(doji, _CONFIG) == ()
    assert detect_order_blocks(doji, _CONFIG) == ()
    real = _pair(0.3, 5.5, bullish, tmp_path)  # 0.15 -> not a Doji
    assert len(detect_engulfing(real, _CONFIG)) == 1
    assert len(detect_order_blocks(real, _CONFIG)) == 1


@pytest.mark.parametrize("bullish", [True, False])
def test_doji_bodied_second_candle(bullish: bool, tmp_path: Path) -> None:
    doji = _pair(0.6, 0.6, bullish, tmp_path)  # 0.6 / 6.0 = 0.10 -> Doji
    assert detect_engulfing(doji, _CONFIG) == ()
    assert detect_order_blocks(doji, _CONFIG) == ()


# ---- Pine port -----------------------------------------------------------------


@pytest.mark.parametrize(
    "build",
    [
        "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine",
        "btmm_poi_btrc_scanner_rc3_parity_dev.pine",
    ],
)
def test_pine_builds_apply_the_same_doji_rule(build: str) -> None:
    source = (_TV / build).read_text(encoding="utf-8")
    for a, b in (("oi", "di"), ("ei", "gi")):
        assert (
            f"if ratio >= C_POI_OB_RATIO_STANDARD and f_poiBodyEff({a}) > "
            f"C_POI_DOJI_BODY_EFF_STANDARD and f_poiBodyEff({b}) > "
            "C_POI_DOJI_BODY_EFF_STANDARD"
        ) in source
    assert "float C_POI_DOJI_BODY_EFF_STANDARD   = 0.10" in source
