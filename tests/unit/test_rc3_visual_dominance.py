"""RC3 visual dominance: ORDER BLOCK > ENGULFING > FVG for ONE formation.

Presentation only. A dominated FVG keeps its registry record (P3), its P5
evaluation and its P8 events; it is just not drawn and does not take a
display slot. Independence is decided by candle identity, never by overlap.
"""

from __future__ import annotations

import csv
import json
from decimal import Decimal
from itertools import permutations
from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.order_blocks import detect_order_blocks
from tests.parity_support.p4_atomic_state_replay import CODE_BY_POI_TYPE
from tests.parity_support.p7z_zone_model import (
    TIER_NA,
    TIER_STANDARD,
    PoiGeometry,
    apply_visual_dominance,
    build_visual_groups,
    build_visual_groups_fast,
    same_visual_formation,
    visual_selection_audit,
)
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "rc3_visual_dominance_fxcm_h4.json"
)
_EXAMPLES = json.loads(_FIXTURE.read_text(encoding="utf-8"))["examples"]
_CONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))

BUY_OB, SELL_OB, BUY_FVG, SELL_FVG = 1, 2, 3, 4
BULL_ENG, BEAR_ENG, SUPPORT, RESISTANCE = 11, 12, 17, 18


def _ms(dt) -> int:
    return int(dt.timestamp() * 1000)


def _registry(name: str, tmp_path: Path) -> dict[int, PoiGeometry]:
    """Run the frozen detectors over real candles and number the records in
    Pine's per-bar registration order (OB, FVG, engulfing)."""
    rows = _EXAMPLES[name]
    path = tmp_path / f"{name}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow((r["time"], r["open"], r["high"], r["low"], r["close"], 1))
    closes = {int(r["time"]): int(r["close_time"]) for r in rows}
    candles = load_v1a_csv(path, Timeframe.H4, close_time_ms_by_open_ms=closes)
    found = [
        *detect_order_blocks(candles, _CONFIG),
        *detect_fair_value_gaps(candles, _CONFIG),
        *detect_engulfing(candles, _CONFIG),
    ]
    order = {"ORDER_BLOCK": 0, "FAIR_VALUE_GAP": 1, "ENGULFING": 2}
    found.sort(
        key=lambda p: (
            p.availability_time_utc,
            next(v for k, v in order.items() if k in p.poi_type.value),
        )
    )
    return {
        i: PoiGeometry(
            i,
            CODE_BY_POI_TYPE[p.poi_type],
            1 if p.direction.value == "BULLISH" else -1,
            float(p.zone_top),
            float(p.zone_bottom),
            _ms(p.availability_time_utc),
            TIER_NA,
            _ms(p.candidate_event_time_utc),
        )
        for i, p in enumerate(found)
    }


def _g(idx, poi_type, top, bottom, avail, src, direction=1):
    return PoiGeometry(idx, poi_type, direction, top, bottom, avail, TIER_STANDARD, src)


# ---- real FXCM formations ----------------------------------------------


