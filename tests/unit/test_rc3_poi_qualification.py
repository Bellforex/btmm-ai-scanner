"""RC3 POI qualification: DETECT -> QUALITY -> ARBITRATE -> MAP.

Author decisions (2026-09-17): an FVG is mapped only when its gap is at least
0.35 x ATR-14 of its departure candle; one originating formation maps one
primary POI (a same-direction candle pattern whose final candle is the FVG's
departure candle is primary; the FVG is suppressed). Real FXCM author cases and
synthetic mutations; every case runs the real engine.
"""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.domain.analyzer import analyze_market_measurements
from btmm_ai_scanner.domain.configuration import MarketMeasurementConfiguration
from btmm_ai_scanner.historical_backtest.identity import (
    ContentAddressedIdentityProvider,
)
from btmm_ai_scanner.measurements.atr import compute_atr_series
from btmm_ai_scanner.poi.analyzer import PoiTimeframeInput, analyze_pois
from btmm_ai_scanner.poi.configuration import (
    InvalidPoiConfigurationError,
    PoiConfiguration,
    validate_configuration,
)
from btmm_ai_scanner.poi.enums import PoiDirection, PoiType
from btmm_ai_scanner.poi.fair_value_gaps import detect_fair_value_gaps
from btmm_ai_scanner.poi.qualification import (
    QualificationReason,
    qualify_candidates,
)
from btmm_ai_scanner.scanner.analyzer import scan_market
from btmm_ai_scanner.scanner.replay import IncrementalReplayKernel
from btmm_ai_scanner.scanner.timeframe_input import ScannerTimeframeInput
from tests.parity_support.level_a_replay import build_scanner_configuration
from tests.parity_support.v1a_csv_loader import load_v1a_csv

_FIXTURE = (
    Path(__file__).resolve().parents[1] / "fixtures" / "rc3_qualification_fxcm.json"
)
_MCONFIG = MarketMeasurementConfiguration(minimum_price_tick=Decimal("0.01"))
_PCONFIG = PoiConfiguration(minimum_price_tick=Decimal("0.01"))
_FVG = (PoiType.BUY_FAIR_VALUE_GAP, PoiType.SELL_FAIR_VALUE_GAP)


def _load(tmp_path_factory, key: str, tf: Timeframe):
    rows = json.loads(_FIXTURE.read_text(encoding="utf-8"))[key]
    path = tmp_path_factory.mktemp(key) / f"{key}.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("time", "open", "high", "low", "close", "volume"))
        for r in rows:
            writer.writerow((r["time"], r["open"], r["high"], r["low"], r["close"], 1))
    return load_v1a_csv(
        path,
        tf,
        close_time_ms_by_open_ms={int(r["time"]): int(r["close_time"]) for r in rows},
    )


def _mapped(candles, tf: Timeframe):
    identity = ContentAddressedIdentityProvider()
    measurement = analyze_market_measurements(candles, _MCONFIG, identity)
    pois = analyze_pois(
        (PoiTimeframeInput(tf, candles, measurement),), _PCONFIG, identity
    )
    return pois.poi_observations


