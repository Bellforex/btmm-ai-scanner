"""RC3 structural context gate and pressure-wick specialization (author 2026-09-17).

Decision A: a qualified candidate maps only when the frozen P2 structure at its
availability agrees with its direction (MAPPED_TREND_ALIGNED), or when a later
break confirms a leg of its direction that it formed inside (from the leg's
origin swing to the break): MAPPED_REVERSAL_CONTEXT at the break. Otherwise it
stays raw: CONTEXT_REJECT_COUNTER_TREND / CONTEXT_REJECT_NEUTRAL.

Decision B: HAMMER over a same-candle BULLISH PRESSURE WICK, SHOOTING STAR over a
same-candle BEARISH PRESSURE WICK. No other non-FVG ordering.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from btmm_ai_scanner.config.enums import Timeframe
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.engulfing import detect_engulfing
from btmm_ai_scanner.poi.enums import PoiType
from btmm_ai_scanner.poi.leg_origin import ContextReason, structure_context_decisions
from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks
from btmm_ai_scanner.poi.qualification import (
    QualificationReason,
    qualify_candidates,
)
from btmm_ai_scanner.poi.single_candle_reversals import detect_single_candle_reversals
from tests.parity_support.ob_origin_series import (
    analyze_rows,
    mirror,
    rows_to_candles,
    trend,
)
from tests.unit.test_rc3_order_block_leg_origin import _continuation, _reversal

_PCONFIG = PoiConfiguration(minimum_price_tick=__import__("decimal").Decimal("0.01"))


def _pairs(pois, candles, types):
    index = {c.record_id: i for i, c in enumerate(candles)}
    bar = {c.availability_time_utc: i for i, c in enumerate(candles)}
    return {
        (o.poi_type, tuple(index[c] for c in o.source_candle_record_ids)): bar[
            o.availability_time_utc
        ]
        for o in pois.poi_observations
        if o.poi_type in types
    }


def _decisions(rows, tmp_path, name):
    _pois, candles, measurement = analyze_rows(rows, tmp_path, name)
    index = {c.record_id: i for i, c in enumerate(candles)}
    engulfings = detect_engulfing(candles, _PCONFIG)
    return {
        tuple(index[c] for c in d.candidate.source_candle_record_ids): d
        for d in structure_context_decisions(
            engulfings, candles, measurement.confirmed_swings
        )
    }


# ---- decision A: the four context outcomes ------------------------------------


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_context_outcomes_on_continuation_and_reversal(
    tmp_path: Path, direction
) -> None:
    flip = (lambda r: r) if direction == "BUY" else mirror
    cont = _decisions(flip(_continuation()), tmp_path, f"c{direction}")
    # formed before the structure had any direction (bootstrap at bar 43)
    assert cont[(40, 41)].reason is ContextReason.CONTEXT_REJECT_NEUTRAL
    assert cont[(40, 41)].mapped is None
    # formed in the established leg of its own direction
    for pair in ((45, 46), (49, 50), (53, 54), (63, 64), (70, 71)):
        assert cont[pair].reason is ContextReason.MAPPED_TREND_ALIGNED, pair

    rev = _decisions(flip(_reversal()), tmp_path, f"r{direction}")
    # formed against the bearish structure, inside the leg the CHOCH confirms
    for pair in ((50, 51), (54, 55)):
        assert rev[pair].reason is ContextReason.MAPPED_REVERSAL_CONTEXT, pair
        candles = rows_to_candles(flip(_reversal()), tmp_path, f"rc{direction}")
        assert (
            rev[pair].mapped.availability_time_utc == candles[59].availability_time_utc
        )


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_counter_trend_noise_without_a_confirming_break_stays_raw(
    tmp_path: Path, direction
) -> None:
    # bullish structure, then a small bearish engulfing inside the running
    # bullish leg; no bearish break follows
    rows = _continuation()[:60]
    rows += [(128.0, 128.3, 127.9, 128.2), (128.2, 128.4, 127.2, 127.3)]  # 60-61
    rows += trend(127.3, 1.0, 12)
    rows = rows if direction == "BUY" else mirror(rows)
    decisions = _decisions(rows, tmp_path, f"n{direction}")
    assert decisions[(60, 61)].reason is ContextReason.CONTEXT_REJECT_COUNTER_TREND
    assert decisions[(60, 61)].mapped is None


# ---- no lookahead and immutability (prefix by prefix) -------------------------


@pytest.mark.parametrize("direction", ["BUY", "SELL"])
def test_context_mapping_never_precedes_and_never_changes(
    tmp_path: Path, direction
) -> None:
    flip = (lambda r: r) if direction == "BUY" else mirror
    rows = flip(_reversal())
    eng = PoiType.BULLISH_ENGULFING if direction == "BUY" else PoiType.BEARISH_ENGULFING
    first: dict = {}
    for end in range(50, len(rows)):
        pois, candles, _m = analyze_rows(
            rows[: end + 1], tmp_path, f"p{direction}{end}"
        )
        seen = _pairs(pois, candles, {eng})
        for key in ((eng, (50, 51)), (eng, (54, 55))):
            present = key in seen
            assert present == (end >= 59), (key, end)  # reversal: at the CHOCH
            if present:
                first.setdefault(key, seen[key])
                assert seen[key] == first[key] == 59  # availability never moves
    rows_c = flip(_continuation())
    for end in range(60, len(rows_c)):
        pois, candles, _m = analyze_rows(
            rows_c[: end + 1], tmp_path, f"q{direction}{end}"
        )
        seen = _pairs(pois, candles, {eng})
        assert seen.get((eng, (40, 41))) is None  # neutral: never mapped later
        assert seen[(eng, (53, 54))] == 54  # aligned: at its own availability


# ---- decision B: hammer / shooting star over the same candle's pressure wick --


def _candles(rows, tmp_path, name):
    return rows_to_candles(rows, tmp_path, name)


@pytest.mark.parametrize(
    ("rows", "named", "wick"),
    [
        # low 90, high 100, open 97.5, close 100: lower wick 75 %, body 25 %
        (
            [(95.0, 96.0, 94.0, 95.0), (97.5, 100.0, 90.0, 100.0)],
            PoiType.HAMMER,
            PoiType.BULLISH_PRESSURE_WICK,
        ),
        # mirror: upper wick 75 %, body 25 %
        (
            [(95.0, 96.0, 94.0, 95.0), (92.5, 100.0, 90.0, 90.0)],
            PoiType.SHOOTING_STAR,
            PoiType.BEARISH_PRESSURE_WICK,
        ),
    ],
)
def test_named_rejection_formation_is_primary_over_its_pressure_wick(
    tmp_path: Path, rows, named, wick
) -> None:
    candles = _candles(rows, tmp_path, named.value)
    last = candles[-1].record_id
    raw = [
        *[
            c
            for c in detect_single_candle_reversals(candles, _PCONFIG)
            if c.source_candle_record_ids == (last,)
        ],
        *[
            c
            for c in detect_pressure_wicks(candles, _PCONFIG)
            if c.source_candle_record_ids == (last,)
        ],
    ]
    assert {c.poi_type for c in raw} == {named, wick}  # both raw detections exist
    mapped, decisions = qualify_candidates(raw, {}, _PCONFIG)
    assert [c.poi_type for c in mapped] == [named]
    (decision,) = decisions
    assert decision.candidate.poi_type is wick
    assert decision.reason is QualificationReason.SAME_ORIGIN_SUPPRESSED
    assert decision.primary_type is named


def test_pressure_wick_on_another_candle_stays_mapped(tmp_path: Path) -> None:
    rows = [
        (95.0, 96.0, 94.0, 95.0),
        (97.5, 100.0, 90.0, 100.0),  # hammer + bullish pressure wick
        (100.0, 101.0, 99.0, 100.5),
        (95.0, 100.0, 90.0, 99.0),  # pressure wick only (body 40 %: not a hammer)
    ]
    candles = _candles(rows, tmp_path, "independent")
    raw = [
        *detect_single_candle_reversals(candles, _PCONFIG),
        *detect_pressure_wicks(candles, _PCONFIG),
    ]
    index = {c.record_id: i for i, c in enumerate(candles)}
    mapped, _d = qualify_candidates(raw, {}, _PCONFIG)
    kept = {(c.poi_type, index[c.source_candle_record_ids[0]]) for c in mapped}
    assert (PoiType.HAMMER, 1) in kept
    assert (PoiType.BULLISH_PRESSURE_WICK, 1) not in kept
    assert (PoiType.BULLISH_PRESSURE_WICK, 3) in kept


def test_other_same_candle_pairs_are_not_ordered(tmp_path: Path) -> None:
    from types import SimpleNamespace
    from uuid import uuid4

    from btmm_ai_scanner.poi.enums import PoiDirection

    cid = uuid4()
    bull = PoiDirection.BULLISH

    def c(t):
        return SimpleNamespace(
            poi_type=t, direction=bull, source_candle_record_ids=(uuid4(), cid)
        )

    items = [
        c(PoiType.BULLISH_ENGULFING),
        c(PoiType.BULLISH_PRESSURE_WICK),
        c(PoiType.MORNING_STAR),
        c(PoiType.BASE_RALLY),
    ]
    mapped, decisions = qualify_candidates(items, {}, _PCONFIG)
    assert mapped == items and decisions == []


def test_timeframe_is_irrelevant_to_the_rule() -> None:
    assert Timeframe.M15  # rule has no timeframe parameter (documented contract)


# ---- Pine USER / PARITY carry the same context gate and wick precedence ------

_TV = Path(__file__).resolve().parents[2] / "tradingview"


@pytest.mark.parametrize(
    "build",
    [
        "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine",
        "btmm_poi_btrc_scanner_rc3_parity_dev.pine",
    ],
)
def test_pine_build_gates_context_and_wick_precedence(build) -> None:
    code = "\n".join(
        ln
        for ln in (_TV / build).read_text(encoding="utf-8").splitlines()
        if not ln.strip().startswith("//")
    )
    emit = code[code.index("f_poiEmit(int typeCode") :]
    emit = emit[: emit.index("\n\n")]
    # keys recorded before any gate
    assert emit.index("map.put(poiOriginKey") < emit.index("bool gated")
    assert emit.index("map.put(poiNamedKey") < emit.index("bool gated")
    assert (
        "if typeCode == C_POI_HAMMER or typeCode == C_POI_SHOOTING_STAR\n"
        "        map.put(poiNamedKey, srcLastT * direction, true)"
    ) in emit
    assert (
        "bool gated = typeCode >= C_POI_BUY_FAIR_VALUE_GAP and typeCode <= "
        "C_POI_EVENING_STAR"
    ) in emit
    assert "if not wickNamed and gated and p2Direction == -direction" in emit
    assert "(not gated or p2Direction == direction)" in emit
    # hammer / shooting star are detected before pressure wicks on each bar
    run = code[code.index("f_poiDetectSingleCandleReversals(p3Wn)") - 400 :]
    assert run.index("f_poiDetectSingleCandleReversals(p3Wn)") < run.index(
        "f_poiDetectPressureWicks(p3Wn)"
    )
    gate = code[code.index("f_poiGateOrderBlocks() =>") :]
    gate = gate[: gate.index("\nf_poiApplyPromotions()")]
    # rescue at this bar's break, before the OB of the same break, regardless
    # of whether the origin swing already anchored an OB
    rescue = gate.index("while k2 < array.size(ctPending)")
    assert gate.index("if not na(best)\n") < rescue
    assert rescue < gate.index("if not na(best) and not map.contains(obSwingUsed")
    assert (
        "cp.candidateTime >= oStart and cp.availTime <= ev.availabilityTime"
    ) in gate
    assert (
        "math.max(math.max(cp.availTime, oConf), math.max(ev.availabilityTime, nowT))"
    ) in gate