@pytest.mark.parametrize(
    ("name", "ob_type", "fvg_type"),
    [("coorigin_buy", BUY_OB, BUY_FVG), ("coorigin_sell", SELL_OB, SELL_FVG)],
)
def test_real_order_block_dominates_its_own_fvg(
    name: str, ob_type: int, fvg_type: int, tmp_path: Path
) -> None:
    geo = _registry(name, tmp_path)
    types = sorted(g.poi_type for g in geo.values())
    assert ob_type in types and fvg_type in types
    ob = next(g for g in geo.values() if g.poi_type == ob_type)
    fvg = next(g for g in geo.values() if g.poi_type == fvg_type)
    assert same_visual_formation(ob, fvg)
    # candle identity: the FVG starts on the OB origin candle, one bar later
    assert fvg.source_time_ms == ob.source_time_ms
    assert fvg.avail_time_ms > ob.avail_time_ms

    candidates, dominated = apply_visual_dominance(sorted(geo), geo)
    assert dominated == {fvg.idx: ob.idx}
    groups = build_visual_groups_fast(sorted(geo), geo, 0.0, 30, "240")
    labels = [g["label"] for g in groups]
    side = "BUY" if ob_type == BUY_OB else "SELL"
    assert f"H4 • {side} OB" in labels
    assert not any("FVG" in label for label in labels)  # annotation belongs to OB
    # the registry is untouched: every detector record is still present
    assert len(geo) == len(candidates) + len(dominated)
    audit = visual_selection_audit(sorted(geo), geo, 0.0, 30, "240")
    row = next(r for r in audit["rows"] if r["idx"] == fvg.idx)
    assert (row["suppressed_by"], row["reason"], row["drawn"]) == (
        ob.idx,
        "SAME_FORMATION_DOMINATED",
        False,
    )
    assert len(audit["rows"]) == len(geo)


def test_real_independent_fvg_near_an_order_block_stays_drawn(tmp_path: Path) -> None:
    geo = _registry("independent_near_ob", tmp_path)
    obs = [g for g in geo.values() if g.poi_type in (BUY_OB, SELL_OB)]
    fvgs = [g for g in geo.values() if g.poi_type in (BUY_FVG, SELL_FVG)]
    independent = [
        f
        for f in fvgs
        if not any(same_visual_formation(f, o) for o in obs)
        and any(
            o.direction == f.direction
            and o.zone_bottom <= f.zone_top
            and f.zone_bottom <= o.zone_top
            for o in obs
        )
    ]
    assert independent, "fixture must hold an FVG touching a different-origin OB"
    _candidates, dominated = apply_visual_dominance(sorted(geo), geo)
    groups = build_visual_groups_fast(sorted(geo), geo, 0.0, 30, "240")
    drawn = {m for g in groups for m in g["members"]}
    for f in independent:
        assert f.idx not in dominated
        assert f.idx in drawn


# ---- synthetic hierarchy cases ------------------------------------------


def test_engulfing_dominates_its_fvg_when_there_is_no_order_block() -> None:
    geo = {
        0: _g(0, BUY_FVG, 12.0, 10.5, 3000, 1000),
        1: _g(1, BULL_ENG, 10.5, 9.0, 2000, 1000),
    }
    _c, dominated = apply_visual_dominance([0, 1], geo)
    assert dominated == {0: 1}
    labels = [g["label"] for g in build_visual_groups_fast([0, 1], geo, 0.0, 30, "60")]
    assert labels == ["H1 • BULL ENGULF"]


def test_bearish_engulfing_dominates_its_sell_fvg() -> None:
    geo = {
        0: _g(0, BEAR_ENG, 21.0, 20.0, 2000, 1000, direction=-1),
        1: _g(1, SELL_FVG, 20.0, 18.0, 3000, 1000, direction=-1),
    }
    assert apply_visual_dominance([0, 1], geo)[1] == {1: 0}


def test_order_block_outranks_engulfing_as_owner() -> None:
    geo = {
        0: _g(0, BULL_ENG, 10.5, 9.0, 2000, 1000),
        1: _g(1, BUY_OB, 10.5, 9.0, 2000, 1000),
        2: _g(2, BUY_FVG, 12.0, 10.5, 3000, 1000),
    }
    assert apply_visual_dominance([0, 1, 2], geo)[1] == {2: 1}
    labels = [
        g["label"] for g in build_visual_groups_fast([0, 1, 2], geo, 0.0, 30, "240")
    ]
    assert labels == ["H4 • BUY OB"]


