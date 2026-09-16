"""RC3 FVG reference fixtures from real FXCM XAUUSD M15 data (Phase 10) and
the FVG mutation locks (Phase 29).

The candles are copied verbatim from a same-session TradingView export whose
window was proven identical to PARITY DEV v4's executed window (RUNMETA count
+ OHLC checksum). Each example's Pine lifecycle outcome at the end of that run
is recorded alongside it.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from tests.parity_support.p7z_zone_model import PoiGeometry, build_visual_groups_fast
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "rc3_fvg_reference_fxcm_m15.json"
)
_EXAMPLES: dict[str, dict] = json.loads(_FIXTURE.read_text(encoding="utf-8"))[
    "examples"
]
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))


def _candles(
    rows: list[dict], tmp_path: Path, name: str
) -> tuple[NormalizedCandle, ...]:
    path = tmp_path / f"{name}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow(
                (r["time"], r["open"], r["high"], r["low"], r["close"], "1")
            )
    closes = {int(r["time"]): int(r["close_time"]) for r in rows}
    return load_v1a_csv(path, Timeframe.M15, close_time_ms_by_open_ms=closes)


def _ms(dt) -> int:
    return int(dt.timestamp() * 1000)


def test_fixture_covers_every_required_reference_kind() -> None:
    kinds = set(_EXAMPLES)
    assert {
        "large_buy",
        "large_sell",
        "minimal_buy",
        "minimal_sell",
        "overlap_a",
        "overlap_b",
        "mitigated",
        "fresh",
    } <= kinds
    types = {e["type"] for e in _EXAMPLES.values()}
    assert types == {"BUY_FAIR_VALUE_GAP", "SELL_FAIR_VALUE_GAP"}


@pytest.mark.parametrize("name", sorted(_EXAMPLES))
def test_real_example_is_detected_exactly(name: str, tmp_path: Path) -> None:
    ex = _EXAMPLES[name]
    candles = _candles(ex["candles"], tmp_path, name)
    found = detect_fair_value_gaps(candles, _CONFIG)
    assert len(found) == 1, name
    fvg = found[0]
    assert fvg.poi_type.value == ex["type"]
    assert (
        str(fvg.zone_top) == ex["zone_top"]
        and str(fvg.zone_bottom) == ex["zone_bottom"]
    )
    # Geometry is the gap between candle 1 and candle 3, never a candle body.
    first, third = candles[0], candles[2]
    if ex["type"] == "BUY_FAIR_VALUE_GAP":
        assert (fvg.zone_top, fvg.zone_bottom) == (third.low, first.high)
    else:
        assert (fvg.zone_top, fvg.zone_bottom) == (first.low, third.high)
    assert fvg.zone_top > fvg.zone_bottom
    # Source is candle 1's open; availability is candle 3's real close.
    assert (
        _ms(fvg.candidate_event_time_utc) == ex["source_ms"] == ex["candles"][0]["time"]
    )
    assert (
        _ms(fvg.availability_time_utc)
        == ex["availability_ms"]
        == ex["candles"][2]["close_time"]
    )
    assert fvg.candidate_event_time_utc < fvg.availability_time_utc
    assert len(fvg.source_candle_record_ids) == 3


def test_minimal_gaps_are_admitted_without_a_width_threshold(tmp_path: Path) -> None:
    for name in ("minimal_buy", "minimal_sell"):
        ex = _EXAMPLES[name]
        width = Decimal(ex["zone_top"]) - Decimal(ex["zone_bottom"])
        assert Decimal("0") < width <= Decimal("0.05")
        assert (
            len(
                detect_fair_value_gaps(_candles(ex["candles"], tmp_path, name), _CONFIG)
            )
            == 1
        )


def test_overlapping_real_gaps_stay_two_distinct_detections(tmp_path: Path) -> None:
    a, b = _EXAMPLES["overlap_a"], _EXAMPLES["overlap_b"]
    assert Decimal(a["zone_bottom"]) <= Decimal(b["zone_top"])
    assert Decimal(b["zone_bottom"]) <= Decimal(a["zone_top"])
    assert (a["source_ms"], a["zone_top"]) != (b["source_ms"], b["zone_top"])


def test_recorded_pine_lifecycle_outcomes() -> None:
    mitigated = _EXAMPLES["mitigated"]["pine_p3life"]
    assert mitigated["freshActive"] == "false" and mitigated["termReason"] == "1"
    assert mitigated["firstTouch"] == mitigated["termTime"]  # first reaction mitigates
    fresh = _EXAMPLES["fresh"]["pine_p3life"]
    assert fresh["freshActive"] == "true" and fresh["termReason"] == "0"


# ---------------------------------------------------------------- mutations


def test_mutation_two_candles_never_form_a_gap(tmp_path: Path) -> None:
    for name, ex in _EXAMPLES.items():
        two = _candles(ex["candles"][:2], tmp_path, name + "_2")
        assert detect_fair_value_gaps(two, _CONFIG) == ()


def test_mutation_wrong_orientation_is_not_the_same_gap(tmp_path: Path) -> None:
    ex = _EXAMPLES["large_buy"]
    rows = ex["candles"]
    # Swap candle 1 and candle 3 prices (keeping times) -> any gap found must
    # not be a BUY gap with the original boundaries.
    swapped = [dict(rows[0]), dict(rows[1]), dict(rows[2])]
    for key in ("open", "high", "low", "close"):
        swapped[0][key], swapped[2][key] = rows[2][key], rows[0][key]
    found = detect_fair_value_gaps(_candles(swapped, tmp_path, "swapped"), _CONFIG)
    assert all(
        not (
            f.poi_type.value == "BUY_FAIR_VALUE_GAP"
            and str(f.zone_top) == ex["zone_top"]
        )
        for f in found
    )


def test_mutation_closing_the_gap_by_one_tick_rejects_it(tmp_path: Path) -> None:
    ex = _EXAMPLES["minimal_buy"]
    rows = [dict(r) for r in ex["candles"]]
    rows[2]["low"] = rows[0]["high"]  # third.low == first.high -> no strict gap
    found = detect_fair_value_gaps(_candles(rows, tmp_path, "closed"), _CONFIG)
    assert all(f.poi_type.value != "BUY_FAIR_VALUE_GAP" for f in found)


def test_mutation_fresh_fvg_is_never_dropped_before_display_selection() -> None:
    geometry = {
        i: PoiGeometry(
            i,
            3 if e["type"].startswith("BUY") else 4,
            1 if e["type"].startswith("BUY") else -1,
            float(e["zone_top"]),
            float(e["zone_bottom"]),
            e["availability_ms"],
            0,
        )
        for i, e in enumerate(_EXAMPLES.values())
    }
    groups = build_visual_groups_fast(sorted(geometry), geometry, 4300.0, 10**6, "15")
    members = sorted(m for g in groups for m in g["members"])
    assert members == sorted(geometry)