def _utc(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


@pytest.fixture(scope="module")
def m15(tmp_path_factory):
    return _load(tmp_path_factory, "m15", Timeframe.M15)


@pytest.fixture(scope="module")
def h1(tmp_path_factory):
    return _load(tmp_path_factory, "h1", Timeframe.H1)


def _raw_fvg(candles, source: str):
    by_id = {c.record_id: c for c in candles}
    return [
        f
        for f in detect_fair_value_gaps(candles, _PCONFIG)
        if _utc(by_id[f.source_candle_record_ids[0]].event_time_utc) == source
    ]


# ---- author case A / B: weak and valid M15 BUY FVG ---------------------------


@pytest.mark.parametrize(
    ("source", "bottom", "top", "quality", "context"),
    [
        # author: weak (X) -> never passes quality, never mapped
        ("2026-09-17T05:15", "4294.06", "4295.89", False, None),
        # author: valid (tick) -> passes quality; on this M15 window the frozen
        # structure is still BEARISH (no bullish CHOCH yet), so the bullish gap
        # is counter-trend and stays raw until a break confirms the leg
        (
            "2026-09-17T05:30",
            "4298.06",
            "4304.27",
            True,
            "CONTEXT_REJECT_COUNTER_TREND",
        ),
    ],
)
def test_author_m15_fvg_pair(m15, source, bottom, top, quality, context) -> None:
    raw = _raw_fvg(m15, source)
    assert len(raw) == 1 and raw[0].poi_type is PoiType.BUY_FAIR_VALUE_GAP
    assert (str(raw[0].zone_bottom), str(raw[0].zone_top)) == (bottom, top)
    atr = compute_atr_series(m15, 14)
    atr_by = {c.record_id: a for c, a in zip(m15, atr, strict=True)}
    passed, _d = qualify_candidates(raw, atr_by, _PCONFIG)
    assert bool(passed) is quality
    by_id = {c.record_id: c for c in m15}
    present = [
        o
        for o in _mapped(m15, Timeframe.M15)
        if o.poi_type is PoiType.BUY_FAIR_VALUE_GAP
        and _utc(by_id[o.source_candle_record_ids[0]].event_time_utc) == source
    ]
    assert not present
    if context is not None:
        from btmm_ai_scanner.poi.leg_origin import structure_context_decisions

        measurement = analyze_market_measurements(
            m15, _MCONFIG, ContentAddressedIdentityProvider()
        )
        (decision,) = structure_context_decisions(
            passed, m15, measurement.confirmed_swings
        )
        assert decision.reason.value == context


def test_author_m15_fvg_decisions_carry_the_gap_quality(m15) -> None:
    atr = compute_atr_series(m15, 14)
    atr_by = {c.record_id: a for c, a in zip(m15, atr, strict=True)}
    raws = _raw_fvg(m15, "2026-09-17T05:15") + _raw_fvg(m15, "2026-09-17T05:30")
    _mapped_c, decisions = qualify_candidates(raws, atr_by, _PCONFIG)
    weak, valid = decisions
    assert weak.reason is QualificationReason.QUALITY_REJECT
    assert weak.gap_atr_ratio is not None and weak.gap_atr_ratio < Decimal("0.25")
    assert valid.reason is QualificationReason.MAPPED
    assert valid.gap_atr_ratio is not None and valid.gap_atr_ratio > Decimal("0.60")


# ---- author H1 case: pressure wick is primary over its own FVG ---------------


def test_author_h1_pressure_wick_is_primary_over_same_origin_fvg(h1) -> None:
    by_id = {c.record_id: c for c in h1}
    raw = _raw_fvg(h1, "2026-09-17T04:00")
    assert len(raw) == 1
    departure = by_id[raw[0].source_candle_record_ids[1]]
    assert _utc(departure.event_time_utc) == "2026-09-17T05:00"

    observations = _mapped(h1, Timeframe.H1)
    wicks = [
        o
        for o in observations
        if o.poi_type is PoiType.BULLISH_PRESSURE_WICK
        and o.source_candle_record_ids == (departure.record_id,)
    ]
    assert len(wicks) == 1
    # counter-trend at 06:00 (bearish structure); the 11:00 bullish CHOCH confirms
    # the leg departing from the 09-16 19:00 low, so the wick maps at the break
    assert _utc(wicks[0].availability_time_utc) == "2026-09-17T12:00"
    assert not [
        o
        for o in observations
        if o.poi_type is PoiType.BUY_FAIR_VALUE_GAP
        and o.source_candle_record_ids == raw[0].source_candle_record_ids
    ]
    atr = compute_atr_series(h1, 14)
    atr_by = {c.record_id: a for c, a in zip(h1, atr, strict=True)}
    _m, decisions = qualify_candidates(
        [*wicks_raw(h1, departure), raw[0]], atr_by, _PCONFIG
    )
    assert decisions[0].reason is QualificationReason.SAME_ORIGIN_SUPPRESSED
    assert decisions[0].primary_type is PoiType.BULLISH_PRESSURE_WICK


def wicks_raw(candles, candle):
    from btmm_ai_scanner.poi.pressure_wicks import detect_pressure_wicks

    return [
        w
        for w in detect_pressure_wicks(candles, _PCONFIG)
        if w.source_candle_record_ids == (candle.record_id,)
    ]


# ---- synthetic unit mutations -----------------------------------------------


_T0 = datetime(2026, 8, 10, tzinfo=UTC)


def _fvg(ids, bottom: str, top: str, direction=PoiDirection.BULLISH):
    from btmm_ai_scanner.poi.fair_value_gaps import FairValueGapCandidate

    return FairValueGapCandidate(
        symbol=InternalSymbol.XAUUSD,
        timeframe=Timeframe.M15,
        poi_type=PoiType.BUY_FAIR_VALUE_GAP
        if direction is PoiDirection.BULLISH
        else PoiType.SELL_FAIR_VALUE_GAP,
        direction=direction,
        zone_top=Decimal(top),
        zone_bottom=Decimal(bottom),
        source_candle_record_ids=tuple(ids),
        candidate_event_time_utc=_T0,
        confirmation_time_utc=_T0 + timedelta(minutes=45),
        availability_time_utc=_T0 + timedelta(minutes=45),
    )


def _pattern(poi_type, last_id, direction=PoiDirection.BULLISH):
    from types import SimpleNamespace

    return SimpleNamespace(
        poi_type=poi_type,
        direction=direction,
        source_candle_record_ids=(uuid4(), last_id),
    )


def test_tiny_gap_is_rejected_and_wide_gap_is_mapped() -> None:
    ids = [uuid4(), uuid4(), uuid4()]
    atr = {ids[1]: Decimal("10")}
    tiny = _fvg(ids, "100.00", "100.01")
    edge = _fvg(ids, "100.00", "103.50")  # exactly 0.35 x ATR
    below = _fvg(ids, "100.00", "103.49")
    mapped, decisions = qualify_candidates([tiny, edge, below], atr, _PCONFIG)
    assert mapped == [edge]
    assert [d.reason for d in decisions] == [
        QualificationReason.QUALITY_REJECT,
        QualificationReason.MAPPED,
        QualificationReason.QUALITY_REJECT,
    ]


def test_frozen_threshold_boundary_uses_the_departure_candle_atr() -> None:
    """Decision C (2026-09-17): 0.35 frozen; 0.349999 rejects, 0.35 admits; the
    ATR is the departure (middle) candle's, never the first or third."""
    assert _PCONFIG.fvg_min_gap_atr_ratio == Decimal("0.35")
    ids = [uuid4(), uuid4(), uuid4()]
    atr = {ids[0]: Decimal("0.0001"), ids[1]: Decimal("1"), ids[2]: Decimal("1000")}
    below = _fvg(ids, "100.000000", "100.349999")
    at = _fvg(ids, "100.000000", "100.350000")
    mapped, decisions = qualify_candidates([below, at], atr, _PCONFIG)
    assert mapped == [at]
    assert [d.reason for d in decisions] == [
        QualificationReason.QUALITY_REJECT,
        QualificationReason.MAPPED,
    ]

def test_no_atr_yet_means_the_gap_cannot_qualify() -> None:
    ids = [uuid4(), uuid4(), uuid4()]
    mapped, decisions = qualify_candidates(
        [_fvg(ids, "1", "900")], {ids[1]: None}, _PCONFIG
    )
    assert mapped == [] and decisions[0].reason is QualificationReason.QUALITY_REJECT


@pytest.mark.parametrize(
    "primary",
    [
        PoiType.BULLISH_PRESSURE_WICK,
        PoiType.BULLISH_ENGULFING,
        PoiType.HAMMER,
        PoiType.MORNING_STAR,
        PoiType.BASE_RALLY,
    ],
)
def test_same_origin_pattern_suppresses_the_fvg(primary) -> None:
    ids = [uuid4(), uuid4(), uuid4()]
    pattern = _pattern(primary, ids[1])
    fvg = _fvg(ids, "100", "110")
    mapped, decisions = qualify_candidates(
        [pattern, fvg], {ids[1]: Decimal("10")}, _PCONFIG
    )
    assert mapped == [pattern]
    assert decisions[0].reason is QualificationReason.SAME_ORIGIN_SUPPRESSED
    assert decisions[0].primary_type is primary


def test_independent_or_opposite_patterns_never_suppress_a_quality_fvg() -> None:
    ids = [uuid4(), uuid4(), uuid4()]
    fvg = _fvg(ids, "100", "110")
    later = _pattern(
        PoiType.BULLISH_ENGULFING, ids[2]
    )  # final candle = FVG third candle
    earlier = _pattern(PoiType.HAMMER, ids[0])  # final candle = FVG first candle
    opposite = _pattern(PoiType.BEARISH_PRESSURE_WICK, ids[1], PoiDirection.BEARISH)
    mapped, decisions = qualify_candidates(
        [later, earlier, opposite, fvg], {ids[1]: Decimal("10")}, _PCONFIG
    )
    assert fvg in mapped and decisions[0].reason is QualificationReason.MAPPED


def test_quality_threshold_must_be_positive() -> None:
    with pytest.raises(InvalidPoiConfigurationError):
        validate_configuration(
            PoiConfiguration(
                minimum_price_tick=Decimal("0.01"), fvg_min_gap_atr_ratio=Decimal("0")
            )
        )


# ---- no lookahead, prefix stability, kernel == batch -------------------------


def test_mapping_decided_at_availability_never_changes_later(m15) -> None:
    def fvgs(n):
        return {
            (
                o.source_candle_record_ids,
                o.availability_time_utc,
                o.zone_bottom,
                o.zone_top,
            )
            for o in _mapped(m15[:n], Timeframe.M15)
            if o.poi_type in _FVG
        }

    cut = (
        next(
            i for i, c in enumerate(m15) if _utc(c.event_time_utc) == "2026-09-17T05:45"
        )
        + 1
    )
    before = fvgs(cut)
    for n in (cut + 1, cut + 4, len(m15)):
        after = fvgs(n)
        assert before <= after, n  # nothing mapped earlier disappears or changes
        assert all(
            item[1] > m15[cut - 1].availability_time_utc for item in after - before
        )


@pytest.mark.parametrize("key", ["m15", "h1"])
def test_replay_kernel_matches_batch(tmp_path_factory, key) -> None:
    tf = Timeframe.M15 if key == "m15" else Timeframe.H1
    candles = _load(tmp_path_factory, key, tf)
    configuration = build_scanner_configuration(
        required_timeframes=frozenset({tf}),
        optional_timeframes=frozenset(),
        minimum_price_tick=Decimal("0.01"),
    )
    kernel = IncrementalReplayKernel(
        (tf,), configuration, ContentAddressedIdentityProvider(), ()
    )
    for n, candle in enumerate(candles, start=1):
        kernel.advance_group({tf: (candle,)})
        if n not in (60, 100, len(candles) - 3, len(candles)):
            continue
        incremental = kernel.finalize().poi_analysis
        batch = scan_market(
            (ScannerTimeframeInput(tf, candles[:n]),),
            (),
            configuration,
            ContentAddressedIdentityProvider(),
        ).poi_analysis
        assert incremental.poi_observations == batch.poi_observations, (key, n)
        assert incremental.current_poi_states == batch.current_poi_states, (key, n)


# ---- Pine USER / PARITY carry the same qualification contract ----------------

_TV = Path(__file__).resolve().parents[2] / "tradingview"


@pytest.mark.parametrize(
    "build",
    [
        "btmm_poi_btrc_scanner_rc3_poi_semantics_dev.pine",
        "btmm_poi_btrc_scanner_rc3_parity_dev.pine",
    ],
)
def test_pine_build_gates_fvg_quality_and_same_origin(build) -> None:
    code = "\n".join(
        ln
        for ln in (_TV / build).read_text(encoding="utf-8").splitlines()
        if not ln.strip().startswith("//")
    )
    assert "float C_POI_FVG_MIN_GAP_ATR          = 0.35" in code
    assert (
        "if typeCode >= C_POI_BASE_RALLY and typeCode <= C_POI_EVENING_STAR\n"
        "        map.put(poiOriginKey, srcLastT * direction, true)"
    ) in code
    fvg = code[code.index("f_poiDetectFvg(int wn) =>") :]
    fvg = fvg[: fvg.index("\nf_poiDetectEngulfing(")]
    assert (
        "if typeCode != 0 and zoneTop - zoneBottom >= C_POI_FVG_MIN_GAP_ATR * "
        "array.get(wAtr, mi) and not map.contains(poiOriginKey, "
        "array.get(wOpenT, mi) * direction)"
    ) in fvg
    assert _PCONFIG.fvg_min_gap_atr_ratio == Decimal(
        "0.35"
    )  # Python master value the Pine constant mirrors


def test_parity_p5_wire_reports_the_reported_lifecycle_status() -> None:
    # Python's P5 row carries CurrentPoiState.poi_lifecycle_status, which includes
    # a pending breach window; Pine's committed `poiStatus` lags it on the first
    # touch bar. The capture wire must log `poiReported`.
    code = (_TV / "btmm_poi_btrc_scanner_rc3_parity_dev.pine").read_text(
        encoding="utf-8"
    )
    assert '"|poiStatus=" + str.tostring(array.get(poiReported, i))' in code
    assert (
        'str.tostring(array.get(poiTier, i)) + "," + '
        'str.tostring(array.get(poiReported, i)) + ","'
    ) in code