@pytest.mark.parametrize(
    "other",
    [
        _g(1, BUY_FVG, 12.0, 10.5, 3000, 999),  # different origin candle
        _g(1, SELL_FVG, 12.0, 10.5, 3000, 1000, direction=-1),  # other direction
        _g(1, SUPPORT, 12.0, 10.5, 3000, 1000),  # S/R is never dominated
        _g(1, BUY_FVG, 12.0, 10.5, 3000, None),  # identity unknown
    ],
)
def test_independent_structures_are_kept(other: PoiGeometry) -> None:
    geo = {0: _g(0, BUY_OB, 10.5, 9.0, 2000, 1000), 1: other}
    assert apply_visual_dominance([0, 1], geo)[1] == {}
    assert len(build_visual_groups_fast([0, 1], geo, 0.0, 30, "240")) == 2


def test_overlap_alone_never_dominates() -> None:
    # FVG fully INSIDE the OB zone but starting on another candle.
    geo = {
        0: _g(0, BUY_OB, 20.0, 5.0, 2000, 1000),
        1: _g(1, BUY_FVG, 12.0, 10.0, 9000, 8000),
    }
    assert not same_visual_formation(geo[0], geo[1])
    assert apply_visual_dominance([0, 1], geo)[1] == {}


def test_fvg_is_not_dominated_by_an_owner_outside_the_fresh_set() -> None:
    geo = {
        0: _g(0, BUY_OB, 10.5, 9.0, 2000, 1000),
        1: _g(1, BUY_FVG, 12.0, 10.5, 3000, 1000),
    }
    assert apply_visual_dominance([1], geo)[1] == {}  # OB mitigated / not fresh


def test_same_visual_formation_is_symmetric_and_irreflexive() -> None:
    pool = [
        _g(0, BUY_OB, 10.5, 9.0, 2000, 1000),
        _g(1, BULL_ENG, 10.5, 9.0, 2000, 1000),
        _g(2, BUY_FVG, 12.0, 10.5, 3000, 1000),
        _g(3, BUY_FVG, 13.0, 12.5, 4000, 2000),
        _g(4, SELL_OB, 10.5, 9.0, 2000, 1000, direction=-1),
        _g(5, SUPPORT, 10.5, 9.0, 2000, 1000),
    ]
    for a, b in permutations(pool, 2):
        assert same_visual_formation(a, b) == same_visual_formation(b, a)
    for a in pool:
        assert not same_visual_formation(a, a)
    assert not same_visual_formation(pool[2], pool[3])  # FVG + FVG


def test_dominated_fvg_frees_a_display_slot_for_an_independent_poi() -> None:
    geo = {
        0: _g(0, BUY_OB, 10.5, 9.0, 2000, 1000),
        1: _g(1, BUY_FVG, 12.0, 10.6, 3000, 1000),  # touches nothing else
        2: _g(2, RESISTANCE, 30.0, 29.0, 5000, 4000, direction=-1),
    }
    audit = visual_selection_audit([0, 1, 2], geo, 11.0, 2, "240")
    assert audit["visual_groups_before_dominance"] == 3
    assert audit["visual_groups"] == 2
    assert audit["slots_recovered"] == 1
    assert audit["boxes_drawn"] == 2
    drawn = {r["idx"] for r in audit["rows"] if r["drawn"]}
    assert drawn == {0, 2}  # the far resistance now fits


def test_oracle_and_fast_projection_agree_with_dominance() -> None:
    geo = {
        0: _g(0, BUY_OB, 10.5, 9.0, 2000, 1000),
        1: _g(1, BUY_FVG, 12.0, 10.5, 3000, 1000),
        2: _g(2, BUY_FVG, 12.2, 11.9, 5000, 4000),  # overlaps the dominated gap
        3: _g(3, SELL_FVG, 30.0, 28.0, 6000, 5500, direction=-1),
    }
    slow = build_visual_groups([0, 1, 2, 3], geo, 11.0, 30, "240")
    fast = build_visual_groups_fast([0, 1, 2, 3], geo, 11.0, 30, "240")
    assert slow == fast
    members = sorted(m for g in fast for m in g["members"])
    assert members == [0, 2, 3]  # 2 stays independent, no longer clustered with 1
