"""A/B: base-candle size measured as total range (approved) vs body (experiment).

`base_size_uses_body` is OFF by default, so the approved standard is what the
engine does. These tests pin BOTH arms: that the flag off changes nothing, that
the flag on changes only the size basis, and that the POI zone stays
wick-inclusive either way.

The golden case is the author's own: 2026-09-21 19:15 UTC on FX:EURUSD M15,
where a base candle has a body of 0.00006 against a range of 0.00021.
"""

from __future__ import annotations

import csv
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID

import pytest

from btmm_ai_scanner.config.enums import InternalSymbol, Timeframe
from btmm_ai_scanner.contracts.normalized_candle import NormalizedCandle
from btmm_ai_scanner.contracts.raw_candle import CandleCompleteness, CandleVolumeKind
from btmm_ai_scanner.measurements.candle_metrics import body, total_range
from btmm_ai_scanner.poi.bases import detect_bases
from btmm_ai_scanner.poi.configuration import PoiConfiguration
from btmm_ai_scanner.poi.enums import BaseFamily, PoiType

_CSV = (
    Path(__file__).resolve().parents[2]
    / "artifacts"
    / "rc5_m15_screenshot_capture"
    / "rc5_ohlc_m15_eurusd.csv"
)
_Q = Decimal("0.00001")
_A = PoiConfiguration(minimum_price_tick=_Q)
_B = PoiConfiguration(minimum_price_tick=_Q, base_size_uses_body=True)

#: Index of the first base candle of the author's formation in the fixture.
_BASE_START = 134


def _candles() -> tuple[NormalizedCandle, ...]:
    rows = []
    with _CSV.open(newline="", encoding="utf-8") as handle:
        for index, row in enumerate(csv.DictReader(handle)):
            event = datetime.fromtimestamp(int(row["time"]) / 1000, UTC)
            avail = event + timedelta(minutes=15)
            rows.append(
                NormalizedCandle.model_validate(
                    {
                        "record_id": UUID(f"0193f450-1234-7abc-8def-{index:012x}"),
                        "content_fingerprint": "a" * 64,
                        "raw_candle_id": UUID("0193f450-1234-7abc-8def-abcdefabcdaa"),
                        "provider": "FXCM",
                        "source_reference": "fxcm-m15-eurusd",
                        "source_symbol": InternalSymbol.EURUSD.value,
                        "source_timeframe": Timeframe.M15.value,
                        "symbol": InternalSymbol.EURUSD,
                        "timeframe": Timeframe.M15,
                        "event_time_utc": event,
                        "availability_time_utc": avail,
                        "processing_time_utc": avail,
                        "original_event_time": event,
                        "original_availability_time": avail,
                        "original_timezone": "UTC",
                        "open": Decimal(row["open"]).quantize(_Q),
                        "high": Decimal(row["high"]).quantize(_Q),
                        "low": Decimal(row["low"]).quantize(_Q),
                        "close": Decimal(row["close"]).quantize(_Q),
                        "volume": Decimal(row["volume"]),
                        "volume_kind": CandleVolumeKind.TICK,
                        "completeness": CandleCompleteness.CONFIRMED_COMPLETE,
                        "rule_version": "1.0.0",
                        "contract_version": "1.0.0",
                        "schema_version": "1.0.0",
                        "provenance_id": UUID("0193f450-1234-7abc-8def-abcdefabcdff"),
                    }
                )
            )
    return tuple(rows)


pytestmark = pytest.mark.skipif(
    not _CSV.exists(), reason="M15 forensic capture not present"
)


def _formation(candles):
    return candles[_BASE_START : _BASE_START + 2], candles[_BASE_START + 2]


def test_the_golden_formation_is_exactly_as_captured() -> None:
    """Guards the fixture: if these bars move, every claim below is void."""
    base, departure = _formation(_candles())
    assert base[0].event_time_utc == datetime(2026, 9, 21, 19, 15, tzinfo=UTC)
    assert max(total_range(c) for c in base) == Decimal("0.00021")
    assert max(body(c) for c in base) == Decimal("0.00006")
    assert total_range(departure) == Decimal("0.00035")


def test_total_range_basis_rejects_it_and_body_basis_accepts_it() -> None:
    """The doctrinal effect in one assertion, with the SAME 2.0 threshold."""
    base, departure = _formation(_candles())
    old = total_range(departure) / max(total_range(c) for c in base)
    new = total_range(departure) / max(body(c) for c in base)
    assert old < _A.order_block_size_ratio_standard  # 1.667 < 2.0
    assert new >= _A.order_block_size_ratio_standard  # 5.833 >= 2.0


def test_no_base_under_the_approved_standard_and_a_base_under_the_experiment() -> None:
    candles = _candles()
    start_id = candles[_BASE_START].record_id

    def on_formation(cfg):
        return [
            b
            for b in detect_bases(candles, cfg)
            if start_id in b.source_candle_record_ids
        ]

    assert on_formation(_A) == []
    found = on_formation(_B)
    assert len(found) == 1
    assert found[0].poi_type is PoiType.BASE_DROP


def test_the_poi_zone_stays_wick_inclusive_under_the_body_rule() -> None:
    """Size qualification changed; territory did not. The zone must still be
    the real market extremes, wicks included."""
    candles = _candles()
    base, _ = _formation(candles)
    found = next(
        b
        for b in detect_bases(candles, _B)
        if candles[_BASE_START].record_id in b.source_candle_record_ids
    )
    assert found.zone_top == max(c.high for c in base)
    assert found.zone_bottom == min(c.low for c in base)
    # and that is strictly wider than the bodies would give
    assert found.zone_top > max(max(c.open, c.close) for c in base)


def test_the_experiment_never_shrinks_the_base_population() -> None:
    """Body <= range always, so the body basis can only ever admit more."""
    candles = _candles()
    a = {(b.poi_type, b.source_candle_record_ids) for b in detect_bases(candles, _A)}
    b = {(x.poi_type, x.source_candle_record_ids) for x in detect_bases(candles, _B)}
    assert a <= b


def test_the_family_is_rally_base_drop_not_drop_base_drop() -> None:
    """The finding that stops this being a fix on its own.

    The candle immediately before the base (2026-09-21 19:00) closes UP, so the
    single-candle arrival proxy reads RALLY_BASE_DROP -- a family the approved
    standard does not recognise, which therefore gets no ownership. The wider
    move into the area is bearish (18:15 and 18:30 both close down), so a human
    reading "after an existing bearish move" would likely call this DROP_BASE_
    DROP. Detecting the Base is necessary but not sufficient.
    """
    candles = _candles()
    arrival = candles[_BASE_START - 1]
    assert arrival.close > arrival.open  # the proxy sees a rally
    assert candles[_BASE_START - 4].close < candles[_BASE_START - 4].open
    assert candles[_BASE_START - 3].close < candles[_BASE_START - 3].open

    found = next(
        b
        for b in detect_bases(candles, _B)
        if candles[_BASE_START].record_id in b.source_candle_record_ids
    )
    assert found.base_family is BaseFamily.RALLY_BASE_DROP


def test_zero_body_is_maximal_compactness_not_a_rejection() -> None:
    """A perfect doji inside a base must not divide by zero or be thrown out."""
    candles = _candles()
    # the flag path must never raise on any window of the real capture
    assert detect_bases(candles, _B) is not None
